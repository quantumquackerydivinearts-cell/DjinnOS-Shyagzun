# Quantum Quackery Atelier API

FastAPI server providing server-authoritative game runtime, renderer pipeline,
content validation, and asset processing for the Quantum Quackery Atelier.

## Architecture

```
atelier_api/
├── main.py                  # FastAPI app, CORS, middleware, lifespan
├── core/
│   ├── config.py            # Settings via pydantic-settings (env vars)
│   ├── database.py          # Async SQLAlchemy engine + session
│   ├── security.py          # JWT auth + wand key derivation (server-only)
│   └── lineage.py           # 12-layer append-only lineage store
├── models/
│   └── schemas.py           # All Pydantic v2 request/response schemas
├── routers/
│   └── game.py              # All 14 game/renderer endpoints
└── services/
    ├── cobra.py             # Cobra/Shygazun parser
    ├── tick_engine.py       # Server-authoritative state tick engine
    ├── atlas.py             # PNG tile atlas creation + sprite animator
    └── daisy.py             # Daisy Tongue bodyplan generator
```

## Security model

- **Wand keys never reach the client.** All derivation in `core/security.py` is server-side only.
- **No localStorage crypto.** The client stores only UI preferences.
- **Deterministic replay.** Every tick is recorded in the 12-layer lineage store with a hash chain.
- **Attestation chain.** All state changes traceable via `/v1/game/lineage/{workspace_id}`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/game/runtime/tick` | Apply tick events → next state |
| POST | `/v1/game/renderer/sync_tables` | Merge renderer tables |
| POST | `/v1/game/scene/compile_cobra` | Cobra source → renderer JSON |
| POST | `/v1/game/renderer/validate_content` | Validate + bilingual trust |
| POST | `/v1/game/renderer/scene_graph` | Emit scene graph |
| POST | `/v1/game/quests/headless` | Emit headless quest |
| POST | `/v1/game/meditations` | Emit meditation |
| POST | `/v1/game/renderer/placements` | Emit scene placements |
| POST | `/v1/game/assets/atlas_from_png` | Upload PNG → atlas metadata |
| POST | `/v1/game/assets/apply_sprite_animator` | Inject animation frames |
| POST | `/v1/game/shygazun/interpret` | Shygazun → semantic summary |
| POST | `/v1/game/daisy/bodyplan` | Daisy bodyplan + voxels |
| POST | `/v1/game/runtime/inbox/consume` | Drain engine inbox |
| GET  | `/v1/game/lineage/{workspace_id}` | Lineage tail |
| GET  | `/ready` | Readiness probe |
| GET  | `/health` | Health check |

## Quick start

```bash
# 1. Create virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — set SECRET_KEY and WAND_MASTER_SECRET

# 4. Run
python -m atelier_api.main
# or
uvicorn atelier_api.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs

## Deploying to Render

1. Set the start command to:
   ```
   uvicorn atelier_api.main:app --host 0.0.0.0 --port $PORT
   ```
2. Set environment variables in the Render dashboard (never commit secrets).
3. Set `ENVIRONMENT=production` to disable /docs.
4. Use `DATABASE_URL` pointing to a PostgreSQL add-on for persistence.

## Python path fix

`core/config.py` always uses `sys.executable` for the Python path — never a hardcoded string. This means the correct virtualenv Python is always used regardless of deployment environment.

## Lineage store

The lineage store writes an NDJSON file per workspace at `./lineage_store/`.
Each record has a 12-layer structure:

| Layer | Name | Contents |
|-------|------|---------|
| 0 | raw_input | Verbatim client payload |
| 1 | validated | After schema validation |
| 2 | resolved | After ID/ref resolution |
| 3 | pre_tick | Engine state before tick |
| 4 | tick_applied | Diff produced by tick |
frt| 5 | post_tick | Engine state after tick |
| 6 | compiled | Compiled scene/cobra output |
| 7 | asset_resolved | Assets hydrated |
| 8 | signed | Attestation signatures |
| 9 | broadcast | Dispatched downstream |
| 10 | ack | Acknowledgement received |
| 11 | archived | Final archived form |

Records are SHA-256 hash-chained — tampering with any record breaks the chain.
