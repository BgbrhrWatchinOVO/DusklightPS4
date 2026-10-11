#!/usr/bin/env bash
# Cross-build Dawn (WebGPU over Vulkan) for the PS4 as one static library, with the options the
# PS5 port uses (ps5/tools/build.py): Vulkan only, no tools, samples or tests.
#   build-dawn.sh [setup]   (setup: reconfigure from scratch)
# PGO=generate instruments it for tools/build-game.sh PGO=generate; PGO=use optimises it with
# PGO_PROFILE (the profile the game is built with). Both in build/dawn, switching rebuilds it: the
# generated sources keep their paths, so the profile matches their functions too.
set -euo pipefail
source "$(dirname "$0")/env.sh"
SRC="$PS4_PORT_ROOT/src/dawn"
BUILD="$PS4_PORT_ROOT/build/dawn"
PGO="${PGO:-}"
PGO_PROFILE="${PGO_PROFILE:-$PS4_PORT_ROOT/pgo/dusklight.profdata}"
OPT="-O3 -DNDEBUG"
case "$PGO" in
    "") ;;
    generate) OPT="$OPT -fprofile-generate" ;;
    use)
        [ -f "$PGO_PROFILE" ] || { echo "no $PGO_PROFILE" >&2; exit 1; }
        OPT="$OPT -fprofile-use=$PGO_PROFILE -Wno-profile-instr-unprofiled -Wno-profile-instr-out-of-date -Wno-backend-plugin" ;;
    *) echo "PGO must be generate or use" >&2; exit 1 ;;
esac

if [ "${1:-}" = setup ] || [ ! -f "$BUILD/build.ninja" ]; then
    rm -rf "$BUILD"
    cmake -S "$SRC" -B "$BUILD" -G Ninja \
        -DCMAKE_TOOLCHAIN_FILE="$PS4_PORT_ROOT/toolchain/ps4.cmake" \
        -DCMAKE_BUILD_TYPE=Release \
        -DDAWN_FETCH_DEPENDENCIES=OFF -DDAWN_BUILD_MONOLITHIC_LIBRARY=STATIC \
        -DDAWN_BUILD_PROTOBUF=OFF -DTINT_BUILD_IR_BINARY=OFF -DDAWN_SUPPORTS_CXX_MODULES=OFF \
        -DDAWN_BUILD_SAMPLES=OFF -DDAWN_BUILD_TESTS=OFF -DDAWN_BUILD_BENCHMARKS=OFF \
        -DDAWN_ENABLE_D3D11=OFF -DDAWN_ENABLE_D3D12=OFF -DDAWN_ENABLE_METAL=OFF \
        -DDAWN_ENABLE_DESKTOP_GL=OFF -DDAWN_ENABLE_OPENGLES=OFF -DDAWN_ENABLE_NULL=OFF \
        -DDAWN_ENABLE_VULKAN=ON -DDAWN_ENABLE_WEBGPU_ON_WEBGPU=OFF \
        -DDAWN_SUPPORTS_GLFW_FOR_WINDOWING=OFF -DDAWN_USE_X11=OFF -DDAWN_USE_WAYLAND=OFF \
        -DTINT_BUILD_TESTS=OFF -DTINT_BUILD_CMD_TOOLS=OFF -DTINT_BUILD_SPV_WRITER=ON \
        -DTINT_BUILD_GLSL_WRITER=OFF -DTINT_BUILD_HLSL_WRITER=OFF -DTINT_BUILD_MSL_WRITER=OFF
fi
# Shader compilation without its debugging checks (SPIR-V validation of every generated module,
# Tint IR validation): they double the time a new pipeline takes on the console.
cmake "$BUILD" -DDAWN_ENABLE_SPIRV_VALIDATION=OFF -DTINT_ENABLE_IR_VALIDATION_ASSERTS=OFF \
    "-DCMAKE_C_FLAGS_RELEASE=$OPT" "-DCMAKE_CXX_FLAGS_RELEASE=$OPT" > /dev/null
cmake --build "$BUILD" --target webgpu_dawn --parallel "${JOBS:-$(nproc)}"
