# Dusklight Setup Studio 0.2.0

Turns your own copy of The Legend of Zelda: Twilight Princess into something your PS4 can run with
Dusklight, the native PS4 port: either one complete package (program, game, textures, settings;
no FTP needed) or an installation over GoldHEN's FTP server. Nothing leaves your computer except
towards your own PS4.

## Start

Double-click the launcher for your system in the release folder (`Dusklight Setup Studio
(Windows).bat`, `(macOS).command`, `(Linux).sh`). It opens the assistant in its own window
(Electron, `gui-frame/`), which starts the Python side (`dsk_weave6bdf`) with the Python
bundled for that system (`runtime/`). Without the window app the launchers open the assistant in
the browser instead (`python -m dsk_weave6bdf gui`).

## Command line

    python -m dsk_weave6bdf check    <image.iso> [--keys keys.bin]
    python -m dsk_weave6bdf compact  <image.iso> <out.iso> [--keys keys.bin]
    python -m dsk_weave6bdf textures <pack.zip|folder> <out.tpak> [--buttons <addon.zip|folder>]
    python -m dsk_weave6bdf package  <image.iso> [--keys keys.bin | --key HEX] [--textures <pack>] [--buttons <addon>] [--lang N]
    python -m dsk_weave6bdf deploy   <image.iso> --ps4 <ip> [--keys keys.bin] [--textures <pack>] [--lang N] [--dry-run]

## What you bring

- Your game as an .iso: GameCube, or Wii (decrypted, or encrypted together with your Wii's
  `keys.bin` from a BootMii backup). Dumping your own disc: https://wii.hacks.guide/dump-games.html
- Optional: Henriko's texture pack (1080p, PC) and the Xbox + PS UI Buttons Addon, ZIP or folder:
  https://www.henrikomagnifico.com/zelda-twilight-princess-4k

The Setup Studio ships no game data and no Nintendo keys.

## Layout

| Folder | What |
|---|---|
| `PS4/` | the Dusklight program: `Dusklight.pkg` and `Dusklight-Dev.pkg` (the base of the complete package, and what the FTP way installs) |
| `dsk_weave6bdf/` | the Setup Studio (Python): disc reading, decryption, compaction, textures, package, FTP, the assistant's pages (`web/`) |
| `gui-frame/` | the window: `main.js` starts the Python side and shows its page, `preload.js` gives the page real paths of dropped files |
| `app/` | Electron 44.4.5 for Windows and Linux; for macOS as ZIP, unpacked on first start (USB sticks hold no symbolic links) |
| `runtime/` | Python 3.13.15 per system, with Pillow 11.3.0 and pycryptodomex 3.23.0 |
| `tools/pkgtool/` | PkgTool (LibOrbisPkg, LGPL-3.0, with our patch for packages over 4 GB) |
| `tools/dotnet/` | Microsoft's .NET 8 runtime for macOS, whose signed `dotnet` runs PkgTool on Apple silicon |

The complete package (`Dusklight-Complete.pkg`) is always saved in the folder with the launchers.
The working folder (compact image, converted pack, backups of your PS4 settings and saves) is
`~/DskStudioC06f`; set `DSK_BUILD_329E_WORK` to use another one.
