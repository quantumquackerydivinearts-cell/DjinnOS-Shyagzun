from __future__ import annotations

import pytest

from qqva.shygazun_compiler import (
    SymbolInventory,
    cobra_to_placement_payloads,
    compile_akinenwun_to_ir,
    derive_render_constraints,
    emit_cobra_entity,
    split_akinenwun,
)


def _inventory() -> SymbolInventory:
    return SymbolInventory(
        by_symbol={
            "Ty": [{"decimal": 0, "tongue": "Lotus", "symbol": "Ty", "meaning": "Earth Initiator"}],
            "Ko": [{"decimal": 19, "tongue": "Lotus", "symbol": "Ko", "meaning": "Experience"}],
            "Wu": [{"decimal": 45, "tongue": "Rose", "symbol": "Wu", "meaning": "Process"}],
            "Vu": [{"decimal": 69, "tongue": "Sakura", "symbol": "Vu", "meaning": "Never / Now"}],
        }
    )


def test_split_akinenwun() -> None:
    assert split_akinenwun("TyKoWuVu") == ["Ty", "Ko", "Wu", "Vu"]


def test_compile_akinenwun_to_ir() -> None:
    ir = compile_akinenwun_to_ir("TyKoWuVu", inventory=_inventory())
    assert ir["canonical_compound"] == "TyKoWuVu"
    assert ir["unresolved"] == []
    assert [atom["decimal"] for atom in ir["symbols"]] == [0, 19, 45, 69]


def test_emit_cobra_entity() -> None:
    cobra = emit_cobra_entity(entity_id="gate_01", x=12, y=8, tag="portal", akinenwun="TyKoWuVu")
    assert "entity gate_01 12 8 portal" in cobra
    assert "  lex TyKoWuVu" in cobra


def test_cobra_to_placement_payloads() -> None:
    source = "\n".join(
        [
            "entity gate_01 12 8 portal",
            "  lex TyKoWuVu",
            "  layer foreground",
        ]
    )
    payloads = cobra_to_placement_payloads(
        source,
        scene_id="renderer-lab",
        workspace_id="main",
        inventory=_inventory(),
    )
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["raw"] == "entity gate_01 12 8 portal"
    assert payload["scene_id"] == "renderer-lab"
    assert payload["context"]["workspace_id"] == "main"
    ir = payload["context"]["shygazun_ir"]
    assert isinstance(ir, dict)
    assert ir["canonical_compound"] == "TyKoWuVu"
    assert payload["context"]["identity"]["entity_id"] == "gate_01"
    assert payload["context"]["identity"]["tag"] == "portal"
    assert payload["context"]["render_constraints"]["use_case"] == "render"
    assert "edge_weight_bias" in payload["context"]["frontier_policy"]
    material = payload["context"]["render_constraints"]["material_library"]
    if material:
        assert "density" in material[0]["properties"]


def test_cobra_to_placement_payloads_is_deterministic() -> None:
    source = "\n".join(
        [
            "entity gate_01 12 8 portal",
            "  lex TyKoWuVu",
            "  layer foreground",
        ]
    )
    first = cobra_to_placement_payloads(
        source,
        scene_id="renderer-lab",
        workspace_id="main",
        inventory=_inventory(),
    )
    second = cobra_to_placement_payloads(
        source,
        scene_id="renderer-lab",
        workspace_id="main",
        inventory=_inventory(),
    )
    assert first == second


def test_recombined_materials_for_apple_blossom() -> None:
    pytest.importorskip("shygazun.kernel.policy.recombiner")
    inventory = SymbolInventory(
        by_symbol={
            "Shak": [
                {"decimal": 1, "tongue": "AppleBlossom", "symbol": "Shak", "meaning": "Fire"}
            ],
            "Puf": [
                {"decimal": 5, "tongue": "AppleBlossom", "symbol": "Puf", "meaning": "Air"}
            ],
        }
    )
    ir = compile_akinenwun_to_ir("ShakPuf", inventory=inventory)
    constraints = derive_render_constraints(ir)
    material = constraints["material_library"]
    symbols = [entry["symbol"] for entry in material]
    assert "Shak" in symbols
    assert "Puf" in symbols
    recombined = [entry for entry in material if entry["symbol"].startswith("AB:")]
    assert recombined
    assert recombined[0]["properties"]["recombined_from"] == ["Shak", "Puf"]


def test_grapevine_alchemy_interface() -> None:
    inventory = SymbolInventory(
        by_symbol={
            "Ru": [{"decimal": 0, "tongue": "Grapevine", "symbol": "Ru", "meaning": "Anchor"}],
            "Ki": [{"decimal": 3, "tongue": "Grapevine", "symbol": "Ki", "meaning": "Stability"}],
            "AE": [{"decimal": 6, "tongue": "Grapevine", "symbol": "AE", "meaning": "Flux"}],
        }
    )
    ir = compile_akinenwun_to_ir("RuKiAE", inventory=inventory)
    constraints = derive_render_constraints(ir)
    alchemy = constraints["alchemy_interface"]
    assert alchemy["enabled"] is True
    assert alchemy["symbols"] == ["Ru", "Ki", "AE"]
    stages = alchemy["stages"]
    assert len(stages) == 3
    assert stages[0]["role"] == "catalyst"
    assert stages[-1]["role"] == "binder"
