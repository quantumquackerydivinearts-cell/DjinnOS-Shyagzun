from __future__ import annotations

import pytest

from qqva.scene_graph import DEFAULT_LAYER_Z, build_scene_graph_from_cobra


def test_scene_graph_requires_realm_scene_id() -> None:
    source = "entity demo 1 2 marker\n  lex TyKoWuVu"
    with pytest.raises(ValueError):
        build_scene_graph_from_cobra(source, realm_id="lapidus", scene_id="lab")


def test_scene_graph_applies_layer_offsets() -> None:
    source = "\n".join(
        [
            "entity demo 1 2 marker",
            "  lex TyKoWuVu",
            "  layer foreground",
            "entity other 3 4 marker",
        ]
    )
    graph = build_scene_graph_from_cobra(source, realm_id="lapidus", scene_id="lapidus/lab")
    nodes = {node["id"]: node for node in graph["nodes"]}
    assert nodes["demo"]["layer"] == "foreground"
    assert nodes["demo"]["z"] == DEFAULT_LAYER_Z["foreground"]
    assert nodes["other"]["layer"] == "midground"
    assert nodes["other"]["z"] == DEFAULT_LAYER_Z["midground"]
