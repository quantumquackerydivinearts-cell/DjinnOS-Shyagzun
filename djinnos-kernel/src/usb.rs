// usb.rs -- USB device enumeration layer.
// Drives an XhciController through the enumeration sequence:
//   enable_slot → address_device → get descriptors → configure_endpoint
// Returns a UsbDevice describing the endpoints and class.

use crate::xhci::XhciController;

// ── USB setup packet builder ──────────────────────────────────────────────────

pub fn setup_get_descriptor(desc_type: u8, desc_idx: u8, len: u16) -> [u8; 8] {
    [0x80, 0x06, desc_idx, desc_type, 0, 0,
     len as u8, (len >> 8) as u8]
}

pub fn setup_set_configuration(config: u8) -> [u8; 8] {
    [0x00, 0x09, config, 0, 0, 0, 0, 0]
}

pub fn setup_set_interface(iface: u8, alt: u8) -> [u8; 8] {
    [0x01, 0x0B, alt, 0, iface, 0, 0, 0]
}

pub fn setup_cdc_set_packet_filter(iface: u8, filter: u16) -> [u8; 8] {
    [0x21, 0x43, filter as u8, (filter >> 8) as u8, iface, 0, 0, 0]
}

// ── USB descriptor types ──────────────────────────────────────────────────────

const DESC_DEVICE:    u8 = 1;
const DESC_CONFIG:    u8 = 2;
const DESC_INTERFACE: u8 = 4;
const DESC_ENDPOINT:  u8 = 5;
const DESC_CDC_FUNC:  u8 = 0x24; // CS_INTERFACE

// CDC subtype for Ethernet functional descriptor
const CDC_SUBTYPE_ECM: u8 = 0x0F;
const CDC_SUBTYPE_UNION: u8 = 0x06;

// Interface classes
const CLASS_CDC:     u8 = 0x02;
const CLASS_CDC_DATA:u8 = 0x0A;
const CLASS_MISC:    u8 = 0xEF; // RNDIS sometimes uses this
const SUBCLASS_ECM:  u8 = 0x06;
const SUBCLASS_RNDIS:u8 = 0x04; // misc subclass for RNDIS
const PROTO_RNDIS:   u8 = 0x01;

// ── Parsed device info ────────────────────────────────────────────────────────

#[derive(Default)]
pub struct UsbDevice {
    pub slot:       u8,
    pub kind:       UsbNetKind,
    pub ctrl_iface: u8,
    pub data_iface: u8,
    pub bulk_out:   u8,  // endpoint NUMBER (1-based)
    pub bulk_in:    u8,
    pub intr_ep:    u8,
    pub bulk_out_epid: u8,  // xHCI endpoint context index
    pub bulk_in_epid:  u8,
    pub mac:        [u8; 6],
    pub max_pkt:    u16,
}

#[derive(Default, PartialEq)]
pub enum UsbNetKind {
    #[default]
    None,
    CdcEcm,
    Rndis,
}

// ── Enumeration ───────────────────────────────────────────────────────────────

pub fn enumerate(xhci: &mut XhciController) -> Option<UsbDevice> {
    // Scan all ports for a connected device
    for port_idx in 0..xhci.max_ports() {
        let port = port_idx + 1;
        if !xhci.port_connected(port) { continue; }
        crate::uart::puts("usb: device on port ");
        crate::uart::putu(port as u64);
        crate::uart::puts("\r\n");

        xhci.reset_port(port);
        // Wait for port to settle
        for _ in 0u32..10_000 { core::hint::spin_loop(); }

        let speed = xhci.port_speed(port);
        crate::uart::puts("usb: speed="); crate::uart::putu(speed as u64);
        crate::uart::puts("\r\n");

        let slot = xhci.enable_slot()?;
        crate::uart::puts("usb: slot="); crate::uart::putu(slot as u64);
        crate::uart::puts("\r\n");

        if !xhci.address_device(slot, port, speed) {
            crate::uart::puts("usb: address_device failed\r\n");
            continue;
        }

        if let Some(dev) = read_descriptors(xhci, slot) {
            return Some(dev);
        }
    }
    None
}

fn read_descriptors(xhci: &mut XhciController, slot: u8) -> Option<UsbDevice> {
    let mut buf = [0u8; 256];

    // Get device descriptor (just first 8 bytes to find max packet size)
    let n = xhci.control(slot, setup_get_descriptor(DESC_DEVICE, 0, 18), true, &mut buf[..18])?;
    if n < 8 { return None; }
    // buf[7] = bMaxPacketSize0 — update EP0 if needed (skipping for now)

    // Get full config descriptor (first pass: get total length)
    let n = xhci.control(slot, setup_get_descriptor(DESC_CONFIG, 0, 9), true, &mut buf[..9])?;
    if n < 9 { return None; }
    let total = u16::from_le_bytes([buf[2], buf[3]]) as usize;
    let total = total.min(256);

    let n = xhci.control(slot, setup_get_descriptor(DESC_CONFIG, 0, total as u16),
                          true, &mut buf[..total])?;
    if n < 9 { return None; }

    parse_config(xhci, slot, &buf[..n])
}

fn parse_config(xhci: &mut XhciController, slot: u8, cfg: &[u8]) -> Option<UsbDevice> {
    let mut dev = UsbDevice { slot, max_pkt: 512, ..Default::default() };
    let mut i = 0;
    let mut cur_iface = 0u8;
    let mut cur_alt   = 0u8;
    let mut in_data_iface = false;

    while i < cfg.len() {
        let len = cfg[i] as usize;
        if len < 2 || i + len > cfg.len() { break; }
        let desc_type = cfg[i + 1];

        match desc_type {
            DESC_INTERFACE => {
                if len < 9 { i += len; continue; }
                cur_iface = cfg[i + 2];
                cur_alt   = cfg[i + 3];
                let cls   = cfg[i + 5];
                let sub   = cfg[i + 6];
                let proto = cfg[i + 7];

                in_data_iface = false;

                // CDC ECM control interface
                if cls == CLASS_CDC && sub == SUBCLASS_ECM {
                    dev.ctrl_iface = cur_iface;
                    dev.kind = UsbNetKind::CdcEcm;
                }
                // CDC data interface (alt=1)
                if cls == CLASS_CDC_DATA && dev.kind == UsbNetKind::CdcEcm {
                    if cur_alt == 1 { in_data_iface = true; dev.data_iface = cur_iface; }
                }
                // RNDIS (misc class)
                if (cls == CLASS_MISC && sub == SUBCLASS_RNDIS && proto == PROTO_RNDIS)
                || (cls == CLASS_CDC  && sub == 2 && proto == 0xFF) {
                    dev.ctrl_iface = cur_iface;
                    dev.kind = UsbNetKind::Rndis;
                    in_data_iface = true;
                }
            }
            DESC_ENDPOINT => {
                if len < 7 { i += len; continue; }
                let addr = cfg[i + 2];
                let attrs = cfg[i + 3];
                let max_pkt = u16::from_le_bytes([cfg[i + 4], cfg[i + 5]]);
                let is_in   = addr & 0x80 != 0;
                let ep_num  = addr & 0x7F;
                let is_bulk = attrs & 0x03 == 2;

                if is_bulk && (in_data_iface || dev.kind == UsbNetKind::Rndis) {
                    if is_in  { dev.bulk_in  = ep_num; dev.max_pkt = max_pkt; }
                    else      { dev.bulk_out = ep_num; }
                }
            }
            DESC_CDC_FUNC => {
                if len < 3 { i += len; continue; }
                let subtype = cfg[i + 2];
                if subtype == CDC_SUBTYPE_ECM && len >= 14 {
                    // Parse iMACAddress string index — we'll use ARP for now
                    // Could get actual MAC from string descriptor here
                }
            }
            _ => {}
        }
        i += len;
    }

    if dev.kind == UsbNetKind::None || dev.bulk_in == 0 || dev.bulk_out == 0 {
        crate::uart::puts("usb: no CDC-ECM/RNDIS interface found\r\n");
        return None;
    }

    crate::uart::puts("usb: found network interface  bulk_in=");
    crate::uart::putu(dev.bulk_in as u64);
    crate::uart::puts("  bulk_out=");
    crate::uart::putu(dev.bulk_out as u64);
    crate::uart::puts("\r\n");

    // Compute xHCI endpoint context indices
    dev.bulk_out_epid = dev.bulk_out * 2;
    dev.bulk_in_epid  = dev.bulk_in  * 2 + 1;

    // SET_CONFIGURATION
    let cfg_val = 1u8; // almost always config 1
    xhci.control(slot, setup_set_configuration(cfg_val), false, &mut [])?;

    // For CDC-ECM: activate data interface alt setting 1
    if dev.kind == UsbNetKind::CdcEcm {
        xhci.control(slot, setup_set_interface(dev.data_iface, 1), false, &mut [])?;
        xhci.control(slot, setup_cdc_set_packet_filter(dev.ctrl_iface, 0x000F),
                     false, &mut [])?;
    }

    // Configure xHCI bulk endpoints
    if !xhci.configure_endpoints(slot, dev.bulk_out, dev.bulk_in, dev.max_pkt) {
        crate::uart::puts("usb: configure_endpoints failed\r\n");
        return None;
    }

    Some(dev)
}