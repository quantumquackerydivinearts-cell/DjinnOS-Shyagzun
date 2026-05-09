#![no_std]
#![no_main]

mod syscall;

use kobra_core::ast::Pool;
use kobra_core::eval::{eval, Output};
use kobra_core::parser::{parse, ParseResult};

use core::sync::atomic::{AtomicUsize, Ordering};

// ── Bump allocator ────────────────────────────────────────────────────────────
// 256 KiB heap for any incidental alloc; the AST uses its own pool so this
// mostly handles libcore internals.

#[cfg(not(test))]
mod alloc_impl {
    use core::alloc::{GlobalAlloc, Layout};
    use core::sync::atomic::{AtomicUsize, Ordering};

    static HEAP: [u8; 262144] = [0u8; 262144];
    static PTR:  AtomicUsize  = AtomicUsize::new(0);

    struct Bump;
    unsafe impl GlobalAlloc for Bump {
        unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
            loop {
                let cur  = PTR.load(Ordering::Relaxed);
                let base = HEAP.as_ptr() as usize;
                let aligned = (base + cur + layout.align() - 1) & !(layout.align() - 1);
                let off  = aligned - base;
                let next = off + layout.size();
                if next > HEAP.len() { return core::ptr::null_mut(); }
                if PTR.compare_exchange(cur, next, Ordering::SeqCst, Ordering::Relaxed).is_ok() {
                    return aligned as *mut u8;
                }
            }
        }
        unsafe fn dealloc(&self, _: *mut u8, _: Layout) {}
    }

    #[global_allocator]
    static A: Bump = Bump;
}

// ── SBI output bridge ─────────────────────────────────────────────────────────

struct SyscallOutput;

impl Output for SyscallOutput {
    fn write(&mut self, s: &[u8]) {
        syscall::write(1, s);
    }
}

// ── Entry ─────────────────────────────────────────────────────────────────────

#[no_mangle]
#[link_section = ".text.start"]
pub extern "C" fn _start() -> ! {
    run();
    syscall::exit(0);
}

fn run() {
    syscall::println(b"");
    syscall::println(b"Kobra v0.1  --  native DjinnOS");
    syscall::println(b"coordinate: 19 (Ko -- experience/intuition)");
    syscall::println(b"37 tongues  1358 symbols");
    syscall::println(b"Type a Kobra expression. 'quit' to exit.");
    syscall::println(b"");

    let mut pool = Pool::empty();
    let mut line = [0u8; 256];

    loop {
        syscall::print(b"ko> ");

        let n = read_line(&mut line);
        if n == 0 { continue; }

        let input = &line[..n];

        if input == b"quit" || input == b"exit" {
            syscall::println(b"bye");
            break;
        }

        pool.reset();
        match parse(input, &mut pool) {
            ParseResult::Ok(root) => {
                syscall::print(b"  ");
                let mut out = SyscallOutput;
                eval(&pool, root, &mut out);
            }
            ParseResult::Empty => {}
            ParseResult::Err => {
                // Operative-ambiguity model: echo unresolved input as live object
                syscall::print(b"  echo: ");
                syscall::println(input);
            }
        }
    }
}

fn read_line(buf: &mut [u8]) -> usize {
    let mut n = 0usize;
    loop {
        let mut ch = [0u8; 1];
        syscall::read(0, &mut ch);
        let b = ch[0];
        if b == b'\n' || b == b'\r' {
            syscall::println(b"");
            break;
        } else if (b == 0x7F || b == 0x08) && n > 0 {
            n -= 1;
            syscall::print(b"\x08 \x08");
        } else if b >= 0x20 && n < buf.len() - 1 {
            buf[n] = b;
            n += 1;
            syscall::write(1, &buf[n-1..n]);
        }
    }
    n
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    syscall::println(b"[PANIC]");
    loop {}
}