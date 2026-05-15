"""
discord_bot.py — Quantum Quackery Discord bot.

Slash commands:
  /streams          — list all live streams with watch links
  /stream <id>      — detail + watch link for a specific stream
  /quacks           — show recent Quack ledger entries (from Atelier API)
  /relay            — show relay health (stream count, uptime)

Config (environment variables):
  DISCORD_BOT_TOKEN      — bot token from Discord Developer Portal
  DISCORD_GUILD_ID       — QQVA guild/server ID (optional; speeds up command registration)
  STREAM_VIEWER_URL      — base URL for watch links (default: https://stream.quantumquackery.com)
  ATELIER_API            — Atelier API base URL (default: http://127.0.0.1:9000)

Usage:
  Called from main.py — run() is awaited in the main asyncio event loop.
  Requires: pip install discord.py
"""

from __future__ import annotations

import os
import asyncio
import time
from typing import Optional

BOT_TOKEN   = os.getenv("DISCORD_BOT_TOKEN",  "")
GUILD_ID    = os.getenv("DISCORD_GUILD_ID",   "")
VIEWER_BASE = os.getenv("STREAM_VIEWER_URL",  "https://stream.quantumquackery.com")
ATELIER_API = os.getenv("ATELIER_API",        "http://127.0.0.1:9000")

# Alchemical colour (Discord uses int)
COLOR_MAGENTA = 0xE91E96
COLOR_GOLD    = 0xD4AF37


def _watch_url(stream_id: str) -> str:
    return f"{VIEWER_BASE}?stream={stream_id}"


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s   = divmod(rem, 60)
    if h:   return f"{h}h {m}m"
    if m:   return f"{m}m {s}s"
    return f"{s}s"


async def start_bot() -> None:
    """Start the Discord bot. Returns immediately if BOT_TOKEN is not set."""
    if not BOT_TOKEN:
        print("[bot] DISCORD_BOT_TOKEN not set — bot disabled")
        return

    try:
        import discord
        from discord import app_commands
    except ImportError:
        print("[bot] discord.py not installed — run: pip install discord.py")
        return

    intents = discord.Intents.default()
    client  = discord.Client(intents=intents)
    tree    = app_commands.CommandTree(client)
    guild   = discord.Object(id=int(GUILD_ID)) if GUILD_ID else None

    # ── /streams ──────────────────────────────────────────────────────────────

    @tree.command(
        name        = "streams",
        description = "List all live Quantum Quackery streams",
        guild       = guild,
    )
    async def cmd_streams(interaction: discord.Interaction) -> None:
        from stream_registry import registry
        reg     = registry()
        streams = reg.all_streams()

        if not streams:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title       = "No live streams",
                    description = "The relay is quiet. Nothing is being broadcast right now.",
                    color       = COLOR_MAGENTA,
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title = f"🔴  {len(streams)} live stream{'s' if len(streams) != 1 else ''}",
            color = COLOR_MAGENTA,
        )
        for s in streams:
            title    = s.meta.get("title", s.stream_id) if s.meta else s.stream_id
            game     = s.meta.get("game",  "?")         if s.meta else "?"
            vc       = reg.viewer_count(s.stream_id)
            age      = _fmt_duration(s.age_s())
            watch    = _watch_url(s.stream_id)
            embed.add_field(
                name  = f"{title}",
                value = (
                    f"**{game}** · {vc} witness{'es' if vc != 1 else ''} · live {age}\n"
                    f"[Watch →]({watch})"
                ),
                inline = False,
            )
        embed.set_footer(text="Quantum Quackery Virtual Atelier")
        await interaction.response.send_message(embed=embed)

    # ── /stream <id> ──────────────────────────────────────────────────────────

    @tree.command(
        name        = "stream",
        description = "Get details and watch link for a specific stream",
        guild       = guild,
    )
    @app_commands.describe(stream_id="Stream ID (e.g. 127_0_0_1)")
    async def cmd_stream(interaction: discord.Interaction, stream_id: str) -> None:
        from stream_registry import registry
        reg = registry()
        s   = reg.get(stream_id)

        if s is None:
            await interaction.response.send_message(
                f"Stream `{stream_id}` not found. Use `/streams` to see what's live.",
                ephemeral=True,
            )
            return

        title  = s.meta.get("title",   s.stream_id) if s.meta else s.stream_id
        game   = s.meta.get("game",    "?")         if s.meta else "?"
        vc     = reg.viewer_count(stream_id)
        age    = _fmt_duration(s.age_s())
        tongues = s.meta.get("tongues", []) if s.meta else []
        t_str  = " · ".join(f"T{t}" for t in tongues) if tongues else "—"

        embed = discord.Embed(
            title       = f"🔴  {title}",
            description = f"[**Watch now →**]({_watch_url(stream_id)})",
            color       = COLOR_MAGENTA,
        )
        embed.add_field(name="Game",     value=game,          inline=True)
        embed.add_field(name="Live for", value=age,           inline=True)
        embed.add_field(name="Tongues",  value=t_str,         inline=True)
        embed.add_field(name="Witnesses",value=str(vc),       inline=True)
        embed.set_footer(text=f"stream ID: {stream_id}")
        await interaction.response.send_message(embed=embed)

    # ── /quacks ───────────────────────────────────────────────────────────────

    @tree.command(
        name        = "quacks",
        description = "Show recent Quack ledger entries",
        guild       = guild,
    )
    async def cmd_quacks(interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            import aiohttp
            async with aiohttp.ClientSession() as sess:
                async with sess.get(
                    f"{ATELIER_API}/v1/quack/ledger",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    quacks = await resp.json()
        except Exception as e:
            await interaction.followup.send(f"Could not reach Atelier API: {e}", ephemeral=True)
            return

        if not quacks:
            await interaction.followup.send("No Quacks in the ledger yet.", ephemeral=True)
            return

        recent = quacks[-10:]  # last 10
        embed  = discord.Embed(
            title       = f"◆  Quack Ledger — {len(quacks)} tongues",
            description = "The byte table grows through Wunashakoun practice.",
            color       = COLOR_GOLD,
        )
        for q in reversed(recent):
            embed.add_field(
                name  = f"T{q['tongue_number']}: {q['tongue_name']}",
                value = f"{q['entry_count']} entries · {q['holder_artisan_id']}",
                inline = True,
            )
        embed.set_footer(text="Quantum Quackery Virtual Atelier · Quack Ledger")
        await interaction.followup.send(embed=embed)

    # ── /relay ────────────────────────────────────────────────────────────────

    @tree.command(
        name        = "relay",
        description = "Show relay health and stream count",
        guild       = guild,
    )
    async def cmd_relay(interaction: discord.Interaction) -> None:
        from stream_registry import registry
        reg = registry()
        n   = len(reg.all_streams())
        embed = discord.Embed(
            title = "◈  Relay Status",
            color = COLOR_MAGENTA if n > 0 else 0x3A0A2A,
        )
        embed.add_field(name="Live streams", value=str(n),       inline=True)
        embed.add_field(name="Relay",        value="relay.quantumquackery.com", inline=True)
        embed.add_field(name="Viewer",       value="stream.quantumquackery.com", inline=True)
        embed.set_footer(text="Quantum Quackery Virtual Atelier")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Bot startup ───────────────────────────────────────────────────────────

    @client.event
    async def on_ready() -> None:
        print(f"[bot] logged in as {client.user}  (id: {client.user.id})")
        if guild:
            await tree.sync(guild=guild)
            print(f"[bot] slash commands synced to guild {GUILD_ID}")
        else:
            await tree.sync()
            print("[bot] slash commands synced globally (may take up to 1h)")

    print(f"[bot] starting Discord bot…")
    await client.start(BOT_TOKEN)
