from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from shygazun.ide.atelier_port import AtelierPort
from shygazun.kernel.kernel import ObserveResult, PlaceResult
from shygazun.kernel.types import Clock, Edge, Frontier
from shygazun.kernel.types.events import KernelEventObj


@dataclass(frozen=True)
class CobraLine:
    raw: str
    speaker_id: str
    scene_id: Optional[str]
    quest_id: Optional[str]
    tags: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class CobraPacket:
    lines: List[CobraLine]
    context: Dict[str, Any]


class CobraRuntime:
    def __init__(self, port: AtelierPort, *, default_speaker_id: str = "player") -> None:
        self._port = port
        self._default_speaker_id = default_speaker_id
        self._last_refusals: List[Dict[str, Any]] = []

    def place_line(
        self,
        raw: str,
        *,
        speaker_id: Optional[str] = None,
        scene_id: Optional[str] = None,
        quest_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlaceResult:
        effective_speaker = speaker_id if speaker_id is not None else self._default_speaker_id
        context: Dict[str, Any] = {"speaker_id": effective_speaker}
        if scene_id is not None:
            context["scene_id"] = scene_id
        if quest_id is not None:
            context["quest_id"] = quest_id
        if tags is not None:
            context["tags"] = dict(tags)
        if metadata is not None:
            context["metadata"] = dict(metadata)

        result = self._port.place_line(raw, context=context)
        self._last_refusals = [dict(refusal) for refusal in result.observe.refusals]
        return result

    def place_packet(self, packet: CobraPacket) -> List[PlaceResult]:
        results: List[PlaceResult] = []
        for line in packet.lines:
            merged_metadata: Dict[str, Any] = dict(packet.context)
            for key, value in line.metadata.items():
                merged_metadata[key] = value
            result = self.place_line(
                line.raw,
                speaker_id=line.speaker_id,
                scene_id=line.scene_id,
                quest_id=line.quest_id,
                tags=dict(line.tags),
                metadata=merged_metadata,
            )
            results.append(result)
        return results

    def observe(self) -> ObserveResult:
        observed = self._port.observe()
        self._last_refusals = [dict(refusal) for refusal in observed.refusals]
        return observed

    def frontiers(self) -> List[Frontier]:
        return self._port.get_frontiers()

    def timeline(self, last: Optional[int] = None) -> Sequence[KernelEventObj]:
        return self._port.get_timeline(last=last)

    def refusals(self) -> List[Dict[str, Any]]:
        return list(self._last_refusals)


__all__ = [
    "CobraLine",
    "CobraPacket",
    "CobraRuntime",
    "Clock",
    "Edge",
]
