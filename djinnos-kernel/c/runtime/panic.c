/*
 * panic.c — Abort handler callable from C kernel modules.
 *
 * Routes into the Rust UART output then halts.  Uses __attribute__((noreturn))
 * so the compiler does not generate unreachable code after calls.
 */

#include <djinnos.h>
#include <string.h>

/* Rust symbol: puts a null-terminated string to UART. */
extern void uart_puts(const char *s);

void __attribute__((noreturn)) djinnos_abort(const char *msg)
{
    uart_puts("\r\n[C ABORT] ");
    if (msg && msg[0]) uart_puts(msg);
    uart_puts("\r\n");
    /* Halt the CPU in an infinite loop. */
    for (;;) {
        __asm__ volatile ("hlt");
    }
}
