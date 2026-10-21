#!/usr/bin/env python3
"""show_data.py: print the pieces of the data bundle a change touches.

Why: the map, the enemy list and the font sheet decide what the first screen can show, and reading
them through a script is faster than reading the whole JSON by eye.

Usage:
    python tools/show_data.py map ship_small
    python tools/show_data.py enemies
    python tools/show_data.py font
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel_path):
    with open(os.path.join(ROOT, rel_path), "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def show_map(map_id):
    data = load(os.path.join("data", "maps", "all.json"))
    for row in data["maps"]:
        if row["id"] != map_id:
            continue
        print("map %s  %dx%d  tile %s" % (row["id"], row["width"], row["height"], row.get("tile_size")))
        print("legend %s" % json.dumps(row.get("tile_legend")))
        print("spawns %s" % json.dumps(row.get("spawns")))
        print("tiles:")
        for line in row["tiles"]:
            print("   |%s|" % line)
        print("triggers:")
        for trigger in row["triggers"]:
            print("   %s" % json.dumps(trigger))
        return 0
    print("no map with id %s" % map_id)
    return 1


def show_enemies():
    data = load(os.path.join("data", "enemies", "all.json"))
    for row in data["enemies"]:
        print(json.dumps(row))
    return 0


def show_font():
    path = os.path.join(ROOT, "game", "sprites_src", "title", "spr_pp_font8.json")
    print(json.dumps(load(path), indent=1))
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    what = sys.argv[1]
    if what == "map":
        return show_map(sys.argv[2] if len(sys.argv) > 2 else "ship_small")
    if what == "enemies":
        return show_enemies()
    if what == "font":
        return show_font()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
