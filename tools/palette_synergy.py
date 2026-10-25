#!/usr/bin/env python3
"""palette_synergy.py: does this sprite read on the ground it stands on, and does either layer fit its set?

Why this exists
---------------
ART-BIBLE.md RULE 0 (Nayil, 2026-10-22): a character sprite palette must separate from the background behind
it. Until now nothing measured that. The background could pass the 16x16 area rule and the sprite could pass
the 8x8 tile rule, and the frame still looked wrong, because the two layers were never compared with each
other. This tool is that comparison.

What it measures, for one scene id, one background PNG and one sprite PNG (or a folder of them):

  R1 body_ground     the sprite's body colour and the background colour behind it do not separate. Two
                     instruments, EITHER one clears the rule: at least 2 brightness rows apart on the 2C02
                     grid (rows 0 to 3), OR at least 3:1 WCAG contrast between the two luminances. FAIL only
                     when both are short. Gamedev ruling, card t_50193088, 2026-10-24, knowledge/ART-BIBLE.md
                     RULE 0 point 2 carries the words.
                     Reason, measured: the row is a coarse band, not a luminance. $10 on $0F is 1 row apart at
                     11.06:1 and $10 on $30 is 2 rows apart at 1.85:1, so on the pairs that matter the row
                     arithmetic ranks them backwards. The 3:1 floor is the same WCAG large text floor R1b
                     already uses, so there is one number for "these can be told apart" in the file.
  R2 same_hue_row    body and ground are the same hue family AND the same row. FAIL.
  R1b overlay_contrast  a TILED LAYER (a sheet whose sidecar declares "layer": true, or whose frame is
                     bigger than a 32x32 battle figure: the wordmark, the car, a window strip) has no feet
                     and no ground it stands on, so R1, R2 and R3 are not asked of it. What is asked instead
                     is that it reads against the pixels it is drawn over: the frame's ink or its body must
                     clear 3:1 contrast (the WCAG large text floor) on every ground colour under it.
                     Gamedev ruling, card t_1c04d011, 2026-10-23, and knowledge/ART-BIBLE.md RULE 0 point 2
                     carries the same words.
                     Reason, measured: the wordmark's ink $0F and its stone body $00 are both 2C02 row 0 while
                     their luminances are 0.000 and 0.202, so the row arithmetic cannot see the difference that
                     makes the letters read; a white body would satisfy the rows and break spec 14's stone.
                     Which sheets are layers is a DECLARATION, not a width: a battle figure up to 32x32 is a
                     figure (knowledge/PALETTE-RULINGS-2026-10-24.md section 7, card t_c498add9).
  R3 white_blob      a near white body (luminance 0.60 or more) on a light ground (0.25 or more). FAIL.
  R4 sprite_tile     more than 3 opaque colours in one 8x8 sprite tile. FAIL. Measured by
                     tools\\nes_check.py check_sprite_tiles(), so the rule lives in one place. The
                     whole-frame restatement of it ("this frame carries 5 colours") is asked only of a frame
                     16x16 and under, because a 24x32 figure is twelve 8x8 tiles under more than one palette
                     by design and the frame-level test would refuse every battle sheet in the project.
  R5 background_area more than 3 colours besides the backdrop in one 16x16 background area. FAIL. Measured by
                     tools\\nes_check.py check_background_areas().
  R6 palette_count   the frame needs more than 4 background palettes, or a sprite frame needs a palette that
                     is not one of the 4. FAIL. For a MULTI-TILE FIGURE (a figure frame bigger than 16x16)
                     R6 is asked per 8x8 tile instead: every tile's opaque colour set has to be a subset of
                     at least one sprite palette of the scene, one FAIL per uncovered tile with the tile's
                     position and its colour set. A frame 16x16 and under keeps the whole-frame reading.
  R7 set_member      a drawn colour that is not in the scene's palette set at all, so no palette can carry it.
                     FAIL, and this is the "not colour coordinated" failure that started RULE 0.

Contrast and luminance arithmetic is NOT restated here: tools\\art\\contrast_check.py owns the WCAG ratio and
the 2C02 luminance table (card CONTRAST-TOOL), and this file imports them. The luminance ROW and the HUE
FAMILY come from the entry number through tools\\scene_palette_set.py, which is where that grid is written down.
The background area and sprite tile rules come from tools\\nes_check.py. Nothing is duplicated.

Ground: the pixels of the background image under the sprite's frame, at the frame's placement. Placement is
either --at X,Y or automatic: horizontally centred, feet on the bottom band of the frame. A room that carries
an attribute map (data\\palettes\\scene_<id>.json with an areas list) may name --at from it later; today the
pixels under the bounding box are the ground, which is the reading the card allows.

Pair a frame with a sprite from ITS OWN cast. This tool measures two things at once (does the frame spend the
scene's set, and does this figure separate from this ground), so a sprite from another scene's palette set fails
set_member on every frame and says nothing about the frame. That happened on 2026-10-22: the R8 concept round put
a battle cast sprite on the title frame, got 32 fails on 8 frames, and read it as "the title frame is not palette
correct" when the title frame passes the background rules 0 times and the pairing was wrong (card t_4bafb4a1,
knowledge\\PALETTE-GATE-DECISIONS-2026-10-22.md). If a sprite fails set_member on every single frame, suspect the pairing
before the art.

Usage:
    python tools\\palette_synergy.py --scene title --background output\\nes_title_frame.png \\
        --sprite game\\sprites_src\\chars\\percy_ow_v2.png
    python tools\\palette_synergy.py --scene ship --background output\\bg_battle_deck_night_frame.png \\
        --sprite game\\sprites_src\\chars
    python tools\\palette_synergy.py --gate              every entry in data\\scene_palettes.json "audit"
    python tools\\palette_synergy.py --selftest

Exit code 0 when every rule passes, 1 when any rule fails. --gate counts only entries whose scene sets
"gate": true, and prints the rest as advisory (the same gated/advisory split tools\\nes_audit_all.py uses, so a
known unfixed scene reports without blocking the build).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter

from PIL import Image

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)
sys.path.insert(0, os.path.join(TOOLS_DIR, "art"))

import contrast_check  # noqa: E402  (WCAG contrast, luminance table, frame geometry: reused, not rewritten)
import nes_check  # noqa: E402       (sprite tile rule, background area rule: reused, not rewritten)
import scene_palette_set  # noqa: E402  (the scene set, the 2C02 grid, hero palettes)

FRAME_W, FRAME_H = 256, 240
TILE = 8
AREA = 16
MAX_SPRITE_COLOURS = 3
MAX_AREA_COLOURS = 3
MAX_BG_PALETTES = 4
ROW_GAP_MIN = 2
NEAR_WHITE = 0.60
LIGHT_GROUND = 0.25
DIAGONAL = 2
# A battle figure is up to 32x32: the five 24x32 party battle sheets and the 32x32 enemy sheets. A sheet whose
# frame is bigger than that is a tiled layer (the wordmark, the car, a window strip), and so is any sheet that
# says so itself in its sidecar with "layer": true. The old line was 16 px wide, which made every battle figure
# in the project a layer and skipped R1, R2, R3 and R6 on all of them (PALETTE-RULINGS-2026-10-24.md section 7).
SPRITE_FIGURE_W = 32
SPRITE_FIGURE_H = 32
# R6 and the whole-frame 3 colour test are asked of one object per frame up to this size. Above it the frame is a
# multi-tile figure and R6 is asked per 8x8 tile, because a 24x32 figure spends more than one palette by design.
WHOLE_FRAME_W = 16
WHOLE_FRAME_H = 16
# WCAG large text contrast, already implemented in contrast_check.contrast(). An overlay has no feet, so this
# is the floor it has to read on: its ink or its body, whichever carries the edge.
OVERLAY_CONTRAST_MIN = 3.0
# R1's second instrument. A row is a coarse band, not a luminance: measured on the 2C02 table, body $10 is
# 1 row from the ground $0F at 11.06:1, and 2 rows from $30 at 1.85:1. So a figure standing on a flat backdrop
# is separated when EITHER the row gap is 2 or the pair clears this floor, and refused only when both are short.
# The number is deliberately the same one R1b uses: one floor in this file for "these can be told apart".
FIGURE_GROUND_CONTRAST_MIN = OVERLAY_CONTRAST_MIN


# -----------------------------------------------------------------------------------------------------------------
# Loading.

def repo_root() -> str:
    return ROOT


def shown(root: str, path: str) -> str:
    """The path as the report prints it: relative to the repo when it can be, absolute when it is on another
    drive (a test writes its PNGs into the system temp folder, which is on C: here and the repo is on D:)."""
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return os.path.abspath(path).replace(os.sep, "/")


def resolve(root: str, path: str) -> str:
    if not path:
        return path
    return path if os.path.isabs(path) else os.path.join(root, path)


def load_background(root: str, path: str) -> Image.Image:
    full = resolve(root, path)
    if not os.path.isfile(full):
        raise SystemExit("palette_synergy: background %s does not exist" % path)
    image = nes_check.load_image(full).convert("RGBA")
    if (image.width, image.height) != (FRAME_W, FRAME_H):
        if image.width % FRAME_W == 0 and image.height % FRAME_H == 0:
            image = image.resize((FRAME_W, FRAME_H), Image.NEAREST)
        else:
            crop = image.crop((0, 0, min(FRAME_W, image.width), min(FRAME_H, image.height)))
            crop.load()
            image = crop
    return image


def sprite_paths(root: str, target: str) -> list:
    full = resolve(root, target)
    if os.path.isdir(full):
        return sorted(glob.glob(os.path.join(full, "*.png")))
    if os.path.isfile(full):
        return [full]
    raise SystemExit("palette_synergy: sprite %s does not exist" % target)


# -----------------------------------------------------------------------------------------------------------------
# The 2C02 readings this file needs, all through the shared definitions.

class Grid:
    """Entry to (row, hue family, luminance). Luminance comes from the table contrast_check.py already owns."""

    def __init__(self, root: str):
        self.colours, self.usable, self.index_of = scene_palette_set.load_master(root)
        self.contrast = contrast_check.load_palette(root)
        self.luminance = {}
        for entry, rgb in enumerate(self.colours):
            self.luminance[entry] = contrast_check.luminance(rgb)

    def entry(self, rgb):
        return self.index_of.get(tuple(rgb))

    def row(self, entry: int) -> int:
        return scene_palette_set.row_of(entry)

    def hue(self, entry: int) -> str:
        return scene_palette_set.hue_family(entry)

    def luma(self, entry: int) -> float:
        return self.luminance[entry]

    def code(self, entry: int) -> str:
        return scene_palette_set.codename(entry)


# -----------------------------------------------------------------------------------------------------------------
# Sprite frames.

def frame_size(root: str, path: str, image: Image.Image, frame_w, frame_h) -> tuple:
    """(frame width, frame height, how, the sheet's own layer declaration) from contrast_check.py geometry(), so
    a sheet is split the project's way: the frame size the sheet declares in its own sidecar, not a size guessed
    from the image."""
    info = contrast_check.geometry(root, path, image, frame_w, frame_h)
    return (int(info["frame_w"]), int(info["frame_h"]), info.get("how", ""),
            bool(info.get("declared_layer", False)))


def frames(image: Image.Image, frame_w: int, frame_h: int) -> list:
    """Every frame box, left to right, top to bottom. A frame with no opaque pixel is skipped by the caller."""
    out = []
    for y in range(0, image.height - frame_h + 1, frame_h):
        for x in range(0, image.width - frame_w + 1, frame_w):
            out.append((x, y, x + frame_w, y + frame_h))
    return out


def frame_pixels(image: Image.Image, box) -> Counter:
    counts = Counter()
    pixels = image.load()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            r, g, b, a = pixels[x, y]
            if a:
                counts[(r, g, b)] += 1
    return counts


def placement(box, frame_w: int, frame_h: int, at) -> tuple:
    """Where the frame sits on the background: --at, else centred with the feet on the bottom band."""
    if at:
        return int(at[0]), int(at[1])
    left = (FRAME_W - frame_w) // 2
    top = FRAME_H - frame_h - DIAGONAL * TILE
    return max(0, left), max(0, top)


def ground_pixels(background: Image.Image, x0: int, y0: int, frame_w: int, frame_h: int) -> Counter:
    counts = Counter()
    pixels = background.load()
    for y in range(y0, min(y0 + frame_h, background.height)):
        for x in range(x0, min(x0 + frame_w, background.width)):
            r, g, b, a = pixels[x, y]
            if a:
                counts[(r, g, b)] += 1
    return counts


# -----------------------------------------------------------------------------------------------------------------
# The rules.

def fail(rule: str, detail: str, **extra) -> dict:
    record = {"rule": rule, "detail": detail}
    record.update(extra)
    return record


def pair_rules(grid: Grid, scene, body: int, ground: int, where: str) -> list:
    """R1, R2 and R3 for one body colour on one ground colour."""
    problems = []
    body_luma, ground_luma = grid.luma(body), grid.luma(ground)
    if body_luma >= NEAR_WHITE and ground_luma >= LIGHT_GROUND:
        problems.append(fail("white_blob",
                             "%s: body %s at luminance %.2f on ground %s at %.2f, the white blob RULE 0 point 2 "
                             "refuses" % (where, grid.code(body), body_luma, grid.code(ground), ground_luma),
                             body=grid.code(body), ground=grid.code(ground)))
    if body == ground:
        problems.append(fail("invisible", "%s: body %s is the ground colour, the figure has no edge there"
                             % (where, grid.code(body)), body=grid.code(body), ground=grid.code(ground)))
        return problems
    gap = abs(grid.row(body) - grid.row(ground))
    separation = contrast_check.contrast(body_luma, ground_luma)
    if gap < ROW_GAP_MIN and separation < FIGURE_GROUND_CONTRAST_MIN:
        problems.append(fail("body_ground",
                             "%s: body %s (row %d) and ground %s (row %d) are %d luminance row(s) apart at "
                             "%.2f:1, and RULE 0 point 2 wants %d rows or %.1f:1"
                             % (where, grid.code(body), grid.row(body), grid.code(ground), grid.row(ground),
                                gap, separation, ROW_GAP_MIN, FIGURE_GROUND_CONTRAST_MIN),
                             body=grid.code(body), ground=grid.code(ground), rows=gap,
                             contrast=round(separation, 2)))
    if grid.hue(body) == grid.hue(ground) and grid.row(body) == grid.row(ground):
        problems.append(fail("same_hue_row",
                             "%s: body %s and ground %s are both %s on row %d"
                             % (where, grid.code(body), grid.code(ground), grid.hue(body), grid.row(body)),
                             body=grid.code(body), ground=grid.code(ground)))
    return problems


def is_sprite_frame(frame_w: int, frame_h: int, declared_layer: bool = False) -> bool:
    """True for one sprite figure, false for a tiled layer (the wordmark, the car, a window strip).

    A sheet is a tiled layer when it DECLARES itself one (\"layer\": true in its sidecar, read through
    contrast_check.geometry()) or when its frame is bigger than a battle figure. It is not a layer because it is
    17 px wide: every battle figure in this project is 24x32 or 32x32, and the old 16 px line skipped R1, R2, R3
    and R6 on all of them while set_member alone decided (PALETTE-RULINGS-2026-10-24.md section 7).
    """
    if declared_layer:
        return False
    return frame_w <= SPRITE_FIGURE_W and frame_h <= SPRITE_FIGURE_H


def is_whole_frame(figure: bool, frame_w: int, frame_h: int) -> bool:
    """True when R6 and the frame-level 3 colour restatement are asked of the whole frame.

    That is one object of 16x16 and under. A bigger figure is a multi-tile figure, and its R6 is per 8x8 tile.
    """
    return figure and frame_w <= WHOLE_FRAME_W and frame_h <= WHOLE_FRAME_H


def tile_fails(grid: Grid, scene, image: Image.Image, box, where: str) -> tuple:
    """R6 per 8x8 tile: (fails, tiles inked, tiles uncovered) for one figure frame.

    A multi-tile figure spends more than one palette by design, so the question is not whether ONE palette carries
    the whole frame but whether every 8x8 tile has a palette that carries it. One fail per uncovered tile, naming
    the tile's position in the sheet and the colour set it needs.
    """
    problems = []
    inked = 0
    uncovered = 0
    pixels = image.load()
    for top in range(box[1], box[3], TILE):
        for left in range(box[0], box[2], TILE):
            needs = set()
            for y in range(top, min(top + TILE, box[3])):
                for x in range(left, min(left + TILE, box[2])):
                    r, g, b, a = pixels[x, y]
                    if a:
                        entry = grid.entry((r, g, b))
                        needs.add(entry if entry is not None else -1)
            if not needs:
                continue
            inked += 1
            if any(needs <= allowed for allowed in scene.sprite_sets()):
                continue
            uncovered += 1
            named = " ".join(grid.code(entry) if entry >= 0 else "off-palette" for entry in sorted(needs))
            problems.append(fail("palette_count",
                                 "%s: 8x8 tile at %d,%d needs %s, which none of the scene's four sprite palettes "
                                 "carries, so the drawing has to change or the set does"
                                 % (where, left, top, named),
                                 tile=[left, top], colours=named, subject="cast"))
    return problems, inked, uncovered


def layer_rules(grid: Grid, body: int, ink, ground: int, where: str) -> list:
    """R1b: a tiled layer reads if its ink or its body clears the 3:1 floor on the ground under it.

    The layer has no feet, so the RULE 0 point 2 row gap is not asked of it (gamedev ruling, card t_1c04d011).
    The question that replaces it is the one the rule exists for: can the pixels under the layer be told apart
    from the layer. Ink is the frame's darkest colour, the outline the layer is drawn with. A body that IS the
    ground colour comes out here as a 1.00:1 pair, which is R3's invisible case in the reading that fits a layer.
    """
    problems = []
    body_contrast = contrast_check.contrast(grid.luma(body), grid.luma(ground))
    ink_contrast = contrast_check.contrast(grid.luma(ink), grid.luma(ground)) if ink is not None else 0.0
    best = max(body_contrast, ink_contrast)
    if best < OVERLAY_CONTRAST_MIN:
        problems.append(fail("overlay_contrast",
                             "%s: tiled layer body %s reads %.2f:1 and its ink %s reads %.2f:1 on ground %s, "
                             "and a layer has to clear %.1f:1 with one of them"
                             % (where, grid.code(body), body_contrast,
                                grid.code(ink) if ink is not None else "none", ink_contrast,
                                grid.code(ground), OVERLAY_CONTRAST_MIN),
                             body=grid.code(body), ground=grid.code(ground),
                             body_contrast=round(body_contrast, 2), ink_contrast=round(ink_contrast, 2)))
    return problems



def frame_report(grid: Grid, scene, image: Image.Image, box, background: Image.Image, at,
                 declared_layer: bool = False) -> dict:
    counts = frame_pixels(image, box)
    frame_w, frame_h = box[2] - box[0], box[3] - box[1]
    if not counts:
        return {"box": list(box), "drawn": 0, "skipped": "no opaque pixel"}
    colours = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    # The body is the largest fill, not the outline: a sprite's most common colour is usually its dark
    # outline, and judging the outline as the body would report every correct figure as invisible on black.
    outline_rgb = min((rgb for rgb, _ in colours), key=lambda rgb: grid.luma(grid.entry(rgb))
                      if grid.entry(rgb) is not None else 0.0)
    fills = [(rgb, count) for rgb, count in colours if rgb != outline_rgb]
    body_rgb = (fills or colours)[0][0]
    body = grid.entry(body_rgb)
    if body is None:
        body = scene.nearest_master(body_rgb)
    entries = []
    for rgb, count in colours:
        entry = grid.entry(rgb)
        entries.append({"hex": "#%02x%02x%02x" % rgb, "entry": grid.code(entry) if entry is not None else None,
                        "on_master": entry is not None, "pixels": count})

    # R7: every drawn colour has to live inside one of the scene's sprite palettes.
    ink = grid.entry(outline_rgb)
    figure = is_sprite_frame(frame_w, frame_h, declared_layer)
    layer = not figure
    whole = is_whole_frame(figure, frame_w, frame_h)

    def verdict(candidate: int, ground_entry: int, where: str) -> list:
        """R1 and R2 for a figure, R1b for a tiled layer: the sheet's own declaration decides which."""
        if layer:
            return layer_rules(grid, candidate, ink, ground_entry, where)
        return pair_rules(grid, scene, candidate, ground_entry, where)

    problems = []
    off_set = [item for item in entries if item["entry"] is None or
               int(item["entry"][1:], 16) not in scene.sprite_colours()]
    for item in off_set:
        problems.append(fail("set_member",
                             "sprite colour %s (%s) is not in any of the scene's 4 sprite palettes"
                             % (item["hex"], item["entry"] or "off the 2C02 palette"),
                             colour=item["hex"], subject="cast"))
    if len(entries) > MAX_SPRITE_COLOURS and whole:
        # The 3 colour limit is a sprite limit: a tile drawn for one object. A strip that is really a tiled
        # background layer (the title car, the logo) is judged per 8x8 tile by nes_check below instead, because
        # no single palette could ever carry a 96 pixel wide layer and the rule was never about that. A 24x32 or
        # 32x32 figure is twelve or sixteen 8x8 tiles under more than one palette by design, so the frame-level
        # restatement is asked only of a frame 16x16 and under, and the per-tile rule below is the one that holds
        # a multi-tile figure.
        problems.append(fail("sprite_tile",
                             "the frame carries %d opaque colours; a sprite palette has %d plus transparency "
                             "for the whole frame" % (len(entries), MAX_SPRITE_COLOURS),
                             colours=len(entries)))

    # R6: which of the 4 sprite palettes can carry this frame.
    fits = [index for index, allowed in enumerate(scene.sprite_sets())
            if all(item["entry"] and int(item["entry"][1:], 16) in allowed for item in entries)]
    tiles = None
    if whole and not fits:
        problems.append(fail("palette_count",
                             "none of the scene's four sprite palettes carries this frame's colours, so the "
                             "drawing has to change or the set does", subject="cast"))
    elif figure:
        # A multi-tile figure: R6 per 8x8 tile, one fail per uncovered tile.
        found, tiles_inked, tiles_uncovered = tile_fails(
            grid, scene, image, box, "the figure at %d,%d" % (box[0], box[1]))
        problems.extend(found)
        tiles = {"inked": tiles_inked, "uncovered": tiles_uncovered}
    problems.extend(nes_check.check_sprite_tiles(image.crop(box)))

    # Ground and R1 to R3 against every background colour under the frame.
    left, top = placement(box, frame_w, frame_h, at)
    ground = ground_pixels(background, left, top, frame_w, frame_h)
    ground_colours = sorted(ground.items(), key=lambda item: (-item[1], item[0]))
    pairs = []
    for rgb, count in ground_colours:
        entry = grid.entry(rgb)
        if entry is None:
            problems.append(fail("set_member",
                                 "background colour #%02x%02x%02x under the sprite is off the 2C02 palette" % rgb))
            continue
        if entry not in scene.bg_colours() and entry != scene.backdrop:
            problems.append(fail("set_member",
                                 "background colour %s under the sprite is not in any of the scene's 4 background "
                                 "palettes" % grid.code(entry), colour=grid.code(entry), subject="ground"))
        for index, palette in enumerate(scene.sprites):
            candidate = int(palette[1])
            where = "sprite palette %d body vs ground at %d,%d" % (index, left, top)
            found = verdict(candidate, entry, where)
            pairs.append({
                "sprite_palette": index,
                "body": grid.code(candidate),
                "body_row": grid.row(candidate),
                "body_hue": grid.hue(candidate),
                "ground": grid.code(entry),
                "ground_row": grid.row(entry),
                "ground_hue": grid.hue(entry),
                "ground_pixels": count,
                "rows_apart": abs(grid.row(candidate) - grid.row(entry)),
                "contrast": round(contrast_check.contrast(grid.luma(candidate), grid.luma(entry)), 2),
                "ink_contrast": round(contrast_check.contrast(grid.luma(ink), grid.luma(entry)), 2)
                if ink is not None else None,
                "ok": not found,
                "fails": [item["rule"] for item in found],
            })
        # The frame's own body colour, which is what actually ships, is judged the same way.
        found = verdict(body, entry, "the frame's body vs ground at %d,%d" % (left, top))
        problems.extend(found)
    return {"box": list(box), "at": [left, top], "drawn": sum(counts.values()),
            "colours": entries, "body": grid.code(body), "body_row": grid.row(body),
            "body_hue": grid.hue(body), "body_luminance": round(grid.luma(body), 3),
            "layer": layer, "ink": grid.code(ink) if ink is not None else None,
            "tiles": tiles, "palettes_that_fit": fits, "pairs": pairs, "problems": problems}


def background_report(grid: Grid, scene, background: Image.Image) -> list:
    """R5 and R6 on the background: 3 colours per 16x16 area, and at most 4 palettes for the frame."""
    problems = []
    problems.extend(nes_check.check_background_areas(background, scene.rgb(scene.backdrop)))
    used = {}
    for (ax, ay), seen in sorted(nes_check.area_colours(background).items()):
        seen = seen - {scene.rgb(scene.backdrop)}
        entries = {grid.entry(rgb) for rgb in seen}
        if None in entries:
            off = ["#%02x%02x%02x" % rgb for rgb in seen if grid.entry(rgb) is None]
            problems.append(fail("set_member",
                                 "background area %d,%d carries %s, off the 2C02 palette" % (ax, ay, ", ".join(off))))
            entries.discard(None)
        fits = [index for index, allowed in enumerate(scene.bg_sets()) if entries <= allowed]
        if not fits:
            problems.append(fail("palette_count",
                                 "background area %d,%d needs colours %s, which no single background palette "
                                 "carries, so the frame needs a fifth background palette"
                                 % (ax, ay, " ".join(sorted(grid.code(entry) for entry in entries))),
                                 area=[ax, ay]))
        for index in fits[:1]:
            used[index] = used.get(index, 0) + 1
    if len(used) > MAX_BG_PALETTES:
        problems.append(fail("palette_count", "the frame uses %d background palettes, the PPU has %d"
                             % (len(used), MAX_BG_PALETTES)))
    return problems


# -----------------------------------------------------------------------------------------------------------------
# One run.

def analyse(root: str, scene_id: str, background_path: str, sprite_targets, at=None,
            frame_w=None, frame_h=None) -> dict:
    grid = Grid(root)
    data = scene_palette_set.load(root)
    scene = scene_palette_set.scene(root, scene_id)
    entry = scene_palette_set.find_scene(data, scene_id)
    background = load_background(root, background_path)
    problems = []
    for problem in background_report(grid, scene, background):
        problems.append(problem)

    def merge(items):
        for item in items:
            item.setdefault("background", background_path)
            problems.append(item)

    merge([])
    sprites = []
    paths = []
    for target in sprite_targets:
        paths.extend(sprite_paths(root, target))
    if not paths:
        raise SystemExit("palette_synergy: no sprite PNG found in %s" % ", ".join(sprite_targets))
    for path in paths:
        image = contrast_check.load_sheet(path)
        fw, fh, how, declared_layer = frame_size(root, path, image, frame_w, frame_h)
        report = {"path": shown(root, path), "size": [image.width, image.height],
                  "frame": [fw, fh], "frame_from": how,
                  "declared_layer": declared_layer,
                  "figure": is_sprite_frame(fw, fh, declared_layer), "frames": [],
                  "tiles": {"inked": 0, "uncovered": 0}}
        for box in frames(image, fw, fh):
            info = frame_report(grid, scene, image, box, background, at, declared_layer)
            if info.get("skipped"):
                continue
            if info.get("tiles"):
                report["tiles"]["inked"] += info["tiles"]["inked"]
                report["tiles"]["uncovered"] += info["tiles"]["uncovered"]
            for problem in info.pop("problems"):
                problem["sprite"] = report["path"]
                problem["frame"] = list(box)
                problems.append(problem)
            report["frames"].append(info)
        sprites.append(report)

    result = {
        "tool": "palette_synergy",
        "scene": scene_id,
        "background": shown(root, resolve(root, background_path)),
        "audit": {"background": background_path, "sprites": list(sprite_targets),
                  "frame": [frame_w, frame_h], "at": list(at) if at else None},
        "backdrop": grid.code(scene.backdrop),
        "gate": bool(entry.get("gate", False)),
        "rules": {
            "body_ground": "body and ground at least %d luminance rows apart or %.1f:1 apart"
                           % (ROW_GAP_MIN, FIGURE_GROUND_CONTRAST_MIN),
            "same_hue_row": "body and ground not the same hue family on the same row",
            "overlay_contrast": "a tiled layer (a sheet that declares \"layer\": true, or a frame bigger than "
                                "%dx%d) clears %.1f:1 with its ink or its body on every ground colour under it"
                                % (SPRITE_FIGURE_W, SPRITE_FIGURE_H, OVERLAY_CONTRAST_MIN),
            "white_blob": "no near white body (%.2f) on a light ground (%.2f)" % (NEAR_WHITE, LIGHT_GROUND),
            "sprite_tile": "at most %d colours per 8x8 sprite tile" % MAX_SPRITE_COLOURS,
            "background_area": "at most %d colours besides the backdrop per 16x16 area" % MAX_AREA_COLOURS,
            "palette_count": "at most %d background and 4 sprite palettes per frame; for a figure bigger than "
                             "%dx%d, every 8x8 tile fits one sprite palette of the scene"
                             % (MAX_BG_PALETTES, WHOLE_FRAME_W, WHOLE_FRAME_H),
            "set_member": "every drawn colour is in the scene's palette set",
        },
        "sprites": sprites,
        "problems": problems,
        "fail_count": len(problems),
        "ok": not problems,
        "exit_code": 0 if not problems else 1,
    }
    return result


def describe(result: dict) -> list:
    lines = []
    lines.append("palette_synergy %s on %s: %s, %d sprite file(s), %d failing pair(s)"
                 % (result["scene"], result["background"], "PASS" if result["ok"] else "FAIL",
                    len(result["sprites"]), result["fail_count"]))
    for problem in result["problems"]:
        where = problem.get("sprite", "")
        box = problem.get("frame")
        prefix = ""
        if where:
            prefix = "%s%s " % (where, (" @%d,%d" % (box[0], box[1])) if box else "")
        lines.append("  FAIL %-16s %s%s" % (problem["rule"], prefix, problem["detail"]))
    for sprite in result["sprites"]:
        tiles = sprite.get("tiles") or {}
        if tiles.get("inked"):
            lines.append("  %s: %d inked 8x8 tiles, %d of them uncovered by any sprite palette of the scene"
                         % (sprite["path"], tiles["inked"], tiles.get("uncovered", 0)))
        for info in sprite["frames"]:
            failing = sum(1 for pair in info["pairs"] if not pair["ok"])
            line = ("  %s @%d,%d body %s row %d hue %s palettes that fit %s pairs failing %d of %d"
                    % (sprite["path"], info["box"][0], info["box"][1], info["body"], info["body_row"],
                       info["body_hue"], info["palettes_that_fit"], failing, len(info["pairs"])))
            if info.get("tiles"):
                line += ", tiles %d inked %d uncovered" % (info["tiles"]["inked"], info["tiles"]["uncovered"])
            if info.get("layer"):
                line += ", tiled layer so R1b: ink %s, separation by contrast on every ground" % info.get("ink")
            lines.append(line)
    return lines


# -----------------------------------------------------------------------------------------------------------------
# Gate mode: every audit entry written down in data\\scene_palettes.json.

# -----------------------------------------------------------------------------------------------------------------
# The cast half, on its own.

def cast_problems(result: dict) -> list:
    """The problems that say the scene's SPRITE palettes cannot carry a named sheet, and nothing else.

    R7 on the sheet's own colours and R6 in both readings (one palette for a whole 16x16 frame, one palette per
    8x8 tile for a multi-tile figure). Everything else a run reports is about the frame the sheet is drawn over:
    the pair rules (R1, R1b, R2, R3), the background's own R5 and R6, and the ground colour under the sprite. A
    cast can be legal on a scene whose frame still fails the pair column, and that is the normal state of this
    project, so a caller asking "does this scene carry this cast" must not read those as a cast failure.

    Why this exists: an audit row can name a sheet its scene cannot carry and nothing said so. The deck's row
    named the walking sailor for a day after the four deck palettes were re-solved for the fight cast, and every
    draw round then measured 16 failures on the difference (card t_4f18c0ac, knowledge/PALETTE-RULINGS-2026-10-24.md).
    A mark on the problem itself beats matching on the wording of a message.
    """
    return [problem for problem in result["problems"] if problem.get("subject") == "cast"]


def audit_entries(root: str, data: dict) -> list:
    out = []
    for item in data.get("audit", []):
        entry = scene_palette_set.find_scene(data, item["scene"])
        out.append({
            "scene": item["scene"],
            "background": item["background"],
            "sprites": item["sprites"],
            "at": item.get("at"),
            "frame": item.get("frame"),
            "gate": bool(entry.get("gate", False)),
            "by_product": bool(item.get(scene_palette_set.BY_PRODUCT_KEY, False)),
        })
    return out


def missing_inputs(root: str, item: dict) -> list:
    """The files an audit row names that are not on disk, in the order the row names them."""
    out = []
    background = item.get("background")
    if background and not os.path.isfile(resolve(root, background)):
        out.append(background)
    for path in item.get("sprites") or []:
        if not os.path.isfile(resolve(root, path)):
            out.append(path)
    return out


def not_measured(item: dict, missing: list) -> dict:
    """A by-product row whose file this tree does not carry, reported instead of refused.

    A by-product is gitignored and two generators write different content under one name (the contact sheet:
    tools/art/make_characters_v2.py measures 11 records here, tools/art/make_title_rows_v2.py 3 on the far side),
    so no clean checkout reproduces it and an audit row cannot claim it as evidence. Refusing the whole run cost
    three Pine jobs (v10aR-0, v10aU-0, v10aV-0); the ruling is that such a row reports NOT MEASURED with a printed
    line (knowledge/PALETTE-RULINGS-2026-10-25.md section 8, card t_c93a983f).
    """
    return {
        "scene": item["scene"], "background": item["background"], "sprites": list(item["sprites"]),
        "measured": False, "by_product": True, "gated": False,
        "ok": True, "fail_count": 0, "problems": [], "skipped": list(missing),
    }


def gate(root: str) -> tuple:
    data = scene_palette_set.load(root)
    results = []
    for item in audit_entries(root, data):
        missing = missing_inputs(root, item)
        if item["by_product"] and missing:
            results.append(not_measured(item, missing))
            continue
        frame_w = item["frame"][0] if item["frame"] else None
        frame_h = item["frame"][1] if item["frame"] else None
        result = analyse(root, item["scene"], item["background"], item["sprites"], item["at"], frame_w, frame_h)
        # A by-product that IS present is measured, and reported as advisory whatever it measures: it is a
        # diagnostic, not a cast ruling (card t_c93a983f).
        result["gated"] = item["gate"] and not item["by_product"]
        result["by_product"] = item["by_product"]
        result["measured"] = True
        results.append(result)
    blocked = [result for result in results if result["gated"] and not result["ok"]]
    advisory = [result for result in results if not result["gated"] and not result["ok"]]
    return results, blocked, advisory


def write_audit(root: str, results: list, path: str | None = None) -> str:
    out = path or os.path.join(root, "output", "palette_synergy.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    payload = {
        "tool": "palette_synergy",
        "mode": "gate",
        "results": [{"scene": result["scene"], "background": result["background"], "gated": result["gated"],
                     "ok": result["ok"], "fail_count": result["fail_count"],
                     "measured": result.get("measured", True),
                     "by_product": bool(result.get("by_product", False)),
                     "skipped": result.get("skipped", []),
                     "fails": sorted({problem["rule"] for problem in result["problems"]}),
                     "problems": result["problems"]} for result in results],
    }
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return out


# -----------------------------------------------------------------------------------------------------------------
# Selftest: two synthetic cases whose verdict is arithmetic, not taste.

def selftest(root: str = ROOT) -> int:
    grid = Grid(root)
    scene = scene_palette_set.scene(root, "title")
    ground = int(scene.backdrop)
    checks = 0
    # A body two rows above the backdrop must pass body_ground.
    body = 0x20  # row 2
    problems = pair_rules(grid, scene, body, ground, "selftest")
    assert not any(problem["rule"] == "body_ground" for problem in problems), problems
    checks += 1
    # A body one row above a black backdrop at 11.06:1 reads, so R1 passes it on the contrast instrument.
    # This is sailor_battle.png frame 2 on the deck, in arithmetic (card t_50193088).
    problems = pair_rules(grid, scene, 0x10, ground, "selftest")
    assert not any(problem["rule"] == "body_ground" for problem in problems), problems
    checks += 1
    # A body one row above a ground of the same luminance reads at 1.00:1, so BOTH instruments are short and
    # body_ground must still refuse it. Without this check the contrast instrument would be a rubber stamp.
    problems = pair_rules(grid, scene, 0x00, 0x11, "selftest")
    assert any(problem["rule"] == "body_ground" for problem in problems), problems
    checks += 1
    # White on white must fail white_blob.
    problems = pair_rules(grid, scene, 0x30, 0x20, "selftest")
    assert any(problem["rule"] == "white_blob" for problem in problems), problems
    checks += 1
    # A tiled layer is judged by R1b instead: stone $00 on the $12 sky is one row apart, which R1 refuses,
    # and the ink $0F carries the edge at 3.75:1, so the layer reads and R1b passes.
    problems = layer_rules(grid, 0x00, 0x0F, 0x12, "selftest")
    assert not problems, problems
    checks += 1
    # Ink on ink, body on ink: nothing carries the edge and R1b must say so.
    problems = layer_rules(grid, 0x0F, 0x0F, 0x0F, "selftest")
    assert any(problem["rule"] == "overlay_contrast" for problem in problems), problems
    checks += 1
    # The size test that decides which of the two is asked: a character sprite against a tiled layer. A battle
    # figure is up to 32x32, and the sheet's own declaration outranks the width.
    assert is_sprite_frame(16, 32) and is_sprite_frame(16, 16) and is_sprite_frame(8, 8)
    assert is_sprite_frame(24, 32) and is_sprite_frame(32, 32) and is_sprite_frame(24, 16)
    assert not is_sprite_frame(224, 64) and not is_sprite_frame(64, 32)
    assert not is_sprite_frame(24, 32, True) and not is_sprite_frame(8, 8, True)
    checks += 1
    # R6's threshold: a frame 16x16 and under is asked as a whole, a bigger figure is asked per 8x8 tile.
    assert is_whole_frame(True, 16, 16) and is_whole_frame(True, 16, 8) and is_whole_frame(True, 8, 16)
    assert not is_whole_frame(True, 24, 32) and not is_whole_frame(True, 32, 32)
    assert not is_whole_frame(False, 16, 16)
    checks += 1
    # R6 per tile, on a synthetic 24x32 figure of twelve 8x8 tiles: the eleven tiles drawn in the title scene's
    # first sprite palette {$0F,$00,$28} are covered, and one tile drawn in $12 (in no title sprite palette) is
    # the one fail, named by its position and its colour set.
    colours, _, _ = scene_palette_set.load_master(root)
    sheet = Image.new("RGBA", (24, 32), (0, 0, 0, 0))
    load = sheet.load()
    for top in range(0, 32, TILE):
        for left in range(0, 24, TILE):
            if (left, top) == (16, 8):
                paint = (0x12, 0x28)
            else:
                paint = (0x0F, 0x00, 0x28)
            for y in range(top, top + TILE):
                for x in range(left, left + TILE):
                    rgb = colours[paint[(x + y) % len(paint)]]
                    load[x, y] = (rgb[0], rgb[1], rgb[2], 255)
    found, inked, uncovered = tile_fails(grid, scene, sheet, (0, 0, 24, 32), "selftest")
    assert inked == 12, inked
    assert uncovered == 1, (uncovered, found)
    assert found[0]["rule"] == "palette_count" and found[0]["tile"] == [16, 8], found
    assert "$12" in found[0]["colours"], found
    checks += 1
    # The hero palettes are dark to light and 3 colours each.
    data = scene_palette_set.load(root)
    for name in scene_palette_set.HEROES:
        palette = scene_palette_set.hero(data, name)
        assert len(palette["colours"]) == 3, name
        checks += 1
    print("palette_synergy selftest: %d check(s) PASS" % checks)
    return 0


# -----------------------------------------------------------------------------------------------------------------
# CLI.

def parse_at(text):
    if not text:
        return None
    parts = text.replace(" ", "").split(",")
    if len(parts) != 2:
        raise SystemExit("--at takes X,Y")
    return int(parts[0]), int(parts[1])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sprite against ground, both measured against the scene's set.")
    parser.add_argument("--scene", default=None)
    parser.add_argument("--background", default=None)
    parser.add_argument("--sprite", action="append", default=[], help="a PNG or a folder; repeatable")
    parser.add_argument("--at", default=None, help="X,Y placement of the sprite frame on the background")
    parser.add_argument("--frame-w", type=int, default=None)
    parser.add_argument("--frame-h", type=int, default=None)
    parser.add_argument("--json", default=None)
    parser.add_argument("--gate", action="store_true", help="run every audit entry in data/scene_palettes.json")
    parser.add_argument("--out", default=None, help="gate only: where to write the JSON report")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--root", default=ROOT)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.selftest:
        return selftest(root)

    if args.gate:
        results, blocked, advisory = gate(root)
        path = write_audit(root, results, args.out)
        unmeasured = [result for result in results if not result.get("measured", True)]
        for result in results:
            if not result.get("measured", True):
                print("palette_synergy %-9s %-18s %-44s NOT MEASURED (by product, not in this tree: %s)"
                      % ("advisory", result["scene"], os.path.basename(result["background"]),
                         ", ".join(result.get("skipped") or ["no file named"])))
                continue
            # A by-product still prints "advisory" whatever it measures: it is a diagnostic, never the gate.
            tag = "GATED" if result["gated"] else "advisory"
            print("palette_synergy %-9s %-18s %-44s %s, %d fail(s)"
                  % (tag, result["scene"], os.path.basename(result["background"]),
                     "PASS" if result["ok"] else "FAIL", result["fail_count"]))
            for problem in result["problems"][:6]:
                print("    %-16s %s" % (problem["rule"], problem["detail"]))
            if result["fail_count"] > 6:
                print("    ... %d more in %s" % (result["fail_count"] - 6, shown(root, path)))
        print("palette_synergy: %d entry(ies), %d gated failure(s), %d advisory failure(s), "
              "%d not measured; report %s"
              % (len(results), len(blocked), len(advisory), len(unmeasured), shown(root, path)))
        return 1 if blocked else 0

    if not (args.scene and args.background and args.sprite):
        parser.error("give --scene, --background and at least one --sprite, or use --gate")
    result = analyse(root, args.scene, args.background, args.sprite, parse_at(args.at),
                     args.frame_w, args.frame_h)
    if args.json:
        path = args.json if os.path.isabs(args.json) else os.path.join(root, args.json)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    if not args.quiet:
        for line in describe(result):
            print(line)
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
