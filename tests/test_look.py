"""Tests for the 8 bit look: a 16 colour room cap, an append only master palette, a whole scale and no filter.

Why a test and not a review note: every one of these rules is a claim that would rot silently. A room palette may grow a
seventeenth colour in a data edit and nothing would fail on a machine with no GameMaker; a master colour may be edited
in place and every sprite indexed after it would shift with no error; a draw call may reach for a named colour and look
right until the palette moves; a scale may pick up a fraction and only look wrong on a monitor the author does not own.
So each rule is broken on purpose in a private copy of data\\ or on a planted module and the checker or the sweep must
say so by file and by field.

Card t_5665c7d8 item and the test that pins it:
1  frame 256x240, whole scale 1 to 6, spec and code read together
   test_the_spec_and_the_code_agree_on_the_frame, test_the_spec_and_the_code_agree_on_the_scale,
   test_the_scale_rule_is_the_whole_one_the_spec_states, test_the_specs_still_state_the_rules_these_tests_pin
2  at most 16 colours per room set, every entry a real role, a 17th refused
   test_every_room_palette_fits_the_screen_cap, test_seventeen_colours_in_a_room_palette_fails and its neighbours
3  the master palette is append only, by a snapshot of ids by position
   test_the_master_palette_is_append_only_by_snapshot, test_an_entry_inserted_ahead_of_the_snapshot_is_caught
4  no fractional scale in draw or camera code
   test_no_fractional_scale_in_the_draw_or_camera_code, test_the_window_is_only_ever_sized_whole
5  texture interpolation off once and never on again
   test_texture_interpolation_is_off_and_never_turned_on
6  draw code resolves colour through pp_role_colour, debug overlay the only exception
   test_draw_colour_comes_from_a_palette_role, test_the_only_named_colour_constants_are_the_listed_ones,
   test_no_colour_literal_in_draw_code, test_every_role_named_in_draw_code_exists_in_the_master_palette
7  the mutation demonstrated, then reverted
   test_a_seventeenth_colour_is_refused_and_reverting_clears_it

Card t_638da7e0 (the rework) item and the test that pins it:
1  the 17 colour refusal names the room's set, not only its position
   test_seventeen_colours_in_a_room_palette_fails, test_a_seventeenth_colour_is_refused_and_reverting_clears_it
2  every engine call in pp_look cites its manual page
   test_every_engine_call_in_the_look_module_cites_its_manual_page
3  a role the room's set does not declare cannot add a colour
   test_a_role_outside_the_rooms_set_draws_the_missing_colour, test_a_set_plus_the_missing_colour_still_fits_the_cap
4  the viewport is the frame times the scale, and the dead letterbox fields are gone
   test_the_viewport_is_the_frame_times_the_scale

Honest limit: nothing here renders a frame, measures a pixel or proves the look on a monitor. What is pinned is the rule.
GameMaker LTS 2026 is installed (the DEVLOG entry for 2026-10-22 records four real runs of this tree that morning), but no
run has yet read a pixel back for this card, so the appearance stays unproven until the 3x screenshot acceptance in spec
13 item 1 through 3 and the first frame measurement are taken from a running build.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re

import check_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The numbers spec 13 and spec 03 decide. They are repeated here on purpose: this file is the pin, so a change has to be
# made in the spec, the module and this file, and cannot arrive by accident in one of them.
SCREEN_CAP = 16
MASTER_SIZE = 54
BASE_W, BASE_H = 256, 240
MIN_SCALE, MAX_SCALE = 1, 6

# The master palette as it stands at this commit, id by position. Append only means these 54 entries stay in this order
# and a new entry may only land past the end, so a palette swap on a boss or a night map cannot shift under existing art.
PALETTE_SNAPSHOT = (
    "#0b0b0f", "#1c1c24", "#2e2e3a", "#4a4a58", "#7a7a88", "#c8c8d4",
    "#081420", "#0d2b3a", "#11485c", "#1a6f82", "#2fa3ab", "#7fd8d4",
    "#1a0f05", "#331d09", "#55300f", "#7d4a1a", "#a86d2a", "#d8a55c",
    "#1c0510", "#3a0a1f", "#5c1230", "#85203f", "#b33a52", "#e07a86",
    "#12150a", "#232a12", "#3a4420", "#55632f", "#7a8a45", "#adbc74",
    "#14110f", "#262019", "#3b3226", "#554738", "#75634c", "#a6957c",
    "#1f1705", "#3a2c08", "#5c460d", "#856719", "#b38f28", "#e8c65a",
    "#0a0614", "#170d2a", "#271640", "#3d2560", "#5c3a87", "#8f6fb8",
    "#180404", "#300808", "#4a0c0c", "#6b1414", "#911f1f", "#c24040",
)

# Every role in data\palette.json at this commit and the position it names. A role moved off its position is the edit
# that would silently repaint a room, so it is pinned by name. A role added later for an appended colour is allowed, and
# the test below requires it to point past the sealed prefix rather than into the middle of it.
ROLE_INDEX_SNAPSHOT = {
    "ink": 0, "paper": 1, "window_shadow": 2, "dim": 3, "window_edge": 5, "text": 5,
    "window": 6, "accent": 17, "marker": 41, "marker_trail": 40, "hazard": 53, "warn": 23,
    "grey_0": 0, "grey_1": 1, "grey_2": 2, "grey_3": 3, "grey_4": 4, "grey_5": 5,
    "sea_0": 6, "sea_1": 7, "sea_2": 8, "sea_3": 9, "sea_4": 10, "sea_5": 11,
    "bronze_0": 12, "bronze_1": 13, "bronze_2": 14, "bronze_3": 15, "bronze_4": 16, "bronze_5": 17,
    "wine_0": 18, "wine_1": 19, "wine_2": 20, "wine_3": 21, "wine_4": 22, "wine_5": 23,
    "moss_0": 24, "moss_1": 25, "moss_2": 26, "moss_3": 27, "moss_4": 28, "moss_5": 29,
    "stone_0": 30, "stone_1": 31, "stone_2": 32, "stone_3": 33, "stone_4": 34, "stone_5": 35,
    "gold_0": 36, "gold_1": 37, "gold_2": 38, "gold_3": 39, "gold_4": 40, "gold_5": 41,
    "violet_0": 42, "violet_1": 43, "violet_2": 44, "violet_3": 45, "violet_4": 46, "violet_5": 47,
    "blood_0": 48, "blood_1": 49, "blood_2": 50, "blood_3": 51, "blood_4": 52, "blood_5": 53,
}

# A draw call, in code rather than in a comment. The literal sweep only judges files that actually draw.
DRAW_CALL = re.compile(r"\bdraw_[a-z0-9_]+\s*\(")
# A colour the code chose rather than looked up: a GameMaker colour name, or a colour built from numbers.
COLOUR_LITERAL = re.compile(r"\bc_[a-z]+\b|\bmake_colou?r_rgb\s*\(")
# The debug overlay is allowed to name colours: it draws diagnostics in black and white on purpose, and it is not part of
# the screen the player sees (the card's own allowance, and the only one).
LITERAL_ALLOWLIST = ("game/objects/obj_pp_debug_overlay",)

# The named colour constants the project ships, and the expression each one is. Anything not listed here fails: a colour
# literal may exist as a named constant in pp_config, never as a call argument at a draw site.
NAMED_COLOUR_CONSTANTS = {
    "PP_UNTINTED": "c_white",
    "PP_COLOUR_MISSING": "make_colour_rgb(255, 0, 255)",
    "PP_TITLE_WHITE": "make_colour_rgb(248, 248, 248)",
    "PP_TITLE_DIM": "make_colour_rgb(0, 88, 0)",
    "PP_TITLE_BACKDROP": "c_black",
}
# The files that use each one today. The three PP_TITLE constants are the title's band palette as GML: $20 white, $0B
# the ground band's dark green (the disabled rule and the window frame) and $0F the backdrop, which are the entries
# data/palettes/scene_title.json declares for the bands they are drawn into (card t_a1170172). There is no grey: the
# font sheet carries one ink and a tinted grey came out as #7b7b7b, which no PPU can output, so the "off" state is a
# rule drawn in $0B (pp_title_draw_disabled). They are raw RGB rather than a role because a role resolves through
# data/palette.json, which holds no 2C02 colour at all; the frame check replaces the role rule for
# game/scripts/pp_title/pp_title.gml and is stricter than a role name. PP_UNTINTED is a blend factor that means "draw
# the sprite as authored", not a colour choice (see the comment in pp_config).
NAMED_COLOUR_USERS = {
    "PP_UNTINTED": (
        "game/scripts/pp_art/pp_art.gml",
        "game/scripts/pp_battle_director/pp_battle_director.gml",
        "game/scripts/pp_dialogue/pp_dialogue.gml",
        "game/scripts/pp_font/pp_font.gml",
        "game/scripts/pp_map/pp_map.gml",
        "game/scripts/pp_overworld/pp_overworld.gml",
        "game/scripts/pp_title/pp_title.gml",
    ),
    "PP_COLOUR_MISSING": ("game/scripts/pp_data/pp_data.gml", "game/scripts/pp_look/pp_look.gml"),
    "PP_TITLE_WHITE": ("game/scripts/pp_title/pp_title.gml",),
    "PP_TITLE_DIM": ("game/scripts/pp_title/pp_title.gml",),
    "PP_TITLE_BACKDROP": ("game/scripts/pp_title/pp_title.gml",),
}

# The one place a window is sized outside pp_look, pinned to the scale the spec calls the default. It runs in the game
# object's Create event before pp_app_boot, so pp_look has an integer window to measure on its first call.
DEFAULT_WINDOW_CALLER = "game/objects/obj_pp_game/Create_0.gml"

# Every engine call pp_look makes, and the manual page that documents it. A call whose page is not written next to it is
# a claim about an engine behaviour that nobody can check without the manual open (card t_638da7e0 item 2). The pages
# were read on 2026-10-22; the filter call is documented as gpu_set_texfilter, which is why this table names that page
# for the underscored spelling the module uses.
MANUAL_CALLS = {
    "surface_resize": "Drawing/Surfaces/surface_resize.htm",
    "display_set_gui_size": "Cameras_And_Display/display_set_gui_size.htm",
    "gpu_set_tex_filter": "Drawing/GPU_Control/gpu_set_texfilter.htm",
    "view_set_wport": "Cameras_And_Display/Cameras_And_Viewports/view_set_wport.htm",
    "camera_set_view_size": "Cameras_And_Display/Cameras_And_Viewports/camera_set_view_size.htm",
}

SEVENTEEN = [
    "grey_0", "grey_1", "grey_2", "grey_3", "grey_4", "grey_5",
    "sea_0", "sea_1", "sea_2", "sea_3", "sea_4", "sea_5",
    "bronze_0", "bronze_1", "bronze_2", "bronze_3", "bronze_4",
]


# ---------------------------------------------------------------------------------------------------------------
# Reading the project.


def read(relative: str) -> str:
    with open(os.path.join(ROOT, *relative.split("/")), "r", encoding="utf-8-sig") as fh:
        return fh.read()


def read_json_file(relative: str):
    return json.loads(read(relative))


def gml_code_only(text: str) -> str:
    """Strip comments, so a rule is judged on code and a comment that names a colour is not a failure."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.split("//")[0] for line in text.splitlines())


def without_strings(code: str) -> str:
    """Blank the inside of string literals, so a comma or a bracket in dialogue text cannot confuse an argument scan."""
    return re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)


def gml_sources() -> dict:
    """Every .gml in game/, as relative path to comment stripped code."""
    sources = {}
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in sorted(filenames):
            if not name.endswith(".gml"):
                continue
            full = os.path.join(dirpath, name)
            with open(full, "r", encoding="utf-8-sig") as fh:
                sources[os.path.relpath(full, ROOT).replace("\\", "/")] = gml_code_only(fh.read())
    return sources


FUNCTION_HEAD = re.compile(r"function\s+(pp_[a-z0-9_]+)\s*\(([^)]*)\)\s*\{")


def functions(code: str) -> list:
    """(name, params, body, start, end) for each function in one module, the body taken by brace matching."""
    found = []
    for match in FUNCTION_HEAD.finditer(code):
        depth = 0
        end = None
        for index in range(match.end() - 1, len(code)):
            char = code[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end is None:
            continue
        found.append({
            "name": match.group(1),
            "params": [p.strip() for p in match.group(2).split(",") if p.strip()],
            "body": code[match.end():end],
            "start": match.end(),
            "end": end,
        })
    return found


def function_body(code: str, name: str) -> str:
    for func in functions(code):
        if func["name"] == name:
            return func["body"]
    return ""


def call_arguments(code: str, name: str) -> list:
    """The top level argument strings of every call to `name`, with the function definition itself skipped."""
    code = without_strings(code)
    calls = []
    for match in re.finditer(r"\b%s\s*\(" % re.escape(name), code):
        if re.search(r"function\s+$", code[:match.start()]):
            continue
        index = match.end()
        depth = 1
        args, current = [], []
        while index < len(code) and depth:
            char = code[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    break
            if char == "," and depth == 1:
                args.append("".join(current).strip())
                current = []
            else:
                current.append(char)
            index += 1
        tail = "".join(current).strip()
        if tail or args:
            args.append(tail)
        calls.append(args)
    return calls


def failures(root):
    return check_data.check(str(root))


# ---------------------------------------------------------------------------------------------------------------
# Item 1: the frame and the scale, read out of the spec and out of the code, so neither can drift alone.


def spec13_numbers() -> dict:
    text = read("specs/13-8bit-look.md")
    frame = re.search(r"Frame and pixels: (\d+)x(\d+), integer scaled \(spec 03\), point sampled", text)
    master = re.search(r"master palette of (\d+) colours", text)
    grid = re.search(r"(\d+) hues by (\d+) visible levels", text)
    cap = re.search(r"At most (\d+) colours on screen at once", text)
    assert frame, "spec 13 no longer states 'Frame and pixels: 256x240, integer scaled (spec 03), point sampled'"
    assert master, "spec 13 no longer states the master palette size"
    assert grid, "spec 13 no longer states the hues by levels grid"
    assert cap, "spec 13 no longer states the on screen colour cap"
    return {
        "frame": (int(frame.group(1)), int(frame.group(2))),
        "master": int(master.group(1)),
        "grid": (int(grid.group(1)), int(grid.group(2))),
        "cap": int(cap.group(1)),
    }


def spec03_numbers() -> dict:
    text = read("specs/03-camera-and-scaling.md")
    base = re.search(r"Base frame (\d+)x(\d+), a hard constant\.\s*Scale (\d+) to (\d+)", text)
    formula = re.search(
        r"`max\((\d+), min\((\d+), floor\(min\(window_w / (\d+), window_h / (\d+)\)\)\)\)`", text)
    default = re.search(r"Default window (\d+)x(\d+) \((\d+)x\)", text)
    gui = re.search(r"display_set_gui_size\((\d+), (\d+)\)", text)
    fullscreen = re.search(r"1080p screen gives (\d+)x(\d+)", text)
    assert base, "spec 03 no longer states 'Base frame 256x240, a hard constant. Scale 1 to 6'"
    assert formula, "spec 03 no longer states the scale formula"
    assert default, "spec 03 no longer states the default window"
    assert gui, "spec 03 no longer states display_set_gui_size"
    assert fullscreen, "spec 03 no longer states the 1080p acceptance result"
    return {
        "frame": (int(base.group(1)), int(base.group(2))),
        "low": int(base.group(3)),
        "high": int(base.group(4)),
        "rule": (int(formula.group(1)), int(formula.group(2)), int(formula.group(3)), int(formula.group(4))),
        "default": (int(default.group(1)), int(default.group(2)), int(default.group(3))),
        "gui": (int(gui.group(1)), int(gui.group(2))),
        "fullscreen": (int(fullscreen.group(1)), int(fullscreen.group(2))),
    }


def spec_scale_for(window_w, window_h, low=MIN_SCALE, high=MAX_SCALE, frame=(BASE_W, BASE_H)) -> int:
    """Spec 03's rule, written in Python exactly as the spec states it: max(1, min(6, floor(min(w/w0, h/h0))))."""
    return max(low, min(high, math.floor(min(window_w / frame[0], window_h / frame[1]))))


def test_the_specs_still_state_the_rules_these_tests_pin():
    look = " ".join(read("specs/13-8bit-look.md").split())
    camera = " ".join(read("specs/03-camera-and-scaling.md").split())
    for phrase in ("integer scaled", "point sampled", "no fractional scaling", "At most 16 colours on screen at once",
                   "New entries are only ever appended, never inserted"):
        assert phrase.lower() in look.lower(), "spec 13 no longer states %r" % phrase
    for phrase in ("integer scale only", "Texture interpolation off once at start", "gpu_set_tex_filter(false)",
                   "never set to a non integer scale", "display_set_gui_size(256, 240)"):
        assert phrase.lower() in camera.lower(), "spec 03 no longer states %r" % phrase


def test_the_spec_and_the_code_agree_on_the_frame():
    thirteen = spec13_numbers()
    three = spec03_numbers()

    assert thirteen["frame"] == three["frame"] == (BASE_W, BASE_H), "the two specs disagree on the frame"
    assert three["gui"] == (BASE_W, BASE_H), "spec 03's GUI size is not the frame"
    assert thirteen["cap"] == SCREEN_CAP
    assert thirteen["master"] == MASTER_SIZE
    assert thirteen["grid"][0] * thirteen["grid"][1] == MASTER_SIZE

    config = gml_code_only(read("game/scripts/pp_config/pp_config.gml"))
    macro = dict(re.findall(r"#macro\s+(PP_[A-Z0-9_]+)\s+(-?\d+)\b", config))
    assert int(macro["PP_FRAME_W"]) == BASE_W
    assert int(macro["PP_FRAME_H"]) == BASE_H
    assert int(macro["PP_MAX_SCALE"]) == MAX_SCALE

    assert (check_data.FRAME_W, check_data.FRAME_H) == (BASE_W, BASE_H)
    assert read_json_file("data/project.json")["base_frame"] == [BASE_W, BASE_H]

    look = gml_code_only(read("game/scripts/pp_look/pp_look.gml"))
    assert re.search(r"var _w = PP_FRAME_W \* _s;", look)
    assert re.search(r"var _h = PP_FRAME_H \* _s;", look)
    assert re.search(r"display_set_gui_size\(PP_FRAME_W, PP_FRAME_H\);", look)


def test_the_spec_and_the_code_agree_on_the_scale():
    three = spec03_numbers()
    assert (three["low"], three["high"]) == (MIN_SCALE, MAX_SCALE), "spec 03 changed the scale range"
    assert three["rule"][0] == MIN_SCALE and three["rule"][1] == MAX_SCALE, "spec 03's formula changed its range"
    assert (three["rule"][2], three["rule"][3]) == (BASE_W, BASE_H), "spec 03's formula changed the frame"

    assert check_data.PALETTE_SIZE == MASTER_SIZE
    assert check_data.MAX_COLOURS_ON_SCREEN == SCREEN_CAP

    # The formula in the module is the formula in the spec: floored divisions, then clamped to the range.
    scale_function = function_body(gml_code_only(read("game/scripts/pp_look/pp_look.gml")), "pp_look_scale_for")
    assert "floor(_ww / PP_FRAME_W)" in scale_function
    assert "floor(_hh / PP_FRAME_H)" in scale_function
    assert "max(1, min(PP_MAX_SCALE, min(_sx, _sy)))" in scale_function
    assert "round" not in scale_function and "* 0." not in scale_function

    # One implementation: the camera asks pp_look instead of carrying a second copy of the maths.
    camera = gml_code_only(read("game/scripts/pp_camera/pp_camera.gml"))
    assert "pp_look_scale_for(" in camera
    assert "floor(_ww / PP_FRAME_W)" not in camera, "pp_camera computes the scale itself again"


def test_the_scale_rule_is_the_whole_one_the_spec_states():
    three = spec03_numbers()
    low, high, fw, fh = three["rule"]

    def rule(window_w, window_h):
        return spec_scale_for(window_w, window_h, low, high, (fw, fh))

    # One frame is 1x, and the spec's default window is exactly 3x, which is the 768x720 it names.
    assert rule(BASE_W, BASE_H) == 1
    default_w, default_h, default_scale = three["default"]
    assert rule(default_w, default_h) == default_scale == 3
    assert (fw * default_scale, fh * default_scale) == (default_w, default_h)
    assert (default_w, default_h) == (768, 720)

    # The 1080p acceptance line in spec 03 is the same rule: 4x, 1024x960, with bars around it.
    assert rule(1920, 1080) == 4
    assert (fw * 4, fh * 4) == three["fullscreen"] == (1024, 960)

    # Never below 1, never above 6, the smaller dimension decides, and a fractional window rounds down.
    assert rule(1, 1) == 1
    assert rule(255, 239) == 1
    assert rule(511, 480) == 1
    assert rule(512, 480) == 2
    assert rule(512, 240) == 1, "the shorter dimension is the one that decides"
    assert rule(600, 480) == 2
    assert rule(1600, 1200) == 5
    assert rule(1792, 1680) == 6, "7x fits the window and the cap is 6"
    assert rule(100000, 100000) == 6
    assert all(isinstance(rule(w, h), int) for w, h in ((768, 720), (1920, 1080), (100000, 100000)))


# ---------------------------------------------------------------------------------------------------------------
# Item 2: at most 16 colours in a room set, every entry a role, a 17th refused.


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
    with open(os.path.join(ROOT, "game", "scripts", "pp_camera", "pp_camera.gml"), "r", encoding="utf-8-sig") as fh:
        camera = gml_code_only(fh.read())
    assert "pp_look_scale_for(" in camera
    assert "floor(_ww / PP_FRAME_W)" not in camera, "pp_camera computes the scale itself again"


def test_every_engine_call_in_the_look_module_cites_its_manual_page():
    lines = read("game/scripts/pp_look/pp_look.gml").splitlines()
    uncited = []
    for call, page in sorted(MANUAL_CALLS.items()):
        cited = False
        for number, line in enumerate(lines):
            if line.lstrip().startswith("//"):
                continue
            if not re.search(r"\b%s\s*\(" % re.escape(call), line):
                continue
            # The page has to sit beside the call it explains, not somewhere in the file: four lines is the width of a
            # comment block and the argument it introduces.
            window = "\n".join(lines[max(0, number - 4):number + 1])
            if "manual.gamemaker.io" in window and page in window:
                cited = True
                break
        if not cited:
            uncited.append("%s (%s)" % (call, page))
    assert uncited == [], "a call with no manual page beside it: %s" % uncited

    # The pages themselves are the manual's own paths, not a guess at a URL: the host and the section are part of the
    # citation, so a wrong page is a wrong claim and not a cosmetic detail.
    text = read("game/scripts/pp_look/pp_look.gml")
    for page in MANUAL_CALLS.values():
        assert "https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/" + page in text, page
    assert "GmlSpec.xml" in text, "the filter call's underscored spelling is not explained"


def test_the_viewport_is_the_frame_times_the_scale():
    look = gml_code_only(read("game/scripts/pp_look/pp_look.gml"))
    apply_window = function_body(look, "pp_look_apply_window")
    for expected in ("view_enabled = true", "view_visible[0] = true", "view_set_xport(0, 0)", "view_set_yport(0, 0)",
                     "view_set_wport(0, _w)", "view_set_hport(0, _h)",
                     "camera_set_view_size(view_camera[0], PP_FRAME_W, PP_FRAME_H)"):
        assert expected in apply_window, "the viewport is not the frame times the scale: %r" % expected
    assert "surface_resize(application_surface, _w, _h)" in apply_window
    assert "window_set_size(_w, _h)" in apply_window

    # The port is re-asserted every step, because a room carries its own view settings and every room in this project
    # has views 0 to 7 invisible: a set made once at boot is gone the first time the room changes.
    update = function_body(look, "pp_look_update")
    for expected in ("!view_enabled", "!view_visible[0]", "view_get_wport(0) != _w", "view_get_hport(0) != _h"):
        assert expected in update, "pp_look_update does not re-assert the viewport: %r" % expected

    # The letterbox offset is gone rather than promised. It was computed into two fields nothing read, while the comment
    # beside it claimed a window that cannot take the scale still centres the frame (card t_638da7e0 item 4).
    assert "offset_x" not in look and "offset_y" not in look
    for relative, code in gml_sources().items():
        assert "offset_x" not in code and "offset_y" not in code, "%s still reads a letterbox offset" % relative


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


def test_every_room_palette_fits_the_screen_cap_and_names_a_real_role():
    palette = read_json_file("data/palette.json")
    roles = palette["roles"]
    rooms = read_json_file("data/room_palettes.json")

    ids = []
    for index, room_set in enumerate(rooms["sets"]):
        ids.append(room_set["id"])
        names = room_set["roles"]
        assert 0 < len(names) <= SCREEN_CAP, "set %r declares %d colours" % (room_set["id"], len(names))
        assert len(set(names)) == len(names), "set %r names a role twice" % room_set["id"]
        for name in names:
            assert name in roles, "set %r names %r, which is not a role in data/palette.json" % (room_set["id"], name)
            assert 0 <= roles[name] < MASTER_SIZE, "set %r names %r at index %d" % (room_set["id"], name, roles[name])
    assert len(set(ids)) == len(ids), "a room palette id is declared twice"
    assert rooms["default"] in ids

    # Every map draws in a declared set, and its own explicit colour list is inside the same cap. check_data only walks
    # data/maps/all.json, so the sample maps are swept here as well, which is the "every room or map" half of the rule.
    map_dir = os.path.join(ROOT, "data", "maps")
    map_files = sorted(name for name in os.listdir(map_dir) if name.endswith(".json"))
    assert "all.json" in map_files, "the map the checker reads is missing"
    for name in map_files:
        for row in read_json_file("data/maps/" + name).get("maps", []):
            if "room_palette" in row:
                assert row["room_palette"] in ids, "%s: map %r names the set %r" % (name, row["id"], row["room_palette"])
            indices = row.get("palette_indices")
            if indices is not None:
                assert len(indices) <= SCREEN_CAP, "%s: map %r lists %d colours" % (name, row["id"], len(indices))
                assert all(isinstance(value, int) and 0 <= value < MASTER_SIZE for value in indices), name


def test_real_data_passes():
    assert failures(ROOT) == []


def test_a_role_outside_the_rooms_set_draws_the_missing_colour():
    """A role the room's set does not declare may not borrow a colour from the master palette (card t_638da7e0 item 3).

    deck_day declares 14 roles and 13 distinct colours, while pp_app and pp_dodge_arena ask for accent, hazard, marker and
    marker_trail. With the master palette as a fallback those four quietly added their colours and a deck_day screen could
    spend 17, which spec 13 rule 2 forbids and acceptance 3 refuses to look at. The lookup now answers only from the set in
    use, and the missing colour is one colour whatever the role, so the cap holds.
    """
    look = read("game/scripts/pp_look/pp_look.gml")
    code = gml_code_only(look)

    index = function_body(code, "pp_look_role_index")
    assert index, "pp_look_role_index is gone"
    assert "_look.master" not in index, "the role lookup falls back to the master palette again"
    assert "return -1" in index, "a role outside the set is not reported as missing"

    colour = function_body(code, "pp_role_colour")
    assert "PP_COLOUR_MISSING" in colour, "an out of set role does not draw the missing colour"
    assert "_look.missing" in colour and "show_debug_message" in colour, "an out of set role is not logged"
    assert "pp_colour(_index)" in colour and "if (_index >= 0)" in colour

    # The behaviour the module now has is the behaviour pp_config already documented for that constant.
    config = " ".join(read("game/scripts/pp_config/pp_config.gml").split())
    assert "PP_COLOUR_MISSING is what a bad palette index or an unknown role draws as" in config


def test_a_set_plus_the_missing_colour_still_fits_the_cap():
    """A declared set of 16 roles plus one missing colour would be 17 on screen, so the data has to leave room for it."""
    roles = read_json_file("data/palette.json")["roles"]
    for room_set in read_json_file("data/room_palettes.json")["sets"]:
        colours = {roles[name] for name in room_set["roles"] if name in roles}
        assert len(colours) + 1 <= SCREEN_CAP, \
            "set %r declares %d distinct colours, and a role outside it adds the missing colour: %d on screen" % (
                room_set["id"], len(colours), len(colours) + 1)


def test_seventeen_colours_in_a_room_palette_fails(data_root, read_json, write_json):
    path = data_root / "data" / "room_palettes.json"
    data = read_json(path)
    data["sets"][0]["roles"] = SEVENTEEN
    write_json(path, data)

    # The refusal names the room's set by id as well as by position: the first set is ui, and whoever reads the failure
    # has to be able to tell which rooms draw in it without counting sets (spec 13 acceptance item 3, PROGRESS.md).
    first_id = data["sets"][0]["id"]
    errors = failures(data_root)
    assert any("data/room_palettes.json" in e and "sets[0]" in e and repr(first_id) in e
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
    assert any("data/room_palettes.json" in e and "sets[1] 'deck_day'.roles[2]" in e and "not a role" in e
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


# ---------------------------------------------------------------------------------------------------------------
# Item 3: the master palette is append only, pinned by a snapshot of ids by position.


def snapshot_failures(colours, roles) -> list:
    """What append only means for one master palette. Empty means the rule held.

    The snapshot is the 54 entries this test file was written against, in order. An entry inserted anywhere ahead of the
    end moves every colour after it, so the prefix stops matching position for position, and any role that pointed past
    the insertion now names a different colour. Both are reported, because both repaint art with no error at runtime.
    """
    problems = []
    if len(colours) < MASTER_SIZE:
        problems.append("count %d is below the sealed %d" % (len(colours), MASTER_SIZE))
    prefix = [value.lower() if isinstance(value, str) else value for value in colours[:MASTER_SIZE]]
    for index, expected in enumerate(PALETTE_SNAPSHOT):
        if index >= len(prefix):
            break
        if prefix[index] != expected:
            problems.append("colours[%d] is %r, the snapshot has %r" % (index, prefix[index], expected))
            break
    moved = [(name, roles.get(name), expected) for name, expected in ROLE_INDEX_SNAPSHOT.items()
             if roles.get(name) != expected]
    for name, actual, expected in moved[:4]:
        problems.append("roles.%s is %r, the snapshot has %d" % (name, actual, expected))
    if len(moved) > 4:
        problems.append("and %d more roles moved" % (len(moved) - 4))
    return problems


def test_the_master_palette_is_append_only_by_snapshot():
    data = read_json_file("data/palette.json")
    colours = [value.lower() for value in data["colours"]]

    # The count, the first entry, the last sealed entry, and every id in between, by position.
    assert len(colours) >= MASTER_SIZE, "the master palette lost an entry; spec 13 allows appending only"
    assert data["frozen"] == MASTER_SIZE, "the sealed prefix is not the shipped %d entries" % MASTER_SIZE
    assert colours[0] == PALETTE_SNAPSHOT[0]
    assert colours[MASTER_SIZE - 1] == PALETTE_SNAPSHOT[-1]
    assert colours[:MASTER_SIZE] == list(PALETTE_SNAPSHOT), "an entry was inserted or moved inside the sealed prefix"

    # The digest seals the snapshot, recomputed here from this file's list rather than trusted from the data file.
    sealed = ",".join(PALETTE_SNAPSHOT)
    assert data["frozen_digest"] == hashlib.sha256(sealed.encode("utf-8")).hexdigest()

    # Every role still points where it pointed. A new role is allowed past the seal, never inside it.
    for name, expected in ROLE_INDEX_SNAPSHOT.items():
        assert data["roles"].get(name) == expected, "role %r moved off index %d" % (name, expected)
    added = {name: index for name, index in data["roles"].items() if name not in ROLE_INDEX_SNAPSHOT}
    for name, index in added.items():
        assert index >= MASTER_SIZE, "new role %r points inside the sealed prefix at %d" % (name, index)
        assert index < len(colours), "new role %r points past the end of the palette" % name
        assert colours[index] not in PALETTE_SNAPSHOT, "new role %r reuses a sealed colour" % name


def test_an_entry_inserted_ahead_of_the_snapshot_is_caught():
    data = read_json_file("data/palette.json")
    assert snapshot_failures(data["colours"], data["roles"]) == []

    head = copy.deepcopy(data["colours"])
    head.insert(0, "#123456")
    assert snapshot_failures(head, data["roles"]), "an entry inserted at the head was not caught"

    middle = copy.deepcopy(data["colours"])
    middle.insert(20, "#123456")
    assert snapshot_failures(middle, data["roles"]), "an entry inserted in the middle was not caught"

    tail = copy.deepcopy(data["colours"])
    tail.append("#123456")
    assert snapshot_failures(tail, data["roles"]) == [], "an appended entry must still pass"


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
# Item 4: no fractional scale in our draw or camera code.


# A window or display dimension divided by the frame, which is the one computation that may become the scale.
FRAME_DIVISION = re.compile(
    r"(?<![\w.])(?:window_get_width\(\)|window_get_height\(\)|display_get_width\(\)|"
    r"display_get_height\(\)|_ww|_hh)\s*/\s*(?:PP_FRAME_W|PP_FRAME_H|256|240)\b")
# Draw calls whose x and y scale arguments decide how many screen pixels one game pixel becomes.
SCALED_DRAW = {
    "draw_sprite_ext": (4, 5),
    "draw_sprite_part_ext": (8, 9),
    "draw_surface_ext": (3, 4),
    "draw_text_transformed": (3, 4),
}


def whole_scale(argument: str) -> bool:
    """True when an argument to a draw call cannot be a fraction."""
    argument = argument.strip()
    if re.fullmatch(r"\d+", argument):
        return True
    if "floor(" in argument or "pp_look_scale" in argument:
        return True
    return argument in {"_s", "_scale", "global.pp_look.scale", "_look.scale"}


def fractional_scale_offenders(code: str) -> list:
    """The lines that turn a window size into a scale without floor(), and the draw scales that are not whole."""
    offenders = []
    for number, line in enumerate(code.splitlines(), 1):
        if FRAME_DIVISION.search(line) and "floor(" not in line:
            offenders.append("line %d divides without floor: %s" % (number, line.strip()))
    for name, positions in SCALED_DRAW.items():
        for args in call_arguments(code, name):
            for position in positions:
                if position >= len(args):
                    offenders.append("%s call with only %d arguments" % (name, len(args)))
                    continue
                if not whole_scale(args[position]):
                    offenders.append("%s scale argument %r at position %d" % (name, args[position], position))
    return offenders


def test_no_fractional_scale_in_the_draw_or_camera_code():
    # No allowlist on the division rule: a scale is a floor of a frame division, which is how pp_look writes it, and
    # nothing else in the project divides a window by the frame at all.
    sources = gml_sources()
    offenders = []
    for relative, code in sorted(sources.items()):
        for problem in fractional_scale_offenders(code):
            offenders.append("%s: %s" % (relative, problem))
    assert offenders == [], "a scale is computed as a fraction:\n" + "\n".join(offenders)

    # The rule bites: these are the shapes that must not come back.
    assert fractional_scale_offenders("var _s = window_get_width() / PP_FRAME_W;")
    assert fractional_scale_offenders("var _s = floor(window_get_width() / PP_FRAME_W);") == []
    assert fractional_scale_offenders("draw_sprite_part_ext(spr, 0, 0, 0, 8, 8, 0, 0, 1.5, 1.5, c_white, 1);")
    assert fractional_scale_offenders("draw_sprite_part_ext(spr, 0, 0, 0, 8, 8, 0, 0, 1, 1, c_white, 1);") == []


def test_the_window_is_only_ever_sized_whole():
    sources = gml_sources()
    spec = spec03_numbers()
    default_scale = spec["default"][2]

    gui = [(relative, args) for relative, code in sources.items() for args in call_arguments(code, "display_set_gui_size")]
    assert gui == [("game/scripts/pp_look/pp_look.gml", ["PP_FRAME_W", "PP_FRAME_H"])], \
        "the GUI is sized somewhere other than pp_look, or not to the frame: %s" % gui

    surfaces = [(relative, args) for relative, code in sources.items()
                for args in call_arguments(code, "surface_resize")]
    assert surfaces == [("game/scripts/pp_look/pp_look.gml", ["application_surface", "_w", "_h"])], surfaces

    windows = [(relative, args) for relative, code in sources.items() for args in call_arguments(code, "window_set_size")]
    look_sites = [args for relative, args in windows if relative == "game/scripts/pp_look/pp_look.gml"]
    assert look_sites == [["_w", "_h"]], "pp_look sizes the window from something other than the frame times a scale"

    # One other site, the default window before pp_look boots. Its multiplier is pinned to the spec's default scale, so
    # a spec edit and an object edit cannot drift apart quietly. (Two sites deciding the default is a defect this test
    # records rather than fixes: game code is not this card's to edit.)
    other = [(relative, args) for relative, args in windows if relative != "game/scripts/pp_look/pp_look.gml"]
    assert [relative for relative, _args in other] == [DEFAULT_WINDOW_CALLER], \
        "a new place sizes the window: %s" % [relative for relative, _args in other]
    assert other[0][1] == ["PP_FRAME_W * %d" % default_scale, "PP_FRAME_H * %d" % default_scale], other[0][1]
    assert (BASE_W * default_scale, BASE_H * default_scale) == (768, 720)


# ---------------------------------------------------------------------------------------------------------------
# Item 5: texture interpolation is off, once, and nothing turns it back on.

TEX_FILTER = re.compile(r"gpu_set_tex_filter\s*\(\s*(true|false)\s*\)")
OTHER_FILTER_SWITCHES = re.compile(r"\btexture_set_interpolation\s*\(|\bgpu_set_texfilter\s*\(|"
                                   r"\bgpu_set_tex_mip_filter\s*\(")


def tex_filter_offenders(sources: dict) -> list:
    """Every way the point sampling rule can be broken, by file."""
    offenders = []
    sites = []
    for relative, code in sources.items():
        for match in TEX_FILTER.finditer(code):
            sites.append((relative, match.group(1)))
            if match.group(1) != "false":
                offenders.append("%s: gpu_set_tex_filter(true)" % relative)
        if OTHER_FILTER_SWITCHES.search(code):
            offenders.append("%s: a second texture filter switch" % relative)
    if len(sites) != 1:
        offenders.append("%d texture filter sites, the look wants exactly one" % len(sites))
    for relative, _value in sites:
        if relative != "game/scripts/pp_look/pp_look.gml":
            offenders.append("the filter is set in %s, not in pp_look" % relative)
    return offenders


def test_texture_interpolation_is_off_and_never_turned_on():
    sources = gml_sources()
    assert tex_filter_offenders(sources) == [], "point sampling is not the only setting:\n" + \
        "\n".join(tex_filter_offenders(sources))

    look = sources["game/scripts/pp_look/pp_look.gml"]
    # One site, inside the function that owns the frame, and that function runs at start before anything draws.
    apply_window = function_body(look, "pp_look_apply_window")
    assert "gpu_set_tex_filter(false)" in apply_window
    assert "pp_look_apply_window();" in function_body(look, "pp_look_init")
    assert "pp_look_init()" in sources["game/scripts/pp_app/pp_app.gml"]

    # The rule bites: a second site, or a true, is a failure.
    assert tex_filter_offenders({"a.gml": "gpu_set_tex_filter(false);"})
    assert tex_filter_offenders({"a.gml": "gpu_set_tex_filter(true);"})
    assert tex_filter_offenders({"game/scripts/pp_look/pp_look.gml": "gpu_set_tex_filter(false);",
                                 "b.gml": "gpu_set_tex_filter(false);"})


# ---------------------------------------------------------------------------------------------------------------
# Item 6: draw code resolves its colour through pp_role_colour, the debug overlay the only exception.

SETTER = re.compile(r"\bdraw_set_colou?r\s*\(")


def role_helpers(sources: dict) -> set:
    """Functions that hand back a colour and get it from pp_role_colour and nothing else (pp_map_kind_colour).

    A function is a role helper only when it has at least one return and every return is a pp_role_colour call or a call
    to another role helper. A draw function that happens to contain a role call is not a colour source, which is the
    loose reading this rule exists to refuse.
    """
    candidates = {}
    for code in sources.values():
        for func in functions(code):
            returns = [value.strip() for value in re.findall(r"\breturn\b([^;]*);", func["body"])]
            candidates[func["name"]] = (func, returns)
    helpers = set()
    changed = True
    while changed:
        changed = False
        for name, (func, returns) in candidates.items():
            if name in helpers or not returns or COLOUR_LITERAL.search(func["body"]):
                continue
            for value in returns:
                if "pp_role_colour(" in value:
                    continue
                called = re.match(r"(pp_[a-z0-9_]+)\s*\(", value)
                if called and called.group(1) in helpers:
                    continue
                break
            else:
                helpers.add(name)
                changed = True
    return helpers


def function_index(sources: dict) -> dict:
    index = {}
    for relative, code in sources.items():
        for func in functions(code):
            func["file"] = relative
            index.setdefault(func["name"], []).append(func)
    return index


def enclosing_function(code: str, position: int):
    for func in functions(code):
        if func["start"] <= position <= func["end"]:
            return func
    return None


def colour_setters(code: str) -> list:
    """(enclosing function or None, argument text) for every draw_set_colour call in one module."""
    code = without_strings(code)
    out = []
    for match in SETTER.finditer(code):
        if re.search(r"function\s+$", code[:match.start()]):
            continue
        index = match.end()
        depth = 1
        chars = []
        while index < len(code) and depth:
            char = code[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    break
            chars.append(char)
            index += 1
        out.append((enclosing_function(code, match.start()), "".join(chars).strip()))
    return out


def colour_from_a_role(expression: str, owner, helpers, index, sources, depth=0) -> bool:
    """True when the expression can only be a palette role.

    Accepted: a pp_role_colour call, a call to a function whose every return is a pp_role_colour, or a local variable
    whose every assignment in the same function is one of those. A parameter is accepted only when every call site of
    its function passes such an expression, which is checked here rather than assumed.
    """
    expression = expression.strip()
    if not expression:
        return False
    if "pp_role_colour(" in expression:
        # A role is a colour, not a number to shift: nothing may be added to or scaled from it on the way to the call.
        return not re.search(r"[+\-*/]", expression)
    called = re.match(r"(pp_[a-z0-9_]+)\s*\(", expression)
    if called and called.group(1) in helpers:
        return True
    if not re.fullmatch(r"_[a-z0-9_]+", expression) or owner is None or depth > 2:
        return False

    if expression in owner["params"]:
        position = owner["params"].index(expression)
        calls = []
        for code in sources.values():
            for args in call_arguments(code, owner["name"]):
                calls.append(args[position] if len(args) > position else "")
        if not calls:
            return False
        return all(colour_from_a_role(arg, None, helpers, index, sources, depth + 1) for arg in calls)

    assignments = re.findall(r"(?<![\w.])%s\s*=\s*([^;]+);" % re.escape(expression), owner["body"])
    if not assignments:
        return False
    return all(colour_from_a_role(value, owner, helpers, index, sources, depth + 1) for value in assignments)


def draw_sources(sources: dict) -> dict:
    return {relative: code for relative, code in sources.items()
            if not any(relative.startswith(allowed) for allowed in LITERAL_ALLOWLIST)}


# The title screen is the one screen whose colours do not come from a room palette role: its frame is decided per
# 16 px band by data/palettes/scene_title.json, and every entry there is a 2C02 output, which data/palette.json cannot
# express (it holds no 2C02 colour at all). The role rule cannot see that, and the check that owns the title instead is
# stronger than a role name: tools/nes_composite_check.py reads the game's own captured frames and refuses any pixel
# outside the band palette, and tests/test_title_bands.py composes the frame at five camera positions and runs the same
# check. Card t_a1170172.
ROLE_RULE_EXEMPT = ("game/scripts/pp_title/pp_title.gml",)


def colour_rule_offenders(sources: dict) -> list:
    index = function_index(sources)
    helpers = role_helpers(sources)
    offenders = []
    for relative, code in sorted(draw_sources(sources).items()):
        if relative.replace("\\", "/") in ROLE_RULE_EXEMPT:
            continue
        for owner, expression in colour_setters(code):
            if owner is None:
                offenders.append("%s: draw_set_colour outside a function: %s" % (relative, expression))
                continue
            if not colour_from_a_role(expression, owner, helpers, index, sources):
                offenders.append("%s: %s sets the colour from %s" % (relative, owner["name"], expression))
    return offenders


def test_draw_colour_comes_from_a_palette_role():
    offenders = colour_rule_offenders(gml_sources())
    assert offenders == [], "a draw call sets its colour from something that is not a role:\n" + "\n".join(offenders)


def test_the_colour_rule_fails_on_a_planted_literal():
    planted = ('function pp_draw_thing() {\n'
               '    draw_set_colour(c_black);\n'
               '    draw_rectangle(0, 0, 1, 1, false);\n'
               '}\n')
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(planted)})

    clean = ('function pp_draw_thing() {\n'
             '    draw_set_colour(pp_role_colour("ink"));\n'
             '    draw_rectangle(0, 0, 1, 1, false);\n'
             '}\n')
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(clean)}) == []

    # A local assigned only from a role passes; one assigned from a literal does not.
    local_ok = ('function pp_draw_thing() {\n'
                '    var _c = pp_role_colour("ink");\n'
                '    if (1) _c = pp_role_colour("warn");\n'
                '    draw_set_colour(_c);\n'
                '}\n')
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(local_ok)}) == []
    local_bad = ('function pp_draw_thing() {\n'
                 '    var _c = pp_role_colour("ink");\n'
                 '    _c = make_colour_rgb(1, 2, 3);\n'
                 '    draw_set_colour(_c);\n'
                 '}\n')
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(local_bad)})

    # A function that merely contains a role call is not a colour source.
    not_a_helper = ('function pp_draw_a() {\n    draw_set_colour(pp_role_colour("ink"));\n}\n'
                    'function pp_draw_b() {\n    draw_set_colour(pp_draw_a());\n}\n')
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(not_a_helper)})

    # A role helper is one whose every return is a role.
    helper_ok = ('function pp_kind_colour(_kind) {\n    switch (_kind) {\n'
                 '        case "a": return pp_role_colour("ink");\n'
                 '        default: return pp_role_colour("dim");\n    }\n}\n'
                 'function pp_draw_b() {\n    draw_set_colour(pp_kind_colour("a"));\n}\n')
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(helper_ok)}) == []

    # A role is never shifted into another colour on the way to the call.
    shifted = ('function pp_draw_thing() {\n'
               '    draw_set_colour(pp_role_colour("ink") + 5);\n}\n')
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(shifted)})

    # A parameter passes only when its call sites pass a role.
    helper = 'function pp_draw_text(_c) {\n    draw_set_colour(_c);\n}\n'
    good_call = helper + 'function pp_use() {\n    pp_draw_text(pp_role_colour("ink"));\n}\n'
    bad_call = helper + 'function pp_use() {\n    pp_draw_text(c_red);\n}\n'
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(good_call)}) == []
    assert colour_rule_offenders({"game/scripts/pp_planted/pp_planted.gml": gml_code_only(bad_call)})


def test_the_only_named_colour_constants_are_the_listed_ones():
    config = gml_code_only(read("game/scripts/pp_config/pp_config.gml"))
    found = {name: re.sub(r"\s+", " ", value) for name, value in
             re.findall(r"#macro\s+(PP_[A-Z0-9_]+)\s+(c_[a-z0-9_]+|make_colou?r_rgb\s*\([^)]*\))", config)}
    assert found == NAMED_COLOUR_CONSTANTS, "the named colour constants changed: %s" % sorted(found)

    sources = gml_sources()
    for name, expected_files in NAMED_COLOUR_USERS.items():
        users = tuple(sorted(relative for relative, code in sources.items()
                             if re.search(r"\b%s\b" % name, code) and not relative.endswith("pp_config.gml")))
        assert users == expected_files, "%s is used in %s" % (name, users)


def test_every_role_named_in_draw_code_exists_in_the_master_palette():
    roles = set(read_json_file("data/palette.json")["roles"])
    named = set()
    for _relative, code in gml_sources().items():
        named.update(re.findall(r'pp_role_colour\("([a-z0-9_]+)"\)', code))
    assert named, "no draw code names a role at all, which would mean the sweep is reading nothing"
    missing = sorted(named - roles)
    assert missing == [], "draw code names roles data/palette.json does not declare: %s" % missing


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


# ---------------------------------------------------------------------------------------------------------------
# Item 7: the mutation shown, then reverted.


def test_a_seventeenth_colour_is_refused_and_reverting_clears_it(data_root, read_json, write_json):
    path = data_root / "data" / "room_palettes.json"
    clean = read_json(path)
    assert failures(data_root) == [], "the private copy is not clean before the mutation"

    mutated = copy.deepcopy(clean)
    mutated["sets"][0]["roles"] = SEVENTEEN
    write_json(path, mutated)

    errors = failures(data_root)
    palettes = [e for e in errors if "data/room_palettes.json" in e]
    assert palettes, "a 17th colour was accepted: %s" % errors
    assert any("sets[0]" in e and repr(clean["sets"][0]["id"]) in e and "17 colours" in e and "screen cap is 16" in e
               for e in palettes), palettes
    assert all("data/room_palettes.json" in e for e in errors), "the mutation broke something else as well: %s" % errors

    write_json(path, clean)
    assert failures(data_root) == [], "reverting the mutation did not clear the failure"
