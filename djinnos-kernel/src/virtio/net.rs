// VirtIO network driver — device ID 1, legacy MMIO transport.
//
// Two virtqueues:
//   0 — receiveq:  we offer buffers; device fills them with incoming frames.
//   1 — transmitq: we push frames; device drains them onto the wire.
//
// Each buffer carries a 12-byte virtio_net_hdr prefix.  For our purposes
// (no GSO/checksum offload) the header is always zero on TX and ignored on RX.
//
// The driver is split into separate RxHalf and TxHalf so smoltcp's Device
// GAT lifetime rules can be satisfied without unsafe aliasing.

use super::mmio::{VirtioMmio, *};
use super::queue::{VirtQueue, Descriptor, AvailRing, UsedRing, QUEUE_SIZE, DESC_F_WRITE};
use core::sync::atomic::{fence, Ordering};
use alloc::vec::Vec;

pub const DEVICE_NET: u32 = 1;

const NET_HDR_LEN: usize = 12;          // virtio_net_hdr is always 12 bytes
const MAX_FRAME:   usize = 1514;        // max Ethernet payload
const BUF_SIZE:    usize = NET_HDR_LEN + MAX_FRAME;
const N_RX:        usize = 8;           // pre-filled RX slots

// ── Static memory ─────────────────────────────────────────────────────────────

#[repr(C, align(4096))]
struct QMem([u8; 8192]);

static mut RX_QMEM: QMem = QMem([0u8; 8192]);
static mut TX_QMEM: QMem = QMem([0u8; 8192]);

static mut RX_BUFS: [[u8; BUF_SIZE]; N_RX] = [[0u8; BUF_SIZE]; N_RX];
static mut TX_BUF:  [u8; BUF_SIZE]         = [0u8; BUF_SIZE];

const DESC_OFF:  usize = 0;
const AVAIL_OFF: usize = QUEUE_SIZE * 16;
const USED_OFF:  usize = 4096;

// ── RX half ───────────────────────────────────────────────────────────────────

pub struct RxHalf {
    q:        VirtQueue,
    dev_base: u64,
    // which slots are currently awaiting re-offer after the receive path
    used_slots: [bool; N_RX],
}

impl RxHalf {
    fn notify(&self) {
        let dev = VirtioMmio::new(self.dev_base);
        dev.write(REG_QUEUE_NOTIFY, 0);
    }

    fn offer(&mut self, slot: usize) {
        let phys = unsafe { RX_BUFS[slot].as_ptr() as u64 };
        self.q.offer(phys, BUF_SIZE as u32);
        self.used_slots[slot] = false;
    }

    /// Return all slots that were consumed during the last smoltcp poll.
    pub fn reclaim_consumed(&mut self) {
        for i in 0..N_RX {
            if self.used_slots[i] {
                self.offer(i);
            }
        }
        self.notify();
    }

    /// Non-blocking receive.  Returns the packet data (without the 12-byte header)
    /// as a heap-allocated Vec, so TxHalf can be borrowed simultaneously.
    pub fn try_recv(&mut self) -> Option<Vec<u8>> {
        fence(Ordering::SeqCst);
        if self.q.used.idx == self.q.last_used { return None; }

        let used_idx = (self.q.last_used as usize) % QUEUE_SIZE;
        let entry    = &self.q.used.ring[used_idx];
        let desc_id  = entry.id as usize % N_RX;
        let full_len = entry.len as usize;
        self.q.last_used = self.q.last_used.wrapping_add(1);

        let data_len = full_len.saturating_sub(NET_HDR_LEN).min(MAX_FRAME);
        let data = unsafe {
            RX_BUFS[desc_id][NET_HDR_LEN..NET_HDR_LEN + data_len].to_vec()
        };
        // Mark as used — reclaim_consumed() will re-offer after smoltcp processes it.
        self.used_slots[desc_id] = true;

        Some(data)
    }
}

// ── TX half ───────────────────────────────────────────────────────────────────

pub struct TxHalf {
    q:        VirtQueue,
    dev_base: u64,
}

impl TxHalf {
    /// Transmit `data` (an Ethernet frame, without the virtio_net_hdr).
    pub fn send(&mut self, data: &[u8]) {
        let len = data.len().min(MAX_FRAME);
        unsafe {
            TX_BUF[..NET_HDR_LEN].fill(0);   // zero virtio_net_hdr
            TX_BUF[NET_HDR_LEN..NET_HDR_LEN + len].copy_from_slice(&data[..len]);
            let phys = TX_BUF.as_ptr() as u64;
            // Single device-readable descriptor (no response needed for TX).
            let i = self.q.free_head as usize;
            self.q.desc[i] = Descriptor {
                addr:  phys,
                len:   (NET_HDR_LEN + len) as u32,
                flags: 0,
                next:  0,
            };
            self.q.free_head = ((i + 1) % QUEUE_SIZE) as u16;
            let avail_idx = (self.q.avail.idx as usize) % QUEUE_SIZE;
            self.q.avail.ring[avail_idx] = i as u16;
            fence(Ordering::SeqCst);
            self.q.avail.idx = self.q.avail.idx.wrapping_add(1);
            fence(Ordering::SeqCst);
        }
        let dev = VirtioMmio::new(self.dev_base);
        dev.write(REG_QUEUE_NOTIFY, 1);
        // Drain the used ring so we don't run out of descriptor slots.
        fence(Ordering::SeqCst);
        while self.q.used.idx != self.q.last_used {
            self.q.last_used = self.q.last_used.wrapping_add(1);
            fence(Ordering::SeqCst);
        }
    }
}

// ── Combined driver (owns both halves) ────────────────────────────────────────

pub struct NetDriver {
    pub rx:  RxHalf,
    pub tx:  TxHalf,
    pub mac: [u8; 6],
}

impl NetDriver {
    pub fn init(base: u64) -> Option<Self> {
        let dev = VirtioMmio::new(base);

        // Standard VirtIO init sequence.
        dev.write(REG_STATUS, 0);
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE);
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE | STATUS_DRIVER);

        dev.write(REG_DEVICE_FEAT_SEL, 0);
        dev.write(REG_DRIVER_FEAT_SEL, 0);
        dev.write(REG_DRIVER_FEATURES, 0);   // negotiate nothing extra

        let s = dev.read(REG_STATUS) | STATUS_FEATURES_OK;
        dev.write(REG_STATUS, s);
        if dev.read(REG_STATUS) & STATUS_FEATURES_OK == 0 { return None; }

        dev.write(REG_GUEST_PAGE_SIZE, 4096);

        // RX queue (0).
        dev.write(REG_QUEUE_SEL, 0);
        if dev.read(REG_QUEUE_NUM_MAX) < QUEUE_SIZE as u32 { return None; }
        dev.write(REG_QUEUE_NUM,   QUEUE_SIZE as u32);
        dev.write(REG_QUEUE_ALIGN, 4096);
        let rx_phys = unsafe { RX_QMEM.0.as_ptr() as u64 };
        dev.write(REG_QUEUE_PFN, (rx_phys >> 12) as u32);

        // TX queue (1).
        dev.write(REG_QUEUE_SEL, 1);
        if dev.read(REG_QUEUE_NUM_MAX) < QUEUE_SIZE as u32 { return None; }
        dev.write(REG_QUEUE_NUM,   QUEUE_SIZE as u32);
        dev.write(REG_QUEUE_ALIGN, 4096);
        let tx_phys = unsafe { TX_QMEM.0.as_ptr() as u64 };
        dev.write(REG_QUEUE_PFN, (tx_phys >> 12) as u32);

        dev.write(REG_STATUS, dev.read(REG_STATUS) | STATUS_DRIVER_OK);

        // Read MAC address from config space (6 bytes at offset 0).
        let w0 = dev.read(REG_CONFIG);
        let w1 = dev.read(REG_CONFIG + 4);
        let mac = [
            w0 as u8, (w0 >> 8) as u8, (w0 >> 16) as u8, (w0 >> 24) as u8,
            w1 as u8, (w1 >> 8) as u8,
        ];

        let (rx_q, tx_q) = unsafe {
            let rb = RX_QMEM.0.as_mut_ptr();
            let rx_q = VirtQueue {
                desc:      &mut *(rb.add(DESC_OFF)  as *mut [Descriptor; QUEUE_SIZE]),
                avail:     &mut *(rb.add(AVAIL_OFF) as *mut AvailRing),
                used:      &    *(rb.add(USED_OFF)  as *const UsedRing),
                free_head: 0,
                last_used: 0,
            };
            let tb = TX_QMEM.0.as_mut_ptr();
            let tx_q = VirtQueue {
                desc:      &mut *(tb.add(DESC_OFF)  as *mut [Descriptor; QUEUE_SIZE]),
                avail:     &mut *(tb.add(AVAIL_OFF) as *mut AvailRing),
                used:      &    *(tb.add(USED_OFF)  as *const UsedRing),
                free_head: 0,
                last_used: 0,
            };
            (rx_q, tx_q)
        };

        let mut drv = NetDriver {
            rx: RxHalf { q: rx_q, dev_base: base, used_slots: [false; N_RX] },
            tx: TxHalf { q: tx_q, dev_base: base },
            mac,
        };

        // Pre-fill all RX slots and notify the device.
        for i in 0..N_RX { drv.rx.offer(i); }
        drv.rx.notify();

        Some(drv)
    }
}

/// Scan the VirtIO bus for the first network device (ID 1).
pub fn find_net() -> Option<u64> {
    for slot in 0..VIRTIO_SLOTS {
        let base = VIRTIO_BASE + slot * VIRTIO_STRIDE;
        let dev  = VirtioMmio::new(base);
        if dev.read(REG_MAGIC)     != VIRTIO_MAGIC { continue; }
        if dev.read(REG_DEVICE_ID) == DEVICE_NET   { return Some(base); }
    }
    None
}
