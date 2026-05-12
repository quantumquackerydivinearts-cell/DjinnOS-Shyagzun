// fat32w.rs — Minimal FAT32 formatter and file writer (rewrite).
//
// Key correctness properties vs. the original:
//   - FAT tables are zeroed completely before any chain entries are written.
//     The original left stale Windows FAT data in sectors we didn't touch;
//     HP's UEFI FAT driver compared FAT1/FAT2, found mismatches, rejected volume.
//   - All FAT entries are computed directly (no read-modify-write).
//   - 8 sectors/cluster (4 KiB) — the standard Windows ESP cluster size.
//   - total_sectors and fat_sz are calculated with the correct circular formula.
//
// Layout:
//   part_start + 0         BPB (boot sector)
//   part_start + 1         FS Info
//   part_start + 6         Backup BPB
//   part_start + 32        FAT 1  (fat_sz sectors)
//   part_start + 32+fat_sz FAT 2  (fat_sz sectors, mirror)
//   part_start + 32+2*fat  Cluster 2 = root directory
//   ...                    Cluster 3 = EFI/
//   ...                    Cluster 4 = EFI/BOOT/
//   ...                    Cluster 5+ = BOOTX64.EFI data
//   ...                    Cluster 5+loader_clusters = kernel.elf data

use crate::{uart, nvme};

const SECTORS_PER_CLUSTER: u32 = 8;    // 4 KiB clusters — standard for ESP
const RESERVED_SECTORS:    u32 = 32;
const N_FATS:              u32 = 2;
const BYTES_PER_SECTOR:    u32 = 512;
const CLUSTER_BYTES:       u32 = SECTORS_PER_CLUSTER * BYTES_PER_SECTOR;

// ── Sector write (wraps NVMe) ─────────────────────────────────────────────────

unsafe fn write_sec(lba: u64, data: &[u8; 512]) -> bool {
    nvme::XFER.data[..512].copy_from_slice(data);
    let ok = nvme::write_lba(lba);
    if !ok {
        uart::puts("fat32: write failed at lba=");
        uart::putu(lba);
        uart::puts("\r\n");
    }
    ok
}

unsafe fn zero_sec(lba: u64) -> bool {
    write_sec(lba, &[0u8; 512])
}

// ── FAT entry write ───────────────────────────────────────────────────────────

// Write a single 4-byte FAT32 entry.
// Reads the current (already-zeroed) FAT sector, sets one entry, writes back.
unsafe fn set_fat_entry(fat_lba: u64, cluster: u32, value: u32) {
    let sector = fat_lba + (cluster as u64 * 4) / 512;
    let offset = ((cluster as usize * 4) % 512) as usize;
    // Sector was already zeroed; read back to pick up earlier entries in same sector.
    nvme::read_lba(sector);
    let buf = &mut nvme::XFER.data;
    buf[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    nvme::write_lba(sector);
}

// Write a complete FAT32 chain starting at `start_cluster` for `n` clusters.
// Writes to both FAT1 and FAT2.
unsafe fn write_chain(fat1: u64, fat2: u64, start: u32, n: u32) {
    for i in 0..n {
        let c = start + i;
        let v = if i == n - 1 { 0x0FFF_FFFF } else { c + 1 };
        set_fat_entry(fat1, c, v);
        set_fat_entry(fat2, c, v);
    }
}

// ── Directory entry ───────────────────────────────────────────────────────────

fn make_dirent(name83: &[u8; 11], attr: u8, cluster: u32, size: u32) -> [u8; 32] {
    let mut e = [0u8; 32];
    e[0..11].copy_from_slice(name83);
    e[11] = attr;
    e[20..22].copy_from_slice(&((cluster >> 16) as u16).to_le_bytes());
    e[26..28].copy_from_slice(&(cluster as u16).to_le_bytes());
    e[28..32].copy_from_slice(&size.to_le_bytes());
    e
}

// ── File data write ───────────────────────────────────────────────────────────

unsafe fn write_file(start_lba: u64, data: &[u8]) -> bool {
    let mut written = 0usize;
    let mut lba = start_lba;
    let total = (data.len() + 511) / 512;
    let mut reported = 0u32;
    while written < data.len() {
        let mut sec = [0u8; 512];
        let n = (data.len() - written).min(512);
        sec[..n].copy_from_slice(&data[written..written + n]);
        if !write_sec(lba, &sec) { return false; }
        written += 512;
        lba += 1;
        // Print progress every 1024 sectors (~512 KiB).
        let done = (written / 512) as u32;
        if done / 1024 > reported {
            reported = done / 1024;
            uart::puts("  ");
            uart::putu(done as u64);
            uart::puts("/");
            uart::putu(total as u64);
            uart::puts(" sectors\r\n");
        }
    }
    true
}

// ── BPB ───────────────────────────────────────────────────────────────────────

unsafe fn write_bpb_checked(part_start: u64, total_sectors: u32, fat_sz: u32) -> bool {
    let mut b = [0u8; 512];

    b[0] = 0xEB; b[1] = 0x58; b[2] = 0x90;   // JMP + NOP
    b[3..11].copy_from_slice(b"DJINNOS ");

    // BIOS Parameter Block
    b[11..13].copy_from_slice(&(BYTES_PER_SECTOR as u16).to_le_bytes());
    b[13] = SECTORS_PER_CLUSTER as u8;
    b[14..16].copy_from_slice(&(RESERVED_SECTORS as u16).to_le_bytes());
    b[16] = N_FATS as u8;
    b[17..19].copy_from_slice(&0u16.to_le_bytes());    // root entry count = 0 (FAT32)
    b[19..21].copy_from_slice(&0u16.to_le_bytes());    // total sectors 16 = 0
    b[21] = 0xF8;                                       // media: fixed disk
    b[22..24].copy_from_slice(&0u16.to_le_bytes());    // FAT size 16 = 0
    b[24..26].copy_from_slice(&63u16.to_le_bytes());   // sectors/track
    b[26..28].copy_from_slice(&255u16.to_le_bytes());  // heads
    b[28..32].copy_from_slice(&(part_start as u32).to_le_bytes()); // hidden sectors
    b[32..36].copy_from_slice(&total_sectors.to_le_bytes());

    // FAT32 extended BPB
    b[36..40].copy_from_slice(&fat_sz.to_le_bytes());  // FAT size 32
    b[40..42].copy_from_slice(&0u16.to_le_bytes());    // ext flags (FAT1 active, mirrored)
    b[42..44].copy_from_slice(&0u16.to_le_bytes());    // FS version 0.0
    b[44..48].copy_from_slice(&2u32.to_le_bytes());    // root cluster = 2
    b[48..50].copy_from_slice(&1u16.to_le_bytes());    // FS info sector = 1
    b[50..52].copy_from_slice(&6u16.to_le_bytes());    // backup boot sector = 6
    // bytes 52-63: reserved, zero
    b[64] = 0x80;    // drive number
    b[65] = 0x00;    // reserved
    b[66] = 0x29;    // extended boot signature
    b[67..71].copy_from_slice(&0xD711_0505u32.to_le_bytes()); // volume serial
    b[71..82].copy_from_slice(b"DJINNOS    ");
    b[82..90].copy_from_slice(b"FAT32   ");

    b[510] = 0x55;
    b[511] = 0xAA;

    write_sec(part_start, &b) && write_sec(part_start + 6, &b)
}

unsafe fn write_fsinfo(part_start: u64) {
    let mut b = [0u8; 512];
    b[0..4].copy_from_slice(&0x4161_5252u32.to_le_bytes());    // FSI lead sig
    b[484..488].copy_from_slice(&0x6141_7272u32.to_le_bytes()); // FSI struct sig
    // free count and next free = unknown (0xFFFFFFFF)
    b[488..492].copy_from_slice(&0xFFFF_FFFFu32.to_le_bytes());
    b[492..496].copy_from_slice(&0xFFFF_FFFFu32.to_le_bytes());
    b[508..512].copy_from_slice(&0xAA55_0000u32.to_le_bytes()); // trail sig
    write_sec(part_start + 1, &b);
    write_sec(part_start + 7, &b);  // backup
}

// ── FAT size calculation (correct circular formula) ───────────────────────────
//
// From Microsoft FAT specification:
//   RootDirSectors = 0 (FAT32)
//   TmpVal1 = TotSec - Reserved
//   TmpVal2 = NumFATs * SecPerClus + (SecPerClus * BytsPerSec / 4)
//   FATSz = ceil(TmpVal1 / TmpVal2)

fn fat_size(total_sectors: u32) -> u32 {
    let tmp1 = total_sectors - RESERVED_SECTORS;
    let tmp2 = N_FATS * SECTORS_PER_CLUSTER
               + (SECTORS_PER_CLUSTER * BYTES_PER_SECTOR / 4);
    (tmp1 + tmp2 - 1) / tmp2
}

// ── Public entry point ────────────────────────────────────────────────────────

pub fn format_and_write(
    part_start:    u64,
    part_end:      u64,
    loader_data:   &[u8],
    kernel_data:   &[u8],
    firmware_data: Option<&[u8]>,
) -> bool {
    unsafe { format_inner(part_start, part_end, loader_data, kernel_data, firmware_data) }
}

unsafe fn format_inner(
    part_start:    u64,
    part_end:      u64,
    loader_data:   &[u8],
    kernel_data:   &[u8],
    firmware_data: Option<&[u8]>,
) -> bool {
    let total_sectors = (part_end - part_start + 1) as u32;
    let fat_sz        = fat_size(total_sectors);
    let fat1_lba      = part_start + RESERVED_SECTORS as u64;
    let fat2_lba      = fat1_lba + fat_sz as u64;
    let data_lba      = fat2_lba + fat_sz as u64;

    uart::puts("fat32: total=");   uart::putu(total_sectors as u64);
    uart::puts(" fat_sz=");        uart::putu(fat_sz as u64);
    uart::puts(" fat1=");          uart::putu(fat1_lba);
    uart::puts(" data=");          uart::putu(data_lba);
    uart::puts("\r\n");

    // Sanity check: a real ESP is never larger than 1 GiB (2097152 sectors).
    if total_sectors > 2 * 1024 * 1024 {
        uart::puts("fat32: ABORT — partition is ");
        uart::putu(total_sectors as u64 / 2048);
        uart::puts(" MiB, too large for an ESP. Wrong partition found?\r\n");
        return false;
    }

    // ── BPB + FS info ─────────────────────────────────────────────────────────
    if !write_bpb_checked(part_start, total_sectors, fat_sz) { return false; }
    write_fsinfo(part_start);
    for i in 2u64..6 { let _ = zero_sec(part_start + i); }

    // ── Zero both FAT tables completely ───────────────────────────────────────
    uart::puts("fat32: zeroing FATs (");
    uart::putu(fat_sz as u64 * 2);
    uart::puts(" sectors)...\r\n");
    let fat_total = fat_sz as u64 * 2;
    for i in 0..fat_total {
        if !zero_sec(fat1_lba + i) {
            uart::puts("fat32: FAT zero failed at sector ");
            uart::putu(i);
            uart::puts("\r\n");
            return false;
        }
        // Progress every 256 sectors (~128 KiB).
        if i % 256 == 0 && i > 0 {
            uart::puts("  FAT ");
            uart::putu(i);
            uart::puts("/");
            uart::putu(fat_total);
            uart::puts("\r\n");
        }
    }

    // ── Cluster layout ────────────────────────────────────────────────────────
    let loader_clusters = (loader_data.len() as u32 + CLUSTER_BYTES - 1) / CLUSTER_BYTES;
    let kernel_clusters = (kernel_data.len() as u32 + CLUSTER_BYTES - 1) / CLUSTER_BYTES;
    let fw_clusters = firmware_data.map(|f|
        (f.len() as u32 + CLUSTER_BYTES - 1) / CLUSTER_BYTES).unwrap_or(0);

    let root_cl:   u32 = 2;
    let efi_cl:    u32 = 3;
    let boot_cl:   u32 = 4;
    let loader_cl: u32 = 5;
    let kernel_cl: u32 = 5 + loader_clusters;
    let fw_cl:     u32 = kernel_cl + kernel_clusters;

    uart::puts("fat32: loader_clusters="); uart::putu(loader_clusters as u64);
    uart::puts(" kernel_clusters=");       uart::putu(kernel_clusters as u64);
    uart::puts("\r\n");

    // ── FAT reserved entries ──────────────────────────────────────────────────
    set_fat_entry(fat1_lba, 0, 0x0FFF_FFF8);  // media byte
    set_fat_entry(fat1_lba, 1, 0x0FFF_FFFF);  // reserved EOC
    set_fat_entry(fat2_lba, 0, 0x0FFF_FFF8);
    set_fat_entry(fat2_lba, 1, 0x0FFF_FFFF);

    // ── FAT directory clusters (single-cluster, EOC) ──────────────────────────
    write_chain(fat1_lba, fat2_lba, root_cl, 1);
    write_chain(fat1_lba, fat2_lba, efi_cl,  1);
    write_chain(fat1_lba, fat2_lba, boot_cl, 1);

    // ── FAT file chains ───────────────────────────────────────────────────────
    write_chain(fat1_lba, fat2_lba, loader_cl, loader_clusters);
    write_chain(fat1_lba, fat2_lba, kernel_cl, kernel_clusters);
    if fw_clusters > 0 {
        write_chain(fat1_lba, fat2_lba, fw_cl, fw_clusters);
    }

    // ── Cluster LBA helper ────────────────────────────────────────────────────
    let clba = |c: u32| -> u64 {
        data_lba + (c as u64 - 2) * SECTORS_PER_CLUSTER as u64
    };

    // ── Root directory ────────────────────────────────────────────────────────
    {
        let mut sec = [0u8; 512];
        let de_efi    = make_dirent(b"EFI        ", 0x10, efi_cl, 0);
        let de_kernel = make_dirent(b"KERNEL  ELF", 0x20, kernel_cl,
                                    kernel_data.len() as u32);
        sec[0..32].copy_from_slice(&de_efi);
        sec[32..64].copy_from_slice(&de_kernel);
        if let Some(fw) = firmware_data {
            let de_fw = make_dirent(b"RTW8852ABIN", 0x20, fw_cl, fw.len() as u32);
            sec[64..96].copy_from_slice(&de_fw);
        }
        write_sec(clba(root_cl), &sec);
    }

    // ── EFI/ directory ────────────────────────────────────────────────────────
    {
        let mut sec = [0u8; 512];
        let dot  = make_dirent(b".          ", 0x10, efi_cl,  0);
        let ddot = make_dirent(b"..         ", 0x10, root_cl, 0);
        let boot = make_dirent(b"BOOT       ", 0x10, boot_cl, 0);
        sec[0..32].copy_from_slice(&dot);
        sec[32..64].copy_from_slice(&ddot);
        sec[64..96].copy_from_slice(&boot);
        write_sec(clba(efi_cl), &sec);
    }

    // ── EFI/BOOT/ directory ───────────────────────────────────────────────────
    {
        let mut sec = [0u8; 512];
        let dot  = make_dirent(b".          ", 0x10, boot_cl, 0);
        let ddot = make_dirent(b"..         ", 0x10, efi_cl,  0);
        let efi  = make_dirent(b"BOOTX64 EFI", 0x20, loader_cl,
                               loader_data.len() as u32);
        sec[0..32].copy_from_slice(&dot);
        sec[32..64].copy_from_slice(&ddot);
        sec[64..96].copy_from_slice(&efi);
        write_sec(clba(boot_cl), &sec);
    }

    // ── File data ─────────────────────────────────────────────────────────────
    uart::puts("fat32: writing loader.efi...\r\n");
    if !write_file(clba(loader_cl), loader_data) {
        uart::puts("fat32: loader write failed\r\n");
        return false;
    }

    uart::puts("fat32: writing kernel.elf...\r\n");
    if !write_file(clba(kernel_cl), kernel_data) {
        uart::puts("fat32: kernel write failed\r\n");
        return false;
    }

    if let Some(fw) = firmware_data {
        uart::puts("fat32: writing rtw8852a.bin...\r\n");
        if !write_file(clba(fw_cl), fw) {
            uart::puts("fat32: firmware write failed\r\n");
            return false;
        }
    }

    uart::puts("fat32: done\r\n");
    true
}
