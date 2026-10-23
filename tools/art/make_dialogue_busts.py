#!/usr/bin/env python3
"""make_dialogue_busts.py: draw the 48x48 four colour dialogue busts, one hand authored grid each.

Card t_4d6b0f4b (DIALOGUE-PORTRAIT). Its parent card t_01432e14 removed a portrait frame from spec 05 because no
speaker carried a bust and `pp_dialogue_draw` drew one anyway; this card is where the bust comes back, and the card
says plainly "do not start this until the sprite exists". So the sprite exists first, in this file, before any GML
learns to draw it.

Geometry, from specs/05-dialogue.md and knowledge/GAMEDEV-DECISIONS-2026-10-23.md D10 point 3
-------------------------------------------------------------------------------------------------
- 48x48 pixels, standing on the dialogue box's top edge at (16, 120). The box is at y 168, so a 48 pixel bust that
  starts at y 120 ends at y 167 and touches the box without covering one pixel of it.
- One pixel frame, drawn INTO the sheet rather than by a rectangle at run time: the box's draw path is one sheet and
  one call, and a frame the engine paints is a second thing that can disagree with the art.
- At most 4 colours from data/nes_palette.json, and at most 3 opaque in any 8x8 tile, because a sprite tile carries 3
  opaque colours plus transparency (ART-BIBLE 1.1 row 16). Each bust here spends exactly 4 entries and the audit below
  proves no tile spends more than 3.
- 48x48 is 36 sprite tiles, 6 to a scanline, inside the PPU's 8 sprites per scanline and 64 in OAM (ART-BIBLE 1.1
  rows 18 and 19). That arithmetic, and the box's 8 pixel padding, is why the bust is 48 and not 64.

The four entries, and why the middle is not transparent
-------------------------------------------------------
    panel  $02 navy, the dialogue window's own fill (data/palettes/scene_ui.json bg0)
    accent one per bust: the hair or helmet, and the frame
    skin   one per bust
    ink    $0F, the canonical black: the silhouette and every feature

A framed portrait with a transparent middle shows the level through its own frame, which reads as a hole rather than a
picture. So the interior is filled with the window's fill and the figure is drawn on it as ink line art: the face is
the one filled mass, the shoulders are an ink outline with a lapel line, and the hair or helmet is the accent. That is
a 3 opaque colour figure, which is exactly what one sprite tile can carry, and it belongs to the dialogue box instead
of floating over the map.

How these were drawn
--------------------
The left half of each sheet is drawn, then mirrored onto the right, so a face cannot be lopsided by a one pixel typo
and the silhouette is symmetric about the axis between x 23 and x 24. Every shape is a number in this file: the face
is 18 pixels wide on rows 9 to 30, the jaw steps in one pixel a row over rows 27 to 30, the eye is a 3x3 ink block at
x 18..20 with a 6 pixel bridge across both halves, the neck is 8 wide, and the shoulders are a trapezoid from row 35
to row 46. The ink outline is not hand listed: `outline()` recolours every pixel of a mass that touches a different
colour, which is the same 1 pixel silhouette rule tools/art/make_characters_v2.py uses.

The three busts answer the three speakers in data/dialogue/all.json that a portrait earns: the gate guard, Percy
(Poseidon) and Prometheus. Nothing was traced, ripped or resampled from any game; the proportions follow
knowledge/ART-BIBLE.md and knowledge/CHARACTER-BIBLE.md.

Usage
    python tools/art/make_dialogue_busts.py            build every bust, print the measured row
    python tools/art/make_dialogue_busts.py --dump     build, then print each frame as ASCII, numbered
    python tools/art/make_dialogue_busts.py --audit    build, then print the per tile colour audit
"""

from __future__ import annotations

import argparse
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_DIR = os.path.join(ROOT, "game", "sprites_src", "chars")
PALETTE_JSON = os.path.join(ROOT, "data", "nes_palette.json")

SIZE = 48
TILE = 8
HALF = 23  # the last left half column; the mirror axis is between 23 and 24
FPS = 1.0

# The role names a grid cell may hold. The four entries a bust may spend are named by role here and resolved to NES
# codes below, which is the only place in this file where a palette entry number is written.
PANEL = "panel"
ACCENT = "accent"
SKIN = "skin"
INK = "ink"

PANEL_CODE = "$02"   # #0000bc: the dialogue window's fill, so the bust belongs to the box it stands on
INK_CODE = "$0F"     # #000000, the canonical black (ART-BIBLE 1.3)

# role -> NES entry, per bust. Four entries each, no more.
BUSTS = {
    "guard": {
        "accent": "$30",  # #fcfcfc: the harbour watch's white helmet, and its frame
        "skin": "$36",    # #f0d0b0, the pale skin the cast sheet already uses
        "note": "the checkpoint sentry: a white watch helmet over a navy tunic, one white collar tab each side",
    },
    "percy": {
        "accent": "$30",
        "skin": "$36",
        "note": "Poseidon before the fight: white hair and a full white beard, his robe the same navy as the box",
    },
    "prometheus": {
        "accent": "$28",  # #f8b800 gold: the flame hair, the collar band, and the frame, which is the fire
        "skin": "$37",    # #fce0a8 a warm pale face, so the gold reads as fire and not as skin
        "note": "the reincarnation: gold flame hair and a gold collar band, his robe the box's own navy",
    },
}


class Grid:
    """A 48x48 grid of role names, transparent where nothing is drawn."""

    def __init__(self, size=SIZE):
        self.size = size
        self.cells = [[None for _ in range(size)] for _ in range(size)]

    def set(self, x, y, role):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.cells[y][x] = role

    def get(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.cells[y][x]
        return None

    def hline(self, x0, x1, y, role):
        for x in range(x0, x1 + 1):
            self.set(x, y, role)

    def vline(self, x, y0, y1, role):
        for y in range(y0, y1 + 1):
            self.set(x, y, role)

    def rect(self, x0, y0, x1, y1, role):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, role)

    def frame_rect(self, x0, y0, x1, y1, role):
        self.hline(x0, x1, y0, role)
        self.hline(x0, x1, y1, role)
        self.vline(x0, y0, y1, role)
        self.vline(x1, y0, y1, role)

    def mirror_x(self):
        """Copy the left half onto the right, so a face cannot be lopsided by a one pixel typo."""
        for y in range(self.size):
            for x in range(self.size // 2):
                self.cells[y][self.size - 1 - x] = self.cells[y][x]

    def count(self, role):
        return sum(1 for row in self.cells for cell in row if cell == role)

    def dump(self, legend):
        lines = []
        for index, row in enumerate(self.cells):
            lines.append("%02d %s" % (index, "".join(legend[cell] if cell else "." for cell in row)))
        return lines


def outline(grid, fill):
    """Recolour every `fill` pixel that touches a different colour with ink: the 1 pixel silhouette, done by rule.

    This is what makes a 3 colour figure read as a figure: the ink edge is already one of the three colours, so the
    silhouette costs nothing extra, and it is applied after the mass and before the features.
    """
    edges = []
    for y in range(grid.size):
        for x in range(grid.size):
            if grid.get(x, y) != fill:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                # The mirror axis is not an edge: the right half does not exist yet while the left half is outlined,
                # and treating it as empty would paint a two pixel seam down the middle of every face.
                if dx > 0 and x == HALF:
                    continue
                neighbour = grid.get(x + dx, y + dy)
                if neighbour is not fill and neighbour != INK:
                    edges.append((x, y))
                    break
    for x, y in edges:
        grid.set(x, y, INK)


def draw_panel(grid):
    """Fill the inside of the frame with the window's own navy: a portrait, not a hole in the level."""
    grid.rect(1, 1, SIZE - 2, SIZE - 2, PANEL)


def draw_face(grid):
    """The head every bust shares, drawn as the left half only: 18 pixels wide across both halves."""
    rows = [
        (9, 18), (10, 16),
        (11, 15), (12, 15), (13, 15), (14, 15), (15, 15), (16, 15), (17, 15), (18, 15),
        (19, 15), (20, 15), (21, 15), (22, 15), (23, 15), (24, 15), (25, 15), (26, 15),
        (27, 15), (28, 16), (29, 17), (30, 18),
    ]
    for y, x0 in rows:
        grid.hline(x0, HALF, y, SKIN)
    # Neck: 8 pixels wide across both halves, rows 31 to 34, under the chin.
    grid.rect(20, 31, HALF, 34, SKIN)
    outline(grid, SKIN)

    # Eye: a 3x3 ink block at x 18..20 rows 18..20, so the bridge is 6 pixels across both halves.
    grid.rect(18, 18, 20, 20, INK)
    # Brow: one ink row over the eye with a row of skin between, the outer end one row up so it reads as a brow.
    grid.hline(17, 21, 16, INK)
    grid.set(16, 15, INK)
    # Nose: one column on the left half, two pixels across once mirrored, from the eye line to above the mouth.
    grid.vline(HALF, 20, 23, INK)
    # Mouth: a line from x 19 to the axis, the corner one row up, so it reads as a mouth and not a slot.
    grid.hline(19, HALF, 27, INK)
    grid.set(19, 26, INK)


def draw_shoulders(grid):
    """The bust half: an ink shoulder line on the panel, with one lapel line inside it.

    The robe is the panel colour, which is how a 3 opaque colour figure pays for a body without spending a fifth
    entry: the shape is stated by ink, the same way the face's silhouette is.
    """
    for y in range(35, SIZE - 1):
        half = 10 + (y - 35)
        if half > 20:
            half = 20
        grid.set(HALF - half, y, INK)
        if y >= 37:
            grid.set(HALF - half + 2, y, INK)
    # Top of the shoulders: an ink line from the outer edge in to the neck, so the neck is not floating.
    grid.hline(HALF - 10, 19, 35, INK)
    grid.hline(19, HALF, 34, INK)


def draw_frame(grid):
    """The 1 pixel frame the geometry asks for, drawn into the sheet so the engine draws no second thing."""
    grid.frame_rect(0, 0, SIZE - 1, SIZE - 1, ACCENT)


def guard_grid():
    g = Grid()
    draw_panel(g)
    draw_face(g)
    draw_shoulders(g)
    # Watch helmet: the accent over the skull on rows 5 to 13, one pixel wider than the face, peaked at the crown.
    g.hline(19, HALF, 5, ACCENT)
    g.hline(16, HALF, 6, ACCENT)
    for y in range(7, 14):
        g.hline(14, HALF, y, ACCENT)
    outline(g, ACCENT)
    # Brim: 11 pixels each side of the axis, one row of accent over an ink line, so the cap has a visor.
    g.hline(13, HALF, 14, ACCENT)
    g.hline(13, HALF, 15, INK)
    # Duty collar: one white tab each side, on the shoulder, below the neck.
    g.rect(13, 41, 16, 43, ACCENT)
    return g


def percy_grid():
    g = Grid()
    draw_panel(g)
    draw_face(g)
    draw_shoulders(g)
    # Hair: the accent, rows 5 to 13, one pixel wider than the face, swept back at the temples.
    g.hline(18, HALF, 5, ACCENT)
    g.hline(16, HALF, 6, ACCENT)
    g.hline(14, HALF, 7, ACCENT)
    for y in range(8, 12):
        g.hline(13, HALF, y, ACCENT)
    g.hline(13, 15, 12, ACCENT)
    g.hline(13, 14, 13, ACCENT)
    g.hline(13, 14, 14, ACCENT)
    outline(g, ACCENT)
    # White brow over the ink brow, so an old god is not a young one: the face's brow ink is row 16, so this is row 14.
    g.hline(16, 20, 14, ACCENT)
    # Beard: the accent, rows 28 to 37, over the jaw and the neck, narrowing to 10 pixels across at the chest.
    beard = [(28, 17), (29, 15), (30, 14), (31, 14), (32, 15), (33, 16), (34, 17), (35, 19), (36, 20), (37, 21)]
    for y, x0 in beard:
        g.hline(x0, HALF, y, ACCENT)
    outline(g, ACCENT)
    # Strands: three short ink marks down the beard, so it reads as hair and not a bib.
    g.hline(16, 17, 31, INK)
    g.hline(19, 20, 32, INK)
    g.hline(16, 17, 34, INK)
    return g


def prometheus_grid():
    g = Grid()
    draw_panel(g)
    draw_face(g)
    draw_shoulders(g)
    # Flame hair: the accent, a solid mass on rows 5 to 11 with a jagged top edge and two notches cut in it, so the
    # silhouette reads as fire and not as a cap.
    g.hline(21, HALF, 3, ACCENT)
    g.hline(20, HALF, 4, ACCENT)
    g.hline(16, HALF, 5, ACCENT)
    g.hline(14, HALF, 6, ACCENT)
    for y in range(7, 12):
        g.hline(13, HALF, y, ACCENT)
    g.set(17, 5, PANEL)
    g.set(19, 4, PANEL)
    g.hline(13, 15, 12, ACCENT)
    g.hline(13, 14, 13, ACCENT)
    outline(g, ACCENT)
    # Strokes inside the mass, so the fire reads as flames and not as a wig.
    g.hline(18, 19, 9, INK)
    g.hline(15, 16, 10, INK)
    g.hline(21, 22, 10, INK)
    # A gold collar band across the chest, the fire carried down onto the robe.
    g.hline(13, HALF, 41, ACCENT)
    g.hline(13, HALF, 42, INK)
    return g


BUILDERS = {
    "guard": guard_grid,
    "percy": percy_grid,
    "prometheus": prometheus_grid,
}


def palette_hex(root=PALETTE_JSON):
    with open(root, "r", encoding="utf-8-sig") as handle:
        document = json.load(handle)
    return {entry["code"]: entry["hex"] for entry in document["entries"]}


def rgba(hex_colour):
    value = hex_colour.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)


def prometheus_licks(g):
    """Two tongues above the mirrored mass, off centre, so the hair reads as fire rather than as a gold crown.

    Everything else on this sheet is drawn as a left half and mirrored, which is what keeps a face from going lopsided
    by one pixel. Fire is the one thing that must NOT be symmetric: a symmetric three tip mass above a face is a crown,
    which is what the first draft looked like at 6x. The tongues and the notches below are placed after the mirror, on
    the right of the axis only.
    """
    # Tongue one, four pixels above the mass's top edge, and tongue two taller and further right. Both start clear of
    # the frame's inner row by one panel pixel, because an ink outline that touches the frame reads as a stray line.
    for y in range(3, 5):
        g.set(25, y, ACCENT)
    for y in range(2, 6):
        g.set(28, y, ACCENT)
    # Notches cut into the top edge, right side only: the staircase between the tongues is what makes them read as
    # separate licks. They are cut to the panel, not to transparency, because the panel is what is behind the fire.
    g.set(24, 4, PANEL)
    g.set(30, 5, PANEL)
    g.set(30, 6, PANEL)
    outline(g, ACCENT)


def build(name):
    """One bust as a Grid: left half drawn, mirrored, the one asymmetric detail, frame last."""
    grid = BUILDERS[name]()
    grid.mirror_x()
    if name == "prometheus":
        prometheus_licks(grid)
    draw_frame(grid)
    return grid, BUSTS[name]


def audit(name, grid, pal, hexes):
    """Every rule the bust has to pass, as a list of problems. Empty means the sheet is legal."""
    problems = []
    roles = {PANEL: PANEL_CODE, ACCENT: pal["accent"], SKIN: pal["skin"], INK: INK_CODE}
    if len(set(roles.values())) > 4:
        problems.append("%s spends %d entries, a bust may spend 4" % (name, len(set(roles.values()))))
    for role, code in roles.items():
        if code not in hexes:
            problems.append("%s names %s for %s, which data/nes_palette.json does not carry" % (name, code, role))

    # The frame: every pixel of the outermost ring, nothing missing.
    for x in range(SIZE):
        for y in (0, SIZE - 1):
            if grid.get(x, y) != ACCENT:
                problems.append("%s misses its frame at %d,%d" % (name, x, y))
    for y in range(SIZE):
        for x in (0, SIZE - 1):
            if grid.get(x, y) != ACCENT:
                problems.append("%s misses its frame at %d,%d" % (name, x, y))

    # Nothing transparent inside the frame: a portrait, not a hole in the level.
    for y in range(1, SIZE - 1):
        for x in range(1, SIZE - 1):
            if grid.get(x, y) is None:
                problems.append("%s leaves %d,%d transparent inside its frame" % (name, x, y))

    # The tile budget: a sprite tile carries 3 opaque colours plus transparency.
    for ty in range(SIZE // TILE):
        for tx in range(SIZE // TILE):
            seen = set()
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    cell = grid.get(x, y)
                    if cell:
                        seen.add(cell)
            if len(seen) > 3:
                problems.append("%s tile %d,%d carries %d colours: %s"
                                % (name, tx, ty, len(seen), ", ".join(sorted(seen))))

    # A bust has to be a bust: a face, an accent mass over it, and a shoulder line on the last row of the frame.
    if grid.count(SKIN) < 150:
        problems.append("%s has %d skin pixels, which is not a face" % (name, grid.count(SKIN)))
    if grid.count(ACCENT) < 150:
        problems.append("%s has %d accent pixels, which is not hair or a helmet" % (name, grid.count(ACCENT)))
    if not any(grid.get(x, SIZE - 2) == INK for x in range(1, SIZE - 1)):
        problems.append("%s has no shoulder line on its last row, so it does not stand on the box" % name)
    return problems


def render(grid, pal, hexes):
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    pixels = image.load()
    codes = {PANEL: PANEL_CODE, ACCENT: pal["accent"], SKIN: pal["skin"], INK: INK_CODE}
    for y in range(SIZE):
        for x in range(SIZE):
            cell = grid.get(x, y)
            if cell:
                pixels[x, y] = rgba(hexes[codes[cell]])
    return image


def write(name, image):
    png = os.path.join(OUT_DIR, "spr_pp_portrait_%s.png" % name)
    meta = os.path.join(OUT_DIR, "spr_pp_portrait_%s.json" % name)
    image.save(png)
    sidecar = {
        "name": "spr_pp_portrait_%s" % name,
        "frame_w": SIZE,
        "frame_h": SIZE,
        "frames": 1,
        "fps": FPS,
    }
    with open(meta, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(sidecar, handle, indent=2)
        handle.write("\n")
    return png, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", action="store_true", help="print every frame as ASCII after building it")
    parser.add_argument("--audit", action="store_true", help="print the per tile audit after building it")
    args = parser.parse_args()

    hexes = palette_hex()
    legend = {PANEL: "n", ACCENT: "+", SKIN: "s", INK: "#"}
    os.makedirs(OUT_DIR, exist_ok=True)

    problems = []
    for name in sorted(BUILDERS):
        grid, pal = build(name)
        found = audit(name, grid, pal, hexes)
        problems.extend(found)
        image = render(grid, pal, hexes)
        png, meta = write(name, image)
        colours = sorted({hexes[c] for c in (PANEL_CODE, pal["accent"], pal["skin"], INK_CODE)})
        print("%-11s %dx%d  %d colours  %s" % (name, image.width, image.height, len(colours),
                                              "ok" if not found else "%d problem(s)" % len(found)))
        print("            %s" % os.path.relpath(png, ROOT).replace(os.sep, "/"))
        print("            panel %s accent %s skin %s ink %s" % (PANEL_CODE, pal["accent"], pal["skin"], INK_CODE))
        if args.dump:
            for line in grid.dump(legend):
                print("            " + line)
        if args.audit:
            for ty in range(SIZE // TILE):
                row = []
                for tx in range(SIZE // TILE):
                    seen = set()
                    for y in range(ty * TILE, ty * TILE + TILE):
                        for x in range(tx * TILE, tx * TILE + TILE):
                            cell = grid.get(x, y)
                            if cell:
                                seen.add(cell)
                    row.append(str(len(seen)))
                print("            tile row %d: colours per tile %s" % (ty, " ".join(row)))

    if problems:
        print("")
        for problem in problems:
            print("FAIL %s" % problem)
        return 1
    print("")
    print("every bust: 48x48, 4 entries, 1 pixel frame, at most 3 colours in any 8x8 tile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
