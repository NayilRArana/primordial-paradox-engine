"""arrange.py: the manager's score.yaml for the title theme v2, arranged to a
7 voice chip MIDI (NES 2A03 plus the Konami VRC6 expansion).

The score is
    assets/audio/title_theme_v2/score.yaml
and this tool does not compose. Every note it writes is one of three things:
a melody note from the yaml, a chord tone of a chord symbol in the yaml, or
the result of a recipe written in the voices block of the yaml.

The output is a Standard MIDI File, format 1, ppq 480, 3/4, tempo from the
meta block, with the eight track names the version 2 renderer expects:

    vrc6 pulse a   the melody, with vibrato and per section duty
    vrc6 pulse b   the guide tone counter melody (section A2 only)
    vrc6 saw       intro pad, oom pah stabs, section B pad
    pulse 1        the broken chord arpeggio, parallel thirds in section B
    pulse 2        the echo of the melody, one eighth late at 40 percent
    triangle       the waltz bass
    noise          hats and the fills
    dpcm           the kick

Determinism: the same score always produces the same bytes. There is no
randomness, no clock, and no set iteration in the output path.

Usage:
    arrange.py [score.yaml] [-o out.mid] [--report report.json] [--self-check]
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys

import yaml

# ------------------------------------------------------------------ constants

PPQ = 480
EIGHTH = PPQ // 2
BEAT = 2 * EIGHTH
BAR = 6 * EIGHTH          # 3/4
SLOTS = 6                 # eighths in a bar
TICKS_PER_BAR = BAR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCORE = os.path.join(ROOT, "assets", "audio", "title_theme_v2", "score.yaml")
DEFAULT_OUT = os.path.join(ROOT, "assets", "audio", "title_theme_v2", "title_theme_v2.mid")
DEFAULT_REPORT = os.path.join(ROOT, "assets", "audio", "title_theme_v2", "arrange_report.json")

# Track names, in the order the renderer fills its voice slots.
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

# Dynamics, from the dynamics block of the score, as chip levels 0 to 15.
DYNAMIC_LEVELS = {"pp": 4, "mp": 8, "mf": 11, "f": 14}

# Declared register of every voice, in MIDI note numbers. The self check
# refuses any note outside its own range.
#   vrc6 pulse a   the melody, octaves 4 and 5
#   vrc6 pulse b   the guide tone, octaves 3 and 4, always under the melody
#   vrc6 saw       the pad and the stabs, octaves 3 and 4
#   pulse 1        the arpeggio sits in octave 4 (C4 to G5); the parallel
#                  thirds of section B follow the melody, so they reach
#                  further up
#   pulse 2        the echo repeats the melody pitches
#   triangle       the bass, octaves 2 and 3
#   noise          percussion, the noise period table is 15 entries long
#   dpcm           the kick and the snare, MIDI notes 36 and 38
VOICE_RANGES = {
    "vrc6 pulse a": (60, 84),
    "vrc6 pulse b": (48, 72),
    "vrc6 saw": (48, 71),
    "pulse 1": (60, 79),
    "pulse 2": (60, 84),
    "triangle": (36, 55),
    "noise": (1, 15),
    "dpcm": (36, 38),
}
# Section B moves the pulse 1 line down a third under the melody, and the
# melody there reaches B5, so the range for that section is wider.
PULSE_1_B_RANGE = (55, 83)

MAX_SIMULTANEOUS_NOTES = 8

# Key of the theme, used to pick a diatonic approach note.
A_MINOR_PCS = frozenset((0, 2, 4, 5, 7, 8, 9, 11))

LETTERS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Chord qualities: the suffix, then the semitones above the root.
# "" is the plain major triad (a bare "C"), "m" the plain minor triad (a bare "Am").
QUALITIES = {
    "": (0, 4, 7),
    "m": (0, 3, 7),
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "5": (0, 7),
    "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "7": (0, 4, 7, 10),
    "m7b5": (0, 3, 6, 10),
    "6": (0, 4, 7, 9),
    "m6": (0, 3, 7, 9),
    "9": (0, 4, 7, 10, 14),
    "m9": (0, 3, 7, 10, 14),
    "sus4": (0, 5, 7),
    "7sus4": (0, 5, 7, 10),
    "7b9": (0, 4, 7, 10, 13),
    "maj9": (0, 4, 7, 11, 14),
}
# Longest suffix first, so 7sus4 wins over sus4 and 7.
QUALITY_SUFFIXES = tuple(sorted(QUALITIES, key=len, reverse=True))

# Root names, longest accidental first so G# does not read as G.
NOTE_NAMES = {
    "A": 9, "Bb": 10, "B": 11, "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3,
    "Eb": 3, "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6, "G": 7,
    "G#": 8, "Ab": 8, "A#": 10, "Bb": 10, "Db": 1, "Cb": 11, "B#": 0,
}


class ChordError(ValueError):
    """Raised when a chord symbol cannot be read."""


class Chord:
    """A parsed chord symbol: root, quality, tones, optional bass note."""

    def __init__(self, symbol, root_pc, quality, tones, bass_pc, bass_name):
        self.symbol = symbol
        self.root_pc = root_pc
        self.quality = quality
        self.tones = tuple(tones)          # semitones above the root
        self.bass_pc = bass_pc if bass_pc is not None else root_pc
        self.bass_name = bass_name
        self.has_slash = bass_pc is not None

    def pitch_classes(self):
        """The pitch classes of the chord, without the slash bass."""
        return tuple(sorted({(self.root_pc + t) % 12 for t in self.tones}))

    def __repr__(self):
        return "Chord(%r)" % self.symbol


def parse_chord(symbol):
    """Parse a chord symbol such as Am, Fmaj7, E7/G# or Bm7b5.

    Returns a Chord. Raises ChordError on anything unreadable.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise ChordError("empty chord symbol")
    text = symbol.strip()

    bass_pc = None
    bass_name = None
    if "/" in text:
        text, bass_text = text.split("/", 1)
        bass_text = bass_text.strip()
        if bass_text not in NOTE_NAMES:
            raise ChordError("unknown bass note %r in %r" % (bass_text, symbol))
        bass_pc = NOTE_NAMES[bass_text]
        bass_name = bass_text

    root_name = None
    for candidate in ("Bb", "Eb", "Ab", "Db", "Gb", "Cb", "Fb", "A#", "C#", "D#",
                      "F#", "G#", "B#", "E#", "A", "B", "C", "D", "E", "F", "G"):
        if text.startswith(candidate):
            root_name = candidate
            break
    if root_name is None:
        raise ChordError("unknown root in chord %r" % symbol)
    root_pc = NOTE_NAMES[root_name]
    rest = text[len(root_name):]

    quality = ""
    for suffix in QUALITY_SUFFIXES:
        if rest.endswith(suffix):
            quality = suffix
            break
    head = rest[:len(rest) - len(quality)]
    if head:
        raise ChordError("unknown chord quality %r in %r" % (head, symbol))

    if quality == "min":
        quality = "m"
    if quality == "maj":
        quality = ""
    tones = QUALITIES[quality]
    return Chord(symbol, root_pc, quality, tones, bass_pc, bass_name)


def note_to_midi(name):
    """'A4' -> 69, 'G#4' -> 68, 'Ab5' -> 68."""
    if not isinstance(name, str) or len(name) < 2:
        raise ValueError("bad note name %r" % (name,))
    letter = name[0].upper()
    if letter not in LETTERS:
        raise ValueError("bad note name %r" % (name,))
    index = 1
    accidental = 0
    if index < len(name) and name[index] in "#b":
        accidental = 1 if name[index] == "#" else -1
        index += 1
    octave = int(name[index:])
    return (octave + 1) * 12 + LETTERS[letter] + accidental


def midi_to_name(pitch):
    """69 -> 'A4'."""
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return "%s%d" % (names[pitch % 12], pitch // 12 - 1)


# ------------------------------------------------------------------- the score

class Bar:
    """One bar of the piece: its section, its chords and its melody."""

    def __init__(self, index, section):
        self.index = index              # 0 based
        self.number = index + 1         # 1 based, as the score counts them
        self.section = section
        self.chords = []                # (Chord or None) for beats 1, 2, 3
        self.melody = []                # (start_slot, length, pitch or None)

    @property
    def first_chord(self):
        for chord in self.chords:
            if chord is not None:
                return chord
        return None

    def chord_at_slot(self, slot):
        """The chord sounding at an eighth slot, 0 to 5."""
        beat = min(2, slot // 2)
        return self.chords[beat]


def load_score(path):
    """Read the score.

    The score as written holds an unquoted colon inside the meta chip value,
    which stops the YAML scanner. Rather than edit the manager's composition,
    the value is quoted in memory and the file is read again. Nothing else in
    the file is touched.
    """
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        repaired = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("chip:") and ": " in stripped[5:]:
                value = stripped[5:].strip().replace('"', "'")
                repaired.append('  chip: "%s"' % value)
            else:
                repaired.append(line)
        return yaml.safe_load("\n".join(repaired))


def section_order(score):
    """The section names in playing order: intro, A, B, A2."""
    order = []
    for name in ("intro", "A", "B", "A2"):
        if name in score.get("chords", {}):
            order.append(name)
    for name in score.get("chords", {}):
        if name not in order:
            order.append(name)
    return order


def expand_melody_section(score, name):
    """The melody bars of one section.

    The A2 melody is a directive in the score: repeat the bars 1 to 12 of
    section A, then the four ending bars that follow it.
    """
    raw = score["melody"][name]
    if not isinstance(raw, str):
        return [list(bar) for bar in raw]
    if name != "A2" or "repeat A bars" not in raw:
        raise ValueError("cannot read the melody of section %r: %r" % (name, raw))

    first, last = 1, 12
    marker = "repeat A bars"
    rest = raw[raw.index(marker) + len(marker):]
    # Only the "1 to 12" clause carries the range; the rest of the sentence
    # is prose, so stop at "then" and read the two integers before it.
    clause = rest.split("then")[0]
    parts = []
    for token in clause.replace(",", " ").split():
        if token.isdigit():
            parts.append(int(token))
    if len(parts) >= 2:
        first, last = parts[0], parts[1]
    elif parts:
        raise ValueError("cannot read the bar range in %r" % raw)

    a_bars = score["melody"]["A"]
    bars = [list(bar) for bar in a_bars[first - 1:last]]
    bars += [list(bar) for bar in score["melody"]["A2_ending"]]
    return bars


def split_chord_symbol(symbol):
    """'Fmaj7|E7' -> ('Fmaj7', 'E7'). A single symbol gives the same chord twice."""
    if isinstance(symbol, str) and "|" in symbol:
        left, right = symbol.split("|", 1)
        return left.strip(), right.strip()
    return symbol, symbol


def build_bars(score):
    """The bars of the piece, in order, with chords and melody attached."""
    bars = []
    melody_sections = {name: expand_melody_section(score, name)
                       for name in section_order(score)}
    for name in section_order(score):
        chords = score["chords"][name]
        melody = melody_sections.get(name, [])
        for offset, symbol in enumerate(chords):
            bar = Bar(len(bars), name)
            left, right = split_chord_symbol(symbol)
            bar.chords = [parse_chord(left), parse_chord(left), parse_chord(right)]
            if offset < len(melody):
                slot = 0
                for entry in melody[offset]:
                    note, length = entry[0], entry[1]
                    pitch = None if note in ("r", "rest", None) else note_to_midi(note)
                    bar.melody.append((slot, length, pitch))
                    slot += length
                if slot != SLOTS:
                    raise ValueError("bar %d of section %s holds %d eighths, not 6"
                                     % (bar.number, name, slot))
            bars.append(bar)
    return bars


# --------------------------------------------------------- chord voice leading

def voice_chord(pitch_classes, lo, hi, previous):
    """Place a chord in a register with smooth voice leading.

    pitch_classes are the pitch classes of the chord, lowest first.
    previous is the previous voicing, lowest first, used to keep the total
    movement small. The result is strictly ascending and inside [lo, hi].

    The search is a dynamic program over the ascending candidate pitches, so
    the total movement is as small as the register allows.
    """
    if not pitch_classes:
        return []
    if len(pitch_classes) > 1:
        for a, b in zip(pitch_classes, pitch_classes[1:]):
            if b <= a:
                raise ValueError("pitch classes must be sorted and unique")
    else:
        pass

    candidates = []
    for pc in pitch_classes:
        options = [p for p in range(lo, hi + 1) if p % 12 == pc]
        if not options:
            raise ValueError("pitch class %d does not fit in %d to %d"
                             % (pc, lo, hi))
        candidates.append(options)

    refs = []
    for index in range(len(pitch_classes)):
        if previous and index < len(previous):
            refs.append(previous[index])
        elif previous:
            refs.append(previous[-1])
        else:
            refs.append((lo + hi) // 2)

    # best[j] is the cheapest way to voice the first i tones ending at
    # candidates[i][j].
    best = [[None] * len(candidates[i]) for i in range(len(candidates))]
    for j, pitch in enumerate(candidates[0]):
        best[0][j] = (abs(pitch - refs[0]), [(pitch, j)])
    for i in range(1, len(candidates)):
        for j, pitch in enumerate(candidates[i]):
            choice = None
            for k, earlier in enumerate(candidates[i - 1]):
                if earlier >= pitch:
                    continue
                if best[i - 1][k] is None:
                    continue
                cost = best[i - 1][k][0] + abs(pitch - refs[i])
                if choice is None or cost < choice[0] or (cost == choice[0] and
                                                         best[i - 1][k][1] < choice[1]):
                    choice = (cost, best[i - 1][k][1] + [(pitch, j)])
            best[i][j] = choice
    last = best[len(candidates) - 1]
    winner = None
    for j in range(len(last)):
        if last[j] is None:
            continue
        if winner is None or last[j][0] < winner[0] or (last[j][0] == winner[0]
                                                       and last[j][1] < winner[1]):
            winner = last[j]
    if winner is None:
        raise ValueError("cannot voice %s inside %d to %d" % (pitch_classes, lo, hi))
    return [pitch for pitch, _ in winner[1]]


class Voicing:
    """Keeps the running voicing of a line so the next chord moves smoothly.

    Two chains are kept, one for the first chord of a bar and one for the
    second, because a bar with a split chord has two harmonic positions and
    each position has its own line.
    """

    def __init__(self, lo, hi):
        self.lo = lo
        self.hi = hi
        self.first = []
        self.second = []

    def place(self, pitch_classes, position):
        chain = self.first if position == 0 else self.second
        voicing = voice_chord(pitch_classes, self.lo, self.hi, chain)
        if position == 0:
            self.first = voicing
        else:
            self.second = voicing
        return voicing


# ------------------------------------------------------------------- the score

class Arrangement:
    """The finished arrangement: one list of notes per track, plus controls."""

    def __init__(self, score, bars):
        self.score = score
        self.bars = bars
        self.notes = {name: [] for name in TRACK_NAMES}
        self.controls = {name: [] for name in TRACK_NAMES}
        self.meta = {
            "bpm": score["meta"]["bpm"],
            "beats_per_bar": 3,
            "loop_start_bar": score["meta"]["loop_start_bar"],
        }

    # helpers -----------------------------------------------------------
    def add(self, track, start_tick, length, pitch, velocity):
        self.notes[track].append((start_tick, length, pitch, velocity))

    def add_control(self, track, tick, controller, value):
        self.controls[track].append((tick, controller, value))

    def bar_start(self, bar):
        return bar.index * TICKS_PER_BAR


# ---------------------------------------------------------- the arrangement

def build_arrangement(score):
    """Turn the score into the eight voice lines."""
    bars = build_bars(score)
    total_bars = score["meta"]["bars"]
    if len(bars) != total_bars:
        raise ValueError("the score holds %d bars, not %d" % (len(bars), total_bars))

    out = Arrangement(score, bars)
    dynamics = score.get("dynamics", {})
    duty = score.get("voices", {}).get("vrc6_pulse_a", {}).get("duty", {})
    vibrato = score.get("voices", {}).get("vrc6_pulse_a", {}).get("vibrato", {})

    # The level of every voice follows the section dynamic, and the echo
    # track sits at 40 percent of the melody level.
    melody_levels = {}
    for bar in bars:
        level = DYNAMIC_LEVELS.get(dynamics.get(bar.section, "mp"), 8)
        melody_levels[bar.index] = level
        out.add_control("vrc6 pulse a", out.bar_start(bar), 11, level)
        out.add_control("vrc6 pulse b", out.bar_start(bar), 11, level)
        out.add_control("vrc6 saw", out.bar_start(bar), 11, level)
        out.add_control("pulse 1", out.bar_start(bar), 11, level)
        out.add_control("pulse 2", out.bar_start(bar), 11, max(0, round(level * 0.4)))
        out.add_control("triangle", out.bar_start(bar), 11, level)
        out.add_control("noise", out.bar_start(bar), 11, level)
        out.add_control("dpcm", out.bar_start(bar), 11, level)

    # The duty of the melody changes with the section, and the arpeggio and
    # the echo keep the thin duty the score gives them.
    for bar in bars:
        start = out.bar_start(bar)
        section_duty = duty.get(bar.section, 0.25)
        out.add_control("vrc6 pulse a", start, 12, vrc6_duty_value(section_duty))
        out.add_control("pulse 1", start, 12, 0)          # 2A03 duty 12.5 percent
        out.add_control("pulse 2", start, 12, 0)          # 2A03 duty 12.5 percent

    melody_notes = []
    for bar in bars:
        start = out.bar_start(bar)
        for slot, length, pitch in bar.melody:
            if pitch is None:
                continue
            tick = start + slot * EIGHTH
            out.add("vrc6 pulse a", tick, length * EIGHTH, pitch, 100)
            melody_notes.append((tick, length * EIGHTH, pitch, 100))

    # The echo of the melody, one eighth late.
    end_of_piece = len(bars) * TICKS_PER_BAR
    for tick, length, pitch, velocity in melody_notes:
        start = tick + EIGHTH
        if start >= end_of_piece:
            continue
        length = min(length, end_of_piece - start)
        out.add("pulse 2", start, length, pitch, velocity)

    # Vibrato: the score asks for it after one eighth, on notes that last at
    # least three eighths, 15 cents deep at 5.5 Hz. The rate is fixed in the
    # renderer, so the depth and the delay are what this writes.
    if vibrato:
        depth_cents = float(vibrato.get("depth_cents", 15))
        after = float(vibrato.get("after_eighths", 1))
        min_eighths = int(vibrato.get("min_note_eighths", 3))
        depth_value = max(0, min(127, round(depth_cents / 100.0 / 2.0 * 127)))
        delay_value = max(0, min(127, round(after)))
        for tick, length, pitch, _velocity in melody_notes:
            if length >= min_eighths * EIGHTH:
                out.add_control("vrc6 pulse a", tick, 1, depth_value)
                out.add_control("vrc6 pulse a", tick, 20, delay_value)
            else:
                out.add_control("vrc6 pulse a", tick, 1, 0)
                out.add_control("vrc6 pulse a", tick, 20, 0)

    _build_pulse_1(out, bars)
    _build_saw(out, bars)
    _build_triangle(out, bars)
    _build_noise(out, bars)
    _build_dpcm(out, bars)
    _build_guide_tone(out, bars)
    return out


def vrc6_duty_value(fraction):
    """The CC12 value the renderer reads as a VRC6 duty of that fraction."""
    step = max(1, min(8, round(fraction * 16)))
    return step - 1


def _build_pulse_1(out, bars):
    """The broken chord arpeggio, and the parallel thirds of section B.

    The arpeggio is the Uematsu prelude figure: the chord tones go up and
    back down in eighths, a triangle wave over the tones of the chord.
    """
    voicing = Voicing(VOICE_RANGES["pulse 1"][0], VOICE_RANGES["pulse 1"][1])
    for bar in bars:
        start = out.bar_start(bar)
        if bar.section == "B":
            _parallel_thirds(out, bar, start)
            continue
        for beat, chord in enumerate(bar.chords):
            if chord is None:
                continue
            pitches = voicing.place(chord.pitch_classes(), 0 if beat < 2 else 1)
            if beat < 2:
                slots = (0, 2)
            else:
                slots = (4,)
            for slot in slots:
                index = _triangle_index(len(pitches), slot)
                out.add("pulse 1", start + slot * EIGHTH, EIGHTH, pitches[index], 88)


def _triangle_index(count, slot):
    """The tone index of an eighth slot in an up and down arpeggio.

    The pattern is a triangle wave over the chord tones, so a four tone
    chord gives root, third, fifth, seventh, fifth, third over the bar.
    """
    if count <= 1:
        return 0
    period = 2 * (count - 1)
    position = slot % period
    if position > count - 1:
        position = period - position
    return position


def _parallel_thirds(out, bar, start):
    """Section B: a third or a sixth under every melody note."""
    lo, hi = PULSE_1_B_RANGE
    for slot, length, pitch in bar.melody:
        if pitch is None:
            continue
        chord = bar.chord_at_slot(slot)
        if chord is None:
            continue
        choice = None
        for offset in (3, 4, 8, 9):
            candidate = pitch - offset
            if candidate < lo or candidate > hi:
                continue
            if (candidate % 12) in chord.pitch_classes():
                choice = candidate
                break
        if choice is None:
            choice = max(lo, min(hi, pitch - 4))
        out.add("pulse 1", start + slot * EIGHTH, length * EIGHTH, choice, 78)


def _build_saw(out, bars):
    """The VRC6 saw: the intro pad, the oom pah stabs, the section B pad."""
    voicing = Voicing(VOICE_RANGES["vrc6 saw"][0], VOICE_RANGES["vrc6 saw"][1])
    shell_voicing = Voicing(VOICE_RANGES["vrc6 saw"][0], VOICE_RANGES["vrc6 saw"][1])
    for bar in bars:
        start = out.bar_start(bar)
        if bar.section == "B":
            chord = bar.first_chord
            if chord is None:
                continue
            # A shell pad (third and seventh) rather than the full triad: the
            # B section already carries the melody, its echo, the thirds line,
            # the walking bass, hats and the kick, so the pad keeps the
            # arrangement inside the eight voice limit.
            offsets = shell_offsets(chord)
            if not offsets:
                continue
            classes = tuple(sorted({(chord.root_pc + t) % 12 for t in offsets}))
            pitches = voicing.place(classes, 0)
            for pitch in pitches:
                out.add("vrc6 saw", start, BAR, pitch, 62)
            continue
        if bar.section == "intro":
            for beat, chord in enumerate(bar.chords):
                if chord is None:
                    continue
                tones = chord.tones[:3]
                pitches = voicing.place(tuple(sorted({(chord.root_pc + t) % 12
                                                     for t in tones})),
                                        0 if beat < 2 else 1)
                for pitch in pitches:
                    out.add("vrc6 saw", start + beat * 2 * EIGHTH, 2 * EIGHTH, pitch, 66)
            continue
        # Section A and A2: shell voicings (the third and the seventh) on
        # beats 2 and 3.
        for beat, chord in enumerate(bar.chords):
            if chord is None or beat == 0:
                continue
            offsets = shell_offsets(chord)
            if not offsets:
                continue
            classes = tuple(sorted({(chord.root_pc + t) % 12 for t in offsets}))
            pitches = shell_voicing.place(classes, 0 if beat < 2 else 1)
            for pitch in pitches:
                out.add("vrc6 saw", start + beat * 2 * EIGHTH, 2 * EIGHTH, pitch, 72)


def shell_offsets(chord):
    """The third and the seventh of a chord, for the shell voicing."""
    tones = chord.tones
    third = tones[1] if len(tones) > 1 else None
    seventh = tones[3] if len(tones) > 3 else (tones[2] if len(tones) > 2 else None)
    offsets = [t for t in (third, seventh) if t is not None]
    return tuple(sorted(set(offsets)))


def _build_triangle(out, bars):
    """The waltz bass: root, rest, and an approach into the next root."""
    lo, hi = VOICE_RANGES["triangle"]
    previous_root = None
    total = len(bars)
    for position, bar in enumerate(bars):
        start = out.bar_start(bar)
        chord = bar.first_chord
        if chord is None:
            continue
        if bar.section == "B":
            _walking_bass(out, bar, start, bars, position, lo, hi)
            continue
        root_pc = chord.bass_pc
        root = _bass_pitch(root_pc, lo, hi, previous_root)
        previous_root = root
        out.add("triangle", start, 2 * EIGHTH, root, 104)

        # The third beat carries the fifth, or an approach into the next
        # bar's bass note when that note changes.
        next_chord = bars[(position + 1) % total].first_chord
        if next_chord is None:
            continue
        next_root = _bass_pitch(next_chord.bass_pc, lo, hi, root)
        if next_root % 12 == root % 12:
            fifth = chord.tones[2] if len(chord.tones) > 2 else 7
            pitch = _bass_pitch((chord.root_pc + fifth) % 12, lo, hi, root)
            out.add("triangle", start + 4 * EIGHTH, 2 * EIGHTH, pitch, 96)
        else:
            pitch = _approach_pitch(next_root, lo, hi, root)
            out.add("triangle", start + 4 * EIGHTH, 2 * EIGHTH, pitch, 96)


def _walking_bass(out, bar, start, bars, position, lo, hi):
    """Section B: root, third, approach, one note per beat."""
    total = len(bars)
    chord = bar.first_chord
    if chord is None:
        return
    root = _bass_pitch(chord.bass_pc, lo, hi, None)
    out.add("triangle", start, 2 * EIGHTH, root, 104)
    third = chord.tones[1] if len(chord.tones) > 1 else 4
    out.add("triangle", start + 2 * EIGHTH, 2 * EIGHTH,
            _bass_pitch((chord.root_pc + third) % 12, lo, hi, root), 100)
    next_chord = bars[(position + 1) % total].first_chord
    if next_chord is None:
        return
    next_root = _bass_pitch(next_chord.bass_pc, lo, hi, root)
    if next_root % 12 == root % 12:
        fifth = chord.tones[2] if len(chord.tones) > 2 else 7
        out.add("triangle", start + 4 * EIGHTH, 2 * EIGHTH,
                _bass_pitch((chord.root_pc + fifth) % 12, lo, hi, root), 96)
    else:
        out.add("triangle", start + 4 * EIGHTH, 2 * EIGHTH,
                _approach_pitch(next_root, lo, hi, root), 96)


def _bass_pitch(pc, lo, hi, reference):
    """A pitch of that pitch class in the bass register, near the reference."""
    options = [p for p in range(lo, hi + 1) if p % 12 == pc]
    if not options:
        options = [p for p in range(lo, hi + 1)]
    if reference is None:
        return options[len(options) // 2]
    return min(options, key=lambda p: (abs(p - reference), p))


def _approach_pitch(target, lo, hi, reference):
    """A note a step below the target, diatonic when the key allows it."""
    options = []
    for offset in (2, 1):
        candidate = target - offset
        if candidate < lo or candidate > hi:
            continue
        if (candidate % 12) in A_MINOR_PCS and (target % 12) in A_MINOR_PCS:
            options.append((0, candidate))
        else:
            options.append((1, candidate))
    if not options:
        return _bass_pitch(target % 12, lo, hi, reference)
    options.sort()
    return options[0][1]


def _build_noise(out, bars):
    """The noise track: closed hats on beats 2 and 3, and the fills."""
    hat_pitch = 6          # noise period index 5, a bright closed hat
    fill_pitches = (12, 10, 8)
    for bar in bars:
        if bar.section == "intro":
            continue
        start = out.bar_start(bar)
        is_fill_bar = bar.number in (20, 36, 52)
        if is_fill_bar:
            # The fill takes the last three eighths of the bar, so it is the
            # third beat plus the second half of the second beat, and the
            # downbeat of the next bar stays clear.
            out.add("noise", start + 2 * EIGHTH, EIGHTH, hat_pitch, 58)
            for index, pitch in enumerate(fill_pitches):
                out.add("noise", start + (3 + index) * EIGHTH, EIGHTH, pitch, 92)
            continue
        for beat in (1, 2):
            out.add("noise", start + beat * 2 * EIGHTH, EIGHTH, hat_pitch, 58)


def _build_dpcm(out, bars):
    """The DPCM kick, on beat 1 of sections B and A2."""
    for bar in bars:
        if bar.section not in ("B", "A2"):
            continue
        out.add("dpcm", out.bar_start(bar), EIGHTH, 36, 112)


def _build_guide_tone(out, bars):
    """The guide tone counter melody of section A2.

    One note per beat: the third or the seventh of the chord, below the
    melody, moving by step, and preferring contrary motion against the
    melody.
    """
    lo, hi = VOICE_RANGES["vrc6 pulse b"]
    previous = None
    previous_melody = None
    for bar in bars:
        if bar.section != "A2":
            continue
        start = out.bar_start(bar)
        for beat in (0, 1, 2):
            slot = beat * 2
            chord = bar.chords[beat]
            if chord is None:
                continue
            melody_pitch = _melody_pitch_at(bar, slot)
            if melody_pitch is None:
                continue
            offsets = [chord.tones[1]] if len(chord.tones) > 1 else [chord.tones[0]]
            if len(chord.tones) > 3:
                offsets.append(chord.tones[3])
            candidates = []
            for offset in offsets:
                pc = (chord.root_pc + offset) % 12
                for pitch in range(lo, hi + 1):
                    if pitch % 12 == pc and pitch < melody_pitch:
                        candidates.append(pitch)
            if not candidates:
                continue
            candidates = sorted(set(candidates))
            direction = 0
            if previous_melody is not None:
                direction = (melody_pitch > previous_melody) - (melody_pitch < previous_melody)
            best = None
            for pitch in candidates:
                if previous is None:
                    score = (abs(pitch - (melody_pitch - 12)), pitch)
                else:
                    step = abs(pitch - previous)
                    stepwise = 0 if 1 <= step <= 2 else 1
                    contrary = 0
                    if direction and previous is not None:
                        contrary = 0 if (pitch - previous) * direction < 0 else 1
                    score = (stepwise, contrary, step, abs(pitch - previous),
                             abs(pitch - (melody_pitch - 12)), pitch)
                if best is None or score < best[0]:
                    best = (score, pitch)
            chosen = best[1]
            out.add("vrc6 pulse b", start + slot * EIGHTH, 2 * EIGHTH, chosen, 84)
            previous = chosen
            previous_melody = melody_pitch


def _melody_pitch_at(bar, slot):
    """The melody pitch sounding at an eighth slot of a bar."""
    for start, length, pitch in bar.melody:
        if pitch is None:
            continue
        if start <= slot < start + length:
            return pitch
    return None


# ----------------------------------------------------------------- the writing

def _varlen(value):
    if value < 0:
        raise ValueError("a MIDI delta time cannot be negative")
    out = bytearray([value & 0x7F])
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def _meta_track(name, bpm, beats_per_bar):
    body = bytearray()
    body += _varlen(0) + b"\xff\x03" + _varlen(len(name)) + name.encode("latin-1")
    body += _varlen(0) + b"\xff\x58\x04" + bytes((beats_per_bar, 2, 24, 8))
    body += _varlen(0) + b"\xff\x51\x03" + struct.pack(">I", 500000 * 60 // bpm)[1:]
    body += _varlen(0) + b"\xff\x59\x02" + bytes((0, 0))     # A minor, no accidentals
    body += _varlen(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def _voice_track(name, notes, controls):
    """One track from notes and control changes.

    Note offs are written before note ons at the same tick, and control
    changes before both, so a control change always applies to the note
    that starts on the same tick.
    """
    events = []
    gap = 8
    for start, length, pitch, velocity in notes:
        end = start + max(1, length - gap)
        events.append((start, 2, bytes((0x90, pitch, velocity))))
        events.append((end, 0, bytes((0x80, pitch, 0))))
    for tick, controller, value in controls:
        events.append((tick, 1, bytes((0xB0, controller, max(0, min(127, value))))))

    events.sort(key=lambda item: (item[0], item[1]))

    body = bytearray()
    body += _varlen(0) + b"\xff\x03" + _varlen(len(name)) + name.encode("latin-1")
    last = 0
    for tick, _order, payload in events:
        body += _varlen(tick - last) + payload
        last = tick
    body += _varlen(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_midi(arrangement, path):
    """Write the arrangement as a Standard MIDI File and return the bytes."""
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(TRACK_NAMES) + 1, PPQ)
    parts = [_meta_track("meta", arrangement.meta["bpm"],
                         arrangement.meta["beats_per_bar"])]
    for name in TRACK_NAMES:
        parts.append(_voice_track(name, arrangement.notes[name],
                                  arrangement.controls[name]))
    data = header + b"".join(parts)
    if path:
        directory = os.path.dirname(os.path.abspath(path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
    return data


# --------------------------------------------------------------- the self check

def read_midi(data):
    """A small reader for the file just written, used by the self check."""
    if data[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    fmt, ntracks, division = struct.unpack(">hhh", data[8:14])
    pos = 14
    tracks = []
    for _ in range(ntracks):
        if data[pos:pos + 4] != b"MTrk":
            raise ValueError("bad track chunk")
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        name = ""
        notes = []
        open_notes = {}
        cursor = 0
        while cursor < len(body):
            delta, cursor = _read_varlen(body, cursor)
            status = body[cursor]
            if status == 0xFF:
                kind = body[cursor + 1]
                cursor += 2
                size, cursor = _read_varlen(body, cursor)
                payload = body[cursor:cursor + size]
                cursor += size
                if kind == 0x03:
                    name = payload.decode("latin-1")
            elif status in (0xF0, 0xF7):
                cursor += 1
                size, cursor = _read_varlen(body, cursor)
                cursor += size
            else:
                if status & 0xF0 == 0x90:
                    pitch = body[cursor + 1]
                    velocity = body[cursor + 2]
                    cursor += 3
                    if velocity > 0:
                        open_notes.setdefault(pitch, []).append(len(notes))
                        notes.append([None, pitch])
                    else:
                        started = open_notes.get(pitch)
                        if started:
                            notes[started.pop(0)][0] = len(notes)
                elif status & 0xF0 == 0x80:
                    pitch = body[cursor + 1]
                    cursor += 3
                    started = open_notes.get(pitch)
                    if started:
                        notes[started.pop(0)][0] = len(notes)
                elif status & 0xF0 in (0xB0, 0xE0):
                    cursor += 3
                else:
                    cursor += 2
        tracks.append((name, notes))
    return {"format": fmt, "ntracks": ntracks, "division": division, "tracks": tracks}


def _read_varlen(data, pos):
    value = 0
    for _ in range(4):
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise ValueError("malformed variable length quantity")


def note_spans(notes):
    """(start, end) pairs from the note list, using a running tick count."""
    spans = []
    tick = 0
    for start, length, pitch, _velocity in notes:
        spans.append((start, start + length, pitch))
    return spans


def max_simultaneous(arrangement):
    """The largest number of notes sounding at the same tick."""
    events = []
    for name in TRACK_NAMES:
        for start, end, _pitch in note_spans(arrangement.notes[name]):
            events.append((start, 1))
            events.append((end, -1))
    events.sort(key=lambda item: (item[0], item[1]))
    count = 0
    best = 0
    for _tick, delta in events:
        count += delta
        if count > best:
            best = count
    return best


def self_check(arrangement, data=None):
    """The checks the card names, as numbers."""
    result = {
        "bars": len(arrangement.bars),
        "bpm": arrangement.meta["bpm"],
        "loop_start_bar": arrangement.meta["loop_start_bar"],
        "tracks": list(TRACK_NAMES),
        "notes": {name: len(arrangement.notes[name]) for name in TRACK_NAMES},
        "max_simultaneous_notes": max_simultaneous(arrangement),
        "out_of_range": [],
    }

    for name in TRACK_NAMES:
        lo, hi = VOICE_RANGES[name]
        for start, end, pitch in note_spans(arrangement.notes[name]):
            if not (lo <= pitch <= hi):
                result["out_of_range"].append(
                    {"track": name, "tick": start, "pitch": pitch,
                     "note": midi_to_name(pitch), "range": [lo, hi]})
        if name == "pulse 1":
            for start, end, pitch in note_spans(arrangement.notes[name]):
                bar = arrangement.bars[min(len(arrangement.bars) - 1, start // TICKS_PER_BAR)]
                if bar.section == "B" and not (PULSE_1_B_RANGE[0] <= pitch <= PULSE_1_B_RANGE[1]):
                    result["out_of_range"].append(
                        {"track": name, "tick": start, "pitch": pitch,
                         "note": midi_to_name(pitch), "range": list(PULSE_1_B_RANGE)})

    # The card asks for bars 1 and 2 of section A (the leitmotif cell). Take
    # them from the bars themselves, not from the head of the note list, so
    # the intro pickup note does not leak into the report.
    section_a = [bar for bar in arrangement.bars if bar.section == "A"][:2]
    result["melody_bars_1_2"] = [
        midi_to_name(pitch)
        for bar in section_a
        for _slot, _length, pitch in bar.melody
        if pitch is not None
    ]
    result["melody_bar_numbers"] = [bar.number for bar in section_a]

    if data is not None:
        parsed = read_midi(data)
        result["midi_tracks"] = [name for name, _notes in parsed["tracks"]]
        result["midi_ntracks"] = parsed["ntracks"]
        result["midi_division"] = parsed["division"]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("score", nargs="?", default=DEFAULT_SCORE)
    parser.add_argument("-o", "--out", default=DEFAULT_OUT)
    parser.add_argument("--report", default=None)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)

    score = load_score(args.score)
    arrangement = build_arrangement(score)
    data = write_midi(arrangement, args.out)

    report = self_check(arrangement, data)
    report["score"] = os.path.abspath(args.score)
    report["midi"] = os.path.abspath(args.out)
    report["midi_bytes"] = len(data)
    report["duration_seconds"] = round(len(arrangement.bars) * TICKS_PER_BAR
                                      / PPQ * 60.0 / arrangement.meta["bpm"], 3)
    if args.report:
        directory = os.path.dirname(os.path.abspath(args.report))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
