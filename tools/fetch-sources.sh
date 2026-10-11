#!/usr/bin/env bash
# Check out every source tree the PS4 build uses into src/.
#   - Dusklight, aurora, Dawn, SDL3 and Abseil come from the PS5 port's repository (refs/dusklight-ps5),
#     whose deps/* tags pin the forks it was tested with; the PS4 port starts from those.
#   - libdrm headers (Mesa's amdgpu winsys includes them; the PS4 has no DRM).
#   - LLVM 21 runtimes source, for DolphinPS4's libc++ 21 sysroot.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PS5="$ROOT/refs/dusklight-ps5"
SRC="$ROOT/src"
DL="$ROOT/downloads"
mkdir -p "$SRC" "$DL"

worktree() {  # worktree <dir> <tag>
    [ -e "$SRC/$1/.git" ] && return
    git -C "$PS5" worktree add --detach "$SRC/$1" "$2"
}

if [ ! -e "$SRC/dusklight/.git" ]; then
    git clone -q "$PS5" "$SRC/dusklight"
    git -C "$SRC/dusklight" checkout -q ps5-v0.1.0
fi
git -C "$SRC/dusklight" config submodule.extern/aurora.url "$PS5"
git -C "$SRC/dusklight" -c protocol.file.allow=always submodule update --init \
    extern/aurora extern/borealis mods/randomizer mods/cosmetics
git -C "$SRC/dusklight/extern/aurora" submodule update --init --recursive

worktree dawn deps/dawn-ps5
worktree sdl3 deps/sdl3-ps5
worktree abseil deps/abseil-20240722-ps5

# Dawn's third-party trees (DEPS), minus the Chromium-only ones.
if [ ! -f "$SRC/dawn/third_party/.fetched" ]; then
    (cd "$SRC/dawn" && python3 tools/fetch_dawn_dependencies.py --use-test-deps=false 2>&1 | tail -5) || \
    (cd "$SRC/dawn" && python3 tools/fetch_dawn_dependencies.py 2>&1 | tail -5)
    touch "$SRC/dawn/third_party/.fetched"
fi

[ -d "$SRC/libdrm/.git" ] || git clone -q --depth 1 --branch libdrm-2.4.125 \
    https://gitlab.freedesktop.org/mesa/drm.git "$SRC/libdrm"

LLVM_VER=21.1.6
LLVM_TAR="llvm-project-$LLVM_VER.src.tar.xz"
if [ ! -f "$DL/$LLVM_TAR" ]; then
    curl -fsSL --max-time 3600 -o "$DL/$LLVM_TAR.part" \
        "https://github.com/llvm/llvm-project/releases/download/llvmorg-$LLVM_VER/$LLVM_TAR"
    mv "$DL/$LLVM_TAR.part" "$DL/$LLVM_TAR"
fi
want=$(gh api "repos/llvm/llvm-project/releases/tags/llvmorg-$LLVM_VER" \
    --jq ".assets[] | select(.name == \"$LLVM_TAR\") | .digest" | sed 's/^sha256://')
echo "$want  $DL/$LLVM_TAR" | sha256sum -c --quiet
echo "sources ready"
