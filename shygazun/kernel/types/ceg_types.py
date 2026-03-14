# kernel/types/ceg_types.py
from __future__ import annotations
from typing import Dict, Any


class Edge:
    def __init__(
        self,
        from_event: str,
        to_event: str,
        type: str,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        self.from_event: str = from_event
        self.to_event: str = to_event
        self.type: str = type
        self.metadata: Dict[str, Any] = metadata or {}
