from __future__ import annotations

import json
import shlex
from typing import Any, Optional, Tuple

from .atelier_port import AtelierPort


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def repl(port: AtelierPort) -> None:
    while True:
        try:
            line = input("atelier> ").strip()
        except EOFError:
            break

        if not line:
            continue
        if line == ":quit":
            break
        if line.startswith(":place "):
            parts = shlex.split(line)
            if len(parts) != 2:
                print(_to_json({"error": "usage: :place \"<text>\""}))
                continue
            place_result = port.place_line(parts[1])
            print(_to_json({"field_id": place_result.field_id, "placement_event": place_result.placement_event}))
            continue
        if line == ":frontiers":
            print(_to_json([{"id": f.id, "status": f.status, "event_ids": list(f.event_ids)} for f in port.get_frontiers()]))
            continue
        if line == ":timeline":
            print(_to_json(port.get_timeline()))
            continue
        if line == ":edges":
            print(_to_json([{"from_event": e.from_event, "to_event": e.to_event, "type": e.type, "metadata": e.metadata} for e in port.get_edges()]))
            continue
        if line.startswith(":attest "):
            try:
                witness, kind, tag = _parse_attest(line)
            except ValueError as exc:
                print(_to_json({"error": str(exc)}))
                continue
            attestation = port.record_attestation(
                witness_id=witness,
                attestation_kind=kind,
                attestation_tag=tag,
                payload={},
                target={},
            )
            print(_to_json(attestation))
            continue

        print(_to_json({"error": "unknown command"}))


def _parse_attest(line: str) -> Tuple[str, str, Optional[str]]:
    args = shlex.split(line)
    witness: Optional[str] = None
    kind: Optional[str] = None
    tag: Optional[str] = None
    for token in args[1:]:
        if "=" not in token:
            raise ValueError("usage: :attest witness=<id> kind=<kind> tag=<tag>")
        key, value = token.split("=", 1)
        if key == "witness":
            witness = value
            continue
        if key == "kind":
            kind = value
            continue
        if key == "tag":
            tag = value
            continue
        if key not in {"witness", "kind", "tag"}:
            raise ValueError(f"unknown attest arg: {key}")
    if witness is None or kind is None:
        raise ValueError("usage: :attest witness=<id> kind=<kind> tag=<tag>")
    return (witness, kind, tag)
