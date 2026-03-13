from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .interpolate import interpolate
from .jsonpath import extract


def evaluate_assertion(assertion: Dict[str, Any], response: Dict[str, Any], variables: Dict[str, Any]) -> None:
    atype_obj = assertion.get("type")
    if not isinstance(atype_obj, str):
        raise AssertionError("assertion.type must be a string")
    atype = atype_obj

    if atype == "http_status":
        _assert_http_status(assertion, response)
        return

    if atype == "equals" and "path" not in assertion and "left" in assertion and "right" in assertion:
        _assert_equals_lr(assertion, variables)
        return

    path_obj = interpolate(assertion.get("path"), variables)
    if not isinstance(path_obj, str):
        raise AssertionError("assertion.path must resolve to string")
    values = extract(path_obj, response)

    if atype == "equals":
        _assert_equals(assertion, values, variables)
        return
    if atype == "not_equals":
        _assert_not_equals(assertion, values, variables)
        return
    if atype == "exists":
        _assert_exists(path_obj, values)
        return
    if atype == "contains":
        _assert_contains(assertion, values, variables)
        return
    if atype == "not_contains":
        _assert_not_contains(assertion, values, variables)
        return
    if atype == "contains_any":
        _assert_contains_any(assertion, values, variables)
        return
    if atype == "count_equals":
        _assert_count_equals(assertion, values)
        return
    if atype == "count_gte":
        _assert_count_gte(assertion, values)
        return
    if atype == "equals_subset_except":
        _assert_equals_subset_except(assertion, values, variables)
        return

    raise AssertionError(f"Unsupported assertion type: {atype}")


def _assert_http_status(assertion: Mapping[str, Any], response: Mapping[str, Any]) -> None:
    expected_obj = assertion.get("value")
    actual_obj = response.get("__http_status__")
    if not isinstance(expected_obj, int) or isinstance(expected_obj, bool):
        raise AssertionError("http_status assertion value must be int")
    if not isinstance(actual_obj, int):
        raise AssertionError("http_status not available in response")
    if actual_obj != expected_obj:
        raise AssertionError(f"http_status failed: expected={expected_obj} actual={actual_obj}")


def _assert_equals_lr(assertion: Mapping[str, Any], variables: Dict[str, Any]) -> None:
    left = interpolate(assertion.get("left"), variables)
    right = interpolate(assertion.get("right"), variables)
    if left != right:
        raise AssertionError(f"equals failed: left={left!r} right={right!r}")


def _assert_equals(assertion: Mapping[str, Any], values: Sequence[Any], variables: Dict[str, Any]) -> None:
    expected = interpolate(assertion.get("value"), variables)
    if len(values) == 0:
        raise AssertionError("equals failed: no values extracted")
    actual = values[0]
    if actual != expected:
        raise AssertionError(f"equals failed: expected={expected!r} actual={actual!r}")


def _assert_not_equals(assertion: Mapping[str, Any], values: Sequence[Any], variables: Dict[str, Any]) -> None:
    expected = interpolate(assertion.get("value"), variables)
    if len(values) == 0:
        raise AssertionError("not_equals failed: no values extracted")
    actual = values[0]
    if actual == expected:
        raise AssertionError(f"not_equals failed: actual equals {expected!r}")


def _assert_exists(path: str, values: Sequence[Any]) -> None:
    if len(values) == 0:
        raise AssertionError(f"exists failed: no values for path {path!r}")


def _normalize(values: Sequence[Any]) -> Sequence[Any]:
    if len(values) == 1 and isinstance(values[0], list):
        return values[0]
    return values


def _assert_contains(assertion: Mapping[str, Any], values: Sequence[Any], variables: Dict[str, Any]) -> None:
    expected = interpolate(assertion.get("value"), variables)
    pool = _normalize(values)
    if expected not in pool:
        raise AssertionError(f"contains failed: {expected!r} not in {pool!r}")


def _assert_not_contains(assertion: Mapping[str, Any], values: Sequence[Any], variables: Dict[str, Any]) -> None:
    forbidden = interpolate(assertion.get("value"), variables)
    pool = _normalize(values)
    if forbidden in pool:
        raise AssertionError(f"not_contains failed: {forbidden!r} found in {pool!r}")


def _assert_contains_any(assertion: Mapping[str, Any], values: Sequence[Any], variables: Dict[str, Any]) -> None:
    expected_values_obj = interpolate(assertion.get("values"), variables)
    if not isinstance(expected_values_obj, list):
        raise AssertionError("contains_any expects list in assertion.values")
    pool = _normalize(values)
    if not any(v in pool for v in expected_values_obj):
        raise AssertionError(f"contains_any failed: none of {expected_values_obj!r} present in {pool!r}")


def _assert_count_equals(assertion: Mapping[str, Any], values: Sequence[Any]) -> None:
    expected_obj = assertion.get("value")
    if not isinstance(expected_obj, int) or isinstance(expected_obj, bool):
        raise AssertionError("count_equals value must be int")
    actual = len(values)
    if actual != expected_obj:
        raise AssertionError(f"count_equals failed: expected={expected_obj} actual={actual}")


def _assert_count_gte(assertion: Mapping[str, Any], values: Sequence[Any]) -> None:
    expected_obj = assertion.get("value")
    if not isinstance(expected_obj, int) or isinstance(expected_obj, bool):
        raise AssertionError("count_gte value must be int")
    actual = len(values)
    if actual < expected_obj:
        raise AssertionError(f"count_gte failed: expected>={expected_obj} actual={actual}")


def _assert_equals_subset_except(
    assertion: Mapping[str, Any],
    values: Sequence[Any],
    variables: Dict[str, Any],
) -> None:
    if len(values) == 0:
        raise AssertionError("equals_subset_except failed: no values extracted")
    current_obj = values[0]
    if not isinstance(current_obj, dict):
        raise AssertionError("equals_subset_except requires current object")

    compare_to_saved = interpolate(assertion.get("compare_to_saved"), variables)
    if not isinstance(compare_to_saved, dict):
        raise AssertionError("equals_subset_except compare_to_saved must resolve to object")

    allowed_obj = assertion.get("allowed_differences")
    if not isinstance(allowed_obj, list):
        raise AssertionError("equals_subset_except allowed_differences must be list")
    allowed: List[str] = []
    for item in allowed_obj:
        if not isinstance(item, str):
            raise AssertionError("equals_subset_except allowed_differences must be list[str]")
        allowed.append(item)
    allowed_set = set(allowed)

    current_keys = set(current_obj.keys())
    expected_keys = set(compare_to_saved.keys())
    if current_keys != expected_keys:
        raise AssertionError(
            "equals_subset_except failed: key mismatch "
            f"current={sorted(current_keys)!r} expected={sorted(expected_keys)!r}"
        )

    for key in sorted(current_keys):
        if key in allowed_set:
            continue
        if current_obj[key] != compare_to_saved[key]:
            raise AssertionError(
                f"equals_subset_except failed at key {key!r}: "
                f"expected={compare_to_saved[key]!r} actual={current_obj[key]!r}"
            )
