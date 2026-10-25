"""tests for tools/drive_v2.py, the PP-DRIVE v2 builder.

The checks are the properties the cue depends on: every bar sums to six eighths, the hook cell
is an arch with one leap and mostly steps, the cell returns as one motif, and the drum figure
actually changes every 4 and every 8 bars.
"""

import importlib.util
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import drive_v2  # noqa: E402


def test_plan_covers_every_bar_once():
    assert sorted(drive_v2.PLAN) == list(range(1, 126))


def test_every_bar_sums_to_six_eighths():
    for bar, token in drive_v2.PLAN.items():
        if token == "rest":
            continue
        if token.startswith("hold:"):
            continue
        notes = drive_v2.LITERAL.get(token) or drive_v2.CELL_HALVES.get(token)
        assert notes is not None, (bar, token)
        assert sum(dur for _name, dur in notes) == 6, (bar, token, notes)


def test_hook_cell_is_an_arch_with_one_leap():
    pitches = [drive_v2.midi_of(name) for name, _dur in drive_v2.CELL_A + drive_v2.CELL_B]
    intervals = [b - a for a, b in zip(pitches, pitches[1:])]
    steps = [gap for gap in intervals if abs(gap) <= 2]
    leaps = [gap for gap in intervals if abs(gap) >= 4]
    assert len(leaps) == 1, intervals
    assert len(steps) / float(len(intervals)) >= 0.65, intervals
    assert max(pitches) - min(pitches) <= 18
    rising = [gap > 0 for gap in intervals if gap != 0]
    turns = sum(1 for a, b in zip(rising, rising[1:]) if a != b)
    assert turns == 1, rising           # one turn is an arch


def test_cell_is_pitch_stable_so_it_counts_as_one_return():
    # the cell is not transposed per section: its pitch classes are the same in every bar
    classes = {drive_v2.midi_of(name) % 12 for name, _dur in drive_v2.CELL_A + drive_v2.CELL_B}
    assert classes == {0, 2, 4, 5, 7, 9}   # C D E F G A, diatonic to Am, C, F and Dm


def test_drum_figure_changes_every_four_and_every_eight_bars():
    four = [drive_v2.drum_bar(bar) for bar in range(2, 6)]
    assert len({tuple(bar) for bar in four}) > 1, four
    eight = [drive_v2.drum_bar(bar) for bar in range(2, 12)] + [drive_v2.drum_bar(81)]
    assert len({tuple(bar) for bar in eight}) > 2, eight
    roll = drive_v2.drum_bar(8)          # the last bar of the first eight bar span
    assert [pitch for _off, _len, pitch, _vel in roll] == [drive_v2.HAT_HARD] + list(drive_v2.FILL)


def test_drum_holes_are_where_the_return_needs_them():
    for bar in (24, 25, 58, 59, 124):
        assert drive_v2.drum_bar(bar) == []
    assert drive_v2.drum_bar(23)


def test_snap_removes_the_flat_ninth_only():
    chords = {1: "E7"}
    # F over E7 is the flat ninth, so it moves down a semitone; A over E7 is the eleventh and stays
    assert drive_v2.snap(1, drive_v2.midi_of("F5"), chords) == drive_v2.midi_of("E5")
    assert drive_v2.snap(1, drive_v2.midi_of("A4"), chords) == drive_v2.midi_of("A4")


def test_build_melody_on_the_real_score():
    source = os.path.join(ROOT, "assets", "audio", "pp_drive", "score_pp_drive.yaml")
    with open(source, encoding="utf-8") as handle:
        score = yaml.safe_load(handle)
    melody = drive_v2.build_melody(score)
    assert sorted(melody) == list(range(1, 126))
    for bar, notes in melody.items():
        assert sum(dur for _name, dur in notes) == 6, (bar, notes)
        for name, _dur in notes:
            if name != "r":
                assert drive_v2.midi_of(name) <= 88, (bar, name)
                assert drive_v2.midi_of(name) >= 48, (bar, name)
