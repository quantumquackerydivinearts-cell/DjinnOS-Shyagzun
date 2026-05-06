// ACPI table scanner and parser.
//
// We walk only what we need — no AML interpreter, no ACPI namespace.
// What we extract:
//   MCFG → PCIe ECAM base (upgrades PCI from legacy CAM to full ECAM)
//   MADT → LAPIC/I/O APIC addresses, IRQ source overrides
//   FADT → DSDT address (stored for Sprint 5 battery / EC access)
//
// Table discovery path:
//   RSDP  →  XSDT (preferred, 64-bit pointers) or RSDT (32-bit fallback)
//      └─ iterate 8-byte entries looking for "MCFG" / "APIC" / "FACP"
//
// RSDP location:
//   UEFI boot : passed by djinnos-loader from EFI config tables
//   Legacy    : scanned at 16-byte alignment in 0x80000–0x9FFFF and
//               0xE0000–0xFFFFF (standard BIOS/EBDA search regions)

use crate::uart;

// ── Global ACPI info ──────────────────────────────────────────────────────────

pub struct AcpiInfo {
    pub rsdp_addr:   u64,
    pub xsdt_addr:   u64,
    pub rsdt_addr:   u64,
    pub fadt_addr:   u64,
    pub dsdt_addr:   u64,
    pub madt_addr:   u64,
    pub mcfg_addr:   u64,

    // PCIe ECAM — the important one for Sprint 3
    pub ecam_base:      u64,
    pub ecam_start_bus: u8,
    pub ecam_end_bus:   u8,

    // Interrupt controller addresses
    pub lapic_addr:     u64,
    pub ioapic_addr:    u64,
    pub ioapic_gsi_base: u32,

    // IRQ source overrides (ISA bus, up to 16 entries)
    pub overrides:      [IrqOverride; 16],
    pub n_overrides:    u8,
}

#[derive(Clone, Copy)]
pub struct IrqOverride {
    pub irq:     u8,   // ISA IRQ number
    pub gsi:     u32,  // Global System Interrupt it maps to
    pub flags:   u16,  // polarity / trigger mode
}

impl IrqOverride {
    pub const fn zero() -> Self { IrqOverride { irq: 0, gsi: 0, flags: 0 } }
}

impl AcpiInfo {
    const fn zeroed() -> Self {
        AcpiInfo {
            rsdp_addr: 0, xsdt_addr: 0, rsdt_addr: 0,
            fadt_addr: 0, dsdt_addr: 0, madt_addr: 0, mcfg_addr: 0,
            ecam_base: 0, ecam_start_bus: 0, ecam_end_bus: 0,
            lapic_addr: 0, ioapic_addr: 0, ioapic_gsi_base: 0,
            overrides: [IrqOverride::zero(); 16],
            n_overrides: 0,
        }
    }
}

static mut INFO: AcpiInfo = AcpiInfo::zeroed();

pub fn get() -> &'static AcpiInfo { unsafe { &INFO } }

// ── Public init ───────────────────────────────────────────────────────────────

/// Initialise ACPI.  `hint` is the RSDP physical address from the bootloader
/// (0 if not provided — we scan the BIOS areas instead).
pub fn init(hint: u64) {
    let rsdp = if hint != 0 && rsdp_valid(hint) {
        hint
    } else {
        match scan_for_rsdp() {
            Some(a) => a,
            None => {
                uart::puts("acpi: RSDP not found\r\n");
                return;
            }
        }
    };

    unsafe {
        INFO.rsdp_addr = rsdp;
        parse_rsdp(rsdp);
    }

    uart::puts("acpi: ");
    uart::puts(if unsafe { INFO.xsdt_addr } != 0 { "XSDT" } else { "RSDT" });
    uart::puts(" found");
    if unsafe { INFO.ecam_base } != 0 {
        uart::puts("  ECAM @ 0x");
        uart::putx(unsafe { INFO.ecam_base });
    }
    uart::puts("\r\n");
}

/// ECAM base for PCI use.  Returns 0 if not yet discovered.
pub fn ecam_base()      -> u64 { unsafe { INFO.ecam_base      } }
pub fn ecam_start_bus() -> u8  { unsafe { INFO.ecam_start_bus } }
pub fn ecam_end_bus()   -> u8  { unsafe { INFO.ecam_end_bus   } }
pub fn dsdt_addr()      -> u64 { unsafe { INFO.dsdt_addr      } }
pub fn fadt_addr()      -> u64 { unsafe { INFO.fadt_addr      } }

// ── RSDP ─────────────────────────────────────────────────────────────────────

const SIG_RSDP: &[u8; 8] = b"RSD PTR ";

fn rsdp_valid(addr: u64) -> bool {
    let p = addr as *const u8;
    unsafe {
        // Signature
        for (i, &b) in SIG_RSDP.iter().enumerate() {
            if *p.add(i) != b { return false; }
        }
        // v1 checksum (first 20 bytes)
        let sum: u8 = (0..20usize).map(|i| *p.add(i)).fold(0u8, u8::wrapping_add);
        if sum != 0 { return false; }
        // v2 extended checksum
        let rev = *p.add(15);
        if rev >= 2 {
            let len = u32_le(p, 20) as usize;
            let esum: u8 = (0..len).map(|i| *p.add(i)).fold(0u8, u8::wrapping_add);
            if esum != 0 { return false; }
        }
        true
    }
}

fn scan_for_rsdp() -> Option<u64> {
    // EBDA (first kilobyte) and upper conventional memory
    for &(start, end) in &[(0x8_0000u64, 0xA_0000u64), (0xE_0000u64, 0x10_0000u64)] {
        let mut a = start;
        while a < end {
            if rsdp_valid(a) { return Some(a); }
            a += 16;
        }
    }
    None
}

unsafe fn parse_rsdp(rsdp: u64) {
    let p = rsdp as *const u8;
    let rev = *p.add(15);

    // XSDT (preferred, v2): 64-bit table pointers
    if rev >= 2 {
        let xsdt = u64_le(p, 24);
        if xsdt != 0 {
            INFO.xsdt_addr = xsdt;
            walk_xsdt(xsdt);
            return;
        }
    }
    // RSDT fallback: 32-bit table pointers
    let rsdt = u32_le(p, 16) as u64;
    INFO.rsdt_addr = rsdt;
    walk_rsdt(rsdt);
}

// ── XSDT / RSDT walker ────────────────────────────────────────────────────────

const HDR: usize = 36; // standard ACPI table header size

unsafe fn walk_xsdt(xsdt: u64) {
    let p   = xsdt as *const u8;
    let len = u32_le(p, 4) as usize;
    let n   = (len - HDR) / 8;
    for i in 0..n {
        let entry = u64_le(p, HDR + i * 8);
        if entry != 0 { dispatch_table(entry); }
    }
}

unsafe fn walk_rsdt(rsdt: u64) {
    let p   = rsdt as *const u8;
    let len = u32_le(p, 4) as usize;
    let n   = (len - HDR) / 4;
    for i in 0..n {
        let entry = u32_le(p, HDR + i * 4) as u64;
        if entry != 0 { dispatch_table(entry); }
    }
}

unsafe fn dispatch_table(addr: u64) {
    let p = addr as *const u8;
    let sig = [*p, *p.add(1), *p.add(2), *p.add(3)];
    match &sig {
        b"FACP" => parse_fadt(addr),
        b"APIC" => parse_madt(addr),
        b"MCFG" => parse_mcfg(addr),
        _ => {}
    }
}

// ── FADT ─────────────────────────────────────────────────────────────────────

unsafe fn parse_fadt(addr: u64) {
    INFO.fadt_addr = addr;
    let p = addr as *const u8;
    // Offset 40: 32-bit DSDT address
    let dsdt32 = u32_le(p, 40) as u64;
    // Offset 132: 64-bit X_DSDT (if table is long enough)
    let len = u32_le(p, 4);
    let dsdt64 = if len > 140 { u64_le(p, 132) } else { 0 };
    INFO.dsdt_addr = if dsdt64 != 0 { dsdt64 } else { dsdt32 };
}

// ── MADT ─────────────────────────────────────────────────────────────────────

unsafe fn parse_madt(addr: u64) {
    INFO.madt_addr = addr;
    let p = addr as *const u8;
    let table_len = u32_le(p, 4) as usize;

    // Offset 36: Local APIC address
    INFO.lapic_addr = u32_le(p, 36) as u64;

    let mut off = HDR + 8; // skip lapic addr (4) + flags (4)
    while off + 2 <= table_len {
        let rec_type = *p.add(off);
        let rec_len  = *p.add(off + 1) as usize;
        if rec_len < 2 { break; }

        match rec_type {
            1 => {
                // I/O APIC: id(1) + reserved(1) + addr(4) + gsi_base(4)
                if rec_len >= 12 {
                    let apic_addr = u32_le(p, off + 4) as u64;
                    if INFO.ioapic_addr == 0 {
                        INFO.ioapic_addr     = apic_addr;
                        INFO.ioapic_gsi_base = u32_le(p, off + 8);
                    }
                }
            }
            2 => {
                // Interrupt Source Override: bus(1) + irq(1) + gsi(4) + flags(2)
                if rec_len >= 10 && INFO.n_overrides < 16 {
                    let irq   = *p.add(off + 3);
                    let gsi   = u32_le(p, off + 4);
                    let flags = u16_le(p, off + 8);
                    let idx   = INFO.n_overrides as usize;
                    INFO.overrides[idx] = IrqOverride { irq, gsi, flags };
                    INFO.n_overrides += 1;
                }
            }
            5 => {
                // Local APIC Address Override (64-bit)
                if rec_len >= 12 {
                    INFO.lapic_addr = u64_le(p, off + 4);
                }
            }
            _ => {}
        }

        off += rec_len;
    }
}

// ── MCFG ─────────────────────────────────────────────────────────────────────

unsafe fn parse_mcfg(addr: u64) {
    INFO.mcfg_addr = addr;
    let p         = addr as *const u8;
    let table_len = u32_le(p, 4) as usize;

    // First allocation structure starts at offset 44 (36 header + 8 reserved).
    let mut off = 44usize;
    while off + 16 <= table_len {
        let base      = u64_le(p, off);
        let segment   = u16_le(p, off + 8);
        let start_bus = *p.add(off + 10);
        let end_bus   = *p.add(off + 11);

        if segment == 0 {
            // Segment group 0 is the main host bus.
            INFO.ecam_base      = base;
            INFO.ecam_start_bus = start_bus;
            INFO.ecam_end_bus   = end_bus;
            break; // usually only one segment in consumer hardware
        }
        off += 16;
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

#[inline]
unsafe fn u16_le(p: *const u8, off: usize) -> u16 {
    u16::from_le_bytes([*p.add(off), *p.add(off + 1)])
}

#[inline]
unsafe fn u32_le(p: *const u8, off: usize) -> u32 {
    u32::from_le_bytes([*p.add(off), *p.add(off+1), *p.add(off+2), *p.add(off+3)])
}

#[inline]
unsafe fn u64_le(p: *const u8, off: usize) -> u64 {
    u64::from_le_bytes([
        *p.add(off),   *p.add(off+1), *p.add(off+2), *p.add(off+3),
        *p.add(off+4), *p.add(off+5), *p.add(off+6), *p.add(off+7),
    ])
}
