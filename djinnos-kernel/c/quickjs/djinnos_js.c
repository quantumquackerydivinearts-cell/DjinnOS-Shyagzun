/*
 * djinnos_js.c -- Faerie JavaScript engine (QuickJS) integration.
 *
 * Provides two entry points callable from Rust via the C API:
 *
 *   int  djinnos_js_eval(const char *src, size_t len,
 *                        char *out, size_t out_cap);
 *
 *     Evaluate JS source `src` in a fresh runtime context.
 *     Writes the string representation of the result into `out`
 *     (null-terminated, truncated at out_cap-1).
 *     Returns 0 on success, -1 on error (error string in out).
 *
 *   int  djinnos_js_eval_dom(const char *script, size_t len,
 *                            char *html_out, size_t html_cap);
 *
 *     Like djinnos_js_eval but the JS context has a minimal DOM:
 *       document.write(s)   -- accumulate HTML output
 *       document.title      -- writable string
 *     After eval the accumulated HTML is written into html_out.
 *     Returns 0 on success, -1 on error.
 *
 * Build: compiled by build.rs as part of the djinnos C archive.
 *        Configured with CONFIG_BIGNUM=0, no POSIX file I/O.
 */

#include "djinnos_port.h"

/* QuickJS — include the amalgam after our port layer so it sees our stubs. */
#define CONFIG_VERSION "djinnos-2024-01-13"
#define JS_STRICT_NAN_BOXING 0
/* Disable features we can't support in freestanding: */
#define CONFIG_PRINTF_RNDU 0

#include "quickjs.h"

/* ── Shared static runtime ──────────────────────────────────────────────── */
/* We use a single long-lived runtime to amortise init cost.  Each eval
   runs in a fresh context so globals don't leak between calls. */

static JSRuntime *_rt = NULL;

static JSRuntime *get_rt(void) {
    if (!_rt) {
        _rt = JS_NewRuntime();
        if (_rt) {
            JS_SetMemoryLimit(_rt, 2 * 1024 * 1024);  /* 2 MiB JS heap */
            JS_SetMaxStackSize(_rt, 256 * 1024);       /* 256 KiB stack */
        }
    }
    return _rt;
}

/* ── Helper: stringify a JS value into out ─────────────────────────────── */

static int val_to_str(JSContext *ctx, JSValue v, char *out, size_t cap) {
    if (JS_IsException(v)) {
        JSValue ex = JS_GetException(ctx);
        const char *s = JS_ToCString(ctx, ex);
        if (s) {
            size_t n = strlen(s);
            if (n >= cap) n = cap - 1;
            memcpy(out, s, n); out[n] = 0;
            JS_FreeCString(ctx, s);
        } else {
            memcpy(out, "exception", 9); out[9] = 0;
        }
        JS_FreeValue(ctx, ex);
        return -1;
    }
    const char *s = JS_ToCString(ctx, v);
    if (s) {
        size_t n = strlen(s);
        if (n >= cap) n = cap - 1;
        memcpy(out, s, n); out[n] = 0;
        JS_FreeCString(ctx, s);
    } else {
        out[0] = 0;
    }
    return 0;
}

/* ── Plain eval ────────────────────────────────────────────────────────── */

int djinnos_js_eval(const char *src, size_t len,
                    char *out, size_t out_cap) {
    if (!src || !out || out_cap == 0) return -1;
    out[0] = 0;

    JSRuntime *rt = get_rt();
    if (!rt) { memcpy(out, "no runtime", 10); out[10] = 0; return -1; }

    JSContext *ctx = JS_NewContext(rt);
    if (!ctx) { memcpy(out, "no context", 10); out[10] = 0; return -1; }

    JSValue v = JS_Eval(ctx, src, len, "<faerie>", JS_EVAL_TYPE_GLOBAL);
    int rc = val_to_str(ctx, v, out, out_cap);
    JS_FreeValue(ctx, v);
    JS_FreeContext(ctx);
    return rc;
}

/* ── DOM-lite eval ─────────────────────────────────────────────────────── */

/* Backing store for document.write output — static, no heap alloc needed. */
static char   _dom_buf[4096];
static size_t _dom_pos;

static JSValue js_document_write(JSContext *ctx, JSValue this_val,
                                 int argc, JSValue *argv) {
    (void)this_val;
    if (argc < 1) return JS_UNDEFINED;
    const char *s = JS_ToCString(ctx, argv[0]);
    if (s) {
        size_t n = strlen(s);
        if (_dom_pos + n < sizeof(_dom_buf) - 1) {
            memcpy(_dom_buf + _dom_pos, s, n);
            _dom_pos += n;
        }
        JS_FreeCString(ctx, s);
    }
    return JS_UNDEFINED;
}

static void setup_dom(JSContext *ctx) {
    JSValue global = JS_GetGlobalObject(ctx);

    /* document object */
    JSValue doc = JS_NewObject(ctx);

    /* document.write(s) */
    JS_SetPropertyStr(ctx, doc, "write",
        JS_NewCFunction(ctx, js_document_write, "write", 1));

    /* document.title — writable string property, initially "" */
    JS_SetPropertyStr(ctx, doc, "title", JS_NewString(ctx, ""));

    JS_SetPropertyStr(ctx, global, "document", doc);
    JS_FreeValue(ctx, global);
    JS_FreeValue(ctx, doc);
}

int djinnos_js_eval_dom(const char *script, size_t len,
                        char *html_out, size_t html_cap) {
    if (!script || !html_out || html_cap == 0) return -1;
    html_out[0] = 0;
    _dom_buf[0] = 0;
    _dom_pos    = 0;

    JSRuntime *rt = get_rt();
    if (!rt) { memcpy(html_out, "no runtime", 10); html_out[10] = 0; return -1; }

    JSContext *ctx = JS_NewContext(rt);
    if (!ctx) { memcpy(html_out, "no context", 10); html_out[10] = 0; return -1; }

    setup_dom(ctx);

    JSValue v = JS_Eval(ctx, script, len, "<faerie>", JS_EVAL_TYPE_GLOBAL);
    int rc = 0;
    if (JS_IsException(v)) {
        /* Eval error — put error in html_out */
        JSValue ex = JS_GetException(ctx);
        const char *s = JS_ToCString(ctx, ex);
        if (s) {
            size_t n = strlen(s);
            if (n >= html_cap) n = html_cap - 1;
            memcpy(html_out, s, n); html_out[n] = 0;
            JS_FreeCString(ctx, s);
        }
        JS_FreeValue(ctx, ex);
        rc = -1;
    } else {
        /* Copy accumulated document.write output */
        size_t n = _dom_pos;
        if (n >= html_cap) n = html_cap - 1;
        memcpy(html_out, _dom_buf, n);
        html_out[n] = 0;
    }

    JS_FreeValue(ctx, v);
    JS_FreeContext(ctx);
    return rc;
}
