from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, TypedDict


class SymbolAtom(TypedDict):
    symbol: str
    decimal: Optional[int]
    tongue: Optional[str]
    meaning: Optional[str]
    declensional: bool


class ShygazunIR(TypedDict):
    akinenwun: str
    symbols: List[SymbolAtom]
    canonical_compound: str
    unresolved: List[str]


class CobraPlacementPayload(TypedDict):
    raw: str
    scene_id: str
    context: Dict[str, Any]


class ByteEntry(TypedDict):
    decimal: int
    tongue: str
    symbol: str
    meaning: str


@dataclass(frozen=True)
class SymbolInventory:
    by_symbol: Mapping[str, Sequence[ByteEntry]]

    def entries_for(self, symbol: str) -> Sequence[ByteEntry]:
        return self.by_symbol.get(symbol, ())


def _load_inventory_from_shygazun_module() -> Optional[SymbolInventory]:
    try:
        from shygazun.kernel.constants.byte_table import SHYGAZUN_SYMBOL_INDEX  # type: ignore

        by_symbol: Dict[str, List[ByteEntry]] = {}
        for symbol, entries in SHYGAZUN_SYMBOL_INDEX.items():
            mapped: List[ByteEntry] = []
            for entry in entries:
                mapped.append(
                    {
                        "decimal": int(entry["decimal"]),
                        "tongue": str(entry["tongue"]),
                        "symbol": str(entry["symbol"]),
                        "meaning": str(entry["meaning"]),
                    }
                )
            by_symbol[str(symbol)] = mapped
        return SymbolInventory(by_symbol=by_symbol)
    except Exception:
        return None


def _load_inventory_from_nested_repo() -> Optional[SymbolInventory]:
    root = Path(__file__).resolve().parents[1]
    module_path = root / "DjinnOS-Shyagzun" / "shygazun" / "kernel" / "constants" / "byte_table.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("nested_shygazun_byte_table", str(module_path))
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw_index = getattr(module, "SHYGAZUN_SYMBOL_INDEX", None)
    if not isinstance(raw_index, dict):
        return None
    by_symbol: Dict[str, List[ByteEntry]] = {}
    for symbol_obj, entries_obj in raw_index.items():
        symbol = str(symbol_obj)
        mapped: List[ByteEntry] = []
        if isinstance(entries_obj, (list, tuple)):
            for entry_obj in entries_obj:
                if not isinstance(entry_obj, dict):
                    continue
                mapped.append(
                    {
                        "decimal": int(entry_obj["decimal"]),
                        "tongue": str(entry_obj["tongue"]),
                        "symbol": str(entry_obj["symbol"]),
                        "meaning": str(entry_obj["meaning"]),
                    }
                )
        if mapped:
            by_symbol[symbol] = mapped
    if not by_symbol:
        return None
    return SymbolInventory(by_symbol=by_symbol)


def default_symbol_inventory() -> SymbolInventory:
    loaded = _load_inventory_from_shygazun_module()
    if loaded is not None:
        return loaded
    loaded = _load_inventory_from_nested_repo()
    if loaded is not None:
        return loaded
    raise RuntimeError("shygazun_symbol_inventory_unavailable")


def split_akinenwun(akinenwun: str) -> List[str]:
    raw = akinenwun.strip()
    if raw == "":
        return []
    parts = re.findall(r"[A-Z]+[a-z]*", raw)
    if not parts:
        return [raw]
    return parts


def compile_akinenwun_to_ir(
    akinenwun: str,
    *,
    inventory: Optional[SymbolInventory] = None,
) -> ShygazunIR:
    symbol_inventory = inventory if inventory is not None else default_symbol_inventory()
    symbols = split_akinenwun(akinenwun)
    atoms: List[SymbolAtom] = []
    unresolved: List[str] = []
    for symbol in symbols:
        entries = symbol_inventory.entries_for(symbol)
        if len(entries) == 0:
            unresolved.append(symbol)
            atoms.append(
                {
                    "symbol": symbol,
                    "decimal": None,
                    "tongue": None,
                    "meaning": None,
                    "declensional": False,
                }
            )
            continue
        first = entries[0]
        atoms.append(
            {
                "symbol": symbol,
                "decimal": int(first["decimal"]),
                "tongue": str(first["tongue"]),
                "meaning": str(first["meaning"]),
                "declensional": len(entries) > 1,
            }
        )
    return {
        "akinenwun": akinenwun.strip(),
        "symbols": atoms,
        "canonical_compound": "".join([atom["symbol"] for atom in atoms]),
        "unresolved": unresolved,
    }


def emit_cobra_entity(
    *,
    entity_id: str,
    x: int,
    y: int,
    tag: str,
    akinenwun: str,
    attributes: Optional[Mapping[str, str]] = None,
) -> str:
    lines: List[str] = [f"entity {entity_id} {x} {y} {tag}", f"  lex {akinenwun.strip()}"]
    if attributes is not None:
        for key in sorted(attributes.keys()):
            lines.append(f"  {key} {attributes[key]}")
    return "\n".join(lines)


def _parse_cobra_entities(source: str) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for raw_line in source.splitlines():
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if line == "" or line.startswith("#"):
            continue
        if indent > 0 and current is not None:
            colon = line.find(":")
            if colon > 0:
                key = line[:colon].strip()
                value = line[colon + 1 :].strip()
            else:
                parts = line.split(maxsplit=1)
                key = parts[0]
                value = parts[1] if len(parts) == 2 else ""
            current["meta"][key] = value
            if key in ("lex", "akinenwun", "shygazun"):
                current["akinenwun"] = value
            continue
        if line.startswith("entity "):
            parts = line.split()
            current = {
                "id": parts[1] if len(parts) > 1 else "anon",
                "x": int(parts[2]) if len(parts) > 2 and parts[2].lstrip("-").isdigit() else 0,
                "y": int(parts[3]) if len(parts) > 3 and parts[3].lstrip("-").isdigit() else 0,
                "tag": parts[4] if len(parts) > 4 else "none",
                "meta": {},
                "akinenwun": "",
            }
            entities.append(current)
            continue
        current = None
    return entities


def cobra_to_placement_payloads(
    source: str,
    *,
    scene_id: str,
    workspace_id: str,
    inventory: Optional[SymbolInventory] = None,
) -> List[CobraPlacementPayload]:
    symbol_inventory = inventory if inventory is not None else default_symbol_inventory()
    entities = _parse_cobra_entities(source)
    payloads: List[CobraPlacementPayload] = []
    for entity in entities:
        akinenwun = str(entity.get("akinenwun", "") or "")
        ir = compile_akinenwun_to_ir(akinenwun, inventory=symbol_inventory) if akinenwun else {
            "akinenwun": "",
            "symbols": [],
            "canonical_compound": "",
            "unresolved": [],
        }
        raw = f"entity {entity['id']} {entity['x']} {entity['y']} {entity['tag']}"
        payloads.append(
            {
                "raw": raw,
                "scene_id": scene_id,
                "context": {
                    "workspace_id": workspace_id,
                    "cobra_entity": entity,
                    "shygazun_ir": ir,
                },
            }
        )
    return payloads


def compile_akinenwun_batch(
    words: Iterable[str],
    *,
    inventory: Optional[SymbolInventory] = None,
) -> List[ShygazunIR]:
    symbol_inventory = inventory if inventory is not None else default_symbol_inventory()
    return [compile_akinenwun_to_ir(word, inventory=symbol_inventory) for word in words]
