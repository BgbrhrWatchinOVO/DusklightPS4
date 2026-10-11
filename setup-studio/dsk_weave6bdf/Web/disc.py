# SPDX-License-Identifier: MIT
"""Game disc images for the Dusklight PS4 Setup Studio: recognise them and write compact copies.

Formats the PS4 port reads (src/dusklight/ps4/disc/raw_disc.cpp):
  - GameCube: a raw image (GZ2E01, GZ2P01, GZ2J01 ...),
  - Wii: an image whose data partition is already decrypted (RZDE01, RZDP01, RZDJ01 ...).
Encrypted Wii images, WBFS/RVZ and Wii U images are recognised and refused with a reason: the
Setup Studio contains no decryption.

A Wii image is always the size of a whole disc (4.7 GB) although Twilight Princess's files take
about 1 GB; Nintendo also placed some files at the end of the disc. `compact()` writes the same
format with only the system files and the game files, packed one after the other, and an updated
file table: about a quarter of the size. `verify()` compares every file of the copy with the
original.
"""
from __future__ import annotations

import dataclasses
import hashlib
import os
try:
    from Cryptodome.Cipher import AES  # pycryptodomex, bundled with the Setup Studio
except ImportError:  # pragma: no cover - only decryption needs it
    AES = None
from pathlib import Path
import struct
from typing import BinaryIO, Callable, Iterator, Optional

GC_MAGIC = 0xC2339F3D
WII_MAGIC = 0x5D1C9EA3
WII_PARTITION_INFO = 0x40000
WII_REGION_INFO = 0x4E000
WII_CLUSTER = 0x8000       # a cluster of a Wii partition: hashes + data
WII_CLUSTER_HASH = 0x400
WII_CLUSTER_DATA = 0x7C00
FILE_ALIGN = 0x800         # file placement in the compact image (a DVD sector)
COPY_CHUNK = 4 << 20

# dusk::GameLanguage (src/dusk/settings.h): the values game.language takes.
LANG_ENGLISH, LANG_GERMAN, LANG_FRENCH, LANG_SPANISH, LANG_ITALIAN, LANG_JAPANESE = 0, 1, 2, 3, 4, 6
LANGUAGE_NAMES = {LANG_ENGLISH: "English", LANG_GERMAN: "Deutsch", LANG_FRENCH: "Français",
                  LANG_SPANISH: "Español", LANG_ITALIAN: "Italiano", LANG_JAPANESE: "日本語"}

# Twilight Princess's discs; other games are refused.
SUPPORTED_GAMES = {"GZ2": "gamecube", "RZD": "wii"}

Progress = Optional[Callable[[int, int], None]]  # (done, total) in bytes


class DiscError(Exception):
    """An image the PS4 port cannot use; the message says why and what to do."""


def be32(data: bytes, offset: int = 0) -> int:
    return struct.unpack_from(">I", data, offset)[0]


@dataclasses.dataclass
class FstFile:
    index: int      # entry number in the file table
    path: str
    offset: int     # in the data partition (Wii) or the image (GameCube)
    size: int


@dataclasses.dataclass
class DiscInfo:
    platform: str           # "gamecube" or "wii"
    game_id: str            # e.g. "RZDP01"
    revision: int
    region: str             # "Europe", "NorthAmerica", "Japan", "Korea"
    languages: list[int]    # game.language values the disc offers
    image_size: int
    files_size: int         # sum of the game files
    file_count: int


def region_of(game_id: str) -> str:
    code = game_id[3]
    if code == "E":
        return "NorthAmerica"
    if code == "J":
        return "Japan"
    if code == "K":
        return "Korea"
    return "Europe"


def languages_of(platform: str, region: str, revision: int) -> list[int]:
    """The languages Dusklight offers for a disc (src/dusk/language.cpp)."""
    if region == "Japan":
        return [LANG_JAPANESE]
    if region == "Europe":
        return [LANG_ENGLISH, LANG_GERMAN, LANG_FRENCH, LANG_SPANISH, LANG_ITALIAN]
    if region == "NorthAmerica" and platform == "wii" and revision == 2:
        return [LANG_ENGLISH, LANG_FRENCH, LANG_SPANISH]
    return [LANG_ENGLISH]


NEEDS_KEYS = ("This Wii image is encrypted. Add your Wii key (paste it, or choose the keys.bin from your "
              "own Wii's BootMii backup), and the Setup Studio decrypts it while compacting.")


def parse_key_text(text: str) -> bytes:
    """A key pasted as text: 32 hex digits, spaces, colons and dashes allowed."""
    digits = "".join(c for c in text if c not in " :-\t\r\n")
    if len(digits) != 32 or any(c not in "0123456789abcdefABCDEF" for c in digits):
        raise DiscError("The Wii key must be 32 hexadecimal characters (0-9, a-f).")
    return bytes.fromhex(digits)


def load_common_key(source) -> bytes:
    """The Wii common key from the user's own console: the 16 key bytes themselves (pasted), or a
    file: BootMii's keys.bin (0x400 bytes, the key at 0x114), a 16-byte key file, or the key as 32
    hex digits in a text file. The Setup Studio ships no key."""
    if isinstance(source, (bytes, bytearray)):
        if len(source) != 16:
            raise DiscError("The Wii key must be 16 bytes.")
        return bytes(source)
    try:
        data = Path(source).read_bytes()
    except OSError as e:
        raise DiscError(f"The keys file cannot be read: {e}") from e
    if len(data) == 0x400:
        return data[0x114:0x124]
    if len(data) == 16:
        return data
    text = data.decode("ascii", "ignore").strip()
    if len(text) == 32 and all(c in "0123456789abcdefABCDEF" for c in text):
        return bytes.fromhex(text)
    raise DiscError("This is not a Wii keys file: choose the keys.bin from your Wii's BootMii backup.")


class Disc:
    """An opened GameCube or Wii image (a decrypted one, or an encrypted one with `keys`, the
    user's keys.bin). Offsets passed to `read` are in the game's data space: the image itself for
    GameCube, the data partition's clusters for Wii (decrypted on the fly when encrypted)."""

    def __init__(self, path: str, keys=None):
        self.path = path
        self.keys = keys
        self.encrypted = False
        self.title_key = b""
        self._clusters: dict[int, bytes] = {}
        self.file: BinaryIO = open(path, "rb")
        self.image_size = os.fstat(self.file.fileno()).st_size
        self.data_start = 0     # Wii: the data partition's clusters
        self.data_size = 0      # Wii: bytes of game data the image holds
        self.partition = 0      # Wii: the data partition
        head = self._raw(0, 0x440)
        if len(head) < 0x440:
            raise DiscError("The file is too small to be a disc image.")
        if head[:4] == b"WBFS":
            raise DiscError("This is a WBFS file. Convert it to an ISO first (for example with Dolphin or wit).")
        if head[:4] in (b"RVZ\x01", b"WIA\x01"):
            raise DiscError("This is a compressed RVZ/WIA image. Convert it to an ISO first (for example with Dolphin).")
        self.game_id = head[:6].decode("ascii", "replace")
        self.revision = head[7]
        if be32(head, 0x18) == WII_MAGIC:
            self.platform = "wii"
            self._open_wii(head)
        elif be32(head, 0x1C) == GC_MAGIC:
            self.platform = "gamecube"
        else:
            raise DiscError("Not a GameCube or Wii image (Wii U images are not supported).")
        prefix = self.game_id[:3]
        if SUPPORTED_GAMES.get(prefix) != self.platform:
            raise DiscError(f"{self.game_id} is not The Legend of Zelda: Twilight Princess.")
        self.header = self.read(0, 0x440)
        self.files = list(self._read_fst())

    # --- reading ----------------------------------------------------------------------------
    def _raw(self, offset: int, size: int) -> bytes:
        self.file.seek(offset)
        return self.file.read(size)

    def _cluster(self, index: int) -> bytes:
        """One cluster's game data, decrypted (the IV is in the encrypted hash block)."""
        data = self._clusters.get(index)
        if data is None:
            raw = self._raw(self.data_start + index * WII_CLUSTER, WII_CLUSTER)
            if len(raw) != WII_CLUSTER:
                raise DiscError("The image ends early (truncated download or copy?).")
            data = AES.new(self.title_key, AES.MODE_CBC, raw[0x3D0:0x3E0]).decrypt(raw[WII_CLUSTER_HASH:])
            if len(self._clusters) >= 64:
                self._clusters.pop(next(iter(self._clusters)))
            self._clusters[index] = data
        return data

    def read(self, offset: int, size: int) -> bytes:
        if self.platform == "gamecube":
            return self._raw(offset, size)
        out = bytearray()
        while size > 0:
            cluster, within = divmod(offset, WII_CLUSTER_DATA)
            n = min(size, WII_CLUSTER_DATA - within)
            if self.encrypted:
                chunk = self._cluster(cluster)[within:within + n]
            else:
                chunk = self._raw(self.data_start + cluster * WII_CLUSTER + WII_CLUSTER_HASH + within, n)
            if len(chunk) != n:
                raise DiscError("The image ends early (truncated download or copy?).")
            out += chunk
            offset += n
            size -= n
        return bytes(out)

    def _open_wii(self, head: bytes) -> None:
        info = self._raw(WII_PARTITION_INFO, 8)
        count, table = be32(info), be32(info, 4) << 2
        if not 0 < count <= 64:
            raise DiscError("The Wii partition table is damaged.")
        for i in range(count):
            entry = self._raw(table + i * 8, 8)
            if be32(entry, 4) != 0:  # 0 = the game's data partition
                continue
            self.partition = be32(entry) << 2
            fields = self._raw(self.partition + 0x2B8, 8)
            self.data_start = self.partition + (be32(fields) << 2)
            stored = be32(fields, 4) << 2
            self.data_size = min(stored, self.image_size - self.data_start) // WII_CLUSTER * WII_CLUSTER_DATA
            inner = self.read(0, 0x20)
            if inner[:6] != head[:6] or be32(inner, 0x18) != WII_MAGIC:
                self._decrypt(head)
            return
        raise DiscError("The Wii image has no game data partition.")

    def _decrypt(self, head: bytes) -> None:
        """Opens the encrypted data partition: the title key from the ticket, decrypted with the
        common key from the user's keys.bin, checked against the inner disc header."""
        if self.keys is None:
            raise DiscError(NEEDS_KEYS)
        if AES is None:
            raise DiscError("Decrypting needs the pycryptodomex module, which comes with the Setup Studio.")
        ticket = self._raw(self.partition, 0x2A4)
        encrypted_key, title_id, key_index = ticket[0x1BF:0x1CF], ticket[0x1DC:0x1E4], ticket[0x1F1]
        if key_index != 0:
            raise DiscError("This disc needs the Korean Wii key, which a keys.bin does not hold.")
        common = load_common_key(self.keys)
        self.title_key = AES.new(common, AES.MODE_CBC, title_id + bytes(8)).decrypt(encrypted_key)
        self.encrypted = True
        self._clusters.clear()
        inner = self.read(0, 0x20)
        if inner[:6] != head[:6] or be32(inner, 0x18) != WII_MAGIC:
            raise DiscError("This Wii key does not fit the disc: is it the common key from a Wii's keys.bin?")

    def _shift(self) -> int:
        return 2 if self.platform == "wii" else 0

    def _read_fst(self) -> Iterator[FstFile]:
        s = self._shift()
        fst_offset, fst_size = be32(self.header, 0x424) << s, be32(self.header, 0x428) << s
        self.fst = self.read(fst_offset, fst_size)
        count = be32(self.fst, 8)
        names = 12 * count
        # Directory nesting: an entry's path comes from the directories whose range covers it.
        stack: list[tuple[int, str]] = []
        for i in range(1, count):
            while stack and i >= stack[-1][0]:
                stack.pop()
            word = be32(self.fst, i * 12)
            name_offset = word & 0xFFFFFF
            end = self.fst.index(b"\0", names + name_offset)
            name = self.fst[names + name_offset:end].decode("shift_jis", "replace")
            path = "/".join([p for _, p in stack] + [name])
            if word >> 24:  # directory: second word = parent, third = next entry after it
                stack.append((be32(self.fst, i * 12 + 8), name))
            else:
                yield FstFile(i, path, be32(self.fst, i * 12 + 4) << s, be32(self.fst, i * 12 + 8))

    def info(self) -> DiscInfo:
        region = region_of(self.game_id)
        return DiscInfo(self.platform, self.game_id, self.revision, region,
                        languages_of(self.platform, region, self.revision), self.image_size,
                        sum(f.size for f in self.files), len(self.files))

    # --- system files -----------------------------------------------------------------------
    def apploader_size(self) -> int:
        head = self.read(0x2440, 0x20)
        return 0x20 + be32(head, 0x14) + be32(head, 0x18)

    def dol_range(self) -> tuple[int, int]:
        offset = be32(self.header, 0x420) << self._shift()
        dol = self.read(offset, 0x100)
        end = 0x100
        for i in range(18):  # 7 text + 11 data sections
            sec_off, sec_size = be32(dol, i * 4), be32(dol, 0x90 + i * 4)
            if sec_size:
                end = max(end, sec_off + sec_size)
        return offset, end

    def close(self) -> None:
        self.file.close()


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


class _DataWriter:
    """Writes game data in the image's format: linearly (GameCube) or as decrypted Wii clusters
    (zero hashes, which the PS4 port skips)."""

    def __init__(self, out: BinaryIO, wii: bool):
        self.out, self.wii = out, wii
        self.pending = bytearray()
        self.written = 0  # data bytes

    def write(self, data: bytes) -> None:
        if not self.wii:
            self.out.write(data)
            self.written += len(data)
            return
        self.pending += data
        while len(self.pending) >= WII_CLUSTER_DATA:
            self.out.write(bytes(WII_CLUSTER_HASH))
            self.out.write(self.pending[:WII_CLUSTER_DATA])
            del self.pending[:WII_CLUSTER_DATA]
            self.written += WII_CLUSTER_DATA

    def pad_to(self, offset: int) -> None:
        current = self.written + len(self.pending)
        if offset < current:
            raise ValueError("layout overlaps")
        while current < offset:
            n = min(offset - current, COPY_CHUNK)
            self.write(bytes(n))
            current += n

    def finish(self) -> int:
        if self.wii and self.pending:
            self.pending += bytes(WII_CLUSTER_DATA - len(self.pending))
            self.write(b"")
        return self.written


def compact(disc: Disc, out_path: str, progress: Progress = None) -> int:
    """Writes a compact copy of `disc` to `out_path`; returns its size in bytes."""
    s = disc._shift()
    wii = disc.platform == "wii"
    # Layout of the game data: boot header, bi2, apploader as they are; then the DOL, the file
    # table and the files, each aligned, in the order of the original (keeps related files near).
    apploader_end = 0x2440 + disc.apploader_size()
    dol_offset, dol_size = disc.dol_range()
    new_dol = _align(apploader_end, FILE_ALIGN)
    new_fst = _align(new_dol + dol_size, FILE_ALIGN)
    fst = bytearray(disc.fst)
    cursor = _align(new_fst + len(fst), FILE_ALIGN)
    placement: list[tuple[FstFile, int]] = []
    for f in sorted(disc.files, key=lambda f: f.offset):
        placement.append((f, cursor))
        struct.pack_into(">I", fst, f.index * 12 + 4, cursor >> s)
        cursor = _align(cursor + f.size, FILE_ALIGN)
    data_end = cursor

    header = bytearray(disc.read(0, apploader_end))
    struct.pack_into(">I", header, 0x420, new_dol >> s)
    struct.pack_into(">I", header, 0x424, new_fst >> s)
    struct.pack_into(">I", header, 0x428, len(fst) >> s)
    struct.pack_into(">I", header, 0x42C, len(fst) >> s)

    total = data_end
    done = 0
    with open(out_path, "wb") as out:
        if wii:
            # Disc header, partition table and region info as they are; one partition (the game's)
            # right after, its header (ticket, TMD, certificates, H3 table) copied, its data size set.
            outer = bytearray(disc._raw(0, 0x50000))
            struct.pack_into(">IIIIIIII", outer, WII_PARTITION_INFO, 1, (WII_PARTITION_INFO + 0x20) >> 2,
                             0, 0, 0, 0, 0, 0)
            partition = 0x50000
            struct.pack_into(">II", outer, WII_PARTITION_INFO + 0x20, partition >> 2, 0)
            out.write(outer)
            data_offset = disc.data_start - disc.partition
            part_header = bytearray(disc._raw(disc.partition, data_offset))
            clusters = _align(data_end, WII_CLUSTER_DATA) // WII_CLUSTER_DATA
            struct.pack_into(">I", part_header, 0x2BC, (clusters * WII_CLUSTER) >> 2)
            out.write(part_header)
        writer = _DataWriter(out, wii)
        writer.write(bytes(header))
        writer.pad_to(new_dol)
        writer.write(disc.read(dol_offset, dol_size))
        writer.pad_to(new_fst)
        writer.write(bytes(fst))
        for f, offset in placement:
            writer.pad_to(offset)
            remaining, source = f.size, f.offset
            while remaining:
                n = min(remaining, COPY_CHUNK)
                writer.write(disc.read(source, n))
                source += n
                remaining -= n
                done += n
                if progress:
                    progress(done, total)
        writer.pad_to(data_end)
        writer.finish()
    return os.path.getsize(out_path)


def file_digests(disc: Disc, progress: Progress = None) -> dict[str, str]:
    """SHA-1 of every game file and of the system files, by path."""
    digests = {}
    total = disc.info().files_size
    done = 0
    dol_offset, dol_size = disc.dol_range()
    digests["sys/main.dol"] = hashlib.sha1(disc.read(dol_offset, dol_size)).hexdigest()
    digests["sys/apploader.img"] = hashlib.sha1(disc.read(0x2440, disc.apploader_size())).hexdigest()
    digests["sys/bi2.bin"] = hashlib.sha1(disc.read(0x440, 0x2000)).hexdigest()
    for f in disc.files:
        h = hashlib.sha1()
        remaining, offset = f.size, f.offset
        while remaining:
            n = min(remaining, COPY_CHUNK)
            h.update(disc.read(offset, n))
            offset += n
            remaining -= n
            done += n
            if progress:
                progress(done, total)
        digests[f.path] = h.hexdigest()
    return digests


def verify(original: Disc, copy: Disc, progress: Progress = None) -> list[str]:
    """Paths whose content differs between the two images (empty: identical game data)."""
    a = file_digests(original, progress)
    b = file_digests(copy)
    problems = [p for p in sorted(set(a) | set(b)) if a.get(p) != b.get(p)]
    if original.game_id != copy.game_id:
        problems.append("game id")
    return problems
