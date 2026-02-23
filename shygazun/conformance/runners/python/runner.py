from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .assertions import (
    all as assert_all,
    contains,
    contains_any,
    count_equals,
    count_gte,
    equals,
    equals_subset_except,
    exists,
    for_each,
    not_contains,
    not_equals,
)
from .canonical_json import canonical_hash
from .errors import AssertionFailure, ConformanceError, HttpError
from .http_client import call
from .interpolate import interpolate
from .jsonpath import extract


class ConformanceRunner:
    def __init__(self, base_url: str, spec: Mapping[str, Any]) -> None:
        self._base_url = base_url.rstrip("/")
        self._spec = dict(spec)
        vars_obj = self._require_mapping(self._spec.get("vars"), "vars")
        self._vars: Dict[str, Any] = dict(vars_obj)
        self._results: List[Dict[str, Any]] = []

    @classmethod
    def from_file(cls, spec_path: Path, base_url_override: Optional[str] = None) -> "ConformanceRunner":
        raw = spec_path.read_text(encoding="utf-8")
        loaded: Any = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ConformanceError("Conformance spec root must be an object")
        base_url_val = loaded.get("base_url")
        if base_url_override is not None:
            base_url = base_url_override
        elif isinstance(base_url_val, str):
            base_url = base_url_val
        else:
            raise ConformanceError("base_url must be present in spec or provided by --base-url")
        return cls(base_url=base_url, spec=loaded)

    def run(self) -> Dict[str, Any]:
        tests = self._require_list(self._spec.get("tests"), "tests")
        for test_obj in tests:
            test = self._require_mapping(test_obj, "test")
            test_id = self._require_str(test.get("id"), "test.id")
            status = self._require_str(test.get("status"), f"{test_id}.status")
            if status == "pending":
                self._results.append({"id": test_id, "status": "pending", "message": "skipped pending test"})
                continue
            if status != "required":
                raise ConformanceError(f"{test_id}: unknown status {status!r}")

            try:
                self._run_test(test)
                self._results.append({"id": test_id, "status": "passed"})
            except ConformanceError as exc:
                self._results.append({"id": test_id, "status": "failed", "error": str(exc)})

        return {"results": self._results, "vars": self._vars}

    def _run_test(self, test: Mapping[str, Any]) -> None:
        test_id = self._require_str(test.get("id"), "test.id")
        steps = self._require_list(test.get("steps"), f"{test_id}.steps")
        for step_obj in steps:
            step = self._require_mapping(step_obj, f"{test_id}.step")
            repeats_raw = step.get("repeat", 1)
            repeats = self._require_int(repeats_raw, f"{test_id}.{self._step_id(step)}.repeat")
            if repeats < 1:
                raise ConformanceError(f"{test_id}.{self._step_id(step)}: repeat must be >= 1")
            for _ in range(repeats):
                self._run_step(test_id, step)

    def _run_step(self, test_id: str, step: Mapping[str, Any]) -> None:
        step_id = self._step_id(step)
        if "call" not in step:
            self._evaluate_assertions(
                test_id=test_id,
                step_id=step_id,
                assertions_obj=step.get("assert", []),
                payload={},
                http_status=None,
            )
            return

        call_obj = self._require_mapping(step.get("call"), f"{test_id}.{step_id}.call")
        method = self._require_str(call_obj.get("method"), f"{test_id}.{step_id}.call.method")
        raw_path = self._require_str(call_obj.get("path"), f"{test_id}.{step_id}.call.path")
        path = self._require_str(interpolate(raw_path, self._vars), f"{test_id}.{step_id}.call.path.interpolated")

        body: Optional[Dict[str, Any]] = None
        if "body" in call_obj:
            interpolated_body = interpolate(call_obj.get("body"), self._vars)
            body = self._require_mapping(interpolated_body, f"{test_id}.{step_id}.call.body")

        assertions_obj = step.get("assert", [])
        has_http_status_assert = self._has_http_status_assert(assertions_obj)

        http_status: Optional[int] = None
        payload: Dict[str, Any]
        try:
            payload = call(self._base_url, method, path, body)
            http_status = 200
        except HttpError as exc:
            http_status = exc.status_code
            if not has_http_status_assert:
                raise ConformanceError(f"{test_id}.{step_id}: {exc}") from exc
            payload = exc.response_json if exc.response_json is not None else {}

        self._enforce_canonical_order(payload, f"{test_id}.{step_id}")
        self._apply_saves(test_id, step_id, step.get("save"), payload)
        self._evaluate_assertions(test_id, step_id, assertions_obj, payload, http_status)

    def _apply_saves(
        self,
        test_id: str,
        step_id: str,
        save_obj: Any,
        payload: Dict[str, Any],
    ) -> None:
        if save_obj is None:
            return
        save = self._require_mapping(save_obj, f"{test_id}.{step_id}.save")
        for key, value in save.items():
            if isinstance(value, str):
                interpolated_path = interpolate(value, self._vars)
                path = self._require_str(interpolated_path, f"{test_id}.{step_id}.save.{key}")
                values = extract(path, payload)
                if not values:
                    raise ConformanceError(f"{test_id}.{step_id}.save.{key}: path {path!r} resolved empty")
                self._vars[key] = values[0]
                continue

            rule = self._require_mapping(value, f"{test_id}.{step_id}.save.{key}")
            canonical_hash_path = self._require_str(
                rule.get("canonical_hash"),
                f"{test_id}.{step_id}.save.{key}.canonical_hash",
            )
            values = extract(canonical_hash_path, payload)
            if not values:
                raise ConformanceError(
                    f"{test_id}.{step_id}.save.{key}: canonical_hash path {canonical_hash_path!r} resolved empty"
                )
            target = values[0]

            if "exclude_metadata_keys_from" in rule:
                spec_value = rule.get("exclude_metadata_keys_from")
                resolved = interpolate(spec_value, self._vars)
                keys: Sequence[str]
                if isinstance(resolved, list):
                    keys = [self._require_str(x, f"{test_id}.{step_id}.save.{key}.exclude_metadata_keys_from") for x in resolved]
                elif isinstance(resolved, str):
                    keys = [resolved]
                else:
                    raise ConformanceError(
                        f"{test_id}.{step_id}.save.{key}: exclude_metadata_keys_from must resolve to str or list[str]"
                    )
                target = self._strip_metadata_keys(target, keys)

            self._vars[key] = canonical_hash(target)

    def _evaluate_assertions(
        self,
        test_id: str,
        step_id: str,
        assertions_obj: Any,
        payload: Dict[str, Any],
        http_status: Optional[int],
    ) -> None:
        assertions = self._require_list(assertions_obj, f"{test_id}.{step_id}.assert")
        for assertion_obj in assertions:
            assertion = self._require_mapping(assertion_obj, f"{test_id}.{step_id}.assertion")
            atype = self._require_str(assertion.get("type"), f"{test_id}.{step_id}.assertion.type")
            try:
                self._evaluate_assertion(assertion, payload, http_status)
            except AssertionFailure as exc:
                raise ConformanceError(f"{test_id}.{step_id}.{atype}: {exc}") from exc

    def _evaluate_assertion(
        self,
        assertion: Mapping[str, Any],
        payload: Dict[str, Any],
        http_status: Optional[int],
    ) -> None:
        atype = self._require_str(assertion.get("type"), "assertion.type")
        if atype == "http_status":
            expected = self._require_int(assertion.get("value"), "assertion.value")
            if http_status is None:
                raise AssertionFailure("http_status failed: no HTTP call executed")
            if http_status != expected:
                raise AssertionFailure(f"http_status failed: expected={expected} actual={http_status}")
            return

        if atype == "equals" and "left" in assertion and "right" in assertion:
            left = interpolate(assertion.get("left"), self._vars)
            right = interpolate(assertion.get("right"), self._vars)
            equals([left], right)
            return

        path = self._require_str(
            interpolate(assertion.get("path"), self._vars),
            "assertion.path",
        )
        values = extract(path, payload)

        if atype == "equals":
            expected = interpolate(assertion.get("value"), self._vars)
            equals(values, expected)
            return
        if atype == "not_equals":
            expected = interpolate(assertion.get("value"), self._vars)
            not_equals(values, expected)
            return
        if atype == "exists":
            exists(values)
            return
        if atype == "contains":
            expected = interpolate(assertion.get("value"), self._vars)
            contains(values, expected)
            return
        if atype == "not_contains":
            forbidden = interpolate(assertion.get("value"), self._vars)
            not_contains(values, forbidden)
            return
        if atype == "contains_any":
            vals = self._require_list(interpolate(assertion.get("values"), self._vars), "assertion.values")
            contains_any(values, vals)
            return
        if atype == "count_equals":
            expected_count = self._require_int(assertion.get("value"), "assertion.value")
            count_equals(values, expected_count)
            return
        if atype == "count_gte":
            expected_min = self._require_int(assertion.get("value"), "assertion.value")
            count_gte(values, expected_min)
            return
        if atype == "all":
            expected = interpolate(assertion.get("value"), self._vars)
            assert_all(values, lambda v: v == expected, f"value != {expected!r}")
            return
        if atype == "for_each":
            nested = self._require_list(assertion.get("assert"), "assertion.assert")

            def evaluator(item: Any) -> None:
                for nested_obj in nested:
                    nested_assertion = self._require_mapping(nested_obj, "assertion.assert[n]")
                    nested_type = self._require_str(nested_assertion.get("type"), "assertion.assert[n].type")
                    if nested_type != "equals":
                        raise AssertionFailure(f"for_each supports nested equals only, got {nested_type!r}")
                    nested_path = self._require_str(
                        interpolate(nested_assertion.get("path"), self._vars),
                        "assertion.assert[n].path",
                    )
                    nested_values = extract(nested_path, item)
                    expected_value = interpolate(nested_assertion.get("value"), self._vars)
                    equals(nested_values, expected_value)

            for_each(values, evaluator)
            return
        if atype == "equals_subset_except":
            current = self._first_obj(values, "equals_subset_except current")
            compare_ref = interpolate(assertion.get("compare_to_saved"), self._vars)
            expected_obj = self._require_mapping(compare_ref, "equals_subset_except.compare_to_saved")
            allowed = self._require_list(assertion.get("allowed_differences"), "allowed_differences")
            allowed_keys = [self._require_str(v, "allowed_differences[]") for v in allowed]
            equals_subset_except(current, expected_obj, allowed_keys)
            return

        raise AssertionFailure(f"Unknown assertion type: {atype}")

    def _enforce_canonical_order(self, payload: Dict[str, Any], context: str) -> None:
        if "frontiers" in payload:
            frontiers = self._require_list(payload.get("frontiers"), f"{context}.frontiers")
            ids = [self._require_str(self._require_mapping(v, f"{context}.frontier").get("id"), f"{context}.frontier.id") for v in frontiers]
            if ids != sorted(ids):
                raise ConformanceError(f"{context}: frontiers must be sorted by id asc")

        if "events" in payload and "edges" in payload:
            self._assert_events_sorted(payload.get("events"), f"{context}.events")
            self._assert_edges_sorted(payload.get("edges"), f"{context}.edges")

        ceg_obj = payload.get("ceg")
        if isinstance(ceg_obj, dict):
            if "events" in ceg_obj:
                self._assert_events_sorted(ceg_obj.get("events"), f"{context}.ceg.events")
            if "edges" in ceg_obj:
                self._assert_edges_sorted(ceg_obj.get("edges"), f"{context}.ceg.edges")

    def _assert_events_sorted(self, events_obj: Any, context: str) -> None:
        events = self._require_list(events_obj, context)
        keys: List[tuple[int, str, str]] = []
        for event_obj in events:
            event = self._require_mapping(event_obj, f"{context}.event")
            at = self._require_mapping(event.get("at"), f"{context}.event.at")
            tick = self._require_int(at.get("tick"), f"{context}.event.at.tick")
            kind = self._require_str(event.get("kind"), f"{context}.event.kind")
            eid = self._require_str(event.get("id"), f"{context}.event.id")
            keys.append((tick, kind, eid))
        if keys != sorted(keys):
            raise ConformanceError(f"{context}: events must be sorted by (tick, kind, id)")

    def _assert_edges_sorted(self, edges_obj: Any, context: str) -> None:
        edges = self._require_list(edges_obj, context)
        keys: List[tuple[str, str, str]] = []
        for edge_obj in edges:
            edge = self._require_mapping(edge_obj, f"{context}.edge")
            from_event = self._require_str(edge.get("from_event"), f"{context}.edge.from_event")
            to_event = self._require_str(edge.get("to_event"), f"{context}.edge.to_event")
            etype = self._require_str(edge.get("type"), f"{context}.edge.type")
            keys.append((from_event, to_event, etype))
        if keys != sorted(keys):
            raise ConformanceError(f"{context}: edges must be sorted by (from_event, to_event, type)")

    def _has_http_status_assert(self, assertions_obj: Any) -> bool:
        if not isinstance(assertions_obj, list):
            return False
        for item in assertions_obj:
            if isinstance(item, dict) and item.get("type") == "http_status":
                return True
        return False

    def _strip_metadata_keys(self, obj: Any, keys: Sequence[str]) -> Any:
        if isinstance(obj, dict):
            out: Dict[str, Any] = {}
            for key, value in obj.items():
                if key == "metadata" and isinstance(value, dict):
                    metadata: Dict[str, Any] = {}
                    for mk, mv in value.items():
                        if mk in keys:
                            continue
                        metadata[mk] = self._strip_metadata_keys(mv, keys)
                    out[key] = metadata
                else:
                    out[key] = self._strip_metadata_keys(value, keys)
            return out
        if isinstance(obj, list):
            return [self._strip_metadata_keys(v, keys) for v in obj]
        return obj

    def _step_id(self, step: Mapping[str, Any]) -> str:
        sid = step.get("id")
        return self._require_str(sid, "step.id")

    def _require_mapping(self, value: Any, label: str) -> Dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        raise ConformanceError(f"{label} must be an object")

    def _require_list(self, value: Any, label: str) -> List[Any]:
        if isinstance(value, list):
            return list(value)
        raise ConformanceError(f"{label} must be a list")

    def _require_str(self, value: Any, label: str) -> str:
        if isinstance(value, str):
            return value
        raise ConformanceError(f"{label} must be a string")

    def _require_int(self, value: Any, label: str) -> int:
        if isinstance(value, bool):
            raise ConformanceError(f"{label} must be an integer")
        if isinstance(value, int):
            return value
        raise ConformanceError(f"{label} must be an integer")

    def _first_obj(self, values: Sequence[Any], label: str) -> Dict[str, Any]:
        if not values:
            raise AssertionFailure(f"{label}: no values extracted")
        first = values[0]
        if isinstance(first, dict):
            return dict(first)
        raise AssertionFailure(f"{label}: expected object, got {type(first).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser(description="DjinnOS conformance runner")
    parser.add_argument("--spec", required=True, help="Path to conformance.json")
    parser.add_argument("--base-url", default=None, help="Optional override for base URL")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    runner = ConformanceRunner.from_file(spec_path, args.base_url)
    summary = runner.run()
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    failed = [r for r in summary["results"] if r.get("status") == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
