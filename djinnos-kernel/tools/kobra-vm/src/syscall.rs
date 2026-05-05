#[inline(always)]
pub fn write(fd: usize, buf: &[u8]) {
    unsafe {
        core::arch::asm!(
            "ecall",
            in("a7") 3usize,
            in("a0") fd,
            in("a1") buf.as_ptr() as usize,
            in("a2") buf.len(),
            options(nostack),
        );
    }
}

#[inline(always)]
pub fn read(fd: usize, buf: &mut [u8]) -> usize {
    let n: usize;
    unsafe {
        core::arch::asm!(
            "ecall",
            in("a7") 4usize,
            in("a0") fd,
            in("a1") buf.as_mut_ptr() as usize,
            in("a2") buf.len(),
            lateout("a0") n,
            options(nostack),
        );
    }
    n
}

#[inline(always)]
pub fn exit(code: i32) -> ! {
    unsafe {
        core::arch::asm!(
            "ecall",
            in("a7") 1usize,
            in("a0") code as usize,
            options(nostack, noreturn),
        );
    }
}

pub fn print(s: &[u8]) { write(1, s); }

pub fn println(s: &[u8]) { write(1, s); write(1, b"\r\n"); }