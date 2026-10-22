#!/usr/bin/env python3
"""check_palette_recipes.py: does data/palette_recipes.json hold what the PAL-STUDY card promised, and does it agree with the palette it cites?

Why this exists
---------------
The palette study (knowledge/PALETTE-SYNERGY.md, card t_3da3f037) writes 57 recipes and 8 scene
palette sets as numbers. Written prose proves nothing: this tool recomputes every colour from
data/nes_palette.json, so a recipe cannot cite an entry number that decodes to a different hex, a
luma row or a luminance than the one it claims.

The four rules it enforces:

  palette     every entry is a usable NES master palette entry, and its hex, row and luminance match
              data/nes_palette.json exactly
  recipes     at least 40 recipes, each with a numbers object and a confidence word
  scenes      exactly 8 scene sets, each one backdrop plus 4 background palettes of 3 entries plus 4
              sprite palettes of 3 entries, all inside the 25 colour frame ceiling
  style       no em dash, en dash or long dash in the JSON or in the study page (Nayil's rule)

Usage:
    python tools\\check_palette_recipes.py
    python tools\\check_palette_recipes.py --quiet     # exit code only

Exit 0 when every rule passes, 1 with one line per failure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
PALETTE = os.path.join(ROOT, "data", "nes_palette.json")
RECIPES = os.path.join(ROOT, "data", "palette_recipes.json")
STUDY = os.path.join(ROOT, "knowledge", "PALETTE-SYNERGY.md")

MIN_RECIPES = 40
SCENE_COUNT = 8
PALETTES_PER_LAYER = 4
ENTRIES_PER_PALETTE = 3
FRAME_CEILING = 25
CONFIDENCE = {"stated", "derived", "inference"}
LONG_DASHES = ("\u2014", "\u2013", "\u2015", "\u2212", "\u2012")


def linear(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexcode: str) -> float:
    r, g, b = (int(hexcode[i:i + 2], 16) for i in (1, 3, 5))
    return round(0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b), 4)


def load() -> tuple[dict, dict]:
    palette = json.load(open(PALETTE, encoding="utf-8"))
    recipes = json.load(open(RECIPES, encoding="utf-8"))
    return palette, recipes


def check_colour(fails: list[str], where: str, entry: dict, table: dict) -> None:
    index = entry.get("index")
    if index not in table:
        fails.append("%s: entry %r is not in the master palette" % (where, index))
        return
    master = table[index]
    if not master.get("usable"):
        fails.append("%s: entry %d (%s) is not a usable entry" % (where, index, master["code"]))
    if entry.get("hex") != master["hex"]:
        fails.append("%s: entry %d hex %s, the palette says %s"
                     % (where, index, entry.get("hex"), master["hex"]))
    if entry.get("code") != master["code"]:
        fails.append("%s: entry %d code %s, the palette says %s"
                     % (where, index, entry.get("code"), master["code"]))
    if entry.get("row") != index // 16:
        fails.append("%s: entry %d row %r, expected %d" % (where, index, entry.get("row"), index // 16))
    if abs(float(entry.get("lum", -1)) - luminance(master["hex"])) > 0.0002:
        fails.append("%s: entry %d lum %r, recomputed %r"
                     % (where, index, entry.get("lum"), luminance(master["hex"])))


def check(palette: dict, recipes: dict) -> list[str]:
    fails: list[str] = []
    table = {e["index"]: e for e in palette["entries"]}

    if recipes.get("kind") != "palette_recipes":
        fails.append("recipes: kind is %r" % recipes.get("kind"))

    rows = recipes.get("recipes") or []
    if len(rows) < MIN_RECIPES:
        fails.append("recipes: %d, the card asks for at least %d" % (len(rows), MIN_RECIPES))
    seen = set()
    for r in rows:
        rid = r.get("id")
        where = "recipe %s" % rid
        if rid in seen:
            fails.append("%s: duplicate id" % where)
        seen.add(rid)
        if not isinstance(r.get("numbers"), dict) or not r["numbers"]:
            fails.append("%s: no numbers object" % where)
        if r.get("confidence") not in CONFIDENCE:
            fails.append("%s: confidence %r is not stated, derived or inference"
                         % (where, r.get("confidence")))
        if not r.get("source"):
            fails.append("%s: no source tag" % where)
        for entry in r.get("entries") or []:
            check_colour(fails, where, entry, table)

    heroes = recipes.get("hero_palettes") or []
    if len(heroes) != 4:
        fails.append("hero_palettes: %d, expected 4" % len(heroes))
    for h in heroes:
        where = "hero %s" % h.get("hero")
        if len(h.get("entries") or []) != ENTRIES_PER_PALETTE:
            fails.append("%s: %d entries, expected %d"
                         % (where, len(h.get("entries") or []), ENTRIES_PER_PALETTE))
        for entry in h.get("entries") or []:
            check_colour(fails, where, entry, table)

    scenes = recipes.get("scene_sets") or []
    if len(scenes) != SCENE_COUNT:
        fails.append("scene_sets: %d, the card asks for %d" % (len(scenes), SCENE_COUNT))
    for s in scenes:
        name = s.get("scene")
        where = "scene %s" % name
        check_colour(fails, where + " backdrop", s.get("backdrop") or {}, table)
        bg = s.get("background") or []
        sp = s.get("sprites") or []
        if len(bg) != PALETTES_PER_LAYER:
            fails.append("%s: %d background palettes, expected %d" % (where, len(bg), PALETTES_PER_LAYER))
        if len(sp) != PALETTES_PER_LAYER:
            fails.append("%s: %d sprite palettes, expected %d" % (where, len(sp), PALETTES_PER_LAYER))
        distinct = {(s.get("backdrop") or {}).get("index")}
        for group, label in ((bg, "bg"), (sp, "sp")):
            for i, p in enumerate(group):
                entries = p.get("entries") or []
                if len(entries) != ENTRIES_PER_PALETTE:
                    fails.append("%s %s%d: %d entries, expected %d"
                                 % (where, label, i, len(entries), ENTRIES_PER_PALETTE))
                for entry in entries:
                    check_colour(fails, "%s %s%d" % (where, label, i), entry, table)
                    distinct.add(entry.get("index"))
        if len(distinct) > FRAME_CEILING:
            fails.append("%s: %d distinct colours, the frame ceiling is %d"
                         % (where, len(distinct), FRAME_CEILING))
        if s.get("distinct_colours") != len(distinct):
            fails.append("%s: distinct_colours says %r, recomputed %d"
                         % (where, s.get("distinct_colours"), len(distinct)))
        plate = (s.get("ground_plate") or {}).get("index")
        in_walkable = any(plate in [e.get("index") for e in p.get("entries") or []]
                          for p in bg if p.get("name") in (s.get("walkable_background") or []))
        if not in_walkable:
            fails.append("%s: the ground plate %r is not an entry of the walkable palette" % (where, plate))

    for path in (RECIPES, STUDY):
        if not os.path.exists(path):
            fails.append("missing file %s" % path)
            continue
        text = open(path, encoding="utf-8").read()
        for dash in LONG_DASHES:
            if dash in text:
                fails.append("%s: contains a long dash U+%04X" % (os.path.basename(path), ord(dash)))

    return fails


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        palette, recipes = load()
    except Exception as exc:  # noqa: BLE001  (the report has to name the parse failure)
        print("cannot read the data files: %s" % exc)
        return 1

    fails = check(palette, recipes)
    if args.quiet:
        print("palette_recipes: %d failure(s)" % len(fails))
        return 1 if fails else 0

    if fails:
        print("FAIL %d" % len(fails))
        for line in fails:
            print("  " + line)
        return 1

    n = len(recipes["recipes"])
    print("PASS palette_recipes: %d recipes, %d hero palettes, %d scene sets, %d failure(s)"
          % (n, len(recipes["hero_palettes"]), len(recipes["scene_sets"]), 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
