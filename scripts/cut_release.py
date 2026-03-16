"""
scripts/cut_release.py
Cut a timestamped release of the Atelier stack.

Checks:
  - Kernel health (http://127.0.0.1:8000/health)
  - API readiness (http://127.0.0.1:9000/ready)
  - Federation green (/v1/federation/health)
  - Render Lab readiness (optional, requires --render-lab-project-id)
  - production_go_no_go.py (runs gate stamp + bundle budget checks)

On success, writes:
  releases/<TIMESTAMP>/
    manifest.json          — release metadata + check results
    production_go_no_go.metrics.json
    render_lab_readiness.json  (if --render-lab-project-id given)
    atelier-desktop-win32-x64.zip  (if present in release/desktop)
    atelier-api-bundle.zip         (always assembled from apps/atelier-api)

Usage:
    py scripts/cut_release.py
    py scripts/cut_release.py --target render_lab --render-lab-project-id rlp_<hex>
    py scripts/cut_release.py --skip-live-checks --skip-build
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT            = Path(__file__).resolve().parents[1]
RELEASES_DIR    = ROOT / "releases"
DESKTOP_DIR     = ROOT / "apps" / "atelier-desktop"
API_DIR         = ROOT / "apps" / "atelier-api"
REPORTS_DIR     = ROOT / "reports"

DESKTOP_RELEASE_DIR = DESKTOP_DIR / "release" / "desktop"
DESKTOP_WIN_ZIP_CANDIDATES = [
    DESKTOP_RELEASE_DIR / "win-unpacked",
    DESKTOP_DIR / "release",
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get_json(url: str, timeout: int = 6) -> tuple[bool, int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            code = resp.status
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
            return code == 200, code, body
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            body = {}
        return False, exc.code, body
    except Exception as exc:
        return False, 0, {"error": str(exc)}


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd or ROOT),
            check=False, capture_output=True, text=True,
        )
    except Exception as exc:
        return False, f"exception:{exc}"
    out = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
    return proc.returncode == 0, out[-2000:]


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------

def _zip_dir(src: Path, dest: Path) -> bool:
    """Zip a directory tree into dest.zip. Returns True on success."""
    if not src.exists():
        return False
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(src.parent))
        return True
    except Exception:
        return False


def _zip_tree(src: Path, dest: Path, *, base: Path | None = None) -> bool:
    """Zip a directory tree, using base as the arcname root."""
    if not src.exists():
        return False
    base = base or src.parent
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(base))
        return True
    except Exception:
        return False


def _copy_file(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    try:
        shutil.copy2(src, dest)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_kernel(kernel_url: str) -> dict[str, Any]:
    ok, code, body = _http_get_json(f"{kernel_url}/health")
    health_ok = ok and str(body.get("status")) == "ok"
    return {"name": "kernel_health", "ok": health_ok,
            "url": f"{kernel_url}/health", "http_status": code, "body": body}


def _check_api(api_url: str) -> dict[str, Any]:
    ok, code, body = _http_get_json(f"{api_url}/ready")
    readiness_ok = ok and str(body.get("status")) == "ready"
    return {"name": "api_readiness", "ok": readiness_ok,
            "url": f"{api_url}/ready", "http_status": code, "body": body}


def _check_federation(api_url: str) -> dict[str, Any]:
    ok, code, body = _http_get_json(f"{api_url}/v1/federation/health")
    fed_ok = ok and str(body.get("status")) == "ok" and body.get("error_count", 1) == 0
    return {"name": "federation_green", "ok": fed_ok,
            "url": f"{api_url}/v1/federation/health", "http_status": code,
            "status": body.get("status"), "error_count": body.get("error_count")}


def _check_render_lab(api_url: str, project_id: str) -> dict[str, Any]:
    ok, code, body = _http_get_json(f"{api_url}/v1/render_lab/projects/{project_id}/readiness")
    rl_ok = (ok and bool(body.get("readiness_green")) and bool(body.get("federation_green")))
    return {
        "name": "render_lab_readiness", "ok": rl_ok,
        "project_id": project_id,
        "readiness_green": body.get("readiness_green"),
        "federation_green": body.get("federation_green"),
        "checks": body.get("checks", []),
        "http_status": code,
    }


# ---------------------------------------------------------------------------
# Release assembly
# ---------------------------------------------------------------------------

def _assemble_api_bundle(out_path: Path) -> bool:
    """Zip the atelier-api directory (excluding .venv and __pycache__)."""
    if not API_DIR.exists():
        return False
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            skip = {".venv", "__pycache__", ".mypy_cache", "atelier.db",
                    "atelier_dev.db", "alembic.db"}
            for f in sorted(API_DIR.rglob("*")):
                if f.is_file() and not any(p in f.parts for p in skip):
                    zf.write(f, Path("atelier-api") / f.relative_to(API_DIR))
        return True
    except Exception:
        return False


def _find_desktop_zip() -> Path | None:
    """Find an existing packed desktop zip or win-unpacked dir."""
    # electron-builder --win portable produces a .zip or .exe in release/
    candidates = sorted(
        (DESKTOP_DIR / "release").rglob("atelier-desktop*.zip")
        if (DESKTOP_DIR / "release").exists() else [],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Cut a timestamped Atelier release.")
    parser.add_argument("--target", default="suite",
                        choices=["suite", "hosted", "render_lab"],
                        help="Release target type.")
    parser.add_argument("--kernel-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-url",    default="http://127.0.0.1:9000")
    parser.add_argument("--skip-live-checks", action="store_true",
                        help="Skip live stack checks (kernel, API, federation).")
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip go/no-go build step (use last built artifacts).")
    parser.add_argument("--render-lab-project-id", default=None,
                        help="Render Lab project ID to gate on readiness (rlp_<hex>).")
    parser.add_argument("--force", action="store_true",
                        help="Write release folder even if checks fail (tagged as NO-GO).")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    print(f"cut_release: target={args.target} ts={ts}")

    checks: list[dict[str, Any]] = []
    go = True

    def add(check: dict[str, Any]) -> None:
        nonlocal go
        checks.append(check)
        status = "PASS" if check["ok"] else "FAIL"
        print(f"  {status}: {check['name']}")
        if not check["ok"]:
            go = False

    # --- live stack checks ---
    if not args.skip_live_checks:
        kernel_url = args.kernel_url.rstrip("/")
        api_url    = args.api_url.rstrip("/")
        add(_check_kernel(kernel_url))
        add(_check_api(api_url))
        add(_check_federation(api_url))
        if args.render_lab_project_id:
            add(_check_render_lab(api_url, args.render_lab_project_id))

    # --- production go/no-go ---
    gng_metrics_path = REPORTS_DIR / "production_go_no_go.metrics.json"
    gng_cmd = [sys.executable, "scripts/production_go_no_go.py",
               "--output", str(gng_metrics_path)]
    if args.skip_build:
        gng_cmd.append("--skip-build")
    if args.skip_live_checks:
        gng_cmd.append("--skip-live-checks")
    if args.render_lab_project_id:
        gng_cmd += ["--render-lab-project-id", args.render_lab_project_id]
    gng_ok, gng_out = _run(gng_cmd)
    add({"name": "production_go_no_go", "ok": gng_ok, "output_tail": gng_out})

    # --- gate decision ---
    label = "GO" if go else "NO-GO"
    print(f"\nRelease gate: {label}")
    if not go and not args.force:
        print("Aborting release. Use --force to write NO-GO release folder.")
        return 1

    # --- assemble release folder ---
    release_dir = RELEASES_DIR / ts
    release_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nAssembling release: {release_dir}")

    artifacts: list[str] = []

    # copy go/no-go metrics
    if gng_metrics_path.exists():
        dest = release_dir / "production_go_no_go.metrics.json"
        _copy_file(gng_metrics_path, dest)
        artifacts.append(dest.name)

    # render lab readiness report (if applicable)
    if args.render_lab_project_id:
        rl_check = next((c for c in checks if c["name"] == "render_lab_readiness"), None)
        if rl_check:
            rl_report_path = release_dir / "render_lab_readiness.json"
            rl_report_path.write_text(
                json.dumps(rl_check, indent=2) + "\n", encoding="utf-8"
            )
            artifacts.append(rl_report_path.name)

    # desktop zip
    existing_desktop_zip = _find_desktop_zip()
    if existing_desktop_zip:
        dest = release_dir / "atelier-desktop-win32-x64.zip"
        _copy_file(existing_desktop_zip, dest)
        artifacts.append(dest.name)
        print(f"  desktop: {existing_desktop_zip.name}")
    else:
        print("  desktop: no zip found (run pack:desktop:win first)")

    # api bundle
    api_bundle_path = release_dir / "atelier-api-bundle.zip"
    if _assemble_api_bundle(api_bundle_path):
        artifacts.append(api_bundle_path.name)
        print(f"  api-bundle: {api_bundle_path.stat().st_size // 1024} KB")
    else:
        print("  api-bundle: failed to assemble")

    # manifest
    manifest: dict[str, Any] = {
        "version":         ts,
        "target":          args.target,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "go":              go,
        "gate_label":      label,
        "artifacts":       artifacts,
        "checks":          checks,
        "render_lab": {
            "project_id": args.render_lab_project_id,
        } if args.render_lab_project_id else None,
        "quality_gate": {
            "go_no_go_enforced": True,
            "metrics_file": "production_go_no_go.metrics.json",
        },
    }
    manifest_path = release_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    artifacts.append(manifest_path.name)
    print(f"\nRelease written: {release_dir}")
    print(f"Gate: {label}")

    # also write a top-level zip of the release folder
    suite_zip = RELEASES_DIR / f"atelier-{args.target}-{ts}.zip"
    _zip_tree(release_dir, suite_zip, base=RELEASES_DIR)
    if suite_zip.exists():
        print(f"Archive: {suite_zip.name} ({suite_zip.stat().st_size // 1024} KB)")

    return 0 if go else 1


if __name__ == "__main__":
    raise SystemExit(main())
