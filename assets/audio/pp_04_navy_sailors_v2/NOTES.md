# PP-04 "Navy Sailors" v2, notes. Card AUTO-MUSIC-NEXT (t_406c2001), written 2026-10-23 20:17 PDT.
#
# Round 4 of this card moved on to `assets/audio/pp_04_navy_sailors_v3/`: v3 is v2 plus two prepared
# dissonance devices in the release, and it kept the hook meter at 100. v2 stays as the round the
# meter was won in.

The cue picked is PP-04 because it is the floor of the hook meter of every cue in the registry,
measured on the same melody track (`vrc6 pulse a`): **74 of 100**, with PP-03 harbor next at 80. The
ear also had it at the soft end (33 of 60 on `gemini-3.5-flash`).

v1 (`assets/audio/pp_04_navy_sailors/`) is untouched. This folder is a new version suffix and every
file in it carries `_v2`.

## 1. The score table before the pick (`tools/hook_score.py`, track `vrc6 pulse a`)

| cue | file | score | weakest criterion |
| --- | --- | --- | --- |
| PP-04 navy | `pp_04_navy_sailors.mid` | **74 / 100** | contour 0 of 5 returns arch or pedal |
| PP-03 harbor v2 | `pp_03_harbor_v2.mid` | 80 | motif coverage 31% |
| PP-01 title v6 | `pp_01_title_v6.mid` | 83 | contour 2 of 12 |
| pp_arrival | `pp_arrival.mid` | 83 | motif coverage 19% |
| PP-02 drive v2 | `pp_drive_v2.mid` | 83 | loop length 125 bars |
| hadrian theme | `hadrian_theme.mid` | 81 | contour 0 of 7 |
| PP-05 small ship v4 | `pp_05_small_ship_v4.mid` | 91 | third return a copy |
| PP-06 percy v2 | `percy_theme_v2.mid` | 91 | contour 1 of 10 |
| pp_boarding | `pp_boarding.mid` | 90 | loop length 14 bars |
| pp_fight fight | `pp_fight_fight.mid` | 84 | motif coverage 37% |

`pp_fight/` also holds a calm state that scores 67 (`pp_fight_calm.mid`, contour 0 of 2). It is not
in `data/audio.json`: it is a state render of the fight folder, not a registry cue, so the pick
stays on the registry floor. That is the one judgement call in this note.

## 2. PP-04 before and after

| criterion | v1 | v2 |
| --- | --- | --- |
| total | **74 / 100** | **100 / 100** |
| motif | 2 bars, 12 notes, 5 returns, 38% coverage | 2 bars, 12 notes, 10 returns, 74% coverage |
| contour | 0 of 5 arch or pedal | 10 of 10 arch |
| leaps per motif | 2 | 1 |
| steps over leaps | 82% | 91% |
| third return | 100% the same (copy) | 75% the same |
| range | 14 semitones | 12 semitones |
| hook cell | 6 notes, repeated 14 times | 6 notes, repeated 20 times |

## 3. Ear, before and after (same judge, back to back)

| read | file | hook | drums | tension | human | variety | structure | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| before | `pp_04_navy_sailors.mp3` | 7 | 5 | 4 | 4 | 7 | 6 | **33** |
| after | `pp_04_navy_sailors_v2.mp3` | 7 | 5 | 4 | 3 | 6 | 6 | **32** |

Judge `gemini-3.5-flash`, one call each, 03:14 and 03:15 UTC, reviews
`assets/audio/ear_reviews/pp_04_navy_sailors_20261024T031441Z.md` and `..._v2_20261024T031555Z.md`.

**The ear went down 1 point, which is its noise floor** (`assets/audio/EAR_SWEEP_2026-10-22.md`:
1 point per criterion). It is not claimed as a win, and the review does not describe v2's build:
it hears "a plain kick-snare-hat grid with no fills" while v2 has a 4 bar kick answer, an open hat
on the third bar of every rung, a tom fill on bars 8, 16 and 24 and crashes on 1, 9, 17, 25, 29 and
32; it hears "no delayed vibrato" while the human pass wrote vibrato on the 5 notes long enough for
it (the release only) and articulation on every one of the 162 lead notes.

What the review is right about, measured: the cue's melody is 162 notes of mostly one to two eighth
lengths, so only 5 notes can carry vibrato, and that is why the human axis sits at 3 or 4 no matter
what the kit does. Fixing that means longer notes in the hook, which is a different hook.

## 4. What changed, and the measure for each

| change | measure | check |
| --- | --- | --- |
| motif N reshaped from the neighbour turn into a step ladder that leaps a fourth to A5 and walks back down to the leading tone | contour 0 of 5 to 10 of 10 arch, leaps 2 to 1, steps 91% | `hook_report_v2.json` |
| the third statement (bars 5 and 6) answers on G5 and passes through Bb4 and A4 instead of holding Bb | third return 100% the same to 75%, still a return | `hook_report_v2.json` |
| the statements now run at bars 1, 3, 5, 7, 17, 19, 21, 23, 25 and 27 (v1 varied bars 3, 4, 7 and 8 by transposition, which broke the match) | coverage 38% to 74%, returns 5 to 10 | `hook_report_v2.json` |
| bar 4 and bar 8 land the A7 on C#5 to A4, the leading tone gesture, so the A7 colour and the arch agree | contour 10 of 10, chromatic colour kept | `hook_report_v2.json` |
| kit written in rungs: 4 bar rung (hat accents on the beat, open hat on the third bar, a soft snare answer in the second bar) and 8 bar rung (three tom run plus a snare pickup on bars 8, 16 and 24, crashes on 1, 9, 17, 25, 29, 32) | 32 bars, 270 noise hits, 4 noise pitches | `build_pp04_v2.py`, render log |
| human pass: articulation on 162 of 162 lead notes, vibrato on 5, 1 grace note, 1 mordent, fills before the section changes at bars 9, 17, 25 and 33 | `render_chip --humanize` | render log |

Only the lead and the kit changed. The power chord, the fifth under it, the saw, the triangle bass
and the release's chords are v1's notes, untouched, so no part is invented.

The dissonance budget, per `knowledge/MUSIC-DISSONANCE.md` (1 to 2 devices per 8 bars, 3 to 6
percent of notes): v1 carried 6 chromatic melody notes, all of them C#5, and every one is the third
of the A7 chord, so v1 spent none of its budget on a device. v2 keeps the same 6, still chord tones,
and adds no new device. It is in band on rate and short on devices: the honest next lever for the
tension axis is two prepared devices in the release, which is round 3 work, not this build.

## 5. Form, tempo, loop

D minor with the Dorian Bb, 4/4, 176 bpm, 32 bars, 43.636 s, loop bars 1 to 28, tail 29 to 32 to
resolve the fight. The tempo is unchanged on purpose: the card's "126 bpm family" is the waltz
family (PP-01 is the 126), and PP-04 is the fight cue whose 45 to 60 s fight length is built on
176. Changing it would move every bar boundary in the score and the fight timing with it.

`pp_04_navy_sailors_v2_loop.json`: 32 bars, 1922015 samples, peak -1.00 dBFS, RMS -16.49 dBFS,
seam sample difference 0. The junction the game uses is bar 28 into bar 1, which that field does not
reach, so `check_seam_v2.py` measures it: loop point sample 1683818 (38.1818 s), seam jump 0, 10 ms
either side gated, and v1 measures the same way, so the loop behaves like the master it replaces.

## 6. Rounds run

1. Baseline: v1, hook meter 74, ear 33 (gemini-3.5-flash).
2. v2 build 1: motif reshaped, coverage work, kit in rungs. Hook meter 88 (the finder fell back to
   a 1 bar motif, so contour read 0).
3. v2 build 2: the statements aligned so the 2 bar motif matches 10 times, hook meter 100. Ear 32.
   Stopped after this round: the meter is full, and the ear is flat at its floor with the only
   measurable defect left (short melody notes, no vibrato room) being a change to the hook itself.

Quota: two ear calls, both served by `gemini-3.5-flash`, no model marked exhausted. The key was read
from HKCU\Environment inside the process, never printed, never written to a file.

## 7. Files

Committed with the build: this note, `score_pp04_v2.yaml`, the OGG, the loop JSON and the reports
below. The two python files (`build_pp04_v2.py`, `check_seam_v2.py`) sit in the folder uncommitted:
the suite gate refuses a python change under `assets/audio` because no test maps to it
(`gate: primordial-paradox: UNMAPPED ... A source change nothing measures is refused`), and adding
an exception to `suite_config.json` is not this lane's file. Q: for gamedev, whether the build
scripts for a cue belong in the tracked tree.

- `pp_04_navy_sailors_v2.mid`, `_v2_humanized.mid`, `_v2.wav`, `_v2.mp3`, `_v2.ogg`
- `pp_04_navy_sailors_v2_loop.json`, `hook_report_v2.json`, `hook_render_v2.json`,
  `pp_04_score_report_v2.json`, `melody_lead_v2.json`, `score_pp04_v2.yaml`, `build_pp04_v2.py`,
  `check_seam_v2.py`

## 8. Q: for gamedev

Q: PP-04 is landed from `assets/audio/pp_04_navy_sailors/pp_04_navy_sailors.ogg` and
`data/audio.json` still says `"placeholder": true` for it. v2 scores 100 on the hook meter against
74 and is flat on the ear, so whether it replaces the master is a registry edit you own, not a call
this lane makes.
