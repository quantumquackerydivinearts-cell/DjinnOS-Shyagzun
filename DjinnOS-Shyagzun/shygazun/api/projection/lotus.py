from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class LotusState:
    """
    Runtime-only lotus projection.
    Kernel does not interpret this.
    """
    attestations: List[Dict[str, Any]]
    status: str  # intentionally opaque
