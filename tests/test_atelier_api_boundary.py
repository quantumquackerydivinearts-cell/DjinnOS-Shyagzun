from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(API_APP_DIR))

from atelier_api.main import app, _kernel_client, _kernel_only_service  # type: ignore[import]
from atelier_api.kernel_integration import KernelIntegrationService  # type: ignore[import]
from atelier_api.services import AtelierService  # type: ignore[import]
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
        policy: Optional[Mapping[str, Any]] = None,
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
    assert data["currency_backing"] == "Silver"
    assert fake.place_calls == 1
    app.dependency_overrides.clear()


def test_game_world_coin_and_market_catalog_are_realm_aware() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    headers = _headers("kernel.observe", role="artisan")

    coins = client.get("/v1/game/world/coins", headers=headers)
    assert coins.status_code == 200
    coins_payload = coins.json()
    assert len(coins_payload) >= 3
    by_realm = {item["realm_id"]: item for item in coins_payload}
    assert by_realm["lapidus"]["backing"] == "Silver"
    assert by_realm["mercurie"]["backing"] == "Water"
    assert by_realm["sulphera"]["backing"] == "Despair"

    markets = client.get("/v1/game/world/markets", headers=headers)
    assert markets.status_code == 200
    markets_payload = markets.json()
    assert len(markets_payload) >= 3
    market_by_realm = {item["realm_id"]: item for item in markets_payload}
    assert market_by_realm["lapidus"]["stock"]["iron_ingot"] > market_by_realm["mercurie"]["stock"]["iron_ingot"]
    app.dependency_overrides.clear()


def test_game_market_quote_differs_by_realm_market_profile() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    lapidus = client.post(
        "/v1/game/rules/market/quote",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "realm_id": "lapidus",
            "item_id": "iron_ingot",
            "side": "buy",
            "quantity": 1,
            "base_price_cents": 1000,
            "scarcity_bp": 0,
            "spread_bp": 0,
        },
        headers=headers,
    )
    sulphera = client.post(
        "/v1/game/rules/market/quote",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "realm_id": "sulphera",
            "item_id": "iron_ingot",
            "side": "buy",
            "quantity": 1,
            "base_price_cents": 1000,
            "scarcity_bp": 0,
            "spread_bp": 0,
        },
        headers=headers,
    )
    assert lapidus.status_code == 200
    assert sulphera.status_code == 200
    lap = lapidus.json()
    sul = sulphera.json()
    assert lap["currency_code"] == "LAP"
    assert sul["currency_code"] == "SUL"
    assert sul["unit_price_cents"] > lap["unit_price_cents"]
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


def test_game_rule_alchemy_interface() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    res = client.post(
        "/v1/game/rules/alchemy/interface",
        json={"workspace_id": "main", "actor_id": "player", "akinenwun": "RuKiAE"},
        headers=headers,
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["actor_id"] == "player"
    assert payload["akinenwun"] == "RuKiAE"
    assert "interface" in payload
    assert "render_constraints" in payload
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


def test_game_rule_radio_evaluate() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    res = client.post(
        "/v1/game/rules/radio/evaluate",
        json={"workspace_id": "main", "actor_id": "player", "underworld_state": "active"},
        headers=headers,
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    assert payload["reason"] == "state_allows_radio"
    app.dependency_overrides.clear()


def test_game_rule_alchemy_crystal_asmodian() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    res = client.post(
        "/v1/game/rules/alchemy/crystal",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "crystal_type": "asmodian",
            "purity": 100,
            "ingredients": {"ore": 1},
            "outputs": {"asmodian_crystal": 1},
            "inventory": {"ore": 2},
        },
        headers=headers,
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["crafted"] is True
    assert payload["key_flags"]["underworld_ring"] == "Lust"
    assert payload["key_flags"]["underworld_visitors_access"] is False
    assert payload["key_flags"]["underworld_royalty_access"] is False
    app.dependency_overrides.clear()


def test_game_rule_infernal_meditation_unlock() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    res = client.post(
        "/v1/game/rules/infernal-meditation/unlock",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "mentor": "Alfir",
            "location": "Castle Azoth Library",
            "section": "restricted",
            "time_of_day": "night",
        },
        headers=headers,
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["unlocked"] is True
    assert payload["flags"]["infernal_meditation"] is True
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


def test_vitriol_apply_ruler_influence_clamps_to_one_to_ten() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "base": {
            "vitality": 10,
            "introspection": 1,
            "tactility": 5,
            "reflectivity": 5,
            "ingenuity": 5,
            "ostentation": 5,
            "levity": 5,
        },
        "modifiers": [],
        "ruler_id": "asmodeus",
        "delta": {"vitality": 3},
        "reason": "trial",
        "event_id": "evt_vitriol_1",
        "applied_tick": 10,
        "duration_turns": 0,
    }
    res = client.post("/v1/game/vitriol/apply-ruler-influence", json=payload, headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["effective"]["vitality"] == 10
    assert out["applied"] is True
    assert fake.place_calls == 1
    app.dependency_overrides.clear()


def test_vitriol_apply_ruler_rejects_axis_violation() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "base": {
            "vitality": 7,
            "introspection": 7,
            "tactility": 7,
            "reflectivity": 7,
            "ingenuity": 7,
            "ostentation": 7,
            "levity": 7,
        },
        "modifiers": [],
        "ruler_id": "asmodeus",
        "delta": {"introspection": 1},
        "reason": "bad_axis",
        "event_id": "evt_vitriol_2",
        "applied_tick": 10,
        "duration_turns": 0,
    }
    res = client.post("/v1/game/vitriol/apply-ruler-influence", json=payload, headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "ruler_axis_violation"
    assert fake.place_calls == 0
    app.dependency_overrides.clear()


def test_vitriol_compute_and_clear_expired_are_deterministic() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    observe_headers = _headers("kernel.observe", role="artisan")
    place_headers = _headers("kernel.place", role="steward", token=_admin_gate_token("tester", "workshop-1"))
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "base": {
            "vitality": 5,
            "introspection": 5,
            "tactility": 5,
            "reflectivity": 5,
            "ingenuity": 5,
            "ostentation": 5,
            "levity": 5,
        },
        "modifiers": [
            {
                "source_ruler": "asmodeus",
                "delta": {"vitality": 2},
                "reason": "buff",
                "event_id": "evt_m1",
                "applied_tick": 2,
                "duration_turns": 2,
            },
            {
                "source_ruler": "mammon",
                "delta": {"ostentation": 1},
                "reason": "boon",
                "event_id": "evt_m2",
                "applied_tick": 1,
                "duration_turns": 0,
            },
        ],
        "current_tick": 5,
    }
    compute_1 = client.post("/v1/game/vitriol/compute", json=payload, headers=observe_headers)
    compute_2 = client.post("/v1/game/vitriol/compute", json=payload, headers=observe_headers)
    assert compute_1.status_code == 200
    assert compute_2.status_code == 200
    assert compute_1.json() == compute_2.json()
    clear_res = client.post("/v1/game/vitriol/clear-expired", json=payload, headers=place_headers)
    assert clear_res.status_code == 200
    clear_out = clear_res.json()
    assert clear_out["removed_count"] == 1
    assert clear_out["effective"]["ostentation"] == 6
    assert fake.place_calls == 1
    app.dependency_overrides.clear()


def test_game_djinn_keshi_and_giann_are_deterministic() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    keshi_payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "djinn_id": "keshi",
        "realm_id": "lapidus",
        "scene_id": "lapidus/intro",
        "ring_id": "overworld",
        "target_frontiers": ["F2", "F1"],
        "tick": 33,
        "reason": "scar_test",
    }
    first = client.post("/v1/game/djinn/apply", json=keshi_payload, headers=headers)
    second = client.post("/v1/game/djinn/apply", json=keshi_payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["hash"] == second_payload["hash"]
    assert first_payload["effect"] == "collapse"
    assert first_payload["scarred_frontiers"] == ["F1", "F2"]
    assert first_payload["frontier_effects"]["F1"] == "collapsed"

    giann_payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "djinn_id": "giann",
        "realm_id": "lapidus",
        "scene_id": "lapidus/intro",
        "ring_id": "overworld",
        "target_frontiers": ["F3"],
        "tick": 34,
        "reason": "boon_test",
    }
    giann = client.post("/v1/game/djinn/apply", json=giann_payload, headers=headers)
    assert giann.status_code == 200
    giann_payload_out = giann.json()
    assert giann_payload_out["effect"] == "open"
    assert giann_payload_out["opened_frontiers"] == ["F3"]
    app.dependency_overrides.clear()


def test_game_djinn_drovitth_records_marks_only_in_sulphera_royalty() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    invalid = client.post(
        "/v1/game/djinn/apply",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "djinn_id": "drovitth",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "ring_id": "overworld",
            "observed_marks": [],
            "tick": 55,
            "reason": "record_test",
        },
        headers=headers,
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "drovitth_requires_sulphera_royalty_ring"

    valid = client.post(
        "/v1/game/djinn/apply",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "djinn_id": "drovitth",
            "realm_id": "sulphera",
            "scene_id": "sulphera/royal_orrery",
            "ring_id": "royalty",
            "observed_marks": [
                {
                    "mark_id": "m2",
                    "source_djinn_id": "giann",
                    "frontier_id": "F2",
                    "effect": "open",
                    "tick": 11,
                    "note": "boon",
                },
                {
                    "mark_id": "m1",
                    "source_djinn_id": "keshi",
                    "frontier_id": "F1",
                    "effect": "collapse",
                    "tick": 10,
                    "note": "scar",
                },
            ],
            "tick": 56,
            "reason": "record_test",
        },
        headers=headers,
    )
    assert valid.status_code == 200
    payload = valid.json()
    assert payload["effect"] == "record"
    assert payload["placements"][0] == "entity royal_orrery 0 0 instrument"
    assert [mark["mark_id"] for mark in payload["orrery_marks"]] == ["m1", "m2"]
    app.dependency_overrides.clear()


def test_game_runtime_consume_executes_feature_plan_deterministically() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "plan_alpha",
        "actions": [
            {
                "action_id": "a1",
                "kind": "levels.apply",
                "payload": {
                    "current_level": 1,
                    "current_xp": 0,
                    "gained_xp": 130,
                    "xp_curve_base": 100,
                    "xp_curve_scale": 25,
                },
            },
            {
                "action_id": "a2",
                "kind": "skills.train",
                "payload": {
                    "skill_id": "alchemy",
                    "current_rank": 1,
                    "points_available": 2,
                    "max_rank": 5,
                },
            },
            {
                "action_id": "a3",
                "kind": "market.quote",
                "payload": {
                    "item_id": "iron_ingot",
                    "side": "buy",
                    "quantity": 1,
                    "base_price_cents": 1000,
                    "scarcity_bp": 200,
                    "spread_bp": 50,
                },
            },
            {
                "action_id": "a4",
                "kind": "djinn.apply",
                "payload": {
                    "djinn_id": "giann",
                    "realm_id": "lapidus",
                    "scene_id": "lapidus/intro",
                    "ring_id": "overworld",
                    "target_frontiers": ["F9"],
                    "tick": 7,
                    "reason": "runtime_plan",
                },
            },
        ],
    }
    first = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    second = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["hash"] == second_payload["hash"]
    assert first_payload["applied_count"] == 4
    assert first_payload["failed_count"] == 0
    assert [item["action_id"] for item in first_payload["results"]] == ["a1", "a2", "a3", "a4"]
    assert all(item["ok"] is True for item in first_payload["results"])
    app.dependency_overrides.clear()


def test_game_runtime_consume_reports_per_action_failure() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "plan_fail",
        "actions": [
            {"action_id": "ok1", "kind": "vitriol.compute", "payload": {"base": {"vitality": 7}, "modifiers": [], "current_tick": 1}},
            {"action_id": "bad1", "kind": "djinn.apply", "payload": {"djinn_id": "drovitth", "realm_id": "lapidus", "scene_id": "lapidus/intro"}},
        ],
    }
    res = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["applied_count"] == 1
    assert out["failed_count"] == 1
    failed = [item for item in out["results"] if not item["ok"]]
    assert len(failed) == 1
    assert "drovitth_requires_sulphera_royalty_ring" in failed[0]["error"]
    app.dependency_overrides.clear()


def test_game_runtime_consume_supports_world_stream_and_realm_economy_actions() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "world_runtime_plan",
        "actions": [
            {
                "action_id": "rload",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "lapidus",
                    "region_key": "lapidus/sector-100",
                    "payload": {"tiles": [1, 2, 3]},
                    "cache_policy": "cache",
                },
            },
            {"action_id": "coins", "kind": "world.coins.list", "payload": {}},
            {"action_id": "markets", "kind": "world.markets.list", "payload": {}},
            {"action_id": "status", "kind": "world.stream.status", "payload": {"realm_id": "lapidus"}},
            {
                "action_id": "runload",
                "kind": "world.region.unload",
                "payload": {"realm_id": "lapidus", "region_key": "lapidus/sector-100"},
            },
        ],
    }
    res = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["failed_count"] == 0
    results = {item["action_id"]: item for item in out["results"]}
    assert results["rload"]["ok"] is True
    assert results["rload"]["result"]["loaded"] is True
    assert results["coins"]["ok"] is True
    assert isinstance(results["coins"]["result"]["items"], list)
    assert any(item["realm_id"] == "sulphera" for item in results["coins"]["result"]["items"])
    assert results["markets"]["ok"] is True
    assert isinstance(results["markets"]["result"]["items"], list)
    assert any(item["realm_id"] == "mercurie" for item in results["markets"]["result"]["items"])
    assert results["status"]["ok"] is True
    assert results["status"]["result"]["realm_id"] == "lapidus"
    assert results["runload"]["ok"] is True
    assert results["runload"]["result"]["unloaded"] is True
    app.dependency_overrides.clear()


def test_game_gate_evaluate_supports_xor_and_nor_with_multi_source_state() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    base_state = {
        "skills": {"alchemy": 3},
        "inventory": {"key_sulphera_ring1": 1},
        "vitriol": {"vitality": 7, "ingenuity": 4},
        "dialogue_flags": ["met_guard"],
        "previous_dialogue": ["dlg_intro_001"],
        "flags": {"boss_seen": False},
    }

    xor_res = client.post(
        "/v1/game/rules/gates/evaluate",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "gate_id": "gate_xor_demo",
            "operator": "xor",
            "state": base_state,
            "requirements": [
                {"source": "skills", "key": "alchemy", "comparator": "gte", "int_value": 5},
                {"source": "previous_dialogue", "key": "dlg_intro_001", "comparator": "present", "bool_value": True},
                {"source": "flags", "key": "boss_seen", "comparator": "eq", "bool_value": False},
            ],
        },
        headers=headers,
    )
    assert xor_res.status_code == 200
    xor_payload = xor_res.json()
    assert xor_payload["operator"] == "xor"
    assert xor_payload["allowed"] is False
    assert xor_payload["matched_count"] == 2

    nor_res = client.post(
        "/v1/game/rules/gates/evaluate",
        json={
            "workspace_id": "main",
            "actor_id": "player",
            "gate_id": "gate_nor_demo",
            "operator": "nor",
            "state": base_state,
            "requirements": [
                {"source": "dialogue_flags", "key": "missing_flag", "comparator": "present", "bool_value": True},
                {"source": "inventory", "key": "key_sulphera_ring9", "comparator": "gte", "int_value": 1},
            ],
        },
        headers=headers,
    )
    assert nor_res.status_code == 200
    nor_payload = nor_res.json()
    assert nor_payload["operator"] == "nor"
    assert nor_payload["allowed"] is True
    assert nor_payload["matched_count"] == 0
    assert fake.place_calls == 2
    app.dependency_overrides.clear()


def test_game_gate_evaluate_deterministic_for_same_payload() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "gate_id": "gate_skill_dialogue_join",
        "operator": "and",
        "state": {
            "skills": {"speech": 2},
            "inventory": {"royal_seal": 1},
            "vitriol": {"introspection": 6},
            "dialogue_flags": ["oath_taken"],
            "previous_dialogue": ["dlg_oath_accepted"],
            "flags": {"steward_marked": True},
        },
        "requirements": [
            {"source": "skills", "key": "speech", "comparator": "gte", "int_value": 2},
            {"source": "previous_dialogue", "key": "dlg_oath_accepted", "comparator": "present", "bool_value": True},
            {"source": "inventory", "key": "royal_seal", "comparator": "gte", "int_value": 1},
            {"source": "vitriol", "key": "introspection", "comparator": "gte", "int_value": 5},
            {"source": "flags", "key": "steward_marked", "comparator": "eq", "bool_value": True},
        ],
    }
    first = client.post("/v1/game/rules/gates/evaluate", json=payload, headers=headers)
    second = client.post("/v1/game/rules/gates/evaluate", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload == second_payload
    assert first_payload["allowed"] is True
    assert first_payload["matched_count"] == first_payload["total_count"]
    assert fake.place_calls == 2
    app.dependency_overrides.clear()


def test_content_validate_does_not_touch_kernel() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _RealmRow:
        def __init__(self, slug: str) -> None:
            self.slug = slug

    class _FakeRepo:
        def get_realm_by_slug(self, slug: str) -> _RealmRow:
            return _RealmRow(slug)

    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=_FakeRepo(), kernel=kernel)
    client = TestClient(app)
    res = client.post(
        "/v1/content/validate",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "scene_1",
            "source": "cobra",
            "payload": "entity demo_gate 1 2 portal\n  lex TyKoWuVu",
        },
        headers=_headers("lesson.read"),
    )
    assert res.status_code == 200
    assert fake.place_calls == 0
    assert fake.attest_calls == 0
    app.dependency_overrides.clear()


def test_scene_graph_emit_requires_realm_scene_match() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    bad = client.post(
        "/v1/game/scene-graph/emit",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "scene_1",
            "nodes": [{"node_id": "n1", "kind": "spawn", "x": 0, "y": 0, "metadata": {}}],
            "edges": [],
        },
        headers=headers,
    )
    assert bad.status_code == 400
    assert fake.place_calls == 0

    ok = client.post(
        "/v1/game/scene-graph/emit",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/scene_1",
            "nodes": [{"node_id": "n1", "kind": "spawn", "x": 0, "y": 0, "metadata": {}}],
            "edges": [],
        },
        headers=headers,
    )
    assert ok.status_code == 200
    assert fake.place_calls == 1
    app.dependency_overrides.clear()
