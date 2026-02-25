const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("atelierDesktop", {
  shell: "electron"
});

