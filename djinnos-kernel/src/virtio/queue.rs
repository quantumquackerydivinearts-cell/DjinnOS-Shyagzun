// VirtIO split-ring virtqueue — polling mode (no interrupts).
//
// The descriptor table, available ring, and used ring are statically allocated.
// All memory is physically contiguous (no IOMMU on QEMU virt).

use core::sync::atomic::{fence, Ordering};

pub const QUEUE_SIZE: usize = 64;

// Descriptor flags
pub const DESC_F_NEXT:  u16 = 1;
pub const DESC_F_WRITE: u16 = 2;   // device writes into this buffer

#[repr(C, align(16))]
pub struct Descriptor {
    pub addr:  u64,
    pub len:   u32,
    pub flags: u16,
    pub next:  u16,
}

#[repr(C, align(2))]
pub struct AvailRing {
    pub flags:      u16,
    pub idx:        u16,
    pub ring:       [u16; QUEUE_SIZE],
    pub used_event: u16,
}

#[repr(C)]
pub struct UsedElem {
    pub id:  u32,
    pub len: u32,
}

#[repr(C, align(4))]
pub struct UsedRing {
    pub flags:       u16,
    pub idx:         u16,
    pub ring:        [UsedElem; QUEUE_SIZE],
    pub avail_event: u16,
}

pub struct VirtQueue {
    pub desc:       &'static mut [Descriptor; QUEUE_SIZE],
    pub avail:      &'static mut AvailRing,
    pub used:       &'static     UsedRing,   // device writes here; we only read
    pub free_head:  u16,
    pub last_used:  u16,
}

impl VirtQueue {
    /// Send a two-descriptor chain: `cmd` is device-readable, `resp` is device-writable.
    /// Returns the descriptor index of the head.
    pub fn send(&mut self, cmd: u64, cmd_len: u32, resp: u64, resp_len: u32) -> u16 {
        let i = self.free_head as usize;
        let j = (i + 1) % QUEUE_SIZE;

        // Command descriptor — device reads
        self.desc[i] = Descriptor {
            addr:  cmd,
            len:   cmd_len,
            flags: DESC_F_NEXT,
            next:  j as u16,
        };

        // Response descriptor — device writes
        self.desc[j] = Descriptor {
            addr:  resp,
            len:   resp_len,
            flags: DESC_F_WRITE,
            next:  0,
        };

        self.free_head = ((j + 1) % QUEUE_SIZE) as u16;

        // Publish to available ring
        let avail_idx = (self.avail.idx as usize) % QUEUE_SIZE;
        self.avail.ring[avail_idx] = i as u16;
        fence(Ordering::SeqCst);
        self.avail.idx = self.avail.idx.wrapping_add(1);
        fence(Ordering::SeqCst);

        i as u16
    }

    /// Send a three-descriptor chain (used for block I/O: header → data → status).
    pub fn send3(
        &mut self,
        a0: u64, n0: u32, f0: u16,
        a1: u64, n1: u32, f1: u16,
        a2: u64, n2: u32, f2: u16,
    ) -> u16 {
        let i = self.free_head as usize;
        let j = (i + 1) % QUEUE_SIZE;
        let k = (i + 2) % QUEUE_SIZE;

        self.desc[i] = Descriptor { addr: a0, len: n0, flags: f0 | DESC_F_NEXT, next: j as u16 };
        self.desc[j] = Descriptor { addr: a1, len: n1, flags: f1 | DESC_F_NEXT, next: k as u16 };
        self.desc[k] = Descriptor { addr: a2, len: n2, flags: f2,               next: 0 };

        self.free_head = ((k + 1) % QUEUE_SIZE) as u16;

        let avail_idx = (self.avail.idx as usize) % QUEUE_SIZE;
        self.avail.ring[avail_idx] = i as u16;
        fence(Ordering::SeqCst);
        self.avail.idx = self.avail.idx.wrapping_add(1);
        fence(Ordering::SeqCst);

        i as u16
    }

    /// Spin until the device has consumed at least one entry from the used ring.
    pub fn poll(&mut self) {
        while self.used.idx == self.last_used {
            fence(Ordering::SeqCst);
        }
        self.last_used = self.last_used.wrapping_add(1);
    }

    /// Offer a single device-writable buffer (receive pattern for input queues).
    pub fn offer(&mut self, buf: u64, len: u32) {
        let i = self.free_head as usize;
        self.desc[i] = Descriptor {
            addr:  buf,
            len,
            flags: DESC_F_WRITE,
            next:  0,
        };
        self.free_head = ((i + 1) % QUEUE_SIZE) as u16;

        let avail_idx = (self.avail.idx as usize) % QUEUE_SIZE;
        self.avail.ring[avail_idx] = i as u16;
        fence(Ordering::SeqCst);
        self.avail.idx = self.avail.idx.wrapping_add(1);
        fence(Ordering::SeqCst);
    }

    /// Non-blocking: return the descriptor id if the device has written an event.
    pub fn try_recv(&mut self) -> Option<u16> {
        fence(Ordering::SeqCst);
        if self.used.idx == self.last_used { return None; }
        let idx  = (self.last_used as usize) % QUEUE_SIZE;
        let id   = self.used.ring[idx].id as u16;
        self.last_used = self.last_used.wrapping_add(1);
        Some(id)
    }
}