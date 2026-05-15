// nvme.rs — NVMe controller driver (installer subset).
//
// Supports exactly what the DjinnOS installer needs:
//   - PCI device discovery (class 0x01, sub 0x08)
//   - Controller reset and queue initialisation
//   - Identify Controller / Identify Namespace (sector size + count)
//   - LBA Read and Write (512-byte or 4096-byte sectors, polling)
//
// One controller, one namespace (nsid=1), one I/O queue pair.
// All I/O is polled — no interrupts, no MSI/MSI-X.
//
// Memory layout (all 4 KiB aligned, static):
//   Admin SQ : ADMIN_DEPTH × 64 B  = 1 KiB
//   Admin CQ : ADMIN_DEPTH × 16 B  = 256 B
//   I/O SQ   : IO_DEPTH    × 64 B  = 2 KiB
//   I/O CQ   : IO_DEPTH    × 16 B  = 512 B
//   Identify : 4 KiB (controller + namespace identify data)
//   Transfer : 4 KiB (single-page DMA window for read/write)
//
// Limitations:
//   - Transfers larger than one page require multiple calls to read_lba/write_lba.
//   - The transfer buffer is not re-entrant; do not call from an ISR.

use crate::uart;

// ── Queue depths ──────────────────────────────────────────────────────────────

const ADMIN_DEPTH: usize = 16;
const IO_DEPTH:    usize = 32;

// ── NVMe register offsets (BAR0 MMIO) ────────────────────────────────────────

const REG_CAP:  usize = 0x00;  // Controller Capabilities (64-bit)
const REG_VS:   usize = 0x08;  // Version
const REG_CC:   usize = 0x14;  // Controller Configuration
const REG_CSTS: usize = 0x1C;  // Controller Status
const REG_AQA:  usize = 0x24;  // Admin Queue Attributes
const REG_ASQ:  usize = 0x28;  // Admin SQ Base Address (64-bit)
const REG_ACQ:  usize = 0x30;  // Admin CQ Base Address (64-bit)

// CC field masks
const CC_EN:       u32 = 1 << 0;
const CC_IOCQES:   u32 = 4 << 20;  // 16-byte CQ entries (2^4)
const CC_IOSQES:   u32 = 6 << 16;  // 64-byte SQ entries (2^6)

// CSTS field masks
const CSTS_RDY:    u32 = 1 << 0;
const CSTS_CFS:    u32 = 1 << 1;   // Controller Fatal Status

// ── Submission queue entry (64 bytes) ────────────────────────────────────────

#[repr(C)]
#[derive(Copy, Clone)]
struct SQEntry {
    cdw0:  u32,  // opcode [7:0], fuse [9:8], cid [31:16]
    nsid:  u32,
    _res:  u64,
    mptr:  u64,
    prp1:  u64,  // physical address of data buffer (page 0)
    prp2:  u64,  // physical address of page 1, or PRP list
    cdw10: u32,
    cdw11: u32,
    cdw12: u32,
    cdw13: u32,
    cdw14: u32,
    cdw15: u32,
}

impl SQEntry {
    const fn zero() -> Self {
        Self { cdw0: 0, nsid: 0, _res: 0, mptr: 0,
               prp1: 0, prp2: 0,
               cdw10: 0, cdw11: 0, cdw12: 0,
               cdw13: 0, cdw14: 0, cdw15: 0 }
    }
}

// ── Completion queue entry (16 bytes) ─────────────────────────────────────────

#[repr(C)]
#[derive(Copy, Clone)]
struct CQEntry {
    dw0: u32,  // command-specific result
    dw1: u32,
    dw2: u32,  // [15:0] SQ head pointer, [31:16] SQ ID
    dw3: u32,  // [15:0] CID, [16] phase, [31:17] status
}

impl CQEntry {
    const fn zero() -> Self { Self { dw0: 0, dw1: 0, dw2: 0, dw3: 0 } }
    fn phase(&self)  -> u32 { (self.dw3 >> 16) & 1 }
    fn status(&self) -> u16 { ((self.dw3 >> 17) & 0x7FFF) as u16 }
    fn cid(&self)    -> u16 { (self.dw3 & 0xFFFF) as u16 }
}

// ── Admin opcodes ─────────────────────────────────────────────────────────────

const ADM_DELETE_SQ:    u8 = 0x00;
const ADM_CREATE_SQ:    u8 = 0x01;
const ADM_DELETE_CQ:    u8 = 0x04;
const ADM_CREATE_CQ:    u8 = 0x05;
const ADM_IDENTIFY:     u8 = 0x06;

// ── I/O opcodes ───────────────────────────────────────────────────────────────

const IO_WRITE: u8 = 0x01;
const IO_READ:  u8 = 0x02;

// ── Static DMA buffers (all 4 KiB aligned) ───────────────────────────────────

#[repr(C, align(4096))]
struct AdminSQ { e: [SQEntry; ADMIN_DEPTH] }

#[repr(C, align(4096))]
struct AdminCQ { e: [CQEntry; ADMIN_DEPTH] }

#[repr(C, align(4096))]
struct IoSQ { e: [SQEntry; IO_DEPTH] }

#[repr(C, align(4096))]
struct IoCQ { e: [CQEntry; IO_DEPTH] }

#[repr(C, align(4096))]
struct IdentifyBuf { data: [u8; 4096] }

#[repr(C, align(4096))]
pub struct TransferBuf { pub data: [u8; 4096] }

static mut ADMIN_SQ: AdminSQ = AdminSQ { e: [SQEntry::zero(); ADMIN_DEPTH] };
static mut ADMIN_CQ: AdminCQ = AdminCQ { e: [CQEntry::zero(); ADMIN_DEPTH] };
static mut IO_SQ:    IoSQ    = IoSQ    { e: [SQEntry::zero(); IO_DEPTH] };
static mut IO_CQ:    IoCQ    = IoCQ    { e: [CQEntry::zero(); IO_DEPTH] };
static mut IDENT:    IdentifyBuf = IdentifyBuf { data: [0u8; 4096] };
pub static mut XFER: TransferBuf = TransferBuf { data: [0u8; 4096] };

// ── Controller state ──────────────────────────────────────────────────────────

struct NvmeCtrl {
    bar:        u64,    // BAR0 MMIO base physical address
    dstrd:      u32,    // doorbell stride (4 << dstrd bytes between doorbells)
    // Admin queue cursors
    asq_tail:   u16,
    acq_head:   u16,
    acq_phase:  u32,
    // I/O queue cursors
    iosq_tail:  u16,
    iocq_head:  u16,
    iocq_phase: u32,
    // Namespace info
    pub lba_size:  u32,   // bytes per logical block (512 or 4096)
    pub lba_count: u64,   // total logical blocks on namespace 1
    // Command ID counter
    next_cid:   u16,
}

static mut CTRL: Option<NvmeCtrl> = None;

// ── MMIO helpers ──────────────────────────────────────────────────────────────

#[inline]
unsafe fn mmio_read32(base: u64, off: usize) -> u32 {
    ((base as usize + off) as *const u32).read_volatile()
}

#[inline]
unsafe fn mmio_write32(base: u64, off: usize, v: u32) {
    ((base as usize + off) as *mut u32).write_volatile(v);
}

#[inline]
unsafe fn mmio_read64(base: u64, off: usize) -> u64 {
    ((base as usize + off) as *const u64).read_volatile()
}

#[inline]
unsafe fn mmio_write64(base: u64, off: usize, v: u64) {
    ((base as usize + off) as *mut u64).write_volatile(v);
}

// ── Doorbell addresses ────────────────────────────────────────────────────────

fn sq_tail_db(bar: u64, qid: u32, dstrd: u32) -> u64 {
    bar + 0x1000 + (2 * qid * (4 << dstrd)) as u64
}

fn cq_head_db(bar: u64, qid: u32, dstrd: u32) -> u64 {
    bar + 0x1000 + ((2 * qid + 1) * (4 << dstrd)) as u64
}

// ── Wait helper (spin with timeout) ──────────────────────────────────────────

unsafe fn wait_csts_rdy(bar: u64, want: u32) -> bool {
    for _ in 0..500_000u32 {
        let csts = mmio_read32(bar, REG_CSTS);
        if csts & CSTS_CFS != 0 { uart::puts("nvme: CFS set\r\n"); return false; }
        if csts & CSTS_RDY == want { return true; }
        core::hint::spin_loop();
    }
    uart::puts("nvme: CSTS timeout\r\n");
    false
}

// ── Submit one admin command and poll for completion ──────────────────────────

unsafe fn admin_submit(c: &mut NvmeCtrl, mut entry: SQEntry) -> Option<u32> {
    let cid = c.next_cid;
    c.next_cid = c.next_cid.wrapping_add(1);
    entry.cdw0 = (entry.cdw0 & 0x0000_FFFF) | ((cid as u32) << 16);

    let tail = c.asq_tail as usize;
    ADMIN_SQ.e[tail] = entry;
    c.asq_tail = ((c.asq_tail + 1) as usize % ADMIN_DEPTH) as u16;

    // Ring the Admin SQ tail doorbell.
    (sq_tail_db(c.bar, 0, c.dstrd) as *mut u32)
        .write_volatile(c.asq_tail as u32);

    // Poll Admin CQ for a matching completion.
    for _ in 0..500_000u32 {
        let cqe = &ADMIN_CQ.e[c.acq_head as usize];
        if cqe.phase() == c.acq_phase && cqe.cid() == cid {
            let status = cqe.status();
            let sq_head = (cqe.dw2 & 0xFFFF) as u16;
            let result  = cqe.dw0;
            c.acq_head = ((c.acq_head + 1) as usize % ADMIN_DEPTH) as u16;
            if c.acq_head == 0 { c.acq_phase ^= 1; }
            // Ring ACQ head doorbell.
            (cq_head_db(c.bar, 0, c.dstrd) as *mut u32)
                .write_volatile(c.acq_head as u32);
            // Update SQ head pointer.
            c.asq_tail = sq_head;  // not strictly needed but keeps state sane
            if status != 0 {
                uart::puts("nvme: admin cmd status=0x");
                uart::putu(status as u64);
                uart::puts("\r\n");
                return None;
            }
            return Some(result);
        }
        core::hint::spin_loop();
    }
    uart::puts("nvme: admin cmd timeout\r\n");
    None
}

// ── Submit one I/O command and poll ──────────────────────────────────────────

unsafe fn io_submit(c: &mut NvmeCtrl, mut entry: SQEntry) -> bool {
    let cid = c.next_cid;
    c.next_cid = c.next_cid.wrapping_add(1);
    entry.cdw0 = (entry.cdw0 & 0x0000_FFFF) | ((cid as u32) << 16);

    let tail = c.iosq_tail as usize;
    IO_SQ.e[tail] = entry;
    c.iosq_tail = ((c.iosq_tail + 1) as usize % IO_DEPTH) as u16;

    (sq_tail_db(c.bar, 1, c.dstrd) as *mut u32)
        .write_volatile(c.iosq_tail as u32);

    for _ in 0..2_000_000u32 {
        let cqe = &IO_CQ.e[c.iocq_head as usize];
        if cqe.phase() == c.iocq_phase && cqe.cid() == cid {
            let status = cqe.status();
            c.iocq_head = ((c.iocq_head + 1) as usize % IO_DEPTH) as u16;
            if c.iocq_head == 0 { c.iocq_phase ^= 1; }
            (cq_head_db(c.bar, 1, c.dstrd) as *mut u32)
                .write_volatile(c.iocq_head as u32);
            if status != 0 {
                uart::puts("nvme: I/O status=0x");
                uart::putu(status as u64);
                uart::puts("\r\n");
                return false;
            }
            return true;
        }
        core::hint::spin_loop();
    }
    uart::puts("nvme: I/O timeout\r\n");
    false
}

// ── Identify helpers ──────────────────────────────────────────────────────────

unsafe fn identify_controller(c: &mut NvmeCtrl) -> bool {
    let buf_pa = core::ptr::addr_of!(IDENT) as u64;
    let mut e = SQEntry::zero();
    e.cdw0  = ADM_IDENTIFY as u32;
    e.nsid  = 0;
    e.prp1  = buf_pa;
    e.cdw10 = 1;  // CNS=1: Identify Controller
    admin_submit(c, e).is_some()
}

unsafe fn identify_namespace(c: &mut NvmeCtrl) -> bool {
    let buf_pa = core::ptr::addr_of!(IDENT) as u64;
    let mut e = SQEntry::zero();
    e.cdw0  = ADM_IDENTIFY as u32;
    e.nsid  = 1;
    e.prp1  = buf_pa;
    e.cdw10 = 0;  // CNS=0: Identify Namespace
    if admin_submit(c, e).is_none() { return false; }

    // NSIZE and NCAP at bytes 0 and 8; FLBAS at byte 26 selects LBA format.
    let nsize  = u64::from_le_bytes(IDENT.data[0..8].try_into().unwrap_or([0;8]));
    let flbas  = IDENT.data[26] & 0x0F;  // LBA format index
    // LBA format descriptor at offset 128 + flbas*4
    let lbaf_off = 128 + (flbas as usize) * 4;
    let lbads  = IDENT.data[lbaf_off + 3]; // LBA data size as 2^lbads
    let lba_sz = if lbads >= 9 && lbads <= 13 { 1u32 << lbads } else { 512 };

    c.lba_size  = lba_sz;
    c.lba_count = nsize;

    uart::puts("nvme: lba_size=");
    uart::putu(lba_sz as u64);
    uart::puts(" count=");
    uart::putu(nsize);
    uart::puts("\r\n");
    true
}

// ── Create I/O queues ─────────────────────────────────────────────────────────

unsafe fn create_io_queues(c: &mut NvmeCtrl) -> bool {
    let cq_pa = core::ptr::addr_of!(IO_CQ) as u64;
    let sq_pa = core::ptr::addr_of!(IO_SQ) as u64;

    // Create I/O Completion Queue 1.
    let mut e = SQEntry::zero();
    e.cdw0  = ADM_CREATE_CQ as u32;
    e.prp1  = cq_pa;
    e.cdw10 = (((IO_DEPTH as u32 - 1) << 16) | 1);  // QSIZE | QID=1
    e.cdw11 = 1;  // PC=1 (physically contiguous), interrupts disabled
    if admin_submit(c, e).is_none() { return false; }

    // Create I/O Submission Queue 1.
    let mut e = SQEntry::zero();
    e.cdw0  = ADM_CREATE_SQ as u32;
    e.prp1  = sq_pa;
    e.cdw10 = (((IO_DEPTH as u32 - 1) << 16) | 1);  // QSIZE | QID=1
    e.cdw11 = (1 << 16) | 1;  // CQID=1, PC=1
    admin_submit(c, e).is_some()
}

// ── Public: initialise ────────────────────────────────────────────────────────

#[cfg(target_arch = "x86_64")]
pub fn init() -> bool {
    unsafe { init_inner() }
}
#[cfg(not(target_arch = "x86_64"))]
pub fn init() -> bool { false }

#[cfg(target_arch = "x86_64")]
unsafe fn init_inner() -> bool {
    // Find NVMe controller: PCI class=0x01, sub=0x08.
    let dev = match crate::pci::find(0x01, 0x08) {
        Some(d) => d,
        None => {
            uart::puts("nvme: no NVMe controller found\r\n");
            return false;
        }
    };

    uart::puts("nvme: [");
    uart_hex16(dev.vendor);
    uart::puts(":");
    uart_hex16(dev.device);
    uart::puts("] bus=");
    uart_hex8(dev.bus);
    uart::puts(" dev=");
    uart_hex8(dev.dev);
    uart::puts("\r\n");

    // Enable PCI bus mastering (bit 2) and memory space (bit 1).
    unsafe {
        let cmd = crate::pci::read16(dev.bus, dev.dev, dev.func, 0x04);
        crate::pci::write32(dev.bus, dev.dev, dev.func, 0x04,
                            (cmd | 0x06) as u32);
    }

    // BAR0 is a 64-bit memory BAR.
    let bar = match dev.bar_mem64(0) {
        Some(b) => b,
        None => {
            uart::puts("nvme: BAR0 not a 64-bit memory BAR\r\n");
            return false;
        }
    };
    uart::puts("nvme: bar=0x");
    uart_hex64(bar);
    uart::puts("\r\n");

    // Read CAP for DSTRD and MQES.
    let cap   = mmio_read64(bar, REG_CAP);
    let dstrd = ((cap >> 32) & 0xF) as u32;
    let mqes  = ((cap & 0xFFFF) + 1) as usize;
    uart::puts("nvme: mqes=");
    uart::putu(mqes as u64);
    uart::puts("\r\n");

    // ── Reset controller ──────────────────────────────────────────────────────
    mmio_write32(bar, REG_CC, 0);   // CC.EN = 0
    if !wait_csts_rdy(bar, 0) { return false; }

    // ── Set up admin queues ───────────────────────────────────────────────────
    let asq_pa = core::ptr::addr_of!(ADMIN_SQ) as u64;
    let acq_pa = core::ptr::addr_of!(ADMIN_CQ) as u64;

    let aqa = ((ADMIN_DEPTH as u32 - 1) << 16) | (ADMIN_DEPTH as u32 - 1);
    mmio_write32(bar, REG_AQA, aqa);
    mmio_write64(bar, REG_ASQ, asq_pa);
    mmio_write64(bar, REG_ACQ, acq_pa);

    // ── Enable controller ─────────────────────────────────────────────────────
    let cc = CC_EN | CC_IOCQES | CC_IOSQES;
    mmio_write32(bar, REG_CC, cc);
    if !wait_csts_rdy(bar, CSTS_RDY) { return false; }

    uart::puts("nvme: controller ready\r\n");

    let mut ctrl = NvmeCtrl {
        bar,
        dstrd,
        asq_tail:   0,
        acq_head:   0,
        acq_phase:  1,
        iosq_tail:  0,
        iocq_head:  0,
        iocq_phase: 1,
        lba_size:   512,
        lba_count:  0,
        next_cid:   1,
    };

    if !identify_controller(&mut ctrl) { return false; }
    if !identify_namespace(&mut ctrl)  { return false; }
    if !create_io_queues(&mut ctrl)    { return false; }

    uart::puts("nvme: init complete\r\n");
    CTRL = Some(ctrl);
    true
}

// ── Public: LBA read into XFER buffer ────────────────────────────────────────
//
// Reads exactly one LBA-sized block at `lba` into XFER.data.
// For 512-byte sectors this reads 512 bytes; for 4096-byte sectors, 4096 bytes.
// Returns false on error.

pub fn read_lba(lba: u64) -> bool {
    unsafe {
        let c = match CTRL.as_mut() {
            Some(c) => c,
            None => { uart::puts("nvme: not init\r\n"); return false; }
        };
        let xfer_pa = core::ptr::addr_of!(XFER) as u64;
        let mut e = SQEntry::zero();
        e.cdw0  = IO_READ as u32;
        e.nsid  = 1;
        e.prp1  = xfer_pa;
        e.cdw10 = (lba & 0xFFFF_FFFF) as u32;
        e.cdw11 = (lba >> 32) as u32;
        e.cdw12 = 0;  // NLB = 0 → transfer 1 block
        io_submit(c, e)
    }
}

// ── Public: write XFER buffer to LBA ─────────────────────────────────────────
//
// Writes XFER.data (one LBA-sized block) to `lba`.

pub fn write_lba(lba: u64) -> bool {
    unsafe {
        let c = match CTRL.as_mut() {
            Some(c) => c,
            None => { uart::puts("nvme: not init\r\n"); return false; }
        };
        let xfer_pa = core::ptr::addr_of!(XFER) as u64;
        let mut e = SQEntry::zero();
        e.cdw0  = IO_WRITE as u32;
        e.nsid  = 1;
        e.prp1  = xfer_pa;
        e.cdw10 = (lba & 0xFFFF_FFFF) as u32;
        e.cdw11 = (lba >> 32) as u32;
        e.cdw12 = 0;  // NLB = 0 → transfer 1 block
        io_submit(c, e)
    }
}

// ── Public: accessors ─────────────────────────────────────────────────────────

pub fn lba_size()  -> u32 { unsafe { CTRL.as_ref().map(|c| c.lba_size).unwrap_or(512) } }
pub fn lba_count() -> u64 { unsafe { CTRL.as_ref().map(|c| c.lba_count).unwrap_or(0) } }
pub fn is_ready()  -> bool { unsafe { CTRL.is_some() } }

// ── UART hex helpers (local, avoids pulling in format!) ───────────────────────

fn uart_hex8(v: u8) {
    let d = b"0123456789abcdef";
    let b = [d[((v>>4)&0xF) as usize], d[(v&0xF) as usize]];
    uart::puts(core::str::from_utf8(&b).unwrap_or("??"));
}

fn uart_hex16(v: u16) {
    let d = b"0123456789abcdef";
    let b = [d[((v>>12)&0xF) as usize], d[((v>>8)&0xF) as usize],
             d[((v>>4)&0xF) as usize],  d[(v&0xF) as usize]];
    uart::puts(core::str::from_utf8(&b).unwrap_or("????"));
}

fn uart_hex64(v: u64) {
    for i in (0..16).rev() {
        let nib = ((v >> (i * 4)) & 0xF) as usize;
        uart::puts(core::str::from_utf8(
            &[b"0123456789abcdef"[nib]]).unwrap_or("?"));
    }
}
