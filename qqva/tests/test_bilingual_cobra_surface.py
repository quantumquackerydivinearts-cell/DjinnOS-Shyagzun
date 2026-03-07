from __future__ import annotations

from qqva.scene_graph import build_scene_graph_from_cobra
from qqva.shygazun_compiler import cobra_to_placement_payloads, derive_bilingual_cobra_surface
from qqva.validators import validate_cobra_content


def test_derive_bilingual_cobra_surface_returns_kernel_backed_payload() -> None:
    payload = derive_bilingual_cobra_surface("Aely Melkowuvune Owu")
    assert payload is not None
    assert payload["authoritative_projection"]["english"] == "We love whales"
    assert payload["code_surface"]["entity_traits"]["animacy"] == "animate"
    assert payload["placement_graph"]["projection_hints"]["animate"] is True


def test_cobra_to_placement_payloads_embeds_bilingual_surface() -> None:
    source = "\n".join(
        [
            "entity whale_1 0 0 fauna",
            "  lex Melkowuvune",
        ]
    )
    payloads = cobra_to_placement_payloads(
        source,
        scene_id="lapidus/test_scene",
        workspace_id="main",
        realm_id="lapidus",
    )
    assert len(payloads) == 1
    bilingual_surface = payloads[0]["context"]["bilingual_cobra_surface"]
    assert bilingual_surface is not None
    assert bilingual_surface["composed_features"]["anatomy_derivation"] == "rose_daisy_structural_metaphor"


def test_scene_graph_embeds_bilingual_surface_in_node_metadata() -> None:
    source = "\n".join(
        [
            "entity whale_1 0 0 fauna",
            "  lex Melkowuvune",
        ]
    )
    graph = build_scene_graph_from_cobra(source, realm_id="lapidus", scene_id="lapidus/test_scene")
    node = graph["nodes"][0]
    bilingual_surface = node["metadata"]["bilingual_cobra_surface"]
    assert bilingual_surface["trust_contract"]["downstream_readiness"]["placement_graph_safe"] is True
    assert bilingual_surface["placement_graph"]["projection_hints"]["anatomy_derivation"] == "rose_daisy_structural_metaphor"


def test_validate_cobra_content_checks_bilingual_readiness() -> None:
    source = "\n".join(
        [
            "entity whale_1 0 0 fauna",
            "  lex Melkowuvune",
        ]
    )
    result = validate_cobra_content(source, realm_id="lapidus", scene_id="lapidus/test_scene")
    assert result.ok is True
    assert all(not warning.startswith("bilingual_") for warning in result.warnings)
