# SPDX-License-Identifier: MIT
"""Henriko's texture pack for the PS4 port: from the user's own download to one .tpak file.

The user downloads the pack from the author's page (the author asks not to redistribute it) and
chooses the ZIP or its extracted folder. This module checks it (the PC Dusklight pack, safe paths,
texture names, the resolution), converts the few DDS files whose size is not a multiple of 4 to
PNG (as the PS5 port's ps5/tools/prepare-textures.py), optionally puts in Henriko's PlayStation
button addon refitted to the Nintendo-style layout (buttons.py), and writes the pack in the
format the port reads in large blocks (src/dusklight/ps4/tpak.cpp, tools/make-tpak.py):

    header (64 bytes): magic b"DTPAK\\0\\1\\0", u32 count, u32 reserved, u64 index offset,
                       u64 index size, then zeros
    files, each starting on a 4 KiB boundary, in Aurora's registration order
    index: per file u64 offset, u64 size, u16 path length, the path ('/'-separated, relative)

No temporary copy of the pack is written: files go from the ZIP straight into the .tpak.
"""
from __future__ import annotations

import dataclasses
import hashlib
import io
import os
import struct
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable, Optional

PAGE = "https://www.henrikomagnifico.com/zelda-twilight-princess-4k"
MAGIC = b"DTPAK\x00\x01\x00"
ALIGN = 4096
EXTENSIONS = {".dds", ".png"}
MAX_UNPACKED = 16 << 30
BUTTONS_FOLDER = PurePosixPath("UI/Menus/Buttons")

Progress = Optional[Callable[[int, int], None]]


class TextureError(Exception):
    """A pack the Setup Studio cannot use; the message says why."""


@dataclasses.dataclass
class PackInfo:
    source: str          # the ZIP or folder chosen
    top_folder: str      # e.g. "HenrikosTP4K-1080p"
    resolution: str      # "1080p", "4K" or "unknown"
    textures: int
    size: int            # bytes of texture data
    unaligned: int       # DDS files converted to PNG
    buttons: int         # PlayStation button textures put in
    sha256: str          # of the ZIP (empty for a folder)


def _sort_key(relative: PurePosixPath):
    return [(part.lower(), part) for part in relative.parts]


def _valid_texture(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise TextureError(f"Unsafe path in the archive: {name}")
    return path.name.startswith("tex1_") and path.suffix.lower() in EXTENSIONS


def _resolution(top: str) -> str:
    name = top.lower()
    if "1080" in name:
        return "1080p"
    if "4k" in name:
        return "4K"
    return "unknown"


class _Source:
    """The pack's texture files: (relative path, size, read function)."""

    def __init__(self, path: Path):
        self.path = path
        self.entries: list[tuple[PurePosixPath, int, Callable[[], bytes]]] = []
        self.top = ""
        self.zip: Optional[zipfile.ZipFile] = None
        if path.is_dir():
            self._from_folder(path)
        elif zipfile.is_zipfile(path):
            self._from_zip(path)
        else:
            raise TextureError("Choose Henriko's texture pack ZIP or its extracted folder.")
        if not self.entries:
            raise TextureError("No texture files found: is this Henriko's Twilight Princess pack?")

    def _from_zip(self, path: Path) -> None:
        self.zip = zipfile.ZipFile(path)
        infos = self.zip.infolist()
        if sum(i.file_size for i in infos) > MAX_UNPACKED:
            raise TextureError("The archive unpacks to more than 16 GiB.")
        for info in infos:
            if info.is_dir() or not _valid_texture(info.filename):
                continue
            parts = PurePosixPath(info.filename).parts
            if not parts[0].startswith("HenrikosTP"):
                raise TextureError(f"Use the PC Dusklight texture pack from {PAGE}")
            self.top = parts[0]
            relative = PurePosixPath(*parts[1:])
            self.entries.append((relative, info.file_size, lambda i=info: self.zip.read(i)))

    def _from_folder(self, path: Path) -> None:
        root = path
        children = [p for p in path.iterdir() if p.is_dir()]
        # The extracted ZIP holds one top folder; accept it or its parent.
        if len(children) == 1 and children[0].name.startswith("HenrikosTP") and not any(
                p.suffix.lower() in EXTENSIONS for p in path.iterdir() if p.is_file()):
            root = children[0]
        self.top = root.name
        for file in root.rglob("*"):
            if file.is_file() and file.name.startswith("tex1_") and file.suffix.lower() in EXTENSIONS:
                relative = PurePosixPath(file.relative_to(root).as_posix())
                self.entries.append((relative, file.stat().st_size, lambda f=file: f.read_bytes()))


def _aligned_dds(data: bytes) -> bool:
    if len(data) < 20 or data[:4] != b"DDS ":
        return True
    height, width = struct.unpack_from("<II", data, 12)
    return width % 4 == 0 and height % 4 == 0


def _to_png(data: bytes) -> bytes:
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


def inspect(path: Path) -> tuple[str, str, int, int]:
    """(top folder, resolution, texture count, bytes) without converting anything."""
    source = _Source(Path(path))
    return source.top, _resolution(source.top), len(source.entries), sum(s for _, s, _ in source.entries)


def build_tpak(pack: Path, out_path: Path, buttons_zip: Optional[Path] = None,
               progress: Progress = None) -> PackInfo:
    pack, out_path = Path(pack), Path(out_path)
    source = _Source(pack)
    files: dict[PurePosixPath, tuple[int, Callable[[], bytes]]] = {
        relative: (size, read) for relative, size, read in source.entries}
    buttons = 0
    if buttons_zip:
        from .buttons import playstation_buttons
        try:
            images = playstation_buttons(Path(buttons_zip))
        except ValueError as e:
            raise TextureError(str(e)) from e
        # The pack's own button textures make way for the PlayStation ones.
        for relative in [r for r in files if r.parent == BUTTONS_FOLDER]:
            del files[relative]
        for stem, png in images.items():
            files[BUTTONS_FOLDER / f"{stem}.png"] = (len(png), lambda data=png: data)
            buttons += 1
    order = sorted(files, key=_sort_key)
    total = sum(files[r][0] for r in order)
    done = unaligned = 0
    entries = []
    tmp = out_path.with_suffix(out_path.suffix + ".partial")
    with open(tmp, "wb") as out:
        out.write(bytes(64))
        for relative in order:
            size, read = files[relative]
            data = read()
            name = relative
            if relative.suffix.lower() == ".dds" and not _aligned_dds(data):
                data = _to_png(data)
                name = relative.with_suffix(".png")
                unaligned += 1
            offset = out.tell()
            if offset % ALIGN:
                out.write(bytes(ALIGN - offset % ALIGN))
                offset = out.tell()
            out.write(data)
            entries.append((offset, len(data), name.as_posix().encode("utf-8")))
            done += size
            if progress:
                progress(done, total)
        index_offset = out.tell()
        for offset, size, path in entries:
            out.write(struct.pack("<QQH", offset, size, len(path)) + path)
        index_size = out.tell() - index_offset
        out.seek(0)
        out.write(MAGIC + struct.pack("<IIQQ", len(entries), 0, index_offset, index_size))
    os.replace(tmp, out_path)
    digest = ""
    if source.zip is not None:
        with open(pack, "rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
    return PackInfo(str(pack), source.top, _resolution(source.top), len(entries),
                    sum(size for _, size, _ in entries), unaligned, buttons, digest)


def read_tpak_index(path: Path) -> list[tuple[str, int, int]]:
    """(path, offset, size) of every file in a .tpak (for checks and tests)."""
    with open(path, "rb") as f:
        head = f.read(64)
        if head[:8] != MAGIC:
            raise TextureError("Not a .tpak file")
        count, _, index_offset, index_size = struct.unpack_from("<IIQQ", head, 8)
        f.seek(index_offset)
        index = f.read(index_size)
    out, pos = [], 0
    for _ in range(count):
        offset, size, length = struct.unpack_from("<QQH", index, pos)
        pos += 18
        out.append((index[pos:pos + length].decode("utf-8"), offset, size))
        pos += length
    return out
