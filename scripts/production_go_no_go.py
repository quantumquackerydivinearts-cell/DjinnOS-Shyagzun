from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUDGETS_PATH = ROOT / "gameplay" / "contracts" / "production_budgets.v1.json"
CHECKLIST_PATH = ROOT / "gameplay" / "contracts" / "renderer_acceptance_checklist.v1.json"
RUNTIME_PLANS_DIR = ROOT / "gameplay" / "runtime_plans"
DESKTOP_DIR = ROOT / "apps" / "atelier-desktop"
DIST_ASSETS_DIR = DESKTOP_DIR / "dist" / "assets"
OUTPUT_DIR = ROOT / "reports"
OUTPUT_PATH = OUTPUT_DIR / "production_go_no_go.metrics.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_command(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover
        return False, f"exception:{exc}"
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, output.strip()


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _gzip_size(path: Path) -> int:
    if not path.exists():
        return 0
    data = path.read_bytes()
    return len(gzip.compress(data, compresslevel=9))


def _find_main_bundle_js() -> Path | None:
    if not DIST_ASSETS_DIR.exists():
        return None
    candidates = sorted(DIST_ASSETS_DIR.glob("index-*.js"), key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0] if candidates else None


def _find_worker_bundle_js() -> Path | None:
    if not DIST_ASSETS_DIR.exists():
        return None
    candidates = sorted(DIST_ASSETS_DIR.glob("labComputeWorker-*.js"), key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0] if candidates else None


def _runtime_plan_metrics() -> dict[str, Any]:
    metrics: dict[str, Any] = {"plan_count": 0, "max_actions": 0, "max_actions_plan": ""}
    if not RUNTIME_PLANS_DIR.exists():
        return metrics
    plans = sorted(RUNTIME_PLANS_DIR.glob("*.json"))
    metrics["plan_count"] = len(plans)
    for plan in plans:
        try:
            payload = _load_json(plan)
            actions = payload.get("actions", [])
            action_count = len(actions) if isinstance(actions, list) else 0
            if action_count > int(metrics["max_actions"]):
                metrics["max_actions"] = action_count
                metrics["max_actions_plan"] = str(plan.relative_to(ROOT))
        except Exception:
            continue
    return metrics


def _gate_metrics() -> dict[str, Any]:
    out: dict[str, Any] = {"missing": [], "mismatch": []}
    checklist = _load_json(CHECKLIST_PATH)
    budgets = _load_json(BUDGETS_PATH)
    required = (
        budgets.get("acceptance", {}).get("required_gate_status_by_id", {})
        if isinstance(budgets, dict)
        else {}
    )
    gates = checklist.get("gates", []) if isinstance(checklist, dict) else []
    by_id = {str(g.get("id")): str(g.get("status", "")) for g in gates if isinstance(g, dict)}
    for gate_id, expected in required.items():
        actual = by_id.get(gate_id)
        if actual is None:
            out["missing"].append(gate_id)
        elif actual != expected:
            out["mismatch"].append({"gate_id": gate_id, "expected": expected, "actual": actual})
    return out


def _http_get_json(url: str, timeout: int = 5) -> tuple[bool, int, dict]:
    """Return (ok, status_code, body_dict).  ok=True when HTTP 200 and body is valid JSON."""
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Production go/no-go harness with hard budgets.")
    parser.add_argument("--skip-build", action="store_true", help="Skip renderer build step.")
    parser.add_argument("--skip-live-checks", action="store_true",
                        help="Skip live stack checks (kernel, API readiness, federation).")
    parser.add_argument("--render-lab-project-id", default=None,
                        help="Render Lab project ID (rlp_<hex>) for readiness check. Optional.")
    parser.add_argument("--kernel-url", default="http://127.0.0.1:8000", help="Kernel base URL.")
    parser.add_argument("--api-url", default="http://127.0.0.1:9000", help="API base URL.")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Metrics output path.")
    args = parser.parse_args()

    budgets = _load_json(BUDGETS_PATH)
    metrics: dict[str, Any] = {
        "id": "production_go_no_go.metrics.v1",
        "budgets_id": budgets.get("id", "production_budgets.v1"),
        "go": True,
        "checks": [],
        "summary": {},
    }

    def add_check(name: str, ok: bool, detail: dict[str, Any]) -> None:
        metrics["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            metrics["go"] = False

    if not args.skip_build:
        ok, output = _run_command(
            [
                "C:\\windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "npm.cmd run build",
            ],
            cwd=DESKTOP_DIR,
        )
        add_check(
            "renderer_build",
            ok,
            {
                "command": "powershell -Command npm.cmd run build",
                "cwd": str(DESKTOP_DIR),
                "output_tail": output[-1000:],
            },
        )

    main_bundle = _find_main_bundle_js()
    worker_bundle = _find_worker_bundle_js()
    main_size = _file_size(main_bundle) if main_bundle else 0
    main_gzip = _gzip_size(main_bundle) if main_bundle else 0
    worker_size = _file_size(worker_bundle) if worker_bundle else 0

    renderer_budget = budgets.get("renderer", {}) if isinstance(budgets, dict) else {}
    max_main = int(renderer_budget.get("max_main_bundle_bytes", 0))
    max_main_gzip = int(renderer_budget.get("max_main_bundle_gzip_bytes", 0))
    max_worker = int(renderer_budget.get("max_worker_bundle_bytes", 0))
    add_check(
        "renderer_bundle_budget",
        bool(main_bundle) and main_size <= max_main and main_gzip <= max_main_gzip and bool(worker_bundle) and worker_size <= max_worker,
        {
            "main_bundle": str(main_bundle.relative_to(ROOT)) if main_bundle else "",
            "main_bundle_bytes": main_size,
            "main_bundle_gzip_bytes": main_gzip,
            "worker_bundle": str(worker_bundle.relative_to(ROOT)) if worker_bundle else "",
            "worker_bundle_bytes": worker_size,
            "budget": {
                "max_main_bundle_bytes": max_main,
                "max_main_bundle_gzip_bytes": max_main_gzip,
                "max_worker_bundle_bytes": max_worker,
            },
        },
    )

    runtime = _runtime_plan_metrics()
    content_budget = budgets.get("content", {}) if isinstance(budgets, dict) else {}
    max_actions = int(content_budget.get("max_runtime_plan_actions", 0))
    max_plan_count = int(content_budget.get("max_runtime_plan_count", 0))
    add_check(
        "runtime_plan_budget",
        int(runtime.get("plan_count", 0)) <= max_plan_count and int(runtime.get("max_actions", 0)) <= max_actions,
        {
            **runtime,
            "budget": {
                "max_runtime_plan_actions": max_actions,
                "max_runtime_plan_count": max_plan_count,
            },
        },
    )

    commands = budgets.get("commands", {}) if isinstance(budgets, dict) else {}
    ok, output = _run_command([sys.executable, "scripts/stamp_renderer_gates.py"], cwd=ROOT)
    add_check("renderer_gate_stamp", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("content_pack_validation", True)):
        ok, output = _run_command([sys.executable, "scripts/ci_validate_content_packs.py"], cwd=ROOT)
        add_check("content_pack_validation", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("python_compile", True)):
        ok, output = _run_command([sys.executable, "-m", "compileall", "qqva"], cwd=ROOT)
        add_check("python_compile_qqva", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("quest_cert_validation", True)):
        ok, output = _run_command([sys.executable, "scripts/validate_quest_cert.py"], cwd=ROOT)
        add_check("quest_cert_validation", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("quest_branch_validation", True)):
        ok, output = _run_command([sys.executable, "scripts/validate_quest_branches.py"], cwd=ROOT)
        add_check("quest_branch_validation", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("quest_invariant_validation", True)):
        ok, output = _run_command([sys.executable, "scripts/validate_quest_invariants.py"], cwd=ROOT)
        add_check("quest_invariant_validation", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("campaign_replay_validation", True)):
        ok, output = _run_command([sys.executable, "scripts/validate_campaign_replays.py"], cwd=ROOT)
        add_check("campaign_replay_validation", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("editor_parity_validation", True)):
        ok, output = _run_command([sys.executable, "scripts/validate_editor_parity.py"], cwd=ROOT)
        add_check("editor_parity_validation", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("art_tooling_validation", True)):
        ok, output = _run_command([sys.executable, "scripts/validate_art_tooling.py"], cwd=ROOT)
        add_check("art_tooling_validation", ok, {"output_tail": output[-1000:]})

    if bool(commands.get("determinism_check", True)):
        ok, output = _run_command([sys.executable, "scripts/verify_determinism.py", "--all-corpora"], cwd=ROOT)
        add_check("determinism_replay_contract", ok, {"output_tail": output[-1000:]})

    gates = _gate_metrics()
    gate_ok = len(gates["missing"]) == 0 and len(gates["mismatch"]) == 0
    add_check("renderer_acceptance_gates", gate_ok, gates)

    # --- Live stack checks: Kernel, API Readiness, Federation ---
    # Require --skip-live-checks to bypass.  Stack must be running when cutting a release.
    if not args.skip_live_checks:
        kernel_url = args.kernel_url.rstrip("/")
        api_url = args.api_url.rstrip("/")

        ok, code, body = _http_get_json(f"{kernel_url}/health")
        add_check("kernel_health", ok, {
            "url": f"{kernel_url}/health",
            "http_status": code,
            "body": body,
        })

        ok, code, body = _http_get_json(f"{api_url}/ready")
        readiness_ok = ok and str(body.get("status")) == "ready"
        add_check("api_readiness", readiness_ok, {
            "url": f"{api_url}/ready",
            "http_status": code,
            "status": body.get("status"),
            "body": body,
        })

        ok, code, body = _http_get_json(f"{api_url}/v1/federation/health")
        federation_ok = ok and str(body.get("status")) == "ok"
        add_check("federation_health", federation_ok, {
            "url": f"{api_url}/v1/federation/health",
            "http_status": code,
            "status": body.get("status"),
            "error_count": body.get("error_count"),
            "active_trust_count": body.get("active_trust_count"),
            "body": body,
        })

        if args.render_lab_project_id:
            rl_project_id = args.render_lab_project_id
            ok, code, body = _http_get_json(
                f"{api_url}/v1/render_lab/projects/{rl_project_id}/readiness"
            )
            rl_ok = ok and bool(body.get("readiness_green")) and bool(body.get("federation_green"))
            add_check("render_lab_readiness", rl_ok, {
                "url": f"{api_url}/v1/render_lab/projects/{rl_project_id}/readiness",
                "http_status": code,
                "project_id": rl_project_id,
                "readiness_green": body.get("readiness_green"),
                "federation_green": body.get("federation_green"),
                "checks": body.get("checks", []),
            })

    checks = metrics["checks"]
    metrics["summary"] = {
        "check_count": len(checks),
        "failed_count": len([c for c in checks if not c.get("ok")]),
        "go": metrics["go"],
    }

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"production_go_no_go: {'PASS' if metrics['go'] else 'FAIL'}")
    print(f"metrics: {out_path}")
    for check in checks:
        print(f"- {check['name']}: {'ok' if check['ok'] else 'fail'}")

    return 0 if metrics["go"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
