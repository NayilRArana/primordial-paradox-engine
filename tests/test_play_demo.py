"""Pins for the demo kit (card DEMO-KIT): the script is playable, and the manifest tells the truth about it.

What these tests hold down, and why each one earns its place:
  1. data/demo/run_001.json passes tools/play_demo.py's own validator, so the file the command reads is the
     file the validator accepts, and not a file that only looks right in an editor;
  2. the clock is honest: every step is a real step at the script's fps, the end step is inside the clock's
     own limit, and the planned recording is at least the 30 s the submission asks for;
  3. the manifest and the script cannot drift: every beat the manifest calls covered or partial is a beat the
     script actually plays, every event in the script is claimed by exactly one beat row, and every row the
     manifest calls not_reachable says why;
  4. the validator really refuses the four faults a script can have and still look plausible: a key the game
     does not read, a clock that goes backwards, a marker with no fallback (a run that hangs on a block
     buffered log), and a recording shorter than the submission needs;
  5. the finished-video check is a gate and not a print: a missing or empty file fails, and a black frame is
     measured as black. The mp4 itself is checked by `python tools\\play_demo.py --check`, which is not run
     here because ffmpeg and a screen are not guaranteed on the machine that runs the tests.

Run: python -m pytest tests/test_play_demo.py -q
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
SCRIPT = os.path.join(ROOT, "data", "demo", "run_001.json")
MANIFEST = os.path.join(ROOT, "data", "demo", "manifest.json")
BEAT_SHEET_TOTAL_S = 900


def load_tool(name: str):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def script():
    return read_json(SCRIPT)


def manifest():
    return read_json(MANIFEST)


# Card TEST-CLASSIFY-33: the eight tests below call load_tool("play_demo"), and tools/play_demo.py
# imports capture_title, which binds ctypes.windll at module level, so the import raises on Linux and
# the test never reaches its assertion. They are marked windows_only for the reason in that loader.
@pytest.mark.windows_only
def test_the_script_the_command_reads_passes_its_own_validator():
    demo = load_tool("play_demo")
    problems = demo.validate_script(script())
    assert problems == [], "data/demo/run_001.json is refused by tools/play_demo.py: %s" % problems


@pytest.mark.windows_only
def test_the_clock_is_steps_at_sixty_a_second_and_covers_at_least_thirty_seconds():
    demo = load_tool("play_demo")
    data = script()
    fps = data["clock"]["fps"]
    assert fps == 60, "the clock is the game's own step rate: 60 a second, not %s" % fps
    seconds = demo.planned_seconds(data)
    assert seconds >= data["record"]["min_seconds"] >= 30
    end_step = data["checks"]["end_step"]
    assert seconds == end_step / float(fps)
    assert end_step <= data["clock"]["max_steps"], "the end step is past the clock's own limit"
    assert seconds == 71.0, "the run is 71 s: a change to it changes the submission, so it is pinned here"


def test_every_step_is_a_whole_step_and_the_steps_only_move_forward():
    data = script()
    steps = [event["step"] for event in data["events"]]
    assert steps == sorted(steps), "the events are not in clock order"
    assert steps[0] == 0, "the recording starts on the first event"
    assert all(isinstance(step, int) for step in steps)


def test_the_seeds_are_pinned_and_the_one_this_slice_reaches_is_named():
    data = script()
    seeds = data["seeds"]
    assert seeds["title_flash"] == 20261021, "PP_TITLE_FLASH_SEED is the attract's stream and is pinned"
    assert "note" in seeds and "PP_TITLE_FLASH_SEED" in seeds["note"]
    assert "not reached" in seeds["note"], "the seed note says which streams this run does not reach"


def test_the_manifest_has_all_thirty_two_beats_once_each():
    data = manifest()
    beats = [row["beat"] for row in data["beats"]]
    assert beats == list(range(1, 33)), "the beat sheet has 32 beats and the manifest must list each once"
    for row in data["beats"]:
        assert row["state"] in ("covered", "partial", "not_reachable"), row
        assert isinstance(row["title"], str) and row["title"], row
        assert isinstance(row["authored_s"], int) and row["authored_s"] > 0, row
    assert sum(row["authored_s"] for row in data["beats"]) == BEAT_SHEET_TOTAL_S


def test_the_manifest_summary_matches_its_own_rows():
    data = manifest()
    summary = data["summary"]
    for state in ("covered", "partial", "not_reachable"):
        expected = [row["beat"] for row in data["beats"] if row["state"] == state]
        assert summary[state] == expected, "%s in the summary does not match the rows" % state
    assert set(summary["covered"]) | set(summary["partial"]) | set(summary["not_reachable"]) == set(range(1, 33))


def test_no_beats_the_script_plays_are_missing_from_the_manifest():
    """The script's beats and the manifest's covered and partial beats are the same set, in both directions."""
    played = {event["beat"] for event in script()["events"]}
    claimed = set(manifest()["summary"]["covered"]) | set(manifest()["summary"]["partial"])
    assert played == claimed, ("the script plays beats %s but the manifest claims %s"
                               % (sorted(played), sorted(claimed)))


def test_every_event_is_claimed_by_a_beat_row_and_every_claim_names_a_real_event():
    """Every event is claimed, and a claim is never a stretch: an event belongs to one beat, or to two
    neighbours when it is the press that ends one beat and starts the next (e02 ends the attract and opens
    the menu, so it is honestly both)."""
    data = manifest()
    event_ids = {event["id"] for event in script()["events"]}
    claims = {}
    for row in data["beats"]:
        for identifier in row.get("events", []):
            assert identifier in event_ids, "beat %d claims %s, which is not in the script" % (row["beat"], identifier)
            claims.setdefault(identifier, []).append(row["beat"])
    assert set(claims) == event_ids, "these events are played but no beat row claims them: %s" % sorted(event_ids - set(claims))
    for identifier, beats in claims.items():
        assert len(beats) <= 2, "%s is claimed by %d beats: %s" % (identifier, len(beats), beats)
        if len(beats) == 2:
            assert beats[1] - beats[0] == 1, "%s is claimed by beats %s, which are not neighbours" % (identifier, beats)


def test_a_covered_or_partial_beat_carries_the_evidence_for_it():
    for row in manifest()["beats"]:
        if row["state"] in ("covered", "partial"):
            assert row.get("events"), "beat %d is %s but names no event" % (row["beat"], row["state"])
            assert isinstance(row.get("evidence"), str) and row["evidence"], "beat %d has no evidence" % row["beat"]


def test_the_unreachable_beats_say_why_and_the_count_is_stated():
    data = manifest()
    assert isinstance(data.get("not_reachable_why"), str) and "rm_pp_ship" in data["not_reachable_why"]
    assert len(data["summary"]["not_reachable"]) == 24, "24 of the 32 beats cannot be reached in this build"
    assert "must not be described as a 15 minute run" in data["summary"]["note"]


def test_the_command_is_the_one_in_the_manifest():
    assert "play_demo.py" in manifest()["command"]
    assert manifest()["script"] == "data/demo/run_001.json"


@pytest.mark.windows_only
def test_the_validator_refuses_a_key_the_game_does_not_read():
    demo = load_tool("play_demo")
    data = script()
    data["events"][1]["key"] = "enter-primed"
    problems = demo.validate_script(data)
    assert any("is not one of" in problem for problem in problems), problems


@pytest.mark.windows_only
def test_the_validator_refuses_a_clock_that_goes_backwards():
    demo = load_tool("play_demo")
    data = script()
    data["events"][2]["step"] = 10
    problems = demo.validate_script(data)
    assert any("backwards" in problem for problem in problems), problems


@pytest.mark.windows_only
def test_the_validator_refuses_a_marker_with_no_fallback_step():
    demo = load_tool("play_demo")
    data = script()
    del data["events"][3]["step"]
    problems = demo.validate_script(data)
    assert any("no fallback step" in problem for problem in problems), problems


@pytest.mark.windows_only
def test_the_validator_refuses_a_recording_under_thirty_seconds():
    demo = load_tool("play_demo")
    data = script()
    data["record"]["min_seconds"] = 12
    problems = demo.validate_script(data)
    assert any("at least 30" in problem for problem in problems), problems


@pytest.mark.windows_only
def test_the_video_check_fails_a_missing_file_instead_of_printing_a_pass():
    """The gate the submission rests on: no file, no pass. It runs before ffmpeg is ever asked for anything."""
    demo = load_tool("play_demo")
    scratch = tempfile.mkdtemp(prefix="pp_demo_")
    missing = os.path.join(scratch, "nothing_here.mp4")
    ok, report = demo.verify_video(missing, script())
    assert ok is False
    assert "FAIL the file is missing or empty" in report["checks"]["file"]


@pytest.mark.windows_only
def test_the_verify_file_is_named_after_the_mp4_and_not_after_the_script():
    """A re-recording written with --out must not overwrite the verdict of the take already on disk.

    run_002.mp4 wrote run_001_verify.json before this pin, so the file that described the good take was
    replaced by the verdict on the new one and the two could not be told apart.
    """
    demo = load_tool("play_demo")
    assert demo.out_stem(os.path.join("output", "demo", "run_002.mp4")) == "run_002"
    assert demo.out_stem("output/demo/run_001.mp4") == "run_001"
    assert demo.out_stem(os.path.join("D:" + os.sep, "repo", "output", "demo", "run_002.mp4")) == "run_002"


@pytest.mark.windows_only
def test_a_black_frame_measures_as_black_and_a_game_frame_does_not():
    from PIL import Image

    demo = load_tool("play_demo")
    scratch = tempfile.mkdtemp(prefix="pp_demo_")
    black = os.path.join(scratch, "black.png")
    Image.new("RGB", (768, 720), (0, 0, 0)).save(black, "PNG")
    assert demo.frame_luma(black) == 0.0
    bright = os.path.join(scratch, "bright.png")
    Image.new("RGB", (768, 720), (0, 120, 248)).save(bright, "PNG")
    assert demo.frame_luma(bright) > demo.MIN_MEAN_LUMA
