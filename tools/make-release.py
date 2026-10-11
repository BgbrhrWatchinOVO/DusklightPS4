#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assembles the Dusklight release folder (no game data, no textures):

  README.txt, the three Setup Studio launchers,
  WorkshopKit/  the Setup Studio, a portable Python (+ Pillow) per system, and in PS4/
                Dusklight.pkg, Dusklight-Dev.pkg
  HowTo/     player manual, developer notes
  Notices/   GPL-3.0, third-party licences, SOURCE.txt, Code/ (patches against the pinned
              upstream trees, from the trees' working state, and the build scripts)
  SHA256SUMS.txt

Usage: make-release.py <out dir>   (the folder is rebuilt; nothing outside it is touched)
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = ROOT / "build" / "release-runtimes"
PYTHON_TAG = "cpython-3.13.15+20260924"
SYSTEMS = {  # release folder name: (python-build-standalone triple, Pillow wheel platform)
    "windows-x64": ("x86_64-pc-windows-msvc", "win_amd64"),
    "macos-arm64": ("aarch64-apple-darwin", "macosx_11_0_arm64"),
    "macos-x64": ("x86_64-apple-darwin", "macosx_10_13_x86_64"),
    "linux-x64": ("x86_64-unknown-linux-gnu", "manylinux_2_28_x86_64"),
}
# Parts of the portable Python the Setup Studio never uses.
TRIM = ["test", "idlelib", "ensurepip", "lib2to3", "pydoc_data", "turtledemo", "site-packages/pip"]
# (patch name, tree, upstream base the changes start from); diffs run to the working tree, which is
# what was built.
TREES = [
    ("dusklight-ps4.patch", "src/dusklight", "ps5-v0.1.0"),
    ("aurora-ps4.patch", "src/dusklight/extern/aurora", "e281999cdb4fee6127525a9a9e97979480db4bf3"),
    ("borealis-ps4.patch", "src/dusklight/extern/borealis", "4ac5e7052a8c49a122f8d57f626b5c75c5ca6968"),
    ("mesa-26.0.8-ps4.patch", "src/mesa", "80c7811"),
    ("dolphinps4-ps4-runtime.patch", "refs/DolphinPS4", "b1879cc"),
    ("dawn-ps4.patch", "src/dawn", "deps/dawn-ps5"),
    ("sdl3-ps4.patch", "src/sdl3", "deps/sdl3-ps5"),
    ("abseil-ps4.patch", "src/abseil", "deps/abseil-20240722-ps5"),
    ("twilight-hd-ps4.patch", "src/twilight-hd-hud", "v2.5.3"),
]
STATIC_PATCHES = ["libcxx-ps4-atomic-wait.patch", "liborbispkg-ps4-dusklight.patch"]

LAUNCH_WINDOWS = r"""@echo off
rem Dusklight Setup Studio for Windows: starts the assistant in your browser.
setlocal
title Dusklight Setup Studio
cd /d "%~dp0WorkshopKit"
"runtime\windows-x64\python\python.exe" -s -E -B -m dsk_weave6bdf gui
if errorlevel 1 pause
"""

LAUNCH_MACOS = """#!/bin/bash
# Dusklight Setup Studio for macOS: starts the assistant in your browser.
cd "$(dirname "$0")/WorkshopKit" || exit 1
case "$(uname -m)" in
    arm64) runtime=runtime/macos-arm64 ;;
    *) runtime=runtime/macos-x64 ;;
esac
# A downloaded copy carries the quarantine flag on every file; this script was opened on purpose.
xattr -dr com.apple.quarantine "$runtime" 2>/dev/null
"$runtime/python/bin/python3.13" -s -E -B -m dsk_weave6bdf gui
status=$?
if [ $status -ne 0 ]; then read -r -p "Press Enter to close ..."; fi
exit $status
"""

LAUNCH_LINUX = """#!/bin/sh
# Dusklight Setup Studio for Linux: starts the assistant in your browser.
cd "$(dirname "$0")/WorkshopKit" || exit 1
exec runtime/linux-x64/python/bin/python3.13 -s -E -B -m dsk_weave6bdf gui
"""

README = """Dusklight for PS4 – Release r25
==============================

The Legend of Zelda: Twilight Princess as a native PS4 program. This folder contains NO game data:
you bring your own game (GameCube image or decrypted Wii image), the Setup Studio puts it on your PS4.

  1. On the PS4: start GoldHEN and switch on its FTP server.
  2. Here: double-click the Setup Studio for your system
       Windows: Dusklight Setup Studio (Windows).bat
       macOS:   Dusklight Setup Studio (macOS).command
       Linux:   Dusklight Setup Studio (Linux).sh
  3. Follow the assistant in your browser, then install Dusklight.pkg with GoldHEN's Package Installer.

Full manual: HowTo/HowTo (English).html

Contents

  WorkshopKit/   the assistant, a portable Python for Windows, macOS and Linux, and in
                 WorkshopKit/PS4 the game program (Dusklight.pkg) and the developer version
                 (Dusklight-Dev.pkg)
  HowTo/      manual
  Notices/    GPL-3.0, third-party licences, source code
  SHA256SUMS.txt  checksums of every file

Fan project, not affiliated with Nintendo.
"""

SOURCE = """Dusklight for PS4 – source code (GPL-3.0)
==========================================

The PS4 program in WorkshopKit/PS4/ is licensed under the GNU General Public License version 3 (GPL-3.0.txt).
Its corresponding source consists of the upstream source trees below plus the changes in
Code/patches (made from the exact state that was built), and the build scripts in Code/tools.

{trees}
  libc++ 21.1.6
      llvm/llvm-project, base llvmorg-21.1.6, changes: patches/libcxx-ps4-atomic-wait.patch
  LibOrbisPkg (package build tool, not part of the program)
      OpenOrbis/LibOrbisPkg, base 594021f, changes: patches/liborbispkg-ps4-dusklight.patch

Versions in this release: PS4 program r25 (git tags ps4-release-r25), Setup Studio {maker}.
"""

UPSTREAM = {
    "src/dusklight": "mshivam019/dusklight-ps5 (Dusklight PS5 port)",
    "src/dusklight/extern/aurora": "aurora, as pinned by dusklight-ps5",
    "src/dusklight/extern/borealis": "borealis, as pinned by dusklight-ps5",
    "src/mesa": "Mesa 26.0.8 (freedesktop.org)",
    "refs/DolphinPS4": "iHaiDeeZ/DolphinPS4",
    "src/dawn": "Dawn, as pinned by dusklight-ps5",
    "src/sdl3": "SDL3, as pinned by dusklight-ps5",
    "src/abseil": "Abseil 20240722, as pinned by dusklight-ps5",
    "src/twilight-hd-hud": "OTPR26/twilight-hd-hud",
}


def run(*cmd: str, cwd: Path | None = None) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def copy_tree(src: Path, dst: Path) -> None:
    """Copies with symlinks resolved (exFAT and FAT sticks have none)."""
    shutil.copytree(src, dst, symlinks=False, ignore_dangling_symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def add_runtime(name: str, triple: str, wheel_platform: str, out: Path) -> Path:
    archive = RUNTIMES / "downloads" / f"{PYTHON_TAG}-{triple}-install_only_stripped.tar.gz"
    with tempfile.TemporaryDirectory(dir=RUNTIMES) as tmp:
        with tarfile.open(archive) as tar:
            tar.extractall(tmp, filter="tar")
        copy_tree(Path(tmp) / "python", out / name / "python")
    lib = out / name / "python" / ("Lib" if name.startswith("windows") else "lib/python3.13")
    for part in TRIM:
        shutil.rmtree(lib / part, ignore_errors=True)
    # terminfo has names differing only in case (E/Eterm, e/eterm), which clash on exFAT, NTFS and
    # APFS; the Setup Studio uses no terminal features.
    for part in ("share/terminfo", "share/man"):
        shutil.rmtree(out / name / "python" / part, ignore_errors=True)
    for dist in (lib / "site-packages").glob("pip-*.dist-info"):
        shutil.rmtree(dist)
    for bin_name in ("pip", "pip3", "pip3.13", "idle3", "idle3.13", "pydoc3", "pydoc3.13"):
        for candidate in (out / name / "python" / "bin" / bin_name, out / name / "python" / "Scripts" / f"{bin_name}.exe"):
            candidate.unlink(missing_ok=True)
    wheel = next((RUNTIMES / "wheels" / wheel_platform).glob("pillow-*.whl"))
    with zipfile.ZipFile(wheel) as z:
        z.extractall(lib / "site-packages")
    return lib


def source_bundle(out: Path) -> list[str]:
    patches = out / "patches"
    patches.mkdir(parents=True)
    rows = []
    for name, tree, base in TREES:
        diff = run("git", "-C", str(ROOT / tree), "diff", "--binary", "--ignore-submodules=all", base)
        (patches / name).write_text(diff)
        shown = base[:12] if re.fullmatch(r"[0-9a-f]{7,40}", base) else base
        rows.append(f"  {tree}\n      {UPSTREAM[tree]}, base {shown}, changes: patches/{name}")
    for name in STATIC_PATCHES:
        # Hand-made diffs may name local temporary files in their headers: keep only the file name.
        lines = (ROOT / "patches" / name).read_text().splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(("--- ", "+++ ")) and "\t20" in line:  # a diff -u file header
                lines[i] = line[:4] + ("a/" if line[0] == "-" else "b/") + Path(line[4:].split("\t")[0].strip()).name \
                    .removesuffix(".orig") + "\n"
        (patches / name).write_text("".join(lines))
    tools = out / "tools"
    tools.mkdir()
    for script in sorted((ROOT / "tools").iterdir()):
        if script.is_file() and script.suffix in (".sh", ".py"):
            shutil.copy2(script, tools / script.name)
    shutil.copy2(ROOT / "refs/DolphinPS4/port/mesa/ac_ps4_drm.c", tools / "ac_ps4_drm.c")
    return rows


def write(path: Path, text: str, newline: str = "\n") -> None:
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1]).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    sys.path.insert(0, str(ROOT / "maker"))
    from dsk_weave6bdf import __version__ as maker_version

    maker = out / "WorkshopKit"
    (maker / "PS4").mkdir(parents=True)
    for pkg in ("Dusklight.pkg", "Dusklight-Dev.pkg"):
        shutil.copy2(ROOT / "out" / pkg, maker / "PS4" / pkg)
    copy_tree(ROOT / "maker" / "dsk_weave6bdf", maker / "dsk_weave6bdf")
    for extra in ("README.md", "requirements.txt"):
        shutil.copy2(ROOT / "maker" / extra, maker / extra)
    libs = {name: add_runtime(name, triple, wheel, maker / "runtime") for name, (triple, wheel) in SYSTEMS.items()}

    write(out / "Dusklight Setup Studio (Windows).bat", LAUNCH_WINDOWS, "\r\n")
    write(out / "Dusklight Setup Studio (macOS).command", LAUNCH_MACOS)
    write(out / "Dusklight Setup Studio (Linux).sh", LAUNCH_LINUX)
    for launcher in out.glob("Dusklight Setup Studio (*"):
        launcher.chmod(0o755)
    write(out / "README.txt", README, "\r\n")

    manual = out / "HowTo"
    (manual / "Internals").mkdir(parents=True)
    shutil.copy2(ROOT / "docs" / "release" / "HowTo (English).html", manual / "HowTo (English).html")
    shutil.copy2(ROOT / "maker" / "README.md", manual / "Internals" / "WorkshopKit-README.md")

    licenses = out / "Notices"
    licenses.mkdir()
    shutil.copy2(ROOT / "docs" / "GPL-3.0.txt", licenses / "GPL-3.0.txt")
    linux_lib = libs["linux-x64"]
    pillow_licence = next(linux_lib.glob("site-packages/pillow-*.dist-info/licenses/LICENSE"))
    run(sys.executable, str(ROOT / "tools" / "third-party-licenses.py"), str(licenses / "THIRD_PARTY_LICENSES.txt"),
        "--python-licence", str(linux_lib / "LICENSE.txt"), "--pillow-licence", str(pillow_licence))
    rows = source_bundle(licenses / "Code")
    write(licenses / "SOURCE.txt", SOURCE.format(trees="\n".join(rows), maker=maker_version), "\r\n")

    names: dict[str, str] = {}
    for path in out.rglob("*"):
        other = names.setdefault(str(path).lower(), str(path))
        if other != str(path):
            raise SystemExit(f"names differ only in case (they clash on USB sticks): {other}, {path}")
    sums = []
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        with open(path, "rb") as f:
            sums.append(f"{hashlib.file_digest(f, 'sha256').hexdigest()}  {path.relative_to(out).as_posix()}")
    write(out / "SHA256SUMS.txt", "\n".join(sums) + "\n")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"{out}: {len(sums)} files, {size / 2**20:.0f} MiB")


if __name__ == "__main__":
    main()
