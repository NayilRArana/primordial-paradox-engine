#!/usr/bin/env python3
"""Pins for the battle screen's actors (card t_4275136f).

The ruling on card t_34b1d96a (knowledge/PALETTE-RULINGS-2026-10-25.md section 15) made the deck's tutorial enemy
drawable in palette terms and said so in numbers. Nothing drew it, and nothing drew the strip or the party either,
so a fight on the deck showed a blank field. Card t_4275136f draws all three. These tests hold down what the
drawing is allowed to disagree with, in four groups:

  1. GEOMETRY IS THE LAYOUT'S. The enemy slot and the four party slots are read from data/ui_layouts.json, and
     every number in pp_battle_director.gml is compared with that file. A layout edit this screen does not follow
     fails here instead of drawing the party a tile off its own block.
  2. THE CAST IS THE RESERVED FOUR. The four sheet ids in the slot table are exactly the four heroes
     data/scene_palettes.json reserves a palette for, and each sheet's sidecar is the 24x32 seven frame strip the
     slots are sized for.
  3. THE ART REACHES THE BUILD. tools/sync_art.py mirrors the strips and the enemy sheets, the index it writes
     carries them at the right sizes, tools/check_build_inputs.py names the same folders so the new Included Files
     resolve to a committed source, and the committed project lists them.
  4. THE DRAW ORDER AND THE PALETTE ARGUMENT. The field, then the enemy, then the party; the enemy is drawn from
     its own sheet with no tint, which is the whole of "background art" that a draw call can carry; and the two
     pre art placeholder rectangles are gone.

No em dash or en dash anywhere in this file: the project refuses them at the door (tests/test_project.py).

Run: python -m pytest tests/test_battle_draw.py -q
"""

from __future__ import annotations

import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import sync_art  # noqa: E402  the mirror rules themselves, never a copy of them

DIRECTOR = os.path.join(ROOT, "game", "scripts", "pp_battle_director", "pp_battle_director.gml")
LAYOUT = os.path.join(ROOT, "data", "ui_layouts.json")
SCENE_PALETTES = os.path.join(ROOT, "data", "scene_palettes.json")
CHARS = os.path.join(ROOT, "game", "sprites_src", "chars")
YPP = os.path.join(ROOT, "game", "PrimordialParadox.yyp")

# The four strips and the seven enemy sheets this card mirrors. Written out because a count of 11 is the number the
# card's own index prose uses, and a folder that quietly gains or loses a sheet should change this list on purpose.
STRIPS = ("bg_battle_corridor", "bg_battle_deck_night", "bg_battle_quay_dusk", "bg_battle_wardroom")
ENEMIES = ("bilge_slime", "deck_rat", "gull", "navy_sailor", "petty_officer", "rogue_wave", "rope_knot")


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def load(path: str) -> dict:
    return json.loads(read(path))


def body(name: str) -> str:
    """One GML function's body, from its `function name(` to the closing brace at the start of a line.

    Every function in this project ends its top level brace at column 0, which is what makes this a safe read: a
    nested block always closes indented.
    """
    text = read(DIRECTOR)
    start = text.find("function %s(" % name)
    assert start >= 0, "%s is not in pp_battle_director.gml" % name
    end = text.find("\n}", start)
    assert end > start, "%s has no top level closing brace" % name
    return text[start:end]


def battle_screen() -> dict:
    for screen in load(LAYOUT)["screens"]:
        if screen["name"] == "battle":
            return screen
    raise AssertionError("data/ui_layouts.json has no battle screen")


def resolved_party() -> list:
    """The party slots as the director resolves them: the layout's tile rect times 8, the size its `pixels` states,
    and the member name lowered, which is the sheet's stem."""
    out = []
    for row in battle_screen()["party"]:
        w, h = (int(part) for part in row["pixels"].split("x"))
        out.append({"id": row["member"].lower(), "x": row["x"] * 8, "y": row["y"] * 8, "w": w, "h": h})
    return out


def resolved_enemy() -> dict:
    """The enemy slot as the director resolves it, from the layout's first `enemies` row."""
    row = battle_screen()["enemies"][0]
    w, h = (int(part) for part in row["pixels"].split("x"))
    return {"x": row["x"] * 8, "y": row["y"] * 8, "w": w, "h": h}


def index_entries() -> dict:
    return {entry["name"]: entry for entry in sync_art.source_entries()}


# ---- 1. Geometry is the layout's, read at run time ---------------------------------------------------------------


def test_the_director_reads_the_battle_screen_out_of_the_layout_file():
    """The slots come from data/ui_layouts.json at run time, so no rect and no hero name is restated in the GML.

    tests/test_enemy_phases.py and tests/test_prometheus_interrupt.py refuse an enemy name in this file; the same
    argument applies to a hero name, and the table that used to hold four of them is what this test replaced.
    """
    reader = body("pp_battle_layout")
    assert 'variable_struct_exists(global.pp_data, "ui_layouts")' in reader
    assert '== "battle"' in reader, "the reader does not find the battle screen by name"
    party = body("pp_battle_party_slots")
    assert "_screen.party" in party and "* 8" in party, "the party column is not the layout's tiles times 8"
    assert "string_lower(string(_row.member))" in party, "the sheet id is not the layout's member name lowered"
    enemy = body("pp_battle_enemy_slot")
    assert "_screen.enemies" in enemy and "* 8" in enemy, "the enemy slot is not the layout's first enemy row"
    assert "pp_battle_pixels(_row.pixels)" in enemy, "the enemy slot size is not the row's own pixels string"
    code = read(DIRECTOR)
    assert "pp_battle_enemy_x" not in code, "the enemy slot is still a constant in the director"
    assert "x: 224, y:" not in code, "the party column is still a table in the director"
    for hero in load(SCENE_PALETTES)["hero_palettes"]:
        assert hero not in code.lower(), "%r is named in the director, which is a table in code" % hero


def test_the_enemy_slot_is_the_layout_files_own_first_slot():
    """Tile 3,8 at 32x32 in data/ui_layouts.json is pixel 24,64 in the director, and no rounding is involved."""
    slot = battle_screen()["enemies"][0]
    numbers = resolved_enemy()
    assert numbers["x"] == slot["x"] * 8 == 24
    assert numbers["y"] == slot["y"] * 8 == 64
    assert numbers["w"] == slot["w"] * 8 == 32
    assert numbers["h"] == slot["h"] * 8 == 32
    assert slot["pixels"] == "32x32"


def test_the_party_column_is_the_layout_files_own_four_members():
    """x=224, y=32/64/96/128, 24x32 each, in the layout's own member order, which is the order it draws in."""
    rows = battle_screen()["party"]
    slots = resolved_party()
    assert len(rows) == len(slots) == 4
    for layout_row, slot in zip(rows, slots):
        assert slot["id"] == layout_row["member"].lower(), "the slot order is not the layout's order"
        assert slot["x"] == layout_row["x"] * 8 == 224
        assert slot["y"] == layout_row["y"] * 8
        assert slot["w"] == layout_row["w"] * 8 == 24
        assert slot["h"] == layout_row["h"] * 8 == 32
    assert [slot["y"] for slot in slots] == [32, 64, 96, 128]


def test_the_party_block_stays_inside_the_frame_and_clear_of_the_band():
    """The column is 24 px at x 224, so it ends at 247 of 256, and its lowest slot ends on row 159, above 168."""
    for slot in resolved_party():
        assert slot["x"] + slot["w"] <= 256
        assert slot["y"] + slot["h"] <= 168, "a party slot reaches into the command band"


# ---- 2. The cast is the reserved four ----------------------------------------------------------------------------


def test_the_four_sheets_are_the_four_heroes_that_hold_a_reserved_palette():
    """data/scene_palettes.json reserves one triple for each of four heroes, and those four are what is drawn."""
    reserved = load(SCENE_PALETTES)["hero_palettes"]
    drawn = [slot["id"] for slot in resolved_party()]
    assert sorted(drawn) == sorted(reserved), "the battle block draws a hero the palette file does not reserve"


@pytest.mark.parametrize("hero", ["konrad", "zander", "percy", "hadrian"])
def test_each_party_sheet_is_the_24x32_seven_frame_strip_the_slot_is_sized_for(hero):
    sidecar = load(os.path.join(CHARS, "%s_battle.json" % hero))
    slot = [row for row in resolved_party() if row["id"] == hero]
    assert slot, "the layout's party column does not name %r" % hero
    assert sidecar["frame_w"] == slot[0]["w"] == 24
    assert sidecar["frame_h"] == slot[0]["h"] == 32
    assert sidecar["frames"] == 7, "the idle pair and the hit frame are the sheet's own seven frames"
    assert os.path.isfile(os.path.join(CHARS, "%s_battle.png" % hero))


def test_the_enemy_sheet_name_is_the_enemy_row_id():
    """No table maps an enemy to a file, so the lookup is the id, and this is the id the tutorial fight names."""
    encounters = load(os.path.join(ROOT, "data", "encounters", "all.json"))
    tutorial = [row for row in encounters["encounters"] if row["id"] == "tutorial_sailors"]
    assert tutorial, "data/encounters/all.json has no tutorial_sailors row"
    enemy_id = tutorial[0]["enemies"][0]
    assert enemy_id == "navy_sailor"
    sidecar = load(os.path.join(ROOT, "game", "sprites_src", "enemies", "%s.json" % enemy_id))
    slot = resolved_enemy()
    assert (sidecar["frame_w"], sidecar["frame_h"]) == (slot["w"], slot["h"]), \
        "the enemy's sheet is not the size the layout's slot states"
    assert 'var _name = string(_battle.enemy.id);' in body("pp_battle_enemy_sprite"), \
        "the enemy sheet is no longer looked up by the enemy row's own id"


# ---- 3. The art reaches the build --------------------------------------------------------------------------------


def test_the_mirror_reads_the_strip_folder_and_the_enemy_folder():
    folders = [os.path.abspath(folder) for folder in sync_art._folders()]
    assert os.path.abspath(sync_art.BG_SRC) in folders
    assert os.path.abspath(sync_art.ENEMY_SRC) in folders


@pytest.mark.parametrize("name", STRIPS)
def test_each_strip_is_indexed_as_one_256x112_picture(name):
    entry = index_entries().get(name)
    assert entry, "%s is not in the art index, so pp_battle_draw_field draws no strip" % name
    assert (entry["frame_w"], entry["frame_h"], entry["frames"]) == (256, 112, 1)
    assert entry["kind"] == "background"


@pytest.mark.parametrize("name", ENEMIES)
def test_each_enemy_sheet_is_indexed_at_its_own_frame_size(name):
    entry = index_entries().get(name)
    assert entry, "%s is not in the art index, so its fight draws a block" % name
    sidecar = load(os.path.join(ROOT, "game", "sprites_src", "enemies", "%s.json" % name))
    assert (entry["frame_w"], entry["frame_h"]) == (sidecar["frame_w"], sidecar["frame_h"])
    assert entry["frames"] == sidecar["frames"]


def test_the_build_input_checker_names_every_folder_the_mirror_reads():
    """A folder tools/sync_art.py mirrors and tools/check_build_inputs.py does not name reads as a file with no
    committed source behind it, so the two lists are held together here rather than by memory."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pp_check_build_inputs", os.path.join(TOOLS, "check_build_inputs.py"))
    assert spec is not None and spec.loader is not None, "cannot load tools/check_build_inputs.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    named = [os.path.abspath(folder) for folder in module.ART_SOURCES]
    for folder in sync_art._folders():
        assert os.path.abspath(folder) in named, "%s is mirrored but not named in check_build_inputs.ART_SOURCES" % folder


def test_the_committed_project_lists_the_new_art():
    """The .yyp is what ships the art as Included Files, so a mirror run that lands art without the project is a
    build with the sheets on disk and not in the game (the FIX-YYP cards are why sync_art rewrites it)."""
    text = read(YPP)
    for name in list(STRIPS) + list(ENEMIES):
        assert '"name": "%s.png"' % name in text, "%s.png is not an Included File of the project" % name


# ---- 4. The draw order and the palette argument ------------------------------------------------------------------


def test_the_field_draws_before_the_actors_and_the_enemy_before_the_party():
    """Draw order is the whole reason the enemy is background art: the strip first, the enemy onto it, then the
    party's sprites over the column. A later card that reorders these three changes what the frame means."""
    draw = body("pp_battle_draw")
    field = draw.find("pp_battle_draw_field(_battle)")
    enemy = draw.find("pp_battle_draw_enemy(_battle, _enemy_slot)")
    party = draw.find("pp_battle_draw_party(_battle)")
    assert -1 not in (field, enemy, party), "one of the three draws is not called from pp_battle_draw"
    assert field < enemy < party


def test_the_pre_art_placeholder_rectangles_are_gone():
    """A hero block at 40,96 and an enemy block at 176,72 were what the screen drew before there was art. Left in
    place beside the real draws they would read as a second enemy, so they are removed, not kept as a fallback."""
    draw = body("pp_battle_draw")
    assert "draw_rectangle(40, 96, 72, 144, false)" not in draw
    assert "draw_rectangle(176, 72, 224, 136, false)" not in draw


def test_the_enemy_is_drawn_untinted_from_the_index_at_its_own_slot():
    """Background art, stated as the only thing a draw call can state: the sheet is drawn exactly as authored, at
    the enemy's slot, so no sprite palette is spent on it (ruling 7.5)."""
    enemy = body("pp_battle_draw_enemy")
    calls = re.findall(r"pp_art_draw\(([^;]*)\);", enemy)
    assert len(calls) == 1, "pp_battle_draw_enemy makes %d art draws, not one" % len(calls)
    assert "PP_UNTINTED" in calls[0], "the enemy's sheet is tinted, which spends a sprite palette on it"
    assert "_slot.x" in calls[0] and "_slot.y" in calls[0], "the enemy is not drawn at its own layout slot"
    assert "draw_sprite_ext" not in enemy and "image_blend" not in enemy


def test_the_party_draw_skips_a_missing_sheet_and_says_how_many_it_drew():
    party = body("pp_battle_draw_party")
    assert "if (!pp_art_has(_name)) continue;" in party, "a missing party sheet must skip, not empty the block"
    assert "_drawn += 1;" in party and "return _drawn;" in party


def test_the_strip_missing_line_no_longer_blames_the_mirror():
    """The line said sync_art does not read the strip folder, which stops being true on this card, so the message
    that is left has to be about the build rather than about a tool that now mirrors it."""
    field = body("pp_battle_draw_field")
    assert "does not read game" not in field
    assert "not in the art index" in field
