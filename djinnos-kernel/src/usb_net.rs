// usb_net.rs -- CDC-ECM / RNDIS network device over USB.
// Implements the same NetworkDevice interface as e1000 so net_stack.rs
// works unchanged.  Backed by an XhciController + UsbDevice.
//
// RNDIS initialization reference: MS-RNDIS spec (publicly available).
// CDC-ECM: USB ECM spec 1.2.

use alloc::vec::Vec;
use crate::xhci::XhciController;
use crate::usb::{UsbDevice, UsbNetKind};

// ── RNDIS constants ───────────────────────────────────────────────────────────
const RNDIS_PACKET_MSG:   u32 = 0x0000_0001;
const RNDIS_INIT_MSG:     u32 = 0x0000_0002;
const RNDIS_INIT_CMPLT:   u32 = 0x8000_0002;
const RNDIS_QUERY_MSG:    u32 = 0x0000_0004;
const RNDIS_QUERY_CMPLT:  u32 = 0x8000_0004;
const RNDIS_SET_MSG:      u32 = 0x0000_0005;
const RNDIS_SET_CMPLT:    u32 = 0x8000_0005;

const OID_802_3_CURRENT_ADDR:  u32 = 0x0101_0102;
const OID_GEN_CURRENT_FILTER:  u32 = 0x0001_010E;
const RNDIS_FILTER_ALL: u32 = 0x0000_001F;

// ── RX half ───────────────────────────────────────────────────────────────────

pub struct UsbRx {
    pending: Option<Vec<u8>>,
    // These are set from the net layer
    pub slot: u8,
    pub ep_in: u8,
}

impl UsbRx {
    pub fn try_recv(&mut self) -> Option<Vec<u8>> {
        self.pending.take()
    }
    pub fn reclaim_consumed(&mut self) {}
}

// ── TX half ───────────────────────────────────────────────────────────────────

pub struct UsbTx {
    pub slot:   u8,
    pub ep_out: u8,
    pub kind:   UsbNetKind,
}

impl UsbTx {
    pub fn send(&self, xhci: &mut XhciController, frame: &[u8]) {
        match self.kind {
            UsbNetKind::CdcEcm => {
                // ECM: raw Ethernet frame
                xhci.bulk_out(self.slot, self.ep_out, frame);
            }
            UsbNetKind::Rndis => {
                // RNDIS: wrap frame in RNDIS_PACKET_MSG header
                let msg_len = 44 + frame.len();
                let mut pkt = [0u8; 44 + 1514];
                let pkt = &mut pkt[..msg_len.min(44 + 1514)];
                // RNDIS message header
                write_le32(pkt, 0, RNDIS_PACKET_MSG);
                write_le32(pkt, 4, msg_len as u32);
                write_le32(pkt, 8, 0); // request id
                write_le32(pkt, 12, 0); // data offset from byte 8 = 36
                // Actually RNDIS PACKET_MSG:
                // [0:3]   MessageType = 1
                // [4:7]   MessageLength
                // [8:11]  DataOffset (offset from byte 8)
                // [12:15] DataLength
                // [16:19] OOBDataOffset
                // [20:23] OOBDataLength
                // [24:27] NumOOBDataElements
                // [28:31] PerPacketInfoOffset
                // [32:35] PerPacketInfoLength
                // [36:39] VcHandle
                // [40:43] Reserved
                // [44..]  Ethernet frame
                write_le32(pkt, 0,  RNDIS_PACKET_MSG);
                write_le32(pkt, 4,  msg_len as u32);
                write_le32(pkt, 8,  36);                    // DataOffset = 36
                write_le32(pkt, 12, frame.len() as u32);    // DataLength
                let fl = frame.len().min(pkt.len() - 44);
                pkt[44..44+fl].copy_from_slice(&frame[..fl]);
                xhci.bulk_out(self.slot, self.ep_out, pkt);
            }
            UsbNetKind::None => {}
        }
    }
}

// ── Combined USB network driver ───────────────────────────────────────────────

pub struct UsbNet {
    pub mac: [u8; 6],
    pub rx:  UsbRx,
    pub tx:  UsbTx,
    xhci:    XhciController,
}

impl UsbNet {
    /// Initialise from an already-enumerated UsbDevice.
    pub fn new(mut xhci: XhciController, dev: UsbDevice) -> Option<Self> {
        let mac = match dev.kind {
            UsbNetKind::Rndis  => rndis_init(&mut xhci, &dev)?,
            UsbNetKind::CdcEcm => [0x52, 0x54, 0x00, 0x12, 0x34, 0x56], // default; ECM provides MAC in descriptor
            UsbNetKind::None   => return None,
        };

        crate::uart::puts("usb_net: MAC ");
        for (k, &b) in mac.iter().enumerate() {
            if k > 0 { crate::uart::puts(":"); }
            crate::uart::putc(hex_hi(b));
            crate::uart::putc(hex_lo(b));
        }
        crate::uart::puts("\r\n");

        Some(UsbNet {
            mac,
            rx: UsbRx { pending: None, slot: dev.slot, ep_in: dev.bulk_in_epid },
            tx: UsbTx { slot: dev.slot, ep_out: dev.bulk_out_epid, kind: dev.kind },
            xhci,
        })
    }

    /// Poll for a received frame (non-blocking).  Returns a Vec of the frame bytes.
    pub fn poll_rx(&mut self) -> Option<Vec<u8>> {
        let mut buf = [0u8; 1600];
        let n = self.xhci.bulk_in(self.rx.slot, self.rx.ep_in, &mut buf);
        if n == 0 { return None; }
        let frame = match self.tx.kind {
            UsbNetKind::Rndis if n > 44 => {
                // Strip RNDIS_PACKET_MSG wrapper
                let data_off  = read_le32(&buf, 8) as usize;
                let data_len  = read_le32(&buf, 12) as usize;
                let start = 8 + data_off;
                if start + data_len <= n {
                    buf[start..start+data_len].to_vec()
                } else { return None; }
            }
            _ => buf[..n].to_vec(), // ECM: raw frame
        };
        Some(frame)
    }

    pub fn send(&mut self, frame: &[u8]) {
        let tx_kind = match self.tx.kind {
            UsbNetKind::CdcEcm => UsbNetKind::CdcEcm,
            UsbNetKind::Rndis  => UsbNetKind::Rndis,
            UsbNetKind::None   => return,
        };
        let slot   = self.tx.slot;
        let ep_out = self.tx.ep_out;
        // Inline send to avoid borrow split issues
        match tx_kind {
            UsbNetKind::CdcEcm => { self.xhci.bulk_out(slot, ep_out, frame); }
            UsbNetKind::Rndis  => {
                let msg_len = 44 + frame.len();
                let mut pkt = [0u8; 44 + 1514];
                let pkt = &mut pkt[..msg_len.min(44 + 1514)];
                write_le32(pkt, 0,  RNDIS_PACKET_MSG);
                write_le32(pkt, 4,  msg_len as u32);
                write_le32(pkt, 8,  36);
                write_le32(pkt, 12, frame.len() as u32);
                let fl = frame.len().min(pkt.len() - 44);
                pkt[44..44+fl].copy_from_slice(&frame[..fl]);
                self.xhci.bulk_out(slot, ep_out, pkt);
            }
            _ => {}
        }
    }
}

// ── RNDIS initialisation ──────────────────────────────────────────────────────

fn rndis_init(xhci: &mut XhciController, dev: &UsbDevice) -> Option<[u8; 6]> {
    let slot   = dev.slot;
    let ep_out = dev.bulk_out_epid;
    let ep_in  = dev.bulk_in_epid;
    let mut buf = [0u8; 128];

    // INITIALIZE
    let mut msg = [0u8; 24];
    write_le32(&mut msg, 0, RNDIS_INIT_MSG);
    write_le32(&mut msg, 4, 24);
    write_le32(&mut msg, 8, 1);   // RequestId=1
    write_le32(&mut msg, 12, 1);  // MajorVersion
    write_le32(&mut msg, 16, 0);  // MinorVersion
    write_le32(&mut msg, 20, 1558); // MaxTransferSize
    xhci.bulk_out(slot, ep_out, &msg);
    let n = xhci.bulk_in(slot, ep_in, &mut buf);
    if n < 12 || read_le32(&buf, 0) != RNDIS_INIT_CMPLT { return None; }

    // QUERY MAC address
    let mut qmsg = [0u8; 28];
    write_le32(&mut qmsg, 0,  RNDIS_QUERY_MSG);
    write_le32(&mut qmsg, 4,  28);
    write_le32(&mut qmsg, 8,  2);   // RequestId
    write_le32(&mut qmsg, 12, OID_802_3_CURRENT_ADDR);
    write_le32(&mut qmsg, 16, 0);   // InformationBufferLength
    write_le32(&mut qmsg, 20, 0);   // InformationBufferOffset
    write_le32(&mut qmsg, 24, 0);   // DeviceVcHandle
    xhci.bulk_out(slot, ep_out, &qmsg);
    let n = xhci.bulk_in(slot, ep_in, &mut buf);
    if n < 32 || read_le32(&buf, 0) != RNDIS_QUERY_CMPLT { return None; }
    let info_len = read_le32(&buf, 16) as usize;
    let info_off = read_le32(&buf, 20) as usize + 8; // offset from byte 8 of response
    if info_off + 6 > n || info_len < 6 { return None; }
    let mut mac = [0u8; 6];
    mac.copy_from_slice(&buf[info_off..info_off+6]);

    // SET packet filter
    let mut smsg = [0u8; 32];
    write_le32(&mut smsg, 0,  RNDIS_SET_MSG);
    write_le32(&mut smsg, 4,  32);
    write_le32(&mut smsg, 8,  3);   // RequestId
    write_le32(&mut smsg, 12, OID_GEN_CURRENT_FILTER);
    write_le32(&mut smsg, 16, 4);   // InformationBufferLength
    write_le32(&mut smsg, 20, 20);  // InformationBufferOffset (from byte 8)
    write_le32(&mut smsg, 28, RNDIS_FILTER_ALL);
    xhci.bulk_out(slot, ep_out, &smsg);
    let n = xhci.bulk_in(slot, ep_in, &mut buf);
    if n < 12 || read_le32(&buf, 0) != RNDIS_SET_CMPLT { return None; }

    Some(mac)
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn read_le32(buf: &[u8], off: usize) -> u32 {
    if off + 4 > buf.len() { return 0; }
    u32::from_le_bytes([buf[off], buf[off+1], buf[off+2], buf[off+3]])
}
fn write_le32(buf: &mut [u8], off: usize, v: u32) {
    if off + 4 > buf.len() { return; }
    buf[off..off+4].copy_from_slice(&v.to_le_bytes());
}
fn hex_hi(v: u8) -> u8 { let n = v >> 4;  if n < 10 { b'0'+n } else { b'a'+n-10 } }
fn hex_lo(v: u8) -> u8 { let n = v & 0xF; if n < 10 { b'0'+n } else { b'a'+n-10 } }