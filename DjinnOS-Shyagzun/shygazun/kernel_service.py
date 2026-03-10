from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Mapping, Optional, cast

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from shygazun.lesson_registry import (
    LessonValidationError,
    load_lesson_registry,
    validate_lesson_payloads,
)
from shygazun.kernel.kernel import Kernel, RegisterPlugin
from shygazun.kernel.register.rose_stub import RoseStub
from shygazun.kernel.register.sakura_stub import SakuraStub
from shygazun.kernel.policy import apply_frontier_policy, frontier_for_akinenwun
from shygazun.kernel.policy.akinenwun_dictionary import AkinenwunDictionary
from shygazun.kernel.policy.recombiner import frontier_hash, frontier_to_obj
from shygazun.kernel.types import Clock, Edge, Frontier
from shygazun.kernel.types.events import KernelEventObj


@dataclass
class InMemoryField:
    field_id: str
    clock: Clock


@dataclass
class RuntimeState:
    lotus_attestation_count: int = 0


class PlaceRequest(BaseModel):
    raw: Optional[str] = None
    utterance: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    addressing: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class EligibilityRequest(BaseModel):
    field_id: str
    frontier_ids: List[str]


class RequestCommitBody(BaseModel):
    field_id: str
    frontier_id: str
    candidate_id: str


class V1AttestRequest(BaseModel):
    field_id: str
    attestation: Dict[str, Any] = Field(default_factory=dict)
    target: Dict[str, Any] = Field(default_factory=dict)


class ReplayRequest(BaseModel):
    bundle: Dict[str, Any]


class AkinenwunLookupRequest(BaseModel):
    akinenwun: str
    mode: Literal["engine", "prose"] = "prose"
    ingest: bool = True
    policy: Dict[str, Any] = Field(default_factory=dict)


class AttestRequest(BaseModel):
    witness_id: str
    attestation_kind: str
    attestation_tag: Optional[str]
    payload: Dict[str, Any] = Field(default_factory=dict)
    target: Dict[str, Any] = Field(default_factory=dict)


class BilingualProjectRequest(BaseModel):
    source_text: str


class LessonValidateRequest(BaseModel):
    lessons: List[Dict[str, Any]] = Field(default_factory=list)


class WandDamageMediaEvidence(BaseModel):
    filename: str
    mime_type: str
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    capture_timestamp: Optional[str] = None
    feature_digest: Optional[str] = None
    metadata_hash: Optional[str] = None
    transcoded_from_mime: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class WandDamageAttestationValidateRequest(BaseModel):
    wand_id: str
    notifier_id: str
    damage_state: Literal["worn", "chipped", "cracked", "broken", "restored", "retired"]
    event_tag: Optional[str] = None
    media: List[WandDamageMediaEvidence] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


_WAND_DAMAGE_ALLOWED_IMAGE_MIME_TYPES: tuple[str, ...] = (
    "image/heic",
    "image/heif",
    "image/jpeg",
    "image/png",
    "image/webp",
)
_WAND_DAMAGE_ALLOWED_IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".heic",
    ".heif",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
)


def _wand_damage_extension(filename: str) -> str:
    lower = str(filename).strip().lower()
    for suffix in sorted(_WAND_DAMAGE_ALLOWED_IMAGE_EXTENSIONS, key=len, reverse=True):
        if lower.endswith(suffix):
            return suffix
    dot_idx = lower.rfind(".")
    if dot_idx < 0:
        return ""
    return lower[dot_idx:]


def _validate_wand_damage_media(media: List[WandDamageMediaEvidence]) -> List[Dict[str, Any]]:
    if not media:
        raise HTTPException(status_code=422, detail="wand_damage_media_required")
    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(media):
        filename = str(item.filename).strip()
        if filename == "":
            raise HTTPException(status_code=422, detail=f"wand_damage_media_filename_required:{idx}")
        mime_type = str(item.mime_type).strip().lower()
        extension = _wand_damage_extension(filename)
        if mime_type not in _WAND_DAMAGE_ALLOWED_IMAGE_MIME_TYPES:
            raise HTTPException(status_code=422, detail=f"wand_damage_media_mime_unsupported:{mime_type}")
        if extension not in _WAND_DAMAGE_ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(status_code=422, detail=f"wand_damage_media_extension_unsupported:{extension or 'none'}")
        if item.size_bytes is not None and int(item.size_bytes) <= 0:
            raise HTTPException(status_code=422, detail=f"wand_damage_media_size_invalid:{idx}")
        normalized.append(
            {
                "filename": filename,
                "mime_type": mime_type,
                "extension": extension,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "capture_timestamp": item.capture_timestamp,
                "feature_digest": item.feature_digest,
                "metadata_hash": item.metadata_hash,
                "transcoded_from_mime": item.transcoded_from_mime,
                "width": item.width,
                "height": item.height,
                "heic_family": mime_type in {"image/heic", "image/heif"},
                "evidence_role": "authoritative_original",
            }
        )
    return normalized


def _json_response(payload: object, status_code: int = 200) -> Response:
    encoded = jsonable_encoder(payload)
    body = json.dumps(encoded, ensure_ascii=False, separators=(",", ":"))
    return Response(content=body, status_code=status_code, media_type="application/json")


def _shop_landing_html() -> str:
    website_url = os.getenv("PUBLIC_WEBSITE_URL", "https://www.quantumquackery.org").strip()
    atelier_url = os.getenv("PUBLIC_ATELIER_URL", "https://atelier-api.quantumquackery.com").strip()
    docs_url = f"{atelier_url.rstrip('/')}/docs"
    cards_html = _shop_cards_html(atelier_url=atelier_url, docs_url=docs_url, website_url=website_url)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Phoenix AMS-CRM Shop</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #111827;
      --muted: #6b7280;
      --accent: #0f766e;
      --accent-2: #14532d;
      --surface: #ffffff;
      --surface-2: #f5f5f4;
      --border: #e5e7eb;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8fafc 0%, #eef2f6 50%, #f8fafc 100%);
    }}
    header {{
      padding: 64px 24px 28px;
      text-align: center;
    }}
    header h1 {{
      margin: 0 0 10px;
      font-size: 2.6rem;
      letter-spacing: 0.01em;
    }}
    .eyebrow {{
      display: inline-block;
      text-transform: uppercase;
      letter-spacing: 0.2em;
      font-size: 0.75rem;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    header p {{
      margin: 0 auto;
      max-width: 760px;
      font-size: 1.05rem;
      color: var(--muted);
      line-height: 1.6;
    }}
    .cta-row {{
      margin-top: 24px;
      display: flex;
      gap: 12px;
      justify-content: center;
      flex-wrap: wrap;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 18px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--border);
      color: var(--ink);
      background: var(--surface);
    }}
    .btn.primary {{
      background: var(--accent);
      color: #ffffff;
      border-color: transparent;
    }}
    .btn.secondary {{
      background: var(--accent-2);
      color: #ffffff;
      border-color: transparent;
    }}
    main {{
      padding: 24px;
      max-width: 1100px;
      margin: 0 auto 64px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px;
      min-height: 210px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
    }}
    .card h3 {{
      margin: 0 0 8px;
      font-size: 1.1rem;
    }}
    .card p {{
      margin: 0 0 16px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .card .price {{
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 10px;
    }}
    .card .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 12px;
    }}
    .tag {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      color: var(--muted);
    }}
    footer {{
      text-align: center;
      padding: 24px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">Phoenix AMS-CRM Shop</div>
    <h1>Service, Software, and Custom Work</h1>
    <p>
      Book consultations, request land assessments, purchase Phoenix AMS-CRM licenses,
      and commission bespoke builds. The Atelier handles secure provisioning and
      guild-aware pricing.
    </p>
    <div class="cta-row">
      <a class="btn primary" href="{atelier_url}" rel="noopener">Open Atelier</a>
      <a class="btn secondary" href="{website_url}" rel="noopener">Visit Quantum Quackery</a>
      <a class="btn" href="{docs_url}" rel="noopener">API Docs</a>
    </div>
  </header>
  <main>
    <div class="grid">
      {cards_html}
    </div>
  </main>
  <footer>
    Phoenix AMS-CRM is powered by the Atelier. Secure provisioning and guild membership
    verification occur inside the Atelier experience.
  </footer>
</body>
</html>"""


def _fetch_shop_items(section_id: str) -> list[dict[str, object]]:
    base_url = os.getenv("SHOP_CONTENT_API_URL", "").strip()
    workspace_id = os.getenv("SHOP_WORKSPACE_ID", "").strip()
    registry_url = os.getenv("SHOP_REGISTRY_URL", "").strip()
    distribution_id = os.getenv("SHOP_DISTRIBUTION_ID", "").strip()

    if distribution_id:
        registry_base = registry_url or base_url
        if registry_base:
            query = urllib.parse.urlencode({"distribution_id": distribution_id})
            url = f"{registry_base.rstrip('/')}/public/distributions/registry?{query}"
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    payload = resp.read().decode("utf-8")
            except Exception:
                payload = ""
            if payload:
                try:
                    record = json.loads(payload)
                except json.JSONDecodeError:
                    record = None
                if isinstance(record, dict):
                    status = str(record.get("status") or "").strip().lower()
                    if status == "active":
                        base_url = str(record.get("base_url") or "").strip() or base_url
                        workspace_id = str(record.get("shop_workspace_id") or "").strip() or workspace_id
    if base_url == "" or workspace_id == "":
        return []
    query = urllib.parse.urlencode({"workspace_id": workspace_id, "section_id": section_id})
    url = f"{base_url.rstrip('/')}/public/shop/items?{query}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            payload = resp.read().decode("utf-8")
    except Exception:
        return []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _shop_sections() -> list[dict[str, str | list[str]]]:
    return [
        {
            "id": "consultations",
            "title": "Service Consultations",
            "price": "Scheduled Sessions",
            "tags": ["Strategy", "Architecture", "Operations"],
            "summary": "Schedule advisory sessions by type and duration, with intake details captured up front.",
            "cta": "Open Consultations",
        },
        {
            "id": "licenses",
            "title": "Phoenix AMS-CRM Licenses",
            "price": "Software Licenses",
            "tags": ["Subscription", "Perpetual"],
            "summary": "SaaS subscription or one-time license delivery with automated account provisioning.",
            "cta": "Open Licenses",
        },
        {
            "id": "catalog",
            "title": "Physical Goods",
            "price": "Catalog Goods",
            "tags": ["Inventory", "Shipping"],
            "summary": "Catalog-based orders with inventory tracking, fulfillment, and shipping updates.",
            "cta": "Open Catalog",
        },
        {
            "id": "custom-orders",
            "title": "Custom Orders",
            "price": "Quote First",
            "tags": ["Request", "Quote", "Approve", "Pay"],
            "summary": "Quote-first flow: request, review, approve, and finalize payment.",
            "cta": "Open Custom Orders",
        },
        {
            "id": "digital",
            "title": "Digital Products",
            "price": "Instant Delivery",
            "tags": ["Downloads", "Access Links"],
            "summary": "Instant delivery on purchase with secure access links.",
            "cta": "Open Digital Library",
        },
        {
            "id": "land-assessments",
            "title": "Land Assessments",
            "price": "Guild Verified",
            "tags": ["Members Free", "Non-members Paid"],
            "summary": "Guild members book free assessments; non-members book paid slots with location intake.",
            "cta": "Open Assessments",
        },
    ]


def _shop_link_overrides() -> dict[str, str]:
    return {
        "consultations": os.getenv("SHOP_LINK_CONSULTATIONS", "").strip(),
        "licenses": os.getenv("SHOP_LINK_LICENSES", "").strip(),
        "catalog": os.getenv("SHOP_LINK_CATALOG", "").strip(),
        "custom-orders": os.getenv("SHOP_LINK_CUSTOM_ORDERS", "").strip(),
        "digital": os.getenv("SHOP_LINK_DIGITAL", "").strip(),
        "land-assessments": os.getenv("SHOP_LINK_LAND_ASSESSMENTS", "").strip(),
    }


def _shop_cards_html(*, atelier_url: str, docs_url: str, website_url: str) -> str:
    link_overrides = _shop_link_overrides()
    cards: list[str] = []
    for section in _shop_sections():
        tags = "".join(f'<span class="tag">{tag}</span>' for tag in section["tags"])  # type: ignore[arg-type]
        override = link_overrides.get(section["id"], "")
        cta_url = override or f"{atelier_url.rstrip('/')}/"
        cards.append(
            f"""<section class="card">
        <div>
          <h3>{section['title']}</h3>
          <div class="price">{section['price']}</div>
          <div class="tags">{tags}</div>
          <p>{section['summary']}</p>
        </div>
        <div class="cta-row">
          <a class="btn" href="/shop/{section['id']}">Details</a>
          <a class="btn primary" href="{cta_url}" rel="noopener">{section['cta']}</a>
        </div>
      </section>"""
        )
    return "\n".join(cards)


def _shop_items_html(items: list[dict[str, object]]) -> str:
    if not items:
        return "<p>No items are listed in this section yet.</p>"
    cards: list[str] = []
    for item in items:
        title = str(item.get("title") or "Untitled").strip()
        summary = str(item.get("summary") or "").strip()
        price_label = str(item.get("price_label") or "").strip()
        link_url = str(item.get("link_url") or "").strip() or "#"
        tags_obj = item.get("tags")
        tags_list = tags_obj if isinstance(tags_obj, list) else []
        tags = "".join(f'<span class="tag">{str(tag)}</span>' for tag in tags_list)
        cards.append(
            f"""<div class="card">
      <h3>{title}</h3>
      <div class="price">{price_label}</div>
      <div class="tags">{tags}</div>
      <p>{summary}</p>
      <div class="cta-row">
        <a class="btn primary" href="{link_url}" rel="noopener">Open</a>
      </div>
    </div>"""
        )
    return f'<div class="grid">{"".join(cards)}</div>'


def _shop_section_html(section_id: str) -> str:
    website_url = os.getenv("PUBLIC_WEBSITE_URL", "https://www.quantumquackery.org").strip()
    atelier_url = os.getenv("PUBLIC_ATELIER_URL", "https://atelier-api.quantumquackery.com").strip()
    docs_url = f"{atelier_url.rstrip('/')}/docs"
    section_map = {item["id"]: item for item in _shop_sections()}
    section = section_map.get(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="shop_section_not_found")
    tags = "".join(f'<span class="tag">{tag}</span>' for tag in section["tags"])  # type: ignore[arg-type]
    override = _shop_link_overrides().get(section_id, "")
    cta_url = override or f"{atelier_url.rstrip('/')}/"
    items_html = _shop_items_html(_fetch_shop_items(section_id))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{section['title']} | Phoenix AMS-CRM Shop</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #111827;
      --muted: #6b7280;
      --accent: #0f766e;
      --accent-2: #14532d;
      --surface: #ffffff;
      --surface-2: #f5f5f4;
      --border: #e5e7eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8fafc 0%, #eef2f6 50%, #f8fafc 100%);
    }}
    main {{
      padding: 48px 24px 64px;
      max-width: 920px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 2.2rem;
    }}
    p {{
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.6;
    }}
    .price {{
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 12px;
    }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }}
    .tag {{
      background: var(--surface-2);
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      color: var(--muted);
    }}
    .cta-row {{
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 18px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--border);
      color: var(--ink);
      background: var(--surface);
    }}
    .btn.primary {{
      background: var(--accent);
      color: #ffffff;
      border-color: transparent;
    }}
    .btn.secondary {{
      background: var(--accent-2);
      color: #ffffff;
      border-color: transparent;
    }}
  </style>
</head>
<body>
  <main>
    <div class="card">
      <h1>{section['title']}</h1>
      <div class="price">{section['price']}</div>
      <div class="tags">{tags}</div>
      <p>{section['summary']}</p>
      <div class="cta-row">
        <a class="btn primary" href="{cta_url}" rel="noopener">{section['cta']}</a>
        <a class="btn" href="/shop">Back to Shop</a>
        <a class="btn secondary" href="{website_url}" rel="noopener">Visit Quantum Quackery</a>
        <a class="btn" href="{docs_url}" rel="noopener">API Docs</a>
      </div>
    </div>
    <div style="margin-top:24px;">
      {items_html}
    </div>
  </main>
</body>
</html>"""


app = FastAPI()

_field = InMemoryField(field_id="F0", clock=Clock(tick=0, causal_epoch="0"))
_registers: List[RegisterPlugin] = cast(List[RegisterPlugin], [RoseStub(), SakuraStub()])
_kernel = Kernel(field=_field, registers=_registers)
_state = RuntimeState()
_akinenwun_dictionary = AkinenwunDictionary()
_lesson_registry = load_lesson_registry()


@app.get("/", response_class=HTMLResponse)
@app.get("/shop", response_class=HTMLResponse)
def shop_landing() -> str:
    return _shop_landing_html()


@app.get("/shop/{section_id}", response_class=HTMLResponse)
def shop_section(section_id: str) -> str:
    return _shop_section_html(section_id)


@app.get("/health")
def health() -> Mapping[str, Any]:
    return {
        "status": "ok",
        "service": "kernel",
        "field_id": _field.field_id,
        "lesson_count": len(_lesson_registry.lessons()),
    }


def _assert_field_id_or_default(field_id: Optional[str]) -> str:
    if field_id is None:
        return _field.field_id
    if field_id == "null":
        return _field.field_id
    if field_id != _field.field_id:
        raise HTTPException(status_code=404, detail="Not Found")
    return field_id


def _extract_raw(req: PlaceRequest) -> str:
    if req.raw is not None:
        return req.raw
    if req.utterance is not None:
        raw_obj = req.utterance.get("raw")
        if isinstance(raw_obj, str):
            return raw_obj
    raise HTTPException(status_code=422, detail="raw required")


@app.post("/place")
def place(req: PlaceRequest) -> Response:
    raw = _extract_raw(req)
    result = _kernel.place(
        raw=raw,
        context=req.context,
        addressing=req.addressing,
        metadata=req.metadata,
    )
    return _json_response(result)


@app.post("/observe")
def observe() -> Response:
    result = _kernel.observe()
    return _json_response(result)


@app.get("/events")
def events() -> Response:
    result: List[KernelEventObj] = list(_kernel.get_events())
    return _json_response(result)


@app.get("/edges")
def edges() -> Response:
    result: List[Edge] = list(_kernel.get_edges())
    return _json_response(result)


@app.post("/attest")
def attest(req: AttestRequest) -> Response:
    result = _kernel.record_attestation(
        witness_id=req.witness_id,
        attestation_kind=req.attestation_kind,
        attestation_tag=req.attestation_tag,
        payload=req.payload,
        target=req.target,
    )
    return _json_response(result)


@app.post("/v0.1/place")
def v1_place(req: PlaceRequest) -> Response:
    context = req.context if req.context is not None else {}
    field_id_obj = context.get("field_id")
    field_id: Optional[str]
    if isinstance(field_id_obj, str):
        field_id = field_id_obj
    elif field_id_obj is None:
        field_id = None
    else:
        field_id = str(field_id_obj)
    _assert_field_id_or_default(field_id)

    raw = _extract_raw(req)
    result = _kernel.place(raw=raw, context=context, addressing=req.addressing, metadata=req.metadata)

    payload: Dict[str, Any] = {
        "field_id": result.field_id,
        "clock": {"tick": result.clock.tick, "causal_epoch": result.clock.causal_epoch},
        "placement_event": result.placement_event,
        "observe": result.observe,
        "diff_exempt_metadata_keys": [],
    }
    return _json_response(payload)


@app.post("/v0.1/evaluate_eligibility")
def v1_evaluate_eligibility(req: EligibilityRequest) -> Response:
    _assert_field_id_or_default(req.field_id)
    observed = _kernel.observe()

    eligible: Dict[str, List[Dict[str, str]]] = {}
    for frontier_id, candidates in observed.eligible_by_frontier.items():
        if frontier_id not in req.frontier_ids:
            continue
        eligible[frontier_id] = [{"id": candidate.id} for candidate in candidates]

    payload = {
        "eligible_by_frontier": eligible,
        "refusals": observed.refusals,
    }
    return _json_response(payload)


@app.get("/v0.1/ceg/{field_id}")
def v1_ceg(field_id: str) -> Response:
    _assert_field_id_or_default(field_id)
    result = {
        "events": list(_kernel.get_events()),
        "edges": list(_kernel.get_edges()),
    }
    return _json_response(result)


@app.get("/v0.1/frontiers/{field_id}")
def v1_frontiers(field_id: str) -> Response:
    _assert_field_id_or_default(field_id)
    sorted_frontiers: List[Frontier] = sorted(_kernel.frontiers, key=lambda f: f.id)
    result = {
        "frontiers": [{"id": frontier.id, "status": frontier.status} for frontier in sorted_frontiers]
    }
    return _json_response(result)


@app.post("/v0.1/request_commit")
def v1_request_commit(req: RequestCommitBody) -> Response:
    _assert_field_id_or_default(req.field_id)
    # Structural no-op: kernel does not auto-commit.
    result = {
        "accepted": True,
        "field_id": req.field_id,
        "frontier_id": req.frontier_id,
        "candidate_id": req.candidate_id,
    }
    return _json_response(result)


@app.post("/v0.1/attest")
def v1_attest(req: V1AttestRequest) -> Response:
    _assert_field_id_or_default(req.field_id)
    witness_obj = req.attestation.get("witness_id")
    kind_obj = req.attestation.get("kind")
    tag_obj = req.attestation.get("tag")
    payload_obj = req.attestation.get("payload")

    witness_id = witness_obj if isinstance(witness_obj, str) else "unknown"
    attest_kind = kind_obj if isinstance(kind_obj, str) else "unknown"
    attestation_tag = tag_obj if isinstance(tag_obj, str) else None
    payload = payload_obj if isinstance(payload_obj, dict) else {}

    recorded = _kernel.record_attestation(
        witness_id=witness_id,
        attestation_kind=attest_kind,
        attestation_tag=attestation_tag,
        payload=payload,
        target=req.target,
    )

    if attest_kind == "lotus":
        _state.lotus_attestation_count += 1

    committed = {
        "id": recorded["id"],
        "kind": "commitment",
        "target": req.target,
    }
    result = {
        "accepted": True,
        "recorded": recorded,
        "committed": committed,
    }
    return _json_response(result)


@app.get("/v0.1/field/{field_id}")
def v1_field(field_id: str) -> Response:
    _assert_field_id_or_default(field_id)
    field_obj = {
        "field_id": _field.field_id,
        "lotus": {"attestation_count": _state.lotus_attestation_count},
    }
    return _json_response({"field": field_obj})


@app.post("/v0.1/replay")
def v1_replay(req: ReplayRequest) -> Response:
    bundle = req.bundle
    field_id_obj = bundle.get("field_id")
    field_id = field_id_obj if isinstance(field_id_obj, str) else _field.field_id
    _assert_field_id_or_default(field_id)

    canonical = {
        "field_id": field_id,
        "placements": bundle.get("placements", []),
        "attestations": bundle.get("attestations", []),
        "metadata": bundle.get("metadata", {}),
    }
    return _json_response({"canonical": canonical})


@app.post("/v0.1/akinenwun/lookup")
def v1_akinenwun_lookup(req: AkinenwunLookupRequest) -> Response:
    try:
        frontier = frontier_for_akinenwun(req.akinenwun, mode=req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    policy = req.policy if isinstance(req.policy, dict) else {}
    if req.ingest:
        entry = _akinenwun_dictionary.ingest_frontier(frontier)
        frontier_obj = entry.frontier_obj
        if policy:
            frontier_obj = apply_frontier_policy(frontier_obj, policy)
        payload: Mapping[str, object] = {
            "akinenwun": entry.akinenwun,
            "mode": entry.mode,
            "frontier_hash": entry.frontier_hash,
            "frontier": frontier_obj,
            "dictionary_size": len(_akinenwun_dictionary.entries()),
            "stored": True,
            "frontier_policy": policy,
        }
        return _json_response(payload)

    frontier_obj = frontier_to_obj(frontier)
    if policy:
        frontier_obj = apply_frontier_policy(frontier_obj, policy)
    payload_no_ingest: Mapping[str, object] = {
        "akinenwun": frontier.akinenwun,
        "mode": frontier.mode,
        "frontier_hash": frontier_hash(frontier),
        "frontier": frontier_obj,
        "dictionary_size": len(_akinenwun_dictionary.entries()),
        "stored": False,
        "frontier_policy": policy,
    }
    return _json_response(payload_no_ingest)


@app.get("/v0.1/shygazun/lessons")
def v1_shygazun_lessons() -> Response:
    payload = {"lessons": list(_lesson_registry.lessons()), "count": len(_lesson_registry.lessons())}
    return _json_response(payload)


@app.get("/v0.1/shygazun/lessons/{lesson_id}")
def v1_shygazun_lesson(lesson_id: str) -> Response:
    try:
        payload = _lesson_registry.lesson(lesson_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="lesson_not_found") from exc
    return _json_response(payload)


@app.post("/v0.1/shygazun/project")
def v1_shygazun_project(req: BilingualProjectRequest) -> Response:
    try:
        payload = _lesson_registry.project_text(req.source_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LessonValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _json_response(payload)


@app.post("/v0.1/shygazun/cobra_surface")
def v1_shygazun_cobra_surface(req: BilingualProjectRequest) -> Response:
    try:
        payload = _lesson_registry.cobra_surface(req.source_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LessonValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _json_response(payload)


@app.post("/v0.1/shygazun/teach/validate")
def v1_shygazun_teach_validate(req: LessonValidateRequest) -> Response:
    try:
        payload = validate_lesson_payloads(req.lessons)
    except LessonValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _json_response(payload)


@app.post("/v0.1/wand/damage/validate")
def v1_wand_damage_validate(req: WandDamageAttestationValidateRequest) -> Response:
    wand_id = str(req.wand_id).strip()
    notifier_id = str(req.notifier_id).strip()
    if wand_id == "":
        raise HTTPException(status_code=422, detail="wand_id_required")
    if notifier_id == "":
        raise HTTPException(status_code=422, detail="notifier_id_required")
    normalized_media = _validate_wand_damage_media(req.media)
    return _json_response(
        {
            "ok": True,
            "schema_family": "wand_damage_attestation",
            "schema_version": "v1",
            "wand_id": wand_id,
            "notifier_id": notifier_id,
            "damage_state": req.damage_state,
            "event_tag": req.event_tag,
            "heic_accepted": True,
            "allowed_image_mime_types": list(_WAND_DAMAGE_ALLOWED_IMAGE_MIME_TYPES),
            "allowed_image_extensions": list(_WAND_DAMAGE_ALLOWED_IMAGE_EXTENSIONS),
            "normalized_media": normalized_media,
            "payload": dict(req.payload),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("shygazun.kernel_service:app", host="0.0.0.0", port=8000, reload=False)
