// Locates the kernel ELF and:
//   1. Exports KERNEL_ELF env var so main.rs can embed it with include_bytes!
//   2. Extracts the address of kernel_uefi_entry from the ELF symbol table
//      and writes it to OUT_DIR/kernel_entry.rs as a Rust constant

use std::path::PathBuf;

fn main() {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let kernel = manifest.join(
        "../djinnos-kernel/target/x86_64-unknown-none/release/djinnos-kernel",
    );

    println!("cargo:rerun-if-changed={}", kernel.display());
    println!("cargo:rustc-env=KERNEL_ELF={}", kernel.display());

    let data = std::fs::read(&kernel)
        .expect("Cannot read kernel ELF — run: cd djinnos-kernel && cargo build --release");

    let addr = find_symbol(&data, "kernel_uefi_entry")
        .expect("kernel_uefi_entry symbol not found in kernel ELF");

    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("kernel_entry.rs");
    std::fs::write(
        &out,
        format!("pub const KERNEL_UEFI_ENTRY: u64 = 0x{:x};\n", addr),
    )
    .unwrap();
}

// ── Minimal ELF64 symbol-table scanner ────────────────────────────────────────

fn find_symbol(data: &[u8], name: &str) -> Option<u64> {
    if data.len() < 64 || &data[0..4] != b"\x7fELF" || data[4] != 2 {
        return None;
    }

    let e_shoff     = u64_le(data, 40) as usize;  // e_shoff (not e_phoff at 32)
    let e_shentsize = u16_le(data, 58) as usize;
    let e_shnum     = u16_le(data, 60) as usize;

    for i in 0..e_shnum {
        let sh = e_shoff + i * e_shentsize;
        if sh + e_shentsize > data.len() { break; }

        if u32_le(data, sh + 4) != 2 { continue; }  // SHT_SYMTAB only

        let sym_off  = u64_le(data, sh + 24) as usize;
        let sym_size = u64_le(data, sh + 32) as usize;
        let sym_ent  = u64_le(data, sh + 56) as usize;
        let str_idx  = u32_le(data, sh + 40) as usize;  // sh_link → .strtab

        let str_sh   = e_shoff + str_idx * e_shentsize;
        let str_off  = u64_le(data, str_sh + 24) as usize;

        if sym_ent == 0 { continue; }
        let n = sym_size / sym_ent;

        for j in 0..n {
            let sym = sym_off + j * sym_ent;
            if sym + 24 > data.len() { break; }

            let name_off = u32_le(data, sym) as usize;
            let value    = u64_le(data, sym + 8);
            if cstr_eq(&data[str_off..], name_off, name.as_bytes()) {
                return Some(value);
            }
        }
    }
    None
}

fn cstr_eq(strtab: &[u8], off: usize, target: &[u8]) -> bool {
    let s = &strtab[off..];
    s.starts_with(target) && s.get(target.len()) == Some(&0)
}

fn u16_le(b: &[u8], o: usize) -> u16 { u16::from_le_bytes(b[o..o+2].try_into().unwrap()) }
fn u32_le(b: &[u8], o: usize) -> u32 { u32::from_le_bytes(b[o..o+4].try_into().unwrap()) }
fn u64_le(b: &[u8], o: usize) -> u64 { u64::from_le_bytes(b[o..o+8].try_into().unwrap()) }
