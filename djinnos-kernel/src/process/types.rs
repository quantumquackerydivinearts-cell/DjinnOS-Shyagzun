// Process types for DjinnOS.
//
// A Process is a YeGaoh complexing — a localized instantiation of the full
// 24-tongue superposition at a specific byte table coordinate.  Each eigenstate
// holds the current byte table address in that tongue's address space.  When
// the process interacts with the kernel (opens a file, sends a packet, etc.)
// the relevant eigenstate advances to the corresponding address.

// ── CPU context (callee-saved RISC-V registers) ───────────────────────────────
// These 14 registers fully describe where a process will resume when scheduled.
// Caller-saved registers are not preserved across context switches — the
// process that yields owns the responsibility of calling convention.

#[repr(C)]
pub struct Context {
    pub ra:  u64,   // return address — where the process resumes
    pub sp:  u64,   // stack pointer
    pub s0:  u64,
    pub s1:  u64,
    pub s2:  u64,
    pub s3:  u64,
    pub s4:  u64,
    pub s5:  u64,
    pub s6:  u64,
    pub s7:  u64,
    pub s8:  u64,
    pub s9:  u64,
    pub s10: u64,
    pub s11: u64,
}

impl Context {
    pub const fn zeroed() -> Self {
        Self { ra:0, sp:0, s0:0, s1:0, s2:0, s3:0,
               s4:0, s5:0, s6:0, s7:0, s8:0, s9:0, s10:0, s11:0 }
    }
}

// ── The 24-tongue eigenstate vector ──────────────────────────────────────────
// Each field is a byte table coordinate — where the process currently sits in
// that tongue's address space.  Defaults express what a newly spawned process
// IS: active (Ta), in motion (Wu), ordered (Va), networked (Ne), minded (A),
// in linear time (Si), mounted (Sa), consciously persisting (Soa).

#[derive(Clone, Copy)]
pub struct Eigenstates {
    pub lotus:          u32,   // default  9  — Ta (Active being / presence)
    pub rose:           u32,   // default 45  — Wu (Process / Way)
    pub sakura:         u32,   // default 66  — Va (Order / Structure / Life)
    pub daisy:          u32,   // default 87  — Ne (Network / System)
    pub apple_blossom:  u32,   // default 98  — A  (Mind +)
    pub aster:          u32,   // default 142 — Si (Linear time)
    pub grapevine:      u32,   // default 156 — Sa (Root volume)
    pub cannabis:       u32,   // default 193 — Soa (Conscious persistence)
    pub dragon:         u32,   // default 261 — Homo sapiens
    pub virus:          u32,   // default 294 — Plavik (Codon / minimal unit)
    pub bacteria:       u32,   // default 316 — Zhove (Resting potential)
    pub excavata:       u32,   // default 0   — (tongue not yet attested)
    pub archaeplastida: u32,
    pub myxozoa:        u32,
    pub archea:         u32,
    pub protist:        u32,
    pub immune:         u32,
    pub neural:         u32,
    pub serpent:        u32,
    pub beast:          u32,
    pub cherub:         u32,
    pub chimera:        u32,
    pub faerie:         u32,
    pub djinn:          u32,
}

impl Eigenstates {
    pub const fn ground() -> Self {
        Self {
            lotus: 9, rose: 45, sakura: 66, daisy: 87,
            apple_blossom: 98, aster: 142, grapevine: 156, cannabis: 193,
            dragon: 261, virus: 294, bacteria: 316,
            excavata: 0, archaeplastida: 0, myxozoa: 0, archea: 0,
            protist: 0, immune: 0, neural: 0, serpent: 0, beast: 0,
            cherub: 0, chimera: 0, faerie: 0, djinn: 0,
        }
    }
}

// ── Process identity and state ────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct ProcessId(pub u32);  // byte table coordinate — identity, not index

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum ProcessState {
    Ready,
    Running,
    Blocked,
    Dead,
}

pub struct Process {
    pub id:          ProcessId,
    pub state:       ProcessState,
    pub eigenstates: Eigenstates,
    pub context:     Context,
    pub stack_index: usize,      // index into STACKS array
}