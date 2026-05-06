// Trap / interrupt handler installation.
//
// RISC-V: sets stvec, handles ecalls, supervisor exceptions, timer.
// x86_64: loads IDT via arch::set_trap_vector (which calls arch::init_idt).
//
// ── Shygazun syscall ABI ──────────────────────────────────────────────────────
//
// Register a7 holds a Shygazun byte address.  The operation IS the meaning of
// that address in the byte table.  On every ecall dispatch the eigenstate
// counter for the corresponding Tongue is advanced automatically.
//
// Primitive set (see byte_table::SYS_* constants for the full table):
//
//   0  (Ty)  spawn ELF process      a0=code_va a1=len → a0=pid
//   1  (Zu)  exit                   a0=code → !
//   2  (Ly)  read / feel            a0=fd a1=buf a2=len → a0=n
//   4  (Fy)  yield                  → void
//   8  (Ti)  get pid                → a0=pid
//   9  (Ta)  clone / fork           a0=flags → a0=child_pid
//  16  (Zo)  sleep ticks            a0=ticks → void
//  19  (Ko)  wait event             a0=mask → a0=event
//  82  (Kael) heap alloc            a0=len → a0=va
//  83  (Ro)  IPC open               a0=id → a0=handle
//  89  (Nz)  IPC send               a0=handle a1=data → void
// 142  (Si)  monotonic ticks        → a0=ticks
// 156  (Sa)  volume info            → a0=block_count
// 157  (Sao) open file              a0=name_va a1=name_len → a0=fd
// 159  (Seth) read directory        a0=dir_va a1=dir_len a2=out_va a3=out_len → a0=n
// 163  (Myk) send packet            a0=dst a1=buf a2=len → a0=ok
// 166  (Mek) emit event             a0=event_id a1=data → void
// 193  (Soa) write / persist        a0=fd a1=buf a2=len → a0=n
// 203  (Sei) sbrk / occupy space    a0=incr → a0=new_break
// 213  (Suy) sleep ticks (time)     a0=ticks → void
// 1138 (Koi) create exchange chan   → a0=chan_id
// 1182 (Rope) bind resource         a0=token → a0=handle
// 1226 (Hook) register IRQ handler  a0=irq a1=fn_va → a0=ok
// 1270 (Fang) constitutive contract a0=class a1=rate → void
// 1314 (Circle) broadcast           a0=event_id a1=data → void

#[cfg(target_arch = "riscv64")]
use crate::uart;

use crate::byte_table;
use crate::eigenstate;
use crate::ipc;
#[cfg(target_arch = "riscv64")]
use crate::vfs;
#[cfg(target_arch = "riscv64")]
use crate::net;

#[cfg(target_arch = "riscv64")]
unsafe extern "C" {
    fn _trap_entry();
}

pub fn init() {
    #[cfg(target_arch = "riscv64")]
    crate::arch::set_trap_vector(_trap_entry as *const () as usize as u64);

    #[cfg(target_arch = "x86_64")]
    crate::arch::set_trap_vector(0);
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
    loop {}
}

// ── RISC-V user-mode ecall dispatcher ────────────────────────────────────────

#[cfg(target_arch = "riscv64")]
const SUM: u64 = 1 << 18; // sstatus.SUM — allow S-mode to access U-mode pages

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

    // ── Timer interrupt — preempt ─────────────────────────────────────────────
    if is_interrupt && code == 5 {
        let next = crate::arch::read_mtime() + crate::arch::TICK_INTERVAL;
        crate::arch::sbi_set_timer(next);
        crate::process::yield_now();
        return;
    }

    // ── ecall (environment call from U-mode) ──────────────────────────────────
    if !is_interrupt && code == 8 {
        let tf = unsafe { &mut *tf };
        let sys = tf.a7 as u32;   // Shygazun byte address

        // Advance the eigenstate for whatever tongue owns this address.
        eigenstate::advance(byte_table::tongue_for_addr(sys));

        dispatch_ecall(tf, sys);
        tf.sepc += 4;            // advance past the ecall instruction
        return;
    }

    // ── Unhandled trap ────────────────────────────────────────────────────────
    uart::puts("\r\n[USER TRAP] ");
    if is_interrupt { uart::puts("interrupt "); } else { uart::puts("exception "); }
    uart::puts("cause="); uart::putu(code);
    uart::puts(" sepc=0x"); uart::putx(sepc);
    uart::puts(" stval=0x"); uart::putx(stval); uart::puts("\r\n");
    loop {}
}

// ── Shygazun ecall dispatch ───────────────────────────────────────────────────

#[cfg(target_arch = "riscv64")]
fn dispatch_ecall(tf: &mut crate::process::TrapFrame, sys: u32) {
    use byte_table::*;

    match sys {
        // ── Lotus — elemental primitives ─────────────────────────────────────

        SYS_TY => {
            // Spawn: load ELF from user address.
            // a0=code_va  a1=len  a2=coordinate (0 → default 19/Ko) → a0=pid
            let code_va    = tf.a0 as usize;
            let len        = tf.a1 as usize;
            let coordinate = if tf.a2 != 0 { tf.a2 as u32 } else { 19 };
            unsafe { core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack)); }
            let slice = unsafe { core::slice::from_raw_parts(code_va as *const u8, len) };
            tf.a0 = crate::process::spawn_elf(coordinate, slice)
                .map(|pid| pid.0 as u64)
                .unwrap_or(u64::MAX);
            unsafe { core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack)); }
        }

        SYS_ZU => {
            // Exit: terminate current process
            crate::process::kill_current();
            crate::process::yield_now();
            loop {}
        }

        SYS_LY => {
            // Read / feel: receive bytes from fd.
            // fd 0 = stdin (byte stream).  fd >= IPC_FD_BASE = channel (u64 words).
            let fd  = tf.a0;
            let va  = tf.a1;
            let max = tf.a2 as usize;

            if ipc::is_ipc_fd(fd) {
                // Channel receive — block until data is available.
                let id = ipc::chan_id(fd);
                loop {
                    if ipc::channel_ready(id) { break; }
                    let slot = crate::process::current_idx();
                    ipc::block_on_channel(slot, id);
                    crate::process::block_current();
                    crate::process::yield_now();
                }
                let word = ipc::recv(id).unwrap_or(0);
                if max >= 8 {
                    unsafe {
                        core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                        (va as *mut u64).write_unaligned(word);
                        core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                    }
                    tf.a0 = 8;
                } else {
                    tf.a0 = 0;
                }
            } else if net::is_net_fd(fd) {
                // TCP recv — non-blocking, returns 0 if no data yet.
                let mut local = [0u8; 4096];
                let want = max.min(local.len());
                let n = net::tcp_recv(fd, &mut local[..want]);
                if n > 0 {
                    unsafe {
                        core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                        core::ptr::copy_nonoverlapping(local.as_ptr(), va as *mut u8, n);
                        core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                    }
                }
                tf.a0 = n as u64;
            } else if vfs::is_file_fd(fd) {
                // File read — sequential, advances offset.
                let mut local_buf = [0u8; 512];
                let want = max.min(local_buf.len());
                let n = vfs::read(fd, &mut local_buf[..want]);
                if n > 0 && max > 0 {
                    unsafe {
                        core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                        core::ptr::copy_nonoverlapping(local_buf.as_ptr(), va as *mut u8, n);
                        core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                    }
                }
                tf.a0 = n as u64;
            } else if fd == 0 && max > 0 {
                // stdin — block until keyboard input is available.
                loop {
                    if crate::kbd::available() { break; }
                    crate::process::block_current();
                    crate::process::yield_now();
                }
                let mut n = 0usize;
                unsafe {
                    core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                    while n < max {
                        match crate::kbd::pop() {
                            Some(b) => { *((va + n as u64) as *mut u8) = b; n += 1; }
                            None    => break,
                        }
                    }
                    core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                }
                tf.a0 = n as u64;
            } else {
                tf.a0 = 0;
            }
        }

        SYS_FY => {
            // Yield — cooperative hand-off
            crate::process::yield_now();
        }

        SYS_TI => {
            // Here / get pid
            tf.a0 = crate::process::current_id().0 as u64;
        }

        SYS_TA => {
            // Active presence / clone — not yet implemented
            tf.a0 = u64::MAX;
        }

        SYS_ZO | SYS_SUY => {
            // Absence / sleep for ticks
            let ticks = tf.a0;
            let deadline = crate::arch::read_mtime() + ticks * crate::arch::TICK_INTERVAL;
            while crate::arch::read_mtime() < deadline {
                crate::process::yield_now();
            }
        }

        SYS_KO => {
            // Experience / wait for event.
            // a0 = event_id (0 = any) → a0 = payload delivered by Circle.
            let event_id = tf.a0;
            let slot = crate::process::current_idx();
            if event_id != 0 {
                ipc::wait_for_event(slot, event_id);
                crate::process::block_current();
                crate::process::yield_now();
                // Resumed by Circle broadcast — collect payload.
                tf.a0 = ipc::take_event_result(slot);
            } else {
                // event_id 0 → cooperative yield.
                crate::process::yield_now();
                tf.a0 = 0;
            }
        }

        // ── Daisy — structural / IPC ──────────────────────────────────────────

        SYS_KAEL => {
            // Cluster alloc — heap allocation. a0=len → a0=ptr (0 on failure)
            let len = (tf.a0 as usize).max(1);
            extern crate alloc;
            use alloc::alloc::{alloc, Layout};
            let layout = match Layout::from_size_align(len, 16) {
                Ok(l)  => l,
                Err(_) => { tf.a0 = 0; return; }
            };
            tf.a0 = unsafe { alloc(layout) } as u64;
        }

        SYS_RO => {
            // Ro — gate/receptor: open IPC channel OR start TCP listen.
            // a0 = 0..15 → IPC channel open (original semantics).
            // a0 >= 1024 → TCP listen on that port number → a0 = net fd.
            let a0 = tf.a0;
            if a0 >= 1024 {
                tf.a0 = net::tcp_socket(a0 as u16);
            } else {
                tf.a0 = ipc::open_channel(a0).unwrap_or(u64::MAX);
            }
        }

        SYS_NZ => {
            // Send on channel: a0 = fd, a1 = word → a0 = 1 (ok) / 0 (fail / full).
            let fd = tf.a0;
            if ipc::is_ipc_fd(fd) {
                tf.a0 = if ipc::send(ipc::chan_id(fd), tf.a1) { 1 } else { 0 };
            } else {
                tf.a0 = 0;
            }
        }

        // ── Aster — time / space ─────────────────────────────────────────────

        SYS_SI => {
            tf.a0 = crate::arch::read_mtime();
        }

        SYS_EP | SYS_ENNO => {
            // Space assign / delete — stub
            tf.a0 = 0;
        }

        // ── Grapevine — storage / messaging ──────────────────────────────────

        SYS_SA => {
            // Sa — feast table / root volume: return block count.
            tf.a0 = vfs::block_count();
        }

        SYS_SAO => {
            // Sao — open a file by name.
            // a0 = name VA (user space), a1 = name length → a0 = fd or u64::MAX.
            let name_va  = tf.a0;
            let name_len = (tf.a1 as usize).min(64);
            let mut name_buf = [0u8; 64];
            unsafe {
                core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                core::ptr::copy_nonoverlapping(name_va as *const u8, name_buf.as_mut_ptr(), name_len);
                core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
            }
            tf.a0 = vfs::open(&name_buf[..name_len]);
        }

        SYS_SYR => {
            // Syr — volatile buffer / anonymous channel.
            tf.a0 = ipc::create_channel()
                .map(|id| id + ipc::IPC_FD_BASE)
                .unwrap_or(u64::MAX);
        }

        SYS_SETH => {
            // Seth — directory listing.
            // a0=dir_va (ignored, root only), a1=dir_len, a2=out_va, a3=out_len → a0=bytes written.
            let out_va  = tf.a2;
            let out_len = (tf.a3 as usize).min(2048);
            let mut local = [0u8; 2048];
            let n = vfs::readdir(&mut local[..out_len]);
            if n > 0 {
                unsafe {
                    core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                    core::ptr::copy_nonoverlapping(local.as_ptr(), out_va as *mut u8, n);
                    core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                }
            }
            tf.a0 = n as u64;
        }

        SYS_MYK => {
            // Send packet to process: a0=dst_pid, a1=buf_va, a2=len → a0=ok.
            // Route through a channel if dst_pid has one registered; stub for now.
            tf.a0 = 0;
        }

        SYS_MEK => {
            // Mek — call/emit: if a0 is a net fd, close it; otherwise broadcast event.
            // a0 = fd (net) → close socket.
            // a0 = event_id (other) a1 = data → broadcast.
            if net::is_net_fd(tf.a0) {
                net::tcp_close(tf.a0);
            } else {
                ipc::broadcast(tf.a0, tf.a1);
            }
        }

        // ── Cannabis — mind-space-time (the core output/input operations) ─────

        SYS_SOA => {
            // Conscious persistence: write bytes to fd.
            // fd 1/2 → UART.  fd >= IPC_FD_BASE → channel (pack bytes into u64 words).
            // a0=fd, a1=buf_va, a2=len → a0=written
            let fd  = tf.a0;
            let va  = tf.a1;
            let len = tf.a2 as usize;

            if ipc::is_ipc_fd(fd) {
                // Pack bytes into u64 words and send to the channel.
                let id = ipc::chan_id(fd);
                let mut written = 0usize;
                unsafe {
                    core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                    let mut i = 0usize;
                    while i < len {
                        // Fill a u64 with up to 8 bytes (little-endian, zero-padded).
                        let mut word = 0u64;
                        let chunk = (len - i).min(8);
                        for j in 0..chunk {
                            let b = *((va + (i + j) as u64) as *const u8);
                            word |= (b as u64) << (j * 8);
                        }
                        if ipc::send(id, word) {
                            written += chunk;
                        } else {
                            break; // channel full
                        }
                        i += chunk;
                    }
                    core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                }
                tf.a0 = written as u64;
                // Advance cannabis eigenstate on conscious output.
                crate::process::advance_cannabis(193);
            } else if net::is_net_fd(fd) {
                // TCP send — `len` is tf.a2 in SYS_SOA context.
                let n = if len > 0 {
                    extern crate alloc;
                    let cap = len.min(65536);
                    let mut local = alloc::vec![0u8; cap];
                    unsafe {
                        core::arch::asm!("csrs sstatus, {v}", v = in(reg) SUM, options(nostack));
                        core::ptr::copy_nonoverlapping(va as *const u8, local.as_mut_ptr(), cap);
                        core::arch::asm!("csrc sstatus, {v}", v = in(reg) SUM, options(nostack));
                    }
                    net::tcp_send(fd, &local[..cap])
                } else { 0 };
                tf.a0 = n as u64;
            } else {
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
                    crate::process::advance_cannabis(193);
                }
                tf.a0 = written as u64;
            }
        }

        SYS_SEI => {
            // Occupy space / sbrk — stub
            tf.a0 = 0;
        }

        // ── Relational tier ───────────────────────────────────────────────────

        SYS_KOI => {
            // Koi — balanced-exchange: create a TCP connection (the ultimate Koi).
            // a0 = packed IPv4 (big-endian u32), a1 = port → a0 = fd or u64::MAX.
            // If a0 == 0: create a plain IPC channel (original Koi semantics).
            if tf.a0 == 0 {
                tf.a0 = ipc::create_channel().unwrap_or(u64::MAX);
            } else {
                let ip_packed = tf.a0 as u32;
                let ip = [
                    (ip_packed >> 24) as u8,
                    (ip_packed >> 16) as u8,
                    (ip_packed >>  8) as u8,
                    ip_packed         as u8,
                ];
                let port = tf.a1 as u16;
                let fd = net::tcp_socket(0);
                if fd != u64::MAX {
                    tf.a0 = if net::tcp_connect(fd, ip, port) != 0 { fd } else { u64::MAX };
                } else {
                    tf.a0 = u64::MAX;
                }
            }
        }

        SYS_ROPE => {
            // Rope — bind ownership of resource token a0 to current process.
            // a0 = token → a0 = token (as handle), or u64::MAX if table full.
            tf.a0 = ipc::bind_resource(tf.a0);
        }

        SYS_HOOK => {
            // Hook — register a user-mode IRQ handler.
            // a0 = IRQ number, a1 = handler VA → a0 = 1 (ok) / 0 (fail).
            let irq    = tf.a0 as u8;
            let fn_va  = tf.a1;
            tf.a0 = if ipc::register_hook(irq, fn_va) { 1 } else { 0 };
        }

        SYS_FANG => {
            // Fang — declare constitutive resource contract.
            // a0 = resource class, a1 = rate → void.
            ipc::declare_contract(tf.a0, tf.a1);
        }

        SYS_CIRCLE => {
            // Circle — broadcast event to all Ko-waiting processes.
            // a0 = event_id, a1 = payload → a0 = number of processes woken.
            tf.a0 = ipc::broadcast(tf.a0, tf.a1) as u64;
        }

        // ── Eigenstate query — read the invocation counter for a tongue ───────
        // a7=0xFFFF0000 | tongue_number → a0 = counter
        addr if addr >> 16 == 0xFFFF => {
            let tongue = (addr & 0xFF) as u8;
            tf.a0 = eigenstate::read(tongue);
        }

        // ── Unknown address — return sentinel, still advances unknown slot ─────
        _ => {
            tf.a0 = u64::MAX;
        }
    }
}

// ── Stubs to satisfy existing call sites ─────────────────────────────────────
// The old API (sys=0 putchar, sys=3 write, sys=4 read) is intentionally gone.
// Any user programs using those numbers will receive u64::MAX from the default
// arm and will need to be recompiled against the Shygazun ABI.
