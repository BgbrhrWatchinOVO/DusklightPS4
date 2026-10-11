#!/usr/bin/env bash
# Build Mesa's RADV for the PS4 with DolphinPS4's scripts/build-mesa.sh, optionally with PGO:
#   PGO=generate  instrumented, in build/mesa-pgogen (tools/build-game.sh PGO=generate links it)
#   PGO=use       optimised with PGO_PROFILE, in build/mesa-pgo (tools/build-game.sh PGO=use)
#   (unset)       build/mesa
# The two PGO directories are at the same depth, so the source paths meson passes (relative to
# the build directory) and with them the profile's names for static functions match.
#   build-mesa.sh [setup]
#   FLAVOR=final  the release winsys without diagnostics (PS4_WINSYS_DIAG=0) in build/mesa-final;
#                 with PGO=use (same depth as build/mesa-pgo, so the profile's names match)
set -euo pipefail
source "$(dirname "$0")/env.sh"
PGO="${PGO:-}"
FLAVOR="${FLAVOR:-dev}"
PGO_PROFILE="${PGO_PROFILE:-$PS4_PORT_ROOT/pgo/dusklight.profdata}"
case "$PGO" in
    "") ;;
    generate)
        export MESA_BUILD="$PS4_PORT_ROOT/build/mesa-pgogen"
        # -fprofile-generate's instrumentation without the driver's part: on linking, the driver
        # adds a profile runtime of its own, which doesn't exist for this target.
        export MESA_EXTRA_FLAGS=", '-Xclang', '-fprofile-instrument=llvm'"
        # meson's compiler checks link test programs: they need the profile runtime.
        export MESA_EXTRA_LINK=", '$PS4_PORT_ROOT/build/profile-rt/libclang_rt.profile-ps4.a'" ;;
    use)
        [ -f "$PGO_PROFILE" ] || { echo "no $PGO_PROFILE" >&2; exit 1; }
        export MESA_BUILD="$PS4_PORT_ROOT/build/mesa-pgo"
        export MESA_EXTRA_FLAGS=", '-fprofile-use=$PGO_PROFILE', '-Wno-profile-instr-unprofiled', '-Wno-profile-instr-out-of-date', '-Wno-backend-plugin'" ;;
    *) echo "PGO must be generate or use" >&2; exit 1 ;;
esac
if [ "$FLAVOR" = final ]; then
    export MESA_BUILD="$PS4_PORT_ROOT/build/mesa-final"
    export MESA_EXTRA_FLAGS="${MESA_EXTRA_FLAGS:-}, '-DPS4_WINSYS_DIAG=0'"
fi
exec bash "$DOLPHINPS4/scripts/build-mesa.sh" "$@"
