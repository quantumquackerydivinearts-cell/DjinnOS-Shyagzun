/*
 * stream_platform.c — DjinnOS streaming platform kernel module.
 *
 * Runs inside the kernel and is served over HTTP at /api/stream/*.
 * Uses QCR (Queried Collapse Routing) for stream discovery: each stream
 * carries byte-table coordinates; the Hopfield network finds the attractor
 * nearest the query, and streams whose coordinates overlap are returned.
 *
 * QQEES integration: each active session emits entropy ticks through the
 * djinnos_entropy_tick() callback exposed from qqees.rs.
 *
 * HTTP routes (handled by djinnos_stream_handle_http):
 *   POST   /api/stream/register     register a new stream
 *   DELETE /api/stream/:id          unregister
 *   GET    /api/stream/list         list all active streams (JSON)
 *   POST   /api/stream/discover     QCR query → matching streams (JSON)
 *   POST   /api/stream/:id/tick     contribute entropy for this session
 */

#include <djinnos.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>

/* ── Stream registry ─────────────────────────────────────────────────────────── */

#define MAX_STREAMS 32

static DjinnStream  g_streams[MAX_STREAMS];
static uint32_t     g_count = 0;

/* ── Minimal JSON builder ─────────────────────────────────────────────────── */

static size_t jstr(char *buf, size_t cap, size_t off, const char *s)
{
    size_t i = 0;
    while (s[i] && off < cap) { buf[off++] = s[i++]; }
    return off;
}

static size_t ju16(char *buf, size_t cap, size_t off, uint16_t v)
{
    char tmp[6]; int n = 0;
    if (v == 0) { tmp[n++] = '0'; }
    else { uint16_t x = v; while (x) { tmp[n++] = '0' + (x % 10); x /= 10; } }
    /* reverse */
    for (int l = 0, r = n-1; l < r; l++, r--) { char t = tmp[l]; tmp[l] = tmp[r]; tmp[r] = t; }
    for (int i = 0; i < n && off < cap; i++) buf[off++] = tmp[i];
    return off;
}

/* Serialise a DjinnStream to JSON object string.  Returns new offset. */
static size_t stream_to_json(const DjinnStream *s, char *buf, size_t cap, size_t off)
{
    off = jstr(buf, cap, off, "{\"id\":\"");
    off = jstr(buf, cap, off, s->id);
    off = jstr(buf, cap, off, "\",\"label\":\"");
    off = jstr(buf, cap, off, s->label);
    off = jstr(buf, cap, off, "\",\"coords\":[");
    for (uint8_t i = 0; i < s->n_coords; i++) {
        if (i > 0 && off < cap) buf[off++] = ',';
        off = ju16(buf, cap, off, s->coords[i]);
    }
    off = jstr(buf, cap, off, "]}");
    return off;
}

/* ── Public API ──────────────────────────────────────────────────────────────── */

int djinnos_stream_register(const DjinnStream *s)
{
    if (!s || g_count >= MAX_STREAMS) return -1;
    /* Overwrite existing stream with the same ID. */
    for (uint32_t i = 0; i < g_count; i++) {
        if (memcmp(g_streams[i].id, s->id, STREAM_ID_LEN) == 0) {
            g_streams[i] = *s;
            g_streams[i].active = 1;
            return 0;
        }
    }
    g_streams[g_count] = *s;
    g_streams[g_count].active = 1;
    g_count++;
    return 0;
}

int djinnos_stream_unregister(const char *id)
{
    for (uint32_t i = 0; i < g_count; i++) {
        if (memcmp(g_streams[i].id, id, STREAM_ID_LEN) == 0) {
            /* Swap with last and shrink. */
            g_streams[i] = g_streams[g_count - 1];
            g_count--;
            return 0;
        }
    }
    return -1;
}

int djinnos_stream_discover(
    const uint8_t     *tongues,
    size_t             n_tongues,
    const DjinnStream **out,
    size_t            *out_n,
    size_t             capacity)
{
    if (!tongues || !out || !out_n) return -1;

    /* Run QCR: collapse the Hopfield network over the query tongues. */
    static uint16_t attractor[256];
    size_t n_attractor = 0;

    int rc = djinnos_query_by_tongue(
        tongues, n_tongues,
        DJINN_GIANN, 0.0f,
        attractor, &n_attractor, 256
    );
    if (rc != 0) { *out_n = 0; return rc; }

    /* Return streams whose coordinate sets intersect the attractor. */
    size_t found = 0;
    for (uint32_t i = 0; i < g_count && found < capacity; i++) {
        const DjinnStream *s = &g_streams[i];
        if (!s->active) continue;
        for (uint8_t ci = 0; ci < s->n_coords; ci++) {
            int hit = 0;
            for (size_t ai = 0; ai < n_attractor; ai++) {
                if (s->coords[ci] == attractor[ai]) { hit = 1; break; }
            }
            if (hit) { out[found++] = s; break; }
        }
    }
    *out_n = found;
    return 0;
}

/* ── Entropy tick (QQEES integration) ───────────────────────────────────────── */
/* Rust symbol from qqees.rs — contributes a timing entropy tick. */
extern void djinnos_entropy_tick(const char *source_id, uint64_t value);

static void emit_entropy(const char *stream_id)
{
    /* Use the kernel tick counter as entropy value. */
    extern uint64_t djinnos_read_ticks(void);
    djinnos_entropy_tick(stream_id, djinnos_read_ticks());
}

/* ── HTTP handler ─────────────────────────────────────────────────────────── */

/* Parse the last path component after /api/stream/ into id_out.
   Returns pointer past the component, or NULL. */
static const char *parse_stream_id(const char *path, char *id_out, size_t cap)
{
    /* path example: /api/stream/my-stream-id */
    const char *p = path;
    /* skip prefix */
    while (*p && *p != '/' ) p++;         /* skip empty leading / */
    if (*p == '/') p++;                   /* skip first / */
    while (*p && *p != '/') p++;          /* skip "api" */
    if (*p == '/') p++;
    while (*p && *p != '/') p++;          /* skip "stream" */
    if (*p == '/') p++;
    size_t i = 0;
    while (*p && *p != '/' && i < cap - 1) id_out[i++] = *p++;
    id_out[i] = '\0';
    return i > 0 ? p : (const char *)0;
}

/* Tiny JSON field extractor: find "key":"value" in a flat JSON object.
   Writes value into val_out (null-terminated), returns 1 on success. */
static int json_get_str(const char *json, const char *key,
                        char *val_out, size_t cap)
{
    /* Find "key" in json. */
    size_t klen = strlen(key);
    const char *p = json;
    while (*p) {
        /* Look for "key" */
        if (*p == '"') {
            const char *q = p + 1;
            size_t i = 0;
            while (*q && *q != '"' && i < klen) { if (*q != key[i]) break; q++; i++; }
            if (i == klen && *q == '"') {
                /* key matched — skip ": " and extract value */
                q++;
                while (*q == ':' || *q == ' ') q++;
                if (*q == '"') {
                    q++;
                    size_t vi = 0;
                    while (*q && *q != '"' && vi < cap - 1) val_out[vi++] = *q++;
                    val_out[vi] = '\0';
                    return 1;
                }
            }
        }
        p++;
    }
    return 0;
}

/* Parse "coords":[n,n,...] from JSON into coords[] array. */
static uint8_t json_get_coords(const char *json,
                               uint16_t *coords, uint8_t max_coords)
{
    const char *p = json;
    /* Find "coords":[ */
    while (*p && !(p[0]=='c' && p[1]=='o' && p[2]=='o' && p[3]=='r')) p++;
    while (*p && *p != '[') p++;
    if (!*p) return 0;
    p++; /* skip [ */
    uint8_t n = 0;
    while (*p && *p != ']' && n < max_coords) {
        while (*p == ' ' || *p == ',') p++;
        if (*p == ']') break;
        uint16_t v = 0;
        while (*p >= '0' && *p <= '9') { v = v * 10 + (*p++ - '0'); }
        coords[n++] = v;
    }
    return n;
}

/* Parse tongue array "tongues":[n,...] from JSON. */
static size_t json_get_tongues(const char *json,
                               uint8_t *tongues, size_t max_t)
{
    const char *p = json;
    while (*p && !(p[0]=='t' && p[1]=='o' && p[2]=='n' && p[3]=='g')) p++;
    while (*p && *p != '[') p++;
    if (!*p) return 0;
    p++;
    size_t n = 0;
    while (*p && *p != ']' && n < max_t) {
        while (*p == ' ' || *p == ',') p++;
        if (*p == ']') break;
        uint8_t v = 0;
        while (*p >= '0' && *p <= '9') { v = (uint8_t)(v * 10 + (*p++ - '0')); }
        tongues[n++] = v;
    }
    return n;
}

/* Write a minimal HTTP/1.0 response into resp_buf. */
static size_t http_resp(char *buf, size_t cap, int status,
                        const char *body, size_t body_len)
{
    const char *status_str = (status == 200) ? "200 OK" :
                             (status == 201) ? "201 Created" :
                             (status == 404) ? "404 Not Found" :
                                               "400 Bad Request";
    size_t off = 0;
    off = jstr(buf, cap, off, "HTTP/1.0 ");
    off = jstr(buf, cap, off, status_str);
    off = jstr(buf, cap, off,
               "\r\nContent-Type: application/json\r\n"
               "Connection: close\r\n\r\n");
    size_t copy = (body_len < cap - off) ? body_len : cap - off - 1;
    if (body && copy > 0) {
        memcpy(buf + off, body, copy);
        off += copy;
    }
    if (off < cap) buf[off] = '\0';
    return off;
}

size_t djinnos_stream_handle_http(
    const char *method,
    const char *path,
    const char *body,
    size_t      body_len,
    char       *resp_buf,
    size_t      resp_cap)
{
    static char json_body[4096];
    size_t joff = 0;

    (void)body_len;

    /* ── POST /api/stream/register ── */
    if (memcmp(method, "POST", 4) == 0 &&
        memcmp(path, "/api/stream/register", 20) == 0)
    {
        DjinnStream s;
        memset(&s, 0, sizeof s);
        json_get_str(body, "id",    s.id,    STREAM_ID_LEN);
        json_get_str(body, "label", s.label, STREAM_LABEL_LEN);
        s.n_coords = json_get_coords(body, s.coords, STREAM_MAX_COORDS);
        if (s.id[0] == '\0') {
            const char *e = "{\"error\":\"id required\"}";
            return http_resp(resp_buf, resp_cap, 400, e, strlen(e));
        }
        int rc = djinnos_stream_register(&s);
        emit_entropy(s.id);
        const char *ok = rc == 0 ? "{\"ok\":true}" : "{\"error\":\"registry full\"}";
        return http_resp(resp_buf, resp_cap, rc == 0 ? 201 : 400, ok, strlen(ok));
    }

    /* ── DELETE /api/stream/:id ── */
    if (memcmp(method, "DELETE", 6) == 0 &&
        memcmp(path, "/api/stream/", 12) == 0)
    {
        char id[STREAM_ID_LEN] = {0};
        parse_stream_id(path, id, STREAM_ID_LEN);
        int rc = djinnos_stream_unregister(id);
        const char *resp = rc == 0 ? "{\"ok\":true}" : "{\"error\":\"not found\"}";
        return http_resp(resp_buf, resp_cap, rc == 0 ? 200 : 404, resp, strlen(resp));
    }

    /* ── GET /api/stream/list ── */
    if (memcmp(method, "GET", 3) == 0 &&
        memcmp(path, "/api/stream/list", 16) == 0)
    {
        joff = jstr(json_body, sizeof json_body, 0, "{\"streams\":[");
        for (uint32_t i = 0; i < g_count; i++) {
            if (i > 0) json_body[joff++] = ',';
            joff = stream_to_json(&g_streams[i], json_body, sizeof json_body, joff);
        }
        joff = jstr(json_body, sizeof json_body, joff, "]}");
        return http_resp(resp_buf, resp_cap, 200, json_body, joff);
    }

    /* ── POST /api/stream/discover ── */
    if (memcmp(method, "POST", 4) == 0 &&
        memcmp(path, "/api/stream/discover", 20) == 0)
    {
        uint8_t tongues[16];
        size_t  n_tongues = json_get_tongues(body, tongues, 16);
        if (n_tongues == 0) {
            const char *e = "{\"error\":\"tongues required\"}";
            return http_resp(resp_buf, resp_cap, 400, e, strlen(e));
        }
        static const DjinnStream *matches[32];
        size_t n_matches = 0;
        djinnos_stream_discover(tongues, n_tongues, matches, &n_matches, 32);

        joff = jstr(json_body, sizeof json_body, 0, "{\"streams\":[");
        for (size_t i = 0; i < n_matches; i++) {
            if (i > 0) json_body[joff++] = ',';
            joff = stream_to_json(matches[i], json_body, sizeof json_body, joff);
        }
        joff = jstr(json_body, sizeof json_body, joff, "]}");
        return http_resp(resp_buf, resp_cap, 200, json_body, joff);
    }

    /* ── POST /api/stream/:id/tick (entropy contribution) ── */
    if (memcmp(method, "POST", 4) == 0 &&
        memcmp(path, "/api/stream/", 12) == 0)
    {
        char id[STREAM_ID_LEN] = {0};
        parse_stream_id(path, id, STREAM_ID_LEN);
        if (id[0]) emit_entropy(id);
        const char *ok = "{\"ok\":true}";
        return http_resp(resp_buf, resp_cap, 200, ok, strlen(ok));
    }

    const char *e = "{\"error\":\"unknown route\"}";
    return http_resp(resp_buf, resp_cap, 404, e, strlen(e));
}
