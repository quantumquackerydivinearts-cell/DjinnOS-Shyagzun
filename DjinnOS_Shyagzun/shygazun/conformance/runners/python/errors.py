from __future__ import annotations

from typing import Any, Dict, Optional


class ConformanceError(Exception):
    pass


class AssertionFailure(ConformanceError):
    pass


class HttpError(ConformanceError):
    def __init__(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        response_text: str,
        response_json: Optional[Dict[str, Any]],
    ) -> None:
        super().__init__(f"{method} {path} -> {status_code}: {response_text}")
        self.method = method
        self.path = path
        self.status_code = status_code
        self.response_text = response_text
        self.response_json = response_json
