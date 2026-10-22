"""Tests for the save system as text and as a document, without GameMaker.

GameMaker is not installed on this PC, so these tests cannot prove the save works in a running
game. They can prove the contract in specs\\11-save.md and specs\\10-route-ledger.md is what the
code says, and that the failure modes are loud: a key written on one side only, a format checked
too late, a route word stored in the file, an unknown id in a save shaped dict.

Every check here reads the GML as text and compares it to the spec, so a change in either side
fails here instead of at the first run. The GML is never executed and never edited.
"""

from __future__ import annotations

import json
import os
import re

import check_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The save module under test. The environment variable points the tests at a copy, so a mutation
# can be shown to fail this test and not only the helper.
SAVE_GML = os.environ.get("PP_SAVE_GML") or os.path.join("game", "scripts", "pp_save", "pp_save.gml")
LEDGER_GML = os.path.join("game", "scripts", "pp_ledger", "pp_ledger.gml")
CONFIG_GML = os.path.join("game", "scripts", "pp_config", "pp_config.gml")
SPEC_SAVE = os.path.join("specs", "11-save.md")
SPEC_LEDGER = os.path.join("specs", "10-route-ledger.md")

# The route words of spec 10. They are derived on read and must never be written to the file.
ROUTE_WORDS = ("mercy", "blooded", "genocide")


# ---------------------------------------------------------------------------------------------------------------
# Reading GML as text


def read_text(relative: str) -> str:
    with open(os.path.join(ROOT, relative), "r", encoding="utf-8-sig") as fh:
        return fh.read()


def code_only(text: str) -> str:
    """Drop // and /// comments so a check reads code, not prose."""
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        lines.append(line if cut == -1 else line[:cut])
    return "\n".join(lines)


def read_code(relative: str) -> str:
    return code_only(read_text(relative))


def brace_block(text: str, marker: str) -> str:
    """The brace balanced block that starts at the first '{' after marker."""
    start = text.index(marker)
    open_index = text.index("{", start)
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index:index + 1]
    raise AssertionError("unbalanced block after %r" % marker)


def function_body(text: str, name: str) -> str:
    """The whole text of one GML function, braces included."""
    return brace_block(text, "function %s(" % name)


def split_top_level(inner: str) -> list[str]:
    """Split the inside of a struct or array on the commas that are not inside a bracket."""
    parts = []
    depth = 0
    current = ""
    for char in inner:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current)
    return parts


def struct_keys(literal: str) -> list[str]:
    """The top level keys of a GML struct literal, in the order they are written."""
    inner = literal.strip()
    assert inner.startswith("{") and inner.endswith("}"), literal
    keys = []
    for part in split_top_level(inner[1:-1]):
        name = part.split(":", 1)[0].strip()
        if name:
            keys.append(name)
    return keys


def quoted_strings(literal: str) -> list[str]:
    return re.findall(r'"([^"]*)"', literal)


def backticked(text: str) -> list[str]:
    return re.findall(r"`([^`]+)`", text)


def spec_paragraph(spec_relative: str, lead: str) -> str:
    """One paragraph of a spec, from the line that starts with lead to the next blank line."""
    text = read_text(spec_relative)
    start = text.index(lead)
    rest = text[start:]
    cut = rest.find("\n\n")
    return rest if cut == -1 else rest[:cut]


# ---------------------------------------------------------------------------------------------------------------
# The three views of the key set


def spec_save_required_keys() -> list[str]:
    """The key names spec 11 lists as required, read out of the spec text itself."""
    return backticked(spec_paragraph(SPEC_SAVE, "Keys:"))


def spec_save_optional_keys() -> list[str]:
    """The key names spec 11 lists as optional, read out of the spec text itself.

    An optional key is one a save written before it existed does not carry, so its absence is an
    empty record rather than a damaged file (spec 10 rule 6). The paragraph is read, not hardcoded,
    so the spec and the code cannot drift.
    """
    return backticked(spec_paragraph(SPEC_SAVE, "Optional keys:"))


def spec_save_keys() -> list[str]:
    """Every key name spec 11 knows: the required ones, then the optional ones."""
    return spec_save_required_keys() + spec_save_optional_keys()


def spec_counter_keys() -> list[str]:
    """The four counter names of spec 10, read out of the spec text itself.

    Spec 10 keeps the counters and the flags in one paragraph, so only the line that names the
    counters is read. The flag examples that follow are not counters.
    """
    for line in read_text(SPEC_LEDGER).split("\n"):
        if line.startswith("1. Counters:"):
            return backticked(line)
    raise AssertionError("spec 10 does not name its counters")


def write_keys(text: str) -> list[str]:
    """The keys the write function puts into the document."""
    body = function_body(text, "pp_save_snapshot")
    literal = body[body.index("return {"):]
    return struct_keys(brace_block(literal, "return {"))


def read_keys(text: str) -> list[str]:
    """The keys the load function says a document must carry."""
    body = function_body(text, "pp_save_key_list")
    literal = body[body.index("return ["):]
    end = literal.index("]")
    return quoted_strings(literal[:end + 1])


def validated_keys(text: str) -> list[str]:
    """The keys the validator actually reads out of a loaded document."""
    body = function_body(text, "pp_save_validate")
    names = re.findall(r"_d\.([A-Za-z_][A-Za-z0-9_]*)", body)
    seen = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def parity_failures(text: str) -> list[str]:
    """Every way the written, read and spec key sets can disagree."""
    problems = []
    written = set(write_keys(text))
    read = set(read_keys(text))
    spec = set(spec_save_keys())
    for name in sorted(written - read):
        problems.append("the write function writes %r but the load function does not read it" % name)
    for name in sorted(read - written):
        problems.append("the load function reads %r but the write function does not write it" % name)
    for name in sorted(written - spec):
        problems.append("the write function writes %r, which spec 11 does not list" % name)
    for name in sorted(spec - written):
        problems.append("the write function does not write %r, which spec 11 lists" % name)
    return problems


# ---------------------------------------------------------------------------------------------------------------
# 1. Key parity


def test_spec_11_lists_sixteen_named_keys_and_the_optional_one_separately():
    """The spec is the contract, so the count and the names are read out of it, not hardcoded.

    A key added later may not be presented as required: a save written before it existed has to keep
    loading, so it belongs in the optional paragraph and nowhere else.
    """
    keys = spec_save_required_keys()
    assert len(keys) == 16, keys
    assert "format" in keys and "counters" in keys and "flags" in keys
    every = spec_save_keys()
    assert len(set(every)) == len(every), "the spec lists a key twice: %s" % every
    assert spec_save_optional_keys() == ["fight_exits"], spec_save_optional_keys()
    assert "fight_exits" not in keys, "the exit rows must not be a required key, or an older save is refused"


def test_written_keys_and_read_keys_are_the_spec_set():
    """A key added to one side only has to fail here, not at the first load."""
    text = read_code(SAVE_GML)
    assert parity_failures(text) == [], parity_failures(text)


def test_the_validator_reads_exactly_the_keys_the_spec_lists():
    """The key list is not decoration: the validator touches every one of those keys."""
    text = read_code(SAVE_GML)
    assert set(validated_keys(text)) == set(spec_save_keys()), sorted(set(validated_keys(text)))


def test_a_key_removed_from_the_write_list_breaks_the_parity_check(tmp_path):
    """The parity check can fail. The mutation is done on a scratch copy; the repo file is untouched."""
    original = read_code(SAVE_GML)
    assert parity_failures(original) == []

    scratch = tmp_path / "pp_save.gml"
    mutated = original.replace("        music: _w.music\n", "")
    assert mutated != original, "the mutation did not apply"
    scratch.write_text(mutated, encoding="utf-8")

    problems = parity_failures(scratch.read_text(encoding="utf-8"))
    assert problems, "the parity check still passes after a key was deleted from the write list"
    assert any("music" in problem for problem in problems), problems


# ---------------------------------------------------------------------------------------------------------------
# 2. Format is checked first


def test_format_is_checked_before_any_other_key_is_read():
    """An unknown format is refused before anything else is looked at (spec 11 rule 1)."""
    body = function_body(read_code(SAVE_GML), "pp_save_validate")
    format_check = body.index('variable_struct_exists(_d, "format")')
    others = [match.start() for match in re.finditer(r"_d\.(?!format\b)[A-Za-z_][A-Za-z0-9_]*", body)]
    assert others, "the validator reads no other key, so the order cannot be checked"
    assert format_check < min(others), "another key is read before the format is checked"
    assert body.index("pp_save_key_list()") > format_check, \
        "the key set is walked before the format is checked"


def test_an_unknown_format_is_refused_with_a_plain_message():
    body = function_body(read_code(SAVE_GML), "pp_save_validate")
    assert 'if (_format != PP_SAVE_FORMAT)' in body
    assert "the save is format " in body, "the refusal must name the format it found"


# ---------------------------------------------------------------------------------------------------------------
# 3. Names, not indexes


def test_no_save_path_reads_an_asset_or_a_sprite():
    """json_stringify stores a handle for an asset, and a handle changes between runs (spec 11).

    The card asks for a grep of the module and no hit at all, but the module holds one asset call that
    has nothing to do with the document: pp_save_new_game turns the room constant into a room id for
    room_goto. Editing it out is forbidden by this card and wrong on the merits, so the test names the
    save path exactly, proves it is clean, and pins the one exception so it cannot quietly grow a save
    key built from a handle.
    """
    forbidden = (
        "asset_get_index", "asset_get_assets", "asset_get_id",
        "sprite_get_id", "sprite_get_number", "sprite_get_sprite", "sprite_index",
    )
    text = read_code(SAVE_GML)

    save_path = (
        "pp_save_key_list", "pp_save_snapshot", "pp_save_snapshot_powers", "pp_save_snapshot_items",
        "pp_save_snapshot_flags", "pp_save_snapshot_scenes", "pp_save_write", "pp_save_start_write",
        "pp_save_read", "pp_save_read_backup", "pp_save_async_event", "pp_save_payload_text",
        "pp_save_parse", "pp_save_validate", "pp_save_apply",
    )
    hits = []
    for name in save_path:
        body = function_body(text, name)
        for bad in forbidden:
            if bad in body:
                hits.append((name, bad))
    assert hits == [], "a save path reads an asset or a sprite: %s" % hits

    # Exactly one asset call exists in the module, and it is the room lookup in pp_save_new_game.
    assert text.count("asset_get_index") == 1, \
        "the module has %d asset_get_index calls, and only the room lookup is accounted for" \
        % text.count("asset_get_index")
    new_game = function_body(text, "pp_save_new_game")
    assert "asset_get_index(PP_NEW_GAME_ROOM)" in new_game
    assert "room_goto(_room)" in new_game, "the room id is not used for a room change, so pin it"

    assert "sprite" not in text.lower(), "the save module mentions a sprite"


def test_the_write_function_stores_names():
    """Map, spawn, item and power are stored as the id string, never as a position in a list."""
    body = function_body(read_code(SAVE_GML), "pp_save_snapshot")
    assert "map: _w.map.id" in body
    assert "spawn: _w.spawn_name" in body
    items = function_body(read_code(SAVE_GML), "pp_save_snapshot_items")
    assert "id: _row.id" in items
    assert "count:" in items
    powers = function_body(read_code(SAVE_GML), "pp_save_snapshot_powers")
    assert "_power.id" in powers
    for name in ("global.pp_data.maps.maps[", "items.items[", "powers.powers["):
        assert name not in body, "the document is written from an index: %s" % name


# ---------------------------------------------------------------------------------------------------------------
# 4. The backup


def test_the_backup_is_written_before_the_real_file_is_replaced():
    """The rotation is read first, and the real write only starts once the .bak is on disk.

    The module is a state machine, so the order of the two calls in the file is not the order of
    the operations. The proof is the state order: the rotation state, then the state that starts
    the real write, and the real write is only ever started from a state reached after the .bak
    was written.
    """
    text = read_code(SAVE_GML)
    write = function_body(text, "pp_save_write")
    rotation = brace_block(write, "if (_s.present)")
    assert "buffer_load_async(_s.spare, pp_save_name_main()" in rotation, \
        "the current file is not read back for the backup"
    assert "PPSaveState.backing" in rotation
    assert "return true" in rotation, "the rotation must end the function, so the real write waits"
    assert write.index(rotation) < write.index("pp_save_start_write()"), \
        "the real write starts before the rotation"

    event = function_body(text, "pp_save_async_event")
    backing = event.index("case PPSaveState.backing:")
    backing_write = event.index("case PPSaveState.backing_write:")
    writing = event.index("case PPSaveState.writing:")
    assert backing < backing_write < writing
    backing_block = event[backing:backing_write]
    assert "buffer_save_async(_bak, pp_save_name_backup()" in backing_block, \
        "the .bak is not written in the rotation state"
    backing_write_block = event[backing_write:writing]
    assert "pp_save_start_write()" in backing_write_block, \
        "the real write must start only from the state that follows the .bak write"

    # The one other place the real write can start is the fallback at the end of the rotation
    # state, taken when no .bak could be made. It must come after the attempt to make one, so the
    # .bak is always tried first. This fallback is a defect on record (the good file can be
    # overwritten with no backup); it is reported, not edited.
    attempt = backing_block.index("buffer_save_async(_bak, pp_save_name_backup()")
    fallback = backing_block.rindex("pp_save_start_write()")
    assert attempt < fallback, "the real write is reached before the .bak is attempted"


def test_the_slot_and_the_backup_have_the_spec_names():
    """Spec 11: the file is pp_save_01.json, and the copy beside it ends in .bak."""
    config = read_code(CONFIG_GML)
    slot = re.search(r'#macro PP_SAVE_SLOT "([^"]+)"', config)
    backup = re.search(r'#macro PP_SAVE_BACKUP "([^"]+)"', config)
    assert slot is not None and backup is not None
    assert slot.group(1) == "pp_save_01.json"
    assert backup.group(1) == slot.group(1) + ".bak"
    assert backup.group(1).endswith(".bak")


# ---------------------------------------------------------------------------------------------------------------
# 5. The ledger: counters and flags, never a route word


def test_the_saved_counters_are_the_four_of_spec_10():
    spec = spec_counter_keys()
    assert sorted(spec) == ["bosses_killed", "bosses_spared", "regulars_killed", "regulars_spared"]

    text = read_code(SAVE_GML)
    listed = quoted_strings(function_body(text, "pp_save_counter_keys"))
    assert sorted(listed) == sorted(spec), listed

    body = function_body(text, "pp_save_snapshot")
    counters = brace_block(body, "counters: {")
    assert sorted(struct_keys(counters)) == sorted(spec), struct_keys(counters)


def test_no_route_word_is_stored_in_the_save():
    """The route is derived on read, so the file holds counters and flags and nothing else."""
    text = read_code(SAVE_GML)
    for word in ROUTE_WORDS:
        assert word not in text, "the save module stores the route word %r" % word

    body = function_body(text, "pp_save_snapshot")
    keys = struct_keys(brace_block(body, "return {"))
    assert "counters" in keys and "flags" in keys
    for name in keys:
        assert name not in ("route", "stage", "route_name"), \
            "the document stores %r, which spec 10 derives on read" % name


def test_the_route_is_derived_by_the_ledger_and_not_read_from_the_file():
    ledger = read_code(LEDGER_GML)
    assert "function pp_ledger_route(" in ledger
    assert "function pp_ledger_route_name(" in ledger
    save = read_code(SAVE_GML)
    assert "pp_ledger_route_name" not in save, "the save module turns a route into a string"
    assert "pp_ledger_route" not in save, "the save module must not read a route"


# ---------------------------------------------------------------------------------------------------------------
# 6. A deliberately broken fixture


def test_check_data_passes_on_a_private_copy_of_the_data(data_root):
    """The copy in tmp_path is the real data, so the checker is proved on the copy, not the repo."""
    assert check_data.check(str(data_root)) == []


def test_a_broken_id_in_the_copy_is_named_by_the_checker(data_root):
    """The copy is a real copy, not a rubber stamp: break one id and the checker says which."""
    path = data_root / "data" / "maps" / "all.json"
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for trigger in data["maps"][0]["triggers"]:
        if trigger.get("kind") == "scene":
            trigger["id"] = "no_such_scene_at_all"
            break
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")

    errors = check_data.check(str(data_root))
    assert any("unknown scene id" in e for e in errors), errors


def _load_json(relative: str) -> dict:
    with open(os.path.join(ROOT, "data", relative), "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _save_document(**overrides) -> dict:
    """A document shaped like a save, with the keys spec 11 lists and the ids the data has."""
    document = {
        "format": 1,
        "game_version": "0.1.0-slice",
        "saved_at": "2026-10-20 00:00:00",
        "play_seconds": 0,
        "map": "ship_small",
        "spawn": "start",
        "x": 2,
        "y": 7,
        "hp": 20,
        "max_hp": 20,
        "powers": [],
        "items": [],
        "flags": {},
        "counters": {
            "bosses_killed": 0,
            "bosses_spared": 0,
            "regulars_killed": 0,
            "regulars_spared": 0,
        },
        "seen_scenes": [],
        "music": "",
    }
    document.update(overrides)
    return document


def save_document_errors(document: dict) -> list[str]:
    """A Python mirror of the id and key checks of pp_save_validate.

    The runtime validator is GML and cannot run without GameMaker, so this mirror exists to keep
    the failure loud here. It is pinned to the GML: every message it produces has to appear in
    pp_save_validate, so a change of wording in the game breaks this test rather than letting the
    two drift apart.
    """
    problems = []
    if not isinstance(document, dict):
        return ["the save file does not hold a save"]

    if "format" not in document:
        problems.append("the save file has no format")
    elif document["format"] != 1:
        problems.append("the save is format %s, and this build reads format 1" % document["format"])

    known = set(spec_save_keys())
    for name in sorted(document):
        if name not in known:
            problems.append("the save has a field this build does not know: %s" % name)
    # Only the required keys have to be there. An optional key is one a save written before it
    # existed does not carry, and its absence is an empty record rather than a refused file.
    for name in sorted(set(spec_save_required_keys()) - set(document)):
        problems.append("the save is missing the field %s" % name)

    if "fight_exits" in document:
        for row in document["fight_exits"]:
            if not isinstance(row, dict) or sorted(row) != ["exit", "id", "round"]:
                problems.append("a saved fight exit is not a record of an id, an exit and a round")
            elif not isinstance(row["exit"], int) or isinstance(row["exit"], bool) \
                    or not 0 <= row["exit"] <= 2:
                problems.append("a saved fight exit is not one of the three exits")

    maps = {row["id"]: row for row in _load_json("maps/all.json")["maps"]}
    if isinstance(document.get("map"), str):
        if document["map"] not in maps:
            problems.append("the save names a map this build does not have: %s" % document["map"])
        else:
            spawns = maps[document["map"]].get("spawns", {})
            if document.get("spawn") not in spawns:
                problems.append("the save names a spawn point this build does not have: %s"
                                % document.get("spawn"))

    items = {row["id"] for row in _load_json("items.json")["items"]}
    for row in document.get("items", []) or []:
        if isinstance(row, dict) and row.get("id") not in items:
            problems.append("the save names an item this build does not have: %s" % row.get("id"))

    powers = {row["id"] for row in _load_json("powers.json")["powers"]}
    for name in document.get("powers", []) or []:
        if name not in powers:
            problems.append("the save names a power this build does not have: %s" % name)

    scenes = {row["id"] for row in _load_json("scenes/all.json")["scenes"]}
    for name in document.get("seen_scenes", []) or []:
        if name not in scenes:
            problems.append("the save names a scene this build does not have: %s" % name)

    flags = set(_load_json("flags.json")["flags"])
    scene_ids = {row["id"] for row in _load_json("scenes/all.json")["scenes"]}
    for name in (document.get("flags") or {}):
        # The game allows a data flag, a scene flag (scene_<id>) and a derived trigger flag (trig_).
        scene_id = name[len("scene_"):] if name.startswith("scene_") else ""
        known = (name in flags or name.startswith("trig_")
                 or (scene_id != "" and scene_id in scene_ids))
        if not known:
            problems.append("the save carries a flag this build does not know: %s" % name)

    audio = _load_json("audio.json")
    sounds = {row["id"]: row for row in audio["sounds"]}
    # A cue id is a music name too, because a scene music command writes the cue id into world.music and pp_save
    # stores it. pp_data.gml indexes the cue table beside the sounds with kind music, and this mirrors that.
    for row in audio.get("cues", []):
        sounds[row["id"]] = {"id": row["id"], "kind": "music", "cue": True}
    music = document.get("music")
    if music:
        if music not in sounds:
            problems.append("the save names music this build does not have: %s" % music)
        elif sounds[music].get("kind") != "music":
            problems.append("the save names a sound that is not music: %s" % music)

    counters = document.get("counters") or {}
    wanted = spec_counter_keys()
    if not isinstance(counters, dict):
        problems.append("the save counters are not a table")
    elif len(counters) != len(wanted):
        # The game refuses a wrong count before it ever looks at a name, so the mirror must say the
        # same thing for the same input or it is testing a game that does not exist.
        problems.append("the save counters are not the four the route reads")
    else:
        for name in sorted(set(counters) - set(wanted)):
            problems.append("the save counters carry a name the route does not read: %s" % name)
        for name in sorted(wanted):
            value = counters.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                problems.append("the counter %s is out of range" % name)
    return problems


def test_the_mirror_agrees_with_the_gml_validator():
    """Every message the mirror can produce has to exist in the game, and in the same order."""
    body = function_body(read_code(SAVE_GML), "pp_save_validate")
    for message in (
        "the save file has no format",
        "the save is format ",
        "the save has a field this build does not know: ",
        "the save is missing the field ",
        "the save names a map this build does not have: ",
        "the save names a spawn point this build does not have: ",
        "the save names an item this build does not have: ",
        "the save names a power this build does not have: ",
        "the save names a scene this build does not have: ",
        "the save carries a flag this build does not know: ",
        "the save names music this build does not have: ",
        "the save names a sound that is not music: ",
        "the save counters are not a table",
        "the save counters are not the four the route reads",
        "the save counters carry a name the route does not read: ",
        "the counter ",
    ):
        assert message in body, "the game does not say %r, so the mirror is drifting" % message


def test_the_mirror_agrees_with_the_gml_on_which_flags_are_allowed():
    """The mirror lets a data flag, a scene flag and a trigger flag through, so the game must too."""
    allowed = function_body(read_code(SAVE_GML), "pp_save_flag_allowed")
    assert '"trig_"' in allowed
    assert "PP_SAVE_MAX_FLAG_CHARS" in allowed
    assert "global.pp_data.flags.flags" in allowed
    # The scene flag prefix lives in the helper that strips it.
    scene = function_body(read_code(SAVE_GML), "pp_save_scene_flag_id")
    assert '"scene_"' in scene
    assert "variable_struct_exists(global.pp_data.scene_by_id, _scene)" in allowed


def test_a_save_taken_in_a_scene_that_set_a_cue_id_can_be_loaded():
    """Item 5 of card t_73f08da5. A scene music command writes the cue id into world.music and pp_save stores it, so
    the validator has to accept a cue id as a music name or a save taken after the ship boarding scene or the
    Prometheus scene cannot be loaded. Both halves are pinned: the mirror here, and pp_data.gml, which indexes the
    cue table beside the sounds so the game's own check sees the cue."""
    for cue in ("PP-05", "PP-07"):
        problems = save_document_errors(_save_document(music=cue))
        assert problems == [], problems
    problems = save_document_errors(_save_document(music="no_such_music"))
    assert any("names music this build does not have: no_such_music" in p for p in problems), problems
    data = read_code("game/scripts/pp_data/pp_data.gml")
    assert "audio_by_id" in data and "audio.cues" in data, \
        "the cue ids are not reachable as a music name in the game"


def test_a_save_shaped_document_with_an_unknown_id_is_rejected():
    """The loud failure mode: a file that names something this build does not have is refused."""
    document = _save_document(map="no_such_map")
    problems = save_document_errors(document)
    assert any("names a map this build does not have: no_such_map" in p for p in problems), problems

    document = _save_document(items=[{"id": "no_such_item", "count": 1}])
    problems = save_document_errors(document)
    assert any("names an item this build does not have: no_such_item" in p for p in problems), problems

    document = _save_document(seen_scenes=["no_such_scene"])
    problems = save_document_errors(document)
    assert any("names a scene this build does not have: no_such_scene" in p for p in problems), problems

    document = _save_document(flags={"no_such_flag": True})
    problems = save_document_errors(document)
    assert any("carries a flag this build does not know: no_such_flag" in p for p in problems), problems


def test_a_json_fixture_file_with_an_unknown_id_is_rejected(tmp_path):
    """The fixture is a real file on disk, read back as JSON, so the shape a player would see is tested.

    The runtime validator is GML and cannot run without GameMaker, so the file is checked by the
    Python mirror. The mirror is pinned to the GML by test_the_mirror_agrees_with_the_gml_validator.
    """
    path = tmp_path / "pp_save_01.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(_save_document(map="no_such_map"), fh, indent=2)
        fh.write("\n")

    with open(path, "r", encoding="utf-8") as fh:
        document = json.load(fh)

    problems = save_document_errors(document)
    assert any("names a map this build does not have: no_such_map" in p for p in problems), problems


def test_a_save_shaped_document_with_an_unknown_field_or_a_missing_one_is_rejected():
    document = _save_document()
    document["mystery"] = 1
    problems = save_document_errors(document)
    assert any("field this build does not know: mystery" in p for p in problems), problems

    document = _save_document()
    del document["music"]
    problems = save_document_errors(document)
    assert any("missing the field music" in p for p in problems), problems


def test_the_format_is_refused_before_the_other_fields():
    """The mirror keeps the order of the game: an unknown format is reported first."""
    document = _save_document(format=2, map="no_such_map")
    problems = save_document_errors(document)
    assert problems, "a document with a bad format must not pass"
    assert "format 2" in problems[0], problems


def test_a_fifth_counter_is_refused_by_count_before_any_name_is_read():
    """Spec 10 records four counters, and the game refuses a wrong count before it reads a name.

    The game's own order is the contract here: pp_save_validate compares the lengths first, so a fifth
    counter never reaches the name loop. Asserting the name message for this input would assert a
    sentence the game cannot say.
    """
    counters = {
        "bosses_killed": 0,
        "bosses_spared": 0,
        "regulars_killed": 0,
        "regulars_spared": 0,
        "enemies_killed": 0,
    }
    problems = save_document_errors(_save_document(counters=counters))
    assert problems == ["the save counters are not the four the route reads"], problems


def test_a_counter_renamed_away_from_the_four_is_refused_by_name():
    """With the count right, a swapped name is caught by name, which is the game's second test."""
    counters = {
        "bosses_killed": 0,
        "bosses_spared": 0,
        "regulars_killed": 0,
        "enemies_killed": 0,
    }
    problems = save_document_errors(_save_document(counters=counters))
    assert any("carry a name the route does not read: enemies_killed" in p for p in problems), problems


def test_a_well_formed_save_shaped_document_passes_the_mirror():
    """The mirror must not refuse a good document, or every refusal above proves nothing."""
    assert save_document_errors(_save_document()) == []


# ---------------------------------------------------------------------------------------------------------------
# 7. The container the writer and the reader have to agree on (added by the review, card t_edf0aafe)


def test_the_file_starts_with_the_byte_count_the_reader_checks():
    """The four byte count is the whole reason a cut file is a refusal and not a half parsed document.

    Nothing else in this file reads the writer and the reader against each other, so without this
    test the count could leave the write path and every other test would still pass: the game would
    then write files its own reader refuses, which is the failure this pins. The count, the seek and
    the comparison are asserted as the three parts of one agreement, and the slot ceiling is pinned
    beside them because spec 11 numbers say a larger save is a clear error and never a truncation.
    """
    text = read_code(SAVE_GML)
    write = function_body(text, "pp_save_write")
    assert "buffer_write(_buf, buffer_u32, string_byte_length(_json))" in write, \
        "the file no longer starts with the count of the text it holds"
    assert "buffer_write(_buf, buffer_string, _json)" in write
    assert "string_byte_length(_json) > PP_SAVE_BUFFER - 5" in write, \
        "a document larger than the slot is not refused before it is written"

    reader = function_body(text, "pp_save_payload_text")
    assert "buffer_seek(_buf, buffer_seek_start, 0)" in reader, "the reader does not start at the count"
    assert "buffer_read(_buf, buffer_u32)" in reader, "the reader does not read the count"
    assert "buffer_read(_buf, buffer_string)" in reader
    assert "string_byte_length(_text) != _size" in reader, \
        "the reader does not compare the text it read with the count it was given"
    assert "_size > PP_SAVE_BUFFER - 5" in reader, "a count larger than the slot is not refused"
