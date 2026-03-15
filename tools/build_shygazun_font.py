"""
tools/build_shygazun_font.py — Shygazun Font Compiler
======================================================

Reads the canonical byte table and compiles a TTF + WOFF2 font from
Alexi's SVG glyphs using FontForge.

Codepoint mapping:
    decimal address → U+E000 + decimal
    e.g. Gaoh (decimal 31) → U+E01F
         Suy  (decimal 213) → U+E0D5

Usage:
    python tools/build_shygazun_font.py

Prerequisites (not yet present — prepare before running):
    1. FontForge installed and on PATH (or as Python package)
       Windows: https://fontforge.org/en-US/downloads/
    2. SVG glyphs placed at:
           assets/glyphs/{tongue}/{symbol}.svg
       e.g. assets/glyphs/Rose/Gaoh.svg
            assets/glyphs/Lotus/Ty.svg
       Each SVG must be:
           - Plain SVG (no inkscape namespaces needed at import time)
           - 1000×1000 unit em square
           - Filled paths only (no strokes — FontForge ignores strokes)

Output:
    assets/fonts/Shygazun.ttf
    assets/fonts/Shygazun.woff2

Also copy both files to:
    apps/atelier-desktop/public/fonts/
so Vite's dev server serves them at /fonts/Shygazun.woff2.
"""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Path bootstrap — find canonical byte table from any CWD
# ---------------------------------------------------------------------------

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SHYGAZUN_SRC = os.path.join(_REPO_ROOT, "DjinnOS_Shyagzun")

for _p in [_SHYGAZUN_SRC, _REPO_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shygazun.kernel.constants.byte_table import SHYGAZUN_BYTE_ROWS  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

GLYPH_DIR  = os.path.join(_REPO_ROOT, "assets", "glyphs")
FONT_DIR   = os.path.join(_REPO_ROOT, "assets", "fonts")
PUBLIC_DIR = os.path.join(_REPO_ROOT, "apps", "atelier-desktop", "public", "fonts")

FONT_NAME   = "Shygazun"
TTF_OUT     = os.path.join(FONT_DIR, f"{FONT_NAME}.ttf")
WOFF2_OUT   = os.path.join(FONT_DIR, f"{FONT_NAME}.woff2")

EM_SIZE = 1000  # SVGs are authored at 1000×1000 units

# ---------------------------------------------------------------------------
# Codepoint mapping
# ---------------------------------------------------------------------------

def decimal_to_codepoint(decimal: int) -> int:
    """Map a Shygazun byte table decimal address to its Unicode PUA codepoint."""
    return 0xE000 + decimal


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------

def build_font() -> None:
    try:
        import fontforge
    except ImportError:
        print(
            "ERROR: FontForge Python bindings not found.\n"
            "Install FontForge and ensure its Python bindings are importable.\n"
            "See https://fontforge.org/en-US/downloads/\n"
            "\n"
            "Once installed and glyphs are placed at assets/glyphs/{tongue}/{symbol}.svg,\n"
            "re-run: python tools/build_shygazun_font.py"
        )
        sys.exit(1)

    os.makedirs(FONT_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    font = fontforge.font()
    font.fontname    = FONT_NAME
    font.familyname  = FONT_NAME
    font.fullname    = f"{FONT_NAME} Regular"
    font.copyright   = "Alexi — Quantum Quackery Divine Arts"
    font.encoding    = "UnicodeFull"
    font.em          = EM_SIZE

    compiled = 0
    skipped: list[tuple[str, str]] = []  # (symbol, reason)

    for row in SHYGAZUN_BYTE_ROWS:
        decimal: int = row["decimal"]
        symbol:  str = row["symbol"]
        tongue:  str = row["tongue"]

        # Skip reserved bytes — they must not be filled
        if 124 <= decimal <= 127:
            continue

        svg_path = os.path.join(GLYPH_DIR, tongue, f"{symbol}.svg")

        if not os.path.isfile(svg_path):
            skipped.append((symbol, f"missing: {svg_path}"))
            continue

        codepoint = decimal_to_codepoint(decimal)
        glyph = font.createChar(codepoint, f"uni{codepoint:04X}")
        glyph.width = EM_SIZE

        try:
            glyph.importOutlines(svg_path)
            glyph.correctDirection()
            compiled += 1
        except Exception as exc:
            skipped.append((symbol, f"import error: {exc}"))

    # Generate TTF
    font.generate(TTF_OUT)

    # Generate WOFF2 via fontforge's built-in converter
    font.generate(WOFF2_OUT)

    # Mirror to public dir for Vite dev server
    import shutil
    shutil.copy2(TTF_OUT, os.path.join(PUBLIC_DIR, f"{FONT_NAME}.ttf"))
    shutil.copy2(WOFF2_OUT, os.path.join(PUBLIC_DIR, f"{FONT_NAME}.woff2"))

    font.close()

    # --- Report ---
    print(f"\nShygazun font build complete")
    print(f"  Glyphs compiled : {compiled}")
    print(f"  Glyphs skipped  : {len(skipped)}")
    if skipped:
        print("  Skipped entries:")
        for sym, reason in skipped:
            print(f"    {sym:20s}  {reason}")
    print(f"  TTF  → {TTF_OUT}")
    print(f"  WOFF2→ {WOFF2_OUT}")
    print(f"  Public copies → {PUBLIC_DIR}")


if __name__ == "__main__":
    build_font()
