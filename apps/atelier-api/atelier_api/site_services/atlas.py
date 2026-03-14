"""
atelier_api/services/atlas.py
Server-side atlas creation from uploaded PNG tiles.
Wand keys and sensitive material never touch this service.
"""
from __future__ import annotations

import base64
import io
import math
from typing import Any
from uuid import uuid4

from PIL import Image

from ..core.config import get_settings

settings = get_settings()


def create_atlas_from_png_bytes(
    png_bytes: bytes,
    tile_size: int = 24,
    padding: int = 0,
) -> dict[str, Any]:
    """
    Given raw PNG bytes, infer atlas dimensions and return atlas metadata
    + a base64 data URL safe to return to the client.
    The PNG is NOT stored server-side unless you add persistence below.
    """
    if len(png_bytes) > settings.atlas_max_upload_bytes:
        raise ValueError(
            f"PNG exceeds max size {settings.atlas_max_upload_bytes // (1024*1024)} MB"
        )

    image = Image.open(io.BytesIO(png_bytes))
    width_px, height_px = image.size

    if width_px > settings.atlas_max_dimension_px or height_px > settings.atlas_max_dimension_px:
        raise ValueError(
            f"PNG dimensions {width_px}×{height_px} exceed max "
            f"{settings.atlas_max_dimension_px}px"
        )

    effective_tile = tile_size + padding * 2
    cols = max(1, math.floor(width_px  / effective_tile))
    rows = max(1, math.floor(height_px / effective_tile))

    # Re-encode as PNG data URL for the client
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    data_url = f"data:image/png;base64,{b64}"

    atlas_id = f"atlas_{uuid4().hex[:12]}"

    return {
        "ok":         True,
        "atlas_id":   atlas_id,
        "cols":       cols,
        "rows":       rows,
        "tile_size":  tile_size,
        "width_px":   width_px,
        "height_px":  height_px,
        "src_data_url": data_url,
    }


def apply_sprite_animator(
    renderer_json: dict[str, Any],
    target_entity_id: str,
    atlas_id: str,
    frame_w: int = 32,
    frame_h: int = 32,
    start_col: int = 0,
    idle_row_start: int = 0,
    walk_row_start: int = 1,
    idle_frames: int = 4,
    walk_frames: int = 8,
) -> dict[str, Any]:
    """
    Inject directional animation frame maps into the target entity
    in the renderer JSON. Returns the modified renderer_json dict.
    """
    FACING_ROWS = {"south": 0, "west": 1, "east": 2, "north": 3}

    def build_frame_set(base_row: int, count: int) -> dict[str, list[dict[str, Any]]]:
        return {
            facing: [
                {
                    "atlas": atlas_id,
                    "col":   start_col + i,
                    "row":   base_row + row_offset,
                    "w":     frame_w,
                    "h":     frame_h,
                    "ms":    120,
                }
                for i in range(count)
            ]
            for facing, row_offset in FACING_ROWS.items()
        }

    animation_spec = {
        "atlas":   atlas_id,
        "frame_w": frame_w,
        "frame_h": frame_h,
        "idle":    build_frame_set(idle_row_start, idle_frames),
        "walk":    build_frame_set(walk_row_start, walk_frames),
    }

    matched = False
    result = dict(renderer_json)

    def inject(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
        nonlocal matched
        out = []
        found = False
        for item in items:
            if isinstance(item, dict) and str(item.get("id", "")) == target_entity_id:
                out.append({**item, "animation": animation_spec})
                found = True
                matched = True
            else:
                out.append(item)
        return out, found

    if "voxels" in result and isinstance(result["voxels"], list):
        result["voxels"], _ = inject(result["voxels"])

    if "entities" in result and isinstance(result["entities"], list):
        result["entities"], _ = inject(result["entities"])

    if not matched:
        raise ValueError(f"Entity '{target_entity_id}' not found in renderer JSON")

    return result
