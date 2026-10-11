# Settings shared by the PS4 build scripts. Source this file.
#
# DolphinPS4's toolchain scripts (refs/DolphinPS4) are used as they are; they keep their sources
# in $PSB/src, the libc++ sysroot in $PSB/sysroot and build trees in $PSB/build, so PSB is this
# project's root and those land next to src/mesa and src/libdrm.
PS4_PORT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PS4_PORT_ROOT
export PSB="$PS4_PORT_ROOT"
export PS4_BUILD_ROOT="$PSB"
export PS4_SYSROOT="$PSB/sysroot"
export OPENORBIS="$PS4_PORT_ROOT/sdk/opt/pacbrew/ps4/openorbis"
export OO_PS4_TOOLCHAIN="$OPENORBIS"
export DOLPHINPS4="$PS4_PORT_ROOT/refs/DolphinPS4"
export LLVM_VER=21.1.6
