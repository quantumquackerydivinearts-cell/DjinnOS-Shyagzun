from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class HttpCallError(RuntimeError):
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
        self.status_code = status_code
        self.response_json = response_json


def call(base_url: str, method: str, path: str, body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = method.upper()
    if normalized not in {"GET", "POST"}:
        raise RuntimeError(f"Unsupported method: {method}")

    url = base_url.rstrip("/") + path
    response = requests.request(method=normalized, url=url, json=body if body is not None else None)

    payload: Optional[Dict[str, Any]]
    try:
        maybe_json: Any = response.json()
        payload = maybe_json if isinstance(maybe_json, dict) else None
    except ValueError:
        payload = None

    if response.status_code != 200:
        raise HttpCallError(
            method=normalized,
            path=path,
            status_code=response.status_code,
            response_text=response.text,
            response_json=payload,
        )

    if payload is None:
        raise RuntimeError(f"{normalized} {path} -> 200: response is not a JSON object")

    return payload
