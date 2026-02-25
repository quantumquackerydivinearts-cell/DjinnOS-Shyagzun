from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional, Set


@dataclass(frozen=True)
class ArtisanIdentity:
    artisan_id: str
    workshop_id: str


@dataclass(frozen=True)
class WorkshopScope:
    scopes: FrozenSet[str]


@dataclass(frozen=True)
class WorkshopContext:
    identity: ArtisanIdentity
    scope: WorkshopScope


def parse_scopes(raw: str) -> FrozenSet[str]:
    parts = [item.strip() for item in raw.split(",")]
    cleaned: Set[str] = {item for item in parts if item}
    return frozenset(cleaned)


def scope_allows(scopes: FrozenSet[str], key: str, value: Optional[str]) -> bool:
    if value is None:
        return True
    exact = f"{key}:{value}"
    wildcard = f"{key}:*"
    return exact in scopes or wildcard in scopes


def enforce_place_scope(ctx: WorkshopContext, payload_context: Dict[str, Any]) -> None:
    scene_id_obj = payload_context.get("scene_id")
    workspace_id_obj = payload_context.get("workspace_id")
    scene_id = scene_id_obj if isinstance(scene_id_obj, str) else None
    workspace_id = workspace_id_obj if isinstance(workspace_id_obj, str) else None

    if not scope_allows(ctx.scope.scopes, "scene", scene_id):
        raise PermissionError("scope_denied:scene")
    if not scope_allows(ctx.scope.scopes, "workspace", workspace_id):
        raise PermissionError("scope_denied:workspace")

