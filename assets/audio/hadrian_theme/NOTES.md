# Hadrian theme, MUS-HADRIAN, 2026-10-22

Cue: "Hadrian, the Data Centre". Score: `score_hadrian.yaml`. Check report: `score_check.json`.
Melody note list: `melody_lead.json`. Originality report: `melody_guard.json`.

## What exists

| File | What it is |
| --- | --- |
| `score_hadrian.yaml` | The composition, in `title_theme_v3/score_v3.yaml` schema plus two added keys: `second_voice` (notes for the fugue answer on vrc6 pulse b) and `meta.profile: hadrian` (selects the 4/4 recipe set in `tools/arrange.py`) |
| `score_check.json` | 19 checks on the score text, all pass (`tools/check_hadrian_score.py`) |
| `melody_lead.json` | The 46 note lead line, `[pitch, duration]`, for `tools/melody_guard.py` |
| `melody_guard.json` | Originality report against `Shared/projects/musikage`: PASS, longest identical interval run 3, best jaccard 0.0000 |
| `hadrian_theme.mid` | The arrangement: 8 voices, 9 tracks, ppq 480, 4/4, 92 bpm, sha256 `bd613653a925a88e4ce6c632cd0b9933b1b21050950f62c9b27ce1f26cb94366` |
| `arrange_report.json` | The arranger's own numbers: 32 bars, `beats_per_bar` 4, `midi_time_signature` "4/4", 83.478 s |
| `hadrian_theme.wav`, `.mp3` | The render (44.1 kHz mono 16 bit WAV, 192k MP3), peak -1.00 dBFS, rms -19.30 dBFS |
| `hadrian_theme_loop.json` | The loop: 32 bars, 83.478277 s, 3,681,392 samples, seam sample difference 0 |

Audio rendered 2026-10-22 02:30. Q1 is resolved; see below for the one musical question left.

## Numbers

- 32 bars, 4/4, 92 bpm, loop of the whole form, 83.478 s per loop (`32 * 4 * 60 / 92`).
- Form: `A` 8 + `A_fugue` 8 (the middle 8) + `A_second` 8 + `close` 8.
- Chords per phrase: Dm, Bb, Gm, A7, Dm, Bb, Eb, A7. Neapolitan Eb at bars 7, 15 and 23; the fourth phrase spends its chromatic move on the Picardy instead (bars 29 to 32 are D major).
- Lead (`vrc6 pulse a`) is silent in 14 of 32 bars: 2, 3, 4, 6, 10, 11, 13, 14, 18, 19, 20, 22, 26, 27.
- Motif H opens all four phrases: D5 C#5 (beats 1 and 2) rest (beat 3) A4 G#4 (eighths on beat 4). Bar 9, the card's check, reads D5 then C#5 as quarters: pass.
- H4, the fugue answer in the fourth, on `vrc6 pulse b` at bars 11 and 14 (middle 8) and 19 and 22: G5 F#5 then D5 C#5, same rhythm, same silence.
- Picardy: bars 29 to 32 are D, Bb, A7, D (all major), and the score asks for the cue's only sustained full triad at bar 32 (the arranger voices the root only there; see Q3).
- Voices: hum on `pulse 2` at duty 0.125 on D4 (MIDI 62) for all 32 bars; saw drone on the chord root, one note per bar; triangle bass on beat 1; noise hats on beats 1 and 3 in eighths; DPCM kick on beats 1 and 3 of every bar; `pulse 1` rests throughout. Vibrato is off on every voice.
- Arranged note counts (`arrange_report.json`): lead 46, answer on `vrc6 pulse b` 16 (bars 11, 14, 19, 22), hum 512 (16 sixteenths x 32 bars), saw 32, triangle 32, hats 96, kick 64, `pulse 1` 0. No note falls outside its voice range.
- Midi time signature "4/4", tempo 652174 us per quarter (92.000 bpm, re-read from the file), duration 83.478 s. Render: peak -1.00 dBFS, rms -19.30 dBFS, loop 32 bars = 83.478277 s (3,681,392 samples at 44.1 kHz), seam sample difference 0.
- Per voice render RMS (each voice rendered alone through the same renderer): lead 0.0329, triangle 0.0526, saw 0.0297, answer 0.0175, kick 0.0288, hats 0.0117, hum 0.0104, `pulse 1` absent. Every voice the score asks for is audible; nothing the score silences sounds.

## Checks run

```
python tools/check_hadrian_score.py        -> 19 passed, 0 failed
python tools/melody_guard.py assets/audio/hadrian_theme/melody_lead.json \
    "<workspace>/Shared/projects/musikage" \
    --json assets/audio/hadrian_theme/melody_guard.json   -> PASS, run 3, max jaccard 0.0000
python tools/arrange.py assets/audio/hadrian_theme/score_hadrian.yaml \
    --report assets/audio/hadrian_theme/arrange_report.json
    -> exit 0, 32 bars, beats_per_bar 4, midi_time_signature "4/4", 83.478 s
python tools/render_chip.py assets/audio/hadrian_theme/hadrian_theme.mid \
    assets/audio/hadrian_theme/hadrian_theme.wav --loop-bars 32 \
    --loop-json assets/audio/hadrian_theme/hadrian_theme_loop.json
    -> wav + mp3 + loop json, loop 83.478277 s (32 * 4 * 60 / 92)
```

The 3/4 path did not move. `tools/arrange.py` rebuilt the same bytes before and
after the 4/4 change for every waltz score: title theme v3 (`481bcb4e...`),
title theme v4 base (`60d25765...`) and the Percy score (`b6d25930...`) were each
identical from a copy of the file with the 4/4 edits reversed and from the new
file. `title_theme_v4_base.mid` on disk is still `60d25765...`, and
`title_theme_v3.mid` is still the pinned `403e9573...`. `percy_theme.mid` on disk
was rewritten at 02:29 by the concurrently running MUS-PERCY card (t_1e516faf),
not by this work; the old-vs-new builds above are the identity proof for it.

## Q1: resolved. arrange.py reads the bar length from the score

`tools/arrange.py` now takes the bar from `meta.time` (`score_geometry`: "4/4" =
4 beats, 8 eighths, 1920 ticks; "3/4" = 3 beats, 6 eighths, 1440 ticks; a score
with no `time` still reads as 3/4). `build_bars_v3` builds one chord entry per
beat, so a split chord "X|Y" is [X, X, Y] in 3/4 and [X, X, Y, Y] in 4/4, and the
bar's slots are checked against the signature instead of the module constant.
`Arrangement` carries `ticks_per_bar` per score, and the report's duration and
timing numbers use it.

The 4/4 recipes are selected by `meta.profile: hadrian` (the key was added to the
score's meta; nothing in the notes or chords changed and the 19 score checks
still pass). They are the ones the card fixed: sixteenth-note server hum on
`pulse 2` on MIDI 62, saw drone on the chord root one note per bar, triangle root
on beat 1 (a whole note per bar in `A_second`), hats in eighths on beats 1 and 3
(beat 1 only in `A_second` and `close`), kick on beats 1 and 3 of every bar,
`pulse 1` silent, `second_voice` on `vrc6 pulse b`, and no vibrato anywhere.

## Q2: the modal jolt at the loop seam (by ear)

Musical and cheap to answer by ear later: bar 32 ends on D major and the loop drops back to D minor in
bar 1. That is deliberate (the Picardy opens the door, the machine closes it again) but it is the one
place a listener may hear a modal jolt. If it reads as an error rather than as the point, the fix is one
chord: bar 32 to Dm, which loses the Picardy.

## Q3: bar 32's full triad is not voiced (by ear, one line to change)

The score's `close` texture line asks the saw to take the full D major triad at bar 32 (D3 A3 D4 F#4),
the only bar in the cue where a triad sounds. The MUS-ARR44 recipe set says "saw low drone on the chord
root one note per bar", so the arrangement keeps one root note there and the triad is not heard. The
Picardy still reads as major because the chords are D major. Say the word and the bar-32 triad goes in
as a four-note saw chord, no other bar changes.
