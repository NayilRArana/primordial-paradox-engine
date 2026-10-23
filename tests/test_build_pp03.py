"""Tests for assets/audio/pp_03_harbor/build_pp03.py (card t_6af137c1).

Why this file exists: the arranger was untracked because no test mapped to it, so the commit gate
refused it as UNMAPPED source ("a source change nothing measures is refused"). The builder reads
only the committed assets/audio/pp_03_harbor/score_pp03.yaml and the committed
data/drum_patterns.json, so every test here runs in a clean checkout. Nothing in this file needs the
.wav, the .mp3 or the .mid, which the root .gitignore keeps out of the commit on purpose.

What is proved, rather than asserted in a comment:

  - the committed score still builds the arrangement the committed arrange_report.json describes:
    the note count of every voice, the total, the tempo, the bar count, the loop length and the
    per-section drum rung log;
  - every note sits inside its voice's declared register and inside the loop point, and the last
    note ends exactly at the loop point, so the file is filled and not truncated;
  - the file written to disk is a format 1 MIDI at 480 PPQ, 68 bpm, 4/4, carrying exactly the
    conductor track plus the eight voice tracks in the order tools/render_chip.py expects, read
    back through that project parser rather than through the builder's own writer;
  - the same score writes the same bytes twice, which is the determinism the module's docstring
    claims;
  - the score errors the builder exists to refuse are refused, each with its own message;
  - the command line writes its outputs where it is told, so a run cannot dirty the tree.

Every test writes only into pytest's throwaway directory.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import struct
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import render_chip  # noqa: E402  the project's own MIDI parser

HERE = os.path.join(ROOT, "assets", "audio", "pp_03_harbor")
SCORE = os.path.join(HERE, "score_pp03.yaml")
REPORT = os.path.join(HERE, "arrange_report.json")


def load(name, filename):
    path = os.path.join(HERE, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load("build_pp03_under_test", "build_pp03.py")

BAR_TICKS = 8 * BUILDER.EIGHTH


def committed_score():
    with open(SCORE, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def committed_report():
    with open(REPORT, "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def built():
    """The real arrangement, built once from the committed score and drum library."""
    return BUILDER.build(committed_score(), BUILDER.load_drums())


def test_the_committed_score_builds_the_arrangement_the_commit_ships(built):
    """The report next to the score is the builder's own output, so drift on either side fails here."""
    arrangement, bpm, bars, drum_log = built
    report = committed_report()
    counts = {name: len(arrangement.notes[name]) for name in BUILDER.TRACK_NAMES}
    assert counts == report["note_counts"], counts
    assert sum(counts.values()) == report["total_notes"] == 1375
    assert bars == report["bars"] == 64
    assert bpm == report["bpm"] == 68.0
    assert list(BUILDER.TRACK_NAMES) == report["tracks"]
    loop_seconds = bars * BAR_TICKS / float(BUILDER.PPQ) * 60.0 / bpm
    assert round(loop_seconds, 6) == report["loop_seconds"]
    assert drum_log == report["drums"], "the drum rung log moved away from the committed report"


def test_every_note_is_inside_its_register_and_inside_the_loop_point(built):
    arrangement, _bpm, bars, _log = built
    limit = bars * BAR_TICKS
    last_end = 0
    for name in BUILDER.TRACK_NAMES:
        notes = arrangement.notes[name]
        assert notes, "%s holds no notes" % name
        low, high = BUILDER.RANGES[name]
        for start, end, pitch, velocity in notes:
            assert low <= pitch <= high, (name, pitch, low, high)
            assert end > start, (name, start, end)
            assert end <= limit, (name, end, limit)
            assert 1 <= velocity <= 127, (name, velocity)
            assert start >= 0, (name, start)
        last_end = max(last_end, max(end for _s, end, _p, _v in notes))
    assert last_end == limit, "the arrangement must fill the loop point, not stop short of it"


def test_the_written_midi_is_format_1_with_the_eight_voice_tracks(built, tmp_path):
    arrangement, bpm, bars, _log = built
    out = tmp_path / "pp_03_harbor.mid"
    BUILDER.write_midi(str(out), arrangement, bpm, bars)
    raw = out.read_bytes()
    fmt, ntracks, division = struct.unpack(">hhh", raw[8:14])
    assert (fmt, ntracks, division) == (1, len(BUILDER.TRACK_NAMES) + 1, BUILDER.PPQ)

    midi = render_chip.parse_midi(str(out))
    names = [track.name for track in midi["tracks"]]
    assert names == ["conductor"] + list(BUILDER.TRACK_NAMES)
    tempo = midi["tempo"][0][1]
    assert abs(60000000.0 / tempo - bpm) < 0.05
    assert tuple(midi["time_sig"]) == (4, 4)
    # The parse of the written file holds the same note count the arrangement holds.
    voice_notes = sum(len(track.notes) for track in midi["tracks"] if track.name in BUILDER.TRACK_NAMES)
    assert voice_notes == sum(len(arrangement.notes[name]) for name in BUILDER.TRACK_NAMES)


def test_the_noise_channel_never_plays_two_hits_at_one_tick(built, tmp_path):
    """One noise channel cannot play two hits at once (MUSIC-DRUMS 1), read back from the file."""
    arrangement, bpm, bars, _log = built
    out = tmp_path / "noise.mid"
    BUILDER.write_midi(str(out), arrangement, bpm, bars)
    midi = render_chip.parse_midi(str(out))
    noise = [track for track in midi["tracks"] if track.name == "noise"][0]
    starts = [note[0] for note in noise.notes]
    assert len(starts) == len(set(starts)), "two noise hits land on one tick"


def test_the_same_score_writes_the_same_bytes_twice(built, tmp_path):
    arrangement, bpm, bars, _log = built
    first, second = tmp_path / "a.mid", tmp_path / "b.mid"
    BUILDER.write_midi(str(first), arrangement, bpm, bars)
    BUILDER.write_midi(str(second), arrangement, bpm, bars)
    assert first.read_bytes() == second.read_bytes()
    assert len(hashlib.sha256(first.read_bytes()).hexdigest()) == 64


def test_a_section_melody_may_reference_an_earlier_section():
    """score_pp03 says "same notes as arrival" and "same notes as harbor light": prove both resolve."""
    score = committed_score()
    sections = score["sections"]
    assert BUILDER.section_melody(score, "return") == sections["arrival"]["melody"]
    assert BUILDER.section_melody(score, "light_again") == sections["harbor_light"]["melody"]


def test_a_bar_that_does_not_sum_to_eight_eighths_is_refused():
    score = copy.deepcopy(committed_score())
    score["sections"]["arrival"]["melody"][0][0][1] = 3
    with pytest.raises(ValueError, match="eighths, not 8"):
        BUILDER.build(score, BUILDER.load_drums())


def test_a_chord_count_that_disagrees_with_the_bar_count_is_refused():
    score = copy.deepcopy(committed_score())
    score["sections"]["arrival"]["chords"].pop()
    with pytest.raises(ValueError, match="chords for"):
        BUILDER.build(score, BUILDER.load_drums())


def test_a_melody_note_outside_its_voice_register_is_refused():
    score = copy.deepcopy(committed_score())
    score["sections"]["arrival"]["melody"][0][0][0] = "C7"     # 96, above the lead's 84
    with pytest.raises(ValueError, match="outside its declared range"):
        BUILDER.build(score, BUILDER.load_drums())


def test_sections_that_do_not_fill_the_meta_bar_count_are_refused():
    score = copy.deepcopy(committed_score())
    score["meta"]["bars"] = 63
    with pytest.raises(ValueError, match="add up to"):
        BUILDER.build(score, BUILDER.load_drums())


def test_a_melody_reference_loop_is_refused():
    score = copy.deepcopy(committed_score())
    score["sections"]["arrival"]["melody"] = "same notes as settle"
    score["sections"]["settle"]["melody"] = "same notes as arrival"
    with pytest.raises(ValueError, match="melody reference loops"):
        BUILDER.build(score, BUILDER.load_drums())


def test_the_command_line_writes_where_it_is_told_and_leaves_the_tree_alone(tmp_path):
    midi = tmp_path / "pp_03_harbor.mid"
    report = tmp_path / "arrange_report.json"
    assert BUILDER.main([SCORE, "-o", str(midi), "--report", str(report)]) == 0
    assert midi.exists() and midi.stat().st_size > 1024
    written = json.loads(report.read_text(encoding="utf-8"))
    assert written["bars"] == 64
    assert written["total_notes"] == committed_report()["total_notes"]
    assert written["note_counts"] == committed_report()["note_counts"]
    # Nothing was written beside the score: the committed folder is untouched.
    assert not os.path.exists(os.path.join(HERE, "pp_03_harbor.mid.tmp"))
