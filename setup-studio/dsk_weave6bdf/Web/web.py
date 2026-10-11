# SPDX-License-Identifier: MIT
"""The Setup Studio's browser assistant: a local web server for the pages in web/.

Python's standard library only. It listens on 127.0.0.1, every API call needs the random token
from the address the Setup Studio opens, and requests naming another host are refused (DNS
rebinding). Nothing is sent anywhere but to the PS4 the user names. The pages choose files
through /api/browse (a browser cannot hand a local file's path to a page), or a native dialog
where tkinter is available.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from . import console
from . import deploy
from . import disc as discmod
from . import package as packagemod
from . import textures

WEB_DIR = Path(__file__).resolve().parent / "web"
# Pages the assistant may open in the system browser: where the user gets what they bring.
LINKS = {
    "henriko": textures.PAGE,                                   # the HD texture pack and button addon
    "dump": "https://wii.hacks.guide/dump-games.html",          # dumping your own disc with CleanRip
    "cleanrip": "https://github.com/emukidid/cleanrip",
    "nand": "https://wii.hacks.guide/nand-backup.html",         # BootMii backup, which writes keys.bin
}
ALLOWED_URLS = set(LINKS.values())
UPLOAD_SLOT = re.compile(r"[a-z0-9-]{1,40}")
IMAGE_SUFFIXES = {".iso", ".gcm"}
PACK_SUFFIXES = {".zip"}


class Job:
    """The one deployment running at a time, as the pages poll it."""

    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.steps: dict[str, dict] = {}
        self.log: list[str] = []
        self.error = ""
        self.result: dict | None = None
        self.started = 0.0

    def report(self, step: str, done: int, total: int, message: str) -> None:
        with self.lock:
            self.steps[step] = {"done": done, "total": total, "message": message, "time": time.time()}
            if message and (not self.log or self.log[-1] != f"{step}: {message}"):
                self.log.append(f"{step}: {message}")

    def snapshot(self) -> dict:
        with self.lock:
            return {"running": self.running, "steps": dict(self.steps), "log": list(self.log[-40:]),
                    "error": self.error, "result": self.result, "started": self.started}


JOB = Job()


def _drives() -> list[str]:
    if os.name != "nt":
        return []
    return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]


def browse(path: str, kind: str) -> dict:
    base = Path(path).expanduser() if path else Path.home()
    if base.is_file():
        base = base.parent
    if not base.is_dir():
        base = Path.home()
    suffixes = (IMAGE_SUFFIXES if kind == "image" else PACK_SUFFIXES if kind in ("pack", "zip")
                else {".bin"} if kind == "keys" else set())
    entries = []
    try:
        for entry in sorted(base.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if entry.name.startswith("."):
                continue
            try:
                if entry.is_dir():
                    entries.append({"name": entry.name, "path": str(entry), "dir": True})
                elif entry.suffix.lower() in suffixes:
                    entries.append({"name": entry.name, "path": str(entry), "dir": False,
                                    "size": entry.stat().st_size})
            except OSError:
                continue
    except OSError as e:
        return {"path": str(base), "parent": str(base.parent), "entries": [], "error": str(e),
                "drives": _drives()}
    return {"path": str(base), "parent": str(base.parent), "entries": entries, "drives": _drives(),
            "home": str(Path.home())}


def _mac_pick(kind: str) -> str:
    # Tk must run on the main thread on macOS (this runs in a request thread): AppleScript instead.
    script = ("POSIX path of (choose folder)" if kind == "folder" else
              'POSIX path of (choose file of type {"iso", "gcm"})' if kind == "image" else
              'POSIX path of (choose file of type {"bin"})' if kind == "keys" else
              'POSIX path of (choose file of type {"zip"})')
    try:
        done = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def native_pick(kind: str) -> str:
    """A native file dialog: AppleScript on macOS, tkinter elsewhere (else "")."""
    if sys.platform == "darwin":
        return _mac_pick(kind)
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return ""
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if kind == "folder":
            return filedialog.askdirectory() or ""
        types = ([("Disc image", "*.iso *.gcm")] if kind == "image" else [("Wii keys", "*.bin")] if kind == "keys"
                 else [("ZIP", "*.zip")])
        return filedialog.askopenfilename(filetypes=types + [("All files", "*")]) or ""
    finally:
        root.destroy()


def uploads_dir() -> Path:
    return deploy.default_work() / "uploads"


def upload_reset(body: dict) -> dict:
    """Starts a copy of dropped files into the work folder (plain browser only; the window app gets
    real paths): empties the slot and checks the space."""
    slot = str(body.get("slot", ""))
    if not UPLOAD_SLOT.fullmatch(slot):
        return {"ok": False, "error": "bad slot"}
    folder = uploads_dir() / slot
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    need = int(body.get("bytes", 0) or 0)
    free = shutil.disk_usage(folder).free
    if need + (512 << 20) > free:
        return {"ok": False, "error": f"Not enough free space for the copy ({need / 2**30:.1f} GB needed, "
                                      f"{free / 2**30:.1f} GB free in {deploy.default_work()})."}
    return {"ok": True}


def upload_target(slot: str, rel: str) -> Path | None:
    parts = rel.split("/")
    if (not UPLOAD_SLOT.fullmatch(slot) or not 0 < len(parts) <= 32
            or any(p in ("", ".", "..") or any(c in p for c in '\\:\0') for p in parts)):
        return None
    return uploads_dir() / slot / Path(*parts)


def key_source(body: dict):
    """The Wii key the page sent: pasted as text (kept in memory only) or a keys.bin path."""
    if body.get("key"):
        return discmod.parse_key_text(str(body["key"]))
    return Path(body["keys"]) if body.get("keys") else None


def check_image(body: dict) -> dict:
    path = body.get("path", "")
    try:
        keys = key_source(body)
        d = discmod.Disc(path, keys=keys)
    except (discmod.DiscError, OSError) as e:
        # An encrypted Wii image: the page opens the Wii key section and checks again.
        given = bool(body.get("key") or body.get("keys"))
        needs_keys = str(e) == discmod.NEEDS_KEYS or (given and "key" in str(e).lower())
        return {"ok": False, "error": str(e), "needsKeys": needs_keys}
    i = d.info()
    d.close()
    return {"ok": True, "encrypted": d.encrypted, "platform": i.platform, "gameId": i.game_id, "revision": i.revision,
            "region": i.region, "languages": [{"id": l, "name": discmod.LANGUAGE_NAMES[l]} for l in i.languages],
            "imageSize": i.image_size, "filesSize": i.files_size, "fileCount": i.file_count}


def check_pack(path: str) -> dict:
    try:
        top, resolution, count, size = textures.inspect(Path(path))
    except (textures.TextureError, OSError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "top": top, "resolution": resolution, "textures": count, "size": size}


def check_buttons(path: str) -> dict:
    try:
        from .buttons import load_layout
        load_layout(Path(path))
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # a damaged ZIP
        return {"ok": False, "error": str(e)}
    return {"ok": True}


def check_ps4(host: str) -> dict:
    try:
        ps4 = console.Console(host, timeout=8)
    except console.ConsoleError as e:
        return {"ok": False, "error": str(e)}
    try:
        game = ps4.size(console.DATA_DIR + "/game.iso")
        config = ps4.size(console.USER_DIR + "/config.json")
        return {"ok": True, "existingGame": game, "existingSettings": config is not None}
    finally:
        ps4.close()


def start_deploy(body: dict) -> dict:
    with JOB.lock:
        if JOB.running:
            return {"ok": False, "error": "busy"}
        JOB.running, JOB.steps, JOB.log, JOB.error, JOB.result = True, {}, [], "", None
        JOB.started = time.time()
    dev = bool(body.get("dev"))
    program = deploy.default_program(dev)
    opts = deploy.Options(
        image=Path(body["image"]), host=str(body.get("host") or "").strip(),
        program=program if program else Path("Dusklight-Dev.pkg" if dev else "Dusklight.pkg"),
        work=deploy.default_work(),
        pack=Path(body["pack"]) if body.get("pack") else None,
        buttons=Path(body["buttons"]) if body.get("buttons") else None,
        language=body.get("language"), twilight_hd=body.get("hud"),
        fast_transitions=body.get("fastTransitions"), keys=key_source(body),
        dry_run=bool(body.get("dryRun")))

    method = body.get("method", "ftp")

    def work() -> None:
        try:
            if method == "package":
                result = packagemod.build(opts, JOB.report)
            else:
                result = deploy.run(opts, JOB.report)
            with JOB.lock:
                JOB.result = result
        except Exception as e:  # shown on the page; details in the console window
            traceback.print_exc()
            with JOB.lock:
                JOB.error = str(e) or e.__class__.__name__
        finally:
            with JOB.lock:
                JOB.running = False
    threading.Thread(target=work, daemon=True).start()
    return {"ok": True}


class Handler(BaseHTTPRequestHandler):
    server_version = "DskStudioC06f"
    token = ""
    port = 0

    def log_message(self, format, *args):  # quiet: the console window shows only problems
        pass

    def _host_ok(self) -> bool:
        host = self.headers.get("Host", "")
        return host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")

    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not self._host_ok():
            self._json({"error": "forbidden"}, HTTPStatus.FORBIDDEN)
            return False
        if self.path.startswith("/api/") and self.headers.get("X-Token") != self.token:
            self._json({"error": "token"}, HTTPStatus.FORBIDDEN)
            return False
        return True

    def do_GET(self):
        if not self._authorized():
            return
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/api/state":
            return self._json({
                "version": __version__, "work": str(deploy.default_work()),
                "release": bool(deploy.default_program(False)), "dev": bool(deploy.default_program(True)),
                "henriko": textures.PAGE, "links": LINKS, "home": str(Path.home()),
                "packageTool": all(Path(p).exists() for p in packagemod.pkgtool()),
                "packageDir": str(packagemod.output_dir())})
        if url.path == "/api/browse":
            return self._json(browse(query.get("path", ""), query.get("kind", "")))
        if url.path == "/api/job":
            return self._json(JOB.snapshot())
        self._static(url.path)

    def do_POST(self):
        if not self._authorized():
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json({"error": "bad json"}, HTTPStatus.BAD_REQUEST)
        path = urlparse(self.path).path
        if path == "/api/check":
            return self._json(check_image(body))
        if path == "/api/pack":
            return self._json(check_pack(body.get("path", "")))
        if path == "/api/buttons":
            return self._json(check_buttons(body.get("path", "")))
        if path == "/api/ps4":
            return self._json(check_ps4(body.get("host", "")))
        if path == "/api/deploy":
            return self._json(start_deploy(body))
        if path == "/api/upload-reset":
            return self._json(upload_reset(body))
        if path == "/api/pick":
            return self._json({"path": native_pick(body.get("kind", "image"))})
        if path == "/api/open":
            url = body.get("url", "")
            if url in ALLOWED_URLS:
                webbrowser.open(url)
                return self._json({"ok": True})
            return self._json({"error": "url"}, HTTPStatus.FORBIDDEN)
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        """/api/upload?slot=..&rel=..: one dropped file copied into the work folder."""
        if not self._authorized():
            return
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        target = upload_target(query.get("slot", ""), query.get("rel", ""))
        if url.path != "/api/upload" or target is None:
            return self._json({"error": "bad upload"}, HTTPStatus.BAD_REQUEST)
        length = int(self.headers.get("Content-Length", "0") or 0)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".partial")
        try:
            with open(tmp, "wb") as out:
                left = length
                while left:
                    block = self.rfile.read(min(left, 1 << 20))
                    if not block:
                        raise OSError("the copy stopped early")
                    out.write(block)
                    left -= len(block)
            os.replace(tmp, target)
        except OSError as e:
            tmp.unlink(missing_ok=True)
            return self._json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
        self._json({"ok": True, "path": str(uploads_dir() / query["slot"] / query["rel"].split("/")[0])})

    def _static(self, path: str) -> None:
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        file = (WEB_DIR / name).resolve()
        if WEB_DIR not in file.parents or not file.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(file.name)[0] or "application/octet-stream")
                         + ("; charset=utf-8" if file.suffix in (".html", ".js", ".css") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(data)


def _exit_when_stdin_closes() -> None:
    try:
        while sys.stdin.buffer.read(4096):
            pass
    except (OSError, ValueError):
        pass
    os._exit(0)


def serve(port: int = 0, open_browser: bool = True, exit_with_stdin: bool = False) -> int:
    shutil.rmtree(uploads_dir(), ignore_errors=True)  # copies of dropped files from a past session
    if exit_with_stdin:
        threading.Thread(target=_exit_when_stdin_closes, daemon=True).start()
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    Handler.token = token
    Handler.port = server.server_address[1]
    url = f"http://127.0.0.1:{Handler.port}/#token={token}"
    print(f"Dusklight Setup Studio {__version__}: {url}", flush=True)
    if not exit_with_stdin:
        print("Keep this window open while you use the assistant; close it to quit.", flush=True)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
