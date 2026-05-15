"""
TCP receiver — listens for DjinnOS stream pushes on port 7700.

Each connected DjinnOS instance becomes one stream.  stream_id is
derived from the source IP (dots replaced with underscores).
Multiple DjinnOS instances can push simultaneously.
"""

import asyncio
import json
import os
import struct
import time

import aiohttp

from protocol        import read_packet, PKT_FRAME, PKT_SEMANTIC, PKT_KEEPALIVE, PKT_META
from stream_registry import registry
from transcode       import rgb_to_jpeg_b64, frame_mime
from discord_notifier import notify_stream_live, notify_stream_end, notify_semantic

ATELIER_STREAMING = os.getenv("ATELIER_STREAMING", "http://localhost:7800")


async def _register_with_backend(stream_id: str, source_ip: str, meta: dict) -> None:
    """Forward META to the atelier-streaming backend for QCR registration."""
    payload = {
        "id":      stream_id,
        "label":   meta.get("title", stream_id),
        "coords":  meta.get("tongues", []),   # tongue numbers as QCR coords
        "src":     source_ip,
    }
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(
                f"{ATELIER_STREAMING}/streams",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=3),
            )
    except Exception:
        pass  # backend unavailable — stream relay continues regardless


async def _handle_source(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    peer      = writer.get_extra_info("peername")
    source_ip = peer[0] if peer else "unknown"
    stream_id = source_ip.replace(".", "_")

    print(f"[receiver] DjinnOS connected  {source_ip}  →  stream:{stream_id}")

    reg    = registry()
    stream = reg.get_or_create(stream_id, source_ip)
    mime   = frame_mime()
    peak_viewers = 0

    try:
        while True:
            pkt = await read_packet(reader)
            if pkt is None:
                break

            # ── META ─────────────────────────────────────────────────────────
            if pkt.pkt_type == PKT_META:
                try:
                    meta = json.loads(pkt.payload.decode("utf-8", errors="replace"))
                    is_new = not stream.meta  # first META = stream just came live
                    stream.meta    = meta
                    stream.frame_w = meta.get("w", 320)
                    stream.frame_h = meta.get("h", 180)
                    print(f"[receiver] {stream_id} META  {meta}")
                    await reg.broadcast(stream_id, {
                        "type": "meta", "stream_id": stream_id, **meta,
                    })
                    await _register_with_backend(stream_id, source_ip, meta)
                    if is_new:
                        await notify_stream_live(
                            stream_id = stream_id,
                            title     = meta.get("title", stream_id),
                            game      = meta.get("game", "7_KLGS"),
                            source_ip = source_ip,
                            tongues   = meta.get("tongues", []),
                        )
                except Exception:
                    pass

            # ── FRAME ─────────────────────────────────────────────────────────
            elif pkt.pkt_type == PKT_FRAME:
                if len(pkt.payload) < 4:
                    continue
                w = struct.unpack_from("<H", pkt.payload, 0)[0]
                h = struct.unpack_from("<H", pkt.payload, 2)[0]
                rgb = pkt.payload[4:]

                if len(rgb) < w * h * 3:
                    continue

                stream.last_frame_ts = time.time()
                stream.frame_w       = w
                stream.frame_h       = h
                vc = reg.viewer_count(stream_id)
                if vc > peak_viewers:
                    peak_viewers = vc

                encoded = rgb_to_jpeg_b64(w, h, rgb)
                if encoded:
                    stream.latest_frame_jpeg = encoded
                    await reg.broadcast(stream_id, {
                        "type": "frame",
                        "fmt":  mime,
                        "data": encoded,
                        "w":    w,
                        "h":    h,
                    })

            # ── SEMANTIC ──────────────────────────────────────────────────────
            elif pkt.pkt_type == PKT_SEMANTIC:
                try:
                    ev = json.loads(pkt.payload.decode("utf-8", errors="replace"))
                    stream.record_event(ev)
                    await reg.broadcast(stream_id, {"type": "semantic", "payload": ev})
                    await notify_semantic(
                        stream_id = stream_id,
                        title     = stream.meta.get("title", stream_id),
                        ev_type   = ev.get("ev", ""),
                        payload_d = ev,
                    )
                except Exception:
                    pass

            # ── KEEPALIVE — no action ─────────────────────────────────────────

    except (ConnectionResetError, asyncio.IncompleteReadError, OSError):
        pass
    finally:
        duration = stream.age_s()
        title    = stream.meta.get("title", stream_id) if stream.meta else stream_id
        vc       = reg.viewer_count(stream_id)
        peak_viewers = max(peak_viewers, vc)
        print(f"[receiver] {source_ip} disconnected  duration={duration:.0f}s  peak={peak_viewers}")
        reg.remove(stream_id)
        if stream.meta:  # only notify if stream was actually live
            import asyncio as _aio
            _aio.ensure_future(notify_stream_end(
                stream_id    = stream_id,
                title        = title,
                duration_s   = duration,
                peak_viewers = peak_viewers,
            ))
        try:
            writer.close()
        except Exception:
            pass


async def start_receiver(host: str = "0.0.0.0", port: int = 7700):
    srv = await asyncio.start_server(_handle_source, host, port)
    print(f"[receiver] listening on {host}:{port}")
    return srv
