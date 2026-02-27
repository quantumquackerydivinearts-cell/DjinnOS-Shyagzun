from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple


VALID_CACHE_POLICIES = {"cache", "stream", "pin"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_to_dict(engine_state: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(engine_state)


def _world_stream_obj(state_obj: Mapping[str, Any]) -> Dict[str, Any]:
    raw = state_obj.get("world_stream")
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _loaded_regions_obj(world_stream: Mapping[str, Any]) -> Dict[str, Any]:
    raw = world_stream.get("loaded_regions")
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _region_id(realm_id: str, region_key: str) -> str:
    return f"{realm_id.strip().lower()}::{region_key.strip()}"


def _normalize_cache_policy(cache_policy: str) -> str:
    normalized = (cache_policy or "").strip().lower() or "cache"
    if normalized not in VALID_CACHE_POLICIES:
        raise ValueError("invalid_cache_policy")
    return normalized


def _normalize_realm_id(realm_id: str) -> str:
    value = realm_id.strip().lower()
    if not value:
        raise ValueError("realm_id_required")
    return value


def _normalize_region_key(region_key: str) -> str:
    value = region_key.strip()
    if not value:
        raise ValueError("region_key_required")
    return value


class WorldStreamController:
    """Deterministic engine-state world region loader with cache policy handling."""

    def __init__(self, *, max_loaded_regions: int = 128) -> None:
        if max_loaded_regions <= 0:
            raise ValueError("max_loaded_regions_must_be_positive")
        self._max_loaded_regions = int(max_loaded_regions)

    @property
    def max_loaded_regions(self) -> int:
        return self._max_loaded_regions

    def load(
        self,
        engine_state: Mapping[str, Any],
        *,
        realm_id: str,
        region_key: str,
        payload: Mapping[str, Any],
        payload_hash: str,
        cache_policy: str = "cache",
    ) -> Dict[str, Any]:
        normalized_realm = _normalize_realm_id(realm_id)
        normalized_key = _normalize_region_key(region_key)
        normalized_policy = _normalize_cache_policy(cache_policy)
        region_id = _region_id(normalized_realm, normalized_key)
        now_iso = _now_iso()

        state_obj = _state_to_dict(engine_state)
        world_stream = _world_stream_obj(state_obj)
        loaded = _loaded_regions_obj(world_stream)
        loaded[region_id] = {
            "realm_id": normalized_realm,
            "region_key": normalized_key,
            "payload": dict(payload),
            "payload_hash": str(payload_hash),
            "cache_policy": normalized_policy,
            "loaded_at": now_iso,
        }

        loaded = self._evict_if_needed(loaded, recently_loaded_region_id=region_id)
        world_stream["loaded_regions"] = loaded
        world_stream["loaded_count"] = len(loaded)
        world_stream["last_loaded"] = {"realm_id": normalized_realm, "region_key": normalized_key}
        state_obj["world_stream"] = world_stream
        return state_obj

    def unload(self, engine_state: Mapping[str, Any], *, realm_id: str, region_key: str) -> Dict[str, Any]:
        normalized_realm = _normalize_realm_id(realm_id)
        normalized_key = _normalize_region_key(region_key)
        region_id = _region_id(normalized_realm, normalized_key)

        state_obj = _state_to_dict(engine_state)
        world_stream = _world_stream_obj(state_obj)
        loaded = _loaded_regions_obj(world_stream)
        loaded.pop(region_id, None)
        world_stream["loaded_regions"] = loaded
        world_stream["loaded_count"] = len(loaded)
        world_stream["last_unloaded"] = {"realm_id": normalized_realm, "region_key": normalized_key}
        state_obj["world_stream"] = world_stream
        return state_obj

    def _evict_if_needed(
        self,
        loaded_regions: Mapping[str, Any],
        *,
        recently_loaded_region_id: str,
    ) -> Dict[str, Any]:
        loaded = dict(loaded_regions)
        if len(loaded) <= self._max_loaded_regions:
            return loaded

        evictable: List[Tuple[str, str]] = []
        for region_id, row in loaded.items():
            if region_id == recently_loaded_region_id:
                continue
            if not isinstance(row, dict):
                continue
            policy = str(row.get("cache_policy", "cache")).strip().lower()
            if policy == "pin":
                continue
            loaded_at = str(row.get("loaded_at", ""))
            evictable.append((region_id, loaded_at))

        evictable.sort(key=lambda item: (item[1], item[0]))
        target_count = self._max_loaded_regions
        while len(loaded) > target_count and evictable:
            region_id, _ = evictable.pop(0)
            loaded.pop(region_id, None)
        return loaded
