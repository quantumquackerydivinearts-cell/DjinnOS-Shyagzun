// profile.rs -- Boot-time user profiles for DjinnOS.
//
// Profiles are stored in the Sa volume as "profiles.cfg".
// Format: one profile per line: name:hash_hex:flags_hex
//
// Permission flags:
//   bit 0 = can_shell    bit 1 = can_atelier
//   bit 2 = can_edit     bit 3 = admin
//
// Password security: FNV-1a 32-bit hash -- not cryptographically strong,
// appropriate for a local bare-metal game OS. Upgrade to a KDF if the
// threat model changes.

const MAX_PROFILES: usize = 8;
const MAX_NAME:     usize = 16;
const CFG_FILE:     &[u8]  = b"profiles.cfg";

#[derive(Clone, Copy)]
pub struct Profile {
    pub name:   [u8; MAX_NAME],
    pub name_n: usize,
    pub hash:   u32,   // FNV-1a of password; 0 = no password required
    pub flags:  u8,
}

impl Profile {
    pub fn name_str(&self) -> &[u8] { &self.name[..self.name_n] }
    pub fn can_shell(&self)   -> bool { self.flags & 0x01 != 0 }
    pub fn can_atelier(&self) -> bool { self.flags & 0x02 != 0 }
    pub fn can_edit(&self)    -> bool { self.flags & 0x04 != 0 }
    pub fn is_admin(&self)    -> bool { self.flags & 0x08 != 0 }
}

static mut PROFILES:   [Profile; MAX_PROFILES] = [
    Profile { name: [0u8; MAX_NAME], name_n: 0, hash: 0, flags: 0 };
    MAX_PROFILES
];
static mut PROFILE_N:  usize               = 0;
static mut ACTIVE_IDX: Option<usize>       = None;
static mut LOGOUT_REQ: bool                = false;

// ── FNV-1a ────────────────────────────────────────────────────────────────────

pub fn fnv1a(data: &[u8]) -> u32 {
    let mut h: u32 = 2166136261;
    for &b in data { h = h.wrapping_mul(16777619) ^ b as u32; }
    h
}

// ── Serialisation helpers ─────────────────────────────────────────────────────

fn hex_u32(n: u32, buf: &mut [u8; 8]) {
    for i in 0..8 {
        let nibble = (n >> (28 - i * 4)) & 0xF;
        buf[i] = if nibble < 10 { b'0' + nibble as u8 } else { b'a' + nibble as u8 - 10 };
    }
}

fn parse_hex_u32(s: &[u8]) -> u32 {
    let mut v = 0u32;
    for &b in s {
        v <<= 4;
        v |= match b {
            b'0'..=b'9' => (b - b'0') as u32,
            b'a'..=b'f' => (b - b'a' + 10) as u32,
            b'A'..=b'F' => (b - b'A' + 10) as u32,
            _ => 0,
        };
    }
    v
}

// ── Defaults ──────────────────────────────────────────────────────────────────

fn add_default(name: &[u8], hash: u32, flags: u8) {
    unsafe {
        if PROFILE_N >= MAX_PROFILES { return; }
        let n = name.len().min(MAX_NAME);
        PROFILES[PROFILE_N].name[..n].copy_from_slice(&name[..n]);
        PROFILES[PROFILE_N].name_n = n;
        PROFILES[PROFILE_N].hash   = hash;
        PROFILES[PROFILE_N].flags  = flags;
        PROFILE_N += 1;
    }
}

fn write_defaults() {
    add_default(b"Ko",    0, 0xFF);
    add_default(b"guest", 0, 0x03);
    save();
}

// ── Save / load ───────────────────────────────────────────────────────────────

fn save() {
    static mut WBUF: [u8; 512] = [0u8; 512];
    let buf = unsafe { &mut WBUF };
    let mut off = 0usize;
    unsafe {
        for i in 0..PROFILE_N {
            let p = &PROFILES[i];
            let nn = p.name_n.min(MAX_NAME);
            if off + nn + 12 > buf.len() { break; }
            buf[off..off+nn].copy_from_slice(&p.name[..nn]);
            off += nn;
            buf[off] = b':'; off += 1;
            let mut hx = [0u8; 8];
            hex_u32(p.hash, &mut hx);
            buf[off..off+8].copy_from_slice(&hx); off += 8;
            buf[off] = b':'; off += 1;
            let mut fx = [0u8; 2];
            let hi = (p.flags >> 4) & 0xF;
            let lo = p.flags & 0xF;
            fx[0] = if hi < 10 { b'0' + hi } else { b'a' + hi - 10 };
            fx[1] = if lo < 10 { b'0' + lo } else { b'a' + lo - 10 };
            buf[off..off+2].copy_from_slice(&fx); off += 2;
            buf[off] = b'\n'; off += 1;
        }
    }
    crate::sa::write_file(CFG_FILE, unsafe { &WBUF[..off] });
}

fn parse_line(line: &[u8]) -> Option<(usize, u32, u8)> {
    // name:hash8:flags2
    let colon1 = line.iter().position(|&b| b == b':')?;
    let rest    = &line[colon1 + 1..];
    let colon2  = rest.iter().position(|&b| b == b':')?;
    if colon1 == 0 || colon2 != 8 || rest.len() < colon2 + 3 { return None; }
    let hash  = parse_hex_u32(&rest[..8]);
    let flags = parse_hex_u32(&rest[colon2+1..colon2+3]) as u8;
    Some((colon1, hash, flags))
}

// ── Public API ────────────────────────────────────────────────────────────────

pub fn load_or_init() {
    static mut RBUF: [u8; 512] = [0u8; 512];
    let buf = unsafe { &mut RBUF };
    let n = crate::sa::read_file(CFG_FILE, buf);
    if n == 0 {
        write_defaults();
        return;
    }
    unsafe { PROFILE_N = 0; }
    let data = &buf[..n];
    let mut start = 0usize;
    while start < data.len() {
        let end = data[start..].iter().position(|&b| b == b'\n')
            .map(|p| start + p).unwrap_or(data.len());
        let line = &data[start..end];
        start = end + 1;
        if line.is_empty() { continue; }
        if let Some((colon1, hash, flags)) = parse_line(line) {
            unsafe {
                if PROFILE_N >= MAX_PROFILES { break; }
                let nn = colon1.min(MAX_NAME);
                PROFILES[PROFILE_N].name[..nn].copy_from_slice(&line[..nn]);
                PROFILES[PROFILE_N].name_n = nn;
                PROFILES[PROFILE_N].hash   = hash;
                PROFILES[PROFILE_N].flags  = flags;
                PROFILE_N += 1;
            }
        }
    }
    if unsafe { PROFILE_N } == 0 { write_defaults(); }
}

pub fn count() -> usize { unsafe { PROFILE_N } }

pub fn get(i: usize) -> Option<&'static Profile> {
    unsafe { if i < PROFILE_N { Some(&PROFILES[i]) } else { None } }
}

pub fn find(name: &[u8]) -> Option<&'static Profile> {
    unsafe {
        PROFILES[..PROFILE_N].iter()
            .find(|p| p.name_str() == name)
    }
}

pub fn authenticate(name: &[u8], password: &[u8]) -> Option<&'static Profile> {
    let p = find(name)?;
    if p.hash == 0 || fnv1a(password) == p.hash { Some(p) } else { None }
}

pub fn active() -> Option<&'static Profile> {
    unsafe { ACTIVE_IDX.and_then(|i| get(i)) }
}

pub fn set_active(p: &'static Profile) {
    unsafe {
        ACTIVE_IDX = PROFILES[..PROFILE_N].iter()
            .position(|q| core::ptr::eq(q, p));
    }
}

pub fn clear_active() {
    unsafe { ACTIVE_IDX = None; }
}

pub fn request_logout() {
    unsafe { LOGOUT_REQ = true; clear_active(); }
}

pub fn consume_logout() -> bool {
    unsafe { if LOGOUT_REQ { LOGOUT_REQ = false; true } else { false } }
}