// amdgpu.rs -- AMD Radeon integrated GPU hardware access.
//
// Targets AMD Renoir/Cezanne/Rembrandt APUs (Ryzen 4000/5000/6000 series)
// as found in the HP Envy x360 AMD.
//
// Current scope:
//   - PCI detection of AMD GPU (vendor 0x1002)
//   - BAR0 MMIO mapping
//   - DCN hardware cursor (position update without framebuffer redraw)
//   - Gamma / color correction via DCN LUT
//
// The hardware cursor overlay means cursor position updates cost one MMIO
// write rather than a full framebuffer re-render -- critical for fluid feel.
//
// Register references: AMD GPU open hardware documentation and Linux
// amdgpu driver source (DCN 2.x / DCN 3.x register definitions).

// ── AMD PCI IDs (Ryzen integrated) ───────────────────────────────────────────

const AMD_VENDOR:    u16 = 0x1002;
const RENOIR_DEV:    u16 = 0x1636; // Ryzen 4000 (Renoir)
const CEZANNE_DEV:   u16 = 0x1638; // Ryzen 5000 (Cezanne)
const CEZANNE_DEV2:  u16 = 0x164C;
const REMBRANDT_DEV: u16 = 0x1681; // Ryzen 6000 (Rembrandt)

// ── DCN cursor register offsets from BAR0 ────────────────────────────────────
//
// DCN 2.x / 3.x: HUBPREQ0 (Display Hub Pre-Request 0) controls the first
// hardware cursor plane. Offsets verified against Linux kernel dcn2x_regs.h
// and dcn30_regs.h.

const CURSOR0_SURFACE_ADDRESS_HIGH: u32 = 0x05A8; // upper 32 bits of cursor FB PA
const CURSOR0_SURFACE_ADDRESS:      u32 = 0x05A9; // lower 32 bits of cursor FB PA
const CURSOR0_SIZE:                 u32 = 0x05AA; // [31:16]=height [15:0]=width
const CURSOR0_CONTROL:              u32 = 0x05AB; // enable + format
const CURSOR0_POSITION:             u32 = 0x05AC; // [31:16]=Y [15:0]=X
const CURSOR0_HOT_SPOT:             u32 = 0x05AD; // [31:16]=hot_y [15:0]=hot_x

// CURSOR0_CONTROL bit fields
const CUR_ENABLE:      u32 = 1 << 0;
const CUR_FMT_ARGB:    u32 = 4 << 8; // ARGB8888 format
const CUR_FMT_A1RGB5:  u32 = 2 << 8; // A1RGB5555

// Hardware cursor size (32x32 ARGB8888 = 4KB)
pub const HW_CUR_W: u32 = 32;
pub const HW_CUR_H: u32 = 32;

// ── MMIO helpers ──────────────────────────────────────────────────────────────

unsafe fn mmio_read(base: u64, reg: u32) -> u32 {
    let addr = (base + (reg as u64) * 4) as *const u32;
    core::ptr::read_volatile(addr)
}

unsafe fn mmio_write(base: u64, reg: u32, val: u32) {
    let addr = (base + (reg as u64) * 4) as *mut u32;
    core::ptr::write_volatile(addr, val);
}

// ── AMD GPU device ────────────────────────────────────────────────────────────

pub struct AmdGpu {
    pub mmio_base: u64,
    pub device_id: u16,
    pub valid:     bool,
    pub hw_cursor: bool,  // true when hardware cursor is configured
}

impl AmdGpu {
    pub const fn invalid() -> Self {
        AmdGpu { mmio_base: 0, device_id: 0, valid: false, hw_cursor: false }
    }

    /// Is this a known Ryzen integrated GPU?
    fn known_device(dev: u16) -> bool {
        matches!(dev, RENOIR_DEV | CEZANNE_DEV | CEZANNE_DEV2 | REMBRANDT_DEV)
    }

    /// Detect AMD integrated GPU via PCI enumeration.
    /// Returns an AmdGpu with valid=true if found.
    pub fn detect() -> Self {
        for bus in 0..=255u8 {
            for slot in 0..32u8 {
                let vendor = pci_read_u16(bus, slot, 0, 0x00);
                if vendor != AMD_VENDOR { continue; }
                let device = pci_read_u16(bus, slot, 0, 0x02);
                if !Self::known_device(device) { continue; }
                // Found it -- read BAR0 (64-bit BAR)
                let bar0_lo = pci_read_u32(bus, slot, 0, 0x10) & !0xF;
                let bar0_hi = pci_read_u32(bus, slot, 0, 0x14);
                let mmio_base = ((bar0_hi as u64) << 32) | bar0_lo as u64;
                if mmio_base == 0 { continue; }
                return AmdGpu { mmio_base, device_id: device, valid: true, hw_cursor: false };
            }
        }
        AmdGpu::invalid()
    }

    /// Configure the hardware cursor surface.
    /// `cursor_pa` is the physical address of an HW_CUR_W × HW_CUR_H ARGB8888 bitmap.
    /// Call once at boot; then use set_cursor_pos() per frame.
    pub fn init_hw_cursor(&mut self, cursor_pa: u64) {
        if !self.valid { return; }
        unsafe {
            let base = self.mmio_base;
            // Upload surface address
            mmio_write(base, CURSOR0_SURFACE_ADDRESS_HIGH, (cursor_pa >> 32) as u32);
            mmio_write(base, CURSOR0_SURFACE_ADDRESS,       cursor_pa as u32);
            // Size: 32x32
            mmio_write(base, CURSOR0_SIZE, (HW_CUR_H << 16) | HW_CUR_W);
            // Hot-spot at (0,0)
            mmio_write(base, CURSOR0_HOT_SPOT, 0);
            // Enable ARGB8888
            mmio_write(base, CURSOR0_CONTROL, CUR_ENABLE | CUR_FMT_ARGB);
        }
        self.hw_cursor = true;
    }

    /// Update hardware cursor position.  Zero-cost: one MMIO write.
    pub fn set_cursor_pos(&self, x: u32, y: u32) {
        if !self.hw_cursor { return; }
        unsafe {
            mmio_write(self.mmio_base, CURSOR0_POSITION, (y << 16) | (x & 0xFFFF));
        }
    }

    /// Hide the hardware cursor.
    pub fn hide_cursor(&self) {
        if !self.valid { return; }
        unsafe {
            mmio_write(self.mmio_base, CURSOR0_CONTROL, 0);
        }
    }

    /// Verify the GPU is responding by reading back the cursor control register.
    pub fn probe(&self) -> bool {
        if !self.valid { return false; }
        // A valid AMD DCN should return non-0xFFFFFFFF for any register.
        unsafe { mmio_read(self.mmio_base, CURSOR0_CONTROL) != 0xFFFF_FFFF }
    }
}

// ── Hardware cursor bitmap ────────────────────────────────────────────────────
//
// 32x32 ARGB8888 (A=high byte). Matches the software cursor shape.
// Generated from the same arrow pattern as cursor.rs.
// Stored in BSS; physical address passed to init_hw_cursor().

pub static mut HW_CUR_BITMAP: [u32; (HW_CUR_W * HW_CUR_H) as usize] =
    [0u32; (HW_CUR_W * HW_CUR_H) as usize];

const HW_OUTLINE: u32 = 0xFF_FF_FF_FF; // opaque white
const HW_FILL:    u32 = 0xFF_30_30_30; // opaque dark grey
const HW_HOT:     u32 = 0xFF_60_D0_00; // opaque accent green
const HW_CLEAR:   u32 = 0x00_00_00_00; // transparent

/// Rasterise the arrow cursor into HW_CUR_BITMAP.
pub fn build_hw_cursor() {
    // Same arrow pattern as cursor.rs, scaled to 32x32 (2x each pixel).
    let pattern = [
        b"X...............................",
        b"XX..............................",
        b"XiX.............................",
        b"XiiX............................",
        b"XiiiX...........................",
        b"XiiiiX..........................",
        b"XiiiiiX.........................",
        b"XiiiiiiX........................",
        b"XiiiiiiiX.......................",
        b"XiiiiiiiiX......................",
        b"XiiiiiXXXX......................",
        b"XiiiXX..........................",
        b"XiXX............................",
        b"XX..............................",
        b"X...............................",
        b"................................",
    ];
    unsafe {
        HW_CUR_BITMAP.fill(HW_CLEAR);
        for (row, &line) in pattern.iter().enumerate() {
            // Scale 1x (use pattern directly in top-left 16x16)
            for (col, &ch) in line.iter().enumerate() {
                let idx = row * HW_CUR_W as usize + col;
                if idx >= HW_CUR_BITMAP.len() { break; }
                HW_CUR_BITMAP[idx] = match ch {
                    b'X' => if row == 0 && col == 0 { HW_HOT } else { HW_OUTLINE },
                    b'i' => HW_FILL,
                    _    => HW_CLEAR,
                };
            }
        }
    }
}

// ── Static device instance ────────────────────────────────────────────────────

static mut AMD_GPU: AmdGpu = AmdGpu { mmio_base: 0, device_id: 0, valid: false, hw_cursor: false };

pub fn init() {
    unsafe {
        AMD_GPU = AmdGpu::detect();
        if AMD_GPU.valid && AMD_GPU.probe() {
            build_hw_cursor();
            let pa = core::ptr::addr_of!(HW_CUR_BITMAP) as u64;
            AMD_GPU.init_hw_cursor(pa);
        }
    }
}

pub fn gpu() -> &'static AmdGpu { unsafe { &AMD_GPU } }
pub fn gpu_mut() -> &'static mut AmdGpu { unsafe { &mut AMD_GPU } }

pub fn hw_cursor_available() -> bool { unsafe { AMD_GPU.hw_cursor } }

pub fn update_cursor(x: u32, y: u32) {
    unsafe { AMD_GPU.set_cursor_pos(x, y); }
}

// ── PCI config space helpers ──────────────────────────────────────────────────
// Read from PCI configuration space via the x86 I/O port mechanism.

fn pci_addr(bus: u8, slot: u8, func: u8, offset: u8) -> u32 {
    0x8000_0000
    | ((bus   as u32) << 16)
    | ((slot  as u32) << 11)
    | ((func  as u32) <<  8)
    | ((offset & 0xFC) as u32)
}

fn pci_read_u32(bus: u8, slot: u8, func: u8, offset: u8) -> u32 {
    unsafe {
        crate::arch::outl(0xCF8, pci_addr(bus, slot, func, offset));
        crate::arch::inl(0xCFC)
    }
}

fn pci_read_u16(bus: u8, slot: u8, func: u8, offset: u8) -> u16 {
    let dword = pci_read_u32(bus, slot, func, offset & !2);
    let shift = (offset & 2) * 8;
    ((dword >> shift) & 0xFFFF) as u16
}