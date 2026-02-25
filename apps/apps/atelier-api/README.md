# Atelier API

FastAPI boundary for Atelier business infrastructure.

## Rules

- Requires actor + capability headers.
- Requires artisan/workshop identity + workshop scope headers.
- Talks to kernel only via `KernelClient`.
- No semantic inference, no direct CEG mutation.

Required headers on protected routes:

- `X-Atelier-Actor`
- `X-Atelier-Capabilities`
- `X-Artisan-Id`
- `X-Artisan-Role` (`apprentice|artisan|senior_artisan|steward`)
- `X-Workshop-Id`
- `X-Workshop-Scopes` (comma list; e.g. `scene:*,workspace:*`)

## Run

```bash
python -m uvicorn atelier_api.main:app --host 127.0.0.1 --port 9000 --app-dir apps/atelier-api
```
