"""Measure the logo band: grey pixel counts in the band where the title logo sits, for the INTRO-1 capture."""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")

# The window screenshot puts the 256x240 viewport at (8, 31) scaled 3x (see capture_title.py and the NES check).
BAND = (68, 121, 716, 331)


def grey_count(path):
    im = Image.open(path).convert("RGB")
    px = im.load()
    x0, y0, x1, y1 = BAND
    total = 0
    for y in range(y0, min(y1, im.size[1])):
        for x in range(x0, min(x1, im.size[0])):
            r, g, b = px[x, y]
            if r == g == b and 90 <= r <= 250:
                total += 1
    return total


for name in ("intro_1.png", "intro_2.png", "intro_3.png", "intro_4.png"):
    p = os.path.join(OUT, name)
    if os.path.exists(p):
        print(name, "grey pixels in the logo band:", grey_count(p))
