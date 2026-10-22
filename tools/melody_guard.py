"""melody_guard.py: the originality check for a melody.

The theme must not resemble any existing game melody. This tool turns a
melody into a sequence of (pitch interval, rhythm) pairs, builds the 5-gram
set of that sequence, and compares it with every melody in a reference
folder. It exits 1 when a reference shares a run of 8 or more identical
intervals with the melody under test.

A reference folder may hold Standard MIDI Files, JSON note lists (a list of
[pitch, duration] pairs, or a list of {"pitch": .., "duration": ..} objects)
and text note lists (one "pitch duration" pair per line, pitch either a MIDI
number or a note name).

Usage:
    melody_guard.py melody.mid reference_folder [more folders ...]
    melody_guard.py --melody-notes notes.json reference_folder

Options:
    --run N          the run length that fails the check (default 8)
    --ngram N        the n-gram length used for the similarity score (default 5)
    --top N          how many closest references to print (default 10)
    --json OUT       write the full report as JSON
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import defaultdict

DEFAULT_RUN = 8
DEFAULT_NGRAM = 5

LETTERS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MELODY_NAMES = ("melody", "lead", "vrc6pulsea", "vrc6 pulse a", "pulse 1", "pulse1")


# ------------------------------------------------------------------ MIDI input

def _read_varlen(data, pos):
    value = 0
    for _ in range(4):
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise ValueError("malformed variable length quantity")


def parse_midi(path):
    """Every track of a Standard MIDI File, as (name, [(start, end, pitch)])."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"MThd":
        raise ValueError("%s is not a Standard MIDI File" % path)
    _fmt, ntracks, _division = struct.unpack(">hhh", data[8:14])
    pos = 14
    tracks = []
    for _ in range(ntracks):
        if data[pos:pos + 4] != b"MTrk":
            break
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + length]
        pos += 8 + length
        name = ""
        notes = []
        pending = {}
        cursor = 0
        tick = 0
        while cursor < len(body):
            delta, cursor = _read_varlen(body, cursor)
            tick += delta
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
                        pending.setdefault(pitch, []).append(tick)
                    else:
                        started = pending.get(pitch)
                        if started:
                            notes.append((started.pop(0), tick, pitch))
                elif status & 0xF0 == 0x80:
                    pitch = body[cursor + 1]
                    cursor += 3
                    started = pending.get(pitch)
                    if started:
                        notes.append((started.pop(0), tick, pitch))
                elif status & 0xF0 in (0xB0, 0xE0):
                    cursor += 3
                else:
                    cursor += 2
        for pitch, starts in pending.items():
            for start in starts:
                notes.append((start, start + 480, pitch))
        notes.sort()
        tracks.append((name, notes))
    return tracks


def note_to_midi(name):
    letter = name[0].upper()
    index = 1
    accidental = 0
    if index < len(name) and name[index] in "#b":
        accidental = 1 if name[index] == "#" else -1
        index += 1
    octave = int(name[index:])
    return (octave + 1) * 12 + LETTERS[letter] + accidental


# ------------------------------------------------------------------ the melody

def melody_from_midi(path):
    """The melody of a MIDI file: (name, [(start, end, pitch)]).

    The track named as a melody wins. Otherwise the track with the highest
    mean pitch and the most notes wins, and percussion tracks never do.
    """
    tracks = parse_midi(path)
    best = []
    best_name = ""
    best_score = None
    for name, notes in tracks:
        if not notes:
            continue
        low = name.lower().replace(" ", "").replace("_", "")
        if any(tag in low for tag in ("noise", "drum", "perc", "kick", "dpcm")):
            continue
        pitches = [n[2] for n in notes]
        mean_pitch = sum(pitches) / float(len(pitches))
        named = any(tag.replace(" ", "") in low for tag in MELODY_NAMES)
        score = (1 if named else 0, round(mean_pitch, 3), len(notes))
        if best_score is None or score > best_score:
            best_score = score
            best = notes
            best_name = name
    return best_name, best


def melody_from_notes(path):
    """A melody from a JSON or text note list, as [(start, end, pitch)]."""
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if isinstance(raw, dict):
            raw = raw.get("notes") or raw.get("melody") or []
        notes = []
        tick = 0
        for entry in raw:
            if isinstance(entry, dict):
                pitch = entry.get("pitch")
                length = entry.get("duration", entry.get("length", entry.get("dur", 240)))
            else:
                pitch = entry[0]
                length = entry[1] if len(entry) > 1 else 240
            if isinstance(pitch, str):
                pitch = note_to_midi(pitch)
            notes.append((tick, tick + int(length), int(pitch)))
            tick += int(length)
        return os.path.basename(path), notes
    notes = []
    tick = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").split()
            if len(parts) < 2:
                continue
            pitch = parts[0]
            length = int(float(parts[1]))
            if not pitch.lstrip("-").isdigit():
                pitch = note_to_midi(pitch)
            pitch = int(pitch)
            notes.append((tick, tick + length, pitch))
            tick += length
    return os.path.basename(path), notes


def load_melody(path):
    if path.lower().endswith((".mid", ".midi")):
        return melody_from_midi(path)
    return melody_from_notes(path)


def intervals(notes):
    """(semitone interval, duration in ticks) between consecutive notes."""
    out = []
    for (_s0, e0, p0), (_s1, _e1, p1) in zip(notes, notes[1:]):
        out.append((p1 - p0, max(1, e0 - _s0)))
    return out


def ngrams(pairs, n=DEFAULT_NGRAM):
    if len(pairs) < n:
        return set()
    return {tuple(pairs[i:i + n]) for i in range(len(pairs) - n + 1)}


def longest_identical_run(a, b):
    """The longest run of consecutive identical (interval, rhythm) pairs."""
    positions = defaultdict(list)
    for index, pair in enumerate(b):
        positions[pair].append(index)
    best = 0
    for i, pair in enumerate(a):
        for j in positions.get(pair, ()):
            run = 0
            while (i + run < len(a) and j + run < len(b)
                   and a[i + run] == b[j + run]):
                run += 1
            if run > best:
                best = run
    return best


def longest_interval_run(a, b):
    """The longest run of identical pitch intervals, whatever the rhythm."""
    ia = [p[0] for p in a]
    ib = [p[0] for p in b]
    positions = defaultdict(list)
    for index, value in enumerate(ib):
        positions[value].append(index)
    best = 0
    for i, value in enumerate(ia):
        for j in positions.get(value, ()):
            run = 0
            while i + run < len(ia) and j + run < len(ib) and ia[i + run] == ib[j + run]:
                run += 1
            if run > best:
                best = run
    return best


def reference_melodies(folder):
    """Every melody in a folder, as (path, intervals)."""
    out = []
    for directory, _dirs, files in os.walk(folder):
        for name in sorted(files):
            lower = name.lower()
            if lower.endswith((".mid", ".midi")):
                path = os.path.join(directory, name)
                try:
                    _track, notes = melody_from_midi(path)
                except Exception:
                    continue
            elif lower.endswith((".json", ".txt")):
                path = os.path.join(directory, name)
                try:
                    _track, notes = melody_from_notes(path)
                except Exception:
                    continue
            else:
                continue
            if len(notes) < 4:
                continue
            out.append((path, intervals(notes)))
    return out


def check(melody_path, folders, run_limit=DEFAULT_RUN, ngram=DEFAULT_NGRAM, top=10):
    """Run the check and return (report dict, exit code)."""
    track_name, notes = load_melody(melody_path)
    pairs = intervals(notes)
    grams = ngrams(pairs, ngram)

    report = {
        "melody": os.path.abspath(melody_path),
        "melody_track": track_name,
        "melody_notes": len(notes),
        "melody_intervals": len(pairs),
        "ngram": ngram,
        "run_limit": run_limit,
        "references": 0,
        "highest_jaccard": 0.0,
        "longest_identical_run": 0,
        "longest_interval_run": 0,
        "closest": [],
        "failures": [],
    }

    worst = []
    melody_key = os.path.normcase(os.path.abspath(melody_path))
    for folder in folders:
        for path, ref_pairs in reference_melodies(folder):
            # A melody is never evidence against itself: when the file under
            # test sits in a scanned folder, skip it.
            if os.path.normcase(os.path.abspath(path)) == melody_key:
                continue
            report["references"] += 1
            if len(ref_pairs) < 3:
                continue
            ref_grams = ngrams(ref_pairs, ngram)
            union = len(grams | ref_grams)
            jaccard = (len(grams & ref_grams) / union) if union else 0.0
            run = longest_identical_run(pairs, ref_pairs)
            interval_run = longest_interval_run(pairs, ref_pairs)
            worst.append((jaccard, run, interval_run, path))
            if run >= run_limit:
                report["failures"].append({"path": path, "run": run,
                                           "jaccard": round(jaccard, 4)})

    worst.sort(key=lambda row: (-row[0], -row[1], row[3]))
    if worst:
        report["highest_jaccard"] = round(worst[0][0], 4)
        report["longest_identical_run"] = max(row[1] for row in worst)
        report["longest_interval_run"] = max(row[2] for row in worst)
        report["closest"] = [
            {"path": row[3], "jaccard": round(row[0], 4), "run": row[1],
             "interval_run": row[2]}
            for row in worst[:top]
        ]
    report["passed"] = not report["failures"]
    return report, (0 if report["passed"] else 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("melody", nargs="?", help="a MIDI file or a note list")
    parser.add_argument("folders", nargs="*", help="reference folders")
    parser.add_argument("--melody-notes", help="a note list to test instead of the first argument")
    parser.add_argument("--run", type=int, default=DEFAULT_RUN)
    parser.add_argument("--ngram", type=int, default=DEFAULT_NGRAM)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--json", dest="json_out", help="write the report as JSON")
    args = parser.parse_args(argv)

    melody_path = args.melody_notes or args.melody
    if not melody_path or not args.folders:
        parser.print_usage()
        print("melody_guard.py: a melody and at least one reference folder are needed")
        return 2

    report, code = check(melody_path, args.folders, args.run, args.ngram, args.top)

    if args.json_out:
        directory = os.path.dirname(os.path.abspath(args.json_out))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)

    print("melody: %s (track %r)" % (report["melody"], report["melody_track"]))
    print("  notes: %d, intervals: %d, %d-grams: %d"
          % (report["melody_notes"], report["melody_intervals"],
             report["ngram"], report["ngram"]))
    print("  references compared: %d" % report["references"])
    print("  highest %d-gram Jaccard: %.4f" % (report["ngram"], report["highest_jaccard"]))
    print("  longest identical (interval, rhythm) run: %d" % report["longest_identical_run"])
    print("  longest identical interval run: %d" % report["longest_interval_run"])
    for row in report["closest"]:
        print("    jaccard %.4f  run %d  interval run %d  %s"
              % (row["jaccard"], row["run"], row["interval_run"], row["path"]))
    if report["failures"]:
        print("FAIL: %d reference(s) share a run of %d or more identical intervals"
              % (len(report["failures"]), report["run_limit"]))
        for row in sorted(report["failures"], key=lambda r: -r["run"])[:10]:
            print("  run %d  %s" % (row["run"], row["path"]))
        return 1
    print("PASS: no reference shares a run of %d or more identical intervals" % report["run_limit"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
