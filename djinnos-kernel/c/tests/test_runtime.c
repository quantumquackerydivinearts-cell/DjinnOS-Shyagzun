/*
 * test_runtime.c — Unit tests for c/runtime/*.
 *
 * These tests are NOT compiled into the kernel binary.  They are compiled
 * and run on the host to verify the C runtime primitives in isolation.
 *
 * Build and run (host, with a normal C compiler):
 *
 *   gcc -I../include -o test_runtime test_runtime.c ../runtime/string.c \
 *       -DTEST_STANDALONE && ./test_runtime
 *
 * Or via the project test harness (future):
 *   cargo test --features c_tests
 */

#include <string.h>
#include <stdint.h>
#include <stddef.h>

/* ── Minimal test harness ─────────────────────────────────────────────────── */

#ifdef TEST_STANDALONE
#include <stdio.h>
#include <stdlib.h>
#define ASSERT(cond, msg) \
    do { if (!(cond)) { \
        fprintf(stderr, "FAIL [%s:%d] %s\n", __FILE__, __LINE__, (msg)); \
        exit(1); \
    } } while(0)
#define PASS(name) printf("PASS  %s\n", (name))
#else
/* Freestanding context: assert via djinnos_abort */
#include <djinnos.h>
#define ASSERT(cond, msg) do { if (!(cond)) djinnos_abort((msg)); } while(0)
#define PASS(name) (void)(name)
#endif

/* ── memcpy tests ──────────────────────────────────────────────────────────── */

static void test_memcpy(void)
{
    unsigned char src[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
    unsigned char dst[8] = { 0 };

    memcpy(dst, src, 8);
    for (int i = 0; i < 8; i++)
        ASSERT(dst[i] == src[i], "memcpy: byte mismatch");

    /* Zero-length copy should be a no-op. */
    unsigned char z[4] = { 0xDE, 0xAD, 0xBE, 0xEF };
    memcpy(z, src, 0);
    ASSERT(z[0] == 0xDE, "memcpy(0): must not write");

    PASS("memcpy");
}

/* ── memmove tests ─────────────────────────────────────────────────────────── */

static void test_memmove(void)
{
    /* Non-overlapping */
    unsigned char a[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
    unsigned char b[8] = { 0 };
    memmove(b, a, 8);
    for (int i = 0; i < 8; i++) ASSERT(b[i] == a[i], "memmove no-overlap");

    /* Overlapping: shift right by 2 within the same buffer */
    unsigned char buf[10] = { 1, 2, 3, 4, 5, 6, 7, 8, 0, 0 };
    memmove(buf + 2, buf, 8);
    ASSERT(buf[2] == 1, "memmove overlap: buf[2]");
    ASSERT(buf[9] == 8, "memmove overlap: buf[9]");

    /* Overlapping: shift left by 1 */
    unsigned char buf2[8] = { 0, 1, 2, 3, 4, 5, 6, 7 };
    memmove(buf2, buf2 + 1, 7);
    ASSERT(buf2[0] == 1, "memmove left shift: buf2[0]");
    ASSERT(buf2[6] == 7, "memmove left shift: buf2[6]");

    PASS("memmove");
}

/* ── memset tests ──────────────────────────────────────────────────────────── */

static void test_memset(void)
{
    unsigned char buf[16];
    memset(buf, 0xAB, 16);
    for (int i = 0; i < 16; i++)
        ASSERT(buf[i] == 0xAB, "memset: byte mismatch");

    memset(buf, 0, 8);
    for (int i = 0; i < 8; i++)  ASSERT(buf[i] == 0x00, "memset zero: first half");
    for (int i = 8; i < 16; i++) ASSERT(buf[i] == 0xAB, "memset zero: second half untouched");

    PASS("memset");
}

/* ── memcmp tests ──────────────────────────────────────────────────────────── */

static void test_memcmp(void)
{
    unsigned char x[4] = { 1, 2, 3, 4 };
    unsigned char y[4] = { 1, 2, 3, 4 };
    unsigned char z[4] = { 1, 2, 4, 4 };

    ASSERT(memcmp(x, y, 4) == 0, "memcmp equal");
    ASSERT(memcmp(x, z, 4)  < 0, "memcmp less");
    ASSERT(memcmp(z, x, 4)  > 0, "memcmp greater");
    ASSERT(memcmp(x, y, 0) == 0, "memcmp zero length");

    PASS("memcmp");
}

/* ── strlen tests ──────────────────────────────────────────────────────────── */

static void test_strlen(void)
{
    ASSERT(strlen("")        == 0, "strlen empty");
    ASSERT(strlen("hello")   == 5, "strlen hello");
    ASSERT(strlen("abc\0xy") == 3, "strlen stops at NUL");

    PASS("strlen");
}

/* ── Entry point ───────────────────────────────────────────────────────────── */

#ifdef TEST_STANDALONE
int main(void)
{
    test_memcpy();
    test_memmove();
    test_memset();
    test_memcmp();
    test_strlen();
    printf("All runtime tests passed.\n");
    return 0;
}
#else
/* Called from the kernel to self-test the C runtime in-situ. */
void djinnos_runtime_selftest(void)
{
    test_memcpy();
    test_memmove();
    test_memset();
    test_memcmp();
    test_strlen();
}
#endif
