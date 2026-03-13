from typing import Any, List
from jsonpath_ng.ext import parse # type: ignore

def extract(obj: Any, path: str) -> List[Any]:
    expr = parse(path)
    return [match.value for match in expr.find(obj)]
