from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    kernel_base_url: str
    required_capability_header: str
    required_actor_header: str


def load_settings() -> Settings:
    return Settings(
        kernel_base_url=os.getenv("KERNEL_BASE_URL", "http://127.0.0.1:8000"),
        required_capability_header="X-Atelier-Capabilities",
        required_actor_header="X-Atelier-Actor",
    )

