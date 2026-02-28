from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuthTokenClaims:
    actor_id: str
    capabilities: tuple[str, ...]
    role: str | None
    exp: int
    iat: int | None


def _b64url_decode(value: str) -> bytes:
    padded = value + ("=" * ((4 - len(value) % 4) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_auth_token(
    *,
    actor_id: str,
    capabilities: tuple[str, ...],
    role: str | None,
    secret: str,
    exp: int,
    iat: int | None = None,
) -> str:
    header = {"alg": "HS256", "typ": "ATELIER"}
    payload = {
        "actor_id": actor_id,
        "capabilities": list(capabilities),
        "role": role,
        "exp": int(exp),
    }
    if iat is not None:
        payload["iat"] = int(iat)
    header_b64 = _b64url_encode(_json_bytes(header))
    payload_b64 = _b64url_encode(_json_bytes(payload))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_auth_token(*, token: str, secret: str, now_ts: int | None = None) -> AuthTokenClaims:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid_token_format")
    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("invalid_token_signature")
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive decode path
        raise ValueError("invalid_token_payload") from exc
    if not isinstance(header, dict) or str(header.get("alg", "")) != "HS256":
        raise ValueError("invalid_token_alg")
    actor_id = str(payload.get("actor_id", "")).strip()
    if actor_id == "":
        raise ValueError("invalid_token_actor")
    raw_caps = payload.get("capabilities")
    if not isinstance(raw_caps, list):
        raise ValueError("invalid_token_capabilities")
    capabilities = tuple(sorted({str(cap).strip() for cap in raw_caps if str(cap).strip() != ""}))
    role_raw = payload.get("role")
    role = str(role_raw).strip().lower() if isinstance(role_raw, str) and role_raw.strip() != "" else None
    exp = int(payload.get("exp", 0))
    iat = int(payload.get("iat")) if payload.get("iat") is not None else None
    now = int(now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp())
    if exp <= now:
        raise ValueError("token_expired")
    return AuthTokenClaims(
        actor_id=actor_id,
        capabilities=capabilities,
        role=role,
        exp=exp,
        iat=iat,
    )
