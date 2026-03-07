from __future__ import annotations

from qqva.aster_colors import resolve_aster_color


def test_resolve_aster_color_supports_fused_compound_tokens() -> None:
    resolved = resolve_aster_color("Ruotki")
    assert resolved["canonical"] == "mix:ru+ot+ki"
    assert resolved["chirality"] == "mixed"
    assert resolved["components"] == ["ru", "ot", "ki"]
    assert resolved["rgb"].startswith("#")


def test_resolve_aster_color_supports_single_aster_tokens() -> None:
    resolved = resolve_aster_color("Ru")
    assert resolved["canonical"] == "ru"
    assert resolved["chirality"] == "aster"
    assert resolved["hue"] == "ru"
