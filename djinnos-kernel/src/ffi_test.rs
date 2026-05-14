// ffi_test.rs — Phase 1 FFI probe.
//
// Calls c_add() from c/test_ffi.c to verify the C toolchain pipeline.
// Guarded by `c_toolchain_available` cfg, set by build.rs only when
// a suitable cross-compiler was found and the C library was linked.
// Without a C compiler the kernel still builds — this becomes a no-op.

#[cfg(c_toolchain_available)]
extern "C" {
    fn c_add(a: i32, b: i32) -> i32;
}

pub fn run() {
    #[cfg(c_toolchain_available)]
    {
        let result = unsafe { c_add(21, 21) };
        crate::uart::puts("ffi: c_add(21, 21) = ");
        crate::uart::putu(result as u64);
        crate::uart::puts(if result == 42 { "  [OK]\r\n" } else { "  [FAIL]\r\n" });
        assert_eq!(result, 42, "C FFI probe failed — check build.rs");
    }
    #[cfg(not(c_toolchain_available))]
    crate::uart::puts("ffi: C toolchain not available — skipped (set CC or install clang)\r\n");
}
