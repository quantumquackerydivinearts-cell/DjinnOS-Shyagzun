// ACPI battery reader — no AML interpreter required.
//
// Strategy:
//   1. Walk DSDT raw bytes looking for EC OperationRegion (opcode 0x80, SpaceID 0x03).
//   2. Walk the corresponding Field definitions (opcode 0x5B 0x81) tracking cumulative
//      bit offsets to derive each named field's EC byte address.
//   3. Match a curated list of common battery field names (varies by OEM but the set
//      below covers most Lenovo, Dell, HP, and ASUS implementations).
//   4. Read those EC registers at runtime for live battery status.
//
// AML subset decoded:
//   DefOpRegion  0x80  NameSeg SpaceID Offset Length
//   DefField     0x5B 0x81  PkgLength NameSeg FieldFlags {FieldList}
//   FieldElement NameSeg PkgLength-encoded bit-count  | 0x00 reserved | 0x01 access
//
// PkgLength encoding (1–4 bytes, two high bits of byte 0 encode byte count):
//   00xxxxxx   → value = low 6 bits (1 byte)
//   01xxxxxx + 1 byte  → value = (low 4 bits << 4) | byte1
//   10xxxxxx + 2 bytes → value = (low 4 bits << 12) | (byte2 << 4) | byte1
//   11xxxxxx + 3 bytes → full 28-bit value across 4 bytes

use crate::{acpi, ec};

// ── Battery layout — EC byte addresses for each field ─────────────────────────

#[derive(Default, Clone, Copy)]
pub struct BatteryLayout {
    pub present:   u8,   // EC addr: battery present flag
    pub status:    u8,   // EC addr: charge state flags
    pub remaining: u8,   // EC addr: remaining capacity LSB (mAh or 10mWh)
    pub full_cap:  u8,   // EC addr: full charge capacity LSB
    pub rate:      u8,   // EC addr: current / power rate LSB (signed)
    pub voltage:   u8,   // EC addr: voltage LSB (mV)
    // Width in bytes for multi-byte fields (1 or 2)
    pub remaining_w: u8,
    pub full_cap_w:  u8,
    pub rate_w:      u8,
    pub voltage_w:   u8,
    pub valid: bool,
}

pub struct BatteryStatus {
    pub present:     bool,
    pub charging:    bool,
    pub discharging: bool,
    pub critical:    bool,
    pub remaining_mah: u32,
    pub full_mah:      u32,
    pub rate_ma:       i32,   // negative = discharging
    pub voltage_mv:    u32,
}

impl BatteryStatus {
    pub fn percent(&self) -> u32 {
        if self.full_mah == 0 { return 0; }
        (self.remaining_mah * 100 / self.full_mah).min(100)
    }
}

// ── DSDT scanner ──────────────────────────────────────────────────────────────

/// Try to detect battery EC register layout by scanning the DSDT.
pub fn detect() -> Option<BatteryLayout> {
    let dsdt_phys = acpi::dsdt_addr();
    if dsdt_phys == 0 || dsdt_phys >= 0x1_0000_0000 { return None; }

    // Read DSDT header to get total length.
    let hdr  = dsdt_phys as *const u8;
    let dlen = unsafe { u32::from_le_bytes([*hdr.add(4), *hdr.add(5), *hdr.add(6), *hdr.add(7)]) } as usize;

    if dlen < 36 || dlen > 4 * 1024 * 1024 { return None; } // sanity
    let data = unsafe { core::slice::from_raw_parts(hdr, dlen) };

    // Step 1: find EC OperationRegion(s) — opcode 0x80, SpaceID 0x03.
    let mut ec_name: [u8; 4] = [0; 4];
    let mut found = false;

    for i in 0..data.len().saturating_sub(12) {
        if data[i] != 0x80 { continue; }
        // Skip optional root/parent prefix (0x5C or 0x5E).
        let name_off = if data[i+1] == 0x5C || data[i+1] == 0x5E { i + 2 } else { i + 1 };
        if name_off + 6 > data.len() { continue; }
        let name = &data[name_off..name_off+4];
        if !is_name(name) { continue; }
        if data[name_off + 4] != 0x03 { continue; } // SpaceID = EmbeddedControl
        ec_name.copy_from_slice(name);
        found = true;
        // Keep going — prefer the LAST EC region (some DSDTs have multiple)
    }
    if !found { return None; }

    // Step 2: find Field definitions for that EC region.
    let mut layout = BatteryLayout::default();
    let mut i = 0usize;

    while i + 8 < data.len() {
        if data[i] != 0x5B || data[i+1] != 0x81 { i += 1; continue; }

        // DefField: 0x5B 0x81 PkgLength RegionName FieldFlags {FieldList}
        let (pkg_total, pkg_bytes) = decode_pkglen(&data[i+2..]);
        let field_start = i + 2 + pkg_bytes;
        if field_start + 5 >= data.len() { i += 1; continue; }

        // Skip optional root/parent prefix in the region name reference.
        let rname_off = if data[field_start] == 0x5C || data[field_start] == 0x5E {
            field_start + 1
        } else {
            field_start
        };
        if rname_off + 4 >= data.len() { i += 1; continue; }
        let rname = &data[rname_off..rname_off+4];
        if rname != &ec_name { i += 1; continue; }

        // FieldFlags is 1 byte after the name.
        let fl_start = rname_off + 5;
        let fl_end   = (i + 2 + pkg_total).min(data.len());

        if fl_start < fl_end {
            walk_field_list(&data[fl_start..fl_end], &mut layout);
        }
        i += 1;
    }

    layout.valid = layout.remaining != 0 || layout.voltage != 0 || layout.full_cap != 0;
    if layout.valid { Some(layout) } else { None }
}

fn walk_field_list(data: &[u8], layout: &mut BatteryLayout) {
    let mut bit_offset: u32 = 0;
    let mut i = 0usize;

    while i < data.len() {
        match data[i] {
            0x00 => {
                // ReservedField: skip N bits.
                let (bits, sz) = decode_pkglen(&data[i+1..]);
                bit_offset += bits as u32;
                i += 1 + sz;
            }
            0x01 => {
                // AccessField: AccessType (1) + AccessAttrib (1).
                i += 3;
            }
            0x02 => {
                // ExtendedAccessField.
                i += 1;
            }
            b if is_name_byte(&b) => {
                if i + 4 >= data.len() { break; }
                let name = &data[i..i+4];
                let (bits, sz) = decode_pkglen(&data[i+4..]);
                if bits == 0 { break; }

                let byte_addr = (bit_offset / 8) as u8;
                let width     = ((bits + 7) / 8) as u8;

                match name {
                    // Battery presence
                    b"BATS" | b"BCNT" | b"BPRS" | b"MBTS" | b"BATT" => {
                        layout.present = byte_addr;
                    }
                    // Battery status flags (charging / discharging / critical)
                    b"BSTS" | b"BSTA" | b"BCHG" | b"BSTT" | b"BST_" => {
                        layout.status = byte_addr;
                    }
                    // Remaining capacity
                    b"BRCA" | b"BRCP" | b"BCAP" | b"BREM" | b"BRMH"
                  | b"RC__" | b"RCAX" => {
                        layout.remaining   = byte_addr;
                        layout.remaining_w = width;
                    }
                    // Full charge capacity
                    b"BFCA" | b"BFCP" | b"LFCA" | b"BFCH" | b"BFC_"
                  | b"LFCM" | b"BFCM" => {
                        layout.full_cap   = byte_addr;
                        layout.full_cap_w = width;
                    }
                    // Present rate / current
                    b"BRTE" | b"BRTV" | b"BCUR" | b"BRAT" | b"BRT_"
                  | b"BCRN" | b"BCNT" => {
                        // BCNT conflicts with present — let presence win
                        if name != b"BCNT" || layout.present == 0 {
                            layout.rate   = byte_addr;
                            layout.rate_w = width;
                        }
                    }
                    // Voltage
                    b"BVLT" | b"BVOL" | b"BPWV" | b"PVOL" | b"BVT_"
                  | b"BVTG" | b"CVTG" => {
                        layout.voltage   = byte_addr;
                        layout.voltage_w = width;
                    }
                    _ => {}
                }

                bit_offset += bits as u32;
                i += 4 + sz;
            }
            _ => { i += 1; }
        }
    }
}

// ── Battery status reader ─────────────────────────────────────────────────────

pub fn read(layout: &BatteryLayout) -> Option<BatteryStatus> {
    // If we have no EC layout, try a quick sanity check via `present` field.
    if layout.present != 0 {
        let p = ec::read(layout.present)?;
        if p == 0 { return None; }
    }

    let status_byte = if layout.status != 0 { ec::read(layout.status).unwrap_or(0) } else { 0 };

    let remaining = read_field(layout.remaining, layout.remaining_w);
    let full_cap  = read_field(layout.full_cap,  layout.full_cap_w);
    let rate_raw  = read_field(layout.rate,       layout.rate_w);
    let voltage   = read_field(layout.voltage,    layout.voltage_w);

    // Rate is signed in some implementations (discharge = negative).
    let rate_ma: i32 = if rate_raw > 0x7FFF { -(0x10000 - rate_raw as i32) } else { rate_raw as i32 };

    Some(BatteryStatus {
        present:     true,
        charging:    status_byte & 0x02 != 0,
        discharging: status_byte & 0x01 != 0,
        critical:    status_byte & 0x04 != 0,
        remaining_mah: remaining,
        full_mah:      full_cap,
        rate_ma,
        voltage_mv:  voltage,
    })
}

fn read_field(addr: u8, width: u8) -> u32 {
    if addr == 0 { return 0; }
    match width {
        2 => ec::read_word(addr).unwrap_or(0) as u32,
        _ => ec::read(addr).unwrap_or(0) as u32,
    }
}

// ── AML helpers ───────────────────────────────────────────────────────────────

/// Decode an AML PkgLength/FieldBitLength from `data`.
/// Returns (value, bytes_consumed).
fn decode_pkglen(data: &[u8]) -> (usize, usize) {
    if data.is_empty() { return (0, 0); }
    let b0 = data[0] as usize;
    match b0 >> 6 {
        0 => (b0 & 0x3F, 1),
        1 if data.len() >= 2 => ((b0 & 0x0F) | ((data[1] as usize) << 4), 2),
        2 if data.len() >= 3 => ((b0 & 0x0F) | ((data[1] as usize) << 4) | ((data[2] as usize) << 12), 3),
        3 if data.len() >= 4 => (
            (b0 & 0x0F)
            | ((data[1] as usize) << 4)
            | ((data[2] as usize) << 12)
            | ((data[3] as usize) << 20),
            4,
        ),
        _ => (0, 1),
    }
}

fn is_name(b: &[u8]) -> bool {
    b.len() >= 4 && b[..4].iter().all(is_name_byte)
}

fn is_name_byte(b: &u8) -> bool {
    (*b >= b'A' && *b <= b'Z') || (*b >= b'0' && *b <= b'9') || *b == b'_'
}
