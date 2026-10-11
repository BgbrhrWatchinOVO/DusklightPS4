# SPDX-License-Identifier: MIT
"""dusklight-setup: the Setup Studio's command line: check, compact, textures, deploy, package, gui."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from . import deploy
from . import disc as discmod
from . import textures


def _progress(label: str):
    start = time.monotonic()
    last = [0.0]

    def report(done: int, total: int) -> None:
        now = time.monotonic()
        if now - last[0] < 0.5 and done < total:
            return
        last[0] = now
        rate = done / max(now - start, 1e-6) / 2**20
        sys.stderr.write(f"\r{label}: {100 * done / max(total, 1):5.1f} %  ({rate:.0f} MiB/s)")
        if done >= total:
            sys.stderr.write("\n")
    return report


def _keys(args):
    if getattr(args, "key", None):
        try:
            return discmod.parse_key_text(args.key)
        except discmod.DiscError as e:
            raise SystemExit(str(e)) from None
    return Path(args.keys) if getattr(args, "keys", None) else None


def cmd_check(args) -> int:
    try:
        d = discmod.Disc(args.image, keys=_keys(args))
    except discmod.DiscError as e:
        print(f"Cannot use this image: {e}")
        return 1
    i = d.info()
    langs = ", ".join(discmod.LANGUAGE_NAMES[l] for l in i.languages)
    print(f"Game:       The Legend of Zelda: Twilight Princess ({i.game_id}, revision {i.revision})")
    print(f"Platform:   {('Wii (encrypted, decrypted with your keys.bin)' if d.encrypted else 'Wii (decrypted)') if i.platform == 'wii' else 'GameCube'}")
    print(f"Region:     {i.region}")
    print(f"Languages:  {langs}")
    print(f"Image:      {i.image_size / 2**30:.2f} GiB, game files {i.files_size / 2**30:.2f} GiB in {i.file_count} files")
    return 0


def cmd_compact(args) -> int:
    try:
        d = discmod.Disc(args.image, keys=_keys(args))
    except discmod.DiscError as e:
        print(f"Cannot use this image: {e}")
        return 1
    size = discmod.compact(d, args.out, _progress("Writing compact image"))
    print(f"{args.out}: {size / 2**30:.2f} GiB (was {d.image_size / 2**30:.2f} GiB)")
    if not args.no_verify:
        copy = discmod.Disc(args.out)
        problems = discmod.verify(d, copy, _progress("Verifying"))
        if problems:
            print(f"VERIFY FAILED: {len(problems)} differences, e.g. {problems[:5]}")
            return 2
        print(f"Verified: all {len(d.files)} files and the system files are identical.")
    return 0


def _bool(value: str) -> bool:
    if value.lower() in ("on", "yes", "true", "1", "an", "ja"):
        return True
    if value.lower() in ("off", "no", "false", "0", "aus", "nein"):
        return False
    raise argparse.ArgumentTypeError("on or off")


def cmd_textures(args) -> int:
    try:
        info = textures.build_tpak(Path(args.pack), Path(args.out), Path(args.buttons) if args.buttons else None,
                                   _progress("Converting textures"))
    except textures.TextureError as e:
        print(f"Cannot use this texture pack: {e}")
        return 1
    print(f"{args.out}: {info.textures} textures ({info.resolution}), {info.size / 2**30:.2f} GiB, "
          f"{info.buttons} PlayStation button textures")
    if info.resolution == "4K":
        print("Warning: the 4K pack needs about four times the graphics memory; the 1080p pack is recommended.")
    return 0


def cmd_deploy(args) -> int:
    """Option B: the Dusklight program package, the game (compacted), the textures and the
    settings onto the PS4 over FTP (deploy.py)."""
    program = Path(args.program) if args.program else deploy.default_program(args.dev)
    if program is None:
        print("Dusklight package not found: pass --program")
        return 1
    opts = deploy.Options(
        image=Path(args.image), host=args.ps4, program=program, work=Path(args.work),
        pack=Path(args.textures) if args.textures else None, tpak=Path(args.tpak) if args.tpak else None,
        buttons=Path(args.buttons) if args.buttons else None, language=args.lang, twilight_hd=args.hud,
        fast_transitions=args.fast_transitions, keys=_keys(args),
        verify_full=args.verify_full, force=args.force,
        dry_run=args.dry_run)
    bars = {}
    labels = {"compact": "Compacting the game image", "verify": "Verifying", "textures": "Converting textures",
              "upload": "Uploading"}

    def report(step: str, done: int, total: int, message: str) -> None:
        if step in labels and total > 1:
            key = (step, message)
            if key not in bars:
                bars[key] = _progress(f"{labels[step]} {message}".strip())
            bars[key](done, total)
        elif message:
            print(f"{step}: {message}")
    try:
        summary = deploy.run(opts, report)
    except (deploy.DeployError, OSError) as e:
        print(f"Failed: {e}")
        return 1
    print("Plan:")
    for local, remote, size in summary["plan"]:
        print(f"  {local}  ->  {remote}  ({size / 2**30:.2f} GiB)")
    print(f"  settings: {summary['settings'] or 'unchanged'}")
    if not args.dry_run:
        print(f"Done. On the PS4: GoldHEN > Package Installer > {program.name}, then start Dusklight.")
    return 0


def cmd_package(args) -> int:
    """The complete package: program, game, textures and settings in one .pkg (package.py)."""
    from . import package
    program = Path(args.program) if args.program else deploy.default_program(args.dev)
    if program is None:
        print("Dusklight package not found: pass --program")
        return 1
    opts = deploy.Options(
        image=Path(args.image), host="", program=program, work=Path(args.work),
        pack=Path(args.textures) if args.textures else None, tpak=Path(args.tpak) if args.tpak else None,
        buttons=Path(args.buttons) if args.buttons else None, language=args.lang, twilight_hd=args.hud,
        fast_transitions=args.fast_transitions, keys=_keys(args))
    bars = {}
    labels = {"compact": "Compacting the game image", "verify": "Verifying", "textures": "Converting textures",
              "package": "Building the package"}

    def report(step: str, done: int, total: int, message: str) -> None:
        if step in labels and total > 1:
            if step not in bars:
                bars[step] = _progress(labels[step])
            bars[step](done, total)
        elif message:
            print(f"{step}: {message}")
    try:
        result = package.build(opts, report)
    except (package.PackageError, deploy.DeployError, OSError) as e:
        print(f"Failed: {e}")
        return 1
    print(f"Done: {result['package']} ({result['size'] / 2**30:.2f} GiB). Install it with a Package Installer "
          "on the PS4.")
    return 0


def cmd_gui(args) -> int:
    from . import web
    return web.serve(port=args.port, open_browser=not args.no_browser, exit_with_stdin=args.exit_with_stdin)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dusklight-setup",
                                     description="Dusklight PS4 Setup Studio (command line)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="recognise a disc image")
    p.add_argument("image")
    p.add_argument("--keys", help="your Wii's keys.bin (BootMii backup), for an encrypted Wii image")
    p.add_argument("--key", help="your Wii's common key as 32 hex digits, instead of --keys")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("compact", help="write a compact copy of a disc image")
    p.add_argument("image")
    p.add_argument("--keys", help="your Wii's keys.bin (BootMii backup), for an encrypted Wii image")
    p.add_argument("--key", help="your Wii's common key as 32 hex digits, instead of --keys")
    p.add_argument("out")
    p.add_argument("--no-verify", action="store_true")
    p.set_defaults(func=cmd_compact)
    p = sub.add_parser("textures", help="convert Henriko's texture pack (ZIP or folder) to a .tpak")
    p.add_argument("pack")
    p.add_argument("out")
    p.add_argument("--buttons", help="Henriko's Xbox + PS UI Buttons Addon (PC), ZIP or folder")
    p.set_defaults(func=cmd_textures)
    p = sub.add_parser("deploy", help="install Dusklight with your game on the PS4 over FTP (option B)")
    p.add_argument("image", help="your GameCube or decrypted Wii image")
    p.add_argument("--keys", help="your Wii's keys.bin (BootMii backup), for an encrypted Wii image")
    p.add_argument("--key", help="your Wii's common key as 32 hex digits, instead of --keys")
    p.add_argument("--ps4", required=True, help="the PS4's IP address (GoldHEN FTP on)")
    p.add_argument("--textures", help="Henriko's texture pack ZIP or folder")
    p.add_argument("--tpak", help="an already converted .tpak instead of --textures")
    p.add_argument("--buttons", help="Henriko's Xbox + PS UI Buttons Addon (PC), ZIP or folder")
    p.add_argument("--lang", type=int, help="game language: 0 English, 1 German, 2 French, 3 Spanish, 4 Italian, 6 Japanese")
    p.add_argument("--hud", type=_bool, help="Wii U-style HUD (Twilight HD): on or off")
    p.add_argument("--fast-transitions", type=_bool)
    p.add_argument("--program", help="Dusklight program package (default: the one shipped)")
    p.add_argument("--dev", action="store_true", help="install the developer version (Dusklight Dev)")
    p.add_argument("--work", default=str(deploy.default_work()), help="working folder")
    p.add_argument("--verify-full", action="store_true", help="read every upload back and compare (slow)")
    p.add_argument("--dry-run", action="store_true", help="prepare and show the plan, transfer nothing")
    p.add_argument("--force", action="store_true", help="send files even if the PS4 has them in the same size")
    p.set_defaults(func=cmd_deploy)
    p = sub.add_parser("package", help="build one complete package with your game (no FTP needed), saved in the "
                                       "folder with the launchers")
    p.add_argument("image", help="your GameCube or Wii image")
    p.add_argument("--keys", help="your Wii's keys.bin (BootMii backup), for an encrypted Wii image")
    p.add_argument("--key", help="your Wii's common key as 32 hex digits, instead of --keys")
    p.add_argument("--textures", help="Henriko's texture pack ZIP or folder")
    p.add_argument("--tpak", help="an already converted .tpak instead of --textures")
    p.add_argument("--buttons", help="Henriko's Xbox + PS UI Buttons Addon (PC), ZIP or folder")
    p.add_argument("--lang", type=int, help="game language: 0 English, 1 German, 2 French, 3 Spanish, 4 Italian, 6 Japanese")
    p.add_argument("--hud", type=_bool, help="Wii U-style HUD (Twilight HD): on or off")
    p.add_argument("--fast-transitions", type=_bool)
    p.add_argument("--program", help="Dusklight program package (default: the one shipped)")
    p.add_argument("--dev", action="store_true", help="package the developer version (Dusklight Dev)")
    p.add_argument("--work", default=str(deploy.default_work()), help="working folder")
    p.set_defaults(func=cmd_package)
    p = sub.add_parser("gui", help="open the assistant")
    p.add_argument("--port", type=int, default=0, help="local port (default: any free one)")
    p.add_argument("--no-browser", action="store_true", help="only print the address")
    p.add_argument("--exit-with-stdin", action="store_true", help="quit when standard input closes (the window app)")
    p.set_defaults(func=cmd_gui)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
