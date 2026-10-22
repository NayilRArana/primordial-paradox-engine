"""make_palette_sheet.py: render output\\art_bible_palette_sheet.png, the 3x palette review sheet.

Why it exists: the workers on this project cannot see images, so a colour table has to be reviewable by
a human or a vision model, not by the worker. This draws every one of the 64 PPU entries at 3x (each
swatch is an 8 x 8 pixel block shown as 24 x 24), labelled with its index, with the 10 entries that
decode to black marked so a reviewer can see at once that they are duplicates and that $0D is the one
to avoid.

Data: data\\nes_palette.json, built and cited by tools\\art\\nes_palette_build.py.

Run: python tools\\art\\make_palette_sheet.py [repo root]
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SCALE = 3
TILE = 8 * SCALE            # 24 px, an 8 x 8 NES tile at 3x
CELL_W = 48
CELL_H = 46
MARGIN = 16
COLUMNS = 16
ROWS = 4
WIDTH = 800
HEADER = 48
FOOTER = 66
MARK = (255, 0, 255)


def load_entries(root: str) -> list:
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)["entries"]


def main(argv: list) -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = [item for item in argv[1:] if not item.startswith("--")]
    if args:
        root = os.path.abspath(args[0])
    entries = load_entries(root)
    if len(entries) != 64:
        print("FAIL data\\nes_palette.json does not hold 64 entries")
        return 1

    height = HEADER + ROWS * CELL_H + FOOTER
    image = Image.new("RGB", (WIDTH, height), (18, 18, 22))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.text((MARGIN, 10), "NES 2C02 master palette, 64 entries at 3x, $00 to $3F", fill=(240, 240, 240), font=font)
    draw.text((MARGIN, 26), "magenta box: flagged (forbidden $0D or a black duplicate). Row ends at $xF.",
              fill=(190, 190, 200), font=font)

    for entry in entries:
        index = entry["index"]
        column = index % COLUMNS
        row = index // COLUMNS
        x = MARGIN + column * CELL_W
        y = HEADER + row * CELL_H
        hex_value = entry["hex"].lstrip("#")
        colour = tuple(int(hex_value[position:position + 2], 16) for position in (0, 2, 4))
        draw.rectangle([x + 6, y + 2, x + 6 + TILE - 1, y + 2 + TILE - 1], fill=colour,
                       outline=(70, 70, 80))
        if "flag" in entry:
            draw.rectangle([x + 4, y, x + 8 + TILE, y + TILE + 3], outline=MARK)
        draw.text((x + 4, y + TILE + 6), entry["code"], fill=(240, 240, 240), font=font)
        if not entry.get("usable", True):
            draw.text((x + 32, y + TILE + 6), "x", fill=MARK, font=font)

    legend_y = HEADER + ROWS * CELL_H + 6
    draw.text((MARGIN, legend_y),
              "Usable entries 55 of 64, distinct colours 55, flagged 10: $0D forbidden, the other nine black duplicates.",
              fill=(190, 190, 200), font=font)
    draw.text((MARGIN, legend_y + 14),
              "Black for art is $0F (canonical). White for art is $30. Backdrop is whatever $3F00 holds.",
              fill=(190, 190, 200), font=font)
    draw.text((MARGIN, legend_y + 28),
              "Source: NESdev wiki PPU palettes (2026-10-21); hex from data\\nes_palette.json.",
              fill=(190, 190, 200), font=font)

    out_dir = os.path.join(root, "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "art_bible_palette_sheet.png")
    image.save(path)
    print("wrote %s: %dx%d at %dx" % (path, image.size[0], image.size[1], SCALE))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
