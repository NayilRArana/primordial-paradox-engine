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
