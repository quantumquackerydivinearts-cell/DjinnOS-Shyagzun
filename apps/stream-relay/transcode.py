"""
Frame transcoding — raw RGB → JPEG (base64).

Uses Pillow when available.  Falls back to raw base64 RGB if not
installed (larger but still renderable on the viewer canvas).
"""

import base64
from typing import Optional

try:
    from PIL import Image
    import io as _io
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


def rgb_to_jpeg_b64(
    width:   int,
    height:  int,
    rgb:     bytes,
    quality: int = 72,
) -> Optional[str]:
    """
    Encode raw RGB bytes as a base64 JPEG string.

    Returns None on encode failure.  On success returns a string
    suitable for embedding in a data URI:
        data:image/jpeg;base64,<return value>
    """
    expected = width * height * 3
    if len(rgb) < expected:
        return None

    if _PIL_OK:
        try:
            img = Image.frombytes("RGB", (width, height), rgb[:expected])
            buf = _io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=False)
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            return None
    else:
        # Pillow missing — send raw RGB, viewer renders with ImageData
        return base64.b64encode(rgb[:expected]).decode("ascii")


def frame_mime(pillow_available: bool = _PIL_OK) -> str:
    return "jpeg" if pillow_available else "rgb"
