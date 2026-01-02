from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, List, Optional

from shygazun.kernel.types import Edge
from shygazun.kernel.ceg_jsonl_adapter import JSONLCEGAdapter


KernelEventObj = Mapping[str, Any]


@dataclass
class CEG:
    """
    Canonical Event Graph (append-only).

    - JSON-first
    - No semantics
    - No inference
    - Optional persistence via adapter
    """

    _events: List[KernelEventObj] = field(default_factory=list)
    _edges: List[Edge] = field(default_factory=list)
    _adapter: Optional[JSONLCEGAdapter] = None

    # -----------------------------
    # Construction
    # -----------------------------

    @classmethod
    def with_adapter(cls, adapter: JSONLCEGAdapter) -> "CEG":
        """
        Construct a CEG with a persistence adapter.
        """
        ceg = cls(adapter=adapter)

        # Hydrate from adapter (append-only replay)
        ceg._events.extend(adapter.load_events())
        ceg._edges.extend(adapter.load_edges())

        return ceg

    # -----------------------------
    # Append operations
    # -----------------------------

    def add_event(self, e: KernelEventObj) -> None:
        self._events.append(e)
        if self._adapter is not None:
            self._adapter.append_event(e)

    def add_edge(self, e: Edge) -> None:
        self._edges.append(e)
        if self._adapter is not None:
            self._adapter.append_edge(e)

    # -----------------------------
    # Read operations
    # -----------------------------

    def get_events(self) -> Sequence[KernelEventObj]:
        return self._events

    def get_edges(self) -> Sequence[Edge]:
        return self._edges
