/*
 * djinnos_port.h -- DjinnOS freestanding bridge for QuickJS.
 *
 * Pre-included before every QuickJS translation unit.
 * Pulls clang's own freestanding headers for primitive types, then
 * provides no-op stubs for everything QuickJS expects from the host OS
 * (malloc, FILE, printf, pthread, math, etc.).
 *
 * Design constraints:
 *   - Compiled with -nostdlibinc (host stdlib excluded; clang resource dir kept)
 *   - Types come from clang's own stdint.h / stddef.h / stdarg.h
 *   - No POSIX, no threads, no file I/O at runtime
 */
#pragma once

/* ── Pull clang freestanding primitives ──────────────────────────────────── */
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdnoreturn.h>
#include <stdatomic.h>

/* ── Integer limits (C11 requires these in stdint.h with STDC_LIMIT_MACROS) */
#ifndef INT64_MAX
#  define INT64_MAX  9223372036854775807LL
#  define INT64_MIN  (-INT64_MAX - 1)
#  define UINT64_MAX 18446744073709551615ULL
#  define INT32_MAX  2147483647
#  define INT32_MIN  (-INT32_MAX - 1)
#  define UINT32_MAX 4294967295U
#endif
#ifndef INT_MAX
#  define INT_MAX  2147483647
#  define INT_MIN  (-INT_MAX - 1)
#  define UINT_MAX 4294967295U
#endif
#ifndef SIZE_MAX
#  define SIZE_MAX ((size_t)-1)
#endif
#ifndef LLONG_MAX
#  define LLONG_MAX  9223372036854775807LL
#  define LLONG_MIN  (-LLONG_MAX - 1)
#  define ULLONG_MAX 18446744073709551615ULL
#endif
#define DBL_MAX 1.7976931348623157e+308
#define DBL_MIN 2.2250738585072014e-308
#define FLT_MAX 3.40282347e+38F

/* ── NULL / bool if not already defined ──────────────────────────────────── */
#ifndef NULL
#  define NULL ((void*)0)
#endif

/* ── POSIX extras QuickJS expects ────────────────────────────────────────── */
typedef long long ssize_t;

/* malloc_usable_size: return 0 (conservative — no block metadata available) */
static inline size_t malloc_usable_size(void *p) { (void)p; return 0; }

/* ── inttypes.h macros ───────────────────────────────────────────────────── */
#ifndef PRId64
#  define PRId8   "d"
#  define PRId16  "d"
#  define PRId32  "d"
#  define PRId64  "lld"
#  define PRIu8   "u"
#  define PRIu16  "u"
#  define PRIu32  "u"
#  define PRIu64  "llu"
#  define PRIx8   "x"
#  define PRIx16  "x"
#  define PRIx32  "x"
#  define PRIx64  "llx"
#  define PRIX64  "llX"
#  define SCNd64  "lld"
#  define SCNu64  "llu"
#endif

/* ── Allocator (backed by kernel heap) ───────────────────────────────────── */

void *djinnos_alloc(size_t size);
void  djinnos_free(void *ptr);

static inline void *malloc(size_t n)           { return djinnos_alloc(n); }
static inline void  free(void *p)              { djinnos_free(p); }
static inline void *calloc(size_t n, size_t s) {
    void *p = djinnos_alloc(n * s);
    if (p) { uint8_t *b = p; for (size_t i = 0; i < n*s; i++) b[i] = 0; }
    return p;
}
static inline void *realloc(void *p, size_t n) {
    void *q = djinnos_alloc(n);
    if (q && p) {
        uint8_t *s = (uint8_t*)p, *d = (uint8_t*)q;
        for (size_t i = 0; i < n; i++) d[i] = s[i];
        djinnos_free(p);
    }
    return q;
}

/* ── String / memory ─────────────────────────────────────────────────────── */

static inline size_t strlen(const char *s) {
    size_t n = 0; while (s[n]) n++; return n;
}
static inline void *memcpy(void *d, const void *s, size_t n) {
    uint8_t *dd = (uint8_t*)d; const uint8_t *ss = (const uint8_t*)s;
    for (size_t i = 0; i < n; i++) dd[i] = ss[i]; return d;
}
static inline void *memmove(void *d, const void *s, size_t n) {
    uint8_t *dd = (uint8_t*)d; const uint8_t *ss = (const uint8_t*)s;
    if (dd < ss) for (size_t i = 0;   i < n; i++) dd[i] = ss[i];
    else         for (size_t i = n; i > 0; i--) dd[i-1] = ss[i-1];
    return d;
}
static inline void *memset(void *d, int c, size_t n) {
    uint8_t *dd = (uint8_t*)d;
    for (size_t i = 0; i < n; i++) dd[i] = (uint8_t)c; return d;
}
static inline int memcmp(const void *a, const void *b, size_t n) {
    const uint8_t *aa = (const uint8_t*)a, *bb = (const uint8_t*)b;
    for (size_t i = 0; i < n; i++)
        if (aa[i] != bb[i]) return (int)aa[i] - (int)bb[i];
    return 0;
}
static inline const void *memchr(const void *s, int c, size_t n) {
    const uint8_t *p = (const uint8_t*)s;
    for (size_t i = 0; i < n; i++) if (p[i] == (uint8_t)c) return &p[i];
    return (void*)0;
}
static inline int strcmp(const char *a, const char *b) {
    while (*a && *a == *b) { a++; b++; }
    return (unsigned char)*a - (unsigned char)*b;
}
static inline int strncmp(const char *a, const char *b, size_t n) {
    while (n-- && *a && *a == *b) { a++; b++; }
    return n == (size_t)-1 ? 0 : (unsigned char)*a - (unsigned char)*b;
}
static inline char *strcpy(char *d, const char *s) {
    char *r = d; while ((*d++ = *s++)); return r;
}
static inline char *strncpy(char *d, const char *s, size_t n) {
    char *r = d;
    while (n-- && (*d++ = *s++));
    while (n-- > 0) *d++ = 0;
    return r;
}
static inline char *strcat(char *d, const char *s) {
    char *r = d; while (*d) d++; while ((*d++ = *s++)); return r;
}
static inline char *strncat(char *d, const char *s, size_t n) {
    char *r = d; while (*d) d++;
    while (n-- && (*d++ = *s++)); *d = 0; return r;
}
static inline char *strchr(const char *s, int c) {
    while (*s) { if (*s == (char)c) return (char*)s; s++; }
    return (void*)0;
}
static inline char *strrchr(const char *s, int c) {
    const char *last = 0;
    while (*s) { if (*s == (char)c) last = s; s++; }
    return (char*)last;
}
static inline char *strstr(const char *h, const char *n) {
    size_t nl = strlen(n);
    if (!nl) return (char*)h;
    while (*h) { if (!memcmp(h, n, nl)) return (char*)h; h++; }
    return 0;
}
static inline char *strdup(const char *s) {
    size_t n = strlen(s) + 1;
    char *p = (char*)malloc(n);
    if (p) memcpy(p, s, n);
    return p;
}

/* ── stdio stubs ─────────────────────────────────────────────────────────── */

typedef struct { int _fd; } FILE;
static FILE _stdout_s = {1};
static FILE _stderr_s = {2};
#define stdout (&_stdout_s)
#define stderr (&_stderr_s)
#define EOF    (-1)
#define SEEK_SET 0
#define SEEK_CUR 1
#define SEEK_END 2

static inline int    fprintf(FILE *f, const char *fmt, ...) { (void)f;(void)fmt; return 0; }
static inline int    printf(const char *fmt, ...)            { (void)fmt; return 0; }
static inline int    sprintf(char *s, const char *fmt, ...)  { if(s)*s=0; (void)fmt; return 0; }
static inline int    snprintf(char *s, size_t n, const char *fmt, ...) { if(s&&n)*s=0; (void)fmt; return 0; }
static inline int    vfprintf(FILE *f, const char *fmt, va_list ap)    { (void)f;(void)fmt;(void)ap; return 0; }
static inline int    vsnprintf(char *s, size_t n, const char *fmt, va_list ap) { if(s&&n)*s=0; (void)fmt;(void)ap; return 0; }
static inline int    fflush(FILE *f)             { (void)f; return 0; }
static inline int    fputc(int c, FILE *f)       { (void)c;(void)f; return c; }
static inline int    fputs(const char *s, FILE *f){ (void)s;(void)f; return 0; }
static inline int    fclose(FILE *f)             { (void)f; return 0; }
static inline FILE  *fopen(const char *p, const char *m) { (void)p;(void)m; return 0; }
static inline size_t fread(void *p, size_t s, size_t n, FILE *f) { (void)p;(void)s;(void)n;(void)f; return 0; }
static inline size_t fwrite(const void *p, size_t s, size_t n, FILE *f) { (void)p;(void)s;(void)n;(void)f; return n; }
static inline int    fseek(FILE *f, long o, int w) { (void)f;(void)o;(void)w; return -1; }
static inline long   ftell(FILE *f)              { (void)f; return -1; }
static inline int    ferror(FILE *f)             { (void)f; return 0; }
static inline int    feof(FILE *f)               { (void)f; return 1; }
static inline int    sscanf(const char *s, const char *fmt, ...) { (void)s;(void)fmt; return 0; }
static inline int    putchar(int c)  { (void)c; return c; }
static inline int    puts(const char *s) { (void)s; return 0; }
static inline int    getchar(void)   { return EOF; }

/* ── stdlib extras ───────────────────────────────────────────────────────── */

static inline void   abort(void)   { while(1); }
static inline void   exit(int c)   { (void)c; while(1); }
static inline long   strtol(const char *s, char **e, int b) {
    long n = 0; int neg = 0; (void)b;
    while (*s == ' ') s++;
    if (*s == '-') { neg = 1; s++; } else if (*s == '+') s++;
    while (*s >= '0' && *s <= '9') { n = n*10 + (*s++ - '0'); }
    if (e) *e = (char*)s;
    return neg ? -n : n;
}
static inline unsigned long strtoul(const char *s, char **e, int b) {
    return (unsigned long)strtol(s, e, b);
}
static inline long long strtoll(const char *s, char **e, int b) {
    return (long long)strtol(s, e, b);
}
static inline unsigned long long strtoull(const char *s, char **e, int b) {
    return (unsigned long long)strtol(s, e, b);
}
static inline double strtod(const char *s, char **e) { (void)s; if(e)*e=(char*)s; return 0.0; }
static inline int    atoi(const char *s) { return (int)strtol(s, 0, 10); }
static inline void  *bsearch(const void *k, const void *b, size_t n, size_t s,
                              int (*cmp)(const void*, const void*)) {
    size_t lo = 0, hi = n;
    while (lo < hi) {
        size_t mid = lo + (hi-lo)/2;
        int r = cmp(k, (const char*)b + mid*s);
        if (r == 0) return (void*)((const char*)b + mid*s);
        if (r < 0) hi = mid; else lo = mid+1;
    }
    return 0;
}
static inline void qsort(void *b, size_t n, size_t s,
                          int (*cmp)(const void*, const void*)) {
    /* Insertion sort — adequate for QuickJS's internal use */
    for (size_t i = 1; i < n; i++) {
        for (size_t j = i; j > 0; j--) {
            char *a = (char*)b + (j-1)*s, *bb = (char*)b + j*s;
            if (cmp(a, bb) <= 0) break;
            for (size_t k = 0; k < s; k++) { char t=a[k]; a[k]=bb[k]; bb[k]=t; }
        }
    }
}

/* ── Math ────────────────────────────────────────────────────────────────── */

#define NAN       __builtin_nan("")
#define INFINITY  __builtin_inf()
#define HUGE_VAL  __builtin_inf()
#define M_PI      3.14159265358979323846
#define M_E       2.71828182845904523536
#define M_LN2     0.693147180559945309417
#define M_LN10    2.30258509299404568402
#define M_LOG2E   1.44269504088896340736
#define M_SQRT2   1.41421356237309504880

static inline double fabs(double x)  { return __builtin_fabs(x); }
static inline double floor(double x) { return __builtin_floor(x); }
static inline double ceil(double x)  { return __builtin_ceil(x); }
static inline double fmod(double x, double y) { return __builtin_fmod(x,y); }
static inline double trunc(double x) { return __builtin_trunc(x); }
static inline double round(double x) { return __builtin_round(x); }
static inline double sqrt(double x)  { return __builtin_sqrt(x); }
static inline float  sqrtf(float x)  { return __builtin_sqrtf(x); }
static inline double log(double x)   { return __builtin_log(x); }
static inline double log2(double x)  { return __builtin_log2(x); }
static inline double log10(double x) { return __builtin_log10(x); }
static inline double exp(double x)   { return __builtin_exp(x); }
static inline double exp2(double x)  { return __builtin_exp2(x); }
static inline double pow(double x, double y)  { return __builtin_pow(x,y); }
static inline double sin(double x)   { return __builtin_sin(x); }
static inline double cos(double x)   { return __builtin_cos(x); }
static inline double tan(double x)   { return __builtin_tan(x); }
static inline double asin(double x)  { return __builtin_asin(x); }
static inline double acos(double x)  { return __builtin_acos(x); }
static inline double atan(double x)  { return __builtin_atan(x); }
static inline double atan2(double y, double x) { return __builtin_atan2(y,x); }
static inline double sinh(double x)  { return __builtin_sinh(x); }
static inline double cosh(double x)  { return __builtin_cosh(x); }
static inline double tanh(double x)  { return __builtin_tanh(x); }
static inline double hypot(double x, double y) { return __builtin_hypot(x,y); }
static inline double cbrt(double x)  { return __builtin_cbrt(x); }
static inline long   lrint(double x) { return (long)__builtin_round(x); }
static inline long long llrint(double x) { return (long long)__builtin_round(x); }
static inline double rint(double x)  { return __builtin_rint(x); }
static inline double nearbyint(double x) { return __builtin_nearbyint(x); }
static inline double copysign(double x, double y) { return __builtin_copysign(x,y); }
static inline double scalbn(double x, int n)  { return __builtin_scalbn(x,n); }
static inline double scalbln(double x, long n){ return __builtin_scalbln(x,n); }
static inline double ldexp(double x, int n)   { return __builtin_ldexp(x,n); }
static inline double frexp(double x, int *e)  { return __builtin_frexp(x,e); }
static inline double modf(double x, double *i){ return __builtin_modf(x,i); }
static inline int isnan(double x)    { return __builtin_isnan(x); }
static inline int isinf(double x)    { return __builtin_isinf(x); }
static inline int isfinite(double x) { return __builtin_isfinite(x); }
static inline int signbit(double x)  { return __builtin_signbit(x); }
static inline double fma(double x, double y, double z) { return __builtin_fma(x,y,z); }

/* ── alloca ──────────────────────────────────────────────────────────────── */
#define alloca __builtin_alloca

/* ── More math (hyperbolic, exponential) ─────────────────────────────────── */
static inline double fmin(double a, double b) { return a < b ? a : b; }
static inline double fmax(double a, double b) { return a > b ? a : b; }
static inline float  fminf(float a, float b)  { return a < b ? a : b; }
static inline float  fmaxf(float a, float b)  { return a > b ? a : b; }
static inline double acosh(double x) { return log(x + sqrt(x*x-1.0)); }
static inline double asinh(double x) { return log(x + sqrt(x*x+1.0)); }
static inline double atanh(double x) { return 0.5*log((1.0+x)/(1.0-x)); }
static inline double expm1(double x) { return exp(x) - 1.0; }
static inline double log1p(double x) { return log(1.0 + x); }

/* ── Floating-point environment ──────────────────────────────────────────── */
#define FE_TONEAREST  0
#define FE_UPWARD     1
#define FE_DOWNWARD   2
#define FE_TOWARDZERO 3
static inline int fesetround(int r)  { (void)r; return 0; }
static inline int fegetround(void)   { return FE_TONEAREST; }

/* ── time / calendar ────────────────────────────────────────────────────── */
typedef long long time_t;
struct timespec { time_t tv_sec; long tv_nsec; };
#define ETIMEDOUT 110
#define CLOCK_REALTIME  0
#define CLOCK_MONOTONIC 1
static inline int clock_gettime(int clk, struct timespec *ts) {
    (void)clk; if(ts){ts->tv_sec=0;ts->tv_nsec=0;} return 0;
}
struct tm {
    int tm_sec, tm_min, tm_hour;
    int tm_mday, tm_mon, tm_year;
    int tm_wday, tm_yday, tm_isdst;
    long tm_gmtoff;
    const char *tm_zone;
};
static inline struct tm *localtime_r(const time_t *t, struct tm *r) {
    (void)t; if(r) { *r = (struct tm){0}; } return r;
}
static inline struct tm *gmtime_r(const time_t *t, struct tm *r) {
    return localtime_r(t, r);
}
static inline time_t mktime(struct tm *t) { (void)t; return 0; }

/* ── QuickJS requires CONFIG_VERSION to be defined ───────────────────────── */
#ifndef CONFIG_VERSION
#  define CONFIG_VERSION "djinnos"
#endif

/* ── assert ──────────────────────────────────────────────────────────────── */
#undef assert
#define assert(x) ((void)(x))
#define NDEBUG 1

/* ── errno ───────────────────────────────────────────────────────────────── */
static int _djinn_errno = 0;
#define errno _djinn_errno
#ifndef EINVAL
#  define EINVAL  22
#  define ENOMEM  12
#  define ERANGE  34
#  define ENOENT   2
#  define EBADF    9
#  define ENOSYS  38
#endif

/* ── ctype ───────────────────────────────────────────────────────────────── */
static inline int isdigit(int c)  { return c >= '0' && c <= '9'; }
static inline int isalpha(int c)  { return (c>='a'&&c<='z')||(c>='A'&&c<='Z'); }
static inline int isalnum(int c)  { return isalpha(c)||isdigit(c); }
static inline int isspace(int c)  { return c==' '||c=='\t'||c=='\n'||c=='\r'||c=='\f'||c=='\v'; }
static inline int isupper(int c)  { return c >= 'A' && c <= 'Z'; }
static inline int islower(int c)  { return c >= 'a' && c <= 'z'; }
static inline int isprint(int c)  { return c >= 0x20 && c < 0x7F; }
static inline int isxdigit(int c) { return isdigit(c)||(c>='a'&&c<='f')||(c>='A'&&c<='F'); }
static inline int toupper(int c)  { return islower(c) ? c-32 : c; }
static inline int tolower(int c)  { return isupper(c) ? c+32 : c; }

/* ── time ────────────────────────────────────────────────────────────────── */
/* time_t already defined above for struct tm */
typedef long long clock_t;
#define CLOCKS_PER_SEC 1000000LL
struct timeval { time_t tv_sec; long tv_usec; };
static inline time_t  time(time_t *t)   { if(t)*t=0; return 0; }
static inline clock_t clock(void)       { return 0; }
static inline int gettimeofday(struct timeval *tv, void *tz) {
    (void)tz; if(tv){tv->tv_sec=0;tv->tv_usec=0;} return 0;
}

/* ── Threading stubs ─────────────────────────────────────────────────────── */
typedef int pthread_mutex_t;
typedef int pthread_mutexattr_t;
typedef int pthread_t;
typedef int pthread_attr_t;
typedef int pthread_cond_t;
typedef int pthread_condattr_t;
typedef int pthread_rwlock_t;
#define PTHREAD_MUTEX_INITIALIZER 0
#define PTHREAD_COND_INITIALIZER  0
static inline int pthread_mutex_init(pthread_mutex_t *m, const pthread_mutexattr_t *a) { (void)m;(void)a; return 0; }
static inline int pthread_mutex_lock(pthread_mutex_t *m)    { (void)m; return 0; }
static inline int pthread_mutex_unlock(pthread_mutex_t *m)  { (void)m; return 0; }
static inline int pthread_mutex_destroy(pthread_mutex_t *m) { (void)m; return 0; }
static inline int pthread_create(pthread_t *t, const pthread_attr_t *a, void*(*fn)(void*), void *arg) {
    (void)t;(void)a;(void)fn;(void)arg; return -1;
}
static inline int pthread_join(pthread_t t, void **r) { (void)t;(void)r; return -1; }
static inline int pthread_cond_init(pthread_cond_t *c, const pthread_condattr_t *a) { (void)c;(void)a; return 0; }
static inline int pthread_cond_destroy(pthread_cond_t *c)                      { (void)c; return 0; }
static inline int pthread_cond_signal(pthread_cond_t *c)                       { (void)c; return 0; }
static inline int pthread_cond_broadcast(pthread_cond_t *c)                    { (void)c; return 0; }
static inline int pthread_cond_wait(pthread_cond_t *c, pthread_mutex_t *m)     { (void)c;(void)m; return 0; }
static inline int pthread_cond_timedwait(pthread_cond_t *c, pthread_mutex_t *m,
                                         const struct timespec *ts)            { (void)c;(void)m;(void)ts; return ETIMEDOUT; }
static inline int pthread_rwlock_init(pthread_rwlock_t *l, void *a)            { (void)l;(void)a; return 0; }
static inline int pthread_rwlock_rdlock(pthread_rwlock_t *l)                   { (void)l; return 0; }
static inline int pthread_rwlock_wrlock(pthread_rwlock_t *l)                   { (void)l; return 0; }
static inline int pthread_rwlock_unlock(pthread_rwlock_t *l)                   { (void)l; return 0; }
static inline int pthread_rwlock_destroy(pthread_rwlock_t *l)                  { (void)l; return 0; }

/* ── setjmp/longjmp (QuickJS exception handling) ─────────────────────────── */
/* Declared but not defined — QuickJS exception path won't be hit in our use */
typedef struct { uint64_t _buf[8]; } jmp_buf[1];
int  setjmp(jmp_buf env);
noreturn void longjmp(jmp_buf env, int val);
