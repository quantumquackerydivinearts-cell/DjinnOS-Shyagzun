"""
DJNX wire protocol parser.

Frame layout (little-endian):
  [4]  magic   b"DJNX"
  [1]  type    PKT_FRAME | PKT_SEMANTIC | PKT_KEEPALIVE | PKT_META
  [4]  length  payload byte count (u32 LE)
  [N]  payload

PKT_FRAME payload:
  [2]  width  u16 LE
  [2]  height u16 LE
  [N]  RGB bytes, R-G-B per pixel, row-major

PKT_SEMANTIC / PKT_META: UTF-8 JSON
PKT_KEEPALIVE: empty
"""

import asyncio
import struct
from dataclasses import dataclass
from typing import Optional

MAGIC        = b"DJNX"
PKT_FRAME    = 0x01
PKT_SEMANTIC = 0x02
PKT_KEEPALIVE= 0x04
PKT_META     = 0x05

MAX_PAYLOAD  = 8 * 1024 * 1024   # 8 MB hard cap


@dataclass
class DjnxPacket:
    pkt_type: int
    payload:  bytes


async def read_packet(reader: asyncio.StreamReader) -> Optional[DjnxPacket]:
    """Read one DJNX packet. Returns None on EOF, error, or protocol violation."""
    try:
        hdr = await reader.readexactly(9)
    except (asyncio.IncompleteReadError, ConnectionResetError, OSError):
        return None

    if hdr[:4] != MAGIC:
        return None

    pkt_type = hdr[4]
    length   = struct.unpack_from("<I", hdr, 5)[0]

    if length > MAX_PAYLOAD:
        return None

    try:
        payload = await reader.readexactly(length) if length > 0 else b""
    except (asyncio.IncompleteReadError, ConnectionResetError, OSError):
        return None

    return DjnxPacket(pkt_type=pkt_type, payload=payload)
