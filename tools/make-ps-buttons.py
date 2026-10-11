#!/usr/bin/env python3
"""Henriko's PlayStation button textures for the Nintendo-style layout of the PS4 build.

The PS4 build maps Circle to A (confirm) and Cross to B (back), where Nintendo puts them
(src/dusklight/ps4/input.cpp). Henriko's "Xbox + PS UI Buttons Addon" draws A as Cross and B
as Circle ("Playstation Layout"), so this swaps the A and B symbols: the round icons trade
places, the plain symbols are refitted to each other's glyph box, and the one texture the addon
leaves as "B" becomes a Cross. Square (X) and Triangle (Y) stay as they are.

The HUD tints the A and B button bases green and red (GameCube colours) and draws the symbols in
white, so the bases are made dark (the tint barely shows on them) and the symbols take the
PlayStation colours, in the saturation of Henriko's own Square and Triangle icons.

    make-ps-buttons.py <addon.zip> <pack>/UI/Menus/Buttons

The Buttons folder's contents are replaced by PNGs, as ps5/tools/prepare-textures.py writes
the prompts.
"""
import argparse
import io
from pathlib import Path, PurePosixPath
import zipfile

from PIL import Image, ImageDraw

LAYOUT = 'Playstation Layout/Buttons/'
A_ICON, B_ICON = 'tex1_24x24_8f5b85ae836ad2aa_2', 'tex1_24x24_d693a49f64dd0597_2'
A_TEXT, B_TEXT = 'tex1_32x46_683dc853245a0f36_0', 'tex1_24x40_b191153a917b3b50_0'
B_DARK = 'tex1_32x32_1bb7a1cd57fff2ba_2'  # a black round "B" the addon does not convert
A_BASE, B_BASE = 'tex1_40x40_0bcb924b474aa8a7_2', 'tex1_64x64_6c871a1cb3258c85_0'
X_TEXT, Y_TEXT = 'tex1_32x45_3b03f19ac102dd38_0', 'tex1_32x40_a57e14b2809290fc_0'
# PlayStation symbol colours, matched to Henriko's pink (200, 96, 152) and teal (0, 136, 128).
CIRCLE_RED, CROSS_BLUE = (216, 72, 84), (88, 136, 216)
SQUARE_PINK, TRIANGLE_TEAL = (200, 96, 152), (0, 136, 128)


def load_layout(archive):
    images = {}
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            name = entry.filename
            path = PurePosixPath(name)
            if ('/' + name).find('/' + LAYOUT) < 0 or not path.name.startswith('tex1_'):
                continue
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'Unsafe archive path: {name}')
            with Image.open(io.BytesIO(z.read(entry))) as image:
                images[path.stem] = image.convert('RGBA')
    for required in (A_ICON, B_ICON, A_TEXT, B_TEXT, B_DARK, A_BASE, B_BASE, X_TEXT, Y_TEXT):
        if required not in images:
            raise ValueError(f'{required} missing: is this the PC Xbox + PS UI Buttons Addon?')
    return images


def refit(glyph_source, target):
    """The glyph of glyph_source, scaled into the box the glyph of target occupies."""
    glyph = glyph_source.crop(glyph_source.getchannel('A').getbbox())
    box = target.getchannel('A').getbbox()
    width, height = box[2] - box[0], box[3] - box[1]
    scale = min(width / glyph.width, height / glyph.height)
    glyph = glyph.resize((max(1, round(glyph.width * scale)), max(1, round(glyph.height * scale))),
                         Image.LANCZOS)
    out = Image.new('RGBA', target.size, (0, 0, 0, 0))
    out.alpha_composite(glyph, (box[0] + (width - glyph.width) // 2, box[1] + (height - glyph.height) // 2))
    return out


def dark_cross(dark_b):
    """The black round button with its white "B" replaced by a white Cross."""
    size = dark_b.width
    out = dark_b.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            # The letter: bright pixels well inside the ring.
            if (x - size / 2) ** 2 + (y - size / 2) ** 2 < (size * 0.42) ** 2 and r + g + b > 120:
                pixels[x, y] = (0, 0, 0, a)
    scale = 4
    layer = Image.new('RGBA', (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    c, arm, width = size * scale / 2, size * scale * 0.2, round(size * scale * 0.085)
    for (x0, y0, x1, y1) in ((c - arm, c - arm, c + arm, c + arm), (c - arm, c + arm, c + arm, c - arm)):
        draw.line((x0, y0, x1, y1), fill=(255, 255, 255, 255), width=width)
        for x, y in ((x0, y0), (x1, y1)):
            draw.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=(255, 255, 255, 255))
    out.alpha_composite(layer.resize((size, size), Image.LANCZOS))
    return out


def dark_base(base):
    """The button base's shape, filled with a dark gradient and a faint rim."""
    alpha = base.getchannel('A')
    w, h = base.size
    out = Image.new('RGBA', base.size)
    pixels, mask = out.load(), alpha.load()
    cx, cy, radius = w / 2, h / 2, min(w, h) / 2
    for y in range(h):
        for x in range(w):
            a = mask[x, y]
            if not a:
                pixels[x, y] = (0, 0, 0, 0)
                continue
            d = min(1.0, ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / radius)
            v = round(56 - 34 * d)
            if d > 0.9:
                v = round(v + (d - 0.9) / 0.1 * 50)  # rim
            pixels[x, y] = (v, v, v + 4, a)
    return out


def colorize(glyph, color):
    """Bright glyph pixels take the colour; the darker drop shadow stays as it is."""
    out = glyph.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            t = min(1.0, max(0.0, ((r + g + b) / 3 - 120) / 100))
            pixels[x, y] = (round(r + (color[0] - r) * t), round(g + (color[1] - g) * t),
                            round(b + (color[2] - b) * t), a)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('addon', type=Path)
    parser.add_argument('buttons', type=Path, help='the texture pack\'s UI/Menus/Buttons folder')
    args = parser.parse_args()
    images = load_layout(args.addon)

    images[A_ICON], images[B_ICON] = images[B_ICON], images[A_ICON]
    a_text, b_text = images[A_TEXT], images[B_TEXT]
    images[A_TEXT], images[B_TEXT] = refit(b_text, a_text), refit(a_text, b_text)
    images[B_DARK] = dark_cross(images[B_DARK])
    images[A_BASE], images[B_BASE] = dark_base(images[A_BASE]), dark_base(images[B_BASE])
    images[A_TEXT] = colorize(images[A_TEXT], CIRCLE_RED)
    images[B_TEXT] = colorize(images[B_TEXT], CROSS_BLUE)
    images[X_TEXT] = colorize(images[X_TEXT], SQUARE_PINK)
    images[Y_TEXT] = colorize(images[Y_TEXT], TRIANGLE_TEAL)

    args.buttons.mkdir(parents=True, exist_ok=True)
    for old in args.buttons.iterdir():
        if old.name.startswith('tex1_'):
            old.unlink()
    for stem, image in sorted(images.items()):
        image.save(args.buttons / f'{stem}.png')
    print(f'{len(images)} button textures (Nintendo-style A/B, PlayStation colours) in {args.buttons}')


if __name__ == '__main__':
    main()
