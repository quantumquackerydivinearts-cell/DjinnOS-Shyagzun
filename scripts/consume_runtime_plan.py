from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib import request


def _admin_gate_token(gate_code: str, actor_id: str, workshop_id: str) -> str:
    payload = f"{gate_code}:{actor_id}:{workshop_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Consume a hand-authored game runtime plan file.")
    parser.add_argument("plan_file", help="Path to runtime plan JSON file")
    parser.add_argument("--base-url", default="http://127.0.0.1:9000", help="Atelier API base URL")
    parser.add_argument("--actor-id", default="tester")
    parser.add_argument("--artisan-id", default="artisan-1")
    parser.add_argument("--role", default="steward")
    parser.add_argument("--workshop-id", default="workshop-1")
    parser.add_argument("--workshop-scopes", default="scene:*,workspace:*")
    parser.add_argument("--capabilities", default="kernel.place")
    parser.add_argument("--admin-gate-code", default="STEWARD_DEV_GATE")
    args = parser.parse_args()

    plan_path = Path(args.plan_file)
    if not plan_path.exists():
        raise SystemExit(f"plan_file_not_found: {plan_path}")

    payload_obj: Any = json.loads(plan_path.read_text(encoding="utf-8"))
    body = json.dumps(payload_obj).encode("utf-8")
    token = _admin_gate_token(args.admin_gate_code, args.actor_id, args.workshop_id)
    req = request.Request(
        url=f"{args.base_url.rstrip('/')}/v1/game/runtime/consume",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Atelier-Actor": args.actor_id,
            "X-Atelier-Capabilities": args.capabilities,
            "X-Artisan-Id": args.artisan_id,
            "X-Artisan-Role": args.role,
            "X-Workshop-Id": args.workshop_id,
            "X-Workshop-Scopes": args.workshop_scopes,
            "X-Admin-Gate-Token": token,
        },
    )
    with request.urlopen(req, timeout=30) as res:
        text = res.read().decode("utf-8")
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
