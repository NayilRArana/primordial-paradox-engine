# PP-04 "Navy Sailors" v3, notes. Card AUTO-MUSIC-NEXT (t_406c2001), 2026-10-23 20:26 PDT.

v3 is v2 plus two prepared dissonance devices in the release. v1
(`assets/audio/pp_04_navy_sailors/`) and v2 (`assets/audio/pp_04_navy_sailors_v2/`) are both
untouched; every file in this folder carries `_v3`.

## 1. The pick, and the score table before it (`tools/hook_score.py`, track `vrc6 pulse a`)

| cue | score | weakest criterion |
| --- | --- | --- |
| **PP-04 navy (v1, the landed master)** | **74 / 100** | contour 0 of 5 returns arch or pedal |
| PP-03 harbor v2 | 80 | motif coverage 31% |
| hadrian theme | 81 | contour 0 of 7 |
| PP-01 title v6 | 83 | contour 2 of 12 |
| pp_arrival | 83 | motif coverage 19% |
| PP-02 drive v2 | 83 | loop length 125 bars |
| pp_fight fight | 84 | motif coverage 37% |
| pp_boarding | 90 | loop length 14 bars |
| PP-05 small ship v4 | 91 | third return a copy |
| PP-06 percy v2 | 91 | contour 1 of 10 |

`pp_fight/` also holds `pp_fight_calm.mid` at 67, lower than every cue above, but it is a state
render of a folder that is not in `data/audio.json`; the pick stays on the registry floor, PP-04.

## 2. Hook meter, three versions

| criterion | v1 | v2 | v3 |
| --- | --- | --- | --- |
| total | **74** | **100** | **100** |
| motif | 2 bars, 5 returns, 38% coverage | 10 returns, 74% | 10 returns, 72% |
| contour | 0 of 5 arch or pedal | 10 of 10 arch | 10 of 10 arch |
| leaps per motif | 2 | 1 | 1 |
| steps over leaps | 82% | 91% | 91% |
| third return | a copy | 75% the same | 75% the same |
| range | 14 semitones | 12 | 12 |
| hook cell | 6 notes, 14 times | 6 notes, 20 times | 6 notes, 20 times |

## 3. Ear, three reads, two judges

| judge | file | hook | drums | tension | human | variety | structure | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash | v1 | 7 | 5 | 4 | 4 | 7 | 6 | **33** |
| gemini-3.5-flash | v2 | 7 | 5 | 4 | 3 | 6 | 6 | **32** |
| gemini-3.5-flash-lite | v2 | 7 | 5 | 4 | 3 | 6 | 6 | **31** |
| gemini-3.5-flash-lite | v3 | 7 | 4 | 5 | 3 | 7 | 6 | **32** |

The comparable pair is the last two, back to back on one judge: **v3 is up 1 (31 to 32), with
tension 4 to 5 and variety 6 to 7 against drums 5 to 4.** The first flash read of v3 could not be
had: `gemini-3.5-flash` answered 429 with its free tier daily quota spent ("retry in 3h40m"), so the
model was rotated to `gemini-3.5-flash-lite` per the card, and v2 was read on that judge too so the
comparison stays on one listener.

Every axis move here is at the ear's own noise floor (1 point per criterion,
`assets/audio/EAR_SWEEP_2026-10-22.md`): the tension move is the one that matches what was actually
changed, and the drums move is in the wrong direction and is not explained by the build (the kit is
bar for bar v2's). Reviews: `..._v3_20261024T031925Z.md`, `..._v2_20261024T031937Z.md`.

## 4. What v3 changes

| change | grammar | measure |
| --- | --- | --- |
| bar 12 (Dm): held D5, then E5 as a one eighth appoggiatura, then back to D5 | preparation D5, dissonance E5 (the ninth), resolution D5 | one device per 8 bars, risk 1 colour, within the 1 to 2 per 8 bars policy |
| bar 16 (A7): E5, then F5 as a one eighth flat thirteenth, then back to E5 and the leading tone C#5 | preparation E5, dissonance F5 (b13), resolution E5 | same budget, the second device of the phrase |
| nothing else | motif N, the 4 and 8 bar kit rungs, the release chords, the tail and the bass are v2's | hook meter 100 unchanged, coverage 74 to 72 percent |

v1 spent none of the dissonance budget: its 6 chromatic melody notes are all C#5, the third of A7,
so they are chord tones, not devices. v3 spends two devices in the release, which is the tune's
relaxed half and the right place for them (`knowledge/MUSIC-DISSONANCE.md` section 2: a dissonance
is tasteful when the listener can predict the resolution).

## 5. Tempo, form, loop

D minor with the Dorian Bb, 4/4, 176 bpm, 32 bars, 43.636 s, loop bars 1 to 28, tail 29 to 32. The
tempo is unchanged on purpose: the card's "126 bpm family" is the waltz family (PP-01 is the 126),
and PP-04 is the fight cue whose 45 to 60 s fight is timed on 176; moving it would move every bar
boundary in the score and the fight timing with it. Q: for gamedev if that is not how the spec
reads.

`pp_04_navy_sailors_v3_loop.json`: 32 bars, 1922015 samples, peak -1.00 dBFS, RMS -16.47 dBFS,
seam sample difference 0. The junction the game uses is bar 28 into bar 1, so `check_seam_v3.py`
measures that one: loop point sample 1683818 (38.1818 s), **seam jump 0**, 10 ms either side gated,
and v1 and v2 measure identically, so v3 loops the way the master does.

## 6. Rounds run (the card's cap is 4)

1. Baseline: v1, hook 74, ear 33.
2. v2 build 1: motif reshaped, coverage work, kit in rungs; hook 88 (the finder fell back to a 1 bar
   motif, contour read 0).
3. v2 build 2: statements realigned so the 2 bar motif matches 10 times; hook 100; ear 32.
4. v3: two prepared devices in the release; hook 100; ear 32 on flash-lite against v2's 31.

Quota: 4 ear calls this run, 3 served (2 flash, 2 flash-lite counting the pair), 1 refused with 429
and rotated; no other model marked exhausted. The key was read from HKCU\Environment inside the
process, never printed, never written to a file.

## 7. Files

Committed: this note, `score_pp04_v3.yaml`, the OGG, the loop JSON and the reports below. The python
files (`build_pp04_v3.py`, `check_seam_v3.py`) sit in the folder uncommitted because the suite gate
refuses a python change under `assets/audio` with no test mapped to it; see v2's NOTES section 7.

- `pp_04_navy_sailors_v3.mid`, `_v3_humanized.mid`, `_v3.wav`, `_v3.mp3`, `_v3.ogg`
- `pp_04_navy_sailors_v3_loop.json`, `hook_report_v3.json`, `hook_render_v3.json`,
  `pp_04_score_report_v3.json`, `melody_lead_v3.json`, `score_pp04_v3.yaml`, `build_pp04_v3.py`,
  `check_seam_v3.py`

## 8. Q: for gamedev

Q: PP-04 is landed from `assets/audio/pp_04_navy_sailors/pp_04_navy_sailors.ogg` and
`data/audio.json` still reads `"placeholder": true`. v3 is 100 on the hook meter against 74 and up
1 on the ear against v2 on the same judge; landing it is a registry and yyp edit you own, not a call
this lane makes.
