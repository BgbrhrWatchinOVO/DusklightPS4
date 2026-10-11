#!/usr/bin/env bash
# Fetch the newest crash report from the console and symbolize it. DolphinPS4's crash logger
# (port/ps4_crashlog.cpp, linked into the game) appends each fatal signal with its registers and
# the code addresses found on the stack to /data/DolphinPS4/crash.log, as ELF addresses.
#   ps4-crash.sh <ps4 ip> [elf]   (elf: the build that crashed; default build/game/dusklight)
set -euo pipefail
source "$(dirname "$0")/env.sh"
HOST="${1:?usage: ps4-crash.sh <ps4 ip> [elf]}"
ELF="${2:-$PS4_PORT_ROOT/build/game/dusklight}"
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT
curl -s --max-time 60 --ignore-content-length "ftp://$HOST:2121/data/DolphinPS4/crash.log" -o "$LOG"
[ -s "$LOG" ] || { echo "no crash.log on the console"; exit 0; }
# The last report only.
last="$(awk '/^=== signal/ {start = NR} END {print start}' "$LOG")"
tail -n +"$last" "$LOG" | sed -n '1,4p'
addresses="$(tail -n +"$last" "$LOG" | grep -oE 'elf 0x[0-9a-f]+|\] 0x[0-9a-f]+' | grep -oE '0x[0-9a-f]+')"
echo "--- symbolized ($ELF):"
for address in $addresses; do
    printf '%s  ' "$address"
    llvm-symbolizer-21 --obj="$ELF" --inlining=false "$address" | head -2 | paste -sd' ' | \
        sed "s|$PS4_PORT_ROOT/src/||g"
done
