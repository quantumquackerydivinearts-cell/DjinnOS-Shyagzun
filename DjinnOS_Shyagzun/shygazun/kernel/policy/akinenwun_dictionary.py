from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from .recombiner import JsonValue, MeaningFrontier, frontier_hash, frontier_to_obj


@dataclass(frozen=True)
class DictionaryEntry:
    akinenwun: str
    mode: str
    frontier_hash: str
    frontier_obj: dict[str, JsonValue]


class AkinenwunDictionary:
    def __init__(self) -> None:
        self._by_word: Dict[Tuple[str, str], DictionaryEntry] = {}
        self._by_hash: Dict[str, DictionaryEntry] = {}

    def ingest_frontier(self, frontier: MeaningFrontier) -> DictionaryEntry:
        entry_hash = frontier_hash(frontier)
        entry = DictionaryEntry(
            akinenwun=frontier.akinenwun,
            mode=frontier.mode,
            frontier_hash=entry_hash,
            frontier_obj=frontier_to_obj(frontier),
        )
        key = (frontier.akinenwun, frontier.mode)
        self._by_word[key] = entry
        self._by_hash[entry_hash] = entry
        return entry

    def get(self, akinenwun: str, *, mode: str = "prose") -> Optional[DictionaryEntry]:
        return self._by_word.get((akinenwun, mode))

    def get_by_hash(self, entry_hash: str) -> Optional[DictionaryEntry]:
        return self._by_hash.get(entry_hash)

    def entries(self) -> Sequence[DictionaryEntry]:
        ordered_keys = sorted(self._by_word.keys())
        return tuple(self._by_word[key] for key in ordered_keys)
