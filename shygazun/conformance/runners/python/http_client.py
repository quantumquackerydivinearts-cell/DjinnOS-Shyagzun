from __future__ import annotations

from typing import Any, Dict, Optional

import requests  # type: ignore[import-untyped]

from .errors import HttpError


def call(
    base_url: str,
    method: str,
    path: str,
    body: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    response = requests.request(method=method, url=url, json=body)
    payload: Optional[Dict[str, Any]]
    try:
        maybe_json: Any = response.json()
        payload = maybe_json if isinstance(maybe_json, dict) else None
    except ValueError:
        payload = None

    if response.status_code != 200:
        raise HttpError(
            method=method,
            path=path,
            status_code=response.status_code,
            response_text=response.text,
            response_json=payload,
        )

    if payload is None:
        raise HttpError(
            method=method,
            path=path,
            status_code=response.status_code,
            response_text="Expected JSON object response body",
            response_json=None,
        )

    return payload
