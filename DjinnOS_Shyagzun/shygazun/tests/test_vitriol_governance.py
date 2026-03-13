from __future__ import annotations

from shygazun.kernel.breath import assemble_vitriol_vector
from shygazun.kernel.constants.vitriol import (
    VITRIOL_GOVERNANCE_ORDER,
    VITRIOL_LETTERS,
    VITRIOL_MAPPING,
)


def test_vitriol_order_locked() -> None:
    assert VITRIOL_GOVERNANCE_ORDER == (
        "Asmodeus",
        "Satan",
        "Beelzebub",
        "Belphegor",
        "Leviathan",
        "Mammon",
        "Lucifer",
    )


def test_vitriol_letter_order_locked() -> None:
    assert VITRIOL_LETTERS == (
        "Vitality",
        "Introspection",
        "Tactility",
        "Reflectivity",
        "Ingenuity",
        "Ostentation",
        "Levity",
    )


def test_vitriol_mapping_alignment() -> None:
    expected = {
        "Vitality": "Asmodeus",
        "Introspection": "Satan",
        "Tactility": "Beelzebub",
        "Reflectivity": "Belphegor",
        "Ingenuity": "Leviathan",
        "Ostentation": "Mammon",
        "Levity": "Lucifer",
    }
    assert VITRIOL_MAPPING == expected


def test_breath_regression_fixture() -> None:
    fixture_metrics = {
        "Vitality": 0.1,
        "Introspection": 0.2,
        "Tactility": 0.3,
        "Reflectivity": 0.4,
        "Ingenuity": 0.5,
        "Ostentation": 0.6,
        "Levity": 0.7,
    }

    vector = assemble_vitriol_vector(fixture_metrics)
    assert vector == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
