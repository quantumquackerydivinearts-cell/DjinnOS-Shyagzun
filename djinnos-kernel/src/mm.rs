// DjinnOS memory manager — Phase 1: linked-list heap allocator.
//
// Registers as the global allocator so the alloc crate works:
// Vec, Box, String, BTreeMap, etc. are all available after init().
//
// Design:
//   Free blocks form a singly-linked list sorted by address.
//   Each block carries a 16-byte header (size + next pointer).
//   alloc()   — first-fit; splits oversized blocks.
//   dealloc() — inserts in address order; coalesces with next block.
//
// Alignment contract:
//   The header is 16 bytes (2 × usize on RV64).  Returned pointers
//   are always block_start + 16, so effective guaranteed alignment
//   is 16 bytes — sufficient for all standard kernel data types.
//   Requests with align > 16 return null (OOM path).
//
// Phase 2 (virtual memory sprint): replace static HEAP with physical
// page allocation over the full RAM map.

use core::alloc::{GlobalAlloc, Layout};
use core::cell::UnsafeCell;
use core::ptr;

// ── Block header ──────────────────────────────────────────────────────────────

const HDR: usize = core::mem::size_of::<Block>();   // 16 bytes on RV64

#[repr(C)]
struct Block {
    size: usize,       // total bytes in this block, header included
    next: *mut Block,
}

// ── Allocator ─────────────────────────────────────────────────────────────────

pub struct Heap(UnsafeCell<*mut Block>);

// Single-core cooperative kernel — no concurrent allocator access.
unsafe impl Sync for Heap {}

impl Heap {
    pub const fn uninit() -> Self {
        Heap(UnsafeCell::new(ptr::null_mut()))
    }

    /// Initialise the heap over the region [start, start+bytes).
    /// Must be called exactly once before any allocation.
    pub unsafe fn init(&self, start: usize, bytes: usize) {
        assert!(bytes > HDR, "heap too small");
        let b = start as *mut Block;
        (*b).size = bytes;
        (*b).next = ptr::null_mut();
        *self.0.get() = b;
    }

    /// Returns (free_bytes, free_block_count) — useful for `info` command.
    pub fn stats(&self) -> (usize, usize) {
        let mut free   = 0usize;
        let mut blocks = 0usize;
        let mut cur = unsafe { *self.0.get() };
        while !cur.is_null() {
            free   += unsafe { (*cur).size } - HDR;
            blocks += 1;
            cur     = unsafe { (*cur).next };
        }
        (free, blocks)
    }
}

unsafe impl GlobalAlloc for Heap {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        // Requests exceeding 16-byte alignment are unsupported in phase 1.
        if layout.align() > HDR { return ptr::null_mut(); }

        // Round total block size up to 8-byte multiple.
        let total = (HDR + layout.size() + 7) & !7;

        let mut prev: *mut *mut Block = self.0.get();
        let mut cur  = *prev;

        while !cur.is_null() {
            let sz = (*cur).size;
            if sz >= total {
                // Split the block if the remainder would hold another useful chunk.
                if sz >= total + HDR + 8 {
                    let rest = (cur as usize + total) as *mut Block;
                    (*rest).size = sz - total;
                    (*rest).next = (*cur).next;
                    *prev = rest;
                    (*cur).size = total;
                } else {
                    // Take the whole block.
                    *prev = (*cur).next;
                }
                (*cur).next = ptr::null_mut();
                return (cur as usize + HDR) as *mut u8;
            }
            prev = &mut (*cur).next;
            cur  = *prev;
        }

        ptr::null_mut()   // out of memory
    }

    unsafe fn dealloc(&self, ptr: *mut u8, _layout: Layout) {
        let blk = (ptr as usize - HDR) as *mut Block;

        // Insert into free list in address order (prerequisite for coalescing).
        let mut prev: *mut *mut Block = self.0.get();
        let mut cur  = *prev;

        while !cur.is_null() && (cur as usize) < (blk as usize) {
            prev = &mut (*cur).next;
            cur  = *prev;
        }

        (*blk).next = cur;
        *prev = blk;

        // Coalesce with the immediately following block if adjacent.
        if !(*blk).next.is_null() {
            let next = (*blk).next;
            if blk as usize + (*blk).size == next as usize {
                (*blk).size += (*next).size;
                (*blk).next  = (*next).next;
            }
        }
    }
}

// ── Static heap backing store (Phase 1) ──────────────────────────────────────
// 8 MiB lives in BSS — zero-cost until touched.
// Replace with physical page allocation once virtual memory lands.

pub const HEAP_SIZE: usize = 8 * 1024 * 1024;

#[repr(align(16))]
struct HeapMem([u8; HEAP_SIZE]);
static mut HEAP_MEM: HeapMem = HeapMem([0u8; HEAP_SIZE]);

// ── Global allocator instance ─────────────────────────────────────────────────

#[global_allocator]
pub static ALLOCATOR: Heap = Heap::uninit();

/// Physical base address of the static heap region.
#[allow(non_snake_case)]
pub unsafe fn HEAP_MEM_BASE() -> u64 {
    HEAP_MEM.0.as_ptr() as u64
}

/// Call once in kernel_main before any heap use.
pub fn init() {
    unsafe {
        ALLOCATOR.init(
            HEAP_MEM.0.as_ptr() as usize,
            HEAP_SIZE,
        );
    }
}

// ── Sv39 kernel identity map (RISC-V only) ────────────────────────────────────
//
// Two 1 GiB gigapages cover everything the kernel touches:
//
//   VA 0x0000_0000 – 0x3FFF_FFFF  →  PA 0x0000_0000 – 0x3FFF_FFFF
//     UART (0x1000_0000), VirtIO MMIO (0x1000_1000+),
//     CLINT (0x200_0000), PLIC (0x0C00_0000), PCIe ECAM (0x3000_0000)
//
//   VA 0x8000_0000 – 0xBFFF_FFFF  →  PA 0x8000_0000 – 0xBFFF_FFFF
//     RAM: kernel text/data/BSS, heap, stack, framebuffer
//
// Gigapage validity: PPN lower 18 bits must be zero.
//   0x0000_0000 >> 12 = 0x00000 — lower 18 bits = 0 ✓
//   0x8000_0000 >> 12 = 0x80000 — lower 18 bits = 0 ✓
//
// x86_64 equivalent: two 1 GiB PML4→PDPT leaf entries.

#[cfg(target_arch = "riscv64")]
pub const PTE_V: u64 = 1 << 0;
#[cfg(target_arch = "riscv64")]
pub const PTE_R: u64 = 1 << 1;
#[cfg(target_arch = "riscv64")]
pub const PTE_W: u64 = 1 << 2;
#[cfg(target_arch = "riscv64")]
pub const PTE_X: u64 = 1 << 3;
#[cfg(target_arch = "riscv64")]
pub const PTE_U: u64 = 1 << 4;
#[cfg(target_arch = "riscv64")]
           const PTE_G: u64 = 1 << 5;
#[cfg(target_arch = "riscv64")]
pub const PTE_A: u64 = 1 << 6;
#[cfg(target_arch = "riscv64")]
pub const PTE_D: u64 = 1 << 7;

#[cfg(target_arch = "riscv64")]
const KERNEL_PTE_FLAGS: u64 = PTE_V | PTE_R | PTE_W | PTE_X | PTE_G | PTE_A | PTE_D;

#[cfg(target_arch = "riscv64")]
#[repr(C, align(4096))]
struct PageTable([u64; 512]);

#[cfg(target_arch = "riscv64")]
static mut KERNEL_PGT: PageTable = PageTable([0u64; 512]);

/// Build the kernel identity map and activate paging.
/// RISC-V: enables Sv39.  x86_64: no-op (boot_x86.s handled it).
pub fn setup_vm() {
    #[cfg(target_arch = "x86_64")]
    { return; }

    #[cfg(target_arch = "riscv64")]
    unsafe {
        let pgt = &mut KERNEL_PGT;

        // VPN[2] index = VA[38:30].
        // For 0x0000_0000: index 0.  For 0x8000_0000: index 2.
        let mmio_ppn = 0x0000_0000u64 >> 12;   // = 0
        let ram_ppn  = 0x8000_0000u64 >> 12;   // = 0x80000

        pgt.0[0] = (mmio_ppn << 10) | KERNEL_PTE_FLAGS;
        pgt.0[2] = (ram_ppn  << 10) | KERNEL_PTE_FLAGS;

        let root_pa = pgt.0.as_ptr() as u64;
        crate::arch::enable_paging(root_pa);
    }
}

/// Physical page allocator — returns 4 KiB-aligned physical pages.
/// Phase 1: simple bump allocator from a fixed region above the heap.
/// Phase 2 (virtual memory sprint 2): replace with bitmap over full RAM map.

static PAGE_BUMP: core::sync::atomic::AtomicU64 =
    core::sync::atomic::AtomicU64::new(0);
static PAGE_LIMIT: core::sync::atomic::AtomicU64 =
    core::sync::atomic::AtomicU64::new(0);

pub const PAGE_SIZE: u64 = 4096;

/// Initialise the physical page allocator.
/// `start` and `end` are physical addresses of the free region.
pub fn page_alloc_init(start: u64, end: u64) {
    let aligned = (start + PAGE_SIZE - 1) & !(PAGE_SIZE - 1);
    PAGE_BUMP .store(aligned, core::sync::atomic::Ordering::Relaxed);
    PAGE_LIMIT.store(end,     core::sync::atomic::Ordering::Relaxed);
}

/// Allocate one physical page (4 KiB).  Returns None if exhausted.
pub fn page_alloc() -> Option<u64> {
    use core::sync::atomic::Ordering;
    loop {
        let cur  = PAGE_BUMP.load(Ordering::Relaxed);
        let next = cur + PAGE_SIZE;
        if next > PAGE_LIMIT.load(Ordering::Relaxed) { return None; }
        if PAGE_BUMP.compare_exchange(cur, next, Ordering::SeqCst, Ordering::Relaxed).is_ok() {
            unsafe { core::ptr::write_bytes(cur as *mut u8, 0, PAGE_SIZE as usize); }
            return Some(cur);
        }
    }
}

// ── User-space page-table primitives (RISC-V / Sv39 only) ────────────────────

#[cfg(target_arch = "riscv64")]
pub fn pt_alloc() -> Option<*mut [u64; 512]> {
    let pa = page_alloc()?;
    Some(pa as *mut [u64; 512])
}

#[cfg(target_arch = "riscv64")]
/// Walk or build the L2→L1→L0 path for `va`, returning a mutable ref to the
/// L0 leaf slot.  Allocates L1/L0 nodes as needed (panics on OOM).
/// Panics if `va` falls inside a kernel gigapage.
unsafe fn leaf_pte(root: *mut [u64; 512], va: u64) -> &'static mut u64 {
    let vpn2 = ((va >> 30) & 0x1FF) as usize;
    let vpn1 = ((va >> 21) & 0x1FF) as usize;
    let vpn0 = ((va >> 12) & 0x1FF) as usize;

    let l2e = &mut (*root)[vpn2];
    if *l2e & PTE_V != 0 && (*l2e & (PTE_R | PTE_W | PTE_X)) != 0 {
        panic!("map_page: VA conflicts with kernel gigapage");
    }
    let l1: *mut [u64; 512] = if *l2e & PTE_V != 0 {
        ((*l2e >> 10) << 12) as *mut [u64; 512]
    } else {
        let pt = pt_alloc().expect("OOM: L1 page table");
        *l2e = ((pt as u64 >> 12) << 10) | PTE_V;
        pt
    };

    let l1e = &mut (*l1)[vpn1];
    let l0: *mut [u64; 512] = if *l1e & PTE_V != 0 {
        ((*l1e >> 10) << 12) as *mut [u64; 512]
    } else {
        let pt = pt_alloc().expect("OOM: L0 page table");
        *l1e = ((pt as u64 >> 12) << 10) | PTE_V;
        pt
    };

    &mut (*l0)[vpn0]
}

#[cfg(target_arch = "riscv64")]
pub unsafe fn map_page(root: *mut [u64; 512], va: u64, pa: u64, flags: u64) {
    *leaf_pte(root, va) = ((pa >> 12) << 10) | flags | PTE_V;
}

#[cfg(target_arch = "riscv64")]
/// Map `va` if not yet mapped (allocating a new page), or OR `flags` into the
/// existing PTE if the VA is already mapped.  Returns the physical address of
/// the (possibly existing) page, or None on OOM.
///
/// This handles ELF segments that share a 4 KiB page (e.g. .text and .rodata
/// placed adjacently by the linker): the first segment creates the mapping and
/// the second segment just adds its flags to the same leaf PTE.
pub unsafe fn map_page_or_update(
    root:  *mut [u64; 512],
    va:    u64,
    flags: u64,
) -> Option<u64> {
    let pte = leaf_pte(root, va);
    if *pte & PTE_V != 0 {
        // Page already mapped — merge new flags in, keep existing PA.
        *pte |= flags;
        Some((*pte >> 10) << 12)
    } else {
        let pa = page_alloc()?;
        *pte = ((pa >> 12) << 10) | flags | PTE_V;
        Some(pa)
    }
}

#[cfg(target_arch = "riscv64")]
/// Allocate a new Sv39 root page table with kernel gigapage entries pre-copied.
/// Both MMIO (VPN2=0) and RAM (VPN2=2) gigapages are included so the kernel
/// trap handler can access UART and code while running with this page table.
/// Returns the physical (= identity-mapped virtual) address of the root.
pub fn new_user_page_table() -> Option<u64> {
    let root = pt_alloc()?;
    unsafe {
        (*root)[0] = KERNEL_PGT.0[0];   // MMIO gigapage  (no PTE_U → U-mode can't access)
        (*root)[2] = KERNEL_PGT.0[2];   // RAM  gigapage  (no PTE_U → U-mode can't access)
    }
    Some(root as u64)
}

#[cfg(target_arch = "riscv64")]
/// Build the satp value for an Sv39 root page table at physical address `pa`.
pub fn make_satp(pa: u64) -> u64 {
    (8u64 << 60) | (pa >> 12)
}