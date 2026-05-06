#![no_std]
#![no_main]
#![allow(dead_code)]
#![allow(static_mut_refs)]

extern crate alloc;

mod arch;
mod byte_table;
mod eigenstate;
mod font;
mod gpu;
mod input;
mod ipc;
mod kbd;
mod mm;
mod process;
mod shell;
mod trap;
mod uart;
mod vfs;

#[cfg(target_arch = "riscv64")]
mod elf;
#[cfg(target_arch = "riscv64")]
mod fs;
#[cfg(target_arch = "riscv64")]
mod net;
#[cfg(target_arch = "riscv64")]
mod virtio;

#[cfg(target_arch = "x86_64")]
mod acpi;
#[cfg(target_arch = "x86_64")]
mod battery;
#[cfg(target_arch = "x86_64")]
mod ec;
#[cfg(target_arch = "x86_64")]
mod fb;
#[cfg(target_arch = "x86_64")]
mod hda;
#[cfg(target_arch = "x86_64")]
mod pci;
#[cfg(target_arch = "x86_64")]
mod ps2;
#[cfg(target_arch = "x86_64")]
mod rtc;

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
    match virtio::find_block().and_then(|base| virtio::BlockDriver::init(base)) {
        None => { uart::puts("BLK: not found\r\n"); }
        Some(mut b) => {
            uart::puts("BLK: online  sectors=");
            uart::putu(b.capacity);
            uart::puts("\r\n");
            match fs::SaVolume::mount(&mut b) {
                None    => { uart::puts("FS: no Sa volume\r\n"); }
                Some(v) => {
                    uart::puts("FS: Sa volume mounted  files=");
                    uart::putu(v.count as u64);
                    uart::puts("\r\n");
                    vfs::mount(b, v);   // consume into static VFS
                }
            }
        }
    }

    uart::puts("NET: scanning...\r\n");
    if net::init() {
        uart::puts("NET: 10.0.2.15/24  HTTP port 80\r\n");
        uart::puts("     host: curl http://localhost:8080/\r\n");
    } else {
        uart::puts("NET: no virtio-net device (add -device virtio-net-device)\r\n");
    }

    let mut sh = shell::Shell::new(rule_y);
    sh.boot_banner();
    sh.render(&gpu as &dyn gpu::GpuSurface);
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
                // Shell no longer needs blk/vol — VFS holds them statically.
                if !consumed {
                    sh.handle_key(key);
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

        net::poll();   // drive smoltcp + HTTP server

        sh.set_frame(frame);
        sh.render(&gpu as &dyn gpu::GpuSurface);
        gpu.flush();
        frame = frame.wrapping_add(1);

        process::yield_now();
    }
}

// ── x86_64 kernel_main ────────────────────────────────────────────────────────
//
// mb2_info: physical address of the multiboot2 info block (0 if booted via
// multiboot1 flat binary in QEMU).  Passed in RDI by boot_x86.s.

#[cfg(target_arch = "x86_64")]
#[no_mangle]
pub extern "C" fn kernel_main(mb2_info: u64) -> ! {
    use crate::gpu::GpuSurface;
    arch::uart_init();
    uart::puts("\r\nDjinnOS kernel [x86_64]\r\n");

    trap::init();
    uart::puts("trap: online\r\n");

    mm::init();
    let (free, _) = mm::ALLOCATOR.stats();
    uart::puts("heap: online  ");
    uart::putu(free as u64 / 1024);
    uart::puts(" KiB free\r\n");

    uart::puts("vm:   4GiB identity map [active]\r\n");

    process::init();
    uart::puts("process subsystem: online\r\n");

    arch::enable_timer();
    uart::puts("timer: online  10ms tick\r\n");

    uart::puts("byte table entries: ");
    uart::putu(byte_table::BYTE_TABLE.len() as u64);
    uart::puts("  candidates: ");
    uart::putu(byte_table::symbol_count() as u64);
    uart::puts("\r\n");

    ps2::init();
    uart::puts("ps2: keyboard init\r\n");

    process::advance_cannabis(193);
    process::spawn(19, ko_idle, 0);

    // Try to find a framebuffer from multiboot2.
    // Falls back to serial-only mode (QEMU development path) if absent.
    match fb::FbDriver::from_mb2(mb2_info) {
        Some(mut fbdrv) => {
            uart::puts("fb: GOP framebuffer online  ");
            uart::putu(fbdrv.width() as u64);
            uart::puts("x");
            uart::putu(fbdrv.height() as u64);
            uart::puts("\r\n");

            let rule_y = fbdrv.height() * 55 / 100;
            x86_splash(&fbdrv, rule_y);

            let mut sh = shell::Shell::new(rule_y);
            sh.boot_banner();
            sh.render(&fbdrv);
            fbdrv.flush();

            let mut frame: u64 = 0;
            loop {
                if let Some(key) = ps2::poll() {
                    // Route key to stdin ring if a user process is waiting,
                    // otherwise give to shell.
                    use input::Key;
                    let consumed = match key {
                        Key::Char(b)   => kbd::push(b),
                        Key::Enter     => kbd::push(b'\n'),
                        Key::Backspace => kbd::push(0x7F),
                    };
                    if !consumed { sh.handle_key(key); }
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
                sh.render(&fbdrv);
                fbdrv.flush();
                frame = frame.wrapping_add(1);
                process::yield_now();
            }
        }

        None => {
            // No framebuffer — fall back to serial Ko shell (QEMU -kernel path).
            uart::puts("fb: no framebuffer tag — serial mode\r\n");
            ps2::init();
            acpi::init(0);
            pci::init();
            hda::init();
            uart::puts("Ko > ");
            let mut line = [0u8; 128];
            let mut len  = 0usize;
            let mut sh   = shell::Shell::new(0);
            sh.boot_banner();

            loop {
                // Serial input
                if let Some(b) = uart::getc() {
                    match b {
                        b'\r' | b'\n' => {
                            uart::puts("\r\n");
                            if len > 0 {
                                sh.handle_key(input::Key::Enter);
                                len = 0;
                            }
                            uart::puts("Ko > ");
                        }
                        0x7F | 0x08 => {
                            if len > 0 {
                                len -= 1;
                                uart::puts("\x08 \x08");
                                sh.handle_key(input::Key::Backspace);
                            }
                        }
                        c if c >= 0x20 && len < 127 => {
                            line[len] = c; len += 1;
                            uart::putc(c);
                            sh.handle_key(input::Key::Char(c));
                        }
                        _ => {}
                    }
                }
                // PS/2 input also feeds shell in serial mode
                if let Some(key) = ps2::poll() {
                    match key {
                        input::Key::Enter => {
                            uart::puts("\r\n");
                            sh.handle_key(key);
                            uart::puts("Ko > ");
                            len = 0;
                        }
                        input::Key::Backspace => {
                            if len > 0 { len -= 1; uart::puts("\x08 \x08"); }
                            sh.handle_key(key);
                        }
                        input::Key::Char(c) => {
                            if len < 127 { line[len] = c; len += 1; uart::putc(c); }
                            sh.handle_key(key);
                        }
                    }
                }
                process::yield_now();
            }
        }
    }
}

// ── Splash ────────────────────────────────────────────────────────────────────

const KO_B: u8 = 0x4b;
const KO_G: u8 = 0x96;
const KO_R: u8 = 0xc8;

fn draw_splash(gpu: &dyn gpu::GpuSurface, rule_y: u32) {
    let w = gpu.width();
    let h = gpu.height();
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
        for px in 0..w { gpu.set_pixel(px, py, 0x10, 0x0c, 0x10); }
    }
}

#[cfg(target_arch = "x86_64")]
fn x86_splash(fb: &fb::FbDriver, rule_y: u32) {
    draw_splash(fb, rule_y);
    // FbDriver flush is a no-op so no explicit call needed.
}

#[cfg(target_arch = "riscv64")]
fn splash(gpu: &mut virtio::GpuDriver, rule_y: u32) {
    draw_splash(gpu, rule_y);
    gpu.flush();
}

// ── Ko idle process (coordinate 19) ──────────────────────────────────────────

fn ko_idle(_: u64) -> ! {
    loop { process::yield_now(); }
}

// ── UEFI kernel entry — called by djinnos-loader after ExitBootServices ───────
//
// At this point we are running with UEFI's identity-mapped page tables.
// We switch to our own kernel stack, zero BSS, then boot normally.
// The page tables from boot_x86.s have NOT been initialised (that happened
// in the 32-bit boot path which was bypassed), so we initialise them here
// before calling `arch::enable_paging` — but since UEFI's identity map
// already covers 0–4 GiB, we can run the kernel without switching CR3 at all
// for Phase 1.  The switch will be forced once user-mode isolation lands.

// Force kernel_uefi_entry to survive LTO dead-code elimination.
// The loader calls it via a raw function pointer resolved at build time.
#[cfg(target_arch = "x86_64")]
#[used]
static _KEEP_UEFI: unsafe extern "sysv64" fn(*const fb::UefiBootInfo) -> ! = kernel_uefi_entry;

#[cfg(target_arch = "x86_64")]
#[no_mangle]
pub unsafe extern "sysv64" fn kernel_uefi_entry(info: *const fb::UefiBootInfo) -> ! {
    extern "C" {
        static _stack_top: u8;
        static _gdt_ptr:   u8;
        static _bss_start: u8;
        static _bss_end:   u8;
    }
    // Switch to the kernel stack (UEFI's may be in reclaimed memory).
    let ksp = core::ptr::addr_of!(_stack_top) as u64;
    core::arch::asm!("mov rsp, {s}", s = in(reg) ksp, options(nostack, nomem));

    // Reload our GDT — UEFI's descriptor table may be in reclaimed memory.
    let gp = core::ptr::addr_of!(_gdt_ptr) as u64;
    core::arch::asm!("lgdt [{g}]", g = in(reg) gp, options(nostack, nomem));

    // Zero BSS (ELF loader zeroed per-segment; kernel statics need it clean).
    let bss_s  = core::ptr::addr_of!(_bss_start) as *mut u64;
    let bss_e  = core::ptr::addr_of!(_bss_end) as usize;
    let qwords = (bss_e - bss_s as usize) / 8;
    for i in 0..qwords { bss_s.add(i).write_volatile(0); }

    let rsdp  = (*info).rsdp_addr;
    let fbdrv = fb::FbDriver::from_uefi(&*info);
    uefi_boot_continue(fbdrv, rsdp)
}

#[cfg(target_arch = "x86_64")]
fn uefi_boot_continue(mut fbdrv: fb::FbDriver, rsdp_hint: u64) -> ! {
    use crate::gpu::GpuSurface;

    arch::uart_init();
    uart::puts("\r\nDjinnOS kernel [x86_64 UEFI]\r\n");

    trap::init();
    uart::puts("trap: online\r\n");

    mm::init();
    let (free, _) = mm::ALLOCATOR.stats();
    uart::puts("heap: online  ");
    uart::putu(free as u64 / 1024);
    uart::puts(" KiB free\r\n");

    uart::puts("fb: GOP framebuffer online  ");
    uart::putu(fbdrv.width() as u64);
    uart::puts("x");
    uart::putu(fbdrv.height() as u64);
    uart::puts("\r\n");

    process::init();
    uart::puts("process subsystem: online\r\n");

    arch::enable_timer();
    uart::puts("timer: online  10ms tick\r\n");

    uart::puts("byte table entries: ");
    uart::putu(byte_table::BYTE_TABLE.len() as u64);
    uart::puts("  candidates: ");
    uart::putu(byte_table::symbol_count() as u64);
    uart::puts("\r\n");

    ps2::init();
    acpi::init(rsdp_hint);
    pci::init();
    hda::init();

    process::advance_cannabis(193);
    process::spawn(19, ko_idle, 0);

    let rule_y = fbdrv.height() * 55 / 100;
    x86_splash(&fbdrv, rule_y);

    let mut sh = shell::Shell::new(rule_y);
    sh.boot_banner();
    sh.render(&fbdrv as &dyn gpu::GpuSurface);
    fbdrv.flush();

    let mut frame: u64 = 0;
    loop {
        if let Some(key) = ps2::poll() {
            use input::Key;
            let consumed = match key {
                Key::Char(b)   => kbd::push(b),
                Key::Enter     => kbd::push(b'\n'),
                Key::Backspace => kbd::push(0x7F),
            };
            if !consumed { sh.handle_key(key); }
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
        sh.render(&fbdrv as &dyn gpu::GpuSurface);
        fbdrv.flush();
        frame = frame.wrapping_add(1);
        process::yield_now();
    }
}

#[panic_handler]
fn panic(_: &PanicInfo) -> ! {
    uart::puts("\r\n[PANIC]\r\n");
    loop {}
}