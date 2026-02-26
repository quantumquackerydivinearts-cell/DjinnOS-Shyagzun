const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("atelierDesktop", {
  shell: "electron",
  fs: {
    chooseDirectory: async () => ipcRenderer.invoke("studio:choose-directory"),
    listCobraScripts: async (rootDir) => ipcRenderer.invoke("studio:list-cobra-scripts", rootDir),
    readCobraScript: async (rootDir, filename) => ipcRenderer.invoke("studio:read-cobra-script", rootDir, filename),
    writeCobraScript: async (rootDir, filename, content) =>
      ipcRenderer.invoke("studio:write-cobra-script", rootDir, filename, content)
  }
});

