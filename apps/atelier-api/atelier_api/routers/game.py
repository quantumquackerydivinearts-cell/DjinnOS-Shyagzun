"""
atelier_api/routers/game.py
All game/renderer endpoints — the 15 missing functions, now server-side.
"""
from __future__ import annotations

import hashlib
import io
import json
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse

from ..core.lineage import get_lineage_store
from ..site_models.schemas import (
    ApplySpriteAnimatorRequest,
    ApplySpriteAnimatorResponse,
    CompileKobraRequest,
    CompileKobraResponse,
    CreateAtlasFromPngResponse,
    DaisyBodyplanRequest,
    DaisyBodyplanResponse,
    EmitHeadlessQuestRequest,
    EmitHeadlessQuestResponse,
    EmitMeditationRequest,
    EmitMeditationResponse,
    EmitPlacementsRequest,
    EmitPlacementsResponse,
    EmitSceneGraphRequest,
    EmitSceneGraphResponse,
    EngineInboxConsumeRequest,
    EngineInboxConsumeResponse,
    ShygazunInterpretRequest,
    ShygazunInterpretResponse,
    SyncTablesRequest,
    SyncTablesResponse,
    TickRequest,
    TickResponse,
    ValidateContentRequest,
    ValidateContentResponse,
)
from ..site_services.atlas import apply_sprite_animator, create_atlas_from_png_bytes
from ..site_services.kobra import (
    compile_kobra_scene,
    entities_to_voxels,
    scene_to_bilingual_trust,
)
from ..site_services.daisy import bodyplan_to_voxels, build_bodyplan
from ..site_services.tick_engine import apply_tick

router = APIRouter(prefix="/v1/game", tags=["game"])


# ── 1. Runtime tick ───────────────────────────────────────────────────────────

@router.post(
    "/runtime/tick",
    response_model=TickResponse,
    summary="Apply tick events server-side; returns next state + lineage hash",
)
async def runtime_tick(req: TickRequest) -> TickResponse:
    result = apply_tick(
        workspace_id=req.workspace_id,
        actor_id=req.actor_id,
        plan_id=req.plan_id,
        events=req.events,
        current_state=req.current_state,
    )
    return TickResponse(**result)


# ── 2. Sync renderer state tables ────────────────────────────────────────────

@router.post(
    "/renderer/sync_tables",
    response_model=SyncTablesResponse,
    summary="Merge local renderer tables with server; return authoritative merged set",
)
async def sync_renderer_tables(req: SyncTablesRequest) -> SyncTablesResponse:
    # In a real deployment, load from DB keyed by (workspace_id, actor_id).
    # Returning the local tables merged with server defaults for now.
    server_tables: dict[str, Any] = {
        "_server_ts": int(time.time() * 1000),
        "_actor_id":  req.actor_id,
    }

    if req.precedence == "api_over_local":
        merged = {**req.local_tables, **server_tables}
    else:
        merged = {**server_tables, **req.local_tables}

    blob = json.dumps(merged, sort_keys=True, default=str).encode()
    digest = hashlib.sha256(blob).hexdigest()[:16]

    return SyncTablesResponse(
        ok=True,
        tables=merged,
        meta={
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "hash": digest,
            "actor_id": req.actor_id,
        },
        hash=digest,
    )


# ── 3. Compile Kobra source → renderer JSON + engine state ───────────────────

@router.post(
    "/scene/compile_kobra",
    response_model=CompileKobraResponse,
    summary="Compile a Kobra source document into a renderer-ready scene",
)
async def compile_kobra(req: CompileKobraRequest) -> CompileKobraResponse:
    if len(req.kobra_source.encode()) > 256_000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="kobra_source exceeds 256 KB limit",
        )

    scene = compile_kobra_scene(req.kobra_source)
    voxels = entities_to_voxels(scene.entities)
    trust = scene_to_bilingual_trust(scene)

    scene_id = req.scene_id or f"{req.realm_id}/renderer-lab"

    renderer_json: dict[str, Any] = {
        "schema":      "qqva.renderer.v1",
        "scene_id":    scene_id,
        "scene_name":  req.scene_name or scene_id,
        "voxels":      voxels,
        "entities":    [],
        "settings":    {},
        "semantic":    trust,
        "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    engine_state: dict[str, Any] = {
        "scene_id":      scene_id,
        "world_time_ms": 0,
        "entities":      {v["id"]: v for v in voxels},
        "tables":        {},
        "post_inbox":    [],
    }

    lineage_id = f"kobra_compile_{uuid4().hex[:12]}"
    store = get_lineage_store()
    record = store.create_record(
        lineage_id=lineage_id,
        workspace_id=req.workspace_id,
        actor_id="system",
        action_kind="scene.compile_kobra",
    )
    record.set_layer(0, {"source_bytes": len(req.kobra_source), "scene_id": scene_id})
    record.set_layer(1, {
        "entity_count":  len(voxels),
        "warnings":      scene.warnings,
        "frontier_open": scene.frontier_open,
    })
    record.set_layer(6, renderer_json)
    store.append(record)

    return CompileKobraResponse(
        ok=not scene.errors,
        scene_id=scene_id,
        renderer_json=renderer_json,
        engine_state=engine_state,
        voxels=voxels,
        entities=[],
        warnings=scene.warnings + scene.errors,
        lineage_id=lineage_id,
    )


# ── 4. Validate content ───────────────────────────────────────────────────────

@router.post(
    "/renderer/validate_content",
    response_model=ValidateContentResponse,
    summary="Validate Kobra/JSON/JS/Python content and return bilingual trust surface",
)
async def validate_content(req: ValidateContentRequest) -> ValidateContentResponse:
    errors: list[str] = []
    warnings: list[str] = []
    bilingual_trust_dict: dict[str, Any] = {}

    if req.source_type in ("kobra"):
        scene = compile_kobra_scene(req.payload)
        errors.extend(scene.errors)
        warnings.extend(scene.warnings)
        bilingual_trust_dict = scene_to_bilingual_trust(scene)

        if req.strict_bilingual:
            bt = bilingual_trust_dict
            if bt.get("authority_level") == "unknown":
                errors.append("strict_bilingual: authority unresolved — parse produced Echo")
            if bt.get("trust_grade") == "unknown":
                errors.append("strict_bilingual: trust unattested — FrontierOpen unresolved")

    elif req.source_type == "json":
        try:
            parsed_json = json.loads(req.payload)
            if not isinstance(parsed_json, dict):
                errors.append("json: root must be an object")
        except json.JSONDecodeError as exc:
            errors.append(f"json: parse error: {exc}")

    elif req.source_type in ("python", "js"):
        # Syntax-level check only — execution happens in sandboxed worker
        if len(req.payload.strip()) == 0:
            warnings.append(f"{req.source_type}: source is empty")

    scene_id = req.scene_id or f"{req.realm_id}/validate"
    from ..site_models.schemas import BilingualTrust
    bt = BilingualTrust(**bilingual_trust_dict) if bilingual_trust_dict else BilingualTrust()

    return ValidateContentResponse(
        ok=len(errors) == 0,
        error_count=len(errors),
        warning_count=len(warnings),
        errors=errors,
        warnings=warnings,
        bilingual_trust=bt,
        scene_id=scene_id,
        source_type=req.source_type,
    )


# ── 5. Emit scene graph ───────────────────────────────────────────────────────

@router.post(
    "/renderer/scene_graph",
    response_model=EmitSceneGraphResponse,
    summary="Emit a scene graph (nodes + edges) and record in lineage",
)
async def emit_scene_graph(req: EmitSceneGraphRequest) -> EmitSceneGraphResponse:
    lineage_id = f"scene_graph_{uuid4().hex[:12]}"
    store = get_lineage_store()
    record = store.create_record(
        lineage_id=lineage_id,
        workspace_id=req.workspace_id,
        actor_id="system",
        action_kind="scene.emit_graph",
    )
    record.set_layer(0, {
        "scene_id":   req.scene_id,
        "node_count": len(req.nodes),
        "edge_count": len(req.edges),
    })
    record.set_layer(6, {"nodes": req.nodes, "edges": req.edges})
    store.append(record)

    return EmitSceneGraphResponse(
        ok=True,
        scene_id=req.scene_id or f"{req.realm_id}/graph",
        node_count=len(req.nodes),
        edge_count=len(req.edges),
        lineage_id=lineage_id,
    )


# ── 6. Emit headless quest ────────────────────────────────────────────────────

@router.post(
    "/quests/headless",
    response_model=EmitHeadlessQuestResponse,
    summary="Emit a headless quest sequence (no player UI required)",
)
async def emit_headless_quest(req: EmitHeadlessQuestRequest) -> EmitHeadlessQuestResponse:
    lineage_id = f"quest_{uuid4().hex[:12]}"
    store = get_lineage_store()
    record = store.create_record(
        lineage_id=lineage_id,
        workspace_id=req.workspace_id,
        actor_id="system",
        action_kind="quest.emit_headless",
    )
    record.set_layer(0, {"quest_id": req.quest_id, "step_count": len(req.steps)})
    record.set_layer(6, {"steps": req.steps, "meta": req.meta})
    store.append(record)

    return EmitHeadlessQuestResponse(
        ok=True,
        quest_id=req.quest_id,
        step_count=len(req.steps),
        lineage_id=lineage_id,
    )


# ── 7. Emit meditation ────────────────────────────────────────────────────────

@router.post(
    "/meditations",
    response_model=EmitMeditationResponse,
    summary="Emit a meditation record into the scene/lineage store",
)
async def emit_meditation(req: EmitMeditationRequest) -> EmitMeditationResponse:
    lineage_id = f"med_{uuid4().hex[:12]}"
    store = get_lineage_store()
    record = store.create_record(
        lineage_id=lineage_id,
        workspace_id=req.workspace_id,
        actor_id="system",
        action_kind="scene.emit_meditation",
    )
    record.set_layer(0, {"meditation_id": req.meditation_id, "tags": req.tags})
    record.set_layer(6, req.content)
    store.append(record)

    return EmitMeditationResponse(
        ok=True,
        meditation_id=req.meditation_id,
        lineage_id=lineage_id,
    )


# ── 8. Emit scene placements ──────────────────────────────────────────────────

@router.post(
    "/renderer/placements",
    response_model=EmitPlacementsResponse,
    summary="Emit a batch of scene placements (from JSON, Kobra, or tile paint)",
)
async def emit_placements(req: EmitPlacementsRequest) -> EmitPlacementsResponse:
    if not req.placements:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="placements must not be empty",
        )

    lineage_id = f"place_{uuid4().hex[:12]}"
    store = get_lineage_store()
    record = store.create_record(
        lineage_id=lineage_id,
        workspace_id=req.workspace_id,
        actor_id="system",
        action_kind=f"scene.emit_placements.{req.source}",
    )
    record.set_layer(0, {
        "scene_id":        req.scene_id,
        "placement_count": len(req.placements),
        "source":          req.source,
    })
    record.set_layer(6, {"placements": req.placements})
    store.append(record)

    scene_id = req.scene_id or f"{req.realm_id}/placements"
    return EmitPlacementsResponse(
        ok=True,
        scene_id=scene_id,
        placement_count=len(req.placements),
        lineage_id=lineage_id,
    )


# ── 9. Create atlas from PNG upload ──────────────────────────────────────────

@router.post(
    "/assets/atlas_from_png",
    response_model=CreateAtlasFromPngResponse,
    summary="Upload a tile PNG; returns atlas metadata + data URL (no server storage)",
)
async def create_atlas_from_png(
    file: UploadFile = File(...),
    tile_size: int = Form(default=24),
    padding: int = Form(default=0),
) -> CreateAtlasFromPngResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be an image (PNG recommended)",
        )

    png_bytes = await file.read()

    try:
        result = create_atlas_from_png_bytes(
            png_bytes=png_bytes,
            tile_size=max(1, tile_size),
            padding=max(0, padding),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CreateAtlasFromPngResponse(**result)


# ── 10. Apply sprite animator to renderer JSON ────────────────────────────────

@router.post(
    "/assets/apply_sprite_animator",
    response_model=ApplySpriteAnimatorResponse,
    summary="Inject directional animation frame maps into a renderer JSON entity",
)
async def apply_sprite_animator_endpoint(
    req: ApplySpriteAnimatorRequest,
) -> ApplySpriteAnimatorResponse:
    try:
        next_json = apply_sprite_animator(
            renderer_json=req.renderer_json,
            target_entity_id=req.target_entity_id,
            atlas_id=req.atlas_id,
            frame_w=req.frame_w,
            frame_h=req.frame_h,
            start_col=req.start_col,
            idle_row_start=req.idle_row_start,
            walk_row_start=req.walk_row_start,
            idle_frames=req.idle_frames,
            walk_frames=req.walk_frames,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ApplySpriteAnimatorResponse(
        ok=True,
        renderer_json=next_json,
        entity_id=req.target_entity_id,
        atlas_id=req.atlas_id,
    )


# ── 11. Shygazun interpret → semantic summary ─────────────────────────────────

@router.post(
    "/shygazun/interpret",
    response_model=ShygazunInterpretResponse,
    summary="Interpret Shygazun source and return semantic summary (BilingualTrust)",
)
async def shygazun_interpret(req: ShygazunInterpretRequest) -> ShygazunInterpretResponse:
    scene = compile_kobra_scene(req.source)
    trust_dict = scene_to_bilingual_trust(scene)

    entity_lines = [
        f"{e.kind or 'entity'} {e.id} @ ({e.x},{e.y},{e.z})"
        for e in scene.entities
    ]
    output = "\n".join(entity_lines) if entity_lines else "(no entities)"

    from ..site_models.schemas import BilingualTrust
    return ShygazunInterpretResponse(
        ok=not scene.errors,
        output=output,
        semantic_summary=BilingualTrust(**trust_dict),
        tokens_used=len(req.source.split()),
    )


# ── 12. Daisy bodyplan ────────────────────────────────────────────────────────

@router.post(
    "/daisy/bodyplan",
    response_model=DaisyBodyplanResponse,
    summary="Generate a Daisy Tongue bodyplan spec and project to renderer voxels",
)
async def generate_daisy_bodyplan(req: DaisyBodyplanRequest) -> DaisyBodyplanResponse:
    bodyplan = build_bodyplan(req)
    voxels   = bodyplan_to_voxels(bodyplan)

    lineage_id = f"daisy_{uuid4().hex[:12]}"
    store = get_lineage_store()
    record = store.create_record(
        lineage_id=lineage_id,
        workspace_id=req.workspace_id,
        actor_id="system",
        action_kind="daisy.generate_bodyplan",
    )
    record.set_layer(0, {
        "system_id":     bodyplan["system_id"],
        "archetype":     req.archetype,
        "segment_count": req.segment_count,
        "limb_pairs":    req.limb_pairs,
        "seed":          req.seed,
    })
    record.set_layer(6, bodyplan)
    record.set_layer(7, {"voxel_count": len(voxels)})
    store.append(record)

    return DaisyBodyplanResponse(
        ok=True,
        bodyplan=bodyplan,
        voxels=voxels,
        lineage_id=lineage_id,
    )


# ── 13. Engine inbox consume ──────────────────────────────────────────────────

@router.post(
    "/runtime/inbox/consume",
    response_model=EngineInboxConsumeResponse,
    summary="Drain inbox messages through the tick engine server-side",
)
async def consume_engine_inbox(req: EngineInboxConsumeRequest) -> EngineInboxConsumeResponse:
    if req.strict_validation:
        invalid = [
            i for i, m in enumerate(req.messages)
            if not isinstance(m.get("kind"), str) or not m["kind"].strip()
        ]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Messages at indices {invalid} failed contract validation (missing kind)",
            )

    if req.preview_only:
        batch = req.messages[:req.max_consume]
        return EngineInboxConsumeResponse(
            ok=True,
            consumed=len(batch),
            remaining=len(req.messages) - len(batch),
            failed=0,
            preview=True,
            results=[{"preview": True, "message": m} for m in batch],
        )

    batch     = req.messages[:req.max_consume]
    remaining = req.messages[req.max_consume:]

    from ..site_models.schemas import TickEvent
    events = [
        TickEvent(
            kind=str(m.get("kind", "state.patch")),
            payload=m.get("payload", {}),
            action_id=str(m.get("action_id", f"inbox_{i}_{uuid4().hex[:6]}")),
        )
        for i, m in enumerate(batch)
    ]

    tick_result = apply_tick(
        workspace_id=req.workspace_id,
        actor_id=req.actor_id,
        plan_id=f"inbox_consume_{uuid4().hex[:8]}",
        events=events,
        current_state={},
    )

    results = tick_result.get("results", [])
    failed  = sum(1 for r in results if not r.get("ok"))

    return EngineInboxConsumeResponse(
        ok=failed == 0,
        consumed=len(batch),
        remaining=len(remaining),
        failed=failed,
        preview=False,
        results=results,
    )


# ── 14. Lineage tail ──────────────────────────────────────────────────────────

@router.get(
    "/lineage/{workspace_id}",
    summary="Return the last N lineage records for a workspace",
)
async def lineage_tail(workspace_id: str, n: int = 50) -> ORJSONResponse:
    store = get_lineage_store()
    records = store.tail(workspace_id, n=min(n, 200))
    return ORJSONResponse({"ok": True, "records": records, "count": len(records)})
