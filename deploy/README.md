# Deploy Automation (API + Kernel)

This folder provides one-time setup and repeatable update scripts for hosting the stack behind one public API domain.

## Files

- `setup_server.sh`: initial server setup (packages, repo, venv, systemd, nginx).
- `update_release.sh`: pull latest code, reinstall deps, restart services.
- `.env.template`: template for `/etc/djinnos/atelier-api.env`.
- `systemd/atelier-kernel.service`: template kernel unit.
- `systemd/atelier-api.service`: template API unit.

## One-time setup (Ubuntu)

```bash
sudo bash deploy/setup_server.sh \
  --repo-url https://github.com/quantumquackerydivinearts-cell/DjinnOS-Shyagzun.git \
  --domain atelier-api.quantumquackery.com \
  --email you@quantumquackery.com
```

Then edit env file:

```bash
sudo nano /etc/djinnos/atelier-api.env
```

Set real values (DB URL, admin gate code, CORS). If your public site is on `quantumquackery.org` and the service host is `atelier-api.quantumquackery.com`, include both origins in `CORS_ALLOWED_ORIGINS`.

Restart API:

```bash
sudo systemctl restart atelier-api
```

## Update on each release

```bash
sudo bash deploy/update_release.sh
```

## Verify

```bash
curl -sSf http://127.0.0.1:8000/events > /dev/null
curl -sSf http://127.0.0.1:9000/health
curl -sSf http://127.0.0.1:9000/ready
curl -sSf https://atelier-api.quantumquackery.com/health
curl -sSf https://atelier-api.quantumquackery.com/ready
```

`/health` is process liveness and returns structured degraded status if the API is up but the database is unavailable. `/ready` is the strict readiness gate and returns non-success until the database is reachable.

## Render note

If you deploy this API on Render, set a real `DATABASE_URL`. The default local fallback points to `127.0.0.1`, which does not exist on Render and will leave `/ready` failing and `/health` degraded.
