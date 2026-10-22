"""Independent review measurements for CHAR-PIPE (card t_d01614a1).

Every number here is measured from PNG pixels with this file's own code. Nothing is read
from output\\char_pipe\\*/char_pipe_report.json, because a gate that trusts the artifact it
polices proves nothing (see the 2026-10-20 thumbnail-gate lesson).
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image

REPO = r"<repo>"
PALETTE = os.path.join(REPO, "data", "nes_palette.json")
TILE = 8
import tempfile  # noqa: E402

WORK = os.path.join(tempfile.gettempdir(), "char_pipe_review")  # scratch, never inside the repo
os.makedirs(WORK, exist_ok=True)


def allowed_colours():
    with open(PALETTE, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    colours = data.get("colours") or data.get("palette") or []
    return {tuple(int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for c in colours}, len(colours)


def load(path):
    with Image.open(path) as img:
        return img.convert("RGBA")


def tile_max(image):
    px = image.load()
    worst = 0
    offenders = []
    for ty in range(image.height // TILE):
        for tx in range(image.width // TILE):
            seen = set()
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    r, g, b, a = px[x, y]
                    if a:
                        seen.add((r, g, b))
            worst = max(worst, len(seen))
            if len(seen) > 3:
                offenders.append(((tx, ty), sorted(seen)))
    return worst, offenders


def report_sheet(path, frame_w, frame_h, allowed):
    image = load(path)
    worst, over = tile_max(image)
    px = image.load()
    alphas = set()
    colours = set()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = px[x, y]
            alphas.add(a)
            if a:
                colours.add((r, g, b))
    off_palette = sorted(colours - allowed)
    # frames, left to right then row by row
    cols = image.width // frame_w
    rows = image.height // frame_h
    frames = []
    for row in range(rows):
        for col in range(cols):
            box = (col * frame_w, row * frame_h, col * frame_w + frame_w, row * frame_h + frame_h)
            crop = image.crop(box)
            opaque = sum(1 for _, _, _, a in crop.getdata() if a)
            frames.append({"box": box, "opaque": opaque, "bytes": crop.tobytes()})
    return {
        "path": os.path.basename(path), "size": image.size, "grid": [cols, rows],
        "worst_tile": worst, "tiles_over_3": over, "alphas": sorted(alphas),
        "visible_colours": len(colours), "off_palette": off_palette,
        "frames": frames, "image": image,
    }


def main():
    allowed, palette_count = allowed_colours()
    print("palette %s holds %d colours" % (os.path.basename(PALETTE), palette_count))
    rows = []
    for label, path in (
        ("with_poses/overworld", os.path.join(REPO, "output", "char_pipe", "with_poses", "spr_pp_char_overworld.png")),
        ("with_poses/battle", os.path.join(REPO, "output", "char_pipe", "with_poses", "spr_pp_char_battle.png")),
        ("no_poses/overworld", os.path.join(REPO, "output", "char_pipe", "no_poses", "spr_pp_char_overworld.png")),
        ("no_poses/battle", os.path.join(REPO, "output", "char_pipe", "no_poses", "spr_pp_char_battle.png")),
    ):
        fw, fh = (16, 16) if "overworld" in label else (24, 32)
        r = report_sheet(path, fw, fh, allowed)
        rows.append((label, r))
        print("\n[%s] %dx%d  frames %dx%d  worst tile %d  over-3 tiles %d  alpha %s  colours %d  off-palette %d"
              % (label, r["size"][0], r["size"][1], r["grid"][0], r["grid"][1], r["worst_tile"],
                 len(r["tiles_over_3"]), r["alphas"], r["visible_colours"], len(r["off_palette"])))
        print("  empty frames: %s" % [f["box"][:2] for f in r["frames"] if f["opaque"] == 0])

    by_label = dict(rows)

    # --- overworld layout: rows down/up/left/right, cols walk0/walk1
    ow = by_label["with_poses/overworld"]
    frames = ow["frames"]
    assert ow["size"] == (32, 64) and len(frames) == 8
    idx = lambda d_row, walk: frames[d_row * 2 + walk]  # noqa: E731
    mirror_ok = True
    for d_row, direction in enumerate(("down", "up", "left", "right")):
        right0, right1 = idx(3, 0), idx(3, 1)
        left0, left1 = idx(2, 0), idx(2, 1)
        # left row must be the mirrored right row
        crop_right0 = ow["image"].crop((0, 3 * 16, 16, 64))
        crop_left0 = ow["image"].crop((0, 2 * 16, 16, 48))
        if crop_left0.tobytes() != crop_right0.transpose(Image.FLIP_LEFT_RIGHT).tobytes():
            mirror_ok = False
        break
    print("\noverworld: left row == mirror(right row): %s" % mirror_ok)
    down0, down1 = idx(0, 0), idx(0, 1)
    up0, up1 = idx(1, 0), idx(1, 1)
    r0, r1 = idx(3, 0), idx(3, 1)
    print("overworld walk frames differ: down %s up %s right %s left %s"
          % (down0["bytes"] != down1["bytes"], up0["bytes"] != up1["bytes"],
             r0["bytes"] != r1["bytes"], idx(2, 0)["bytes"] != idx(2, 1)["bytes"]))
    print("overworld opaque pixels per frame: %s" % [f["opaque"] for f in frames])

    # --- battle frames
    bt = by_label["with_poses/battle"]
    names = ["idle_0", "idle_1", "attack_0", "attack_1", "attack_2", "hurt_0", "down_0"]
    print("\nbattle: %dx%d, %d frames at 24x32" % (bt["size"][0], bt["size"][1], len(bt["frames"])))
    print("battle opaque per frame: %s" % dict(zip(names, [f["opaque"] for f in bt["frames"]])))
    distinct = {}
    for i in range(len(bt["frames"])):
        for j in range(i + 1, len(bt["frames"])):
            distinct["%s/%s" % (names[i], names[j])] = bt["frames"][i]["bytes"] != bt["frames"][j]["bytes"]
    dupes = [k for k, v in distinct.items() if not v]
    print("battle identical frame pairs: %s" % (dupes or "none"))

    # --- TODO frames in the no-pose sheet: should be a pure single-colour diagonal X
    nop = by_label["no_poses/battle"]
    todo_like = []
    for name, frame in zip(names, nop["frames"]):
        px = nop["image"].crop(frame["box"]).load()
        marks = [(x, y) for y in range(32) for x in range(24) if px[x, y][3]]
        diag = [(x, y) for (x, y) in marks if x == y or x + y == 23]
        todo_like.append((name, len(marks), len(marks) == len(diag) and len(marks) > 0))
    print("\nno_poses battle frames: (name, opaque, is_plain_diagonal_X) = %s" % todo_like)

    # --- preview
    for label in ("with_poses", "no_poses"):
        p = os.path.join(REPO, "output", "char_pipe", label, "preview_3x.png")
        img = load(p)
        print("\npreview %s: %dx%d (3x sheets would be 504x%d + gap)" % (label, img.width, img.height,
                                                                        (64 + 32) * 3))

    # --- falsification: is nes_check load-bearing? inject a 4th colour into one tile
    src = os.path.join(REPO, "output", "char_pipe", "with_poses", "spr_pp_char_battle.png")
    broken_path = os.path.join(tempfile.mkdtemp(prefix="char_pipe_review_"), "broken_battle.png")
    broken = load(src)
    bp = broken.load()
    extra = None
    for colour in allowed:
        extra = colour
        break
    # paint 4 opaque palette colours into one 8x8 tile so the sprite rule must fail
    picked = [c for c in sorted(allowed)][:4]
    for i, colour in enumerate(picked):
        for k in range(TILE):
            bp[i * TILE + k, k * TILE + 0] = colour + (255,)
    broken.save(broken_path)
    worst, over = tile_max(broken)
    print("\nfalsification image: worst tile %d, tiles over 3 = %d (solver must be doing work)"
          % (worst, len(over)))
    print("BROKEN_PATH=%s" % broken_path)


if __name__ == "__main__":
    main()
