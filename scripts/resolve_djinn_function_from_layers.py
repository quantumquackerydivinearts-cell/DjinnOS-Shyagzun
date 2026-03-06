from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request


ROOT = Path(__file__).resolve().parents[1]


def _admin_gate_token(gate_code: str, actor_id: str, workshop_id: str) -> str:
    payload = f"{gate_code}:{actor_id}:{workshop_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _resolve_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def _parse_time(value: str) -> datetime:
    raw = str(value or "").strip()
    if raw == "":
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


class ApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        actor_id: str,
        artisan_id: str,
        role: str,
        workshop_id: str,
        workshop_scopes: str,
        capabilities: str,
        admin_gate_code: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        token = _admin_gate_token(admin_gate_code, actor_id, workshop_id)
        self.headers = {
            "Content-Type": "application/json",
            "X-Atelier-Actor": actor_id,
            "X-Atelier-Capabilities": capabilities,
            "X-Artisan-Id": artisan_id,
            "X-Artisan-Role": role,
            "X-Workshop-Id": workshop_id,
            "X-Workshop-Scopes": workshop_scopes,
            "X-Admin-Gate-Token": token,
        }

    def get_json(self, path: str, params: dict[str, str]) -> Any:
        query = parse.urlencode(params)
        req = request.Request(
            url=f"{self.base_url}{path}?{query}",
            method="GET",
            headers=self.headers,
        )
        with request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))


def _node_by_id(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in nodes:
        node_id = row.get("id")
        if isinstance(node_id, str) and node_id != "":
            out[node_id] = row
    return out


def _inbound_transition_map(edges: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for edge in edges:
        if str(edge.get("edge_kind", "")) != "state.transition":
            continue
        from_id = edge.get("from_node_id")
        to_id = edge.get("to_node_id")
        if not isinstance(from_id, str) or not isinstance(to_id, str):
            continue
        out.setdefault(to_id, []).append(from_id)
    return out


def _find_ancestor_by_layer(
    *,
    start_node_id: str,
    target_layer: int,
    inbound_map: dict[str, list[str]],
    by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    seen: set[str] = set()
    queue: list[str] = [start_node_id]
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        current_node = by_id.get(current)
        if current_node is not None and int(current_node.get("layer_index", -1)) == target_layer:
            return current_node
        for parent in inbound_map.get(current, []):
            if parent not in seen:
                queue.append(parent)
    return None


def _select_best_binding(
    *,
    l12_nodes: list[dict[str, Any]],
    bind_edges: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
    require_active_state: bool,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    inbound_by_l12: dict[str, list[str]] = {}
    for edge in bind_edges:
        from_id = edge.get("from_node_id")
        to_id = edge.get("to_node_id")
        if isinstance(from_id, str) and isinstance(to_id, str):
            inbound_by_l12.setdefault(to_id, []).append(from_id)

    candidates: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []
    for l12 in l12_nodes:
        l12_id = l12.get("id")
        if not isinstance(l12_id, str):
            continue
        l11_ids = inbound_by_l12.get(l12_id, [])
        for l11_id in l11_ids:
            l11 = nodes_by_id.get(l11_id)
            if l11 is None:
                continue
            if int(l11.get("layer_index", -1)) != 11:
                continue
            l11_payload = l11.get("payload", {})
            state = str((l11_payload if isinstance(l11_payload, dict) else {}).get("state", ""))
            if require_active_state and state != "active":
                continue
            created_at = _parse_time(str(l11.get("created_at", "")))
            candidates.append((created_at, l12, l11))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, l12_best, l11_best = candidates[0]
    return l12_best, l11_best


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve Djinn function call target from 12-layer graph state.")
    parser.add_argument("--workspace-id", default="main")
    parser.add_argument("--function-id", default="djinn.renderer.stream.execute")
    parser.add_argument("--function-version", default="v1")
    parser.add_argument(
        "--state",
        default="active",
        choices=["active", "staged", "any"],
        help="Required L11 state for resolution.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:9000")
    parser.add_argument("--actor-id", default="tester")
    parser.add_argument("--artisan-id", default="artisan-1")
    parser.add_argument("--role", default="steward")
    parser.add_argument("--workshop-id", default="workshop-1")
    parser.add_argument("--workshop-scopes", default="scene:*,workspace:*")
    parser.add_argument("--capabilities", default="layer.read,function.read")
    parser.add_argument("--admin-gate-code", default="STEWARD_DEV_GATE")
    parser.add_argument("--output", default="reports/renderer_toolchain/djinn_function_resolution.report.json")
    args = parser.parse_args()

    workspace_id = str(args.workspace_id or "main")
    function_id = str(args.function_id)
    function_version = str(args.function_version)

    client = ApiClient(
        base_url=args.base_url,
        actor_id=args.actor_id,
        artisan_id=args.artisan_id,
        role=args.role,
        workshop_id=args.workshop_id,
        workshop_scopes=args.workshop_scopes,
        capabilities=args.capabilities,
        admin_gate_code=args.admin_gate_code,
    )

    nodes_raw = client.get_json("/v1/game/layers/nodes", {"workspace_id": workspace_id})
    edges_raw = client.get_json("/v1/game/layers/edges", {"workspace_id": workspace_id})
    funcs_raw = client.get_json("/v1/game/functions", {"workspace_id": workspace_id})

    nodes = [row for row in nodes_raw if isinstance(row, dict)] if isinstance(nodes_raw, list) else []
    edges = [row for row in edges_raw if isinstance(row, dict)] if isinstance(edges_raw, list) else []
    funcs = [row for row in funcs_raw if isinstance(row, dict)] if isinstance(funcs_raw, list) else []

    function_entry = None
    for row in funcs:
        if str(row.get("function_id", "")) == function_id and str(row.get("version", "")) == function_version:
            function_entry = row
            break

    l12_nodes: list[dict[str, Any]] = []
    for node in nodes:
        if int(node.get("layer_index", -1)) != 12:
            continue
        payload = node.get("payload", {})
        if not isinstance(payload, dict):
            continue
        if str(payload.get("kind", "")) != "djinn.function.binding":
            continue
        fn = payload.get("function", {})
        if not isinstance(fn, dict):
            continue
        if str(fn.get("function_id", "")) != function_id:
            continue
        if str(fn.get("version", "")) != function_version:
            continue
        l12_nodes.append(node)

    bind_edges = [
        edge
        for edge in edges
        if str(edge.get("edge_kind", "")) == "function.binds"
    ]
    nodes_by_id = _node_by_id(nodes)
    inbound_transitions = _inbound_transition_map(edges)

    require_active = args.state == "active"
    selected = _select_best_binding(
        l12_nodes=l12_nodes,
        bind_edges=bind_edges,
        nodes_by_id=nodes_by_id,
        require_active_state=require_active,
    )

    resolved = False
    reason = ""
    l12 = None
    l11 = None
    l3 = None
    l4 = None
    warnings: list[str] = []

    if function_entry is None:
        reason = "function_store_entry_not_found"
    elif len(l12_nodes) == 0:
        reason = "layer12_binding_not_found"
    elif selected is None:
        reason = f"no_binding_matches_state:{args.state}"
    else:
        l12, l11 = selected
        if args.state == "staged":
            l11_payload = l11.get("payload", {})
            l11_state = str((l11_payload if isinstance(l11_payload, dict) else {}).get("state", ""))
            if l11_state != "staged":
                reason = f"selected_binding_state_mismatch:{l11_state}"
            else:
                resolved = True
                reason = "ok"
        elif args.state == "any":
            resolved = True
            reason = "ok"
        else:
            resolved = True
            reason = "ok"

        if resolved:
            l11_id = str(l11.get("id", ""))
            l3 = _find_ancestor_by_layer(
                start_node_id=l11_id,
                target_layer=3,
                inbound_map=inbound_transitions,
                by_id=nodes_by_id,
            )
            l4 = _find_ancestor_by_layer(
                start_node_id=l11_id,
                target_layer=4,
                inbound_map=inbound_transitions,
                by_id=nodes_by_id,
            )
            if l3 is None:
                warnings.append("missing_layer3_stream_node")
            if l4 is None:
                warnings.append("missing_layer4_prefetch_node")

    payload_binding: dict[str, Any] = {}
    if isinstance(l12, dict):
        payload_l12 = l12.get("payload", {})
        if isinstance(payload_l12, dict):
            binding = payload_l12.get("binding", {})
            if isinstance(binding, dict):
                payload_binding = binding
    recursion_profile = payload_binding.get("recursion_profile", {})
    if not isinstance(recursion_profile, dict):
        recursion_profile = {}

    result = {
        "id": "renderer_djinn_resolve.report.v1",
        "workspace_id": workspace_id,
        "resolved": resolved,
        "reason": reason,
        "requested": {
            "function_id": function_id,
            "version": function_version,
            "state": args.state,
        },
        "function_store": {
            "id": str((function_entry or {}).get("id", "")),
            "function_id": str((function_entry or {}).get("function_id", "")),
            "version": str((function_entry or {}).get("version", "")),
            "signature": str((function_entry or {}).get("signature", "")),
            "function_hash": str((function_entry or {}).get("function_hash", "")),
        },
        "binding": {
            "layer12_node_id": str((l12 or {}).get("id", "")) if isinstance(l12, dict) else "",
            "layer12_node_key": str((l12 or {}).get("node_key", "")) if isinstance(l12, dict) else "",
            "layer11_node_id": str((l11 or {}).get("id", "")) if isinstance(l11, dict) else "",
            "layer11_node_key": str((l11 or {}).get("node_key", "")) if isinstance(l11, dict) else "",
            "layer11_state": str((((l11 or {}).get("payload", {}) if isinstance(l11, dict) else {}) or {}).get("state", "")),
        },
        "artifacts": {
            "pack_id": str(payload_binding.get("pack_id", "")),
            "stream_manifest_sha256": str(payload_binding.get("stream_manifest_sha256", "")),
            "prefetch_manifest_hash": str(payload_binding.get("prefetch_manifest_hash", "")),
            "layer3_node_key": str((l3 or {}).get("node_key", "")) if isinstance(l3, dict) else "",
            "layer4_node_key": str((l4 or {}).get("node_key", "")) if isinstance(l4, dict) else "",
            "recursion_profile": recursion_profile,
        },
        "djinn_call": {
            "function_id": function_id,
            "version": function_version,
            "args": {
                "pack_id": str(payload_binding.get("pack_id", "")),
                "stream_manifest_sha256": str(payload_binding.get("stream_manifest_sha256", "")),
                "prefetch_manifest_hash": str(payload_binding.get("prefetch_manifest_hash", "")),
                "workspace_id": workspace_id,
                "reference_coeff_bp": int(recursion_profile.get("reference_coeff_bp", 0)),
                "recursion_coeff_bp": int(recursion_profile.get("recursion_coeff_bp", 0)),
            },
        },
        "warnings": warnings,
    }

    output_path = _resolve_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("renderer_djinn_function_resolved" if resolved else "renderer_djinn_function_unresolved")
    print(f"- workspace:{workspace_id}")
    print(f"- function:{function_id}:{function_version}")
    print(f"- state:{args.state}")
    print(f"- resolved:{str(resolved).lower()}")
    print(f"- reason:{reason}")
    print(f"- report:{output_path}")
    return 0 if resolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
