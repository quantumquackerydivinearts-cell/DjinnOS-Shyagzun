mod types;
mod table;

pub use types::{Address, ByteEntry, EntryKind, Tongue};
pub use table::BYTE_TABLE;

/// Look up an entry by byte address. O(log n) binary search over rodata.
pub fn lookup(addr: u32) -> Option<&'static ByteEntry> {
    let target = Address(addr);
    BYTE_TABLE
        .binary_search_by_key(&target, |e| e.address)
        .ok()
        .map(|i| &BYTE_TABLE[i])
}

/// Number of symbol-bearing entries (candidates).
pub fn symbol_count() -> usize {
    BYTE_TABLE.iter().filter(|e| e.kind == EntryKind::Symbol).count()
}

/// Number of entries for a given tongue.
pub fn tongue_count(tongue: Tongue) -> usize {
    BYTE_TABLE
        .iter()
        .filter(|e| e.tongue == Some(tongue))
        .count()
}