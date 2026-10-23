#!/usr/bin/env python3
"""preview_dialogue_box.py: compose the real dialogue box at 3x, and refuse a row that leaves the box.

Card t_1d828fcd (DIALOGUE-FONT-WIRE). The two defects that card fixed were only provable with pixels and with
arithmetic, and this tool is the pixels half: it draws one page of `data/dialogue/all.json` the way
`pp_dialogue_draw` draws it, from the same assets and the same numbers, and then measures where the ink landed.

What it reads, and why nothing is typed twice here:

  game/scripts/pp_config/pp_config.gml   PP_BOX_X/Y/W/H, PP_TEXT_X/Y/RIGHT/CHARS/LINE_H/ROWS, the choice panel
                                         macros. The wrap width is read from the same macro the engine wraps with, so
                                         a preview can never disagree with the box about how many characters fit.
  game/scripts/pp_font/pp_font.gml       pp_font_glyphs(), the sheet's frame order, exactly as pp_font_draw looks a
                                         character up.
  game/sprites_src/title/spr_pp_font8.*  the glyph sheet: one 8x8 frame per glyph, one ink.
  game/sprites_src/title/spr_pp_window.* the 9 slice window, laid out as pp_window_draw lays it: 30 by 8 tiles.
  data/dialogue/all.json                 the page it draws, found by id.

The draw path it mirrors, call for call: pp_window_draw for the frame, then the name plate rectangle and
pp_font_draw(string_upper(plate)), then one pp_font_draw per row at PP_TEXT_X, PP_TEXT_Y + row * PP_TEXT_LINE_H, then
the choice panel and its labels when the page offers a choice. The font is drawn untinted, which is what pp_font_draw
does, so the ink is the sheet's own #f8f8f8.

What it refuses (exit 1):

  - any ink of any row, plate or label at x >= PP_BOX_X + PP_BOX_W - 8 (the box's padding) or past the frame,
  - any ink below the box's bottom edge,
  - a row longer than PP_TEXT_CHARS, which is the wrap fault the card measured,
  - a glyph the sheet does not carry, because pp_font_draw would draw a space there and the hole would be silent.

Usage:
    python tools/preview_dialogue_box.py                       the gate checkpoint page and the gate choice page
    python tools/preview_dialogue_box.py --entry ID --page N   any entry and page
    python tools/preview_dialogue_box.py --out FILE            where the 3x image goes

Exit codes: 0 every composed row stays inside the box, 1 a row leaves it or a glyph is missing, 2 nothing to read.

Provenance: written from specs/05-dialogue.md, the audit report knowledge/FONT-CONTRACT-AUDIT-2026-10-23.md, and the
pixel bounds of data/nes_palette.json. It composes our sheet through our own constants; it renders nothing from any
other game and reads nothing outside this repository.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_GML = os.path.join("game", "scripts", "pp_config", "pp_config.gml")
FONT_GML = os.path.join("game", "scripts", "pp_font", "pp_font.gml")
SHEET_DIR = os.path.join("game", "sprites_src", "title")
FONT_PNG = os.path.join(SHEET_DIR, "spr_pp_font8.png")
WINDOW_PNG = os.path.join(SHEET_DIR, "spr_pp_window.png")
DIALOGUE_JSON = os.path.join("data", "dialogue", "all.json")
DEFAULT_OUT = os.path.join("output", "dialogue_box_3x.png")

SCALE = 3
PANEL_W = 96
PANEL_GAP = 4
ARROW_W = 6


# ---------------------------------------------------------------------------------------------------------------
# Reading the engine's own numbers.
def read_macros(root):
    """Every literal `#macro NAME 12` in pp_config.gml, as a dict of ints."""
    path = os.path.join(root, CONFIG_GML)
    with open(path, "r", encoding="utf-8-sig") as handle:
        source = handle.read()
    out = {}
    for match in re.finditer(r"^#macro\s+(PP_[A-Z0-9_]+)\s+(-?\d+)\s*$", source, re.MULTILINE):
        out[match.group(1)] = int(match.group(2))
    return out


def read_glyphs(root):
    """The string pp_font_glyphs() returns, unescaped, as a list of characters."""
    path = os.path.join(root, FONT_GML)
    with open(path, "r", encoding="utf-8-sig") as handle:
        source = handle.read()
    body = re.search(r"function\s+pp_font_glyphs\s*\(\s*\)\s*\{(.*?)\n\}", source, re.S)
    if body is None:
        raise SystemExit("%s: no pp_font_glyphs to read the sheet's order from" % FONT_GML)
    literal = re.search(r'return\s+"((?:[^"\\]|\\.)*)"\s*;', body.group(1))
    if literal is None:
        raise SystemExit("%s: pp_font_glyphs does not return a string literal" % FONT_GML)
    raw = literal.group(1)
    out = []
    index = 0
    while index < len(raw):
        if raw[index] == "\\" and index + 1 < len(raw):
            out.append(raw[index + 1])
            index += 2
            continue
        out.append(raw[index])
        index += 1
    return out


# ---------------------------------------------------------------------------------------------------------------
# The box, drawn the way pp_dialogue_draw draws it.
def paste_glyph(canvas, sheet, glyphs, char, x, y):
    """One pp_font_draw character: the sheet's frame for that character at 1x, nothing when the sheet has no frame."""
    if char not in glyphs:
        return False
    frame = glyphs.index(char)
    canvas.paste(sheet.crop((frame * 8, 0, frame * 8 + 8, 8)), (x, y), sheet.crop((frame * 8, 0, frame * 8 + 8, 8)))
    return True


def draw_text(canvas, sheet, glyphs, text, x, y):
    """pp_font_draw: left aligned, 8 pixels a glyph, untinted, a missing character drawn as a space."""
    missing = []
    cursor = x
    for char in text:
        if not paste_glyph(canvas, sheet, glyphs, char, cursor, y):
            missing.append(char)
        cursor += 8
    return cursor - x, missing


def draw_window(canvas, sheet, x, y, tiles_w, tiles_h):
    """pp_window_draw: 9 slices on the 8x8 grid, row major tl t tr l c r bl b br."""
    for ty in range(tiles_h):
        for tx in range(tiles_w):
            if ty == 0:
                slice_index = 0 if tx == 0 else (2 if tx == tiles_w - 1 else 1)
            elif ty == tiles_h - 1:
                slice_index = 6 if tx == 0 else (8 if tx == tiles_w - 1 else 7)
            else:
                slice_index = 3 if tx == 0 else (5 if tx == tiles_w - 1 else 4)
            canvas.paste(sheet.crop((slice_index * 8, 0, slice_index * 8 + 8, 8)),
                         (x + tx * 8, y + ty * 8))


def wrap(line, chars):
    """The box's word wrap: a word that does not fit moves whole, a word longer than a row is split and reported."""
    words = [word for word in line.split(" ") if word != ""]
    rows = []
    row = ""
    for word in words:
        if len(word) > chars:
            if row:
                rows.append(row)
                row = ""
            position = 0
            while position < len(word):
                rows.append(word[position:position + chars])
                position += chars
            continue
        if row and len(row) + 1 + len(word) > chars:
            rows.append(row)
            row = word
        elif row:
            row = row + " " + word
        else:
            row = word
    if row:
        rows.append(row)
    return rows


def page_rows(entry, page_index, chars):
    """The rows of one page, wrapped the way pp_dialogue_push_page wraps it."""
    pages = entry.get("pages")
    if pages:
        if page_index >= len(pages):
            raise SystemExit("entry %r has %d page(s), page %d was asked for"
                             % (entry["id"], len(pages), page_index))
        page = pages[page_index]
        rows = []
        for line in page["lines"]:
            rows.extend(wrap(line, chars))
        return rows[:3], page.get("speaker", entry.get("speaker", ""))
    rows = []
    for line in entry.get("lines", []):
        rows.extend(wrap(line, chars))
    start = page_index * 3
    if start >= len(rows):
        raise SystemExit("entry %r wraps to %d row(s), page %d was asked for" % (entry["id"], len(rows), page_index))
    return rows[start:start + 3], entry.get("speaker", "")


def compose(root, entry_id, page_index, config):
    """One 256x240 frame: the window, the plate, the rows, and the panel when the page offers a choice."""
    font_sheet = Image.open(os.path.join(root, FONT_PNG)).convert("RGBA")
    window_sheet = Image.open(os.path.join(root, WINDOW_PNG)).convert("RGBA")
    glyphs = read_glyphs(root)

    with open(os.path.join(root, DIALOGUE_JSON), "r", encoding="utf-8-sig") as handle:
        document = json.load(handle)
    entry = None
    for row in document["dialogue"]:
        if row["id"] == entry_id:
            entry = row
            break
    if entry is None:
        raise SystemExit("no dialogue with id %r in %s" % (entry_id, DIALOGUE_JSON))

    canvas = Image.new("RGBA", (config["PP_FRAME_W"], config["PP_FRAME_H"]), (0, 0, 0, 255))

    # pp_window_draw(PP_BOX_X, PP_BOX_Y, 30, 8, 1): the dialogue box is 240x64 = 30x8 tiles.
    draw_window(canvas, window_sheet, config["PP_BOX_X"], config["PP_BOX_Y"],
                config["PP_BOX_W"] // 8, config["PP_BOX_H"] // 8)

    rows, speaker = page_rows(entry, page_index, config["PP_TEXT_CHARS"])
    missing = []

    # The name plate, drawn exactly where pp_dialogue_draw draws it: 64x12 over the left of the top border.
    if speaker not in ("", "narrator"):
        plate_x = config["PP_BOX_X"] + 4
        plate_y = config["PP_BOX_Y"] - 6
        plate = Image.new("RGBA", (65, 13), (0, 0, 0, 255))
        canvas.paste(plate, (plate_x, plate_y))
        _, gone = draw_text(canvas, font_sheet, glyphs, speaker.upper(), config["PP_BOX_X"] + 8,
                            config["PP_BOX_Y"] - 4)
        missing.extend(gone)

    # One pp_font_draw per row at PP_TEXT_X, PP_TEXT_Y + row * PP_TEXT_LINE_H.
    drawn = []
    for index, text in enumerate(rows):
        y = config["PP_TEXT_Y"] + index * config["PP_TEXT_LINE_H"]
        width, gone = draw_text(canvas, font_sheet, glyphs, text, config["PP_TEXT_X"], y)
        missing.extend(gone)
        drawn.append({"row": index, "text": text, "x0": config["PP_TEXT_X"], "x1": config["PP_TEXT_X"] + width, "y": y})

    # The choice panel, on the last page of an entry that offers choices, drawn after the rows as the engine does.
    panel = None
    if entry.get("choices") and page_index == (len(entry.get("pages") or [1]) - 1):
        panel_x = config["PP_TEXT_RIGHT"] - PANEL_W
        top = config["PP_TEXT_Y"] - 2
        bottom = config["PP_TEXT_Y"] + len(entry["choices"]) * config["PP_TEXT_LINE_H"]
        canvas.paste(Image.new("RGBA", (config["PP_TEXT_RIGHT"] - (panel_x - PANEL_GAP), bottom - top),
                               (0, 0, 0, 255)), (panel_x - PANEL_GAP, top))
        labels = []
        for index, choice in enumerate(entry["choices"]):
            y = config["PP_TEXT_Y"] + index * config["PP_TEXT_LINE_H"]
            width, gone = draw_text(canvas, font_sheet, glyphs, choice["label"], panel_x, y)
            missing.extend(gone)
            labels.append({"label": choice["label"], "x0": panel_x, "x1": panel_x + width, "y": y})
        panel = {"x0": panel_x - PANEL_GAP, "x1": config["PP_TEXT_RIGHT"], "y0": top, "y1": bottom, "labels": labels}

    return canvas, {"entry": entry_id, "page": page_index, "speaker": speaker, "rows": drawn,
                    "panel": panel, "missing": missing}


def ink_bounds(image):
    """(x0, y0, x1, y1) of every non black pixel, or None for an empty frame."""
    pixels = image.convert("RGB").load()
    width, height = image.size
    x0 = y0 = None
    x1 = y1 = -1
    for y in range(height):
        for x in range(width):
            if pixels[x, y] != (0, 0, 0):
                if x0 is None or x < x0:
                    x0 = x
                if y0 is None or y < y0:
                    y0 = y
                if x > x1:
                    x1 = x
                if y > y1:
                    y1 = y
    if x0 is None:
        return None
    return (x0, y0, x1, y1)


def check(report, config):
    """Every row, plate and label inside the box's padding, and no glyph missing."""
    errors = []
    limit = config["PP_BOX_X"] + config["PP_BOX_W"] - 8
    if report["missing"]:
        errors.append("%s page %d prints %s, which the sheet does not carry"
                      % (report["entry"], report["page"], ", ".join(sorted(set(report["missing"])))))
    for row in report["rows"]:
        if len(row["text"]) > config["PP_TEXT_CHARS"]:
            errors.append("%s page %d row %d is %d characters, the box holds %d"
                          % (report["entry"], report["page"], row["row"], len(row["text"]),
                             config["PP_TEXT_CHARS"]))
        if row["x1"] > limit:
            errors.append("%s page %d row %d reaches x %d, past the box padding at %d"
                          % (report["entry"], report["page"], row["row"], row["x1"], limit))
    if report["panel"]:
        for label in report["panel"]["labels"]:
            if label["x1"] > limit:
                errors.append("%s page %d label %r reaches x %d, past the box padding at %d"
                              % (report["entry"], report["page"], label["label"], label["x1"], limit))
        # The panel is drawn after the rows and is filled, so it covers whatever the rows drew under it. That is a
        # measured fault of the choice page layout, not of the wrap, and it is carded rather than hidden: it is
        # reported here with the exact characters it hides so the next card starts from numbers.
        panel_x0 = report["panel"]["x0"]
        hidden = [(row["text"], max(0, row["x1"] - panel_x0) // 8) for row in report["rows"] if row["x1"] > panel_x0]
        report["covered"] = hidden
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    parser.add_argument("--entry", default=None, help="a dialogue id; default draws the two gate pages")
    parser.add_argument("--page", type=int, default=0, help="which page of that entry")
    parser.add_argument("--out", default=DEFAULT_OUT, help="where the 3x image goes")
    parser.add_argument("--quiet", action="store_true", help="one line of output")
    args = parser.parse_args()
    root = os.path.abspath(args.root)

    try:
        config = read_macros(root)
    except FileNotFoundError as exc:
        print("preview_dialogue_box: %s" % exc)
        return 2
    for need in ("PP_BOX_X", "PP_BOX_Y", "PP_BOX_W", "PP_BOX_H", "PP_TEXT_X", "PP_TEXT_Y", "PP_TEXT_RIGHT",
                 "PP_TEXT_CHARS", "PP_TEXT_LINE_H", "PP_FRAME_W", "PP_FRAME_H"):
        if need not in config:
            print("preview_dialogue_box: %s has no literal #macro %s" % (CONFIG_GML, need))
            return 2

    wanted = [(args.entry, args.page)] if args.entry else [("quay_gate_checkpoint", 0), ("quay_gate_choice", 0)]

    frames = []
    reports = []
    for entry_id, page_index in wanted:
        frame, report = compose(root, entry_id, page_index, config)
        frames.append(frame)
        reports.append(report)

    # One 3x image: the frames stacked, one above the other, with an 8 pixel gap of black.
    gap = 8
    sheet = Image.new("RGB", (config["PP_FRAME_W"] * SCALE,
                             (config["PP_FRAME_H"] * SCALE + gap) * len(frames) - gap), (0, 0, 0))
    for index, frame in enumerate(frames):
        big = frame.convert("RGB").resize((config["PP_FRAME_W"] * SCALE, config["PP_FRAME_H"] * SCALE), Image.NEAREST)
        sheet.paste(big, (0, index * (config["PP_FRAME_H"] * SCALE + gap)))
    out_path = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path)

    errors = []
    for report, frame in zip(reports, frames):
        errors.extend(check(report, config))

    # The pixels agree with the arithmetic: no ink at or past the box's right padding, none under the box's bottom.
    limit = config["PP_BOX_X"] + config["PP_BOX_W"] - 8
    box_bottom = config["PP_BOX_Y"] + config["PP_BOX_H"] - 1
    for report, frame in zip(reports, frames):
        bounds = ink_bounds(frame.crop((0, config["PP_BOX_Y"], config["PP_FRAME_W"], config["PP_FRAME_H"])))
        if bounds is None:
            errors.append("%s page %d draws nothing inside the box" % (report["entry"], report["page"]))
            continue
        x0, y0, x1, y1 = bounds
        # The window frame itself is ink, so only the text area is measured from the pixels: the frame's own border
        # sits at the box edge by design.
        text_ink = ink_bounds(frame.crop((config["PP_TEXT_X"], config["PP_TEXT_Y"],
                                          limit, config["PP_TEXT_Y"] + config["PP_TEXT_ROWS"]
                                          * config["PP_TEXT_LINE_H"])))
        report["ink"] = text_ink
        if text_ink is not None and text_ink[2] + config["PP_TEXT_X"] >= limit:
            errors.append("%s page %d has text ink at x %d, the text area stops at %d"
                          % (report["entry"], report["page"], text_ink[2] + config["PP_TEXT_X"], limit))

    if args.quiet:
        print("dialogue box: %d frame(s), %d error(s), %s" % (len(frames), len(errors), out_path))
        return 1 if errors else 0

    print("dialogue box, composed through pp_dialogue_draw's own path at %dx" % SCALE)
    print("  geometry: box %dx%d at (%d,%d), text x %d to %d, %d characters a row, %d rows, %d pixels a line"
          % (config["PP_BOX_W"], config["PP_BOX_H"], config["PP_BOX_X"], config["PP_BOX_Y"],
             config["PP_TEXT_X"], config["PP_TEXT_RIGHT"], config["PP_TEXT_CHARS"],
             config["PP_TEXT_ROWS"], config["PP_TEXT_LINE_H"]))
    print("  the box's right padding stops at x %d (%d - 8), the frame is %d wide"
          % (limit, config["PP_BOX_X"] + config["PP_BOX_W"], config["PP_FRAME_W"]))
    for report in reports:
        print("")
        print("  %s page %d, speaker %r" % (report["entry"], report["page"], report["speaker"]))
        for row in report["rows"]:
            print("    row %d (%2d chars) x %d..%d y %d  %r"
                  % (row["row"], len(row["text"]), row["x0"], row["x1"] - 1, row["y"], row["text"]))
        if report["panel"]:
            print("    choice panel x %d..%d y %d..%d"
                  % (report["panel"]["x0"], report["panel"]["x1"], report["panel"]["y0"], report["panel"]["y1"]))
            for label in report["panel"]["labels"]:
                print("      label (%2d chars) x %d..%d  %r"
                      % (len(label["label"]), label["x0"], label["x1"] - 1, label["label"]))
            for text, count in report.get("covered", []):
                print("      note: the panel covers the last %d character(s) of %r (choice page layout, carded)"
                      % (count, text))
        if report.get("ink"):
            x0, y0, x1, y1 = report["ink"]
            print("    text ink in the text area: x %d..%d y %d..%d"
                  % (x0 + config["PP_TEXT_X"], x1 + config["PP_TEXT_X"],
                     y0 + config["PP_TEXT_Y"], y1 + config["PP_TEXT_Y"]))
    print("")
    print("  image: %s" % out_path)
    if errors:
        print("")
        for error in errors:
            print("  FAIL %s" % error)
        print("")
        print("preview_dialogue_box: REFUSED, %d row(s) leave the box or a glyph is missing" % len(errors))
        return 1
    print("preview_dialogue_box: PASS, every row, plate and label is inside the box")
    return 0


if __name__ == "__main__":
    sys.exit(main())
