from __future__ import annotations

import pytest

from shygazun.kernel.policy.recombiner import (
    EngineAssembly,
    MeaningFrontier,
    ProseAssembly,
    frontier_canonical_json,
    frontier_hash,
    frontier_to_obj,
    frontier_for_akinenwun,
    parse_akinenwun,
    recombine,
)


def test_recombine_engine_groups_by_tongue_in_input_order() -> None:
    result = recombine([0, 24, 48, 72, 98, 128, 156], mode="engine")
    assert isinstance(result, EngineAssembly)
    assert result.decimals == (0, 24, 48, 72, 98, 128, 156)
    assert tuple(result.by_tongue.keys()) == (
        "Lotus",
        "Rose",
        "Sakura",
        "Daisy",
        "AppleBlossom",
        "Aster",
        "Grapevine",
    )
    assert result.by_tongue["Lotus"][0]["symbol"] == "Ty"
    assert result.by_tongue["Grapevine"][0]["symbol"] == "Sa"


def test_recombine_prose_is_explicitly_ambiguous_surface() -> None:
    result = recombine([0, 19, 45, 69], mode="prose")
    assert isinstance(result, ProseAssembly)
    assert result.decimals == (0, 19, 45, 69)
    assert "Earth Initiator / material beginning" in result.line
    assert "Experience / intuition" in result.line
    assert "Process / Way" in result.line
    assert "Death-moment / Never / Now" in result.line
    assert " ; " in result.line


def test_recombine_deterministic_for_same_input() -> None:
    first = recombine([6, 31, 54, 82, 108, 147, 168], mode="prose")
    second = recombine([6, 31, 54, 82, 108, 147, 168], mode="prose")
    assert isinstance(first, ProseAssembly)
    assert isinstance(second, ProseAssembly)
    assert first.line == second.line
    assert first.decimals == second.decimals


def test_parse_akinenwun_requires_compound_without_spaces() -> None:
    assert parse_akinenwun("TyKoWuVu") == ("Ty", "Ko", "Wu", "Vu")

    with pytest.raises(ValueError, match="must not contain spaces"):
        frontier_for_akinenwun("Ty Ko")


def test_frontier_for_akinenwun_returns_meaning_paths() -> None:
    frontier = frontier_for_akinenwun("TyKoWuVu", mode="prose")
    assert isinstance(frontier, MeaningFrontier)
    assert frontier.akinenwun == "TyKoWuVu"
    assert len(frontier.paths) >= 1
    first_path = frontier.paths[0]
    assert first_path.symbols == ("Ty", "Ko", "Wu", "Vu")
    assert first_path.decimals == (0, 19, 45, 69)
    assert isinstance(first_path.assembly, ProseAssembly)
    assert "Earth Initiator / material beginning" in first_path.assembly.line


def test_frontier_serialization_and_hash_are_deterministic() -> None:
    first = frontier_for_akinenwun("TyKoWuVu", mode="prose")
    second = frontier_for_akinenwun("TyKoWuVu", mode="prose")
    assert frontier_to_obj(first) == frontier_to_obj(second)
    assert frontier_canonical_json(first) == frontier_canonical_json(second)
    assert frontier_hash(first) == frontier_hash(second)
