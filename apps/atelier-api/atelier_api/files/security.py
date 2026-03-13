"""
atelier_api/core/security.py
JWT auth + wand-key derivation.
Wand keys are NEVER serialised to the client — all derivation is server-side.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Wand key derivation (server-only) ────────────────────────────────────────

def derive_wand_epoch_key(wand_id: str, epoch: int, extra_context: str = "") -> bytes:
    """
    Derives a deterministic epoch key for a wand.
    The result NEVER leaves this function boundary to the client.
    Used only for server-side attestation chain signing.
    """
    base = f"{wand_id}:{epoch}:{extra_context}".encode()
    return hashlib.pbkdf2_hmac(
        "sha256",
        base,
        settings.wand_master_secret.encode(),
        settings.wand_epoch_hmac_iterations,
        dklen=32,
    )


def sign_attestation(wand_id: str, epoch: int, payload_bytes: bytes) -> str:
    """
    Returns a hex HMAC signature over the payload.
    Clients receive only the signature, never the key.
    """
    key = derive_wand_epoch_key(wand_id, epoch)
    sig = hmac.new(key, payload_bytes, hashlib.sha256)
    return sig.hexdigest()


def verify_attestation(wand_id: str, epoch: int, payload_bytes: bytes, signature: str) -> bool:
    expected = sign_attestation(wand_id, epoch, payload_bytes)
    return hmac.compare_digest(expected, signature)


def generate_secure_id(prefix: str = "") -> str:
    token = secrets.token_urlsafe(16)
    return f"{prefix}_{token}" if prefix else token
