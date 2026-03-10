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

Set real values (DB URL, admin gate code, CORS). If your public site is on `quantumquackery.org` and the service host is `atelier-api.quantumquackery.com`, include both origins in `CORS_ALLOWED_ORIGINS`. If the API talks to the kernel over a private/internal network, set `KERNEL_INTERNAL_BASE_URL` and leave `KERNEL_BASE_URL` as the public fallback.

If you are serving the shop landing page from a new subdomain (for example `shop.quantumquackery.org`), point that DNS record to the API host and set:

- `PUBLIC_WEBSITE_URL` (for the main site)
- `PUBLIC_ATELIER_URL` (for the Atelier host)
- `PUBLIC_SHOP_URL` (canonical shop host used for absolute shop links)
- `SHOP_WORKSPACE_ID` (workspace that owns shop content)
- `SHOP_CONTENT_API_URL` (API base URL for pulling shop content from the kernel)
- `SHOP_DISTRIBUTION_ID` (optional: fetch shop base URL/workspace from the distribution registry)
- `SHOP_REGISTRY_URL` (optional: base URL hosting `/public/distributions/registry`)
- `SHOP_LINK_*` (optional: per-section CTA override links)
- `SHOP_CHECKOUT_*` (optional: per-section checkout links)
- `STRIPE_SECRET_KEY` (server-side secret key for Checkout)
- `STRIPE_SUCCESS_URL` (redirect target after successful payment)
- `STRIPE_CANCEL_URL` (redirect target after cancel)
- `STRIPE_WEBHOOK_SECRET` (signature verification for Stripe webhooks)
- `STRIPE_PRICE_*` (price IDs per section, used to create Checkout sessions)
- `COMMISSION_RATE_*` (commission rate per section, decimal)
- `TAX_RATE_*` (tax rate per section, decimal)
- Add the shop subdomain to `CORS_ALLOWED_ORIGINS` if your frontend will call the API.

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

If you deploy this API on Render, set a real `DATABASE_URL`. The default local fallback points to `127.0.0.1`, which does not exist on Render and will leave `/ready` failing and `/health` degraded. For multi-service deployments, also consider setting:

- `KERNEL_INTERNAL_BASE_URL` for private service-to-service calls
- `KERNEL_CONNECT_RETRIES`
- `KERNEL_CONNECT_BACKOFF_MS`

The API now prefers `KERNEL_INTERNAL_BASE_URL` when present, retries kernel probes with backoff, and logs a startup kernel probe result without failing process startup.
