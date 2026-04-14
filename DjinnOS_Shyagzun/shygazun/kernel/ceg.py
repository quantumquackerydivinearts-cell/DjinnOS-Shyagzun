from __future__ import annotations

from typing import List, Sequence

from .types import Edge
from .types.events import KernelEventObj

__all__ = ["CEG", "KernelEventObj"]


class CEG:
    def __init__(self) -> None:
        self._events: List[KernelEventObj] = []
        self._edges: List[Edge] = []

    def add_event(self, evt: KernelEventObj) -> None:
        self._events.append(evt)

    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    def get_events(self) -> Sequence[KernelEventObj]:
        return sorted(
            self._events,
            key=lambda evt: (
                int(evt["at"]["tick"]),
                str(evt["kind"]),
                str(evt["id"]),
            ),
        )

    def get_edges(self) -> Sequence[Edge]:
        return sorted(
            self._edges,
            key=lambda edge: (edge.from_event, edge.to_event, edge.type),
        )
