mod types;
pub use types::{Context, Eigenstates, Process, ProcessId, ProcessState};

use core::sync::atomic::{AtomicUsize, Ordering};

core::arch::global_asm!(include_str!("switch.s"));

extern "C" {
    fn switch_context(from: *mut Context, to: *const Context);
}

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
            id:          ProcessId(9),   // Ta — Active being
            state:       ProcessState::Running,
            eigenstates: Eigenstates::ground(),
            context:     Context::zeroed(),
            stack_index: 0,
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
        from  // no other ready process — stay
    }
}