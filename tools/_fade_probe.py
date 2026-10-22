"""Scratch probe for the title fade art and the build's sprite list (card INTRO-1)."""
import json
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "game", "sprites_src", "title")


def colours(path):
    im = Image.open(path).convert("RGBA")
    counts = {}
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            key = "#%02x%02x%02x" % (r, g, b)
            counts[key] = counts.get(key, 0) + 1
    return im.size, sorted(counts.items(), key=lambda kv: -kv[1])


def main():
    for name in ["title_L1_sky", "title_L1_sky_fade1", "title_L1_sky_fade2", "title_L1_sky_fade3",
                 "title_L1_sky_fade4", "title_L2_clouds_fade4", "title_L6_road_fade4", "spr_title_car_fade4"]:
        p = os.path.join(SRC, name + ".png")
        if not os.path.exists(p):
            print(name, "MISSING")
            continue
        size, cols = colours(p)
        print(name, size, "colours:", cols[:8])
    print()
    yyp = os.path.join(ROOT, "game", "PrimordialParadox.yyp")
    with open(yyp, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    names = [r.get("id", {}).get("name") or r.get("name") for r in data.get("resources", [])]
    names = [n for n in names if n]
    for target in ["title_L1_sky_fade4", "spr_title_star", "spr_title_car_fade4", "title_L7_fg_fade4"]:
        hits = [n for n in names if n.endswith(target)]
        print("yyp resource for", target, "->", hits)


if __name__ == "__main__":
    main()
