// x86_64 architecture primitives for DjinnOS.
//
// Phase 1: COM1 serial UART, PIT timer at 100 Hz, 8259 PIC, IDT.
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
    fn _isr_fault();
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
        let fault_gate = make_gate(_isr_fault as *const () as u64);
        for i in 0..256usize {
            IDT.0[i] = fault_gate;
        }
        IDT.0[0x20] = make_gate(_isr_timer as *const () as u64);

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
    unsafe { outb(PIC1_CMD, 0x20); }  // master EOI
}

// ── PIT + 8259 PIC ────────────────────────────────────────────────────────────

const PIT_CH0:  u16 = 0x40;
const PIT_CMD:  u16 = 0x43;
const PIC1_CMD: u16 = 0x20;
const PIC1_DAT: u16 = 0x21;
const PIC2_CMD: u16 = 0xA0;
const PIC2_DAT: u16 = 0xA1;

/// No-op on x86_64 — PIT auto-reloads; tick counter is incremented by ISR.
pub fn sbi_set_timer(_deadline: u64) {}

pub fn enable_timer() {
    unsafe {
        // Remap 8259 PIC: master → 0x20, slave → 0x28
        outb(PIC1_CMD, 0x11); io_wait();
        outb(PIC2_CMD, 0x11); io_wait();
        outb(PIC1_DAT, 0x20); io_wait();
        outb(PIC2_DAT, 0x28); io_wait();
        outb(PIC1_DAT, 0x04); io_wait();   // slave on IRQ2
        outb(PIC2_DAT, 0x02); io_wait();
        outb(PIC1_DAT, 0x01); io_wait();   // 8086 mode
        outb(PIC2_DAT, 0x01); io_wait();
        outb(PIC1_DAT, 0xFE);              // unmask IRQ0 (timer) only
        outb(PIC2_DAT, 0xFF);              // mask all slave IRQs

        // PIT channel 0: rate generator (mode 2), 100 Hz
        // divisor = 1193182 / 100 = 11932 = 0x2E9C
        outb(PIT_CMD, 0x34);
        outb(PIT_CH0, 0x9C);
        outb(PIT_CH0, 0x2E);

        asm!("sti", options(nostack));
    }
}

// ── wfi ──────────────────────────────────────────────────────────────────────

pub fn wfi() {
    unsafe { asm!("hlt", options(nostack)); }
}