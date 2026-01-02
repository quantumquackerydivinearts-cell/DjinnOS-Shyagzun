import json
from pathlib import Path
from typing import Dict, Any, Optional

from .http_client import HttpClient
from .canonical_json import canonical_hash
from .assertions import (
    assert_equals,
    assert_exists,
    assert_contains,
    assert_not_contains,
    assert_count_equals,
    assert_count_gte,
)
from .errors import ConformanceError
from .jsonpath import extract


class ConformanceRunner:
    def __init__(self, base_url: str, spec_path: Path) -> None:
        self.client: HttpClient = HttpClient(base_url)
        self.spec: Dict[str, Any] = json.loads(
            spec_path.read_text(encoding="utf-8")
        )
        self.vars: Dict[str, Any] = {}

    def run(self) -> None:
        for test in self.spec["tests"]:
            if test.get("status") == "pending":
                print(f"SKIP {test['id']} (pending)")
                continue

            print(f"RUN {test['id']} — {test['name']}")
            for step in test["steps"]:
                self.run_step(step)

    def run_step(self, step: Dict[str, Any]) -> None:
        call: Dict[str, Any] = step["call"]
        body: Optional[Any] = None

        if "body" in call:
            body = self.interpolate(call["body"])

        response: Any = self.client.call(
            call["method"],
            call["path"],
            body,
        )

        if "save" in step:
            self.save_vars(step["save"], response)

        for assertion in step.get("assert", []):
            self.evaluate_assertion(assertion, response)

    def interpolate(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self.interpolate(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.interpolate(v) for v in obj]
        if isinstance(obj, str):
            for k, v in self.vars.items():
                obj = obj.replace(f"{{{{{k}}}}}", str(v))
        return obj

    def save_vars(self, mappings: Dict[str, str], response: Any) -> None:
        for var, path in mappings.items():
            values = extract(response, path)
            if not values:
                raise ConformanceError(f"Save failed: {path}")
            self.vars[var] = values[0]

    def evaluate_assertion(self, assertion: Dict[str, Any], response: Any) -> None:
        assertion_type: str = assertion["type"]

        if assertion_type == "equals":
            values = extract(response, assertion["path"])
            assert_equals(values[0], assertion["value"])

        elif assertion_type == "exists":
            values = extract(response, assertion["path"])
            assert_exists(values)

        elif assertion_type == "contains":
            values = extract(response, assertion["path"])
            assert_contains(values, assertion["value"])

        elif assertion_type == "not_contains":
            values = extract(response, assertion["path"])
            assert_not_contains(values, assertion["value"])

        elif assertion_type == "count_equals":
            values = extract(response, assertion["path"])
            assert_count_equals(values, assertion["value"])

        elif assertion_type == "count_gte":
            values = extract(response, assertion["path"])
            assert_count_gte(values, assertion["value"])

        else:
            raise ConformanceError(f"Unknown assertion type: {assertion_type}")
