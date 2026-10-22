"""check_drum_patterns.py: independent check on data/drum_patterns.json.

Reads only the JSON, not the authoring modules, so a bug in the generator cannot
hide here. Exits nonzero with a list of failures, and prints the counts the card
asks for (120 patterns, 40 fills, waltz 25 or more, every pattern has a feel and
a tempo, sources listed).

Usage:
    check_drum_patterns.py [path]
"""

from __future__ import annotations

import json
import os
import sys

DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "drum_patterns.json")
FEELS = {"waltz", "march", "rock", "metal", "baroque", "boss", "calm", "battle"}
INSTRUMENTS = {"noise", "dpcm_kick", "dpcm_snare"}
METERS = {"4/4": 16, "3/4": 12, "6/8": 6}  # 6/8 is six eighths per bar, two bars per pattern
HIT_KEYS = {"instrument", "velocity", "accent"}
PLACEMENTS = {"before_section_change", "phrase_end_4", "phrase_end_8", "phrase_end_16"}
FILL_TYPES_REQUIRED = {"noise_roll", "tom_sweep", "snare_flam", "cymbal_decay"}


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.exists(path):
        print("FAIL: %s does not exist" % path)
        return 1
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    doc = json.loads(raw)
    errors = []

    def fail(msg):
        errors.append(msg)

    for bad, name in (("\u2014", "em dash"), ("\u2013", "en dash")):
        if bad in raw:
            fail("long dash (%s) found in the file" % name)

    sources = doc.get("sources") or []
    source_ids = {s.get("id") for s in sources}
    if len(sources) < 8:
        fail("only %d sources listed, 8 or more expected" % len(sources))
    for s in sources:
        for key in ("id", "title", "url", "read", "claim"):
            if not s.get(key):
                fail("source %s missing %s" % (s.get("id"), key))

    patterns = doc.get("patterns") or []
    if len(patterns) != 120:
        fail("pattern count is %d, expected exactly 120" % len(patterns))
    ids = [p.get("id") for p in patterns]
    if len(set(ids)) != len(ids):
        fail("duplicate pattern ids")
    feels = {}
    for p in patterns:
        pid = p.get("id", "?")
        feel = p.get("feel")
        if feel not in FEELS:
            fail("%s: feel %r not in the eight allowed feels" % (pid, feel))
        feels[feel] = feels.get(feel, 0) + 1
        tempo = p.get("tempo") or {}
        try:
            tmin, tmax, tdef = int(tempo["min"]), int(tempo["max"]), int(tempo["default"])
        except (KeyError, TypeError, ValueError):
            fail("%s: tempo is not {min,max,default} integers" % pid)
            tmin = tmax = tdef = 0
        if not (40 <= tmin <= tmax <= 260):
            fail("%s: tempo %r outside 40..260 or min above max" % (pid, tempo))
        if not tmin <= tdef <= tmax:
            fail("%s: default tempo %d outside min %d and max %d" % (pid, tdef, tmin, tmax))
        meter = p.get("meter")
        if meter not in METERS:
            fail("%s: meter %r not one of 4/4, 3/4, 6/8" % (pid, meter))
            continue
        bars = p.get("bars")
        expected = METERS[meter] * bars
        if meter == "6/8" and (bars != 2 or expected != 12):
            fail("%s: 6/8 pattern must be two bars and twelve steps, got bars %r steps %r"
                 % (pid, bars, p.get("steps_count")))
        if p.get("steps_count") != expected:
            fail("%s: steps_count %r, expected %d" % (pid, p.get("steps_count"), expected))
        steps = p.get("steps") or []
        if len(steps) != expected:
            fail("%s: grid has %d steps, expected %d" % (pid, len(steps), expected))
            continue
        if not any(steps):
            fail("%s: empty grid" % pid)
        for index, hits in enumerate(steps):
            noise_here = [h for h in hits if h.get("instrument") == "noise"]
            if len(noise_here) > 1:
                fail("%s: step %d has %d noise hits, the channel plays one at a time"
                     % (pid, index, len(noise_here)))
            for h in hits:
                inst = h.get("instrument")
                if inst not in INSTRUMENTS:
                    fail("%s: step %d instrument %r" % (pid, index, inst))
                if set(h) - HIT_KEYS - {"period", "loop", "rate"}:
                    fail("%s: step %d has unknown hit fields %s" % (pid, index, sorted(set(h))))
                v = h.get("velocity")
                if not isinstance(v, int) or not 1 <= v <= 127:
                    fail("%s: step %d velocity %r" % (pid, index, v))
                if h.get("accent") is not (v >= 113):
                    fail("%s: step %d accent %r does not match velocity %r" % (pid, index, h.get("accent"), v))
                if inst == "noise":
                    per = h.get("period")
                    if not isinstance(per, int) or not 0 <= per <= 15:
                        fail("%s: step %d noise period %r" % (pid, index, per))
                    if h.get("loop") not in ("long", "short"):
                        fail("%s: step %d noise loop %r" % (pid, index, h.get("loop")))
                elif inst and inst.startswith("dpcm"):
                    rate = h.get("rate")
                    if not isinstance(rate, int) or not 0 <= rate <= 15:
                        fail("%s: step %d dpcm rate %r" % (pid, index, rate))
        for sid in p.get("sources") or []:
            if sid not in source_ids:
                fail("%s: cites unknown source %s" % (pid, sid))
        if not p.get("sources"):
            fail("%s: no sources cited" % pid)
    missing_feels = FEELS - set(feels)
    if missing_feels:
        fail("no patterns for feels: %s" % sorted(missing_feels))

    fills = doc.get("fills") or []
    if len(fills) != 40:
        fail("fill count is %d, expected exactly 40" % len(fills))
    fill_ids = [f.get("id") for f in fills]
    if len(set(fill_ids)) != len(fill_ids):
        fail("duplicate fill ids")
    fill_types, placements, beat_lengths = {}, {}, {}
    for f in fills:
        fid = f.get("id", "?")
        ftype = f.get("type")
        fill_types[ftype] = fill_types.get(ftype, 0) + 1
        beats = f.get("length_beats")
        if beats not in (1, 2):
            fail("%s: length_beats %r, expected 1 or 2" % (fid, beats))
        beat_lengths[beats] = beat_lengths.get(beats, 0) + 1
        if f.get("steps_count") != beats * 4:
            fail("%s: steps_count %r does not match %r beats" % (fid, f.get("steps_count"), beats))
        steps = f.get("steps") or []
        if len(steps) != f.get("steps_count"):
            fail("%s: grid has %d steps, expected %d" % (fid, len(steps), f.get("steps_count") or 0))
        for place in f.get("placement") or []:
            if place not in PLACEMENTS:
                fail("%s: placement %r" % (fid, place))
            placements[place] = placements.get(place, 0) + 1
        if not f.get("placement"):
            fail("%s: no placement" % fid)
        if not f.get("fits_feels"):
            fail("%s: no feels listed" % fid)
        for feel in f.get("fits_feels") or []:
            if feel not in FEELS:
                fail("%s: fits_feels has %r" % (fid, feel))
        for index, hits in enumerate(steps):
            if len([h for h in hits if h.get("instrument") == "noise"]) > 1:
                fail("%s: step %d has two noise hits" % (fid, index))
            for h in hits:
                v = h.get("velocity")
                if not isinstance(v, int) or not 1 <= v <= 127:
                    fail("%s: step %d velocity %r" % (fid, index, v))
                if h.get("instrument") == "noise":
                    per = h.get("period")
                    if not isinstance(per, int) or not 0 <= per <= 15:
                        fail("%s: step %d period %r" % (fid, index, per))
                    if h.get("loop") not in ("long", "short"):
                        fail("%s: step %d loop %r" % (fid, index, h.get("loop")))
                elif str(h.get("instrument", "")).startswith("dpcm"):
                    rate = h.get("rate")
                    if not isinstance(rate, int) or not 0 <= rate <= 15:
                        fail("%s: step %d rate %r" % (fid, index, rate))
                else:
                    fail("%s: step %d instrument %r" % (fid, index, h.get("instrument")))
    if not FILL_TYPES_REQUIRED <= set(fill_types):
        fail("fill types missing: %s" % sorted(FILL_TYPES_REQUIRED - set(fill_types)))
    if 1 not in beat_lengths or 2 not in beat_lengths:
        fail("fills must include both 1 beat and 2 beat lengths, got %s" % beat_lengths)
    if len(placements) < 4:
        fail("fills do not cover all four placements: %s" % sorted(placements))

    waltz = doc.get("waltz_section") or {}
    non_plain = waltz.get("non_plain_3_4_ids") or []
    if len(non_plain) < 25:
        fail("waltz section lists %d non plain 3/4 patterns, 25 or more expected" % len(non_plain))
    by_id = {p.get("id"): p for p in patterns}
    for pid in waltz.get("pattern_ids") or []:
        p = by_id.get(pid)
        if p is None:
            fail("waltz section names unknown pattern %s" % pid)
            continue
        if p.get("feel") != "waltz":
            fail("waltz section names %s which has feel %r" % (pid, p.get("feel")))
        if p.get("meter") == "3/4" and p.get("steps_count") != 12:
            fail("%s: 3/4 waltz is not a 12 step grid" % pid)
        if p.get("meter") == "6/8" and p.get("steps_count") != 12:
            fail("%s: 6/8 waltz is not a 12 step grid" % pid)
    for pid in non_plain:
        p = by_id.get(pid)
        if p is None:
            fail("non plain waltz names unknown pattern %s" % pid)
        elif "plain" in (p.get("tags") or []):
            fail("non plain waltz includes a pattern tagged plain: %s" % pid)
    covered = {p.get("id") for p in patterns
               if p.get("feel") == "waltz" and "plain" not in (p.get("tags") or [])}
    for technique in ("hemiola_3_2", "syncopated_kick", "ghost_note", "march_waltz",
                      "rock_waltz", "accents_only", "cut_time"):
        if not any(technique in (p.get("devices") or []) for p in patterns
                   if p.get("feel") == "waltz" and p.get("id") in covered):
            fail("waltz section has no pattern using %s" % technique)
    ladder = waltz.get("variation_ladder") or {}
    if len(ladder.get("rungs") or []) < 5:
        fail("variation ladder has fewer than 5 rungs")
    for key in ("four_bar_cycle", "eight_bar_cycle"):
        if key not in ladder:
            fail("variation ladder is missing %s" % key)
    if len(waltz.get("rules") or []) < 8:
        fail("waltz rule set has fewer than 8 rules")
    for rule in waltz.get("rules") or []:
        for sid in rule.get("sources") or []:
            if sid not in source_ids:
                fail("waltz rule %s cites unknown source %s" % (rule.get("id"), sid))

    print("patterns: %d" % len(patterns))
    print("fills: %d (types %s)" % (len(fills), dict(sorted(fill_types.items()))))
    print("feels: %s" % dict(sorted(feels.items())))
    print("waltz: %d total, %d in 3/4, %d non plain 3/4, %d in 6/8"
          % (len(waltz.get("pattern_ids") or []), len(waltz.get("pattern_ids_3_4") or []),
             len(non_plain), len(waltz.get("pattern_ids_6_8") or [])))
    print("fills by placement: %s" % dict(sorted(placements.items())))
    print("sources: %d" % len(sources))
    if errors:
        print("\nFAIL (%d problems)" % len(errors))
        for e in errors[:40]:
            print("  - %s" % e)
        return 1
    print("\nOK: every check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
