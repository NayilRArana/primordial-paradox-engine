#!/usr/bin/env python3
"""nes_snap.py: put art drawn in the project palette onto the real 2C02 master palette.

Why this exists
---------------
data\\palette.json is the project's drawing palette: 9 hues by 6 levels, convenient to paint with, but its
hex values are the project's own and most of them are NOT outputs the Ricoh 2C02 can produce. The NES
validator (tools\\nes_check.py) checks pixels against data\\nes_palette.json, the 64 real outputs, so art
painted straight from data\\palette.json fails the palette rule even when the tile and area rules pass
(measured 2026-10-21: every title layer failed with "off palette at N pixels").

The mapping is curated, not computed. Nearest-colour search is the wrong tool here: the 2C02's dark end is
a handful of saturated entries (black, $02 indigo, $0C dark teal, the dark greens), so "nearest" hands a
dark blue-grey a dark green. NIGHT_TABLE below names the entry each project colour becomes, chosen to keep
the relationships the drawing code relies on (sky darker than horizon, structure darker than sky, grass
ramp in order). Any project colour missing from the table falls back to nearest usable entry.

Usage:
    python tools\\art\\nes_snap.py              # print the table, with the master hex for each entry
    python tools\\art\\nes_snap.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

MASTER = os.path.join("data", "nes_palette.json")
PROJECT = os.path.join("data", "palette.json")

# Project index -> 2C02 entry. The comment on each line is the role the drawing code gives the colour;
# see the palette block at the top of tools/art/make_title_world.py.
NIGHT_TABLE = {
    0: 0x0C,   # INK          #0b0b0f near black   -> $0C dark teal: silhouettes read against a black sky
    1: 0x0F,   # ASPHALT      #1c1c24 dark grey    -> $0F black: the road at night
    3: 0x00,   # DIM          #4a4a58 mid grey     -> $00 grey: cloud edges, lane shadow, stone trim
    5: 0x20,   # BRIGHT       #c8c8d4 pale grey    -> $20 white: stars, lane markings, chalk, moonlit edge
    6: 0x0F,   # SKY_DEEP     #081420 night sky    -> $0F black: the shared backdrop, as NES nights are
    7: 0x12,   # SKY_MID      #0d2b3a upper sky    -> $12 $0058f8: first blue band above the horizon
    8: 0x11,   # SKY_LOW      #11485c horizon glow -> $11 $0078f8: the lighter band the glow sits in
    25: 0x0B,  # GREEN_DEEP   #232a12 deep green   -> $0B $005800: the foot of the green ramp
    26: 0x0A,  # GREEN_MID    #3a4420 mid green    -> $0A $006800
    27: 0x09,  # GREEN_LIT    #55632f lit green    -> $09 $007800
    29: 0x1A,  # GREEN_PALE   #adbc74 verge grass  -> $1A $00a800: the moonlit verge band
    30: 0x02,  # STONE_DEEP   #14110f structure    -> $02 $0000bc: cathedral, poles, embankment
    32: 0x08,  # STONE_MID    #3b3226 dry stone    -> $08 $503000: the dry stone wall
    41: 0x38,  # GOLD         #e8c65a lit windows  -> $38 $f8d878: lit windows and the moon
}


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_rgb(value: str) -> tuple:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def load_master(root: str) -> tuple:
    """Return (colours, usable): colours[i] is the RGB output of entry $i, usable[i] says it may be used."""
    path = os.path.join(root, MASTER)
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = [read_rgb(value) for value in data["colours"]]
    flags = data.get("usable")
    if isinstance(flags, list) and len(flags) == len(colours):
        usable = [bool(flag) for flag in flags]
    else:
        usable = []
        for index, rgb in enumerate(colours):
            if index == 0x0D:
                usable.append(False)
            elif rgb == (0, 0, 0) and index != 0x0F:
                usable.append(False)
            else:
                usable.append(True)
    return colours, usable


def load_project(root: str) -> list:
    path = os.path.join(root, PROJECT)
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return [read_rgb(value) for value in data["colours"]]


def distance(a: tuple, b: tuple) -> int:
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return dr * dr * 2 + dg * dg * 4 + db * db * 3


def nearest(rgb: tuple, master: list, usable: list) -> int:
    """The nearest usable master entry, for a colour the table does not name."""
    best = None
    for index, candidate in enumerate(master):
        if not usable[index]:
            continue
        score = distance(rgb, candidate)
        if best is None or score < best[0] or (score == best[0] and index < best[1]):
            best = (score, index)
    return best[1]


def flash_step(entry: int) -> int:
    """The lightning frame: one rung up the 2C02's own ladder.

    The palette is laid out in rows of sixteen, each column one step lighter than the one above it
    ($0C dark teal, $1C teal, $2C pale teal), so a flash is the same picture drawn from entry + $10.
    Two exceptions the layout forces: the black column ($0F) has no lighter sibling and lifts to grey
    ($00), and the top row ($30 to $3D) is already the lightest the chip has, so it stays put. That is
    what makes the flash a palette swap the PPU really does rather than a computed brightening.
    """
    if entry == 0x0F:
        return 0x00
    row = entry >> 4
    if row >= 3:
        return entry
    return entry + 0x10


def flash_map(entries) -> dict:
    """{entry: flash entry} for every master entry in use."""
    return {entry: flash_step(entry) for entry in sorted(set(entries))}


def flash_image(image, master_index_of: dict, master: list, mapping: dict, transparent: int = 0):
    """The same picture drawn one palette rung up. Transparency is left alone."""
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            if a == transparent:
                continue
            index = master_index_of.get((r, g, b))
            if index is None:
                continue
            pixels[x, y] = master[mapping.get(index, index)] + (a,)
    return out


class Snap:
    """The table plus the two lookups a generator needs: by project index, and by RGB."""

    def __init__(self, root: str, table=None):
        self.master, self.usable = load_master(root)
        self.project = load_project(root)
        self.table = dict(NIGHT_TABLE if table is None else table)
        for source, target in self.table.items():
            if source < 0 or source >= len(self.project):
                raise SystemExit("nes_snap: project index %d is outside data/palette.json" % source)
            if target < 0 or target >= len(self.master):
                raise SystemExit("nes_snap: master entry $%02X does not exist" % target)
            if not self.usable[target]:
                raise SystemExit("nes_snap: master entry $%02X is flagged unusable" % target)
        self._by_rgb = {}
        for index in range(len(self.project)):
            self._by_rgb[self.project[index]] = self.table.get(index)

    def master_index(self, project_index: int) -> int:
        target = self.table.get(project_index)
        if target is not None:
            return target
        return nearest(self.project[project_index], self.master, self.usable)

    def rgb_for(self, project_index: int) -> tuple:
        return self.master[self.master_index(project_index)]

    def index_of_rgb(self, rgb: tuple) -> int:
        """Master entry for a pixel colour. Colours outside the project palette go to their nearest entry."""
        if rgb in self._by_rgb:
            target = self._by_rgb[rgb]
            if target is not None:
                return target
        return nearest(rgb, self.master, self.usable)

    def image(self, picture):
        """A copy of a PIL image with every opaque pixel moved onto a master output."""
        out = picture.copy()
        pixels = out.load()
        cache = {}
        for y in range(out.height):
            for x in range(out.width):
                r, g, b, a = pixels[x, y]
                if a == 0:
                    continue
                key = (r, g, b)
                target = cache.get(key)
                if target is None:
                    target = self.master[self.index_of_rgb(key)]
                    cache[key] = target
                pixels[x, y] = target + (a,)
        return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=repo_root())
    parser.add_argument("--json", dest="json_path", default=None)
    args = parser.parse_args(argv)

    snap = Snap(args.root)
    print("project index -> master entry   project hex -> master hex   role")
    targets = []
    for source in sorted(snap.table):
        target = snap.table[source]
        targets.append(target)
        print("  %2d -> $%02X  #%02x%02x%02x -> #%02x%02x%02x  %s"
              % ((source, target) + snap.project[source] + snap.master[target]))
    print("%d project colours onto %d master entries; every entry usable: %s"
          % (len(snap.table), len(set(targets)),
             all(snap.usable[target] for target in targets)))
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({str(key): value for key, value in sorted(snap.table.items())}, handle, indent=2)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
