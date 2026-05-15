"""
WebSocket broadcaster — serves viewers on port 7701.

URL patterns:
  ws://relay:7701/stream/<stream_id>?token=<bearer>   — watch a stream
  ws://relay:7701/                                     — list live streams

On connect, the viewer immediately receives:
  - META packet (stream metadata + game info)
  - Latest JPEG frame (so the canvas shows something instantly)
  - Last 10 semantic events (catch up on recent game state)

Then live updates are pushed as they arrive from DjinnOS.

Viewer → relay messages:
  {"type":"witness","payload":{...}}   — Lotus attestation event
    → broadcast back to all stream participants as {"type":"witness_event",...}
"""

import asyncio
import json
from urllib.parse import urlparse, parse_qs
from typing import Optional

import websockets
import websockets.exceptions

from guild_gate        import validate_token
from stream_registry   import registry
from discord_notifier  import notify_witness_join


# ── Connection handler ────────────────────────────────────────────────────────

async def _viewer_handler(websocket) -> None:
    path   = getattr(websocket, "path", "/")
    parsed = urlparse(path)
    parts  = [p for p in parsed.path.strip("/").split("/") if p]

    # Root — list available streams
    if not parts or (len(parts) == 1 and parts[0] == ""):
        reg     = registry()
        streams = [
            {
                "id":      s.stream_id,
                "game":    s.meta.get("game", "?"),
                "viewers": reg.viewer_count(s.stream_id),
                "age_s":   round(s.age_s()),
            }
            for s in reg.all_streams()
        ]
        await websocket.send(json.dumps({"type": "streams", "list": streams}))
        return

    # Extract stream_id from path: /stream/<id> or /<id>
    stream_id = parts[1] if (len(parts) >= 2 and parts[0] == "stream") else parts[0]

    # Guild auth
    qs    = parse_qs(parsed.query)
    token = qs.get("token", [""])[0]
    user  = await validate_token(token)
    if user is None:
        await websocket.send(json.dumps({"type": "error", "msg": "auth_required"}))
        await websocket.close(1008, "unauthorized")
        return

    reg    = registry()
    stream = reg.get(stream_id)
    if stream is None:
        await websocket.send(json.dumps({"type": "error", "msg": "stream_not_found"}))
        return

    # Catch-up: send current state immediately
    if stream.meta:
        await websocket.send(json.dumps({"type": "meta", "stream_id": stream_id, **stream.meta}))
    if stream.latest_frame_jpeg:
        await websocket.send(json.dumps({
            "type": "frame",
            "fmt":  "jpeg",
            "data": stream.latest_frame_jpeg,
            "w":    stream.frame_w,
            "h":    stream.frame_h,
        }))
    for ev in stream.recent_events[-10:]:
        await websocket.send(json.dumps({"type": "semantic", "payload": ev}))

    q: asyncio.Queue = asyncio.Queue(maxsize=30)
    reg.add_viewer(stream_id, q)
    vc       = reg.viewer_count(stream_id)
    username = user.get("artisan_id", user.get("discord_username", "witness"))
    title    = (stream.meta or {}).get("title", stream_id)
    print(f"[ws] viewer joined  stream:{stream_id}  viewers:{vc}  user:{username}")
    # Notify Discord when the first witness arrives (not every join).
    if vc == 1:
        import asyncio as _aio
        _aio.ensure_future(notify_witness_join(stream_id, title, username, vc))

    try:
        await asyncio.gather(
            _send_loop(websocket, stream_id, q),
            _recv_loop(websocket, stream_id, user),
            return_exceptions=True,
        )
    finally:
        reg.remove_viewer(stream_id, q)
        vc = reg.viewer_count(stream_id)
        print(f"[ws] viewer left    stream:{stream_id}  viewers:{vc}")


async def _send_loop(websocket, stream_id: str, q: asyncio.Queue) -> None:
    """Push queued messages to the viewer.  Keepalive ping every 30 s of silence."""
    while True:
        try:
            msg = await asyncio.wait_for(q.get(), timeout=30.0)
            await websocket.send(json.dumps(msg))
        except asyncio.TimeoutError:
            await websocket.ping()
        except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError):
            break
        except Exception:
            break


async def _recv_loop(websocket, stream_id: str, user: dict) -> None:
    """Receive messages from viewer (witness attestation, chat, etc.)."""
    reg = registry()
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            ev_type = msg.get("type")

            if ev_type == "witness":
                # Lotus attestation — broadcast back into the stream
                await reg.broadcast(stream_id, {
                    "type":    "witness_event",
                    "from":    user.get("artisan_id", "viewer"),
                    "payload": msg.get("payload", {}),
                })

    except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError):
        pass
    except Exception:
        pass


# ── Start ─────────────────────────────────────────────────────────────────────

async def start_broadcaster(host: str = "0.0.0.0", port: int = 7701):
    srv = await websockets.serve(_viewer_handler, host, port)
    print(f"[ws]       listening on {host}:{port}")
    return srv
