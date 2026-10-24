# PP-03 "Harbor" v3, notes. Card AUTO-MUSIC-NEXT (t_fd8198d5), 2026-10-24 00:20 PDT.

v1 (`assets/audio/pp_03_harbor/`) and v2 (`assets/audio/pp_03_harbor_v2/`) are both untouched;
every file in this folder carries `_v3`. The registry row PP-03 still points at v1's OGG, which is a
gamedev edit and not a call this lane makes (Q: at the end).

## 1. The pick, and the score table before it (`tools/hook_score.py`, melody track `vrc6 pulse a`)

Every cue is scored on the newest build that exists for it, which is the method the last two cards
of this series used (the superseded builds are their own cards' baselines, not the cue's state
today). Of the six landed registry cues, PP-03 was the floor:

| cue | file scored | score | weakest criterion |
| --- | --- | --- | --- |
| **PP-03 harbor** | pp_03_harbor_v2.mid | **80 / 100** | motif coverage 31 percent |
| PP-01 title | pp_01_title_v6.mid | 83 | contour 2 of 12 |
| PP-02 drive | pp_drive_v2.mid | 83 | loop length 125 bars |
| PP-05 small ship | pp_05_small_ship_v4.mid | 91 | third return a copy |
| PP-06 Percy | percy_theme_v2.mid | 91 | contour 1 of 10 |
| PP-04 navy sailors | pp_04_navy_sailors_v3.mid | 100 | none |

Masters that exist in `assets/audio/` but are not rows of `data/audio.json`, scored for completeness:
pp_arrival 83, pp_boarding 90, hadrian_theme 81, pp_fight_states 79, pp_fight_calm 67. The last two
are a folder of state renders, and last card made the same call about them: the pick stays on a
registry cue.

For the record, scoring the landed masters instead of the newest builds puts PP-03 v1 at 63 and
PP-06 (percy_theme v1) at 61, but both are superseded by their own cards (PP-03 v2 80, Percy v2 91),
and the registry still points at those old files only because landing a new build is a gamedev edit.
On the ear ledger PP-03's landed master reads 27 of 60 in the sweep and 30 on the flash-lite judge
when measured again below, so both meters put the cue at or near the bottom.

## 2. Hook meter, v2 to v3

| criterion | v2 | v3 |
| --- | --- | --- |
| total | **80** | **100** |
| motif | 2 bars, 9 returns, 31 percent coverage | 2 bars, 10 returns, 66 percent |
| contour | 7 of 9 arch or pedal | 10 of 10 arch |
| leaps per motif | 1 | 1 |
| steps over leaps | 67 percent | 67 percent |
| third return | a copy (100 percent) | 80 percent the same |
| range | 15 semitones | 15 semitones |
| loop | 64 bars | 32 bars |
| melody notes | 216 | 107 |

## 3. Ear, one judge, two builds and one discarded round

| judge | file | hook | drums | tension | human | variety | structure | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | v2 (landed build) | 5 | 4 | 6 | 3 | 7 | 5 | **30** |
| gemini-3.5-flash-lite | v3 as shipped | 7 | 4 | 5 | 3 | 7 | 6 | **32** |
| gemini-3.5-flash-lite | v3 with two more inner-voice appoggiaturas (discarded) | 6 | 4 | 5 | 3 | 6 | 5 | **29** |

Reviews: `ear_reviews/pp_03_harbor_v2_20261024T071751Z.md`,
`ear_reviews/pp_03_harbor_v3_20261024T071744Z.md`,
`ear_reviews/pp_03_harbor_v3_20261024T071837Z.md`. All three calls were served on the first model in
the rotation, so no 429 fallback was needed and the three rows are comparable.

The third row is the honest cost of listening twice: the only difference between it and the shipped
build is two extra prepared appoggiaturas in the inner voice (bars 2 and 6 of three sections), and it
scored 3 points lower on criteria that were not changed (hook, variety, structure). That is the
ear's own noise floor of about 1 point per criterion (`assets/audio/EAR_SWEEP_2026-10-22.md`), so the
build was reverted to the arrangement the judge scored 32, one device per 8 bar section, which is
also the calmer of the two and fits the brief "low intensity under text".

## 4. What v3 changes

| change | reason | measure |
| --- | --- | --- |
| the cue is 32 bars (112.941 s at 68 bpm) instead of 64 (225.882 s) | the hook grammar accepts an 8, 16 or 32 bar loop and scored 64 at half credit; the cue is two bar statements now, so 32 bars is the length that holds them | loop length 3 of 6 to 6 of 6 |
| one two bar cell, stated ten times, in place of eight different 8 bar melodies | coverage was the weakest criterion at 31 percent; the cell is v2's motif H (rise A4 C5 D5 E5, leap down a fourth to B4, tonic A4) | coverage 31 to 66 percent, returns 9 to 10 |
| the third statement ends on the leading tone G#4, which bar 7 resolves to A4 | the third return has to carry an operation, and the operation is a real cadential one inside the same key | third return 100 to 80 percent the same |
| the close lifts a fourth to G5 at statement 11 and falls back by step | a second operation on a later return, so the eleventh statement is not a copy either | contour still 10 of 10 arch |
| the light section is written in halves (augmentation) over C major, with the flat sixth answer (H2) | contrast by density, which is the ear sweep's own note that arrangement is where the headroom is; it also keeps the light section's notes off the motif, which is what the coverage figure costs | light section 18 melody notes of 107 |
| one device per 8 bar section: the inner voice takes the ninth on the downbeat and resolves by step to the third | `knowledge/MUSIC-DISSONANCE.md` section 4 budget of 1 or 2 per 8 bars, risk 2, prepared and resolved, never on the first or last note of a statement (F1), never in a cadence bar (F2), 4 bars apart (F4) | section bars 5 of every section |
| the lead takes D#5 as a chromatic lower neighbour of E5 for one eighth in the light section | the only device in the lead, DIS-02, risk 1, weak beat, resolves up a semitone onto the note it left (F7 and F8 satisfied) | light section bar 22 |
| drums: the rung list changes the home pattern bar by bar inside an 8 bar cycle, the builder adds a one beat fill on every fourth bar and a two beat fill on every eighth, ghosts between; four home patterns (CLM-01, CLM-01, CLM-03, CLM-08) and a turnaround fill (FLX-10) into the seam | the card asks for variation every 4 and 8 bars; every rung and every fill is read by id from `data/drum_patterns.json`, nothing invented | 32 bars, no two bars identical |
| humanize: velocity table, two tick micro shift, three tick gate, duty steps between 0.25 and 0.125 per four bar block, plus `tools/humanize.py` over the whole file (763 notes in, 782 out, 100 percent of notes re-articulated on the frame grid, one grace note, one mordent, 16 section fills) | the card asks for humanize; the humanized MIDI is what renders | human 3, unchanged, which is the ear's ceiling for a tracker render |

Tempo stays 68 bpm. The card's "126 bpm family" is the balancer's generic phrasing; no spec pins a
tempo for PP-03 and v1 and v2 both sit at 68, which is what a low intensity cue under intro text
wants. Changing it to 126 would be a spec decision, not this card's, so it is left alone and named
here rather than silently overridden.

## 5. Checks run

- Hook meter, before and after: section 1 and section 2, from `hook_report_v3.json` and
  `python tools/hook_score.py assets/audio/pp_03_harbor_v3/pp_03_harbor_v3.mid`.
- Seam: `python assets/audio/pp_03_harbor_v3/check_seam_v3.py ... _v3.wav 32` gives loop point sample
  4980706 (112.9412 s), **seam jump 0**, last sample of the loop 0, first sample 0, no tail beyond
  the loop point, and the renderer reports `seam sample difference 0`. v2 loops the same way.
- Render: `tools/render_chip.py ... --loop-bars 32 --humanize`, 112.941 s, peak -1.00 dBFS, rms
  -16.02 dBFS, 4980706 samples, renderer v2 voice path (2A03 plus VRC6, eight tracks).
- Project gates, this PC, 00:22 PDT: `check_data` exit 0, `check_cues` exit 0 (landed 6, pending 11),
  `check_cleanroom` exit 0, `check_dissonance_rules` exit 0, `check_drum_patterns` exit 0,
  `check_music_style_bible` exit 0, and `pytest tests/test_audio.py tests/test_check_data.py` 62
  passed in 12.71 s.
- Dashes: this file carries no em dash, en dash, figure dash or horizontal bar.

## 6. Rounds (the card caps at 4)

1. Baseline: PP-03 v2, hook 80, ear 30 on flash-lite.
2. v3 build 1: the 32 bar form, one cell, the varied third return; hook 95 (coverage 59, third
   return still read as a copy), then 99 (contour dinged by the variation), then 100 once the
   variation was written as a leading tone that the next bar resolves.
3. v3 build 2: two extra inner-voice appoggiaturas; ear 29, lower than build 1 on unchanged
   criteria, so reverted to build 1.
4. Not used. The two remaining lows (drums 4, tension 5) are the ear's own ceiling for a calm cue:
   the sweep never hears drums above 5 in the set and names arrangement, not melody, as the
   headroom.

## 7. Files

`score_pp03_v3.yaml`, `build_pp03_v3.py` (the arranger, changed only in its default paths),
`check_seam_v3.py`, `pp_03_harbor_v3.mid`, `pp_03_harbor_v3_humanized.mid`,
`pp_03_harbor_v3.wav`, `pp_03_harbor_v3.mp3`, `pp_03_harbor_v3.ogg`,
`pp_03_harbor_v3_loop.json`, `arrange_report_v3.json`, `hook_report_v3.json`.

Committed: this note, the score, the OGG, the loop JSON, the two reports and the three ear reviews,
in three commits through the lane wrapper. The two python files and the MIDI, WAV and MP3 renders stay
in the folder untracked, which is how v2 and v3 of the other cues are kept: the suite gate refuses a
python change under `assets/audio` with no test mapped to it, and the renders are rebuilt from the
score by one command. `data/ear_ledger.csv` is appended by `tools/ear_critic.py` and was deliberately
not committed: the working copy of that file carries 76 uncommitted rows written by earlier lanes,
and a commit of it would carry their work with mine.

## 8. Q: for gamedev

Q: PP-03 is landed from `assets/audio/pp_03_harbor/pp_03_harbor.ogg` (v1, hook 63, ear 27). v3 is
100 on the hook meter against v2's 80 and up 2 on the same judge against v2 (30 to 32), and it is
half the length (112.9 s against 225.9 s), which is a change to how often the loop restarts under
the arrival text. Landing it, and whether the shorter loop is wanted, are your edits: `data/audio.json`
and the yyp entry, not this lane's.
