from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from .errors import AssertionFailure


def _first(values: Sequence[Any], label: str) -> Any:
    if not values:
        raise AssertionFailure(f"{label}: no values extracted")
    return values[0]


def _pool(values: Sequence[Any]) -> Sequence[Any]:
    if len(values) == 1 and isinstance(values[0], list):
        return values[0]
    return values


def equals(values: Sequence[Any], expected: Any) -> None:
    actual = _first(values, "equals")
    if actual != expected:
        raise AssertionFailure(f"equals failed: expected={expected!r} actual={actual!r}")


def not_equals(values: Sequence[Any], expected: Any) -> None:
    actual = _first(values, "not_equals")
    if actual == expected:
        raise AssertionFailure(f"not_equals failed: both={actual!r}")


def exists(values: Sequence[Any]) -> None:
    if len(values) == 0:
        raise AssertionFailure("exists failed: value was not found")


def contains(values: Sequence[Any], expected: Any) -> None:
    items = _pool(values)
    if expected not in items:
        raise AssertionFailure(f"contains failed: expected member {expected!r} not in {items!r}")


def not_contains(values: Sequence[Any], forbidden: Any) -> None:
    items = _pool(values)
    if forbidden in items:
        raise AssertionFailure(f"not_contains failed: forbidden member {forbidden!r} present in {items!r}")


def contains_any(values: Sequence[Any], expected_values: Sequence[Any]) -> None:
    items = _pool(values)
    if not any(value in items for value in expected_values):
        raise AssertionFailure(
            f"contains_any failed: none of {list(expected_values)!r} present in {items!r}"
        )


def count_equals(values: Sequence[Any], count: int) -> None:
    actual = len(values)
    if actual != count:
        raise AssertionFailure(f"count_equals failed: expected={count} actual={actual}")


def count_gte(values: Sequence[Any], count: int) -> None:
    actual = len(values)
    if actual < count:
        raise AssertionFailure(f"count_gte failed: expected>={count} actual={actual}")


def all(values: Sequence[Any], predicate: Callable[[Any], bool], message: str) -> None:
    for index, value in enumerate(values):
        if not predicate(value):
            raise AssertionFailure(f"all failed at index {index}: {message}; value={value!r}")


def for_each(values: Sequence[Any], assertion: Callable[[Any], None]) -> None:
    for index, value in enumerate(values):
        try:
            assertion(value)
        except AssertionFailure as exc:
            raise AssertionFailure(f"for_each failed at index {index}: {exc}") from exc


def equals_subset_except(
    current: Mapping[str, Any],
    expected: Mapping[str, Any],
    allowed_differences: Sequence[str],
) -> None:
    allowed = set(allowed_differences)
    current_keys = set(current.keys())
    expected_keys = set(expected.keys())
    if current_keys != expected_keys:
        raise AssertionFailure(
            f"equals_subset_except failed: key sets differ current={sorted(current_keys)!r} "
            f"expected={sorted(expected_keys)!r}"
        )
    for key in sorted(current_keys):
        if key in allowed:
            continue
        if current[key] != expected[key]:
            raise AssertionFailure(
                f"equals_subset_except failed: disallowed difference at key {key!r}; "
                f"expected={expected[key]!r} actual={current[key]!r}"
            )
