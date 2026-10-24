"""build_pp04.py: turn score_pp04.yaml into the PP-04 MIDI and its report.

Card MUS-CUE-PP04. This script owns the recipe: the yaml holds the melody, the chords
and the bar counts, and this file turns them into the eight chip voices. It writes the
MIDI with the project's own writer (tools/arrange.py, imported, never modified) so the
renderer and every other cue agree about the track names and the meta track.

    python build_pp04.py

Outputs, next to this file: pp_04_navy_sailors.mid, pp_04_score_report.json,
melody_lead.json (the lead line as [pitch, eighths] for tools/melody_guard.py).

Voices used, all eight of them chip voices: vrc6 pulse a, vrc6 pulse b, vrc6 saw,
pulse 1, pulse 2, triangle, noise, dpcm. No sample, no acoustic instrument.
"""

from __future__ import annotations

import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import arrange  # noqa: E402  the shared MIDI writer, read only

SCORE = os.path.join(HERE, "score_pp04_v3.yaml")
MIDI = os.path.join(HERE, "pp_04_navy_sailors_v3.mid")
REPORT = os.path.join(HERE, "pp_04_score_report_v3.json")
MELODY = os.path.join(HERE, "melody_lead_v3.json")

EIGHTH = arrange.EIGHTH            # 240 ticks
BEAT = 2 * EIGHTH
BAR = 4 * BEAT                     # 4/4: 1920 ticks
SLOTS = 8                          # eighths in a bar
TICKS_PER_BAR = BAR

# Section loudness, as the chip level 0 to 15 of every voice before the per voice share.
SECTION_LEVEL = {"A": 9, "B": 7, "A2": 11, "A3": 12}
# The share of that level each voice takes. The lead and the bass carry the cue, the
# power chord is a texture under them, the pad and the saw are the floor.
TRACK_SHARE = {
    "vrc6 pulse a": 1.00,
    "vrc6 pulse b": 0.60,
    "vrc6 saw": 0.50,
    "pulse 1": 0.80,
    "pulse 2": 0.80,
    "triangle": 1.00,
    "noise": 0.65,
    "dpcm": 1.00,
}
# The palm mute of the riff (RCK-03) and the open gate of the lead.
GATE_MUTED = 0.40
GATE_LEAD = 0.90
GATE_BASS = 0.80
GATE_HAT = 0.55

PULSE_DUTY_50_2A03 = 2             # DUTY_TABLE index of the 50 percent 2A03 square
HAT_PITCH = 6                      # top rate, the hat sits above the warning alarm
FILL_PITCHES = (12, 10, 8)
CRASH_PITCH = 10

# Bass roots by pitch class, inside the triangle register 36 to 55. The line
# D2 C2 Bb2 A2 G2 is the bass of the cue: where Bb falls below the usable bottom the
# line leaps the seventh instead of dropping out of the register.
BASS_ROOT = {2: 38, 0: 36, 10: 46, 9: 45, 7: 43}
# The power chord root, in the riff register (MET-10 low).
RIFF_ROOT = {2: 50, 0: 48, 10: 46, 9: 45, 7: 43}
# The held fifth of vrc6 pulse b, octave 4, the power fifth layer.
FIFTH_PC = {0: 7, 2: 9, 10: 5, 9: 4, 7: 2}       # root pc -> fifth pc


class _Bar:
    """The one attribute arrange.Arrangement.bar_start reads: the bar index."""

    def __init__(self, index):
        self.index = index


def start_of(out, bar):
    return out.bar_start(_Bar(bar["index"]))


def section_bars(score):
    """Every bar in playing order, with its section, its chord and its melody."""
    order = ("A", "B", "A2", "A3")
    bars = []
    melody_a = None
    for name in order:
        block = score["sections"][name]
        melody = block["melody"]
        if isinstance(melody, str):
            if "same notes as A" in melody:
                if melody_a is None:
                    raise ValueError("A must be read before %s" % name)
                melody = [list(row) for row in melody_a]
            else:
                raise ValueError("unreadable melody line for %s: %r" % (name, melody))
        if name == "A":
            melody_a = [list(row) for row in melody]
        if len(melody) != len(block["chords"]):
            raise ValueError("%s has %d bars of melody and %d chords"
                             % (name, len(melody), len(block["chords"])))
        for offset, (chord, notes) in enumerate(zip(block["chords"], melody)):
            total = sum(length for _pitch, length in notes)
            if total != SLOTS:
                raise ValueError("%s bar %d sums to %d eighths, not %d"
                                 % (name, offset + 1, total, SLOTS))
            bars.append({
                "index": len(bars),
                "number": block["bars"][offset],
                "section": name,
                "chord": chord,
                "melody": [(arrange.note_to_midi(pitch), length) for pitch, length in notes],
            })
    return bars


def chord_root_pc(symbol):
    chord = arrange.parse_chord(symbol)
    return chord.root_pc


def fifth_pitch(root_pc, lo=60, hi=71):
    pc = FIFTH_PC.get(root_pc)
    if pc is None:
        pc = (root_pc + 7) % 12
    for pitch in range(lo, hi + 1):
        if pitch % 12 == pc:
            return pitch
    raise ValueError("no fifth of pc %d inside %d to %d" % (root_pc, lo, hi))


def build(score):
    bars = section_bars(score)
    meta = {
        "bpm": float(score["meta"]["bpm"]),
        "beats_per_bar": 4,
        "loop_start_bar": int(score["meta"]["loop_start_bar"]),
        "ticks_per_bar": TICKS_PER_BAR,
    }
    out = arrange.Arrangement(score, bars, meta)
    first = {}
    for bar in bars:
        first.setdefault(bar["section"], bar["number"])

    # ---------------------------------------------------------------- levels and duties
    for bar in bars:
        start = start_of(out, bar)
        level = SECTION_LEVEL[bar["section"]]
        for track in arrange.TRACK_NAMES:
            value = max(0, min(15, int(round(level * TRACK_SHARE[track]))))
            out.add_control(track, start, 11, value)
        out.add_control("pulse 1", start, 12, PULSE_DUTY_50_2A03)
        out.add_control("pulse 2", start, 12, PULSE_DUTY_50_2A03)
        out.add_control("vrc6 pulse b", start, 12, arrange.vrc6_duty_value(0.5))
        duty = score["voices"]["vrc6_pulse_a"]["duty"][bar["section"]]
        out.add_control("vrc6 pulse a", start, 12, arrange.vrc6_duty_value(duty))

    # ---------------------------------------------------------------- the lead
    melody_notes = []
    for bar in bars:
        start = start_of(out, bar)
        slot = 0
        for pitch, length in bar["melody"]:
            tick = start + slot * EIGHTH
            held = int(round(length * EIGHTH * GATE_LEAD))
            out.add("vrc6 pulse a", tick, held, pitch, 108)
            melody_notes.append((tick, held, pitch))
            slot += length

    # Vibrato after one eighth on notes that last three eighths or more.
    depth = int(round(12 / 100.0 / 2.0 * 127))
    for tick, length, _pitch in melody_notes:
        if length >= 3 * EIGHTH:
            out.add_control("vrc6 pulse a", tick, 1, depth)
            out.add_control("vrc6 pulse a", tick, 20, 1)
        else:
            out.add_control("vrc6 pulse a", tick, 1, 0)
            out.add_control("vrc6 pulse a", tick, 20, 0)

    # ---------------------------------------------------------------- the rest of the band
    previous_root = None
    for position, bar in enumerate(bars):
        start = start_of(out, bar)
        section = bar["section"]
        pc = chord_root_pc(bar["chord"])
        bass = BASS_ROOT[pc]
        riff = RIFF_ROOT[pc]
        fifth = bass + 7

        # vrc6 pulse b: the chord fifth held for the bar, the power fifth layer.
        out.add("vrc6 pulse b", start, int(BAR * 0.94), fifth_pitch(pc), 84)

        # vrc6 saw: the low root, one note per bar.
        out.add("vrc6 saw", start, int(BAR * 0.96), riff, 72)

        # triangle: the bass in eighths, with a step below the next root on the last
        # eighth of a bar that changes chord (the Capcom approach note).
        next_bass = None
        if position + 1 < len(bars):
            next_bass = BASS_ROOT[chord_root_pc(bars[position + 1]["chord"])]
        for slot in range(SLOTS):
            pitch = bass
            if slot == SLOTS - 1 and next_bass is not None and next_bass != bass:
                approach = next_bass - 2
                if 36 <= approach <= 55:
                    pitch = approach
            tick = start + slot * EIGHTH
            out.add("triangle", tick, int(EIGHTH * GATE_BASS), pitch, 112)
        previous_root = bass

        # The power chord: root on pulse 1, fifth on pulse 2, muted eighths. It takes a
        # break in the first half of the bridge, which is what makes the release read.
        chord_heard = not (section == "B" and bar["number"] < first["B"] + 4)
        if chord_heard:
            for slot in range(SLOTS):
                tick = start + slot * EIGHTH
                out.add("pulse 1", tick, int(EIGHTH * GATE_MUTED), riff, 104)
                out.add("pulse 2", tick, int(EIGHTH * GATE_MUTED), riff + 7, 96)

        # noise: hats only, top rate, written in rungs. The 4 bar rung answers the pattern
        # (an open hat on the third bar, a softer hat between the beats), the 8 bar rung adds
        # a tom fill and a crash into the next phrase, so the kit changes every 4 bars and
        # turns over every 8.
        number = bar["number"]
        rung4 = (number - 1) % 4
        sixteenth_bars = (7, 8, 23, 24)
        fill_bars = (8, 16, 24)
        crash_bars = (1, 9, 17, 25, 29, 32)
        hat_slots = list(range(SLOTS))
        if section == "B" and number < first["B"] + 4:
            hat_slots = [2, 6]
        if number in sixteenth_bars:
            hat_slots = list(range(SLOTS)) + [s + 0.5 for s in range(SLOTS)]
        hat_level = 52 if section != "B" else 40
        for slot in hat_slots:
            on_beat = float(slot).is_integer() and int(slot) % 2 == 0
            out.add("noise", start + int(slot * EIGHTH), int(EIGHTH * GATE_HAT),
                    HAT_PITCH, hat_level if on_beat else hat_level - 10)
        if rung4 == 2 and number not in sixteenth_bars:
            # the 4 bar rung: an open hat on the last eighth of the third bar
            out.add("noise", start + (SLOTS - 1) * EIGHTH, 2 * EIGHTH, 4, 56)
        if number in fill_bars:
            # the 8 bar rung: a three tom run over the last beat and a bit
            for index, pitch in enumerate(FILL_PITCHES):
                out.add("noise", start + (5 + index) * EIGHTH, EIGHTH, pitch, 96 - 6 * index)
            out.add("noise", start + (SLOTS - 1) * EIGHTH, EIGHTH, FILL_PITCHES[-1], 88)
        if number in crash_bars:
            out.add("noise", start, 2 * EIGHTH, CRASH_PITCH, 104)

        # dpcm: the kit, also in rungs. The 4 bar rung answers in the second bar; the 8 bar
        # rung ends on a snare pickup that hands the fill to the noise channel.
        if section in ("A", "A2", "A3"):
            out.add("dpcm", start, EIGHTH, 36, 116)
            out.add("dpcm", start + 2 * BEAT, EIGHTH, 38, 100)
            if section in ("A2", "A3"):
                out.add("dpcm", start + 3 * BEAT, EIGHTH, 36, 104)
            if rung4 == 1:
                out.add("dpcm", start + 3 * BEAT + EIGHTH, EIGHTH, 38, 74)
            if number in fill_bars:
                out.add("dpcm", start + 3 * BEAT + EIGHTH, EIGHTH, 38, 96)
        elif section == "B":
            if bar["number"] >= first["B"] + 4:
                out.add("dpcm", start, EIGHTH, 36, 104)
                if bar["number"] == first["B"] + 7:
                    out.add("dpcm", start + 3 * BEAT + EIGHTH, EIGHTH, 38, 100)
                else:
                    out.add("dpcm", start + 2 * BEAT, EIGHTH, 38, 92)
    return out, bars


def main():
    with open(SCORE, "r", encoding="utf-8") as handle:
        score = yaml.safe_load(handle)
    arrangement, bars = build(score)
    arrange.write_midi(arrangement, MIDI)

    lead = [[pitch, int(round(length / float(EIGHTH)))]
            for track in ("vrc6 pulse a",)
            for tick, length, pitch, _velocity in arrangement.notes[track]]
    with open(MELODY, "w", encoding="utf-8") as handle:
        json.dump(lead, handle, indent=1)
        handle.write("\n")

    bpm = float(score["meta"]["bpm"])
    seconds = len(bars) * TICKS_PER_BAR / arrange.PPQ * 60.0 / bpm
    loop_bars = int(score["meta"]["loop_end_bar"]) - int(score["meta"]["loop_start_bar"]) + 1
    first_note = min(tick for tick, _l, _p, _v in arrangement.notes["vrc6 pulse a"])
    hook_end = 2 * TICKS_PER_BAR / arrange.PPQ * 60.0 / bpm
    phrase_end = 4 * TICKS_PER_BAR / arrange.PPQ * 60.0 / bpm
    report = {
        "cue": "PP-04 Navy Sailors",
        "score": os.path.basename(SCORE),
        "midi": os.path.basename(MIDI),
        "bpm": bpm,
        "beats_per_bar": 4,
        "bars": len(bars),
        "sections": {name: len([b for b in bars if b["section"] == name])
                     for name in ("A", "B", "A2", "A3")},
        "chords": [bar["chord"] for bar in bars],
        "duration_seconds": round(seconds, 3),
        "bar_seconds": round(TICKS_PER_BAR / arrange.PPQ * 60.0 / bpm, 4),
        "loop_start_bar": int(score["meta"]["loop_start_bar"]),
        "loop_end_bar": int(score["meta"]["loop_end_bar"]),
        "loop_bars": loop_bars,
        "loop_seconds": round(loop_bars * TICKS_PER_BAR / arrange.PPQ * 60.0 / bpm, 3),
        "tail_bars": len(bars) - loop_bars,
        "first_lead_note_seconds": round(first_note / arrange.PPQ * 60.0 / bpm, 4),
        "hook_cell_end_seconds": round(hook_end, 3),
        "four_bar_phrase_end_seconds": round(phrase_end, 3),
        "lead_notes_in_first_4s": len([1 for tick, _l, _p, _v in arrangement.notes["vrc6 pulse a"]
                                       if tick < 4.0 * bpm / 60.0 * arrange.PPQ]),
        "notes": {track: len(arrangement.notes[track]) for track in arrange.TRACK_NAMES},
        "voice_ranges": {track: [min([p for _s, _e, p, _v in arrangement.notes[track]] or [0]),
                                 max([p for _s, _e, p, _v in arrangement.notes[track]] or [0])]
                         for track in arrange.TRACK_NAMES},
        "voices": list(arrange.TRACK_NAMES),
        "warning_blip": "alarm: MIDI 84 and 88 (C6 1046.5 Hz, E6 1318.5 Hz)",
    }
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("wrote", os.path.basename(MIDI), "%.3f s, %d bars, %d lead notes"
          % (seconds, len(bars), report["notes"]["vrc6 pulse a"]))
    print("hook cell ends at %.3f s, four bar phrase at %.3f s"
          % (hook_end, phrase_end))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
