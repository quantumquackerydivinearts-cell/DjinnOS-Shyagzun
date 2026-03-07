from __future__ import annotations

from atelier_api.services import AtelierService


def test_translate_shygazun_runtime_uses_lesson_exact_projection_for_i_love_whales() -> None:
    result = AtelierService._translate_shygazun_runtime(
        {
            "source_text": "I love whales",
            "direction": "english_to_shygazun",
        }
    )
    assert result["target_text"] == "Aely Melkowuvune Awu"
    assert result["resolved_count"] == 3
    assert result["confidence"] == 1.0
    assert result["lexicon_version"] == "phase2.lesson-backed"


def test_translate_shygazun_runtime_uses_lesson_aliases_for_basic_reverse_lookup() -> None:
    result = AtelierService._translate_shygazun_runtime(
        {
            "source_text": "Awu Melkowuvune",
            "direction": "shygazun_to_english",
        }
    )
    assert result["target_text"] == "I whales"
    assert result["resolved_count"] == 2
    assert result["unresolved"] == []
