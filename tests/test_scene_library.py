from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, Tuple
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parent.parent
API_APP_DIR = ROOT / "apps" / "atelier-api"
sys.path.insert(0, str(API_APP_DIR))

from atelier_api.models import Scene  # type: ignore[import]
from atelier_api.services import AtelierService  # type: ignore[import]


class FakeSceneRepo:
    def __init__(self) -> None:
        self.rows: Dict[Tuple[str, str, str], Scene] = {}

    def list_scenes(self, workspace_id: str, realm_id: str | None = None):
        rows = [row for key, row in self.rows.items() if key[0] == workspace_id]
        if realm_id is not None:
            rows = [row for row in rows if row.realm_id == realm_id]
        return rows

    def get_scene(self, workspace_id: str, realm_id: str, scene_id: str):
        return self.rows.get((workspace_id, realm_id, scene_id))

    def create_scene(self, row: Scene):
        if row.id is None:
            row.id = str(uuid4())
        self.rows[(row.workspace_id, row.realm_id, row.scene_id)] = row
        return row

    def save_scene(self, row: Scene):
        if row.id is None:
            row.id = str(uuid4())
        self.rows[(row.workspace_id, row.realm_id, row.scene_id)] = row
        return row


def _service() -> AtelierService:
    return AtelierService(repo=FakeSceneRepo(), kernel=None)


def test_scene_library_create_and_update() -> None:
    svc = _service()
    created = svc.create_scene(
        payload=type(
            "Obj",
            (),
            {
                "workspace_id": "main",
                "realm_id": "lapidus",
                "scene_id": "lapidus/intro",
                "name": "Intro",
                "description": "",
                "content": {"nodes": []},
            },
        )()
    )
    assert created.scene_id == "lapidus/intro"
    assert created.content_hash != ""

    updated = svc.update_scene(
        workspace_id="main",
        realm_id="lapidus",
        scene_id="lapidus/intro",
        payload=type("Obj", (), {"name": "Intro 2", "description": None, "content": {"nodes": [1]}})(),
    )
    assert updated.name == "Intro 2"
    assert updated.content["nodes"] == [1]


def test_scene_library_rejects_mismatched_scene_id() -> None:
    svc = _service()
    with pytest.raises(ValueError):
        svc.create_scene(
            payload=type(
                "Obj",
                (),
                {
                    "workspace_id": "main",
                    "realm_id": "lapidus",
                    "scene_id": "intro",
                    "name": "Bad",
                    "description": "",
                    "content": {},
                },
            )()
        )


def test_scene_library_compile_from_cobra() -> None:
    svc = _service()
    compiled = svc.create_scene_from_cobra(
        payload=type(
            "Obj",
            (),
            {
                "workspace_id": "main",
                "realm_id": "lapidus",
                "scene_id": "lapidus/intro",
                "name": "Intro",
                "description": "",
                "cobra_source": "entity demo 1 2 marker\n  lex TyKoWuVu",
            },
        )()
    )
    assert compiled.scene_id == "lapidus/intro"
    assert isinstance(compiled.content.get("nodes"), list)
