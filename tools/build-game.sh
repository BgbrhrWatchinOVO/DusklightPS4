#!/usr/bin/env bash
# Configure and build Dusklight for the PS4 (src/dusklight with its ps4/ platform), with
# DolphinPS4's toolchain and link setup, the PS4 Dawn (tools/build-dawn.sh), SDL3
# (tools/build-sdl3.sh) and Mesa (DolphinPS4's scripts/build-mesa.sh). Options as the PS5 port's
# ps5/tools/build.py.
#   build-game.sh [setup]   (setup: reconfigure from scratch)
#
# Profile-guided optimisation (PGO=...):
#   PGO=generate  an instrumented build in build/game-pgogen (tools/build-profile-rt.sh first); it
#                 writes /data/dusklight-ps4/pgo/dusklight.profraw on the console while it runs
#   PGO=use       the release build optimised with pgo/dusklight.profdata (llvm-profdata merge)
# Dawn and Mesa take part: build them first with the same PGO mode (tools/build-dawn.sh,
# tools/build-mesa.sh); the game links build/mesa-pgogen or build/mesa-pgo accordingly.
set -euo pipefail
source "$(dirname "$0")/env.sh"
SRC="$PS4_PORT_ROOT/src/dusklight"
PGO="${PGO:-}"
PGO_PROFILE="${PGO_PROFILE:-$PS4_PORT_ROOT/pgo/dusklight.profdata}"
# The PS4's CPU (AMD Jaguar): AVX, F16C, BMI, and its scheduling.
OPT="-O3 -DNDEBUG -g -march=btver2"
# FLAVOR=final: the release without developer tools (PS4_DEV_TOOLS=OFF) in build/game-final,
# linked with build/mesa-final (tools/build-mesa.sh FLAVOR=final). The default is the developer
# build (profiler, heap checks, diagnostics) in build/game.
FLAVOR="${FLAVOR:-dev}"
case "$FLAVOR" in dev|final) ;; *) echo "FLAVOR must be dev or final" >&2; exit 1 ;; esac
DEV_TOOLS=ON
[ "$FLAVOR" = final ] && DEV_TOOLS=OFF
MESA_BUILD="$PS4_PORT_ROOT/build/mesa"
case "$PGO" in
    "") BUILD="$PS4_PORT_ROOT/build/game" ;;
    generate)
        BUILD="$PS4_PORT_ROOT/build/game-pgogen"
        [ -f "$PS4_PORT_ROOT/build/profile-rt/libclang_rt.profile-ps4.a" ] || "$(dirname "$0")/build-profile-rt.sh"
        OPT="$OPT -fprofile-generate"
        MESA_BUILD="$PS4_PORT_ROOT/build/mesa-pgogen" ;;
    use)
        BUILD="$PS4_PORT_ROOT/build/game"
        [ -f "$PGO_PROFILE" ] || { echo "no $PGO_PROFILE: merge the console's .profraw first" >&2; exit 1; }
        OPT="$OPT -fprofile-use=$PGO_PROFILE -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date -Wno-backend-plugin"
        [ -d "$PS4_PORT_ROOT/build/mesa-pgo" ] && MESA_BUILD="$PS4_PORT_ROOT/build/mesa-pgo" ;;
    *) echo "PGO must be generate or use" >&2; exit 1 ;;
esac
if [ "$FLAVOR" = final ]; then
    [ "$PGO" = generate ] && { echo "FLAVOR=final is a release: PGO=use or none" >&2; exit 1; }
    BUILD="$PS4_PORT_ROOT/build/game-final"
    MESA_BUILD="$PS4_PORT_ROOT/build/mesa-final"
fi

if [ "${1:-}" = setup ] || [ ! -f "$BUILD/build.ninja" ]; then
    rm -rf "$BUILD"
    env -u CFLAGS -u CXXFLAGS -u CPPFLAGS -u LDFLAGS -u LIBS \
        cmake -S "$SRC" -B "$BUILD" -G Ninja \
        -DCMAKE_TOOLCHAIN_FILE="$DOLPHINPS4/toolchain/ps4-love-modern.cmake" \
        "-DCMAKE_PROJECT_dusklight_INCLUDE=$DOLPHINPS4/toolchain/ps4-love-style.cmake" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DPS4_PORT_ROOT="$PS4_PORT_ROOT" -DPS4_MESA_BUILD="$PS4_PORT_ROOT/build/mesa" \
        -DPS4_PAID=0x3800000000000035 \
        -DDUSK_ENABLE_CODE_MODS=ON -DAURORA_DAWN_PROVIDER=vendor \
        -DPS4_SYMGEN="$PS4_PORT_ROOT/downloads/symgen/symgen-linux-x86_64" \
        -DPS4_SYMDB_BYTES=8388608 -DPS4_TWILIGHT_HD_DIR="$PS4_PORT_ROOT/src/twilight-hd-hud" -DFUNCHOOK_DISASM=distorm \
        -DFETCHCONTENT_SOURCE_DIR_DAWN="$PS4_PORT_ROOT/src/dawn" \
        "-DFETCHCONTENT_SOURCE_DIR_ABSEIL-CPP=$PS4_PORT_ROOT/src/abseil" \
        -DAURORA_SDL3_PROVIDER=system -DSDL3_DIR="$PS4_PORT_ROOT/build/sdl3" \
        -DAURORA_ENABLE_TESTS=OFF -DDAWN_SUPPORTS_CXX_MODULES=OFF -DDAWN_BUILD_PROTOBUF=OFF \
        -DTINT_BUILD_IR_BINARY=OFF -DDAWN_ENABLE_VULKAN=ON -DDAWN_ENABLE_DESKTOP_GL=OFF \
        -DDAWN_ENABLE_OPENGLES=OFF -DDAWN_USE_X11=OFF -DDAWN_USE_WAYLAND=OFF \
        -DZSTD_BUILD_DICTBUILDER=OFF
fi
# Optimisation flags and the PGO mode, applied to an existing build too.
cmake "$BUILD" "-DCMAKE_C_FLAGS_RELEASE=$OPT" "-DCMAKE_CXX_FLAGS_RELEASE=$OPT" "-DPS4_PGO=$PGO" \
    -DPS4_MESA_BUILD="$MESA_BUILD" -DPS4_DEV_TOOLS="$DEV_TOOLS" \
    -DPS4_PROFILE_RT="$PS4_PORT_ROOT/build/profile-rt/libclang_rt.profile-ps4.a" > /dev/null
[ "${CONFIGURE_ONLY:-0}" = 1 ] && exit 0
cmake --build "$BUILD" --target dusklight_eboot --parallel "${JOBS:-$(nproc)}" -- ${NINJA_ARGS:-}
