# SPDX-License-Identifier: MIT
"""The complete package: program, game, textures and settings in one .pkg, built on this computer.

The Dusklight program package (WorkshopKit/PS4/Dusklight.pkg) is unpacked into a GP4 project with PkgTool
(LibOrbisPkg), the compact game image and the converted texture pack are added under /app0, where
the port looks first (game.iso, texture_replacements/), the chosen settings go into
default-config.json (they apply when Dusklight starts for the first time), and PkgTool builds the
package again. It is installed with a Package Installer on the PS4; no FTP needed.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from . import config as configmod
from . import deploy
from . import disc as discmod

TOOLS = Path(__file__).resolve().parents[1] / "tools"
OUTPUT_NAME = "Dusklight-Complete.pkg"


def output_dir() -> Path:
    """Where the package is saved: always the folder with the launchers (the one holding
    WorkshopKit/), so it is found next to the Setup Studio that built it."""
    return Path(__file__).resolve().parents[2]


class PackageError(Exception):
    pass


def pkgtool() -> list[str]:
    """PkgTool for this system. macOS runs it with Microsoft's signed dotnet host (an unsigned
    program would not start on Apple silicon)."""
    if sys.platform == "darwin":
        arch = "arm64" if platform.machine() == "arm64" else "x64"
        return [str(TOOLS / "dotnet" / f"macos-{arch}" / "dotnet"), str(TOOLS / "pkgtool" / "portable" / "PkgTool.Core.dll")]
    if os.name == "nt":
        return [str(TOOLS / "pkgtool" / "windows-x64" / "PkgTool.Core.exe")]
    return [str(TOOLS / "pkgtool" / "linux-x64" / "PkgTool.Core")]


def _env() -> dict:
    # No ICU needed (PkgTool compares no localized text); no telemetry.
    return dict(os.environ, DOTNET_SYSTEM_GLOBALIZATION_INVARIANT="1", DOTNET_CLI_TELEMETRY_OPTOUT="1")


def _pkgtool(*args: str) -> None:
    done = subprocess.run(pkgtool() + list(args), capture_output=True, text=True, env=_env())
    if done.returncode != 0:
        raise PackageError(f"PkgTool {args[0]} failed: {(done.stdout + done.stderr).strip()[-800:]}")


def _project(program: Path, project: Path, iso: Path, tpak: Path | None, choices: configmod.Choices) -> int:
    """The GP4 project of the complete package; returns the bytes it holds."""
    shutil.rmtree(project, ignore_errors=True)
    _pkgtool("pkg_makegp4", str(program), str(project))
    config = project / "default-config.json"
    config.write_bytes(configmod.merged(config.read_bytes() if config.exists() else None, choices))
    gp4 = project / "Project.gp4"
    tree = ET.parse(gp4)
    root = tree.getroot()
    files, rootdir = root.find("files"), root.find("rootdir")
    if files is None or rootdir is None:
        raise PackageError("The Dusklight package's project has no file list.")
    # The large files stay where they are: GP4 paths may be absolute.
    ET.SubElement(files, "file", targ_path="game.iso", orig_path=str(iso.resolve()))
    if tpak is not None:
        ET.SubElement(files, "file", targ_path=f"texture_replacements/{tpak.name}", orig_path=str(tpak.resolve()))
        ET.SubElement(rootdir, "dir", targ_name="texture_replacements")
    tree.write(gp4, encoding="utf-8", xml_declaration=True)
    return sum((project / f.get("orig_path")).stat().st_size for f in files.iter("file"))


def build(opts: deploy.Options, report: deploy.Report) -> dict:
    """Builds the complete package into output_dir(); returns {"package": path, "size": bytes}."""
    out_dir = output_dir()
    try:
        game = discmod.Disc(str(opts.image), keys=opts.keys)
    except discmod.DiscError as e:
        raise PackageError(str(e)) from e
    info = game.info()
    if opts.language is not None and opts.language not in info.languages:
        raise PackageError("This disc does not offer the chosen language.")
    if not opts.program.is_file():
        raise PackageError(f"Dusklight program package not found: {opts.program}")
    opts.work.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    iso = deploy.prepare_image(game, opts.image, opts.work, report)
    tpak = opts.tpak
    if tpak is None and opts.pack is not None:
        tpak = deploy.prepare_textures(opts.pack, opts.buttons, opts.work, report)
    choices = configmod.Choices(language=opts.language, textures=True if tpak else False,
                                twilight_hd=opts.twilight_hd, fast_transitions=opts.fast_transitions)

    report("package", 0, 1, "preparing")
    project = opts.work / "package-project"
    total = _project(opts.program, project, iso, tpak, choices)
    free = shutil.disk_usage(out_dir).free
    if total + (256 << 20) > free:
        raise PackageError(f"Not enough free space for the package ({total / 2**30:.1f} GB needed, "
                           f"{free / 2**30:.1f} GB free in {out_dir}).")

    staging = out_dir / ".dusklight-package.partial"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    process = subprocess.Popen(pkgtool() + ["pkg_build", str(project / "Project.gp4"), str(staging)],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=_env())
    while process.poll() is None:
        written = sum(f.stat().st_size for f in staging.glob("*") if f.is_file())
        report("package", min(written, total), total, "")
        time.sleep(1)
    output = process.stdout.read() if process.stdout else ""
    built = sorted(staging.glob("*.pkg"))
    if process.returncode != 0 or not built:
        shutil.rmtree(staging, ignore_errors=True)
        raise PackageError(f"PkgTool could not build the package: {output.strip()[-800:]}")
    target = out_dir / OUTPUT_NAME
    os.replace(built[0], target)
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(project, ignore_errors=True)
    size = target.stat().st_size
    report("package", total, total, target.name)
    report("done", 1, 1, str(target))
    return {"package": str(target), "size": size}
