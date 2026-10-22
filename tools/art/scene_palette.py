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
    python tools/art/scene_palette.py solve --scene title     # measure the art, write the scene JSON
    python tools/art/scene_palette.py solve --scene ship
    python tools/art/scene_palette.py apply --scene title     # enforce it on the strips on disk
    python tools/art/scene_palette.py show --scene title
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

CELL = 16          # background attribute area
SUBTILE = 8        # sprite tile
LIMIT = 3          # colours per palette, besides the backdrop / plus transparency
PALETTE_DIR = os.path.join("data", "palettes")


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
    """Rewrite every opaque pixel that is not a usable 2C02 colour onto the nearest one. Returns pixels moved."""
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
    x0, y0, x1, y1 = box
    pixels = image.load()
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


def write_scene(root: str, name: str, backdrop: int, background, sprites, notes) -> str:
    colours, usable, _index_of = load_master(root)
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
    path = scene_path(root, name)
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
                 "spr_pp_window", "spr_pp_font8", "spr_pp_menu_cursor"]


def sprite_colour_pool(root: str):
    _c, _u, index_of = load_master(root)
    pool = set()
    for name in TITLE_SPRITES:
        try:
            image, _meta = load_strip(root, name)
        except OSError:
            continue
        for r, g, b, a in image.getdata():
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

    for name in TITLE_SPRITES:
        try:
            image, meta = load_strip(root, name)
        except OSError:
            continue
        stats = enforce_sprites(image, scene, meta["frame_w"], meta["frame_h"])
        image.save(os.path.join(root, "game", "sprites_src", "title", name + ".png"), "PNG")
        report["sprites"][name] = stats
    return report


SHIP_SPRITES = ["sailor_ow", "sailor_battle"]
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

def solve_title(root: str) -> dict:
    _colours, usable, index_of = load_master(root)
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
        "the font and the cursor, 3 colours plus transparency",
        "solved by tools/art/scene_palette.py from the art on disk, then checked again by "
        "tools/nes_composite_check.py",
    ]
    path = write_scene(root, "title", backdrop, background, sprites, notes)
    leftover = 0
    scene = load_scene(root, "title")
    for counts in profiles:
        index, covered = scene.pick_bg(counts)
        leftover += sum(counts.values()) - covered
    return {"path": path, "scene": scene, "areas": len(profiles), "pixels_outside": leftover}


def solve_ship(root: str) -> dict:
    colours, usable, index_of = load_master(root)
    path = os.path.join(root, "game", "sprites_src", "env", "ts_ship.png")
    with Image.open(path) as handle:
        image = handle.convert("RGBA")
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
    path_out = write_scene(root, "ship", backdrop, background, sprites, notes)
    scene = load_scene(root, "ship")
    leftover = 0
    for counts in profiles:
        _index, covered = scene.pick_bg(counts)
        leftover += sum(counts.values()) - covered
    return {"path": path_out, "scene": scene, "areas": len(profiles), "pixels_outside": leftover}


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
    print("  file: %s" % os.path.relpath(result["path"]))


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
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    names = ["title", "ship"] if args.scene == "all" else [args.scene]
    status = 0
    for name in names:
        if args.command == "solve":
            result = solve_title(root) if name == "title" else solve_ship(root)
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
