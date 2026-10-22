# Music, drums: what makes NES percussion interesting, and the rules this project uses

Card: MUS-DRUMS, 2026-10-21. Companion data: `data/drum_patterns.json` (120 patterns, 40 fills),
authoring source `tools/_drum_dsl.py`, `tools/_drum_waltz.py`, `tools/_drum_feels.py`,
`tools/_drum_fills.py`, generator `tools/gen_drum_patterns.py`, check
`tools/check_drum_patterns.py`.

Why this file exists: Nayil heard title theme v3 at 126 bpm and said the drums need to be more
interesting, and the Gemini ear review (`assets\audio\title_theme_v3\EAR_REVIEW_126.md`) scored
rhythm and drum interest 4 of 10, human feel 3 of 10, and blamed "a strict boom chick chick waltz
backing on the noise and triangle channels that never shifts". This is the study that answers it.

Ground rule followed (PLAN-V2 section 0): technique comes from public documentation and tutorials,
quoted and cited. Nothing was ripped, traced, transcribed or copied from a game. Every grid in the
json was written for this project. The two plain patterns (WZ-01, RCK-16) are control cases: they are
the sound the review complained about, kept so the arranger can see what to avoid.

---

## 1. The hardware, in one page

The 2A03 gives percussion two voices, and neither of them is a drum:

- **Noise** is a pseudo random bit generator clocked at one of sixteen rates. Period `$0` clocks the
  shift register every 4 CPU cycles (repeat rate about 4.8 kHz) and period `$F` every 4068 cycles
  (about 4.7 Hz). The period is the pitch control: a short period is a hiss, a long period is a
  rumble. The mode flag chooses which bit feeds back: long mode runs the full 32,767 step white
  sequence, short mode uses a 93 or 31 step loop that is buzzy and nearly tonal (NESdev, APU Noise).
- **The DMC** plays 1 bit delta samples, at one of sixteen playback rates, from CPU memory. A one byte
  loop is a pitched buzz, a 17 byte loop lands in the mid range, a 33 byte loop is very low
  (NESdev, APU DMC). A 17 to 33 byte noise loop at a moderate rate is the standard chip snare, and a
  low rate on a short loop is the standard kick.
- Both channels have an envelope with sixteen constant volume levels, close to linear, so a level
  ramp in the tracker reads as a smooth crescendo (NESdev, APU Envelope).

That is the whole kit: one noise voice that can be at one pitch and one length at a time, and one
sample voice. Everything that sounds like a drum kit is a decision about **which channel hits, at
which period and rate, for how long, at which level**. That is why the pattern file stores a period
and a loop mode per noise hit and a rate per DMC hit rather than an instrument name alone.

The one sound rule matters for writing: the noise channel cannot hold two sounds at once, so a
pattern that has a hat and a snare on the same step is not playable (jfound, chiptune tutorial). The
json carries this as a check: no step may hold two noise hits. A noise hit and a DMC hit on the same
step is fine, because they are different channels.

## 2. What makes chip drums interesting, as rules

1. **The decay is the drum.** Closed hat 20 to 40 ms, open hat 150 to 250 ms, snare body 120 to
   180 ms, kick with a pitch fall of about 30 ms (ripples-music). On the 2A03 the "decay" is the note
   length plus the envelope, and the amount of decay is a stronger expressive control than the volume
   (same source). So a good fill is mostly a note length decision.
2. **Pitch is a sweep, not a knob.** A tom fill is a run of noise hits whose period climbs; a falling
   pitch is a rising period. That is why `FLT-01` writes periods 6, 8, 10, 12 and `BOS-10` writes 7,
   9, 11. There is no glide on the noise channel, so the illusion is built from discrete hits 1 to 2
   steps apart.
3. **Short mode is a texture, not a trick.** The 93 step mode turns noise metallic (musicproductionwiki,
   Wikipedia-style summaries of the same behaviour in NESdev). It is the right colour for cymbals,
   robot percussion and ghost tails, and the wrong colour for a snare body (`FLR-05`, `FLC-03`, `WZ-13`).
4. **Levels carry the genre.** A calm cue is the same rhythm as a loud one with every level at 2 or 3
   (`CLM-06` versus `WZ-01`). Before adding notes, ask whether the section should simply be quieter.
5. **Space is an instrument.** Bars with three hits (`BOS-05`, `BAT-09`, `RCK-13`) read as louder than
   busy bars, and a cue that never drops out sounds like a conveyor belt, which is exactly the phrase
   the ear review used.
6. **Repetition with change is the structure of the genre** (alexanderbrandon guide): one cell, then
   one thing changed. Two things changed in the same bar reads as a new tune, not a variation.
7. **Percussion carries the groove in chiptune because nothing else can** (same guide). In a cue with
   a dense lead the drums must be simple; in a cue with a sustained pad the drums can be the event.

## 3. The waltz problem, and the family that solves it

A waltz on the chip defaults to boom chick chick: DMC kick on 1, a noise stab on 2 and 3. The review
heard it for 52 bars. The file replaces it with 35 waltz patterns in seven families, all 12 step grids
(one bar of sixteenths in 3/4, two bars of eighths in 6/8), and only `WZ-01` is the plain groove, kept
as the control.

**Hemiola, two against three.** Six equal subdivisions can be heard as two groups of three or three
groups of two (Soundbrenner). In 3/4 the device spans two bars: accents every two quarter notes give
three larger pulses across two bars (same source). A hemiola only reads if the metre of three is
established first, otherwise it sounds like a metre change (Music Stack Exchange answer), and the
accents that carry it are exactly the positions where several metric layers coincide (Frontiers in
Psychology study of march, waltz and hemiola accent strength). Implementation: `WZ-02` (accents on 1
and 3) paired with `WZ-03` (accent pulled to beat 2), `WZ-05` for the vertical version (kick in
threes, hat and snare in twos), `WZ-24` for the baroque cadential hemiola, `WZ-31` for the 6/8 to 3/4
swap. The pairs are listed in the json as `two_bar_hemiola_pairs`, because one half alone reads as a
mistake.

**Kick on 1 and the and of 2.** `WZ-06`, `WZ-07`, `WZ-08`. The second kick goes to step 6 of 12 (the
and of 2) or step 10 (the and of 3), never to beat 2, which is the weak beat the ear already expects.
This is the cheapest cure for stiffness and it costs one DMC hit.

**Snare on 3 with ghost notes.** `WZ-10` to `WZ-13`. Ghosts stay at level 2 or 3 (velocity 28 to 42)
and at period 5 to 7; anything louder becomes a second snare part. Flams are written as two hits one
step apart, soft then loud (`WZ-11`), which at 80 to 120 bpm is 60 to 125 ms of separation, the range
where a flam reads as one thick stroke.

**March waltz.** `WZ-14` to `WZ-16`: even eighths, bass drum on 1 and 2, snare on 3, ruffs into the
beat. A march pulse in 3/4 disguises the waltz without changing the harmony.

**Rock waltz.** `WZ-17` to `WZ-20`: backbeat on 3, eighth or sixteenth hat, one displaced kick, half
time available (`WZ-19`).

**Baroque pulse with only accents.** `WZ-21` to `WZ-24`: one instrument, three weighted strokes, no
filler. A baroque texture puts the drums on the metre and lets the continuo carry the motion, so a
rock hat pattern in a baroque cue destroys the style in one bar.

**Cut time feel.** `WZ-25` to `WZ-27`: two felt pulses inside three quarter notes. Use for four bars,
then return to three, or the metre stops reading as a waltz.

**Compound waltz.** `WZ-30` to `WZ-35`: 6/8 with twelve steps over two bars. In compound metre the
snare belongs inside the big beat (steps 2, 3, 8, 9), because the dotted quarter already carries the
accent (Frontiers accent model).

## 4. The variation ladder (the rule set the card asked for)

The full ladder is in the json (`waltz_section.variation_ladder`) with bar by bar scripts for four,
eight and sixteen bar phrases. In short:

| rung | name | what changes | channels |
|---|---|---|---|
| 0 | plain | the section's home pattern | 0 |
| 1 | add ghost note | one soft hit at level 2 to 3 in an empty step | 0 |
| 2 | displace one accent | second kick to the and of 2 or the and of 3 | 0 |
| 3 | add fill | last beat, or last two beats at bar 8 | 0 |
| 4 | drop out the kick | one bar with no DMC kick at all | -1 |
| 5 | crash on the new downbeat | one long low noise hit, first bar of a section only | 0 |

Four bar cycle: 0, 1, 0, 3 (one beat fill). Eight bar cycle: 0, 1, 0, 3, 2, 1 with a period sweep, 4,
3 (two beat fill). Sixteen bars: two eight bar cycles, the second one opening with rung 5 and the
section's other home pattern.

Hard rules: never climb two rungs in one bar; never rung 3 on two consecutive bars; rung 5 once per
section; a section shorter than four bars gets rungs 0 and 3 only.

## 5. The fill library

40 fills in five types, each tagged with `placement` (before a section change, phrase end at 4, 8 or
16 bars) and `fits_feels`:

- **noise rolls** (8): even, crescendo, hairpin, buzz in short mode, a roll that stops early and
  leaves a gap, a roll that speeds up, a roll that hands over to toms.
- **tom sweeps** (8): four and six hit falls, an ascending version, a sixteen note cascade, kick and
  tom alternation, a timpani style DMC rate drop, a triplet gesture, a sweep into a crash.
- **snare flams** (8): closing flam, cascade, flams with ghosts, flam into silence, flam on the new
  downbeat, flam plus roll, double flam, flam with a tom answer.
- **cymbal style decay** (6): long low period crash, swell, metallic short mode, choke, crash into
  the downbeat, crash under toms.
- **mixed** (10): one beat exchanges, rock fill with open hat, 3/4 and 6/8 waltz fills, march
  rudiments, battle crescendo, a silence fill, a boss fill ending on period 15, a unison hit, and a
  loop point turnaround that ends soft so the seam does not click.

Placement counts in the json: `before_section_change` 28, `phrase_end_16` 17, `phrase_end_4` 14,
`phrase_end_8` 14. Those are placements available, not a schedule: the rules in
`fills_section.placement_rules` say which one is allowed where.

## 6. How the arranger reads the file

- Pick a feel and meter, then one home pattern from `waltz_section.non_plain_3_4_ids` for a waltz
  (never `WZ-01`), or from `patterns` filtered by feel for anything else.
- Read `steps` as a list of steps, each a list of hits. A hit has `instrument`, `velocity`, `accent`,
  and either `period` + `loop` (noise) or `rate` (DMC).
- Convert for `tools/render_chip.py`: noise period `p` becomes **MIDI note p + 1** (the renderer uses
  `pitch - 1` as the period index, clamped 0 to 15), `dpcm_kick` is note 36, `dpcm_snare` is note 38,
  velocity goes straight through, and a short mode hit needs CC12 = 1 at that note. This is the
  project's own mapping, not a chip fact: `DR-S11`.
- Step length is `60 / bpm / 4` for a 16th grid and `60 / bpm / 2` for the 6/8 eighth grid.
- Apply the variation ladder from `waltz_section.variation_ladder`, and take fills from the library
  by `placement` and `fits_feels`.

## 7. Sources

| id | source | url | depth when read | what it supports |
|---|---|---|---|---|
| DR-S01 | NESdev Wiki, APU Noise | https://www.nesdev.org/wiki/APU_Noise | full page | sixteen periods and their rates, mode flag, 93 vs 32767 step sequences |
| DR-S02 | NESdev Wiki, APU DMC | https://www.nesdev.org/wiki/APU_DMC | full page | sixteen playback rates, loop length decides pitch, short sample as drum |
| DR-S03 | NESdev Wiki, APU Envelope | https://www.nesdev.org/wiki/APU_Envelope | full page | sixteen constant volume levels, near linear volume, envelope loop flag |
| DR-S04 | Ripples Music, 8 bit drums without a sample pack | https://ripples-music.com/blog/how-to-make-8-bit-drums | excerpt | hat, snare and kick decay times, decay as the expressive control, one noise channel |
| DR-S05 | Soundbrenner, Hemiola | https://soundbrenner.com/blogs/articles/hemiola | excerpt | six subdivisions, three against two, the two bar 3/4 hemiola |
| DR-S06 | Music Stack Exchange, 2/2 imposed in 3/4 | https://music.stackexchange.com/questions/82690 | excerpt | a hemiola needs three established first |
| DR-S07 | Music Production Wiki, recreate the chiptune sound | https://musicproductionwiki.com/articles/how-to-recreate-the-chiptune-sound | excerpt | sixteen preset noise frequencies, fast attack for a hat, short mode as metallic |
| DR-S08 | jfound, chiptune in the browser | https://tracks.jfound.net/blog/make-chiptune-music-browser | excerpt | the 16 step starting groove, one noise sound at a time |
| DR-S09 | Frontiers in Psychology 5:1257, hemiola metre switching | https://frontiersin.org/articles/10.3389/fpsyg.2014.01257/full | excerpt | accent strength for march, waltz and hemiola, pivot positions |
| DR-S10 | Alexander Brandon, 8 bit music practical guide | https://alexanderbrandon.net/blog/8-bit-music-chiptune-guide | excerpt | noise as drums, pitch and length as the only controls, repetition with change |
| DR-S11 | this repository, tools/render_chip.py | tools/render_chip.py | full file | period to MIDI note mapping, CC12 loop bit, notes 36 and 38 for DMC |

Every pattern in the json carries the ids it was built from. DR-S04 to DR-S10 were read as search
result excerpts rather than full pages, and the json says so per source (`depth`), because a claim
taken from an excerpt is weaker evidence than a claim read on the page.

## 8. What this file does not claim

- These are not transcriptions or measurements of any commercial game's drums. The sources are
  documentation and tutorials; the numbers (periods, rates, note lengths) are hardware facts, and the
  grids are this project's own writing. The MUS-DATA-STATS corpus study, which would let a pattern's
  accent distribution be compared against real repertoire, was **not on disk** when this file was
  written (no `data/*stats*.json`), so no claim here is corpus derived.
- Tempo ranges per feel are design ranges for this project, informed by the style bible's tempos, not
  measurements.
- A sixteenth grid cannot hold a true triplet. Patterns that need a triplet gesture (`MAR-10`,
  `BOS-04`, `FLT-07`) write it as a main hit plus two softer hits, which the ear rounds at tempo; a
  real triplet needs a 12 or 24 tick grid per beat and is a renderer and arranger decision, not a
  pattern file decision.
- The renderer's noise short mode uses a fixed period rather than the mode's own period, which is a
  simplification in `tools/render_chip.py`; the data still stores both period and loop mode, so the
  renderer can be corrected without touching a single pattern.
