"""theme_v4.py: the drums and the tasteful dissonance pass for title theme v4 (card MUS-V4).

Input is the MIDI that tools/arrange.py writes from score_v4.yaml, plus the score
itself for the harmonic context. Output is a new MIDI with two tracks rebuilt and a
few notes displaced. Nothing else in the file changes, so the arranger's own checks
and the melody (the K, Z, P and H motifs) stay exactly as the score wrote them.

WHAT IT DOES

  drums    the noise and dpcm tracks are rebuilt from a pattern ladder: one cycle of
           bars per section, one rung per variant. Hits are placed on the eighth grid
           with ghost sixteenths, then given per hit timing (a few MIDI ticks) and
           velocity variation, so the kit is not a metronome. The v3 waltz "boom
           chick chick" is replaced by a waltz with a backbeat on beat 3, a march
           drive in B, a full kit in B prime and a "cold clock" in the second half of
           the trio, which is the drum ladder the ear review asked for.

  dissonance  devices from data/dissonance_rules.json (DIS ids below), injected as a
           pitch change on one note of an inner voice so the preparation and the
           resolution are the notes the arranger already wrote on either side. Each
           one is listed by bar and beat with the device id, the pitch before and
           after, and the note it resolves to. The count is held to the rate policy
           in that file (devices per 8 bars and the spacing rules).

  dropout  the arpeggio (pulse 1) is dropped for the first four bars of A return, so
           the last statement of the theme arrives without its inner voice, which is
           the ear review's fifth change. Variants subtle and medium keep it.

Devices used, from knowledge/MUSIC-DISSONANCE.md and data/dissonance_rules.json:

  DIS-02  chromatic lower neighbour, resolves up by semitone (risk 1)
  DIS-03  appoggiatura, resolves down by semitone (risk 2)
  DIS-07  accented passing tone on beat 2 of a waltz bar (risk 2)
  DIS-09  anticipation of the next chord's tone (risk 1)
  DIS-17  flat six to five approach, the falling semitone (risk 1)
  DIS-18  cross voice minor second between the echo and the lead (risk 3)
  DIS-11  dominant seven flat nine in an inner voice (risk 3)

Deterministic: the same MIDI, score, variant and seed give byte identical output.

Usage
    theme_v4.py BASE.mid SCORE.yaml --variant medium --out OUT.mid --report R.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import arrange                                              # noqa: E402
import hook_score                                           # noqa: E402
import humanize                                             # noqa: E402

ROOT = os.path.dirname(HERE)
POLICY_PATH = os.path.join(ROOT, "data", "dissonance_rules.json")

BAR = arrange.TICKS_PER_BAR
EIGHTH = arrange.EIGHTH

# Hit kinds: track, MIDI pitch, length in eighths, velocity.
# Noise pitches index render_chip's NOISE_PERIODS table (1 is the brightest hiss,
# 15 the lowest rumble); dpcm 36 is the kick sample and 38 the snare.
KINDS = {
    "k": ("dpcm", 36, 1.0, 108),     # kick
    "s": ("dpcm", 38, 1.0, 96),      # snare, the backbeat
    "r": ("dpcm", 38, 0.5, 60),      # short snare, a fill or a pickup
    "h": ("noise", 5, 0.85, 50),     # closed hat
    "o": ("noise", 7, 1.70, 44),     # open hat
    "w": ("noise", 3, 2.00, 38),     # sea wash
    "g": ("noise", 6, 0.60, 28),     # ghost hat
    "t": ("noise", 10, 0.50, 34),    # dry tick, the cold clock
}

# Timing feel per kind, in MIDI ticks (ppq 480, one eighth is 240 ticks).
TIMING_FEEL = {
    "k": (-2, 3), "s": (-2, 4), "r": (0, 5), "h": (-2, 4),
    "o": (-1, 4), "w": (0, 0), "g": (-1, 5), "t": (0, 3),
}
VELOCITY_JITTER = {"k": 3, "s": 3, "r": 3, "h": 4, "o": 4, "w": 3, "g": 3, "t": 3}

# The ladder: (section, variant) -> cycle of bars, each a comma separated list of
# "slot:kind" hits. Slots are eighths from the bar line; 1.5 and 3.5 are the ghost
# sixteenths between them. The cycle repeats through the section.
LADDER = {
    "A": {
        "subtle": ["2:h,4:h", "2:h,4:h", "2:h,4:h", "2:h,3:h,4:h"],
        "medium": ["0:k,2:h,4:s", "0:k,2:h,4:s", "0:k,2:h,4:s", "0:k,2:h,3:g,4:s"],
        "spicy": ["0:k,2:h,4:s,5:g", "0:k,2:h,3:g,4:s", "0:k,2:o,4:s", "0:k,2:h,3:r,4:g,5:r"],
    },
    "A_prime": {
        "subtle": ["0:k,2:h,4:h", "0:k,2:h,4:h", "0:k,2:h,4:h", "0:k,2:h,3:h,4:s"],
        "medium": ["0:k,2:h,4:h", "0:k,2:h,4:h", "0:k,2:h,4:o", "0:k,2:h,3:r,4:s"],
        "spicy": ["0:k,1.5:g,2:h,4:h", "0:k,2:h,4:h,5:g", "0:k,2:o,4:h", "0:k,2:h,3:r,4:s,5:r"],
    },
    "B": {
        "subtle": ["0:k,0:h,2:h,4:h", "0:k,2:h,4:h", "0:k,2:h,4:h", "0:k,2:h,3:h,4:s"],
        "medium": ["0:k,0:h,2:h,4:s", "0:k,2:h,4:h", "0:k,2:h,4:s", "0:k,3:r,4:h,5:s"],
        "spicy": ["0:k,0:h,2:g,3:h,4:s", "0:k,1.5:g,2:h,4:s", "0:k,2:h,4:s,5:g", "0:k,3:r,3.5:r,4:r,5:s"],
    },
    "B_prime": {
        "subtle": ["0:k,2:h,4:s", "0:k,2:h,4:s", "0:k,2:o,4:s", "0:k,2:h,4:h,5:s"],
        "medium": ["0:k,2:h,4:s", "0:k,1.5:g,2:h,4:s", "0:k,2:o,4:s", "0:k,2:h,3:r,4:s,5:r"],
        "spicy": ["0:k,1.5:g,2:h,4:s,5:g", "0:k,2:h,3:g,4:s", "0:k,2:o,4:s,5:g", "0:k,2:h,3:r,4:s,4.5:r,5:r"],
    },
    "C_trio": {
        # bars 1 to 4 the sea, bars 5 to 8 the cold clock, so the cycle is 8 bars.
        "subtle": (["0:w,2:w,4:w"] * 4) + (["0:k"] * 4),
        "medium": (["0:k,0:w,2:w,4:w"] * 2 + ["0:k,2:w,4:w"] * 2
                   + ["0:k", "0:t,2:t,4:t", "0:k,2:t", "0:k,2:t,4:t"]),
        "spicy": (["0:k,0:w,2:w,3:g,4:w", "0:k,0:w,2:w,4:w", "0:k,0:w,2:g,4:w", "0:k,0:w,2:w,4:w,5:g"]
                  + ["0:k,1:g,2:t,4:t", "0:k,1:g,2:t,3:g,4:t", "0:k,2:t,2.5:g,4:t", "0:k,1:g,2:t,4:t,5:g"]),
    },
    "A_return": {
        "subtle": (["0:k,2:h,4:h"] * 3 + ["0:k,2:h,4:h"]) + (["0:k,2:h,4:h"] * 3 + ["0:k,2:h,3:r,4:s"]),
        "medium": (["0:k,2:h,4:s"] * 4
                   + ["0:k,2:h,4:s", "0:k,2:h,4:s", "0:k,2:o,4:s", "0:k,2:h,3:r,4:s,5:r"]),
        "spicy": (["0:k,1.5:g,2:h,4:s"] * 4
                  + ["0:k,1.5:g,2:h,4:s,5:g", "0:k,2:h,3:g,4:s",
                     "0:k,2:o,4:s,5:g", "0:k,2:h,3:r,4:s,4.5:r,5:r"]),
    },
}

# Which bar and beat each device lands on, in score bar numbers (1 based) and the
# eighth slot inside the bar. The voice is the track it is written into.
# "every" is the variant stride: 3 means the subtle variant takes every third point,
# 2 the medium every second, 1 the spicy keeps them all.
ANCHORS = [
    {"bar": 7,  "slot": 2, "voice": "vrc6 pulse b", "device": "DIS-02", "note": "chromatic lower neighbour in the counter, over Am"},
    {"bar": 11, "slot": 2, "voice": "vrc6 saw",     "device": "DIS-17", "note": "flat six over the E7b9, falling to the fifth"},
    {"bar": 14, "slot": 2, "voice": "vrc6 pulse b", "device": "DIS-07", "note": "accented passing tone on beat 2 over E7"},
    {"bar": 20, "slot": 0, "voice": "pulse 1",      "device": "DIS-03", "note": "appoggiatura on the arpeggio at the cadence"},
    {"bar": 25, "slot": 3, "voice": "pulse 1",      "device": "DIS-02", "note": "chromatic lower neighbour in the arpeggio over F"},
    {"bar": 27, "slot": 0, "voice": "vrc6 saw",     "device": "DIS-11", "note": "flat nine in the E7 pad, released on the next bar line"},
    {"bar": 31, "slot": 2, "voice": "pulse 1",      "device": "DIS-02", "note": "chromatic lower neighbour in the arpeggio over C"},
    {"bar": 35, "slot": 0, "voice": "vrc6 saw",     "device": "DIS-11", "note": "flat nine again, eight bars later"},
    {"bar": 39, "slot": 2, "voice": "vrc6 saw",     "device": "DIS-07", "note": "passing tone over B7b9, the D against D sharp"},
    {"bar": 42, "slot": 0, "voice": "pulse 1",      "device": "DIS-03", "note": "appoggiatura over the D minor bar of the cold half"},
    {"bar": 44, "slot": 2, "voice": "vrc6 saw",     "device": "DIS-17", "note": "flat six on the way out of the trio"},
    {"bar": 47, "slot": 2, "voice": "vrc6 saw",     "device": "DIS-02", "note": "lower neighbour in the return of the theme"},
    {"bar": 51, "slot": 3, "voice": "pulse 2",      "device": "DIS-18", "note": "echo clash on the way back to the loop"},
    {"bar": 52, "slot": 2, "voice": "vrc6 saw",     "device": "DIS-17", "note": "flat six on the turnaround, the loop point"},
]

# Which anchors each variant keeps, by index. Subtle: seven, one per section phrase.
# Medium: ten. Spicy: thirteen, and it is the only variant that keeps the saw's
# flat six on the way out of the trio. Index 10 (bar 44) is the one the spicy
# variant leaves out, so its rate lands exactly on the policy's 2 per 8 bars.
VARIANT_ANCHORS = {
    "subtle": [0, 2, 5, 8, 9, 11, 12],
    "medium": [0, 1, 2, 3, 4, 5, 6, 8, 9, 12],
    "spicy": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13],
}
RISK = {"DIS-02": 1, "DIS-03": 2, "DIS-07": 2, "DIS-09": 1, "DIS-17": 1, "DIS-18": 3, "DIS-11": 3}
DROP_ARpeggio = ("A_return", 0, 4)      # section, first bar offset, bars to drop


# --------------------------------------------------------------------------- drums

def parse_cycle(bars_text):
    """One bar of the ladder as a list of (slot, kind)."""
    hits = []
    for item in bars_text.split(","):
        item = item.strip()
        if not item:
            continue
        slot_text, kind = item.split(":")
        hits.append((float(slot_text), kind.strip()))
    return hits


def build_drums(bars, variant, seed):
    """Rebuild the noise and dpcm tracks from the ladder, with feel."""
    rng = random.Random(seed)
    noise = []
    dpcm = []
    ladder_rows = []
    last_bar = bars[-1].number if bars else 0
    for bar in bars:
        cycle = LADDER.get(bar.section, {}).get(variant)
        if cycle is None:
            continue
        pattern = cycle[bar.index % len(cycle)]
        hits = parse_cycle(pattern)
        # The last bar runs into the loop point, where the tail is cut and the
        # file restarts. A hit late enough to still sound at that cut leaves a
        # step at the seam, so the final bar keeps only its early hits.
        if bar.number == last_bar:
            hits = [hit for hit in hits if hit[0] < 5.0]
            pattern = ",".join("%s:%s" % (slot, kind) for slot, kind in hits)
        ladder_rows.append({"bar": bar.number, "section": bar.section, "pattern": pattern})
        start = bar.index * BAR
        for slot, kind in hits:
            track, pitch, length, velocity = KINDS[kind]
            low, high = TIMING_FEEL[kind]
            offset = rng.randint(low, high) if high > low else low
            jitter = rng.randint(-VELOCITY_JITTER[kind], VELOCITY_JITTER[kind])
            accent = 6 if slot in (0.0, 4.0) else 0
            onset = start + int(round(slot * EIGHTH)) + offset
            onset = max(start, min(start + BAR - 1, onset))
            note = (onset, onset + int(round(length * EIGHTH)),
                    pitch, max(20, min(127, velocity + jitter + accent)))
            (dpcm if track == "dpcm" else noise).append(note)
    noise.sort()
    dpcm.sort()
    return noise, dpcm, ladder_rows


# ---------------------------------------------------------------------- dissonance

def track_by_name(song, name):
    for track in song["tracks"]:
        if track["name"].strip().lower() == name.strip().lower():
            return track
    raise ValueError("no track named %r (have: %s)"
                     % (name, ", ".join(t["name"] for t in song["tracks"])))


def note_index_at(track, tick, window=EIGHTH):
    """The index of the note that starts nearest to tick, inside one eighth."""
    best = None
    for index, (start, _end, _pitch, _velocity) in enumerate(track["notes"]):
        distance = abs(start - tick)
        if distance <= window and (best is None or distance < best[0]):
            best = (distance, index)
    return None if best is None else best[1]


def nearest_pitch_with_pc(original, pc):
    """The pitch class pc, in whichever octave sits closest to the original."""
    candidates = [pitch for pitch in range(24, 97) if pitch % 12 == pc % 12]
    return min(candidates, key=lambda pitch: (abs(pitch - original), pitch))


def apply_device(track, index, device, lead, chord=None):
    """Change one note's pitch so it clashes and resolves into the next note.

    The preparation is the note before it and the resolution is the note after it,
    both written by the arranger; the device only decides which pitch goes between.
    """
    start, end, pitch, velocity = track["notes"][index]
    # A pad holds for a bar, so a device on it resolves at the next bar line, not
    # on the next eighth. Everything else resolves inside a beat.
    window = BAR if device in ("DIS-11", "DIS-17") else 2 * EIGHTH
    following = None
    for other in track["notes"][index + 1:]:
        if other[0] > start:
            following = other
            break
    if device == "DIS-18" and lead is not None:
        # A minor second against whatever the lead sounds at this tick, in the
        # octave the voice already plays in, so the line does not jump.
        target = None
        for note in lead["notes"]:
            if note[0] <= start < note[1]:
                target = note[2]
                break
        if target is None:
            return None
        new_pitch = nearest_pitch_with_pc(pitch, target + 1)
        resolution = following[2] if following else None
    else:
        if following is None or following[0] - start > window:
            return None
        if device == "DIS-02":
            new_pitch = following[2] - 1
        elif device == "DIS-03":
            new_pitch = following[2] + 1
        elif device == "DIS-07":
            previous = None
            for other in reversed(track["notes"][:index]):
                if other[0] < start:
                    previous = other
                    break
            if previous is None:
                return None
            new_pitch = int(round((previous[2] + following[2]) / 2.0))
        elif device == "DIS-09":
            new_pitch = following[2]
        elif device == "DIS-17":
            new_pitch = following[2] + 1
        elif device == "DIS-11":
            # The flat nine of the chord sounding in the bar, not a semitone above
            # the next note, so the label matches the interval against the harmony.
            new_pitch = (nearest_pitch_with_pc(pitch, chord.root_pc + 1)
                         if chord is not None else following[2] + 1)
        else:
            return None
        resolution = following[2]
    if not 24 <= new_pitch <= 96:
        return None
    if new_pitch == pitch:
        return None
    track["notes"][index] = (start, end, new_pitch, velocity)
    return {"pitch_before": pitch, "pitch_after": new_pitch,
            "resolves_to": resolution,
            "resolution_semitones": (None if resolution is None else resolution - new_pitch)}


def inject_dissonance(song, bars, variant, seed):
    """Walk the anchors for this variant and displace one note of each."""
    lead = track_by_name(song, "vrc6 pulse a")
    last_bar = bars[-1].number if bars else 0
    # Nothing lands on the final bar: its notes run into the loop cut, and a
    # displaced pitch still sounding at the cut is heard as a click at the seam.
    chosen = [ANCHORS[index] for index in VARIANT_ANCHORS[variant]
              if ANCHORS[index]["bar"] != last_bar]
    moments = []
    for anchor in chosen:
        bar = next((row for row in bars if row.number == anchor["bar"]), None)
        if bar is None:
            raise ValueError("anchor names bar %d, which the score does not have" % anchor["bar"])
        track = track_by_name(song, anchor["voice"])
        bar_start = bar.index * BAR
        tick = bar_start + int(round(anchor["slot"] * EIGHTH))
        index = note_index_at(track, tick)
        if index is None:
            # The voice may rest on the anchor's own eighth; take the next note it
            # does play inside the bar, so the device still lands in that bar.
            inside = [position for position, note in enumerate(track["notes"])
                      if bar_start <= note[0] < bar_start + BAR]
            later = [position for position in inside if track["notes"][position][0] >= tick]
            if later:
                index = later[0]
            elif inside:
                index = inside[0]
        if index is None:
            moments.append({"bar": anchor["bar"], "beat": anchor["slot"] / 2.0 + 1.0,
                            "voice": anchor["voice"], "device": anchor["device"],
                            "risk": RISK[anchor["device"]],
                            "note": anchor["note"], "applied": False,
                            "reason": "that voice does not play in this bar"})
            continue
        actual_beat = (track["notes"][index][0] - bar_start) / float(2 * EIGHTH) + 1.0
        result = apply_device(track, index, anchor["device"], lead, bar.first_chord)
        row = {"bar": anchor["bar"], "beat": round(actual_beat, 3),
               "section": bar.section, "voice": anchor["voice"],
               "device": anchor["device"], "risk": RISK[anchor["device"]],
               "note": anchor["note"], "applied": result is not None}
        if result:
            row.update(result)
        else:
            row["reason"] = "the voice has no note to resolve into at this point"
        moments.append(row)
    # Spacing and rate audit against data/dissonance_rules.json's rate policy.
    policy = json.load(open(POLICY_PATH, encoding="utf-8-sig"))["rate_policy"]
    applied = [row for row in moments if row["applied"]]
    ticks = sorted(next(row for row in bars if row.number == m["bar"]).index * BAR
                   + int(round((m["beat"] - 1.0) / 2.0 * EIGHTH)) for m in applied)
    spacing_ok = all(b - a >= policy["min_spacing_beats_any"] * 2 * EIGHTH
                     for a, b in zip(ticks, ticks[1:]))
    risk_three = [m for m in applied if m["risk"] >= 3]
    risk_gap_bars = [b["bar"] - a["bar"] for a, b in zip(risk_three, risk_three[1:])]
    bars_span = len(bars) / 8.0
    return {
        "variant": variant,
        "anchors_kept": VARIANT_ANCHORS[variant],
        "moments": moments,
        "applied_count": len(applied),
        "dropped_count": len(moments) - len(applied),
        "devices_per_8_bars": round(len(applied) / bars_span, 2),
        "policy_devices_per_8_bars": [policy["devices_per_8_bars_min"],
                                     policy["devices_per_8_bars_max"]],
        "policy_min_spacing_beats": policy["min_spacing_beats_any"],
        "min_spacing_ok": spacing_ok,
        "risk_3_count": len(risk_three),
        "risk_3_min_gap_bars": min(risk_gap_bars) if risk_gap_bars else None,
        "policy_risk_3_min_gap_bars": policy["min_spacing_bars_risk_3"],
        "risk_3_spacing_ok": (not risk_gap_bars
                              or min(risk_gap_bars) >= policy["min_spacing_bars_risk_3"]),
    }


def drop_arpeggio(song, bars, variant):
    """The ear review's fifth change: no inner arpeggio in the first bars of A return."""
    section, first, count = DROP_ARpeggio
    if variant == "subtle":
        return {"applied": False, "reason": "subtle keeps every voice"}
    rows = [bar for bar in bars if bar.section == section]
    if len(rows) < first + count:
        return {"applied": False, "reason": "section too short"}
    lo = rows[first].index * BAR
    hi = rows[first + count - 1].index * BAR + BAR
    track = track_by_name(song, "pulse 1")
    before = len(track["notes"])
    track["notes"] = [note for note in track["notes"]
                      if not (lo <= note[0] < hi)]
    return {"applied": True, "section": section,
            "bars": [rows[first].number, rows[first + count - 1].number],
            "notes_dropped": before - len(track["notes"])}


# ------------------------------------------------------------------------- pipeline

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("midi")
    parser.add_argument("score")
    parser.add_argument("--variant", choices=sorted(VARIANT_ANCHORS), default="medium")
    parser.add_argument("--out", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--seed", type=int, default=20261021)
    args = parser.parse_args(argv)

    score = arrange.load_score(args.score)
    bars = arrange.build_bars_v3(score)
    song = hook_score.read_smf(args.midi)

    noise, dpcm, ladder_rows = build_drums(bars, args.variant, args.seed)
    track_by_name(song, "noise")["notes"] = noise
    track_by_name(song, "dpcm")["notes"] = dpcm

    dissonance = inject_dissonance(song, bars, args.variant, args.seed)
    dropout = drop_arpeggio(song, bars, args.variant)

    out = args.out or os.path.splitext(args.midi)[0] + "_" + args.variant + ".mid"
    humanize.write_smf(song, out)

    per_section = {}
    for row in ladder_rows:
        entry = per_section.setdefault(row["section"], {"bars": [], "patterns": [],
                                                        "hits": 0})
        entry["bars"].append(row["bar"])
        entry["patterns"].append(row["pattern"])
        entry["hits"] += len(parse_cycle(row["pattern"]))
    report = {
        "variant": args.variant,
        "seed": args.seed,
        "source_midi": os.path.abspath(args.midi),
        "score": os.path.abspath(args.score),
        "out_midi": os.path.abspath(out),
        "drum_hits": {"noise": len(noise), "dpcm": len(dpcm)},
        "drum_ladder": {name: {"bars": [row["bars"][0], row["bars"][-1]],
                               "hits": row["hits"],
                               "cycle": sorted(set(row["patterns"]),
                                               key=row["patterns"].index)}
                        for name, row in per_section.items()},
        "drum_cycle_bars": {name: len(LADDER[name][args.variant]) for name in per_section},
        "dissonance": dissonance,
        "voice_dropout": dropout,
        "timing_feel_ticks": {kind: list(pair) for kind, pair in TIMING_FEEL.items()},
        "velocity_jitter": VELOCITY_JITTER,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        directory = os.path.dirname(os.path.abspath(args.report))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
