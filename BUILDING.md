# Building Dusklight for PS4

> **Status:** these steps follow the scripts in `tools/`, which built release r25. Rebuilding from scratch with only this repository has **not been verified end to end** yet. If something is missing or a patch does not apply, please open an issue or a pull request.

## What the PS4 program is made of

The program is the upstream source trees below plus the changes in `patches/` (made from the exact state that was built) and the scripts in `tools/`.

| Tree (path in the build root) | Upstream | Base | Changes |
|---|---|---|---|
| `src/dusklight` | [mshivam019/dusklight-ps5](https://github.com/mshivam019/dusklight-ps5) (Dusklight PS5 port) | tag `ps5-v0.1.0` | `patches/dusklight-ps4.patch` |
| `src/dusklight/extern/aurora` | aurora, as pinned by dusklight-ps5 | `e281999cdb4f` | `patches/aurora-ps4.patch` |
| `src/dusklight/extern/borealis` | borealis, as pinned by dusklight-ps5 | `4ac5e7052a8c` | `patches/borealis-ps4.patch` |
| `src/mesa` | Mesa 26.0.8 (freedesktop.org) | `80c7811` | `patches/mesa-26.0.8-ps4.patch` |
| `refs/DolphinPS4` | [iHaiDeeZ/DolphinPS4](https://github.com/iHaiDeeZ/DolphinPS4) | `b1879cc` | `patches/dolphinps4-ps4-runtime.patch`; `tools/ac_ps4_drm.c` is its `port/mesa/ac_ps4_drm.c` as built |
| `src/dawn` | Dawn, as pinned by dusklight-ps5 | tag `deps/dawn-ps5` | `patches/dawn-ps4.patch` |
| `src/sdl3` | SDL3, as pinned by dusklight-ps5 | tag `deps/sdl3-ps5` | `patches/sdl3-ps4.patch` |
| `src/abseil` | Abseil 20240722, as pinned by dusklight-ps5 | tag `deps/abseil-20240722-ps5` | `patches/abseil-ps4.patch` |
| `src/twilight-hd-hud` | [OTPR26/twilight-hd-hud](https://github.com/OTPR26/twilight-hd-hud) | `v2.5.3` | `patches/twilight-hd-ps4.patch` |
| libc++ 21.1.6 | llvm/llvm-project | `llvmorg-21.1.6` | `patches/libcxx-ps4-atomic-wait.patch` |
| package tool | OpenOrbis/LibOrbisPkg | `594021f` | `patches/liborbispkg-ps4-dusklight.patch` (full source: `third_party/`) |

## Steps (Linux x86_64 host)

1. **Build root.** Create an empty directory and copy `tools/` and `patches/` from this repository into it. `tools/env.sh` takes the directory above `tools/` as the build root.
2. **Reference trees.**
   - `git clone https://github.com/mshivam019/dusklight-ps5 refs/dusklight-ps5` and fetch its tags (`git -C refs/dusklight-ps5 fetch --tags`); its `deps/*` tags pin Dawn, SDL3 and Abseil.
   - `git clone https://github.com/iHaiDeeZ/DolphinPS4 refs/DolphinPS4`, check out `b1879cc`, apply `patches/dolphinps4-ps4-runtime.patch` and copy `tools/ac_ps4_drm.c` over `refs/DolphinPS4/port/mesa/ac_ps4_drm.c` (DolphinPS4's Mesa build copies that file into Mesa, so edit the port copy, not `src/mesa`).
3. **SDK.** `tools/fetch-openorbis.sh` downloads the PacBrew OpenOrbis SDK packages (SHA-256 checked) into `sdk/`.
4. **Sources.** `tools/fetch-sources.sh` checks out Dusklight, aurora, borealis, Dawn (with its dependencies), SDL3, Abseil, the libdrm headers and the LLVM 21.1.6 source. It uses the GitHub CLI (`gh`) to check the LLVM tarball's digest. Clone Mesa 26.0.8 into `src/mesa` and Twilight HD v2.5.3 into `src/twilight-hd-hud` yourself.
5. **Patches.** Apply each patch in `patches/` to its tree from the table (`git -C <tree> apply <patch>`).
6. **Toolchain sysroot.** Build DolphinPS4's libc++ 21 sysroot and runtime with its own scripts in `refs/DolphinPS4/scripts` (see its README; the libc++ scripts may need `chmod +x`).
7. **Libraries and game**, release flavour:
   ```
   FLAVOR=final tools/build-mesa.sh
   tools/build-dawn.sh
   tools/build-sdl3.sh
   FLAVOR=final tools/build-game.sh
   FLAVOR=final RELEASE=25 tools/package-game.sh
   ```
   The package lands in `out/`. `FLAVOR=dev` (the default) builds the Dev variant with profiler and diagnostics.

## Notes

- **No PGO profile is included.** Release r25 was built with profile-guided optimisation (`PGO=use` with a profile recorded on the console). Without it the build is a normal `-O3` build and somewhat slower. To make your own profile: `tools/build-profile-rt.sh`, a `PGO=generate` build of Mesa, Dawn and the game, play for 15+ minutes, `tools/pgo-merge.sh <ps4 ip>`, then build with `PGO=use`.
- The PS4's CPU is an AMD Jaguar: the game builds with `-march=btver2`. The decompiled JSystem and aurora libraries build with UB guards (`-ftrivial-auto-var-init=zero -fno-strict-aliasing -fwrapv -fno-delete-null-pointer-checks`), because aggressive inlining exposed undefined behaviour in the original code.
- Diagnostics: `tools/ps4-crash.sh <ip> [elf]` symbolises DolphinPS4's crash log, `tools/ps4-samples.py` reads the Dev build's sampling profiler output.
- The Setup Studio needs no build: `cd setup-studio && python -m dsk_weave6bdf gui` (Python 3.11+, `pip install -r requirements.txt`). The release ZIP adds Electron, Python per system and PkgTool.
