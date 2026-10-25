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
    assert any("longer than a %d character line" % check_data.LINE_CHARS in e for e in errors), errors


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


def test_two_triggers_on_one_tile_are_refused(data_root, read_json, write_json):
    """Card TRIGGER-TILE-RULE: pp_map_trigger_at returns the first row, so a second row on that tile is dead data."""
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    triggers = data["maps"][0]["triggers"]
    first, second = triggers[0], triggers[1]
    second["x"], second["y"] = first["x"], first["y"]
    write_json(path, data)

    errors = failures(data_root)
    tile = "(%d,%d)" % (first["x"], first["y"])
    assert any(
        "triggers[1].x/y" in e and tile in e and first["kind"] in e and first["id"] in e and "(triggers[0])" in e
        for e in errors
    ), errors


def test_the_same_tile_on_a_second_map_is_not_a_clash(data_root, read_json, write_json):
    """The set is per map row: two maps may each carry a trigger on the same tile without either being refused."""
    path = data_root / "data" / "maps" / "all.json"
    data = read_json(path)
    donor = data["maps"][0]["triggers"][0]
    host = data["maps"][1]["triggers"][0]
    host["x"], host["y"] = donor["x"], donor["y"]
    write_json(path, data)

    errors = failures(data_root)
    assert not any("already carries" in e for e in errors), errors


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


# ---------------------------------------------------------------------------------------------------------------
# Angle handedness (delta C5). These are the tests the delta asks for: a data angle of 90 has to travel down the
# screen, and a positive curve has to turn clockwise, because those are the words the recipes are written in.

def one_frame_pattern(**overrides):
    frame = {
        "at": 0, "count": 1, "spread": 0, "origin": "top", "speed": 4.0, "angle": 90,
        "accel": 0, "curve": 0, "life": 40, "size": 8, "delay": 0, "jitter_angle": 0,
        "wobble": {"amp": 0, "period": 10},
    }
    frame.update(overrides)
    return {"id": "test_recipe", "aim": "fixed", "length": 60, "max_concurrent": 4, "frames": [frame]}


def test_data_angle_90_at_origin_top_reaches_the_bottom_of_the_box():
    """Passing a data angle straight into a GameMaker direction sends 90 upward, so the hazard would leave the box at
    the top and the phase would have nothing to dodge. The path must cross the whole box instead."""
    result = check_data.simulate(one_frame_pattern(), trace=True)
    path = result["paths"][0]
    assert path[0][1] < check_data.ARENA_Y1, "hazard must start above the box"
    assert path[-1][1] > check_data.ARENA_Y2, "a 90 degree emitter at origin top must reach the bottom edge"
    assert all(later[1] >= earlier[1] for earlier, later in zip(path, path[1:])), "downward travel must be monotonic"


def test_positive_curve_turns_clockwise_on_screen():
    """A recipe is written in screen terms, so from angle 0 (right) a positive curve bends toward the bottom of the
    screen. In GameMaker terms that is a decreasing direction, which is why the curve is negated once at spawn."""
    result = check_data.simulate(
        one_frame_pattern(origin="centre", angle=0, speed=1.0, curve=6, life=90), trace=True)
    path = result["paths"][0]
    assert path[3][0] > path[0][0], "the hazard must still be travelling right after three steps"
    assert path[3][1] > path[0][1], "a positive curve must bend the path downward on screen"


def test_per_frame_aim_is_simulated_like_the_emitter():
    """pp_dodge_recipe.gml honours `aim` on a frame as well as on the pattern, so the checker has to as well. The
    frame angle points up and away from the marker, so only an aimed frame can send the hazard downward."""
    per_frame = check_data.simulate(one_frame_pattern(angle=270, aim=True), trace=True)
    assert per_frame["paths"][0][-1][1] > per_frame["paths"][0][0][1]

    pattern_level = one_frame_pattern(angle=270)
    pattern_level["aim"] = "at_marker"
    aimed = check_data.simulate(pattern_level, trace=True)
    assert aimed["paths"][0][-1][1] > aimed["paths"][0][0][1]


def test_angle_to_gm_mirrors_and_wraps():
    assert check_data.angle_to_gm(0) == 0
    assert check_data.angle_to_gm(90) == 270
    assert check_data.angle_to_gm(270) == 90
    assert check_data.angle_to_gm(450) == 270
    assert check_data.angle_to_gm(-90) == 90


# --- the music cue registry (spec 12, card G0-2) ----------------------------------------------------------------

CUE_IDS = ["PP-01", "PP-02", "PP-03", "PP-04", "PP-05", "PP-06", "PP-07", "PP-08", "PP-09",
           "PP-10", "PP-11", "PP-12", "PP-13", "PP-14", "PP-15a", "PP-15b", "PP-16"]
ROOT_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def test_cue_registry_uses_the_musicians_own_ids_and_count_is_pinned(read_json):
    """The cue ids come from the musician's list, not from a name invented in code, and there are seventeen of them.
    Pinning the count means a cue that is quietly dropped from the table fails here instead of failing as silence."""
    data = read_json(os.path.join(ROOT_DATA, "audio.json"))
    assert [row["id"] for row in data["cues"]] == CUE_IDS
    assert len(data["cues"]) == 17
    for row in data["cues"]:
        assert row["placeholder"] is True, "no OGG exists yet, so every cue must say so"
        assert row["loop"] in (True, False)
        assert row["asset"] and not row["asset"].endswith(".ogg"), "the loader adds the extension itself"


def test_the_four_slice_cues_are_registered(read_json):
    data = read_json(os.path.join(ROOT_DATA, "audio.json"))
    ids = {row["id"] for row in data["cues"]}
    assert {"PP-05", "PP-06", "PP-15a", "PP-15b"} <= ids
    boss = {row["id"] for row in data["cues"] if row.get("boss")}
    assert boss == {"PP-06", "PP-10", "PP-14"}, "boss music gets priority 12 (spec 12 rule 1)"


def test_duplicate_cue_id_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "audio.json"
    data = read_json(path)
    data["cues"][1]["id"] = data["cues"][0]["id"]
    write_json(path, data)

    errors = failures(data_root)
    assert any("duplicate cue id" in e for e in errors), errors


def test_cue_without_the_placeholder_flag_fails(data_root, read_json, write_json):
    """A cue that does not say placeholder would claim an OGG the build does not ship."""
    path = data_root / "data" / "audio.json"
    data = read_json(path)
    del data["cues"][0]["placeholder"]
    write_json(path, data)

    errors = failures(data_root)
    assert any("cues[0].placeholder" in e and "missing" in e for e in errors), errors


def test_missing_slice_cue_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "audio.json"
    data = read_json(path)
    data["cues"] = [row for row in data["cues"] if row["id"] != "PP-15b"]
    write_json(path, data)

    errors = failures(data_root)
    assert any("needs cue PP-15b" in e for e in errors), errors


def test_unknown_cue_id_in_a_scene_is_named(data_root, read_json, write_json):
    path = data_root / "data" / "scenes" / "all.json"
    data = read_json(path)
    for command in data["scenes"][0]["commands"]:
        if command.get("cmd") == "music":
            command["id"] = "PP-99"
            break
    write_json(path, data)

    errors = failures(data_root)
    assert any("unknown sound or cue id" in e and "PP-99" in e for e in errors), errors


def test_cue_stand_in_must_be_a_music_entry(data_root, read_json, write_json):
    path = data_root / "data" / "audio.json"
    data = read_json(path)
    for row in data["cues"]:
        if row["id"] == "PP-05":
            row["placeholder_sound"] = "ui_blip"
    write_json(path, data)

    errors = failures(data_root)
    assert any("placeholder_sound" in e and "not a music entry" in e for e in errors), errors


def test_cue_route_must_be_one_of_the_project_routes(data_root, read_json, write_json):
    path = data_root / "data" / "audio.json"
    data = read_json(path)
    for row in data["cues"]:
        if row["id"] == "PP-15a":
            row["route"] = "pacifist"
    write_json(path, data)

    errors = failures(data_root)
    assert any("cues[14].route" in e and "route labels" in e for e in errors), errors


def test_cue_asset_is_a_bare_name(data_root, read_json, write_json):
    path = data_root / "data" / "audio.json"
    data = read_json(path)
    data["cues"][0]["asset"] = "pp_01_wessex_lane.ogg"
    write_json(path, data)

    errors = failures(data_root)
    assert any("without the .ogg" in e for e in errors), errors


# ----------------------------------------------------------------------------------------------------------------
# The phase crossing's talk names (spec 16 section 10, card t_155e22e2). A phase row carries a dialogue id in
# talk_set and a talk card phase in talk_phase, and the checker refuses a name that resolves in the wrong namespace.


def percy_phase_row(data):
    for enemy in data["enemies"]:
        if enemy["id"] == "percy":
            return enemy["phases"][0]
    raise AssertionError("data/enemies/all.json no longer has a percy phase row")


def test_a_talk_phase_that_names_no_card_is_refused(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    percy_phase_row(data)["talk_phase"] = "percy_wounded"
    write_json(path, data)

    errors = failures(data_root)
    assert any("no talk card" in e and "percy_wounded" in e for e in errors), errors


def test_a_phase_card_no_phase_row_names_is_unreachable(data_root, read_json, write_json):
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    del percy_phase_row(data)["talk_phase"]
    write_json(path, data)

    errors = failures(data_root)
    assert any("unreachable" in e and "cards[" in e for e in errors), errors


def test_the_card_phase_is_not_readable_as_a_dialogue_id(data_root, read_json, write_json):
    """The confusion this card settled: talk_set is a dialogue id, so the card's phase there must be refused."""
    path = data_root / "data" / "enemies" / "all.json"
    data = read_json(path)
    percy_phase_row(data)["talk_set"] = "percy_phase2"
    write_json(path, data)

    errors = failures(data_root)
    assert any("unknown dialogue id" in e and "talk_set" in e and "percy_phase2" in e for e in errors), errors


def test_a_renamed_phase_card_breaks_both_ends(data_root, read_json, write_json):
    path = data_root / "data" / "talk_cards.json"
    data = read_json(path)
    for card in data["cards"]:
        if card["enemy"] == "percy" and card["phase"] == "percy_phase2":
            card["phase"] = "percy_phase3"
    write_json(path, data)

    errors = failures(data_root)
    assert any("no talk card" in e and "talk_phase" in e for e in errors), errors
    assert any("unreachable" in e and "percy_phase3" in e for e in errors), errors
