# kernel/types/utterance.py
from __future__ import annotations
from typing import Any, Dict, Optional


class Utterance:
    def __init__(
        self,
        raw: str,
        addressing: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.raw: str = raw
        self.addressing: Dict[str, Any] = addressing or {}
        self.metadata: Dict[str, Any] = metadata or {}
