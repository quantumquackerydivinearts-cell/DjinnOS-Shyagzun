from __future__ import annotations

from typing import Any, Dict, Optional

from .atelier_port import AtelierPort


def build_projection(port: AtelierPort, *, timeline_last: Optional[int] = None) -> Dict[str, Any]:
    """
    Read-only projection for tooling layers.
    """
    frontiers = sorted(list(port.get_frontiers()), key=lambda f: f["id"])
    timeline = list(port.get_timeline(last=timeline_last))
    edges = list(port.get_edges())
    return {
        "frontiers": frontiers,
        "timeline": timeline,
        "edges": edges,
    }

