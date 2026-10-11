#!/usr/bin/env bash
# Cross-build SDL3 for the PS4 as a static library, with the PS5 port's options
# (ps5/tools/build.py): console build, no window system, GPU API or HIDAPI; SceAudioOut audio.
#   build-sdl3.sh [setup]   (setup: reconfigure from scratch)
set -euo pipefail
source "$(dirname "$0")/env.sh"
SRC="$PS4_PORT_ROOT/src/sdl3"
BUILD="$PS4_PORT_ROOT/build/sdl3"

if [ "${1:-}" = setup ] || [ ! -f "$BUILD/build.ninja" ]; then
    rm -rf "$BUILD"
    cmake -S "$SRC" -B "$BUILD" -G Ninja \
        -DCMAKE_TOOLCHAIN_FILE="$PS4_PORT_ROOT/toolchain/ps4.cmake" \
        -DCMAKE_BUILD_TYPE=Release \
        -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TEST_LIBRARY=OFF -DSDL_TESTS=OFF \
        -DSDL_UNIX_CONSOLE_BUILD=ON -DSDL_X11=OFF -DSDL_WAYLAND=OFF -DSDL_KMSDRM=OFF \
        -DSDL_AUDIO=ON -DSDL_JOYSTICK=ON -DSDL_HAPTIC=ON -DSDL_SENSOR=ON -DSDL_HIDAPI=OFF \
        -DSDL_DUMMYAUDIO=OFF -DSDL_DISKAUDIO=OFF -DSDL_CAMERA=OFF -DSDL_DIALOG=OFF -DSDL_TRAY=OFF \
        -DSDL_VULKAN=OFF -DSDL_OPENGL=OFF -DSDL_OPENGLES=OFF \
        -DLIBC_HAS_WCSNLEN=OFF -DLIBC_HAS_WCSLCPY=OFF -DLIBC_HAS_WCSLCAT=OFF \
        -DSDL_DLOPEN_NOTES=OFF
fi
cmake --build "$BUILD" --target SDL3-static --parallel "${JOBS:-$(nproc)}"
