from dataclasses import dataclass
from typing import List, Optional, Literal

FrontierStatus = Literal["active", "inconsistent", "closed"]

@dataclass(frozen=True)
class InconsistencyProof:
    conflicting_event_ids: List[str]
    description: Optional[str] = None

@dataclass(frozen=True)
class Frontier:
    id: str
    event_ids: List[str]
    status: FrontierStatus
    inconsistency_proof: Optional[InconsistencyProof] = None
