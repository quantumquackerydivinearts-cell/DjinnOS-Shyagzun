// Trap / interrupt handler installation.
//
// RISC-V: sets stvec, handles ecalls, supervisor exceptions, timer.
// x86_64: loads IDT via arch::set_trap_vector (which calls arch::init_idt).

#[cfg(target_arch = "riscv64")]
use crate::uart;

#[cfg(target_arch = "riscv64")]
unsafe extern "C" {
    fn _trap_entry();
}

pub fn init() {
    #[cfg(target_arch = "riscv64")]
    crate::arch::set_trap_vector(_trap_entry as *const () as usize as u64);

    #[cfg(target_arch = "x86_64")]
    crate::arch::set_trap_vector(0);  // addr unused; init_idt() populates IDT
}

// ── RISC-V kernel trap handler ────────────────────────────────────────────────

#[cfg(target_arch = "riscv64")]
#[no_mangle]
pub extern "C" fn _trap_handler(cause: u64, sepc: u64, stval: u64) {
    let is_interrupt = cause >> 63 != 0;
    let code = cause & 0x7fff_ffff_ffff_ffff;

    if is_interrupt && code == 5 {
        let next = crate::arch::read_mtime() + crate::arch::TICK_INTERVAL;
        crate::arch::sbi_set_timer(next);
        return;
    }

    uart::puts("\r\n[TRAP] ");
    if is_interrupt { uart::puts("interrupt "); } else { uart::puts("exception "); }
    uart::puts("cause="); uart::putu(code);
    uart::puts(" sepc=0x"); uart::putx(sepc);
    uart::puts(" stval=0x"); uart::putx(stval);
    uart::puts("\r\n");

    let name = match (is_interrupt, code) {
        (false,  1) => "instruction access fault",
        (false,  2) => "illegal instruction",
        (false,  5) => "load access fault",
        (false,  7) => "store access fault",
        (false,  8) => "ecall (syscall)",
        (false, 12) => "instruction page fault",
        (false, 13) => "load page fault",
        (false, 15) => "store page fault",
        (true,   1) => "supervisor software interrupt",
        (true,   9) => "supervisor external interrupt",
        _           => "unknown",
    };
    uart::puts("       "); uart::puts(name); uart::puts("\r\n");
    loop {}
}

// ── RISC-V user-mode trap handler ─────────────────────────────────────────────

#[cfg(target_arch = "riscv64")]
const SUM: u64 = 1 << 18;

#[cfg(target_arch = "riscv64")]
#[no_mangle]
pub extern "C" fn _trap_handler_user(
    tf:    *mut crate::process::TrapFrame,
    cause: u64,
    sepc:  u64,
    stval: u64,
) {
    let is_interrupt = cause >> 63 != 0;
    let code = cause & 0x7fff_ffff_ffff_ffff;

    if is_interrupt && code == 5 {
        let next = crate::arch::read_mtime() + crate::arch::TICK_INTERVAL;
        crate::arch::sbi_set_timer(next);
        crate::process::yield_now();
        return;
    }

    if !is_interrupt && code == 8 {
        let tf = unsafe { &mut *tf };
        match tf.a7 {
            0 => { uart::putc(tf.a0 as u8); }

            1 => {
                crate::process::kill_current();
                crate::process::yield_now();
                loop {}
            }

            2 => { crate::process::yield_now(); }

            3 => {
                let fd  = tf.a0;
                let va  = tf.a1;
                let len = tf.a2 as usize;
                let mut written = 0usize;
                if fd == 1 || fd == 2 {
                    unsafe {
                        core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                        for i in 0..len {
                            let b = *((va + i as u64) as *const u8);
                            uart::putc(b);
                            crate::kbd::stdout_push(b);
                            written += 1;
                        }
                        core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                    }
                }
                tf.a0 = written as u64;
            }

            4 => {
                let fd  = tf.a0;
                let va  = tf.a1;
                let max = tf.a2 as usize;
                if fd == 0 && max > 0 {
                    loop {
                        if crate::kbd::available() { break; }
                        crate::process::block_current();
                        crate::process::yield_now();
                    }
                    let mut n = 0usize;
                    unsafe {
                        core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                        while n < max {
                            if let Some(b) = crate::kbd::pop() {
                                *((va + n as u64) as *mut u8) = b;
                                n += 1;
                            } else {
                                break;
                            }
                        }
                        core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                    }
                    tf.a0 = n as u64;
                } else {
                    tf.a0 = 0;
                }
            }

            _ => { tf.a0 = u64::MAX; }
        }
        tf.sepc += 4;
        return;
    }

    uart::puts("\r\n[USER TRAP] ");
    if is_interrupt { uart::puts("interrupt "); } else { uart::puts("exception "); }
    uart::puts("cause="); uart::putu(code);
    uart::puts(" sepc=0x"); uart::putx(sepc);
    uart::puts(" stval=0x"); uart::putx(stval); uart::puts("\r\n");
    loop {}
}