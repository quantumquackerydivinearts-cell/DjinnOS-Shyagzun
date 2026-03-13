from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
from itertools import product
import json
from typing import Dict, Final, Literal, Mapping, Sequence, Tuple, TypeAlias, Union

from shygazun.kernel.constants.byte_table import (
    SHYGAZUN_SYMBOL_INDEX,
    ShygazunByteEntry,
    byte_entry,
    symbol_entries,
)


RecombinerMode = Literal["engine", "prose"]

_TONGUE_ORDER: Final[Tuple[str, ...]] = (
    "Lotus",
    "Rose",
    "Sakura",
    "Daisy",
    "AppleBlossom",
    "Aster",
    "Grapevine",
)


@dataclass(frozen=True)
class EngineAssembly:
    mode: Literal["engine"]
    decimals: Tuple[int, ...]
    entries: Tuple[ShygazunByteEntry, ...]
    by_tongue: Dict[str, Tuple[ShygazunByteEntry, ...]]
    symbol_declensions: Dict[str, Tuple[ShygazunByteEntry, ...]]


@dataclass(frozen=True)
class ProseAssembly:
    mode: Literal["prose"]
    decimals: Tuple[int, ...]
    entries: Tuple[ShygazunByteEntry, ...]
    line: str
    symbol_declensions: Dict[str, Tuple[ShygazunByteEntry, ...]]


Recombination = Union[EngineAssembly, ProseAssembly]

JsonValue: TypeAlias = Union[None, bool, int, float, str, list["JsonValue"], dict[str, "JsonValue"]]


@dataclass(frozen=True)
class MeaningPath:
    symbols: Tuple[str, ...]
    decimals: Tuple[int, ...]
    assembly: Recombination


@dataclass(frozen=True)
class MeaningFrontier:
    akinenwun: str
    mode: RecombinerMode
    paths: Tuple[MeaningPath, ...]


def recombine(
    decimals: Sequence[int],
    *,
    mode: RecombinerMode = "engine",
) -> Recombination:
    entries = tuple(byte_entry(decimal) for decimal in decimals)
    if mode == "engine":
        return compile_engine(entries, tuple(decimals))
    return compose_prose(entries, tuple(decimals))


def compile_engine(entries: Sequence[ShygazunByteEntry], decimals: Sequence[int]) -> EngineAssembly:
    grouped_mut: Dict[str, list[ShygazunByteEntry]] = {tongue: [] for tongue in _TONGUE_ORDER}
    for entry in entries:
        tongue = entry["tongue"]
        if tongue not in grouped_mut:
            grouped_mut[tongue] = []
        grouped_mut[tongue].append(entry)

    grouped: Dict[str, Tuple[ShygazunByteEntry, ...]] = {
        tongue: tuple(rows) for tongue, rows in grouped_mut.items() if rows
    }
    return EngineAssembly(
        mode="engine",
        decimals=tuple(decimals),
        entries=tuple(entries),
        by_tongue=grouped,
        symbol_declensions=_symbol_declensions(entries),
    )


def compose_prose(entries: Sequence[ShygazunByteEntry], decimals: Sequence[int]) -> ProseAssembly:
    # Prose mode is explicit: ambiguity is deliberate and surfaced as alternatives.
    rendered: list[str] = []
    for entry in entries:
        alternatives = tuple(item["meaning"] for item in symbol_entries(entry["symbol"]))
        if len(alternatives) == 1:
            rendered.append(alternatives[0])
        else:
            rendered.append("(" + " | ".join(alternatives) + ")")
    return ProseAssembly(
        mode="prose",
        decimals=tuple(decimals),
        entries=tuple(entries),
        line=" ; ".join(rendered),
        symbol_declensions=_symbol_declensions(entries),
    )


def _symbol_declensions(entries: Sequence[ShygazunByteEntry]) -> Dict[str, Tuple[ShygazunByteEntry, ...]]:
    declensions: Dict[str, Tuple[ShygazunByteEntry, ...]] = {}
    for entry in entries:
        symbol = entry["symbol"]
        if symbol not in declensions:
            declensions[symbol] = tuple(symbol_entries(symbol))
    return declensions


def parse_akinenwun(akinenwun: str) -> Tuple[str, ...]:
    segmentations = _segment_akinenwun(akinenwun)
    if not segmentations:
        raise ValueError("akinenwun cannot be segmented")
    if len(segmentations) > 1:
        raise ValueError("akinenwun has multiple segmentations; use frontier_for_akinenwun()")
    return segmentations[0]


def frontier_for_akinenwun(akinenwun: str, *, mode: RecombinerMode = "prose") -> MeaningFrontier:
    if not akinenwun:
        raise ValueError("akinenwun cannot be empty")
    if any(char.isspace() for char in akinenwun):
        raise ValueError("akinenwun must not contain spaces")

    segmentations = _segment_akinenwun(akinenwun)
    if not segmentations:
        raise ValueError("akinenwun cannot be segmented")

    paths: list[MeaningPath] = []
    for symbols in segmentations:
        option_rows = [tuple(symbol_entries(symbol)) for symbol in symbols]
        for selected in product(*option_rows):
            entries = tuple(selected)
            decimals = tuple(entry["decimal"] for entry in entries)
            assembly: Recombination
            if mode == "engine":
                assembly = compile_engine(entries, decimals)
            else:
                assembly = compose_prose(entries, decimals)
            paths.append(MeaningPath(symbols=symbols, decimals=decimals, assembly=assembly))

    return MeaningFrontier(akinenwun=akinenwun, mode=mode, paths=tuple(paths))


def _segment_akinenwun(akinenwun: str) -> Tuple[Tuple[str, ...], ...]:
    symbols = tuple(sorted(SHYGAZUN_SYMBOL_INDEX.keys(), key=lambda item: (-len(item), item)))

    @lru_cache(maxsize=None)
    def _walk(offset: int) -> Tuple[Tuple[str, ...], ...]:
        if offset == len(akinenwun):
            return (tuple(),)

        candidates: list[Tuple[str, ...]] = []
        for symbol in symbols:
            if akinenwun.startswith(symbol, offset):
                suffixes = _walk(offset + len(symbol))
                for suffix in suffixes:
                    candidates.append((symbol, *suffix))
        return tuple(candidates)

    return _walk(0)


def frontier_to_obj(frontier: MeaningFrontier) -> dict[str, JsonValue]:
    return {
        "akinenwun": frontier.akinenwun,
        "mode": frontier.mode,
        "paths": [_path_to_obj(path) for path in frontier.paths],
    }


def apply_frontier_policy(
    frontier_obj: Mapping[str, JsonValue],
    policy: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    """
    Attach weighting metadata without mutating canonical frontier contents.
    Weights are derived from tongue-aware bias rules in policy.
    """
    paths_obj = frontier_obj.get("paths")
    if not isinstance(paths_obj, list):
        return dict(frontier_obj)
    bias_obj = policy.get("edge_weight_bias")
    bias = bias_obj if isinstance(bias_obj, dict) else {}
    weight_map = {
        "Rose": ("relation", float(bias.get("relation", 0.0) or 0.0)),
        "Daisy": ("closure", float(bias.get("closure", 0.0) or 0.0)),
        "Aster": ("time", float(bias.get("time", 0.0) or 0.0)),
        "Grapevine": ("system", float(bias.get("system", 0.0) or 0.0)),
    }
    enriched_paths: list[JsonValue] = []
    for path in paths_obj:
        if not isinstance(path, dict):
            enriched_paths.append(path)
            continue
        symbols_obj = path.get("symbols")
        weights: list[JsonValue] = []
        total_weight = 0.0
        if isinstance(symbols_obj, list):
            for symbol in symbols_obj:
                symbol_str = str(symbol)
                entries = symbol_entries(symbol_str)
                tongue = entries[0]["tongue"] if entries else ""
                weight_key, weight_value = weight_map.get(tongue, ("relation", 0.0))
                weight_entry = {
                    "symbol": symbol_str,
                    "tongue": tongue,
                    "weights": {
                        "relation": weight_value if weight_key == "relation" else 0.0,
                        "closure": weight_value if weight_key == "closure" else 0.0,
                        "time": weight_value if weight_key == "time" else 0.0,
                        "system": weight_value if weight_key == "system" else 0.0,
                    },
                }
                total_weight += float(weight_value)
                weights.append(weight_entry)
        enriched = dict(path)
        enriched["edge_weights"] = weights
        enriched["path_weight"] = total_weight
        enriched_paths.append(enriched)
    enriched_frontier = dict(frontier_obj)
    enriched_frontier["policy"] = dict(policy)
    enriched_frontier["paths"] = enriched_paths
    return enriched_frontier


def frontier_canonical_json(frontier: MeaningFrontier) -> str:
    return json.dumps(frontier_to_obj(frontier), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def frontier_hash(frontier: MeaningFrontier) -> str:
    payload = frontier_canonical_json(frontier).encode("utf-8")
    return "h_" + hashlib.sha256(payload).hexdigest()


def _path_to_obj(path: MeaningPath) -> dict[str, JsonValue]:
    return {
        "symbols": list(path.symbols),
        "decimals": list(path.decimals),
        "assembly": _assembly_to_obj(path.assembly),
    }


def _assembly_to_obj(assembly: Recombination) -> dict[str, JsonValue]:
    entries: list[JsonValue] = [_entry_to_obj(entry) for entry in assembly.entries]
    symbol_declensions: dict[str, JsonValue] = {
        symbol: [_entry_to_obj(entry) for entry in variants]
        for symbol, variants in assembly.symbol_declensions.items()
    }
    base: dict[str, JsonValue] = {
        "mode": assembly.mode,
        "decimals": list(assembly.decimals),
        "entries": entries,
        "symbol_declensions": symbol_declensions,
    }
    if isinstance(assembly, EngineAssembly):
        by_tongue: dict[str, JsonValue] = {
            tongue: [_entry_to_obj(entry) for entry in grouped]
            for tongue, grouped in assembly.by_tongue.items()
        }
        base["by_tongue"] = by_tongue
    else:
        base["line"] = assembly.line
    return base


def _entry_to_obj(entry: ShygazunByteEntry) -> dict[str, JsonValue]:
    return {
        "decimal": entry["decimal"],
        "binary": entry["binary"],
        "tongue": entry["tongue"],
        "symbol": entry["symbol"],
        "meaning": entry["meaning"],
    }
