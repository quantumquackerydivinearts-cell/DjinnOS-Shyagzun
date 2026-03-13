from __future__ import annotations

from typing import Any, List

from jsonpath_ng.ext import parse  # type: ignore[import-untyped]


def _normalize_jayway(path: str) -> str:
    # jsonpath-ng ext uses '&' for conjunction inside filters.
    return path.replace('&&', '&')


def extract(path: str, obj: Any) -> List[Any]:
    normalized_path = _normalize_jayway(path)
    try:
        expr = parse(normalized_path)
    except Exception as exc:
        raise ValueError(f"Invalid JSONPath: {path}") from exc
    return [match.value for match in expr.find(obj)]
