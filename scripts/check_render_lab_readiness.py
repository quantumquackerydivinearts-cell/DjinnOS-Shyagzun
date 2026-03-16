"""
scripts/check_render_lab_readiness.py
Check Render Lab readiness and federation status for a specific project.

Usage:
    py scripts/check_render_lab_readiness.py --project-id rlp_<hex16> --output reports/render_lab_readiness.json
    py scripts/check_render_lab_readiness.py --project-id rlp_<hex16> --skip-federation
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "gameplay" / "contracts" / "render_lab_readiness.v1.json"
OUTPUT_DIR = ROOT / "reports"


def _http_get_json(url: str, timeout: int = 8) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"http_{exc.code}:{url}") from exc
    except Exception as exc:
        raise RuntimeError(f"http_error:{url}:{exc}") from exc


def check(
    project_id: str,
    api_url: str = "http://127.0.0.1:9000",
    skip_federation: bool = False,
) -> dict[str, Any]:
    readiness_url = f"{api_url}/v1/render_lab/projects/{project_id}/readiness"
    if not skip_federation:
        readiness_url += "?api_url=" + api_url

    try:
        data = _http_get_json(readiness_url)
    except RuntimeError as exc:
        return {
            "id": "render_lab_readiness.v1",
            "project_id": project_id,
            "go": False,
            "readiness_green": False,
            "federation_green": False,
            "checks": [],
            "error": str(exc),
        }

    readiness_green = bool(data.get("readiness_green", False))
    federation_green = bool(data.get("federation_green", False)) if not skip_federation else True

    go = readiness_green and (federation_green if not skip_federation else True)

    result: dict[str, Any] = {
        "id": "render_lab_readiness.v1",
        "project_id": project_id,
        "project_type": data.get("project_type", "unknown"),
        "go": go,
        "readiness_green": readiness_green,
        "federation_green": federation_green if not skip_federation else None,
        "checks": data.get("checks", []),
        "federation": data.get("federation") if not skip_federation else None,
        "checked_at": data.get("checked_at", ""),
    }

    _print_summary(result)
    return result


def _print_summary(result: dict[str, Any]) -> None:
    go_label = "GO" if result["go"] else "NO-GO"
    print(f"render_lab_readiness:{go_label}:project={result['project_id']}")
    for check in result.get("checks", []):
        status = "PASS" if check.get("ok") else "FAIL"
        print(f"  {status}: {check.get('name', '?')}")
    if result.get("federation") is not None:
        fed_ok = result.get("federation_green", False)
        print(f"  {'PASS' if fed_ok else 'FAIL'}: federation")
    if result.get("error"):
        print(f"  ERROR: {result['error']}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Render Lab readiness for a project")
    parser.add_argument("--project-id", required=True, help="Render Lab project ID (rlp_<hex>)")
    parser.add_argument("--api-url", default="http://127.0.0.1:9000", help="Atelier API base URL")
    parser.add_argument("--output", default=None, help="Write JSON report to this path")
    parser.add_argument("--skip-federation", action="store_true", help="Skip federation green check")
    args = parser.parse_args()

    result = check(
        project_id=args.project_id,
        api_url=args.api_url,
        skip_federation=args.skip_federation,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"render_lab_readiness_report_written:{out_path}")

    return 0 if result["go"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
