"""hook_score.py: measure how memorable a melody is, as a number with reasons.

Input is either a Standard MIDI File (the melody track of an arrange.py
output) or a melody list in JSON. The report is a 0 to 100 score, one line per
criterion with the measured number, and concrete suggestions for the weakest
ones.

The numbers come from knowledge/MUSIC-HOOK-GRAMMAR.md when that file exists
and holds a fenced yaml block with a `hook_score:` mapping; otherwise the
defaults in DEFAULTS below are used and the report says so. The defaults are
Nayil's MEM-TOOLS card of 2026-10-21 (the grammar research replaces them):

    a hook cell of 2 to 6 notes with a repeated rhythm cell
    at least 60 percent of the notes inside a 1 to 2 bar motif that returns
        at least 3 times
    steps over leaps at least 65 percent, with one leap per motif
    range of at most an octave and a half
    contour arch or pedal
    a pitch repeated at least once
    loop length 8, 16 or 32 bars
    a variation on the third return

No randomness, no clock: the same input always gives the same report.

Melody list format (JSON): either a bare list or an object with a "notes" key,
optionally "bars", "beats_per_bar" and "ppq". Each note is one of

    {"start": 1.5, "dur": 1.0, "pitch": 69}       start in beats, dur in beats
    {"bar": 2, "beat": 0.0, "dur": 0.5, "pitch": 72}   1 based bar
    [start_beats, pitch, dur_beats]
    [pitch, dur_beats]                            in playing order

Usage:
    hook_score.py FILE.mid [--track NAME] [--json PATH] [--grammar PATH]
    hook_score.py --melody-json FILE.json [--json PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAMMAR_PATH = os.path.join(ROOT, "knowledge", "MUSIC-HOOK-GRAMMAR.md")

# Names tried in order when no --track is given: the melody track of an
# arrange.py output, then the usual generic names.
MELODY_TRACK_NAMES = ("vrc6 pulse a", "melody", "lead", "pulse a")

DEFAULTS = {
    "hook_cell_notes": [2, 6],
    "motif_bars": [1, 2],
    "motif_min_returns": 3,
    "motif_min_coverage": 0.60,
    "motif_match_min": 0.60,
    "step_semitones": 2,
    "step_ratio_min": 0.65,
    "leap_semitones": 4,
    "leaps_per_motif": 1,
    "max_range_semitones": 18,
    "pedal_range_semitones": 5,
    "repeat_pitch_min": 1,
    "loop_bars": [8, 16, 32],
    "third_return_similarity": [0.30, 0.85],
    "grid": "sixteenth",
    "weights": {
        "motif_coverage": 20,
        "motif_returns": 12,
        "hook_cell": 10,
        "step_ratio": 12,
        "leaps_per_motif": 8,
        "range": 8,
        "contour": 10,
        "repeat_pitch": 6,
        "loop_length": 6,
        "third_return": 8,
    },
}

GRID_DIVISIONS = {"sixteenth": 4, "eighth": 2}


# ---------------------------------------------------------------- grammar file

def load_grammar(path=None):
    """Merge the `hook_score:` yaml block of the grammar file over DEFAULTS.

    Returns (config, source) where source is the path used or the string
    "defaults" when no usable block was found.
    """
    config = json.loads(json.dumps(DEFAULTS))  # deep copy, no shared lists
    path = path or GRAMMAR_PATH
    if not os.path.exists(path):
        return config, "defaults"
    try:
        import yaml
    except Exception:                                   # pragma: no cover
        return config, "defaults"
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    blocks = []
    inside = False
    current = []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if inside:
                blocks.append("\n".join(current))
                current = []
            inside = not inside
            continue
        if inside:
            current.append(line)
    for block in blocks:
        if "hook_score:" not in block:
            continue
        try:
            data = yaml.safe_load(block) or {}
        except Exception:
            continue
        table = data.get("hook_score")
        if not isinstance(table, dict):
            continue
        for key, value in table.items():
            if key == "weights" and isinstance(value, dict):
                config["weights"].update(value)
            elif key in config:
                config[key] = value
        return config, os.path.abspath(path)
    return config, "defaults"


# ---------------------------------------------------------------- MIDI reading

def _read_varlen(data, pos):
    value = 0
    for _ in range(4):
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise ValueError("malformed variable length quantity")


def read_smf(path):
    """Read a Standard MIDI File into a plain dict.

    {"format", "division", "tempo_us", "time_sig",
     "tracks": [{"name", "notes": [(start, end, pitch, velocity)],
                 "cc": {controller: [(tick, value)]}}]}

    Running status is handled. Meta events other than the track name, the
    tempo and the time signature are ignored; arrange.py writes no others.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    return parse_smf(data, name=path)


def parse_smf(data, name="<bytes>"):
    """The reader itself, on bytes, so a caller can parse what it wrote."""
    path = name
    if data[:4] != b"MThd":
        raise ValueError("%s is not a Standard MIDI File (no MThd header)" % path)
    header_len = struct.unpack(">I", data[4:8])[0]
    fmt, ntracks, division = struct.unpack(">hhh", data[8:14])
    if division <= 0:
        raise ValueError("SMPTE time division is not supported (division=%d)" % division)

    pos = 8 + header_len
    tracks = []
    tempo_us = None
    time_sig = None
    for _ in range(ntracks):
        if data[pos:pos + 4] != b"MTrk":
            break
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        tick = 0
        ipos = 0
        status = 0
        name = ""
        notes = []
        cc = {}
        open_notes = {}
        while ipos < len(chunk):
            delta, ipos = _read_varlen(chunk, ipos)
            tick += delta
            byte = chunk[ipos]
            if byte & 0x80:
                status = byte
                ipos += 1
            if status == 0xFF:
                meta = chunk[ipos]
                ipos += 1
                size, ipos = _read_varlen(chunk, ipos)
                payload = chunk[ipos:ipos + size]
                ipos += size
                if meta == 0x03:
                    name = payload.decode("latin-1", "replace").strip()
                elif meta == 0x51 and size == 3 and tempo_us is None:
                    tempo_us = int.from_bytes(payload, "big")
                elif meta == 0x58 and size >= 2 and time_sig is None:
                    time_sig = (payload[0], 2 ** payload[1])
            elif status in (0xF0, 0xF7):
                size, ipos = _read_varlen(chunk, ipos)
                ipos += size
            else:
                kind = status & 0xF0
                nbytes = 1 if kind in (0xC0, 0xD0) else 2
                payload = chunk[ipos:ipos + nbytes]
                ipos += nbytes
                if kind == 0x90 and payload[1] > 0:
                    open_notes.setdefault(payload[0], []).append((tick, payload[1]))
                elif kind == 0x80 or (kind == 0x90 and payload[1] == 0):
                    started = open_notes.get(payload[0])
                    if started:
                        start, velocity = started.pop(0)
                        notes.append((start, tick, payload[0], velocity))
                elif kind == 0xB0:
                    cc.setdefault(payload[0], []).append((tick, payload[1]))
        for pitch, started in open_notes.items():
            for start, velocity in started:
                notes.append((start, tick, pitch, velocity))
        notes.sort()
        for events in cc.values():
            events.sort()
        tracks.append({"name": name, "notes": notes, "cc": cc})

    return {"format": fmt, "division": division,
            "tempo_us": tempo_us or 500000,
            "time_sig": time_sig or (4, 4),
            "tracks": tracks}


def pick_melody_track(song, wanted=None):
    """The melody track: the named one, or the highest average pitch."""
    tracks = [track for track in song["tracks"] if track["notes"]]
    if not tracks:
        raise ValueError("no track holds a note")
    if wanted:
        lowered = wanted.strip().lower()
        for track in tracks:
            if track["name"].strip().lower() == lowered:
                return track
        raise ValueError("no track named %r (have: %s)"
                         % (wanted, ", ".join(t["name"] for t in tracks)))
    for name in MELODY_TRACK_NAMES:
        for track in tracks:
            if track["name"].strip().lower() == name:
                return track
    return max(tracks, key=lambda t: sum(n[2] for n in t["notes"]) / len(t["notes"]))


# --------------------------------------------------------------- the grid view

class Note:
    """One melody note on the grid: start tick, duration, pitch, position."""

    __slots__ = ("start", "dur", "pitch", "velocity", "bar", "slot", "dur_slots")

    def __init__(self, start, dur, pitch, velocity, bar, slot, dur_slots):
        self.start = start
        self.dur = dur
        self.pitch = pitch
        self.velocity = velocity
        self.bar = bar
        self.slot = slot
        self.dur_slots = dur_slots

    def key(self):
        return (self.slot, self.dur_slots, self.pitch)

    def __repr__(self):                                  # pragma: no cover
        return "Note(bar=%d slot=%d dur=%d pitch=%d)" % (
            self.bar, self.slot, self.dur_slots, self.pitch)


class Melody:
    """A melody on a fixed grid, with the per bar signature of its notes."""

    def __init__(self, raw_notes, division, beats_per_bar, grid_div,
                 bars=None, name=""):
        self.division = division
        self.beats_per_bar = beats_per_bar
        self.bar_ticks = beats_per_bar * division
        self.grid = max(1, division // grid_div)
        self.slots_per_bar = max(1, self.bar_ticks // self.grid)
        self.name = name
        self.notes = []
        for start, end, pitch, velocity in raw_notes:
            dur = max(1, end - start)
            bar = start // self.bar_ticks
            slot = int(round((start - bar * self.bar_ticks) / float(self.grid)))
            dur_slots = max(1, int(round(dur / float(self.grid))))
            self.notes.append(Note(start, dur, pitch, velocity,
                                   bar, slot, dur_slots))
        self.notes.sort(key=lambda n: (n.start, n.pitch))
        last_end = max([n.start + n.dur for n in self.notes], default=0)
        derived = int((last_end + self.bar_ticks - 1) // self.bar_ticks)
        self.bars = bars if bars else max(1, derived)

    def bar_signature(self, bar):
        """The notes starting in a bar, as slots counted from the bar start."""
        return tuple(n.key() for n in self.notes if n.bar == bar)

    def segment(self, start_bar, length):
        """Bar aligned signature of a segment, slots counted from its start."""
        slots = self.slots_per_bar
        out = []
        for offset in range(length):
            for slot, dur_slots, pitch in self.bar_signature(start_bar + offset):
                out.append((offset * slots + slot, dur_slots, pitch))
        return tuple(out)

    def segment_notes(self, start_bar, length):
        return [n for n in self.notes
                if start_bar <= n.bar < start_bar + length]

    def pitches_of(self, start_bar, length):
        return [n.pitch for n in self.segment_notes(start_bar, length)]


# --------------------------------------------------------------- the analysis

def find_motif(melody, config):
    """The 1 or 2 bar segment that returns most, and covers most notes.

    A return is a bar aligned segment that is at least `motif_match_min`
    similar to the motif (same slots, durations and pitches), so a phrase that
    comes back with a note or two changed still counts as a return. That is
    also what makes the third return criterion measurable: if only exact
    copies counted, the third return would always be identical to the first.
    """
    best = None
    bar_options = list(config["motif_bars"])
    match_min = float(config.get("motif_match_min", 0.60))
    for length in bar_options:
        if melody.bars < length:
            continue
        starts = list(range(0, melody.bars - length + 1))
        cache = {start: melody.segment(start, length) for start in starts}
        for start, signature in cache.items():
            if not signature:
                continue
            occurrences = [s for s in starts
                           if _similarity(cache[s], signature) >= match_min]
            covered = sum(len(cache[s]) for s in occurrences)
            coverage = covered / float(len(melody.notes))
            candidate = {
                "bars": length,
                "start_bar": start,
                "notes": len(signature),
                "occurrences": occurrences,
                "returns": len(occurrences),
                "coverage": coverage,
            }
            key = (round(coverage, 6), len(occurrences), -length, -start)
            if best is None or key > best[0]:
                best = (key, candidate)
    if best is None:
        return None
    return best[1]


def _intervals(pitches):
    return [b - a for a, b in zip(pitches, pitches[1:])]


def _contour(pitches, pedal_range):
    """'arch', 'pedal' or '' for one phrase of pitches."""
    if len(pitches) < 3:
        return ""
    if max(pitches) - min(pitches) <= pedal_range:
        counts = {}
        for pitch in pitches:
            counts[pitch] = counts.get(pitch, 0) + 1
        if max(counts.values()) >= 2:
            return "pedal"
    diffs = _intervals(pitches)
    rising = [d > 0 for d in diffs if d != 0]
    if len(rising) >= 3:
        turns = sum(1 for a, b in zip(rising, rising[1:]) if a != b)
        if turns == 1:
            return "arch"
    return ""


def repeated_rhythm_cell(melody, low, high):
    """The longest run of 2 to 6 note durations that appears at least twice."""
    durations = [n.dur_slots for n in melody.notes]
    best = None
    for size in range(high, low - 1, -1):
        if len(durations) < size * 2:
            continue
        seen = {}
        for index in range(0, len(durations) - size + 1):
            window = tuple(durations[index:index + size])
            if len(set(window)) == 1 and size > 2:
                # a run of equal lengths is a rhythm too, keep it
                pass
            seen.setdefault(window, []).append(index)
        for window, places in sorted(seen.items()):
            if len(places) >= 2 and all(b - a >= size for a, b in zip(places, places[1:])):
                best = (size, window, len(places))
                break
        if best:
            return best
    return best


def _similarity(first, second):
    if not first or not second:
        return 0.0
    return SequenceMatcher(a=list(first), b=list(second), autojunk=False).ratio()


def score_melody(melody, config, source="defaults", extra=None):
    """Score a Melody against the config. Returns the report dict."""
    weights = config["weights"]
    total_notes = len(melody.notes)
    motif = find_motif(melody, config)
    criteria = []

    def add(key, label, weight, fraction, measured, ideal, suggestion):
        fraction = max(0.0, min(1.0, float(fraction)))
        criteria.append({
            "key": key,
            "criterion": label,
            "weight": weight,
            "fraction": round(fraction, 4),
            "points": round(weight * fraction, 2),
            "measured": measured,
            "ideal": ideal,
            "pass": fraction >= 0.999,
            "suggestion": suggestion if fraction < 0.999 else "",
        })

    if motif is None:
        add("motif_coverage", "motif coverage", weights["motif_coverage"], 0.0,
            "0 notes", "at least %d%% of notes inside the motif"
            % round(config["motif_min_coverage"] * 100),
            "there is no 1 or 2 bar motif at all; repeat a 1 or 2 bar phrase "
            "note for note so the ear has something to hold")
        add("motif_returns", "motif returns", weights["motif_returns"], 0.0,
            "0 returns", "at least %d" % config["motif_min_returns"],
            "nothing returns; a hook is a phrase the listener hears three times")
        add("hook_cell", "hook cell", weights["hook_cell"], 0.0, "none",
            "2 to 6 notes with a repeated rhythm cell",
            "write a 2 to 6 note cell with one rhythm and repeat that rhythm")
        add("step_ratio", "steps over leaps", weights["step_ratio"], 0.0,
            "no motif", "at least %d%% steps" % round(config["step_ratio_min"] * 100),
            "no motif to measure; write the motif first")
        add("leaps_per_motif", "leaps per motif", weights["leaps_per_motif"], 0.0,
            "no motif", "exactly %d" % config["leaps_per_motif"],
            "no motif to measure")
        add("range", "range", weights["range"], 1.0,
            "%d semitones" % (max(n.pitch for n in melody.notes)
                              - min(n.pitch for n in melody.notes)),
            "at most %d semitones" % config["max_range_semitones"], "")
        add("contour", "contour", weights["contour"], 0.0, "none",
            "arch or pedal", "shape each phrase as an arch (up then down) or "
            "hold a pedal pitch")
    else:
        coverage = motif["coverage"]
        need_coverage = config["motif_min_coverage"]
        add("motif_coverage", "motif coverage", weights["motif_coverage"],
            min(1.0, coverage / need_coverage),
            "%d%% of %d notes inside the motif"
            % (round(coverage * 100), total_notes),
            "at least %d%%" % round(need_coverage * 100),
            "the motif leaves too many notes outside it; move material into "
            "the %d bar phrase or drop the notes that do not belong"
            % motif["bars"])

        returns = motif["returns"]
        need_returns = config["motif_min_returns"]
        add("motif_returns", "motif returns", weights["motif_returns"],
            min(1.0, returns / float(need_returns)),
            "%d returns" % returns,
            "at least %d" % need_returns,
            "motif returns only %d times; repeat the %d bar phrase until it "
            "has been heard %d times" % (returns, motif["bars"], need_returns))

        cell = repeated_rhythm_cell(melody, config["hook_cell_notes"][0],
                                    config["hook_cell_notes"][1])
        if cell:
            size, window, places = cell
            add("hook_cell", "hook cell", weights["hook_cell"], 1.0,
                "%d notes, rhythm %s repeated %d times"
                % (size, "/".join(str(w) for w in window), places),
                "2 to 6 notes with a repeated rhythm cell", "")
        else:
            add("hook_cell", "hook cell", weights["hook_cell"], 0.0,
                "no repeated rhythm cell of 2 to 6 notes",
                "2 to 6 notes with a repeated rhythm cell",
                "no rhythm cell of 2 to 6 notes repeats; write one rhythm and "
                "reuse it, the ear remembers rhythm before pitch")

        pitches = melody.pitches_of(motif["start_bar"], motif["bars"])
        intervals = _intervals(pitches)
        steps = sum(1 for gap in intervals if abs(gap) <= config["step_semitones"])
        leaps = sum(1 for gap in intervals if abs(gap) >= config["leap_semitones"])
        ratio = steps / float(len(intervals)) if intervals else 0.0
        add("step_ratio", "steps over leaps", weights["step_ratio"],
            min(1.0, ratio / config["step_ratio_min"]),
            "%d%% steps (%d of %d intervals), %d leaps"
            % (round(ratio * 100), steps, len(intervals), leaps),
            "at least %d%% steps" % round(config["step_ratio_min"] * 100),
            "the motif jumps too much (%d%% steps); turn leaps into steps and "
            "keep the one big jump for the phrase peak" % round(ratio * 100))

        target = config["leaps_per_motif"]
        if leaps == target:
            leap_fraction = 1.0
        elif abs(leaps - target) == 1:
            leap_fraction = 0.5
        else:
            leap_fraction = 0.25
        add("leaps_per_motif", "leaps per motif", weights["leaps_per_motif"],
            leap_fraction, "%d leaps" % leaps,
            "exactly %d" % target,
            "the motif has %d leaps; one leap (%d or more semitones) per "
            "motif is what makes it sing" % (leaps, config["leap_semitones"]))

        contour_hits = 0
        contour_names = []
        for start in motif["occurrences"]:
            shape = _contour(melody.pitches_of(start, motif["bars"]),
                             config["pedal_range_semitones"])
            contour_names.append(shape or "-")
            if shape:
                contour_hits += 1
        add("contour", "contour", weights["contour"],
            contour_hits / float(len(motif["occurrences"])) if motif["occurrences"] else 0.0,
            "%d of %d returns are arch or pedal (%s)"
            % (contour_hits, len(motif["occurrences"]), " ".join(contour_names)),
            "every return arch or pedal",
            "the phrase wanders; shape it as an arch (rise to one peak then "
            "fall) or hold a pedal pitch")

        similarity = None
        if returns >= 3:
            first = melody.segment(motif["occurrences"][0], motif["bars"])
            third = melody.segment(motif["occurrences"][2], motif["bars"])
            similarity = _similarity(first, third)
            low, high = config["third_return_similarity"]
            if low <= similarity <= high:
                third_fraction = 1.0
                third_suggestion = ""
            elif similarity > high:
                third_fraction = 0.4
                third_suggestion = ("the third return is a copy (%d%% the same); "
                                    "change the ending, add a passing note or "
                                    "start it on a different chord tone"
                                    % round(similarity * 100))
            else:
                third_fraction = 0.5
                third_suggestion = ("the third return is too different (%d%% the "
                                    "same); keep the rhythm and contour, change "
                                    "one or two notes" % round(similarity * 100))
            add("third_return", "variation on the third return",
                weights["third_return"], third_fraction,
                "%d%% the same as the first return" % round(similarity * 100),
                "%d to %d%% the same"
                % (round(low * 100), round(high * 100)), third_suggestion)
        else:
            add("third_return", "variation on the third return",
                weights["third_return"], 0.0, "no third return",
                "%d to %d%% the same as the first"
                % (round(config["third_return_similarity"][0] * 100),
                   round(config["third_return_similarity"][1] * 100)),
                "there is no third return to vary; the motif has to come back "
                "three times first")

    pitches_all = [n.pitch for n in melody.notes]
    spread = max(pitches_all) - min(pitches_all) if pitches_all else 0
    max_range = config["max_range_semitones"]
    add("range", "range", weights["range"],
        min(1.0, max_range / spread) if spread else 1.0,
        "%d semitones (%d to %d)" % (spread, min(pitches_all or [0]), max(pitches_all or [0])),
        "at most %d semitones" % max_range,
        "the melody spans %d semitones; keep it inside an octave and a half "
        "so it stays singable" % spread)

    repeats = sum(1 for a, b in zip(pitches_all, pitches_all[1:]) if a == b)
    need_repeat = config["repeat_pitch_min"]
    add("repeat_pitch", "repeated pitch", weights["repeat_pitch"],
        min(1.0, repeats / float(need_repeat)) if need_repeat else 1.0,
        "%d repeated pitches in a row" % repeats,
        "at least %d" % need_repeat,
        "no pitch repeats; holding one note twice gives the phrase weight")

    loop_options = [int(value) for value in config["loop_bars"]]
    if melody.bars in loop_options:
        loop_fraction = 1.0
    elif melody.bars % max(loop_options) == 0 or any(melody.bars % value == 0 for value in loop_options):
        loop_fraction = 0.5
    elif melody.bars % 4 == 0:
        loop_fraction = 0.2
    else:
        loop_fraction = 0.0
    add("loop_length", "loop length", weights["loop_length"], loop_fraction,
        "%d bars" % melody.bars,
        " or ".join(str(value) for value in loop_options) + " bars",
        "%d bars does not loop cleanly; write 8, 16 or 32 bars so the cue can "
        "repeat without a seam" % melody.bars)

    earned = sum(item["points"] for item in criteria)
    total_weight = sum(item["weight"] for item in criteria) or 1
    score = int(round(100.0 * earned / total_weight))
    criteria.sort(key=lambda item: item["weight"] * (1.0 - item["fraction"]),
                  reverse=True)
    weakest = criteria[0]
    report = {
        "source": source,
        "melody_track": melody.name,
        "bars": melody.bars,
        "notes": total_notes,
        "grid": config["grid"],
        "score": max(0, min(100, score)),
        "points": round(earned, 2),
        "weights_total": total_weight,
        "weakest": {"criterion": weakest["criterion"], "key": weakest["key"],
                    "fraction": weakest["fraction"],
                    "points": weakest["points"], "of": weakest["weight"]},
        "motif": None if motif is None else {
            "bars": motif["bars"],
            "start_bar": motif["start_bar"],
            "notes": motif["notes"],
            "returns": motif["returns"],
            "coverage": round(motif["coverage"], 4),
            "occurrence_bars": [bar + 1 for bar in motif["occurrences"]],
        },
        "criteria": criteria,
        "suggestions": [item["suggestion"] for item in criteria
                        if item["suggestion"]],
    }
    if extra:
        report.update(extra)
    return report


def melody_from_melody_json(path):
    """Read a melody list and return raw notes plus the timing it declares."""
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        raw = data.get("notes") or []
        bars = data.get("bars")
        beats_per_bar = int(data.get("beats_per_bar", 4))
        division = int(data.get("ppq", 480))
        name = data.get("name", os.path.basename(path))
    else:
        raw = data
        bars = None
        beats_per_bar = 4
        division = 480
        name = os.path.basename(path)
    notes = []
    cursor = 0.0
    for item in raw:
        if isinstance(item, dict):
            pitch = int(item["pitch"])
            dur = float(item.get("dur", item.get("duration_beats", 1.0)))
            if "start" in item:
                start = float(item["start"])
            elif "bar" in item:
                start = (float(item["bar"]) - 1) * beats_per_bar + float(item.get("beat", 0.0))
            else:
                start = cursor
        elif isinstance(item, (list, tuple)):
            if len(item) >= 3:
                start, pitch, dur = float(item[0]), int(item[1]), float(item[2])
            else:
                pitch, dur = int(item[0]), float(item[1])
                start = cursor
        else:
            raise ValueError("cannot read a note from %r" % (item,))
        notes.append((start, pitch, dur))
        cursor = start + dur
    raw_notes = []
    for start, pitch, dur in notes:
        start_tick = int(round(start * division))
        end_tick = max(start_tick + 1, int(round((start + dur) * division)))
        raw_notes.append((start_tick, end_tick, pitch, 100))
    return raw_notes, division, beats_per_bar, bars, name


def melody_from_midi(path, track=None):
    song = read_smf(path)
    chosen = pick_melody_track(song, track)
    beats_per_bar = song["time_sig"][0]
    return (song, chosen, beats_per_bar)


def score_file(path, track=None, config=None, grammar_source="defaults"):
    """Score a .mid file; returns the report dict."""
    if config is None:
        config, grammar_source = load_grammar()
    song, chosen, beats_per_bar = melody_from_midi(path, track)
    grid_div = GRID_DIVISIONS.get(config["grid"], 4)
    melody = Melody(chosen["notes"], song["division"], beats_per_bar, grid_div,
                    name=chosen["name"])
    report = score_melody(melody, config, source=os.path.abspath(path),
                          extra={"grammar": grammar_source,
                                 "tempo_us": song["tempo_us"],
                                 "midi_tracks": [t["name"] for t in song["tracks"]]})
    return report


def score_melody_json(path, config=None, grammar_source="defaults"):
    if config is None:
        config, grammar_source = load_grammar()
    raw_notes, division, beats_per_bar, bars, name = melody_from_melody_json(path)
    melody = Melody(raw_notes, division, beats_per_bar,
                    GRID_DIVISIONS.get(config["grid"], 4), bars=bars, name=name)
    return score_melody(melody, config, source=os.path.abspath(path),
                        extra={"grammar": grammar_source})


# ------------------------------------------------------------------- printing

def format_report(report):
    lines = []
    lines.append("hook_score: %s" % report["source"])
    lines.append("  melody track %r, %d bars, %d notes, score %d / 100"
                 % (report["melody_track"], report["bars"], report["notes"],
                    report["score"]))
    motif = report.get("motif")
    if motif:
        lines.append("  motif %d bar(s) from bar %d, %d notes, %d returns, %d%% coverage"
                     % (motif["bars"], motif["start_bar"] + 1, motif["notes"],
                        motif["returns"], round(motif["coverage"] * 100)))
    for item in sorted(report["criteria"], key=lambda i: -i["points"] / max(i["weight"], 1)):
        mark = "ok  " if item["pass"] else "fix "
        lines.append("  [%s] %-28s %5.1f / %-3d %s"
                     % (mark, item["criterion"], item["points"], item["weight"],
                        item["measured"]))
    weakest = report["weakest"]
    lines.append("  weakest: %s (%.1f of %d): %s"
                 % (weakest["criterion"], weakest["points"], weakest["of"],
                    next((i["measured"] for i in report["criteria"]
                          if i["key"] == weakest["key"]), "")))
    if report["suggestions"]:
        lines.append("  suggestions:")
        for suggestion in report["suggestions"]:
            lines.append("    - %s" % suggestion)
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("midi", nargs="?", default=None,
                        help="Standard MIDI File to score")
    parser.add_argument("--melody-json", default=None,
                        help="score a melody list instead of a MIDI file")
    parser.add_argument("--track", default=None,
                        help="melody track name (default: the arrange.py melody)")
    parser.add_argument("--json", default=None, help="write the report JSON here")
    parser.add_argument("--grammar", default=None,
                        help="hook grammar markdown (default: knowledge/MUSIC-HOOK-GRAMMAR.md)")
    args = parser.parse_args(argv)
    if not args.midi and not args.melody_json:
        parser.error("give a MIDI file or --melody-json")

    config, source = load_grammar(args.grammar)
    if args.melody_json:
        report = score_melody_json(args.melody_json, config, source)
    else:
        report = score_file(args.midi, args.track, config, source)
    print(format_report(report))
    if args.json:
        directory = os.path.dirname(os.path.abspath(args.json))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.json, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print("  json: %s" % os.path.abspath(args.json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
