"""
In-memory stream registry.

Each active DjinnOS source becomes a StreamInfo keyed by stream_id
(derived from source IP).  Viewer WebSocket handlers subscribe via
asyncio.Queue objects — one queue per connected viewer.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class StreamInfo:
    stream_id:          str
    source_ip:          str
    meta:               dict
    started_at:         float = field(default_factory=time.time)
    last_frame_ts:      float = field(default_factory=time.time)
    frame_w:            int   = 320
    frame_h:            int   = 180
    latest_frame_jpeg:  Optional[str] = None   # base64 JPEG string
    recent_events:      list  = field(default_factory=list)

    MAX_EVENTS: int = 100

    def record_event(self, ev: dict) -> None:
        self.recent_events.append(ev)
        if len(self.recent_events) > self.MAX_EVENTS:
            self.recent_events.pop(0)

    def age_s(self) -> float:
        return time.time() - self.started_at

    def frame_lag_s(self) -> float:
        return time.time() - self.last_frame_ts


class StreamRegistry:
    def __init__(self) -> None:
        self._streams: Dict[str, StreamInfo]         = {}
        self._queues:  Dict[str, Set[asyncio.Queue]] = {}

    # ── Stream lifecycle ──────────────────────────────────────────────────────

    def get_or_create(self, stream_id: str, source_ip: str) -> StreamInfo:
        if stream_id not in self._streams:
            self._streams[stream_id] = StreamInfo(
                stream_id=stream_id, source_ip=source_ip, meta={},
            )
            self._queues[stream_id] = set()
        return self._streams[stream_id]

    def remove(self, stream_id: str) -> None:
        self._streams.pop(stream_id, None)
        self._queues.pop(stream_id, None)

    def get(self, stream_id: str) -> Optional[StreamInfo]:
        return self._streams.get(stream_id)

    def all_streams(self) -> List[StreamInfo]:
        return list(self._streams.values())

    # ── Viewer subscriptions ──────────────────────────────────────────────────

    def add_viewer(self, stream_id: str, q: asyncio.Queue) -> None:
        if stream_id in self._queues:
            self._queues[stream_id].add(q)

    def remove_viewer(self, stream_id: str, q: asyncio.Queue) -> None:
        self._queues.get(stream_id, set()).discard(q)

    def viewer_count(self, stream_id: str) -> int:
        return len(self._queues.get(stream_id, set()))

    async def broadcast(self, stream_id: str, message: dict) -> None:
        """Push message to every viewer subscribed to this stream."""
        for q in list(self._queues.get(stream_id, set())):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass   # slow viewer — frame is dropped, not buffered


_registry = StreamRegistry()


def registry() -> StreamRegistry:
    return _registry
