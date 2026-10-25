"""tests for assets/audio/pp_drive/cue_cut_v3.py, the shot list's cut grid proof.

The script is the card's evidence, so the properties checked here are the ones the card asks for
and nothing more: the twelve shots add to the film length, every hard cut rounds to the bar the
shot list names, every one of those bars is attacked in the arranged MIDI, the dump carries a
marker per cut, and the cue is 178 seconds within one bar.

The script is imported and run once, not shelled out to, because this suite runs inside a gate with
a short budget and a fresh interpreter for every test would spend the budget on startup. It writes
its two artefacts beside itself exactly as it does when it is run as a command, so what is asserted
is what ships.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = os.path.join(ROOT, "assets", "audio", "pp_drive")
CUE_MAP = os.path.join(FOLDER, "cue_map_v3.json")
DUMP = os.path.join(FOLDER, "cut_dump_v3.txt")

if FOLDER not in sys.path:
    sys.path.insert(0, FOLDER)

import cue_cut_v3  # noqa: E402

_EXIT = cue_cut_v3.build_map()


def payload():
    with open(CUE_MAP, encoding="utf-8") as handle:
        return json.load(handle)


def test_the_script_returns_zero():
    assert _EXIT == 0


def test_the_shots_add_to_the_film_length():
    boss = payload()
    assert boss["film_steps"] == 10680
    assert boss["film_seconds"] == 178.0
    assert len(boss["shots"]) == 12
    assert len(boss["cuts"]) == 11


def test_every_check_the_script_makes_passes():
    checks = payload()["checks"]
    assert checks["shot_sum_matches_cuts"] is True
    assert checks["every_cut_rounds_to_the_stated_bar"] is True
    assert checks["every_cut_bar_attacked"] is True


def test_the_cuts_are_the_bars_the_shot_list_names():
    assert [cut["bar"] for cut in payload()["cuts"]] == [8, 18, 25, 34, 46, 59, 69, 79, 92, 105, 113]


def test_the_drift_is_one_cuts_rounding_and_not_a_lattice_offset():
    """Decision D18: the cut steps are round(bar x 85.714), so each is within half a step of its own downbeat.

    The retired 86 step snap is the counter-example, and it is asserted against rather than described: on that
    lattice every cut runs late by bar x 0.286 steps, which is 32 steps at the last cut.
    """
    cuts = payload()["cuts"]
    per_bar = payload()["grid"]["steps_per_bar"]
    for cut in cuts:
        exact = cut["bar"] * per_bar
        assert abs(cut["step"] - exact) <= 0.5, (cut["bar"], cut["step"], exact)
        retired = cut["bar"] * (86 - per_bar)
        assert abs(cut["drift_steps"]) < retired, (cut["bar"], cut["drift_steps"], retired)
    assert max(abs(cut["drift_steps"]) for cut in cuts) <= 0.5


def test_the_dump_has_a_line_a_bar_and_a_marker_a_cut():
    with open(DUMP, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    bars = [line for line in lines if line[:3].strip().isdigit() and "|" in line]
    assert len(bars) == 125
    assert len([line for line in bars if ">> CUT" in line]) == 11


def test_the_cue_is_178_seconds_within_one_bar():
    boss = payload()
    assert abs(boss["cue_seconds"] - 178.0) <= boss["grid"]["seconds_per_bar"]
