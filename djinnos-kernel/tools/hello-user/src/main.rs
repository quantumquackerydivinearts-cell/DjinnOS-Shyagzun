#![no_std]
#![no_main]

// ── Syscall ABI ───────────────────────────────────────────────────────────────
//   a7=0  sys_putchar(a0: u8)
//   a7=1  sys_exit(a0: i32)
//   a7=3  sys_write(a0: fd, a1: *buf, a2: len) → bytes_written
//   a7=4  sys_read(a0: fd, a1: *buf, a2: max)  → bytes_read

#[inline(always)]
fn sys_write(fd: usize, buf: &[u8]) {
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
fn sys_read(fd: usize, buf: &mut [u8]) -> usize {
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
fn sys_exit(code: i32) -> ! {
    unsafe {
        core::arch::asm!(
            "ecall",
            in("a7") 1usize,
            in("a0") code as usize,
            options(nostack, noreturn),
        );
    }
}

// ── Entry ─────────────────────────────────────────────────────────────────────

#[no_mangle]
#[link_section = ".text.start"]
pub extern "C" fn _start() -> ! {
    sys_write(1, b"\r\nKo shell (user mode)\r\n");
    sys_write(1, b"Type a line, press Enter to echo it back.\r\n");
    sys_write(1, b"Type 'quit' to exit.\r\n\r\n");

    let mut line = [0u8; 80];

    loop {
        sys_write(1, b"user> ");

        // Read one line.
        let mut len = 0usize;
        loop {
            let mut ch = [0u8; 1];
            sys_read(0, &mut ch);
            let b = ch[0];

            if b == b'\n' || b == b'\r' {
                sys_write(1, b"\r\n");
                break;
            } else if b == 0x7F || b == 0x08 {
                // Backspace
                if len > 0 {
                    len -= 1;
                    sys_write(1, b"\x08 \x08");
                }
            } else if b >= 0x20 && len < 79 {
                line[len] = b;
                len += 1;
                sys_write(1, &line[len - 1..len]); // echo
            }
        }

        // Check for 'quit'
        if &line[..len] == b"quit" {
            sys_write(1, b"bye\r\n");
            sys_exit(0);
        }

        if len == 0 { continue; }

        sys_write(1, b"  => ");
        sys_write(1, &line[..len]);
        sys_write(1, b"\r\n");
    }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}