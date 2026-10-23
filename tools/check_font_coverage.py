#!/usr/bin/env python3
"""check_font_coverage.py: refuse the build when a string the slice prints has no glyph.

Card R50 (t_41c97c88), steps S4 and S6 of ROADMAP-2026-10-23.md. The slice prints text from five places, and a
character that is not in `spr_pp_font8` is drawn as a space by `pp_font_draw`, so a missing glyph is a silent hole
in the dialogue box, not a crash. This tool is the gate that makes it loud.

What it reads, and why each part is read rather than typed here:

1. The glyph order comes from `game/scripts/pp_font/pp_font.gml`, from the string `pp_font_glyphs()` returns.
   That function is what the running game looks a character up in, so it is the covered set by definition. The
   same order is declared twice more, in `data/ui_layouts.json` (`font.glyphs`, which `tools/bake_meta.py` reads to
   wrap model output) and in `tools/art/pressstart2p_font.py` (`GLYPHS`, which rasterises the sheet). Those two are
   copies, so the tool refuses a run where they disagree with the runtime string instead of trusting one of them.

2. The sheet itself, `game/sprites_src/title/spr_pp_font8.png` plus its `.json` sidecar: one 8x8 frame per glyph, in
   that same order, one ink colour, no pixel of a frame outside its own cell, and no frame blank except the space.
   The sidecar's frame count has to equal the length of the order, so a sheet regenerated against a shorter glyph
   list is caught here rather than at the first draw.

3. The ink, against RULE 0: every visible pixel of every frame is one colour, that colour is one of the 64 outputs of
   the 2C02 (`data/nes_palette.json`), and it is already declared by a scene palette under `data/palettes/`. A new
   colour, or a colour no room declares, is a failure. The added glyphs of this card spend no new colour: they are
   drawn in the one ink the other 46 frames already use.

4. The printed text, from the five sources the card names. Only fields the game actually draws are scanned; ids,
   keys, paths, hex digests and the model prompt prose in `data/meta_bake.json` are not text on screen. The mapping
   is `PRINTED_FIELDS` below and it is deliberately explicit, so a file that grows a new printed field is a change
   to this table and not a silent gap:

     data/dialogue/all.json    dialogue[].lines[], dialogue[].pages[].lines[], dialogue[].choices[].label
     data/ui_layouts.json      screens[].text.* (every string under `text`, the layout's own labels and rows)
     data/title.json           nothing: its rows name art files and layer speeds, the menu words live in GML
     data/meta_bake.json       rows[].text[], rows[].hint, rows[].fallback.text[]
     data/enemies/all.json     enemies[].name

Usage:
    python tools/check_font_coverage.py             scan, print covered and missing, exit 1 on any missing character
    python tools/check_font_coverage.py --quiet     one line of output, the CI form
    python tools/check_font_coverage.py --root DIR  check another checkout (used by the tests)

Exit codes: 0 every character is covered and the sheet is sound, 1 a missing character or a font defect, 2 nothing
to read (a path is wrong), which is not a pass.

Provenance: written from specs/05-dialogue.md (the font and the box), specs/13-8bit-look.md (one 8x8 font, whole
pixels), specs/19-llm-talk.md Q6/D6 (code prepends the `* ` marker) and TITLE-COORD.md. No external code or art was
read or reused, and the tool reads nothing outside this repository.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FONT_GML = os.path.join("game", "scripts", "pp_font", "pp_font.gml")
UI_LAYOUTS = os.path.join("data", "ui_layouts.json")
RASTERISER = os.path.join("tools", "art", "pressstart2p_font.py")
UI_COMPOSER = os.path.join("tools", "art", "make_ui_nes.py")
SHEET_PNG = os.path.join("game", "sprites_src", "title", "spr_pp_font8.png")
SHEET_JSON = os.path.join("game", "sprites_src", "title", "spr_pp_font8.json")
NES_PALETTE = os.path.join("data", "nes_palette.json")
PALETTES_DIR = os.path.join("data", "palettes")

# Which strings in which file reach a draw call. See the module docstring; this table is the whole policy.
PRINTED_FIELDS = (
    ("data/dialogue/all.json", ("dialogue",), ("lines", "pages.lines", "choices.label")),
    ("data/ui_layouts.json", ("screens",), ("text",)),
    ("data/title.json", (), ()),
    ("data/meta_bake.json", ("rows",), ("text", "hint", "fallback.text")),
    ("data/enemies/all.json", ("enemies",), ("name",)),
)


class FontDefect(Exception):
    """A fault in the font itself: the sheet does not match the glyph order the game looks characters up in."""


# ---------------------------------------------------------------------------------------------------------------
# Reading the font.
# ---------------------------------------------------------------------------------------------------------------
def read_gml_glyphs(root):
    """The glyph string `pp_font_glyphs()` returns, unescaped, as a list of characters."""
    path = os.path.join(root, FONT_GML)
    with open(path, "r", encoding="utf-8-sig") as handle:
        source = handle.read()
    body = re.search(r"function\s+pp_font_glyphs\s*\(\s*\)\s*\{(.*?)\n\}", source, re.S)
    if body is None:
        raise FontDefect("%s: no pp_font_glyphs function to read the covered set from" % FONT_GML)
    literal = re.search(r'return\s+"((?:[^"\\]|\\.)*)"\s*;', body.group(1))
    if literal is None:
        raise FontDefect("%s: pp_font_glyphs does not return a string literal" % FONT_GML)
    raw = literal.group(1)
    out = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "\\" and index + 1 < len(raw):
            out.append(raw[index + 1])
            index += 2
            continue
        out.append(char)
        index += 1
    return out


def read_declared_glyphs(root):
    """The three copies of the order: the ui layout's `font.glyphs`, the rasteriser's GLYPHS and the UI composer's.

    `tools/art/make_ui_nes.py` is the file that WRITES `data/ui_layouts.json` and draws the battle, dialogue and menu
    screens with this sheet, so it carries its own copy of the set. It is checked here too: a composer whose alphabet
    is shorter than the sheet refuses the very text this tool is meant to protect.
    """
    with open(os.path.join(root, UI_LAYOUTS), "r", encoding="utf-8-sig") as handle:
        layout = json.load(handle)
    declared = (layout.get("font") or {}).get("glyphs")
    if not isinstance(declared, str) or not declared:
        raise FontDefect("%s: font.glyphs is missing, so the bake has no alphabet to wrap to" % UI_LAYOUTS)
    return declared, _read_glyphs_literal(os.path.join(root, RASTERISER)), \
        _read_glyphs_literal(os.path.join(root, UI_COMPOSER))


def _read_glyphs_literal(path):
    """A module's `GLYPHS = sorted("<literal>", key=ord)` line, as a sorted list."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        source = handle.read()
    match = re.search(r'^GLYPHS\s*=\s*sorted\(\s*"((?:[^"\\]|\\.)*)"', source, re.M)
    if match is None:
        raise FontDefect("%s: no GLYPHS literal to compare the sheet's frame order against" % path)
    literal = match.group(1).replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
    return sorted(literal, key=ord)


def read_sheet(root, order):
    """Verify the sheet frame by frame and return the set of inks it spends.

    One frame per glyph, in the order the game indexes by, one 8x8 cell each, and nothing lit outside the cell. A
    blank frame is a glyph that draws nothing, which for anything but the space is a hole in the text.
    """
    meta_path = os.path.join(root, SHEET_JSON)
    with open(meta_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    if (meta.get("frame_w"), meta.get("frame_h")) != (8, 8):
        raise FontDefect("%s: cell is %sx%s, the font is 8x8 (spec 13)"
                         % (SHEET_JSON, meta.get("frame_w"), meta.get("frame_h")))
    if meta.get("frames") != len(order):
        raise FontDefect("%s: %s frames but the glyph string has %d characters, so at least one glyph is at the "
                         "wrong index" % (SHEET_JSON, meta.get("frames"), len(order)))

    png_path = os.path.join(root, SHEET_PNG)
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
    expected = (8 * len(order), 8)
    if sheet.size != expected:
        raise FontDefect("%s: %s, one 8x8 frame per glyph expects %s" % (SHEET_PNG, sheet.size, expected))

    inks = set()
    blank = []
    for index, char in enumerate(order):
        lit = 0
        for y in range(8):
            for x in range(8):
                r, g, b, a = sheet.getpixel((index * 8 + x, y))
                if a == 0:
                    continue
                if a != 255:
                    raise FontDefect("%s: frame %d (%r) has a half transparent pixel at %d,%d"
                                     % (SHEET_PNG, index, char, x, y))
                inks.add("#%02x%02x%02x" % (r, g, b))
                lit += 1
        if lit == 0 and char != " ":
            blank.append(char)
    if blank:
        raise FontDefect("%s: %d glyph(s) draw nothing: %s"
                         % (SHEET_PNG, len(blank), ", ".join(repr(c) for c in blank)))
    return inks


def check_inks(root, inks):
    """RULE 0: the ink is a 2C02 output the scenes already declare, and there is only one of it."""
    with open(os.path.join(root, NES_PALETTE), "r", encoding="utf-8-sig") as handle:
        nes = json.load(handle)
    legal = {value.lower() for value in _collect_hexes(nes)}

    declared = set()
    palettes_dir = os.path.join(root, PALETTES_DIR)
    for name in sorted(os.listdir(palettes_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(root, PALETTES_DIR, name), "r", encoding="utf-8-sig") as handle:
            declared.update(_collect_hexes(json.load(handle)))

    errors = []
    if len(inks) != 1:
        errors.append("%s spends %d colours, the font is one ink (spec 13): %s"
                      % (SHEET_PNG, len(inks), ", ".join(sorted(inks))))
    for ink in sorted(inks):
        if ink not in legal:
            errors.append("%s: ink %s is not one of the 64 outputs of the 2C02 (data/nes_palette.json)" % (SHEET_PNG, ink))
        if ink not in declared:
            errors.append("%s: ink %s is declared by no palette under data/palettes/, so a room cannot spend it"
                          % (SHEET_PNG, ink))
    return errors


def _collect_hexes(node):
    """Every '#rrggbb' string anywhere in a JSON document."""
    out = []
    if isinstance(node, str):
        if re.match(r"^#[0-9a-fA-F]{6}$", node):
            out.append(node.lower())
    elif isinstance(node, dict):
        for value in node.values():
            out.extend(_collect_hexes(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(_collect_hexes(value))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Reading the printed text.
# ---------------------------------------------------------------------------------------------------------------
def _walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            for text in _walk_strings(value):
                yield text
    elif isinstance(node, list):
        for value in node:
            for text in _walk_strings(value):
                yield text


def _rows(document, path):
    """Every row dict under `first.second...`, e.g. ('dialogue',) or ('rows',)."""
    nodes = [document]
    for key in path:
        nxt = []
        for node in nodes:
            if isinstance(node, dict) and isinstance(node.get(key), list):
                nxt.extend(node[key])
        nodes = nxt
    return nodes


def _field_strings(row, dotted):
    """The printed strings at a dotted field, e.g. 'pages.lines' or 'fallback.text'."""
    nodes = [row]
    for part in dotted.split("."):
        nxt = []
        for node in nodes:
            if isinstance(node, dict) and part in node:
                nxt.append(node[part])
        nodes = nxt
    out = []
    for node in nodes:
        out.extend(_walk_strings(node))
    return out


def scan_printed(root, wanted):
    """Return ([{file, field, text}], [files read with no printed field])."""
    found = []
    silent = []
    for path, row_path, fields in PRINTED_FIELDS:
        full = os.path.join(root, path)
        if not os.path.isfile(full):
            raise FileNotFoundError("%s is missing, so the coverage of its text is unmeasured" % path)
        with open(full, "r", encoding="utf-8-sig") as handle:
            document = json.load(handle)
        count = 0
        if fields:
            for row in _rows(document, row_path):
                for field in fields:
                    for text in _field_strings(row, field):
                        found.append({"file": path, "field": field, "text": text})
                        count += 1
        if count == 0:
            silent.append(path)
        wanted.append((path, count))
    return found, silent


# ---------------------------------------------------------------------------------------------------------------
# The verdict.
# ---------------------------------------------------------------------------------------------------------------
def coverage(root):
    """(order, printed, missing) where missing is a list of {char, file, field, text}."""
    order = read_gml_glyphs(root)
    declared, raster, composer = read_declared_glyphs(root)
    if declared != "".join(order):
        raise FontDefect("%s: font.glyphs is %r, the runtime string is %r"
                         % (UI_LAYOUTS, declared, "".join(order)))
    if raster != order:
        raise FontDefect("%s: GLYPHS is %r, the runtime string is %r"
                         % (RASTERISER, "".join(raster), "".join(order)))
    if composer != order:
        raise FontDefect("%s: GLYPHS is %r, the runtime string is %r"
                         % (UI_COMPOSER, "".join(composer), "".join(order)))

    inks = read_sheet(root, order)
    ink_errors = check_inks(root, inks)

    covered = set(order)
    printed, _ = scan_printed(root, [])
    missing = []
    seen = set()
    for row in printed:
        for char in row["text"]:
            if char in covered or char in seen:
                continue
            seen.add(char)
            missing.append({"char": char, "file": row["file"], "field": row["field"], "text": row["text"]})
    return order, inks, ink_errors, printed, missing


def printable(char):
    """A character as ASCII a terminal cannot mangle: repr for the marks, '?' for anything unprintable."""
    if 32 <= ord(char) < 127:
        return repr(char)
    return "U+%04X" % ord(char)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    parser.add_argument("--quiet", action="store_true", help="one line of output, the CI form")
    args = parser.parse_args()
    root = os.path.abspath(args.root)

    try:
        order, inks, ink_errors, printed, missing = coverage(root)
    except FileNotFoundError as exc:
        print("check_font_coverage: %s" % exc)
        return 2
    except FontDefect as exc:
        print("check_font_coverage: %s" % exc)
        return 1

    per_file = {}
    for row in printed:
        per_file[row["file"]] = per_file.get(row["file"], 0) + 1
    unread_fields = [path for path, _, _ in PRINTED_FIELDS if per_file.get(path, 0) == 0]

    if args.quiet:
        print("check_font_coverage: %d glyphs, %d printed strings, %d missing, %d ink error(s), exit %d"
              % (len(order), len(printed), len(missing), len(ink_errors), 1 if (missing or ink_errors) else 0))
        return 1 if (missing or ink_errors) else 0

    print("font: %s" % SHEET_PNG)
    print("  %d glyphs in ASCII order: %s" % (len(order), "".join(order)))
    print("  ink: %s" % ", ".join(sorted(inks)))
    print("  the game, %s, %s and %s all declare the same order"
          % (UI_LAYOUTS, RASTERISER, UI_COMPOSER))
    for error in ink_errors:
        print("  FAIL %s" % error)
    print("")
    print("printed text scanned (a file with 0 is a file this slice prints nothing from):")
    for path, _, _ in PRINTED_FIELDS:
        print("  %-28s %4d string(s)" % (path, per_file.get(path, 0)))
    required = set()
    for row in printed:
        required.update(row["text"])
    print("")
    print("required set (%d): %s" % (len(required), "".join(sorted(required))))
    print("covered set  (%d): %s" % (len(order), "".join(order)))
    print("missing set  (%d): %s" % (len(missing), ",".join(printable(row["char"]) for row in missing)))
    for row in missing:
        print("  %s not in the font, printed by %s %s: %s"
              % (printable(row["char"]), row["file"], row["field"], row["text"]))
    if unread_fields:
        print("")
        print("note: %s carries no printed field, so it contributes no characters" % ", ".join(unread_fields))
    if missing or ink_errors:
        print("")
        print("check_font_coverage: REFUSED, %d missing character(s) and %d font defect(s). Add the glyph to the "
              "sheet inside the existing 8x8 cell, or drop the character from the text."
              % (len(missing), len(ink_errors)))
        return 1
    print("")
    print("check_font_coverage: PASS, every character the slice prints is in the font")
    return 0


if __name__ == "__main__":
    sys.exit(main())
