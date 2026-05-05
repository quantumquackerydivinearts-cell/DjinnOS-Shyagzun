#![no_std]
#![no_main]
#![allow(dead_code)]
#![allow(static_mut_refs)]
mod byte_table;
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

// ── Splash screen ─────────────────────────────────────────────────────────────
//
// DjinnOS identity colours derived from the byte table:
//   Background: deep void (byte 6 — Wu, void, #080608)
//   Rule line:  Ko-gold  (byte 19 — Ko, experience, warm amber)

fn splash(gpu: &mut virtio::GpuDriver) {
    let w = gpu.width;
    let h = gpu.height;

    // Void background
    gpu.fill(0x08, 0x06, 0x08);

    // Ko-gold horizontal rule at 60% height
    let rule_y = h * 6 / 10;
    for x in (w / 8)..(w * 7 / 8) {
        gpu.set_pixel(x, rule_y,     0x4b, 0x96, 0xc8);  // Ko gold (BGR)
        gpu.set_pixel(x, rule_y + 1, 0x2a, 0x5a, 0x8b);  // dim echo
    }

    // Flush everything to the physical display
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