const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const fs = require("fs/promises");
const path = require("path");
const { execFile } = require("child_process");

const isDev = !app.isPackaged;
const STUDIO_FILE_LIMIT = 1024 * 1024;
const STUDIO_BINARY_FILE_LIMIT = 25 * 1024 * 1024;
const STUDIO_PYTHON_TIMEOUT_MS = 15000;
const APP_ICON_PATH = path.join(__dirname, "..", "public", "icon.png");

function runtimeQuery() {
  const query = {};
  if (process.env.KOS_API_BASE && process.env.KOS_API_BASE.trim() !== "") {
    query.apiBase = process.env.KOS_API_BASE.trim();
  }
  if (process.env.KOS_KERNEL_BASE && process.env.KOS_KERNEL_BASE.trim() !== "") {
    query.kernelBase = process.env.KOS_KERNEL_BASE.trim();
  }
  return query;
}

function assertWithinRoot(rootDir, targetPath) {
  const normalizedRoot = path.resolve(rootDir);
  const normalizedTarget = path.resolve(targetPath);
  if (!normalizedTarget.startsWith(normalizedRoot)) {
    throw new Error("studio_fs_scope_error");
  }
  return normalizedTarget;
}

function execFileAsync(cmd, args, options) {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, options, (error, stdout, stderr) => {
      if (error) {
        const payload = {
          message: error.message || String(error),
          code: error.code || null,
          stdout: stdout ? String(stdout) : "",
          stderr: stderr ? String(stderr) : "",
        };
        reject(payload);
        return;
      }
      resolve({
        stdout: stdout ? String(stdout) : "",
        stderr: stderr ? String(stderr) : "",
      });
    });
  });
}

async function runPythonScript({ rootDir, sourceText, filename, timeoutMs }) {
  const normalizedRoot = path.resolve(rootDir);
  const safeFilename = filename && typeof filename === "string" && filename.trim() !== "" ? filename.trim() : `renderer_python_${Date.now()}.py`;
  const tempDir = assertWithinRoot(normalizedRoot, path.join(normalizedRoot, ".atelier_tmp"));
  const tempPath = assertWithinRoot(normalizedRoot, path.join(tempDir, safeFilename));
  await fs.mkdir(path.dirname(tempPath), { recursive: true });
  await fs.writeFile(tempPath, sourceText, "utf8");

  const env = { ...process.env, PYTHONIOENCODING: "utf-8" };
  const timeout = Math.max(1000, Number(timeoutMs || STUDIO_PYTHON_TIMEOUT_MS));
  const attempts = [
    { cmd: "py", args: ["-3", tempPath] },
    { cmd: "python", args: [tempPath] },
    { cmd: "python3", args: [tempPath] },
  ];
  let lastError = null;
  for (const attempt of attempts) {
    try {
      const result = await execFileAsync(attempt.cmd, attempt.args, { cwd: normalizedRoot, env, timeout });
      return { ok: true, command: `${attempt.cmd} ${attempt.args.join(" ")}`, stdout: result.stdout, stderr: result.stderr, tempPath };
    } catch (error) {
      if (error && error.code === "ENOENT") {
        lastError = error;
        continue;
      }
      return {
        ok: false,
        command: `${attempt.cmd} ${attempt.args.join(" ")}`,
        stdout: error && error.stdout ? error.stdout : "",
        stderr: error && error.stderr ? error.stderr : error && error.message ? error.message : "python_exec_failed",
        tempPath,
      };
    }
  }
  return {
    ok: false,
    command: "",
    stdout: "",
    stderr: lastError && lastError.message ? lastError.message : "python_not_found",
    tempPath,
  };
}

function registerIpcHandlers() {
  ipcMain.handle("studio:choose-directory", async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory", "createDirectory"],
      title: "Select Kobra Script Folder"
    });
    if (result.canceled || result.filePaths.length === 0) {
      return { ok: false };
    }
    return { ok: true, directory: result.filePaths[0] };
  });

  ipcMain.handle("studio:list-kobra-scripts", async (_event, rootDir) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    const normalizedRoot = path.resolve(rootDir);
    const entries = await fs.readdir(normalizedRoot, { withFileTypes: true });
    const files = entries
      .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".ko"))
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

  ipcMain.handle("studio:read-kobra-script", async (_event, rootDir, filename) => {
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

  ipcMain.handle("studio:write-kobra-script", async (_event, rootDir, filename, content) => {
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

  ipcMain.handle("studio:run-python", async (_event, rootDir, sourceText, options) => {
    if (typeof rootDir !== "string" || rootDir.trim() === "") {
      throw new Error("studio_fs_root_required");
    }
    if (typeof sourceText !== "string" || sourceText.trim() === "") {
      throw new Error("studio_python_source_required");
    }
    if (sourceText.length > STUDIO_FILE_LIMIT) {
      throw new Error("studio_python_source_too_large");
    }
    const opts = options && typeof options === "object" ? options : {};
    const timeoutMs = Number(opts.timeoutMs || STUDIO_PYTHON_TIMEOUT_MS);
    const filename = typeof opts.filename === "string" ? opts.filename : "";
    return await runPythonScript({ rootDir, sourceText, filename, timeoutMs });
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
    const query = { ...runtimeQuery(), view };
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
      const params = new URLSearchParams(query).toString();
      renderWin.loadURL(`http://127.0.0.1:5173/?${params}`);
    } else {
      renderWin.loadFile(path.join(__dirname, "..", "dist", "index.html"), { query });
    }
    return { ok: true };
  });
}

function createWindow() {
  const query = runtimeQuery();
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
    const params = new URLSearchParams(query).toString();
    const suffix = params ? `?${params}` : "";
    win.loadURL(`http://127.0.0.1:5173${suffix}`);
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"), { query });
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
