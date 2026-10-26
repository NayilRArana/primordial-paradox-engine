#!/usr/bin/env python3
"""compose_battle_frame.py: the battle field with its strip, its party and its enemy, drawn from the shipped art.

Why this file exists (card t_4275136f). The battle screen draws three things that no picture in this repository
showed together: the baked strip (pp_battle_draw_field), the four party battle sheets at x=224
(pp_battle_draw_party) and the enemy's sheet at tile 3,8 (pp_battle_draw_enemy). The evidence a reviewer can look at
has to come from somewhere, and there are two honest sources: a window capture of the built game, which needs
GameMaker, a build and an idle machine, and this tool, which draws the same three sheets at the same numbers out of
the same data the director reads. This is the second one, and it says so: the file it writes is a COMPOSED frame,
not a capture, and the game log line that proves the build drew it is a separate claim.

What it draws, in the director's own order, and nothing else:

  1. the backdrop, from the scene's own palette file (data/palettes/scene_battle_<scene>.json, "backdrop");
  2. the strip, game/sprites_src/bg/bg_battle_<strip>.png, at pp_battle_bg_x/y (0,0);
  3. the enemy's sheet, game/sprites_src/enemies/<enemy id>.png, frame 0, at the battle screen's first enemy slot
     from data/ui_layouts.json (tile 3,8, 32x32), which is ruling 7.5's background art;
  4. the party's four sheets, game/sprites_src/chars/<hero>_battle.png, frame 0, at the layout's four party slots
     (x=224, y=32, 64, 96 and 128, 24x32 each), in the file's member order.

Frame 0 is not a choice: a fresh fight is turn 0 and its first step, and pp_battle_actor_frame reads frame 0 until
step 7 of an 8 fps sheet, so frame 0 is exactly what the first frame of a real fight draws.

What it does NOT draw, and why. The command band, the message window, the enemy's name and its health bar are the
director's HUD, drawn in data/room_palettes.json's four universal roles (ink $00, paper $01, dim $03, text $05).
Three of those four are not entries of the deck scene's own palette set (data/palettes/scene_battle_deck_night.json:
bg0 $02 $01 $30, bg1 $01 $11 $21, bg2 $00 $30 $02, bg3 $0F $02 $00, sprites sp0 to sp3), so a frame that carries
the HUD cannot read 0 failures in tools/palette_synergy.py and the failures would be about the HUD, not about the
three things this card draws. The HUD stays out, and the number this tool is checked by is the field's.

Usage:
    python tools\\art\\compose_battle_frame.py
    python tools\\art\\compose_battle_frame.py --strip deck_night --scene battle_deck_night --out output\\x.png

Deterministic: the same art and the same data give the same bytes, PNG written with no timestamp chunk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))
import palette_synergy  # noqa: E402  the 2C02 entry table, measured rather than restated

FRAME_W, FRAME_H = 256, 240
TILE = 8
STRIPS = ("corridor", "wardroom", "deck_night", "quay_dusk")


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def battle_screen(root: str) -> dict:
    for screen in read_json(os.path.join(root, "data", "ui_layouts.json"))["screens"]:
        if screen["name"] == "battle":
            return screen
    raise SystemExit("compose_battle_frame: data/ui_layouts.json has no battle screen")


def enemy_slots(root: str) -> list:
    """The battle screen's enemy slots in pixels, read from the layout's tile units."""
    return [
        {"x": int(slot["x"]) * TILE, "y": int(slot["y"]) * TILE,
         "w": int(slot["w"]) * TILE, "h": int(slot["h"]) * TILE}
        for slot in battle_screen(root)["enemies"]
    ]


def party_slots(root: str) -> list:
    """The four party slots in pixels, in the layout's member order, ids lowercased for the sheet names."""
    return [
        {"id": slot["member"].lower(), "x": int(slot["x"]) * TILE, "y": int(slot["y"]) * TILE,
         "w": int(slot["w"]) * TILE, "h": int(slot["h"]) * TILE}
        for slot in battle_screen(root)["party"]
    ]


def backdrop_hex(root: str, scene: str) -> str:
    """The scene's one shared backdrop, as the hex data/nes_palette.json gives for its entry number."""
    palette = read_json(os.path.join(root, "data", "palettes", "scene_%s.json" % scene))
    index = int(palette["backdrop"])
    for entry in read_json(os.path.join(root, "data", "nes_palette.json"))["entries"]:
        if int(entry["index"]) == index:
            return entry["hex"]
    raise SystemExit("compose_battle_frame: background entry %d is not in data/nes_palette.json" % index)


def first_frame(path: str) -> Image.Image:
    """Frame 0 of a sheet, as RGBA: the sidecar's frame_w is what one frame is, whatever the strip is long for."""
    sidecar = read_json(os.path.splitext(path)[0] + ".json")
    sheet = Image.open(path).convert("RGBA")
    width, height = int(sidecar["frame_w"]), int(sidecar["frame_h"])
    return sheet.crop((0, 0, width, height))


def compose(root: str, strip: str, scene: str, enemy: str) -> Image.Image:
    """The field: backdrop, strip at the origin, the enemy at its slot, the party in its four slots."""
    if strip not in STRIPS:
        raise SystemExit("compose_battle_frame: %r is not one of %s" % (strip, ", ".join(STRIPS)))
    colour = backdrop_hex(root, scene)
    frame = Image.new("RGBA", (FRAME_W, FRAME_H),
                      (int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16), 255))

    strip_path = os.path.join(root, "game", "sprites_src", "bg", "bg_battle_%s.png" % strip)
    strip_image = Image.open(strip_path).convert("RGBA")
    frame.alpha_composite(strip_image, (0, 0))

    slot = enemy_slots(root)[0]
    enemy_path = os.path.join(root, "game", "sprites_src", "enemies", "%s.png" % enemy)
    if not os.path.isfile(enemy_path):
        raise SystemExit("compose_battle_frame: no sheet at %s" % enemy_path)
    frame.alpha_composite(first_frame(enemy_path), (slot["x"], slot["y"]))

    for party in party_slots(root):
        sheet = os.path.join(root, "game", "sprites_src", "chars", "%s_battle.png" % party["id"])
        if not os.path.isfile(sheet):
            raise SystemExit("compose_battle_frame: no sheet at %s" % sheet)
        frame.alpha_composite(first_frame(sheet), (party["x"], party["y"]))

    return frame


def write_png(image: Image.Image, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    # No timestamp chunk, so the same art gives the same bytes (the repository's PNG rule, see tests/test_project.py).
    image.convert("RGB").save(path, optimize=True)


def tile_sets(image: Image.Image, box: tuple) -> list:
    """The palette entry set of every 8x8 tile inside box that has any opaque pixel, with its position.

    This is the unit the PPU judges a figure in: one 8x8 tile, three opaque colours, one palette. A tile with no
    opaque pixel is skipped, which is why the counts below read as "inked tiles" and not as "tiles".
    """
    grid = palette_synergy.Grid(ROOT)
    pixels = image.convert("RGBA").load()
    out = []
    for top in range(box[1], box[3], TILE):
        for left in range(box[0], box[2], TILE):
            needs = set()
            for y in range(top, min(top + TILE, box[3])):
                for x in range(left, min(left + TILE, box[2])):
                    r, g, b, a = pixels[x, y]
                    if a:
                        needs.add(grid.entry((r, g, b)))
            if needs:
                out.append((left, top, needs))
    return out


def coverage(source: str, allowed: set) -> dict:
    """How many of a sheet's inked 8x8 tiles are carried by one palette plus the backdrop."""
    sheet = Image.open(source).convert("RGBA")
    sidecar = read_json(os.path.splitext(source)[0] + ".json")
    frame = sheet.crop((0, 0, int(sidecar["frame_w"]), int(sidecar["frame_h"])))
    inked = fit = 0
    misses = []
    for left, top, needs in tile_sets(frame, (0, 0, frame.width, frame.height)):
        inked += 1
        if None in needs:
            misses.append((left, top, "off the 2C02 palette"))
            continue
        if needs <= allowed:
            fit += 1
        else:
            misses.append((left, top, sorted(needs - allowed)))
    return {"inked": inked, "fit": fit, "misses": misses}


def check(root: str, strip: str, scene: str, enemy: str, frame: Image.Image) -> tuple:
    """The numbers the frame has to hold: the sheets in their right place, and each one on a legal palette.

    1. REGIONS ARE THE SHEETS. Every actor's rectangle in the frame is the sheet's own frame 0, pixel for pixel,
       wherever the sheet is opaque. A draw at the wrong slot, a wrong frame or a scaled sheet fails here.
    2. THE ENEMY SPENDS THE AREA'S BACKGROUND TRIPLE. Its slot sits on bg2 cells only (ruling 15.1), so every inked
       8x8 tile of the sheet has to fit bg2 plus the shared backdrop. This is ruling 15.3's 36 of 36, measured on
       the sheet that ships now.
    3. EACH HERO SPENDS HIS OWN RESERVED TRIPLE. data/scene_palettes.json hero_palettes, one triple per hero, with
       no backdrop, because a sprite has transparency instead.
    """
    problems = []
    strip_path = os.path.join(root, "game", "sprites_src", "bg", "bg_battle_%s.png" % strip)
    strip_image = Image.open(strip_path).convert("RGBA")

    slots = ([{"name": enemy, "box": enemy_slots(root)[0], "path": os.path.join(
        root, "game", "sprites_src", "enemies", "%s.png" % enemy)}]
        + [{"name": party["id"], "box": party, "path": os.path.join(
            root, "game", "sprites_src", "chars", "%s_battle.png" % party["id"])} for party in party_slots(root)])
    busy = [(slot["box"]["x"], slot["box"]["y"], slot["box"]["x"] + slot["box"]["w"],
             slot["box"]["y"] + slot["box"]["h"]) for slot in slots]

    if not strip_matches(frame, strip_image, busy):
        problems.append("the strip at 0,0 is not bg_battle_%s.png" % strip)

    palette = read_json(os.path.join(root, "data", "palettes", "scene_%s.json" % scene))
    rows = {row["name"]: set(row["colours"]) for row in palette["background"]}
    backdrop = int(palette["backdrop"])
    hero_colours = {name: set(row["colours"])
                    for name, row in read_json(os.path.join(root, "data", "scene_palettes.json"))["hero_palettes"].items()}

    for actor in slots:
        source = Image.open(actor["path"]).convert("RGBA")
        sidecar = read_json(os.path.splitext(actor["path"])[0] + ".json")
        sheet_frame = source.crop((0, 0, int(sidecar["frame_w"]), int(sidecar["frame_h"])))
        box = actor["box"]
        drawn = frame.convert("RGBA").crop((box["x"], box["y"], box["x"] + sheet_frame.width,
                                           box["y"] + sheet_frame.height))
        if not same_pixels(drawn, sheet_frame):
            problems.append("%s is not drawn at %d,%d" % (os.path.basename(actor["path"]), box["x"], box["y"]))

    enemy_path = slots[0]["path"]
    enemy_fit = coverage(enemy_path, rows["bg2"] | {backdrop})
    if enemy_fit["fit"] != enemy_fit["inked"]:
        problems.append("the enemy's sheet fits bg2 plus the backdrop on %d of %d inked tiles: %s"
                        % (enemy_fit["fit"], enemy_fit["inked"], enemy_fit["misses"][:4]))

    party_fit = {}
    for party in party_slots(root):
        path = os.path.join(root, "game", "sprites_src", "chars", "%s_battle.png" % party["id"])
        fit = coverage(path, hero_colours[party["id"]])
        party_fit[party["id"]] = fit
        if fit["fit"] != fit["inked"]:
            problems.append("%s fits its reserved triple on %d of %d inked tiles: %s"
                            % (party["id"], fit["fit"], fit["inked"], fit["misses"][:4]))

    return problems, {
        "strip": "bg_battle_%s.png" % strip,
        "enemy": {"id": enemy, "inked": enemy_fit["inked"], "fit": enemy_fit["fit"]},
        "party": {name: {"inked": fit["inked"], "fit": fit["fit"]} for name, fit in party_fit.items()},
    }


def strip_matches(frame: Image.Image, strip: Image.Image, busy: list) -> bool:
    """True when every pixel of the strip's rectangle is the strip's own pixel, outside the actors' rectangles.

    The actors stand ON the strip, so the rectangles they occupy are the one place the strip is expected to be
    covered. Everywhere else inside the strip's 256x112, the frame has to be the committed PNG exactly.
    """
    a = frame.convert("RGBA").load()
    b = strip.load()
    for y in range(strip.height):
        for x in range(strip.width):
            if any(x >= x0 and x < x1 and y >= y0 and y < y1 for x0, y0, x1, y1 in busy):
                continue
            if a[x, y][:3] != b[x, y][:3]:
                return False
    return True


def same_pixels(drawn: Image.Image, sheet: Image.Image) -> bool:
    """True when every pixel the sheet draws is the pixel the frame carries at that spot.

    The sheet's transparent pixels are NOT compared: the frame has the ground there, which is the whole point of a
    sprite. Everything the sheet does draw has to match exactly, at 1:1, with no blend.
    """
    a = drawn.load()
    b = sheet.load()
    for y in range(sheet.height):
        for x in range(sheet.width):
            sr, sg, sb, sa = b[x, y]
            if sa == 0:
                continue
            if a[x, y][:3] != (sr, sg, sb):
                return False
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compose the battle field from the shipped art.")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--strip", default="deck_night", help="one of %s" % ", ".join(STRIPS))
    parser.add_argument("--scene", default="battle_deck_night", help="the scene palette file the frame spends")
    parser.add_argument("--enemy", default="navy_sailor", help="the enemy id, which is the sheet's file stem")
    parser.add_argument("--out", default=None)
    parser.add_argument("--check", action="store_true",
                        help="check the frame's regions, the enemy's background triple and each hero's triple")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    out = args.out or os.path.join(root, "output", "battle_%s_%s_frame.png" % (args.strip, args.enemy))
    frame = compose(root, args.strip, args.scene, args.enemy)
    write_png(frame, out)

    colours = sorted({"%02x%02x%02x" % colour
                      for _count, colour in frame.convert("RGB").getcolors(maxcolors=1 << 16)})
    print("battle frame: %s, %dx%d, %d colours" % (out, frame.width, frame.height, len(colours)))
    print("  strip     : bg_battle_%s.png at 0,0 (256x112)" % args.strip)
    print("  enemy     : %s.png frame 0 at %d,%d (%dx%d)"
          % (args.enemy, enemy_slots(root)[0]["x"], enemy_slots(root)[0]["y"],
             enemy_slots(root)[0]["w"], enemy_slots(root)[0]["h"]))
    for party in party_slots(root):
        print("  party     : %s_battle.png frame 0 at %d,%d (%dx%d)"
              % (party["id"], party["x"], party["y"], party["w"], party["h"]))

    if not args.check:
        return 0

    problems, numbers = check(root, args.strip, args.scene, args.enemy, frame)
    failed_draws = len([problem for problem in problems if "is not drawn at" in problem])
    strip_ok = not [problem for problem in problems if problem.startswith("the strip at")]
    print("check: strip at 0,0 %s, %d of 5 actor(s) drawn as their own sheet"
          % ("matches" if strip_ok else "differs", 5 - failed_draws))
    print("check: enemy %s fits %d of %d inked tiles on bg2 plus the backdrop"
          % (numbers["enemy"]["id"], numbers["enemy"]["fit"], numbers["enemy"]["inked"]))
    for name, fit in numbers["party"].items():
        print("check: %s fits %d of %d inked tiles on his reserved triple"
              % (name, fit["fit"], fit["inked"]))
    for problem in problems:
        print("check: FAIL %s" % problem)
    print("check: %s" % ("PASS" if not problems else "FAIL"))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
