from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from .shygazun_compiler import SymbolInventory, compile_akinenwun_to_ir, default_symbol_inventory
from .validators import validate_scene_realm


def _load_scene_graph_defaults() -> tuple[List[str], Dict[str, int]]:
    root = Path(__file__).resolve().parents[1]
    defaults_path = root / "scene_graph_defaults.json"
    if defaults_path.exists():
        try:
            payload = json.loads(defaults_path.read_text(encoding="utf-8"))
            layer_order = payload.get("layer_order")
            layer_z = payload.get("layer_z")
            if isinstance(layer_order, list) and isinstance(layer_z, dict):
                order = [str(item) for item in layer_order if str(item)]
                z_map = {str(key): int(value) for key, value in layer_z.items()}
                if order and z_map:
                    return order, z_map
        except Exception:
            pass
    fallback_order = ["background", "midground", "foreground", "overlay", "ui"]
    fallback_z = {layer: index * 10 for index, layer in enumerate(fallback_order)}
    return fallback_order, fallback_z


DEFAULT_LAYER_ORDER, DEFAULT_LAYER_Z = _load_scene_graph_defaults()


class SceneNode(TypedDict):
    id: str
    entity_id: str
    tag: str
    x: int
    y: int
    z: int
    layer: str
    akinenwun: str
    metadata: Dict[str, Any]


class SceneLayer(TypedDict):
    name: str
    z_offset: int


class SceneGraph(TypedDict):
    realm_id: str
    scene_id: str
    layers: List[SceneLayer]
    nodes: List[SceneNode]


class CobraEntity(TypedDict):
    id: str
    x: int
    y: int
    tag: str
    meta: Dict[str, Any]
    akinenwun: str


@dataclass(frozen=True)
class SceneGraphBuild:
    graph: SceneGraph
    nodes: List[SceneNode]


def _parse_cobra_entities(source: str) -> List[CobraEntity]:
    entities: List[CobraEntity] = []
    current: Optional[CobraEntity] = None
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


def _layer_for_entity(entity: CobraEntity) -> str:
    raw_layer = entity["meta"].get("layer")
    if isinstance(raw_layer, str) and raw_layer.strip() != "":
        return raw_layer.strip()
    return "midground"


def _z_for_entity(entity: CobraEntity, layer: str) -> int:
    base = DEFAULT_LAYER_Z.get(layer, DEFAULT_LAYER_Z["midground"])
    z_raw = entity["meta"].get("z")
    if isinstance(z_raw, str) and z_raw.lstrip("-").isdigit():
        return base + int(z_raw)
    if isinstance(z_raw, int):
        return base + z_raw
    return base


def build_scene_graph_from_cobra(
    source: str,
    *,
    realm_id: str,
    scene_id: str,
    inventory: Optional[SymbolInventory] = None,
) -> SceneGraph:
    realm_error = validate_scene_realm(scene_id, realm_id)
    if realm_error:
        raise ValueError(realm_error)

    symbol_inventory = inventory if inventory is not None else default_symbol_inventory()
    entities = _parse_cobra_entities(source)
    nodes: List[SceneNode] = []
    for entity in entities:
        akinenwun = str(entity.get("akinenwun") or "").strip()
        canonical = ""
        if akinenwun:
            ir = compile_akinenwun_to_ir(akinenwun, inventory=symbol_inventory)
            canonical = ir["canonical_compound"]
        layer = _layer_for_entity(entity)
        z = _z_for_entity(entity, layer)
        nodes.append(
            {
                "id": str(entity["id"]),
                "entity_id": str(entity["id"]),
                "tag": str(entity["tag"]),
                "x": int(entity["x"]),
                "y": int(entity["y"]),
                "z": z,
                "layer": layer,
                "akinenwun": canonical,
                "metadata": dict(entity["meta"]),
            }
        )

    layers = [{"name": name, "z_offset": DEFAULT_LAYER_Z[name]} for name in DEFAULT_LAYER_ORDER]
    return {
        "realm_id": realm_id.strip().lower(),
        "scene_id": scene_id.strip(),
        "layers": layers,
        "nodes": nodes,
    }
