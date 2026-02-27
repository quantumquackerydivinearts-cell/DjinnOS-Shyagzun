from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, Tuple
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(API_APP_DIR))

from atelier_api.models import Realm, WorldRegion  # type: ignore[import]
from atelier_api.services import AtelierService  # type: ignore[import]
from qqva.world_stream import WorldStreamController


class FakeWorldRegionRepo:
    def __init__(self) -> None:
        self.realms: Dict[str, Realm] = {}
        self.rows: Dict[Tuple[str, str, str], WorldRegion] = {}

    def add_realm(self, slug: str) -> None:
        self.realms[slug] = Realm(id=str(uuid4()), slug=slug, name=slug.title(), description="", created_at=datetime.utcnow())

    def get_realm_by_slug(self, slug: str) -> Realm | None:
        return self.realms.get(slug)

    def list_world_regions(self, workspace_id: str, realm_id: str | None = None):
        rows = [row for key, row in self.rows.items() if key[0] == workspace_id]
        if realm_id is not None:
            rows = [row for row in rows if row.realm_id == realm_id]
        return rows

    def get_world_region(self, workspace_id: str, realm_id: str, region_key: str) -> WorldRegion | None:
        return self.rows.get((workspace_id, realm_id, region_key))

    def create_world_region(self, row: WorldRegion) -> WorldRegion:
        if row.id is None:
            row.id = str(uuid4())
        self.rows[(row.workspace_id, row.realm_id, row.region_key)] = row
        return row

    def save_world_region(self, row: WorldRegion) -> WorldRegion:
        if row.id is None:
            row.id = str(uuid4())
        self.rows[(row.workspace_id, row.realm_id, row.region_key)] = row
        return row


def _service(max_loaded_regions: int = 2) -> tuple[AtelierService, FakeWorldRegionRepo]:
    repo = FakeWorldRegionRepo()
    repo.add_realm("lapidus")
    svc = AtelierService(
        repo=repo,
        kernel=None,
        world_stream=WorldStreamController(max_loaded_regions=max_loaded_regions),
    )
    return svc, repo


def test_world_region_service_evicts_oldest_non_pinned() -> None:
    svc, repo = _service(max_loaded_regions=2)
    for key, policy in [
        ("lapidus/pinned", "pin"),
        ("lapidus/cache", "cache"),
        ("lapidus/stream", "stream"),
    ]:
        svc.load_world_region(
            payload=type(
                "Obj",
                (),
                {
                    "workspace_id": "main",
                    "realm_id": "lapidus",
                    "region_key": key,
                    "payload": {"k": key},
                    "cache_policy": policy,
                },
            )()
        )

    rows = repo.list_world_regions("main", "lapidus")
    loaded_keys = sorted(row.region_key for row in rows if row.loaded)
    assert loaded_keys == ["lapidus/pinned", "lapidus/stream"]


def test_world_region_service_load_is_deterministic_for_same_payload() -> None:
    svc, _ = _service(max_loaded_regions=4)
    payload_obj = type(
        "Obj",
        (),
        {
            "workspace_id": "main",
            "realm_id": "lapidus",
            "region_key": "lapidus/sector-001",
            "payload": {"tiles": [1, 2, 3]},
            "cache_policy": "cache",
        },
    )()
    first = svc.load_world_region(payload=payload_obj)
    second = svc.load_world_region(payload=payload_obj)
    assert first.payload_hash == second.payload_hash
    assert first.region_key == second.region_key
    assert second.loaded is True


def test_world_region_service_status_reports_occupancy_and_policy_counts() -> None:
    svc, _ = _service(max_loaded_regions=3)
    for key, policy in [
        ("lapidus/p1", "pin"),
        ("lapidus/c1", "cache"),
    ]:
        svc.load_world_region(
            payload=type(
                "Obj",
                (),
                {
                    "workspace_id": "main",
                    "realm_id": "lapidus",
                    "region_key": key,
                    "payload": {},
                    "cache_policy": policy,
                },
            )()
        )

    status = svc.world_stream_status(workspace_id="main", realm_id="lapidus")
    assert status.loaded_count == 2
    assert status.capacity == 3
    assert status.policy_counts["pin"] == 1
    assert status.policy_counts["cache"] == 1
    assert status.policy_counts["stream"] == 0
    assert status.pressure_components["stream_occupancy"] == status.pressure
    assert status.pressure_components["demon_total"] == 0.0
    assert status.demon_pressures["lucifer"] == 0.0
