# Release Targets

Ko's Labyrnth Atelier ships in two intentionally different forms.

## Local Atelier Bundle

Use this for end users.

- Target flag: `local`
- Output name: `atelier-suite-<version>.zip`
- Database: `SQLite`
- Kernel: bundled with the installer payload
- Python deps: bundled offline wheelhouse
- Startup model: launcher starts local kernel and API automatically
- Goal: single-user, offline-first, minimal support burden

This is the default packaging target because it has the fewest moving parts on random Windows machines.

## Hosted Atelier Stack

Use this for managed or shared deployments.

- Target flag: `hosted`
- Output name: `atelier-hosted-suite-<version>.zip`
- Database: `PostgreSQL`
- Kernel: external managed service
- Python deps: managed by deployment environment
- Startup model: infra launches services; desktop points at hosted endpoints
- Goal: stronger operations, multi-user coordination, controlled upgrades

Hosted mode assumes you control deployment infrastructure and can handle:

- `DATABASE_URL`
- Alembic migrations
- service supervision
- secrets management
- TLS / reverse proxy / firewall policy

## Packaging

Examples:

```powershell
py scripts/package_suite.ps1 -Target local
py scripts/package_suite.ps1 -Target hosted
```

## Practical Rule

If the user is downloading from your site or GitHub Releases and expects one-click setup, give them the `local` target.

If you are running Atelier as an administered service for one or more users, use the `hosted` target.
