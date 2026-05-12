// gpt.rs — GPT partition table reader.
//
// Reads LBA 1 (the GPT header) and the partition entry array that follows.
// Used by the installer to locate the EFI System Partition on the NVMe drive.
//
// Only reads — never writes the partition table.

use crate::uart;

// ── GPT header (LBA 1, first 92 bytes are the standard header) ───────────────

const GPT_SIGNATURE: u64 = 0x5452_4150_2049_4645; // "EFI PART"

#[repr(C)]
struct GptHeader {
    signature:      u64,
    revision:       u32,
    header_size:    u32,
    header_crc32:   u32,
    _reserved:      u32,
    my_lba:         u64,
    alt_lba:        u64,
    first_usable:   u64,
    last_usable:    u64,
    disk_guid:      [u8; 16],
    part_entry_lba: u64,
    n_parts:        u32,
    part_entry_sz:  u32,
    parts_crc32:    u32,
}

// ── GPT partition entry (128 bytes) ──────────────────────────────────────────

// EFI System Partition type GUID (mixed-endian as stored on disk):
//   C12A7328-F81F-11D2-BA4B-00A0C93EC93B
const ESP_TYPE_GUID: [u8; 16] = [
    0x28, 0x73, 0x2A, 0xC1,  // C12A7328 (little-endian u32)
    0x1F, 0xF8,              // F81F (little-endian u16)
    0xD2, 0x11,              // 11D2 (big-endian u16)
    0xBA, 0x4B,              // BA4B
    0x00, 0xA0, 0xC9, 0x3E, 0xC9, 0x3B,
];

pub struct Partition {
    pub start_lba: u64,
    pub end_lba:   u64,   // inclusive
    pub is_esp:    bool,
}

// ── Public: find EFI System Partition ────────────────────────────────────────

/// Scan the GPT and return the ESP partition info, or None if not found.
pub fn find_esp() -> Option<Partition> {
    unsafe { find_esp_inner() }
}

unsafe fn find_esp_inner() -> Option<Partition> {
    // Read LBA 1 → GPT header.
    if !crate::nvme::read_lba(1) {
        uart::puts("gpt: failed to read LBA 1\r\n");
        return None;
    }

    let hdr = &*(crate::nvme::XFER.data.as_ptr() as *const GptHeader);
    if hdr.signature != GPT_SIGNATURE {
        uart::puts("gpt: bad signature\r\n");
        return None;
    }

    let n     = hdr.n_parts as u64;
    let esz   = hdr.part_entry_sz as u64;  // typically 128
    let elba  = hdr.part_entry_lba;
    let lba_sz = crate::nvme::lba_size() as u64;

    uart::puts("gpt: n_parts=");
    uart::putu(n);
    uart::puts(" entry_lba=");
    uart::putu(elba);
    uart::puts("\r\n");

    if esz < 128 || esz > 512 {
        uart::puts("gpt: unexpected entry size\r\n");
        return None;
    }

    // Walk partition entries — they are packed into sectors starting at elba.
    let entries_per_lba = (lba_sz / esz).max(1);
    let mut idx: u64 = 0;

    while idx < n {
        let lba = elba + idx / entries_per_lba;
        if !crate::nvme::read_lba(lba) { return None; }

        let batch_start = idx;
        let batch_end   = (batch_start + entries_per_lba).min(n);

        for i in batch_start..batch_end {
            let off = ((i - batch_start) * esz) as usize;
            if off + 128 > crate::nvme::XFER.data.len() { break; }
            let entry = &crate::nvme::XFER.data[off..off + 128];

            // Bytes 0–15: partition type GUID.
            if entry[0..16] == ESP_TYPE_GUID {
                let start = u64::from_le_bytes(entry[32..40].try_into().unwrap_or([0;8]));
                let end   = u64::from_le_bytes(entry[40..48].try_into().unwrap_or([0;8]));
                uart::puts("gpt: ESP found start=");
                uart::putu(start);
                uart::puts(" end=");
                uart::putu(end);
                uart::puts("\r\n");
                return Some(Partition { start_lba: start, end_lba: end, is_esp: true });
            }
        }
        idx = batch_end;
    }

    uart::puts("gpt: no ESP found\r\n");
    None
}
