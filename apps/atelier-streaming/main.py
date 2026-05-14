"""
apps/atelier-streaming — DjinnOS streaming platform bridge.

Bridges the DjinnOS kernel's C streaming module, MediaMTX media server,
BoK trajectory tracking, Roko assessment, and QQEES entropy to the
Atelier desktop's broadcaster control room.

Ports:
  7800  REST API (CORS-open, consumed by Atelier desktop at port 5173)
  7801  WebSocket (live resonance markers → Atelier + stream.html)

Public-facing (stream.quantumquackery.com):
  Stream relay (apps/stream-relay/) handles WebSocket viewer protocol
  MediaMTX handles RTMP ingest + HLS/WebRTC output

Environment:
  MEDIAMTX_API   MediaMTX REST API (default http://localhost:9997)
  ATELIER_API    Atelier API base (default http://127.0.0.1:9000)
  KERNEL_HTTP    DjinnOS kernel HTTP (default http://10.0.2.15)
  REQUIRE_AUTH   enforce Atelier auth (default false)
  HLS_BASE       HLS output base URL
  RTMP_BASE      RTMP ingest base URL
  WEBRTC_BASE    WebRTC WHEP base URL
"""

import asyncio
import json
import os
import time

import aiohttp
from aiohttp import web

import mediamtx
import bok as bok_mod

KERNEL_HTTP  = os.getenv("KERNEL_HTTP",  "http://10.0.2.15")
ATELIER_API  = os.getenv("ATELIER_API",  "http://127.0.0.1:9000")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

# ── Auth ──────────────────────────────────────────────────────────────────────

async def validate_token(token: str) -> dict | None:
    if not REQUIRE_AUTH:
        return {"artisan_id": "dev", "role": "steward"}
    if not token:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{ATELIER_API}/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                return await r.json() if r.status == 200 else None
    except Exception:
        return None


def bearer(req: web.Request) -> str:
    return req.headers.get("Authorization", "").removeprefix("Bearer ").strip()


def cors(resp: web.Response) -> web.Response:
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return resp


def j(data, status: int = 200) -> web.Response:
    return cors(web.json_response(data, status=status))


# ── WebSocket broadcast ───────────────────────────────────────────────────────

_ws_clients: set[web.WebSocketResponse] = set()


async def broadcast_ws(msg: dict) -> None:
    payload = json.dumps(msg)
    for ws in list(_ws_clients):
        try:
            await ws.send_str(payload)
        except Exception:
            _ws_clients.discard(ws)


# ── Kernel proxy ──────────────────────────────────────────────────────────────

async def kernel_post(path: str, payload: dict) -> dict:
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{KERNEL_HTTP}{path}", json=payload,
                          timeout=aiohttp.ClientTimeout(total=5)) as r:
            return await r.json()


# ── Route handlers ────────────────────────────────────────────────────────────

async def health(req: web.Request) -> web.Response:
    return j({"ok": True, "ts": time.time()})


async def stream_start(req: web.Request) -> web.Response:
    """POST /streams — register stream, create MediaMTX path, get RTMP key."""
    token = bearer(req)
    user  = await validate_token(token)
    if user is None:
        return j({"error": "unauthorized"}, 401)

    body       = await req.json()
    artisan_id = user.get("artisan_id", "unknown")
    stream_id  = body.get("id") or f"{artisan_id}-{int(time.time())}"
    key        = mediamtx.generate_key(artisan_id)

    # Register with MediaMTX
    await mediamtx.create_path(key)

    # Register with DjinnOS kernel C module
    try:
        await kernel_post("/api/stream/register", {
            "id":     stream_id,
            "label":  body.get("label", stream_id),
            "coords": body.get("coords", []),
        })
    except Exception:
        pass

    # Create BoK session
    bok_mod.create_session(stream_id, artisan_id)

    return j({
        "ok":      True,
        "id":      stream_id,
        "key":     key,
        "rtmp":    mediamtx.rtmp_url(key),
        "hls":     mediamtx.hls_url(key),
        "webrtc":  mediamtx.webrtc_url(key),
    }, 201)


async def stream_key(req: web.Request) -> web.Response:
    """GET /streams/:id/key — re-fetch the RTMP key for an existing session."""
    sid  = req.match_info["stream_id"]
    s    = bok_mod.get_session(sid)
    if not s:
        return j({"error": "session not found"}, 404)
    # Key is derivable from artisan + stream id; return a placeholder
    # (real impl would store key in session)
    return j({"key": sid, "rtmp": mediamtx.rtmp_url(sid)})


async def stream_status(req: web.Request) -> web.Response:
    """GET /streams/:id/status — MediaMTX live check."""
    sid   = req.match_info["stream_id"]
    s     = bok_mod.get_session(sid)
    live  = await mediamtx.is_path_active(sid)
    views = await mediamtx.reader_count(sid)
    return j({
        "id":           sid,
        "live":         live,
        "viewers":      views,
        "entropy_ticks": s.entropy_ticks if s else 0,
    })


async def stream_bok(req: web.Request) -> web.Response:
    """POST /streams/:id/bok — submit a BoK transition point."""
    sid  = req.match_info["stream_id"]
    body = await req.json()
    re   = float(body.get("re", -0.7))
    im   = float(body.get("im",  0.27))
    session = bok_mod.add_point(sid, re, im)

    # Contribute to QQEES entropy via kernel
    try:
        await kernel_post(f"/api/stream/{sid}/tick", {})
    except Exception:
        pass

    # Broadcast BoK update to WebSocket viewers
    await broadcast_ws({"type": "bok_update", "stream_id": sid, "re": re, "im": im})

    return j({"ok": True, "ticks": session.entropy_ticks if session else 0})


async def stream_end(req: web.Request) -> web.Response:
    """POST /streams/:id/end — end session, assess, return summary."""
    sid   = req.match_info["stream_id"]
    token = bearer(req)
    _     = await validate_token(token)

    summary = await bok_mod.assess_session(sid)

    # Remove from kernel registry
    try:
        await kernel_post(f"/api/stream/{sid}/end", {})
    except Exception:
        pass

    # Remove MediaMTX path
    await mediamtx.delete_path(sid)

    # Broadcast session-end event to WS
    await broadcast_ws({"type": "session_ended", "stream_id": sid, "summary": summary})

    bok_mod.cleanup(sid)

    return j({"ok": True, "summary": summary})


async def stream_list(req: web.Request) -> web.Response:
    """GET /streams — proxy kernel stream list."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{KERNEL_HTTP}/api/stream/list",
                             timeout=aiohttp.ClientTimeout(total=3)) as r:
                data = await r.json()
        return j(data)
    except Exception:
        return j({"streams": []})


async def stream_discover(req: web.Request) -> web.Response:
    """POST /discover — QCR routing via kernel Hopfield + MediaMTX live filter."""
    body    = await req.json()
    tongues = body.get("tongues", [])
    mode    = body.get("mode", "giann")
    temp    = float(body.get("temp", 1.0))

    # QCR via kernel
    try:
        data = await kernel_post("/api/stream/discover", {
            "tongues": tongues, "mode": mode, "temp": temp,
        })
    except Exception:
        data = {"streams": []}

    # Annotate each stream with MediaMTX live status
    annotated = []
    for s in data.get("streams", []):
        live = await mediamtx.is_path_active(s.get("id", ""))
        annotated.append({**s, "live": live})

    return j({"streams": annotated})


async def resonance_marker(req: web.Request) -> web.Response:
    """POST /streams/:id/resonate — viewer drops a resonance marker."""
    sid  = req.match_info["stream_id"]
    body = await req.json()
    marker = {
        "stream_id":  sid,
        "artisan_id": body.get("artisan_id", "viewer"),
        "ts":         body.get("ts", time.time()),
        "bok":        body.get("bok"),
        "note":       body.get("note", ""),
    }
    await broadcast_ws({"type": "resonance_marker", **marker})
    return j({"ok": True})


async def ws_handler(req: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(req)
    _ws_clients.add(ws)
    try:
        async for _msg in ws:
            pass
    finally:
        _ws_clients.discard(ws)
    return ws


async def options_handler(req: web.Request) -> web.Response:
    return cors(web.Response(status=204))


# ── App ───────────────────────────────────────────────────────────────────────

def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get( "/health",                          health)
    app.router.add_post("/streams",                         stream_start)
    app.router.add_get( "/streams",                         stream_list)
    app.router.add_get( "/streams/{stream_id}/key",         stream_key)
    app.router.add_get( "/streams/{stream_id}/status",      stream_status)
    app.router.add_post("/streams/{stream_id}/bok",         stream_bok)
    app.router.add_post("/streams/{stream_id}/end",         stream_end)
    app.router.add_post("/streams/{stream_id}/resonate",    resonance_marker)
    app.router.add_post("/discover",                        stream_discover)
    app.router.add_get( "/ws",                              ws_handler)
    app.router.add_route("OPTIONS", "/{path:.*}",           options_handler)
    return app


async def _main() -> None:
    app    = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site   = web.TCPSite(runner, "0.0.0.0", 7800)
    await site.start()
    print(
        "[atelier-streaming] REST :7800  WS :7800/ws\n"
        f"  kernel  = {KERNEL_HTTP}\n"
        f"  atelier = {ATELIER_API}\n"
        f"  rtmp    = {mediamtx.RTMP_BASE}\n"
        f"  auth    = REQUIRE_AUTH={os.getenv('REQUIRE_AUTH','false')}"
    )
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_main())
