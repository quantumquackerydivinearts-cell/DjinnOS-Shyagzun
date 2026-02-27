from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(API_APP_DIR))

from atelier_api.main import app, _kernel_client  # type: ignore[import]
from atelier_api.types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse  # type: ignore[import]


class FakeKernelClient:
    def __init__(self) -> None:
        self.place_calls = 0
        self.attest_calls = 0

    def place(self, raw: str, *, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        self.place_calls += 1
        return {"ok": True, "raw": raw, "context": dict(context or {})}

    def observe(self) -> ObserveResponse:
        return {
            "field_id": "F0",
            "clock": {"tick": 1, "causal_epoch": "0"},
            "candidates_by_frontier": {},
            "eligible_by_frontier": {},
            "eligibility_events": [],
            "refusals": [],
        }

    def events(self) -> Sequence[KernelEventObj]:
        return [{"id": "evt_1", "kind": "placement", "at": {"tick": 1, "causal_epoch": "0"}}]

    def edges(self) -> Sequence[EdgeObj]:
        return []

    def attest(
        self,
        *,
        witness_id: str,
        attestation_kind: str,
        attestation_tag: Optional[str],
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.attest_calls += 1
        return {"id": "evt_att", "kind": "attestation"}

    def frontiers(self) -> Sequence[FrontierObj]:
        return [{"id": "F0", "event_ids": [], "status": "active", "inconsistency_proof": None}]

    def akinenwun_lookup(
        self,
        *,
        akinenwun: str,
        mode: str,
        ingest: bool,
    ) -> Mapping[str, Any]:
        return {
            "akinenwun": akinenwun,
            "mode": mode,
            "frontier_hash": "h_demo",
            "frontier": {"paths": []},
            "stored": ingest,
            "dictionary_size": 1 if ingest else 0,
        }


def _admin_gate_token(actor_id: str, workshop_id: str) -> str:
    payload = f"STEWARD_DEV_GATE:{actor_id}:{workshop_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _headers(caps: str, role: str = "artisan", token: Optional[str] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "X-Atelier-Actor": "tester",
        "X-Atelier-Capabilities": caps,
        "X-Artisan-Id": "artisan-1",
        "X-Artisan-Role": role,
        "X-Workshop-Id": "workshop-1",
        "X-Workshop-Scopes": "scene:*,workspace:*",
    }
    if token is not None:
        headers["X-Admin-Gate-Token"] = token
    return headers


def test_requires_actor_header() -> None:
    client = TestClient(app)
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {}},
        headers={
            "X-Artisan-Id": "artisan-1",
            "X-Artisan-Role": "artisan",
            "X-Workshop-Id": "workshop-1",
            "X-Workshop-Scopes": "scene:*,workspace:*",
        },
    )
    assert res.status_code == 401


def test_forbidden_without_place_capability() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    res = client.post("/v1/atelier/place", json={"raw": "x", "context": {}}, headers=_headers("kernel.observe"))
    assert res.status_code == 403
    assert fake.place_calls == 0
    app.dependency_overrides.clear()


def test_place_requires_verified_admin_gate() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {"scene_id": "s1"}},
        headers=_headers("kernel.place", role="steward"),
    )
    assert res.status_code == 403
    assert fake.place_calls == 0
    app.dependency_overrides.clear()


def test_place_succeeds_for_steward_with_gate_token() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {"scene_id": "s1"}},
        headers=_headers("kernel.place", role="steward", token=token),
    )
    assert res.status_code == 200
    assert fake.place_calls == 1
    assert fake.attest_calls == 0
    app.dependency_overrides.clear()


def test_place_denied_when_scene_not_in_scope() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    res = client.post(
        "/v1/atelier/place",
        json={"raw": "x", "context": {"scene_id": "restricted"}},
        headers={
            "X-Atelier-Actor": "tester",
            "X-Atelier-Capabilities": "kernel.place",
            "X-Artisan-Id": "artisan-1",
            "X-Artisan-Role": "steward",
            "X-Workshop-Id": "workshop-1",
            "X-Workshop-Scopes": "scene:allowed,workspace:*",
            "X-Admin-Gate-Token": token,
        },
    )
    assert res.status_code == 403
    assert fake.place_calls == 0
    app.dependency_overrides.clear()


def test_artisan_cannot_attest_by_role() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    res = client.post(
        "/v1/atelier/attest",
        json={
            "witness_id": "w1",
            "attestation_kind": "recognition",
            "attestation_tag": None,
            "payload": {},
            "target": {},
        },
        headers=_headers("kernel.attest"),
    )
    assert res.status_code == 403
    assert fake.attest_calls == 0
    app.dependency_overrides.clear()


def test_senior_artisan_can_attest() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    headers = _headers("kernel.attest")
    headers["X-Artisan-Role"] = "senior_artisan"
    res = client.post(
        "/v1/atelier/attest",
        json={
            "witness_id": "w1",
            "attestation_kind": "recognition",
            "attestation_tag": None,
            "payload": {},
            "target": {},
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert fake.attest_calls == 1
    app.dependency_overrides.clear()


def test_admin_gate_verify_requires_steward_and_valid_code() -> None:
    client = TestClient(app)
    not_steward = client.post(
        "/v1/atelier/admin/gate/verify",
        json={"gate_code": "STEWARD_DEV_GATE"},
        headers=_headers("kernel.place", role="artisan"),
    )
    assert not_steward.status_code == 403

    ok = client.post(
        "/v1/atelier/admin/gate/verify",
        json={"gate_code": "STEWARD_DEV_GATE"},
        headers=_headers("kernel.place", role="steward"),
    )
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["verified_admin"] is True
    assert payload["required_role"] == "steward"
    assert isinstance(payload["admin_gate_token"], str)


def test_ambroflow_place_succeeds_for_steward_with_gate_token() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    res = client.post(
        "/v1/ambroflow/place",
        json={
            "raw": "x",
            "scene_id": "s1",
            "tags": {"tone": "flat"},
            "metadata": {"m": 1},
            "context": {"workspace_id": "workshop-1"},
        },
        headers=_headers("kernel.place", role="steward", token=token),
    )
    assert res.status_code == 200
    payload = res.json()
    context = payload["context"]
    assert context["speaker_id"] == "player"
    assert context["scene_id"] == "s1"
    assert context["tags"] == {"tone": "flat"}
    assert fake.place_calls == 1
    app.dependency_overrides.clear()


def test_ambroflow_semantic_value_uses_observe_shape() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    res = client.get("/v1/ambroflow/semantic-value", headers=_headers("kernel.observe"))
    assert res.status_code == 200
    payload = res.json()
    assert "clock" in payload
    assert "candidates_by_frontier" in payload
    assert "eligible_by_frontier" in payload
    assert "refusals" in payload
    app.dependency_overrides.clear()


def test_ambroflow_akinenwun_lookup_uses_observe_capability() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)

    denied = client.post(
        "/v1/ambroflow/akinenwun/lookup",
        json={"akinenwun": "TyKoWuVu", "mode": "prose", "ingest": True},
        headers=_headers("kernel.timeline"),
    )
    assert denied.status_code == 403

    ok = client.post(
        "/v1/ambroflow/akinenwun/lookup",
        json={"akinenwun": "TyKoWuVu", "mode": "prose", "ingest": True},
        headers=_headers("kernel.observe"),
    )
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["frontier_hash"] == "h_demo"
    assert payload["stored"] is True
    app.dependency_overrides.clear()


def test_game_rule_levels_apply_is_deterministic() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "current_level": 1,
        "current_xp": 50,
        "gained_xp": 120,
        "xp_curve_base": 100,
        "xp_curve_scale": 25,
    }
    first = client.post("/v1/game/rules/levels/apply", json=payload, headers=headers)
    second = client.post("/v1/game/rules/levels/apply", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["leveled_up"] is True
    assert fake.place_calls == 2
    app.dependency_overrides.clear()


def test_game_rule_market_trade_rejects_when_wallet_insufficient() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "item_id": "iron_ingot",
        "side": "buy",
        "quantity": 10,
        "unit_price_cents": 1500,
        "fee_bp": 50,
        "wallet_cents": 1000,
        "inventory_qty": 0,
        "available_liquidity": 100,
    }
    res = client.post("/v1/game/rules/market/trade", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["filled_qty"] == 0
    assert data["status"] == "rejected_insufficient_funds"
    assert fake.place_calls == 1
    app.dependency_overrides.clear()


def test_game_save_export_hash_stable_for_same_kernel_state() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    headers = _headers("kernel.observe", role="artisan")
    first = client.get("/v1/game/saves/export?workspace_id=main", headers=headers)
    second = client.get("/v1/game/saves/export?workspace_id=main", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["hash"] == second_payload["hash"]
    assert first_payload["payload"] == second_payload["payload"]
    app.dependency_overrides.clear()


def test_game_rule_alchemy_craft_success_and_failure() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    success = client.post(
        "/v1/game/rules/alchemy/craft",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "recipe_id": "minor_heal",
            "ingredients": {"herb": 2, "water": 1},
            "outputs": {"potion_minor_heal": 1},
            "inventory": {"herb": 5, "water": 3},
        },
        headers=headers,
    )
    assert success.status_code == 200
    success_payload = success.json()
    assert success_payload["crafted"] is True
    assert success_payload["inventory_after"]["potion_minor_heal"] == 1

    failure = client.post(
        "/v1/game/rules/alchemy/craft",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "recipe_id": "minor_heal",
            "ingredients": {"herb": 99},
            "outputs": {"potion_minor_heal": 1},
            "inventory": {"herb": 1},
        },
        headers=headers,
    )
    assert failure.status_code == 200
    failure_payload = failure.json()
    assert failure_payload["crafted"] is False
    assert failure_payload["reason"].startswith("missing:")
    app.dependency_overrides.clear()


def test_game_rule_blacksmith_and_combat_paths() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    forge = client.post(
        "/v1/game/rules/blacksmith/forge",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "blueprint_id": "iron_sword",
            "materials": {"iron_ingot": 3, "wood": 1},
            "outputs": {"iron_sword": 1},
            "inventory": {"iron_ingot": 4, "wood": 2},
            "durability_bonus": 2,
        },
        headers=headers,
    )
    assert forge.status_code == 200
    forge_payload = forge.json()
    assert forge_payload["forged"] is True
    assert forge_payload["durability_score"] >= 1

    combat = client.post(
        "/v1/game/rules/combat/resolve",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "round_id": "r1",
            "attacker": {"id": "player", "hp": 100, "attack": 18, "defense": 6},
            "defender": {"id": "wolf", "hp": 10, "attack": 9, "defense": 4},
        },
        headers=headers,
    )
    assert combat.status_code == 200
    combat_payload = combat.json()
    assert combat_payload["damage"] == 14
    assert combat_payload["defender_hp_after"] == 0
    assert combat_payload["defender_defeated"] is True
    app.dependency_overrides.clear()


def test_game_dialogue_emit_sorted_by_line_id() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    response = client.post(
        "/v1/game/dialogue/emit",
        json={
            "workspace_id": "main",
            "scene_id": "scene_1",
            "dialogue_id": "dlg_intro",
            "turns": [
                {"line_id": "l2", "speaker_id": "npc", "raw": "second"},
                {"line_id": "l1", "speaker_id": "player", "raw": "first"},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["emitted"] == 2
    assert payload["emitted_line_ids"] == ["l1", "l2"]
    assert fake.place_calls == 2
    app.dependency_overrides.clear()
