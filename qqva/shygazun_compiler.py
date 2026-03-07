
from __future__ import annotations
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, TypedDict, cast

from .aster_colors import resolve_aster_color

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


class SceneGraphPayload(TypedDict):
    scene_id: str
    realm_id: str
    graph: Dict[str, Any]


class ByteEntry(TypedDict):
    decimal: int
    tongue: str
    symbol: str
    meaning: str


class RenderConstraintMaterial(TypedDict):
    symbol: str
    meaning: Optional[str]
    tongue: str
    properties: Dict[str, Any]


class RenderConstraintPalette(TypedDict):
    tongue: str
    symbols: List[str]


class RenderConstraints(TypedDict):
    use_case: str
    material_library: List[RenderConstraintMaterial]
    feature_palette: List[RenderConstraintPalette]
    feature_roles: Dict[str, str]
    symbol_sequence: List[str]
    unresolved: List[str]
    primary_tongue: Optional[str]
    frontier_policy: Dict[str, Any]
    rose_vector_calculus: Dict[str, Any]
    alchemy_interface: Dict[str, Any]


class PlacementIdentity(TypedDict):
    entity_id: str
    tag: str
    akinenwun: str


class DjinnLayerReferences(TypedDict):
    function_id: str
    function_version: str
    layer_projection_report: str
    reference_coeff_bp: int
    recursion_coeff_bp: int
    recursion_enabled: bool
    behavior_words: List[str]
    model: str


class BilingualCobraSurface(TypedDict, total=False):
    source_text: str
    authoritative_projection: Optional[Dict[str, Any]]
    composed_features: Dict[str, Any]
    byte_table_trace: Dict[str, Any]
    structural_verifications: List[Dict[str, Any]]
    code_surface: Dict[str, Any]
    placement_graph: Dict[str, Any]
    trust_contract: Dict[str, Any]


@dataclass(frozen=True)
class SymbolInventory:
    by_symbol: Mapping[str, Sequence[ByteEntry]]

    def entries_for(self, symbol: str) -> Sequence[ByteEntry]:
        return self.by_symbol.get(symbol, ())


@dataclass(frozen=True)
class LessonRegistryPort:
    registry: Any

    def cobra_surface(self, source_text: str) -> BilingualCobraSurface:
        payload = self.registry.cobra_surface(source_text)
        return cast(BilingualCobraSurface, payload)


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


def _load_lesson_registry_from_shygazun_module() -> Optional[LessonRegistryPort]:
    try:
        from shygazun.lesson_registry import load_lesson_registry  # type: ignore

        return LessonRegistryPort(registry=load_lesson_registry())
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


def _load_lesson_registry_from_nested_repo() -> Optional[LessonRegistryPort]:
    root = Path(__file__).resolve().parents[1]
    package_root = root / "DjinnOS-Shyagzun"
    module_path = root / "DjinnOS-Shyagzun" / "shygazun" / "lesson_registry.py"
    if not module_path.exists():
        return None
    try:
        sys.path.insert(0, str(package_root))
        spec = importlib.util.spec_from_file_location("nested_shygazun_lesson_registry", str(module_path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        load_lesson_registry = getattr(module, "load_lesson_registry", None)
        if load_lesson_registry is None:
            return None
        return LessonRegistryPort(registry=load_lesson_registry())
    except Exception:
        return None
    finally:
        if str(package_root) in sys.path:
            sys.path.remove(str(package_root))


def default_symbol_inventory() -> SymbolInventory:
    loaded = _load_inventory_from_shygazun_module()
    if loaded is not None:
        return loaded
    loaded = _load_inventory_from_nested_repo()
    if loaded is not None:
        return loaded
    raise RuntimeError("shygazun_symbol_inventory_unavailable")


def default_lesson_registry() -> Optional[LessonRegistryPort]:
    loaded = _load_lesson_registry_from_shygazun_module()
    if loaded is not None:
        return loaded
    return _load_lesson_registry_from_nested_repo()


def _material_properties_for_symbol(symbol: str, meaning: Optional[str]) -> Dict[str, Any]:
    """
    Minimal physics-oriented material properties derived from AppleBlossom symbols.
    Density is elementally graded: Earth densest, Fire least dense.
    """
    element_density = {
        "Zot": 100.0,  # Earth
        "Mel": 70.0,   # Water
        "Puf": 40.0,   # Air
        "Shak": 10.0,  # Fire
    }
    composite_density = {
        "Zhuk": 20.0,  # Plasma (Fire,Fire)
        "Kyzu": 35.0,  # Sulphur (Fire,Air)
        "Alky": 50.0,  # Alkahest/Alcohol (Fire,Water)
        "Kazho": 85.0, # Magma/Lava (Fire,Earth)
        "Puky": 30.0,  # Smoke (Air,Fire)
        "Pyfu": 25.0,  # Gas (Air,Air)
        "Mipa": 45.0,  # Carbonation (Air,Water)
        "Zitef": 75.0, # Mercury (Air,Earth)
        "Shem": 60.0,  # Steam (Water,Fire)
        "Lefu": 55.0,  # Vapor (Water,Air)
        "Milo": 70.0,  # Mixed fluids (Water,Water)
        "Myza": 80.0,  # Erosion (Water,Earth)
        "Zashu": 90.0, # Radiation stones (Earth,Fire)
        "Fozt": 65.0,  # Dust (Earth,Air)
        "Mazi": 95.0,  # Sediment (Earth,Water)
        "Zaot": 100.0, # Salt (Earth,Earth)
        "A": 50.0,     # Mind +
        "O": 50.0,     # Mind -
        "I": 50.0,     # Space +
        "E": 50.0,     # Space -
        "Y": 50.0,     # Time +
        "U": 50.0,     # Time -
    }
    density = element_density.get(symbol)
    if density is None:
        density = composite_density.get(symbol, 50.0)
    props = {
        "density": density,
        "friction": 60.0 if density >= 80 else 35.0,
        "restitution": 15.0 if density >= 80 else 25.0,
        "flow": 80.0 if symbol in {"Mel", "Milo", "Mipa", "Shem", "Lefu"} else 0.0,
        "volatility": 80.0 if symbol in {"Shak", "Puf", "Puky", "Pyfu"} else 20.0,
    }
    if meaning:
        props["label"] = meaning
    return props


def _recombine_apple_blossom_materials(atoms: Sequence[SymbolAtom]) -> List[RenderConstraintMaterial]:
    apple_atoms = [atom for atom in atoms if atom.get("tongue") == "AppleBlossom"]
    if len(apple_atoms) < 2:
        return []

    try:
        from shygazun.kernel.policy.recombiner import recombine  # type: ignore
    except Exception:
        return []

    combos: List[List[SymbolAtom]] = []
    # Full sequence first
    combos.append(apple_atoms)
    # Contiguous pairs
    for idx in range(len(apple_atoms) - 1):
        combos.append([apple_atoms[idx], apple_atoms[idx + 1]])

    materials: List[RenderConstraintMaterial] = []
    seen: set[str] = set()
    for combo in combos:
        decimals = [atom["decimal"] for atom in combo if atom.get("decimal") is not None]
        symbols = [str(atom.get("symbol") or "") for atom in combo]
        if len(decimals) < 2:
            continue
        combo_id = "AB:" + "".join(symbols)
        if combo_id in seen:
            continue
        seen.add(combo_id)

        assembly = recombine(decimals, mode="prose")
        line = getattr(assembly, "line", "")
        props_list = [
            _material_properties_for_symbol(str(atom.get("symbol") or ""), atom.get("meaning"))
            for atom in combo
        ]
        density = sum(float(item.get("density", 50.0)) for item in props_list) / len(props_list)
        friction = sum(float(item.get("friction", 35.0)) for item in props_list) / len(props_list)
        restitution = sum(float(item.get("restitution", 20.0)) for item in props_list) / len(props_list)
        flow = max(float(item.get("flow", 0.0)) for item in props_list)
        volatility = max(float(item.get("volatility", 20.0)) for item in props_list)
        materials.append(
            {
                "symbol": combo_id,
                "meaning": line or None,
                "tongue": "AppleBlossom",
                "properties": {
                    "density": density,
                    "friction": friction,
                    "restitution": restitution,
                    "flow": flow,
                    "volatility": volatility,
                    "recombined_from": symbols,
                    "recombine_line": line,
                },
            }
        )
    return materials


def _rose_ring_scalar(symbol: str) -> Optional[int]:
    ring_map = {
        "Gaoh": 0,
        "Ao": 1,
        "Ye": 2,
        "Ui": 3,
        "Shu": 4,
        "Kiel": 5,
        "Yeshu": 6,
        "Lao": 7,
        "Shushy": 8,
        "Uinshu": 9,
        "Kokiel": 10,
        "Aonkiel": 11,
    }
    if symbol in ring_map:
        return ring_map[symbol]
    vector_map = {
        "Ru": 0,
        "Ot": 1,
        "El": 2,
        "Ki": 3,
        "Fu": 4,
        "Ka": 5,
        "AE": 6,
    }
    if symbol in vector_map:
        scalar = vector_map[symbol] * 2
        return 11 if scalar > 11 else scalar
    return None


def _rose_vector_calculus(atoms: Sequence[SymbolAtom]) -> Dict[str, Any]:
    scalars: List[int] = []
    sources: List[str] = []
    polarity = 0
    for atom in atoms:
        if atom.get("tongue") != "Rose":
            continue
        symbol = str(atom.get("symbol") or "")
        if symbol == "Ha":
            polarity = 1
            continue
        if symbol == "Ga":
            polarity = -1
            continue
        scalar = _rose_ring_scalar(symbol)
        if scalar is None:
            continue
        scalars.append(scalar)
        sources.append(symbol)
    if not scalars:
        return {
            "ring": 12,
            "mode": "ring12",
            "enabled": True,
            "scalars": [],
            "sources": [],
            "vector": {"x": 0.0, "y": 0.0},
            "phase_deg": 0.0,
            "polarity": polarity,
            "targets": ["lighting", "material", "movement"],
        }
    import math

    angles = [(scalar / 12.0) * (2.0 * math.pi) for scalar in scalars]
    x = sum(math.cos(angle) for angle in angles) / len(angles)
    y = sum(math.sin(angle) for angle in angles) / len(angles)
    phase = math.degrees(math.atan2(y, x)) % 360.0
    return {
        "ring": 12,
        "mode": "ring12",
        "enabled": True,
        "scalars": scalars,
        "sources": sources,
        "vector": {"x": x, "y": y},
        "phase_deg": phase,
        "polarity": polarity,
        "targets": ["lighting", "material", "movement"],
    }


def _derive_alchemy_interface(atoms: Sequence[SymbolAtom]) -> Dict[str, Any]:
    grapevine_atoms = [atom for atom in atoms if atom.get("tongue") == "Grapevine"]
    if not grapevine_atoms:
        return {"enabled": False, "symbols": [], "stages": [], "mix_profile": {}}

    symbols = [str(atom.get("symbol") or "") for atom in grapevine_atoms]
    decimals = [int(atom["decimal"]) for atom in grapevine_atoms if atom.get("decimal") is not None]
    mean_decimal = sum(decimals) / max(1, len(decimals)) if decimals else 0.0
    stage_count = len(grapevine_atoms)
    stages: List[Dict[str, Any]] = []
    for idx, atom in enumerate(grapevine_atoms):
        if stage_count == 1:
            role = "agent"
        elif idx == 0:
            role = "catalyst"
        elif idx == stage_count - 1:
            role = "binder"
        else:
            role = "agent"
        stages.append(
            {
                "id": f"gv_{idx + 1}",
                "symbol": str(atom.get("symbol") or ""),
                "decimal": atom.get("decimal"),
                "meaning": atom.get("meaning"),
                "role": role,
            }
        )
    mix_profile = {
        "count": stage_count,
        "mean_decimal": mean_decimal,
        "sequence": symbols,
    }
    return {"enabled": True, "symbols": symbols, "stages": stages, "mix_profile": mix_profile}


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


def derive_render_constraints(
    ir: ShygazunIR,
    *,
    use_case: str = "render",
    material_tongue: str = "AppleBlossom",
) -> RenderConstraints:
    symbols = [atom["symbol"] for atom in ir["symbols"]]
    material_library: List[RenderConstraintMaterial] = []
    feature_map: Dict[str, List[str]] = {}
    feature_roles: Dict[str, str] = {
        "Rose": "vector_calculus",
        "Daisy": "structure_topology",
        "Aster": "time_space",
        "Grapevine": "systems",
        "Lotus": "prime_elements",
        "Sakura": "orientation_motion",
        "AppleBlossom": "materials",
    }
    weight_bias = {
        "relation": 0.0,
        "closure": 0.0,
        "time": 0.0,
        "system": 0.0,
    }
    primary_tongue: Optional[str] = None
    for atom in ir["symbols"]:
        tongue = atom.get("tongue")
        if tongue and primary_tongue is None:
            primary_tongue = tongue
        if tongue == material_tongue:
            properties = _material_properties_for_symbol(atom["symbol"], atom.get("meaning"))
            material_library.append(
                {
                    "symbol": atom["symbol"],
                    "meaning": atom.get("meaning"),
                    "tongue": tongue or material_tongue,
                    "properties": properties,
                }
            )
        elif tongue:
            feature_map.setdefault(tongue, []).append(atom["symbol"])
            if tongue == "Rose":
                weight_bias["relation"] += 0.25
            elif tongue == "Daisy":
                weight_bias["closure"] += 0.2
            elif tongue == "Aster":
                weight_bias["time"] += 0.2
            elif tongue == "Grapevine":
                weight_bias["system"] += 0.2
    if material_tongue == "AppleBlossom" and material_library:
        recombined = _recombine_apple_blossom_materials(ir["symbols"])
        if recombined:
            seen = {entry["symbol"] for entry in material_library}
            for entry in recombined:
                if entry["symbol"] in seen:
                    continue
                material_library.append(entry)
                seen.add(entry["symbol"])
    feature_palette = [
        {"tongue": tongue, "symbols": symbols_for_tongue}
        for tongue, symbols_for_tongue in sorted(feature_map.items())
    ]
    frontier_policy = {
        "use_case": use_case,
        "material_tongue": material_tongue,
        "feature_tongues": [palette["tongue"] for palette in feature_palette],
        "allow_unresolved": False,
        "edge_weight_bias": weight_bias,
        "mode_priority": "renderer_overrides",
    }
    rose_vector_calculus = _rose_vector_calculus(ir["symbols"])
    alchemy_interface = _derive_alchemy_interface(ir["symbols"])
    return {
        "use_case": use_case,
        "material_library": material_library,
        "feature_palette": feature_palette,
        "feature_roles": feature_roles,
        "symbol_sequence": symbols,
        "unresolved": list(ir["unresolved"]),
        "primary_tongue": primary_tongue,
        "frontier_policy": frontier_policy,
        "rose_vector_calculus": rose_vector_calculus,
        "alchemy_interface": alchemy_interface,
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
            if colon > 0 and " " not in line[:colon]:
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


def _normalize_aster_metadata(meta: Dict[str, Any]) -> None:
    source = ""
    aster_colors_obj = meta.get("aster_colors")
    if isinstance(aster_colors_obj, list):
        parts = [str(item).strip() for item in aster_colors_obj if str(item).strip() != ""]
        if parts:
            source = "+".join(parts)
    elif isinstance(aster_colors_obj, str) and aster_colors_obj.strip() != "":
        source = aster_colors_obj.strip()
    if source == "":
        explicit_aster = str(meta.get("aster_color") or "").strip()
        if explicit_aster != "":
            source = explicit_aster
        else:
            color_text = str(meta.get("color") or "").strip()
            if color_text.lower().startswith("aster:"):
                source = color_text.split(":", 1)[1].strip()
    if source == "":
        return
    resolved = resolve_aster_color(source)
    meta["aster_color"] = resolved["canonical"]
    meta["rgb"] = resolved["rgb"]
    meta["color"] = resolved["rgb"]
    meta["aster_palette_spot"] = resolved["palette_spot"]
    meta["aster_components"] = list(resolved["components"])


def _first_meta_value(meta: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = meta.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text != "":
            return text
    return ""


def _parse_bp(value: str, default_value: int) -> int:
    text = str(value or "").strip()
    if text == "":
        return default_value
    if not re.fullmatch(r"-?\d+", text):
        return default_value
    parsed = int(text)
    if parsed < 0:
        return 0
    if parsed > 10000:
        return 10000
    return parsed


def derive_djinn_layer_references(
    *,
    meta: Mapping[str, Any],
    ir: Optional[ShygazunIR] = None,
) -> DjinnLayerReferences:
    behavior_set: set[str] = set()
    if ir is not None:
        for atom in ir.get("symbols", []):
            symbol = str(atom.get("symbol") or "").strip()
            if symbol != "":
                behavior_set.add(symbol)
    behavior_words = sorted(behavior_set)

    function_id = _first_meta_value(
        meta,
        (
            "djinn_function",
            "djinn.function",
            "function_id",
            "layer_function_id",
        ),
    )
    function_version = _first_meta_value(
        meta,
        (
            "djinn_function_version",
            "djinn.function.version",
            "function_version",
            "layer_function_version",
        ),
    )
    if function_version == "":
        function_version = "v1"

    projection_report = _first_meta_value(
        meta,
        (
            "layer_projection_report",
            "renderer_layer_projection_report",
            "djinn_layer_projection",
        ),
    )

    reference_coeff_default = 7000
    recursion_coeff_default = 3000
    if "Na" in behavior_set:
        reference_coeff_default = 5000
        recursion_coeff_default = 5000
    if "Kysael" in behavior_set:
        reference_coeff_default = 8000
        recursion_coeff_default = 2000

    reference_coeff_bp = _parse_bp(
        _first_meta_value(meta, ("reference_coeff_bp", "djinn_reference_coeff_bp")),
        reference_coeff_default,
    )
    recursion_coeff_bp = _parse_bp(
        _first_meta_value(meta, ("recursion_coeff_bp", "djinn_recursion_coeff_bp")),
        recursion_coeff_default,
    )
    recursion_enabled = "Wu" in behavior_set or recursion_coeff_bp > 0
    model = "labyr_nth.linear_recurrence.v1" if recursion_enabled else "labyr_nth.reference_only.v1"

    return {
        "function_id": function_id,
        "function_version": function_version,
        "layer_projection_report": projection_report,
        "reference_coeff_bp": reference_coeff_bp,
        "recursion_coeff_bp": recursion_coeff_bp,
        "recursion_enabled": recursion_enabled,
        "behavior_words": behavior_words,
        "model": model,
    }


def derive_bilingual_cobra_surface(
    source_text: str,
    *,
    lesson_registry: Optional[LessonRegistryPort] = None,
) -> Optional[BilingualCobraSurface]:
    registry = lesson_registry if lesson_registry is not None else default_lesson_registry()
    if registry is None:
        return None
    normalized = str(source_text or "").strip()
    if normalized == "":
        return None
    try:
        return registry.cobra_surface(normalized)
    except Exception:
        return None


def cobra_to_placement_payloads(
    source: str,
    *,
    scene_id: str,
    workspace_id: str,
    realm_id: str = "lapidus",
    use_case: str = "render",
    inventory: Optional[SymbolInventory] = None,
) -> List[CobraPlacementPayload]:
    symbol_inventory = inventory if inventory is not None else default_symbol_inventory()
    lesson_registry = default_lesson_registry()
    entities = _parse_cobra_entities(source)
    payloads: List[CobraPlacementPayload] = []
    for entity in entities:
        entity_meta_obj = entity.get("meta")
        if isinstance(entity_meta_obj, dict):
            _normalize_aster_metadata(entity_meta_obj)
        akinenwun = str(entity.get("akinenwun", "") or "")
        ir = compile_akinenwun_to_ir(akinenwun, inventory=symbol_inventory) if akinenwun else {
            "akinenwun": "",
            "symbols": [],
            "canonical_compound": "",
            "unresolved": [],
        }
        raw = f"entity {entity['id']} {entity['x']} {entity['y']} {entity['tag']}"
        identity: PlacementIdentity = {
            "entity_id": str(entity["id"]),
            "tag": str(entity["tag"]),
            "akinenwun": ir["canonical_compound"],
        }
        constraints = derive_render_constraints(ir, use_case=use_case)
        entity_meta: Mapping[str, Any] = entity_meta_obj if isinstance(entity_meta_obj, dict) else {}
        djinn_refs = derive_djinn_layer_references(meta=entity_meta, ir=ir)
        bilingual_surface = derive_bilingual_cobra_surface(akinenwun, lesson_registry=lesson_registry)
        payloads.append(
            {
                "raw": raw,
                "scene_id": scene_id,
                "context": {
                    "workspace_id": workspace_id,
                    "realm_id": realm_id,
                    "cobra_entity": entity,
                    "shygazun_ir": ir,
                    "identity": identity,
                    "render_constraints": constraints,
                    "frontier_policy": constraints["frontier_policy"],
                    "djinn_layer_references": djinn_refs,
                    "bilingual_cobra_surface": bilingual_surface,
                },
            }
        )
    return payloads


def cobra_to_scene_graph(
    source: str,
    *,
    scene_id: str,
    realm_id: str,
    inventory: Optional[SymbolInventory] = None,
) -> SceneGraphPayload:
    from .scene_graph import build_scene_graph_from_cobra

    graph = build_scene_graph_from_cobra(
        source,
        realm_id=realm_id,
        scene_id=scene_id,
        inventory=inventory,
    )
    return {"scene_id": scene_id, "realm_id": realm_id, "graph": graph}


def compile_akinenwun_batch(
    words: Iterable[str],
    *,
    inventory: Optional[SymbolInventory] = None,
) -> List[ShygazunIR]:
    symbol_inventory = inventory if inventory is not None else default_symbol_inventory()
    return [compile_akinenwun_to_ir(word, inventory=symbol_inventory) for word in words]
