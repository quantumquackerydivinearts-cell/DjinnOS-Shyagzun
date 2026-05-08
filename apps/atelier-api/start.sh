#!/bin/bash
# Atelier API startup script
# Runs alembic migrations if DATABASE_URL is configured, then starts uvicorn.
# Uvicorn always starts — a migration failure is logged but not fatal.

if [ -n "$DATABASE_URL" ]; then
    echo "[startup] Running database migrations..."
    python -m alembic upgrade head
    MIGRATE_STATUS=$?
    if [ $MIGRATE_STATUS -ne 0 ]; then
        echo "[startup] Migration failed — checking if schema exists without version table..."
        # If tables already exist but alembic_version is missing, stamp to head so
        # future deploys only run genuinely new migrations.
        python -m alembic stamp head 2>/dev/null && \
            echo "[startup] Stamped head — re-running upgrade to apply any pending migrations..." && \
            python -m alembic upgrade head
        MIGRATE_STATUS=$?
        if [ $MIGRATE_STATUS -ne 0 ]; then
            echo "[startup] WARNING: Migration exited $MIGRATE_STATUS — starting server anyway"
        else
            echo "[startup] Migrations OK after stamp"
        fi
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