// VirtIO keyboard input driver — device ID 18, v1 legacy MMIO transport.
//
// The eventq is pre-populated with writable 8-byte buffers.  When a key
// event occurs the device fills one buffer and advances the used ring.
// We drain the used ring each poll(), re-offer the buffer, and return the
// decoded key.

use super::mmio::{VirtioMmio, *};
use super::queue::{VirtQueue, Descriptor, AvailRing, UsedRing, QUEUE_SIZE};
use core::sync::atomic::{fence, Ordering};

pub const DEVICE_INPUT: u32 = 18;

// virtio_input_event wire layout
const EV_SYN: u16 = 0;
const EV_KEY: u16 = 1;
const KEY_PRESS:   u32 = 1;
const KEY_REPEAT:  u32 = 2;

const EVENT_SLOTS: usize = 32;
const EVENT_BYTES: usize = 8;  // u16 type + u16 code + u32 value

// ── Static memory ─────────────────────────────────────────────────────────────

#[repr(C, align(4096))]
struct KbdQueueMem([u8; 8192]);
static mut KBD_QUEUE_MEM: KbdQueueMem = KbdQueueMem([0u8; 8192]);

// Pre-allocated event receive buffers — device writes 8 bytes into each.
static mut EVENT_BUFS: [[u8; EVENT_BYTES]; EVENT_SLOTS] =
    [[0u8; EVENT_BYTES]; EVENT_SLOTS];

const KBD_DESC_OFF:  usize = 0;
const KBD_AVAIL_OFF: usize = QUEUE_SIZE * 16;
const KBD_USED_OFF:  usize = 4096;

// ── Public key event ──────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Key {
    Char(u8),
    Enter,
    Backspace,
}

// ── Driver ────────────────────────────────────────────────────────────────────

pub struct InputDriver {
    dev:        VirtioMmio,
    queue:      VirtQueue,
    shift_held: bool,
}

impl InputDriver {
    pub fn init(base: u64) -> Option<Self> {
        let dev = VirtioMmio::new(base);

        dev.write(REG_STATUS, 0);
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE);
        dev.write(REG_STATUS, STATUS_ACKNOWLEDGE | STATUS_DRIVER);

        dev.write(REG_DEVICE_FEAT_SEL,  0);
        dev.write(REG_DRIVER_FEAT_SEL, 0);
        dev.write(REG_DRIVER_FEATURES,  0);

        let s = dev.read(REG_STATUS) | STATUS_FEATURES_OK;
        dev.write(REG_STATUS, s);
        if dev.read(REG_STATUS) & STATUS_FEATURES_OK == 0 { return None; }

        // Set up eventq (queue 0) — v1 protocol
        dev.write(REG_GUEST_PAGE_SIZE, 4096);
        dev.write(REG_QUEUE_SEL, 0);
        if dev.read(REG_QUEUE_NUM_MAX) < QUEUE_SIZE as u32 { return None; }
        dev.write(REG_QUEUE_NUM,   QUEUE_SIZE as u32);
        dev.write(REG_QUEUE_ALIGN, 4096);

        let base_phys = unsafe { KBD_QUEUE_MEM.0.as_ptr() as u64 };
        dev.write(REG_QUEUE_PFN, (base_phys >> 12) as u32);

        dev.write(REG_STATUS, dev.read(REG_STATUS) | STATUS_DRIVER_OK);

        let mut queue = unsafe {
            let b    = KBD_QUEUE_MEM.0.as_mut_ptr();
            let desc  = &mut *(b.add(KBD_DESC_OFF)  as *mut [Descriptor; QUEUE_SIZE]);
            let avail = &mut *(b.add(KBD_AVAIL_OFF) as *mut AvailRing);
            let used  = &    *(b.add(KBD_USED_OFF)  as *const UsedRing);
            VirtQueue { desc, avail, used, free_head: 0, last_used: 0 }
        };

        // Pre-fill all event slots so the device has buffers to write into
        unsafe {
            for i in 0..EVENT_SLOTS {
                let phys = EVENT_BUFS[i].as_ptr() as u64;
                queue.offer(phys, EVENT_BYTES as u32);
            }
        }
        dev.write(REG_QUEUE_NOTIFY, 0);

        Some(InputDriver { dev, queue, shift_held: false })
    }

    /// Non-blocking: return the next decoded key if one is available.
    pub fn poll(&mut self) -> Option<Key> {
        if let Some(desc_id) = self.queue.try_recv() {
            let slot = desc_id as usize % EVENT_SLOTS;
            let key  = unsafe { self.parse_event(&EVENT_BUFS[slot]) };

            // Re-offer the buffer so the device can reuse it
            let phys = unsafe { EVENT_BUFS[slot].as_ptr() as u64 };
            self.queue.offer(phys, EVENT_BYTES as u32);
            fence(Ordering::SeqCst);
            self.dev.write(REG_QUEUE_NOTIFY, 0);

            key
        } else {
            None
        }
    }

    unsafe fn parse_event(&mut self, buf: &[u8; EVENT_BYTES]) -> Option<Key> {
        let ev_type  = u16::from_le_bytes([buf[0], buf[1]]);
        let ev_code  = u16::from_le_bytes([buf[2], buf[3]]);
        let ev_value = u32::from_le_bytes([buf[4], buf[5], buf[6], buf[7]]);

        if ev_type != EV_KEY { return None; }

        // Track shift state before the press/repeat filter so release events
        // (ev_value == 0) can clear shift_held.
        if ev_code == 42 || ev_code == 54 {
            self.shift_held = ev_value == KEY_PRESS || ev_value == KEY_REPEAT;
            return None;
        }

        if ev_value != KEY_PRESS && ev_value != KEY_REPEAT { return None; }

        match ev_code {
            28 => Some(Key::Enter),
            14 => Some(Key::Backspace),
            _  => keycode_to_char(ev_code, self.shift_held).map(Key::Char),
        }
    }
}

fn keycode_to_char(code: u16, shift: bool) -> Option<u8> {
    let pair: Option<(u8, u8)> = match code {
        2  => Some((b'1', b'!')),  3  => Some((b'2', b'@')),
        4  => Some((b'3', b'#')),  5  => Some((b'4', b'$')),
        6  => Some((b'5', b'%')),  7  => Some((b'6', b'^')),
        8  => Some((b'7', b'&')),  9  => Some((b'8', b'*')),
        10 => Some((b'9', b'(')),  11 => Some((b'0', b')')),
        12 => Some((b'-', b'_')),  13 => Some((b'=', b'+')),
        16 => Some((b'q', b'Q')),  17 => Some((b'w', b'W')),
        18 => Some((b'e', b'E')),  19 => Some((b'r', b'R')),
        20 => Some((b't', b'T')),  21 => Some((b'y', b'Y')),
        22 => Some((b'u', b'U')),  23 => Some((b'i', b'I')),
        24 => Some((b'o', b'O')),  25 => Some((b'p', b'P')),
        30 => Some((b'a', b'A')),  31 => Some((b's', b'S')),
        32 => Some((b'd', b'D')),  33 => Some((b'f', b'F')),
        34 => Some((b'g', b'G')),  35 => Some((b'h', b'H')),
        36 => Some((b'j', b'J')),  37 => Some((b'k', b'K')),
        38 => Some((b'l', b'L')),  39 => Some((b';', b':')),
        26 => Some((b'[', b'{')),  27 => Some((b']', b'}')),
        40 => Some((b'\'',b'"')),  41 => Some((b'`', b'~')),
        43 => Some((b'\\',b'|')),
        44 => Some((b'z', b'Z')),  45 => Some((b'x', b'X')),
        46 => Some((b'c', b'C')),  47 => Some((b'v', b'V')),
        48 => Some((b'b', b'B')),  49 => Some((b'n', b'N')),
        50 => Some((b'm', b'M')),  51 => Some((b',', b'<')),
        52 => Some((b'.', b'>')),  53 => Some((b'/', b'?')),
        57 => Some((b' ', b' ')),
        _ => None,
    };
    pair.map(|(lo, hi)| if shift { hi } else { lo })
}