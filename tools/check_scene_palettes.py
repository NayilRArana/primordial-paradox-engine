#!/usr/bin/env python3
"""check_scene_palettes.py: does the shipped art fit the palette its scene declares?

Why this exists
---------------
data\\palettes\\scene_title.json and scene_ship.json say, in entry numbers, exactly what colour the NES
may put on screen for those two scenes: one backdrop, four background palettes of three, four sprite
palettes of three. Writing that down proves nothing. This tool measures the art on disk against it,
and it measures the two layers the way the frame is actually drawn:

  background   the seven scrolling title strips composed at their data\\title.json y offsets, which is
               the frame the player sees, so an area is judged on the screen and not on one strip;
  sprites      every 8x16 sprite of every sprite sheet, because a sprite has three colours plus
               transparency whether it is drawn as 8x8 or 8x16, and 8x16 is the stricter reading;
  ship         the tileset sheet stacked to a 256x240 frame, so each 16x16 tile lands in exactly one
               attribute area and the same 8x8 tiles are also read as sprite material.

Two authorities, on purpose. This tool asks tools\\nes_composite_check.py to judge the composed frames,
so the pixel rules live in one place and are not restated here; and it does the palette arithmetic the
frame check cannot do without a sprite mask (which sprite uses which of the four groups).

Usage:
    python tools\\check_scene_palettes.py
    python tools\\check_scene_palettes.py --json output\\scene_palettes.json --root <repo>

Exit 0 when every scene fits, 1 when any rule fails, with each failure on its own line.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, os.path.join(TOOLS_DIR, "art"))

import scene_palette  # noqa: E402  (the art lane's single authority for which palette is which)

SCENE_NAMES = ("title", "ship")
SPRITE_HEIGHT = 16
SUBTILE = 8
CELL = 16
FRAME_W, FRAME_H = 256, 240
# The ship's cast is its WALKING cast, because a walking room draws walking sheets: the party's four walking
# sheets plus the sailor actor. sailor_battle.png came off this list on card t_a6a7a436: the ship's four sprite
# palettes are the party's four walking triples now (ruling section 17), a 168x32 battle figure is drawn on a
# strip and never on a walking map, and under these four rows 40 of its 72 inked 8x8 tiles are uncovered by any
# row.
# Card t_0b9c2faf answered the sheet's own card and this list is the RETIRED verdict: it is not the sailor
# fight's art (that is game/sprites_src/enemies/navy_sailor.png, 32x32, drawn as background art in the battle
# screen's 32x32 enemy slot), no 24x32 slot in this game is anything but a hero's, and no single sprite palette
# carries a frame of it (two or three do, and the PPU gives four rows to the whole strip). So it is judged on no
# row, it is out of this list and out of tools/art/scene_palette.py's solve pool, and
# tools/art/make_characters.py no longer writes it. This list and that one are the same five names by test.
SHIP_SPRITES = ("hadrian_ow_v2", "konrad_ow_v2", "zander_ow_v2", "percy_ow_v2", "sailor_ow_v2")
MAX_SPRITES_PER_LINE = 8
MAX_SPRITES = 64
MAX_COLOURS_ON_SCREEN = 25


def composite_check(frame_path: str, extra: list[str] | None = None) -> tuple[int, str]:
    """Run tools\\nes_composite_check.py on one frame and return (exit code, its report)."""
    command = [sys.executable, os.path.join(TOOLS_DIR, "nes_composite_check.py"), frame_path]
    if extra:
        command.extend(extra)
    result = subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def scene_budget(scene) -> dict:
    """The colours a scene is allowed to spend, counted the way the PPU counts them."""
    background = set()
    for row in scene.background:
        background.update(row)
    sprites = set()
    for row in scene.sprites:
        sprites.update(row)
    return {
        "scene": scene.name,
        "backdrop": scene.backdrop,
        "background_palettes": [[scene.colours[entry] for entry in row] for row in scene.background],
        "sprite_palettes": [[scene.colours[entry] for entry in row] for row in scene.sprites],
        "background_colours": len(background),
        "sprite_colours": len(sprites),
        "distinct_colours": len(background | sprites | {scene.backdrop}),
        "limit": MAX_COLOURS_ON_SCREEN,
    }


def group_colours(image: Image.Image, scene, frame_w: int, frame_h: int, step: int = SPRITE_HEIGHT):
    """Yield (frame, x, y, colour set) for every 8xstep group of a sprite sheet."""
    for frame in range(max(1, image.width // frame_w)):
        ox = frame * frame_w
        for ty in range(0, frame_h, step):
            for tx in range(0, frame_w, SUBTILE):
                box = (ox + tx, ty,
                       min(ox + frame_w, ox + tx + SUBTILE) - 1,
                       min(frame_h, ty + step) - 1)
                counts = scene_palette._pixel_counts(image, box, scene.index_of, {})
                if counts:
                    yield frame, tx, ty, set(counts)


def check_title(root: str, report: dict) -> list[str]:
    """The composed title frame and every sprite sheet it draws."""
    scene = scene_palette.load_scene(root, "title")
    failures = []
    frame_path = os.path.join(tempfile.mkdtemp(prefix="pp_title_"), "frame.png")
    scene_palette.compose_frame(root, frame_path)
    code, text = composite_check(frame_path)
    # The report names the file and not the scratch directory it was composed in: a temp directory name changes on
    # every run, so recording one would mean this report could never be regenerated byte for byte, and
    # output/scene_palettes.json is committed (card t_933d8840).
    report["title_frame"] = {"frame": os.path.basename(frame_path), "exit": code,
                             "report": text.strip().splitlines()}
    if code != 0:
        failures.append("title: the composed background frame fails nes_composite_check.py (exit %d)" % code)

    sprite_sets = scene.sprite_sets()
    per_asset = {}
    for name in scene_palette.TITLE_SPRITES:
        try:
            image, meta = scene_palette.load_strip(root, name)
        except OSError:
            failures.append("title: %s is missing from game/sprites_src/title" % name)
            continue
        fw, fh = meta["frame_w"], meta["frame_h"]
        groups = list(group_colours(image, scene, fw, fh))
        over = [g for g in groups if len(g[3]) > 3]
        homeless = [g for g in groups if not any(g[3] <= row for row in sprite_sets)]
        frames = max(1, image.width // fw)
        # OAM cost of the asset drawn as one object: 8x16 sprites, 8 across and fh/16 down, so a
        # scanline inside the object is covered by the `across` sprites of that one band.
        across = (fw + SUBTILE - 1) // SUBTILE
        busiest = across
        per_asset[name] = {
            "frame": [fw, fh], "frames": frames, "groups": len(groups),
            "groups_over_three": len(over), "groups_outside_a_palette": len(homeless),
            "worst_colours": max((len(g[3]) for g in groups), default=0),
            "oam_sprites_per_frame": across * (fh // SPRITE_HEIGHT),
            "busiest_scanline": busiest,
        }
        if over:
            failures.append("title: %s has %d group(s) of 8x%d with more than 3 colours (worst %d)"
                            % (name, len(over), SPRITE_HEIGHT, per_asset[name]["worst_colours"]))
        if homeless:
            failures.append("title: %s has %d group(s) whose colours fit none of the four sprite palettes"
                            % (name, len(homeless)))
    report["title_sprites"] = per_asset

    # The car alone, judged by the project's own frame checker rather than by this file's arithmetic.
    car = os.path.join(root, "game", "sprites_src", "title", "spr_title_car.png")
    if os.path.isfile(car):
        with Image.open(car) as handle:
            sheet = handle.convert("RGBA")
        one = sheet.crop((0, 0, 64, 32))
        frame = Image.new("RGBA", (FRAME_W, FRAME_H), scene.colours[scene.backdrop] + (255,))
        frame.alpha_composite(one, (0, 0))
        tmp = tempfile.mkdtemp(prefix="pp_car_")
        frame_path = os.path.join(tmp, "car.png")
        frame.save(frame_path, "PNG")
        sprites = []
        for y in range(0, 32, SPRITE_HEIGHT):
            for x in range(0, 64, SUBTILE):
                sprites.append({"x": x, "y": y, "w": SUBTILE, "h": SPRITE_HEIGHT,
                                "transparent": "#%02x%02x%02x" % scene.colours[scene.backdrop]})
        list_path = os.path.join(tmp, "car_sprites.json")
        with open(list_path, "w", encoding="utf-8") as handle:
            json.dump({"sprites": sprites}, handle, indent=2)
        code, text = composite_check(frame_path, ["--sprites", list_path, "--sprite-height",
                                                 str(SPRITE_HEIGHT),
                                                 "--backdrop", "#%02x%02x%02x" % scene.colours[scene.backdrop]])
        report["title_car_frame"] = {"exit": code, "report": text.strip().splitlines()}
        if code != 0:
            failures.append("title: the car frame 0 fails nes_composite_check.py --sprites (exit %d)" % code)
    return failures


def check_ship(root: str, report: dict) -> list[str]:
    """The ship tileset as a 256x240 stack, so every tile lands in one attribute area."""
    scene = scene_palette.load_scene(root, "ship")
    path = os.path.join(root, "game", "sprites_src", "env", "ts_ship.png")
    if not os.path.isfile(path):
        return ["ship: game/sprites_src/env/ts_ship.png is missing"]
    with Image.open(path) as handle:
        sheet = handle.convert("RGBA")
    bg_sets = scene.bg_sets()
    sprite_sets = scene.sprite_sets()
    failures = []
    tiles = 0
    homeless_bg = []
    histogram = [0, 0, 0, 0]
    for ty in range(0, sheet.height, CELL):
        for tx in range(0, sheet.width, CELL):
            box = (tx, ty, min(sheet.width, tx + CELL) - 1, min(sheet.height, ty + CELL) - 1)
            counts = scene_palette._pixel_counts(sheet, box, scene.index_of, {})
            if not counts:
                continue
            tiles += 1
            colours = set(counts)
            fits = [index for index, allowed in enumerate(bg_sets) if colours <= allowed]
            if not fits:
                homeless_bg.append([tx, ty])
            else:
                histogram[min(fits)] += 1
    if homeless_bg:
        failures.append("ship: %d of %d 16x16 tiles fit none of the four background palettes (first %s)"
                        % (len(homeless_bg), tiles, homeless_bg[0]))
    report["ship_sheet"] = {"tiles": tiles, "background_histogram": histogram,
                            "tiles_outside_background_palettes": len(homeless_bg),
                            "sheet": [sheet.width, sheet.height]}

    # Sprites are the ship's walking cast, not its walls. A background tile may spend the shared backdrop
    # as its fourth colour; a sprite cannot, because its fourth state is transparency, so the sheet is
    # deliberately not held to the sprite rule. The party's four walking sheets and the sailor actor are
    # (card t_a6a7a436, ruling section 17).
    per_asset = {}
    for name in SHIP_SPRITES:
        base = os.path.join(root, "game", "sprites_src", "chars", name)
        if not (os.path.isfile(base + ".png") and os.path.isfile(base + ".json")):
            continue
        with open(base + ".json", "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        with Image.open(base + ".png") as handle:
            image = handle.convert("RGBA")
        fw, fh = meta["frame_w"], meta["frame_h"]
        groups = list(group_colours(image, scene, fw, fh))
        over = [g for g in groups if len(g[3]) > 3]
        homeless = [g for g in groups if not any(g[3] <= row for row in sprite_sets)]
        per_asset[name] = {"frame": [fw, fh], "frames": max(1, image.width // fw),
                           "groups": len(groups), "groups_over_three": len(over),
                           "groups_outside_a_palette": len(homeless),
                           "worst_colours": max((len(g[3]) for g in groups), default=0)}
        if over:
            failures.append("ship: %s has %d group(s) of 8x%d with more than 3 colours (worst %d)"
                            % (name, len(over), SPRITE_HEIGHT, per_asset[name]["worst_colours"]))
        if homeless:
            failures.append("ship: %s has %d group(s) whose colours fit none of the four sprite palettes"
                            % (name, len(homeless)))
    report["ship_sprites"] = per_asset

    stack = Image.new("RGBA", (FRAME_W, FRAME_H), scene.colours[scene.backdrop] + (255,))
    y = 0
    while y < FRAME_H:
        stack.alpha_composite(sheet.crop((0, 0, min(sheet.width, FRAME_W),
                                          min(sheet.height, FRAME_H - y))), (0, y))
        y += sheet.height
    frame_path = os.path.join(tempfile.mkdtemp(prefix="pp_ship_"), "ship_stack.png")
    stack.save(frame_path, "PNG")
    code, text = composite_check(frame_path)
    # Basename for the same reason as the title frame above: this report is committed, so it may not carry a name that
    # changes on every run.
    report["ship_frame"] = {"frame": os.path.basename(frame_path), "exit": code,
                            "report": text.strip().splitlines()}
    if code != 0:
        failures.append("ship: the tiled sheet frame fails nes_composite_check.py (exit %d)" % code)
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--json", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    report = {"scenes": {}, "failures": []}
    for name in SCENE_NAMES:
        report["scenes"][name] = scene_budget(scene_palette.load_scene(root, name))
    report["failures"].extend(check_title(root, report))
    report["failures"].extend(check_ship(root, report))

    if not args.quiet:
        for name, budget in report["scenes"].items():
            print("scene %s: backdrop $%02X, %d background colours + %d sprite colours = %d on screen (limit %d)"
                  % (name, budget["backdrop"], budget["background_colours"],
                     budget["sprite_colours"], budget["distinct_colours"], budget["limit"]))
            for index, row in enumerate(budget["background_palettes"]):
                print("  bg%d  %s" % (index, "  ".join("#%02x%02x%02x" % rgb for rgb in row)))
            for index, row in enumerate(budget["sprite_palettes"]):
                print("  sp%d  %s" % (index, "  ".join("#%02x%02x%02x" % rgb for rgb in row)))
        for name, asset in report.get("title_sprites", {}).items():
            print("  sprite %-22s %dx%d %2d frames  %3d groups of 8x%d  over three: %d  worst %d  "
                  "OAM %d per frame, busiest scanline %d"
                  % (name, asset["frame"][0], asset["frame"][1], asset["frames"], asset["groups"],
                     SPRITE_HEIGHT, asset["groups_over_three"], asset["worst_colours"],
                     asset["oam_sprites_per_frame"], asset["busiest_scanline"]))
        for key in ("title_frame", "title_car_frame", "ship_frame"):
            entry = report.get(key)
            if entry:
                print("%s: nes_composite_check.py exit %d" % (key, entry["exit"]))
        ship = report.get("ship_sheet", {})
        if ship:
            print("ship sheet %s: %d tiles, background palette histogram %s"
                  % (ship["sheet"], ship["tiles"], ship["background_histogram"]))
        for name, asset in report.get("ship_sprites", {}).items():
            print("  ship sprite %-18s %dx%d %2d frames  %3d groups of 8x%d  over three: %d  worst %d"
                  % (name, asset["frame"][0], asset["frame"][1], asset["frames"], asset["groups"],
                     SPRITE_HEIGHT, asset["groups_over_three"], asset["worst_colours"]))
        if report["failures"]:
            for line in report["failures"]:
                print("FAIL %s" % line)
        else:
            print("PASS: both scenes are drawn inside their declared palettes")

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
