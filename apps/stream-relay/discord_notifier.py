"""
discord_notifier.py — Discord webhook + bot notification hub.

Sends structured embeds to a Discord webhook URL for:
  - Stream goes live / ends
  - Witness joins a stream
  - Semantic events (quest state, Shygazun words, etc.)
  - Quack minted (called from atelier-api via HTTP)

Config (environment variables):
  DISCORD_WEBHOOK_URL        — primary webhook (stream events)
  DISCORD_QUACK_WEBHOOK_URL  — separate webhook for Quack mints (optional)
  STREAM_VIEWER_URL          — base URL for watch links
                               (default: https://stream.quantumquackery.com)
"""

import asyncio
import os
import time
from typing import Optional

import aiohttp

WEBHOOK_URL       = os.getenv("DISCORD_WEBHOOK_URL", "")
QUACK_WEBHOOK_URL = os.getenv("DISCORD_QUACK_WEBHOOK_URL", "") or WEBHOOK_URL
VIEWER_BASE       = os.getenv("STREAM_VIEWER_URL", "https://stream.quantumquackery.com")

# Alchemical Theatre palette
COLOR_LIVE    = 0xE91E96   # magenta — stream live
COLOR_END     = 0x3A0A2A   # plum — stream ended
COLOR_WITNESS = 0xFFB7DD   # pink — witness joined
COLOR_QUACK   = 0xD4AF37   # gold — Quack minted
COLOR_SEMANTIC = 0x8060C0  # purple — semantic event


async def _post(webhook_url: str, payload: dict) -> None:
    """Fire-and-forget webhook POST. Silently swallows errors."""
    if not webhook_url:
        return
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(webhook_url, json=payload,
                         timeout=aiohttp.ClientTimeout(total=5))
    except Exception:
        pass


def _watch_url(stream_id: str) -> str:
    return f"{VIEWER_BASE}?stream={stream_id}"


# ── Stream lifecycle ──────────────────────────────────────────────────────────

async def notify_stream_live(
    stream_id:  str,
    title:      str,
    game:       str       = "7_KLGS",
    source_ip:  str       = "",
    tongues:    list[int] = (),
) -> None:
    if not WEBHOOK_URL:
        return
    tongue_str = " · ".join(f"T{t}" for t in tongues) if tongues else "—"
    payload = {
        "embeds": [{
            "title":       f"🔴  {title or 'Untitled Stream'}",
            "description": f"**{game}** is live on the relay.\n[**Watch →**]({_watch_url(stream_id)})",
            "color":       COLOR_LIVE,
            "fields": [
                {"name": "Stream ID",  "value": f"`{stream_id}`",  "inline": True},
                {"name": "Tongues",    "value": tongue_str,         "inline": True},
            ],
            "footer": {"text": "Quantum Quackery Virtual Atelier"},
            "timestamp": _now_iso(),
        }]
    }
    await _post(WEBHOOK_URL, payload)


async def notify_stream_end(
    stream_id:    str,
    title:        str,
    duration_s:   float,
    peak_viewers: int = 0,
) -> None:
    if not WEBHOOK_URL:
        return
    dur = _fmt_duration(duration_s)
    payload = {
        "embeds": [{
            "title":       f"⬛  {title or stream_id} — ended",
            "color":       COLOR_END,
            "fields": [
                {"name": "Duration",      "value": dur,                  "inline": True},
                {"name": "Peak witnesses","value": str(peak_viewers),    "inline": True},
            ],
            "footer": {"text": "Quantum Quackery Virtual Atelier"},
            "timestamp": _now_iso(),
        }]
    }
    await _post(WEBHOOK_URL, payload)


async def notify_witness_join(
    stream_id: str,
    title:     str,
    username:  str,
    viewer_n:  int,
) -> None:
    """Posted when the first witness joins (or optionally for every join)."""
    if not WEBHOOK_URL:
        return
    payload = {
        "embeds": [{
            "title":       f"◈  {username} is witnessing",
            "description": f"[{title or stream_id}]({_watch_url(stream_id)}) — {viewer_n} witness{'es' if viewer_n != 1 else ''} present",
            "color":       COLOR_WITNESS,
            "timestamp":   _now_iso(),
        }]
    }
    await _post(WEBHOOK_URL, payload)


# ── Quack minted ──────────────────────────────────────────────────────────────

async def notify_quack_minted(
    tongue_number: int,
    tongue_name:   str,
    artisan_id:    str,
    entry_count:   int,
    rank_title:    str = "",
) -> None:
    if not QUACK_WEBHOOK_URL:
        return
    payload = {
        "embeds": [{
            "title":       f"◆  Quack minted — Tongue {tongue_number}: {tongue_name}",
            "description": (
                f"**{artisan_id}** extended the byte table with **{entry_count}** new entries.\n"
                f"The semantic substrate grows."
            ),
            "color":       COLOR_QUACK,
            "fields": [
                {"name": "Tongue",     "value": f"{tongue_number} — {tongue_name}", "inline": True},
                {"name": "Entries",    "value": str(entry_count),                    "inline": True},
                {"name": "Artisan",    "value": artisan_id,                          "inline": True},
                *(
                    [{"name": "Rank", "value": rank_title, "inline": True}]
                    if rank_title else []
                ),
            ],
            "footer":    {"text": "Quantum Quackery Guild · Quack Ledger"},
            "timestamp": _now_iso(),
        }]
    }
    await _post(QUACK_WEBHOOK_URL, payload)


# ── Semantic event ────────────────────────────────────────────────────────────

async def notify_semantic(
    stream_id: str,
    title:     str,
    ev_type:   str,
    payload_d: dict,
) -> None:
    """Post notable semantic events (quest state changes, Shygazun words)."""
    if not WEBHOOK_URL:
        return
    # Only post semantically notable events, not every frame-level one.
    NOTABLE = {"quest_state", "shygazun_word", "ko_dialogue", "perk_unlocked"}
    if ev_type not in NOTABLE:
        return
    summary = _semantic_summary(ev_type, payload_d)
    if not summary:
        return
    payload = {
        "embeds": [{
            "title":       f"◇  {ev_type.replace('_', ' ').title()}",
            "description": f"[{title or stream_id}]({_watch_url(stream_id)})\n{summary}",
            "color":       COLOR_SEMANTIC,
            "timestamp":   _now_iso(),
        }]
    }
    await _post(WEBHOOK_URL, payload)


def _semantic_summary(ev_type: str, d: dict) -> str:
    if ev_type == "quest_state":
        qid    = d.get("id", "?")
        status = d.get("status", "?")
        return f"Quest `{qid}` → **{status}**"
    if ev_type == "shygazun_word":
        symbol = d.get("symbol", "?")
        tongue = d.get("tongue", "?")
        return f"**{symbol}** · {tongue}"
    if ev_type == "ko_dialogue":
        text = d.get("text", "")
        return f"*{text[:120]}…*" if len(text) > 120 else f"*{text}*"
    if ev_type == "perk_unlocked":
        return f"Perk unlocked: **{d.get('perk_id', '?')}**"
    return ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
