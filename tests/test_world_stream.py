from __future__ import annotations

from typing import Any, Dict

import pytest

from qqva.world_stream import WorldStreamController


def _loaded_ids(state: Dict[str, Any]) -> list[str]:
    world_stream = state.get("world_stream")
    if not isinstance(world_stream, dict):
        return []
    loaded = world_stream.get("loaded_regions")
    if not isinstance(loaded, dict):
        return []
    return sorted(loaded.keys())


def test_world_stream_load_and_unload_round_trip() -> None:
    controller = WorldStreamController(max_loaded_regions=4)
    state: Dict[str, Any] = {}
    loaded = controller.load(
        state,
        realm_id="lapidus",
        region_key="room_a",
        payload={"tiles": [1, 2]},
        payload_hash="h-room-a",
        cache_policy="cache",
    )
    assert loaded["world_stream"]["loaded_count"] == 1
    assert _loaded_ids(loaded) == ["lapidus::room_a"]

    unloaded = controller.unload(loaded, realm_id="lapidus", region_key="room_a")
    assert unloaded["world_stream"]["loaded_count"] == 0
    assert _loaded_ids(unloaded) == []


def test_world_stream_load_normalizes_inputs() -> None:
    controller = WorldStreamController(max_loaded_regions=2)
    loaded = controller.load(
        {},
        realm_id="  LAPIDUS ",
        region_key=" room_a ",
        payload={},
        payload_hash="h",
        cache_policy=" Stream ",
    )
    row = loaded["world_stream"]["loaded_regions"]["lapidus::room_a"]
    assert row["realm_id"] == "lapidus"
    assert row["region_key"] == "room_a"
    assert row["cache_policy"] == "stream"


def test_world_stream_rejects_invalid_cache_policy() -> None:
    controller = WorldStreamController()
    with pytest.raises(ValueError):
        controller.load(
            {},
            realm_id="lapidus",
            region_key="room_a",
            payload={},
            payload_hash="h",
            cache_policy="bad-policy",
        )


def test_world_stream_evicts_oldest_non_pinned_when_over_limit() -> None:
    controller = WorldStreamController(max_loaded_regions=2)
    state: Dict[str, Any] = {}
    state = controller.load(
        state,
        realm_id="lapidus",
        region_key="pinned_room",
        payload={},
        payload_hash="h1",
        cache_policy="pin",
    )
    state = controller.load(
        state,
        realm_id="lapidus",
        region_key="cache_room",
        payload={},
        payload_hash="h2",
        cache_policy="cache",
    )
    state = controller.load(
        state,
        realm_id="lapidus",
        region_key="stream_room",
        payload={},
        payload_hash="h3",
        cache_policy="stream",
    )
    # cache_room is the oldest evictable entry.
    assert _loaded_ids(state) == ["lapidus::pinned_room", "lapidus::stream_room"]

