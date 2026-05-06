// ACPI Embedded Controller driver — standard I/O port interface.
//
// I/O ports (defined in ACPI ECDT or DSDT _CRS; 0x62/0x66 is universal):
//   0x62  EC data register   (read response / write data)
//   0x66  EC command/status  (write command / read status flags)
//
// Status bits:
//   bit 0  OBF — Output Buffer Full: EC has data ready to read
//   bit 1  IBF — Input Buffer Full:  EC is processing; must wait before write
//   bit 3  CMD — last write was a command byte (not data)
//
// Commands used here:
//   0x80  RD_EC  — read byte:  send 0x80, send address, read result
//   0x81  WR_EC  — write byte: send 0x81, send address, send data

use crate::arch::{inb, outb};

const EC_DATA: u16 = 0x62;
const EC_CMD:  u16 = 0x66;
const OBF: u8 = 0x01;
const IBF: u8 = 0x02;

const TIMEOUT: u32 = 250_000;

fn wait_ibf_clear() -> bool {
    for _ in 0..TIMEOUT {
        if unsafe { inb(EC_CMD) } & IBF == 0 { return true; }
        unsafe { core::arch::asm!("pause", options(nostack, nomem)); }
    }
    false
}

fn wait_obf_set() -> bool {
    for _ in 0..TIMEOUT {
        if unsafe { inb(EC_CMD) } & OBF != 0 { return true; }
        unsafe { core::arch::asm!("pause", options(nostack, nomem)); }
    }
    false
}

/// Read one byte from EC address space at `addr`.
pub fn read(addr: u8) -> Option<u8> {
    if !wait_ibf_clear() { return None; }
    unsafe { outb(EC_CMD, 0x80); }
    if !wait_ibf_clear() { return None; }
    unsafe { outb(EC_DATA, addr); }
    if !wait_obf_set() { return None; }
    Some(unsafe { inb(EC_DATA) })
}

/// Write one byte to EC address space at `addr`.
pub fn write(addr: u8, val: u8) -> bool {
    if !wait_ibf_clear() { return false; }
    unsafe { outb(EC_CMD, 0x81); }
    if !wait_ibf_clear() { return false; }
    unsafe { outb(EC_DATA, addr); }
    if !wait_ibf_clear() { return false; }
    unsafe { outb(EC_DATA, val); }
    true
}

/// Read a little-endian 16-bit word at `addr` and `addr + 1`.
pub fn read_word(addr: u8) -> Option<u16> {
    let lo = read(addr)?;
    let hi = read(addr.wrapping_add(1))?;
    Some(lo as u16 | ((hi as u16) << 8))
}

/// Returns true if the EC status register gives a sane response.
/// Does not touch the data port so it is side-effect free.
pub fn present() -> bool {
    let s = unsafe { inb(EC_CMD) };
    s != 0xFF   // 0xFF means no device on the bus
}
