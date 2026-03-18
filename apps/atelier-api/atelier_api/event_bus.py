"""
Lightweight in-process pub/sub for SSE push.

publish_sync() is safe to call from sync route handlers (FastAPI threadpool).
subscribe()/unsubscribe() are called from async SSE handler coroutines.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, DefaultDict, List

# conversation_id → list of subscriber queues
_subscribers: DefaultDict[str, List[asyncio.Queue]] = defaultdict(list)
_loop: asyncio.AbstractEventLoop | None = None


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def subscribe(conversation_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    _subscribers[conversation_id].append(q)
    return q


def unsubscribe(conversation_id: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(conversation_id)
    if subs and q in subs:
        subs.remove(q)
    # Clean up empty lists to avoid unbounded growth
    if subs is not None and not subs:
        _subscribers.pop(conversation_id, None)


def publish_sync(conversation_id: str, payload: dict[str, Any]) -> None:
    """Push payload to all SSE subscribers for conversation_id.

    Thread-safe: called from sync FastAPI handlers running in threadpool.
    No-ops silently when no event loop is set or no subscribers exist.
    """
    if _loop is None:
        return
    for q in list(_subscribers.get(conversation_id, [])):
        try:
            _loop.call_soon_threadsafe(q.put_nowait, payload)
        except asyncio.QueueFull:
            # Slow consumer — drop the event rather than block
            pass
