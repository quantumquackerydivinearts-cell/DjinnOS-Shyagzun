const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("atelierDesktop", {
  shell: "electron",
  renderer: {
    openWindow: async () => ipcRenderer.invoke("renderer:open-window", { view: "renderer-full" })
  },
  fs: {
    chooseDirectory: async () => ipcRenderer.invoke("studio:choose-directory"),
    listCobraScripts: async (rootDir) => ipcRenderer.invoke("studio:list-cobra-scripts", rootDir),
    listAssetsBySuffix: async (rootDir, suffix) => ipcRenderer.invoke("studio:list-assets-by-suffix", rootDir, suffix),
    readCobraScript: async (rootDir, filename) => ipcRenderer.invoke("studio:read-cobra-script", rootDir, filename),
    readTextFile: async (rootDir, filename) => ipcRenderer.invoke("studio:read-text-file", rootDir, filename),
    writeCobraScript: async (rootDir, filename, content) =>
      ipcRenderer.invoke("studio:write-cobra-script", rootDir, filename, content),
    writeTextFile: async (rootDir, filename, content) =>
      ipcRenderer.invoke("studio:write-text-file", rootDir, filename, content)
  }
});

