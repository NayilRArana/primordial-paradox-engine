"""gen_drum_patterns.py: build data/drum_patterns.json from the hand written library.

Sources of the rules in this file, all read on 2026-10-21:

  DR-S01  NESdev APU Noise        full page
  DR-S02  NESdev APU DMC          full page
  DR-S03  NESdev APU Envelope     full page
  DR-S04  ripples-music, 8 bit drums without a sample pack   search excerpt
  DR-S05  Soundbrenner, Hemiola   search excerpt
  DR-S06  Music Stack Exchange, 2/2 imposed in 3/4            search excerpt
  DR-S07  musicproductionwiki, recreate the chiptune sound    search excerpt
  DR-S08  tracks.jfound.net, chiptune in the browser          search excerpt
  DR-S09  Frontiers in Psychology 5:1257, hemiola metre switching   search excerpt
  DR-S10  alexanderbrandon.net, 8 bit music practical guide   search excerpt
  DR-S11  tools/render_chip.py (this repository)              read, internal

Nothing here transcribes a copyrighted pattern. The grids are written for this
project from the technique in the sources; the control case WZ-01 and RCK-16 are
the plain patterns the ear review complained about, kept so the arranger can see
what to avoid.

Usage:
    gen_drum_patterns.py            write data/drum_patterns.json
    gen_drum_patterns.py --check    build in memory and run the checks only
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _drum_dsl import FEELS, SUBDIVISION, expand_pattern, expand_step_hits  # noqa: E402
from _drum_fills import FILLS  # noqa: E402
from _drum_feels import BAROQUE, BATTLE, BOSS, CALM, MARCH, METAL, ROCK  # noqa: E402
from _drum_waltz import WALTZ_3_4  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "data", "drum_patterns.json")

SOURCES = [
    {"id": "DR-S01", "title": "NESdev Wiki, APU Noise",
     "url": "https://www.nesdev.org/wiki/APU_Noise", "read": "2026-10-21",
     "depth": "full page",
     "claim": "The noise channel has 16 timer periods, from 4 CPU cycles ($0) to 4068 ($F) NTSC. The mode flag picks feedback bit 6 (a 93 step or 31 step buzzy sequence) instead of bit 1 (the 32767 step white sequence). The period table gives the repeat rate for each value, so period 0 is a 4811 Hz hiss and period F is a 4.7 Hz flutter."},
    {"id": "DR-S02", "title": "NESdev Wiki, APU DMC",
     "url": "https://www.nesdev.org/wiki/APU_DMC", "read": "2026-10-21",
     "depth": "full page",
     "claim": "The DMC plays 1 bit delta samples at 16 playback rates ($4010 low nibble), 4181 Hz at $0 up to 33143 Hz at $F. A one byte loop gives a pitched buzz, a 17 byte loop gives mid pitches, a 33 byte loop gives very low pitches, which is how a short sample becomes a drum."},
    {"id": "DR-S03", "title": "NESdev Wiki, APU Envelope",
     "url": "https://www.nesdev.org/wiki/APU_Envelope", "read": "2026-10-21",
     "depth": "full page",
     "claim": "Every channel has a constant volume mode with 16 levels and a decaying envelope with 16 divider periods plus a loop flag. Volume is close to linear, so a velocity ramp from the tracker reads as a smooth crescendo."},
    {"id": "DR-S04", "title": "Ripples Music, How to make 8 bit drums without a sample pack",
     "url": "https://ripples-music.com/blog/how-to-make-8-bit-drums", "read": "2026-10-21",
     "depth": "search excerpt",
     "claim": "A chip kit is noise with a fast envelope for hats and snares plus a fast falling tone for kicks and toms. Closed hat decay is 20 to 40 ms, open hat 150 to 250 ms, snare body 120 to 180 ms, kick pitch fall about 30 ms. Varying the decay rather than the volume is the expressive control, and the NES had one noise channel plus whatever the triangle was not using."},
    {"id": "DR-S05", "title": "Soundbrenner, Hemiola",
     "url": "https://soundbrenner.com/blogs/articles/hemiola", "read": "2026-10-21",
     "depth": "search excerpt",
     "claim": "Six equal subdivisions can be heard as two groups of three or three groups of two. In 3/4 a hemiola stretches across two bars, so the accents fall every two quarter notes and there are three larger pulses in the space of two bars."},
    {"id": "DR-S06", "title": "Music Stack Exchange, What is it called when 2/2 is imposed in 3/4",
     "url": "https://music.stackexchange.com/questions/82690/what-is-it-called-when-2-2-is-imposed-in-3-4", "read": "2026-10-21",
     "depth": "search excerpt",
     "claim": "A hemiola needs the metre of three established first, then the pattern of two set against it; a two against three that is never anchored sounds like a metre change instead of a hemiola."},
    {"id": "DR-S07", "title": "Music Production Wiki, How to recreate the chiptune sound",
     "url": "https://musicproductionwiki.com/articles/how-to-recreate-the-chiptune-sound", "read": "2026-10-21",
     "depth": "search excerpt",
     "claim": "The noise channel offers sixteen preset frequencies and its own volume envelope. A fast attack and instant decay is a hi hat, a longer decay at a lower noise pitch is a snare, and the short mode gives the tonal metallic buzz. The DMC let later composers stream real drum hits, which is why late NES kits are punchier than early ones."},
    {"id": "DR-S08", "title": "jfound, How to make chiptune music in your browser",
     "url": "https://tracks.jfound.net/blog/make-chiptune-music-browser", "read": "2026-10-21",
     "depth": "search excerpt",
     "claim": "A 16 step grid with kick on 1 and 9, a short noise hit on 5 and 13 for the snare, and hats for constant motion is the canonical starting groove, and a single noise channel can only hold one sound at a time, so busy layered programming breaks the illusion."},
    {"id": "DR-S09", "title": "Frontiers in Psychology 5:1257, Neural correlates of intentional switching from ternary to binary meter in a musical hemiola pattern",
     "url": "https://frontiersin.org/articles/10.3389/fpsyg.2014.01257/full", "read": "2026-10-21",
     "depth": "search excerpt",
     "claim": "Accent strength at each pulse position is modelled for binary (march), ternary (waltz) and hemiola patterns. Downbeats carry several coinciding metric layers and upbeats only one, and in a hemiola the positions where three layers coincide are the strongest and act as the pivot for a metre switch."},
    {"id": "DR-S10", "title": "Alexander Brandon, 8 bit music: a practical guide",
     "url": "https://alexanderbrandon.net/blog/8-bit-music-chiptune-guide", "read": "2026-10-21",
     "depth": "search excerpt",
     "claim": "Program the noise channel as drums: short bursts are hi hats, longer ones are snares, and pitch and length are the only controls. Percussion carries the groove in chiptune because there is nothing else to carry it."},
    {"id": "DR-S11", "title": "This repository, tools/render_chip.py",
     "url": "tools/render_chip.py", "read": "2026-10-21",
     "depth": "full file",
     "claim": "The project renderer maps a noise note to period index pitch - 1 clamped to 0..15, plays the short mode when CC12 has bit 0 set, renders DMC kick on MIDI note 36 and DMC snare on note 38, and applies a per note linear decay. So a noise period p is written as MIDI note p + 1 and a short mode hit needs CC12 = 1 at that note."},
]

FEEL_SPECS = {
    "waltz": {
        "meters": ["3/4", "6/8"],
        "tempo": {"min": 72, "max": 142, "default": 104},
        "channel_budget": "noise plus DMC; the triangle is usually busy with the bass in 3/4",
        "use": ["title", "town", "ending", "memory"],
        "rule": "The waltz tread is one bar of three; the drum writing lives in which of the three beats carries weight, not in how many hits there are.",
    },
    "march": {
        "meters": ["4/4", "6/8"],
        "tempo": {"min": 92, "max": 134, "default": 112},
        "channel_budget": "DMC kick and snare, noise for ruffs",
        "use": ["field", "overworld", "boss_approach"],
        "rule": "A march is a snare part first and a kit second: the side drum states the rudiments and the bass drum marks the floor.",
    },
    "rock": {
        "meters": ["4/4"],
        "tempo": {"min": 100, "max": 148, "default": 124},
        "channel_budget": "DMC kick, DMC snare, noise hat",
        "use": ["town", "battle", "chase"],
        "rule": "Backbeat on 2 and 4, eighth or sixteenth hat, and one displaced kick per bar. The displaced kick is what separates rock from four on the floor.",
    },
    "metal": {
        "meters": ["4/4", "6/8"],
        "tempo": {"min": 140, "max": 224, "default": 176},
        "channel_budget": "DMC kick as a wall, DMC snare as the backbeat, noise hat",
        "use": ["battle", "boss"],
        "rule": "The kick is the riff. Any bar where the kick stops is a bar the guitar has to carry alone, so stop it deliberately and never by accident.",
    },
    "baroque": {
        "meters": ["3/4", "4/4", "6/8"],
        "tempo": {"min": 66, "max": 160, "default": 96},
        "channel_budget": "DMC timpani, noise only as a shadow",
        "use": ["town", "castle", "ending", "memory"],
        "rule": "Accents only. A baroque texture puts the drums on the metre and the continuo carries the motion, so a rock hat pattern destroys the style instantly.",
    },
    "boss": {
        "meters": ["4/4", "6/8"],
        "tempo": {"min": 76, "max": 128, "default": 100},
        "channel_budget": "DMC kick low rate, DMC snare, noise tom",
        "use": ["boss", "boss_phase_2"],
        "rule": "Asymmetry and space. The boss groove avoids a repeating two bar cell inside one bar, because the player should not be able to predict the next hit.",
    },
    "calm": {
        "meters": ["4/4", "6/8", "3/4"],
        "tempo": {"min": 60, "max": 96, "default": 76},
        "channel_budget": "noise at high period, one soft DMC kick",
        "use": ["memory", "town_night", "sad"],
        "rule": "Levels at 2 or 3 and periods at 7 or higher. Calm is a level and period decision, not a rhythm decision.",
    },
    "battle": {
        "meters": ["4/4", "6/8"],
        "tempo": {"min": 144, "max": 196, "default": 168},
        "channel_budget": "DMC kick and snare, noise hat; the pulse channels belong to the lead",
        "use": ["battle", "chase"],
        "rule": "The drums hold the tempo and nothing else, because the lead is doing the work. Every battle pattern must survive being played under a lead at sixteenth density.",
    },
}

INSTRUMENTS = {
    "noise": {
        "chip": "2A03 noise channel ($400C volume, $400E period and mode, $400F length)",
        "period_range": [0, 15],
        "period_usage": {
            "0-2": "closed hat, tick, brightest hiss (4811 to 1202 Hz repeat)",
            "3-5": "open hat, rim, short snare top",
            "6-8": "snare body, brush",
            "9-11": "tom, low snare, dark brush",
            "12-13": "floor tom, crash rumble",
            "14-15": "sub thump, cymbal wash, longest decay",
        },
        "loop_mode": {
            "long": "32767 step white noise, the normal drum and hat sound",
            "short": "93 or 31 step metallic buzz, for cymbals, robots and ghost tails",
        },
        "renderer_mapping": "period p -> MIDI note p + 1; loop short -> CC12 = 1 on that note; note length is the decay",
    },
    "dpcm_kick": {
        "chip": "DMC ($4010 rate, $4011 direct load, $4012 address, $4013 length)",
        "rate_range": [0, 15],
        "rate_usage": {
            "9-10": "low kick, timpani",
            "11": "standard kick",
            "12": "high kick, tom",
            "13-14": "snare, clap tail",
        },
        "renderer_mapping": "MIDI note 36, velocity is the accent",
    },
    "dpcm_snare": {
        "chip": "DMC, a 17 to 33 byte noise loop",
        "rate_range": [0, 15],
        "rate_usage": {"12": "low snare", "13": "standard snare", "14": "bright snare"},
        "renderer_mapping": "MIDI note 38, velocity is the accent",
    },
}

WALTZ_RULES = [
    {"id": "WZ-R1", "rule": "Never run a waltz section on WZ-01 alone. The ear review of theme v3 scored drums 4 of 10 for exactly that, so WZ-01 is a control case here, not a groove.",
     "sources": ["DR-S10"]},
    {"id": "WZ-R2", "rule": "Change one layer at a time: the kick position in bar 1, the ghost notes in bar 2, the snare weight in bar 3, and a fill in bar 4. Two layers moving in the same bar sounds like a different tune.",
     "sources": ["DR-S10", "DR-S08"]},
    {"id": "WZ-R3", "rule": "Establish three before playing two. A hemiola only reads when the listener has already heard a bar or two of plain waltz, so put WZ-02 and WZ-03 no earlier than the third bar of the section.",
     "sources": ["DR-S06", "DR-S09"]},
    {"id": "WZ-R4", "rule": "Hemiola is a two bar device. Pair WZ-02 (accent on 1 and 3) with WZ-03 (accent on 2) and never repeat one half alone; one bar of it reads as a mistake, two bars read as three beats against two.",
     "sources": ["DR-S05", "DR-S09"]},
    {"id": "WZ-R5", "rule": "The second kick goes on the and of 2 (step 6 of 12) or the and of 3 (step 10), never on beat 2 itself, which is the position the ear is already expecting as the weak beat.",
     "sources": ["DR-S09"]},
    {"id": "WZ-R6", "rule": "Ghost notes stay at level 2 or 3 (velocity 28 to 42) and use a period of 5 to 7. A ghost at level 4 or louder stops being a ghost and becomes a second snare part.",
     "sources": ["DR-S01", "DR-S03"]},
    {"id": "WZ-R7", "rule": "One bar in every eight drops the kick entirely (WZ-28 or WZ-35). The silence costs no channel and it is the cheapest way to make the next bar sound composed.",
     "sources": ["DR-S10"]},
    {"id": "WZ-R8", "rule": "A crash is a long note, not a loud one: period 12 to 14, level 7 to 8, held for a beat or more. Short hits at period 14 sound like a cough.",
     "sources": ["DR-S05", "DR-S01"]},
    {"id": "WZ-R9", "rule": "In 6/8 the snare belongs inside the big beat (steps 2, 3, 8, 9 of 12), not on it, because the dotted quarter already carries the accent.",
     "sources": ["DR-S09"]},
    {"id": "WZ-R10", "rule": "Keep the level map stable inside a section: if the snare is level 9 in bar 1, it stays 9 unless the phrase is building. Changing levels at random is what the ear review heard as a rigid grid.",
     "sources": ["DR-S04"]},
    {"id": "WZ-R11", "rule": "The bar before a section change takes a fill from the library, and the fill must end on or just before the downbeat of the new section. A fill that stops two steps early leaves a hole the new section has to fill.",
     "sources": ["DR-S08"]},
    {"id": "WZ-R12", "rule": "Cut time in 3/4 (WZ-25 to WZ-27) is for a waltz that should feel slow without slowing down. Use it for one four bar stretch, then return to a three feel, or the metre stops reading as a waltz at all.",
     "sources": ["DR-S06"]},
]

VARIATION_LADDER = {
    "rungs": [
        {"rung": 0, "name": "plain", "what": "the section's home pattern, unmodified",
         "example": "WZ-01 in 3/4, RCK-01 in 4/4 rock", "channels_added": 0},
        {"rung": 1, "name": "add ghost note", "what": "one soft hit at level 2 to 3 in an empty step",
         "example": "WZ-10, WZ-11, MAR-14", "channels_added": 0},
        {"rung": 2, "name": "displace one accent", "what": "move the second kick to the and of 2 or the and of 3",
         "example": "WZ-06, WZ-07, RCK-06", "channels_added": 0},
        {"rung": 3, "name": "add fill", "what": "the last beat or two beats of the bar becomes a fill from the library",
         "example": "FLR-02 in 4/4, FLX-03 in 3/4", "channels_added": 0},
        {"rung": 4, "name": "drop out the kick for one bar", "what": "no DMC kick for a whole bar; the noise keeps the time",
         "example": "WZ-28, MAR-09, BAT-09", "channels_added": -1},
        {"rung": 5, "name": "crash on the new downbeat", "what": "a long low noise hit on the first beat of the new section only",
         "example": "FLC-01, FLC-05, RCK-09", "channels_added": 0},
    ],
    "four_bar_cycle": {
        "bar_1": "rung 0",
        "bar_2": "rung 1",
        "bar_3": "rung 0",
        "bar_4": "rung 3 with a one beat fill on the last beat",
        "note": "The four bar cycle is the default. It changes the bar the listener remembers and leaves the home pattern in place for two thirds of the phrase.",
    },
    "eight_bar_cycle": {
        "bar_1": "rung 0",
        "bar_2": "rung 1",
        "bar_3": "rung 0",
        "bar_4": "rung 3 with a one beat fill",
        "bar_5": "rung 2, displaced accent",
        "bar_6": "rung 1 plus a period sweep on the hat",
        "bar_7": "rung 4, kick drops out",
        "bar_8": "rung 3 with a two beat fill, ending the fill on the last step",
        "note": "The eight bar cycle adds the two devices a four bar phrase cannot hold: the displaced accent and the kick drop out. The last bar carries the bigger fill because eight bars is where a listener expects a seam.",
    },
    "sixteen_bar_cycle": {
        "what": "two eight bar cycles, the second one starting with the crash rung and the section's other home pattern",
        "note": "The crash marks the top of the sixteen, so the phrase has a landmark without the drums getting busier.",
    },
    "hard_rules": [
        "Never climb two rungs in the same bar.",
        "Never use rung 3 on two consecutive bars.",
        "Rung 5 happens once per section, on the first bar only.",
        "A section shorter than four bars gets rungs 0 and 3 and nothing else.",
    ],
}

TWO_BAR_HEMIOLA_PAIRS = [
    {"pair": ["WZ-02", "WZ-03"], "effect": "three beats of 2/4 across two bars of 3/4", "bars": "any even bar pair after bar 3"},
    {"pair": ["WZ-02", "WZ-24"], "effect": "hemiola that resolves into a baroque cadence", "bars": "the two bars before a section change"},
    {"pair": ["WZ-31", "WZ-30"], "effect": "6/8 heard as 3/4 then back to compound", "bars": "inside a 6/8 section, never at its start"},
]


def build() -> dict:
    patterns = WALTZ_3_4 + MARCH + ROCK + METAL + BAROQUE + BOSS + CALM + BATTLE
    seen = set()
    for p in patterns:
        if p.id in seen:
            raise SystemExit("duplicate pattern id %s" % p.id)
        seen.add(p.id)
    expanded = [expand_pattern(p, sources=_pattern_sources(p)) for p in patterns]
    fills = [expand_fill(f) for f in FILLS]
    waltz_ids = [p["id"] for p in expanded if p["feel"] == "waltz"]
    waltz_34 = [p["id"] for p in expanded if p["feel"] == "waltz" and p["meter"] == "3/4"]
    waltz_68 = [p["id"] for p in expanded if p["feel"] == "waltz" and p["meter"] == "6/8"]
    plain_control = [p["id"] for p in expanded if p["feel"] == "waltz" and "plain" in p["tags"]]
    non_plain = [pid for pid in waltz_34 if pid not in plain_control]

    doc = {
        "meta": {
            "name": "Primordial Paradox drum pattern library",
            "version": "1.0",
            "written": "2026-10-21",
            "card": "MUS-DRUMS",
            "author": "research-assistant",
            "purpose": "Give the arranger a measured, sourced vocabulary of NES drum grooves and fills, with the waltz written as a family rather than one pattern, because the ear review of title theme v3 scored the drums 4 of 10 and blamed a waltz that never changed.",
            "method": "Technique read from public chip documentation and drum tutorials (DR-S01 to DR-S10), mapped onto this project's renderer (DR-S11), then written as original grids. No copyrighted pattern was copied or transcribed; the two plain control patterns are written here from the same technique as everything else.",
            "grid_legend": {
                "steps": "one bar of 16 steps in 4/4, one bar of 12 steps in 3/4, two bars of 6 eighth steps in 6/8, each step one subdivision (16th, 16th, 8th)",
                "step": "a list of hits; a step may hold a noise hit and a DMC hit together because they are separate channels",
                "hit_fields": ["instrument", "velocity", "accent", "period", "loop", "rate"],
                "velocity": "14, 28, 42, 57, 71, 85, 99, 113, 127 for authoring levels 1 to 9",
                "accent": "true when velocity is 113 or more, which is authoring level 8 or 9",
                "period": "noise timer period 0 to 15; higher is darker and slower, so a rising period across hits is a falling pitch",
                "loop": "long is white noise, short is the 93 step metallic buzz",
                "rate": "DMC playback rate index 0 to 15; higher is brighter and shorter",
            },
            "counts": {
                "patterns": len(expanded),
                "fills": len(fills),
                "waltz_patterns": len(waltz_ids),
                "waltz_3_4": len(waltz_34),
                "waltz_3_4_non_plain": len(non_plain),
                "waltz_6_8": len(waltz_68),
            },
            "statistics_dependency": "The MUS-DATA-STATS card's corpus statistics were not on disk when this file was written (no data/*stats*.json), so every rule here comes from the public sources listed below plus this project's own renderer. When the stats json lands, the counts to compare against are the accent positions and the bar lengths in this file's patterns.",
        },
        "sources": SOURCES,
        "instruments": INSTRUMENTS,
        "feels": FEEL_SPECS,
        "patterns": expanded,
        "fills": fills,
        "waltz_section": {
            "why": "The ear review at 126 bpm (assets/audio/title_theme_v3/EAR_REVIEW_126.md) scored drums 4 of 10 and blamed a waltz pattern that never changes. This section is the answer: a family of waltz grooves plus a written rule set for varying them.",
            "pattern_ids": waltz_ids,
            "pattern_ids_3_4": waltz_34,
            "plain_control_ids": plain_control,
            "non_plain_3_4_ids": non_plain,
            "pattern_ids_6_8": waltz_68,
            "two_bar_hemiola_pairs": TWO_BAR_HEMIOLA_PAIRS,
            "rules": WALTZ_RULES,
            "variation_ladder": VARIATION_LADDER,
            "arranger_reading": "Pick one home pattern per section from non_plain_3_4_ids (or pattern_ids_6_8 for a compound section), then read the variation ladder as a bar by bar script. WZ-01 stays unused except as a control.",
        },
        "fills_section": {
            "why": "Forty fills, split by technique, each tagged with where it belongs so the arranger never has to invent one at bar 8.",
            "count": len(fills),
            "by_type": _count_by(fills, "type"),
            "by_placement": _count_by_placement(fills),
            "placement_rules": [
                "phrase_end_4 means the last beat of every fourth bar; use a one beat fill, never two.",
                "phrase_end_8 means the last beat of bar 4 and the last two beats of bar 8; the two beat fill is the bar 8 one.",
                "phrase_end_16 means the last two beats of bar 16 or the last two beats before a loop point, and it is the one place a big fill is welcome.",
                "before_section_change means the last beat before the new section starts, rising into the downbeat, and it may be used at 4, 8 or 16 depending on section length.",
                "Never two fills in a row, and never a fill on the first bar of a section.",
            ],
        },
        "renderer_contract": {
            "note": "How the arranger turns a hit into events for tools/render_chip.py (DR-S11).",
            "noise": "MIDI note = period + 1, velocity = hit velocity, note length = the decay you want; for loop short send CC12 = 1 before the note.",
            "dpcm_kick": "MIDI note 36, velocity = hit velocity.",
            "dpcm_snare": "MIDI note 38, velocity = hit velocity.",
            "step_seconds": "60 / bpm / 4 for a 16th grid, 60 / bpm / 2 for the 6/8 eighth grid.",
            "one_sound_rule": "The noise channel plays one hit at a time, so two noise hits written on the same step are an authoring error unless they are the same lane's alternation (DR-S08).",
        },
    }
    return doc


def _pattern_sources(p) -> list:
    """Every pattern cites the sources its technique comes from."""
    base = {"waltz": ["DR-S05", "DR-S06", "DR-S09", "DR-S01"],
            "march": ["DR-S08", "DR-S09", "DR-S01"],
            "rock": ["DR-S08", "DR-S04", "DR-S01"],
            "metal": ["DR-S04", "DR-S07", "DR-S01"],
            "baroque": ["DR-S09", "DR-S05", "DR-S02"],
            "boss": ["DR-S09", "DR-S04", "DR-S01"],
            "calm": ["DR-S04", "DR-S07", "DR-S03"],
            "battle": ["DR-S08", "DR-S10", "DR-S01"]}[p.feel]
    out = list(base)
    if any(d.startswith("dpcm") for d in p.devices) or any(l.inst.startswith("dpcm") for l in p.lanes):
        out.append("DR-S02")
    if "short_mode" in p.tags or any(l.loop == "short" for l in p.lanes if isinstance(l.loop, str)):
        out.append("DR-S07")
    out.append("DR-S10")
    seen, ordered = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def expand_fill(f) -> dict:
    grid = [[] for _ in range(f.steps)]
    for lane in f.lanes:
        if lane.hits and lane.inst == "noise":
            if lane.period is None:
                raise SystemExit("%s: noise lane without period" % f.id)
        period_map = {}
        loop_map = {}
        rate_map = {}
        if lane.inst == "noise":
            period_map = ({s: lane.period for s, _ in lane.hits} if isinstance(lane.period, int)
                          else dict(lane.period))
            loop_map = ({s: lane.loop for s, _ in lane.hits} if isinstance(lane.loop, str)
                        else dict(lane.loop))
        elif lane.inst.startswith("dpcm"):
            rate_map = ({s: lane.rate for s, _ in lane.hits} if isinstance(lane.rate, int)
                        else dict(lane.rate))
        for step, level in lane.hits:
            if not 0 <= step < f.steps:
                raise SystemExit("%s: %s hit at step %d outside %d steps" % (f.id, lane.inst, step, f.steps))
            if not 1 <= level <= 9:
                raise SystemExit("%s: %s level %r outside 1..9" % (f.id, lane.inst, level))
            velocity = [0, 14, 28, 42, 57, 71, 85, 99, 113, 127][level]
            hit = {"instrument": lane.inst, "velocity": velocity, "accent": velocity >= 113}
            if lane.inst == "noise":
                period = period_map.get(step)
                if not isinstance(period, int) or not 0 <= period <= 15:
                    raise SystemExit("%s: period %r at step %d" % (f.id, period, step))
                hit["period"] = period
                hit["loop"] = loop_map.get(step, "long")
            elif lane.inst.startswith("dpcm"):
                rate = rate_map.get(step)
                if not isinstance(rate, int) or not 0 <= rate <= 15:
                    raise SystemExit("%s: rate %r at step %d" % (f.id, rate, step))
                hit["rate"] = rate
            grid[step].append(hit)
    for step_hits in grid:
        step_hits.sort(key=lambda h: (h["instrument"], -h["velocity"]))
    return {
        "id": f.id,
        "name": f.name,
        "type": f.type,
        "length_beats": f.beats,
        "steps_count": f.steps,
        "fits_feels": f.feels,
        "placement": f.placement,
        "note": f.note,
        "steps": grid,
    }


def _count_by(items, key):
    out = {}
    for item in items:
        out[item[key]] = out.get(item[key], 0) + 1
    return out


def _count_by_placement(fills):
    out = {}
    for f in fills:
        for place in f["placement"]:
            out[place] = out.get(place, 0) + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    doc = build()
    counts = doc["meta"]["counts"]
    print("patterns %d, fills %d, waltz %d (3/4 %d, of which plain control %d, non plain %d; 6/8 %d)"
          % (counts["patterns"], counts["fills"], counts["waltz_patterns"], counts["waltz_3_4"],
             len(doc["waltz_section"]["plain_control_ids"]), counts["waltz_3_4_non_plain"],
             counts["waltz_6_8"]))
    if args.check:
        print("check mode: nothing written")
        return 0
    text = json.dumps(doc, indent=1, ensure_ascii=True)
    for bad in ("\u2014", "\u2013"):
        if bad in text:
            raise SystemExit("long dash found in output")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.write("\n")
    print("wrote %s (%d bytes)" % (args.out, len(text)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
