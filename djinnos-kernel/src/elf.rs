// ELF64 parser — only the subset needed for loading user processes.
// Parses PT_LOAD segments and the entry point; ignores everything else.

pub const PT_LOAD: u32 = 1;
pub const PF_X:    u32 = 1;
pub const PF_W:    u32 = 2;
pub const PF_R:    u32 = 4;

#[repr(C)]
struct Elf64Ehdr {
    e_ident:     [u8; 16],
    e_type:      u16,
    e_machine:   u16,
    e_version:   u32,
    e_entry:     u64,
    e_phoff:     u64,
    e_shoff:     u64,
    e_flags:     u32,
    e_ehsize:    u16,
    e_phentsize: u16,
    e_phnum:     u16,
    e_shentsize: u16,
    e_shnum:     u16,
    e_shstrndx:  u16,
}

#[repr(C)]
struct Elf64Phdr {
    p_type:   u32,
    p_flags:  u32,
    p_offset: u64,
    p_vaddr:  u64,
    p_paddr:  u64,
    p_filesz: u64,
    p_memsz:  u64,
    p_align:  u64,
}

#[derive(Clone, Copy)]
pub struct LoadSeg {
    pub vaddr:  u64,
    pub filesz: u64,
    pub memsz:  u64,
    pub offset: u64,
    pub flags:  u32,
}

pub const MAX_SEGS: usize = 8;

pub struct ElfInfo {
    pub entry:     u64,
    pub segs:      [LoadSeg; MAX_SEGS],
    pub seg_count: usize,
}

pub fn parse(data: &[u8]) -> Option<ElfInfo> {
    if data.len() < core::mem::size_of::<Elf64Ehdr>() { return None; }

    let ehdr = unsafe { &*(data.as_ptr() as *const Elf64Ehdr) };

    if &ehdr.e_ident[0..4] != b"\x7fELF" { return None; }
    if ehdr.e_ident[4] != 2              { return None; }   // ELF64
    if ehdr.e_machine != 0xF3 && ehdr.e_machine != 0x3E { return None; } // RISC-V | x86-64

    let phoff = ehdr.e_phoff as usize;
    let phnum = ehdr.e_phnum as usize;
    let phsz  = ehdr.e_phentsize as usize;

    let mut info = ElfInfo {
        entry:     ehdr.e_entry,
        segs:      [LoadSeg { vaddr: 0, filesz: 0, memsz: 0, offset: 0, flags: 0 }; MAX_SEGS],
        seg_count: 0,
    };

    for i in 0..phnum {
        let off = phoff + i * phsz;
        if off + core::mem::size_of::<Elf64Phdr>() > data.len() { break; }
        let ph = unsafe { &*(data[off..].as_ptr() as *const Elf64Phdr) };
        if ph.p_type != PT_LOAD { continue; }
        if info.seg_count >= MAX_SEGS { break; }
        info.segs[info.seg_count] = LoadSeg {
            vaddr:  ph.p_vaddr,
            filesz: ph.p_filesz,
            memsz:  ph.p_memsz,
            offset: ph.p_offset,
            flags:  ph.p_flags,
        };
        info.seg_count += 1;
    }

    if info.seg_count == 0 { None } else { Some(info) }
}