/*
 * test_ffi.c — Phase 1 FFI probe.
 *
 * Compiled into the kernel and called from Rust to verify the end-to-end
 * C toolchain pipeline works before any heavier functionality is added.
 */

#include <djinnos.h>

int c_add(int a, int b)
{
    return a + b;
}
