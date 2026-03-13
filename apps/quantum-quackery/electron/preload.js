// atelier-desktop/electron/preload.js
// Exposes a typed, sandboxed API bridge to the renderer.
// The renderer calls window.atelierAPI.* — never raw fetch or Node APIs.
// All actual network/FS calls happen in main.js via ipcMain.handle.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("atelierAPI", {
  // ── API calls → FastAPI server ─────────────────────────────────────────────
  call: (method, path, body) =>
    ipcRenderer.invoke("api:call", { method, path, body }),

  get: (path) =>
    ipcRenderer.invoke("api:call", { method: "GET", path }),

  post: (path, body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path, body }),

  // Convenience wrappers for the endpoints we built
  ready: () =>
    ipcRenderer.invoke("api:call", { method: "GET", path: "/ready" }),

  tick: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/runtime/tick", body }),

  compileCobra: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/scene/compile_cobra", body }),

  validateContent: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/renderer/validate_content", body }),

  syncTables: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/renderer/sync_tables", body }),

  emitSceneGraph: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/renderer/scene_graph", body }),

  emitPlacements: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/renderer/placements", body }),

  emitHeadlessQuest: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/quests/headless", body }),

  emitMeditation: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/meditations", body }),

  shygazunInterpret: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/shygazun/interpret", body }),

  daisyBodyplan: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/daisy/bodyplan", body }),

  consumeInbox: (body) =>
    ipcRenderer.invoke("api:call", { method: "POST", path: "/v1/game/runtime/inbox/consume", body }),

  lineageTail: (workspaceId, n = 50) =>
    ipcRenderer.invoke("api:call", {
      method: "GET",
      path: `/v1/game/lineage/${encodeURIComponent(workspaceId)}?n=${n}`,
    }),

  // ── Studio FS (gated to DjinnOS/apps/) ────────────────────────────────────
  fs: {
    read:    (filePath)          => ipcRenderer.invoke("fs:readFile",  filePath),
    write:   (filePath, content) => ipcRenderer.invoke("fs:writeFile", filePath, content),
    listDir: (dirPath)           => ipcRenderer.invoke("fs:listDir",   dirPath),
  },
});
