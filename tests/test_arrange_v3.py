"""Tests for the version 3 arranger (tools/arrange.py, MUS-V3).

What is proved here, rather than asserted in a comment:

  - the version 3 score reads as seven sections in the order the score lists
    them, 52 bars at 126 bpm (74.286 s);
  - every bar holds six eighths, and the chord written in the MIDI is the
    chord in the score, section by section;
  - the melodies the card names read exactly as composed: the Kronos motif in
    bar 1 of section A, the Percy motif in bar 1 of the trio, the Hadrian
    motif in bar 5 of the trio, the octave lift in A prime and the dominant
    the loop turns on in the last bar of A return;
  - no voice writes outside its register and at most 8 notes sound at once;
  - running the arranger twice gives the same bytes, and the file it writes is
    a format 1 MIDI, 3/4, 126 bpm, with the eight tracks the renderer expects;
  - the loop starts at the first bar of section A.

The test writes only into a throwaway folder and never opens a window.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import arrange  # noqa: E402

SCORE_PATH = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "score_v3.yaml")
SECTIONS = ["intro", "A", "A_prime", "B", "B_prime", "C_trio", "A_return"]


@pytest.fixture(scope="module")
def score():
    return arrange.load_score(SCORE_PATH)


@pytest.fixture(scope="module")
def bars(score):
    return arrange.build_bars_v3(score)


@pytest.fixture(scope="module")
def arrangement(score):
    return arrange.build_arrangement_v3(score)


def bar_of(bars, section, offset):
    chosen = [bar for bar in bars if bar.section == section]
    return chosen[offset]


def names_of(bar):
    return [arrange.midi_to_name(pitch) for _slot, _length, pitch in bar.melody
            if pitch is not None]


# ------------------------------------------------------------------ the score


def test_sections_are_in_the_order_the_score_lists(score):
    assert arrange.v3_section_names(score) == SECTIONS


def test_the_piece_is_52_bars_at_126_bpm(bars, arrangement):
    assert len(bars) == 52
    assert arrangement.meta["bpm"] == 126
    assert round(len(bars) * 3 * 60.0 / arrangement.meta["bpm"], 3) == 74.286


def test_section_lengths(score, bars):
    counts = {}
    for bar in bars:
        counts[bar.section] = counts.get(bar.section, 0) + 1
    assert counts["intro"] == 4
    for name in SECTIONS[1:]:
        assert counts[name] == 8
        assert int(score["sections"][name]["bars"]) == 8


def test_every_bar_holds_six_eighths(bars):
    for bar in bars:
        total = sum(length for _slot, length, _pitch in bar.melody)
        assert total == 6, "bar %d of %s holds %d eighths" % (bar.number, bar.section, total)


def test_the_chord_of_every_bar_is_the_chord_in_the_score(score, bars):
    for name in SECTIONS:
        written = [arrange.chord_symbol_of_bar(bar) for bar in bars if bar.section == name]
        assert written == list(score["sections"][name]["chords"]), name


def test_the_key_is_a_minor(score):
    assert score["meta"]["key"] == "A minor"


# ----------------------------------------------------------------- the melodies


def test_kronos_motif_in_bar_one_of_section_a(bars):
    assert names_of(bar_of(bars, "A", 0)) == ["E5", "C5", "D5", "E5"]


def test_kronos_answer_in_bar_two_of_section_a(bars):
    assert names_of(bar_of(bars, "A", 1)) == ["B4", "G#4", "A4", "B4"]


def test_percy_motif_in_bar_one_of_the_trio(bars):
    assert names_of(bar_of(bars, "C_trio", 0)) == ["E4", "G4", "B4"]


def test_percy_crest_and_fall_in_bar_two_of_the_trio(bars):
    assert names_of(bar_of(bars, "C_trio", 1)) == ["E5", "D5", "B4"]


def test_hadrian_motif_in_bar_five_of_the_trio(bars):
    assert names_of(bar_of(bars, "C_trio", 4)) == ["D5", "C#5"]


def test_hadrian_second_prong_in_bar_six_of_the_trio(bars):
    assert names_of(bar_of(bars, "C_trio", 5)) == ["A4", "G#4"]


def test_a_prime_lifts_the_first_four_bars_one_octave(bars):
    for offset in range(4):
        low = [pitch for _slot, _length, pitch in bar_of(bars, "A", offset).melody if pitch]
        high = [pitch for _slot, _length, pitch in bar_of(bars, "A_prime", offset).melody if pitch]
        assert high == [pitch + 12 for pitch in low], "bar %d" % (offset + 1)
    for offset in range(4, 8):
        assert names_of(bar_of(bars, "A_prime", offset)) == names_of(bar_of(bars, "A", offset))


def test_b_prime_raises_bars_five_and_six_one_octave(bars):
    for offset in (4, 5):
        low = [pitch for _slot, _length, pitch in bar_of(bars, "B", offset).melody if pitch]
        high = [pitch for _slot, _length, pitch in bar_of(bars, "B_prime", offset).melody if pitch]
        assert high == [pitch + 12 for pitch in low], "bar %d" % (offset + 1)
    for offset in (0, 1, 2, 3, 6, 7):
        assert names_of(bar_of(bars, "B_prime", offset)) == names_of(bar_of(bars, "B", offset))


def test_a_return_holds_the_dominant_in_its_last_bar(bars):
    last = bar_of(bars, "A_return", 7)
    assert names_of(last) == ["B4"]
    assert sum(length for _slot, length, _pitch in last.melody) == 6


def test_the_directive_reader_refuses_an_unknown_wording():
    score = {"sections": {"A": {"bars": 1, "chords": ["Am"],
                                "melody": [[["A4", 6]]]},
                          "B": {"bars": 1, "chords": ["Am"],
                                "melody": "something the arranger cannot read"}}}
    with pytest.raises(ValueError):
        arrange.build_bars_v3(score)


# --------------------------------------------------------------- the writing


def test_no_voice_writes_outside_its_register(arrangement):
    from_check = arrange.self_check_v3(arrangement)
    assert from_check["out_of_range"] == []


def test_at_most_eight_notes_sound_at_once(arrangement):
    assert arrange.max_simultaneous(arrangement) <= 8


def test_every_voice_writes_something(arrangement):
    for name in arrange.TRACK_NAMES:
        assert arrangement.notes[name], name


def test_the_loop_starts_at_the_first_bar_of_section_a(arrangement):
    assert arrangement.meta["loop_start_bar"] == 5


def test_the_file_is_deterministic(tmp_path, score):
    first = arrange.write_midi(arrange.build_arrangement_v3(score),
                               str(tmp_path / "a.mid"))
    second = arrange.write_midi(arrange.build_arrangement_v3(score),
                                str(tmp_path / "b.mid"))
    assert first == second


def test_the_written_file_is_a_midi_with_eight_voice_tracks(tmp_path, score):
    path = str(tmp_path / "v3.mid")
    data = arrange.write_midi(arrange.build_arrangement_v3(score), path)
    parsed = arrange.read_midi(data)
    assert parsed["format"] == 1
    assert parsed["division"] == arrange.PPQ
    names = [name for name, _notes in parsed["tracks"]]
    assert names == ["meta"] + list(arrange.TRACK_NAMES)


def test_the_tempo_and_the_time_signature_are_in_the_file(tmp_path, score):
    path = str(tmp_path / "v3.mid")
    data = arrange.write_midi(arrange.build_arrangement_v3(score), path)
    parsed = arrange.read_midi(data)
    assert parsed["tempo_us"] == arrange._microseconds_per_quarter(126)
    assert parsed["time_sig"] == (3, 4)


def test_the_self_check_reads_the_whole_piece(tmp_path, score):
    path = str(tmp_path / "v3.mid")
    arrangement = arrange.build_arrangement_v3(score)
    data = arrange.write_midi(arrangement, path)
    report = arrange.self_check_v3(arrangement, data)
    assert report["bars"] == 52
    assert report["midi_bpm"] == 126
    assert report["midi_time_signature"] == "3/4"
    assert report["chords_match_score"] is True
    assert report["tempo_meta_matches_score"] is True
    assert report["loop_start_bar"] == 5
    assert report["loop_bars"] == 48
    assert report["max_simultaneous_notes"] <= 8
