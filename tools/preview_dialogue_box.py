#!/usr/bin/env python3
"""preview_dialogue_box.py: compose the real dialogue box at 3x, and refuse a row that leaves the box.

Card t_1d828fcd (DIALOGUE-FONT-WIRE) and card t_01432e14 (DIALOGUE-CHOICE-PANEL). The defects those cards fixed were
only provable with pixels and with arithmetic, and this tool is the pixels half: it draws one page of
`data/dialogue/all.json` the way `pp_dialogue_draw` draws it, from the same assets and the same numbers, and then
measures where the ink landed.

What it reads, and why nothing is typed twice here:

  game/scripts/pp_config/pp_config.gml   PP_BOX_X/Y/W/H, PP_TEXT_X/Y/RIGHT/CHARS/LINE_H/ROWS, and the choice rows'
                                         PP_CHOICE_ARROW_X/ARROW_W/LABEL_X. The wrap width is read from the same macro
                                         the engine wraps with, so a preview can never disagree with the box about how
                                         many characters fit.
  game/scripts/pp_font/pp_font.gml       pp_font_glyphs(), the sheet's frame order, exactly as pp_font_draw looks a
                                         character up.
  game/sprites_src/title/spr_pp_font8.*  the glyph sheet: one 8x8 frame per glyph, one ink.
  game/sprites_src/title/spr_pp_window.* the 9 slice window, laid out as pp_window_draw lays it: 30 by 8 tiles.
  data/dialogue/all.json                 the page it draws, found by id.

The draw path it mirrors, call for call: pp_window_draw for the frame, then the name plate rectangle and
pp_font_draw(string_upper(plate)), then one pp_font_draw per row at PP_TEXT_X, PP_TEXT_Y + row * PP_TEXT_LINE_H, and
then, on the last page of an entry that offers choices, the choice rows in the rows' place: the 6x6 cursor at
PP_CHOICE_ARROW_X and one pp_font_draw per label at PP_CHOICE_LABEL_X, with no row drawn under them (spec 05, card
t_01432e14). The font is drawn untinted, which is what pp_font_draw does, so the ink is the sheet's own #f8f8f8.

What it refuses (exit 1):

  - any ink of any row, plate or label at x >= PP_BOX_X + PP_BOX_W - 8 (the box's padding) or past the frame,
  - any ink below the box's bottom edge,
  - a row longer than PP_TEXT_CHARS, which is the wrap fault the first card measured,
  - a glyph the sheet does not carry, because pp_font_draw would draw a space there and the hole would be silent,
  - ANY overlap between a dialogue row's cell and a choice glyph's cell, or between a choice glyph and the cursor.
    This is the card t_01432e14 fault: the old 96 pixel panel covered 3 to 6 characters of every prompt row. The
    engine answers it by not drawing the rows at all while the labels are up, so the rects this tool compares are the
    rects actually drawn; a later edit that draws both fails here instead of shipping.

Usage:
    python tools/preview_dialogue_box.py                       the gate checkpoint page and the gate choice page
    python tools/preview_dialogue_box.py --entry ID --page N   any entry and page
    python tools/preview_dialogue_box.py --cursor N            which choice the cursor sits on
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
CHARS_DIR = os.path.join("game", "sprites_src", "chars")
DIALOGUE_JSON = os.path.join("data", "dialogue", "all.json")
DEFAULT_OUT = os.path.join("output", "dialogue_box_3x.png")

SCALE = 3


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
    """The rows of one page, wrapped the way pp_dialogue_push_page wraps it, with its plate and its bust name."""
    portrait = entry.get("portrait", "")
    pages = entry.get("pages")
    if pages:
        if page_index >= len(pages):
            raise SystemExit("entry %r has %d page(s), page %d was asked for"
                             % (entry["id"], len(pages), page_index))
        page = pages[page_index]
        rows = []
        for line in page["lines"]:
            rows.extend(wrap(line, chars))
        # pp_dialogue_pages: the page's own value replaces the entry's, the way its speaker does. The empty string is
        # a page that draws no bust.
        if "portrait" in page:
            portrait = page["portrait"]
        return rows[:3], page.get("speaker", entry.get("speaker", "")), portrait
    rows = []
    for line in entry.get("lines", []):
        rows.extend(wrap(line, chars))
    start = page_index * 3
    if start >= len(rows):
        raise SystemExit("entry %r wraps to %d row(s), page %d was asked for" % (entry["id"], len(rows), page_index))
    return rows[start:start + 3], entry.get("speaker", ""), portrait


def page_count(entry, chars):
    """How many pages the box makes of this entry, the way pp_dialogue_push_page makes them."""
    if entry.get("pages"):
        return len(entry["pages"])
    rows = []
    for line in entry.get("lines", []):
        rows.extend(wrap(line, chars))
    return max(1, (len(rows) + 2) // 3)


def ink_colour(sheet):
    """The sheet's own ink, so the cursor block is drawn in the colour pp_font_draw would draw a glyph in."""
    pixels = sheet.load()
    for y in range(sheet.height):
        for x in range(sheet.width):
            pixel = pixels[x, y]
            if pixel[3] > 0:
                return pixel
    return (255, 255, 255, 255)


def compose(root, entry_id, page_index, config, cursor=0):
    """One 256x240 frame: the window, the plate, the rows, or the choice rows in their place."""
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

    rows, speaker, bust = page_rows(entry, page_index, config["PP_TEXT_CHARS"])
    missing = []
    portrait_rect = None

    # The bust (spec 05 Geometry, card t_4d6b0f4b): drawn BEFORE the plate and the rows, exactly where
    # pp_dialogue_draw draws it, from the same sheet name the engine asks pp_art_info for. A page with no bust draws
    # none. A page whose sheet is missing is an error here rather than a silent nothing, because the preview's job is
    # to catch the data pointing at art that does not exist.
    if bust:
        bust_path = os.path.join(root, CHARS_DIR, "spr_pp_portrait_%s.png" % bust)
        if not os.path.isfile(bust_path):
            raise SystemExit("page %d of %r names the bust %r, but %s is not there"
                             % (page_index, entry_id, bust, bust_path))
        bust_image = Image.open(bust_path).convert("RGBA")
        canvas.paste(bust_image, (config["PP_PORTRAIT_X"], config["PP_PORTRAIT_Y"]), bust_image)
        portrait_rect = {"x0": config["PP_PORTRAIT_X"], "y0": config["PP_PORTRAIT_Y"],
                         "x1": config["PP_PORTRAIT_X"] + bust_image.width,
                         "y1": config["PP_PORTRAIT_Y"] + bust_image.height,
                         "w": bust_image.width, "h": bust_image.height}

    # The name plate, drawn exactly where pp_dialogue_draw draws it: 64 wide over the left of the top border, moved
    # right of the bust when there is one, so the two never share a pixel.
    plate_rect = None
    if speaker not in ("", "narrator"):
        plate_x = config["PP_PLATE_BUST_X"] if bust else config["PP_PLATE_X"]
        plate_y = config["PP_BOX_Y"] - 6
        plate = Image.new("RGBA", (config["PP_PLATE_W"] + 1, 13), (0, 0, 0, 255))
        canvas.paste(plate, (plate_x, plate_y))
        plate_rect = {"x0": plate_x, "y0": plate_y,
                      "x1": plate_x + config["PP_PLATE_W"] + 1, "y1": plate_y + 13}
        _, gone = draw_text(canvas, font_sheet, glyphs, speaker.upper(), plate_x + 4,
                            config["PP_BOX_Y"] - 4)
        missing.extend(gone)

    line_h = config["PP_TEXT_LINE_H"]
    drawn = []
    menu = None

    # The last page of an entry that offers choices replaces its rows with the labels (spec 05, card t_01432e14):
    # the cursor in column 0 of the text area, the label in column 1, and no row drawn underneath.
    offers = bool(entry.get("choices")) and page_index == page_count(entry, config["PP_TEXT_CHARS"]) - 1
    if offers:
        labels = []
        for index, choice in enumerate(entry["choices"]):
            y = config["PP_TEXT_Y"] + index * line_h
            width, gone = draw_text(canvas, font_sheet, glyphs, choice["label"], config["PP_CHOICE_LABEL_X"], y)
            missing.extend(gone)
            labels.append({"label": choice["label"], "x0": config["PP_CHOICE_LABEL_X"],
                           "x1": config["PP_CHOICE_LABEL_X"] + width, "y0": y, "y1": y + line_h})
        arrow = None
        if 0 <= cursor < len(labels):
            arrow_x = config["PP_CHOICE_ARROW_X"]
            arrow_y = config["PP_TEXT_Y"] + cursor * line_h + 1
            arrow = {"x0": arrow_x, "y0": arrow_y,
                     "x1": arrow_x + config["PP_CHOICE_ARROW_W"], "y1": arrow_y + config["PP_CHOICE_ARROW_W"]}
            canvas.paste(Image.new("RGBA", (config["PP_CHOICE_ARROW_W"], config["PP_CHOICE_ARROW_W"]),
                                   ink_colour(font_sheet)), (arrow_x, arrow_y))
        menu = {"labels": labels, "arrow": arrow, "rows_replaced": rows}
    else:
        # One pp_font_draw per row at PP_TEXT_X, PP_TEXT_Y + row * PP_TEXT_LINE_H.
        for index, text in enumerate(rows):
            y = config["PP_TEXT_Y"] + index * line_h
            width, gone = draw_text(canvas, font_sheet, glyphs, text, config["PP_TEXT_X"], y)
            missing.extend(gone)
            drawn.append({"row": index, "text": text, "x0": config["PP_TEXT_X"], "x1": config["PP_TEXT_X"] + width,
                          "y0": y, "y1": y + line_h})

    return canvas, {"entry": entry_id, "page": page_index, "speaker": speaker, "rows": drawn,
                    "portrait": portrait_rect, "plate": plate_rect, "menu": menu, "missing": missing}


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


def layout_conflicts(entry, page, row_rects, label_rects, arrow_rect):
    """Any dialogue row cell that shares a pixel with a choice glyph or the cursor. This is the card t_01432e14 fault.

    The rows and the labels are both drawn in the text area's three 10 pixel rows, so this only holds while a choice
    page draws the labels INSTEAD of the rows. That is the ruling, and this is the mechanical proof of it: hand it both
    lists and it fails, which is what the old 96 pixel panel did to 3 to 6 characters of every prompt row.
    """
    errors = []
    targets = list(label_rects) + ([arrow_rect] if arrow_rect else [])
    for row in row_rects:
        for cell in targets:
            if (row["x0"] < cell["x1"] and cell["x0"] < row["x1"]
                    and row["y0"] < cell["y1"] and cell["y0"] < row["y1"]):
                what = "the cursor" if cell is arrow_rect else "a choice label"
                errors.append("%s page %d: %s at x %d..%d y %d..%d is drawn over the row %r at x %d..%d"
                              % (entry, page, what, cell["x0"], cell["x1"] - 1, cell["y0"], cell["y1"] - 1,
                                 row["text"], row["x0"], row["x1"] - 1))
    return errors


def check(report, config):
    """Every row, plate and label inside the box's padding, nothing drawn over anything, and no glyph missing."""
    errors = []
    limit = config["PP_BOX_X"] + config["PP_BOX_W"] - 8
    if report["missing"]:
        errors.append("%s page %d prints %s, which the sheet does not carry"
                      % (report["entry"], report["page"], ", ".join(sorted(set(report["missing"])))))

    # The bust, when the page carries one: 48x48 at the portrait's own x and y, its last row one pixel above the box,
    # the whole sheet inside the 256x240 frame, and no pixel shared with a dialogue row, a choice label or the cursor.
    bust = report["portrait"]
    if bust is not None:
        if (bust["w"], bust["h"]) != (config["PP_PORTRAIT_SIZE"], config["PP_PORTRAIT_SIZE"]):
            errors.append("%s page %d draws a %dx%d bust, the geometry says %dx%d"
                          % (report["entry"], report["page"], bust["w"], bust["h"],
                             config["PP_PORTRAIT_SIZE"], config["PP_PORTRAIT_SIZE"]))
        if bust["y1"] != config["PP_BOX_Y"]:
            errors.append("%s page %d puts the bust's last row at y %d, the box's top edge is y %d"
                          % (report["entry"], report["page"], bust["y1"] - 1, config["PP_BOX_Y"]))
        if bust["x1"] > config["PP_FRAME_W"] or bust["y1"] > config["PP_FRAME_H"]:
            errors.append("%s page %d draws the bust outside the %dx%d frame"
                          % (report["entry"], report["page"], config["PP_FRAME_W"], config["PP_FRAME_H"]))
        targets = list(report["rows"])
        if report["menu"]:
            targets += list(report["menu"]["labels"])
            if report["menu"]["arrow"] is not None:
                targets.append(report["menu"]["arrow"])
        for cell in targets:
            if (bust["x0"] < cell["x1"] and cell["x0"] < bust["x1"]
                    and bust["y0"] < cell["y1"] and cell["y0"] < bust["y1"]):
                errors.append("%s page %d draws the bust over %r at x %d..%d y %d..%d"
                              % (report["entry"], report["page"], cell.get("text", cell.get("label", "the cursor")),
                                 cell["x0"], cell["x1"] - 1, cell["y0"], cell["y1"] - 1))
        if report["plate"] is not None and (bust["x0"] < report["plate"]["x1"] and report["plate"]["x0"] < bust["x1"]
                                            and bust["y0"] < report["plate"]["y1"]
                                            and report["plate"]["y0"] < bust["y1"]):
            errors.append("%s page %d draws the plate at x %d..%d over the bust at x %d..%d"
                          % (report["entry"], report["page"], report["plate"]["x0"], report["plate"]["x1"] - 1,
                             bust["x0"], bust["x1"] - 1))

    for row in report["rows"]:
        if len(row["text"]) > config["PP_TEXT_CHARS"]:
            errors.append("%s page %d row %d is %d characters, the box holds %d"
                          % (report["entry"], report["page"], row["row"], len(row["text"]),
                             config["PP_TEXT_CHARS"]))
        if row["x1"] > limit:
            errors.append("%s page %d row %d reaches x %d, past the box padding at %d"
                          % (report["entry"], report["page"], row["row"], row["x1"], limit))

    menu = report["menu"]
    if menu:
        if len(menu["labels"]) > config["PP_TEXT_ROWS"]:
            errors.append("%s page %d offers %d choices, the text area has %d rows"
                          % (report["entry"], report["page"], len(menu["labels"]), config["PP_TEXT_ROWS"]))
        for label in menu["labels"]:
            if label["x1"] > limit:
                errors.append("%s page %d label %r reaches x %d, past the box padding at %d"
                              % (report["entry"], report["page"], label["label"], label["x1"], limit))
            if label["x0"] < config["PP_TEXT_X"]:
                errors.append("%s page %d label %r starts at x %d, left of the text area at %d"
                              % (report["entry"], report["page"], label["label"], label["x0"],
                                 config["PP_TEXT_X"]))
        arrow = menu["arrow"]
        if arrow is not None:
            if arrow["x0"] < config["PP_TEXT_X"] or arrow["x1"] > config["PP_CHOICE_LABEL_X"]:
                errors.append("%s page %d cursor x %d..%d does not fit the first text column x %d..%d"
                              % (report["entry"], report["page"], arrow["x0"], arrow["x1"] - 1,
                                 config["PP_TEXT_X"], config["PP_CHOICE_LABEL_X"] - 1))
        errors.extend(layout_conflicts(report["entry"], report["page"], report["rows"],
                                      menu["labels"], menu["arrow"]))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    parser.add_argument("--entry", default=None, help="a dialogue id; default draws the two gate pages")
    parser.add_argument("--page", type=int, default=0, help="which page of that entry")
    parser.add_argument("--cursor", type=int, default=0, help="which choice the cursor sits on")
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
                 "PP_TEXT_CHARS", "PP_TEXT_LINE_H", "PP_TEXT_ROWS", "PP_FRAME_W", "PP_FRAME_H",
                 "PP_CHOICE_ARROW_X", "PP_CHOICE_ARROW_W", "PP_CHOICE_LABEL_X",
                 "PP_PORTRAIT_X", "PP_PORTRAIT_Y", "PP_PORTRAIT_SIZE",
                 "PP_PLATE_X", "PP_PLATE_W", "PP_PLATE_BUST_X"):
        if need not in config:
            print("preview_dialogue_box: %s has no literal #macro %s" % (CONFIG_GML, need))
            return 2

    wanted = [(args.entry, args.page)] if args.entry else [("quay_gate_checkpoint", 0), ("quay_gate_choice", 0)]

    frames = []
    reports = []
    for entry_id, page_index in wanted:
        frame, report = compose(root, entry_id, page_index, config, args.cursor)
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
        if report["portrait"] is not None:
            bust = report["portrait"]
            print("    bust %dx%d at x %d..%d y %d..%d, last row %d, the box's top edge %d"
                  % (bust["w"], bust["h"], bust["x0"], bust["x1"] - 1, bust["y0"], bust["y1"] - 1,
                     bust["y1"] - 1, config["PP_BOX_Y"]))
        else:
            print("    no bust on this page")
        if report["plate"] is not None:
            print("    plate x %d..%d y %d..%d" % (report["plate"]["x0"], report["plate"]["x1"] - 1,
                                                   report["plate"]["y0"], report["plate"]["y1"] - 1))
        for row in report["rows"]:
            print("    row %d (%2d chars) x %d..%d y %d  %r"
                  % (row["row"], len(row["text"]), row["x0"], row["x1"] - 1, row["y0"], row["text"]))
        if report["menu"]:
            print("    the rows are replaced by %d choice row(s), cursor in column 0"
                  % len(report["menu"]["labels"]))
            arrow = report["menu"]["arrow"]
            if arrow is not None:
                print("      cursor x %d..%d y %d..%d"
                      % (arrow["x0"], arrow["x1"] - 1, arrow["y0"], arrow["y1"] - 1))
            for label in report["menu"]["labels"]:
                print("      label (%2d chars) x %d..%d  %r"
                      % (len(label["label"]), label["x0"], label["x1"] - 1, label["label"]))
            for text in report["menu"]["rows_replaced"]:
                print("      replaced row (not drawn) %r" % text)
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
        print("preview_dialogue_box: REFUSED, %d row(s) leave the box, overlap a choice or a glyph is missing"
              % len(errors))
        return 1
    print("preview_dialogue_box: PASS, every row, plate and choice is inside the box and nothing overlaps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
