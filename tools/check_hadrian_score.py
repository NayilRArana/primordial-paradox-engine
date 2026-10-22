"""check_hadrian_score.py: the MUS-HADRIAN checks, on the score text, no rendering.

Reads assets/audio/hadrian_theme/score_hadrian.yaml and proves, deterministically:
  bars, time signature, key, bpm, every bar's eighth count, the chord frame, the
  Neapolitan placement, the fugue answer, the Picardy turn, and the card's own
  check that bar 9 of the lead reads D then C#.
Writes the report as JSON next to the score (or --json) and prints one line a check.

Usage: python tools/check_hadrian_score.py [score] [--json OUT]
"""
import argparse
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCORE = os.path.join(ROOT, "assets", "audio", "hadrian_theme", "score_hadrian.yaml")
DEFAULT_JSON = os.path.join(ROOT, "assets", "audio", "hadrian_theme", "score_check.json")

EIGHTHS_PER_BAR = 8          # 4/4
PHRASE = 8                   # every section is one 8 bar phrase

# The bident cells, by pitch class where a name is not enough. Octave is ignored
# on purpose: the answer is the same shape higher up.
H_DESCENT = [2, 1, 9, 8]     # D, C#, A, G# (semitones above C)
H4_DESCENT = [7, 6, 2, 1]    # G, F#, D, C#  the same shape a fourth up

NOTE_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
           "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10,
           "Bb": 10, "B": 11}


def note_pc(name):
    """'C#5' -> 1. A rest returns None."""
    if name in (None, "r", "rest"):
        return None
    letter = name[0].upper()
    rest = name[1:]
    while rest and rest[-1].isdigit():
        rest = rest[:-1]
    return NOTE_PC[letter + rest]


def note_octave(name):
    digits = "".join(ch for ch in name if ch.isdigit())
    return int(digits) if digits else None


def chord_quality(symbol):
    """'Dm' -> minor, 'D' -> major, 'A7' -> major, 'Eb' -> major, 'Bb' -> major."""
    root = symbol[0]
    rest = symbol[1:]
    if rest.startswith("#") or rest.startswith("b"):
        rest = rest[1:]
    if rest.startswith("m") and not rest.startswith("maj"):
        return "minor"
    if rest.startswith("dim") or rest.startswith("o"):
        return "diminished"
    return "major"


def chord_root_pc(symbol):
    letter = symbol[0]
    rest = symbol[1:]
    if rest[:1] in ("#", "b"):
        return NOTE_PC[letter + rest[0]]
    return NOTE_PC[letter]


def bars_of(score):
    """Flat list of (absolute bar number, section, chord, melody bar, second voice bar)."""
    rows = []
    for name, spec in score["sections"].items():
        chords = spec.get("chords") or []
        melody = spec.get("melody") or []
        second = spec.get("second_voice") or []
        for offset in range(int(spec["bars"])):
            rows.append({
                "number": len(rows) + 1,
                "section": name,
                "chord": chords[offset],
                "melody": melody[offset],
                "second": second[offset] if offset < len(second) else None,
            })
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("score", nargs="?", default=DEFAULT_SCORE)
    parser.add_argument("--json", default=DEFAULT_JSON)
    args = parser.parse_args(argv)

    with open(args.score, "r", encoding="utf-8") as handle:
        score = yaml.safe_load(handle)

    rows = bars_of(score)
    meta = score["meta"]
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # 1. the card's headline numbers
    total = sum(int(spec["bars"]) for spec in score["sections"].values())
    check("32 bars", total == 32 and len(rows) == 32,
          "%d bars declared, %d bars walked" % (total, len(rows)))
    check("92 bpm", float(meta["bpm"]) == 92.0, "meta bpm %s" % meta["bpm"])
    check("key D minor", str(meta["key"]).strip().lower() == "d minor", "meta key %s" % meta["key"])
    check("time 4/4", str(meta["time"]).strip() == "4/4", "meta time %s" % meta["time"])
    check("loop covers all 32 bars",
          meta["loop_start_section"] == "A" and meta["loop_end_section"] == "close",
          "loop %s to %s" % (meta["loop_start_section"], meta["loop_end_section"]))

    # 2. every bar holds 8 eighths, in the lead and in the second voice
    bad_lead, bad_second = [], []
    for row in rows:
        if row["melody"] is None:
            bad_lead.append(row["number"])
            continue
        length = sum(int(entry[1]) for entry in row["melody"])
        if length != EIGHTHS_PER_BAR:
            bad_lead.append(row["number"])
    for row in rows:
        if row["second"] is None:
            continue
        length = sum(int(entry[1]) for entry in row["second"])
        if length != EIGHTHS_PER_BAR:
            bad_second.append(row["number"])
    check("every lead bar is 8 eighths", not bad_lead, "off: %s" % (bad_lead or "none"))
    check("every second voice bar is 8 eighths", not bad_second, "off: %s" % (bad_second or "none"))

    # 3. chords line up one per bar, and each section is 8 bars
    section_lengths = {name: int(spec["bars"]) for name, spec in score["sections"].items()}
    chord_counts = {name: len(spec.get("chords") or []) for name, spec in score["sections"].items()}
    check("one chord per bar", section_lengths == chord_counts,
          "bars %s chords %s" % (section_lengths, chord_counts))
    check("four phrases of 8 bars", all(count == PHRASE for count in section_lengths.values()),
          str(section_lengths))

    # 4. the harmonic frame: Dm, Bb, Gm, A7 in every phrase, plus the one Neapolitan of each phrase
    frame = {2, 10, 7, 9}        # D, Bb, G, A
    neapolitan = [row["number"] for row in rows if row["chord"] in ("Eb", "Ebmaj", "EbM")]
    off_frame = [row["number"] for row in rows
                 if row["number"] <= 28
                 and chord_root_pc(row["chord"]) not in frame
                 and row["number"] not in neapolitan]
    check("frame is Dm, Bb, Gm, A7 plus the Neapolitan (bars 1 to 28)", not off_frame,
          "outside: %s" % (off_frame or "none"))

    # 5. the Neapolitan Eb once per 8 bar phrase, at bar 7 of the phrase
    check("Neapolitan Eb at bars 7, 15, 23", neapolitan == [7, 15, 23], "Eb bars %s" % neapolitan)

    # 6. the card's own check: bar 9 lead reads D then C# on the first two beats
    bar9 = rows[8]
    head = bar9["melody"][:2]
    names = [entry[0] for entry in head]
    durations = [int(entry[1]) for entry in head]
    check("bar 9 lead is D5 C#5 on beats 1 and 2",
          names == ["D5", "C#5"] and durations == [2, 2],
          "bar 9 starts %s durations %s, section %s" % (names, durations, bar9["section"]))

    # 7. H stated at the top of each phrase, and the answer in the fourth in the middle 8
    def pitches(bar):
        return [entry[0] for entry in bar if entry[0] not in ("r", "rest", None)]

    firsts = [pitches(rows[index]["melody"]) for index in (0, 8, 16, 24)]
    h_ok = all(bar[:4] == ["D5", "C#5", "A4", "G#4"] for bar in firsts)
    check("H opens all four phrases", h_ok,
          "; ".join(str(bar[:4]) for bar in firsts))

    answers = [row["number"] for row in rows
               if row["second"] and pitches(row["second"])[:4] == ["G5", "F#5", "D5", "C#5"]]
    check("H4 answer in the fourth on pulse b in the middle 8",
          [number for number in answers if 9 <= number <= 16] == [11, 14],
          "answer bars %s (middle 8: %s)"
          % (answers, [number for number in answers if 9 <= number <= 16]))

    # 8. the Picardy turn: last 4 bars are D major, and the cue ends on a D major triad
    last_four = rows[28:]
    qualities = [chord_quality(row["chord"]) for row in last_four]
    roots = [chord_root_pc(row["chord"]) for row in last_four]
    check("last 4 bars are a Picardy turn to D major",
          all(q == "major" for q in qualities) and roots[-1] == 2 and qualities[-1] == "major",
          "roots %s qualities %s" % (roots, qualities))

    # 9. the brief's instrument assignments, as written in the voices block
    voices = score["voices"]
    check("hum on pulse 2 at duty 12.5 percent",
          "pulse_2" in voices and float(voices["pulse_2"]["duty"]) == 0.125,
          "pulse_2 %s" % voices.get("pulse_2"))
    check("no vibrato on any voice",
          all(v.get("vibrato") in (None, "none", "None") for v in voices.values()),
          {name: v.get("vibrato") for name, v in voices.items()})
    check("lead is vrc6 pulse a, duty 25 percent",
          float(voices["vrc6_pulse_a"]["duty"]) == 0.25, str(voices["vrc6_pulse_a"]))

    # 10. silence is real: the lead rests in at least 10 of the 32 bars
    silent = [row["number"] for row in rows
              if all(entry[0] in ("r", "rest", None) for entry in row["melody"])]
    check("lead silent in at least 10 bars", len(silent) >= 10,
          "%d silent bars: %s" % (len(silent), silent))

    beats_per_bar = int(str(meta["time"]).split("/")[0])
    seconds = (total * beats_per_bar * 60.0) / float(meta["bpm"])
    report = {
        "score": os.path.abspath(args.score),
        "bars": len(rows),
        "bpm": float(meta["bpm"]),
        "key": meta["key"],
        "time": meta["time"],
        "beats_per_bar": beats_per_bar,
        "eighths_per_bar": EIGHTHS_PER_BAR,
        "sections": section_lengths,
        "loop_seconds": round(seconds, 3),
        "neapolitan_bars": neapolitan,
        "answer_bars": answers,
        "picardy_bars": [row["number"] for row in last_four],
        "silent_lead_bars": silent,
        "melody_by_bar": {row["number"]: [entry[0] for entry in row["melody"]] for row in rows},
        "checks": checks,
        "passed": sum(1 for c in checks if c["pass"]),
        "failed": sum(1 for c in checks if not c["pass"]),
    }
    directory = os.path.dirname(os.path.abspath(args.json))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(args.json, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")

    for entry in checks:
        print("%s %-52s %s" % ("PASS" if entry["pass"] else "FAIL", entry["check"], entry["detail"]))
    print("%d passed, %d failed, loop %.1f s at %g bpm over %d bars of %s"
          % (report["passed"], report["failed"], report["loop_seconds"],
             report["bpm"], report["bars"], report["time"]))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
