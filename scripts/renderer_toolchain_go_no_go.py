from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, output.strip()


def _validate_schema(path: Path, schema_path: Path) -> tuple[bool, str]:
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return False, "missing_dependency:jsonschema"
    payload = _load_json(path)
    schema = _load_json(schema_path)
    errs = list(Draft202012Validator(schema).iter_errors(payload))
    if errs:
        first = errs[0]
        p = ".".join(str(v) for v in first.path) if list(first.path) else "$"
        return False, f"schema_error:{p}:{first.message}"
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Renderer production toolchain go/no-go runner.")
    parser.add_argument("--source", required=True, help="Input source JSON for renderer pack compile.")
    parser.add_argument("--out-dir", default="reports/renderer_toolchain", help="Output directory for artifacts/reports.")
    parser.add_argument("--workspace-id", default="main")
    parser.add_argument("--stream-partition-mode", default="material_aware", choices=["fixed_grid", "material_aware", "lod_aware"])
    parser.add_argument("--stream-chunk-size-x", type=int, default=64)
    parser.add_argument("--stream-chunk-size-y", type=int, default=64)
    parser.add_argument("--stream-max-chunk-voxels", type=int, default=8000)
    parser.add_argument("--stream-max-chunk-bytes", type=int, default=1048576)
    parser.add_argument("--stream-max-ring", type=int, default=2)
    parser.add_argument("--hotset-materials", default="")
    parser.add_argument("--hotset-atlas-ids", default="")
    parser.add_argument("--hotset-textures", default="")
    parser.add_argument("--hotset-target-max-chunks", type=int, default=12)
    parser.add_argument("--optimize-hotset-global", action="store_true")
    parser.add_argument("--hotset-global-passes", type=int, default=2)
    parser.add_argument("--baseline-pack", default="", help="Optional baseline pack.v2 for diff report.")
    parser.add_argument("--baseline-stream", default="", help="Optional baseline stream manifest for diff report.")
    parser.add_argument("--report", default="", help="Optional explicit report path.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = ROOT / source_path

    compiled_path = out_dir / "compiled.pack.v2.json"
    stream_path = out_dir / "stream.manifest.v1.json"
    prefetch_path = out_dir / "stream.prefetch.v1.json"
    residency_report_path = out_dir / "residency_budget.report.json"
    pack_diff_path = out_dir / "pack.diff.json"
    stream_diff_path = out_dir / "stream.diff.json"
    report_path = Path(args.report) if args.report else (out_dir / "toolchain.report.v1.json")
    if not report_path.is_absolute():
        report_path = ROOT / report_path

    checks: list[dict[str, Any]] = []
    go = True

    def add_check(name: str, ok: bool, detail: dict[str, Any]) -> None:
        nonlocal go
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            go = False

    cmd_compile = [
        sys.executable,
        "scripts/build_renderer_pack_v2.py",
        "--input",
        str(source_path),
        "--output",
        str(compiled_path),
        "--workspace-id",
        str(args.workspace_id),
        "--source",
        "renderer_toolchain_go_no_go",
    ]
    ok, output = _run(cmd_compile)
    add_check("compile_pack_v2", ok, {"output_tail": output[-1200:]})

    if ok:
        ok_schema, msg = _validate_schema(compiled_path, ROOT / "schemas/renderer/renderer_pack.v2.schema.json")
        add_check("validate_pack_v2_schema", ok_schema, {"message": msg})
        ok_validator, out_validator = _run(
            [sys.executable, "scripts/validate_renderer_pack_v2.py", "--input", str(compiled_path)]
        )
        add_check("validate_pack_v2_script", ok_validator, {"output_tail": out_validator[-1200:]})

    cmd_stream = [
        sys.executable,
        "scripts/build_renderer_stream_manifest_v1.py",
        "--input",
        str(compiled_path),
        "--output",
        str(stream_path),
        "--partition-mode",
        str(args.stream_partition_mode),
        "--chunk-size-x",
        str(args.stream_chunk_size_x),
        "--chunk-size-y",
        str(args.stream_chunk_size_y),
        "--max-chunk-voxels",
        str(args.stream_max_chunk_voxels),
        "--max-chunk-bytes",
        str(args.stream_max_chunk_bytes),
        "--optimize-locality",
        "--boundary-band",
        "2",
        "--optimize-passes",
        "2",
        "--hotset-materials",
        str(args.hotset_materials),
        "--hotset-atlas-ids",
        str(args.hotset_atlas_ids),
        "--hotset-textures",
        str(args.hotset_textures),
        "--hotset-target-max-chunks",
        str(args.hotset_target_max_chunks),
    ]
    if args.optimize_hotset_global:
        cmd_stream.extend(
            [
                "--optimize-hotset-global",
                "--hotset-global-passes",
                str(args.hotset_global_passes),
            ]
        )
    ok_stream, out_stream = _run(cmd_stream)
    add_check("build_stream_manifest", ok_stream, {"output_tail": out_stream[-1200:]})

    if ok_stream:
        ok_stream_schema, msg_stream = _validate_schema(
            stream_path, ROOT / "schemas/renderer/renderer_stream_manifest.v1.schema.json"
        )
        add_check("validate_stream_manifest_schema", ok_stream_schema, {"message": msg_stream})

    cmd_prefetch = [
        sys.executable,
        "scripts/build_renderer_prefetch_manifest_v1.py",
        "--input",
        str(stream_path),
        "--output",
        str(prefetch_path),
        "--max-ring",
        str(args.stream_max_ring),
    ]
    ok_prefetch, out_prefetch = _run(cmd_prefetch)
    add_check("build_prefetch_manifest", ok_prefetch, {"output_tail": out_prefetch[-1200:]})

    if ok_prefetch:
        ok_prefetch_schema, msg_prefetch = _validate_schema(
            prefetch_path, ROOT / "schemas/renderer/renderer_stream_prefetch_manifest.v1.schema.json"
        )
        add_check("validate_prefetch_manifest_schema", ok_prefetch_schema, {"message": msg_prefetch})

    ok_budget, out_budget = _run(
        [
            sys.executable,
            "scripts/check_renderer_stream_residency_budgets.py",
            "--input",
            str(stream_path),
            "--output",
            str(residency_report_path),
        ]
    )
    add_check("residency_budget_gate", ok_budget, {"output_tail": out_budget[-1200:]})

    if args.baseline_pack:
        baseline_pack = Path(args.baseline_pack)
        if not baseline_pack.is_absolute():
            baseline_pack = ROOT / baseline_pack
        ok_diff, out_diff = _run(
            [
                sys.executable,
                "scripts/diff_renderer_packs_v2.py",
                "--before",
                str(baseline_pack),
                "--after",
                str(compiled_path),
                "--output",
                str(pack_diff_path),
            ]
        )
        add_check("diff_pack_v2", ok_diff, {"output_tail": out_diff[-1200:]})

    if args.baseline_stream:
        baseline_stream = Path(args.baseline_stream)
        if not baseline_stream.is_absolute():
            baseline_stream = ROOT / baseline_stream
        ok_sdiff, out_sdiff = _run(
            [
                sys.executable,
                "scripts/diff_renderer_stream_manifests_v1.py",
                "--before",
                str(baseline_stream),
                "--after",
                str(stream_path),
                "--output",
                str(stream_diff_path),
            ]
        )
        add_check("diff_stream_manifest_v1", ok_sdiff, {"output_tail": out_sdiff[-1200:]})

    report = {
        "id": "renderer_toolchain_report.v1",
        "go": go,
        "inputs": {
            "source": str(source_path),
            "workspace_id": str(args.workspace_id),
            "stream_partition_mode": str(args.stream_partition_mode),
            "stream_chunk_size_x": int(args.stream_chunk_size_x),
            "stream_chunk_size_y": int(args.stream_chunk_size_y),
            "stream_max_chunk_voxels": int(args.stream_max_chunk_voxels),
            "stream_max_chunk_bytes": int(args.stream_max_chunk_bytes),
            "stream_max_ring": int(args.stream_max_ring),
            "hotset_materials": str(args.hotset_materials),
            "hotset_atlas_ids": str(args.hotset_atlas_ids),
            "hotset_textures": str(args.hotset_textures),
            "hotset_target_max_chunks": int(args.hotset_target_max_chunks),
            "optimize_hotset_global": bool(args.optimize_hotset_global),
            "hotset_global_passes": int(args.hotset_global_passes),
        },
        "artifacts": {
            "compiled_pack_v2": str(compiled_path),
            "stream_manifest_v1": str(stream_path),
            "prefetch_manifest_v1": str(prefetch_path),
            "residency_budget_report": str(residency_report_path),
            "pack_diff_report": str(pack_diff_path) if args.baseline_pack else "",
            "stream_diff_report": str(stream_diff_path) if args.baseline_stream else "",
        },
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "failed_count": len([c for c in checks if not c.get("ok")]),
            "go": go,
        },
    }
    _write_json(report_path, report)

    ok_schema, msg = _validate_schema(report_path, ROOT / "schemas/renderer/renderer_toolchain_report.v1.schema.json")
    if not ok_schema:
        print("renderer_toolchain_go_no_go:FAIL")
        print(f"- report_schema_error:{msg}")
        print(f"- report:{report_path}")
        return 1

    print(f"renderer_toolchain_go_no_go:{'PASS' if go else 'FAIL'}")
    print(f"- report:{report_path}")
    print(f"- checks:{len(checks)}")
    print(f"- failed:{len([c for c in checks if not c.get('ok')])}")
    return 0 if go else 1


if __name__ == "__main__":
    raise SystemExit(main())
