from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib import parse, request


ROOT = Path(__file__).resolve().parents[1]


def _admin_gate_token(gate_code: str, actor_id: str, workshop_id: str) -> str:
    payload = f"{gate_code}:{actor_id}:{workshop_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonical_hash(value: Any) -> str:
    txt = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def _resolve_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


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

    def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        req = request.Request(
            url=f"{self.base_url}{path}",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers=self.headers,
        )
        with request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))


def _read_optional_json(path_text: str) -> Any:
    if path_text.strip() == "":
        return {}
    path = _resolve_path(path_text)
    if not path.exists():
        return {}
    return _load_json(path)


def _ensure_layer_node(
    *,
    client: ApiClient,
    workspace_id: str,
    layer_index: int,
    node_key: str,
    payload: dict[str, Any],
    node_index: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    existing = node_index.get(node_key)
    if existing is not None:
        return existing, False
    created = client.post_json(
        "/v1/game/layers/nodes",
        {
            "workspace_id": workspace_id,
            "layer_index": int(layer_index),
            "node_key": node_key,
            "payload": payload,
        },
    )
    node_index[node_key] = created
    return created, True


def _ensure_layer_edge(
    *,
    client: ApiClient,
    workspace_id: str,
    from_node_id: str,
    to_node_id: str,
    edge_kind: str,
    metadata: dict[str, Any],
    edge_index: set[tuple[str, str, str]],
) -> bool:
    key = (from_node_id, to_node_id, edge_kind)
    if key in edge_index:
        return False
    client.post_json(
        "/v1/game/layers/edges",
        {
            "workspace_id": workspace_id,
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "edge_kind": edge_kind,
            "metadata": metadata,
        },
    )
    edge_index.add(key)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Project renderer toolchain artifacts into 12-layer graph + Djinn function binding.")
    parser.add_argument("--report", required=True, help="Path to renderer_toolchain_report.v1 JSON.")
    parser.add_argument("--workspace-id", default="main")
    parser.add_argument("--function-id", default="djinn.renderer.stream.execute")
    parser.add_argument("--function-version", default="v1")
    parser.add_argument("--activate", action="store_true", help="Mark L11 active pointer for this pack.")
    parser.add_argument("--reference-coeff-bp", type=int, default=7000, help="Reference coefficient in basis points (0..10000).")
    parser.add_argument("--recursion-coeff-bp", type=int, default=3000, help="Recursion coefficient in basis points (0..10000).")
    parser.add_argument("--base-url", default="http://127.0.0.1:9000")
    parser.add_argument("--actor-id", default="tester")
    parser.add_argument("--artisan-id", default="artisan-1")
    parser.add_argument("--role", default="steward")
    parser.add_argument("--workshop-id", default="workshop-1")
    parser.add_argument("--workshop-scopes", default="scene:*,workspace:*")
    parser.add_argument("--capabilities", default="layer.read,layer.write,function.read,function.write")
    parser.add_argument("--admin-gate-code", default="STEWARD_DEV_GATE")
    parser.add_argument("--output", default="reports/renderer_toolchain/layer_projection.report.json")
    args = parser.parse_args()

    workspace_id = str(args.workspace_id or "main")
    reference_coeff_bp = int(args.reference_coeff_bp)
    recursion_coeff_bp = int(args.recursion_coeff_bp)
    if reference_coeff_bp < 0 or reference_coeff_bp > 10000:
        print("renderer_layer_projection_failed:reference_coeff_out_of_range")
        return 1
    if recursion_coeff_bp < 0 or recursion_coeff_bp > 10000:
        print("renderer_layer_projection_failed:recursion_coeff_out_of_range")
        return 1
    report_path = _resolve_path(args.report)
    if not report_path.exists():
        print(f"renderer_layer_projection_failed:missing_report:{report_path}")
        return 1
    report_obj = _load_json(report_path)
    if not isinstance(report_obj, dict) or str(report_obj.get("id", "")) != "renderer_toolchain_report.v1":
        print("renderer_layer_projection_failed:invalid_report_id")
        return 1

    artifacts_obj = report_obj.get("artifacts", {})
    artifacts = artifacts_obj if isinstance(artifacts_obj, dict) else {}
    compiled_pack = _read_optional_json(str(artifacts.get("compiled_pack_v2", "")))
    stream_manifest = _read_optional_json(str(artifacts.get("stream_manifest_v1", "")))
    prefetch_manifest = _read_optional_json(str(artifacts.get("prefetch_manifest_v1", "")))
    residency_report = _read_optional_json(str(artifacts.get("residency_budget_report", "")))

    if not isinstance(compiled_pack, dict) or str(compiled_pack.get("schema", "")) != "atelier.renderer.pack.v2":
        print("renderer_layer_projection_failed:compiled_pack_v2_missing_or_invalid")
        return 1
    if not isinstance(stream_manifest, dict) or str(stream_manifest.get("schema", "")) != "atelier.renderer.stream_manifest.v1":
        print("renderer_layer_projection_failed:stream_manifest_v1_missing_or_invalid")
        return 1
    if not isinstance(prefetch_manifest, dict) or str(prefetch_manifest.get("schema", "")) != "atelier.renderer.stream_prefetch_manifest.v1":
        print("renderer_layer_projection_failed:prefetch_manifest_v1_missing_or_invalid")
        return 1

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
    node_index: dict[str, dict[str, Any]] = {}
    if isinstance(nodes_raw, list):
        for row in nodes_raw:
            if isinstance(row, dict):
                k = row.get("node_key")
                if isinstance(k, str) and k != "":
                    node_index[k] = row
    edge_index: set[tuple[str, str, str]] = set()
    if isinstance(edges_raw, list):
        for row in edges_raw:
            if not isinstance(row, dict):
                continue
            frm = row.get("from_node_id")
            to = row.get("to_node_id")
            kind = row.get("edge_kind")
            if isinstance(frm, str) and isinstance(to, str) and isinstance(kind, str):
                edge_index.add((frm, to, kind))

    pack_id = str(compiled_pack.get("pack_id", ""))
    compile_hash = str((compiled_pack.get("compile", {}) or {}).get("compile_hash", ""))
    stream_hash = str(stream_manifest.get("manifest_sha256", ""))
    prefetch_hash = _canonical_hash(prefetch_manifest)
    report_hash = _canonical_hash(report_obj)
    residency_hash = _canonical_hash(residency_report)
    go = bool(report_obj.get("go", False))
    recursion_profile = {
        "model": "labyr_nth.linear_recurrence.v1",
        "reference_key": pack_id,
        "reference_coeff_bp": reference_coeff_bp,
        "recursion_coeff_bp": recursion_coeff_bp,
        "coefficient_sum_bp": reference_coeff_bp + recursion_coeff_bp,
        "stable_if_sum_le_10000": bool(reference_coeff_bp + recursion_coeff_bp <= 10000),
    }

    layers: list[tuple[int, str, dict[str, Any]]] = [
        (
            1,
            f"renderer.input.{report_hash[:16]}",
            {
                "kind": "renderer.input",
                "source": report_obj.get("inputs", {}),
                "report_hash": report_hash,
            },
        ),
        (
            2,
            f"renderer.pack.v2.{pack_id}",
            {
                "kind": "renderer.pack.v2",
                "pack_id": pack_id,
                "compile_hash": compile_hash,
                "pack_sha256": (compiled_pack.get("hashes", {}) or {}).get("pack_sha256", ""),
            },
        ),
        (
            3,
            f"renderer.stream.v1.{stream_hash[:24]}",
            {
                "kind": "renderer.stream.v1",
                "manifest_sha256": stream_hash,
                "chunk_count": (stream_manifest.get("stats", {}) or {}).get("chunk_count", 0),
                "partition": stream_manifest.get("partition", {}),
                "hotset": stream_manifest.get("hotset", {}),
            },
        ),
        (
            4,
            f"renderer.prefetch.v1.{prefetch_hash[:24]}",
            {
                "kind": "renderer.prefetch.v1",
                "max_ring": prefetch_manifest.get("max_ring", 0),
                "chunk_count": prefetch_manifest.get("chunk_count", 0),
                "prefetch_hash": prefetch_hash,
            },
        ),
        (
            5,
            f"renderer.validation.{compile_hash[:16]}",
            {
                "kind": "renderer.validation",
                "checks": [c for c in report_obj.get("checks", []) if isinstance(c, dict)],
                "failed_count": (report_obj.get("summary", {}) or {}).get("failed_count", 0),
            },
        ),
        (
            6,
            f"renderer.residency.report.{residency_hash[:16]}",
            {
                "kind": "renderer.residency.report",
                "report_hash": residency_hash,
                "report": residency_report if isinstance(residency_report, dict) else {},
            },
        ),
        (
            7,
            f"renderer.budget.status.{pack_id}",
            {
                "kind": "renderer.budget.status",
                "ok": bool((residency_report or {}).get("ok", False)) if isinstance(residency_report, dict) else False,
                "violation_count": (residency_report.get("violation_count", 0) if isinstance(residency_report, dict) else 0),
                "recursion_profile": recursion_profile,
            },
        ),
        (
            8,
            f"renderer.toolchain.gonogo.{pack_id}",
            {
                "kind": "renderer.toolchain.gonogo",
                "go": go,
                "summary": report_obj.get("summary", {}),
                "artifacts": report_obj.get("artifacts", {}),
                "recursion_profile": recursion_profile,
            },
        ),
        (
            9,
            f"renderer.state.candidate.{pack_id}",
            {
                "kind": "renderer.state",
                "state": "candidate",
                "pack_id": pack_id,
                "go": go,
                "recursion_profile": recursion_profile,
            },
        ),
        (
            10,
            f"renderer.state.approved.{pack_id}",
            {
                "kind": "renderer.state",
                "state": "approved" if go else "rejected",
                "pack_id": pack_id,
                "go": go,
                "recursion_profile": recursion_profile,
            },
        ),
        (
            11,
            f"renderer.state.active.{pack_id}",
            {
                "kind": "renderer.state",
                "state": "active" if bool(args.activate and go) else "staged",
                "pack_id": pack_id,
                "go": go,
                "activate_requested": bool(args.activate),
                "recursion_profile": recursion_profile,
            },
        ),
    ]

    created_nodes: list[str] = []
    reused_nodes: list[str] = []
    node_id_by_key: dict[str, str] = {}
    for layer_index, node_key, payload in layers:
        row, created = _ensure_layer_node(
            client=client,
            workspace_id=workspace_id,
            layer_index=layer_index,
            node_key=node_key,
            payload=payload,
            node_index=node_index,
        )
        node_id = str(row.get("id", ""))
        node_id_by_key[node_key] = node_id
        if created:
            created_nodes.append(node_key)
        else:
            reused_nodes.append(node_key)

    # Ensure function store binding entry exists.
    function_id = str(args.function_id)
    function_version = str(args.function_version)
    function_signature = "renderer_stream_execute(pack_id:str, stream_manifest:str, prefetch_manifest:str) -> dict"
    function_body = (
        "resolve active layer-11 state; load layer-3 stream + layer-4 prefetch; "
        "materialize selected chunk window; return runtime payload"
    )
    function_created = False
    if isinstance(funcs_raw, list):
        found = [
            f
            for f in funcs_raw
            if isinstance(f, dict)
            and str(f.get("function_id", "")) == function_id
            and str(f.get("version", "")) == function_version
        ]
        if len(found) == 0:
            client.post_json(
                "/v1/game/functions",
                {
                    "workspace_id": workspace_id,
                    "function_id": function_id,
                    "version": function_version,
                    "signature": function_signature,
                    "body": function_body,
                    "metadata": {
                        "kind": "djinn.renderer.binding",
                        "pack_id": pack_id,
                    },
                },
            )
            function_created = True

    l12_key = f"djinn.function.{function_id}.{function_version}"
    l12_payload = {
        "kind": "djinn.function.binding",
        "function": {
            "function_id": function_id,
            "version": function_version,
            "signature": function_signature,
        },
        "binding": {
            "pack_id": pack_id,
            "stream_manifest_sha256": stream_hash,
            "prefetch_manifest_hash": prefetch_hash,
            "active": bool(args.activate and go),
            "recursion_profile": recursion_profile,
        },
        "state_requirements": {
            "required_layer_11_state": "active" if bool(args.activate and go) else "staged",
            "required_go": bool(go),
        },
    }
    l12_row, l12_created = _ensure_layer_node(
        client=client,
        workspace_id=workspace_id,
        layer_index=12,
        node_key=l12_key,
        payload=l12_payload,
        node_index=node_index,
    )
    l12_id = str(l12_row.get("id", ""))
    if l12_created:
        created_nodes.append(l12_key)
    else:
        reused_nodes.append(l12_key)
    node_id_by_key[l12_key] = l12_id

    created_edges = 0
    layer_keys = [key for _, key, _ in layers]
    for i in range(len(layer_keys) - 1):
        from_id = node_id_by_key[layer_keys[i]]
        to_id = node_id_by_key[layer_keys[i + 1]]
        if _ensure_layer_edge(
            client=client,
            workspace_id=workspace_id,
            from_node_id=from_id,
            to_node_id=to_id,
            edge_kind="state.transition",
            metadata={"phase": i + 1},
            edge_index=edge_index,
        ):
            created_edges += 1
    if _ensure_layer_edge(
        client=client,
        workspace_id=workspace_id,
        from_node_id=node_id_by_key[layer_keys[-1]],
        to_node_id=l12_id,
        edge_kind="function.binds",
        metadata={"function_id": function_id, "version": function_version},
        edge_index=edge_index,
    ):
        created_edges += 1

    output = {
        "id": "renderer_layer_projection.report.v1",
        "workspace_id": workspace_id,
        "pack_id": pack_id,
        "go": go,
        "activate": bool(args.activate),
        "function_binding": {
            "function_id": function_id,
            "version": function_version,
            "function_store_created": function_created,
            "layer_12_node_key": l12_key,
            "layer_12_node_id": l12_id,
        },
        "recursion_profile": recursion_profile,
        "created_node_keys": created_nodes,
        "reused_node_keys": reused_nodes,
        "created_edge_count": created_edges,
    }
    output_path = _resolve_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print("renderer_layer_projection_ok")
    print(f"- pack_id:{pack_id}")
    print(f"- created_nodes:{len(created_nodes)}")
    print(f"- reused_nodes:{len(reused_nodes)}")
    print(f"- created_edges:{created_edges}")
    print(f"- layer12:{l12_key}")
    print(f"- coeff_bp:{reference_coeff_bp}:{recursion_coeff_bp}")
    print(f"- report:{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
