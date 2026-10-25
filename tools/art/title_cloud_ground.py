#!/usr/bin/env python3
"""title_cloud_ground.py: the ground crop the title cloud is judged on, built rather than pasted.

Why this exists
---------------
Card t_19b41ab7 (2026-10-25). Two things read output/cloud_sky_ground.png: tests/test_palette_synergy.py
measures game/sprites_src/title/spr_title_cloud.png on it, and tools/art/make_title_rows_v2.py draws the
cloud's contact row on it. Nothing wrote it. It was a one-off crop sitting in one working tree, matched by
`output/*` in .gitignore and in no commit, so a clean checkout of 5f290c5 reported

    SystemExit: palette_synergy: background output/cloud_sky_ground.png does not exist

while this machine reported 1529 passed. A fixture a test reads has to be something a tool can rebuild, so
this is that tool. It is not a new ground and it sets no art ruling: the crop it writes is byte for byte the
file that was already being measured (176 bytes, sha256 80a7f373...), which is how the reading survives a
clean checkout without a hand-copied picture entering git.

What it is, exactly
-------------------
Rows CLOUD_DY to CLOUD_DY+15, columns 0 to 47, of frame 0 of game/sprites_src/title/title_L1_sky.png.

The cloud sprite is 24x16 and is tiled along x, so the ground is two sprite widths of the band it hangs in,
taken from the layer's own left edge. Frame 0 is the sky as the strip starts; the parallax clouds that move
are title_L2_clouds, drawn ON this band, so they are not part of the ground.

CLOUD_DY is read out of tools/art/compose_title_preview.py rather than copied here. That constant is the y the
composer draws the sprite at, so a composer that moves the cloud has to move this crop with it, and this tool
refuses to guess a number instead of failing.

Usage:
    python tools\\art\\title_cloud_ground.py                write output\\cloud_sky_ground.png
    python tools\\art\\title_cloud_ground.py --check         exit 1 when the file on disk is not what this builds
    python tools\\art\\title_cloud_ground.py --out PATH      write somewhere else
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKY_LAYER = os.path.join("game", "sprites_src", "title", "title_L1_sky.png")
COMPOSER = os.path.join("tools", "art", "compose_title_preview.py")
DEFAULT_OUT = os.path.join("output", "cloud_sky_ground.png")

# Two 24 px sprite widths of the band, and the sprite's own height. Both are facts about the sprite, not about
# the crop: a 24x16 sheet tiled along x is read against the band it covers.
WIDTH, HEIGHT = 48, 16

# The file this tool reproduced on 2026-10-25, the first time it ran. Kept as a fact so `--check` can say
# whether a regeneration changed the ground the two readers measure.
KNOWN_SHA256 = "80a7f373397fe133dc9f8043c59f43ef5ac498b655996b6ad3da6a52df0f2b15"


def cloud_dy(root: str = ROOT) -> int:
    """The sprite's own y in the composed preview, read out of the composer's source.

    Read with ast rather than imported: the composer builds PIL images at import time in some paths, and this
    tool only needs one integer. A composer that stops naming CLOUD_DY is an error here, not a silent 80.
    """
    path = os.path.join(root, COMPOSER)
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    for node in tree.body:
        if not isinstance(node, ast.Assign) or node.value is None:
            continue
        value = node.value
        for target in node.targets:
            if isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple):
                names = [element.id for element in target.elts if isinstance(element, ast.Name)]
                if "CLOUD_DY" in names:
                    index = names.index("CLOUD_DY")
                    if index < len(value.elts) and isinstance(value.elts[index], ast.Constant):
                        return int(value.elts[index].value)  # type: ignore[arg-type]
            elif isinstance(target, ast.Name) and target.id == "CLOUD_DY":
                if isinstance(value, ast.Constant):
                    return int(value.value)  # type: ignore[arg-type]
    raise SystemExit("title_cloud_ground: %s does not name CLOUD_DY, so the band this crop takes cannot be read"
                     % COMPOSER.replace(os.sep, "/"))


def build(root: str = ROOT) -> bytes:
    """The PNG bytes of the ground: rows CLOUD_DY to CLOUD_DY+15, columns 0 to 47, frame 0 of the sky strip."""
    sky_path = os.path.join(root, SKY_LAYER)
    if not os.path.isfile(sky_path):
        raise SystemExit("title_cloud_ground: %s is missing; it is the layer the ground is cut from"
                         % SKY_LAYER.replace(os.sep, "/"))
    y = cloud_dy(root)
    with Image.open(sky_path) as image:
        frame = image.convert("RGBA")
        if frame.height < y + HEIGHT or frame.width < WIDTH:
            raise SystemExit("title_cloud_ground: %s is %dx%d, too small for rows %d to %d and columns 0 to %d"
                             % (SKY_LAYER.replace(os.sep, "/"), frame.width, frame.height, y, y + HEIGHT - 1,
                                WIDTH - 1))
        ground = frame.crop((0, y, WIDTH, y + HEIGHT))
    buffer = io.BytesIO()
    ground.save(buffer, format="PNG")
    return buffer.getvalue()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the 48x16 title sky band the cloud sprite is judged on.")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--out", default=None)
    parser.add_argument("--check", action="store_true",
                        help="compare with the file on disk and exit 1 when it differs")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    out_path = os.path.join(root, args.out or DEFAULT_OUT)
    payload = build(root)
    digest = hashlib.sha256(payload).hexdigest()
    y = cloud_dy(root)
    print("ground: %s frame 0, rows %d to %d, columns 0 to %d, %dx%d, sha256 %s"
          % (SKY_LAYER.replace(os.sep, "/"), y, y + HEIGHT - 1, WIDTH - 1, WIDTH, HEIGHT, digest[:12]))

    if args.check:
        if not os.path.isfile(out_path):
            print("FAIL %s is not on disk: python tools\\art\\title_cloud_ground.py"
                  % os.path.relpath(out_path, root).replace(os.sep, "/"))
            return 1
        with open(out_path, "rb") as handle:
            on_disk = handle.read()
        if on_disk != payload:
            print("FAIL %s is not what this tool builds (%d bytes on disk, %d built); the ground moved. "
                  "Rewrite it and say why in the card"
                  % (os.path.relpath(out_path, root).replace(os.sep, "/"), len(on_disk), len(payload)))
            return 1
        print("PASS %s is the crop this tool builds" % os.path.relpath(out_path, root).replace(os.sep, "/"))
        return 0

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as handle:
        handle.write(payload)
    print("wrote %s (%d bytes)" % (os.path.relpath(out_path, root).replace(os.sep, "/"), len(payload)))
    if digest != KNOWN_SHA256:
        print("note: this is not the sha256 first recorded (%s); the ground has changed since 2026-10-25"
              % KNOWN_SHA256[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
