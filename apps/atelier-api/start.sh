#!/bin/bash
# Atelier API startup script
# Runs alembic migrations if DATABASE_URL is configured, then starts uvicorn.
# Uvicorn always starts — a migration failure is logged but not fatal.

if [ -n "$DATABASE_URL" ]; then
    echo "[startup] Running database migrations..."

    # Check DB state: if schema exists but alembic_version table is missing,
    # stamp to the last known-good migration (0040) before running upgrade
    # so that only genuinely new migrations (0041+) get applied.
    python - <<'PYEOF'
import sys
try:
    from atelier_api.db import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        has_ver = conn.execute(text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name='alembic_version')"
        )).scalar()
        has_schema = conn.execute(text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name='workspaces')"
        )).scalar()
    if has_schema and not has_ver:
        sys.exit(2)   # needs stamp-then-upgrade
    sys.exit(0)       # fresh DB or already versioned
except Exception as e:
    print(f"[startup] db-check error: {e}", flush=True)
    sys.exit(0)
PYEOF
    DB_STATE=$?

    if [ $DB_STATE -eq 2 ]; then
        echo "[startup] Schema exists without alembic_version — stamping 0040 then upgrading..."
        python -m alembic stamp 0040_supra_librix
        STAMP_STATUS=$?
        if [ $STAMP_STATUS -ne 0 ]; then
            echo "[startup] WARNING: stamp failed ($STAMP_STATUS) — attempting full upgrade anyway"
        fi
    fi

    python -m alembic upgrade head
    MIGRATE_STATUS=$?
    if [ $MIGRATE_STATUS -ne 0 ]; then
        echo "[startup] WARNING: Migration exited $MIGRATE_STATUS — starting server anyway"
    else
        echo "[startup] Migrations OK"
    fi
else
    echo "[startup] DATABASE_URL not set — skipping migrations"
fi

echo "[startup] Starting uvicorn on port ${PORT:-9000}..."
exec python -m uvicorn atelier_api.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-9000}"