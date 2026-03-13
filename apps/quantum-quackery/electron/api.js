// atelier-desktop/src/api.js
//
// Drop-in replacement for wherever App.jsx currently does:
//   fetch("http://127.0.0.1:9000/...")
//
// Usage — replace existing fetch calls with:
//   import { apiCall } from "./api.js";
//   const data = await apiCall("/v1/atelier/place", "POST", body);
//
// In Electron: routes through preload.js IPC bridge (no CORS, no port issue)
// In browser (Vite dev): routes through vite.config.js proxy to localhost:8000
// In browser (production): routes through VITE_API_URL env var

const IS_ELECTRON = typeof window !== "undefined" && typeof window.atelierAPI !== "undefined";
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function apiCall(path, method = "GET", body = null, headers = {}) {
  // Electron path — goes through preload IPC, bypasses CORS entirely
  if (IS_ELECTRON) {
    const result = await window.atelierAPI.call(method, path, body);
    if (!result.ok) {
      throw new Error(`API ${method} ${path} → ${result.status}: ${result.error || "unknown error"}`);
    }
    return result.data;
  }

  // Browser path — direct fetch with env-var base URL
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      // Forward the Atelier capability headers your existing API expects
      "X-Atelier-Actor":        "desktop-user",
      "X-Atelier-Capabilities": "kernel.place",
      "X-Artisan-Id":           "artisan-desktop",
      "X-Workshop-Id":          "workshop-primary",
      "X-Workshop-Scopes":      "scene:*,workspace:*",
      ...headers,
    },
    body: body !== null ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${method} ${path} → ${res.status}: ${text}`);
  }

  return res.json();
}

// Convenience wrappers matching existing App.jsx call patterns
export const apiGet  = (path, headers)       => apiCall(path, "GET",    null,  headers);
export const apiPost = (path, body, headers) => apiCall(path, "POST",   body,  headers);
export const apiPut  = (path, body, headers) => apiCall(path, "PUT",    body,  headers);
export const apiDel  = (path, headers)       => apiCall(path, "DELETE", null,  headers);
