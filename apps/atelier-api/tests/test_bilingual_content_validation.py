from __future__ import annotations

from atelier_api.validators import validate_kobra_content


def test_validate_kobra_content_emits_bilingual_stats_for_whale_alias() -> None:
    source = "\n".join(
        [
            "entity whale_1 0 0 fauna",
            "  lex Melkowuvune",
        ]
    )
    result = validate_kobra_content(source, realm_id="lapidus", scene_id="lapidus/test_scene")
    assert result.ok is True
    assert result.stats["entities"] == 1
    assert "bilingual_warning_count" in result.stats
    assert "bilingual_warnings" in result.stats


def test_validate_kobra_content_keeps_bilingual_warnings_empty_for_safe_surface() -> None:
    source = "\n".join(
        [
            "entity whale_1 0 0 fauna",
            "  lex Melkowuvune",
        ]
    )
    result = validate_kobra_content(source, realm_id="lapidus", scene_id="lapidus/test_scene")
    bilingual_warnings = result.stats["bilingual_warnings"]
    assert isinstance(bilingual_warnings, list)
    assert all(not warning.startswith("bilingual_") for warning in bilingual_warnings)
