from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    kernel_base_url: str
    database_url: str
    admin_gate_code: str
    admin_gate_bypass: bool
    required_capability_header: str
    required_actor_header: str
    cors_allowed_origins: tuple[str, ...]


def _parse_origins(raw: str) -> tuple[str, ...]:
    parts = [item.strip() for item in raw.split(",")]
    return tuple(item for item in parts if item)


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    return value in ("1", "true", "yes", "on")


def load_settings() -> Settings:
    return Settings(
        kernel_base_url=os.getenv("KERNEL_BASE_URL", "http://127.0.0.1:8000"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://atelier:atelier@127.0.0.1:5432/atelier",
        ),
        admin_gate_code=os.getenv("ADMIN_GATE_CODE", "STEWARD_DEV_GATE"),
        admin_gate_bypass=_parse_bool(os.getenv("ADMIN_GATE_BYPASS", "false")),
        required_capability_header="X-Atelier-Capabilities",
        required_actor_header="X-Atelier-Actor",
        cors_allowed_origins=_parse_origins(
            os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173,capacitor://localhost,http://localhost",
            )
        ),
    )
