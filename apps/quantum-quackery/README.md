# Quantum Quackery — Full Stack Configuration Guide

## Directory map (what goes where in C:\DjinnOS\apps\apps)

```
C:\DjinnOS\apps\apps\
├── atelier-api\                ← FastAPI on Render
│   └── atelier_api\
│       └── main.py             ← Add CORS origins from atelier-api-cors-patch.py
│
├── atelier-desktop\            ← Electron + React/Vite desktop app
│   ├── index.html              ← NEW: Vite entry point (replaces nothing, add this)
│   ├── package.json            ← REPLACE with new version (adds Vite + electron-builder)
│   ├── vite.config.js          ← NEW: add this
│   ├── .env.development        ← NEW: add this
│   ├── .env.production         ← NEW: add this
│   ├── electron\
│   │   ├── main.js             ← REPLACE with new version (Vite-aware, adds IPC)
│   │   └── preload.js          ← NEW: add this
│   └── src\
│       ├── main.jsx            ← NEW: React entry point
│       └── App.jsx             ← KEEP your existing App.jsx, unchanged
│
└── quantum-quackery\           ← Static site on Cloudflare Pages
    ├── index.html              ← REPLACE with new version (API-wired)
    ├── _headers                ← NEW: Cloudflare edge headers
    └── _redirects              ← NEW: Cloudflare redirects
```

---

## Step 1 — Atelier Desktop (make App.jsx actually run)

```bash
cd C:\DjinnOS\apps\apps\atelier-desktop

# Install dependencies (first time only)
npm install

# Development: Vite dev server + Electron side by side
npm run electron:dev

# Production build
npm run electron:build
# Output goes to dist-electron\
```

**How it works now:**
- In dev, Electron loads `http://localhost:5173` (Vite HMR)
- In prod, Electron loads `dist/index.html` (built bundle)
- `App.jsx` is transpiled by Vite — JSX works
- All API calls go through `window.atelierAPI.*` (preload bridge)
- FS access is sandboxed to `C:\DjinnOS\apps\`

**Wiring App.jsx to the new API bridge:**

Anywhere in App.jsx where you have:
```js
const data = await apiCall("/v1/game/runtime/tick", "POST", body);
```

In Electron (desktop), `window.atelierAPI` is available:
```js
const isElectron = typeof window.atelierAPI !== "undefined";
const result = isElectron
  ? await window.atelierAPI.tick(body)
  : await fetch(`${import.meta.env.VITE_API_URL}/v1/game/runtime/tick`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(r => r.json());
```

Or wrap it once in a utility:
```js
// src/api.js
const BASE = import.meta.env.VITE_API_URL;
const isElectron = typeof window.atelierAPI !== "undefined";

export async function apiCall(path, method = "GET", body = null) {
  if (isElectron) {
    const { data } = await window.atelierAPI.call(method, path, body);
    return data;
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}
```

---

## Step 2 — Landing Page (Cloudflare Pages)

The `quantum-quackery/` folder is your Cloudflare Pages source.

**Cloudflare Pages settings:**
- Build command: *(none — it's static HTML)*
- Build output directory: `/` (root)
- Root directory: `quantum-quackery`

**What the new index.html does:**
- Polls `/ready` on your Render API → lights the status dot green/red
- Fetches `/public/guild/artisans` → renders the Guild Hall roster
- Falls back gracefully if the API is offline

**Deploy:**
```bash
# Option A: Push to GitHub, Cloudflare Pages auto-deploys
git add quantum-quackery/
git commit -m "wire landing page to API"
git push

# Option B: Wrangler CLI
npx wrangler pages deploy quantum-quackery --project-name=quantum-quackery
```

---

## Step 3 — API CORS (Render)

Open `atelier_api/main.py` and find your `CORSMiddleware` call.
Add these origins to the `allow_origins` list:

```python
"https://quantumquackery.org",
"https://www.quantumquackery.org",
```

Then redeploy on Render (push to your connected branch).

---

## Step 4 — New API endpoints (merge into main.py)

The new endpoints (tick, compile_cobra, validate_content, etc.)
are in the separate `atelier-api/` folder from this session.

**Fastest merge path:**
1. Copy `atelier_api/routers/game.py` into your existing `atelier_api/` folder
2. Copy `atelier_api/services/` folder contents alongside your existing services
3. In your existing `main.py`, add at the bottom of your router includes:
   ```python
   from .routers.game import router as game_router
   app.include_router(game_router)
   ```
4. The new routes sit under `/v1/game/*` — they won't conflict with anything
   already in your 4582-line main.py because your existing routes use
   different prefixes.

---

## Environment variables on Render

Set these in your Render service dashboard (Settings → Environment):

| Key | Value |
|-----|-------|
| `SECRET_KEY` | 32+ char random string |
| `WAND_MASTER_SECRET` | 32+ char random string |
| `ENVIRONMENT` | `production` |
| `PYTHON_PATH` | *(leave unset — uses sys.executable automatically)* |

---

## The full request path

```
User browser
  → quantumquackery.org (Cloudflare Pages CDN)
    → index.html loads
    → JS calls https://atelier-api.quantumquackery.com/ready
      → Cloudflare DNS (proxy enabled — orange cloud)
        → Render service
          → FastAPI main.py
          → Response cached at Cloudflare edge (if you add Cache rules)

Electron desktop app
  → window.atelierAPI.tick(body)
    → preload.js IPC
      → main.js ipcMain.handle("api:call")
        → fetch https://atelier-api.quantumquackery.com/v1/game/runtime/tick
          → Render FastAPI
          → tick_engine.py applies events server-side
          → lineage.py records to 12-layer store
          → Response returns to Electron renderer
```
