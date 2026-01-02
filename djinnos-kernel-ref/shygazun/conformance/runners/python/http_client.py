from typing import Any, Optional
import requests
from .errors import HttpError

class HttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def call(
        self,
        method: str,
        path: str,
        body: Optional[Any] = None,
    ) -> Any:
        url = self.base_url + path
        resp = requests.request(method, url, json=body)

        if resp.status_code >= 400:
            raise HttpError(f"{method} {path} → {resp.status_code}: {resp.text}")

        return resp.json()

