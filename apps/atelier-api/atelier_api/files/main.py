"""
atelier_api/main.py
FastAPI application entry point for the Quantum Quackery Atelier API.
"""
from __future__ import annotations

import sys
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from .core.config import get_settings
from .routers import game

settings = get_settings()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info(
        "atelier_api_starting",
        version=settings.app_version,
        environment=settings.environment,
        python=sys.executable,          # always sys.executable — never hardcoded path
    )
    # Ensure lineage store directory exists
    settings.lineage_store_path.mkdir(parents=True, exist_ok=True)
    yield
    log.info("atelier_api_shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    # Disable default /docs in production if desired
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Any) -> Any:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time-Ms"] = f"{elapsed * 1000:.1f}"
    return response


# ── Global exception handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    log.error("unhandled_exception", path=str(request.url), error=str(exc))
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"ok": False, "error": "internal_server_error", "detail": str(exc)},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(game.router)


# ── Health / readiness ────────────────────────────────────────────────────────
@app.get("/ready", summary="Service readiness probe")
async def ready() -> ORJSONResponse:
    return ORJSONResponse({
        "ok": True,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "python": sys.executable,
    })


@app.get("/health", summary="Health check")
async def health() -> ORJSONResponse:
    return ORJSONResponse({"ok": True, "uptime_ms": int(time.time() * 1000)})


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "atelier_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        workers=settings.workers,
    )
