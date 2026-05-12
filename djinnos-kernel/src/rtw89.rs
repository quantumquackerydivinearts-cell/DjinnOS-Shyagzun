// rtw89.rs — Realtek RTL8852AE Wi-Fi 6 driver (Sprint W1: init + firmware)
//
// PCI: [10ec:8852]  class=02/80  BAR0 = PCIe MMIO register space
// Firmware: rtw8852a.bin loaded from ramdisk (placed on ESP by installer)
//
// Reference: Linux kernel drivers/net/wireless/realtek/rtw89/
// Chip: RTL8852AE — MAC_AX generation, 2T2R, PCIe interface
//
// Sprint W1 scope:
//   - PCI device find + BAR0 map
//   - Power-on sequence (SYS_* registers)
//   - Firmware parse + download to device
//   - Poll for firmware boot completion
//   - MAC address read
//
// Sprint W2 scope (next):
//   - MAC init (channel, rate tables, RX filter)
//   - 802.11 scan + association (open networks)
//   - WPA2-CCMP (4-way handshake + CCMP)
//   - DHCP handoff to existing net stack

use crate::uart;

// ── PCI identifiers ───────────────────────────────────────────────────────────

pub const VENDOR: u16 = 0x10EC;
pub const DEVICE: u16 = 0x8852;

// ── MAC_AX register map (BAR0 offsets) ───────────────────────────────────────
// From Linux rtw89/reg.h — MAC_AX generation (RTL8852A/B, RTL8852C, etc.)

// System / power
const R_AX_SYS_FUNC_EN:    u32 = 0x0002;   // u16 — system function enable
const R_AX_SYS_PW_CTRL:    u32 = 0x0004;   // power control
const R_AX_SYS_CLK_CTRL:   u32 = 0x0008;   // clock control
const R_AX_SYS_RST_CTRL:   u32 = 0x000C;   // reset control
const R_AX_SYS_SDIO_CTRL:  u32 = 0x0070;   // SDIO/PCIe control
const R_AX_DBG_CTRL:        u32 = 0x0080;
const R_AX_PLATFORM_ENABLE: u32 = 0x0088;  // platform enable
const R_AX_WLRF_CTRL:       u32 = 0x029C;  // RF control

// Firmware download
const R_AX_FWDL_CTRL:       u32 = 0x018C;  // firmware download control
const R_AX_BOOT_OPTION:     u32 = 0x00A0;  // boot option (DLFW=1 tells ROM to wait for download)
const R_AX_WLAN_FUN_EN:     u32 = 0x0086;  // WLAN function enable — must be set before BOOT_OPTION is writable
const R_AX_WLRF1:           u32 = 0x0090;  // WLAN RF enable 1
const B_AX_WLAN_FUNC_EN:    u32 = 1 << 0;
const B_AX_WLRF1_PWR_RDY:   u32 = 1 << 1;  // poll bit: WLAN power good
const R_AX_WCPU_FW_CTRL:    u32 = 0x01E0;  // CPU firmware control
const R_AX_HCI_FUNC_EN:     u32 = 0x01A8;  // HCI TX/RX DMA enable
const R_AX_HALT_H2C_CTRL:   u32 = 0x01B4;
const B_AX_HCI_TXDMA_EN:    u32 = 1 << 0;
const B_AX_HCI_RXDMA_EN:    u32 = 1 << 1;

// Boot option
const RTW89_FW_BOOT_OPTION_DLFW: u32 = 0x1;

// Firmware control bits
const B_AX_WCPU_FWDL_EN:    u32 = 1 << 0;
const B_AX_FWDL_PATH_RDY:   u32 = 1 << 16;
const B_AX_FWDL_STS_SHIFT:  u32 = 28;
const B_AX_FWDL_STS_MASK:   u32 = 0x7 << 28;  // 3-bit status field

// MAC RX/TX
const R_AX_DMAC_TABLE_CTRL: u32 = 0x8010;
const R_AX_RXFLTR_CFG:      u32 = 0x4224;
const R_AX_MAC_ADDR0:       u32 = 0x4210;  // MAC address bytes 0-3 (LE)
const R_AX_MAC_ADDR4:       u32 = 0x4214;  // MAC address bytes 4-5

// System function enable bits
const B_AX_FEN_BBRSTB:      u16 = 1 << 0;
const B_AX_FEN_BB_GLB_RSTN: u16 = 1 << 1;
const B_AX_FEN_WLANEN:      u16 = 1 << 7;
const B_AX_FEN_WLAN_EN:     u16 = 1 << 12;

// Platform enable bits
const B_AX_WCPU_EN:         u32 = 1 << 0;
const B_AX_PLATFORM_EN:     u32 = 1 << 4;

// ── MMIO helpers ──────────────────────────────────────────────────────────────

#[inline]
unsafe fn r8(base: u64, off: u32) -> u8 {
    ((base + off as u64) as *const u8).read_volatile()
}

#[inline]
unsafe fn r16(base: u64, off: u32) -> u16 {
    ((base + off as u64) as *const u16).read_volatile()
}

#[inline]
unsafe fn r32(base: u64, off: u32) -> u32 {
    ((base + off as u64) as *const u32).read_volatile()
}

#[inline]
unsafe fn w8(base: u64, off: u32, v: u8) {
    ((base + off as u64) as *mut u8).write_volatile(v);
}

#[inline]
unsafe fn w16(base: u64, off: u32, v: u16) {
    ((base + off as u64) as *mut u16).write_volatile(v);
}

#[inline]
unsafe fn w32(base: u64, off: u32, v: u32) {
    ((base + off as u64) as *mut u32).write_volatile(v);
}

// Spin until condition or timeout.  Returns true if condition met.
unsafe fn poll32(base: u64, off: u32, mask: u32, want: u32, iters: u32) -> bool {
    for _ in 0..iters {
        if r32(base, off) & mask == want { return true; }
        core::hint::spin_loop();
    }
    false
}

// ── RTW89 firmware file format ────────────────────────────────────────────────
//
// rtw8852a_fw.bin uses the MAC_AX / RTW89 binary header (NO text magic).
// Layout (all little-endian):
//   Offset  0: u8   drv_info_size
//   Offset  1: u8   rsvd0
//   Offset  2: u8   fw_type
//   Offset  3: u8   fw_db
//   Offset  4: u8[4] version
//   Offset  8: u8   month
//   Offset  9: u8   date
//   Offset 10: u8   hour
//   Offset 11: u8   min
//   Offset 12: u16  year
//   Offset 14: u16  sec_num  — number of download sections
//   Offset 16: u32  dw4
//   Offset 20: u32  dw5
//   Offset 24: u32  dw6
//   Offset 28: u32  dw7
//   Offset 32: sec_num × section descriptors (16 bytes each):
//              u32  checksum
//              u32  start_addr
//              u32  length
//              u32  reserved
//   Offset 32 + sec_num*16: raw section data (packed, no padding)

// ── MFW (Multi-FirmWare) container ───────────────────────────────────────────
//
// When byte 0 == 0xFF the file is a container holding multiple firmware blobs
// (one per chip-cut / firmware type).  Header layout:
//   u8       sig     0xFF
//   u8       fw_nr   number of entries
//   u8[14]   rsvd    zeros
// Followed by fw_nr × 16-byte info entries:
//   u8  cv       chip version (CAV=0, CBV=1, …)
//   u8  type     RTW89_FW_NORMAL=1, WOWLAN=3, …
//   u8  mp       manufacturing test firmware flag
//   u8  rsvd
//   u32 shift    file offset of the sub-firmware (LE)
//   u32 size     byte length of the sub-firmware (LE)
//   u32 rsvd

const MFW_SIG:      u8 = 0xFF;
const MFW_HDR_SIZE: usize = 16;
const MFW_INFO_SIZE: usize = 16;
const RTW89_FW_NORMAL: u8 = 1;

// Extract the sub-firmware slice for normal WiFi use.
// Prints all entries so UART shows what's inside.
// Falls through transparently if this is not an MFW container.
fn mfw_extract(fw: &[u8]) -> Option<&[u8]> {
    if fw.len() < MFW_HDR_SIZE { return None; }
    if fw[0] != MFW_SIG {
        return Some(fw);  // legacy bare fw_hdr — pass through unchanged
    }

    let fw_nr = fw[1] as usize;
    uart::puts("rtw89: MFW fw_nr=");
    uart::putu(fw_nr as u64);
    uart::puts("\r\n");

    if MFW_HDR_SIZE + fw_nr * MFW_INFO_SIZE > fw.len() {
        uart::puts("rtw89: MFW header truncated\r\n");
        return None;
    }

    let mut best: Option<(usize, usize)> = None;  // (shift, size)
    for i in 0..fw_nr {
        let b      = MFW_HDR_SIZE + i * MFW_INFO_SIZE;
        let cv     = fw[b];
        let fwtype = fw[b + 1];
        let mp     = fw[b + 2];
        let shift  = u32::from_le_bytes([fw[b+4], fw[b+5], fw[b+6], fw[b+7]]) as usize;
        let size   = u32::from_le_bytes([fw[b+8], fw[b+9], fw[b+10], fw[b+11]]) as usize;


        if fwtype == RTW89_FW_NORMAL && mp == 0 && shift + size <= fw.len() {
            if best.is_none() {
                best = Some((shift, size));  // first match wins; prefer cv=0 (CAV/A-cut)
            } else if cv == 0 {
                best = Some((shift, size));  // prefer CAV over CBV etc.
            }
        }
    }

    match best {
        None => {
            uart::puts("rtw89: no normal WiFi firmware entry in MFW\r\n");
            None
        }
        Some((shift, size)) => {
            uart::puts("rtw89: using sub-firmware at 0x");
            uart::putx(shift as u64);
            uart::puts(" size=");
            uart::putu(size as u64);
            uart::puts("\r\n");
            Some(&fw[shift..shift + size])
        }
    }
}

const FW_HDR_SIZE: usize = 32;

#[derive(Copy, Clone)]
struct FwSection {
    start_addr: u32,
    len:        u32,
    data_off:   usize,   // byte offset into fw_data slice
}

fn parse_fw(fw: &[u8]) -> Option<([u8; 4], u8, usize, [FwSection; 10], usize)> {
    if fw.len() < 32 { return None; }

    let ver    = [fw[4], fw[5], fw[6], fw[7]];
    let fw_type = fw[2];

    // sec_num: try u8 at offset 8 (layout A), fallback to bits 27:24 of word3.
    let word3   = u32::from_le_bytes([fw[12], fw[13], fw[14], fw[15]]);
    let nsecs_a = fw[8] as usize;
    let nsecs_b = ((word3 >> 24) & 0x0F) as usize;
    let n_secs = if nsecs_a >= 1 && nsecs_a <= 10 { nsecs_a }
                 else if nsecs_b >= 1 && nsecs_b <= 10 { nsecs_b }
                 else {
                     uart::puts("rtw89: no valid sec_num\r\n");
                     return None;
                 };

    // Section descriptor table always starts after the 32-byte main header.
    let sec_tbl_base = FW_HDR_SIZE;
    let sec_tbl_end  = sec_tbl_base + n_secs * 16;

    if sec_tbl_end > fw.len() {
        uart::puts("rtw89: section table truncated\r\n");
        return None;
    }

    let mut secs = [FwSection { start_addr: 0, len: 0, data_off: 0 }; 10];
    let mut data_cursor = sec_tbl_end;

    for i in 0..n_secs {
        let base = sec_tbl_base + i * 16;
        // Linux rtw89_fw_hdr_section layout:
        //   w0 (+0):  type/flags
        //   w1 (+4):  length in bits 23:0 (RTW89_FWSECTION_HDR_SEC_SIZE_MASK)
        //   w2 (+8):  start_addr
        //   w3 (+12): reserved/checksum
        let w1   = u32::from_le_bytes(fw[base+4..base+8].try_into().unwrap_or([0;4]));
        let len  = w1 & 0x00FF_FFFF;  // bits 23:0
        let addr = u32::from_le_bytes(fw[base+8..base+12].try_into().unwrap_or([0;4]));
        secs[i] = FwSection { start_addr: addr, len, data_off: data_cursor };
        data_cursor += len as usize;
    }

    Some((ver, fw_type, n_secs, secs, data_cursor))
}

// ── Power-on sequence ─────────────────────────────────────────────────────────
//
// Condensed from rtw89_pwr_seq_cmd execution in Linux rtw89/mac.c
// for RTL8852AE (pwr_on_seq_8852a).

unsafe fn dump_regs(bar: u64, label: &str) {
    uart::puts("rtw89: regs [");
    uart::puts(label);
    uart::puts("]\r\n");
    for &(name, off) in &[
        ("SYS_PW_CTRL ", R_AX_SYS_PW_CTRL),
        ("SYS_FUNC_EN ", R_AX_SYS_FUNC_EN as u32),
        ("SYS_CLK_CTRL", R_AX_SYS_CLK_CTRL),
        ("SYS_RST_CTRL", R_AX_SYS_RST_CTRL),
        ("PLATFORM_EN ", R_AX_PLATFORM_ENABLE),
        ("HCI_FUNC_EN ", R_AX_HCI_FUNC_EN),
        ("WCPU_FW_CTRL", R_AX_WCPU_FW_CTRL),
        ("BOOT_OPTION ", R_AX_BOOT_OPTION),
        ("WLRF_CTRL   ", R_AX_WLRF_CTRL),
    ] {
        uart::puts("  ");
        uart::puts(name);
        uart::puts(" = 0x");
        uart::putx(r32(bar, off) as u64);
        uart::puts("\r\n");
    }
}

unsafe fn power_on(bar: u64) -> bool {
    uart::puts("rtw89: power on...\r\n");

    // Verify MMIO is reachable: read SYS_PW_CTRL, write a bit, read back.
    // If MMIO isn't mapped, reads return 0 or 0xFFFFFFFF and writes are no-ops.
    let pw0 = r32(bar, R_AX_SYS_PW_CTRL);
    w32(bar, R_AX_SYS_PW_CTRL, pw0 | (1 << 0));
    let pw1 = r32(bar, R_AX_SYS_PW_CTRL);
    uart::puts("rtw89: SYS_PW_CTRL before=0x");
    uart::putx(pw0 as u64);
    uart::puts(" after=0x");
    uart::putx(pw1 as u64);
    uart::puts("\r\n");

    if pw0 == 0xFFFF_FFFF || pw1 == 0xFFFF_FFFF {
        uart::puts("rtw89: MMIO reads all-ones — PCIe link down or BAR not decoded\r\n");
        return false;
    }
    if pw0 == 0 && pw1 == 0 {
        uart::puts("rtw89: MMIO reads all-zero — chip may be in D3 or BAR unmap\r\n");
        // Continue anyway — some chips have 0 as reset default for SYS_PW_CTRL.
    }

    // Step: enable WLAN function — required by rtw8852a power sequence before
    // BOOT_OPTION becomes writable.
    w32(bar, R_AX_WLAN_FUN_EN, B_AX_WLAN_FUNC_EN);
    // Poll for WLAN power-good (bit 1) with timeout.
    let mut wl_rdy = false;
    for _ in 0..2_000_000u32 {
        if r32(bar, R_AX_WLAN_FUN_EN) & B_AX_WLRF1_PWR_RDY != 0 {
            wl_rdy = true;
            break;
        }
        core::hint::spin_loop();
    }
    uart::puts("rtw89: WLAN_FUN_EN=0x");
    uart::putx(r32(bar, R_AX_WLAN_FUN_EN) as u64);
    uart::puts(if wl_rdy { " (rdy)\r\n" } else { " (timeout)\r\n" });

    // WLRF1 enable (part of power sequence).
    w32(bar, R_AX_WLRF1, 0x1);

    // System function enable: BB, RF, WLAN.
    let fen = r16(bar, R_AX_SYS_FUNC_EN);
    w16(bar, R_AX_SYS_FUNC_EN,
        fen | B_AX_FEN_BBRSTB | B_AX_FEN_BB_GLB_RSTN
            | B_AX_FEN_WLANEN | B_AX_FEN_WLAN_EN);

    // Clocks.
    let clk = r32(bar, R_AX_SYS_CLK_CTRL);
    w32(bar, R_AX_SYS_CLK_CTRL, clk | (1 << 0) | (1 << 2));

    // R_AX_SYS_ISO_CTRL (0x0074) — release power-domain isolation.
    // Linux rtw8852a_pwr_on_seq sets bit 3 here then polls bit 4 (power good).
    // Without this, BOOT_OPTION at 0x00A0 is read-only (isolated domain).
    const R_AX_SYS_ISO_CTRL: u32 = 0x0074;
    w32(bar, R_AX_SYS_ISO_CTRL, r32(bar, R_AX_SYS_ISO_CTRL) | (1 << 3));
    let mut iso_rdy = false;
    for _ in 0..2_000_000u32 {
        if r32(bar, R_AX_SYS_ISO_CTRL) & (1 << 4) != 0 {
            iso_rdy = true;
            break;
        }
        core::hint::spin_loop();
    }
    uart::puts("rtw89: SYS_ISO_CTRL=0x");
    uart::putx(r32(bar, R_AX_SYS_ISO_CTRL) as u64);
    uart::puts(if iso_rdy { " (pwr good)\r\n" } else { " (no pwr good)\r\n" });

    // Platform enable — power MAC domain.  Written LAST so WCPU doesn't start
    // before fw_download() sets BOOT_OPTION = DLFW.
    w32(bar, R_AX_PLATFORM_ENABLE, B_AX_PLATFORM_EN);

    // Give hardware time to settle.
    for _ in 0..200_000u32 { core::hint::spin_loop(); }

    uart::puts("rtw89: power on done\r\n");
    true
}

// ── Firmware download ─────────────────────────────────────────────────────────
//
// Writes each firmware section directly via MMIO into the device's
// address space.  This is the "safe" FWDL path — no PCIe DMA required,
// avoids IOMMU issues.  Slower than DMA but correct for bare-metal.

unsafe fn fw_download(bar: u64, fw: &[u8]) -> bool {
    uart::puts("rtw89: parsing firmware...\r\n");

    // Unwrap MFW container if present (byte 0 == 0xFF).
    let fw = match mfw_extract(fw) {
        Some(f) => f,
        None => {
            uart::puts("rtw89: no suitable sub-firmware in MFW container\r\n");
            return false;
        }
    };

    let parsed = match parse_fw(fw) {
        Some(p) => p,
        None    => { uart::puts("rtw89: firmware parse failed\r\n"); return false; }
    };
    let (ver, _cat, n_secs, ref secs, _total) = parsed;

    uart::puts("rtw89: fw ver=");
    for b in &ver { uart::putu(*b as u64); uart::puts("."); }
    uart::puts(" secs=");
    uart::putu(n_secs as u64);
    uart::puts("\r\n");

    // BOOT_OPTION must be written BEFORE PLATFORM_ENABLE starts the WCPU.
    // Writing PLATFORM_ENABLE bit 4 (B_AX_PLATFORM_EN) starts the WCPU immediately;
    // the ROM reads BOOT_OPTION at startup and enters DLFW mode if it's set to 0x1.
    uart::puts("rtw89: BOOT_OPTION before=0x");
    uart::putx(r32(bar, R_AX_BOOT_OPTION) as u64);
    uart::puts("\r\n");
    w32(bar, R_AX_BOOT_OPTION, RTW89_FW_BOOT_OPTION_DLFW);
    uart::puts("rtw89: BOOT_OPTION written=0x");
    uart::putx(r32(bar, R_AX_BOOT_OPTION) as u64);
    uart::puts("\r\n");

    // Alternative DLFW trigger: set WCPU_FWDL_EN (bit 0 of WCPU_FW_CTRL) before
    // starting WCPU. ROM may check this instead of (or in addition to) BOOT_OPTION.
    w32(bar, R_AX_WCPU_FW_CTRL, B_AX_WCPU_FWDL_EN);
    uart::puts("rtw89: WCPU_FW_CTRL pre-kick=0x");
    uart::putx(r32(bar, R_AX_WCPU_FW_CTRL) as u64);
    uart::puts("\r\n");

    // HCI_FUNC_EN — write now (before WCPU starts, will be re-init'd by firmware).
    w32(bar, R_AX_HCI_FUNC_EN, B_AX_HCI_TXDMA_EN | B_AX_HCI_RXDMA_EN);

    // Kick WCPU: write B_AX_PLATFORM_EN | B_AX_WCPU_EN = 0x11 together.
    // This starts the WCPU. It will read BOOT_OPTION (0x1 = DLFW) and
    // respond by setting FWDL_PATH_RDY (bit 16 of WCPU_FW_CTRL).
    w32(bar, R_AX_PLATFORM_ENABLE, B_AX_PLATFORM_EN | B_AX_WCPU_EN);
    uart::puts("rtw89: PLATFORM_ENABLE=0x");
    uart::putx(r32(bar, R_AX_PLATFORM_ENABLE) as u64);
    uart::puts("\r\n");

    // Check WCPU_FW_CTRL immediately — ROM sets FWDL_PATH_RDY within milliseconds.
    for _ in 0..50_000u32 { core::hint::spin_loop(); }
    uart::puts("rtw89: WCPU_FW_CTRL early=0x");
    uart::putx(r32(bar, R_AX_WCPU_FW_CTRL) as u64);
    uart::puts("\r\n");

    let mut fwdl_rdy = false;
    'wait: for _ in 0..10_000_000u32 {
        let v = r32(bar, R_AX_WCPU_FW_CTRL);
        if v & B_AX_FWDL_PATH_RDY != 0 {
            fwdl_rdy = true;
            break 'wait;
        }
        core::hint::spin_loop();
    }
    dump_regs(bar, "after-wcpu-kick");
    if !fwdl_rdy {
        uart::puts("rtw89: FWDL path not ready\r\n");
        return false;
    }
    uart::puts("rtw89: FWDL path ready\r\n");

    // Now tell hardware we're the downloader.
    let ctrl = r32(bar, R_AX_WCPU_FW_CTRL);
    w32(bar, R_AX_WCPU_FW_CTRL, ctrl | B_AX_WCPU_FWDL_EN);

    // Download each section via FWDL write port.
    // The device maps firmware write space starting at R_AX_FWDL_CTRL.
    for i in 0..n_secs {
        let sec = &secs[i];
        if sec.len == 0 { continue; }
        let data_end = sec.data_off + sec.len as usize;
        if data_end > fw.len() {
            uart::puts("rtw89: section out of bounds\r\n");
            return false;
        }
        let data = &fw[sec.data_off..data_end];

        uart::puts("rtw89: section ");
        uart::putu(i as u64);
        uart::puts(" addr=0x");
        uart::putx(sec.start_addr as u64);
        uart::puts(" len=");
        uart::putu(sec.len as u64);
        uart::puts("\r\n");

        // Write section destination address into FWDL control.
        w32(bar, R_AX_FWDL_CTRL, sec.start_addr);

        // Write firmware bytes via FWDL write port (R_AX_FWDL_CTRL + 4).
        let port = R_AX_FWDL_CTRL + 4;
        let mut off = 0usize;
        while off + 4 <= data.len() {
            let dw = u32::from_le_bytes([data[off], data[off+1],
                                          data[off+2], data[off+3]]);
            w32(bar, port, dw);
            off += 4;
        }
        // Handle remaining bytes (< 4).
        if off < data.len() {
            let mut tail = [0u8; 4];
            tail[..data.len()-off].copy_from_slice(&data[off..]);
            w32(bar, port, u32::from_le_bytes(tail));
        }
    }

    // Signal end of download to firmware.
    // Linux: rtw89_fwdl_phase2 — clear FWDL_EN so firmware knows download is done.
    let ctrl = r32(bar, R_AX_WCPU_FW_CTRL);
    w32(bar, R_AX_WCPU_FW_CTRL, ctrl & !B_AX_WCPU_FWDL_EN);

    uart::puts("rtw89: download complete, waiting for firmware boot...\r\n");

    // The firmware status byte lives at R_AX_WCPU_FW_CTRL + 1 (0x01E1).
    // Linux defines:
    //   0x00 = initial / in progress
    //   0x04 = WCPU firmware download ready (booted successfully)
    //   0x07 = error
    // Dump the byte every 500k iterations so UART shows progress.
    for _ in 0..10_000_000u32 {
        let sts = r8(bar, R_AX_WCPU_FW_CTRL + 1);
        let ctrl = r32(bar, R_AX_WCPU_FW_CTRL);
        match sts {
            0x04 => {
                uart::puts("rtw89: firmware booted (sts=4)\r\n");
                return true;
            }
            0x07 => {
                uart::puts("rtw89: firmware download error (sts=7)\r\n");
                return false;
            }
            _ => {}
        }
        // Also accept the old-style status field (bits 30:28 == 2) as a fallback.
        let old_sts = (ctrl & B_AX_FWDL_STS_MASK) >> B_AX_FWDL_STS_SHIFT;
        if old_sts == 2 {
            uart::puts("rtw89: firmware booted (legacy sts=2)\r\n");
            return true;
        }
        core::hint::spin_loop();
    }

    uart::puts("rtw89: firmware boot timeout\r\n");
    uart::puts("  final sts=0x");
    uart::putx(r8(bar, R_AX_WCPU_FW_CTRL + 1) as u64);
    uart::puts(" ctrl=0x");
    uart::putx(r32(bar, R_AX_WCPU_FW_CTRL) as u64);
    uart::puts("\r\n");
    false
}

// ── MAC address read ───────────────────────────────────────────────────────────

unsafe fn read_mac(bar: u64) -> [u8; 6] {
    let lo = r32(bar, R_AX_MAC_ADDR0);
    let hi = r32(bar, R_AX_MAC_ADDR4);
    [
        (lo      ) as u8,
        (lo >>  8) as u8,
        (lo >> 16) as u8,
        (lo >> 24) as u8,
        (hi      ) as u8,
        (hi >>  8) as u8,
    ]
}

// ── Driver state ──────────────────────────────────────────────────────────────

pub struct Rtw89 {
    bar:  u64,
    pub mac: [u8; 6],
    pub ready: bool,
}

static mut DRV: Option<Rtw89> = None;

pub fn get() -> Option<&'static mut Rtw89> {
    unsafe { DRV.as_mut() }
}

// ── Public init ───────────────────────────────────────────────────────────────

pub fn init() -> bool {
    unsafe { init_inner() }
}

unsafe fn init_inner() -> bool {
    // Find [10ec:8852] in PCI table.
    let dev = match crate::pci::find_id(VENDOR, DEVICE) {
        Some(d) => d,
        None => {
            uart::puts("rtw89: [10ec:8852] not found in PCI table\r\n");
            return false;
        }
    };

    uart::puts("rtw89: found [10ec:8852] bus=");
    crate::pci::wifi_scan();  // already scanned at boot — just log
    uart::puts("\r\n");

    // Enable PCI bus master + memory space.
    let cmd = crate::pci::read16(dev.bus, dev.dev, dev.func, 0x04);
    crate::pci::write32(dev.bus, dev.dev, dev.func, 0x04, (cmd | 0x06) as u32);

    // RTL8852AE BAR layout (from lspci on Linux):
    //   BAR0: I/O ports (legacy compat, 256 bytes) — we ignore this
    //   BAR1: empty (32-bit before the 64-bit pair)
    //   BAR2+3: 64-bit non-prefetchable MMIO, 1 MiB — THIS is what we need
    //
    // UEFI does not configure the WiFi MMIO BAR (it doesn't need WiFi to boot).
    // If BAR2 is unconfigured (0 or all-ones) we assign 0xFEB0_0000.

    const WIFI_MMIO: u64 = 0xFEB0_0000;

    // Dump all BARs for diagnostics.
    unsafe {
        for i in 0usize..6 {
            let v = crate::pci::read32(dev.bus, dev.dev, dev.func, 0x10 + i as u8 * 4);
            uart::puts("rtw89: BAR"); uart::putu(i as u64);
            uart::puts("=0x"); uart::putx(v as u64); uart::puts("\r\n");
        }
    }

    let bar = unsafe {
        let raw2 = crate::pci::read32(dev.bus, dev.dev, dev.func, 0x18); // BAR2
        let raw3 = crate::pci::read32(dev.bus, dev.dev, dev.func, 0x1C); // BAR3

        if raw2 & 1 != 0 {
            // I/O BAR at index 2 — unexpected, try to find any memory BAR
            uart::puts("rtw89: BAR2 is I/O, scanning...\r\n");
            // Fall through to assignment
            crate::pci::write32(dev.bus, dev.dev, dev.func, 0x18, 0xFFFF_FFFF);
            let probe2 = crate::pci::read32(dev.bus, dev.dev, dev.func, 0x18);
            let is64 = (probe2 & 0x6) == 0x4;
            crate::pci::write32(dev.bus, dev.dev, dev.func, 0x18,
                                (WIFI_MMIO as u32) | (probe2 & 0xF));
            if is64 {
                crate::pci::write32(dev.bus, dev.dev, dev.func, 0x1C, 0);
            }
            WIFI_MMIO
        } else if raw2 == 0 || raw2 == 0xFFFF_FFF0 || raw2 == 0xFFFF_FFFF {
            // BAR2 not configured — probe and assign.
            crate::pci::write32(dev.bus, dev.dev, dev.func, 0x18, 0xFFFF_FFFF);
            let probe2 = crate::pci::read32(dev.bus, dev.dev, dev.func, 0x18);
            let is64 = (probe2 & 0x6) == 0x4;
            let size = (!(probe2 & 0xFFFF_FFF0)).wrapping_add(1);
            uart::puts("rtw89: BAR2 unconfigured, size=0x");
            uart::putx(size as u64); uart::puts("\r\n");
            crate::pci::write32(dev.bus, dev.dev, dev.func, 0x18,
                                (WIFI_MMIO as u32) | (probe2 & 0xF));
            if is64 {
                crate::pci::write32(dev.bus, dev.dev, dev.func, 0x1C, 0);
            }
            WIFI_MMIO
        } else if (raw2 & 0x6) == 0x4 {
            // 64-bit memory BAR, already configured.
            (raw2 & 0xFFFF_FFF0) as u64 | ((raw3 as u64) << 32)
        } else {
            // 32-bit memory BAR, already configured.
            (raw2 & 0xFFFF_FFF0) as u64
        }
    };
    uart::puts("rtw89: BAR0=0x");
    uart::putx(bar);
    uart::puts("\r\n");

    // Get firmware from ramdisk.
    let fw = match crate::ramdisk::find(b"rtw8852a.bin") {
        Some(f) => f,
        None => {
            uart::puts("rtw89: rtw8852a.bin not in ramdisk\r\n");
            uart::puts("       run install from USB with firmware on stick\r\n");
            return false;
        }
    };
    uart::puts("rtw89: firmware ");
    uart::putu(fw.len() as u64);
    uart::puts(" bytes\r\n");

    // Power on sequence.
    if !power_on(bar) { return false; }

    // Firmware download.
    if !fw_download(bar, fw) { return false; }

    // Read MAC address.
    let mac = read_mac(bar);
    uart::puts("rtw89: MAC=");
    for (i, b) in mac.iter().enumerate() {
        if i > 0 { uart::puts(":"); }
        let hi = b"0123456789abcdef"[(*b >> 4) as usize];
        let lo = b"0123456789abcdef"[(*b & 0xF) as usize];
        uart::putc(hi); uart::putc(lo);
    }
    uart::puts("\r\n");

    DRV = Some(Rtw89 { bar, mac, ready: true });
    uart::puts("rtw89: init complete — Sprint W2 (802.11 mgmt) next\r\n");
    true
}

// ── Shell hook ────────────────────────────────────────────────────────────────

pub fn status() {
    match get() {
        None => uart::puts("rtw89: not initialised\r\n"),
        Some(d) => {
            uart::puts("rtw89: ready  MAC=");
            for (i, b) in d.mac.iter().enumerate() {
                if i > 0 { uart::puts(":"); }
                let hi = b"0123456789abcdef"[(*b >> 4) as usize];
                let lo = b"0123456789abcdef"[(*b & 0xF) as usize];
                uart::putc(hi); uart::putc(lo);
            }
            uart::puts("\r\n");
        }
    }
}
