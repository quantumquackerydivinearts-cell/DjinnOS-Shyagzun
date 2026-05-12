// x86_64 network module — same public API as RISC-V net.rs, backed by e1000.
// Allows browser.rs, shell.rs Myrun, and world.rs to compile on x86_64
// unchanged once the cfg gates are removed.

use crate::net_stack::TcpStack;

pub const NET_FD_BASE:  u64  = 48;
pub const MAX_SOCKETS: usize = 8;

pub struct NetInfo {
    pub mac:       [u8; 6],
    pub ip:        [u8; 4],
    pub http_port: u16,
    pub active:    bool,
}

static mut STACK:        Option<TcpStack> = None;
static mut USB_NET_ACTIVE: bool = false;

/// True when the USB port is in use for phone tethering (xhci consumed by UsbNet).
/// Used by printer::init() to avoid re-initialising the same controller.
pub fn usb_net_active() -> bool { unsafe { USB_NET_ACTIVE } }

fn stack() -> Option<&'static mut TcpStack> {
    unsafe { STACK.as_mut() }
}

pub fn init() -> bool {
    // Try wired e1000 first (desktop / docked laptop), then USB tethering.
    if let Some(mut nic) = crate::e1000::E1000Net::find_and_init() {
        // DHCP on wired too — works with QEMU SLIRP and real routers.
        crate::dhcp::acquire(&mut nic);
        unsafe { core::ptr::write_volatile(&mut STACK, Some(TcpStack::new(nic))); }
        crate::uart::puts("NET: e1000 ready\r\n");
        return true;
    }

    crate::uart::puts("NET: no e1000 — scanning USB for tethered phone...\r\n");
    if let Some(mut xhci) = crate::xhci::XhciController::find_and_init() {
        if let Some(dev) = crate::usb::enumerate(&mut xhci) {
            if let Some(mut usb_nic) = crate::usb_net::UsbNet::new(xhci, dev) {
                // Run DHCP — the phone assigns an IP from its tethering subnet.
                let got_ip = crate::dhcp::acquire(&mut usb_nic);
                if !got_ip {
                    // Static fallback: Android default tethering range.
                    crate::net_stack::set_addrs(
                        [192, 168, 42, 2],
                        [192, 168, 42, 129],
                    );
                    crate::uart::puts("NET: USB — using static 192.168.42.2\r\n");
                }
                unsafe {
                    core::ptr::write_volatile(&mut STACK, Some(TcpStack::new(usb_nic)));
                    USB_NET_ACTIVE = true;
                }
                crate::uart::puts("NET: USB tethering ready\r\n");
                return true;
            }
        }
    }
    false
}


pub fn poll() {
    if let Some(s) = stack() { s.poll(); }
}

pub fn info() -> Option<NetInfo> {
    let s = stack()?;
    Some(NetInfo {
        mac:       s.net.mac(),
        ip:        crate::net_stack::our_ip(),
        http_port: 0,
        active:    true,
    })
}

#[inline] pub fn is_net_fd(fd: u64) -> bool {
    fd >= NET_FD_BASE && fd < NET_FD_BASE + MAX_SOCKETS as u64
}
#[inline] pub fn net_slot(fd: u64) -> usize { (fd - NET_FD_BASE) as usize }

pub fn tcp_socket(_: u16) -> u64 {
    match stack().and_then(|s| s.alloc_slot()) {
        Some(slot) => NET_FD_BASE + slot as u64,
        None       => u64::MAX,
    }
}

pub fn tcp_connect(fd: u64, ip: [u8; 4], port: u16) -> u64 {
    match stack() {
        None    => { crate::uart::puts("tcp: no stack\r\n"); 0 }
        Some(s) => if s.connect(net_slot(fd), ip, port) { 1 } else { 0 }
    }
}

pub fn tcp_ready(fd: u64) -> bool {
    stack().map(|s| s.ready(net_slot(fd))).unwrap_or(false)
}

pub fn tcp_send(fd: u64, data: &[u8]) -> usize {
    stack().map(|s| s.send(net_slot(fd), data)).unwrap_or(0)
}

pub fn tcp_recv(fd: u64, buf: &mut [u8]) -> usize {
    stack().map(|s| s.recv(net_slot(fd), buf)).unwrap_or(0)
}

pub fn tcp_close(fd: u64) {
    if let Some(s) = stack() { s.close(net_slot(fd)); }
}