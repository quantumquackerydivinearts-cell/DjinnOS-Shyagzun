# Atelier API

FastAPI boundary for Atelier business infrastructure.

## Rules

- Requires actor + capability headers.
- Requires artisan/workshop identity + workshop scope headers.
- Talks to kernel only via `KernelClient`.
- No semantic inference, no direct CEG mutation.
- Postgres-backed business domain for CRM, booking, lessons, and modules.

Required headers on protected routes:

- `X-Atelier-Actor`
- `X-Atelier-Capabilities`
- `X-Artisan-Id`
- `X-Artisan-Role` (`apprentice|artisan|senior_artisan|steward`)
- `X-Workshop-Id`
- `X-Workshop-Scopes` (comma list; e.g. `scene:*,workspace:*`)

## Postgres + Alembic

Environment variable:

- `DATABASE_URL` (default: `postgresql+psycopg://atelier:atelier@127.0.0.1:5432/atelier`)

Run migration:

```bash
python -m alembic -c apps/atelier-api/alembic.ini upgrade head
```

## Run

```bash
python -m uvicorn atelier_api.main:app --host 127.0.0.1 --port 9000 --app-dir apps/atelier-api
```

## Auth Modes

Environment variables:

- AUTH_MODE (legacy|mixed|token_required, default: mixed)
- AUTH_TOKEN_SECRET (HMAC secret for bearer token signing; set a real secret outside local dev)

Behavior:

- legacy: requires legacy X-Atelier-* and artisan/workshop headers on protected routes.
- mixed: accepts either bearer token claims or legacy headers. If both are present, bearer claims are preferred.
- 	oken_required: requires Authorization: Bearer <token> and rejects legacy-only auth.

Bearer token claims currently include actor, capabilities, artisan identity, role, workshop identity, and workshop scopes.
