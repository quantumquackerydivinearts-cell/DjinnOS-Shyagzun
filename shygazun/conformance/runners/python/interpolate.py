from __future__ import annotations

import re
from typing import Any, Dict


_VAR_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")
_WHOLE_RE = re.compile(r"^\{\{([a-zA-Z0-9_]+)\}\}$")


def interpolate(obj: Any, variables: Dict[str, Any]) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for key, value in obj.items():
            out[str(key)] = interpolate(value, variables)
        return out
    if isinstance(obj, list):
        return [interpolate(item, variables) for item in obj]
    if isinstance(obj, str):
        return _interpolate_str(obj, variables)
    return obj


def _interpolate_str(template: str, variables: Dict[str, Any]) -> Any:
    whole = _WHOLE_RE.match(template)
    if whole is not None:
        key = whole.group(1)
        if key not in variables:
            raise RuntimeError(f"Missing interpolation variable: {key}")
        return variables[key]

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise RuntimeError(f"Missing interpolation variable: {key}")
        return str(variables[key])

    return _VAR_RE.sub(repl, template)
