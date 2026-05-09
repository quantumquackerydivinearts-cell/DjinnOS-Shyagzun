// Tongue and coordinate-space classification.
//
// There are 37 Tongues (Lotus through Circle).  The byte table also contains
// non-Tongue coordinate groups — MetaTopology, MetaPhysics, Physics, Chemistry,
// and the structural reservation blocks (124–127 YeGaoh headers, 214–227 group
// headers).  These are NOT tongues; they are architectural coordinate space.

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Space {
    Tongue(u8, &'static str), // tongue number (1-37), name
    Reserved(&'static str),   // structural reservation or non-tongue group
}

pub fn classify(addr: u16) -> Space {
    match addr {
        0..=23   => Space::Tongue(1,  "Lotus"),
        24..=47  => Space::Tongue(2,  "Rose"),
        48..=71  => Space::Tongue(3,  "Sakura"),
        72..=97  => Space::Tongue(4,  "Daisy"),
        98..=123 => Space::Tongue(5,  "AppleBlossom"),
        124..=127 => Space::Reserved("YeGaoh-headers"),
        128..=155 => Space::Tongue(6,  "Aster"),
        156..=183 => Space::Tongue(7,  "Grapevine"),
        184..=213 => Space::Tongue(8,  "Cannabis"),
        214..=227 => Space::Reserved("group-headers"),
        228..=242 => Space::Reserved("MetaTopology"),
        243..=248 => Space::Reserved("MetaPhysics"),
        249..=252 => Space::Reserved("Physics"),
        253..=255 => Space::Reserved("Chemistry"),
        256..=285 => Space::Tongue(9,  "Dragon"),
        286..=315 => Space::Tongue(10, "Virus"),
        316..=345 => Space::Tongue(11, "Bacteria"),
        346..=377 => Space::Tongue(12, "Excavata"),
        378..=409 => Space::Tongue(13, "Archaeplastida"),
        410..=443 => Space::Tongue(14, "Myxozoa"),
        444..=477 => Space::Tongue(15, "Archaea"),
        478..=511 => Space::Tongue(16, "Protist"),
        512..=545 => Space::Tongue(17, "Immune"),
        546..=581 => Space::Tongue(18, "Neural"),
        582..=617 => Space::Tongue(19, "Serpent"),
        618..=655 => Space::Tongue(20, "Beast"),
        656..=693 => Space::Tongue(21, "Cherub"),
        694..=731 => Space::Tongue(22, "Chimera"),
        732..=769 => Space::Tongue(23, "Faerie"),
        770..=809 => Space::Tongue(24, "Djinn"),
        810..=849 => Space::Tongue(25, "Fold"),
        850..=889 => Space::Tongue(26, "Topology"),
        890..=929 => Space::Tongue(27, "Phase"),
        930..=969 => Space::Tongue(28, "Gradient"),
        970..=1009 => Space::Tongue(29, "Curvature"),
        1010..=1051 => Space::Tongue(30, "Prion"),
        1052..=1093 => Space::Tongue(31, "Blood"),
        1094..=1137 => Space::Tongue(32, "Moon"),
        1138..=1181 => Space::Tongue(33, "Koi"),
        1182..=1225 => Space::Tongue(34, "Rope"),
        1226..=1269 => Space::Tongue(35, "Hook"),
        1270..=1313 => Space::Tongue(36, "Fang"),
        1314..=1357 => Space::Tongue(37, "Circle"),
        _ => Space::Reserved("unknown"),
    }
}