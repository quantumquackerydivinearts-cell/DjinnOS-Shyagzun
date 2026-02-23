from __future__ import annotations

from typing import Any, List

from jsonpath_ng.ext import parse  # type: ignore[import-not-found]


def extract(path: str, obj: Any) -> List[Any]:
    expr = parse(path)
    return [match.value for match in expr.find(obj)]
