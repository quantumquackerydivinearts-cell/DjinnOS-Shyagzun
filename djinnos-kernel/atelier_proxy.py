#!/usr/bin/env python3
"""
atelier_proxy.py  —  TLS bridge for the DjinnOS kernel
=======================================================
Listens on plain HTTP port 9000. Forwards every request to the hosted
Atelier API over HTTPS. Lets the kernel reach production without a local
API process running — it connects to 10.0.2.2:9000 exactly as before.

No external packages — stdlib only.
"""
import http.server
import urllib.request
import urllib.error
import sys

UPSTREAM = "https://djinnos-shyagzun-atelier-api.onrender.com"
PORT     = 9000

# Headers that must not be forwarded upstream.
_HOP_BY_HOP = frozenset({
    "host", "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade",
})


class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def _forward(self, method: str) -> None:
        url    = UPSTREAM + self.path
        length = int(self.headers.get("Content-Length", 0) or 0)
        body   = self.rfile.read(length) if length else None

        fwd_headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in _HOP_BY_HOP
        }

        try:
            req = urllib.request.Request(url, data=body,
                                         headers=fwd_headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in _HOP_BY_HOP:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())

        except urllib.error.HTTPError as exc:
            body = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as exc:
            msg = str(exc).encode()
            self.send_response(502)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):    self._forward("GET")
    def do_POST(self):   self._forward("POST")
    def do_PUT(self):    self._forward("PUT")
    def do_DELETE(self): self._forward("DELETE")
    def do_PATCH(self):  self._forward("PATCH")

    def log_message(self, fmt, *args):
        pass  # stay quiet — UART output is the user's focus


if __name__ == "__main__":
    try:
        server = http.server.HTTPServer(("", PORT), ProxyHandler)
    except OSError as exc:
        print(f"[atelier-proxy] port {PORT} in use — is the local API running? ({exc})",
              flush=True)
        sys.exit(1)

    print(f"[atelier-proxy] :{PORT} → {UPSTREAM}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("[atelier-proxy] stopped", flush=True)