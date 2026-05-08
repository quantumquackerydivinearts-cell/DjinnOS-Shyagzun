// Intel e1000 NIC driver — polling mode, no interrupts.
//
// Supports: 82540EM (QEMU -device e1000), 82545EM, 82574L (e1000e),
//           I217-LM, I219-V/LM, I211 — all share the same MMIO layout.
//
// Interface mirrors VirtIO NetDriver (same field names / method signatures)
// so net_stack.rs compiles unchanged on x86_64 via a type alias.

use alloc::vec::Vec;

// ── MMIO register offsets ─────────────────────────────────────────────────────

const REG_CTRL:  u32 = 0x0000;
const REG_EERD:  u32 = 0x0014;
const REG_IMC:   u32 = 0x00D8;
const REG_RCTL:  u32 = 0x0100;
const REG_TCTL:  u32 = 0x0400;
const REG_TIPG:  u32 = 0x0410;
const REG_RDBAL: u32 = 0x2800;
const REG_RDBAH: u32 = 0x2804;
const REG_RDLEN: u32 = 0x2808;
const REG_RDH:   u32 = 0x2810;
const REG_RDT:   u32 = 0x2818;
const REG_TDBAL: u32 = 0x3800;
const REG_TDBAH: u32 = 0x3804;
const REG_TDLEN: u32 = 0x3808;
const REG_TDH:   u32 = 0x3810;
const REG_TDT:   u32 = 0x3818;
const REG_MTA:   u32 = 0x5200;  // 128 × u32 multicast table
const REG_RAL0:  u32 = 0x5400;
const REG_RAH0:  u32 = 0x5404;

// CTRL
const CTRL_SLU: u32 = 1 << 6;   // Set Link Up
const CTRL_RST: u32 = 1 << 26;  // Software reset

// RCTL
const RCTL_EN:    u32 = 1 << 1;   // Receiver Enable
const RCTL_BAM:   u32 = 1 << 15;  // Broadcast Accept Mode
const RCTL_SECRC: u32 = 1 << 26;  // Strip CRC

// TCTL
const TCTL_EN:   u32 = 1 << 1;        // Transmit Enable
const TCTL_PSP:  u32 = 1 << 3;        // Pad Short Packets
const TCTL_CT:   u32 = 0x0F << 4;     // Collision Threshold (16)
const TCTL_COLD: u32 = 0x3F << 12;    // Collision Distance (full-duplex)

// TX descriptor command byte
const CMD_EOP:  u8 = 0x01;  // End of Packet
const CMD_IFCS: u8 = 0x02;  // Insert FCS/CRC
const CMD_RS:   u8 = 0x08;  // Report Status (set DD on completion)

// RX descriptor status bits
const RX_DD: u8 = 0x01;  // Descriptor Done

// Ring and buffer sizes
const RX_N:     usize = 32;
const TX_N:     usize = 32;
const BUF_SIZE: usize = 2048;

// ── Descriptor layouts ────────────────────────────────────────────────────────

#[repr(C)]
#[derive(Clone, Copy)]
struct RxDesc {
    addr:    u64,
    length:  u16,
    csum:    u16,
    status:  u8,
    errors:  u8,
    special: u16,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct TxDesc {
    addr:    u64,
    length:  u16,
    cso:     u8,   // checksum offset (unused)
    cmd:     u8,
    status:  u8,
    css:     u8,   // checksum start (unused)
    special: u16,
}

impl RxDesc { const fn new() -> Self { RxDesc { addr: 0, length: 0, csum: 0, status: 0, errors: 0, special: 0 } } }
impl TxDesc { const fn new() -> Self { TxDesc { addr: 0, length: 0, cso: 0, cmd: 0, status: 0xFF, css: 0, special: 0 } } }

// ── Static DMA-accessible memory (lives in BSS, naturally aligned) ─────────────

#[repr(C, align(16))]
struct RxRing([RxDesc; RX_N]);
#[repr(C, align(16))]
struct TxRing([TxDesc; TX_N]);

static mut RX_RING: RxRing = RxRing([RxDesc::new(); RX_N]);
static mut TX_RING: TxRing = TxRing([TxDesc::new(); TX_N]);
static mut RX_BUFS: [[u8; BUF_SIZE]; RX_N] = [[0u8; BUF_SIZE]; RX_N];
static mut TX_BUFS: [[u8; BUF_SIZE]; TX_N] = [[0u8; BUF_SIZE]; TX_N];

// ── Helpers ───────────────────────────────────────────────────────────────────

fn put_hex_byte(v: u8) {
    const H: [u8; 16] = *b"0123456789abcdef";
    crate::uart::putc(H[(v >> 4) as usize]);
    crate::uart::putc(H[(v & 0xf) as usize]);
}

// ── MMIO accessors ────────────────────────────────────────────────────────────

#[inline(always)]
fn wr(base: u64, off: u32, val: u32) {
    unsafe { ((base + off as u64) as *mut u32).write_volatile(val); }
}

#[inline(always)]
fn rd(base: u64, off: u32) -> u32 {
    unsafe { ((base + off as u64) as *const u32).read_volatile() }
}

// ── EEPROM ────────────────────────────────────────────────────────────────────
//
// 82540EM EERD layout:  bits[7:2]=word-addr  bit[0]=START  bit[4]=DONE  bits[31:16]=DATA

fn eeprom_read(base: u64, word: u8) -> u16 {
    wr(base, REG_EERD, ((word as u32) << 2) | 1);
    loop {
        let v = rd(base, REG_EERD);
        if v & (1 << 4) != 0 { return (v >> 16) as u16; }
        core::hint::spin_loop();
    }
}

fn mac_from_eeprom(base: u64) -> [u8; 6] {
    let w0 = eeprom_read(base, 0);
    let w1 = eeprom_read(base, 1);
    let w2 = eeprom_read(base, 2);
    [w0 as u8, (w0 >> 8) as u8, w1 as u8, (w1 >> 8) as u8, w2 as u8, (w2 >> 8) as u8]
}

// ── RX half ───────────────────────────────────────────────────────────────────

pub struct E1000Rx {
    mmio: u64,
    head: usize,  // next descriptor to poll
}

impl E1000Rx {
    /// Non-blocking receive.  Copies frame into a Vec, re-offers the DMA slot.
    /// Returns None immediately if no frame is waiting.
    pub fn try_recv(&mut self) -> Option<Vec<u8>> {
        let status = unsafe { RX_RING.0[self.head].status };
        if status & RX_DD == 0 { return None; }
        let len = (unsafe { RX_RING.0[self.head].length } as usize).min(BUF_SIZE);
        let frame = unsafe { RX_BUFS[self.head][..len].to_vec() };
        // Re-offer this slot to hardware before advancing head.
        unsafe { RX_RING.0[self.head].status = 0; }
        wr(self.mmio, REG_RDT, self.head as u32);
        self.head = (self.head + 1) % RX_N;
        Some(frame)
    }

    /// No-op: e1000 reclaims inline in try_recv (unlike VirtIO which batches).
    pub fn reclaim_consumed(&mut self) {}
}

// ── TX half ───────────────────────────────────────────────────────────────────

pub struct E1000Tx {
    mmio: u64,
    tail: usize,  // next descriptor to fill
}

impl E1000Tx {
    /// Synchronous send — returns after the NIC confirms the frame is queued.
    pub fn send(&mut self, data: &[u8]) {
        let n = data.len().min(BUF_SIZE);
        let i = self.tail;
        unsafe {
            TX_BUFS[i][..n].copy_from_slice(&data[..n]);
            TX_RING.0[i].addr   = TX_BUFS[i].as_ptr() as u64;
            TX_RING.0[i].length = n as u16;
            TX_RING.0[i].cmd    = CMD_EOP | CMD_IFCS | CMD_RS;
            TX_RING.0[i].status = 0;
        }
        self.tail = (i + 1) % TX_N;
        wr(self.mmio, REG_TDT, self.tail as u32);
        // Spin until DD (Descriptor Done) confirms the NIC has consumed the descriptor.
        for _ in 0u32..200_000 {
            if unsafe { TX_RING.0[i].status } & 0x01 != 0 { break; }
            core::hint::spin_loop();
        }
    }
}

// ── Combined driver (mirrors VirtIO NetDriver layout) ─────────────────────────

pub struct E1000Net {
    pub mac: [u8; 6],
    pub rx:  E1000Rx,
    pub tx:  E1000Tx,
}

// PCI IDs: Intel vendor + known PRO/1000 / e1000e / I2xx device IDs.
pub const VENDOR: u16 = 0x8086;
const DEVICE_IDS: &[u16] = &[
    0x100E, // 82540EM  — QEMU default
    0x100F, // 82545EM  — common server NIC
    0x10D3, // 82574L   — e1000e, common on older Intel boards
    0x10EA, // 82577LM  — Centrino platforms
    0x1502, // 82579LM  — Sandy/Ivy Bridge
    0x1503, // 82579V
    0x153A, // I217-LM  — Haswell
    0x153B, // I217-V
    0x1559, // I218-V   — Broadwell
    0x15A0, // I218-LM
    0x1533, // I210
    0x1539, // I211
    0x15B7, // I219-LM  — Skylake+ (very common)
    0x15B8, // I219-V
    0x15D7, // I219-LM (Kaby Lake)
    0x15D8, // I219-V  (Kaby Lake)
    0x15E3, // I219-LM (Coffee Lake)
    0x156F, // I219-LM (Cannon Lake)
    0x1570, // I219-V  (Cannon Lake)
    0x0D4F, // I219-LM (Tiger Lake)
    0x0D4C, // I219-V  (Tiger Lake)
    0x0DC7, // I219-LM (Alder Lake)
    0x0DC8, // I219-V  (Alder Lake)
];

impl E1000Net {
    pub fn init(mmio_base: u64, bus: u8, dev: u8, func: u8) -> Option<Self> {
        // Enable MMIO decoding + bus mastering in PCI command register.
        unsafe {
            let cmd = crate::pci::read16(bus, dev, func, 0x04);
            crate::pci::write32(bus, dev, func, 0x04, (cmd | 0x0006) as u32);
        }

        // Software reset — wait for it to de-assert.
        wr(mmio_base, REG_CTRL, rd(mmio_base, REG_CTRL) | CTRL_RST);
        for _ in 0u32..10_000 { core::hint::spin_loop(); }
        while rd(mmio_base, REG_CTRL) & CTRL_RST != 0 { core::hint::spin_loop(); }

        // Set link-up, disable auto-speed detection (ASDE off).
        wr(mmio_base, REG_CTRL, rd(mmio_base, REG_CTRL) | CTRL_SLU);

        // Mask all interrupts — we poll.
        wr(mmio_base, REG_IMC, 0xFFFF_FFFF);

        // Read MAC from EEPROM, program into Receive Address register 0.
        let mac = mac_from_eeprom(mmio_base);
        let ral = u32::from_le_bytes([mac[0], mac[1], mac[2], mac[3]]);
        let rah = (mac[4] as u32) | ((mac[5] as u32) << 8) | (1 << 31); // AV bit
        wr(mmio_base, REG_RAL0, ral);
        wr(mmio_base, REG_RAH0, rah);

        // Clear Multicast Table Array (128 words).
        for i in 0u32..128 { wr(mmio_base, REG_MTA + i * 4, 0); }

        // ── RX ring setup ──────────────────────────────────────────────────────
        for i in 0..RX_N {
            unsafe {
                RX_RING.0[i].addr   = RX_BUFS[i].as_ptr() as u64;
                RX_RING.0[i].status = 0;
            }
        }
        let rx_phys = unsafe { RX_RING.0.as_ptr() as u64 };
        wr(mmio_base, REG_RDBAL, rx_phys as u32);
        wr(mmio_base, REG_RDBAH, (rx_phys >> 32) as u32);
        wr(mmio_base, REG_RDLEN, (RX_N * 16) as u32);
        wr(mmio_base, REG_RDH, 0);
        // Offer all but the last slot so head != tail.
        wr(mmio_base, REG_RDT, (RX_N - 1) as u32);
        // RCTL: enable, accept broadcast, strip CRC, 2048-byte buffers (BSIZE=00).
        wr(mmio_base, REG_RCTL, RCTL_EN | RCTL_BAM | RCTL_SECRC);

        // ── TX ring setup ──────────────────────────────────────────────────────
        for i in 0..TX_N {
            unsafe {
                TX_RING.0[i].addr   = TX_BUFS[i].as_ptr() as u64;
                TX_RING.0[i].status = 0xFF; // pre-mark all as done
            }
        }
        let tx_phys = unsafe { TX_RING.0.as_ptr() as u64 };
        wr(mmio_base, REG_TDBAL, tx_phys as u32);
        wr(mmio_base, REG_TDBAH, (tx_phys >> 32) as u32);
        wr(mmio_base, REG_TDLEN, (TX_N * 16) as u32);
        wr(mmio_base, REG_TDH, 0);
        wr(mmio_base, REG_TDT, 0);
        // TCTL: enable, pad short packets.
        wr(mmio_base, REG_TCTL, TCTL_EN | TCTL_PSP | TCTL_CT | TCTL_COLD);
        // Standard IPG for copper (from the 82540EM datasheet).
        wr(mmio_base, REG_TIPG, 0x0060_2006);

        crate::uart::puts("e1000: MAC ");
        for (k, &b) in mac.iter().enumerate() {
            if k > 0 { crate::uart::puts(":"); }
            put_hex_byte(b);
        }
        crate::uart::puts("\r\n");

        Some(E1000Net {
            mac,
            rx: E1000Rx { mmio: mmio_base, head: 0 },
            tx: E1000Tx { mmio: mmio_base, tail: 0 },
        })
    }

    /// Scan the PCI device table for a supported Intel NIC and initialise it.
    pub fn find_and_init() -> Option<Self> {
        for slot in crate::pci::devices() {
            let d = match slot { Some(d) => d, None => continue };
            if d.vendor != VENDOR { continue; }
            if !DEVICE_IDS.contains(&d.device) { continue; }
            let mmio = d.bar_mem64(0).or_else(|| d.bar_mem32(0))?;
            crate::uart::puts("e1000: device ");
            crate::uart::putx(d.device as u64);
            crate::uart::puts(" BAR0=");
            crate::uart::putx(mmio);
            crate::uart::puts("\r\n");
            return Self::init(mmio, d.bus, d.dev, d.func);
        }
        None
    }
}