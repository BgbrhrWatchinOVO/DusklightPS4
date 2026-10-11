// SPDX-License-Identifier: MIT
// The Dusklight Setup Studio's browser assistant (served by web.py on 127.0.0.1).
"use strict";

const TEXT = {
  en: {
    subtitle: "Twilight Princess on your PS4, with your own game",
    stepWelcome: "Welcome", stepGame: "Game", stepTextures: "HD textures", stepSettings: "Settings",
    stepPs4: "PS4", stepInstall: "Install",
    welcomeTitle: "Welcome",
    thanks1: "This port stands on the work of many people. Thank you to everyone whose work and ideas made it possible, including the artists, programmers, writers and scientists behind the modern tools it was built with. Ideas, code and AI should be free, shared and open to everyone.",
    thanks2: "Thank you to the developers of The Legend of Zelda: Twilight Princess for a game that is still loved today.",
    thanks3: "Thank you to the community around the game, especially the developers of Dusklight and everyone who worked on the decompilation, the PS5 port, DolphinPS4 and Twilight HD.",
    thanks4: "This port exists because of their work. Have a lot of fun with it.",
    needTitle: "What you need", needGame: "The game files", needTextures: "The textures",
    doesTitle: "What the script does",
    does1: "Runs on Linux, Windows, and macOS, with a GUI",
    does2: "Asks which language you want and whether to install improved textures",
    does3: "Builds a ready-to-install package",
    tip: "If you enjoy it, please consider supporting the developers mentioned above; any amount helps. Feedback about bugs, errors, misconfigurations or possible improvements is welcome.",
    signoff: "Have fun, and good luck!",
    legal: "Game data belongs to Nintendo and the texture pack's author asks that it is only downloaded from his page, so you bring both yourself. Everything stays on your computer and your PS4; nothing is uploaded anywhere else.",
    start: "Start", next: "Next", back: "Back", skip: "Without textures", browse: "Browse…",
    gameTitle: "Choose your game",
    gameIntro: "Twilight Princess for GameCube or for Wii: both work. Choose the .iso of your own disc.",
    gcTitle: "GameCube", gcText: "Works directly. Nothing else needed.",
    gcIds: "GZ2E01 (USA) · GZ2P01 (Europe, 5 languages) · GZ2J01 (Japan)",
    wiiTitle: "Wii", wiiText: "A decrypted image works directly. An encrypted dump (as CleanRip makes it) needs your Wii key: add it below.",
    wiiIds: "RZDE01 (USA) · RZDP01 (Europe, 5 languages) · RZDJ01 (Japan)",
    wiiKeyTitle: "Wii dump? Add your Wii key",
    wiiKeyText: "Only needed for an encrypted Wii dump. Paste your Wii's common key, or choose the keys.bin from your own Wii's BootMii backup. The key is only used to decrypt your disc on this computer and is never saved.",
    keyPasteLabel: "Wii common key (32 hexadecimal characters)", or: "or", applyKey: "Use this key",
    keysLabel: "keys.bin from your own BootMii backup",
    keysHint: "The Setup Studio contains no Nintendo keys. BootMii writes keys.bin together with its NAND backup (nand.bin) to the SD card; the common key is also shown by tools that read keys.bin.",
    checking: "Checking…",
    gameOk: (g) => `The Legend of Zelda: Twilight Princess, ${g.gameId} (${g.platform === "wii" ? (g.encrypted ? "Wii, encrypted: it is decrypted while it is made smaller" : "Wii, decrypted") : "GameCube"}, ${regionName(g.region)}). ${g.fileCount} files, ${gib(g.filesSize)} of game data; ${g.imageSize < g.filesSize * 1.2 ? "the image is already compact" : `the PS4 gets a compact copy of ${gib(g.filesSize * 1.05)} instead of ${gib(g.imageSize)}`}.`,
    texTitle: "HD textures (optional)",
    texText: "Henriko's texture pack makes the game sharper. Download the 1080p version for Dusklight (PC) from his page, then choose the ZIP or its extracted folder here. On the same page you also find the PlayStation buttons addon (Xbox + PS UI Buttons Addon, PC version), which puts PlayStation symbols on all buttons.",
    openHenriko: "Open Henriko's download page",
    linkDump: "dump your own disc (guide)", linkHenriko: "Henriko's download page",
    needTexturesNote: "(the HD texture pack and the PlayStation buttons addon are both on this page)",
    linkDumpLong: "How to dump your own disc with CleanRip", linkNand: "How to make a BootMii backup (keys.bin)", texPack: "Texture pack (ZIP or folder)",
    texButtons: "PlayStation buttons addon (optional, ZIP or folder, PC version), also on Henriko's page",
    dropHintImage: "or drag the file (and your keys.bin, for an encrypted Wii dump) into this window",
    dropHintTextures: "Tip: drag the texture pack and the button addon (folders or ZIPs) into this window, together or one by one.",
    dropNotImage: "That is not a disc image: drop the .iso file here.",
    copying: (p) => `Copying into the work folder… ${p} %`,
    packOk: (p) => `${p.textures} textures (${p.resolution}), ${gib(p.size)}.`,
    pack4k: "This is the 4K version: it needs about four times the graphics memory and can stutter on the PS4. The 1080p version is recommended.",
    buttonsOk: "PlayStation buttons found; they are adapted to the Nintendo layout (Circle confirms).",
    setTitle: "Settings", setLanguage: "Game language", setHud: "Wii U-style HUD (Twilight HD)",
    setFast: "Faster scene transitions", setVersion: "Version", setRelease: "Dusklight (recommended)",
    setDev: "Dusklight Dev: frame counter, profiler and logs for troubleshooting",
    setMethod: "How to install",
    setPackage: "Build a complete package: game, textures and settings in one file, no FTP needed (recommended)",
    setFtp: "Send everything to the PS4 over FTP",
    sumSaveTo: "Saved in",
    insNoteFtp: "Your settings and save data on the PS4 are copied to this computer first. Files already on the PS4 are not sent again.",
    insNotePackage: "The package is saved in the folder you started the Setup Studio from (shown above). Building takes a few minutes and needs about 3 GB of free space there.",
    build: "Build the package",
    sumMethod: "Install", methodPackage: "Complete package", methodFtp: "Over FTP",
    steppackage: "Building the package",
    donePackage: (path) => `Done: ${path} (in the folder you started the Setup Studio from). Copy it to the top folder of a USB drive (exFAT), plug the drive into the PS4 and install it with the Package Installer (Settings › Debug Settings › Game › Package Installer, available with GoldHEN). Then start Dusklight.`,
    noPackageTool: "The package tool is missing from this Setup Studio download; only FTP is available.",
    ps4Title: "Connect to your PS4",
    ps4Text: "Switch on GoldHEN's FTP server on the PS4 and enter its IP address (GoldHEN shows it when FTP starts).",
    test: "Test connection", ps4Ok: "Connected.", ps4Existing: (s) => `Dusklight is already set up there (game ${gib(s)}); it is updated.`,
    insTitle: "Install", install: "Install on the PS4",
    insNote: "Your settings and save data on the PS4 are copied to this computer first. Files already on the PS4 are not sent again.",
    sumGame: "Game", sumTextures: "HD textures", sumNone: "none", sumLanguage: "Language", sumHud: "Wii U HUD",
    sumVersion: "Version", sumPs4: "PS4", on: "on", off: "off",
    stepcompact: "Compacting the game image", stepverify: "Checking every file", steptextures: "Converting textures",
    stepbackup: "Backing up your settings and saves", stepupload: "Sending to the PS4", stepconfig: "Applying settings",
    done: (pkg) => `Done. On the PS4, open GoldHEN › Package Installer, install ${pkg} and start Dusklight. Your backup is in ${state.work}/backups.`,
    failed: (e) => `It did not work: ${e}`,
    browseTitle: "Choose", go: "Go", native: "System dialog…", useFolder: "Use this folder", cancel: "Cancel",
    footer: "Fan project, not affiliated with Nintendo. The package you install is for your own use only.",
    noProgram: "The Dusklight package is missing from this Setup Studio download.",
    afterCrash: "If the game ever crashes, restart the PS4 completely before starting it again.",
  },
};

const MESSAGES = [[/^busy$/, "An installation is already running."]];

function localize(message) {
  for (const [pattern, text] of MESSAGES) {
    if (pattern.test(message)) return message.replace(pattern, text);
  }
  return message;
}

const state = { links: {}, page: 0, game: null, pack: null, buttons: null, host: "", work: "", henriko: "" };
const token = new URLSearchParams(location.hash.slice(1)).get("token") || "";
const $ = (id) => document.getElementById(id);
const t = (key, ...args) => { const v = TEXT.en[key] ?? key; return typeof v === "function" ? v(...args) : v; };
const gib = (bytes) => `${(bytes / 2 ** 30).toFixed(2)} GB`;
const regionName = (r) => ({ Europe: "Europe", NorthAmerica: "North America", Japan: "Japan", Korea: "Korea" })[r] || r;

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "X-Token": token, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return res.json();
}

function applyText() {
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
}

function show(page) {
  state.page = page;
  document.querySelectorAll("[data-page]").forEach((s) => { s.hidden = Number(s.dataset.page) !== page; });
  document.querySelectorAll(".steps li").forEach((li) => {
    const n = Number(li.dataset.step);
    li.classList.toggle("active", n === page);
    li.classList.toggle("done", n < page);
  });
  if (page === 3) fillLanguages();
  if (page === 5) showSummary();
  window.scrollTo(0, 0);
}

function result(el, kind, text) {
  el.className = `result ${kind}`;
  el.textContent = text;
}

// --- 1 game -------------------------------------------------------------------------------------
function showGame(g) { result($("imageResult"), "ok", t("gameOk", g)); }

async function checkImage() {
  const path = $("image").value.trim();
  const key = $("keyText").value.trim();       // pasted: stays in this page's memory, never stored
  const keys = key ? "" : $("keys").value.trim();
  if (state.game && state.game.path === path && state.game.keys === keys && state.game.key === key) return;  // leaving the field after a check
  state.game = null;
  $("imageNext").disabled = true;
  if (!path) return;
  result($("imageResult"), "", t("checking"));
  const g = await api("/api/check", { path, keys, key });
  if (!g.ok) {
    if (g.needsKeys) $("wiiKey").open = true;
    return result($("imageResult"), "bad", localize(g.error));
  }
  state.game = { ...g, path, keys: g.encrypted ? keys : "", key: g.encrypted ? key : "" };
  showGame(state.game);
  $("imageNext").disabled = false;
}

// --- 2 textures ---------------------------------------------------------------------------------
async function checkPack() {
  const path = $("pack").value.trim();
  if (state.pack && state.pack.path === path) return;
  state.pack = null;
  $("texNext").disabled = true;
  if (!path) return result($("packResult"), "", "");
  result($("packResult"), "", t("checking"));
  const p = await api("/api/pack", { path });
  if (!p.ok) return result($("packResult"), "bad", localize(p.error));
  state.pack = { ...p, path };
  result($("packResult"), p.resolution === "4K" ? "bad" : "ok", t("packOk", p) + (p.resolution === "4K" ? " " + t("pack4k") : ""));
  $("texNext").disabled = false;
}

async function checkButtons() {
  const path = $("buttons").value.trim();
  if (state.buttons && state.buttons === path) return;
  state.buttons = null;
  if (!path) return result($("buttonsResult"), "", "");
  const b = await api("/api/buttons", { path });
  if (!b.ok) return result($("buttonsResult"), "bad", localize(b.error));
  state.buttons = path;
  result($("buttonsResult"), "ok", t("buttonsOk"));
}

// --- 3 settings ---------------------------------------------------------------------------------
function fillLanguages() {
  const select = $("language");
  const current = select.value;
  select.replaceChildren();
  for (const l of state.game?.languages ?? []) {
    const o = document.createElement("option");
    o.value = l.id;
    o.textContent = l.name;
    select.append(o);
  }
  const preferred = [...select.options].find((o) => o.value === current) ||
    [...select.options].find((o) => o.value === "0");
  if (preferred) select.value = preferred.value;
}

// --- 4 PS4 --------------------------------------------------------------------------------------
async function testPs4() {
  const host = $("host").value.trim();
  $("ps4Next").disabled = true;
  if (!host) return;
  try { localStorage.setItem("dusklight-setup-host", host); } catch (e) { /* ignore */ }
  result($("ps4Result"), "", t("checking"));
  const r = await api("/api/ps4", { host });
  if (!r.ok) return result($("ps4Result"), "bad", localize(r.error));
  state.host = host;
  result($("ps4Result"), "ok", t("ps4Ok") + (r.existingGame ? " " + t("ps4Existing", r.existingGame) : ""));
  $("ps4Next").disabled = false;
}

// --- 5 install ----------------------------------------------------------------------------------
const method = () => document.querySelector("input[name=method]:checked").value;

function choices() {
  return {
    image: state.game.path, pack: state.pack?.path || null, buttons: state.pack ? state.buttons : null,
    language: Number($("language").value), hud: $("hud").checked, fastTransitions: $("fast").checked,
    dev: document.querySelector("input[name=version]:checked").value === "dev", host: state.host,
    method: method(), keys: state.game.keys || null, key: state.game.key || null,
  };
}

function showSummary() {
  const c = choices();
  const rows = [
    [t("sumGame"), `${state.game.gameId} · ${c.image}`],
    [t("sumTextures"), state.pack ? `${state.pack.resolution} · ${state.pack.path}` : t("sumNone")],
    [t("sumLanguage"), $("language").selectedOptions[0]?.textContent || ""],
    [t("sumHud"), c.hud ? t("on") : t("off")],
    [t("sumVersion"), c.dev ? "Dusklight Dev" : "Dusklight"],
    [t("sumMethod"), c.method === "package" ? t("methodPackage") : t("methodFtp")],
    ...(c.method === "ftp" ? [[t("sumPs4"), c.host]] : [[t("sumSaveTo"), state.packageDir]]),
  ];
  $("insNote").textContent = t(c.method === "package" ? "insNotePackage" : "insNoteFtp");
  $("install").textContent = t(c.method === "package" ? "build" : "install");
  $("summary").replaceChildren(...rows.flatMap(([k, v]) => {
    const dt = document.createElement("dt"); dt.textContent = k;
    const dd = document.createElement("dd"); dd.textContent = v;
    return [dt, dd];
  }));
}

const STEPS = {
  ftp: ["compact", "verify", "textures", "backup", "upload", "config"],
  package: ["compact", "verify", "textures", "package"],
};

async function install() {
  $("insActions").hidden = true;
  $("progress").hidden = false;
  $("failed").hidden = $("done").hidden = true;
  const list = $("progressList");
  list.replaceChildren(...STEPS[method()].filter((s) => s !== "textures" || state.pack).map((s) => {
    const li = document.createElement("li");
    li.dataset.step = s;
    li.innerHTML = `<div class="label"><span></span><span class="pct"></span></div><div class="bar"><i></i></div>`;
    li.querySelector(".label span").textContent = t(`step${s}`);
    return li;
  }));
  const start = await api("/api/deploy", choices());
  if (!start.ok) return fail(start.error);
  const poll = async () => {
    const job = await api("/api/job");
    for (const [step, s] of Object.entries(job.steps)) {
      const li = list.querySelector(`[data-step="${step}"]`);
      if (!li) continue;
      const frac = s.total ? Math.min(1, s.done / s.total) : 0;
      li.querySelector(".bar > i").style.width = `${(frac * 100).toFixed(1)}%`;
      li.querySelector(".pct").textContent = `${(frac * 100).toFixed(0)} %` + (s.message && step === "upload" && frac < 1 ? ` · ${s.message}` : "");
      li.classList.toggle("finished", frac >= 1);
    }
    $("log").textContent = job.log.join("\n");
    if (job.running) return setTimeout(poll, 500);
    if (job.error) return fail(job.error);
    $("done").hidden = false;
    if (method() === "package" && job.result) {
      $("done").textContent = `${t("donePackage", job.result.package)} ${t("afterCrash")}`;
      return;
    }
    const pkg = choices().dev ? "Dusklight-Dev.pkg" : "Dusklight.pkg";
    $("done").textContent = `${t("done", pkg)} ${t("afterCrash")}`;
  };
  poll();
}

function fail(error) {
  $("failed").hidden = false;
  $("failed").textContent = t("failed", localize(error));
  $("insActions").hidden = false;
}

// --- file browser -------------------------------------------------------------------------------
let browseTarget = null, browseKind = "image", browseRequest = 0;

async function browseTo(path) {
  const request = ++browseRequest;
  const r = await api(`/api/browse?path=${encodeURIComponent(path || "")}&kind=${browseKind}`);
  if (request !== browseRequest) return;  // a later folder was asked for meanwhile
  $("browsePath").value = r.path;
  $("browseUp").dataset.path = r.parent;
  $("drives").replaceChildren(...(r.drives || []).map((d) => {
    const b = document.createElement("button"); b.type = "button"; b.textContent = d;
    b.onclick = () => browseTo(d); return b;
  }));
  $("browseList").replaceChildren(...r.entries.map((e) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.className = e.dir ? "dir" : "file";
    const name = document.createElement("span"); name.textContent = e.name;
    b.append(name);
    if (!e.dir) { const s = document.createElement("span"); s.className = "size"; s.textContent = gib(e.size); b.append(s); }
    b.onclick = () => (e.dir ? browseTo(e.path) : pick(e.path));
    li.append(b);
    return li;
  }));
}

function pick(path) {
  $("browser").close();
  const input = $(browseTarget);
  input.value = path;
  input.dispatchEvent(new Event("change"));
}

function openBrowser(kind, target) {
  browseKind = kind;
  browseTarget = target;
  $("browseFolder").hidden = kind !== "pack" && kind !== "zip" && kind !== "folder";
  const current = $(target).value.trim();
  browseTo(current);
  $("browser").showModal();
}

// --- wiring -------------------------------------------------------------------------------------
// The complete package needs no PS4 connection: its step is skipped.
document.querySelectorAll("[data-next]").forEach((b) => (b.onclick = () => show(state.page === 3 && method() === "package" ? 5 : state.page + 1)));
document.querySelectorAll("[data-back]").forEach((b) => (b.onclick = () => show(state.page === 5 && method() === "package" ? 3 : state.page - 1)));
const markMethod = () => { document.querySelector('.steps li[data-step="4"]').hidden = method() === "package"; };
document.querySelectorAll("input[name=method]").forEach((r) => r.addEventListener("change", markMethod));

document.querySelectorAll("[data-browse]").forEach((b) => (b.onclick = () => openBrowser(b.dataset.browse, b.dataset.target)));
$("image").addEventListener("change", checkImage);
$("keys").addEventListener("change", checkImage);
$("keyText").addEventListener("change", checkImage);
$("keyText").addEventListener("input", () => {
  // A complete pasted key is checked right away.
  if ($("keyText").value.replace(/[\s:-]/g, "").length === 32) checkImage();
});
$("applyKey").onclick = () => { state.game = null; checkImage(); };
$("pack").addEventListener("change", checkPack);
$("buttons").addEventListener("change", checkButtons);
$("imageNext").onclick = () => show(2);
$("texNext").onclick = () => show(3);
$("skipTextures").onclick = () => { state.pack = null; $("pack").value = ""; result($("packResult"), "", ""); show(3); };
// Links open in the system browser (the server allows only these pages).
document.querySelectorAll("[data-open]").forEach((link) => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.links[link.dataset.open]) api("/api/open", { url: state.links[link.dataset.open] });
  });
});
$("testPs4").onclick = testPs4;
$("host").addEventListener("keydown", (e) => { if (e.key === "Enter") testPs4(); });
$("ps4Next").onclick = () => show(5);
$("install").onclick = install;
$("browseUp").onclick = () => browseTo($("browseUp").dataset.path);
$("browseGo").onclick = () => browseTo($("browsePath").value);
$("browsePath").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); browseTo($("browsePath").value); } });
$("browseFolder").onclick = () => pick($("browsePath").value);
$("browseNative").onclick = async () => {
  const kind = browseKind === "pack" || browseKind === "zip" ? "folder" : browseKind;
  // The window app has the system's own dialogs; a plain browser asks the Python side.
  const path = window.dusklight ? await window.dusklight.pick(kind) : (await api("/api/pick", { kind })).path;
  if (path) pick(path);
};

// --- drag and drop ------------------------------------------------------------------------------
// In the window app (Electron) a dropped file or folder arrives with its real path. A plain
// browser does not reveal paths, so there the dropped data is copied into the work folder.
const IMAGE_NAME = /\.(iso|gcm)$/i;
let dropCount = 0;

function dropZone(event) {
  const zone = event.target instanceof Element ? event.target.closest("[data-drop]") : null;
  if (zone && !zone.closest("[hidden]")) return zone;
  const card = document.querySelector(`[data-page="${state.page}"][data-drop]`);
  return card || null;
}

function markZone(zone) {
  document.querySelectorAll(".drop-active").forEach((el) => el.classList.remove("drop-active"));
  if (!zone) return;
  zone.classList.add("drop-active");
  zone.closest(".card")?.classList.add("drop-active");
}

function readEntries(dir) {
  const reader = dir.createReader();
  const all = [];
  return new Promise((resolve, reject) => {
    const next = () => reader.readEntries((batch) => {
      if (!batch.length) return resolve(all);
      all.push(...batch);
      next();
    }, reject);
    next();
  });
}

async function filesBelow(dir, prefix) {
  const out = [];
  for (const entry of await readEntries(dir)) {
    if (entry.isDirectory) out.push(...await filesBelow(entry, `${prefix}${entry.name}/`));
    else out.push({ rel: `${prefix}${entry.name}`, file: await new Promise((res, rej) => entry.file(res, rej)) });
  }
  return out;
}

function put(url, file, progress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("X-Token", token);
    xhr.upload.onprogress = (e) => progress(e.loaded);
    xhr.onload = () => {
      let body = {};
      try { body = JSON.parse(xhr.responseText); } catch (e) { /* not JSON */ }
      if (xhr.status === 200) resolve(body); else reject(new Error(body.error || `HTTP ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("copy failed"));
    xhr.send(file);
  });
}

async function copyIntoWork(item, el) {
  const slot = `drop-${++dropCount}`;
  const files = item.isDir ? await filesBelow(item.entry, `${item.name}/`) : [{ rel: item.name, file: item.file }];
  const total = files.reduce((n, f) => n + f.file.size, 0);
  const reset = await api("/api/upload-reset", { slot, bytes: total });
  if (!reset.ok) throw new Error(reset.error);
  let done = 0;
  let path = "";
  for (const f of files) {
    const r = await put(`/api/upload?slot=${slot}&rel=${encodeURIComponent(f.rel)}`, f.file,
      (loaded) => result(el, "", t("copying", Math.floor((100 * (done + loaded)) / Math.max(total, 1)))));
    done += f.file.size;
    path = r.path;
  }
  return path;
}

async function droppedPath(item, el) {
  if (window.dusklight && item.file) {
    const path = window.dusklight.pathForFile(item.file);
    if (path) return path;
  }
  return copyIntoWork(item, el);
}

function setField(id, path) {
  const input = $(id);
  input.value = path;
  input.dispatchEvent(new Event("change"));
}

async function handleDrop(items, target) {
  for (const item of items) {
    let field = target;
    if (!item.isDir && IMAGE_NAME.test(item.name)) field = "image";
    else if (!item.isDir && /\.bin$/i.test(item.name) && (target === "image" || target === "keys")) field = "keys";
    else if (target === "image" || target === "keys") { result($("imageResult"), "bad", t("dropNotImage")); continue; }
    if (field === "keys") $("wiiKey").open = true;
    const el = $(field === "image" || field === "keys" ? "imageResult" : field === "buttons" ? "buttonsResult" : "packResult");
    try {
      const path = await droppedPath(item, el);
      if (field === "auto") field = (await api("/api/buttons", { path })).ok ? "buttons" : "pack";
      setField(field, path);
    } catch (e) {
      result(el, "bad", localize(e.message || String(e)));
    }
  }
}

window.addEventListener("dragover", (e) => {
  e.preventDefault();  // never let the window open a dropped file itself
  const zone = dropZone(e);
  e.dataTransfer.dropEffect = zone ? "copy" : "none";
  markZone(zone);
});
window.addEventListener("dragleave", (e) => { if (!e.relatedTarget) markZone(null); });
window.addEventListener("drop", (e) => {
  e.preventDefault();
  const zone = dropZone(e);
  markZone(null);
  if (!zone) return;
  // DataTransfer items are only readable during the event: take them now.
  const items = [...e.dataTransfer.items].filter((i) => i.kind === "file").map((i) => {
    const entry = i.webkitGetAsEntry ? i.webkitGetAsEntry() : null;
    const file = i.getAsFile();
    return { entry, file, isDir: !!(entry && entry.isDirectory), name: (entry && entry.name) || (file && file.name) || "" };
  });
  handleDrop(items, zone.dataset.drop);
});

(async function init() {
  try { $("host").value = localStorage.getItem("dusklight-setup-host") || ""; } catch (e) { /* ignore */ }
  applyText();
  show(0);
  const s = await api("/api/state");
  state.work = s.work;
  state.packageDir = s.packageDir || "";
  if (!s.packageTool) {
    document.querySelector("input[name=method][value=package]").disabled = true;
    document.querySelector("input[name=method][value=ftp]").checked = true;
    document.querySelector("input[name=method][value=package]").closest("label").title = t("noPackageTool");
  }
  markMethod();
  state.henriko = s.henriko;
  state.links = s.links || { henriko: s.henriko };
  document.querySelectorAll("[data-open]").forEach((link) => { link.title = state.links[link.dataset.open] || ""; });
  $("version").textContent = `v${s.version}`;
  if (!s.release) result($("imageResult"), "bad", t("noProgram"));
})();
