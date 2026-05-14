"""
Guild authentication gate.

Validates viewer Bearer tokens against the Atelier API.
Set REQUIRE_AUTH=true in the environment to enforce authentication.
Dev mode (default) accepts any connection without a token.

QCR integration: the Atelier API issues tokens to guild members.
Stewards, senior artisans, and paying viewers hold valid tokens.
The relay enforces the token boundary — the Atelier manages issuance.
"""

import os
from typing import Optional

import aiohttp

REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
ATELIER_API  = os.getenv("ATELIER_API",  "http://127.0.0.1:9000")

_DEV_USER = {"artisan_id": "dev", "role": "steward", "workspace_id": "dev"}


async def validate_token(token: str) -> Optional[dict]:
    """
    Validate a Bearer token.  Returns user info dict or None if invalid.

    In dev mode (REQUIRE_AUTH=false) returns a synthetic steward record
    regardless of token value, so the relay works without the Atelier running.
    """
    if not REQUIRE_AUTH:
        return _DEV_USER

    if not token or not token.strip():
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ATELIER_API}/v1/auth/me",
                headers={"Authorization": f"Bearer {token.strip()}"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception:
        return None
