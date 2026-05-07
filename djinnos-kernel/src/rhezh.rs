// Byte 258 — Rhezh — ChaCha20-Poly1305
// Memory without persistent self / Turritopsis dohrnii
//
// AEAD: the session key (mu) is the memory that persists across records.
// The nonce (vu) is the non-persistent self — unique per record, never repeated.
// Ba (Plain/Explicit) enters the void; Bo (Hidden/Occulted) emerges.
//
//   mu  — Mu (Water Terminator / memory from):  32-byte session traffic key
//   vu  — Vu (Death-moment / Never / Now):       12-byte per-record nonce
//   fi  — Fi (Known / context-sensitive):        additional authenticated data
//   ba  — Ba (Plain / Explicit):                plaintext
//   bo  — Bo (Hidden / Occulted):               ciphertext output (+ 16-byte tag)

// ── ChaCha20 ──────────────────────────────────────────────────────────────────

const CC_CONST: [u32; 4] = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574];

#[inline(always)]
fn qr(s: &mut [u32; 16], a: usize, b: usize, c: usize, d: usize) {
    s[a]=s[a].wrapping_add(s[b]); s[d]^=s[a]; s[d]=s[d].rotate_left(16);
    s[c]=s[c].wrapping_add(s[d]); s[b]^=s[c]; s[b]=s[b].rotate_left(12);
    s[a]=s[a].wrapping_add(s[b]); s[d]^=s[a]; s[d]=s[d].rotate_left(8);
    s[c]=s[c].wrapping_add(s[d]); s[b]^=s[c]; s[b]=s[b].rotate_left(7);
}

fn chacha20_block(mu: &[u8; 32], ctr: u32, vu: &[u8; 12]) -> [u8; 64] {
    let mut s = [0u32; 16];
    s[0..4].copy_from_slice(&CC_CONST);
    for i in 0..8 {
        s[4+i] = u32::from_le_bytes([mu[i*4],mu[i*4+1],mu[i*4+2],mu[i*4+3]]);
    }
    s[12] = ctr;
    s[13] = u32::from_le_bytes([vu[0], vu[1], vu[2], vu[3]]);
    s[14] = u32::from_le_bytes([vu[4], vu[5], vu[6], vu[7]]);
    s[15] = u32::from_le_bytes([vu[8], vu[9], vu[10], vu[11]]);
    let init = s;
    for _ in 0..10 {
        qr(&mut s,0,4,8, 12); qr(&mut s,1,5,9, 13);
        qr(&mut s,2,6,10,14); qr(&mut s,3,7,11,15);
        qr(&mut s,0,5,10,15); qr(&mut s,1,6,11,12);
        qr(&mut s,2,7,8, 13); qr(&mut s,3,4,9, 14);
    }
    for i in 0..16 { s[i] = s[i].wrapping_add(init[i]); }
    let mut out = [0u8; 64];
    for i in 0..16 { out[i*4..i*4+4].copy_from_slice(&s[i].to_le_bytes()); }
    out
}

fn chacha20_xor(mu: &[u8; 32], start_ctr: u32, vu: &[u8; 12], buf: &mut [u8]) {
    let mut ctr = start_ctr;
    let mut off = 0;
    while off < buf.len() {
        let ks = chacha20_block(mu, ctr, vu);
        let n  = (buf.len() - off).min(64);
        for i in 0..n { buf[off+i] ^= ks[i]; }
        ctr = ctr.wrapping_add(1);
        off += 64;
    }
}

// ── Poly1305 (RFC 8439) ───────────────────────────────────────────────────────
//
// Incremental state with a 16-byte pending buffer.
// pad16() zero-fills the current partial block and processes it — required by
// the RFC 8439 MAC construction which zero-pads AAD and ciphertext independently.

struct Poly {
    otk: [u8; 32],
    h:   [u64; 5],    // accumulator limbs (26-bit each)
    r:   [u64; 5],    // key r limbs
    r5:  [u64; 5],    // r * 5 (for wrap-around reduction)
    buf: [u8; 16],    // pending partial block
    blen: usize,
}

impl Poly {
    fn new(otk: &[u8; 32]) -> Self {
        let r_raw = u128::from_le_bytes([
            otk[0],otk[1],otk[2],otk[3],otk[4],otk[5],otk[6],otk[7],
            otk[8],otk[9],otk[10],otk[11],otk[12],otk[13],otk[14],otk[15],
        ]);
        let r = r_raw & 0x0ffffffc_0ffffffc_0ffffffc_0fffffffu128;
        let mut p = Poly {
            otk: *otk, h: [0;5],
            r: [0;5], r5: [0;5],
            buf: [0;16], blen: 0,
        };
        p.r[0] = ((r      ) & 0x3ffffff) as u64;
        p.r[1] = ((r >> 26) & 0x3ffffff) as u64;
        p.r[2] = ((r >> 52) & 0x3ffffff) as u64;
        p.r[3] = ((r >> 78) & 0x3ffffff) as u64;
        p.r[4] = ((r >>104) & 0x3ffffff) as u64;
        for i in 0..5 { p.r5[i] = p.r[i] * 5; }
        p
    }

    fn block17(&mut self, blk: &[u8; 17]) {
        let t0 = u32::from_le_bytes([blk[0],blk[1],blk[2],blk[3]]) as u64;
        let t1 = u32::from_le_bytes([blk[4],blk[5],blk[6],blk[7]]) as u64;
        let t2 = u32::from_le_bytes([blk[8],blk[9],blk[10],blk[11]]) as u64;
        let t3 = u32::from_le_bytes([blk[12],blk[13],blk[14],blk[15]]) as u64;
        let t4 = blk[16] as u64;
        self.h[0] += t0 & 0x3ffffff;
        self.h[1] += ((t0>>26)|(t1<<6 )) & 0x3ffffff;
        self.h[2] += ((t1>>20)|(t2<<12)) & 0x3ffffff;
        self.h[3] += ((t2>>14)|(t3<<18)) & 0x3ffffff;
        self.h[4] += ((t3>>8) |(t4<<24)) & 0x3ffffff;
        let (h,r,r5) = (&mut self.h, &self.r, &self.r5);
        let d0=(h[0]as u128*r[0]as u128)+(h[1]as u128*r5[4]as u128)+(h[2]as u128*r5[3]as u128)+(h[3]as u128*r5[2]as u128)+(h[4]as u128*r5[1]as u128);
        let d1=(h[0]as u128*r[1]as u128)+(h[1]as u128*r[0]as u128) +(h[2]as u128*r5[4]as u128)+(h[3]as u128*r5[3]as u128)+(h[4]as u128*r5[2]as u128);
        let d2=(h[0]as u128*r[2]as u128)+(h[1]as u128*r[1]as u128) +(h[2]as u128*r[0]as u128) +(h[3]as u128*r5[4]as u128)+(h[4]as u128*r5[3]as u128);
        let d3=(h[0]as u128*r[3]as u128)+(h[1]as u128*r[2]as u128) +(h[2]as u128*r[1]as u128) +(h[3]as u128*r[0]as u128) +(h[4]as u128*r5[4]as u128);
        let d4=(h[0]as u128*r[4]as u128)+(h[1]as u128*r[3]as u128) +(h[2]as u128*r[2]as u128) +(h[3]as u128*r[1]as u128) +(h[4]as u128*r[0]as u128);
        let c0=d0>>26; h[0]=(d0&0x3ffffff) as u64;
        let c1=(d1+c0)>>26; h[1]=((d1+c0)&0x3ffffff) as u64;
        let c2=(d2+c1)>>26; h[2]=((d2+c1)&0x3ffffff) as u64;
        let c3=(d3+c2)>>26; h[3]=((d3+c2)&0x3ffffff) as u64;
        let c4=(d4+c3)>>26; h[4]=((d4+c3)&0x3ffffff) as u64;
        h[0] += c4 as u64 * 5;
        let c5 = h[0]>>26; h[0] &= 0x3ffffff; h[1] += c5;
    }

    fn process16(&mut self, blk: &[u8; 16]) {
        let mut b17 = [0u8; 17];
        b17[..16].copy_from_slice(blk);
        b17[16] = 1;
        self.block17(&b17);
    }

    /// Feed bytes into the MAC state.
    fn feed(&mut self, data: &[u8]) {
        let mut i = 0;
        if self.blen > 0 {
            let need = 16 - self.blen;
            let take = need.min(data.len());
            self.buf[self.blen..self.blen+take].copy_from_slice(&data[..take]);
            self.blen += take;
            i = take;
            if self.blen == 16 {
                let b = self.buf;
                self.process16(&b);
                self.blen = 0;
            }
        }
        while i + 16 <= data.len() {
            let mut b = [0u8; 16];
            b.copy_from_slice(&data[i..i+16]);
            self.process16(&b);
            i += 16;
        }
        let rem = data.len() - i;
        if rem > 0 {
            self.buf[..rem].copy_from_slice(&data[i..]);
            self.blen = rem;
        }
    }

    /// Zero-pad current partial block to 16 bytes and process it.
    /// Called between AAD and ciphertext, and between ciphertext and length fields.
    fn pad16(&mut self) {
        if self.blen > 0 {
            for j in self.blen..16 { self.buf[j] = 0; }
            let b = self.buf;
            self.process16(&b);
            self.blen = 0;
        }
    }

    fn finish(mut self) -> [u8; 16] {
        // Process any remaining partial block with variable-length high bit.
        if self.blen > 0 {
            let mut b17 = [0u8; 17];
            b17[..self.blen].copy_from_slice(&self.buf[..self.blen]);
            b17[self.blen] = 1;
            self.block17(&b17);
        }
        let (mut h0,mut h1,mut h2,mut h3,mut h4) =
            (self.h[0],self.h[1],self.h[2],self.h[3],self.h[4]);
        // Final carry.
        let c=h1>>26;h1&=0x3ffffff;h2+=c;
        let c=h2>>26;h2&=0x3ffffff;h3+=c;
        let c=h3>>26;h3&=0x3ffffff;h4+=c;
        let c=h4>>26;h4&=0x3ffffff;h0+=c*5;
        let c=h0>>26;h0&=0x3ffffff;h1+=c;
        // Conditionally subtract p = 2^130 - 5.
        let mut g0=h0.wrapping_add(5);let c=g0>>26;g0&=0x3ffffff;
        let mut g1=h1.wrapping_add(c);let c=g1>>26;g1&=0x3ffffff;
        let mut g2=h2.wrapping_add(c);let c=g2>>26;g2&=0x3ffffff;
        let mut g3=h3.wrapping_add(c);let c=g3>>26;g3&=0x3ffffff;
        let mut g4=h4.wrapping_add(c).wrapping_sub(1u64<<26);
        let mask=(g4>>63).wrapping_sub(1)&0x3ffffff;
        g0&=mask;g1&=mask;g2&=mask;g3&=mask;g4&=mask;
        let im=!mask&0x3ffffff;
        h0=(h0&im)|g0;h1=(h1&im)|g1;h2=(h2&im)|g2;h3=(h3&im)|g3;h4=(h4&im)|g4;
        // Pack h into 128-bit LE and add s.
        let hval = (h0 as u128)
            | ((h1 as u128) << 26)
            | ((h2 as u128) << 52)
            | ((h3 as u128) << 78)
            | ((h4 as u128) << 104);
        let s0 = u64::from_le_bytes([
            self.otk[16],self.otk[17],self.otk[18],self.otk[19],
            self.otk[20],self.otk[21],self.otk[22],self.otk[23],
        ]);
        let s1 = u64::from_le_bytes([
            self.otk[24],self.otk[25],self.otk[26],self.otk[27],
            self.otk[28],self.otk[29],self.otk[30],self.otk[31],
        ]);
        let sval = s0 as u128 | ((s1 as u128) << 64);
        hval.wrapping_add(sval).to_le_bytes()
    }
}

// ── AEAD tag (RFC 8439 §2.8) ─────────────────────────────────────────────────

fn rhezh_tag(mu: &[u8; 32], vu: &[u8; 12], fi: &[u8], bo_ct: &[u8]) -> [u8; 16] {
    let otk_block = chacha20_block(mu, 0, vu);
    let mut otk = [0u8; 32];
    otk.copy_from_slice(&otk_block[..32]);

    let mut mac = Poly::new(&otk);
    mac.feed(fi);       // AAD
    mac.pad16();        // pad AAD to 16-byte boundary
    mac.feed(bo_ct);    // ciphertext
    mac.pad16();        // pad ciphertext to 16-byte boundary

    let mut lens = [0u8; 16];
    lens[0..8].copy_from_slice(&(fi.len() as u64).to_le_bytes());
    lens[8..16].copy_from_slice(&(bo_ct.len() as u64).to_le_bytes());
    mac.feed(&lens);

    mac.finish()
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Rhezh seal: encrypt ba → bo[..ba.len()] and append 16-byte tag at bo[ba.len()..].
/// bo must be at least ba.len() + 16 bytes.
pub fn rhezh_seal(mu: &[u8; 32], vu: &[u8; 12], fi: &[u8], ba: &[u8], bo: &mut [u8]) {
    let ct = &mut bo[..ba.len()];
    ct.copy_from_slice(ba);
    chacha20_xor(mu, 1, vu, ct);
    let tag = rhezh_tag(mu, vu, fi, &bo[..ba.len()]);
    bo[ba.len()..ba.len()+16].copy_from_slice(&tag);
}

/// Rhezh open: verify tag and decrypt bo (ciphertext+tag) → ba.
/// Returns false and leaves ba undefined if authentication fails.
pub fn rhezh_open(mu: &[u8; 32], vu: &[u8; 12], fi: &[u8], bo: &[u8], ba: &mut [u8]) -> bool {
    if bo.len() < 16 { return false; }
    let ct_len = bo.len() - 16;
    if ba.len() < ct_len { return false; }
    let expected = rhezh_tag(mu, vu, fi, &bo[..ct_len]);
    let tag = &bo[ct_len..ct_len+16];
    let mut diff = 0u8;
    for i in 0..16 { diff |= tag[i] ^ expected[i]; }
    if diff != 0 { return false; }
    ba[..ct_len].copy_from_slice(&bo[..ct_len]);
    chacha20_xor(mu, 1, vu, &mut ba[..ct_len]);
    true
}