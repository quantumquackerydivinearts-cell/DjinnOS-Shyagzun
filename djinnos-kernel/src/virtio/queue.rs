// VirtIO split-ring virtqueue — polling mode (no interrupts).
//
// The descriptor table, available ring, and used ring are statically allocated.
// All memory is physically contiguous (no IOMMU on QEMU virt).

use core::sync::atomic::{fence, Ordering};
use core::ptr::{read_volatile, write_volatile};

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
    // Raw pointers: the three ring regions are non-overlapping parts of the
    // same static buffer.  Using &'static mut references for all three is
    // technically aliasing-UB under Rust's borrow model even when the ranges
    // are disjoint; raw pointers carry no aliasing obligations.
    //
    // IMPORTANT: all three pointer fields are loaded with read_volatile in
    // every method.  Fat LTO + -Oz may otherwise keep the values only in
    // registers and not write them to the struct's memory, so non-volatile
    // reads of these fields (e.g. in a non-inlined callee) get BSS-zero
    // instead of the correct address.
    pub desc:       *mut [Descriptor; QUEUE_SIZE],
    pub avail:      *mut AvailRing,
    pub used:       *const UsedRing,   // device writes here; we only read
    pub free_head:  u16,
    pub last_used:  u16,
}

impl VirtQueue {
    /// Create a VirtQueue and write all pointer fields with volatile semantics.
    /// This guarantees the pointer values land in the struct's memory even when
    /// -Oz/LTO would otherwise keep them only in registers.
    #[inline(never)]
    pub unsafe fn new(
        desc:  *mut [Descriptor; QUEUE_SIZE],
        avail: *mut AvailRing,
        used:  *const UsedRing,
    ) -> Self {
        let mut q = VirtQueue { desc, avail, used, free_head: 0, last_used: 0 };
        // Volatile self-writes: force the pointer values into q's memory so
        // that any later (non-inlined) reader gets the correct addresses.
        write_volatile(&mut q.desc,  desc);
        write_volatile(&mut q.avail, avail);
        write_volatile(&mut q.used  as *mut *const UsedRing, used);
        q
    }

    // Volatile loads of the pointer fields prevent the compiler from
    // treating them as "always known" and substituting cached/zero values.
    #[inline(always)]
    unsafe fn vp_desc(&self) -> *mut [Descriptor; QUEUE_SIZE] {
        read_volatile(&self.desc as *const *mut [Descriptor; QUEUE_SIZE])
    }
    #[inline(always)]
    unsafe fn vp_avail(&self) -> *mut AvailRing {
        read_volatile(&self.avail as *const *mut AvailRing)
    }
    #[inline(always)]
    unsafe fn vp_used(&self) -> *const UsedRing {
        read_volatile(&self.used as *const *const UsedRing)
    }
}

impl VirtQueue {
    /// Send a two-descriptor chain: `cmd` is device-readable, `resp` is device-writable.
    /// Returns the descriptor index of the head.
    pub fn send(&mut self, cmd: u64, cmd_len: u32, resp: u64, resp_len: u32) -> u16 {
        let i = self.free_head as usize;
        let j = (i + 1) % QUEUE_SIZE;

        unsafe {
            let desc = self.vp_desc();
            write_volatile(&mut (*desc)[i], Descriptor { addr: cmd,  len: cmd_len,  flags: DESC_F_NEXT,  next: j as u16 });
            write_volatile(&mut (*desc)[j], Descriptor { addr: resp, len: resp_len, flags: DESC_F_WRITE, next: 0 });
        }
        self.free_head = ((j + 1) % QUEUE_SIZE) as u16;

        unsafe {
            let avail = self.vp_avail();
            let cur_idx = read_volatile(&(*avail).idx);
            let avail_idx = (cur_idx as usize) % QUEUE_SIZE;
            write_volatile(&mut (*avail).ring[avail_idx], i as u16);
            fence(Ordering::SeqCst);
            write_volatile(&mut (*avail).idx, cur_idx.wrapping_add(1));
            fence(Ordering::SeqCst);
        }
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

        unsafe {
            let desc = self.vp_desc();
            write_volatile(&mut (*desc)[i], Descriptor { addr: a0, len: n0, flags: f0 | DESC_F_NEXT, next: j as u16 });
            write_volatile(&mut (*desc)[j], Descriptor { addr: a1, len: n1, flags: f1 | DESC_F_NEXT, next: k as u16 });
            write_volatile(&mut (*desc)[k], Descriptor { addr: a2, len: n2, flags: f2,               next: 0 });
        }
        self.free_head = ((k + 1) % QUEUE_SIZE) as u16;

        unsafe {
            let avail = self.vp_avail();
            let cur_idx = read_volatile(&(*avail).idx);
            let avail_idx = (cur_idx as usize) % QUEUE_SIZE;
            write_volatile(&mut (*avail).ring[avail_idx], i as u16);
            fence(Ordering::SeqCst);
            write_volatile(&mut (*avail).idx, cur_idx.wrapping_add(1));
            fence(Ordering::SeqCst);
        }

        i as u16
    }

    /// Spin until the device has consumed at least one entry from the used ring.
    pub fn poll(&mut self) {
        loop {
            fence(Ordering::SeqCst);
            if unsafe { read_volatile(&(*self.vp_used()).idx) } != self.last_used { break; }
        }
        self.last_used = self.last_used.wrapping_add(1);
    }

    /// Offer a single device-writable buffer (receive pattern for input queues).
    pub fn offer(&mut self, buf: u64, len: u32) {
        let i = self.free_head as usize;
        unsafe {
            let desc = self.vp_desc();
            write_volatile(&mut (*desc)[i], Descriptor { addr: buf, len, flags: DESC_F_WRITE, next: 0 });
        }
        self.free_head = ((i + 1) % QUEUE_SIZE) as u16;

        unsafe {
            let avail = self.vp_avail();
            let cur_idx = read_volatile(&(*avail).idx);
            let avail_idx = (cur_idx as usize) % QUEUE_SIZE;
            write_volatile(&mut (*avail).ring[avail_idx], i as u16);
            fence(Ordering::SeqCst);
            write_volatile(&mut (*avail).idx, cur_idx.wrapping_add(1));
            fence(Ordering::SeqCst);
        }
    }

    /// Non-blocking: return the descriptor id if the device has written an event.
    pub fn try_recv(&mut self) -> Option<u16> {
        fence(Ordering::SeqCst);
        unsafe {
            let used = self.vp_used();
            if read_volatile(&(*used).idx) == self.last_used { return None; }
            let idx = (self.last_used as usize) % QUEUE_SIZE;
            let id  = read_volatile(&(*used).ring[idx].id) as u16;
            self.last_used = self.last_used.wrapping_add(1);
            Some(id)
        }
    }
}