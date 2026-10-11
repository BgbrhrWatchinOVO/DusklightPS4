#!/usr/bin/env bash
# Package the PS4 build (tools/build-game.sh) as DSKL00001, "Dusklight": eboot.bin, the game's
# res/ folder, the console preset (ps4/default-config.json) and the icon. No game data: the title
# reads your own disc image from /data/dusklight-ps4/game.iso. The package lands in out/ as
# Dusklight-v<RELEASE>.pkg; the release number is also in the title ("Dusklight v2") and APP_VER.
#   RELEASE=2 package-game.sh
#   RELEASE=8 VARIANT=Profiling GAME_BUILD=build/game-pgogen package-game.sh   (another build;
#       the variant is added to the title and the file name)
# Release packages (tools/build-game.sh FLAVOR=...): RELEASE still sets APP_VER.
#   FLAVOR=final  "Dusklight" (DSKL00001), out/Dusklight.pkg, from build/game-final
#   FLAVOR=dev    "Dusklight Dev" (DSKL00002, installs next to it), out/Dusklight-Dev.pkg, build/game
# A complete package, as the Setup Studio builds it on the user's computer from their own files
# (never published): EMBED_ISO=<game.iso> puts the game image in the package (/app0/game.iso),
# EMBED_TPAK=<pack.tpak> a texture pack (/app0/texture_replacements, switched on in the preset).
set -euo pipefail
source "$(dirname "$0")/env.sh"
SRC="$PS4_PORT_ROOT/src/dusklight"
FLAVOR="${FLAVOR:-}"
TITLE_ID=DSKL00001
LABEL=DUSKLIGHT
case "$FLAVOR" in
    "") DEFAULT_BUILD=build/game ;;
    final) DEFAULT_BUILD=build/game-final ;;
    dev) DEFAULT_BUILD=build/game; TITLE_ID=DSKL00002; LABEL=DUSKLIGHTDEV ;;
    *) echo "FLAVOR must be final or dev" >&2; exit 1 ;;
esac
BUILD="$PS4_PORT_ROOT/${GAME_BUILD:-$DEFAULT_BUILD}"
VARIANT="${VARIANT:-}"
OUT="$PS4_PORT_ROOT/out"
RELEASE="${RELEASE:?set RELEASE, the number this build is shown and filed under}"
[[ "$RELEASE" =~ ^[0-9]{1,2}$ ]] || { echo "RELEASE must be a number below 100" >&2; exit 1; }
VERSION="$(printf '%02d.00' "$RELEASE")"
TWILIGHT_HD="$PS4_PORT_ROOT/src/twilight-hd-hud"

eboot="$BUILD/dusklight_eboot/eboot.bin"
[ -f "$eboot" ] || { echo "no $eboot: run tools/build-game.sh" >&2; exit 1; }
# The console starts the title at its entry point as if code began at address 0: a segment in
# front of .text (an orphan section such as SDL3's .note.dlopen) shifts the code and crashes the
# title at launch (CE-34878-0, SIGSEGV at the entry).
first="$(llvm-readelf-21 -lW "$BUILD/dusklight" | awk '$1 == "LOAD" && !seen {print $3, $7, $8; seen = 1}')"
case "$first" in
    "0x0000000000000000 R E") ;;
    *) echo "the first LOAD segment must be code at address 0, not: $first" >&2; exit 1 ;;
esac

stage="$BUILD/stage"
rm -rf "$stage"
mkdir -p "$stage/sce_sys"
cp "$eboot" "$stage/"
cp -r "$SRC/res" "$stage/res"
cp "$SRC/ps4/default-config.json" "$stage/"
if [ -n "${EMBED_ISO:-}" ]; then
    # A hard link where possible: the image is up to 4.7 GB.
    ln "$EMBED_ISO" "$stage/game.iso" 2>/dev/null || cp "$EMBED_ISO" "$stage/game.iso"
fi
if [ -n "${EMBED_TPAK:-}" ]; then
    mkdir -p "$stage/texture_replacements"
    ln "$EMBED_TPAK" "$stage/texture_replacements/" 2>/dev/null || cp "$EMBED_TPAK" "$stage/texture_replacements/"
    sed -i 's/"game.enableTextureReplacements": false/"game.enableTextureReplacements": true/' "$stage/default-config.json"
fi
# The pipeline list Dusklight's own releases bundle (v2.0.3, from the Windows build): aurora
# compiles it in the background, so areas need fewer shaders compiled when first entered.
[ -f "$PS4_PORT_ROOT/assets/initial_pipeline_cache.db" ] && \
    cp "$PS4_PORT_ROOT/assets/initial_pipeline_cache.db" "$stage/"
cp "$SRC/ps5/sce_sys/icon0.png" "$stage/sce_sys/"
# The shell's splash while the game loads (ps4_hide_splash dismisses it at the first frame):
# Dusklight's prelaunch background and logo (assets/pic1.png, 1920x1080, 24-bit).
[ -f "$PS4_PORT_ROOT/assets/pic1.png" ] && cp "$PS4_PORT_ROOT/assets/pic1.png" "$stage/sce_sys/"
# Twilight HD (github.com/OTPR26/twilight-hd-hud, MIT): its code is linked into the game
# (ps4/Platform.cmake), so the package's mod.so only names the built-in module.
if [ -f "$TWILIGHT_HD/mod.json" ]; then
    mod="$stage/mods/twilight_hd_hud"
    mkdir -p "$mod/lib/ps4-x86_64"
    cp "$TWILIGHT_HD/mod.json" "$TWILIGHT_HD/LICENSE" "$mod/"
    printf 'twilight_hd_hud\n' > "$mod/lib/ps4-x86_64/mod.so"
    cp -r "$TWILIGHT_HD/res" "$mod/res"
    cp -r "$TWILIGHT_HD/overlay" "$mod/overlay"
    cp -r "$TWILIGHT_HD/textures-universal" "$mod/textures"
    find "$mod" -name '.*' -exec rm -rf {} +
fi
case "$FLAVOR" in
    final) title="Dusklight"; name="Dusklight" ;;
    dev) title="Dusklight Dev"; name="Dusklight-Dev" ;;
    *) title="Dusklight v$RELEASE${VARIANT:+ ($VARIANT)}"; name="Dusklight-v$RELEASE${VARIANT:+-$VARIANT}" ;;
esac
# LibOrbisPkg's packer aborts on multi-GB packages ("Playgo Chunk hash file was not allocated
# enough space"); src/liborbispkg has the fix, built to build/pkgtool-linux-x64 (dotnet publish).
[ -x "$PS4_PORT_ROOT/build/pkgtool-linux-x64/PkgTool.Core" ] && \
    export PS4_PKGTOOL="$PS4_PORT_ROOT/build/pkgtool-linux-x64/PkgTool.Core"
pkg="$(SFO_STYLE=plain DOLPHIN_PS4_MODULES_DIR=/nonexistent \
    bash "$DOLPHINPS4/scripts/make-pkg.sh" "$stage" "$TITLE_ID" "$title" "$VERSION" \
    "$LABEL" "$OUT" | tail -1)"
named="$OUT/$name.pkg"
mv -f "$pkg" "$named"
# The linked ELF with its debug info, to symbolize crash reports of this release (tools/ps4-crash.sh).
mkdir -p "$OUT/elf"
cp "$BUILD/dusklight" "$OUT/elf/$name-r$RELEASE.elf"
echo "game: $named ($title, $TITLE_ID, APP_VER $VERSION)"
