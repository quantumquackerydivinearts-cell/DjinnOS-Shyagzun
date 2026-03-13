"""
atelier_api/core/lineage.py
12-layer lineage store.
Every tick, scene compile, and state transition is appended here.
Provides deterministic replay and attestation chain.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import get_settings

settings = get_settings()

LAYER_NAMES = [
    "raw_input",       # 0  — verbatim client payload
    "validated",       # 1  — after schema validation
    "resolved",        # 2  — after ID/ref resolution
    "pre_tick",        # 3  — engine state before tick
    "tick_applied",    # 4  — diff produced by tick
    "post_tick",       # 5  — engine state after tick
    "compiled",        # 6  — compiled scene/cobra output
    "asset_resolved",  # 7  — assets hydrated
    "signed",          # 8  — attestation signatures applied
    "broadcast",       # 9  — dispatched to downstream
    "ack",             # 10 — acknowledgement received
    "archived",        # 11 — final archived form
]

assert len(LAYER_NAMES) == 12


@dataclass
class LineageRecord:
    lineage_id: str
    workspace_id: str
    actor_id: str
    action_kind: str
    timestamp_ms: int
    layers: dict[str, Any] = field(default_factory=dict)
    parent_hash: str = ""
    hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        blob = json.dumps(
            {
                "lineage_id": self.lineage_id,
                "workspace_id": self.workspace_id,
                "actor_id": self.actor_id,
                "action_kind": self.action_kind,
                "timestamp_ms": self.timestamp_ms,
                "parent_hash": self.parent_hash,
                "layers": self.layers,
            },
            sort_keys=True,
            default=str,
        ).encode()
        return hashlib.sha256(blob).hexdigest()

    def set_layer(self, layer_index: int, data: Any) -> None:
        name = LAYER_NAMES[layer_index]
        self.layers[name] = data
        self.hash = self._compute_hash()

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "workspace_id": self.workspace_id,
            "actor_id": self.actor_id,
            "action_kind": self.action_kind,
            "timestamp_ms": self.timestamp_ms,
            "parent_hash": self.parent_hash,
            "hash": self.hash,
            "layers": self.layers,
        }


class LineageStore:
    """
    Append-only file-based lineage store.
    Each workspace gets its own NDJSON log file.
    Replace with PostgreSQL/S3 for production scale.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or settings.lineage_store_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._last_hashes: dict[str, str] = {}

    def _log_path(self, workspace_id: str) -> Path:
        safe = workspace_id.replace("/", "_").replace(".", "_")
        return self.base_path / f"{safe}.ndjson"

    def append(self, record: LineageRecord) -> None:
        path = self._log_path(record.workspace_id)
        # Chain hashes
        parent = self._last_hashes.get(record.workspace_id, "")
        record.parent_hash = parent
        record.hash = record._compute_hash()
        self._last_hashes[record.workspace_id] = record.hash

        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")

    def create_record(
        self,
        lineage_id: str,
        workspace_id: str,
        actor_id: str,
        action_kind: str,
    ) -> LineageRecord:
        return LineageRecord(
            lineage_id=lineage_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action_kind=action_kind,
            timestamp_ms=int(time.time() * 1000),
        )

    def tail(self, workspace_id: str, n: int = 50) -> list[dict[str, Any]]:
        path = self._log_path(workspace_id)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines[-n:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return records


# Module-level singleton
_store: LineageStore | None = None


def get_lineage_store() -> LineageStore:
    global _store
    if _store is None:
        _store = LineageStore()
    return _store
