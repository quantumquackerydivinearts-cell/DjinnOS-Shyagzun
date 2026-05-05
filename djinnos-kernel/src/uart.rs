// 16550A UART — QEMU virt maps it at 0x10000000.
// One byte writes, no interrupts needed for early boot output.

const UART: *mut u8 = 0x10000000 as *mut u8;

pub fn putc(byte: u8) {
    unsafe { UART.write_volatile(byte) }
}

pub fn puts(s: &str) {
    for b in s.bytes() { putc(b); }
}

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