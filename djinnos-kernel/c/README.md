# DjinnOS kernel C sources

C is a first-class language in the DjinnOS kernel build.  Rust remains the
primary language; C is used for modules that benefit from direct ABI
compatibility with `djinnos.h`, for algorithm-heavy code that profits from
C's tooling, and for anything that needs to cross the C↔Rust boundary
without marshalling overhead.

## Directory layout

```
c/
  include/          Freestanding headers (no libc)
    stdint.h        Fixed-width integer types
    stddef.h        size_t, NULL, ptrdiff_t, offsetof
    string.h        memcpy / memset / memcmp / memmove / strlen
    djinnos.h       DjinnOS public C API (Phase 1–4)

  runtime/          Minimal C-side runtime (Phase 3)
    string.c        Memory / string primitives
    alloc.c         djinnos_alloc / djinnos_free → kernel heap
    panic.c         djinnos_abort → kernel UART + halt

  streaming/        Streaming platform kernel module (Phase 4)
    stream_platform.c   Stream registry + QCR discovery + HTTP handler

  examples/         Standalone demonstration programs (not linked into kernel)
    hopfield_demo.c

  tests/            Unit tests (compiled and run on host via a separate target)
    test_runtime.c

  test_ffi.c        Phase 1 FFI probe: c_add(a, b) = a + b
```

## Build system

C sources are compiled by `build.rs` using the `cc` crate with freestanding
flags.  The resulting static library `libdjinnos_c.a` is linked directly into
the kernel binary.

### Compiler selection (in priority order)

1. `CC_x86_64_unknown_none` environment variable
2. `CC` environment variable
3. `clang` with `--target=x86_64-unknown-none-elf`
4. `x86_64-elf-gcc`
5. `x86_64-linux-gnu-gcc`
6. `gcc` (fallback; may not produce bare-metal ELF on all hosts)

Recommended: install LLVM/Clang or a cross-GCC toolchain.

```sh
# macOS / Homebrew
brew install llvm

# Ubuntu / Debian
apt install gcc-multilib binutils-x86-64-linux-gnu

# Windows (via winget, then add to PATH)
winget install LLVM.LLVM
```

### Required flags (applied by build.rs automatically)

```
-ffreestanding -nostdlib -fno-builtin -nostartfiles
-m64 -mno-red-zone -mno-mmx -mno-sse -mno-sse2
-fno-stack-protector -O2
```

## Writing a new C module

1. Create `c/<subdir>/your_module.c`.
2. `#include <djinnos.h>` for the kernel API.
3. Declare any Rust-visible exports with `__attribute__((visibility("default")))`.
4. Add corresponding `extern "C"` declarations in Rust and register with the
   appropriate subsystem (HTTP router, eigenstate hooks, etc.).

## C ↔ Rust FFI rules

- Pass byte buffers as `(const uint8_t *buf, size_t len)` pairs — never Rust
  slice fat pointers.
- Return `0` for success, negative `errno`-style values for errors.
- No Rust types (enums with data, trait objects, `Vec`, `String`) cross the
  boundary.  Use `uint8_t` tags + plain C structs.
- Strings are null-terminated `const char *`; lengths are always explicit.
