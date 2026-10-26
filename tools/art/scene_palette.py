#!/usr/bin/env python3
"""scene_palette.py: the palette a title or ship frame is allowed to draw with, as data.

Why this exists
---------------
The art was correct layer by layer and wrong as a frame. Each strip passed the 16x16 area rule on its
own, because each strip was solved against its own backdrop; the layers were then composited and the
areas of the *screen* mixed palettes from two different layers. Measured 2026-10-21: 11 colours in the
night frame and 35 screen areas carrying four colours that do not belong to one palette. The NES does
not have eleven colours to spend: it has four background palettes of three, one shared backdrop, and
four sprite palettes of three plus transparency, and an area may use exactly one of them.

So the palette becomes a fact of the scene, written down before the art is made:

    data/palettes/scene_title.json   backdrop + 4 background palettes + 4 sprite palettes
    data/palettes/scene_ship.json    the same, for the ship tileset

and this module is the only thing allowed to decide which palette an area or a sprite tile gets. The
generators call `apply_scene()` after they have drawn and snapped, so what lands on disk is already
inside the budget, and tools/nes_composite_check.py checks the result again from the pixels, without
using anything this module knows.

A scene file can hold two things a solve does not compute, and write_scene() carries both forward: the
`judged` row (the ground the room's cast is measured on) and a half marked pinned (`sprites_pinned` for a
cast decision like the party's four walking triples on the ship, `background_pinned` for a ruled row set, which
the ship carried until card t_463cb8c1 replaced it with the measured floor below). See the docstring of
write_scene(). The ship's background half no longer needs its pin: the rows are the fit to the drawing that the
solve itself now measures, and solve_ship() refuses a proposal that repaints more of the drawing than the rows
already in the file.

The three rules it enforces, all from knowledge/ART-BIBLE.md section 1:

  background   16x16 screen areas; one palette of 3 entries plus the shared backdrop per area
  sprites      8x8 tiles; one sprite palette of 3 entries plus transparency per tile
  backdrop     background palette 0 entry 0, shared with every sprite palette; $0F black here

Dithering: the NES style is flat bands, and a checker dither only where two palette regions meet. So
`flatten_checker()` removes a 2x2 checker that sits *inside* one area (it spends two colours to say
what one colour says) and leaves it alone where the block straddles an area boundary.

Clean room: the rules are published hardware behaviour (PPU palettes, PPU attribute tables); the code
is our own. No art, palette or data from any published game is read or reproduced here.

Usage:
    python tools/art/scene_palette.py solve --scene title     # measure the art, print the proposal
    python tools/art/scene_palette.py solve --scene ship      # the same, for the ship sheet's rows
    python tools/art/scene_palette.py solve --scene ship --write   # move the design, then rebuild the art
    python tools/art/scene_palette.py apply --scene title     # enforce it on the strips on disk
    python tools/art/scene_palette.py show --scene title
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nes_tile  # noqa: E402  (the alpha rule, shared with tools/pp_intro_art.py)

CELL = 16          # background attribute area
SUBTILE = 8        # sprite tile
LIMIT = 3          # colours per palette, besides the backdrop / plus transparency
PALETTE_DIR = os.path.join("data", "palettes")
# Three keys this solver writes around rather than computes, all owned by the scene file itself:
#   judged              the audit row that says which ground the room's cast is measured on (card t_1dc346b9)
#   sprites_pinned      the sprite half is a cast decision, so a solve keeps it (ruling section 17, t_a6a7a436)
#   background_pinned   the background rows are a ruling, not a solve product, so a solve keeps them
#                       (ruling section 21, card t_23b5739a). The ship no longer carries the key: its solve now
#                       measures the DRAWING and keeps the file's rows whenever the proposal repaints more of it
#                       (ruling section 23, card t_463cb8c1), which is the same protection with a number behind it.
JUDGED_KEY = "judged"
SPRITES_PINNED_KEY = "sprites_pinned"
BACKGROUND_PINNED_KEY = "background_pinned"


# ---------------------------------------------------------------------------------------------------
# The 2C02 master palette.
# ---------------------------------------------------------------------------------------------------

def read_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def load_master(root: str):
    """Return (colours, usable, index_of): index_of prefers a usable entry over a black duplicate."""
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = [read_rgb(value) for value in data["colours"]]
    flags = data.get("usable")
    if isinstance(flags, list) and len(flags) == len(colours):
        usable = [bool(flag) for flag in flags]
    else:
        usable = [not (index == 0x0D or (rgb == (0, 0, 0) and index != 0x0F))
                  for index, rgb in enumerate(colours)]
    index_of = {}
    for index, rgb in enumerate(colours):
        if usable[index] and rgb not in index_of:
            index_of[rgb] = index
    for index, rgb in enumerate(colours):
        index_of.setdefault(rgb, index)
    return colours, usable, index_of


def distance(a, b) -> int:
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return dr * dr * 2 + dg * dg * 4 + db * db * 3


# ---------------------------------------------------------------------------------------------------
# The scene file.
# ---------------------------------------------------------------------------------------------------

class Scene:
    """backdrop + four background palettes of three + four sprite palettes of three, entry numbers."""

    def __init__(self, payload: dict, root: str):
        self.payload = payload
        self.root = root
        self.name = payload.get("scene", "?")
        self.backdrop = int(payload["backdrop"])
        self.background = [list(map(int, row["colours"])) for row in payload["background"]]
        self.sprites = [list(map(int, row["colours"])) for row in payload["sprites"]]
        if len(self.background) != 4 or len(self.sprites) != 4:
            raise SystemExit("scene_palette: %s must declare 4 background and 4 sprite palettes" % self.name)
        for row in self.background + self.sprites:
            if len(row) != LIMIT:
                raise SystemExit("scene_palette: %s has a palette of %d entries, the rule is %d"
                                 % (self.name, len(row), LIMIT))
        self.colours, self.usable, self.index_of = load_master(root)
        for row in self.background + self.sprites:
            for entry in row:
                if not 0 <= entry < len(self.colours):
                    raise SystemExit("scene_palette: $%02X is outside the 2C02 palette" % entry)
                if not self.usable[entry]:
                    raise SystemExit("scene_palette: $%02X is a forbidden entry" % entry)
        if not self.usable[self.backdrop]:
            raise SystemExit("scene_palette: backdrop $%02X is a forbidden entry" % self.backdrop)

    # -- lookup ------------------------------------------------------------------------------------

    def bg_sets(self):
        return [set(row) | {self.backdrop} for row in self.background]

    def sprite_sets(self):
        return [set(row) for row in self.sprites]

    def bg_colours(self) -> set:
        out = set()
        for row in self.background:
            out.update(row)
        return out

    def sprite_colours(self) -> set:
        out = set()
        for row in self.sprites:
            out.update(row)
        return out

    def rgb(self, entry: int):
        return self.colours[entry]

    def entry_of(self, rgb) -> int | None:
        return self.index_of.get(rgb)

    # -- which palette for a set of colours --------------------------------------------------------

    def pick_bg(self, counts: dict) -> tuple[int, int]:
        """(palette index, pixels that palette already covers) for one area's colour counts."""
        best = (-1, -1)
        for index, allowed in enumerate(self.bg_sets()):
            covered = sum(n for entry, n in counts.items() if entry in allowed)
            if covered > best[1]:
                best = (index, covered)
        return best

    def pick_sprite(self, counts: dict) -> tuple[int, int]:
        best = (-1, -1)
        for index, allowed in enumerate(self.sprite_sets()):
            covered = sum(n for entry, n in counts.items() if entry in allowed)
            if covered > best[1]:
                best = (index, covered)
        return best

    def nearest_in(self, entry: int, allowed) -> int:
        """The closest allowed entry to `entry`, deterministic on ties (lower entry wins)."""
        rgb = self.colours[entry]
        best = None
        for candidate in sorted(allowed):
            score = distance(rgb, self.colours[candidate])
            if best is None or score < best[0]:
                best = (score, candidate)
        return best[1]

    def nearest_master(self, rgb) -> int:
        """The closest usable 2C02 entry to an arbitrary colour.

        The generators draw in ordinary 24 bit colour and only some of their pixels land on a chip
        colour. The rest (a car's smooth shading, a cursor's anti aliased edge) are not on the NES at
        all, and the enforcement passes used to skip them, which is how a sprite could keep four
        colours in one 8x8 tile and still report clean. This maps every such pixel onto the master
        palette first, so the per area and per tile rules have something to work with.
        """
        best = None
        for entry, colour in enumerate(self.colours):
            if not self.usable[entry]:
                continue
            score = distance(rgb, colour)
            if best is None or score < best[0]:
                best = (score, entry)
        return best[1]


def snap_to_master(image: Image.Image, scene: Scene) -> int:
    """Rewrite every opaque pixel that is not a usable 2C02 colour onto the nearest one.

    A pixel with partial alpha is not drawable at all, so it is made into one of the two states the PPU has first
    (see nes_tile.solid_alpha: opaque, a 2 pixel checker, or transparent). Without that step a puff drawn at
    alpha 110 kept its alpha through every merge, and tools\\nes_check.py refused the whole strip for it.
    """
    if image.getchannel("A").getextrema() != (255, 255):
        image.paste(nes_tile.solid_alpha(image))
    pixels = image.load()
    index_of = scene.index_of
    moved = 0
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            entry = index_of.get((r, g, b))
            if entry is not None and scene.colours[entry] == (r, g, b):
                continue
            entry = scene.nearest_master((r, g, b))
            pixels[x, y] = scene.colours[entry] + (255,)
            moved += 1
    return moved


def scene_path(root: str, name: str) -> str:
    return os.path.join(root, PALETTE_DIR, "scene_%s.json" % name)


def load_scene(root: str, name: str) -> Scene:
    path = scene_path(root, name)
    with open(path, "r", encoding="utf-8-sig") as handle:
        return Scene(json.load(handle), root)


# ---------------------------------------------------------------------------------------------------
# Enforcement: make the pixels obey the scene.
# ---------------------------------------------------------------------------------------------------

def _pixel_counts(image: Image.Image, box, index_of, into: dict):
    """Count the master-palette entries an opaque box of the image uses.

    The box is clamped to the image, because a caller that asks for an 8x16 group on a sheet that is only 8 px
    tall (the star) or that runs past the last frame would otherwise read off the end and lose the whole pass to
    an IndexError instead of measuring the pixels that exist.
    """
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(image.width - 1, x1), min(image.height - 1, y1)
    pixels = image.load()
    if x1 < x0 or y1 < y0:
        return into
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            entry = index_of.get((r, g, b))
            if entry is not None:
                into[entry] = into.get(entry, 0) + 1
    return into


def enforce_background(image: Image.Image, scene: Scene, y_offset: int = 0) -> dict:
    """Force every 16x16 screen area of one background layer into a single scene palette.

    `y_offset` is the layer's screen y, so the areas are the ones the PPU sees and not the strip's own
    rows. Returns counts: areas touched, palette histogram and pixels moved.
    """
    pixels = image.load()
    index_of = scene.index_of
    moved = snap_to_master(image, scene)
    areas = 0
    histogram = [0, 0, 0, 0]
    for sy in range(0, image.height - 1, CELL):        # screen rows, aligned to the layer bottom edge
        top = sy - y_offset
        if top + CELL <= 0 or top >= image.height:
            continue
        y0 = max(0, top)
        y1 = min(image.height - 1, top + CELL - 1)
        for sx in range(0, image.width, CELL):
            x0 = sx
            x1 = min(image.width - 1, sx + CELL - 1)
            counts = _pixel_counts(image, (x0, y0, x1, y1), index_of, {})
            if not counts:
                continue
            index, _covered = scene.pick_bg(counts)
            allowed = scene.bg_sets()[index]
            histogram[index] += 1
            areas += 1
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    r, g, b, a = pixels[x, y]
                    if a == 0:
                        continue
                    entry = index_of.get((r, g, b))
                    if entry is None:
                        continue
                    if entry in allowed:
                        if (r, g, b) != scene.colours[entry]:
                            pixels[x, y] = scene.colours[entry] + (255,)
                        continue
                    target = scene.nearest_in(entry, allowed)
                    pixels[x, y] = scene.colours[target] + (255,)
                    moved += 1
    return {"areas": areas, "histogram": histogram, "pixels_moved": moved}


def enforce_sprites(image: Image.Image, scene: Scene, frame_w: int, frame_h: int,
                    sprite_height: int = 16) -> dict:
    """Force every 8x8 (or 8x16) sprite tile of one sprite sheet into a single sprite palette of three.

    Nothing is drawn behind a sprite, so transparency is the fourth state and is left alone.
    `sprite_height` is the OAM sprite height the frame will be drawn with. 16 is the stricter of the
    two the PPU offers: three colours in one 8x16 sprite also means three colours in each of its two
    8x8 halves, so art enforced at 16 is legal at either height, and it spends half the OAM entries.
    """
    pixels = image.load()
    index_of = scene.index_of
    moved = snap_to_master(image, scene)
    tiles = 0
    histogram = [0, 0, 0, 0]
    over = 0
    worst = 0
    step = 8 if sprite_height == 8 else 16
    frames = max(1, image.width // frame_w)
    for frame in range(frames):
        ox = frame * frame_w
        for ty in range(0, frame_h, step):
            for tx in range(0, frame_w, SUBTILE):
                x0, y0 = ox + tx, ty
                x1 = min(ox + frame_w - 1, x0 + SUBTILE - 1)
                y1 = min(frame_h - 1, y0 + step - 1)
                # The strip can be shorter than the frame says (an 8 px tall sheet asked for a 16 px group), so
                # the box is clamped here as well as in _pixel_counts: the counting call clamps its own copy, and
                # the write loop below indexes the image directly.
                x1 = min(x1, image.width - 1)
                y1 = min(y1, image.height - 1)
                counts = _pixel_counts(image, (x0, y0, x1, y1), index_of, {})
                if not counts:
                    continue
                if len(counts) > LIMIT:
                    over += 1
                worst = max(worst, len(counts))
                index, _covered = scene.pick_sprite(counts)
                allowed = scene.sprite_sets()[index]
                histogram[index] += 1
                tiles += 1
                for y in range(y0, y1 + 1):
                    for x in range(x0, x1 + 1):
                        r, g, b, a = pixels[x, y]
                        if a == 0:
                            continue
                        entry = index_of.get((r, g, b))
                        if entry is None:
                            continue
                        if entry in allowed:
                            continue
                        target = scene.nearest_in(entry, allowed)
                        pixels[x, y] = scene.colours[target] + (255,)
                        moved += 1
    return {"tiles": tiles, "histogram": histogram, "pixels_moved": moved,
            "sprite_height": step, "tiles_over_three": over, "worst_colours": worst}


def flatten_checker(image: Image.Image, scene: Scene, y_offset: int = 0) -> int:
    """Replace a same-area 2x2 checker with the majority colour; keep it where areas meet.

    A checker is the NES way to blend two palette colours at a boundary, so it is honest where a block
    straddles two attribute areas and wasteful inside one. Returns the pixels changed.
    """
    pixels = image.load()
    index_of = scene.index_of
    changed = 0
    for y0 in range(0, image.height - 1, 2):
        for x0 in range(0, image.width - 1, 2):
            same_area = ((x0 // CELL) == ((x0 + 1) // CELL)) and \
                        (((y0 + y_offset) // CELL) == ((y0 + 1 + y_offset) // CELL))
            if not same_area:
                continue
            values = []
            for dy in (0, 1):
                for dx in (0, 1):
                    r, g, b, a = pixels[x0 + dx, y0 + dy]
                    values.append(None if a == 0 else index_of.get((r, g, b), -1))
            if None in values or len(set(values)) != 2:
                continue
            if not (values[0] == values[3] and values[1] == values[2] and values[0] != values[1]):
                continue
            counts = {}
            for entry in values:
                counts[entry] = counts.get(entry, 0) + 1
            keep = max(counts, key=lambda entry: (counts[entry], -entry))
            for dy in (0, 1):
                for dx in (0, 1):
                    if values[dy * 2 + dx] != keep:
                        pixels[x0 + dx, y0 + dy] = scene.colours[keep] + (255,)
                        changed += 1
    return changed


# ---------------------------------------------------------------------------------------------------
# Solving a scene from the art: which four triples cover the frame best.
# ---------------------------------------------------------------------------------------------------

def area_profiles(image: Image.Image, index_of, y_offset: int = 0):
    """[(counts by entry)] for every 16x16 screen area that has pixels."""
    out = []
    for sy in range(0, image.height - 1, CELL):
        top = sy - y_offset
        if top + CELL <= 0 or top >= image.height:
            continue
        y0 = max(0, top)
        y1 = min(image.height - 1, top + CELL - 1)
        for sx in range(0, image.width, CELL):
            counts = _pixel_counts(image, (sx, y0, min(image.width - 1, sx + CELL - 1), y1), index_of, {})
            if counts:
                out.append(counts)
    return out


def solve(profiles, backlog=None, rounds: int = 4, gamma=None, keep=None) -> list[list[int]]:
    """Greedy cover of the profiles by `rounds` palettes of three entries.

    The unit that matters is the *area*, not the pixel: an area that keeps two of its three colours is
    an area that failed, whatever the pixel count says. So a triple is scored by how many whole areas
    it covers, then by how many pixels, then by the lower entries, which makes the choice deterministic
    and stops a large flat band from outvoting the small things standing on it.

    `gamma` (a multiplier) lets the caller prefer a triple that also covers colours still unused by any
    earlier palette, and `keep` forces entries into the pool so a scene can reserve a colour it knows
    the art needs even when the measurement has not reached that area yet.
    """
    pool = set()
    for counts in profiles:
        pool.update(counts)
    if keep:
        pool.update(keep)
    if backlog:
        pool.update(backlog)
    pool = sorted(pool)
    remaining = [dict(counts) for counts in profiles]
    chosen = []
    for _ in range(rounds):
        best = None
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                for k in range(j + 1, len(pool)):
                    allowed = {pool[i], pool[j], pool[k]}
                    whole = 0
                    pixels = 0
                    for counts in remaining:
                        if counts and set(counts) <= allowed:
                            whole += 1
                        pixels += sum(n for entry, n in counts.items() if entry in allowed)
                    score = (whole, pixels, -pool[i] - pool[j] - pool[k])
                    if best is None or score > best[0]:
                        best = (score, [pool[i], pool[j], pool[k]])
        chosen.append(list(best[1]))
        allowed = set(best[1])
        for counts in remaining:
            if counts and set(counts) <= allowed:
                counts.clear()
            else:
                for entry in list(counts):
                    if entry in allowed:
                        del counts[entry]
    return chosen


def _file_payload(path: str) -> dict:
    """The scene file as it is on disk, or {} when there is none. A file that cannot be read is not a file to
    carry anything forward from, so it is treated the same way."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_scene(root: str, name: str, backdrop: int, background, sprites, notes) -> str:
    """Write the scene file, carrying forward the parts a solve does not own.

    A scene file can be written by more than one card. `judged` is the audit row that says what ground a room's
    cast is measured on, and this solver has never emitted one, so a solve used to delete it (the defect card
    t_5802ecdb closed on tools/art/make_battle_bg.py and card t_dec4e92c closed on make_exterior_maps.py, same
    shape in a third file). `sprites_pinned: true` marks a sprite half that is a CAST DECISION rather than a
    solve product: the ship's four rows are the party's four walking triples, shared with the towns by hand
    (knowledge/PALETTE-RULINGS-2026-10-25.md section 17, card t_a6a7a436), so a solve keeps that half and the
    notes that explain it and prints what it kept.

    `background_pinned: true` marks the same thing for the BACKGROUND half: the rows are a ruling, not a solve
    product (ruling section 21, card t_23b5739a). The ship's rows are an input to the pixels of ts_ship.png, so a
    solve that writes them repaints the art; measured on 2026-10-25 the solver's rows rebuild a different sheet
    (151 pixels over 6 tiles) and drop one of the ten declared colours. Pinning the half means a
    `solve --write` prints the proposal and keeps the file, and removing the key is how a card that means to move
    the design does it. A file with neither pin takes the solver's rows for both halves, which is the control the
    tests measure.
    """
    colours, usable, _index_of = load_master(root)
    path = scene_path(root, name)
    before = _file_payload(path)
    pinned = bool(before.get(SPRITES_PINNED_KEY))
    background_pinned = bool(before.get(BACKGROUND_PINNED_KEY)) and bool(before.get("background"))
    if pinned and before.get("sprites"):
        sprites = [[int(entry) for entry in row["colours"]] for row in before["sprites"]]
        print("scene_palette: %s keeps its pinned sprite half (sprites_pinned true)" % os.path.basename(path))
    if background_pinned:
        background = [[int(entry) for entry in row["colours"]] for row in before["background"]]
        if "backdrop" in before:
            backdrop = int(before["backdrop"])
        print("scene_palette: %s keeps its pinned background half (background_pinned true); the proposal is "
              "not applied" % os.path.basename(path))
    if (pinned or background_pinned) and before.get("notes"):
        notes = list(before["notes"])
    payload = {
        "format": 1,
        "kind": "scene_palette",
        "scene": name,
        "rule": "NES: 1 backdrop shared by both layers, 4 background palettes of 3 entries on 16x16 "
                "areas, 4 sprite palettes of 3 entries plus transparency on 8x8 tiles; every entry is "
                "a data/nes_palette.json entry number",
        "backdrop": backdrop,
        "background": [{"name": "bg%d" % index, "colours": row,
                        "hex": ["#%02x%02x%02x" % colours[entry] for entry in row]}
                       for index, row in enumerate(background)],
        "sprites": [{"name": "sp%d" % index, "colours": row,
                     "hex": ["#%02x%02x%02x" % colours[entry] for entry in row]}
                    for index, row in enumerate(sprites)],
        "notes": notes,
    }
    if pinned:
        payload[SPRITES_PINNED_KEY] = True
    if background_pinned:
        payload[BACKGROUND_PINNED_KEY] = True
    if before.get(JUDGED_KEY):
        payload[JUDGED_KEY] = before[JUDGED_KEY]
        print("scene_palette: %s keeps its %d judged row(s) verbatim"
              % (os.path.basename(path), len(before[JUDGED_KEY])))
    if before and before == payload:
        # Both halves pinned (or the solve landed exactly the rows already there): do not rewrite the file, so a
        # `solve --write` cannot leave a layout-only diff in the tree it was told to keep.
        print("scene_palette: %s already holds these rows; nothing written" % os.path.basename(path))
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


# ---------------------------------------------------------------------------------------------------
# Scene sources: how the title frame is composed, and where the ship tiles live.
# ---------------------------------------------------------------------------------------------------

def title_composite(root: str) -> Image.Image:
    """Frame 0 of the title drive, background layers only, composed the way data/title.json says."""
    with open(os.path.join(root, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    frame = Image.new("RGBA", (256, 240), (0, 0, 0, 0))
    for row in table["layers"]:
        image, meta = load_strip(root, row["name"])
        one = image.crop((0, 0, meta["frame_w"], meta["frame_h"]))
        frame.alpha_composite(one, (0, row["y"]))
    return frame


def load_strip(root: str, name: str):
    base = os.path.join(root, "game", "sprites_src", "title", name)
    with open(base + ".json", "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    with Image.open(base + ".png") as handle:
        return handle.convert("RGBA"), meta


TITLE_SPRITES = ["spr_title_car", "spr_pp_title_logo", "spr_title_sign", "spr_title_cone",
                 # spr_pp_window, spr_pp_font8 and spr_pp_menu_cursor are NOT here, and that is a decision:
                 # tools/art/make_title_ui.py writes them in the UI palette, they pass tools/nes_check.py as they
                 # are (measured 2026-10-22: all three PASS with no palette pass), and tests/test_make_title_ui.py
                 # pins their ink to the exact bytes that generator writes. Repainting them here would only fight
                 # the generator, the way it used to: the cursor's ink $0b0b0f came back as $0F black and four pins
                 # went red over art nobody had asked to change.
                 # The effects the title draws and the cast it keeps for the interior scenes. They were missing
                 # from this list, which is why they were the only title art the enforcement never touched: the
                 # cloud, the exhaust, the star and the three busts shipped in the project's drawing palette,
                 # with partial alpha, and in 10 to 16 pixel frames that cannot be cut into 8x8 tiles.
                 "spr_title_cloud", "spr_title_exhaust", "spr_title_star",
                 "spr_title_cloud_fade1", "spr_title_cloud_fade2",
                 "spr_title_cloud_fade3", "spr_title_cloud_fade4",
                 "spr_title_exhaust_fade1", "spr_title_exhaust_fade2",
                 "spr_title_exhaust_fade3", "spr_title_exhaust_fade4",
                 "spr_title_konrad", "spr_title_zander", "spr_title_bubble", "spr_title_wheel"]

# The sprites whose frames are 16x16 drawings rather than parts of a bigger object. A face cannot survive being
# flattened to three colours across an 8x16 sprite, and it does not have to: the PPU's sprite rule is per OAM
# sprite, 8x8 is one, and each tile may pick its own one of the four sprite palettes. The rest of the list is
# enforced at 8x16 because those parts are drawn as pairs of tiles and the stricter grouping costs them nothing.
CAST_SPRITES = ("spr_title_zander", "spr_title_konrad", "spr_title_bubble", "spr_title_wheel")


def master_copy(image: Image.Image, colours, usable, index_of) -> Image.Image:
    """A copy of the art as the cartridge will hold it: solid alpha, every pixel on a usable 2C02 entry.

    The solver has to see the colours the enforcement will actually produce. Some sheets are drawn in the project
    palette (the cast, the cloud, the exhaust), and those pixels are not on the master palette at all, so profiling
    them raw dropped them out of the solve entirely and their palettes were chosen from the handful of pixels that
    happened to be chip colours already.
    """
    out = image.copy()
    if out.getchannel("A").getextrema() != (255, 255):
        out.paste(nes_tile.solid_alpha(out))
    pixels = out.load()
    cache = {}
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            key = (r, g, b)
            entry = cache.get(key)
            if entry is None:
                entry = index_of.get(key)
                if entry is None or not usable[entry] or colours[entry] != key:
                    entry = 0x0F
                    best = None
                    for candidate, colour in enumerate(colours):
                        if not usable[candidate]:
                            continue
                        score = distance(key, colour)
                        if best is None or score < best[0]:
                            best = (score, candidate)
                    entry = best[1]
                cache[key] = entry
            pixels[x, y] = colours[entry] + (255,)
    return out


def sprite_colour_pool(root: str):
    colours, usable, index_of = load_master(root)
    pool = set()
    for name in TITLE_SPRITES:
        try:
            image, _meta = load_strip(root, name)
        except OSError:
            continue
        for r, g, b, a in master_copy(image, colours, usable, index_of).getdata():
            if a == 0:
                continue
            entry = index_of.get((r, g, b))
            if entry is not None:
                pool.add(entry)
    return pool


# ---------------------------------------------------------------------------------------------------
# Apply: run the enforcement over the art on disk.
# ---------------------------------------------------------------------------------------------------

def enforce_area_map(image: Image.Image, scene: Scene, y_offset: int, area_map: dict) -> int:
    """Remap one background layer against a palette chosen per *screen* area by the composite.

    This is the difference between a layer that passes on its own and a frame that passes: an area of
    the screen can hold pixels from four different strips, and it is the area, not the strip, that has
    one palette. Pixels whose screen row falls in an area with no assignment are left alone.
    """
    pixels = image.load()
    index_of = scene.index_of
    moved = snap_to_master(image, scene)
    # The screen area rows, not the strip's rows: a layer whose y is 92 has its first screen area
    # boundary at strip row 4, so chunking the strip in 16s would straddle two areas on every row.
    for area_y in range(0, 240, CELL):
        ly0 = area_y - y_offset
        ly1 = ly0 + CELL - 1
        if ly1 < 0 or ly0 >= image.height:
            continue
        y0 = max(0, ly0)
        y1 = min(image.height - 1, ly1)
        for sx in range(0, image.width, CELL):
            index = area_map.get((sx % 256, area_y))
            if index is None:
                continue
            allowed = scene.bg_sets()[index]
            for y in range(y0, y1 + 1):
                for x in range(sx, min(image.width - 1, sx + CELL - 1) + 1):
                    r, g, b, a = pixels[x, y]
                    if a == 0:
                        continue
                    entry = index_of.get((r, g, b))
                    if entry is None or entry in allowed:
                        continue
                    target = scene.nearest_in(entry, allowed)
                    pixels[x, y] = scene.colours[target] + (255,)
                    moved += 1
    return moved


def write_frame_preview(root: str) -> dict:
    """Rewrite the 3x preview of the drive, background layers only, from the strips as they are now on disk.

    The preview is a finished frame, and the audit judges it as one, so it has to be composed AFTER the palette
    pass and not before it: make_title_world draws the strips, this module repaints them into the scene's four
    background palettes, and a preview rendered before the repaint is a picture of art that is no longer on disk
    (measured 2026-10-22: 25 screen areas in the preview carried colours the strips no longer had).

    It carries the background and no sprite. That is the same split tools\\check_scene_palettes.py already makes
    ("the composed background frame and every sprite sheet it draws"): a background pixel is spent from one of
    the four background palettes, a sprite pixel from one of the four sprite palettes, and a frame check without
    a sprite mask cannot tell the two apart. Drawing the sign or the headlight cone into this file would charge
    their white against the hedge's three greens, which is a fault of the measuring, not of the art. The sprite
    is judged where it belongs: every 8x16 group of every sheet, in tools\\check_scene_palettes.py.
    """
    import make_title_world as world

    with open(os.path.join(root, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    layer_specs = []
    for row in table["layers"]:
        image, meta = load_strip(root, row["name"])
        layer_specs.append({"name": row["name"], "y": row["y"], "speed": row["speed"],
                            "frames": [image.crop((0, 0, meta["frame_w"], meta["frame_h"]))]})
    frame = world.compose(layer_specs, camera_x=0.0)
    out = os.path.join(root, "output", "ts2_world_preview.png")
    frame.resize((256 * 3, 240 * 3), Image.NEAREST).save(out, "PNG")
    scene = load_scene(root, "title")
    sidecar = os.path.join(root, "output", "ts2_world_preview.json")
    with open(sidecar, "w", encoding="utf-8", newline="\n") as handle:
        json.dump({"frame": ["ts2_world_preview.png"], "scale": 3,
                   "backdrop": "#%02x%02x%02x" % scene.colours[scene.backdrop],
                   "backdrop_entry": scene.backdrop,
                   "sprites": "not drawn: a sprite pixel is spent from a sprite palette, and this frame is "
                              "measured against the four background palettes",
                   "note": "composed from data/title.json after the scene palette pass; the backdrop is the "
                           "scene's $3F00 colour, which is what the checker measures the areas against"},
                  handle, indent=2, sort_keys=True)
        handle.write("\n")
    return {"preview": out, "sidecar": sidecar}


def apply_title(root: str) -> dict:
    scene = load_scene(root, "title")
    table_path = os.path.join(root, "data", "title.json")
    with open(table_path, "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    report = {"scene": "title", "layers": {}, "sprites": {}, "passes": []}

    # Pass 1 and 2: the palette of each screen area comes from the composite, and every layer is then
    # rewritten to it. Two passes are enough because the first pass leaves every area inside one
    # palette, so the second measurement cannot disagree with the choice.
    rows = [row for row in table["layers"]]
    for number in range(2):
        composite = title_composite(root)
        area_map = {}
        moved = 0
        for sy in range(0, 240 - 1, CELL):
            for sx in range(0, 256, CELL):
                box = (sx, sy, min(255, sx + CELL - 1), min(239, sy + CELL - 1))
                counts = _pixel_counts(composite, box, scene.index_of, {})
                if counts:
                    area_map[(sx, sy)] = scene.pick_bg(counts)[0]
        for row in rows:
            name = row["name"]
            y = row.get("y", 0)
            image, meta = load_strip(root, name)
            fw, fh = meta["frame_w"], meta["frame_h"]
            for frame in range(image.width // fw):
                one = image.crop((frame * fw, 0, (frame + 1) * fw, fh))
                moved += enforce_area_map(one, scene, y, area_map)
                image.paste(one, (frame * fw, 0))
            image.save(os.path.join(root, "game", "sprites_src", "title", name + ".png"), "PNG")
        report["passes"].append({"pass": number + 1, "pixels_moved": moved})

    # The checker dither: keep it where two areas meet, flatten it inside an area.
    for row in rows:
        name = row["name"]
        y = row.get("y", 0)
        image, meta = load_strip(root, name)
        fw, fh = meta["frame_w"], meta["frame_h"]
        checkers = 0
        for frame in range(image.width // fw):
            one = image.crop((frame * fw, 0, (frame + 1) * fw, fh))
            checkers += flatten_checker(one, scene, y)
            image.paste(one, (frame * fw, 0))
        image.save(os.path.join(root, "game", "sprites_src", "title", name + ".png"), "PNG")
        report["layers"][name] = {"checkers_flattened": checkers, "y": y}

    # Which sheets the band plan paints. Those are decided by their band palette (title_bands.apply, the last pass), so
    # the per-area enforcement must not touch them first: card t_a1170172 measured what happens when it does. The new
    # sprite row sp0 holds the wordmark's $0F, and a car group the enforcement had no reason to move chose sp0 and took
    # black pixels, which the band pass then skipped as the backdrop, so a black outline appeared on the car's body.
    # The busts are not band painted (they are not drawn on the title screen), so they are the sheets this pass owns.
    band_painted = {name for name in (scene.payload.get("band_sprites") or {}) if not name.startswith("_")}
    for name in TITLE_SPRITES:
        if name in band_painted:
            report["sprites"][name] = {"band_painted": True}
            continue
        try:
            image, meta = load_strip(root, name)
        except OSError:
            continue
        # 8x16 for every sheet, because that is the unit the checker groups by: tools/check_scene_palettes.py
        # asks whether each 8x16 group of the sheet fits one of the four sprite palettes. Enforcing an 8x8 tile
        # at a time lets the top half of a group take one palette and the bottom half another, which the art then
        # fails on (measured 2026-10-22: spr_title_bubble, one group, no palette covered it). A sheet whose frame
        # is only 8 px tall (the star) has 8x8 groups, so the height is capped at the frame height: asking for a
        # 16 px group on an 8 px sheet walks off the bottom of the image.
        stats = enforce_sprites(image, scene, meta["frame_w"], meta["frame_h"],
                                sprite_height=min(16, meta["frame_h"]))
        image.save(os.path.join(root, "game", "sprites_src", "title", name + ".png"), "PNG")
        report["sprites"][name] = stats
    report["frame"] = write_frame_preview(root)
    # The flash strips are derived from the layers, so they are lifted from the repainted layers and not from the
    # ones the generator drew: see make_title_world.rebuild_flash() for the measurement that made this necessary.
    import make_title_world as world
    report["flash"] = {"strips": world.rebuild_flash(root)}
    # The last pass is the band plan (card t_a1170172). An area-by-area choice made at one camera position does
    # not survive a scroll: the road moves by a number of pixels that is not a multiple of 16, so a 16x16 area of
    # the next frame mixes two of the areas this pass just decided. Bands do not move, so tools/art/title_bands.py
    # is what the art on disk is finally expressed in, and data/palettes/scene_title.json "bands" is the decision.
    import title_bands
    report["bands"] = title_bands.apply(root)
    # The fade twins are derived art too, and they are the last thing lifted: every pass above can rewrite a base
    # strip, so the fades are rebuilt here from the bases as they are on disk now, exactly as the flash strips are
    # a few lines up. Card t_cd6a0d24 measured what leaving them out costs: 13 committed fade strips were the
    # fades of pictures the game no longer draws, five animations behind their own art, and nothing noticed.
    # The generator is imported from this file's own tree and not from `root`: a pass can be run over a copy of the
    # art (tests/test_title_art_v2.py does exactly that), and a copy carries no tools/ directory.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pp_intro_art
    report["fades"] = {"strips": pp_intro_art.write_fades(root)}
    return report


# The ship's cast is the WALKING cast, and this list is the same five sheets tools/check_scene_palettes.py
# judges on the ship's judged row and the same five the room draws (game/scripts/pp_overworld/pp_overworld.gml
# pp_hero_sheet zander_ow_v2, pp_sailor_sheet sailor_ow_v2, and the party's four walking sheets on the other
# three rooms). Card t_0b9c2faf retired the two 2026-10-22 names this list carried:
#   - sailor_battle is a 168x32 SEVEN FRAME 24x32 battle sheet, and no slot in this game takes it. The battle
#     screen's enemy slot is 32x32 px and reads game/sprites_src/enemies/<enemy id>.png as background art
#     (pp_battle_draw_enemy, card t_4275136f), and the only 24x32 slots are the four party slots in
#     data/ui_layouts.json, which are the four heroes. Measured on this tree: it carries ten entries
#     ($00 $02 $07 $08 $0F $10 $17 $27 $30 $36) and every frame of it needs two or three sprite palettes of
#     three, where each party battle sheet needs exactly one. It is judged on no row, it is out of this pool,
#     and tools/art/make_characters.py no longer writes it (see BATTLE_RETIRED there).
#   - sailor_ow is the 2026-10-22 walking sheet that sailor_ow_v2 replaced, and pp_overworld draws the v2.
SHIP_SPRITES = ["hadrian_ow_v2", "konrad_ow_v2", "zander_ow_v2", "percy_ow_v2", "sailor_ow_v2"]
CHARS_DIR = os.path.join("game", "sprites_src", "chars")


def load_cast(root: str, name: str):
    """One cast sheet from game/sprites_src/chars plus its animation contract."""
    base = os.path.join(root, CHARS_DIR, name)
    with open(base + ".json", "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    with Image.open(base + ".png") as handle:
        return handle.convert("RGBA"), meta


def cast_profiles(root: str, names, index_of):
    """The 8x16 groups of the ship's cast, the way the frame will draw them."""
    out = []
    for name in names:
        try:
            image, meta = load_cast(root, name)
        except OSError:
            continue
        fw, fh = meta["frame_w"], meta["frame_h"]
        for frame in range(max(1, image.width // fw)):
            ox = frame * fw
            for ty in range(0, fh, 16):
                for tx in range(0, fw, SUBTILE):
                    counts = _pixel_counts(image, (ox + tx, ty, min(ox + fw, ox + tx + SUBTILE) - 1,
                                                   min(fh, ty + 16) - 1), index_of, {})
                    if counts:
                        out.append(counts)
    return out


def enforce_ship_sheet(image: Image.Image, scene: Scene):
    """Force every 16x16 tile of the ship sheet into one scene background palette."""
    moved = 0
    histogram = [0, 0, 0, 0]
    pixels = image.load()
    for ty in range(0, image.height, CELL):
        for tx in range(0, image.width, CELL):
            box = (tx, ty, min(image.width - 1, tx + CELL - 1), min(image.height - 1, ty + CELL - 1))
            counts = _pixel_counts(image, box, scene.index_of, {})
            if not counts:
                continue
            index, _covered = scene.pick_bg(counts)
            allowed = scene.bg_sets()[index]
            histogram[index] += 1
            for y in range(box[1], box[3] + 1):
                for x in range(box[0], box[2] + 1):
                    r, g, b, a = pixels[x, y]
                    if a == 0:
                        continue
                    entry = scene.index_of.get((r, g, b))
                    if entry is None or entry in allowed:
                        continue
                    target = scene.nearest_in(entry, allowed)
                    pixels[x, y] = scene.colours[target] + (255,)
                    moved += 1
    return {"tiles": sum(histogram), "pixels_moved": moved, "histogram": histogram}


def apply_ship(root: str) -> dict:
    """The ship tileset sheet is 16 columns of 16x16 tiles; the rule is per tile, so no composite."""
    scene = load_scene(root, "ship")
    path = os.path.join(root, "game", "sprites_src", "env", "ts_ship.png")
    if not os.path.isfile(path):
        raise SystemExit("scene_palette: %s is missing; run tools/art/make_env_ship.py first" % path)
    with Image.open(path) as handle:
        image = handle.convert("RGBA")
    stats = enforce_ship_sheet(image, scene)
    image.save(path, "PNG", optimize=False)
    # The cast is the scene's sprite material: the walls may spend the shared backdrop as a fourth
    # colour, a sailor may not, so each 8x16 group of the cast is forced into one sprite palette.
    cast = {}
    for name in SHIP_SPRITES:
        try:
            image, meta = load_cast(root, name)
        except OSError:
            cast[name] = {"missing": True}
            continue
        cast[name] = enforce_sprites(image, scene, meta["frame_w"], meta["frame_h"])
        image.save(os.path.join(root, CHARS_DIR, name + ".png"), "PNG")
    return dict(stats, scene="ship", cast=cast)


# ---------------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------------

def solve_title(root: str, write: bool = False) -> dict:
    """Measure the art and propose four background and four sprite palettes that cover it.

    `write` defaults to False, and that default is the important part. The palette file is an INPUT to the
    v2 generators (title_logo_v2.py and title_car_v2.py pick their colours out of data/palettes/scene_title.json),
    so a solve that writes it by default is a loop: solve changes the palette, the generator draws new art from
    the changed palette, the next solve changes the palette again. Measured 2026-10-22: one solve turned the
    logo into a six-colour sprite and moved the car's glass out of the window band, and the art pins in
    tests/test_title_art_v2.py failed against art the palette move had caused. A solve is a report; use
    `solve --write` when you mean to move the design.
    """
    colours, usable, index_of = load_master(root)
    composite = title_composite(root)
    profiles = area_profiles(composite, index_of)
    backdrop = 0x0F
    background = solve(profiles, backlog=[backdrop])
    # The backdrop may never be spent as a palette colour, or an area could not tell it from its own.
    background = [[entry for entry in row if entry != backdrop] for row in background]
    background = [row if len(row) == LIMIT else row + [0x20][: LIMIT - len(row)] for row in background]

    sprite_pool = sprite_colour_pool(root)
    sprite_profiles = []
    for name in TITLE_SPRITES:
        try:
            image, meta = load_strip(root, name)
        except OSError:
            continue
        # Profiled as the cartridge will hold it, not as it was drawn: see master_copy.
        image = master_copy(image, colours, usable, index_of)
        fw, fh = meta["frame_w"], meta["frame_h"]
        for frame in range(image.width // fw):
            one = image.crop((frame * fw, 0, (frame + 1) * fw, fh))
            for ty in range(0, fh, SUBTILE):
                for tx in range(0, fw, SUBTILE):
                    counts = _pixel_counts(one, (tx, ty, min(fw - 1, tx + SUBTILE - 1),
                                                 min(fh - 1, ty + SUBTILE - 1)), index_of, {})
                    if counts:
                        sprite_profiles.append(counts)
    sprites = solve(sprite_profiles, backlog=sorted(sprite_pool - {backdrop}))

    notes = [
        "backdrop $0F black is background palette 0 entry 0 and is shared with every sprite palette",
        "background palettes cover the composite of the seven scrolling layers in data/title.json, "
        "16x16 screen areas",
        "sprite palettes cover every 8x8 tile of the car, the logo, the sign, the cone, the window, "
        "the font, the cursor, and the title's cast and effects (cloud, exhaust, star and their fades), "
        "3 colours plus transparency",
        "solved by tools/art/scene_palette.py from the art on disk, then checked again by "
        "tools/nes_composite_check.py",
    ]
    path = write_scene(root, "title", backdrop, background, sprites, notes) if write else scene_path(root, "title")
    leftover = 0
    # Without --write the file on disk is not the thing that was measured, so the report has to be the
    # PROPOSAL. Printing the file's rows here is how a drift survives: the command looks like it agreed
    # with the art when it was describing the art's input (card t_92d59163).
    scene = load_scene(root, "title") if write else proposed_scene(root, "title", backdrop, background, sprites)
    for counts in profiles:
        index, covered = scene.pick_bg(counts)
        leftover += sum(counts.values()) - covered
    return {"path": path, "scene": scene, "areas": len(profiles), "pixels_outside": leftover, "written": write}


def solve_ship(root: str, write: bool = False) -> dict:
    """Measure the ship DRAWING and propose four background and four sprite palettes that cover it.

    `write` defaults to False for the same reason `solve_title()`'s does, and the ship's version of the loop is
    sharper because the sheet is not drawn FROM these rows, it is repainted INTO them:
    `tools/art/make_env_ship.py build()` runs `enforce_ship_sheet()` over the in-memory sheet and saves the
    result, so the rows in `data/palettes/scene_ship.json` are an input to the pixels of `ts_ship.png`. A solve
    that writes by default therefore edits the art, and card t_92d59163 measured exactly that on 2026-10-25.

    Two things keep that honest, and neither is a convention:

    One, it measures the DRAWING (`ship_drawing()`, make_env_ship.render_sheet()) and not the enforced PNG. The
    PNG is the drawing after the rows on disk were applied to it, so solving it asks the rows to agree with
    themselves; card t_463cb8c1 measured the difference on 2026-10-25, when the same proposal covered every tile
    of the enforced sheet and repainted 646 pixels of the drawing.

    Two, the proposal has to beat the rows already in the file, by the measure ruling section 21.2 used: pixels of
    the drawing the row set repaints, then tiles it splits. A proposal that repaints more is reported in full and
    not written, `--write` or not, because writing it makes the art worse: on 2026-10-25 the ship's file rows
    repaint 76 of 12288 pixels and split 2 tiles, and the solver's proposal repaints 725 and splits 19 (646 before
    the ship's art was redrawn in its rows, so the redraw widened the gap). The `background_pinned: true` key
    (ruling section 21.5, card t_23b5739a) is the other half of the same idea and still wins when present, but the
    redrawn art no longer needs it: the numbers are the pin now, and a later proposal that is genuinely better
    moves the rows without anyone having to remove a key.
    """
    colours, usable, index_of = load_master(root)
    image = ship_drawing(root)
    profiles = area_profiles(image, index_of)
    backdrop = 0x0F
    background = solve(profiles, backlog=[backdrop])
    background = [[entry for entry in row if entry != backdrop] for row in background]
    background = [row if len(row) == LIMIT else row + [0x30][: LIMIT - len(row)] for row in background]
    # Sprites on the ship are cut from the same ten colours, three per tile plus transparency.
    subtiles = []
    for ty in range(0, image.height, SUBTILE):
        for tx in range(0, image.width, SUBTILE):
            counts = _pixel_counts(image, (tx, ty, min(image.width - 1, tx + SUBTILE - 1),
                                           min(image.height - 1, ty + SUBTILE - 1)), index_of, {})
            if counts:
                subtiles.append(counts)
    sprites = solve(subtiles + cast_profiles(root, SHIP_SPRITES, index_of),
                    backlog=sorted({entry for c in subtiles for entry in c}
                                   | {entry for c in cast_profiles(root, SHIP_SPRITES, index_of)
                                      for entry in c}))
    notes = [
        "backdrop $0F black is the hull shadow and the hatch void",
        "background palettes cover the 48 16x16 tiles of ts_ship.png, one palette per tile",
        "sprite palettes cover the same art cut to 8x8, 3 colours plus transparency, so any tile can "
        "also be drawn as sprites",
        "solved by tools/art/scene_palette.py and checked by tools/nes_composite_check.py",
    ]
    before = _file_payload(scene_path(root, "ship"))
    pinned = bool(before.get(BACKGROUND_PINNED_KEY))
    file_rows = [[int(entry) for entry in row["colours"]] for row in before.get("background", [])]
    kept = file_rows if (pinned and file_rows) else None
    proposal_pixels, proposal_split = repaint_cost(profiles, backdrop, background)
    file_pixels, file_split = repaint_cost(profiles, backdrop, file_rows)
    worse = file_pixels is not None and proposal_pixels > file_pixels
    write_this = write and not pinned and not worse
    path_out = write_scene(root, "ship", backdrop, background, sprites, notes) if write_this \
        else scene_path(root, "ship")
    scene = load_scene(root, "ship") if write_this else proposed_scene(root, "ship", backdrop,
                                                                      background, sprites)
    leftover = 0
    for counts in profiles:
        _index, covered = scene.pick_bg(counts)
        leftover += sum(counts.values()) - covered
    return {"path": path_out, "scene": scene, "areas": len(profiles), "pixels_outside": leftover,
            "written": write_this, "pinned": pinned, "kept": kept,
            "proposal": {"pixels": proposal_pixels, "tiles_split": proposal_split},
            "file": {"pixels": file_pixels, "tiles_split": file_split}}


def ship_drawing(root: str) -> Image.Image:
    """The ship sheet as make_env_ship DRAWS it, before the scene palette pass repaints it into the rows.

    The rows exist to serve the drawing, so the drawing is what a solve has to measure. Measuring
    `game/sprites_src/env/ts_ship.png` instead is circular: that file is the drawing AFTER the enforce pass
    repainted it into the rows on disk, so the solver is shown its own answer and reports a disagreement it
    cannot fix (measured 2026-10-25 on card t_463cb8c1: on the enforced sheet the proposal covered every tile,
    on the drawing the same proposal repaints 646 pixels). `render_sheet()` is pure geometry with no file input,
    so it is the same picture under any root; a tree without the generator falls back to the PNG on disk.
    """
    try:
        import make_env_ship
        return make_env_ship.render_sheet().convert("RGBA")
    except (ImportError, OSError):
        path = os.path.join(root, "game", "sprites_src", "env", "ts_ship.png")
        with Image.open(path) as handle:
            return handle.convert("RGBA")


def repaint_cost(profiles, backdrop: int, rows) -> tuple:
    """(pixels a row set would repaint of the drawing, tiles it would split) for one background half.

    The same measure ruling section 21.2 used on the raw sheet: a pixel is repainted when its colour is not in
    the row its tile picks, and a tile is split when any of its pixels is. `rows` may be empty.
    """
    if not rows:
        return (None, None)
    sets = [set(row) | {backdrop} for row in rows]
    pixels = 0
    split = 0
    for counts in profiles:
        total = sum(counts.values())
        covered = 0
        for allowed in sets:
            here = sum(n for entry, n in counts.items() if entry in allowed)
            if here > covered:
                covered = here
        pixels += total - covered
        if total > covered:
            split += 1
    return (pixels, split)


def proposed_scene(root: str, name: str, backdrop: int, background, sprites) -> "Scene":
    """A Scene built from a solve's PROPOSAL, so `solve` can describe what it measured and not the file.

    `Scene` is the same object the enforcement and the checkers read, so the report a bare solve prints is
    the palette set the enforcement would apply, not a summary restated here.
    """
    return Scene({
        "scene": name,
        "backdrop": backdrop,
        "background": [{"name": "bg%d" % index, "colours": list(row)} for index, row in enumerate(background)],
        "sprites": [{"name": "sp%d" % index, "colours": list(row)} for index, row in enumerate(sprites)],
    }, root)


def _display(path: str) -> str:
    """A path for a report: relative when that makes sense, absolute when it does not (another drive)."""
    try:
        return os.path.relpath(path)
    except ValueError:
        return path


def describe(result: dict) -> None:
    scene = result["scene"]
    colours = scene.colours
    print("%s: backdrop $%02X #%02x%02x%02x   %d 16x16 areas, %d pixels outside the chosen palette "
          "before enforcement" % ((scene.name, scene.backdrop) + colours[scene.backdrop]
                                  + (result["areas"], result["pixels_outside"])))
    for label, rows in (("background", scene.background), ("sprites", scene.sprites)):
        for index, row in enumerate(rows):
            print("  %s %d  %s" % (label, index,
                                   "  ".join("$%02X #%02x%02x%02x" % ((entry,) + colours[entry])
                                             for entry in row)))
    proposal = result.get("proposal") or {}
    filed = result.get("file") or {}
    if proposal.get("pixels") is not None and filed.get("pixels") is not None:
        print("  repaint on the drawing: the proposal %d of 12288 pixels over %d tiles, the file's rows %d over "
              "%d tiles" % (proposal["pixels"], proposal["tiles_split"], filed["pixels"], filed["tiles_split"]))
    if result.get("pinned"):
        print("  NOT applied: the background rows are PINNED (background_pinned true, ruling section 21) and the "
              "sprite half is pinned too, so a write keeps the file's own rows and touches neither half.")
        if result.get("kept"):
            print("  the file's rows are: " + " | ".join(
                "bg%d %s" % (index, " ".join("$%02X" % entry for entry in row))
                for index, row in enumerate(result["kept"])))
        print("  file: %s" % _display(result["path"]))
    elif proposal.get("pixels") is not None and filed.get("pixels") is not None \
            and proposal["pixels"] > filed["pixels"]:
        print("  NOT applied: the proposal repaints more of the drawing than the rows already in the file, so a "
              "write would make the art worse (card t_463cb8c1).")
        print("  the file's rows are the better fit and stay as they are.")
        print("  file: %s" % _display(result["path"]))
    else:
        print("  %s: %s" % ("written" if result.get("written") else "proposal only, nothing written; the file is",
                            _display(result["path"])))



def compose_frame(root: str, out_path: str) -> str:
    """Write frame 0 of the title drive at 1x, the frame tools/nes_composite_check.py judges."""
    frame = title_composite(root)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    frame.save(out_path, "PNG")
    return out_path


FONT_ORDER = " !',-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def swatch_bars(scene: Scene, width: int) -> Image.Image:
    """The eight palettes as labelled bars, so a 3x preview shows the budget the frame was drawn in."""
    font = None
    font_path = os.path.join(scene.root, "game", "sprites_src", "title", "spr_pp_font8.png")
    if os.path.isfile(font_path):
        with Image.open(font_path) as handle:
            font = handle.convert("RGBA")
    rows = scene.background + scene.sprites
    sheet = Image.new("RGBA", (width, len(rows) * 12 + 4), (0, 0, 0, 255))
    for index, row in enumerate(rows):
        y = 2 + index * 12
        label = ("bg%d" if index < 4 else "sp%d") % (index if index < 4 else index - 4)
        if font is not None:
            for column, char in enumerate(label):
                if char not in FONT_ORDER:
                    continue
                glyph = FONT_ORDER.index(char)
                if glyph * 8 + 8 > font.width:
                    continue
                sheet.paste(font.crop((glyph * 8, 0, glyph * 8 + 8, 8)), (4 + column * 8, y))
        for slot, entry in enumerate(row):
            x = 32 + slot * 20
            for dy in range(10):
                for dx in range(18):
                    sheet.putpixel((x + dx, y + dy), scene.colours[entry] + (255,))
    return sheet


def write_preview(root: str, out_path: str) -> str:
    scene = load_scene(root, "title")
    frame = title_composite(root)
    big = frame.resize((frame.width * 3, frame.height * 3), Image.NEAREST)
    bars = swatch_bars(scene, big.width)
    canvas = Image.new("RGBA", (big.width, big.height + bars.height + 4), (0, 0, 0, 255))
    canvas.paste(big, (0, 0))
    canvas.paste(bars, (0, big.height + 4))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path, "PNG")
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["solve", "apply", "show", "frame", "preview"])
    parser.add_argument("--scene", default="title", choices=["title", "ship", "all"])
    parser.add_argument("--out", default=None)
    parser.add_argument("--write", action="store_true",
                        help="solve only: save the proposed palettes to data/palettes/<scene>.json. The file is "
                             "an input to the generators for BOTH scenes (the title strips pick their colours "
                             "out of scene_title.json, and make_env_ship repaints ts_ship.png into "
                             "scene_ship.json's rows), so a solve that writes by default fights the art.")
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    names = ["title", "ship"] if args.scene == "all" else [args.scene]
    status = 0
    for name in names:
        if args.command == "solve":
            result = solve_title(root, write=args.write) if name == "title" else solve_ship(root, write=args.write)
            describe(result)
        elif args.command == "apply":
            report = apply_title(root) if name == "title" else apply_ship(root)
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "frame":
            out = args.out or os.path.join(root, "output", "nes_title_frame.png")
            print(compose_frame(root, out))
        elif args.command == "preview":
            out = args.out or os.path.join(root, "output", "nes_palette_preview.png")
            print(write_preview(root, out))
        else:
            scene = load_scene(root, name)
            describe({"scene": scene, "path": scene_path(root, name), "areas": 0, "pixels_outside": 0})
    return status


if __name__ == "__main__":
    sys.exit(main())
