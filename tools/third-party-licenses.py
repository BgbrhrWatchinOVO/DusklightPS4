#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Writes THIRD_PARTY_LICENSES.txt for a Dusklight PS4 release from the licence files of the
pinned source trees (and, for the Setup Studio, of the bundled Python and Pillow).

Usage: third-party-licenses.py <out.txt> [--runtime <extracted python dir> --pillow <PIL dist-info>]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / "build" / "game-final" / "_deps"
SDK = ROOT / "sdk" / "opt" / "pacbrew" / "ps4" / "openorbis" / "usr" / "include"

# (component, what it is used for, licence, files whose text is reproduced)
PROGRAM = [
    ("Dusklight (game code, decompilation, JSystem)", "TwilitRealm/dusklight on zeldaret/tp", "CC0-1.0",
     [ROOT / "src/dusklight/LICENSE.md"]),
    ("Dusklight PS5 port (template for the console layer)", "mshivam019/dusklight-ps5", "CC0-1.0",
     [ROOT / "refs/dusklight-ps5/LICENSE.md"]),
    ("DolphinPS4 runtime (ps4_runtime, crash log, string functions, sampler)", "iHaiDeeZ/DolphinPS4",
     "GPL-2.0-or-later (the program as a whole is distributed under GPL-3.0)", [ROOT / "refs/DolphinPS4/LICENSE"]),
    ("GNM winsys ac_ps4_drm.c", "DolphinPS4", "MIT", ["header:" + str(ROOT / "refs/DolphinPS4/port/mesa/ac_ps4_drm.c"), ROOT / "src/mesa/licenses/MIT"]),
    ("VideoOut WSI", "after PS5_Mesa (Mihawk)", "MIT", ["header:" + str(ROOT / "src/mesa/src/vulkan/wsi/wsi_common_videoout.c"), ROOT / "src/mesa/licenses/MIT"]),
    ("aurora", "encounter/aurora", "MIT", [ROOT / "src/dusklight/extern/aurora/LICENSE"]),
    ("borealis", "TwilitRealm/borealis", "MIT", [ROOT / "src/dusklight/extern/borealis/LICENSE"]),
    ("nod (disc reading, in aurora)", "encounter/nod", "MIT OR Apache-2.0", [DEPS / "aurora_nod-src/LICENSE-MIT"]),
    ("Twilight HD HUD (built in)", "OTPR26/twilight-hd-hud", "MIT", [ROOT / "src/twilight-hd-hud/LICENSE"]),
    ("Mesa (RADV, ACO, NIR, Vulkan runtime, util, addrlib)", "freedesktop.org", "MIT (some files BSL-1.0, Apache-2.0)",
     [ROOT / "src/mesa/docs/license.rst", ROOT / "src/mesa/licenses/MIT", ROOT / "src/mesa/licenses/BSL-1.0"]),
    ("Dawn and Tint (WebGPU)", "Google", "BSD-3-Clause", [ROOT / "src/dawn/LICENSE"]),
    ("SPIRV-Tools", "Khronos (in Dawn)", "Apache-2.0", [ROOT / "src/dawn/third_party/spirv-tools/src/LICENSE"]),
    ("SPIRV-Headers", "Khronos (in Dawn)", "MIT", [ROOT / "src/dawn/third_party/spirv-headers/src/LICENSE"]),
    ("Vulkan-Headers", "Khronos (in Dawn)", "Apache-2.0 OR MIT", [ROOT / "src/dawn/third_party/vulkan-headers/src/LICENSE.md"]),
    ("Vulkan-Utility-Libraries", "Khronos (in Dawn)", "Apache-2.0", [ROOT / "src/dawn/third_party/vulkan-utility-libraries/src/LICENSE.md"]),
    ("Abseil", "Google", "Apache-2.0", [ROOT / "src/abseil/LICENSE"]),
    ("libc++, libc++abi, libunwind", "LLVM 21.1.6", "Apache-2.0 WITH LLVM-exception",
     [ROOT / "src/llvm-project-21.1.6.src/libcxx/LICENSE.TXT"]),
    ("SDL3", "libsdl.org", "Zlib", [ROOT / "src/sdl3/LICENSE.txt"]),
    ("funchook", "kubo/funchook", "GPL-2.0-or-later with linking exception", [DEPS / "funchook-src/LICENSE"]),
    ("diStorm3 (in funchook)", "Gil Dabah", "BSD-3-Clause", [DEPS / "funchook-src/distorm/COPYING"]),
    ("fmt", "Victor Zverovich", "MIT", [DEPS / "fmt-src/LICENSE"]),
    ("Dear ImGui", "Omar Cornut", "MIT", [DEPS / "imgui-src/LICENSE.txt"]),
    ("RmlUi", "RmlUi", "MIT", [DEPS / "rmlui-src/LICENSE.txt"]),
    ("FreeType", "The FreeType Project", "FTL", [DEPS / "freetype-src/docs/FTL.TXT"]),
    ("miniz", "", "MIT", [DEPS / "miniz-src/LICENSE"]),
    ("nlohmann/json", "Niels Lohmann", "MIT", [DEPS / "nlohmann_json-src/LICENSE.MIT"]),
    ("PicoSHA2", "okdshin", "MIT", [DEPS / "picosha2-src/LICENSE"]),
    ("xxHash", "Yann Collet", "BSD-2-Clause", [DEPS / "xxhash-src/LICENSE"]),
    ("zstd", "Meta", "BSD-3-Clause", [DEPS / "zstd-src/LICENSE"]),
    ("cxxopts", "Jarryd Beck", "MIT", [DEPS / "cxxopts-src/LICENSE"]),
    ("Tracy (headers)", "Bartosz Taudul", "BSD-3-Clause", [DEPS / "tracy-src/LICENSE"]),
    ("SQLite", "sqlite.org", "Public domain", []),
    ("libpng", "PS4 SDK", "libpng-2.0", ["header:" + str(SDK / "png.h")]),
    ("zlib", "PS4 SDK", "Zlib", ["header:" + str(SDK / "zlib.h")]),
    ("OpenOrbis PS4 toolchain runtime (crt1.o, libc.a)", "OpenOrbis / PacBrew", "to be confirmed before public release",
     []),
]

ASSETS = [
    ("Alegreya SC", "font in the package", "OFL-1.1", [ROOT / "src/dusklight/ps5/licenses/Alegreya-SC-OFL.txt"]),
    ("Fira Sans, Fira Sans Condensed", "fonts in the package", "OFL-1.1", [ROOT / "src/dusklight/ps5/licenses/Fira-Sans-OFL.txt"]),
    ("Inter", "font in the package", "OFL-1.1", [ROOT / "src/dusklight/ps5/licenses/Inter-OFL.txt"]),
    ("Noto Sans Mono", "font in the package", "OFL-1.1", [ROOT / "src/dusklight/ps5/licenses/Noto-Sans-Mono-OFL.txt"]),
    ("Material Symbols", "icons in the package", "Apache-2.0", [ROOT / "src/dusklight/ps5/licenses/Material-Symbols-Apache-2.0.txt"]),
]


def header_comment(path: Path) -> str:
    """The licence notice from a source file's leading comment."""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"/\*(.*?)\*/", text, re.S)
    if not match:
        raise SystemExit(f"{path}: no leading comment")
    lines = [re.sub(r"^\s*\*? ?", "", l) for l in match.group(1).splitlines()]
    return "\n".join(lines).strip()


def section(name: str, origin: str, licence: str, files: list) -> str:
    out = ["=" * 100, name, f"  {origin}" if origin else "", f"  Licence: {licence}", "=" * 100, ""]
    for f in files:
        if isinstance(f, str) and f.startswith("header:"):
            out += [header_comment(Path(f[7:])), ""]
        else:
            path = Path(f)
            if not path.is_file():
                raise SystemExit(f"missing licence file: {path}")
            out += [path.read_text(encoding="utf-8", errors="replace").rstrip(), ""]
    return "\n".join(l for l in out if l is not None) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--python-licence", help="CPython LICENSE.txt of the bundled runtime")
    parser.add_argument("--pillow-licence", help="Pillow's LICENSE from its wheel")
    args = parser.parse_args()
    parts = ["Dusklight for PS4 – third-party licences",
             "",
             "The PS4 program (Dusklight.pkg, Dusklight-Dev.pkg) is distributed under the GNU General Public",
             "License version 3 (Notices/GPL-3.0.txt), because it contains GPL-2.0-or-later code from DolphinPS4",
             "together with Apache-2.0 code. The components and their licence texts follow.",
             "",
             "PART 1 – THE PS4 PROGRAM", ""]
    parts += [section(*entry) for entry in PROGRAM]
    parts += ["PART 2 – FONTS AND ICONS IN THE PS4 PACKAGE", ""]
    parts += [section(*entry) for entry in ASSETS]
    if args.python_licence or args.pillow_licence:
        parts += ["PART 3 – THE SETUP STUDIO", "",
                  "The Setup Studio's own code is MIT-licensed. It ships portable Python builds from",
                  "astral-sh/python-build-standalone (release 20260924, CPython 3.13.15); these bundle further",
                  "libraries (among them OpenSSL, libffi, SQLite, Tcl/Tk), whose licences that project documents.",
                  ""]
        if args.python_licence:
            parts.append(section("CPython 3.13.15", "Python Software Foundation", "PSF-2.0", [args.python_licence]))
        if args.pillow_licence:
            parts.append(section("Pillow 11.3.0", "Jeffrey A. Clark and contributors", "MIT-CMU", [args.pillow_licence]))
    Path(args.out).write_text("\n".join(parts), encoding="utf-8")
    print(f"{args.out}: {len(PROGRAM) + len(ASSETS)} components")


if __name__ == "__main__":
    main()
