/*
 * djinnos.h — DjinnOS Shygazun syscall ABI for x86-64 user programs.
 *
 * Syscall convention:
 *   instruction : SYSCALL
 *   num  (RAX)  : Shygazun byte-table address of the operation
 *   a0   (RDI)  : first argument
 *   a1   (RSI)  : second argument
 *   a2   (RDX)  : third argument
 *   a3   (R10)  : fourth argument   (R10, not RCX — SYSCALL clobbers RCX)
 *   a4   (R8)   : fifth argument
 *   a5   (R9)   : sixth argument
 *   return      : RAX  (u64; u64::MAX = error)
 *
 * Compile against this header with:
 *   x86_64-linux-musl-gcc -static -nostdlib -o prog prog.c djinnos_start.s
 *
 * djinnos_start.s must provide _start → call main → sys_exit(rax).
 */

#pragma once
#include <stddef.h>
#include <stdint.h>

/* ── Syscall numbers (Shygazun byte-table addresses) ── */
#define SYS_TY    0    /* spawn ELF  */
#define SYS_ZU    1    /* exit       */
#define SYS_LY    2    /* read       */
#define SYS_FY    4    /* yield      */
#define SYS_SAO   157  /* open file  */
#define SYS_SOA   193  /* write      */
#define SYS_SEI   203  /* sbrk       */
#define SYS_SI    142  /* ticks      */

/* ── Raw syscall wrappers ── */
static inline uint64_t
_djn_syscall0(uint64_t num)
{
    uint64_t ret;
    __asm__ volatile (
        "syscall"
        : "=a"(ret)
        : "0"(num)
        : "rcx", "r11", "memory"
    );
    return ret;
}

static inline uint64_t
_djn_syscall1(uint64_t num, uint64_t a0)
{
    uint64_t ret;
    __asm__ volatile (
        "syscall"
        : "=a"(ret)
        : "0"(num), "D"(a0)
        : "rcx", "r11", "memory"
    );
    return ret;
}

static inline uint64_t
_djn_syscall2(uint64_t num, uint64_t a0, uint64_t a1)
{
    uint64_t ret;
    __asm__ volatile (
        "syscall"
        : "=a"(ret)
        : "0"(num), "D"(a0), "S"(a1)
        : "rcx", "r11", "memory"
    );
    return ret;
}

static inline uint64_t
_djn_syscall3(uint64_t num, uint64_t a0, uint64_t a1, uint64_t a2)
{
    uint64_t ret;
    __asm__ volatile (
        "syscall"
        : "=a"(ret)
        : "0"(num), "D"(a0), "S"(a1), "d"(a2)
        : "rcx", "r11", "memory"
    );
    return ret;
}

/* ── High-level API ── */

static inline void
sys_exit(int code)
{
    _djn_syscall1(SYS_ZU, (uint64_t)code);
    __builtin_unreachable();
}

static inline ssize_t
sys_write(int fd, const void *buf, size_t len)
{
    return (ssize_t)_djn_syscall3(SYS_SOA,
        (uint64_t)fd, (uint64_t)buf, (uint64_t)len);
}

static inline ssize_t
sys_read(int fd, void *buf, size_t len)
{
    return (ssize_t)_djn_syscall3(SYS_LY,
        (uint64_t)fd, (uint64_t)buf, (uint64_t)len);
}

static inline void *
sys_sbrk(size_t incr)
{
    uint64_t ret = _djn_syscall1(SYS_SEI, (uint64_t)incr);
    return (ret == (uint64_t)-1) ? (void *)-1 : (void *)ret;
}

static inline uint64_t
sys_ticks(void)
{
    return _djn_syscall0(SYS_SI);
}

static inline void
sys_yield(void)
{
    _djn_syscall0(SYS_FY);
}

/* ── Minimal stdio shims ── */

static inline int
djn_puts(const char *s)
{
    size_t n = 0;
    while (s[n]) n++;
    return (int)sys_write(1, s, n);
}

static inline int
djn_putchar(int c)
{
    char b = (char)c;
    sys_write(1, &b, 1);
    return c;
}
