from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence, List

from shygazun.kernel.types import Edge


class JSONLCEGAdapter:
    """
    Reference CEG persistence adapter (v0.1.0).

    - Append-only
    - Order-preserving
    - JSON-first
    - No inference
    - No schema enforcement
    """

    def __init__(self, events_path: Path, edges_path: Path) -> None:
        self._events_path = events_path
        self._edges_path = edges_path

        # Ensure files exist
        self._events_path.parent.mkdir(parents=True, exist_ok=True)
        self._edges_path.parent.mkdir(parents=True, exist_ok=True)

        self._events_path.touch(exist_ok=True)
        self._edges_path.touch(exist_ok=True)

    # -----------------------------
    # Append operations
    # -----------------------------

    def append_event(self, event: Mapping[str, Any]) -> None:
        try:
            with self._events_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False))
                f.write("\n")
        except Exception as e:
            raise RuntimeError("Failed to append event") from e

    def append_edge(self, edge: Edge) -> None:
        try:
            with self._edges_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(edge, ensure_ascii=False))
                f.write("\n")
        except Exception as e:
            raise RuntimeError("Failed to append edge") from e

    # -----------------------------
    # Load operations
    # -----------------------------

    def load_events(self) -> Sequence[Mapping[str, Any]]:
        events: List[Mapping[str, Any]] = []
        try:
            with self._events_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    events.append(json.loads(line))
        except Exception as e:
            raise RuntimeError("Failed to load events") from e
        return events

    def load_edges(self) -> Sequence[Edge]:
        edges: List[Edge] = []
        try:
            with self._edges_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    edges.append(json.loads(line))
        except Exception as e:
            raise RuntimeError("Failed to load edges") from e
        return edges
