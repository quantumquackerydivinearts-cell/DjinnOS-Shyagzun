# switch_context — RISC-V RV64 context switch
#
# Signature (Rust): extern "C" fn switch_context(from: *mut Context, to: *const Context)
#   a0 = pointer to outgoing process's Context struct
#   a1 = pointer to incoming process's Context struct
#
# Saves the 14 callee-saved registers into *from, then loads them from *to.
# When the outgoing process is next scheduled, it resumes at the instruction
# after its own call to switch_context (because ra was saved here).

.section .text
.global switch_context
.align 2

switch_context:
    # Save outgoing context into *a0
    sd  ra,   0(a0)
    sd  sp,   8(a0)
    sd  s0,  16(a0)
    sd  s1,  24(a0)
    sd  s2,  32(a0)
    sd  s3,  40(a0)
    sd  s4,  48(a0)
    sd  s5,  56(a0)
    sd  s6,  64(a0)
    sd  s7,  72(a0)
    sd  s8,  80(a0)
    sd  s9,  88(a0)
    sd  s10, 96(a0)
    sd  s11,104(a0)

    # Load incoming context from *a1
    ld  ra,   0(a1)
    ld  sp,   8(a1)
    ld  s0,  16(a1)
    ld  s1,  24(a1)
    ld  s2,  32(a1)
    ld  s3,  40(a1)
    ld  s4,  48(a1)
    ld  s5,  56(a1)
    ld  s6,  64(a1)
    ld  s7,  72(a1)
    ld  s8,  80(a1)
    ld  s9,  88(a1)
    ld  s10, 96(a1)
    ld  s11,104(a1)

    ret