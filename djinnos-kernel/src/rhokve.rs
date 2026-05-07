// Byte 257 — Rhokve — X25519
// Cognition without apparatus / Physarum polycephalum
//
// Curve25519 Diffie-Hellman over GF(2^255 - 19).
// Field elements: 5 limbs, each < 2^52, radix 2^51.
// value = h[0] + h[1]*2^51 + h[2]*2^102 + h[3]*2^153 + h[4]*2^204
//
// Parameters:
//   ungkael — ga+wu+ung: the Kael-charged spatial element (private scalar)
//   ung     — the structural curve point (public key or base point)

const MASK51: u64 = (1u64 << 51) - 1;
const P: [u64; 5] = [
    0x0007ffffffffffff,  // 2^51 - 1
    0x0007ffffffffffff,
    0x0007ffffffffffff,
    0x0007ffffffffffff,
    0x0007ffffffffffff,
];

// ── Field arithmetic ──────────────────────────────────────────────────────────

fn fe_from_bytes(b: &[u8; 32]) -> [u64; 5] {
    let mut b2 = *b;
    b2[31] &= 0x7f;   // clear bit 255 (must be 0 for Curve25519)

    let load = |i: usize| -> u64 {
        let mut buf = [0u8; 8];
        let n = 8.min(32usize.saturating_sub(i));
        buf[..n].copy_from_slice(&b2[i..i + n]);
        u64::from_le_bytes(buf)
    };

    [
        load(0)  & MASK51,
        (load(6)  >> 3)  & MASK51,
        (load(12) >> 6)  & MASK51,
        (load(19) >> 1)  & MASK51,
        (load(24) >> 12) & MASK51,
    ]
}

fn fe_to_bytes(h: &[u64; 5]) -> [u8; 32] {
    let h = fe_reduce_full(h);
    let v0 = h[0] | (h[1] << 51);
    let v1 = (h[1] >> 13) | (h[2] << 38);
    let v2 = (h[2] >> 26) | (h[3] << 25);
    let v3 = (h[3] >> 39) | (h[4] << 12);
    let mut out = [0u8; 32];
    out[0..8].copy_from_slice(&v0.to_le_bytes());
    out[8..16].copy_from_slice(&v1.to_le_bytes());
    out[16..24].copy_from_slice(&v2.to_le_bytes());
    out[24..32].copy_from_slice(&v3.to_le_bytes());
    out
}

fn fe_reduce_full(h: &[u64; 5]) -> [u64; 5] {
    // Reduce until h < p.
    let mut r = *h;
    // First pass: propagate carries.
    for _ in 0..2 {
        let c0 = r[0] >> 51; r[0] &= MASK51;
        let c1 = r[1].wrapping_add(c0) >> 51; r[1] = r[1].wrapping_add(c0) & MASK51;
        let c2 = r[2].wrapping_add(c1) >> 51; r[2] = r[2].wrapping_add(c1) & MASK51;
        let c3 = r[3].wrapping_add(c2) >> 51; r[3] = r[3].wrapping_add(c2) & MASK51;
        let c4 = r[4].wrapping_add(c3) >> 51; r[4] = r[4].wrapping_add(c3) & MASK51;
        r[0] = r[0].wrapping_add(c4 * 19);
    }
    // Subtract p if >= p.
    let mut s = r;
    let mut borrow = 0i64;
    for i in 0..5 {
        let d = s[i] as i64 - P[i] as i64 + borrow;
        borrow = d >> 63;
        s[i] = (d & MASK51 as i64) as u64;
    }
    // Select s if no borrow (s < p), else r.
    let mask = borrow as u64;  // 0xfff...f if borrow, 0 if not
    for i in 0..5 {
        r[i] = (r[i] & mask) | (s[i] & !mask);
    }
    r
}

fn fe_add(a: &[u64; 5], b: &[u64; 5]) -> [u64; 5] {
    let mut r = [0u64; 5];
    for i in 0..5 { r[i] = a[i] + b[i]; }
    r
}

fn fe_sub(a: &[u64; 5], b: &[u64; 5]) -> [u64; 5] {
    // Add 2p before subtracting to avoid underflow.
    const TWO_P: [u64; 5] = [
        (MASK51 + 1) * 2 - 38,  // 2*(2^51) - 2*19 at limb 0
        (MASK51 + 1) * 2 - 2,   // 2*(2^51) - 2 at limbs 1-4
        (MASK51 + 1) * 2 - 2,
        (MASK51 + 1) * 2 - 2,
        (MASK51 + 1) * 2 - 2,
    ];
    let mut r = [0u64; 5];
    for i in 0..5 { r[i] = a[i] + TWO_P[i] - b[i]; }
    r
}

fn fe_mul(a: &[u64; 5], b: &[u64; 5]) -> [u64; 5] {
    // Schoolbook with wrap-around reduction.
    // Cross terms at position >= 5 reduce by factor 19 (2^255 ≡ 19 mod p).
    let b19 = [b[0]*19, b[1]*19, b[2]*19, b[3]*19, b[4]*19];

    let mut t = [0u128; 5];
    t[0] += a[0] as u128 * b[0]   as u128;
    t[0] += a[1] as u128 * b19[4] as u128;
    t[0] += a[2] as u128 * b19[3] as u128;
    t[0] += a[3] as u128 * b19[2] as u128;
    t[0] += a[4] as u128 * b19[1] as u128;

    t[1] += a[0] as u128 * b[1]   as u128;
    t[1] += a[1] as u128 * b[0]   as u128;
    t[1] += a[2] as u128 * b19[4] as u128;
    t[1] += a[3] as u128 * b19[3] as u128;
    t[1] += a[4] as u128 * b19[2] as u128;

    t[2] += a[0] as u128 * b[2]   as u128;
    t[2] += a[1] as u128 * b[1]   as u128;
    t[2] += a[2] as u128 * b[0]   as u128;
    t[2] += a[3] as u128 * b19[4] as u128;
    t[2] += a[4] as u128 * b19[3] as u128;

    t[3] += a[0] as u128 * b[3]   as u128;
    t[3] += a[1] as u128 * b[2]   as u128;
    t[3] += a[2] as u128 * b[1]   as u128;
    t[3] += a[3] as u128 * b[0]   as u128;
    t[3] += a[4] as u128 * b19[4] as u128;

    t[4] += a[0] as u128 * b[4]   as u128;
    t[4] += a[1] as u128 * b[3]   as u128;
    t[4] += a[2] as u128 * b[2]   as u128;
    t[4] += a[3] as u128 * b[1]   as u128;
    t[4] += a[4] as u128 * b[0]   as u128;

    fe_carry128(&t)
}

fn fe_square(a: &[u64; 5]) -> [u64; 5] {
    fe_mul(a, a)
}

fn fe_sq_n(a: &[u64; 5], n: usize) -> [u64; 5] {
    let mut r = *a;
    for _ in 0..n { r = fe_square(&r); }
    r
}

fn fe_carry128(t: &[u128; 5]) -> [u64; 5] {
    let c0 = t[0] >> 51; let h0 = (t[0] & MASK51 as u128) as u64;
    let c1 = (t[1] + c0) >> 51; let h1 = ((t[1] + c0) & MASK51 as u128) as u64;
    let c2 = (t[2] + c1) >> 51; let h2 = ((t[2] + c1) & MASK51 as u128) as u64;
    let c3 = (t[3] + c2) >> 51; let h3 = ((t[3] + c2) & MASK51 as u128) as u64;
    let c4 = (t[4] + c3) >> 51; let h4 = ((t[4] + c3) & MASK51 as u128) as u64;
    let c5 = h0 + (c4 as u64) * 19;
    let h0 = c5 & MASK51;
    let h1 = h1 + (c5 >> 51);
    [h0, h1, h2, h3, h4]
}

fn fe_invert(z: &[u64; 5]) -> [u64; 5] {
    // z^(p-2) via addition chain giving z^(2^255 - 21).
    // Chain from curve25519-donna (Bernstein).
    let z2  = fe_square(z);
    let z4  = fe_square(&z2);
    let z8  = fe_square(&z4);
    let z9  = fe_mul(&z8, z);
    let z11 = fe_mul(&z9, &z2);
    let z22 = fe_square(&z11);
    let z2_5_0  = fe_mul(&z22, &z9);          // z^31  = z^(2^5-1)
    let z2_10_5 = fe_sq_n(&z2_5_0, 5);
    let z2_10_0 = fe_mul(&z2_10_5, &z2_5_0);  // z^(2^10-1)
    let z2_20_10= fe_sq_n(&z2_10_0, 10);
    let z2_20_0 = fe_mul(&z2_20_10, &z2_10_0);// z^(2^20-1)
    let z2_40_20= fe_sq_n(&z2_20_0, 20);
    let z2_40_0 = fe_mul(&z2_40_20, &z2_20_0);// z^(2^40-1)
    let z2_50_10= fe_sq_n(&z2_40_0, 10);
    let z2_50_0 = fe_mul(&z2_50_10, &z2_10_0);// z^(2^50-1)
    let z2_100_50=fe_sq_n(&z2_50_0, 50);
    let z2_100_0= fe_mul(&z2_100_50, &z2_50_0);// z^(2^100-1)
    let z2_200_100=fe_sq_n(&z2_100_0, 100);
    let z2_200_0= fe_mul(&z2_200_100, &z2_100_0);// z^(2^200-1)
    let z2_250_50=fe_sq_n(&z2_200_0, 50);
    let z2_250_0= fe_mul(&z2_250_50, &z2_50_0);// z^(2^250-1)
    // z^(2^255-32) = z2_250_0^(2^5)
    let z2_255_5= fe_sq_n(&z2_250_0, 5);
    // z^(2^255-32+11) = z^(2^255-21) = z^(p-2)
    fe_mul(&z2_255_5, &z11)
}

// Constant-time conditional swap.
fn cswap(swap: u64, a: &mut [u64; 5], b: &mut [u64; 5]) {
    let mask = 0u64.wrapping_sub(swap);  // 0 or 0xfff...f
    for i in 0..5 {
        let t = mask & (a[i] ^ b[i]);
        a[i] ^= t;
        b[i] ^= t;
    }
}

// ── Montgomery ladder ─────────────────────────────────────────────────────────

fn ladder(k: &[u8; 32], u: &[u64; 5]) -> [u64; 5] {
    let a24: [u64; 5] = [121665, 0, 0, 0, 0];  // (486662-2)/4

    let mut x1 = *u;
    let mut x2 = [1u64, 0, 0, 0, 0];
    let mut z2 = [0u64; 5];
    let mut x3 = *u;
    let mut z3 = [1u64, 0, 0, 0, 0];

    let mut swap: u64 = 0;

    // Process scalar bits from high to low.
    let mut t = 254i32;
    while t >= 0 {
        let ki = ((k[(t / 8) as usize] >> (t % 8)) & 1) as u64;
        swap ^= ki;
        cswap(swap, &mut x2, &mut x3);
        cswap(swap, &mut z2, &mut z3);
        swap = ki;

        // Montgomery double-and-add.
        let a  = fe_add(&x2, &z2);
        let aa = fe_square(&a);
        let b  = fe_sub(&x2, &z2);
        let bb = fe_square(&b);
        let e  = fe_sub(&aa, &bb);
        let c  = fe_add(&x3, &z3);
        let d  = fe_sub(&x3, &z3);
        let da = fe_mul(&d, &a);
        let cb = fe_mul(&c, &b);
        let x3n = fe_square(&fe_add(&da, &cb));
        let z3n = fe_mul(&x1, &fe_square(&fe_sub(&da, &cb)));
        let x2n = fe_mul(&aa, &bb);
        let z2n = fe_mul(&e, &fe_add(&aa, &fe_mul(&a24, &e)));

        x2 = x2n; z2 = z2n; x3 = x3n; z3 = z3n;
        t -= 1;
    }
    cswap(swap, &mut x2, &mut x3);
    cswap(swap, &mut z2, &mut z3);

    fe_mul(&x2, &fe_invert(&z2))
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Byte 257 — Rhokve.
/// Scalar multiplication: ungkael × ung point on Curve25519.
/// Returns the x-coordinate of the resulting point.
pub fn rhokve(ungkael: &[u8; 32], ung: &[u8; 32]) -> [u8; 32] {
    let mut k = *ungkael;
    // Clamp the scalar (RFC 7748 §5).
    k[0]  &= 248;
    k[31] &= 127;
    k[31] |= 64;

    let u = fe_from_bytes(ung);
    let r = ladder(&k, &u);
    fe_to_bytes(&r)
}

/// Rhokve applied to the base point (9) — derives public key from private.
pub fn rhokve_ung(ungkael: &[u8; 32]) -> [u8; 32] {
    let mut base = [0u8; 32];
    base[0] = 9;
    rhokve(ungkael, &base)
}