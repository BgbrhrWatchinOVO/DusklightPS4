// SPDX-License-Identifier: MIT
// Dusklight Setup Studio in its own window: starts the Python side (dsk_weave6bdf gui, from the
// WorkshopKit folder next to this app) and shows its page. Dropped files and folders reach the page
// with their real paths (preload.js); the Python side does all the work.
//
//   electron <this folder> --maker-dir=<WorkshopKit folder>
"use strict";
const { app, BrowserWindow, dialog, ipcMain, nativeTheme } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");

function option(name) {
  const prefix = `--${name}=`;
  const found = process.argv.find((a) => a.startsWith(prefix));
  return found ? found.slice(prefix.length) : null;
}

const makerDir = path.resolve(option("maker-dir") || path.join(__dirname, ".."));

function pythonPath() {
  const runtime = path.join(makerDir, "runtime");
  if (process.platform === "win32") return path.join(runtime, "windows-x64", "python", "python.exe");
  if (process.platform === "darwin") {
    return path.join(runtime, process.arch === "arm64" ? "macos-arm64" : "macos-x64", "python", "bin", "python3.13");
  }
  return path.join(runtime, "linux-x64", "python", "bin", "python3.13");
}

app.setName("Dusklight Setup Studio");
if (!app.requestSingleInstanceLock()) {
  app.quit();
}

let server = null;
let win = null;
let pageUrl = null;
let quitting = false;
let output = "";

function startServer() {
  return new Promise((resolve, reject) => {
    // --exit-with-stdin: the Python side ends when this pipe closes, also if the window crashes.
    server = spawn(pythonPath(), ["-s", "-E", "-B", "-m", "dsk_weave6bdf", "gui", "--no-browser", "--exit-with-stdin"], {
      cwd: makerDir, stdio: ["pipe", "pipe", "pipe"], windowsHide: true,
    });
    const timer = setTimeout(() => reject(new Error("The assistant did not start within 60 seconds.")), 60000);
    const collect = (chunk) => {
      output = (output + chunk.toString()).slice(-20000);
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+\/#token=[\w-]+/);
      if (match && !pageUrl) {
        pageUrl = match[0];
        clearTimeout(timer);
        resolve(pageUrl);
      }
    };
    server.stdout.on("data", collect);
    server.stderr.on("data", collect);
    server.on("error", (error) => { clearTimeout(timer); reject(error); });
    server.on("exit", (code) => {
      if (!pageUrl) {
        clearTimeout(timer);
        reject(new Error(`The assistant stopped (exit code ${code}).`));
      } else if (!quitting) {
        dialog.showErrorBox("Dusklight Setup Studio", `The assistant stopped unexpectedly.\n\n${output.slice(-1500)}`);
        app.quit();
      }
    });
  });
}

function fromOurPage(event) {
  try {
    return new URL(event.senderFrame.url).origin === new URL(pageUrl).origin;
  } catch {
    return false;
  }
}

ipcMain.handle("dusklight:pick", async (event, kind) => {
  if (!fromOurPage(event)) return "";
  const filters = {
    image: [{ name: "Disc image", extensions: ["iso", "gcm"] }],
    zip: [{ name: "ZIP", extensions: ["zip"] }],
    keys: [{ name: "Wii keys", extensions: ["bin"] }],
  }[kind];
  const folder = kind === "folder";
  const result = await dialog.showOpenDialog(win, {
    properties: [folder ? "openDirectory" : "openFile"],
    filters: folder ? undefined : [...(filters || []), { name: "All files", extensions: ["*"] }],
  });
  return result.canceled ? "" : result.filePaths[0];
});

function createWindow() {
  win = new BrowserWindow({
    width: 1060, height: 880, minWidth: 420, minHeight: 520,
    title: "Dusklight Setup Studio",
    show: !process.env.DSK_BUILD_329E_HIDDEN,  // automated tests run the window unseen
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#15141a" : "#f4f1ea",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: false,
    },
  });
  const origin = new URL(pageUrl).origin;
  // Only the assistant's own page: a file dropped beside a drop zone must not replace it.
  win.webContents.on("will-navigate", (event, target) => {
    if (new URL(target).origin !== origin) event.preventDefault();
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.loadURL(pageUrl);
}

app.on("second-instance", () => {
  if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
});

app.whenReady().then(async () => {
  try {
    await startServer();
  } catch (error) {
    dialog.showErrorBox("Dusklight Setup Studio", `${error.message}\n\n${output.slice(-1500)}`);
    app.quit();
    return;
  }
  createWindow();
});

app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => {
  quitting = true;
  if (server && server.exitCode === null) server.kill();
});
