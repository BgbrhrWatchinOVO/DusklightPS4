#!/usr/bin/env bash
# Build the Dawn probe (probe-dawn/) and package it as DSKL00099, "Dusklight PS4 Probe".
# Needs build/mesa (DolphinPS4's scripts/build-mesa.sh) and build/dawn (tools/build-dawn.sh).
# The package lands in out/.
set -euo pipefail
source "$(dirname "$0")/env.sh"
BUILD="$PS4_PORT_ROOT/build/probe-dawn"
OUT="$PS4_PORT_ROOT/out"

rm -rf "$BUILD"
env -u CFLAGS -u CXXFLAGS -u CPPFLAGS -u LDFLAGS -u LIBS \
    cmake -S "$PS4_PORT_ROOT/probe-dawn" -B "$BUILD" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$DOLPHINPS4/toolchain/ps4-love-modern.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DDOLPHINPS4="$DOLPHINPS4" -DDAWN_SRC="$PS4_PORT_ROOT/src/dawn" \
    -DDAWN_BUILD="$PS4_PORT_ROOT/build/dawn" -DPS4_MESA_BUILD="$PS4_PORT_ROOT/build/mesa" \
    -DPS4_PAID=0x3800000000000035 >/dev/null
cmake --build "$BUILD" --parallel "${JOBS:-$(nproc)}"
eboot="$BUILD/dawn_probe_eboot/eboot.bin"
[ -f "$eboot" ] || { echo "probe: build failed" >&2; exit 1; }

stage="$BUILD/stage"
mkdir -p "$stage/sce_sys"
cp "$eboot" "$stage/"
cp "$DOLPHINPS4/sce_sys/icon0.png" "$stage/sce_sys/"
pkg="$(SFO_STYLE=plain DOLPHIN_PS4_MODULES_DIR=/nonexistent \
    bash "$DOLPHINPS4/scripts/make-pkg.sh" "$stage" DSKL00099 "Dusklight PS4 Probe" 01.00 \
    DUSKPROBE "$OUT" | tail -1)"
echo "probe: $pkg"
