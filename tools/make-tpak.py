#!/usr/bin/env python3
"""Pack a texture replacement folder into one file for the PS4 build (ps4/tpak.cpp).

The console's hard drive seeks for every one of a pack's ~1,800 files, so replacements loaded
one by one came in at ~4 MB/s. In one file, in the order Aurora registers the folder (path
components compared without case, then exactly; a shorter path first), the textures of an area
sit next to each other and the console reads them in large blocks.

Layout, little-endian:
    header (64 bytes): magic b"DTPAK\\0\\1\\0", u32 count, u32 reserved, u64 index offset,
                       u64 index size, then zeros
    files, each starting on a 4 KiB boundary
    index: per file u64 offset, u64 size, u16 path length, the path ('/'-separated, relative)

    make-tpak.py <texture folder> <out.tpak>
"""
import argparse
import struct
from pathlib import Path

MAGIC = b'DTPAK\x00\x01\x00'
ALIGN = 4096
EXTENSIONS = {'.dds', '.png'}


def sort_key(relative):
    return [(part.lower(), part) for part in relative.parts]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('folder', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()

    files = sorted((p.relative_to(args.folder) for p in args.folder.rglob('*')
                    if p.is_file() and p.suffix.lower() in EXTENSIONS), key=sort_key)
    entries = []
    with open(args.out, 'wb') as out:
        out.write(bytes(64))
        for relative in files:
            offset = out.tell()
            if offset % ALIGN:
                out.write(bytes(ALIGN - offset % ALIGN))
                offset = out.tell()
            data = (args.folder / relative).read_bytes()
            out.write(data)
            entries.append((offset, len(data), relative.as_posix().encode('utf-8')))
        index_offset = out.tell()
        for offset, size, path in entries:
            out.write(struct.pack('<QQH', offset, size, len(path)) + path)
        index_size = out.tell() - index_offset
        out.seek(0)
        out.write(MAGIC + struct.pack('<IIQQ', len(entries), 0, index_offset, index_size))
    total = sum(size for _, size, _ in entries)
    print(f'{args.out}: {len(entries)} files, {total / 2**20:.1f} MiB of textures, '
          f'{args.out.stat().st_size / 2**20:.1f} MiB packed')


if __name__ == '__main__':
    main()
