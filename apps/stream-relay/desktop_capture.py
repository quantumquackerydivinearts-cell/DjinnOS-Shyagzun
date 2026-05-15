"""
desktop_capture.py — Stream a desktop session as a DjinnOS DJNX feed.

Captures the screen (or a window), downsamples to STREAM_W×STREAM_H,
and sends as PKT_FRAME packets to the stream relay on port 7700.

Usage:
    python desktop_capture.py                     # full screen, 10fps
    python desktop_capture.py --fps 15            # 15fps
    python desktop_capture.py --w 640 --h 360     # custom resolution
    python desktop_capture.py --relay 1.2.3.4     # different relay IP

Requirements:
    pip install mss pillow

The relay then broadcasts to witnesses at relay.quantumquackery.com.
Set a stream title in DjinnOS Atelier → Soastream before capturing,
or use --title "My Dev Session".
"""

import asyncio
import struct
import socket
import time
import argparse
import sys
import os

MAGIC        = b"DJNX"
PKT_FRAME    = 0x01
PKT_META     = 0x05
PKT_KEEPALIVE = 0x04

DEFAULT_RELAY = "127.0.0.1"
DEFAULT_PORT  = 7700
DEFAULT_W     = 320
DEFAULT_H     = 180
DEFAULT_FPS   = 10


def build_packet(pkt_type: int, payload: bytes) -> bytes:
    hdr = MAGIC + bytes([pkt_type]) + struct.pack("<I", len(payload))
    return hdr + payload


def build_meta(w: int, h: int, fps: int, title: str, src_ip: str) -> bytes:
    import json
    meta = {
        "type":    "desktop_stream",
        "game":    "DEV",
        "version": 1,
        "title":   title,
        "w":       w,
        "h":       h,
        "fps":     fps,
        "src":     src_ip,
        "tongues": [],
    }
    return build_packet(PKT_META, json.dumps(meta).encode("utf-8"))


def build_frame(rgb_bytes: bytes, w: int, h: int) -> bytes:
    dim_hdr = struct.pack("<HH", w, h)
    return build_packet(PKT_FRAME, dim_hdr + rgb_bytes)


def capture_rgb(w: int, h: int) -> bytes:
    """Capture full screen, return RGB bytes at target resolution."""
    try:
        import mss
        import mss.tools
        from PIL import Image
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # all monitors combined
            img = sct.grab(monitor)
            pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            pil = pil.resize((w, h), Image.BILINEAR)
            return pil.tobytes()  # RGB bytes
    except ImportError:
        raise RuntimeError("Install dependencies: pip install mss pillow")


def send_all(sock: socket.socket, data: bytes) -> None:
    off = 0
    while off < len(data):
        sent = sock.send(data[off:off + 1400])
        if sent == 0:
            raise ConnectionError("relay disconnected")
        off += sent


def main():
    p = argparse.ArgumentParser(description="Stream desktop to DjinnOS relay")
    p.add_argument("--relay",  default=DEFAULT_RELAY, help="Relay IP")
    p.add_argument("--port",   type=int, default=DEFAULT_PORT, help="Relay TCP port")
    p.add_argument("--w",      type=int, default=DEFAULT_W,    help="Capture width")
    p.add_argument("--h",      type=int, default=DEFAULT_H,    help="Capture height")
    p.add_argument("--fps",    type=int, default=DEFAULT_FPS,  help="Frames per second")
    p.add_argument("--title",  default="Dev Session",           help="Stream title")
    args = p.parse_args()

    frame_interval = 1.0 / max(1, args.fps)
    src_ip = socket.gethostbyname(socket.gethostname())

    print(f"[capture] {args.w}×{args.h} @ {args.fps}fps → {args.relay}:{args.port}")
    print(f"[capture] title: {args.title!r}")
    print(f"[capture] Ctrl+C to stop")

    meta_pkt = build_meta(args.w, args.h, args.fps, args.title, src_ip)
    ka_pkt   = build_packet(PKT_KEEPALIVE, b"")

    sock = None
    ka_counter = 0
    KA_EVERY = max(1, 30 * args.fps)  # keepalive every ~30s

    try:
        while True:
            # Connect / reconnect loop
            if sock is None:
                try:
                    sock = socket.create_connection((args.relay, args.port), timeout=5)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    send_all(sock, meta_pkt)
                    print(f"[capture] connected, streaming…")
                except Exception as e:
                    print(f"[capture] connect failed: {e} — retrying in 3s")
                    sock = None
                    time.sleep(3)
                    continue

            t0 = time.monotonic()

            try:
                rgb = capture_rgb(args.w, args.h)
                frame_pkt = build_frame(rgb, args.w, args.h)
                send_all(sock, frame_pkt)

                ka_counter += 1
                if ka_counter >= KA_EVERY:
                    send_all(sock, ka_pkt)
                    ka_counter = 0

            except Exception as e:
                print(f"[capture] stream error: {e} — reconnecting")
                try: sock.close()
                except Exception: pass
                sock = None
                continue

            elapsed = time.monotonic() - t0
            sleep = frame_interval - elapsed
            if sleep > 0:
                time.sleep(sleep)

    except KeyboardInterrupt:
        print("\n[capture] stopped")
    finally:
        if sock:
            try: sock.close()
            except Exception: pass


if __name__ == "__main__":
    main()
