# SPDX-License-Identifier: MIT
"""Option B, the published way: Dusklight onto the PS4 with the user's own game, over FTP.

Steps (each reported through `report`, for the command line and the browser assistant alike):
  1. compact the game image (and verify every file against the original),
  2. convert the texture pack, if one was chosen,
  3. back up the console's settings and memory card to this computer,
  4. upload the Dusklight program package, the game image and the texture pack (files the console
     already holds unchanged, by a checksum manifest kept there, are skipped),
  5. merge the chosen settings into the console's config.json.
The program package is then installed with GoldHEN's Package Installer on the console.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import posixpath
from pathlib import Path
from typing import Callable, Optional

from . import __version__
from . import config as configmod
from . import console
from . import disc as discmod
from . import textures


@dataclasses.dataclass
class Options:
    image: Path
    host: str
    program: Path
    work: Path
    pack: Optional[Path] = None        # Henriko ZIP or folder
    tpak: Optional[Path] = None        # an already converted pack instead
    buttons: Optional[Path] = None     # PlayStation button addon ZIP
    language: Optional[int] = None
    twilight_hd: Optional[bool] = None
    fast_transitions: Optional[bool] = None
    keys: Optional[Path | bytes] = None  # for an encrypted Wii image: the user's keys.bin, or the key itself
    verify_full: bool = False
    force: bool = False
    dry_run: bool = False


# report(step, done, total, message): step is one of "compact", "verify", "textures", "backup",
# "upload", "config", "done"; done/total in bytes (0/0 when not measurable).
Report = Callable[[str, int, int, str], None]


class DeployError(Exception):
    pass


def _sha1(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha1").hexdigest()


def prepare_image(game: discmod.Disc, image: Path, work: Path, report: Report) -> Path:
    """The compact copy of the image in `work`, made (and verified) unless it is current."""
    info = game.info()
    out = work / f"{info.game_id}-compact.iso"
    if out.exists() and out.stat().st_mtime >= image.stat().st_mtime:
        report("compact", 1, 1, f"{out.name} is up to date")
        report("verify", 1, 1, "")
        return out
    discmod.compact(game, str(out), lambda d, t: report("compact", d, t, ""))
    problems = discmod.verify(game, discmod.Disc(str(out)), lambda d, t: report("verify", d, t, ""))
    if problems:
        out.unlink(missing_ok=True)
        raise DeployError(f"The compact image differs from the original ({', '.join(problems[:3])}).")
    report("verify", 1, 1, f"all {info.file_count} files identical")
    return out


def _pack_name(top: str) -> str:
    safe = "".join(c for c in top if c.isalnum() or c in "-_.").strip(".")
    return f"{safe or 'textures'}.tpak"


def prepare_textures(pack: Path, buttons: Optional[Path], work: Path, report: Report) -> Path:
    """The converted pack in `work`, named after the pack's folder; converted again only when the
    source (texture count and size, ZIP or addon date) or the Setup Studio changed."""
    try:
        top, resolution, count, size = textures.inspect(pack)
    except (textures.TextureError, OSError) as e:
        raise DeployError(str(e)) from e
    out = work / _pack_name(top)
    stamp = {"maker": __version__, "pack": str(Path(pack).resolve()), "textures": count, "size": size,
             "packTime": Path(pack).stat().st_mtime,
             "buttons": str(Path(buttons).resolve()) if buttons else None,
             "buttonsTime": Path(buttons).stat().st_mtime if buttons else None}
    stamp_file = out.with_suffix(".source.json")
    try:
        current = out.is_file() and json.loads(stamp_file.read_text()) == stamp
    except (OSError, ValueError):
        current = False
    if current:
        report("textures", 1, 1, f"{out.name} is up to date")
        return out
    stamp_file.unlink(missing_ok=True)
    try:
        textures.build_tpak(pack, out, buttons, lambda d, t: report("textures", d, t, ""))
    except textures.TextureError as e:
        raise DeployError(str(e)) from e
    stamp_file.write_text(json.dumps(stamp))
    report("textures", 1, 1, f"{out.name} ({resolution}, {count} textures)")
    return out


def run(opts: Options, report: Report) -> dict:
    """Runs option B; returns a summary. Raises DeployError (or the modules' errors) on failure."""
    try:
        game = discmod.Disc(str(opts.image), keys=opts.keys)
    except discmod.DiscError as e:
        raise DeployError(str(e)) from e
    info = game.info()
    if opts.language is not None and opts.language not in info.languages:
        raise DeployError("This disc does not offer the chosen language.")
    if not opts.program.is_file():
        raise DeployError(f"Dusklight program package not found: {opts.program}")
    opts.work.mkdir(parents=True, exist_ok=True)

    iso = prepare_image(game, opts.image, opts.work, report)
    tpak = opts.tpak
    if tpak is None and opts.pack is not None:
        tpak = prepare_textures(opts.pack, opts.buttons, opts.work, report)

    choices = configmod.Choices(language=opts.language, textures=True if tpak else None,
                                twilight_hd=opts.twilight_hd, fast_transitions=opts.fast_transitions)
    plan = [(opts.program, f"{console.PKG_DIR}/{opts.program.name}"), (iso, f"{console.DATA_DIR}/game.iso")]
    if tpak:
        plan.append((tpak, f"{console.USER_DIR}/texture_replacements/{tpak.name}"))
    summary = {"plan": [(str(l), r, l.stat().st_size) for l, r in plan], "settings": choices.settings(),
               "uploaded": [], "skipped": [], "removed": [], "backup": None}
    if opts.dry_run:
        report("done", 1, 1, "dry run: nothing transferred")
        return summary

    try:
        ps4 = console.Console(opts.host)
    except console.ConsoleError as e:
        raise DeployError(str(e)) from e
    try:
        backup = console.backup_dir(opts.work / "backups")
        report("backup", 0, 1, "")
        saved = ps4.backup_user_data(backup)
        summary["backup"] = {"folder": str(backup), "files": saved}
        report("backup", 1, 1, ", ".join(saved) if saved else "nothing yet (first installation)")

        manifest = ps4.read_manifest()
        for local, remote in plan:
            digest = _sha1(local)
            if not opts.force and manifest.get(remote) == digest and ps4.size(remote) == local.stat().st_size:
                summary["skipped"].append(remote)
                report("upload", 1, 1, f"{local.name}: already on the PS4")
                continue
            ps4.upload(local, remote, lambda d, t, n=local.name: report("upload", d, t, n))
            if opts.verify_full and not ps4.verify_full(local, remote):
                raise DeployError(f"{remote}: the read-back check failed; run again.")
            manifest[remote] = digest
            ps4.write_manifest(manifest)
            summary["uploaded"].append(remote)

        if tpak:
            # The console loads every pack in the folder: one the Setup Studio put there earlier
            # under another name (another resolution) goes, once the new one is complete; packs
            # the user added stay.
            folder = f"{console.USER_DIR}/texture_replacements/"
            stale = [r for r in manifest if r.startswith(folder) and r.endswith(".tpak") and r != plan[-1][1]]
            for remote in stale:
                ps4.remove(remote)
                del manifest[remote]
                summary["removed"].append(remote)
                report("upload", 1, 1, f"{posixpath.basename(remote)}: removed (replaced)")
            if stale:
                ps4.write_manifest(manifest)

        report("config", 0, 1, "")
        existing = ps4.read(f"{console.USER_DIR}/config.json")
        ps4.write(f"{console.USER_DIR}/config.json", configmod.merged(existing, choices))
        report("config", 1, 1, "")
    finally:
        ps4.close()
    report("done", 1, 1, opts.program.name)
    return summary


def default_program(dev: bool) -> Optional[Path]:
    """The Dusklight package shipped with the Setup Studio: WorkshopKit/PS4/ in the release, or the
    port's build output when run from the source tree."""
    name = "Dusklight-Dev.pkg" if dev else "Dusklight.pkg"
    here = Path(__file__).resolve().parent
    for candidate in (here.parent / "PS4" / name, here.parents[1] / "out" / name):
        if candidate.is_file():
            return candidate
    return None


def default_work() -> Path:
    return Path(os.environ.get("DSK_BUILD_329E_WORK", Path.home() / "DskStudioC06f"))
