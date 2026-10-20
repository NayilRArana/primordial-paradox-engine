"""Tests for tools/check_data.py: the real data passes, and every class of mistake it claims to catch does fail.

Each test breaks exactly one thing in a private copy of data\\ and asserts the error names the file and the field, so
the checker cannot rot into a script that prints "ok" while a fight points at a pattern that does not exist.
"""

from __future__ import annotations

import os

import check_data


def failures(root):
    return check_data.check(str(root))


def test_real_data_passes():
    assert failures(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) == []


def test_unknown_pattern_id_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][0]["patterns"] = ["no_such_pattern"]
    write_json(path, data)

    errors = failures(data_root)
    assert any("unknown pattern id" in e and "patterns[0]" in e for e in errors), errors


def test_speed_out_of_range_names_the_field(data_root, read_json, write_json):
    path = data_root / "data" / "patterns" / "all.json"
    data = read_json(path)
    data["patterns"][0]["frames"][0]["speed"] = 9.0
    write_json(path, data)

    errors = failures(data_root)
    assert any("frames[0].speed" in e and "outside" in e for e in errors), errors


def test_map_row_width_is_checked(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    data["maps"][0]["tiles"][0] = "#" * 5
    write_json(path, data)

    errors = failures(data_root)
    assert any("tiles[0]" in e and "map width" in e for e in errors), errors


def test_trigger_outside_the_map_is_checked(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    data["maps"][0]["triggers"][0]["x"] = 99
    write_json(path, data)

    errors = failures(data_root)
    assert any("triggers[0].x" in e and "outside the map width" in e for e in errors), errors


def test_missing_dialogue_reference_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    data["enemies"][0]["talk_dialogue"] = "no_such_dialogue"
    write_json(path, data)

    errors = failures(data_root)
    assert any("unknown dialogue id" in e for e in errors), errors


def test_unknown_flag_condition_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    for trigger in data["maps"][0]["triggers"]:
        if trigger.get("condition"):
            trigger["condition"] = "no_such_flag"
            break
    write_json(path, data)

    errors = failures(data_root)
    assert any("unknown flag id" in e for e in errors), errors


def test_palette_size_is_enforced(data_root, read_json, write_json):
    path = data_root / "data" / "palette.json"
    data = read_json(path)
    data["colours"].pop()
    write_json(path, data)

    errors = failures(data_root)
    assert any("the master palette is 54" in e for e in errors), errors


def test_unknown_scene_command_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "scenes" / "all.json"
    data = read_json(path)
    data["scenes"][0]["commands"][0] = {"cmd": "teleport"}
    write_json(path, data)

    errors = failures(data_root)
    assert any("unknown command" in e for e in errors), errors


def test_concurrency_above_the_declared_cap_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "patterns" / "all.json"
    data = read_json(path)
    data["patterns"][0]["frames"][0]["count"] = 8
    data["patterns"][0]["max_concurrent"] = 2
    write_json(path, data)

    errors = failures(data_root)
    assert any("exceeds declared max_concurrent" in e or "peak" in e for e in errors), errors


def test_spawn_on_a_blocked_tile_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    data["maps"][0]["spawns"]["start"] = {"x": 0, "y": 0}
    write_json(path, data)

    errors = failures(data_root)
    assert any("sits on a blocked tile" in e for e in errors), errors


def test_duplicate_id_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "items.json"
    data = read_json(path)
    data["items"].append(dict(data["items"][0]))
    write_json(path, data)

    errors = failures(data_root)
    assert any("duplicate id" in e for e in errors), errors


def test_scene_move_into_a_wall_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "scenes" / "all.json"
    data = read_json(path)
    data["scenes"][0]["commands"].insert(1, {"cmd": "move", "actor": "hero", "dir": "up", "tiles": 6})
    write_json(path, data)

    errors = failures(data_root)
    assert any("walks into a blocked tile" in e for e in errors), errors


def test_missing_file_is_named(data_root):
    (data_root / "data" / "items.json").unlink()

    errors = failures(data_root)
    assert any("data/items.json" in e and "missing" in e for e in errors), errors


def test_word_longer_than_a_line_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "dialogue" / "all.json"
    data = read_json(path)
    data["dialogue"][0]["lines"][0] = "* " + "A" * 40
    write_json(path, data)

    errors = failures(data_root)
    assert any("longer than a 30 character line" in e for e in errors), errors


def test_pattern_that_never_ends_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "patterns" / "all.json"
    data = read_json(path)
    # A hazard that appears in the last step of the pattern and then cannot leave before the 900 step cap.
    data["patterns"][0]["frames"][0]["at"] = 898
    data["patterns"][0]["frames"][0]["speed"] = 0.25
    data["patterns"][0]["frames"][0]["life"] = 900
    data["patterns"][0]["length"] = 899
    data["patterns"][0]["max_concurrent"] = 4
    write_json(path, data)

    errors = failures(data_root)
    assert any("step cap" in e for e in errors), errors


def test_story_flag_with_no_blocked_tile_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    data["maps"][1]["story_flag"] = "ship_door_open"   # the cabin has no story blocked tile
    write_json(path, data)

    errors = failures(data_root)
    assert any("no tile is story blocked" in e for e in errors), errors


def test_map_trigger_must_name_a_spawn_point(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    for trigger in data["maps"][0]["triggers"]:
        if trigger["kind"] == "map":
            trigger.pop("spawn", None)
    write_json(path, data)

    errors = failures(data_root)
    assert any("must name the spawn point" in e for e in errors), errors


def test_map_trigger_spawn_must_exist_on_the_target_map(data_root, read_json, write_json):
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    for trigger in data["maps"][0]["triggers"]:
        if trigger["kind"] == "map":
            trigger["spawn"] = "not_a_spawn"
    write_json(path, data)

    errors = failures(data_root)
    assert any("is not a spawn point of map" in e for e in errors), errors


def test_encounter_must_declare_its_result_flags(data_root, read_json, write_json):
    path = data_root / "data" / "encounters" / "all.json"
    data = read_json(path)
    data["encounters"][0].pop("flags_on_spare", None)
    write_json(path, data)

    errors = failures(data_root)
    assert any("flags_on_spare" in e and "missing" in e for e in errors), errors


def test_branch_cycle_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "scenes" / "all.json"
    data = read_json(path)
    # A second scene that branches to the first, and the first branches back: a cutscene that never ends.
    loop_a = {"id": "loop_a", "name": "A", "map": "ship_small", "start": {"x": 2, "y": 7},
              "commands": [{"cmd": "branch", "flag": "ship_deck_seen", "scene": "loop_b"}, {"cmd": "end"}]}
    loop_b = {"id": "loop_b", "name": "B", "map": "ship_small", "start": {"x": 2, "y": 7},
              "commands": [{"cmd": "branch", "flag": "ship_deck_seen", "scene": "loop_a"}, {"cmd": "end"}]}
    data["scenes"].extend([loop_a, loop_b])
    write_json(path, data)

    errors = failures(data_root)
    assert any("branch cycle" in e for e in errors), errors
