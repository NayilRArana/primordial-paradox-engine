"""Tests for tools/scene_palette_set.py (card PAL-SYSTEM, 2026-10-22).

Why this file exists: ART-BIBLE RULE 0 makes a scene's palette set an input to the art, not a report on it.
That only holds if the file is real, complete for every scene, and derived from the per scene files that the
art lane already solved. The strongest test here is the regeneration test: `build()` must reproduce the file
that is on disk byte for byte, so a hand edit that drifts from the measured art fails the suite.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "art"))

import scene_palette_set  # noqa: E402


def data():
    return scene_palette_set.load(ROOT)


def test_file_is_there_and_is_the_right_kind():
    payload = data()
    assert payload["kind"] == "scene_palettes"
    assert payload["format"] == 1
    assert payload["master"] == "data/nes_palette.json"


def test_every_scene_file_the_art_lane_solved_is_in_the_set():
    listed = set(scene_palette_set.scene_ids(data()))
    on_disk = {os.path.basename(path)[len("scene_"):-len(".json")]
               for path in scene_palette_set.source_files(ROOT)}
    assert on_disk <= listed, "a scene file on disk is not in the palette set"
    assert len(listed) == len(on_disk)


def test_every_scene_is_one_backdrop_four_plus_four_of_three():
    colours, usable, _ = scene_palette_set.load_master(ROOT)
    for entry in data()["scenes"]:
        assert usable[entry["backdrop"]], entry["id"]
        assert 0 <= entry["backdrop"] < len(colours)
        for key in ("background", "sprites"):
            rows = entry[key]
            assert len(rows) == 4, "%s has %d %s palettes" % (entry["id"], len(rows), key)
            for row in rows:
                assert len(row["colours"]) == 3, (entry["id"], key, row)
                assert len(set(row["colours"])) == 3, (entry["id"], key, row)
                for value in row["colours"]:
                    assert usable[value], "%s uses forbidden entry $%02X" % (entry["id"], value)


def test_the_four_hero_palettes_are_fixed_and_dark_to_light():
    payload = data()
    assert sorted(payload["hero_palettes"]) == sorted(scene_palette_set.HEROES)
    for name, palette in payload["hero_palettes"].items():
        entries = palette["colours"]
        assert palette["fixed"] is True, name
        assert len(entries) == 3 and len(set(entries)) == 3, name
        rows = [scene_palette_set.row_of(value) for value in entries]
        assert rows == sorted(rows), "%s is not outline, body, accent: %s" % (name, rows)
    # RULE 0 point 3 names the colours in words; the entries are what the tools read.
    assert payload["hero_palettes"]["percy"]["colours"] == [15, 18, 40]
    assert payload["hero_palettes"]["hadrian"]["colours"] == [15, 3, 35]
    assert payload["hero_palettes"]["zander"]["colours"] == [15, 33, 49]
    assert payload["hero_palettes"]["konrad"]["colours"] == [15, 0, 39]


def test_a_scene_can_be_loaded_as_the_art_lanes_own_scene_object():
    scene = scene_palette_set.scene(ROOT, "title")
    assert scene.name == "title"
    assert len(scene.background) == 4 and len(scene.sprites) == 4
    assert len(scene.bg_sets()[0]) == 4  # three entries plus the shared backdrop
    assert scene.rgb(scene.backdrop) == (0, 0, 0)


def test_every_entry_of_the_set_is_a_usable_master_entry():
    payload = data()
    entries = scene_palette_set.scene_entries(payload, "title")
    _, usable, _ = scene_palette_set.load_master(ROOT)
    assert entries, "title has no entries"
    for entry in entries:
        assert usable[entry], "$%02X is not usable" % entry


def test_validate_passes_on_the_shipped_file():
    assert scene_palette_set.validate(ROOT) == []


def test_validate_catches_a_broken_scene():
    payload = json.loads(json.dumps(data()))
    payload["scenes"][0]["background"] = payload["scenes"][0]["background"][:3]
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("background palettes" in problem for problem in problems), problems

    payload = json.loads(json.dumps(data()))
    payload["hero_palettes"]["percy"]["colours"] = [15, 18]
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("percy" in problem for problem in problems), problems

    payload = json.loads(json.dumps(data()))
    payload["scenes"][0]["backdrop"] = 13  # $0D, the entry the art bible forbids
    problems = scene_palette_set.validate(ROOT, payload)
    assert any("forbidden" in problem for problem in problems), problems


def test_build_reproduces_the_file_on_disk():
    """The file must be derived, not hand written: a regeneration either changes nothing or the art changed."""
    rebuilt = json.loads(json.dumps(scene_palette_set.build(ROOT)))
    shipped = data()
    assert rebuilt["scenes"] == shipped["scenes"]
    assert rebuilt["hero_palettes"] == shipped["hero_palettes"]
    assert rebuilt["rule"] == shipped["rule"]
    # The audit rows are derived too. They were a constant in tools/scene_palette_set.py until card t_4f18c0ac,
    # and that is how the deck's row kept naming the walking sailor after the deck's palettes were re-solved for
    # the fight cast: two files, no comparison. Now the rows live in data/palettes/scene_*.json, so a hand edit to
    # data/scene_palettes.json is a drift the rebuild test catches.
    assert rebuilt["audit"] == shipped["audit"]


# -----------------------------------------------------------------------------------------------------------------
# The cast check (card t_4f18c0ac). An audit row may only name sheets the scene's four sprite palettes can carry.

def judged_rows():
    return scene_palette_set.judged_rows(ROOT)


def test_every_judged_row_lives_in_a_scene_file_and_names_a_frame_and_a_cast():
    rows = judged_rows()
    assert rows, "no scene file carries a judged row"
    scene_ids = set(scene_palette_set.scene_ids(data()))
    for row in rows:
        assert row["scene"] in scene_ids, row["scene"]
        assert row["background"], row
        assert row["sprites"], row


def test_the_deck_audit_row_names_the_fight_cast_and_not_the_walking_sailor():
    """The row corrected on 2026-10-24: the deck's four palettes were solved for sailor_battle + navy_sailor."""
    deck = [row for row in judged_rows() if row["scene"] == "battle_deck_night"]
    assert len(deck) == 1, deck
    sprites = [os.path.basename(path) for path in deck[0]["sprites"]]
    assert "sailor_battle.png" in sprites
    assert "navy_sailor.png" in sprites
    assert "sailor_ow_v2.png" not in sprites, "the walking sailor has no deck palette and is judged on the ship"


def test_the_cast_check_catches_the_row_that_was_stale():
    """The mutation this check exists for: the old row, put back, is refused with the $12 the draw lane measured."""
    broken = json.loads(json.dumps(data()))
    for row in broken["audit"]:
        if row["scene"] == "battle_deck_night":
            row["sprites"] = ["game/sprites_src/chars/sailor_battle.png",
                              "game/sprites_src/chars/sailor_ow_v2.png"]
    problems = scene_palette_set.cast_problems(ROOT, broken)
    assert len(problems) == 1, problems
    assert "battle_deck_night" in problems[0]
    assert "sailor_ow_v2.png" in problems[0]
    assert "$12" in problems[0]
    # And it is part of validate, so the suite fails on it rather than only this function.
    assert any("sailor_ow_v2.png" in problem for problem in scene_palette_set.validate(ROOT, broken))


def test_every_judged_row_of_the_shipped_file_has_a_cast_its_scene_can_carry():
    """No exemptions here: the shipped rows that are enforced measure clean, through the tool's own cast reading."""
    assert scene_palette_set.cast_problems(ROOT, data()) == []


def test_the_exempt_rows_are_the_known_two_and_say_why():
    """An exemption is a ruling, not a way to quiet the check, so the exact list is held here."""
    exempt = [row for row in judged_rows() if row.get("exempt")]
    assert [(row["scene"], os.path.basename(row["sprites"][0])) for row in exempt] == [
        ("battle_corridor", "percy_battle.png"),
        ("battle_corridor", "sprites_v2_sheet.png"),
    ], exempt
    for row in exempt:
        assert len(row["exempt"]) > 80, "an exemption has to say why, in words: %s" % row["exempt"]


def test_a_judged_row_may_not_be_exempt_without_a_reason():
    broken = json.loads(json.dumps(data()))
    for row in broken["audit"]:
        if row.get("exempt"):
            row["exempt"] = " "
            break
    problems = scene_palette_set.validate(ROOT, broken)
    assert any("exempt with no reason" in problem for problem in problems), problems


def test_the_quay_strip_has_no_judged_row_because_nothing_in_play_draws_it():
    """Ruling on card t_4f18c0ac: no encounter names battle_quay_dusk and no room set maps to it."""
    assert not [row for row in judged_rows() if row["scene"] == "battle_quay_dusk"]
    assert "battle_quay_dusk" in scene_palette_set.scene_ids(data()), "the set still exists; only its row is absent"


def test_cli_validate_and_list(capsys):
    assert scene_palette_set.main(["validate"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert scene_palette_set.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "title" in out and "ship" in out


def test_cli_show_names_the_palettes(capsys):
    assert scene_palette_set.main(["show", "--scene", "title"]) == 0
    out = capsys.readouterr().out
    assert "$0F" in out and "percy" in out


def test_the_ship_judged_row_names_the_tileset_and_not_the_capture():
    """Card t_1dc346b9 ruling 2026-10-25: a ground has to be something a tool can measure.

    output/ship_dialogue.png is a composed capture carrying colours off the 2C02 palette, and
    palette_synergy charges the capture's own background_area and set_member failures to whatever
    sprite stands on it, so it cannot be evidence about the ship cast. The ship tileset is authored
    inside the scene's own background palettes, so the pair column measures only the sprite.
    """
    ship = [row for row in judged_rows() if row["scene"] == "ship"
            and "ts_ship.png" in row["background"]]
    assert len(ship) == 1, ship
    row = ship[0]
    sprites = [os.path.basename(path) for path in row["sprites"]]
    assert "sailor_ow_v2.png" in sprites and "sailor_battle.png" in sprites, sprites
    assert row["at"] == [64, 64], row
    assert not [r for r in judged_rows()
                if r["scene"] == "ship" and "ship_dialogue" in r["background"]], (
        "no ship judged row may name the capture as its ground (t_1dc346b9)")


def test_the_cloud_declares_itself_a_layer_in_its_sidecar_and_in_its_generator():
    """Card t_1dc346b9 ruling: the cloud hangs in the sky band over the strip's own cloud tops, so it is
    judged by R1b overlay_contrast, not by the figure tests. cf3d43a made a 24x16 frame a figure, and the
    white crown then read white_blob on the 5 white pixels of its own sky crop: scenery meeting scenery.
    The declaration lives in the sidecar AND in save_strip, so a regeneration cannot lose it.
    """
    sidecar = json.load(open(os.path.join(ROOT, "game", "sprites_src", "title",
                                          "spr_title_cloud.json"), encoding="utf-8"))
    assert sidecar.get("layer") is True, sidecar
    gen = open(os.path.join(ROOT, "tools", "art", "make_title_car.py"),
               encoding="utf-8").read()
    assert 'meta["layer"] = True' in gen, "the generator stopped owning the declaration"
