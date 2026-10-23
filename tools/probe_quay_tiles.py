#!/usr/bin/env python3
"""probe_quay_tiles.py: say, in numbers, what the exterior tile wiring draws on southampton_town_quay.

Card R28 (t_7d1380f9). The game draws the exterior from three things: the map row's tile characters, the character to
tile table in `game/scripts/pp_map_tile/pp_map_tile.gml`, and the sheet card R46 delivered at
`game/sprites_src/env/quay/quay_tiles.png`. A GML module cannot be called from Python, so this probe reads the table
out of the GML source and the sheet out of its own manifest, and refuses when the two disagree.

What it reports:

1. Which map row it read (`data/maps/all.json` first, the same file the game loads).
2. How many tiles the row draws, how many characters it uses, and how many of those the table does not name, which is
   the number the card's check calls "wrong". Eight or fewer passes; the list is printed either way.
3. Every drawn tile index against the sheet's own tile count and character, so a gid that names no art, or the wrong
   art, is named here rather than found on a screen.
4. The layer order, read off the two sources: ground and props before the hero, above the hero after him.
5. One 256x240 frame composed the way the game composes it, saved to `output/quay_tile_frame_preview.png`, then judged
   by `tools/nes_composite_check.py` (the checker `tools/nes_audit_all.py` runs for a frame) with the screen colour cap.

Usage:
    python tools/probe_quay_tiles.py
    python tools/probe_quay_tiles.py --rows <a json file with a maps array> --id southampton_town_quay
    python tools/probe_quay_tiles.py --no-frame        every check but the composed frame

Exit codes: 0 every check holds, 1 a check failed, 2 the inputs are not there.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

TABLE_GML = os.path.join(ROOT, "game", "scripts", "pp_map_tile", "pp_map_tile.gml")
MAP_GML = os.path.join(ROOT, "game", "scripts", "pp_map", "pp_map.gml")
OVERWORLD_GML = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")
QUAY_JSON = os.path.join(ROOT, "game", "sprites_src", "env", "quay", "quay_tiles.json")
QUAY_PNG = os.path.join(ROOT, "game", "sprites_src", "env", "quay", "quay_tiles.png")
HERO_PNG = os.path.join(ROOT, "game", "datafiles", "art", "zander_ow_v2.png")
MAPS_JSON = os.path.join(ROOT, "data", "maps", "all.json")
OSM_JSON = os.path.join(ROOT, "data", "maps", "osm", "southampton_town_quay.json")
ART_MANIFEST = os.path.join(ROOT, "game", "datafiles", "art", "title_manifest.json")
FRAME_OUT = os.path.join(ROOT, "output", "quay_tile_frame_preview.png")
HERO_FRAME = os.path.join(ROOT, "output", "quay_layer_order_hero.png")

TILE = 16
VIEW_W = 16
VIEW_H = 15
PLANES = {"PP_TILE_PLANE_GROUND": 0, "PP_TILE_PLANE_PROPS": 1, "PP_TILE_PLANE_ABOVE": 2}
PLANE_NAME = {0: "ground", 1: "props", 2: "above"}

# The OSM map holds terrain kinds, not the game's characters (tools/osm_to_map.py draws one flat colour per kind).
# This is how the probe reads that file when data/maps/all.json does not carry the row yet: the quay's own kind to
# character table. Card ARRIVAL-MAP-2 is the card that lands the real row, with its own legend.
OSM_KIND_CHAR = {
    "ground": ".", "park": ",", "water": "w", "quay": "q", "rail": "b",
    "path": ".", "road_minor": ",", "road_major": ",", "building": "#", "door": "D",
}

ROW = re.compile(r'\{\s*ch:\s*"(?P<ch>[^"]*)"\s*,\s*gid:\s*(?P<gid>\d+)\s*,\s*plane:\s*(?P<plane>PP_TILE_PLANE_\w+)\s*,'
                 r'\s*group:\s*"(?P<group>[^"]*)"')


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def load(path: str):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def gml_rows(path: str) -> dict:
    """The character to (gid, plane) table of each set, read out of the GML source itself."""
    code = "\n".join(line.split("//")[0] for line in read(path).splitlines())
    sets = {"quay": "pp_map_tile_rows_quay", "ship": "pp_map_tile_rows_ship"}
    table = {}
    for name, function in sets.items():
        start = code.find("function %s()" % function)
        if start < 0:
            raise SystemExit("probe: %s does not define %s()" % (os.path.basename(path), function))
        end = code.find("\n}", start)
        body = code[start:end]
        rows = {}
        for match in ROW.finditer(body):
            rows[match.group("ch")] = (int(match.group("gid")), PLANES[match.group("plane")], match.group("group"))
        table[name] = rows
    # The office profile is the quay table with the floor and the desk overridden in pp_map_tile_build().
    office = dict(table["quay"])
    build = code[code.find("function pp_map_tile_build("):]
    build = build[:build.find("\n}")]
    floor = re.search(r'_table\[\$ "\."\] = \{ gid: (\d+)', build)
    if floor:
        office["."] = (int(floor.group(1)), PLANES["PP_TILE_PLANE_GROUND"], "bg2_brick_iron")
    table["office"] = office
    return table


def room_set(room_palette: str) -> str:
    """The set pp_map_tile_set_for_room() picks for a room palette id, read out of the same GML file."""
    code = read(TABLE_GML)
    start = code.find("function pp_map_tile_set_for_room(")
    body = code[start:code.find("\n}", start)]
    for palette, name in re.findall(r'if \(_id == "(\w+)"\) return PP_TILE_SET_(\w+);', body):
        if palette == room_palette:
            return name.lower()
    return "ship"


def map_row(maps_path: str, map_id: str) -> tuple:
    """The map row, and the file it came from. The game loads data/maps/all.json; a row that is not there yet means
    card ARRIVAL-MAP-2 has not spliced it, so the probe falls back to the OSM geometry it will be drawn from."""
    if os.path.isfile(maps_path):
        payload = load(maps_path)
        rows = payload["maps"] if isinstance(payload, dict) and "maps" in payload else payload
        for row in rows:
            if row.get("id") == map_id:
                return row, maps_path
    if map_id != "southampton_town_quay" or not os.path.isfile(OSM_JSON):
        raise SystemExit("probe: no map row %r in %s and no OSM fallback" % (map_id, maps_path))
    doc = load(OSM_JSON)
    width, height = doc["width"], doc["height"]
    names = {i + 1: name for i, name in enumerate(["ground", "park", "water", "quay", "rail", "path",
                                                   "road_minor", "road_major", "building", "door"])}
    data = doc["layers"][0]["data"]
    rows = ["".join(OSM_KIND_CHAR[names[gid]] for gid in data[y * width:(y + 1) * width]) for y in range(height)]
    row = {
        "id": map_id,
        "name": "Southampton, Town Quay (read from %s)" % os.path.relpath(OSM_JSON, ROOT).replace(os.sep, "/"),
        "width": width, "height": height,
        "tile_legend": {".": "floor", "#": "wall", "D": "door"},
        "tiles": rows,
        "room_palette": "quay_night",
        "spawns": {"start": {"x": 11, "y": 1}},
    }
    return row, OSM_JSON


def order_check() -> list:
    """The layer order, read off the code: ground and props in pp_map_draw, above in pp_map_draw_above, and the
    overworld calling the two around the hero. Returns the problems found, empty when the order holds."""
    problems = []
    draw = read(MAP_GML)
    body = draw[draw.find("function pp_map_draw("):]
    body = body[:body.find("\n}")]
    if body.find("PP_TILE_PLANE_GROUND") < 0 or body.find("PP_TILE_PLANE_GROUND") > body.find("PP_TILE_PLANE_PROPS"):
        problems.append("pp_map_draw does not draw the ground plane before the props plane")
    if "PP_TILE_PLANE_ABOVE" in body:
        problems.append("pp_map_draw draws the above plane, so the hero cannot be between the planes")
    above = draw[draw.find("function pp_map_draw_above("):]
    above = above[:above.find("\n}")]
    if "PP_TILE_PLANE_ABOVE" not in above:
        problems.append("pp_map_draw_above does not draw the above plane")

    world = read(OVERWORLD_GML)
    view = world[world.find("function pp_overworld_draw("):]
    view = view[:view.find("\nfunction ", 10)]
    order = [view.find("pp_map_draw("), view.find("pp_overworld_draw_hero("), view.find("pp_map_draw_above(")]
    if min(order) < 0:
        problems.append("pp_overworld_draw is missing one of the three: the map, the hero, the above plane")
    elif order != sorted(order):
        problems.append("pp_overworld_draw calls the map, the hero and the above plane out of order")
    return problems


def compose(row: dict, table: dict, sheet, hero, with_hero: bool) -> tuple:
    """One 256x240 frame, composed in the order pp_overworld_draw draws it: ground, props, (the hero), above."""
    from PIL import Image

    set_name = room_set(row.get("room_palette", ""))
    cols = 8
    spawn = (row.get("spawns") or {}).get("start", {"x": 0, "y": 0})
    cam_x = max(0, min(row["width"] - VIEW_W, spawn["x"] - VIEW_W // 2))
    cam_y = max(0, min(row["height"] - VIEW_H, spawn["y"] - VIEW_H // 2))

    frame = Image.new("RGBA", (VIEW_W * TILE, VIEW_H * TILE), (0, 0, 0, 255))
    drawn = []
    counts = {0: 0, 1: 0, 2: 0}
    for plane in (0, 1):
        for ty in range(cam_y, cam_y + VIEW_H):
            for tx in range(cam_x, cam_x + VIEW_W):
                ch = row["tiles"][ty][tx]
                gid, tile_plane, _group = table[set_name].get(ch, (table[set_name]["."] if "." in table[set_name] else None))
                counts[tile_plane] += 1
                if tile_plane != plane:
                    continue
                sx = (gid % cols) * TILE
                sy = (gid // cols) * TILE
                frame.paste(sheet.crop((sx, sy, sx + TILE, sy + TILE)),
                            ((tx - cam_x) * TILE, (ty - cam_y) * TILE))
                drawn.append((tx, ty, ch, gid))

    # The hero, 12x12 standing in a 16x16 tile, drawn where pp_overworld_draw_hero puts him.
    hx = (spawn["x"] - cam_x) * TILE + 2
    hy = (spawn["y"] - cam_y) * TILE + 2
    if with_hero:
        frame.alpha_composite(hero.crop((0, 0, TILE, TILE)), (hx, hy))
    hero_box = (hx, hy, 12, 12)

    for ty in range(cam_y, cam_y + VIEW_H):
        for tx in range(cam_x, cam_x + VIEW_W):
            ch = row["tiles"][ty][tx]
            fallback = table[set_name]["."] if "." in table[set_name] else None
            gid, tile_plane, _group = table[set_name].get(ch, fallback)
            counts[tile_plane] += 1
            if tile_plane != 2:
                continue
            sx = (gid % cols) * TILE
            sy = (gid // cols) * TILE
            frame.alpha_composite(sheet.crop((sx, sy, sx + TILE, sy + TILE)),
                                  ((tx - cam_x) * TILE, (ty - cam_y) * TILE))
            drawn.append((tx, ty, ch, gid))
    return frame, set_name, (cam_x, cam_y), counts, hero_box


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--id", default="southampton_town_quay", help="the map id to probe")
    parser.add_argument("--rows", default=MAPS_JSON, help="the file holding the map rows (default data/maps/all.json)")
    parser.add_argument("--no-frame", action="store_true", help="skip the composed frame")
    args = parser.parse_args(argv)

    for path in (TABLE_GML, MAP_GML, OVERWORLD_GML, QUAY_JSON, QUAY_PNG):
        if not os.path.isfile(path):
            print("probe: missing %s" % os.path.relpath(path, ROOT), file=sys.stderr)
            return 2

    table = gml_rows(TABLE_GML)
    manifest = load(QUAY_JSON)
    tiles = {tile["character"]: tile for tile in manifest["tiles"]}
    tilecount = int(manifest["tilecount"])
    row, source = map_row(args.rows, args.id)
    set_name = room_set(row.get("room_palette", ""))
    failures = []

    print("map: %s (%dx%d) read from %s" % (row["id"], row["width"], row["height"],
                                            os.path.relpath(source, ROOT).replace(os.sep, "/")))
    print("room palette: %r, tile set: %r, sheet: %s (%d tiles, %d columns)"
          % (row.get("room_palette", ""), set_name, manifest["name"], tilecount, manifest["columns"]))

    used = {}
    for line in row["tiles"]:
        for ch in line:
            used[ch] = used.get(ch, 0) + 1
    unnamed = sorted(ch for ch in used if ch not in table[set_name])
    print("tile characters: %d uses of %d characters (%s)"
          % (sum(used.values()), len(used), " ".join(sorted(used))))
    print("characters the %s table does not name: %d%s"
          % (set_name, len(unnamed), "" if not unnamed else " (" + " ".join(unnamed) + ")"))
    if len(unnamed) > 8:
        failures.append("%d characters are not in the %s table, more than the 8 the card allows"
                        % (len(unnamed), set_name))

    print("every drawn character against the sheet:")
    for ch in sorted(used):
        gid, plane, group = table[set_name].get(ch, (None, None, None))
        if gid is None:
            print("  %r: unnamed, draws the set default" % ch)
            continue
        art = next((t for t in manifest["tiles"] if t["index"] == gid), None)
        same = art is not None and art["character"] == ch
        print("  %r: gid %d %s on the %s plane%s"
              % (ch, gid, art["name"] if art else "NO ART AT THAT INDEX", PLANE_NAME[plane],
                 "" if same else " (the sheet names a different character at that index)"))
        if not 0 <= gid < tilecount:
            failures.append("character %r draws gid %d, outside the sheet's %d tiles" % (ch, gid, tilecount))
        elif set_name != "office" and not same:
            failures.append("character %r draws gid %d, which the sheet calls %r"
                            % (ch, gid, art["name"] if art else "nothing"))

    problems = order_check()
    print("layer order: ground and props before the hero, above after him: %s"
          % ("holds" if not problems else "; ".join(problems)))
    failures.extend(problems)

    if not args.no_frame:
        from PIL import Image

        with Image.open(QUAY_PNG) as sheet_image:
            sheet = sheet_image.convert("RGBA")
        with Image.open(HERO_PNG) as hero_image:
            hero = hero_image.convert("RGBA")
        frame, set_name, cam, counts, hero_box = compose(row, table, sheet, hero, False)
        os.makedirs(os.path.dirname(FRAME_OUT), exist_ok=True)
        frame.convert("RGB").save(FRAME_OUT)
        print("frame: %s at %dx%d, camera %s, planes ground %d props %d above %d"
              % (os.path.relpath(FRAME_OUT, ROOT).replace(os.sep, "/"), frame.width, frame.height,
                 cam, counts[0], counts[1], counts[2]))

        import nes_composite_check as composite

        palette_path = composite.default_palette_path(ROOT)
        palette = composite.load_palette(palette_path)
        with open(palette_path, "r", encoding="utf-8-sig") as handle:
            palette["entries"] = json.load(handle).get("entries")
        checked, info = composite.load_frame(FRAME_OUT, palette["allowed"], "1")
        report = composite.check_frame(checked, palette, None, None)
        report["frame"] = info
        for line in composite.describe(report, info):
            print("  " + line.strip())
        colours = report["screen"]["colours"]
        print("  screen colours: %d (cap 16)" % colours)
        if colours > 16:
            failures.append("the frame spends %d colours, over the 16 a screen may hold" % colours)
        if not report["ok"]:
            failures.append("tools/nes_composite_check.py refuses the frame: %d problems"
                            % len(report["problems"]))
        print("  note: this gated frame is the tile planes only. A hero drawn over the paving adds his eight sprite"
              " colours to the 16x16 block under him, and the block rule counts every pixel in a block, so the hero"
              " frame is written beside it ungated: %s"
              % os.path.relpath(HERO_FRAME, ROOT).replace(os.sep, "/"))

        # The same frame with the hero between the planes, kept as the look at artifact of the layer order.
        hero_frame, _set, _cam, _counts, _box = compose(row, table, sheet, hero, True)
        hero_frame.convert("RGB").save(HERO_FRAME)
        checked_hero, info_hero = composite.load_frame(HERO_FRAME, palette["allowed"], "1")
        hero_report = composite.check_frame(checked_hero, palette, None, None)
        print("  hero frame: %s, hero at %d,%d, %d colours on screen, %d block(s) over the background rule"
              " (the sprite over the ground, as named above)"
              % (os.path.relpath(HERO_FRAME, ROOT).replace(os.sep, "/"), hero_box[0], hero_box[1],
                 hero_report["screen"]["colours"], len(hero_report["background"]["problems"])))
        if hero_report["screen"]["colours"] > 16:
            failures.append("the hero frame spends %d colours, over the 16 a screen may hold"
                            % hero_report["screen"]["colours"])
        hero_tile = row["tiles"][(hero_box[1] + 6) // TILE + cam[1]][(hero_box[0] + 6) // TILE + cam[0]]
        print("  hero stands on %r, which the table puts on the %s plane, so he is drawn over it"
              % (hero_tile, PLANE_NAME[table[set_name][hero_tile][1]]))

    print()
    if failures:
        for failure in failures:
            print("FAIL: %s" % failure)
        return 1
    print("PASS: every check in the card's list holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
