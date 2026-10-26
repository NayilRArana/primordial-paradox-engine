"""R25 TITLE-PATH: the two paths a title menu row can take, pinned where a regression would appear.

Why these are source pins and not a run: GameMaker is not callable from the Python suite, so nothing here pretends
to press a key. What is pinned is the property the card is about, at the level where each defect actually lived:

  1. START opens the menu, and the cursor starts on NEW GAME. The prompt only answered the confirm key, so the pad's
     start did nothing even though the row on screen says PRESS START, and the index was the literal 0 rather than the
     row named NEW GAME.
  2. NEW GAME reaches the crawl, and the crawl ends by starting the run and then taking the route's next step, which
     is the drive once card R21 writes it. A route that does not carry that step yet leaves the new run's own map up.
  3. CONTINUE with a save applies it and moves the frame to the run's room. pp_save_apply rebuilds the saved map and
     puts the hero back on the saved tile, so the landing is pinned where it is implemented, in pp_save, which this
     card may read and may not edit.
  4. CONTINUE with no save is inert (the ready check runs before the apply and returns between them) and dim (the row
     is drawn in the grey the settings placeholder uses, not the white every row used to get).
  5. The attract loop keeps running behind the menu, and the title stops reading keys once the run has been asked for.

Two of the checks are also run against a deliberately broken copy, so a check that reads nothing cannot pass quietly.

Run: python -m pytest tests/test_title_path.py -q
"""

from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE = "game/scripts/pp_title/pp_title.gml"
TITLE_OBJECT = "game/objects/obj_pp_title/Create_0.gml"
SAVE = "game/scripts/pp_save/pp_save.gml"
TITLE_DATA = os.path.join(ROOT, "data", "title.json")

# The save calls the title is allowed to make. It reads the slot, asks whether it holds a run, applies it, and starts a
# new one; it never writes, reads or parses the file itself, because that is pp_save's own business (card R26).
ALLOWED_SAVE_CALLS = {"pp_save_title_start", "pp_save_ready", "pp_save_apply", "pp_save_new_game"}


def code_of(path):
    """The file with its comments removed, so prose that names a function is not read as a call to it."""
    with open(os.path.join(ROOT, path), "r", encoding="utf-8-sig") as handle:
        text = handle.read()
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        lines.append(line if cut == -1 else line[:cut])
    return "\n".join(lines)


def body_of(code, name):
    """The brace balanced body of one function, or an empty string when it is not defined here."""
    match = re.search(r"^function\s+%s\s*\(" % re.escape(name), code, re.MULTILINE)
    if match is None:
        return ""
    start = code.index("{", match.end())
    depth = 0
    for index in range(start, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return code[start:index + 1]
    raise AssertionError("unbalanced body for %s" % name)


def phase_block(step_body, phase, nxt):
    """The lines of one phase branch of pp_title_step, from its opening if to the next phase's opening."""
    start = step_body.find('_s.phase == "%s"' % phase)
    assert start != -1, "pp_title_step has no %s phase" % phase
    end = step_body.find('_s.phase == "%s"' % nxt, start)
    return step_body[start:end if end != -1 else len(step_body)]


def continue_branch(select_body):
    """The CONTINUE arm of pp_title_select, up to the SETTINGS arm."""
    start = select_body.find('_name == "CONTINUE"')
    assert start != -1, "pp_title_select has no CONTINUE arm"
    end = select_body.find('_name == "SETTINGS"', start)
    return select_body[start:end if end != -1 else len(select_body)]


def continue_is_inert(branch):
    """True when the ready check comes first and a row that is not ready leaves before the apply."""
    ready = branch.find("pp_save_ready(")
    apply_at = branch.find("pp_save_apply(")
    if ready == -1 or apply_at == -1 or ready > apply_at:
        return False
    between = branch[ready:apply_at]
    return "return" in between


def continue_is_dim(code):
    """True when the CONTINUE row is drawn as the disabled row when the slot holds no run.

    Card t_a1170172 replaced the grey text tag with a rule through the row in PP_TITLE_DIM, drawn by
    pp_title_draw_disabled, so this pin follows the call and not the removed PP_TITLE_GREY macro.
    """
    words = body_of(code, "pp_title_draw_words")
    return bool(re.search(r'_label\s*==\s*"CONTINUE"\s*&&\s*!_has_save\s*\)\s*\{\s*pp_title_draw_disabled\(\s*_label', words))


def test_start_opens_the_menu_and_the_cursor_starts_on_new_game():
    """The prompt answers the start action, and the cursor is set by the row's name, not by a literal zero."""
    step = body_of(code_of(TITLE), "pp_title_step")
    prompt = phase_block(step, "prompt", "menu")
    assert 'pp_pressed("menu")' in prompt, "PRESS START opens nothing unless the prompt reads the start action"
    assert 'pp_pressed("confirm")' in prompt, "the confirm key must still open the menu"
    assert '_s.phase = "menu"' in prompt
    assert re.search(r'_s\.menu_index\s*=\s*pp_title_menu_index\(\s*_s\s*,\s*"NEW GAME"\s*\)', prompt), (
        "the cursor must start on the row named NEW GAME, not on whatever index 0 happens to be")


def test_the_menu_opens_on_the_new_game_row_by_name():
    """The helper resolves a name, the default table puts NEW GAME first, and the data file cannot silently move it."""
    code = code_of(TITLE)
    helper = body_of(code, "pp_title_menu_index")
    assert "_s.data.menu" in helper and "return i" in helper, "the helper must return the row a name sits on"
    defaults = code[code.find("function pp_title_defaults"):]
    menu = re.search(r'menu:\s*\[(.*?)\]', defaults, re.DOTALL)
    assert menu is not None, "pp_title_defaults must carry the menu table"
    labels = [row.strip().strip('"') for row in menu.group(1).split(",") if row.strip()]
    assert labels[0] == "NEW GAME", "the menu opens on NEW GAME, and NEW GAME is the first row: %s" % labels
    with open(TITLE_DATA, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if "menu" in data:
        assert data["menu"][0] == "NEW GAME", "data/title.json reorders the menu away from NEW GAME first"


def test_new_game_starts_the_crawl():
    """The NEW GAME arm enters the intro phase and builds the crawl from the machine's own beats."""
    select = body_of(code_of(TITLE), "pp_title_select")
    start = select.find('_name == "NEW GAME"')
    arm = select[start:select.find('_name == "CONTINUE"', start)]
    assert '_s.phase = "intro"' in arm
    assert "pp_title_crawl_new(_s)" in arm, "the crawl must be built from pp_text's beats when NEW GAME is chosen"


def test_the_crawl_starts_the_run_and_then_takes_the_routes_next_step():
    """The crawl's end starts a new run and hands to whatever the route says follows the crawl."""
    code = code_of(TITLE)
    intro = body_of(code, "pp_title_step_intro")
    new_game_at = intro.find("pp_save_new_game()")
    handoff_at = intro.find("pp_title_crawl_handoff()")
    assert new_game_at != -1, "the end of the crawl must start the run"
    assert handoff_at > new_game_at, "the route's next step is taken after the run exists, not before"
    handoff = body_of(code, "pp_title_crawl_handoff")
    assert 'pp_slice_route_row("crawl")' in handoff, "the step after the crawl is the route's own row"
    assert "pp_slice_handoff(_next)" in handoff, "the handoff is the app's, so there is one walker and one rule"
    assert "return false" in handoff, "a route step that is not in the build must leave the new run's map standing"
    assert handoff.find("pp_slice_walk_enabled()") < handoff.find("pp_slice_handoff(_next)"), (
        "the demo walk owns every handoff while it is switched on, so the screen must not take this one as well")


def test_continue_without_a_save_is_inert():
    """Choosing CONTINUE with no run does nothing but make the move cue, and it never reaches the apply."""
    assert continue_is_inert(continue_branch(body_of(code_of(TITLE), "pp_title_select"))), (
        "the ready check must come before pp_save_apply and return between them")


def test_the_inert_check_bites():
    """The check above must fail on the defect it exists for: an unguarded apply, and a guard after the apply."""
    unguarded = 'if (_name == "CONTINUE") { pp_audio_play("menu_select"); pp_save_apply(); return; }'
    assert not continue_is_inert(unguarded)
    guard_after = 'if (_name == "CONTINUE") { pp_save_apply(); if (!pp_save_ready()) { return; } return; }'
    assert not continue_is_inert(guard_after)


def test_continue_without_a_save_is_dim():
    """The row is drawn as the disabled row when the slot is empty, and the same row used to get the white."""
    code = code_of(TITLE)
    assert continue_is_dim(code), "the CONTINUE row must be drawn dim when there is no save"
    white_again = code.replace(
        'pp_title_draw_disabled(_label, _cx, _cy);',
        'pp_font_draw_centre(_label, _cx, _cy, 1);')
    assert not continue_is_dim(white_again), "the check must fail on the defect it was written for"


def test_continue_with_a_save_applies_it_and_moves_to_the_runs_room():
    """The load reaches the overworld and the frame moves to the room a run is played in."""
    code = code_of(TITLE)
    branch = continue_branch(body_of(code, "pp_title_select"))
    assert "pp_save_apply()" in branch, "CONTINUE must apply the save it just checked"
    assert 'if (pp_save_apply())' in branch, "a load that failed must not leave the menu"
    assert '_s.phase = "leaving"' in branch, "the title must stop reading keys while the load fades in"
    assert "pp_title_goto_run_room()" in branch, "a load asks for the overworld but does not move the room"
    room = body_of(code, "pp_title_goto_run_room")
    assert "asset_get_index(PP_NEW_GAME_ROOM)" in room, "the run's room is the one the new game room macro names"
    assert "room_goto(_room)" in room


def test_the_saved_map_and_tile_are_what_the_load_lands_on():
    """pp_save_apply is read, not edited: it is the code that puts the map and the tile back (spec 11 rule 5)."""
    apply_body = body_of(code_of(SAVE), "pp_save_apply")
    assert "pp_overworld_new(_d.map, _d.spawn)" in apply_body, "the load builds the saved map at its spawn"
    assert "pp_map_walkable(_world.map, _d.x, _d.y)" in apply_body, "the saved tile is checked before it is used"
    assert "pp_overworld_hero(_d.x, _d.y)" in apply_body, "the hero lands on the saved tile, not on the spawn"
    assert "pp_app_request(PPMode.overworld" in apply_body, "the load asks the app machine for the overworld"


def test_the_title_does_not_own_the_save_slot():
    """One owner per file: the title reads and applies, and never writes, reads or parses the slot itself."""
    code = code_of(TITLE)
    assert "function pp_save_" not in code, "pp_save is card R26's file; this card may not define its functions"
    calls = set(re.findall(r"\b(pp_save_[a-z_]+)\s*\(", code))
    stray = calls - ALLOWED_SAVE_CALLS
    assert stray == set(), "the title reaches past its four save calls: %s" % sorted(stray)


def test_the_attract_loop_keeps_running_behind_the_menu():
    """The scroll advances before any phase branch, so the drive keeps moving while the menu is up."""
    step = body_of(code_of(TITLE), "pp_title_step")
    scroll_at = step.find("_s.scroll +=")
    first_phase = step.find('_s.phase == "open"')
    assert scroll_at != -1 and first_phase != -1
    assert scroll_at < first_phase, "the world must scroll on every step, not only while the prompt is up"


def test_the_title_stops_acting_once_the_run_is_asked_for():
    """Leaving is a phase with its own return, so a second press during the fade cannot start a second run."""
    step = body_of(code_of(TITLE), "pp_title_step")
    leaving_at = step.find('if (_s.phase == "leaving") return;')
    assert leaving_at != -1, "the leaving phase must return rather than fall through to the menu"
    assert leaving_at < step.find('_s.phase == "menu"'), "the guard must sit before the phases that read a key"


def test_the_title_object_enters_the_screen_once():
    """One place builds the screen's state: the enter call. A second build is what left a phase-less struct behind."""
    create = code_of(TITLE_OBJECT)
    assert "pp_title_enter({})" in create
    assert "pp_title_state_new()" not in create, "the state is made in pp_title_enter, not a second time in Create"


# Card DEMO-WALK. The day 1 video is the run room's free walk, and the game's own route hands the crawl to the drive
# scene, which owns the screen for 178 s and pages twelve captions that each wait for a press. So the recording holds
# that one route step: the crawl resolves the step the route names, is told it is held, and leaves the run room
# standing. These pins hold the switch to that shape, and hold the script and the route to the same step id.

DEMO_SCRIPT = os.path.join(ROOT, "data", "demo", "run_001.json")
SLICE = os.path.join(ROOT, "data", "slice.json")


def test_a_held_route_step_leaves_the_run_room_standing():
    """The held check sits on the resolved route id and returns before any handoff is taken."""
    code = code_of(TITLE)
    handoff = body_of(code, "pp_title_crawl_handoff")
    held_at = handoff.find("pp_title_route_held(_next_id)")
    assert held_at != -1, "the handoff must ask whether the route's next step is held in this run"
    assert held_at < handoff.find("pp_slice_handoff(_next)"), (
        "the held check must come before the handoff, or the drive scene is asked for and runs anyway")
    assert handoff.find("pp_title_route_held(_next_id)") > handoff.find('pp_slice_route_row("crawl")'), (
        "the id that is held is the route's own next step, not a name written into the screen")


def test_the_held_switch_is_one_environment_name_and_empty_means_take_the_step():
    """PP_ROUTE_HOLD is split like every other PP_ name, and an unset value takes the route as the file says."""
    code = code_of(TITLE)
    assert '#macro PP_ROUTE_HOLD "PP_" + "ROUTE_HOLD"' in code, "the environment name is split, not written whole"
    helper = body_of(code, "pp_title_route_held")
    assert "environment_get_variable(PP_ROUTE_HOLD)" in helper
    assert 'if (_held == "") return false;' in helper, "an unset switch must take the step, never hold it"
    assert "string_split(_held" in helper, "the switch names one id or a comma separated list of them"


def test_the_demo_script_holds_the_step_the_route_actually_names_after_the_crawl():
    """The script's switch and data/slice.json cannot drift: the id the script holds is the crawl's own next step."""
    with open(DEMO_SCRIPT, "r", encoding="utf-8") as handle:
        script = json.load(handle)
    with open(SLICE, "r", encoding="utf-8") as handle:
        route = json.load(handle)["route"]
    env = (script.get("game") or {}).get("env") or {}
    held = [part.strip() for part in str(env.get("PP_ROUTE_HOLD", "")).split(",") if part.strip()]
    rows = {row["id"]: row for row in route["steps"]}
    assert held, "data/demo/run_001.json sets PP_ROUTE_HOLD, so the recording's path is stated in the script"
    assert route["first"] in rows and "crawl" in rows, "the route the script relies on has a crawl row"
    crawl_next = rows["crawl"].get("next", "")
    for identifier in held:
        assert identifier in rows, "the script holds %r, which data/slice.json does not have" % identifier
        assert identifier == crawl_next, (
            "the script holds %r but the route hands the crawl to %r, so the hold would not take"
            % (identifier, crawl_next))
