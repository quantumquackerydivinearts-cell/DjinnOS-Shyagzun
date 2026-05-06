mod types;
pub use types::{Context, Eigenstates, Process, ProcessId, ProcessState, TrapFrame};

use core::sync::atomic::{AtomicUsize, Ordering};

#[cfg(target_arch = "riscv64")]
core::arch::global_asm!(include_str!("switch.s"));

#[cfg(target_arch = "x86_64")]
core::arch::global_asm!(include_str!("switch_x86.s"));

extern "C" {
    fn switch_context(from: *mut Context, to: *const Context);
}

// Defined in boot.s — srets into user mode from a TrapFrame (RISC-V only).
#[cfg(target_arch = "riscv64")]
unsafe extern "C" { fn user_resume(); }

// ── Static process table ──────────────────────────────────────────────────────

pub const MAX_PROCS: usize = 8;
const STACK_SIZE:    usize = 64 * 1024;   // 64 KiB per process

// Stacks live in BSS — zero-initialised, no heap needed.
static mut STACKS: [[u8; STACK_SIZE]; MAX_PROCS] = [[0u8; STACK_SIZE]; MAX_PROCS];

// Process table — kernel occupies slot 0.
static mut PROCS:   [Option<Process>; MAX_PROCS] = [const { None }; MAX_PROCS];
static     CURRENT: AtomicUsize = AtomicUsize::new(0);

// ── Boot: register the kernel itself as the first YeGaoh complex ─────────────
//
// The kernel's coordinate is 9 (Ta — Active being / presence).
// Its context is left zeroed; it never actually needs to be restored via
// switch_context because it never yields to itself.

pub fn init() {
    unsafe {
        PROCS[0] = Some(Process {
            id:          ProcessId(9),
            state:       ProcessState::Running,
            eigenstates: Eigenstates::ground(),
            context:     Context::zeroed(),
            stack_index: 0,
            is_user:     false,
            trapframe:   TrapFrame::zeroed(),
        });
    }
}

// ── Complexing operator — spawn ───────────────────────────────────────────────
//
// Creates a new YeGaoh complex at `coordinate` that will run `entry(arg)`.
// The coordinate IS the process identity; it should be a meaningful byte table
// address (e.g. 19 = Ko, "Experience / intuition" for an interactive shell).
//
// Returns None if the process table is full.

pub fn spawn(coordinate: u32, entry: fn(u64) -> !, arg: u64) -> Option<ProcessId> {
    unsafe {
        let slot = PROCS.iter().position(|p| p.is_none())?;

        // Stack grows downward — set sp to top of the stack region.
        let stack_top = STACKS[slot].as_ptr().add(STACK_SIZE) as u64;

        let mut ctx = Context::zeroed();
        ctx.ra = entry as usize as u64;  // resume here when first scheduled
        ctx.sp = stack_top;
        ctx.s0 = arg;                // pass arg through s0; entry reads it

        PROCS[slot] = Some(Process {
            id:          ProcessId(coordinate),
            state:       ProcessState::Ready,
            eigenstates: Eigenstates::ground(),
            context:     ctx,
            stack_index: slot,
            is_user:     false,
            trapframe:   TrapFrame::zeroed(),
        });

        Some(ProcessId(coordinate))
    }
}

// ── Dissolve — exit ───────────────────────────────────────────────────────────
//
// Marks the current complex as Dead and yields.  The scheduler will skip it.
// The stack and slot are reclaimed on the next spawn that needs them.

pub fn exit() -> ! {
    unsafe {
        let cur = CURRENT.load(Ordering::Relaxed);
        if let Some(p) = PROCS[cur].as_mut() {
            p.state = ProcessState::Dead;
        }
    }
    yield_now();
    loop {}  // unreachable — yield_now never returns to a Dead process
}

// ── Cooperative yield ─────────────────────────────────────────────────────────
//
// Surrenders the CPU to the next Ready process.  The outgoing process resumes
// here when it is next scheduled.

pub fn yield_now() {
    unsafe {
        let cur_idx = CURRENT.load(Ordering::Relaxed);

        // Round-robin: find the next Ready process
        let next_idx = next_ready(cur_idx);
        if next_idx == cur_idx {
            return;  // only one runnable process — keep going
        }

        CURRENT.store(next_idx, Ordering::Relaxed);

        // Transition states: outgoing → Ready so it can be rescheduled,
        // incoming → Running so it won't be double-scheduled.
        if let Some(ref mut p) = PROCS[cur_idx] {
            if p.state == ProcessState::Running { p.state = ProcessState::Ready; }
        }
        if let Some(ref mut p) = PROCS[next_idx] {
            p.state = ProcessState::Running;
        }

        if PROCS[cur_idx].is_some() && PROCS[next_idx].is_some() {
            let from = core::ptr::addr_of_mut!(
                PROCS[cur_idx].as_mut().unwrap().context);
            let to   = core::ptr::addr_of!(
                PROCS[next_idx].as_ref().unwrap().context);
            switch_context(from, to);
        }
    }
}

// ── Current process accessors ─────────────────────────────────────────────────

pub fn current_id() -> ProcessId {
    unsafe {
        let idx = CURRENT.load(Ordering::Relaxed);
        PROCS[idx].as_ref().map(|p| p.id).unwrap_or(ProcessId(0))
    }
}

/// Raw slot index of the currently running process (for trap handler use).
pub fn current_idx() -> usize {
    CURRENT.load(Ordering::Relaxed)
}

/// Mark the current process as Dead (called by sys_exit before yield_now).
/// Releases all IPC state (Rope bindings, Hook registrations, Fang contracts).
pub fn kill_current() {
    unsafe {
        let idx = CURRENT.load(Ordering::Relaxed);
        if let Some(p) = PROCS[idx].as_mut() {
            let pid = p.id.0;
            p.state = ProcessState::Dead;
            // Release IPC and file resources — before the slot is reclaimed.
            #[cfg(target_arch = "riscv64")]
            {
                crate::ipc::cleanup(pid);
                crate::vfs::close_all(pid);
            }
            let _ = pid;
        }
    }
}

/// Mark all user ELF processes as Dead so stdin and slots become free.
/// Called by the Ko shell `run` command before spawning a replacement.
pub fn kill_user_processes() {
    unsafe {
        for slot in PROCS.iter_mut() {
            if let Some(p) = slot {
                if p.is_user { p.state = ProcessState::Dead; }
            }
        }
    }
}

/// Mark the current process as Blocked (waiting for I/O).
/// Caller must call yield_now() immediately after.
pub fn block_current() {
    unsafe {
        let idx = CURRENT.load(Ordering::Relaxed);
        if let Some(p) = PROCS[idx].as_mut() {
            p.state = ProcessState::Blocked;
        }
    }
}

/// Wake the first Blocked process (stdin data is available).
/// Returns true if any process was unblocked.
pub fn unblock_stdin_waiters() -> bool {
    unsafe {
        for slot in PROCS.iter_mut() {
            if let Some(p) = slot {
                if p.state == ProcessState::Blocked {
                    p.state = ProcessState::Ready;
                    return true;
                }
            }
        }
        false
    }
}

/// Wake a specific process slot unconditionally (IPC / Circle wakeup).
pub fn unblock_slot(slot: usize) {
    unsafe {
        if slot < MAX_PROCS {
            if let Some(p) = PROCS[slot].as_mut() {
                if p.state == ProcessState::Blocked {
                    p.state = ProcessState::Ready;
                }
            }
        }
    }
}

/// Advance the grapevine eigenstate (e.g. on file open).
/// Called by the kernel on storage interactions.
pub fn advance_grapevine(addr: u32) {
    unsafe {
        let idx = CURRENT.load(Ordering::Relaxed);
        if let Some(p) = PROCS[idx].as_mut() {
            p.eigenstates.grapevine = addr;
        }
    }
}

/// Advance the cannabis eigenstate (e.g. on conscious output to screen).
pub fn advance_cannabis(addr: u32) {
    unsafe {
        let idx = CURRENT.load(Ordering::Relaxed);
        if let Some(p) = PROCS[idx].as_mut() {
            p.eigenstates.cannabis = addr;
        }
    }
}

// ── Internal ──────────────────────────────────────────────────────────────────

fn next_ready(from: usize) -> usize {
    unsafe {
        for i in 1..=MAX_PROCS {
            let idx = (from + i) % MAX_PROCS;
            if let Some(ref p) = PROCS[idx] {
                if p.state == ProcessState::Ready {
                    return idx;
                }
            }
        }
        from
    }
}

// ── ELF loader (RISC-V only — requires Sv39 and user_resume) ─────────────────

#[cfg(target_arch = "riscv64")]
const USTACK_TOP:   u64   = 0x7FFF_0000;
#[cfg(target_arch = "riscv64")]
const USTACK_PAGES: usize = 8;

/// Parse, map, and spawn a user-mode ELF process.
/// `coordinate` is the byte-table coordinate used as the process identity.
#[cfg(target_arch = "riscv64")]
pub fn spawn_elf(coordinate: u32, data: &[u8]) -> Option<ProcessId> {
    use crate::{elf, mm};

    let info = elf::parse(data)?;

    let root_pa = mm::new_user_page_table()?;
    let root    = root_pa as *mut [u64; 512];

    // Map each PT_LOAD segment.
    //
    // Segments from the same ELF may share a 4 KiB page (e.g. .text and
    // .rodata placed back-to-back by the linker).  map_page_or_update handles
    // that case by reusing the existing physical page and OR-ing the new flags
    // into the leaf PTE rather than allocating a second page.
    for seg in &info.segs[..info.seg_count] {
        let mut pte_flags = mm::PTE_U | mm::PTE_A | mm::PTE_D;
        if seg.flags & elf::PF_R != 0 { pte_flags |= mm::PTE_R; }
        if seg.flags & elf::PF_W != 0 { pte_flags |= mm::PTE_W; }
        if seg.flags & elf::PF_X != 0 { pte_flags |= mm::PTE_X; }

        let page_base = seg.vaddr & !(mm::PAGE_SIZE - 1);
        let page_end  = (seg.vaddr + seg.memsz + mm::PAGE_SIZE - 1) & !(mm::PAGE_SIZE - 1);
        let pages     = ((page_end - page_base) / mm::PAGE_SIZE) as usize;

        for p in 0..pages {
            let page_va = page_base + p as u64 * mm::PAGE_SIZE;

            // Get or create the physical page, merging flags if already mapped.
            let pa = unsafe { mm::map_page_or_update(root, page_va, pte_flags)? };

            // Copy only the bytes of this segment that fall within this page.
            let page_va_end  = page_va + mm::PAGE_SIZE;
            let seg_data_end = seg.vaddr + seg.filesz;
            let copy_va_lo   = seg.vaddr.max(page_va);
            let copy_va_hi   = seg_data_end.min(page_va_end);

            if copy_va_lo < copy_va_hi {
                let copy_len = (copy_va_hi - copy_va_lo) as usize;
                let page_off = (copy_va_lo - page_va)    as usize;
                let file_off = seg.offset as usize
                             + (copy_va_lo - seg.vaddr)  as usize;
                if file_off + copy_len <= data.len() {
                    unsafe {
                        core::ptr::copy_nonoverlapping(
                            data.as_ptr().add(file_off),
                            (pa + page_off as u64) as *mut u8,
                            copy_len,
                        );
                    }
                }
            }
        }
    }

    // Map user stack.
    for p in 0..USTACK_PAGES {
        let pa = mm::page_alloc()?;
        let va = USTACK_TOP - (USTACK_PAGES - p) as u64 * mm::PAGE_SIZE;
        let flags = mm::PTE_R | mm::PTE_W | mm::PTE_U | mm::PTE_A | mm::PTE_D;
        unsafe { mm::map_page(root, va, pa, flags); }
    }

    unsafe {
        // Prefer empty slots; fall back to Dead slots so re-running after exit works.
        let slot = PROCS.iter().position(|p| p.is_none())
            .or_else(|| PROCS.iter().position(|p|
                matches!(p, Some(ref q) if q.state == ProcessState::Dead)
            ))?;
        PROCS[slot] = None; // clear any Dead occupant
        let kstack_top = STACKS[slot].as_ptr().add(STACK_SIZE) as u64;
        let satp       = mm::make_satp(root_pa);

        let mut tf      = TrapFrame::zeroed();
        tf.sepc         = info.entry;
        tf.sstatus      = 0;              // SPP=0 → sret to U-mode
        tf.sp           = USTACK_TOP;
        tf.satp         = satp;
        tf.ksp          = kstack_top;

        // Kernel context: switch_context restores ra=user_resume, s0=trapframe ptr.
        let mut ctx = Context::zeroed();
        ctx.ra = user_resume as *const () as usize as u64;
        ctx.sp = kstack_top;
        // s0 is patched below once the Process is placed in PROCS.

        PROCS[slot] = Some(Process {
            id:          ProcessId(coordinate),
            state:       ProcessState::Ready,
            eigenstates: Eigenstates::ground(),
            context:     ctx,
            stack_index: slot,
            is_user:     true,
            trapframe:   tf,
        });

        // Patch s0 to point at the embedded trapframe.
        let tf_ptr = core::ptr::addr_of!(PROCS[slot].as_ref().unwrap().trapframe) as u64;
        PROCS[slot].as_mut().unwrap().context.s0 = tf_ptr;

        Some(ProcessId(coordinate))
    }
}