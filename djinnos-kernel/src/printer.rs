// printer.rs -- USB printer driver for DjinnOS.
//
// Targets: HP Officejet 6500A (and any USB class-7 PCL3-capable device).
//
// Connection: USB Type-B cable, xHCI host controller.
// Port:       USB class 7 (Printer), bulk OUT endpoint.
//
// Only active when the USB port is NOT in use for phone tethering.
// If x86net::usb_net_active() is true at init, the printer is unavailable
// until the phone is disconnected and DjinnOS is rebooted.
//
// Output format: PCL3 text mode.
//   The Officejet 6500A accepts basic PCL3 over USB for plain-text documents.
//   The printer's internal font renderer handles the typography.
//   If the Officejet firmware rejects PCL3 text (some revisions do),
//   the raster path (marked TODO below) is the fallback.
//
// Paper sizes supported (set in print_bkl / print_text):
//   2  = US Letter  (216 x 279 mm)
//   25 = A5         (148 x 210 mm)
//   26 = A4         (210 x 297 mm)
//
// Sending large print jobs:
//   xhci::bulk_out() sends up to max_pkt (512 bytes) per call.
//   bulk_stream() loops until all data is sent.

// -- PCL3 command constants ---------------------------------------------------

// Paper size PCL codes.
pub const PCL_PAPER_LETTER: u32 = 2;
pub const PCL_PAPER_A5:     u32 = 25;
pub const PCL_PAPER_A4:     u32 = 26;

// Pitch (characters per inch).
pub const PCL_PITCH_10: u32 = 10;   // standard Courier 10
pub const PCL_PITCH_12: u32 = 12;   // Courier 12 (fits ~57 chars on A5)

// Lines per inch.
pub const PCL_LPI_6: u32 = 6;       // 6 lpi = standard spacing
pub const PCL_LPI_8: u32 = 8;       // 8 lpi = compact

// -- Printer state ------------------------------------------------------------

pub struct PrinterState {
    slot:          u8,
    bulk_out_epid: u8,
    max_pkt:       u16,
    pub ready:     bool,
}

static mut PRINTER: Option<PrinterState> = None;

pub fn printer() -> Option<&'static mut PrinterState> {
    unsafe { PRINTER.as_mut() }
}

pub fn is_ready() -> bool {
    unsafe { PRINTER.as_ref().map_or(false, |p| p.ready) }
}

// -- Init ---------------------------------------------------------------------

/// Scan for a USB printer.  Must be called after x86net::init().
/// Safe to call even if USB tethering is active -- it will detect the conflict
/// and do nothing.
#[cfg(target_arch = "x86_64")]
pub fn init() {
    // If phone tethering consumed the xhci controller, we can't also use it
    // for the printer without a shared-controller refactor.  Leave the printer
    // unavailable and log the conflict.
    if crate::x86net::usb_net_active() {
        crate::uart::puts("printer: USB port in use for tethering -- printer unavailable\r\n");
        return;
    }

    // USB tethering is not active; try to find a printer on the USB bus.
    if let Some(mut xhci) = crate::xhci::XhciController::find_and_init() {
        if let Some(dev) = crate::usb::enumerate_printer(&mut xhci) {
            let ps = PrinterState {
                slot:          dev.slot,
                bulk_out_epid: dev.bulk_out_epid,
                max_pkt:       dev.max_pkt,
                ready:         true,
            };
            // Store xhci inside the static so it lives as long as the printer.
            unsafe {
                XHCI_FOR_PRINTER = Some(xhci);
                PRINTER = Some(ps);
            }
            crate::uart::puts("printer: ready\r\n");
        } else {
            crate::uart::puts("printer: no USB printer found\r\n");
        }
    }
}

#[cfg(not(target_arch = "x86_64"))]
pub fn init() {}   // RISC-V: no USB printer support yet.

// The xhci controller lives here when claimed for the printer.
#[cfg(target_arch = "x86_64")]
static mut XHCI_FOR_PRINTER: Option<crate::xhci::XhciController> = None;

#[cfg(target_arch = "x86_64")]
fn get_xhci() -> Option<&'static mut crate::xhci::XhciController> {
    unsafe { XHCI_FOR_PRINTER.as_mut() }
}
#[cfg(not(target_arch = "x86_64"))]
fn get_xhci() -> Option<&'static mut ()> { None }

// -- Bulk streaming -----------------------------------------------------------

/// Send `data` to the printer in max_pkt-sized chunks.
/// Returns true if all bytes were sent successfully.
fn bulk_stream(data: &[u8]) -> bool {
    #[cfg(not(target_arch = "x86_64"))]
    { let _ = data; return false; }
    #[cfg(target_arch = "x86_64")]
    {
        let ps   = match unsafe { PRINTER.as_ref() } { Some(p) => p, None => return false };
        let xhci = match get_xhci() { Some(x) => x, None => return false };
        let chunk = ps.max_pkt as usize;
        let mut pos = 0usize;
        while pos < data.len() {
            let end = (pos + chunk).min(data.len());
            if !xhci.bulk_out(ps.slot, ps.bulk_out_epid, &data[pos..end]) {
                return false;
            }
            pos = end;
        }
        true
    }
}

// -- PCL3 builder -------------------------------------------------------------
//
// Builds PCL commands into a fixed-size static scratch buffer,
// then streams to the printer in chunks.

const PCL_BUF: usize = 2048;
static mut PCL_SCRATCH: [u8; PCL_BUF] = [0u8; PCL_BUF];

struct PclBuf {
    n: usize,
}

impl PclBuf {
    fn new() -> Self { Self { n: 0 } }

    fn push(&mut self, b: u8) {
        let buf = unsafe { &mut PCL_SCRATCH };
        if self.n < PCL_BUF { buf[self.n] = b; self.n += 1; }
    }

    fn write(&mut self, s: &[u8]) {
        for &b in s { self.push(b); }
    }

    // PCL escape sequence: ESC followed by the given bytes.
    fn esc(&mut self, cmd: &[u8]) {
        self.push(0x1B);
        self.write(cmd);
    }

    // PCL numeric parameter: write digits of v.
    fn num(&mut self, v: u32) {
        if v == 0 { self.push(b'0'); return; }
        let mut tmp = [0u8; 10]; let mut n = 0; let mut x = v;
        while x > 0 { tmp[n] = b'0' + (x % 10) as u8; n += 1; x /= 10; }
        for i in (0..n).rev() { self.push(tmp[i]); }
    }

    fn flush(&mut self) -> bool {
        let buf = unsafe { &PCL_SCRATCH[..self.n] };
        let ok = bulk_stream(buf);
        self.n = 0;
        ok
    }
}

// -- PCL3 page setup ----------------------------------------------------------

fn pcl_page_header(pcl: &mut PclBuf, paper: u32, pitch: u32, lpi: u32) {
    pcl.esc(b"E");                  // Printer Reset
    pcl.esc(b"&l"); pcl.num(paper); pcl.push(b'A'); // paper size
    pcl.esc(b"&l0O");               // portrait orientation
    pcl.esc(b"&l"); pcl.num(lpi); pcl.push(b'D');   // lines per inch
    pcl.esc(b"(s0P");               // fixed-pitch spacing
    pcl.esc(b"(s"); pcl.num(pitch); pcl.push(b'H'); // characters per inch
    pcl.esc(b"(s0S");               // upright
    pcl.esc(b"(s0B");               // medium stroke weight
    pcl.esc(b"(0U");                // ISO-8859-1 symbol set
    // Set top-of-form margin: ~1 inch = 720 decipoints.
    pcl.esc(b"&l720E");
    // Perforation skip off (don't skip over page break area).
    pcl.esc(b"&l0L");
}

fn pcl_end_job(pcl: &mut PclBuf) {
    pcl.push(0x0C);   // form feed -- eject last page
    pcl.esc(b"E");    // reset
}

// -- Print a .bkl file --------------------------------------------------------
//
// .bkl format: pages delimited by form-feed (0x0C).
// Each page is typeset text lines separated by '\n'.
//
// PCL3 text mode: text is sent as-is; '\r\n' advances the line;
// 0x0C advances the page.

pub fn print_bkl(data: &[u8]) -> bool {
    if !is_ready() { return false; }
    let paper = pcl_paper_for_preset(crate::book::book().preset_idx);
    let mut pcl = PclBuf::new();
    pcl_page_header(&mut pcl, paper, PCL_PITCH_12, PCL_LPI_6);
    if !pcl.flush() { return false; }

    // Stream the .bkl content, replacing bare '\n' with '\r\n' and
    // passing 0x0C (form feed) directly as PCL page advance.
    const CHUNK: usize = 256;
    static mut LINE_BUF: [u8; CHUNK] = [0u8; CHUNK];
    let mut ln = 0usize;
    let buf = unsafe { &mut LINE_BUF };

    macro_rules! flush_line {
        () => {
            if ln > 0 {
                if !bulk_stream(&buf[..ln]) { return false; }
                ln = 0;
            }
        }
    }

    for &b in data {
        match b {
            b'\n' => {
                buf[ln] = b'\r'; ln += 1;
                buf[ln] = b'\n'; ln += 1;
                if ln + 2 >= CHUNK { flush_line!(); }
            }
            0x0C => {
                flush_line!();
                buf[ln] = 0x0C; ln += 1;
                flush_line!();
            }
            _ => {
                buf[ln] = b; ln += 1;
                if ln + 2 >= CHUNK { flush_line!(); }
            }
        }
    }
    flush_line!();

    let mut pcl = PclBuf::new();
    pcl_end_job(&mut pcl);
    pcl.flush()
}

/// Print a Sa-resident .bkl file by name.
pub fn print_sa_file(name: &[u8]) -> PrintResult {
    if !is_ready() { return PrintResult::NoPrinter; }
    const MAX_BKL: usize = 32768;
    static mut BKL_BUF: [u8; MAX_BKL] = [0u8; MAX_BKL];
    let n = crate::sa::read_file(name, unsafe { &mut BKL_BUF });
    if n == 0 { return PrintResult::FileNotFound; }
    if print_bkl(unsafe { &BKL_BUF[..n] }) {
        PrintResult::Ok
    } else {
        PrintResult::TransferError
    }
}

/// Print raw text (e.g. a binding spec) as a plain document.
pub fn print_text(data: &[u8], paper: u32) -> bool {
    if !is_ready() { return false; }
    let mut pcl = PclBuf::new();
    pcl_page_header(&mut pcl, paper, PCL_PITCH_10, PCL_LPI_6);
    if !pcl.flush() { return false; }

    const CHUNK: usize = 256;
    static mut TXT_BUF: [u8; CHUNK] = [0u8; CHUNK];
    let mut ln = 0usize;
    let buf = unsafe { &mut TXT_BUF };
    for &b in data {
        match b {
            0 => break,
            b'\n' => {
                buf[ln] = b'\r'; ln += 1;
                buf[ln] = b'\n'; ln += 1;
                if !bulk_stream(&buf[..ln]) { return false; }
                ln = 0;
            }
            _ => {
                buf[ln] = b; ln += 1;
                if ln + 2 >= CHUNK {
                    if !bulk_stream(&buf[..ln]) { return false; }
                    ln = 0;
                }
            }
        }
    }
    if ln > 0 && !bulk_stream(&buf[..ln]) { return false; }

    let mut pcl = PclBuf::new();
    pcl_end_job(&mut pcl);
    pcl.flush()
}

// -- Result type --------------------------------------------------------------

#[derive(Copy, Clone, PartialEq)]
pub enum PrintResult { Ok, NoPrinter, FileNotFound, TransferError }

impl PrintResult {
    pub fn as_bytes(&self) -> &'static [u8] {
        match self {
            Self::Ok            => b"print: sent",
            Self::NoPrinter     => b"print: no USB printer (not connected or USB in use for tethering)",
            Self::FileNotFound  => b"print: file not found",
            Self::TransferError => b"print: USB transfer error",
        }
    }
}

// -- PCL paper size from book preset index ------------------------------------

pub fn pcl_paper_for_preset(preset_idx: usize) -> u32 {
    // Matches PRESETS array order in book.rs:
    // 0=A5, 1=Trade(152x229), 2=Royal, 3=Demy, 4=Digest, 5=A6
    match preset_idx {
        0 | 5 => PCL_PAPER_A5,    // A5, A6 pocket -> print on A5 stock
        _     => PCL_PAPER_LETTER, // All others: print on Letter, centre on page
    }
}

// -- TODO: Raster path --------------------------------------------------------
//
// If PCL3 text mode is rejected by the firmware (some HP Officejet revisions
// only accept PCL3GUI raster), the fallback is to rasterize each page using
// the kernel's bitmap font at 2x scale on a 150 DPI grid, compress each raster
// row with PCL RLE (method 1), and send as PCL raster graphics:
//
//   ESC*r0A      -- enter raster
//   ESC*r<w>S    -- raster width in dots
//   ESC*r<h>T    -- raster height in dots
//   ESC*b1M      -- RLE compression
//   ESC*b<n>W<data> -- one raster row (repeat per row)
//   ESC*rB       -- end raster
//
// At 150 DPI, A5 page (148x210mm) = 874x1240 pixels.
// At 2x font scale, each char cell = 16x16px; text area = 54 cols x 77 lines.
// RLE-compressed raster for a text page is typically 20-40KB.
// Total for 128-page book: ~4MB, ~8000 bulk_out() calls at 512 bytes each.
//
// Implement when PCL3 text mode is confirmed non-functional on the Officejet.
