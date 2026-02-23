from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping


_VAR_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")
_WHOLE_VAR_RE = re.compile(r"^\{\{([a-zA-Z0-9_]+)\}\}$")


def _replace_string(template: str, variables: Mapping[str, Any]) -> Any:
    whole = _WHOLE_VAR_RE.match(template)
    if whole is not None:
        key = whole.group(1)
        if key not in variables:
            raise KeyError(f"Missing interpolation variable: {key}")
        return variables[key]

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise KeyError(f"Missing interpolation variable: {key}")
        return str(variables[key])

    return _VAR_RE.sub(replacer, template)


def interpolate(obj: Any, variables: Mapping[str, Any]) -> Any:
    if isinstance(obj, dict):
        out_dict: Dict[str, Any] = {}
        for key, value in obj.items():
            out_dict[str(key)] = interpolate(value, variables)
        return out_dict
    if isinstance(obj, list):
        out_list: List[Any] = []
        for item in obj:
            out_list.append(interpolate(item, variables))
        return out_list
    if isinstance(obj, str):
        return _replace_string(obj, variables)
    return obj
