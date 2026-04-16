"""
scripts/seed_game_registry.py
==============================
Parse a game's JS registry file and write (or POST) a registry.json for the
Atelier export system.

Usage
-----
  # Write directly to the file system (no API needed — dev default):
  python scripts/seed_game_registry.py --game 7_KLGS

  # POST to a running Atelier API instead:
  python scripts/seed_game_registry.py --game 7_KLGS --api http://127.0.0.1:9000

  # Specify a different registry JS path explicitly:
  python scripts/seed_game_registry.py --game 7_KLGS --js apps/atelier-desktop/src/game7Registry.js

The script uses a lightweight JS-object-literal parser (no Node.js required).
It extracts the CHARACTERS, QUESTS, ITEMS, OBJECTS, and RECIPES arrays and
writes them to:
  apps/atelier-api/atelier_api/files/exports/{game_slug}/registry.json

or POSTs the JSON body to:
  POST /v1/export/registry/{game_slug}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── Repo root relative to this script ─────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _js_path_for_game(game_slug: str) -> Path:
    """Infer the JS registry path for a game slug (e.g. '7_KLGS')."""
    number = game_slug.split("_")[0]
    return _REPO_ROOT / "apps" / "atelier-desktop" / "src" / f"game{number}Registry.js"


def _output_path(game_slug: str) -> Path:
    return (
        _REPO_ROOT
        / "apps"
        / "atelier-api"
        / "atelier_api"
        / "files"
        / "exports"
        / game_slug
        / "registry.json"
    )


# ── JS literal parser ─────────────────────────────────────────────────────────

def _strip_comments(text: str) -> str:
    """Remove // line comments and /* block comments */ from JS text."""
    # Block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Line comments — but don't strip URLs (://); safe enough for our JS files
    text = re.sub(r"(?<!:)//[^\n]*", "", text)
    return text


def _extract_array(js: str, var_name: str) -> list:
    """
    Extract a top-level `export const VAR_NAME = [...];` array from JS source.

    Uses a simple bracket-matching extraction, then feeds the content to
    json.loads after converting JS object literals to valid JSON.
    """
    # Find `export const VAR_NAME = [`
    pattern = rf"export\s+const\s+{re.escape(var_name)}\s*=\s*\["
    m = re.search(pattern, js)
    if not m:
        return []

    start = m.end() - 1  # position of the opening [
    depth = 0
    i = start
    while i < len(js):
        ch = js[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1

    raw = js[start : i + 1]  # includes outer [ ... ]
    return _js_literal_to_json(raw)


def _js_literal_to_json(text: str) -> list | dict:
    """
    Convert a JS object/array literal to a Python value via json.loads.

    Handles:
    - Unquoted object keys  (name: "value" → "name": "value")
    - Trailing commas       ([1, 2, 3,] → [1, 2, 3])
    - null / true / false   (already valid JSON)
    - String concatenation with +  (joined at parse time)
    """
    # Join string concatenations: "foo" + \n "bar" → "foobar"
    text = re.sub(r'"\s*\+\s*"', "", text, flags=re.DOTALL)

    # Quote unquoted object keys: {key: → {"key":
    # Match after { or , (with optional whitespace/newlines), or at line start
    # following whitespace — handles both same-line and multi-line object literals.
    text = re.sub(
        r'([{,]\s*)([A-Za-z_$][A-Za-z0-9_$]*)(\s*:)',
        lambda m: f'{m.group(1)}"{m.group(2)}"{m.group(3)}',
        text,
    )
    # Handle keys at the start of a line (after leading whitespace) that were
    # missed because they follow a newline rather than { or ,
    text = re.sub(
        r'(^\s*)([A-Za-z_$][A-Za-z0-9_$]*)(\s*:)(?!\s*/)',
        lambda m: f'{m.group(1)}"{m.group(2)}"{m.group(3)}',
        text,
        flags=re.MULTILINE,
    )

    # Remove trailing commas before } or ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # Surface enough context to debug
        lines = text.splitlines()
        lineno = exc.lineno - 1
        snippet = "\n".join(lines[max(0, lineno - 2) : lineno + 3])
        raise ValueError(
            f"JSON parse error in extracted JS block at line {exc.lineno}: {exc.msg}\n"
            f"Context:\n{snippet}"
        ) from exc


def load_registry_from_js(js_path: Path) -> dict:
    """Parse game7Registry.js and return the registry dict."""
    text = js_path.read_text(encoding="utf-8")
    clean = _strip_comments(text)

    characters = _extract_array(clean, "CHARACTERS")
    quests     = _extract_array(clean, "QUESTS")
    items      = _extract_array(clean, "ITEMS")
    objects    = _extract_array(clean, "OBJECTS")
    recipes    = _extract_array(clean, "RECIPES")

    # Add slug field to quests (Ambroflow loader keys by slug)
    for q in quests:
        if "slug" not in q and "id" in q:
            q["slug"] = q["id"]

    return {
        "characters": characters,
        "quests":     quests,
        "items":      items,
        "objects":    objects,
        "recipes":    recipes,
    }


# ── Delivery ──────────────────────────────────────────────────────────────────

def write_to_file(game_slug: str, registry: dict) -> Path:
    path = _output_path(game_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"game_slug": game_slug, **registry}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def post_to_api(game_slug: str, registry: dict, api_base: str) -> None:
    try:
        import httpx
    except ImportError as exc:
        raise SystemExit("httpx is required for --api mode: pip install httpx") from exc

    url = f"{api_base.rstrip('/')}/v1/export/registry/{game_slug}"
    r = httpx.post(url, json=registry, timeout=30.0)
    r.raise_for_status()
    print(f"  API response: {r.json()}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Atelier game registry from JS source.")
    parser.add_argument("--game", required=True, help="Game slug, e.g. 7_KLGS")
    parser.add_argument("--js",   default=None,  help="Override path to the JS registry file")
    parser.add_argument("--api",  default=None,  help="POST to this API base URL instead of writing a file")
    args = parser.parse_args()

    js_path = Path(args.js) if args.js else _js_path_for_game(args.game)
    if not js_path.exists():
        raise SystemExit(f"JS registry not found: {js_path}")

    print(f"Parsing {js_path} …")
    registry = load_registry_from_js(js_path)

    counts = {k: len(v) for k, v in registry.items()}
    print(f"  Extracted: {counts}")

    if args.api:
        print(f"POSTing to {args.api} …")
        post_to_api(args.game, registry, args.api)
        print("Done.")
    else:
        out = write_to_file(args.game, registry)
        print(f"Written: {out}")
        print("Done.")


if __name__ == "__main__":
    main()