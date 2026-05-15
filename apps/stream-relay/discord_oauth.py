"""
discord_oauth.py — Discord OAuth2 witness authentication.

Flow:
  GET  /discord/oauth/start?stream=<id>
       → redirect to Discord authorization URL
  GET  /discord/oauth/callback?code=<code>&state=<stream_id>
       → exchange code, fetch user, issue relay session token
       → redirect to viewer: /stream.html?stream=<id>&token=<tok>

Issued tokens are stored in an in-memory session store (TTL 8 hours).
guild_gate.validate_token() also checks this store, so a Discord-authed
witness can connect to the WebSocket with the same token.

Config (environment variables):
  DISCORD_CLIENT_ID      — from Discord Developer Portal
  DISCORD_CLIENT_SECRET  — from Discord Developer Portal
  DISCORD_REDIRECT_URI   — must match Portal setting
                           (default: http://localhost:7702/discord/oauth/callback)
  STREAM_VIEWER_URL      — base URL for post-auth redirect
                           (default: https://stream.quantumquackery.com)
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from typing import Optional
from urllib.parse import urlencode

import aiohttp
from aiohttp import web

CLIENT_ID     = os.getenv("DISCORD_CLIENT_ID",     "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET",  "")
REDIRECT_URI  = os.getenv("DISCORD_REDIRECT_URI",
                           "https://relay.quantumquackery.com/discord/oauth/callback")
VIEWER_BASE   = os.getenv("STREAM_VIEWER_URL",
                           "https://stream.quantumquackery.com")

DISCORD_AUTH_URL  = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_ME_URL    = "https://discord.com/api/users/@me"

SESSION_TTL = 8 * 3600  # 8 hours

# ── In-memory session store ───────────────────────────────────────────────────
# token → {artisan_id, discord_username, discord_id, expires_at}
_SESSIONS: dict[str, dict] = {}


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, v in _SESSIONS.items() if v["expires_at"] < now]
    for k in expired:
        del _SESSIONS[k]


def create_session(discord_id: str, discord_username: str) -> str:
    _purge_expired()
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {
        "artisan_id":       f"discord_{discord_id}",
        "discord_id":       discord_id,
        "discord_username": discord_username,
        "role":             "witness",
        "expires_at":       time.time() + SESSION_TTL,
    }
    return token


def lookup_session(token: str) -> Optional[dict]:
    _purge_expired()
    entry = _SESSIONS.get(token)
    if entry is None:
        return None
    if entry["expires_at"] < time.time():
        del _SESSIONS[token]
        return None
    return entry


# ── Route handlers ────────────────────────────────────────────────────────────

async def oauth_start(request: web.Request) -> web.Response:
    """Redirect the browser to Discord's authorization page."""
    if not CLIENT_ID:
        return web.Response(status=503, text="Discord OAuth not configured")

    stream_id = request.rel_url.query.get("stream", "")
    # state carries the stream_id so we can redirect back after auth
    state = stream_id or "lobby"

    params = {
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         "identify",
        "state":         state,
    }
    url = f"{DISCORD_AUTH_URL}?{urlencode(params)}"
    raise web.HTTPFound(url)


async def oauth_callback(request: web.Request) -> web.Response:
    """Handle Discord's callback, exchange code, issue relay token."""
    qs        = request.rel_url.query
    code      = qs.get("code", "")
    stream_id = qs.get("state", "")
    error     = qs.get("error", "")

    if error or not code:
        return web.Response(status=400, text=f"OAuth error: {error or 'no code'}")

    if not CLIENT_ID or not CLIENT_SECRET:
        return web.Response(status=503, text="Discord OAuth not configured")

    try:
        async with aiohttp.ClientSession() as sess:
            # Exchange code for access token
            async with sess.post(
                DISCORD_TOKEN_URL,
                data={
                    "client_id":     CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type":    "authorization_code",
                    "code":          code,
                    "redirect_uri":  REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return web.Response(status=502, text="Token exchange failed")
                tok_data = await resp.json()

            access_token = tok_data.get("access_token", "")
            if not access_token:
                return web.Response(status=502, text="No access token in response")

            # Fetch user identity
            async with sess.get(
                DISCORD_ME_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return web.Response(status=502, text="Failed to fetch Discord user")
                user = await resp.json()

    except Exception as exc:
        return web.Response(status=502, text=f"OAuth request failed: {exc}")

    discord_id       = user.get("id", "unknown")
    discord_username = user.get("username", "witness")
    # Include discriminator for legacy accounts
    if user.get("discriminator", "0") != "0":
        discord_username = f"{discord_username}#{user['discriminator']}"

    relay_token = create_session(discord_id, discord_username)

    # Redirect viewer back to the stream page with token pre-filled
    viewer_url = VIEWER_BASE
    sep = "&" if "?" in viewer_url else "?"
    if stream_id and stream_id != "lobby":
        viewer_url += f"{sep}stream={stream_id}&token={relay_token}"
    else:
        viewer_url += f"{sep}token={relay_token}"

    print(f"[oauth] Discord auth OK  user:{discord_username}  id:{discord_id}")
    raise web.HTTPFound(viewer_url)
