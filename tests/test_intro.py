"""Pins for INTRO-1: the NES fade, the star sprite and data, the crawl data and the capture path.

What these tests hold down, and why each one earns its place:
  1. the fade is the hardware rule and not an alpha wash: one step moves every colour one brightness
     row down (the entry sixteen below it in data/nes_palette.json), and row zero lands on black;
  2. the same fade run twice is byte identical, so a rebuilt strip is not a new picture;
  3. the star generator is deterministic too: re-running it rewrites the committed sprite byte for byte;
  4. spr_title_star is three 8x8 pattern tiles (a 5x5 cross inside each, because a sprite sheet cuts
     into whole tiles) and passes tools/nes_check.py as a sprite;
  5. the star data is the card's shapes (sickle 9, thunderbolt 7, trident 3, bident 2, loose 3 = 24),
     every point inside the 256x240 frame and above the crawl band;
  6. the crawl data is 6 beats of at most 32 columns with the card's timing numbers;
  7. tools/capture_title.py still carries the --intro path at the card's four times, because the frames
     this card is reviewed on come from that path.

Run: python -m pytest tests/test_intro.py -q
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
STAR_PATH = os.path.join(ROOT, "game", "sprites_src", "title", "spr_title_star.png")
PY = sys.executable or "python"


def load(name: str):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_one_fade_step_is_one_brightness_row():
    art = load("pp_intro_art")
    palette = art.load_palette()
    source = Image.new("RGB", (8, 1))
    for x in range(8):
        source.putpixel((x, 0), palette[1 + x])
    faded = art.fade_image(source, 1, palette)
    for x in range(8):
        entry = 1 + x
        expected = palette[art.darker_entry(entry, 1)] if entry + 16 < len(palette) else palette[0]
        # The strip comes back RGBA: the colour has to be the darker row and the alpha has to be solid, because
        # the PPU has an on and an off and no wash between them (tools/nes_check.py refuses partial alpha).
        got = faded.getpixel((x, 0))
        assert got[:3] == expected, (x, entry, expected, got)
        assert got[3] == 255, (x, entry, got)


def test_the_fade_is_deterministic():
    art = load("pp_intro_art")
    palette = art.load_palette()
    source = Image.new("RGB", (16, 16), palette[0x12])
    first = art.fade_image(source, 4, palette)
    second = art.fade_image(source, 4, palette)
    assert first.tobytes() == second.tobytes()


def test_the_star_generator_rewrites_the_committed_sprite():
    art = load("pp_intro_art")
    palette = art.load_palette()
    before = open(STAR_PATH, "rb").read()
    art.write_star_sprite(palette)
    after = open(STAR_PATH, "rb").read()
    assert before == after


def test_the_star_sprite_is_three_frames_and_nes_legal():
    meta = read_json("game/sprites_src/title/spr_title_star.json")
    assert (meta["frames"], meta["frame_w"], meta["frame_h"]) == (3, 8, 8)
    assert Image.open(STAR_PATH).size == (24, 8)
    result = subprocess.run([PY, os.path.join(TOOLS, "nes_check.py"), STAR_PATH, "--type", "sprite"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_star_data_is_the_cards_shapes():
    data = read_json("data/intro_stars.json")
    counts = {shape["name"]: len(shape["points"]) for shape in data["shapes"]}
    assert counts == {"sickle": 9, "thunderbolt": 7, "trident": 3, "bident": 2}
    loose = data["loose"]
    assert len(loose) == 3
    points = [point for shape in data["shapes"] for point in shape["points"]] + loose
    assert len(points) == 24
    for x, y in points:
        assert 2 <= x <= 253, (x, y)
        assert 2 <= y <= 160, (x, y)


def test_the_crawl_data_fits_the_card():
    data = read_json("data/intro_text.json")
    assert data["columns"] == 32
    assert len(data["beats"]) == 6
    for beat in data["beats"]:
        for line in beat:
            assert len(line) <= 32, line
            assert line == line.upper(), line
    assert data["timing"]["chars_per_second"] == 18
    assert data["timing"]["skip_key"] == "start"


def test_the_capture_path_keeps_the_cards_four_times():
    with open(os.path.join(TOOLS, "capture_title.py"), "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "--intro" in text
    assert "def run_intro_capture(" in text
    assert "INTRO_TIMES = (1.0, 4.0, 8.0, 14.0)" in text
    assert "intro_%d.png" in text
