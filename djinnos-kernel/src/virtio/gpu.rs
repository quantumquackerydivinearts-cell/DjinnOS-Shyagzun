// VirtIO GPU driver — polling mode.
//
// Implements the minimal command set needed for a framebuffer display:
//   1. GET_DISPLAY_INFO   → learn screen dimensions
//   2. RESOURCE_CREATE_2D → allocate a host-side resource
//   3. RESOURCE_ATTACH_BACKING → link our physical framebuffer pages
//   4. SET_SCANOUT        → connect resource to the physical display
//   5. TRANSFER_TO_HOST_2D → mark our writes as ready
//   6. RESOURCE_FLUSH     → push to screen
//
// Framebuffer format: BGRX8888 (4 bytes per pixel, blue first).

use super::mmio::{VirtioMmio, *};
use super::queue::{VirtQueue, Descriptor, AvailRing, UsedRing, UsedElem, QUEUE_SIZE};
use core::ptr::write_volatile;

// ── VirtIO GPU command types ─────────────────────────────────────────────────

const CMD_GET_DISPLAY_INFO:     u32 = 0x0100;
const CMD_RESOURCE_CREATE_2D:   u32 = 0x0101;
const CMD_SET_SCANOUT:          u32 = 0x0103;
const CMD_RESOURCE_FLUSH:       u32 = 0x0104;
const CMD_TRANSFER_TO_HOST_2D:  u32 = 0x0105;
const CMD_RESOURCE_ATTACH_BACKING: u32 = 0x0106;

const RESP_OK_NODATA:           u32 = 0x1100;
const RESP_OK_DISPLAY_INFO:     u32 = 0x1101;

const FORMAT_BGRX8888: u32 = 1;
const RESOURCE_ID:     u32 = 1;   // arbitrary non-zero resource handle

// Framebuffer lives at a fixed physical address (96 MiB into RAM).
// 1280 × 800 × 4 = 4 096 000 bytes ≈ 4 MiB — well within QEMU's 128 MiB.
pub const FB_PHYS: u64   = 0x80000000 + 96 * 1024 * 1024;
pub const FB_MAX_W: u32  = 1280;
pub const FB_MAX_H: u32  = 800;

// ── Command / response wire structs ─────────────────────────────────────────

#[repr(C)]
struct CtrlHdr {
    type_:    u32,
    flags:    u32,
    fence_id: u64,
    ctx_id:   u32,
    padding:  u32,
}

impl CtrlHdr {
    const fn cmd(t: u32) -> Self {
        Self { type_: t, flags: 0, fence_id: 0, ctx_id: 0, padding: 0 }
    }
}

#[repr(C)] struct Rect { x: u32, y: u32, w: u32, h: u32 }

#[repr(C)]
struct DisplayInfo {
    hdr:   CtrlHdr,
    pmodes: [DisplayMode; 16],
}
#[repr(C)]
struct DisplayMode {
    rect:    Rect,
    enabled: u32,
    flags:   u32,
}

#[repr(C)]
struct ResourceCreate2d {
    hdr:         CtrlHdr,
    resource_id: u32,
    format:      u32,
    width:        u32,
    height:       u32,
}

#[repr(C)]
struct ResourceAttachBacking {
    hdr:         CtrlHdr,
    resource_id: u32,
    nr_entries:  u32,
    addr:        u64,
    length:      u32,
    padding:     u32,
}

#[repr(C)]
struct SetScanout {
    hdr:         CtrlHdr,
    r:           Rect,
    scanout_id:  u32,
    resource_id: u32,
}

#[repr(C)]
struct TransferToHost {
    hdr:         CtrlHdr,
    r:           Rect,
    offset:      u64,
    resource_id: u32,
    padding:     u32,
}

#[repr(C)]
struct ResourceFlush {
    hdr:         CtrlHdr,
    r:           Rect,
    resource_id: u32,
    padding:     u32,
}

// ── Static queue memory ───────────────────────────────────────────────────────
//
// VirtIO MMIO v1 (legacy) requires a specific page-aligned layout:
//   Page 0: descriptor table (1024 B) + available ring (134 B) + padding
//   Page 1: used ring (518 B)
//
// The entire block is referenced by a single page-frame-number written to
// REG_QUEUE_PFN.  Offsets within it are fixed by the spec.

const V1_QUEUE_BYTES: usize = 8192;  // 2 × 4096-byte pages

#[repr(C, align(4096))]
struct V1QueueMem([u8; V1_QUEUE_BYTES]);

static mut CTRL_QUEUE_MEM: V1QueueMem = V1QueueMem([0u8; V1_QUEUE_BYTES]);

// Byte offsets within V1QueueMem (queue size = 64)
const V1_DESC_OFF:  usize = 0;                       // 0
const V1_AVAIL_OFF: usize = QUEUE_SIZE * 16;          // 1024
const V1_USED_OFF:  usize = 4096;                     // page-aligned gap

// Staging buffers for commands and responses.
static mut CMD:  [u8; 256] = [0u8; 256];
static mut RESP: [u8; 256] = [0u8; 256];

// ── GpuDriver ────────────────────────────────────────────────────────────────

pub struct GpuDriver {
    dev:    VirtioMmio,
    queue:  VirtQueue,
    pub width:  u32,
    pub height: u32,
}

impl GpuDriver {
    /// Initialise the VirtIO GPU at `base`.  Returns None if negotiation fails.
    pub fn init(base: u64) -> Option<Self> {
        let dev = VirtioMmio::new(base);

        // Device initialisation sequence (VirtIO spec §3.1.1)
        dev.write(REG_STATUS, 0);                                    // reset
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE);
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE | STATUS_DRIVER);

        // Accept no optional features for now
        dev.write(REG_DEVICE_FEAT_SEL,  0);
        dev.write(REG_DRIVER_FEAT_SEL, 0);
        dev.write(REG_DRIVER_FEATURES,  0);

        let s = dev.read(REG_STATUS) | STATUS_FEATURES_OK;
        dev.write(REG_STATUS, s);
        if dev.read(REG_STATUS) & STATUS_FEATURES_OK == 0 { return None; }

        // Set up control queue (queue 0) — v1 legacy protocol
        dev.write(REG_GUEST_PAGE_SIZE, 4096);
        dev.write(REG_QUEUE_SEL, 0);
        let qmax = dev.read(REG_QUEUE_NUM_MAX) as usize;
        if qmax < QUEUE_SIZE { return None; }
        dev.write(REG_QUEUE_NUM,   QUEUE_SIZE as u32);
        dev.write(REG_QUEUE_ALIGN, 4096);

        let base_phys = unsafe {
            CTRL_QUEUE_MEM.0.as_ptr() as u64
        };
        dev.write(REG_QUEUE_PFN, (base_phys >> 12) as u32);

        dev.write(REG_STATUS, dev.read(REG_STATUS) | STATUS_DRIVER_OK);

        // Build VirtQueue view over the raw bytes (raw pointers — no aliasing UB)
        let queue = unsafe {
            let base  = CTRL_QUEUE_MEM.0.as_mut_ptr();
            let desc  = base.add(V1_DESC_OFF)  as *mut [Descriptor; QUEUE_SIZE];
            let avail = base.add(V1_AVAIL_OFF) as *mut AvailRing;
            let used  = base.add(V1_USED_OFF)  as *const UsedRing;
            // VIRTQ_AVAIL_F_NO_INTERRUPT: we poll used.idx directly; tell the
            // device not to raise interrupts.  Un-acked interrupts accumulate in
            // QEMU and eventually cause the device to stop writing to used ring.
            core::ptr::write_volatile(&mut (*avail).flags, 1u16);
            VirtQueue::new(desc, avail, used)
        };

        let mut gpu = GpuDriver { dev, queue, width: FB_MAX_W, height: FB_MAX_H };

        // Discover real display dimensions
        if let Some((w, h)) = gpu.get_display_info() {
            gpu.width  = w.min(FB_MAX_W);
            gpu.height = h.min(FB_MAX_H);
        }

        // Create resource, attach backing, set scanout
        gpu.resource_create_2d();
        gpu.resource_attach_backing();
        gpu.set_scanout();

        Some(gpu)
    }

    fn send_cmd<T>(&mut self, cmd: &T, cmd_size: u32) {
        unsafe {
            // Volatile byte-by-byte copy into CMD: the GPU reads this buffer via DMA.
            // Non-volatile copy_nonoverlapping is eliminated by LTO when it sees no
            // Rust-visible read of CMD — causing the GPU to process stale/garbage data.
            let src = cmd as *const T as *const u8;
            let dst = CMD.as_mut_ptr();
            for i in 0..cmd_size as usize {
                core::ptr::write_volatile(dst.add(i), src.add(i).read());
            }
            let cmd_phys  = CMD.as_ptr()  as u64;
            let resp_phys = RESP.as_ptr() as u64;
            self.queue.send(cmd_phys, cmd_size, resp_phys, 64);
            self.dev.write(REG_QUEUE_NOTIFY, 0);
            self.queue.poll();
        }
    }

    fn get_display_info(&mut self) -> Option<(u32, u32)> {
        let cmd = CtrlHdr::cmd(CMD_GET_DISPLAY_INFO);
        self.send_cmd(&cmd, core::mem::size_of::<CtrlHdr>() as u32);
        unsafe {
            // Volatile reads from RESP: the GPU writes this buffer via DMA.
            // Non-volatile reads risk the compiler caching a pre-DMA value.
            // DisplayInfo layout: hdr(24) + pmodes[0]: rect{x,y,w,h}(16) + enabled(4) + flags(4)
            //   hdr.type_           offset 0
            //   pmodes[0].rect.w    offset 32
            //   pmodes[0].rect.h    offset 36
            //   pmodes[0].enabled   offset 40
            let resp = RESP.as_ptr();
            let hdr_type = core::ptr::read_volatile(resp as *const u32);
            let w       = core::ptr::read_volatile((resp as *const u8).add(32) as *const u32);
            let h       = core::ptr::read_volatile((resp as *const u8).add(36) as *const u32);
            let enabled = core::ptr::read_volatile((resp as *const u8).add(40) as *const u32);
            if hdr_type == RESP_OK_DISPLAY_INFO && enabled != 0 {
                if w > 0 && h > 0 { return Some((w, h)); }
            }
        }
        None
    }

    fn resource_create_2d(&mut self) {
        let cmd = ResourceCreate2d {
            hdr:         CtrlHdr::cmd(CMD_RESOURCE_CREATE_2D),
            resource_id: RESOURCE_ID,
            format:      FORMAT_BGRX8888,
            width:        self.width,
            height:       self.height,
        };
        self.send_cmd(&cmd, core::mem::size_of::<ResourceCreate2d>() as u32);
    }

    fn resource_attach_backing(&mut self) {
        let fb_len = self.width * self.height * 4;
        let cmd = ResourceAttachBacking {
            hdr:         CtrlHdr::cmd(CMD_RESOURCE_ATTACH_BACKING),
            resource_id: RESOURCE_ID,
            nr_entries:  1,
            addr:        FB_PHYS,
            length:      fb_len,
            padding:     0,
        };
        self.send_cmd(&cmd, core::mem::size_of::<ResourceAttachBacking>() as u32);
    }

    fn set_scanout(&mut self) {
        let cmd = SetScanout {
            hdr:         CtrlHdr::cmd(CMD_SET_SCANOUT),
            r:           Rect { x: 0, y: 0, w: self.width, h: self.height },
            scanout_id:  0,
            resource_id: RESOURCE_ID,
        };
        self.send_cmd(&cmd, core::mem::size_of::<SetScanout>() as u32);
    }

    /// Write pixel data to the physical framebuffer then flush to screen.
    pub fn flush(&mut self) {
        // Tell the host our pixel data is ready
        let transfer = TransferToHost {
            hdr:         CtrlHdr::cmd(CMD_TRANSFER_TO_HOST_2D),
            r:           Rect { x: 0, y: 0, w: self.width, h: self.height },
            offset:      0,
            resource_id: RESOURCE_ID,
            padding:     0,
        };
        self.send_cmd(&transfer, core::mem::size_of::<TransferToHost>() as u32);

        // Flush to display
        let flush = ResourceFlush {
            hdr:         CtrlHdr::cmd(CMD_RESOURCE_FLUSH),
            r:           Rect { x: 0, y: 0, w: self.width, h: self.height },
            resource_id: RESOURCE_ID,
            padding:     0,
        };
        self.send_cmd(&flush, core::mem::size_of::<ResourceFlush>() as u32);
    }

    /// Fill the entire screen with a solid colour (BGRX format).
    pub fn fill(&self, b: u8, g: u8, r: u8) {  // also used directly in splash()
        let pixel: u32 = (r as u32) << 16 | (g as u32) << 8 | (b as u32);
        let count = (self.width * self.height) as usize;
        let fb = FB_PHYS as *mut u32;
        for i in 0..count {
            unsafe { write_volatile(fb.add(i), pixel); }
        }
    }

    /// Write a single pixel at (x, y).
    pub fn set_pixel(&self, x: u32, y: u32, b: u8, g: u8, r: u8) {
        if x >= self.width || y >= self.height { return; }
        let idx = (y * self.width + x) as usize;
        let pixel: u32 = (r as u32) << 16 | (g as u32) << 8 | (b as u32);
        unsafe { write_volatile((FB_PHYS as *mut u32).add(idx), pixel); }
    }
}

// ── GpuSurface implementation ─────────────────────────────────────────────────

impl crate::gpu::GpuSurface for GpuDriver {
    fn width(&self)  -> u32 { self.width  }
    fn height(&self) -> u32 { self.height }
    fn set_pixel(&self, x: u32, y: u32, b: u8, g: u8, r: u8) { self.set_pixel(x, y, b, g, r) }
    fn fill(&self, b: u8, g: u8, r: u8)                       { self.fill(b, g, r) }
    fn flush(&mut self)                                         { self.flush() }

    /// #[inline(never)] keeps this a real function call from Shell::render.
    /// write_volatile prevents −Oz from miscomputing the pixel address via
    /// the slli/srli register trick that causes the sepc=0x100 / stval crash.
    #[inline(never)]
    fn fill_rect(&self, x: u32, y: u32, rw: u32, rh: u32, b: u8, g: u8, r: u8) {
        let pixel: u32 = (r as u32) << 16 | (g as u32) << 8 | b as u32;
        let fb     = FB_PHYS as *mut u32;
        let stride = self.width as usize;
        let x1     = (x + rw).min(self.width)  as usize;
        let y1     = (y + rh).min(self.height) as usize;
        for row in (y as usize)..y1 {
            for col in (x as usize)..x1 {
                unsafe { write_volatile(fb.add(row * stride + col), pixel); }
            }
        }
    }
}