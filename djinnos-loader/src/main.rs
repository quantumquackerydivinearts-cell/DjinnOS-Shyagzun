//! DjinnOS UEFI loader.
//!
//! The kernel ELF is embedded at build time (no filesystem read needed).
//! Steps at runtime:
//!   1. Query GOP → framebuffer address, dimensions, pixel format.
//!   2. Parse embedded kernel ELF; copy PT_LOAD segments to physical addresses.
//!   3. ExitBootServices.
//!   4. Call kernel_uefi_entry(&boot_info) — never returns.
//!
//! Build order:
//!   cd djinnos-kernel && cargo build --target x86_64-unknown-none --release
//!   cd djinnos-loader  && cargo build --release
//! Output: target/x86_64-unknown-uefi/release/djinnos-loader.efi
//! → copy to D:\EFI\BOOT\BOOTX64.EFI

#![no_std]
#![no_main]

use uefi::prelude::*;
use uefi::proto::console::gop::{GraphicsOutput, PixelFormat};
use uefi::table::boot::{AllocateType, MemoryType, OpenProtocolAttributes, OpenProtocolParams,
                        SearchType};
use uefi::Identify;

// ── Build-time constants ──────────────────────────────────────────────────────

// Kernel ELF embedded at build time — no filesystem read needed.
static KERNEL_ELF: &[u8] = include_bytes!(env!("KERNEL_ELF"));

// kernel_uefi_entry address extracted from the kernel ELF's symbol table.
include!(concat!(env!("OUT_DIR"), "/kernel_entry.rs"));

// ── Boot info layout (must match kernel's fb::UefiBootInfo) ──────────────────

/// Must stay in sync with fb::UefiBootInfo in the kernel.
#[repr(C)]
struct UefiBootInfo {
    fb_addr:   u64,
    fb_width:  u32,
    fb_height: u32,
    fb_pitch:  u32,
    r_pos:     u8,
    g_pos:     u8,
    b_pos:     u8,
    _pad:      u8,
    rsdp_addr: u64,   // ACPI RSDP physical address (0 if not found)
}

// kernel_uefi_entry is resolved at build time; we call it via raw function pointer.

// ── Panic handler ─────────────────────────────────────────────────────────────

#[panic_handler]
fn panic_handler(_: &core::panic::PanicInfo) -> ! {
    loop { unsafe { core::arch::asm!("hlt"); } }
}

// ── UEFI entry ────────────────────────────────────────────────────────────────

#[entry]
fn efi_main(image: Handle, st: SystemTable<Boot>) -> Status {

    // All boot-services work happens in this block so that the borrow of `st`
    // via `bt` ends before `st.exit_boot_services()` moves `st`.
    let (fb_addr, fb_w, fb_h, fb_pitch, r_pos, g_pos, b_pos) = {
        let bt = st.boot_services();

        // ── 1. GOP framebuffer ────────────────────────────────────────────────

        let gop_handles = bt
            .locate_handle_buffer(SearchType::ByProtocol(&GraphicsOutput::GUID))
            .expect("No GOP");
        let gop_handle = gop_handles[0];

        let mut gop = unsafe {
            bt.open_protocol::<GraphicsOutput>(
                OpenProtocolParams { handle: gop_handle, agent: image, controller: None },
                OpenProtocolAttributes::GetProtocol,
            )
            .expect("Cannot open GOP")
        };

        let mode_info = gop.current_mode_info();
        let (w, h) = mode_info.resolution();
        let fb_addr = gop.frame_buffer().as_mut_ptr() as u64;
        let pitch   = gop.frame_buffer().size() / h;

        let (r, g, b): (u8, u8, u8) = match mode_info.pixel_format() {
            PixelFormat::Bgr => (16, 8, 0),
            _                => (0,  8, 16),
        };

        drop(gop);

        // ── 2. Copy kernel ELF PT_LOAD segments ───────────────────────────────

        load_elf(KERNEL_ELF, bt);

        (fb_addr, w as u32, h as u32, pitch as u32, r, g, b)
    };
    // `bt` borrow of `st` ends here.

    // Find ACPI RSDP from the EFI system table config entries.
    let rsdp_addr = find_rsdp_in_config_tables(&st);

    // ── 3. Exit boot services ─────────────────────────────────────────────────

    static mut BOOT_INFO: UefiBootInfo = UefiBootInfo {
        fb_addr: 0, fb_width: 0, fb_height: 0, fb_pitch: 0,
        r_pos: 0, g_pos: 0, b_pos: 0, _pad: 0, rsdp_addr: 0,
    };
    unsafe {
        BOOT_INFO = UefiBootInfo {
            fb_addr, fb_width: fb_w, fb_height: fb_h, fb_pitch,
            r_pos, g_pos, b_pos, _pad: 0,
            rsdp_addr,
        };
    }

    let (_rt, _mm) = st.exit_boot_services(MemoryType::LOADER_DATA);

    // ── 4. Jump to kernel ─────────────────────────────────────────────────────

    // Call kernel_uefi_entry via the address extracted at build time.
    type KernelEntry = unsafe extern "sysv64" fn(*const UefiBootInfo) -> !;
    let entry: KernelEntry = unsafe { core::mem::transmute(KERNEL_UEFI_ENTRY) };
    unsafe { entry(&raw const BOOT_INFO) }
}

// ── ACPI RSDP discovery ───────────────────────────────────────────────────────
//
// The EFI system table carries a config table array where one entry points to
// the ACPI RSDP.  We match on the GUID bytes for both ACPI 1.0 and 2.0.
//
// ACPI 2.0 GUID: {8868E871-E4F1-11D3-BC22-0080C73C8881}
// ACPI 1.0 GUID: {EB9D2D31-2D88-11D3-9A16-0090273FC14D}

fn find_rsdp_in_config_tables(st: &SystemTable<Boot>) -> u64 {
    // ACPI 2.0 GUID bytes (little-endian fields as in EFI spec)
    const ACPI2: [u8; 16] = [
        0x71, 0xE8, 0x68, 0x88,  0xF1, 0xE4, 0xD3, 0x11,
        0xBC, 0x22, 0x00, 0x80,  0xC7, 0x3C, 0x88, 0x81,
    ];
    const ACPI1: [u8; 16] = [
        0x31, 0x2D, 0x9D, 0xEB,  0x88, 0x2D, 0xD3, 0x11,
        0x9A, 0x16, 0x00, 0x90,  0x27, 0x3F, 0xC1, 0x4D,
    ];

    let config = st.config_table();
    let mut acpi1_ptr: u64 = 0;

    for entry in config {
        let g = entry.guid.to_bytes();
        if g == ACPI2 {
            return entry.address as *const u8 as u64;  // prefer ACPI 2.0
        }
        if g == ACPI1 {
            acpi1_ptr = entry.address as *const u8 as u64;
        }
    }
    acpi1_ptr  // fallback to ACPI 1.0 (or 0 if neither found)
}

// ── Minimal ELF64 PT_LOAD loader ─────────────────────────────────────────────

fn load_elf(data: &[u8], bt: &BootServices) {
    if data.len() < 64 || &data[0..4] != b"\x7fELF" || data[4] != 2 {
        panic!("Bad kernel ELF");
    }

    let e_phoff     = u64_le(data, 32) as usize;
    let e_phentsize = u16_le(data, 54) as usize;
    let e_phnum     = u16_le(data, 56) as usize;

    for i in 0..e_phnum {
        let ph = e_phoff + i * e_phentsize;
        if ph + 56 > data.len() { break; }

        if u32_le(data, ph) != 1 { continue; }  // PT_LOAD only

        let p_off    = u64_le(data, ph + 8)  as usize;
        let p_paddr  = u64_le(data, ph + 24) as u64;
        let p_filesz = u64_le(data, ph + 32) as usize;
        let p_memsz  = u64_le(data, ph + 40) as usize;

        if p_memsz == 0 { continue; }

        let page_addr = (p_paddr & !0xFFF) as usize;
        let pages = (p_memsz + (p_paddr as usize & 0xFFF) + 0xFFF) / 0x1000;

        // Allocate at the exact physical address.  Ignore errors — the segment
        // may partially overlap another (e.g. .text / .rodata on same page).
        let _ = bt.allocate_pages(
            AllocateType::Address(page_addr as u64),
            MemoryType::LOADER_DATA,
            pages,
        );

        // Copy file data.
        if p_filesz > 0 {
            let end = (p_off + p_filesz).min(data.len());
            let len = end - p_off;
            unsafe {
                core::ptr::copy_nonoverlapping(
                    data.as_ptr().add(p_off),
                    p_paddr as *mut u8,
                    len,
                );
            }
        }
        // Zero bss portion.
        if p_memsz > p_filesz {
            unsafe {
                core::ptr::write_bytes(
                    (p_paddr + p_filesz as u64) as *mut u8,
                    0,
                    p_memsz - p_filesz,
                );
            }
        }
    }
}

fn u16_le(b: &[u8], off: usize) -> u16 {
    u16::from_le_bytes(b[off..off+2].try_into().unwrap())
}
fn u32_le(b: &[u8], off: usize) -> u32 {
    u32::from_le_bytes(b[off..off+4].try_into().unwrap())
}
fn u64_le(b: &[u8], off: usize) -> u64 {
    u64::from_le_bytes(b[off..off+8].try_into().unwrap())
}
