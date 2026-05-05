// VirtIO block driver — device ID 2, v1 legacy MMIO transport.
//
// One queue (requestq = 0).  Each I/O uses a 3-descriptor chain:
//   desc[0]  request header  (device reads  — type, reserved, sector)
//   desc[1]  data buffer     (device writes for READ, device reads for WRITE)
//   desc[2]  status byte     (device writes — 0=ok, 1=ioerr, 2=unsupported)

use super::mmio::{VirtioMmio, *};
use super::queue::{VirtQueue, Descriptor, AvailRing, UsedRing, QUEUE_SIZE, DESC_F_WRITE};

const VIRTIO_BLK_T_IN:  u32 = 0;   // read
const VIRTIO_BLK_T_OUT: u32 = 1;   // write
const BLK_S_OK:          u8 = 0;

pub const SECTOR_SIZE: usize = 512;

#[repr(C)]
struct BlkHdr {
    type_:    u32,
    reserved: u32,
    sector:   u64,
}

// ── Static memory ─────────────────────────────────────────────────────────────

#[repr(C, align(4096))]
struct BlkQueueMem([u8; 8192]);
static mut BLK_QUEUE_MEM: BlkQueueMem = BlkQueueMem([0u8; 8192]);
static mut BLK_HDR:    [u8; 16] = [0u8; 16];
static mut BLK_STATUS: [u8;  1] = [0u8;  1];

const BLK_DESC_OFF:  usize = 0;
const BLK_AVAIL_OFF: usize = QUEUE_SIZE * 16;
const BLK_USED_OFF:  usize = 4096;

// ── Driver ────────────────────────────────────────────────────────────────────

pub struct BlockDriver {
    dev:   VirtioMmio,
    queue: VirtQueue,
    pub capacity: u64,   // capacity in sectors
}

impl BlockDriver {
    pub fn init(base: u64) -> Option<Self> {
        let dev = VirtioMmio::new(base);

        dev.write(REG_STATUS, 0);
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE);
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE | STATUS_DRIVER);

        dev.write(REG_DEVICE_FEAT_SEL, 0);
        dev.write(REG_DRIVER_FEAT_SEL, 0);
        dev.write(REG_DRIVER_FEATURES, 0);

        let s = dev.read(REG_STATUS) | STATUS_FEATURES_OK;
        dev.write(REG_STATUS, s);
        if dev.read(REG_STATUS) & STATUS_FEATURES_OK == 0 { return None; }

        dev.write(REG_GUEST_PAGE_SIZE, 4096);
        dev.write(REG_QUEUE_SEL, 0);
        if dev.read(REG_QUEUE_NUM_MAX) < QUEUE_SIZE as u32 { return None; }
        dev.write(REG_QUEUE_NUM,   QUEUE_SIZE as u32);
        dev.write(REG_QUEUE_ALIGN, 4096);

        let base_phys = unsafe { BLK_QUEUE_MEM.0.as_ptr() as u64 };
        dev.write(REG_QUEUE_PFN, (base_phys >> 12) as u32);

        dev.write(REG_STATUS, dev.read(REG_STATUS) | STATUS_DRIVER_OK);

        let queue = unsafe {
            let b    = BLK_QUEUE_MEM.0.as_mut_ptr();
            let desc  = &mut *(b.add(BLK_DESC_OFF)  as *mut [Descriptor; QUEUE_SIZE]);
            let avail = &mut *(b.add(BLK_AVAIL_OFF) as *mut AvailRing);
            let used  = &    *(b.add(BLK_USED_OFF)  as *const UsedRing);
            VirtQueue { desc, avail, used, free_head: 0, last_used: 0 }
        };

        // Capacity is at device config offset 0 — two 32-bit words (lo, hi)
        let cap_lo = dev.read(REG_CONFIG)     as u64;
        let cap_hi = dev.read(REG_CONFIG + 4) as u64;
        let capacity = (cap_hi << 32) | cap_lo;

        Some(BlockDriver { dev, queue, capacity })
    }

    /// Read one 512-byte sector into `buf`.  Returns true on success.
    pub fn read_sector(&mut self, lba: u64, buf: &mut [u8; SECTOR_SIZE]) -> bool {
        unsafe {
            let hdr = BlkHdr { type_: VIRTIO_BLK_T_IN, reserved: 0, sector: lba };
            core::ptr::copy_nonoverlapping(
                &hdr as *const _ as *const u8,
                BLK_HDR.as_mut_ptr(), 16,
            );
            BLK_STATUS[0] = 0xff;

            let hdr_phys    = BLK_HDR.as_ptr()   as u64;
            let data_phys   = buf.as_mut_ptr()    as u64;
            let status_phys = BLK_STATUS.as_ptr() as u64;

            // header (R) → data buffer (W) → status byte (W)
            // Save free_head so we can reclaim the 3 descriptors after poll().
            let saved_head = self.queue.free_head;
            self.queue.send3(
                hdr_phys,    16,          0,           // readonly header
                data_phys,   512,         DESC_F_WRITE, // device writes data
                status_phys, 1,           DESC_F_WRITE, // device writes status
            );
            self.dev.write(REG_QUEUE_NOTIFY, 0);
            self.queue.poll();
            // Synchronous one-at-a-time I/O: device is done, reclaim descriptors.
            self.queue.free_head = saved_head;

            BLK_STATUS[0] == BLK_S_OK
        }
    }
}