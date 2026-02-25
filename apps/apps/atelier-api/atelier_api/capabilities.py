from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Set


@dataclass(frozen=True)
class CapabilityContext:
    actor_id: str
    capabilities: FrozenSet[str]


def parse_capabilities(raw: str) -> FrozenSet[str]:
    parts = [token.strip() for token in raw.split(",")]
    cleaned: Set[str] = {token for token in parts if token}
    return frozenset(cleaned)


def require_capability(ctx: CapabilityContext, needed: Iterable[str]) -> None:
    missing = [cap for cap in needed if cap not in ctx.capabilities]
    if missing:
        missing_csv = ",".join(sorted(missing))
        raise PermissionError(f"missing_capabilities:{missing_csv}")

