from dataclasses import dataclass
from typing import Dict, Any, List, Literal

EdgeType = Literal[
    "depends",
    "conflicts",
    "enables",
    "blocks",
]

@dataclass(frozen=True)
class Edge:
    from_event: str
    to_event: str
    type: EdgeType
    metadata: Dict[str, Any]

@dataclass(frozen=True)
class CausalEventGraph:
    events: List[Any]   # KernelEvent union, kept loose on purpose
    edges: List[Edge]
