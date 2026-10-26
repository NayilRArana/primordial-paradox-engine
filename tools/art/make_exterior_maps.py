#!/usr/bin/env python3
"""make_exterior_maps.py: turn the three OpenStreetMap drafts into playable ts_exterior sample maps.

The OSM card (MAP-OSM) left three Tiled drafts under data/maps/osm/. This script crops a 32x30 window out of
each draft, keeps the street layout the survey actually found (roads, buildings, park, water, quay, doors),
dresses it with the tiles ts_exterior.png provides, and writes:

  data/maps/westminster_sample.json     London street by Big Ben, tower pieces standing in the block
  data/maps/winchester_sample.json      Winchester High Street, cobbles, cathedral pieces
  data/maps/southampton_sample.json     Town Quay, quay stone, railing, animated water
  data/palettes/scene_<place>.json      the 4 NES background palettes that scene spends
  output/<place>_sample_preview_2x.png  the whole map at 2x for a human to look at
  output/<place>_frame.png              256x240 viewport at the spawn, what the PPU would show
  output/<place>_frame_3x.png           the same frame at 3x

Every map obeys data/schemas/maps.schema.json, uses only tiles from ts_exterior.json, and carries a collision
layer derived from the tileset's solid flags. The crop is chosen by a fixed score, so two runs give the same maps.

Usage:
    python tools/art/make_exterior_maps.py --root <repo>
"""

from __future__ import annotations

import argparse
import json
import os
from collections import deque

from PIL import Image

TILE = 16
MAP_W = 32
MAP_H = 30
FRAME_W = 16
FRAME_H = 15
SCALE_PREVIEW = 2
SCALE_FRAME = 3
LEGEND_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ@#"

# OSM gid meaning, from tools/osm_to_map.py TERRAIN_GID.
OSM = {"ground": 1, "park": 2, "water": 3, "quay": 4, "rail": 5, "path": 6,
       "road_minor": 7, "road_major": 8, "building": 9, "door": 10}

PLACES = [
    {
        "id": "westminster_sample",
        "osm": "westminster_big_ben",
        "name": "Westminster, the street by Big Ben",
        "scene": "westminster",
        "landmark": "big_ben",
        "want_water": False,
        "allowed_palettes": ["bg0_stone", "bg1_brick", "bg2_green", "bg4_red"],
        "notes": "London: asphalt and kerbs, brick blocks, a red phone box, a post box and the clock tower",
    },
    {
        "id": "winchester_sample",
        "osm": "winchester_high_street",
        "name": "Winchester High Street",
        "scene": "winchester",
        "landmark": "cathedral",
        "want_water": False,
        "allowed_palettes": ["bg0_stone", "bg1_brick", "bg2_green", "bg4_red"],
        "notes": "cobbles down the high street, shop fronts with awnings, cathedral masonry, a phone box",
    },
    {
        "id": "southampton_sample",
        "osm": "southampton_town_quay",
        "name": "Southampton, Town Quay",
        "scene": "southampton",
        "landmark": None,
        "want_water": True,
        "allowed_palettes": ["bg0_stone", "bg1_brick", "bg2_green", "bg3_water"],
        "notes": "quay stone, railings along the water, open water on two animation frames, brick sheds",
    },
]


def repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def load_tileset(root: str) -> dict:
    path = os.path.join(root, "game", "sprites_src", "env", "ts_exterior.json")
    with open(path, encoding="utf-8") as handle:
        meta = json.load(handle)
    by_name = {tile["name"]: tile for tile in meta["tiles"]}
    return meta, by_name


def load_osm(root: str, name: str) -> dict:
    path = os.path.join(root, "data", "maps", "osm", name + ".json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def grid_of(draft: dict) -> list[list[int]]:
    layer = next(l for l in draft["layers"] if l.get("type") == "tilelayer")
    w, h = draft["width"], draft["height"]
    return [[layer["data"][y * w + x] for x in range(w)] for y in range(h)]


def building_column(grid: list[list[int]], x: int, y: int, height: int) -> bool:
    h = len(grid)
    if y + height > h:
        return False
    return all(grid[y + i][x] == OSM["building"] for i in range(height))


def building_block(grid: list[list[int]], x: int, y: int, w: int, h: int) -> bool:
    return all(grid[y + j][x + i] == OSM["building"]
               for j in range(h) for i in range(w) if y + j < len(grid) and x + i < len(grid[0]))


def crop_score(grid: list[list[int]], x0: int, y0: int, place: dict) -> int:
    counts = {name: 0 for name in OSM}
    for y in range(y0, y0 + MAP_H):
        for x in range(x0, x0 + MAP_W):
            gid = grid[y][x]
            for name, value in OSM.items():
                if gid == value:
                    counts[name] += 1
    kinds = sum(1 for name, value in counts.items() if value > 2)
    score = 6 * kinds
    score += min(counts["building"], 180)
    score += min(counts["road_major"], 60) + min(counts["road_minor"], 40)
    score += min(counts["park"], 50) + min(counts["path"], 40)
    score += 4 * min(counts["door"], 4)
    if place["want_water"]:
        score += min(counts["water"], 220) + min(counts["quay"], 80)
    else:
        score -= counts["water"]
    if place["landmark"] == "big_ben":
        for y in range(y0, y0 + MAP_H - 4):
            for x in range(x0, x0 + MAP_W):
                if building_column(grid, x, y, 4) and y + 4 < len(grid) and grid[y + 4][x] != OSM["building"]:
                    score += 40
                    break
    if place["landmark"] == "cathedral":
        for y in range(y0, y0 + MAP_H - 2):
            for x in range(x0, x0 + MAP_W - 4):
                if building_block(grid, x, y, 5, 3):
                    score += 40
                    break
    return score


def best_crop(grid: list[list[int]], place: dict) -> tuple[int, int]:
    h, w = len(grid), len(grid[0])
    best = None
    for y0 in range(0, h - MAP_H + 1):
        for x0 in range(0, w - MAP_W + 1):
            score = crop_score(grid, x0, y0, place)
            if best is None or score > best[0]:
                best = (score, x0, y0)
    return best[1], best[2]


def pick(names: list[str], x: int, y: int, salt: int = 0) -> str:
    return names[(x * 7 + y * 13 + salt) % len(names)]


def remap_cell(name: str, x: int, y: int, place: dict) -> str:
    scene = place["scene"]
    if name == "ground":
        if scene == "winchester":
            return pick(["pavement_a", "cobble_b", "pavement_b"], x, y)
        return pick(["pavement_a", "pavement_b"], x, y)
    if name == "park":
        return pick(["grass_a", "grass_b"], x, y)
    if name == "path":
        return pick(["pavement_b", "pavement_a"], x, y) if scene != "winchester" else pick(["cobble_a", "cobble_c"], x, y)
    if name == "water":
        # A place that does not spend the water palette (bg3_water) cannot draw water: the OSM draft carries a
        # stray river cell or two, and one stray tile would cost the scene a whole background palette.
        if "bg3_water" not in place["allowed_palettes"]:
            return pick(["cobble_c", "pavement_b"], x, y)
        return pick(["water_a", "water_b"], x, y)
    if name == "quay":
        return pick(["quay_stone", "quay_flag"], x, y)
    if name == "rail":
        return pick(["cobble_b", "gutter"], x, y)
    if name in ("road_minor", "road_major"):
        return pick(["road_a", "road_b"], x, y)
    if name == "building":
        return pick(["brick_a", "brick_b", "brick_c"], x, y)
    return "pavement_a"


def build_ground(grid: list[list[int]], x0: int, y0: int, place: dict) -> list[list[str]]:
    out = []
    for y in range(MAP_H):
        row = []
        for x in range(MAP_W):
            gid = grid[y0 + y][x0 + x]
            name = next((n for n, v in OSM.items() if v == gid), "ground")
            if name == "door":
                row.append(pick(["door_a", "door_b"], x, y))
            elif name == "building":
                above = grid[y0 + y - 1][x0 + x] if y0 + y > 0 else 0
                if above != OSM["building"]:
                    row.append(pick(["wall_top", "brick_cornice"], x, y))
                else:
                    row.append(pick(["brick_a", "brick_b", "brick_c", "window_lit", "window_dark"], x, y))
            else:
                row.append(remap_cell(name, x, y, place))
        out.append(row)
    return out


def is_road(tile: str) -> bool:
    return tile in ("road_a", "road_b", "road_line", "road_line_h", "crosswalk")


def add_kerbs(tiles: list[list[str]]) -> None:
    walkable = ("pavement_a", "pavement_b", "pavement_grate", "cobble_a", "cobble_b", "cobble_c")
    for y in range(MAP_H):
        for x in range(MAP_W):
            if tiles[y][x] not in walkable:
                continue
            east = x + 1 < MAP_W and is_road(tiles[y][x + 1])
            west = x - 1 >= 0 and is_road(tiles[y - 0][x - 1])
            if east and not west:
                tiles[y][x] = "kerb_w"
            elif west and not east:
                tiles[y][x] = "kerb_e"


def place_landmark(tiles: list[list[str]], grid: list[list[int]], x0: int, y0: int, place: dict) -> bool:
    if place["landmark"] == "big_ben":
        best = None
        for y in range(MAP_H - 4, 1, -1):
            for x in range(MAP_W):
                if all(tiles[y + i][x] in ("brick_a", "brick_b", "brick_c", "window_lit", "window_dark",
                                           "wall_top", "brick_cornice") for i in range(4)):
                    below = tiles[y + 4][x] if y + 4 < MAP_H else "blank"
                    if below not in ("water_a", "water_b", "water_deep"):
                        score = abs(x - MAP_W // 2) + abs(y - (MAP_H - 8))
                        if best is None or score < best[0]:
                            best = (score, x, y)
        if best is None:
            return False
        _, x, y = best
        tiles[y][x] = "tower_roof"
        tiles[y + 1][x] = "tower_clock"
        tiles[y + 2][x] = "tower_mid"
        tiles[y + 3][x] = "tower_base"
        return True
    if place["landmark"] == "cathedral":
        best = None
        for y in range(MAP_H - 3):
            for x in range(MAP_W - 4):
                if all(tiles[y + j][x + i] in ("brick_a", "brick_b", "brick_c", "window_lit", "window_dark",
                                               "wall_top", "brick_cornice")
                       for j in range(3) for i in range(5)):
                    score = abs(x - MAP_W // 2) + abs(y - (MAP_H // 3))
                    if best is None or score < best[0]:
                        best = (score, x, y)
        if best is None:
            return False
        _, x, y = best
        rows = [
            ["cath_buttress", "cath_wall", "cath_wall", "cath_wall", "cath_buttress"],
            ["cath_buttress", "cath_window", "cath_window", "cath_window", "cath_buttress"],
            ["cath_buttress", "cath_wall", "cath_door", "cath_wall", "cath_buttress"],
        ]
        for j, line in enumerate(rows):
            for i, tile in enumerate(line):
                tiles[y + j][x + i] = tile
        return True
    return False


def add_crosswalk(tiles: list[list[str]]) -> tuple[int, int] | None:
    for y in range(2, MAP_H - 2):
        for x in range(2, MAP_W - 2):
            if not is_road(tiles[y][x]) or tiles[y][x] == "crosswalk":
                continue
            vertical = is_road(tiles[y - 1][x]) and is_road(tiles[y + 1][x])
            horizontal = is_road(tiles[y][x - 1]) and is_road(tiles[y][x + 1])
            if vertical and not horizontal:
                tiles[y][x] = "crosswalk"
                if is_road(tiles[y][x + 1]):
                    tiles[y][x + 1] = "crosswalk"
                return x, y
            if horizontal and not vertical:
                tiles[y][x] = "crosswalk"
                if is_road(tiles[y + 1][x]):
                    tiles[y + 1][x] = "crosswalk"
                return x, y
    return None


def add_shop_fronts(tiles: list[list[str]], place: dict) -> None:
    for y in range(1, MAP_H - 1):
        for x in range(1, MAP_W - 1):
            tile = tiles[y][x]
            if tile not in ("brick_a", "brick_b", "brick_c", "window_lit", "window_dark"):
                continue
            south = tiles[y + 1][x]
            if south not in ("pavement_a", "pavement_b", "cobble_a", "cobble_b", "cobble_c", "kerb_w", "kerb_e"):
                continue
            if (x * 3 + y * 5) % 17 == 0:
                tiles[y][x] = "shop_front"
                if tiles[y - 1][x] in ("brick_a", "brick_b", "brick_c"):
                    tiles[y - 1][x] = "awning" if place["scene"] != "southampton" else "awning_green"
            elif (x * 3 + y * 5) % 17 == 5:
                tiles[y][x] = "shop_door"


def add_street_furniture(tiles: list[list[str]], place: dict) -> dict:
    """Deterministic furniture: a walk over the pavement in reading order, one fixture every N free cells."""
    walkable = ("pavement_a", "pavement_b", "pavement_grate", "cobble_a", "cobble_b", "cobble_c")
    used = {}
    free = [(x, y) for y in range(MAP_H - 1) for x in range(MAP_W) if tiles[y][x] in walkable]
    for index, (x, y) in enumerate(free):
        if index % 53 == 11 and "phone" not in used and place["scene"] != "southampton":
            if tiles[y - 1][x] in walkable:
                tiles[y - 1][x] = "phone_box_top"
                tiles[y][x] = "phone_box_body"
                used["phone"] = (x, y)
        elif index % 37 == 3 and "post" not in used and place["scene"] != "southampton":
            tiles[y][x] = "post_box"
            used["post"] = (x, y)
        elif index % 13 == 7:
            tiles[y][x] = "lamp_post"
            if tiles[y - 1][x] in walkable:
                tiles[y - 1][x] = "lamp_head"
            used["lamp"] = (x, y)
        elif index % 17 == 5:
            tiles[y][x] = "bollard"
        elif index % 29 == 9:
            tiles[y][x] = "bench"
        elif index % 41 == 13:
            tiles[y][x] = "sign_street"
    # railings along the water, trees and hedges in the park
    for y in range(MAP_H):
        for x in range(MAP_W):
            if tiles[y][x] in walkable or tiles[y][x] in ("quay_stone", "quay_flag"):
                touches_water = any(0 <= x + dx < MAP_W and 0 <= y + dy < MAP_H
                                    and tiles[y + dy][x + dx] in ("water_a", "water_b", "water_deep")
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if touches_water:
                    tiles[y][x] = "railing_a" if (x + y) % 2 else "railing_b"
            if tiles[y][x] in ("grass_a", "grass_b"):
                if (x * 5 + y * 3) % 23 == 0:
                    tiles[y][x] = pick(["tree_canopy_a", "tree_canopy_b", "tree_canopy_c"], x, y)
                elif (x * 5 + y * 3) % 7 == 4 and any(
                        0 <= x + dx < MAP_W and 0 <= y + dy < MAP_H
                        and tiles[y + dy][x + dx] in walkable for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    tiles[y][x] = pick(["hedge_a", "hedge_b"], x, y)
    return used


def add_traffic_light(tiles: list[list[str]], crossing: tuple[int, int] | None, place: dict) -> None:
    # The traffic light is bg4_red. A scene that spends its four background palettes elsewhere (Southampton:
    # stone, brick, green, water) cannot afford it, so it is left out there instead of blowing the budget.
    if not crossing or "bg4_red" not in place["allowed_palettes"]:
        return
    cx, cy = crossing
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0)):
        x, y = cx + dx, cy + dy
        if 0 <= x < MAP_W and 1 <= y < MAP_H:
            if tiles[y][x] in ("pavement_a", "pavement_b", "kerb_w", "kerb_e", "cobble_a", "cobble_b"):
                tiles[y][x] = "traffic_top"
                if tiles[y + 1][x] in ("pavement_a", "pavement_b", "kerb_w", "kerb_e"):
                    tiles[y + 1][x] = "traffic_body"
                return


def build_collision(tiles: list[list[str]], solid: set) -> list[str]:
    rows = []
    for y in range(MAP_H):
        rows.append("".join("1" if tiles[y][x] in solid else "0" for x in range(MAP_W)))
    return rows


def components(collision: list[str]) -> list[list[tuple[int, int]]]:
    """Every connected walkable region, largest first. A spawn dropped in a pocket the player cannot leave is
    the defect this exists to stop."""
    seen = set()
    out = []
    for y in range(MAP_H):
        for x in range(MAP_W):
            if collision[y][x] != "0" or (x, y) in seen:
                continue
            region = [(x, y)]
            seen.add((x, y))
            queue = deque([(x, y)])
            while queue:
                cx, cy = queue.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < MAP_W and 0 <= ny < MAP_H and (nx, ny) not in seen and collision[ny][nx] == "0":
                        seen.add((nx, ny))
                        region.append((nx, ny))
                        queue.append((nx, ny))
            out.append(region)
    out.sort(key=len, reverse=True)
    return out


def find_start(tiles: list[list[str]], collision: list[str]) -> tuple[int, int]:
    regions = components(collision)
    if not regions:
        raise SystemExit("no walkable tile at all")
    main = set(regions[0])
    best = None
    for y in range(2, MAP_H - 2):
        for x in range(2, MAP_W - 2):
            if (x, y) not in main:
                continue
            near_road = any(0 <= x + dx < MAP_W and 0 <= y + dy < MAP_H
                            and is_road(tiles[y + dy][x + dx])
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)))
            if not near_road:
                continue
            score = abs(x - MAP_W // 2) + abs(y - (MAP_H - 10))
            if best is None or score < best[0]:
                best = (score, x, y)
    if best is None:
        x, y = regions[0][0]
        return x, y
    return best[1], best[2]


def reachable(collision: list[str], start: tuple[int, int]) -> set:
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H and (nx, ny) not in seen and collision[ny][nx] == "0":
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def legend_for(tiles: list[list[str]], by_name: dict) -> dict:
    used = {tile for row in tiles for tile in row}
    return {LEGEND_CHARS[by_name[name]["index"]]: by_name[name].get("name", name) for name in sorted(used)}


def render_map(tiles: list[list[str]], sheet: Image.Image, by_name: dict) -> Image.Image:
    image = Image.new("RGB", (MAP_W * TILE, MAP_H * TILE), (0, 0, 0))
    for y in range(MAP_H):
        for x in range(MAP_W):
            tile = by_name[tiles[y][x]]
            sx = (tile["index"] % 16) * TILE
            sy = (tile["index"] // 16) * TILE
            image.paste(sheet.crop((sx, sy, sx + TILE, sy + TILE)).convert("RGB"), (x * TILE, y * TILE))
    return image


def render_frame(tiles: list[list[str]], sheet: Image.Image, by_name: dict, start: tuple[int, int]) -> Image.Image:
    x0 = max(0, min(MAP_W - FRAME_W, start[0] - FRAME_W // 2))
    y0 = max(0, min(MAP_H - FRAME_H, start[1] - FRAME_H // 2))
    image = Image.new("RGB", (FRAME_W * TILE, FRAME_H * TILE), (0, 0, 0))
    for y in range(FRAME_H):
        for x in range(FRAME_W):
            tile = by_name[tiles[y0 + y][x0 + x]]
            sx = (tile["index"] % 16) * TILE
            sy = (tile["index"] // 16) * TILE
            image.paste(sheet.crop((sx, sy, sx + TILE, sy + TILE)).convert("RGB"), (x * TILE, y * TILE))
    return image


def palette_entries(meta: dict) -> dict:
    return {name: [item["entry"] for item in items] for name, items in meta["palettes"].items()}


def solved_sprites(path: str, placeholder: list) -> list:
    """The sprite half a card solved in this file, or [] when the file carries only the placeholder.

    The generator writes four PLACEHOLDER sprite palettes (a copy of the background groups), and it used to write
    the whole file, so a card that solved them for the cast that walks here lost the decision on the next run.
    Card t_dec4e92c solved the three towns for the party's four walking sheets and hit exactly that. The rule
    below is mechanical rather than a flag: a sprite half IDENTICAL to the placeholder needs no carrying (the
    generator reproduces it), and one that differs is a decision, kept and printed.
    """
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return []
    rows = payload.get("sprites") or []
    return rows if rows and rows != placeholder else []


def judged_rows(path: str) -> list:
    """The audit rows cards wrote in this file, kept verbatim (card t_5802ecdb's rule, on this generator).

    A judged row names the ground a cast is measured on; this generator writes no row and cannot answer for one,
    so it must not delete one. tools/art/make_battle_bg.py had the same defect on the battle strips and card
    t_5802ecdb fixed it there; card t_dec4e92c fixed it here, where the three towns now carry their own rows.
    """
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return []
    return list(payload.get("judged") or [])


def write_scene_palette(root: str, place: dict, meta: dict, ts_meta: dict) -> str:
    entries = palette_entries(ts_meta)
    hexes = {entry["index"]: entry["hex"] for entry in json.load(
        open(os.path.join(root, "data", "nes_palette.json"), encoding="utf-8"))["entries"]}
    background = []
    for i, name in enumerate(place["allowed_palettes"]):
        background.append({
            "name": "bg%d" % i,
            "palette": name,
            "colours": entries[name],
            "hex": [hexes[e] for e in entries[name]],
        })
    placeholder = [
        {"name": "sp0", "colours": [0, 15, 16], "hex": [hexes[0], hexes[15], hexes[16]]},
        {"name": "sp1", "colours": [7, 23, 40], "hex": [hexes[7], hexes[23], hexes[40]]},
        {"name": "sp2", "colours": [9, 10, 42], "hex": [hexes[9], hexes[10], hexes[42]]},
        {"name": "sp3", "colours": [2, 18, 48], "hex": [hexes[2], hexes[18], hexes[48]]},
    ]
    scene = {
        "format": 1,
        "kind": "scene_palette",
        "scene": place["scene"],
        "backdrop": 15,
        "rule": "NES: 1 backdrop shared by both layers, 4 background palettes of 3 entries on 16x16 areas, "
                "4 sprite palettes of 3 entries plus transparency on 8x8 tiles; every entry is a "
                "data/nes_palette.json entry number",
        "background": background,
        "sprites": placeholder,
        "notes": [
            "written by tools/art/make_exterior_maps.py because no NES-PALETTES scene file existed for this "
            "tileset; same format as data/palettes/scene_ship.json",
            "background palettes are the 4 groups the scene map actually spends, in tileset order",
            "sprite palettes are the PLACEHOLDER char lane set, a copy of the background groups, so a character "
            "cannot add a 14th colour to the frame. A card that solves them for the cast that walks here writes "
            "its rows in this file and this generator keeps them: card t_dec4e92c solved southampton, westminster "
            "and winchester for the party's four walking sheets, and the same run keeps every judged row it finds",
        ],
    }
    path = os.path.join(root, "data", "palettes", "scene_%s.json" % place["scene"])
    kept_sprites = solved_sprites(path, placeholder)
    if kept_sprites:
        scene["sprites"] = kept_sprites
    kept_judged = judged_rows(path)
    if kept_judged:
        scene["judged"] = kept_judged
    # newline="\n": a text handle on Windows turns every \n into \r\n, so the same run wrote different bytes on the
    # gate's Linux host and the committed file could never be reproduced there (card t_155bcd6d). Every file this
    # generator owns is written with an explicit LF for that reason.
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(scene, handle, indent=2)
        handle.write("\n")
    if kept_sprites or kept_judged:
        print("%-22s kept %d solved sprite row(s) and %d judged row(s) already in scene_%s.json"
              % (place["id"], len(kept_sprites), len(kept_judged), place["scene"]))
    return path


def enforce_palette_budget(tiles: list[list[str]], place: dict, by_name: dict) -> list[str]:
    """A scene may spend at most 4 background palettes. Measured, not hoped for: a tile from a fifth palette is
    a hard failure here, so the map is never written with an impossible frame."""
    allowed = list(place["allowed_palettes"])
    if len(allowed) > 4:
        raise SystemExit("%s: allowed_palettes names %d palettes, a NES scene has 4" % (place["id"], len(allowed)))
    used = sorted({by_name[t]["palette"] for row in tiles for t in row})
    extra = [name for name in used if name not in allowed]
    if extra:
        offenders = sorted({t for row in tiles for t in row if by_name[t]["palette"] in extra})
        raise SystemExit("%s spends %d background palettes %s; %s is outside the 4 %s. Tiles at fault: %s"
                         % (place["id"], len(used), used, extra, allowed, offenders))
    return used


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    root = args.root or repo_root()
    ts_meta, by_name = load_tileset(root)
    solid = {name for name, tile in by_name.items() if tile.get("solid")}
    sheet = Image.open(os.path.join(root, "game", "sprites_src", "env", "ts_exterior.png")).convert("RGBA")

    report = []
    for place in PLACES:
        draft = load_osm(root, place["osm"])
        grid = grid_of(draft)
        x0, y0 = best_crop(grid, place)
        tiles = build_ground(grid, x0, y0, place)
        add_crosswalk_spot = add_crosswalk(tiles)
        add_kerbs(tiles)
        add_shop_fronts(tiles, place)
        landmark = place_landmark(tiles, grid, x0, y0, place)
        furniture = add_street_furniture(tiles, place)
        add_traffic_light(tiles, add_crosswalk_spot, place)
        collision_rows = build_collision(tiles, solid)
        regions = components(collision_rows)
        start = find_start(tiles, collision_rows)
        seen = reachable(collision_rows, start)
        walkable = sum(row.count("0") for row in collision_rows)
        palette_used = enforce_palette_budget(tiles, place, by_name)
        legend = legend_for(tiles, by_name)

        tiles_rows = ["".join(LEGEND_CHARS[by_name[t]["index"]] for t in row) for row in tiles]
        palette_path = write_scene_palette(root, place, None, ts_meta)
        map_doc = {
            "id": place["id"],
            "name": place["name"],
            "tileset": "ts_exterior",
            "width": MAP_W,
            "height": MAP_H,
            "tile_legend": legend,
            "tiles": tiles_rows,
            "collision": collision_rows,
            "palette_indices": sorted({entry for name in place["allowed_palettes"]
                                       for entry in palette_entries(ts_meta)[name]}),
            "palette_groups": palette_used,
            "spawns": {"start": {"x": start[0], "y": start[1]}},
            "triggers": [],
            "checks": {
                "background_palettes_spent": len(palette_used),
                "background_palette_limit": 4,
                "walkable_tiles": walkable,
                "walkable_regions": len(regions),
                "main_region_tiles": len(regions[0]) if regions else 0,
                "reachable_from_start": len(seen),
                "reachable_pct_of_main_region": round(100.0 * len(seen) / len(regions[0]), 1) if regions else 0.0,
            },
        }
        doc = {
            "format": 1,
            "kind": "maps",
            "tile_size": TILE,
            "tileset": "ts_exterior",
            "scene_palette": os.path.relpath(palette_path, root).replace("\\", "/"),
            "source": {
                "draft": "data/maps/osm/%s.json" % place["osm"],
                "attribution": "(c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0, "
                               "https://www.openstreetmap.org/copyright",
                "crop": {"x": x0, "y": y0, "width": MAP_W, "height": MAP_H},
                "landmark_placed": landmark,
                "notes": place["notes"],
            },
            "maps": [map_doc],
        }
        out = os.path.join(root, "data", "maps", place["id"] + ".json")
        with open(out, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(doc, handle, indent=2)
            handle.write("\n")

        preview = render_map(tiles, sheet, by_name)
        preview.resize((preview.width * SCALE_PREVIEW, preview.height * SCALE_PREVIEW), Image.NEAREST).save(
            os.path.join(root, "output", "%s_preview_2x.png" % place["id"]))
        frame = render_frame(tiles, sheet, by_name, start)
        frame.save(os.path.join(root, "output", "%s_frame.png" % place["id"]))
        frame.resize((frame.width * SCALE_FRAME, frame.height * SCALE_FRAME), Image.NEAREST).save(
            os.path.join(root, "output", "%s_frame_3x.png" % place["id"]))

        palettes_used = palette_used
        report.append({
            "map": place["id"],
            "crop": [x0, y0],
            "tiles_used": len(legend),
            "walkable": walkable,
            "regions": len(regions),
            "main_region": len(regions[0]) if regions else 0,
            "reachable": len(seen),
            "reachable_pct": round(100.0 * len(seen) / len(regions[0]), 1) if regions else 0.0,
            "start": list(start),
            "landmark": landmark,
            "palettes_used": palettes_used,
            "furniture": sorted(furniture),
        })
        print("%-22s crop %2d,%2d  tiles %2d  walkable %3d  regions %2d  reachable %3d/%3d (%.1f%%)  "
              "start %d,%d  landmark %s  palettes %d"
              % (place["id"], x0, y0, len(legend), walkable, len(regions), len(seen),
                 len(regions[0]) if regions else 0,
                 100.0 * len(seen) / len(regions[0]) if regions else 0.0,
                 start[0], start[1], landmark, len(palettes_used)))
    with open(os.path.join(root, "output", "ts_exterior_maps_report.json"), "w", encoding="utf-8",
              newline="\n") as handle:
        json.dump({"format": 1, "kind": "ts_exterior_maps_report", "maps": report}, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
