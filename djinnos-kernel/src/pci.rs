// PCI bus enumeration — legacy Configuration Access Mechanism (CAM).
//
// I/O port 0xCF8: PCI address register (32-bit, write)
//   bit 31 = enable, bits 23:16 = bus, 15:11 = device,
//   10:8 = function, 7:2 = register, 1:0 = 0
// I/O port 0xCFC: PCI data register (32-bit, read/write)
//
// CAM works on all x86 machines without ACPI.  Covers the first 256 bytes of
// each device's config space, which contains all standard BARs and IRQ info.
// Extended config space (registers 256–4095) requires ECAM from the ACPI MCFG
// table — that's Sprint 3.
//
// Discovered devices are stored in a static table.  Sprint 4 (HDA audio)
// and Sprint 6 (WiFi) use pci::find() to locate their controllers.

use crate::arch::{inl, outl};

// ── Config space access ───────────────────────────────────────────────────────
//
// Two access mechanisms:
//   ECAM (preferred): MMIO window at acpi::ecam_base() — covers full 4 KiB
//     per function including PCIe extended capabilities (registers 256–4095).
//   CAM  (fallback):  Legacy I/O ports 0xCF8/0xCFC — only first 256 bytes.
//
// After acpi::init() sets the ECAM base, all subsequent config-space reads
// automatically use ECAM.  Before acpi::init() (or on machines without MCFG)
// the legacy port method is used.

const PCI_ADDR: u16 = 0xCF8;
const PCI_DATA: u16 = 0xCFC;

#[inline]
fn cam_addr_reg(bus: u8, dev: u8, func: u8, off: u8) -> u32 {
    0x8000_0000
        | ((bus  as u32) << 16)
        | ((dev  as u32) << 11)
        | ((func as u32) <<  8)
        | (off & 0xFC)   as u32
}

#[inline]
fn ecam_ptr(bus: u8, dev: u8, func: u8, off: u16) -> *mut u32 {
    let base = crate::acpi::ecam_base();
    let addr = base
        | ((bus  as u64) << 20)
        | ((dev  as u64) << 15)
        | ((func as u64) << 12)
        | (off   as u64);
    addr as *mut u32
}

/// Read a 32-bit config register.  Uses ECAM when available, else CAM.
pub unsafe fn read32(bus: u8, dev: u8, func: u8, off: u8) -> u32 {
    if crate::acpi::ecam_base() != 0 {
        (ecam_ptr(bus, dev, func, off as u16) as *const u32).read_volatile()
    } else {
        outl(PCI_ADDR, cam_addr_reg(bus, dev, func, off));
        inl(PCI_DATA)
    }
}

/// Read a 32-bit register at a 16-bit offset (PCIe extended config space).
/// Requires ECAM; falls back to 0xFFFFFFFF if ECAM is not available.
pub unsafe fn read32_ext(bus: u8, dev: u8, func: u8, off: u16) -> u32 {
    if crate::acpi::ecam_base() != 0 {
        let p = ecam_ptr(bus, dev, func, off & !3);
        (p as *const u32).read_volatile()
    } else {
        0xFFFF_FFFF
    }
}

pub unsafe fn write32(bus: u8, dev: u8, func: u8, off: u8, val: u32) {
    if crate::acpi::ecam_base() != 0 {
        ecam_ptr(bus, dev, func, off as u16).write_volatile(val);
    } else {
        outl(PCI_ADDR, cam_addr_reg(bus, dev, func, off));
        outl(PCI_DATA, val);
    }
}

pub unsafe fn read16(bus: u8, dev: u8, func: u8, off: u8) -> u16 {
    (read32(bus, dev, func, off & !3) >> ((off & 2) * 8)) as u16
}

pub unsafe fn read8(bus: u8, dev: u8, func: u8, off: u8) -> u8 {
    (read32(bus, dev, func, off & !3) >> ((off & 3) * 8)) as u8
}

// ── Device record ─────────────────────────────────────────────────────────────

pub struct PciDevice {
    pub bus:     u8,
    pub dev:     u8,
    pub func:    u8,
    pub vendor:  u16,
    pub device:  u16,
    pub class:   u8,
    pub sub:     u8,
    pub prog_if: u8,
    pub rev:     u8,
    pub header:  u8,
    pub bar:     [u32; 6],
    pub irq_line: u8,
}

impl PciDevice {
    /// Physical address of a 32-bit memory BAR (masks off flag bits).
    pub fn bar_mem32(&self, idx: usize) -> Option<u64> {
        let v = self.bar[idx];
        if v & 1 != 0 { return None; }  // I/O bar
        if v & 0x6 == 0x4 { return None; }  // 64-bit — handled by bar_mem64
        Some((v & 0xFFFF_FFF0) as u64)
    }

    /// Physical address of a 64-bit memory BAR (reads BAR[idx] + BAR[idx+1]).
    pub fn bar_mem64(&self, idx: usize) -> Option<u64> {
        if idx + 1 >= 6 { return None; }
        let lo = self.bar[idx];
        if lo & 1 != 0 || lo & 0x6 != 0x4 { return None; }  // not a 64-bit mem BAR
        let hi = self.bar[idx + 1];
        Some((lo & 0xFFFF_FFF0) as u64 | ((hi as u64) << 32))
    }
}

// ── Static device table ───────────────────────────────────────────────────────

pub const MAX_DEVS: usize = 64;

static mut DEVS:  [Option<PciDevice>; MAX_DEVS] = [const { None }; MAX_DEVS];
static mut NDEVS: usize = 0;

pub fn count() -> usize { unsafe { NDEVS } }

pub fn devices() -> &'static [Option<PciDevice>] {
    unsafe { &DEVS[..NDEVS] }
}

/// Return the first device matching class + subclass.
pub fn find(class: u8, sub: u8) -> Option<&'static PciDevice> {
    unsafe {
        for i in 0..NDEVS {
            if let Some(ref d) = DEVS[i] {
                if d.class == class && d.sub == sub { return Some(d); }
            }
        }
    }
    None
}

/// Return the first device matching vendor + device ID.
pub fn find_id(vendor: u16, device: u16) -> Option<&'static PciDevice> {
    unsafe {
        for i in 0..NDEVS {
            if let Some(ref d) = DEVS[i] {
                if d.vendor == vendor && d.device == device { return Some(d); }
            }
        }
    }
    None
}

// ── Enumeration ───────────────────────────────────────────────────────────────

pub fn init() {
    unsafe { NDEVS = 0; }
    scan_bus(0);
    crate::uart::puts("pci: ");
    crate::uart::putu(count() as u64);
    crate::uart::puts(" devices\r\n");
}

fn scan_bus(bus: u8) {
    for dev in 0u8..32 {
        unsafe {
            let id = read32(bus, dev, 0, 0);
            if id == 0xFFFF_FFFF || id & 0xFFFF == 0xFFFF { continue; }

            let hdr = read8(bus, dev, 0, 0x0E);
            let funcs: u8 = if hdr & 0x80 != 0 { 8 } else { 1 };
            for f in 0..funcs { probe(bus, dev, f); }
        }
    }
}

fn probe(bus: u8, dev: u8, func: u8) {
    unsafe {
        let id = read32(bus, dev, func, 0);
        if id == 0xFFFF_FFFF || id & 0xFFFF == 0xFFFF { return; }

        let vendor   = (id & 0xFFFF) as u16;
        let device   = (id >> 16) as u16;
        let class_dw = read32(bus, dev, func, 0x08);
        let rev      = (class_dw & 0xFF) as u8;
        let prog_if  = ((class_dw >>  8) & 0xFF) as u8;
        let sub      = ((class_dw >> 16) & 0xFF) as u8;
        let class    = ((class_dw >> 24) & 0xFF) as u8;
        let header   = read8(bus, dev, func, 0x0E) & 0x7F;
        let irq_line = read8(bus, dev, func, 0x3C);

        let mut bar = [0u32; 6];
        if header == 0x00 {
            for i in 0..6usize {
                bar[i] = read32(bus, dev, func, 0x10 + i as u8 * 4);
            }
        }

        // Follow PCI-PCI bridges to secondary buses.
        if class == 0x06 && sub == 0x04 {
            let b = read8(bus, dev, func, 0x19);  // secondary bus number
            if b != 0 { scan_bus(b); }
        }

        if NDEVS < MAX_DEVS {
            DEVS[NDEVS] = Some(PciDevice {
                bus, dev, func, vendor, device,
                class, sub, prog_if, rev, header, bar, irq_line,
            });
            NDEVS += 1;
        }
    }
}

// ── Class/subclass description table ─────────────────────────────────────────

pub fn class_name(class: u8, sub: u8) -> &'static str {
    match (class, sub) {
        (0x00, 0x01) => "VGA (legacy)",
        (0x01, 0x01) => "IDE",
        (0x01, 0x06) => "SATA (AHCI)",
        (0x01, 0x08) => "NVMe",
        (0x02, 0x00) => "Ethernet",
        (0x02, 0x80) => "Network (other)",
        (0x03, 0x00) => "VGA display",
        (0x03, 0x02) => "Display (3D)",
        (0x04, 0x01) => "Audio (AC97)",
        (0x04, 0x03) => "HDA audio",
        (0x04, 0x80) => "Audio (other)",
        (0x06, 0x00) => "Host bridge",
        (0x06, 0x01) => "ISA bridge",
        (0x06, 0x04) => "PCI-PCI bridge",
        (0x06, 0x80) => "Bridge (other)",
        (0x07, 0x00) => "Serial (16550)",
        (0x0B, 0x40) => "Co-processor",
        (0x0C, 0x03) => "USB",
        (0x0C, 0x05) => "SMBus",
        (0x0C, 0x80) => "Serial bus (other)",
        _            => "unknown",
    }
}
