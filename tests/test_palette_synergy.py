"""Tests for tools/palette_synergy.py (card PAL-SYSTEM, 2026-10-22).

The rules in ART-BIBLE RULE 0 point 2 are arithmetic on the 2C02 grid, so every case here is a picture whose
verdict is decided before the tool runs: a body two rows from the ground passes, a body one row away passes only
when it clears 3:1 contrast as well, white on white fails, a colour outside the scene's set fails, a four colour
tile fails. The last test runs the tool on the frames that ship today, which is the answer the card actually
asked for.
"""

from __future__ import annotations

import json
import os
import sys

import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import palette_synergy  # noqa: E402
import scene_palette_set  # noqa: E402

COLOURS, USABLE, _ = scene_palette_set.load_master(ROOT)
BLACK = COLOURS[15]


def write_png(path, pixels, size=(16, 16), background=None):
    image = Image.new("RGBA", size, (background or (0, 0, 0, 0)))
    for (x, y), rgb in pixels.items():
        image.putpixel((x, y), tuple(rgb) + (255,) if len(rgb) == 3 else tuple(rgb))
    image.save(path)
    return path


def rules_of(result):
    return {problem["rule"] for problem in result["problems"]}


BASE = {"scene": "title"}


def analyse(tmp_path, background_pixels, sprite_pixels, size=(16, 16), background=None, sidecar=None):
    background = write_png(tmp_path / "bg.png", background_pixels, size=(256, 240),
                           background=background or BLACK)
    sprite = write_png(tmp_path / "spr.png", sprite_pixels, size=size)
    if sidecar is not None:
        (tmp_path / "spr.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return palette_synergy.analyse(ROOT, BASE["scene"], background, [sprite])


def test_selftest_passes():
    assert palette_synergy.selftest(ROOT) == 0


def test_a_body_two_rows_off_the_ground_passes_body_ground(tmp_path):
    # $20 is row 2 (#f8f8f8); the backdrop $0F is row 0, so the gap is 2 and RULE 0 point 2 is met.
    body = COLOURS[0x20]
    result = analyse(tmp_path, {}, {(x, y): body for x in range(16) for y in range(16)})
    assert "body_ground" not in rules_of(result), result["problems"]
    assert "white_blob" not in rules_of(result), result["problems"]


def test_a_body_one_row_off_a_black_ground_passes_on_contrast(tmp_path):
    # $10 is row 1 (#bcbcbc, luminance 0.503) on the row 0 backdrop $0F (0.000): one row apart, 11.06:1.
    # The row is a coarse band, not a luminance, so R1 asks separation two ways and either clears it
    # (gamedev ruling, card t_50193088: this is sailor_battle.png frame 2 on battle_deck_night).
    body = COLOURS[0x10]
    result = analyse(tmp_path, {}, {(x, y): body for x in range(16) for y in range(16)})
    assert "body_ground" not in rules_of(result), result["problems"]
    assert result["exit_code"] == 0


def test_a_body_one_row_off_a_same_luminance_ground_fails_body_ground(tmp_path):
    # $00 is row 0 (#7c7c7c, 0.202) on $11 row 1 (#4478bc, 0.202): one row apart at 1.00:1, so BOTH
    # instruments are short and the pair is refused. This is the check that keeps the second instrument
    # from becoming a rubber stamp.
    result = analyse(tmp_path, {}, {(x, y): COLOURS[0x00] for x in range(16) for y in range(16)},
                     background=COLOURS[0x11])
    body_ground = [problem for problem in result["problems"] if problem["rule"] == "body_ground"]
    assert body_ground, result["problems"]
    assert body_ground[0]["rows"] == 1
    assert result["exit_code"] == 1


def test_white_on_a_light_ground_fails_white_blob(tmp_path):
    body = COLOURS[0x30]
    result = analyse(tmp_path, {(x, y): body for x in range(256) for y in range(240)}, {(x, y): body for x in range(16) for y in range(16)})
    assert "white_blob" in rules_of(result), result["problems"]


def test_a_colour_outside_the_scene_set_fails_set_member(tmp_path):
    # #ff00ff is not a 2C02 colour at all.
    result = analyse(tmp_path, {}, {(x, y): (255, 0, 255) for x in range(16) for y in range(16)})
    assert "set_member" in rules_of(result), result["problems"]


def test_four_colours_in_one_frame_fails_sprite_tile(tmp_path):
    entries = [0x20, 0x30, 0x28, 0x16]
    pixels = {}
    for index, entry in enumerate(entries):
        for x in range(index * 4, index * 4 + 4):
            for y in range(16):
                pixels[(x, y)] = COLOURS[entry]
    result = analyse(tmp_path, {}, pixels)
    assert "sprite_tile" in rules_of(result), result["problems"]
    assert "palette_count" in rules_of(result), result["problems"]


def test_no_message_names_a_fifth_sprite_palette(tmp_path):
    """Card t_c93a983f: a frame has FOUR sprite palettes, so the remedy is the drawing or the set.

    The tool used to print "... so the frame needs a fifth sprite palette" per uncovered tile and again for a
    whole frame, and that sentence is what made the party battle cast read as an open budget question for a week
    (ruling 7.1 of knowledge/PALETTE-RULINGS-2026-10-25.md: the PPU picks a sprite palette with two attribute
    bits, so a fifth one is not a budget that can be raised). The rule name, the tile coordinates and the colour
    set stay exactly where every reader and the audit counts already expect them.
    """
    source = open(os.path.join(ROOT, "tools", "palette_synergy.py"), encoding="utf-8").read()
    assert "fifth sprite palette" not in source, "the tool still names a palette the chip does not have"
    pixels = {}
    for top in range(0, 32, 8):
        for left in range(0, 24, 8):
            pair = (0x0F, 0x0C) if (left, top) == (16, 8) else (0x0F, 0x00)
            for y in range(top, top + 8):
                for x in range(left, left + 8):
                    pixels[(x, y)] = COLOURS[pair[(x + y) % 2]]
    result = analyse(tmp_path, {}, pixels, size=(24, 32),
                     sidecar={"frame_w": 24, "frame_h": 32, "frames": 1})
    assert "fifth sprite palette" not in json.dumps(result["problems"]), result["problems"]
    palette_count = [problem for problem in result["problems"] if problem["rule"] == "palette_count"]
    assert palette_count, result["problems"]
    assert palette_count[0]["tile"] == [16, 8], palette_count[0]
    assert palette_count[0]["colours"] == "$0C $0F", palette_count[0]
    assert "none of the scene's four sprite palettes" in palette_count[0]["detail"], palette_count[0]


def by_product_root(tmp_path, by_product=True, gate=True):
    """A tree whose only audit row is the by-product row: data/ copied, output/ deliberately absent."""
    import shutil

    root = str(tmp_path / "tree")
    shutil.copytree(os.path.join(ROOT, "data"), os.path.join(root, "data"))
    path = os.path.join(root, "data", "scene_palettes.json")
    payload = json.load(open(path, encoding="utf-8"))
    row = [item for item in payload["audit"] if item.get("by_product")]
    assert len(row) == 1, payload["audit"]
    row = row[0]
    row["sprites"] = ["output/not_in_this_tree.png"]
    if by_product:
        row["by_product"] = True
    else:
        row.pop("by_product", None)
    row.pop("exempt", None)
    payload["audit"] = [row]
    for entry in payload["scenes"]:
        if entry["id"] == row["scene"]:
            entry["gate"] = gate
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return root


def test_a_by_product_row_with_no_file_reports_not_measured_instead_of_exiting(tmp_path, capsys):
    """Card t_c93a983f: output/sprites_v2_sheet.png is gitignored, and refusing on it cost three Pine jobs.

    A by-product is a diagnostic no clean checkout reproduces, so the row reports NOT MEASURED with a printed
    line (ruling section 8) rather than SystemExit for the whole gate, and it never gates the build.
    """
    root = by_product_root(tmp_path)
    results, blocked, advisory = palette_synergy.gate(root)
    assert len(results) == 1, results
    assert results[0]["measured"] is False, results[0]
    assert results[0]["by_product"] is True, results[0]
    assert results[0]["gated"] is False, results[0]
    assert results[0]["skipped"] == ["output/bg_battle_corridor_frame.png", "output/not_in_this_tree.png"], results[0]
    assert blocked == [] and advisory == [], (blocked, advisory)

    code = palette_synergy.main(["--gate", "--root", root])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "NOT MEASURED" in out, out
    assert "not_in_this_tree.png" in out, out
    report = json.load(open(os.path.join(root, "output", "palette_synergy.json"), encoding="utf-8"))
    assert report["results"][0]["measured"] is False, report["results"][0]
    assert report["results"][0]["by_product"] is True, report["results"][0]


def test_a_by_product_row_that_is_present_is_measured_and_advisory(tmp_path):
    """Whatever it measures, a by-product is advice: it is a contact sheet, not a cast ruling."""
    root = by_product_root(tmp_path)
    path = os.path.join(root, "data", "scene_palettes.json")
    payload = json.load(open(path, encoding="utf-8"))
    payload["audit"][0]["sprites"] = [os.path.join(ROOT, "game", "sprites_src", "chars", "percy_battle.png")]
    payload["audit"][0]["background"] = os.path.join(ROOT, "output", "bg_battle_corridor_frame.png")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    results, blocked, advisory = palette_synergy.gate(root)
    result = results[0]
    assert result["measured"] is True and result["by_product"] is True, result
    assert result["gated"] is False, "a by-product must not gate the build whatever it measures"
    assert blocked == [], blocked
    assert result["fail_count"] == len(result["problems"]), result


def test_the_pair_table_covers_every_sprite_palette(tmp_path):
    result = analyse(tmp_path, {}, {(x, y): COLOURS[0x20] for x in range(16) for y in range(16)})
    frame = result["sprites"][0]["frames"][0]
    assert [pair["sprite_palette"] for pair in frame["pairs"]] == [0, 1, 2, 3]
    for pair in frame["pairs"]:
        assert set(pair) >= {"sprite_palette", "body", "ground", "rows_apart", "contrast", "ok", "fails"}


def test_a_24x32_battle_figure_is_judged_as_a_figure(tmp_path):
    """Card t_c498add9: a 24x32 or 32x32 battle figure is a FIGURE, not a tiled layer.

    The same pixels are judged twice below, once undeclared and once declared a layer. Stone $00 on the $02 night
    is row 0 on row 0 at 2.91:1, so both of R1's instruments are short and it refuses; as a layer it would be
    refused by R1b instead (body 2.91:1, ink 1.73:1 against the same ground). So the rule NAME the tool reports is
    the whole proof of which branch it took.
    """
    pixels = {}
    for y in range(32):
        for x in range(24):
            pixels[(x, y)] = COLOURS[0x00] if (x + y) % 3 else COLOURS[0x0F]
    result = analyse(tmp_path, {}, pixels, size=(24, 32), background=COLOURS[0x02])
    sprite = result["sprites"][0]
    assert sprite["frame"] == [24, 32], sprite["frame"]
    assert sprite["figure"] is True and sprite["declared_layer"] is False, sprite
    assert sprite["frames"][0]["layer"] is False
    assert "body_ground" in rules_of(result), result["problems"]
    assert "overlay_contrast" not in rules_of(result), result["problems"]


def test_a_sheet_that_declares_itself_a_layer_is_judged_as_a_layer(tmp_path):
    """The declaration outranks the size: the same 24x32 pixels with "layer": true get R1b, not R1."""
    pixels = {}
    for y in range(32):
        for x in range(24):
            pixels[(x, y)] = COLOURS[0x00] if (x + y) % 3 else COLOURS[0x0F]
    result = analyse(tmp_path, {}, pixels, size=(24, 32), background=COLOURS[0x02],
                     sidecar={"frame_w": 24, "frame_h": 32, "frames": 1, "layer": True})
    sprite = result["sprites"][0]
    assert sprite["declared_layer"] is True and sprite["figure"] is False, sprite
    assert sprite["frames"][0]["layer"] is True
    assert "body_ground" not in rules_of(result), result["problems"]
    assert "overlay_contrast" in rules_of(result), result["problems"]


def test_r6_for_a_multi_tile_figure_is_asked_per_8x8_tile(tmp_path):
    """Every 8x8 tile of a figure must fit one sprite palette of the scene, and an uncovered tile is named."""
    pixels = {}
    for top in range(0, 32, 8):
        for left in range(0, 24, 8):
            pair = (0x0F, 0x0C) if (left, top) == (16, 8) else (0x0F, 0x00)
            for y in range(top, top + 8):
                for x in range(left, left + 8):
                    pixels[(x, y)] = COLOURS[pair[(x + y) % 2]]
    result = analyse(tmp_path, {}, pixels, size=(24, 32),
                     sidecar={"frame_w": 24, "frame_h": 32, "frames": 1})
    sprite = result["sprites"][0]
    assert sprite["tiles"] == {"inked": 12, "uncovered": 1}, sprite["tiles"]
    palette_count = [problem for problem in result["problems"] if problem["rule"] == "palette_count"]
    assert len(palette_count) == 1, palette_count
    assert palette_count[0]["tile"] == [16, 8], palette_count[0]
    assert palette_count[0]["colours"] == "$0C $0F", palette_count[0]
    assert "set_member" not in rules_of(result), result["problems"]


def test_cli_writes_a_json_report_and_sets_the_exit_code(tmp_path):
    # $00 grey on the $11 ground at the same luminance: one row apart at 1.00:1, refused by both instruments.
    sprite = write_png(tmp_path / "spr.png", {(x, y): COLOURS[0x00] for x in range(16) for y in range(16)})
    background = write_png(tmp_path / "bg.png", {}, size=(256, 240), background=COLOURS[0x11])
    out = tmp_path / "report.json"
    code = palette_synergy.main(["--scene", "title", "--background", str(background),
                                 "--sprite", str(sprite), "--json", str(out), "--quiet"])
    assert code == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["tool"] == "palette_synergy"
    assert payload["scene"] == "title"
    assert payload["ok"] is False
    assert payload["fail_count"] >= 1


def test_cli_passes_a_clean_sprite(tmp_path):
    sprite = write_png(tmp_path / "spr.png", {(x, y): COLOURS[0x20] for x in range(16) for y in range(16)})
    background = write_png(tmp_path / "bg.png", {}, size=(256, 240), background=BLACK)
    code = palette_synergy.main(["--scene", "title", "--background", str(background),
                                 "--sprite", str(sprite), "--quiet"])
    assert code == 0


@pytest.mark.parametrize("frame", ["output/nes_title_frame.png"])
def test_the_shipped_title_frame_reports_its_pairs(frame):
    """Not an assertion that it passes: it fails today, and that failing list is what the card asked for. What is
    pinned is that the tool runs on the real frame and produces the pair table instead of crashing."""
    path = os.path.join(ROOT, frame)
    # No skip here. A skip on a missing input is how this test reported healthy while it measured
    # nothing, and tests/test_test_inputs.py exists to forbid it; the frame is committed instead.
    assert os.path.isfile(path), (
        "%s is not on disk; it is committed, so a checkout without it is a broken checkout "
        "(regenerate with tools/art/scene_palette.py)" % frame)
    result = palette_synergy.analyse(ROOT, "title", path, ["game/sprites_src/chars/percy_ow_v2.png"])
    assert result["sprites"], "no sprite was measured"
    assert result["sprites"][0]["frames"], "no frame was measured"
    assert result["fail_count"] == len(result["problems"])
    assert result["exit_code"] == (0 if result["ok"] else 1)



def test_the_two_ruled_grounds_measure_clean_today():
    """Card t_1dc346b9, 2026-10-25, the pair column of the two rulings, pinned.

    The cloud is judged as a sky-band layer (sidecar declares "layer": true) on
    output/cloud_sky_ground.png: R1b, 0 failing pairs, 0 uncovered tiles. The walking sailor and his
    battle twin are judged as ship cast on the ship tileset: figures, 0 failing pairs, 0 uncovered.
    Both were FAIL on the stale readings the queue rows carried (6 pairs for the cloud under cf3d43a's
    figure reading; 16 pairs on the sailor once the deck's palettes were re-solved for the fight cast),
    and both were the reason this card exists: the rows may not claim a ground a tool cannot measure.
    """
    cloud = palette_synergy.analyse(ROOT, "title", "output/cloud_sky_ground.png",
                                    ["game/sprites_src/title/spr_title_cloud.png"],
                                    frame_w=24, frame_h=16, at=(0, 0))
    assert cloud["ok"], cloud["problems"]
    csheet = cloud["sprites"][0]
    assert len(csheet["frames"]) == 3
    for frame in csheet["frames"]:
        assert frame["layer"] is True, frame
    assert csheet["tiles"]["uncovered"] == 0, csheet["tiles"]

    for sheet in ["game/sprites_src/chars/hadrian_ow_v2.png",
                  "game/sprites_src/chars/konrad_ow_v2.png",
                  "game/sprites_src/chars/zander_ow_v2.png",
                  "game/sprites_src/chars/percy_ow_v2.png",
                  "game/sprites_src/chars/sailor_ow_v2.png"]:
        result = palette_synergy.analyse(ROOT, "ship", "game/sprites_src/env/ts_ship.png",
                                         [sheet], at=(64, 64))
        assert result["ok"], (sheet, result["problems"])
        assert result["sprites"][0]["tiles"]["uncovered"] == 0, sheet



def test_a_party_cast_strip_reads_the_hero_four_as_its_sprite_palettes():
    """Card t_6e8ca42f: the tool reads the room, not the declaration, on the four battle strips.

    On a battle strip the four RESERVED HERO PALETTES are the strip's four sprite palettes (ruling 7.1,
    card t_c93a983f), so a Scene for one has to be assembled from allowed_sprite_rows() rather than from the
    entry's own rows. Read the other way it measured the repainted party sheets against palettes the strip
    does not spend: percy_battle.png as 73 palette_count failures on the corridor ground, every one of them
    about a triple the chip draws with. And it is not a widening: the row count stays four, and a scene
    without the flag still reads its own rows, which is what the ship and the title below check.
    """
    data = scene_palette_set.load(ROOT)
    heroes = [list(map(int, scene_palette_set.hero(data, name)["colours"]))
              for name in scene_palette_set.HEROES]
    for scene_id in scene_palette_set.PARTY_CAST_SCENES:
        assert scene_palette_set.find_scene(data, scene_id).get("party_cast") is True, scene_id
        scene = scene_palette_set.scene(ROOT, scene_id)
        assert scene.sprites == heroes, scene_id
        assert [sorted(row) for row in scene.sprite_sets()] == [sorted(row) for row in heroes], scene_id
        assert len(scene.sprites) == 4, "a strip has four sprite palettes, not eight: %s" % scene_id
    for scene_id in ("ship", "title"):
        entry = scene_palette_set.find_scene(data, scene_id)
        scene = scene_palette_set.scene(ROOT, scene_id)
        assert scene.sprites == [list(map(int, row["colours"])) for row in entry["sprites"]], scene_id


def test_the_corridor_ground_carries_the_party_four_sheets():
    """The measured half of card t_6e8ca42f, on the shipped art, one sheet at a time.

    `--scene battle_corridor --background output/bg_battle_corridor_frame.png --frame-w 24 --frame-h 32`:
    before the tool read the strip's four, percy_battle.png measured 73 failing pairs (all palette_count)
    and hadrian_battle.png 86 (72 palette_count, 14 set_member on $03 and $23). Both are one reserved hero
    triple each since card t_d5483a88, so on the ground they are drawn over they have to measure clean:
    0 fails, 0 uncovered tiles, 7 frames of 24x32.
    """
    for name in scene_palette_set.HEROES:
        sheet = "game/sprites_src/chars/%s_battle.png" % name
        result = palette_synergy.analyse(ROOT, "battle_corridor", "output/bg_battle_corridor_frame.png",
                                         [sheet], frame_w=24, frame_h=32)
        assert result["ok"], (sheet, [(problem["rule"], problem["detail"]) for problem in result["problems"]][:4])
        sprite = result["sprites"][0]
        assert sprite["frame"] == [24, 32], sheet
        assert len(sprite["frames"]) == 7, sheet
        assert sprite["tiles"]["uncovered"] == 0, (sheet, sprite["tiles"])
        assert sprite["tiles"]["inked"] >= 72, (sheet, sprite["tiles"])
