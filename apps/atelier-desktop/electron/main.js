const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const fs = require("fs/promises");
const path = require("path");

const isDev = !app.isPackaged;
const STUDIO_FILE_LIMIT = 1024 * 1024;

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
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1320,
    height: 860,
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
