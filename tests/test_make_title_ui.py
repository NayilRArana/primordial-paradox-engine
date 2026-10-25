"""Tests for tools/art/make_title_ui.py: the title logo, the 8x8 font and the menu cursor.

The generator writes into a throwaway root (a copy of data\\, a copy of the committed title art and empty
output folders), so the test never writes into the live tree and never depends on a file another lane is
editing in place.

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

CONTRACT_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?()*\" :'- "


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

    The title art is copied in, not left as an empty folder, because generate() ends with
    scene_palette.apply_title(): it composes data\\title.json's layers and remaps the UI sprites into the title
    scene's sprite palettes. The committed spr_pp_menu_cursor.png is the post pass art, so a root without the
    strips measures the pre pass sprite and reports drift that exists only in the harness. Measured 2026-10-22:
    the pre pass cursor is sha256 6a15feed..., the committed and live one is 7e15e4ad..., and the font strip is
    unchanged by the pass because it is drawn in one colour. The copies are still throwaway: apply_title rewrites
    the copies under the temporary root and never the live files.

    spr_pp_title_logo is deliberately NOT copied, so test_this_generator_writes_no_logo keeps measuring what it
    says it measures: the file is absent before the run and absent after it.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_title_ui as gen

    with open(os.path.join(ROOT, "data", "title.json"), "r", encoding="utf-8-sig") as handle:
        layer_names = [row["name"] for row in json.load(handle)["layers"]]

    runs = []
    for name in ("run_a", "run_b"):
        root = tmp_path_factory.mktemp(name)
        shutil.copytree(os.path.join(ROOT, "data"), root / "data")
        sprite_dir = root / "game" / "sprites_src" / "title"
        sprite_dir.mkdir(parents=True)
        for layer in layer_names:
            for suffix in (".png", ".json"):
                shutil.copyfile(os.path.join(SPRITES, layer + suffix), sprite_dir / (layer + suffix))
        (root / "output").mkdir(parents=True)
        assert gen.generate(str(root)) == 0, "the generator reported a failure"
        runs.append(root)
    return runs


def sprite_paths(root) -> dict:
    out = {}
    for name in ("spr_pp_font8", "spr_pp_menu_cursor"):
        out[name] = (
            os.path.join(root, "game", "sprites_src", "title", name + ".png"),
            os.path.join(root, "game", "sprites_src", "title", name + ".json"),
        )
    return out


def palette_hexes() -> set:
    with open(os.path.join(ROOT, "data", "palette.json"), "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return {c.lower() for c in data["colours"]}


def nes_palette_hexes() -> set:
    """The 2C02 outputs. The font is drawn on screen, so its pixels answer to the chip, not to the project palette."""
    with open(os.path.join(ROOT, "data", "nes_palette.json"), "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return {c.lower() for c in data["colours"]}


# ---------------------------------------------------------------------------------------------------------------
# Determinism.

def test_two_runs_produce_identical_bytes(generated):
    run_a, run_b = generated
    names = ("spr_pp_font8", "spr_pp_menu_cursor")
    for name in names:
        png_a, json_a = sprite_paths(run_a)[name]
        png_b, json_b = sprite_paths(run_b)[name]
        assert sha256(png_a) == sha256(png_b), "%s png differs between runs" % name
        assert sha256(json_a) == sha256(json_b), "%s json differs between runs" % name
    assert sha256(os.path.join(run_a, "output", "title_ui_preview.png")) == \
        sha256(os.path.join(run_b, "output", "title_ui_preview.png")), "the preview differs between runs"


# ---------------------------------------------------------------------------------------------------------------
# The palette rules.

@pytest.mark.parametrize("name", ["spr_pp_font8", "spr_pp_menu_cursor"])
def test_every_pixel_is_a_master_palette_colour(generated, name):
    root = generated[0]
    png_path, _ = sprite_paths(root)[name]
    # The font strip is the text the title screen draws and the cursor is drawn on the same frame, so both must be
    # 2C02 outputs (tools/nes_check.py enforces that too). The project palette holds no 2C02 entry at all, so a
    # cursor painted from it could never appear on a legal frame: card t_a1170172 moved it to the two entries the
    # title's ground bands declare.
    allowed = nes_palette_hexes()
    source = "data/nes_palette.json"
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
        seen = set()
        pixels = sheet.get_flattened_data() if hasattr(sheet, "get_flattened_data") else sheet.getdata()
        for r, g, b, a in pixels:
            if a == 0:
                continue
            value = "#%02x%02x%02x" % (r, g, b)
            assert value in allowed, "%s uses %s, which is not in %s" % (name, value, source)
            seen.add(value)
    assert len(seen) <= 16, "%s uses %d colours, the room cap is 16" % (name, len(seen))


# ---------------------------------------------------------------------------------------------------------------
# The interface contract: name, size, frame count.

def test_this_generator_writes_no_logo(generated):
    """One generator owns one asset name: spr_pp_title_logo belongs to tools/art/title_logo_v2.py.

    While this generator still wrote a 224x56 logo under that name, running it put the v1 art back over
    the v2 sheet and the title screen drew the wrong wordmark. The check is on the generated tree, so it
    fails the moment the write comes back.
    """
    root = generated[0]
    sprite_dir = os.path.join(root, "game", "sprites_src", "title")
    assert not os.path.exists(os.path.join(sprite_dir, "spr_pp_title_logo.png")), \
        "make_title_ui wrote a logo; the 224x56 v1 art would overwrite the v2 sprite"
    assert not os.path.exists(os.path.join(sprite_dir, "spr_pp_title_logo.json"))
    with Image.open(os.path.join(SPRITES, "spr_pp_title_logo.png")) as img:
        assert img.size == (224 * 2, 64), "the shipped logo is the v2 sheet, 224x64 by two frames"


def test_font_matches_the_contract(generated):
    root = generated[0]
    png_path, json_path = sprite_paths(root)["spr_pp_font8"]
    with open(json_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    assert meta["name"] == "spr_pp_font8"
    assert (meta["frame_w"], meta["frame_h"]) == (8, 8)
    assert meta["frames"] == 77, "26 capitals, 26 lowercase, 10 digits, 12 marks, 2 brackets and the space"
    with Image.open(png_path) as img:
        assert img.size == (8 * 77, 8)


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
    """One frame per contract glyph in ASCII order, and every frame is the Press Start 2P glyph.

    The font is no longer hand drawn: it is rasterised from Press Start 2P at 8 px (tools\\art\\pressstart2p_font.py,
    SIL OFL 1.1, licence text in knowledge\\licences). So the check is not "the strokes are the grid in make_title_ui"
    any more, it is "the strip in the repository is the font we license, in the order the contract fixes".
    """
    root = generated[0]
    png_path, _ = sprite_paths(root)["spr_pp_font8"]
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_title_ui as gen
    import pressstart2p_font

    order = list(gen.GLYPH_ORDER)
    assert len(order) == 77
    assert order == pressstart2p_font.GLYPHS, "the frame order must be ASCII order over the contract glyphs"
    for glyph in CONTRACT_GLYPHS:
        assert glyph in gen.FONT, "the logo grid is missing the contract glyph %r" % glyph
    # ASCII order means the space comes first and the lowercase letters last.
    assert order[0] == " "
    assert order[-1] == "z"
    with Image.open(png_path) as img:
        sheet = img.convert("RGBA")
        for index, glyph in enumerate(order):
            cell = sheet.crop((index * 8, 0, index * 8 + 8, 8))
            lit = {
                (x, y) for y in range(8) for x in range(8)
                if cell.getpixel((x, y))[3] > 0
            }
            rows = pressstart2p_font.bitmap(glyph)
            expected = {(x, y) for y in range(8) for x in range(8) if rows[y][x] == "#"}
            assert lit == expected, "the frame for %r is not the Press Start 2P glyph" % glyph
            if glyph == " ":
                assert lit == set(), "the space frame is not empty"
            else:
                assert lit, "the frame for %r is empty" % glyph


# ---------------------------------------------------------------------------------------------------------------
# The logo.

def logo_frame(index: int) -> Image.Image:
    """The v1 layout logo, drawn in process.

    make_title_ui no longer writes spr_pp_title_logo (tools/art/title_logo_v2.py owns that name), so the
    logo the layout preview shows is drawn through the generator instead of read from a sprite file.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_title_ui as gen

    return gen.logo_frame(index, gen.load_palette(ROOT))


def test_logo_reads_primordial_over_paradox(generated):
    root = generated[0]
    frame = logo_frame(0)
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
    frame = logo_frame(0)
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
    frame = logo_frame(0)
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
    frame0 = logo_frame(0)
    frame1 = logo_frame(1)
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
    # Card t_a1170172: the outline and the unlit body used to be the project palette's ink and the body gold. Neither
    # is a 2C02 output, so the cursor is drawn from the same two entries the font is: $20 white for the lit body and
    # $0B dark green for the lit frame's outline.
    # Card t_ae4bbd15: the unlit frame is no longer the whole silhouette in $0B. Measured on the composed frame with
    # this sprite removed, the cell the cursor is drawn in is 64 pixels of $11 #0078f8, the band 4 sky, and body $0B
    # on that ground is 2.10:1, which tools/palette_synergy.py refused. The unlit frame is now the same arrow as a
    # 50 percent white dither with a white rim, so it still reads as the arrow and still dims.
    sys.path.insert(0, os.path.join(ROOT, "tools", "art"))
    import make_title_ui as gen
    lit_ink = tuple(int(gen.FONT_INK[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    dim_ink = tuple(int(gen.FONT_DIM[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    for x, y in body:
        assert frame0[x, y] == lit_ink, "cursor frame 0 body pixel %d,%d is %r" % (x, y, frame0[x, y])
        expected = lit_ink if (x + y) % 2 == 0 else (0, 0, 0, 0)
        assert frame1[x, y] == expected, "cursor frame 1 body pixel %d,%d is %r" % (x, y, frame1[x, y])
    for x, y in outline:
        assert frame0[x, y] == dim_ink, "cursor frame 0 outline pixel %d,%d is %r" % (x, y, frame0[x, y])
        assert frame1[x, y] == lit_ink, "cursor frame 1 outline pixel %d,%d is %r" % (x, y, frame1[x, y])
    for x in range(8):
        for y in range(8):
            if (x, y) in body or (x, y) in outline:
                continue
            assert frame0[x, y][3] == 0, "cursor frame 0 has ink outside the arrow at %d,%d" % (x, y)
            assert frame1[x, y][3] == 0, "cursor frame 1 has ink outside the arrow at %d,%d" % (x, y)
    # Both frames have to give the ground rule a light body to read: $20 is the entry the rule measures on the sky
    # the cursor is drawn on (card t_ae4bbd15, palette_synergy body_ground), and the unlit frame must not spend any
    # other entry or it would be back to a dark shape on blue.
    entries0 = {frame0[x, y] for x in range(8) for y in range(8) if frame0[x, y][3]}
    entries1 = {frame1[x, y] for x in range(8) for y in range(8) if frame1[x, y][3]}
    assert entries0 == {lit_ink, dim_ink}, "cursor frame 0 spends %r, not exactly $20 and $0B" % (entries0,)
    assert entries1 == {lit_ink}, "cursor frame 1 spends %r, not exactly $20" % (entries1,)


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

    logo = logo_frame(0)
    shimmer = logo_frame(1)
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

# Card TEST-CLASSIFY-33: hashes the PNG the script writes on this host against the committed copy, so
# only the Pillow and zlib builds that wrote the committed files pass it.
@pytest.mark.host_png_bytes
def test_the_committed_sprites_match_a_fresh_run(generated):
    """The PNGs in the repository must be the ones the script writes, not an edited copy."""
    root = generated[0]
    for name in ("spr_pp_font8", "spr_pp_menu_cursor"):
        fresh_png, fresh_json = sprite_paths(root)[name]
        live_png = os.path.join(SPRITES, name + ".png")
        live_json = os.path.join(SPRITES, name + ".json")
        assert os.path.exists(live_png), "%s is missing from the repository" % live_png
        assert sha256(fresh_png) == sha256(live_png), \
            "%s in the repository is not what the script writes" % name
        assert sha256(fresh_json) == sha256(live_json), \
            "%s.json in the repository is not what the script writes" % name
