# Title theme v4: drums, tasteful dissonance, human feel (card MUS-V4)

Built from `score_v3.yaml` copied to `score_v4.yaml` (no edit to the v3 file; the
leitmotifs K (Kronos), Z (Zephyr/turnaround), P (Percy) and H (Hadrian) are untouched
and verified by FFT below). Tempo 126 bpm, 52 bars, 3/4: 74.267 s, loop bar 5 to 52.

Pipeline, one command per step, deterministic (seeds in the reports):

    theme_v4.py    base MIDI + score_v4 -> drums, dissonance, voice dropout (per variant)
    humanize.py    articulation, velocity, envelopes, vibrato, fills, onset micro-timing
    render_chip.py MIDI -> WAV -> MP3 + loop JSON
    measure_theme_v3.py  loop seam, per voice levels, FFT leitmotifs, OGG

## Files

| variant | audio | loop json | reports |
|---|---|---|---|
| subtle | title_theme_v4_subtle.mp3 / .ogg / .wav | title_theme_v4_subtle_loop.json | spice_subtle.json, humanize_subtle.json |
| medium | title_theme_v4_medium.mp3 / .ogg / .wav | title_theme_v4_medium_loop.json | spice_medium.json, humanize_medium.json |
| spicy  | title_theme_v4_spicy.mp3 / .ogg / .wav  | title_theme_v4_spicy_loop.json  | spice_spicy.json, humanize_spicy.json |

## Ear loop, scores per iteration (tools/ear_critic.py, gemini-3.5-flash)

Six dimensions: hook, drums, tension, human, variety, structure. Target set by the card:
drums 7+, tension 7+, human 6+, hook 7+.

| iteration | what changed | subtle | medium | spicy |
|---|---|---|---|---|
| 1 | first drum ladder, dissonance pass, no onset jitter | 7/5/6/4/8/7 | 7/5/6/4/8/7 | 7/5/6/4/7/6 |
| 2 | onset micro-timing 0.45 / 0.75 / 1.1 frames | 7/5/5/4/7/6 | 7/5/6/4/8/7 | 7/4/5/4/6/6 |
| 3 (delivered) | final bar kept out of the loop cut (drums, no device on bar 52) | not rescored | not rescored | not rescored |

The target was NOT reached. Hook is the only dimension at 7; drums stayed at 5 (4 for
spicy), tension 5 to 6, human feel stuck at 4 across both scored rounds, even though
round 2 moved 406 to 675 of roughly 1050 note onsets off the grid by up to a frame.
What that means, plainly: this ear did not separate three genuinely different drum
builds (18, 26 and 32 hits in section A; 104, 123 and 104 noise hits per file), and it
repeated the same two complaints both rounds (a static waltz kit, a safe harmony). Its
numbers are not yet a usable oracle; they need Nayil's own scores in
`data/ear_calibration.csv` before any further tuning trusts them.

The ear's own suggestions, and what was done with them:

1. Delayed vibrato on long lead notes. Already present (21 to 51 notes per file carry
   vibrato, `humanize` step 4). Not changed.
2. A sixteenth fill into the next section. `humanize` writes 19 to 23 fills before
   section changes; round 2 added 3 more by density.
3. Syncopated bass pedal. Not done: it rewrites the arranger's bass, outside this card.
4. F minor 6 (minor iv) at bars 33 to 36. Not done: it is a chord change and belongs in
   `score_v4.yaml` as a proposal for Nayil, not a silent edit. This is the strongest of
   the five and the one most likely to move tension.
5. Dropout before the climax. Done in medium and spicy: the arpeggio rests bars 45 to 48
   (24 notes).

## Drum ladder

Hit kinds: `k` kick (DPCM 36), `s` snare (DPCM 38), `r` short snare, `h` closed hat,
`o` open hat, `g` ghost hat, `w` sea wash, `t` dry tick (the cold clock). Slots are
eighths 0 to 5 in a 3/4 bar; each rung is one bar, cycled through the section.

### subtle (18 to 28 hits per section, hats and kick only in A)

| section | bars | cycle (one rung per bar) | hits |
|---|---|---|---|
| A | 5-12 | `2:h,4:h` / `2:h,3:h,4:h` | 18 |
| A_prime | 13-20 | `0:k,2:h,4:h` / `0:k,2:h,3:h,4:s` | 26 |
| B | 21-28 | `0:k,0:h,2:h,4:h` / `0:k,2:h,4:h` / `0:k,2:h,3:h,4:s` | 28 |
| B_prime | 29-36 | `0:k,2:h,4:s` / `0:k,2:o,4:s` / `0:k,2:h,4:h,5:s` | 26 |
| C_trio | 37-44 | `0:k` / `0:w,2:w,4:w` (cold clock in the second half) | 16 |
| A_return | 45-52 | `0:k,2:h,4:h` / `0:k,2:h,3:r,4:s` | 25 |

### medium (23 to 30 hits, backbeat on the third beat)

| section | cycle | hits |
|---|---|---|
| A | `0:k,2:h,4:s` / `0:k,2:h,3:g,4:s` | 26 |
| A_prime | `0:k,2:h,4:h` / `0:k,2:h,4:o` / `0:k,2:h,3:r,4:s` | 26 |
| B | `0:k,0:h,2:h,4:s` / `0:k,2:h,4:h` / `0:k,2:h,4:s` / `0:k,3:r,4:h,5:s` | 28 |
| B_prime | `0:k,2:h,4:s` / `0:k,1.5:g,2:h,4:s` / `0:k,2:o,4:s` / `0:k,2:h,3:r,4:s,5:r` | 30 |
| C_trio | `0:k` / `0:t,2:t,4:t` / `0:k,2:t` / `0:k,2:t,4:t` / `0:k,0:w,2:w,4:w` / `0:k,2:w,4:w` | 23 |
| A_return | `0:k,2:h,4:s` / `0:k,2:o,4:s` / `0:k,2:h,3:r,4:s,5:r` | 26 |

### spicy (32 to 38 hits, ghosts and pickups)

| section | cycle | hits |
|---|---|---|
| A | `0:k,2:h,4:s,5:g` / `0:k,2:h,3:g,4:s` / `0:k,2:o,4:s` / `0:k,2:h,3:r,4:g,5:r` | 32 |
| A_prime | `0:k,1.5:g,2:h,4:h` / `0:k,2:h,4:h,5:g` / `0:k,2:o,4:h` / `0:k,2:h,3:r,4:s,5:r` | 32 |
| B | `0:k,0:h,2:g,3:h,4:s` / `0:k,1.5:g,2:h,4:s` / `0:k,2:h,4:s,5:g` / `0:k,3:r,3.5:r,4:r,5:s` | 36 |
| B_prime | `0:k,1.5:g,2:h,4:s,5:g` / `0:k,2:h,3:g,4:s` / `0:k,2:o,4:s,5:g` / `0:k,2:h,3:r,4:s,4.5:r,5:r` | 38 |
| C_trio | 8 rungs, cold clock `t` in bars 2 to 5, sea wash `w` in bars 6 to 8 | 36 |
| A_return | 5 rungs, from `0:k,1.5:g,2:h,4:s,5:g` to the 7 hit fill `0:k,2:h,3:r,4:s,4.5:r,5:r` | 35 |

Per hit timing feel in MIDI ticks (ppq 480, one eighth is 240): kick -2 to +3,
snare -2 to +4, short snare 0 to +5, hat -2 to +4, open hat -1 to +4, ghost -1 to +5,
wash 0, tick 0 to +3. Velocity jitter +-3 (hats and open hats +-4), plus +6 on the
downbeat and the third beat.

The last bar of the file is cut to hits before slot 5, and no dissonance device is
placed on it, so the loop cut is not mid-hit.

## Dissonant moments (bar, beat, voice, device, pitch before, after, resolution)

Devices come from `data/dissonance_rules.json`; risk 1 is the mildest, 3 the sharpest.
Subtle keeps 7 anchors, medium 10, spicy 12 (13 less the bar 52 device the loop cut
removed).

Common to all three variants:

| bar | beat | voice | device | pitch | risk | what it is |
|---|---|---|---|---|---|---|
| 7 | 2.0 | vrc6 pulse b | DIS-02 | C4 to B3 to C4 | 1 | chromatic lower neighbour in the counter, over Am |
| 14 | 2.5 | vrc6 pulse b | DIS-07 | F5 to F#5 to F5 | 2 | accented passing tone on beat 2 over E7 |
| 27 | 1.0 | vrc6 saw | DIS-11 | D3 to F3 to D3 | 3 | flat nine in the E7 pad, released on the next bar line |
| 39 | 2.0 | vrc6 saw | DIS-07 | D#3 to C#3 to D#3 | 2 | passing tone over B7b9, the D against D sharp |
| 42 | 1.0 | pulse 1 | DIS-03 | D5 to A#4 to A4 | 2 | appoggiatura over the D minor bar of the cold half |
| 51 | 3.0 | pulse 2 | DIS-18 | D5 to C#5 to C5 | 3 | echo clash on the way back to the loop |

Medium and spicy add:

| bar | beat | voice | device | pitch | risk |
|---|---|---|---|---|---|
| 11 | 2.0 | vrc6 saw | DIS-17 | D3 to D#3 to D3 | 1 |
| 20 | 1.0 | pulse 1 | DIS-03 | A3 to F4 to E4 | 2 |
| 25 | 2.5 | pulse 1 | DIS-02 | C4 to E4 to F4 | 1 |
| 31 | 2.0 | pulse 1 | DIS-02 | E4 to F#4 to G4 | 1 |

Spicy only: bar 35 beat 1.0 vrc6 saw DIS-11 D3 to F3 to D3 (the flat nine again, eight
bars later); bar 47 beat 2.0 vrc6 saw DIS-02 C3 to B2 to C3.

Medium and spicy also rest the arpeggio (pulse 1) for bars 45 to 48, which is the ear's
dropout before the last statement.

## Humanize settings per variant

Same seed (20261022), same articulation, velocity, envelope, vibrato and fill rules.
Only the onset micro-timing differs, which is the whole point of the ladder:

| | subtle | medium | spicy |
|---|---|---|---|
| onset frames | 0.45 | 0.75 | 1.1 |
| notes moved off the grid | 406 of 1048 | 675 of 1044 | 645 of 1094 |
| notes changed overall | 96.3 percent | 96.7 percent | 96.8 percent |
| vibrato notes | 31 | 21 | 21 |
| fills before section changes | 19 | 22 | 23 |
| phrase breaths | 20 | 20 | 20 |
| grace notes / mordents | 1 / 1 | 1 / 1 | 1 / 1 |

One frame is 1/60 s, about 16.8 MIDI ticks at 126 bpm; the shift is applied per note at
a fixed probability (70 to 75 percent at these settings), so the beat is elastic, not
sloppy, and never drifts because the grid is still the reference.

## Checks

| check | subtle | medium | spicy |
|---|---|---|---|
| duration | 74.267 s | 74.267 s | 74.267 s |
| loop bar 5 to 52 | 68.553 s | 68.553 s | 68.553 s |
| loop seam step (needs below -60 dBFS) | -90.31 dBFS PASS | -90.31 dBFS PASS | -15.57 dBFS FAIL |
| FFT Kronos bar 5 E5 C5 D5 E5 | all within 3 cents | all within 3 cents | all within 3 cents |
| FFT Percy bar 37 E4 G4 B4 | within 1 cent | within 1 cent | within 1 cent |
| FFT Hadrian bar 41 D5 C#5 | within 1 cent | within 1 cent | within 1 cent |
| silent voices | none | none | none |
| clipping voices | none | none | none |
| mp3, ogg, wav, midi, loop json | present | present | present |

Leitmotif pitches are read from `score_v4.yaml` by the measure tool, not typed in, so
the FFT check cannot drift from the composition. The in mix melody band test (380 to
900 Hz on the full mix) passes on the sections where the lead is in that band; it
reports no where the melody sits above it (Percy and Hadrian in some variants), which
is expected for a waltz lead in the fifth octave.

Open check: spicy fails the loop seam at -15.57 dBFS. The first sample of the loop is
mid-attack (its head peak is -12.81 dBFS, the loudest of the three) while the file's
last sample is near silence, so the seam steps. Subtle and medium both land on near
zero at the loop point. A first fix (last bar takes the loop start's own drum pattern)
made subtle fail as well, so it was rolled back; the cause is the phase at bar 5 beat 1,
not the kit on bar 52. Fixing it means changing what sounds on the loop downbeat (a
kick on beat 1 of bar 5), which is a musical choice for Nayil, not a defect to paper
over with a fade.

## What Nayil has to decide by ear

1. Which variant: subtle, medium or spicy (the drum density ladder above).
2. Whether the bar 5 downbeat keeps its kick (which is what costs spicy its clean loop
   seam) or moves to the hat so all three loop seamlessly.
3. Whether the ear's F minor 6 at bars 33 to 36 goes into `score_v4.yaml`: it is the one
   suggested change that is a composition decision rather than a production one.
