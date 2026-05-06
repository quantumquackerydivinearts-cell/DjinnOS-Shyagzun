// Shygazun IPC — inter-process communication primitives.
//
// Five relational modes, one backing module:
//
//   Koi  (1138) — create a balanced-exchange channel (symmetric ring)
//   Rope (1182) — bind ownership of a resource token to current process
//   Hook (1226) — register a user-mode IRQ handler by mechanism
//   Fang (1270) — declare a constitutive resource contract
//   Circle(1314)— broadcast an event; all waiters unblock with the payload
//
//   Ro   (83)   — open a channel by ID → returns IPC fd (IPC_FD_BASE + id)
//   Nz   (89)   — send one word on a channel fd
//
// fd scheme (matches trap.rs dispatch):
//   0–2    stdin / stdout / stderr
//   16–31  IPC channels (fd − IPC_FD_BASE = channel_id)
//
// All state is static — no heap allocation required.

use core::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use crate::process;

// ── Constants ─────────────────────────────────────────────────────────────────

pub const IPC_FD_BASE:    u64  = 16;
pub const MAX_CHANNELS:   usize = 16;
pub const MAX_HOOKS:      usize = 32;
pub const MAX_CONTRACTS:  usize = 16;
pub const MAX_EVENTS:     usize = 32;
pub const MAX_EVENT_WAIT: usize = 8;
const     CHAN_BUF:        usize = 32;   // words per channel ring
const     MAX_PROCS:       usize = crate::process::MAX_PROCS;

// ── Channel ring (Koi) ────────────────────────────────────────────────────────

struct Channel {
    buf:   [u64; CHAN_BUF],
    head:  usize,
    count: usize,
    used:  bool,
}

impl Channel {
    const fn empty() -> Self {
        Self { buf: [0u64; CHAN_BUF], head: 0, count: 0, used: false }
    }

    fn push(&mut self, word: u64) -> bool {
        if self.count == CHAN_BUF { return false; }
        let tail = (self.head + self.count) % CHAN_BUF;
        self.buf[tail] = word;
        self.count += 1;
        true
    }

    fn pop(&mut self) -> Option<u64> {
        if self.count == 0 { return None; }
        let word = self.buf[self.head];
        self.head = (self.head + 1) % CHAN_BUF;
        self.count -= 1;
        Some(word)
    }
}

static mut CHANNELS: [Channel; MAX_CHANNELS] = [const { Channel::empty() }; MAX_CHANNELS];

// Parallel-to-PROCS tables for per-process IPC wait state.
static mut WAIT_CHANNEL: [i32; MAX_PROCS] = [-1i32; MAX_PROCS]; // -1 = not waiting
static mut WAIT_EVENT:   [u64; MAX_PROCS] = [0u64;  MAX_PROCS]; // 0 = not waiting

// ── Koi — create a balanced-exchange channel ──────────────────────────────────

/// Allocate a new channel.  Returns the channel ID (16-based fd = id + IPC_FD_BASE).
pub fn create_channel() -> Option<u64> {
    unsafe {
        for (i, ch) in CHANNELS.iter_mut().enumerate() {
            if !ch.used {
                ch.used  = true;
                ch.head  = 0;
                ch.count = 0;
                return Some(i as u64);
            }
        }
        None
    }
}

/// Release a channel.
pub fn close_channel(id: usize) {
    unsafe {
        if id < MAX_CHANNELS {
            CHANNELS[id].used = false;
        }
    }
}

// ── Ro — open channel → fd ────────────────────────────────────────────────────

/// Validate that channel `id` exists and return its fd (id + IPC_FD_BASE).
pub fn open_channel(id: u64) -> Option<u64> {
    unsafe {
        let idx = id as usize;
        if idx < MAX_CHANNELS && CHANNELS[idx].used {
            Some(id + IPC_FD_BASE)
        } else {
            None
        }
    }
}

/// True if `fd` refers to an IPC channel (not stdin/stdout).
#[inline]
pub fn is_ipc_fd(fd: u64) -> bool {
    fd >= IPC_FD_BASE && (fd - IPC_FD_BASE) < MAX_CHANNELS as u64
}

#[inline]
pub fn chan_id(fd: u64) -> usize {
    (fd - IPC_FD_BASE) as usize
}

// ── Nz / Soa — send on a channel ─────────────────────────────────────────────

/// Push `word` onto channel `chan_id`.
/// Returns true on success.  Wakes any process blocked on this channel.
pub fn send(id: usize, word: u64) -> bool {
    unsafe {
        if id >= MAX_CHANNELS || !CHANNELS[id].used { return false; }
        let ok = CHANNELS[id].push(word);
        if ok {
            // Wake any process waiting specifically on this channel.
            for (slot, &wait) in WAIT_CHANNEL.iter().enumerate() {
                if wait == id as i32 {
                    WAIT_CHANNEL[slot] = -1;
                    process::unblock_slot(slot);
                }
            }
        }
        ok
    }
}

/// Pop one word from channel `chan_id`.  Returns None if the ring is empty.
pub fn recv(id: usize) -> Option<u64> {
    unsafe {
        if id >= MAX_CHANNELS || !CHANNELS[id].used { return None; }
        CHANNELS[id].pop()
    }
}

/// Mark `slot` as waiting on channel `id`.
/// Caller must call `process::block_current()` + `yield_now()` immediately after.
pub fn block_on_channel(slot: usize, id: usize) {
    unsafe {
        if slot < MAX_PROCS {
            WAIT_CHANNEL[slot] = id as i32;
        }
    }
}

/// True if channel `id` has data ready.
pub fn channel_ready(id: usize) -> bool {
    unsafe {
        id < MAX_CHANNELS && CHANNELS[id].used && CHANNELS[id].count > 0
    }
}

// ── Rope — resource ownership binding ────────────────────────────────────────

struct RopeBind {
    token: u64,
    pid:   u32,
    used:  bool,
}

static mut ROPE_TABLE: [RopeBind; 32] = [const { RopeBind { token: 0, pid: 0, used: false } }; 32];

/// Bind `token` to the current process.  Returns the token as the handle.
pub fn bind_resource(token: u64) -> u64 {
    let pid = crate::process::current_id().0;
    unsafe {
        for slot in ROPE_TABLE.iter_mut() {
            if !slot.used {
                slot.token = token;
                slot.pid   = pid;
                slot.used  = true;
                return token;
            }
        }
    }
    u64::MAX
}

/// Release all resource bindings owned by `pid` (called on process exit).
pub fn release_bindings(pid: u32) {
    unsafe {
        for slot in ROPE_TABLE.iter_mut() {
            if slot.used && slot.pid == pid {
                slot.used = false;
            }
        }
    }
}

/// True if `token` is bound to some process.
pub fn is_bound(token: u64) -> bool {
    unsafe {
        ROPE_TABLE.iter().any(|s| s.used && s.token == token)
    }
}

// ── Hook — user-mode IRQ handler registration ─────────────────────────────────

pub struct IrqHook {
    pub irq:     u8,
    pub fn_va:   u64,   // virtual address of the handler in user space
    pub pid:     u32,
    pub active:  bool,
}

static mut HOOKS: [IrqHook; MAX_HOOKS] = [const {
    IrqHook { irq: 0, fn_va: 0, pid: 0, active: false }
}; MAX_HOOKS];

/// Register a user-mode function at `fn_va` as the handler for `irq`.
/// Returns true on success.  Replaces any prior handler for the same IRQ.
pub fn register_hook(irq: u8, fn_va: u64) -> bool {
    let pid = crate::process::current_id().0;
    unsafe {
        // Replace existing hook for this irq if present.
        for hook in HOOKS.iter_mut() {
            if hook.active && hook.irq == irq {
                hook.fn_va = fn_va;
                hook.pid   = pid;
                return true;
            }
        }
        // Find empty slot.
        for hook in HOOKS.iter_mut() {
            if !hook.active {
                hook.irq    = irq;
                hook.fn_va  = fn_va;
                hook.pid    = pid;
                hook.active = true;
                return true;
            }
        }
        false
    }
}

/// Return the registered hook for `irq`, if any.
pub fn hook_for_irq(irq: u8) -> Option<(u64, u32)> {
    unsafe {
        for hook in HOOKS.iter() {
            if hook.active && hook.irq == irq {
                return Some((hook.fn_va, hook.pid));
            }
        }
        None
    }
}

/// Remove all hooks registered by `pid`.
pub fn release_hooks(pid: u32) {
    unsafe {
        for hook in HOOKS.iter_mut() {
            if hook.active && hook.pid == pid {
                hook.active = false;
            }
        }
    }
}

// ── Fang — constitutive resource contract ────────────────────────────────────

struct Contract {
    resource: u64,
    rate:     u64,
    pid:      u32,
    active:   bool,
}

static mut CONTRACTS: [Contract; MAX_CONTRACTS] = [const {
    Contract { resource: 0, rate: 0, pid: 0, active: false }
}; MAX_CONTRACTS];

/// Declare that the current process constitutively consumes `resource` at `rate`.
pub fn declare_contract(resource: u64, rate: u64) {
    let pid = crate::process::current_id().0;
    unsafe {
        // Update existing contract for same (pid, resource).
        for c in CONTRACTS.iter_mut() {
            if c.active && c.pid == pid && c.resource == resource {
                c.rate = rate;
                return;
            }
        }
        for c in CONTRACTS.iter_mut() {
            if !c.active {
                c.resource = resource;
                c.rate     = rate;
                c.pid      = pid;
                c.active   = true;
                return;
            }
        }
    }
}

/// Sum of `rate` across all contracts for `resource` (kernel quota view).
pub fn total_rate(resource: u64) -> u64 {
    unsafe {
        CONTRACTS.iter()
            .filter(|c| c.active && c.resource == resource)
            .fold(0u64, |acc, c| acc.wrapping_add(c.rate))
    }
}

/// Release all contracts for `pid` (called on process exit).
pub fn release_contracts(pid: u32) {
    unsafe {
        for c in CONTRACTS.iter_mut() {
            if c.active && c.pid == pid { c.active = false; }
        }
    }
}

// ── Circle — broadcast event ──────────────────────────────────────────────────

/// Mark current process as waiting for event `event_id`.
/// Caller must call `block_current()` + `yield_now()` immediately after.
pub fn wait_for_event(slot: usize, event_id: u64) {
    unsafe {
        if slot < MAX_PROCS { WAIT_EVENT[slot] = event_id; }
    }
}

/// Broadcast `event_id` with payload `data`.
/// All processes waiting on this event_id are unblocked; their a0 will be set
/// to `data` via `deliver_event_result`.
/// Returns the number of processes woken.
pub fn broadcast(event_id: u64, data: u64) -> u32 {
    let mut woken = 0u32;
    unsafe {
        for slot in 0..MAX_PROCS {
            if WAIT_EVENT[slot] == event_id && event_id != 0 {
                WAIT_EVENT[slot] = 0;
                // Store the payload so the process can retrieve it via a0.
                EVENT_RESULTS[slot] = data;
                process::unblock_slot(slot);
                woken += 1;
            }
        }
    }
    woken
}

// Per-slot event payload — written by broadcast, read by the woken process.
static mut EVENT_RESULTS: [u64; MAX_PROCS] = [0u64; MAX_PROCS];

/// Called by the trap handler after a process is woken from Ko (wait event).
/// Returns the event payload that was delivered.
pub fn take_event_result(slot: usize) -> u64 {
    unsafe {
        let v = EVENT_RESULTS[slot];
        EVENT_RESULTS[slot] = 0;
        v
    }
}

// ── Process-exit cleanup ──────────────────────────────────────────────────────

/// Release all IPC state for `pid` when a process exits.
pub fn cleanup(pid: u32) {
    release_bindings(pid);
    release_hooks(pid);
    release_contracts(pid);
}
