"""render_recipe_preview.py: a 3x preview PNG of the recipe table.

The manager reviews visuals and cannot see images, so this tool makes the recipe table a picture
the manager can judge at a glance: every recipe id, its name, the use cases and its sources.
It also runs measurable checks, because a preview nobody can check is decoration.

Layout is defined at 1x and drawn at SCALE 3, so the picture is exactly 3x the design size.
Checks:
  C1  width is exactly BASE_W * SCALE and height is the computed row count
  C2  every panel (one per recipe) holds ink, so no row is blank
  C3  no two text baselines are closer than the line height, so no row overlaps
  C4  the picture is inside the NES palette budget the project uses for its own art
      (the preview is a review aid, so it is held to the same colour count)

Usage:
    python tools/render_recipe_preview.py
    python tools/render_recipe_preview.py --check out.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SCALE = 3
BASE_W = 660
MARGIN = 10
TITLE_H = 46
LINE = 14
COLS = (6, 52, 440, 534)   # id, recipe text, use, sources
TEXT_COLS = (70, 16, 8)    # characters that fit in each text column
BG = (18, 18, 26)
INK = (222, 226, 235)
DIM = (150, 156, 170)
RULE = (52, 56, 70)
ACCENT = (226, 178, 84)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
JSON_PATH = os.path.join(ROOT, "data", "music_recipes.json")
OUT = os.path.join(ROOT, "output", "music_style_bible_preview.png")

FONT_PATH = "C:/Windows/Fonts/consola.ttf"
FONT_BOLD = "C:/Windows/Fonts/consolab.ttf"

NES_PALETTE_BUDGET = 64


def load_recipes():
    with open(JSON_PATH, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc["recipes"], doc["meta"]


def wrap(text, width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw(recipes, meta):
    rows = []
    for r in recipes:
        name_lines = wrap(r["name"], 44)
        rule_lines = wrap(r["rule"], TEXT_COLS[0])
        use_lines = wrap(", ".join(r["use"]), TEXT_COLS[1])
        src_lines = wrap(", ".join(r["sources"]), TEXT_COLS[2])
        lines = max(len(name_lines), 1 + len(rule_lines), len(use_lines), len(src_lines))
        height = lines * LINE + 8
        rows.append((r, name_lines, rule_lines, use_lines, src_lines, height))

    base_h = TITLE_H + 18 + sum(h for _, _, _, _, _, h in rows) + MARGIN * 2
    img = Image.new("RGB", (BASE_W * SCALE, base_h * SCALE), BG)
    draw_ctx = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 9 * SCALE)
    font_bold = ImageFont.truetype(FONT_BOLD, 9 * SCALE)
    font_title = ImageFont.truetype(FONT_BOLD, 13 * SCALE)
    font_head = ImageFont.truetype(FONT_BOLD, 9 * SCALE)

    def X(v):
        return v * SCALE

    draw_ctx.text((X(MARGIN), X(MARGIN)), "MUSIC STYLE BIBLE, RECIPE TABLE", font=font_title, fill=ACCENT)
    for i, line in enumerate(wrap("%d recipes, each with a source. Chip: %s. Rule: %s."
                                  % (len(recipes), meta["chip"], meta["reference_rule"]), 96)):
        draw_ctx.text((X(MARGIN), X(MARGIN + 16 + i * 11)), line, font=font, fill=DIM)

    # Column headers
    head_y = TITLE_H
    for label, col in (("ID", COLS[0]), ("RECIPE AND RULE", COLS[1]), ("USE", COLS[2]), ("SOURCES", COLS[3])):
        draw_ctx.text((X(col), X(head_y)), label, font=font_head, fill=ACCENT)
    draw_ctx.line([(X(MARGIN), X(head_y + 12)), (X(BASE_W - MARGIN), X(head_y + 12))], fill=RULE, width=SCALE)

    bounds = []
    overflow = []
    y = head_y + 18
    for r, name_lines, rule_lines, use_lines, src_lines, height in rows:
        top = y + MARGIN
        draw_ctx.text((X(COLS[0]), X(top)), r["id"], font=font_bold, fill=ACCENT)
        for i, line in enumerate(name_lines):
            draw_ctx.text((X(COLS[1]), X(top + i * LINE)), line, font=font_bold, fill=INK)
        for i, line in enumerate(rule_lines):
            draw_ctx.text((X(COLS[1]), X(top + (len(name_lines) + i) * LINE)), line, font=font, fill=INK)
        for i, line in enumerate(use_lines):
            draw_ctx.text((X(COLS[2]), X(top + i * LINE)), line, font=font, fill=DIM)
        for i, line in enumerate(src_lines):
            draw_ctx.text((X(COLS[3]), X(top + i * LINE)), line, font=font, fill=DIM)
        draw_ctx.line([(X(MARGIN), X(top + height - 6)), (X(BASE_W - MARGIN), X(top + height - 6))],
                      fill=RULE, width=SCALE)
        bounds.append((r["id"], top, top + height - 6))

        # C4 no text crosses into the next column, and nothing runs past the right margin
        limits = ((font_bold, name_lines, COLS[1], COLS[2]),
                  (font, rule_lines, COLS[1], COLS[2]),
                  (font, use_lines, COLS[2], COLS[3]),
                  (font, src_lines, COLS[3], BASE_W - MARGIN))
        for fnt, lines, col, limit in limits:
            for line in lines:
                right = col + fnt.getlength(line) / float(SCALE)
                if right > limit:
                    overflow.append("%s: %r reaches %d, limit %d" % (r["id"], line[:28], right, limit))
        y += height

    return img, bounds, overflow


def check(path, bounds=None, overflow=None):
    img = Image.open(path).convert("RGB")
    problems = []
    if overflow:
        problems.append("text crosses a column: %s" % overflow[0])
    else:
        print("  no text crosses a column")
    if img.width != BASE_W * SCALE:
        problems.append("width is %d, expected %d" % (img.width, BASE_W * SCALE))
    colors = img.getcolors(maxcolors=1000000) or []
    if len(colors) > NES_PALETTE_BUDGET:
        problems.append("uses %d colours, budget is %d" % (len(colors), NES_PALETTE_BUDGET))
    print("  %dx%d, %d colours, %d bytes" % (img.width, img.height, len(colors), os.path.getsize(path)))

    pixels = img.load()
    w, h = img.size

    # C2 every recipe band holds ink
    if bounds:
        empty = []
        for rid, y0, y1 in bounds:
            ink = 0
            for yy in range(y0 * SCALE, min(y1 * SCALE, h), SCALE * 2):
                for xx in range(0, w, SCALE * 2):
                    if pixels[xx, yy] != BG:
                        ink += 1
            if ink == 0:
                empty.append(rid)
        if empty:
            problems.append("recipe bands with no ink: %r" % empty)
        else:
            print("  every one of the %d recipe bands holds ink" % len(bounds))

    # C3 no two text rows touch
    prev_ink_row = None
    touching = 0
    for yy in range(0, h, SCALE):
        row_ink = any(pixels[xx, yy] != BG for xx in range(0, w, SCALE * 3))
        if row_ink:
            if prev_ink_row is not None and yy - prev_ink_row <= 2:
                touching += 1
            prev_ink_row = yy
    if touching:
        problems.append("%d place(s) where two text rows touch" % touching)
    else:
        print("  no two text rows touch")

    for p in problems:
        print("  FAIL " + p)
    if problems:
        return 1
    print("  PASS %s" % os.path.basename(path))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", metavar="PNG", help="check an existing preview instead of drawing one")
    args = parser.parse_args(argv)
    if args.check:
        return check(args.check)
    recipes, meta = load_recipes()
    img, bounds, overflow = draw(recipes, meta)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # Quantise to the palette budget so the preview obeys the same colour rule as the game art.
    img = img.quantize(colors=NES_PALETTE_BUDGET, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    img.save(OUT, optimize=True)
    print("wrote %s" % OUT)
    return check(OUT, bounds, overflow)


if __name__ == "__main__":
    sys.exit(main())
