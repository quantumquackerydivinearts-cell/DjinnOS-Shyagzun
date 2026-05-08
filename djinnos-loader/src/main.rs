// DjinnOS UEFI bootloader
// ========================
// Loaded as EFI/BOOT/BOOTX64.EFI from an EFI System Partition.
// Reads \djinnos-kernel from the same partition, parses its ELF64 segments,
// loads them into physical memory, then hands control to kernel_uefi_entry.
//
// Build: cargo build --release   (target = x86_64-unknown-uefi in .cargo/config)
// Output: target/x86_64-unknown-uefi/release/djinnos-loader.efi
//
// UefiBootInfo layout MUST stay in sync with fb.rs:UefiBootInfo in the kernel.

#![no_std]
#![no_main]
#![allow(dead_code)]

use core::ptr;

// ── UefiBootInfo (must match djinnos-kernel/src/fb.rs) ───────────────────────

#[repr(C)]
struct UefiBootInfo {
    fb_addr:   u64,
    fb_width:  u32,
    fb_height: u32,
    fb_pitch:  u32,   // bytes per row
    r_pos:     u8,
    g_pos:     u8,
    b_pos:     u8,
    _pad:      u8,
    rsdp_addr: u64,
}

static mut BOOT_INFO: UefiBootInfo = UefiBootInfo {
    fb_addr: 0, fb_width: 0, fb_height: 0, fb_pitch: 0,
    r_pos: 0, g_pos: 8, b_pos: 16, _pad: 0, rsdp_addr: 0,
};

// ── EFI types ─────────────────────────────────────────────────────────────────

type EfiStatus = usize;
type EfiHandle = *const ();

const SUCCESS: EfiStatus = 0;
const BUFFER_TOO_SMALL: EfiStatus = 0x8000_0000_0000_0005;

// Memory types for AllocatePool / AllocatePages
const EFI_LOADER_CODE: u32 = 1;
const EFI_LOADER_DATA: u32 = 2;

// AllocatePages type
const ALLOCATE_ADDRESS: u32 = 2;

// OpenProtocol attributes
const BY_HANDLE_PROTOCOL: u32 = 0x1;

// File open mode
const FILE_READ: u64 = 1;

#[repr(C)]
struct Guid { d1: u32, d2: u16, d3: u16, d4: [u8; 8] }

const GOP_GUID: Guid = Guid {
    d1: 0x9042_a9de, d2: 0x23dc, d3: 0x4a38,
    d4: [0x96, 0xfb, 0x7a, 0xde, 0xd0, 0x80, 0x51, 0x6a],
};
const SFS_GUID: Guid = Guid {
    d1: 0x0964_e5b2, d2: 0x6459, d3: 0x11d2,
    d4: [0x8e, 0x39, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b],
};
const BLOCKIO_GUID: Guid = Guid {
    d1: 0x964e_5b21, d2: 0x6459, d3: 0x11d2,
    d4: [0x8e, 0x39, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b],
};
const LI_GUID: Guid = Guid {
    d1: 0x5b1b_31a1, d2: 0x9562, d3: 0x11d2,
    d4: [0x8e, 0x3f, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b],
};
const ACPI20_GUID: Guid = Guid {
    d1: 0x8868_e871, d2: 0xe4f1, d3: 0x11d3,
    d4: [0xbc, 0x22, 0x00, 0x80, 0xc7, 0x3c, 0x88, 0x81],
};
const ACPI10_GUID: Guid = Guid {
    d1: 0xeb9d_2d30, d2: 0x2d88, d3: 0x11d3,
    d4: [0x9a, 0x16, 0x00, 0x90, 0x27, 0x3f, 0xc1, 0x4d],
};
const FILE_INFO_GUID: Guid = Guid {
    d1: 0x0957_6e92, d2: 0x6d3f, d3: 0x11d2,
    d4: [0x8e, 0x39, 0x00, 0xa0, 0xc9, 0x69, 0x72, 0x3b],
};

fn guid_eq(a: &Guid, b: &Guid) -> bool {
    a.d1 == b.d1 && a.d2 == b.d2 && a.d3 == b.d3 && a.d4 == b.d4
}

// ── EFI table / protocol definitions ─────────────────────────────────────────

#[repr(C)]
pub struct EfiTableHdr { sig: u64, rev: u32, sz: u32, crc: u32, _res: u32 }

type ConOutStr = unsafe extern "efiapi" fn(*mut ConOut, *const u16) -> EfiStatus;
#[repr(C)]
pub struct ConOut {
    reset:         *const (),
    output_string: ConOutStr,
}

#[repr(C)]
pub struct SystemTable {
    hdr:         EfiTableHdr,
    fw_vendor:   *const u16,
    fw_rev:      u32, _pad: u32,
    con_in_hdl:  EfiHandle,
    con_in:      *const (),
    con_out_hdl: EfiHandle,
    con_out:     *mut ConOut,
    stderr_hdl:  EfiHandle,
    stderr:      *const (),
    runtime_svc: *const (),
    boot_svc:    *const BootServices,
    n_cfg:       usize,
    cfg_table:   *const CfgEntry,
}

unsafe fn say_hex(st: *const SystemTable, n: u64) {
    let out = (*st).con_out;
    if out.is_null() { return; }
    let mut buf = [0u16; 18];
    buf[0] = b'0' as u16; buf[1] = b'x' as u16;
    for i in 0..16 {
        let nib = ((n >> (60 - i*4)) & 0xF) as u8;
        buf[2+i] = if nib < 10 { (b'0' + nib) as u16 }
                   else { (b'a' + nib - 10) as u16 };
    }
    buf[17] = 0;
    ((*out).output_string)(out, buf.as_ptr());
    ((*(*st).boot_svc).stall)(1_000_000);
}

// Print an ASCII string to the UEFI console and pause so the user can read it.
unsafe fn say(st: *const SystemTable, msg: &[u8]) {
    let out = (*st).con_out;
    if !out.is_null() {
        let mut buf = [0u16; 80];
        let n = msg.len().min(79);
        for i in 0..n { buf[i] = msg[i] as u16; }
        buf[n] = 0;
        ((*out).output_string)(out, buf.as_ptr());
    }
    // 2-second stall so text is readable before any screen clear.
    let bs = (*st).boot_svc;
    ((*bs).stall)(2_000_000);
}

#[repr(C)]
struct CfgEntry { guid: Guid, table: *const () }

type AllocPagesFn  = unsafe extern "efiapi" fn(u32, u32, usize, *mut u64) -> EfiStatus;
type FreePagesFn   = unsafe extern "efiapi" fn(u64, usize) -> EfiStatus;
type GetMemMapFn   = unsafe extern "efiapi" fn(*mut usize, *mut u8, *mut usize, *mut usize, *mut u32) -> EfiStatus;
type AllocPoolFn   = unsafe extern "efiapi" fn(u32, usize, *mut *mut u8) -> EfiStatus;
type FreePoolFn    = unsafe extern "efiapi" fn(*mut u8) -> EfiStatus;
type HandleProtoFn = unsafe extern "efiapi" fn(EfiHandle, *const Guid, *mut *const ()) -> EfiStatus;
type ExitBsFn      = unsafe extern "efiapi" fn(EfiHandle, usize) -> EfiStatus;
type OpenProtoFn   = unsafe extern "efiapi" fn(EfiHandle, *const Guid, *mut *const (), EfiHandle, EfiHandle, u32) -> EfiStatus;
type LocProtoFn    = unsafe extern "efiapi" fn(*const Guid, *const (), *mut *const ()) -> EfiStatus;

#[repr(C)]
struct BootServices {
    hdr:            EfiTableHdr,     // +0x00
    raise_tpl:      *const (),       // +0x18
    restore_tpl:    *const (),       // +0x20
    alloc_pages:    AllocPagesFn,    // +0x28
    free_pages:     FreePagesFn,     // +0x30
    get_mem_map:    GetMemMapFn,     // +0x38
    alloc_pool:     AllocPoolFn,     // +0x40
    free_pool:      FreePoolFn,      // +0x48
    create_event:   *const (),       // +0x50
    set_timer:      *const (),       // +0x58
    wait_event:     *const (),       // +0x60
    signal_event:   *const (),       // +0x68
    close_event:    *const (),       // +0x70
    check_event:    *const (),       // +0x78
    inst_proto:     *const (),       // +0x80
    reinst_proto:   *const (),       // +0x88
    uninst_proto:   *const (),       // +0x90
    handle_proto:   HandleProtoFn,   // +0x98
    _reserved:      *const (),       // +0xa0
    reg_notify:     *const (),       // +0xa8
    loc_handle:     *const (),       // +0xb0
    loc_dev_path:   *const (),       // +0xb8
    inst_cfg:       *const (),       // +0xc0
    load_image:     *const (),       // +0xc8
    start_image:    *const (),       // +0xd0
    exit:           *const (),       // +0xd8
    unload_image:   *const (),       // +0xe0
    exit_bs:        ExitBsFn,        // +0xe8
    get_monotonic:  *const (),       // +0xf0
    stall:          unsafe extern "efiapi" fn(usize) -> EfiStatus, // +0xf8
    set_watchdog:   *const (),       // +0x100
    connect_ctrl:   unsafe extern "efiapi" fn(EfiHandle, *const EfiHandle, *const (), u8) -> EfiStatus, // +0x108
    disconnect_ctrl:*const (),       // +0x110
    open_proto:     OpenProtoFn,     // +0x118
    close_proto:    *const (),       // +0x120
    open_proto_info:*const (),       // +0x128
    protos_per_hdl: *const (),       // +0x130
    loc_hdl_buf:    unsafe extern "efiapi" fn(u32, *const Guid, *const (), *mut usize, *mut *mut EfiHandle) -> EfiStatus, // +0x138
    loc_proto:      LocProtoFn,      // +0x140
}

// GOP
#[repr(C)]
struct GopModeInfo {
    version:     u32,
    h_res:       u32,
    v_res:       u32,
    pixel_fmt:   u32,  // 0=RGB, 1=BGR, 2=bitmask, 3=blt-only
    r_mask: u32, g_mask: u32, b_mask: u32, x_mask: u32,
    scan_px:     u32,
}
#[repr(C)]
struct GopMode {
    max_mode: u32, mode: u32,
    info:     *const GopModeInfo,
    info_sz:  usize,
    fb_base:  u64,
    fb_sz:    usize,
}
type GopSetMode = unsafe extern "efiapi" fn(*mut Gop, u32) -> EfiStatus;
#[repr(C)]
struct Gop {
    query_mode: *const (),
    set_mode:   GopSetMode,
    blt:        *const (),
    mode:       *const GopMode,
}

// LoadedImage
#[repr(C)]
struct LoadedImage {
    rev:         u32, _pad: u32,
    parent_hdl:  EfiHandle,
    system_tbl:  *const SystemTable,
    dev_hdl:     EfiHandle,
    file_path:   *const (),
    // ... (we only need dev_hdl)
}

// SimpleFileSystem + File
type SfsOpenVol = unsafe extern "efiapi" fn(*mut Sfs, *mut *mut File) -> EfiStatus;
#[repr(C)]
struct Sfs { rev: u64, open_volume: SfsOpenVol }

type FileOpen    = unsafe extern "efiapi" fn(*mut File, *mut *mut File, *const u16, u64, u64) -> EfiStatus;
type FileClose   = unsafe extern "efiapi" fn(*mut File) -> EfiStatus;
type FileRead    = unsafe extern "efiapi" fn(*mut File, *mut usize, *mut u8) -> EfiStatus;
type FileGetInfo = unsafe extern "efiapi" fn(*mut File, *const Guid, *mut usize, *mut u8) -> EfiStatus;
#[repr(C)]
struct File {
    rev:      u64,
    open:     FileOpen,
    close:    FileClose,
    _delete:  *const (),
    read:     FileRead,
    _write:   *const (),
    _get_pos: *const (),
    _set_pos: *const (),
    get_info: FileGetInfo,
}

// FileInfo (fixed prefix; variable-length name follows)
#[repr(C)]
struct FileInfo {
    struct_size:   u64,
    file_size:     u64,
    physical_size: u64,
    // 3 × EFI_TIME (each 16 bytes)
    create_time:   [u8; 16],
    access_time:   [u8; 16],
    modify_time:   [u8; 16],
    attribute:     u64,
    // CHAR16 filename follows
}

// ── BlockIo types ────────────────────────────────────────────────────────────

#[repr(C)]
struct BlockIoMedia {
    media_id:          u32,
    removable_media:   u8,
    media_present:     u8,
    logical_partition: u8,
    read_only:         u8,
    write_caching:     u8,
    _pad:              [u8; 3],
    block_size:        u32,
    io_align:          u32,
    last_block:        u64,
}

type BlockReadFn = unsafe extern "efiapi" fn(*mut BlockIo, u32, u64, usize, *mut u8) -> EfiStatus;

#[repr(C)]
struct BlockIo {
    revision:    u64,
    media:       *const BlockIoMedia,
    reset:       *const (),
    read_blocks: BlockReadFn,
}

// Static sector buffers — BlockIo requires stable (non-stack) memory for reads
// on some platforms; BSS memory is safe.
static mut SECTOR_BUF: [u8; 512]  = [0u8; 512];
static mut FAT_BUF:    [u8; 512]  = [0u8; 512];
static mut DIR_BUF:    [u8; 4096] = [0u8; 4096]; // one full cluster

// ── ELF64 types ───────────────────────────────────────────────────────────────

#[repr(C)]
struct Ehdr {
    ident:     [u8; 16],
    etype:     u16,
    machine:   u16,
    version:   u32,
    entry:     u64,
    phoff:     u64,
    shoff:     u64,
    flags:     u32,
    ehsize:    u16,
    phentsize: u16,
    phnum:     u16,
    shentsize: u16,
    shnum:     u16,
    shstrndx:  u16,
}

#[repr(C)]
struct Phdr {
    ptype:  u32,
    flags:  u32,
    offset: u64,
    vaddr:  u64,
    paddr:  u64,
    filesz: u64,
    memsz:  u64,
    align:  u64,
}

#[repr(C)]
struct Shdr {
    name:      u32,
    shtype:    u32,
    flags:     u64,
    addr:      u64,
    offset:    u64,
    size:      u64,
    link:      u32,
    info:      u32,
    addralign: u64,
    entsize:   u64,
}

const PT_LOAD: u32 = 1;
const ELF_MAGIC: [u8; 4] = [0x7f, b'E', b'L', b'F'];

// ── Memory map scratch buffer ─────────────────────────────────────────────────

const MMAP_SZ: usize = 32 * 1024;
// UEFI requires the memory descriptor buffer to be aligned to at least 8 bytes.
#[repr(align(8))]
struct MmapBuf { data: [u8; MMAP_SZ] }
static mut MMAP_BUF: MmapBuf = MmapBuf { data: [0u8; MMAP_SZ] };

// ── Entry ─────────────────────────────────────────────────────────────────────

#[no_mangle]
pub extern "efiapi" fn efi_main(
    image: EfiHandle,
    st:    *const SystemTable,
) -> EfiStatus {
    unsafe { main_inner(image, st) }
}

unsafe fn main_inner(image: EfiHandle, st: *const SystemTable) -> EfiStatus {
    let bs = (*st).boot_svc;
    say(st, b"DjinnOS loader\r\n");

    // ── GOP framebuffer ───────────────────────────────────────────────────────
    let mut gop_ptr: *const () = ptr::null();
    let r = ((*bs).loc_proto)(&GOP_GUID, ptr::null(), &mut gop_ptr);
    if r != SUCCESS || gop_ptr.is_null() {
        say(st, b"FAIL: no GOP\r\n"); return r;
    }
    say(st, b"GOP ok\r\n");
    let gop = gop_ptr as *const Gop;
    let mode = (*gop).mode;
    let info = (*mode).info;

    let pf = (*info).pixel_fmt;
    BOOT_INFO.fb_addr   = (*mode).fb_base;
    BOOT_INFO.fb_width  = (*info).h_res;
    BOOT_INFO.fb_height = (*info).v_res;
    BOOT_INFO.fb_pitch  = (*info).scan_px * 4;
    BOOT_INFO.r_pos = if pf == 1 { 16 } else { 0 };
    BOOT_INFO.g_pos = 8;
    BOOT_INFO.b_pos = if pf == 1 { 0 } else { 16 };

    // ── RSDP from configuration table ────────────────────────────────────────
    let n = (*st).n_cfg;
    let cfg = (*st).cfg_table;
    for i in 0..n {
        let e = &*cfg.add(i);
        if guid_eq(&e.guid, &ACPI20_GUID) {
            BOOT_INFO.rsdp_addr = e.table as u64; break;
        }
        if guid_eq(&e.guid, &ACPI10_GUID) && BOOT_INFO.rsdp_addr == 0 {
            BOOT_INFO.rsdp_addr = e.table as u64;
        }
    }
    say(st, b"RSDP ok\r\n");

    // ── Open EFI partition filesystem ─────────────────────────────────────────
    let mut li_ptr: *const () = ptr::null();
    let r = ((*bs).handle_proto)(image, &LI_GUID, &mut li_ptr);
    if r != SUCCESS { say(st, b"FAIL: LoadedImage\r\n"); return r; }
    let li = li_ptr as *const LoadedImage;

    // ── Reconnect storage drivers ─────────────────────────────────────────────
    // HP UEFI disconnects the FAT32 driver after loading the boot application.
    // Reconnect all controllers recursively so SFS protocols become visible.
    // ── Reconnect all controllers then scan all handles for SFS ──────────────
    const KNAME: &[u16] = &[
        b'\\' as u16, b'k' as u16, b'e' as u16, b'r' as u16, b'n' as u16,
        b'e' as u16,  b'l' as u16, b'.' as u16, b'e' as u16, b'l' as u16,
        b'f' as u16,  0,
    ];

    // ── Load kernel via BlockIo + raw FAT32 (HP disconnects SFS) ────────────
    say(st, b"BlockIo scan...\r\n");
    let mut n_bio: usize = 0;
    let mut bio_hdls: *mut EfiHandle = ptr::null_mut();
    let r = ((*bs).loc_hdl_buf)(2, &BLOCKIO_GUID, ptr::null(),
                                  &mut n_bio, &mut bio_hdls);
    if r != SUCCESS { say(st, b"FAIL: no BlockIo\r\n"); return r; }
    say(st, b"BlockIo n="); say_hex(st, n_bio as u64);

    let mut kbuf: *mut u8 = ptr::null_mut();
    let mut fsize: usize = 0;

    'bio: for i in 0..n_bio {
        let h = *bio_hdls.add(i);
        let mut bio_ptr: *const () = ptr::null();
        if ((*bs).handle_proto)(h, &BLOCKIO_GUID, &mut bio_ptr) != SUCCESS { continue; }
        let bio = bio_ptr as *mut BlockIo;
        let media = (*bio).media;
        if (*media).media_present == 0 { continue; }
        let mid = (*media).media_id;

        // Read LBA 0: check for FAT32 BPB with our volume label
        if ((*bio).read_blocks)(bio, mid, 0, 512,
                                 SECTOR_BUF.as_mut_ptr()) != SUCCESS { continue; }
        let s = &SECTOR_BUF;
        if s[510] != 0x55 || s[511] != 0xAA { continue; }
        if &s[82..90] != b"FAT32   " { continue; }
        // No volume label check — Rufus may set any label.

        say(st, b"FAT32 volume found\r\n");

        // Parse BPB
        let spc        = s[13] as u64;  // sectors per cluster
        let reserved   = u16::from_le_bytes([s[14], s[15]]) as u64;
        let num_fats   = s[16] as u64;
        let fat32_sz   = u32::from_le_bytes([s[36], s[37], s[38], s[39]]) as u64;
        let root_clust = u32::from_le_bytes([s[44], s[45], s[46], s[47]]) as u64;
        let fat_start  = reserved;
        let data_start = reserved + num_fats * fat32_sz;

        // Read root directory (one sector of first cluster)
        let root_lba = data_start + (root_clust - 2) * spc;
        if ((*bio).read_blocks)(bio, mid, root_lba, 4096,
                                 DIR_BUF.as_mut_ptr()) != SUCCESS { continue; }

        // Find KERNEL.ELF directory entry
        let mut first_cluster: u32 = 0;
        let mut file_size: u32 = 0;
        let mut j = 0;
        while j + 32 <= 4096 {
            let e = &DIR_BUF[j..j+32];
            if e[0] == 0 { break; }
            if e[0] == 0xE5 || e[11] & 0x0F == 0x0F { j += 32; continue; }
            if &e[0..8] == b"KERNEL  " && &e[8..11] == b"ELF" {
                let hi = u16::from_le_bytes([e[20], e[21]]) as u32;
                let lo = u16::from_le_bytes([e[26], e[27]]) as u32;
                first_cluster = (hi << 16) | lo;
                file_size = u32::from_le_bytes([e[28], e[29], e[30], e[31]]);
                break;
            }
            j += 32;
        }

        if first_cluster == 0 {
            say(st, b"kernel.elf not in dir\r\n"); continue;
        }
        say(st, b"kernel.elf dir entry found\r\n");

        // Allocate pool buffer for the kernel
        fsize = file_size as usize;
        let r = ((*bs).alloc_pool)(EFI_LOADER_DATA, fsize, &mut kbuf);
        if r != SUCCESS { say(st, b"FAIL: alloc_pool\r\n"); return r; }

        // Read kernel following FAT32 cluster chain
        let mut offset: usize = 0;
        let mut cur = first_cluster;
        while offset < fsize && cur < 0x0FFF_FFF8 {
            let clust_lba = data_start + (cur as u64 - 2) * spc;
            for s_idx in 0..spc {
                if offset >= fsize { break; }
                if ((*bio).read_blocks)(bio, mid, clust_lba + s_idx, 512,
                                         SECTOR_BUF.as_mut_ptr()) != SUCCESS { break; }
                let n = 512usize.min(fsize - offset);
                ptr::copy_nonoverlapping(SECTOR_BUF.as_ptr(), kbuf.add(offset), n);
                offset += n;
            }
            // Next cluster from FAT
            let fat_byte  = (cur as u64) * 4;
            let fat_lba   = fat_start + fat_byte / 512;
            let fat_off   = (fat_byte % 512) as usize;
            if ((*bio).read_blocks)(bio, mid, fat_lba, 512,
                                     FAT_BUF.as_mut_ptr()) != SUCCESS { break; }
            cur = u32::from_le_bytes([FAT_BUF[fat_off], FAT_BUF[fat_off+1],
                                       FAT_BUF[fat_off+2], FAT_BUF[fat_off+3]])
                  & 0x0FFF_FFFF;
        }
        say(st, b"kernel read ok\r\n");
        break 'bio;
    }
    ((*bs).free_pool)(bio_hdls as *mut u8);

    if kbuf.is_null() { say(st, b"FAIL: kernel not found on any BlockIo\r\n"); return 1; }

    // ── Validate ELF ─────────────────────────────────────────────────────────
    let ehdr = &*(kbuf as *const Ehdr);
    if ehdr.ident[..4] != ELF_MAGIC {
        say(st, b"FAIL: bad ELF magic\r\n"); return 1;
    }
    if ehdr.machine != 0x3E {
        say(st, b"FAIL: not x86_64 ELF\r\n"); return 1;
    }
    say(st, b"ELF ok\r\n");

    // ── Load PT_LOAD segments into physical memory ────────────────────────────
    say(st, b"loading segments...\r\n");
    for i in 0..ehdr.phnum as usize {
        let phdr = &*(kbuf.add(ehdr.phoff as usize + i * ehdr.phentsize as usize)
                       as *const Phdr);
        if phdr.ptype != PT_LOAD || phdr.memsz == 0 { continue; }
        let pages = (phdr.memsz as usize + 0xFFF) / 0x1000;
        let mut paddr = phdr.paddr;
        let _ = ((*bs).alloc_pages)(ALLOCATE_ADDRESS, EFI_LOADER_CODE, pages, &mut paddr);
        ptr::copy_nonoverlapping(
            kbuf.add(phdr.offset as usize),
            phdr.paddr as *mut u8,
            phdr.filesz as usize,
        );
        if phdr.memsz > phdr.filesz {
            ptr::write_bytes(
                (phdr.paddr + phdr.filesz) as *mut u8,
                0,
                (phdr.memsz - phdr.filesz) as usize,
            );
        }
    }
    say(st, b"segments ok\r\n");

    // ── Find kernel_uefi_entry via .uefi_hdr section ─────────────────────────
    let shstrtab_hdr = &*(kbuf.add(
        ehdr.shoff as usize + ehdr.shstrndx as usize * ehdr.shentsize as usize
    ) as *const Shdr);
    let shstrtab = core::slice::from_raw_parts(
        kbuf.add(shstrtab_hdr.offset as usize),
        shstrtab_hdr.size as usize,
    );

    let mut entry_addr: u64 = 0;
    for i in 0..ehdr.shnum as usize {
        let shdr = &*(kbuf.add(ehdr.shoff as usize + i * ehdr.shentsize as usize)
                       as *const Shdr);
        let n = shdr.name as usize;
        if n + 9 <= shstrtab.len() && &shstrtab[n..n+9] == b".uefi_hdr" {
            entry_addr = *(shdr.addr as *const u64);
            break;
        }
    }
    if entry_addr == 0 {
        say(st, b"FAIL: .uefi_hdr not found\r\n"); return 1;
    }
    say(st, b"entry="); say_hex(st, entry_addr);

    // Paint framebuffer green to confirm GOP address is correct
    {
        let fb   = BOOT_INFO.fb_addr as *mut u32;
        let rows = BOOT_INFO.fb_height as usize;
        let cols = (BOOT_INFO.fb_pitch / 4) as usize;
        for row in 0..rows { for col in 0..cols {
            fb.add(row * cols + col).write_volatile(0x0000_3300);
        }}
    }
    say(st, b"fb painted green - if screen is dark fb_addr is wrong\r\n");
    say(st, b"fb_addr="); say_hex(st, BOOT_INFO.fb_addr);
    say(st, b"fb_w=");    say_hex(st, BOOT_INFO.fb_width as u64);
    say(st, b"fb_h=");    say_hex(st, BOOT_INFO.fb_height as u64);

    ((*bs).free_pool)(kbuf);

    // ExitBootServices retry loop — the memory map key can go stale between
    // GetMemoryMap and ExitBootServices if a UEFI timer callback fires.
    // Spec-recommended pattern: retry until SUCCESS.
    loop {
        let mut sz:  usize = MMAP_SZ;
        let mut key: usize = 0;
        let mut ds:  usize = 0;
        let mut ver: u32   = 0;
        ((*bs).get_mem_map)(
            &mut sz, MMAP_BUF.data.as_mut_ptr(), &mut key, &mut ds, &mut ver,
        );
        let r = ((*bs).exit_bs)(image, key);
        if r == SUCCESS { break; }
        // Print error so we can see what HP's firmware returns.
        say(st, b"ExitBS="); say_hex(st, r as u64);
        // EFI_INVALID_PARAMETER (0x...0002) = stale key, retry.
        // Anything else is fatal — print and bail.
        if r != 0x8000_0000_0000_0002 {
            say(st, b"FAIL: ExitBootServices fatal\r\n");
            return r;
        }
    }

    // Jump to kernel (SysV64: arg0 in RDI)
    let info_ptr = core::ptr::addr_of!(BOOT_INFO) as u64;
    core::arch::asm!(
        "cli",
        "mov rdi, {info}",
        "jmp {entry}",
        info  = in(reg) info_ptr,
        entry = in(reg) entry_addr,
        options(noreturn, nostack),
    );
}

/// Call GetMemoryMap to obtain the current map key (needed by ExitBootServices).
unsafe fn get_map_key(bs: *const BootServices) -> usize {
    let mut sz:   usize = MMAP_SZ;
    let mut key:  usize = 0;
    let mut desc: usize = 0;
    let mut ver:  u32   = 0;
    // First call may return BUFFER_TOO_SMALL; that still fills in `key`.
    ((*bs).get_mem_map)(
        &mut sz,
        core::ptr::addr_of_mut!(MMAP_BUF.data) as *mut u8,
        &mut key,
        &mut desc,
        &mut ver,
    );
    key
}

// ── Panic handler (required for no_std) ──────────────────────────────────────

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }
