/* switch_context — x86_64 (Intel syntax)
 *
 * extern "C" fn switch_context(from: *mut Context, to: *const Context)
 *   rdi = outgoing Context*, rsi = incoming Context*
 *
 * Context layout (offsets match types.rs):
 *   0  ra  ← saved rip (return address from CALL)
 *   8  sp  ← rsp (after the pop)
 *  16  s0  ← rbx
 *  24  s1  ← rbp
 *  32  s2  ← r12
 *  40  s3  ← r13
 *  48  s4  ← r14
 *  56  s5  ← r15
 */

.section .text
.global switch_context
.align 4

switch_context:
    /* The CALL that invoked us pushed the return address onto the stack.
     * Pop it into rax — that becomes Context.ra for this process. */
    pop   rax

    /* Save outgoing context */
    mov   [rdi +  0], rax     /* ra */
    mov   [rdi +  8], rsp     /* sp */
    mov   [rdi + 16], rbx     /* s0 */
    mov   [rdi + 24], rbp     /* s1 */
    mov   [rdi + 32], r12     /* s2 */
    mov   [rdi + 40], r13     /* s3 */
    mov   [rdi + 48], r14     /* s4 */
    mov   [rdi + 56], r15     /* s5 */

    /* Load incoming context */
    mov   r15, [rsi + 56]
    mov   r14, [rsi + 48]
    mov   r13, [rsi + 40]
    mov   r12, [rsi + 32]
    mov   rbp, [rsi + 24]
    mov   rbx, [rsi + 16]
    mov   rsp, [rsi +  8]

    /* Push ra onto the new stack, then ret to jump there.
     * For a fresh spawn: sp=kstack_top, ra=entry fn — jumps directly.
     * For a resumed process: sp = saved rsp, ra = return site. */
    push  qword ptr [rsi + 0]
    ret