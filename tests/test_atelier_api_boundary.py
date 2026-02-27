from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
from typing import Any, Dict, Mapping, Optional, Sequence

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(API_APP_DIR))

from atelier_api.main import app, _atelier_service, _kernel_client, _kernel_only_service  # type: ignore[import]
from atelier_api.kernel_integration import KernelIntegrationService  # type: ignore[import]
from atelier_api.models import PlayerState, Realm, WorldRegion  # type: ignore[import]
from atelier_api.services import AtelierService  # type: ignore[import]
from atelier_api.types import EdgeObj, FrontierObj, KernelEventObj, ObserveResponse  # type: ignore[import]
from qqva.world_stream import WorldStreamController  # type: ignore[import]


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


def test_game_runtime_action_catalog_lists_supported_runtime_actions() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    headers = _headers("kernel.observe", role="artisan")
    res = client.get("/v1/game/runtime/actions/catalog", headers=headers)
    assert res.status_code == 200
    payload = res.json()
    assert payload["action_count"] >= 20
    actions = payload["actions"]
    by_kind = {item["kind"]: item for item in actions}
    assert "world.region.preload.scenegraph" in by_kind
    preload = by_kind["world.region.preload.scenegraph"]
    assert preload["requires_realm"] is True
    assert "chunk_size" in preload["payload_fields"]
    assert "scene_content" in preload["payload_fields"]
    assert "world.stream.status" in by_kind
    assert "market.trade" in by_kind
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


def test_game_dialogue_resolve_uses_player_state_and_is_deterministic() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _DialogueRepo:
        def __init__(self) -> None:
            now = datetime.now(timezone.utc)
            self.rows: dict[tuple[str, str], PlayerState] = {
                ("main", "player_dialogue"): PlayerState(
                    workspace_id="main",
                    actor_id="player_dialogue",
                    state_version=3,
                    levels_json="{}",
                    skills_json='{"alchemy":3,"speech":1}',
                    perks_json="{}",
                    vitriol_json='{"effective":{"ingenuity":6}}',
                    inventory_json='{"items":{"seal":1}}',
                    market_json="{}",
                    flags_json='{"dialogue_flags":["met_guard"],"previous_dialogue":["dlg_intro"],"boss_seen":false}',
                    clock_json='{"tick":42}',
                    created_at=now,
                    updated_at=now,
                )
            }

        def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
            return self.rows.get((workspace_id, actor_id))

        def save_player_state(self, row: PlayerState) -> PlayerState:
            self.rows[(row.workspace_id, row.actor_id)] = row
            return row

    repo = _DialogueRepo()
    app.dependency_overrides[_atelier_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    headers = _headers("kernel.place", role="steward", token=_admin_gate_token("tester", "workshop-1"))
    body = {
        "workspace_id": "main",
        "actor_id": "player_dialogue",
        "dialogue_id": "dlg_gate",
        "node_id": "n0",
        "choices": [
            {
                "choice_id": "c_fail",
                "text": "Locked",
                "next_node_id": "n_fail",
                "priority": 5,
                "requirements": [{"source": "skills", "key": "alchemy", "comparator": "gte", "int_value": 9}],
            },
            {
                "choice_id": "c_pass",
                "text": "Proceed",
                "next_node_id": "n1",
                "priority": 10,
                "requirements": [
                    {"source": "skills", "key": "alchemy", "comparator": "gte", "int_value": 3},
                    {"source": "dialogue_flags", "key": "met_guard", "comparator": "present", "bool_value": True},
                ],
            },
        ],
    }

    first = client.post("/v1/game/dialogue/resolve", json=body, headers=headers)
    second = client.post("/v1/game/dialogue/resolve", json=body, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["hash"] == second_payload["hash"]
    assert first_payload["state_source"] == "player_state"
    assert first_payload["eligible_choice_ids"] == ["c_pass"]
    assert first_payload["selected_choice_id"] == "c_pass"
    assert first_payload["selected_next_node_id"] == "n1"
    app.dependency_overrides.clear()


def test_game_quest_transition_persists_state_machine_in_player_state() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _QuestRepo:
        def __init__(self) -> None:
            self.rows: dict[tuple[str, str], PlayerState] = {}

        def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
            return self.rows.get((workspace_id, actor_id))

        def save_player_state(self, row: PlayerState) -> PlayerState:
            self.rows[(row.workspace_id, row.actor_id)] = row
            return row

    repo = _QuestRepo()
    app.dependency_overrides[_atelier_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    place_headers = _headers("kernel.place", role="steward", token=_admin_gate_token("tester", "workshop-1"))
    observe_headers = _headers("kernel.observe", role="artisan")

    advance = client.post(
        "/v1/game/quests/transition",
        json={
            "workspace_id": "main",
            "actor_id": "player_quest",
            "quest_id": "q_intro",
            "event_id": "evt_start",
            "from_states": ["inactive"],
            "to_state": "active",
            "set_flags": {"quest_intro_started": True},
        },
        headers=place_headers,
    )
    assert advance.status_code == 200
    advance_payload = advance.json()
    assert advance_payload["transitioned"] is True
    assert advance_payload["previous_state"] == "inactive"
    assert advance_payload["next_state"] == "active"

    blocked = client.post(
        "/v1/game/quests/transition",
        json={
            "workspace_id": "main",
            "actor_id": "player_quest",
            "quest_id": "q_intro",
            "event_id": "evt_start_again",
            "from_states": ["inactive"],
            "to_state": "active",
        },
        headers=place_headers,
    )
    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert blocked_payload["transitioned"] is False
    assert blocked_payload["reason"] == "invalid_from_state"

    state = client.get("/v1/game/state?workspace_id=main&actor_id=player_quest", headers=observe_headers)
    assert state.status_code == 200
    state_payload = state.json()
    quest_states = state_payload["tables"]["flags"]["quest_states"]
    assert quest_states["q_intro"]["state"] == "active"
    assert state_payload["tables"]["flags"]["quest_intro_started"] is True
    app.dependency_overrides.clear()


def test_game_quest_advance_resolves_edges_deterministically_and_persists_step() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _QuestAdvanceRepo:
        def __init__(self) -> None:
            self.rows: dict[tuple[str, str], PlayerState] = {}

        def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
            return self.rows.get((workspace_id, actor_id))

        def save_player_state(self, row: PlayerState) -> PlayerState:
            self.rows[(row.workspace_id, row.actor_id)] = row
            return row

    repo = _QuestAdvanceRepo()
    app.dependency_overrides[_atelier_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    headers = _headers("kernel.place", role="steward", token=_admin_gate_token("tester", "workshop-1"))
    observe_headers = _headers("kernel.observe", role="artisan")
    body = {
        "workspace_id": "main",
        "actor_id": "player_quest_advance",
        "quest_id": "q_main",
        "event_id": "evt_step_1",
        "current_step_id": "s_start",
        "state": {
            "skills": {"alchemy": 4},
            "inventory": {"lapidus_key": 1},
            "vitriol": {},
            "dialogue_flags": ["met_guard"],
            "previous_dialogue": ["dlg_intro"],
            "flags": {"intro_done": True},
        },
        "edges": [
            {
                "edge_id": "e_blocked",
                "to_step_id": "s_blocked",
                "priority": 5,
                "requirements": [{"source": "skills", "key": "alchemy", "comparator": "gte", "int_value": 8}],
            },
            {
                "edge_id": "e_open",
                "to_step_id": "s_market",
                "priority": 10,
                "requirements": [
                    {"source": "skills", "key": "alchemy", "comparator": "gte", "int_value": 3},
                    {"source": "dialogue_flags", "key": "met_guard", "comparator": "present", "bool_value": True},
                ],
                "set_flags": {"quest_main_market_open": True},
            },
        ],
    }
    first = client.post("/v1/game/quests/advance", json=body, headers=headers)
    second = client.post("/v1/game/quests/advance", json={**body, "actor_id": "player_quest_advance_b"}, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["advanced"] is True
    assert first_payload["selected_edge_id"] == "e_open"
    assert first_payload["next_step_id"] == "s_market"
    assert first_payload["eligible_edge_ids"] == ["e_open"]
    assert second_payload["advanced"] is True
    assert second_payload["selected_edge_id"] == "e_open"
    assert second_payload["next_step_id"] == "s_market"

    state = client.get(
        "/v1/game/state?workspace_id=main&actor_id=player_quest_advance",
        headers=observe_headers,
    )
    assert state.status_code == 200
    state_payload = state.json()
    quest_state = state_payload["tables"]["flags"]["quest_states"]["q_main"]
    assert quest_state["step_id"] == "s_market"
    assert state_payload["tables"]["flags"]["quest_main_market_open"] is True
    app.dependency_overrides.clear()


def test_game_quest_graph_catalog_and_advance_by_graph_are_headless_and_persisted() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _ManifestRow:
        def __init__(
            self,
            *,
            id: str,
            workspace_id: str,
            realm_id: str,
            manifest_id: str,
            name: str,
            kind: str,
            payload_json: str,
            payload_hash: str,
            created_at: datetime,
        ) -> None:
            self.id = id
            self.workspace_id = workspace_id
            self.realm_id = realm_id
            self.manifest_id = manifest_id
            self.name = name
            self.kind = kind
            self.payload_json = payload_json
            self.payload_hash = payload_hash
            self.created_at = created_at

    class _QuestGraphRepo:
        def __init__(self) -> None:
            self.rows: dict[tuple[str, str], PlayerState] = {}
            self.manifests: list[_ManifestRow] = []

        def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
            return self.rows.get((workspace_id, actor_id))

        def save_player_state(self, row: PlayerState) -> PlayerState:
            self.rows[(row.workspace_id, row.actor_id)] = row
            return row

        def list_asset_manifests(self, workspace_id: str) -> Sequence[_ManifestRow]:
            return [row for row in self.manifests if row.workspace_id == workspace_id]

        def create_asset_manifest(self, row: object) -> object:
            payload_json = str(getattr(row, "payload_json", "{}"))
            manifest = _ManifestRow(
                id=f"m_{len(self.manifests) + 1}",
                workspace_id=str(getattr(row, "workspace_id")),
                realm_id=str(getattr(row, "realm_id")),
                manifest_id=str(getattr(row, "manifest_id")),
                name=str(getattr(row, "name")),
                kind=str(getattr(row, "kind")),
                payload_json=payload_json,
                payload_hash=str(getattr(row, "payload_hash")),
                created_at=datetime.now(timezone.utc),
            )
            self.manifests.append(manifest)
            return manifest

    repo = _QuestGraphRepo()
    app.dependency_overrides[_atelier_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    write_headers = _headers("quest.write", role="steward")
    read_headers = _headers("quest.read", role="artisan")
    place_headers = _headers("kernel.place", role="steward", token=_admin_gate_token("tester", "workshop-1"))
    observe_headers = _headers("kernel.observe", role="artisan")

    upsert = client.post(
        "/v1/game/quests/graphs",
        json={
            "workspace_id": "main",
            "quest_id": "q_market",
            "version": "v1",
            "start_step_id": "s0",
            "headless": True,
            "steps": [
                {
                    "step_id": "s0",
                    "edges": [
                        {
                            "edge_id": "e1",
                            "to_step_id": "s1",
                            "priority": 10,
                            "requirements": [
                                {"source": "skills", "key": "alchemy", "comparator": "gte", "int_value": 2}
                            ],
                            "set_flags": {"market_unlocked": True},
                        }
                    ],
                }
            ],
        },
        headers=write_headers,
    )
    assert upsert.status_code == 200
    graph_payload = upsert.json()
    assert graph_payload["headless"] is True
    assert graph_payload["version"] == "v1"
    assert graph_payload["steps"][0]["step_id"] == "s0"

    loaded = client.get(
        "/v1/game/quests/graphs?workspace_id=main&quest_id=q_market&version=v1",
        headers=read_headers,
    )
    assert loaded.status_code == 200
    assert loaded.json()["manifest_id"] == graph_payload["manifest_id"]

    advance = client.post(
        "/v1/game/quests/advance/by-graph",
        json={
            "workspace_id": "main",
            "actor_id": "player_graph",
            "quest_id": "q_market",
            "event_id": "evt_graph_1",
            "current_step_id": "s0",
            "version": "v1",
            "headless": True,
            "state": {
                "skills": {"alchemy": 3},
                "inventory": {},
                "vitriol": {},
                "dialogue_flags": [],
                "previous_dialogue": [],
                "flags": {},
            },
        },
        headers=place_headers,
    )
    assert advance.status_code == 200
    adv_payload = advance.json()
    assert adv_payload["advance"]["advanced"] is True
    assert adv_payload["advance"]["next_step_id"] == "s1"

    state = client.get(
        "/v1/game/state?workspace_id=main&actor_id=player_graph",
        headers=observe_headers,
    )
    assert state.status_code == 200
    flags = state.json()["tables"]["flags"]
    assert flags["quest_states"]["q_market"]["step_id"] == "s1"
    assert flags["market_unlocked"] is True

    rejected = client.post(
        "/v1/game/quests/advance/by-graph",
        json={
            "workspace_id": "main",
            "actor_id": "player_graph",
            "quest_id": "q_market",
            "event_id": "evt_graph_2",
            "current_step_id": "s1",
            "version": "v1",
            "headless": False,
            "state": {"skills": {}, "inventory": {}, "vitriol": {}, "dialogue_flags": [], "previous_dialogue": [], "flags": {}},
        },
        headers=place_headers,
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "quests_must_be_headless"
    app.dependency_overrides.clear()


def test_game_quest_graph_list_supports_filters_and_paging() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _ManifestRow:
        def __init__(
            self,
            *,
            id: str,
            workspace_id: str,
            realm_id: str,
            manifest_id: str,
            name: str,
            kind: str,
            payload_json: str,
            payload_hash: str,
            created_at: datetime,
        ) -> None:
            self.id = id
            self.workspace_id = workspace_id
            self.realm_id = realm_id
            self.manifest_id = manifest_id
            self.name = name
            self.kind = kind
            self.payload_json = payload_json
            self.payload_hash = payload_hash
            self.created_at = created_at

    class _QuestGraphListRepo:
        def __init__(self) -> None:
            self.manifests: list[_ManifestRow] = []

        def list_asset_manifests(self, workspace_id: str) -> Sequence[_ManifestRow]:
            return [row for row in self.manifests if row.workspace_id == workspace_id]

        def create_asset_manifest(self, row: object) -> object:
            idx = len(self.manifests) + 1
            manifest = _ManifestRow(
                id=f"m_{idx}",
                workspace_id=str(getattr(row, "workspace_id")),
                realm_id=str(getattr(row, "realm_id")),
                manifest_id=str(getattr(row, "manifest_id")),
                name=str(getattr(row, "name")),
                kind=str(getattr(row, "kind")),
                payload_json=str(getattr(row, "payload_json")),
                payload_hash=str(getattr(row, "payload_hash")),
                created_at=datetime.now(timezone.utc),
            )
            self.manifests.append(manifest)
            return manifest

    repo = _QuestGraphListRepo()
    app.dependency_overrides[_atelier_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    write_headers = _headers("quest.write", role="steward")
    read_headers = _headers("quest.read", role="artisan")

    for quest_id, version in [("q_alpha", "v1"), ("q_alpha", "v2"), ("q_beta", "v1")]:
        res = client.post(
            "/v1/game/quests/graphs",
            json={
                "workspace_id": "main",
                "quest_id": quest_id,
                "version": version,
                "start_step_id": "s0",
                "headless": True,
                "steps": [{"step_id": "s0", "edges": []}],
            },
            headers=write_headers,
        )
        assert res.status_code == 200

    full = client.get(
        "/v1/game/quests/graphs/all?workspace_id=main",
        headers=read_headers,
    )
    assert full.status_code == 200
    full_payload = full.json()
    assert full_payload["total"] == 3
    assert len(full_payload["items"]) == 3

    filtered = client.get(
        "/v1/game/quests/graphs/all?workspace_id=main&quest_id=q_alpha",
        headers=read_headers,
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["total"] == 2
    assert all(item["quest_id"] == "q_alpha" for item in filtered_payload["items"])

    paged = client.get(
        "/v1/game/quests/graphs/all?workspace_id=main&limit=1&offset=1",
        headers=read_headers,
    )
    assert paged.status_code == 200
    paged_payload = paged.json()
    assert paged_payload["total"] == 3
    assert paged_payload["limit"] == 1
    assert paged_payload["offset"] == 1
    assert len(paged_payload["items"]) == 1
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


def test_game_runtime_replay_reexecutes_stored_plan_and_verifies_hash() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _RuntimePlanRepo:
        def __init__(self) -> None:
            self._runs: list[object] = []

        def create_runtime_plan_run(self, row: object) -> object:
            if getattr(row, "id", None) is None:
                setattr(row, "id", f"rpr_{len(self._runs) + 1}")
            self._runs.append(row)
            return row

        def get_latest_runtime_plan_run(self, workspace_id: str, actor_id: str, plan_id: str) -> object | None:
            matches = [
                row
                for row in self._runs
                if getattr(row, "workspace_id", "") == workspace_id
                and getattr(row, "actor_id", "") == actor_id
                and getattr(row, "plan_id", "") == plan_id
            ]
            return matches[-1] if matches else None

    repo = _RuntimePlanRepo()
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    app.dependency_overrides[_atelier_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    consume_payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "replayable_plan",
        "actions": [
            {
                "action_id": "compute_vitriol",
                "kind": "vitriol.compute",
                "payload": {
                    "base": {
                        "vitality": 7,
                        "introspection": 6,
                        "tactility": 6,
                        "reflectivity": 6,
                        "ingenuity": 6,
                        "ostentation": 6,
                        "levity": 6,
                    },
                    "modifiers": [],
                    "current_tick": 42,
                },
            }
        ],
    }
    consumed = client.post("/v1/game/runtime/consume", json=consume_payload, headers=headers)
    assert consumed.status_code == 200
    consumed_hash = consumed.json()["hash"]

    replayed = client.post(
        "/v1/game/runtime/replay",
        json={"workspace_id": "main", "actor_id": "player", "plan_id": "replayable_plan"},
        headers=headers,
    )
    assert replayed.status_code == 200
    replay_payload = replayed.json()
    assert replay_payload["hash_match"] is True
    assert replay_payload["baseline_hash"] == consumed_hash
    assert replay_payload["replay_hash"] == consumed_hash
    assert replay_payload["baseline_run_id"] != ""
    app.dependency_overrides.clear()


def test_game_runtime_runs_endpoint_lists_persisted_runs_with_filters() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _RuntimePlanRepo:
        def __init__(self) -> None:
            self._runs: list[object] = []

        def create_runtime_plan_run(self, row: object) -> object:
            if getattr(row, "id", None) is None:
                setattr(row, "id", f"rpr_{len(self._runs) + 1}")
            self._runs.append(row)
            return row

        def get_latest_runtime_plan_run(self, workspace_id: str, actor_id: str, plan_id: str) -> object | None:
            matches = [
                row
                for row in self._runs
                if getattr(row, "workspace_id", "") == workspace_id
                and getattr(row, "actor_id", "") == actor_id
                and getattr(row, "plan_id", "") == plan_id
            ]
            return matches[-1] if matches else None

        def list_runtime_plan_runs_for_actor(self, workspace_id: str, actor_id: str, plan_id: str | None = None):
            rows = [
                row
                for row in self._runs
                if getattr(row, "workspace_id", "") == workspace_id
                and getattr(row, "actor_id", "") == actor_id
            ]
            if plan_id is not None and plan_id.strip() != "":
                rows = [row for row in rows if getattr(row, "plan_id", "") == plan_id]
            rows.sort(
                key=lambda row: (getattr(row, "created_at", datetime.now(timezone.utc)), getattr(row, "id", "")),
                reverse=True,
            )
            return rows

    repo = _RuntimePlanRepo()
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    app.dependency_overrides[_atelier_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    place_headers = _headers("kernel.place", role="steward", token=token)
    observe_headers = _headers("kernel.observe", role="artisan")

    for plan_id in ["plan_a", "plan_b", "plan_a"]:
        consumed = client.post(
            "/v1/game/runtime/consume",
            json={
                "workspace_id": "main",
                "actor_id": "player",
                "plan_id": plan_id,
                "actions": [
                    {
                        "action_id": f"compute_{plan_id}",
                        "kind": "vitriol.compute",
                        "payload": {"base": {"vitality": 7}, "modifiers": [], "current_tick": 1},
                    }
                ],
            },
            headers=place_headers,
        )
        assert consumed.status_code == 200

    all_runs = client.get(
        "/v1/game/runtime/runs?workspace_id=main&actor_id=player&limit=2",
        headers=observe_headers,
    )
    assert all_runs.status_code == 200
    all_payload = all_runs.json()
    assert len(all_payload) == 2
    assert all_payload[0]["plan_id"] in {"plan_a", "plan_b"}
    assert "applied_count" in all_payload[0]["result_summary"]

    filtered = client.get(
        "/v1/game/runtime/runs?workspace_id=main&actor_id=player&plan_id=plan_b",
        headers=observe_headers,
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert len(filtered_payload) == 1
    assert filtered_payload[0]["plan_id"] == "plan_b"
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
    assert any(
        item["realm_id"] == "lapidus" and item["dominant_operator"] == "lord_nexiott"
        for item in results["markets"]["result"]["items"]
    )
    assert results["status"]["ok"] is True
    assert results["status"]["result"]["realm_id"] == "lapidus"
    assert results["runload"]["ok"] is True
    assert results["runload"]["result"]["unloaded"] is True
    app.dependency_overrides.clear()


def test_game_runtime_consume_world_stream_runtime_path_applies_capacity_and_realm_scoping() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(
        repo=None,
        kernel=kernel,
        world_stream=WorldStreamController(max_loaded_regions=2),
    )
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "world_runtime_capacity_plan",
        "actions": [
            {
                "action_id": "load_pin",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "lapidus",
                    "region_key": "lapidus/pinned",
                    "payload": {"seed": 1},
                    "cache_policy": "pin",
                },
            },
            {
                "action_id": "load_cache",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "lapidus",
                    "region_key": "lapidus/cache",
                    "payload": {"seed": 2},
                    "cache_policy": "cache",
                },
            },
            {
                "action_id": "load_stream",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "lapidus",
                    "region_key": "lapidus/stream",
                    "payload": {"seed": 3},
                    "cache_policy": "stream",
                },
            },
            {
                "action_id": "status_lapidus",
                "kind": "world.stream.status",
                "payload": {"realm_id": "lapidus"},
            },
            {
                "action_id": "load_mercurie",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "mercurie",
                    "region_key": "mercurie/glade",
                    "payload": {"seed": 4},
                    "cache_policy": "cache",
                },
            },
            {
                "action_id": "status_mercurie",
                "kind": "world.stream.status",
                "payload": {"realm_id": "mercurie"},
            },
        ],
    }
    res = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["failed_count"] == 0
    results = {item["action_id"]: item for item in out["results"]}
    assert results["load_pin"]["ok"] is True
    assert results["load_cache"]["ok"] is True
    assert results["load_stream"]["ok"] is True
    lapidus_status = results["status_lapidus"]["result"]
    assert lapidus_status["total_regions"] == 3
    assert lapidus_status["loaded_count"] == 2
    assert lapidus_status["unloaded_count"] == 1
    assert lapidus_status["policy_counts"]["pin"] == 1
    assert lapidus_status["policy_counts"]["stream"] == 1
    assert lapidus_status["policy_counts"]["cache"] == 0
    mercurie_status = results["status_mercurie"]["result"]
    assert mercurie_status["realm_id"] == "mercurie"
    assert mercurie_status["total_regions"] == 1
    assert mercurie_status["loaded_count"] == 1
    assert mercurie_status["unloaded_count"] == 0
    app.dependency_overrides.clear()


def test_game_runtime_consume_mixed_realm_world_stream_plan_is_hash_deterministic() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(
        repo=None,
        kernel=kernel,
        world_stream=WorldStreamController(max_loaded_regions=3),
    )
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "mixed_realm_world_stream_plan",
        "actions": [
            {
                "action_id": "l1",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "lapidus",
                    "region_key": "lapidus/a",
                    "payload": {"seed": 11},
                    "cache_policy": "pin",
                },
            },
            {
                "action_id": "l2",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "mercurie",
                    "region_key": "mercurie/a",
                    "payload": {"seed": 12},
                    "cache_policy": "cache",
                },
            },
            {
                "action_id": "l3",
                "kind": "world.region.load",
                "payload": {
                    "realm_id": "sulphera",
                    "region_key": "sulphera/a",
                    "payload": {"seed": 13},
                    "cache_policy": "stream",
                },
            },
            {
                "action_id": "u1",
                "kind": "world.region.unload",
                "payload": {"realm_id": "mercurie", "region_key": "mercurie/a"},
            },
            {"action_id": "s1", "kind": "world.stream.status", "payload": {"realm_id": "lapidus"}},
            {"action_id": "s2", "kind": "world.stream.status", "payload": {"realm_id": "mercurie"}},
            {"action_id": "s3", "kind": "world.stream.status", "payload": {"realm_id": "sulphera"}},
        ],
    }
    first = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    second = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["hash"] == second_payload["hash"]
    assert first_payload["applied_count"] == 7
    assert first_payload["failed_count"] == 0
    app.dependency_overrides.clear()


def test_game_runtime_consume_supports_scenegraph_region_preload_action() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(
        repo=None,
        kernel=kernel,
        world_stream=WorldStreamController(max_loaded_regions=8),
    )
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "scenegraph_preload_plan",
        "actions": [
            {
                "action_id": "preload",
                "kind": "world.region.preload.scenegraph",
                "payload": {
                    "realm_id": "lapidus",
                    "scene_id": "lapidus/player_home",
                    "chunk_size": 10,
                    "cache_policy": "stream",
                    "region_prefix": "lapidus/player_home",
                    "scene_content": {
                        "nodes": [
                            {"node_id": "desk", "kind": "furniture", "x": 2, "y": 3, "metadata": {"z": 0}},
                            {"node_id": "bed", "kind": "furniture", "x": 12, "y": 3, "metadata": {"z": 0}},
                            {"node_id": "alembic", "kind": "tool", "x": 2, "y": 14, "metadata": {"z": 1}},
                        ],
                        "edges": [],
                    },
                },
            },
            {"action_id": "status", "kind": "world.stream.status", "payload": {"realm_id": "lapidus"}},
        ],
    }
    res = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["failed_count"] == 0
    results = {item["action_id"]: item for item in out["results"]}
    preload_result = results["preload"]["result"]
    assert preload_result["region_count"] == 3
    assert sorted(preload_result["region_keys"]) == [
        "lapidus/player_home/chunk_0_0",
        "lapidus/player_home/chunk_0_1",
        "lapidus/player_home/chunk_1_0",
    ]
    status_result = results["status"]["result"]
    assert status_result["total_regions"] == 3
    assert status_result["loaded_count"] == 3
    assert status_result["policy_counts"]["stream"] == 3
    app.dependency_overrides.clear()


def test_game_runtime_consume_supports_market_stock_adjust_and_trade_override() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "market_stock_runtime_plan",
        "actions": [
            {
                "action_id": "set_stock",
                "kind": "world.market.stock.adjust",
                "payload": {"realm_id": "lapidus", "item_id": "iron_ingot", "set_qty": 3},
            },
            {
                "action_id": "buy_trade",
                "kind": "market.trade",
                "payload": {
                    "realm_id": "lapidus",
                    "item_id": "iron_ingot",
                    "side": "buy",
                    "quantity": 5,
                    "unit_price_cents": 1000,
                    "fee_bp": 0,
                    "wallet_cents": 10000,
                    "inventory_qty": 0,
                    "available_liquidity": 999,
                },
            },
            {
                "action_id": "list_markets",
                "kind": "world.markets.list",
                "payload": {"realm_id": "lapidus"},
            },
            {
                "action_id": "add_stock",
                "kind": "world.market.stock.adjust",
                "payload": {"realm_id": "lapidus", "item_id": "iron_ingot", "delta": 2},
            },
            {
                "action_id": "list_markets_after",
                "kind": "world.markets.list",
                "payload": {"realm_id": "lapidus"},
            },
        ],
    }
    res = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["failed_count"] == 0
    results = {item["action_id"]: item for item in out["results"]}
    assert results["set_stock"]["result"]["stock_before_qty"] == 1200
    assert results["set_stock"]["result"]["stock_after_qty"] == 3
    assert results["buy_trade"]["ok"] is True
    assert results["buy_trade"]["result"]["filled_qty"] == 3
    assert results["buy_trade"]["result"]["stock_before_qty"] == 3
    assert results["buy_trade"]["result"]["stock_after_qty"] == 0
    first_market_items = results["list_markets"]["result"]["items"]
    assert isinstance(first_market_items, list)
    assert first_market_items[0]["stock"]["iron_ingot"] == 0
    assert results["add_stock"]["result"]["stock_before_qty"] == 0
    assert results["add_stock"]["result"]["stock_after_qty"] == 2
    second_market_items = results["list_markets_after"]["result"]["items"]
    assert isinstance(second_market_items, list)
    assert second_market_items[0]["stock"]["iron_ingot"] == 2
    app.dependency_overrides.clear()


def test_game_runtime_consume_supports_market_sovereignty_transition_with_redistribution() -> None:
    fake = FakeKernelClient()
    app.dependency_overrides[_kernel_client] = lambda: fake
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    payload = {
        "workspace_id": "main",
        "actor_id": "player",
        "plan_id": "lapidus_sovereignty_plan",
        "actions": [
            {
                "action_id": "transition",
                "kind": "world.market.sovereignty.transition",
                "payload": {
                    "realm_id": "lapidus",
                    "overthrow": True,
                    "victor_id": "player_commonwealth",
                    "market_network": "realm_redistribution_council",
                    "dominance_bp": 800,
                    "redistribution_mode": "universal_staple_equity",
                    "beneficiary_groups": ["citizens", "artisans", "farmers"],
                    "tick": 999,
                },
            },
            {
                "action_id": "markets_after_transition",
                "kind": "world.markets.list",
                "payload": {"realm_id": "lapidus"},
            },
        ],
    }
    res = client.post("/v1/game/runtime/consume", json=payload, headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["failed_count"] == 0
    results = {item["action_id"]: item for item in out["results"]}
    assert results["transition"]["ok"] is True
    assert results["transition"]["result"]["prior_operator"] == "lord_nexiott"
    assert results["transition"]["result"]["new_operator"] == "player_commonwealth"
    assert results["transition"]["result"]["market_network"] == "realm_redistribution_council"
    assert results["transition"]["result"]["dominance_bp"] == 800
    markets = results["markets_after_transition"]["result"]["items"]
    assert isinstance(markets, list)
    assert len(markets) == 1
    lapidus = markets[0]
    assert lapidus["dominant_operator"] == "player_commonwealth"
    assert lapidus["market_network"] == "realm_redistribution_council"
    assert lapidus["dominance_bp"] == 800
    assert lapidus["redistribution_policy"]["active"] is True
    assert lapidus["redistribution_policy"]["mode"] == "universal_staple_equity"
    app.dependency_overrides.clear()


def test_game_tick_persistent_queue_executes_due_events_only() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _TickRepo:
        def __init__(self) -> None:
            self.rows: dict[tuple[str, str], PlayerState] = {}

        def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
            return self.rows.get((workspace_id, actor_id))

        def save_player_state(self, row: PlayerState) -> PlayerState:
            self.rows[(row.workspace_id, row.actor_id)] = row
            return row

    repo = _TickRepo()
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)

    first = client.post(
        "/v1/game/state/tick",
        json={
            "workspace_id": "main",
            "actor_id": "player_tick_q",
            "dt_ms": 100,
            "events": [
                {
                    "event_id": "e_future",
                    "kind": "flags.set",
                    "due_tick": 2,
                    "payload": {"key": "future_flag", "value": True},
                }
            ],
        },
        headers=headers,
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["tick"] == 1
    assert first_payload["processed_count"] == 0
    assert first_payload["queue_size"] == 1
    assert first_payload["tables"]["flags"].get("future_flag") is None

    second = client.post(
        "/v1/game/state/tick",
        json={
            "workspace_id": "main",
            "actor_id": "player_tick_q",
            "dt_ms": 100,
            "events": [],
        },
        headers=headers,
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["tick"] == 2
    assert second_payload["processed_count"] == 1
    assert second_payload["queue_size"] == 0
    assert second_payload["tables"]["flags"]["future_flag"] is True
    assert len(second_payload["results"]) == 1
    assert second_payload["results"][0]["event_id"] == "e_future"
    assert second_payload["results"][0]["due_tick"] == 2
    app.dependency_overrides.clear()


def test_game_tick_event_queue_order_is_deterministic() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)

    class _TickRepo:
        def __init__(self) -> None:
            self.rows: dict[tuple[str, str], PlayerState] = {}

        def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
            return self.rows.get((workspace_id, actor_id))

        def save_player_state(self, row: PlayerState) -> PlayerState:
            self.rows[(row.workspace_id, row.actor_id)] = row
            return row

    repo = _TickRepo()
    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
    client = TestClient(app)
    token = _admin_gate_token("tester", "workshop-1")
    headers = _headers("kernel.place", role="steward", token=token)
    body = {
        "workspace_id": "main",
        "dt_ms": 50,
        "events": [
            {"event_id": "late", "kind": "flags.set", "due_tick": 3, "payload": {"key": "late", "value": True}},
            {"event_id": "early", "kind": "flags.set", "due_tick": 2, "payload": {"key": "early", "value": True}},
        ],
    }

    run_one_t1 = client.post("/v1/game/state/tick", json={**body, "actor_id": "player_tick_d1"}, headers=headers)
    run_two_t1 = client.post("/v1/game/state/tick", json={**body, "actor_id": "player_tick_d2"}, headers=headers)
    assert run_one_t1.status_code == 200
    assert run_two_t1.status_code == 200
    p1 = run_one_t1.json()
    p2 = run_two_t1.json()
    assert p1["queue_size"] == p2["queue_size"] == 2
    assert p1["processed_count"] == p2["processed_count"] == 0
    assert p1["queue_size"] == 2

    run_one_t2 = client.post(
        "/v1/game/state/tick",
        json={"workspace_id": "main", "actor_id": "player_tick_d1", "events": [], "dt_ms": 50},
        headers=headers,
    )
    run_two_t2 = client.post(
        "/v1/game/state/tick",
        json={"workspace_id": "main", "actor_id": "player_tick_d2", "events": [], "dt_ms": 50},
        headers=headers,
    )
    assert run_one_t2.status_code == 200
    assert run_two_t2.status_code == 200
    q1 = run_one_t2.json()
    q2 = run_two_t2.json()
    assert q1["queue_size"] == q2["queue_size"] == 1
    assert q1["processed_count"] == 1
    assert q2["processed_count"] == 1
    assert q1["results"][0]["event_id"] == "early"
    assert q2["results"][0]["event_id"] == "early"

    run_one_t3 = client.post(
        "/v1/game/state/tick",
        json={"workspace_id": "main", "actor_id": "player_tick_d1", "events": [], "dt_ms": 50},
        headers=headers,
    )
    run_two_t3 = client.post(
        "/v1/game/state/tick",
        json={"workspace_id": "main", "actor_id": "player_tick_d2", "events": [], "dt_ms": 50},
        headers=headers,
    )
    assert run_one_t3.status_code == 200
    assert run_two_t3.status_code == 200
    r1 = run_one_t3.json()
    r2 = run_two_t3.json()
    assert r1["queue_size"] == r2["queue_size"] == 0
    assert r1["processed_count"] == 1
    assert r2["processed_count"] == 1
    assert r1["results"][0]["event_id"] == "late"
    assert r2["results"][0]["event_id"] == "late"
    assert r1["tables"]["flags"]["early"] is True
    assert r1["tables"]["flags"]["late"] is True
    app.dependency_overrides.clear()


def test_game_tick_soak_mixed_systems_is_deterministic_and_queue_bounded() -> None:
    def _run_soak() -> dict[str, object]:
        fake = FakeKernelClient()
        kernel = KernelIntegrationService(fake)

        class _SoakRepo:
            def __init__(self) -> None:
                now = datetime.now(timezone.utc)
                self.player_rows: dict[tuple[str, str], PlayerState] = {}
                self.realms: dict[str, Realm] = {
                    "lapidus": Realm(id="realm_lapidus", slug="lapidus", name="Lapidus", description="", created_at=now),
                    "mercurie": Realm(id="realm_mercurie", slug="mercurie", name="Mercurie", description="", created_at=now),
                    "sulphera": Realm(id="realm_sulphera", slug="sulphera", name="Sulphera", description="", created_at=now),
                }
                self.region_rows: dict[tuple[str, str, str], WorldRegion] = {}

            def get_player_state(self, workspace_id: str, actor_id: str) -> PlayerState | None:
                return self.player_rows.get((workspace_id, actor_id))

            def save_player_state(self, row: PlayerState) -> PlayerState:
                self.player_rows[(row.workspace_id, row.actor_id)] = row
                return row

            def get_realm_by_slug(self, slug: str) -> Realm | None:
                return self.realms.get(slug)

            def list_world_regions(self, workspace_id: str, realm_id: str | None = None):
                rows = [row for (ws, _, _), row in self.region_rows.items() if ws == workspace_id]
                if realm_id is not None:
                    rows = [row for row in rows if row.realm_id == realm_id]
                return rows

            def get_world_region(self, workspace_id: str, realm_id: str, region_key: str) -> WorldRegion | None:
                return self.region_rows.get((workspace_id, realm_id, region_key))

            def create_world_region(self, row: WorldRegion) -> WorldRegion:
                if row.id is None:
                    row.id = f"wr_{len(self.region_rows) + 1}"
                self.region_rows[(row.workspace_id, row.realm_id, row.region_key)] = row
                return row

            def save_world_region(self, row: WorldRegion) -> WorldRegion:
                if row.id is None:
                    row.id = f"wr_{len(self.region_rows) + 1}"
                self.region_rows[(row.workspace_id, row.realm_id, row.region_key)] = row
                return row

        repo = _SoakRepo()
        app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=repo, kernel=kernel)
        client = TestClient(app)
        token = _admin_gate_token("tester", "workshop-1")
        place_headers = _headers("kernel.place", role="steward", token=token)
        observe_headers = _headers("kernel.observe", role="artisan")
        actor_id = "player_tick_soak"

        tick_hashes: list[str] = []
        queue_sizes: list[int] = []

        for step in range(1, 321):
            if step % 10 == 0:
                runtime_res = client.post(
                    "/v1/game/runtime/consume",
                    json={
                        "workspace_id": "main",
                        "actor_id": actor_id,
                        "plan_id": f"soak_plan_{step}",
                        "actions": [
                            {
                                "action_id": f"load_{step}",
                                "kind": "world.region.load",
                                "payload": {
                                    "realm_id": "lapidus",
                                    "region_key": f"lapidus/sector-{step // 10:03d}",
                                    "payload": {"seed": step, "tiles": [step % 7, (step + 1) % 7]},
                                    "cache_policy": "stream",
                                },
                            },
                            {
                                "action_id": f"status_{step}",
                                "kind": "world.stream.status",
                                "payload": {"realm_id": "lapidus"},
                            },
                            {
                                "action_id": f"markets_{step}",
                                "kind": "world.markets.list",
                                "payload": {"realm_id": "lapidus"},
                            },
                        ],
                    },
                    headers=place_headers,
                )
                assert runtime_res.status_code == 200
                runtime_payload = runtime_res.json()
                assert runtime_payload["failed_count"] == 0

            if step % 15 == 0:
                djinn_res = client.post(
                    "/v1/game/djinn/apply",
                    json={
                        "workspace_id": "main",
                        "actor_id": actor_id,
                        "djinn_id": "giann",
                        "realm_id": "lapidus",
                        "scene_id": "lapidus/intro",
                        "ring_id": "overworld",
                        "target_frontiers": [f"F{step % 9}"],
                        "tick": step,
                        "reason": "soak",
                    },
                    headers=place_headers,
                )
                assert djinn_res.status_code == 200
                assert djinn_res.json()["effect"] == "open"

            if step % 20 == 0:
                dialogue_res = client.post(
                    "/v1/game/dialogue/emit",
                    json={
                        "workspace_id": "main",
                        "scene_id": "lapidus/intro",
                        "dialogue_id": f"dlg_soak_{step}",
                        "turns": [
                            {"line_id": "l2", "speaker_id": "npc", "raw": "second"},
                            {"line_id": "l1", "speaker_id": "player", "raw": "first"},
                        ],
                    },
                    headers=place_headers,
                )
                assert dialogue_res.status_code == 200
                assert dialogue_res.json()["emitted_line_ids"] == ["l1", "l2"]

            events: list[dict[str, object]] = [
                {"event_id": f"flag_{step}", "kind": "flags.set", "payload": {"key": "tick_parity_even", "value": step % 2 == 0}},
            ]
            if step % 3 == 0:
                events.append(
                    {
                        "event_id": f"quote_{step}",
                        "kind": "market.quote",
                        "payload": {
                            "realm_id": "lapidus",
                            "item_id": "iron_ingot",
                            "side": "buy",
                            "quantity": 1,
                            "base_price_cents": 1000,
                            "scarcity_bp": 10,
                            "spread_bp": 120,
                        },
                    }
                )
            if step % 4 == 0:
                events.append(
                    {
                        "event_id": f"trade_{step}",
                        "kind": "market.trade",
                        "payload": {
                            "realm_id": "lapidus",
                            "item_id": "iron_ingot",
                            "side": "buy",
                            "quantity": 1,
                            "unit_price_cents": 1000,
                            "wallet_cents": 100000,
                            "inventory_qty": 0,
                            "available_liquidity": 1000,
                        },
                    }
                )
            if step % 5 == 0:
                events.append(
                    {
                        "event_id": f"vitriol_{step}",
                        "kind": "vitriol.compute",
                        "payload": {
                            "base": {
                                "vitality": 6,
                                "introspection": 6,
                                "tactility": 6,
                                "reflectivity": 6,
                                "ingenuity": 6,
                                "ostentation": 6,
                                "levity": 6,
                            },
                            "modifiers": [],
                            "current_tick": step,
                        },
                    }
                )
            if step % 7 == 0:
                events.append(
                    {
                        "event_id": f"future_{step}",
                        "kind": "flags.set",
                        "due_tick": step + 2,
                        "payload": {"key": f"future_{step}", "value": True},
                    }
                )

            tick_res = client.post(
                "/v1/game/state/tick",
                json={
                    "workspace_id": "main",
                    "actor_id": actor_id,
                    "dt_ms": 16,
                    "events": events,
                },
                headers=place_headers,
            )
            assert tick_res.status_code == 200
            tick_payload = tick_res.json()
            tick_hashes.append(str(tick_payload["hash"]))
            queue_sizes.append(int(tick_payload["queue_size"]))
            assert int(tick_payload["queue_size"]) <= 32

        for _ in range(6):
            drain_res = client.post(
                "/v1/game/state/tick",
                json={"workspace_id": "main", "actor_id": actor_id, "dt_ms": 16, "events": []},
                headers=place_headers,
            )
            assert drain_res.status_code == 200
            drain_payload = drain_res.json()
            tick_hashes.append(str(drain_payload["hash"]))
            queue_sizes.append(int(drain_payload["queue_size"]))
            assert int(drain_payload["queue_size"]) <= 32

        state_res = client.get(
            f"/v1/game/state?workspace_id=main&actor_id={actor_id}",
            headers=observe_headers,
        )
        assert state_res.status_code == 200
        state_payload = state_res.json()
        app.dependency_overrides.clear()
        return {
            "tick_hashes": tick_hashes,
            "queue_sizes": queue_sizes,
            "state_hash": state_payload["hash"],
        }

    first = _run_soak()
    second = _run_soak()
    assert first["tick_hashes"] == second["tick_hashes"]
    assert first["queue_sizes"] == second["queue_sizes"]
    assert first["state_hash"] == second["state_hash"]


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


def test_isometric_render_contract_compiles_scene_regions_and_assets() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)
    now = datetime.now(timezone.utc)

    class _SceneRow:
        id = "scene-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        scene_id = "lapidus/intro"
        name = "Intro"
        description = ""
        content_json = (
            '{"nodes":[{"node_id":"desk_1","kind":"desk","x":4,"y":2,'
            '"metadata":{"z":1,"akinenwun":"TyKoWuVu"}}],"edges":[]}'
        )
        content_hash = "h_scene"
        created_at = now
        updated_at = now

    class _RegionRow:
        id = "region-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        region_key = "lapidus/sector-001"
        payload_json = (
            '{"entities":['
            '{"id":"npc_1","kind":"npc","x":5,"y":3,"z":0,"sprite":"npc_idle"},'
            '{"id":"mystery_1","kind":"unknown","x":6,"y":3,"z":0}'
            ']}'
        )
        payload_hash = "h_region"
        cache_policy = "cache"
        loaded = True
        created_at = now
        updated_at = now

    class _ManifestRow:
        id = "manifest-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "sprite_pack_1"
        name = "Sprites"
        kind = "sprite"
        payload_json = '{"atlas_version":"atlas_v2","desk":"atlas/desk.png","npc":"atlas/npc.png"}'
        payload_hash = "h_manifest"
        created_at = now

    class _MaterialManifestRow:
        id = "manifest-row-2"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "material_pack_1"
        name = "Materials"
        kind = "material"
        payload_json = '{"material_pack_version":"mat_v3","desk":"wood","npc":"cloth"}'
        payload_hash = "h_manifest_material"
        created_at = now

    class _RenderRepo:
        def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> _SceneRow | None:
            if workspace_id == "main" and realm_id == "lapidus" and scene_id == "lapidus/intro":
                return _SceneRow()
            return None

        def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[_RegionRow]:
            if workspace_id != "main":
                return []
            if realm_id is not None and realm_id != "lapidus":
                return []
            return [_RegionRow()]

        def list_asset_manifests(self, workspace_id: str) -> Sequence[_ManifestRow]:
            if workspace_id != "main":
                return []
            return [_ManifestRow(), _MaterialManifestRow()]

    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=_RenderRepo(), kernel=kernel)
    client = TestClient(app)
    res = client.post(
        "/v1/game/renderer/isometric-contract",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "tile_width": 64,
            "tile_height": 32,
            "elevation_step": 16,
        },
        headers=_headers("kernel.observe"),
    )
    assert res.status_code == 200
    out = res.json()
    assert out["projection"]["type"] == "isometric_2_5d"
    assert out["drawable_count"] == 3
    assert out["asset_pack"]["atlas_version"] == "atlas_v2"
    assert out["asset_pack"]["material_pack_version"] == "mat_v3"
    ids = [item["drawable_id"] for item in out["drawables"]]
    assert "desk_1" in ids
    assert "lapidus/sector-001:npc_1" in ids
    assert "lapidus/sector-001:mystery_1" in ids
    unknown = next(item for item in out["drawables"] if item["drawable_id"] == "lapidus/sector-001:mystery_1")
    assert unknown["sprite"] == "placeholder://sprite/missing"
    assert unknown["metadata"]["asset_fallback"]["sprite_source"] == "fallback:missing"
    assert out["stats"]["fallback_count"] == 1
    first = out["drawables"][0]
    assert "screen_x" in first
    assert "screen_y" in first
    assert isinstance(first["depth_key"], (int, float))
    app.dependency_overrides.clear()


def test_render_graph_contract_compiles_nodes_with_world_transforms() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)
    now = datetime.now(timezone.utc)

    class _SceneRow:
        id = "scene-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        scene_id = "lapidus/intro"
        name = "Intro"
        description = ""
        content_json = (
            '{"nodes":[{"node_id":"desk_1","kind":"desk","x":4,"y":2,'
            '"metadata":{"z":1,"akinenwun":"TyKoWuVu"}}],"edges":[]}'
        )
        content_hash = "h_scene"
        created_at = now
        updated_at = now

    class _RegionRow:
        id = "region-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        region_key = "lapidus/sector-001"
        payload_json = '{"entities":[{"id":"npc_1","kind":"npc","x":5,"y":3,"z":0}]}'
        payload_hash = "h_region"
        cache_policy = "cache"
        loaded = True
        created_at = now
        updated_at = now

    class _ManifestRow:
        id = "manifest-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "sprite_pack_1"
        name = "Sprites"
        kind = "sprite"
        payload_json = '{"atlas_version":"atlas_v2","desk":"atlas/desk.png","npc":"atlas/npc.png"}'
        payload_hash = "h_manifest"
        created_at = now

    class _MaterialManifestRow:
        id = "manifest-row-2"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "material_pack_1"
        name = "Materials"
        kind = "material"
        payload_json = '{"material_pack_version":"mat_v3","desk":"wood","npc":"cloth"}'
        payload_hash = "h_manifest_material"
        created_at = now

    class _RenderRepo:
        def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> _SceneRow | None:
            if workspace_id == "main" and realm_id == "lapidus" and scene_id == "lapidus/intro":
                return _SceneRow()
            return None

        def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[_RegionRow]:
            if workspace_id != "main":
                return []
            if realm_id is not None and realm_id != "lapidus":
                return []
            return [_RegionRow()]

        def list_asset_manifests(self, workspace_id: str) -> Sequence[_ManifestRow]:
            if workspace_id != "main":
                return []
            return [_ManifestRow(), _MaterialManifestRow()]

    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=_RenderRepo(), kernel=kernel)
    client = TestClient(app)
    res = client.post(
        "/v1/game/renderer/render-graph",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "coordinate_space": "world_right_handed_y_up",
        },
        headers=_headers("kernel.observe"),
    )
    assert res.status_code == 200
    out = res.json()
    assert out["node_count"] == 2
    assert out["coordinate_space"] == "world_right_handed_y_up"
    assert out["asset_pack"]["atlas_version"] == "atlas_v2"
    ids = [item["node_id"] for item in out["nodes"]]
    assert "desk_1" in ids
    assert "lapidus/sector-001:npc_1" in ids
    node = out["nodes"][0]
    assert "position" in node["transform"]
    assert "screen_hint" in node["transform"]
    app.dependency_overrides.clear()


def test_isometric_render_contract_supports_asset_pack_id_pinning() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)
    now = datetime.now(timezone.utc)

    class _SceneRow:
        id = "scene-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        scene_id = "lapidus/intro"
        name = "Intro"
        description = ""
        content_json = '{"nodes":[{"node_id":"desk_1","kind":"desk","x":1,"y":1,"metadata":{"z":0}}],"edges":[]}'
        content_hash = "h_scene"
        created_at = now
        updated_at = now

    class _ManifestA:
        id = "manifest-a"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "sprite_pack_alpha"
        name = "Sprites A"
        kind = "sprite"
        payload_json = '{"asset_pack_id":"pack_alpha","atlas_version":"atlas_vA","desk":"atlas_a/desk.png"}'
        payload_hash = "h_a"
        created_at = now

    class _ManifestB:
        id = "manifest-b"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "sprite_pack_beta"
        name = "Sprites B"
        kind = "sprite"
        payload_json = '{"asset_pack_id":"pack_beta","atlas_version":"atlas_vB","desk":"atlas_b/desk.png"}'
        payload_hash = "h_b"
        created_at = now

    class _MaterialB:
        id = "manifest-bm"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "material_pack_beta"
        name = "Materials B"
        kind = "material"
        payload_json = '{"asset_pack_id":"pack_beta","material_pack_version":"mat_vB","desk":"oak"}'
        payload_hash = "h_bm"
        created_at = now

    class _RenderRepo:
        def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> _SceneRow | None:
            if workspace_id == "main" and realm_id == "lapidus" and scene_id == "lapidus/intro":
                return _SceneRow()
            return None

        def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[object]:
            return []

        def list_asset_manifests(self, workspace_id: str) -> Sequence[object]:
            if workspace_id != "main":
                return []
            return [_ManifestA(), _ManifestB(), _MaterialB()]

    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=_RenderRepo(), kernel=kernel)
    client = TestClient(app)
    res = client.post(
        "/v1/game/renderer/isometric-contract",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "asset_pack_id": "pack_beta",
            "renderer_atlas_versions": ["atlas_vB"],
            "renderer_material_versions": ["mat_vB"],
        },
        headers=_headers("kernel.observe"),
    )
    assert res.status_code == 200
    out = res.json()
    assert out["asset_pack"]["asset_pack_id"] == "pack_beta"
    assert out["asset_pack"]["atlas_version"] == "atlas_vB"
    assert out["asset_pack"]["material_pack_version"] == "mat_vB"
    assert out["drawables"][0]["sprite"] == "atlas_b/desk.png"
    app.dependency_overrides.clear()


def test_isometric_render_contract_strict_assets_and_version_guards_fail_fast() -> None:
    fake = FakeKernelClient()
    kernel = KernelIntegrationService(fake)
    now = datetime.now(timezone.utc)

    class _SceneRow:
        id = "scene-row-1"
        workspace_id = "main"
        realm_id = "lapidus"
        scene_id = "lapidus/intro"
        name = "Intro"
        description = ""
        content_json = '{"nodes":[{"node_id":"mystery_1","kind":"unknown","x":1,"y":1,"metadata":{"z":0}}],"edges":[]}'
        content_hash = "h_scene"
        created_at = now
        updated_at = now

    class _Manifest:
        id = "manifest-1"
        workspace_id = "main"
        realm_id = "lapidus"
        manifest_id = "sprite_pack_1"
        name = "Sprites"
        kind = "sprite"
        payload_json = '{"atlas_version":"atlas_v2","desk":"atlas/desk.png"}'
        payload_hash = "h_manifest"
        created_at = now

    class _RenderRepo:
        def get_scene(self, workspace_id: str, realm_id: str, scene_id: str) -> _SceneRow | None:
            if workspace_id == "main" and realm_id == "lapidus" and scene_id == "lapidus/intro":
                return _SceneRow()
            return None

        def list_world_regions(self, workspace_id: str, realm_id: str | None = None) -> Sequence[object]:
            return []

        def list_asset_manifests(self, workspace_id: str) -> Sequence[object]:
            if workspace_id != "main":
                return []
            return [_Manifest()]

    app.dependency_overrides[_kernel_only_service] = lambda: AtelierService(repo=_RenderRepo(), kernel=kernel)
    client = TestClient(app)

    incompatible = client.post(
        "/v1/game/renderer/isometric-contract",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "renderer_atlas_versions": ["atlas_v1_only"],
        },
        headers=_headers("kernel.observe"),
    )
    assert incompatible.status_code == 400
    assert "incompatible_atlas_version:atlas_v2" in incompatible.json()["detail"]

    strict = client.post(
        "/v1/game/renderer/isometric-contract",
        json={
            "workspace_id": "main",
            "realm_id": "lapidus",
            "scene_id": "lapidus/intro",
            "strict_assets": True,
            "renderer_atlas_versions": ["atlas_v2"],
        },
        headers=_headers("kernel.observe"),
    )
    assert strict.status_code == 400
    assert "missing_sprite_asset" in strict.json()["detail"]
    app.dependency_overrides.clear()
