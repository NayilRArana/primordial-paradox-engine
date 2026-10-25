"""Tests for the audio bus contract: data\\audio.json, game\\scripts\\pp_audio\\pp_audio.gml and the checker.

What is pinned here, and why each pin earns its place:
  - the cue table holds exactly the musician's seventeen ids, one row each, with a title, an asset
    name, a loop flag and a placeholder flag, so a rename cannot detach the musician's music
    from the game without a red test;
  - every cue id asked for by a map, a scene or an encounter is a row in that table, and the
    rows nothing asks for are the recorded list, not an accident;
  - the crossfade is the macro 30, not three literals, and the priorities are the spec numbers;
  - focus handling is the documented engine call, made in exactly one place, and routed through
    pp_audio_focus;
  - check_data refuses a cue id no row defines, on a private copy of data\\.

Honest limits. There is no data\\music directory and no pp_*.ogg anywhere in the tree, so no cue
has a file to play. GameMaker builds this tree and the build log shows the module loading and
playing, but no test below listens to a speaker: what is pinned is the contract between the data,
the module text and the checker. Anything about how it sounds is unproven and said so.

Defects this file still records rather than hides:
  1. Thirteen of the seventeen rows are asked for by no map, scene or encounter, and data\\audio.json
     has no "unused" marker to say so on purpose. Card item 2's second half needs a data decision.
  2. The placeholder stand-in a cue names can never play: pp_audio_music hands it to pp_audio_play,
     which refuses every name that is not in pp_audio_cues(), and none of the three stand-ins is.
  3. Focus is polled once per step from pp_audio_step, not delivered as an event, because the
     engine documents no Windows focus event. Recorded in the focus tests and on the card.
The seventeen ids the musician's round 1 note carries are all in the table now, so the shortfall
the review returned on card t_8de1aca9 is closed and pinned by a test instead of documented.
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
TEXT_MODULE = os.path.join(ROOT, "game", "scripts", "pp_text", "pp_text.gml")
MUSICIAN = os.path.join(SHARED, "notes", "notebook-2026-10-19", "round1", "musician.md")

# The musician's seventeen ids, in the order his note lists them and the table holds them. The
# card's own list had fourteen; the gate card (t_8de1aca9 item 2) asks for his ids exactly, so
# PP-03, PP-04 and PP-13 are rows now and this list is the note, not the card.
CUE_IDS = [
    "PP-01", "PP-02", "PP-03", "PP-04", "PP-05", "PP-06", "PP-07", "PP-08", "PP-09",
    "PP-10", "PP-11", "PP-12", "PP-13", "PP-14", "PP-15a", "PP-15b", "PP-16",
]

# The rows no map, scene or encounter asks for today. Pinned exactly so a row added to or dropped
# from the table cannot slip into or out of this list unnoticed. This is a recorded gap, not an
# approval: data\\audio.json has no field that marks a cue unused on purpose.
#
# PP-03 (Harbor) left this list on 2026-10-23, card t_6b4724a9. Three references appeared for it:
# data\\maps\\all.json gives "music": "PP-03" to southampton_town_quay and to quay_dock_office, and
# data\\scenes\\all.json opens quay_gate_checkpoint with {"cmd": "music", "id": "PP-03"}. The row's own
# note in data\\audio.json calls it "the arrival and gate cue", which is exactly those three places,
# and assets\\audio\\pp_03_harbor\\pp_03_harbor.ogg is on disk, so the references are intended and the
# pin moves, not the data. Those three references are working tree changes, not committed ones: this
# pin only holds at HEAD once they are committed, and it must ride in the same commit as them.
# PP-02 (The Drive) left this list on 2026-10-24, card t_e8a8f18a. Two references appeared for it:
# data\\maps\\all.json gives "music": "PP-02" to the drive_m4_corridor row, and data\\scenes\\all.json opens
# drive_to_southampton with {"cmd": "music", "id": "PP-02"}. The row's own note in data\\audio.json calls it
# "The Drive", assets\\audio\\pp_drive\\NOTES-v3.md prints this film's eleven hard cuts on its downbeats at 125
# bars, and the scene sums to exactly the 10,680 steps that cue is scored for, so the references are intended
# and the pin moves, not the data. The two references ride in the same commit as this pin.
# The eleven that remain, and why each is still unreferenced:
#   PP-01  delivered and scored, but the title path streams it by file name through
#          pp_audio_play_theme, so no map, scene or encounter asks for the id. It needs a title
#          scene command, which is a data change this pin cannot make for it.
#   PP-08  not composed. No assets\\audio\\pp_08_dead_rising folder; the row falls back to PP-03.
#   PP-09  not composed. No assets\\audio\\pp_09_data_center folder; falls back to PP-03.
#   PP-10  not composed. Boss row with no folder; falls back to PP-06 so the fight keeps priority 12.
#   PP-11  not composed. No folder; falls back to PP-02.
#   PP-12  not composed. No folder; falls back to PP-03.
#   PP-13  not composed. No folder; falls back to PP-03. The row exists so the musician's own id in
#          notes\\notebook-2026-10-19\\round1\\musician.md has a home in the table.
#   PP-14  not composed. Boss row with no folder; falls back to PP-06.
#   PP-15a not composed. The genocide ending; falls back to PP-01.
#   PP-15b not composed. The mercy ending; falls back to PP-01.
#   PP-16  not composed. No folder; falls back to PP-01.
RECORDED_UNREFERENCED = [
    "PP-01", "PP-08", "PP-09", "PP-10", "PP-11", "PP-12",
    "PP-13", "PP-14", "PP-15a", "PP-15b", "PP-16",
]

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


def _function(text, name):
    """The body of one function, brace balanced, so a claim about a call is about that function.

    A whole module search cannot tell a call in pp_audio_focus from one in pp_audio_music, and
    three of the fixes on this card are about which function does what.
    """
    code = _code(text)
    start = code.index("function %s(" % name)
    depth = 0
    for offset, character in enumerate(code[start:]):
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return code[start:start + offset + 1]
    raise AssertionError("no balanced body for %s" % name)


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

def test_cue_table_is_exactly_the_seventeen_ids_the_musician_wrote():
    """No more and no fewer. Sorting on both sides means a reordered table is fine and a renamed,
    added or dropped id is not: that is the failure a silent detach of the musician's music from
    the game would otherwise be."""
    ids = _cue_ids()
    assert len(ids) == 17
    assert sorted(ids) == sorted(CUE_IDS)
    assert sorted(ids) == sorted(_musician_ids()), "the table and the musician's own list disagree"
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


def test_the_three_cues_the_card_left_out_are_rows_with_the_musicians_own_assets():
    """The shortfall card t_8de1aca9 item 2 returned. PP-03 Harbor, PP-04 Navy Sailors and PP-13 Titan
    Employees had no row, so the day their OGGs arrived there was nowhere for them to land. Each is a
    row now, with the title the note's table writes and the asset name the loader will append .ogg to.
    PP-04 is the tutorial fight cue, so the encounter points at it instead of the old sound id."""
    rows = {row["id"]: row for row in _cue_rows()}
    wanted = {
        "PP-03": ("Harbor", "pp_03_harbor"),
        "PP-04": ("Navy Sailors", "pp_04_navy_sailors"),
        "PP-13": ("Titan Employees", "pp_13_titan_employees"),
    }
    for cue, (title, asset) in wanted.items():
        assert cue in rows, "%s is missing from the cue table" % cue
        assert rows[cue]["title"] == title
        assert rows[cue]["asset"] == asset
        assert rows[cue]["loop"] is True
        assert rows[cue]["placeholder"] is True
        assert rows[cue]["placeholder_sound"] is None
    assert sorted(_musician_ids() - set(_cue_ids())) == [], "the note still has a cue the table cannot hold"
    encounter = [row for row in _read(os.path.join(DATA, "encounters", "all.json"))["encounters"]
                 if row.get("id") == "tutorial_sailors"]
    assert encounter and encounter[0]["music"] == "PP-04", "the tutorial fight must ask for its own cue id"


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
    silently; the fix is a reference or an unused flag in the data, which this card may not add.
    The pin moved once, on 2026-10-23 (card t_6b4724a9): PP-03 left it when the quay maps and the
    gate checkpoint scene gained their PP-03 music reference, and the list explains each row that
    is still on it. It moved a second time, on 2026-10-24 (card t_e8a8f18a): PP-02 left it when the
    drive corridor map row and the drive scene named it as their music."""
    referenced = {ref for _name, _path, ref in _music_references()
                  if isinstance(ref, str) and ref.startswith("PP-")}
    assert referenced, "no cue is referenced at all, so this test proves nothing"
    unreferenced = sorted(set(_cue_ids()) - referenced)
    assert unreferenced == RECORDED_UNREFERENCED, (
        "the unreferenced set moved: newly unreferenced %s, newly referenced %s"
        % (sorted(set(unreferenced) - set(RECORDED_UNREFERENCED)),
           sorted(set(RECORDED_UNREFERENCED) - set(unreferenced))))


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


# --- item 2: the blip the game plays goes through the blip function ----------------------------------------------

def test_the_text_reveal_plays_its_blip_through_pp_audio_blip():
    """Spec 12 rule 6 wants a blip at 0.5 of the effect level and rule 2 wants a UI sound at priority
    4. pp_audio_blip is the one place those two numbers are applied. pp_text used to build the blip
    cue and hand it to pp_audio_play, the effect path at priority 5 and the full level, so the rule
    was written and never called; the build log showed pp_audio_play's own "played, instance" line
    for text_blip_a. The call site is read here, and the old one must be gone from the whole file."""
    text = _text(TEXT_MODULE)
    assert "pp_audio_blip(_rv.speaker);" in _code(text), "the reveal must call pp_audio_blip"
    assert "pp_audio_play(pp_audio_blip_cue(" not in _code(text), "the old effect path call is back"
    module = _text(MODULE)
    blip = _function(module, "pp_audio_blip")
    assert 'pp_audio_sfx("ui", _cue)' in blip, "a blip is a UI sound, priority 4 (rule 2)"
    assert "PP_AUDIO_GAIN_SFX * PP_AUDIO_GAIN_BLIP" in blip, "a blip is half the effect level (rule 6)"


# --- item 3: one music source, and focus reaches the one that is playing ----------------------------------------

def test_the_title_theme_is_handed_to_the_fade_before_a_cue_starts():
    """The theme was a second music source: its own instance, untouched by pp_audio_music, by the
    stop and by focus. The build log showed "focus lost, music paused" while the only music playing
    was the theme, at instance 400001, and music_inst was -1. So a cue start now hands a live theme
    to the fade slot, and the theme's own stream goes with it to be destroyed."""
    music = _function(_text(MODULE), "pp_audio_music")
    assert "pp_audio_theme_release(_a, _fade_ms);" in music
    assert music.index("pp_audio_theme_release") < music.index("audio_create_stream"), \
        "the theme must be released before the incoming track starts"
    release = _function(_text(MODULE), "pp_audio_theme_release")
    assert "pp_audio_fade_handoff(_a, _a.theme_inst, _stream, _fade_ms);" in release
    assert "_a.theme_inst = -1;" in release, "a released theme must not be addressed again"
    stop = _function(_text(MODULE), "pp_audio_music_stop")
    assert "pp_audio_theme_release(_a, _fade_ms)" in stop, "a stop must silence the theme too"


def test_focus_pauses_and_resumes_both_music_slots():
    """Spec 12 rule 8 is about the music that is playing, not about the cue slot. Both instances are
    paused, and both are resumed where they stopped."""
    focus = _function(_text(MODULE), "pp_audio_focus")
    assert "audio_pause_sound(_a.music_inst)" in focus
    assert "audio_pause_sound(_a.theme_inst)" in focus
    assert "audio_resume_sound(_a.music_inst)" in focus
    assert "audio_resume_sound(_a.theme_inst)" in focus


def test_the_theme_plays_at_the_music_level_and_a_duck_multiplies_it():
    """The theme started at the engine default gain of 1.0 while every other track started at 0.7, so
    the title was louder than the game. It now starts at the music level, and the duck and unduck
    multiply that level instead of replacing it with 1.0 on the way back."""
    module = _text(MODULE)
    assert _macro(_code(module), "PP_AUDIO_GAIN_MUSIC") == "0.7"
    theme = _function(module, "pp_audio_play_theme")
    assert "audio_play_sound(_stream, PP_AUDIO_PRI_MUSIC, true, _gain)" in theme
    assert "var _gain = PP_AUDIO_GAIN_MUSIC;" in theme
    duck = _function(module, "pp_audio_duck_db")
    assert "PP_AUDIO_GAIN_MUSIC * power(10, _db / 20)" in duck
    unduck = _function(module, "pp_audio_unduck")
    assert "audio_sound_gain(_a.theme_inst, PP_AUDIO_GAIN_MUSIC, 0)" in unduck
    assert "audio_sound_gain(_a.theme_inst, 1, 0)" not in _code(module), "the theme can never jump to 1.0"


def test_the_theme_can_start_again_once_a_cue_has_released_it():
    """pp_audio_theme_release hands the theme to the fade and then leaves theme_inst in the state at
    -1, so a guard that only asks whether the key exists answers "a theme is already playing" for
    the rest of the run. That is what pp_audio_play_theme did while duck and unduck in the same
    module already tested <= -1, so a return to the title after a cue would have been silent and
    logged nothing at all. Absent and released are the same answer, in all three functions."""
    module = _text(MODULE)
    released = _function(module, "pp_audio_theme_release")
    assert "_a.theme_inst = -1;" in released, "a released theme is left in the state at -1"
    for name in ("pp_audio_play_theme", "pp_audio_duck_db", "pp_audio_unduck"):
        body = _function(module, name)
        assert 'variable_struct_exists(_a, "theme_inst") || _a.theme_inst <= -1' in body, \
            "%s must treat an absent theme and a released theme the same way" % name


# --- item 7: a fast change cannot orphan a stream ---------------------------------------------------------------

def test_a_second_fade_finishes_the_first_so_no_stream_is_orphaned():
    """audio_create_stream.htm warns that a stream which is never destroyed leaks and eventually
    crashes the game. The fade slot holds one instance and one stream, so a third cue or a stop
    inside the 500 ms window used to overwrite the pending pair and orphan the first stream. The
    handoff now flushes what is there first, and the step finishes a fade through the same call."""
    module = _text(MODULE)
    handoff = _function(module, "pp_audio_fade_handoff")
    assert "pp_audio_fade_flush(_a);" in handoff
    assert handoff.index("pp_audio_fade_flush") < handoff.index("_a.fade_inst = _inst;")
    flush = _function(module, "pp_audio_fade_flush")
    assert "audio_stop_sound(_a.fade_inst);" in flush
    assert "audio_destroy_stream(_a.fade_stream)" in flush
    step = _function(module, "pp_audio_step")
    assert "pp_audio_fade_flush(_a)" in step, "the step must finish a fade through the same call"
    code = _code(module)
    assert "_a.fade_inst = _a.music_inst;" not in code, "the fade slot is written by the helper only"
    assert "_a.fade_stream = _a.music_stream;" not in code, "the fade slot is written by the helper only"


# --- item 4: every audio call names the manual page it came from ------------------------------------------------

def test_every_audio_call_names_the_manual_page_it_came_from():
    """The review found three calls with no page named: audio_is_playing, audio_create_buffer_sound
    and the audio_mono / audio_stereo constants. A count in prose drifted too ("all six pages" while
    eight were named), so the header names the pages and no longer counts them."""
    text = _text(MODULE)
    for page in ("audio_play_sound.htm", "audio_sound_gain.htm", "audio_pause_sound.htm",
                 "audio_resume_sound.htm", "audio_stop_sound.htm", "audio_is_playing.htm",
                 "audio_channel_num.htm", "audio_create_stream.htm",
                 "audio_create_buffer_sound.htm", "window_has_focus.htm"):
        assert page in text, "no manual page named for %s" % page
    assert "audio_mono" in text and "audio_stereo" in text
    assert "All six pages" not in text and "All seven pages" not in text
    assert "states as its own behaviour" not in text, \
        "rule 9 must not be attributed to a page that does not state it"


def test_rule_nine_is_recorded_as_unproven_because_the_engine_page_does_not_promise_it():
    """Spec 12 rule 9 says a sound replaces the oldest of its kind. audio_channel_num.htm says a sound
    of lower priority is stopped to free a channel and says nothing about age, so the rule is our
    wish, not an engine guarantee. It is stated as unproven in the module and in PROVENANCE."""
    module = _text(MODULE)
    assert "oldest" in module
    assert "unproven" in module
    provenance = _text(os.path.join(ROOT, "knowledge", "PROVENANCE.md"))
    assert "rule 9" in provenance.lower()
    assert "audio_is_playing" in provenance
    assert "audio_create_buffer_sound" in provenance

