from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    kernel_base_url: str
    kernel_internal_base_url: str
    database_url: str
    admin_gate_code: str
    admin_gate_bypass: bool
    auth_mode: str
    auth_token_secret: str
    required_capability_header: str
    required_actor_header: str
    cors_allowed_origins: tuple[str, ...]
    kernel_connect_retries: int
    kernel_connect_backoff_ms: int
    public_website_url: str
    public_atelier_url: str
    shop_workspace_id: str


def _parse_origins(raw: str) -> tuple[str, ...]:
    parts = [item.strip() for item in raw.split(",")]
    return tuple(item for item in parts if item)


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    return value in ("1", "true", "yes", "on")


def load_settings() -> Settings:
    return Settings(
        kernel_base_url=os.getenv("KERNEL_BASE_URL", "http://127.0.0.1:8000"),
        kernel_internal_base_url=os.getenv("KERNEL_INTERNAL_BASE_URL", "").strip(),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://atelier:atelier@127.0.0.1:5432/atelier",
        ),
        admin_gate_code=os.getenv("ADMIN_GATE_CODE", "STEWARD_DEV_GATE"),
        admin_gate_bypass=_parse_bool(os.getenv("ADMIN_GATE_BYPASS", "false")),
        auth_mode=os.getenv("AUTH_MODE", "mixed").strip().lower(),
        auth_token_secret=os.getenv("AUTH_TOKEN_SECRET", "DEV_ONLY_CHANGE_ME"),
        required_capability_header="X-Atelier-Capabilities",
        required_actor_header="X-Atelier-Actor",
        cors_allowed_origins=_parse_origins(
            os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173,capacitor://localhost,http://localhost,https://shop.quantumquackery.org",
            )
        ),
        kernel_connect_retries=max(1, int(os.getenv("KERNEL_CONNECT_RETRIES", "4").strip() or "4")),
        kernel_connect_backoff_ms=max(0, int(os.getenv("KERNEL_CONNECT_BACKOFF_MS", "400").strip() or "400")),
        public_website_url=os.getenv("PUBLIC_WEBSITE_URL", "https://www.quantumquackery.org").strip(),
        public_atelier_url=os.getenv("PUBLIC_ATELIER_URL", "https://atelier-api.quantumquackery.com").strip(),
        shop_workspace_id=os.getenv("SHOP_WORKSPACE_ID", "").strip(),
    )
