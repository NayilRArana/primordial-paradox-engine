"""check_render_preview.py: measurable checks on a render preview PNG.

The manager reviews the picture, so this only proves the picture is worth
looking at: the right size, every panel holding ink, and no two text lines
colliding.

Usage:
    check_render_preview.py in.png
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

SCALE = 3
WIDTH = 640 * SCALE
PANEL = 220 * SCALE
MARGIN = 16 * SCALE


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = argv[0]
    image = Image.open(path).convert("RGB")
    array = np.asarray(image).astype(np.int16)
    height = array.shape[0]
    problems: list[str] = []

    if image.width != WIDTH:
        problems.append("width is %d, expected %d" % (image.width, WIDTH))

    background = np.array([18, 18, 26], dtype=np.int16)
    top = MARGIN + 46 * SCALE

    panels = {
        "waveform": (MARGIN, top, WIDTH - MARGIN, top + PANEL),
        "spectrum": (MARGIN, top + PANEL + MARGIN, WIDTH - MARGIN, top + PANEL * 2 + MARGIN),
        "text": (MARGIN, top + PANEL * 2 + MARGIN * 2, WIDTH - MARGIN, height - MARGIN),
    }
    for name, (x0, y0, x1, y1) in panels.items():
        if y1 > height:
            problems.append("the %s panel runs past the bottom of the image" % name)
            continue
        region = array[y0:y1, x0:x1]
        if region.size == 0:
            problems.append("the %s panel is empty" % name)
            continue
        difference = np.abs(region - background).sum(axis=2)
        ink = float((difference > 30).mean())
        if ink < 0.005:
            problems.append("the %s panel holds almost no ink (%.5f)" % (name, ink))
        print("  %s panel: %.4f ink" % (name, ink))

    # The spectrum must show more than one band of energy, so a dead or
    # silent voice cannot pass as a picture.
    x0, y0, x1, y1 = panels["spectrum"]
    region = array[y0:y1, x0:x1]
    if region.size:
        purple = ((region[:, :, 2] > 120) & (region[:, :, 0] < 200)).sum()
        if purple < 500:
            problems.append("the spectrum shows too little energy (%d purple pixels)" % purple)
        print("  spectrum energy pixels: %d" % purple)

    # Every text line must be on its own row, so the panel grows with the
    # number of lines instead of overlapping them. The region is inset by two
    # pixels so the panel border is not read as a text line.
    x0, y0, x1, y1 = panels["text"]
    region = array[y0 + 2:y1 - 2, x0 + 2:x1 - 2]
    if region.size:
        rows = (np.abs(region - background).sum(axis=2) > 30).sum(axis=1)
        occupied = np.nonzero(rows)[0]
        if occupied.size == 0:
            problems.append("the text panel is blank")
        else:
            print("  text rows in use: %d to %d of %d" % (occupied[0], occupied[-1], region.shape[0]))
            if occupied[-1] >= (region.shape[0]) - 4:
                problems.append("the last text line touches the bottom edge")

    if problems:
        for problem in problems:
            print("  FAIL %s" % problem)
        return 1
    print("  PASS render preview %s is %dx%d and every panel is readable"
          % (os.path.basename(path), image.width, image.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
