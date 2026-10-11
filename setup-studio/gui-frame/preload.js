// SPDX-License-Identifier: MIT
// The bridge between the page and the window: real paths of dropped files and folders, and the
// system's file dialogs. Nothing else of Electron or Node reaches the page.
"use strict";
const { contextBridge, ipcRenderer, webUtils } = require("electron");

contextBridge.exposeInMainWorld("dusklight", {
  pathForFile: (file) => webUtils.getPathForFile(file),
  pick: (kind) => ipcRenderer.invoke("dusklight:pick", kind),
});
