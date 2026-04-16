"""Shared path constants and utility functions for the Render Lab."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT           = Path(__file__).resolve().parents[5]  # c:/DjinnOS
SCRIPTS_DIR    = ROOT / "scripts"
PACKS_DIR      = ROOT / "gameplay" / "renderer_packs" / "compiled"
STREAMS_DIR    = ROOT / "gameplay" / "renderer_packs" / "streams"
SOURCES_DIR    = ROOT / "gameplay" / "renderer_packs" / "sources"
REPORTS_DIR    = ROOT / "reports" / "renderer_toolchain"
BUDGETS_CONTRACT  = ROOT / "gameplay" / "contracts" / "renderer_stream_budgets.v1.json"
CANONICAL_SOURCE  = ROOT / "apps" / "atelier-desktop" / "public" / "renderer-pack-source.json"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_project_id() -> str:
    raw = f"rlp_{int(time.time() * 1000)}_{os.getpid()}"
    return "rlp_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def new_lineage_id() -> str:
    raw = f"lin_{int(time.time() * 1000000)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def run_script(args: list[str], cwd: Path | None = None) -> tuple[bool, str, int]:
    """Run a Python toolchain script. Returns (ok, output_tail, elapsed_ms)."""
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            ["python"] + args,
            cwd=str(cwd) if cwd else str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        return False, f"exception:{exc}", int((time.monotonic() - t0) * 1000)
    elapsed = int((time.monotonic() - t0) * 1000)
    combined = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
    tail = combined[-2000:] if len(combined) > 2000 else combined
    return proc.returncode == 0, tail, elapsed


def http_get_json(url: str, timeout: int = 5) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        raise RuntimeError(f"http_get_failed:{url}:{exc}") from exc


def project_artifact_paths(project_id: str) -> dict[str, Path]:
    return {
        "compiled_pack":     PACKS_DIR / f"{project_id}.v2.json",
        "stream_manifest":   STREAMS_DIR / f"{project_id}.stream.v1.json",
        "prefetch_manifest": STREAMS_DIR / f"{project_id}.prefetch.v1.json",
        "budget_report":     REPORTS_DIR / f"residency_budget.{project_id}.json",
        "toolchain_report":  REPORTS_DIR / f"report.{project_id}.json",
        "layer_projection":  REPORTS_DIR / f"layer_projection.{project_id}.json",
    }