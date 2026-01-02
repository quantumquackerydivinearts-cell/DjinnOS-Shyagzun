from dataclasses import dataclass
from typing import Protocol
from .clock import Clock

class FieldLike(Protocol):
    """
    Structural contract only.
    No immutability guarantees.
    """

    field_id: str
    clock: Clock
    
from dataclasses import dataclass
from typing import Dict, Any
from .clock import Clock
from .lotus import LotusState


@dataclass
class Field:
    field_id: str
    clock: Clock
    tensions: Dict[str, Any]
    gates: Dict[str, Any]
    obligations: Dict[str, Any]
    atoms: Dict[str, Any]
    lotus: LotusState
