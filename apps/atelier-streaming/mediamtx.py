"""
mediamtx.py — MediaMTX REST API wrapper.

MediaMTX (formerly rtsp-simple-server) is the media server sidecar.
It handles RTMP ingest from OBS, HLS output, and WebRTC WHEP.

Default MediaMTX REST API: http://localhost:9997
Configurable via MEDIAMTX_API env var.

Key endpoints we use:
  GET  /v3/paths/list            — list active path/stream slots
  GET  /v3/paths/get/{name}      — path details (bytes, readers, active)
  POST /v3/config/paths/add/{n}  — create a path (stream key)
  POST /v3/config/paths/delete/{n} — remove a path
  GET  /v3/hlsmuxers/list        — HLS muxers (one per active stream)
  GET  /v3/webrtcsessions/list   — WebRTC sessions

MediaMTX config notes:
  - Each stream key maps to a path name: /live/<key>
  - RTMP ingest:   rtmp://host:1935/live/<key>
  - HLS output:    https://host:8888/live/<key>/index.m3u8
  - WebRTC WHEP:   https://host:8889/live/<key>/whep
"""

import os
import secrets
import aiohttp

MEDIAMTX_API = os.getenv("MEDIAMTX_API", "http://localhost:9997")
HLS_BASE     = os.getenv("HLS_BASE",      "https://stream.quantumquackery.com:8888")
RTMP_BASE    = os.getenv("RTMP_BASE",      "rtmp://stream.quantumquackery.com:1935")
WEBRTC_BASE  = os.getenv("WEBRTC_BASE",   "https://stream.quantumquackery.com:8889")


def generate_key(artisan_id: str) -> str:
    token = secrets.token_urlsafe(12)
    return f"{artisan_id}-{token}"


async def create_path(key: str) -> bool:
    """Register a stream key path with MediaMTX."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{MEDIAMTX_API}/v3/config/paths/add/live/{key}",
                json={"name": f"live/{key}"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                return r.status in (200, 201, 204)
    except Exception:
        return True   # If MediaMTX unreachable, proceed optimistically


async def delete_path(key: str) -> bool:
    """Unregister a stream key path from MediaMTX."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{MEDIAMTX_API}/v3/config/paths/delete/live/{key}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                return r.status in (200, 204)
    except Exception:
        return True


async def is_path_active(key: str) -> bool:
    """Returns True if MediaMTX reports an active publisher on this path."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{MEDIAMTX_API}/v3/paths/get/live/{key}",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as r:
                if r.status != 200:
                    return False
                d = await r.json()
                return bool(d.get("source") and d.get("source", {}).get("type"))
    except Exception:
        return False


async def reader_count(key: str) -> int:
    """Returns number of active readers (viewers) on this path."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{MEDIAMTX_API}/v3/paths/get/live/{key}",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as r:
                if r.status != 200:
                    return 0
                d = await r.json()
                readers = d.get("readers", [])
                return len(readers) if isinstance(readers, list) else 0
    except Exception:
        return 0


def hls_url(key: str) -> str:
    return f"{HLS_BASE}/live/{key}/index.m3u8"

def rtmp_url(key: str) -> str:
    return f"{RTMP_BASE}/live/{key}"

def webrtc_url(key: str) -> str:
    return f"{WEBRTC_BASE}/live/{key}/whep"
