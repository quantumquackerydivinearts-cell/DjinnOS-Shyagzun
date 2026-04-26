#!/usr/bin/env python3
"""
Generate the Supra Librix tile grid.

Produces a JSON file consumed by the SupraLibrixPanel React component.

Output
------
  apps/atelier-api/static/supra_librix_tiles.json

  {
    "resolution": 1,           -- degrees per tile
    "width": 360,              -- number of longitude tiles
    "height": 180,             -- number of latitude tiles
    "tiles": [0.0, 0.73, ...]  -- row-major flat array, 0=water/white, 1=inland/black
  }

  Tile index i:
    xi  = i % width              (0 = lon -180)
    yi  = i // width             (0 = lat  +90)
    lon = -180 + (xi + 0.5)      (tile centre)
    lat =   90 - (yi + 0.5)      (tile centre)

Dependencies (standalone — not in API requirements)
----------------------------------------------------
  pip install numpy geopandas shapely

For admin-1 (states/provinces) support:
  pip install geodatasets
"""

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

try:
    import geopandas as gpd
    try:
        from shapely import contains_xy as _shp_contains  # shapely >= 2.0
    except ImportError:
        from shapely.vectorized import contains as _shp_contains  # shapely < 2.0
except ImportError:
    print("ERROR: pip install numpy geopandas shapely geodatasets", file=sys.stderr)
    sys.exit(1)

RESOLUTION = 1
WIDTH      = 360 // RESOLUTION
HEIGHT     = 180 // RESOLUTION

OUT_PATH = (
    Path(__file__).parent.parent
    / "apps" / "atelier-api" / "static" / "supra_librix_tiles.json"
)


# ── Land mask ─────────────────────────────────────────────────────────────────

def _load_land_geometry():
    """Load land polygon union from the best available source."""
    try:
        import geodatasets
        gdf = gpd.read_file(geodatasets.get_path("naturalearth.land"))
        print("  source: geodatasets naturalearth.land")
    except Exception:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gdf = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        print("  source: geopandas built-in naturalearth_lowres (50m, no admin-1)")

    union_fn = getattr(gdf.geometry, "union_all", None) or gdf.geometry.unary_union
    return union_fn() if callable(union_fn) else union_fn


def build_land_mask(land_geom) -> np.ndarray:
    """
    Bool array [HEIGHT, WIDTH], True = land.
    Uses shapely vectorised point-in-polygon for speed.
    """
    res = RESOLUTION
    lons = np.arange(-180 + res / 2, 180, res, dtype=np.float64)
    lats = np.arange( 90  - res / 2, -90, -res, dtype=np.float64)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    flat = _shp_contains(land_geom, lon_grid.ravel(), lat_grid.ravel())
    return flat.reshape(HEIGHT, WIDTH)


# ── Distance from shore ───────────────────────────────────────────────────────

def bfs_distance(land_mask: np.ndarray) -> np.ndarray:
    """
    For every land tile return its BFS step-distance to the nearest water tile,
    normalised to 0–1.  Water tiles return 0.

    Longitude wraps (x=0 is adjacent to x=WIDTH-1).
    Latitude does not wrap.
    """
    h, w = land_mask.shape

    # dist: -1 = unvisited land, 0 = water
    dist = np.where(land_mask, -1, 0).astype(np.int32)

    # Find coastal land tiles using a vectorised neighbourhood check.
    # Pad longitude with wrap, latitude with constant False (no land beyond poles).
    left  = land_mask[:, -1:]
    right = land_mask[:,  :1]
    wide  = np.hstack([left, land_mask, right])          # w+2 cols
    padded = np.pad(wide, ((1, 1), (0, 0)),
                    mode="constant", constant_values=False)  # h+2 rows

    is_coast = land_mask & (
        ~padded[:-2, 1:-1] |   # north
        ~padded[2:,  1:-1] |   # south
        ~padded[1:-1, :-2] |   # west (with wrap)
        ~padded[1:-1,  2:]     # east (with wrap)
    )

    queue: deque = deque()
    ys, xs = np.where(is_coast)
    for y, x in zip(ys.tolist(), xs.tolist()):
        dist[y, x] = 1
        queue.append((y, x))

    # BFS
    while queue:
        y, x = queue.popleft()
        d = dist[y, x]
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny = y + dy
            nx = (x + dx) % w
            if 0 <= ny < h and dist[ny, nx] == -1:
                dist[ny, nx] = d + 1
                queue.append((ny, nx))

    # Normalise
    land_vals = dist[land_mask]
    max_d = int(land_vals.max()) if land_vals.size else 1
    result = np.where(land_mask, dist / max_d, 0.0).astype(np.float32)
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Loading land geometry...")
    land_geom = _load_land_geometry()

    print("Building land mask...")
    land_mask = build_land_mask(land_geom)
    land_pct  = 100 * land_mask.sum() / land_mask.size
    print(f"  {land_mask.sum()} land tiles / {land_mask.size} total ({land_pct:.1f}% land)")

    print("Computing distance-from-shore (BFS)...")
    dist_grid = bfs_distance(land_mask)

    tiles = [round(float(v), 3) for v in dist_grid.ravel()]

    data = {
        "resolution": RESOLUTION,
        "width":      WIDTH,
        "height":     HEIGHT,
        "tiles":      tiles,
    }

    OUT_PATH.write_text(
        json.dumps(data, separators=(",", ":")),
        encoding="utf-8",
    )
    kb = OUT_PATH.stat().st_size / 1024
    print(f"Written {len(tiles)} tiles -> {OUT_PATH}  ({kb:.0f} KB)")


if __name__ == "__main__":
    main()