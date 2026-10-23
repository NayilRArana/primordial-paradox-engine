"""build_pp03.py: the arranger for PP-03 "Harbor", the arrival cue.

Reads assets/audio/pp_03_harbor/score_pp03.yaml (the recipe) and
data/drum_patterns.json (the drum kit), and writes pp_03_harbor.mid in the
eight track layout tools/render_chip.py expects:

    vrc6 pulse a, vrc6 pulse b, vrc6 saw, pulse 1, pulse 2, triangle, noise, dpcm

Nothing here composes. Every note is one of four things: a note written in the
yaml melody, a chord tone of a chord symbol in the yaml, the echo of a melody
note, or a hit read by id from the drum pattern file. The drums follow the
project's own pattern library and the variation ladder in
knowledge/MUSIC-DRUMS.md, which is the part the 2026-10-22 ear sweep scored
lowest (3 to 5) and the part this card exists to fix.

Determinism: the same score and the same pattern file always produce the same
bytes. There is no randomness, no clock and no dictionary-order output.

Usage:
    build_pp03.py [score.yaml] [-o out.mid] [--report report.json] [--check]

Exit 0 on success. --check also runs the score checks and prints them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys

import yaml

PPQ = 480
EIGHTH = PPQ // 2
BAR_TICKS = 8 * EIGHTH
STEPS = 16                     # a bar of sixteenths on the drum grid
STEP_TICKS = BAR_TICKS // STEPS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
DEFAULT_SCORE = os.path.join(HERE, "score_pp03.yaml")
DEFAULT_OUT = os.path.join(HERE, "pp_03_harbor.mid")
DEFAULT_REPORT = os.path.join(HERE, "arrange_report.json")
DRUM_FILE = os.path.join(ROOT, "data", "drum_patterns.json")

TRACK_NAMES = (
    "vrc6 pulse a",
    "vrc6 pulse b",
    "vrc6 saw",
    "pulse 1",
    "pulse 2",
    "triangle",
    "noise",
    "dpcm",
)

# Declared register of every voice, MIDI note numbers. The check refuses a note
# outside its own voice's range.
RANGES = {
    "vrc6 pulse a": (60, 84),
    "vrc6 pulse b": (55, 76),
    "vrc6 saw": (36, 64),
    "pulse 1": (48, 72),
    "pulse 2": (60, 84),
    "triangle": (33, 60),
    "noise": (1, 16),
    "dpcm": (36, 38),
}

LETTERS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE_RE = re.compile(r"^([A-G])(#|b)?(-?\d)$")
CHORD_RE = re.compile(r"^([A-G][#b]?)(maj7|m7|dim|m|7)?(?:/([A-G][#b]?))?$")

THIRD = {"": 4, "7": 4, "maj7": 4, "m": 3, "m7": 3, "dim": 3}
SEVENTH = {"": None, "7": 10, "maj7": 11, "m7": 10, "dim": None, "m": None}


def note_number(name):
    match = NOTE_RE.match(name)
    if not match:
        raise ValueError("not a note name: %r" % (name,))
    letter, accidental, octave = match.groups()
    value = (int(octave) + 1) * 12 + LETTERS[letter]
    if accidental == "#":
        value += 1
    elif accidental == "b":
        value -= 1
    return value


def pitch_class(name):
    match = re.match(r"^([A-G])(#|b)?$", name)
    if not match:
        raise ValueError("not a pitch class: %r" % (name,))
    letter, accidental = match.groups()
    value = LETTERS[letter]
    if accidental == "#":
        value += 1
    elif accidental == "b":
        value -= 1
    return value % 12


def in_register(pc, low, high):
    """The pitch of this class nearest the bottom of a register window."""
    value = low + ((pc - low) % 12)
    if value > high:
        value -= 12
    return value


class Chord(object):
    def __init__(self, symbol):
        match = CHORD_RE.match(symbol.strip())
        if not match:
            raise ValueError("unknown chord symbol: %r" % (symbol,))
        root, quality, bass = match.groups()
        quality = quality or ""
        self.symbol = symbol
        self.root = pitch_class(root)
        self.third = (self.root + THIRD[quality]) % 12
        self.fifth = (self.root + 7) % 12
        seventh = SEVENTH[quality]
        self.seventh = None if seventh is None else (self.root + seventh) % 12
        self.bass = pitch_class(bass) if bass else self.root


class Arrangement(object):
    def __init__(self):
        self.notes = {name: [] for name in TRACK_NAMES}
        self.controls = {name: [] for name in TRACK_NAMES}

    def add(self, track, start, end, pitch, velocity):
        low, high = RANGES[track]
        if not (low <= pitch <= high):
            raise ValueError("%s: note %d outside its declared range %d to %d"
                             % (track, pitch, low, high))
        if end <= start:
            raise ValueError("%s: zero length note at tick %d" % (track, start))
        self.notes[track].append((start, end, pitch, velocity))

    def control(self, track, tick, controller, value):
        self.controls[track].append((tick, controller, max(0, min(127, int(value)))))


# ------------------------------------------------------------------ drums

def load_drums():
    with open(DRUM_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def home_grid(drums, pattern_id):
    for pattern in drums["patterns"]:
        if pattern["id"] == pattern_id:
            grid = pattern["steps"]
            if len(grid) != STEPS:
                raise ValueError("%s is not a %d step pattern" % (pattern_id, STEPS))
            return [[dict(hit) for hit in step] for step in grid]
    raise ValueError("no pattern with id %r in %s" % (pattern_id, DRUM_FILE))


def fill_grid(drums, fill_id):
    for fill in drums["fills"]:
        if fill["id"] == fill_id:
            return [[dict(hit) for hit in step] for step in fill["steps"]]
    raise ValueError("no fill with id %r in %s" % (fill_id, DRUM_FILE))


def clear_steps(grid, first):
    for step in range(first, STEPS):
        grid[step] = []


def place_fill(grid, fill, first):
    """Put a library fill on the last steps of the bar, replacing what was there."""
    width = len(fill)
    if width > STEPS:
        raise ValueError("fill is longer than a bar")
    first = min(first, STEPS - width)
    clear_steps(grid, first)
    for offset, hits in enumerate(fill):
        grid[first + offset] = [dict(hit) for hit in hits]


def ghost(grid, step, period=6, velocity=26):
    if any(hit["instrument"] == "noise" for hit in grid[step]):
        return
    grid[step].append({"instrument": "noise", "velocity": velocity,
                       "accent": False, "period": period, "loop": "long"})


def displace_kick(grid):
    """Rung 2: move the second kick to the and of 3, or add one there."""
    kicks = [i for i, step in enumerate(grid)
             if any(hit["instrument"] == "dpcm_kick" for hit in step)]
    later = [i for i in kicks if i > 0]
    if later:
        source = later[0]
        grid[source] = [hit for hit in grid[source] if hit["instrument"] != "dpcm_kick"]
        if not any(hit["instrument"] == "dpcm_kick" for hit in grid[10]):
            grid[10].append({"instrument": "dpcm_kick", "velocity": 40,
                             "accent": False, "rate": 11})
    else:
        if not any(hit["instrument"] == "dpcm_kick" for hit in grid[10]):
            grid[10].append({"instrument": "dpcm_kick", "velocity": 40,
                             "accent": False, "rate": 11})


def drop_kick(grid):
    """Rung 4: no DMC kick for the whole bar. The noise keeps the time."""
    for step in grid:
        step[:] = [hit for hit in step if hit["instrument"] != "dpcm_kick"]


def crash(grid, period=13, velocity=38):
    """Rung 5: one long low noise hit on the first beat."""
    if any(hit["instrument"] == "noise" for hit in grid[0]):
        grid[0] = [hit for hit in grid[0] if hit["instrument"] != "noise"]
    grid[0].append({"instrument": "noise", "velocity": velocity,
                    "accent": True, "period": period, "loop": "long"})


def sweep_hat(grid):
    """Rung 6's second half: the hat brightens by one period step."""
    for step in grid:
        for hit in step:
            if hit["instrument"] == "noise":
                hit["period"] = min(15, int(hit["period"]) + 1)


def build_bar_grid(drums, spec, bar_index):
    """One bar of drums from the section's home pattern and its rung."""
    rungs = spec["rungs"]
    rung = rungs[bar_index % len(rungs)]
    grid = home_grid(drums, spec["home"])
    if rung == 0:
        pass
    elif rung == 1:
        ghost(grid, 6)
    elif rung == 2:
        displace_kick(grid)
    elif rung == 3:
        fill = fill_grid(drums, spec["fill_end"] if len(fill_grid(drums, spec["fill_end"])) == 8
                         else spec["fill_beat"])
        place_fill(grid, fill, STEPS - len(fill))
        ghost(grid, 4)
    elif rung == 4:
        drop_kick(grid)
    elif rung == 5:
        crash(grid)
    elif rung == 6:
        ghost(grid, 6)
        sweep_hat(grid)
    elif rung == 7:
        place_fill(grid, fill_grid(drums, spec["fill_end"]), 8)
    else:
        raise ValueError("unknown drum rung %r" % (rung,))
    return rung, grid


def noise_length_ticks(period):
    """The decay, in ticks, from the note length rule in MUSIC-DRUMS 2.1."""
    if period <= 2:
        return 30       # closed hat, 55 ms at 68 bpm
    if period <= 5:
        return 55       # open hat, 100 ms
    if period <= 8:
        return 80       # brush or snare body, 147 ms
    if period <= 11:
        return 110      # tom, 200 ms
    return 240          # crash wash, 440 ms


DPCM_LENGTH = {36: 80, 38: 70}


def add_drums(arr, drums, spec, bar_start, bar_index, scale):
    rung, grid = build_bar_grid(drums, spec, bar_index)
    for step_index, hits in enumerate(grid):
        noise = [hit for hit in hits if hit["instrument"] == "noise"]
        if len(noise) > 1:
            raise ValueError("bar %d step %d holds two noise hits, which the noise "
                             "channel cannot play (MUSIC-DRUMS 1)"
                             % (bar_index + 1, step_index))
        tick = bar_start + step_index * STEP_TICKS
        for hit in hits:
            velocity = int(round(hit["velocity"] * scale))
            velocity = max(12, min(60, velocity))
            if hit["instrument"] == "noise":
                period = int(hit["period"])
                arr.add("noise", tick, tick + noise_length_ticks(period),
                        period + 1, velocity)
            elif hit["instrument"] == "dpcm_kick":
                arr.add("dpcm", tick, tick + DPCM_LENGTH[36], 36, velocity)
            elif hit["instrument"] == "dpcm_snare":
                arr.add("dpcm", tick, tick + DPCM_LENGTH[38], 38, velocity)
            else:
                raise ValueError("unknown drum instrument %r" % (hit["instrument"],))
    return rung


# ------------------------------------------------------------------ voices

def section_melody(score, name, seen=None):
    """The melody of a section, following a "same notes as X" reference."""
    sections = score["sections"]
    seen = seen or set()
    if name in seen:
        raise ValueError("melody reference loops at %r" % (name,))
    seen.add(name)
    if name not in sections:
        name = name.replace(" ", "_")
    melody = sections[name]["melody"]
    if isinstance(melody, str):
        match = re.match(r"^same notes as ([\w ]+?)\s*$", melody.strip())
        if not match:
            raise ValueError("section %r has a text melody that is not a reference: %r"
                             % (name, melody))
        return section_melody(score, match.group(1), seen)
    return melody


def add_lead(arr, melody, bars_start, level, vibrato, phrase_end_rest=0):
    """The lead on vrc6 pulse a, plus its echo on pulse 2."""
    for bar_index, bar in enumerate(melody):
        cursor = 0
        bar_start = (bars_start + bar_index) * BAR_TICKS
        phrase_end = phrase_end_rest and (bar_index + 1) % 4 == 0
        for event in bar:
            name, length = event[0], int(event[1])
            start = bar_start + cursor * EIGHTH
            end = start + length * EIGHTH
            if name != "r":
                pitch = note_number(name)
                # HOK-30: the phrase breathes. On the last bar of every four the
                # last lead note gives up its final eighth, so the rest is a
                # written breath and not a rounding accident.
                if phrase_end and cursor + length == 8 and length > 1:
                    end -= EIGHTH
                    length -= 1
                arr.add("vrc6 pulse a", start, end, pitch, 100)
                if length >= vibrato["min_note_eighths"]:
                    arr.control("vrc6 pulse a", start, 1, vibrato["depth"])
                    arr.control("vrc6 pulse a", start, 20, vibrato["after_eighths"])
                    arr.control("vrc6 pulse a", end, 1, 0)
                    arr.control("vrc6 pulse a", end, 20, 0)
            cursor += int(event[1])
        if cursor != 8:
            raise ValueError("bar %d of the lead holds %d eighths, not 8"
                             % (bars_start + bar_index + 1, cursor))


def add_echo(arr, melody, bars_start):
    """CHIP-08: the lead again on pulse 2, one eighth late, at 40 percent."""
    for bar_index, bar in enumerate(melody):
        cursor = 0
        bar_start = (bars_start + bar_index) * BAR_TICKS
        for event in bar:
            name, length = event[0], int(event[1])
            if name != "r":
                pitch = note_number(name)
                start = bar_start + cursor * EIGHTH + EIGHTH
                end = min(start + length * EIGHTH, (bars_start + bar_index + 1) * BAR_TICKS)
                if end > start:
                    arr.add("pulse 2", start, end, pitch, 80)
            cursor += length


def add_harmony(arr, chords, bars_start, arp_mode, guide=True, arp_level=5,
                walk_bars=(), dropout_bars=(), next_root=None):
    """The accompaniment: pad, broken chord, guide tone and bass."""
    chord_list = [Chord(symbol) for symbol in chords]
    for index, chord in enumerate(chord_list):
        bar = bars_start + index
        bar_start = bar * BAR_TICKS
        root = in_register(chord.root, 48, 59)
        third = in_register(chord.third, 48, 62)
        fifth = in_register(chord.fifth, 48, 62)

        # The pad: root then fifth, half notes, one voice breathing.
        arr.add("vrc6 saw", bar_start, bar_start + 2 * EIGHTH, root, 90)
        arr.add("vrc6 saw", bar_start + 2 * EIGHTH, bar_start + 4 * EIGHTH, fifth, 80)
        arr.control("vrc6 saw", bar_start, 11, 6)

        # The guide tone: the third of the chord, half notes, octave 4.
        if guide:
            guide_pitch = in_register(chord.third, 60, 71)
            arr.add("vrc6 pulse b", bar_start, bar_start + 2 * EIGHTH, guide_pitch, 70)
            arr.add("vrc6 pulse b", bar_start + 2 * EIGHTH, bar_start + 4 * EIGHTH,
                    in_register(chord.fifth, 60, 71), 60)

        # The broken chord on pulse 1.
        if (index + 1) not in dropout_bars:
            if arp_mode == "eighths":
                pattern = [root, fifth, third, fifth, root, fifth, third, fifth]
                length = EIGHTH
            elif arp_mode == "quarters":
                pattern = [root, fifth, third, fifth]
                length = 2 * EIGHTH
            else:
                raise ValueError("unknown arp mode %r" % (arp_mode,))
            for step, pitch in enumerate(pattern):
                arr.add("pulse 1", bar_start + step * length,
                        bar_start + (step + 1) * length, pitch, 90)
            arr.control("pulse 1", bar_start, 11, arp_level)

        # The bass on the triangle.
        bass_root = in_register(chord.bass, 40, 51)
        bass_fifth = in_register(chord.fifth, 40, 55)
        if (index + 1) in walk_bars:
            approach = None
            if index + 1 < len(chord_list):
                approach = in_register(chord_list[index + 1].bass, 40, 51) - 1
            elif next_root is not None:
                approach = in_register(next_root, 40, 51) - 1
            elif chord_list:
                approach = in_register(chord_list[0].bass, 40, 51) - 1
            line = [bass_root, in_register(chord.third, 40, 55), bass_fifth, approach]
            for step, pitch in enumerate(line):
                if pitch is None:
                    continue
                arr.add("triangle", bar_start + step * 2 * EIGHTH,
                        bar_start + (step + 1) * 2 * EIGHTH, pitch, 100)
        else:
            arr.add("triangle", bar_start, bar_start + 2 * EIGHTH, bass_root, 105)
            arr.add("triangle", bar_start + 2 * EIGHTH, bar_start + 4 * EIGHTH,
                    bass_fifth, 95)
        arr.control("triangle", bar_start, 11, 8)


# ------------------------------------------------------------------ the build

def build(score, drums):
    meta = score["meta"]
    if meta["time"] != "4/4":
        raise ValueError("this arranger is written for 4/4; the score says %r" % (meta["time"],))
    bpm = float(meta["bpm"])
    total_bars = int(meta["bars"])
    arr = Arrangement()

    voices = score["voices"]
    lead = voices["vrc6_pulse_a"]
    vibrato = {"after_eighths": lead.get("vibrato", {}).get("after_eighths", 1),
               "min_note_eighths": lead.get("vibrato", {}).get("min_note_eighths", 3),
               "depth": lead.get("vibrato", {}).get("depth", 12)}
    arr.control("vrc6 pulse a", 0, 12, lead.get("duty", 3))
    arr.control("vrc6 pulse a", 0, 11, lead.get("level", 11))
    arr.control("vrc6 pulse b", 0, 12, voices["vrc6_pulse_b"].get("duty", 3))
    arr.control("vrc6 pulse b", 0, 11, voices["vrc6_pulse_b"].get("level", 3))
    arr.control("pulse 1", 0, 12, voices["pulse_1"].get("duty", 0))
    arr.control("pulse 2", 0, 12, voices["pulse_2"].get("duty", 0))
    arr.control("pulse 2", 0, 11, voices["pulse_2"].get("level", 4))
    arr.control("noise", 0, 11, voices["noise"].get("level", 6))
    arr.control("dpcm", 0, 11, voices["dpcm"].get("level", 7))

    bar_cursor = 0
    order = list(score["sections"].keys())
    names = list(score["sections"].keys())
    drum_log = []
    for name in names:
        spec = score["sections"][name]
        bars = int(spec["bars"])
        chords = spec["chords"]
        if len(chords) != bars:
            raise ValueError("section %r has %d chords for %d bars" % (name, len(chords), bars))
        melody = section_melody(score, name)
        if len(melody) != bars:
            raise ValueError("section %r has %d melody bars for %d bars"
                             % (name, len(melody), bars))

        add_lead(arr, melody, bar_cursor, lead.get("level", 11), vibrato,
                 phrase_end_rest=int(lead.get("phrase_end_rest_eighths", 0)))
        if int(spec.get("echo", 0)):
            add_echo(arr, melody, bar_cursor)

        arp_level = voices["pulse_1"].get("level", 5)
        if name == "read":
            arp_level = 4
        if name == "return":
            arp_level = 6
        add_harmony(arr, chords, bar_cursor,
                    spec.get("arp", "eighths"),
                    arp_level=arp_level,
                    walk_bars=spec.get("walk_bars", ()),
                    dropout_bars=spec.get("arp_dropout_bars", ()),
                    next_root=(Chord(chords[0]).root if chords else None))

        scale = float(spec.get("level_scale", 1.0))
        rungs = []
        for bar_index in range(bars):
            rungs.append(add_drums(arr, drums, spec["drums"], (bar_cursor + bar_index) * BAR_TICKS,
                                   bar_index, scale))
        drum_log.append({"section": name, "home": spec["drums"]["home"], "rungs": rungs})

        # Keep every voice's level as the score states it, section by section.
        for track in ("vrc6 pulse a", "vrc6 pulse b", "triangle", "noise", "dpcm"):
            arr.control(track, bar_cursor * BAR_TICKS, 11, voices[
                {"vrc6 pulse a": "vrc6_pulse_a", "vrc6 pulse b": "vrc6_pulse_b",
                 "triangle": "triangle", "noise": "noise", "dpcm": "dpcm"}[track]].get("level", 8))

        bar_cursor += bars

    if bar_cursor != total_bars:
        raise ValueError("the sections add up to %d bars, the meta block says %d"
                         % (bar_cursor, total_bars))

    # Nothing may sound past the loop point.
    limit = total_bars * BAR_TICKS
    for track, notes in arr.notes.items():
        for start, end, pitch, velocity in notes:
            if end > limit:
                raise ValueError("%s: a note ends at %d, past the loop point %d"
                                 % (track, end, limit))

    return arr, bpm, total_bars, drum_log


# ------------------------------------------------------------------ MIDI out

def varlen(value):
    if value < 0:
        raise ValueError("negative delta")
    buffer = bytearray([value & 0x7F])
    value >>= 7
    while value:
        buffer.insert(0, 0x80 | (value & 0x7F))
        value >>= 7
    return bytes(buffer)


def meta_track(bpm, bars):
    body = bytearray()
    body += b"\x00\xff\x03" + varlen(len(b"conductor")) + b"conductor"
    body += b"\x00\xff\x58\x04" + bytes((4, 2, 24, 8))          # 4/4
    us_per_qn = int(round(60000000.0 / bpm))
    body += b"\x00\xff\x51\x03" + us_per_qn.to_bytes(3, "big")
    body += b"\x00\xff\x59\x02" + bytes((0, 0))                # A minor, no accidentals
    body += b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def voice_track(name, notes, controls):
    # At one tick the order is: control change, then note off, then note on. A
    # note that ends exactly where the same pitch restarts depends on that
    # order: with the note on first, the fresh note would be closed by the old
    # note's off and the renderer would drop it.
    events = []
    for tick, controller, value in controls:
        events.append((tick, 0, bytes((0xB0, controller, value & 0x7F))))
    for start, end, pitch, velocity in notes:
        events.append((end, 1, bytes((0x80, pitch & 0x7F, 0x40))))
        events.append((start, 2, bytes((0x90, pitch & 0x7F, velocity & 0x7F))))
    events.sort(key=lambda row: (row[0], row[1]))
    body = bytearray()
    body += b"\x00\xff\x03" + varlen(len(name.encode("latin-1"))) + name.encode("latin-1")
    body += b"\x00\xff\x04" + varlen(len(name.encode("latin-1"))) + name.encode("latin-1")
    cursor = 0
    for tick, _order, payload in events:
        body += varlen(tick - cursor) + payload
        cursor = tick
    body += b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_midi(path, arr, bpm, bars):
    chunks = [meta_track(bpm, bars)]
    for name in TRACK_NAMES:
        chunks.append(voice_track(name, arr.notes[name], arr.controls[name]))
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), PPQ)
    with open(path, "wb") as handle:
        handle.write(header)
        for chunk in chunks:
            handle.write(chunk)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Arrange PP-03 Harbor to a chip MIDI.")
    parser.add_argument("score", nargs="?", default=DEFAULT_SCORE)
    parser.add_argument("-o", "--out", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    score_path = os.path.abspath(args.score)
    with open(score_path, "r", encoding="utf-8") as handle:
        score = yaml.safe_load(handle)
    drums = load_drums()
    arr, bpm, bars, drum_log = build(score, drums)

    out_path = args.out or os.path.join(os.path.dirname(score_path), "pp_03_harbor.mid")
    write_midi(out_path, arr, bpm, bars)

    counts = {name: len(arr.notes[name]) for name in TRACK_NAMES}
    loop_seconds = bars * 8 * EIGHTH / float(PPQ) * 60.0 / bpm
    report = {
        "score": score_path,
        "midi": os.path.abspath(out_path),
        "bpm": bpm,
        "time_signature": score["meta"]["time"],
        "bars": bars,
        "bar_seconds": 4 * 60.0 / bpm,
        "loop_seconds": round(loop_seconds, 6),
        "ppq": PPQ,
        "tracks": list(TRACK_NAMES),
        "note_counts": counts,
        "total_notes": sum(counts.values()),
        "drums": drum_log,
        "drum_source": DRUM_FILE,
        "first_bar_chord": score["sections"][list(score["sections"])[0]]["chords"][0],
        "last_bar_chord": score["sections"][list(score["sections"])[-1]]["chords"][-1],
    }
    report_path = args.report or os.path.join(os.path.dirname(score_path), "arrange_report.json")
    with open(report_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("score: %s" % score_path)
    print("midi:  %s" % os.path.abspath(out_path))
    print("  %d bars, %.3f s per loop, %.1f bpm, %s"
          % (bars, loop_seconds, bpm, score["meta"]["time"]))
    print("  notes: " + ", ".join("%s %d" % (name, counts[name]) for name in TRACK_NAMES))
    print("  total: %d notes" % report["total_notes"])
    print("  first chord %s, last chord %s"
          % (report["first_bar_chord"], report["last_bar_chord"]))
    print("  drums: " + " | ".join("%s %s %s" % (row["section"], row["home"],
                                                 ",".join(str(r) for r in row["rungs"]))
                                   for row in drum_log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
