#!/usr/bin/env python3
"""preview_battle_font.py: compose the battle menu and the game over card at 3x, through the real draw path.

Card BATTLE-FONT-WIRE. The card's claim is that the battle and app screens print the 8x8 sheet, measured in the
sheet's 8 pixel cell, and that the one-ink rule still holds. Arithmetic cannot show that; this tool draws the two
frames the card names and then measures where the ink landed, the way tools/preview_dialogue_box.py does for the
dialogue box.

What it reads, and why nothing is typed twice here:

  game/scripts/pp_config/pp_config.gml            PP_FRAME_W/H, PP_MENU_TOP and the rest of the literal macros.
  game/scripts/pp_font/pp_font.gml                pp_font_glyphs(), the sheet's frame order, and pp_font_cols().
  game/sprites_src/title/spr_pp_font8.*           the glyph sheet: one 8x8 frame per glyph, one ink.
  data/palette.json + data/room_palettes.json     the role colours the screens fill with (ink, paper, dim, text).
  game/scripts/pp_battle_commands/pp_command_table the five labels and their order.
  data/enemies/all.json, data/characters/party.json  the enemy's name and the hero's HP and WILL numbers.
  data/encounters/all.json + data/dialogue/all.json  the line the message window prints.
  game/scripts/pp_battle_director/pp_battle_director.gml  the game over rows and the refusal sentences.

The draw path it mirrors, call for call, is pp_battle_draw_menu for frame one and pp_battle_draw_gameover for frame
two: the rectangles at the same coordinates, then pp_font_draw's equivalent (one 8 px frame pasted per character, in
the sheet's own ink, never tinted).

What it refuses (exit 1):

  - a character of any drawn string that the sheet does not carry, because pp_font_draw would draw a space there,
  - a string whose ink leaves the region its owner gave it (the menu band, the message window, the card's inner
    rectangle, the black band under the card),
  - the game over card's inner rectangle being smaller than the card's own rows, which is what the row and note
    arithmetic below measures rather than assumes,
  - the card geometry in this tool disagreeing with the numbers in pp_battle_draw_gameover: the tool refuses to
    preview a card the game no longer draws.

Usage:
    python tools/preview_battle_font.py                    the battle menu and the game over card
    python tools/preview_battle_font.py --out FILE         where the 3x image goes
    python tools/preview_battle_font.py --quiet            one line of output

Exit codes: 0 every string is in the sheet and inside its region, 1 a fault, 2 nothing to read.

Provenance: written from knowledge/FONT-CONTRACT-AUDIT-2026-10-23.md (rules 1 to 6), specs/13-8bit-look.md (one 8x8
font, whole pixels) and specs/07-battle-director.md. It composes our sheet through our own constants and renders
nothing from any other game; it reads nothing outside this repository.
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
COMMANDS_GML = os.path.join("game", "scripts", "pp_battle_commands", "pp_battle_commands.gml")
DIRECTOR_GML = os.path.join("game", "scripts", "pp_battle_director", "pp_battle_director.gml")
FONT_PNG = os.path.join("game", "sprites_src", "title", "spr_pp_font8.png")
PALETTE_JSON = os.path.join("data", "palette.json")
ROOM_PALETTES_JSON = os.path.join("data", "room_palettes.json")
ENEMIES_JSON = os.path.join("data", "enemies", "all.json")
PARTY_JSON = os.path.join("data", "characters", "party.json")
ENCOUNTERS_JSON = os.path.join("data", "encounters", "all.json")
DIALOGUE_JSON = os.path.join("data", "dialogue", "all.json")
DEFAULT_OUT = os.path.join("output", "battle_font_3x.png")

SCALE = 3
CELL = 8

# pp_battle_draw_gameover's own card, as the literals the function draws. The tool checks each of these strings is in
# that function, so a moved card fails here instead of producing a preview of a screen the game no longer has.
GAMEOVER_GEOMETRY = (
    "draw_rectangle(0, 0, PP_FRAME_W, PP_FRAME_H, false)",
    "draw_rectangle(63, 63, 193, 177, false)",
    "draw_rectangle(64, 64, 192, 176, false)",
    "draw_rectangle(66, 66, 190, 174, false)",
    "draw_rectangle(96, 94, 160, 96, false)",
)


# ---------------------------------------------------------------------------------------------------------------
# Reading the engine's own numbers.
def read_macros(root):
    """Every literal `#macro NAME 12` in pp_config.gml, as a dict of ints."""
    with open(os.path.join(root, CONFIG_GML), "r", encoding="utf-8-sig") as handle:
        source = handle.read()
    out = {}
    for match in re.finditer(r"^#macro\s+(PP_[A-Z0-9_]+)\s+(-?\d+)\s*$", source, re.MULTILINE):
        out[match.group(1)] = int(match.group(2))
    return out


def read_glyphs(root):
    """The string pp_font_glyphs() returns, unescaped, as a list of characters."""
    with open(os.path.join(root, FONT_GML), "r", encoding="utf-8-sig") as handle:
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


def read_roles(root):
    """role name -> '#rrggbb' for the palette set the ui screens draw with."""
    with open(os.path.join(root, PALETTE_JSON), "r", encoding="utf-8-sig") as handle:
        palette = json.load(handle)
    with open(os.path.join(root, ROOM_PALETTES_JSON), "r", encoding="utf-8-sig") as handle:
        rooms = json.load(handle)
    wanted = rooms.get("default")
    roles = {}
    for row in rooms.get("sets", []):
        if row.get("id") == wanted:
            roles = row.get("roles") or []
            break
    colours = palette["colours"]
    out = {}
    for name in roles:
        if name in palette["roles"]:
            out[name] = colours[palette["roles"][name]]
    for need in ("ink", "paper", "dim", "text"):
        if need not in out:
            raise SystemExit("data/palette.json and data/room_palettes.json do not give the %r role" % need)
    return out


def read_commands(root):
    """The five labels, in the order pp_command_table returns them."""
    with open(os.path.join(root, COMMANDS_GML), "r", encoding="utf-8-sig") as handle:
        source = handle.read()
    body = re.search(r"function\s+pp_command_table\s*\(\s*\)\s*\{(.*?)\n\}", source, re.S)
    if body is None:
        raise SystemExit("%s: no pp_command_table" % COMMANDS_GML)
    labels = re.findall(r"label:\s*\"([^\"]+)\"", body.group(1))
    if len(labels) != 5:
        raise SystemExit("%s: pp_command_table gives %d labels, the menu has five" % (COMMANDS_GML, len(labels)))
    return labels


def read_director(root):
    """The game over rows, the refusal sentences and the card's own geometry, read rather than typed."""
    with open(os.path.join(root, DIRECTOR_GML), "r", encoding="utf-8-sig") as handle:
        source = handle.read()
    rows_body = re.search(r"function\s+pp_battle_gameover_rows\s*\(\s*\)\s*\{(.*?)\n\}", source, re.S)
    if rows_body is None:
        raise SystemExit("%s: no pp_battle_gameover_rows" % DIRECTOR_GML)
    rows = re.findall(r"\"([^\"]+)\"", rows_body.group(1))
    note_body = re.search(r"function\s+pp_battle_draw_gameover\s*\(\s*_battle\s*\)\s*\{(.*?)\n\}", source, re.S)
    if note_body is None:
        raise SystemExit("%s: no pp_battle_draw_gameover" % DIRECTOR_GML)
    card = note_body.group(1)
    for line in GAMEOVER_GEOMETRY:
        if line not in card:
            raise SystemExit("%s: pp_battle_draw_gameover no longer draws %r, so this preview is of a card that "
                             "does not exist" % (DIRECTOR_GML, line))
    notes = re.findall(r'_battle\.gameover_note = "([^"]+)"', source)
    return rows, notes


def read_party_and_enemy(root, enemy_id):
    with open(os.path.join(root, PARTY_JSON), "r", encoding="utf-8-sig") as handle:
        party = json.load(handle)["characters"][0]
    with open(os.path.join(root, ENEMIES_JSON), "r", encoding="utf-8-sig") as handle:
        enemies = json.load(handle)["enemies"]
    enemy = None
    for row in enemies:
        if row.get("id") == enemy_id:
            enemy = row
            break
    if enemy is None:
        raise SystemExit("data/enemies/all.json has no enemy %r" % enemy_id)
    return party, enemy


def read_message(root, encounter_id):
    """The first line of the encounter's intro dialogue, wrapped the way pp_text_board_draw wraps it."""
    with open(os.path.join(root, ENCOUNTERS_JSON), "r", encoding="utf-8-sig") as handle:
        encounters = json.load(handle)["encounters"]
    with open(os.path.join(root, DIALOGUE_JSON), "r", encoding="utf-8-sig") as handle:
        dialogue = json.load(handle)["dialogue"]
    encounter = None
    for row in encounters:
        if row.get("id") == encounter_id:
            encounter = row
            break
    if encounter is None:
        raise SystemExit("data/encounters/all.json has no encounter %r" % encounter_id)
    wanted = encounter.get("intro_dialogue")
    lines = []
    for row in dialogue:
        if row.get("id") == wanted:
            lines = row.get("lines") or []
            break
    if not lines:
        raise SystemExit("the encounter %r names no intro line this preview can draw" % encounter_id)
    return lines[0]


# ---------------------------------------------------------------------------------------------------------------
# The sheet, the wrap, and one frame.
def wrap(text, columns):
    """pp_font_wrap: greedy by word, and a word longer than a row is split."""
    words = [word for word in text.split(" ") if word != ""]
    rows = []
    row = ""
    for word in words:
        if len(word) > columns:
            if row:
                rows.append(row)
                row = ""
            position = 0
            while position < len(word):
                rows.append(word[position:position + columns])
                position += columns
            row = rows.pop()
            continue
        if not row:
            row = word
        elif len(row) + 1 + len(word) <= columns:
            row = row + " " + word
        else:
            rows.append(row)
            row = word
    if row:
        rows.append(row)
    return rows or [""]


class Frame:
    """A 256x240 canvas, the sheet, and a record of every string drawn and where its ink landed."""

    def __init__(self, config, roles, sheet, glyphs):
        self.width = config["PP_FRAME_W"]
        self.height = config["PP_FRAME_H"]
        self.roles = roles
        self.sheet = sheet
        self.glyphs = glyphs
        self.image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255))
        self.drawn = []
        self.missing = []

    def fill(self, role, x0, y0, x1, y1, outline=False):
        colour = self.roles[role]
        if outline:
            for x in range(int(x0), int(x1) + 1):
                self.image.putpixel((x, int(y0)), _rgba(colour))
                self.image.putpixel((x, int(y1)), _rgba(colour))
            for y in range(int(y0), int(y1) + 1):
                self.image.putpixel((int(x0), y), _rgba(colour))
                self.image.putpixel((int(x1), y), _rgba(colour))
            return
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.image.putpixel((x, y), _rgba(colour))

    def text(self, content, x, y, region, owner, columns=None, line_h=CELL, centre=None, strike=False,
             cursor=False):
        """One pp_font_draw (or a wrapped block of them), plus the rule a struck or cursored row carries."""
        rows = wrap(content, columns) if columns else [content]
        boxes = []
        for index, row in enumerate(rows):
            row_y = y + index * line_h
            start = centre - (len(row) * CELL) // 2 if centre is not None else x
            ink = self.paste(row, start, row_y)
            if ink[0] is not None:
                boxes.append((ink[0], ink[1], start + len(row) * CELL - 1, row_y + CELL - 1))
            self.drawn.append({"text": row, "owner": owner, "x": start, "y": row_y,
                               "x1": start + len(row) * CELL - 1, "y1": row_y + CELL - 1,
                               "region": region})
        if strike and boxes:
            x0, y0, x1, _y1 = boxes[0]
            self.fill("dim", x0, y0 + 4, x1, y0 + 4)
        if cursor and boxes:
            x0, y0, x1, _y1 = boxes[0]
            self.fill("text", x0, y0 + 9, x1, y0 + 10)
        return len(rows)

    def paste(self, content, x, y):
        """pp_font_draw: one 8x8 frame per character, in the sheet's own ink, a missing character left as a space."""
        cursor = x
        ink = [None, None, None, None]
        for char in content:
            if char not in self.glyphs:
                self.missing.append(char)
                cursor += CELL
                continue
            frame = self.glyphs.index(char)
            tile = self.sheet.crop((frame * CELL, 0, frame * CELL + CELL, CELL))
            self.image.paste(tile, (cursor, y), tile)
            if char != " " and 0 <= cursor < self.width and 0 <= y < self.height:
                if ink[0] is None or cursor < ink[0]:
                    ink[0] = cursor
                if ink[2] is None or cursor > ink[2]:
                    ink[2] = cursor
                if ink[1] is None or y < ink[1]:
                    ink[1] = y
                if ink[3] is None or y > ink[3]:
                    ink[3] = y
            cursor += CELL
        return ink[0], ink[1], ink[2], ink[3]


def _rgba(hex_colour):
    return (int(hex_colour[1:3], 16), int(hex_colour[3:5], 16), int(hex_colour[5:7], 16), 255)


def ink_bounds(image, box=None):
    """(x0, y0, x1, y1) of every pixel that is not the frame's black, or None."""
    x0, y0, x1, y1 = box if box else (0, 0, image.size[0] - 1, image.size[1] - 1)
    pixels = image.convert("RGB").load()
    out = None
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if pixels[x, y] != (0, 0, 0):
                if out is None:
                    out = [x, y, x, y]
                else:
                    out[0] = min(out[0], x)
                    out[1] = min(out[1], y)
                    out[2] = max(out[2], x)
                    out[3] = max(out[3], y)
    return None if out is None else tuple(out)


# ---------------------------------------------------------------------------------------------------------------
# Frame one: the battle menu, drawn as pp_battle_draw and pp_battle_draw_menu draw it.
def battle_frame(config, roles, sheet, glyphs, labels, enemy, party, message, cursor, note):
    frame = Frame(config, roles, sheet, glyphs)
    menu_top = config["PP_MENU_TOP"]

    # pp_battle_draw: the field is the paper role, then the two bodies, then the bars.
    frame.fill("paper", 0, 0, frame.width - 1, frame.height - 1)
    frame.fill("ink", 40, 96, 72, 144)
    frame.fill("text", 176, 72, 224, 136)
    frame.text(enemy["name"], 0, 56, (128, 48, frame.width - 1, 71), "the enemy's name over its block", centre=200)

    enemy_frac = 1.0
    frame.fill("dim", 168, 144, 232, 148)
    frame.fill("text", 168, 144, 168 + int(64 * enemy_frac), 148)

    # The HP line as pp_battle_draw joins it since card t_f476435e: a slash, because the sheet now carries one.
    hp_line = "HP %d/%d   WILL %d/%d" % (party["max_hp"], party["max_hp"], party["will_max"],
                                         party["will_max"])
    frame.text(hp_line, 16, 156, (0, 152, frame.width - 1, 167), "the player's HP and WILL line")

    # The message window: pp_battle_text_box_* is the top 48 px of the frame, filled and bordered.
    frame.fill("paper", 0, 0, frame.width - 1, 47)
    frame.fill("dim", 0, 0, frame.width - 1, 47, outline=True)
    columns = _cols(frame.width - 32)
    frame.text(message, 16, 16, (16, 8, 16 + columns * CELL - 1, 47), "the message window's line", columns=columns,
               line_h=10)

    # pp_battle_draw_menu: the band, its border, the five labels, the cursor arrow and the refusal note.
    frame.fill("paper", 8, menu_top, frame.width - 8, frame.height - 8)
    frame.fill("dim", 8, menu_top, frame.width - 8, frame.height - 8, outline=True)
    for index, label in enumerate(labels):
        x = 24 + (index % 2) * 104
        y = menu_top + 8 + (index // 2) * 20
        frame.text(label, x, y, (8, menu_top, frame.width - 9, menu_top + 8 + 2 * 20 + CELL - 1),
                   "a command label", strike=(index == 3))
        if index == cursor:
            frame.fill("text", x - 6, y, x - 1, y + 4)
    frame.text(note, 16, frame.height - 16, (16, frame.height - 16, 16 + columns * CELL - 1, frame.height - 1),
               "the refusal note", columns=columns)
    return frame


# ---------------------------------------------------------------------------------------------------------------
# Frame two: the game over card, drawn as pp_battle_draw_gameover draws it after the fade.
def gameover_frame(config, roles, sheet, glyphs, enemy, rows, note, cursor):
    frame = Frame(config, roles, sheet, glyphs)
    frame.fill("ink", 0, 0, frame.width - 1, frame.height - 1)
    frame.fill("dim", 63, 63, 193, 177)
    frame.fill("paper", 64, 64, 192, 176)
    frame.fill("ink", 66, 66, 190, 174)
    inner = (66, 66, 190, 174)
    card_columns = _cols(124)

    frame.text("GAME OVER", 0, 78, inner, "the card's title", centre=frame.width // 2)
    frame.fill("dim", 96, 94, 160, 96)
    frame.text(enemy["name"] + " stands over you.", 0, 102, (66, 98, 190, 128), "the enemy sentence",
               columns=card_columns, centre=frame.width // 2)

    for index, label in enumerate(rows):
        y = 132 + index * 16
        enabled = index != 0
        frame.text(label, 0, y, (66, 130 + index * 16, 190, 130 + index * 16 + CELL + 3), "a game over row",
                   centre=frame.width // 2, strike=not enabled, cursor=(index == cursor))
    frame.text(note, 0, 182, (8, 182, frame.width - 9, 182 + CELL - 1), "the sentence under the card",
               columns=_cols(frame.width - 16), centre=frame.width // 2)
    return frame


def _cols(pixels):
    return max(1, pixels // CELL)


# ---------------------------------------------------------------------------------------------------------------
# The verdict.
def check(frame, config):
    errors = []
    if frame.missing:
        errors.append("the sheet has no frame for %s, so pp_font_draw would print a space there"
                      % ", ".join(sorted(set(frame.missing))))
    for row in frame.drawn:
        x0, y0, x1, y1 = row["region"]
        if row["x"] < x0 or row["x1"] > x1 or row["y"] < y0 or row["y1"] > y1:
            errors.append("%r (%s) reaches x %d..%d y %d..%d, its region is x %d..%d y %d..%d"
                          % (row["text"], row["owner"], row["x"], row["x1"], row["y"], row["y1"],
                             x0, x1, y0, y1))
    bounds = ink_bounds(frame.image)
    if bounds is None:
        errors.append("the frame is empty")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    parser.add_argument("--enemy", default="navy_sailor", help="the enemy whose name the frames print")
    parser.add_argument("--encounter", default="tutorial_sailors", help="the encounter whose first line prints")
    parser.add_argument("--out", default=DEFAULT_OUT, help="where the 3x image goes")
    parser.add_argument("--quiet", action="store_true", help="one line of output")
    args = parser.parse_args()
    root = os.path.abspath(args.root)

    try:
        config = read_macros(root)
        glyphs = read_glyphs(root)
        roles = read_roles(root)
        labels = read_commands(root)
        rows, notes = read_director(root)
        party, enemy = read_party_and_enemy(root, args.enemy)
        message = read_message(root, args.encounter)
    except FileNotFoundError as exc:
        print("preview_battle_font: %s" % exc)
        return 2

    for need in ("PP_FRAME_W", "PP_FRAME_H", "PP_MENU_TOP"):
        if need not in config:
            print("preview_battle_font: %s has no literal #macro %s" % (CONFIG_GML, need))
            return 2

    with Image.open(os.path.join(root, FONT_PNG)) as img:
        sheet = img.convert("RGBA")
    inks = set()
    for y in range(sheet.size[1]):
        for x in range(sheet.size[0]):
            pixel = sheet.getpixel((x, y))
            if pixel[3] != 0:
                inks.add("#%02x%02x%02x" % (pixel[0], pixel[1], pixel[2]))
    sheet_inks = sorted(inks)
    if len(sheet_inks) != 1:
        print("preview_battle_font: %s spends %d colours, the sheet is one ink (rule 6): %s"
              % (FONT_PNG, len(sheet_inks), ", ".join(sheet_inks)))
        return 1

    # The refusal note is a real one from the director, and the game over note is the longest the card can be given,
    # so the preview measures the case that is hardest to fit rather than an easy one.
    refusal = "no power taken yet"
    if not notes:
        print("preview_battle_font: %s names no game over sentence to draw" % DIRECTOR_GML)
        return 2
    note = max(notes, key=len)

    frames = [
        ("battle menu", battle_frame(config, roles, sheet, glyphs, labels, enemy, party, message, 1, refusal)),
        ("game over", gameover_frame(config, roles, sheet, glyphs, enemy, rows, note, 1)),
    ]

    errors = []
    for name, frame in frames:
        for error in check(frame, config):
            errors.append("%s: %s" % (name, error))

    gap = 8
    composed = Image.new("RGB", (config["PP_FRAME_W"] * SCALE,
                                 (config["PP_FRAME_H"] * SCALE + gap) * len(frames) - gap), (0, 0, 0))
    for index, (_name, frame) in enumerate(frames):
        big = frame.image.convert("RGB").resize((config["PP_FRAME_W"] * SCALE, config["PP_FRAME_H"] * SCALE),
                                                Image.NEAREST)
        composed.paste(big, (0, index * (config["PP_FRAME_H"] * SCALE + gap)))
    out_path = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    composed.save(out_path)

    if args.quiet:
        print("battle font: %d frame(s), %d string(s), %d error(s), %s"
              % (len(frames), sum(len(frame.drawn) for _n, frame in frames), len(errors), out_path))
        return 1 if errors else 0

    print("battle and game over frames, composed through their own draw path at %dx" % SCALE)
    print("  font: %d glyphs, one %d px cell, sheet ink %s (the role fill behind it is not a tint)"
          % (len(glyphs), CELL, sheet_inks[0]))
    print("  the message window wraps at %d columns (%d px) and the game over card at %d (%d px)"
          % (_cols(config["PP_FRAME_W"] - 32), config["PP_FRAME_W"] - 32, _cols(124), 124))
    for name, frame in frames:
        print("")
        print("  %s" % name)
        for row in frame.drawn:
            print("    %-32r x %3d..%3d y %3d..%3d  %s"
                  % (row["text"], row["x"], row["x1"], row["y"], row["y1"], row["owner"]))
        bounds = ink_bounds(frame.image)
        print("    ink on the whole frame: x %d..%d y %d..%d"
              % (bounds[0], bounds[2], bounds[1], bounds[3]))
    print("")
    print("  image: %s" % out_path)
    if errors:
        print("")
        for error in errors:
            print("  FAIL %s" % error)
        print("")
        print("preview_battle_font: REFUSED, %d fault(s)" % len(errors))
        return 1
    print("preview_battle_font: PASS, every string is in the sheet and inside the region its owner gave it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
