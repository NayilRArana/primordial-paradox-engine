"""Tests for the 8 bit look: a 16 colour room cap, an append only master palette, and no colour literal in draw code.

Why a test and not a review note: every one of these rules is a claim that would rot silently. A room palette may grow a
seventeenth colour in a data edit and nothing would fail on a machine with no GameMaker; a master colour may be edited in
place and every sprite indexed after it would shift with no error; a draw call may reach for a named colour and look
right until the palette moves. So each rule is broken on purpose in a private copy of data\\ and the checker must say so
by file and by field, and the sweep over our own GML must fail on a planted colour literal as well as on the real code.
"""

from __future__ import annotations

import os
import re

import check_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The numbers spec 13 and spec 03 decide. They are repeated here on purpose: this file is the pin, so a change to one of
# them has to be made in two places and cannot arrive by accident.
SCREEN_CAP = 16
MASTER_SIZE = 54
BASE_W, BASE_H = 256, 240
MAX_SCALE = 6

# A draw call, in code rather than in a comment. The sweep only judges files that actually draw.
DRAW_CALL = re.compile(r"\bdraw_[a-z0-9_]+\s*\(")
# A colour the code chose rather than looked up: a GameMaker colour name, or a colour built from numbers.
COLOUR_LITERAL = re.compile(r"\bc_[a-z]+\b|\bmake_colou?r_rgb\s*\(")
# The debug overlay is allowed to name colours: it draws diagnostics in black and white on purpose, and it is not part of
# the screen the player sees (the card's own allowance).
LITERAL_ALLOWLIST = ("game/objects/obj_pp_debug_overlay",)

SEVENTEEN = [
    "grey_0", "grey_1", "grey_2", "grey_3", "grey_4", "grey_5",
    "sea_0", "sea_1", "sea_2", "sea_3", "sea_4", "sea_5",
    "bronze_0", "bronze_1", "bronze_2", "bronze_3", "bronze_4",
]


def failures(root):
    return check_data.check(str(root))


def gml_code_only(text: str) -> str:
    """Strip comments, so a rule is judged on code and a comment that names a colour is not a failure."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//")[0] for line in text.splitlines())


def test_the_pins_agree_with_the_checker():
    assert (check_data.FRAME_W, check_data.FRAME_H) == (BASE_W, BASE_H)
    assert check_data.PALETTE_SIZE == MASTER_SIZE
    assert check_data.MAX_COLOURS_ON_SCREEN == SCREEN_CAP
    assert check_data.PALETTE_LEVELS == 6
    assert len(check_data.PALETTE_FAMILIES) * check_data.PALETTE_LEVELS == MASTER_SIZE


def test_the_look_module_owns_the_numbers_and_the_scale():
    with open(os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml"), "r", encoding="utf-8-sig") as fh:
        config = fh.read()
    assert re.search(r"#macro\s+PP_FRAME_W\s+%d\b" % BASE_W, config)
    assert re.search(r"#macro\s+PP_FRAME_H\s+%d\b" % BASE_H, config)
    assert re.search(r"#macro\s+PP_MAX_SCALE\s+%d\b" % MAX_SCALE, config)

    with open(os.path.join(ROOT, "game", "scripts", "pp_look", "pp_look.gml"), "r", encoding="utf-8-sig") as fh:
        look = gml_code_only(fh.read())
    for name in ("pp_look_init", "pp_look_scale_for", "pp_look_apply_window", "pp_look_scale", "pp_look_update",
                 "pp_look_pixel", "pp_look_palette", "pp_look_role_index", "pp_role_colour"):
        assert re.search(r"function\s+%s\s*\(" % name, look), "%s is not defined in pp_look" % name
    # One implementation of the scale: the camera module asks pp_look instead of carrying a second copy of the maths.
    with open(os.path.join(ROOT, "game", "scripts", "pp_camera", "pp_camera.gml"), "r", encoding="utf-8-sig") as fh:
        camera = gml_code_only(fh.read())
    assert "pp_look_scale_for(" in camera
    assert "floor(_ww / PP_FRAME_W)" not in camera, "pp_camera computes the scale itself again"


def test_role_resolution_is_defined_once():
    counts = {}
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in filenames:
            if not name.endswith(".gml"):
                continue
            with open(os.path.join(dirpath, name), "r", encoding="utf-8-sig") as fh:
                code = gml_code_only(fh.read())
            for match in re.finditer(r"function\s+(pp_[a-z0-9_]+)\s*\(", code):
                counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    assert duplicates == [], "defined in more than one place: %s" % duplicates
    assert "pp_role_colour" in counts and "pp_pattern" not in counts


def test_real_data_passes():
    assert failures(ROOT) == []


def test_seventeen_colours_in_a_room_palette_fails(data_root, read_json, write_json):
    path = data_root / "data" / "room_palettes.json"
    data = read_json(path)
    data["sets"][0]["roles"] = SEVENTEEN
    write_json(path, data)

    errors = failures(data_root)
    assert any("data/room_palettes.json" in e and "sets[0].roles" in e
               and "17 colours" in e and "screen cap is 16" in e for e in errors), errors


def test_sixteen_colours_in_a_room_palette_still_passes(data_root, read_json, write_json):
    path = data_root / "data" / "room_palettes.json"
    data = read_json(path)
    data["sets"][0]["roles"] = SEVENTEEN[:SCREEN_CAP]
    write_json(path, data)

    assert failures(data_root) == []


def test_unknown_role_in_a_room_palette_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "room_palettes.json"
    data = read_json(path)
    data["sets"][1]["roles"][2] = "neon"
    write_json(path, data)

    errors = failures(data_root)
    assert any("data/room_palettes.json" in e and "sets[1].roles[2]" in e and "not a role" in e
               for e in errors), errors


def test_duplicate_room_palette_id_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "room_palettes.json"
    data = read_json(path)
    data["sets"][1]["id"] = data["sets"][0]["id"]
    write_json(path, data)

    errors = failures(data_root)
    assert any("duplicate set id" in e for e in errors), errors


def test_a_map_naming_an_unknown_set_fails(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    data["maps"][0]["room_palette"] = "nowhere"
    write_json(path, data)

    errors = failures(data_root)
    assert any("data/maps/all.json" in e and "maps[0].room_palette" in e and "not a set" in e
               for e in errors), errors


def test_a_master_colour_edited_in_place_fails(data_root, read_json, write_json):
    path = data_root / "data" / "palette.json"
    data = read_json(path)
    data["colours"][5] = "#010203"
    write_json(path, data)

    errors = failures(data_root)
    assert any("data/palette.json" in e and "frozen_digest" in e for e in errors), errors


def test_a_master_colour_removed_and_one_appended_still_fails(data_root, read_json, write_json):
    path = data_root / "data" / "palette.json"
    data = read_json(path)
    data["colours"].pop(5)
    data["colours"].append("#010203")
    write_json(path, data)

    errors = failures(data_root)
    assert any("frozen_digest" in e for e in errors), errors


def test_appending_a_new_master_colour_passes(data_root, read_json, write_json):
    path = data_root / "data" / "palette.json"
    data = read_json(path)
    data["colours"].append("#010203")
    write_json(path, data)

    assert failures(data_root) == []


def test_a_family_role_pointing_at_the_wrong_level_fails(data_root, read_json, write_json):
    path = data_root / "data" / "palette.json"
    data = read_json(path)
    data["roles"]["sea_4"] = data["roles"]["sea_4"] + 1
    write_json(path, data)

    errors = failures(data_root)
    assert any("roles.sea_4" in e and "level 4" in e for e in errors), errors


# ---------------------------------------------------------------------------------------------------------------
# The sweep over our own GML.


def draw_code_offenders(text: str) -> str:
    """The colour literals in one module's code, as a printable list. Comments are not code."""
    code = gml_code_only(text)
    if not DRAW_CALL.search(code):
        return ""
    found = sorted(set(match.group(0) for match in COLOUR_LITERAL.finditer(code)))
    return str(found) if found else ""


def test_no_colour_literal_in_draw_code():
    offenders = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in sorted(filenames):
            if not name.endswith(".gml"):
                continue
            full = os.path.join(dirpath, name)
            relative = os.path.relpath(full, ROOT).replace("\\", "/")
            if any(relative.startswith(allowed) for allowed in LITERAL_ALLOWLIST):
                continue
            with open(full, "r", encoding="utf-8-sig") as fh:
                code = gml_code_only(fh.read())
            found = draw_code_offenders(code)
            if found:
                offenders.append("%s: %s" % (relative, found))
    assert offenders == [], "a draw call names a colour instead of asking the palette for a role:\n" + "\n".join(offenders)


def test_the_sweep_fails_on_a_planted_colour_literal():
    planted = "draw_set_colour(c_black);\ndraw_rectangle(0, 0, 1, 1, false);"
    assert draw_code_offenders(planted) != ""
    # And a literal in a comment is not a failure, which is the defect the shared GML audit hit before.
    assert draw_code_offenders("// this used to be draw_set_colour(c_black);\ndraw_rectangle(0, 0, 1, 1, false);") == ""
