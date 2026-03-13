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
    public_shop_url: str
    shop_workspace_id: str
    stripe_secret_key: str
    stripe_success_url: str
    stripe_cancel_url: str
    stripe_webhook_secret: str
    stripe_prices: dict[str, str]
    commission_rates: dict[str, float]
    tax_rates: dict[str, float]


def _parse_origins(raw: str) -> tuple[str, ...]:
    parts = [item.strip() for item in raw.split(",")]
    return tuple(item for item in parts if item)


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    return value in ("1", "true", "yes", "on")


def _parse_float(raw: str, default: float = 0.0) -> float:
    try:
        return float(raw.strip())
    except (ValueError, AttributeError):
        return default


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
        public_shop_url=os.getenv("PUBLIC_SHOP_URL", "").strip(),
        shop_workspace_id=os.getenv("SHOP_WORKSPACE_ID", "").strip(),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", "").strip(),
        stripe_success_url=os.getenv("STRIPE_SUCCESS_URL", "").strip(),
        stripe_cancel_url=os.getenv("STRIPE_CANCEL_URL", "").strip(),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", "").strip(),
        stripe_prices={
            "consultations": os.getenv("STRIPE_PRICE_CONSULTATIONS", "").strip(),
            "licenses": os.getenv("STRIPE_PRICE_LICENSES", "").strip(),
            "catalog": os.getenv("STRIPE_PRICE_CATALOG", "").strip(),
            "custom-orders": os.getenv("STRIPE_PRICE_CUSTOM_ORDERS", "").strip(),
            "digital": os.getenv("STRIPE_PRICE_DIGITAL", "").strip(),
            "land-assessments": os.getenv("STRIPE_PRICE_LAND_ASSESSMENTS", "").strip(),
        },
        commission_rates={
            "consultations": _parse_float(os.getenv("COMMISSION_RATE_CONSULTATIONS", "0.15"), 0.15),
            "licenses": _parse_float(os.getenv("COMMISSION_RATE_LICENSES", "0.20"), 0.20),
            "catalog": _parse_float(os.getenv("COMMISSION_RATE_CATALOG", "0.18"), 0.18),
            "custom-orders": _parse_float(os.getenv("COMMISSION_RATE_CUSTOM_ORDERS", "0.20"), 0.20),
            "digital": _parse_float(os.getenv("COMMISSION_RATE_DIGITAL", "0.12"), 0.12),
            "land-assessments": _parse_float(os.getenv("COMMISSION_RATE_LAND_ASSESSMENTS", "0.10"), 0.10),
        },
        tax_rates={
            "consultations": _parse_float(os.getenv("TAX_RATE_CONSULTATIONS", "0.0"), 0.0),
            "licenses": _parse_float(os.getenv("TAX_RATE_LICENSES", "0.0"), 0.0),
            "catalog": _parse_float(os.getenv("TAX_RATE_CATALOG", "0.0"), 0.0),
            "custom-orders": _parse_float(os.getenv("TAX_RATE_CUSTOM_ORDERS", "0.0"), 0.0),
            "digital": _parse_float(os.getenv("TAX_RATE_DIGITAL", "0.0"), 0.0),
            "land-assessments": _parse_float(os.getenv("TAX_RATE_LAND_ASSESSMENTS", "0.0"), 0.0),
        },
    )
