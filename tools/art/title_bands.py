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

# The sheets that spend the backdrop colour as an INK, so the band pass leaves their black pixels alone: the wordmark's
# 1 px outline, which specs/13-8bit-look.md:19 requires, and the menu window's field, which is the backdrop by design.
# Every other sprite has the backdrop repainted into its band palette: a sprite's fourth state is transparency, so black
# in a sprite is one of its three entries and a group that carries it outside a declared palette is a group the frame
# cannot draw (card t_a1170172, review round 1 item 1).
BACKDROP_INK = ("spr_pp_title_logo", "spr_pp_window")


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


def lifted(rgb, palette, ordered):
    """The flash colour for one pixel: its nearest palette entry, then the next brighter one in that palette."""
    base = nearest(rgb, palette)
    position = ordered.index(base)
    return ordered[position + 1] if position + 1 < len(ordered) else ordered[position]


def map_image(image: Image.Image, rows, backdrop, mode: str = "nearest", keep_backdrop: bool = True) -> int:
    """Repaint one sheet. rows is a list of palettes indexed by pixel row, or a single palette for every row.

    `keep_backdrop` says whether a pixel painted in the shared backdrop colour is left alone. A background layer and
    the two sheets that spend black as an ink (the wordmark's outline, the menu window's field) want that; any other
    sprite does not, because a sprite's fourth state is transparency and black in its palette is a real entry, so
    pixels the generator drew in the project's near black have to be repainted into the sheet's own palette or its 8x16
    group fits no sprite palette at all (card t_a1170172: the car's tyres).

    Partial alpha is resolved here too, before anything is repainted. A repaint keeps the alpha it found, so this pass
    inherited the exhaust's and the cloud's half transparent puffs unchanged, and the game then drew them over the
    road: the captured frame carried #616161, #001923 and #619761, the three values those puffs blend to, none of them
    a PPU entry (measured 2026-10-22, 24 pixels at x81-86 y211-219). A NES sprite pixel is on or off, so every sheet
    this pass writes leaves here with alpha 0 or 255 and the dither `nes_tile.solid_alpha` describes is what a fade
    uses instead. card t_a1170172, review round 2.
    """
    if image.getchannel("A").getextrema() != (255, 255):
        image.paste(scene_palette.nes_tile.solid_alpha(image))
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
            if keep_backdrop and rgb == backdrop:
                continue
            target = lifted(rgb, palette, ordered) if mode == "brighter" else nearest(rgb, palette)
            if target != rgb:
                pixels[x, y] = target + (a,)
                moved += 1
    return moved


def sheet_pairs(image: Image.Image, rows, backdrop, scene) -> dict:
    """{source 2C02 entry: [the targets it lifts to on this strip, most used first]}.

    The lift is per band, and one strip covers fifteen of them, so a source entry can lift to a different target on a
    different row of the same strip. What a strip does is therefore measured, not computed once for the frame: this is
    the reading the flash table is written from, and it is why the table lists targets rather than one target.
    """
    pixels = image.load()
    single = not isinstance(rows, list) or (rows and not isinstance(rows[0], list))
    cache = {}
    counts = {}
    for y in range(image.height):
        palette = rows if single else rows[y]
        key = (palette[0], palette[-1], id(palette))
        ordered = cache.get(key)
        if ordered is None:
            ordered = sorted(palette, key=lambda rgb: (luma(rgb), rgb))
            cache[key] = ordered
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            rgb = (r, g, b)
            if rgb == backdrop:
                continue
            source = scene.entry_of(rgb)
            target = scene.entry_of(lifted(rgb, palette, ordered))
            if source is None or target is None:
                continue
            counts[(source, target)] = counts.get((source, target), 0) + 1
    pairs = {}
    for (source, target), count in counts.items():
        pairs.setdefault(source, []).append((-count, target))
    return {source: [target for _count, target in sorted(targets)]
            for source, targets in sorted(pairs.items())}


def write_flash_table(root: str, table: dict, pairs_by_layer: dict, layer_flash: list) -> str:
    """Write data/title_flash.json from the two sheets of every strip that has a twin.

    Shape 2. A single table over entries cannot describe the flash, because the lift happens inside the band palette
    and the bands differ: $00 grey lifts to $28 gold on the sky band and to $20 white on the ground, and both are true
    on the same strip. So `by_layer` gives, for one strip, every target a source entry lifts to there, most used
    first, and `palette` keeps the one-target summary a reader wants at a glance. Card t_a1170172.
    """
    flat = {}
    weight = {}
    for pairs in pairs_by_layer.values():
        for source, targets in pairs.items():
            for rank, target in enumerate(targets):
                key = (source, target)
                weight[key] = weight.get(key, 0) + (len(targets) - rank)
    for (source, target), count in sorted(weight.items()):
        if source not in flat or count > weight[(source, flat[source])]:
            flat[source] = target
    payload = {
        "format": 2,
        "kind": "title_flash",
        "frames": 2,
        "layers": list(layer_flash),
        "by_layer": {name: {str(source): targets for source, targets in sorted(pairs.items())}
                     for name, pairs in sorted(pairs_by_layer.items())},
        "palette": {str(source): target for source, target in sorted(flat.items())},
        "palette_space": "2C02 entry numbers (data/nes_palette.json)",
        "note": "the flash is the same picture lifted one rung brighter inside the palette of the 16 px band each "
                "row of the strip is drawn in. A strip covers fifteen bands, so one source entry can lift to more "
                "than one target on the same strip: `by_layer` lists them, most used first, read off the strip and "
                "its `_flash` twin on disk; `palette` is the flat summary. The runtime swaps the whole scene to the "
                "twin sheets for two frames rather than swapping entries",
        "derived_by": "tools/art/title_bands.py apply, from game/sprites_src/title/<layer>.png and _flash.png",
        "source": table.get("flash", {}).get("file", "title_flash.json"),
    }
    path = os.path.join(root, "data", "title_flash.json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return path


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
    pairs_by_layer = {}
    for name in names:
        flash_png = os.path.join(root, "game", "sprites_src", "title", name + "_flash.png")
        base_png = os.path.join(root, "game", "sprites_src", "title", name + ".png")
        if not (os.path.isfile(flash_png) and os.path.isfile(base_png)):
            continue
        rows = layer_rows(root, name, table, plan)
        image = Image.open(base_png).convert("RGBA")
        pairs_by_layer[name + "_flash"] = sheet_pairs(image, rows, backdrop, scene)
        moved = map_image(image, rows, backdrop, "brighter")
        image.save(flash_png, "PNG")
        report["flash"][name + "_flash"] = {"pixels_moved": moved,
                                            "pairs": len(pairs_by_layer[name + "_flash"])}

    for name, palette in sprite_palettes(scene).items():
        png = os.path.join(root, "game", "sprites_src", "title", name + ".png")
        if not os.path.isfile(png):
            continue
        image = Image.open(png).convert("RGBA")
        moved = map_image(image, palette, backdrop, "nearest", keep_backdrop=name in BACKDROP_INK)
        image.save(png, "PNG")
        report["sprites"][name] = {"pixels_moved": moved,
                                   "palette": ["#%02x%02x%02x" % rgb for rgb in palette]}

    for band, palette in enumerate(plan):
        report["bands"].append({"band": band, "y": band * BAND,
                                "colours": ["#%02x%02x%02x" % rgb for rgb in palette]})

    # The table the game and the tests read is derived here, off the two sheets that just shipped, because the
    # lift is per band: one source entry lifts to a different target in a different band, which no single table
    # over entries can express. Card t_a1170172 wrote the table off the whole 2C02 ladder instead, so it described
    # a swap the strips do not make and tests/test_make_title_world.py was right to refuse it.
    layer_flash = [name + "_flash" for name in names if name + "_flash" in pairs_by_layer]
    if layer_flash:
        write_flash_table(root, table, pairs_by_layer, layer_flash)
        report["flash_table"] = os.path.join(root, "data", "title_flash.json")
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
    moved = map_image(image, palettes[name], tuple(scene.rgb(scene.backdrop)), "nearest",
                      keep_backdrop=name in BACKDROP_INK)
    image.save(png, "PNG")
    return moved


def flash_pairs(root: str) -> dict:
    """{source 2C02 entry: flash 2C02 entry} across every strip on disk, the flat summary only.

    Kept for callers that want one number per entry; the authoritative reading is `apply`, which measures
    each strip separately and writes data/title_flash.json with `by_layer`. See `sheet_pairs`.
    """
    scene = scene_palette.load_scene(root, "title")
    plan = band_plan(scene)
    backdrop = tuple(scene.rgb(scene.backdrop))
    with open(os.path.join(root, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        table = json.load(handle)
    pairs = {}
    for row in table["layers"] + table.get("backgrounds", []):
        base_png = os.path.join(root, "game", "sprites_src", "title", row["name"] + ".png")
        if not os.path.isfile(base_png):
            continue
        image = Image.open(base_png).convert("RGBA")
        rows = layer_rows(root, row["name"], table, plan)
        for source, target in sheet_pairs(image, rows, backdrop, scene).items():
            pairs.setdefault(source, target)
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
