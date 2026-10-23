# PP-05 "Small Ship", render note. Card MUS-CUE-PP05 (t_1c42a535), GAME-ROADMAP-1 child R13, step S5.

A bed, not a fanfare. It plays under a 32 s boarding scene, a free three room walk and the ship's log
save, so the whole cue is one 60 s loop that can be stopped at the log terminal and restarted without a
seam the player can hear.

## The four facts the card asks for

| | |
| --- | --- |
| Tempo | 96 bpm, 4/4 (MIDI tempo 625000 us per quarter, re-read from the file) |
| Bars | 24: A 8, A_fugue 8, A_second 4, close 4 |
| Voices | 2A03 pulse 2 (hum), 2A03 triangle (bass), 2A03 noise (hats), DPCM (kick), VRC6 pulse a (lead), VRC6 pulse b (the low call), VRC6 saw (drone); 2A03 pulse 1 is silent by design. Eight voice lines, nine MIDI tracks. No sampled or non chip voice anywhere. |
| Loop point | bars 1 to 24, whole form, sample 0 to 2646000 at 44.1 kHz = 60.000000 s. Sample rate and bar grid are exact (`24 * 4 * 60 / 96 = 60.0`), so the loop is 24 whole bars and the wrap is sample 2646000 back to sample 0 |

## What exists here

| File | What it is |
| --- | --- |
| `score_pp_05.yaml` | The composition: D minor, 4/4, 96 bpm, 24 bars. Sections, chords, the melody bar by bar, the low voice, and the texture the arranger writes. Same schema as `title_theme_v3/score_v3.yaml` plus `meta.profile` and a per section `second_voice` |
| `pp_05_small_ship.mid` | The arrangement, 9 tracks, ppq 480, 4/4, 96 bpm, 60.0 s |
| `pp_05_small_ship.wav` | 44.1 kHz mono 16 bit, peak -1.00 dBFS, rms -17.87 dBFS |
| `pp_05_small_ship.mp3` | 192 kbps, ffprobe duration 60.000000 s |
| `pp_05_small_ship.ogg` | Vorbis, quality 6 (112.6 kbps effective), ffprobe duration 60.000000 s |
| `pp_05_small_ship_loop.json` | The renderer's loop record: 24 bars, 60.0 s, seam sample difference 0, edge window 1 ms |
| `arrange_report.json` | The arranger's own numbers for this score |
| `measure_pp_05.json` | My bar level measurement of the WAV: per bar rms, section means, seam figures, six checks |
| `melody_guard.json` | Originality report on the MIDI melody |
| `hook_report.json` | The hook meter's score of the melody, kept because it is the weakest number here (see below) |
| `check_motif.py` | Reads the MIDI and proves K is present and no quotation of K exists (shape in K's own rhythm, or K's own pitches) |

## The theme carries the family leitmotif, transformed

`knowledge/CHARACTER-BIBLE.md` gives K as E5 C5 D5 E5, a dotted quarter then three stepwise eighths, in
A minor, the family call. This cue never states that shape in that key or that rhythm. It applies three
of the four operations the same table allows:

- **Key change plus augmentation**, bars 1, 5 and 21: A4 F4 G4 A4 in D minor, written 4 1 1 2 instead of
  3 1 1 1 (bar 21 splits it across the bar line, 6 1 1). Same interval shape, twice the length, new key.
- **Transposition**, bars 10 and 14 on VRC6 pulse b, a fifth down: D4 Bb3 C4 D4, in the low voice, and
  bar 13 on the lead an octave up: A5 F5 G5 A5.
- **Inversion**, bar 17: A4 C5 Bb4 A4, the third rising and the two steps falling, kept diatonic in D minor.

The lead states K at bars 1, 5, 13, 17, 21 and the low voice at 10 and 14. Nothing is quoted, which is
also what `melody_guard.json` reports.

## Checks run

```
python tools/arrange.py assets/audio/pp_05_small_ship/score_pp_05.yaml \
    --report assets/audio/pp_05_small_ship/arrange_report.json \
    --hook-report assets/audio/pp_05_small_ship/hook_report.json
  -> exit 0, 24 bars, beats_per_bar 4, time signature "4/4", bpm 96.0, duration 60.0 s,
     chords_match_score true, out_of_range [], vibrato_controls 0, midi_duration_seconds 60.0
     notes: lead 43, pulse b 8, hum 384, saw 24, triangle 24, hats 80, kick 48, pulse 1 0

python tools/melody_guard.py assets/audio/pp_05_small_ship/pp_05_small_ship.mid \
    "<workspace>/Shared/projects/musikage" \
    --json assets/audio/pp_05_small_ship/melody_guard.json
  -> PASS. 43 melody notes, 42 intervals, 29 reference melodies, highest 5-gram Jaccard 0.0000,
     longest identical (interval, rhythm) run 0, longest identical interval run 6 (limit 8)

python tools/render_chip.py assets/audio/pp_05_small_ship/pp_05_small_ship.mid \
    assets/audio/pp_05_small_ship/pp_05_small_ship.wav --loop-bars 24 \
    --mp3 assets/audio/pp_05_small_ship/pp_05_small_ship.mp3 \
    --loop-json assets/audio/pp_05_small_ship/pp_05_small_ship_loop.json
  -> 60.000 s, peak -1.00 dBFS, rms -17.87 dBFS, loop 24 bars 2646000 samples,
     seam sample difference 0, edge peak head 1640 tail 0

ffmpeg -i pp_05_small_ship.wav -c:a libvorbis -q:a 6 pp_05_small_ship.ogg
  -> ogg written, 844,739 bytes

ffprobe (all three codecs): mp3 60.000000 s, ogg 60.000000 s, wav 60.000000 s, all 44.1 kHz mono
python assets/audio/pp_05_small_ship/measure_pp_05.py -> measure_pp_05.json, six checks true, pass true
python assets/audio/pp_05_small_ship/check_motif.py -> PASS, five checks:
  melody bar 1 A4 F4 G4 A4 at 4 1 1 2 eighths (K augmented, D minor)
  K interval shape -4 +2 +2 found 5 times, bars 1, 5, 10, 13, 14
  0 quotations in K's own rhythm, 0 in K's own pitches, and E5 never sounds in the cue
```

The six measured checks: seconds is 60, 24 bars read, no silent bar, close is quieter than A and
A_fugue, the wrap step is at most 1 percent of peak (it is 0 samples), the 1 ms edge jump is at most
2 percent (215 samples against a peak of 29203, which is 0.74 percent).

## Numbers a reviewer can argue with

- Section mean RMS: A 3785.0, A_fugue 4018.8, A_second 5414.3, close 3766.8. Bar rms runs -18.96 to
  -15.37 dBFS, quietest bar 4, loudest bar 20. The corridor is the one place the cue gains weight,
  because the arranger's recipe for that section holds the bass as a whole note instead of a beat 1
  attack. It is 3.1 dB, and the close gives it back.
- The lead is silent in 15 of 24 bars; its longest silence is six bars. Rests are written, not implied.
- Harmony is one cell: Dm Bb F C then Dm Bb Gm A7 in A, the same with iv for III in A_fugue, cut to four
  chords in A_second, and Dm Bb A7 Dm in close. Bars 8, 16 and 20 are half cadences on V7; bar 24 is the
  only authentic cadence, so the loop closes once per 60 s instead of every eight bars.
- One deliberate dissonance device: A4 over the Gm bar in bar 7 is a ninth that resolves to the root of
  V7 in bar 8. The only chromatic pitch in the cue is C#5 (bars 16, 20, 23), the raised seventh of D
  harmonic minor over V7, which resolves to D each time. That is about 5 percent of melody notes carrying
  a named device, inside the 3 to 6 percent band `knowledge/MUSIC-DISSONANCE.md` sets.
- Hook meter (`hook_report.json`): 58 of 100, weakest item motif coverage 21 percent. That is the one
  number that would look better on a hook and it is low on purpose: the meter wants a two bar cell stated
  three times, and this cue is a bed built from a one bar cell with long rests. If a stronger hook is
  wanted the fix is musical, not technical: make K a two bar statement and repeat it three times.

## Decisions I made, and the ones I did not

- `meta.profile` is `hadrian` because `tools/arrange.py` carries three recipe sets and this card's file
  scope is this folder only, so the arranger cannot learn a fourth here. The hadrian set is the one that
  reads as a bed, and its fixed pitch hum doubles as the ship's engine. Section names stay A, A_fugue,
  A_second and close because that set reads its levels per section name.
- `data/audio.json` is untouched, as the card says. The PP-05 row still says `placeholder: true` and
  `placeholder_sound: ship_ambient`, so nothing in the game points at these files yet. Wiring it is a
  one line change for whoever owns that file.
- `python tools/check_build_inputs.py` currently exits 1 naming `pp_05_small_ship.ogg` as an
  UNCOMMITTED SOURCE. That is direction B of that check: a lane dropped a new audio file that the
  mirror will pick up while git does not carry it. Nothing in this folder can fix it, because the fix is
  a commit and the shared tree has hundreds of files from other lanes waiting. Q: for gamedev to commit
  this folder with the next delivery commit; `check_data.py` passes on the same tree.

## Which files here the commit carries, and why two do not

Committed: `score_pp_05.yaml`, `pp_05_small_ship.ogg`, `pp_05_small_ship_loop.json`,
`arrange_report.json`, `hook_report.json`, `measure_pp_05.json`, `melody_guard.json` and this note.
This folder carries no arranger of its own: `score_pp_05.yaml` is built by `tools/arrange.py`, which
is tracked and already measured by `tests/test_hook_score.py` and the arrange self tests.

`check_motif.py` and `measure_pp_05.py` are WORKING TREE TOOLS, deliberately not committed.
`check_motif.py` reads `pp_05_small_ship.mid` and `measure_pp_05.py` reads
`pp_05_small_ship.wav` (and its own copy of the folder path is absolute), and both of those are
masters the root `.gitignore` keeps out of the repository. A test for either could only skip when
the master is absent, and this project ruled that out after card t_50a290de: a test that passes by
skipping reads nothing and looks healthy at HEAD. They stay beside the master and run from the live
tree:

```
python assets/audio/pp_05_small_ship/check_motif.py
python assets/audio/pp_05_small_ship/measure_pp_05.py
```

## Three questions for the ear

1. The DPCM kick on beats 1 and 3 runs for all 60 s. It is what makes the loop a pulse rather than a pad,
   and it may read as too martial under the cabin and the log prompt. Flattening it needs an arranger
   recipe, not a score edit.
2. The corridor lift (section mean 3.1 dB above A, from the held triangle). Keep it as the walk's own
   colour, or flatline it so the walk and the deck sit at the same weight.
3. Hook score 58. Accept it for a bed, or state K twice as long so the meter has its two bar cell.

Rendered 2026-10-22. Score, MIDI and both codecs are in this folder; nothing outside it was written.
