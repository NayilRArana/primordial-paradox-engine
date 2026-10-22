"""Tests for the drum varier and the dissonance injector (tools/spice.py, MUS-SPICE).

What is proved here, rather than asserted in a comment:

  - the drums are replaced bar by bar from the pattern library: every bar the
    arranger gave a drum note gets a pattern, a bar it left silent stays silent,
    the noise channel never plays two hits at once, and the DMC channel only
    ever plays the kick and the snare;
  - the ladder climbs with the strength: more fills, ghost notes, displaced
    accents and kicked dropped bars at 3 than at 1, and a crash on the first
    drum bar of every section;
  - the dissonance count climbs with the strength and follows the rate policy:
    a device never lands on a frozen leitmotif bar unless it is the pad's flat
    ninth, never on the first or last bar of a section;
  - the leitmotif bars of the melody are byte identical, and every melody note
    outside a device bar survives unchanged;
  - the arrangement's own note ceiling is never raised, and hook_score.py does
    not drop by more than five points;
  - strength 0 changes nothing at all;
  - two runs with the same seed are byte identical, and two different seeds are
    allowed to choose different patterns;
  - the humanizer rerun and the score yaml input both work end to end.

The tests read the committed title theme v3 MIDI and write only into a throwaway
folder. They never open a window and never touch the network.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import hook_score    # noqa: E402
import humanize      # noqa: E402
import spice         # noqa: E402

V3_MIDI = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "title_theme_v3_126.mid")
V3_SCORE = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "score_v3.yaml")

DIVISION = 480
BEATS_PER_BAR = 3
BAR = BEATS_PER_BAR * DIVISION


def read_song(path=V3_MIDI):
    return hook_score.read_smf(path)


def score_dict():
    return spice.load_score(V3_SCORE)


def spiced(song=None, drums=2, dissonance=2, seed=spice.DEFAULT_SEED, score=None):
    song = song if song is not None else read_song()
    score = score if score is not None else score_dict()
    return spice.spice_song(song, seed=seed, drums=drums, dissonance=dissonance,
                            score=score)


def notes_of(song, name):
    track = spice.track_of(song, name)
    return sorted(track["notes"]) if track else []


# ------------------------------------------------------------------- the drums

def test_every_drum_bar_gets_a_pattern_and_the_intro_stays_silent():
    song = read_song()
    out, report = spiced(song, drums=3, dissonance=0)
    bars_in = {n[0] // BAR for name in spice.DRUM_TRACKS for n in notes_of(song, name)}
    bars_out = {n[0] // BAR for name in spice.DRUM_TRACKS for n in notes_of(out, name)}
    assert bars_out == bars_in, "the drum bars changed set"
    for bar in range(4):
        assert not [n for n in notes_of(out, "noise") if n[0] // BAR == bar]
        assert not [n for n in notes_of(out, "dpcm") if n[0] // BAR == bar]
    assert report["drums"]["changed_steps"] > 0
    assert len(report["drums"]["bars"]) == len(bars_in)


def test_the_noise_channel_plays_one_sound_at_a_time():
    out, _report = spiced(drums=3, dissonance=0)
    noise = notes_of(out, "noise")
    overlapping = [(a, b) for a, b in zip(noise, noise[1:]) if b[0] < a[1]]
    assert overlapping == []
    assert {note[2] for note in noise} <= set(range(1, 16))


def test_the_dmc_channel_only_plays_the_kick_and_the_snare():
    out, _report = spiced(drums=3, dissonance=0)
    dpcm = notes_of(out, "dpcm")
    assert dpcm
    assert {note[2] for note in dpcm} <= {36, 38}
    overlapping = [(a, b) for a, b in zip(dpcm, dpcm[1:]) if b[0] < a[1]]
    assert overlapping == []


def test_a_crash_lands_on_the_first_drum_bar_of_every_section():
    out, report = spiced(drums=3, dissonance=0)
    noise = notes_of(out, "noise")
    sections = report["sections"]
    first_drum_bar_of_section = {}
    for section in sections:
        start = section["first_bar"] - 1
        for offset in range(section["bars"]):
            bar = start + offset
            if [n for n in noise if n[0] // BAR == bar]:
                first_drum_bar_of_section[section["name"]] = bar
                break
    crashed = {note[0] // BAR for note in noise if note[2] == spice.CRASH_NOTE}
    assert report["drums"]["crashes"] == len(crashed)
    for name, bar in first_drum_bar_of_section.items():
        assert bar in crashed, "no crash on the first drum bar of %s" % name


def test_the_ladder_climbs_with_the_strength():
    reports = {}
    rungs = {}
    for strength in (1, 2, 3):
        _out, report = spiced(drums=strength, dissonance=0)
        reports[strength] = report["drums"]
        rungs[strength] = {item["rung"] for item in report["drums"]["bars"].values()}
    assert (reports[1]["changed_steps"] < reports[2]["changed_steps"]
            < reports[3]["changed_steps"])
    assert reports[1]["fills"] == 0
    assert reports[2]["fills"] > 0
    assert reports[3]["fills"] > 0
    # Each strength adds rungs the one below never used: strength 1 is the home
    # pattern and the crash only, strength 3 reaches the displaced accent, the
    # kick drop out and the hemiola pair.
    assert rungs[1] <= {0, 5}
    assert {2, 4, "hemiola"} <= rungs[3]
    assert len(rungs[3]) > len(rungs[1])
    assert reports[3]["ghost_notes"] > 0
    assert reports[3]["kicks_dropped"] > 0
    assert reports[3]["hemiola_bars"], "strength 3 plays the hemiola pair"
    assert not reports[1]["hemiola_bars"]


def test_the_patterns_come_from_the_library_and_not_from_the_plain_control():
    _out, report = spiced(drums=3, dissonance=0)
    library = spice.load_library(spice.DEFAULT_DRUM_DATA)
    used = set(report["drums"]["patterns"])
    assert used
    assert used <= set(library["patterns"])
    plain = set((library.get("waltz") or {}).get("plain_control_ids") or [])
    assert not (used & plain), "the plain control pattern must not be a home groove"


# -------------------------------------------------------------- the dissonance

def test_dissonance_grows_with_the_strength_and_keeps_its_rate():
    counts = {}
    for strength in (1, 2, 3):
        _out, report = spiced(drums=0, dissonance=strength)
        counts[strength] = report["dissonance"]["injected"]
        assert counts[strength] > 0
        windows = {}
        for item in report["dissonance"]["devices"]:
            window = (item["bar"] - 1) // 8
            windows[window] = windows.get(window, 0) + 1
        for window, count in windows.items():
            assert count <= spice.STRENGTH_BUDGET[strength], (
                "eight bar window %d holds %d devices at strength %d"
                % (window, count, strength))
    assert counts[1] <= counts[2] <= counts[3]
    assert counts[3] > counts[1]


def test_the_flat_ninth_lands_once_per_sixteen_bars():
    _out, report = spiced(drums=0, dissonance=3)
    bars = [item["bar"] for item in report["dissonance"]["devices"]
            if item["device"] == "dominant_flat_nine"]
    assert bars, "strength 3 injects the dominant flat nine"
    for earlier, later in zip(bars, bars[1:]):
        assert later - earlier >= spice.SPACED_DEVICE_BARS


def test_no_melody_device_touches_a_frozen_bar():
    _out, report = spiced(drums=0, dissonance=3)
    frozen = set(report["leitmotif"]["bars"])
    for item in report["dissonance"]["devices"]:
        if item["device"] == "dominant_flat_nine":
            continue
        assert item["bar"] not in frozen, (
            "%s landed on the frozen bar %d" % (item["device"], item["bar"]))


def test_no_device_lands_on_a_section_edge():
    _out, report = spiced(drums=0, dissonance=3)
    edges = set()
    for section in report["sections"]:
        top = section["first_bar"] + section["bars"] - 1
        edges.add(section["first_bar"])
        edges.add(top)
    for item in report["dissonance"]["devices"]:
        assert item["bar"] not in edges
        assert item["bar"] != 1


def test_every_device_reports_its_bar_beat_and_rule():
    _out, report = spiced(drums=0, dissonance=3)
    for item in report["dissonance"]["devices"]:
        assert item["rule"] in {name for name, _risk in spice.DEVICE_RULES.values()}
        assert 1 <= item["beat"] <= BEATS_PER_BAR + 1
        assert item["detail"]
        assert item["voice"] in {"vrc6 pulse a", "vrc6 saw", "pulse 2"}


# --------------------------------------------------------- the frozen melody

def test_the_leitmotif_bars_are_byte_identical():
    song = read_song()
    out, report = spiced(song, drums=3, dissonance=3)
    assert report["leitmotif"]["count"] > 0
    assert report["leitmotif"]["identical"], report["leitmotif"]
    bars = set(report["leitmotif"]["bars"])
    assert {5, 9, 21}.issubset(bars), "the K statements of A and the Z of B are frozen"
    held = 0
    for bar in bars:
        before = [n for n in notes_of(song, spice.MELODY_TRACK) if n[0] // BAR == bar - 1]
        after = [n for n in notes_of(out, spice.MELODY_TRACK) if n[0] // BAR == bar - 1]
        assert before == after
        if before:
            held += 1
    # A motif return can start on a bar the melody rests in, so not every frozen
    # bar holds a note; the ones that do are the proof, and they are the majority.
    assert held >= 20, "only %d frozen bars hold a melody note" % held


def test_the_melody_outside_the_device_bars_is_untouched():
    song = read_song()
    out, report = spiced(song, drums=3, dissonance=3)
    touched = {item["bar"] - 1 for item in report["dissonance"]["devices"]}
    before = [n for n in notes_of(song, spice.MELODY_TRACK) if n[0] // BAR not in touched]
    after = [n for n in notes_of(out, spice.MELODY_TRACK) if n[0] // BAR not in touched]
    assert before == after
    assert report["melody_unchanged_outside_devices"]["passed"]


def test_hook_score_does_not_drop_by_more_than_five():
    song = read_song()
    out, report = spiced(song, drums=3, dissonance=3)
    before = spice.melody_score(song, hook_score.load_grammar()[0])
    after = spice.melody_score(out, hook_score.load_grammar()[0])
    assert before - after <= spice.DEFAULT_MAX_HOOK_DROP
    assert report["dissonance"]["hook"]["drop"] <= spice.DEFAULT_MAX_HOOK_DROP


def test_the_note_ceiling_of_the_arrangement_is_never_raised():
    song = read_song()
    peak_in = spice.max_simultaneous(song)
    for strength in (1, 2, 3):
        out, report = spiced(song, drums=strength, dissonance=strength)
        assert spice.max_simultaneous(out) <= peak_in
        assert report["peak_simultaneous_in"] == peak_in


# ----------------------------------------------------------- structure, files

def test_the_song_keeps_its_tracks_tempo_and_meter():
    song = read_song()
    out, _report = spiced(song, drums=3, dissonance=3)
    assert [t["name"] for t in out["tracks"]] == [t["name"] for t in song["tracks"]]
    assert out["division"] == song["division"]
    assert out["tempo_us"] == song["tempo_us"]
    assert out["time_sig"] == song["time_sig"]


def test_strength_zero_changes_nothing():
    song = read_song()
    out, report = spiced(song, drums=0, dissonance=0)
    assert report["dissonance"]["injected"] == 0
    assert report["drums"]["changed_steps"] == 0
    for before, after in zip(song["tracks"], out["tracks"]):
        assert sorted(before["notes"]) == sorted(after["notes"])


def test_two_runs_are_byte_identical(tmp_path):
    first = tmp_path / "one.mid"
    second = tmp_path / "two.mid"
    report_one = spice.spice_file(V3_MIDI, str(first), drums=3, dissonance=3)
    report_two = spice.spice_file(V3_MIDI, str(second), drums=3, dissonance=3)
    assert first.read_bytes() == second.read_bytes()
    assert report_one["sha256_out"] == report_two["sha256_out"]


def test_a_different_seed_may_choose_different_patterns():
    _out_default, report_default = spiced(drums=3, dissonance=0)
    _out_other, report_other = spiced(drums=3, dissonance=0, seed=spice.DEFAULT_SEED + 7)
    assert report_default["drums"]["patterns"] != report_other["drums"]["patterns"]


def test_the_report_writes_as_json(tmp_path):
    report = spice.spice_file(V3_MIDI, str(tmp_path / "out.mid"), drums=2, dissonance=2)
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    again = json.loads(path.read_text(encoding="utf-8"))
    assert again["drums"]["changed_steps"] == report["drums"]["changed_steps"]
    assert again["leitmotif"]["identical"] is True
    text = spice.format_report(report)
    assert "spice:" in text
    assert "leitmotif:" in text


def test_the_humanizer_rerun_keeps_the_eight_voices(tmp_path):
    target = tmp_path / "out.mid"
    report = spice.spice_file(V3_MIDI, str(target), drums=2, dissonance=2,
                              humanize_after=True)
    assert target.exists()
    assert report["humanize"] is not None
    assert report["humanize"]["notes_changed"] > 0
    song = hook_score.read_smf(str(target))
    assert [t["name"] for t in song["tracks"]] == [t["name"] for t in read_song()["tracks"]]


def test_a_score_yaml_is_arranged_first(tmp_path):
    target = tmp_path / "from_score.mid"
    report = spice.spice_file(V3_SCORE, str(target), drums=2, dissonance=2)
    assert target.exists()
    assert report["drums"]["changed_steps"] > 0
    song = hook_score.read_smf(str(target))
    assert len(song["tracks"]) == 9
    assert not [name for name in os.listdir(str(tmp_path)) if name.endswith(".spice-arranged.mid")]


# --------------------------------------------------------------- a small song

def synthetic_song():
    """Eight bars of the eight voice schema with one dominant bar and long notes."""
    names = ("meta", "vrc6 pulse a", "vrc6 pulse b", "vrc6 saw", "pulse 1",
             "pulse 2", "triangle", "noise", "dpcm")
    tracks = [{"name": name, "notes": [], "cc": {}} for name in names]
    by_name = {track["name"]: track for track in tracks}

    melody = by_name["vrc6 pulse a"]
    saw = by_name["vrc6 saw"]
    arpeggio = by_name["pulse 1"]
    bass = by_name["triangle"]
    noise = by_name["noise"]
    dpcm = by_name["dpcm"]

    # bar 1: E5 held for the whole bar (a neighbour host)
    melody["notes"].append((0, BAR, 76, 100))
    # bar 2: E5 then D5 (a whole tone apart, a passing host)
    melody["notes"].append((BAR, BAR + 3 * DIVISION // 2, 76, 100))
    melody["notes"].append((BAR + 3 * DIVISION // 2, 2 * BAR, 74, 100))
    for bar in range(2, 8):
        start = bar * BAR
        melody["notes"].append((start, start + 2 * DIVISION, 72 + bar % 4, 100))
        melody["notes"].append((start + 2 * DIVISION, start + BAR, 74, 100))

    for bar in range(8):
        start = bar * BAR
        for third in (0, 4, 7):
            saw["notes"].append((start, start + 2 * DIVISION, 52 + third, 80))
        arpeggio["notes"].append((start, start + DIVISION // 2, 64, 90))
        bass["notes"].append((start, start + BAR, 45, 100))
        if bar >= 2:
            noise["notes"].append((start, start + 2 * DIVISION, 5, 52))
            dpcm["notes"].append((start, start + 2 * DIVISION, 36, 112))

    return {"format": 1, "division": DIVISION, "tempo_us": 476190,
            "time_sig": (3, 4), "tracks": tracks}


def test_a_small_song_gets_drums_and_colour():
    song = synthetic_song()
    score = {"meta": {"key": "A minor"},
             "sections": {"S": {"bars": 8,
                                "chords": ["Am", "Am", "E7", "E7", "Am", "Dm", "E7", "Am"]}}}
    out, report = spice.spice_song(song, drums=2, dissonance=2, score=score)
    assert report["drums"]["changed_steps"] > 0
    assert report["dissonance"]["injected"] >= 1
    voices = {item["voice"] for item in report["dissonance"]["devices"]}
    assert voices <= {"vrc6 pulse a", "vrc6 saw", "pulse 2"}
    # The clash and the flat ninth only exist at strength 3, and both add a note,
    # so they only land where the piece still has headroom under its own note
    # ceiling: here the thin version of the eight bars, with one loud bar to set
    # the ceiling above the density of the dominant bar.
    lean = synthetic_song()
    for track in lean["tracks"]:
        if track["name"] in ("pulse 1", "pulse 2", "noise", "dpcm"):
            track["notes"] = []
    saw = next(track for track in lean["tracks"] if track["name"] == "vrc6 saw")
    for pitch in (55, 60, 64, 67):
        saw["notes"].append((7 * BAR, 7 * BAR + DIVISION, pitch, 80))
    out3, report3 = spice.spice_song(lean, drums=0, dissonance=3, score=score)
    flat_ninth = [item for item in report3["dissonance"]["devices"]
                  if item["device"] == "dominant_flat_nine"]
    assert flat_ninth, "an E7 bar must take the flat ninth at strength 3"
    saw_out = notes_of(out3, "vrc6 saw")
    added = [note for note in saw_out if note[2] % 12 == (4 + 1) % 12]
    assert added, "the flat ninth is an F over the E dominant"


def test_a_song_without_a_score_still_gets_drums():
    song = synthetic_song()
    _out, report = spice.spice_song(song, drums=2, dissonance=0, score=None)
    assert report["sections_known"] is False
    assert report["drums"]["changed_steps"] > 0
    assert any("inferred" in warning for warning in report["warnings"])
