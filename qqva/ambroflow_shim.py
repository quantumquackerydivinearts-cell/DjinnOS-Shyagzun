from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .atelier_port import AtelierPort
from .types import ObserveResult, PlaceResult


@dataclass(frozen=True)
class AmbroflowLine:
    raw: str
    speaker_id: str
    scene_id: Optional[str]
    tags: Dict[str, str]
    metadata: Dict[str, Any]


class AmbroflowShim:
    """
    Placement emitter + frontier observer only.
    """

    def __init__(self, port: AtelierPort, *, default_speaker_id: str = "player") -> None:
        self._port = port
        self._default_speaker_id = default_speaker_id
        self._last_observe: Optional[ObserveResult] = None

    def place_line(
        self,
        raw: str,
        *,
        speaker_id: Optional[str] = None,
        scene_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlaceResult:
        context: Dict[str, Any] = {"speaker_id": speaker_id or self._default_speaker_id}
        if scene_id is not None:
            context["scene_id"] = scene_id
        if tags is not None:
            context["tags"] = dict(tags)
        if metadata is not None:
            context["metadata"] = dict(metadata)
        return self._port.place_line(raw, context=context)

    def place_batch(self, lines: List[AmbroflowLine]) -> List[PlaceResult]:
        return [
            self.place_line(
                line.raw,
                speaker_id=line.speaker_id,
                scene_id=line.scene_id,
                tags=line.tags,
                metadata=line.metadata,
            )
            for line in lines
        ]

    def observe(self) -> ObserveResult:
        self._last_observe = self._port.observe()
        return self._last_observe

    def refusals(self) -> List[Dict[str, Any]]:
        if self._last_observe is None:
            return []
        return list(self._last_observe["refusals"])

