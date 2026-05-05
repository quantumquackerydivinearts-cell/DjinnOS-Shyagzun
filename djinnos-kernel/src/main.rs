#![no_std]
#![no_main]
#![allow(dead_code)]
#![allow(static_mut_refs)]
mod byte_table;
mod font;
mod process;
mod uart;
mod virtio;

use core::panic::PanicInfo;

core::arch::global_asm!(include_str!("boot.s"));

// ── Entry point ───────────────────────────────────────────────────────────────

#[no_mangle]
pub extern "C" fn kernel_main() -> ! {
    uart::puts("\r\nDjinnOS kernel\r\n");

    // Register the kernel itself as the first YeGaoh complex (Ta, byte 9).
    process::init();
    uart::puts("process subsystem: online\r\n");

    // Byte table diagnostic
    uart::puts("byte table entries: ");
    uart::putu(byte_table::BYTE_TABLE.len() as u64);
    uart::puts("  candidates: ");
    uart::putu(byte_table::symbol_count() as u64);
    uart::puts("\r\n");

    // VirtIO GPU
    uart::puts("GPU: scanning VirtIO bus...\r\n");
    match virtio::find_gpu() {
        None => {
            uart::puts("GPU: not found (pass -device virtio-gpu-device to QEMU)\r\n");
            uart::puts("continuing without display\r\n");
            loop {}
        }
        Some(base) => {
            uart::puts("GPU: found at 0x");
            uart::putx(base);
            uart::puts("\r\n");

            match virtio::GpuDriver::init(base) {
                None => {
                    uart::puts("GPU: init failed\r\n");
                    loop {}
                }
                Some(mut gpu) => {
                    uart::puts("GPU: ");
                    uart::putu(gpu.width  as u64);
                    uart::puts("x");
                    uart::putu(gpu.height as u64);
                    uart::puts(" online\r\n");

                    // Advance cannabis eigenstate — kernel is now consciously
                    // acting on display (Soa: conscious persistence, byte 193)
                    process::advance_cannabis(193);

                    // Draw DjinnOS splash: deep indigo background + Ko-gold rule
                    splash(&mut gpu);

                    uart::puts("display: splash rendered\r\n");
                    uart::puts("\r\nbyte table online. coordinate space established.\r\n");

                    // Spawn the first user process at coordinate 19 (Ko — Experience).
                    process::spawn(19, first_process, 0);

                    // Yield into the scheduler — kernel becomes idle
                    process::yield_now();

                    loop {}
                }
            }
        }
    }
}

// ── Splash / desktop bootstrap ────────────────────────────────────────────────
//
// Colours from the byte table:
//   Void background : byte  6 — Void         #080608
//   Ko-gold         : byte 19 — Ko           #c8964b  (warm amber)
//   Desktop floor   : byte  9 — Ta           #0e0c10  (barely lighter than void)

// BGR components for Ko-gold (#c8964b)
const KO_B: u8 = 0x4b;
const KO_G: u8 = 0x96;
const KO_R: u8 = 0xc8;

fn splash(gpu: &mut virtio::GpuDriver) {
    let w = gpu.width;
    let h = gpu.height;

    // ── Void background ───────────────────────────────────────────────────────
    gpu.fill(0x08, 0x06, 0x08);

    // ── Ko-gold rule at 55% height ────────────────────────────────────────────
    let rule_y   = h * 55 / 100;
    let rule_x0  = w / 10;
    let rule_x1  = w * 9 / 10;
    for x in rule_x0..rule_x1 {
        gpu.set_pixel(x, rule_y,     KO_B, KO_G, KO_R);
        gpu.set_pixel(x, rule_y + 1, KO_B / 2, KO_G / 2, KO_R / 2);
    }

    // ── "DjinnOS" centred above the rule — 4× scale ───────────────────────────
    let text      = "DjinnOS";
    let char_w    = font::GLYPH_W * 4;
    let char_h    = font::GLYPH_H * 4;
    let text_w    = text.len() as u32 * char_w;
    let text_x    = (w - text_w) / 2;
    let text_y    = rule_y - char_h - 24;   // 24px gap above rule

    font::draw_str(gpu, text_x, text_y, text, 4, KO_R, KO_G, KO_B);

    // ── Desktop floor below the rule ─────────────────────────────────────────
    // Slightly lighter void — the empty desktop space
    for py in (rule_y + 4)..h {
        for px in 0..w {
            gpu.set_pixel(px, py, 0x10, 0x0c, 0x10);
        }
    }

    gpu.flush();
}

// ── First user process (Ko — Experience / intuition, byte 19) ─────────────────

fn first_process(_arg: u64) -> ! {
    uart::puts("[Ko process]: running at coordinate 19\r\n");
    // This process will become the shell once input drivers exist.
    loop {
        process::yield_now();
    }
}

// ── Panic handler ─────────────────────────────────────────────────────────────

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    uart::puts("\r\n[PANIC]\r\n");
    loop {}
}