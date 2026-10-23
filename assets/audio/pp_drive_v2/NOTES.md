# PP-DRIVE v2, the weakest cue rebuilt by the hook score. Card AUTO-MUSIC-NEXT (t_6a70f6e8)

Written 2026-10-23 for Primordial Paradox, musician lane. v1 (`assets/audio/pp_drive/`) is
untouched and still the version the task cards before this one delivered; everything below is new
files in `assets/audio/pp_drive_v2/`.

## 1. Why this cue was the target

The card asked for the cue or theme with the lowest ear or hook score. Measured, not remembered:

| cue | ear total of 60 (data/ear_ledger.csv, latest row) | hook score of 100 (tools/hook_score.py, today) |
| --- | --- | --- |
| pp_drive | never scored, no row | 61 |
| percy_theme | 33 | 61 |
| pp_03_harbor | never scored | 63 |
| title_theme_v2 | 32 | 63 |
| title_theme (v1) | 27 | 71 |
| pp_05_small_ship | never scored | 67 |
| hadrian_theme | 35 | 81 |
| title_theme_v5 | 35 | 73 |

pp_drive is the delivered cue with the lowest hook score, and it is also the only current cue with
no ear review at all. `title_theme` v1 has the lowest ear total (27) but it is three versions
behind, and the ear sweep itself says it "needs the least of his time"; rebuilding a superseded
render would not have moved the game. The other low hook score, percy at 61, is a bouncy boss
theme the ear reads as fine (33 of 60), and its weakness is the same motif-coverage item, so the
fix here is the one that transfers.

Full before table, every MIDI in the folder, printed by the workspace script
`score_table.py`: hadrian 81, pp_04 74, title_theme_v5 73, title_theme v1 71, v4_medium 70,
v4_spicy 68, v4_subtle 68, pp_05 67, pp_03 63, title v2 63, v3 65, percy 61, pp_drive 61.

## 2. What changed

v1's lead was arpeggios: three notes a bar, no two bar cell, and its own NOTES.md recorded 46 of
100 with motif coverage at 13 percent. v2 keeps everything the film depends on and rebuilds the
lead as a hook.

- Harmony, section lengths (A 25, B 34, A_return 66), 3/4, 126 bpm, the 125 bar grid and the shot
  map are v1's, unchanged. The render is 178.563 s, the same length as v1 to the sample.
- The lead is one two bar cell: C5 D5 E5 G5 then A5 G5 E5 A4. Durations 2 1 1 2 | 1 1 1 3, an arch
  contour, six of seven intervals steps, one leap (E5 down a fifth to A4), range 12 semitones. Its
  five pitch classes (A C D E G) are diatonic to every chord in the cue except the two dominant
  sevenths, so the same eight notes sit inside all three sections and count as one returning hook.
  `snap()` repairs the flat ninth over E7 and B7 and touches nothing else.
- The leitmotifs are stated where CHARACTER-BIBLE puts them, on the literal bars v1 used: K at 5,
  6 and 74, inverted at 13, augmented at 70, 71, 124, in C at 34; Z at 26 and 28; P at 60, 61,
  64, 65 and 98, moved to A minor at 114 and 115; H at 17, 18, 38, 39, 94, 95 and 123 with its
  rest preserved.
- Dissonance, by `knowledge/MUSIC-DISSONANCE.md`: DIS-02, the chromatic lower neighbour, as the
  sharp five for one eighth, resolving up a semitone, in bars 11, 45, 63, 83, 101 and 117 (2 per
  8 bars at most, which is inside the document's 1 to 3 rate), plus the flat six to five the
  cell's last note makes every time it returns.
- Drums, written by `drive_v2.py` after the arrange step, every 4 and every 8 bars: a ghost note
  on the and of beat 1 every 4 bars, a heavier beat 3 hat every 4th bar, a three note roll to end
  every 8 bar span, alternating 8 bar spans with a hard hat on beat 1, a snare under the kick on
  every eighth bar of the return, and a two bar hole at 24 to 25, 58 to 59 and 124. Noise went
  from 289 arranged hits to 382; dpcm from 66 to 73.
- Humanize: `render_chip.py --humanize`, chip legal, every note ends on a frame boundary.

## 3. The score table, before and after

| item | v1 (pp_drive) | v2 (pp_drive_v2) |
| --- | --- | --- |
| hook_score | 61 (46 in v1's own record) | 83 |
| motif coverage | 13 percent | 63 percent, passes at 20 of 20 |
| motif returns | 7 | 37 |
| hook cell | yes | yes, 6 note rhythm repeated |
| steps over leaps | 0 percent of 3 sampled intervals | 67 percent |
| range | 20 semitones | 17 semitones, inside the octave and a half |
| contour | fails | 30 of 37 returns arch or pedal |
| leaps per motif | 0 | 0 in the window the tool picks (the cell itself has the one leap, E5 to A4, and the tool's chosen window is the first half of it) |
| third return | copy | 89 percent the same, still a copy by the tool's rule |
| loop length | 0 of 6, 125 bars | 0 of 6, unchanged, because the film is 178 s (see section 5) |

## 4. The checks, with the numbers printed

- `tools/arrange.py` on the v2 score: exit 0, sections A 25 / B 34 / A_return 66, first bars 1, 26,
  60, `"out_of_range": []`, eight tracks.
- `tools/render_chip.py`: 178.563 s at 44.1 kHz, peak -1.00 dBFS, rms -15.93 dBFS, renderer v2.
  Humanized: 178.550 s, peak -1.00 dBFS, rms -16.42 dBFS, different bytes.
- Loop seam, `seam_check.py` in this folder, on the rendered wav: A to A join steps 288 of a
  11,666 maximum step inside the section (0.02), B to B join steps 1,129 of 18,586 (0.06). Both
  seams are quieter than the material's own transitions, so neither clicks.
- Chip limits: eight voices, 2A03 pulse 1, pulse 2, triangle, noise, DPCM plus VRC6 pulse A, pulse
  B and saw. Noise and DPCM hold one pitch at a time: the drum pass writes one hit per eighth slot
  and every added hit was checked against the arranged notes on the same channel. No note outside
  its voice range (`out_of_range: []`).
- `knowledge/MUSIC-STYLE-BIBLE.md`, `CHARACTER-BIBLE.md` and `MUSIC-HOOK-GRAMMAR.md` are the
  technique sources; no published tune is quoted or transcribed here.

## 5. Not done, and why

- **The ear loop did not run.** `python tools/ear_critic.py --dry-run
  assets/audio/pp_drive/pp_drive.mp3` reports `key: absent from GEMINI_API_KEY, a real run would
  refuse`, and the Windows user environment does not define `GEMINI_API_KEY` either (checked by
  length only, never printed, no key file opened). So the four round ear loop the card asks for
  could not start, and no rotation across Gemini models happened. What exists instead is the hook
  score loop: v1 at 61, the degree transposition at 73, the fixed pitch cell at 83, with the
  previous file kept at every step (v1 itself is the previous version, untouched).
  **Q: for gamedev / Nayil:** the ear loop needs a session that has `GEMINI_API_KEY` in its
  environment. Once one exists:
  `python tools/ear_critic.py --model gemini-3.5-flash assets/audio/pp_drive_v2/pp_drive_v2.mp3`,
  then rotate to `gemini-3.5-pro` and the medium variant, and re-score
  `pp_drive_v2_humanized.mp3` against it.
- **Loop length stays 125 bars.** hook_score wants 8, 16 or 32 bars. The shot list and the film
  are 178 s and the cut bar grid is gamedev's spec, so changing the bar count would break every
  cut bar on `data/title_timing.json`. The sectional loops (A to A, B to B) are the cue's real
  loop, and section 4 measures them clean.
- **Third return is still 89 percent the same.** The variation bar (V) exists in the plan, but the
  tool's chosen window is the two bar phrase that starts one bar early, so its third occurrence
  does not land on a V bar. A fix would mean moving V to wherever the tool's third hit falls;
  left as the next round's first task rather than guessed at.
- No edit to `data/audio.json`, scenes, art or the engine; the registration question from v1's
  NOTES.md section 6 (Q1) is still open and still gamedev's call.

## 6. Files

| File | What |
| --- | --- |
| `score_pp_drive_v2.yaml` | the score: same meta and chords as v1, new lead, v2 motif notes |
| `pp_drive_v2.mid` | arranged MIDI, v2 lead, drums rewritten by `drive_v2.py` |
| `pp_drive_v2.wav` / `.mp3` / `.ogg` | render, 178.563 s |
| `pp_drive_v2_humanized.wav` / `.mp3` | humanized render, 178.550 s |
| `pp_drive_v2_loop.json`, `pp_drive_v2_humanized_loop.json` | loop and voice maps from the renderer |
| `arrange_report_v2.json` | arranger self check |
| `hook_report_v2.json` | the hook grammar reading, 83 of 100 |
| `seam_check.py` | the loop seam measurement in section 4 |
| `tools/drive_v2.py` | how the lead and the drums are built, and how to rebuild them |
