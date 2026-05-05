// Grapevine filesystem — Sa / Seth / Sao.
//
// The filesystem ontology comes directly from the byte table (Tongue 7):
//   Sa   (156) — Feast table / root volume
//   Seth (159) — Platter / directory / bundle
//   Sao  (157) — Cup / file / persistent object
//
// Disk layout:
//   Sector 0      : Sa  — volume header (magic, name, file count)
//   Sectors 1–16  : Seth — directory table, up to 128 Sao entries × 64 bytes
//   Sector 17+    : Sao  — file data, one contiguous run per file

use crate::virtio::BlockDriver;

// ── Constants ─────────────────────────────────────────────────────────────────

pub const SA_MAGIC:          &[u8; 8] = b"DJINNOS\0";
pub const SAO_ENTRY_SIZE:    usize    = 64;
pub const ENTRIES_PER_SECTOR: usize   = 512 / SAO_ENTRY_SIZE;   // 8
pub const SETH_SECTORS:      usize    = 16;
pub const MAX_FILES:         usize    = SETH_SECTORS * ENTRIES_PER_SECTOR; // 128
pub const SAO_DATA_START:    u64      = 1 + SETH_SECTORS as u64; // sector 17

pub const SECTOR: usize = 512;

// ── Types ─────────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, Default)]
pub struct SaoEntry {
    pub name:  [u8; 32],
    pub start: u32,   // first data sector
    pub len:   u32,   // file length in bytes
}

impl SaoEntry {
    pub fn name_str(&self) -> &[u8] {
        let end = self.name.iter().position(|&b| b == 0).unwrap_or(32);
        &self.name[..end]
    }
}

pub struct SaVolume {
    pub name:    [u8; 32],
    pub count:   u32,
    entries:     [SaoEntry; MAX_FILES],
}

// ── Mount ─────────────────────────────────────────────────────────────────────

impl SaVolume {
    pub fn mount(blk: &mut BlockDriver) -> Option<Self> {
        let mut sec = [0u8; SECTOR];

        // Read Sa header
        if !blk.read_sector(0, &mut sec) { return None; }
        if &sec[0..8] != SA_MAGIC       { return None; }

        let mut name = [0u8; 32];
        name.copy_from_slice(&sec[8..40]);
        let count = u32::from_le_bytes([sec[40], sec[41], sec[42], sec[43]]);

        let mut entries = [SaoEntry::default(); MAX_FILES];
        let max = (count as usize).min(MAX_FILES);

        // Read Seth directory sectors one at a time
        for t in 0..SETH_SECTORS {
            if t * ENTRIES_PER_SECTOR >= max { break; }
            if !blk.read_sector(1 + t as u64, &mut sec) { break; }

            for e in 0..ENTRIES_PER_SECTOR {
                let i = t * ENTRIES_PER_SECTOR + e;
                if i >= max { break; }

                let base = &sec[e * SAO_ENTRY_SIZE..(e + 1) * SAO_ENTRY_SIZE];
                let mut ename = [0u8; 32];
                ename.copy_from_slice(&base[0..32]);
                let start = u32::from_le_bytes([base[32], base[33], base[34], base[35]]);
                let len   = u32::from_le_bytes([base[36], base[37], base[38], base[39]]);
                entries[i] = SaoEntry { name: ename, start, len };
            }
        }

        Some(SaVolume { name, count, entries })
    }

    pub fn list(&self) -> &[SaoEntry] {
        &self.entries[..self.count.min(MAX_FILES as u32) as usize]
    }

    pub fn find(&self, name: &[u8]) -> Option<&SaoEntry> {
        self.list().iter().find(|e| e.name_str() == name)
    }

    /// Read up to `buf.len()` bytes from a Sao file into `buf`.
    /// Returns the number of bytes actually read.
    pub fn read_file(
        &self,
        blk:   &mut BlockDriver,
        entry: &SaoEntry,
        buf:   &mut [u8],
    ) -> usize {
        let want = (entry.len as usize).min(buf.len());
        let mut done = 0;
        let mut sector = entry.start as u64;
        let mut tmp = [0u8; SECTOR];

        while done < want {
            if !blk.read_sector(sector, &mut tmp) { break; }
            let chunk = (want - done).min(SECTOR);
            buf[done..done + chunk].copy_from_slice(&tmp[..chunk]);
            done   += chunk;
            sector += 1;
        }
        done
    }
}