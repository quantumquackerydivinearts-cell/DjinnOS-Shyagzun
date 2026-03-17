# ============================================================
# CORS PATCH for atelier_api/main.py
# ============================================================
# Your existing main.py has CORSMiddleware already.
# Replace or merge your existing cors_origins list with this.
# The critical additions are the Cloudflare Pages domain and
# the Render service URL.
#
# Find your existing:
#     app.add_middleware(CORSMiddleware, ...)
# and replace the allow_origins list with the one below.
# ============================================================

CORS_ORIGINS = [
    # Local development
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",

    # Cloudflare Pages — landing page
    "https://quantumquackery.org",
    "https://www.quantumquackery.org",

    # Cloudflare Pages preview deployments (branch deploys)
    # Format: https://<branch>.<project>.pages.dev
    # Add your Cloudflare Pages project name below:
    # "https://*.quantum-quackery.pages.dev",  # wildcard doesn't work in CORS
    # Instead, add specific preview URLs as needed during development.

    # Atelier web app
    "https://atelier.quantumquackery.com",

    # Render service self-reference (for health checks)
    "https://djinnos-shyagzun-atelier-api.onrender.com",
]

# In your main.py, the middleware call should look like this:
#
# from fastapi.middleware.cors import CORSMiddleware
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=CORS_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
#     allow_headers=["*"],
#     expose_headers=["X-Process-Time-Ms"],
# )
