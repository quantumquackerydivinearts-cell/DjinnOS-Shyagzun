// VirtIO MMIO register interface — version 2 spec.
// QEMU virt places 8 VirtIO slots at 0x10001000..0x10008000 (4KiB each).

use core::ptr::{read_volatile, write_volatile};

pub const VIRTIO_BASE:    u64 = 0x10001000;
pub const VIRTIO_STRIDE:  u64 = 0x1000;
pub const VIRTIO_SLOTS:   u64 = 8;

// Register offsets (bytes)
pub const REG_MAGIC:            usize = 0x000;
pub const REG_VERSION:          usize = 0x004;
pub const REG_DEVICE_ID:        usize = 0x008;
pub const REG_VENDOR_ID:        usize = 0x00c;
pub const REG_DEVICE_FEATURES:  usize = 0x010;
pub const REG_DEVICE_FEAT_SEL:  usize = 0x014;
pub const REG_DRIVER_FEATURES:  usize = 0x020;
pub const REG_DRIVER_FEAT_SEL:  usize = 0x024;
pub const REG_QUEUE_SEL:        usize = 0x030;
pub const REG_QUEUE_NUM_MAX:    usize = 0x034;
pub const REG_QUEUE_NUM:        usize = 0x038;
pub const REG_QUEUE_READY:      usize = 0x044;
pub const REG_QUEUE_NOTIFY:     usize = 0x050;
pub const REG_INTERRUPT_STATUS: usize = 0x060;
pub const REG_INTERRUPT_ACK:    usize = 0x064;
pub const REG_STATUS:           usize = 0x070;
// Version 2 (modern) queue ring pointers
pub const REG_QUEUE_DESC_LOW:   usize = 0x080;
pub const REG_QUEUE_DESC_HIGH:  usize = 0x084;
pub const REG_QUEUE_AVAIL_LOW:  usize = 0x090;
pub const REG_QUEUE_AVAIL_HIGH: usize = 0x094;
pub const REG_QUEUE_USED_LOW:   usize = 0x0a0;
pub const REG_QUEUE_USED_HIGH:  usize = 0x0a4;
pub const REG_CONFIG:           usize = 0x100;

// Version 1 (legacy) queue registers
pub const REG_GUEST_PAGE_SIZE:  usize = 0x028;
pub const REG_QUEUE_ALIGN:      usize = 0x03c;
pub const REG_QUEUE_PFN:        usize = 0x040;

// Device status bits
pub const STATUS_ACKNOWLEDGE:  u32 = 1;
pub const STATUS_DRIVER:       u32 = 2;
pub const STATUS_DRIVER_OK:    u32 = 4;
pub const STATUS_FEATURES_OK:  u32 = 8;
pub const STATUS_FAILED:       u32 = 128;

// Magic value — "virt" in little-endian
pub const VIRTIO_MAGIC: u32 = 0x74726976;

// Device IDs
pub const DEVICE_GPU:   u32 = 16;
pub const DEVICE_BLOCK: u32 =  2;

pub struct VirtioMmio {
    pub base: u64,
}

impl VirtioMmio {
    #[inline(never)]
    pub fn new(base: u64) -> Self {
        let mut s = Self { base };
        // Volatile write forces base into the struct's memory rather than
        // keeping it only in a register under -Oz/LTO.
        unsafe { core::ptr::write_volatile(&mut s.base, base); }
        s
    }

    #[inline]
    pub fn read(&self, offset: usize) -> u32 {
        unsafe { read_volatile((self.base as usize + offset) as *const u32) }
    }

    #[inline]
    pub fn write(&self, offset: usize, val: u32) {
        unsafe { write_volatile((self.base as usize + offset) as *mut u32, val) }
    }
}

/// Scan VirtIO MMIO bus for the first input device (ID 18).
/// GPU: bus=virtio-mmio-bus.1 → slot 1 (0x10002000)
/// KBD: bus=virtio-mmio-bus.3 → slot 3 (0x10004000)
pub fn find_input() -> Option<u64> {
    for slot in 0..VIRTIO_SLOTS {
        let base   = VIRTIO_BASE + slot * VIRTIO_STRIDE;
        let dev    = VirtioMmio::new(base);
        if dev.read(REG_MAGIC)     != VIRTIO_MAGIC           { continue; }
        if dev.read(REG_DEVICE_ID) == super::input::DEVICE_INPUT { return Some(base); }
    }
    None
}

/// Scan VirtIO MMIO bus for the first block device (ID 2).
pub fn find_block() -> Option<u64> {
    for slot in 0..VIRTIO_SLOTS {
        let base = VIRTIO_BASE + slot * VIRTIO_STRIDE;
        let dev  = VirtioMmio::new(base);
        if dev.read(REG_MAGIC)     != VIRTIO_MAGIC  { continue; }
        if dev.read(REG_DEVICE_ID) == DEVICE_BLOCK  { return Some(base); }
    }
    None
}

/// Scan VirtIO MMIO bus and return the base address of the first GPU device.
pub fn find_gpu() -> Option<u64> {
    for slot in 0..VIRTIO_SLOTS {
        let base = VIRTIO_BASE + slot * VIRTIO_STRIDE;
        let dev  = VirtioMmio::new(base);
        if dev.read(REG_MAGIC)     != VIRTIO_MAGIC { continue; }
        if dev.read(REG_DEVICE_ID) == DEVICE_GPU   { return Some(base); }
    }
    None
}