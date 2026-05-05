// UART abstraction.
//
// RISC-V: 16550A mapped at 0x10000000 (QEMU virt MMIO).
// x86_64:  COM1 at I/O port 0x3F8 (16550A, programmed by arch::uart_init).

#[cfg(target_arch = "riscv64")]
const UART_MMIO: *mut u8 = 0x10000000 as *mut u8;

pub fn putc(byte: u8) {
    #[cfg(target_arch = "riscv64")]
    unsafe { UART_MMIO.write_volatile(byte) }

    #[cfg(target_arch = "x86_64")]
    crate::arch::uart_putc(byte);
}

/// Non-blocking read — returns None if no byte waiting.
#[allow(dead_code)]
pub fn getc() -> Option<u8> {
    #[cfg(target_arch = "riscv64")]
    { None }  // RISC-V uses VirtIO keyboard, not UART input

    #[cfg(target_arch = "x86_64")]
    crate::arch::uart_getc()
}

pub fn puts(s: &str) {
    for b in s.bytes() { putc(b); }
}

pub fn putc_char(c: u8) { putc(c); }

pub fn putu(mut n: u64) {
    if n == 0 { putc(b'0'); return; }
    let mut buf = [0u8; 20];
    let mut i = 20usize;
    while n > 0 {
        i -= 1;
        buf[i] = b'0' + (n % 10) as u8;
        n /= 10;
    }
    for &b in &buf[i..] { putc(b); }
}

pub fn putx(mut n: u64) {
    let digits = b"0123456789abcdef";
    let mut buf = [0u8; 16];
    let mut i = 16usize;
    if n == 0 { putc(b'0'); return; }
    while n > 0 {
        i -= 1;
        buf[i] = digits[(n & 0xf) as usize];
        n >>= 4;
    }
    for &b in &buf[i..] { putc(b); }
}