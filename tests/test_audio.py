"""Tests for the audio bus contract: data\\audio.json, game\\scripts\\pp_audio\\pp_audio.gml and the checker.

What is pinned here, and why each pin earns its place:
  - the cue table holds exactly the ids card G0-2T names, one row each, with a title, an asset
    name, a loop flag and a placeholder flag, so a rename cannot detach the musician's music
    from the game without a red test;
  - every cue id asked for by a map, a scene or an encounter is a row in that table, and the
    rows nothing asks for are the recorded list, not an accident;
  - the crossfade is the macro 30, not three literals, and the priorities are the spec numbers;
  - focus handling is the documented engine call, made in exactly one place, and routed through
    pp_audio_focus;
  - check_data refuses a cue id no row defines, on a private copy of data\\.

Honest limits. There is no data\\music directory and no pp_*.ogg anywhere in the tree, so no cue
has a file to play; GameMaker is not installed, so nothing here compiles, runs or is heard. What
is proved is the contract between the data, the module text and the checker. The sound is
unproven, and this file does not claim anything is audible.

Four defects this file records rather than hides, all reported on card t_0c5dc024:
  1. The musician's round 1 note (section 4) lists seventeen cue ids and the table holds fourteen.
     The three missing rows are PP-03 Harbor, PP-04 Navy Sailors and PP-13 Titan Employees. The
     card's own id list also leaves them out, so the table matches the card and not the note.
  2. Eleven of the fourteen rows are asked for by no map, scene or encounter, and data\\audio.json
     has no "unused" marker to say so on purpose. Card item 2's second half needs a data decision.
  3. The placeholder stand-in a cue names can never play: pp_audio_music hands it to pp_audio_play,
     which refuses every name that is not in pp_audio_cues(), and none of the three stand-ins is.
  4. Focus is polled once per step from pp_audio_step, not delivered as an event, because the
     engine documents no Windows focus event. Recorded in the focus tests and on the card.
"""

from __future__ import annotations

import json
import os
import re

import check_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.dirname(os.path.dirname(ROOT))
DATA = os.path.join(ROOT, "data")
MODULE = os.path.join(ROOT, "game", "scripts", "pp_audio", "pp_audio.gml")
STEP_EVENT = os.path.join(ROOT, "game", "objects", "obj_pp_game", "Step_0.gml")
SPEC = os.path.join(ROOT, "specs", "12-audio.md")
MUSICIAN = os.path.join(SHARED, "notes", "notebook-2026-10-19", "round1", "musician.md")

# The ids card G0-2T names, in the card's order. Not the musician's full list: this module's
# docstring names the three ids his note has and this table does not.
CARD_CUE_IDS = [
    "PP-01", "PP-02", "PP-05", "PP-06", "PP-07", "PP-08", "PP-09",
    "PP-10", "PP-11", "PP-12", "PP-14", "PP-15a", "PP-15b", "PP-16",
]

# The rows no map, scene or encounter asks for today. Pinned exactly so a row added to or dropped
# from the table cannot slip into or out of this list unnoticed. This is a recorded gap, not an
# approval: data\\audio.json has no field that marks a cue unused on purpose.
RECORDED_UNREFERENCED = [
    "PP-01", "PP-02", "PP-08", "PP-09", "PP-10", "PP-11", "PP-12",
    "PP-14", "PP-15a", "PP-15b", "PP-16",
]

# The musician's ids his round 1 note carries and the table does not. Same meaning as above.
RECORDED_MUSICIAN_GAP = ["PP-03", "PP-04", "PP-13"]

CUE_ID_RE = re.compile(r"^PP-[0-9]{2}[ab]?$")


def _text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _code(text):
    """The module with its comment tails removed, so a literal quoted in a comment is not a use.

    Every claim below about a number or a call is about code the compiler would see. The module
    is heavily commented (the manual citations live there), and a comment naming the fade time
    must not be able to satisfy a test about the fade macro.
    """
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _macro(code, name):
    match = re.search(r"^#macro\s+%s\s+(\S+)" % re.escape(name), code, re.MULTILINE)
    return match.group(1) if match else None


def _cue_rows():
    return _read(os.path.join(DATA, "audio.json"))["cues"]


def _cue_ids():
    return [row.get("id") for row in _cue_rows()]


def _musician_ids():
    """The cue ids the musician's note carries, read from its own tables (rows that start "| PP-")."""
    ids = set()
    for line in _text(MUSICIAN).splitlines():
        match = re.match(r"^\|\s*(PP-[0-9]{2}[ab]?)\b", line)
        if match:
            ids.add(match.group(1))
    return ids


def _music_references():
    """Every music reference in the data, as (file, path, id).

    The three shapes the game actually reads: a map row's "music", an encounter's "music", and a
    scene command {"cmd": "music", "id": ...}. A reference may still be an old sound id during the
    handover, so only cue shaped ids are compared against the cue table here; check_data decides
    whether a non cue id is a music entry.
    """
    refs = []
    for name in ("maps/all.json", "maps/ship_sample.json"):
        data = _read(os.path.join(DATA, name))
        for index, row in enumerate(data.get("maps", [])):
            music = row.get("music")
            if isinstance(music, str) and music:
                refs.append((name, "maps[%d].music" % index, music))
    data = _read(os.path.join(DATA, "encounters", "all.json"))
    for index, row in enumerate(data.get("encounters", [])):
        music = row.get("music")
        if isinstance(music, str) and music:
            refs.append(("encounters/all.json", "encounters[%d].music" % index, music))
    data = _read(os.path.join(DATA, "scenes", "all.json"))
    for index, scene in enumerate(data.get("scenes", [])):
        for step, command in enumerate(scene.get("commands", [])):
            if isinstance(command, dict) and command.get("cmd") == "music":
                refs.append(("scenes/all.json",
                             "scenes[%d].commands[%d].id" % (index, step), command.get("id")))
    return refs


# --- item 1: the table is exactly the ids the card names, fully filled in ---------------------------------------

def test_cue_table_is_exactly_the_fourteen_ids_the_card_names():
    """No more and no fewer. Sorting on both sides means a reordered table is fine and a renamed,
    added or dropped id is not: that is the failure a silent detach of the musician's music from
    the game would otherwise be."""
    ids = _cue_ids()
    assert len(ids) == 14
    assert sorted(ids) == sorted(CARD_CUE_IDS)
    assert all(CUE_ID_RE.match(row_id) for row_id in ids), "every id must look like PP-01 or PP-15a"


def test_every_cue_row_carries_title_asset_loop_and_placeholder():
    """The four fields the bus and the loader read. An asset is a bare lowercase name because the
    loader appends .ogg, and placeholder is required because no cue has a file yet: a row without
    it would claim an OGG the build does not ship."""
    for row in _cue_rows():
        where = row.get("id", "<no id>")
        assert isinstance(row.get("title"), str) and row["title"].strip(), "%s has no title" % where
        asset = row.get("asset")
        assert isinstance(asset, str) and asset, "%s has no asset name" % where
        assert not asset.lower().endswith(".ogg"), "%s asset must be a bare name, not a file" % where
        assert re.fullmatch(r"[a-z0-9_]+", asset), "%s asset is not a lowercase name" % where
        assert isinstance(row.get("loop"), bool), "%s loop must be a boolean" % where
        assert isinstance(row.get("placeholder"), bool), "%s placeholder must be a boolean" % where
        assert row["placeholder"] is True, "%s claims a delivered OGG and none exists" % where
    assets = [row["asset"] for row in _cue_rows()]
    assert len(set(assets)) == len(assets), "two cues would load the same file"


def test_the_bus_reads_that_table_and_refuses_an_id_it_does_not_hold():
    """The table is only a contract if the module loads it. Both halves are read from the module
    text: the registry comes from audio.json's cues, and an unregistered id returns undefined
    rather than a made up entry."""
    code = _code(_text(MODULE))
    assert 'pp_data_json("audio.json")' in code
    assert "pp_data_index(_data.cues)" in code
    assert "function pp_audio_cue(_id)" in code
    assert "variable_struct_exists(_reg, _id)" in code


def test_no_cue_id_was_invented_against_the_musicians_note():
    """Every id in the table is one the musician actually wrote in his round 1 note, which is the
    point of using his labels: a code side name would be a name he never chose."""
    invented = sorted(set(_cue_ids()) - _musician_ids())
    assert invented == [], "cue ids the musician never wrote: %s" % invented


def test_the_placeholder_stand_in_cannot_reach_a_playable_effect():
    """DEFECT, reported on card t_0c5dc024. Three cues name a stand-in for the months before their
    OGG arrives (PP-05 ship_ambient, PP-06 battle_percy, PP-07 pp_07_prometheus). pp_audio_music
    hands that name to pp_audio_play, which first refuses any name not in pp_audio_cues(), and that
    list is the effect names only: no music id is in it. So the stand-in path is dead, the cue logs
    "unknown cue" and stays silent, and the sfx manifest could not have helped either because it
    holds the effect set. Pinned so the dead path is visible; the fix is a game code change this
    card may not make."""
    code = _code(_text(MODULE))
    effects_block = code.split("function pp_audio_cues()", 1)[1].split("]", 1)[0]
    effects = set(re.findall(r'"([A-Za-z0-9_]+)"', effects_block))
    stand_ins = {row["placeholder_sound"] for row in _cue_rows() if row.get("placeholder_sound")}
    assert stand_ins == {"ship_ambient", "battle_percy", "pp_07_prometheus"}
    assert sorted(stand_ins - effects) == ["battle_percy", "pp_07_prometheus", "ship_ambient"]
    assert "pp_audio_play(_entry.placeholder_sound);" in code, "the stand-in is routed through pp_audio_play"
    assert code.index("if (!_is_cue)") < code.index("_a.entries[$ _cue]"), \
        "the unknown name is refused before the manifest is consulted"


def test_the_three_musician_cues_missing_from_the_table_are_the_recorded_gap():
    """DEFECT, reported on card t_0c5dc024. The note lists seventeen ids; the table holds fourteen.
    PP-03 Harbor, PP-04 Navy Sailors and PP-13 Titan Employees have no row, so when their OGGs
    arrive there is nowhere for them to land. The card's own list also leaves them out, so this is
    a card and data decision, not something a test may fix. Pinned so the gap cannot grow or
    shrink without a red test."""
    assert sorted(_musician_ids() - set(_cue_ids())) == RECORDED_MUSICIAN_GAP


# --- item 2: every reference resolves, and every row is accounted for -------------------------------------------

def test_every_music_reference_in_the_data_resolves_to_a_cue_row():
    refs = _music_references()
    assert len(refs) >= 5, "the reference walk found almost nothing, so the test would be vacuous"
    table = set(_cue_ids())
    unresolved = [(name, path, ref) for name, path, ref in refs
                  if isinstance(ref, str) and ref.startswith("PP-") and ref not in table]
    assert unresolved == [], "cue ids asked for by the data and not in the table: %s" % unresolved


def test_unreferenced_cue_rows_are_the_recorded_debt_list():
    """DEFECT, reported on card t_0c5dc024. Card item 2 wants every row reachable from a reference
    or marked unused on purpose, and data\\audio.json has no such marker, so eleven rows are simply
    unreferenced: the boss themes, the endings and the opening cues are not asked for by any map,
    scene or encounter yet. The exact set is pinned so the state is visible and cannot drift
    silently; the fix is a reference or an unused flag in the data, which this card may not add."""
    referenced = {ref for _name, _path, ref in _music_references()
                  if isinstance(ref, str) and ref.startswith("PP-")}
    assert referenced, "no cue is referenced at all, so this test proves nothing"
    unreferenced = sorted(set(_cue_ids()) - referenced)
    assert unreferenced == RECORDED_UNREFERENCED


# --- item 3: the crossfade is one macro of 30 steps -------------------------------------------------------------

def test_crossfade_is_thirty_steps_from_one_macro():
    """Spec 12 rule 4 decides 30 steps. Three literal 30s in the module would drift apart, so the
    number lives once in PP_AUDIO_FADE_STEPS and the code asks for the macro."""
    code = _code(_text(MODULE))
    assert _macro(code, "PP_AUDIO_FADE_STEPS") == "30"
    body = re.sub(r"^#macro\s+PP_AUDIO_FADE_STEPS\s+30\s*$", "", code, flags=re.MULTILINE)
    stray = re.findall(r"(?<![\w.])30(?![\w])", body)
    assert stray == [], "the fade time is written as a literal %d more time(s) beside the macro" % len(stray)
    assert code.count("PP_AUDIO_FADE_STEPS") >= 3, "the macro must be used, not only declared"
    assert "30 steps" in _text(SPEC), "spec 12 is the source of the number"


# --- item 4: the priorities the spec decides, read from the module text ----------------------------------------

def test_priorities_are_boss_12_sfx_5_ui_4():
    code = _code(_text(MODULE))
    assert _macro(code, "PP_AUDIO_PRI_BOSS") == "12"
    assert _macro(code, "PP_AUDIO_PRI_SFX") == "5"
    assert _macro(code, "PP_AUDIO_PRI_UI") == "4"
    assert _macro(code, "PP_AUDIO_PRI_MUSIC") == "10"
    assert "_priority = PP_AUDIO_PRI_BOSS" in code, "a boss cue must be given the boss priority"
    assert "variable_struct_exists(_entry, \"boss\")" in code
    assert "_priority = PP_AUDIO_PRI_UI" in code
    assert "_priority = PP_AUDIO_PRI_SFX" in code


# --- item 5: focus handling through the documented engine call -------------------------------------------------

def test_focus_is_the_documented_engine_call_made_in_one_place():
    """window_has_focus is the call, from the manual page
    Cameras_And_Display/The_Game_Window/window_has_focus.htm, which the module cites. One call site
    in the whole game tree: a second poll somewhere else is how the pause rule gets half applied."""
    hits = []
    for base, _dirs, files in os.walk(os.path.join(ROOT, "game")):
        for name in files:
            if name.endswith(".gml"):
                path = os.path.join(base, name)
                if "window_has_focus" in _code(_text(path)):
                    hits.append(os.path.relpath(path, ROOT).replace(os.sep, "/"))
    assert hits == ["game/scripts/pp_audio/pp_audio.gml"], "focus is polled in: %s" % hits
    module = _text(MODULE)
    assert "pp_audio_focus(!window_has_focus());" in _code(module)
    assert "window_has_focus.htm" in module, "the call must name the manual page it came from"


def test_focus_pauses_the_music_and_stops_the_effects_and_resumes_where_it_stopped():
    """Spec 12 rule 8: losing focus pauses music and stops SFX, regaining it resumes the music where
    it stopped. The module does that with audio_pause_sound and audio_resume_sound on the music
    instance, which the manual says resumes from the paused position, and by stopping each recorded
    effect instance."""
    code = _code(_text(MODULE))
    assert "function pp_audio_focus(_paused)" in code
    assert "audio_pause_sound(_a.music_inst)" in code
    assert "audio_resume_sound(_a.music_inst)" in code
    assert "audio_is_playing(_a.sfx_insts[i])" in code, "an effect must be checked before it is stopped"
    assert "audio_stop_sound(_a.sfx_insts[i])" in code
    assert "pp_audio_focus(!window_has_focus());" in code, "nothing would ever call the focus rule"


def test_focus_runs_from_the_step_path_because_the_engine_has_no_windows_focus_event():
    """The deviation from card item 5, pinned so it is visible in review and not only in a summary.

    The card asked for a real focus event rather than a poll of the window inside Step. The manual's
    Object Events and Other Events pages list no focus event, and the Async System page's onResume
    is for mobile targets only, so on Windows there is no event to subscribe to: window_has_focus is
    documented on its own page as a poll ("With this function you can poll the window (or tab)
    state"). The build therefore polls once per step from pp_audio_step, called by obj_pp_game's
    Step event. Recorded as a defect for the gamedev lane to rule on: either the card's wording
    changes or the game accepts the poll, which is what the engine offers.
    """
    assert "pp_audio_step();" in _code(_text(STEP_EVENT))
    code = _code(_text(MODULE))
    assert "function pp_audio_step()" in code
    assert "pp_audio_focus(!window_has_focus());" in code


# --- item 6: check_data refuses a cue id no row defines ---------------------------------------------------------

def test_check_data_refuses_an_unknown_cue_id_in_a_map(data_root, read_json, write_json):
    """A room pointed at a cue nobody registered is silent at runtime and says nothing. The checker
    must name the id and the field, on a private copy of data\\ so the real file is untouched."""
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    data["maps"][0]["music"] = "PP-99"
    write_json(path, data)

    errors = check_data.check(str(data_root))
    assert any("unknown sound or cue id 'PP-99'" in error and "maps[0].music" in error
               for error in errors), errors


def test_check_data_refuses_an_unknown_cue_id_in_a_scene(data_root, read_json, write_json):
    path = data_root / "data" / "scenes" / "all.json"
    data = read_json(path)
    for command in data["scenes"][0]["commands"]:
        if command.get("cmd") == "music":
            command["id"] = "PP-98"
            break
    else:
        raise AssertionError("the first scene has no music command to break")
    write_json(path, data)

    errors = check_data.check(str(data_root))
    assert any("unknown sound or cue id 'PP-98'" in error and "commands" in error
               for error in errors), errors


def test_check_data_refuses_an_unknown_cue_id_in_an_encounter(data_root, read_json, write_json):
    path = data_root / "data" / "encounters" / "all.json"
    data = read_json(path)
    data["encounters"][0]["music"] = "PP-97"
    write_json(path, data)

    errors = check_data.check(str(data_root))
    assert any("unknown sound or cue id 'PP-97'" in error and "encounters[0].music" in error
               for error in errors), errors
