#!/usr/bin/env python3
"""
browser_proxy.py  --  Faerie Browser HTTP proxy
================================================
Listens on plain HTTP port 8080.  Accepts HTTP-proxy-style requests
from the DjinnOS kernel where the path IS the full target URL:

    GET http://quantumquackery.org/page HTTP/1.0

Fetches the target URL over HTTPS (or HTTP) and returns the response.
No JS, no cookies, no cache -- pure pipe.

No external packages -- stdlib only.
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import sys

PORT = 8888

_HOP = frozenset({
    "host", "connection", "keep-alive", "transfer-encoding",
    "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade",
})


class FaerieProxyHandler(http.server.BaseHTTPRequestHandler):

    def _forward(self, method: str) -> None:
        path = self.path.strip()

        # Require a full URL in the path.
        if not (path.startswith("http://") or path.startswith("https://")):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Faerie proxy requires a full URL in the request path.")
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        body   = self.rfile.read(length) if length else None

        fwd = {k: v for k, v in self.headers.items() if k.lower() not in _HOP}
        fwd["User-Agent"]      = "DjinnOS/Faerie"
        # Force plaintext -- the kernel has no decompressor.
        fwd["Accept-Encoding"] = "identity"

        try:
            req = urllib.request.Request(path, data=body, headers=fwd, method=method)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    skip = {"content-encoding", "transfer-encoding"}
                    if k.lower() not in _HOP and k.lower() not in skip:
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

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

    def do_GET(self):  self._forward("GET")
    def do_POST(self): self._forward("POST")

    def log_message(self, fmt, *args):
        pass  # silent


if __name__ == "__main__":
    try:
        class ThreadedProxy(socketserver.ThreadingMixIn, http.server.HTTPServer):
            daemon_threads = True
        server = ThreadedProxy(("", PORT), FaerieProxyHandler)
    except OSError as exc:
        print(f"[faerie-proxy] port {PORT} in use ({exc})", flush=True)
        sys.exit(1)

    print(f"[faerie-proxy] :{PORT} ready  (Faerie Browser HTTP forward proxy)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("[faerie-proxy] stopped", flush=True)