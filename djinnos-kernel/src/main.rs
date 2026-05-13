#![no_std]
#![no_main]
#![allow(dead_code)]
#![allow(static_mut_refs)]

extern crate alloc;

mod agent;
mod alchemy;
mod book;
mod foraging;
mod perk_screen;
mod printer;
mod atelier;
mod combat;
mod dialogue;
mod dialogue_tree;
mod dungeon;
mod nvme;
mod gpt;
mod fat32w;
mod installer;
mod rtw89;
mod intel;
mod http_intel;
mod http_building;
mod journal;
mod ko_flags;
mod meditation;
mod player_state;
mod quest_tracker;
mod shop;
mod game7;
mod home;
mod npc_placements;
mod truetype;
mod npc_screen;
mod skills;
mod sprite;
mod voxel_lab;
mod zone_registry;
#[cfg(target_arch = "x86_64")]
mod amdgpu;
mod compositor;
mod background;
mod dhcp;
mod faerie_pages;
mod login;
mod mesh;
mod ne_bar;
mod profile;
mod render2d;
mod style;
mod voxel_modeler;
#[cfg(target_arch = "x86_64")]
mod cursor;
mod voxel;
mod kos_characters;
mod sa;
mod arch;
mod byte_table;
mod editor;
mod kos_labyrnth;
mod eigenstate;
mod kobra;
mod kobra_repl;
mod palette;
mod tiler;
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
mod crypto;
mod net_stack;
mod rhezh;
mod rhokve;
mod renderer_bridge;
mod world;
mod browser;

#[cfg(not(target_arch = "riscv64"))]
mod e1000;
#[cfg(not(target_arch = "riscv64"))]
mod xhci;
#[cfg(not(target_arch = "riscv64"))]
mod usb;
#[cfg(not(target_arch = "riscv64"))]
mod usb_net;
#[cfg(not(target_arch = "riscv64"))]
mod x86net;
// Expose crate::net on x86_64 with the same API as the RISC-V net.rs.
#[cfg(not(target_arch = "riscv64"))]
mod net { pub use crate::x86net::*; }

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
mod ramdisk;
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
mod i2c_hid;
mod recombination;
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
        let pa_start = core::ptr::addr_of!(_stack_top) as u64;
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

    renderer_bridge::verify_and_log();

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
        uart::puts("NET: 10.0.2.15/24  gw 10.0.2.2\r\n");
    } else {
        uart::puts("NET: no virtio-net device\r\n");
    }
    let mut sh = shell::Shell::new(rule_y);
    sh.boot_banner();
    sh.render(&gpu as &dyn gpu::GpuSurface);
    gpu.flush();

    process::spawn(19, ko_idle, 0);

    let mut frame: u64       = 0;
    let mut game_mode: bool   = false;
    let mut browser_mode: bool = false;
    // 60 fps cap: 10 MHz CLINT / 60 ≈ 166_666 ticks ≈ 16.7 ms per frame.
    let mut next_flush: u64 = arch::read_mtime();

    loop {
        if world::consume_launch() {
            game_mode    = true;
            browser_mode = false;
        }
        if browser::consume_launch() {
            browser_mode = true;
            game_mode    = false;
        }

        if let Some(ref mut k) = kbd {
            while let Some(key) = k.poll() {
                use virtio::input::Key;
                if game_mode {
                    match key {
                        Key::Escape => {
                            game_mode = false;
                            world::world().exit();
                            sh.set_frame(frame);
                        }
                        _ => { world::world().handle_key(key); }
                    }
                } else if browser_mode {
                    match key {
                        Key::Escape => {
                            browser_mode = false;
                            browser::browser().exit();
                            sh.set_frame(frame);
                        }
                        _ => { browser::browser().handle_key(key); }
                    }
                } else {
                    match key {
                        Key::Char(b)   => { kbd::push(b); }
                        Key::Enter     => { kbd::push(b'\n'); }
                        Key::Backspace => { kbd::push(0x7F); }
                        _ => {}
                    }
                    sh.handle_key(key);
                }
            }
        }

        if !game_mode && !browser_mode {
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

        net::poll();

        // Gate rendering and GPU flush to ~60 fps.  QEMU's VirtIO GPU SDL
        // display path cannot keep up with thousands of flush calls per second;
        // poll() would spin forever waiting for a used-ring write that never
        // comes.  net::poll() and input still run at full loop speed.
        let now = arch::read_mtime();
        if now >= next_flush {
            next_flush = now + 166_666;
            if game_mode {
                world::world().render(&gpu as &dyn gpu::GpuSurface);
            } else if browser_mode {
                browser::browser().render(&gpu as &dyn gpu::GpuSurface);
            } else {
                sh.set_frame(frame);
                sh.render(&gpu as &dyn gpu::GpuSurface);
            }
            gpu.flush();
            frame = frame.wrapping_add(1);
        }

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

    uart::puts("NET: scanning for e1000...\r\n");
    if x86net::init() {
        uart::puts("NET: e1000 online  10.0.2.15/24  gw 10.0.2.2\r\n");
    } else {
        uart::puts("NET: no e1000 NIC found\r\n");
    }

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
                    use input::Key;
                    let consumed = match key {
                        Key::Char(b)   => kbd::push(b),
                        Key::Enter     => kbd::push(b'\n'),
                        Key::Backspace => kbd::push(0x7F),
                        _              => false,
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

                x86net::poll();
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
                        _ => {}
                    }
                }
                process::yield_now();
            }
        }
    }
}

// ── Splash ────────────────────────────────────────────────────────────────────

fn draw_splash(gpu: &dyn gpu::GpuSurface, rule_y: u32) {
    use crate::render2d::It;
    use crate::style;

    let it = It::new(gpu);
    let t  = style::get();
    let w  = gpu.width();
    let h  = gpu.height();

    // Full-screen vertical gradient: bg -> slightly lighter at rule_y
    it.grad_v(0, 0, w, rule_y, t.bg, style::mix(t.bg, t.surface, 120));

    // Lower panel: slightly darker than bg, fills below the rule
    it.fill(0, rule_y + 2, w, h.saturating_sub(rule_y + 2), style::darken(t.bg, 15));

    // Wordmark -- "DjinnOS" centred above rule, scale 4, with shadow
    let scale  = 4u32;
    let ch_w   = font::GLYPH_W * scale;
    let ch_h   = font::GLYPH_H * scale;
    let label  = "DjinnOS";
    let lw     = label.len() as u32 * ch_w;
    let lx     = (w.saturating_sub(lw)) / 2;
    let ly     = rule_y.saturating_sub(ch_h + style::M6 + style::M4);
    // Drop shadow
    it.text(lx + 3, ly + 3, label, scale, t.shadow);
    // Gold title
    it.text(lx, ly, label, scale, t.header);

    // Subtitle: "Ko's Labyrinth — 7_KLGS"
    let sub  = "Ko's Labyrinth  7_KLGS";
    let sw   = sub.len() as u32 * font::GLYPH_W * 2;
    let sx   = (w.saturating_sub(sw)) / 2;
    let sy   = ly + ch_h + style::M3;
    it.text(sx, sy, sub, 2, t.text_dim);

    // Horizontal rule: gradient fade from edges, bright at center
    let rx0 = w / 8;
    let rx1 = w * 6 / 8;
    it.grad_h(rx0,        rule_y, rx1 / 2, style::RULE_W, t.shadow, t.rule);
    it.grad_h(rx0 + rx1/2, rule_y, rx1 / 2, style::RULE_W, t.rule, t.shadow);
    // Second pixel, dimmer
    it.grad_h(rx0,        rule_y + 1, rx1 / 2, style::RULE_W, t.bg, t.shadow);
    it.grad_h(rx0 + rx1/2, rule_y + 1, rx1 / 2, style::RULE_W, t.shadow, t.bg);

    // Accent bar above wordmark — thin horizontal stripe in accent green
    let bar_y = ly.saturating_sub(style::M4);
    let bar_w = w * 2 / 5;
    let bar_x = (w.saturating_sub(bar_w)) / 2;
    it.grad_h(bar_x, bar_y, bar_w / 2, 2, t.shadow, t.accent);
    it.grad_h(bar_x + bar_w / 2, bar_y, bar_w / 2, 2, t.accent, t.shadow);

    // Bottom caption: "Kaelshunshikeaninsuy" in dim accent, bottom-center
    let cap  = "Kaelshunshikeaninsuy";
    let cw   = cap.len() as u32 * font::GLYPH_W * 2;
    let cx   = (w.saturating_sub(cw)) / 2;
    let cy   = h.saturating_sub(font::GLYPH_H * 2 + style::M4 * 2);
    it.text(cx, cy, cap, 2, style::darken(t.accent, 40));
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

// UEFI header section — djinnos-loader scans ELF section headers for ".uefi_hdr"
// and reads the 8-byte function pointer it contains to find the entry point.
// This survives stripping (section headers are kept; only .symtab is stripped).
#[cfg(target_arch = "x86_64")]
#[used]
#[link_section = ".uefi_hdr"]
static UEFI_ENTRY_PTR: unsafe extern "sysv64" fn(*const fb::UefiBootInfo) -> ! =
    kernel_uefi_entry;

// Minimal trampoline — the only job of this function is to atomically:
//   1. cli   — block timer IRQs before UEFI's IDT handlers disappear
//   2. switch RSP to the kernel stack
//   3. reload our own GDT
//   4. JMP (not CALL) to kernel_uefi_body
//
// Using JMP means no return address is pushed; kernel_uefi_body gets a fresh
// prologue on the kernel stack with no UEFI frame mixed in.  RDI (= info) is
// preserved by the asm block and received as the first argument of the body.
#[cfg(target_arch = "x86_64")]
#[no_mangle]
pub unsafe extern "sysv64" fn kernel_uefi_entry(info: *const fb::UefiBootInfo) -> ! {
    extern "C" {
        static _stack_top: u8;
        static _gdt_ptr:   u8;
    }
    core::arch::asm!(
        "cli",
        "mov rsp, {ksp}",
        "lgdt [{gdt}]",
        // Far-return to reload CS=0x08 from our new GDT before enabling
        // interrupts.  After lgdt the CS shadow register still holds UEFI's
        // selector (typically 0x38 or higher).  Our GDT has only three entries
        // (null/0x08/0x10), so IRET from any interrupt would try to restore
        // UEFI's CS, find it beyond our GDT limit, #GP → _isr_fault → hlt.
        // lretq atomically sets CS=0x08 and jumps to kernel_uefi_body.
        // RDI (= info) is preserved through the push/lretq sequence.
        "lea rax, [{body}]",  // rax = kernel_uefi_body address (RIP-relative)
        "push 8",             // new CS = 0x08 (code64 in our GDT)
        "push rax",           // new RIP = kernel_uefi_body
        ".byte 0x48, 0xcb",   // REX.W + CB = 64-bit far return (lretq)
        ksp  = in(reg) core::ptr::addr_of!(_stack_top) as u64,
        gdt  = in(reg) core::ptr::addr_of!(_gdt_ptr) as u64,
        body = sym kernel_uefi_body,
        options(noreturn),
    );
}

// Called via far-return from kernel_uefi_entry.  Runs on the kernel stack
// with interrupts disabled and CS=0x08.  RDI = info (sysv64 first arg).
#[cfg(target_arch = "x86_64")]
unsafe extern "sysv64" fn kernel_uefi_body(info: *const fb::UefiBootInfo) -> ! {
    // Reload SS, DS, ES with our GDT data64 descriptor (0x10).
    // lretq set CS=0x08 but left SS holding UEFI's selector (often 0x18–0x38).
    // When IRET restores the saved SS after any interrupt, if that selector
    // isn't in our 3-entry GDT the CPU throws #GP → _isr_fault → hlt.
    core::arch::asm!(
        "mov ax, 0x10",
        "mov ss, ax",
        "mov ds, ax",
        "mov es, ax",
        out("ax") _,
        options(nostack, preserves_flags),
    );
    let rsdp   = (*info).rsdp_addr;
    let rdaddr = (*info).ramdisk_addr;
    let rdcnt  = (*info).ramdisk_count;
    let fbdrv  = fb::FbDriver::from_uefi(&*info);
    uefi_boot_continue(fbdrv, rsdp, rdaddr, rdcnt)
}

#[cfg(target_arch = "x86_64")]
fn uefi_boot_continue(mut fbdrv: fb::FbDriver, rsdp_hint: u64, rdaddr: u64, rdcnt: u32) -> ! {
    use crate::gpu::GpuSurface;

    arch::uart_init();
    uart::puts("\r\nDjinnOS kernel [x86_64 UEFI]\r\n");

    trap::init();
    mm::init();
    process::init();
    kos_characters::init();
    sa::init_empty(b"DjinnOS");
    ramdisk::init(rdaddr, rdcnt);

    let rule_y = fbdrv.height() * 55 / 100;
    style::init();
    x86_splash(&fbdrv, rule_y);
    let mut sh = shell::Shell::new(rule_y);
    sh.boot_banner();
    sh.render(&fbdrv as &dyn gpu::GpuSurface);
    fbdrv.flush();

    // PS/2: UEFI enables i8042; we extend init to enable the aux (mouse) port.
    ps2::init();
    // I2C HID: probe LPSS controller + trackpad (HP Envy ELAN / Synaptics).
    // Non-fatal if no I2C controller found (USB mouse / PS/2 still work).
    i2c_hid::init();
    cursor::init(fbdrv.width(), fbdrv.height());

    // Graphics stack init.
    style::init();
    #[cfg(target_arch = "x86_64")]
    amdgpu::init();
    compositor::init();

    arch::enable_timer();
    arch::start_timer();

    acpi::init(rsdp_hint);
    acpi::disable_iommu();  // must precede any PCIe DMA driver
    pci::init();
    hda::init();

    process::advance_cannabis(193);
    process::spawn(19, ko_idle, 0);

    printer::init();
    profile::load_or_init();
    eigenstate::load();
    player_state::load();
    journal::journal().load();
    foraging::fae().load();
    faerie_pages::seed(); // write initial local:// pages to Sa if absent
    let mut login_screen = login::LoginScreen::new(rule_y);

    let mut repl  = kobra_repl::KobraRepl::new(rule_y);
    repl.reset();
    let mut ed    = editor::Editor::new(rule_y);
    let mut tilr  = tiler::Tiler::new(rule_y);
    let mut atl   = atelier::Atelier::new(rule_y);
    let mut vlab  = voxel_lab::VoxelLab::new(rule_y);
    let mut vrsei = voxel_modeler::Vrsei::new(rule_y);

    #[derive(PartialEq)]
    enum AppMode {
        Login, Shell, Repl, Editor, Tiler, Browser, Atelier, VoxelLab, Vrsei,
        Alchemy, Combat, Shop, Meditation, Journal, Book, Perks, Game7, NpcScreen, Home,
    }
    let mut mode         = AppMode::Login;
    let mut from_atelier = false;

    let mut frame: u64 = 0;
    // Render only on meaningful events.  The HP Envy's i8042 emits noise
    // bytes; treating every PS/2 byte as a render trigger floods the
    // uncached framebuffer and hides real input.
    let mut dirty    = true;  // initial render
    let mut mode_name = "DjinnOS"; // kept in sync with mode each iteration
    loop {
        // Mode name kept current for eigenstate advance and Ne Bar display.
        mode_name = match mode {
            AppMode::Login     => "DjinnOS",
            AppMode::Shell     => "Ko",
            AppMode::Repl      => "Soa",
            AppMode::Editor    => "Saoshin",
            AppMode::Tiler     => "Samos",
            AppMode::Browser   => "Faerie",
            AppMode::Atelier   => "Kaelshunshikeaninsuy",
            AppMode::VoxelLab  => "To",
            AppMode::Vrsei     => "Vrsei",
            AppMode::Alchemy   => "Alchemy",
            AppMode::Combat    => "Combat",
            AppMode::Shop      => "Shop",
            AppMode::Meditation=> "Meditation",
            AppMode::Journal   => "Journal",
            AppMode::Book      => "Codex",
            AppMode::Perks     => "Perks",
            AppMode::Game7     => "7_KLGS",
            AppMode::NpcScreen => "NPC",
            AppMode::Home      => "Home",
        };

        // ── Logout check ──────────────────────────────────────────────────────
        if profile::consume_logout() {
            login_screen = login::LoginScreen::new(rule_y);
            mode  = AppMode::Login;
            dirty = true;
        }

        // ── Mode-switch requests (set by shell commands or Atelier) ──────────
        if kobra_repl::consume_request() {
            repl.reset();
            mode  = AppMode::Repl;
            dirty = true;
        }
        if let Some(name) = editor::consume_request() {
            ed.load(name);
            mode  = AppMode::Editor;
            dirty = true;
        }
        if tiler::consume_request() {
            tilr.reset();
            mode  = AppMode::Tiler;
            dirty = true;
        }
        if browser::consume_launch() {
            mode  = AppMode::Browser;
            dirty = true;
        }
        if atelier::consume_request() {
            atl.reset();
            mode  = AppMode::Atelier;
            dirty = true;
        }
        if voxel_lab::consume_request() {
            mode  = AppMode::VoxelLab;
            dirty = true;
        }
        if alchemy::consume_request() {
            alchemy::workbench().open(rule_y);
            mode  = AppMode::Alchemy;
            dirty = true;
        }
        if combat::consume_request() {
            mode  = AppMode::Combat;
            dirty = true;
        }
        if shop::consume_request() {
            shop::shop().open_player_shop(rule_y);
            mode  = AppMode::Shop;
            dirty = true;
        }
        if meditation::consume_request() {
            meditation::meditation().open(rule_y);
            mode  = AppMode::Meditation;
            dirty = true;
        }
        if journal::consume_request() {
            journal::journal().open(rule_y);
            mode  = AppMode::Journal;
            dirty = true;
        }
        if perk_screen::consume_request() {
            perk_screen::screen().open(rule_y);
            mode  = AppMode::Perks;
            dirty = true;
        }
        if book::consume_request() {
            book::book().open(rule_y);
            mode  = AppMode::Book;
            dirty = true;
        }
        if game7::consume_request() {
            game7::game7().open(rule_y);
            mode  = AppMode::Game7;
            dirty = true;
        }
        if home::consume_request() {
            home::home().open(rule_y);
            mode  = AppMode::Home;
            dirty = true;
        }
        if npc_screen::consume_request() {
            mode  = AppMode::NpcScreen;
            dirty = true;
        }
        // NPC screen exits back to Game7 (its caller).
        if mode == AppMode::Shell && npc_screen::screen().exited {
            npc_screen::screen().exited = false;
            mode  = AppMode::Game7;
            dirty = true;
        }
        // Return from combat triggered inside dungeon walk.
        if mode == AppMode::Shell && game7::consume_from_combat() {
            // Combat was initiated from Game7 -- resume it.
            game7::game7().on_combat_return();
            mode  = AppMode::Game7;
            dirty = true;
        }
        // Atelier sub-tool dispatch
        if mode == AppMode::Atelier {
            if let Some(launch) = atl.consume_launch() {
                use atelier::AtelierLaunch;
                match launch {
                    AtelierLaunch::KoStudio => {
                        repl.reset(); mode = AppMode::Repl; from_atelier = true;
                    }
                    AtelierLaunch::Yew => {
                        ed.load(atelier::launch_input());
                        mode = AppMode::Editor; from_atelier = true;
                    }
                    AtelierLaunch::Ledger => {
                        tilr.reset(); mode = AppMode::Tiler; from_atelier = true;
                    }
                    AtelierLaunch::Faerie => {
                        crate::browser::request_launch(atelier::launch_input());
                        mode = AppMode::Browser; from_atelier = true;
                    }
                    AtelierLaunch::VoxelLab => {
                        vlab.open(&[]);
                        mode = AppMode::VoxelLab; from_atelier = true;
                    }
                    AtelierLaunch::Vrsei => {
                        vrsei.open();
                        mode = AppMode::Vrsei; from_atelier = true;
                    }
                    AtelierLaunch::Shell => {
                        from_atelier = false; mode = AppMode::Shell;
                    }
                }
                dirty = true;
            }
        }

        // ── Mouse polling ─────────────────────────────────────────────────
        #[cfg(target_arch = "x86_64")]
        {
            // I2C HID (trackpad) — poll then drain
            i2c_hid::poll();
            while let Some(mev) = i2c_hid::poll_mouse() {
                cursor::update(mev, fbdrv.width(), fbdrv.height());
                let (cx, cy) = cursor::pos();
                compositor::get().on_cursor_move(cx, cy);
                eigenstate::advance(eigenstate::T_SAKURA);
                dirty = true;
            }
            // PS/2 mouse (USB HID mouse / external)
            while let Some(mev) = ps2::poll_mouse() {
                cursor::update(mev, fbdrv.width(), fbdrv.height());
                let (cx, cy) = cursor::pos();
                compositor::get().on_cursor_move(cx, cy);
                eigenstate::advance(eigenstate::T_SAKURA);
                dirty = true;
            }
            // Left click dispatch
            if cursor::left_clicked() {
                let (cx, cy) = cursor::pos();
                if mode == AppMode::Browser {
                    browser::browser().handle_click(cx, cy);
                    dirty = true;
                }
            }
        }

        // ── Notification tick ─────────────────────────────────────────────
        if compositor::get().tick_notifs() { dirty = true; }

        // ── Key handling ──────────────────────────────────────────────────
        if let Some(key) = ps2::poll() {
            // Every key press is presence — Lotus advances on input.
            eigenstate::advance(eigenstate::T_LOTUS);
            // Mode-specific tongue advances on each keypress in that mode.
            eigenstate::advance_mode(mode_name);
            use input::Key;
            match mode {
                AppMode::Login => {
                    login_screen.handle_key(key);
                    if login_screen.done {
                        home::home().open(rule_y);
                        mode = AppMode::Home;
                    }
                    dirty = true;
                }
                AppMode::Home => {
                    home::home().handle_key(key);
                    if home::home().exited {
                        home::home().exited = false;
                        mode = AppMode::Shell;
                    } else if let Some(launch) = home::home().launch.take() {
                        use home::TileLaunch;
                        match launch {
                            TileLaunch::Atelier   => { atl.reset(); mode = AppMode::Atelier; }
                            TileLaunch::Play      => { game7::game7().open(rule_y); mode = AppMode::Game7; }
                            TileLaunch::Journal   => { journal::journal().open(rule_y); journal::request(); mode = AppMode::Journal; }
                            TileLaunch::Shell     => { mode = AppMode::Shell; }
                            TileLaunch::Meditation=> { meditation::meditation().open(rule_y); meditation::request(); mode = AppMode::Meditation; }
                            TileLaunch::Codex     => { book::book().open(rule_y); book::request(); mode = AppMode::Book; }
                        }
                    }
                    dirty = true;
                }
                AppMode::Repl => {
                    let was_exited = repl.exited();
                    repl.handle_key(key);
                    if !was_exited && repl.exited() {
                        mode = if from_atelier { from_atelier = false; AppMode::Atelier }
                               else { AppMode::Shell };
                    }
                    dirty = true;
                }
                AppMode::Editor => {
                    let was_exited = ed.exited();
                    ed.handle_key(key);
                    if !was_exited && ed.exited() {
                        mode = if from_atelier { from_atelier = false; AppMode::Atelier }
                               else { AppMode::Shell };
                    }
                    dirty = true;
                }
                AppMode::Tiler => {
                    let was_exited = tilr.exited();
                    tilr.handle_key(key);
                    if !was_exited && tilr.exited() {
                        mode = if from_atelier { from_atelier = false; AppMode::Atelier }
                               else { AppMode::Shell };
                    }
                    dirty = true;
                }
                AppMode::Browser => {
                    use input::Key;
                    match key {
                        Key::Escape => {
                            browser::browser().exit();
                            mode = if from_atelier { from_atelier = false; AppMode::Atelier }
                                   else { AppMode::Shell };
                        }
                        _ => { browser::browser().handle_key(key); }
                    }
                    dirty = true;
                }
                AppMode::Atelier => {
                    atl.handle_key(key);
                    dirty = true;
                }
                AppMode::VoxelLab => {
                    let was_exited = vlab.exited();
                    vlab.handle_key(key);
                    if !was_exited && vlab.exited() {
                        mode = if from_atelier { from_atelier = false; AppMode::Atelier }
                               else { AppMode::Shell };
                    }
                    dirty = true;
                }
                AppMode::Vrsei => {
                    let was_exited = vrsei.exited();
                    vrsei.handle_key(key);
                    if !was_exited && vrsei.exited() {
                        mode = if from_atelier { from_atelier = false; AppMode::Atelier }
                               else { AppMode::Shell };
                    }
                    dirty = true;
                }
                AppMode::Alchemy => {
                    let was = alchemy::workbench().exited();
                    alchemy::workbench().handle_key(key);
                    if !was && alchemy::workbench().exited() { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::Combat => {
                    let was = combat::combat().exited();
                    combat::combat().handle_key(key);
                    if !was && combat::combat().exited() { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::Shop => {
                    let was = shop::shop().exited();
                    shop::shop().handle_key(key);
                    if !was && shop::shop().exited() { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::Meditation => {
                    let was = meditation::meditation().exited();
                    meditation::meditation().handle_key(key);
                    if !was && meditation::meditation().exited() { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::Journal => {
                    let was = journal::journal().exited();
                    journal::journal().handle_key(key);
                    if !was && journal::journal().exited() { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::Book => {
                    let was = book::book().exited();
                    book::book().handle_key(key);
                    if !was && book::book().exited() { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::Perks => {
                    let was = perk_screen::screen().exited();
                    perk_screen::screen().handle_key(key);
                    if !was && perk_screen::screen().exited() { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::Game7 => {
                    let was = game7::game7().exited;
                    game7::game7().handle_key(key);
                    if !was && game7::game7().exited { mode = AppMode::Shell; }
                    dirty = true;
                }
                AppMode::NpcScreen => {
                    let was = npc_screen::screen().exited;
                    npc_screen::screen().handle_key(key);
                    if !was && npc_screen::screen().exited {
                        npc_screen::screen().exited = false;
                        mode = AppMode::Game7;
                    }
                    dirty = true;
                }
                AppMode::Shell => match key {
                    Key::Char(b) => {
                        sh.handle_key(key); kbd::push(b); dirty = true;
                    }
                    Key::Enter => {
                        sh.handle_key(key); kbd::push(b'\n'); dirty = true;
                    }
                    Key::Backspace => {
                        sh.handle_key(key); kbd::push(0x7F); dirty = true;
                    }
                    _ => { sh.handle_key(key); }
                },
            }
        }

        // ── stdout drain (shell mode only) ────────────────────────────────
        if mode == AppMode::Shell {
            let mut line = [0u8; 80];
            let mut n = 0usize;
            while let Some(b) = kbd::stdout_pop() {
                if b == b'\n' || b == b'\r' {
                    if n > 0 { sh.push_user_line(&line[..n]); n = 0; dirty = true; }
                } else if b >= 0x20 && n < 79 {
                    line[n] = b; n += 1;
                }
            }
            if n > 0 { sh.push_user_line(&line[..n]); dirty = true; }
        }

        x86net::poll();

        // Persist eigenstate every ~5 s so linguistic history survives reboots.
        if frame % 300 == 0 && frame > 0 { eigenstate::persist(); }

        if dirty {
            dirty = false;
            compositor::get().mark_dirty(compositor::LayerKind::Content);
            let fb_ref = &fbdrv as &dyn gpu::GpuSurface;
            let profile_name = profile::active()
                .map(|p| core::str::from_utf8(p.name_str()).unwrap_or(""))
                .unwrap_or("");
            compositor::get().render(fb_ref, mode_name, profile_name, frame, |gpu| {
                match mode {
                    AppMode::Shell => {
                        sh.set_frame(frame);
                        sh.render(gpu);
                    }
                    AppMode::Repl     => { repl.render(gpu); }
                    AppMode::Editor   => { ed.render(gpu); }
                    AppMode::Tiler    => { tilr.render(gpu); }
                    AppMode::Browser  => { browser::browser().render(gpu); }
                    AppMode::Atelier  => { atl.render(gpu); }
                    AppMode::Login     => { login_screen.render(gpu); }
                    AppMode::VoxelLab  => { vlab.render(gpu); }
                    AppMode::Vrsei     => { vrsei.render(gpu); }
                    AppMode::Alchemy   => { alchemy::workbench().render(gpu); }
                    AppMode::Combat    => { combat::combat().render(gpu); }
                    AppMode::Shop      => { shop::shop().render(gpu); }
                    AppMode::Meditation=> { meditation::meditation().render(gpu); }
                    AppMode::Journal   => { journal::journal().render(gpu); }
                    AppMode::Book      => { book::book().render(gpu); }
                    AppMode::Perks     => { perk_screen::screen().render(gpu); }
                    AppMode::Game7     => { game7::game7().render(gpu); }
                    AppMode::NpcScreen => { npc_screen::screen().render(gpu); }
                    AppMode::Home      => { home::home().render(gpu); }
                }
            });
            fbdrv.flush();
            frame = frame.wrapping_add(1);
        }
        process::yield_now();
    }
}

#[panic_handler]
fn panic(_: &PanicInfo) -> ! {
    uart::puts("\r\n[PANIC]\r\n");
    loop {}
}