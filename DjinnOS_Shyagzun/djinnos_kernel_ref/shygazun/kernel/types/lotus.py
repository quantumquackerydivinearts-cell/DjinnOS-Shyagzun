from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Lotus Requirement (used in Preconditions)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LotusRequirement:
    """
    Structural requirement for an external attestation.

    Kernel does NOT interpret this.
    Kernel only checks presence/absence.
    """
    kind: str
    attestation_tag: Optional[str] = None


# ---------------------------------------------------------------------------
# Lotus State (lives on Field)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LotusState:
    """
    Opaque lotus state.

    Kernel v0.1.1 does not inspect, mutate, or resolve this.
    """
    attestations: List[Dict[str, Any]]
    status: str  # intentionally opaque
