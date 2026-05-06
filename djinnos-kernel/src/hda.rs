// Intel HDA (High Definition Audio) controller driver.
//
// Works with any HDA-compliant codec, including Realtek ALC (most consumer
// motherboards) and QEMU's virtual HDA codec (ich9-intel-hda).
//
// Architecture:
//   Controller (PCIe, class 04:03) ←CORB/RIRB→ Codec chips (Realtek, etc.)
//   Controller ←DMA streams→ Audio buffer in RAM → Codec DAC → analogue output
//
// Initialisation sequence:
//   1. Map BAR0 (MMIO register file)
//   2. Controller reset via GCTL
//   3. Allocate CORB / RIRB ring buffers; start DMA engines
//   4. Enumerate codecs via STATESTS; query each codec's AFG
//   5. Walk widget graph: find DAC → (mixer) → output pin path
//   6. Bind stream 1 to the DAC; set 48kHz/16-bit/stereo format
//   7. Set up stream descriptor + BDL pointing at static audio buffer
//   8. `play_tone(freq)` fills the buffer and starts the DMA

use core::ptr::{read_volatile, write_volatile};
use core::sync::atomic::{fence, Ordering};
use crate::{pci, uart};

// ── MMIO register offsets ─────────────────────────────────────────────────────

const GCAP:      u16 = 0x00;
const GCTL:      u16 = 0x08;
const WAKEEN:    u16 = 0x0C;
const STATESTS:  u16 = 0x0E;
const INTCTL:    u16 = 0x20;
const CORBLBASE: u16 = 0x40;
const CORBUBASE: u16 = 0x44;
const CORBWP:    u16 = 0x48;
const CORBRP:    u16 = 0x4A;
const CORBCTL:   u16 = 0x4C;
const CORBSIZE:  u16 = 0x4E;
const RIRBLBASE: u16 = 0x50;
const RIRBUBASE: u16 = 0x54;
const RIRBWP:    u16 = 0x58;
const RINTCNT:   u16 = 0x5A;
const RIRBCTL:   u16 = 0x5C;
const RIRBSTS:   u16 = 0x5D;
const RIRBSIZE:  u16 = 0x5E;

// Stream descriptor field offsets (relative to SD base)
const SD_CTL:   u16 = 0x00;
const SD_STS:   u16 = 0x03;
const SD_LPIB:  u16 = 0x04;
const SD_CBL:   u16 = 0x08;
const SD_LVI:   u16 = 0x0C;
const SD_FMT:   u16 = 0x12;
const SD_BDPL:  u16 = 0x18;
const SD_BDPU:  u16 = 0x1C;

// ── HDA verb helpers ──────────────────────────────────────────────────────────

// GET verbs (12-bit verb code + 8-bit param in bits 19:0)
const GET_PARAM:       u32 = 0xF0000;
const GET_CONN_LIST:   u32 = 0xF0200;
const GET_CONN_SEL:    u32 = 0xF0100;
const GET_PIN_CTRL:    u32 = 0xF0700;
const GET_EAPD_BTL:    u32 = 0xF0C00;
const GET_PIN_CFG:     u32 = 0xF1C00;
const GET_STREAM_FMT:  u32 = 0xA0000;

// SET verbs
const SET_POWER_STATE: u32 = 0x70500;  // payload = D0..D3
const SET_STREAM_CHAN:  u32 = 0x70600;  // payload = (stream<<4) | channel
const SET_STREAM_FMT:  u32 = 0x20000;  // 4-format: payload = format word
const SET_PIN_CTRL:    u32 = 0x70700;  // payload = pin control byte
const SET_EAPD_BTL:    u32 = 0x70C00;  // bit1=EAPD
const SET_AMP_OUT:     u32 = 0x30000;  // 4-format amp set (direction/chan/mute/gain in bits 15:0)

// GET_PARAM parameter IDs
const PAR_VENDOR_ID:   u8 = 0x00;
const PAR_REVISION_ID: u8 = 0x02;
const PAR_NODE_COUNT:  u8 = 0x04;
const PAR_FN_TYPE:     u8 = 0x05;
const PAR_WIDGET_CAP:  u8 = 0x09;
const PAR_PIN_CAP:     u8 = 0x0C;
const PAR_OUT_AMP:     u8 = 0x12;

// Widget types (bits 23:20 of WIDGET_CAP)
const WT_OUTPUT:  u8 = 0x0;
const WT_INPUT:   u8 = 0x1;
const WT_MIXER:   u8 = 0x2;
const WT_SELECTOR:u8 = 0x3;
const WT_PIN:     u8 = 0x4;

// Stream format word: 48kHz, 16-bit, stereo
// BASE=0 (48kHz), MULT=000 (×1), DIVN=000 (÷1), BITS=0001 (16b), CHAN=0001 (stereo)
const FMT_48K_16B_2CH: u16 = 0x0011;

// ── Static DMA buffers (identity-mapped → physical = virtual) ─────────────────

const CORB_ENTRIES: usize = 256;
const RIRB_ENTRIES: usize = 256;
const BDL_ENTRIES:  usize = 4;
const AUDIO_BYTES:  usize = 8192;  // 2048 stereo i16 samples (~42ms at 48kHz)

#[repr(C, align(128))]
struct CorbBuf([u32; CORB_ENTRIES]);

#[repr(C, align(128))]
struct RirbBuf([u64; RIRB_ENTRIES]);

#[repr(C, align(128))]
struct BdlBuf([BdlEntry; BDL_ENTRIES]);

#[repr(C, align(4096))]
struct AudioBuf([u8; AUDIO_BYTES]);

#[repr(C)]
#[derive(Clone, Copy)]
struct BdlEntry {
    addr_lo: u32,
    addr_hi: u32,
    len:     u32,
    flags:   u32,  // bit 0 = IOC
}

static mut CORB:  CorbBuf  = CorbBuf([0; CORB_ENTRIES]);
static mut RIRB:  RirbBuf  = RirbBuf([0; RIRB_ENTRIES]);
static mut BDL:   BdlBuf   = BdlBuf([BdlEntry { addr_lo: 0, addr_hi: 0, len: 0, flags: 0 }; BDL_ENTRIES]);
static mut AUDIO: AudioBuf = AudioBuf([0; AUDIO_BYTES]);

// ── Driver state ──────────────────────────────────────────────────────────────

pub struct HdaController {
    mmio:       u64,
    sd_base:    u16,
    codec_addr: u8,
    afg_nid:    u8,
    pub dac_nid: u8,
    pub pin_nid: u8,
    rirb_rp:    usize,
    pub vendor: u32,
    pub stream_running: bool,
}

static mut DRIVER: Option<HdaController> = None;

pub fn get() -> Option<&'static mut HdaController> {
    unsafe { DRIVER.as_mut() }
}

// ── Public init ───────────────────────────────────────────────────────────────

pub fn init() {
    let dev = match pci::find(0x04, 0x03) {
        Some(d) => d,
        None => { uart::puts("hda: no controller\r\n"); return; }
    };

    let bar0 = unsafe { pci::read32(dev.bus, dev.dev, dev.func, 0x10) };
    let bar1 = unsafe { pci::read32(dev.bus, dev.dev, dev.func, 0x14) };

    let mmio: u64 = if (bar0 >> 1) & 3 == 2 {
        // 64-bit BAR
        (bar0 & 0xFFFF_FFF0) as u64 | ((bar1 as u64) << 32)
    } else {
        (bar0 & 0xFFFF_FFF0) as u64
    };

    if mmio == 0 || mmio >= 0x1_0000_0000 {
        uart::puts("hda: BAR0 out of 4 GiB range\r\n");
        return;
    }

    // Enable PCI bus mastering and memory decode.
    let cmd = unsafe { pci::read16(dev.bus, dev.dev, dev.func, 0x04) };
    unsafe { pci::write32(dev.bus, dev.dev, dev.func, 0x04, (cmd | 0x06) as u32); }

    let mut hda = HdaController {
        mmio,
        sd_base: 0,
        codec_addr: 0,
        afg_nid: 0,
        dac_nid: 0,
        pin_nid: 0,
        rirb_rp: 0,
        vendor: 0,
        stream_running: false,
    };

    hda.reset_controller();
    hda.setup_corb();
    hda.setup_rirb();

    // Discover codecs (STATESTS bitmask).
    let statests = hda.read16(STATESTS);
    let mut found_codec = false;
    for i in 0u8..15 {
        if statests & (1 << i) != 0 {
            hda.codec_addr = i;
            found_codec = true;
            break;
        }
    }
    if !found_codec {
        uart::puts("hda: no codec detected\r\n");
        unsafe { DRIVER = Some(hda); }
        return;
    }

    hda.vendor = hda.send_verb(hda.codec_addr, 0, GET_PARAM | PAR_VENDOR_ID as u32);

    if hda.enumerate_afg() {
        hda.init_codec_path();
        hda.setup_stream();
    }

    uart::puts("hda: codec ");
    uart::putx((hda.vendor >> 16) as u64);
    uart::puts(":");
    uart::putx((hda.vendor & 0xFFFF) as u64);
    uart::puts("  dac=");
    uart::putu(hda.dac_nid as u64);
    uart::puts(" pin=");
    uart::putu(hda.pin_nid as u64);
    uart::puts("\r\n");

    unsafe { DRIVER = Some(hda); }
}

// ── Controller initialisation ─────────────────────────────────────────────────

impl HdaController {
    fn reset_controller(&mut self) {
        // Clear CRST to reset.
        self.write32(GCTL as u16, 0);
        spin_wait(|| self.read32(GCTL as u16) & 1 == 0);
        // Assert CRST.
        self.write32(GCTL as u16, 1);
        spin_wait(|| self.read32(GCTL as u16) & 1 != 0);
        // HDA spec: wait ≥521 µs after reset before codec enumeration.
        for _ in 0..500_000u32 { unsafe { core::arch::asm!("nop"); } }

        // Read GCAP to find first output stream descriptor offset.
        let gcap = self.read16(GCAP);
        let iss  = ((gcap >> 8) & 0xF) as u16;  // input stream count
        self.sd_base = 0x80 + iss * 0x20;
    }

    fn setup_corb(&mut self) {
        let phys = unsafe { core::ptr::addr_of!(CORB) as u64 };
        // Stop CORB DMA.
        self.write8(CORBCTL, 0);
        // Set size to 256 entries (0b10).
        self.write8(CORBSIZE, 0x02);
        // Write base address.
        self.write32(CORBLBASE, phys as u32);
        self.write32(CORBUBASE, (phys >> 32) as u32);
        // Reset CORB read pointer.
        self.write16(CORBRP, 0x8000);
        self.write16(CORBRP, 0x0000);
        // Reset write pointer.
        self.write16(CORBWP, 0);
        // Start CORB DMA.
        self.write8(CORBCTL, 0x02);
    }

    fn setup_rirb(&mut self) {
        let phys = unsafe { core::ptr::addr_of!(RIRB) as u64 };
        // Stop RIRB DMA.
        self.write8(RIRBCTL, 0);
        // Set size to 256 entries.
        self.write8(RIRBSIZE, 0x02);
        // Write base address.
        self.write32(RIRBLBASE, phys as u32);
        self.write32(RIRBUBASE, (phys >> 32) as u32);
        // Reset write pointer.
        self.write16(RIRBWP, 0x8000);
        // Set interrupt count.
        self.write16(RINTCNT, 0xFF);
        self.rirb_rp = 0;
        // Start RIRB DMA.
        self.write8(RIRBCTL, 0x02);
    }

    // ── Codec command / response ──────────────────────────────────────────────

    pub fn send_verb(&mut self, cad: u8, nid: u8, verb: u32) -> u32 {
        let cmd: u32 = ((cad as u32) << 28)
                     | ((nid as u32) << 20)
                     | (verb & 0xF_FFFF);
        unsafe {
            let wp = (self.read16(CORBWP) as usize + 1) & 0xFF;
            CORB.0[wp] = cmd;
            fence(Ordering::SeqCst);
            self.write16(CORBWP, wp as u16);

            // Poll RIRB write pointer for a new response.
            let mut timeout = 2_000_000u32;
            loop {
                fence(Ordering::SeqCst);
                let hwrp = self.read16(RIRBWP) as usize;
                if hwrp != self.rirb_rp {
                    self.rirb_rp = hwrp;
                    // Clear RIRB status.
                    self.write8(RIRBSTS, self.read8(RIRBSTS));
                    return (RIRB.0[hwrp] & 0xFFFF_FFFF) as u32;
                }
                timeout -= 1;
                if timeout == 0 { return 0xFFFF_FFFF; }
            }
        }
    }

    fn gp(&mut self, nid: u8, param: u8) -> u32 {
        self.send_verb(self.codec_addr, nid, GET_PARAM | param as u32)
    }

    // ── Codec enumeration ─────────────────────────────────────────────────────

    fn enumerate_afg(&mut self) -> bool {
        let node_count = self.gp(0, PAR_NODE_COUNT);
        let start = ((node_count >> 16) & 0xFF) as u8;
        let total = (node_count & 0xFF) as u8;

        for i in 0..total {
            let nid = start + i;
            let ftype = self.gp(nid, PAR_FN_TYPE) & 0xFF;
            if ftype == 0x01 {  // Audio Function Group
                self.afg_nid = nid;
                return self.find_dac_pin_path(nid);
            }
        }
        false
    }

    fn find_dac_pin_path(&mut self, afg: u8) -> bool {
        let nc  = self.gp(afg, PAR_NODE_COUNT);
        let start = ((nc >> 16) & 0xFF) as u8;
        let total = (nc & 0xFF) as u8;

        let mut first_dac: u8 = 0;
        let mut first_pin: u8 = 0;

        for i in 0..total.min(32) {
            let nid  = start + i;
            let wcap = self.gp(nid, PAR_WIDGET_CAP);
            let wtype = ((wcap >> 20) & 0xF) as u8;

            match wtype {
                WT_OUTPUT if first_dac == 0 => first_dac = nid,
                WT_PIN => {
                    let pcap = self.gp(nid, PAR_PIN_CAP);
                    let cfg  = self.send_verb(self.codec_addr, nid, GET_PIN_CFG);
                    // PIN_CAP bit 4 = output capable.
                    // Config default bits 31:30: 00=unknown, 01=jack, 10=no-connection, 11=fixed
                    let port = (cfg >> 30) & 0x3;
                    let loc  = (cfg >> 24) & 0xF;  // 0=N/A, 1=rear, 2=front
                    if pcap & (1 << 4) != 0 && port != 2 {
                        // Prefer rear/front-panel over N/A jacks
                        if first_pin == 0 || loc == 1 { first_pin = nid; }
                    }
                }
                _ => {}
            }
        }

        if first_dac != 0 && first_pin != 0 {
            self.dac_nid = first_dac;
            self.pin_nid = first_pin;
            true
        } else {
            // Fallback: use the path found even if incomplete
            self.dac_nid = if first_dac != 0 { first_dac } else { start };
            self.pin_nid = if first_pin != 0 { first_pin } else { start + 1 };
            first_dac != 0 || first_pin != 0
        }
    }

    // ── Codec path initialisation ─────────────────────────────────────────────

    fn init_codec_path(&mut self) {
        let cad = self.codec_addr;

        // Power up AFG and relevant widgets.
        self.send_verb(cad, self.afg_nid, SET_POWER_STATE | 0);
        self.send_verb(cad, self.dac_nid, SET_POWER_STATE | 0);
        self.send_verb(cad, self.pin_nid, SET_POWER_STATE | 0);

        // Bind stream 1, channel 0 to the DAC.
        self.send_verb(cad, self.dac_nid, SET_STREAM_CHAN | (1 << 4) | 0);

        // Set format on DAC: 48kHz, 16-bit, stereo.
        self.send_verb(cad, self.dac_nid, SET_STREAM_FMT | FMT_48K_16B_2CH as u32);

        // Unmute and set output amplifier on DAC (if it has one).
        let amp_cap = self.gp(self.dac_nid, PAR_OUT_AMP);
        if amp_cap != 0 {
            let max_gain = (amp_cap >> 8) & 0x7F;
            // AMP SET verb (4-format): bit15=OUTPUT, bit13=RIGHT, bit12=LEFT, bit7=MUTE, bits6:0=GAIN
            let gain = max_gain.min(0x57);  // use 0dB or max, whichever is lower
            let amp_verb = 0x30000
                | (1 << 15)   // output direction
                | (1 << 13)   // right channel
                | (1 << 12)   // left channel
                | gain;       // unmuted (bit7=0), gain value
            self.send_verb(cad, self.dac_nid, amp_verb);
        }

        // Enable output on the pin complex.
        // bit7=HeadphoneEnable, bit6=OutputEnable, bit5=InEnable, bit0=VRefEn
        let pin_cap = self.gp(self.pin_nid, PAR_PIN_CAP);
        let hp_bit  = if pin_cap & (1 << 3) != 0 { 0x80u32 } else { 0 };  // HP capable
        self.send_verb(cad, self.pin_nid, SET_PIN_CTRL | hp_bit | 0x40); // OutEnable | maybe HP

        // Unmute pin amplifier if present.
        let amp_cap = self.gp(self.pin_nid, PAR_OUT_AMP);
        if amp_cap != 0 {
            let max_gain = (amp_cap >> 8) & 0x7F;
            let amp_verb = 0x30000 | (1 << 15) | (1 << 13) | (1 << 12) | max_gain.min(0x57);
            self.send_verb(cad, self.pin_nid, amp_verb);
        }

        // Enable EAPD (external amp power-down) if available — common on Realtek.
        self.send_verb(cad, self.pin_nid, SET_EAPD_BTL | 0x02);
    }

    // ── DMA stream setup ──────────────────────────────────────────────────────

    fn setup_stream(&mut self) {
        let audio_phys = unsafe { core::ptr::addr_of!(AUDIO) as u64 };
        let bdl_phys   = unsafe { core::ptr::addr_of!(BDL)   as u64 };

        // Build BDL: two entries covering the full audio buffer.
        let half = (AUDIO_BYTES / 2) as u32;
        unsafe {
            BDL.0[0] = BdlEntry { addr_lo: audio_phys as u32, addr_hi: (audio_phys >> 32) as u32, len: half, flags: 1 };
            BDL.0[1] = BdlEntry { addr_lo: (audio_phys + half as u64) as u32, addr_hi: (audio_phys >> 32) as u32, len: half, flags: 1 };
        }

        let sd = self.sd_base;

        // Stop stream, clear status.
        self.write_sd8(sd, SD_CTL,  0);
        self.write_sd8(sd, SD_STS, 0x1C);

        // Set stream number in SD_CTL (bits 23:20 = stream tag, use 1).
        // Also set data direction and stream number: bit 19:16 = stripe, bits 23:20 = tag
        // SD_CTL[2:0] = run/dma/irq, bits 23:20 = stream tag
        // Write to the byte at +3 (high byte of the 3-byte CTL register)
        let ctl_hi_off = sd + SD_CTL + 2;
        self.write_sd8(sd, SD_CTL + 2, 0x10);  // stream tag = 1 (bits 7:4)

        // Buffer parameters.
        self.write_sd32(sd, SD_CBL, AUDIO_BYTES as u32);  // cyclic buffer length
        self.write_sd16(sd, SD_LVI, 1);                   // last valid BDL index (2 entries → 1)

        // Sample format.
        self.write_sd16(sd, SD_FMT, FMT_48K_16B_2CH);

        // BDL address.
        self.write_sd32(sd, SD_BDPL, bdl_phys as u32);
        self.write_sd32(sd, SD_BDPU, (bdl_phys >> 32) as u32);
    }

    // ── Audio generation and playback ─────────────────────────────────────────

    /// Fill the DMA buffer with a square wave at `freq_hz` and start the stream.
    pub fn play_tone(&mut self, freq_hz: u32) {
        const SAMPLE_RATE: u32 = 48000;
        let period = if freq_hz > 0 { SAMPLE_RATE / freq_hz } else { 1 };
        let amp: i16 = 12000;

        unsafe {
            let buf = &mut AUDIO.0;
            let total_samples = AUDIO_BYTES / 4;  // stereo i16 pairs
            for i in 0..total_samples {
                let phase = (i as u32) % period;
                let sample: i16 = if phase < period / 2 { amp } else { -amp };
                let ptr = buf.as_mut_ptr().add(i * 4) as *mut i16;
                ptr.write(sample);          // left
                ptr.add(1).write(sample);   // right
            }
            fence(Ordering::SeqCst);
        }

        self.start_stream();
    }

    /// Stop audio output.
    pub fn stop(&mut self) {
        let sd = self.sd_base;
        let ctl = self.read_sd8(sd, SD_CTL);
        self.write_sd8(sd, SD_CTL, ctl & !0x02);  // clear RUN bit
        self.stream_running = false;
    }

    fn start_stream(&mut self) {
        let sd = self.sd_base;
        let ctl = self.read_sd8(sd, SD_CTL);
        self.write_sd8(sd, SD_CTL, ctl | 0x02);   // set RUN bit
        self.stream_running = true;
    }

    // ── MMIO accessors ────────────────────────────────────────────────────────

    fn read8(&self, off: u16) -> u8 {
        unsafe { read_volatile((self.mmio + off as u64) as *const u8) }
    }
    fn read16(&self, off: u16) -> u16 {
        unsafe { read_volatile((self.mmio + off as u64) as *const u16) }
    }
    fn read32(&self, off: u16) -> u32 {
        unsafe { read_volatile((self.mmio + off as u64) as *const u32) }
    }
    fn write8(&self, off: u16, v: u8) {
        unsafe { write_volatile((self.mmio + off as u64) as *mut u8, v) }
    }
    fn write16(&self, off: u16, v: u16) {
        unsafe { write_volatile((self.mmio + off as u64) as *mut u16, v) }
    }
    fn write32(&self, off: u16, v: u32) {
        unsafe { write_volatile((self.mmio + off as u64) as *mut u32, v) }
    }

    // Stream descriptor accessors (use sd_base + field offset)
    fn read_sd8(&self,  sd: u16, f: u16) -> u8  { self.read8(sd + f) }
    fn read_sd16(&self, sd: u16, f: u16) -> u16 { self.read16(sd + f) }
    fn write_sd8(&self,  sd: u16, f: u16, v: u8)  { self.write8(sd + f, v) }
    fn write_sd16(&self, sd: u16, f: u16, v: u16) { self.write16(sd + f, v) }
    fn write_sd32(&self, sd: u16, f: u16, v: u32) { self.write32(sd + f, v) }
}

// ── Spinwait helper ───────────────────────────────────────────────────────────

fn spin_wait(cond: impl Fn() -> bool) {
    let mut n = 0u32;
    while !cond() {
        n += 1;
        if n > 10_000_000 { break; }
        unsafe { core::arch::asm!("pause"); }
    }
}
