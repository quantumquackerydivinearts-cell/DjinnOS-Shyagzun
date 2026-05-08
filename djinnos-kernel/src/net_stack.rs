// Hand-rolled TCP/IP stack for DjinnOS.
//
// Layers (bottom to top):
//   NetworkDevice trait → VirtIO NET (Ethernet frames in/out)
//   ARP                 → IP→MAC resolution, single-entry cache per connection
//   IPv4                → packet construction/parsing
//   TCP Varshan         → connection state machine (Zo/Fy/Sakura/Zu)
//   TcpStack            → manages up to 8 simultaneous connections
//
// Designed for QEMU SLIRP: reliable, in-order, no retransmission required.

use alloc::vec::Vec;

// Type-alias the NIC driver so the rest of this file compiles unchanged on
// both architectures.  E1000Net exposes identical field names and method
// signatures to VirtIO NetDriver.
#[cfg(target_arch = "riscv64")]
use crate::virtio::NetDriver;
#[cfg(not(target_arch = "riscv64"))]
use crate::e1000::E1000Net as NetDriver;

pub const OUR_IP:     [u8; 4] = [10,  0,  2, 15];
pub const GATEWAY_IP: [u8; 4] = [10,  0,  2,  2];

const ETH_ARP:  u16 = 0x0806;
const ETH_IPV4: u16 = 0x0800;
const IP_TCP:   u8  = 6;

// ── Checksums ─────────────────────────────────────────────────────────────────

fn ones_complement_sum(data: &[u8]) -> u16 {
    let mut sum: u32 = 0;
    let mut i = 0;
    while i + 1 < data.len() {
        sum += u16::from_be_bytes([data[i], data[i+1]]) as u32;
        i += 2;
    }
    if i < data.len() { sum += (data[i] as u32) << 8; }
    while sum >> 16 != 0 { sum = (sum & 0xffff) + (sum >> 16); }
    !(sum as u16)
}

fn tcp_checksum(src_ip: &[u8;4], dst_ip: &[u8;4], tcp_seg: &[u8]) -> u16 {
    // Pseudo-header + TCP segment
    let mut buf = [0u8; 12 + 1500];
    buf[0..4].copy_from_slice(src_ip);
    buf[4..8].copy_from_slice(dst_ip);
    buf[9] = IP_TCP;
    let len = tcp_seg.len() as u16;
    buf[10..12].copy_from_slice(&len.to_be_bytes());
    buf[12..12+tcp_seg.len()].copy_from_slice(tcp_seg);
    ones_complement_sum(&buf[..12+tcp_seg.len()])
}

// ── Frame builder — Ethernet + IPv4 + TCP in one stack buffer ─────────────────

fn send_tcp_seg(net: &mut NetDriver, v: &Varshan, flags: u8, payload: &[u8]) {
    let tcp_len  = 20 + payload.len();
    let ip_len   = 20 + tcp_len;
    let frame_len = 14 + ip_len;
    let mut buf = [0u8; 1514];

    // Ethernet header
    buf[0..6].copy_from_slice(&v.dst_mac);
    buf[6..12].copy_from_slice(&net.mac);
    buf[12..14].copy_from_slice(&ETH_IPV4.to_be_bytes());

    // IPv4 header
    let ip = &mut buf[14..34];
    ip[0] = 0x45;
    ip[2..4].copy_from_slice(&(ip_len as u16).to_be_bytes());
    ip[6..8].copy_from_slice(&0x4000u16.to_be_bytes()); // DF flag
    ip[8] = 64;  // TTL
    ip[9] = IP_TCP;
    ip[12..16].copy_from_slice(&OUR_IP);
    ip[16..20].copy_from_slice(&v.dst_ip);
    let ip_cs = ones_complement_sum(&buf[14..34]);
    buf[14+10..14+12].copy_from_slice(&ip_cs.to_be_bytes());

    // TCP header
    let tcp = &mut buf[34..34+tcp_len];
    tcp[0..2].copy_from_slice(&v.src_port.to_be_bytes());
    tcp[2..4].copy_from_slice(&v.dst_port.to_be_bytes());
    tcp[4..8].copy_from_slice(&v.seq.to_be_bytes());
    tcp[8..12].copy_from_slice(&v.ack.to_be_bytes());
    tcp[12] = 0x50;  // data offset = 5 (20-byte header)
    tcp[13] = flags;
    tcp[14..16].copy_from_slice(&8192u16.to_be_bytes()); // window
    // checksum at tcp[16..18] — computed below
    tcp[20..tcp_len].copy_from_slice(payload);
    let tcp_cs = tcp_checksum(&OUR_IP, &v.dst_ip, &buf[34..34+tcp_len]);
    buf[34+16..34+18].copy_from_slice(&tcp_cs.to_be_bytes());

    net.tx.send(&buf[..frame_len]);
}

// ── ARP ───────────────────────────────────────────────────────────────────────

fn arp_send_request(net: &mut NetDriver, target_ip: [u8;4]) {
    let broadcast = [0xffu8; 6];
    let mut buf = [0u8; 14+28];
    buf[0..6].copy_from_slice(&broadcast);
    buf[6..12].copy_from_slice(&net.mac);
    buf[12..14].copy_from_slice(&ETH_ARP.to_be_bytes());
    let a = &mut buf[14..];
    a[0..2].copy_from_slice(&1u16.to_be_bytes()); // Ethernet
    a[2..4].copy_from_slice(&0x0800u16.to_be_bytes()); // IPv4
    a[4] = 6; a[5] = 4;
    a[6..8].copy_from_slice(&1u16.to_be_bytes()); // request
    a[8..14].copy_from_slice(&net.mac);
    a[14..18].copy_from_slice(&OUR_IP);
    // target MAC = 0 (unknown)
    a[24..28].copy_from_slice(&target_ip);
    net.tx.send(&buf);
}

fn arp_reply_mac(frame: &[u8], wanted_ip: [u8;4]) -> Option<[u8;6]> {
    if frame.len() < 42 { return None; }
    if u16::from_be_bytes([frame[12],frame[13]]) != ETH_ARP { return None; }
    let a = &frame[14..];
    if a.len() < 28 { return None; }
    if u16::from_be_bytes([a[6],a[7]]) != 2 { return None; } // reply
    let sender_ip: [u8;4] = [a[14],a[15],a[16],a[17]];
    if sender_ip != wanted_ip { return None; }
    Some([a[8],a[9],a[10],a[11],a[12],a[13]])
}

/// Resolve target_ip → MAC via ARP.  Spins until reply (QEMU SLIRP is fast).
pub fn arp_resolve(net: &mut NetDriver, target_ip: [u8;4]) -> [u8;6] {
    for _ in 0..20 {
        arp_send_request(net, target_ip);
        for _ in 0..50000 {
            if let Some(frame) = net.rx.try_recv() {
                let result = arp_reply_mac(&frame, target_ip);
                net.rx.reclaim_consumed();
                if let Some(mac) = result { return mac; }
            }
        }
    }
    // QEMU SLIRP gateway fallback MAC
    [0x52, 0x54, 0x00, 0x12, 0x35, 0x02]
}

// ── TCP — Varshan ─────────────────────────────────────────────────────────────
//
// States named with the Lotus/Sakura akinen that describe the membrane's
// ontological character in that state.
//
//   ZoVarshan   — Zo (Absence / passive non-being):       CLOSED
//   FyVarshan   — Fy (Air Initiator / thought toward):    SYN_SENT
//   SakuraVarshan — Sakura precision (full signal-recv):  ESTABLISHED
//   ZuVarshan   — Zu (Earth Terminator / empirical close): FIN / CLOSING

#[derive(PartialEq, Clone, Copy, Debug)]
pub enum VarshanState {
    ZoVarshan,
    FyVarshan,
    SakuraVarshan,
    ZuVarshan,
}

pub struct Varshan {
    pub dst_ip:   [u8; 4],
    pub dst_mac:  [u8; 6],
    pub src_port: u16,
    pub dst_port: u16,
    pub seq:      u32,      // our next seq to send
    pub ack:      u32,      // next expected from peer
    pub rx_buf:   Vec<u8>,
    pub state:    VarshanState,
}

// ── TCP frame parser ──────────────────────────────────────────────────────────

struct TcpSeg<'a> {
    src_port: u16,
    dst_port: u16,
    seq:      u32,
    ack:      u32,
    flags:    u8,
    payload:  &'a [u8],
}

fn parse_tcp_frame(frame: &[u8]) -> Option<TcpSeg<'_>> {
    if frame.len() < 54 { return None; }  // 14 eth + 20 ip + 20 tcp
    if u16::from_be_bytes([frame[12],frame[13]]) != ETH_IPV4 { return None; }
    let ip = &frame[14..];
    if ip[9] != IP_TCP { return None; }
    let ihl = ((ip[0] & 0x0f) * 4) as usize;
    if ip.len() < ihl + 20 { return None; }
    let tcp = &ip[ihl..];
    let data_off = ((tcp[12] >> 4) * 4) as usize;
    if tcp.len() < data_off { return None; }
    Some(TcpSeg {
        src_port: u16::from_be_bytes([tcp[0],tcp[1]]),
        dst_port: u16::from_be_bytes([tcp[2],tcp[3]]),
        seq:      u32::from_be_bytes([tcp[4],tcp[5],tcp[6],tcp[7]]),
        ack:      u32::from_be_bytes([tcp[8],tcp[9],tcp[10],tcp[11]]),
        flags:    tcp[13],
        payload:  &tcp[data_off..],
    })
}

// ── TcpStack ──────────────────────────────────────────────────────────────────

pub struct TcpStack {
    pub net:   NetDriver,
    conns:     [Option<Varshan>; 8],
    port_ctr:  u16,
}

impl TcpStack {
    pub fn new(net: NetDriver) -> Self {
        Self {
            net,
            conns: [None,None,None,None,None,None,None,None],
            port_ctr: 49152,
        }
    }

    fn next_port(&mut self) -> u16 {
        let p = self.port_ctr;
        self.port_ctr = if self.port_ctr >= 65000 { 49152 } else { self.port_ctr + 1 };
        p
    }

    /// Allocate a connection slot (skipping slot 0 which is reserved for HTTP listener
    /// parity with the old smoltcp net.rs).
    pub fn alloc_slot(&self) -> Option<usize> {
        for i in 1..8 {
            if self.conns[i].is_none() { return Some(i); }
        }
        None
    }

    /// Initiate a TCP connection (sends SYN, returns immediately).
    /// Call poll() repeatedly then check ready() before sending data.
    pub fn connect(&mut self, slot: usize, dst_ip: [u8;4], dst_port: u16) -> bool {
        let dst_mac = arp_resolve(&mut self.net, dst_ip);
        let src_port = self.next_port();
        let isn = crate::arch::read_mtime() as u32 ^ 0xdeadbeef;

        let v = Varshan {
            dst_ip, dst_mac, src_port, dst_port,
            seq: isn, ack: 0,
            rx_buf: Vec::new(),
            state: VarshanState::FyVarshan,
        };
        // Send SYN
        send_tcp_seg(&mut self.net, &v, 0x02, &[]);
        let mut v = v;
        v.seq = isn.wrapping_add(1);

        self.conns[slot] = Some(v);
        true
    }

    /// Drive the receive path — call every main loop iteration.
    pub fn poll(&mut self) {
        loop {
            // Use try_recv, process frame, reclaim
            let frame = match self.net.rx.try_recv() {
                Some(f) => f,
                None    => break,
            };
            let seg = parse_tcp_frame(&frame);
            if let Some(s) = seg {
                self.dispatch(s.src_port, s.dst_port, s.seq, s.flags, s.payload);
            }
            self.net.rx.reclaim_consumed();
        }
    }

    fn dispatch(&mut self, src_port: u16, dst_port: u16, seq: u32, flags: u8, payload: &[u8]) {
        for i in 0..8 {
            if let Some(ref v) = self.conns[i] {
                if v.src_port == dst_port && v.dst_port == src_port {
                    // Take ownership to allow simultaneous &mut self.net borrow.
                    let mut v = self.conns[i].take().unwrap();
                    let keep = self.process_seg(&mut v, seq, flags, payload);
                    if keep { self.conns[i] = Some(v); }
                    return;
                }
            }
        }
    }

    // Returns false if the connection should be dropped.
    fn process_seg(&mut self, v: &mut Varshan, seq: u32, flags: u8, payload: &[u8]) -> bool {
        match v.state {
            VarshanState::FyVarshan => {
                if flags & 0x12 == 0x12 {  // SYN+ACK
                    v.ack = seq.wrapping_add(1);
                    v.state = VarshanState::SakuraVarshan;
                    send_tcp_seg(&mut self.net, v, 0x10, &[]);  // ACK
                } else if flags & 0x04 != 0 {  // RST
                    v.state = VarshanState::ZoVarshan;
                    return false;
                }
                true
            }
            VarshanState::SakuraVarshan => {
                // ACK any new data first.
                if !payload.is_empty() {
                    v.rx_buf.extend_from_slice(payload);
                    v.ack = seq.wrapping_add(payload.len() as u32);
                    send_tcp_seg(&mut self.net, v, 0x10, &[]);  // ACK
                }
                if flags & 0x01 != 0 {  // FIN
                    v.ack = v.ack.wrapping_add(1);
                    v.state = VarshanState::ZuVarshan;
                    send_tcp_seg(&mut self.net, v, 0x10, &[]);  // ACK the FIN
                }
                if flags & 0x04 != 0 {  // RST
                    v.state = VarshanState::ZoVarshan;
                    return false;
                }
                true
            }
            VarshanState::ZuVarshan => {
                // Absorb any remaining data; ignore.
                true
            }
            VarshanState::ZoVarshan => false,
        }
    }

    /// Send data on an established connection.
    pub fn send(&mut self, slot: usize, data: &[u8]) -> usize {
        let mut v = match self.conns[slot].take() {
            Some(v) if v.state == VarshanState::SakuraVarshan => v,
            other => { self.conns[slot] = other; return 0; }
        };
        send_tcp_seg(&mut self.net, &v, 0x18, data);  // PSH+ACK
        v.seq = v.seq.wrapping_add(data.len() as u32);
        self.conns[slot] = Some(v);
        data.len()
    }

    /// Read received data into buf.  Returns bytes copied.
    pub fn recv(&mut self, slot: usize, buf: &mut [u8]) -> usize {
        if let Some(ref mut v) = self.conns[slot] {
            let n = v.rx_buf.len().min(buf.len());
            if n == 0 { return 0; }
            buf[..n].copy_from_slice(&v.rx_buf[..n]);
            v.rx_buf.drain(..n);
            n
        } else {
            0
        }
    }

    /// True if the connection is in SakuraVarshan (ESTABLISHED).
    pub fn ready(&self, slot: usize) -> bool {
        matches!(
            self.conns[slot].as_ref().map(|v| v.state),
            Some(VarshanState::SakuraVarshan)
        )
    }

    /// Send FIN and remove the connection.
    pub fn close(&mut self, slot: usize) {
        if let Some(mut v) = self.conns[slot].take() {
            if v.state == VarshanState::SakuraVarshan {
                send_tcp_seg(&mut self.net, &v, 0x11, &[]);  // FIN+ACK
                v.seq = v.seq.wrapping_add(1);
            }
            // Drop v — ZoVarshan.
        }
    }

    pub fn slot_used(&self, slot: usize) -> bool {
        self.conns[slot].is_some()
    }

    #[cfg(target_arch = "riscv64")]
    pub fn print_queue_addrs(&self) {
        use crate::uart;
        uart::puts("rx_avail="); uart::putx(self.net.rx.q.avail as u64); uart::puts("\r\n");
        uart::puts("rx_used ="); uart::putx(self.net.rx.q.used  as u64); uart::puts("\r\n");
        uart::puts("tx_avail="); uart::putx(self.net.tx.q.avail as u64); uart::puts("\r\n");
        uart::puts("tx_used ="); uart::putx(self.net.tx.q.used  as u64); uart::puts("\r\n");
    }
}