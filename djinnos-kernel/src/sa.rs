// Sa volume — in-RAM block device for x86_64.
//
// The volume is a flat byte array formatted as the Sa disk image defined
// in fs.rs.  All sector reads and writes operate on the static buffer.
//
// Disk layout (matches fs.rs exactly):
//   Sector 0       : Sa header  (magic, volume name, file count, next_free)
//   Sectors 1–16   : Seth directory (128 SaoEntries × 64 bytes each)
//   Sector 17+     : Sao file data
//
// Session persistence: changes survive until reboot.
// Reboot persistence: requires NVMe or USB write-back driver (Phase 2).
//   On the next boot the loader can read SA.VOL from USB FAT32 and pass
//   the image pointer to the kernel via UefiBootInfo (sa_addr / sa_size).
//
// Sector allocator: linear append.  Files are written at next_free_sector,
// which advances monotonically.  For updates that fit in the same sector
// count the data is updated in-place; larger updates append and redirect
// the directory entry.  The old sectors are orphaned (no compaction yet).

// ── Constants ─────────────────────────────────────────────────────────────────

pub const SA_MAGIC:        &[u8; 8] = b"DJINNOS\0";
pub const SECTOR:          usize    = 512;
pub const MAX_FILES:       usize    = 128;
pub const SETH_SECTORS:    usize    = 16;
pub const DATA_START_SEC:  usize    = 1 + SETH_SECTORS; // sector 17
pub const SAO_ENTRY_SIZE:  usize    = 64;
pub const ENTRIES_PER_SEC: usize    = SECTOR / SAO_ENTRY_SIZE; // 8

/// Total in-RAM volume size.  4 MiB covers game state, .ko files,
/// authoring data, and short audio clips.  Extend for voiced dialogue.
pub const SA_SIZE_BYTES: usize = 4 * 1024 * 1024;
pub const SA_SIZE_SECS:  usize = SA_SIZE_BYTES / SECTOR;  // 8192

// ── Static buffer ─────────────────────────────────────────────────────────────

static mut SA_BUF:  [u8; SA_SIZE_BYTES] = [0u8; SA_SIZE_BYTES];
static mut SA_INIT: bool                = false;

// ── Directory entry ───────────────────────────────────────────────────────────

#[derive(Clone, Copy, Default)]
pub struct SaoEntry {
    pub name:  [u8; 32],
    pub start: u32,  // first data sector
    pub len:   u32,  // file length in bytes
}

impl SaoEntry {
    pub fn name_bytes(&self) -> &[u8] {
        let end = self.name.iter().position(|&b| b == 0).unwrap_or(32);
        &self.name[..end]
    }
    pub fn is_empty(&self) -> bool { self.len == 0 && self.name[0] == 0 }
}

// ── Sector I/O on the static buffer ──────────────────────────────────────────

pub fn read_sector(n: usize, buf: &mut [u8; SECTOR]) -> bool {
    let off = n * SECTOR;
    if off + SECTOR > SA_SIZE_BYTES { return false; }
    buf.copy_from_slice(unsafe { &SA_BUF[off..off + SECTOR] });
    true
}

pub fn write_sector(n: usize, buf: &[u8; SECTOR]) -> bool {
    let off = n * SECTOR;
    if off + SECTOR > SA_SIZE_BYTES { return false; }
    unsafe { SA_BUF[off..off + SECTOR].copy_from_slice(buf); }
    true
}

// ── Header access ─────────────────────────────────────────────────────────────

fn read_header() -> (u32, u32) {
    // Returns (file_count, next_free_sector).
    let off = 0usize;
    let buf = unsafe { &SA_BUF[off..off + SECTOR] };
    let count = u32::from_le_bytes([buf[40], buf[41], buf[42], buf[43]]);
    let next  = u32::from_le_bytes([buf[44], buf[45], buf[46], buf[47]]);
    let next  = if next < DATA_START_SEC as u32 { DATA_START_SEC as u32 } else { next };
    (count, next)
}

fn write_header(count: u32, next_free: u32) {
    let buf = unsafe { &mut SA_BUF[0..SECTOR] };
    buf[0..8].copy_from_slice(SA_MAGIC);
    buf[40..44].copy_from_slice(&count.to_le_bytes());
    buf[44..48].copy_from_slice(&next_free.to_le_bytes());
}

// ── Directory I/O ─────────────────────────────────────────────────────────────

fn read_entry(index: usize) -> SaoEntry {
    let sec  = 1 + index / ENTRIES_PER_SEC;
    let slot = index % ENTRIES_PER_SEC;
    let off  = sec * SECTOR + slot * SAO_ENTRY_SIZE;
    if off + SAO_ENTRY_SIZE > SA_SIZE_BYTES { return SaoEntry::default(); }
    let src = unsafe { &SA_BUF[off..off + SAO_ENTRY_SIZE] };
    let mut name = [0u8; 32];
    name.copy_from_slice(&src[0..32]);
    let start = u32::from_le_bytes([src[32], src[33], src[34], src[35]]);
    let len   = u32::from_le_bytes([src[36], src[37], src[38], src[39]]);
    SaoEntry { name, start, len }
}

fn write_entry(index: usize, e: &SaoEntry) {
    let sec  = 1 + index / ENTRIES_PER_SEC;
    let slot = index % ENTRIES_PER_SEC;
    let off  = sec * SECTOR + slot * SAO_ENTRY_SIZE;
    if off + SAO_ENTRY_SIZE > SA_SIZE_BYTES { return; }
    let dst = unsafe { &mut SA_BUF[off..off + SAO_ENTRY_SIZE] };
    dst[0..32].copy_from_slice(&e.name);
    dst[32..36].copy_from_slice(&e.start.to_le_bytes());
    dst[36..40].copy_from_slice(&e.len.to_le_bytes());
    dst[40..SAO_ENTRY_SIZE].fill(0);
}

fn find_entry_index(name: &[u8]) -> Option<usize> {
    let (count, _) = read_header();
    for i in 0..count.min(MAX_FILES as u32) as usize {
        let e = read_entry(i);
        if e.name_bytes() == name { return Some(i); }
    }
    None
}

// ── Initialisation ────────────────────────────────────────────────────────────

/// Initialise an empty Sa volume.  Called if no SA.VOL was found on the USB.
pub fn init_empty(vol_name: &[u8]) {
    unsafe {
        SA_BUF.fill(0);
        let buf = &mut SA_BUF[0..SECTOR];
        buf[0..8].copy_from_slice(SA_MAGIC);
        let nlen = vol_name.len().min(32);
        buf[8..8 + nlen].copy_from_slice(&vol_name[..nlen]);
        SA_INIT = true;
    }
    write_header(0, DATA_START_SEC as u32);
}

/// Load a pre-existing Sa image from a raw byte slice.
/// Called by the UEFI boot path when the loader found SA.VOL on the USB.
pub fn load_image(data: &[u8]) {
    let copy = data.len().min(SA_SIZE_BYTES);
    unsafe {
        SA_BUF[..copy].copy_from_slice(&data[..copy]);
        if copy < SA_SIZE_BYTES { SA_BUF[copy..].fill(0); }
        // Validate magic; fall back to empty if corrupt.
        if &SA_BUF[0..8] != SA_MAGIC {
            SA_BUF.fill(0);
            init_empty(b"DjinnOS");
        }
        SA_INIT = true;
    }
}

pub fn is_init() -> bool { unsafe { SA_INIT } }

// ── High-level read/write API ─────────────────────────────────────────────────

/// Read a file into `out`.  Returns bytes read, 0 if not found.
pub fn read_file(name: &[u8], out: &mut [u8]) -> usize {
    let idx = match find_entry_index(name) { Some(i) => i, None => return 0 };
    let e   = read_entry(idx);
    let len = (e.len as usize).min(out.len());
    let off = e.start as usize * SECTOR;
    if off + len > SA_SIZE_BYTES { return 0; }
    out[..len].copy_from_slice(unsafe { &SA_BUF[off..off + len] });
    len
}

/// Write or create a file.  Returns true on success.
///
/// Update strategy:
///   - Existing file, data fits in same sector count: update in-place.
///   - Existing file, data is larger: append new data, redirect entry.
///   - New file: append data, create entry.
pub fn write_file(name: &[u8], data: &[u8]) -> bool {
    if !unsafe { SA_INIT } { return false; }
    let (mut count, mut next_free) = read_header();

    let secs_needed = (data.len() + SECTOR - 1) / SECTOR;
    let idx = find_entry_index(name);

    let (start_sec, entry_idx) = match idx {
        Some(i) => {
            let e = read_entry(i);
            let secs_have = (e.len as usize + SECTOR - 1) / SECTOR;
            if secs_needed <= secs_have {
                // Fits in existing allocation — update in-place.
                (e.start as usize, i)
            } else {
                // Need more space — append and redirect.
                let s = next_free as usize;
                next_free += secs_needed as u32;
                (s, i)
            }
        }
        None => {
            // New file — append.
            if count >= MAX_FILES as u32 { return false; }
            let s = next_free as usize;
            next_free += secs_needed as u32;
            let i = count as usize;
            count += 1;
            (s, i)
        }
    };

    // Bounds check
    if (start_sec + secs_needed) * SECTOR > SA_SIZE_BYTES { return false; }

    // Write data
    let dst_off = start_sec * SECTOR;
    unsafe {
        SA_BUF[dst_off..dst_off + data.len()].copy_from_slice(data);
        // Zero-pad the last partial sector.
        let tail = data.len() % SECTOR;
        if tail != 0 {
            let pad_start = dst_off + data.len();
            let pad_end   = pad_start + (SECTOR - tail);
            if pad_end <= SA_SIZE_BYTES {
                SA_BUF[pad_start..pad_end].fill(0);
            }
        }
    }

    // Write directory entry.
    let mut ename = [0u8; 32];
    let nlen = name.len().min(32);
    ename[..nlen].copy_from_slice(&name[..nlen]);
    write_entry(entry_idx, &SaoEntry {
        name:  ename,
        start: start_sec as u32,
        len:   data.len() as u32,
    });

    write_header(count, next_free);
    true
}

/// Delete a file by zeroing its directory entry and decrementing count.
/// Does not reclaim data sectors (no compaction in Phase 1).
pub fn delete_file(name: &[u8]) -> bool {
    let idx = match find_entry_index(name) { Some(i) => i, None => return false };
    let (count, next_free) = read_header();
    write_entry(idx, &SaoEntry::default());
    // Compact: move last entry into the vacated slot if not already last.
    let last = count.saturating_sub(1) as usize;
    if idx != last {
        let last_e = read_entry(last);
        write_entry(idx, &last_e);
        write_entry(last, &SaoEntry::default());
    }
    write_header(count.saturating_sub(1), next_free);
    true
}

/// List all files via callback.
pub fn for_each(mut f: impl FnMut(&[u8], u32)) {
    let (count, _) = read_header();
    for i in 0..count.min(MAX_FILES as u32) as usize {
        let e = read_entry(i);
        if !e.is_empty() { f(e.name_bytes(), e.len); }
    }
}

/// Number of files currently in the volume.
pub fn file_count() -> u32 { read_header().0 }

/// Bytes used by file data (approximate — includes orphaned sectors).
pub fn bytes_used() -> u32 {
    let (_, next_free) = read_header();
    next_free.saturating_sub(DATA_START_SEC as u32) * SECTOR as u32
}

/// Bytes remaining before the volume is full.
pub fn bytes_free() -> u32 {
    let used = bytes_used();
    let cap  = (SA_SIZE_BYTES - DATA_START_SEC * SECTOR) as u32;
    cap.saturating_sub(used)
}

/// Return a raw slice of the full volume image.
/// Used by the loader write-back path when NVMe/USB persistence is available.
pub fn image() -> &'static [u8] {
    unsafe { &SA_BUF[..SA_SIZE_BYTES] }
}