"""
Render Lab router package.

Sub-modules:
  projects      — project CRUD (create, list, get, archive)
  pipeline      — pipeline stage execution (compile → validate → stream → prefetch → budget_check → go_no_go → layer_project)
  arch_diagram  — architecture diagram parse, export, SVG generation, script persistence, and defaults
  readiness     — project readiness and federation health checks
  tile_scripts  — tile generator scripts: hardcoded defaults (ring_bloom, maze_carve, …) and user-saved scripts
  voxel_ingest  — tile → voxel bridge: POST /projects/{id}/ingest converts tile script output to voxel scene source JSON and links it to the pipeline
  dungeon_export — Atelier tile layout → Ambroflow DungeonLayout export and validation
"""
from fastapi import APIRouter

from . import arch_diagram, dungeon_export, pipeline, projects, readiness, tile_scripts, voxel_ingest

router = APIRouter(prefix="/v1/render_lab", tags=["render_lab"])

router.include_router(projects.router)
router.include_router(pipeline.router)
router.include_router(arch_diagram.router)
router.include_router(readiness.router)
router.include_router(tile_scripts.router)
router.include_router(dungeon_export.router)
router.include_router(voxel_ingest.router)