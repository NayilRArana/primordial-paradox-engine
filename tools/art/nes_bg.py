#!/usr/bin/env python3
"""The NES background rule for the title layers, as a solver and as an independent checker.

Clean room: the rule itself is a hardware fact, published in every NES programming guide: a background
tilemap is a grid of 16x16 attribute areas, and each area draws from one palette of three colours plus
one shared backdrop colour that every area may use. Nothing here is copied from any game; the code is
plain geometry (counting, nearest colour by RGB distance) written for this project.

Two entry points, deliberately separate so one cannot hide the other's mistakes:

  reduce_areas()  the SOLVER. It walks each 16x16 area of a strip, keeps the dominant colour plus the
                  colours a priority list names, and remaps every other pixel to the nearest kept colour.
                  This is what turns a drawing into something the cartridge can hold.

  check_areas()   the CHECKER. It counts the colours in each area and nothing else. It never looks at
                  the solver's choices, so a strip that passes here really does satisfy the rule.

The role of a strip decides which rule applies. A background layer is held to the 16x16 rule above. A
sprite is held to the 8x8 rule in nes_tile.py (three colours plus transparency per 8x8 tile). The layer
table lives in data\\title.json, which is also what the game reads at runtime, so the art and the engine
cannot drift apart.

Usage:
    python tools/art/nes_bg.py check --root <repo>
    python tools/art/nes_bg.py check --root <repo> --layer title_L1_sky
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

AREA = 16          # the NES background attribute area
LIMIT = 3          # colours per area, besides the shared backdrop
TRANSPARENT = 255  # the index value the art tools use for "no pixel"


def load_palette(root: str):
    """Return (colours, index_of): colours is a list of (r, g, b), index_of maps an rgb triple to its index.

    This is data\\palette.json, the project's drawing palette: the space the strips are drawn in before
    they are snapped to the chip. The solver needs it; the checker must not use it (see load_chip_palette).
    """
    path = os.path.join(root, "data", "palette.json")
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = []
    index_of = {}
    for index, value in enumerate(data["colours"]):
        value = value.lstrip("#")
        rgb = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
        colours.append(rgb)
        index_of[rgb] = index
    return colours, index_of


def load_chip_palette(root: str):
    """Return (colours, index_of) for the palette the cartridge can actually show: data\\nes_palette.json.

    The generator snaps every strip onto the Ricoh 2C02's own outputs before it writes it (tools\\art\\
    nes_snap.py), and data\\title.json records each layer's backdrop as a 2C02 entry number. So the
    checker has to read that same space, or it would fail every shipped pixel against the project's
    drawing palette and compare backdrop numbers from two different palettes. Falls back to the project
    palette only when the chip palette file is absent, so a tree without it still gets an answer.

    index_of prefers a usable entry over a forbidden duplicate: the 2C02 repeats black several times and
    only $0F may be drawn with, and an area's own colour must never be read as its backdrop.
    """
    path = os.path.join(root, "data", "nes_palette.json")
    if not os.path.isfile(path):
        return load_palette(root)
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = []
    for value in data["colours"]:
        value = value.lstrip("#")
        colours.append((int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)))
    flags = data.get("usable")
    if not isinstance(flags, list) or len(flags) != len(colours):
        flags = [index != 0x0D and not (rgb == (0, 0, 0) and index != 0x0F)
                 for index, rgb in enumerate(colours)]
    index_of = {}
    for index, rgb in enumerate(colours):
        if flags[index] and rgb not in index_of:
            index_of[rgb] = index
    for index, rgb in enumerate(colours):
        index_of.setdefault(rgb, index)
    return colours, index_of


def area_boxes(width: int, height: int, cell: int = AREA):
    """Every attribute area of one frame, as (cx, cy, x0, y0, x1, y1) with x1 and y1 inclusive."""
    for cy in range((height + cell - 1) // cell):
        for cx in range((width + cell - 1) // cell):
            x0 = cx * cell
            y0 = cy * cell
            yield cx, cy, x0, y0, min(width - 1, x0 + cell - 1), min(height - 1, y0 + cell - 1)


def _pixels(image: Image.Image):
    """Yield (x, y, rgb or None) for one frame, in row order."""
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            yield x, y, None if a == 0 else (r, g, b)


def area_colours(image: Image.Image, index_of):
    """The palette indices each 16x16 area of one frame carries. Transparent pixels are not counted."""
    seen = {}
    for cx, cy, x0, y0, x1, y1 in area_boxes(image.width, image.height):
        found = set()
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                r, g, b, a = image.getpixel((x, y))
                if a == 0:
                    continue
                index = index_of.get((r, g, b))
                if index is not None:
                    found.add(index)
        if found:
            seen[(cx, cy)] = found
    return seen


def check_areas(image: Image.Image, index_of, backdrop=None, limit: int = LIMIT):
    """Every area that breaks the background rule, as (cx, cy, sorted colours).

    An area may carry `limit` colours plus the shared backdrop. The backdrop is exempt because on the
    cartridge it is the one colour every area is allowed to share.
    """
    bad = []
    for (cx, cy), found in sorted(area_colours(image, index_of).items()):
        counted = found - {backdrop} if backdrop is not None else found
        if len(counted) > limit:
            bad.append((cx, cy, sorted(found)))
    return bad


def reduce_areas(image: Image.Image, index_of, colours, backdrop=None, limit: int = LIMIT, priority=()):
    """Force every 16x16 area down to `limit` colours plus the backdrop. Returns (new image, changed pixels).

    The kept colours are the dominant colour of the area plus the colours the priority list names
    first, so an accent such as a lit window survives and a background tone does not. Dropped pixels
    move to the nearest kept colour by RGB distance, and a tie goes to the lower index, so the result
    is deterministic.
    """
    rank = {index: order for order, index in enumerate(priority)}
    pixels = image.load()
    changed = 0
    for cx, cy, x0, y0, x1, y1 in area_boxes(image.width, image.height):
        counts = {}
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                r, g, b, a = pixels[x, y]
                if a == 0:
                    continue
                index = index_of.get((r, g, b))
                if index is None:
                    continue
                counts[index] = counts.get(index, 0) + 1
        if not counts:
            continue
        counted = {index: n for index, n in counts.items() if index != backdrop} if backdrop is not None else counts
        if len(counted) <= limit:
            continue
        dominant = max(counted, key=lambda index: (counted[index], -index))
        rest = [index for index in counted if index != dominant]
        rest.sort(key=lambda index: (rank.get(index, 99), -counted[index], index))
        keep = [dominant] + rest[:limit - 1]
        keep_set = set(keep)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                r, g, b, a = pixels[x, y]
                if a == 0:
                    continue
                index = index_of.get((r, g, b))
                if index is None or index in keep_set or (backdrop is not None and index == backdrop):
                    continue
                best = min(keep, key=lambda k: (
                    (colours[index][0] - colours[k][0]) ** 2
                    + (colours[index][1] - colours[k][1]) ** 2
                    + (colours[index][2] - colours[k][2]) ** 2, k))
                pixels[x, y] = colours[best] + (255,)
                changed += 1
    return image, changed


def load_title_table(root: str):
    """The layer table the art and the game share: data\\title.json."""
    path = os.path.join(root, "data", "title.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def layer_entries(root: str):
    """Every background layer, as (name, backdrop) pairs, from data\\title.json.

    Two lists are read: `layers` (the seamless strips the screen scrolls) and `backgrounds` (the still
    pictures such as the opening shot). Both are backgrounds to the hardware, so both are held to the
    16x16 rule; the list they sit in only tells the runtime how to draw them.
    """
    table = load_title_table(root)
    out = []
    for key in ("layers", "backgrounds"):
        for row in table.get(key, []) or []:
            if not isinstance(row, dict):
                continue
            if row.get("role", "background") != "background":
                continue
            out.append((row.get("name"), row.get("backdrop")))
    return out


def load_strip(root: str, name: str):
    """One animation strip and its sidecar, from game\\sprites_src\\title."""
    base = os.path.join(root, "game", "sprites_src", "title", name)
    with open(base + ".json", "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    with Image.open(base + ".png") as handle:
        image = handle.convert("RGBA")
    return image, meta


def check(root: str, only=None) -> int:
    # The pixels on disk are 2C02 outputs and the backdrop numbers in data\title.json are entry
    # numbers, so the checker reads the chip palette; the solver's drawing palette is a different space.
    colours, index_of = load_chip_palette(root)
    problems = []
    entries = layer_entries(root)
    if not entries:
        print("data/title.json names no background layer, so there is nothing to check")
        return 1
    print("NES background rule: 16x16 areas, %d colours plus the shared backdrop" % LIMIT)
    for name, backdrop in entries:
        if only and name != only:
            continue
        if not name:
            problems.append("data/title.json has a layer with no name")
            continue
        try:
            image, meta = load_strip(root, name)
        except (OSError, ValueError) as exc:
            problems.append("%s: cannot read the strip (%s)" % (name, exc))
            continue
        frames = image.width // meta["frame_w"]
        bad = []
        for frame in range(frames):
            one = image.crop((frame * meta["frame_w"], 0,
                              (frame + 1) * meta["frame_w"], meta["frame_h"]))
            bad = check_areas(one, index_of, backdrop)
            for cx, cy, found in bad:
                problems.append("%s frame %d area %d,%d carries %d colours %s"
                                % (name, frame, cx, cy, len(found), found))
        # every pixel must be a master palette entry
        stray = 0
        for _, _, rgb in _pixels(image):
            if rgb is not None and rgb not in index_of:
                stray += 1
        if stray:
            problems.append("%s has %d pixels that are not master palette entries" % (name, stray))
        print("  %-18s %3dx%-3d %d frame(s)  backdrop %s  %s"
              % (name, meta["frame_w"], meta["frame_h"], frames,
                 "none" if backdrop is None else backdrop,
                 "OK" if not bad else "FAIL"))
    if problems:
        for line in problems:
            print("FAIL " + line)
        print("\n%d background rule problem(s)" % len(problems))
        return 1
    print("\nevery background layer holds to the 16x16 rule")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    parser.add_argument("--layer", default=None)
    args = parser.parse_args()
    root = os.path.abspath(args.root)
    if args.command == "check":
        return check(root, args.layer)
    return 2


if __name__ == "__main__":
    sys.exit(main())
