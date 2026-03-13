import json
import hashlib
from typing import Any

def canonicalize(obj: Any) -> str:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

def canonical_hash(obj: Any) -> str:
    canon = canonicalize(obj)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()
