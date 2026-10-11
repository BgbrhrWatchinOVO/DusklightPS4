#!/usr/bin/env bash
# Build compiler-rt's profile runtime (clang -fprofile-generate) for the PS4 as a static library:
# build/profile-rt/libclang_rt.profile-ps4.a. The compiler-rt release must match the host clang
# (21.1.8), so the raw profiles it writes are the format llvm-profdata reads.
set -euo pipefail
source "$(dirname "$0")/env.sh"
SRC="$PS4_PORT_ROOT/src/compiler-rt/lib/profile"
OUT="$PS4_PORT_ROOT/build/profile-rt"
[ -d "$SRC" ] || { echo "no $SRC: unpack compiler-rt-21.1.8.src.tar.xz into src/compiler-rt" >&2; exit 1; }

# Without __ORBIS__: compiler-rt's PS4 branches are for Sony's SDK (no getenv, no hostname);
# OpenOrbis has both.
FLAGS=(-target x86_64-pc-freebsd12-elf -D_GNU_SOURCE -D__PS4__ -D__OPENORBIS__ -DPS4
       -D__BSD_VISIBLE -D_BSD_SOURCE -fPIC -funwind-tables -O2 -march=btver2
       -isysroot "$OPENORBIS" -isystem "$PS4_SYSROOT/libc-overlay" -isystem "$OPENORBIS/include"
       -I"$OPENORBIS/usr/include" -I"$SRC/../../include"
       -DCOMPILER_RT_HAS_ATOMICS=1 -DCOMPILER_RT_HAS_UNAME=1
       -fno-profile-instr-generate -fno-coverage-mapping)
SOURCES=(InstrProfiling.c InstrProfilingBuffer.c InstrProfilingFile.c InstrProfilingInternal.c
         InstrProfilingMerge.c InstrProfilingMergeFile.c InstrProfilingNameVar.c
         InstrProfilingPlatformLinux.c InstrProfilingUtil.c InstrProfilingValue.c
         InstrProfilingVersionVar.c InstrProfilingWriter.c)

rm -rf "$OUT"
mkdir -p "$OUT/obj" "$OUT/overlay/sys"
# FreeBSD's procctl (parent-death signals around fork) does not exist on the console.
cat > "$OUT/overlay/sys/procctl.h" <<'HEADER'
#pragma once
#include <sys/types.h>
#define P_PID 0
#define PROC_PDEATHSIG_CTL 11
#define PROC_PDEATHSIG_STATUS 12
static inline int procctl(int idtype, pid_t id, int cmd, void *data) {
    (void)idtype; (void)id; (void)cmd; (void)data;
    return -1;
}
HEADER
FLAGS+=(-isystem "$OUT/overlay")
# No binary ids: they are read from the ELF header through __ehdr_start, and the console's image
# has no header in memory (code starts at address 0), so the walk ran through code and hung.
mkdir -p "$OUT/src"
sed 's/^#ifdef NT_GNU_BUILD_ID$/#if 0 \/\* PS4: no ELF header in memory \*\//' "$SRC/InstrProfilingPlatformLinux.c" \
    > "$OUT/src/InstrProfilingPlatformLinux.c"
grep -q '^#if 0 /\* PS4' "$OUT/src/InstrProfilingPlatformLinux.c" || { echo "binary id patch did not apply" >&2; exit 1; }
for source in "${SOURCES[@]}"; do
    input="$SRC/$source"
    [ -f "$OUT/src/$source" ] && input="$OUT/src/$source"
    clang-21 "${FLAGS[@]}" -I"$SRC" -std=gnu11 -c "$input" -o "$OUT/obj/${source%.c}.o"
done
clang++-21 "${FLAGS[@]}" -nostdinc++ -isystem "$PS4_SYSROOT/include/c++/v1" -std=c++17 -fno-exceptions -fno-rtti \
    -c "$SRC/InstrProfilingRuntime.cpp" -o "$OUT/obj/InstrProfilingRuntime.o"
llvm-ar-21 rcs "$OUT/libclang_rt.profile-ps4.a" "$OUT"/obj/*.o
echo "profile runtime: $OUT/libclang_rt.profile-ps4.a"
