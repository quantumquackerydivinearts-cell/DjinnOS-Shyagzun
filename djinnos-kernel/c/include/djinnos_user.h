/*
 * djinnos_user.h — DjinnOS syscall interface for ring-3 user programs.
 *
 * Include this (instead of or alongside djinnos.h) in C programs that run
 * in ring-3 user mode.  Each function wraps the x86-64 SYSCALL instruction.
 * The kernel's syscall numbers are byte-table addresses — meaningful, not
 * arbitrary.
 *
 * Syscall ABI (x86-64 SYSCALL/SYSRET):
 *   rax = syscall number
 *   rdi, rsi, rdx, r10, r8, r9 = arguments 1–6
 *   return value in rax
 *   rcx and r11 are clobbered by SYSCALL/SYSRET
 *
 * Syscall numbers correspond to Shygazun byte-table addresses.
 * The full table is in djinnos-kernel/src/byte_table/mod.rs.
 */
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Syscall numbers (Shygazun byte-table addresses) ────────────────────── */

#define SYS_ZU      1   /* exit current process                             */
#define SYS_LY      2   /* read(fd, buf, len) → bytes                       */
#define SYS_KO     19   /* sbrk(incr) → old_break                           */
#define SYS_SOA   193   /* write(fd, data, len) → bytes                     */
#define SYS_MEK   166   /* tcp_close(fd)                                     */
#define SYS_KOI  1138   /* tcp_connect(ip_packed_u32, port) → fd            */
#define SYS_RO     83   /* tcp_listen(port) → fd                            */

/* ── Well-known file descriptors ────────────────────────────────────────── */

#define DJINN_STDIN   0
#define DJINN_STDOUT  1
#define DJINN_STDERR  2

/* ── Inline syscall wrappers ────────────────────────────────────────────── */

/**
 * Exit the current ring-3 process and return control to the kernel.
 * The kernel thread that called djinnos_spawn_elf() resumes after this.
 */
static inline void __attribute__((noreturn)) djinnos_exit(void) {
    __asm__ volatile(
        "syscall"
        :
        : "a"((uint64_t)SYS_ZU)
        : "rcx", "r11", "memory"
    );
    __builtin_unreachable();
}

/**
 * Write len bytes from buf to fd.
 *   fd=1 → UART/stdout, fd=2 → UART/stderr
 * Returns bytes written, or a negative error code.
 */
static inline long djinnos_write(int fd, const void *buf, size_t len) {
    long ret;
    __asm__ volatile(
        "syscall"
        : "=a"(ret)
        : "a"((uint64_t)SYS_SOA),
          "D"((uint64_t)(unsigned)fd),
          "S"(buf),
          "d"(len)
        : "rcx", "r11", "memory"
    );
    return ret;
}

/**
 * Read up to len bytes from fd into buf.
 *   fd=0 → keyboard/stdin (blocks until data available)
 * Returns bytes read, or a negative error code.
 */
static inline long djinnos_read(int fd, void *buf, size_t len) {
    long ret;
    __asm__ volatile(
        "syscall"
        : "=a"(ret)
        : "a"((uint64_t)SYS_LY),
          "D"((uint64_t)(unsigned)fd),
          "S"(buf),
          "d"(len)
        : "rcx", "r11", "memory"
    );
    return ret;
}

/**
 * Expand the user heap by incr bytes.
 * Returns a pointer to the start of the new region.
 * Returns (void *)UINT64_MAX on OOM.
 *
 * A minimal malloc can be built on top of this:
 *   static char *heap_top = NULL;
 *   void *malloc(size_t n) {
 *       void *p = djinnos_sbrk(n);
 *       return (p == (void *)UINT64_MAX) ? NULL : p;
 *   }
 */
static inline void *djinnos_sbrk(long incr) {
    uint64_t ret;
    __asm__ volatile(
        "syscall"
        : "=a"(ret)
        : "a"((uint64_t)SYS_KO),
          "D"((uint64_t)incr)
        : "rcx", "r11", "memory"
    );
    return (void *)ret;
}

/**
 * Write a null-terminated string to stdout (fd 1).
 * Convenience wrapper around djinnos_write().
 */
static inline void djinnos_print(const char *s) {
    if (!s) return;
    size_t len = 0;
    while (s[len]) len++;
    djinnos_write(DJINN_STDOUT, s, len);
}

/**
 * Open a TCP connection to ip0.ip1.ip2.ip3:port.
 *
 * The kernel uses ip_packed = (ip0 << 24) | (ip1 << 16) | (ip2 << 8) | ip3
 * as a single u32 argument.
 *
 * Returns a file descriptor (uint64_t), or UINT64_MAX on failure.
 * The connection is non-blocking — poll djinnos_tcp_poll() before I/O.
 */
static inline uint64_t djinnos_tcp_connect(
    uint8_t ip0, uint8_t ip1, uint8_t ip2, uint8_t ip3,
    uint16_t port
) {
    uint32_t ip_packed = ((uint32_t)ip0 << 24)
                       | ((uint32_t)ip1 << 16)
                       | ((uint32_t)ip2 <<  8)
                       |  (uint32_t)ip3;
    uint64_t ret;
    __asm__ volatile(
        "syscall"
        : "=a"(ret)
        : "a"((uint64_t)SYS_KOI),
          "D"((uint64_t)ip_packed),
          "S"((uint64_t)port)
        : "rcx", "r11", "memory"
    );
    return ret;
}

/**
 * Close a TCP socket fd previously returned by djinnos_tcp_connect().
 */
static inline void djinnos_tcp_close(uint64_t fd) {
    __asm__ volatile(
        "syscall"
        :
        : "a"((uint64_t)SYS_MEK),
          "D"(fd)
        : "rcx", "r11", "memory"
    );
}

/**
 * Listen for incoming TCP connections on port.
 * Returns a server fd, or UINT64_MAX on failure.
 */
static inline uint64_t djinnos_tcp_listen(uint16_t port) {
    uint64_t ret;
    __asm__ volatile(
        "syscall"
        : "=a"(ret)
        : "a"((uint64_t)SYS_RO),
          "D"((uint64_t)port)
        : "rcx", "r11", "memory"
    );
    return ret;
}

/* ── Minimal stdio-like helpers (no libc) ───────────────────────────────── */

/**
 * Write a single character to stdout.
 */
static inline void djinnos_putchar(char c) {
    djinnos_write(DJINN_STDOUT, &c, 1);
}

/**
 * Write a null-terminated string followed by a newline to stdout.
 */
static inline void djinnos_println(const char *s) {
    djinnos_print(s);
    djinnos_putchar('\n');
}

/**
 * Write a uint64 in decimal to stdout.
 */
static inline void djinnos_print_u64(uint64_t n) {
    if (n == 0) { djinnos_putchar('0'); return; }
    char buf[20];
    int i = 0;
    while (n > 0) { buf[i++] = '0' + (char)(n % 10); n /= 10; }
    while (i-- > 0) djinnos_putchar(buf[i + 1]);
}

/**
 * Write a uint64 in hexadecimal (with 0x prefix) to stdout.
 */
static inline void djinnos_print_hex(uint64_t n) {
    const char *hex = "0123456789abcdef";
    djinnos_print("0x");
    for (int shift = 60; shift >= 0; shift -= 4) {
        djinnos_putchar(hex[(n >> shift) & 0xF]);
    }
}

#ifdef __cplusplus
}
#endif
