// RAM disk — files loaded by the UEFI loader before ExitBootServices.
//
// The loader scans the root FAT32 directory on the boot USB and reads every
// regular file (≤ 8 MiB, excluding KERNEL.ELF) into pool-allocated RAM.
// It passes a pointer to the flat file table via UefiBootInfo.
//
// Table layout (matches djinnos-loader RD_TABLE):
//   Each entry is 48 bytes:
//     name[32]  — lowercase null-terminated 8.3 name ("readme.txt")
//     data[8]   — u64 little-endian physical address of file bytes
//     size[4]   — u32 little-endian byte count
//     _pad[4]

// Embedded read-only filesystem — files baked into the kernel binary at
// compile time.  No USB scanning, no FAT32 geometry issues.
// The loader's ramdisk (UefiBootInfo.ramdisk_addr) supplements these with
// any files it found on the boot USB; embedded files are always available.

struct EmbeddedFile {
    name: &'static [u8],
    data: &'static [u8],
}

static EMBEDDED: &[EmbeddedFile] = &[
    EmbeddedFile {
        name: b"selfspec.ko",
        data: include_bytes!(
            "../../DjinnOS_Shyagzun/shygazun/sanctum/charters/selfspec.ko"
        ),
    },
    EmbeddedFile {
        name: b"koslbryn.ko",
        data: include_bytes!(
            "../../DjinnOS_Shyagzun/shygazun/sanctum/koslbryn.ko"
        ),
    },
];

// ── Loader ramdisk (USB files, may be empty) ──────────────────────────────────

#[repr(C)]
pub struct RamFile {
    pub name: [u8; 32],
    pub data: u64,
    pub size: u32,
    pub _pad: u32,
}

static mut USB_TABLE: *const RamFile = core::ptr::null();
static mut USB_COUNT: u32 = 0;

pub fn init(addr: u64, count: u32) {
    unsafe {
        USB_TABLE = addr as *const RamFile;
        USB_COUNT = count;
    }
}

// ── Unified accessors (embedded first, then USB) ──────────────────────────────

pub fn file_count() -> usize {
    unsafe { EMBEDDED.len() + USB_COUNT as usize }
}

pub struct FileRef {
    pub name: &'static [u8],
    pub data: &'static [u8],
}

pub fn get(i: usize) -> Option<FileRef> {
    if i < EMBEDDED.len() {
        let f = &EMBEDDED[i];
        return Some(FileRef { name: f.name, data: f.data });
    }
    let j = i - EMBEDDED.len();
    unsafe {
        if USB_TABLE.is_null() || j >= USB_COUNT as usize { return None; }
        let f = &*USB_TABLE.add(j);
        let nlen = f.name.iter().position(|&b| b == 0).unwrap_or(32);
        let dlen = f.size as usize;
        Some(FileRef {
            name: core::slice::from_raw_parts(f.name.as_ptr(), nlen),
            data: core::slice::from_raw_parts(f.data as *const u8, dlen),
        })
    }
}

pub fn find(name: &[u8]) -> Option<&'static [u8]> {
    // Volatile edit slot takes priority over embedded/USB copies.
    unsafe {
        if EDIT_ACTIVE && &EDIT_NAME[..EDIT_NAME_N] == name {
            return Some(core::slice::from_raw_parts(EDIT_DATA.as_ptr(), EDIT_DATA_N));
        }
    }
    for f in EMBEDDED {
        if f.name == name { return Some(f.data); }
    }
    unsafe {
        for i in 0..USB_COUNT as usize {
            let f = &*USB_TABLE.add(i);
            let nlen = f.name.iter().position(|&b| b == 0).unwrap_or(32);
            if &f.name[..nlen] == name {
                return Some(core::slice::from_raw_parts(
                    f.data as *const u8, f.size as usize));
            }
        }
    }
    None
}

pub fn name_str(f: &RamFile) -> &[u8] {
    let len = f.name.iter().position(|&b| b == 0).unwrap_or(32);
    &f.name[..len]
}

// ── Volatile edit slot — written by the in-kernel editor, overrides find() ───

static mut EDIT_ACTIVE: bool    = false;
static mut EDIT_NAME:   [u8; 32] = [0u8; 32];
static mut EDIT_NAME_N: usize   = 0;
static mut EDIT_DATA:   [u8; 8192] = [0u8; 8192];
static mut EDIT_DATA_N: usize   = 0;

/// Write (or overwrite) the volatile edit slot for `name`.
/// The editor calls this on save; `find()` returns it in preference to
/// the embedded/USB copy.
pub fn write_edit(name: &[u8], data: &[u8]) {
    unsafe {
        let nn = name.len().min(31);
        EDIT_NAME[..nn].copy_from_slice(&name[..nn]);
        EDIT_NAME_N = nn;
        let dn = data.len().min(8192);
        EDIT_DATA[..dn].copy_from_slice(&data[..dn]);
        EDIT_DATA_N = dn;
        EDIT_ACTIVE = true;
    }
}