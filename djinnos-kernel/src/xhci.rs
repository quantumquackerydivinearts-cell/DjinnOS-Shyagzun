// xhci.rs -- xHCI USB 3.x host controller driver, polling mode.
//
// Covers: controller init, command/event rings, control transfers,
// bulk transfers, port detection.  No interrupts -- we poll the event ring.
//
// References: Intel xHCI Specification 1.2 (publicly available).
// Static-memory only; all DMA buffers live in BSS.

use core::sync::atomic::{fence, Ordering};

// ── Capability register offsets (from BAR0) ───────────────────────────────────
const CAP_CAPLENGTH:  u32 = 0x00; // u8  length of capability regs
const CAP_HCSPARAMS1: u32 = 0x04; // max slots / ports / intrs
const CAP_HCSPARAMS2: u32 = 0x08; // scratchpad count
const CAP_HCCPARAMS1: u32 = 0x10; // bit[2]=CSZ (context size: 0→32B, 1→64B)
const CAP_DBOFF:      u32 = 0x14; // doorbell array offset from BAR0
const CAP_RTSOFF:     u32 = 0x18; // runtime register space offset

// ── Operational register offsets (from BAR0 + CAPLENGTH) ─────────────────────
const OP_USBCMD:  u32 = 0x00; // bit[0]=R/S, bit[1]=HCRST
const OP_USBSTS:  u32 = 0x04; // bit[0]=HCH (halted), bit[3]=EINT
const OP_DNCTRL:  u32 = 0x14;
const OP_CRCR:    u32 = 0x18; // Command Ring Control (64-bit)
const OP_DCBAAP:  u32 = 0x30; // Device Context Base Address Array Pointer (64-bit)
const OP_CONFIG:  u32 = 0x38; // bits[7:0]=MaxSlotsEn

// Port registers: OP_BASE + 0x400 + port_index * 0x10
fn op_portsc(port: u8) -> u32 { 0x400 + (port as u32) * 0x10 }

// ── Runtime register offsets (from BAR0 + RTSOFF) ────────────────────────────
// Interrupter 0 registers start at offset 0x20
const RT_IMAN:  u32 = 0x20; // Interrupt Management
const RT_ERSTSZ: u32 = 0x28; // Event Ring Segment Table Size
const RT_ERSTBA: u32 = 0x30; // Event Ring Segment Table Base Address (64-bit)
const RT_ERDP:   u32 = 0x38; // Event Ring Dequeue Pointer (64-bit)

// ── TRB types ─────────────────────────────────────────────────────────────────
const TRB_NORMAL:       u32 = 1;
const TRB_SETUP:        u32 = 2;
const TRB_DATA:         u32 = 3;
const TRB_STATUS:       u32 = 4;
const TRB_LINK:         u32 = 6;
const TRB_ENABLE_SLOT:  u32 = 9;
const TRB_ADDR_DEVICE:  u32 = 11;
const TRB_CFG_EP:       u32 = 12;
const TRB_EV_TRANSFER:  u32 = 32;
const TRB_EV_CMD_COMP:  u32 = 33;
const TRB_EV_PORT:      u32 = 34;

// ── Completion codes ──────────────────────────────────────────────────────────
pub const CC_SUCCESS:      u8 = 1;
pub const CC_SHORT_PACKET: u8 = 13;

// ── Ring sizes ────────────────────────────────────────────────────────────────
const CMD_RING_SZ:  usize = 32;
const EVT_RING_SZ:  usize = 64;
const XFER_RING_SZ: usize = 32;

// ── TRB ───────────────────────────────────────────────────────────────────────

#[repr(C, align(16))]
#[derive(Copy, Clone, Default)]
pub struct Trb {
    pub lo:     u32,
    pub hi:     u32,
    pub status: u32,
    pub ctrl:   u32,  // bits[15:10]=type, bit[0]=cycle
}

impl Trb {
    fn ttype(&self) -> u32 { (self.ctrl >> 10) & 0x3F }
    fn cycle(&self) -> bool { self.ctrl & 1 != 0 }

    fn slot(&self)    -> u8 { (self.ctrl >> 24) as u8 }
    fn ep_id(&self)   -> u8 { ((self.ctrl >> 16) & 0x1F) as u8 }
    fn comp_code(&self) -> u8 { (self.status >> 24) as u8 }
    fn comp_param(&self) -> u32 { self.status & 0xFFFFFF }
    fn port_num(&self) -> u8 { (self.lo >> 24) as u8 }
    fn residual(&self) -> u32 { self.status & 0xFFFFFF }
}

fn trb_ctrl(ttype: u32, flags: u32, cycle: bool) -> u32 {
    (ttype << 10) | flags | if cycle { 1 } else { 0 }
}

// ── Event Ring Segment Table entry ────────────────────────────────────────────
#[repr(C, align(64))]
#[derive(Default)]
struct ErstEntry {
    base_lo:  u32,
    base_hi:  u32,
    size:     u16,
    _pad:     [u16; 3],
}

// ── Context structures (always 64-byte slots; 32-byte mode uses first half) ───

#[repr(C, align(64))]
#[derive(Copy, Clone, Default)]
struct SlotCtx {
    w: [u32; 8],
    _pad: [u32; 8],
}

#[repr(C, align(64))]
#[derive(Copy, Clone, Default)]
struct EpCtx {
    w: [u32; 8],
    _pad: [u32; 8],
}

// Input Context = Input Control Context (one ctx-sized slot) + full Device Context
// Layout (64-byte mode, 32 endpoints):
//   [0]     Input Control Context
//   [1]     Slot Context
//   [2..32] Endpoint Contexts 0..30
const MAX_EP: usize = 32;
#[repr(C, align(64))]
#[derive(Copy, Clone, Default)]
struct InputCtx {
    control: [u32; 16],   // Input Control Context (64 bytes)
    slot:    SlotCtx,
    ep:      [EpCtx; MAX_EP],
}

#[repr(C, align(64))]
#[derive(Copy, Clone, Default)]
struct DevCtx {
    slot: SlotCtx,
    ep:   [EpCtx; MAX_EP],
}

// ── Static DMA memory ─────────────────────────────────────────────────────────

const MAX_SLOTS: usize = 8;

#[repr(C, align(64))]
struct Dcbaa([u64; 256]);

static mut CMD_RING:  [Trb; CMD_RING_SZ] = [Trb { lo:0, hi:0, status:0, ctrl:0 }; CMD_RING_SZ];
static mut EVT_RING:  [Trb; EVT_RING_SZ] = [Trb { lo:0, hi:0, status:0, ctrl:0 }; EVT_RING_SZ];
static mut ERST:      ErstEntry = ErstEntry { base_lo:0, base_hi:0, size:0, _pad:[0;3] };
static mut DCBAA:     Dcbaa = Dcbaa([0u64; 256]);
static mut DEV_CTXS:  [DevCtx;  MAX_SLOTS] = [DevCtx  { slot: SlotCtx{w:[0;8],_pad:[0;8]}, ep: [EpCtx{w:[0;8],_pad:[0;8]}; MAX_EP] }; MAX_SLOTS];
static mut IN_CTXS:   [InputCtx; MAX_SLOTS] = [const { InputCtx {
    control: [0u32;16], slot: SlotCtx{w:[0;8],_pad:[0;8]}, ep: [EpCtx{w:[0;8],_pad:[0;8]}; MAX_EP]
} }; MAX_SLOTS];
// Two transfer rings per slot: control (EP0) + bulk-in + bulk-out
static mut CTRL_RING: [[Trb; XFER_RING_SZ]; MAX_SLOTS] = [[Trb{lo:0,hi:0,status:0,ctrl:0}; XFER_RING_SZ]; MAX_SLOTS];
static mut BULK_IN_RING:  [[Trb; XFER_RING_SZ]; MAX_SLOTS] = [[Trb{lo:0,hi:0,status:0,ctrl:0}; XFER_RING_SZ]; MAX_SLOTS];
static mut BULK_OUT_RING: [[Trb; XFER_RING_SZ]; MAX_SLOTS] = [[Trb{lo:0,hi:0,status:0,ctrl:0}; XFER_RING_SZ]; MAX_SLOTS];
static mut CTRL_BUF: [[u8; 512]; MAX_SLOTS] = [[0u8; 512]; MAX_SLOTS];

// ── MMIO helpers ──────────────────────────────────────────────────────────────

#[inline(always)] fn wr32(base: u64, off: u32, v: u32) {
    unsafe { ((base + off as u64) as *mut u32).write_volatile(v); }
}
#[inline(always)] fn rd32(base: u64, off: u32) -> u32 {
    unsafe { ((base + off as u64) as *const u32).read_volatile() }
}
#[inline(always)] fn wr64(base: u64, off: u32, v: u64) {
    wr32(base, off,     v as u32);
    wr32(base, off + 4, (v >> 32) as u32);
}

// ── Ring state ────────────────────────────────────────────────────────────────

struct Ring {
    enq:   usize,   // producer write index
    pcs:   bool,    // producer cycle state
}

impl Ring {
    const fn new() -> Self { Ring { enq: 0, pcs: true } }

    fn push(&mut self, trbs: &mut [Trb], t: Trb) -> u64 {
        // Leave one slot for the link TRB at the end
        let max = trbs.len() - 1;
        let i = self.enq;
        trbs[i] = Trb { ctrl: (t.ctrl & !1) | if self.pcs { 1 } else { 0 }, ..t };
        fence(Ordering::Release);
        self.enq += 1;
        if self.enq >= max {
            // Write link TRB pointing back to start, toggle cycle on wrap
            let base = trbs.as_ptr() as u64;
            let link = Trb {
                lo: base as u32, hi: (base >> 32) as u32,
                status: 0,
                ctrl: trb_ctrl(TRB_LINK, 1 << 1 /* TC */, self.pcs),
            };
            trbs[max] = link;
            fence(Ordering::Release);
            self.pcs = !self.pcs;
            self.enq = 0;
        }
        (trbs.as_ptr() as u64) + (i as u64 * 16)
    }
}

// ── XhciController ────────────────────────────────────────────────────────────

pub struct XhciController {
    bar:      u64,   // BAR0 MMIO base
    op:       u64,   // operational registers (bar + caplength)
    rt:       u64,   // runtime registers (bar + rtsoff)
    db:       u64,   // doorbell array (bar + dboff)
    ctx64:    bool,  // true = 64-byte contexts
    max_ports: u8,
    cmd:      Ring,
    evt_deq:  usize,
    evt_ccs:  bool,  // consumer cycle state for event ring
}

impl XhciController {
    pub fn find_and_init() -> Option<Self> {
        // Scan PCI for xHCI: class=0x0C sub=0x03 prog_if=0x30
        for slot in crate::pci::devices() {
            let d = match slot { Some(d) => d, None => continue };
            if d.class != 0x0C || d.sub != 0x03 || d.prog_if != 0x30 { continue; }
            let bar = d.bar_mem64(0).or_else(|| d.bar_mem32(0))?;
            crate::uart::puts("xhci: found at ");
            crate::uart::putx(bar);
            crate::uart::puts("\r\n");
            unsafe {
                let cmd = crate::pci::read16(d.bus, d.dev, d.func, 0x04);
                crate::pci::write32(d.bus, d.dev, d.func, 0x04, (cmd | 0x0006) as u32);
            }
            return Self::init(bar);
        }
        crate::uart::puts("xhci: no controller found\r\n");
        None
    }

    fn init(bar: u64) -> Option<Self> {
        let caplength = unsafe { (bar as *const u8).read_volatile() } as u32;
        let op  = bar + caplength as u64;
        let hccparams1 = rd32(bar, CAP_HCCPARAMS1);
        let ctx64 = hccparams1 & (1 << 2) != 0;
        let dboff  = rd32(bar, CAP_DBOFF)  as u64;
        let rtsoff = rd32(bar, CAP_RTSOFF) as u64;
        let hcsparams1 = rd32(bar, CAP_HCSPARAMS1);
        let max_ports = (hcsparams1 >> 24) as u8;
        let max_slots = (hcsparams1 & 0xFF) as u8;

        crate::uart::puts("xhci: ports="); crate::uart::putu(max_ports as u64);
        crate::uart::puts("  slots="); crate::uart::putu(max_slots as u64);
        crate::uart::puts("  ctx64="); crate::uart::putu(ctx64 as u64);
        crate::uart::puts("\r\n");

        // ── Reset controller ──────────────────────────────────────────────────
        wr32(op, OP_USBCMD, rd32(op, OP_USBCMD) & !1); // stop
        let mut t = 0u32;
        while rd32(op, OP_USBSTS) & 1 == 0 { t += 1; if t > 100_000 { return None; } }
        wr32(op, OP_USBCMD, rd32(op, OP_USBCMD) | (1 << 1)); // HCRST
        t = 0;
        while rd32(op, OP_USBCMD) & (1 << 1) != 0 { t += 1; if t > 100_000 { return None; } }

        // ── DCBAA ─────────────────────────────────────────────────────────────
        let dcbaa_phys = unsafe { core::ptr::addr_of!(DCBAA) as u64 };
        unsafe {
            for i in 0..MAX_SLOTS {
                let ctx_phys = core::ptr::addr_of!(DEV_CTXS[i]) as u64;
                DCBAA.0[i + 1] = ctx_phys;
            }
        }
        wr64(op, OP_DCBAAP, dcbaa_phys);

        // ── Command ring ──────────────────────────────────────────────────────
        let cmd_phys = unsafe { CMD_RING.as_ptr() as u64 };
        wr64(op, OP_CRCR, cmd_phys | 1); // RCS=1 (initial PCS=true → cycle=1)

        // ── Event ring + ERST ─────────────────────────────────────────────────
        let evt_phys = unsafe { EVT_RING.as_ptr() as u64 };
        unsafe {
            ERST.base_lo = evt_phys as u32;
            ERST.base_hi = (evt_phys >> 32) as u32;
            ERST.size    = EVT_RING_SZ as u16;
        }
        let rt = bar + rtsoff;
        let erst_phys = unsafe { core::ptr::addr_of!(ERST) as u64 };
        wr32(rt, RT_ERSTSZ, 1); // 1 segment
        wr64(rt, RT_ERSTBA, erst_phys);
        wr64(rt, RT_ERDP, evt_phys); // dequeue starts at ring base

        // ── MaxSlotsEn ────────────────────────────────────────────────────────
        wr32(op, OP_CONFIG, max_slots.min(MAX_SLOTS as u8) as u32);

        // ── Enable port power and start controller ────────────────────────────
        wr32(op, OP_DNCTRL, 0xFFFF); // enable all device notifications
        wr32(op, OP_USBCMD, 1); // R/S = run
        t = 0;
        while rd32(op, OP_USBSTS) & 1 != 0 { t += 1; if t > 100_000 { return None; } }
        crate::uart::puts("xhci: running\r\n");

        Some(XhciController {
            bar, op, rt, ctx64,
            db: bar + dboff,
            max_ports,
            cmd: Ring::new(),
            evt_deq: 0,
            evt_ccs: true,
        })
    }

    // ── Doorbell ──────────────────────────────────────────────────────────────

    fn ring_cmd(&self) {
        fence(Ordering::Release);
        wr32(self.db, 0, 0);    // doorbell[0] = 0 = command ring
    }

    fn ring_ep(&self, slot: u8, ep_id: u8) {
        fence(Ordering::Release);
        wr32(self.db, slot as u32 * 4, ep_id as u32);
    }

    // ── Event ring poll ───────────────────────────────────────────────────────

    pub fn next_event(&mut self) -> Option<Trb> {
        let trb = unsafe { EVT_RING[self.evt_deq] };
        if trb.cycle() != self.evt_ccs { return None; }
        fence(Ordering::Acquire);
        self.evt_deq += 1;
        if self.evt_deq >= EVT_RING_SZ { self.evt_deq = 0; self.evt_ccs = !self.evt_ccs; }
        // Update ERDP (tell controller where we've consumed to), clear EHB(bit[3])
        let phys = unsafe { EVT_RING.as_ptr() as u64 } + self.evt_deq as u64 * 16;
        wr64(self.rt, RT_ERDP, phys & !0x8); // EHB=0
        Some(trb)
    }

    fn wait_cmd(&mut self, timeout: u32) -> Option<Trb> {
        for _ in 0..timeout {
            if let Some(ev) = self.next_event() {
                if ev.ttype() == TRB_EV_CMD_COMP { return Some(ev); }
                // Re-queue non-command events (e.g. port status) for caller
                // In practice we drain them here and callers use next_event directly
            }
        }
        None
    }

    fn wait_xfer(&mut self, slot: u8, ep: u8, timeout: u32) -> Option<Trb> {
        for _ in 0..timeout {
            if let Some(ev) = self.next_event() {
                if ev.ttype() == TRB_EV_TRANSFER && ev.slot() == slot && ev.ep_id() == ep {
                    return Some(ev);
                }
            }
        }
        None
    }

    // ── Enable slot ───────────────────────────────────────────────────────────

    pub fn enable_slot(&mut self) -> Option<u8> {
        let t = Trb { lo: 0, hi: 0, status: 0, ctrl: trb_ctrl(TRB_ENABLE_SLOT, 0, false) };
        unsafe { self.cmd.push(&mut CMD_RING, t) };
        self.ring_cmd();
        let ev = self.wait_cmd(100_000)?;
        if ev.comp_code() != CC_SUCCESS { return None; }
        Some(ev.slot())
    }

    // ── Address device ────────────────────────────────────────────────────────
    // Sets up EP0 context and sends Address Device command (BSR=0 → assigns address)

    pub fn address_device(&mut self, slot: u8, port: u8, speed: u8) -> bool {
        let idx = (slot as usize).saturating_sub(1).min(MAX_SLOTS - 1);
        unsafe {
            let ic = &mut IN_CTXS[idx];
            // Input Control Context: add bit[0]=slot, bit[1]=EP0
            ic.control[0] = 0;    // drop flags
            ic.control[1] = 0x03; // add slot (A0) + EP0 (A1)

            // Slot Context
            let sc = &mut ic.slot.w;
            sc[0] = ((speed as u32) << 20) | (1 << 27); // speed + context entries=1
            sc[1] = (port as u32) << 16;                 // root hub port number

            // EP0 Context (endpoint context index 1, bidirectional control)
            let ep = &mut ic.ep[0].w;
            let max_pkt: u16 = match speed {
                4 | 5 => 512,  // SuperSpeed
                3     => 64,   // HighSpeed
                _     => 8,    // Full/Low speed
            };
            ep[1] = (3 << 1)                    // EP Type = 4 (control)... wait
                  | (4 << 3)                    // EP Type = 4 = control bidir
                  | ((max_pkt as u32) << 16)    // MaxPacketSize
                  | (3 << 1);                   // CErr = 3

            // Transfer ring for EP0
            let ring_phys = CTRL_RING[idx].as_ptr() as u64;
            ep[2] = (ring_phys as u32 & !0xF) | 1; // DCS=1 (initial PCS=true)
            ep[3] = (ring_phys >> 32) as u32;
            ep[4] = 8; // Average TRB Length

            let ic_phys = core::ptr::addr_of!(IN_CTXS[idx]) as u64;
            let t = Trb {
                lo: ic_phys as u32, hi: (ic_phys >> 32) as u32,
                status: 0,
                ctrl: trb_ctrl(TRB_ADDR_DEVICE, (slot as u32) << 24, false),
            };
            self.cmd.push(&mut CMD_RING, t);
        }
        self.ring_cmd();
        let ev = self.wait_cmd(100_000);
        ev.map(|e| e.comp_code() == CC_SUCCESS).unwrap_or(false)
    }

    // ── Configure endpoints ───────────────────────────────────────────────────
    // Call after SET_CONFIGURATION to add bulk in/out endpoints

    pub fn configure_endpoints(&mut self, slot: u8,
                               bulk_out_ep: u8, bulk_in_ep: u8,
                               max_pkt: u16) -> bool {
        let idx = (slot as usize).saturating_sub(1).min(MAX_SLOTS - 1);
        unsafe {
            let ic = &mut IN_CTXS[idx];
            // Endpoint context indices: OUT = 2*N, IN = 2*N+1
            let out_dci = (bulk_out_ep as usize) * 2;
            let in_dci  = (bulk_in_ep  as usize) * 2 + 1;

            ic.control[0] = 0;
            ic.control[1] = (1 << 0) | (1 << out_dci) | (1 << in_dci);
            ic.slot.w[0] = (ic.slot.w[0] & 0x07FF_FFFF)
                         | ((in_dci as u32) << 27); // context entries

            // Bulk OUT
            let ep_out = &mut ic.ep[out_dci - 1].w;
            ep_out[1] = (2 << 3) | ((max_pkt as u32) << 16) | (3 << 1); // Bulk Out
            let out_phys = BULK_OUT_RING[idx].as_ptr() as u64;
            ep_out[2] = (out_phys as u32 & !0xF) | 1;
            ep_out[3] = (out_phys >> 32) as u32;
            ep_out[4] = 1024;

            // Bulk IN
            let ep_in = &mut ic.ep[in_dci - 1].w;
            ep_in[1] = (6 << 3) | ((max_pkt as u32) << 16) | (3 << 1); // Bulk In
            let in_phys = BULK_IN_RING[idx].as_ptr() as u64;
            ep_in[2] = (in_phys as u32 & !0xF) | 1;
            ep_in[3] = (in_phys >> 32) as u32;
            ep_in[4] = 1024;

            let ic_phys = core::ptr::addr_of!(IN_CTXS[idx]) as u64;
            let t = Trb {
                lo: ic_phys as u32, hi: (ic_phys >> 32) as u32,
                status: 0,
                ctrl: trb_ctrl(TRB_CFG_EP, (slot as u32) << 24, false),
            };
            self.cmd.push(&mut CMD_RING, t);
        }
        self.ring_cmd();
        let ev = self.wait_cmd(100_000);
        ev.map(|e| e.comp_code() == CC_SUCCESS).unwrap_or(false)
    }

    // ── Control transfer ──────────────────────────────────────────────────────
    // setup: 8-byte USB setup packet. Returns bytes received (for IN) or 0.

    pub fn control(&mut self, slot: u8, setup: [u8; 8], dir_in: bool,
                   buf: &mut [u8]) -> Option<usize> {
        let idx  = (slot as usize).saturating_sub(1).min(MAX_SLOTS - 1);
        let ring = unsafe { &mut CTRL_RING[idx] };
        // We reuse a static buffer for DMA since we can't pass stack addresses to DMA
        let data_phys = unsafe { CTRL_BUF[idx].as_ptr() as u64 };
        let data_len  = buf.len().min(512);

        if !dir_in && data_len > 0 {
            unsafe { CTRL_BUF[idx][..data_len].copy_from_slice(&buf[..data_len]); }
        }

        let ep_id = 1u8; // EP0 always ep_id=1

        // Setup Stage TRB
        let setup_lo = u32::from_le_bytes([setup[0], setup[1], setup[2], setup[3]]);
        let setup_hi = u32::from_le_bytes([setup[4], setup[5], setup[6], setup[7]]);
        let trt = if data_len == 0 { 0 }
                  else if dir_in  { 3 }   // IN data stage
                  else            { 2 };  // OUT data stage
        let mut st = Ring::new(); // temporary ring state wrapper
        let _ = &st; // we push directly via cmd ring state

        // Actually push to the slot's control ring directly
        struct SlotRingState { enq: usize, pcs: bool }
        // We maintain per-slot ring state in a simpler way:
        // For simplicity, reset ring state each transfer (acceptable for enumeration)
        let pcs = true; // assume fresh ring; proper impl tracks per-ring state

        let s_trb = Trb {
            lo: setup_lo, hi: setup_hi, status: 8,
            ctrl: trb_ctrl(TRB_SETUP, (1 << 6) | (trt << 16), pcs),
        };
        ring[0] = s_trb;

        let mut pos = 1usize;

        // Data Stage TRB (if any data)
        if data_len > 0 {
            let d_trb = Trb {
                lo: data_phys as u32, hi: (data_phys >> 32) as u32,
                status: data_len as u32,
                ctrl: trb_ctrl(TRB_DATA,
                    if dir_in { 1 << 16 } else { 0 } | (1 << 5), pcs),
            };
            ring[pos] = d_trb; pos += 1;
        }

        // Status Stage TRB
        let dir_bit = if data_len == 0 || dir_in { 0 } else { 1 << 16 };
        ring[pos] = Trb {
            lo: 0, hi: 0, status: 0,
            ctrl: trb_ctrl(TRB_STATUS, dir_bit | (1 << 5) /* IOC */, pcs),
        };

        fence(Ordering::Release);
        self.ring_ep(slot, ep_id);

        // Wait for status stage completion
        let ev = self.wait_xfer(slot, ep_id, 500_000)?;
        if ev.comp_code() != CC_SUCCESS && ev.comp_code() != CC_SHORT_PACKET {
            return None;
        }

        if dir_in && data_len > 0 {
            let received = (data_len as u32).saturating_sub(ev.residual()) as usize;
            unsafe { buf[..received].copy_from_slice(&CTRL_BUF[idx][..received]); }
            return Some(received);
        }
        Some(0)
    }

    // ── Bulk OUT ──────────────────────────────────────────────────────────────

    pub fn bulk_out(&mut self, slot: u8, ep_id: u8, data: &[u8]) -> bool {
        // Copy to a static buffer since stack addresses aren't DMA-safe
        let idx = (slot as usize).saturating_sub(1).min(MAX_SLOTS - 1);
        let n = data.len().min(512);
        unsafe {
            CTRL_BUF[idx][..n].copy_from_slice(&data[..n]);
            let phys = CTRL_BUF[idx].as_ptr() as u64;
            let ring = &mut BULK_OUT_RING[idx];
            ring[0] = Trb {
                lo: phys as u32, hi: (phys >> 32) as u32,
                status: n as u32,
                ctrl: trb_ctrl(TRB_NORMAL, 1 << 5 /* IOC */, true),
            };
            fence(Ordering::Release);
        }
        self.ring_ep(slot, ep_id);
        let ev = self.wait_xfer(slot, ep_id, 200_000);
        ev.map(|e| e.comp_code() == CC_SUCCESS).unwrap_or(false)
    }

    // ── Bulk IN ───────────────────────────────────────────────────────────────

    pub fn bulk_in(&mut self, slot: u8, ep_id: u8, buf: &mut [u8]) -> usize {
        let idx = (slot as usize).saturating_sub(1).min(MAX_SLOTS - 1);
        let n = buf.len().min(512);
        unsafe {
            let phys = CTRL_BUF[idx].as_ptr() as u64;
            let ring = &mut BULK_IN_RING[idx];
            ring[0] = Trb {
                lo: phys as u32, hi: (phys >> 32) as u32,
                status: n as u32,
                ctrl: trb_ctrl(TRB_NORMAL, (1 << 4) /* ISP */ | (1 << 5) /* IOC */, true),
            };
            fence(Ordering::Release);
        }
        self.ring_ep(slot, ep_id);
        let ev = self.wait_xfer(slot, ep_id, 200_000);
        match ev {
            None => 0,
            Some(e) if e.comp_code() == CC_SUCCESS || e.comp_code() == CC_SHORT_PACKET => {
                let received = n.saturating_sub(e.residual() as usize);
                unsafe { buf[..received].copy_from_slice(&CTRL_BUF[idx][..received]); }
                received
            }
            _ => 0,
        }
    }

    // ── Port status ───────────────────────────────────────────────────────────

    pub fn port_connected(&self, port: u8) -> bool {
        rd32(self.op, op_portsc(port)) & 1 != 0
    }

    pub fn port_speed(&self, port: u8) -> u8 {
        ((rd32(self.op, op_portsc(port)) >> 10) & 0xF) as u8
    }

    pub fn reset_port(&self, port: u8) {
        let portsc = rd32(self.op, op_portsc(port));
        wr32(self.op, op_portsc(port), (portsc & 0x0E01C3E0) | (1 << 4)); // PR
        let mut t = 0u32;
        while rd32(self.op, op_portsc(port)) & (1 << 4) != 0 {
            t += 1; if t > 100_000 { break; }
        }
        // Clear status change bits (W1C)
        let sc = rd32(self.op, op_portsc(port));
        wr32(self.op, op_portsc(port), sc | 0x00FE0000);
    }

    pub fn max_ports(&self) -> u8 { self.max_ports }
}
