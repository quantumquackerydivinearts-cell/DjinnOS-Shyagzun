// Network stack — hand-rolled TCP/IP over VirtIO NET.
// Full smoltcp implementation preserved in net_smoltcp.rs.

use crate::net_stack::TcpStack;

pub const NET_FD_BASE:  u64  = 48;
pub const MAX_SOCKETS: usize = 8;

pub struct NetInfo {
    pub mac:       [u8; 6],
    pub ip:        [u8; 4],
    pub http_port: u16,
    pub active:    bool,
}

static mut STACK: Option<TcpStack> = None;

#[inline]
fn stack() -> Option<&'static mut TcpStack> {
    unsafe { STACK.as_mut() }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

pub fn init() -> bool {
    let base = match crate::virtio::find_net() {
        Some(b) => b,
        None    => return false,
    };
    let net = match crate::virtio::NetDriver::init(base) {
        Some(d) => d,
        None    => return false,
    };
    // write_volatile forces ALL bytes of the TcpStack (including VirtQueue
    // pointer fields) to land in STACK's static memory.  Without it, -Oz/LTO
    // keeps the pointer values in registers and never writes them to the global,
    // so any non-inlined function that reads them gets BSS-zero.
    unsafe {
        core::ptr::write_volatile(&mut STACK, Some(TcpStack::new(net)));
    }
    true
}


/// Drive the receive path — call from the main event loop.
pub fn poll() {
    if let Some(s) = stack() { s.poll(); }
}

pub fn info() -> Option<NetInfo> {
    let s = stack()?;
    Some(NetInfo {
        mac:       s.net.mac,
        ip:        crate::net_stack::OUR_IP,
        http_port: 0,
        active:    true,
    })
}

// ── Socket API (fd = NET_FD_BASE + slot) ──────────────────────────────────────

#[inline]
pub fn is_net_fd(fd: u64) -> bool {
    fd >= NET_FD_BASE && fd < NET_FD_BASE + MAX_SOCKETS as u64
}

#[inline]
pub fn net_slot(fd: u64) -> usize { (fd - NET_FD_BASE) as usize }

/// Allocate a TCP socket fd.  listen_port unused (client-only for now).
pub fn tcp_socket(_listen_port: u16) -> u64 {
    let s = match stack() { Some(s) => s, None => return u64::MAX };
    match s.alloc_slot() {
        Some(slot) => NET_FD_BASE + slot as u64,
        None       => u64::MAX,
    }
}

/// Initiate TCP connect (sends SYN, completes asynchronously via poll()).
pub fn tcp_connect(fd: u64, ip: [u8; 4], port: u16) -> u64 {
    let s = match stack() {
        Some(s) => s,
        None    => { crate::uart::puts("tcp: no stack\r\n"); return 0; }
    };
    let slot = net_slot(fd);
    if s.connect(slot, ip, port) { 1 } else { 0 }
}

/// True once the three-way handshake completes (SakuraVarshan).
pub fn tcp_ready(fd: u64) -> bool {
    stack().map(|s| s.ready(net_slot(fd))).unwrap_or(false)
}

/// Send bytes on an established connection.
pub fn tcp_send(fd: u64, data: &[u8]) -> usize {
    stack().map(|s| s.send(net_slot(fd), data)).unwrap_or(0)
}

/// Receive bytes (non-blocking).
pub fn tcp_recv(fd: u64, buf: &mut [u8]) -> usize {
    stack().map(|s| s.recv(net_slot(fd), buf)).unwrap_or(0)
}

/// Send FIN and release the slot.
pub fn tcp_close(fd: u64) {
    if let Some(s) = stack() { s.close(net_slot(fd)); }
}