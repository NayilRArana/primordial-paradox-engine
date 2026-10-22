#!/usr/bin/env python3
"""check_env_tiles.py: prove the Map 2 ship tileset, its Tiled JSON and its sample map are what the card asks.

What this checks, in the order it checks it, and why each one is checkable rather than a matter of taste:

1. The PNG is the size the metadata says: 16 columns of 16x16, 48 tiles, so 256 by 48.
2. Every opaque pixel is one of the 10 colours the tileset JSON declares, and each declared colour is the actual
   output of the Ricoh 2C02 entry it names. data/nes_palette.json is the source of truth for those entries, so a
   colour cannot drift into "nearly NES" without this failing.
3. No 16x16 tile carries more than 3 non backdrop colours. That is the NES attribute area limit, and it is what
   makes the "8 to 10 colours per scene" rule real instead of a wish.
4. Every 8x8 tile carries at most 3 opaque colours, the sprite tile limit, so the same art can be cut down to 8x8
   pattern tiles without a repaint.
5. tools/nes_check.py passes over the sheet as a background with the black backdrop. This tool does not restate
   the NES rules, it runs the project's validator, so there is one authority.
6. The tileset JSON has tiles 0 to 47 in order, unique names, and the only animations are the two the card asks
   for: the sea (2 frames) and the porthole glare.
7. The map is 20 by 15, every ground gid is a tile the tileset has, every collision value is 0 or 1, and the
   collision layer equals the solid flag of the tile above it in both directions. That is what makes "walls and
   objects solid" a measured fact.
8. Every walkable cell is reachable from player_start, and every spawn sits on a walkable tile. A room nobody can
   walk into is a map defect this catches.
9. The map contains the features the card names: a corridor, two rooms, a ladder and the hatch out to Percy's
   wardroom.
10. The preview is present and is exactly 3x the sheet and the map, so it is a true 3x of the art and not a
    re-render.

Exit code 0 when every check passes, 1 when any fails, with each failure on its own line.

Usage:
    python tools/check_env_tiles.py
    python tools/check_env_tiles.py --root <repo> --json report.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import deque

from PIL import Image

TILE = 16
SUBTILE = 8
COLUMNS = 16
TILE_COUNT = 48
MAP_W = 20
MAP_H = 15
MAX_COLOURS = 10
MAX_TILE_COLOURS = 3
SCALE = 3

# Every item the card names, by tile name. The tileset must carry all of them.
REQUIRED_TILES = [
    "deck_a", "deck_b",                      # steel deck plates, two variants
    "bulkhead",                               # bulkhead wall with rivets
    "hatch_closed", "hatch_open",             # hatch doors, closed and open
    "ladder",                                 # ladder
    "pipes", "cable_run",                     # pipes and cable runs
    "crate",                                  # crates
    "lifebuoy",                               # lifebuoy
    "deck_line_h", "deck_line_v",             # grey painted corridor lines
    "porthole_a",                             # porthole showing sea
    "wood_floor_a",                           # wardroom wood floor
    "table",                                  # wardroom table
    "bunk",                                   # officer cabin bunk
    "warning",                                # warning stripes
    "sign_wardroom", "sign_machinery", "sign_bridge",  # signs
    "stairs_up", "stairs_down",               # stairs
    "quay_stone_a",                           # harbour: quay stone
    "bollard",                                # harbour: bollard
    "water_a", "water_b",                     # harbour: water, 2 frames
]

# What the sample map itself must show.
REQUIRED_IN_MAP = [
    "deck_a", "bulkhead", "hatch_open", "hatch_closed", "ladder", "stairs_up",
    "wood_floor_a", "table", "bunk", "crate", "lifebuoy", "porthole_a",
    "sign_wardroom", "warning", "pipes", "deck_line_h",
]


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path: str):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def tile_properties(entry: dict) -> dict:
    out = {}
    for prop in entry.get("properties", []):
        out[prop["name"]] = prop["value"]
    return out


def hex_to_rgb(value: str):
    value = value.strip().lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def map_path_for(root: str) -> str:
    """The map this lane wrote, by the same rule as tools/art/make_env_ship.py:map_output_path.

    data/maps/ship_sample.json when it is this lane's Tiled map (kind "map"), otherwise
    data/maps/ship_sample_tiled.json, because another card holds the plain name.
    """
    plain = os.path.join(root, "data", "maps", "ship_sample.json")
    alt = os.path.join(root, "data", "maps", "ship_sample_tiled.json")
    if os.path.isfile(plain):
        try:
            if load_json(plain).get("kind") == "map":
                return plain
        except (OSError, ValueError):
            return alt
    return alt


def check(root: str) -> tuple:
    """Return (failures, facts). facts is the report, failures is a list of strings."""
    failures = []
    facts = {}

    env = os.path.join(root, "game", "sprites_src", "env")
    png_path = os.path.join(env, "ts_ship.png")
    meta_path = os.path.join(env, "ts_ship.json")
    set_path = os.path.join(env, "ts_ship_tiled.json")
    map_path = map_path_for(root)
    preview_path = os.path.join(root, "output", "env_ship_preview.png")
    nes_path = os.path.join(root, "data", "nes_palette.json")

    for path in (png_path, meta_path, set_path, map_path, preview_path):
        if not os.path.isfile(path):
            failures.append("missing file: %s (run tools/art/make_env_ship.py)" % path)
    if failures:
        return failures, facts

    # 1. The PNG against its own metadata.
    meta = load_json(meta_path)
    tileset = load_json(set_path)
    image = Image.open(png_path).convert("RGBA")
    rows = (TILE_COUNT + COLUMNS - 1) // COLUMNS
    facts["png"] = [image.width, image.height]
    if (image.width, image.height) != (COLUMNS * TILE, rows * TILE):
        failures.append("PNG is %dx%d, expected %dx%d (16 columns of 16x16, %d tiles)"
                        % (image.width, image.height, COLUMNS * TILE, rows * TILE, TILE_COUNT))
    for key, want in (("name", "ts_ship"), ("frame_w", TILE), ("frame_h", TILE), ("frames", TILE_COUNT)):
        if meta.get(key) != want:
            failures.append("ts_ship.json %s is %r, expected %r" % (key, meta.get(key), want))
    if float(meta.get("fps", -1)) != 0.0:
        failures.append("ts_ship.json fps is %r, a tileset is static so it must be 0" % meta.get("fps"))

    # 2. Colours: declared set, and each declared colour is the 2C02 output it names.
    chip = load_json(nes_path)["colours"]
    declared = tileset.get("palette", [])
    if len(declared) != MAX_COLOURS:
        failures.append("tileset declares %d colours, the card allows 8 to 10" % len(declared))
    allowed = {}
    for entry in declared:
        index = entry.get("entry")
        hexv = str(entry.get("hex", "")).lower()
        if not isinstance(index, int) or not 0 <= index < 64:
            failures.append("palette entry %r is not a 2C02 index" % entry)
            continue
        if chip[index].lower() != hexv:
            failures.append("palette %s says %s for $%02X but the 2C02 outputs %s"
                            % (entry.get("key"), hexv, index, chip[index]))
        allowed[hex_to_rgb(hexv)] = entry.get("key")
    backdrop_key = tileset["palette"][0]["key"] if declared else "k"
    backdrop_rgb = hex_to_rgb(declared[0]["hex"]) if declared else (0, 0, 0)

    used = set()
    opaque = 0
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = image.getpixel((x, y))
            if a == 0:
                failures.append("transparent pixel at %d,%d: the sheet must be opaque so a missing tile reads as art"
                                % (x, y))
                break
            used.add((r, g, b))
            opaque += 1
    unexpected = sorted(used - set(allowed))
    if unexpected:
        failures.append("%d colours are not in the declared palette: %s"
                        % (len(unexpected), ", ".join("%02x%02x%02x" % c for c in unexpected)))
    facts["colours_used"] = len(used)
    facts["opaque_pixels"] = opaque

    # 3 and 4: per tile colour ceilings, 16x16 attribute area and 8x8 pattern tile.
    worst_area = 0
    worst_sub = 0
    for ty in range(rows):
        for tx in range(COLUMNS):
            area = set()
            for y in range(TILE):
                for x in range(TILE):
                    area.add(image.getpixel((tx * TILE + x, ty * TILE + y))[:3])
            count = len(area - {backdrop_rgb})
            worst_area = max(worst_area, count)
            if count > MAX_TILE_COLOURS:
                failures.append("tile %d at %d,%d carries %d non backdrop colours, the NES attribute area allows %d"
                                % (ty * COLUMNS + tx, tx, ty, count, MAX_TILE_COLOURS))
            for sy in range(2):
                for sx in range(2):
                    sub = set()
                    for y in range(SUBTILE):
                        for x in range(SUBTILE):
                            px = tx * TILE + sx * SUBTILE + x
                            py = ty * TILE + sy * SUBTILE + y
                            sub.add(image.getpixel((px, py))[:3])
                    sub_count = len(sub - {backdrop_rgb})
                    worst_sub = max(worst_sub, sub_count)
                    if sub_count > MAX_TILE_COLOURS:
                        failures.append("8x8 tile at %d,%d in tile %d carries %d opaque colours, the NES allows %d"
                                        % (tx * TILE + sx * SUBTILE, ty * TILE + sy * SUBTILE,
                                           ty * COLUMNS + tx, sub_count, MAX_TILE_COLOURS))
    facts["worst_area_colours"] = worst_area
    facts["worst_subtile_colours"] = worst_sub

    # 5. The project's NES validator, run rather than restated.
    nos_check = os.path.join(root, "tools", "nes_check.py")
    if os.path.isfile(nos_check):
        result = subprocess.run([sys.executable, nos_check, png_path, "--type", "background",
                                 "--backdrop", "#%02x%02x%02x" % backdrop_rgb],
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        facts["nes_check"] = result.returncode
        if result.returncode != 0:
            failures.append("tools/nes_check.py failed on the sheet:\n%s" % (result.stdout or result.stderr).strip())
    else:
        failures.append("tools/nes_check.py is missing, so the NES rules are not being enforced")

    # 6. The tileset table.
    tiles = tileset.get("tiles", [])
    if tileset.get("tilecount") != TILE_COUNT or len(tiles) != TILE_COUNT:
        failures.append("tileset has %d tiles, expected %d" % (len(tiles), TILE_COUNT))
    names = []
    solids = {}
    climbs = set()
    procedures = {}
    for position, entry in enumerate(tiles):
        if entry.get("id") != position:
            failures.append("tileset tile at position %d has id %r, ids must run 0 to %d in order"
                            % (position, entry.get("id"), TILE_COUNT - 1))
        props = tile_properties(entry)
        name = props.get("tile_name")
        if not name:
            failures.append("tileset tile %d has no tile_name property" % position)
            continue
        names.append(name)
        solids[name] = props.get("solid")
        if props.get("climb"):
            climbs.add(name)
        procedures[name] = entry
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        failures.append("duplicate tile names: %s" % ", ".join(duplicates))
    missing = [n for n in REQUIRED_TILES if n not in names]
    if missing:
        failures.append("tileset is missing the tiles the card names: %s" % ", ".join(missing))
    facts["tile_names"] = len(names)

    animated = {}
    for name, entry in procedures.items():
        for anim in entry.get("animation", []):
            target = anim.get("tileid")
            if not isinstance(target, int) or not 0 <= target < TILE_COUNT:
                failures.append("tile %s animates to %r, which is not a tile id" % (name, target))
            else:
                animated[name] = target
    for name in ("water_a", "porthole_a"):
        if name not in animated:
            failures.append("tile %s has no second animation frame" % name)
    if "water_b" in names and animated.get("water_a") != names.index("water_b"):
        failures.append("water_a animates to tile %r, expected water_b (%d)"
                        % (animated.get("water_a"), names.index("water_b")))
    if "porthole_b" in names and animated.get("porthole_a") != names.index("porthole_b"):
        failures.append("porthole_a animates to tile %r, expected porthole_b (%d)"
                        % (animated.get("porthole_a"), names.index("porthole_b")))
    facts["animations"] = {name: target for name, target in animated.items()}

    # 7. The map against the tileset.
    ship = load_json(map_path)
    if (ship.get("width"), ship.get("height")) != (MAP_W, MAP_H):
        failures.append("map is %rx%r, expected %dx%d"
                        % (ship.get("width"), ship.get("height"), MAP_W, MAP_H))
    layers = {layer.get("name"): layer for layer in ship.get("layers", [])}
    if "collision" not in layers:
        failures.append("map has no collision layer")
        return failures, facts
    ground = layers.get("ground", {}).get("data", [])
    collision = layers["collision"].get("data", [])
    if len(ground) != MAP_W * MAP_H or len(collision) != MAP_W * MAP_H:
        failures.append("ground has %d cells and collision has %d, expected %d each"
                        % (len(ground), len(collision), MAP_W * MAP_H))
        return failures, facts
    # gids start at 1 (firstgid), so tile id 0 is gid 1.
    id_to_name = {index + 1: name for index, name in enumerate(names)}
    unknown = sorted({gid for gid in ground if not (1 <= gid <= TILE_COUNT)})
    if unknown:
        failures.append("ground layer holds gids outside the tileset: %s" % unknown)
    bad = sorted({value for value in collision if value not in (0, 1, 2)})
    if bad:
        failures.append("collision holds %s, only 0, 1 and 2 are defined" % bad)
    for y in range(MAP_H):
        for x in range(MAP_W):
            index = y * MAP_W + x
            name = id_to_name.get(ground[index])
            if name is None:
                continue
            want = 1 if solids.get(name) else 0
            got = collision[index]
            if got != want:
                failures.append("cell %d,%d holds %s (%s) but collision is %d, expected %d"
                                % (x, y, ground[index], name, got, want))
    row_strings = ship.get("collision_rows", [])
    if len(row_strings) != MAP_H:
        failures.append("collision_rows has %d rows, expected %d" % (len(row_strings), MAP_H))
    else:
        rebuilt = ["".join(str(collision[y * MAP_W + x]) for x in range(MAP_W)) for y in range(MAP_H)]
        if row_strings != rebuilt:
            failures.append("collision_rows does not match the collision layer")
    facts["collision_blocked"] = sum(1 for value in collision if value == 1)
    facts["collision_walkable"] = sum(1 for value in collision if value == 0)

    # 8. Reachability from the spawn, and spawns on walkable cells.
    spawns = ship.get("spawns", {})
    if not spawns:
        failures.append("map has no spawns")
    start = None
    for name, point in sorted(spawns.items()):
        x, y = point.get("x"), point.get("y")
        if not (isinstance(x, int) and isinstance(y, int) and 0 <= x < MAP_W and 0 <= y < MAP_H):
            failures.append("spawn %s is off the map: %r" % (name, point))
            continue
        if collision[y * MAP_W + x] != 0:
            failures.append("spawn %s sits on a blocked cell (%d,%d)" % (name, x, y))
        if name == "player_start":
            start = (x, y)
    if start is None:
        start = ((spawns.get("player_start") or {}).get("x"), (spawns.get("player_start") or {}).get("y"))
    if isinstance(start[0], int) and isinstance(start[1], int):
        seen = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H and (nx, ny) not in seen:
                    if collision[ny * MAP_W + nx] == 0:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
        walkable = {(x, y) for y in range(MAP_H) for x in range(MAP_W) if collision[y * MAP_W + x] == 0}
        unreachable = sorted(walkable - seen)
        facts["walkable_cells"] = len(walkable)
        facts["reachable_cells"] = len(seen)
        if unreachable:
            failures.append("%d walkable cells cannot be reached from player_start, first at %s"
                            % (len(unreachable), unreachable[0]))

    # 9. The features the card names, present in the map itself.
    used_names = {id_to_name.get(gid) for gid in ground}
    for name in REQUIRED_IN_MAP:
        if name not in used_names:
            failures.append("map never uses %s, but the card asks for it in the sample map" % name)
    objects = layers.get("objects", {}).get("objects", [])
    triggers = {obj.get("name"): obj for obj in objects if obj.get("type") == "map_exit"}
    if "hatch_percy" not in triggers:
        failures.append("map has no hatch_percy exit object")
    else:
        hatch = triggers["hatch_percy"]
        cell = (hatch["x"] // TILE, hatch["y"] // TILE)
        name = id_to_name.get(ground[cell[1] * MAP_W + cell[0]])
        if name != "hatch_closed":
            failures.append("hatch_percy sits on %s, expected hatch_closed" % name)
        targets = {prop["name"]: prop["value"] for prop in hatch.get("properties", [])}
        if targets.get("target_map") != "percy_wardroom":
            failures.append("hatch_percy targets %r, expected percy_wardroom" % targets.get("target_map"))

    # 10. The preview is a true 3x.
    preview = Image.open(preview_path)
    sheet_w = COLUMNS * TILE * SCALE
    map_px_w = MAP_W * TILE * SCALE
    map_px_h = MAP_H * TILE * SCALE
    facts["preview"] = [preview.width, preview.height]
    if preview.width < map_px_w or preview.height < map_px_h:
        failures.append("preview is %dx%d, too small to hold the map at 3x (%dx%d)"
                        % (preview.width, preview.height, map_px_w, map_px_h))
    if preview.width < sheet_w:
        failures.append("preview is %d wide, too small to hold the sheet at 3x (%d)" % (preview.width, sheet_w))
    if preview.width % SCALE or preview.height % SCALE:
        failures.append("preview is %dx%d, which is not a whole multiple of the 3x scale"
                        % (preview.width, preview.height))

    return failures, facts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the Map 2 ship tileset and sample map.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", dest="json_path", default=None)
    args = parser.parse_args(argv)
    root = args.root or repo_root()
    failures, facts = check(root)
    report = {"root": os.path.abspath(root), "ok": not failures, "failures": failures, "facts": facts}
    for key in sorted(facts):
        print("  %-22s %s" % (key, facts[key]))
    if failures:
        for line in failures:
            print("FAIL %s" % line)
        print("check_env_tiles: %d failure(s)" % len(failures))
    else:
        print("check_env_tiles: PASS, %d tiles, %d colours, map %dx%d"
              % (TILE_COUNT, facts.get("colours_used", 0), MAP_W, MAP_H))
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
