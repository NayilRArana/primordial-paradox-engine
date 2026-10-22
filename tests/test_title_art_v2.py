"""Pins for TS2-ART-A: the v2 title logo and the v2 title car.

What these tests hold down, and why each one earns its place:
  1. both sprites pass tools/nes_check.py as sprites, so the card's check is a test rather than a habit;
  2. the logo uses exactly 4 colours, the car at most the 7 named in the script, and every colour is a real
     2C02 entry (a sprite drawn in an invented palette passes its own checker and fails the hardware);
  3. the car's glass is one colour and lives only in the window band (rows 8 to 15), which is the card's
     "dark tinted windows, no faces or busts" made measurable;
  4. the title no longer draws spr_title_theo, spr_title_ronan or spr_title_bubble, while the sprite files stay
     on disk for the interior scenes later;
  5. the generators are deterministic: a second run writes byte identical PNGs.

Run: python -m pytest tests/test_title_art_v2.py -q
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

from PIL import Image
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE_DIR = os.path.join(ROOT, "game", "sprites_src", "title")
PY = sys.executable or "python"


@pytest.fixture(scope="module", autouse=True)
def v2_sprites():
    """Draw both sprites before anything is measured.

    The v2 generators are the source of truth for these two files, so this fixture runs them rather than
    trusting whatever is on disk: tests/test_make_title_ui.py still carries the v1 logo generator, which writes
    the same sprite name into a temporary root, and the module order of a suite run must not decide which logo
    the checks see.
    """
    for script in (("tools", "art", "title_logo_v2.py"), ("tools", "art", "title_car_v2.py")):
        result = subprocess.run([PY, os.path.join(*script)], cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    return True


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *args], cwd=ROOT, capture_output=True, text=True)


def nes_palette() -> set:
    with open(os.path.join(ROOT, "data", "nes_palette.json"), encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return {value.lower() for value in data["colours"]}


def opaque_colours(path: str) -> dict:
    image = Image.open(path).convert("RGBA")
    counts = {}
    for pixel in image.getdata():
        if pixel[3] == 0:
            continue
        key = "#%02x%02x%02x" % pixel[:3]
        counts[key] = counts.get(key, 0) + 1
    return counts


def test_logo_passes_nes_check():
    result = run(os.path.join("tools", "nes_check.py"),
                 os.path.join("game", "sprites_src", "title", "spr_pp_title_logo.png"),
                 "--type", "sprite")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_car_passes_nes_check():
    result = run(os.path.join("tools", "nes_check.py"),
                 os.path.join("game", "sprites_src", "title", "spr_title_car.png"),
                 "--type", "sprite")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_logo_is_four_nes_colours_two_frames():
    path = os.path.join(TITLE_DIR, "spr_pp_title_logo.png")
    with Image.open(path) as image:
        assert image.size == (224 * 2, 64)
    with open(os.path.join(TITLE_DIR, "spr_pp_title_logo.json"), encoding="utf-8") as handle:
        meta = json.load(handle)
    assert (meta["frame_w"], meta["frame_h"], meta["frames"]) == (224, 64, 2)
    colours = opaque_colours(path)
    assert len(colours) == 4, colours
    assert set(colours) <= nes_palette(), set(colours) - nes_palette()


def test_car_colours_are_nes_and_glass_is_one_colour_in_the_window_band():
    path = os.path.join(TITLE_DIR, "spr_title_car.png")
    with Image.open(path) as image:
        assert image.size == (64 * 3, 32)
        pixels = image.convert("RGBA").load()
        for frame in range(3):
            for y in range(32):
                for x in range(64):
                    pixel = pixels[frame * 64 + x, y]
                    if pixel[3] == 0:
                        continue
                    key = "#%02x%02x%02x" % pixel[:3]
                    assert key in nes_palette(), (frame, x, y, key)
                    # The dark tint (#004058, $0C) is the glass and nothing else, and the glass never
                    # leaves the window band: no face, no bust, no interior.
                    if key == "#004058":
                        assert 8 <= y <= 15, (frame, x, y)
    with open(os.path.join(TITLE_DIR, "spr_title_car.json"), encoding="utf-8") as handle:
        meta = json.load(handle)
    assert (meta["frame_w"], meta["frame_h"], meta["frames"]) == (64, 32, 3)
    assert len(opaque_colours(path)) <= 7


def test_title_draws_no_cast_but_keeps_the_files():
    script = open(os.path.join(ROOT, "game", "scripts", "pp_title", "pp_title.gml"),
                  encoding="utf-8").read()
    for name in ("spr_title_theo", "spr_title_ronan", "spr_title_bubble"):
        assert 'pp_art_draw("%s"' % name not in script, name
        assert os.path.isfile(os.path.join(TITLE_DIR, name + ".png")), name


def test_generators_are_deterministic():
    for script, sprite in ((("tools", "art", "title_logo_v2.py"), "spr_pp_title_logo"),
                           (("tools", "art", "title_car_v2.py"), "spr_title_car")):
        path = os.path.join(*script)
        first = run(path)
        assert first.returncode == 0, first.stdout + first.stderr
        before = sha256(os.path.join(TITLE_DIR, sprite + ".png"))
        second = run(path)
        assert second.returncode == 0, second.stdout + second.stderr
        after = sha256(os.path.join(TITLE_DIR, sprite + ".png"))
        assert before == after, sprite


# ---------------------------------------------------------------------------------------------------------------
# The three things the card names that a colour count cannot see: the drop shadow, the crossing, the shimmer.

def logo_module():
    """The generator as a module, so the geometry the test measures is the geometry that drew the PNG."""
    art = os.path.join(ROOT, "tools", "art")
    if art not in sys.path:
        sys.path.insert(0, art)
    import title_logo_v2

    return title_logo_v2


def logo_geometry():
    """(module, line 1 body, whole body, sickle, bolt, emblem placed on the sheet)."""
    mod = logo_module()
    line_one = mod.line_pixels("PRIMORDIAL", mod.LOGO_LINES[0][1])
    body = set(line_one)
    for text, top in mod.LOGO_LINES:
        body |= mod.line_pixels(text, top)
    sickle, bolt = mod.emblem_shapes()
    emblem = {(x + mod.EMBLEM_LEFT, y + mod.EMBLEM_TOP) for x, y in sickle | bolt}
    return mod, line_one, body | emblem, sickle, bolt, emblem


def logo_frame(index: int) -> Image.Image:
    with Image.open(os.path.join(TITLE_DIR, "spr_pp_title_logo.png")) as image:
        sheet = image.convert("RGBA")
    return sheet.crop((index * 224, 0, (index + 1) * 224, 64))


def ink_run(px, x, y, dx, dy, ink, limit=6):
    run = 0
    cx, cy = x + dx, y + dy
    while 0 <= cx < 224 and 0 <= cy < 64 and px[cx, cy] == ink and run < limit:
        run += 1
        cx += dx
        cy += dy
    return run


def edge_runs(px, line_one, ink):
    """The ink run out of every straight edge of the first line, one list per direction.

    Only straight edges are sampled, so a serif or a letter corner cannot be mistaken for a shadow. The
    first line is used because nothing is drawn above it, which is what makes the up run meaningful.
    """
    runs = {"up": [], "down": [], "left": [], "right": []}
    for x, y in line_one:
        if (x, y - 1) not in line_one and (x, y + 1) in line_one \
                and (x - 1, y - 1) not in line_one and (x + 1, y - 1) not in line_one \
                and (x - 1, y) in line_one and (x + 1, y) in line_one:
            runs["up"].append(ink_run(px, x, y, 0, -1, ink))
        if (x, y + 1) not in line_one and (x, y - 1) in line_one \
                and (x - 1, y + 1) not in line_one and (x + 1, y + 1) not in line_one \
                and (x - 1, y) in line_one and (x + 1, y) in line_one and (x - 2, y) in line_one:
            runs["down"].append(ink_run(px, x, y, 0, 1, ink))
        if (x - 1, y) not in line_one and (x + 1, y) in line_one \
                and (x - 1, y - 1) not in line_one and (x - 1, y + 1) not in line_one \
                and (x, y - 1) in line_one and (x, y + 1) in line_one \
                and (x - 3, y - 2) not in line_one and (x - 2, y - 1) not in line_one:
            runs["left"].append(ink_run(px, x, y, -1, 0, ink))
        if (x + 1, y) not in line_one and (x - 1, y) in line_one \
                and (x + 1, y - 1) not in line_one and (x + 1, y + 1) not in line_one \
                and (x, y - 1) in line_one and (x, y + 1) in line_one and (x, y - 2) in line_one:
            runs["right"].append(ink_run(px, x, y, 1, 0, ink))
    return runs


def test_the_logo_has_a_one_pixel_drop_shadow_outside_the_outline():
    """A shadow that lands inside the outline ring is not a shadow: it is more of the same ink.

    The card asks for a 1 px drop shadow, so the ink has to sit outside the 8 neighbour ring on the down
    right side. That makes the ink run below and to the right 2 where it is 1 above and to the left.
    """
    mod, line_one, body, _, _, _ = logo_geometry()
    colours, _ = mod.nes_tile.load_nes_palette(ROOT)
    ink = colours[mod.INK]
    ring = mod.nes_tile.outline_of(body)
    for index in (0, 1):
        frame = logo_frame(index)
        px = frame.load()
        ink_pixels = {(x, y) for y in range(64) for x in range(224) if px[x, y] == ink}
        outside = ink_pixels - ring
        assert len(outside) > 100, \
            "frame %d: every ink pixel is inside the outline ring, so there is no drop shadow" % index
        runs = edge_runs(px, line_one, ink)
        assert len(runs["down"]) >= 40 and len(runs["right"]) >= 40, runs
        assert len(runs["up"]) >= 40 and len(runs["left"]) >= 40, runs
        assert min(runs["up"]) == 1 and min(runs["left"]) == 1, runs
        assert min(runs["down"]) == 2 and min(runs["right"]) == 2, runs


def test_the_emblem_is_a_crossed_sickle_and_thunderbolt():
    """The two shapes have to share pixels, or the mark is two shapes beside each other, not a crossing."""
    mod, _, _, sickle, bolt, emblem = logo_geometry()
    shared = sickle & bolt
    assert shared, "the thunderbolt and the sickle share no pixels, they cannot read as crossed"
    assert all(0 <= x < mod.EMBLEM_W and 0 <= y < mod.EMBLEM_H for x, y in sickle | bolt), \
        "an emblem stroke leaves the 32x16 box"
    colours, _ = mod.nes_tile.load_nes_palette(ROOT)
    gold = colours[mod.GOLD]
    px = logo_frame(0).load()
    for x, y in sorted(shared):
        assert px[x + mod.EMBLEM_LEFT, y + mod.EMBLEM_TOP] == gold, \
            "the shared pixel (%d, %d) is not gold, so the bolt does not pass over the sickle" % (x, y)
    assert max(y for _, y in emblem) < mod.LOGO_LINES[1][1], "the emblem runs into the second line"


def test_the_gold_shimmer_crosses_both_lines():
    """One frame of shimmer that lights only the first word is half a shimmer."""
    mod = logo_module()
    colours, _ = mod.nes_tile.load_nes_palette(ROOT)
    gold = colours[mod.GOLD]
    normal, shimmer = logo_frame(0), logo_frame(1)
    for text, top in mod.LOGO_LINES:
        mask = mod.line_pixels(text, top)
        changed = sum(1 for point in mask if normal.getpixel(point) != shimmer.getpixel(point))
        before = sum(1 for point in mask if normal.getpixel(point) == gold)
        after = sum(1 for point in mask if shimmer.getpixel(point) == gold)
        assert changed > 20, "%s takes no shimmer, %d pixels changed" % (text, changed)
        assert after > before, "%s gains no gold in the shimmer frame (%d -> %d)" % (text, before, after)
