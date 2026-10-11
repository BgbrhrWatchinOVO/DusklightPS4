#!/usr/bin/env python3
"""Where the main, render and FIFO threads spend their time, from the PS4 profiler's sampler
(ps4/prof/ps4_profiler.cpp writes /data/dusklight-ps4/samples.bin: ~1000 samples a second per
thread, each the code address the thread was at and the word on top of its stack).

    ps4-samples.py <samples.bin> <elf> [--from S] [--to S] [--seconds LIST] [--top N]

--seconds takes a file of log lines; the seconds of its "slow second"/"hitch" lines (the second
before each line's timestamp) are the only ones counted - where the frame rate dropped.
Addresses outside the eboot (system libraries: libkernel waits, libc) are charged to the eboot
function whose return address is on top of the stack, when there is one."""
import argparse
import collections
import json
import re
import struct
import subprocess
import sys

THREADS = ["main", "render", "fifo"]


def load(path):
    data = open(path, "rb").read()
    if data[:4] != b"DSMP":
        sys.exit(f"{path}: not a samples file")
    record = struct.Struct("<IIQQ")
    usable = (len(data) - 8) // record.size * record.size
    return [record.unpack_from(data, 8 + i) for i in range(0, usable, record.size)]


def text_ranges(elf):
    out = subprocess.run(["llvm-readelf-21", "-SW", elf], capture_output=True, text=True, check=True).stdout
    ranges = []
    for line in out.splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)\s+\S+\s+(\S*X\S*)", line)
        if m:
            start, size = int(m.group(2), 16), int(m.group(3), 16)
            ranges.append((start, start + size))
    return ranges


def symbolize(elf, addresses):
    names = {}
    addresses = sorted(addresses)
    for i in range(0, len(addresses), 20000):
        chunk = addresses[i:i + 20000]
        out = subprocess.run(["llvm-symbolizer-21", f"--obj={elf}", "--output-style=JSON", "--demangle"],
                             input="\n".join(hex(a) for a in chunk), capture_output=True, text=True).stdout
        for line, address in zip(out.splitlines(), chunk):
            frames = json.loads(line).get("Symbol", [])
            if not frames:
                names[address] = ("?", "?")
                continue

            def short(frame):
                name = frame.get("FunctionName") or "?"
                name = re.sub(r"\(.*\)( const)?$", "", name)  # drop parameter lists
                return name[:110]
            # Innermost (where inlined code came from) and outermost (the real function).
            names[address] = (short(frames[0]), short(frames[-1]))
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("samples")
    parser.add_argument("elf")
    parser.add_argument("--from", dest="start", type=float, default=0)
    parser.add_argument("--to", dest="end", type=float, default=1e9)
    parser.add_argument("--seconds", help="log lines whose slow seconds to count")
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    samples = load(args.samples)
    wanted = None
    if args.seconds:
        wanted = set()
        for line in open(args.seconds, errors="replace"):
            m = re.search(r"\[prof\]\s+([\d.]+) (slow second|hitch)", line)
            if m:
                wanted.add(int(float(m.group(1))) - 1)
    ranges = text_ranges(args.elf)

    def in_eboot(address):
        return any(a <= address < b for a, b in ranges)

    picked = []
    for ms, thread, rip, stack in samples:
        second = ms / 1000.0
        if second < args.start or second >= args.end:
            continue
        if wanted is not None and int(second) not in wanted:
            continue
        if in_eboot(rip):
            picked.append((thread, rip, False))
        elif in_eboot(stack):
            picked.append((thread, stack, True))  # in a system library, called from here
        else:
            picked.append((thread, None, True))
    names = symbolize(args.elf, {address for _, address, _ in picked if address is not None})

    span = (max(s[0] for s in samples) - min(s[0] for s in samples)) / 1000.0 if samples else 0
    print(f"{len(samples)} samples over {span:.0f} s, {len(picked)} counted")
    for index, thread in enumerate(THREADS):
        rows = [(address, system) for t, address, system in picked if t == index]
        if not rows:
            continue
        inner = collections.Counter()
        outer = collections.Counter()
        for address, system in rows:
            if address is None:
                inner["(system library, caller unknown)"] += 1
                outer["(system library, caller unknown)"] += 1
                continue
            i, o = names[address]
            tag = " [in a system call from here]" if system else ""
            inner[i + tag] += 1
            outer[o + tag] += 1
        total = len(rows)
        print(f"\n=== {thread}: {total} samples")
        print("  -- by function (inlined code charged to where it came from):")
        for name, count in inner.most_common(args.top):
            print(f"  {100.0 * count / total:5.1f}%  {name}")
        print("  -- by real (outermost) function:")
        for name, count in outer.most_common(args.top):
            print(f"  {100.0 * count / total:5.1f}%  {name}")


if __name__ == "__main__":
    main()
