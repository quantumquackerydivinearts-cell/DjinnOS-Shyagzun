# kernel/ids.py
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def stable_hash_obj(obj: Any) -> str:
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def derive_event_id(parts: Any) -> str:
    # parts should already be deterministic: tuples, dicts, strings, ints
    return "E_" + stable_hash_obj(parts)
