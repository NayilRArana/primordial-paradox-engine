"""spice.py: the drum varier and the dissonance injector for an arrange.py MIDI.

The ear review of title theme v3 at 126 bpm (assets/audio/title_theme_v3/
EAR_REVIEW_126.md) scored drums 4, tension and dissonance 5, and blamed a waltz
drum pattern that never changes and a harmony that is too safe. This tool is
the answer to those two numbers. It reads the MIDI tools/arrange.py writes (or
the score yaml, which it arranges first), and applies two passes:

drums        replaces the noise and DPCM tracks bar by bar with patterns from
             data\\drum_patterns.json (or a small built in set when that file is
             absent): one home pattern per section, then the variation ladder
             of the waltz section of that file read as the bar by bar script
             its `four_bar_cycle`, `eight_bar_cycle` and `sixteen_bar_cycle`
             describe, with fills at phrase ends and before section changes and
             a crash on the downbeat of a new section. A bar the arranger left
             without any drum note stays silent, and a bar is never filled with
             two noise hits at once, because the noise channel plays one sound
             at a time.

dissonance    injects the devices data\\dissonance_rules.json describes, from
             the safe family only: a chromatic passing tone (DIS-01), a
             chromatic lower neighbour (DIS-02), an appoggiatura on a strong
             beat (DIS-03), one dominant seven flat nine per sixteen bars
             (DIS-11) and a sparse minor second between the echo and the lead
             (DIS-18). The forbidden list of the same file is enforced, and
             every leitmotif bar is frozen: no device may touch a bar whose
             melody is a motif statement, and the tool proves the melody events
             of those bars are unchanged, byte for byte.

Both passes are deterministic: the same input, the same seed and the same
strengths give byte identical output. The tool prints a report of every change
with its bar, its beat and the device used, and writes the same report as JSON.

The leitmotif bars are found without reading a comment: a bar is frozen when
its melody matches one of the cells the score's `motifs` block declares (same
number of notes, every interval within one semitone of the declared cell, so a
cell transposed or spelled a third lower still matches), or when it lies inside
an occurrence of the motif tools/hook_score.py itself finds. The report lists
the frozen bars so the rule can be checked by eye.

Usage:
    spice.py IN.mid [OUT.mid] [--drums N] [--dissonance N] [--seed N]
    spice.py score.yaml [OUT.mid]         (arranges the score first)
    spice.py IN.mid OUT.mid --humanize    (reruns tools/humanize.py on the out)

    --drums 0..3      0 leaves the drums exactly as arranged
    --dissonance 0..3 0 injects nothing
    --score PATH      the score the MIDI came from (default: looked up)
    --report PATH     write the JSON report here
    --max-hook-drop N refuse the melody devices that would cost more than N
                      hook_score points (default 5, the card's limit)
    --dry-run         report only, write nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hook_score                                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

DEFAULT_DRUM_DATA = os.path.join(ROOT, "data", "drum_patterns.json")
DEFAULT_DISSONANCE_DATA = os.path.join(ROOT, "data", "dissonance_rules.json")
DEFAULT_SCORE = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "score_v3.yaml")

DEFAULT_SEED = 20261022
DEFAULT_DRUMS = 2
DEFAULT_DISSONANCE = 2
DEFAULT_MAX_HOOK_DROP = 5

MELODY_TRACK = "vrc6 pulse a"
ECHO_TRACK = "pulse 2"
COUNTER_TRACK = "vrc6 pulse b"
SAW_TRACK = "vrc6 saw"

DRUM_TRACKS = ("noise", "dpcm")

# The noise channel plays one sound at a time, so a noise note is cut where the
# next noise onset of the same bar begins. The DPCM channel is a second channel
# and gets its own cut. A hit is two sixteenths long by default and a crash is
# one beat, which is the decay the drum library asks for (WZ-R8).
HIT_STEPS = 2
CRASH_STEPS = 4
# A crash is a long note, not a loud one: period 12 to 14, held for a beat
# (WZ-R8). The renderer takes the noise period plus one as the MIDI note.
CRASH_PERIOD = 13
CRASH_NOTE = CRASH_PERIOD + 1
CRASH_VELOCITY = 99

MAX_SIMULTANEOUS = 8

# Device name -> (rule id in data/dissonance_rules.json, risk level).
DEVICE_RULES = {
    "chromatic_passing": ("DIS-01", 1),
    "chromatic_neighbour": ("DIS-02", 1),
    "appoggiatura": ("DIS-03", 2),
    "dominant_flat_nine": ("DIS-11", 3),
    "echo_semitone_clash": ("DIS-18", 3),
}

# Which devices a strength may use, and how many devices an eight bar window
# may hold. The ladder follows the risk levels of data/dissonance_rules.json:
# strength 1 is the risk 1 colour, strength 2 adds the risk 2 edge, strength 3
# adds the risk 3 clash. The rate policy of that file is 1 or 2 devices per
# eight bars at 3 to 6 percent of melody notes and one risk 3 per eight bars,
# so strengths 1 and 2 sit inside the band and strength 3 is its top.
STRENGTH_DEVICES = {
    0: (),
    1: ("chromatic_passing", "chromatic_neighbour"),
    2: ("chromatic_passing", "chromatic_neighbour", "appoggiatura"),
    3: ("chromatic_passing", "chromatic_neighbour", "appoggiatura",
        "dominant_flat_nine", "echo_semitone_clash"),
}
STRENGTH_BUDGET = {0: 0, 1: 1, 2: 2, 3: 3}
STRENGTH_DRUM_LADDER = {0: 0, 1: 1, 2: 2, 3: 3}

RISK3_MIN_BARS_APART = 4
# The two devices that add a note to a voice that was silent: only these can
# push the number of notes sounding at once past the ceiling, so only these are
# tested against it. The three melody devices rewrite one written note into two
# or three and never sound more notes at a time than the note they replaced.
ADDED_NOTE_DEVICES = ("dominant_flat_nine", "echo_semitone_clash")
SPACED_DEVICES = ("dominant_flat_nine", "echo_semitone_clash")
SPACED_DEVICE_BARS = 16
# When two risk 3 devices want the same eight bar window, the flat ninth goes
# first: it is the harmony change the ear review asked for, and the echo clash is
# the rarer garnish.
DEVICE_PRIORITY = {"dominant_flat_nine": 0, "echo_semitone_clash": 1,
                   "chromatic_passing": 0, "chromatic_neighbour": 1,
                   "appoggiatura": 2}

NOTE_OFFSETS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE_ONLY = re.compile(r"\b([A-G][#b]?)(\d)\b")

SCALES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
}


# --------------------------------------------------------------------- helpers

def _read_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _lazy(name):
    """Import a sibling tool at call time, so importing spice stays cheap."""
    module = __import__(name)
    return module


def bar_ticks_of(song):
    beats = int(song.get("time_sig", (4, 4))[0]) or 4
    return beats * int(song["division"])


def bars_of(song):
    """The number of bars the song occupies, rounded up to a whole bar."""
    bar_ticks = bar_ticks_of(song)
    last = max([note[1] for track in song["tracks"] for note in track["notes"]], default=0)
    return max(1, int((last + bar_ticks - 1) // bar_ticks))


def track_of(song, name):
    for track in song["tracks"]:
        if track["name"].strip().lower() == name.strip().lower():
            return track
    return None


def note_name(pitch):
    letters = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return "%s%d" % (letters[int(pitch) % 12], int(pitch) // 12 - 1)


def _beat_of(tick, bar_ticks, division):
    within = tick % bar_ticks
    return within / float(division) + 1.0


def _scale_of_score(score):
    """The pitch classes of the score's key, with the minor leading tone raised."""
    if not score:
        return None, None
    meta = score.get("meta") or {}
    key = str(meta.get("key") or "").strip()
    found = NOTE_ONLY.match(key.split()[0]) if key else None
    if not found:
        return None, None
    letter, accidental = found.group(1), found.group(1)[1:]
    root = (NOTE_OFFSETS[letter[0]] + (1 if accidental == "#" else -1 if accidental == "b" else 0)) % 12
    quality = "minor" if "minor" in key or "min" in key else "major"
    steps = SCALES[quality]
    pcs = {(root + step) % 12 for step in steps}
    if quality == "minor":
        pcs.add((root + 11) % 12)          # the harmonic minor leading tone
    return pcs, (root, quality)


# ------------------------------------------------------------- score sections

def load_score(path):
    if not path or not os.path.exists(path):
        return None
    yaml = _lazy("yaml")
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or None


def default_score_for(midi_path):
    """The score a MIDI probably came from: next to it, then the title theme."""
    if not midi_path:
        return None
    folder = os.path.dirname(os.path.abspath(midi_path))
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".yaml") and name.startswith("score"):
            return os.path.join(folder, name)
    if os.path.exists(DEFAULT_SCORE):
        return DEFAULT_SCORE
    return None


def section_table(score, bars, warnings):
    """[{"name", "first_bar", "bars", "chords"}] for every section, 0 based.

    A score without a `sections` block gives eight bar blocks instead, so the
    drum ladder and the forbidden list still have section edges to work with;
    the report says the sections were inferred, because a chord is then unknown
    and the E7 flat nine device has nothing to test.
    """
    sections = (score or {}).get("sections")
    if isinstance(sections, dict) and sections:
        total = sum(int((spec or {}).get("bars") or 0) for spec in sections.values())
        if total != bars:
            warnings.append("score declares %d bars, the MIDI has %d; sections inferred"
                            % (total, bars))
        else:
            table = []
            first = 0
            for name, spec in sections.items():
                count = int(spec.get("bars") or 0)
                chords = list(spec.get("chords") or [])
                if len(chords) != count:
                    chords = []
                table.append({"name": name, "first_bar": first, "bars": count,
                              "chords": chords})
                first += count
            return table, True
    table = []
    for index in range(0, bars, 8):
        count = min(8, bars - index)
        table.append({"name": "block%d" % (index // 8 + 1), "first_bar": index,
                      "bars": count, "chords": []})
    warnings.append("no usable sections block; %d eight bar blocks inferred" % len(table))
    return table, False


def section_edges(sections):
    """The bars a device may not use: the first and the last bar of a section."""
    forbidden = {}
    for section in sections:
        first = section["first_bar"]
        last = first + section["bars"] - 1
        forbidden.setdefault(first, "first bar of section %s" % section["name"])
        forbidden.setdefault(last, "last bar of section %s" % section["name"])
    return forbidden


def section_of_bar(sections, bar):
    for section in sections:
        if section["first_bar"] <= bar < section["first_bar"] + section["bars"]:
            return section
    return None


# ------------------------------------------------------ the leitmotif freeze

def motif_cells(score):
    """The declared motif cells as interval shapes, read from the motifs block.

    The block is prose with the notes in parentheses ("E5 C5 D5 E5"), so the
    notes are what the match uses. A cell of fewer than two notes cannot shape a
    bar and is skipped.
    """
    cells = []
    motifs = (score or {}).get("motifs")
    if not isinstance(motifs, dict):
        return cells
    for key, text in motifs.items():
        if not isinstance(text, str):
            continue
        names = NOTE_ONLY.findall(text)
        pitches = []
        for letter, octave in names:
            letter = letter
            base = NOTE_OFFSETS[letter[0]]
            if letter[1:] == "#":
                base += 1
            elif letter[1:] == "b":
                base -= 1
            pitches.append(base + 12 * (int(octave) + 1))
        if len(pitches) < 2:
            continue
        cells.append({"id": key, "size": len(pitches),
                      "intervals": tuple(b - a for a, b in zip(pitches, pitches[1:]))})
    return cells


def melody_bars(song):
    """{bar: [notes]} for the melody track."""
    track = track_of(song, MELODY_TRACK)
    if track is None or not track["notes"]:
        with_notes = [t for t in song["tracks"] if t["notes"]]
        if not with_notes:
            return {}, None
        track = max(with_notes,
                    key=lambda t: sum(n[2] for n in t["notes"]) / len(t["notes"]))
    bar_ticks = bar_ticks_of(song)
    out = {}
    for note in sorted(track["notes"]):
        out.setdefault(note[0] // bar_ticks, []).append(note)
    return out, track


def motif_shaped(intervals, cell):
    """True when a bar's intervals are the cell's, within a semitone per step.

    The tolerance is what lets "K a third lower" count as a K statement: its
    shape is one semitone off the cell's first interval, and it is still the
    motif by ear. Being generous here only freezes more bars, which is the safe
    direction for a leitmotif.
    """
    if len(intervals) != cell["size"] - 1:
        return False
    return all(abs(a - b) <= 1 for a, b in zip(intervals, cell["intervals"]))


def frozen_bars(song, score, config):
    """The bars no device may touch: motif statements and motif returns."""
    by_bar, _track = melody_bars(song)
    cells = motif_cells(score)
    frozen = {}
    for bar, notes in by_bar.items():
        if len(notes) < 2:
            continue
        intervals = tuple(b[2] - a[2] for a, b in zip(notes, notes[1:]))
        for cell in cells:
            if motif_shaped(intervals, cell):
                frozen[bar] = "motif %s" % cell["id"]
                break
    melody = _melody_view(song, by_bar)
    if melody is not None:
        motif = hook_score.find_motif(melody, config)
        if motif:
            for start in motif["occurrences"]:
                for bar in range(start, start + motif["bars"]):
                    frozen.setdefault(bar, "hook_score motif return")
    return frozen


def _melody_view(song, by_bar):
    if not by_bar:
        return None
    track = track_of(song, MELODY_TRACK)
    if track is None or not track["notes"]:
        return None
    return hook_score.Melody(list(track["notes"]), song["division"],
                             int(song.get("time_sig", (4, 4))[0]), 4,
                             name=track["name"])


# ------------------------------------------------------------- the drum plan

def builtin_library(meter="3/4", steps=12):
    """A small built in set, used when data/drum_patterns.json is absent.

    The schema is the library's own: a pattern owns a list of steps, and a step
    holds a noise hit (period plus level) and or a DMC hit.
    """
    def hit(instrument, velocity, period=None, loop="long"):
        out = {"instrument": instrument, "velocity": velocity, "accent": False}
        if period is not None:
            out["period"] = period
            out["loop"] = loop
        return out

    patterns = [
        {"id": "SPK-01", "name": "Built in: waltz with a ghost snare",
         "feel": "waltz", "meter": "3/4", "bars": 1, "steps_count": 12,
         "steps": [[hit("dpcm_kick", 127)], [], [], [], [hit("noise", 57, 4)], [],
                   [hit("noise", 28, 6)], [], [hit("noise", 71, 4)], [], [], []]},
        {"id": "SPK-02", "name": "Built in: waltz with the kick on the and of two",
         "feel": "waltz", "meter": "3/4", "bars": 1, "steps_count": 12,
         "steps": [[hit("dpcm_kick", 127)], [], [], [], [hit("noise", 57, 4)], [],
                   [hit("dpcm_kick", 99)], [], [hit("noise", 71, 4)], [], [],
                   [hit("noise", 42, 5)]]},
        {"id": "SPK-03", "name": "Built in: soft waltz, snare on three",
         "feel": "waltz", "meter": "3/4", "bars": 1, "steps_count": 12,
         "steps": [[hit("dpcm_kick", 113)], [], [], [], [hit("noise", 42, 5)], [], [], [],
                   [hit("dpcm_snare", 71)], [hit("noise", 42, 5)], [], []]},
    ]
    fills = [
        {"id": "SPK-F1", "name": "Built in: one beat roll", "type": "noise_roll",
         "length_beats": 1, "steps_count": 4, "fits_feels": ["waltz"],
         "placement": ["phrase_end_4"],
         "steps": [[hit("dpcm_kick", 113)], [hit("dpcm_snare", 71)],
                   [hit("dpcm_snare", 85)], [hit("dpcm_snare", 113)]]},
        {"id": "SPK-F2", "name": "Built in: two beat roll", "type": "noise_roll",
         "length_beats": 2, "steps_count": 8, "fits_feels": ["waltz"],
         "placement": ["phrase_end_8"],
         "steps": [[hit("dpcm_kick", 113)], [hit("dpcm_snare", 42)],
                   [hit("dpcm_snare", 57)], [hit("dpcm_snare", 71)],
                   [hit("dpcm_kick", 99)], [hit("dpcm_snare", 85)],
                   [hit("dpcm_snare", 99)], [hit("dpcm_snare", 127)]]},
    ]
    return {"patterns": {p["id"]: p for p in patterns},
            "fills": {f["id"]: f for f in fills},
            "order": [p["id"] for p in patterns],
            "waltz": {"plain_control_ids": [], "non_plain_3_4_ids": [p["id"] for p in patterns],
                      "two_bar_hemiola_pairs": []},
            "source": "built-in"}


def load_library(path):
    """The pattern library from data/drum_patterns.json, or the built in set."""
    data = _read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("patterns"), list):
        return builtin_library()
    patterns = {p["id"]: p for p in data["patterns"] if p.get("id") and p.get("steps")}
    fills = {f["id"]: f for f in (data.get("fills") or []) if f.get("id") and f.get("steps")}
    waltz = data.get("waltz_section") or {}
    return {"patterns": patterns, "fills": fills,
            "order": [p["id"] for p in data["patterns"]],
            "waltz": waltz, "source": os.path.abspath(path)}


def meter_string(song):
    numerator, denominator = song.get("time_sig", (4, 4))
    return "%d/%d" % (int(numerator), int(denominator))


def home_patterns(library, meter, feel):
    """The patterns a section may use as its home groove.

    The plain control pattern is excluded (WZ-R1), and so is every pattern whose
    tags make it a device rather than a groove: a hemiola is a two bar figure
    that comes after the metre is established (WZ-R3, WZ-R4), cut time is one
    four bar stretch (WZ-R12) and the drop out bar is a rung of the ladder, not
    a home. Using one of those as a section's home would put a device on every
    bar of the section.
    """
    patterns = library["patterns"]
    waltz = library.get("waltz") or {}
    meter_key = meter.replace("/", "_")
    listed = waltz.get("non_plain_%s_ids" % meter_key) or []
    excluded = set(waltz.get("plain_control_ids") or ())
    device_tags = {"hemiola", "cut_time", "dropout"}

    def usable(pid):
        pattern = patterns.get(pid)
        if not pattern or pattern.get("meter") != meter or pattern.get("bars") != 1:
            return False
        if pid in excluded:
            return False
        if device_tags & set(pattern.get("tags") or ()):
            return False
        return True

    out = [pid for pid in listed if usable(pid)]
    if not out:
        out = [pid for pid in library["order"]
               if usable(pid) and patterns[pid].get("feel") == feel]
    if not out:
        out = [pid for pid in library["order"] if usable(pid)]
    return sorted(out)


def soft_patterns(library, meter):
    """Soft grooves for a section the score asks to keep quiet."""
    patterns = library["patterns"]
    for wanted in (("calm",), ("baroque",)):
        out = sorted([pid for pid in library["order"]
                      if pid in patterns and patterns[pid].get("meter") == meter
                      and patterns[pid].get("bars") == 1
                      and patterns[pid].get("feel") in wanted
                      and not ({"hemiola", "cut_time", "dropout"}
                               & set(patterns[pid].get("tags") or ()))])
        if out:
            return out
    return []


def fill_patterns(library, beats):
    """Waltz fills of one or two beats, from the library's fills block."""
    out = []
    for fid, fill in sorted(library["fills"].items()):
        if fill.get("length_beats") != beats:
            continue
        if "waltz" in (fill.get("fits_feels") or []):
            out.append(fid)
    if not out:
        out = [fid for fid, fill in sorted(library["fills"].items())
               if fill.get("length_beats") == beats]
    return out


def ladder_rungs(strength, bars_in_section):
    """The rung of every bar of a section, read from the library's ladder.

    0 plain, 1 ghost note, 2 displaced accent, 3 fill, 4 kick drop out,
    5 crash. The cycles are the library's `four_bar_cycle` and `eight_bar_cycle`
    written out, and the three hard rules of the ladder are repaired here: no
    two fills in a row, one crash per section on its first bar, and a section
    shorter than four bars gets rungs 0 and 3 only.
    """
    if strength <= 0 or bars_in_section <= 0:
        return [0] * max(0, bars_in_section)
    n = bars_in_section
    if n < 4:
        rungs = [0] * n
        if strength >= 2 and n:
            rungs[-1] = 3
        if n:
            rungs[0] = 5 if strength >= 1 else 0
        return rungs
    if strength == 1:
        rungs = [0] * n
    elif strength == 2:
        cycle = (0, 1, 0, 3)
        rungs = [cycle[index % 4] for index in range(n)]
    else:
        cycle = (0, 1, 0, 3, 2, 1, 4, 3)
        rungs = [cycle[index % 8] for index in range(n)]
    if strength >= 1:
        rungs[0] = 5
    if strength >= 2:
        rungs[-1] = 3
    if strength >= 3:
        if n > 6:
            # The hemiola pair needs three bars of plain waltz first (WZ-R3).
            rungs[2] = "hemiola_a"
            rungs[3] = "hemiola_b"
        if n > 8:
            # The sixteen bar cycle marks its top with the crash rung again and
            # with the section's other home pattern.
            rungs[8] = 5
            if n > 9:
                rungs[9] = 0
    # Hard rule: never two fills in a row.
    for index in range(1, n):
        if rungs[index] == 3 and rungs[index - 1] == 3:
            rungs[index - 1] = 0
    return rungs


def drum_plan(song, sections, strength, seed, library, warnings):
    """{bar: {"pattern", "rung", "fill", "crash"}} for every drum bar."""
    patterns = library["patterns"]
    meter = meter_string(song)
    feel = "waltz"
    dry = [track_of(song, name) for name in DRUM_TRACKS]
    activity = {}
    for track in dry:
        for note in track["notes"] if track else []:
            activity.setdefault(note[0] // bar_ticks_of(song), 0)
            activity[note[0] // bar_ticks_of(song)] += 1

    rng = random.Random("spice-drums-%d" % seed)
    plan = {}
    previous_home = None
    for section_index, section in enumerate(sections):
        name = section["name"].lower()
        loud = home_patterns(library, meter, feel)
        soft = soft_patterns(library, meter)
        pool = loud
        if any(word in name for word in ("trio", "calm", "intro", "memory")) and soft:
            pool = soft
        if not pool:
            warnings.append("no %s pattern in the library, drums left alone" % meter)
            continue
        home = pool[rng.randrange(len(pool))]
        if home == previous_home and len(pool) > 1:
            home = pool[(pool.index(home) + 1) % len(pool)]
        alternate = pool[(pool.index(home) + 1) % len(pool)]
        previous_home = home

        bars = section["bars"]
        first = section["first_bar"]
        drum_bars = [first + offset for offset in range(bars)
                     if activity.get(first + offset)]
        if not drum_bars:
            continue
        rungs = ladder_rungs(STRENGTH_DRUM_LADDER.get(strength, 0), len(drum_bars))
        for offset, bar in enumerate(drum_bars):
            rung = rungs[offset]
            pattern = home
            if rung == "hemiola_a":
                pair = (library.get("waltz") or {}).get("two_bar_hemiola_pairs") or []
                pattern = pair[0]["pair"][0] if pair else home
                rung = 0
                plan[bar] = {"pattern": pattern, "rung": "hemiola", "fill": None,
                             "crash": False, "section": section["name"]}
                continue
            if rung == "hemiola_b":
                pair = (library.get("waltz") or {}).get("two_bar_hemiola_pairs") or []
                pattern = pair[0]["pair"][1] if pair else home
                rung = 0
                plan[bar] = {"pattern": pattern, "rung": "hemiola", "fill": None,
                             "crash": False, "section": section["name"]}
                continue
            if bar == first + 8 and STRENGTH_DRUM_LADDER.get(strength, 0) >= 3:
                pattern = alternate
            fill = None
            if rung == 3:
                remaining = len(drum_bars) - offset
                beats = 2 if (remaining == 1 and len(drum_bars) >= 8) else 1
                options = fill_patterns(library, beats)
                fill = options[rng.randrange(len(options))] if options else None
            if rung == "crash":
                rung = 0
            plan[bar] = {"pattern": pattern, "rung": rung, "fill": fill,
                         "crash": bool(offset == 0 and strength >= 1),
                         "section": section["name"]}
    return plan


def pattern_steps(pattern, steps_per_bar, bar_offset=0):
    """The steps of one bar of a pattern, as a list of step hit lists."""
    steps = pattern.get("steps") or []
    total = len(steps)
    if not total:
        return [[] for _ in range(steps_per_bar)]
    start = (bar_offset * steps_per_bar) % total
    return [list(steps[(start + index) % total]) for index in range(steps_per_bar)]


def fill_steps(fill, count):
    steps = list(fill.get("steps") or [])
    if not steps:
        return [[] for _ in range(count)]
    out = []
    for index in range(count):
        out.append(list(steps[index]) if index < len(steps) else [])
    return out


def apply_rung(steps, rung, bar, seed):
    """Rewrite a bar's step list for one rung of the variation ladder."""
    notes = []
    count = len(steps)
    if rung == 1:
        # A ghost note: one soft noise hit in an empty step, level 2 or 3, a
        # period of 5 to 7 (WZ-R6). The step chosen is the first empty one after
        # a hit, which is where a ghost reads as a ghost.
        for index in range(count):
            if steps[index]:
                continue
            if index and steps[index - 1]:
                steps[index] = [{"instrument": "noise", "velocity": 34,
                                 "period": 6 + (bar % 2), "loop": "short"}]
                notes.append("ghost note at step %d" % (index + 1))
                break
    elif rung == 2:
        # The second kick moves to the and of 2 or the and of 3 (WZ-R5).
        kicks = [index for index in range(count)
                 if any(hit.get("instrument") == "dpcm_kick" for hit in steps[index])]
        if len(kicks) >= 2:
            source = kicks[1]
            for target in (6, 10):
                if target < count and not steps[target] and target != source:
                    steps[target] = steps[source]
                    steps[source] = []
                    notes.append("kick moved from step %d to step %d"
                                 % (source + 1, target + 1))
                    break
    elif rung == 4:
        dropped = 0
        for index in range(count):
            kept = [hit for hit in steps[index] if hit.get("instrument") != "dpcm_kick"]
            if len(kept) != len(steps[index]):
                dropped += 1
            steps[index] = kept
        if dropped:
            notes.append("kick dropped for the bar")
        if not any(steps):
            # The ladder says the noise keeps the time when the kick drops out,
            # so a bar that only had DMC hits keeps a soft hat instead of going
            # silent: a silent bar is not the rung, it is a hole.
            if count > 4:
                steps[4] = [{"instrument": "noise", "velocity": 42, "period": 4,
                             "loop": "long"}]
                notes.append("soft hat on beat 2 keeps the time")
    return steps, notes


def render_bar(hits_by_step, bar_start, step_ticks, crash=False):
    """Turn a bar of step hit lists into (start, end, pitch, velocity) notes.

    The noise channel gets one note at a time: each noise hit ends where the next
    noise onset begins, and a crash is held for one beat (WZ-R8). The DPCM
    channel is cut at its own next onset only.
    """
    out = []
    for channel, name in (("noise", "noise"), ("dpcm", "dpcm")):
        onsets = []
        for index, step in enumerate(hits_by_step):
            for hit in step:
                instrument = hit.get("instrument")
                if channel == "noise" and instrument != "noise":
                    continue
                if channel == "dpcm" and not str(instrument).startswith("dpcm"):
                    continue
                start = bar_start + index * step_ticks
                if channel == "noise":
                    pitch = int(hit.get("period") or 5) + 1
                    length = step_ticks * (CRASH_STEPS if (crash and index == 0)
                                           else HIT_STEPS)
                else:
                    pitch = 36 if instrument == "dpcm_kick" else 38
                    length = step_ticks * HIT_STEPS
                onsets.append([start, pitch, int(hit.get("velocity") or 70), length])
        onsets.sort()
        for index, note in enumerate(onsets):
            limit = onsets[index + 1][0] if index + 1 < len(onsets) else bar_start + \
                len(hits_by_step) * step_ticks
            end = min(note[0] + note[3], limit)
            end = max(note[0] + 1, end)
            out.append((note[0], end, note[1], note[2]))
    return sorted(out)


def drum_step_map(notes, bar_start, step_ticks, steps_per_bar):
    """{step: tuple of (channel, pitch, velocity)} for comparison and counting."""
    out = {}
    for start, _end, pitch, velocity in notes:
        index = (start - bar_start) // step_ticks
        if index < 0 or index >= steps_per_bar:
            continue
        channel = "noise" if 1 <= pitch <= 15 else "dpcm"
        out.setdefault(index, []).append((channel, pitch, velocity))
    return {index: tuple(sorted(value)) for index, value in out.items()}


def peak_with_drums(song, start, end, extra):
    """The largest number of notes sounding at once in [start, end).

    The song's own drum tracks are ignored, because they are the notes being
    replaced; `extra` holds the ones that would replace them.
    """
    events = []
    for track in song["tracks"]:
        if track["name"].strip().lower() in DRUM_TRACKS:
            continue
        for note in track["notes"]:
            if note[0] < end and start < note[1]:
                events.append((max(note[0], start), 1))
                events.append((min(note[1], end), -1))
    for note in extra:
        events.append((max(note[0], start), 1))
        events.append((min(note[1], end), -1))
    events.sort(key=lambda item: (item[0], item[1]))
    count = best = 0
    for _tick, delta in events:
        count += delta
        best = max(best, count)
    return best


def apply_drums(song, sections, strength, seed, library, warnings, ceiling=None):
    """Replace the drum tracks bar by bar. Returns (report fragment).

    A bar whose pattern would make the piece denser than the arrangement already
    was loses its quietest hits, one at a time, until the bar fits. The ghost
    notes go first, which is also the right musical answer.
    """
    bar_ticks = bar_ticks_of(song)
    division = int(song["division"])
    step_ticks = division // 4
    steps_per_bar = bar_ticks // step_ticks
    plan = drum_plan(song, sections, strength, seed, library, warnings) if strength else {}

    noise = track_of(song, "noise")
    dpcm = track_of(song, "dpcm")
    if noise is None or dpcm is None:
        warnings.append("the song has no noise or no dpcm track, drums left alone")
        return {"changed_steps": 0, "bars": {}, "patterns": {}, "fills": 0,
                "crashes": 0, "ghost_notes": 0, "kicks_dropped": 0,
                "displaced_accents": 0, "hemiola_bars": [], "silent_bars": [],
                "steps_in": 0, "steps_out": 0, "hits_dropped": 0,
                "source": library.get("source")}

    report = {"changed_steps": 0, "bars": {}, "patterns": {}, "fills": 0,
              "crashes": 0, "ghost_notes": 0, "kicks_dropped": 0,
              "displaced_accents": 0, "hemiola_bars": [], "silent_bars": [],
              "steps_in": 0, "steps_out": 0, "hits_dropped": 0,
              "source": library.get("source")}

    before = {}
    for bar in range(bars_of(song)):
        bar_start = bar * bar_ticks
        before[bar] = (drum_step_map([n for n in noise["notes"]
                                      if bar_start <= n[0] < bar_start + bar_ticks],
                                     bar_start, step_ticks, steps_per_bar),
                       drum_step_map([n for n in dpcm["notes"]
                                      if bar_start <= n[0] < bar_start + bar_ticks],
                                     bar_start, step_ticks, steps_per_bar))

    new_noise = []
    new_dpcm = []
    for bar in range(bars_of(song)):
        bar_start = bar * bar_ticks
        item = plan.get(bar)
        if item is None:
            new_noise.extend([n for n in noise["notes"]
                              if bar_start <= n[0] < bar_start + bar_ticks])
            new_dpcm.extend([n for n in dpcm["notes"]
                             if bar_start <= n[0] < bar_start + bar_ticks])
            has_notes = before[bar][0] or before[bar][1]
            if has_notes:
                report["silent_bars"].append(bar + 1)
            continue

        pattern = library["patterns"][item["pattern"]]
        offset = 0
        if pattern.get("steps_count") and steps_per_bar:
            offset = 0
        steps = pattern_steps(pattern, steps_per_bar, offset)
        changes = []
        if item.get("fill"):
            fill = library["fills"].get(item["fill"])
            if fill:
                count = int(fill.get("steps_count") or steps_per_bar)
                count = max(1, min(steps_per_bar, count))
                fill_block = fill_steps(fill, count)
                start = steps_per_bar - count
                steps[start:] = fill_block
                changes.append("fill %s over the last %d step(s)" % (item["fill"], count))
                report["fills"] += 1
        steps, rung_changes = apply_rung(steps, item["rung"], bar, seed)
        changes.extend(rung_changes)
        if item["rung"] == 1 and rung_changes:
            report["ghost_notes"] += 1
        if item["rung"] == 2 and rung_changes:
            report["displaced_accents"] += 1
        if item["rung"] == 4 and rung_changes:
            report["kicks_dropped"] += 1
        if item["rung"] == "hemiola":
            report["hemiola_bars"].append(bar + 1)
            changes.append("hemiola bar from %s" % item["pattern"])
        if item.get("crash"):
            steps[0] = [hit for hit in steps[0] if hit.get("instrument") != "noise"]
            steps[0].append({"instrument": "noise", "velocity": CRASH_VELOCITY,
                             "period": CRASH_PERIOD, "loop": "long"})
            report["crashes"] += 1
            changes.append("crash on the downbeat (period %d, one beat)" % CRASH_PERIOD)

        rendered = render_bar(steps, bar_start, step_ticks, crash=bool(item.get("crash")))
        if ceiling is not None:
            dropped = 0
            while rendered and peak_with_drums(song, bar_start, bar_start + bar_ticks,
                                               rendered) > ceiling:
                victim = min(rendered, key=lambda note: (note[3], -note[0]))
                rendered.remove(victim)
                dropped += 1
            if dropped:
                report["hits_dropped"] += dropped
                changes.append("%d quiet hit(s) dropped to stay inside the "
                               "arrangement's note ceiling" % dropped)
        for note in rendered:
            if 1 <= note[2] <= 15:
                new_noise.append(note)
            else:
                new_dpcm.append(note)

        after_noise = drum_step_map([n for n in rendered if 1 <= n[2] <= 15],
                                    bar_start, step_ticks, steps_per_bar)
        after_dpcm = drum_step_map([n for n in rendered if not (1 <= n[2] <= 15)],
                                   bar_start, step_ticks, steps_per_bar)
        in_map = dict(before[bar][0])
        in_map.update(before[bar][1])
        out_map = dict(after_noise)
        out_map.update(after_dpcm)
        changed = [step for step in sorted(set(in_map) | set(out_map))
                   if in_map.get(step) != out_map.get(step)]
        report["changed_steps"] += len(changed)
        report["patterns"][item["pattern"]] = report["patterns"].get(item["pattern"], 0) + 1
        report["bars"][str(bar + 1)] = {
            "pattern": item["pattern"], "rung": item["rung"],
            "section": item["section"], "fill": item.get("fill"),
            "crash": bool(item.get("crash")),
            "changed_steps": [step + 1 for step in changed],
            "changes": changes,
        }

    report["steps_in"] = sum(len(value) for pair in before.values() for value in pair)
    steps_out = 0
    for bar in range(bars_of(song)):
        bar_start = bar * bar_ticks
        window = [n for n in new_noise if bar_start <= n[0] < bar_start + bar_ticks]
        steps_out += len(drum_step_map(window, bar_start, step_ticks, steps_per_bar))
        window = [n for n in new_dpcm if bar_start <= n[0] < bar_start + bar_ticks]
        steps_out += len(drum_step_map(window, bar_start, step_ticks, steps_per_bar))
    report["steps_out"] = steps_out
    noise["notes"] = sorted(new_noise)
    dpcm["notes"] = sorted(new_dpcm)
    return report


# --------------------------------------------------------- the dissonance pass

def chord_parts(section, bar):
    """The chord symbols sounding in a bar, one or two, or none."""
    if not section or not section.get("chords"):
        return []
    offset = bar - section["first_bar"]
    if offset < 0 or offset >= len(section["chords"]):
        return []
    symbol = str(section["chords"][offset])
    return [part.strip() for part in symbol.split("|") if part.strip()]


def chord_object(symbol):
    if not symbol:
        return None
    arrange = _lazy("arrange")
    try:
        return arrange.parse_chord(symbol)
    except Exception:
        return None


def is_dominant(chord):
    """A dominant seventh colour: a major third and a minor seventh."""
    if chord is None:
        return False
    tones = list(getattr(chord, "tones", []) or [])
    return 4 in tones and 10 in tones


def simultaneous_count(song, start, end, skip=None):
    """The largest number of notes sounding at once inside [start, end)."""
    events = []
    for track in song["tracks"]:
        for note in track["notes"]:
            if note[0] < end and start < note[1]:
                events.append((note[0], 1))
                events.append((note[1], -1))
    events.sort(key=lambda item: (item[0], item[1]))
    count = best = 0
    for _tick, delta in events:
        count += delta
        best = max(best, count)
    return best


def _device_candidates(song, sections, frozen, scale_pcs, devices, step_ticks):
    """Every place a device could go, in bar order, before budgets are applied."""
    division = int(song["division"])
    bar_ticks = bar_ticks_of(song)
    by_bar, melody_track = melody_bars(song)
    echo = track_of(song, ECHO_TRACK)
    saw = track_of(song, SAW_TRACK)
    edges = section_edges(sections)
    candidates = []
    for bar in sorted(by_bar):
        notes = sorted(by_bar[bar])
        section = section_of_bar(sections, bar)
        bar_start = bar * bar_ticks
        blocked = None
        if bar in edges:
            blocked = "F2/F3 %s" % edges[bar]
        elif bar == 0:
            blocked = "F3 first bar of the cue"
        if blocked:
            candidates.append({"bar": bar, "device": None, "blocked": blocked,
                               "tick": bar_start})
            continue

        # A frozen bar keeps its melody, so the three devices that rewrite a
        # melody note and the echo clash are refused there (F1). The flat ninth
        # is a pad note laid over the chord and never touches the motif, so it
        # is still allowed.
        frozen_here = bar in frozen
        order = list(devices)
        fits = []
        for device in order:
            if frozen_here and device != "dominant_flat_nine":
                found = None
            elif device == "chromatic_passing":
                found = _passing_candidate(notes, step_ticks)
            elif device == "chromatic_neighbour":
                found = _neighbour_candidate(notes, step_ticks, bar_ticks)
            elif device == "appoggiatura" and scale_pcs:
                found = _appoggiatura_candidate(notes, step_ticks, scale_pcs)
            elif device == "dominant_flat_nine" and section is not None:
                found = _flat_nine_candidate(bar, section, saw, bar_ticks, division)
            elif device == "echo_semitone_clash" and echo is not None:
                found = _echo_clash_candidate(notes, echo, step_ticks, bar_start, bar_ticks)
            else:
                found = None
            if found:
                fits.append(found | {"bar": bar, "device": device, "section": section})
        if fits:
            # The two devices that add a note are rare, spaced by design and
            # asked for by name, so one of them always wins its bar. Between the
            # devices that rewrite a melody note, which one is used moves with
            # the bar number, so a score full of long notes does not become a
            # score full of one device. The choice is deterministic because the
            # bar number is; the seed only decides where the drum patterns land.
            harmony = [fit for fit in fits if fit["device"] in ADDED_NOTE_DEVICES]
            melody = [fit for fit in fits if fit["device"] not in ADDED_NOTE_DEVICES]
            if harmony:
                candidates.append(harmony[0])
            else:
                candidates.append(melody[bar % len(melody)])
        else:
            reason = ("F1 frozen leitmotif bar (%s)" % frozen[bar] if frozen_here
                      else "no usable slot")
            candidates.append({"bar": bar, "device": None, "blocked": reason,
                               "tick": bar_start})
    return candidates, melody_track


def _passing_candidate(notes, step_ticks):
    """A chromatic passing tone between two melody notes a whole tone apart."""
    for index in range(len(notes) - 1):
        first, second = notes[index], notes[index + 1]
        if second[0] != first[1]:
            continue
        gap = second[2] - first[2]
        if abs(gap) != 2:
            continue
        if (first[1] - first[0]) < 2 * step_ticks:
            continue
        tick = second[0] - step_ticks
        pitch = second[2] + (1 if gap > 0 else -1)
        return {"tick": tick, "voice": MELODY_TRACK, "rule": "DIS-01", "risk": 1,
                "host": first, "next": second, "split": True, "note": (tick, second[0], pitch),
                "detail": "%s to %s %s to %s" % (note_name(first[2]), note_name(second[2]),
                                                 "rising" if gap > 0 else "falling",
                                                 note_name(pitch))}
    return None


def _neighbour_candidate(notes, step_ticks, bar_ticks):
    """A chromatic lower neighbour on a held note, returning to the same pitch.

    The neighbour needs two sixteenths of the note's tail: one for the dip, one
    for the return, so the note has to be at least a beat long.
    """
    for index in range(len(notes)):
        note = notes[index]
        length = note[1] - note[0]
        if length < 4 * step_ticks:
            continue
        if index + 1 < len(notes) and notes[index + 1][0] != note[1]:
            continue
        dip = note[1] - 2 * step_ticks
        if note[2] - 1 < 1:
            continue
        return {"tick": dip, "voice": MELODY_TRACK, "rule": "DIS-02", "risk": 1,
                "host": note, "neighbour": (dip, dip + step_ticks, note[2] - 1),
                "return": (dip + step_ticks, note[1], note[2]),
                "detail": "%s dips to %s and returns" % (note_name(note[2]),
                                                         note_name(note[2] - 1))}
    return None


def _appoggiatura_candidate(notes, step_ticks, scale_pcs):
    """A chromatic appoggiatura on a strong beat, resolving down by semitone.

    The strong beat note is rewritten as the appoggiatura for one sixteenth,
    then the chord tone for the rest, so the bar keeps its written length and
    the release lands where the player would put it.
    """
    bar_grid = None
    for note in notes:
        length = note[1] - note[0]
        if length < 2 * step_ticks:
            continue
        if bar_grid is None:
            bar_grid = note[0]
        if (note[0] - bar_grid) % (6 * step_ticks) >= 2 * step_ticks:
            continue
        pitch = note[2] + 1
        if pitch > 127 or (pitch % 12) in scale_pcs:
            continue
        tick = note[0]
        return {"tick": tick, "voice": MELODY_TRACK, "rule": "DIS-03", "risk": 2,
                "host": note, "appoggiatura": (tick, tick + step_ticks, pitch),
                "resolution": (tick + step_ticks, note[1], note[2]),
                "detail": "%s appoggiatura resolving to %s" % (note_name(pitch),
                                                               note_name(note[2]))}
    return None


def _flat_nine_candidate(bar, section, saw, bar_ticks, division):
    """One flat ninth added to the pad over a dominant seventh bar."""
    if saw is None or not saw["notes"]:
        return None
    chords = [chord_object(part) for part in chord_parts(section, bar)]
    dominants = [chord for chord in chords if is_dominant(chord)]
    if not dominants:
        return None
    chord = dominants[-1]
    bar_start = bar * bar_ticks
    tick = bar_start + 2 * division
    window = [note for note in saw["notes"]
              if bar_start <= note[0] < bar_start + bar_ticks]
    if not window:
        return None
    host = min(window, key=lambda note: (abs(note[0] - tick), note[2]))
    flat_nine_pc = (chord.root_pc + 1) % 12
    pitch = host[2]
    while pitch % 12 != flat_nine_pc:
        pitch += 1
    while pitch > 74:
        pitch -= 12
    if pitch < 43 or pitch > 79:
        return None
    end = min(host[1], host[0] + division // 2)
    if end <= host[0]:
        end = host[0] + division // 2
    return {"tick": host[0], "voice": SAW_TRACK, "rule": "DIS-11", "risk": 3,
            "note": (host[0], end, pitch),
            "detail": "%s flat ninth over %s" % (note_name(pitch), chord.symbol)}


def _echo_clash_candidate(notes, echo, step_ticks, bar_start, bar_ticks):
    """A minor second between the echo and a melody note the lead is holding.

    Any two sixteenth window inside the held note will do, as long as the echo
    is free there: the echo repeats the melody an eighth late, so its notes sit
    under the lead most of the time and the clashing window has to be found.
    """
    for note in notes:
        length = note[1] - note[0]
        if length < 3 * step_ticks:
            continue
        tick = note[0] + step_ticks
        while tick + 2 * step_ticks <= note[1]:
            end = tick + 2 * step_ticks
            if end > bar_start + bar_ticks:
                break
            busy = any(other[0] < end and tick < other[1] for other in echo["notes"])
            if busy:
                tick += step_ticks
                continue
            pitch = note[2] - 1
            if pitch < 43:
                pitch = note[2] + 1
            if pitch < 43 or pitch > 96:
                tick += step_ticks
                continue
            return {"tick": tick, "voice": ECHO_TRACK, "rule": "DIS-18", "risk": 3,
                    "note": (tick, end, pitch),
                    "detail": "echo %s against the lead %s" % (note_name(pitch),
                                                               note_name(note[2]))}
    return None


def select_devices(candidates, sections, strength, song, ceiling=None):
    """Apply the budgets, the spacing rules and the chip's note limit.

    The note limit is the peak the arranger itself reached, so a device may never
    make the piece denser than the arrangement already was.
    """
    budget = STRENGTH_BUDGET.get(strength, 0)
    ceiling = MAX_SIMULTANEOUS if ceiling is None else ceiling
    if not budget:
        return [], {}
    division = int(song["division"])
    bar_ticks = bar_ticks_of(song)
    accepted = []
    rejected = {}
    per_window = {}
    last_tick = None
    spaced_bar = {}
    # The risk 3 devices are rare by design and the card asks for them by name,
    # so they are offered the budget first; the colour fills what is left. The
    # order is still deterministic: risk first, then bar order.
    ordered = sorted(candidates,
                     key=lambda item: (0 if item.get("device") is None else -1,
                                       0 if item.get("device") is None
                                       else -DEVICE_RULES[item["device"]][1],
                                       DEVICE_PRIORITY.get(item.get("device"), 9),
                                       item["bar"]))
    for item in ordered:
        if item.get("device") is None:
            reason = item.get("blocked") or "no device"
            key = reason.split(" ")[0]
            rejected[key] = rejected.get(key, 0) + 1
            continue
        device = item["device"]
        bar = item["bar"]
        risk = DEVICE_RULES[device][1]
        window = bar // 8
        if per_window.get(window, 0) >= budget:
            rejected["budget"] = rejected.get("budget", 0) + 1
            continue
        risk3 = sum(1 for other in accepted if DEVICE_RULES[other["device"]][1] == 3)
        risk3_windows = {}
        for other in accepted:
            if DEVICE_RULES[other["device"]][1] == 3:
                risk3_windows[other["bar"] // 8] = risk3_windows.get(other["bar"] // 8, 0) + 1
        if risk == 3 and risk3_windows.get(window, 0) >= 1:
            rejected["risk3_budget"] = rejected.get("risk3_budget", 0) + 1
            continue
        if last_tick is not None and abs(item["tick"] - last_tick) < 2 * division:
            rejected["F4 spacing"] = rejected.get("F4 spacing", 0) + 1
            continue
        if device in SPACED_DEVICES:
            previous = spaced_bar.get(device)
            if previous is not None and abs(bar - previous) < SPACED_DEVICE_BARS:
                rejected["F4 risk3 spacing"] = rejected.get("F4 risk3 spacing", 0) + 1
                continue
        if risk == 3 and "risk3_bar" in spaced_bar:
            if abs(bar - spaced_bar["risk3_bar"]) < RISK3_MIN_BARS_APART:
                rejected["F4 risk3 spacing"] = rejected.get("F4 risk3 spacing", 0) + 1
                continue
        span = item.get("note") or item.get("neighbour") or item.get("appoggiatura")
        if item["device"] in ADDED_NOTE_DEVICES and span and \
                simultaneous_count(song, span[0], span[1]) + 1 > ceiling:
            rejected["simultaneous"] = rejected.get("simultaneous", 0) + 1
            continue
        accepted.append(item)
        per_window[window] = per_window.get(window, 0) + 1
        last_tick = item["tick"]
        if device in SPACED_DEVICES:
            spaced_bar[device] = bar
        if risk == 3:
            spaced_bar["risk3_bar"] = bar
    return accepted, rejected


def melody_score(song, config):
    """The hook score of the melody track, computed exactly the way the tool does."""
    track = track_of(song, MELODY_TRACK)
    if track is None or not track["notes"]:
        return None
    melody = hook_score.Melody(list(track["notes"]), song["division"],
                               int(song.get("time_sig", (4, 4))[0]), 4,
                               name=track["name"])
    return hook_score.score_melody(melody, config)["score"]


def guard_hook_score(song, accepted, melody_track, config, report, warnings,
                     allowed=None):
    """Drop melody devices from the end until the hook score keeps its points.

    The card's check is that hook_score.py does not drop by more than five
    points. A device that costs more than that is not worth its colour, so it is
    reverted and the report says which one and why.
    """
    allowed = DEFAULT_MAX_HOOK_DROP if allowed is None else allowed
    before = melody_score(song, config)
    report["hook"] = {"before": before, "after": before, "drop": 0,
                      "allowed_drop": allowed, "reverted": []}
    if before is None:
        return accepted
    melody_devices = [item for item in accepted
                      if item["voice"] == MELODY_TRACK]
    if not melody_devices:
        return accepted

    # The devices are applied by the caller after this guard, so the score is
    # measured on a copy of the melody track with each device applied in order.
    def score_with(items):
        saved = list(melody_track["notes"])
        try:
            for item in items:
                if item["voice"] != MELODY_TRACK:
                    continue
                _apply_melody_device_preview(melody_track, item)
            return melody_score(song, config)
        finally:
            melody_track["notes"] = saved

    kept = list(accepted)
    guard = 0
    while True:
        score = score_with(kept)
        if score is None or before - score <= allowed:
            report["hook"]["after"] = score
            report["hook"]["drop"] = 0 if score is None else before - score
            return kept
        victims = [item for item in kept if item["voice"] == MELODY_TRACK]
        if not victims or guard > 12:
            warnings.append("hook score guard could not reach the limit")
            report["hook"]["after"] = score
            report["hook"]["drop"] = before - score
            return kept
        victim = victims[-1]
        kept.remove(victim)
        report["hook"]["reverted"].append({
            "bar": victim["bar"] + 1, "device": victim["device"],
            "score": score})
        guard += 1


def _apply_melody_device_preview(track, item):
    device = item["device"]
    if device == "chromatic_passing":
        first = item["host"]
        if first not in track["notes"]:
            return
        track["notes"].remove(first)
        track["notes"].append((first[0], item["note"][0], first[2], first[3]))
        track["notes"].append((item["note"][0], item["note"][1], item["note"][2], first[3]))
    elif device == "chromatic_neighbour":
        host = item["host"]
        if host not in track["notes"]:
            return
        track["notes"].remove(host)
        track["notes"].append((host[0], item["neighbour"][0], host[2], host[3]))
        track["notes"].append(item["neighbour"] + (max(1, host[3] - 6),))
        track["notes"].append(item["return"] + (host[3],))
    elif device == "appoggiatura":
        host = item["host"]
        if host not in track["notes"]:
            return
        track["notes"].remove(host)
        track["notes"].append(item["appoggiatura"] + (max(1, host[3] - 4),))
        track["notes"].append(item["resolution"] + (host[3],))
    track["notes"].sort()


# --------------------------------------------------------------- verification

def melody_digest(song, bars):
    """A sha256 over every melody note event of the given bars."""
    track = track_of(song, MELODY_TRACK)
    bar_ticks = bar_ticks_of(song)
    if track is None:
        return None, 0
    events = []
    for note in sorted(track["notes"]):
        if note[0] // bar_ticks in bars:
            events.append(note)
    payload = b"".join(b"%d:%d:%d:%d;" % (n[0], n[1], n[2], n[3]) for n in events)
    return hashlib.sha256(payload).hexdigest(), len(events)


def verify_frozen_bars(before, after, frozen):
    """The leitmotif bars are unchanged, note for note and byte for byte."""
    bars = set(frozen)
    digest_before, count_before = melody_digest(before, bars)
    digest_after, count_after = melody_digest(after, bars)
    return {
        "bars": [bar + 1 for bar in sorted(bars)],
        "count": len(bars),
        "notes_before": count_before,
        "notes_after": count_after,
        "sha256_before": digest_before,
        "sha256_after": digest_after,
        "identical": digest_before == digest_after and count_before == count_after,
    }


def melody_untouched_outside(before, after, touched_bars):
    """Every melody note outside the device bars survives unchanged."""
    bar_ticks = bar_ticks_of(before)
    track_before = track_of(before, MELODY_TRACK)
    track_after = track_of(after, MELODY_TRACK)
    if track_before is None or track_after is None:
        return True, 0
    kept = [note for note in track_before["notes"]
            if note[0] // bar_ticks not in touched_bars]
    others = [note for note in track_after["notes"]
              if note[0] // bar_ticks not in touched_bars]
    return sorted(kept) == sorted(others), len(kept)


# ------------------------------------------------------------------ the pass

def spice_song(song_in, seed=DEFAULT_SEED, drums=DEFAULT_DRUMS,
               dissonance=DEFAULT_DISSONANCE, score=None, library=None,
               rules_data=None, warnings=None, max_hook_drop=DEFAULT_MAX_HOOK_DROP):
    """Return (song_out, report). The input dict is not modified."""
    warnings = warnings if warnings is not None else []
    song = {"format": song_in.get("format", 1), "division": int(song_in["division"]),
            "tempo_us": int(song_in.get("tempo_us", 500000)),
            "time_sig": tuple(song_in.get("time_sig", (4, 4))),
            "tracks": [{"name": track["name"],
                        "notes": [tuple(note) for note in track["notes"]],
                        "cc": {controller: list(events) for controller, events
                               in track["cc"].items()}}
                       for track in song_in["tracks"]]}
    snapshot = {"format": song["format"], "division": song["division"],
                "tempo_us": song["tempo_us"], "time_sig": song["time_sig"],
                "tracks": [{"name": track["name"], "notes": list(track["notes"]),
                            "cc": dict(track["cc"])} for track in song["tracks"]]}

    library = library or load_library(DEFAULT_DRUM_DATA)
    rules_data = rules_data if rules_data is not None else _read_json(DEFAULT_DISSONANCE_DATA)
    bars = bars_of(song)
    sections, sections_known = section_table(score, bars, warnings)
    scale_pcs, key_info = _scale_of_score(score)

    frozen = frozen_bars(song, score, hook_score.load_grammar()[0]) if dissonance else {}
    frozen_after = dict(frozen)
    peak_in = max_simultaneous(snapshot)

    drum_report = apply_drums(song, sections, drums, seed, library, warnings,
                              ceiling=peak_in)

    dis_report = {"injected": 0, "notes_added": 0, "by_device": {}, "devices": [],
                  "rejected": {}, "protected_bars": [bar + 1 for bar in sorted(frozen)],
                  "rules_source": (os.path.abspath(DEFAULT_DISSONANCE_DATA)
                                   if rules_data else None)}
    if dissonance:
        melody_track = track_of(song, MELODY_TRACK)
        config, _source = hook_score.load_grammar()
        devices = STRENGTH_DEVICES.get(dissonance, ())
        candidates, _track = _device_candidates(song, sections, frozen_after, scale_pcs,
                                                devices, int(song["division"]) // 4)
        accepted, rejected = select_devices(candidates, sections, dissonance, song,
                                            ceiling=peak_in)
        dis_report["rejected"] = rejected
        if melody_track is not None:
            accepted = guard_hook_score(song, accepted, melody_track, config,
                                        dis_report, warnings,
                                        allowed=max_hook_drop)
            dis_report = _apply_selected(song, accepted, dis_report)
        else:
            warnings.append("no melody track; nothing injected")
        if rules_data:
            known = {rule["id"] for rule in rules_data.get("rules") or []}
            missing = sorted({DEVICE_RULES[item["device"]][0] for item in accepted}
                             - known)
            if missing:
                warnings.append("rule ids not in the rules file: %s" % ", ".join(missing))

    simultaneity = max_simultaneous(song)
    leitmotif = verify_frozen_bars(snapshot, song, frozen_after)
    untouched, note_count = melody_untouched_outside(
        snapshot, song, {item["bar"] - 1 for item in dis_report["devices"]})
    dis_report["devices"].sort(key=lambda item: (item["bar"], item["tick"]))

    report = {
        "tool": "spice.py",
        "seed": seed,
        "drums_strength": drums,
        "dissonance_strength": dissonance,
        "division": song["division"],
        "tempo_us": song["tempo_us"],
        "time_sig": "%d/%d" % song["time_sig"],
        "bar_ticks": bar_ticks_of(song),
        "bars": bars,
        "sections_known": sections_known,
        "sections": [{"name": section["name"], "first_bar": section["first_bar"] + 1,
                      "bars": section["bars"]} for section in sections],
        "key": (None if key_info is None else "%d %s" % (key_info[0], key_info[1])),
        "drums": drum_report,
        "dissonance": dis_report,
        "leitmotif": leitmotif,
        "melody_unchanged_outside_devices": {"passed": untouched, "notes": note_count},
        "max_simultaneous_notes": simultaneity,
        "peak_simultaneous_in": peak_in,
        "chip_limit": MAX_SIMULTANEOUS,
        "warnings": warnings,
    }
    return song, report


def max_simultaneous(song):
    events = []
    for track in song["tracks"]:
        for note in track["notes"]:
            events.append((note[0], 1))
            events.append((note[1], -1))
    events.sort(key=lambda item: (item[0], item[1]))
    count = best = 0
    for _tick, delta in events:
        count += delta
        best = max(best, count)
    return best


def _apply_selected(song, accepted, report):
    """Apply the accepted devices to the song, filling the report as it goes."""
    division = int(song["division"])
    bar_ticks = bar_ticks_of(song)
    for item in accepted:
        device = item["device"]
        track = track_of(song, item["voice"])
        if track is None:
            continue
        if device == "chromatic_passing":
            host = item["host"]
            if host not in track["notes"]:
                continue
            track["notes"].remove(host)
            track["notes"].append((host[0], item["note"][0], host[2], host[3]))
            track["notes"].append((item["note"][0], item["note"][1], item["note"][2],
                                   host[3]))
            added = 1
        elif device == "chromatic_neighbour":
            host = item["host"]
            if host not in track["notes"]:
                continue
            track["notes"].remove(host)
            track["notes"].append((host[0], item["neighbour"][0], host[2], host[3]))
            track["notes"].append(item["neighbour"] + (max(1, host[3] - 6),))
            track["notes"].append(item["return"] + (host[3],))
            added = 2
        elif device == "appoggiatura":
            host = item["host"]
            if host not in track["notes"]:
                continue
            track["notes"].remove(host)
            track["notes"].append(item["appoggiatura"] + (max(1, host[3] - 4),))
            track["notes"].append(item["resolution"] + (host[3],))
            added = 1
        else:
            note = item["note"]
            track["notes"].append((note[0], note[1], note[2], 70))
            added = 1
        track["notes"].sort()
        report["injected"] += 1
        report["notes_added"] += added
        report["by_device"][device] = report["by_device"].get(device, 0) + 1
        report["devices"].append({
            "bar": item["bar"] + 1,
            "beat": round(_beat_of(item["tick"], bar_ticks, division), 2),
            "voice": item["voice"],
            "device": device,
            "rule": item["rule"],
            "risk": DEVICE_RULES[device][1],
            "detail": item.get("detail", ""),
            "tick": item["tick"],
        })
    return report


# ----------------------------------------------------------------- file level

def arrange_score(score_path, out_path, warnings):
    """Arrange a score yaml to a MIDI, so spice can take either input."""
    arrange = _lazy("arrange")
    score = load_score(score_path)
    if not isinstance(score, dict):
        raise ValueError("cannot read a score from %s" % score_path)
    if isinstance(score.get("sections"), dict):
        arrangement = arrange.build_arrangement_v3(score)
    else:
        arrangement = arrange.build_arrangement(score)
    arrange.write_midi(arrangement, out_path)
    return score


def spice_file(source, target=None, seed=DEFAULT_SEED, drums=DEFAULT_DRUMS,
               dissonance=DEFAULT_DISSONANCE, score_path=None,
               drum_data=DEFAULT_DRUM_DATA, dissonance_data=DEFAULT_DISSONANCE_DATA,
               humanize_after=False, humanize_seed=None,
               max_hook_drop=DEFAULT_MAX_HOOK_DROP, write=True):
    """Spice a MIDI file (or a score yaml). Returns the report."""
    warnings = []
    source = os.path.abspath(source)
    temp = None
    if source.lower().endswith((".yaml", ".yml")):
        temp = source + ".spice-arranged.mid"
        score = arrange_score(source, temp, warnings)
        midi_path = temp
        score_path = score_path or source
    else:
        midi_path = source
        score = load_score(score_path or default_score_for(source))
        if score is None:
            warnings.append("no score read, so the sections and the chords are unknown")

    with open(midi_path, "rb") as handle:
        data = handle.read()
    song = hook_score.parse_smf(data, name=midi_path)
    song_out, report = spice_song(song, seed=seed, drums=drums, dissonance=dissonance,
                                  score=score, library=load_library(drum_data),
                                  rules_data=_read_json(dissonance_data),
                                  warnings=warnings, max_hook_drop=max_hook_drop)
    result = humanize_module().write_smf(song_out)
    report["midi_in"] = source
    report["score"] = os.path.abspath(score_path) if score_path else None
    report["bytes_in"] = len(data)
    report["bytes_out"] = len(result)
    report["sha256_in"] = hashlib.sha256(data).hexdigest()
    report["sha256_out"] = hashlib.sha256(result).hexdigest()
    report["humanize"] = None

    if write and target:
        if humanize_after:
            report["humanize"] = humanize_after_pass(result, humanize_seed)
            result = report["humanize"].pop("_bytes")
            report["sha256_final"] = hashlib.sha256(result).hexdigest()
        directory = os.path.dirname(os.path.abspath(target))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(result)
        report["midi_out"] = os.path.abspath(target)
    if temp and os.path.exists(temp):
        os.unlink(temp)
    return report


def humanize_module():
    """tools/humanize.py, imported on demand: it carries the project's SMF writer."""
    return _lazy("humanize")


def humanize_after_pass(data, humanize_seed=None):
    """Run the project's humanizer over the spiced bytes, keeping the report."""
    humanize = humanize_module()
    seed = DEFAULT_SEED if humanize_seed is None else humanize_seed
    result, report = humanize.humanize_bytes(data, seed=seed, name="spice")
    keep = {key: report.get(key) for key in
            ("seed", "notes", "notes_changed", "fills", "grace_notes", "mordents",
             "breaths", "vibrato_notes", "envelope_points", "sha256_in", "sha256_out")}
    keep["_bytes"] = result
    return keep


def default_output(source, drums, dissonance):
    base, extension = os.path.splitext(source)
    return "%s_spice_d%d_x%d%s" % (base, drums, dissonance, extension or ".mid")


def format_report(report):
    lines = []
    lines.append("spice: %s" % report.get("midi_in"))
    if report.get("midi_out"):
        lines.append("  out %s" % report["midi_out"])
    lines.append("  seed %d | drums %d | dissonance %d | %d bars | %s | %d ticks per bar"
                 % (report["seed"], report["drums_strength"],
                    report["dissonance_strength"], report["bars"], report["time_sig"],
                    report["bar_ticks"]))
    if report.get("score"):
        lines.append("  score %s (%s sections)"
                     % (report["score"], "declared" if report["sections_known"]
                        else "inferred"))
    drums = report["drums"]
    lines.append("  drums: %d pattern(s) over %d bar(s), %d drum steps changed "
                 "(input %d steps, output %d)"
                 % (len(drums["patterns"]), len(drums["bars"]), drums["changed_steps"],
                    drums["steps_in"], drums["steps_out"]))
    lines.append("    fills %d | crashes %d | ghost notes %d | displaced accents %d "
                 "| kicks dropped %d | hemiola bars %s"
                 % (drums["fills"], drums["crashes"], drums["ghost_notes"],
                    drums["displaced_accents"], drums["kicks_dropped"],
                    ",".join(str(bar) for bar in drums["hemiola_bars"]) or "none"))
    for name in sorted(drums["patterns"]):
        lines.append("    pattern %-8s %d bar(s)" % (name, drums["patterns"][name]))
    if drums["silent_bars"]:
        lines.append("    bars left without drums (no drum note in the input): %s"
                     % ",".join(str(bar) for bar in drums["silent_bars"]))
    for bar in sorted(drums["bars"], key=lambda value: int(value)):
        item = drums["bars"][bar]
        detail = "; ".join(item["changes"]) if item["changes"] else "home pattern"
        lines.append("    bar %2s %-9s %-8s rung %-4s %2d step(s) changed  %s"
                     % (bar, item["section"], item["pattern"], item["rung"],
                        len(item["changed_steps"]), detail))

    dis = report["dissonance"]
    lines.append("  dissonance: %d device(s), %d note(s) added"
                 % (dis["injected"], dis["notes_added"]))
    for item in dis["devices"]:
        lines.append("    bar %2d beat %-4s %-13s %-20s %-6s %s"
                     % (item["bar"], item["beat"], item["voice"], item["device"],
                        item["rule"], item["detail"]))
    if dis["rejected"]:
        lines.append("    refused: %s" % ", ".join(
            "%s %d" % (key, value) for key, value in sorted(dis["rejected"].items())))

    leitmotif = report["leitmotif"]
    lines.append("  leitmotif: %d frozen bar(s) %s"
                 % (leitmotif["count"], ",".join(str(bar) for bar in leitmotif["bars"])))
    lines.append("    melody events identical: %s (%d notes, sha %s)"
                 % ("yes" if leitmotif["identical"] else "NO",
                    leitmotif["notes_after"],
                    (leitmotif["sha256_after"] or "")[:16]))
    others = report["melody_unchanged_outside_devices"]
    lines.append("    melody outside the device bars unchanged: %s (%d notes)"
                 % ("yes" if others["passed"] else "NO", others["notes"]))
    hook = dis["hook"] if isinstance(dis.get("hook"), dict) else None
    if hook:
        lines.append("  hook_score: %s before, %s after, drop %s (allowed %s)%s"
                     % (hook["before"], hook["after"], hook["drop"], hook["allowed_drop"],
                        "" if not hook["reverted"] else
                        "; reverted %d device(s) for cost" % len(hook["reverted"])))
    lines.append("  notes sounding at once: %d (the arrangement peaks at %d, the chip "
                 "declares %d)" % (report["max_simultaneous_notes"],
                                   report["peak_simultaneous_in"], report["chip_limit"]))
    if report.get("humanize"):
        human = report["humanize"]
        lines.append("  humanize rerun: seed %s, %d notes changed, %d fills, sha %s"
                     % (human.get("seed"), human.get("notes_changed"),
                        human.get("fills"), (human.get("sha256_out") or "")[:16]))
    for warning in report.get("warnings") or []:
        lines.append("  warning: %s" % warning)
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="an arrange.py MIDI, or a score yaml")
    parser.add_argument("out", nargs="?", default=None, help="output MIDI")
    parser.add_argument("--drums", type=int, default=DEFAULT_DRUMS, choices=(0, 1, 2, 3),
                        help="drum variation strength, 0 to 3 (default %d)" % DEFAULT_DRUMS)
    parser.add_argument("--dissonance", type=int, default=DEFAULT_DISSONANCE,
                        choices=(0, 1, 2, 3),
                        help="dissonance strength, 0 to 3 (default %d)"
                             % DEFAULT_DISSONANCE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="fixed seed (default %d)" % DEFAULT_SEED)
    parser.add_argument("--score", default=None,
                        help="the score the MIDI came from (default: looked up)")
    parser.add_argument("--drum-data", default=DEFAULT_DRUM_DATA,
                        help="data/drum_patterns.json")
    parser.add_argument("--dissonance-data", default=DEFAULT_DISSONANCE_DATA,
                        help="data/dissonance_rules.json")
    parser.add_argument("--report", default=None, help="write the JSON report here")
    parser.add_argument("--humanize", action="store_true",
                        help="rerun tools/humanize.py on the output")
    parser.add_argument("--humanize-seed", type=int, default=None,
                        help="seed for the humanizer (default: the spice seed)")
    parser.add_argument("--max-hook-drop", type=int, default=DEFAULT_MAX_HOOK_DROP,
                        help="refuse melody devices that cost more hook_score points "
                             "(default %d)" % DEFAULT_MAX_HOOK_DROP)
    parser.add_argument("--dry-run", action="store_true",
                        help="report only, write no MIDI")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.out:
        args.out = default_output(args.source, args.drums, args.dissonance)

    report = spice_file(args.source, args.out, seed=args.seed, drums=args.drums,
                        dissonance=args.dissonance, score_path=args.score,
                        drum_data=args.drum_data,
                        dissonance_data=args.dissonance_data,
                        humanize_after=args.humanize,
                        humanize_seed=args.humanize_seed,
                        max_hook_drop=args.max_hook_drop,
                        write=not args.dry_run)
    print(format_report(report))
    if args.report:
        directory = os.path.dirname(os.path.abspath(args.report))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print("  json: %s" % os.path.abspath(args.report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
