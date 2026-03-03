from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "gameplay" / "contracts" / "determinism_corpus.v1.json"
CORPUS_GLOB = "determinism_corpus*.v1.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_pointer(payload: Any, pointer: str) -> tuple[bool, Any]:
    current = payload
    if not pointer:
        return True, current
    for raw_part in pointer.split("."):
        part = raw_part.strip()
        if not part:
            continue
        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            idx = int(part)
            if idx < 0 or idx >= len(current):
                return False, None
            current = current[idx]
            continue
        return False, None
    return True, current


def _validate_required_fields(payload: Any, fields: list[str]) -> list[str]:
    missing: list[str] = []
    for pointer in fields:
        ok, _ = _resolve_pointer(payload, pointer)
        if not ok:
            missing.append(pointer)
    return missing


def _case_hash(case: dict[str, Any]) -> tuple[bool, str, str, list[str]]:
    case_path = ROOT / str(case.get("path", ""))
    if not case_path.exists():
        return False, str(case_path), "", []
    payload = _load_json(case_path)
    required_fields = case.get("required_fields", [])
    fields = [str(f) for f in required_fields] if isinstance(required_fields, list) else []
    missing_fields = _validate_required_fields(payload, fields)
    digest = _canonical_json_hash(payload)
    return True, str(case_path), digest, missing_fields


def _discover_corpora() -> list[Path]:
    contracts_dir = ROOT / "gameplay" / "contracts"
    corpora = sorted(p for p in contracts_dir.glob(CORPUS_GLOB) if p.is_file())
    # Keep deterministic stable ordering with base corpus first when present.
    corpora.sort(key=lambda p: (0 if p.name == "determinism_corpus.v1.json" else 1, p.name))
    return corpora


def _iter_corpora(args: argparse.Namespace) -> list[Path]:
    if args.all_corpora:
        return _discover_corpora()
    corpus_path = Path(args.corpus)
    if not corpus_path.is_absolute():
        corpus_path = ROOT / corpus_path
    return [corpus_path]


def _run_corpus(corpus_path: Path, update: bool) -> tuple[bool, dict[str, Any], dict[str, Any] | None]:
    corpus = _load_json(corpus_path)
    cases = corpus.get("cases", []) if isinstance(corpus, dict) else []

    missing_files: list[dict[str, str]] = []
    mismatch: list[dict[str, str]] = []
    missing_fields: list[dict[str, Any]] = []
    updated = 0

    for case in cases:
        if not isinstance(case, dict):
            continue
        ok, resolved_path, actual, absent_fields = _case_hash(case)
        case_id = str(case.get("id", ""))
        if not ok:
            missing_files.append({"id": case_id, "path": resolved_path})
            continue
        if absent_fields:
            missing_fields.append({"id": case_id, "path": resolved_path, "fields": absent_fields})

        expected = str(case.get("expected_hash", ""))
        if update:
            if expected != actual:
                case["expected_hash"] = actual
                updated += 1
        elif expected != actual:
            mismatch.append({
                "id": case_id,
                "path": resolved_path,
                "expected_hash": expected,
                "actual_hash": actual,
            })

    result = {
        "corpus": str(corpus_path),
        "case_count": len(cases),
        "missing_files": missing_files,
        "missing_fields": missing_fields,
        "mismatch": mismatch,
        "updated": updated,
    }

    if update:
        corpus["updated_at"] = dt.date.today().isoformat()
        corpus_path.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
        return True, result, corpus

    ok = not missing_files and not missing_fields and not mismatch
    return ok, result, None


def _print_result(result: dict[str, Any], update: bool) -> None:
    corpus = result["corpus"]
    if update:
        print(f"determinism: UPDATED ({result['updated']} hash updates) [{corpus}]")
        return
    failed = bool(result["missing_files"] or result["missing_fields"] or result["mismatch"])
    print(f"determinism: {'FAIL' if failed else 'PASS'} ({result['case_count']} cases) [{corpus}]")
    if result["missing_files"]:
        print(f"- missing_files: {len(result['missing_files'])}")
        for item in result["missing_files"]:
            print(f"  - {item['id']}: {item['path']}")
    if result["missing_fields"]:
        print(f"- missing_fields: {len(result['missing_fields'])}")
        for item in result["missing_fields"]:
            print(f"  - {item['id']}: {', '.join(item['fields'])}")
    if result["mismatch"]:
        print(f"- mismatched_cases: {len(result['mismatch'])}")
        for item in result["mismatch"]:
            print(f"  - {item['id']}: expected={item['expected_hash']} actual={item['actual_hash']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify canonical deterministic hashes for corpus inputs.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="Path to determinism corpus JSON")
    parser.add_argument("--all-corpora", action="store_true", help="Verify all determinism corpora under gameplay/contracts")
    parser.add_argument("--update", action="store_true", help="Update expected hashes in corpus file(s)")
    args = parser.parse_args()

    corpora = _iter_corpora(args)
    if not corpora:
        print("determinism: FAIL (no corpus files found)")
        return 1

    all_ok = True
    total_cases = 0
    total_updated = 0

    for corpus_path in corpora:
        ok, result, _ = _run_corpus(corpus_path, args.update)
        _print_result(result, args.update)
        all_ok = all_ok and ok
        total_cases += int(result.get("case_count", 0))
        total_updated += int(result.get("updated", 0))

    if args.update:
        print(f"determinism: UPDATED_TOTAL ({total_updated} hash updates across {len(corpora)} corpus files)")
        return 0

    print(f"determinism: {'PASS' if all_ok else 'FAIL'} TOTAL ({total_cases} cases across {len(corpora)} corpus files)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
