"""
Guild REST API — port 7702.

Endpoints:
  GET  /health              — liveness check
  GET  /streams             — list all live streams
  GET  /streams/<id>        — stream detail + recent semantic events
  GET  /streams/<id>/events — semantic event log (last 100)

Intended for guild stewards and the Atelier dashboard.
CORS is open so the Atelier frontend can poll it directly.
"""

import time
from aiohttp import web


def _cors(resp: web.Response) -> web.Response:
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return resp


def _json(data, status: int = 200) -> web.Response:
    return _cors(web.json_response(data, status=status))


# ── Route handlers ────────────────────────────────────────────────────────────

async def get_health(request: web.Request) -> web.Response:
    from stream_registry import registry
    reg = registry()
    return _json({"ok": True, "streams": len(reg.all_streams()), "ts": time.time()})


async def get_streams(request: web.Request) -> web.Response:
    from stream_registry import registry
    reg = registry()
    out = []
    for s in reg.all_streams():
        out.append({
            "id":        s.stream_id,
            "source_ip": s.source_ip,
            "game":      s.meta.get("game", "unknown"),
            "viewers":   reg.viewer_count(s.stream_id),
            "age_s":     round(s.age_s()),
            "frame_lag": round(s.frame_lag_s(), 2),
            "meta":      s.meta,
        })
    return _json({"streams": out})


async def get_stream(request: web.Request) -> web.Response:
    from stream_registry import registry
    sid = request.match_info["stream_id"]
    reg = registry()
    s   = reg.get(sid)
    if s is None:
        return _json({"error": "not_found"}, status=404)
    return _json({
        "id":        s.stream_id,
        "source_ip": s.source_ip,
        "meta":      s.meta,
        "viewers":   reg.viewer_count(s.stream_id),
        "age_s":     round(s.age_s()),
        "frame_lag": round(s.frame_lag_s(), 2),
        "frame_w":   s.frame_w,
        "frame_h":   s.frame_h,
        "events":    s.recent_events[-20:],
    })


async def get_stream_events(request: web.Request) -> web.Response:
    from stream_registry import registry
    sid = request.match_info["stream_id"]
    reg = registry()
    s   = reg.get(sid)
    if s is None:
        return _json({"error": "not_found"}, status=404)
    return _json({"stream_id": sid, "events": s.recent_events})


async def options_handler(request: web.Request) -> web.Response:
    return _cors(web.Response(status=204))


# ── App factory ───────────────────────────────────────────────────────────────

def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get( "/health",                     get_health)
    app.router.add_get( "/streams",                    get_streams)
    app.router.add_get( "/streams/{stream_id}",        get_stream)
    app.router.add_get( "/streams/{stream_id}/events", get_stream_events)
    app.router.add_route("OPTIONS", "/{path_info:.*}", options_handler)
    return app


async def start_rest(host: str = "0.0.0.0", port: int = 7702):
    app    = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site   = web.TCPSite(runner, host, port)
    await site.start()
    print(f"[rest]     listening on {host}:{port}")
    return runner
