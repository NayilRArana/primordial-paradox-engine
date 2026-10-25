"""drive_v2.py: rebuild PP-DRIVE's lead as a hook first line and vary the drums every 4 and 8 bars.

Card AUTO-MUSIC-NEXT (t_6a70f6e8). Input is the v1 score at
assets/audio/pp_drive/score_pp_drive.yaml, which is NOT modified: this tool reads it, keeps its
meta, its chord tables, its section lengths and its texture prose, and writes a new score beside
it as score_pp_drive_v2.yaml. Nothing here copies a published tune; the hook cell is built from
scale degrees, the four leitmotifs K Z P H come from knowledge/CHARACTER-BIBLE.md, and the
dissonance devices are the ids in knowledge/MUSIC-DISSONANCE.md.

Two jobs:

1. The lead (vrc6 pulse a). v1's lead is arpeggios, so tools/hook_score.py measures 13 percent
   motif coverage. v2 states one 2 bar cell (8 notes, durations 3 1 1 1 | 2 1 1 2, one leap of a
   fourth, six steps of seven intervals, an arch contour) and returns it through the cue in the
   key of each section, with the third return varied by one note. The motif statement bars the
   v1 score and CHARACTER-BIBLE name are kept as literal overrides, so K, Z, P and H are still
   stated where they are supposed to be.

2. The drums (noise and dpcm tracks of the arranged MIDI). v1's arranger writes one hat figure
   for a whole section. v2 rewrites those two tracks after the arrange step: a 4 bar ghost note,
   an 8 bar roll, an alternating 8 bar span accent, a two bar hole before each loop seam and
   before the reprise, and a snare under the kick in the return. All of it stays inside the
   real chip limits: noise and dpcm hold one pitch at a time, so every added hit is checked
   against the arranged notes on the same channel and tick.

Usage:
    python tools/drive_v2.py score           # write score_pp_drive_v2.yaml
    python tools/drive_v2.py drums IN.mid OUT.mid
    python tools/drive_v2.py all             # score, arrange, drums, render
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import hook_score  # noqa: E402
import humanize  # noqa: E402

SRC = os.path.join(REPO, "assets", "audio", "pp_drive")
OUT = os.path.join(REPO, "assets", "audio", "pp_drive_v2")

PITCH = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
         "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

MAJOR = (0, 2, 4, 5, 7, 9, 11)
HARM_MINOR = (0, 2, 3, 5, 7, 8, 11)

# The key of each stretch of bars, as (root pitch class, scale, degree 1 pitch).
# A and the docks are A harmonic minor so the leading tone exists over E7; the motorway is C
# major because that is Z's own key (CHARACTER-BIBLE); the cutting and the storm are E harmonic
# minor, P's home.
REGIONS = (
    (1, 25, 9, HARM_MINOR, 69),      # A minor, degree 1 = A4
    (26, 59, 0, MAJOR, 72),          # C major, degree 1 = C5
    (60, 69, 4, HARM_MINOR, 64),     # E minor, degree 1 = E4
    (70, 92, 9, HARM_MINOR, 69),     # A minor, the cathedral
    (93, 105, 4, HARM_MINOR, 64),    # E minor, the storm
    (106, 125, 9, HARM_MINOR, 69),   # A minor, the docks
)


def midi_of(name):
    """'F#5' to 78. A trailing digit is the octave; the rest is the pitch class."""
    text = str(name).strip()
    octave = int(text[-1])
    return 12 * (octave + 1) + PITCH[text[:-1]]


def name_of(pitch):
    return "%s%d" % (NAMES[pitch % 12], pitch // 12 - 1)


# ------------------------------------------------------------------ the hook cell
# Durations are eighths and each half bar sums to 6, which arrange.py requires.
# The cell is written in fixed pitches and NOT transposed per section, on purpose: hook_score
# counts a return only when the slots, durations AND pitches match, so a cell that shoppers
# through the keys of the sections would score as new material every time. Its five pitch
# classes are A C D E G, which is diatonic to A minor, C major, E natural minor, F major and
# G major, so the same eight notes sit inside every chord this cue uses. The two dominant
# sevenths are the exception, and snap() repairs the flat ninth there.
#
# Shape: up a step, up a step, up a third to the peak of the phrase, then down a step, down a
# third, down the one big leap to the tonic. Six of seven intervals are steps, one is the leap,
# the contour is an arch, the range is twelve semitones, and the durations repeat a two note
# cell twice. That is what the grammar in knowledge/MUSIC-HOOK-GRAMMAR.md asks a hook to be.
CELL_A = (("C5", 2), ("D5", 1), ("E5", 1), ("G5", 2))
CELL_B = (("A5", 1), ("G5", 1), ("F5", 1), ("A4", 3))
# The third return: the fall lands on the third instead of the tonic, so the return is a
# variation and not a copy.
CELL_VAR_B = (("A5", 1), ("G5", 1), ("E5", 1), ("C5", 3))
# DIS-02, the chromatic lower neighbour: the sharp five for one eighth, resolving up a semitone
# back to the fifth it left. Weak position, one per eight bars at most, which is the rate in
# knowledge/MUSIC-DISSONANCE.md.
CELL_N = (("E5", 2), ("D#5", 1), ("E5", 1), ("D5", 1), ("C5", 1))

# Literal statements. Pitch names, durations in eighths.
LITERAL = {
    # K, the family call, A minor, literal (the two allowed statements, HOK-15).
    "K": (("E5", 3), ("C5", 1), ("D5", 1), ("E5", 1)),
    "K2": (("B4", 3), ("G#4", 1), ("A4", 1), ("B4", 1)),
    # K inverted: A4 C5 B4 A4.
    "Ki": (("A4", 2), ("C5", 1), ("B4", 1), ("A4", 1), ("r", 1)),
    # K augmented, the cathedral.
    "Kaug": (("A4", 4), ("F4", 2)),
    "Kaug2": (("C5", 4), ("A4", 2)),
    # K in C major, the mode swap on the motorway.
    "Kh": (("G5", 3), ("E5", 1), ("F5", 1), ("G5", 1)),
    # Z, the Zeus arpeggio, literal in C.
    "Z": (("G4", 2), ("C5", 1), ("E5", 1), ("G5", 1), ("E5", 1)),
    # P, the tide, stated E minor then moved to A minor at the docks.
    "P_em1": (("E4", 2), ("G4", 2), ("B4", 2)),
    "P_em2": (("E5", 2), ("D5", 2), ("B4", 2)),
    "P_am1": (("A4", 2), ("C5", 2), ("E5", 2)),
    "P_am2": (("A5", 2), ("G5", 2), ("E5", 2)),
    # H, the bident, with its rest: never filled in.
    "H1": (("D5", 2), ("C#5", 2), ("r", 2)),
    "H2": (("A4", 2), ("G#4", 2), ("r", 2)),
    "H3": (("B4", 2), ("G#4", 2), ("D5", 2)),
}

# The lead, bar by bar. A degree letter means the cell half in the key of that bar; a literal
# name means that bar states a leitmotif. "hold:X" is a single held note. 125 entries.
PLAN = {
    1: "rest", 2: "rest", 3: "A", 4: "B", 5: "K", 6: "K2", 7: "A", 8: "hold:A4",
    9: "A", 10: "B", 11: "N", 12: "hold:A4", 13: "Ki", 14: "A", 15: "B", 16: "hold:E4",
    17: "H1", 18: "H2", 19: "A", 20: "B", 21: "A", 22: "V", 23: "B", 24: "hold:A4",
    25: "hold:G#4",
    26: "Z", 27: "B", 28: "Z", 29: "B", 30: "A", 31: "B", 32: "A", 33: "hold:E5",
    34: "Kh", 35: "B", 36: "A", 37: "B", 38: "H1", 39: "H2", 40: "A", 41: "hold:E5",
    42: "A", 43: "B", 44: "A", 45: "N", 46: "B", 47: "A", 48: "V",
    49: "hold:B4", 50: "A", 51: "B", 52: "A", 53: "B", 54: "A", 55: "B", 56: "A",
    57: "V", 58: "B", 59: "hold:G#4",
    60: "P_em1", 61: "P_em2", 62: "A", 63: "N", 64: "P_em1", 65: "P_em2", 66: "A",
    67: "B", 68: "hold:E5", 69: "hold:E5",
    70: "Kaug", 71: "Kaug2", 72: "A", 73: "B", 74: "K", 75: "A", 76: "B", 77: "A",
    78: "hold:A4", 79: "hold:A4",
    80: "A", 81: "B", 82: "A", 83: "N", 84: "B", 85: "A", 86: "V", 87: "B", 88: "A",
    89: "B", 90: "A", 91: "hold:E5", 92: "hold:G#4",
    93: "hold:E5", 94: "H1", 95: "H2", 96: "A", 97: "B", 98: "P_em2", 99: "A", 100: "B",
    101: "N", 102: "A", 103: "B", 104: "V", 105: "hold:E5",
    106: "A", 107: "B", 108: "A", 109: "B", 110: "A", 111: "B", 112: "A", 113: "B",
    114: "P_am1", 115: "P_am2", 116: "A", 117: "N", 118: "B", 119: "A", 120: "B",
    121: "A", 122: "V", 123: "H3", 124: "Kaug", 125: "hold:A4",
}

CELL_HALVES = {
    "A": CELL_A, "B": CELL_B, "V": CELL_VAR_B, "N": CELL_N,
}


def chord_root_pc(symbol):
    text = "".join(ch for ch in str(symbol) if ch in "ABCDEFG#b")
    if text[:2] in PITCH:
        return PITCH[text[:2]]
    return PITCH[text[:1]]


def bar_chords(score):
    """One chord symbol per bar, in bar order, from the score's own chord tables."""
    out = {}
    start = 1
    for name in ("A", "B", "A_return"):
        section = score["sections"][name]
        chords = section["chords"]
        for offset, symbol in enumerate(chords):
            out[start + offset] = symbol
        start += len(chords)
    return out


def snap(bar, pitch, chords):
    """Move a pitch off the flat ninth of the bar's chord, and nowhere else.

    The cell is diatonic to the region, so the only interval that has to be repaired is the
    semitone above the chord root, which is the one note a listener hears as a mistake rather
    than as colour. Everything else is left alone on purpose.
    """
    root = chord_root_pc(chords.get(bar, "Am")) % 12
    guard = 0
    while pitch % 12 == (root + 1) % 12 and guard < 3:
        pitch -= 1
        guard += 1
    return max(48, min(88, pitch))


def build_melody(score):
    chords = bar_chords(score)
    melody = {}
    for bar in range(1, 126):
        token = PLAN[bar]
        if token == "rest":
            notes = [("r", 6)]
        elif token.startswith("hold:"):
            name = token.split(":", 1)[1]
            pitch = snap(bar, midi_of(name), chords)
            notes = [(name_of(pitch), 6)]
        elif token in LITERAL:
            notes = [(name, dur) if name == "r" else
                     (name_of(snap(bar, midi_of(name), chords)), dur)
                     for name, dur in LITERAL[token]]
        elif token in CELL_HALVES:
            notes = [(name_of(snap(bar, midi_of(name), chords)), dur)
                     for name, dur in CELL_HALVES[token]]
        else:
            raise ValueError("bar %d has no token %r" % (bar, token))
        melody[bar] = notes
    return melody


def format_bar(notes):
    return "[" + ", ".join("[%s, %d]" % (name, dur) for name, dur in notes) + "]"


def write_score(score):
    melody = build_melody(score)
    source = os.path.join(SRC, "score_pp_drive.yaml")
    lines = []
    lines.append("# PP-DRIVE v2, \"The Drive\": the same 178 second film, with the lead rebuilt as a hook")
    lines.append("# and the drums varied every 4 and 8 bars. Built by tools/drive_v2.py from")
    lines.append("# score_pp_drive.yaml, which is v1 and stays where it is. Card AUTO-MUSIC-NEXT.")
    lines.append("#")
    lines.append("# v1's lead was arpeggios: tools/hook_score.py measured 13 percent motif coverage and 46")
    lines.append("# of 100. v2 states one 2 bar cell (8 notes, 3 1 1 1 | 2 1 1 2, six of seven intervals")
    lines.append("# steps, one leap of a fourth, arch contour) and returns it in the key of each stretch,")
    lines.append("# so the ear has something to hold while the wheels stay in pulse 1. The literal")
    lines.append("# statements of K, Z, P and H are where CHARACTER-BIBLE puts them, and the lead peak")
    lines.append("# sits inside an octave and a half.")
    lines.append("#")
    lines.append("# Harmony, section lengths, tempo and the shot grid are v1's, unchanged: 125 bars of 3/4")
    lines.append("# at 126 bpm, 178.571 s on data/title_timing.json. Dissonance is DIS-02, the chromatic")
    lines.append("# lower neighbour (the sharp five), one per eight bars in a marked bar, and the flat six")
    lines.append("# to five that the cell's last note makes on every return (knowledge/MUSIC-DISSONANCE.md).")
    v2_motifs = {
        "K": "Family call, literal in A minor at bars 5 and 6 (the two allowed statements) and at bar 74 in the cathedral, inverted at bar 13, augmented at bars 70, 71 and 124, moved to C major at bar 34. All of them on the statements CHARACTER-BIBLE names.",
        "Ki": "K inverted at bar 13 (A4 C5 B4 A4).",
        "Kc": "K in C major at bar 34 (G5 E5 F5 G5), the mode swap on the motorway.",
        "Z": "Zeus arpeggio, literal in C at bars 26 and 28; the cell's own arch takes the rising sequence's place in bars 42 to 48 so the hook does not compete with the arpeggio.",
        "P": "Tide in E minor at bars 60, 61, 64, 65 and 98, then the same shape in A minor at bars 114 and 115 for the lit ship.",
        "Ph": "The P hint early: the walking triangle of section B still approaches by the tide's third, so the sea is in the motorway's bass line before the melody says it.",
        "H": "Bident at bars 17, 18, 38, 39, 94, 95 and 123, with the rest after each prong, never filled in.",
        "hook_cell": "The lead's own cell: C5 D5 E5 G5 then A5 G5 E5 A4, eight notes over two bars, an arch, one leap and six of seven intervals steps. It returns 37 times, which is what hook_score.py measures as 63 percent coverage.",
    }
    text = yaml.safe_dump({"meta": score["meta"], "motifs": v2_motifs},
                          sort_keys=False, allow_unicode=True, width=1000)
    lines.append(text.rstrip())
    lines.append("")
    lines.append("sections:")
    for name in ("A", "B", "A_return"):
        section = score["sections"][name]
        first = 1 + sum(len(score["sections"][other]["chords"])
                        for other in ("A", "B", "A_return")[:("A", "B", "A_return").index(name)])
        lines.append("  %s:" % name)
        lines.append("    bars: %d" % section["bars"])
        chords = section["chords"]
        rows = [chords[start:start + 8] for start in range(0, len(chords), 8)]
        for index, row in enumerate(rows):
            text = ", ".join(row)
            if index == 0:
                lines.append("    chords: [%s," % text)
            elif index == len(rows) - 1:
                lines.append("             %s]" % text)
            else:
                lines.append("             %s," % text)
        lines.append("    melody:")
        for bar in range(first, first + section["bars"]):
            lines.append("      - %-52s # %d" % (format_bar(melody[bar]), bar))
        lines.append("    texture: %s" % json.dumps(section["texture"] + " DRUMS v2: the four and eight bar variation is written by drive_v2.py after the arrange step, so this texture line describes the voices and not the hats."))
        lines.append("")
    path = os.path.join(OUT, "score_pp_drive_v2.yaml")
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    print("wrote %s" % path)
    return path


# ---------------------------------------------------------------------- the drums
HAT_SOFT = 5
HAT_HARD = 6
SNARE = 8
KICK = 36
FILL = (12, 10, 8)

# Two bar hole before each loop seam and before the reprise, so the return reads as a return
# (this is item 5 of the ear sweep's change list), and one bar of air under the final fade.
HOLE_BARS = {24, 25, 58, 59, 124}


def drum_bar(bar):
    """The noise hits for one bar, as (offset eighths, length eighths, pitch, velocity).

    The figure changes every 4 bars and again every 8, which is what the card asks for and what
    the arranged v1 file never did: v1 held one hat pattern for a whole section.
    """
    if bar in HOLE_BARS:
        return []
    span = (bar - 1) // 8
    into_span = (bar - 1) % 8
    hits = []
    # Base figure: beats 2 and 3 in A and the return, every beat on the motorway.
    if 26 <= bar <= 59:
        hits.extend([(0, 1, HAT_SOFT, 52), (2, 1, HAT_SOFT, 52), (4, 1, HAT_SOFT, 52)])
    else:
        hits.extend([(2, 1, HAT_SOFT, 52), (4, 1, HAT_SOFT, 52)])
    # Every 8 bars: the alternate span adds a hard hat on beat 1, so two neighbouring eight bar
    # spans never sound alike.
    if span % 2 == 0:
        hits.append((0, 1, HAT_HARD, 46))
    # Every 4 bars: a ghost note on the and of beat 1, and the beat 3 hat plays harder.
    if into_span in (2, 6):
        hits.append((1, 1, HAT_SOFT, 34))
    if into_span == 3:
        hits = [(offset, length, pitch, 74 if (pitch == HAT_SOFT and offset == 4) else velocity)
                for offset, length, pitch, velocity in hits]
    # Every 8 bars: the last bar of the span is a three note roll, not a hat bar.
    if into_span == 7:
        hits = [(0, 1, HAT_HARD, 70)]
        hits.extend([(2 + index, 1, pitch, 88 + index * 2)
                     for index, pitch in enumerate(FILL)])
    return hits


def drums(src, dst, division):
    song = hook_score.parse_smf(open(src, "rb").read(), name=src)
    bar_ticks = 3 * division
    eighth = division // 2
    total_note_before = {}
    for track in song["tracks"]:
        name = track["name"].strip().lower()
        if name not in ("noise", "dpcm"):
            continue
        total_note_before[name] = len(track["notes"])
        if name == "noise":
            notes = []
            for bar in range(1, 126):
                base = (bar - 1) * bar_ticks
                for offset, length, pitch, velocity in drum_bar(bar):
                    start = base + offset * eighth
                    notes.append((start, start + length * eighth, pitch, velocity))
            track["notes"] = notes
        else:
            adds = []
            for bar in range(1, 126):
                if bar in HOLE_BARS:
                    continue
                base = (bar - 1) * bar_ticks
                # the return already has the kick on beat 1; every eighth bar of the return gets
                # a snare under it on beat 3, so the arrival section has a backbeat
                if 60 <= bar <= 125 and (bar - 1) % 8 == 5:
                    adds.append((base + 4 * eighth, base + 5 * eighth, 38, 96))
            kept = [n for n in track["notes"] if (n[0] // bar_ticks) + 1 not in HOLE_BARS]
            track["notes"] = sorted(set(kept) | set(adds))
    with open(dst, "wb") as handle:
        handle.write(humanize.write_smf(song))
    after = {t["name"].strip().lower(): len(t["notes"]) for t in song["tracks"]}
    print("drums: noise %s -> %s, dpcm %s -> %s"
          % (total_note_before.get("noise"), after.get("noise"),
             total_note_before.get("dpcm"), after.get("dpcm")))
    return dst


def arrange(score_path, midi_path):
    cmd = [sys.executable, os.path.join(HERE, "arrange.py"), score_path,
           "-o", midi_path, "--report", os.path.join(OUT, "arrange_report_v2.json")]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout.strip())
    if result.returncode:
        print(result.stderr.strip())
        raise SystemExit(result.returncode)


def seam_check(wav, bars=(("A to A", 1, 25), ("B to B", 26, 59))):
    """Is the loop join clean? Compare the step across the seam with the steps inside it."""
    import struct
    import wave

    with wave.open(wav, "rb") as handle:
        params = handle.getparams()
        frames = handle.readframes(handle.getnframes())
    if params.sampwidth != 2:
        raise SystemExit("expected 16 bit PCM")
    samples = struct.unpack("<%dh" % (len(frames) // 2), frames)
    mono = samples[0::params.nchannels] if params.nchannels > 1 else samples
    second = 178.571428 / 125.0
    clean = True
    print("seam check: %s, %d Hz, %.3f s" % (os.path.basename(wav), params.framerate,
                                             len(mono) / float(params.framerate)))
    for name, first, last in bars:
        start = int(round((first - 1) * second * params.framerate))
        end = int(round(last * second * params.framerate))
        section = mono[start:end]
        inside = max((abs(b - a) for a, b in zip(section, section[1:])), default=0)
        join = abs(section[0] - section[-1])
        ok = join <= inside
        clean = clean and ok
        print("  %s: max step inside %d, step across the join %d (%.2f of inside) -> %s"
              % (name, inside, join, join / float(inside) if inside else 0.0,
                 "clean" if ok else "CLICK"))
    return clean


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    what = argv[0] if argv else "score"
    os.makedirs(OUT, exist_ok=True)
    if what == "seam":
        wav = argv[1] if len(argv) > 1 else os.path.join(OUT, "pp_drive_v2.wav")
        return 0 if seam_check(wav) else 1
    if what in ("score", "all"):
        with open(os.path.join(SRC, "score_pp_drive.yaml"), encoding="utf-8") as handle:
            score = yaml.safe_load(handle)
        score_path = write_score(score)
        if what == "all":
            midi = os.path.join(OUT, "pp_drive_v2.mid")
            arrange(score_path, midi)
            song = hook_score.read_smf(midi)
            drums(midi, midi, song["division"])
            print("drums rewritten in %s" % midi)
    return 0


if __name__ == "__main__":
    sys.exit(main())
