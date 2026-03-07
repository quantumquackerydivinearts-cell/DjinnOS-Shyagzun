from __future__ import annotations

from typing import TypedDict


class AsterColorResolution(TypedDict):
    input: str
    canonical: str
    chirality: str
    hue: str
    rgb: str
    palette_spot: str
    components: list[str]
    palette_version: str


ASTER_PALETTE_VERSION = "aster_palette_v1"

_ASTER_TOKEN_RGB: dict[str, tuple[int, int, int]] = {
    "ru": (198, 40, 40),
    "ot": (239, 108, 0),
    "el": (249, 168, 37),
    "ki": (46, 125, 50),
    "fu": (21, 101, 192),
    "ka": (40, 53, 147),
    "ae": (106, 27, 154),
    "ha": (255, 255, 255),
    "ga": (17, 17, 17),
    "na": (158, 158, 158),
    "ung": (78, 52, 46),
    "wu": (207, 216, 220),
}

_HUE_BASE_RGB: dict[str, tuple[int, int, int]] = {
    "red": (216, 58, 58),
    "orange": (224, 126, 40),
    "yellow": (228, 196, 56),
    "green": (52, 176, 88),
    "blue": (48, 120, 210),
    "indigo": (86, 92, 196),
    "violet": (144, 88, 210),
}

_RIGHT_ALIAS_TO_HUE: dict[str, str] = {
    "ry": "red",
    "rightred": "red",
    "rightchiralred": "red",
    "oth": "orange",
    "rightorange": "orange",
    "rightchiralorange": "orange",
    "le": "yellow",
    "rightyellow": "yellow",
    "rightchiralyellow": "yellow",
    "gi": "green",
    "rightgreen": "green",
    "rightchiralgreen": "green",
    "fe": "blue",
    "rightblue": "blue",
    "rightchiralblue": "blue",
    "ky": "indigo",
    "rightindigo": "indigo",
    "rightchiralindigo": "indigo",
    "alz": "violet",
    "rightviolet": "violet",
    "rightchiralviolet": "violet",
}

_LEFT_ALIAS_TO_HUE: dict[str, str] = {
    "ra": "red",
    "leftred": "red",
    "leftchiralred": "red",
    "tho": "orange",
    "leftorange": "orange",
    "leftchiralorange": "orange",
    "lu": "yellow",
    "leftyellow": "yellow",
    "leftchiralyellow": "yellow",
    "ge": "green",
    "leftgreen": "green",
    "leftchiralgreen": "green",
    "fo": "blue",
    "leftblue": "blue",
    "leftchiralblue": "blue",
    "kw": "indigo",
    "leftindigo": "indigo",
    "leftchiralindigo": "indigo",
    "dr": "violet",
    "leftviolet": "violet",
    "leftchiralviolet": "violet",
}

_LEFT_BLACK_BIAS = 0.32
_RIGHT_WHITE_BIAS = 0.28


def _normalize_token(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


def _mix_toward_black(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    keep = 1.0 - factor
    return (
        int(round(rgb[0] * keep)),
        int(round(rgb[1] * keep)),
        int(round(rgb[2] * keep)),
    )


def _mix_toward_white(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return (
        int(round(rgb[0] + ((255 - rgb[0]) * factor))),
        int(round(rgb[1] + ((255 - rgb[1]) * factor))),
        int(round(rgb[2] + ((255 - rgb[2]) * factor))),
    )


def _split_tokens(raw: str) -> list[str]:
    normalized = raw.replace("|", "+").replace(",", "+").replace("/", "+")
    return [part.strip() for part in normalized.split("+") if part.strip() != ""]


def _split_compound_token(raw: str) -> list[str]:
    normalized = _normalize_token(raw)
    if not normalized:
        return []
    candidates = sorted(_ASTER_TOKEN_RGB.keys(), key=lambda item: (-len(item), item))
    parts: list[str] = []
    offset = 0
    while offset < len(normalized):
        matched = None
        for candidate in candidates:
            if normalized.startswith(candidate, offset):
                matched = candidate
                break
        if matched is None:
            return []
        parts.append(matched)
        offset += len(matched)
    return parts


def _resolve_single(token: str) -> AsterColorResolution:
    normalized = _normalize_token(token)
    if normalized in _ASTER_TOKEN_RGB:
        rgb = _ASTER_TOKEN_RGB[normalized]
        return {
            "input": token,
            "canonical": normalized,
            "chirality": "aster",
            "hue": normalized,
            "rgb": _rgb_to_hex(rgb),
            "palette_spot": normalized,
            "components": [normalized],
            "palette_version": ASTER_PALETTE_VERSION,
        }
    if normalized in _RIGHT_ALIAS_TO_HUE:
        hue = _RIGHT_ALIAS_TO_HUE[normalized]
        rgb = _mix_toward_white(_HUE_BASE_RGB[hue], _RIGHT_WHITE_BIAS)
        canonical = f"right_{hue}"
        return {
            "input": token,
            "canonical": canonical,
            "chirality": "right",
            "hue": hue,
            "rgb": _rgb_to_hex(rgb),
            "palette_spot": canonical,
            "components": [canonical],
            "palette_version": ASTER_PALETTE_VERSION,
        }
    if normalized in _LEFT_ALIAS_TO_HUE:
        hue = _LEFT_ALIAS_TO_HUE[normalized]
        rgb = _mix_toward_black(_HUE_BASE_RGB[hue], _LEFT_BLACK_BIAS)
        canonical = f"left_{hue}"
        return {
            "input": token,
            "canonical": canonical,
            "chirality": "left",
            "hue": hue,
            "rgb": _rgb_to_hex(rgb),
            "palette_spot": canonical,
            "components": [canonical],
            "palette_version": ASTER_PALETTE_VERSION,
        }
    raise ValueError(f"unknown_aster_color_token:{token}")


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))


def _nearest_palette_spot(rgb: tuple[int, int, int]) -> str:
    best_name = ""
    best_dist = 10**12
    for token, candidate_rgb in _ASTER_TOKEN_RGB.items():
        dist = (
            (rgb[0] - candidate_rgb[0]) ** 2
            + (rgb[1] - candidate_rgb[1]) ** 2
            + (rgb[2] - candidate_rgb[2]) ** 2
        )
        if dist < best_dist:
            best_dist = dist
            best_name = token
    for hue, base in _HUE_BASE_RGB.items():
        for chirality in ("right", "left"):
            candidate_name = f"{chirality}_{hue}"
            candidate_rgb = (
                _mix_toward_white(base, _RIGHT_WHITE_BIAS)
                if chirality == "right"
                else _mix_toward_black(base, _LEFT_BLACK_BIAS)
            )
            dist = (
                (rgb[0] - candidate_rgb[0]) ** 2
                + (rgb[1] - candidate_rgb[1]) ** 2
                + (rgb[2] - candidate_rgb[2]) ** 2
            )
            if dist < best_dist:
                best_dist = dist
                best_name = candidate_name
    return best_name


def resolve_aster_color(token: str) -> AsterColorResolution:
    raw = token.strip()
    if raw == "":
        raise ValueError("unknown_aster_color_token:")
    parts = _split_tokens(raw)
    if len(parts) == 1:
        compound_parts = _split_compound_token(parts[0])
        if len(compound_parts) > 1:
            parts = compound_parts
    if len(parts) == 1:
        return _resolve_single(parts[0])

    resolved_parts = [_resolve_single(part) for part in parts]
    rgbs = [_hex_to_rgb(part["rgb"]) for part in resolved_parts]
    mix_rgb = (
        int(round(sum(item[0] for item in rgbs) / len(rgbs))),
        int(round(sum(item[1] for item in rgbs) / len(rgbs))),
        int(round(sum(item[2] for item in rgbs) / len(rgbs))),
    )
    chirality_set = {item["chirality"] for item in resolved_parts}
    if len(chirality_set) == 1:
        chirality = next(iter(chirality_set))
    else:
        chirality = "mixed"
    component_canonicals = [item["canonical"] for item in resolved_parts]
    canonical = "mix:" + "+".join(component_canonicals)
    palette_spot = _nearest_palette_spot(mix_rgb)
    return {
        "input": token,
        "canonical": canonical,
        "chirality": chirality,
        "hue": "mixed",
        "rgb": _rgb_to_hex(mix_rgb),
        "palette_spot": palette_spot,
        "components": component_canonicals,
        "palette_version": ASTER_PALETTE_VERSION,
    }
