// dhcp.rs -- DHCP client for DjinnOS.
//
// Implements DISCOVER -> OFFER -> REQUEST -> ACK over raw Ethernet/UDP.
// Works with any NetworkDevice (E1000, UsbNet/RNDIS, VirtIO).
//
// After a successful lease, calls net_stack::set_addrs() to configure
// OUR_IP and GATEWAY_IP for the TCP stack.
//
// Android/Motorola USB tethering: assigns from 192.168.42.0/24,
// gateway = 192.168.42.129, DHCP server = 192.168.42.129.

use crate::net_stack::NetworkDevice;

const ETH_IPV4: u16 = 0x0800;
const IP_UDP:   u8  = 17;
const BOOTP_REQUEST: u8 = 1;
const BOOTP_REPLY:   u8 = 2;
const DHCP_MAGIC: [u8; 4] = [0x63, 0x82, 0x53, 0x63];
const OPT_MSG_TYPE: u8 = 53;
const OPT_SERVER_ID: u8 = 54;
const OPT_REQ_IP: u8 = 50;
const OPT_ROUTER: u8 = 3;
const OPT_MASK:   u8 = 1;
const OPT_END:    u8 = 255;
const DHCP_DISCOVER: u8 = 1;
const DHCP_OFFER:    u8 = 2;
const DHCP_REQUEST:  u8 = 3;
const DHCP_ACK:      u8 = 5;

pub struct DhcpResult {
    pub ip:      [u8; 4],
    pub gateway: [u8; 4],
    pub mask:    [u8; 4],
}

// ── Frame builder ─────────────────────────────────────────────────────────────

fn udp_checksum_zero() -> [u8; 2] { [0u8; 2] } // UDP checksum is optional for IPv4

fn build_dhcp(mac: [u8; 6], msg_type: u8, xid: u32,
              offered_ip: [u8; 4], server_ip: [u8; 4],
              buf: &mut [u8; 512]) -> usize
{
    // Ethernet header
    let bcast = [0xFFu8; 6];
    buf[0..6].copy_from_slice(&bcast);
    buf[6..12].copy_from_slice(&mac);
    buf[12..14].copy_from_slice(&ETH_IPV4.to_be_bytes());

    // IPv4 header (20 bytes at offset 14)
    let payload_len = 8 + 236 + 64; // UDP + BOOTP fixed + options budget
    let ip_len = 20 + payload_len;
    let ip = &mut buf[14..34];
    ip[0] = 0x45;
    ip[1] = 0;
    ip[2..4].copy_from_slice(&(ip_len as u16).to_be_bytes());
    ip[4..6].copy_from_slice(&(xid as u16).to_be_bytes()); // use xid as IP ID
    ip[6..8].copy_from_slice(&0u16.to_be_bytes());
    ip[8] = 64;        // TTL
    ip[9] = IP_UDP;
    // src = 0.0.0.0, dst = 255.255.255.255
    ip[12..16].fill(0);
    ip[16..20].fill(0xFF);
    // IP checksum
    let cs = ip_checksum(&buf[14..34]);
    buf[14+10..14+12].copy_from_slice(&cs.to_be_bytes());

    // UDP header (8 bytes at offset 34)
    buf[34..36].copy_from_slice(&68u16.to_be_bytes()); // src port (DHCP client)
    buf[36..38].copy_from_slice(&67u16.to_be_bytes()); // dst port (DHCP server)
    let udp_len = (payload_len as u16).to_be_bytes();
    buf[38..40].copy_from_slice(&udp_len);
    buf[40..42].copy_from_slice(&udp_checksum_zero());  // checksum = 0 (optional)

    // BOOTP payload starts at offset 42
    let b = &mut buf[42..];
    b[0] = BOOTP_REQUEST;
    b[1] = 1; // htype = Ethernet
    b[2] = 6; // hlen  = 6 (MAC length)
    b[3] = 0; // hops  = 0
    b[4..8].copy_from_slice(&xid.to_be_bytes());
    b[8..10].fill(0);  // secs
    b[10..12].copy_from_slice(&0x8000u16.to_be_bytes()); // flags: broadcast
    b[12..16].fill(0); // ciaddr = 0
    b[16..20].copy_from_slice(&offered_ip); // yiaddr
    b[20..24].fill(0); // siaddr
    b[24..28].fill(0); // giaddr
    b[28..34].copy_from_slice(&mac);
    b[34..44].fill(0); // chaddr padding
    // sname (64 bytes) + file (128 bytes) = skip
    // options start at b[236]
    let opt = &mut b[236..];
    opt[0..4].copy_from_slice(&DHCP_MAGIC);
    let mut oi = 4usize;

    // Option 53: message type
    opt[oi] = OPT_MSG_TYPE; opt[oi+1] = 1; opt[oi+2] = msg_type; oi += 3;

    if msg_type == DHCP_REQUEST {
        // Option 50: requested IP
        opt[oi] = OPT_REQ_IP; opt[oi+1] = 4;
        opt[oi+2..oi+6].copy_from_slice(&offered_ip); oi += 6;
        // Option 54: server identifier
        opt[oi] = OPT_SERVER_ID; opt[oi+1] = 4;
        opt[oi+2..oi+6].copy_from_slice(&server_ip); oi += 6;
    }

    // Option 61: client identifier
    opt[oi] = 61; opt[oi+1] = 7; opt[oi+2] = 1;
    opt[oi+3..oi+9].copy_from_slice(&mac); oi += 9;

    // Option 55: parameter request list
    opt[oi] = 55; opt[oi+1] = 3; opt[oi+2] = OPT_MASK; opt[oi+3] = OPT_ROUTER; opt[oi+4] = 6; oi += 5;

    // End
    opt[oi] = OPT_END; oi += 1;

    42 + 236 + oi  // total frame length
}

// ── Frame parser ──────────────────────────────────────────────────────────────

struct DhcpReply {
    msg_type:  u8,
    your_ip:   [u8; 4],
    server_ip: [u8; 4],
    gateway:   [u8; 4],
    mask:      [u8; 4],
}

fn parse_dhcp_reply(frame: &[u8], xid: u32) -> Option<DhcpReply> {
    if frame.len() < 42 + 240 { return None; }
    // Ethernet ethertype check
    if u16::from_be_bytes([frame[12], frame[13]]) != ETH_IPV4 { return None; }
    // IP proto = UDP
    if frame[14 + 9] != IP_UDP { return None; }
    // UDP dst port = 68
    if u16::from_be_bytes([frame[36], frame[37]]) != 68 { return None; }
    // BOOTP op = reply
    let b = &frame[42..];
    if b[0] != BOOTP_REPLY { return None; }
    // XID match
    let pkt_xid = u32::from_be_bytes([b[4], b[5], b[6], b[7]]);
    if pkt_xid != xid { return None; }
    // Magic cookie
    if b[236..240] != DHCP_MAGIC { return None; }

    let your_ip   = [b[16], b[17], b[18], b[19]];
    let server_ip = [b[20], b[21], b[22], b[23]];

    let mut msg_type  = 0u8;
    let mut gateway   = [0u8; 4];
    let mut mask      = [255, 255, 255, 0];
    let mut srv_id    = server_ip;

    let mut oi = 240usize;
    while oi + 1 < b.len() {
        let t = b[oi]; oi += 1;
        if t == OPT_END { break; }
        if t == 0 { continue; } // pad
        if oi >= b.len() { break; }
        let l = b[oi] as usize; oi += 1;
        if oi + l > b.len() { break; }
        let v = &b[oi..oi+l];
        match t {
            OPT_MSG_TYPE if l >= 1 => { msg_type = v[0]; }
            OPT_ROUTER   if l >= 4 => { gateway = [v[0],v[1],v[2],v[3]]; }
            OPT_MASK     if l >= 4 => { mask    = [v[0],v[1],v[2],v[3]]; }
            OPT_SERVER_ID if l >= 4 => { srv_id = [v[0],v[1],v[2],v[3]]; }
            _ => {}
        }
        oi += l;
    }

    if msg_type == 0 { return None; }
    Some(DhcpReply { msg_type, your_ip, server_ip: srv_id, gateway, mask })
}

// ── IP checksum ───────────────────────────────────────────────────────────────

fn ip_checksum(hdr: &[u8]) -> u16 {
    let mut sum = 0u32;
    let mut i = 0;
    while i + 1 < hdr.len() {
        sum += u16::from_be_bytes([hdr[i], hdr[i+1]]) as u32;
        i += 2;
    }
    while sum >> 16 != 0 { sum = (sum & 0xffff) + (sum >> 16); }
    !(sum as u16)
}

// ── XID source ────────────────────────────────────────────────────────────────

fn make_xid(mac: [u8; 6]) -> u32 {
    let t = crate::arch::read_mtime() as u32;
    t ^ u32::from_le_bytes([mac[2], mac[3], mac[4], mac[5]])
}

// ── Main acquire function ─────────────────────────────────────────────────────

/// Run DHCP on the given NIC and configure the TCP stack.
/// Returns true and logs IP on success; returns false and falls back to
/// static config on failure.
pub fn acquire(nic: &mut dyn NetworkDevice) -> bool {
    let mac = nic.mac();
    let xid = make_xid(mac);
    let mut buf = [0u8; 512];

    crate::uart::puts("DHCP: sending DISCOVER...\r\n");

    // ── DISCOVER ──────────────────────────────────────────────────────────────
    let n = build_dhcp(mac, DHCP_DISCOVER, xid, [0;4], [0;4], &mut buf);
    nic.send_frame(&buf[..n]);

    // Poll for OFFER (up to ~2M iterations ≈ several seconds)
    let offer = poll_for(nic, xid, DHCP_OFFER, 2_000_000);
    let Some(offer) = offer else {
        crate::uart::puts("DHCP: no OFFER received\r\n");
        return false;
    };

    crate::uart::puts("DHCP: got OFFER ");
    print_ip(offer.your_ip);

    // ── REQUEST ───────────────────────────────────────────────────────────────
    let n = build_dhcp(mac, DHCP_REQUEST, xid, offer.your_ip, offer.server_ip, &mut buf);
    nic.send_frame(&buf[..n]);

    // Poll for ACK
    let ack = poll_for(nic, xid, DHCP_ACK, 2_000_000);
    let Some(ack) = ack else {
        crate::uart::puts("DHCP: no ACK received\r\n");
        return false;
    };

    crate::uart::puts("DHCP: ACK — IP ");
    print_ip(ack.your_ip);
    crate::uart::puts(" GW ");
    print_ip(ack.gateway);

    crate::net_stack::set_addrs(ack.your_ip, ack.gateway);
    true
}

fn poll_for(nic: &mut dyn NetworkDevice, xid: u32, want: u8, limit: u32)
    -> Option<DhcpReply>
{
    for _ in 0..limit {
        if let Some(frame) = nic.recv_frame() {
            if let Some(reply) = parse_dhcp_reply(&frame, xid) {
                if reply.msg_type == want { return Some(reply); }
            }
        }
    }
    None
}

fn print_ip(ip: [u8; 4]) {
    for (i, &b) in ip.iter().enumerate() {
        if i > 0 { crate::uart::putc(b'.'); }
        let mut tmp = [0u8; 3]; let mut n = 0;
        let mut v = b; if v == 0 { crate::uart::putc(b'0'); } else {
            while v > 0 { tmp[n] = b'0' + v % 10; n += 1; v /= 10; }
            for i in (0..n).rev() { crate::uart::putc(tmp[i]); }
        }
    }
    crate::uart::puts("\r\n");
}
