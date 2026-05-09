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