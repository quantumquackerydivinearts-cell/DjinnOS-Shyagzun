// DjinnOS network stack — smoltcp over VirtIO.
//
// Static configuration (QEMU user-mode network defaults):
//   IP:      10.0.2.15 / 24
//   Gateway: 10.0.2.2
//   HTTP:    port 80 → serves Sa filesystem files
//
// QEMU launch flags required (add to your run command):
//   -netdev user,id=net0,hostfwd=tcp::8080-:80
//   -device virtio-net-device,netdev=net0
//
// Access from host:  curl http://localhost:8080/readme.txt
//
// Syscall exposure (fd 48..63 = network sockets):
//   SYS_KOI  (1138)  tcp_connect(ip_packed, port) → fd
//   SYS_RO   (83)    tcp_listen(port)             → fd   [already wired, now real]
//   SYS_LY   (2)     recv on net fd               → bytes
//   SYS_SOA  (193)   send on net fd               → bytes
//   SYS_MEK  (166)   close socket fd              → void
//
// The network layer (smoltcp) is driven by net::poll() called from the main
// loop every iteration.  No interrupts — purely cooperative.

use smoltcp::iface::{Config, Interface, SocketSet};
use smoltcp::phy::{Device, DeviceCapabilities, RxToken, TxToken};
use smoltcp::socket::tcp::{Socket as TcpSocket, SocketBuffer};
use smoltcp::time::Instant;
use smoltcp::wire::{EthernetAddress, IpAddress, IpCidr, Ipv4Address};

use alloc::vec;
use alloc::vec::Vec;

use crate::virtio::{NetDriver, net::RxHalf, net::TxHalf};

// ── Network constants ─────────────────────────────────────────────────────────

pub const NET_FD_BASE: u64  = 48;
pub const MAX_SOCKETS: usize = 8;   // fd 48..55

pub const OUR_IP:   [u8; 4] = [10, 0, 2, 15];
pub const GW_IP:    [u8; 4] = [10, 0, 2,  2];
pub const HTTP_PORT: u16    = 80;
const MTIME_HZ:     u64    = 10_000_000;  // QEMU RISC-V: 10 MHz

#[inline]
pub fn is_net_fd(fd: u64) -> bool {
    fd >= NET_FD_BASE && fd < NET_FD_BASE + MAX_SOCKETS as u64
}
#[inline]
pub fn net_slot(fd: u64) -> usize { (fd - NET_FD_BASE) as usize }

// ── smoltcp Device adapter ────────────────────────────────────────────────────
//
// Split-borrow design: RxHalf and TxHalf are separate struct fields of NetDriver
// so we can hold a mutable reference to TxHalf in TxToken while also having
// moved data out of RxHalf into RxToken.

pub struct SmolDev<'d> {
    pub rx: &'d mut RxHalf,
    pub tx: &'d mut TxHalf,
}

pub struct SmolRx { data: Vec<u8> }
pub struct SmolTx<'d> { tx: &'d mut TxHalf }

impl RxToken for SmolRx {
    fn consume<R, F: FnOnce(&mut [u8]) -> R>(mut self, f: F) -> R {
        f(&mut self.data)
    }
}

impl<'d> TxToken for SmolTx<'d> {
    fn consume<R, F: FnOnce(&mut [u8]) -> R>(self, len: usize, f: F) -> R {
        let mut buf = vec![0u8; len];
        let r = f(&mut buf);
        self.tx.send(&buf);
        r
    }
}

impl<'d> Device for SmolDev<'d> {
    type RxToken<'a> = SmolRx   where Self: 'a;
    type TxToken<'a> = SmolTx<'a> where Self: 'a;

    fn receive(&mut self, _ts: Instant) -> Option<(Self::RxToken<'_>, Self::TxToken<'_>)> {
        let data = self.rx.try_recv()?;
        Some((SmolRx { data }, SmolTx { tx: self.tx }))
    }

    fn transmit(&mut self, _ts: Instant) -> Option<Self::TxToken<'_>> {
        Some(SmolTx { tx: self.tx })
    }

    fn capabilities(&self) -> DeviceCapabilities {
        let mut caps = DeviceCapabilities::default();
        caps.max_transmission_unit = 1514;
        caps
    }
}

// ── Static network state ──────────────────────────────────────────────────────

static mut NET_DRV:  Option<NetDriver>  = None;
static mut NET_IFACE: Option<Interface> = None;
static mut NET_SOCKS: Option<SocketSet<'static>> = None;

// Socket table: maps fd slot → smoltcp SocketHandle
use smoltcp::iface::SocketHandle;
static mut SOCK_HANDLES: [Option<SocketHandle>; MAX_SOCKETS] =
    [const { None }; MAX_SOCKETS];

// Dedicated handle for the HTTP listener (slot 0 = fd 48).
static mut HTTP_HANDLE: Option<SocketHandle> = None;

// ── Timestamp helper ──────────────────────────────────────────────────────────

fn now_ms() -> Instant {
    Instant::from_millis((crate::arch::read_mtime() / (MTIME_HZ / 1000)) as i64)
}

// ── Initialisation ────────────────────────────────────────────────────────────

/// Probe VirtIO net, build smoltcp interface, start listening on port 80.
/// Returns false if no network device is found.
pub fn init() -> bool {
    let base = match crate::virtio::find_net() {
        Some(b) => b,
        None    => return false,
    };
    let drv = match NetDriver::init(base) {
        Some(d) => d,
        None    => return false,
    };
    let mac = drv.mac;

    // Stash the driver.
    unsafe { NET_DRV = Some(drv); }

    // Build smoltcp interface.
    let cfg = Config::new(EthernetAddress(mac).into());
    let iface = {
        let drv = unsafe { NET_DRV.as_mut().unwrap() };
        let mut dev = SmolDev { rx: &mut drv.rx, tx: &mut drv.tx };
        let mut iface = Interface::new(cfg, &mut dev, now_ms());
        iface.update_ip_addrs(|addrs| {
            addrs.push(IpCidr::new(
                IpAddress::Ipv4(Ipv4Address(OUR_IP)), 24,
            )).ok();
        });
        iface.routes_mut()
            .add_default_ipv4_route(Ipv4Address(GW_IP))
            .ok();
        iface
    };
    unsafe { NET_IFACE = Some(iface); }

    // Create socket set with a preallocated HTTP listener.
    let mut sockets = SocketSet::new(Vec::new());
    let rx_buf = SocketBuffer::new(vec![0u8; 8192]);
    let tx_buf = SocketBuffer::new(vec![0u8; 8192]);
    let mut http_sock = TcpSocket::new(rx_buf, tx_buf);
    http_sock.listen(HTTP_PORT).ok();
    let handle = sockets.add(http_sock);
    unsafe {
        HTTP_HANDLE       = Some(handle);
        SOCK_HANDLES[0]   = Some(handle);
    }
    unsafe { NET_SOCKS = Some(sockets); }

    true
}

// ── Main poll loop ────────────────────────────────────────────────────────────

/// Drive smoltcp and the HTTP server.  Call from the kernel main loop.
pub fn poll() {
    let (iface, socks, drv) = unsafe {
        match (NET_IFACE.as_mut(), NET_SOCKS.as_mut(), NET_DRV.as_mut()) {
            (Some(i), Some(s), Some(d)) => (i, s, d),
            _ => return,
        }
    };

    let ts = now_ms();
    {
        let mut dev = SmolDev { rx: &mut drv.rx, tx: &mut drv.tx };
        iface.poll(ts, &mut dev, socks);
    }
    drv.rx.reclaim_consumed();

    // HTTP server: check listener, handle one request.
    let handle = match unsafe { HTTP_HANDLE } {
        Some(h) => h,
        None    => return,
    };
    let sock = socks.get_mut::<TcpSocket>(handle);
    if sock.may_recv() {
        let mut req = [0u8; 1024];
        let n = sock.recv_slice(&mut req).unwrap_or(0);
        if n > 0 {
            let resp = handle_http(&req[..n]);
            let _ = sock.send_slice(&resp);
            sock.close();
        }
    }
    // If the socket has been closed (by us or the peer), re-arm the listener.
    let sock = socks.get_mut::<TcpSocket>(handle);
    if !sock.is_open() {
        sock.listen(HTTP_PORT).ok();
    }
}

// ── HTTP request handler ──────────────────────────────────────────────────────

fn parse_method(req: &str) -> &str {
    req.lines().next().unwrap_or("").split_whitespace().next().unwrap_or("GET")
}

fn parse_body(req: &str) -> &str {
    if let Some(i) = req.find("\r\n\r\n") { &req[i+4..] }
    else if let Some(i) = req.find("\n\n") { &req[i+2..] }
    else { "" }
}

fn handle_http(req: &[u8]) -> Vec<u8> {
    let req_str = core::str::from_utf8(req).unwrap_or("");
    let method  = parse_method(req_str);
    let path    = parse_get_path(req_str);
    let body    = parse_body(req_str);

    // Semantic substrate routes — handled before file serving.
    if let Some(resp) = crate::http_intel::try_handle(method, path, body) {
        return resp;
    }

    // Streaming platform routes (/api/stream/*).
    if crate::stream_platform::is_stream_route(path) {
        return crate::stream_platform::handle_stream_request(method, path, body.as_bytes());
    }

    let (body, content_type, status) = if path == "/" || path.is_empty() {
        // Directory listing
        let listing = build_index();
        (listing, b"text/html".as_ref(), 200u16)
    } else {
        // Strip leading /
        let name = path.trim_start_matches('/').as_bytes();
        let mut buf = vec![0u8; 65536];
        let n = crate::vfs::read_named(name, &mut buf);
        if n == 0 {
            (build_404(path), b"text/html".as_ref(), 404u16)
        } else {
            buf.truncate(n);
            let ct = content_type_for(name);
            (buf, ct, 200u16)
        }
    };

    build_response(status, content_type, &body)
}

fn parse_get_path(req: &str) -> &str {
    // "GET /path HTTP/1.x"
    let line = req.lines().next().unwrap_or("");
    let mut parts = line.split_whitespace();
    let _method = parts.next().unwrap_or("");
    parts.next().unwrap_or("/")
}

fn content_type_for(name: &[u8]) -> &'static [u8] {
    match name.rsplit(|&b| b == b'.').next() {
        Some(b"html") | Some(b"htm") => b"text/html",
        Some(b"txt")                 => b"text/plain",
        Some(b"json")                => b"application/json",
        Some(b"js")                  => b"application/javascript",
        Some(b"css")                 => b"text/css",
        Some(b"png")                 => b"image/png",
        Some(b"jpg") | Some(b"jpeg")=> b"image/jpeg",
        _                            => b"application/octet-stream",
    }
}

fn build_index() -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(b"<!DOCTYPE html><html><head><title>DjinnOS Sa Volume</title>\
        <style>body{font-family:monospace;background:#100c10;color:#c8964b;padding:2em}\
        a{color:#80d080}h1{color:#c8966b}</style></head><body>\
        <h1>DjinnOS / Sa volume</h1><ul>");
    crate::vfs::for_each_entry(|name, size| {
        out.extend_from_slice(b"<li><a href='/");
        out.extend_from_slice(name);
        out.extend_from_slice(b"'>");
        out.extend_from_slice(name);
        out.extend_from_slice(b"</a> &mdash; ");
        let mut tmp = [0u8; 12];
        let n = write_u32(&mut tmp, size);
        out.extend_from_slice(&tmp[..n]);
        out.extend_from_slice(b" B</li>");
    });
    out.extend_from_slice(b"</ul></body></html>");
    out
}

fn build_404(path: &str) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(b"<!DOCTYPE html><html><body><h1>404 Not Found</h1><p>");
    out.extend_from_slice(path.as_bytes());
    out.extend_from_slice(b"</p></body></html>");
    out
}

fn build_response(status: u16, content_type: &[u8], body: &[u8]) -> Vec<u8> {
    let status_str = if status == 200 { "200 OK" } else { "404 Not Found" };
    let mut resp = Vec::new();
    resp.extend_from_slice(b"HTTP/1.0 ");
    resp.extend_from_slice(status_str.as_bytes());
    resp.extend_from_slice(b"\r\nContent-Type: ");
    resp.extend_from_slice(content_type);
    resp.extend_from_slice(b"\r\nContent-Length: ");
    let mut tmp = [0u8; 12];
    let n = write_u32(&mut tmp, body.len() as u32);
    resp.extend_from_slice(&tmp[..n]);
    resp.extend_from_slice(b"\r\nConnection: close\r\nServer: DjinnOS/1.0\r\n\r\n");
    resp.extend_from_slice(body);
    resp
}

// ── Socket syscall support ────────────────────────────────────────────────────

/// Allocate a new TCP socket, return its fd (NET_FD_BASE + slot).
/// If `listen_port` is non-zero the socket enters listen mode immediately.
pub fn tcp_socket(listen_port: u16) -> u64 {
    let socks = unsafe { match NET_SOCKS.as_mut() { Some(s) => s, None => return u64::MAX } };
    let handles = unsafe { &mut SOCK_HANDLES };

    // Find a free slot (skip slot 0 = HTTP listener).
    for i in 1..MAX_SOCKETS {
        if handles[i].is_none() {
            let rx = SocketBuffer::new(vec![0u8; 4096]);
            let tx = SocketBuffer::new(vec![0u8; 4096]);
            let mut sock = TcpSocket::new(rx, tx);
            if listen_port != 0 {
                sock.listen(listen_port).ok();
            }
            let handle = socks.add(sock);
            handles[i] = Some(handle);
            return NET_FD_BASE + i as u64;
        }
    }
    u64::MAX
}

/// Connect a socket to (ip, port). Returns 1 if the connect was initiated
/// (it completes asynchronously on the next poll).
pub fn tcp_connect(fd: u64, ip: [u8; 4], port: u16) -> u64 {
    let (socks, iface) = unsafe {
        match (NET_SOCKS.as_mut(), NET_IFACE.as_mut()) {
            (Some(s), Some(i)) => (s, i),
            _ => return 0,
        }
    };
    let slot = net_slot(fd);
    let handle = match unsafe { SOCK_HANDLES[slot] } { Some(h) => h, None => return 0 };
    let local_port = 49152 + (slot as u16 * 17);
    let remote = (IpAddress::Ipv4(Ipv4Address(ip)), port);
    let sock = socks.get_mut::<TcpSocket>(handle);
    sock.connect(iface.context(), remote, local_port).map(|_| 1u64).unwrap_or(0)
}

/// Send bytes on a TCP socket.  Returns bytes queued.
pub fn tcp_send(fd: u64, data: &[u8]) -> usize {
    let socks = unsafe { match NET_SOCKS.as_mut() { Some(s) => s, None => return 0 } };
    let slot = net_slot(fd);
    let handle = match unsafe { SOCK_HANDLES[slot] } { Some(h) => h, None => return 0 };
    let sock = socks.get_mut::<TcpSocket>(handle);
    if sock.may_send() {
        sock.send_slice(data).unwrap_or(0)
    } else {
        0
    }
}

/// Receive bytes from a TCP socket.  Returns bytes read.
pub fn tcp_recv(fd: u64, buf: &mut [u8]) -> usize {
    let socks = unsafe { match NET_SOCKS.as_mut() { Some(s) => s, None => return 0 } };
    let slot = net_slot(fd);
    let handle = match unsafe { SOCK_HANDLES[slot] } { Some(h) => h, None => return 0 };
    let sock = socks.get_mut::<TcpSocket>(handle);
    if sock.may_recv() {
        sock.recv_slice(buf).unwrap_or(0)
    } else {
        0
    }
}

/// Close a socket.
pub fn tcp_close(fd: u64) {
    let socks = unsafe { match NET_SOCKS.as_mut() { Some(s) => s, None => return } };
    let slot = net_slot(fd);
    if let Some(handle) = unsafe { SOCK_HANDLES[slot].take() } {
        socks.get_mut::<TcpSocket>(handle).close();
        socks.remove(handle);
    }
}

/// True if the socket is established.
pub fn tcp_ready(fd: u64) -> bool {
    let socks = unsafe { match NET_SOCKS.as_mut() { Some(s) => s, None => return false } };
    let slot = net_slot(fd);
    let handle = match unsafe { SOCK_HANDLES[slot] } { Some(h) => h, None => return false };
    socks.get::<TcpSocket>(handle).may_send()
}

// ── Status query for shell ────────────────────────────────────────────────────

pub struct NetInfo {
    pub mac:       [u8; 6],
    pub ip:        [u8; 4],
    pub http_port: u16,
    pub active:    bool,
}

pub fn info() -> Option<NetInfo> {
    let drv = unsafe { NET_DRV.as_ref()? };
    Some(NetInfo {
        mac:       drv.mac,
        ip:        OUR_IP,
        http_port: HTTP_PORT,
        active:    true,
    })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn write_u32(buf: &mut [u8], mut n: u32) -> usize {
    if n == 0 { if !buf.is_empty() { buf[0] = b'0'; } return 1; }
    let mut tmp = [0u8; 10]; let mut len = 0;
    while n > 0 { tmp[len] = b'0' + (n % 10) as u8; n /= 10; len += 1; }
    for i in 0..len { buf[i] = tmp[len - 1 - i]; }
    len
}
