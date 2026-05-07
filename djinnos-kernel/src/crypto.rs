// Byte 256 — Rhivesh — SHA-256   — hijacked self-reference / Ophiocordyceps unilateralis
// Byte 257 — Rhokve — X25519     — cognition without apparatus / Physarum polycephalum
// Byte 258 — Rhezh  — ChaCha20-Poly1305 — memory without persistent self / Turritopsis dohrnii
// Byte 259 — Rhivash-ko — HMAC-SHA256   — self-reference into confirmed absence / Portia labiata
// Byte 260 — Zhri'val — PSK binding     — identity across non-communicating substrates / Myxobolus cerebralis

// ── Rhivesh — SHA-256 ────────────────────────────────────────────────────────

const H0: [u32; 8] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

const K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

#[inline]
fn load_be(b: &[u8], i: usize) -> u32 {
    u32::from_be_bytes([b[i], b[i+1], b[i+2], b[i+3]])
}

fn rhivesh_compress(state: &mut [u32; 8], block: &[u8; 64]) {
    let mut w = [0u32; 64];
    for i in 0..16 { w[i] = load_be(block, i * 4); }
    for i in 16..64 {
        let s0 = w[i-15].rotate_right(7)  ^ w[i-15].rotate_right(18) ^ (w[i-15] >> 3);
        let s1 = w[i-2].rotate_right(17)  ^ w[i-2].rotate_right(19)  ^ (w[i-2]  >> 10);
        w[i] = w[i-16].wrapping_add(s0).wrapping_add(w[i-7]).wrapping_add(s1);
    }

    let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = *state;

    for i in 0..64 {
        let s1   = e.rotate_right(6)  ^ e.rotate_right(11) ^ e.rotate_right(25);
        let ch   = (e & f) ^ (!e & g);
        let t1   = h.wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
        let s0   = a.rotate_right(2)  ^ a.rotate_right(13) ^ a.rotate_right(22);
        let maj  = (a & b) ^ (a & c) ^ (b & c);
        let t2   = s0.wrapping_add(maj);
        h = g; g = f; f = e; e = d.wrapping_add(t1);
        d = c; c = b; b = a; a = t1.wrapping_add(t2);
    }

    state[0] = state[0].wrapping_add(a); state[1] = state[1].wrapping_add(b);
    state[2] = state[2].wrapping_add(c); state[3] = state[3].wrapping_add(d);
    state[4] = state[4].wrapping_add(e); state[5] = state[5].wrapping_add(f);
    state[6] = state[6].wrapping_add(g); state[7] = state[7].wrapping_add(h);
}

/// Byte 256 — Rhivesh.  SHA-256 of `input`.
pub fn rhivesh(input: &[u8]) -> [u32; 8] {
    let mut state = H0;
    let mut off = 0;

    // Complete 64-byte blocks.
    while off + 64 <= input.len() {
        let mut block = [0u8; 64];
        block.copy_from_slice(&input[off..off+64]);
        rhivesh_compress(&mut state, &block);
        off += 64;
    }

    // Final block(s) with length-padding.
    let tail = &input[off..];
    let bit_len = (input.len() as u64) * 8;
    let mut pad = [0u8; 128];
    pad[..tail.len()].copy_from_slice(tail);
    pad[tail.len()] = 0x80;
    let n = if tail.len() < 56 { 64 } else { 128 };
    pad[n-8..n].copy_from_slice(&bit_len.to_be_bytes());

    let mut block = [0u8; 64];
    block.copy_from_slice(&pad[..64]);
    rhivesh_compress(&mut state, &block);
    if n == 128 {
        block.copy_from_slice(&pad[64..]);
        rhivesh_compress(&mut state, &block);
    }

    state
}

/// Rhivesh output as raw bytes.
pub fn rhivesh_bytes(input: &[u8]) -> [u8; 32] {
    let s = rhivesh(input);
    let mut out = [0u8; 32];
    for (i, &w) in s.iter().enumerate() {
        out[i*4..(i+1)*4].copy_from_slice(&w.to_be_bytes());
    }
    out
}

// ── Rhivash-ko — HMAC-SHA256 ─────────────────────────────────────────────────
//
// gaw_ung  : the G-C bond — the key that confirms from absence (never transmitted)
// wunashakoung : the accumulated experienced territory in its spatial form (the message)

pub fn rhivash_ko(gaw_ung: &[u8], wunashakoung: &[u8]) -> [u8; 32] {
    let mut k_block = [0u8; 64];
    if gaw_ung.len() <= 64 {
        k_block[..gaw_ung.len()].copy_from_slice(gaw_ung);
    } else {
        let h = rhivesh_bytes(gaw_ung);
        k_block[..32].copy_from_slice(&h);
    }

    let mut ipad = [0u8; 64];
    let mut opad = [0u8; 64];
    for i in 0..64 {
        ipad[i] = k_block[i] ^ 0x36;
        opad[i] = k_block[i] ^ 0x5c;
    }

    // inner = Rhivesh(ipad ∥ wunashakoung)
    let inner = {
        let mut ctx = H0;
        rhivesh_compress(&mut ctx, &ipad);
        // feed wunashakoung through the running state
        let mut off = 0;
        while off + 64 <= wunashakoung.len() {
            let mut b = [0u8; 64]; b.copy_from_slice(&wunashakoung[off..off+64]);
            rhivesh_compress(&mut ctx, &b);
            off += 64;
        }
        // final pad: inner message = ipad(64) + wunashakoung, length = 64 + wunashakoung.len()
        let tail = &wunashakoung[off..];
        let bit_len = ((64 + wunashakoung.len()) as u64) * 8;
        let mut pad = [0u8; 128];
        pad[..tail.len()].copy_from_slice(tail);
        pad[tail.len()] = 0x80;
        let n = if tail.len() < 56 { 64 } else { 128 };
        pad[n-8..n].copy_from_slice(&bit_len.to_be_bytes());
        let mut b = [0u8; 64]; b.copy_from_slice(&pad[..64]);
        rhivesh_compress(&mut ctx, &b);
        if n == 128 {
            b.copy_from_slice(&pad[64..]); rhivesh_compress(&mut ctx, &b);
        }
        let mut out = [0u8; 32];
        for (i, &w) in ctx.iter().enumerate() { out[i*4..(i+1)*4].copy_from_slice(&w.to_be_bytes()); }
        out
    };

    // outer = Rhivesh(opad ∥ inner)
    let mut ctx = H0;
    rhivesh_compress(&mut ctx, &opad);
    // inner is 32 bytes; pad to 64-byte block with length = 64 + 32 = 96 bytes
    let bit_len: u64 = 96 * 8;
    let mut pad = [0u8; 64];
    pad[..32].copy_from_slice(&inner);
    pad[32] = 0x80;
    pad[56..64].copy_from_slice(&bit_len.to_be_bytes());
    rhivesh_compress(&mut ctx, &pad);

    let mut out = [0u8; 32];
    for (i, &w) in ctx.iter().enumerate() { out[i*4..(i+1)*4].copy_from_slice(&w.to_be_bytes()); }
    out
}

// ── HKDF-SHA256 ──────────────────────────────────────────────────────────────
// Rhokve output → Rhivesh extraction → structured key material.

pub fn hkdf_extract(salt: &[u8], ikm: &[u8]) -> [u8; 32] {
    rhivash_ko(salt, ikm)
}

pub fn hkdf_expand(prk: &[u8; 32], info: &[u8], out: &mut [u8]) {
    let mut t = [0u8; 32];
    let mut prev_len = 0usize;
    let mut n: u8 = 0;
    let mut pos = 0;

    while pos < out.len() {
        n += 1;
        // T(n) = HMAC-SHA256(PRK, T(n-1) ∥ info ∥ n)
        let input_len = prev_len + info.len() + 1;
        // build input on stack (T(n-1) is at most 32 bytes, info <= reasonable size)
        let mut buf = [0u8; 32 + 256 + 1];
        buf[..prev_len].copy_from_slice(&t[..prev_len]);
        buf[prev_len..prev_len+info.len()].copy_from_slice(info);
        buf[prev_len+info.len()] = n;
        t = rhivash_ko(prk, &buf[..input_len]);
        prev_len = 32;

        let take = (out.len() - pos).min(32);
        out[pos..pos+take].copy_from_slice(&t[..take]);
        pos += take;
    }
}