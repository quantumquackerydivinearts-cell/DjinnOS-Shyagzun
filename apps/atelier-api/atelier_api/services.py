from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import math
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, cast
import subprocess
from pathlib import Path

def _ensure_repo_root_on_path() -> None:
    current = Path(__file__).resolve()
    candidates = [current.parents[3], current.parents[2], current.parents[1]]
    for candidate in candidates:
        qqva_dir = candidate / "qqva"
        shygazun_dir = candidate / "DjinnOS-Shyagzun"
        if qqva_dir.is_dir():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)
        if shygazun_dir.is_dir():
            shygazun_str = str(shygazun_dir)
            if shygazun_str not in sys.path:
                sys.path.insert(0, shygazun_str)
        if qqva_dir.is_dir() or shygazun_dir.is_dir():
            return


_ensure_repo_root_on_path()

from qqva.world_stream import WorldStreamController
from qqva.aster_colors import resolve_aster_color
from qqva.shygazun_compiler import derive_semantic_runtime_dispatch
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from jsonschema import Draft202012Validator
from DjinnOS_Shygazun.shygazun.lesson_registry import load_lesson_registry

from .business_schemas import (
    ArtisanBootstrapInput,
    ArtisanAccessIssueInput,
    ArtisanAccessIssueOut,
    ArtisanAccessStatusOut,
    ArtisanAccessVerifyInput,
    BookingCreate,
    BookingOut,
    ClientCreate,
    ClientOut,
    ContactCreate,
    ContactOut,
    LeadCreate,
    LeadOut,
    LedgerEntryOut,
    InventoryItemCreate,
    InventoryItemOut,
    LessonCreate,
    LessonOut,
    LessonProgressOut,
    LessonConsumeInput,
    ModuleCreate,
    ModuleOut,
    OrderCreate,
    OrderOut,
    PublicCommissionInquiryCreate,
    PublicCommissionQuoteOut,
    QuoteCreate,
    QuoteOut,
    ContractCreate,
    ContractUpdate,
    ContractOut,
    ShopItemCreate,
    ShopItemOut,
    ShopItemUpdate,
    ShopItemVisibilityUpdate,
    HeadlessQuestEmitInput,
    HeadlessQuestEmitOut,
    MeditationEmitInput,
    MeditationEmitOut,
    SceneGraphEmitInput,
    SceneGraphEmitOut,
    SaveExportOut,
    InventoryAdjustInput,
    LevelApplyInput,
    LevelApplyOut,
    SkillTrainInput,
    SkillTrainOut,
    SkillCatalogOut,
    CANONICAL_GAME_SKILLS,
    PerkUnlockInput,
    PerkUnlockOut,
    AlchemyCraftInput,
    AlchemyCraftOut,
    AlchemyInterfaceInput,
    AlchemyInterfaceOut,
    AlchemyCrystalInput,
    AlchemyCrystalOut,
    BlacksmithForgeInput,
    BlacksmithForgeOut,
    CombatResolveInput,
    CombatResolveOut,
    MarketQuoteInput,
    MarketQuoteOut,
    MarketTradeInput,
    MarketTradeOut,
    RadioEvaluateInput,
    RadioEvaluateOut,
    InfernalMeditationUnlockInput,
    InfernalMeditationUnlockOut,
    GateEvaluateInput,
    GateEvaluateOut,
    GateStateInput,
    GateRequirement,
    GateRequirementResult,
    GateOperator,
    RuntimeConsumeInput,
    RuntimeConsumeOut,
    RuntimeActionInput,
    RuntimeActionOut,
    RuntimeReplayInput,
    RuntimeReplayOut,
    RuntimePlanRunOut,
    RuntimeActionCatalogOut,
    RuntimeActionCatalogItemOut,
    ModuleSpecOut,
    ModuleCatalogOut,
    ModuleValidateInput,
    ModuleValidateOut,
    ShygazunInterpretInput,
    ShygazunInterpretOut,
    ShygazunTranslateInput,
    ShygazunTranslateOut,
    ShygazunCorrectInput,
    ShygazunCorrectOut,
    DialogueChoiceResolveOut,
    DialogueResolveInput,
    DialogueResolveOut,
    CharacterDictionaryCreate,
    CharacterDictionaryOut,
    NamedQuestCreate,
    NamedQuestOut,
    QuestTransitionInput,
    QuestTransitionOut,
    QuestAdvanceInput,
    QuestAdvanceByGraphInput,
    QuestAdvanceByGraphDryRunOut,
    QuestAdvanceByGraphOut,
    QuestAdvanceOut,
    QuestGraphHashOut,
    QuestGraphValidateOut,
    QuestGraphOut,
    QuestGraphListOut,
    QuestGraphStepInput,
    QuestGraphUpsertInput,
    BreathKoGenerateInput,
    BreathKoListOut,
    BreathKoOut,
    QuestStepEdgeResolveOut,
    JournalEntryCreate,
    JournalEntryOut,
    LayerNodeCreate,
    LayerNodeOut,
    LayerEdgeCreate,
    LayerEdgeOut,
    LayerEventOut,
    LayerTraceOut,
    FunctionStoreCreate,
    FunctionStoreOut,
    PlayerStateApplyInput,
    PlayerStateOut,
    PlayerStateTables,
    GameEventInput,
    GameTickInput,
    GameTickOut,
    GameTickEventResult,
    AssetManifestCreate,
    AssetManifestOut,
    ContentValidateInput,
    ContentValidateOut,
    RealmOut,
    RealmValidateInput,
    RealmValidateOut,
    SceneCreateInput,
    SceneUpdateInput,
    SceneOut,
    SceneEmitOut,
    SceneCompileInput,
    WorldRegionLoadInput,
    WorldRegionUnloadInput,
    WorldRegionOut,
    WorldRegionUnloadOut,
    WorldStreamStatusOut,
    RealmCoinOut,
    RealmMarketOut,
    Numeral3DInput,
    Numeral3DOut,
    FibonacciOrderingInput,
    FibonacciOrderingOut,
    DialogueEmitInput,
    DialogueEmitOut,
    VitriolApplyRulerInfluenceInput,
    VitriolApplyOut,
    VitriolClearExpiredInput,
    VitriolClearExpiredOut,
    VitriolComputeInput,
    VitriolComputeOut,
    VitriolModifier,
    DjinnApplyInput,
    DjinnApplyOut,
    DjinnOrreryMark,
    SupplierCreate,
    SupplierOut,
)
from .rendering_schemas import (
    RendererTablesInput,
    RendererTablesOut,
    IsometricRenderContractInput,
    IsometricRenderContractOut,
    IsometricDrawableOut,
    RenderGraphContractInput,
    RenderGraphContractOut,
    RenderGraphNodeOut,
    RendererAssetDiagnosticsInput,
    RendererAssetDiagnosticsOut,
)
from core.config import load_settings
from .kernel_integration import KernelIntegrationService
from .market_logic import get_realm_coin, get_realm_market, list_realm_coins, list_realm_markets
from .pygame_worker import PygameWorkerManager, get_pygame_worker_manager
from .db import engine
from .models import (
    ArtisanAccount,
    Booking,
    CRMContact,
    CharacterDictionaryEntry,
    Client,
    FunctionStoreEntry,
    InventoryItem,
    JournalEntry,
    Lead,
    LedgerEntry,
    LayerEdge,
    LayerEvent,
    LayerNode,
    Lesson,
    LessonProgress,
    LearningModule,
    NamedQuest,
    Order,
    Contract,
    Quote,
    ShopItem,
    Supplier,
    PlayerState,
    RuntimePlanRun,
    AssetManifest,
    Realm,
    Scene,
    WorldRegion,
    GuildConversationRecord,
    GuildMessageEnvelopeRecord,
    DistributionRegistryRecord,
    DistributionHandshakeRecord,
    WandDamageAttestationRecord,
    WandKeyEpochRecord,
    WandRegistryRecord,
    GuildRegistryRecord,
)
from .repositories import AtelierRepository
from .validators import build_scene_graph_content_from_cobra, validate_cobra_content, validate_json_content, validate_scene_realm
from .types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse


def _safe_parse_json(raw: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


class AtelierService:
    _QUEST_GRAPH_RUNTIME_SCHEMA_VERSION = "v1"
    _BREATH_KO_KIND = "breath.ko.v1"
    _BREATH_KO_FIXED_SCALE = 1_000_000
    _BREATH_KO_ESCAPE_RADIUS = 4
    _BREATH_KO_MAX_ITER_CAP = 16384
    _BREATH_KO_SUPPORTED_MAX_ITER = 4096
    _DEATH_PATRON_ID = "ohadame"
    _DEATH_PATRON_NAME = "Ohadame the Goddess of Past Life Memories and Akashic Memory"
    _ATTAINMENT_HARMONY_PATRON_ID = "moshize"
    _ATTAINMENT_HARMONY_PATRON_NAME = "Moshize the Goddess of Attainment and Harmony"
    _KILL_PATRON_ID = "negaya"
    _KILL_PATRON_NAME = "Negaya the Void Wraith and Knower of Bodies"
    _VITRIOL_AXES: tuple[str, ...] = (
        "vitality",
        "introspection",
        "tactility",
        "reflectivity",
        "ingenuity",
        "ostentation",
        "levity",
    )
    _VITRIOL_RULER_AXIS: dict[str, str] = {
        "asmodeus": "vitality",
        "satan": "introspection",
        "beelzebub": "tactility",
        "belphegor": "reflectivity",
        "leviathan": "ingenuity",
        "mammon": "ostentation",
        "lucifer": "levity",
    }
    _GUILD_MESSAGE_ENVELOPE_SCHEMA_FAMILY = "guild_message_envelope"
    _GUILD_MESSAGE_ENVELOPE_SCHEMA_VERSION = "v1"
    _GUILD_MESSAGE_CIPHER_FAMILY = "experimental_hash_stream_v1"
    _GUILD_MESSAGE_PROTOCOL_FAMILY = "guild_message_signal_artifice"
    _GUILD_MESSAGE_PROTOCOL_VERSION = "v1"
    _GUILD_MESSAGE_SUPPORTED_PROTOCOL_VERSIONS = ("v1",)
    _TRI_SOURCE_ENTROPY_SCHEMA_FAMILY = "tri_source_entropy_mix"
    _TRI_SOURCE_ENTROPY_SCHEMA_VERSION = "v1"
    _DEMON_PRESSURE_DEFAULTS: dict[str, float] = {
        "asmodeus": 0.0,
        "satan": 0.0,
        "beelzebub": 0.0,
        "belphegor": 0.0,
        "leviathan": 0.0,
        "mammon": 0.0,
        "lucifer": 0.0,
        "ruzoa": 0.0,
        "zukoru": 0.0,
        "kielum": 0.0,
        "othieru": 0.0,
        "po_elfan": 0.0,
        "kaganue": 0.0,
    }
    _DEMON_MALADY_DOMAINS: dict[str, str] = {
        "asmodeus": "vitality_corruption",
        "satan": "introspective_decay",
        "beelzebub": "tactile_corrosion",
        "belphegor": "reflective_stagnation",
        "leviathan": "ingenuity_distortion",
        "mammon": "ostentation_blight",
        "lucifer": "levity_collapse",
        "ruzoa": "depression",
        "zukoru": "nihilism",
        "kielum": "abuse",
        "othieru": "abandon",
        "po_elfan": "anxiety",
        "kaganue": "confusion",
    }
    _DJINN_ALIGNMENT: dict[str, str] = {
        "keshi": "chaotic_evil",
        "giann": "chaotic_good",
        "drovitth": "lawful_neutral",
    }
    _WORLD_STREAM_MAX_LOADED_REGIONS = 128
    _SANITY_KEYS: tuple[str, ...] = ("alchemical", "terrestrial", "cosmic", "narrative")
    _UNDERWORLD_RING_ORDER: tuple[str, ...] = (
        "pride",
        "greed",
        "envy",
        "gluttony",
        "sloth",
        "wrath",
        "lust",
    )
    _SULPHERA_RING_RULERS: dict[str, str] = {
        "pride": "lucifer",
        "greed": "mammon",
        "envy": "leviathan",
        "gluttony": "beelzebub",
        "sloth": "belphegor",
        "wrath": "satan",
        "lust": "asmodeus",
    }
    _MERCURIE_DUNGEON_ZONES: tuple[str, ...] = (
        "zone_tideglass",
        "zone_cindergrove",
        "zone_rootbloom",
        "zone_thornveil",
        "zone_dewspire",
    )
    _LAPIDUS_DUNGEON_IDS: tuple[str, ...] = ("lapidus_mines_mt_hieronymus",)
    _FAE_KINDS: tuple[str, ...] = ("undines", "salamanders", "dryads", "faeries", "gnomes")
    _SOCIAL_CLASSES: tuple[str, ...] = ("assassins", "nobles", "royals", "townsfolk", "merchants", "gods")
    _REALM_IDS: tuple[str, ...] = ("lapidus", "mercurie", "sulphera")
    _LANGUAGE_DEITY_DEFAULT = "jabiru"
    _LANGUAGE_DEMON_CONFUSER = "kaganue"
    _SHYGAZUN_TRANSLATION_LEXICON_EN_TO_SHY: dict[str, str] = {
        "i": "Awu",
        "we": "Owu",
        "you": "Iwu",
        "y'all": "Ewu",
        "yall": "Ewu",
        "he": "Ywu",
        "she": "Ywu",
        "they": "Uwu",
        "love": "Aely",
        "whale": "MelKoWuVu",
        "whales": "Melkowuvune",
        "water": "Mel",
        "earth": "Zot",
        "air": "Puf",
        "fire": "Shak",
        "life": "Va",
        "chaos": "Vo",
        "presence": "Ta",
        "absence": "Zo",
        "process": "Wu",
        "experience": "Ko",
    }
    _SHYGAZUN_OPPOSITION_PAIRS: tuple[tuple[str, str], ...] = (
        ("A", "O"),
        ("I", "E"),
        ("Y", "U"),
        ("Ta", "Zo"),
        ("Ha", "Ga"),
        ("Va", "Vo"),
    )

    def __init__(
        self,
        repo: AtelierRepository | None,
        kernel: KernelIntegrationService,
        world_stream: WorldStreamController | None = None,
        pygame_worker: PygameWorkerManager | None = None,
    ) -> None:
        self._repo = repo
        self._kernel = kernel
        self._world_stream = world_stream or WorldStreamController(
            max_loaded_regions=self._WORLD_STREAM_MAX_LOADED_REGIONS
        )
        self._pygame_worker = pygame_worker or get_pygame_worker_manager()

    def _require_repo(self) -> AtelierRepository:
        if self._repo is None:
            raise RuntimeError("repository_unavailable")
        return self._repo

    @staticmethod
    def _canonical_json(payload: object) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _canonical_hash(payload: object) -> str:
        return hashlib.sha256(AtelierService._canonical_json(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def _resolve_aster_metadata(meta: dict[str, object]) -> tuple[str | None, str | None]:
        source = ""
        aster_colors_obj = meta.get("aster_colors")
        if isinstance(aster_colors_obj, list):
            parts = [str(item).strip() for item in aster_colors_obj if str(item).strip() != ""]
            if parts:
                source = "+".join(parts)
        elif isinstance(aster_colors_obj, str) and aster_colors_obj.strip() != "":
            source = aster_colors_obj.strip()
        elif "aster_colors" in meta and aster_colors_obj is not None:
            raise ValueError("invalid_aster_colors_type")

        if source == "":
            explicit_aster = str(meta.get("aster_color") or "").strip()
            if explicit_aster != "":
                source = explicit_aster
            else:
                color_text = str(meta.get("color") or "").strip()
                if color_text.lower().startswith("aster:"):
                    source = color_text.split(":", 1)[1].strip()
        if source == "":
            return None, None

        resolved = resolve_aster_color(source)
        meta["aster_color"] = resolved["canonical"]
        meta["rgb"] = resolved["rgb"]
        meta["color"] = resolved["rgb"]
        meta["aster_palette_spot"] = resolved["palette_spot"]
        meta["aster_components"] = list(resolved["components"])
        return str(resolved["canonical"]), str(resolved["rgb"])

    def _validate_aster_scene_content(self, content: Mapping[str, object]) -> None:
        nodes_obj = content.get("nodes")
        if not isinstance(nodes_obj, list):
            return
        for node in nodes_obj:
            if not isinstance(node, dict):
                continue
            metadata_obj = node.get("metadata")
            if not isinstance(metadata_obj, dict):
                continue
            self._resolve_aster_metadata(cast(dict[str, object], metadata_obj))

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    def _load_json_file(self, path: Path) -> dict[str, object]:
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        return cast(dict[str, object], parsed) if isinstance(parsed, dict) else {}

    def _load_shygazun_byte_entries(self) -> list[dict[str, object]]:
        raw_index: object | None = None
        try:
            from shygazun.kernel.constants.byte_table import SHYGAZUN_SYMBOL_INDEX  # type: ignore

            raw_index = SHYGAZUN_SYMBOL_INDEX
        except Exception:
            module_path = self._repo_root() / "DjinnOS-Shyagzun" / "shygazun" / "kernel" / "constants" / "byte_table.py"
            if module_path.exists():
                spec = importlib.util.spec_from_file_location("nested_shygazun_byte_table", str(module_path))
                if spec is not None and spec.loader is not None:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    raw_index = getattr(module, "SHYGAZUN_SYMBOL_INDEX", None)
        if not isinstance(raw_index, dict):
            raise ValueError("shygazun_symbol_index_unavailable")
        entries: list[dict[str, object]] = []
        for symbol_obj, entry_objs in raw_index.items():
            if not isinstance(entry_objs, (list, tuple)):
                continue
            for entry_obj in entry_objs:
                if not isinstance(entry_obj, dict):
                    continue
                decimal = self._int_from_table(entry_obj.get("decimal"), -1)
                if decimal < 0:
                    continue
                symbol = str(entry_obj.get("symbol", symbol_obj)).strip()
                tongue = str(entry_obj.get("tongue", "")).strip()
                meaning = str(entry_obj.get("meaning", "")).strip()
                if symbol == "":
                    continue
                entries.append(
                    {
                        "decimal": decimal,
                        "symbol": symbol,
                        "tongue": tongue,
                        "meaning": meaning,
                    }
                )
        entries.sort(key=lambda item: (int(item["decimal"]), str(item["symbol"]), str(item["tongue"])))
        return entries

    def _load_byte_table_into_layers(
        self,
        *,
        workspace_id: str,
        actor_id: str,
    ) -> dict[str, object]:
        entries = self._load_shygazun_byte_entries()
        if self._repo is None:
            return {
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "persisted": False,
                "reason": "repository_unavailable",
                "entry_count": len(entries),
                "seeded": {
                    "layer_nodes_created": 0,
                    "layer_nodes_skipped": 0,
                    "layer_edges_created": 0,
                    "layer_edges_skipped": 0,
                    "layer_events_created": 0,
                },
            }
        repo = self._require_repo()
        seeded = {
            "layer_nodes_created": 0,
            "layer_nodes_skipped": 0,
            "layer_edges_created": 0,
            "layer_edges_skipped": 0,
            "layer_events_created": 0,
        }
        existing_nodes = repo.list_layer_nodes(workspace_id=workspace_id)
        node_by_key: dict[str, LayerNode] = {row.node_key: row for row in existing_nodes}
        existing_edges = repo.list_layer_edges(workspace_id=workspace_id)
        edge_keys = {(row.from_node_id, row.to_node_id, row.edge_kind) for row in existing_edges}

        def _ensure_node(layer_index: int, node_key: str, payload_obj: dict[str, object]) -> LayerNode:
            row = node_by_key.get(node_key)
            if row is not None:
                seeded["layer_nodes_skipped"] += 1
                return row
            payload_hash = self._canonical_hash(payload_obj)
            row = repo.create_layer_node(
                LayerNode(
                    workspace_id=workspace_id,
                    layer_index=layer_index,
                    node_key=node_key,
                    payload_json=self._canonical_json(payload_obj),
                    payload_hash=payload_hash,
                )
            )
            node_by_key[node_key] = row
            seeded["layer_nodes_created"] += 1
            repo.create_layer_event(
                LayerEvent(
                    workspace_id=workspace_id,
                    event_kind="content.pack.load_byte_table",
                    actor_id=actor_id,
                    node_id=row.id,
                    edge_id=None,
                    payload_hash=payload_hash,
                )
            )
            seeded["layer_events_created"] += 1
            return row

        def _ensure_edge(from_node_id: str, to_node_id: str, edge_kind: str, metadata_obj: dict[str, object]) -> None:
            edge_key = (from_node_id, to_node_id, edge_kind)
            if edge_key in edge_keys:
                seeded["layer_edges_skipped"] += 1
                return
            row = repo.create_layer_edge(
                LayerEdge(
                    workspace_id=workspace_id,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    edge_kind=edge_kind,
                    metadata_json=self._canonical_json(metadata_obj),
                )
            )
            edge_keys.add(edge_key)
            seeded["layer_edges_created"] += 1
            repo.create_layer_event(
                LayerEvent(
                    workspace_id=workspace_id,
                    event_kind="content.pack.load_byte_table.edge",
                    actor_id=actor_id,
                    node_id=None,
                    edge_id=row.id,
                    payload_hash=self._canonical_hash(metadata_obj),
                )
            )
            seeded["layer_events_created"] += 1

        for entry in entries:
            decimal = int(entry["decimal"])
            symbol = str(entry["symbol"])
            tongue = str(entry["tongue"])
            meaning = str(entry["meaning"])
            bits = format(max(0, min(255, decimal)), "08b")
            node_l1 = _ensure_node(
                1,
                f"byte_table::byte::{decimal:03d}",
                {"decimal": decimal, "bits8": bits},
            )
            node_l2 = _ensure_node(
                2,
                f"byte_table::scalar::{decimal:03d}",
                {"decimal": decimal, "float": float(decimal)},
            )
            node_l3 = _ensure_node(
                3,
                f"byte_table::bool::{symbol}::{decimal:03d}",
                {"has_tongue": tongue != "", "has_meaning": meaning != ""},
            )
            node_l10_symbol = _ensure_node(
                10,
                f"byte_table::symbol::{symbol}::{decimal:03d}",
                {"decimal": decimal, "symbol": symbol, "tongue": tongue, "meaning": meaning},
            )
            node_l10_tongue = _ensure_node(
                10,
                f"byte_table::tongue::{tongue if tongue != '' else 'unknown'}",
                {"tongue": tongue},
            )
            _ensure_edge(node_l1.id, node_l2.id, "classifies", {"from": "byte", "to": "scalar"})
            _ensure_edge(node_l2.id, node_l10_symbol.id, "maps_to_symbol", {"decimal": decimal, "symbol": symbol})
            _ensure_edge(node_l3.id, node_l10_symbol.id, "constrains", {"has_meaning": meaning != ""})
            _ensure_edge(node_l10_symbol.id, node_l10_tongue.id, "belongs_to_tongue", {"tongue": tongue})

        return {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "persisted": True,
            "entry_count": len(entries),
            "seeded": seeded,
        }

    def _load_canon_content_pack(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
        pack_dir: str = "gameplay/content_packs/canon",
        apply_to_db: bool = True,
    ) -> dict[str, object]:
        base_dir = self._repo_root() / pack_dir
        manifest_path = base_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"content_pack_manifest_missing:{manifest_path}")
        manifest = self._load_json_file(manifest_path)
        files_obj = manifest.get("files")
        files = [str(item) for item in files_obj] if isinstance(files_obj, list) else []
        if len(files) == 0:
            raise ValueError("content_pack_manifest_files_empty")

        loaded_docs: dict[str, dict[str, object]] = {}
        for filename in files:
            path = base_dir / filename
            if not path.exists():
                raise ValueError(f"content_pack_file_missing:{path}")
            loaded_docs[filename] = self._load_json_file(path)

        summary: dict[str, object] = {
            "pack_dir": str(pack_dir),
            "manifest": manifest,
            "loaded_files": sorted(list(loaded_docs.keys())),
            "apply_to_db": bool(apply_to_db),
            "seeded": {
                "characters_created": 0,
                "characters_skipped": 0,
                "quests_created": 0,
                "quests_skipped": 0,
                "scene_dialogue_staged": 0,
                "scene_dialogue_skipped": 0,
                "items_created": 0,
                "items_skipped": 0,
                "flags_added": 0,
                "layer_nodes_created": 0,
                "layer_nodes_skipped": 0,
                "layer_events_created": 0,
            },
            "counts": {},
        }

        characters_doc = loaded_docs.get("characters.json", {})
        quests_doc = loaded_docs.get("quests.json", {})
        items_doc = loaded_docs.get("items.json", {})
        flags_doc = loaded_docs.get("flags.json", {})
        tools_doc = loaded_docs.get("tools.json", {})

        characters = self._list_of_dicts(characters_doc.get("characters"))
        quests = self._list_of_dicts(quests_doc.get("quests"))
        items = self._list_of_dicts(items_doc.get("items"))
        flags = self._list_of_dicts(flags_doc.get("flags"))
        tools = self._list_of_dicts(tools_doc.get("tools"))

        summary["counts"] = {
            "characters": len(characters),
            "quests": len(quests),
            "items": len(items),
            "flags": len(flags),
            "tools": len(tools),
        }

        if not apply_to_db:
            return summary

        repo = self._require_repo()
        seeded = cast(dict[str, int], summary["seeded"])

        existing_chars = self.list_character_dictionary_entries(workspace_id)
        existing_char_ids = {row.character_id for row in existing_chars}
        for row in characters:
            character_id = str(row.get("character_id", "")).strip()
            name = str(row.get("name", "")).strip()
            if character_id == "" or name == "":
                continue
            if character_id in existing_char_ids:
                seeded["characters_skipped"] += 1
                continue
            self.create_character_dictionary_entry(
                CharacterDictionaryCreate(
                    workspace_id=workspace_id,
                    character_id=character_id,
                    name=name,
                    aliases=[],
                    bio="",
                    tags=[],
                    faction=character_id.split("_", 1)[1] if "_" in character_id else "",
                    metadata={},
                )
            )
            existing_char_ids.add(character_id)
            seeded["characters_created"] += 1

        existing_quests = self.list_named_quests(workspace_id)
        existing_quest_ids = {row.quest_id for row in existing_quests}
        quest_dialogue_rows: list[dict[str, object]] = []
        for row in quests:
            quest_id = str(row.get("quest_id", "")).strip()
            name = str(row.get("name", "")).strip()
            if quest_id == "" or name == "":
                continue
            quest_dialogue_rows.append(
                {
                    "quest_id": quest_id,
                    "scene_id": f"quest/{quest_id.lower()}",
                    "dialogue_id": f"dlg.{quest_id.lower()}.intro",
                    "title": name,
                    "lines": [
                        {
                            "speaker": "narrator",
                            "text": name,
                        }
                    ],
                }
            )
            if quest_id in existing_quest_ids:
                seeded["quests_skipped"] += 1
                continue
            self.create_named_quest(
                NamedQuestCreate(
                    workspace_id=workspace_id,
                    quest_id=quest_id,
                    name=name,
                    status="inactive",
                    current_step="",
                    requirements={},
                    rewards={},
                )
            )
            existing_quest_ids.add(quest_id)
            seeded["quests_created"] += 1

        existing_items = self.list_inventory_items(workspace_id)
        existing_skus = {row.sku for row in existing_items}
        for row in items:
            item_id = str(row.get("item_id", "")).strip()
            item_name = str(row.get("item_name", "")).strip()
            item_template = str(row.get("item_template", "")).strip()
            material_var = bool(row.get("material_var", False))
            effective_name = item_name if item_name != "" else item_template
            if effective_name == "":
                continue
            sku = item_id if item_id != "" else f"canon.item.{self._canonical_hash(row)[:12]}"
            if sku in existing_skus:
                seeded["items_skipped"] += 1
                continue
            notes = ""
            if material_var:
                notes = "material_var=true"
            if "source_label" in row:
                source_label = str(row.get("source_label", "")).strip()
                if source_label != "":
                    notes = f"{notes};source_label={source_label}".strip(";")
            repo.create_inventory_item(
                InventoryItem(
                    workspace_id=workspace_id,
                    sku=sku,
                    name=effective_name,
                    quantity_on_hand=0,
                    reorder_level=0,
                    unit_cost_cents=0,
                    currency="USD",
                    supplier_id=None,
                    notes=notes,
                )
            )
            existing_skus.add(sku)
            seeded["items_created"] += 1

        state = self.get_player_state(workspace_id=workspace_id, actor_id=actor_id)
        current_flags = dict(state.tables.flags)
        added = 0
        for row in flags:
            name = str(row.get("name", "")).strip()
            if name == "":
                continue
            key = f"canon.flag.{name.lower().replace(' ', '_')}"
            if key in current_flags:
                continue
            current_flags[key] = False
            added += 1
        if added > 0:
            self.apply_player_state(
                payload=PlayerStateApplyInput(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    mode="merge",
                    tables=PlayerStateTables(flags=current_flags),
                ),
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        seeded["flags_added"] = added

        # 12-layer lineage projection for canon pack content.
        layer_map = {
            "flags.json": 3,       # booleans
            "items.json": 5,       # entities
            "tools.json": 5,       # entities/tools
            "characters.json": 6,  # character histories
            "quests.json": 9,      # dialogue/story quest surfaces
            "start_sequence.json": 9,
            "fate_knocks_quiz.json": 9,
        }
        existing_nodes = self.list_layer_nodes(workspace_id=workspace_id)
        existing_node_keys = {row.node_key for row in existing_nodes}
        for filename, doc in loaded_docs.items():
            layer_index = layer_map.get(filename)
            if layer_index is None:
                continue
            key_suffix = filename.replace(".json", "")
            node_key = f"canon::{key_suffix}"
            if node_key in existing_node_keys:
                seeded["layer_nodes_skipped"] += 1
                continue
            payload_obj: dict[str, object] = {
                "pack_id": str(doc.get("pack_id", "")),
                "schema_version": str(doc.get("schema_version", "")),
                "filename": filename,
                "counts": summary.get("counts", {}),
            }
            node_hash = self._canonical_hash(payload_obj)
            node = repo.create_layer_node(
                LayerNode(
                    workspace_id=workspace_id,
                    layer_index=layer_index,
                    node_key=node_key,
                    payload_json=self._canonical_json(payload_obj),
                    payload_hash=node_hash,
                )
            )
            seeded["layer_nodes_created"] += 1
            existing_node_keys.add(node_key)
            repo.create_layer_event(
                LayerEvent(
                    workspace_id=workspace_id,
                    event_kind="content.pack.load_canon",
                    actor_id=actor_id,
                    node_id=node.id,
                    edge_id=None,
                    payload_hash=node_hash,
                )
            )
            seeded["layer_events_created"] += 1

        # Stage per-quest dialogue surfaces in layer 9 for scene dialogue bootstrapping.
        for dialogue in quest_dialogue_rows:
            quest_id = str(dialogue.get("quest_id", "")).strip()
            if quest_id == "":
                continue
            dialogue_key = f"canon::dialogue::{quest_id}"
            if dialogue_key in existing_node_keys:
                seeded["scene_dialogue_skipped"] += 1
                continue
            dialogue_payload = {
                "quest_id": quest_id,
                "scene_id": str(dialogue.get("scene_id", "")),
                "dialogue_id": str(dialogue.get("dialogue_id", "")),
                "title": str(dialogue.get("title", "")),
                "lines": dialogue.get("lines", []),
            }
            dialogue_hash = self._canonical_hash(dialogue_payload)
            node = repo.create_layer_node(
                LayerNode(
                    workspace_id=workspace_id,
                    layer_index=9,
                    node_key=dialogue_key,
                    payload_json=self._canonical_json(dialogue_payload),
                    payload_hash=dialogue_hash,
                )
            )
            existing_node_keys.add(dialogue_key)
            seeded["scene_dialogue_staged"] += 1
            seeded["layer_nodes_created"] += 1
            repo.create_layer_event(
                LayerEvent(
                    workspace_id=workspace_id,
                    event_kind="content.pack.dialogue.stage",
                    actor_id=actor_id,
                    node_id=node.id,
                    edge_id=None,
                    payload_hash=dialogue_hash,
                )
            )
            seeded["layer_events_created"] += 1
        return summary

    def _bootstrap_fate_knocks(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
        payload: Mapping[str, object],
    ) -> dict[str, object]:
        player_name = str(payload.get("player_name", "")).strip()
        player_gender = str(payload.get("player_gender", "")).strip()
        if player_name == "":
            raise ValueError("player_name_required")
        if player_gender == "":
            raise ValueError("player_gender_required")
        month = str(payload.get("month", "Shyalz")).strip() or "Shyalz"
        deadline_hour_local = max(0, min(23, self._int_from_table(payload.get("deadline_hour_local"), 19)))
        points_budget = max(1, self._int_from_table(payload.get("quiz_points_budget"), 28))
        min_per_answer = max(0, self._int_from_table(payload.get("quiz_min_per_answer"), 1))
        max_per_answer = max(min_per_answer, self._int_from_table(payload.get("quiz_max_per_answer"), 10))
        vitriol_obj = payload.get("vitriol_answers")
        vitriol_answers = [self._int_from_table(item, 0) for item in vitriol_obj] if isinstance(vitriol_obj, list) else []
        quiz_answers_obj = payload.get("quiz_answers")
        quiz_answers = [self._int_from_table(item, 0) for item in quiz_answers_obj] if isinstance(quiz_answers_obj, list) else []
        if len(vitriol_answers) == 0 and len(quiz_answers) >= 7:
            vitriol_answers = quiz_answers[:7]
        perk_obj = payload.get("perk_answers")
        perk_answers = [str(item).strip() for item in perk_obj] if isinstance(perk_obj, list) else []
        skill_aptitude_obj = payload.get("skill_aptitude_answers")
        skill_aptitude_answers = (
            [str(item).strip() for item in skill_aptitude_obj]
            if isinstance(skill_aptitude_obj, list)
            else []
        )
        power_answer = str(payload.get("power_answer", "")).strip()
        finance_answer = str(payload.get("finance_answer", "")).strip()
        non_vitriol_obj = payload.get("non_vitriol_answers")
        if isinstance(non_vitriol_obj, dict):
            if len(perk_answers) == 0:
                perk_embedded = non_vitriol_obj.get("perk_answers")
                if isinstance(perk_embedded, list):
                    perk_answers = [str(item).strip() for item in perk_embedded]
            if len(skill_aptitude_answers) == 0:
                apt_embedded = non_vitriol_obj.get("skill_aptitude_answers")
                if isinstance(apt_embedded, list):
                    skill_aptitude_answers = [str(item).strip() for item in apt_embedded]
            if power_answer == "":
                power_answer = str(non_vitriol_obj.get("power_answer", "")).strip()
            if finance_answer == "":
                finance_answer = str(non_vitriol_obj.get("finance_answer", "")).strip()
        perk_answers = [item for item in perk_answers if item != ""]
        skill_aptitude_answers = [item for item in skill_aptitude_answers if item != ""]
        worldview_answers = [item for item in [power_answer, finance_answer] if item != ""]

        vitriol_valid = (
            len(vitriol_answers) == 7
            and all(min_per_answer <= item <= max_per_answer for item in vitriol_answers)
            and sum(vitriol_answers) == points_budget
        )
        v3_mode = (
            len(perk_answers) > 0
            or len(skill_aptitude_answers) > 0
            or power_answer != ""
            or finance_answer != ""
            or "non_vitriol_answers" in payload
        )
        v3_valid = (
            vitriol_valid
            and len(perk_answers) == 3
            and len(skill_aptitude_answers) == 3
            and power_answer != ""
            and finance_answer != ""
        )
        quiz_valid = v3_valid if v3_mode else vitriol_valid
        vitriol_axes = (
            "vitality",
            "introspection",
            "tactility",
            "reflectivity",
            "ingenuity",
            "ostentation",
            "levity",
        )
        vitriol_map = {axis: (vitriol_answers[index] if quiz_valid else 0) for index, axis in enumerate(vitriol_axes)}
        dominant_sorted = sorted(vitriol_map.items(), key=lambda item: (-item[1], item[0]))
        skill_tags = [item[0] for item in dominant_sorted[:3]]
        levity_value = int(vitriol_map.get("levity", 0))

        perk_candidates: list[str] = []
        if v3_mode and quiz_valid:
            perk_text = " ".join(perk_answers).lower()
            if ("iron" in perk_text and "skin" in perk_text) or "iron_skin" in perk_text:
                perk_candidates.append("Iron Skin")
            if "flashbulb" in perk_text or ("memory" in perk_text and "elder" in perk_text):
                perk_candidates.append("Flashbulb Memory")

        skill_table = [
            "barter",
            "energy_weapons",
            "explosives",
            "guns",
            "lockpick",
            "medicine",
            "melee_weapons",
            "repair",
            "alchemy",
            "sneak",
            "hack",
            "speech",
            "survival",
            "unarmed",
            "meditation",
            "magic",
            "blacksmithing",
            "silversmithing",
            "goldsmithing",
        ]
        skill_modulation: dict[str, int] = {}
        if quiz_valid:
            vitriol_avg = sum(vitriol_map.values()) / max(1, len(vitriol_map))
            aptitude_bias = 0.0
            for answer in skill_aptitude_answers:
                lowered = answer.lower()
                if any(token in lowered for token in ("expert", "high", "master", "focused", "disciplined")):
                    aptitude_bias += 0.8
                elif any(token in lowered for token in ("low", "novice", "weak", "uncertain", "untrained")):
                    aptitude_bias -= 0.4
                else:
                    aptitude_bias += 0.2
            aptitude_avg = max(1.0, vitriol_avg + aptitude_bias)
            levity_tradeoff = max(0.0, (levity_value - 5) * 0.06)
            for skill_id in skill_table:
                base = (vitriol_avg * 8.0) + (aptitude_avg * 2.0)
                if skill_id in {"speech", "sneak", "magic"}:
                    # Levity affords higher expressive/flexible skills.
                    tuned = base * (1.0 + levity_tradeoff)
                else:
                    # Cost appears as reduced non-levity profile headroom.
                    tuned = base * (1.0 - (levity_tradeoff * 0.5))
                skill_modulation[skill_id] = max(1, min(100, int(round(tuned))))
        power_finance_profile = {
            "power": power_answer if quiz_valid else "",
            "finance": finance_answer if quiz_valid else "",
            "power_score": (
                70
                if ("duty" in power_answer.lower() or "service" in power_answer.lower())
                else 60
                if ("shared" in power_answer.lower() or "balance" in power_answer.lower())
                else 50
                if power_answer != ""
                else 0
            ),
            "finance_score": (
                70
                if ("redistribution" in finance_answer.lower() or "equity" in finance_answer.lower())
                else 60
                if ("trade" in finance_answer.lower() or "stability" in finance_answer.lower())
                else 50
                if finance_answer != ""
                else 0
            ),
        }

        if self._repo is None:
            return {
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "quest_id": "0001_KLST",
                "quest_name": "Fate Knocks",
                "day_index": 1,
                "month": month,
                "location": "Azonithia/Wiltoll Street/player_home",
                "weather": "storm_morning",
                "castle_report_deadline_hour_local": deadline_hour_local,
                "stipend_revocation_if_missed": True,
                "lottery_selected": True,
                "quiz_version": "v3" if v3_mode else "v1",
                "quiz_points_budget": points_budget,
                "quiz_min_per_answer": min_per_answer,
                "quiz_max_per_answer": max_per_answer,
                "quiz_answers": quiz_answers,
                "vitriol_answers": vitriol_answers,
                "non_vitriol_answers": {
                    "perk_answers": perk_answers if v3_mode else [],
                    "skill_aptitude_answers": skill_aptitude_answers if v3_mode else [],
                    "power_answer": power_answer if v3_mode else "",
                    "finance_answer": finance_answer if v3_mode else "",
                },
                "quiz_valid": quiz_valid,
                "quiz_completed": quiz_valid,
                "vitriol": vitriol_map if quiz_valid else {},
                "skill_tags": skill_tags,
                "perk_candidates": perk_candidates,
                "skill_aptitude_answers": skill_aptitude_answers if v3_mode else [],
                "skill_modulation": skill_modulation if quiz_valid else {},
                "power_finance_profile": power_finance_profile,
                "wake_scene_id": "lapidus/home_morning",
                "letter_scene_id": "lapidus/home_morning",
                "travel_target_scene_id": "lapidus/castle_evening",
                "destiny_calls_unlocked": quiz_valid,
                "destiny_calls_quest_id": "0002_KLST" if quiz_valid else "",
                "persisted": False,
                "reason": "repository_unavailable",
            }

        state = self.get_player_state(workspace_id=workspace_id, actor_id=actor_id)
        merged_flags = dict(state.tables.flags)
        merged_flags.update(
            {
                "intro.day_index": 1,
                "intro.quest_id": "0001_KLST",
                "intro.quest_name": "Fate Knocks",
                "intro.location": "Azonithia/Wiltoll Street/player_home",
                "intro.weather": "storm_morning",
                "intro.month": month,
                "intro.planet": "Aeralune",
                "intro.legacy_planet": "Kepler 452B",
                "intro.courier_service": "Royal Courier Service",
                "intro.letter_from": "0000_0451",
                "intro.letter_sender_name": "Alexandria Hypatia",
                "intro.castle_report_deadline_hour_local": deadline_hour_local,
                "intro.castle_report_required": True,
                "intro.castle_report_penalty": "royal_stipend_revoked",
                "intro.royal_lottery_selected": True,
                "intro.apprenticeship_role": "high_alchemist_apprentice",
                "player.name": player_name,
                "player.gender": player_gender,
                "player.origin.parent_alchemist_status": "deceased_plague",
                "player.origin.parent_mother_role": "baker",
                "intro.quiz_question_count": 15 if v3_mode else 7,
                "intro.quiz_points_budget": points_budget,
                "intro.quiz_min_per_answer": min_per_answer,
                "intro.quiz_max_per_answer": max_per_answer,
                "intro.quiz_version": "v3" if v3_mode else "v1",
                "intro.quiz_completed": quiz_valid,
                "intro.quiz_answer_count": 15 if v3_mode else len(vitriol_answers),
                "intro.quiz_answers_legacy": quiz_answers,
                "intro.quiz_vitriol_answers": vitriol_answers,
                "intro.quiz_perk_answers": perk_answers if v3_mode else [],
                "intro.quiz_skill_aptitude_answers": skill_aptitude_answers if v3_mode else [],
                "intro.quiz_worldview_answers": worldview_answers if v3_mode else [],
                "intro.perk_candidates": perk_candidates,
                "intro.skill_modulation": skill_modulation if quiz_valid else {},
                "intro.power_finance_profile": power_finance_profile,
                "intro.fate_knocks_resolved": False,
                "intro.fate_knocks_status": "active",
                "intro.fate_knocks_current_step": "route_to_castle_azoth",
                "intro.wake_scene_id": "lapidus/home_morning",
                "intro.letter_scene_id": "lapidus/home_morning",
                "intro.travel_target_scene_id": "lapidus/castle_evening",
                "intro.destiny_calls_unlocked": quiz_valid,
                "intro.destiny_calls_quest_id": "0002_KLST" if quiz_valid else "",
                "skills.tag_primary": skill_tags[0] if len(skill_tags) > 0 else "",
                "skills.tag_secondary": skill_tags[1] if len(skill_tags) > 1 else "",
                "skills.tag_tertiary": skill_tags[2] if len(skill_tags) > 2 else "",
            }
        )
        self.apply_player_state(
            payload=PlayerStateApplyInput(
                workspace_id=workspace_id,
                actor_id=actor_id,
                mode="merge",
                tables=PlayerStateTables(flags=merged_flags, vitriol=vitriol_map if quiz_valid else {}),
            ),
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

        existing_quests = self.list_named_quests(workspace_id)
        if "0001_KLST" not in {row.quest_id for row in existing_quests}:
            self.create_named_quest(
                NamedQuestCreate(
                    workspace_id=workspace_id,
                    quest_id="0001_KLST",
                    name="Fate Knocks",
                    status="active",
                    current_step="route_to_castle_azoth",
                    requirements={},
                    rewards={},
                )
            )
        if quiz_valid and "0002_KLST" not in {row.quest_id for row in existing_quests}:
            self.create_named_quest(
                NamedQuestCreate(
                    workspace_id=workspace_id,
                    quest_id="0002_KLST",
                    name="Destiny Calls",
                    status="active",
                    current_step="opened_by_fate_knocks_quiz",
                    requirements={"from_quest": "0001_KLST", "quiz_completed": True},
                    rewards={},
                )
            )

        return {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "quest_id": "0001_KLST",
            "quest_name": "Fate Knocks",
            "day_index": 1,
            "month": month,
            "location": "Azonithia/Wiltoll Street/player_home",
            "weather": "storm_morning",
            "castle_report_deadline_hour_local": deadline_hour_local,
            "stipend_revocation_if_missed": True,
            "lottery_selected": True,
            "quiz_version": "v3" if v3_mode else "v1",
            "quiz_points_budget": points_budget,
            "quiz_min_per_answer": min_per_answer,
            "quiz_max_per_answer": max_per_answer,
            "quiz_answers": quiz_answers,
            "vitriol_answers": vitriol_answers,
            "non_vitriol_answers": {
                "perk_answers": perk_answers if v3_mode else [],
                "skill_aptitude_answers": skill_aptitude_answers if v3_mode else [],
                "power_answer": power_answer if v3_mode else "",
                "finance_answer": finance_answer if v3_mode else "",
            },
            "quiz_valid": quiz_valid,
            "quiz_completed": quiz_valid,
            "vitriol": vitriol_map if quiz_valid else {},
            "skill_tags": skill_tags,
            "perk_candidates": perk_candidates,
            "skill_aptitude_answers": skill_aptitude_answers if v3_mode else [],
            "skill_modulation": skill_modulation if quiz_valid else {},
            "power_finance_profile": power_finance_profile,
            "wake_scene_id": "lapidus/home_morning",
            "letter_scene_id": "lapidus/home_morning",
            "travel_target_scene_id": "lapidus/castle_evening",
            "destiny_calls_unlocked": quiz_valid,
            "destiny_calls_quest_id": "0002_KLST" if quiz_valid else "",
        }

    def _fate_knocks_report_to_castle(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
        payload: Mapping[str, object],
    ) -> dict[str, object]:
        scene_id = str(payload.get("scene_id", "lapidus/castle_evening")).strip() or "lapidus/castle_evening"
        met_hypatia = bool(payload.get("met_hypatia", True))
        current_hour = self._int_from_table(payload.get("current_hour_local"), 19)

        if self._repo is None:
            quiz_completed = bool(payload.get("quiz_completed", False))
            destiny_unlocked = bool(payload.get("destiny_calls_unlocked", False)) or quiz_completed
            return {
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "quest_id": "0001_KLST",
                "scene_id": scene_id,
                "met_hypatia": met_hypatia,
                "reported_to_castle": True,
                "fate_knocks_resolved": met_hypatia,
                "destiny_calls_unlocked": destiny_unlocked,
                "destiny_calls_quest_id": "0002_KLST" if destiny_unlocked else "",
                "persisted": False,
                "reason": "repository_unavailable",
            }

        state = self.get_player_state(workspace_id=workspace_id, actor_id=actor_id)
        flags = dict(state.tables.flags)
        quiz_completed = bool(flags.get("intro.quiz_completed", False))
        destiny_unlocked = bool(flags.get("intro.destiny_calls_unlocked", False))
        if not destiny_unlocked and quiz_completed:
            destiny_unlocked = True
            flags["intro.destiny_calls_unlocked"] = True
            flags["intro.destiny_calls_quest_id"] = "0002_KLST"

        flags["intro.castle_report_completed"] = True
        flags["intro.castle_report_scene_id"] = scene_id
        flags["intro.castle_report_hour_local"] = current_hour
        flags["intro.met_hypatia"] = met_hypatia
        flags["intro.fate_knocks_resolved"] = met_hypatia
        flags["intro.fate_knocks_status"] = "resolved" if met_hypatia else "active"
        flags["intro.fate_knocks_current_step"] = "resolved_hypatia_meeting" if met_hypatia else "await_hypatia_meeting"
        flags["intro.next_quest_id"] = "0002_KLST" if destiny_unlocked else ""

        quest_states_obj = self._dict_from_table(flags.get("quest_states"))
        quest_states: dict[str, object] = dict(quest_states_obj)
        quest_states["0001_KLST"] = {
            "state": "resolved" if met_hypatia else "active",
            "step_id": "resolved_hypatia_meeting" if met_hypatia else "await_hypatia_meeting",
            "last_event_id": "report_to_hypatia",
            "updated_tick": self._int_from_table(state.tables.clock.get("tick"), 0),
        }
        if destiny_unlocked:
            existing_q2 = self._dict_from_table(quest_states.get("0002_KLST"))
            next_step = str(existing_q2.get("step_id") or "opened_by_fate_knocks_quiz")
            quest_states["0002_KLST"] = {
                "state": str(existing_q2.get("state") or "active"),
                "step_id": next_step,
                "last_event_id": str(existing_q2.get("last_event_id") or "fate_knocks_quiz_unlock"),
                "updated_tick": self._int_from_table(state.tables.clock.get("tick"), 0),
            }
        flags["quest_states"] = quest_states

        self.apply_player_state(
            payload=PlayerStateApplyInput(
                workspace_id=workspace_id,
                actor_id=actor_id,
                mode="merge",
                tables=PlayerStateTables(flags=flags),
            ),
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

        existing_quests = self.list_named_quests(workspace_id)
        existing_ids = {row.quest_id for row in existing_quests}
        if destiny_unlocked and "0002_KLST" not in existing_ids:
            self.create_named_quest(
                NamedQuestCreate(
                    workspace_id=workspace_id,
                    quest_id="0002_KLST",
                    name="Destiny Calls",
                    status="active",
                    current_step="opened_by_fate_knocks_quiz",
                    requirements={"from_quest": "0001_KLST", "quiz_completed": True},
                    rewards={},
                )
            )

        return {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "quest_id": "0001_KLST",
            "scene_id": scene_id,
            "current_hour_local": current_hour,
            "met_hypatia": met_hypatia,
            "reported_to_castle": True,
            "fate_knocks_resolved": met_hypatia,
            "fate_knocks_status": "resolved" if met_hypatia else "active",
            "destiny_calls_unlocked": destiny_unlocked,
            "destiny_calls_quest_id": "0002_KLST" if destiny_unlocked else "",
        }

    def _fate_knocks_deadline_check(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
        payload: Mapping[str, object],
    ) -> dict[str, object]:
        if self._repo is None:
            current_hour = self._int_from_table(payload.get("current_hour_local"), 0)
            return {
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "quest_id": "0001_KLST",
                "current_hour_local": current_hour,
                "deadline_hour_local": self._int_from_table(payload.get("deadline_hour_local"), 19),
                "reported_to_castle": False,
                "triggered": False,
                "royal_stipend_active": True,
                "royal_stipend_revoked": False,
                "deadline_failed": False,
                "world_decay_index": 0,
                "persisted": False,
                "reason": "repository_unavailable",
            }
        state = self.get_player_state(workspace_id=workspace_id, actor_id=actor_id)
        flags = dict(state.tables.flags)
        quest_id = str(flags.get("intro.quest_id", "0001_KLST"))
        deadline_hour = self._int_from_table(flags.get("intro.castle_report_deadline_hour_local", 19), 19)
        current_hour = self._int_from_table(payload.get("current_hour_local"), self._int_from_table(state.tables.clock.get("hour_local"), 0))
        reported = bool(flags.get("intro.castle_report_completed", False))
        stipend_revoked = bool(flags.get("intro.royal_stipend_revoked", False))
        stipend_active = bool(flags.get("intro.royal_stipend_active", True))

        triggered = False
        if not reported and current_hour >= deadline_hour and not stipend_revoked:
            stipend_revoked = True
            stipend_active = False
            flags["intro.royal_stipend_revoked"] = True
            flags["intro.royal_stipend_active"] = False
            flags["intro.deadline_failed"] = True
            decay_index = self._int_from_table(flags.get("world_decay_index"), 0)
            flags["world_decay_index"] = decay_index + 1
            triggered = True

        if triggered:
            self.apply_player_state(
                payload=PlayerStateApplyInput(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    mode="merge",
                    tables=PlayerStateTables(flags=flags),
                ),
                actor_id=actor_id,
                workshop_id=workshop_id,
            )

        return {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "quest_id": quest_id,
            "current_hour_local": current_hour,
            "deadline_hour_local": deadline_hour,
            "reported_to_castle": reported,
            "triggered": triggered,
            "royal_stipend_active": stipend_active if not triggered else False,
            "royal_stipend_revoked": stipend_revoked,
            "deadline_failed": bool(flags.get("intro.deadline_failed", False)),
            "world_decay_index": self._int_from_table(flags.get("world_decay_index"), 0),
        }

    @staticmethod
    def _clamp_unit(value: object) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    @classmethod
    def _distort_token_for_kaganue(
        cls,
        *,
        token: str,
        seed: int,
        index: int,
    ) -> str:
        if token.strip() == "":
            return token
        out_chars: list[str] = []
        for char_index, char in enumerate(token):
            if not char.isalpha():
                out_chars.append(char)
                continue
            shift = 1 + ((seed + index + char_index) % 3)
            alphabet = "abcdefghijklmnopqrstuvwxyz"
            is_upper = char.isupper()
            base_char = char.lower()
            pos = alphabet.find(base_char)
            if pos < 0:
                out_chars.append(char)
                continue
            shifted = alphabet[(pos + shift) % len(alphabet)]
            out_chars.append(shifted.upper() if is_upper else shifted)
        return "".join(out_chars)

    @classmethod
    def _resolve_symbol_entry_for_token(
        cls,
        *,
        token: str,
    ) -> list[dict[str, object]]:
        try:
            from qqva.shygazun_compiler import default_symbol_inventory, split_akinenwun

            inventory = default_symbol_inventory()
            parts = split_akinenwun(token)
        except Exception:
            return []
        out: list[dict[str, object]] = []
        for part in parts:
            entries = inventory.entries_for(part)
            if len(entries) == 0:
                out.append(
                    {
                        "symbol": part,
                        "known": False,
                        "tongue": None,
                        "meaning": None,
                        "decimal": None,
                    }
                )
                continue
            entry = entries[0]
            out.append(
                {
                    "symbol": str(entry["symbol"]),
                    "known": True,
                    "tongue": str(entry["tongue"]),
                    "meaning": str(entry["meaning"]),
                    "decimal": int(entry["decimal"]),
                }
            )
        return out

    @classmethod
    def _is_symbol_opposition(cls, left: str, right: str) -> bool:
        pair = {left, right}
        for a, b in cls._SHYGAZUN_OPPOSITION_PAIRS:
            if pair == {a, b}:
                return True
        return False

    @classmethod
    def _compound_relation_trace(
        cls,
        *,
        primitives: Sequence[Mapping[str, object]],
        lore_overlay: str,
    ) -> dict[str, object]:
        if len(primitives) <= 1:
            return {
                "relation_kind": "atomic",
                "edges": [],
                "lore_overlay": lore_overlay,
                "explanation": "atomic symbol with no compound edge",
            }
        edges: list[dict[str, object]] = []
        relation_counts = {"opposition": 0, "reinforcement": 0, "composition": 0}
        for idx in range(len(primitives) - 1):
            left = primitives[idx]
            right = primitives[idx + 1]
            left_symbol = str(left.get("symbol") or "")
            right_symbol = str(right.get("symbol") or "")
            left_tongue = left.get("tongue")
            right_tongue = right.get("tongue")
            if cls._is_symbol_opposition(left_symbol, right_symbol):
                relation = "opposition"
            elif left_tongue is not None and left_tongue == right_tongue:
                relation = "reinforcement"
            else:
                relation = "composition"
            relation_counts[relation] += 1
            edges.append(
                {
                    "from": left_symbol,
                    "to": right_symbol,
                    "relation": relation,
                }
            )
        if relation_counts["opposition"] > 0:
            primary_relation = "opposition"
        elif relation_counts["reinforcement"] > relation_counts["composition"]:
            primary_relation = "reinforcement"
        else:
            primary_relation = "composition"
        if primary_relation == "opposition":
            explanation = "compound encodes semantic tension; meaning resolves through contradiction"
        elif primary_relation == "reinforcement":
            explanation = "compound reinforces a single semantic family across adjacent symbols"
        else:
            explanation = "compound composes distinct primitives into a derived semantic packet"
        if lore_overlay == "anecdotal":
            explanation += " with anecdotal overlay enabled"
        return {
            "relation_kind": primary_relation,
            "edges": edges,
            "lore_overlay": lore_overlay,
            "explanation": explanation,
        }

    @classmethod
    def _interpret_shygazun_runtime(cls, payload: Mapping[str, object]) -> dict[str, object]:
        deity = str(payload.get("deity", cls._LANGUAGE_DEITY_DEFAULT)).strip().lower() or cls._LANGUAGE_DEITY_DEFAULT
        utterance_raw = str(payload.get("utterance", "")).strip()
        if utterance_raw == "":
            raise ValueError("utterance_required")
        mode = str(payload.get("mode", "explicit")).strip().lower() or "explicit"
        explain_mode = str(payload.get("explain_mode", "none")).strip().lower() or "none"
        lore_overlay = str(payload.get("lore_overlay", "none")).strip().lower() or "none"
        mutate_tokens = bool(payload.get("mutate_tokens", True))
        kaganue_pressure = cls._clamp_unit(payload.get("kaganue_pressure", cls._DEMON_PRESSURE_DEFAULTS.get("kaganue", 0.0)))
        normalized_utterance = " ".join(utterance_raw.split())
        source_tokens = [token for token in normalized_utterance.split(" ") if token.strip() != ""]
        canonical_tokens = [token.lower() for token in source_tokens]
        confusion_budget = max(0, min(len(canonical_tokens), int(round(kaganue_pressure * len(canonical_tokens)))))
        seed_raw = cls._canonical_hash(
            {
                "deity": deity,
                "mode": mode,
                "utterance": normalized_utterance,
                "kaganue_pressure": kaganue_pressure,
            }
        )
        seed = int(seed_raw[:8], 16)
        ranked_indexes = sorted(
            range(len(canonical_tokens)),
            key=lambda token_index: cls._canonical_hash(
                {
                    "seed": seed_raw,
                    "token_index": token_index,
                    "token": canonical_tokens[token_index],
                }
            ),
        )
        distorted_tokens = list(canonical_tokens)
        mutated_indexes = set(ranked_indexes[:confusion_budget]) if mutate_tokens else set()
        for token_index in sorted(mutated_indexes):
            distorted_tokens[token_index] = cls._distort_token_for_kaganue(
                token=canonical_tokens[token_index],
                seed=seed,
                index=token_index,
            )
        akinenwun_hits: list[dict[str, object]] = []
        compound_trace: list[dict[str, object]] = []
        try:
            from qqva.shygazun_compiler import compile_akinenwun_to_ir

            for idx, token in enumerate(source_tokens):
                if token.isalpha():
                    try:
                        ir = compile_akinenwun_to_ir(token)
                    except Exception:
                        continue
                    if isinstance(ir, dict) and len(ir.keys()) > 0:
                        akinenwun_hits.append(
                            {
                                "token": token,
                                "ir_hash": cls._canonical_hash(ir)[:16],
                            }
                        )
                if explain_mode in {"compound", "compound_explain", "full"}:
                    primitives = cls._resolve_symbol_entry_for_token(token=token)
                    if len(primitives) > 0:
                        compound_trace.append(
                            {
                                "token": token,
                                "token_index": idx,
                                "primitives": list(primitives),
                                "relation_trace": cls._compound_relation_trace(
                                    primitives=primitives,
                                    lore_overlay=lore_overlay,
                                ),
                            }
                        )
        except Exception:
            akinenwun_hits = []
            compound_trace = []
        out: dict[str, object] = {
            "deity": deity,
            "demon": cls._LANGUAGE_DEMON_CONFUSER,
            "mode": mode,
            "explain_mode": explain_mode,
            "lore_overlay": lore_overlay,
            "utterance": normalized_utterance,
            "canonical_tokens": canonical_tokens,
            "interpreted_tokens": distorted_tokens,
            "kaganue_pressure": kaganue_pressure,
            "confusion_index": round(kaganue_pressure * 100.0, 2),
            "mutated_count": len(mutated_indexes),
            "semantic_payload": {
                "token_count": len(canonical_tokens),
                "akinenwun_hits": akinenwun_hits,
                "story_vector": {
                    "density": len(canonical_tokens),
                    "entropy_hint": cls._canonical_hash(distorted_tokens)[:12],
                },
            },
        }
        if explain_mode in {"compound", "compound_explain", "full"}:
            out["compound_trace"] = compound_trace
        return out

    @classmethod
    def _tokenize_translation_input(cls, text: str) -> list[str]:
        return [token for token in re.findall(r"[A-Za-z][A-Za-z']*", text) if token.strip() != ""]

    @classmethod
    def _lesson_backed_translation_assets(cls) -> dict[str, dict[str, str]]:
        assets = {
            "english_to_shygazun": {},
            "shygazun_to_english": {},
            "english_examples": {},
            "shygazun_examples": {},
        }
        try:
            registry = load_lesson_registry()
            assets["english_to_shygazun"] = dict(registry.english_to_shygazun_lexicon())
            assets["shygazun_to_english"] = dict(registry.shygazun_to_english_lexicon())
            assets["english_examples"] = dict(registry.english_projection_examples())
            assets["shygazun_examples"] = dict(registry.shygazun_projection_examples())
        except Exception:
            return assets
        return assets

    @classmethod
    def _translate_shygazun_runtime(cls, payload: Mapping[str, object]) -> dict[str, object]:
        source_raw = str(payload.get("source_text", "")).strip()
        if source_raw == "":
            raise ValueError("source_text_required")
        direction = str(payload.get("direction", "auto")).strip().lower() or "auto"
        if direction not in {"auto", "english_to_shygazun", "shygazun_to_english"}:
            raise ValueError("invalid_translation_direction")

        tokens = cls._tokenize_translation_input(source_raw)
        if len(tokens) == 0:
            raise ValueError("translation_tokens_required")

        lesson_assets = cls._lesson_backed_translation_assets()
        lex_en_to_shy = dict(cls._SHYGAZUN_TRANSLATION_LEXICON_EN_TO_SHY)
        lex_en_to_shy.update(cast(dict[str, str], lesson_assets["english_to_shygazun"]))
        lex_shy_to_en = {value.lower(): key for key, value in lex_en_to_shy.items()}
        lex_shy_to_en.update(cast(dict[str, str], lesson_assets["shygazun_to_english"]))

        if direction == "auto":
            has_compound_shape = any(re.search(r"[A-Z][a-z]+[A-Z]", token) for token in tokens)
            if has_compound_shape:
                direction = "shygazun_to_english"
            else:
                direction = "english_to_shygazun"

        translated: list[str] = []
        unresolved: list[str] = []
        mappings: list[dict[str, object]] = []

        if direction == "english_to_shygazun":
            normalized_english = " ".join(token.lower() for token in tokens)
            exact_projection = cast(dict[str, str], lesson_assets["english_examples"]).get(normalized_english)
            if exact_projection is not None:
                translated = exact_projection.split(" ")
                target_text = exact_projection
                mappings = [
                    {"source": source_raw, "target": exact_projection, "resolved": True, "resolution_kind": "lesson_exact_projection"}
                ]
                resolved_count = len(tokens)
                token_count = len(tokens)
                confidence = 1.0
                round_trip_preview = normalized_english
                return {
                    "direction": direction,
                    "source_text": source_raw,
                    "target_text": target_text,
                    "token_count": token_count,
                    "resolved_count": resolved_count,
                    "unresolved": unresolved,
                    "confidence": confidence,
                    "mappings": mappings,
                    "round_trip_preview": round_trip_preview,
                    "lexicon_version": "phase2.lesson-backed",
                }
            for raw_token in tokens:
                token = raw_token.lower()
                mapped = lex_en_to_shy.get(token)
                if mapped is None:
                    unresolved.append(raw_token)
                    translated.append(raw_token)
                    mappings.append({"source": raw_token, "target": raw_token, "resolved": False})
                else:
                    translated.append(mapped)
                    mappings.append({"source": raw_token, "target": mapped, "resolved": True})
            target_text = " ".join(translated)
        else:
            normalized_shygazun = " ".join(tokens).lower()
            exact_projection = cast(dict[str, str], lesson_assets["shygazun_examples"]).get(normalized_shygazun)
            if exact_projection is not None:
                target_text = exact_projection
                mappings = [
                    {"source": source_raw, "target": exact_projection, "resolved": True, "resolution_kind": "lesson_exact_projection"}
                ]
                resolved_count = len(tokens)
                token_count = len(tokens)
                confidence = 1.0
                round_trip_preview = normalized_shygazun
                return {
                    "direction": direction,
                    "source_text": source_raw,
                    "target_text": target_text,
                    "token_count": token_count,
                    "resolved_count": resolved_count,
                    "unresolved": unresolved,
                    "confidence": confidence,
                    "mappings": mappings,
                    "round_trip_preview": round_trip_preview,
                    "lexicon_version": "phase2.lesson-backed",
                }
            for raw_token in tokens:
                token = raw_token.lower()
                mapped = lex_shy_to_en.get(token)
                if mapped is None:
                    unresolved.append(raw_token)
                    translated.append(raw_token.lower())
                    mappings.append({"source": raw_token, "target": raw_token.lower(), "resolved": False})
                else:
                    translated.append(mapped)
                    mappings.append({"source": raw_token, "target": mapped, "resolved": True})
            target_text = " ".join(translated)

        resolved_count = sum(1 for item in mappings if bool(item.get("resolved", False)))
        token_count = len(tokens)
        confidence = 0.0 if token_count == 0 else round(resolved_count / token_count, 4)
        round_trip_preview = ""
        if direction == "english_to_shygazun":
            back_tokens = []
            for token in translated:
                back_tokens.append(lex_shy_to_en.get(token.lower(), token.lower()))
            round_trip_preview = " ".join(back_tokens)
        else:
            back_tokens = []
            for token in translated:
                back_tokens.append(lex_en_to_shy.get(token.lower(), token))
            round_trip_preview = " ".join(back_tokens)

        return {
            "direction": direction,
            "source_text": source_raw,
            "target_text": target_text,
            "token_count": token_count,
            "resolved_count": resolved_count,
            "unresolved": unresolved,
            "confidence": confidence,
            "mappings": mappings,
            "round_trip_preview": round_trip_preview,
            "lexicon_version": "phase2.lesson-backed",
        }

    @classmethod
    def _canonical_symbol_lookup(cls) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for shy_token in cls._SHYGAZUN_TRANSLATION_LEXICON_EN_TO_SHY.values():
            lowered = str(shy_token).lower()
            if lowered != "" and lowered not in lookup:
                lookup[lowered] = str(shy_token)
        try:
            from qqva.shygazun_compiler import default_symbol_inventory

            inventory = default_symbol_inventory()
            by_symbol = getattr(inventory, "by_symbol", {})
            if isinstance(by_symbol, dict):
                for symbol_obj in by_symbol.keys():
                    symbol = str(symbol_obj)
                    lowered = symbol.lower()
                    if lowered not in lookup:
                        lookup[lowered] = symbol
        except Exception:
            lookup = {}
        return lookup

    @classmethod
    def _canonicalize_shygazun_token(
        cls,
        *,
        token: str,
        lookup: Mapping[str, str],
    ) -> tuple[str, bool, list[str]]:
        raw = token.strip()
        if raw == "":
            return raw, False, []
        direct = lookup.get(raw.lower())
        if direct is not None:
            return direct, True, [direct]
        if not raw.isalpha():
            return raw, False, []

        n = len(raw)
        best: list[list[str] | None] = [None] * (n + 1)
        best[0] = []
        for index in range(n):
            prefix = best[index]
            if prefix is None:
                continue
            for end in range(index + 1, n + 1):
                segment = raw[index:end].lower()
                canonical = lookup.get(segment)
                if canonical is None:
                    continue
                candidate = [*prefix, canonical]
                existing = best[end]
                if existing is None or len(candidate) < len(existing):
                    best[end] = candidate
        segments = best[n]
        if segments is None or len(segments) == 0:
            return raw, False, []
        corrected = "".join(segments)
        return corrected, True, segments

    @classmethod
    def _correct_shygazun_runtime(cls, payload: Mapping[str, object]) -> dict[str, object]:
        source_raw = str(payload.get("source_text", "")).strip()
        if source_raw == "":
            raise ValueError("source_text_required")
        lookup = cls._canonical_symbol_lookup()
        word_pattern = re.compile(r"[A-Za-z]+")
        corrected_parts: list[str] = []
        corrections: list[dict[str, object]] = []
        unresolved: list[str] = []
        cursor = 0
        resolved_count = 0
        for match in word_pattern.finditer(source_raw):
            start, end = match.span()
            raw_token = source_raw[start:end]
            corrected_parts.append(source_raw[cursor:start])
            corrected_token, resolved, segments = cls._canonicalize_shygazun_token(
                token=raw_token,
                lookup=lookup,
            )
            corrected_parts.append(corrected_token)
            if resolved:
                resolved_count += 1
            else:
                unresolved.append(raw_token)
            corrections.append(
                {
                    "source": raw_token,
                    "corrected": corrected_token,
                    "resolved": resolved,
                    "segments": segments,
                }
            )
            cursor = end
        corrected_parts.append(source_raw[cursor:])
        corrected_text = "".join(corrected_parts)
        token_count = len(corrections)
        confidence = 0.0 if token_count == 0 else round(resolved_count / token_count, 4)
        return {
            "source_text": source_raw,
            "corrected_text": corrected_text,
            "token_count": token_count,
            "resolved_count": resolved_count,
            "unresolved": unresolved,
            "confidence": confidence,
            "corrections": corrections,
            "mode": "canonical_symbol_case_and_segmentation",
        }

    def translate_shygazun(self, payload: ShygazunTranslateInput) -> ShygazunTranslateOut:
        out = self._translate_shygazun_runtime(
            {
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
                "source_text": payload.source_text,
                "direction": payload.direction,
            }
        )
        lineage_nodes, lineage_edges, fn_id, fn_hash, node_refs, nodes_by_layer = self._persist_math_lineage(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            node_payloads=[
                (
                    1,
                    "shygazun.translate.byte_basis",
                    {
                        "source_bytes": list(payload.source_text.encode("utf-8")),
                        "token_count": int(out.get("token_count", 0)),
                    },
                ),
                (
                    7,
                    "shygazun.translate.causal_chunk",
                    {
                        "direction": str(out.get("direction", payload.direction)),
                        "resolved_count": int(out.get("resolved_count", 0)),
                        "unresolved_count": len(cast(list[object], out.get("unresolved", []))),
                    },
                ),
                (
                    8,
                    "shygazun.translate.path",
                    {
                        "mappings": cast(list[dict[str, object]], out.get("mappings", [])),
                    },
                ),
                (
                    9,
                    "shygazun.translate.dialogue",
                    {
                        "source_text": str(out.get("source_text", payload.source_text)),
                        "target_text": str(out.get("target_text", "")),
                    },
                ),
                (
                    10,
                    "shygazun.translate.entities",
                    {
                        "resolved_targets": [
                            str(item.get("target", ""))
                            for item in cast(list[dict[str, object]], out.get("mappings", []))
                            if bool(item.get("resolved", False))
                        ],
                    },
                ),
                (
                    11,
                    "shygazun.translate.render_constraints",
                    {
                        "lexicon_version": str(out.get("lexicon_version", "phase1.v1")),
                        "confidence": float(out.get("confidence", 0.0)),
                    },
                ),
            ],
            edge_payloads=[
                ("derives", 1, 7, {"from_key": "shygazun.translate.byte_basis", "to_key": "shygazun.translate.causal_chunk"}),
                ("indexes", 7, 8, {"from_key": "shygazun.translate.causal_chunk", "to_key": "shygazun.translate.path"}),
                ("binds", 8, 9, {"from_key": "shygazun.translate.path", "to_key": "shygazun.translate.dialogue"}),
                ("names", 9, 10, {"from_key": "shygazun.translate.dialogue", "to_key": "shygazun.translate.entities"}),
                ("constrains", 10, 11, {"from_key": "shygazun.translate.entities", "to_key": "shygazun.translate.render_constraints"}),
            ],
            function_id="shygazun.translate.compute",
            function_signature="(source_text:str,direction:str)->translation",
            function_body="deterministic lexical mapping with unresolved passthrough",
            function_metadata={
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
                "direction": payload.direction,
            },
        )
        out.update(
            {
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
                "lineage_node_ids": lineage_nodes,
                "lineage_edge_ids": lineage_edges,
                "lineage_node_refs": node_refs,
                "lineage_nodes_by_layer": nodes_by_layer,
                "function_store_id": fn_id,
                "function_hash": fn_hash,
            }
        )
        return ShygazunTranslateOut(**out)

    def interpret_shygazun(self, payload: ShygazunInterpretInput) -> ShygazunInterpretOut:
        out = self._interpret_shygazun_runtime(
            {
                "utterance": payload.utterance,
                "deity": payload.deity,
                "mode": payload.mode,
                "explain_mode": payload.explain_mode,
                "lore_overlay": payload.lore_overlay,
                "mutate_tokens": payload.mutate_tokens,
                "kaganue_pressure": payload.kaganue_pressure,
            }
        )
        lineage_nodes, lineage_edges, fn_id, fn_hash, node_refs, nodes_by_layer = self._persist_math_lineage(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            node_payloads=[
                (
                    1,
                    "shygazun.interpret.byte_basis",
                    {
                        "utterance_bytes": list(payload.utterance.encode("utf-8")),
                        "token_count": int(
                            self._int_from_table(
                                self._dict_from_table(out.get("semantic_payload")).get("token_count"),
                                0,
                            )
                        ),
                    },
                ),
                (
                    7,
                    "shygazun.interpret.causal_chunk",
                    {
                        "deity": str(out.get("deity", "")),
                        "demon": str(out.get("demon", "")),
                        "mutated_count": int(self._int_from_table(out.get("mutated_count"), 0)),
                    },
                ),
                (
                    8,
                    "shygazun.interpret.path",
                    {
                        "canonical_tokens": cast(list[object], out.get("canonical_tokens", [])),
                        "interpreted_tokens": cast(list[object], out.get("interpreted_tokens", [])),
                    },
                ),
                (
                    9,
                    "shygazun.interpret.dialogue",
                    {
                        "utterance": str(out.get("utterance", "")),
                    },
                ),
                (
                    11,
                    "shygazun.interpret.render_constraints",
                    {
                        "confusion_index": float(out.get("confusion_index", 0.0)),
                        "kaganue_pressure": float(out.get("kaganue_pressure", 0.0)),
                    },
                ),
            ],
            edge_payloads=[
                ("derives", 1, 7, {"from_key": "shygazun.interpret.byte_basis", "to_key": "shygazun.interpret.causal_chunk"}),
                ("indexes", 7, 8, {"from_key": "shygazun.interpret.causal_chunk", "to_key": "shygazun.interpret.path"}),
                ("binds", 8, 9, {"from_key": "shygazun.interpret.path", "to_key": "shygazun.interpret.dialogue"}),
                ("constrains", 9, 11, {"from_key": "shygazun.interpret.dialogue", "to_key": "shygazun.interpret.render_constraints"}),
            ],
            function_id="shygazun.interpret.compute",
            function_signature="(utterance:str,pressure:float,mode:str)->semantic_payload",
            function_body="deterministic token interpretation with optional confusion mutation",
            function_metadata={
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
                "mode": payload.mode,
            },
        )
        out.update(
            {
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
                "lineage_node_ids": lineage_nodes,
                "lineage_edge_ids": lineage_edges,
                "lineage_node_refs": node_refs,
                "lineage_nodes_by_layer": nodes_by_layer,
                "function_store_id": fn_id,
                "function_hash": fn_hash,
            }
        )
        return ShygazunInterpretOut(**out)

    def correct_shygazun(self, payload: ShygazunCorrectInput) -> ShygazunCorrectOut:
        out = self._correct_shygazun_runtime(
            {
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
                "source_text": payload.source_text,
            }
        )
        lineage_nodes, lineage_edges, fn_id, fn_hash, node_refs, nodes_by_layer = self._persist_math_lineage(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            node_payloads=[
                (
                    1,
                    "shygazun.correct.byte_basis",
                    {
                        "source_bytes": list(payload.source_text.encode("utf-8")),
                        "token_count": int(out.get("token_count", 0)),
                    },
                ),
                (
                    7,
                    "shygazun.correct.causal_chunk",
                    {
                        "resolved_count": int(out.get("resolved_count", 0)),
                        "unresolved_count": len(cast(list[object], out.get("unresolved", []))),
                        "mode": str(out.get("mode", "canonical_symbol_case_and_segmentation")),
                    },
                ),
                (
                    8,
                    "shygazun.correct.path",
                    {
                        "corrections": cast(list[dict[str, object]], out.get("corrections", [])),
                    },
                ),
                (
                    9,
                    "shygazun.correct.dialogue",
                    {
                        "source_text": str(out.get("source_text", payload.source_text)),
                        "corrected_text": str(out.get("corrected_text", "")),
                    },
                ),
                (
                    11,
                    "shygazun.correct.render_constraints",
                    {
                        "confidence": float(out.get("confidence", 0.0)),
                        "mode": str(out.get("mode", "canonical_symbol_case_and_segmentation")),
                    },
                ),
            ],
            edge_payloads=[
                ("derives", 1, 7, {"from_key": "shygazun.correct.byte_basis", "to_key": "shygazun.correct.causal_chunk"}),
                ("indexes", 7, 8, {"from_key": "shygazun.correct.causal_chunk", "to_key": "shygazun.correct.path"}),
                ("binds", 8, 9, {"from_key": "shygazun.correct.path", "to_key": "shygazun.correct.dialogue"}),
                ("constrains", 9, 11, {"from_key": "shygazun.correct.dialogue", "to_key": "shygazun.correct.render_constraints"}),
            ],
            function_id="shygazun.correct.compute",
            function_signature="(source_text:str)->canonicalized_text",
            function_body="deterministic case+segmentation correction against canonical symbol lookup",
            function_metadata={
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
            },
        )
        out.update(
            {
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
                "lineage_node_ids": lineage_nodes,
                "lineage_edge_ids": lineage_edges,
                "lineage_node_refs": node_refs,
                "lineage_nodes_by_layer": nodes_by_layer,
                "function_store_id": fn_id,
                "function_hash": fn_hash,
            }
        )
        return ShygazunCorrectOut(**out)

    @staticmethod
    def _csv_to_list(value: str) -> list[str]:
        if value.strip() == "":
            return []
        return [item for item in value.split(",") if item]

    @staticmethod
    def _list_to_csv(values: Sequence[str]) -> str:
        return ",".join(item.strip() for item in values if item.strip() != "")

    @staticmethod
    def _repo_root_path() -> Path:
        return Path(__file__).resolve().parents[3]

    @classmethod
    def _module_specs_dir(cls) -> Path:
        return cls._repo_root_path() / "gameplay" / "modules"

    @classmethod
    def _deep_merge_map(cls, base: Mapping[str, object], override: Mapping[str, object]) -> dict[str, object]:
        merged = dict(base)
        for key, value in override.items():
            if (
                key in merged
                and isinstance(merged.get(key), dict)
                and isinstance(value, dict)
            ):
                merged[key] = cls._deep_merge_map(
                    cast(dict[str, object], merged[key]),
                    cast(dict[str, object], value),
                )
            else:
                merged[key] = value
        return merged

    @classmethod
    def _load_module_spec(cls, module_id: str) -> dict[str, object]:
        normalized = module_id.strip()
        if normalized == "":
            raise ValueError("module_id_required")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
            raise ValueError("invalid_module_id")
        spec_path = cls._module_specs_dir() / f"{normalized}.json"
        if not spec_path.is_file():
            raise ValueError("module_spec_not_found")
        parsed = json.loads(spec_path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("invalid_module_spec")
        return cast(dict[str, object], parsed)

    @classmethod
    def _module_spec_to_out(cls, spec: Mapping[str, object]) -> ModuleSpecOut:
        inputs_obj = spec.get("inputs")
        inputs = cast(dict[str, object], inputs_obj) if isinstance(inputs_obj, dict) else {}
        outputs_obj = spec.get("outputs")
        outputs = cast(dict[str, object], outputs_obj) if isinstance(outputs_obj, dict) else {}
        execution_obj = spec.get("execution")
        execution = cast(dict[str, object], execution_obj) if isinstance(execution_obj, dict) else {}
        required_refs_obj = inputs.get("required_refs")
        optional_refs_obj = inputs.get("optional_refs")
        expected_ref_keys_obj = outputs.get("expected_ref_keys")
        payload_obj = inputs.get("payload")
        return ModuleSpecOut(
            module_id=str(spec.get("module_id", "")),
            module_version=str(spec.get("module_version", "")),
            purpose=str(spec.get("purpose", "")),
            runtime_action_kind=str(execution.get("runtime_action_kind", "")),
            required_refs=[str(item) for item in required_refs_obj] if isinstance(required_refs_obj, list) else [],
            optional_refs=[str(item) for item in optional_refs_obj] if isinstance(optional_refs_obj, list) else [],
            expected_ref_keys=[str(item) for item in expected_ref_keys_obj] if isinstance(expected_ref_keys_obj, list) else [],
            payload=cast(dict[str, object], payload_obj) if isinstance(payload_obj, dict) else {},
        )

    def _validate_module_spec_dict(self, spec: Mapping[str, object]) -> ModuleValidateOut:
        errors: list[str] = []
        warnings: list[str] = []
        module_id = str(spec.get("module_id", "")).strip()
        module_version = str(spec.get("module_version", "")).strip()
        if module_id == "":
            errors.append("module_id_required")
        elif not re.fullmatch(r"[A-Za-z0-9._-]+", module_id):
            errors.append("invalid_module_id")
        if module_version == "":
            errors.append("module_version_required")

        execution_obj = spec.get("execution")
        execution = cast(dict[str, object], execution_obj) if isinstance(execution_obj, dict) else {}
        runtime_action_kind = str(execution.get("runtime_action_kind", "")).strip()
        if runtime_action_kind == "":
            errors.append("runtime_action_kind_required")
        elif runtime_action_kind == "module.run":
            errors.append("module_run_recursion_disallowed")
        else:
            valid_kinds = {item.kind for item in self.runtime_action_catalog().actions}
            if runtime_action_kind not in valid_kinds:
                errors.append("unsupported_runtime_action_kind")

        inputs_obj = spec.get("inputs")
        inputs = cast(dict[str, object], inputs_obj) if isinstance(inputs_obj, dict) else {}
        payload_obj = inputs.get("payload")
        if not isinstance(payload_obj, dict):
            errors.append("inputs.payload_required")

        outputs_obj = spec.get("outputs")
        outputs = cast(dict[str, object], outputs_obj) if isinstance(outputs_obj, dict) else {}
        expected_ref_keys_obj = outputs.get("expected_ref_keys")
        if expected_ref_keys_obj is not None and not isinstance(expected_ref_keys_obj, list):
            errors.append("outputs.expected_ref_keys_must_be_list")
        if isinstance(expected_ref_keys_obj, list):
            for item in expected_ref_keys_obj:
                ref = str(item).strip()
                if not re.fullmatch(r"L\d+:[A-Za-z0-9._-]+", ref):
                    errors.append(f"invalid_expected_ref_key:{ref}")
        if isinstance(expected_ref_keys_obj, list) and len(expected_ref_keys_obj) == 0:
            warnings.append("expected_ref_keys_empty")

        return ModuleValidateOut(
            ok=len(errors) == 0,
            module_id=module_id,
            module_version=module_version,
            runtime_action_kind=runtime_action_kind,
            errors=sorted(set(errors)),
            warnings=sorted(set(warnings)),
        )

    def list_module_specs(self) -> ModuleCatalogOut:
        specs_dir = self._module_specs_dir()
        modules: list[ModuleSpecOut] = []
        if specs_dir.is_dir():
            for path in sorted(specs_dir.glob("*.json")):
                try:
                    parsed = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(parsed, dict):
                        modules.append(self._module_spec_to_out(cast(dict[str, object], parsed)))
                except Exception:
                    continue
        modules.sort(key=lambda item: item.module_id)
        return ModuleCatalogOut(module_count=len(modules), modules=modules)

    def get_module_spec(self, module_id: str) -> ModuleSpecOut:
        spec = self._load_module_spec(module_id)
        return self._module_spec_to_out(spec)

    def validate_module_spec(self, payload: ModuleValidateInput) -> ModuleValidateOut:
        if payload.spec is not None:
            return self._validate_module_spec_dict(payload.spec)
        if payload.module_id is None:
            raise ValueError("module_id_or_spec_required")
        spec = self._load_module_spec(payload.module_id)
        return self._validate_module_spec_dict(spec)

    @staticmethod
    def _json_to_object_map(value: str) -> dict[str, object]:
        if value.strip() == "":
            return {}
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, object] = {}
        for key, item in parsed.items():
            if isinstance(key, str):
                out[key] = cast(object, item)
        return out

    @staticmethod
    def _default_player_tables() -> PlayerStateTables:
        return PlayerStateTables(
            levels={},
            skills={},
            perks={},
            vitriol={},
            inventory={},
            market={},
            flags={},
            clock={},
        )

    @staticmethod
    def _merge_player_tables(base: PlayerStateTables, incoming: PlayerStateTables) -> PlayerStateTables:
        def merge_map(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
            merged = dict(left)
            for key, value in right.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = merge_map(cast(dict[str, object], merged[key]), cast(dict[str, object], value))
                else:
                    merged[key] = value
            return merged

        return PlayerStateTables(
            levels=merge_map(base.levels, incoming.levels),
            skills=merge_map(base.skills, incoming.skills),
            perks=merge_map(base.perks, incoming.perks),
            vitriol=merge_map(base.vitriol, incoming.vitriol),
            inventory=merge_map(base.inventory, incoming.inventory),
            market=merge_map(base.market, incoming.market),
            flags=merge_map(base.flags, incoming.flags),
            clock=merge_map(base.clock, incoming.clock),
        )

    def health(self) -> None:
        self._require_repo().ping()

    def _database_health_status(self) -> Mapping[str, Any]:
        try:
            self.health()
            return {"status": "up"}
        except Exception as exc:
            return {"status": "down", "detail": str(exc)}

    def _kernel_health_status(self) -> Mapping[str, Any]:
        settings = load_settings()
        try:
            health = self._kernel.health_status(actor_id="healthcheck", workshop_id="system")
            return {
                "status": "up",
                "base_url": str(settings.kernel_internal_base_url or settings.kernel_base_url or "").strip() or None,
                "health": dict(health) if isinstance(health, Mapping) else {"raw": health},
            }
        except Exception as exc:
            return {
                "status": "down",
                "detail": str(exc),
                "base_url": str(settings.kernel_internal_base_url or settings.kernel_base_url or "").strip() or None,
            }

    def _migration_health_status(self) -> Mapping[str, Any]:
        try:
            status = dict(self.get_migration_status())
            return {
                "status": "up" if bool(status.get("up_to_date")) else "down",
                **status,
            }
        except Exception as exc:
            return {"status": "down", "detail": str(exc)}

    def _config_health_status(self) -> Mapping[str, Any]:
        settings = load_settings()
        database_url = str(settings.database_url or "").strip()
        kernel_base_url = str(settings.kernel_base_url or "").strip()
        kernel_internal_base_url = str(settings.kernel_internal_base_url or "").strip()
        admin_gate_code = str(settings.admin_gate_code or "").strip()
        auth_token_secret = str(settings.auth_token_secret or "").strip()
        issues: list[str] = []
        if not kernel_base_url:
            issues.append("kernel_base_url_missing")
        elif "onrender.com" in kernel_base_url and not kernel_internal_base_url:
            issues.append("kernel_internal_base_url_missing")
        if not database_url:
            issues.append("database_url_missing")
        elif "127.0.0.1:5432" in database_url or database_url.endswith("@127.0.0.1:5432/atelier"):
            issues.append("database_url_local_default")
        if not admin_gate_code or admin_gate_code in ("CHANGE_ME", "STEWARD_DEV_GATE"):
            issues.append("admin_gate_code_default")
        if not auth_token_secret or auth_token_secret == "DEV_ONLY_CHANGE_ME":
            issues.append("auth_token_secret_default")
        return {
            "status": "up" if not issues else "warning",
            "issues": issues,
            "kernel_base_url": kernel_base_url,
            "kernel_internal_base_url": kernel_internal_base_url or None,
            "kernel_connect_retries": settings.kernel_connect_retries,
            "kernel_connect_backoff_ms": settings.kernel_connect_backoff_ms,
        }

    def get_readiness_status(self) -> Mapping[str, Any]:
        database = self._database_health_status()
        kernel = self._kernel_health_status()
        migrations = self._migration_health_status()
        config = self._config_health_status()
        ready = (
            str(database.get("status")) == "up"
            and str(kernel.get("status")) == "up"
            and str(migrations.get("status")) == "up"
            and str(config.get("status")) in ("up",)
        )
        return {
            "status": "ready" if ready else "not_ready",
            "api": {"status": "up"},
            "database": database,
            "kernel": kernel,
            "migrations": migrations,
            "config": config,
        }

    def get_federation_health(self, *, distribution_id: Optional[str] = None, limit: int = 25) -> Mapping[str, Any]:
        local_protocol = {
            "family": self._GUILD_MESSAGE_PROTOCOL_FAMILY,
            "version": self._GUILD_MESSAGE_PROTOCOL_VERSION,
            "supported_versions": list(self._GUILD_MESSAGE_SUPPORTED_PROTOCOL_VERSIONS),
        }
        targets: list[Mapping[str, Any]] = []
        distribution_records: list[Mapping[str, Any]]
        if distribution_id:
            try:
                distribution_records = [self.get_distribution_registry_entry(distribution_id=distribution_id)]
            except ValueError as exc:
                if str(exc) != "distribution_not_found":
                    raise
                distribution_id_norm = str(distribution_id or "").strip() or "unknown_distribution"
                return {
                    "status": "degraded",
                    "local_protocol": local_protocol,
                    "readiness": self.get_readiness_status(),
                    "target_count": 1,
                    "active_trust_count": 0,
                    "error_count": 1,
                    "targets": [
                        {
                            "distribution_id": distribution_id_norm,
                            "display_name": distribution_id_norm,
                            "base_url": None,
                            "status": "error",
                            "trust_grade": "unreachable",
                            "detail": "distribution_not_found",
                        }
                    ],
                }
        else:
            distribution_records = list(self.list_distribution_registry(limit=limit))
        for record in distribution_records:
            distribution_id_norm = str(record.get("distribution_id") or "").strip()
            if not distribution_id_norm:
                continue
            summary: dict[str, Any] = {
                "distribution_id": distribution_id_norm,
                "display_name": str(record.get("display_name") or "").strip() or distribution_id_norm,
                "base_url": str(record.get("base_url") or "").strip() or None,
                "status": "unknown",
                "trust_grade": "unknown",
            }
            try:
                capabilities = self.discover_distribution_capabilities(distribution_id=distribution_id_norm)
                summary["capabilities"] = capabilities
                summary["status"] = "reachable"
                key_descriptor = capabilities.get("key_descriptor") if isinstance(capabilities, Mapping) else None
                handshake = capabilities.get("handshake") if isinstance(capabilities, Mapping) else None
                messaging_protocol = capabilities.get("messaging_protocol") if isinstance(capabilities, Mapping) else None
                summary["key_present"] = bool(isinstance(key_descriptor, Mapping) and key_descriptor.get("public_key_ref"))
                summary["handshake_active"] = bool(isinstance(handshake, Mapping) and handshake.get("handshake_id"))
                try:
                    self._ensure_distribution_protocol_compatibility(distribution_id=distribution_id_norm)
                    summary["protocol_compatible"] = True
                except Exception as exc:
                    summary["protocol_compatible"] = False
                    summary["protocol_detail"] = str(exc)
                if summary["key_present"] and summary["handshake_active"] and summary.get("protocol_compatible"):
                    summary["trust_grade"] = "active"
                elif summary["key_present"] and summary.get("protocol_compatible"):
                    summary["trust_grade"] = "key_known"
                elif summary["key_present"]:
                    summary["trust_grade"] = "key_only"
                else:
                    summary["trust_grade"] = "untrusted"
                if isinstance(messaging_protocol, Mapping):
                    summary["messaging_protocol"] = dict(messaging_protocol)
            except Exception as exc:
                summary["status"] = "error"
                summary["trust_grade"] = "unreachable"
                summary["detail"] = str(exc)
            targets.append(summary)
        active_count = sum(1 for item in targets if str(item.get("trust_grade")) == "active")
        error_count = sum(1 for item in targets if str(item.get("status")) == "error")
        return {
            "status": "ok" if error_count == 0 else "degraded",
            "local_protocol": local_protocol,
            "readiness": self.get_readiness_status(),
            "target_count": len(targets),
            "active_trust_count": active_count,
            "error_count": error_count,
            "targets": targets,
        }

    def emit_placement(
        self,
        *,
        raw: str,
        context: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.place(
            raw=raw,
            context=context,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

    def observe(self, *, actor_id: str, workshop_id: str) -> ObserveResponse:
        return self._kernel.observe(actor_id=actor_id, workshop_id=workshop_id)

    def timeline(self, *, actor_id: str, workshop_id: str) -> Sequence[KernelEventObj]:
        return self._kernel.timeline(actor_id=actor_id, workshop_id=workshop_id)

    def edges(self, *, actor_id: str, workshop_id: str) -> Sequence[EdgeObj]:
        return self._kernel.edges(actor_id=actor_id, workshop_id=workshop_id)

    def frontiers(self, *, actor_id: str, workshop_id: str) -> Sequence[FrontierObj]:
        return self._kernel.frontiers(actor_id=actor_id, workshop_id=workshop_id)

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.attest(
            witness_id=witness_id,
            attestation_kind=attestation_kind,
            attestation_tag=attestation_tag,
            payload=payload,
            target=target,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

    def akinenwun_lookup(
        self,
        *,
        akinenwun: str,
        mode: str,
        ingest: bool,
        policy: Mapping[str, Any] | None = None,
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.akinenwun_lookup(
            akinenwun=akinenwun,
            mode=mode,
            ingest=ingest,
            policy=policy or {},
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

    def validate_wand_damage_attestation(
        self,
        *,
        wand_id: str,
        notifier_id: str,
        damage_state: str,
        event_tag: Optional[str],
        media: Sequence[Mapping[str, Any]],
        payload: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        return self._kernel.validate_wand_damage_attestation(
            wand_id=wand_id,
            notifier_id=notifier_id,
            damage_state=damage_state,
            event_tag=event_tag,
            media=media,
            payload=payload,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )

    @classmethod
    def _security_state_dir(cls) -> Path:
        env_path = os.environ.get("ATELIER_SECURITY_STATE_DIR", "").strip()
        if env_path:
            root = Path(env_path)
        else:
            root = Path(__file__).resolve().parents[1] / "runtime" / "security"
        root.mkdir(parents=True, exist_ok=True)
        return root

    @classmethod
    def _security_bucket_dir(cls, bucket: str) -> Path:
        target = cls._security_state_dir() / bucket
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _safe_storage_component(value: Optional[str], fallback: str) -> str:
        text = str(value or "").strip()
        if text == "":
            text = fallback
        cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in text)
        return cleaned or fallback

    @classmethod
    def _load_bucket_records(cls, bucket: str) -> list[dict[str, Any]]:
        root = cls._security_bucket_dir(bucket)
        records: list[dict[str, Any]] = []
        for path in sorted(root.glob("*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return records

    @classmethod
    def _load_recursive_records(cls, bucket: str) -> list[dict[str, Any]]:
        root = cls._security_bucket_dir(bucket)
        records: list[dict[str, Any]] = []
        for path in sorted(root.glob("**/*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return records

    @classmethod
    @lru_cache(maxsize=8)
    def _schema_validator(cls, schema_name: str) -> Draft202012Validator:
        schema_path = cls._repo_root_path() / "schemas" / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        return Draft202012Validator(schema)

    @classmethod
    def _normalize_entropy_source(cls, *, label: str, source: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
        if not isinstance(source, Mapping):
            return None
        normalized = {str(key): value for key, value in dict(source).items()}
        if not normalized:
            return None
        if label == "temple":
            schema_family = "temple_entropy_source"
            required_fields = ("provenance_id", "source_type", "state_digest")
        elif label == "theatre":
            schema_family = "theatre_entropy_source"
            required_fields = ("provenance_id", "source_type", "media_digest")
        else:
            raise ValueError(f"unsupported_entropy_source_label:{label}")
        if str(normalized.get("schema_family") or "").strip() != schema_family:
            raise ValueError(f"{label}_entropy_source_schema_family_invalid")
        if str(normalized.get("schema_version") or "").strip() != "v1":
            raise ValueError(f"{label}_entropy_source_schema_version_invalid")
        for field_name in required_fields:
            if str(normalized.get(field_name) or "").strip() == "":
                raise ValueError(f"{label}_entropy_source_{field_name}_required")
        schema_name = f"{schema_family}.schema.json"
        try:
            cls._schema_validator(schema_name).validate(normalized)
        except Exception as exc:
            raise ValueError(f"{label}_entropy_source_schema_validation_failed:{str(exc)}") from exc
        return normalized

    @classmethod
    def _resolve_entropy_component(
        cls,
        *,
        digest: Optional[str],
        source: Optional[Mapping[str, Any]],
        label: str,
    ) -> dict[str, Any]:
        digest_text = str(digest or "").strip()
        source_payload = cls._normalize_entropy_source(label=label, source=source)
        if source_payload is not None:
            if digest_text == "":
                digest_text = cls._canonical_hash(source_payload)
            return {
                "digest": hashlib.sha256(digest_text.encode("utf-8")).hexdigest(),
                "source_record": source_payload,
                "label": label,
            }
        return {
            "digest": hashlib.sha256(digest_text.encode("utf-8")).hexdigest(),
            "source_record": None,
            "label": label,
        }

    @classmethod
    def _entropy_mix_runtime(
        cls,
        *,
        wand_id: str,
        wand_passkey_ward: Optional[str] = None,
        temple_entropy_digest: Optional[str] = None,
        theatre_entropy_digest: Optional[str] = None,
        attestation_media_digests: Sequence[str] = (),
        context: Mapping[str, Any],
        system_entropy_digest: Optional[str] = None,
        temple_entropy_source: Optional[Mapping[str, Any]] = None,
        theatre_entropy_source: Optional[Mapping[str, Any]] = None,
        attestation_sources: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, object]:
        media_digests = [str(item).strip() for item in attestation_media_digests if str(item).strip() != ""]
        context_digest = hashlib.sha256(
            json.dumps(dict(context), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        effective_system_entropy_digest = system_entropy_digest or hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        wand_digest = hashlib.sha256(str(wand_id).encode("utf-8")).hexdigest()
        wand_passkey_digest = hashlib.sha256(str(wand_passkey_ward or "").encode("utf-8")).hexdigest()
        temple_component = cls._resolve_entropy_component(
            digest=temple_entropy_digest,
            source=temple_entropy_source,
            label="temple",
        )
        theatre_component = cls._resolve_entropy_component(
            digest=theatre_entropy_digest,
            source=theatre_entropy_source,
            label="theatre",
        )
        normalized_attestation_sources = [dict(item) for item in attestation_sources if isinstance(item, Mapping)]
        if normalized_attestation_sources and not media_digests:
            media_digests = [cls._canonical_hash(item) for item in normalized_attestation_sources]
        attestation_digest = hashlib.sha256("|".join(media_digests).encode("utf-8")).hexdigest()
        root_material = b"|".join(
            (
                bytes.fromhex(effective_system_entropy_digest),
                bytes.fromhex(wand_digest),
                bytes.fromhex(wand_passkey_digest),
                bytes.fromhex(str(temple_component["digest"])),
                bytes.fromhex(str(theatre_component["digest"])),
                bytes.fromhex(attestation_digest),
                bytes.fromhex(context_digest),
            )
        )
        mix_digest = hashlib.sha256(root_material).hexdigest()
        active_sources = 1 + int(bool(str(wand_passkey_ward or "").strip())) + int(bool(temple_entropy_digest)) + int(bool(theatre_entropy_digest)) + int(bool(media_digests))
        quality = "baseline"
        if active_sources >= 4:
            quality = "rich"
        elif active_sources >= 3:
            quality = "elevated"
        return {
            "schema_family": cls._TRI_SOURCE_ENTROPY_SCHEMA_FAMILY,
            "schema_version": cls._TRI_SOURCE_ENTROPY_SCHEMA_VERSION,
            "mix_digest": mix_digest,
            "quality": quality,
            "active_source_count": active_sources,
            "components": {
                "system_entropy_digest": effective_system_entropy_digest,
                "wand_digest": wand_digest,
                "wand_passkey_digest": wand_passkey_digest,
                "has_wand_passkey_ward": bool(str(wand_passkey_ward or "").strip()),
                "temple_entropy_digest": temple_component["digest"],
                "theatre_entropy_digest": theatre_component["digest"],
                "attestation_digest": attestation_digest,
                "context_digest": context_digest,
                "attestation_media_digests": media_digests,
                "temple_entropy_source": temple_component["source_record"],
                "theatre_entropy_source": theatre_component["source_record"],
                "attestation_sources": normalized_attestation_sources,
            },
        }

    @classmethod
    def _guild_message_keystream(cls, root_key: bytes, nonce: bytes, length: int) -> bytes:
        blocks: list[bytes] = []
        counter = 0
        while sum(len(item) for item in blocks) < length:
            block = hashlib.sha256(root_key + nonce + counter.to_bytes(4, "big")).digest()
            blocks.append(block)
            counter += 1
        return b"".join(blocks)[:length]

    @staticmethod
    def _semantic_relay_status(dispatch: Mapping[str, Any], *, remote: bool) -> str:
        channel = str(dispatch.get("dispatch_channel") or "local")
        if remote:
            if channel == "gateway":
                return "gateway_pending"
            if channel == "stream":
                return "stream_buffered"
            if channel == "packet":
                return "packet_pending"
            if channel == "event":
                return "event_pending"
            return "remote_pending"
        if channel == "stream":
            return "stream_local"
        if channel == "packet":
            return "packet_local"
        if channel == "event":
            return "event_local"
        return "local_only"

    @staticmethod
    def _semantic_storage_bucket(dispatch: Mapping[str, Any]) -> str:
        persistence_mode = str(dispatch.get("persistence_mode") or "ephemeral")
        mapping = {
            "persistent": "persistent",
            "database_cluster": "database_cluster",
            "archive": "archive",
            "directory": "directory",
            "cache": "cache",
            "buffered": "buffered",
            "ephemeral": "ephemeral",
        }
        return mapping.get(persistence_mode, "ephemeral")

    @staticmethod
    def _normalize_security_session(
        *,
        security_session: Optional[Mapping[str, Any]],
        conversation_id: Optional[str],
        conversation_kind: Optional[str],
        sender_member_id: Optional[str],
        recipient_member_id: Optional[str],
        recipient_distribution_id: Optional[str],
    ) -> dict[str, Any]:
        payload = dict(security_session or {})
        session_context = {
            "conversation_id": str(conversation_id or "").strip(),
            "conversation_kind": str(conversation_kind or "").strip() or "guild_channel",
            "sender_member_id": str(sender_member_id or "").strip(),
            "recipient_member_id": str(recipient_member_id or "").strip(),
            "recipient_distribution_id": str(recipient_distribution_id or "").strip(),
        }
        session_seed = json.dumps(session_context, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        session_id = str(payload.get("session_id") or "").strip() or (
            "gsess_" + hashlib.sha256(session_seed.encode("utf-8")).hexdigest()[:24]
        )
        return {
            "schema_family": str(payload.get("schema_family") or "signal_artifice_session"),
            "schema_version": str(payload.get("schema_version") or "v1"),
            "session_id": session_id,
            "session_mode": str(payload.get("session_mode") or "double_ratchet_like"),
            "sender_identity_key_ref": str(payload.get("sender_identity_key_ref") or sender_member_id or ""),
            "sender_signed_pre_key_ref": str(payload.get("sender_signed_pre_key_ref") or ""),
            "sender_one_time_pre_key_ref": str(payload.get("sender_one_time_pre_key_ref") or ""),
            "recipient_identity_key_ref": str(payload.get("recipient_identity_key_ref") or recipient_member_id or ""),
            "recipient_signed_pre_key_ref": str(payload.get("recipient_signed_pre_key_ref") or ""),
            "recipient_one_time_pre_key_ref": str(payload.get("recipient_one_time_pre_key_ref") or ""),
            "session_epoch": int(payload.get("session_epoch") or 1),
            "sealed_sender": bool(payload.get("sealed_sender", True)),
            "ratchet_seed_digest": str(
                payload.get("ratchet_seed_digest")
                or hashlib.sha256((session_id + "::ratchet").encode("utf-8")).hexdigest()
            ),
            "metadata": dict(payload.get("metadata") or {}),
        }

    @classmethod
    def _encrypt_guild_message_runtime(
        cls,
        *,
        guild_id: str,
        channel_id: str,
        sender_id: str,
        wand_id: str,
        message_text: str,
        wand_passkey_ward: Optional[str] = None,
        conversation_id: Optional[str] = None,
        conversation_kind: Optional[str] = None,
        thread_id: Optional[str] = None,
        sender_member_id: Optional[str] = None,
        recipient_member_id: Optional[str] = None,
        recipient_distribution_id: Optional[str] = None,
        recipient_guild_id: Optional[str] = None,
        recipient_channel_id: Optional[str] = None,
        recipient_actor_id: Optional[str] = None,
        temple_entropy_digest: Optional[str] = None,
        theatre_entropy_digest: Optional[str] = None,
        attestation_media_digests: Sequence[str] = (),
        temple_entropy_source: Optional[Mapping[str, Any]] = None,
        theatre_entropy_source: Optional[Mapping[str, Any]] = None,
        attestation_sources: Sequence[Mapping[str, Any]] = (),
        security_session: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, object]:
        metadata_payload = dict(metadata or {})
        session_payload = cls._normalize_security_session(
            security_session=security_session,
            conversation_id=conversation_id,
            conversation_kind=conversation_kind,
            sender_member_id=sender_member_id,
            recipient_member_id=recipient_member_id,
            recipient_distribution_id=recipient_distribution_id,
        )
        header_context = {
            "conversation_id": conversation_id or "",
            "conversation_kind": conversation_kind or "guild_channel",
            "guild_id": guild_id,
            "channel_id": channel_id,
            "thread_id": thread_id or "",
            "sender_id": sender_id,
            "sender_member_id": sender_member_id or "",
            "wand_id": wand_id,
            "recipient_member_id": recipient_member_id or "",
            "recipient_distribution_id": recipient_distribution_id or "",
            "recipient_guild_id": recipient_guild_id or "",
            "recipient_channel_id": recipient_channel_id or "",
            "recipient_actor_id": recipient_actor_id or "",
            "security_session": session_payload,
            "metadata": metadata_payload,
        }
        entropy_mix = cls._entropy_mix_runtime(
            wand_id=wand_id,
            wand_passkey_ward=wand_passkey_ward,
            temple_entropy_digest=temple_entropy_digest,
            theatre_entropy_digest=theatre_entropy_digest,
            attestation_media_digests=attestation_media_digests,
            context=header_context,
            temple_entropy_source=temple_entropy_source,
            theatre_entropy_source=theatre_entropy_source,
            attestation_sources=attestation_sources,
        )
        root_key = bytes.fromhex(str(entropy_mix["mix_digest"]))
        system_nonce = secrets.token_bytes(16)
        message_bytes = message_text.encode("utf-8")
        keystream = cls._guild_message_keystream(root_key, system_nonce, len(message_bytes))
        ciphertext = bytes(left ^ right for left, right in zip(message_bytes, keystream))
        mac = hmac.new(root_key, system_nonce + ciphertext, hashlib.sha256).hexdigest()
        return {
            "schema_family": cls._GUILD_MESSAGE_ENVELOPE_SCHEMA_FAMILY,
            "schema_version": cls._GUILD_MESSAGE_ENVELOPE_SCHEMA_VERSION,
            "cipher_family": cls._GUILD_MESSAGE_CIPHER_FAMILY,
            "conversation_id": str(conversation_id or "").strip() or None,
            "conversation_kind": str(conversation_kind or "").strip() or "guild_channel",
            "guild_id": guild_id,
            "channel_id": channel_id,
            "thread_id": thread_id,
            "sender_id": sender_id,
            "sender_member_id": str(sender_member_id or "").strip() or None,
            "wand_id": wand_id,
            "recipient_member_id": str(recipient_member_id or "").strip() or None,
            "recipient_distribution_id": str(recipient_distribution_id or "").strip() or None,
            "recipient_guild_id": str(recipient_guild_id or "").strip() or None,
            "recipient_channel_id": str(recipient_channel_id or "").strip() or None,
            "recipient_actor_id": str(recipient_actor_id or "").strip() or None,
            "security_session": session_payload,
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
            "nonce_b64": base64.b64encode(system_nonce).decode("ascii"),
            "mac_hex": mac,
            "plaintext_digest": hashlib.sha256(message_bytes).hexdigest(),
            "derivation": {**cast(Mapping[str, Any], entropy_mix["components"])},
            "entropy_mix": entropy_mix,
            "metadata": metadata_payload,
        }

    def encrypt_guild_message(
        self,
        *,
        guild_id: str,
        channel_id: str,
        sender_id: str,
        wand_id: str,
        message_text: str,
        wand_passkey_ward: Optional[str] = None,
        conversation_id: Optional[str] = None,
        conversation_kind: Optional[str] = None,
        thread_id: Optional[str] = None,
        sender_member_id: Optional[str] = None,
        recipient_member_id: Optional[str] = None,
        recipient_distribution_id: Optional[str] = None,
        recipient_guild_id: Optional[str] = None,
        recipient_channel_id: Optional[str] = None,
        recipient_actor_id: Optional[str] = None,
        temple_entropy_digest: Optional[str] = None,
        theatre_entropy_digest: Optional[str] = None,
        attestation_media_digests: Sequence[str] = (),
        temple_entropy_source: Optional[Mapping[str, Any]] = None,
        theatre_entropy_source: Optional[Mapping[str, Any]] = None,
        attestation_sources: Sequence[Mapping[str, Any]] = (),
        security_session: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        guild_id_norm = str(guild_id).strip()
        channel_id_norm = str(channel_id).strip()
        sender_id_norm = str(sender_id).strip()
        wand_id_norm = str(wand_id).strip()
        message_text_norm = str(message_text)
        if guild_id_norm == "":
            raise ValueError("guild_id_required")
        if channel_id_norm == "":
            raise ValueError("channel_id_required")
        if sender_id_norm == "":
            raise ValueError("sender_id_required")
        if wand_id_norm == "":
            raise ValueError("wand_id_required")
        if message_text_norm.strip() == "":
            raise ValueError("message_text_required")
        conversation_kind_norm = str(conversation_kind or "").strip() or "guild_channel"
        conversation_id_norm = str(conversation_id or "").strip() or None
        if conversation_kind_norm == "member_dm" and str(recipient_member_id or "").strip() == "":
            raise ValueError("recipient_member_id_required")
        latest_epoch = next(iter(self.list_wand_key_epochs(wand_id=wand_id_norm, limit=1)), None)
        if isinstance(latest_epoch, Mapping) and bool(latest_epoch.get("revoked")):
            raise ValueError("wand_revoked")
        recipient_distribution_norm = str(recipient_distribution_id or "").strip()
        recipient_metadata = dict(metadata or {})
        if recipient_distribution_norm:
            recipient_key = self.get_distribution_key_descriptor(distribution_id=recipient_distribution_norm)
            recipient_protocol = self._ensure_distribution_protocol_compatibility(distribution_id=recipient_distribution_norm)
            recipient_metadata = {
                **recipient_metadata,
                "recipient_distribution_key": recipient_key,
                "recipient_distribution_protocol": recipient_protocol["distribution"],
                "recipient_distribution_handshake_protocol": recipient_protocol["handshake"],
            }
        semantic_dispatch = derive_semantic_runtime_dispatch(message_text_norm)
        if semantic_dispatch is not None:
            recipient_metadata = {
                **recipient_metadata,
                "semantic_runtime_dispatch": dict(semantic_dispatch),
            }
        return self._encrypt_guild_message_runtime(
            guild_id=guild_id_norm,
            channel_id=channel_id_norm,
            sender_id=sender_id_norm,
            wand_id=wand_id_norm,
            wand_passkey_ward=wand_passkey_ward,
            message_text=message_text_norm,
            conversation_id=conversation_id_norm,
            conversation_kind=conversation_kind_norm,
            thread_id=thread_id,
            sender_member_id=sender_member_id,
            recipient_member_id=recipient_member_id,
            recipient_distribution_id=recipient_distribution_norm or None,
            recipient_guild_id=recipient_guild_id,
            recipient_channel_id=recipient_channel_id,
            recipient_actor_id=recipient_actor_id,
            temple_entropy_digest=temple_entropy_digest,
            theatre_entropy_digest=theatre_entropy_digest,
            attestation_media_digests=attestation_media_digests,
            temple_entropy_source=temple_entropy_source,
            theatre_entropy_source=theatre_entropy_source,
            attestation_sources=attestation_sources,
            security_session=security_session,
            metadata=recipient_metadata,
        )

    def decrypt_guild_message(
        self,
        *,
        envelope: Mapping[str, Any],
        wand_id: str,
        wand_passkey_ward: Optional[str],
        temple_entropy_digest: Optional[str],
        theatre_entropy_digest: Optional[str],
        attestation_media_digests: Sequence[str],
        temple_entropy_source: Optional[Mapping[str, Any]],
        theatre_entropy_source: Optional[Mapping[str, Any]],
        attestation_sources: Sequence[Mapping[str, Any]],
        metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        wand_id_norm = str(wand_id).strip()
        if wand_id_norm == "":
            raise ValueError("wand_id_required")
        latest_epoch = next(iter(self.list_wand_key_epochs(wand_id=wand_id_norm, limit=1)), None)
        if isinstance(latest_epoch, Mapping) and bool(latest_epoch.get("revoked")):
            raise ValueError("wand_revoked")
        derivation_obj = envelope.get("derivation")
        derivation = dict(cast(Mapping[str, Any], derivation_obj)) if isinstance(derivation_obj, Mapping) else {}
        header_context = {
            "guild_id": str(envelope.get("guild_id") or "").strip(),
            "channel_id": str(envelope.get("channel_id") or "").strip(),
            "conversation_id": str(envelope.get("conversation_id") or "").strip(),
            "conversation_kind": str(envelope.get("conversation_kind") or "").strip(),
            "thread_id": str(envelope.get("thread_id") or "").strip(),
            "sender_id": str(envelope.get("sender_id") or "").strip(),
            "sender_member_id": str(envelope.get("sender_member_id") or "").strip(),
            "wand_id": wand_id_norm,
            "recipient_member_id": str(envelope.get("recipient_member_id") or "").strip(),
            "recipient_distribution_id": str(envelope.get("recipient_distribution_id") or "").strip(),
            "recipient_guild_id": str(envelope.get("recipient_guild_id") or "").strip(),
            "recipient_channel_id": str(envelope.get("recipient_channel_id") or "").strip(),
            "recipient_actor_id": str(envelope.get("recipient_actor_id") or "").strip(),
            "security_session": dict(cast(Mapping[str, Any], envelope.get("security_session") or {})),
            "metadata": dict(metadata),
        }
        entropy_mix = self._entropy_mix_runtime(
            wand_id=wand_id_norm,
            wand_passkey_ward=wand_passkey_ward,
            temple_entropy_digest=temple_entropy_digest,
            theatre_entropy_digest=theatre_entropy_digest,
            attestation_media_digests=attestation_media_digests,
            context=header_context,
            system_entropy_digest=str(derivation.get("system_entropy_digest") or ""),
            temple_entropy_source=temple_entropy_source,
            theatre_entropy_source=theatre_entropy_source,
            attestation_sources=attestation_sources,
        )
        root_key = bytes.fromhex(str(entropy_mix["mix_digest"]))
        nonce = base64.b64decode(str(envelope.get("nonce_b64") or ""))
        ciphertext = base64.b64decode(str(envelope.get("ciphertext_b64") or ""))
        expected_mac = hmac.new(root_key, nonce + ciphertext, hashlib.sha256).hexdigest()
        provided_mac = str(envelope.get("mac_hex") or "")
        keystream = self._guild_message_keystream(root_key, nonce, len(ciphertext))
        plaintext_bytes = bytes(left ^ right for left, right in zip(ciphertext, keystream))
        try:
            plaintext = plaintext_bytes.decode("utf-8")
        except UnicodeDecodeError:
            plaintext = ""
        plaintext_digest = hashlib.sha256(plaintext_bytes).hexdigest()
        verified = (
            hmac.compare_digest(expected_mac, provided_mac)
            and plaintext_digest == str(envelope.get("plaintext_digest") or plaintext_digest)
            and plaintext != ""
        )
        return {
            "verified": verified,
            "plaintext": plaintext,
            "plaintext_digest": plaintext_digest,
            "expected_mac_hex": expected_mac,
            "provided_mac_hex": provided_mac,
            "entropy_mix": entropy_mix,
            "derivation_replayed": {**cast(Mapping[str, Any], entropy_mix["components"])},
        }

    def persist_guild_message_envelope(
        self,
        *,
        envelope: Mapping[str, Any],
        metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        envelope_obj = dict(envelope)
        now = datetime.now(timezone.utc).isoformat()
        envelope_metadata = cast(Mapping[str, Any], envelope_obj.get("metadata") or {}) if isinstance(envelope_obj.get("metadata"), Mapping) else {}
        metadata_payload = dict(metadata)
        semantic_dispatch_obj = metadata_payload.get("semantic_runtime_dispatch") or envelope_metadata.get("semantic_runtime_dispatch")
        semantic_dispatch = cast(Mapping[str, Any], semantic_dispatch_obj) if isinstance(semantic_dispatch_obj, Mapping) else {}
        relay_status = (
            self._semantic_relay_status(
                semantic_dispatch,
                remote=bool(str(envelope_obj.get("recipient_distribution_id") or "").strip()),
            )
            if semantic_dispatch
            else ("remote_pending" if str(envelope_obj.get("recipient_distribution_id") or "").strip() else "local_only")
        )
        persisted_metadata = {
            **metadata_payload,
            "relay_status": relay_status,
            "delivery_receipts": list(dict(metadata).get("delivery_receipts") or []),
        }
        if semantic_dispatch:
            persisted_metadata["semantic_runtime_dispatch"] = dict(semantic_dispatch)
        payload = {
            "envelope": envelope_obj,
            "metadata": persisted_metadata,
            "recorded_at": now,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        message_id = "gmsg_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        if self._repo is not None and hasattr(self._repo, "create_guild_message_envelope_record"):
            try:
                row = GuildMessageEnvelopeRecord(
                    message_id=message_id,
                    conversation_id=str(envelope_obj.get("conversation_id") or "") or None,
                    conversation_kind=str(envelope_obj.get("conversation_kind") or "guild_channel"),
                    guild_id=str(envelope_obj.get("guild_id") or ""),
                    channel_id=str(envelope_obj.get("channel_id") or ""),
                    thread_id=str(envelope_obj.get("thread_id") or "") or None,
                    sender_id=str(envelope_obj.get("sender_id") or ""),
                    wand_id=str(envelope_obj.get("wand_id") or ""),
                    envelope_json=json.dumps(envelope_obj, ensure_ascii=False),
                    metadata_json=json.dumps(persisted_metadata, ensure_ascii=False),
                    recorded_at=datetime.fromisoformat(now.replace("Z", "+00:00")),
                )
                self._repo.create_guild_message_envelope_record(row)
                return {
                    "message_id": message_id,
                    "recorded_at": now,
                    "guild_id": envelope_obj.get("guild_id"),
                    "channel_id": envelope_obj.get("channel_id"),
                    "thread_id": envelope_obj.get("thread_id"),
                    "relay_status": relay_status,
                    "delivery_receipts": [],
                    "semantic_storage_bucket": self._semantic_storage_bucket(semantic_dispatch) if semantic_dispatch else "database",
                    "storage_backend": "database",
                }
            except Exception:
                pass
        guild_component = self._safe_storage_component(str(envelope_obj.get("guild_id") or ""), "guild")
        channel_component = self._safe_storage_component(str(envelope_obj.get("channel_id") or ""), "channel")
        thread_component = self._safe_storage_component(str(envelope_obj.get("thread_id") or ""), "__root__")
        conversation_component = self._safe_storage_component(str(envelope_obj.get("conversation_id") or ""), "__conversation__")
        semantic_bucket = self._semantic_storage_bucket(semantic_dispatch) if semantic_dispatch else "default"
        target_dir = self._security_bucket_dir("guild_messages") / semantic_bucket / guild_component / channel_component / thread_component / conversation_component
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{message_id}.json"
        target.write_text(json.dumps({**payload, "message_id": message_id}, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "message_id": message_id,
            "conversation_id": envelope_obj.get("conversation_id"),
            "conversation_kind": envelope_obj.get("conversation_kind"),
            "recorded_at": now,
            "guild_id": envelope_obj.get("guild_id"),
            "channel_id": envelope_obj.get("channel_id"),
            "thread_id": envelope_obj.get("thread_id"),
            "relay_status": relay_status,
            "delivery_receipts": [],
            "semantic_storage_bucket": semantic_bucket,
            "storage_path": str(target.relative_to(self._security_state_dir())),
            "storage_backend": "file",
        }

    def update_guild_message_relay_status(
        self,
        *,
        message_id: str,
        relay_status: str,
        receipt: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        message_id_norm = str(message_id).strip()
        relay_status_norm = str(relay_status).strip()
        if message_id_norm == "":
            raise ValueError("message_id_required")
        if relay_status_norm == "":
            raise ValueError("relay_status_required")
        receipt_payload = dict(receipt)
        distribution_id = str(receipt_payload.get("distribution_id") or "").strip()
        signed_receipt = dict(receipt_payload)
        if distribution_id:
            signed_receipt = self._sign_distribution_receipt(
                distribution_id=distribution_id,
                message_id=message_id_norm,
                relay_status=relay_status_norm,
                receipt=receipt_payload,
            )
        if self._repo is not None and hasattr(self._repo, "get_guild_message_envelope_record") and hasattr(self._repo, "save_guild_message_envelope_record"):
            try:
                row = self._repo.get_guild_message_envelope_record(message_id_norm)
                if row is not None:
                    metadata = json.loads(row.metadata_json)
                    receipts = metadata.get("delivery_receipts")
                    if not isinstance(receipts, list):
                        receipts = []
                    receipts = [*receipts, {**signed_receipt, "recorded_at": datetime.now(timezone.utc).isoformat()}]
                    metadata["delivery_receipts"] = receipts
                    metadata["relay_status"] = relay_status_norm
                    row.metadata_json = json.dumps(metadata, ensure_ascii=False)
                    saved = self._repo.save_guild_message_envelope_record(row)
                    return {
                        "message_id": saved.message_id,
                        "relay_status": relay_status_norm,
                        "delivery_receipts": receipts,
                        "storage_backend": "database",
                    }
            except Exception:
                pass
        records = self._load_recursive_records("guild_messages")
        for record in records:
            if str(record.get("message_id") or "").strip() != message_id_norm:
                continue
            metadata = record.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            receipts = metadata.get("delivery_receipts")
            if not isinstance(receipts, list):
                receipts = []
            receipts = [*receipts, {**signed_receipt, "recorded_at": datetime.now(timezone.utc).isoformat()}]
            metadata["delivery_receipts"] = receipts
            metadata["relay_status"] = relay_status_norm
            path_str = record.get("storage_path")
            if isinstance(path_str, str) and path_str:
                target = self._security_state_dir() / path_str
            else:
                matches = list(self._security_bucket_dir("guild_messages").rglob(f"{message_id_norm}.json"))
                if not matches:
                    break
                target = matches[0]
            file_payload = json.loads(target.read_text(encoding="utf-8"))
            file_payload["metadata"] = metadata
            target.write_text(json.dumps(file_payload, indent=2, ensure_ascii=False), encoding="utf-8")
            return {
                "message_id": message_id_norm,
                "relay_status": relay_status_norm,
                "delivery_receipts": receipts,
                "storage_backend": "file",
            }
        raise ValueError("message_not_found")

    def list_guild_message_history(
        self,
        *,
        conversation_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        limit: int = 50,
    ) -> Sequence[Mapping[str, Any]]:
        if self._repo is not None and hasattr(self._repo, "list_guild_message_envelope_records"):
            try:
                rows = self._repo.list_guild_message_envelope_records(
                    conversation_id=str(conversation_id).strip() if conversation_id else None,
                    guild_id=str(guild_id).strip() if guild_id else None,
                    channel_id=str(channel_id).strip() if channel_id else None,
                    thread_id=str(thread_id).strip() if thread_id else None,
                    limit=limit,
                )
                return [
                    {
                        "message_id": row.message_id,
                        "envelope": json.loads(row.envelope_json),
                        "metadata": json.loads(row.metadata_json),
                        "recorded_at": row.recorded_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_recursive_records("guild_messages")
        if conversation_id:
            conversation_id_norm = str(conversation_id).strip()
            records = [item for item in records if str(cast(Mapping[str, Any], item.get("envelope") or {}).get("conversation_id") or "").strip() == conversation_id_norm]
        if guild_id:
            guild_id_norm = str(guild_id).strip()
            records = [item for item in records if str(cast(Mapping[str, Any], item.get("envelope") or {}).get("guild_id") or "").strip() == guild_id_norm]
        if channel_id:
            channel_id_norm = str(channel_id).strip()
            records = [item for item in records if str(cast(Mapping[str, Any], item.get("envelope") or {}).get("channel_id") or "").strip() == channel_id_norm]
        if thread_id:
            thread_id_norm = str(thread_id).strip()
            records = [item for item in records if str(cast(Mapping[str, Any], item.get("envelope") or {}).get("thread_id") or "").strip() == thread_id_norm]
        records.sort(key=lambda item: str(item.get("recorded_at") or ""), reverse=True)
        return records[: max(1, min(int(limit), 250))]

    def upsert_guild_conversation(
        self,
        *,
        conversation_id: str,
        conversation_kind: str,
        guild_id: str,
        channel_id: Optional[str],
        thread_id: Optional[str],
        title: str,
        participant_member_ids: Sequence[str],
        participant_guild_ids: Sequence[str],
        distribution_id: Optional[str],
        security_session: Mapping[str, Any],
        metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        conversation_id_norm = str(conversation_id).strip()
        guild_id_norm = str(guild_id).strip()
        if conversation_id_norm == "":
            raise ValueError("conversation_id_required")
        if guild_id_norm == "":
            raise ValueError("guild_id_required")
        conversation_kind_norm = str(conversation_kind).strip() or "guild_channel"
        participant_members = [str(item).strip() for item in participant_member_ids if str(item).strip()]
        participant_guilds = [str(item).strip() for item in participant_guild_ids if str(item).strip()]
        normalized_session = self._normalize_security_session(
            security_session=security_session,
            conversation_id=conversation_id_norm,
            conversation_kind=conversation_kind_norm,
            sender_member_id=participant_members[0] if participant_members else None,
            recipient_member_id=participant_members[1] if len(participant_members) > 1 else None,
            recipient_distribution_id=distribution_id,
        )
        now = datetime.now(timezone.utc).isoformat()
        if self._repo is not None and hasattr(self._repo, "get_guild_conversation_record") and hasattr(self._repo, "save_guild_conversation_record"):
            try:
                existing = self._repo.get_guild_conversation_record(conversation_id_norm)
                if existing is None:
                    existing = GuildConversationRecord(conversation_id=conversation_id_norm, guild_id=guild_id_norm)
                existing.conversation_kind = conversation_kind_norm
                existing.guild_id = guild_id_norm
                existing.channel_id = str(channel_id or "").strip() or None
                existing.thread_id = str(thread_id or "").strip() or None
                existing.title = str(title or "").strip()
                existing.participant_member_ids_json = json.dumps(participant_members, ensure_ascii=False)
                existing.participant_guild_ids_json = json.dumps(participant_guilds, ensure_ascii=False)
                existing.distribution_id = str(distribution_id or "").strip()
                existing.security_session_json = json.dumps(normalized_session, ensure_ascii=False)
                existing.metadata_json = json.dumps(dict(metadata), ensure_ascii=False)
                existing.updated_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
                saved = self._repo.save_guild_conversation_record(existing)
                return {
                    "conversation_id": saved.conversation_id,
                    "conversation_kind": saved.conversation_kind,
                    "guild_id": saved.guild_id,
                    "channel_id": saved.channel_id,
                    "thread_id": saved.thread_id,
                    "title": saved.title,
                    "participant_member_ids": participant_members,
                    "participant_guild_ids": participant_guilds,
                    "distribution_id": saved.distribution_id,
                    "security_session": normalized_session,
                    "metadata": dict(metadata),
                    "status": saved.status,
                    "updated_at": saved.updated_at.isoformat(),
                    "storage_backend": "database",
                }
            except Exception:
                pass
        payload = {
            "conversation_id": conversation_id_norm,
            "conversation_kind": conversation_kind_norm,
            "guild_id": guild_id_norm,
            "channel_id": str(channel_id or "").strip() or None,
            "thread_id": str(thread_id or "").strip() or None,
            "title": str(title or "").strip(),
            "participant_member_ids": participant_members,
            "participant_guild_ids": participant_guilds,
            "distribution_id": str(distribution_id or "").strip() or None,
            "security_session": normalized_session,
            "metadata": dict(metadata),
            "status": "active",
            "updated_at": now,
        }
        target = self._security_bucket_dir("guild_conversations") / f"{conversation_id_norm}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {**payload, "storage_backend": "file"}

    def get_guild_conversation(self, *, conversation_id: str) -> Mapping[str, Any]:
        conversation_id_norm = str(conversation_id).strip()
        if conversation_id_norm == "":
            raise ValueError("conversation_id_required")
        if self._repo is not None and hasattr(self._repo, "get_guild_conversation_record"):
            try:
                row = self._repo.get_guild_conversation_record(conversation_id_norm)
                if row is not None:
                    return {
                        "conversation_id": row.conversation_id,
                        "conversation_kind": row.conversation_kind,
                        "guild_id": row.guild_id,
                        "channel_id": row.channel_id,
                        "thread_id": row.thread_id,
                        "title": row.title,
                        "participant_member_ids": json.loads(row.participant_member_ids_json),
                        "participant_guild_ids": json.loads(row.participant_guild_ids_json),
                        "distribution_id": row.distribution_id or None,
                        "security_session": json.loads(row.security_session_json),
                        "metadata": json.loads(row.metadata_json),
                        "status": row.status,
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
            except Exception:
                pass
        target = self._security_bucket_dir("guild_conversations") / f"{conversation_id_norm}.json"
        if not target.exists():
            raise ValueError("conversation_not_found")
        return json.loads(target.read_text(encoding="utf-8"))

    def list_guild_conversations(
        self,
        *,
        guild_id: Optional[str] = None,
        conversation_kind: Optional[str] = None,
        participant_member_id: Optional[str] = None,
        limit: int = 50,
    ) -> Sequence[Mapping[str, Any]]:
        if self._repo is not None and hasattr(self._repo, "list_guild_conversation_records"):
            try:
                rows = self._repo.list_guild_conversation_records(
                    guild_id=str(guild_id).strip() if guild_id else None,
                    conversation_kind=str(conversation_kind).strip() if conversation_kind else None,
                    participant_member_id=str(participant_member_id).strip() if participant_member_id else None,
                    limit=limit,
                )
                return [
                    {
                        "conversation_id": row.conversation_id,
                        "conversation_kind": row.conversation_kind,
                        "guild_id": row.guild_id,
                        "channel_id": row.channel_id,
                        "thread_id": row.thread_id,
                        "title": row.title,
                        "participant_member_ids": json.loads(row.participant_member_ids_json),
                        "participant_guild_ids": json.loads(row.participant_guild_ids_json),
                        "distribution_id": row.distribution_id or None,
                        "security_session": json.loads(row.security_session_json),
                        "metadata": json.loads(row.metadata_json),
                        "status": row.status,
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_bucket_records("guild_conversations")
        if guild_id:
            guild_id_norm = str(guild_id).strip()
            records = [item for item in records if str(item.get("guild_id") or "").strip() == guild_id_norm]
        if conversation_kind:
            kind_norm = str(conversation_kind).strip()
            records = [item for item in records if str(item.get("conversation_kind") or "").strip() == kind_norm]
        if participant_member_id:
            member_norm = str(participant_member_id).strip()
            records = [
                item for item in records
                if isinstance(item.get("participant_member_ids"), list)
                and member_norm in [str(value).strip() for value in cast(Sequence[Any], item.get("participant_member_ids") or [])]
            ]
        records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return records[: max(1, min(int(limit), 250))]

    def mix_entropy(
        self,
        *,
        wand_id: str,
        wand_passkey_ward: Optional[str] = None,
        temple_entropy_digest: Optional[str] = None,
        theatre_entropy_digest: Optional[str] = None,
        attestation_media_digests: Sequence[str] = (),
        temple_entropy_source: Optional[Mapping[str, Any]] = None,
        theatre_entropy_source: Optional[Mapping[str, Any]] = None,
        attestation_sources: Sequence[Mapping[str, Any]] = (),
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        wand_id_norm = str(wand_id).strip()
        if wand_id_norm == "":
            raise ValueError("wand_id_required")
        return self._entropy_mix_runtime(
            wand_id=wand_id_norm,
            wand_passkey_ward=wand_passkey_ward,
            temple_entropy_digest=temple_entropy_digest,
            theatre_entropy_digest=theatre_entropy_digest,
            attestation_media_digests=attestation_media_digests,
            temple_entropy_source=temple_entropy_source,
            theatre_entropy_source=theatre_entropy_source,
            attestation_sources=attestation_sources,
            context=context or {},
        )

    def persist_wand_damage_attestation(
        self,
        *,
        wand_id: str,
        notifier_id: str,
        damage_state: str,
        event_tag: Optional[str],
        media: Sequence[Mapping[str, Any]],
        payload: Mapping[str, Any],
        actor_id: str,
        workshop_id: str,
    ) -> Mapping[str, Any]:
        validated = self.validate_wand_damage_attestation(
            wand_id=wand_id,
            notifier_id=notifier_id,
            damage_state=damage_state,
            event_tag=event_tag,
            media=media,
            payload=payload,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        now = datetime.now(timezone.utc).isoformat()
        normalized_media = cast(Sequence[Mapping[str, Any]], validated.get("normalized_media") or media)
        record_payload = {
            "wand_id": wand_id,
            "notifier_id": notifier_id,
            "damage_state": damage_state,
            "event_tag": event_tag,
            "media": [dict(item) for item in normalized_media],
            "payload": dict(payload),
            "validated": dict(validated),
            "actor_id": actor_id,
            "workshop_id": workshop_id,
            "recorded_at": now,
        }
        canonical = json.dumps(record_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        record_id = "watt_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        if self._repo is not None and hasattr(self._repo, "create_wand_damage_attestation_record"):
            try:
                row = WandDamageAttestationRecord(
                    record_id=record_id,
                    wand_id=str(wand_id),
                    notifier_id=str(notifier_id),
                    damage_state=str(damage_state),
                    event_tag=event_tag,
                    actor_id=str(actor_id),
                    workshop_id=str(workshop_id),
                    media_json=json.dumps([dict(item) for item in normalized_media], ensure_ascii=False),
                    payload_json=json.dumps(dict(payload), ensure_ascii=False),
                    validated_json=json.dumps(dict(validated), ensure_ascii=False),
                    recorded_at=datetime.fromisoformat(now.replace("Z", "+00:00")),
                )
                self._repo.create_wand_damage_attestation_record(row)
                return {
                    "record_id": record_id,
                    "recorded_at": now,
                    "storage_bucket": "wand_attestations",
                    "media_count": len(normalized_media),
                    "validation": validated,
                    "storage_backend": "database",
                }
            except Exception:
                pass
        target = self._security_bucket_dir("wand_attestations") / f"{record_id}.json"
        target.write_text(json.dumps({**record_payload, "record_id": record_id}, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "record_id": record_id,
            "recorded_at": now,
            "storage_bucket": "wand_attestations",
            "media_count": len(normalized_media),
            "validation": validated,
            "storage_backend": "file",
        }

    def list_wand_damage_attestations(
        self,
        *,
        wand_id: Optional[str] = None,
        limit: int = 50,
    ) -> Sequence[Mapping[str, Any]]:
        if self._repo is not None and hasattr(self._repo, "list_wand_damage_attestation_records"):
            try:
                rows = self._repo.list_wand_damage_attestation_records(
                    wand_id=str(wand_id).strip() if wand_id else None,
                    limit=limit,
                )
                return [
                    {
                        "record_id": row.record_id,
                        "wand_id": row.wand_id,
                        "notifier_id": row.notifier_id,
                        "damage_state": row.damage_state,
                        "event_tag": row.event_tag,
                        "actor_id": row.actor_id,
                        "workshop_id": row.workshop_id,
                        "media": json.loads(row.media_json),
                        "payload": json.loads(row.payload_json),
                        "validated": json.loads(row.validated_json),
                        "recorded_at": row.recorded_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_bucket_records("wand_attestations")
        if wand_id:
            wand_id_norm = str(wand_id).strip()
            records = [item for item in records if str(item.get("wand_id") or "").strip() == wand_id_norm]
        return records[: max(1, min(int(limit), 250))]

    def transition_wand_key_epoch(
        self,
        *,
        wand_id: str,
        attestation_record_id: str,
        notifier_id: str,
        previous_epoch_id: Optional[str],
        damage_state: str,
        temple_entropy_digest: Optional[str],
        theatre_entropy_digest: Optional[str],
        attestation_media_digests: Sequence[str],
        revoked: bool,
        metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        wand_id_norm = str(wand_id).strip()
        attestation_record_id_norm = str(attestation_record_id).strip()
        notifier_id_norm = str(notifier_id).strip()
        if wand_id_norm == "":
            raise ValueError("wand_id_required")
        if attestation_record_id_norm == "":
            raise ValueError("attestation_record_id_required")
        if notifier_id_norm == "":
            raise ValueError("notifier_id_required")
        history = self.list_wand_damage_attestations(wand_id=wand_id_norm, limit=250)
        matching_record = next((item for item in history if str(item.get("record_id") or "") == attestation_record_id_norm), None)
        if matching_record is None:
            raise ValueError("attestation_record_not_found")
        entropy_mix = self._entropy_mix_runtime(
            wand_id=wand_id_norm,
            temple_entropy_digest=temple_entropy_digest,
            theatre_entropy_digest=theatre_entropy_digest,
            attestation_media_digests=attestation_media_digests,
            context={
                "wand_id": wand_id_norm,
                "attestation_record_id": attestation_record_id_norm,
                "notifier_id": notifier_id_norm,
                "previous_epoch_id": previous_epoch_id or "",
                "damage_state": damage_state,
                "metadata": dict(metadata),
            },
        )
        now = datetime.now(timezone.utc).isoformat()
        epoch_payload = {
            "wand_id": wand_id_norm,
            "attestation_record_id": attestation_record_id_norm,
            "notifier_id": notifier_id_norm,
            "previous_epoch_id": previous_epoch_id,
            "damage_state": damage_state,
            "revoked": revoked,
            "entropy_mix": entropy_mix,
            "metadata": dict(metadata),
            "recorded_at": now,
        }
        epoch_canonical = json.dumps(epoch_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        epoch_id = "wep_" + hashlib.sha256(epoch_canonical.encode("utf-8")).hexdigest()[:24]
        if self._repo is not None and hasattr(self._repo, "create_wand_key_epoch_record"):
            try:
                row = WandKeyEpochRecord(
                    epoch_id=epoch_id,
                    wand_id=wand_id_norm,
                    attestation_record_id=attestation_record_id_norm,
                    notifier_id=notifier_id_norm,
                    previous_epoch_id=previous_epoch_id,
                    damage_state=damage_state,
                    revoked=revoked,
                    entropy_mix_json=json.dumps(entropy_mix, ensure_ascii=False),
                    metadata_json=json.dumps(dict(metadata), ensure_ascii=False),
                    recorded_at=datetime.fromisoformat(now.replace("Z", "+00:00")),
                )
                self._repo.create_wand_key_epoch_record(row)
                return {
                    "epoch_id": epoch_id,
                    "recorded_at": now,
                    "wand_id": wand_id_norm,
                    "attestation_record_id": attestation_record_id_norm,
                    "revoked": revoked,
                    "mix_digest": entropy_mix["mix_digest"],
                    "quality": entropy_mix["quality"],
                    "storage_backend": "database",
                }
            except Exception:
                pass
        target = self._security_bucket_dir("wand_epochs") / f"{epoch_id}.json"
        target.write_text(json.dumps({**epoch_payload, "epoch_id": epoch_id}, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "epoch_id": epoch_id,
            "recorded_at": now,
            "wand_id": wand_id_norm,
            "attestation_record_id": attestation_record_id_norm,
            "revoked": revoked,
            "mix_digest": entropy_mix["mix_digest"],
            "quality": entropy_mix["quality"],
            "storage_backend": "file",
        }

    def list_wand_key_epochs(
        self,
        *,
        wand_id: Optional[str] = None,
        limit: int = 50,
    ) -> Sequence[Mapping[str, Any]]:
        if self._repo is not None and hasattr(self._repo, "list_wand_key_epoch_records"):
            try:
                rows = self._repo.list_wand_key_epoch_records(
                    wand_id=str(wand_id).strip() if wand_id else None,
                    limit=limit,
                )
                return [
                    {
                        "epoch_id": row.epoch_id,
                        "wand_id": row.wand_id,
                        "attestation_record_id": row.attestation_record_id,
                        "notifier_id": row.notifier_id,
                        "previous_epoch_id": row.previous_epoch_id,
                        "damage_state": row.damage_state,
                        "revoked": row.revoked,
                        "entropy_mix": json.loads(row.entropy_mix_json),
                        "metadata": json.loads(row.metadata_json),
                        "recorded_at": row.recorded_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_bucket_records("wand_epochs")
        if wand_id:
            wand_id_norm = str(wand_id).strip()
            records = [item for item in records if str(item.get("wand_id") or "").strip() == wand_id_norm]
        return records[: max(1, min(int(limit), 250))]

    def get_wand_status(
        self,
        *,
        wand_id: str,
    ) -> Mapping[str, Any]:
        wand_id_norm = str(wand_id).strip()
        if wand_id_norm == "":
            raise ValueError("wand_id_required")
        attestation_history = list(self.list_wand_damage_attestations(wand_id=wand_id_norm, limit=250))
        epoch_history = list(self.list_wand_key_epochs(wand_id=wand_id_norm, limit=250))
        latest_attestation = attestation_history[0] if attestation_history else None
        latest_epoch = epoch_history[0] if epoch_history else None
        revoked = bool(latest_epoch.get("revoked")) if isinstance(latest_epoch, Mapping) else False
        return {
            "wand_id": wand_id_norm,
            "revoked": revoked,
            "status": "revoked" if revoked else "active",
            "latest_attestation": latest_attestation,
            "latest_epoch": latest_epoch,
            "attestation_count": len(attestation_history),
            "epoch_count": len(epoch_history),
        }

    def register_wand(
        self,
        *,
        wand_id: str,
        maker_id: str,
        maker_date: str,
        atelier_origin: str,
        material_profile: Mapping[str, Any],
        dimensions: Mapping[str, Any],
        structural_fingerprint: str,
        craft_record_hash: str,
        ownership_chain: Sequence[Mapping[str, Any]],
        metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        wand_id_norm = str(wand_id).strip()
        maker_id_norm = str(maker_id).strip()
        if wand_id_norm == "":
            raise ValueError("wand_id_required")
        if maker_id_norm == "":
            raise ValueError("maker_id_required")
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "wand_id": wand_id_norm,
            "maker_id": maker_id_norm,
            "maker_date": str(maker_date or "").strip(),
            "atelier_origin": str(atelier_origin or "").strip(),
            "material_profile": dict(material_profile),
            "dimensions": dict(dimensions),
            "wand_spec": {
                "maker_date": str(maker_date or "").strip(),
                "material_profile": dict(material_profile),
                "dimensions": dict(dimensions),
                "structural_fingerprint": str(structural_fingerprint or "").strip(),
                "craft_record_hash": str(craft_record_hash or "").strip(),
            },
            "structural_fingerprint": str(structural_fingerprint or "").strip(),
            "craft_record_hash": str(craft_record_hash or "").strip(),
            "ownership_chain": [dict(item) for item in ownership_chain if isinstance(item, Mapping)],
            "metadata": dict(metadata),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        if self._repo is not None and hasattr(self._repo, "get_wand_registry_record") and hasattr(self._repo, "save_wand_registry_record"):
            try:
                existing = self._repo.get_wand_registry_record(wand_id_norm)
                if existing is None:
                    existing = WandRegistryRecord(wand_id=wand_id_norm, maker_id=maker_id_norm)
                existing.maker_id = maker_id_norm
                existing.maker_date = str(maker_date or "").strip()
                existing.atelier_origin = str(atelier_origin or "").strip()
                existing.material_profile_json = json.dumps(dict(material_profile), ensure_ascii=False)
                existing.dimensions_json = json.dumps(dict(dimensions), ensure_ascii=False)
                existing.structural_fingerprint = str(structural_fingerprint or "").strip()
                existing.craft_record_hash = str(craft_record_hash or "").strip()
                existing.ownership_chain_json = json.dumps(
                    [dict(item) for item in ownership_chain if isinstance(item, Mapping)],
                    ensure_ascii=False,
                )
                existing.metadata_json = json.dumps(dict(metadata), ensure_ascii=False)
                existing.status = "active"
                existing.updated_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
                saved = self._repo.save_wand_registry_record(existing)
                return {
                    "wand_id": saved.wand_id,
                    "maker_id": saved.maker_id,
                    "maker_date": saved.maker_date,
                    "atelier_origin": saved.atelier_origin,
                    "wand_spec": {
                        "maker_date": saved.maker_date,
                        "material_profile": json.loads(saved.material_profile_json),
                        "dimensions": json.loads(saved.dimensions_json),
                        "structural_fingerprint": saved.structural_fingerprint,
                        "craft_record_hash": saved.craft_record_hash,
                    },
                    "status": saved.status,
                    "updated_at": saved.updated_at.isoformat(),
                    "storage_backend": "database",
                }
            except Exception:
                pass
        target = self._security_bucket_dir("wand_registry") / f"{wand_id_norm}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "wand_id": wand_id_norm,
            "maker_id": maker_id_norm,
            "atelier_origin": str(atelier_origin or "").strip(),
            "status": "active",
            "updated_at": now,
            "storage_backend": "file",
        }

    def get_wand_registry_entry(self, *, wand_id: str) -> Mapping[str, Any]:
        wand_id_norm = str(wand_id).strip()
        if wand_id_norm == "":
            raise ValueError("wand_id_required")
        if self._repo is not None and hasattr(self._repo, "get_wand_registry_record"):
            try:
                row = self._repo.get_wand_registry_record(wand_id_norm)
                if row is not None:
                    return {
                        "wand_id": row.wand_id,
                        "maker_id": row.maker_id,
                        "maker_date": row.maker_date,
                        "atelier_origin": row.atelier_origin,
                        "material_profile": json.loads(row.material_profile_json),
                        "dimensions": json.loads(row.dimensions_json),
                        "wand_spec": {
                            "maker_date": row.maker_date,
                            "material_profile": json.loads(row.material_profile_json),
                            "dimensions": json.loads(row.dimensions_json),
                            "structural_fingerprint": row.structural_fingerprint,
                            "craft_record_hash": row.craft_record_hash,
                        },
                        "structural_fingerprint": row.structural_fingerprint,
                        "craft_record_hash": row.craft_record_hash,
                        "ownership_chain": json.loads(row.ownership_chain_json),
                        "metadata": json.loads(row.metadata_json),
                        "status": row.status,
                        "created_at": row.created_at.isoformat(),
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
            except Exception:
                pass
        path = self._security_bucket_dir("wand_registry") / f"{wand_id_norm}.json"
        if not path.exists():
            raise ValueError("wand_not_found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("wand_not_found")
        return {**payload, "storage_backend": "file"}

    def list_wand_registry(self, *, limit: int = 50) -> Sequence[Mapping[str, Any]]:
        if self._repo is not None and hasattr(self._repo, "list_wand_registry_records"):
            try:
                rows = self._repo.list_wand_registry_records(limit=limit)
                return [
                    {
                        "wand_id": row.wand_id,
                        "maker_id": row.maker_id,
                        "maker_date": row.maker_date,
                        "atelier_origin": row.atelier_origin,
                        "wand_spec": {
                            "maker_date": row.maker_date,
                            "material_profile": json.loads(row.material_profile_json),
                            "dimensions": json.loads(row.dimensions_json),
                            "structural_fingerprint": row.structural_fingerprint,
                            "craft_record_hash": row.craft_record_hash,
                        },
                        "structural_fingerprint": row.structural_fingerprint,
                        "craft_record_hash": row.craft_record_hash,
                        "status": row.status,
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_bucket_records("wand_registry")
        return records[: max(1, min(int(limit), 250))]

    def register_guild(
        self,
        *,
        guild_id: str,
        display_name: str,
        distribution_id: str,
        owner_artisan_id: str,
        owner_profile_name: str,
        owner_profile_email: str,
        member_profiles: Sequence[Mapping[str, Any]],
        charter: Mapping[str, Any],
        metadata: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        guild_id_norm = str(guild_id).strip()
        owner_artisan_id_norm = str(owner_artisan_id).strip()
        if guild_id_norm == "":
            raise ValueError("guild_id_required")
        if owner_artisan_id_norm == "":
            raise ValueError("owner_artisan_id_required")
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "guild_id": guild_id_norm,
            "display_name": str(display_name or "").strip(),
            "distribution_id": str(distribution_id or "").strip(),
            "owner_artisan_id": owner_artisan_id_norm,
            "owner_profile_name": str(owner_profile_name or "").strip(),
            "owner_profile_email": str(owner_profile_email or "").strip(),
            "member_profiles": [dict(item) for item in member_profiles if isinstance(item, Mapping)],
            "charter": dict(charter),
            "metadata": dict(metadata),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        if self._repo is not None and hasattr(self._repo, "get_guild_registry_record") and hasattr(self._repo, "save_guild_registry_record"):
            try:
                existing = self._repo.get_guild_registry_record(guild_id_norm)
                if existing is None:
                    existing = GuildRegistryRecord(guild_id=guild_id_norm)
                existing.display_name = str(display_name or "").strip()
                existing.distribution_id = str(distribution_id or "").strip()
                existing.owner_artisan_id = owner_artisan_id_norm
                existing.owner_profile_name = str(owner_profile_name or "").strip()
                existing.owner_profile_email = str(owner_profile_email or "").strip()
                existing.member_profiles_json = json.dumps([dict(item) for item in member_profiles if isinstance(item, Mapping)], ensure_ascii=False)
                existing.charter_json = json.dumps(dict(charter), ensure_ascii=False)
                existing.metadata_json = json.dumps(dict(metadata), ensure_ascii=False)
                existing.status = "active"
                existing.updated_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
                saved = self._repo.save_guild_registry_record(existing)
                return {
                    "guild_id": saved.guild_id,
                    "display_name": saved.display_name,
                    "distribution_id": saved.distribution_id,
                    "owner_artisan_id": saved.owner_artisan_id,
                    "owner_profile_name": saved.owner_profile_name,
                    "owner_profile_email": saved.owner_profile_email,
                    "status": saved.status,
                    "updated_at": saved.updated_at.isoformat(),
                    "storage_backend": "database",
                }
            except Exception:
                pass
        target = self._security_bucket_dir("guild_registry") / f"{guild_id_norm}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "guild_id": guild_id_norm,
            "display_name": str(display_name or "").strip(),
            "distribution_id": str(distribution_id or "").strip(),
            "owner_artisan_id": owner_artisan_id_norm,
            "owner_profile_name": str(owner_profile_name or "").strip(),
            "owner_profile_email": str(owner_profile_email or "").strip(),
            "status": "active",
            "updated_at": now,
            "storage_backend": "file",
        }

    def get_guild_registry_entry(self, *, guild_id: str) -> Mapping[str, Any]:
        guild_id_norm = str(guild_id).strip()
        if guild_id_norm == "":
            raise ValueError("guild_id_required")
        if self._repo is not None and hasattr(self._repo, "get_guild_registry_record"):
            try:
                row = self._repo.get_guild_registry_record(guild_id_norm)
                if row is not None:
                    return {
                        "guild_id": row.guild_id,
                        "display_name": row.display_name,
                        "distribution_id": row.distribution_id,
                        "owner_artisan_id": row.owner_artisan_id,
                        "owner_profile_name": row.owner_profile_name,
                        "owner_profile_email": row.owner_profile_email,
                        "member_profiles": json.loads(row.member_profiles_json),
                        "charter": json.loads(row.charter_json),
                        "metadata": json.loads(row.metadata_json),
                        "status": row.status,
                        "created_at": row.created_at.isoformat(),
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
            except Exception:
                pass
        path = self._security_bucket_dir("guild_registry") / f"{guild_id_norm}.json"
        if not path.exists():
            raise ValueError("guild_not_found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("guild_not_found")
        return {**payload, "storage_backend": "file"}

    def list_guild_registry(self, *, limit: int = 50) -> Sequence[Mapping[str, Any]]:
        if self._repo is not None and hasattr(self._repo, "list_guild_registry_records"):
            try:
                rows = self._repo.list_guild_registry_records(limit=limit)
                return [
                    {
                        "guild_id": row.guild_id,
                        "display_name": row.display_name,
                        "distribution_id": row.distribution_id,
                        "owner_artisan_id": row.owner_artisan_id,
                        "owner_profile_name": row.owner_profile_name,
                        "owner_profile_email": row.owner_profile_email,
                        "charter": json.loads(row.charter_json),
                        "metadata": json.loads(row.metadata_json),
                        "status": row.status,
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_bucket_records("guild_registry")
        return records[: max(1, min(int(limit), 250))]

    def register_distribution(
        self,
        *,
        distribution_id: str,
        display_name: str,
        base_url: str,
        transport_kind: str,
        public_key_ref: str,
        protocol_family: str = _GUILD_MESSAGE_PROTOCOL_FAMILY,
        protocol_version: str = _GUILD_MESSAGE_PROTOCOL_VERSION,
        supported_protocol_versions: Sequence[str] = _GUILD_MESSAGE_SUPPORTED_PROTOCOL_VERSIONS,
        guild_ids: Sequence[str] = (),
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        distribution_id_norm = str(distribution_id).strip()
        if distribution_id_norm == "":
            raise ValueError("distribution_id_required")
        now = datetime.now(timezone.utc).isoformat()
        normalized_guild_ids = [
            str(item).strip() for item in guild_ids if str(item).strip() != ""
        ]
        protocol_family_norm = str(protocol_family or self._GUILD_MESSAGE_PROTOCOL_FAMILY).strip() or self._GUILD_MESSAGE_PROTOCOL_FAMILY
        protocol_version_norm = str(protocol_version or self._GUILD_MESSAGE_PROTOCOL_VERSION).strip() or self._GUILD_MESSAGE_PROTOCOL_VERSION
        supported_versions = [
            str(item).strip()
            for item in supported_protocol_versions
            if str(item).strip() != ""
        ]
        if protocol_version_norm not in supported_versions:
            supported_versions.append(protocol_version_norm)
        metadata_payload = dict(metadata or {})
        metadata_payload["messaging_protocol"] = {
            "family": protocol_family_norm,
            "version": protocol_version_norm,
            "supported_versions": sorted(set(supported_versions)),
        }
        payload = {
            "distribution_id": distribution_id_norm,
            "display_name": str(display_name or "").strip(),
            "base_url": str(base_url or "").strip(),
            "transport_kind": str(transport_kind or "https").strip() or "https",
            "public_key_ref": str(public_key_ref or "").strip(),
            "guild_ids": normalized_guild_ids,
            "metadata": metadata_payload,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        if self._repo is not None and hasattr(self._repo, "get_distribution_registry_record") and hasattr(self._repo, "save_distribution_registry_record"):
            try:
                existing = self._repo.get_distribution_registry_record(distribution_id_norm)
                if existing is None:
                    existing = DistributionRegistryRecord(distribution_id=distribution_id_norm)
                existing.display_name = str(display_name or "").strip()
                existing.base_url = str(base_url or "").strip()
                existing.transport_kind = str(transport_kind or "https").strip() or "https"
                existing.public_key_ref = str(public_key_ref or "").strip()
                existing.guild_ids_json = json.dumps(normalized_guild_ids, ensure_ascii=False)
                existing.metadata_json = json.dumps(metadata_payload, ensure_ascii=False)
                existing.status = "active"
                existing.updated_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
                saved = self._repo.save_distribution_registry_record(existing)
                return {
                    "distribution_id": saved.distribution_id,
                    "display_name": saved.display_name,
                    "base_url": saved.base_url,
                    "transport_kind": saved.transport_kind,
                    "public_key_ref": saved.public_key_ref,
                    "guild_ids": json.loads(saved.guild_ids_json),
                    "metadata": json.loads(saved.metadata_json),
                    "status": saved.status,
                    "updated_at": saved.updated_at.isoformat(),
                    "storage_backend": "database",
                }
            except Exception:
                pass
        target = self._security_bucket_dir("distribution_registry") / f"{distribution_id_norm}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {**payload, "storage_backend": "file"}

    def set_distribution_shop_workspace_id(
        self,
        *,
        distribution_id: str,
        shop_workspace_id: str,
        steward_id: str,
    ) -> Mapping[str, Any]:
        distribution_id_norm = str(distribution_id).strip()
        workspace_id_norm = str(shop_workspace_id).strip()
        if distribution_id_norm == "":
            raise ValueError("distribution_id_required")
        if workspace_id_norm == "":
            raise ValueError("shop_workspace_id_required")
        now = datetime.now(timezone.utc).isoformat()
        if self._repo is not None and hasattr(self._repo, "get_distribution_registry_record") and hasattr(self._repo, "save_distribution_registry_record"):
            row = self._repo.get_distribution_registry_record(distribution_id_norm)
            if row is None:
                raise ValueError("distribution_not_found")
            try:
                metadata_obj = json.loads(row.metadata_json)
            except json.JSONDecodeError:
                metadata_obj = {}
            if not isinstance(metadata_obj, dict):
                metadata_obj = {}
            metadata_obj["shop_workspace_id"] = workspace_id_norm
            metadata_obj["shop_updated_by"] = steward_id
            metadata_obj["shop_updated_at"] = now
            row.metadata_json = json.dumps(metadata_obj, ensure_ascii=False)
            row.updated_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
            saved = self._repo.save_distribution_registry_record(row)
            return {
                "distribution_id": saved.distribution_id,
                "display_name": saved.display_name,
                "base_url": saved.base_url,
                "status": saved.status,
                "metadata": json.loads(saved.metadata_json),
                "updated_at": saved.updated_at.isoformat(),
                "storage_backend": "database",
            }
        path = self._security_bucket_dir("distribution_registry") / f"{distribution_id_norm}.json"
        if not path.exists():
            raise ValueError("distribution_not_found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("distribution_not_found")
        metadata_obj = payload.get("metadata")
        metadata = dict(metadata_obj) if isinstance(metadata_obj, Mapping) else {}
        metadata["shop_workspace_id"] = workspace_id_norm
        metadata["shop_updated_by"] = steward_id
        metadata["shop_updated_at"] = now
        payload["metadata"] = metadata
        payload["updated_at"] = now
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {**payload, "storage_backend": "file"}

    def get_distribution_registry_entry(self, *, distribution_id: str) -> Mapping[str, Any]:
        distribution_id_norm = str(distribution_id).strip()
        if distribution_id_norm == "":
            raise ValueError("distribution_id_required")
        if self._repo is not None and hasattr(self._repo, "get_distribution_registry_record"):
            try:
                row = self._repo.get_distribution_registry_record(distribution_id_norm)
                if row is not None:
                    return {
                        "distribution_id": row.distribution_id,
                        "display_name": row.display_name,
                        "base_url": row.base_url,
                        "transport_kind": row.transport_kind,
                        "public_key_ref": row.public_key_ref,
                        "guild_ids": json.loads(row.guild_ids_json),
                        "metadata": json.loads(row.metadata_json),
                        "status": row.status,
                        "created_at": row.created_at.isoformat(),
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
            except Exception:
                pass
        path = self._security_bucket_dir("distribution_registry") / f"{distribution_id_norm}.json"
        if not path.exists():
            raise ValueError("distribution_not_found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("distribution_not_found")
        return {**payload, "storage_backend": "file"}

    def list_distribution_registry(self, *, limit: int = 50) -> Sequence[Mapping[str, Any]]:
        if self._repo is not None and hasattr(self._repo, "list_distribution_registry_records"):
            try:
                rows = self._repo.list_distribution_registry_records(limit=limit)
                return [
                    {
                        "distribution_id": row.distribution_id,
                        "display_name": row.display_name,
                        "base_url": row.base_url,
                        "transport_kind": row.transport_kind,
                        "public_key_ref": row.public_key_ref,
                        "guild_ids": json.loads(row.guild_ids_json),
                        "status": row.status,
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_bucket_records("distribution_registry")
        return records[: max(1, min(int(limit), 250))]

    def get_distribution_key_descriptor(self, *, distribution_id: str) -> Mapping[str, Any]:
        record = self.get_distribution_registry_entry(distribution_id=distribution_id)
        public_key_ref = str(record.get("public_key_ref") or "").strip()
        if public_key_ref == "":
            raise ValueError("recipient_distribution_key_unavailable")
        metadata_obj = record.get("metadata")
        metadata = dict(cast(Mapping[str, Any], metadata_obj)) if isinstance(metadata_obj, Mapping) else {}
        protocol_obj = metadata.get("messaging_protocol")
        protocol = dict(cast(Mapping[str, Any], protocol_obj)) if isinstance(protocol_obj, Mapping) else {
            "family": self._GUILD_MESSAGE_PROTOCOL_FAMILY,
            "version": self._GUILD_MESSAGE_PROTOCOL_VERSION,
            "supported_versions": list(self._GUILD_MESSAGE_SUPPORTED_PROTOCOL_VERSIONS),
        }
        return {
            "distribution_id": str(record.get("distribution_id") or "").strip(),
            "display_name": str(record.get("display_name") or "").strip(),
            "base_url": str(record.get("base_url") or "").strip(),
            "transport_kind": str(record.get("transport_kind") or "").strip(),
            "public_key_ref": public_key_ref,
            "messaging_protocol": protocol,
            "status": str(record.get("status") or "").strip(),
        }

    def register_distribution_handshake(
        self,
        *,
        distribution_id: str,
        local_distribution_id: str,
        remote_public_key_ref: str,
        handshake_mode: str,
        protocol_family: str = _GUILD_MESSAGE_PROTOCOL_FAMILY,
        local_protocol_version: str = _GUILD_MESSAGE_PROTOCOL_VERSION,
        remote_protocol_version: str = _GUILD_MESSAGE_PROTOCOL_VERSION,
        negotiated_protocol_version: str = _GUILD_MESSAGE_PROTOCOL_VERSION,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        record = self.get_distribution_registry_entry(distribution_id=distribution_id)
        distribution_id_norm = str(record.get("distribution_id") or "").strip()
        if distribution_id_norm == "":
            raise ValueError("distribution_id_required")
        now = datetime.now(timezone.utc).isoformat()
        resolved_remote_key = str(remote_public_key_ref or record.get("public_key_ref") or "").strip()
        if resolved_remote_key == "":
            raise ValueError("remote_public_key_ref_required")
        protocol_family_norm = str(protocol_family or self._GUILD_MESSAGE_PROTOCOL_FAMILY).strip() or self._GUILD_MESSAGE_PROTOCOL_FAMILY
        local_protocol_version_norm = str(local_protocol_version or self._GUILD_MESSAGE_PROTOCOL_VERSION).strip() or self._GUILD_MESSAGE_PROTOCOL_VERSION
        remote_protocol_version_norm = str(remote_protocol_version or self._GUILD_MESSAGE_PROTOCOL_VERSION).strip() or self._GUILD_MESSAGE_PROTOCOL_VERSION
        negotiated_protocol_version_norm = str(negotiated_protocol_version or local_protocol_version_norm).strip() or local_protocol_version_norm
        metadata_payload = dict(metadata or {})
        metadata_payload["protocol_negotiation"] = {
            "family": protocol_family_norm,
            "local_version": local_protocol_version_norm,
            "remote_version": remote_protocol_version_norm,
            "negotiated_version": negotiated_protocol_version_norm,
        }
        secret_bytes = secrets.token_bytes(32)
        secret_b64 = base64.b64encode(secret_bytes).decode("ascii")
        secret_digest = hashlib.sha256(secret_bytes).hexdigest()
        handshake_id = "dhs_" + hashlib.sha256(
            json.dumps(
                {
                    "distribution_id": distribution_id_norm,
                    "local_distribution_id": str(local_distribution_id or "").strip(),
                    "remote_public_key_ref": resolved_remote_key,
                    "handshake_mode": str(handshake_mode or "mutual_hmac").strip() or "mutual_hmac",
                    "protocol_negotiation": metadata_payload["protocol_negotiation"],
                    "secret_digest": secret_digest,
                    "metadata": metadata_payload,
                    "created_at": now,
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:24]
        payload = {
            "handshake_id": handshake_id,
            "distribution_id": distribution_id_norm,
            "local_distribution_id": str(local_distribution_id or "").strip(),
            "remote_public_key_ref": resolved_remote_key,
            "handshake_mode": str(handshake_mode or "mutual_hmac").strip() or "mutual_hmac",
            "shared_secret_b64": secret_b64,
            "shared_secret_digest": secret_digest,
            "metadata": metadata_payload,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        if self._repo is not None and hasattr(self._repo, "save_distribution_handshake_record"):
            try:
                row = DistributionHandshakeRecord(
                    handshake_id=handshake_id,
                    distribution_id=distribution_id_norm,
                    local_distribution_id=str(local_distribution_id or "").strip(),
                    remote_public_key_ref=resolved_remote_key,
                    handshake_mode=str(handshake_mode or "mutual_hmac").strip() or "mutual_hmac",
                    shared_secret_b64=secret_b64,
                    shared_secret_digest=secret_digest,
                    metadata_json=json.dumps(metadata_payload, ensure_ascii=False),
                    status="active",
                    created_at=datetime.fromisoformat(now.replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(now.replace("Z", "+00:00")),
                )
                saved = self._repo.save_distribution_handshake_record(row)
                return {
                    "handshake_id": saved.handshake_id,
                    "distribution_id": saved.distribution_id,
                    "local_distribution_id": saved.local_distribution_id,
                    "remote_public_key_ref": saved.remote_public_key_ref,
                    "handshake_mode": saved.handshake_mode,
                    "shared_secret_digest": saved.shared_secret_digest,
                    "status": saved.status,
                    "updated_at": saved.updated_at.isoformat(),
                    "storage_backend": "database",
                }
            except Exception:
                pass
        target = self._security_bucket_dir("distribution_handshakes") / f"{handshake_id}.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {k: v for k, v in {**payload, "storage_backend": "file"}.items() if k != "shared_secret_b64"}

    def list_distribution_handshakes(
        self,
        *,
        distribution_id: Optional[str] = None,
        limit: int = 50,
    ) -> Sequence[Mapping[str, Any]]:
        distribution_id_norm = str(distribution_id).strip() if distribution_id else None
        if self._repo is not None and hasattr(self._repo, "list_distribution_handshake_records"):
            try:
                rows = self._repo.list_distribution_handshake_records(
                    distribution_id=distribution_id_norm,
                    limit=limit,
                )
                return [
                    {
                        "handshake_id": row.handshake_id,
                        "distribution_id": row.distribution_id,
                        "local_distribution_id": row.local_distribution_id,
                        "remote_public_key_ref": row.remote_public_key_ref,
                        "handshake_mode": row.handshake_mode,
                        "shared_secret_digest": row.shared_secret_digest,
                        "metadata": json.loads(row.metadata_json),
                        "status": row.status,
                        "created_at": row.created_at.isoformat(),
                        "updated_at": row.updated_at.isoformat(),
                        "storage_backend": "database",
                    }
                    for row in rows
                ]
            except Exception:
                pass
        records = self._load_bucket_records("distribution_handshakes")
        if distribution_id_norm:
            records = [
                item for item in records
                if str(item.get("distribution_id") or "").strip() == distribution_id_norm
            ]
        records.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
        return [
            {k: v for k, v in record.items() if k != "shared_secret_b64"}
            for record in records[: max(1, min(int(limit), 250))]
        ]

    def discover_distribution_capabilities(self, *, distribution_id: str) -> Mapping[str, Any]:
        distribution = self.get_distribution_registry_entry(distribution_id=distribution_id)
        distribution_id_norm = str(distribution.get("distribution_id") or "").strip()
        if distribution_id_norm == "":
            raise ValueError("distribution_not_found")
        guilds = []
        for record in self.list_guild_registry(limit=250):
            if str(record.get("distribution_id") or "").strip() != distribution_id_norm:
                continue
            charter = record.get("charter")
            if not isinstance(charter, Mapping):
                charter = {}
            channels = charter.get("channels")
            if not isinstance(channels, list):
                channels = []
            guilds.append(
                {
                    "guild_id": str(record.get("guild_id") or "").strip(),
                    "display_name": str(record.get("display_name") or "").strip(),
                    "channels": [str(item).strip() for item in channels if str(item).strip() != ""],
                    "status": str(record.get("status") or "").strip(),
                }
            )
        handshake = next(iter(self.list_distribution_handshakes(distribution_id=distribution_id_norm, limit=1)), None)
        key_descriptor = self.get_distribution_key_descriptor(distribution_id=distribution_id_norm)
        protocol_summary = {
            "distribution": key_descriptor.get("messaging_protocol") or {},
            "handshake": (
                dict(cast(Mapping[str, Any], (handshake or {}).get("metadata", {})).get("protocol_negotiation") or {})
                if isinstance(handshake, Mapping)
                else {}
            ),
            "local_required": {
                "family": self._GUILD_MESSAGE_PROTOCOL_FAMILY,
                "version": self._GUILD_MESSAGE_PROTOCOL_VERSION,
                "supported_versions": list(self._GUILD_MESSAGE_SUPPORTED_PROTOCOL_VERSIONS),
            },
        }
        return {
            "distribution": distribution,
            "guilds": guilds,
            "key_descriptor": key_descriptor,
            "handshake": handshake,
            "messaging_protocol": protocol_summary,
        }

    def _ensure_distribution_protocol_compatibility(self, *, distribution_id: str) -> Mapping[str, Any]:
        capabilities = self.discover_distribution_capabilities(distribution_id=distribution_id)
        protocol_obj = capabilities.get("messaging_protocol")
        protocol_summary = dict(cast(Mapping[str, Any], protocol_obj)) if isinstance(protocol_obj, Mapping) else {}
        distribution_protocol_obj = protocol_summary.get("distribution")
        distribution_protocol = dict(cast(Mapping[str, Any], distribution_protocol_obj)) if isinstance(distribution_protocol_obj, Mapping) else {}
        handshake_protocol_obj = protocol_summary.get("handshake")
        handshake_protocol = dict(cast(Mapping[str, Any], handshake_protocol_obj)) if isinstance(handshake_protocol_obj, Mapping) else {}
        family = str(distribution_protocol.get("family") or "").strip() or self._GUILD_MESSAGE_PROTOCOL_FAMILY
        version = str(distribution_protocol.get("version") or "").strip() or self._GUILD_MESSAGE_PROTOCOL_VERSION
        supported_versions_obj = distribution_protocol.get("supported_versions")
        supported_versions = [
            str(item).strip()
            for item in cast(Sequence[Any], supported_versions_obj or [])
            if str(item).strip() != ""
        ]
        if version not in supported_versions:
            supported_versions.append(version)
        if family != self._GUILD_MESSAGE_PROTOCOL_FAMILY:
            raise ValueError("recipient_distribution_protocol_family_incompatible")
        if self._GUILD_MESSAGE_PROTOCOL_VERSION not in supported_versions:
            raise ValueError("recipient_distribution_protocol_version_unsupported")
        negotiated_version = str(handshake_protocol.get("negotiated_version") or "").strip()
        if negotiated_version and negotiated_version != self._GUILD_MESSAGE_PROTOCOL_VERSION:
            raise ValueError("recipient_distribution_handshake_protocol_incompatible")
        return {
            "distribution": distribution_protocol,
            "handshake": handshake_protocol,
        }

    def _get_distribution_handshake_secret(self, *, distribution_id: str) -> tuple[str, bytes]:
        distribution_id_norm = str(distribution_id).strip()
        if distribution_id_norm == "":
            raise ValueError("distribution_id_required")
        if self._repo is not None and hasattr(self._repo, "get_distribution_handshake_record"):
            try:
                row = self._repo.get_distribution_handshake_record(distribution_id_norm)
                if row is not None and str(row.status or "").strip() == "active":
                    return row.handshake_id, base64.b64decode(row.shared_secret_b64)
            except Exception:
                pass
        records = self._load_bucket_records("distribution_handshakes")
        for record in records:
            if str(record.get("distribution_id") or "").strip() != distribution_id_norm:
                continue
            if str(record.get("status") or "").strip() != "active":
                continue
            secret_b64 = str(record.get("shared_secret_b64") or "").strip()
            if secret_b64:
                return str(record.get("handshake_id") or "").strip(), base64.b64decode(secret_b64)
        raise ValueError("distribution_handshake_unavailable")

    def _sign_distribution_receipt(
        self,
        *,
        distribution_id: str,
        message_id: str,
        relay_status: str,
        receipt: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        handshake_id, secret = self._get_distribution_handshake_secret(distribution_id=distribution_id)
        signature_payload = {
            "distribution_id": str(distribution_id).strip(),
            "message_id": str(message_id).strip(),
            "relay_status": str(relay_status).strip(),
            "receipt": dict(receipt),
        }
        canonical = json.dumps(signature_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        signature = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            **dict(receipt),
            "signature_family": "distribution_receipt_hmac_v1",
            "handshake_id": handshake_id,
            "signature_hex": signature,
        }

    def get_migration_status(self) -> Mapping[str, Any]:
        repo_root = self._repo_root_path()
        alembic_ini = repo_root / "apps" / "atelier-api" / "alembic.ini"
        config = Config(str(alembic_ini))
        config.set_main_option("script_location", str(repo_root / "apps" / "atelier-api" / "alembic"))
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()
        return {
            "head_revision": head_revision,
            "current_revision": current_revision,
            "up_to_date": current_revision == head_revision,
            "pending": [] if current_revision == head_revision else [head_revision],
        }

    def list_contacts(self, workspace_id: str) -> Sequence[ContactOut]:
        rows = self._require_repo().list_contacts(workspace_id=workspace_id)
        return [ContactOut.model_validate(row, from_attributes=True) for row in rows]

    def create_contact(self, payload: ContactCreate) -> ContactOut:
        row = CRMContact(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            notes=payload.notes,
        )
        out = self._require_repo().create_contact(row)
        return ContactOut.model_validate(out, from_attributes=True)

    def list_bookings(self, workspace_id: str) -> Sequence[BookingOut]:
        rows = self._require_repo().list_bookings(workspace_id=workspace_id)
        return [BookingOut.model_validate(row, from_attributes=True) for row in rows]

    def create_booking(self, payload: BookingCreate) -> BookingOut:
        row = Booking(
            workspace_id=payload.workspace_id,
            contact_id=payload.contact_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            status=payload.status,
            notes=payload.notes,
        )
        out = self._require_repo().create_booking(row)
        return BookingOut.model_validate(out, from_attributes=True)

    def list_lessons(self, workspace_id: str) -> Sequence[LessonOut]:
        rows = self._require_repo().list_lessons(workspace_id=workspace_id)
        return [LessonOut.model_validate(row, from_attributes=True) for row in rows]

    def create_lesson(self, payload: LessonCreate) -> LessonOut:
        row = Lesson(
            workspace_id=payload.workspace_id,
            title=payload.title,
            body=payload.body,
            status=payload.status,
        )
        out = self._require_repo().create_lesson(row)
        return LessonOut.model_validate(out, from_attributes=True)

    def list_lesson_progress(self, workspace_id: str, actor_id: str) -> Sequence[LessonProgressOut]:
        rows = self._require_repo().list_lesson_progress(workspace_id=workspace_id, actor_id=actor_id)
        return [LessonProgressOut.model_validate(row, from_attributes=True) for row in rows]

    def consume_lesson(self, payload: LessonConsumeInput) -> LessonProgressOut:
        repo = self._require_repo()
        row = repo.get_lesson_progress(payload.workspace_id, payload.actor_id, payload.lesson_id)
        now = datetime.now(timezone.utc)
        if row is None:
            row = LessonProgress(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                lesson_id=payload.lesson_id,
                status=payload.status,
                completed_at=now if payload.status == "consumed" else None,
                updated_at=now,
            )
        else:
            row.status = payload.status
            if payload.status == "consumed" and row.completed_at is None:
                row.completed_at = now
            row.updated_at = now
        saved = repo.save_lesson_progress(row)
        return LessonProgressOut.model_validate(saved, from_attributes=True)

    def list_modules(self, workspace_id: str) -> Sequence[ModuleOut]:
        rows = self._require_repo().list_modules(workspace_id=workspace_id)
        return [ModuleOut.model_validate(row, from_attributes=True) for row in rows]

    def create_module(self, payload: ModuleCreate) -> ModuleOut:
        row = LearningModule(
            workspace_id=payload.workspace_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
        )
        out = self._require_repo().create_module(row)
        return ModuleOut.model_validate(out, from_attributes=True)

    def list_leads(self, workspace_id: str) -> Sequence[LeadOut]:
        rows = self._require_repo().list_leads(workspace_id=workspace_id)
        return [LeadOut.model_validate(row, from_attributes=True) for row in rows]

    def create_lead(self, payload: LeadCreate) -> LeadOut:
        row = Lead(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            details=payload.details,
            status=payload.status,
            source=payload.source,
        )
        out = self._require_repo().create_lead(row)
        return LeadOut.model_validate(out, from_attributes=True)

    def list_clients(self, workspace_id: str) -> Sequence[ClientOut]:
        rows = self._require_repo().list_clients(workspace_id=workspace_id)
        return [ClientOut.model_validate(row, from_attributes=True) for row in rows]

    def create_client(self, payload: ClientCreate) -> ClientOut:
        row = Client(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            status=payload.status,
        )
        out = self._require_repo().create_client(row)
        return ClientOut.model_validate(out, from_attributes=True)

    def list_quotes(self, workspace_id: str) -> Sequence[QuoteOut]:
        rows = self._require_repo().list_quotes(workspace_id=workspace_id)
        return [QuoteOut.model_validate(row, from_attributes=True) for row in rows]

    def create_quote(self, payload: QuoteCreate) -> QuoteOut:
        row = Quote(
            workspace_id=payload.workspace_id,
            lead_id=payload.lead_id,
            client_id=payload.client_id,
            title=payload.title,
            amount_cents=payload.amount_cents,
            currency=payload.currency,
            status=payload.status,
            is_public=payload.is_public,
            notes=payload.notes,
        )
        out = self._require_repo().create_quote(row)
        return QuoteOut.model_validate(out, from_attributes=True)

    def list_orders(self, workspace_id: str) -> Sequence[OrderOut]:
        rows = self._require_repo().list_orders(workspace_id=workspace_id)
        return [OrderOut.model_validate(row, from_attributes=True) for row in rows]

    def create_order(self, payload: OrderCreate) -> OrderOut:
        row = Order(
            workspace_id=payload.workspace_id,
            quote_id=payload.quote_id,
            client_id=payload.client_id,
            title=payload.title,
            amount_cents=payload.amount_cents,
            currency=payload.currency,
            status=payload.status,
            notes=payload.notes,
        )
        out = self._require_repo().create_order(row)
        return OrderOut.model_validate(out, from_attributes=True)

    def list_contracts(self, workspace_id: str) -> Sequence[ContractOut]:
        rows = self._require_repo().list_contracts(workspace_id=workspace_id)
        return [ContractOut.model_validate(row, from_attributes=True) for row in rows]

    def create_contract(self, payload: ContractCreate) -> ContractOut:
        now = datetime.utcnow()
        row = Contract(
            workspace_id=payload.workspace_id,
            title=payload.title,
            category=payload.category,
            party_name=payload.party_name,
            party_email=payload.party_email,
            party_phone=payload.party_phone,
            artisan_id=payload.artisan_id,
            amount_cents=payload.amount_cents,
            currency=payload.currency,
            status="draft",
            terms=payload.terms,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        out = self._require_repo().create_contract(row)
        return ContractOut.model_validate(out, from_attributes=True)

    def update_contract(self, *, workspace_id: str, contract_id: str, payload: ContractUpdate) -> ContractOut:
        repo = self._require_repo()
        row = repo.get_contract(workspace_id=workspace_id, contract_id=contract_id)
        if row is None:
            raise ValueError("contract_not_found")
        if payload.title is not None:
            row.title = payload.title
        if payload.category is not None:
            row.category = payload.category
        if payload.party_name is not None:
            row.party_name = payload.party_name
        if payload.party_email is not None:
            row.party_email = payload.party_email
        if payload.party_phone is not None:
            row.party_phone = payload.party_phone
        if payload.artisan_id is not None:
            row.artisan_id = payload.artisan_id
        if payload.amount_cents is not None:
            row.amount_cents = payload.amount_cents
        if payload.currency is not None:
            row.currency = payload.currency
        if payload.terms is not None:
            row.terms = payload.terms
        if payload.notes is not None:
            row.notes = payload.notes
        row.updated_at = datetime.utcnow()
        saved = repo.update_contract(row)
        return ContractOut.model_validate(saved, from_attributes=True)

    def validate_contract(self, *, workspace_id: str, contract_id: str) -> ContractOut:
        repo = self._require_repo()
        row = repo.get_contract(workspace_id=workspace_id, contract_id=contract_id)
        if row is None:
            raise ValueError("contract_not_found")
        if row.status == "cancelled":
            raise ValueError("contract_cancelled")
        if row.status == "processed":
            raise ValueError("contract_processed")
        row.status = "validated"
        row.validated_at = datetime.utcnow()
        row.updated_at = row.validated_at
        saved = repo.update_contract(row)
        return ContractOut.model_validate(saved, from_attributes=True)

    def cancel_contract(self, *, workspace_id: str, contract_id: str) -> ContractOut:
        repo = self._require_repo()
        row = repo.get_contract(workspace_id=workspace_id, contract_id=contract_id)
        if row is None:
            raise ValueError("contract_not_found")
        if row.status == "processed":
            raise ValueError("contract_processed")
        row.status = "cancelled"
        row.cancelled_at = datetime.utcnow()
        row.updated_at = row.cancelled_at
        saved = repo.update_contract(row)
        return ContractOut.model_validate(saved, from_attributes=True)

    def process_contract(self, *, workspace_id: str, contract_id: str) -> ContractOut:
        repo = self._require_repo()
        row = repo.get_contract(workspace_id=workspace_id, contract_id=contract_id)
        if row is None:
            raise ValueError("contract_not_found")
        if row.status != "validated":
            raise ValueError("contract_not_validated")
        row.status = "processed"
        row.processed_at = datetime.utcnow()
        row.updated_at = row.processed_at
        saved = repo.update_contract(row)
        return ContractOut.model_validate(saved, from_attributes=True)

    def list_ledger_entries(
        self,
        workspace_id: str,
        account_type: str | None = None,
        owner_id: str | None = None,
    ) -> Sequence[LedgerEntryOut]:
        rows = self._require_repo().list_ledger_entries(
            workspace_id=workspace_id,
            account_type=account_type,
            owner_id=owner_id,
        )
        outputs: list[LedgerEntryOut] = []
        for row in rows:
            outputs.append(
                LedgerEntryOut(
                    id=row.id,
                    workspace_id=row.workspace_id,
                    account_type=row.account_type,
                    owner_id=row.owner_id,
                    amount_cents=row.amount_cents,
                    currency=row.currency,
                    section_id=row.section_id,
                    reference_type=row.reference_type,
                    reference_id=row.reference_id,
                    metadata=_safe_parse_json(row.metadata_json),
                    created_at=row.created_at,
                )
            )
        return outputs

    def summarize_artisan_payouts(
        self,
        workspace_id: str,
        month: str,
    ) -> dict[str, object]:
        payables = self._require_repo().list_ledger_entries(
            workspace_id=workspace_id,
            account_type="artisan_payable",
            owner_id=None,
        )
        payouts = self._require_repo().list_ledger_entries(
            workspace_id=workspace_id,
            account_type="artisan_payout",
            owner_id=None,
        )
        by_owner: dict[str, dict[str, int]] = {}
        for row in payables:
            created = row.created_at
            if created.strftime("%Y-%m") != month:
                continue
            owner = row.owner_id or "unassigned"
            record = by_owner.setdefault(owner, {"payable_cents": 0, "paid_cents": 0})
            record["payable_cents"] += int(row.amount_cents)
        for row in payouts:
            created = row.created_at
            if created.strftime("%Y-%m") != month:
                continue
            owner = row.owner_id or "unassigned"
            record = by_owner.setdefault(owner, {"payable_cents": 0, "paid_cents": 0})
            record["paid_cents"] += int(row.amount_cents)
        results = []
        for owner, record in by_owner.items():
            remaining = max(0, record["payable_cents"] - record["paid_cents"])
            results.append(
                {
                    "artisan_id": owner,
                    "payable_cents": record["payable_cents"],
                    "paid_cents": record["paid_cents"],
                    "remaining_cents": remaining,
                }
            )
        return {"month": month, "currency": "USD", "payouts": results}

    def run_monthly_payouts(
        self,
        workspace_id: str,
        month: str,
        *,
        dry_run: bool = False,
    ) -> dict[str, object]:
        summary = self.summarize_artisan_payouts(workspace_id=workspace_id, month=month)
        payouts = summary.get("payouts", [])
        created_entries: list[LedgerEntry] = []
        if not dry_run and isinstance(payouts, list):
            for payout in payouts:
                if not isinstance(payout, dict):
                    continue
                artisan_id = str(payout.get("artisan_id") or "unassigned")
                remaining = int(payout.get("remaining_cents") or 0)
                if remaining <= 0:
                    continue
                created_entries.append(
                    LedgerEntry(
                        workspace_id=workspace_id,
                        account_type="artisan_payout",
                        owner_id=artisan_id,
                        amount_cents=remaining,
                        currency="USD",
                        section_id=None,
                        reference_type="monthly_payout",
                        reference_id=f"{month}:{artisan_id}",
                        metadata_json=json.dumps({"month": month}),
                    )
                )
            if created_entries:
                self._require_repo().create_ledger_entries(created_entries)
        summary["payout_created"] = len(created_entries)
        summary["dry_run"] = dry_run
        return summary

    def record_shop_sale_ledger(
        self,
        *,
        workspace_id: str,
        section_id: str,
        artisan_id: str | None,
        currency: str,
        gross_cents: int,
        fee_cents: int,
        tax_cents: int,
        commission_cents: int,
        net_cents: int,
        reference_type: str,
        reference_id: str,
        metadata: dict[str, object],
    ) -> Sequence[LedgerEntryOut]:
        if self._require_repo().ledger_reference_exists(reference_id):
            return []
        net_after_tax = max(0, net_cents - tax_cents)
        artisan_due = max(0, net_after_tax - commission_cents)
        entries = [
            LedgerEntry(
                workspace_id=workspace_id,
                account_type="platform_cash",
                owner_id=None,
                amount_cents=max(0, net_cents),
                currency=currency,
                section_id=section_id,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata_json=json.dumps({"gross_cents": gross_cents, **metadata}),
            ),
            LedgerEntry(
                workspace_id=workspace_id,
                account_type="processor_fees",
                owner_id=None,
                amount_cents=max(0, fee_cents),
                currency=currency,
                section_id=section_id,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata_json=json.dumps(metadata),
            ),
            LedgerEntry(
                workspace_id=workspace_id,
                account_type="tax_liability",
                owner_id=None,
                amount_cents=max(0, tax_cents),
                currency=currency,
                section_id=section_id,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata_json=json.dumps(metadata),
            ),
            LedgerEntry(
                workspace_id=workspace_id,
                account_type="platform_revenue",
                owner_id=None,
                amount_cents=max(0, commission_cents),
                currency=currency,
                section_id=section_id,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata_json=json.dumps(metadata),
            ),
            LedgerEntry(
                workspace_id=workspace_id,
                account_type="artisan_payable",
                owner_id=artisan_id,
                amount_cents=max(0, artisan_due),
                currency=currency,
                section_id=section_id,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata_json=json.dumps(metadata),
            ),
        ]
        created = self._require_repo().create_ledger_entries(entries)
        return [
            LedgerEntryOut(
                id=row.id,
                workspace_id=row.workspace_id,
                account_type=row.account_type,
                owner_id=row.owner_id,
                amount_cents=row.amount_cents,
                currency=row.currency,
                section_id=row.section_id,
                reference_type=row.reference_type,
                reference_id=row.reference_id,
                metadata=_safe_parse_json(row.metadata_json),
                created_at=row.created_at,
            )
            for row in created
        ]

    def list_inventory_items(self, workspace_id: str) -> Sequence[InventoryItemOut]:
        rows = self._require_repo().list_inventory_items(workspace_id=workspace_id)
        return [InventoryItemOut.model_validate(row, from_attributes=True) for row in rows]

    def create_inventory_item(self, payload: InventoryItemCreate) -> InventoryItemOut:
        row = InventoryItem(
            workspace_id=payload.workspace_id,
            sku=payload.sku,
            name=payload.name,
            quantity_on_hand=payload.quantity_on_hand,
            reorder_level=payload.reorder_level,
            unit_cost_cents=payload.unit_cost_cents,
            currency=payload.currency,
            supplier_id=payload.supplier_id,
            notes=payload.notes,
        )
        out = self._require_repo().create_inventory_item(row)
        return InventoryItemOut.model_validate(out, from_attributes=True)

    def adjust_inventory_item(self, payload: InventoryAdjustInput) -> InventoryItemOut:
        repo = self._require_repo()
        row = repo.get_inventory_item(payload.workspace_id, payload.inventory_item_id)
        if row is None:
            raise ValueError("inventory_item_not_found")
        row.quantity_on_hand = row.quantity_on_hand + payload.delta
        saved = repo.update_inventory_item(row)
        return InventoryItemOut.model_validate(saved, from_attributes=True)

    def emit_headless_quest(
        self,
        *,
        payload: HeadlessQuestEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> HeadlessQuestEmitOut:
        emitted_step_ids: list[str] = []
        for step in payload.steps:
            context: dict[str, object] = {
                "workspace_id": payload.workspace_id,
                "quest_id": payload.quest_id,
                "step_id": step.step_id,
                "headless": True,
            }
            if payload.scene_id is not None:
                context["scene_id"] = payload.scene_id
            if step.context:
                context["step_context"] = dict(step.context)
            self._kernel.place(
                raw=step.raw,
                context=context,
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
            emitted_step_ids.append(step.step_id)
        return HeadlessQuestEmitOut(
            quest_id=payload.quest_id,
            emitted=len(emitted_step_ids),
            emitted_step_ids=emitted_step_ids,
        )

    def emit_meditation(
        self,
        *,
        payload: MeditationEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> MeditationEmitOut:
        raw = f"meditation.session {payload.session_id} phase={payload.phase} duration={payload.duration_seconds}"
        context: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "session_id": payload.session_id,
            "phase": payload.phase,
            "duration_seconds": payload.duration_seconds,
            "tags": dict(payload.tags),
            "headless": True,
        }
        self._kernel.place(
            raw=raw,
            context=context,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return MeditationEmitOut(session_id=payload.session_id, emitted=1, phase=payload.phase)

    def emit_scene_graph(
        self,
        *,
        payload: SceneGraphEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> SceneGraphEmitOut:
        realm_error = validate_scene_realm(payload.scene_id, payload.realm_id)
        if realm_error:
            raise ValueError(realm_error)
        sorted_nodes = sorted(payload.nodes, key=lambda node: node.node_id)
        sorted_edges = sorted(payload.edges, key=lambda edge: (edge.from_node_id, edge.to_node_id, edge.relation))
        for node in sorted_nodes:
            raw = f"scene.node {payload.scene_id} {node.node_id} {node.kind} {node.x} {node.y}"
            context: dict[str, object] = {
                "workspace_id": payload.workspace_id,
                "realm_id": payload.realm_id,
                "scene_id": payload.scene_id,
                "node_id": node.node_id,
                "metadata": dict(node.metadata),
            }
            self._kernel.place(raw=raw, context=context, actor_id=actor_id, workshop_id=workshop_id)
        for edge in sorted_edges:
            raw = f"scene.edge {payload.scene_id} {edge.from_node_id} {edge.to_node_id} {edge.relation}"
            context = {
                "workspace_id": payload.workspace_id,
                "realm_id": payload.realm_id,
                "scene_id": payload.scene_id,
                "from_node_id": edge.from_node_id,
                "to_node_id": edge.to_node_id,
                "relation": edge.relation,
                "metadata": dict(edge.metadata),
            }
            self._kernel.place(raw=raw, context=context, actor_id=actor_id, workshop_id=workshop_id)
        return SceneGraphEmitOut(
            scene_id=payload.scene_id,
            nodes_emitted=len(sorted_nodes),
            edges_emitted=len(sorted_edges),
        )

    def export_save_snapshot(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
    ) -> SaveExportOut:
        timeline = list(self._kernel.timeline(actor_id=actor_id, workshop_id=workshop_id))
        frontiers = list(self._kernel.frontiers(actor_id=actor_id, workshop_id=workshop_id))
        observe = self._kernel.observe(actor_id=actor_id, workshop_id=workshop_id)
        payload: dict[str, object] = {
            "workspace_id": workspace_id,
            "clock": observe.get("clock", {}),
            "frontiers": frontiers,
            "timeline": timeline,
            "candidates_by_frontier": observe.get("candidates_by_frontier", {}),
            "eligible_by_frontier": observe.get("eligible_by_frontier", {}),
            "refusals": observe.get("refusals", []),
        }
        return SaveExportOut(
            workspace_id=workspace_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            timeline_count=len(timeline),
            frontier_count=len(frontiers),
            hash=self._canonical_hash(payload),
            payload=payload,
        )

    def _player_state_to_tables(self, row: PlayerState) -> PlayerStateTables:
        return PlayerStateTables(
            levels=self._json_to_object_map(row.levels_json),
            skills=self._json_to_object_map(row.skills_json),
            perks=self._json_to_object_map(row.perks_json),
            vitriol=self._json_to_object_map(row.vitriol_json),
            inventory=self._json_to_object_map(row.inventory_json),
            market=self._json_to_object_map(row.market_json),
            flags=self._json_to_object_map(row.flags_json),
            clock=self._json_to_object_map(row.clock_json),
        )

    def _ensure_player_state(self, workspace_id: str, actor_id: str) -> PlayerState:
        repo = self._require_repo()
        row = repo.get_player_state(workspace_id, actor_id)
        if row is not None:
            return row
        defaults = self._default_player_tables()
        row = PlayerState(
            workspace_id=workspace_id,
            actor_id=actor_id,
            state_version=1,
            levels_json=self._canonical_json(defaults.levels),
            skills_json=self._canonical_json(defaults.skills),
            perks_json=self._canonical_json(defaults.perks),
            vitriol_json=self._canonical_json(defaults.vitriol),
            inventory_json=self._canonical_json(defaults.inventory),
            market_json=self._canonical_json(defaults.market),
            flags_json=self._canonical_json(defaults.flags),
            clock_json=self._canonical_json(defaults.clock),
        )
        return repo.save_player_state(row)

    def get_player_state(
        self,
        *,
        workspace_id: str,
        actor_id: str,
    ) -> PlayerStateOut:
        row = self._ensure_player_state(workspace_id, actor_id)
        tables = self._player_state_to_tables(row)
        hash_payload: dict[str, object] = {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "state_version": row.state_version,
            "tables": tables.model_dump(),
        }
        return PlayerStateOut(
            workspace_id=workspace_id,
            actor_id=actor_id,
            state_version=row.state_version,
            generated_at=datetime.now(timezone.utc).isoformat(),
            hash=self._canonical_hash(hash_payload),
            tables=tables,
        )

    def apply_player_state(
        self,
        *,
        payload: PlayerStateApplyInput,
        actor_id: str,
        workshop_id: str,
    ) -> PlayerStateOut:
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        current = self._player_state_to_tables(row)
        if payload.mode == "replace":
            next_tables = payload.tables
        else:
            next_tables = self._merge_player_tables(current, payload.tables)
        row.state_version = max(1, int(row.state_version) + 1)
        row.levels_json = self._canonical_json(next_tables.levels)
        row.skills_json = self._canonical_json(next_tables.skills)
        row.perks_json = self._canonical_json(next_tables.perks)
        row.vitriol_json = self._canonical_json(next_tables.vitriol)
        row.inventory_json = self._canonical_json(next_tables.inventory)
        row.market_json = self._canonical_json(next_tables.market)
        row.flags_json = self._canonical_json(next_tables.flags)
        row.clock_json = self._canonical_json(next_tables.clock)
        row.updated_at = datetime.now(timezone.utc)
        repo.save_player_state(row)

        self._kernel.place(
            raw=f"game.state.apply {payload.actor_id} mode={payload.mode}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "player_state_apply",
                "state_version": row.state_version,
                "tables": next_tables.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "state_version": row.state_version,
            "tables": next_tables.model_dump(),
        }
        return PlayerStateOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            state_version=row.state_version,
            generated_at=datetime.now(timezone.utc).isoformat(),
            hash=self._canonical_hash(hash_payload),
            tables=next_tables,
        )

    @staticmethod
    def _int_from_table(value: object, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _list_from_table(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    @staticmethod
    def _dict_from_table(value: object) -> dict[str, object]:
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _list_of_dicts(value: object) -> list[dict[str, object]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    def _event_payload_with_defaults(
        self,
        payload: Mapping[str, object],
        workspace_id: str,
        actor_id: str,
    ) -> dict[str, object]:
        merged = dict(payload)
        merged.setdefault("workspace_id", workspace_id)
        merged.setdefault("actor_id", actor_id)
        return merged

    def _apply_game_event(
        self,
        *,
        event: GameEventInput,
        tables: PlayerStateTables,
        workspace_id: str,
        actor_id: str,
        workshop_id: str,
    ) -> tuple[PlayerStateTables, GameTickEventResult]:
        kind = event.kind.strip().lower()
        payload = self._event_payload_with_defaults(event.payload, workspace_id, actor_id)
        updated_tables = tables
        try:
            if kind == "levels.apply":
                current_level = self._int_from_table(tables.levels.get("current_level"), 1)
                current_xp = self._int_from_table(tables.levels.get("current_xp"), 0)
                payload.setdefault("current_level", current_level)
                payload.setdefault("current_xp", current_xp)
                level_payload = LevelApplyInput.model_validate(payload)
                result = self.apply_level_progress(
                    payload=level_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                levels = dict(tables.levels)
                levels["current_level"] = result.level_after
                levels["current_xp"] = result.xp_after
                levels["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "levels": levels})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "skills.train":
                ranks = self._dict_from_table(tables.skills.get("ranks"))
                skill_id = self._canonical_skill_id(str(payload.get("skill_id") or ""))
                payload["skill_id"] = skill_id
                payload.setdefault("current_rank", self._int_from_table(ranks.get(skill_id, 0), 0))
                payload.setdefault("points_available", self._int_from_table(tables.skills.get("points_available"), 0))
                skill_payload = SkillTrainInput.model_validate(payload)
                result = self.train_skill(
                    payload=skill_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                ranks[result.skill_id] = result.rank_after
                skills = dict(tables.skills)
                skills["ranks"] = ranks
                skills["points_available"] = result.points_remaining
                skills["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "skills": skills})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "perks.unlock":
                unlocked = self._list_from_table(tables.perks.get("unlocked"))
                payload.setdefault("unlocked_perks", unlocked)
                payload.setdefault("actor_level", self._int_from_table(tables.levels.get("current_level"), 1))
                payload.setdefault("actor_skills", self._dict_from_table(tables.skills.get("ranks")))
                perk_payload = PerkUnlockInput.model_validate(payload)
                result = self.unlock_perk(
                    payload=perk_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                perks = dict(tables.perks)
                perks["unlocked"] = result.unlocked_perks
                perks["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "perks": perks})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "alchemy.craft":
                inventory = self._dict_from_table(tables.inventory.get("items"))
                payload.setdefault("inventory", inventory)
                alchemy_payload = AlchemyCraftInput.model_validate(payload)
                result = self.craft_alchemy(
                    payload=alchemy_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                inv = dict(tables.inventory)
                inv["items"] = result.inventory_after
                alchemy = dict(tables.alchemy)
                alchemy["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inv, "alchemy": alchemy})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "alchemy.interface":
                alchemy_payload = AlchemyInterfaceInput.model_validate(payload)
                result = self.build_alchemy_interface(
                    payload=alchemy_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                alchemy = dict(tables.alchemy)
                alchemy["interface"] = result.interface
                alchemy["constraints"] = result.render_constraints
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "alchemy": alchemy})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "alchemy.crystal":
                inventory = self._dict_from_table(tables.inventory.get("items"))
                payload.setdefault("inventory", inventory)
                flags = self._dict_from_table(tables.flags)
                payload.setdefault("infernal_meditation", bool(flags.get("infernal_meditation")))
                payload.setdefault("vitriol_trials_cleared", bool(flags.get("vitriol_trials_cleared")))
                crystal_payload = AlchemyCrystalInput.model_validate(payload)
                result = self.craft_alchemy_crystal(
                    payload=crystal_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                inv = dict(tables.inventory)
                inv["items"] = result.inventory_after
                alchemy = dict(tables.alchemy)
                alchemy["last_crystal"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inv, "alchemy": alchemy})
                if result.key_flags:
                    flags = dict(updated_tables.flags)
                    flags.update(result.key_flags)
                    updated_tables = PlayerStateTables(**{**updated_tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=result.crafted, detail=result.reason, payload=result.model_dump())
            if kind == "blacksmith.forge":
                inventory = self._dict_from_table(tables.inventory.get("items"))
                payload.setdefault("inventory", inventory)
                forge_payload = BlacksmithForgeInput.model_validate(payload)
                result = self.forge_blacksmith(
                    payload=forge_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                inv = dict(tables.inventory)
                inv["items"] = result.inventory_after
                blacksmith = dict(tables.blacksmith)
                blacksmith["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inv, "blacksmith": blacksmith})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "market.quote":
                quote_payload = MarketQuoteInput.model_validate(payload)
                result = self.market_quote(
                    payload=quote_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                market = dict(tables.market)
                market["last_quote"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "market": market})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "market.trade":
                market_inv = self._dict_from_table(tables.market.get("inventory"))
                payload.setdefault("wallet_cents", self._int_from_table(tables.market.get("wallet_cents"), 0))
                payload.setdefault("inventory_qty", self._int_from_table(market_inv.get(str(payload.get("item_id") or "")), 0))
                payload.setdefault("available_liquidity", self._int_from_table(tables.market.get("available_liquidity"), 0))
                trade_payload = MarketTradeInput.model_validate(payload)
                result = self.market_trade(
                    payload=trade_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                market = dict(tables.market)
                market_inv = dict(market_inv)
                market_inv[result.item_id] = result.inventory_after_qty
                market["inventory"] = market_inv
                market["wallet_cents"] = result.wallet_after_cents
                market["last_trade"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "market": market})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.status, payload=result.model_dump())
            if kind == "radio.evaluate":
                radio_payload = RadioEvaluateInput.model_validate(payload)
                result = self.evaluate_radio_availability(
                    payload=radio_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                flags = dict(tables.flags)
                flags.update(result.flags)
                flags["last_radio"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail=result.reason, payload=result.model_dump())
            if kind == "infernal_meditation.unlock":
                unlock_payload = InfernalMeditationUnlockInput.model_validate(payload)
                result = self.unlock_infernal_meditation(
                    payload=unlock_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                flags = dict(tables.flags)
                flags.update(result.flags)
                flags["last_infernal_meditation"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=result.unlocked, detail=result.reason, payload=result.model_dump())
            if kind == "vitriol.apply":
                payload.setdefault("base", self._dict_from_table(tables.vitriol.get("base")))
                payload.setdefault("modifiers", self._list_of_dicts(tables.vitriol.get("modifiers")))
                vitriol_payload = VitriolApplyRulerInfluenceInput.model_validate(payload)
                result = self.vitriol_apply_ruler_influence(
                    payload=vitriol_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                vitriol = dict(tables.vitriol)
                vitriol["effective"] = result.effective
                vitriol["modifiers"] = [item.model_dump() for item in result.active_modifiers]
                vitriol["base"] = vitriol_payload.base
                vitriol["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "vitriol": vitriol})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "vitriol.compute":
                payload.setdefault("base", self._dict_from_table(tables.vitriol.get("base")))
                payload.setdefault("modifiers", self._list_of_dicts(tables.vitriol.get("modifiers")))
                vitriol_payload = VitriolComputeInput.model_validate(payload)
                result = self.vitriol_compute(payload=vitriol_payload)
                vitriol = dict(tables.vitriol)
                vitriol["effective"] = result.effective
                vitriol["modifiers"] = [item.model_dump() for item in result.active_modifiers]
                vitriol["base"] = vitriol_payload.base
                vitriol["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "vitriol": vitriol})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "vitriol.clear":
                payload.setdefault("base", self._dict_from_table(tables.vitriol.get("base")))
                payload.setdefault("modifiers", self._list_of_dicts(tables.vitriol.get("modifiers")))
                vitriol_payload = VitriolClearExpiredInput.model_validate(payload)
                result = self.vitriol_clear_expired(
                    payload=vitriol_payload,
                    actor_id=actor_id,
                    workshop_id=workshop_id,
                    emit_kernel=False,
                )
                vitriol = dict(tables.vitriol)
                vitriol["effective"] = result.effective
                vitriol["modifiers"] = [item.model_dump() for item in result.active_modifiers]
                vitriol["base"] = vitriol_payload.base
                vitriol["last"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "vitriol": vitriol})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "inventory.adjust":
                item_id = str(payload.get("item_id") or "")
                delta = self._int_from_table(payload.get("delta"), 0)
                inventory = dict(tables.inventory)
                items = dict(self._dict_from_table(inventory.get("items")))
                items[item_id] = self._int_from_table(items.get(item_id, 0), 0) + delta
                inventory["items"] = items
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "inventory": inventory})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload={"item_id": item_id, "delta": delta})
            if kind == "flags.set":
                key = str(payload.get("key") or "")
                value = bool(payload.get("value"))
                flags = dict(tables.flags)
                flags[key] = value
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload={"key": key, "value": value})
            if kind == "math.numeral_3d":
                numeral_payload = Numeral3DInput.model_validate(payload)
                result = self.compute_numeral_3d(payload=numeral_payload, actor_id=actor_id)
                flags = dict(tables.flags)
                flags["math_numeral_3d"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
            if kind == "math.fibonacci_ordering":
                fib_payload = FibonacciOrderingInput.model_validate(payload)
                result = self.compute_fibonacci_ordering(payload=fib_payload, actor_id=actor_id)
                flags = dict(tables.flags)
                flags["math_fibonacci_ordering"] = result.model_dump()
                updated_tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
                return updated_tables, GameTickEventResult(kind=event.kind, ok=True, detail="ok", payload=result.model_dump())
        except Exception as exc:
            return tables, GameTickEventResult(kind=event.kind, ok=False, detail=str(exc), payload=dict(payload))
        return tables, GameTickEventResult(kind=event.kind, ok=False, detail="unsupported_event", payload=dict(payload))

    def game_tick(
        self,
        *,
        payload: GameTickInput,
        actor_id: str,
        workshop_id: str,
    ) -> GameTickOut:
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        tables = self._player_state_to_tables(row)
        updated_tables = tables
        clock = dict(updated_tables.clock)
        tick_before = self._int_from_table(clock.get("tick"), 0)
        tick_after = tick_before + 1

        raw_queue = self._list_of_dicts(clock.get("event_queue"))
        normalized_queue: list[dict[str, object]] = []
        next_seq = self._int_from_table(clock.get("next_event_seq"), 1)
        for item in raw_queue:
            kind = str(item.get("kind") or "").strip()
            if kind == "":
                continue
            payload_obj = item.get("payload")
            queue_payload = payload_obj if isinstance(payload_obj, dict) else {}
            event_id = str(item.get("event_id") or "")
            due_tick = self._int_from_table(item.get("due_tick"), tick_after)
            seq = self._int_from_table(item.get("seq"), next_seq)
            next_seq = max(next_seq, seq + 1)
            normalized_queue.append(
                {
                    "event_id": event_id,
                    "kind": kind,
                    "due_tick": due_tick,
                    "seq": seq,
                    "payload": queue_payload,
                }
            )

        for event in payload.events:
            due_tick = event.due_tick if event.due_tick is not None else tick_after
            normalized_queue.append(
                {
                    "event_id": event.event_id,
                    "kind": event.kind,
                    "due_tick": int(due_tick),
                    "seq": next_seq,
                    "payload": dict(event.payload),
                }
            )
            next_seq += 1

        due_events = [item for item in normalized_queue if self._int_from_table(item.get("due_tick"), tick_after) <= tick_after]
        pending_events = [item for item in normalized_queue if self._int_from_table(item.get("due_tick"), tick_after) > tick_after]
        due_events.sort(
            key=lambda item: (
                self._int_from_table(item.get("due_tick"), tick_after),
                self._int_from_table(item.get("seq"), 0),
                str(item.get("kind") or ""),
                self._canonical_hash(item.get("payload", {})),
                str(item.get("event_id") or ""),
            )
        )

        results: list[GameTickEventResult] = []
        for queued in due_events:
            runtime_event = GameEventInput(
                event_id=str(queued.get("event_id") or ""),
                kind=str(queued.get("kind") or ""),
                due_tick=self._int_from_table(queued.get("due_tick"), tick_after),
                payload=cast(dict[str, object], queued.get("payload", {})),
            )
            updated_tables, result = self._apply_game_event(
                event=runtime_event,
                tables=updated_tables,
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                workshop_id=workshop_id,
            )
            results.append(
                result.model_copy(
                    update={
                        "event_id": runtime_event.event_id,
                        "due_tick": runtime_event.due_tick,
                        "sequence": self._int_from_table(queued.get("seq"), 0),
                    }
                )
            )

        clock = dict(updated_tables.clock)
        clock["tick"] = tick_after
        clock["dt_ms"] = max(0, int(payload.dt_ms))
        clock["next_event_seq"] = next_seq
        clock["event_queue"] = [
            {
                "event_id": str(item.get("event_id") or ""),
                "kind": str(item.get("kind") or ""),
                "due_tick": self._int_from_table(item.get("due_tick"), tick_after),
                "seq": self._int_from_table(item.get("seq"), 0),
                "payload": cast(dict[str, object], item.get("payload", {})),
            }
            for item in sorted(
                pending_events,
                key=lambda item: (
                    self._int_from_table(item.get("due_tick"), tick_after),
                    self._int_from_table(item.get("seq"), 0),
                ),
            )
        ]
        clock["last_processed_count"] = len(due_events)
        clock["last_queued_count"] = len(pending_events)
        updated_tables = PlayerStateTables(**{**updated_tables.model_dump(), "clock": clock})
        row.state_version = max(1, int(row.state_version) + 1)
        row.levels_json = self._canonical_json(updated_tables.levels)
        row.skills_json = self._canonical_json(updated_tables.skills)
        row.perks_json = self._canonical_json(updated_tables.perks)
        row.vitriol_json = self._canonical_json(updated_tables.vitriol)
        row.inventory_json = self._canonical_json(updated_tables.inventory)
        row.market_json = self._canonical_json(updated_tables.market)
        row.flags_json = self._canonical_json(updated_tables.flags)
        row.clock_json = self._canonical_json(updated_tables.clock)
        row.updated_at = datetime.now(timezone.utc)
        repo.save_player_state(row)

        self._kernel.place(
            raw=f"game.state.tick {payload.actor_id} events={len(payload.events)}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "game_tick",
                "state_version": row.state_version,
                "tick": clock["tick"],
                "results": [item.model_dump() for item in results],
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "state_version": row.state_version,
            "tick": clock["tick"],
            "dt_ms": payload.dt_ms,
            "results": [item.model_dump() for item in results],
            "tables": updated_tables.model_dump(),
        }
        return GameTickOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            state_version=row.state_version,
            tick=clock["tick"],
            dt_ms=payload.dt_ms,
            applied=sum(1 for item in results if item.ok),
            processed_count=len(due_events),
            queued_count=len(pending_events),
            queue_size=len(pending_events),
            results=results,
            hash=self._canonical_hash(hash_payload),
            tables=updated_tables,
        )

    def apply_level_progress(
        self,
        *,
        payload: LevelApplyInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> LevelApplyOut:
        level_before = max(1, payload.current_level)
        xp = max(0, payload.current_xp) + max(0, payload.gained_xp)
        level = level_before

        def xp_needed(target_level: int) -> int:
            return max(1, payload.xp_curve_base + ((target_level - 1) * payload.xp_curve_scale))

        gained_levels = 0
        while xp >= xp_needed(level):
            xp -= xp_needed(level)
            level += 1
            gained_levels += 1

        result = LevelApplyOut(
            actor_id=payload.actor_id,
            level_before=level_before,
            level_after=level,
            xp_after=xp,
            leveled_up=gained_levels > 0,
            levels_gained=gained_levels,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.level.apply {payload.actor_id} +xp={payload.gained_xp}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "level_progress",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def train_skill(
        self,
        *,
        payload: SkillTrainInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> SkillTrainOut:
        skill_id = self._canonical_skill_id(payload.skill_id)
        rank_before = max(0, payload.current_rank)
        points = max(0, payload.points_available)
        max_rank = max(1, payload.max_rank)
        trained = points > 0 and rank_before < max_rank
        rank_after = rank_before + 1 if trained else rank_before
        points_after = points - 1 if trained else points
        result = SkillTrainOut(
            actor_id=payload.actor_id,
            skill_id=skill_id,
            rank_before=rank_before,
            rank_after=rank_after,
            points_remaining=points_after,
            trained=trained,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.skill.train {payload.actor_id} {skill_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "skill_train",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def unlock_perk(
        self,
        *,
        payload: PerkUnlockInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> PerkUnlockOut:
        unlocked_set = set(payload.unlocked_perks)
        if payload.perk_id in unlocked_set:
            result = PerkUnlockOut(
                actor_id=payload.actor_id,
                perk_id=payload.perk_id,
                unlocked=False,
                reason="already_unlocked",
                unlocked_perks=sorted(unlocked_set),
            )
        elif payload.actor_level < payload.required_level:
            result = PerkUnlockOut(
                actor_id=payload.actor_id,
                perk_id=payload.perk_id,
                unlocked=False,
                reason="level_requirement_not_met",
                unlocked_perks=sorted(unlocked_set),
            )
        else:
            missing = [
                skill_id
                for skill_id, required_rank in payload.required_skills.items()
                if payload.actor_skills.get(skill_id, 0) < required_rank
            ]
            if missing:
                result = PerkUnlockOut(
                    actor_id=payload.actor_id,
                    perk_id=payload.perk_id,
                    unlocked=False,
                    reason="skill_requirement_not_met",
                    unlocked_perks=sorted(unlocked_set),
                )
            else:
                unlocked_set.add(payload.perk_id)
                result = PerkUnlockOut(
                    actor_id=payload.actor_id,
                    perk_id=payload.perk_id,
                    unlocked=True,
                    reason="ok",
                    unlocked_perks=sorted(unlocked_set),
                )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.perk.unlock {payload.actor_id} {payload.perk_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "perk_unlock",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _apply_recipe(
        *,
        inventory: Mapping[str, int],
        consume: Mapping[str, int],
        produce: Mapping[str, int],
    ) -> tuple[bool, str, dict[str, int]]:
        next_inventory: dict[str, int] = {key: max(0, int(value)) for key, value in inventory.items()}
        for key, needed in consume.items():
            required = max(0, int(needed))
            if next_inventory.get(key, 0) < required:
                return False, f"missing:{key}", next_inventory
        for key, needed in consume.items():
            required = max(0, int(needed))
            next_inventory[key] = max(0, next_inventory.get(key, 0) - required)
        for key, amount in produce.items():
            gain = max(0, int(amount))
            next_inventory[key] = next_inventory.get(key, 0) + gain
        return True, "ok", next_inventory

    def craft_alchemy(
        self,
        *,
        payload: AlchemyCraftInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> AlchemyCraftOut:
        crafted, reason, inventory_after = self._apply_recipe(
            inventory=payload.inventory,
            consume=payload.ingredients,
            produce=payload.outputs,
        )
        result = AlchemyCraftOut(
            actor_id=payload.actor_id,
            recipe_id=payload.recipe_id,
            crafted=crafted,
            reason=reason,
            inventory_after=inventory_after,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.alchemy.craft {payload.actor_id} {payload.recipe_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "alchemy_craft",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _asmodian_ring_for_purity(purity: int) -> tuple[str, int]:
        rings = ["Pride", "Greed", "Gluttony", "Envy", "Sloth", "Wrath", "Lust"]
        normalized = max(0, min(100, int(purity)))
        idx = round((normalized / 100) * (len(rings) - 1))
        return rings[idx], idx

    def craft_alchemy_crystal(
        self,
        *,
        payload: AlchemyCrystalInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> AlchemyCrystalOut:
        crafted, reason, inventory_after = self._apply_recipe(
            inventory=payload.inventory,
            consume=payload.ingredients,
            produce=payload.outputs,
        )
        purity = max(0, min(100, int(payload.purity)))
        crystal_type = str(payload.crystal_type or "").strip().lower()
        key_flags: dict[str, object] = {}
        infernal_meditation = bool(payload.infernal_meditation)
        vitriol_trials_cleared = bool(payload.vitriol_trials_cleared)
        if crafted:
            if crystal_type == "radio":
                key_flags = {
                    "radio_key": True,
                    "radio_crystal_purity": purity,
                    "overworld_key": True,
                }
            elif crystal_type == "asmodian":
                ring, ring_index = self._asmodian_ring_for_purity(purity)
                key_flags = {
                    "asmodian_key": True,
                    "asmodian_crystal_purity": purity,
                    "underworld_ring": ring,
                    "underworld_ring_index": ring_index,
                    "underworld_visitors_access": infernal_meditation,
                    "underworld_royalty_access": vitriol_trials_cleared,
                }
            else:
                reason = "unknown_crystal_type"
                crafted = False
        result = AlchemyCrystalOut(
            actor_id=payload.actor_id,
            crystal_type=crystal_type,
            purity=purity,
            crafted=crafted,
            reason=reason,
            inventory_after=inventory_after,
            key_flags=key_flags,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.alchemy.crystal {payload.actor_id} {crystal_type}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "alchemy_crystal",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def build_alchemy_interface(
        self,
        *,
        payload: AlchemyInterfaceInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> AlchemyInterfaceOut:
        from qqva.shygazun_compiler import compile_akinenwun_to_ir, derive_render_constraints

        ir = compile_akinenwun_to_ir(payload.akinenwun)
        constraints = derive_render_constraints(ir)
        interface = constraints.get("alchemy_interface", {})
        result = AlchemyInterfaceOut(
            actor_id=payload.actor_id,
            akinenwun=payload.akinenwun,
            interface=cast(dict[str, object], interface),
            render_constraints=cast(dict[str, object], constraints),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.alchemy.interface {payload.actor_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "alchemy_interface",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def forge_blacksmith(
        self,
        *,
        payload: BlacksmithForgeInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> BlacksmithForgeOut:
        forged, reason, inventory_after = self._apply_recipe(
            inventory=payload.inventory,
            consume=payload.materials,
            produce=payload.outputs,
        )
        durability = 0
        if forged:
            durability = max(1, sum(max(0, int(v)) for v in payload.materials.values()) + payload.durability_bonus)
        result = BlacksmithForgeOut(
            actor_id=payload.actor_id,
            blueprint_id=payload.blueprint_id,
            forged=forged,
            reason=reason,
            durability_score=durability,
            inventory_after=inventory_after,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.blacksmith.forge {payload.actor_id} {payload.blueprint_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "blacksmith_forge",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def resolve_combat(
        self,
        *,
        payload: CombatResolveInput,
        actor_id: str,
        workshop_id: str,
    ) -> CombatResolveOut:
        base_attack = max(0, payload.attacker.attack)
        base_defense = max(0, payload.defender.defense)
        damage = max(0, base_attack - base_defense)
        defender_hp_after = max(0, payload.defender.hp - damage)
        result = CombatResolveOut(
            actor_id=payload.actor_id,
            round_id=payload.round_id,
            damage=damage,
            defender_hp_after=defender_hp_after,
            defender_defeated=defender_hp_after == 0,
        )
        self._kernel.place(
            raw=f"game.combat.resolve {payload.actor_id} {payload.round_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "combat_resolve",
                "attacker_id": payload.attacker.id,
                "defender_id": payload.defender.id,
                "result": result.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return result

    def market_quote(
        self,
        *,
        payload: MarketQuoteInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> MarketQuoteOut:
        market = get_realm_market(payload.realm_id)
        coin = get_realm_coin(payload.realm_id)
        quantity = max(0, payload.quantity)
        base = max(1, payload.base_price_cents)
        scarcity_multiplier_bp = 10000 + payload.scarcity_bp + market.volatility_bp
        spread_bp = max(0, payload.spread_bp + market.spread_bp)
        side_adjust_bp = spread_bp if payload.side.lower() == "buy" else -spread_bp
        effective_bp = max(1, scarcity_multiplier_bp + side_adjust_bp)
        unit_price = max(1, (base * effective_bp) // 10000)
        subtotal = unit_price * quantity
        stock_available = max(0, int(market.stock.get(payload.item_id, 0)))
        result = MarketQuoteOut(
            actor_id=payload.actor_id,
            realm_id=market.realm_id,
            market_id=market.market_id,
            currency_code=coin.currency_code,
            currency_name=coin.currency_name,
            currency_backing=coin.backing,
            item_id=payload.item_id,
            side=payload.side.lower(),
            quantity=quantity,
            stock_available=stock_available,
            market_volatility_bp=market.volatility_bp,
            unit_price_cents=unit_price,
            subtotal_cents=subtotal,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.market.quote {payload.actor_id} {payload.item_id} {payload.side}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "market_quote",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def market_trade(
        self,
        *,
        payload: MarketTradeInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> MarketTradeOut:
        market = get_realm_market(payload.realm_id)
        coin = get_realm_coin(payload.realm_id)
        side = payload.side.lower()
        requested_qty = max(0, payload.quantity)
        stock_available = max(0, int(market.stock.get(payload.item_id, 0)))
        liquidity = max(0, min(payload.available_liquidity, stock_available))
        filled_qty = min(requested_qty, liquidity)
        unit_price = max(1, payload.unit_price_cents)
        subtotal = filled_qty * unit_price
        fee_bp = max(0, payload.fee_bp + market.fee_bp)
        fee_cents = (subtotal * fee_bp) // 10000
        total_cents = subtotal + fee_cents

        wallet = payload.wallet_cents
        inventory = payload.inventory_qty
        status = "filled" if filled_qty == requested_qty else "partial"

        if side == "buy":
            affordable_qty = filled_qty
            if total_cents > wallet and unit_price > 0:
                per_unit_total = unit_price + ((unit_price * fee_bp) // 10000)
                if per_unit_total > 0:
                    affordable_qty = wallet // per_unit_total
            filled_qty = max(0, min(filled_qty, affordable_qty))
            subtotal = filled_qty * unit_price
            fee_cents = (subtotal * fee_bp) // 10000
            total_cents = subtotal + fee_cents
            wallet_after = wallet - total_cents
            inventory_after = inventory + filled_qty
            if filled_qty == 0:
                status = "rejected_insufficient_funds"
            elif filled_qty < requested_qty:
                status = "partial"
        else:
            sellable = max(0, inventory)
            filled_qty = max(0, min(filled_qty, sellable))
            subtotal = filled_qty * unit_price
            fee_cents = (subtotal * fee_bp) // 10000
            total_cents = subtotal - fee_cents
            wallet_after = wallet + total_cents
            inventory_after = inventory - filled_qty
            if filled_qty == 0:
                status = "rejected_insufficient_inventory"
            elif filled_qty < requested_qty:
                status = "partial"

        result = MarketTradeOut(
            actor_id=payload.actor_id,
            realm_id=market.realm_id,
            market_id=market.market_id,
            currency_code=coin.currency_code,
            currency_name=coin.currency_name,
            currency_backing=coin.backing,
            item_id=payload.item_id,
            side=side,
            requested_qty=requested_qty,
            filled_qty=filled_qty,
            stock_available=stock_available,
            market_volatility_bp=market.volatility_bp,
            unit_price_cents=unit_price,
            subtotal_cents=subtotal,
            fee_cents=fee_cents,
            total_cents=total_cents,
            wallet_after_cents=wallet_after,
            inventory_after_qty=inventory_after,
            status=status,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.market.trade {payload.actor_id} {payload.item_id} {side}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "market_trade",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def list_realm_coins(self, realm_id: str | None = None) -> Sequence[RealmCoinOut]:
        return [
            RealmCoinOut(
                realm_id=item.realm_id,
                currency_code=item.currency_code,
                currency_name=item.currency_name,
                backing=item.backing,
            )
            for item in list_realm_coins(realm_id)
        ]

    def list_realm_markets(self, realm_id: str | None = None) -> Sequence[RealmMarketOut]:
        return [
            RealmMarketOut(
                realm_id=item.realm_id,
                market_id=item.market_id,
                display_name=item.display_name,
                dominant_operator=item.dominant_operator,
                market_network=item.market_network,
                dominance_bp=item.dominance_bp,
                volatility_bp=item.volatility_bp,
                spread_bp=item.spread_bp,
                fee_bp=item.fee_bp,
                stock={key: int(value) for key, value in item.stock.items()},
            )
            for item in list_realm_markets(realm_id)
        ]

    def evaluate_radio_availability(
        self,
        *,
        payload: RadioEvaluateInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> RadioEvaluateOut:
        state = str(payload.underworld_state or "").strip().lower()
        override = payload.override_available
        if override is not None:
            available = bool(override)
            reason = "override"
        else:
            if state in {"open", "active", "unstable", "awakened"}:
                available = True
                reason = "state_allows_radio"
            elif state in {"sealed", "silent", "collapsed", "dormant", "closed"}:
                available = False
                reason = "state_blocks_radio"
            else:
                available = False
                reason = "unknown_state"
        flags = {
            "radio_available": available,
            "underworld_state": state,
        }
        result = RadioEvaluateOut(
            actor_id=payload.actor_id,
            underworld_state=state,
            available=available,
            reason=reason,
            flags=flags,
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.radio.evaluate {payload.actor_id} {state}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "radio_evaluate",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def unlock_infernal_meditation(
        self,
        *,
        payload: InfernalMeditationUnlockInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> InfernalMeditationUnlockOut:
        mentor = str(payload.mentor or "").strip().lower()
        location = str(payload.location or "").strip().lower()
        section = str(payload.section or "").strip().lower()
        time_of_day = str(payload.time_of_day or "").strip().lower()
        ok = (
            mentor == "alfir"
            and location == "castle azoth library"
            and section == "restricted"
            and time_of_day == "night"
        )
        reason = "ok" if ok else "conditions_not_met"
        flags = {
            "infernal_meditation": ok,
            "infernal_meditation_mentor": mentor,
            "infernal_meditation_location": location,
            "infernal_meditation_section": section,
            "infernal_meditation_time": time_of_day,
        }
        result = InfernalMeditationUnlockOut(actor_id=payload.actor_id, unlocked=ok, reason=reason, flags=flags)
        if emit_kernel:
            self._kernel.place(
                raw=f"game.infernal_meditation.unlock {payload.actor_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "infernal_meditation_unlock",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _gate_expected_value(requirement: GateRequirement) -> int | str | bool | None:
        if requirement.int_value is not None:
            return int(requirement.int_value)
        if requirement.str_value is not None:
            return requirement.str_value
        if requirement.bool_value is not None:
            return bool(requirement.bool_value)
        return None

    @staticmethod
    def _gate_actual_value(payload: GateEvaluateInput, requirement: GateRequirement) -> int | str | bool | None:
        source = requirement.source
        key = requirement.key
        if source == "skills":
            return int(payload.state.skills.get(key, 0))
        if source == "inventory":
            return int(payload.state.inventory.get(key, 0))
        if source == "vitriol":
            return int(payload.state.vitriol.get(key, 0))
        if source == "chaos":
            return int(payload.state.chaos.get(key, 0))
        if source == "order":
            return int(payload.state.order.get(key, 0))
        if source == "sanity":
            return int(payload.state.sanity.get(key, 0))
        if source == "factions":
            return int(payload.state.factions.get(key, 0))
        if source == "underworld":
            return int(payload.state.underworld.get(key, 0))
        if source == "affiliations":
            return key in payload.state.affiliations
        if source == "flags":
            return bool(payload.state.flags.get(key, False))
        if source == "dialogue_flags":
            return key in payload.state.dialogue_flags
        if source == "akashic_memory":
            return key in payload.state.akashic_memory
        if source == "void_mark":
            return key in payload.state.void_mark
        return key in payload.state.previous_dialogue

    @classmethod
    def _evaluate_gate_requirement(cls, payload: GateEvaluateInput, requirement: GateRequirement) -> GateRequirementResult:
        actual = cls._gate_actual_value(payload, requirement)
        expected = cls._gate_expected_value(requirement)
        matched = False
        reason = "not_matched"
        if requirement.comparator == "gte":
            if not isinstance(actual, int):
                reason = "invalid_actual_type_for_gte"
            elif requirement.int_value is None:
                reason = "missing_int_value"
            else:
                matched = actual >= requirement.int_value
                reason = "ok" if matched else "below_threshold"
        elif requirement.comparator == "eq":
            if expected is None:
                reason = "missing_expected_value"
            else:
                matched = actual == expected
                reason = "ok" if matched else "not_equal"
        else:
            expected_present = requirement.bool_value if requirement.bool_value is not None else True
            actual_present = bool(actual)
            matched = actual_present == expected_present
            expected = expected_present
            actual = actual_present
            reason = "ok" if matched else "presence_mismatch"
        return GateRequirementResult(
            source=requirement.source,
            key=requirement.key,
            comparator=requirement.comparator,
            matched=matched,
            actual=actual,
            expected=expected,
            reason=reason,
        )

    @staticmethod
    def _combine_gate_results(operator: GateOperator, result_flags: Sequence[bool]) -> bool:
        if operator == "and":
            return all(result_flags)
        if operator == "or":
            return any(result_flags)
        if operator == "xor":
            return sum(1 for value in result_flags if value) == 1
        return not any(result_flags)

    def evaluate_gate(
        self,
        *,
        payload: GateEvaluateInput,
        actor_id: str,
        workshop_id: str,
    ) -> GateEvaluateOut:
        requirement_results = [self._evaluate_gate_requirement(payload, requirement) for requirement in payload.requirements]
        result_flags = [item.matched for item in requirement_results]
        allowed = self._combine_gate_results(payload.operator, result_flags)
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "gate_id": payload.gate_id,
            "operator": payload.operator,
            "state": payload.state.model_dump(),
            "requirements": [item.model_dump() for item in payload.requirements],
            "results": [item.model_dump() for item in requirement_results],
            "allowed": allowed,
        }
        result = GateEvaluateOut(
            actor_id=payload.actor_id,
            gate_id=payload.gate_id,
            operator=payload.operator,
            allowed=allowed,
            matched_count=sum(1 for value in result_flags if value),
            total_count=len(result_flags),
            results=requirement_results,
            hash=self._canonical_hash(hash_payload),
        )
        self._kernel.place(
            raw=f"game.gate.evaluate {payload.actor_id} {payload.gate_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "gate_evaluate",
                "result": result.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return result

    @classmethod
    def _gate_state_from_tables(cls, tables: PlayerStateTables) -> GateStateInput:
        skills_obj = cls._dict_from_table(tables.skills.get("ranks"))
        if not skills_obj:
            skills_obj = cls._dict_from_table(tables.skills)
        skills: dict[str, int] = {
            key: cls._int_from_table(value, 0)
            for key, value in skills_obj.items()
        }

        inventory_obj = cls._dict_from_table(tables.inventory.get("items"))
        if not inventory_obj:
            inventory_obj = cls._dict_from_table(tables.inventory)
        inventory: dict[str, int] = {
            key: cls._int_from_table(value, 0)
            for key, value in inventory_obj.items()
        }

        vitriol_obj = cls._dict_from_table(tables.vitriol.get("effective"))
        if not vitriol_obj:
            vitriol_obj = cls._dict_from_table(tables.vitriol.get("base"))
        vitriol: dict[str, int] = {
            key: cls._int_from_table(value, 0)
            for key, value in vitriol_obj.items()
        }

        flags_obj = cls._dict_from_table(tables.flags)
        dialogue_flags = cls._list_from_table(flags_obj.get("dialogue_flags"))
        previous_dialogue = cls._list_from_table(flags_obj.get("previous_dialogue"))
        bool_flags: dict[str, bool] = {
            key: bool(value)
            for key, value in flags_obj.items()
            if isinstance(key, str) and isinstance(value, bool)
        }
        breath_obj = cls._dict_from_table(flags_obj.get("breath_ko"))
        chaos: dict[str, int] = {
            "meter": cls._int_from_table(breath_obj.get("chaos_meter"), 0),
            "kd_ratio_milli": cls._int_from_table(breath_obj.get("kd_ratio_milli"), 0),
            "kills": cls._int_from_table(breath_obj.get("kills"), 0),
        }
        order: dict[str, int] = {
            "meter": max(0, min(100, 100 - chaos["meter"])),
            "deaths": cls._int_from_table(breath_obj.get("deaths"), 0),
        }
        akashic_memory = cls._list_from_table(flags_obj.get("akashic_memory"))
        akashic_seed = str(breath_obj.get("akashic_memory_seed", "")).strip()
        if akashic_seed != "":
            akashic_memory = sorted(set([*akashic_memory, akashic_seed]))
        void_mark = cls._list_from_table(flags_obj.get("void_mark"))
        void_hash = str(breath_obj.get("void_body_mark_hash", "")).strip()
        if void_hash != "":
            void_mark = sorted(set([*void_mark, void_hash]))
        sanity_obj = cls._dict_from_table(flags_obj.get("sanity"))
        sanity: dict[str, int] = {
            key: max(0, min(100, cls._int_from_table(sanity_obj.get(key), 50)))
            for key in cls._SANITY_KEYS
        }
        factions_obj = cls._dict_from_table(flags_obj.get("factions"))
        factions: dict[str, int] = {
            key: max(0, min(100, cls._int_from_table(value, 0)))
            for key, value in factions_obj.items()
            if isinstance(key, str)
        }
        underworld_obj = cls._dict_from_table(flags_obj.get("underworld_access"))
        underworld: dict[str, int] = {
            "infernal_meditation": 1 if bool(underworld_obj.get("infernal_meditation")) else 0,
            "visitors_unlocked": 1 if bool(underworld_obj.get("visitors_unlocked")) else 0,
            "royalty_unlocked": 1 if bool(underworld_obj.get("royalty_unlocked")) else 0,
            "asmodian_purity": max(0, min(100, cls._int_from_table(underworld_obj.get("asmodian_purity"), 0))),
            "asmodian_ring_index": max(0, min(6, cls._int_from_table(underworld_obj.get("asmodian_ring_index"), 0))),
        }
        affiliations = cls._list_from_table(flags_obj.get("affiliations"))

        return GateStateInput(
            skills=skills,
            inventory=inventory,
            vitriol=vitriol,
            dialogue_flags=dialogue_flags,
            previous_dialogue=previous_dialogue,
            flags=bool_flags,
            chaos=chaos,
            order=order,
            akashic_memory=akashic_memory,
            void_mark=void_mark,
            sanity=sanity,
            factions=factions,
            underworld=underworld,
            affiliations=affiliations,
        )

    @classmethod
    def _extract_sanity_from_flags(cls, flags_obj: Mapping[str, object]) -> dict[str, int]:
        sanity_obj = cls._dict_from_table(flags_obj.get("sanity"))
        return {
            key: max(0, min(100, cls._int_from_table(sanity_obj.get(key), 50)))
            for key in cls._SANITY_KEYS
        }

    @classmethod
    def _apply_sanity_adjustment(
        cls,
        *,
        current: Mapping[str, int],
        delta: Mapping[str, object] | None = None,
        set_values: Mapping[str, object] | None = None,
    ) -> dict[str, int]:
        next_values = {key: max(0, min(100, int(current.get(key, 50)))) for key in cls._SANITY_KEYS}
        if delta is not None:
            for key in cls._SANITY_KEYS:
                if key in delta:
                    next_values[key] = max(0, min(100, next_values[key] + cls._int_from_table(delta.get(key), 0)))
        if set_values is not None:
            for key in cls._SANITY_KEYS:
                if key in set_values:
                    next_values[key] = max(0, min(100, cls._int_from_table(set_values.get(key), next_values[key])))
        return next_values

    @classmethod
    def _evaluate_underworld_access(
        cls,
        *,
        infernal_meditation: bool,
        vitriol_trials_cleared: bool,
        asmodian_purity: int,
    ) -> dict[str, object]:
        purity = max(0, min(100, int(asmodian_purity)))
        ring_index = min(6, max(0, (purity * 7) // 101))
        asmodian_entry_ring = cls._UNDERWORLD_RING_ORDER[ring_index]
        visitors_unlocked = bool(infernal_meditation)
        royalty_unlocked = bool(vitriol_trials_cleared)
        return {
            "infernal_meditation": bool(infernal_meditation),
            "vitriol_trials_cleared": bool(vitriol_trials_cleared),
            "asmodian_purity": purity,
            "asmodian_ring_index": ring_index,
            "asmodian_entry_ring": asmodian_entry_ring,
            "visitors_unlocked": visitors_unlocked,
            "royalty_unlocked": royalty_unlocked,
            "accessible_rings": (
                ["visitors", "royalty"] if visitors_unlocked and royalty_unlocked else
                ["visitors"] if visitors_unlocked else []
            ),
        }

    @classmethod
    def _normalize_affiliations(
        cls,
        *,
        fae_kind: str,
        social_class: str,
        realm_bindings: Sequence[object],
    ) -> dict[str, object]:
        fae = fae_kind.strip().lower()
        if fae != "" and fae not in cls._FAE_KINDS:
            raise ValueError("invalid_fae_kind")
        social = social_class.strip().lower()
        if social != "" and social not in cls._SOCIAL_CLASSES:
            raise ValueError("invalid_social_class")
        realms = sorted(
            {
                str(item).strip().lower()
                for item in realm_bindings
                if str(item).strip().lower() in cls._REALM_IDS
            }
        )
        if fae != "" and "mercurie" not in realms:
            raise ValueError("fae_require_mercurie_binding")
        if social == "assassins":
            required = {"lapidus", "mercurie"}
            if not required.issubset(set(realms)):
                raise ValueError("assassins_require_lapidus_and_mercurie_binding")
        affiliations: list[str] = []
        if fae != "":
            affiliations.append(f"fae:{fae}")
        if social != "":
            affiliations.append(f"class:{social}")
        for realm in realms:
            affiliations.append(f"realm:{realm}")
        return {
            "fae_kind": fae,
            "social_class": social,
            "realm_bindings": realms,
            "affiliations": affiliations,
        }

    def resolve_dialogue_branch(
        self,
        *,
        payload: DialogueResolveInput,
        actor_id: str,
        workshop_id: str,
    ) -> DialogueResolveOut:
        state_source: str
        if payload.state is not None:
            state = payload.state
            state_source = "payload"
        else:
            tables = self.get_player_state(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
            ).tables
            state = self._gate_state_from_tables(tables)
            state_source = "player_state"

        evaluations: list[DialogueChoiceResolveOut] = []
        for choice in sorted(payload.choices, key=lambda item: (item.priority, item.choice_id)):
            gate_payload = GateEvaluateInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                gate_id=f"{payload.dialogue_id}:{payload.node_id}:{choice.choice_id}",
                operator="and",
                state=state,
                requirements=choice.requirements,
            )
            results = [self._evaluate_gate_requirement(gate_payload, requirement) for requirement in choice.requirements]
            matched_count = sum(1 for item in results if item.matched)
            eligible = all(item.matched for item in results)
            evaluations.append(
                DialogueChoiceResolveOut(
                    choice_id=choice.choice_id,
                    text=choice.text,
                    next_node_id=choice.next_node_id,
                    priority=choice.priority,
                    eligible=eligible,
                    matched_count=matched_count,
                    total_count=len(results),
                    results=results,
                )
            )

        eligible_choices = [item for item in evaluations if item.eligible]
        selected = eligible_choices[0] if eligible_choices else None
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "dialogue_id": payload.dialogue_id,
            "node_id": payload.node_id,
            "state_source": state_source,
            "state": state.model_dump(),
            "evaluations": [item.model_dump() for item in evaluations],
            "selected_choice_id": selected.choice_id if selected else None,
            "selected_next_node_id": selected.next_node_id if selected else None,
        }
        out = DialogueResolveOut(
            dialogue_id=payload.dialogue_id,
            node_id=payload.node_id,
            state_source="payload" if state_source == "payload" else "player_state",
            eligible_choice_ids=[item.choice_id for item in eligible_choices],
            selected_choice_id=selected.choice_id if selected else None,
            selected_next_node_id=selected.next_node_id if selected else None,
            evaluations=evaluations,
            hash=self._canonical_hash(hash_payload),
        )
        self._kernel.place(
            raw=f"game.dialogue.resolve {payload.actor_id} {payload.dialogue_id} {payload.node_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "dialogue_branch_resolve",
                "result": out.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return out

    def transition_quest_state(
        self,
        *,
        payload: QuestTransitionInput,
        actor_id: str,
        workshop_id: str,
    ) -> QuestTransitionOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        tables = self._player_state_to_tables(row)
        flags = dict(tables.flags)

        quest_states_obj = self._dict_from_table(flags.get("quest_states"))
        quest_states: dict[str, object] = dict(quest_states_obj)
        existing_entry = self._dict_from_table(quest_states.get(payload.quest_id))
        previous_state = str(existing_entry.get("state") or "inactive")

        allowed_from = {item.strip() for item in payload.from_states if item.strip() != ""}
        next_state = payload.to_state.strip() or previous_state
        if payload.event_id.strip() == "":
            transitioned = False
            reason = "event_id_required"
            next_state = previous_state
        elif allowed_from and previous_state not in allowed_from:
            transitioned = False
            reason = "invalid_from_state"
            next_state = previous_state
        elif previous_state == next_state:
            transitioned = False
            reason = "no_state_change"
        else:
            transitioned = True
            reason = "ok"

        if transitioned:
            tick = self._int_from_table(self._dict_from_table(tables.clock).get("tick"), 0)
            quest_states[payload.quest_id] = {
                "state": next_state,
                "last_event_id": payload.event_id,
                "updated_tick": tick,
                "metadata": dict(payload.metadata),
            }
            history = self._list_of_dicts(flags.get("quest_history"))
            history.append(
                {
                    "quest_id": payload.quest_id,
                    "event_id": payload.event_id,
                    "from_state": previous_state,
                    "to_state": next_state,
                    "tick": tick,
                }
            )
            flags["quest_history"] = history
            for key, value in payload.set_flags.items():
                flags[key] = bool(value)
            flags["quest_states"] = quest_states
            tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
            row.state_version = max(1, int(row.state_version) + 1)
            row.levels_json = self._canonical_json(tables.levels)
            row.skills_json = self._canonical_json(tables.skills)
            row.perks_json = self._canonical_json(tables.perks)
            row.vitriol_json = self._canonical_json(tables.vitriol)
            row.inventory_json = self._canonical_json(tables.inventory)
            row.market_json = self._canonical_json(tables.market)
            row.flags_json = self._canonical_json(tables.flags)
            row.clock_json = self._canonical_json(tables.clock)
            row.updated_at = datetime.now(timezone.utc)
            repo.save_player_state(row)

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "quest_id": payload.quest_id,
            "event_id": payload.event_id,
            "previous_state": previous_state,
            "next_state": next_state,
            "transitioned": transitioned,
            "reason": reason,
            "state_version": int(row.state_version),
        }
        out = QuestTransitionOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            quest_id=payload.quest_id,
            event_id=payload.event_id,
            previous_state=previous_state,
            next_state=next_state,
            transitioned=transitioned,
            reason=reason,
            state_version=int(row.state_version),
            hash=self._canonical_hash(hash_payload),
        )
        self._kernel.place(
            raw=f"game.quest.transition {payload.actor_id} {payload.quest_id} {payload.event_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "quest_transition",
                "result": out.model_dump(),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return out

    def advance_quest_step(
        self,
        *,
        payload: QuestAdvanceInput,
        actor_id: str,
        workshop_id: str,
        persist: bool = True,
        emit_kernel: bool = True,
    ) -> QuestAdvanceOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        repo = self._require_repo()
        row = self._ensure_player_state(payload.workspace_id, payload.actor_id)
        tables = self._player_state_to_tables(row)
        flags = dict(tables.flags)

        quest_states_obj = self._dict_from_table(flags.get("quest_states"))
        quest_states: dict[str, object] = dict(quest_states_obj)
        existing_entry = self._dict_from_table(quest_states.get(payload.quest_id))
        previous_step_id = str(existing_entry.get("step_id") or payload.current_step_id).strip()
        if previous_step_id == "":
            previous_step_id = payload.current_step_id.strip()

        if payload.state is not None:
            state = payload.state
            state_source: str = "payload"
        else:
            state = self._gate_state_from_tables(tables)
            state_source = "player_state"

        evaluations: list[QuestStepEdgeResolveOut] = []
        for edge in sorted(payload.edges, key=lambda item: (item.priority, item.edge_id, item.to_step_id)):
            gate_payload = GateEvaluateInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                gate_id=f"{payload.quest_id}:{previous_step_id}:{edge.edge_id}",
                operator="and",
                state=state,
                requirements=edge.requirements,
            )
            results = [self._evaluate_gate_requirement(gate_payload, requirement) for requirement in edge.requirements]
            matched_count = sum(1 for item in results if item.matched)
            eligible = all(item.matched for item in results)
            evaluations.append(
                QuestStepEdgeResolveOut(
                    edge_id=edge.edge_id,
                    to_step_id=edge.to_step_id,
                    priority=edge.priority,
                    eligible=eligible,
                    matched_count=matched_count,
                    total_count=len(results),
                    results=results,
                )
            )

        eligible_edges = [item for item in evaluations if item.eligible]
        selected = eligible_edges[0] if eligible_edges else None
        next_step_id = selected.to_step_id if selected is not None else previous_step_id

        if payload.event_id.strip() == "":
            advanced = False
            reason = "event_id_required"
            selected = None
            next_step_id = previous_step_id
        elif selected is None:
            advanced = False
            reason = "no_eligible_edge"
        elif next_step_id == previous_step_id:
            advanced = False
            reason = "no_step_change"
        else:
            advanced = True
            reason = "ok"

        if advanced and persist:
            tick = self._int_from_table(self._dict_from_table(tables.clock).get("tick"), 0)
            quest_states[payload.quest_id] = {
                "state": str(existing_entry.get("state") or "active"),
                "step_id": next_step_id,
                "last_event_id": payload.event_id,
                "last_edge_id": selected.edge_id if selected is not None else "",
                "updated_tick": tick,
            }
            history = self._list_of_dicts(flags.get("quest_history"))
            history.append(
                {
                    "quest_id": payload.quest_id,
                    "event_id": payload.event_id,
                    "from_step_id": previous_step_id,
                    "to_step_id": next_step_id,
                    "edge_id": selected.edge_id if selected is not None else "",
                    "tick": tick,
                }
            )
            flags["quest_history"] = history
            for edge in payload.edges:
                if selected is not None and edge.edge_id == selected.edge_id:
                    for key, value in edge.set_flags.items():
                        flags[key] = bool(value)
                    break
            flags["quest_states"] = quest_states
            tables = PlayerStateTables(**{**tables.model_dump(), "flags": flags})
            row.state_version = max(1, int(row.state_version) + 1)
            row.levels_json = self._canonical_json(tables.levels)
            row.skills_json = self._canonical_json(tables.skills)
            row.perks_json = self._canonical_json(tables.perks)
            row.vitriol_json = self._canonical_json(tables.vitriol)
            row.inventory_json = self._canonical_json(tables.inventory)
            row.market_json = self._canonical_json(tables.market)
            row.flags_json = self._canonical_json(tables.flags)
            row.clock_json = self._canonical_json(tables.clock)
            row.updated_at = datetime.now(timezone.utc)
            repo.save_player_state(row)

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "quest_id": payload.quest_id,
            "event_id": payload.event_id,
            "previous_step_id": previous_step_id,
            "next_step_id": next_step_id,
            "advanced": advanced,
            "reason": reason,
            "state_source": state_source,
            "state_version": int(row.state_version),
            "persist": persist,
            "state": state.model_dump(),
            "evaluations": [item.model_dump() for item in evaluations],
            "selected_edge_id": selected.edge_id if selected is not None else None,
        }
        out = QuestAdvanceOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            quest_id=payload.quest_id,
            event_id=payload.event_id,
            previous_step_id=previous_step_id,
            next_step_id=next_step_id,
            advanced=advanced,
            reason=reason,
            state_source="payload" if state_source == "payload" else "player_state",
            state_version=int(row.state_version),
            eligible_edge_ids=[item.edge_id for item in eligible_edges],
            selected_edge_id=selected.edge_id if selected is not None else None,
            evaluations=evaluations,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.quest.advance {payload.actor_id} {payload.quest_id} {payload.event_id}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "quest_advance",
                    "result": out.model_dump(),
                    "persisted": persist,
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return out

    @staticmethod
    def _quest_graph_manifest_id(quest_id: str, version: str) -> str:
        return f"quest_graph:{quest_id.strip()}:{version.strip()}"

    @staticmethod
    def _canonical_quest_graph_steps(steps: Sequence[QuestGraphStepInput]) -> list[QuestGraphStepInput]:
        normalized_steps: list[QuestGraphStepInput] = []
        for step in sorted(steps, key=lambda item: item.step_id):
            normalized_edges = sorted(
                step.edges,
                key=lambda item: (item.priority, item.edge_id, item.to_step_id),
            )
            normalized_steps.append(
                QuestGraphStepInput(
                    step_id=step.step_id,
                    edges=normalized_edges,
                    metadata=dict(step.metadata),
                )
            )
        return normalized_steps

    @classmethod
    def _quest_graph_from_manifest(cls, row: AssetManifestOut) -> QuestGraphOut:
        payload_obj = row.payload if isinstance(row.payload, dict) else {}
        metadata = cls._dict_from_table(payload_obj.get("metadata"))
        runtime_schema_version = str(metadata.get("runtime_schema_version") or cls._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION).strip()
        if runtime_schema_version == "":
            runtime_schema_version = cls._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION
        steps_raw = payload_obj.get("steps")
        step_items = steps_raw if isinstance(steps_raw, list) else []
        steps: list[QuestGraphStepInput] = []
        for item in step_items:
            if isinstance(item, dict):
                steps.append(QuestGraphStepInput.model_validate(item))
        return QuestGraphOut(
            workspace_id=row.workspace_id,
            quest_id=str(payload_obj.get("quest_id") or ""),
            version=str(payload_obj.get("version") or ""),
            start_step_id=str(payload_obj.get("start_step_id") or ""),
            headless=bool(payload_obj.get("headless", True)),
            runtime_schema_version=runtime_schema_version,
            steps=cls._canonical_quest_graph_steps(steps),
            metadata=metadata,
            manifest_id=row.manifest_id,
            payload_hash=row.payload_hash,
            created_at=row.created_at,
        )

    def validate_quest_graph(self, payload: QuestGraphUpsertInput) -> QuestGraphValidateOut:
        errors: list[str] = []
        warnings: list[str] = []
        if not payload.headless:
            errors.append("quests_must_be_headless")
        quest_id = payload.quest_id.strip()
        version = payload.version.strip()
        start_step_id = payload.start_step_id.strip()
        if quest_id == "":
            errors.append("quest_id_required")
        if version == "":
            errors.append("version_required")
        if start_step_id == "":
            errors.append("start_step_id_required")

        steps = self._canonical_quest_graph_steps(payload.steps)
        if not steps:
            errors.append("steps_required")

        step_ids: list[str] = []
        seen_steps: set[str] = set()
        total_edges = 0
        for step in steps:
            sid = step.step_id.strip()
            if sid == "":
                errors.append("empty_step_id")
                continue
            step_ids.append(sid)
            if sid in seen_steps:
                errors.append(f"duplicate_step_id:{sid}")
            seen_steps.add(sid)

        step_set = set(step_ids)
        if start_step_id != "" and start_step_id not in step_set:
            errors.append(f"start_step_missing:{start_step_id}")

        for step in steps:
            seen_edges: set[str] = set()
            for edge in step.edges:
                total_edges += 1
                edge_id = edge.edge_id.strip()
                to_step_id = edge.to_step_id.strip()
                if edge_id == "":
                    errors.append(f"empty_edge_id:{step.step_id}")
                elif edge_id in seen_edges:
                    errors.append(f"duplicate_edge_id:{step.step_id}:{edge_id}")
                else:
                    seen_edges.add(edge_id)
                if to_step_id == "":
                    errors.append(f"empty_edge_target:{step.step_id}:{edge_id or 'unknown'}")
                elif to_step_id not in step_set:
                    errors.append(f"invalid_edge_target:{step.step_id}:{edge_id or 'unknown'}->{to_step_id}")
                if edge.priority < 0:
                    warnings.append(f"negative_priority:{step.step_id}:{edge_id or 'unknown'}")

        metadata = dict(payload.metadata)
        runtime_schema_version = str(metadata.get("runtime_schema_version") or self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION).strip()
        if runtime_schema_version == "":
            runtime_schema_version = self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION
        if runtime_schema_version != self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION:
            warnings.append(
                f"incompatible_runtime_schema_version:{runtime_schema_version}:supported:{self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION}"
            )
        metadata["runtime_schema_version"] = runtime_schema_version

        graph_payload: dict[str, object] = {
            "quest_id": quest_id,
            "version": version,
            "start_step_id": start_step_id,
            "headless": True,
            "steps": [item.model_dump() for item in steps],
            "metadata": metadata,
        }
        return QuestGraphValidateOut(
            ok=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats={"step_count": len(step_ids), "edge_count": total_edges},
            graph_hash=self._canonical_hash(graph_payload),
        )

    def upsert_quest_graph(self, payload: QuestGraphUpsertInput) -> QuestGraphOut:
        validation = self.validate_quest_graph(payload)
        if not validation.ok:
            raise ValueError(f"quest_graph_invalid:{';'.join(validation.errors)}")
        quest_id = payload.quest_id.strip()
        version = payload.version.strip()
        if quest_id == "":
            raise ValueError("quest_id_required")
        if version == "":
            raise ValueError("version_required")
        manifest_id = self._quest_graph_manifest_id(quest_id, version)

        manifests = self.list_asset_manifests(payload.workspace_id)
        existing = next(
            (
                row
                for row in manifests
                if row.kind.strip().lower() == "quest.graph.v1" and row.manifest_id == manifest_id
            ),
            None,
        )
        if existing is not None:
            out = self._quest_graph_from_manifest(existing)
            if not out.headless:
                raise ValueError("quests_must_be_headless")
            return out

        steps = self._canonical_quest_graph_steps(payload.steps)
        metadata = dict(payload.metadata)
        runtime_schema_version = str(metadata.get("runtime_schema_version") or self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION).strip()
        if runtime_schema_version == "":
            runtime_schema_version = self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION
        metadata["runtime_schema_version"] = runtime_schema_version
        payload_obj: dict[str, object] = {
            "quest_id": quest_id,
            "version": version,
            "start_step_id": payload.start_step_id.strip(),
            "headless": True,
            "steps": [item.model_dump() for item in steps],
            "metadata": metadata,
        }
        saved = self.create_asset_manifest(
            AssetManifestCreate(
                workspace_id=payload.workspace_id,
                realm_id="lapidus",
                manifest_id=manifest_id,
                name=f"Quest Graph {quest_id} v{version}",
                kind="quest.graph.v1",
                payload=payload_obj,
            )
        )
        return self._quest_graph_from_manifest(saved)

    def get_quest_graph(
        self,
        *,
        workspace_id: str,
        quest_id: str,
        version: str | None = None,
        enforce_runtime_compat: bool = True,
    ) -> QuestGraphOut:
        quest_key = quest_id.strip()
        if quest_key == "":
            raise ValueError("quest_id_required")
        version_filter = (version or "").strip()

        manifests = self.list_asset_manifests(workspace_id)
        candidates: list[QuestGraphOut] = []
        for row in manifests:
            if row.kind.strip().lower() != "quest.graph.v1":
                continue
            parsed = self._quest_graph_from_manifest(row)
            if parsed.quest_id != quest_key:
                continue
            if version_filter != "" and parsed.version != version_filter:
                continue
            if not parsed.headless:
                continue
            candidates.append(parsed)
        if not candidates:
            raise ValueError("quest_graph_not_found")
        candidates.sort(key=lambda item: (item.created_at, item.version, item.manifest_id), reverse=True)
        selected = candidates[0]
        if enforce_runtime_compat and selected.runtime_schema_version != self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION:
            raise ValueError(
                "quest_graph_incompatible_runtime_schema:"
                f"{selected.runtime_schema_version}:supported:{self._QUEST_GRAPH_RUNTIME_SCHEMA_VERSION}"
            )
        return selected

    def get_latest_quest_graph(
        self,
        *,
        workspace_id: str,
        quest_id: str,
    ) -> QuestGraphOut:
        return self.get_quest_graph(
            workspace_id=workspace_id,
            quest_id=quest_id,
            version=None,
        )

    def hash_quest_graph(
        self,
        *,
        workspace_id: str,
        quest_id: str,
        version: str | None = None,
    ) -> QuestGraphHashOut:
        graph = self.get_quest_graph(
            workspace_id=workspace_id,
            quest_id=quest_id,
            version=version,
            enforce_runtime_compat=False,
        )
        graph_payload: dict[str, object] = {
            "quest_id": graph.quest_id,
            "version": graph.version,
            "start_step_id": graph.start_step_id,
            "headless": graph.headless,
            "steps": [item.model_dump() for item in graph.steps],
            "metadata": graph.metadata,
        }
        return QuestGraphHashOut(
            workspace_id=graph.workspace_id,
            quest_id=graph.quest_id,
            version=graph.version,
            manifest_id=graph.manifest_id,
            graph_hash=self._canonical_hash(graph_payload),
        )

    def list_quest_graphs(
        self,
        *,
        workspace_id: str,
        quest_id: str | None = None,
        version: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> QuestGraphListOut:
        quest_filter = (quest_id or "").strip()
        version_filter = (version or "").strip()
        page_limit = max(1, min(500, int(limit)))
        page_offset = max(0, int(offset))

        manifests = self.list_asset_manifests(workspace_id)
        items: list[QuestGraphOut] = []
        for row in manifests:
            if row.kind.strip().lower() != "quest.graph.v1":
                continue
            parsed = self._quest_graph_from_manifest(row)
            if not parsed.headless:
                continue
            if quest_filter != "" and parsed.quest_id != quest_filter:
                continue
            if version_filter != "" and parsed.version != version_filter:
                continue
            items.append(parsed)
        items.sort(key=lambda item: (item.created_at, item.quest_id, item.version, item.manifest_id), reverse=True)
        total = len(items)
        paged = items[page_offset : page_offset + page_limit]
        return QuestGraphListOut(
            total=total,
            limit=page_limit,
            offset=page_offset,
            items=paged,
        )

    def advance_quest_step_by_graph(
        self,
        *,
        payload: QuestAdvanceByGraphInput,
        actor_id: str,
        workshop_id: str,
    ) -> QuestAdvanceByGraphOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        graph = self.get_quest_graph(
            workspace_id=payload.workspace_id,
            quest_id=payload.quest_id,
            version=payload.version,
        )
        step_id = payload.current_step_id.strip()
        if step_id == "":
            step_id = graph.start_step_id
        step = next((item for item in graph.steps if item.step_id == step_id), None)
        if step is None:
            raise ValueError("quest_step_not_found")
        advance = self.advance_quest_step(
            payload=QuestAdvanceInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                quest_id=payload.quest_id,
                event_id=payload.event_id,
                current_step_id=step_id,
                headless=True,
                state=payload.state,
                edges=step.edges,
            ),
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return QuestAdvanceByGraphOut(graph=graph, advance=advance)

    def advance_quest_step_by_graph_dry_run(
        self,
        *,
        payload: QuestAdvanceByGraphInput,
        actor_id: str,
        workshop_id: str,
    ) -> QuestAdvanceByGraphDryRunOut:
        if not payload.headless:
            raise ValueError("quests_must_be_headless")
        graph = self.get_quest_graph(
            workspace_id=payload.workspace_id,
            quest_id=payload.quest_id,
            version=payload.version,
        )
        step_id = payload.current_step_id.strip()
        if step_id == "":
            step_id = graph.start_step_id
        step = next((item for item in graph.steps if item.step_id == step_id), None)
        if step is None:
            raise ValueError("quest_step_not_found")
        advance = self.advance_quest_step(
            payload=QuestAdvanceInput(
                workspace_id=payload.workspace_id,
                actor_id=payload.actor_id,
                quest_id=payload.quest_id,
                event_id=payload.event_id,
                current_step_id=step_id,
                headless=True,
                state=payload.state,
                edges=step.edges,
            ),
            actor_id=actor_id,
            workshop_id=workshop_id,
            persist=False,
            emit_kernel=False,
        )
        return QuestAdvanceByGraphDryRunOut(graph=graph, advance=advance, persisted=False)

    @staticmethod
    def _hex_to_int(value: str) -> int:
        return int(value, 16)

    @staticmethod
    def _name_to_int(value: str) -> int:
        encoded = value.encode("utf-8")
        if len(encoded) == 0:
            return 0
        return int.from_bytes(encoded, byteorder="big", signed=False)

    @staticmethod
    def _is_prime(value: int) -> bool:
        n = int(value)
        if n < 2:
            return False
        if n in (2, 3):
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return False
            i += 6
        return True

    @staticmethod
    def _fibonacci_sequence(count: int) -> list[int]:
        n = max(0, int(count))
        if n == 0:
            return []
        seq = [1, 1]
        while len(seq) < n:
            seq.append(seq[-1] + seq[-2])
        return seq[:n]

    def _persist_math_lineage(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        node_payloads: Sequence[tuple[int, str, dict[str, object]]],
        edge_payloads: Sequence[tuple[str, int, int, dict[str, object]]],
        function_id: str,
        function_signature: str,
        function_body: str,
        function_metadata: dict[str, object],
    ) -> tuple[list[str], list[str], str | None, str | None, dict[str, str], dict[int, list[str]]]:
        if self._repo is None:
            return [], [], None, None, {}, {}
        function_hash = self._canonical_hash(
            {
                "workspace_id": workspace_id,
                "function_id": function_id,
                "version": "v1",
                "signature": function_signature,
                "body": function_body,
                "metadata": function_metadata,
            }
        )
        function_node_key = f"function.{function_id}"
        effective_nodes = list(node_payloads)
        effective_nodes.append(
            (
                12,
                function_node_key,
                {
                    "function_id": function_id,
                    "version": "v1",
                    "signature": function_signature,
                    "function_hash": function_hash,
                },
            )
        )
        effective_edges = list(edge_payloads)
        if effective_nodes:
            non_function_nodes = [node for node in effective_nodes if not (node[0] == 12 and node[1] == function_node_key)]
            if non_function_nodes:
                terminal_layer, terminal_key, _ = max(non_function_nodes, key=lambda row: row[0])
                effective_edges.append(
                    (
                        "resolved_by",
                        terminal_layer,
                        12,
                        {"from_key": terminal_key, "to_key": function_node_key, "function_id": function_id},
                    )
                )
        created_nodes: list[LayerNodeOut] = []
        for layer_index, node_key, payload in effective_nodes:
            created_nodes.append(
                self.create_layer_node(
                    payload=LayerNodeCreate(
                        workspace_id=workspace_id,
                        layer_index=layer_index,
                        node_key=node_key,
                        payload=payload,
                    ),
                    actor_id=actor_id,
                )
            )
        node_lookup: dict[tuple[int, str], str] = {
            (node.layer_index, node.node_key): node.id for node in created_nodes
        }
        created_edges: list[LayerEdgeOut] = []
        for edge_kind, from_layer, to_layer, metadata in effective_edges:
            from_key = str(metadata.get("from_key") or "")
            to_key = str(metadata.get("to_key") or "")
            from_node_id = node_lookup.get((from_layer, from_key))
            to_node_id = node_lookup.get((to_layer, to_key))
            if from_node_id is None or to_node_id is None:
                continue
            created_edges.append(
                self.create_layer_edge(
                    payload=LayerEdgeCreate(
                        workspace_id=workspace_id,
                        from_node_id=from_node_id,
                        to_node_id=to_node_id,
                        edge_kind=edge_kind,
                        metadata=metadata,
                    ),
                    actor_id=actor_id,
                )
            )
        node_refs: dict[str, str] = {}
        nodes_by_layer: dict[int, list[str]] = {}
        for node in created_nodes:
            node_refs[f"L{node.layer_index}:{node.node_key}"] = node.id
            nodes_by_layer.setdefault(node.layer_index, []).append(node.id)
        for layer, values in nodes_by_layer.items():
            values.sort()
        fn = self.create_function_store_entry(
            payload=FunctionStoreCreate(
                workspace_id=workspace_id,
                function_id=function_id,
                version="v1",
                signature=function_signature,
                body=function_body,
                metadata=function_metadata,
            ),
            actor_id=actor_id,
        )
        return [node.id for node in created_nodes], [edge.id for edge in created_edges], fn.id, fn.function_hash, node_refs, nodes_by_layer

    @classmethod
    def _level_from_tables(cls, tables: PlayerStateTables) -> int:
        levels = cls._dict_from_table(tables.levels)
        for key in ("current_level", "level", "current", "value"):
            maybe = levels.get(key)
            if isinstance(maybe, int):
                return max(1, maybe)
        return 1

    @classmethod
    def _kills_deaths_from_tables(cls, tables: PlayerStateTables) -> tuple[int, int]:
        flags = cls._dict_from_table(tables.flags)
        levels = cls._dict_from_table(tables.levels)
        combat = cls._dict_from_table(flags.get("combat"))
        stats = cls._dict_from_table(flags.get("stats"))
        candidates = [flags, combat, stats, levels]

        def _first_int(keys: tuple[str, ...]) -> int | None:
            for entry in candidates:
                for key in keys:
                    value = entry.get(key)
                    if isinstance(value, int):
                        return value
            return None

        kills = _first_int(("kills", "kill_count", "defeats", "k"))
        deaths = _first_int(("deaths", "death_count", "d"))
        return max(0, kills or 0), max(0, deaths or 0)

    def compute_numeral_3d(
        self,
        *,
        payload: Numeral3DInput,
        actor_id: str,
    ) -> Numeral3DOut:
        ring_base = max(2, min(64, int(payload.ring_base)))
        x = int(payload.x)
        y = int(payload.y)
        z = int(payload.z)
        dx = x % ring_base
        dy = y % ring_base
        dz = z % ring_base
        scalar_index = dx + (dy * ring_base) + (dz * ring_base * ring_base)
        octant = (
            ("P" if x >= 0 else "N")
            + ("P" if y >= 0 else "N")
            + ("P" if z >= 0 else "N")
        )
        magnitude = round(math.sqrt((x * x) + (y * y) + (z * z)), 6)
        lineage_nodes, lineage_edges, fn_id, fn_hash, node_refs, nodes_by_layer = self._persist_math_lineage(
            workspace_id=payload.workspace_id,
            actor_id=actor_id,
            node_payloads=[
                (1, "numeral.bitgrid", {"bits": {"x": format(dx, "b"), "y": format(dy, "b"), "z": format(dz, "b")}, "ring_base": ring_base}),
                (2, "numeral.scalar", {"scalar_index": scalar_index, "ring_base": ring_base}),
                (3, "numeral.polarity", {"x_positive": x >= 0, "y_positive": y >= 0, "z_positive": z >= 0}),
                (4, "numeral.vector", {"x": x, "y": y, "z": z, "octant": octant, "magnitude": magnitude}),
                (7, "numeral.causal_chunk", {"operation": "vector_to_scalar_projection", "ring_base": ring_base}),
                (8, "numeral.path", {"digits": {"x": dx, "y": dy, "z": dz}, "ordering": "axis_lexicographic"}),
                (11, "numeral.render_constraints", {"projection": "2.5d_or_3d", "depth_hint": dz, "octant": octant}),
            ],
            edge_payloads=[
                ("derives", 1, 2, {"from_key": "numeral.bitgrid", "to_key": "numeral.scalar"}),
                ("classifies", 2, 3, {"from_key": "numeral.scalar", "to_key": "numeral.polarity"}),
                ("derives", 4, 2, {"from_key": "numeral.vector", "to_key": "numeral.scalar"}),
                ("coordinates", 3, 4, {"from_key": "numeral.polarity", "to_key": "numeral.vector"}),
                ("chunks", 4, 7, {"from_key": "numeral.vector", "to_key": "numeral.causal_chunk"}),
                ("indexes", 7, 8, {"from_key": "numeral.causal_chunk", "to_key": "numeral.path"}),
                ("constrains", 8, 11, {"from_key": "numeral.path", "to_key": "numeral.render_constraints"}),
            ],
            function_id="math.numeral_3d.compute",
            function_signature="(x:int,y:int,z:int,ring_base:int)->numeral3d",
            function_body="scalar_index = (x%base) + (y%base)*base + (z%base)*base^2",
            function_metadata={
                "ring_base": ring_base,
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
            },
        )
        return Numeral3DOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            ring_base=ring_base,
            vector={"x": x, "y": y, "z": z},
            digits={"x": dx, "y": dy, "z": dz},
            scalar_index=scalar_index,
            octant=octant,
            magnitude=magnitude,
            lineage_node_ids=lineage_nodes,
            lineage_edge_ids=lineage_edges,
            lineage_node_refs=node_refs,
            lineage_nodes_by_layer=nodes_by_layer,
            function_store_id=fn_id,
            function_hash=fn_hash,
        )

    def compute_fibonacci_ordering(
        self,
        *,
        payload: FibonacciOrderingInput,
        actor_id: str,
    ) -> FibonacciOrderingOut:
        ring_base = max(2, min(64, int(payload.ring_base)))
        raw_items = [str(item).strip() for item in payload.item_ids]
        items = [item for item in raw_items if item != ""]
        if not items:
            raise ValueError("item_ids_required")
        canonical_items = sorted(set(items))
        fib = self._fibonacci_sequence(len(canonical_items))
        weighted: list[tuple[str, int, int]] = []
        for index, item_id in enumerate(canonical_items):
            weight = fib[index]
            if payload.prioritize_primes and self._is_prime(index + 2):
                weight += ring_base
            weighted.append((item_id, weight, index))
        weighted.sort(key=lambda row: (-row[1], row[0], row[2]))
        ordered_item_ids = [row[0] for row in weighted]
        rank_map = {item_id: rank for rank, item_id in enumerate(ordered_item_ids)}
        lineage_nodes, lineage_edges, fn_id, fn_hash, node_refs, nodes_by_layer = self._persist_math_lineage(
            workspace_id=payload.workspace_id,
            actor_id=actor_id,
            node_payloads=[
                (1, "fibonacci.bitgrid", {"weights_binary": [format(value, "b") for value in fib], "count": len(fib)}),
                (2, "fibonacci.scalars", {"weights": fib, "ring_base": ring_base}),
                (3, "fibonacci.prime_flags", {"prime_index_flags": [self._is_prime(index + 2) for index, _ in enumerate(canonical_items)]}),
                (7, "fibonacci.causal_chunk", {"operation": "rank_weighting", "prioritize_primes": bool(payload.prioritize_primes)}),
                (8, "fibonacci.order", {"ordered_item_ids": ordered_item_ids, "rank_map": rank_map}),
                (10, "fibonacci.items", {"item_ids": canonical_items}),
                (11, "fibonacci.render_constraints", {"ordering_channel": "scenegraph_priority", "priority_count": len(ordered_item_ids)}),
            ],
            edge_payloads=[
                ("derives", 1, 2, {"from_key": "fibonacci.bitgrid", "to_key": "fibonacci.scalars"}),
                ("classifies", 2, 3, {"from_key": "fibonacci.scalars", "to_key": "fibonacci.prime_flags"}),
                ("chunks", 3, 7, {"from_key": "fibonacci.prime_flags", "to_key": "fibonacci.causal_chunk"}),
                ("weights", 2, 8, {"from_key": "fibonacci.scalars", "to_key": "fibonacci.order"}),
                ("indexes", 10, 8, {"from_key": "fibonacci.items", "to_key": "fibonacci.order"}),
                ("constrains", 8, 11, {"from_key": "fibonacci.order", "to_key": "fibonacci.render_constraints"}),
            ],
            function_id="math.fibonacci_ordering.compute",
            function_signature="(item_ids:list[str],ring_base:int,prioritize_primes:bool)->ordering",
            function_body="weight(i)=fib(i)+base if prime-index boost enabled",
            function_metadata={
                "ring_base": ring_base,
                "prioritize_primes": bool(payload.prioritize_primes),
                "workspace_id": payload.workspace_id,
                "actor_id": payload.actor_id,
            },
        )
        return FibonacciOrderingOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            ring_base=ring_base,
            item_ids=canonical_items,
            ordered_item_ids=ordered_item_ids,
            fibonacci_weights=fib,
            rank_map=rank_map,
            lineage_node_ids=lineage_nodes,
            lineage_edge_ids=lineage_edges,
            lineage_node_refs=node_refs,
            lineage_nodes_by_layer=nodes_by_layer,
            function_store_id=fn_id,
            function_hash=fn_hash,
        )

    @staticmethod
    def _chaos_from_kd(*, kills: int, deaths: int) -> tuple[int, int]:
        safe_kills = max(0, int(kills))
        safe_deaths = max(0, int(deaths))
        kd_ratio_milli = (safe_kills * 1000) // max(1, safe_deaths)
        total = max(1, safe_kills + safe_deaths)
        delta = safe_kills - safe_deaths
        # Polarity rule:
        # - More kills than deaths => higher chaos.
        # - More deaths than kills => lower chaos (order-leaning).
        if delta > 0:
            delta_milli = (delta * 1000) // total
            chaos_meter = min(100, 50 + (delta_milli // 20))
        elif delta < 0:
            delta_milli = ((-delta) * 1000) // total
            chaos_meter = max(0, 50 - (delta_milli // 20))
        else:
            chaos_meter = 50
        return kd_ratio_milli, chaos_meter

    @classmethod
    def _akashic_memory_seed(
        cls,
        *,
        snapshot_hash: str,
        actor_id: str,
        player_name: str,
        canonical_game_number: int,
        deaths: int,
    ) -> str:
        seed_hash = cls._canonical_hash(
            {
                "snapshot_hash": snapshot_hash,
                "actor_id": actor_id,
                "player_name": player_name,
                "canonical_game_number": canonical_game_number,
                "deaths": max(0, deaths),
                "patron": cls._DEATH_PATRON_ID,
            }
        )
        return f"akm_{seed_hash[:24]}"

    @classmethod
    def _build_breath_ko_iteration(
        cls,
        *,
        azoth_int: int,
        save_hash_int: int,
        max_iter: int,
        attempt: int,
    ) -> tuple[int, int, int, bool, str]:
        scale = cls._BREATH_KO_FIXED_SCALE
        escape_sq = (cls._BREATH_KO_ESCAPE_RADIUS * scale) ** 2
        seed = cls._canonical_hash(
            {
                "azoth_int": str(azoth_int),
                "save_hash_int": str(save_hash_int),
                "max_iter": max_iter,
                "attempt": attempt,
            }
        )
        seed_int = cls._hex_to_int(seed)
        b_real = int(seed_int % (4 * scale)) - (2 * scale)
        b_imag = int((seed_int >> 29) % (4 * scale)) - (2 * scale)
        x_real = int((azoth_int % (4 * scale)) - (2 * scale))
        x_imag = int((save_hash_int % (4 * scale)) - (2 * scale))

        escaped = False
        escape_iter = max_iter
        samples: list[tuple[int, int, int]] = []
        for i in range(max_iter):
            rr = x_real * x_real
            ii = x_imag * x_imag
            ri2 = 2 * x_real * x_imag
            x_real = (rr - ii) // scale + b_real
            x_imag = ri2 // scale + b_imag
            mag_sq = (x_real * x_real) + (x_imag * x_imag)
            if i < 64 or i % 97 == 0:
                samples.append((i, x_real, x_imag))
            if mag_sq > escape_sq:
                escaped = True
                escape_iter = i + 1
                break
        if not samples or samples[-1][0] != escape_iter:
            samples.append((escape_iter, x_real, x_imag))
        orbit_signature_hash = cls._canonical_hash(
            {
                "samples": samples,
                "escaped": escaped,
                "escape_iter": escape_iter,
                "max_iter": max_iter,
                "b_real": b_real,
                "b_imag": b_imag,
            }
        )
        return b_real, b_imag, escape_iter, escaped, orbit_signature_hash

    @classmethod
    def _breath_ko_from_manifest(cls, row: AssetManifestOut) -> BreathKoOut:
        payload = row.payload if isinstance(row.payload, dict) else {}
        return BreathKoOut(
            breath_id=str(payload.get("breath_id") or row.manifest_id),
            workspace_id=row.workspace_id,
            actor_id=str(payload.get("actor_id") or ""),
            snapshot_hash=str(payload.get("snapshot_hash") or ""),
            player_name=str(payload.get("player_name") or ""),
            canonical_game_number=int(payload.get("canonical_game_number") or 0),
            level=int(payload.get("level") or 1),
            quest_completion=int(payload.get("quest_completion") or 0),
            kills=int(payload.get("kills") or 0),
            deaths=int(payload.get("deaths") or 0),
            kill_patron_id=str(payload.get("kill_patron_id") or cls._KILL_PATRON_ID),
            kill_patron_name=str(payload.get("kill_patron_name") or cls._KILL_PATRON_NAME),
            death_patron_id=str(payload.get("death_patron_id") or cls._DEATH_PATRON_ID),
            death_patron_name=str(payload.get("death_patron_name") or cls._DEATH_PATRON_NAME),
            kd_ratio_milli=int(payload.get("kd_ratio_milli") or 0),
            chaos_meter=int(payload.get("chaos_meter") or 0),
            akashic_memory_seed=str(payload.get("akashic_memory_seed") or ""),
            void_body_mark_hash=str(payload.get("void_body_mark_hash") or ""),
            azoth_int=str(payload.get("azoth_int") or "0"),
            b_real=int(payload.get("b_real") or 0),
            b_imag=int(payload.get("b_imag") or 0),
            max_iter=int(payload.get("max_iter") or cls._BREATH_KO_SUPPORTED_MAX_ITER),
            escape_iter=int(payload.get("escape_iter") or 0),
            escaped=bool(payload.get("escaped", False)),
            orbit_signature_hash=str(payload.get("orbit_signature_hash") or ""),
            palette_seed=int(payload.get("palette_seed") or 0),
            special_case_rank=int(payload.get("special_case_rank") or 0),
            collision_attempt=int(payload.get("collision_attempt") or 0),
            created_at=row.created_at,
        )

    def list_breath_ko(
        self,
        *,
        workspace_id: str,
        actor_id: str | None = None,
    ) -> BreathKoListOut:
        actor_filter = (actor_id or "").strip()
        manifests = self.list_asset_manifests(workspace_id)
        items: list[BreathKoOut] = []
        for row in manifests:
            if row.kind.strip().lower() != self._BREATH_KO_KIND:
                continue
            parsed = self._breath_ko_from_manifest(row)
            if actor_filter != "" and parsed.actor_id != actor_filter:
                continue
            items.append(parsed)
        items.sort(key=lambda item: (item.created_at, item.breath_id), reverse=True)
        return BreathKoListOut(total=len(items), items=items)

    @staticmethod
    def _breath_policy_tags(*, chaos_meter: int, order_meter: int, kills: int, deaths: int) -> list[str]:
        tags: list[str] = []
        if chaos_meter >= 67:
            tags.append("chaos.high")
        elif chaos_meter <= 33:
            tags.append("chaos.low")
        else:
            tags.append("chaos.mid")
        if order_meter >= 67:
            tags.append("order.high")
        elif order_meter <= 33:
            tags.append("order.low")
        else:
            tags.append("order.mid")
        if deaths > kills:
            tags.append("strategy.death_forward")
        elif kills > deaths:
            tags.append("strategy.kill_forward")
        else:
            tags.append("strategy.balanced")
        return tags

    def _build_breath_ko_ephemeral(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        player_name: str,
        canonical_game_number: int,
        quest_completion: int,
        kills: int,
        deaths: int,
        level: int,
        max_iter: int,
    ) -> BreathKoOut:
        snapshot_hash = self._canonical_hash(
            {
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "player_name": player_name,
                "canonical_game_number": canonical_game_number,
                "quest_completion": quest_completion,
                "kills": kills,
                "deaths": deaths,
                "level": level,
                "max_iter": max_iter,
                "mode": "ephemeral",
            }
        )
        save_hash_int = self._hex_to_int(snapshot_hash)
        player_name_int = self._name_to_int(player_name)
        kd_ratio_milli, chaos_meter = self._chaos_from_kd(kills=kills, deaths=deaths)
        akashic_memory_seed = self._akashic_memory_seed(
            snapshot_hash=snapshot_hash,
            actor_id=actor_id,
            player_name=player_name,
            canonical_game_number=canonical_game_number,
            deaths=deaths,
        )
        void_body_mark_hash = self._canonical_hash(
            {
                "snapshot_hash": snapshot_hash,
                "actor_id": actor_id,
                "player_name": player_name,
                "canonical_game_number": canonical_game_number,
                "kills": kills,
                "patron": self._KILL_PATRON_ID,
            }
        )
        azoth_int = (
            (17 * level)
            + (31 * (quest_completion ** 2))
            + (43 * (canonical_game_number ** 3))
            + (59 * (save_hash_int ** 2))
            + (71 * (player_name_int ** 2))
            + (73 * (chaos_meter ** 2))
            + (79 * kd_ratio_milli)
        )
        b_real, b_imag, escape_iter, escaped, orbit_signature_hash = self._build_breath_ko_iteration(
            azoth_int=azoth_int,
            save_hash_int=save_hash_int,
            max_iter=max_iter,
            attempt=0,
        )
        palette_seed = int(orbit_signature_hash[:8], 16)
        special_case_rank = int(orbit_signature_hash[8:16], 16) % 10000
        breath_id = f"breath_ko:{actor_id}:{snapshot_hash[:12]}:{orbit_signature_hash[:12]}:0"
        return BreathKoOut(
            breath_id=breath_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            snapshot_hash=snapshot_hash,
            player_name=player_name,
            canonical_game_number=canonical_game_number,
            level=level,
            quest_completion=quest_completion,
            kills=kills,
            deaths=deaths,
            kill_patron_id=self._KILL_PATRON_ID,
            kill_patron_name=self._KILL_PATRON_NAME,
            death_patron_id=self._DEATH_PATRON_ID,
            death_patron_name=self._DEATH_PATRON_NAME,
            kd_ratio_milli=kd_ratio_milli,
            chaos_meter=chaos_meter,
            akashic_memory_seed=akashic_memory_seed,
            void_body_mark_hash=void_body_mark_hash,
            azoth_int=str(azoth_int),
            b_real=b_real,
            b_imag=b_imag,
            max_iter=max_iter,
            escape_iter=escape_iter,
            escaped=escaped,
            orbit_signature_hash=orbit_signature_hash,
            palette_seed=palette_seed,
            special_case_rank=special_case_rank,
            collision_attempt=0,
            created_at=datetime.now(timezone.utc),
        )

    def evaluate_breath_ko(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        payload: Mapping[str, object],
        kernel_actor_id: str,
        workshop_id: str,
        persist_state: bool = True,
        emit_kernel: bool = True,
    ) -> dict[str, object]:
        generate_inputs_present = any(
            key in payload
            for key in ("player_name", "canonical_game_number", "quest_completion", "kills", "deaths", "level", "max_iter")
        )
        latest: BreathKoOut | None = None
        if self._repo is not None:
            latest = next(iter(self.list_breath_ko(workspace_id=workspace_id, actor_id=actor_id).items), None)
        selected: BreathKoOut | None = latest
        if generate_inputs_present or selected is None:
            player_name = str(payload.get("player_name") or (selected.player_name if selected is not None else "")).strip()
            canonical_game_number = payload.get("canonical_game_number")
            if canonical_game_number is None and selected is not None:
                canonical_game_number = selected.canonical_game_number
            quest_completion = payload.get("quest_completion")
            if quest_completion is None and selected is not None:
                quest_completion = selected.quest_completion
            if player_name == "" or canonical_game_number is None or quest_completion is None:
                raise ValueError("breath_ko_evaluate_requires_player_name_canonical_game_number_quest_completion")
            if self._repo is None:
                selected = self._build_breath_ko_ephemeral(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    player_name=player_name,
                    canonical_game_number=int(canonical_game_number),
                    quest_completion=int(quest_completion),
                    kills=max(0, int(payload.get("kills") or 0)),
                    deaths=max(0, int(payload.get("deaths") or 0)),
                    level=max(1, int(payload.get("level") or 1)),
                    max_iter=max(1, min(self._BREATH_KO_MAX_ITER_CAP, int(payload.get("max_iter") or self._BREATH_KO_SUPPORTED_MAX_ITER))),
                )
            else:
                selected = self.generate_breath_ko(
                    payload=BreathKoGenerateInput(
                        workspace_id=workspace_id,
                        actor_id=actor_id,
                        player_name=player_name,
                        canonical_game_number=int(canonical_game_number),
                        quest_completion=int(quest_completion),
                        kills=int(payload["kills"]) if "kills" in payload and payload.get("kills") is not None else None,
                        deaths=int(payload["deaths"]) if "deaths" in payload and payload.get("deaths") is not None else None,
                        level=int(payload["level"]) if "level" in payload and payload.get("level") is not None else None,
                        max_iter=int(payload["max_iter"]) if "max_iter" in payload and payload.get("max_iter") is not None else self._BREATH_KO_SUPPORTED_MAX_ITER,
                    ),
                    actor_id=kernel_actor_id,
                    workshop_id=workshop_id,
                )
        if selected is None:
            raise ValueError("breath_ko_not_found")
        order_meter = max(0, min(100, 100 - int(selected.chaos_meter)))
        out: dict[str, object] = {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "breath_id": selected.breath_id,
            "snapshot_hash": selected.snapshot_hash,
            "chaos_meter": int(selected.chaos_meter),
            "order_meter": order_meter,
            "kills": int(selected.kills),
            "deaths": int(selected.deaths),
            "kill_patron_id": selected.kill_patron_id,
            "death_patron_id": selected.death_patron_id,
            "akashic_memory_seed": selected.akashic_memory_seed,
            "void_body_mark_hash": selected.void_body_mark_hash,
            "policy_tags": self._breath_policy_tags(
                chaos_meter=int(selected.chaos_meter),
                order_meter=order_meter,
                kills=int(selected.kills),
                deaths=int(selected.deaths),
            ),
        }
        if persist_state and self._repo is not None:
            state = self.get_player_state(workspace_id=workspace_id, actor_id=actor_id)
            flags = dict(state.tables.flags)
            flags["breath_ko"] = {
                "breath_id": selected.breath_id,
                "snapshot_hash": selected.snapshot_hash,
                "chaos_meter": int(selected.chaos_meter),
                "order_meter": order_meter,
                "kills": int(selected.kills),
                "deaths": int(selected.deaths),
                "kd_ratio_milli": int(selected.kd_ratio_milli),
                "kill_patron_id": selected.kill_patron_id,
                "death_patron_id": selected.death_patron_id,
                "akashic_memory_seed": selected.akashic_memory_seed,
                "void_body_mark_hash": selected.void_body_mark_hash,
            }
            akashic_memory = self._list_from_table(flags.get("akashic_memory"))
            if selected.akashic_memory_seed != "":
                akashic_memory = sorted(set([*akashic_memory, selected.akashic_memory_seed]))
            flags["akashic_memory"] = akashic_memory
            void_mark = self._list_from_table(flags.get("void_mark"))
            if selected.void_body_mark_hash != "":
                void_mark = sorted(set([*void_mark, selected.void_body_mark_hash]))
            flags["void_mark"] = void_mark
            self.apply_player_state(
                payload=PlayerStateApplyInput(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    tables=PlayerStateTables(flags=flags),
                    mode="merge",
                ),
                actor_id=kernel_actor_id,
                workshop_id=workshop_id,
            )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.breath.ko.evaluate {actor_id} {selected.breath_id}",
                context={
                    "workspace_id": workspace_id,
                    "rule": "breath_ko_evaluate",
                    "result": out,
                },
                actor_id=kernel_actor_id,
                workshop_id=workshop_id,
            )
        return out

    def generate_breath_ko(
        self,
        *,
        payload: BreathKoGenerateInput,
        actor_id: str,
        workshop_id: str,
    ) -> BreathKoOut:
        player_name = payload.player_name.strip()
        if player_name == "":
            raise ValueError("player_name_required")
        canonical_game_number = max(0, int(payload.canonical_game_number))
        quest_completion = max(0, int(payload.quest_completion))
        max_iter = max(1, min(self._BREATH_KO_MAX_ITER_CAP, int(payload.max_iter)))

        state = self.get_player_state(workspace_id=payload.workspace_id, actor_id=payload.actor_id)
        snapshot_hash = state.hash
        level = int(payload.level) if payload.level is not None else self._level_from_tables(state.tables)
        level = max(1, level)
        inferred_kills, inferred_deaths = self._kills_deaths_from_tables(state.tables)
        kills = max(0, int(payload.kills)) if payload.kills is not None else inferred_kills
        deaths = max(0, int(payload.deaths)) if payload.deaths is not None else inferred_deaths
        kd_ratio_milli, chaos_meter = self._chaos_from_kd(kills=kills, deaths=deaths)
        akashic_memory_seed = self._akashic_memory_seed(
            snapshot_hash=snapshot_hash,
            actor_id=payload.actor_id,
            player_name=player_name,
            canonical_game_number=canonical_game_number,
            deaths=deaths,
        )
        void_body_mark_hash = self._canonical_hash(
            {
                "snapshot_hash": snapshot_hash,
                "actor_id": payload.actor_id,
                "player_name": player_name,
                "canonical_game_number": canonical_game_number,
                "kills": kills,
                "patron": self._KILL_PATRON_ID,
            }
        )

        save_hash_int = self._hex_to_int(snapshot_hash)
        player_name_int = self._name_to_int(player_name)
        # Azoth polynomial monomial resolution over canonical deterministic inputs.
        azoth_int = (
            (17 * level)
            + (31 * (quest_completion ** 2))
            + (43 * (canonical_game_number ** 3))
            + (59 * (save_hash_int ** 2))
            + (71 * (player_name_int ** 2))
            + (73 * (chaos_meter ** 2))
            + (79 * kd_ratio_milli)
        )

        existing = self.list_breath_ko(workspace_id=payload.workspace_id, actor_id=payload.actor_id).items
        for item in existing:
            if (
                item.snapshot_hash == snapshot_hash
                and item.player_name == player_name
                and item.canonical_game_number == canonical_game_number
                and item.quest_completion == quest_completion
                and item.level == level
                and item.kills == kills
                and item.deaths == deaths
                and item.chaos_meter == chaos_meter
                and item.max_iter == max_iter
            ):
                return item

        existing_orbit_hashes = {item.orbit_signature_hash for item in existing if item.orbit_signature_hash != ""}
        selected: tuple[int, int, int, bool, str, int] | None = None
        for attempt in range(64):
            b_real, b_imag, escape_iter, escaped, orbit_signature_hash = self._build_breath_ko_iteration(
                azoth_int=azoth_int,
                save_hash_int=save_hash_int,
                max_iter=max_iter,
                attempt=attempt,
            )
            if orbit_signature_hash in existing_orbit_hashes:
                continue
            selected = (b_real, b_imag, escape_iter, escaped, orbit_signature_hash, attempt)
            break
        if selected is None:
            raise ValueError("breath_ko_collision_budget_exhausted")

        b_real, b_imag, escape_iter, escaped, orbit_signature_hash, collision_attempt = selected
        palette_seed = int(orbit_signature_hash[:8], 16)
        special_case_rank = int(orbit_signature_hash[8:16], 16) % 10000
        breath_id = (
            f"breath_ko:{payload.actor_id}:"
            f"{snapshot_hash[:12]}:{orbit_signature_hash[:12]}:{collision_attempt}"
        )
        manifest_id = f"{breath_id}:v1"
        breath_payload: dict[str, object] = {
            "breath_id": breath_id,
            "actor_id": payload.actor_id,
            "snapshot_hash": snapshot_hash,
            "player_name": player_name,
            "canonical_game_number": canonical_game_number,
            "level": level,
            "quest_completion": quest_completion,
            "kills": kills,
            "deaths": deaths,
            "kill_patron_id": self._KILL_PATRON_ID,
            "kill_patron_name": self._KILL_PATRON_NAME,
            "death_patron_id": self._DEATH_PATRON_ID,
            "death_patron_name": self._DEATH_PATRON_NAME,
            "kd_ratio_milli": kd_ratio_milli,
            "chaos_meter": chaos_meter,
            "akashic_memory_seed": akashic_memory_seed,
            "void_body_mark_hash": void_body_mark_hash,
            "azoth_int": str(azoth_int),
            "b_real": b_real,
            "b_imag": b_imag,
            "max_iter": max_iter,
            "escape_iter": escape_iter,
            "escaped": escaped,
            "orbit_signature_hash": orbit_signature_hash,
            "palette_seed": palette_seed,
            "special_case_rank": special_case_rank,
            "collision_attempt": collision_attempt,
            "fractal": "x^2+b",
            "fixed_scale": self._BREATH_KO_FIXED_SCALE,
        }
        saved = self.create_asset_manifest(
            AssetManifestCreate(
                workspace_id=payload.workspace_id,
                realm_id="lapidus",
                manifest_id=manifest_id,
                name=f"Breath of Ko {payload.actor_id}",
                kind=self._BREATH_KO_KIND,
                payload=breath_payload,
            )
        )
        out = self._breath_ko_from_manifest(saved)
        self._kernel.place(
            raw=f"game.breath.ko.generate {payload.actor_id} {out.breath_id}",
            context={
                "workspace_id": payload.workspace_id,
                "rule": "breath_ko_generate",
                "result": out.model_dump(mode="json"),
            },
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return out

    def emit_dialogue(
        self,
        *,
        payload: DialogueEmitInput,
        actor_id: str,
        workshop_id: str,
    ) -> DialogueEmitOut:
        sorted_turns = sorted(payload.turns, key=lambda turn: turn.line_id)
        emitted_line_ids: list[str] = []
        for turn in sorted_turns:
            context: dict[str, object] = {
                "workspace_id": payload.workspace_id,
                "scene_id": payload.scene_id,
                "dialogue_id": payload.dialogue_id,
                "line_id": turn.line_id,
                "speaker_id": turn.speaker_id,
            }
            if turn.tags:
                context["tags"] = dict(turn.tags)
            if turn.metadata:
                context["metadata"] = dict(turn.metadata)
            self._kernel.place(
                raw=turn.raw,
                context=context,
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
            emitted_line_ids.append(turn.line_id)
        return DialogueEmitOut(
            dialogue_id=payload.dialogue_id,
            scene_id=payload.scene_id,
            emitted=len(emitted_line_ids),
            emitted_line_ids=emitted_line_ids,
        )

    @classmethod
    def _normalize_vitriol_base(cls, raw: Mapping[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for axis in cls._VITRIOL_AXES:
            base_value = int(raw.get(axis, 1))
            normalized[axis] = max(1, min(10, base_value))
        return normalized

    @classmethod
    def _is_modifier_active(cls, modifier: VitriolModifier, current_tick: int) -> bool:
        if modifier.duration_turns <= 0:
            return True
        end_tick = modifier.applied_tick + modifier.duration_turns
        return current_tick < end_tick

    @classmethod
    def _compute_vitriol(
        cls,
        *,
        base: Mapping[str, int],
        modifiers: Sequence[VitriolModifier],
        current_tick: int,
    ) -> tuple[dict[str, int], list[VitriolModifier]]:
        effective = cls._normalize_vitriol_base(base)
        active: list[VitriolModifier] = []
        for modifier in modifiers:
            if not cls._is_modifier_active(modifier, current_tick):
                continue
            active.append(modifier)
            for axis, delta in modifier.delta.items():
                if axis not in effective:
                    continue
                next_value = effective[axis] + int(delta)
                effective[axis] = max(1, min(10, next_value))
        return effective, active

    @classmethod
    def _validate_ruler_delta(cls, ruler_id: str, delta: Mapping[str, int]) -> None:
        normalized_ruler = ruler_id.strip().lower()
        if normalized_ruler not in cls._VITRIOL_RULER_AXIS:
            raise ValueError("invalid_ruler")
        governed_axis = cls._VITRIOL_RULER_AXIS[normalized_ruler]
        invalid_axes = [axis for axis in delta.keys() if axis != governed_axis]
        if invalid_axes:
            raise ValueError("ruler_axis_violation")

    def vitriol_compute(self, *, payload: VitriolComputeInput) -> VitriolComputeOut:
        effective, active_modifiers = self._compute_vitriol(
            base=payload.base,
            modifiers=payload.modifiers,
            current_tick=payload.current_tick,
        )
        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "effective": effective,
            "active_modifiers": [item.model_dump() for item in active_modifiers],
            "current_tick": payload.current_tick,
        }
        return VitriolComputeOut(
            actor_id=payload.actor_id,
            effective=effective,
            active_modifiers=active_modifiers,
            hash=self._canonical_hash(hash_payload),
        )

    def vitriol_apply_ruler_influence(
        self,
        *,
        payload: VitriolApplyRulerInfluenceInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> VitriolApplyOut:
        self._validate_ruler_delta(payload.ruler_id, payload.delta)
        modifier = VitriolModifier(
            source_ruler=payload.ruler_id.strip().lower(),
            delta={axis: int(value) for axis, value in payload.delta.items()},
            reason=payload.reason,
            event_id=payload.event_id,
            applied_tick=payload.applied_tick,
            duration_turns=payload.duration_turns,
        )
        next_modifiers = [*payload.modifiers, modifier]
        effective, active_modifiers = self._compute_vitriol(
            base=payload.base,
            modifiers=next_modifiers,
            current_tick=payload.applied_tick,
        )
        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "effective": effective,
            "active_modifiers": [item.model_dump() for item in active_modifiers],
            "tick": payload.applied_tick,
        }
        result = VitriolApplyOut(
            actor_id=payload.actor_id,
            applied=True,
            modifier=modifier,
            effective=effective,
            active_modifiers=active_modifiers,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.vitriol.apply {payload.actor_id} {modifier.source_ruler}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "vitriol_apply_ruler_influence",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    def vitriol_clear_expired(
        self,
        *,
        payload: VitriolClearExpiredInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> VitriolClearExpiredOut:
        kept: list[VitriolModifier] = [
            modifier for modifier in payload.modifiers if self._is_modifier_active(modifier, payload.current_tick)
        ]
        removed_count = len(payload.modifiers) - len(kept)
        effective, active_modifiers = self._compute_vitriol(
            base=payload.base,
            modifiers=kept,
            current_tick=payload.current_tick,
        )
        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "effective": effective,
            "active_modifiers": [item.model_dump() for item in active_modifiers],
            "current_tick": payload.current_tick,
        }
        result = VitriolClearExpiredOut(
            actor_id=payload.actor_id,
            removed_count=removed_count,
            active_modifiers=active_modifiers,
            effective=effective,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.vitriol.clear_expired {payload.actor_id} removed={removed_count}",
                context={
                    "workspace_id": payload.workspace_id,
                    "rule": "vitriol_clear_expired",
                    "result": result.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return result

    @staticmethod
    def _normalize_frontier_ids(values: Sequence[str]) -> list[str]:
        normalized = sorted({value.strip() for value in values if value.strip() != ""})
        return normalized

    @staticmethod
    def _safe_token(value: str) -> str:
        return "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in value)

    @staticmethod
    def _dict_result(value: object) -> dict[str, object]:
        if hasattr(value, "model_dump"):
            dumped = cast(Any, value).model_dump()
            if isinstance(dumped, dict):
                return cast(dict[str, object], dumped)
        if isinstance(value, dict):
            return cast(dict[str, object], value)
        if isinstance(value, list):
            return {"items": cast(list[object], value)}
        return {"value": cast(object, value)}

    def runtime_action_catalog(self) -> RuntimeActionCatalogOut:
        actions: list[RuntimeActionCatalogItemOut] = [
            RuntimeActionCatalogItemOut(
                kind="levels.apply",
                summary="Apply deterministic level progression.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "xp_delta": "int"},
                example_payload={"xp_delta": 25},
            ),
            RuntimeActionCatalogItemOut(
                kind="skills.train",
                summary="Train a named skill by deterministic delta.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "skill_id": "str", "delta": "int"},
                example_payload={"skill_id": "alchemy", "delta": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="perks.unlock",
                summary="Unlock a perk when requirements are met.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "perk_id": "str"},
                example_payload={"perk_id": "steady_hands"},
            ),
            RuntimeActionCatalogItemOut(
                kind="alchemy.craft",
                summary="Resolve alchemy craft transaction.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "recipe_id": "str"},
                example_payload={"recipe_id": "minor_heal"},
            ),
            RuntimeActionCatalogItemOut(
                kind="blacksmith.forge",
                summary="Resolve blacksmith forging transaction.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "recipe_id": "str"},
                example_payload={"recipe_id": "iron_blade"},
            ),
            RuntimeActionCatalogItemOut(
                kind="combat.resolve",
                summary="Resolve deterministic combat exchange.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "enemy_id": "str"},
                example_payload={"enemy_id": "arena_bandit"},
            ),
            RuntimeActionCatalogItemOut(
                kind="market.quote",
                summary="Compute market quote for side/quantity.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "actor_id": "str", "realm_id": "str", "item_id": "str"},
                example_payload={"realm_id": "lapidus", "item_id": "iron_ingot", "side": "buy", "quantity": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="market.trade",
                summary="Execute market trade with liquidity limits.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "actor_id": "str", "realm_id": "str", "item_id": "str"},
                example_payload={"realm_id": "lapidus", "item_id": "iron_ingot", "side": "buy", "quantity": 2},
            ),
            RuntimeActionCatalogItemOut(
                kind="vitriol.apply",
                summary="Apply ruler modifier to VITRIOL state.",
                payload_fields={"workspace_id": "str", "actor_id": "str", "ruler_id": "str"},
                example_payload={"ruler_id": "asmodeus", "delta": {"vitality": 1}, "applied_tick": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="vitriol.compute",
                summary="Compute effective VITRIOL values from base+modifiers.",
                payload_fields={"base": "dict", "modifiers": "list", "current_tick": "int"},
                example_payload={"base": {"vitality": 7}, "modifiers": [], "current_tick": 1},
            ),
            RuntimeActionCatalogItemOut(
                kind="vitriol.clear",
                summary="Clear expired VITRIOL modifiers by tick.",
                payload_fields={"base": "dict", "modifiers": "list", "current_tick": "int"},
                example_payload={"base": {"vitality": 7}, "modifiers": [], "current_tick": 50},
            ),
            RuntimeActionCatalogItemOut(
                kind="djinn.apply",
                summary="Apply Djinn frontier influence and marks.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "actor_id": "str", "djinn_id": "str", "realm_id": "str"},
                example_payload={"djinn_id": "giann", "realm_id": "lapidus", "scene_id": "lapidus/intro"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.region.load",
                summary="Load one world region into stream state.",
                requires_realm=True,
                payload_fields={
                    "workspace_id": "str",
                    "realm_id": "str",
                    "region_key": "str",
                    "payload": "dict",
                    "bind_render_scene": "bool|optional",
                    "scene_id": "str|optional",
                    "scene_content": "dict|optional",
                },
                example_payload={
                    "realm_id": "lapidus",
                    "region_key": "lapidus/chunk_0_0",
                    "cache_policy": "stream",
                    "bind_render_scene": True,
                    "scene_id": "lapidus/player_home",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="world.region.preload.scenegraph",
                summary="Chunk scenegraph nodes and preload derived regions.",
                requires_realm=True,
                payload_fields={
                    "realm_id": "str",
                    "scene_id": "str",
                    "scene_content": "dict",
                    "chunk_size": "int",
                    "cache_policy": "str",
                },
                example_payload={
                    "realm_id": "lapidus",
                    "scene_id": "lapidus/player_home",
                    "chunk_size": 12,
                    "cache_policy": "stream",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="world.region.unload",
                summary="Unload one region from stream state.",
                requires_realm=True,
                payload_fields={
                    "workspace_id": "str",
                    "realm_id": "str",
                    "region_key": "str",
                    "bind_render_scene": "bool|optional",
                    "scene_id": "str|optional",
                },
                example_payload={
                    "realm_id": "lapidus",
                    "region_key": "lapidus/chunk_0_0",
                    "bind_render_scene": True,
                    "scene_id": "lapidus/player_home",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="world.stream.status",
                summary="Inspect stream occupancy/capacity and policy counts.",
                requires_realm=True,
                payload_fields={"workspace_id": "str", "realm_id": "str"},
                example_payload={"realm_id": "lapidus"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.coins.list",
                summary="List realm currencies.",
                requires_realm=False,
                payload_fields={"realm_id": "str(optional)"},
                example_payload={},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.markets.list",
                summary="List realm market profiles/stocks.",
                requires_realm=False,
                payload_fields={"realm_id": "str(optional)"},
                example_payload={"realm_id": "lapidus"},
            ),
            RuntimeActionCatalogItemOut(
                kind="world.market.stock.adjust",
                summary="Override market stock during runtime plan.",
                requires_realm=True,
                payload_fields={
                    "realm_id": "str",
                    "item_id": "str",
                    "delta": "int|optional",
                    "set_qty": "int|optional",
                    "use_breath_context": "bool|optional",
                    "influence_bp": "int|optional",
                    "royl_loyalty": "int(0..100)|optional (Lapidus)",
                },
                example_payload={
                    "realm_id": "lapidus",
                    "item_id": "iron_ingot",
                    "delta": 5,
                    "use_breath_context": True,
                    "influence_bp": 5000,
                    "royl_loyalty": 80,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="world.market.sovereignty.transition",
                summary="Apply market control transition + redistribution policy.",
                requires_realm=True,
                payload_fields={"realm_id": "str", "overthrow": "bool", "victor_id": "str"},
                example_payload={"realm_id": "lapidus", "overthrow": True, "victor_id": "player_commonwealth"},
            ),
            RuntimeActionCatalogItemOut(
                kind="breath.ko.evaluate",
                summary="Evaluate Breath of Ko state for runtime decisions and persist flags.",
                payload_fields={
                    "workspace_id": "str",
                    "actor_id": "str",
                    "player_name": "str|optional",
                    "canonical_game_number": "int|optional",
                    "quest_completion": "int|optional",
                    "kills": "int|optional",
                    "deaths": "int|optional",
                },
                example_payload={
                    "player_name": "Kael",
                    "canonical_game_number": 42,
                    "quest_completion": 73,
                    "kills": 3,
                    "deaths": 6,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="sanity.adjust",
                summary="Adjust four sanity channels (alchemical, terrestrial, cosmic, narrative).",
                payload_fields={
                    "delta": "dict[str,int]|optional",
                    "set": "dict[str,int]|optional",
                },
                example_payload={"delta": {"cosmic": -5, "narrative": 3}},
            ),
            RuntimeActionCatalogItemOut(
                kind="radio.evaluate",
                summary="Evaluate radio availability from underworld state.",
                payload_fields={"underworld_state": "str", "override_available": "bool|optional"},
                example_payload={"underworld_state": "active"},
            ),
            RuntimeActionCatalogItemOut(
                kind="alchemy.crystal",
                summary="Craft radio or asmodian key crystals.",
                payload_fields={"crystal_type": "str", "purity": "int", "ingredients": "dict", "outputs": "dict", "inventory": "dict"},
                example_payload={"crystal_type": "asmodian", "purity": 100, "ingredients": {"ore": 1}, "outputs": {"asmodian_crystal": 1}},
            ),
            RuntimeActionCatalogItemOut(
                kind="infernal_meditation.unlock",
                summary="Unlock Infernal Meditation (Alfir, Castle Azoth Library restricted section at night).",
                payload_fields={"mentor": "str", "location": "str", "section": "str", "time_of_day": "str"},
                example_payload={"mentor": "Alfir", "location": "Castle Azoth Library", "section": "restricted", "time_of_day": "night"},
            ),
            RuntimeActionCatalogItemOut(
                kind="faction.loyalty.adjust",
                summary="Adjust faction loyalty score (0..100), e.g. ROYL.",
                payload_fields={"faction_id": "str", "delta": "int|optional", "set_score": "int|optional"},
                example_payload={"faction_id": "royl", "delta": 8},
            ),
            RuntimeActionCatalogItemOut(
                kind="underworld.access.evaluate",
                summary="Compute Underworld ring access from infernal meditation, trials, and asmodian purity.",
                payload_fields={
                    "infernal_meditation": "bool|optional",
                    "vitriol_trials_cleared": "bool|optional",
                    "asmodian_purity": "int|optional",
                },
                example_payload={"infernal_meditation": True, "vitriol_trials_cleared": True, "asmodian_purity": 100},
            ),
            RuntimeActionCatalogItemOut(
                kind="affiliation.assign",
                summary="Assign actor Fae/social affiliations and realm bindings.",
                payload_fields={
                    "fae_kind": "str|optional (undines,salamanders,dryads,faeries,gnomes)",
                    "social_class": "str|optional (assassins,nobles,royals,townsfolk,merchants,gods)",
                    "realm_bindings": "list[str]",
                },
                example_payload={"fae_kind": "undines", "social_class": "townsfolk", "realm_bindings": ["mercurie"]},
            ),
            RuntimeActionCatalogItemOut(
                kind="quest.advance_by_graph",
                summary="Advance quest deterministically using latest or specified quest graph.",
                payload_fields={
                    "workspace_id": "str",
                    "actor_id": "str",
                    "quest_id": "str",
                    "from_step_id": "str|optional",
                    "graph_version": "str|optional",
                    "dry_run": "bool|optional",
                },
                example_payload={
                    "workspace_id": "main",
                    "actor_id": "player",
                    "quest_id": "main_story",
                    "from_step_id": "intro",
                    "dry_run": False,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="quest.fate_knocks.bootstrap",
                summary="Bootstrap Day 1 opening for Fate Knocks including quiz budget/VITRIOL mapping and Castle Azoth deadline.",
                payload_fields={
                    "player_name": "str",
                    "player_gender": "str",
                    "month": "str|optional (default Shyalz)",
                    "deadline_hour_local": "int|optional (default 19)",
                    "quiz_points_budget": "int|optional (default 28)",
                    "quiz_min_per_answer": "int|optional (default 1)",
                    "quiz_max_per_answer": "int|optional (default 10)",
                    "vitriol_answers": "list[int]|optional (len 7, sum == budget)",
                    "non_vitriol_answers": "dict|optional ({perk_answers[3], skill_aptitude_answers[3], power_answer, finance_answer})",
                    "quiz_answers": "list[int]|optional legacy fallback",
                },
                example_payload={
                    "player_name": "Kael",
                    "player_gender": "nonbinary",
                    "month": "Shyalz",
                    "deadline_hour_local": 19,
                    "quiz_points_budget": 28,
                    "quiz_min_per_answer": 1,
                    "quiz_max_per_answer": 10,
                    "vitriol_answers": [4, 4, 4, 4, 4, 4, 4],
                    "non_vitriol_answers": {
                        "perk_answers": ["Iron Skin", "Flashbulb Memory", "None"],
                        "skill_aptitude_answers": ["focused", "disciplined", "novice"],
                        "power_answer": "service before dominion",
                        "finance_answer": "redistribution with stable trade",
                    },
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="quest.fate_knocks.deadline_check",
                summary="Evaluate Castle Azoth report deadline and revoke stipend if missed.",
                payload_fields={
                    "current_hour_local": "int|optional (falls back to player clock hour_local)",
                },
                example_payload={"current_hour_local": 20},
            ),
            RuntimeActionCatalogItemOut(
                kind="quest.fate_knocks.report_to_castle",
                summary="Resolve Fate Knocks by reporting to Castle Azoth and meeting Hypatia.",
                payload_fields={
                    "scene_id": "str|optional (default lapidus/castle_evening)",
                    "met_hypatia": "bool|optional (default true)",
                    "current_hour_local": "int|optional (default 19)",
                },
                example_payload={
                    "scene_id": "lapidus/castle_evening",
                    "met_hypatia": True,
                    "current_hour_local": 19,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="dungeon.enter",
                summary="Enter a dungeon run deterministically per-entry, generated in-memory only for current runtime execution.",
                payload_fields={
                    "dungeon_id": "str",
                    "player_level": "int|optional",
                    "quest_progress": "int|optional",
                    "entry_nonce": "str|optional",
                    "run_label": "str|optional",
                },
                example_payload={
                    "dungeon_id": "sulphera/pride",
                    "player_level": 4,
                    "quest_progress": 2,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="dungeon.generate",
                summary="Generate deterministic dungeon scaffold and multifaceted cypher (visual/text/alchemical/Shygazun) without entering active run.",
                payload_fields={
                    "dungeon_id": "str",
                    "player_level": "int|optional",
                    "quest_progress": "int|optional",
                    "entry_ordinal": "int|optional",
                },
                example_payload={
                    "dungeon_id": "mercurie/zone_tideglass",
                    "player_level": 6,
                    "quest_progress": 9,
                    "entry_ordinal": 3,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="dungeon.complete",
                summary="Resolve active dungeon as complete, reveal full key material, and persist success meta-progression.",
                payload_fields={
                    "dungeon_id": "str",
                    "run_id": "str|optional",
                },
                example_payload={
                    "dungeon_id": "sulphera/pride",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="dungeon.fail",
                summary="Resolve active dungeon as failed with partial retention meta-progression.",
                payload_fields={
                    "dungeon_id": "str",
                    "run_id": "str|optional",
                    "retention_ratio_bp": "int|optional (default 2500)",
                },
                example_payload={
                    "dungeon_id": "sulphera/pride",
                    "retention_ratio_bp": 2500,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="dungeon.decode",
                summary="Derive deterministic final text key formula and contextual Shygazun byte sequence from collected key shards.",
                payload_fields={
                    "dungeon_id": "str",
                    "run_id": "str|optional",
                },
                example_payload={
                    "dungeon_id": "sulphera/pride",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="shygazun.interpret",
                summary="Interpret Shygazun text under Jabiru with deterministic Kaganue confusion pressure.",
                payload_fields={
                    "utterance": "str",
                    "deity": "str|optional (default jabiru)",
                    "mode": "str|optional",
                    "kaganue_pressure": "float(0..1)|optional",
                    "mutate_tokens": "bool|optional",
                    "explain_mode": "str|optional (none|compound|full)",
                    "lore_overlay": "str|optional (none|anecdotal)",
                },
                example_payload={
                    "utterance": "entity hearth 4 2 furnace lex TyKoWuVu",
                    "deity": "jabiru",
                    "mode": "explicit",
                    "kaganue_pressure": 0.25,
                    "explain_mode": "compound",
                    "lore_overlay": "anecdotal",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="shygazun.translate",
                summary="Deterministic Phase-1 lexicon translator for English <-> Shygazun.",
                payload_fields={
                    "source_text": "str",
                    "direction": "str|optional (auto|english_to_shygazun|shygazun_to_english)",
                },
                example_payload={
                    "source_text": "love whale",
                    "direction": "english_to_shygazun",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="shygazun.correct",
                summary="Canonicalize Shygazun token casing/segmentation with deterministic symbol lookup.",
                payload_fields={
                    "source_text": "str",
                },
                example_payload={
                    "source_text": "tykowuvu aely ta zo",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="math.numeral_3d",
                summary="Compute base-ring 3D numeral projection and lineage references.",
                payload_fields={
                    "workspace_id": "str",
                    "actor_id": "str",
                    "x": "int",
                    "y": "int",
                    "z": "int",
                    "ring_base": "int|optional (default 12)",
                },
                example_payload={"workspace_id": "main", "actor_id": "player", "x": 3, "y": 5, "z": 2, "ring_base": 12},
            ),
            RuntimeActionCatalogItemOut(
                kind="math.fibonacci_ordering",
                summary="Compute deterministic Fibonacci ordering with optional prime-index boost.",
                payload_fields={
                    "workspace_id": "str",
                    "actor_id": "str",
                    "item_ids": "list[str]",
                    "ring_base": "int|optional (default 12)",
                    "prioritize_primes": "bool|optional",
                },
                example_payload={
                    "workspace_id": "main",
                    "actor_id": "player",
                    "item_ids": ["market", "alchemy", "combat", "dialogue"],
                    "ring_base": 12,
                    "prioritize_primes": True,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="audio.cue.stage",
                summary="Stage an audio cue in deterministic runtime state from file/asset metadata.",
                payload_fields={
                    "cue_id": "str",
                    "filename": "str",
                    "channel": "str|optional",
                    "loop": "bool|optional",
                    "gain": "float(0..2)|optional",
                    "start_ms": "int|optional",
                },
                example_payload={
                    "cue_id": "sfx_door_open",
                    "filename": "sfx/door_open.wav",
                    "channel": "sfx",
                    "loop": False,
                    "gain": 1.0,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="audio.cue.play",
                summary="Emit deterministic play command for a staged audio cue.",
                payload_fields={
                    "cue_id": "str",
                    "channel": "str|optional",
                    "loop": "bool|optional",
                    "gain": "float(0..2)|optional",
                    "start_ms": "int|optional",
                },
                example_payload={
                    "cue_id": "sfx_door_open",
                    "channel": "sfx",
                    "loop": False,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="audio.cue.stop",
                summary="Emit deterministic stop command for one cue or full channel.",
                payload_fields={
                    "cue_id": "str|optional",
                    "channel": "str|optional",
                    "all": "bool|optional",
                },
                example_payload={
                    "channel": "music",
                    "all": True,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="render.scene.load",
                summary="Load a scenegraph into deterministic renderer runtime state.",
                requires_realm=True,
                payload_fields={"realm_id": "str", "scene_id": "str", "scene_content": "dict|optional"},
                example_payload={"realm_id": "lapidus", "scene_id": "lapidus/player_home"},
            ),
            RuntimeActionCatalogItemOut(
                kind="render.scene.tick",
                summary="Advance renderer runtime tick and apply deterministic entity updates.",
                payload_fields={
                    "dt": "int|optional",
                    "updates": "list[dict]|optional",
                    "enqueue_pygame": "bool|optional",
                    "pygame_command_kind": "str|optional",
                },
                example_payload={
                    "dt": 1,
                    "updates": [{"scene_id": "lapidus/player_home", "entity_id": "npc_1", "x": 5, "y": 2}],
                    "enqueue_pygame": True,
                    "pygame_command_kind": "render_scene_tick_delta",
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="render.scene.unload",
                summary="Unload a scenegraph from renderer runtime state.",
                requires_realm=True,
                payload_fields={"realm_id": "str", "scene_id": "str"},
                example_payload={"realm_id": "lapidus", "scene_id": "lapidus/player_home"},
            ),
            RuntimeActionCatalogItemOut(
                kind="render.scene.reconcile",
                summary="Reconcile scene identities and placements against expected scenegraph.",
                requires_realm=True,
                payload_fields={"realm_id": "str", "scene_id": "str", "scene_content": "dict|optional", "apply": "bool|optional"},
                example_payload={"realm_id": "lapidus", "scene_id": "lapidus/player_home", "apply": True},
            ),
            RuntimeActionCatalogItemOut(
                kind="pygame.worker.enqueue",
                summary="Enqueue a command for the isolated pygame worker manager.",
                payload_fields={
                    "command_kind": "str|optional (default runtime_action.forward)",
                    "runtime_action_kind": "str",
                    "payload": "dict|optional",
                },
                example_payload={
                    "command_kind": "runtime_action.forward",
                    "runtime_action_kind": "audio.cue.play",
                    "payload": {"cue_id": "sfx_door_open", "channel": "sfx"},
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="pygame.worker.status",
                summary="Return queue/availability status for the isolated pygame worker manager.",
                payload_fields={},
                example_payload={},
            ),
            RuntimeActionCatalogItemOut(
                kind="pygame.worker.dequeue",
                summary="Dequeue one or more pending commands from the isolated pygame worker manager.",
                payload_fields={
                    "max_items": "int|optional (default 1, max 256)",
                },
                example_payload={"max_items": 16},
            ),
            RuntimeActionCatalogItemOut(
                kind="content.pack.load_canon",
                summary="Load canonical content pack files and hydrate DB/player-state defaults deterministically.",
                payload_fields={
                    "pack_dir": "str|optional (default gameplay/content_packs/canon)",
                    "apply_to_db": "bool|optional (default true)",
                    "actor_id": "str|optional (defaults runtime actor_id)",
                },
                example_payload={
                    "pack_dir": "gameplay/content_packs/canon",
                    "apply_to_db": True,
                },
            ),
            RuntimeActionCatalogItemOut(
                kind="content.pack.load_byte_table",
                summary="Materialize full Shygazun byte table into 12-layer lineage nodes/edges.",
                payload_fields={},
                example_payload={},
            ),
            RuntimeActionCatalogItemOut(
                kind="module.run",
                summary="Run a module spec from gameplay/modules and enforce expected lineage refs.",
                payload_fields={
                    "module_id": "str",
                    "module_version": "str|optional",
                    "payload_overrides": "dict|optional",
                },
                example_payload={
                    "module_id": "module.shygazun.interpret",
                    "module_version": "v1",
                    "payload_overrides": {"kaganue_pressure": 0.15},
                },
            ),
        ]
        return RuntimeActionCatalogOut(action_count=len(actions), actions=actions)

    def consume_runtime_plan(
        self,
        *,
        payload: RuntimeConsumeInput,
        actor_id: str,
        workshop_id: str,
    ) -> RuntimeConsumeOut:
        results: list[RuntimeActionOut] = []
        runtime_regions: dict[str, dict[str, object]] = {}
        runtime_market_stock: dict[str, dict[str, int]] = {}
        runtime_market_meta: dict[str, dict[str, object]] = {}
        runtime_breath_context: dict[str, dict[str, object]] = {}
        runtime_sanity_state: dict[str, dict[str, int]] = {}
        runtime_flags_state: dict[str, dict[str, object]] = {}
        runtime_render_state: dict[str, object] = {
            "tick": 0,
            "loaded_scenes": {},
            "entities": {},
            "placement_index": {},
        }
        runtime_scene_clock_state: dict[str, object] = {
            "scene_minutes_total": 0,
            "scene_advances_count": 0,
            "last_scene_id": "",
            "last_clock_advance": 0,
        }
        runtime_audio_state: dict[str, object] = {
            "tick": 0,
            "commands_emitted": 0,
            "staged_cues": {},
            "last_command": {},
        }
        runtime_dungeon_state: dict[str, object] = {
            "active_runs": {},
            "entry_counters": {},
            "meta": {},
        }

        def _normalize_realm_for_runtime(value: object) -> str:
            realm = str(value or "").strip().lower()
            if realm == "":
                raise ValueError("realm_id_required")
            return realm

        def _render_scene_key(realm_id: str, scene_id: str) -> str:
            return f"{realm_id}::{scene_id}"

        def _render_identity(scene_key: str, entity_id: str) -> str:
            return f"{scene_key}::{entity_id}"

        def _render_state_maps() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]], dict[str, str], int]:
            loaded_obj = runtime_render_state.get("loaded_scenes")
            entities_obj = runtime_render_state.get("entities")
            placement_obj = runtime_render_state.get("placement_index")
            tick_val = self._int_from_table(runtime_render_state.get("tick"), 0)
            loaded = cast(dict[str, dict[str, object]], loaded_obj) if isinstance(loaded_obj, dict) else {}
            entities = cast(dict[str, dict[str, object]], entities_obj) if isinstance(entities_obj, dict) else {}
            placement = cast(dict[str, str], placement_obj) if isinstance(placement_obj, dict) else {}
            runtime_render_state["loaded_scenes"] = loaded
            runtime_render_state["entities"] = entities
            runtime_render_state["placement_index"] = placement
            runtime_render_state["tick"] = tick_val
            return loaded, entities, placement, tick_val

        def _render_summary() -> dict[str, object]:
            loaded, entities, placement, tick_val = _render_state_maps()
            return {
                "tick": tick_val,
                "loaded_scene_count": len(loaded),
                "entity_count": len(entities),
                "placement_count": len(placement),
            }

        def _scene_clock_summary() -> dict[str, object]:
            return {
                "scene_minutes_total": self._int_from_table(runtime_scene_clock_state.get("scene_minutes_total"), 0),
                "scene_advances_count": self._int_from_table(runtime_scene_clock_state.get("scene_advances_count"), 0),
                "last_scene_id": str(runtime_scene_clock_state.get("last_scene_id", "")),
                "last_clock_advance": self._int_from_table(runtime_scene_clock_state.get("last_clock_advance"), 0),
            }

        def _enforce_scene_clock_policy(action_kind: str, action_payload: Mapping[str, object]) -> None:
            guarded_fields = ("clock_advance", "game_clock", "advance_minutes", "advance_hours", "dt_ms")
            if action_kind != "render.scene.tick":
                violating = sorted([field for field in guarded_fields if field in action_payload])
                if len(violating) > 0:
                    raise ValueError(f"scene_clock_mutation_disallowed:{','.join(violating)}")
                return
            scene_id = str(action_payload.get("scene_id", "")).strip()
            if scene_id == "":
                raise ValueError("scene_id_required_for_scene_tick")
            if "clock_advance" not in action_payload:
                raise ValueError("clock_advance_required_for_scene_tick")
            clock_advance = self._int_from_table(action_payload.get("clock_advance"), -1)
            if clock_advance < 0:
                raise ValueError("clock_advance_must_be_non_negative")

        def _audio_maps() -> tuple[dict[str, dict[str, object]], int, int]:
            staged_obj = runtime_audio_state.get("staged_cues")
            staged = cast(dict[str, dict[str, object]], staged_obj) if isinstance(staged_obj, dict) else {}
            tick_val = self._int_from_table(runtime_audio_state.get("tick"), 0)
            emitted = self._int_from_table(runtime_audio_state.get("commands_emitted"), 0)
            runtime_audio_state["staged_cues"] = staged
            runtime_audio_state["tick"] = tick_val
            runtime_audio_state["commands_emitted"] = emitted
            return staged, tick_val, emitted

        def _audio_summary() -> dict[str, object]:
            staged, tick_val, emitted = _audio_maps()
            return {
                "tick": tick_val,
                "staged_count": len(staged),
                "commands_emitted": emitted,
                "last_command": runtime_audio_state.get("last_command", {}),
            }

        def _audio_channel(value: object) -> str:
            channel = str(value or "sfx").strip().lower()
            return channel if channel != "" else "sfx"

        def _audio_gain(value: object, fallback: float = 1.0) -> float:
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                parsed = fallback
            return max(0.0, min(2.0, parsed))

        def _dungeon_maps() -> tuple[dict[str, dict[str, object]], dict[str, int], dict[str, dict[str, object]]]:
            active_obj = runtime_dungeon_state.get("active_runs")
            counters_obj = runtime_dungeon_state.get("entry_counters")
            meta_obj = runtime_dungeon_state.get("meta")
            active = cast(dict[str, dict[str, object]], active_obj) if isinstance(active_obj, dict) else {}
            counters = cast(dict[str, int], counters_obj) if isinstance(counters_obj, dict) else {}
            meta = cast(dict[str, dict[str, object]], meta_obj) if isinstance(meta_obj, dict) else {}
            runtime_dungeon_state["active_runs"] = active
            runtime_dungeon_state["entry_counters"] = counters
            runtime_dungeon_state["meta"] = meta
            return active, counters, meta

        def _normalize_dungeon_id(value: object) -> str:
            dungeon_id = str(value or "").strip().lower()
            if dungeon_id == "":
                raise ValueError("dungeon_id_required")
            return dungeon_id

        def _dungeon_registry_row(dungeon_id: str) -> dict[str, object]:
            if dungeon_id in {f"sulphera/{ring}" for ring in self._UNDERWORLD_RING_ORDER}:
                ring = dungeon_id.split("/", 1)[1]
                return {
                    "realm_id": "sulphera",
                    "domain_type": "ring",
                    "domain_id": ring,
                    "ruler": self._SULPHERA_RING_RULERS.get(ring, "unknown"),
                    "hostile": ring not in {"visitors", "royalty"},
                    "time_scale_to_lapidus": 24,
                }
            if dungeon_id in {f"mercurie/{zone}" for zone in self._MERCURIE_DUNGEON_ZONES}:
                zone = dungeon_id.split("/", 1)[1]
                return {
                    "realm_id": "mercurie",
                    "domain_type": "zone",
                    "domain_id": zone,
                    "ruler": "fae_courts",
                    "hostile": True,
                    "time_scale_to_lapidus": 3,
                }
            if dungeon_id == "lapidus/lapidus_mines_mt_hieronymus":
                return {
                    "realm_id": "lapidus",
                    "domain_type": "mine",
                    "domain_id": "lapidus_mines_mt_hieronymus",
                    "ruler": "guild_charter",
                    "hostile": False,
                    "time_scale_to_lapidus": 1,
                }
            raise ValueError("unknown_dungeon_id")

        def _dungeon_seed_hash(
            *,
            dungeon_id: str,
            entry_ordinal: int,
            player_level: int,
            quest_progress: int,
            actor_id_for_seed: str,
            workspace_id_for_seed: str,
            entry_nonce: str,
        ) -> str:
            return self._canonical_hash(
                {
                    "workspace_id": workspace_id_for_seed,
                    "actor_id": actor_id_for_seed,
                    "dungeon_id": dungeon_id,
                    "entry_ordinal": entry_ordinal,
                    "player_level": player_level,
                    "quest_progress": quest_progress,
                    "entry_nonce": entry_nonce,
                }
            )

        def _seed_int(seed_hash: str, label: str, *, modulo: int, offset: int = 0) -> int:
            if modulo <= 0:
                raise ValueError("modulo_must_be_positive")
            digest = hashlib.sha256(f"{seed_hash}:{label}".encode("utf-8")).hexdigest()
            return offset + (int(digest[:12], 16) % modulo)

        def _dungeon_generate(
            *,
            dungeon_id: str,
            player_level: int,
            quest_progress: int,
            entry_ordinal: int,
            actor_key: str,
            entry_nonce: str,
            run_label: str,
        ) -> dict[str, object]:
            row = _dungeon_registry_row(dungeon_id)
            seed_hash = _dungeon_seed_hash(
                dungeon_id=dungeon_id,
                entry_ordinal=entry_ordinal,
                player_level=player_level,
                quest_progress=quest_progress,
                actor_id_for_seed=actor_key,
                workspace_id_for_seed=payload.workspace_id,
                entry_nonce=entry_nonce,
            )
            realm_id = str(row.get("realm_id"))
            hostile = bool(row.get("hostile", True))
            floor_count = 2 + _seed_int(seed_hash, "floor_count", modulo=4)
            rooms_per_floor = 6 + _seed_int(seed_hash, "rooms_per_floor", modulo=7)
            difficulty_tier = max(1, min(20, 1 + (player_level // 2) + (quest_progress // 4)))
            enemy_density_bp = 0 if not hostile else max(1000, min(9500, 2200 + difficulty_tier * 250))
            if difficulty_tier <= 4:
                shard_min, shard_max = 4, 6
            elif difficulty_tier <= 10:
                shard_min, shard_max = 6, 7
            else:
                shard_min, shard_max = 7, 8
            cypher_shard_count = shard_min + _seed_int(
                seed_hash,
                "cypher_shard_count_clamped",
                modulo=(shard_max - shard_min + 1),
            )
            base_bytes = [28, 17, 10, 45, 63, 72, 90, 109, 111]
            shard_rows: list[dict[str, object]] = []
            for index in range(cypher_shard_count):
                shard_hash = hashlib.sha256(f"{seed_hash}:shard:{index}".encode("utf-8")).hexdigest()
                text_key = shard_hash[:8].upper()
                visual_key = f"glyph_{shard_hash[8:12]}"
                byte_a = base_bytes[_seed_int(seed_hash, f"b{index}a", modulo=len(base_bytes))]
                byte_b = base_bytes[_seed_int(seed_hash, f"b{index}b", modulo=len(base_bytes))]
                alchemical_formula = f"{text_key}:{visual_key}:{byte_a:03d}-{byte_b:03d}"
                shard_rows.append(
                    {
                        "shard_id": f"{dungeon_id.replace('/', '_')}_shard_{index + 1}",
                        "textual_key_fragment": text_key,
                        "visual_key_fragment": visual_key,
                        "shygazun_byte_sequence": [byte_a, byte_b],
                        "alchemical_formula_fragment": alchemical_formula,
                    }
                )
            shard_rows = sorted(shard_rows, key=lambda item: str(item.get("shard_id", "")))
            if realm_id == "lapidus":
                population = {
                    "hostile_entities": [],
                    "neutral_entities": ["gnome_miners", "child_laborers", "foreman"],
                    "resource_nodes": [
                        "iron_vein",
                        "silver_vein",
                        "coal_seam",
                        "saltpeter_deposit",
                        "sulphur_pocket",
                    ],
                }
            else:
                enemy_count = max(2, (floor_count * rooms_per_floor * enemy_density_bp) // 10000)
                population = {
                    "hostile_entities": [f"enemy_{idx+1}" for idx in range(enemy_count)],
                    "neutral_entities": [],
                    "resource_nodes": [f"node_{idx+1}" for idx in range(max(3, floor_count))],
                }
            run_id = f"run:{self._safe_token(dungeon_id)}:{entry_ordinal}:{seed_hash[:10]}"
            return {
                "run_id": run_id,
                "run_label": run_label if run_label != "" else f"{dungeon_id}#{entry_ordinal}",
                "workspace_id": payload.workspace_id,
                "actor_id": actor_key,
                "dungeon_id": dungeon_id,
                "realm_id": realm_id,
                "domain_type": str(row.get("domain_type", "")),
                "domain_id": str(row.get("domain_id", "")),
                "ruler": str(row.get("ruler", "")),
                "hostile": hostile,
                "entry_ordinal": entry_ordinal,
                "player_level": player_level,
                "quest_progress": quest_progress,
                "difficulty_tier": difficulty_tier,
                "time_scale_to_lapidus": int(row.get("time_scale_to_lapidus", 1)),
                "floor_count": floor_count,
                "rooms_per_floor": rooms_per_floor,
                "enemy_density_bp": enemy_density_bp,
                "population": population,
                "cypher_shards": shard_rows,
                "seed_hash": seed_hash,
                "in_memory_only": True,
                "status": "active",
            }

        def _dungeon_decode_payload(run: Mapping[str, object]) -> dict[str, object]:
            shard_rows_obj = run.get("cypher_shards")
            shard_rows = shard_rows_obj if isinstance(shard_rows_obj, list) else []
            text_parts: list[str] = []
            visual_parts: list[str] = []
            byte_sequence: list[int] = []
            formula_parts: list[str] = []
            for shard in shard_rows:
                if not isinstance(shard, dict):
                    continue
                text_parts.append(str(shard.get("textual_key_fragment", "")))
                visual_parts.append(str(shard.get("visual_key_fragment", "")))
                bytes_obj = shard.get("shygazun_byte_sequence")
                if isinstance(bytes_obj, list):
                    for b in bytes_obj:
                        byte_sequence.append(max(0, min(255, self._int_from_table(b, 0))))
                formula_parts.append(str(shard.get("alchemical_formula_fragment", "")))
            key_text = "-".join([part for part in text_parts if part != ""])
            visual_signature = ".".join([part for part in visual_parts if part != ""])
            formula = " + ".join([part for part in formula_parts if part != ""])
            semantic_context = {
                "dungeon_id": str(run.get("dungeon_id", "")),
                "realm_id": str(run.get("realm_id", "")),
                "ruler": str(run.get("ruler", "")),
                "difficulty_tier": self._int_from_table(run.get("difficulty_tier"), 1),
            }
            return {
                "text_key": key_text,
                "visual_key_signature": visual_signature,
                "shygazun_byte_sequence": byte_sequence,
                "semantic_context": semantic_context,
                "alchemical_formula": formula,
                "decode_hash": self._canonical_hash(
                    {
                        "text_key": key_text,
                        "visual_key_signature": visual_signature,
                        "shygazun_byte_sequence": byte_sequence,
                        "semantic_context": semantic_context,
                        "alchemical_formula": formula,
                    }
                ),
            }

        def _dungeon_meta_load(actor_key: str) -> dict[str, object]:
            _, _, meta = _dungeon_maps()
            existing = meta.get(actor_key)
            if isinstance(existing, dict):
                return dict(existing)
            loaded: dict[str, object] = {"entries": {}, "completed": {}, "failed": {}, "retained": {}}
            if self._repo is not None:
                state = self.get_player_state(workspace_id=payload.workspace_id, actor_id=actor_key)
                flags = self._dict_from_table(state.tables.flags)
                dungeon_meta_obj = flags.get("dungeon_meta")
                if isinstance(dungeon_meta_obj, dict):
                    loaded = {
                        "entries": dict(cast(dict[str, object], dungeon_meta_obj.get("entries", {}))),
                        "completed": dict(cast(dict[str, object], dungeon_meta_obj.get("completed", {}))),
                        "failed": dict(cast(dict[str, object], dungeon_meta_obj.get("failed", {}))),
                        "retained": dict(cast(dict[str, object], dungeon_meta_obj.get("retained", {}))),
                    }
            meta[actor_key] = loaded
            return dict(loaded)

        def _dungeon_meta_save(actor_key: str, meta_value: Mapping[str, object]) -> None:
            _, _, meta = _dungeon_maps()
            serial = {
                "entries": dict(cast(dict[str, object], meta_value.get("entries", {}))),
                "completed": dict(cast(dict[str, object], meta_value.get("completed", {}))),
                "failed": dict(cast(dict[str, object], meta_value.get("failed", {}))),
                "retained": dict(cast(dict[str, object], meta_value.get("retained", {}))),
            }
            meta[actor_key] = serial
            if self._repo is None:
                return
            state = self.get_player_state(workspace_id=payload.workspace_id, actor_id=actor_key)
            flags = self._dict_from_table(state.tables.flags)
            flags["dungeon_meta"] = serial
            self.apply_player_state(
                payload=PlayerStateApplyInput(
                    workspace_id=payload.workspace_id,
                    actor_id=actor_key,
                    tables=PlayerStateTables(flags=flags),
                    mode="merge",
                ),
                actor_id=actor_id,
                workshop_id=workshop_id,
            )

        def _load_scene_content_for_runtime(action_payload: Mapping[str, object]) -> tuple[str, str, dict[str, object]]:
            realm_id = str(action_payload.get("realm_id", "")).strip().lower()
            scene_id = str(action_payload.get("scene_id", "")).strip()
            content_obj = action_payload.get("scene_content")
            scene_content = cast(dict[str, object], content_obj) if isinstance(content_obj, dict) else None
            if scene_content is None:
                if realm_id == "" or scene_id == "":
                    raise ValueError("scene_content_or_realm_scene_required")
                scene_row = self.get_scene(
                    workspace_id=payload.workspace_id,
                    realm_id=realm_id,
                    scene_id=scene_id,
                )
                if scene_row is None:
                    raise ValueError("scene_not_found")
                scene_content = scene_row.content
            if scene_content is None:
                raise ValueError("scene_content_required")
            if realm_id == "":
                realm_id = str(scene_content.get("realm_id", "")).strip().lower()
            if scene_id == "":
                scene_id = str(scene_content.get("scene_id", "")).strip()
            if realm_id == "" or scene_id == "":
                raise ValueError("realm_or_scene_required")
            return realm_id, scene_id, scene_content

        def _extract_scene_entities(scene_content: Mapping[str, object], scene_id: str) -> list[dict[str, object]]:
            nodes_obj = scene_content.get("nodes")
            nodes = nodes_obj if isinstance(nodes_obj, list) else []
            out: list[dict[str, object]] = []
            for node_index, node in enumerate(nodes):
                if not isinstance(node, dict):
                    continue
                node_id = str(node.get("node_id") or f"node_{node_index}")
                kind = str(node.get("kind") or "entity")
                x = float(node.get("x") or 0.0)
                y = float(node.get("y") or 0.0)
                metadata_obj = node.get("metadata")
                metadata = cast(dict[str, object], metadata_obj) if isinstance(metadata_obj, dict) else {}
                self._resolve_aster_metadata(metadata)
                z = self._int_from_table(metadata.get("z"), 0)
                placement_id = str(metadata.get("placement_id") or f"{scene_id}:{node_id}")
                out.append(
                    {
                        "entity_id": node_id,
                        "kind": kind,
                        "x": x,
                        "y": y,
                        "z": z,
                        "metadata": dict(metadata),
                        "placement_id": placement_id,
                    }
                )
            out.sort(key=lambda item: (str(item.get("entity_id", "")), str(item.get("placement_id", ""))))
            return out

        def _render_scene_load(action_payload: Mapping[str, object]) -> dict[str, object]:
            loaded_scenes, entities, placement_index, tick_val = _render_state_maps()
            realm_id, scene_id, scene_content = _load_scene_content_for_runtime(action_payload)
            scene_key = _render_scene_key(realm_id, scene_id)
            scene_entities = _extract_scene_entities(scene_content, scene_id)
            previous_scene = loaded_scenes.get(scene_key, {})
            previous_ids_obj = previous_scene.get("entity_ids")
            previous_ids = [str(item) for item in previous_ids_obj] if isinstance(previous_ids_obj, list) else []
            for identity in previous_ids:
                row = entities.pop(identity, None)
                if isinstance(row, dict):
                    placement_id = str(row.get("placement_id", "")).strip()
                    if placement_id != "":
                        placement_index.pop(placement_id, None)
            upserted = 0
            replaced = len(previous_ids)
            identity_ids: list[str] = []
            for item in scene_entities:
                identity = _render_identity(scene_key, str(item.get("entity_id", "")))
                entities[identity] = {
                    "identity": identity,
                    "scene_key": scene_key,
                    "realm_id": realm_id,
                    "scene_id": scene_id,
                    **item,
                }
                placement_id = str(item.get("placement_id", "")).strip()
                if placement_id != "":
                    placement_index[placement_id] = identity
                identity_ids.append(identity)
                upserted += 1
            loaded_scenes[scene_key] = {
                "realm_id": realm_id,
                "scene_id": scene_id,
                "entity_ids": sorted(identity_ids),
                "loaded_tick": tick_val,
                "last_tick": tick_val,
            }
            return {
                "workspace_id": payload.workspace_id,
                "realm_id": realm_id,
                "scene_id": scene_id,
                "scene_key": scene_key,
                "loaded_entities": upserted,
                "replaced_entities": replaced,
                "renderer_state": _render_summary(),
            }

        def _resolve_runtime_identity(update_obj: Mapping[str, object]) -> str | None:
            identity = str(update_obj.get("identity", "")).strip()
            if identity != "":
                return identity
            loaded_scenes, _, placement_index, _ = _render_state_maps()
            placement_id = str(update_obj.get("placement_id", "")).strip()
            if placement_id != "" and placement_id in placement_index:
                return placement_index[placement_id]
            realm_id = str(update_obj.get("realm_id", "")).strip().lower()
            scene_id = str(update_obj.get("scene_id", "")).strip()
            entity_id = str(update_obj.get("entity_id", "")).strip()
            if scene_id != "" and entity_id != "":
                if realm_id == "":
                    for key, scene_row in loaded_scenes.items():
                        if not isinstance(scene_row, dict):
                            continue
                        if str(scene_row.get("scene_id", "")) == scene_id:
                            realm_id = str(scene_row.get("realm_id", "")).strip().lower()
                            if realm_id != "":
                                break
                if realm_id != "":
                    return _render_identity(_render_scene_key(realm_id, scene_id), entity_id)
            return None

        def _render_scene_tick(
            action_payload: Mapping[str, object],
            *,
            action_id: str,
        ) -> dict[str, object]:
            loaded_scenes, entities, placement_index, tick_val = _render_state_maps()
            scene_id = str(action_payload.get("scene_id", "")).strip()
            if scene_id == "":
                raise ValueError("scene_id_required_for_scene_tick")
            if "clock_advance" not in action_payload:
                raise ValueError("clock_advance_required_for_scene_tick")
            clock_advance = max(0, self._int_from_table(action_payload.get("clock_advance"), 0))
            dt = max(0, self._int_from_table(action_payload.get("dt"), clock_advance))
            next_tick = tick_val + dt
            runtime_render_state["tick"] = next_tick
            runtime_scene_clock_state["scene_minutes_total"] = (
                self._int_from_table(runtime_scene_clock_state.get("scene_minutes_total"), 0) + clock_advance
            )
            runtime_scene_clock_state["scene_advances_count"] = (
                self._int_from_table(runtime_scene_clock_state.get("scene_advances_count"), 0) + 1
            )
            runtime_scene_clock_state["last_scene_id"] = scene_id
            runtime_scene_clock_state["last_clock_advance"] = clock_advance
            updates_obj = action_payload.get("updates")
            updates = updates_obj if isinstance(updates_obj, list) else []
            normalized_updates = [item for item in updates if isinstance(item, dict)]
            normalized_updates.sort(
                key=lambda item: (
                    str(cast(dict[str, object], item).get("identity", "")),
                    str(cast(dict[str, object], item).get("placement_id", "")),
                    str(cast(dict[str, object], item).get("scene_id", "")),
                    str(cast(dict[str, object], item).get("entity_id", "")),
                )
            )
            applied = 0
            removed = 0
            pygame_ops: list[dict[str, object]] = []
            for raw_item in normalized_updates:
                update = cast(dict[str, object], raw_item)
                identity = _resolve_runtime_identity(update)
                if identity is None:
                    continue
                entity = entities.get(identity)
                if not isinstance(entity, dict):
                    continue
                if bool(update.get("remove", False)):
                    placement_id = str(entity.get("placement_id", "")).strip()
                    if placement_id != "":
                        placement_index.pop(placement_id, None)
                    pygame_ops.append(
                        {
                            "op": "remove",
                            "identity": identity,
                            "placement_id": placement_id,
                            "scene_key": str(entity.get("scene_key", "")),
                            "entity_id": str(entity.get("entity_id", "")),
                            "realm_id": str(entity.get("realm_id", "")),
                            "scene_id": str(entity.get("scene_id", "")),
                            "tick": next_tick,
                        }
                    )
                    entities.pop(identity, None)
                    scene_key = str(entity.get("scene_key", ""))
                    scene_row = loaded_scenes.get(scene_key)
                    if isinstance(scene_row, dict):
                        ids_obj = scene_row.get("entity_ids")
                        ids = [str(item) for item in ids_obj] if isinstance(ids_obj, list) else []
                        scene_row["entity_ids"] = sorted([item for item in ids if item != identity])
                        scene_row["last_tick"] = next_tick
                    removed += 1
                    continue
                for axis in ("x", "y"):
                    if axis in update:
                        entity[axis] = float(update.get(axis) or 0.0)
                if "z" in update:
                    entity["z"] = int(update.get("z") or 0)
                if "kind" in update:
                    entity["kind"] = str(update.get("kind") or entity.get("kind") or "entity")
                if "metadata" in update and isinstance(update.get("metadata"), dict):
                    merged_meta = dict(cast(dict[str, object], entity.get("metadata", {})))
                    merged_meta.update(cast(dict[str, object], update.get("metadata")))
                    self._resolve_aster_metadata(merged_meta)
                    entity["metadata"] = merged_meta
                scene_key = str(entity.get("scene_key", ""))
                scene_row = loaded_scenes.get(scene_key)
                if isinstance(scene_row, dict):
                    scene_row["last_tick"] = next_tick
                pygame_ops.append(
                    {
                        "op": "move",
                        "identity": identity,
                        "placement_id": str(entity.get("placement_id", "")),
                        "scene_key": scene_key,
                        "entity_id": str(entity.get("entity_id", "")),
                        "realm_id": str(entity.get("realm_id", "")),
                        "scene_id": str(entity.get("scene_id", "")),
                        "kind": str(entity.get("kind", "entity")),
                        "x": float(entity.get("x", 0.0)),
                        "y": float(entity.get("y", 0.0)),
                        "z": int(entity.get("z", 0)),
                        "metadata": dict(cast(dict[str, object], entity.get("metadata", {}))),
                        "tick": next_tick,
                    }
                )
                applied += 1
            enqueue_pygame = bool(action_payload.get("enqueue_pygame", False))
            pygame_enqueue: dict[str, object] | None = None
            if enqueue_pygame:
                command_kind = str(action_payload.get("pygame_command_kind", "render_scene_tick_delta")).strip().lower()
                if command_kind == "":
                    command_kind = "render_scene_tick_delta"
                pygame_enqueue = self._pygame_worker.enqueue(
                    workspace_id=payload.workspace_id,
                    actor_id=payload.actor_id,
                    action_id=action_id,
                    command_kind=command_kind,
                    runtime_action_kind="render.scene.tick",
                    payload={
                        "tick_before": tick_val,
                        "tick_after": next_tick,
                        "ops": pygame_ops,
                    },
                )
            return {
                "workspace_id": payload.workspace_id,
                "scene_id": scene_id,
                "clock_advance": clock_advance,
                "tick_before": tick_val,
                "tick_after": next_tick,
                "applied_updates": applied,
                "removed_entities": removed,
                "pygame_delta_ops": pygame_ops,
                "pygame_enqueue": pygame_enqueue,
                "renderer_state": _render_summary(),
                "scene_clock_state": _scene_clock_summary(),
            }

        def _render_scene_unload(action_payload: Mapping[str, object]) -> dict[str, object]:
            loaded_scenes, entities, placement_index, tick_val = _render_state_maps()
            realm_id = str(action_payload.get("realm_id", "")).strip().lower()
            scene_id = str(action_payload.get("scene_id", "")).strip()
            if realm_id == "" or scene_id == "":
                raise ValueError("realm_or_scene_required")
            scene_key = _render_scene_key(realm_id, scene_id)
            scene_row = loaded_scenes.pop(scene_key, None)
            ids_obj = scene_row.get("entity_ids") if isinstance(scene_row, dict) else []
            ids = [str(item) for item in ids_obj] if isinstance(ids_obj, list) else []
            removed = 0
            for identity in ids:
                row = entities.pop(identity, None)
                if isinstance(row, dict):
                    placement_id = str(row.get("placement_id", "")).strip()
                    if placement_id != "":
                        placement_index.pop(placement_id, None)
                    removed += 1
            return {
                "workspace_id": payload.workspace_id,
                "realm_id": realm_id,
                "scene_id": scene_id,
                "scene_key": scene_key,
                "unloaded": scene_row is not None,
                "removed_entities": removed,
                "tick": tick_val,
                "renderer_state": _render_summary(),
            }

        def _render_scene_reconcile(action_payload: Mapping[str, object]) -> dict[str, object]:
            loaded_scenes, entities, placement_index, tick_val = _render_state_maps()
            realm_id, scene_id, scene_content = _load_scene_content_for_runtime(action_payload)
            scene_key = _render_scene_key(realm_id, scene_id)
            expected_entities = _extract_scene_entities(scene_content, scene_id)
            expected_map: dict[str, dict[str, object]] = {}
            for item in expected_entities:
                identity = _render_identity(scene_key, str(item.get("entity_id", "")))
                expected_map[identity] = {
                    "identity": identity,
                    "scene_key": scene_key,
                    "realm_id": realm_id,
                    "scene_id": scene_id,
                    **item,
                }
            existing_obj = loaded_scenes.get(scene_key, {})
            existing_ids_obj = existing_obj.get("entity_ids") if isinstance(existing_obj, dict) else []
            existing_ids = {str(item) for item in existing_ids_obj} if isinstance(existing_ids_obj, list) else set()
            expected_ids = set(expected_map.keys())
            missing_ids = sorted(expected_ids - existing_ids)
            stale_ids = sorted(existing_ids - expected_ids)
            changed_ids: list[str] = []
            for identity in sorted(expected_ids & existing_ids):
                existing_entity = entities.get(identity)
                expected_entity = expected_map[identity]
                if not isinstance(existing_entity, dict):
                    changed_ids.append(identity)
                    continue
                current_projection = (
                    float(existing_entity.get("x", 0.0)),
                    float(existing_entity.get("y", 0.0)),
                    int(existing_entity.get("z", 0)),
                    str(existing_entity.get("kind", "")),
                    self._canonical_hash(existing_entity.get("metadata", {})),
                )
                expected_projection = (
                    float(expected_entity.get("x", 0.0)),
                    float(expected_entity.get("y", 0.0)),
                    int(expected_entity.get("z", 0)),
                    str(expected_entity.get("kind", "")),
                    self._canonical_hash(expected_entity.get("metadata", {})),
                )
                if current_projection != expected_projection:
                    changed_ids.append(identity)
            apply_changes = bool(action_payload.get("apply", True))
            if apply_changes:
                for identity in stale_ids:
                    stale_row = entities.pop(identity, None)
                    if isinstance(stale_row, dict):
                        placement_id = str(stale_row.get("placement_id", "")).strip()
                        if placement_id != "":
                            placement_index.pop(placement_id, None)
                merged_ids = sorted(expected_ids)
                for identity in merged_ids:
                    row = expected_map[identity]
                    entities[identity] = row
                    placement_id = str(row.get("placement_id", "")).strip()
                    if placement_id != "":
                        placement_index[placement_id] = identity
                loaded_scenes[scene_key] = {
                    "realm_id": realm_id,
                    "scene_id": scene_id,
                    "entity_ids": merged_ids,
                    "loaded_tick": self._int_from_table(
                        (existing_obj if isinstance(existing_obj, dict) else {}).get("loaded_tick"),
                        tick_val,
                    ),
                    "last_tick": tick_val,
                }
            return {
                "workspace_id": payload.workspace_id,
                "realm_id": realm_id,
                "scene_id": scene_id,
                "scene_key": scene_key,
                "missing_identities": missing_ids,
                "stale_identities": stale_ids,
                "changed_identities": sorted(changed_ids),
                "apply": apply_changes,
                "renderer_state": _render_summary(),
            }

        def _stock_overrides_for_realm(realm_id: str) -> dict[str, int]:
            overrides = runtime_market_stock.get(realm_id)
            if overrides is None:
                overrides = {}
                runtime_market_stock[realm_id] = overrides
            return overrides

        def _effective_stock(realm_id: str, item_id: str) -> int:
            market = get_realm_market(realm_id)
            overrides = _stock_overrides_for_realm(realm_id)
            if item_id in overrides:
                return max(0, int(overrides[item_id]))
            return max(0, int(market.stock.get(item_id, 0)))

        def _runtime_loaded_regions() -> dict[str, dict[str, object]]:
            loaded_regions: dict[str, dict[str, object]] = {}
            for region_id, row in runtime_regions.items():
                if not bool(row.get("loaded")):
                    continue
                loaded_regions[region_id] = {
                    "realm_id": str(row.get("realm_id", "")),
                    "region_key": str(row.get("region_key", "")),
                    "payload": cast(dict[str, object], row.get("payload", {})),
                    "payload_hash": str(row.get("payload_hash", "")),
                    "cache_policy": str(row.get("cache_policy", "cache")),
                    "loaded_at": str(row.get("updated_at", row.get("created_at", ""))),
                }
            return loaded_regions

        def _sync_runtime_region_loaded_flags(projected_loaded: Mapping[str, object]) -> None:
            projected_ids = {str(key) for key in projected_loaded.keys()}
            now_iso = "runtime"
            for region_id, row in runtime_regions.items():
                should_be_loaded = region_id in projected_ids
                if bool(row.get("loaded")) != should_be_loaded:
                    row["loaded"] = should_be_loaded
                    row["updated_at"] = now_iso

        def _runtime_load_region(action_payload: Mapping[str, object]) -> object:
            if self._repo is None:
                realm_id = str(action_payload.get("realm_id", "")).strip().lower()
                region_key = str(action_payload.get("region_key", "")).strip()
                if realm_id == "" or region_key == "":
                    raise ValueError("realm_or_region_required")
                payload_obj = action_payload.get("payload", {})
                if not isinstance(payload_obj, dict):
                    payload_obj = {}
                cache_policy = str(action_payload.get("cache_policy", "cache")).strip().lower() or "cache"
                region_id = f"{realm_id}::{region_key}"
                now_iso = "runtime"
                existing_region = runtime_regions.get(region_id)
                created_at = (
                    str(existing_region.get("created_at", now_iso))
                    if isinstance(existing_region, dict)
                    else now_iso
                )
                payload_hash = self._canonical_hash(payload_obj)
                runtime_regions[region_id] = {
                    "id": region_id,
                    "workspace_id": payload.workspace_id,
                    "realm_id": realm_id,
                    "region_key": region_key,
                    "payload": cast(dict[str, object], payload_obj),
                    "payload_hash": payload_hash,
                    "cache_policy": cache_policy,
                    "loaded": True,
                    "created_at": created_at,
                    "updated_at": now_iso,
                }
                projected_state = self._world_stream.load(
                    {"world_stream": {"loaded_regions": _runtime_loaded_regions()}},
                    realm_id=realm_id,
                    region_key=region_key,
                    payload=cast(dict[str, object], payload_obj),
                    payload_hash=payload_hash,
                    cache_policy=cache_policy,
                )
                projected_stream = projected_state.get("world_stream")
                projected_loaded_obj = (
                    projected_stream.get("loaded_regions")
                    if isinstance(projected_stream, dict)
                    else {}
                )
                projected_loaded = projected_loaded_obj if isinstance(projected_loaded_obj, dict) else {}
                _sync_runtime_region_loaded_flags(projected_loaded)
                return dict(runtime_regions[region_id])
            return self.load_world_region(payload=WorldRegionLoadInput(**dict(action_payload)))

        def _runtime_unload_region(action_payload: Mapping[str, object]) -> object:
            if self._repo is None:
                realm_id = str(action_payload.get("realm_id", "")).strip().lower()
                region_key = str(action_payload.get("region_key", "")).strip()
                if realm_id == "" or region_key == "":
                    raise ValueError("realm_or_region_required")
                region_id = f"{realm_id}::{region_key}"
                unloaded = bool(runtime_regions.get(region_id, {}).get("loaded"))
                projected_state = self._world_stream.unload(
                    {"world_stream": {"loaded_regions": _runtime_loaded_regions()}},
                    realm_id=realm_id,
                    region_key=region_key,
                )
                projected_stream = projected_state.get("world_stream")
                projected_loaded_obj = (
                    projected_stream.get("loaded_regions")
                    if isinstance(projected_stream, dict)
                    else {}
                )
                projected_loaded = projected_loaded_obj if isinstance(projected_loaded_obj, dict) else {}
                _sync_runtime_region_loaded_flags(projected_loaded)
                row = runtime_regions.get(region_id)
                if row is not None:
                    row["loaded"] = False
                    row["updated_at"] = "runtime"
                return {
                    "workspace_id": payload.workspace_id,
                    "realm_id": realm_id,
                    "region_key": region_key,
                    "unloaded": unloaded,
                }
            return self.unload_world_region(payload=WorldRegionUnloadInput(**dict(action_payload)))

        def _world_region_scene_bind_payload(
            *,
            action_payload: Mapping[str, object],
            region_result: Mapping[str, object],
        ) -> dict[str, object] | None:
            if not bool(action_payload.get("bind_render_scene", False)):
                return None
            realm_id = str(action_payload.get("realm_id") or region_result.get("realm_id") or "").strip().lower()
            if realm_id == "":
                raise ValueError("realm_id_required_for_bind_render_scene")
            scene_id = str(
                action_payload.get("scene_id")
                or action_payload.get("runtime_scene_id")
                or ""
            ).strip()
            if scene_id == "":
                region_payload_obj = region_result.get("payload")
                if isinstance(region_payload_obj, dict):
                    scene_id = str(region_payload_obj.get("scene_id") or "").strip()
            if scene_id == "":
                raise ValueError("scene_id_required_for_bind_render_scene")
            bind_payload: dict[str, object] = {
                "realm_id": realm_id,
                "scene_id": scene_id,
            }
            scene_content_obj = action_payload.get("scene_content")
            if not isinstance(scene_content_obj, dict):
                region_payload_obj = region_result.get("payload")
                if isinstance(region_payload_obj, dict) and isinstance(region_payload_obj.get("scene_content"), dict):
                    scene_content_obj = cast(dict[str, object], region_payload_obj.get("scene_content"))
            if isinstance(scene_content_obj, dict):
                bind_payload["scene_content"] = cast(dict[str, object], scene_content_obj)
            return bind_payload

        for action in payload.actions:
            action_payload = dict(action.payload)
            action_payload.setdefault("workspace_id", payload.workspace_id)
            action_payload.setdefault("actor_id", payload.actor_id)
            try:
                _enforce_scene_clock_policy(action.kind, action_payload)
                if action.kind == "levels.apply":
                    result = self.apply_level_progress(
                        payload=LevelApplyInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "skills.train":
                    result = self.train_skill(
                        payload=SkillTrainInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "perks.unlock":
                    result = self.unlock_perk(
                        payload=PerkUnlockInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "alchemy.craft":
                    result = self.craft_alchemy(
                        payload=AlchemyCraftInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "blacksmith.forge":
                    result = self.forge_blacksmith(
                        payload=BlacksmithForgeInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "combat.resolve":
                    result = self.resolve_combat(
                        payload=CombatResolveInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "market.quote":
                    result = self.market_quote(
                        payload=MarketQuoteInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "market.trade":
                    trade_input = MarketTradeInput(**action_payload)
                    realm_id = _normalize_realm_for_runtime(trade_input.realm_id)
                    stock_before = _effective_stock(realm_id, trade_input.item_id)
                    adjusted_payload = trade_input.model_copy(
                        update={"available_liquidity": min(trade_input.available_liquidity, stock_before)}
                    )
                    trade_result = self.market_trade(
                        payload=adjusted_payload,
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                    stock_after = stock_before
                    if trade_result.side == "buy":
                        stock_after = max(0, stock_before - trade_result.filled_qty)
                    elif trade_result.side == "sell":
                        stock_after = max(0, stock_before + trade_result.filled_qty)
                    _stock_overrides_for_realm(realm_id)[trade_input.item_id] = stock_after
                    result = {
                        **trade_result.model_dump(),
                        "stock_before_qty": stock_before,
                        "stock_after_qty": stock_after,
                    }
                elif action.kind == "vitriol.apply":
                    result = self.vitriol_apply_ruler_influence(
                        payload=VitriolApplyRulerInfluenceInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "vitriol.compute":
                    result = self.vitriol_compute(payload=VitriolComputeInput(**action_payload))
                elif action.kind == "vitriol.clear":
                    result = self.vitriol_clear_expired(
                        payload=VitriolClearExpiredInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "djinn.apply":
                    result = self.apply_djinn_influence(
                        payload=DjinnApplyInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                elif action.kind == "world.region.load":
                    loaded_result = self._dict_result(_runtime_load_region(action_payload))
                    scene_bind_payload = _world_region_scene_bind_payload(
                        action_payload=action_payload,
                        region_result=loaded_result,
                    )
                    if scene_bind_payload is not None:
                        loaded_result["render_scene"] = _render_scene_load(scene_bind_payload)
                    result = loaded_result
                elif action.kind == "world.region.unload":
                    unloaded_result = self._dict_result(_runtime_unload_region(action_payload))
                    scene_bind_payload = _world_region_scene_bind_payload(
                        action_payload=action_payload,
                        region_result=unloaded_result,
                    )
                    if scene_bind_payload is not None:
                        unloaded_result["render_scene"] = _render_scene_unload(scene_bind_payload)
                    result = unloaded_result
                elif action.kind == "world.region.preload.scenegraph":
                    scene_content_obj: dict[str, object] | None = None
                    realm_id = str(action_payload.get("realm_id", "")).strip().lower()
                    scene_id = str(action_payload.get("scene_id", "")).strip()
                    if isinstance(action_payload.get("scene_content"), dict):
                        scene_content_obj = cast(dict[str, object], action_payload.get("scene_content"))
                    elif scene_id != "" and self._repo is not None:
                        if realm_id == "":
                            raise ValueError("realm_id_required")
                        scene_row = self.get_scene(
                            workspace_id=payload.workspace_id,
                            realm_id=realm_id,
                            scene_id=scene_id,
                        )
                        if scene_row is None:
                            raise ValueError("scene_not_found")
                        scene_content_obj = scene_row.content
                    if scene_content_obj is None:
                        raise ValueError("scene_content_or_scene_id_required")
                    if realm_id == "":
                        realm_from_content = str(scene_content_obj.get("realm_id", "")).strip().lower()
                        if realm_from_content != "":
                            realm_id = realm_from_content
                    if realm_id == "":
                        raise ValueError("realm_id_required")
                    chunk_size_raw = int(action_payload.get("chunk_size", 16))
                    chunk_size = max(1, chunk_size_raw)
                    cache_policy = str(action_payload.get("cache_policy", "stream")).strip().lower() or "stream"
                    region_prefix_raw = str(action_payload.get("region_prefix", "")).strip()
                    if region_prefix_raw != "":
                        region_prefix = region_prefix_raw
                    elif scene_id != "":
                        safe_scene = "".join(ch if (ch.isalnum() or ch in {"_", "-", "/"}) else "_" for ch in scene_id)
                        region_prefix = f"{realm_id}/scene/{safe_scene}"
                    else:
                        region_prefix = f"{realm_id}/scene/runtime"
                    nodes_obj = scene_content_obj.get("nodes")
                    nodes = nodes_obj if isinstance(nodes_obj, list) else []
                    regions: dict[str, list[dict[str, object]]] = {}
                    for node_index, node in enumerate(nodes):
                        if not isinstance(node, dict):
                            continue
                        node_id = str(node.get("node_id") or f"node_{node_index}")
                        kind = str(node.get("kind") or "entity")
                        x = float(node.get("x") or 0.0)
                        y = float(node.get("y") or 0.0)
                        metadata_obj = node.get("metadata")
                        metadata = metadata_obj if isinstance(metadata_obj, dict) else {}
                        z = self._int_from_table(metadata.get("z"), 0)
                        chunk_x = int(x) // chunk_size
                        chunk_y = int(y) // chunk_size
                        region_key = f"{region_prefix}/chunk_{chunk_x}_{chunk_y}"
                        entities = regions.get(region_key)
                        if entities is None:
                            entities = []
                            regions[region_key] = entities
                        entities.append(
                            {
                                "id": node_id,
                                "kind": kind,
                                "x": x,
                                "y": y,
                                "z": z,
                                "metadata": dict(metadata),
                            }
                        )
                    preload_limit_raw = action_payload.get("preload_limit")
                    preload_limit = int(preload_limit_raw) if preload_limit_raw is not None else 0
                    region_results: list[dict[str, object]] = []
                    preloaded_keys: list[str] = []
                    for index, region_key in enumerate(sorted(regions.keys())):
                        if preload_limit > 0 and index >= preload_limit:
                            break
                        entities = sorted(regions[region_key], key=lambda item: str(item.get("id", "")))
                        load_payload = {
                            "workspace_id": payload.workspace_id,
                            "realm_id": realm_id,
                            "region_key": region_key,
                            "payload": {
                                "scene_id": scene_id,
                                "chunk_size": chunk_size,
                                "entities": entities,
                            },
                            "cache_policy": cache_policy,
                        }
                        loaded = _runtime_load_region(load_payload)
                        loaded_map = self._dict_result(loaded)
                        loaded_map["source"] = "scenegraph_preload"
                        region_results.append(loaded_map)
                        preloaded_keys.append(region_key)
                    result = {
                        "workspace_id": payload.workspace_id,
                        "realm_id": realm_id,
                        "scene_id": scene_id,
                        "chunk_size": chunk_size,
                        "cache_policy": cache_policy,
                        "region_count": len(region_results),
                        "region_keys": preloaded_keys,
                        "regions": region_results,
                    }
                elif action.kind == "world.stream.status":
                    if self._repo is None:
                        realm_filter = cast(Optional[str], action_payload.get("realm_id"))
                        realm_norm = (
                            str(realm_filter).strip().lower()
                            if isinstance(realm_filter, str) and str(realm_filter).strip() != ""
                            else None
                        )
                        scoped_rows = [
                            row
                            for row in runtime_regions.values()
                            if realm_norm is None or row.get("realm_id") == realm_norm
                        ]
                        loaded_rows = [
                            row
                            for row in scoped_rows
                            if bool(row.get("loaded"))
                        ]
                        policy_counts: dict[str, int] = {"cache": 0, "stream": 0, "pin": 0}
                        for row in loaded_rows:
                            policy = str(row.get("cache_policy", "cache")).strip().lower()
                            policy_counts[policy] = policy_counts.get(policy, 0) + 1
                        capacity = self._world_stream.max_loaded_regions
                        total_regions = len(scoped_rows)
                        loaded_count = len(loaded_rows)
                        unloaded_count = max(0, total_regions - loaded_count)
                        pressure = 0.0 if capacity <= 0 else float(loaded_count) / float(capacity)
                        result = {
                            "workspace_id": payload.workspace_id,
                            "realm_id": realm_norm,
                            "total_regions": total_regions,
                            "loaded_count": loaded_count,
                            "unloaded_count": unloaded_count,
                            "capacity": capacity,
                            "pressure": pressure,
                            "policy_counts": policy_counts,
                            "pressure_components": {
                                "stream_occupancy": pressure,
                                "demon_total": 0.0,
                                "composite": pressure,
                            },
                            "demon_pressures": dict(self._DEMON_PRESSURE_DEFAULTS),
                            "demon_maladies": dict(self._DEMON_MALADY_DOMAINS),
                        }
                    else:
                        result = self.world_stream_status(
                            workspace_id=str(action_payload.get("workspace_id", payload.workspace_id)),
                            realm_id=cast(Optional[str], action_payload.get("realm_id")),
                        )
                elif action.kind == "world.coins.list":
                    result = [item.model_dump() for item in self.list_realm_coins(cast(Optional[str], action_payload.get("realm_id")))]
                elif action.kind == "world.markets.list":
                    realm_filter = cast(Optional[str], action_payload.get("realm_id"))
                    markets = self.list_realm_markets(realm_filter)
                    market_rows: list[dict[str, object]] = []
                    for market in markets:
                        row = market.model_dump()
                        stock_map = {key: int(value) for key, value in market.stock.items()}
                        realm_overrides = runtime_market_stock.get(market.realm_id, {})
                        for item_id, qty in realm_overrides.items():
                            stock_map[item_id] = max(0, int(qty))
                        row["stock"] = stock_map
                        meta_overrides = runtime_market_meta.get(market.realm_id, {})
                        for key, value in meta_overrides.items():
                            row[key] = value
                        market_rows.append(row)
                    result = market_rows
                elif action.kind == "world.market.stock.adjust":
                    realm_id = _normalize_realm_for_runtime(action_payload.get("realm_id"))
                    item_id = str(action_payload.get("item_id", "")).strip()
                    if item_id == "":
                        raise ValueError("item_id_required")
                    stock_before = _effective_stock(realm_id, item_id)
                    set_qty_raw = action_payload.get("set_qty")
                    breath_context: dict[str, object] | None = None
                    if set_qty_raw is None:
                        delta = int(action_payload.get("delta", 0))
                        effective_delta = delta
                        if bool(action_payload.get("use_breath_context", False)):
                            has_generation_inputs = any(
                                key in action_payload
                                for key in (
                                    "player_name",
                                    "canonical_game_number",
                                    "quest_completion",
                                    "kills",
                                    "deaths",
                                    "level",
                                    "max_iter",
                                )
                            )
                            cached = runtime_breath_context.get(payload.actor_id)
                            if has_generation_inputs or cached is None:
                                breath_context = self.evaluate_breath_ko(
                                    workspace_id=payload.workspace_id,
                                    actor_id=payload.actor_id,
                                    payload=action_payload,
                                    kernel_actor_id=actor_id,
                                    workshop_id=workshop_id,
                                    persist_state=True,
                                    emit_kernel=False,
                                )
                                runtime_breath_context[payload.actor_id] = breath_context
                            else:
                                breath_context = dict(cached)
                            chaos_meter = int(breath_context.get("chaos_meter", 0))
                            order_meter = int(breath_context.get("order_meter", 0))
                            reward_metric = 50
                            reward_axis = "neutral"
                            if realm_id == "mercurie":
                                reward_metric = order_meter
                                reward_axis = "order"
                            elif realm_id == "sulphera":
                                reward_metric = chaos_meter
                                reward_axis = "chaos"
                            elif realm_id == "lapidus":
                                reward_metric = max(0, min(100, int(action_payload.get("royl_loyalty", 0))))
                                reward_axis = "royl_loyalty"
                            influence_bp = max(0, min(10000, int(action_payload.get("influence_bp", 2500))))
                            reward_adv = max(-50, min(50, reward_metric - 50))
                            effective_delta += (delta * reward_adv * influence_bp) // 500000
                        stock_after = max(0, stock_before + effective_delta)
                    else:
                        stock_after = max(0, int(set_qty_raw))
                    _stock_overrides_for_realm(realm_id)[item_id] = stock_after
                    result_map: dict[str, object] = {
                        "workspace_id": payload.workspace_id,
                        "realm_id": realm_id,
                        "item_id": item_id,
                        "stock_before_qty": stock_before,
                        "stock_after_qty": stock_after,
                    }
                    if set_qty_raw is None:
                        result_map["delta"] = int(action_payload.get("delta", 0))
                        result_map["effective_delta"] = stock_after - stock_before
                        if bool(action_payload.get("use_breath_context", False)):
                            result_map["realm_reward_policy"] = (
                                "order" if realm_id == "mercurie" else
                                "chaos" if realm_id == "sulphera" else
                                "royl_loyalty" if realm_id == "lapidus" else
                                "neutral"
                            )
                    if breath_context is not None:
                        result_map["breath_context"] = breath_context
                    result = result_map
                elif action.kind == "world.market.sovereignty.transition":
                    realm_id = _normalize_realm_for_runtime(action_payload.get("realm_id"))
                    market = get_realm_market(realm_id)
                    victor_id = str(action_payload.get("victor_id", "player_commonwealth")).strip().lower()
                    if victor_id == "":
                        raise ValueError("victor_id_required")
                    if not bool(action_payload.get("overthrow", True)):
                        raise ValueError("sovereignty_transition_requires_overthrow")
                    prior_operator = str(
                        runtime_market_meta.get(realm_id, {}).get("dominant_operator", market.dominant_operator)
                    )
                    redistribution_mode = str(
                        action_payload.get("redistribution_mode", "equalized_public_distribution")
                    ).strip().lower() or "equalized_public_distribution"
                    beneficiary_groups_raw = action_payload.get("beneficiary_groups", [])
                    beneficiary_groups: list[str] = []
                    if isinstance(beneficiary_groups_raw, list):
                        for item in beneficiary_groups_raw:
                            token = str(item).strip().lower()
                            if token != "":
                                beneficiary_groups.append(token)
                    if len(beneficiary_groups) == 0:
                        beneficiary_groups = ["citizens", "artisans", "travelers"]
                    dominant_network = str(
                        action_payload.get("market_network", "public_redistribution_council")
                    ).strip().lower() or "public_redistribution_council"
                    dominance_bp_raw = int(action_payload.get("dominance_bp", 1000))
                    dominance_bp = max(0, min(10000, dominance_bp_raw))
                    transition_tick = int(action_payload.get("tick", 0))
                    transition_note = str(action_payload.get("note", "market_sovereignty_transition")).strip()
                    runtime_market_meta[realm_id] = {
                        "dominant_operator": victor_id,
                        "market_network": dominant_network,
                        "dominance_bp": dominance_bp,
                        "redistribution_policy": {
                            "mode": redistribution_mode,
                            "beneficiary_groups": beneficiary_groups,
                            "active": True,
                            "transition_tick": transition_tick,
                            "note": transition_note,
                        },
                    }
                    result = {
                        "workspace_id": payload.workspace_id,
                        "realm_id": realm_id,
                        "overthrow": True,
                        "prior_operator": prior_operator,
                        "new_operator": victor_id,
                        "market_network": dominant_network,
                        "dominance_bp": dominance_bp,
                        "redistribution_policy": runtime_market_meta[realm_id]["redistribution_policy"],
                    }
                elif action.kind == "breath.ko.evaluate":
                    result = self.evaluate_breath_ko(
                        workspace_id=payload.workspace_id,
                        actor_id=payload.actor_id,
                        payload=action_payload,
                        kernel_actor_id=actor_id,
                        workshop_id=workshop_id,
                        persist_state=bool(action_payload.get("persist_state", True)),
                        emit_kernel=bool(action_payload.get("emit_kernel", True)),
                    )
                    runtime_breath_context[payload.actor_id] = dict(result)
                elif action.kind == "sanity.adjust":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    delta_obj = action_payload.get("delta")
                    set_obj = action_payload.get("set")
                    delta_map = cast(dict[str, object], delta_obj) if isinstance(delta_obj, dict) else {}
                    set_map = cast(dict[str, object], set_obj) if isinstance(set_obj, dict) else {}
                    if self._repo is None:
                        current = runtime_sanity_state.get(
                            actor_key,
                            {key: 50 for key in self._SANITY_KEYS},
                        )
                        updated = self._apply_sanity_adjustment(
                            current=current,
                            delta=delta_map,
                            set_values=set_map,
                        )
                        runtime_sanity_state[actor_key] = dict(updated)
                        result = {
                            "workspace_id": payload.workspace_id,
                            "actor_id": actor_key,
                            "sanity": updated,
                        }
                    else:
                        state = self.get_player_state(workspace_id=payload.workspace_id, actor_id=actor_key)
                        flags_obj = dict(state.tables.flags)
                        current = self._extract_sanity_from_flags(flags_obj)
                        updated = self._apply_sanity_adjustment(
                            current=current,
                            delta=delta_map,
                            set_values=set_map,
                        )
                        flags_obj["sanity"] = updated
                        self.apply_player_state(
                            payload=PlayerStateApplyInput(
                                workspace_id=payload.workspace_id,
                                actor_id=actor_key,
                                tables=PlayerStateTables(flags=flags_obj),
                                mode="merge",
                            ),
                            actor_id=actor_id,
                            workshop_id=workshop_id,
                        )
                        result = {
                            "workspace_id": payload.workspace_id,
                            "actor_id": actor_key,
                            "sanity": updated,
                        }
                elif action.kind == "radio.evaluate":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    actor_flags = runtime_flags_state.get(actor_key, {})
                    inferred_underworld_state = str(actor_flags.get("underworld_state", "dormant"))
                    action_payload.setdefault("underworld_state", inferred_underworld_state)
                    radio = self.evaluate_radio_availability(
                        payload=RadioEvaluateInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                    merged = dict(actor_flags)
                    merged.update(radio.flags)
                    runtime_flags_state[actor_key] = merged
                    result = radio.model_dump()
                elif action.kind == "alchemy.crystal":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    actor_flags = runtime_flags_state.get(actor_key, {})
                    action_payload.setdefault("infernal_meditation", bool(actor_flags.get("infernal_meditation", False)))
                    action_payload.setdefault("vitriol_trials_cleared", bool(actor_flags.get("vitriol_trials_cleared", False)))
                    crystal = self.craft_alchemy_crystal(
                        payload=AlchemyCrystalInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                    if crystal.key_flags:
                        merged = dict(actor_flags)
                        merged.update(crystal.key_flags)
                        runtime_flags_state[actor_key] = merged
                    result = crystal.model_dump()
                elif action.kind == "infernal_meditation.unlock":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    unlock = self.unlock_infernal_meditation(
                        payload=InfernalMeditationUnlockInput(**action_payload),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                    merged = dict(runtime_flags_state.get(actor_key, {}))
                    merged.update(unlock.flags)
                    runtime_flags_state[actor_key] = merged
                    result = unlock.model_dump()
                elif action.kind == "faction.loyalty.adjust":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    faction_id = str(action_payload.get("faction_id", "")).strip().lower()
                    if faction_id == "":
                        raise ValueError("faction_id_required")
                    actor_flags = dict(runtime_flags_state.get(actor_key, {}))
                    factions_obj = actor_flags.get("factions")
                    factions = dict(cast(dict[str, object], factions_obj)) if isinstance(factions_obj, dict) else {}
                    current_score = max(0, min(100, self._int_from_table(factions.get(faction_id), 0)))
                    if action_payload.get("set_score") is not None:
                        next_score = max(0, min(100, int(action_payload.get("set_score"))))
                    else:
                        next_score = max(0, min(100, current_score + int(action_payload.get("delta", 0))))
                    factions[faction_id] = next_score
                    actor_flags["factions"] = factions
                    runtime_flags_state[actor_key] = actor_flags
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": actor_key,
                        "faction_id": faction_id,
                        "score_before": current_score,
                        "score_after": next_score,
                        "factions": {str(k): int(self._int_from_table(v, 0)) for k, v in factions.items()},
                    }
                elif action.kind == "underworld.access.evaluate":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    actor_flags = dict(runtime_flags_state.get(actor_key, {}))
                    infernal_meditation = bool(action_payload.get("infernal_meditation", actor_flags.get("infernal_meditation", False)))
                    vitriol_trials_cleared = bool(action_payload.get("vitriol_trials_cleared", actor_flags.get("vitriol_trials_cleared", False)))
                    asmodian_purity = int(action_payload.get("asmodian_purity", actor_flags.get("asmodian_purity", 0)))
                    underworld_access = self._evaluate_underworld_access(
                        infernal_meditation=infernal_meditation,
                        vitriol_trials_cleared=vitriol_trials_cleared,
                        asmodian_purity=asmodian_purity,
                    )
                    actor_flags["underworld_access"] = underworld_access
                    actor_flags["underworld_state"] = "active" if infernal_meditation else "dormant"
                    runtime_flags_state[actor_key] = actor_flags
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": actor_key,
                        **underworld_access,
                    }
                elif action.kind == "affiliation.assign":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    normalized = self._normalize_affiliations(
                        fae_kind=str(action_payload.get("fae_kind", "")),
                        social_class=str(action_payload.get("social_class", "")),
                        realm_bindings=cast(list[object], action_payload.get("realm_bindings", [])),
                    )
                    actor_flags = dict(runtime_flags_state.get(actor_key, {}))
                    actor_flags["affiliation_profile"] = {
                        "fae_kind": normalized["fae_kind"],
                        "social_class": normalized["social_class"],
                        "realm_bindings": normalized["realm_bindings"],
                    }
                    actor_flags["affiliations"] = normalized["affiliations"]
                    runtime_flags_state[actor_key] = actor_flags
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": actor_key,
                        **normalized,
                    }
                elif action.kind == "quest.advance_by_graph":
                    normalized_payload = dict(action_payload)
                    normalized_payload.setdefault("workspace_id", payload.workspace_id)
                    normalized_payload.setdefault("actor_id", payload.actor_id)
                    dry_run = bool(normalized_payload.pop("dry_run", False))
                    quest_payload = QuestAdvanceByGraphInput.model_validate(normalized_payload)
                    if dry_run:
                        result = self.advance_quest_step_by_graph_dry_run(payload=quest_payload).model_dump()
                    else:
                        result = self.advance_quest_step_by_graph(
                            payload=quest_payload,
                            actor_id=actor_id,
                            workshop_id=workshop_id,
                        ).model_dump()
                elif action.kind == "quest.fate_knocks.bootstrap":
                    result = self._bootstrap_fate_knocks(
                        workspace_id=payload.workspace_id,
                        actor_id=payload.actor_id,
                        workshop_id=workshop_id,
                        payload=action_payload,
                    )
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    actor_flags = dict(runtime_flags_state.get(actor_key, {}))
                    actor_flags["intro.quiz_completed"] = bool(result.get("quiz_completed", False))
                    actor_flags["intro.destiny_calls_unlocked"] = bool(result.get("destiny_calls_unlocked", False))
                    actor_flags["intro.destiny_calls_quest_id"] = str(result.get("destiny_calls_quest_id", ""))
                    runtime_flags_state[actor_key] = actor_flags
                elif action.kind == "quest.fate_knocks.deadline_check":
                    result = self._fate_knocks_deadline_check(
                        workspace_id=payload.workspace_id,
                        actor_id=payload.actor_id,
                        workshop_id=workshop_id,
                        payload=action_payload,
                    )
                elif action.kind == "quest.fate_knocks.report_to_castle":
                    actor_key = str(action_payload.get("actor_id", payload.actor_id))
                    actor_flags = dict(runtime_flags_state.get(actor_key, {}))
                    action_payload.setdefault("quiz_completed", bool(actor_flags.get("intro.quiz_completed", False)))
                    action_payload.setdefault(
                        "destiny_calls_unlocked", bool(actor_flags.get("intro.destiny_calls_unlocked", False))
                    )
                    result = self._fate_knocks_report_to_castle(
                        workspace_id=payload.workspace_id,
                        actor_id=payload.actor_id,
                        workshop_id=workshop_id,
                        payload=action_payload,
                    )
                    actor_flags["intro.castle_report_completed"] = bool(result.get("reported_to_castle", False))
                    actor_flags["intro.met_hypatia"] = bool(result.get("met_hypatia", False))
                    actor_flags["intro.fate_knocks_resolved"] = bool(result.get("fate_knocks_resolved", False))
                    actor_flags["intro.destiny_calls_unlocked"] = bool(result.get("destiny_calls_unlocked", False))
                    actor_flags["intro.destiny_calls_quest_id"] = str(result.get("destiny_calls_quest_id", ""))
                    runtime_flags_state[actor_key] = actor_flags
                elif action.kind in {"dungeon.enter", "dungeon.generate"}:
                    active_runs, counters, _ = _dungeon_maps()
                    actor_key = str(action_payload.get("actor_id", payload.actor_id)).strip() or payload.actor_id
                    dungeon_id = _normalize_dungeon_id(action_payload.get("dungeon_id"))
                    player_level = max(1, self._int_from_table(action_payload.get("player_level"), 1))
                    quest_progress = max(0, self._int_from_table(action_payload.get("quest_progress"), 0))
                    entry_nonce = str(action_payload.get("entry_nonce", "")).strip()
                    run_label = str(action_payload.get("run_label", "")).strip()
                    meta_value = _dungeon_meta_load(actor_key)
                    entries_obj = cast(dict[str, object], meta_value.get("entries", {}))
                    persisted_count = max(0, self._int_from_table(entries_obj.get(dungeon_id), 0))
                    counter_key = f"{actor_key}::{dungeon_id}"
                    runtime_count = max(0, self._int_from_table(counters.get(counter_key), persisted_count))
                    entry_ordinal = max(1, self._int_from_table(action_payload.get("entry_ordinal"), runtime_count + 1))
                    generated = _dungeon_generate(
                        dungeon_id=dungeon_id,
                        player_level=player_level,
                        quest_progress=quest_progress,
                        entry_ordinal=entry_ordinal,
                        actor_key=actor_key,
                        entry_nonce=entry_nonce,
                        run_label=run_label,
                    )
                    counters[counter_key] = max(runtime_count, entry_ordinal)
                    entries_obj[dungeon_id] = counters[counter_key]
                    meta_value["entries"] = entries_obj
                    _dungeon_meta_save(actor_key, meta_value)
                    if action.kind == "dungeon.enter":
                        active_key = f"{actor_key}::{dungeon_id}"
                        active_runs[active_key] = dict(generated)
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": actor_key,
                        "action": "enter" if action.kind == "dungeon.enter" else "generate",
                        "dungeon_id": dungeon_id,
                        "entry_ordinal": entry_ordinal,
                        "run_id": str(generated.get("run_id", "")),
                        "realm_id": str(generated.get("realm_id", "")),
                        "difficulty_tier": self._int_from_table(generated.get("difficulty_tier"), 1),
                        "time_scale_to_lapidus": self._int_from_table(generated.get("time_scale_to_lapidus"), 1),
                        "hostile": bool(generated.get("hostile", True)),
                        "floor_count": self._int_from_table(generated.get("floor_count"), 0),
                        "rooms_per_floor": self._int_from_table(generated.get("rooms_per_floor"), 0),
                        "population": dict(cast(dict[str, object], generated.get("population", {}))),
                        "cypher_shards": list(cast(list[object], generated.get("cypher_shards", []))),
                        "seed_hash": str(generated.get("seed_hash", "")),
                        "in_memory_only": True,
                    }
                elif action.kind in {"dungeon.complete", "dungeon.fail", "dungeon.decode"}:
                    active_runs, _, _ = _dungeon_maps()
                    actor_key = str(action_payload.get("actor_id", payload.actor_id)).strip() or payload.actor_id
                    dungeon_id = _normalize_dungeon_id(action_payload.get("dungeon_id"))
                    active_key = f"{actor_key}::{dungeon_id}"
                    run = active_runs.get(active_key)
                    if not isinstance(run, dict):
                        raise ValueError("dungeon_run_not_active")
                    expected_run_id = str(action_payload.get("run_id", "")).strip()
                    if expected_run_id != "" and expected_run_id != str(run.get("run_id", "")):
                        raise ValueError("dungeon_run_mismatch")
                    if action.kind == "dungeon.decode":
                        decode = _dungeon_decode_payload(run)
                        result = {
                            "workspace_id": payload.workspace_id,
                            "actor_id": actor_key,
                            "dungeon_id": dungeon_id,
                            "run_id": str(run.get("run_id", "")),
                            "decoded": decode,
                            "in_memory_only": True,
                        }
                    else:
                        decode = _dungeon_decode_payload(run)
                        meta_value = _dungeon_meta_load(actor_key)
                        completed_obj = cast(dict[str, object], meta_value.get("completed", {}))
                        failed_obj = cast(dict[str, object], meta_value.get("failed", {}))
                        retained_obj = cast(dict[str, object], meta_value.get("retained", {}))
                        if action.kind == "dungeon.complete":
                            run["status"] = "completed"
                            completed_obj[dungeon_id] = self._int_from_table(completed_obj.get(dungeon_id), 0) + 1
                            retain_count = len(cast(list[object], run.get("cypher_shards", [])))
                        else:
                            run["status"] = "failed"
                            failed_obj[dungeon_id] = self._int_from_table(failed_obj.get(dungeon_id), 0) + 1
                            ratio_bp = max(0, min(10000, self._int_from_table(action_payload.get("retention_ratio_bp"), 2500)))
                            total_shards = len(cast(list[object], run.get("cypher_shards", [])))
                            retain_count = max(0, min(total_shards, (total_shards * ratio_bp) // 10000))
                        retained_obj[dungeon_id] = max(
                            self._int_from_table(retained_obj.get(dungeon_id), 0),
                            retain_count,
                        )
                        meta_value["completed"] = completed_obj
                        meta_value["failed"] = failed_obj
                        meta_value["retained"] = retained_obj
                        _dungeon_meta_save(actor_key, meta_value)
                        active_runs.pop(active_key, None)
                        result = {
                            "workspace_id": payload.workspace_id,
                            "actor_id": actor_key,
                            "dungeon_id": dungeon_id,
                            "run_id": str(run.get("run_id", "")),
                            "status": str(run.get("status", "")),
                            "retained_shard_count": retain_count,
                            "decoded": decode if action.kind == "dungeon.complete" else {},
                            "meta_progression": {
                                "entries": dict(cast(dict[str, object], meta_value.get("entries", {}))),
                                "completed": dict(completed_obj),
                                "failed": dict(failed_obj),
                                "retained": dict(retained_obj),
                            },
                            "in_memory_only": True,
                        }
                elif action.kind == "shygazun.interpret":
                    normalized_payload = dict(action_payload)
                    normalized_payload.setdefault("workspace_id", payload.workspace_id)
                    normalized_payload.setdefault("actor_id", payload.actor_id)
                    result = self.interpret_shygazun(
                        payload=ShygazunInterpretInput.model_validate(normalized_payload),
                    ).model_dump()
                elif action.kind == "shygazun.translate":
                    normalized_payload = dict(action_payload)
                    normalized_payload.setdefault("workspace_id", payload.workspace_id)
                    normalized_payload.setdefault("actor_id", payload.actor_id)
                    result = self.translate_shygazun(
                        payload=ShygazunTranslateInput.model_validate(normalized_payload),
                    ).model_dump()
                elif action.kind == "shygazun.correct":
                    normalized_payload = dict(action_payload)
                    normalized_payload.setdefault("workspace_id", payload.workspace_id)
                    normalized_payload.setdefault("actor_id", payload.actor_id)
                    result = self.correct_shygazun(
                        payload=ShygazunCorrectInput.model_validate(normalized_payload),
                    ).model_dump()
                elif action.kind == "math.numeral_3d":
                    normalized_payload = dict(action_payload)
                    normalized_payload.setdefault("workspace_id", payload.workspace_id)
                    normalized_payload.setdefault("actor_id", payload.actor_id)
                    result = self.compute_numeral_3d(
                        payload=Numeral3DInput.model_validate(normalized_payload),
                        actor_id=actor_id,
                    ).model_dump()
                elif action.kind == "math.fibonacci_ordering":
                    normalized_payload = dict(action_payload)
                    normalized_payload.setdefault("workspace_id", payload.workspace_id)
                    normalized_payload.setdefault("actor_id", payload.actor_id)
                    result = self.compute_fibonacci_ordering(
                        payload=FibonacciOrderingInput.model_validate(normalized_payload),
                        actor_id=actor_id,
                    ).model_dump()
                elif action.kind == "audio.cue.stage":
                    staged, _, _ = _audio_maps()
                    cue_id = str(action_payload.get("cue_id", "")).strip()
                    if cue_id == "":
                        raise ValueError("cue_id_required")
                    filename = str(action_payload.get("filename", "")).strip()
                    if filename == "":
                        raise ValueError("filename_required")
                    channel = _audio_channel(action_payload.get("channel", "sfx"))
                    loop = bool(action_payload.get("loop", False))
                    gain = _audio_gain(action_payload.get("gain", 1.0), 1.0)
                    start_ms = max(0, self._int_from_table(action_payload.get("start_ms"), 0))
                    tags_obj = action_payload.get("tags")
                    tags = [str(item).strip() for item in tags_obj] if isinstance(tags_obj, list) else []
                    tags = [item for item in tags if item != ""]
                    staged[cue_id] = {
                        "cue_id": cue_id,
                        "filename": filename,
                        "channel": channel,
                        "loop": loop,
                        "gain": gain,
                        "start_ms": start_ms,
                        "tags": sorted(tags),
                    }
                    runtime_audio_state["last_command"] = {
                        "op": "stage",
                        "cue_id": cue_id,
                        "channel": channel,
                    }
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": payload.actor_id,
                        "cue": dict(staged[cue_id]),
                        "audio_state": _audio_summary(),
                    }
                elif action.kind == "audio.cue.play":
                    staged, tick_val, emitted = _audio_maps()
                    cue_id = str(action_payload.get("cue_id", "")).strip()
                    if cue_id == "":
                        raise ValueError("cue_id_required")
                    cue = staged.get(cue_id)
                    if not isinstance(cue, dict):
                        raise ValueError("cue_not_staged")
                    channel = _audio_channel(action_payload.get("channel", cue.get("channel", "sfx")))
                    loop = bool(action_payload.get("loop", cue.get("loop", False)))
                    gain = _audio_gain(action_payload.get("gain", cue.get("gain", 1.0)), 1.0)
                    start_ms = max(0, self._int_from_table(action_payload.get("start_ms"), cue.get("start_ms", 0)))
                    next_tick = tick_val + 1
                    runtime_audio_state["tick"] = next_tick
                    runtime_audio_state["commands_emitted"] = emitted + 1
                    command = {
                        "op": "play",
                        "cue_id": cue_id,
                        "filename": str(cue.get("filename", "")),
                        "channel": channel,
                        "loop": loop,
                        "gain": gain,
                        "start_ms": start_ms,
                        "issued_tick": next_tick,
                    }
                    runtime_audio_state["last_command"] = command
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": payload.actor_id,
                        "command": command,
                        "audio_state": _audio_summary(),
                    }
                elif action.kind == "audio.cue.stop":
                    staged, tick_val, emitted = _audio_maps()
                    cue_id = str(action_payload.get("cue_id", "")).strip()
                    channel = _audio_channel(action_payload.get("channel", "sfx"))
                    stop_all = bool(action_payload.get("all", False))
                    if stop_all and cue_id != "":
                        cue_id = ""
                    if cue_id != "" and cue_id not in staged:
                        raise ValueError("cue_not_staged")
                    next_tick = tick_val + 1
                    runtime_audio_state["tick"] = next_tick
                    runtime_audio_state["commands_emitted"] = emitted + 1
                    command = {
                        "op": "stop_all" if stop_all else "stop",
                        "cue_id": cue_id,
                        "channel": channel,
                        "issued_tick": next_tick,
                    }
                    runtime_audio_state["last_command"] = command
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": payload.actor_id,
                        "command": command,
                        "audio_state": _audio_summary(),
                    }
                elif action.kind == "render.scene.load":
                    result = _render_scene_load(action_payload)
                elif action.kind == "render.scene.tick":
                    result = _render_scene_tick(action_payload, action_id=action.action_id)
                elif action.kind == "render.scene.unload":
                    result = _render_scene_unload(action_payload)
                elif action.kind == "render.scene.reconcile":
                    result = _render_scene_reconcile(action_payload)
                elif action.kind == "pygame.worker.enqueue":
                    command_kind = str(action_payload.get("command_kind", "runtime_action.forward")).strip().lower()
                    if command_kind == "":
                        command_kind = "runtime_action.forward"
                    runtime_action_kind = str(action_payload.get("runtime_action_kind", "")).strip()
                    if runtime_action_kind == "":
                        raise ValueError("runtime_action_kind_required")
                    command_payload_obj = action_payload.get("payload")
                    command_payload = (
                        cast(dict[str, object], command_payload_obj)
                        if isinstance(command_payload_obj, dict)
                        else {}
                    )
                    enqueue_receipt = self._pygame_worker.enqueue(
                        workspace_id=payload.workspace_id,
                        actor_id=payload.actor_id,
                        action_id=action.action_id,
                        command_kind=command_kind,
                        runtime_action_kind=runtime_action_kind,
                        payload=command_payload,
                    )
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": payload.actor_id,
                        "enqueue": enqueue_receipt,
                    }
                elif action.kind == "pygame.worker.status":
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": payload.actor_id,
                        "status": self._pygame_worker.status(),
                    }
                elif action.kind == "pygame.worker.dequeue":
                    max_items = max(1, min(256, self._int_from_table(action_payload.get("max_items"), 1)))
                    items: list[dict[str, object]] = []
                    for _ in range(max_items):
                        item = self._pygame_worker.dequeue_nowait()
                        if item is None:
                            break
                        items.append(item)
                    result = {
                        "workspace_id": payload.workspace_id,
                        "actor_id": payload.actor_id,
                        "dequeued_count": len(items),
                        "items": items,
                        "status": self._pygame_worker.status(),
                    }
                elif action.kind == "content.pack.load_canon":
                    pack_dir = str(action_payload.get("pack_dir", "gameplay/content_packs/canon")).strip()
                    if pack_dir == "":
                        pack_dir = "gameplay/content_packs/canon"
                    apply_to_db = bool(action_payload.get("apply_to_db", True))
                    target_actor_id = str(action_payload.get("actor_id", payload.actor_id)).strip()
                    if target_actor_id == "":
                        target_actor_id = payload.actor_id
                    result = self._load_canon_content_pack(
                        workspace_id=payload.workspace_id,
                        actor_id=target_actor_id,
                        workshop_id=workshop_id,
                        pack_dir=pack_dir,
                        apply_to_db=apply_to_db,
                    )
                elif action.kind == "content.pack.load_byte_table":
                    result = self._load_byte_table_into_layers(
                        workspace_id=payload.workspace_id,
                        actor_id=payload.actor_id,
                    )
                elif action.kind == "module.run":
                    module_id = str(action_payload.get("module_id", "")).strip()
                    expected_version = str(action_payload.get("module_version", "")).strip()
                    payload_overrides_obj = action_payload.get("payload_overrides")
                    payload_overrides = (
                        cast(dict[str, object], payload_overrides_obj)
                        if isinstance(payload_overrides_obj, dict)
                        else {}
                    )
                    spec = self._load_module_spec(module_id)
                    spec_version = str(spec.get("module_version", ""))
                    if expected_version != "" and expected_version != spec_version:
                        raise ValueError("module_version_mismatch")
                    execution_obj = spec.get("execution")
                    execution = cast(dict[str, object], execution_obj) if isinstance(execution_obj, dict) else {}
                    runtime_action_kind = str(execution.get("runtime_action_kind", "")).strip()
                    if runtime_action_kind == "":
                        raise ValueError("module_runtime_action_kind_required")
                    if runtime_action_kind == "module.run":
                        raise ValueError("module_run_recursion_disallowed")
                    inputs_obj = spec.get("inputs")
                    inputs = cast(dict[str, object], inputs_obj) if isinstance(inputs_obj, dict) else {}
                    base_payload_obj = inputs.get("payload")
                    base_payload = cast(dict[str, object], base_payload_obj) if isinstance(base_payload_obj, dict) else {}
                    merged_payload = self._deep_merge_map(base_payload, payload_overrides)
                    merged_payload.setdefault("workspace_id", payload.workspace_id)
                    merged_payload.setdefault("actor_id", payload.actor_id)
                    nested_run = self.consume_runtime_plan(
                        payload=RuntimeConsumeInput(
                            workspace_id=payload.workspace_id,
                            actor_id=payload.actor_id,
                            plan_id=f"{payload.plan_id}::{module_id}",
                            actions=[
                                RuntimeActionInput(
                                    action_id=f"{action.action_id}::exec",
                                    kind=cast(Any, runtime_action_kind),
                                    payload=merged_payload,
                                )
                            ],
                        ),
                        actor_id=actor_id,
                        workshop_id=workshop_id,
                    )
                    nested_action = nested_run.actions[0] if len(nested_run.actions) > 0 else None
                    if nested_action is None:
                        raise ValueError("module_nested_action_missing")
                    if not nested_action.ok:
                        raise ValueError(f"module_nested_failed:{nested_action.error}")
                    outputs_obj = spec.get("outputs")
                    outputs = cast(dict[str, object], outputs_obj) if isinstance(outputs_obj, dict) else {}
                    expected_refs_obj = outputs.get("expected_ref_keys")
                    expected_ref_keys = (
                        [str(item) for item in expected_refs_obj if str(item).strip() != ""]
                        if isinstance(expected_refs_obj, list)
                        else []
                    )
                    lineage_refs_obj = nested_action.result.get("lineage_node_refs")
                    lineage_refs = (
                        cast(dict[str, object], lineage_refs_obj)
                        if isinstance(lineage_refs_obj, dict)
                        else {}
                    )
                    available_ref_keys = sorted(str(key) for key in lineage_refs.keys())
                    missing_ref_keys = sorted(key for key in expected_ref_keys if key not in lineage_refs)
                    if len(missing_ref_keys) > 0:
                        raise ValueError(f"module_expected_refs_missing:{','.join(missing_ref_keys)}")
                    result = {
                        "module_id": module_id,
                        "module_version": spec_version,
                        "runtime_action_kind": runtime_action_kind,
                        "expected_ref_keys": expected_ref_keys,
                        "available_ref_keys": available_ref_keys,
                        "nested": nested_run.model_dump(),
                    }
                else:
                    raise ValueError(f"unsupported_runtime_action:{action.kind}")
                results.append(
                    RuntimeActionOut(
                        action_id=action.action_id,
                        kind=action.kind,
                        ok=True,
                        result=self._dict_result(result),
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive capture for file-driven plans
                results.append(
                    RuntimeActionOut(
                        action_id=action.action_id,
                        kind=action.kind,
                        ok=False,
                        error=str(exc),
                    )
                )
        applied_count = sum(1 for item in results if item.ok)
        failed_count = len(results) - applied_count
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "plan_id": payload.plan_id,
            "results": [item.model_dump(mode="json") for item in results],
        }
        out = RuntimeConsumeOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
            applied_count=applied_count,
            failed_count=failed_count,
            results=results,
            hash=self._canonical_hash(hash_payload),
        )
        if self._repo is not None and hasattr(self._repo, "create_runtime_plan_run"):
            plan_payload_json = self._canonical_json(
                {
                    "workspace_id": payload.workspace_id,
                    "actor_id": payload.actor_id,
                    "plan_id": payload.plan_id,
                    "actions": [item.model_dump(mode="json") for item in payload.actions],
                }
            )
            plan_hash = self._canonical_hash(
                {
                    "workspace_id": payload.workspace_id,
                    "actor_id": payload.actor_id,
                    "plan_id": payload.plan_id,
                    "actions": [item.model_dump(mode="json") for item in payload.actions],
                }
            )
            self._repo.create_runtime_plan_run(
                RuntimePlanRun(
                    workspace_id=payload.workspace_id,
                    actor_id=payload.actor_id,
                    plan_id=payload.plan_id,
                    plan_payload_json=plan_payload_json,
                    plan_hash=plan_hash,
                    result_json=self._canonical_json(out.model_dump(mode="json")),
                    result_hash=out.hash,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return out

    def replay_runtime_plan(
        self,
        *,
        payload: RuntimeReplayInput,
        actor_id: str,
        workshop_id: str,
    ) -> RuntimeReplayOut:
        repo = self._require_repo()
        baseline = repo.get_latest_runtime_plan_run(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
        )
        if baseline is None:
            raise ValueError("runtime_plan_not_found")
        plan_obj = self._json_to_object_map(baseline.plan_payload_json)
        actions_obj = plan_obj.get("actions")
        actions = actions_obj if isinstance(actions_obj, list) else []
        replay_in = RuntimeConsumeInput(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
            actions=actions,
        )
        replay_out = self.consume_runtime_plan(
            payload=replay_in,
            actor_id=actor_id,
            workshop_id=workshop_id,
        )
        return RuntimeReplayOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            plan_id=payload.plan_id,
            baseline_hash=baseline.result_hash,
            replay_hash=replay_out.hash,
            hash_match=baseline.result_hash == replay_out.hash,
            baseline_run_id=baseline.id,
            replay=replay_out,
        )

    def list_runtime_plan_runs(
        self,
        *,
        workspace_id: str,
        actor_id: str,
        plan_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[RuntimePlanRunOut]:
        repo = self._require_repo()
        actor = actor_id.strip()
        if actor == "":
            raise ValueError("actor_id_required")
        plan_filter = (plan_id or "").strip()
        max_rows = max(1, min(500, int(limit)))
        rows = list(repo.list_runtime_plan_runs_for_actor(workspace_id, actor, plan_filter if plan_filter != "" else None))

        out_rows: list[RuntimePlanRunOut] = []
        for row in rows[:max_rows]:
            result_obj = self._json_to_object_map(row.result_json)
            out_rows.append(
                RuntimePlanRunOut(
                    run_id=row.id,
                    workspace_id=row.workspace_id,
                    actor_id=row.actor_id,
                    plan_id=row.plan_id,
                    plan_hash=row.plan_hash,
                    result_hash=row.result_hash,
                    result_summary={
                        "applied_count": int(result_obj.get("applied_count", 0) or 0),
                        "failed_count": int(result_obj.get("failed_count", 0) or 0),
                        "hash": str(result_obj.get("hash", "")),
                    },
                    created_at=row.created_at,
                )
            )
        return out_rows

    def apply_djinn_influence(
        self,
        *,
        payload: DjinnApplyInput,
        actor_id: str,
        workshop_id: str,
        emit_kernel: bool = True,
    ) -> DjinnApplyOut:
        djinn_id = payload.djinn_id.strip().lower()
        if djinn_id not in self._DJINN_ALIGNMENT:
            raise ValueError("invalid_djinn")
        normalized_realm = payload.realm_id.strip().lower()
        normalized_ring = payload.ring_id.strip().lower()
        if djinn_id == "drovitth":
            if normalized_realm != "sulphera" or normalized_ring not in {"royal", "royalty"}:
                raise ValueError("drovitth_requires_sulphera_royalty_ring")

        target_frontiers = self._normalize_frontier_ids(payload.target_frontiers)
        frontier_effects: dict[str, str] = {}
        scarred_frontiers: list[str] = []
        opened_frontiers: list[str] = []
        placements: list[str] = []
        orrery_marks: list[DjinnOrreryMark] = []
        effect: str = "record"

        if djinn_id == "keshi":
            effect = "collapse"
            for frontier_id in target_frontiers:
                frontier_effects[frontier_id] = "collapsed"
                scarred_frontiers.append(frontier_id)
                token = self._safe_token(frontier_id)
                placements.append(f"entity scar_{token} 0 0 scar")
                orrery_marks.append(
                    DjinnOrreryMark(
                        mark_id=f"keshi:{token}:{payload.tick}",
                        source_djinn_id="keshi",
                        frontier_id=frontier_id,
                        effect="collapse",
                        tick=payload.tick,
                        note=payload.reason or "kernel_scar",
                    )
                )
        elif djinn_id == "giann":
            effect = "open"
            for frontier_id in target_frontiers:
                frontier_effects[frontier_id] = "opened"
                opened_frontiers.append(frontier_id)
                token = self._safe_token(frontier_id)
                placements.append(f"entity boon_{token} 0 0 boon")
                orrery_marks.append(
                    DjinnOrreryMark(
                        mark_id=f"giann:{token}:{payload.tick}",
                        source_djinn_id="giann",
                        frontier_id=frontier_id,
                        effect="open",
                        tick=payload.tick,
                        note=payload.reason or "player_boon",
                    )
                )
        else:
            effect = "record"
            placements.append("entity royal_orrery 0 0 instrument")
            observed = [
                mark
                for mark in payload.observed_marks
                if mark.source_djinn_id.strip().lower() in {"keshi", "giann"}
            ]
            orrery_marks = sorted(
                observed,
                key=lambda mark: (
                    int(mark.tick),
                    mark.source_djinn_id.strip().lower(),
                    mark.frontier_id,
                    mark.mark_id,
                ),
            )

        hash_payload: dict[str, object] = {
            "actor_id": payload.actor_id,
            "djinn_id": djinn_id,
            "effect": effect,
            "frontier_effects": frontier_effects,
            "scarred_frontiers": scarred_frontiers,
            "opened_frontiers": opened_frontiers,
            "placements": placements,
            "orrery_marks": [mark.model_dump() for mark in orrery_marks],
            "tick": payload.tick,
        }
        out = DjinnApplyOut(
            actor_id=payload.actor_id,
            djinn_id=cast(Any, djinn_id),
            alignment=self._DJINN_ALIGNMENT[djinn_id],
            effect=cast(Any, effect),
            applied=True,
            frontier_effects=frontier_effects,
            scarred_frontiers=scarred_frontiers,
            opened_frontiers=opened_frontiers,
            placements=placements,
            orrery_marks=orrery_marks,
            hash=self._canonical_hash(hash_payload),
        )
        if emit_kernel:
            self._kernel.place(
                raw=f"game.djinn.apply {payload.actor_id} {djinn_id} {effect}",
                context={
                    "workspace_id": payload.workspace_id,
                    "scene_id": payload.scene_id,
                    "realm_id": normalized_realm,
                    "ring_id": normalized_ring,
                    "rule": "djinn_apply_influence",
                    "result": out.model_dump(),
                },
                actor_id=actor_id,
                workshop_id=workshop_id,
            )
        return out

    def renderer_tables(
        self,
        *,
        payload: RendererTablesInput,
        actor_id: str,
        workshop_id: str,
    ) -> RendererTablesOut:
        tables: dict[str, object] = {}
        if payload.level is not None:
            tables["levels"] = self.apply_level_progress(
                payload=payload.level,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.skill is not None:
            tables["skills"] = self.train_skill(
                payload=payload.skill,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.perk is not None:
            tables["perks"] = self.unlock_perk(
                payload=payload.perk,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.alchemy is not None:
            tables["alchemy"] = self.craft_alchemy(
                payload=payload.alchemy,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.blacksmith is not None:
            tables["blacksmith"] = self.forge_blacksmith(
                payload=payload.blacksmith,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        market: dict[str, object] = {}
        if payload.market_quote is not None:
            market["quote"] = self.market_quote(
                payload=payload.market_quote,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.market_trade is not None:
            market["trade"] = self.market_trade(
                payload=payload.market_trade,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if market:
            tables["market"] = market
        vitriol: dict[str, object] = {}
        if payload.vitriol_apply is not None:
            vitriol["apply"] = self.vitriol_apply_ruler_influence(
                payload=payload.vitriol_apply,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if payload.vitriol_compute is not None:
            vitriol["compute"] = self.vitriol_compute(payload=payload.vitriol_compute).model_dump()
        if payload.vitriol_clear is not None:
            vitriol["clear"] = self.vitriol_clear_expired(
                payload=payload.vitriol_clear,
                actor_id=actor_id,
                workshop_id=workshop_id,
                emit_kernel=False,
            ).model_dump()
        if vitriol:
            tables["vitriol"] = vitriol

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "tables": tables,
        }
        return RendererTablesOut(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            hash=self._canonical_hash(hash_payload),
            tables=tables,
        )

    def build_isometric_render_contract(
        self,
        *,
        payload: IsometricRenderContractInput,
    ) -> IsometricRenderContractOut:
        tile_width = max(8, int(payload.tile_width))
        tile_height = max(4, int(payload.tile_height))
        elevation_step = max(1, int(payload.elevation_step))
        render_mode = str(payload.render_mode or "2.5d").strip().lower()
        if render_mode not in {"2.5d", "3d"}:
            raise ValueError(f"unsupported_render_mode:{render_mode}")
        camera_yaw_deg = max(-180.0, min(180.0, float(payload.camera_yaw_deg)))
        camera_pitch_deg = max(5.0, min(80.0, float(payload.camera_pitch_deg)))
        camera_zoom = max(0.25, min(4.0, float(payload.camera_zoom)))
        camera_pan_x = float(payload.camera_pan_x)
        camera_pan_y = float(payload.camera_pan_y)
        camera_yaw = math.radians(camera_yaw_deg)
        camera_pitch = math.radians(camera_pitch_deg)
        camera_cos_yaw = math.cos(camera_yaw)
        camera_sin_yaw = math.sin(camera_yaw)
        camera_cos_pitch = math.cos(camera_pitch)
        camera_sin_pitch = math.sin(camera_pitch)
        camera_focal = max(120.0, float(tile_width) * 3.6) * camera_zoom
        camera_depth_scale = max(8.0, float(tile_width) * 0.75)
        realm_id = payload.realm_id.strip().lower()
        scene = self.get_scene(
            workspace_id=payload.workspace_id,
            realm_id=realm_id,
            scene_id=payload.scene_id,
        )
        if scene is None:
            raise ValueError("scene_not_found")

        drawables: list[IsometricDrawableOut] = []
        scene_nodes_raw = scene.content.get("nodes")
        scene_nodes = scene_nodes_raw if isinstance(scene_nodes_raw, list) else []

        manifest_rows = self.list_asset_manifests(payload.workspace_id)
        sprite_lookup: dict[str, str] = {}
        material_lookup: dict[str, str] = {}
        atlas_version = "v1"
        material_pack_version = "v1"
        requested_pack_id = (payload.asset_pack_id or "").strip()
        for row in manifest_rows:
            if row.realm_id != realm_id:
                continue
            payload_obj = row.payload if isinstance(row.payload, dict) else {}
            if requested_pack_id != "":
                payload_pack_id = str(payload_obj.get("asset_pack_id") or "").strip()
                if row.manifest_id != requested_pack_id and payload_pack_id != requested_pack_id:
                    continue
            atlas_version_raw = payload_obj.get("atlas_version")
            if isinstance(atlas_version_raw, str) and atlas_version_raw.strip() != "":
                atlas_version = atlas_version_raw.strip()
            material_version_raw = payload_obj.get("material_pack_version")
            if isinstance(material_version_raw, str) and material_version_raw.strip() != "":
                material_pack_version = material_version_raw.strip()
            if row.kind.strip().lower() == "sprite":
                for key, value in payload_obj.items():
                    if key in {"atlas_version", "material_pack_version", "asset_pack_id"}:
                        continue
                    if isinstance(value, str):
                        sprite_lookup[str(key)] = value
            if row.kind.strip().lower() == "material":
                for key, value in payload_obj.items():
                    if key in {"atlas_version", "material_pack_version", "asset_pack_id"}:
                        continue
                    if isinstance(value, str):
                        material_lookup[str(key)] = value

        allowed_atlas_versions = {str(item).strip() for item in payload.renderer_atlas_versions if str(item).strip() != ""}
        if allowed_atlas_versions and atlas_version not in allowed_atlas_versions:
            raise ValueError(f"incompatible_atlas_version:{atlas_version}")
        allowed_material_versions = {str(item).strip() for item in payload.renderer_material_versions if str(item).strip() != ""}
        if allowed_material_versions and material_pack_version not in allowed_material_versions:
            raise ValueError(f"incompatible_material_pack_version:{material_pack_version}")

        missing_sprite = "placeholder://sprite/missing"
        fallback_count = 0

        def _resolve_sprite(*, explicit: str, lookup_key: str, kind: str) -> tuple[str, str]:
            if explicit != "":
                return explicit, "explicit"
            if lookup_key in sprite_lookup:
                return sprite_lookup[lookup_key], "lookup:key"
            if kind in sprite_lookup:
                return sprite_lookup[kind], "lookup:kind"
            if payload.strict_assets:
                raise ValueError(f"missing_sprite_asset:{lookup_key or kind}")
            return missing_sprite, "fallback:missing"

        def _resolve_material(*, explicit: str, kind: str) -> tuple[str, str]:
            if explicit != "":
                return explicit, "explicit"
            if kind in material_lookup:
                return material_lookup[kind], "lookup:kind"
            if payload.strict_assets:
                raise ValueError(f"missing_material_asset:{kind}")
            return "default", "fallback:default"

        def _resolve_aster_color_from_metadata(meta: dict[str, object]) -> tuple[str | None, str | None]:
            return self._resolve_aster_metadata(meta)

        def _project_position(*, x: float, y: float, z: int) -> tuple[float, float, float]:
            if render_mode == "2.5d":
                screen_x = (x - y) * (tile_width / 2.0)
                screen_y = (x + y) * (tile_height / 2.0) - (z * elevation_step)
                depth_key = (x + y) + (z * 0.01)
                return screen_x, screen_y, depth_key
            wx = x
            wy = y
            wz = float(z)
            rot_x = (wx * camera_cos_yaw) - (wy * camera_sin_yaw)
            rot_y = (wx * camera_sin_yaw) + (wy * camera_cos_yaw)
            depth_y = (rot_y * camera_cos_pitch) - (wz * camera_sin_pitch)
            elev_z = (rot_y * camera_sin_pitch) + (wz * camera_cos_pitch)
            depth = max(-camera_focal * 0.6, depth_y * camera_depth_scale)
            scale = camera_focal / max(24.0, camera_focal + depth)
            screen_x = (rot_x * tile_width * 1.15 * scale) + camera_pan_x
            screen_y = (depth_y * tile_height * 0.28 * scale) - (elev_z * elevation_step * 1.35 * scale) + camera_pan_y
            depth_key = depth_y + (elev_z * 0.2)
            return screen_x, screen_y, depth_key

        for index, node in enumerate(scene_nodes):
            if not isinstance(node, dict):
                continue
            metadata_obj = node.get("metadata")
            metadata = metadata_obj if isinstance(metadata_obj, dict) else {}
            x = float(node.get("x") or 0.0)
            y = float(node.get("y") or 0.0)
            z = self._int_from_table(metadata.get("z"), 0)
            node_id = str(node.get("node_id") or f"scene_node_{index}")
            kind = str(node.get("kind") or "entity")
            sprite, sprite_source = _resolve_sprite(
                explicit=str(metadata.get("sprite") or ""),
                lookup_key=node_id,
                kind=kind,
            )
            material, material_source = _resolve_material(
                explicit=str(metadata.get("material") or ""),
                kind=kind,
            )
            screen_x, screen_y, depth_key = _project_position(x=x, y=y, z=z)
            out_meta = dict(metadata)
            aster_color, rgb = _resolve_aster_color_from_metadata(out_meta)
            if aster_color is not None and rgb is not None:
                out_meta["aster_color"] = aster_color
                out_meta["rgb"] = rgb
                out_meta["color"] = rgb
            if sprite_source.startswith("fallback") or material_source.startswith("fallback"):
                fallback_count += 1
                out_meta["asset_fallback"] = {
                    "sprite_source": sprite_source,
                    "material_source": material_source,
                }
            if payload.include_material_constraints:
                akinenwun = str(metadata.get("akinenwun") or "").strip()
                if akinenwun != "":
                    try:
                        from qqva.shygazun_compiler import compile_akinenwun_to_ir, derive_render_constraints

                        constraints = derive_render_constraints(compile_akinenwun_to_ir(akinenwun))
                        out_meta["render_constraints"] = constraints
                    except Exception:
                        out_meta["render_constraints"] = {"status": "unavailable"}
            drawables.append(
                IsometricDrawableOut(
                    drawable_id=node_id,
                    source="scene",
                    kind=kind,
                    x=x,
                    y=y,
                    z=z,
                    screen_x=screen_x,
                    screen_y=screen_y,
                    depth_key=depth_key,
                    sprite=sprite,
                    material=material,
                    aster_color=aster_color,
                    rgb=rgb,
                    metadata=out_meta,
                )
            )

        world_regions = self.list_world_regions(workspace_id=payload.workspace_id, realm_id=realm_id)
        for row in world_regions:
            if not payload.include_unloaded_regions and not row.loaded:
                continue
            entities_obj = row.payload.get("entities")
            entities = entities_obj if isinstance(entities_obj, list) else []
            for index, entity in enumerate(entities):
                if isinstance(entity, str):
                    entity_id = entity
                    ex = float(index)
                    ey = 0.0
                    ez = 0
                    kind = "region_entity"
                    meta: dict[str, object] = {}
                    sprite, sprite_source = _resolve_sprite(
                        explicit="",
                        lookup_key=entity_id,
                        kind=kind,
                    )
                    material, material_source = _resolve_material(
                        explicit="",
                        kind=kind,
                    )
                elif isinstance(entity, dict):
                    entity_id = str(entity.get("id") or entity.get("entity_id") or f"{row.region_key}:{index}")
                    ex = float(entity.get("x") or index)
                    ey = float(entity.get("y") or 0.0)
                    ez = self._int_from_table(entity.get("z"), 0)
                    kind = str(entity.get("kind") or entity.get("tag") or "region_entity")
                    meta = dict(entity.get("metadata") or {}) if isinstance(entity.get("metadata"), dict) else {}
                    sprite, sprite_source = _resolve_sprite(
                        explicit=str(entity.get("sprite") or ""),
                        lookup_key=entity_id,
                        kind=kind,
                    )
                    material, material_source = _resolve_material(
                        explicit=str(entity.get("material") or ""),
                        kind=kind,
                    )
                else:
                    continue
                aster_color, rgb = _resolve_aster_color_from_metadata(meta)
                if aster_color is not None and rgb is not None:
                    meta["aster_color"] = aster_color
                    meta["rgb"] = rgb
                    meta["color"] = rgb
                screen_x, screen_y, depth_key = _project_position(x=ex, y=ey, z=ez)
                if sprite_source.startswith("fallback") or material_source.startswith("fallback"):
                    fallback_count += 1
                    meta["asset_fallback"] = {
                        "sprite_source": sprite_source,
                        "material_source": material_source,
                    }
                drawables.append(
                    IsometricDrawableOut(
                        drawable_id=f"{row.region_key}:{entity_id}",
                        source="region",
                        kind=kind,
                        x=ex,
                        y=ey,
                        z=ez,
                        screen_x=screen_x,
                        screen_y=screen_y,
                        depth_key=depth_key,
                        sprite=sprite,
                        material=material,
                        aster_color=aster_color,
                        rgb=rgb,
                        metadata=meta,
                    )
                )

        drawables.sort(
            key=lambda item: (
                item.depth_key,
                item.screen_y,
                item.screen_x,
                item.drawable_id,
            )
        )
        projection_type = "isometric_2_5d" if render_mode == "2.5d" else "projection_3d"
        projection: dict[str, object] = {
            "type": projection_type,
            "tile_width": tile_width,
            "tile_height": tile_height,
            "elevation_step": elevation_step,
        }
        if render_mode == "3d":
            projection["camera"] = {
                "yaw_deg": camera_yaw_deg,
                "pitch_deg": camera_pitch_deg,
                "zoom": camera_zoom,
                "pan_x": camera_pan_x,
                "pan_y": camera_pan_y,
            }
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "realm_id": realm_id,
            "scene_id": payload.scene_id,
            "render_mode": render_mode,
            "projection": projection,
            "asset_pack": {
                "asset_pack_id": requested_pack_id if requested_pack_id != "" else None,
                "atlas_version": atlas_version,
                "material_pack_version": material_pack_version,
                "fallback_sprite": missing_sprite,
            },
            "drawables": [item.model_dump() for item in drawables],
        }
        return IsometricRenderContractOut(
            workspace_id=payload.workspace_id,
            realm_id=realm_id,
            scene_id=payload.scene_id,
            render_mode=render_mode,
            projection=projection,
            asset_pack={
                "asset_pack_id": requested_pack_id if requested_pack_id != "" else None,
                "atlas_version": atlas_version,
                "material_pack_version": material_pack_version,
                "fallback_sprite": missing_sprite,
            },
            drawable_count=len(drawables),
            drawables=drawables,
            stats={
                "scene_nodes": len(scene_nodes),
                "region_count": len(world_regions),
                "asset_manifest_count": len(manifest_rows),
                "fallback_count": fallback_count,
            },
            hash=self._canonical_hash(hash_payload),
        )

    def renderer_asset_diagnostics(
        self,
        *,
        payload: RendererAssetDiagnosticsInput,
    ) -> RendererAssetDiagnosticsOut:
        realm_id = payload.realm_id.strip().lower()
        scene = self.get_scene(
            workspace_id=payload.workspace_id,
            realm_id=realm_id,
            scene_id=payload.scene_id,
        )
        if scene is None:
            raise ValueError("scene_not_found")
        requested_pack_id = (payload.asset_pack_id or "").strip()
        manifest_rows = self.list_asset_manifests(payload.workspace_id)
        selected_manifest_count = 0
        sprite_lookup: dict[str, str] = {}
        material_lookup: dict[str, str] = {}
        atlas_version = "v1"
        material_pack_version = "v1"
        reserved_keys = {"atlas_version", "material_pack_version", "asset_pack_id"}
        for row in manifest_rows:
            if row.realm_id != realm_id:
                continue
            payload_obj = row.payload if isinstance(row.payload, dict) else {}
            if requested_pack_id != "":
                payload_pack_id = str(payload_obj.get("asset_pack_id") or "").strip()
                if row.manifest_id != requested_pack_id and payload_pack_id != requested_pack_id:
                    continue
            selected_manifest_count += 1
            atlas_version_raw = payload_obj.get("atlas_version")
            if isinstance(atlas_version_raw, str) and atlas_version_raw.strip() != "":
                atlas_version = atlas_version_raw.strip()
            material_version_raw = payload_obj.get("material_pack_version")
            if isinstance(material_version_raw, str) and material_version_raw.strip() != "":
                material_pack_version = material_version_raw.strip()
            kind = row.kind.strip().lower()
            if kind == "sprite":
                for key, value in payload_obj.items():
                    if key in reserved_keys:
                        continue
                    if isinstance(value, str) and value.strip() != "":
                        sprite_lookup[str(key)] = value.strip()
            if kind == "material":
                for key, value in payload_obj.items():
                    if key in reserved_keys:
                        continue
                    if isinstance(value, str) and value.strip() != "":
                        material_lookup[str(key)] = value.strip()

        scene_nodes_raw = scene.content.get("nodes")
        scene_nodes = scene_nodes_raw if isinstance(scene_nodes_raw, list) else []
        candidates: list[tuple[str, str, str, str]] = []
        for index, node in enumerate(scene_nodes):
            if not isinstance(node, dict):
                continue
            metadata_obj = node.get("metadata")
            metadata = metadata_obj if isinstance(metadata_obj, dict) else {}
            node_id = str(node.get("node_id") or f"scene_node_{index}")
            kind = str(node.get("kind") or "entity")
            explicit_sprite = str(metadata.get("sprite") or "")
            explicit_material = str(metadata.get("material") or "")
            candidates.append((node_id, kind, explicit_sprite.strip(), explicit_material.strip()))

        world_regions = self.list_world_regions(workspace_id=payload.workspace_id, realm_id=realm_id)
        for row in world_regions:
            if not payload.include_unloaded_regions and not row.loaded:
                continue
            entities_obj = row.payload.get("entities")
            entities = entities_obj if isinstance(entities_obj, list) else []
            for index, entity in enumerate(entities):
                if isinstance(entity, str):
                    entity_id = entity
                    kind = "region_entity"
                    explicit_sprite = ""
                    explicit_material = ""
                elif isinstance(entity, dict):
                    entity_id = str(entity.get("id") or entity.get("entity_id") or f"{row.region_key}:{index}")
                    kind = str(entity.get("kind") or entity.get("tag") or "region_entity")
                    explicit_sprite = str(entity.get("sprite") or "").strip()
                    explicit_material = str(entity.get("material") or "").strip()
                else:
                    continue
                candidates.append((f"{row.region_key}:{entity_id}", kind, explicit_sprite, explicit_material))

        missing_sprites: list[str] = []
        missing_materials: list[str] = []
        for candidate_id, kind, explicit_sprite, explicit_material in candidates:
            has_sprite = explicit_sprite != "" or candidate_id in sprite_lookup or kind in sprite_lookup
            if not has_sprite:
                missing_sprites.append(candidate_id)
            has_material = explicit_material != "" or kind in material_lookup
            if not has_material:
                missing_materials.append(candidate_id)

        invalid_sprite_refs: list[str] = []
        for key, value in sprite_lookup.items():
            valid = value.startswith(("placeholder://", "atlas://", "http://", "https://", "/")) or "/" in value
            if not valid:
                invalid_sprite_refs.append(f"{key}:{value}")
        invalid_material_refs: list[str] = []
        for key, value in material_lookup.items():
            if value.strip() == "":
                invalid_material_refs.append(f"{key}:{value}")

        missing_sprites = sorted(set(missing_sprites))
        missing_materials = sorted(set(missing_materials))
        invalid_sprite_refs = sorted(set(invalid_sprite_refs))
        invalid_material_refs = sorted(set(invalid_material_refs))
        ok = len(missing_sprites) == 0 and len(missing_materials) == 0 and len(invalid_sprite_refs) == 0 and len(invalid_material_refs) == 0
        if payload.strict_assets and (len(missing_sprites) > 0 or len(missing_materials) > 0):
            ok = False
        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "realm_id": realm_id,
            "scene_id": payload.scene_id,
            "asset_pack_id": requested_pack_id if requested_pack_id != "" else None,
            "atlas_version": atlas_version,
            "material_pack_version": material_pack_version,
            "missing_sprites": missing_sprites,
            "missing_materials": missing_materials,
            "invalid_sprite_refs": invalid_sprite_refs,
            "invalid_material_refs": invalid_material_refs,
            "candidate_count": len(candidates),
            "scene_node_count": len(scene_nodes),
            "manifest_count": selected_manifest_count,
            "sprite_entry_count": len(sprite_lookup),
            "material_entry_count": len(material_lookup),
        }
        return RendererAssetDiagnosticsOut(
            workspace_id=payload.workspace_id,
            realm_id=realm_id,
            scene_id=payload.scene_id,
            asset_pack_id=requested_pack_id if requested_pack_id != "" else None,
            atlas_version=atlas_version,
            material_pack_version=material_pack_version,
            manifest_count=selected_manifest_count,
            scene_node_count=len(scene_nodes),
            candidate_count=len(candidates),
            sprite_entry_count=len(sprite_lookup),
            material_entry_count=len(material_lookup),
            missing_sprites=missing_sprites,
            missing_materials=missing_materials,
            invalid_sprite_refs=invalid_sprite_refs,
            invalid_material_refs=invalid_material_refs,
            ok=ok,
            hash=self._canonical_hash(hash_payload),
        )

    def build_render_graph_contract(
        self,
        *,
        payload: RenderGraphContractInput,
    ) -> RenderGraphContractOut:
        iso = self.build_isometric_render_contract(
            payload=IsometricRenderContractInput(
                workspace_id=payload.workspace_id,
                realm_id=payload.realm_id,
                scene_id=payload.scene_id,
                render_mode=payload.render_mode,
                asset_pack_id=payload.asset_pack_id,
                strict_assets=payload.strict_assets,
                renderer_atlas_versions=payload.renderer_atlas_versions,
                renderer_material_versions=payload.renderer_material_versions,
                camera_yaw_deg=payload.camera_yaw_deg,
                camera_pitch_deg=payload.camera_pitch_deg,
                camera_zoom=payload.camera_zoom,
                camera_pan_x=payload.camera_pan_x,
                camera_pan_y=payload.camera_pan_y,
                include_unloaded_regions=payload.include_unloaded_regions,
                include_material_constraints=payload.include_material_constraints,
            )
        )
        nodes: list[RenderGraphNodeOut] = []
        for drawable in iso.drawables:
            nodes.append(
                RenderGraphNodeOut(
                    node_id=drawable.drawable_id,
                    source=drawable.source,
                    kind=drawable.kind,
                    transform={
                        "position": {"x": drawable.x, "y": float(drawable.z), "z": drawable.y},
                        "screen_hint": {"x": drawable.screen_x, "y": drawable.screen_y},
                        "depth_key": drawable.depth_key,
                    },
                    material=drawable.material,
                    sprite=drawable.sprite,
                    aster_color=drawable.aster_color,
                    rgb=drawable.rgb,
                    metadata=drawable.metadata,
                )
            )

        hash_payload: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "realm_id": payload.realm_id.strip().lower(),
            "scene_id": payload.scene_id,
            "render_mode": iso.render_mode,
            "coordinate_space": payload.coordinate_space,
            "nodes": [item.model_dump() for item in nodes],
            "asset_pack": iso.asset_pack,
        }
        return RenderGraphContractOut(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            scene_id=payload.scene_id,
            render_mode=iso.render_mode,
            coordinate_space=payload.coordinate_space,
            node_count=len(nodes),
            nodes=nodes,
            asset_pack=iso.asset_pack,
            stats={
                **iso.stats,
                "source_contract": str(iso.projection.get("type") or "isometric_2_5d"),
            },
            hash=self._canonical_hash(hash_payload),
        )

    def list_suppliers(self, workspace_id: str) -> Sequence[SupplierOut]:
        rows = self._require_repo().list_suppliers(workspace_id=workspace_id)
        return [SupplierOut.model_validate(row, from_attributes=True) for row in rows]

    def create_supplier(self, payload: SupplierCreate) -> SupplierOut:
        row = Supplier(
            workspace_id=payload.workspace_id,
            supplier_name=payload.supplier_name,
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            contact_phone=payload.contact_phone,
            notes=payload.notes,
        )
        out = self._require_repo().create_supplier(row)
        return SupplierOut.model_validate(out, from_attributes=True)

    def create_public_inquiry(self, payload: PublicCommissionInquiryCreate) -> LeadOut:
        row = Lead(
            workspace_id=payload.workspace_id,
            full_name=payload.full_name,
            email=payload.email,
            details=payload.details,
            status="new",
            source="public_commission_hall",
        )
        out = self._require_repo().create_lead(row)
        return LeadOut.model_validate(out, from_attributes=True)

    @staticmethod
    def _shop_tags_from_json(raw: str) -> list[str]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip() != ""]
        return []

    @staticmethod
    def _shop_tags_to_json(tags: list[str]) -> str:
        clean = [str(tag).strip() for tag in tags if str(tag).strip() != ""]
        return json.dumps(clean, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def _shop_item_out(cls, row: ShopItem) -> ShopItemOut:
        return ShopItemOut(
            id=row.id,
            workspace_id=row.workspace_id,
            artisan_id=row.artisan_id,
            artisan_profile_name=row.artisan_profile_name,
            artisan_profile_email=row.artisan_profile_email,
            section_id=row.section_id,
            title=row.title,
            summary=row.summary,
            price_label=row.price_label,
            tags=cls._shop_tags_from_json(row.tags_json),
            link_url=row.link_url,
            visible=row.visible,
            steward_approved=row.steward_approved,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_shop_items(
        self,
        *,
        workspace_id: str,
        artisan_id: str | None = None,
        section_id: str | None = None,
        include_hidden: bool = True,
    ) -> Sequence[ShopItemOut]:
        rows = self._require_repo().list_shop_items(
            workspace_id=workspace_id,
            artisan_id=artisan_id,
            section_id=section_id,
            include_hidden=include_hidden,
        )
        return [self._shop_item_out(row) for row in rows]

    def get_shop_item(self, *, workspace_id: str, item_id: str) -> ShopItemOut:
        repo = self._require_repo()
        row = repo.get_shop_item(workspace_id=workspace_id, item_id=item_id)
        if row is None:
            raise ValueError("shop_item_not_found")
        return self._shop_item_out(row)

    def create_shop_item(
        self,
        *,
        payload: ShopItemCreate,
        artisan_id: str,
        workshop_id: str,
    ) -> ShopItemOut:
        repo = self._require_repo()
        artisan = repo.get_artisan_account(artisan_id)
        if artisan is None:
            raise ValueError("artisan_not_found")
        if artisan.workshop_id != workshop_id:
            raise ValueError("artisan_workshop_mismatch")
        now = datetime.utcnow()
        row = ShopItem(
            workspace_id=payload.workspace_id,
            artisan_id=artisan_id,
            artisan_profile_name=artisan.profile_name,
            artisan_profile_email=artisan.profile_email,
            section_id=payload.section_id.strip().lower(),
            title=payload.title.strip(),
            summary=payload.summary.strip(),
            price_label=payload.price_label.strip(),
            tags_json=self._shop_tags_to_json(payload.tags),
            link_url=payload.link_url.strip(),
            visible=False,
            steward_approved=False,
            approved_by="",
            approved_at=None,
            created_at=now,
            updated_at=now,
        )
        saved = repo.create_shop_item(row)
        return self._shop_item_out(saved)

    def update_shop_item(
        self,
        *,
        workspace_id: str,
        item_id: str,
        payload: ShopItemUpdate,
        artisan_id: str,
        is_steward: bool,
    ) -> ShopItemOut:
        repo = self._require_repo()
        row = repo.get_shop_item(workspace_id=workspace_id, item_id=item_id)
        if row is None:
            raise ValueError("shop_item_not_found")
        if not is_steward and row.artisan_id != artisan_id:
            raise ValueError("shop_item_forbidden")

        if payload.section_id is not None:
            row.section_id = payload.section_id.strip().lower()
        if payload.title is not None:
            row.title = payload.title.strip()
        if payload.summary is not None:
            row.summary = payload.summary.strip()
        if payload.price_label is not None:
            row.price_label = payload.price_label.strip()
        if payload.tags is not None:
            row.tags_json = self._shop_tags_to_json(payload.tags)
        if payload.link_url is not None:
            row.link_url = payload.link_url.strip()
        row.updated_at = datetime.utcnow()
        saved = repo.update_shop_item(row)
        return self._shop_item_out(saved)

    def set_shop_item_visibility(
        self,
        *,
        workspace_id: str,
        item_id: str,
        payload: ShopItemVisibilityUpdate,
        steward_id: str,
    ) -> ShopItemOut:
        repo = self._require_repo()
        row = repo.get_shop_item(workspace_id=workspace_id, item_id=item_id)
        if row is None:
            raise ValueError("shop_item_not_found")
        row.visible = payload.visible
        if payload.visible:
            row.steward_approved = True
            row.approved_by = steward_id
            row.approved_at = datetime.utcnow()
        else:
            row.steward_approved = False
            row.approved_by = steward_id
            row.approved_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        saved = repo.update_shop_item(row)
        return self._shop_item_out(saved)

    def list_public_commission_quotes(self, workspace_id: str) -> Sequence[PublicCommissionQuoteOut]:
        rows = self._require_repo().list_public_quotes(workspace_id=workspace_id)
        return [
            PublicCommissionQuoteOut(
                id=row.id,
                workspace_id=row.workspace_id,
                title=row.title,
                amount_cents=row.amount_cents,
                currency=row.currency,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def list_asset_manifests(self, workspace_id: str) -> Sequence[AssetManifestOut]:
        rows = self._require_repo().list_asset_manifests(workspace_id=workspace_id)
        return [
            AssetManifestOut(
                id=row.id,
                workspace_id=row.workspace_id,
                realm_id=row.realm_id,
                manifest_id=row.manifest_id,
                name=row.name,
                kind=row.kind,
                payload=self._json_to_object_map(row.payload_json),
                payload_hash=row.payload_hash,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_asset_manifest(self, payload: AssetManifestCreate) -> AssetManifestOut:
        payload_hash = self._canonical_hash(payload.payload)
        row = AssetManifest(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower() or "lapidus",
            manifest_id=payload.manifest_id,
            name=payload.name,
            kind=payload.kind,
            payload_json=self._canonical_json(payload.payload),
            payload_hash=payload_hash,
        )
        saved = self._require_repo().create_asset_manifest(row)
        return AssetManifestOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            manifest_id=saved.manifest_id,
            name=saved.name,
            kind=saved.kind,
            payload=self._json_to_object_map(saved.payload_json),
            payload_hash=saved.payload_hash,
            created_at=saved.created_at,
        )

    def list_realms(self) -> Sequence[RealmOut]:
        rows = self._require_repo().list_realms()
        return [
            RealmOut(
                id=row.id,
                slug=row.slug,
                name=row.name,
                description=row.description,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def validate_realm(self, payload: RealmValidateInput) -> RealmValidateOut:
        slug = payload.realm_id.strip().lower()
        row = self._require_repo().get_realm_by_slug(slug)
        if row is None:
            return RealmValidateOut(realm_id=payload.realm_id, ok=False, reason="unknown_realm")
        return RealmValidateOut(realm_id=row.slug, ok=True, reason="ok")

    def validate_content(self, payload: ContentValidateInput) -> ContentValidateOut:
        realm_validation = self.validate_realm(RealmValidateInput(realm_id=payload.realm_id))
        errors: list[str] = []
        warnings: list[str] = []
        stats: dict[str, object] = {}
        if not realm_validation.ok:
            errors.append(f"unknown_realm:{payload.realm_id}")
        if payload.source == "cobra":
            result = validate_cobra_content(payload.payload, realm_id=payload.realm_id, scene_id=payload.scene_id)
        else:
            result = validate_json_content(payload.payload, realm_id=payload.realm_id, scene_id=payload.scene_id)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
        stats.update(result.stats)
        if payload.strict_bilingual:
            bilingual_warnings = [warning for warning in warnings if warning.startswith("bilingual_")]
            errors.extend(bilingual_warnings)
        ok = len(errors) == 0
        return ContentValidateOut(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id,
            scene_id=payload.scene_id,
            source=payload.source,
            ok=ok,
            errors=errors,
            warnings=warnings,
            stats=stats,
        )

    def list_scenes(self, workspace_id: str, realm_id: str | None = None) -> Sequence[SceneOut]:
        rows = self._require_repo().list_scenes(workspace_id=workspace_id, realm_id=realm_id)
        return [
            SceneOut(
                id=row.id,
                workspace_id=row.workspace_id,
                realm_id=row.realm_id,
                scene_id=row.scene_id,
                name=row.name,
                description=row.description,
                content=self._json_to_object_map(row.content_json),
                content_hash=row.content_hash,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> SceneOut | None:
        row = self._require_repo().get_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id)
        if row is None:
            return None
        return SceneOut(
            id=row.id,
            workspace_id=row.workspace_id,
            realm_id=row.realm_id,
            scene_id=row.scene_id,
            name=row.name,
            description=row.description,
            content=self._json_to_object_map(row.content_json),
            content_hash=row.content_hash,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_scene(self, payload: SceneCreateInput) -> SceneOut:
        realm_error = validate_scene_realm(payload.scene_id, payload.realm_id)
        if realm_error:
            raise ValueError(realm_error)
        self._validate_aster_scene_content(payload.content)
        content_hash = self._canonical_hash(payload.content)
        row = Scene(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            scene_id=payload.scene_id.strip(),
            name=payload.name,
            description=payload.description,
            content_json=self._canonical_json(payload.content),
            content_hash=content_hash,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        saved = self._require_repo().create_scene(row)
        return SceneOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            scene_id=saved.scene_id,
            name=saved.name,
            description=saved.description,
            content=self._json_to_object_map(saved.content_json),
            content_hash=saved.content_hash,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    def update_scene(self, workspace_id: str, realm_id: str, scene_id: str, payload: SceneUpdateInput) -> SceneOut:
        row = self._require_repo().get_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id)
        if row is None:
            raise ValueError("scene_not_found")
        if payload.name is not None:
            row.name = payload.name
        if payload.description is not None:
            row.description = payload.description
        if payload.content is not None:
            self._validate_aster_scene_content(payload.content)
            row.content_json = self._canonical_json(payload.content)
            row.content_hash = self._canonical_hash(payload.content)
        row.updated_at = datetime.utcnow()
        saved = self._require_repo().save_scene(row)
        return SceneOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            scene_id=saved.scene_id,
            name=saved.name,
            description=saved.description,
            content=self._json_to_object_map(saved.content_json),
            content_hash=saved.content_hash,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    def emit_scene_from_library(
        self,
        *,
        workspace_id: str,
        realm_id: str,
        scene_id: str,
        actor_id: str,
        workshop_id: str,
    ) -> SceneEmitOut:
        row = self._require_repo().get_scene(workspace_id=workspace_id, realm_id=realm_id, scene_id=scene_id)
        if row is None:
            raise ValueError("scene_not_found")
        content = self._json_to_object_map(row.content_json)
        nodes_obj = content.get("nodes")
        edges_obj = content.get("edges")
        if not isinstance(nodes_obj, list) or not isinstance(edges_obj, list):
            raise ValueError("scene_graph_invalid")
        payload = SceneGraphEmitInput(
            workspace_id=workspace_id,
            realm_id=realm_id,
            scene_id=scene_id,
            nodes=nodes_obj,
            edges=edges_obj,
        )
        result = self.emit_scene_graph(payload=payload, actor_id=actor_id, workshop_id=workshop_id)
        return SceneEmitOut(
            scene_id=result.scene_id,
            nodes_emitted=result.nodes_emitted,
            edges_emitted=result.edges_emitted,
        )

    def create_scene_from_cobra(self, payload: SceneCompileInput) -> SceneOut:
        content = build_scene_graph_content_from_cobra(
            payload.cobra_source,
            realm_id=payload.realm_id,
            scene_id=payload.scene_id,
        )
        create_payload = SceneCreateInput(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id,
            scene_id=payload.scene_id,
            name=payload.name,
            description=payload.description,
            content=content,
        )
        return self.create_scene(create_payload)

    def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[WorldRegionOut]:
        rows = self._require_repo().list_world_regions(workspace_id=workspace_id, realm_id=realm_id)
        return [
            WorldRegionOut(
                id=row.id,
                workspace_id=row.workspace_id,
                realm_id=row.realm_id,
                region_key=row.region_key,
                payload=self._json_to_object_map(row.payload_json),
                payload_hash=row.payload_hash,
                cache_policy=row.cache_policy,
                loaded=row.loaded,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    @staticmethod
    def _region_id(realm_id: str, region_key: str) -> str:
        return f"{realm_id.strip().lower()}::{region_key.strip()}"

    def _reconcile_world_stream_loaded_flags(
        self,
        *,
        workspace_id: str,
        recently_loaded_row: WorldRegion,
    ) -> None:
        repo = self._require_repo()
        rows = list(repo.list_world_regions(workspace_id=workspace_id, realm_id=None))
        loaded_regions: dict[str, object] = {}
        for row in rows:
            if not row.loaded:
                continue
            loaded_regions[self._region_id(row.realm_id, row.region_key)] = {
                "realm_id": row.realm_id,
                "region_key": row.region_key,
                "payload": self._json_to_object_map(row.payload_json),
                "payload_hash": row.payload_hash,
                "cache_policy": row.cache_policy,
                "loaded_at": row.updated_at.isoformat() if row.updated_at else row.created_at.isoformat(),
            }

        projected_state = self._world_stream.load(
            {"world_stream": {"loaded_regions": loaded_regions}},
            realm_id=recently_loaded_row.realm_id,
            region_key=recently_loaded_row.region_key,
            payload=self._json_to_object_map(recently_loaded_row.payload_json),
            payload_hash=recently_loaded_row.payload_hash,
            cache_policy=recently_loaded_row.cache_policy,
        )
        world_stream_obj = projected_state.get("world_stream")
        projected_loaded_obj = (
            world_stream_obj.get("loaded_regions") if isinstance(world_stream_obj, dict) else {}
        )
        projected_loaded = projected_loaded_obj if isinstance(projected_loaded_obj, dict) else {}
        projected_ids = {str(key) for key in projected_loaded.keys()}
        now = datetime.utcnow()
        for row in rows:
            region_id = self._region_id(row.realm_id, row.region_key)
            should_be_loaded = region_id in projected_ids
            if row.loaded != should_be_loaded:
                row.loaded = should_be_loaded
                row.updated_at = now
                repo.save_world_region(row)

    def world_stream_status(self, workspace_id: str, realm_id: str | None = None) -> WorldStreamStatusOut:
        normalized_realm = realm_id.strip().lower() if isinstance(realm_id, str) and realm_id.strip() != "" else None
        rows = self._require_repo().list_world_regions(workspace_id=workspace_id, realm_id=normalized_realm)
        total_regions = len(rows)
        loaded_rows = [row for row in rows if row.loaded]
        policy_counts: dict[str, int] = {"cache": 0, "stream": 0, "pin": 0}
        for row in loaded_rows:
            policy = row.cache_policy.strip().lower()
            if policy in policy_counts:
                policy_counts[policy] += 1
            else:
                policy_counts[policy] = policy_counts.get(policy, 0) + 1
        capacity = self._world_stream.max_loaded_regions
        loaded_count = len(loaded_rows)
        unloaded_count = max(0, total_regions - loaded_count)
        pressure = 0.0 if capacity <= 0 else float(loaded_count) / float(capacity)
        pressure_components = {
            "stream_occupancy": pressure,
            "demon_total": 0.0,
            "composite": pressure,
        }
        return WorldStreamStatusOut(
            workspace_id=workspace_id,
            realm_id=normalized_realm,
            total_regions=total_regions,
            loaded_count=loaded_count,
            unloaded_count=unloaded_count,
            capacity=capacity,
            pressure=pressure,
            policy_counts=policy_counts,
            pressure_components=pressure_components,
            demon_pressures=dict(self._DEMON_PRESSURE_DEFAULTS),
            demon_maladies=dict(self._DEMON_MALADY_DOMAINS),
        )

    def load_world_region(self, payload: WorldRegionLoadInput) -> WorldRegionOut:
        realm_validation = self.validate_realm(RealmValidateInput(realm_id=payload.realm_id))
        if not realm_validation.ok:
            raise ValueError(f"unknown_realm:{payload.realm_id}")
        region_key = payload.region_key.strip()
        if not region_key:
            raise ValueError("region_key_required")
        cache_policy = payload.cache_policy.strip().lower() or "cache"
        if cache_policy not in {"cache", "stream", "pin"}:
            raise ValueError("invalid_cache_policy")
        repo = self._require_repo()
        existing = repo.get_world_region(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            region_key=region_key,
        )
        payload_hash = self._canonical_hash(payload.payload)
        now = datetime.utcnow()
        if existing is None:
            row = WorldRegion(
                workspace_id=payload.workspace_id,
                realm_id=payload.realm_id.strip().lower(),
                region_key=region_key,
                payload_json=self._canonical_json(payload.payload),
                payload_hash=payload_hash,
                cache_policy=cache_policy,
                loaded=True,
                created_at=now,
                updated_at=now,
            )
            saved = repo.create_world_region(row)
        else:
            existing.payload_json = self._canonical_json(payload.payload)
            existing.payload_hash = payload_hash
            existing.cache_policy = cache_policy
            existing.loaded = True
            existing.updated_at = now
            saved = repo.save_world_region(existing)
        self._reconcile_world_stream_loaded_flags(
            workspace_id=saved.workspace_id,
            recently_loaded_row=saved,
        )
        refreshed = repo.get_world_region(
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            region_key=saved.region_key,
        )
        if refreshed is not None:
            saved = refreshed
        return WorldRegionOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            realm_id=saved.realm_id,
            region_key=saved.region_key,
            payload=self._json_to_object_map(saved.payload_json),
            payload_hash=saved.payload_hash,
            cache_policy=saved.cache_policy,
            loaded=saved.loaded,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    def unload_world_region(self, payload: WorldRegionUnloadInput) -> WorldRegionUnloadOut:
        region_key = payload.region_key.strip()
        if not region_key:
            raise ValueError("region_key_required")
        repo = self._require_repo()
        row = repo.get_world_region(
            workspace_id=payload.workspace_id,
            realm_id=payload.realm_id.strip().lower(),
            region_key=region_key,
        )
        if row is None:
            return WorldRegionUnloadOut(
                workspace_id=payload.workspace_id,
                realm_id=payload.realm_id.strip().lower(),
                region_key=region_key,
                unloaded=False,
            )
        row.loaded = False
        row.updated_at = datetime.utcnow()
        repo.save_world_region(row)
        return WorldRegionUnloadOut(
            workspace_id=row.workspace_id,
            realm_id=row.realm_id,
            region_key=row.region_key,
            unloaded=True,
        )

    def list_character_dictionary_entries(self, workspace_id: str) -> Sequence[CharacterDictionaryOut]:
        rows = self._require_repo().list_character_dictionary_entries(workspace_id=workspace_id)
        return [
            CharacterDictionaryOut(
                id=row.id,
                workspace_id=row.workspace_id,
                character_id=row.character_id,
                name=row.name,
                aliases=self._csv_to_list(row.aliases_csv),
                bio=row.bio,
                tags=self._csv_to_list(row.tags_csv),
                faction=row.faction,
                metadata=self._json_to_object_map(row.metadata_json),
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_character_dictionary_entry(self, payload: CharacterDictionaryCreate) -> CharacterDictionaryOut:
        row = CharacterDictionaryEntry(
            workspace_id=payload.workspace_id,
            character_id=payload.character_id,
            name=payload.name,
            aliases_csv=self._list_to_csv(payload.aliases),
            bio=payload.bio,
            tags_csv=self._list_to_csv(payload.tags),
            faction=payload.faction,
            metadata_json=self._canonical_json(payload.metadata),
        )
        out = self._require_repo().create_character_dictionary_entry(row)
        return CharacterDictionaryOut(
            id=out.id,
            workspace_id=out.workspace_id,
            character_id=out.character_id,
            name=out.name,
            aliases=self._csv_to_list(out.aliases_csv),
            bio=out.bio,
            tags=self._csv_to_list(out.tags_csv),
            faction=out.faction,
            metadata=self._json_to_object_map(out.metadata_json),
            created_at=out.created_at,
        )

    def list_named_quests(self, workspace_id: str) -> Sequence[NamedQuestOut]:
        rows = self._require_repo().list_named_quests(workspace_id=workspace_id)
        return [
            NamedQuestOut(
                id=row.id,
                workspace_id=row.workspace_id,
                quest_id=row.quest_id,
                name=row.name,
                status=row.status,
                current_step=row.current_step,
                requirements=self._json_to_object_map(row.requirements_json),
                rewards=self._json_to_object_map(row.rewards_json),
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_named_quest(self, payload: NamedQuestCreate) -> NamedQuestOut:
        row = NamedQuest(
            workspace_id=payload.workspace_id,
            quest_id=payload.quest_id,
            name=payload.name,
            status=payload.status,
            current_step=payload.current_step,
            requirements_json=self._canonical_json(payload.requirements),
            rewards_json=self._canonical_json(payload.rewards),
        )
        out = self._require_repo().create_named_quest(row)
        return NamedQuestOut(
            id=out.id,
            workspace_id=out.workspace_id,
            quest_id=out.quest_id,
            name=out.name,
            status=out.status,
            current_step=out.current_step,
            requirements=self._json_to_object_map(out.requirements_json),
            rewards=self._json_to_object_map(out.rewards_json),
            created_at=out.created_at,
        )

    def list_journal_entries(self, workspace_id: str, actor_id: str | None = None) -> Sequence[JournalEntryOut]:
        rows = self._require_repo().list_journal_entries(workspace_id=workspace_id, actor_id=actor_id)
        return [
            JournalEntryOut(
                id=row.id,
                workspace_id=row.workspace_id,
                actor_id=row.actor_id,
                entry_id=row.entry_id,
                title=row.title,
                body=row.body,
                kind=row.kind,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_journal_entry(self, payload: JournalEntryCreate) -> JournalEntryOut:
        row = JournalEntry(
            workspace_id=payload.workspace_id,
            actor_id=payload.actor_id,
            entry_id=payload.entry_id,
            title=payload.title,
            body=payload.body,
            kind=payload.kind,
        )
        out = self._require_repo().create_journal_entry(row)
        return JournalEntryOut(
            id=out.id,
            workspace_id=out.workspace_id,
            actor_id=out.actor_id,
            entry_id=out.entry_id,
            title=out.title,
            body=out.body,
            kind=out.kind,
            created_at=out.created_at,
        )

    def _to_layer_node_out(self, row: LayerNode) -> LayerNodeOut:
        return LayerNodeOut(
            id=row.id,
            workspace_id=row.workspace_id,
            layer_index=row.layer_index,
            node_key=row.node_key,
            payload=self._json_to_object_map(row.payload_json),
            payload_hash=row.payload_hash,
            created_at=row.created_at,
        )

    def _to_layer_edge_out(self, row: LayerEdge) -> LayerEdgeOut:
        return LayerEdgeOut(
            id=row.id,
            workspace_id=row.workspace_id,
            from_node_id=row.from_node_id,
            to_node_id=row.to_node_id,
            edge_kind=row.edge_kind,
            metadata=self._json_to_object_map(row.metadata_json),
            created_at=row.created_at,
        )

    def _to_layer_event_out(self, row: LayerEvent) -> LayerEventOut:
        return LayerEventOut(
            id=row.id,
            workspace_id=row.workspace_id,
            event_kind=row.event_kind,
            actor_id=row.actor_id,
            node_id=row.node_id,
            edge_id=row.edge_id,
            payload_hash=row.payload_hash,
            created_at=row.created_at,
        )

    def list_layer_nodes(self, workspace_id: str, layer_index: int | None = None) -> Sequence[LayerNodeOut]:
        rows = self._require_repo().list_layer_nodes(workspace_id=workspace_id, layer_index=layer_index)
        return [self._to_layer_node_out(row) for row in rows]

    def create_layer_node(
        self,
        *,
        payload: LayerNodeCreate,
        actor_id: str,
    ) -> LayerNodeOut:
        repo = self._require_repo()
        node_payload_hash = self._canonical_hash(
            {
                "workspace_id": payload.workspace_id,
                "layer_index": payload.layer_index,
                "node_key": payload.node_key,
                "payload": payload.payload,
            }
        )
        row = LayerNode(
            workspace_id=payload.workspace_id,
            layer_index=payload.layer_index,
            node_key=payload.node_key,
            payload_json=self._canonical_json(payload.payload),
            payload_hash=node_payload_hash,
        )
        saved = repo.create_layer_node(row)
        repo.create_layer_event(
            LayerEvent(
                workspace_id=payload.workspace_id,
                event_kind="layer_node_created",
                actor_id=actor_id,
                node_id=saved.id,
                edge_id=None,
                payload_hash=node_payload_hash,
            )
        )
        return self._to_layer_node_out(saved)

    def list_layer_edges(self, workspace_id: str, node_id: str | None = None) -> Sequence[LayerEdgeOut]:
        rows = self._require_repo().list_layer_edges(workspace_id=workspace_id, node_id=node_id)
        return [self._to_layer_edge_out(row) for row in rows]

    def create_layer_edge(
        self,
        *,
        payload: LayerEdgeCreate,
        actor_id: str,
    ) -> LayerEdgeOut:
        repo = self._require_repo()
        from_node = repo.get_layer_node(payload.workspace_id, payload.from_node_id)
        to_node = repo.get_layer_node(payload.workspace_id, payload.to_node_id)
        if from_node is None or to_node is None:
            raise ValueError("layer_node_not_found")
        edge_payload_hash = self._canonical_hash(
            {
                "workspace_id": payload.workspace_id,
                "from_node_id": payload.from_node_id,
                "to_node_id": payload.to_node_id,
                "edge_kind": payload.edge_kind,
                "metadata": payload.metadata,
            }
        )
        row = LayerEdge(
            workspace_id=payload.workspace_id,
            from_node_id=payload.from_node_id,
            to_node_id=payload.to_node_id,
            edge_kind=payload.edge_kind,
            metadata_json=self._canonical_json(payload.metadata),
        )
        saved = repo.create_layer_edge(row)
        repo.create_layer_event(
            LayerEvent(
                workspace_id=payload.workspace_id,
                event_kind="layer_edge_created",
                actor_id=actor_id,
                node_id=None,
                edge_id=saved.id,
                payload_hash=edge_payload_hash,
            )
        )
        return self._to_layer_edge_out(saved)

    def list_layer_events(self, workspace_id: str) -> Sequence[LayerEventOut]:
        rows = self._require_repo().list_layer_events(workspace_id=workspace_id)
        return [self._to_layer_event_out(row) for row in rows]

    def trace_layer_node(self, workspace_id: str, node_id: str) -> LayerTraceOut:
        repo = self._require_repo()
        node = repo.get_layer_node(workspace_id=workspace_id, node_id=node_id)
        if node is None:
            raise ValueError("layer_node_not_found")
        all_edges = repo.list_layer_edges(workspace_id=workspace_id, node_id=node_id)
        inbound: list[LayerEdgeOut] = []
        outbound: list[LayerEdgeOut] = []
        for edge in all_edges:
            edge_out = self._to_layer_edge_out(edge)
            if edge.to_node_id == node_id:
                inbound.append(edge_out)
            if edge.from_node_id == node_id:
                outbound.append(edge_out)
        return LayerTraceOut(
            node=self._to_layer_node_out(node),
            inbound=sorted(inbound, key=lambda item: item.id),
            outbound=sorted(outbound, key=lambda item: item.id),
        )

    def list_function_store_entries(self, workspace_id: str) -> Sequence[FunctionStoreOut]:
        rows = self._require_repo().list_function_store_entries(workspace_id=workspace_id)
        return [
            FunctionStoreOut(
                id=row.id,
                workspace_id=row.workspace_id,
                function_id=row.function_id,
                version=row.version,
                signature=row.signature,
                body=row.body,
                metadata=self._json_to_object_map(row.metadata_json),
                function_hash=row.function_hash,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def create_function_store_entry(
        self,
        *,
        payload: FunctionStoreCreate,
        actor_id: str,
    ) -> FunctionStoreOut:
        repo = self._require_repo()
        function_hash = self._canonical_hash(
            {
                "workspace_id": payload.workspace_id,
                "function_id": payload.function_id,
                "version": payload.version,
                "signature": payload.signature,
                "body": payload.body,
                "metadata": payload.metadata,
            }
        )
        row = FunctionStoreEntry(
            workspace_id=payload.workspace_id,
            function_id=payload.function_id,
            version=payload.version,
            signature=payload.signature,
            body=payload.body,
            metadata_json=self._canonical_json(payload.metadata),
            function_hash=function_hash,
        )
        saved = repo.create_function_store_entry(row)
        repo.create_layer_event(
            LayerEvent(
                workspace_id=payload.workspace_id,
                event_kind="function_store_entry_created",
                actor_id=actor_id,
                node_id=None,
                edge_id=None,
                payload_hash=function_hash,
            )
        )
        return FunctionStoreOut(
            id=saved.id,
            workspace_id=saved.workspace_id,
            function_id=saved.function_id,
            version=saved.version,
            signature=saved.signature,
            body=saved.body,
            metadata=self._json_to_object_map(saved.metadata_json),
            function_hash=saved.function_hash,
            created_at=saved.created_at,
        )

    @staticmethod
    def _derive_artisan_code(
        *,
        artisan_id: str,
        profile_name: str,
        profile_email: str,
        role: str,
        workshop_id: str,
    ) -> str:
        seed = f"{artisan_id}|{profile_name}|{profile_email}|{role}|{workshop_id}".encode("utf-8")
        digest = hashlib.sha256(seed).hexdigest().upper()[:12]
        return f"AID-{digest}"

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @staticmethod
    def _to_access_status(row: ArtisanAccount) -> ArtisanAccessStatusOut:
        return ArtisanAccessStatusOut(
            artisan_id=row.artisan_id,
            role=row.role,
            workshop_id=row.workshop_id,
            profile_name=row.profile_name,
            profile_email=row.profile_email,
            profile_timezone="UTC",
            artisan_access_verified=row.artisan_access_verified,
        )

    def issue_artisan_access_code(
        self,
        *,
        artisan_id: str,
        role: str,
        workshop_id: str,
        payload: ArtisanAccessIssueInput,
    ) -> ArtisanAccessIssueOut:
        repo = self._require_repo()
        row = repo.upsert_artisan_account(
            artisan_id=artisan_id,
            role=role,
            workshop_id=workshop_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
        )
        code = self._derive_artisan_code(
            artisan_id=artisan_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
            role=role,
            workshop_id=workshop_id,
        )
        row.artisan_code_hash = self._hash_code(code)
        row.artisan_access_verified = False
        saved = repo.save_artisan_account(row)
        return ArtisanAccessIssueOut(artisan_code=code, status=self._to_access_status(saved))

    def verify_artisan_access_code(
        self,
        *,
        artisan_id: str,
        role: str,
        workshop_id: str,
        payload: ArtisanAccessVerifyInput,
    ) -> ArtisanAccessStatusOut:
        repo = self._require_repo()
        row = repo.upsert_artisan_account(
            artisan_id=artisan_id,
            role=role,
            workshop_id=workshop_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
        )
        expected_code = self._derive_artisan_code(
            artisan_id=artisan_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
            role=role,
            workshop_id=workshop_id,
        )
        row.artisan_access_verified = payload.artisan_code == expected_code and row.artisan_code_hash == self._hash_code(payload.artisan_code)
        saved = repo.save_artisan_account(row)
        return self._to_access_status(saved)

    def artisan_access_status(self, *, artisan_id: str, role: str, workshop_id: str) -> ArtisanAccessStatusOut:
        repo = self._require_repo()
        existing = repo.get_artisan_account(artisan_id)
        if existing is None:
            row = repo.upsert_artisan_account(
                artisan_id=artisan_id,
                role=role,
                workshop_id=workshop_id,
                profile_name="",
                profile_email="",
            )
            return self._to_access_status(row)
        existing.role = role
        existing.workshop_id = workshop_id
        saved = repo.save_artisan_account(existing)
        return self._to_access_status(saved)

    def bootstrap_artisan_access(
        self,
        *,
        role: str,
        workshop_id: str,
        payload: ArtisanBootstrapInput,
    ) -> ArtisanAccessIssueOut:
        repo = self._require_repo()
        row = repo.upsert_artisan_account(
            artisan_id=payload.artisan_id,
            role=role,
            workshop_id=workshop_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
        )
        code = self._derive_artisan_code(
            artisan_id=payload.artisan_id,
            profile_name=payload.profile_name,
            profile_email=payload.profile_email,
            role=role,
            workshop_id=workshop_id,
        )
        row.artisan_code_hash = self._hash_code(code)
        row.artisan_access_verified = True
        saved = repo.save_artisan_account(row)
        return ArtisanAccessIssueOut(artisan_code=code, status=self._to_access_status(saved))
    @staticmethod
    def _canonical_skill_id(raw_skill_id: str) -> str:
        normalized = str(raw_skill_id or "").strip().lower()
        if normalized == "":
            return ""
        normalized = normalized.replace("-", "_").replace(" ", "_")
        alias_map = {
            "energyweapons": "energy_weapons",
            "melee": "melee_weapons",
            "meleeweapon": "melee_weapons",
            "meleeweapons": "melee_weapons",
            "lock_pick": "lockpick",
        }
        mapped = alias_map.get(normalized, normalized)
        if mapped in CANONICAL_GAME_SKILLS:
            return mapped
        return normalized

    def list_skill_catalog(self) -> SkillCatalogOut:
        return SkillCatalogOut(skills=list(CANONICAL_GAME_SKILLS))

# --- PYTHON PATH FIX ---
# Get the Python running this API server
PYTHON_EXE = sys.executable

# DjinnOS root (adjust if needed)
DJINNOS_ROOT = Path(__file__).parent.parent.parent.parent  # Goes up to repo root
SCRIPTS_DIR = DJINNOS_ROOT / "scripts"
GAMEPLAY_DIR = DJINNOS_ROOT / "gameplay"

def run_python_script(script_path: str, input_data: str = None, timeout: int = 30):
    """
    Execute a Python script using the same interpreter running this server.
    
    Args:
        script_path: Path to .py file (relative to DjinnOS root or absolute)
        input_data: String to pass as stdin
        timeout: Max execution time in seconds
        
    Returns:
        dict with {"ok": bool, "stdout": str, "stderr": str, "returncode": int}
    """
    script = Path(script_path)
    if not script.is_absolute():
        script = DJINNOS_ROOT / script
    
    if not script.exists():
        return {
            "ok": False,
            "error": f"Script not found: {script}",
            "stdout": "",
            "stderr": "",
            "returncode": -1
        }
    
    try:
        result = subprocess.run(
            [PYTHON_EXE, str(script)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(DJINNOS_ROOT)  # Run from repo root
        )
        
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": f"Script timeout after {timeout}s",
            "stdout": "",
            "stderr": "",
            "returncode": -1
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "stdout": "",
            "stderr": "",
            "returncode": -1
        }