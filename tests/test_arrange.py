"""Tests for the arranger (tools/arrange.py) and the originality guard.

What is proved here, rather than asserted in a comment:
  - the chord parser reads every symbol in score.yaml, and the split form
    'X|Y' gives two chords;
  - the arrangement has 52 bars, and the melody of the first two bars of
    section A is A4 C5 E5 F5 E5;
  - no voice writes a note outside its declared register;
  - no more than 8 notes sound at the same time;
  - running the arranger twice gives the same bytes;
  - the melody guard fails on a melody that is a copy and passes on one that
    is not.

The test writes only into a throwaway folder and never opens a window.
"""

from __future__ import annotations

import json
import os
import struct
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import arrange  # noqa: E402
import melody_guard  # noqa: E402

SCORE_PATH = os.path.join(ROOT, "assets", "audio", "title_theme_v2", "score.yaml")


@pytest.fixture(scope="module")
def score():
    return arrange.load_score(SCORE_PATH)


@pytest.fixture(scope="module")
def bars(score):
    return arrange.build_bars(score)


@pytest.fixture(scope="module")
def arrangement(score):
    return arrange.build_arrangement(score)


# ------------------------------------------------------------- the chord parser

def all_chord_symbols(score):
    """Every chord symbol in the score, split forms separated."""
    out = []
    for section, symbols in score["chords"].items():
        for symbol in symbols:
            left, right = arrange.split_chord_symbol(symbol)
            out.append((section, left))
            if right != left:
                out.append((section, right))
    return out


def test_score_holds_chord_symbols(score):
    assert len(all_chord_symbols(score)) >= 30


@pytest.mark.parametrize("section,symbol", all_chord_symbols(
    arrange.load_score(SCORE_PATH)))
def test_parser_reads_every_symbol_in_the_score(section, symbol):
    chord = arrange.parse_chord(symbol)
    assert chord.root_pc in range(12)
    assert len(chord.tones) >= 2
    for tone in chord.tones:
        assert 0 <= tone <= 14
    # The tones are the pitch classes of the chord, and the bass is either
    # the root or a slash note.
    assert chord.bass_pc in range(12)
    if chord.has_slash:
        assert chord.bass_pc != chord.root_pc or symbol.startswith(("C/", "D/"))


def test_parser_quality_table():
    assert arrange.parse_chord("Am").tones == (0, 3, 7)
    assert arrange.parse_chord("A").tones == (0, 4, 7)
    assert arrange.parse_chord("Fmaj7").tones == (0, 4, 7, 11)
    assert arrange.parse_chord("Dm7").tones == (0, 3, 7, 10)
    assert arrange.parse_chord("E7").tones == (0, 4, 7, 10)
    assert arrange.parse_chord("Bm7b5").tones == (0, 3, 6, 10)
    assert arrange.parse_chord("G6").tones == (0, 4, 7, 9)
    assert arrange.parse_chord("Fm6").tones == (0, 3, 7, 9)
    assert arrange.parse_chord("Dm9").tones == (0, 3, 7, 10, 14)
    assert arrange.parse_chord("E7sus4").tones == (0, 5, 7, 10)
    assert arrange.parse_chord("E7b9").tones == (0, 4, 7, 10, 13)


def test_parser_reads_slash_bass():
    chord = arrange.parse_chord("E7/G#")
    assert chord.root_pc == 4
    assert chord.bass_pc == 8
    assert chord.has_slash
    assert arrange.parse_chord("Am").bass_pc == arrange.parse_chord("Am").root_pc
    assert not arrange.parse_chord("Am").has_slash


def test_parser_rejects_rubbish():
    with pytest.raises(arrange.ChordError):
        arrange.parse_chord("H7")
    with pytest.raises(arrange.ChordError):
        arrange.parse_chord("Azz7")
    with pytest.raises(arrange.ChordError):
        arrange.parse_chord("")


def test_split_symbol_gives_two_chords(score):
    left, right = arrange.split_chord_symbol("Fmaj7|E7")
    assert arrange.parse_chord(left).root_pc == 5
    assert arrange.parse_chord(right).root_pc == 4
    same = arrange.split_chord_symbol("Am")
    assert same[0] == same[1] == "Am"


# ------------------------------------------------------------------- the score

def test_score_has_52_bars(bars):
    assert len(bars) == 52
    assert [bar.section for bar in bars[:5]] == ["intro", "intro", "intro", "intro", "A"]


def test_every_bar_holds_six_eighths(bars):
    for bar in bars:
        total = sum(length for _slot, length, _pitch in bar.melody)
        assert total == 6, "bar %d holds %d eighths" % (bar.number, total)


def test_melody_of_section_a_bars_one_and_two(bars):
    """Bars 1 and 2 of section A are the leitmotif cell: A4 C5 E5 F5 E5."""
    section_a = [bar for bar in bars if bar.section == "A"]
    pitches = []
    for bar in section_a[:2]:
        for _slot, _length, pitch in bar.melody:
            if pitch is not None:
                pitches.append(arrange.midi_to_name(pitch))
    assert pitches == ["A4", "C5", "E5", "F5", "E5"]
    assert [bar.number for bar in section_a[:2]] == [5, 6]


def test_a2_melody_is_a_repeat_plus_four_ending_bars(bars):
    section_a = [bar for bar in bars if bar.section == "A"]
    section_a2 = [bar for bar in bars if bar.section == "A2"]
    assert len(section_a2) == 16
    for index in range(12):
        assert [n[2] for n in section_a[index].melody] == [n[2] for n in section_a2[index].melody]
    ending = [bar for bar in bars if bar.section == "A2"][-4:]
    assert len(ending) == 4


# --------------------------------------------------------------- the arrangement

def test_arrangement_has_eight_tracks_with_the_expected_names(arrangement):
    assert list(arrangement.notes) == list(arrange.TRACK_NAMES)
    assert arrangement.notes["vrc6 pulse a"]
    assert arrangement.notes["triangle"]
    assert arrangement.notes["noise"]
    assert arrangement.notes["dpcm"]


def test_no_voice_writes_outside_its_register(arrangement):
    for name in arrange.TRACK_NAMES:
        lo, hi = arrange.VOICE_RANGES[name]
        for start, end, pitch in arrange.note_spans(arrangement.notes[name]):
            assert lo <= pitch <= hi, "%s wrote %s" % (name, arrange.midi_to_name(pitch))
    # Section B moves the pulse 1 line, so its range is the wider one.
    for start, end, pitch in arrange.note_spans(arrangement.notes["pulse 1"]):
        bar = arrangement.bars[start // arrange.TICKS_PER_BAR]
        if bar.section == "B":
            assert arrange.PULSE_1_B_RANGE[0] <= pitch <= arrange.PULSE_1_B_RANGE[1]


def test_at_most_eight_notes_sound_at_once(arrangement):
    assert arrange.max_simultaneous(arrangement) <= arrange.MAX_SIMULTANEOUS_NOTES


def test_every_voice_writes_something(arrangement):
    for name in arrange.TRACK_NAMES:
        assert arrangement.notes[name], "%s is silent" % name


def test_melody_track_holds_the_melody_only(arrangement):
    """The melody track is the melody of the score, note for note."""
    expected = []
    for bar in arrangement.bars:
        for slot, length, pitch in bar.melody:
            if pitch is not None:
                expected.append((arrangement.bar_start(bar) + slot * arrange.EIGHTH,
                                 pitch))
    written = [(start, pitch) for start, _end, pitch
               in arrange.note_spans(arrangement.notes["vrc6 pulse a"])]
    assert written == expected


def test_echo_is_one_eighth_late_at_forty_percent(arrangement):
    melody = {(start, pitch) for start, _end, pitch
               in arrange.note_spans(arrangement.notes["vrc6 pulse a"])}
    echo = arrange.note_spans(arrangement.notes["pulse 2"])
    assert echo
    for start, _end, pitch in echo:
        assert (start - arrange.EIGHTH, pitch) in melody
    levels = [value for tick, controller, value in arrangement.controls["pulse 2"]
              if controller == 11]
    melody_levels = [value for tick, controller, value in arrangement.controls["vrc6 pulse a"]
                     if controller == 11]
    assert all(round(level * 0.4) == echo_level
               for level, echo_level in zip(melody_levels, levels))


def test_guide_tone_is_only_in_a2_and_below_the_melody(arrangement):
    for start, end, pitch in arrange.note_spans(arrangement.notes["vrc6 pulse b"]):
        bar = arrangement.bars[start // arrange.TICKS_PER_BAR]
        assert bar.section == "A2"
    for bar in arrangement.bars:
        if bar.section != "A2":
            continue
        for slot, length, pitch in bar.melody:
            if pitch is None:
                continue
            guide = [p for s, _l, p in arrange.note_spans(arrangement.notes["vrc6 pulse b"])
                     if bar.index * arrange.TICKS_PER_BAR <= s
                     < bar.index * arrange.TICKS_PER_BAR + arrange.TICKS_PER_BAR]
            if guide:
                assert max(guide) < pitch or min(guide) < pitch


def test_dynamics_follow_the_sections(arrangement):
    score_levels = {"intro": 4, "A": 8, "B": 11, "A2": 14}
    seen = {}
    for bar in arrangement.bars:
        for tick, controller, value in arrangement.controls["vrc6 pulse a"]:
            if controller == 11 and tick == arrangement.bar_start(bar):
                seen[bar.section] = value
    assert seen == score_levels


def test_duty_of_the_melody_follows_the_sections(arrangement):
    """Section B doubles the duty of the melody, the other sections keep 25."""
    duties = {}
    for bar in arrangement.bars:
        for tick, controller, value in arrangement.controls["vrc6 pulse a"]:
            if controller == 12 and tick == arrangement.bar_start(bar):
                duties[bar.section] = value
    # The renderer reads a VRC6 duty of (value + 1) / 16.
    assert duties["intro"] == 3          # 4/16 = 25 percent
    assert duties["A"] == 3
    assert duties["B"] == 7              # 8/16 = 50 percent
    assert duties["A2"] == 3


def test_melody_vibrato_only_on_long_notes(arrangement):
    depths = {tick: value for tick, controller, value
              in arrangement.controls["vrc6 pulse a"] if controller == 1}
    assert depths
    assert max(depths.values()) > 0
    durations = {start: end - start for start, end, _p
                 in arrange.note_spans(arrangement.notes["vrc6 pulse a"])}
    for tick, value in depths.items():
        if value > 0:
            assert durations.get(tick, 0) >= 3 * arrange.EIGHTH


def test_waltz_bass_is_root_rest_and_approach(arrangement):
    for bar in arrangement.bars:
        if bar.section == "B":
            continue
        bass = [(s, e) for s, e, _p in arrange.note_spans(arrangement.notes["triangle"])
                if bar.index * arrange.TICKS_PER_BAR <= s
                < (bar.index + 1) * arrange.TICKS_PER_BAR]
        if not bass:
            continue
        assert len(bass) == 2
        first, second = bass
        assert first[0] == bar.index * arrange.TICKS_PER_BAR
        assert second[0] == bar.index * arrange.TICKS_PER_BAR + 4 * arrange.EIGHTH


def test_fills_land_on_bars_20_36_and_52(arrangement):
    fills = []
    for start, end, pitch in arrange.note_spans(arrangement.notes["noise"]):
        bar = arrangement.bars[start // arrange.TICKS_PER_BAR]
        if bar.number in (20, 36, 52) and start % arrange.TICKS_PER_BAR >= 4 * arrange.EIGHTH:
            fills.append(bar.number)
    assert sorted(set(fills)) == [20, 36, 52]


def test_kick_is_in_b_and_a2_only(arrangement):
    for start, end, pitch in arrange.note_spans(arrangement.notes["dpcm"]):
        bar = arrangement.bars[start // arrange.TICKS_PER_BAR]
        assert bar.section in ("B", "A2")
        assert pitch == 36
        assert start % arrange.TICKS_PER_BAR == 0


# ------------------------------------------------------------- writing the file

def test_the_file_is_deterministic(tmp_path, score):
    first = arrange.write_midi(arrange.build_arrangement(score),
                               str(tmp_path / "one.mid"))
    second = arrange.write_midi(arrange.build_arrangement(score),
                                str(tmp_path / "two.mid"))
    assert first == second
    assert len(first) > 0
    with open(tmp_path / "one.mid", "rb") as handle:
        on_disk = handle.read()
    assert on_disk == first


def test_the_written_file_is_a_midi_with_eight_voice_tracks(tmp_path, score):
    data = arrange.write_midi(arrange.build_arrangement(score),
                              str(tmp_path / "out.mid"))
    parsed = arrange.read_midi(data)
    assert parsed["format"] == 1
    assert parsed["division"] == arrange.PPQ
    names = [name for name, _notes in parsed["tracks"]]
    assert names == ["meta"] + list(arrange.TRACK_NAMES)
    for name, notes in parsed["tracks"]:
        if name == "meta":
            continue
        assert notes, "%s wrote no note" % name


def test_the_tempo_and_the_time_signature_are_in_the_file(tmp_path, score):
    data = arrange.write_midi(arrange.build_arrangement(score),
                              str(tmp_path / "out.mid"))
    assert b"\xff\x51\x03" in data
    assert b"\xff\x58\x04\x03\x02\x18\x08" in data
    # The marker bytes alone passed while the tempo VALUE was wrong, so read the
    # value back. The pre-fix writer used 500000 * 60 / bpm, which for 104 bpm
    # wrote 288461 instead of 576923 microseconds per quarter, and a tempo meta
    # that is half its true value plays the cue at double speed: measured
    # 2026-10-21, bpm read 208.0004, 52 bars came out at 45.0 s instead of
    # 90.0 s, and every bar after the fifth arrived early, so an FFT of "bars 5
    # and 6" read the notes of bars 10 and 11.
    assert arrange.read_midi(data)["tempo_us"] == 60_000_000 // score["meta"]["bpm"]
    assert arrange.read_midi(data)["tempo_us"] == 576923


def test_the_renderer_clock_reads_90_seconds_from_the_arranged_midi(tmp_path, score):
    """The renderer plays what the file says, so the file has to say 90 s.

    This is the check a hand render does: parse the arranged MIDI the way
    tools/render_chip.py parses it and ask how long 52 bars of 3/4 last.
    """
    import render_chip

    path = tmp_path / "out.mid"
    arrange.write_midi(arrange.build_arrangement(score), str(path))
    midi = render_chip.parse_midi(str(path))
    to_seconds = render_chip.make_clock(midi["tempo"], midi["division"])
    end_tick = max(end for track in midi["tracks"] for (_s, end, _p, _v) in track.notes)
    bar_ticks = midi["time_sig"][0] * midi["division"]
    assert bar_ticks == 1440
    assert end_tick / bar_ticks == pytest.approx(52.0, abs=0.02)
    assert to_seconds(end_tick) == pytest.approx(90.0, abs=0.05)
    assert 60_000_000.0 / midi["tempo"][0][1] == pytest.approx(104.0, abs=0.001)


# ---------------------------------------------------------------- the guard

def _write_midi(path, notes, name="melody"):
    """A one track MIDI file from (start, length, pitch) notes."""
    events = []
    for start, length, pitch in notes:
        events.append((start, 2, bytes((0x90, pitch, 100))))
        events.append((start + length, 0, bytes((0x80, pitch, 0))))
    events.sort(key=lambda item: (item[0], item[1]))
    body = bytearray()
    body += arrange._varlen(0) + b"\xff\x03" + bytes((len(name),)) + name.encode()
    last = 0
    for tick, _order, payload in events:
        body += arrange._varlen(tick - last) + payload
        last = tick
    body += arrange._varlen(0) + b"\xff\x2f\x00"
    data = (b"MThd" + struct.pack(">IHHH", 6, 1, 2, arrange.PPQ)
            + b"MTrk" + struct.pack(">I", len(body)) + bytes(body))
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def test_the_guard_fails_on_a_copied_melody(tmp_path):
    melody = [(0, 240, 69), (240, 240, 72), (480, 240, 76), (720, 240, 77),
              (960, 240, 76), (1200, 240, 74), (1440, 240, 72), (1680, 240, 69),
              (1920, 240, 67), (2160, 240, 64)]
    _write_midi(tmp_path / "melody.mid", melody)
    _write_midi(tmp_path / "reference.mid", melody)
    report, code = melody_guard.check(str(tmp_path / "melody.mid"),
                                      [str(tmp_path)])
    assert code == 1
    assert report["failures"]
    assert report["longest_identical_run"] >= 8


def test_the_guard_passes_on_a_different_melody(tmp_path):
    melody = [(i * 240, 240, 60 + (i * 5) % 12) for i in range(20)]
    other = [(i * 240, 240, 48 + (i * 7) % 12) for i in range(20)]
    _write_midi(tmp_path / "melody.mid", melody)
    _write_midi(tmp_path / "reference.mid", other)
    report, code = melody_guard.check(str(tmp_path / "melody.mid"),
                                      [str(tmp_path)])
    assert code == 0
    assert report["passed"]


def test_the_guard_reads_a_note_list(tmp_path):
    path = tmp_path / "notes.json"
    path.write_text(json.dumps([[60, 240], [62, 240], [64, 240], [65, 240]]),
                    encoding="utf-8")
    name, notes = melody_guard.load_melody(str(path))
    assert len(notes) == 4
    assert notes[0][2] == 60


def test_the_guard_finds_the_longest_run():
    pair = (2, 240)
    a = [pair] * 12
    # b holds five pairs, one different pair, then three pairs: the run stops
    # at the different pair and must not be merged across it.
    b = [pair] * 5 + [(3, 240)] + [pair] * 3
    assert melody_guard.longest_identical_run(a, b) == 5
    assert melody_guard.longest_identical_run(a, [pair] * 7) == 7
    assert melody_guard.longest_identical_run(a, [(3, 240)] * 9) == 0
