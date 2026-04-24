const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("atelierDesktop", {
  shell: "electron",
  renderer: {
    openWindow: async () => ipcRenderer.invoke("renderer:open-window", { view: "renderer-full" })
  },
  fs: {
    chooseDirectory: async () => ipcRenderer.invoke("studio:choose-directory"),
    listKobraScripts: async (rootDir) => ipcRenderer.invoke("studio:list-kobra-scripts", rootDir),
    listAssetsBySuffix: async (rootDir, suffix) => ipcRenderer.invoke("studio:list-assets-by-suffix", rootDir, suffix),
    listRuntimePlans: async (rootDir) => ipcRenderer.invoke("studio:list-runtime-plans", rootDir),
    readKobraScript: async (rootDir, filename) => ipcRenderer.invoke("studio:read-kobra-script", rootDir, filename),
    readTextFile: async (rootDir, filename) => ipcRenderer.invoke("studio:read-text-file", rootDir, filename),
    readBinaryFileBase64: async (rootDir, filename) =>
      ipcRenderer.invoke("studio:read-binary-file-base64", rootDir, filename),
    runPython: async (rootDir, sourceText, options) =>
      ipcRenderer.invoke("studio:run-python", rootDir, sourceText, options),
    writeKobraScript: async (rootDir, filename, content) =>
      ipcRenderer.invoke("studio:write-kobra-script", rootDir, filename, content),
    writeTextFile: async (rootDir, filename, content) =>
      ipcRenderer.invoke("studio:write-text-file", rootDir, filename, content)
  }
});

