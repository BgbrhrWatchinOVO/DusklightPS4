# SPDX-License-Identifier: MIT
"""The PS4 over GoldHEN's FTP server (port 2121): upload, download, back up, check.

Uploads go to "<name>.partial" first and are renamed when complete, so an interrupted transfer
never leaves a broken game image or pack under its real name. After an upload the size on the
console is compared; `verify_full` reads the file back and compares SHA-1 (slow, but the
console's FTP server has been seen returning corrupt downloads, so a mismatch on read-back is
retried before it counts).
"""
from __future__ import annotations

import ftplib
import hashlib
import io
import os
import posixpath
import time
from pathlib import Path
from typing import Callable, Optional

FTP_PORT = 2121
DATA_DIR = "/data/dusklight-ps4"
USER_DIR = DATA_DIR + "/user"
PKG_DIR = "/data/pkg"
BLOCK = 1 << 20

Progress = Optional[Callable[[int, int], None]]


class ConsoleError(Exception):
    pass


class Console:
    def __init__(self, host: str, port: int = FTP_PORT, timeout: float = 30.0):
        self.host, self.port = host, port
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(host, port, timeout=timeout)
            self.ftp.login()
            self.ftp.set_pasv(True)
        except (OSError, ftplib.Error) as e:
            raise ConsoleError(
                f"No connection to the PS4 at {host}:{port}. Is GoldHEN's FTP server on, and are "
                f"the PS4 and this computer in the same network? ({e})") from e

    # --- queries ------------------------------------------------------------------------------
    def exists(self, path: str) -> bool:
        return self.size(path) is not None

    def size(self, path: str) -> Optional[int]:
        try:
            self.ftp.voidcmd("TYPE I")
            return self.ftp.size(path)
        except ftplib.error_perm:
            return None

    def listdir(self, path: str) -> list[str]:
        try:
            return [posixpath.basename(n) for n in self.ftp.nlst(path)]
        except ftplib.error_perm:
            return []

    def makedirs(self, path: str) -> None:
        current = ""
        for part in path.strip("/").split("/"):
            current += "/" + part
            try:
                self.ftp.mkd(current)
            except ftplib.error_perm:
                pass  # exists

    # --- transfers ----------------------------------------------------------------------------
    def read(self, path: str) -> Optional[bytes]:
        buffer = io.BytesIO()
        try:
            self.ftp.retrbinary(f"RETR {path}", buffer.write, BLOCK)
        except ftplib.error_perm:
            return None
        return buffer.getvalue()

    def write(self, path: str, data: bytes) -> None:
        self.makedirs(posixpath.dirname(path))
        tmp = path + ".partial"
        self.ftp.storbinary(f"STOR {tmp}", io.BytesIO(data), BLOCK)
        self._replace(tmp, path)

    def upload(self, local: Path, path: str, progress: Progress = None) -> None:
        local = Path(local)
        total = local.stat().st_size
        self.makedirs(posixpath.dirname(path))
        tmp = path + ".partial"
        done = [0]

        def sent(block: bytes) -> None:
            done[0] += len(block)
            if progress:
                progress(done[0], total)
        with open(local, "rb") as f:
            self.ftp.storbinary(f"STOR {tmp}", f, BLOCK, callback=sent)
        remote = self.size(tmp)
        if remote != total:
            raise ConsoleError(f"{path}: the console holds {remote} bytes instead of {total}. Try again.")
        self._replace(tmp, path)

    def _replace(self, tmp: str, path: str) -> None:
        try:
            self.ftp.delete(path)
        except ftplib.error_perm:
            pass
        self.ftp.rename(tmp, path)

    def remove(self, path: str) -> bool:
        try:
            self.ftp.delete(path)
            return True
        except ftplib.error_perm:
            return False

    def sha1(self, path: str) -> str:
        h = hashlib.sha1()
        self.ftp.retrbinary(f"RETR {path}", h.update, BLOCK)
        return h.hexdigest()

    def verify_full(self, local: Path, path: str, attempts: int = 2) -> bool:
        with open(local, "rb") as f:
            want = hashlib.file_digest(f, "sha1").hexdigest()
        for _ in range(attempts):
            if self.sha1(path) == want:
                return True
        return False

    MANIFEST = DATA_DIR + "/maker-manifest.json"

    def read_manifest(self) -> dict:
        import json
        data = self.read(self.MANIFEST)
        try:
            return json.loads(data) if data else {}
        except ValueError:
            return {}

    def write_manifest(self, manifest: dict) -> None:
        import json
        self.write(self.MANIFEST, json.dumps(manifest, indent=2, sort_keys=True).encode())

    def backup_user_data(self, target: Path) -> list[str]:
        """Copies config.json and the memory card files to `target`; returns what was saved."""
        saved = []
        target.mkdir(parents=True, exist_ok=True)
        config = self.read(USER_DIR + "/config.json")
        if config is not None:
            (target / "config.json").write_bytes(config)
            saved.append("config.json")
        for region in self.listdir(USER_DIR):
            card = f"{USER_DIR}/{region}/Card A"
            for name in self.listdir(card):
                if name.lower().endswith(".gci"):
                    data = self.read(f"{card}/{name}")
                    if data is not None:
                        out = target / region / "Card A"
                        out.mkdir(parents=True, exist_ok=True)
                        (out / name).write_bytes(data)
                        saved.append(f"{region}/Card A/{name}")
        return saved

    def close(self) -> None:
        try:
            self.ftp.quit()
        except (OSError, ftplib.Error):
            pass


def backup_dir(base: Path) -> Path:
    return base / time.strftime("ps4-backup-%Y%m%d-%H%M%S")
