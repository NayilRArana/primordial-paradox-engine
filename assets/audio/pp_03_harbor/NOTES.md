# PP-03 "Harbor", the arrival cue. Render note.

Card MUS-CUE-PP03 (GAME-ROADMAP-1 R12, step S4). Written 2026-10-22 by the musician lane.
Scope: this folder only. `data/audio.json` is untouched; the wiring card owns that row.

## The render, in the numbers the card asks for

| | |
| --- | --- |
| Cue | PP-03 "Harbor", asset `pp_03_harbor`, loop |
| Tempo | 68 bpm, 4/4 (882353 us per quarter) |
| Bars | 64, eight sections of 8 |
| Loop point | the whole file: bar 1 to bar 64, sample 0 to 9,961,412 |
| Loop length | 225.882 s (3:46) at 44.1 kHz mono 16 bit, 9,961,412 samples |
| Key | A minor; sections 3, 4 and 7 sit in C major (the relative major) |
| Voices | the seven of the 2A03 plus VRC6: `vrc6 pulse a`, `vrc6 pulse b`, `vrc6 saw`, `pulse 1`, `pulse 2`, `triangle`, plus `noise` and `dpcm` for drums. No sample outside DPCM: the only sampled sounds are the DMC kick and snare |
| Peak / RMS | -1.00 dBFS / -16.12 dBFS |
| Files | `pp_03_harbor.mid`, `.wav`, `.mp3` (192k), `.ogg` (vorbis q6), `pp_03_harbor_loop.json` |

Why a 3:46 loop under four pages of text: at 68 bpm a bar is 3.53 s, so the loop outlasts the read and
turns over only after the player has finished the first page set. Sections 1 and 8 are the same chord
(Am), and bar 1 and bar 64 sound the same bass root (MIDI 40) and pad root (MIDI 52), which is the
seam check the card asks for.

## The score

- `score_pp03.yaml` is the recipe: eight sections, chords per bar, the lead in eighth-note durations,
  the texture in prose, and the drum plan by pattern id. Original; no published melody is quoted.
- `build_pp03.py` is the arranger: it reads that yaml plus `data/drum_patterns.json` and writes the MIDI
  in the eight track layout `tools/render_chip.py` expects. Deterministic, no randomness.
- The lead is motif H, the harbor tide: root, third, fifth rising, then a crest and a fall. It is Percy's
  own cell from `percy_theme/score_percy.yaml` (motif P) in A minor and longer values, which is FOX-01:
  the same shape in a new place, per the leitmotif rule, since PP-06 is "Percy, Tyrant of the Harbor".
- The accompaniment is the calm set: broken chord on `pulse 1` (CLS-01 register, eighths in the outer
  sections and quarters in the middle for contrast), guide tone on `vrc6 pulse b` in half notes (BAR-11),
  pad on the saw, bass on the triangle as root and fifth with a walking bar where the section says so.
  The echo arrives on `pulse 2` from section 3 (CHIP-08: one eighth late, 40 percent).

## The drums, which is what this card was really about

The 2026-10-22 ear sweep scored drums 3 to 5 on every master and said the noise channel holds one
boom-chick figure for the whole track. This cue answers it with the project's own kit and ladder, not
with new invention:

- Home patterns by id from `data/drum_patterns.json`: CLM-01 (brushed quarter pulse), CLM-03 (heartbeat
  kick), CLM-07 (two strikes per bar) and CLM-08 (soft noise floor with one accent). All four are calm
  patterns, every level 2 to 3 before the section scale.
- The eight bar variation ladder from `knowledge/MUSIC-DRUMS.md` section 4, bar by bar: 0, 1, 0, 3, 2, 1,
  4, 3. Ghost notes land at step 6, the displaced kick at the and of 3, the kick drops out for one bar in
  every section, the hat brightens by one period in the rung 6 bars, and rung 5 is a soft crash on the
  downbeat of four sections only.
- A library fill into every section end: FLF-01 (one beat closing flam) on the fourth bar, FLR-01 (one
  beat sixteenth roll) on the eighth bar, which is the "16th note snare fill into the next section" the
  ear asked for. FLX-10, the loop point turnaround, in bar 64 so the seam reads as a return.
- Measured result: 37 distinct bar grids in 64 bars, longest run of identical bars 1. The drums cannot be
  heard as one static figure.

## Checks run, with the output they returned

```
python tools/melody_guard.py assets/audio/pp_03_harbor/pp_03_harbor.mid \
    "<workspace>/Shared/projects/musikage" \
    --json assets/audio/pp_03_harbor/melody_guard.json
  -> PASS, 29 references, longest identical (interval, rhythm) run 1,
     longest identical interval run 4, highest 5-gram Jaccard 0.0000

python assets/audio/pp_03_harbor/build_pp03.py
  -> exit 0, 64 bars, 225.882 s, 1375 notes, first chord Am, last chord Am

python tools/render_chip.py ... --loop-bars 64 --loop-json ...
  -> 225.882 s, peak -1.00 dBFS, rms -16.12 dBFS, seam sample difference 0

python assets/audio/pp_03_harbor/check_pp03.py --json score_check.json
  -> 20 passed, 0 failed
```

`check_pp03.py` re-reads the MIDI with the project's own parser. It checks: format 1 and division 480;
eight voice tracks named as the renderer expects; no voice outside the 2A03 plus VRC6 set; 68 bpm; 4/4;
every note inside the loop point; the arrangement exactly 64 bars; every note inside its declared
register; the score opens and closes on the same chord; bar 1 and bar 64 sound the same bass and pad
root; the noise channel never plays two hits at one tick; every four bar phrase ends with a lead rest of
an eighth; the lead rests in at least half the bars; 37 distinct drum bars; the wav, mp3 and ogg exist and
agree to 0.000000 s; the render is exactly 64 bars; the loop json reports 64 bars and seam difference 0.

Per 8 bar block RMS from the wav: 0.1508, 0.1508, 0.1535, 0.1640, 0.1546, 0.1479, 0.1641, 0.1639. Every
section sounds, the reading stretch (block 6) is the quietest, and nothing dips out.

## Note counts (arranged)

| voice | notes | role |
| --- | --- | --- |
| vrc6 pulse a | 172 | the lead, duty 0.25, vibrato on held notes |
| vrc6 pulse b | 128 | the guide tone, half notes |
| vrc6 saw | 128 | the pad, root then fifth |
| pulse 1 | 408 | the broken chord |
| pulse 2 | 129 | the echo of the lead, from section 3 |
| triangle | 140 | the bass |
| noise | 136 | hat, brush, snare, ghost, fill, crash |
| dpcm | 134 | kick and snare |

## Which files here the commit carries, and why two do not

Committed: `score_pp03.yaml`, `build_pp03.py`, `arrange_report.json`, `pp_03_harbor.ogg`,
`pp_03_harbor_loop.json`, `score_check.json`, `melody_guard.json` and this note. The builder is
measured by `tests/test_build_pp03.py` (card t_6af137c1), which reads the committed score and the
committed `data/drum_patterns.json` only: it rebuilds the arrangement, checks it against
`arrange_report.json`, writes a MIDI into a throwaway folder and reads it back through
`tools/render_chip.py`.

`check_pp03.py` is a WORKING TREE TOOL, deliberately not committed. It re-reads `pp_03_harbor.mid`
and then opens `pp_03_harbor.wav` and `pp_03_harbor.mp3` and measures all three renders with ffprobe,
and the wav and mp3 are the masters the root `.gitignore` keeps out of the repository. A test for it
could only skip when a master is absent, and this project already ruled that out after card
t_50a290de: two tests passing by skipping looked healthy at HEAD while reading nothing. So the
checker stays beside the master and is run from the live tree:

```
python assets/audio/pp_03_harbor/check_pp03.py --json score_check.json
```

## What is not done here, on purpose

- `data/audio.json` still carries `placeholder: true` for PP-03. The wiring card flips it to this asset.
- Nothing was uploaded, published or sent. The files sit in this folder.
- The ear critic was not run on this cue: `tools/ear_critic.py` needs the Gemini quota, which the ear
  sweep of 2026-10-22 used up (20 requests per day, free tier). The drum claim above is measured from
  the MIDI and the audio, not from a model's opinion.

## The decision left to Nayil, by ear

Section 8 bar 64 ends on Am held under the pad, and the loop returns to bar 1 on the same chord, so the
seam is deliberate rather than disguised. If it reads as a restart instead of a swell, the one-line fix
is to raise the section 8 crash to bar 63 or to give bar 64 a bar of lead rest; both are score edits and
neither touches anything outside this folder.
