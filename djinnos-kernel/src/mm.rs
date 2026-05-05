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

const HEAP_SIZE: usize = 8 * 1024 * 1024;

#[repr(align(16))]
struct HeapMem([u8; HEAP_SIZE]);
static mut HEAP_MEM: HeapMem = HeapMem([0u8; HEAP_SIZE]);

// ── Global allocator instance ─────────────────────────────────────────────────

#[global_allocator]
pub static ALLOCATOR: Heap = Heap::uninit();

/// Call once in kernel_main before any heap use.
pub fn init() {
    unsafe {
        ALLOCATOR.init(
            HEAP_MEM.0.as_ptr() as usize,
            HEAP_SIZE,
        );
    }
}