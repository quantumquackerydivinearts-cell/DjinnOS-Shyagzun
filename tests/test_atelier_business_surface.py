from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any, Dict, Sequence

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(API_APP_DIR))

from atelier_api.main import app, _atelier_service  # type: ignore[import]


class FakeAtelierService:
    def bootstrap_artisan_access(self, *, role: str, workshop_id: str, payload: Any) -> Dict[str, Any]:
        return {
            "artisan_code": "AID-KAEL001",
            "status": {
                "artisan_id": payload.artisan_id,
                "role": role,
                "workshop_id": workshop_id,
                "profile_name": payload.profile_name,
                "profile_email": payload.profile_email,
                "artisan_access_verified": True,
            },
        }

    def issue_artisan_access_code(self, *, artisan_id: str, role: str, workshop_id: str, payload: Any) -> Dict[str, Any]:
        return {
            "artisan_code": "AID-TESTCODE",
            "status": {
                "artisan_id": artisan_id,
                "role": role,
                "workshop_id": workshop_id,
                "profile_name": payload.profile_name,
                "profile_email": payload.profile_email,
                "artisan_access_verified": False,
            },
        }

    def verify_artisan_access_code(self, *, artisan_id: str, role: str, workshop_id: str, payload: Any) -> Dict[str, Any]:
        return {
            "artisan_id": artisan_id,
            "role": role,
            "workshop_id": workshop_id,
            "profile_name": payload.profile_name,
            "profile_email": payload.profile_email,
            "artisan_access_verified": payload.artisan_code == "AID-TESTCODE",
        }

    def artisan_access_status(self, *, artisan_id: str, role: str, workshop_id: str) -> Dict[str, Any]:
        return {
            "artisan_id": artisan_id,
            "role": role,
            "workshop_id": workshop_id,
            "profile_name": "Status User",
            "profile_email": "status@example.com",
            "artisan_access_verified": True,
        }

    def list_leads(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "lead-1",
                "workspace_id": workspace_id,
                "full_name": "Lead One",
                "email": "lead@example.com",
                "details": "",
                "status": "new",
                "source": "internal",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_lead(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "lead-created",
            "workspace_id": payload.workspace_id,
            "full_name": payload.full_name,
            "email": payload.email,
            "details": payload.details,
            "status": payload.status,
            "source": payload.source,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_clients(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "client-1",
                "workspace_id": workspace_id,
                "full_name": "Client One",
                "email": "client@example.com",
                "phone": None,
                "status": "active",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_client(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "client-created",
            "workspace_id": payload.workspace_id,
            "full_name": payload.full_name,
            "email": payload.email,
            "phone": payload.phone,
            "status": payload.status,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_quotes(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "quote-1",
                "workspace_id": workspace_id,
                "lead_id": None,
                "client_id": None,
                "title": "Quote One",
                "amount_cents": 10000,
                "currency": "USD",
                "status": "draft",
                "is_public": False,
                "notes": "",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_quote(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "quote-created",
            "workspace_id": payload.workspace_id,
            "lead_id": payload.lead_id,
            "client_id": payload.client_id,
            "title": payload.title,
            "amount_cents": payload.amount_cents,
            "currency": payload.currency,
            "status": payload.status,
            "is_public": payload.is_public,
            "notes": payload.notes,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_orders(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "order-1",
                "workspace_id": workspace_id,
                "quote_id": None,
                "client_id": None,
                "title": "Order One",
                "amount_cents": 5000,
                "currency": "USD",
                "status": "open",
                "notes": "",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_order(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "order-created",
            "workspace_id": payload.workspace_id,
            "quote_id": payload.quote_id,
            "client_id": payload.client_id,
            "title": payload.title,
            "amount_cents": payload.amount_cents,
            "currency": payload.currency,
            "status": payload.status,
            "notes": payload.notes,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_suppliers(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "supplier-1",
                "workspace_id": workspace_id,
                "supplier_name": "North Forge Supply",
                "contact_name": "Rin",
                "contact_email": "rin@supply.example",
                "contact_phone": None,
                "notes": "",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_supplier(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "supplier-created",
            "workspace_id": payload.workspace_id,
            "supplier_name": payload.supplier_name,
            "contact_name": payload.contact_name,
            "contact_email": payload.contact_email,
            "contact_phone": payload.contact_phone,
            "notes": payload.notes,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_inventory_items(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "inv-1",
                "workspace_id": workspace_id,
                "sku": "INK-001",
                "name": "Aether Ink",
                "quantity_on_hand": 12,
                "reorder_level": 5,
                "unit_cost_cents": 1299,
                "currency": "USD",
                "supplier_id": "supplier-1",
                "notes": "",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_inventory_item(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "inv-created",
            "workspace_id": payload.workspace_id,
            "sku": payload.sku,
            "name": payload.name,
            "quantity_on_hand": payload.quantity_on_hand,
            "reorder_level": payload.reorder_level,
            "unit_cost_cents": payload.unit_cost_cents,
            "currency": payload.currency,
            "supplier_id": payload.supplier_id,
            "notes": payload.notes,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_public_commission_quotes(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "public-quote-1",
                "workspace_id": workspace_id,
                "title": "Public Quote",
                "amount_cents": 12000,
                "currency": "USD",
                "status": "published",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_public_inquiry(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "lead-public",
            "workspace_id": payload.workspace_id,
            "full_name": payload.full_name,
            "email": payload.email,
            "details": payload.details,
            "status": "new",
            "source": "public_commission_hall",
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_character_dictionary_entries(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "char-1",
                "workspace_id": workspace_id,
                "character_id": "npc_kael",
                "name": "Kael",
                "aliases": ["Kael the Steward"],
                "bio": "Workshop steward and quest-giver.",
                "tags": ["steward", "mentor"],
                "faction": "guild_hall",
                "metadata": {"rank": "senior"},
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_character_dictionary_entry(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "char-created",
            "workspace_id": payload.workspace_id,
            "character_id": payload.character_id,
            "name": payload.name,
            "aliases": payload.aliases,
            "bio": payload.bio,
            "tags": payload.tags,
            "faction": payload.faction,
            "metadata": payload.metadata,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_named_quests(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "quest-1",
                "workspace_id": workspace_id,
                "quest_id": "q_intro",
                "name": "Atelier Initiation",
                "status": "active",
                "current_step": "meet_steward",
                "requirements": {"skills": {"speech": 1}},
                "rewards": {"xp": 100},
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_named_quest(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "quest-created",
            "workspace_id": payload.workspace_id,
            "quest_id": payload.quest_id,
            "name": payload.name,
            "status": payload.status,
            "current_step": payload.current_step,
            "requirements": payload.requirements,
            "rewards": payload.rewards,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_journal_entries(self, workspace_id: str, actor_id: str | None = None) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "journal-1",
                "workspace_id": workspace_id,
                "actor_id": actor_id or "player",
                "entry_id": "entry_intro",
                "title": "First Entry",
                "body": "Met Kael in the foyer.",
                "kind": "quest",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_journal_entry(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "journal-created",
            "workspace_id": payload.workspace_id,
            "actor_id": payload.actor_id,
            "entry_id": payload.entry_id,
            "title": payload.title,
            "body": payload.body,
            "kind": payload.kind,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_layer_nodes(self, workspace_id: str, layer_index: int | None = None) -> Sequence[Dict[str, Any]]:
        _ = layer_index
        return [
            {
                "id": "node-1",
                "workspace_id": workspace_id,
                "layer_index": 5,
                "node_key": "entity.player",
                "payload": {"hp": 100},
                "payload_hash": "h-node-1",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_layer_node(self, *, payload: Any, actor_id: str) -> Dict[str, Any]:
        _ = actor_id
        return {
            "id": "node-created",
            "workspace_id": payload.workspace_id,
            "layer_index": payload.layer_index,
            "node_key": payload.node_key,
            "payload": payload.payload,
            "payload_hash": "h-node-created",
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_layer_edges(self, workspace_id: str, node_id: str | None = None) -> Sequence[Dict[str, Any]]:
        _ = node_id
        return [
            {
                "id": "edge-1",
                "workspace_id": workspace_id,
                "from_node_id": "node-1",
                "to_node_id": "node-2",
                "edge_kind": "derives_from",
                "metadata": {"weight": 1},
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_layer_edge(self, *, payload: Any, actor_id: str) -> Dict[str, Any]:
        _ = actor_id
        return {
            "id": "edge-created",
            "workspace_id": payload.workspace_id,
            "from_node_id": payload.from_node_id,
            "to_node_id": payload.to_node_id,
            "edge_kind": payload.edge_kind,
            "metadata": payload.metadata,
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_layer_events(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "event-1",
                "workspace_id": workspace_id,
                "event_kind": "layer_node_created",
                "actor_id": "tester",
                "node_id": "node-1",
                "edge_id": None,
                "payload_hash": "h-node-1",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def trace_layer_node(self, workspace_id: str, node_id: str) -> Dict[str, Any]:
        return {
            "node": {
                "id": node_id,
                "workspace_id": workspace_id,
                "layer_index": 5,
                "node_key": "entity.player",
                "payload": {"hp": 100},
                "payload_hash": "h-node-1",
                "created_at": "2026-02-25T00:00:00Z",
            },
            "inbound": [],
            "outbound": [
                {
                    "id": "edge-1",
                    "workspace_id": workspace_id,
                    "from_node_id": node_id,
                    "to_node_id": "node-2",
                    "edge_kind": "derives_from",
                    "metadata": {},
                    "created_at": "2026-02-25T00:00:00Z",
                }
            ],
        }

    def list_function_store_entries(self, workspace_id: str) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "fn-1",
                "workspace_id": workspace_id,
                "function_id": "combat.resolve",
                "version": "1.0.0",
                "signature": "(attacker,defender)->result",
                "body": "return {}",
                "metadata": {"layer": 12},
                "function_hash": "h-fn-1",
                "created_at": "2026-02-25T00:00:00Z",
            }
        ]

    def create_function_store_entry(self, *, payload: Any, actor_id: str) -> Dict[str, Any]:
        _ = actor_id
        return {
            "id": "fn-created",
            "workspace_id": payload.workspace_id,
            "function_id": payload.function_id,
            "version": payload.version,
            "signature": payload.signature,
            "body": payload.body,
            "metadata": payload.metadata,
            "function_hash": "h-fn-created",
            "created_at": "2026-02-25T00:00:00Z",
        }

    def list_scenes(self, workspace_id: str, realm_id: str | None = None) -> Sequence[Dict[str, Any]]:
        _ = realm_id
        return [
            {
                "id": "scene-1",
                "workspace_id": workspace_id,
                "realm_id": "lapidus",
                "scene_id": "lapidus/intro",
                "name": "Intro",
                "description": "First scene",
                "content": {"nodes": [], "edges": []},
                "content_hash": "h-scene-1",
                "created_at": "2026-02-25T00:00:00Z",
                "updated_at": "2026-02-25T00:00:00Z",
            }
        ]

    def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> Dict[str, Any] | None:
        if realm_id != "lapidus" or scene_id != "lapidus/intro":
            return None
        return {
            "id": "scene-1",
            "workspace_id": workspace_id,
            "realm_id": realm_id,
            "scene_id": scene_id,
            "name": "Intro",
            "description": "First scene",
            "content": {"nodes": [], "edges": []},
            "content_hash": "h-scene-1",
            "created_at": "2026-02-25T00:00:00Z",
            "updated_at": "2026-02-25T00:00:00Z",
        }

    def create_scene(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "scene-created",
            "workspace_id": payload.workspace_id,
            "realm_id": payload.realm_id,
            "scene_id": payload.scene_id,
            "name": payload.name,
            "description": payload.description,
            "content": payload.content,
            "content_hash": "h-scene-created",
            "created_at": "2026-02-25T00:00:00Z",
            "updated_at": "2026-02-25T00:00:00Z",
        }

    def update_scene(self, workspace_id: str, realm_id: str, scene_id: str, payload: Any) -> Dict[str, Any]:
        return {
            "id": "scene-updated",
            "workspace_id": workspace_id,
            "realm_id": realm_id,
            "scene_id": scene_id,
            "name": payload.name or "Intro",
            "description": payload.description or "First scene",
            "content": payload.content or {"nodes": [], "edges": []},
            "content_hash": "h-scene-updated",
            "created_at": "2026-02-25T00:00:00Z",
            "updated_at": "2026-02-25T00:00:00Z",
        }

    def emit_scene_from_library(
        self,
        *,
        workspace_id: str,
        realm_id: str,
        scene_id: str,
        actor_id: str,
        workshop_id: str,
    ) -> Dict[str, Any]:
        _ = (actor_id, workshop_id)
        return {"scene_id": scene_id, "nodes_emitted": 1, "edges_emitted": 0}

    def create_scene_from_cobra(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "scene-compiled",
            "workspace_id": payload.workspace_id,
            "realm_id": payload.realm_id,
            "scene_id": payload.scene_id,
            "name": payload.name,
            "description": payload.description,
            "content": {"nodes": [{"node_id": "n1", "kind": "spawn", "x": 0, "y": 0, "metadata": {}}], "edges": []},
            "content_hash": "h-scene-compiled",
            "created_at": "2026-02-25T00:00:00Z",
            "updated_at": "2026-02-25T00:00:00Z",
        }

    def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[Dict[str, Any]]:
        return [
            {
                "id": "region-1",
                "workspace_id": workspace_id,
                "realm_id": realm_id or "lapidus",
                "region_key": "lapidus/sector-001",
                "payload": {"tiles": [1, 2, 3]},
                "payload_hash": "h-region-1",
                "cache_policy": "cache",
                "loaded": True,
                "created_at": "2026-02-25T00:00:00Z",
                "updated_at": "2026-02-25T00:00:00Z",
            }
        ]

    def load_world_region(self, payload: Any) -> Dict[str, Any]:
        return {
            "id": "region-loaded",
            "workspace_id": payload.workspace_id,
            "realm_id": payload.realm_id,
            "region_key": payload.region_key,
            "payload": payload.payload,
            "payload_hash": "h-region-loaded",
            "cache_policy": payload.cache_policy,
            "loaded": True,
            "created_at": "2026-02-25T00:00:00Z",
            "updated_at": "2026-02-25T00:00:00Z",
        }

    def unload_world_region(self, payload: Any) -> Dict[str, Any]:
        return {
            "workspace_id": payload.workspace_id,
            "realm_id": payload.realm_id,
            "region_key": payload.region_key,
            "unloaded": True,
        }


def _admin_gate_token(actor_id: str, workshop_id: str, gate_code: str = "STEWARD_DEV_GATE") -> str:
    payload = f"{gate_code}:{actor_id}:{workshop_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _headers(caps: str, role: str = "steward", token: str | None = None) -> Dict[str, str]:
    return {
        "X-Atelier-Actor": "tester",
        "X-Atelier-Capabilities": caps,
        "X-Artisan-Id": "artisan-1",
        "X-Artisan-Role": role,
        "X-Workshop-Id": "workshop-1",
        "X-Workshop-Scopes": "scene:*,workspace:*",
        **({ "X-Admin-Gate-Token": token } if token else {}),
    }


def test_lead_client_quote_order_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    leads = client.get("/v1/leads?workspace_id=main", headers=_headers("lead.read"))
    assert leads.status_code == 200
    assert leads.json()[0]["id"] == "lead-1"

    lead_create = client.post(
        "/v1/leads",
        headers=_headers("lead.write"),
        json={"workspace_id": "main", "full_name": "New Lead", "email": None, "details": "", "status": "new", "source": "internal"},
    )
    assert lead_create.status_code == 200
    assert lead_create.json()["id"] == "lead-created"

    clients = client.get("/v1/clients?workspace_id=main", headers=_headers("client.read"))
    assert clients.status_code == 200
    assert clients.json()[0]["id"] == "client-1"

    client_create = client.post(
        "/v1/clients",
        headers=_headers("client.write"),
        json={"workspace_id": "main", "full_name": "New Client", "email": None, "phone": None, "status": "active"},
    )
    assert client_create.status_code == 200
    assert client_create.json()["id"] == "client-created"

    quotes = client.get("/v1/quotes?workspace_id=main", headers=_headers("quote.read"))
    assert quotes.status_code == 200
    assert quotes.json()[0]["id"] == "quote-1"

    quote_create = client.post(
        "/v1/quotes",
        headers=_headers("quote.write"),
        json={
            "workspace_id": "main",
            "lead_id": None,
            "client_id": None,
            "title": "New Quote",
            "amount_cents": 1000,
            "currency": "USD",
            "status": "draft",
            "is_public": False,
            "notes": "",
        },
    )
    assert quote_create.status_code == 200
    assert quote_create.json()["id"] == "quote-created"

    orders = client.get("/v1/orders?workspace_id=main", headers=_headers("order.read"))
    assert orders.status_code == 200
    assert orders.json()[0]["id"] == "order-1"

    order_create = client.post(
        "/v1/orders",
        headers=_headers("order.write"),
        json={
            "workspace_id": "main",
            "quote_id": None,
            "client_id": None,
            "title": "New Order",
            "amount_cents": 900,
            "currency": "USD",
            "status": "open",
            "notes": "",
        },
    )
    assert order_create.status_code == 200
    assert order_create.json()["id"] == "order-created"
    app.dependency_overrides.clear()


def test_public_commission_hall_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    public_quotes = client.get("/public/commission-hall/quotes?workspace_id=main")
    assert public_quotes.status_code == 200
    assert public_quotes.json()[0]["id"] == "public-quote-1"

    inquiry = client.post(
        "/public/commission-hall/inquiries",
        json={"workspace_id": "main", "full_name": "Visitor", "email": "v@example.com", "details": "Commission request"},
    )
    assert inquiry.status_code == 200
    assert inquiry.json()["id"] == "lead-public"
    app.dependency_overrides.clear()


def test_public_privacy_manifest_route() -> None:
    client = TestClient(app)
    res = client.get("/public/privacy/manifest")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == "1.0.0"
    assert payload["application"]["name"] == "Quantum Quackery Virtual Atelier"


def test_inventory_and_supplier_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    suppliers = client.get("/v1/suppliers?workspace_id=main", headers=_headers("supplier.read"))
    assert suppliers.status_code == 200
    assert suppliers.json()[0]["id"] == "supplier-1"

    supplier_create = client.post(
        "/v1/suppliers",
        headers=_headers("supplier.write"),
        json={
            "workspace_id": "main",
            "supplier_name": "Forge Traders",
            "contact_name": "Ari",
            "contact_email": "ari@example.com",
            "contact_phone": None,
            "notes": "",
        },
    )
    assert supplier_create.status_code == 200
    assert supplier_create.json()["id"] == "supplier-created"

    inventory = client.get("/v1/inventory?workspace_id=main", headers=_headers("inventory.read"))
    assert inventory.status_code == 200
    assert inventory.json()[0]["id"] == "inv-1"

    inventory_create = client.post(
        "/v1/inventory",
        headers=_headers("inventory.write"),
        json={
            "workspace_id": "main",
            "sku": "INK-777",
            "name": "Void Ink",
            "quantity_on_hand": 7,
            "reorder_level": 3,
            "unit_cost_cents": 1999,
            "currency": "USD",
            "supplier_id": None,
            "notes": "",
        },
    )
    assert inventory_create.status_code == 200
    assert inventory_create.json()["id"] == "inv-created"
    app.dependency_overrides.clear()


def test_artisan_access_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    issue = client.post(
        "/v1/access/artisan-id/issue",
        headers=_headers("kernel.observe"),
        json={"profile_name": "Tester", "profile_email": "t@example.com"},
    )
    assert issue.status_code == 200
    issue_payload = issue.json()
    assert issue_payload["artisan_code"] == "AID-TESTCODE"
    assert issue_payload["status"]["artisan_access_verified"] is False

    verify = client.post(
        "/v1/access/artisan-id/verify",
        headers=_headers("kernel.observe"),
        json={"profile_name": "Tester", "profile_email": "t@example.com", "artisan_code": "AID-TESTCODE"},
    )
    assert verify.status_code == 200
    assert verify.json()["artisan_access_verified"] is True

    status = client.get("/v1/access/artisan-id/status", headers=_headers("kernel.observe"))
    assert status.status_code == 200
    assert status.json()["artisan_access_verified"] is True
    app.dependency_overrides.clear()


def test_admin_bootstrap_artisan_account() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    forbidden = client.post(
        "/v1/admin/artisans/bootstrap",
        headers=_headers("kernel.place", role="artisan"),
        json={
            "gate_code": "STEWARD_DEV_GATE",
            "artisan_id": "kael-001",
            "profile_name": "Kael",
            "profile_email": "kael@example.com",
        },
    )
    assert forbidden.status_code == 403

    ok = client.post(
        "/v1/admin/artisans/bootstrap",
        headers=_headers("kernel.place", role="steward"),
        json={
            "gate_code": "STEWARD_DEV_GATE",
            "artisan_id": "kael-001",
            "profile_name": "Kael",
            "profile_email": "kael@example.com",
        },
    )
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["status"]["artisan_id"] == "kael-001"
    assert payload["status"]["role"] == "steward"
    assert payload["status"]["artisan_access_verified"] is True
    app.dependency_overrides.clear()


def test_character_quest_journal_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    characters = client.get("/v1/game/characters?workspace_id=main", headers=_headers("character.read"))
    assert characters.status_code == 200
    assert characters.json()[0]["id"] == "char-1"

    character_create = client.post(
        "/v1/game/characters",
        headers=_headers("character.write"),
        json={
            "workspace_id": "main",
            "character_id": "npc_rin",
            "name": "Rin",
            "aliases": ["Quartermaster"],
            "bio": "Keeps inventory in order.",
            "tags": ["supplier", "inventory"],
            "faction": "workshop",
            "metadata": {"shift": "night"},
        },
    )
    assert character_create.status_code == 200
    assert character_create.json()["id"] == "char-created"

    quests = client.get("/v1/game/quests?workspace_id=main", headers=_headers("quest.read"))
    assert quests.status_code == 200
    assert quests.json()[0]["id"] == "quest-1"

    quest_create = client.post(
        "/v1/game/quests",
        headers=_headers("quest.write"),
        json={
            "workspace_id": "main",
            "quest_id": "q_supply_run",
            "name": "Supply Run",
            "status": "active",
            "current_step": "collect_ink",
            "requirements": {"inventory": {"INK-001": 1}},
            "rewards": {"xp": 50, "gold": 20},
        },
    )
    assert quest_create.status_code == 200
    assert quest_create.json()["id"] == "quest-created"

    journal = client.get(
        "/v1/game/journal?workspace_id=main&actor_id=player",
        headers=_headers("journal.read"),
    )
    assert journal.status_code == 200
    assert journal.json()[0]["id"] == "journal-1"

    journal_create = client.post(
        "/v1/game/journal",
        headers=_headers("journal.write"),
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "entry_id": "entry_supply_run_start",
            "title": "Supply Run Started",
            "body": "Need to gather ink and parchment.",
            "kind": "quest",
        },
    )
    assert journal_create.status_code == 200
    assert journal_create.json()["id"] == "journal-created"
    app.dependency_overrides.clear()


def test_layered_lineage_and_function_store_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    nodes = client.get("/v1/game/layers/nodes?workspace_id=main", headers=_headers("layer.read"))
    assert nodes.status_code == 200
    assert nodes.json()[0]["id"] == "node-1"

    node_create = client.post(
        "/v1/game/layers/nodes",
        headers=_headers("layer.write"),
        json={
            "workspace_id": "main",
            "layer_index": 5,
            "node_key": "entity.enemy.wolf",
            "payload": {"hp": 40},
        },
    )
    assert node_create.status_code == 200
    assert node_create.json()["id"] == "node-created"

    edges = client.get("/v1/game/layers/edges?workspace_id=main", headers=_headers("layer.read"))
    assert edges.status_code == 200
    assert edges.json()[0]["id"] == "edge-1"

    edge_create = client.post(
        "/v1/game/layers/edges",
        headers=_headers("layer.write"),
        json={
            "workspace_id": "main",
            "from_node_id": "node-1",
            "to_node_id": "node-2",
            "edge_kind": "references",
            "metadata": {"weight": 2},
        },
    )
    assert edge_create.status_code == 200
    assert edge_create.json()["id"] == "edge-created"

    events = client.get("/v1/game/layers/events?workspace_id=main", headers=_headers("layer.read"))
    assert events.status_code == 200
    assert events.json()[0]["id"] == "event-1"

    trace = client.get("/v1/game/layers/trace/node-1?workspace_id=main", headers=_headers("layer.read"))
    assert trace.status_code == 200
    assert trace.json()["node"]["id"] == "node-1"

    functions = client.get("/v1/game/functions?workspace_id=main", headers=_headers("function.read"))
    assert functions.status_code == 200
    assert functions.json()[0]["id"] == "fn-1"

    function_create = client.post(
        "/v1/game/functions",
        headers=_headers("function.write"),
        json={
            "workspace_id": "main",
            "function_id": "quest.advance",
            "version": "1.0.0",
            "signature": "(state,input)->state",
            "body": "return state",
            "metadata": {"layer": 12},
        },
    )
    assert function_create.status_code == 200
    assert function_create.json()["id"] == "fn-created"
    app.dependency_overrides.clear()


def test_scene_library_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    scenes = client.get("/v1/game/scenes?workspace_id=main", headers=_headers("scene.read"))
    assert scenes.status_code == 200
    assert scenes.json()[0]["scene_id"] == "lapidus/intro"

    scene = client.get(
        "/v1/game/scenes/lapidus/intro?workspace_id=main&realm_id=lapidus",
        headers=_headers("scene.read"),
    )
    assert scene.status_code == 200
    assert scene.json()["scene_id"] == "lapidus/intro"

    created = client.post(
        "/v1/game/scenes",
        headers=_headers("scene.write"),
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "name": "Intro",
            "description": "",
            "content": {"nodes": [], "edges": []},
        },
    )
    assert created.status_code == 200
    assert created.json()["id"] == "scene-created"

    updated = client.put(
        "/v1/game/scenes/lapidus/intro?workspace_id=main&realm_id=lapidus",
        headers=_headers("scene.write"),
        json={"name": "Intro 2"},
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == "scene-updated"

    token = _admin_gate_token("tester", "workshop-1")
    emitted = client.post(
        "/v1/game/scenes/lapidus/intro/emit?workspace_id=main&realm_id=lapidus",
        headers=_headers("kernel.place", token=token),
    )
    assert emitted.status_code == 200
    assert emitted.json()["nodes_emitted"] == 1

    compiled = client.post(
        "/v1/game/scenes/compile",
        headers=_headers("scene.write"),
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "name": "Intro",
            "description": "",
            "cobra_source": "entity demo 1 2 marker\n  lex TyKoWuVu",
        },
    )
    assert compiled.status_code == 200
    assert compiled.json()["id"] == "scene-compiled"
    app.dependency_overrides.clear()


def test_world_region_streaming_routes() -> None:
    app.dependency_overrides[_atelier_service] = lambda: FakeAtelierService()
    client = TestClient(app)

    listed = client.get(
        "/v1/game/world/regions?workspace_id=main&realm_id=lapidus",
        headers=_headers("scene.read"),
    )
    assert listed.status_code == 200
    assert listed.json()[0]["region_key"] == "lapidus/sector-001"

    loaded = client.post(
        "/v1/game/world/regions/load",
        headers=_headers("scene.write"),
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "region_key": "lapidus/sector-002",
            "payload": {"tiles": [4, 5, 6]},
            "cache_policy": "stream",
        },
    )
    assert loaded.status_code == 200
    assert loaded.json()["id"] == "region-loaded"
    assert loaded.json()["loaded"] is True

    unloaded = client.post(
        "/v1/game/world/regions/unload",
        headers=_headers("scene.write"),
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "region_key": "lapidus/sector-002",
        },
    )
    assert unloaded.status_code == 200
    assert unloaded.json()["unloaded"] is True
    app.dependency_overrides.clear()
