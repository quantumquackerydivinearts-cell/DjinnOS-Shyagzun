// Byte table types.
// An Address is a coordinate in the Shygazun space — not an array index.
// Gaps between cluster ends and binary boundaries are the prime factorization
// pattern visible in the geometry; they are not empty slots.

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub struct Address(pub u32);

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
#[repr(u8)]
#[allow(dead_code)]
pub enum Tongue {
    Lotus          =  1,
    Rose           =  2,
    Sakura         =  3,
    Daisy          =  4,
    AppleBlossom   =  5,
    Aster          =  6,
    Grapevine      =  7,
    Cannabis       =  8,
    Dragon         =  9,
    Virus          = 10,
    Bacteria       = 11,
    Excavata       = 12,
    Archaeplastida = 13,
    Myxozoa        = 14,
    Archea         = 15,
    Protist        = 16,
    Immune         = 17,
    Neural         = 18,
    Serpent        = 19,
    Beast          = 20,
    Cherub         = 21,
    Chimera        = 22,
    Faerie         = 23,
    Djinn          = 24,
    Moon           = 32,
    Koi            = 33,
    Rope           = 34,
    Hook           = 35,
    Fang           = 36,
    Circle         = 37,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum EntryKind {
    Symbol,        // Symbol-bearing candidate entry
    Reserved,      // Cluster / directory header — contents not yet conscious
    MetaTopology,  // Structural primitive: language philosophy, grammar, pronouns
    MetaPhysics,   // Structural primitive: physics correspondences
    Physics,       // Structural primitive: physical law
    Chemistry,     // Structural primitive: chemical law
}

pub struct ByteEntry {
    pub address: Address,
    pub kind:    EntryKind,
    pub tongue:  Option<Tongue>,
    pub glyph:   Option<&'static str>,
    pub meaning: &'static str,
}

impl ByteEntry {
    pub const fn symbol(
        addr:    u32,
        tongue:  Tongue,
        glyph:   &'static str,
        meaning: &'static str,
    ) -> Self {
        Self {
            address: Address(addr),
            kind:    EntryKind::Symbol,
            tongue:  Some(tongue),
            glyph:   Some(glyph),
            meaning,
        }
    }

    pub const fn reserved(
        addr:    u32,
        glyph:   &'static str,
        meaning: &'static str,
    ) -> Self {
        Self {
            address: Address(addr),
            kind:    EntryKind::Reserved,
            tongue:  None,
            glyph:   Some(glyph),
            meaning,
        }
    }

    pub const fn meta(
        addr:    u32,
        kind:    EntryKind,
        meaning: &'static str,
    ) -> Self {
        Self {
            address: Address(addr),
            kind,
            tongue:  None,
            glyph:   None,
            meaning,
        }
    }
}