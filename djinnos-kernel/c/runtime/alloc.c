/*
 * alloc.c — C-visible kernel heap allocator.
 *
 * djinnos_alloc / djinnos_free are thin forwarding wrappers around the
 * Rust global allocator declared in mm.rs.  The Rust symbols are exported
 * via extern "C" in mm.rs so they are visible at C link time.
 */

#include <djinnos.h>
#include <stddef.h>

/*
 * Rust allocator entry points (defined in mm.rs, exported with #[no_mangle]).
 * We call them directly rather than going through alloc::alloc to avoid any
 * hosted-runtime overhead.
 */
extern void *djinnos_heap_alloc(size_t size, size_t align);
extern void  djinnos_heap_free (void *ptr,   size_t size, size_t align);

void *djinnos_alloc(size_t size)
{
    if (size == 0) return (void *)0;
    return djinnos_heap_alloc(size, 16);  /* 16-byte aligned, matches mm.rs HDR */
}

void djinnos_free(void *ptr)
{
    /*
     * The kernel allocator does not need the size at free time in the
     * current linked-list implementation (it reads it from the block header).
     * Pass 0; the Rust side ignores it for this implementation.
     */
    if (ptr) djinnos_heap_free(ptr, 0, 16);
}
