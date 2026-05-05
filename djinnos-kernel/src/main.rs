#![no_std]
#![no_main]
#![allow(dead_code)]
#![allow(static_mut_refs)]

mod byte_table;
mod font;
mod process;
mod shell;
mod uart;
mod virtio;

use core::panic::PanicInfo;

core::arch::global_asm!(include_str!("boot.s"));

#[no_mangle]
pub extern "C" fn kernel_main() -> ! {
    uart::puts("\r\nDjinnOS kernel\r\n");

    process::init();
    uart::puts("process subsystem: online\r\n");

    uart::puts("byte table entries: ");
    uart::putu(byte_table::BYTE_TABLE.len() as u64);
    uart::puts("  candidates: ");
    uart::putu(byte_table::symbol_count() as u64);
    uart::puts("\r\n");

    // ── GPU ───────────────────────────────────────────────────────────────────
    uart::puts("GPU: scanning...\r\n");
    let gpu_base = virtio::find_gpu().expect("GPU not found");
    uart::puts("GPU: found\r\n");
    let mut gpu = virtio::GpuDriver::init(gpu_base).expect("GPU init failed");
    uart::puts("GPU: online ");
    uart::putu(gpu.width as u64); uart::puts("x");
    uart::putu(gpu.height as u64); uart::puts("\r\n");

    process::advance_cannabis(193);  // Soa — conscious persistence

    // ── Splash ────────────────────────────────────────────────────────────────
    let rule_y = gpu.height * 55 / 100;
    splash(&mut gpu, rule_y);

    // ── Keyboard ─────────────────────────────────────────────────────────────
    uart::puts("KBD: scanning...\r\n");
    let mut kbd = virtio::find_input()
        .and_then(|base| virtio::InputDriver::init(base));
    match kbd {
        Some(_) => uart::puts("KBD: online\r\n"),
        None    => uart::puts("KBD: not found (add -device virtio-keyboard-device)\r\n"),
    }

    // ── Shell ─────────────────────────────────────────────────────────────────
    let mut sh = shell::Shell::new(rule_y);
    sh.boot_banner();
    sh.render(&gpu);
    gpu.flush();

    process::spawn(19, ko_idle, 0);

    // ── Main event loop ───────────────────────────────────────────────────────
    loop {
        let mut got_input = false;
        if let Some(ref mut k) = kbd {
            while let Some(key) = k.poll() {
                sh.handle_key(key);
                got_input = true;
            }
        }
        if got_input || sh.needs_flush() {
            sh.render(&gpu);
            gpu.flush();
        }
        process::yield_now();
    }
}

// ── Splash ────────────────────────────────────────────────────────────────────

const KO_B: u8 = 0x4b; const KO_G: u8 = 0x96; const KO_R: u8 = 0xc8;

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