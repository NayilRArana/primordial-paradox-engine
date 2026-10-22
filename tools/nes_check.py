"""nes_check.py: does this PNG obey the NES (Ricoh 2C02 PPU) drawing rules?

The rules, and where each one comes from:

1. Palette. Every visible pixel must be one of the PPU's outputs. The PPU palette is 64 values, $00 to
   $3F (NESdev wiki, "PPU palettes": https://www.nesdev.org/wiki/PPU_palettes). The list lives in
   data\\nes_palette.json, built and cited by tools\\art\\nes_palette_build.py. When the art bible lands
   (data\\art_bible.json, the ART-BIBLE card) that file names the working subset and this tool reads it
   instead, because a project may choose to paint from fewer colours than the chip can show.
2. Grid. NES art is 8x8 tiles, because the PPU fetches 8x8 pattern table tiles. A PNG whose width or
   height is not a multiple of 8 cannot be cut into tiles, so it fails.
3. Sprite tiles. A sprite pixel selects one of 4 colours in one of 4 sprite palettes, and entry 0 is
   transparent, so a single 8x8 sprite tile carries at most 3 opaque colours (wiki, "Palette RAM").
4. Background areas. The background is drawn through 16x16 attribute areas; each area picks one of 4
   background palettes, again with entry 0 of palette 0 as the backdrop, so a 16x16 area carries at
   most 3 colours plus the one shared backdrop colour.
5. Colours on screen. 4 background palettes of 3 colours plus a shared backdrop, 4 sprite palettes of 3
   colours plus that same backdrop: 12 + 12 + 1 = 25 is the ceiling for one frame. The tool counts the
   distinct colours in the image and fails above 25.

Exit code 0 when every rule passes, 1 when any rule fails. On failure the offending tiles are listed,
each with the colours it carries, so the fix is mechanical: read the list, repaint those tiles.

Usage:
    python tools\\nes_check.py game\\sprites_src\\title\\spr_pp_font8.png --type sprite
    python tools\\nes_check.py output\\frame.png --type background --backdrop "#000000"
    python tools\\nes_check.py strip.png --type sprite --palette data\\palette.json --json out.json

What it deliberately does not do: it does not judge whether the art is good, and it does not guess a
palette. If you point it at a palette file it trusts that file, so pass the right one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from PIL import Image

TILE = 8
AREA = 16
MAX_COLOURS_ON_SCREEN = 25
FRAME_W = 256
FRAME_H = 240


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# -----------------------------------------------------------------------------------------------------------------
# Palettes.

def palette_path(root: str, override: str | None = None) -> tuple:
    """The palette file to use, and why. The art bible wins when it exists, because it is the project's choice."""
    if override:
        return os.path.abspath(override), "the file named with --palette"
    bible = os.path.join(root, "data", "art_bible.json")
    if os.path.isfile(bible):
        return bible, "data\\art_bible.json, the art bible's working subset"
    return os.path.join(root, "data", "nes_palette.json"), "data\\nes_palette.json, the 2C02 palette"


def load_palette(path: str) -> dict:
    """Read a palette file. Accepts the 2C02 schema and the master palette schema, both plain hex lists."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    colours = data.get("colours")
    if colours is None and "palette" in data:
        colours = data["palette"]
    if not isinstance(colours, list) or not colours:
        raise SystemExit("%s has no colours list" % path)
    allowed = {}
    for position, value in enumerate(colours):
        if not isinstance(value, str):
            raise SystemExit("%s has a non string colour at %d" % (path, position))
        value = value.strip().lower()
        if value.startswith("#"):
            value = value[1:]
        if len(value) != 6:
            raise SystemExit("%s has %r, which is not a #RRGGBB colour" % (path, value))
        rgb = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
        allowed.setdefault(rgb, (position, "#" + value))
    return {"allowed": allowed, "raw": data, "count": len(colours)}


def parse_colour(text: str, palette: dict) -> tuple:
    """A backdrop given as #RRGGBB, RRGGBB, or $0F / 15 (a palette index)."""
    value = text.strip().lower()
    if value.startswith("$") or value.isdigit():
        index = int(value.lstrip("$"), 16 if value.startswith("$") else 10)
        entries = palette["raw"].get("entries")
        if isinstance(entries, list) and 0 <= index < len(entries):
            entry = entries[index]
            rgb = entry["hex"] if isinstance(entry, dict) else entry
            return hex_to_rgb(rgb)
        raise SystemExit("backdrop index %d is not in the palette file" % index)
    return hex_to_rgb(value)


def hex_to_rgb(value: str) -> tuple:
    value = value.strip().lower().lstrip("#")
    if len(value) != 6:
        raise SystemExit("%r is not a #RRGGBB colour" % value)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rgb_hex(rgb) -> str:
    return "#%02x%02x%02x" % rgb[:3]


# -----------------------------------------------------------------------------------------------------------------
# Images.

def load_image(path: str) -> Image.Image:
    if not os.path.isfile(path):
        raise SystemExit("%s does not exist" % path)
    with Image.open(path) as img:
        sheet = img.convert("RGBA")
    return sheet


def visible_pixels(image: Image.Image):
    """(x, y, rgb, alpha) for every pixel the player can see, in raster order."""
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            yield x, y, (r, g, b), a


# -----------------------------------------------------------------------------------------------------------------
# The rules. Each returns a list of offence records; an empty list means the rule passed.

def check_grid(image: Image.Image) -> list:
    problems = []
    if image.width % TILE:
        problems.append({"rule": "grid", "detail": "width %d is not a multiple of 8" % image.width})
    if image.height % TILE:
        problems.append({"rule": "grid", "detail": "height %d is not a multiple of 8" % image.height})
    return problems


def check_palette(image: Image.Image, palette: dict) -> list:
    allowed = palette["allowed"]
    offenders = Counter()
    for x, y, rgb, alpha in visible_pixels(image):
        if alpha != 255:
            offenders[(rgb, "alpha %d" % alpha)] += 1
            continue
        if rgb not in allowed:
            offenders[(rgb, "off palette")] += 1
    problems = []
    for (rgb, why), count in sorted(offenders.items(), key=lambda item: (-item[1], item[0])):
        problems.append({
            "rule": "palette",
            "colour": rgb_hex(rgb),
            "detail": "%s at %d pixels" % (why, count),
        })
    return problems


def tile_colours(image: Image.Image) -> dict:
    """Every 8x8 tile, with the distinct opaque colours it carries. Key: (tile_x, tile_y)."""
    pixels = image.load()
    out = {}
    for ty in range(image.height // TILE):
        for tx in range(image.width // TILE):
            seen = set()
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    r, g, b, a = pixels[x, y]
                    if a:
                        seen.add((r, g, b))
            out[(tx, ty)] = seen
    return out


def check_sprite_tiles(image: Image.Image) -> list:
    problems = []
    for (tx, ty), seen in sorted(tile_colours(image).items()):
        if len(seen) > 3:
            problems.append({
                "rule": "sprite_tile",
                "tile": [tx, ty],
                "colours": sorted(rgb_hex(rgb) for rgb in seen),
                "detail": "tile %d,%d carries %d colours, a sprite tile has 3 plus transparent"
                          % (tx, ty, len(seen)),
            })
    return problems


def backdrop_of(image: Image.Image, declared) -> tuple:
    """The shared backdrop colour: what the caller declared, else the most common colour in the image."""
    if declared is not None:
        return tuple(declared), "declared"
    counts = Counter()
    for _, _, rgb, alpha in visible_pixels(image):
        if alpha:
            counts[rgb] += 1
    if not counts:
        return None, "empty image"
    return counts.most_common(1)[0][0], "the most common colour in the image"


def area_colours(image: Image.Image) -> dict:
    """Every 16x16 attribute area, clipped to the image, with its distinct opaque colours."""
    pixels = image.load()
    out = {}
    for ay in range(0, image.height, AREA):
        for ax in range(0, image.width, AREA):
            seen = set()
            for y in range(ay, min(ay + AREA, image.height)):
                for x in range(ax, min(ax + AREA, image.width)):
                    r, g, b, a = pixels[x, y]
                    if a:
                        seen.add((r, g, b))
            out[(ax, ay)] = seen
    return out


def check_background_areas(image: Image.Image, backdrop) -> list:
    problems = []
    for (ax, ay), seen in sorted(area_colours(image).items()):
        if backdrop is not None:
            seen = seen - {tuple(backdrop)}
        if len(seen) > 3:
            problems.append({
                "rule": "background_area",
                "area": [ax, ay],
                "colours": sorted(rgb_hex(rgb) for rgb in seen),
                "detail": "16x16 area at %d,%d carries %d colours besides the backdrop, the limit is 3"
                          % (ax, ay, len(seen)),
            })
    return problems


def screen_colours(image: Image.Image) -> set:
    return {rgb for _, _, rgb, alpha in visible_pixels(image) if alpha}


def check_screen_colours(image: Image.Image, limit: int = MAX_COLOURS_ON_SCREEN) -> list:
    seen = screen_colours(image)
    if len(seen) > limit:
        return [{
            "rule": "screen_colours",
            "colours": sorted(rgb_hex(rgb) for rgb in seen),
            "detail": "%d colours in the image, one frame may show %d" % (len(seen), limit),
        }]
    return []


# -----------------------------------------------------------------------------------------------------------------
# The run.

def check(image: Image.Image, kind: str, palette: dict, backdrop=None, limit: int = MAX_COLOURS_ON_SCREEN) -> dict:
    problems = []
    problems += check_grid(image)
    problems += check_palette(image, palette)
    if kind == "sprite":
        problems += check_sprite_tiles(image)
        shade, how = None, "not used for sprites"
    else:
        shade, how = backdrop_of(image, backdrop)
        problems += check_background_areas(image, shade)
    problems += check_screen_colours(image, limit)
    return {
        "kind": kind,
        "size": [image.width, image.height],
        "tiles": [image.width // TILE, image.height // TILE],
        "colours": len(screen_colours(image)),
        "backdrop": rgb_hex(shade) if shade else None,
        "backdrop_from": how,
        "problems": problems,
        "ok": not problems,
    }


def describe(report: dict, path: str) -> list:
    lines = []
    lines.append("%s  %dx%d  %d tiles  %d colours  %s"
                 % (path, report["size"][0], report["size"][1],
                    report["tiles"][0] * report["tiles"][1], report["colours"],
                    "PASS" if report["ok"] else "FAIL %d problem(s)" % len(report["problems"])))
    if report["kind"] == "background" and report["backdrop"]:
        lines.append("  backdrop %s (%s)" % (report["backdrop"], report["backdrop_from"]))
    for problem in report["problems"]:
        where = ""
        if "tile" in problem:
            where = " tile %d,%d" % tuple(problem["tile"])
        elif "area" in problem:
            where = " area %d,%d" % tuple(problem["area"])
        colour = (" " + problem["colour"]) if "colour" in problem else ""
        lines.append("  [%s]%s%s %s" % (problem["rule"], where, colour, problem["detail"]))
        if "colours" in problem:
            lines.append("    colours: %s" % " ".join(problem["colours"]))
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check a PNG against the NES drawing rules.")
    parser.add_argument("png", help="the image to check")
    parser.add_argument("--type", required=True, choices=("sprite", "background"),
                        help="sprite: 8x8 tiles, 3 colours plus transparent. background: 16x16 areas plus a backdrop")
    parser.add_argument("--palette", default=None, help="palette file; default data\\nes_palette.json, or the art bible")
    parser.add_argument("--backdrop", default=None, help="background backdrop, #RRGGBB or $0F or 15")
    parser.add_argument("--max-colours", type=int, default=MAX_COLOURS_ON_SCREEN,
                        help="colours allowed on screen in one frame (25 on a NES)")
    parser.add_argument("--json", dest="json_path", default=None, help="write the report as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    root = repo_root()
    path, why = palette_path(root, args.palette)
    palette = load_palette(path)
    image = load_image(args.png)
    backdrop = parse_colour(args.backdrop, palette) if args.backdrop else None
    report = check(image, args.type, palette, backdrop, args.max_colours)
    report["png"] = os.path.abspath(args.png)
    report["palette"] = os.path.abspath(path)
    report["palette_source"] = why
    report["palette_colours"] = palette["count"]

    lines = describe(report, os.path.abspath(args.png))
    lines.append("  palette: %s (%d colours)" % (why, palette["count"]))
    if not args.quiet or not report["ok"]:
        for line in lines:
            print(line)
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
