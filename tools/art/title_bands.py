#!/usr/bin/env python3
"""title_bands.py: the title frame's colours, decided once per 16-px row band.

Why this exists
---------------
A NES frame gives each 16x16 attribute area one of four background palettes of three colours plus the one
shared backdrop, and the PPU cannot switch palette part way down an area. The title is seven scrolling
layers, a logo, a car, a headlight cone, a rain cloud, a road sign and a menu box drawn over each other,
and each of those passed the area rule alone while the frame did not (card t_a1170172, measured
2026-10-22: 25 of 240 areas carried four or five colours, and two blended colours no PPU can output).

The fix has to hold while the world scrolls, not just at one camera position. The layers move along x
and nothing moves along y, so a 16-px row band of the *screen* always takes its pixels from the same
16-px row band of a strip. That makes the row band the stable unit, and this module is the only thing
allowed to decide which palette a band gets:

    data/palettes/scene_title.json   "bands": one palette name per 16-px band, top to bottom
                                     "band_sprites": which palette each sprite is drawn inside

Every layer strip is repainted so that a row band only contains its palette's three colours (or the
black backdrop), and every sprite is repainted into the one palette that all the bands it can touch
share. What lands on disk is then inside the budget at every scroll offset, which is what
tools/nes_composite_check.py measures afterwards from the pixels, without using anything this module
knows.

Two paint modes, both deterministic:
    nearest    a pixel takes the closest colour of its band's palette. Used for the base art.
    brighter   a pixel takes its closest palette colour and then the next brighter one in that palette.
               Used for the *_flash strips, so a lightning frame is still a lift of the drive and is
               still inside the budget (the old one-rung-up 2C02 ladder left the palette entirely).

Clean room: the rules are published hardware behaviour (PPU palettes, PPU attribute tables, OAM). The
code is our own. No art, palette or data from any published game is read or reproduced here.

Usage:
    python tools\\art\\title_bands.py apply      # repaint the title art into its band plan
    python tools\\art\\title_bands.py show       # print the plan and what each band spends
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scene_palette  # noqa: E402  (the scene file's loader and the master palette)

BAND = 16
ROWS = 240 // BAND


def luma(rgb) -> float:
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def nearest(rgb, choices):
    """The closest colour in choices by squared RGB distance; ties go to the lower value, so it is stable."""
    best = None
    best_distance = None
    for choice in choices:
        distance = sum((int(a) - int(b)) ** 2 for a, b in zip(rgb[:3], choice[:3]))
        if best_distance is None or distance < best_distance or (distance == best_distance and choice < best):
            best, best_distance = choice, distance
    return best


def band_plan(scene) -> list:
    """The three colours of every 16-px row band, top to bottom, as RGB tuples."""
    payload = scene.payload.get("bands")
    if not isinstance(payload, dict):
        raise SystemExit("title_bands: data/palettes/scene_title.json has no \"bands\" section")
    names = payload.get("palette")
    if not isinstance(names, list) or len(names) != ROWS:
        raise SystemExit("title_bands: \"bands\".palette must name one palette per %d-px band, %d of them"
                         % (BAND, ROWS))
    by_name = {}
    for row in payload.get("background") or scene.payload["background"]:
        by_name[row["name"]] = [scene.rgb(int(entry)) for entry in row["colours"]]
    plan = []
    for index, name in enumerate(names):
        if name not in by_name:
            raise SystemExit("title_bands: band %d names palette %r, which the file does not declare" % (index, name))
        plan.append(by_name[name])
    return plan


def sprite_palettes(scene) -> dict:
    """{sprite name: [rgb, rgb, rgb]} for every sheet the title card draws."""
    payload = scene.payload.get("band_sprites")
    if not isinstance(payload, dict):
        raise SystemExit("title_bands: data/palettes/scene_title.json has no \"band_sprites\" section")
    by_name = {row["name"]: [scene.rgb(int(entry)) for entry in row["colours"]]
               for row in scene.payload["background"]}
    out = {}
    for name, wanted in payload.items():
        if name.startswith("_"):
            continue
        wanted_list = wanted if isinstance(wanted, list) else [wanted]
        sets = []
        for palette_name in wanted_list:
            if palette_name not in by_name:
                raise SystemExit("title_bands: %s asks for palette %r, which the file does not declare"
                                 % (name, palette_name))
            sets.append(set(by_name[palette_name]))
        shared = set.intersection(*sets)
        if not shared:
            raise SystemExit("title_bands: %s spans palettes %s, which share no colour" % (name, wanted_list))
        out[name] = sorted(shared)
    return out


def map_image(image: Image.Image, rows, backdrop, mode: str = "nearest") -> int:
    """Repaint one sheet. rows is a list of palettes indexed by pixel row, or a single palette for every row."""
    pixels = image.load()
    moved = 0
    single = not isinstance(rows, list) or (rows and not isinstance(rows[0], list))
    cache = {}
    for y in range(image.height):
        palette = rows if single else rows[y]
        key = (palette[0], palette[-1], id(palette), mode)
        ordered = None
        if key in cache:
            ordered = cache[key]
        else:
            ordered = sorted(palette, key=lambda rgb: (luma(rgb), rgb))
            cache[key] = ordered
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            rgb = (r, g, b)
            if rgb == backdrop:
                continue
            base = nearest(rgb, palette)
            target = base
            if mode == "brighter":
                position = ordered.index(base)
                target = ordered[position + 1] if position + 1 < len(ordered) else ordered[position]
            if target != rgb:
                pixels[x, y] = target + (a,)
                moved += 1
    return moved


def layer_rows(root: str, name: str, table: dict, plan: list):
    """The band palette for every art row of one layer, from the y the layer is drawn at."""
    y = 0
    for row in table["layers"] + table.get("backgrounds", []):
        if row["name"] == name:
            y = int(row.get("y", 0))
            break
    out = []
    for art_row in range(0, 4096):
        band = (y + art_row) // BAND
        out.append(plan[band] if 0 <= band < ROWS else plan[ROWS - 1])
        if art_row >= 240:
            break
    return out


def apply(root: str) -> dict:
    """Repaint every title sheet into the band plan. Returns what moved, per sheet."""
    scene = scene_palette.load_scene(root, "title")
    plan = band_plan(scene)
    backdrop = tuple(scene.rgb(scene.backdrop))
    with open(os.path.join(root, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    report = {"bands": [], "layers": {}, "sprites": {}, "flash": {}}

    names = [row["name"] for row in table["layers"] + table.get("backgrounds", [])]
    ys = {row["name"]: int(row.get("y", 0)) for row in table["layers"] + table.get("backgrounds", [])}
    for name in names:
        rows = layer_rows(root, name, table, plan)
        png = os.path.join(root, "game", "sprites_src", "title", name + ".png")
        if not os.path.isfile(png):
            continue
        image = Image.open(png).convert("RGBA")
        moved = map_image(image, rows, backdrop, "nearest")
        image.save(png, "PNG")
        report["layers"][name] = {"pixels_moved": moved, "y": ys.get(name, 0)}

    # The flash strips are the same picture lifted inside the band palette. They are written after the base
    # strips, from the base strips as they are on disk now, so the two can never disagree.
    for name in names:
        flash_png = os.path.join(root, "game", "sprites_src", "title", name + "_flash.png")
        base_png = os.path.join(root, "game", "sprites_src", "title", name + ".png")
        if not (os.path.isfile(flash_png) and os.path.isfile(base_png)):
            continue
        rows = layer_rows(root, name, table, plan)
        image = Image.open(base_png).convert("RGBA")
        moved = map_image(image, rows, backdrop, "brighter")
        image.save(flash_png, "PNG")
        report["flash"][name + "_flash"] = {"pixels_moved": moved}

    for name, palette in sprite_palettes(scene).items():
        png = os.path.join(root, "game", "sprites_src", "title", name + ".png")
        if not os.path.isfile(png):
            continue
        image = Image.open(png).convert("RGBA")
        moved = map_image(image, palette, backdrop, "nearest")
        image.save(png, "PNG")
        report["sprites"][name] = {"pixels_moved": moved,
                                   "palette": ["#%02x%02x%02x" % rgb for rgb in palette]}

    for band, palette in enumerate(plan):
        report["bands"].append({"band": band, "y": band * BAND,
                                "colours": ["#%02x%02x%02x" % rgb for rgb in palette]})
    return report


def paint_sheet(root: str, name: str) -> int:
    """Repaint one sheet in root with the band palette the committed scene file gives it.

    The palette is read from THIS tool's repository, not from root, because it is a design input rather than an
    output: a generator pointed at a bare tree still has to write the colours the title frame will spend. Card
    t_a1170172.
    """
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    scene = scene_palette.load_scene(repo, "title")
    palettes = sprite_palettes(scene)
    if name not in palettes:
        return 0
    png = os.path.join(root, "game", "sprites_src", "title", name + ".png")
    if not os.path.isfile(png):
        return 0
    image = Image.open(png).convert("RGBA")
    moved = map_image(image, palettes[name], tuple(scene.rgb(scene.backdrop)), "nearest")
    image.save(png, "PNG")
    return moved


def flash_pairs(root: str) -> dict:
    """{source 2C02 entry: flash 2C02 entry} read off the strips on disk, pixel for pixel.

    Card t_a1170172: the flash twin used to be built by lifting each colour one rung up the whole 2C02 ladder, which
    after the band plan is a frame the chip cannot show: the lifted entry may belong to another band's palette. The
    twin is now the same picture lifted inside its own band palette, so the table the game swaps by has to be read
    back off the two sheets rather than computed from the ladder.
    """
    scene = scene_palette.load_scene(root, "title")
    index_of = {}
    for entry in range(64):
        index_of.setdefault(tuple(scene.rgb(entry)), entry)
    with open(os.path.join(root, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    pairs = {}
    counts = {}
    for row in table["layers"] + table.get("backgrounds", []):
        base_png = os.path.join(root, "game", "sprites_src", "title", row["name"] + ".png")
        flash_png = os.path.join(root, "game", "sprites_src", "title", row["name"] + "_flash.png")
        if not (os.path.isfile(base_png) and os.path.isfile(flash_png)):
            continue
        base = Image.open(base_png).convert("RGBA")
        twin = Image.open(flash_png).convert("RGBA")
        for y in range(min(base.height, twin.height)):
            for x in range(min(base.width, twin.width)):
                r, g, b, a = base.getpixel((x, y))
                fr, fg, fb, fa = twin.getpixel((x, y))
                if not a:
                    continue
                source = index_of.get((r, g, b))
                target = index_of.get((fr, fg, fb))
                if source is None or target is None:
                    continue
                key = (source, target)
                counts[key] = counts.get(key, 0) + 1
    for (source, target), count in sorted(counts.items(), key=lambda item: -item[1]):
        if source not in pairs:
            pairs[source] = target
    return pairs


def show(root: str) -> int:
    scene = scene_palette.load_scene(root, "title")
    plan = band_plan(scene)
    print("title bands, %d px each, backdrop #%02x%02x%02x" % (BAND, *(scene.rgb(scene.backdrop))))
    for band, palette in enumerate(plan):
        print("  band %2d y%3d-%3d  %s" % (band, band * BAND, band * BAND + BAND - 1,
                                           " ".join("#%02x%02x%02x" % rgb for rgb in palette)))
    print("sprites:")
    for name, palette in sorted(sprite_palettes(scene).items()):
        print("  %-24s %s" % (name, " ".join("#%02x%02x%02x" % rgb for rgb in palette)))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Repaint the title art into its per-band palette plan.")
    parser.add_argument("action", choices=("apply", "show"))
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    args = parser.parse_args(argv)
    if args.action == "show":
        return show(args.root)
    report = apply(args.root)
    layers = sum(row["pixels_moved"] for row in report["layers"].values())
    flash = sum(row["pixels_moved"] for row in report["flash"].values())
    sprites = sum(row["pixels_moved"] for row in report["sprites"].values())
    print("title bands: %d layer sheet(s) repainted, %d pixels; %d flash sheet(s), %d pixels; "
          "%d sprite sheet(s), %d pixels"
          % (len(report["layers"]), layers, len(report["flash"]), flash, len(report["sprites"]), sprites))
    return 0


if __name__ == "__main__":
    sys.exit(main())
