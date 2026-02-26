from __future__ import annotations

from qqva.shygazun_compiler import (
    SymbolInventory,
    cobra_to_placement_payloads,
    compile_akinenwun_to_ir,
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
