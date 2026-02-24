from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .assertions import evaluate_assertion
from .canonical import canonical_hash
from .http_client import HttpCallError, call
from .interpolate import interpolate
from .jsonpath import extract


def run_conformance(base_url: str, conformance_path: str) -> None:
    spec = _load_spec(conformance_path)
    _read_canonical_rules(spec)
    tests = _require_list(spec.get("tests"), "tests")
    variables = _initial_variables(spec)

    failed = False
    for test_obj in tests:
        test = _require_mapping(test_obj, "test")
        name = _test_name(test)
        status = _require_str(test.get("status"), f"{name}.status")
        if status == "pending":
            print(f"PASS {name} (pending)")
            continue
        if status != "required":
            raise RuntimeError(f"{name}: unknown status {status!r}")

        try:
            _run_test(base_url, test, variables)
            print(f"PASS {name}")
        except Exception as exc:
            failed = True
            print(f"FAIL {name} ({exc})")

    if failed:
        raise RuntimeError("Conformance failed")


def _load_spec(conformance_path: str) -> Dict[str, Any]:
    with open(conformance_path, "r", encoding="utf-8") as fh:
        obj: Any = json.load(fh)
    if not isinstance(obj, dict):
        raise RuntimeError("Conformance file root must be object")
    return obj


def _read_canonical_rules(spec: Mapping[str, Any]) -> Dict[str, Any]:
    canonicalization = spec.get("canonicalization")
    if isinstance(canonicalization, dict):
        return dict(canonicalization)
    return {}


def _initial_variables(spec: Mapping[str, Any]) -> Dict[str, Any]:
    vars_obj = spec.get("vars")
    if isinstance(vars_obj, dict):
        return dict(vars_obj)
    return {}


def _test_name(test: Mapping[str, Any]) -> str:
    id_obj = test.get("id")
    name_obj = test.get("name")
    if isinstance(id_obj, str) and isinstance(name_obj, str):
        return f"{id_obj} {name_obj}"
    if isinstance(id_obj, str):
        return id_obj
    raise RuntimeError("test.id must be string")


def _run_test(base_url: str, test: Mapping[str, Any], variables: Dict[str, Any]) -> None:
    steps = _require_list(test.get("steps"), "test.steps")
    for step_obj in steps:
        step = _require_mapping(step_obj, "step")
        repeat_obj = step.get("repeat", 1)
        repeat = _require_int(repeat_obj, "step.repeat")
        if repeat < 1:
            raise RuntimeError("step.repeat must be >= 1")
        for _ in range(repeat):
            _run_step(base_url, step, variables)


def _run_step(base_url: str, step: Mapping[str, Any], variables: Dict[str, Any]) -> None:
    call_obj = step.get("call")
    if call_obj is None:
        response: Dict[str, Any] = {"__http_status__": 200}
        _evaluate_assertions(step, response, variables)
        return

    call_map = _require_mapping(call_obj, "step.call")
    method = _require_str(call_map.get("method"), "step.call.method")
    raw_path = _require_str(call_map.get("path"), "step.call.path")
    path_obj = interpolate(raw_path, variables)
    if not isinstance(path_obj, str):
        raise RuntimeError("Interpolated path must be string")
    path = path_obj

    body: Optional[Dict[str, Any]] = None
    if "body" in call_map:
        interpolated = interpolate(call_map.get("body"), variables)
        body = _require_mapping(interpolated, "step.call.body")

    assertions = _assertions(step)
    expects_http_status = any(
        isinstance(a, dict) and isinstance(a.get("type"), str) and a.get("type") == "http_status"
        for a in assertions
    )

    response_obj: Dict[str, Any]
    try:
        response_obj = call(base_url, method, path, body)
        response_obj["__http_status__"] = 200
    except HttpCallError as exc:
        if not expects_http_status:
            raise
        response_obj = dict(exc.response_json) if exc.response_json is not None else {}
        response_obj["__http_status__"] = exc.status_code

    _enforce_canonical_order(response_obj)
    _apply_save(step, response_obj, variables)
    _evaluate_assertions(step, response_obj, variables)


def _assertions(step: Mapping[str, Any]) -> List[Dict[str, Any]]:
    assertions_obj = step.get("assert", [])
    assertions_list = _require_list(assertions_obj, "step.assert")
    out: List[Dict[str, Any]] = []
    for item in assertions_list:
        out.append(_require_mapping(item, "assertion"))
    return out


def _apply_save(step: Mapping[str, Any], response: Dict[str, Any], variables: Dict[str, Any]) -> None:
    save_obj = step.get("save")
    if save_obj is None:
        return
    save = _require_mapping(save_obj, "step.save")
    for var_name, rule_obj in save.items():
        if isinstance(rule_obj, str):
            path_obj = interpolate(rule_obj, variables)
            if not isinstance(path_obj, str):
                raise RuntimeError(f"save.{var_name}: interpolated path must be string")
            values = extract(path_obj, response)
            if not values:
                raise RuntimeError(f"save.{var_name}: no values at path {path_obj!r}")
            variables[var_name] = values[0]
            continue

        rule = _require_mapping(rule_obj, f"save.{var_name}")
        canonical_path = _require_str(rule.get("canonical_hash"), f"save.{var_name}.canonical_hash")
        values = extract(canonical_path, response)
        if not values:
            raise RuntimeError(f"save.{var_name}: no values at canonical_hash path {canonical_path!r}")
        value = values[0]
        if "exclude_metadata_keys_from" in rule:
            exclude_obj = interpolate(rule.get("exclude_metadata_keys_from"), variables)
            excluded = _to_str_list(exclude_obj, f"save.{var_name}.exclude_metadata_keys_from")
            value = _strip_metadata_keys(value, excluded)
        variables[var_name] = canonical_hash(value)


def _evaluate_assertions(step: Mapping[str, Any], response: Dict[str, Any], variables: Dict[str, Any]) -> None:
    for assertion in _assertions(step):
        evaluate_assertion(assertion, response, variables)


def _enforce_canonical_order(response: Mapping[str, Any]) -> None:
    if "frontiers" in response:
        frontiers = _require_list(response.get("frontiers"), "response.frontiers")
        ids: List[str] = []
        for frontier_obj in frontiers:
            frontier = _require_mapping(frontier_obj, "response.frontier")
            ids.append(_require_str(frontier.get("id"), "response.frontier.id"))
        if ids != sorted(ids):
            raise RuntimeError("frontiers are not sorted by id asc")

    if "events" in response:
        _assert_events_sorted(response.get("events"), "response.events")
    if "edges" in response:
        _assert_edges_sorted(response.get("edges"), "response.edges")

    ceg_obj = response.get("ceg")
    if isinstance(ceg_obj, dict):
        if "events" in ceg_obj:
            _assert_events_sorted(ceg_obj.get("events"), "response.ceg.events")
        if "edges" in ceg_obj:
            _assert_edges_sorted(ceg_obj.get("edges"), "response.ceg.edges")


def _assert_events_sorted(events_obj: Any, label: str) -> None:
    events = _require_list(events_obj, label)
    keys: List[Tuple[int, str, str]] = []
    for event_obj in events:
        event = _require_mapping(event_obj, f"{label}.event")
        at = _require_mapping(event.get("at"), f"{label}.event.at")
        tick = _require_int(at.get("tick"), f"{label}.event.at.tick")
        kind = _require_str(event.get("kind"), f"{label}.event.kind")
        event_id = _require_str(event.get("id"), f"{label}.event.id")
        keys.append((tick, kind, event_id))
    if keys != sorted(keys):
        raise RuntimeError(f"{label} are not sorted by (tick, kind, id)")


def _assert_edges_sorted(edges_obj: Any, label: str) -> None:
    edges = _require_list(edges_obj, label)
    keys: List[Tuple[str, str, str]] = []
    for edge_obj in edges:
        edge = _require_mapping(edge_obj, f"{label}.edge")
        from_event = _require_str(edge.get("from_event"), f"{label}.edge.from_event")
        to_event = _require_str(edge.get("to_event"), f"{label}.edge.to_event")
        edge_type = _require_str(edge.get("type"), f"{label}.edge.type")
        keys.append((from_event, to_event, edge_type))
    if keys != sorted(keys):
        raise RuntimeError(f"{label} are not sorted by (from_event, to_event, type)")


def _strip_metadata_keys(obj: Any, excluded: Sequence[str]) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for key, value in obj.items():
            if key == "metadata" and isinstance(value, dict):
                md: Dict[str, Any] = {}
                for mk, mv in value.items():
                    if mk in excluded:
                        continue
                    md[mk] = _strip_metadata_keys(mv, excluded)
                out[key] = md
            else:
                out[key] = _strip_metadata_keys(value, excluded)
        return out
    if isinstance(obj, list):
        return [_strip_metadata_keys(item, excluded) for item in obj]
    return obj


def _to_str_list(value: Any, label: str) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if not isinstance(item, str):
                raise RuntimeError(f"{label} must be str or list[str]")
            out.append(item)
        return out
    raise RuntimeError(f"{label} must be str or list[str]")


def _require_mapping(value: Any, label: str) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    raise RuntimeError(f"{label} must be object")


def _require_list(value: Any, label: str) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    raise RuntimeError(f"{label} must be list")


def _require_str(value: Any, label: str) -> str:
    if isinstance(value, str):
        return value
    raise RuntimeError(f"{label} must be string")


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{label} must be int")
    if isinstance(value, int):
        return value
    raise RuntimeError(f"{label} must be int")


def main() -> int:
    parser = argparse.ArgumentParser(description="DjinnOS reference conformance runner")
    parser.add_argument("--base-url", required=True, help="Base URL of kernel service")
    parser.add_argument("--file", required=True, help="Conformance JSON path")
    args = parser.parse_args()

    run_conformance(args.base_url, args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
