// VFS — virtual filesystem state for Shygazun ecall access.
//
// Lifts the Sa volume and VirtIO block driver into static storage so the
// trap handler (ecall path) can reach them without requiring pass-by-reference
// from kernel_main.
//
// fd allocation:
//   0–2   stdin / stdout / stderr
//   16–31 IPC channels  (ipc::IPC_FD_BASE)
//   32–47 open file fds (FILE_FD_BASE .. FILE_FD_BASE + MAX_OPEN)
//
// Syscalls wired here (RISC-V only — filesystem lives on VirtIO block):
//   SYS_SA   (156) — volume block count
//   SYS_SAO  (157) — open file by name → fd
//   SYS_SETH (159) — serialise directory listing into user buffer
//   SYS_LY   (2)   — sequential read from an open file fd
//   (close is implicit: fds freed when process exits via cleanup())

#[cfg(target_arch = "riscv64")]
use crate::{fs, virtio};

// ── File-fd constants ─────────────────────────────────────────────────────────

pub const FILE_FD_BASE: u64   = 32;
pub const MAX_OPEN:     usize = 16;

#[inline]
pub fn is_file_fd(fd: u64) -> bool {
    fd >= FILE_FD_BASE && fd < FILE_FD_BASE + MAX_OPEN as u64
}

#[inline]
pub fn file_slot(fd: u64) -> usize {
    (fd - FILE_FD_BASE) as usize
}

// ── Static filesystem state ───────────────────────────────────────────────────

#[cfg(target_arch = "riscv64")]
static mut BLK_STATE: Option<virtio::BlockDriver> = None;

#[cfg(target_arch = "riscv64")]
static mut VOL_STATE: Option<fs::SaVolume> = None;

// Open file table (RISC-V only — filesystem lives on VirtIO block).

#[cfg(target_arch = "riscv64")]
#[derive(Clone, Copy)]
struct OpenFile {
    entry:  fs::SaoEntry,
    offset: u32,
    pid:    u32,
    valid:  bool,
}

#[cfg(target_arch = "riscv64")]
impl OpenFile {
    const fn empty() -> Self {
        OpenFile {
            entry:  fs::SaoEntry { name: [0u8; 32], start: 0, len: 0 },
            offset: 0,
            pid:    0,
            valid:  false,
        }
    }
}

#[cfg(target_arch = "riscv64")]
static mut OPEN_FILES: [OpenFile; MAX_OPEN] = [const { OpenFile::empty() }; MAX_OPEN];

// ── Mount — called once from kernel_main after Sa volume is found ─────────────

/// Move the block driver and mounted volume into static VFS storage.
/// After this call the originals are consumed — pass them as owned values.
#[cfg(target_arch = "riscv64")]
pub fn mount(blk: virtio::BlockDriver, vol: fs::SaVolume) {
    unsafe {
        BLK_STATE = Some(blk);
        VOL_STATE = Some(vol);
    }
}

/// True if a volume is mounted.
#[cfg(target_arch = "riscv64")]
pub fn is_mounted() -> bool {
    unsafe { VOL_STATE.is_some() }
}

/// Return the mounted volume's file count (for SYS_SA).
#[cfg(target_arch = "riscv64")]
pub fn block_count() -> u64 {
    unsafe {
        BLK_STATE.as_ref().map(|b| b.capacity).unwrap_or(0)
    }
}

// ── SYS_SAO — open a file by name ────────────────────────────────────────────

/// Find `name` in the volume and allocate an open-file fd.
/// Returns the fd (FILE_FD_BASE + slot) or u64::MAX on failure.
#[cfg(target_arch = "riscv64")]
pub fn open(name: &[u8]) -> u64 {
    unsafe {
        let vol = match VOL_STATE.as_ref() { Some(v) => v, None => return u64::MAX };
        let entry = match vol.find(name) { Some(e) => *e, None => return u64::MAX };

        let pid = crate::process::current_id().0;
        for (i, slot) in OPEN_FILES.iter_mut().enumerate() {
            if !slot.valid {
                slot.entry  = entry;
                slot.offset = 0;
                slot.pid    = pid;
                slot.valid  = true;
                // Advance grapevine eigenstate on file open (Sao = byte 157).
                crate::process::advance_grapevine(157);
                return FILE_FD_BASE + i as u64;
            }
        }
        u64::MAX // no free slots
    }
}

// ── SYS_LY on a file fd — sequential read ────────────────────────────────────

/// Read up to `want` bytes from open file `fd` into `buf`.
/// Advances the internal offset.  Returns the number of bytes actually read.
/// Returns 0 at EOF or on error.
#[cfg(target_arch = "riscv64")]
pub fn read(fd: u64, buf: &mut [u8]) -> usize {
    let slot = file_slot(fd);
    unsafe {
        let f = match OPEN_FILES.get_mut(slot) {
            Some(f) if f.valid => f,
            _                  => return 0,
        };

        let remaining = f.entry.len.saturating_sub(f.offset) as usize;
        if remaining == 0 { return 0; }

        let want = buf.len().min(remaining);
        let blk  = match BLK_STATE.as_mut() { Some(b) => b, None => return 0 };

        // Read sector by sector from the offset.
        let mut done    = 0usize;
        let mut offset  = f.offset as usize;
        let mut sector  = f.entry.start as u64 + (offset / fs::SECTOR) as u64;
        let mut sec_off = offset % fs::SECTOR;
        let mut tmp     = [0u8; fs::SECTOR];

        while done < want {
            if !blk.read_sector(sector, &mut tmp) { break; }
            let available = (fs::SECTOR - sec_off).min(want - done);
            buf[done..done + available].copy_from_slice(&tmp[sec_off..sec_off + available]);
            done    += available;
            offset  += available;
            sector  += 1;
            sec_off  = 0;
        }

        f.offset += done as u32;
        done
    }
}

// ── SYS_SETH — serialise directory listing ────────────────────────────────────

/// Write the directory listing into `out` as NUL-terminated names.
/// Format per entry: name bytes (≤32) + '\n' separator.
/// Returns the total bytes written.
#[cfg(target_arch = "riscv64")]
pub fn readdir(out: &mut [u8]) -> usize {
    unsafe {
        let vol = match VOL_STATE.as_ref() { Some(v) => v, None => return 0 };
        let mut pos = 0usize;

        for entry in vol.list() {
            let name = entry.name_str();
            if name.is_empty() { continue; }
            // name
            let nlen = name.len().min(out.len().saturating_sub(pos + 1));
            if nlen == 0 { break; }
            out[pos..pos + nlen].copy_from_slice(&name[..nlen]);
            pos += nlen;
            // size as decimal, space-padded
            if pos + 12 < out.len() {
                out[pos] = b' '; pos += 1;
                let mut tmp = [0u8; 10];
                let slen = write_u32(&mut tmp, entry.len);
                out[pos..pos + slen].copy_from_slice(&tmp[..slen]);
                pos += slen;
            }
            // newline
            if pos < out.len() { out[pos] = b'\n'; pos += 1; }
        }
        pos
    }
}

// ── SYS_ZU cleanup — close all fds for a process ─────────────────────────────

/// Release all open file fds belonging to `pid`.
pub fn close_all(pid: u32) {
    #[cfg(target_arch = "riscv64")]
    unsafe {
        for slot in OPEN_FILES.iter_mut() {
            if slot.valid && slot.pid == pid {
                slot.valid = false;
            }
        }
    }
    #[cfg(not(target_arch = "riscv64"))]
    let _ = pid;
}

// ── Shell helpers — forward to static state so shell can still call fs ops ────
//
// After vfs::mount() moves the block driver and volume into static storage,
// kernel_main no longer has local copies.  The shell's cmd_ls / cmd_cat must
// be redirected to use vfs.  These thin wrappers do that.

/// Read a named file into `buf`, returning bytes read.  0 = not found / error.
#[cfg(target_arch = "riscv64")]
pub fn read_named(name: &[u8], buf: &mut [u8]) -> usize {
    unsafe {
        let vol = match VOL_STATE.as_ref() { Some(v) => v, None => return 0 };
        let blk = match BLK_STATE.as_mut() { Some(b) => b, None => return 0 };
        match vol.find(name) {
            None    => 0,
            Some(e) => vol.read_file(blk, e, buf),
        }
    }
}

/// Iterate entries, calling `f(name, size)` for each.
#[cfg(target_arch = "riscv64")]
pub fn for_each_entry(mut f: impl FnMut(&[u8], u32)) {
    unsafe {
        if let Some(vol) = VOL_STATE.as_ref() {
            for e in vol.list() {
                let name = e.name_str();
                if !name.is_empty() { f(name, e.len); }
            }
        }
    }
}

/// Find an entry by name; returns (start_sector, length_bytes) or None.
#[cfg(target_arch = "riscv64")]
pub fn find_entry(name: &[u8]) -> Option<(u64, u32)> {
    unsafe {
        let vol = VOL_STATE.as_ref()?;
        let e   = vol.find(name)?;
        Some((e.start as u64, e.len))
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn write_u32(buf: &mut [u8], mut n: u32) -> usize {
    if n == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10];
    let mut len = 0;
    while n > 0 { tmp[len] = b'0' + (n % 10) as u8; n /= 10; len += 1; }
    for i in 0..len { buf[i] = tmp[len - 1 - i]; }
    len
}
