// Linear framebuffer driver for x86_64.
//
// On real hardware GRUB negotiates a GOP (Graphics Output Protocol) mode with
// the UEFI firmware and passes the framebuffer address + layout via a
// multiboot2 tag.  We read that tag once at boot and wrap the raw pointer in
// FbDriver, which implements GpuSurface identically to VirtIO GpuDriver.
//
// Multiboot2 framebuffer tag (type 8):
//   u16 type = 8, u16 flags, u32 size
//   u64 addr, u32 pitch (bytes/row), u32 width, u32 height
//   u8 bpp, u8 fb_type (1 = RGB), u16 reserved
//   — for fb_type 1 (RGB):
//   u8 red_pos, u8 red_size, u8 green_pos, u8 green_size,
//   u8 blue_pos, u8 blue_size
//
// The physical framebuffer address is usually in the 0x8000_0000–0xFFFF_FFFF
// range.  Our boot page tables cover 0–4 GiB with 2 MiB huge pages, so all
// addresses within the first 4 GiB are accessible immediately.

use crate::gpu::GpuSurface;
use core::ptr::write_volatile;

pub struct FbDriver {
    addr:     *mut u32,
    _width:   u32,
    _height:  u32,
    pitch_px: u32,  // pitch in 32-bit pixels (pitch_bytes / 4)
    r_pos:    u8,
    g_pos:    u8,
    b_pos:    u8,
}

unsafe impl Send for FbDriver {}
unsafe impl Sync for FbDriver {}

/// Framebuffer info passed by the UEFI loader (matches djinnos-loader's UefiBootInfo).
/// MUST stay in sync with the struct in djinnos-loader/src/main.rs.
#[repr(C)]
pub struct UefiBootInfo {
    pub fb_addr:       u64,
    pub fb_width:      u32,
    pub fb_height:     u32,
    pub fb_pitch:      u32,
    pub r_pos:         u8,
    pub g_pos:         u8,
    pub b_pos:         u8,
    pub _pad:          u8,
    pub rsdp_addr:     u64,  // ACPI RSDP physical address (0 if unavailable)
    pub ramdisk_addr:  u64,  // pointer to RamFile table (0 if empty)
    pub ramdisk_count: u32,  // number of entries in the table
    pub _rd_pad:       u32,
}

impl FbDriver {
    /// Construct directly from a UEFI boot info block (no MB2 parsing).
    pub fn from_uefi(info: &UefiBootInfo) -> Self {
        FbDriver {
            addr:     info.fb_addr as *mut u32,
            _width:   info.fb_width,
            _height:  info.fb_height,
            pitch_px: info.fb_pitch / 4, // GOP is always 32 bpp
            r_pos:    info.r_pos,
            g_pos:    info.g_pos,
            b_pos:    info.b_pos,
        }
    }

    /// Parse the multiboot2 info block at `info_phys` and find the
    /// framebuffer tag.  Returns None if not present or fb_type ≠ RGB.
    pub fn from_mb2(info_phys: u64) -> Option<Self> {
        if info_phys == 0 { return None; }

        // Safety: identity-mapped; called once during kernel init.
        let total_size = unsafe { *(info_phys as *const u32) } as usize;
        let mut off = 8usize;

        while off + 8 <= total_size {
            let tag_ptr = (info_phys + off as u64) as *const u8;
            let typ  = unsafe { read_u16(tag_ptr) };
            let size = unsafe { read_u32(tag_ptr.add(4)) } as usize;

            if typ == 0 { break; }

            if typ == 8 && size >= 32 {
                // Framebuffer tag
                let addr   = unsafe { read_u64(tag_ptr.add(8)) };
                let pitch  = unsafe { read_u32(tag_ptr.add(16)) };
                let width  = unsafe { read_u32(tag_ptr.add(20)) };
                let height = unsafe { read_u32(tag_ptr.add(24)) };
                let bpp    = unsafe { *tag_ptr.add(26) };
                let fb_type= unsafe { *tag_ptr.add(27) };

                if fb_type == 1 && bpp >= 24 && size >= 38 {
                    let r_pos  = unsafe { *tag_ptr.add(28) };
                    let g_pos  = unsafe { *tag_ptr.add(30) };
                    let b_pos  = unsafe { *tag_ptr.add(32) };
                    let bytes_per_px = (bpp as u32 + 7) / 8;
                    let pitch_px = pitch / bytes_per_px;

                    return Some(FbDriver {
                        addr:     addr as *mut u32,
                        _width:   width,
                        _height:  height,
                        pitch_px,
                        r_pos, g_pos, b_pos,
                    });
                }
            }

            // Tags are padded to 8-byte alignment.
            off += (size + 7) & !7;
        }
        None
    }

    #[inline]
    fn pack(&self, b: u8, g: u8, r: u8) -> u32 {
        ((r as u32) << self.r_pos)
      | ((g as u32) << self.g_pos)
      | ((b as u32) << self.b_pos)
    }
}

impl GpuSurface for FbDriver {
    fn width(&self)  -> u32 { self._width  }
    fn height(&self) -> u32 { self._height }

    fn set_pixel(&self, x: u32, y: u32, b: u8, g: u8, r: u8) {
        if x >= self._width || y >= self._height { return; }
        let idx = (y * self.pitch_px + x) as usize;
        unsafe { write_volatile(self.addr.add(idx), self.pack(b, g, r)); }
    }

    /// Contiguous row write — one pass through a single cache line run.
    /// The compiler can vectorise this loop; individual set_pixel calls
    /// cannot be combined because each is marked write_volatile.
    fn fill_span(&self, x0: u32, x1: u32, y: u32, b: u8, g: u8, r: u8) {
        if y >= self._height { return; }
        let x0 = x0.min(self._width);
        let x1 = x1.min(self._width);
        if x0 >= x1 { return; }
        let pixel    = self.pack(b, g, r);
        let row_base = (y * self.pitch_px) as usize;
        for x in x0 as usize..x1 as usize {
            unsafe { write_volatile(self.addr.add(row_base + x), pixel); }
        }
    }

    /// Blit a row of BGR triples — packs and writes each pixel in one pass.
    fn blit_row(&self, src: &[(u8, u8, u8)], x0: u32, y: u32) {
        if y >= self._height { return; }
        let row_base = (y * self.pitch_px) as usize;
        for (i, &(b, g, r)) in src.iter().enumerate() {
            let x = x0 as usize + i;
            if x < self._width as usize {
                unsafe { write_volatile(self.addr.add(row_base + x), self.pack(b, g, r)); }
            }
        }
    }

    fn fill(&self, b: u8, g: u8, r: u8) {
        let pixel = self.pack(b, g, r);
        let total = (self._height * self.pitch_px) as usize;
        for i in 0..total {
            unsafe { write_volatile(self.addr.add(i), pixel); }
        }
    }

    fn flush(&mut self) {
        // Direct-write framebuffer — display sees writes immediately.
    }
}

// ── Unaligned pointer helpers ─────────────────────────────────────────────────

#[inline]
unsafe fn read_u16(p: *const u8) -> u16 {
    core::ptr::read_unaligned(p as *const u16)
}

#[inline]
unsafe fn read_u32(p: *const u8) -> u32 {
    core::ptr::read_unaligned(p as *const u32)
}

#[inline]
unsafe fn read_u64(p: *const u8) -> u64 {
    core::ptr::read_unaligned(p as *const u64)
}
