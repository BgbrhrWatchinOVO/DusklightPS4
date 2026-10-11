#!/usr/bin/env bash
# Fetch the measurement build's raw profiles from the console and merge them into
# pgo/dusklight.profdata for tools/build-game.sh PGO=use. The build writes two files in turn
# (ps4/pgo.cpp); the newer one that llvm-profdata reads is used, as the counters only grow.
#   pgo-merge.sh <ps4 ip>
set -euo pipefail
source "$(dirname "$0")/env.sh"
HOST="${1:?usage: pgo-merge.sh <ps4 ip>}"
OUT="$PS4_PORT_ROOT/pgo"
RAW="$OUT/raw-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RAW"

best=""
best_counts=0
for name in dusklight-a.profraw dusklight-b.profraw; do
    curl -s --max-time 600 --ignore-content-length "ftp://$HOST:2121/data/dusklight-ps4/pgo/$name" -o "$RAW/$name" || continue
    [ -s "$RAW/$name" ] || continue
    # The total of all counters: the newer, complete dump has the larger one.
    if llvm-profdata-21 show "$RAW/$name" > /dev/null 2>&1; then
        total="$(llvm-profdata-21 show "$RAW/$name" 2>/dev/null | awk '/^Total count:/ {print $3; exit}')"
        echo "$name: $(du -h "$RAW/$name" | cut -f1), counter total $total"
        if [ "$total" -gt "$best_counts" ]; then
            best="$RAW/$name"
            best_counts="$total"
        fi
    else
        echo "$name: unreadable (written while the title closed?)"
    fi
done
[ -n "$best" ] || { echo "no usable profile" >&2; exit 1; }
llvm-profdata-21 merge -o "$OUT/dusklight.profdata" "$best"
llvm-profdata-21 show "$OUT/dusklight.profdata" | head -8
echo "merged $best -> $OUT/dusklight.profdata"
