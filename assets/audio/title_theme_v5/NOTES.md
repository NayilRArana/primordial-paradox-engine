# Title theme v5: drums that change every 4 and 8 bars (card MUS-V5)

v5 is v4's best variant rebuilt. The ear sweep (assets/audio/EAR_SWEEP_2026-10-22.md) ranks
`title_theme_v4_medium` first of the nine masters at a pooled total of 36.0, so medium is the
base. The score is v4's (`score_v4.yaml` copied to `score_v5.yaml`, no harmonic edit), the
leitmotifs K (Kronos), Z (turnaround), P (Percy) and H (Hadrian) are the score's own notes and
are re-measured by FFT below, and no device or drum writes into the lead voice.

Source chain, one command per step, deterministic (seed 20261022):

    arrange (v4)            title_theme_v5_base.mid, carried over from v4, same score
    tools/theme_v5.py       the 4 and 8 bar drum ladder, 12 devices, the hole, the dropout
    tools/humanize.py       articulation, velocity, envelopes, vibrato, fills, micro timing
    tools/render_chip.py    MIDI -> WAV -> MP3 + loop JSON (renderer v2, soft limiter)
    tools/measure_theme_v3.py   loop seam, per voice levels, FFT leitmotifs, OGG

## Files

| file | what it is |
|---|---|
| title_theme_v5.mp3, .ogg | the deliverable pair, both from the same WAV |
| title_theme_v5.wav | the master before the lossy encode |
| title_theme_v5.mid | the humanized MIDI that was rendered |
| title_theme_v5_loop.json | loop report: start bar 5, end bar 52, seam, per voice, FFT |
| arrange_report_v5.json | drum ladder per bar, fills, devices, spacing audit |
| humanize_v5.json | articulation, onset shifts, vibrato, fills |
| title_theme_v5_round1.mp3 | round 1, the only build the ear scored |
| score_v5.yaml | the score, identical to v4's |

## What changed from v4 medium

1. Drums change every 4 bars. Each section is eight bars, and its kit is written as two four
   bar blocks (`block1`, `block2` in `tools/theme_v5.py`). Twelve distinct four bar blocks in
   the 48 loop bars, one per section block, so bar 9 does not repeat bar 5.
2. Drums change every 8 bars. The last bar of each block carries a fill and the last bar of
   each eight bar span carries a bigger one (four eighths instead of three, plus a velocity
   accent), so the eight bar line is audible, not just the four. Six fills at four bar ends and
   six at eight bar ends.
3. Three low noise periods are used as toms (pitch 9, 11 and 13 on the noise channel) so the
   eight bar fill is a descending tom run rather than another snare.
4. Section levels (velocity points on the kit): A -6, A prime -2, B -8, B prime +4, trio -14,
   A return +2. This is the structure complaint the ear made of v4 ("uniform levels").
5. A hole before the reprise: the trio's clock stops on beat 3 of bar 44 and the return
   arrives on the kick at bar 45. The arpeggio dropout in bars 45 to 48 is kept from v4.
6. The kit's block boundaries are counted from each section's own first bar. Round 1 counted
   them from the absolute bar index, which put every boundary four bars late and landed the
   fills mid phrase; that is fixed in the delivered build.

Drum hits: 96 on dpcm, 79 on noise. Per hit timing and velocity jitter are v4's, unchanged.

## Dissonance: 11 applied devices, 1 dropped

Devices come from `data/dissonance_rules.json` through v4's machinery: one note of an inner
voice is displaced so the preparation and the resolution are the notes the arranger already
wrote. Rate 1.69 devices per eight bars against the policy band of 1 to 2. Two risk 3 devices,
eight bars apart, inside the four bar spacing rule. Minimum spacing between any two devices is
above the two beat floor.

| bar | beat | voice | device | risk | pitch before to after to resolution |
|---|---|---|---|---|---|
| 7 | 2.0 | vrc6 pulse b | DIS-02 | 1 | 60 -> 59 -> 60 |
| 11 | 2.0 | vrc6 saw | DIS-17 | 1 | 50 -> 51 -> 50 |
| 14 | 2.5 | vrc6 pulse b | DIS-07 | 2 | 77 -> 78 -> 77 |
| 20 | 1.0 | pulse 1 | DIS-03 | 2 | 57 -> 65 -> 64 |
| 25 | 2.5 | pulse 1 | DIS-02 | 1 | 60 -> 64 -> 65 |
| 27 | 1.0 | vrc6 saw | DIS-11 | 3 | 50 -> 53 -> 50 |
| 31 | 2.0 | pulse 1 | DIS-02 | 1 | 64 -> 66 -> 67 |
| 35 | 1.0 | vrc6 saw | DIS-11 | 3 | 50 -> 53 -> 50 |
| 39 | 2.0 | vrc6 saw | DIS-07 | 2 | 51 -> 49 -> 51 |
| 42 | 1.0 | pulse 1 | DIS-03 | 2 | 74 -> 70 -> 69 |
| 47 | 2.0 | vrc6 saw | DIS-02 | 1 | 48 -> 47 -> 48 |

Dropped: bar 44 beat 1.0, DIS-17 on the saw, refused by the tool because that voice has no note
to resolve into there. The tool records the refusal rather than forcing it, which is the F7 rule
in MUSIC-DISSONANCE.md section 7.

## Ear loop: scores per round

Rubric order: hook, drums, tension, human, variety, structure. Targets from the card: drums 7,
tension 7, human 6, hook 7.

| round | build | model | hook | drums | tension | human | variety | structure |
|---|---|---|---|---|---|---|---|---|
| 1 | 4 and 8 bar ladder, 12 devices | gemini-3.5-flash | 7 | 5 | 6 | 4 | 7 | 6 |
| 2 | delivered: fills from 2.0, section levels, hole at 44, block offset fixed | not scored | | | | | | |

Round 1 review: `assets/audio/ear_reviews/title_theme_v5_20261022T231713Z.md`.

Round 2 was built, rendered and measured, and could not be scored: the free tier ran out. The
rotation the card asks for was followed and every model was unavailable:

| model | answer |
|---|---|
| gemini-3.5-flash | 503 UNAVAILABLE at 23:14 UTC, then 429 at 23:35 UTC (quota, retry in 7h39m) |
| gemini-3.6-flash | 429 quota exceeded, retry in 7h43m |
| gemini-3.8-flash | 503 UNAVAILABLE, three attempts across seven minutes |

`PP_EAR_MAX_RETRIES=0` was set so a 429 or 503 returns at once instead of sleeping, which is the
card's "do not wait". Two rounds of the six are therefore done, one of them scored.

Read the round 1 numbers against the sweep's own noise floor: a one point difference on any
criterion is noise. 7/5/6/4/7/6 is exactly what v4 medium scored in the sweep, so the ear did
not hear the 4 and 8 bar ladder at round 1. That is consistent with the sweep's finding that
this ear gave drums 5 to nine different masters and never gave human feel above 4 to any of
them, and its round 1 review repeats the same two complaints v4 got ("flat boom-tch-tch", "hard
quantized"). Its numbers are not yet an oracle for drums or human feel; they need Nayil's own
scores in `data/ear_calibration.csv`.

## Hook score (tools/hook_score.py, run on Pine)

    68 / 100, melody track 'vrc6 pulse a', 52 bars, 137 notes
    motif 2 bars from bar 10, 7 notes, 4 returns, 21% coverage
    ok: motif returns 12.0, hook cell 10.0, steps over leaps 12.0, variation on third return 8.0,
        repeated pitch 6.0
    fix: range 5.0 of 8 (29 semitones), leaps per motif 4.0 of 8 (no leaps),
         motif coverage 7.1 of 20 (21%), contour 2.5 of 10, loop length 1.2 of 6 (52 bars)

The lead is the score's own melody, unchanged from v3 and v4, so this number is not new work:
it is the measurement the card asks for on the delivered MIDI. Its weakest rows are compositional
and belong to whoever edits `score_v5.yaml`: motif coverage, contour and the 52 bar loop length.
A drum or dissonance pass cannot move them.

## Checks

| check | result |
|---|---|
| duration | 74.266803 s (card asks 74 s) |
| loop | bar 5 to bar 52, 48 bars, 68.552517 s |
| loop seam step (needs below -60 dBFS) | 0 samples, -90.31 dBFS PASS |
| head peak at the loop point | -8.61 dBFS |
| FFT Kronos bar 5: E5 C5 D5 E5 | all ok, worst -1.40 cents |
| FFT Percy bar 37: E4 G4 B4 | all ok, worst -0.91 cents |
| FFT Hadrian bar 41: D5 C#5 | all ok, worst +0.43 cents |
| silent voices | none (all eight measured, every one above -50 dBFS rms) |
| clipping voices | none, master peak -1.00 dBFS |
| mp3, ogg, wav, midi, loop json | all present, ogg written by the measure step |
| humanize | 1056 of 1060 notes changed, 648 onsets moved by up to 0.75 frames, 20 vibrato notes, 24 fills, 20 phrase breaths, 2 notes under the 85 percent articulation floor (frame grid) |
| arranger tests (pytest, on Pine) | 143 passed, 2 skipped, exit 0 (test_arrange, test_arrange_v3, test_humanize, test_hook_score, test_dissonance_rules) |
| data/dissonance_rules.json spacing audit | min spacing ok, risk 3 gap 8 bars ok |

All Python checks and the pytest run went through Pine (`pine_offload.py --cmd`), not the PC.
Result: `data/results/offload-mus-v5-0.json` in the arananet pine project.

## What Nayil has to decide by ear

1. Which drum build he prefers: v5 (fills on the four and eight bar lines, section levels, the
   hole at 44) or v4 medium, which is the one the ear actually scored.
2. Whether the trio's final bar should lose its clock (the hole) or keep it and let the return
   arrive over it. It is the one change here that removes a sound rather than adding one.
3. Whether to resume the ear loop after the free tier resets in about 8 hours, and whether to put
   his own scores in `data/ear_calibration.csv` first, because the ear has not separated drum
   builds in any round so far.

## What this file does not claim

It does not claim v5 reached the card's targets (drums 7, tension 7, human 6, hook 7). Round 1
reached hook 7 and nothing else, and round 2 has no ear score at all. It does not claim the drum
ladder is an improvement an ear can hear: the one measurement we have says the ear could not tell
v5 round 1 from v4 medium.
