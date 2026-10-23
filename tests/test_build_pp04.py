"""Tests for assets/audio/pp_04_navy_sailors/build_pp04.py (card t_6af137c1).

Why this file exists: the arranger was untracked because no test mapped to it, so the commit gate
refused it as UNMAPPED source. This builder reads only the committed
assets/audio/pp_04_navy_sailors/score_pp04.yaml and the committed tools/arrange.py, so nothing here
needs the .wav, the .mp3 or the .mid that the root .gitignore keeps out of the commit.

What is proved, rather than asserted in a comment:

  - the committed score still builds the cue the committed pp_04_score_report.json describes: note
    count per voice, the chord per bar, the bar and loop counts, the duration in seconds and the
    measured register of every voice;
  - only the eight chip voices are used and each one is played, so "8 bit voices only" is a
    property of the build and not only of the check script;
  - the file written through tools/arrange.py reads back through tools/melody_guard.py with the
    eight voice tracks, and its lead line is exactly the committed melody_lead.json;
  - the same score writes the same bytes twice;
  - the score errors this builder refuses are refused, each with its own message;
  - the command line's own report is written where it is told, so a test run cannot dirty the tree.

Every test writes only into pytest's throwaway directory.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import arrange  # noqa: E402  the shared MIDI writer the builder imports
import melody_guard  # noqa: E402

HERE = os.path.join(ROOT, "assets", "audio", "pp_04_navy_sailors")
SCORE = os.path.join(HERE, "score_pp04.yaml")
REPORT = os.path.join(HERE, "pp_04_score_report.json")
MELODY = os.path.join(HERE, "melody_lead.json")


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(name, filename):
    return load_path(name, os.path.join(HERE, filename))


BUILDER = load("build_pp04_under_test", "build_pp04.py")


def committed_score():
    with open(SCORE, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def committed_report():
    with open(REPORT, "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def built():
    return BUILDER.build(committed_score())


def test_the_committed_score_builds_the_cue_the_commit_ships(built):
    """The report next to the score is this builder's own output, so drift fails here."""
    arrangement, bars = built
    report = committed_report()
    assert len(bars) == report["bars"] == 32
    assert [bar["chord"] for bar in bars] == report["chords"]
    assert [bar["number"] for bar in bars] == list(range(1, 33))
    assert sum(1 for bar in bars if bar["section"] == "B") == report["sections"]["B"]

    counts = {track: len(arrangement.notes[track]) for track in arrange.TRACK_NAMES}
    assert counts == report["notes"], counts
    for track, spans in arrangement.notes.items():
        pitches = [pitch for _start, _length, pitch, _velocity in spans]
        if pitches:
            assert [min(pitches), max(pitches)] == report["voice_ranges"][track], track

    bpm = float(committed_score()["meta"]["bpm"])
    seconds = len(bars) * BUILDER.TICKS_PER_BAR / arrange.PPQ * 60.0 / bpm
    assert round(seconds, 3) == report["duration_seconds"]
    loop_bars = int(committed_score()["meta"]["loop_end_bar"]) - int(committed_score()["meta"]["loop_start_bar"]) + 1
    assert loop_bars == report["loop_bars"]
    lead_start = min(start for start, _l, _p, _v in arrangement.notes["vrc6 pulse a"])
    assert round(lead_start / arrange.PPQ * 60.0 / bpm, 4) == report["first_lead_note_seconds"]


def test_only_the_eight_chip_voices_are_used_and_every_one_plays(built):
    arrangement, _bars = built
    assert set(arrangement.notes) == set(arrange.TRACK_NAMES)
    for track in arrange.TRACK_NAMES:
        assert arrangement.notes[track], "%s is silent" % track
        for start, length, pitch, velocity in arrangement.notes[track]:
            assert 0 <= start, (track, start)
            assert length > 0, (track, start, length)
            assert 0 <= pitch <= 127, (track, pitch)
            assert 0 <= velocity <= 127, (track, velocity)


def test_every_note_stays_inside_the_loop_and_the_tail(built):
    """Nothing sounds past the last bar, and the cue's own tail is the four bars after the loop."""
    arrangement, bars = built
    end = len(bars) * BUILDER.TICKS_PER_BAR
    for track in arrange.TRACK_NAMES:
        for start, length, _pitch, _velocity in arrangement.notes[track]:
            assert start + length <= end, (track, start, length, end)


def test_the_written_midi_reads_back_as_the_committed_lead_line(built, tmp_path):
    arrangement, _bars = built
    out = tmp_path / "pp_04_navy_sailors.mid"
    arrange.write_midi(arrangement, str(out))
    tracks = melody_guard.parse_midi(str(out))
    names = [name for name, _notes in tracks]
    assert names == ["meta"] + list(arrange.TRACK_NAMES)
    lead = dict(tracks)["vrc6 pulse a"]
    read_back = [[pitch, int(round((stop - start) / float(arrange.EIGHTH)))]
                 for start, stop, pitch in lead]
    with open(MELODY, "r", encoding="utf-8") as handle:
        committed = json.load(handle)
    assert read_back == committed, "the lead line moved away from the committed melody_lead.json"


def test_the_same_score_writes_the_same_bytes_twice(built, tmp_path):
    arrangement, _bars = built
    first, second = tmp_path / "a.mid", tmp_path / "b.mid"
    arrange.write_midi(arrangement, str(first))
    arrange.write_midi(arrangement, str(second))
    assert first.read_bytes() == second.read_bytes()


def test_a_melody_bar_that_does_not_sum_to_eight_eighths_is_refused():
    score = copy.deepcopy(committed_score())
    score["sections"]["A"]["melody"][0][0][1] = 3
    with pytest.raises(ValueError, match="eighths, not 8"):
        BUILDER.build(score)


def test_a_section_with_a_chord_for_every_bar_is_required():
    score = copy.deepcopy(committed_score())
    score["sections"]["B"]["chords"].pop()
    with pytest.raises(ValueError, match="bars of melody and"):
        BUILDER.build(score)


def test_a_melody_line_that_is_not_a_note_list_is_refused():
    score = copy.deepcopy(committed_score())
    score["sections"]["A2"]["melody"] = "same notes as something else"
    with pytest.raises(ValueError, match="unreadable melody line"):
        BUILDER.build(score)


def test_the_command_line_writes_its_outputs_beside_the_score(tmp_path):
    """main() writes to fixed names, so it runs from a second module instance pointed at a copy.

    The tree itself is never written: the score is copied into the throwaway folder and every
    output constant of the copy is redirected there.
    """
    folder = tmp_path / "pp_04_navy_sailors"
    folder.mkdir()
    shutil.copy2(SCORE, str(folder / "score_pp04.yaml"))
    module = load("build_pp04_cli", "build_pp04.py")
    module.SCORE = str(folder / "score_pp04.yaml")
    module.MIDI = str(folder / "pp_04_navy_sailors.mid")
    module.REPORT = str(folder / "pp_04_score_report.json")
    module.MELODY = str(folder / "melody_lead.json")

    assert module.main() == 0
    assert (folder / "pp_04_navy_sailors.mid").exists()
    written = json.loads((folder / "pp_04_score_report.json").read_text(encoding="utf-8"))
    assert written["bars"] == 32
    assert written["notes"] == committed_report()["notes"]
    assert json.loads((folder / "melody_lead.json").read_text(encoding="utf-8"))
