// x86_64 architecture primitives for DjinnOS.
//
// Timer: Local APIC periodic at 100 Hz, calibrated against PIT channel 2.
// The 8259 PIC is remapped to 0x70–0x7F then fully masked — LAPIC only.
// ISR stubs live in boot_x86.s; they call back into Rust via _timer_tick.

use core::arch::asm;
use core::sync::atomic::{AtomicU64, Ordering};

// ── Port I/O ──────────────────────────────────────────────────────────────────

#[inline(always)]
pub unsafe fn outb(port: u16, val: u8) {
    asm!("out dx, al", in("dx") port, in("al") val, options(nostack, nomem));
}

#[inline(always)]
pub unsafe fn inb(port: u16) -> u8 {
    let val: u8;
    asm!("in al, dx", out("al") val, in("dx") port, options(nostack, nomem));
    val
}

#[inline(always)]
pub unsafe fn outl(port: u16, val: u32) {
    asm!("out dx, eax", in("dx") port, in("eax") val, options(nostack, nomem));
}

#[inline(always)]
pub unsafe fn inl(port: u16) -> u32 {
    let val: u32;
    asm!("in eax, dx", out("eax") val, in("dx") port, options(nostack, nomem));
    val
}

#[inline]
fn io_wait() {
    unsafe { outb(0x80, 0) }
}

// ── COM1 serial UART (16550A at I/O port 0x3F8) ───────────────────────────────

const COM1: u16 = 0x3F8;

pub fn uart_init() {
    unsafe {
        outb(COM1 + 1, 0x00);   // disable interrupts
        outb(COM1 + 3, 0x80);   // DLAB on
        outb(COM1 + 0, 0x03);   // divisor = 3 → 38400 baud
        outb(COM1 + 1, 0x00);
        outb(COM1 + 3, 0x03);   // 8N1, DLAB off
        outb(COM1 + 2, 0xC7);   // FIFO, 14-byte threshold
        outb(COM1 + 4, 0x0B);   // RTS/DSR/OUT2
    }
}

pub fn uart_putc(byte: u8) {
    unsafe {
        while inb(COM1 + 5) & 0x20 == 0 {}
        outb(COM1, byte);
    }
}

pub fn uart_getc() -> Option<u8> {
    unsafe {
        if inb(COM1 + 5) & 0x01 != 0 { Some(inb(COM1)) } else { None }
    }
}

// ── Paging (boot_x86.s already set up 2 MiB identity map) ────────────────────

pub fn enable_paging(_root_pa: u64) { /* no-op: boot assembly handled it */ }

pub fn flush_tlb() {
    unsafe {
        let cr3: u64;
        asm!("mov {0}, cr3", out(reg) cr3, options(nostack, nomem));
        asm!("mov cr3, {0}", in(reg) cr3, options(nostack, nomem));
    }
}

pub fn paging_active() -> bool {
    let cr0: u64;
    unsafe { asm!("mov {0}, cr0", out(reg) cr0, options(nostack, nomem)); }
    cr0 & (1 << 31) != 0
}

// ── IDT ───────────────────────────────────────────────────────────────────────

#[repr(C, align(16))]
struct Idt([[u64; 2]; 256]);
static mut IDT: Idt = Idt([[0u64; 2]; 256]);

// ISR stubs are defined in boot_x86.s and call back into _timer_tick.
extern "C" {
    fn _isr_timer();
    fn _isr_fault();    // CPU exceptions 0x00–0x1F: hlt (real bugs)
    fn _isr_generic();  // hardware IRQs 0x20–0xFE: LAPIC EOI + iretq
    fn _isr_spurious(); // LAPIC spurious 0xFF: iretq, no EOI
}

fn make_gate(handler: u64) -> [u64; 2] {
    // 64-bit interrupt gate low qword layout:
    //   [0:15]  = offset[15:0]
    //   [16:31] = code segment selector = 0x08
    //   [32:39] = IST = 0
    //   [40:47] = type/attr = 0x8E  (P=1 DPL=0 gate=0xE)
    //   [48:63] = offset[31:16]
    let lo = (handler & 0x0000_FFFF)
           | (0x0008_u64 << 16)
           | (0x8E_u64 << 40)                    // type byte at bits 40–47
           | ((handler & 0xFFFF_0000) << 32);    // offset[31:16] at bits 48–63
    let hi = handler >> 32;                      // offset[63:32]
    [lo, hi]
}

fn init_idt() {
    unsafe {
        let fault_gate   = make_gate(_isr_fault   as *const () as u64);
        let generic_gate = make_gate(_isr_generic as *const () as u64);
        // CPU exception vectors: fatal fault handler
        for i in 0x00..0x20usize { IDT.0[i] = fault_gate; }
        // Hardware IRQ vectors: generic EOI + iretq (silences unexpected IOAPIC IRQs)
        for i in 0x20..0xFFusize { IDT.0[i] = generic_gate; }
        IDT.0[0x20] = make_gate(_isr_timer    as *const () as u64);
        IDT.0[0xFF] = make_gate(_isr_spurious as *const () as u64);

        #[repr(C, packed)]
        struct Idtr { limit: u16, base: u64 }
        let idtr = Idtr {
            limit: (core::mem::size_of::<Idt>() - 1) as u16,
            base:  IDT.0.as_ptr() as u64,
        };
        let ptr = &idtr as *const Idtr as u64;
        asm!("lidt [{0}]", in(reg) ptr, options(nostack));
    }
}

/// Called by trap::init().  Populates and loads the IDT.
pub fn set_trap_vector(_addr: u64) {
    init_idt();
}

// ── Timer tick counter ────────────────────────────────────────────────────────

pub static TICKS: AtomicU64 = AtomicU64::new(0);

/// Ticks per scheduler quantum (1 tick = 10 ms at 100 Hz PIT).
pub const TICK_INTERVAL: u64 = 1;

pub fn read_mtime() -> u64 {
    TICKS.load(Ordering::Relaxed)
}

/// Called from the _isr_timer assembly stub.
#[no_mangle]
pub extern "C" fn _timer_tick() {
    TICKS.fetch_add(1, Ordering::Relaxed);
    unsafe { lapic_write(LAPIC_EOI, 0); }  // LAPIC EOI (write 0 to offset 0xB0)
}

// ── LAPIC (Local APIC) ────────────────────────────────────────────────────────
//
// The LAPIC base address lives in MSR 0x1B bits [51:12].  On every x86_64
// CPU the LAPIC is identity-mapped in physical memory (typically 0xFEE00000).
// UEFI's 0–4 GiB identity map covers it.

const IA32_APIC_BASE: u32 = 0x1B;
const APIC_BASE_X2APIC_ENABLE: u64 = 1 << 10;  // MSR 0x1B bit 10

// LAPIC register offsets (MMIO) / MSR index suffix (x2APIC: 0x800 + offset>>4)
const LAPIC_EOI:       u32 = 0x0B0;
const LAPIC_SVR:       u32 = 0x0F0;
const LAPIC_LVT_TIMER: u32 = 0x320;
const LAPIC_TIMER_ICR: u32 = 0x380;
const LAPIC_TIMER_CCR: u32 = 0x390;
const LAPIC_TIMER_DCR: u32 = 0x3E0;

const LAPIC_SW_ENABLE:      u32 = 1 << 8;
const LAPIC_TIMER_PERIODIC: u32 = 1 << 17;
const LAPIC_TIMER_MASKED:   u32 = 1 << 16;

// x2APIC: access LAPIC via MSRs instead of MMIO.  UEFI on AMD Ryzen often
// enables x2APIC; in that mode the 0xFEE00000 MMIO window is disabled and
// writes to it fault silently or cause #GP.
static X2APIC: core::sync::atomic::AtomicBool =
    core::sync::atomic::AtomicBool::new(false);

unsafe fn rdmsr(msr: u32) -> u64 {
    let lo: u32; let hi: u32;
    asm!("rdmsr", in("ecx") msr, out("eax") lo, out("edx") hi,
         options(nostack, nomem));
    ((hi as u64) << 32) | lo as u64
}

unsafe fn wrmsr(msr: u32, val: u64) {
    asm!("wrmsr",
         in("ecx") msr,
         in("eax") val as u32,
         in("edx") (val >> 32) as u32,
         options(nostack, nomem));
}

fn lapic_mmio_base() -> u64 {
    unsafe { rdmsr(IA32_APIC_BASE) & 0xFFFF_F000 }
}

// x2APIC MSR address for a given xAPIC MMIO register offset.
// Formula: 0x800 + (mmio_offset >> 4).  e.g. EOI=0x0B0 → MSR 0x80B.
#[inline]
fn x2apic_msr(reg: u32) -> u32 { 0x800 + (reg >> 4) }

unsafe fn lapic_read(reg: u32) -> u32 {
    if X2APIC.load(Ordering::Relaxed) {
        rdmsr(x2apic_msr(reg)) as u32
    } else {
        core::ptr::read_volatile((lapic_mmio_base() + reg as u64) as *const u32)
    }
}

unsafe fn lapic_write(reg: u32, val: u32) {
    if X2APIC.load(Ordering::Relaxed) {
        wrmsr(x2apic_msr(reg), val as u64);
    } else {
        core::ptr::write_volatile((lapic_mmio_base() + reg as u64) as *mut u32, val);
    }
}

// ── 8259 PIC ──────────────────────────────────────────────────────────────────

const PIC1_CMD: u16 = 0x20;
const PIC1_DAT: u16 = 0x21;
const PIC2_CMD: u16 = 0xA0;
const PIC2_DAT: u16 = 0xA1;

/// No-op on x86_64 — tick counter incremented by LAPIC ISR.
pub fn sbi_set_timer(_deadline: u64) {}

// ── I/O APIC ──────────────────────────────────────────────────────────────────
// Default IOAPIC base address (0xFEC00000) is universal on x86 systems.
// Each redirection entry controls one IRQ; bit 16 of the low word is the mask.

const IOAPIC_BASE:    u64 = 0xFEC0_0000;
const IOAPIC_REGSEL:  u64 = IOAPIC_BASE;        // index register (write)
const IOAPIC_IOWIN:   u64 = IOAPIC_BASE + 0x10; // data window (read/write)

unsafe fn ioapic_write(reg: u32, val: u32) {
    core::ptr::write_volatile(IOAPIC_REGSEL as *mut u32, reg);
    core::ptr::write_volatile(IOAPIC_IOWIN  as *mut u32, val);
}

unsafe fn ioapic_read(reg: u32) -> u32 {
    core::ptr::write_volatile(IOAPIC_REGSEL as *mut u32, reg);
    core::ptr::read_volatile(IOAPIC_IOWIN  as *const u32)
}

/// Mask every IOAPIC redirection entry.
/// Prevents level-triggered IRQs (keyboard, USB, etc.) from causing an
/// interrupt storm after STI — the IOAPIC would otherwise keep re-delivering
/// them until the source is drained, which the kernel hasn't arranged to do.
unsafe fn mask_ioapic() {
    // IOAPIC VER register (0x01): bits [23:16] = max redirection entry index.
    let ver = ioapic_read(0x01);
    let max_entry = (ver >> 16) & 0xFF;
    for i in 0..=max_entry {
        // Redirection table low word is at register 0x10 + 2*i.
        // Bit 16 = interrupt mask (1 = masked).
        let reg = 0x10 + 2 * i;
        let lo  = ioapic_read(reg);
        ioapic_write(reg, lo | (1 << 16));
    }
}

/// Read APIC hardware state without arming the timer.
/// Returns (raw MSR value, x2apic_active).
pub fn probe_apic() -> (u64, bool) {
    unsafe {
        let msr = rdmsr(IA32_APIC_BASE);
        let x2 = msr & APIC_BASE_X2APIC_ENABLE != 0;
        (msr, x2)
    }
}

pub fn enable_timer() {
    unsafe {
        // Detect x2APIC mode — UEFI on AMD Ryzen commonly enables this.
        let apic_msr = rdmsr(IA32_APIC_BASE);
        if apic_msr & APIC_BASE_X2APIC_ENABLE != 0 {
            X2APIC.store(true, Ordering::Relaxed);
        }

        // Remap 8259 to 0x70–0x7F then mask everything.  Remapping avoids
        // spurious 8259 IRQs colliding with CPU exception vectors 0x00–0x1F.
        outb(PIC1_CMD, 0x11); io_wait();
        outb(PIC2_CMD, 0x11); io_wait();
        outb(PIC1_DAT, 0x70); io_wait();  // master base → 0x70
        outb(PIC2_DAT, 0x78); io_wait();  // slave  base → 0x78
        outb(PIC1_DAT, 0x04); io_wait();  // slave on IRQ2
        outb(PIC2_DAT, 0x02); io_wait();
        outb(PIC1_DAT, 0x01); io_wait();  // 8086 mode
        outb(PIC2_DAT, 0x01); io_wait();
        outb(PIC1_DAT, 0xFF);             // mask all master IRQs
        outb(PIC2_DAT, 0xFF);             // mask all slave  IRQs

        // Enable LAPIC.
        lapic_write(LAPIC_SVR, LAPIC_SW_ENABLE | 0xFF);

        // Fixed initial count for ~100 Hz.  CPUID leaf 0x16 is unreliable on
        // some AMD Zen revisions.  2_000_000 ticks ÷ (LAPIC_clock / 16) gives
        // 62–125 Hz across the 2–4 GHz LAPIC clock range — safe and usable.
        let initial: u32 = 2_000_000;

        // Mask LAPIC LINT0 (defaults to ExtINT — forwards legacy PIC interrupts
        // even after the 8259 is masked) and LINT1 (NMI pin).
        lapic_write(0x350, lapic_read(0x350) | (1 << 16)); // LINT0 masked
        lapic_write(0x360, lapic_read(0x360) | (1 << 16)); // LINT1 masked

        // Mask every IOAPIC redirection entry before STI.
        mask_ioapic();

        // LVT_TIMER must be written BEFORE ICR.  Writing ICR immediately starts
        // the counter; if mode is set afterwards the timer fires once in one-shot
        // mode and stops before periodic mode is established.
        lapic_write(LAPIC_TIMER_DCR, 0x3);                         // divide by 16
        lapic_write(LAPIC_LVT_TIMER, 0x20 | LAPIC_TIMER_PERIODIC); // mode first
        lapic_write(LAPIC_TIMER_ICR, initial);                      // then start
        // NOTE: STI is NOT called here.  Call arch::start_timer() to enable
        // interrupts after confirming the counter is running via probe_timer().
    }
}

/// Enable interrupts — call only after enable_timer() and probe_timer()
/// confirm the LAPIC counter is actually counting down.
pub fn start_timer() {
    unsafe { asm!("sti", options(nostack)); }
}

/// Verify the LAPIC timer is counting.  Returns (ccr_before, ccr_after, lvt).
/// If ccr_before > ccr_after > 0 the timer is running correctly.
/// Called with interrupts still disabled (no STI yet).
pub fn probe_timer() -> (u32, u32, u32) {
    unsafe {
        let ccr1 = lapic_read(LAPIC_TIMER_CCR);
        // Spin ~3 ms at 3 GHz to give the counter time to decrease.
        for _ in 0..10_000_000u32 {
            core::arch::asm!("pause", options(nostack, nomem));
        }
        let ccr2 = lapic_read(LAPIC_TIMER_CCR);
        let lvt  = lapic_read(LAPIC_LVT_TIMER);
        (ccr1, ccr2, lvt)
    }
}

// ── wfi ──────────────────────────────────────────────────────────────────────

pub fn wfi() {
    unsafe { asm!("hlt", options(nostack)); }
}


// ── Ring-3 userspace infrastructure ──────────────────────────────────────────
//
// GDT layout (replaces the 3-entry boot GDT):
//   0x00  null
//   0x08  kernel CS  64-bit code ring 0
//   0x10  kernel DS  data ring 0
//   0x18  user DS    data ring 3       ← SYSRETQ sets SS = STAR[63:48]+8
//   0x20  user CS    64-bit code ring 3 ← SYSRETQ sets CS = STAR[63:48]+16
//   0x28  TSS low    (16-byte 64-bit TSS descriptor)
//   0x30  TSS high
//
// STAR MSR[63:48] = 0x10 → SYSRETQ: CS = 0x10+16 = 0x20 (ring 3), SS = 0x10+8 = 0x18 (ring 3)
// STAR MSR[47:32] = 0x08 → SYSCALL: CS = 0x08 (ring 0), SS = 0x08+8 = 0x10 (ring 0)

pub const SEL_KCODE: u16 = 0x08;
pub const SEL_KDATA: u16 = 0x10;
pub const SEL_UDATA: u16 = 0x1B;  // 0x18 | RPL=3
pub const SEL_UCODE: u16 = 0x23;  // 0x20 | RPL=3
pub const SEL_TSS:   u16 = 0x28;

#[repr(C, align(16))]
struct X86Gdt {
    null:    u64,
    kcode:   u64,
    kdata:   u64,
    udata:   u64,
    ucode:   u64,
    tss_lo:  u64,
    tss_hi:  u64,
}

// 64-bit TSS — only RSP0 matters for SYSCALL handler stack.
#[repr(C, packed)]
struct X86Tss {
    _res0:      u32,
    rsp0:       u64,   // kernel stack for privilege-level transitions
    _rsp1:      u64,
    _rsp2:      u64,
    _res1:      u64,
    _ist:       [u64; 7],
    _res2:      u64,
    _res3:      u16,
    iomap_base: u16,   // offset past TSS end → no I/O permission bitmap
}

static mut X86_GDT: X86Gdt = X86Gdt {
    null:  0,
    kcode: 0x00AF_9A00_0000_FFFF,  // 64-bit code DPL=0
    kdata: 0x00CF_9200_0000_FFFF,  // data DPL=0
    udata: 0x00CF_F200_0000_FFFF,  // data DPL=3
    ucode: 0x00AF_FA00_0000_FFFF,  // 64-bit code DPL=3
    tss_lo: 0,
    tss_hi: 0,
};

static mut X86_TSS: X86Tss = X86Tss {
    _res0: 0, rsp0: 0, _rsp1: 0, _rsp2: 0, _res1: 0,
    _ist: [0; 7], _res2: 0, _res3: 0,
    iomap_base: core::mem::size_of::<X86Tss>() as u16,
};

// 16 KiB kernel-only stack used during SYSCALL handling.
// Top of stack is stored in _kernel_rsp_save (boot_x86.s data symbol).
const KSYSCALL_STACK_LEN: usize = 16 * 1024;
pub static mut KSYSCALL_STACK: [u8; KSYSCALL_STACK_LEN] = [0; KSYSCALL_STACK_LEN];

// 4 MiB flat user heap — allocated from BSS so it's always accessible.
pub const USER_HEAP_LEN: usize = 4 * 1024 * 1024;
pub static mut USER_HEAP: [u8; USER_HEAP_LEN] = [0; USER_HEAP_LEN];
pub static mut USER_HEAP_BREAK: usize = 0;

// External symbols defined in boot_x86.s
unsafe extern "C" {
    static mut _user_rsp_save:   u64;
    static mut _kernel_rsp_save: u64;
}

/// One-time ring-3 setup.  Call after init_idt() in the UEFI boot path.
pub fn setup_userspace() {
    unsafe {
        // ── TSS descriptor ────────────────────────────────────────────────────
        let tss_addr  = &X86_TSS as *const X86Tss as u64;
        let tss_limit = (core::mem::size_of::<X86Tss>() - 1) as u64;
        X86_GDT.tss_lo =
              (tss_limit & 0xFFFF)
            | ((tss_addr & 0xFFFF) << 16)
            | (((tss_addr >> 16) & 0xFF) << 32)
            | (0x89u64 << 40)                       // present, type=9 (avail 64-bit TSS)
            | (((tss_limit >> 16) & 0xF) << 48)
            | (((tss_addr >> 24) & 0xFF) << 56);
        X86_GDT.tss_hi = tss_addr >> 32;

        // ── TSS kernel stack ──────────────────────────────────────────────────
        let ksp = KSYSCALL_STACK.as_ptr().add(KSYSCALL_STACK_LEN) as u64;
        X86_TSS.rsp0 = ksp;
        _kernel_rsp_save = ksp;

        // ── Load new GDT ──────────────────────────────────────────────────────
        #[repr(C, packed)]
        struct Gdtr { limit: u16, base: u64 }
        let gdtr = Gdtr {
            limit: (core::mem::size_of::<X86Gdt>() - 1) as u16,
            base:  &X86_GDT as *const X86Gdt as u64,
        };
        asm!("lgdt [{p}]", p = in(reg) &gdtr as *const Gdtr as u64, options(nostack));

        // Reload CS via far return (the only valid way to change CS in 64-bit mode).
        // Reload DS/ES/SS/FS/GS with mov.
        asm!(
            "push 0x08",
            "lea  rax, [rip + 2f]",
            "push rax",
            "retfq",
            "2:",
            "mov ax, 0x10",
            "mov ds, ax",
            "mov es, ax",
            "mov fs, ax",
            "mov gs, ax",
            "mov ss, ax",
            out("rax") _,
            options(nostack),
        );

        // ── Load TSS ──────────────────────────────────────────────────────────
        asm!("ltr {:x}", in(reg) SEL_TSS, options(nostack));

        // ── Enable SYSCALL instruction (EFER.SCE = 1) ─────────────────────────
        let efer = rdmsr(0xC000_0080);
        wrmsr(0xC000_0080, efer | 1);

        // STAR: kernel CS = 0x08 at bits[47:32], user base = 0x10 at bits[63:48]
        // SYSRETQ: CS = STAR[63:48]+16 = 0x20  SS = STAR[63:48]+8 = 0x18
        wrmsr(0xC000_0081, (0x0010u64 << 48) | (0x0008u64 << 32));

        // LSTAR: syscall entry point
        unsafe extern "C" { fn _syscall_entry(); }
        wrmsr(0xC000_0082, _syscall_entry as *const () as u64);

        // SFMASK: clear IF, TF, DF on SYSCALL entry (interrupts off in kernel)
        wrmsr(0xC000_0084, (1 << 9) | (1 << 8) | (1 << 10));
    }
    make_all_user_accessible();
    crate::uart::puts("userspace: ring-3 ready (SYSCALL/SYSRETQ wired)\r\n");
}

/// Set U/S=1 on every present page table entry so ring-3 code can
/// access the full identity-mapped address space.
/// This is the simple "trust user code" policy for Phase 1.  Proper
/// per-process page tables with isolation come in Phase 2.
pub fn make_all_user_accessible() {
    unsafe {
        let cr3: u64;
        asm!("mov {}, cr3", out(reg) cr3, options(nostack, nomem));
        let pml4 = (cr3 & !0xFFF) as *mut u64;

        for i in 0..512usize {
            let e4 = pml4.add(i).read_volatile();
            if e4 & 1 == 0 { continue; }
            pml4.add(i).write_volatile(e4 | (1 << 2));  // U/S = 1

            let pdpt = (e4 & 0x0000_FFFF_FFFF_F000) as *mut u64;
            for j in 0..512usize {
                let e3 = pdpt.add(j).read_volatile();
                if e3 & 1 == 0 { continue; }
                pdpt.add(j).write_volatile(e3 | (1 << 2));
                if e3 & (1 << 7) != 0 { continue; }  // 1 GiB page — no PD below

                let pd = (e3 & 0x0000_FFFF_FFFF_F000) as *mut u64;
                for k in 0..512usize {
                    let e2 = pd.add(k).read_volatile();
                    if e2 & 1 == 0 { continue; }
                    pd.add(k).write_volatile(e2 | (1 << 2));  // 2 MiB huge page U/S=1
                }
            }
        }
        flush_tlb();
    }
}

/// Enter user mode at `entry` with `user_stack` as the initial RSP.
/// Does NOT return — uses IRETQ to transition ring 0 → ring 3.
pub fn enter_user_x86(entry: u64, user_stack: u64) -> ! {
    // RFLAGS for user mode: IF=1 (interrupts on), reserved bit 1 set.
    const USER_RFLAGS: u64 = 0x202;

    unsafe {
        // IRETQ pops (from current RSP upward): RIP, CS, RFLAGS, RSP, SS.
        // We build this frame on the current kernel stack and then iretq.
        asm!(
            "push {ss}",     // SS  (user)
            "push {rsp_u}",  // RSP (user)
            "push {rf}",     // RFLAGS
            "push {cs}",     // CS  (user)
            "push {rip}",    // RIP (entry)
            // Clear all user-visible registers before entering ring 3.
            "xor eax, eax",
            "xor ebx, ebx",
            "xor ecx, ecx",
            "xor edx, edx",
            "xor esi, esi",
            "xor edi, edi",
            "xor r8d,  r8d",
            "xor r9d,  r9d",
            "xor r10d, r10d",
            "xor r11d, r11d",
            "xor r12d, r12d",
            "xor r13d, r13d",
            "xor r14d, r14d",
            "xor r15d, r15d",
            "xor ebp, ebp",
            "iretq",
            ss    = in(reg) SEL_UDATA as u64,
            rsp_u = in(reg) user_stack,
            rf    = in(reg) USER_RFLAGS,
            cs    = in(reg) SEL_UCODE as u64,
            rip   = in(reg) entry,
            options(noreturn, nostack),
        );
    }
}

/// Expand the user heap by `incr` bytes.  Returns the old break (base of new region).
/// Uses a flat 4 MiB static arena — zero OS-level paging required.
pub fn user_sbrk(incr: usize) -> u64 {
    unsafe {
        let old = USER_HEAP.as_ptr().add(USER_HEAP_BREAK) as u64;
        if incr > 0 {
            USER_HEAP_BREAK += incr;
            if USER_HEAP_BREAK > USER_HEAP_LEN {
                USER_HEAP_BREAK = USER_HEAP_LEN;
                return u64::MAX;  // OOM
            }
        }
        old
    }
}

// ── enter_user / exit_user — cooperative ring-3 session ──────────────────────
//
// Unlike enter_user_x86 (which is diverging), enter_user returns normally once
// the user process calls SYS_ZU.  The symmetry is maintained by _enter_user_x86
// and _exit_user_x86 in boot_x86.s: the former saves callee-saved kernel context
// and arms the SYSCALL stack; the latter restores it and rets to our call site.

unsafe extern "C" {
    fn _enter_user_x86(entry: u64, user_stack: u64);
    fn _exit_user_x86() -> !;
}

/// Enter ring-3 at `entry` with `user_stack` as the initial RSP.
/// Returns when the user process exits via SYS_ZU (exit syscall).
pub fn enter_user(entry: u64, user_stack: u64) {
    unsafe { _enter_user_x86(entry, user_stack); }
}

/// Restore the kernel context saved by `enter_user` and return to its call site.
/// Called by the x86-64 syscall dispatcher on SYS_ZU.
pub fn exit_user() -> ! {
    unsafe { _exit_user_x86() }
}