// atelier-desktop/electron/main.js
// Loads Vite dev server in development, built dist/ in production.
// Never enables nodeIntegration. All API calls go through preload.js bridge.

const { app, BrowserWindow, ipcMain, shell } = require("electron");
const path = require("path");

const IS_DEV = process.env.NODE_ENV === "development" || !app.isPackaged;
const VITE_DEV_URL = "http://localhost:5173";
const API_URL = process.env.VITE_API_URL || "https://atelier-api.quantumquackery.com";

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      contextIsolation: true,
      sandbox: false,           // must be false to allow preload script
      nodeIntegration: false,   // never true
      preload: path.join(__dirname, "preload.js"),
    },
    // Remove default menu bar in production
    autoHideMenuBar: !IS_DEV,
    title: "Quantum Quackery Atelier",
    backgroundColor: "#0a0a0f",
  });

  if (IS_DEV) {
    win.loadURL(VITE_DEV_URL);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  // Open external links in default browser, not Electron
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http")) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });
}

// ── IPC: API bridge ───────────────────────────────────────────────────────────
// The preload exposes window.atelierAPI which calls these handlers.
// This keeps the renderer sandboxed — it never makes raw Node/net calls.

ipcMain.handle("api:call", async (_event, { method, path: apiPath, body }) => {
  const url = `${API_URL}${apiPath}`;
  try {
    const res = await fetch(url, {
      method: method || "GET",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, status: 0, data: null, error: err.message };
  }
});

// Studio FS operations — only paths inside DjinnOS apps are accessible
const ALLOWED_FS_ROOT = path.join(
  process.env.USERPROFILE || process.env.HOME || "",
  "DjinnOS",
  "apps"
);

ipcMain.handle("fs:readFile", async (_event, filePath) => {
  const fs = require("fs").promises;
  const resolved = path.resolve(filePath);
  if (!resolved.startsWith(ALLOWED_FS_ROOT)) {
    return { ok: false, error: "path_not_allowed" };
  }
  try {
    const content = await fs.readFile(resolved, "utf8");
    return { ok: true, content };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

ipcMain.handle("fs:writeFile", async (_event, filePath, content) => {
  const fs = require("fs").promises;
  const resolved = path.resolve(filePath);
  if (!resolved.startsWith(ALLOWED_FS_ROOT)) {
    return { ok: false, error: "path_not_allowed" };
  }
  try {
    await fs.writeFile(resolved, content, "utf8");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

ipcMain.handle("fs:listDir", async (_event, dirPath) => {
  const fs = require("fs").promises;
  const resolved = path.resolve(dirPath);
  if (!resolved.startsWith(ALLOWED_FS_ROOT)) {
    return { ok: false, error: "path_not_allowed" };
  }
  try {
    const entries = await fs.readdir(resolved, { withFileTypes: true });
    return {
      ok: true,
      entries: entries.map((e) => ({
        name: e.name,
        isDir: e.isDirectory(),
        path: path.join(resolved, e.name),
      })),
    };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

// ── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
