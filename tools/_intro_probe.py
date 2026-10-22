"""Scratch probe for the INTRO-1 frames: sizes, palette colours, star and text locations."""
import sys
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")


def main():
    for i in range(1, 5):
        p = os.path.join(OUT, "intro_%d.png" % i)
        if not os.path.exists(p):
            print(p, "MISSING")
            continue
        im = Image.open(p).convert("RGB")
        cols = im.getcolors(maxcolors=1000000)
        cols.sort(reverse=True)
        print(p, im.size, "unique", len(cols))
        print("  top10", [(c, rgb) for c, rgb in cols[:10]])
        # Bright pixels (white-ish) count: stars and text are near white.
        px = im.load()
        w, h = im.size
        white = 0
        for y in range(h):
            for x in range(w):
                r, g, b = px[x, y]
                if r > 220 and g > 220 and b > 220:
                    white += 1
        print("  near-white pixels", white)


if __name__ == "__main__":
    main()
