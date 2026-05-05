// Sublayer: phonological segmentation of a word into akinen/akinenwun.
//
// Uses greedy longest-prefix matching against the full symbol table.
// SYMBOLS is pre-sorted longest-first so the first match is the longest match.

include!(concat!(env!("OUT_DIR"), "/sorted_symbols.rs"));

pub const MAX_AKINEN: usize = 16;

#[derive(Clone, Copy)]
pub struct Akinen {
    pub addr: u16,
    pub name: &'static str,
}

impl Akinen {
    const UNKNOWN: Akinen = Akinen { addr: u16::MAX, name: "?" };
}

/// Break `word` (ASCII bytes) into a sequence of akinen.
/// Returns (slice, count) — count is the number of valid entries.
pub fn segment(word: &[u8]) -> ([Akinen; MAX_AKINEN], usize) {
    let mut out = [Akinen::UNKNOWN; MAX_AKINEN];
    let mut count = 0;
    let mut pos = 0;

    while pos < word.len() && count < MAX_AKINEN {
        if let Some((addr, name)) = longest_prefix(&word[pos..]) {
            out[count] = Akinen { addr, name };
            pos += name.len();
        } else {
            // Consume one byte as unknown
            out[count] = Akinen { addr: u16::MAX, name: "?" };
            pos += 1;
        }
        count += 1;
    }

    (out, count)
}

fn longest_prefix(input: &[u8]) -> Option<(u16, &'static str)> {
    // SYMBOLS is sorted longest-first, so the first match is the longest.
    for &(name, addr) in SYMBOLS {
        if input.starts_with(name.as_bytes()) {
            return Some((addr, name));
        }
    }
    None
}