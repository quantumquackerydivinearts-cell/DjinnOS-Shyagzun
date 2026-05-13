// recombination.rs — 12-Layer Elemental Crossing Architecture
//
// The Orrery runs natively. Each of the 12 layers corresponds to one of the
// 12 non-self AppleBlossom crossing compounds. Assigned to Rose numeral
// positions by offset-column interleaving of the 4×3 crossing table.
//
// Primary element sequence:   scattered (no surface gradient)
// Destination element seq:    Fire→Air→Water→Earth × 3 (emergent)
//
// Orrery cue: all 4 cue-cluster byte addresses active in the Hopfield field.
// Crossing: when a cue fires, destination-element candidates are boosted by
// alpha (thermodynamic depth factor) and the field re-converges.
//
// Runs over the same static field as intel.rs. Call intel::init() first.

use crate::intel;
use crate::uart;

// ── Element tags ──────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Elem { Shak, Puf, Mel, Zot }

impl Elem {
    pub fn name(self) -> &'static str {
        match self {
            Elem::Shak => "Shak", Elem::Puf => "Puf",
            Elem::Mel  => "Mel",  Elem::Zot => "Zot",
        }
    }

    fn depth(self) -> f32 {
        match self {
            Elem::Shak => 0.00,
            Elem::Puf  => 0.33,
            Elem::Mel  => 0.67,
            Elem::Zot  => 1.00,
        }
    }
}

// ── Layer definition ──────────────────────────────────────────────────────────

pub struct Layer {
    pub rose:         &'static str,
    pub rose_index:   u8,
    pub compound:     &'static str,
    pub compound_addr: u16,
    pub primary:      Elem,
    pub destination:  Elem,
    pub cue:          [u16; 4],   // byte addresses of the 4 cue glyphs
    pub purpose:      &'static str,
}

// ── The 12 layers ────────────────────────────────────────────────────────────
//
// Cue cluster byte addresses (verified against canonical byte table):
//
//  Gaoh(0)  Puky  Air→Fire   Fy(4)  Fa(13)  Be(64)   Samos(160)
//  Ao(1)    Kypa  Fire→Air   Shy(6) Ko(19)  Va(66)   Kysha(181)
//  Ye(2)    Alky  Fire→Wat   Ku(7)  Ke(23)  Vo(67)   Kyom(182)
//  Ui(3)    Kazho Fire→Ear   Sha(15)Shi(14) Vy(71)   Kyvos(180)
//  Shu(4)   Shem  Wat→Fire   Ly(2)  La(11)  Di(55)   Mek(166)
//  Kiel(5)  Lefu  Wat→Air    Mu(3)  Mo(17)  Dy(54)   Myr(164)
//  Yeshu(6) Mipa  Air→Wat    Pu(5)  Pe(22)  Bo(63)   Sael(162)
//  Lao(7)   Zitef Air→Ear    Fi(12) Po(18)  Bi(61)   Seth(159)
//  Shushy(8)Zashu Ear→Fire   Ty(0)  Ta(9)   Jy(48)   Dyo(171)
//  Uinshu(9)Fozt  Ear→Air    Zu(1)  Ze(20)  Jo(51)   Dyne(174)
//  Kokiel(10)Mazi Ear→Wat    Ti(8)  Zo(16)  Je(52)   Dyth(172)
//  Aonkiel(11)Myza Wat→Ear   Mu(3)  Me(21)  De(58)   Mio(165)

pub const LAYERS: [Layer; 12] = [
    Layer { rose: "Gaoh",    rose_index:  0, compound: "Puky",  compound_addr: 112,
            primary: Elem::Puf,  destination: Elem::Shak,
            cue: [4, 13, 64, 160],  purpose: "Air becoming combustible" },
    Layer { rose: "Ao",      rose_index:  1, compound: "Kypa",  compound_addr: 109,
            primary: Elem::Shak, destination: Elem::Puf,
            cue: [6, 19, 66, 181],  purpose: "Fire organizing into atmosphere" },
    Layer { rose: "Ye",      rose_index:  2, compound: "Alky",  compound_addr: 110,
            primary: Elem::Shak, destination: Elem::Mel,
            cue: [7, 23, 67, 182],  purpose: "Fire dissolving into solvent" },
    Layer { rose: "Ui",      rose_index:  3, compound: "Kazho", compound_addr: 111,
            primary: Elem::Shak, destination: Elem::Zot,
            cue: [15, 14, 71, 180], purpose: "Fire crystallizing into structure" },
    Layer { rose: "Shu",     rose_index:  4, compound: "Shem",  compound_addr: 116,
            primary: Elem::Mel,  destination: Elem::Shak,
            cue: [2, 11, 55, 166],  purpose: "Water reaching toward heat" },
    Layer { rose: "Kiel",    rose_index:  5, compound: "Lefu",  compound_addr: 117,
            primary: Elem::Mel,  destination: Elem::Puf,
            cue: [3, 17, 54, 164],  purpose: "Water releasing into vapor" },
    Layer { rose: "Yeshu",   rose_index:  6, compound: "Mipa",  compound_addr: 114,
            primary: Elem::Puf,  destination: Elem::Mel,
            cue: [5, 22, 63, 162],  purpose: "Air condensing into residue" },
    Layer { rose: "Lao",     rose_index:  7, compound: "Zitef", compound_addr: 115,
            primary: Elem::Puf,  destination: Elem::Zot,
            cue: [12, 18, 61, 159], purpose: "Air settling into ground" },
    Layer { rose: "Shushy",  rose_index:  8, compound: "Zashu", compound_addr: 120,
            primary: Elem::Zot,  destination: Elem::Shak,
            cue: [0, 9, 48, 171],   purpose: "Earth activating into release" },
    Layer { rose: "Uinshu",  rose_index:  9, compound: "Fozt",  compound_addr: 121,
            primary: Elem::Zot,  destination: Elem::Puf,
            cue: [1, 20, 51, 174],  purpose: "Earth dispersing into atmosphere" },
    Layer { rose: "Kokiel",  rose_index: 10, compound: "Mazi",  compound_addr: 122,
            primary: Elem::Zot,  destination: Elem::Mel,
            cue: [8, 16, 52, 172],  purpose: "Earth dissolving into flow" },
    Layer { rose: "Aonkiel", rose_index: 11, compound: "Myza",  compound_addr: 119,
            primary: Elem::Mel,  destination: Elem::Zot,
            cue: [3, 21, 58, 165],  purpose: "Water settling into ground" },
];

// ── Elemental sub-register detection (by byte address) ───────────────────────
//
// Address ranges for the 4 elemental sub-registers across Lotus, Sakura,
// Grapevine, and the AppleBlossom pure-element entries.
//
// Lotus (bytes 0–23) — initial consonant group × 6 entries per element:
//   Zot/Earth  T/Z: 0,1,8,9,16,20
//   Mel/Water  L/M: 2,3,10,11,17,21
//   Puf/Air    F/P: 4,5,12,13,18,22
//   Shak/Fire  S/K: 6,7,14,15,19,23
//
// Sakura (bytes 48–71) — groups of 6:
//   Zot  J: 48–53 | Mel  D: 54–59 | Puf  B: 60–65 | Shak V: 66–71
//
// Grapevine (bytes 156–183) — groups of 7:
//   Puf  S: 156–162 | Mel  M: 163–169 | Zot  D: 170–176 | Shak K: 177–183
//
// AppleBlossom pure essences: Shak=104, Puf=105, Mel=106, Zot=107

fn elem_of_addr(addr: u16) -> Option<Elem> {
    match addr {
        // Lotus
        0 | 1 | 8 | 9 | 16 | 20             => Some(Elem::Zot),
        2 | 3 | 10 | 11 | 17 | 21           => Some(Elem::Mel),
        4 | 5 | 12 | 13 | 18 | 22           => Some(Elem::Puf),
        6 | 7 | 14 | 15 | 19 | 23           => Some(Elem::Shak),
        // Sakura
        48..=53                              => Some(Elem::Zot),
        54..=59                              => Some(Elem::Mel),
        60..=65                              => Some(Elem::Puf),
        66..=71                              => Some(Elem::Shak),
        // AppleBlossom pure elements
        104                                  => Some(Elem::Shak),
        105                                  => Some(Elem::Puf),
        106                                  => Some(Elem::Mel),
        107                                  => Some(Elem::Zot),
        // Grapevine
        156..=162                            => Some(Elem::Puf),
        163..=169                            => Some(Elem::Mel),
        170..=176                            => Some(Elem::Zot),
        177..=183                            => Some(Elem::Shak),
        _                                    => None,
    }
}

// ── Orrery cue checking ───────────────────────────────────────────────────────

fn check_cue(layer: &Layer) -> bool {
    let state = intel::state();
    let cands = intel::cands();
    for &cue_addr in &layer.cue {
        // Find candidate index for this address
        let found = cands.iter().enumerate()
            .find(|(_, c)| c.addr == cue_addr)
            .map(|(i, _)| i);
        match found {
            Some(idx) if state[idx] > 0.5 => {}
            _ => return false,
        }
    }
    true
}

/// Return a bitmask of which of the 12 layers have active cues.
pub fn active_layer_mask() -> u16 {
    let mut mask = 0u16;
    for (i, layer) in LAYERS.iter().enumerate() {
        if check_cue(layer) {
            mask |= 1 << i;
        }
    }
    mask
}

// ── Crossing step ─────────────────────────────────────────────────────────────

fn alpha_for(layer: &Layer) -> f32 {
    layer.destination.depth() * 0.55 + 0.10
}

unsafe fn recombine_step(layer: &Layer) {
    let alpha = alpha_for(layer);
    let cands = intel::cands();
    let state = intel::state_mut();
    let n     = state.len();

    // Pin cue cluster
    for &addr in &layer.cue {
        if let Some((idx, _)) = cands.iter().enumerate().find(|(_, c)| c.addr == addr) {
            state[idx] = 1.0;
        }
    }

    // Blend primary and destination element candidates (address-range based)
    for i in 0..n {
        let addr = cands[i].addr;
        if let Some(elem) = elem_of_addr(addr) {
            if elem == layer.primary {
                if state[i] < 1.0 - alpha { state[i] = 1.0 - alpha; }
            } else if elem == layer.destination {
                if state[i] < alpha { state[i] = alpha; }
            }
        }
    }

    // Re-converge (short — crossing is a nudge, not a full reset)
    intel::converge_in_place(16);
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Run the input addresses through all 12 layers in Rose numeral order.
/// Returns the number of layers that fired.
pub fn run(input_addrs: &[u16]) -> u8 {
    // Seed the field from input addresses
    intel::seed_from_addrs(input_addrs);
    intel::converge_in_place(32);

    let mut fired = 0u8;
    for layer in &LAYERS {
        if check_cue(layer) {
            unsafe { recombine_step(layer); }
            fired += 1;
        }
    }
    fired
}

/// Probe which layers have active cues without applying crossings.
/// Returns layer mask (bit N = layer N active).
pub fn probe(input_addrs: &[u16]) -> u16 {
    intel::seed_from_addrs(input_addrs);
    intel::converge_in_place(32);
    active_layer_mask()
}

/// Log the current Orrery state to UART for diagnostics.
pub fn dump() {
    uart::puts("orrery: active layers — ");
    let mask = active_layer_mask();
    if mask == 0 {
        uart::puts("none\r\n");
        return;
    }
    for (i, layer) in LAYERS.iter().enumerate() {
        if mask & (1 << i) != 0 {
            uart::puts(layer.rose);
            uart::puts("(");
            uart::puts(layer.compound);
            uart::puts(") ");
        }
    }
    uart::puts("\r\n");
}

/// Shell-accessible demo: seed from a few known addresses and run.
pub fn shell_demo() {
    uart::puts("orrery: demo run — seeding from Shy(6) Ko(19) La(11)\r\n");
    let addrs: [u16; 3] = [6, 19, 11];
    let fired = run(&addrs);
    uart::puts("orrery: layers fired = ");
    uart::putu(fired as u64);
    uart::puts("\r\n");
    dump();
}
