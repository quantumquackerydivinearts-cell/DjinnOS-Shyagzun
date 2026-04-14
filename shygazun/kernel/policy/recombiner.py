from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
from itertools import product
import json
from typing import Dict, Final, Literal, Mapping, Sequence, Tuple, TypeAlias, Union

from ..constants.byte_table import (
    SHYGAZUN_SYMBOL_INDEX,
    ShygazunByteEntry,
    byte_entry,
    symbol_entries,
)
from ..constants.tongue_topology import TONGUE_REGISTRY


RecombinerMode = Literal["engine", "prose"]

_TONGUE_ORDER: Final[Tuple[str, ...]] = tuple(t.name for t in TONGUE_REGISTRY)


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
    return next(iter(segmentations))


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


# VITRIOL stat keys in canonical order (V I T R I O L).
# Each Shygazun tongue maps to one stat — placing words from that tongue
# presses that stat in the Orrery's edge-weight accounting.
_TONGUE_VITRIOL: Dict[str, str] = {
    "Lotus":          "vitality",
    "Rose":           "ingenuity",
    "Sakura":         "reflectivity",
    "Daisy":          "tactility",
    "AppleBlossom":   "ingenuity",
    "Aster":          "reflectivity",
    "Grapevine":      "ostentation",
    "Cannabis":       "ostentation",
    "Dragon":         "introspection",
    "Virus":          "tactility",
    "Bacteria":       "vitality",
    "Excavata":       "reflectivity",
    "Archaeplastida": "vitality",
    "Myxozoa":        "introspection",
    "Archaea":        "ingenuity",
    "Protist":        "levity",
    "Immune":         "introspection",
    "Neural":         "tactility",
    "Serpent":        "vitality",
    "Beast":          "vitality",
    "Cherub":         "ostentation",
    "Chimera":        "ingenuity",
    "Faerie":         "ostentation",
    "Djinn":          "levity",
    "Fold":           "reflectivity",
    "Topology":       "ingenuity",
    "Phase":          "levity",
    "Gradient":       "tactility",
    "Curvature":      "ingenuity",
}

_VITRIOL_KEYS: Tuple[str, ...] = (
    "vitality", "introspection", "tactility", "reflectivity",
    "ingenuity", "ostentation", "levity",
)

# Sub-axis VITRIOL overrides keyed by byte address range (lo, hi_inclusive, stat).
# Ranges omitted here fall through to _TONGUE_VITRIOL tongue-level default.
_DECIMAL_VITRIOL_RANGES: Final[Tuple[Tuple[int, int, str], ...]] = (
    # Dragon — Dva (Spatial voids) → reflectivity; Kwe (Temporal voids) → levity
    (266, 275, "reflectivity"),
    (276, 285, "levity"),
    # Virus — Pla (Ordinal) → levity; Wik (Catalytic) → ingenuity
    (286, 295, "levity"),
    (306, 315, "ingenuity"),
    # Bacteria — Zho (Mind) → introspection; Ri (Time) → levity
    (316, 325, "introspection"),
    (326, 335, "levity"),
    # Excavata — Ran (Rotation) → levity; Yef (Traversal) → tactility; closure → introspection
    (346, 355, "levity"),
    (356, 365, "tactility"),
    (376, 377, "introspection"),
    # Archaeplastida — Mel (Water-Incidental) → tactility; Puf (Air-Constitutive) → ingenuity; Shak (Fire-Incidental) → ostentation
    (386, 393, "tactility"),
    (394, 401, "ingenuity"),
    (402, 409, "ostentation"),
    # Myxozoa — Oa axis → reflectivity; Nav axis → vitality (positive and -lo)
    (416, 421, "reflectivity"),
    (422, 426, "vitality"),
    (433, 438, "reflectivity"),
    (439, 443, "vitality"),
    # Archaea — Eth axis → introspection; Urg axis → tactility (positive and -lo)
    (444, 449, "introspection"),
    (450, 455, "tactility"),
    (461, 466, "introspection"),
    (467, 472, "tactility"),
    # Protist — Oi axis → tactility; Grev axis → reflectivity (positive and -lo)
    (484, 489, "tactility"),
    (490, 494, "reflectivity"),
    (501, 506, "tactility"),
    (507, 511, "reflectivity"),
    # Immune — Rek axis → vitality; Trev axis → ingenuity (positive and -lo)
    (518, 523, "vitality"),
    (524, 528, "ingenuity"),
    (535, 540, "vitality"),
    (541, 545, "ingenuity"),
    # Neural — Nal axis → reflectivity; Drev axis → vitality (positive and -lo)
    (552, 557, "reflectivity"),
    (558, 563, "vitality"),
    (570, 575, "reflectivity"),
    (576, 581, "vitality"),
    # Serpent — element axis determines stat (Fire=vitality matches dominant)
    (588, 593, "tactility"),      # Water x dimensions
    (594, 599, "ingenuity"),      # Air x dimensions
    (600, 605, "reflectivity"),   # Earth x dimensions
    (606, 611, "levity"),         # Seed x dimensions
    (612, 617, "introspection"),  # Shakti x dimensions
    # Beast — Gev (winding) → ostentation; Drek (binding) → ingenuity; closure → introspection
    (618, 623, "ostentation"),
    (630, 635, "ingenuity"),
    (636, 641, "ostentation"),
    (648, 653, "ingenuity"),
    (654, 655, "introspection"),
    # Cherub — Threl (tension) → ingenuity; Vlov (transmutation) → tactility; closure → introspection
    (662, 667, "ingenuity"),
    (668, 673, "tactility"),
    (680, 685, "ingenuity"),
    (686, 691, "tactility"),
    (692, 693, "introspection"),
    # Chimera — Glov (constitutional knowing) → introspection; Wrek (form-transition) → levity; closure → introspection
    (694, 699, "introspection"),
    (706, 711, "levity"),
    (712, 717, "introspection"),
    (724, 729, "levity"),
    (730, 731, "introspection"),
    # Faerie — Zel (elemental recognition) → introspection; Plov (sovereignty) → vitality; closure → introspection
    (738, 743, "introspection"),
    (744, 749, "vitality"),
    (756, 761, "introspection"),
    (762, 767, "vitality"),
    (768, 769, "introspection"),
    # Djinn — dimension determines stat: A/O (Mind) → introspection; I/E (Space) → reflectivity; Y/U (Time) → levity (matches dominant); subregisters → introspection
    (770, 775, "introspection"),  # A x elements (Mind+)
    (776, 781, "introspection"),  # O x elements (Mind-)
    (782, 787, "reflectivity"),   # I x elements (Space+)
    (788, 793, "reflectivity"),   # E x elements (Space-)
    (806, 809, "introspection"),  # subregisters (closure)
    # Fold — zone determines stat (Jos×Vex and Das×Vex match dominant reflectivity)
    (810, 813, "vitality"),       # Jos×Jos: maximum compression
    (814, 817, "tactility"),      # Jos×Blis: compression-flow boundary
    (818, 821, "ingenuity"),      # Jos×Das: compression-open boundary
    (826, 829, "tactility"),      # Blis×Blis: bilateral flow
    (830, 833, "levity"),         # Blis×Das: flow-open boundary
    (834, 837, "vitality"),       # Blis×Vex: flow-surface boundary
    (838, 841, "ingenuity"),      # Das×Das: maximum spatial openness
    (846, 849, "ostentation"),    # Vex×Vex: maximum information density / Olympus
    # Topology — primitive determines stat (Torev×Torev matches dominant ingenuity)
    (856, 861, "reflectivity"),   # Torev×Glaen
    (862, 867, "tactility"),      # Torev×Fulnaz
    (868, 873, "introspection"),  # Torev×Zhifan
    (874, 879, "reflectivity"),   # Glaen×Glaen
    (880, 885, "tactility"),      # Glaen×Fulnaz
    (886, 889, "introspection"),  # Glaen×Zhifan
    # Phase — transition determines stat (Water→Air matches dominant levity)
    (890, 895, "vitality"),       # Fire→Water: Nigredo / hydrophobic collapse
    (902, 907, "ingenuity"),      # Air→Earth: Citrinitas / cooperative folding
    (908, 913, "ostentation"),    # Earth→Fire: Rubedo / allostery
    (914, 919, "ingenuity"),      # Kael→Shakti: phase separation
    (920, 925, "introspection"),  # Shakti→Kael: exotic state generation
    (926, 929, "introspection"),  # Mobius closure
    # Gradient — gradient type determines stat (Skath×Skath matches dominant tactility)
    (930, 933, "vitality"),       # Drev×Drev: descent
    (938, 941, "ingenuity"),      # Phelv×Phelv: saddle / transition state
    (942, 945, "reflectivity"),   # Zoln×Zoln: basin / equilibrium
    (946, 949, "vitality"),       # Drev×Skath: descent meeting barrier
    (950, 953, "vitality"),       # Drev×Phelv: descent approaching saddle
    (954, 957, "vitality"),       # Drev×Zoln: descent completing into basin
    (962, 965, "reflectivity"),   # Skath×Zoln: barrier finding its basin
    (966, 969, "ingenuity"),      # Phelv×Zoln: saddle completing into new basin
    # Curvature — curvature type determines stat (Frenz×Frenz and Frenz×Glathn match dominant ingenuity)
    (970, 973, "vitality"),       # Vresk×Vresk: bowl / positive curvature
    (974, 977, "ostentation"),    # Tholv×Tholv: dome / negative curvature
    (982, 985, "levity"),         # Glathn×Glathn: flat / near-zero curvature
    (986, 989, "reflectivity"),   # Vresk×Tholv: curvature inversion
    (990, 993, "vitality"),       # Vresk×Frenz: bowl approaching saddle
    (994, 997, "levity"),         # Vresk×Glathn: bowl grading to flat
    (998, 1001, "ostentation"),   # Tholv×Frenz: dome meeting saddle
    (1002, 1005, "levity"),       # Tholv×Glathn: dome fading to flat
)

# Byte address ranges whose entries are -lo (universalized error / mode-capture) forms.
# These press the same VITRIOL stat as their positive axis but carry a dissonance flag.
_DISSONANCE_RANGES: Final[Tuple[Tuple[int, int], ...]] = (
    (427, 443),   # Myxozoa -lo (Iv-lo, Oa-lo, Nav-lo)
    (461, 477),   # Archaea -lo (Eth-lo, Urg-lo, Krev-lo)
    (495, 511),   # Protist -lo (Ae-lo, Oi-lo, Grev-lo)
    (529, 545),   # Immune -lo (Siv-lo, Rek-lo, Trev-lo)
    (564, 581),   # Neural -lo (Vel-lo, Nal-lo, Drev-lo)
    (636, 653),   # Beast -lo (Gev-lo, Pral-lo, Drek-lo)
    (674, 691),   # Cherub -lo (Shev-lo, Threl-lo, Vlov-lo)
    (712, 729),   # Chimera -lo (Glov-lo, Prest-lo, Wrek-lo)
    (750, 767),   # Faerie -lo (Fev-lo, Zel-lo, Plov-lo)
)


def _vitriol_stat_for_entry(entry: ShygazunByteEntry) -> str:
    decimal = entry["decimal"]
    for lo, hi, stat in _DECIMAL_VITRIOL_RANGES:
        if lo <= decimal <= hi:
            return stat
    return _TONGUE_VITRIOL.get(entry["tongue"], "ingenuity")


def _is_dissonant(decimal: int) -> bool:
    for lo, hi in _DISSONANCE_RANGES:
        if lo <= decimal <= hi:
            return True
    return False


def apply_frontier_policy(
    frontier_obj: Mapping[str, JsonValue],
    policy: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    """
    Attach VITRIOL weighting metadata without mutating canonical frontier contents.
    Each symbol is scored against its tongue's VITRIOL stat; bias values from
    policy.edge_weight_bias tune the per-stat weights.
    """
    paths_obj = frontier_obj.get("paths")
    if not isinstance(paths_obj, list):
        return dict(frontier_obj)
    bias_obj = policy.get("edge_weight_bias")
    bias = bias_obj if isinstance(bias_obj, dict) else {}

    def _bias_float(key: str) -> float:
        v = bias.get(key)
        return float(v) if isinstance(v, (int, float)) else 0.0

    stat_bias: Dict[str, float] = {k: _bias_float(k) for k in _VITRIOL_KEYS}

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
                sym_entry = entries[0] if entries else None
                tongue = sym_entry["tongue"] if sym_entry else ""
                decimal = sym_entry["decimal"] if sym_entry else -1
                stat = _vitriol_stat_for_entry(sym_entry) if sym_entry else "ingenuity"
                dissonant = _is_dissonant(decimal)
                weight_value = stat_bias[stat]
                stat_weights: Dict[str, float] = {k: 0.0 for k in _VITRIOL_KEYS}
                stat_weights[stat] = weight_value
                weight_entry = {
                    "symbol": symbol_str,
                    "tongue": tongue,
                    "vitriol_stat": stat,
                    "dissonant": dissonant,
                    "weights": stat_weights,
                }
                total_weight += weight_value
                weights.append(weight_entry)  # type: ignore[arg-type]
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
