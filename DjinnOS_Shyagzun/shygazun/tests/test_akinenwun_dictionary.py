from __future__ import annotations

from shygazun.kernel.policy.akinenwun_dictionary import AkinenwunDictionary
from shygazun.kernel.policy.recombiner import frontier_for_akinenwun


def test_dictionary_ingests_frontier_and_indexes_by_word_and_hash() -> None:
    dictionary = AkinenwunDictionary()
    frontier = frontier_for_akinenwun("TyKoWuVu", mode="prose")

    entry = dictionary.ingest_frontier(frontier)
    assert entry.akinenwun == "TyKoWuVu"
    assert entry.mode == "prose"
    assert entry.frontier_hash.startswith("h_")

    by_word = dictionary.get("TyKoWuVu", mode="prose")
    assert by_word is not None
    assert by_word.frontier_hash == entry.frontier_hash

    by_hash = dictionary.get_by_hash(entry.frontier_hash)
    assert by_hash is not None
    assert by_hash.akinenwun == "TyKoWuVu"


def test_dictionary_entries_are_sorted_by_word_and_mode() -> None:
    dictionary = AkinenwunDictionary()
    dictionary.ingest_frontier(frontier_for_akinenwun("TyKo", mode="prose"))
    dictionary.ingest_frontier(frontier_for_akinenwun("TyKo", mode="engine"))
    dictionary.ingest_frontier(frontier_for_akinenwun("TyKoWuVu", mode="prose"))

    entries = dictionary.entries()
    assert len(entries) == 3
    keys = [(entry.akinenwun, entry.mode) for entry in entries]
    assert keys == sorted(keys)
