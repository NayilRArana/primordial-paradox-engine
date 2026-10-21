"""Tests for tools/art/make_title_ui.py: the title logo, the 8x8 font and the menu cursor.

The generator writes into a throwaway root (a copy of data\\palette.json plus empty output folders), so the test
never writes into the live tree and never depends on files another lane is writing.

What is proved here, rather than asserted in a comment:
  - two runs of the same script produce byte identical files, so the art is deterministic;
  - every visible pixel is an exact entry of data\\palette.json and no sprite exceeds the 16 colour cap;
  - the three sprites match the interface contract in TITLE-COORD.md (name, size, frame count);
  - the font strip carries every contract glyph, one frame per glyph in ASCII order;
  - the logo reads PRIMORDIAL over PARADOX and the lightning crack crosses the O of PARADOX;
  - the cursor is an arrow with a 1 px outline, lit in frame 0 and dim in frame 1.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES = os.path.join(ROOT, "game", "sprites_src", "title")

INK = (11, 11, 15, 255)
STONE = (117, 99, 76, 255)
STONE_LIT = (166, 149, 124, 255)
GOLD = (179, 143, 40, 255)
DIM = (46, 46, 58, 255)
PAPER = (200, 200, 212, 255)

CONTRACT_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!? :'- "


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    """Run the generator twice in two throwaway roots and return both output trees.

    The generator is imported and called in process, not run as a child process. That is deliberate: spawning a child
    was the one step in this test that could fail for a reason that has nothing to do with the art. On Windows the
    spawn can fail with "The request is not supported" (WinError 50) or with a stale inherited handle (WinError 6)
    when an earlier test has left the process in an odd state, and then the failure reads like a fault in the logo when
    it is a fault in the harness. Calling the generator directly removes that whole failure class.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_title_ui as gen

    runs = []
    for name in ("run_a", "run_b"):
        root = tmp_path_factory.mktemp(name)
        shutil.copytree(os.path.join(ROOT, "data"), root / "data")
        (root / "game" / "sprites_src" / "title").mkdir(parents=True)
        (root / "output").mkdir(parents=True)
        assert gen.generate(str(root)) == 0, "the generator reported a failure"
        runs.append(root)
    return runs


def sprite_paths(root) -> dict:
    out = {}
    for name in ("spr_pp_title_logo", "spr_pp_font8", "spr_pp_menu_cursor"):
        out[name] = (
            os.path.join(root, "game", "sprites_src", "title", name + ".png"),
            os.path.join(root, "game", "sprites_src", "title", name + ".json"),
        )
    return out


def palette_hexes() -> set:
    with open(os.path.join(ROOT, "data", "palette.json"), "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return {c.lower() for c in data["colours"]}


# ---------------------------------------------------------------------------------------------------------------
# Determinism.

def test_two_runs_produce_identical_bytes(generated):
    run_a, run_b = generated
    names = ("spr_pp_title_logo", "spr_pp_font8", "spr_pp_menu_cursor")
    for name in names:
        png_a, json_a = sprite_paths(run_a)[name]
        png_b, json_b = sprite_paths(run_b)[name]
        assert sha256(png_a) == sha256(png_b), "%s png differs between runs" % name
        assert sha256(json_a) == sha256(json_b), "%s json differs between runs" % name
    assert sha256(os.path.join(run_a, "output", "title_ui_preview.png")) == \
        sha256(os.path.join(run_b, "output", "title_ui_preview.png")), "the preview differs between runs"


# ---------------------------------------------------------------------------------------------------------------
# The palette rules.

@pytest.mark.parametrize("name", ["spr_pp_title_logo", "spr_pp_font8", "spr_pp_menu_cursor"])
def test_every_pixel_is_a_master_palette_colour(generated, name):
    root = generated[0]
    png_path, _ = sprite_paths(root)[name]
    allowed = palette_hexes()
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
        seen = set()
        pixels = sheet.get_flattened_data() if hasattr(sheet, "get_flattened_data") else sheet.getdata()
        for r, g, b, a in pixels:
            if a == 0:
                continue
            value = "#%02x%02x%02x" % (r, g, b)
            assert value in allowed, "%s uses %s, which is not in data/palette.json" % (name, value)
            seen.add(value)
    assert len(seen) <= 16, "%s uses %d colours, the room cap is 16" % (name, len(seen))


# ---------------------------------------------------------------------------------------------------------------
# The interface contract: name, size, frame count.

def test_logo_matches_the_contract(generated):
    root = generated[0]
    png_path, json_path = sprite_paths(root)["spr_pp_title_logo"]
    with open(json_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    assert meta["name"] == "spr_pp_title_logo"
    assert (meta["frame_w"], meta["frame_h"]) == (224, 56), "the contract says about 224x56"
    assert meta["frames"] == 2, "frame 0 normal, frame 1 gold shimmer"
    with Image.open(png_path) as img:
        assert img.size == (224 * 2, 56), "the strip is the frames side by side"


def test_font_matches_the_contract(generated):
    root = generated[0]
    png_path, json_path = sprite_paths(root)["spr_pp_font8"]
    with open(json_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    assert meta["name"] == "spr_pp_font8"
    assert (meta["frame_w"], meta["frame_h"]) == (8, 8)
    assert meta["frames"] == 44, "26 letters, 10 digits, 7 marks and the space"
    with Image.open(png_path) as img:
        assert img.size == (8 * 44, 8)


def test_cursor_matches_the_contract(generated):
    root = generated[0]
    png_path, json_path = sprite_paths(root)["spr_pp_menu_cursor"]
    with open(json_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    assert meta["name"] == "spr_pp_menu_cursor"
    assert (meta["frame_w"], meta["frame_h"]) == (8, 8)
    assert meta["frames"] == 2
    with Image.open(png_path) as img:
        assert img.size == (16, 8)


# ---------------------------------------------------------------------------------------------------------------
# The font strip itself.

def test_font_strip_carries_every_contract_glyph_in_ascii_order(generated):
    root = generated[0]
    png_path, _ = sprite_paths(root)["spr_pp_font8"]
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_title_ui as gen

    order = sorted(gen.FONT.keys(), key=ord)
    assert len(order) == 44
    for glyph in CONTRACT_GLYPHS:
        assert glyph in gen.FONT, "the font is missing the contract glyph %r" % glyph
    # ASCII order means the space comes first and the letters last.
    assert order[0] == " "
    assert order[-1] == "Z"
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
        for index, glyph in enumerate(order):
            cell = sheet.crop((index * 8, 0, index * 8 + 8, 8))
            lit = 0
            for y in range(8):
                for x in range(8):
                    if cell.getpixel((x, y))[3] > 0:
                        lit += 1
            if glyph == " ":
                assert lit == 0, "the space frame is not empty"
            else:
                assert lit > 0, "the frame for %r is empty" % glyph
                assert all(
                    cell.getpixel((1 + gx, gy))[3] > 0
                    for gy in range(gen.GLYPH_H)
                    for gx in range(gen.GLYPH_W)
                    if gen.FONT[glyph][gy][gx] == "#"
                ), "the frame for %r is missing a stroke pixel" % glyph


# ---------------------------------------------------------------------------------------------------------------
# The logo.

def logo_frame(root, index: int) -> Image.Image:
    png_path, _ = sprite_paths(root)["spr_pp_title_logo"]
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
    return sheet.crop((index * 224, 0, (index + 1) * 224, 56))


def test_logo_reads_primordial_over_paradox(generated):
    root = generated[0]
    frame = logo_frame(root, 0)
    pixels = frame.load()
    # The gold inlay is part of a letter, so a column of a letter counts when it holds stone, lit stone or gold.
    stone = {STONE, STONE_LIT, GOLD}
    for text, top, height, count in (("PRIMORDIAL", 5, 21, 10), ("PARADOX", 30, 21, 7)):
        columns = [x for x in range(224)
                   if any(pixels[x, y] in stone for y in range(top, top + height))]
        groups = []
        for x in columns:
            if groups and x == groups[-1][1] + 1:
                groups[-1][1] = x
            else:
                groups.append([x, x])
        assert len(groups) == count, "%s should be %d letters, the PNG shows %d" % (text, count, len(groups))


def test_logo_carries_stone_gold_and_a_dark_outline(generated):
    root = generated[0]
    frame = logo_frame(root, 0)
    pixels = frame.load()
    seen = set()
    for y in range(56):
        for x in range(224):
            colour = pixels[x, y]
            if colour[3] == 0:
                continue
            seen.add(colour)
    assert INK in seen, "no dark outline"
    assert STONE in seen and STONE_LIT in seen, "no weathered stone"
    assert GOLD in seen, "no gold inlay"


def test_the_crack_crosses_the_o_of_paradox(generated):
    """The lightning crack has to break the O of PARADOX, not just sit next to it."""
    root = generated[0]
    frame = logo_frame(root, 0)
    pixels = frame.load()
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_title_ui as gen

    line = [l for l in gen.LOGO_LINES if l[5] == "paradox"][0]
    text, sx, sy, gutter, top, tag = line
    mask, width, placed = gen.letter_mask(text, sx, sy, gutter)
    x_offset = (gen.LOGO_W - width) // 2
    placed = [(ch, i, x_offset + x0, w) for ch, i, x0, w in placed]
    o_letter = [p for p in placed if p[0] == "O"][-1]
    ox0, owidth = o_letter[2], o_letter[3]
    y0, y1 = top, top + gen.GLYPH_H * sy - 1

    ink = [(x, y) for x in range(ox0, ox0 + owidth) for y in range(y0, y1 + 1)
           if pixels[x, y] == INK]
    assert len(ink) >= 6, "the crack does not cross the O of PARADOX (%d ink px)" % len(ink)


def test_frame_one_is_a_shimmer_and_not_a_second_drawing(generated):
    root = generated[0]
    frame0 = logo_frame(root, 0)
    frame1 = logo_frame(root, 1)
    differing = sum(
        1
        for y in range(56)
        for x in range(224)
        if frame0.getpixel((x, y)) != frame1.getpixel((x, y))
    )
    assert differing > 20, "frame 1 is too close to frame 0 to read as a shimmer"
    # The shimmer is a band of gold, so the band must actually be gold in frame 1.
    gold_pixels = sum(
        1
        for y in range(56)
        for x in range(224)
        if frame1.getpixel((x, y)) == GOLD
    )
    assert gold_pixels > sum(
        1
        for y in range(56)
        for x in range(224)
        if frame0.getpixel((x, y)) == GOLD
    ), "frame 1 has no more gold than frame 0, so nothing shimmers"


# ---------------------------------------------------------------------------------------------------------------
# The cursor.

def test_cursor_is_an_outlined_arrow_that_changes_state(generated):
    root = generated[0]
    png_path, _ = sprite_paths(root)["spr_pp_menu_cursor"]
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
    frame0 = sheet.crop((0, 0, 8, 8)).load()
    frame1 = sheet.crop((8, 0, 16, 8)).load()

    body = {(1, 1), (2, 1),
            (1, 2), (2, 2), (3, 2),
            (1, 3), (2, 3), (3, 3), (4, 3),
            (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
            (1, 5), (2, 5), (3, 5), (4, 5),
            (1, 6), (2, 6), (3, 6)}
    outline = set()
    for x, y in body:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (x + dx, y + dy) not in body and 0 <= x + dx < 8 and 0 <= y + dy < 8:
                    outline.add((x + dx, y + dy))
    for name, cell, fill in (("frame 0", frame0, GOLD), ("frame 1", frame1, DIM)):
        for x in range(8):
            for y in range(8):
                pixel = cell[x, y]
                if (x, y) in body:
                    assert pixel == fill, "cursor %s body pixel %d,%d is %r" % (name, x, y, pixel)
                elif (x, y) in outline:
                    assert pixel == INK, "cursor %s outline pixel %d,%d is %r" % (name, x, y, pixel)
                else:
                    assert pixel[3] == 0, "cursor %s has ink outside the arrow at %d,%d" % (name, x, y)


# ---------------------------------------------------------------------------------------------------------------
# The preview the director looks at.

def test_preview_holds_the_logo_the_font_and_the_cursor(generated):
    """The preview is what the director looks at, so it must carry the real art at 3x, not a redrawing."""
    root = generated[0]
    preview_path = os.path.join(root, "output", "title_ui_preview.png")
    with Image.open(preview_path) as img:
        preview = img.convert("RGBA")
    assert preview.width >= 640 and preview.height >= 480, "the preview is too small to judge"

    def holds(sprite, box, scale):
        x, y = box
        big = sprite.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)
        if x + big.width > preview.width or y + big.height > preview.height:
            return False
        for cx in range(big.width):
            for cy in range(big.height):
                source = big.getpixel((cx, cy))
                if source[3] == 0:
                    continue
                if preview.getpixel((x + cx, y + cy))[:3] != source[:3]:
                    return False
        return True

    logo = logo_frame(root, 0)
    shimmer = logo_frame(root, 1)
    png_path, _ = sprite_paths(root)["spr_pp_font8"]
    with Image.open(png_path) as img:
        font = img.convert("RGBA")
    cur_path, _ = sprite_paths(root)["spr_pp_menu_cursor"]
    with Image.open(cur_path) as img:
        cursor = img.convert("RGBA")

    assert holds(logo, (48, 76), 3), "the preview does not carry the 3x logo, frame 0"
    assert holds(shimmer, (48, 268), 3), "the preview does not carry the 3x logo, frame 1"
    assert holds(font, (48, 474), 3), "the preview does not carry the 3x font strip"
    assert holds(cursor.crop((0, 0, 8, 8)), (48, 560), 3), "the preview does not carry the 3x cursor"


# ---------------------------------------------------------------------------------------------------------------
# The committed files match what the script produces.

def test_the_committed_sprites_match_a_fresh_run(generated):
    """The PNGs in the repository must be the ones the script writes, not an edited copy."""
    root = generated[0]
    for name in ("spr_pp_title_logo", "spr_pp_font8", "spr_pp_menu_cursor"):
        fresh_png, fresh_json = sprite_paths(root)[name]
        live_png = os.path.join(SPRITES, name + ".png")
        live_json = os.path.join(SPRITES, name + ".json")
        assert os.path.exists(live_png), "%s is missing from the repository" % live_png
        assert sha256(fresh_png) == sha256(live_png), \
            "%s in the repository is not what the script writes" % name
        assert sha256(fresh_json) == sha256(live_json), \
            "%s.json in the repository is not what the script writes" % name
