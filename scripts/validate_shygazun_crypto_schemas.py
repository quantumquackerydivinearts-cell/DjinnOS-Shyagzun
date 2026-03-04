from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "shygazun_crypto"

SCHEMA_FILES = {
    "completion_claim": SCHEMA_DIR / "completion_claim.schema.json",
    "share_token": SCHEMA_DIR / "share_token.schema.json",
    "forge_permit": SCHEMA_DIR / "forge_permit.schema.json",
}

SAMPLES: dict[str, dict[str, Any]] = {
    "completion_claim": {
        "claim_id": "clm_01jt6v8h8v9k3f3g3h2x4k7y5m",
        "workspace_id": "main",
        "actor_id": "player",
        "run_id": "run:sulphera_pride:14:97bb7965ff",
        "dungeon_id": "sulphera/pride",
        "difficulty_tier": 7,
        "combat_kills": 0,
        "alerts_triggered": 1,
        "civilian_harm": 0,
        "completion_mode": "pacifist",
        "pacifism_score": 0.93,
        "issued_at": "2026-03-04T21:42:00Z",
        "expires_at": "2026-03-11T21:42:00Z",
        "nonce": "n_5f78b7e677f14be4a0a445f3",
        "key_version": "sig-v2-2026q1",
        "sig_alg": "Ed25519",
        "sig": "QmFzZTY0dXJsU2lnbmF0dXJlX0NvbXBsZXRpb25DbGFpbQAAAAAAAAAA"
    },
    "share_token": {
        "token_id": "sht_01jt6vdc1z6x5sh9s3j9t0m9z8",
        "workspace_id": "main",
        "actor_id": "player",
        "recipe_id": "sulphuric_ink_v3",
        "share_ref": "share_4_of_8",
        "claim_id": "clm_01jt6v8h8v9k3f3g3h2x4k7y5m",
        "unlock_path": "dungeon_clear",
        "issued_at": "2026-03-04T21:43:00Z",
        "expires_at": "2026-03-05T21:43:00Z",
        "nonce": "n_50b790b31e2c4f9cb31f6ed3",
        "jti": "jti_01jt6ve18z6a1c1j8gm0xk5k3x",
        "key_version": "sig-v2-2026q1",
        "sig_alg": "Ed25519",
        "sig": "QmFzZTY0dXJsU2lnbmF0dXJlX1NoYXJlVG9rZW4AAAAAAAAAAAAAAA"
    },
    "forge_permit": {
        "permit_id": "fgp_01jt6vg6z4tn5we5k8sw9n7t2e",
        "workspace_id": "main",
        "actor_id": "player",
        "recipe_id": "sulphuric_ink_v3",
        "effective_k": 4,
        "shares_used": ["share_1_of_8", "share_2_of_8", "share_4_of_8", "share_7_of_8"],
        "issued_at": "2026-03-04T21:44:00Z",
        "expires_at": "2026-03-04T21:49:00Z",
        "nonce": "n_3298e0be1f7a4a50a53e02f4",
        "jti": "jti_01jt6vgk5r8m6q3kp83t12h7mw",
        "key_version": "sig-v2-2026q1",
        "sig_alg": "Ed25519",
        "sig": "QmFzZTY0dXJsU2lnbmF0dXJlX0ZvcmdlUGVybWl0AAAAAAAAAAAAAA"
    },
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_validator() -> Any:
    try:
        from jsonschema import Draft202012Validator
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("missing_dependency:jsonschema") from exc
    return Draft202012Validator


def _validate_payload(
    *,
    schema_name: str,
    payload: Any,
    Draft202012Validator: Any,
    errors: list[str],
    label: str,
) -> None:
    schema_path = SCHEMA_FILES[schema_name]
    if not schema_path.exists():
        errors.append(f"missing_schema:{schema_path}")
        return
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    violations = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if not violations:
        return
    for violation in violations:
        path_txt = ".".join(str(p) for p in violation.path) if list(violation.path) else "$"
        errors.append(f"{label}:{schema_name}:{path_txt}:{violation.message}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Shygazun crypto payloads against Draft 2020-12 schemas."
    )
    parser.add_argument("--completion-claim", type=Path, help="Path to completion claim JSON payload.")
    parser.add_argument("--share-token", type=Path, help="Path to share token JSON payload.")
    parser.add_argument("--forge-permit", type=Path, help="Path to forge permit JSON payload.")
    args = parser.parse_args()

    errors: list[str] = []

    try:
        Draft202012Validator = _load_validator()
    except RuntimeError as exc:
        print("shygazun_crypto_schema_validation_failed")
        print(f"- {exc}")
        print("- install_hint:python -m pip install jsonschema")
        return 1

    for name, path in SCHEMA_FILES.items():
        if not path.exists():
            errors.append(f"missing_schema:{path}")
    if errors:
        print("shygazun_crypto_schema_validation_failed")
        for err in errors:
            print(f"- {err}")
        return 1

    _validate_payload(
        schema_name="completion_claim",
        payload=SAMPLES["completion_claim"],
        Draft202012Validator=Draft202012Validator,
        errors=errors,
        label="sample",
    )
    _validate_payload(
        schema_name="share_token",
        payload=SAMPLES["share_token"],
        Draft202012Validator=Draft202012Validator,
        errors=errors,
        label="sample",
    )
    _validate_payload(
        schema_name="forge_permit",
        payload=SAMPLES["forge_permit"],
        Draft202012Validator=Draft202012Validator,
        errors=errors,
        label="sample",
    )

    payload_args = {
        "completion_claim": args.completion_claim,
        "share_token": args.share_token,
        "forge_permit": args.forge_permit,
    }
    for schema_name, payload_path in payload_args.items():
        if payload_path is None:
            continue
        if not payload_path.exists():
            errors.append(f"missing_payload:{payload_path}")
            continue
        try:
            payload = _load_json(payload_path)
        except Exception as exc:
            errors.append(f"invalid_json:{payload_path}:{exc}")
            continue
        _validate_payload(
            schema_name=schema_name,
            payload=payload,
            Draft202012Validator=Draft202012Validator,
            errors=errors,
            label=str(payload_path),
        )

    if errors:
        print("shygazun_crypto_schema_validation_failed")
        for err in errors:
            print(f"- {err}")
        return 1

    print("shygazun_crypto_schema_validation_ok")
    print(f"- schemas:{len(SCHEMA_FILES)}")
    checked_payloads = 3 + sum(1 for v in payload_args.values() if v is not None)
    print(f"- payload_sets_validated:{checked_payloads}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
