from __future__ import annotations

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


def _headers(caps: str, role: str = "steward") -> Dict[str, str]:
    return {
        "X-Atelier-Actor": "tester",
        "X-Atelier-Capabilities": caps,
        "X-Artisan-Id": "artisan-1",
        "X-Artisan-Role": role,
        "X-Workshop-Id": "workshop-1",
        "X-Workshop-Scopes": "scene:*,workspace:*",
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
