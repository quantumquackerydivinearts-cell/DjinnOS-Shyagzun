const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const fs = require("fs/promises");
const path = require("path");

const isDev = !app.isPackaged;
const STUDIO_FILE_LIMIT = 1024 * 1024;
const STUDIO_BINARY_FILE_LIMIT = 25 * 1024 * 1024;
const APP_ICON_PATH = path.join(__dirname, "..", "public", "icon.png");

function assertWithinRoot(rootDir, targetPath) {
  const normalizedRoot = path.resolve(rootDir);
  const normalizedTarget = path.resolve(targetPath);
  if (!normalizedTarget.startsWith(normalizedRoot)) {
    throw new Error("studio_fs_scope_error");
  }
  return normalizedTarget;
}

function registerIpcHandlers() {
  ipcMain.handle("studio:choose-directory", async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory", "createDirectory"],
      title: "Select Cobra Script Folder"
    });
    if (result.canceled || result.filePaths.length === 0) {
      return { ok: false };
    }
    return { ok: true, directory: result.filePaths[0] };
  });

  ipcMain.handle("studio:list-cobra-scripts", async (_event, rootDir) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const entries = await fs.readdir(normalizedRoot, { withFileTypes: true });
    const files = entries
      .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".cobra"))
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b));
    return { ok: true, files };
  });

  ipcMain.handle("studio:list-assets-by-suffix", async (_event, rootDir, suffix) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    if (typeof suffix !== "string" || suffix.trim() === "") {
      throw new Error("studio_fs_suffix_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const normalizedSuffix = suffix.toLowerCase();
    const entries = await fs.readdir(normalizedRoot, { withFileTypes: true });
    const files = entries
      .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(normalizedSuffix))
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b));
    return { ok: true, files };
  });

  ipcMain.handle("studio:list-runtime-plans", async (_event, rootDir) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const runtimePlansRoot = assertWithinRoot(normalizedRoot, path.join(normalizedRoot, "gameplay", "runtime_plans"));
    let rootStat;
    try {
      rootStat = await fs.stat(runtimePlansRoot);
    } catch {
      return { ok: true, files: [] };
    }
    if (!rootStat.isDirectory()) {
      return { ok: true, files: [] };
    }
    const out = [];
    const stack = [{ absDir: runtimePlansRoot, relDir: "gameplay/runtime_plans" }];
    while (stack.length > 0) {
      const current = stack.pop();
      const entries = await fs.readdir(current.absDir, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory()) {
          stack.push({
            absDir: assertWithinRoot(normalizedRoot, path.join(current.absDir, entry.name)),
            relDir: `${current.relDir}/${entry.name}`.replaceAll("\\", "/"),
          });
          continue;
        }
        if (!entry.isFile() || !entry.name.toLowerCase().endsWith(".json")) {
          continue;
        }
        out.push(`${current.relDir}/${entry.name}`.replaceAll("\\", "/"));
      }
    }
    out.sort((a, b) => a.localeCompare(b));
    return { ok: true, files: out };
  });

  ipcMain.handle("studio:read-cobra-script", async (_event, rootDir, filename) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    if (typeof filename !== "string" || filename.trim() === "") {
      throw new Error("studio_fs_filename_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const absolutePath = assertWithinRoot(normalizedRoot, path.join(normalizedRoot, filename));
    const stat = await fs.stat(absolutePath);
    if (!stat.isFile()) {
      throw new Error("studio_fs_not_file");
    }
    if (stat.size > STUDIO_FILE_LIMIT) {
      throw new Error("studio_fs_file_too_large");
    }
    const content = await fs.readFile(absolutePath, "utf8");
    return { ok: true, filename: path.basename(absolutePath), content };
  });

  ipcMain.handle("studio:write-cobra-script", async (_event, rootDir, filename, content) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    if (typeof filename !== "string" || filename.trim() === "") {
      throw new Error("studio_fs_filename_required");
    }
    if (typeof content !== "string") {
      throw new Error("studio_fs_content_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const absolutePath = assertWithinRoot(normalizedRoot, path.join(normalizedRoot, filename));
    await fs.mkdir(path.dirname(absolutePath), { recursive: true });
    await fs.writeFile(absolutePath, content, "utf8");
    return { ok: true, filename: path.basename(absolutePath) };
  });

  ipcMain.handle("studio:read-text-file", async (_event, rootDir, filename) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    if (typeof filename !== "string" || filename.trim() === "") {
      throw new Error("studio_fs_filename_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const absolutePath = assertWithinRoot(normalizedRoot, path.join(normalizedRoot, filename));
    const stat = await fs.stat(absolutePath);
    if (!stat.isFile()) {
      throw new Error("studio_fs_not_file");
    }
    if (stat.size > STUDIO_FILE_LIMIT) {
      throw new Error("studio_fs_file_too_large");
    }
    const content = await fs.readFile(absolutePath, "utf8");
    return { ok: true, filename: path.basename(absolutePath), content };
  });

  ipcMain.handle("studio:write-text-file", async (_event, rootDir, filename, content) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    if (typeof filename !== "string" || filename.trim() === "") {
      throw new Error("studio_fs_filename_required");
    }
    if (typeof content !== "string") {
      throw new Error("studio_fs_content_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const absolutePath = assertWithinRoot(normalizedRoot, path.join(normalizedRoot, filename));
    await fs.mkdir(path.dirname(absolutePath), { recursive: true });
    await fs.writeFile(absolutePath, content, "utf8");
    return { ok: true, filename: path.basename(absolutePath) };
  });

  ipcMain.handle("studio:read-binary-file-base64", async (_event, rootDir, filename) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    if (typeof filename !== "string" || filename.trim() === "") {
      throw new Error("studio_fs_filename_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const absolutePath = assertWithinRoot(normalizedRoot, path.join(normalizedRoot, filename));
    const stat = await fs.stat(absolutePath);
    if (!stat.isFile()) {
      throw new Error("studio_fs_not_file");
    }
    if (stat.size > STUDIO_BINARY_FILE_LIMIT) {
      throw new Error("studio_fs_binary_file_too_large");
    }
    const bytes = await fs.readFile(absolutePath);
    return {
      ok: true,
      filename: path.basename(absolutePath),
      size: stat.size,
      base64: bytes.toString("base64"),
    };
  });

  ipcMain.handle("renderer:open-window", async (_event, payload) => {
    const view = payload && payload.view ? payload.view : "renderer-full";
    const renderWin = new BrowserWindow({
      width: 1280,
      height: 720,
      fullscreen: true,
      autoHideMenuBar: true,
      icon: APP_ICON_PATH,
      webPreferences: {
        contextIsolation: true,
        sandbox: true,
        nodeIntegration: false,
        preload: path.join(__dirname, "preload.js")
      }
    });
    if (isDev) {
      renderWin.loadURL(`http://127.0.0.1:5173/?view=${view}`);
    } else {
      renderWin.loadFile(path.join(__dirname, "..", "dist", "index.html"), { query: { view } });
    }
    return { ok: true };
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1320,
    height: 860,
    icon: APP_ICON_PATH,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js")
    }
  });

  if (isDev) {
    win.loadURL("http://127.0.0.1:5173");
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

app.whenReady().then(() => {
  registerIpcHandlers();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
