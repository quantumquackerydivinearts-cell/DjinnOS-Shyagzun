"""
Process the Mercurie map photograph into game-ready texture assets.

Usage
-----
    python scripts/process_mercurie_map.py <path_to_photo>
    # e.g.
    python scripts/process_mercurie_map.py "C:/Users/quant/Downloads/mercurie_map.jpg"

Outputs (written to apps/atelier-api/static/maps/)
-------
    mercurie_map_full.png       — full-res cleaned map
    mercurie_map_thumb.png      — 256x256 inventory thumbnail
    mercurie_map_folded.png     — folded appearance (quarters) for journal discovery

Requires: Pillow
"""

import sys
import math
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw
except ImportError:
    print("ERROR: pip install Pillow")
    sys.exit(1)

OUT_DIR = Path(__file__).parent.parent / "apps" / "atelier-api" / "static" / "maps"


# ── Image cleanup ─────────────────────────────────────────────────────────────

def enhance(img: Image.Image) -> Image.Image:
    """Recover graphite detail from a dim photograph."""
    # Convert to RGB if needed
    img = img.convert("RGB")

    # Auto-levels: stretch contrast to fill 0-255
    img = ImageOps.autocontrast(img, cutoff=1)

    # Boost brightness slightly
    img = ImageEnhance.Brightness(img).enhance(1.25)

    # Boost contrast to make graphite lines crisp
    img = ImageEnhance.Contrast(img).enhance(1.6)

    # Slight sharpening to recover detail lost in the photo
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))

    return img


def crop_to_paper(img: Image.Image) -> Image.Image:
    """
    Crop to the paper region by finding the largest bright rectangle.
    Works by thresholding luminance and finding the bounding box of the
    white/light region, then padding inward slightly to exclude shadows.
    """
    gray = img.convert("L")
    w, h = gray.size

    # Threshold: pixels brighter than this are likely paper
    threshold = 140
    binary = gray.point(lambda p: 255 if p > threshold else 0)

    # Find bounding box of the bright region
    bbox = binary.getbbox()
    if bbox is None:
        return img  # fallback: return as-is

    x0, y0, x1, y1 = bbox

    # Pad inward slightly to clip shadow/edge artefacts
    pad = 12
    x0 = min(x0 + pad, w)
    y0 = min(y0 + pad, h)
    x1 = max(x1 - pad, 0)
    y1 = max(y1 - pad, 0)

    return img.crop((x0, y0, x1, y1))


# ── Fold effect ───────────────────────────────────────────────────────────────

def apply_fold_lines(img: Image.Image, divisions: int = 4) -> Image.Image:
    """
    Simulate a map folded into a grid of `divisions` × `divisions` panels.
    Adds dark crease lines and a subtle shadow gradient across each panel
    to sell the folded-paper look.
    """
    img = img.copy().convert("RGBA")
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    # Draw fold crease lines
    crease_color = (30, 25, 20, 160)
    crease_width = 3

    for i in range(1, divisions):
        x = w * i // divisions
        draw.rectangle([x - crease_width, 0, x + crease_width, h], fill=crease_color)

    for i in range(1, divisions):
        y = h * i // divisions
        draw.rectangle([0, y - crease_width, w, y + crease_width], fill=crease_color)

    # Subtle shadow gradient on each panel edge (inside the crease)
    shadow_w = 18
    shadow_alpha_max = 55

    for i in range(divisions + 1):
        x = w * i // divisions
        for dx in range(shadow_w):
            alpha = int(shadow_alpha_max * (1 - dx / shadow_w))
            # Right-side inner shadow
            cx = x + crease_width + dx
            if 0 < cx < w:
                draw.rectangle([cx, 0, cx, h], fill=(0, 0, 0, alpha))
            # Left-side inner shadow
            cx = x - crease_width - dx
            if 0 < cx < w:
                draw.rectangle([cx, 0, cx, h], fill=(0, 0, 0, alpha))

    for i in range(divisions + 1):
        y = h * i // divisions
        for dy in range(shadow_w):
            alpha = int(shadow_alpha_max * (1 - dy / shadow_w))
            cy = y + crease_width + dy
            if 0 < cy < h:
                draw.rectangle([0, cy, w, cy], fill=(0, 0, 0, alpha))
            cy = y - crease_width - dy
            if 0 < cy < h:
                draw.rectangle([0, cy, w, cy], fill=(0, 0, 0, alpha))

    return img.convert("RGB")


def make_thumbnail(img: Image.Image, size: int = 256) -> Image.Image:
    """Square thumbnail with the map centred and letterboxed."""
    thumb = img.copy()
    thumb.thumbnail((size, size), Image.LANCZOS)
    out = Image.new("RGB", (size, size), (240, 235, 220))  # aged paper background
    ox = (size - thumb.width)  // 2
    oy = (size - thumb.height) // 2
    out.paste(thumb, (ox, oy))
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        # Try to find a recent image in Downloads
        downloads = Path.home() / "Downloads"
        candidates = sorted(
            list(downloads.glob("*.jpg")) + list(downloads.glob("*.jpeg")) +
            list(downloads.glob("*.png")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if downloads.exists() else []
        if not candidates:
            print("Usage: python process_mercurie_map.py <image_path>")
            sys.exit(1)
        src = candidates[0]
        print(f"No path given — using most recent Downloads image: {src.name}")
    else:
        src = Path(sys.argv[1])

    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {src.name}...")
    img = Image.open(src)
    print(f"  Original size: {img.size}")

    print("Enhancing...")
    img = enhance(img)

    print("Cropping to paper...")
    img = crop_to_paper(img)
    print(f"  Cropped size: {img.size}")

    # Save full resolution
    full_path = OUT_DIR / "mercurie_map_full.png"
    img.save(full_path)
    print(f"  -> {full_path}")

    # Save folded version
    print("Applying fold lines...")
    folded = apply_fold_lines(img, divisions=4)
    folded_path = OUT_DIR / "mercurie_map_folded.png"
    folded.save(folded_path)
    print(f"  -> {folded_path}")

    # Save thumbnail
    thumb = make_thumbnail(img)
    thumb_path = OUT_DIR / "mercurie_map_thumb.png"
    thumb.save(thumb_path)
    print(f"  -> {thumb_path}")

    print("Done.")


if __name__ == "__main__":
    main()