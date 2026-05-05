#![no_std]
#![no_main]
#![allow(dead_code)]
#![allow(static_mut_refs)]

extern crate alloc;

mod arch;
mod byte_table;
mod kbd;
mod mm;
mod process;
mod trap;
mod uart;

#[cfg(target_arch = "riscv64")]
mod elf;
#[cfg(target_arch = "riscv64")]
mod font;
#[cfg(target_arch = "riscv64")]
mod fs;
#[cfg(target_arch = "riscv64")]
mod shell;
#[cfg(target_arch = "riscv64")]
mod virtio;

use core::panic::PanicInfo;

#[cfg(target_arch = "riscv64")]
core::arch::global_asm!(include_str!("boot.s"));

#[cfg(target_arch = "x86_64")]
core::arch::global_asm!(include_str!("boot_x86.s"));

// ── RISC-V kernel_main ────────────────────────────────────────────────────────

#[cfg(target_arch = "riscv64")]
#[no_mangle]
pub extern "C" fn kernel_main() -> ! {
    uart::puts("\r\nDjinnOS kernel\r\n");

    trap::init();
    uart::puts("trap: online\r\n");

    mm::init();
    uart::puts("heap: online  ");
    let (free, _) = mm::ALLOCATOR.stats();
    uart::putu(free as u64 / 1024);
    uart::puts(" KiB free\r\n");

    mm::setup_vm();
    uart::puts("vm:   Sv39 online");
    if arch::paging_active() {
        uart::puts("  [active]\r\n");
    } else {
        uart::puts("  [FAILED]\r\n");
    }

    {
        extern "C" { static _stack_top: u8; }
        let pa_start = unsafe { core::ptr::addr_of!(_stack_top) as u64 };
        mm::page_alloc_init(pa_start, 0x8600_0000);
    }
    uart::puts("pmem: page allocator online\r\n");

    process::init();
    uart::puts("process subsystem: online\r\n");

    arch::sbi_set_timer(arch::read_mtime() + arch::TICK_INTERVAL);
    arch::enable_timer();
    uart::puts("timer: online  10ms tick\r\n");

    uart::puts("byte table entries: ");
    uart::putu(byte_table::BYTE_TABLE.len() as u64);
    uart::puts("  candidates: ");
    uart::putu(byte_table::symbol_count() as u64);
    uart::puts("\r\n");

    uart::puts("GPU: scanning...\r\n");
    let gpu_base = virtio::find_gpu().expect("GPU not found");
    uart::puts("GPU: found\r\n");
    let mut gpu = virtio::GpuDriver::init(gpu_base).expect("GPU init failed");
    uart::puts("GPU: online ");
    uart::putu(gpu.width as u64); uart::puts("x");
    uart::putu(gpu.height as u64); uart::puts("\r\n");

    process::advance_cannabis(193);

    let rule_y = gpu.height * 55 / 100;
    splash(&mut gpu, rule_y);

    uart::puts("KBD: scanning...\r\n");
    let mut kbd = virtio::find_input()
        .and_then(|base| virtio::InputDriver::init(base));
    match kbd {
        Some(_) => uart::puts("KBD: online\r\n"),
        None    => uart::puts("KBD: not found\r\n"),
    }

    uart::puts("BLK: scanning...\r\n");
    let mut blk = virtio::find_block()
        .and_then(|base| virtio::BlockDriver::init(base));
    let vol = match blk.as_mut() {
        None => { uart::puts("BLK: not found\r\n"); None }
        Some(b) => {
            uart::puts("BLK: online  sectors=");
            uart::putu(b.capacity);
            uart::puts("\r\n");
            match fs::SaVolume::mount(b) {
                None    => { uart::puts("FS: no Sa volume\r\n"); None }
                Some(v) => {
                    uart::puts("FS: Sa volume mounted  files=");
                    uart::putu(v.count as u64);
                    uart::puts("\r\n");
                    Some(v)
                }
            }
        }
    };

    let mut sh = shell::Shell::new(rule_y);
    sh.boot_banner();
    sh.render(&gpu);
    gpu.flush();

    process::spawn(19, ko_idle, 0);

    let mut frame: u64 = 0;
    loop {
        if let Some(ref mut k) = kbd {
            while let Some(key) = k.poll() {
                use virtio::input::Key;
                let consumed = match key {
                    Key::Char(b)   => kbd::push(b),
                    Key::Enter     => kbd::push(b'\n'),
                    Key::Backspace => kbd::push(0x7F),
                };
                if !consumed {
                    sh.handle_key(key, blk.as_mut(), vol.as_ref());
                }
            }
        }

        {
            let mut line = [0u8; 80];
            let mut n = 0usize;
            while let Some(b) = kbd::stdout_pop() {
                if b == b'\n' || b == b'\r' {
                    if n > 0 { sh.push_user_line(&line[..n]); n = 0; }
                } else if b >= 0x20 && n < 79 {
                    line[n] = b; n += 1;
                }
            }
            if n > 0 { sh.push_user_line(&line[..n]); }
        }

        sh.set_frame(frame);
        sh.render(&gpu);
        gpu.flush();
        frame = frame.wrapping_add(1);

        process::yield_now();
    }
}

// ── x86_64 kernel_main ────────────────────────────────────────────────────────

#[cfg(target_arch = "x86_64")]
#[no_mangle]
pub extern "C" fn kernel_main() -> ! {
    arch::uart_init();
    uart::puts("\r\nDjinnOS kernel [x86_64]\r\n");

    trap::init();
    uart::puts("trap: online\r\n");

    mm::init();
    let (free, _) = mm::ALLOCATOR.stats();
    uart::puts("heap: online  ");
    uart::putu(free as u64 / 1024);
    uart::puts(" KiB free\r\n");

    uart::puts("vm:   2MB identity pages [active]\r\n");

    // No page allocator needed for Phase 1 (no user ELFs).

    process::init();
    uart::puts("process subsystem: online\r\n");

    arch::enable_timer();
    uart::puts("timer: online  10ms tick\r\n");

    uart::puts("byte table entries: ");
    uart::putu(byte_table::BYTE_TABLE.len() as u64);
    uart::puts("  candidates: ");
    uart::putu(byte_table::symbol_count() as u64);
    uart::puts("\r\n");

    process::advance_cannabis(193);

    uart::puts("\r\nKo shell — x86_64 serial\r\n");
    uart::puts("Type 'help' for commands.\r\n> ");

    process::spawn(19, ko_idle, 0);

    // Serial Ko shell: simple line editor on COM1
    let mut line = [0u8; 128];
    let mut len  = 0usize;

    loop {
        if let Some(b) = uart::getc() {
            match b {
                b'\r' | b'\n' => {
                    uart::puts("\r\n");
                    if len > 0 {
                        handle_serial_cmd(&line[..len]);
                        len = 0;
                    }
                    uart::puts("> ");
                }
                0x7F | 0x08 => {
                    if len > 0 {
                        len -= 1;
                        uart::puts("\x08 \x08");
                    }
                }
                b if b >= 0x20 && len < 127 => {
                    line[len] = b;
                    len += 1;
                    uart::putc(b);
                }
                _ => {}
            }
        }
        process::yield_now();
    }
}

#[cfg(target_arch = "x86_64")]
fn handle_serial_cmd(cmd: &[u8]) {
    match cmd {
        b"help" => {
            uart::puts("commands: help  info\r\n");
        }
        b"info" => {
            let (free, blocks) = mm::ALLOCATOR.stats();
            uart::puts("heap free: ");
            uart::putu(free as u64 / 1024);
            uart::puts(" KiB  blocks: ");
            uart::putu(blocks as u64);
            uart::puts("\r\n");
            uart::puts("byte table: ");
            uart::putu(byte_table::BYTE_TABLE.len() as u64);
            uart::puts(" entries\r\n");
        }
        _ => {
            uart::puts("unknown: ");
            for &b in cmd { uart::putc(b); }
            uart::puts("\r\n");
        }
    }
}

// ── Splash (RISC-V only) ─────────────────────────────────────────────────────

#[cfg(target_arch = "riscv64")]
const KO_B: u8 = 0x4b;
#[cfg(target_arch = "riscv64")]
const KO_G: u8 = 0x96;
#[cfg(target_arch = "riscv64")]
const KO_R: u8 = 0xc8;

#[cfg(target_arch = "riscv64")]
fn splash(gpu: &mut virtio::GpuDriver, rule_y: u32) {
    let w = gpu.width;
    let h = gpu.height;

    gpu.fill(0x08, 0x06, 0x08);

    let rule_x0 = w / 10;
    let rule_x1 = w * 9 / 10;
    for x in rule_x0..rule_x1 {
        gpu.set_pixel(x, rule_y,     KO_B, KO_G, KO_R);
        gpu.set_pixel(x, rule_y + 1, KO_B / 2, KO_G / 2, KO_R / 2);
    }

    let text   = "DjinnOS";
    let text_w = text.len() as u32 * font::GLYPH_W * 4;
    let text_x = (w - text_w) / 2;
    let text_y = rule_y - font::GLYPH_H * 4 - 24;
    font::draw_str(gpu, text_x, text_y, text, 4, KO_R, KO_G, KO_B);

    for py in (rule_y + 4)..h {
        for px in 0..w {
            gpu.set_pixel(px, py, 0x10, 0x0c, 0x10);
        }
    }

    gpu.flush();
}

// ── Ko idle process (coordinate 19) ──────────────────────────────────────────

fn ko_idle(_: u64) -> ! {
    loop { process::yield_now(); }
}

#[panic_handler]
fn panic(_: &PanicInfo) -> ! {
    uart::puts("\r\n[PANIC]\r\n");
    loop {}
}