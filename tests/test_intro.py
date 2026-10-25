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
     this card is reviewed on come from that path;
  8. every committed fade strip is the fade of the base strip committed beside it, which is the ordering
     rule card t_cd6a0d24 was opened for: five animations had fades of pictures the game no longer draws,
     and the tool that was supposed to notice only asked whether the files existed.

Run: python -m pytest tests/test_intro.py -q
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys

import pytest
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


# Card TEST-CLASSIFY-33: this compares the PNG the generator writes on this host with the committed
# copy, byte for byte. The pixels agree off the box; the Pillow and zlib encoder does not, so only the
# host that wrote the committed file can pass it.
@pytest.mark.host_png_bytes
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
                            capture_output=True, text=True, stdin=subprocess.DEVNULL)
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


# ---------------------------------------------------------------------------------------------------------
# Card t_cd6a0d24: the fade strips are derived art, so they have to be the fades of the bases that ship.
# ---------------------------------------------------------------------------------------------------------

def committed(rel: str) -> bytes:
    """The bytes HEAD holds for one path, so the pair a commit ships is what gets judged.

    The `./` makes the path relative to ROOT: this tree is a subdirectory of the repo it lives in, so a bare
    `HEAD:game/...` names the wrong place.
    """
    result = subprocess.run(["git", "-C", ROOT, "show", "HEAD:./%s" % rel.replace("\\", "/")],
                            capture_output=True, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout


def committed_image(rel: str) -> Image.Image:
    with Image.open(io.BytesIO(committed(rel))) as handle:
        return handle.convert("RGBA")


@pytest.mark.needs_git_checkout
def test_every_committed_fade_strip_is_the_fade_of_the_base_it_ships_with():
    """The ordering rule, as a red test: ship a base without re-running the fades and this fails, naming the file.

    Measured on the tree this card was opened on: 13 strips across five animations were the fades of pictures the
    game no longer draws, and the only thing that could have noticed asked whether the file existed.

    The pair judged here is the one in HEAD, not the working copy. A lane can be mid repaint with a base that is
    newer than any fade it has written yet, and that is not a defect the suite should report at someone else's
    door; the working copy is judged by `python tools/pp_intro_art.py --check`, which is the command a lane runs
    after touching art. Both sides of the comparison come from the same commit, so this one can only be red for
    the thing that matters: a commit that shipped a stale fade.
    """
    art = load("pp_intro_art")
    palette = art.load_palette()
    rule = art.fade_rule(ROOT)
    stale = []
    for name in art.FADED_ANIMATIONS:
        base_rel = "game/sprites_src/title/%s.png" % name
        sidecar = json.loads(committed("game/sprites_src/title/%s.json" % name).decode("utf-8"))
        base = committed_image(base_rel)
        for steps in range(1, art.FADE_STEPS + 1):
            twin = "%s_fade%d" % (name, steps)
            want = art.fade_for(twin, base, sidecar, steps, palette, rule)
            have = committed_image("game/sprites_src/title/%s.png" % twin)
            assert have.size == want.size, "%s is %dx%d and its base fades to %dx%d" % (
                twin, have.width, have.height, want.width, want.height)
            if have.tobytes() != want.tobytes():
                differing = sum(1 for a, b in zip(have.getdata(), want.getdata()) if a != b)
                stale.append("%s%s.png is not the fade of %s.png (%d pixel(s) differ)"
                             % ("game/sprites_src/title/", twin, name, differing))
    assert stale == [], "\n".join(stale)


def test_the_fade_check_catches_a_base_repainted_underneath_it(tmp_path):
    """A stale fade is reported as stale, not as missing: the check has to read the picture, not the file list."""
    art = load("pp_intro_art")
    palette = art.load_palette()
    root = private_root(tmp_path)
    src = os.path.join(root, "game", "sprites_src", "title")
    # The working tree can hold a base a lane has not finished with, so the copy starts from fades this test wrote
    # itself: the subject is the detector, not the state of somebody else's art.
    art.write_fades(root, palette)
    assert art.check_fades(root, palette) == []

    # Repaint one base strip the way an art lane would: an opaque pixel becomes another chip colour. Its fades are
    # now pictures of a strip that no longer exists.
    base_path = os.path.join(src, "title_L6_road.png")
    with Image.open(base_path) as handle:
        sheet = handle.convert("RGBA")
    painted = None
    for y in range(sheet.height):
        for x in range(sheet.width):
            if painted is None and sheet.getpixel((x, y))[3] == 255:
                sheet.putpixel((x, y), palette[0x21] + (255,))
                painted = (x, y)
    assert painted is not None
    sheet.save(base_path)

    stale = art.check_fades(root, palette)
    assert any("title_L6_road_fade1.png is not the fade of title_L6_road.png" in line for line in stale), stale
    # The strips of the other animations are still the fades of their own bases: the check is per strip, not a
    # whole-directory flag that one repaint would silence.
    assert not any("title_L7_fg" in line for line in stale), stale


def test_writing_the_fades_twice_changes_nothing(tmp_path):
    """The generator is the last writer, so a second run has to be a no-op: that is what makes the order safe.

    scene_palette.py's apply pass ends by calling write_fades() here, so on a lane that runs the art order the
    generator runs twice in a row. If the second write differed, every art pass would leave the tree dirty.
    """
    art = load("pp_intro_art")
    palette = art.load_palette()
    root = private_root(tmp_path)
    src = os.path.join(root, "game", "sprites_src", "title")
    art.write_fades(root, palette)
    first = read_pngs(src)
    art.write_fades(root, palette)
    second = read_pngs(src)
    changed = [name for name in first if first[name] != second[name]]
    assert changed == [], changed


def private_root(tmp_path) -> str:
    """A root with the palette, the scene and the title art copied in, so a test can rewrite art and nothing else."""
    root = os.path.join(str(tmp_path), "root")
    src = os.path.join(root, "game", "sprites_src", "title")
    os.makedirs(src, exist_ok=True)
    os.makedirs(os.path.join(root, "data", "palettes"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "data", "nes_palette.json"),
                os.path.join(root, "data", "nes_palette.json"))
    shutil.copy(os.path.join(ROOT, "data", "palettes", "scene_title.json"),
                os.path.join(root, "data", "palettes", "scene_title.json"))
    title = os.path.join(ROOT, "game", "sprites_src", "title")
    for name in os.listdir(title):
        shutil.copy(os.path.join(title, name), os.path.join(src, name))
    return root


def read_pngs(directory: str) -> dict:
    out = {}
    for name in sorted(os.listdir(directory)):
        if name.endswith(".png"):
            with open(os.path.join(directory, name), "rb") as handle:
                out[name] = handle.read()
    return out
