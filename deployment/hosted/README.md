# Hosted Atelier Stack

This deployment path is for managed infrastructure, not end-user local installs.

## Services

- `postgres`: persistent PostgreSQL database
- `kernel`: Shygazun kernel service
- `api`: Atelier API backed by PostgreSQL and connected to the kernel

## Quick Start

1. Copy `.env.example` to `.env`
2. Set `POSTGRES_PASSWORD`
3. Set `AUTH_TOKEN_SECRET`
4. Run:

```bash
docker compose -f deployment/hosted/docker-compose.yml --env-file deployment/hosted/.env up --build -d
```

5. Verify:

```bash
curl http://127.0.0.1:8000/events
curl http://127.0.0.1:9000/health
```

## Desktop Client

Point the desktop client at the hosted services:

- `api_base_url=http://<host>:9000`
- `kernel_base_url=http://<host>:8000`

Do not use the local setup wizard for this deployment target.

## Notes

- API container runs Alembic migrations on startup.
- This stack is intended for controlled admin environments.
- Add a reverse proxy, TLS, and real secrets before public exposure.
