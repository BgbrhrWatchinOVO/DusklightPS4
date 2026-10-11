# Dusklight for PS4

*The Legend of Zelda: Twilight Princess as a native PS4 program – not an emulator.*

A PS4 port of **Dusklight**, the PC port built on the Twilight Princess decompilation. The game code runs natively on the console – no Dolphin, no emulation layer.

**This repository and the releases contain no game data and no keys.** You need your own disc, dumped yourself. The Setup Studio builds the PS4 package on your own computer.

## Download

Get **DusklightPS4Port.zip** from the [Releases](../../releases) page (release r25, Setup Studio 0.2.0).

SHA-256: `26e0ece7672d6ce0273c4fd285adcd77a49ecc750b3a21cc490e7efeaef4981f`

Mirror: [megaup.net](https://megaup.net/82b8eaff24918636eb5856bcf62b3406/DusklightPS4Port.zip)

## Features

- Native PS4 program (OpenOrbis toolchain, Mesa RADV on GNM, Dawn/WebGPU renderer)
- Up to 60 FPS – on a PS4 Pro mostly a locked 60, short dips into the 50s in busy areas like Castle Town
- PlayStation buttons in Nintendo positions (Circle = A, Cross = B, Triangle/Square = X/Y)
- Wii U style HUD built in (Twilight HD HUD), can be switched off
- Optional HD textures – Henriko's pack, **not included**, download it from his page
- Faster scene transitions option, Dusklight menu on the touchpad
- Release build + Dev build (frame counter and logs for troubleshooting)

## Requirements

- PS4 or PS4 Pro with GoldHEN
- **Your own dump of the game as .iso**
    - GameCube: GZ2E01 / GZ2P01 / GZ2J01
    - Wii: RZDE01 / RZDP01 / RZDJ01 – decrypted, or encrypted together with the keys.bin from a BootMii NAND backup of your own Wii
    - Not supported: WBFS/RVZ (convert to ISO first), the Wii U HD version
    - Dump guide: [wii.hacks.guide/dump-games.html](https://wii.hacks.guide/dump-games.html) ([CleanRip](https://github.com/emukidid/cleanrip))
- *Optional:* Henriko's Twilight Princess 4K pack, **1080p version for Dusklight (PC)**, plus the "Xbox + PS UI Buttons Addon": [henrikomagnifico.com](https://www.henrikomagnifico.com/zelda-twilight-princess-4k)
- A PC with Windows 64-bit, macOS (Apple silicon/Intel) or Linux 64-bit – nothing to install

## How to install

1. Extract the ZIP and start the Setup Studio for your system (.bat / .command / .sh)
2. Drag your .iso into the window (optionally the texture pack and button addon too)
3. Choose language, HUD and transitions → **Build complete package** (~3 GB, a few minutes)
4. Copy *Dusklight-Complete.pkg* to an exFAT USB drive and install it with GoldHEN's Package Installer
5. Start Dusklight from the home screen

Sending everything over FTP instead is also possible. The full manual is in [docs/manual.html](docs/manual.html) and in the *HowTo* folder of the release.

## Known issues / testing status

- Tested on a PS4 Pro. On a base/slim PS4 expect lower frame rates in the field (slower CPU)
- Setup Studio tested on Linux; Windows and macOS untested so far
- Error CE-34878-0: restart the PS4 **completely** (not rest mode), otherwise the next start can be very slow
- "Disc check" notice with decrypted Wii images is normal → "Continue anyway"

Reports are welcome as issues.

## Repository layout

| Path | What |
|---|---|
| `patches/` | the PS4 changes, as patches against the exact upstream commits listed in [BUILDING.md](BUILDING.md) |
| `tools/` | build, packaging and diagnostic scripts; `tools/ac_ps4_drm.c` is the PS4 GNM winsys for Mesa as built |
| `setup-studio/` | source of the Setup Studio (Python + Electron window); the release ZIP adds the bundled runtimes |
| `third_party/` | LibOrbisPkg 594021f with this project's patch (the package tool, LGPL-3.0) |
| `docs/` | the player manual |

## Building from source

See [BUILDING.md](BUILDING.md). Rebuilding from these patches has not been verified end to end yet – reports and fixes are very welcome.

## License

The PS4 program is GPL-3.0 (see [LICENSE](LICENSE)); third-party licenses are in [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt). Forks and mirrors are welcome.

## Credits

- zeldaret – Twilight Princess decompilation
- TwilitRealm – Dusklight (PC port)
- mshivam019 – Dusklight PS5 port (base of this port)
- iHaiDeeZ – DolphinPS4 (PS4 platform layer, Mesa on GNM)
- OTPR26 – Twilight HD HUD
- Henriko – HD texture pack (linked, not included)
- OpenOrbis (toolchain, LibOrbisPkg), the GoldHEN team, Mesa, Dawn, SDL, LLVM

---

Fan project, not affiliated with Nintendo. "The Legend of Zelda" and "Twilight Princess" are trademarks of Nintendo. Game files and keys are not provided; issues asking for them will be closed.
