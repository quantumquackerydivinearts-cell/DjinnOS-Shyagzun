from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet


ROLE_APPRENTICE = "apprentice"
ROLE_ARTISAN = "artisan"
ROLE_SENIOR_ARTISAN = "senior_artisan"
ROLE_STEWARD = "steward"


@dataclass(frozen=True)
class RoleContext:
    role: str


ROLE_CAPABILITIES: Dict[str, FrozenSet[str]] = {
    ROLE_APPRENTICE: frozenset({"kernel.observe", "kernel.timeline", "kernel.frontiers"}),
    ROLE_ARTISAN: frozenset({"kernel.place", "kernel.observe", "kernel.timeline", "kernel.frontiers", "kernel.edges"}),
    ROLE_SENIOR_ARTISAN: frozenset(
        {
            "kernel.place",
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "kernel.edges",
            "kernel.attest",
        }
    ),
    ROLE_STEWARD: frozenset(
        {
            "kernel.place",
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "kernel.edges",
            "kernel.attest",
        }
    ),
}


def role_allows(role: str, capability: str) -> bool:
    allowed = ROLE_CAPABILITIES.get(role)
    if allowed is None:
        return False
    return capability in allowed

