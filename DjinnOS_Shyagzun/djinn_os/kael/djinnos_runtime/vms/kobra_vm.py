"""
djinnos_runtime/vms/kobra_vm.py
================================
KobraVM — the Kobra abstract machine as a registered DjinnOS runtime VM.

This is the deployment entry point for Kobra execution in the DjinnOS stack.
The canonical implementation lives in shygazun.kernel.kobra — this file
makes it operational: runnable, addressable, and observable.

Per the DjinnOS charter: Kael is where instances run, not where they are
defined. This file runs the VM; shygazun.kernel.kobra defines it.

HTTP API
--------
  GET  /health               → { ok, vm, version, kobra }
  POST /eval                 → evaluate a Kobra token sequence
    body: { tokens: [str, ...], input?: any }
    resp: { ok: bool, value: any, error?: str }
  POST /parse                → parse a Kobra source document
    body: { source: str }
    resp: { ok: bool, result: str, error?: str }
  POST /evaluate             → full document evaluation via KobraEvaluator
    body: { source: str }
    resp: { ok: bool, document: obj, error?: str }

Usage
-----
  python kobra_vm.py                # port 7000
  python kobra_vm.py --port 7001
  uvicorn kobra_vm:app --port 7000  # as ASGI app
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Resolve the shygazun package root: vms/ → djinnos_runtime/ → kael/ → djinn_os/ → DjinnOS_Shyagzun/
_HERE = Path(__file__).resolve().parent
_SHYGAZUN_ROOT = _HERE.parents[3]   # DjinnOS_Shyagzun/
if str(_SHYGAZUN_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHYGAZUN_ROOT))

try:
    from shygazun.kernel.kobra.vm import KobraVM, KaelShi, KaelKe
    from shygazun.kernel.kobra import parse as kobra_parse, KobraEvaluator
    _KOBRA_OK = True
    _KOBRA_ERR = ""
except ImportError as _e:
    _KOBRA_OK = False
    _KOBRA_ERR = str(_e)

VERSION = "0.1.0"
VM_NAME = "KobraVM"

# ── ASGI app ──────────────────────────────────────────────────────────────────

try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import uvicorn
    _ASGI_OK = True
except ImportError:
    _ASGI_OK = False


def build_app() -> "FastAPI":
    app = FastAPI(title=VM_NAME, version=VERSION, docs_url="/docs")

    @app.get("/health")
    def health():
        return {
            "ok":      _KOBRA_OK,
            "vm":      VM_NAME,
            "version": VERSION,
            "kobra":   _KOBRA_OK,
            "error":   _KOBRA_ERR or None,
        }

    @app.post("/eval")
    async def eval_tokens(body: dict):
        if not _KOBRA_OK:
            return JSONResponse(503, {"ok": False, "error": _KOBRA_ERR})
        tokens = body.get("tokens", [])
        input_val = body.get("input", None)
        if not isinstance(tokens, list):
            return {"ok": False, "error": "tokens must be a list"}
        vm = KobraVM({})
        result = vm.exec([str(t) for t in tokens], input_val)
        if isinstance(result, KaelShi):
            return {"ok": True, "value": result.value}
        return {"ok": False, "error": result.reason, "value": result.value}

    @app.post("/parse")
    async def parse_source(body: dict):
        if not _KOBRA_OK:
            return JSONResponse(503, {"ok": False, "error": _KOBRA_ERR})
        source = body.get("source", "")
        if not isinstance(source, str):
            return {"ok": False, "error": "source must be a string"}
        try:
            result = kobra_parse(source)
            return {"ok": True, "result": repr(result)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @app.post("/evaluate")
    async def evaluate_document(body: dict):
        if not _KOBRA_OK:
            return JSONResponse(503, {"ok": False, "error": _KOBRA_ERR})
        source = body.get("source", "")
        if not isinstance(source, str):
            return {"ok": False, "error": "source must be a string"}
        try:
            ev = KobraEvaluator()
            doc = ev.evaluate(source)
            return {
                "ok":       True,
                "document": {
                    "clusters": [
                        {
                            "id": c.cluster_id,
                            "sections": [
                                {
                                    "lo":        s.lo_address,
                                    "header":    s.header,
                                    "artifacts": [
                                        {"key": a.key, "tokens": a.tokens}
                                        for a in s.artifacts
                                    ],
                                }
                                for s in c.sections
                            ],
                        }
                        for c in doc.clusters
                    ]
                },
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return app


# Expose as module-level `app` for uvicorn direct use
if _ASGI_OK:
    app = build_app()


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    if not _ASGI_OK:
        print("fastapi + uvicorn required: pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)

    ap = argparse.ArgumentParser(description=f"{VM_NAME} service")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7000)
    ap.add_argument("--reload", action="store_true")
    args = ap.parse_args()

    uvicorn.run(
        "kobra_vm:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(_HERE),
    )


if __name__ == "__main__":
    main()