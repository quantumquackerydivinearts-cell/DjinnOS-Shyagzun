"""
atelier_api/routers/export.py
============================
Game data export endpoints — packages registry and portrait assets for
consumption by the Ambroflow Engine (or any other runtime).

Endpoints
---------
POST /v1/export/registry/{game_slug}
    Store or update a game registry blob (characters, quests, items, objects).
    The Atelier desktop sends this after reading game7Registry.js.

GET  /v1/export/registry/{game_slug}
    Retrieve the stored registry for a game.

PUT  /v1/export/portrait/{char_id}
    Upload a PNG portrait for a specific character ID.
    Accepts multipart/form-data with a ``file`` field.

GET  /v1/export/portrait/{char_id}
    Retrieve the portrait PNG for a character.

GET  /v1/export/bundle/{game_slug}
    Full export bundle: registry JSON + index of available portrait IDs.
    Ambroflow uses this to bootstrap a GameDataBundle.

Storage
-------
Registry files: files/exports/{game_slug}/registry.json
Portrait files: files/exports/{game_slug}/portraits/{char_id}.png

Both are committed to the repo as Atelier authoring output.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse, Response

router = APIRouter(prefix="/v1/export", tags=["export"])

# Resolve storage root relative to this file so it works regardless of CWD.
_STORAGE_ROOT = Path(__file__).parent.parent / "files" / "exports"


def _registry_path(game_slug: str) -> Path:
    return _STORAGE_ROOT / game_slug / "registry.json"


def _portrait_path(game_slug: str, char_id: str) -> Path:
    # char_id may contain /, _, etc. — sanitise to a safe filename.
    safe = char_id.replace("/", "_").replace("..", "_")
    return _STORAGE_ROOT / game_slug / "portraits" / f"{safe}.png"


def _slug_from_char_id(char_id: str) -> str:
    """
    Infer game slug from a char_id like '0006_WTCH' or '2001_VDWR'.
    Returns '' if no slug can be inferred (caller must supply it separately).
    """
    return ""


# ── Registry ──────────────────────────────────────────────────────────────────

@router.post(
    "/registry/{game_slug}",
    summary="Store or update the game registry for a slug",
    status_code=status.HTTP_200_OK,
)
async def store_registry(game_slug: str, body: dict[str, Any]) -> ORJSONResponse:
    """
    Receive the full game registry from the Atelier desktop and persist it.

    Body schema (all fields optional — store whatever the desktop sends):
    {
        "characters": [...],
        "quests":     [...],
        "items":      [...],
        "objects":    [...]
    }
    """
    path = _registry_path(game_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    return ORJSONResponse({"ok": True, "game_slug": game_slug, "path": str(path)})


@router.get(
    "/registry/{game_slug}",
    summary="Retrieve the stored game registry for a slug",
)
async def get_registry(game_slug: str) -> ORJSONResponse:
    path = _registry_path(game_slug)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registry found for {game_slug!r}. "
                   f"POST to /v1/export/registry/{game_slug} first.",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return ORJSONResponse({"ok": True, "game_slug": game_slug, "registry": data})


# ── Portraits ─────────────────────────────────────────────────────────────────

@router.put(
    "/portrait/{game_slug}/{char_id}",
    summary="Upload a PNG portrait for a character",
    status_code=status.HTTP_200_OK,
)
async def upload_portrait(
    game_slug: str,
    char_id:   str,
    file:      UploadFile = File(...),
) -> ORJSONResponse:
    """
    Store a PNG portrait for the given character ID within a game.

    The Atelier desktop sends this after constructing the portrait in Render Lab.
    Accepts image/png. Overwrites any existing portrait for this character.
    """
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Portrait must be a PNG, JPEG, or WebP image.",
        )

    data = await file.read()
    if len(data) > 4 * 1024 * 1024:  # 4 MB cap
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Portrait file exceeds 4 MB limit.",
        )

    path = _portrait_path(game_slug, char_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    return ORJSONResponse({
        "ok":       True,
        "game_slug": game_slug,
        "char_id":  char_id,
        "bytes":    len(data),
    })


@router.get(
    "/portrait/{game_slug}/{char_id}",
    summary="Retrieve a character portrait PNG",
    responses={200: {"content": {"image/png": {}}}},
)
async def get_portrait(game_slug: str, char_id: str) -> Response:
    path = _portrait_path(game_slug, char_id)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No portrait found for {char_id!r} in {game_slug!r}.",
        )
    return Response(content=path.read_bytes(), media_type="image/png")


# ── Bundle ────────────────────────────────────────────────────────────────────

@router.get(
    "/bundle/{game_slug}",
    summary="Full export bundle: registry + portrait manifest",
)
async def get_bundle(game_slug: str) -> ORJSONResponse:
    """
    Returns the complete export bundle for Ambroflow to load.

    {
        "ok":        true,
        "game_slug": "7_KLGS",
        "registry":  { characters, quests, items, objects },
        "portraits": ["0006_WTCH", "0019_ROYL", ...]   // IDs with stored portraits
    }

    Ambroflow fetches individual portraits via GET /v1/export/portrait/{game_slug}/{char_id}.
    """
    path = _registry_path(game_slug)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registry found for {game_slug!r}.",
        )

    registry = json.loads(path.read_text(encoding="utf-8"))

    # Collect portrait IDs that have been uploaded
    portrait_dir = _STORAGE_ROOT / game_slug / "portraits"
    portrait_ids: list[str] = []
    if portrait_dir.exists():
        for p in portrait_dir.glob("*.png"):
            portrait_ids.append(p.stem)

    return ORJSONResponse({
        "ok":        True,
        "game_slug": game_slug,
        "registry":  registry,
        "portraits": sorted(portrait_ids),
    })
