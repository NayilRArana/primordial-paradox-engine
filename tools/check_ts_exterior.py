#!/usr/bin/env python3
"""check_ts_exterior.py: prove the exterior tileset and its three sample maps are what TILES-EXTERIOR asks for.

Every rule below is measured against the files on disk, not restated from the generator's intent:

1. ts_exterior.png is exactly columns*16 by rows*16 as ts_exterior.json declares, and the json lists that many
   tiles, numbered 0..n-1, with unique names.
2. Every opaque pixel is the output of an entry in data/nes_palette.json, so no colour can drift into "nearly
   NES" without this failing. Entries flagged usable false are refused.
3. No 16x16 tile carries more than 3 colours besides the one shared backdrop: the NES attribute area limit.
4. No 8x8 quarter of a tile carries more than 3 colours besides the backdrop, so the same art cuts down to
   pattern tiles.
5. The whole sheet shows at most 25 distinct colours, the ceiling of a NES frame.
6. The json declares only 3 entry palettes, each entry's hex equals the hex of the entry number it names, read
   back from data/nes_palette.json, and the whole set plus the backdrop stays under the 25 colours one frame can
   show. A tileset serves several scenes, so declaring more than 4 groups is legal; the per-scene 4 group budget
   is rule 10.
7. Every feature the card names is declared in the json and resolves to tiles that exist; the water animation
   is exactly the 2 frames the card asks for and both frames exist.
8. Each of the three sample maps is 32x30, uses only tiles this tileset has, and its collision layer is 0 or 1
   and equals the solid flag of the tile above it in both directions.
9. Every spawn sits on a walkable tile inside the map's largest walkable region and at least 99% of that region
   is reachable from it, so no sample ships with the player boxed into a pocket.
10. Each map spends at most 4 background palettes.
11. The 2x previews are exactly twice the rendered map (1024x960) and the frames are 256x240, with the 3x frame
    exactly 3x (768x720).
12. The project's own validators agree: tools/nes_check.py passes over the sheet as a background with the black
    backdrop, and tools/nes_composite_check.py passes over each 256x240 frame. This tool does not restate the
    NES rules, it runs them.
13. Every tile a player can walk on draws only entries under 0.25 luminance, because the party's walking bodies
    are near white and RULE 0 point 2 refuses a near white body on a light ground. The exemption list is empty:
    the park was its last member and the grass was darkened on card t_b01c88ff (knowledge/PALETTE-RULINGS-2026-10-25.md
    section 22). The list stays in the tool so a future exemption is a decision that shows up in a diff with a
    card name on it, not a quiet pass.

Exit 0 when every check passes, 1 when any fails, with each failure on its own line.

Usage:
    python tools/check_ts_exterior.py
    python tools/check_ts_exterior.py --root <repo> --json report.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import deque

from PIL import Image

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.join(TOOLS_DIR, "art") not in sys.path:
    sys.path.insert(0, os.path.join(TOOLS_DIR, "art"))
import contrast_check  # noqa: E402  (the WCAG luminance table: reused, not restated)

TILE = 16
BACKDROP_HEX = "#000000"
MAP_W, MAP_H = 32, 30
# RULE 0 point 2's light line, and the same numbers tools/palette_synergy.py uses (LIGHT_GROUND 0.25, a near
# white body 0.60). A ground at or above this luminance turns the party's $30, $31 and $28 bodies into the white
# blob RULE 0 refuses, so no tile a player can walk on may draw an entry at or above it.
LIGHT_GROUND = 0.25
# Walkable tiles still light, each named with the card that ends it. EMPTY since card t_b01c88ff: the park's
# grass drew H $2A #58d854 at 0.518, the white blob hazard card t_454c1876 did not touch. The three walkable
# grass tiles were darkened instead, not this check weakened; the list stays so an exemption shows in a diff.
WALKABLE_LIGHT_EXEMPT: dict[str, str] = {}
SAMPLE_MAPS = ("westminster_sample", "winchester_sample", "southampton_sample")
CARD_FEATURES = [
    "road with centre line", "kerb", "pavement", "cobbles", "brick building walls (3 variants)",
    "shop front with awning", "doors", "windows with light", "red phone box", "post box", "hedge", "tree",
    "lamp post", "bollard", "quay stone", "water (2 frames)", "railing", "bench", "traffic light",
    "crosswalk", "Big Ben tower pieces (4 tiles tall)", "cathedral wall pieces",
]
LEGEND_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ@#"


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.lines: list[str] = []

    def check(self, ok: bool, ok_text: str, fail_text: str) -> bool:
        if ok:
            self.lines.append("PASS " + ok_text)
        else:
            self.fails.append(fail_text)
            self.lines.append("FAIL " + fail_text)
        return ok


def load_palette(root: str) -> tuple[dict, set]:
    path = os.path.join(root, "data", "nes_palette.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    by_hex, usable = {}, set()
    for entry in data["entries"]:
        by_hex[entry["hex"].lower()] = entry
        if entry.get("usable", True):
            usable.add(entry["hex"].lower())
    return by_hex, usable


def hexes(image: Image.Image) -> dict:
    image = image.convert("RGBA")
    counts = {}
    for pixel in image.getdata():
        if pixel[3] == 0:
            continue
        key = "#%02x%02x%02x" % pixel[:3]
        counts[key] = counts.get(key, 0) + 1
    return counts


def check_sheet(root: str, rep: Report) -> dict:
    sheet_path = os.path.join(root, "game", "sprites_src", "env", "ts_exterior.png")
    json_path = os.path.join(root, "game", "sprites_src", "env", "ts_exterior.json")
    meta = json.load(open(json_path, encoding="utf-8"))
    sheet = Image.open(sheet_path).convert("RGBA")
    by_hex, usable = load_palette(root)

    rep.check(sheet.size == (meta["columns"] * TILE, meta["rows"] * TILE),
              "sheet is %dx%d, the %d columns by %d rows the json declares"
              % (sheet.width, sheet.height, meta["columns"], meta["rows"]),
              "sheet is %dx%d but the json declares %dx%d"
              % (sheet.width, sheet.height, meta["columns"] * TILE, meta["rows"] * TILE))

    names = [tile["name"] for tile in meta["tiles"]]
    rep.check(len(names) == meta["frames"] == len(set(names)),
              "%d tiles, unique names, matching frames" % len(names),
              "tile count/names disagree: %d tiles, %d frames, %d unique" % (len(names), meta["frames"], len(set(names))))
    rep.check([tile["index"] for tile in meta["tiles"]] == list(range(len(names))),
              "tiles numbered 0..%d in order" % (len(names) - 1),
              "tiles are not numbered 0..n-1 in order")

    colours = hexes(sheet)
    outside = sorted(c for c in colours if c not in by_hex)
    rep.check(not outside, "%d colours, every one a data/nes_palette.json entry" % len(colours),
              "%d colour(s) are not PPU outputs: %s" % (len(outside), outside))
    forbidden = sorted(c for c in colours if c in by_hex and c not in usable)
    rep.check(not forbidden, "no colour comes from an entry flagged usable false",
              "colour(s) from unusable entries: %s" % forbidden)
    rep.check(len(colours) <= 25, "%d colours on the sheet (25 allowed)" % len(colours),
              "%d colours on the sheet, over the 25 a frame may show" % len(colours))

    tile_colours, quarter_colours = {}, {}
    for tile in meta["tiles"]:
        idx = tile["index"]
        cx, cy = (idx % meta["columns"]) * TILE, (idx // meta["columns"]) * TILE
        box = sheet.crop((cx, cy, cx + TILE, cy + TILE))
        seen = {("#%02x%02x%02x" % px[:3]) for px in box.convert("RGBA").getdata() if px[3] and px[:3] != (0, 0, 0)}
        tile_colours[tile["name"]] = len(seen)
        if len(seen) > 3:
            rep.fails.append("tile %s (%d,%d) carries %d colours besides the backdrop" % (tile["name"], idx % meta["columns"], idx // meta["columns"], len(seen)))
        for qy in range(2):
            for qx in range(2):
                part = box.crop((qx * 8, qy * 8, qx * 8 + 8, qy * 8 + 8)).convert("RGBA")
                qseen = {("#%02x%02x%02x" % px[:3]) for px in part.getdata() if px[3] and px[:3] != (0, 0, 0)}
                quarter_colours[(tile["name"], qx, qy)] = len(qseen)
                if len(qseen) > 3:
                    rep.fails.append("tile %s quarter %d,%d carries %d colours besides the backdrop" % (tile["name"], qx, qy, len(qseen)))
    rep.check(not [n for n, c in tile_colours.items() if c > 3],
              "worst 16x16 tile carries %d colours besides the backdrop (3 allowed)" % max(tile_colours.values()),
              "16x16 tiles over 3 colours: %s" % sorted(n for n, c in tile_colours.items() if c > 3))
    rep.check(not [k for k, c in quarter_colours.items() if c > 3],
              "worst 8x8 quarter carries %d colours besides the backdrop (3 allowed)" % max(quarter_colours.values()),
              "8x8 quarters over 3 colours: %s" % sorted(k for k, c in quarter_colours.items() if c > 3))

    palettes = meta["palettes"]
    union = {int(meta["backdrop"]["entry"])}
    bad = []
    for name, items in palettes.items():
        if len(items) != 3:
            bad.append("%s has %d entries" % (name, len(items)))
        for item in items:
            union.add(int(item["entry"]))
            entry = by_hex.get(item["hex"].lower())
            if entry is None or entry["index"] != item["entry"]:
                bad.append("%s entry %s is not %s" % (name, item["entry"], item["hex"]))
    rep.check(not bad, "every declared palette is 3 entries and names the entry whose hex it shows",
              "palette declarations disagree with data/nes_palette.json: %s" % bad)
    # A tileset is a library shared by several scenes, so it may declare more than the 4 groups one frame can
    # hold; the per-scene budget is rule 10. What no frame can survive is more than 25 colours in total, and
    # every entry a scene picks must fit inside 4 groups of 3 plus the backdrop, which rule 10 measures.
    rep.check(len(union) <= 25,
              "the declared palettes plus the backdrop name %d entries, under the 25 a frame may show" % len(union),
              "the declared palettes plus the backdrop name %d entries, over the 25 a frame may show" % len(union))

    missing = [f for f in CARD_FEATURES if f not in meta.get("features", {})]
    unknown = sorted({t for tiles in meta.get("features", {}).values() for t in tiles} - set(names))
    rep.check(not missing and not unknown, "all %d card features declared, every named tile exists" % len(CARD_FEATURES),
              "features missing %s or naming unknown tiles %s" % (missing, unknown))

    anim = meta.get("animations", {}).get("water")
    rep.check(anim == ["water_a", "water_b"], "water animation is exactly 2 frames: %s" % anim,
              "water animation is %s, the card asks for 2 frames" % (anim,))
    rep.check(all(isinstance(t.get("solid"), bool) for t in meta["tiles"]),
              "every tile carries a boolean solid flag",
              "some tiles have no boolean solid flag")
    return meta


def check_walkable_band(root: str, meta: dict, rep: Report) -> None:
    """Rule 13: a tile a player can walk on draws only entries under the light line.

    ART-BIBLE RULE 0 point 2 refuses a near-white body (luminance 0.60 or more) on a light ground (0.25 or
    more), and the party's four walking sheets carry $30 #fcfcfc, $31 #a4e4fc and $28 #f8b800 as their bodies.
    So the ground under their feet has to sit below 0.25 luminance wherever they can stand, and the only way
    to know that is to read the tiles they can stand on. Card t_454c1876 moved the street off it: pavement,
    cobbles, kerbs, roads, the crossing and the quay now draw bg0_stone's M $00 (0.202) and the shared
    backdrop $0F (0.000), and its L $10 (0.503) and W $30 (0.973) are architecture only.
    """
    by_hex, _usable = load_palette(root)
    sheet = Image.open(os.path.join(root, "game", "sprites_src", "env", "ts_exterior.png")).convert("RGBA")
    walkable = [tile for tile in meta["tiles"] if not tile.get("solid")]
    light = []
    for tile in walkable:
        idx = tile["index"]
        cx, cy = (idx % meta["columns"]) * TILE, (idx // meta["columns"]) * TILE
        box = sheet.crop((cx, cy, cx + TILE, cy + TILE)).convert("RGBA")
        worst = None
        for px in box.getdata():
            if px[3] == 0:
                continue
            rgb = tuple(px[:3])
            entry = by_hex.get("#%02x%02x%02x" % rgb)
            if entry is None:
                continue
            value = contrast_check.luminance(rgb)
            if value >= LIGHT_GROUND and (worst is None or value > worst[1]):
                worst = (int(entry["index"]), value)
        if worst is not None and tile["name"] not in WALKABLE_LIGHT_EXEMPT:
            light.append("%s draws $%02X at luminance %.3f" % (tile["name"], worst[0], worst[1]))
    exempt = sorted(name for name in WALKABLE_LIGHT_EXEMPT if name in {tile["name"] for tile in walkable})
    rep.check(not light,
              "all %d walkable tile(s) draw only entries under %.2f luminance, %d exemption(s) named"
              % (len(walkable), LIGHT_GROUND, len(exempt)),
              "walkable tile(s) drawing a light entry (under %.2f is the rule): %s"
              % (LIGHT_GROUND, "; ".join(light)))
    for name in exempt:
        rep.lines.append("EXEMPT %s: walkable and light (%.2f is the line), carded as %s"
                         % (name, LIGHT_GROUND, WALKABLE_LIGHT_EXEMPT[name]))


def load_map(root: str, mid: str) -> dict:
    with open(os.path.join(root, "data", "maps", mid + ".json"), encoding="utf-8") as handle:
        return json.load(handle)


def components(collision: list[str]) -> list[list[tuple[int, int]]]:
    seen, out = set(), []
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


def check_map(root: str, mid: str, meta: dict, rep: Report) -> dict:
    doc = load_map(root, mid)
    m = doc["maps"][0]
    by_name = {tile["name"]: tile for tile in meta["tiles"]}
    char_to_name = {LEGEND_CHARS[tile["index"]]: tile["name"] for tile in meta["tiles"]}

    rep.check(m["width"] == MAP_W and m["height"] == MAP_H, "%s is %dx%d" % (mid, m["width"], m["height"]),
              "%s is %dx%d, the card asks for %dx%d" % (mid, m["width"], m["height"], MAP_W, MAP_H))
    rep.check(len(m["tiles"]) == MAP_H and all(len(row) == MAP_W for row in m["tiles"]),
              "%s has %d tile rows of %d" % (mid, len(m["tiles"]), MAP_W),
              "%s tile rows are the wrong shape" % mid)
    unknown = sorted({c for row in m["tiles"] for c in row} - set(char_to_name))
    rep.check(not unknown, "%s uses only tiles this tileset has (%d distinct)" % (mid, len({c for row in m["tiles"] for c in row})),
              "%s uses legend characters the tileset does not have: %s" % (mid, unknown))
    rep.check(len(m["collision"]) == MAP_H and all(len(row) == MAP_W for row in m["collision"]),
              "%s collision layer is %dx%d" % (mid, MAP_W, MAP_H),
              "%s collision layer is the wrong shape" % mid)
    bad_chars = sorted({c for row in m["collision"] for c in row} - {"0", "1"})
    rep.check(not bad_chars, "%s collision values are only 0 and 1" % mid,
              "%s collision has values other than 0 and 1: %s" % (mid, bad_chars))

    mismatched = []
    for y in range(MAP_H):
        for x in range(MAP_W):
            name = char_to_name[m["tiles"][y][x]]
            if (m["collision"][y][x] == "1") != bool(by_name[name]["solid"]):
                mismatched.append((x, y, name, m["collision"][y][x]))
    rep.check(not mismatched, "%s collision equals the solid flag of every tile (both directions)" % mid,
              "%s collision disagrees with the solid flag at %s" % (mid, mismatched[:8]))

    palettes = sorted({by_name[char_to_name[c]]["palette"] for row in m["tiles"] for c in row})
    rep.check(len(palettes) <= 4, "%s spends %d background palettes: %s" % (mid, len(palettes), palettes),
              "%s spends %d background palettes, a scene has 4" % (mid, len(palettes)))

    start = (m["spawns"]["start"]["x"], m["spawns"]["start"]["y"])
    rep.check(m["collision"][start[1]][start[0]] == "0", "%s spawn %s is walkable" % (mid, start),
              "%s spawn %s is inside a solid tile" % (mid, start))
    regions = components(m["collision"])
    main = set(regions[0]) if regions else set()
    rep.check(start in main, "%s spawn sits in the largest walkable region (%d tiles)" % (mid, len(main)),
              "%s spawn is outside the largest walkable region (%d tiles)" % (mid, len(main)))
    seen = {start}
    queue = deque([start])
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H and (nx, ny) not in seen and m["collision"][ny][nx] == "0":
                seen.add((nx, ny))
                queue.append((nx, ny))
    pct = 100.0 * len(seen) / len(main) if main else 0.0
    rep.check(pct >= 99.0, "%s reaches %d of %d main-region tiles (%.1f%%)" % (mid, len(seen), len(main), pct),
              "%s reaches only %d of %d main-region tiles (%.1f%%)" % (mid, len(seen), len(main), pct))
    return {"map": mid, "palettes": palettes, "regions": len(regions), "main_region": len(main),
            "reachable": len(seen), "spawn": list(start)}


def check_previews(root: str, rep: Report) -> None:
    for mid in SAMPLE_MAPS:
        path = os.path.join(root, "output", "%s_preview_2x.png" % mid)
        if not os.path.exists(path):
            rep.check(False, "", "%s_preview_2x.png is missing" % mid)
            continue
        with Image.open(path) as image:
            want = (MAP_W * TILE * 2, MAP_H * TILE * 2)
            rep.check(image.size == want, "%s_preview_2x.png is %dx%d, exactly 2x the map" % (mid, image.width, image.height),
                      "%s_preview_2x.png is %dx%d, expected %dx%d" % (mid, image.width, image.height, want[0], want[1]))
        frame = os.path.join(root, "output", "%s_frame.png" % mid)
        with Image.open(frame) as image:
            rep.check(image.size == (256, 240), "%s_frame.png is 256x240" % mid,
                      "%s_frame.png is %dx%d, a NES frame is 256x240" % (mid, image.width, image.height))
        frame3 = os.path.join(root, "output", "%s_frame_3x.png" % mid)
        with Image.open(frame3) as image:
            rep.check(image.size == (768, 720), "%s_frame_3x.png is 768x720" % mid,
                      "%s_frame_3x.png is %dx%d, expected 768x720" % (mid, image.width, image.height))
    sheet_preview = os.path.join(root, "output", "ts_exterior_preview_3x.png")
    with Image.open(sheet_preview) as image:
        rep.check(image.size == (256 * 3, 64 * 3), "ts_exterior_preview_3x.png is 768x192",
                  "ts_exterior_preview_3x.png is %dx%d" % (image.width, image.height))


def run_validators(root: str, rep: Report) -> None:
    python = sys.executable
    sheet = os.path.join(root, "game", "sprites_src", "env", "ts_exterior.png")
    out = subprocess.run([python, os.path.join(root, "tools", "nes_check.py"), sheet, "--type", "background",
                          "--backdrop", BACKDROP_HEX, "--json", os.path.join(root, "output", "_ts_ext_nes.json")],
                         capture_output=True, text=True, cwd=root, stdin=subprocess.DEVNULL)
    summary = [line for line in out.stdout.splitlines() if "colours" in line or "PASS" in line or "FAIL" in line]
    rep.check(out.returncode == 0, "nes_check.py --type background passes on the sheet (%s)" % (summary[0].strip() if summary else "no output"),
              "nes_check.py --type background fails on the sheet: %s" % out.stdout.strip()[:600])
    for mid in SAMPLE_MAPS:
        frame = os.path.join(root, "output", "%s_frame.png" % mid)
        out = subprocess.run([python, os.path.join(root, "tools", "nes_composite_check.py"), frame,
                              "--overlay", os.path.join(root, "output", "_%s_overlay.png" % mid),
                              "--json", os.path.join(root, "output", "_%s_composite.json" % mid)],
                             capture_output=True, text=True, cwd=root, stdin=subprocess.DEVNULL)
        bg = [line.strip() for line in out.stdout.splitlines() if line.strip().startswith("background:")]
        rep.check(out.returncode == 0, "nes_composite_check.py passes on %s_frame.png (%s)" % (mid, " ".join(bg)),
                  "nes_composite_check.py fails on %s_frame.png: %s" % (mid, out.stdout.strip()[:800]))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    root = args.root or repo_root()
    rep = Report()
    meta = check_sheet(root, rep)
    check_walkable_band(root, meta, rep)
    maps = [check_map(root, mid, meta, rep) for mid in SAMPLE_MAPS]
    check_previews(root, rep)
    run_validators(root, rep)

    for line in rep.lines:
        print(line)
    for fail in rep.fails:
        print("FAIL " + fail)
    print("%d checks passed, %d failed" % (len(rep.lines) - len(rep.fails), len(rep.fails)))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"format": 1, "kind": "check_ts_exterior", "maps": maps,
                       "passed": len(rep.lines) - len(rep.fails), "failed": len(rep.fails),
                       "failures": rep.fails}, handle, indent=2)
            handle.write("\n")
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
