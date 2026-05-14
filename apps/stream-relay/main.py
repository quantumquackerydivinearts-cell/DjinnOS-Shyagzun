"""
DjinnOS Stream Relay — asyncio entrypoint.

Ports:
  7700  TCP   DjinnOS → relay (DJNX wire protocol)
  7701  WS    relay   → viewers (WebSocket)
  7702  HTTP  Guild REST API (stream list, event log, health)

Environment:
  BIND           bind address (default 0.0.0.0)
  RECEIVER_PORT  DjinnOS push port (default 7700)
  WS_PORT        viewer WebSocket port (default 7701)
  REST_PORT      REST API port (default 7702)
  REQUIRE_AUTH   enforce Atelier token validation (default false)
  ATELIER_API    Atelier API base URL (default http://127.0.0.1:9000)
"""

import asyncio
import os
import signal

from djinn_receiver import start_receiver
from ws_broadcaster import start_broadcaster
from rest_api       import start_rest

BIND          = os.getenv("BIND",           "0.0.0.0")
RECV_PORT     = int(os.getenv("RECEIVER_PORT", "7700"))
WS_PORT       = int(os.getenv("WS_PORT",       "7701"))
REST_PORT     = int(os.getenv("REST_PORT",      "7702"))
REQUIRE_AUTH  = os.getenv("REQUIRE_AUTH",  "false")
ATELIER_API   = os.getenv("ATELIER_API",   "http://127.0.0.1:9000")


def _banner() -> None:
    print(f"""
  ┌─ DjinnOS Stream Relay ────────────────────────────────────────┐
  │                                                                │
  │  DjinnOS push  tcp  :{RECV_PORT:<5}   (DJNX wire protocol)        │
  │  Viewer WS     ws   :{WS_PORT:<5}   /stream/<id>?token=<tok>  │
  │  Guild API     http :{REST_PORT:<5}   /streams  /health         │
  │                                                                │
  │  Auth          REQUIRE_AUTH={REQUIRE_AUTH:<5}                        │
  │  Atelier API   {ATELIER_API:<47} │
  │                                                                │
  │  In DjinnOS Ko shell:                                          │
  │    stream <your-relay-ip>:{RECV_PORT:<5}                              │
  └────────────────────────────────────────────────────────────────┘
""")


async def _main() -> None:
    recv_srv  = await start_receiver(BIND, RECV_PORT)
    ws_srv    = await start_broadcaster(BIND, WS_PORT)
    rest_runner = await start_rest(BIND, REST_PORT)

    _banner()

    loop = asyncio.get_running_loop()
    stop: asyncio.Future = loop.create_future()

    def _on_signal() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except NotImplementedError:
            pass   # Windows — caught by KeyboardInterrupt instead

    try:
        await stop
    except KeyboardInterrupt:
        pass

    print("\n[relay] shutting down...")
    recv_srv.close()
    ws_srv.close()
    await recv_srv.wait_closed()
    await rest_runner.cleanup()
    print("[relay] done")


if __name__ == "__main__":
    asyncio.run(_main())
