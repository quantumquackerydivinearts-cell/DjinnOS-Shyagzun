/*
 * string.h — freestanding memory and string primitives for DjinnOS kernel C.
 * Implementations live in c/runtime/string.c.
 */
#pragma once

#include <stddef.h>

void *memcpy (void *dst, const void *src, size_t n);
void *memmove(void *dst, const void *src, size_t n);
void *memset (void *dst, int c, size_t n);
int   memcmp (const void *a, const void *b, size_t n);
size_t strlen(const char *s);
