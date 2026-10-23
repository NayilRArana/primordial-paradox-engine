# PP-01 title theme, landed build: v5

Card R37 (TITLE-V5), step S1 audio of ROADMAP-2026-10-23.md. This folder is the asset the
title screen plays. The file is `pp_01_title.ogg` (with `.mp3`, `.wav` and `.mid` siblings),
74.266803 s, loop 48 bars from bar 5, loop seam 0 samples.

## 1. The comparison, and the winner

Two candidates were in play, both of them already rendered and measured:

- v5: fills on the four and eight bar lines, section velocity levels, a hole at bar 44
  (`assets/audio/title_theme_v5/`).
- v4 medium: the build the ear scored 7/5/6/4/7/6 in the 2026-10-22 sweep
  (`assets/audio/title_theme_v4/title_theme_v4_medium.mp3`). v5 is v4's arrangement plus a
  drum ladder and section levels, so this is a kit comparison, not a tune comparison.

`measure_candidates.py` scores both on the four axes the handoff card names, from the two
final humanized MIDIs and the reports each build's own tools wrote. It only awards an axis
when a named indicator clears its stated noise floor; otherwise the axis is a tie.

| axis | v5 | v4 medium | winner |
| --- | --- | --- | --- |
| hook | 73 of 100 on hook_score, 137 melody notes | 70 of 100, the same 137 notes | tie |
| drums | 25 filled bars, change rate 0.92, 12 aligned four bar blocks | 13 filled bars, change rate 0.77, 12 blocks | v5 |
| tension | 1.69 devices per 8 bars, 2 risk 3, 10 of 11 verified in the MIDI | 1.54 per 8 bars, 2 risk 3, 10 of 10 verified | tie |
| human | 102 distinct velocities, 20 vibrato notes, short notes 0.13 | 94 distinct velocities, 21 vibrato, short notes 0.15 | v5 |

Winner: **v5, by 2 of 4 axes**. Hook is a tie because the lead voice is the same melody in
both builds (the same 137 note sequence, snapped to the sixteenth grid), so the three point
hook score gap is the humanizer moving velocities and lengths, not a better tune. Tension is a
tie because both builds sit inside the 1 to 2 devices per eight bar band the dissonance policy
asks for.

The thinnest part of the result, said plainly: the human axis is won on one indicator, eight
more distinct velocities out of 94 to 102, which is the smallest indicator in the table. The
drum axis win is the real one (25 filled bars against 13, a change rate of 0.92 against 0.77),
and it is the difference the v5 build was written to make.

The ear could not break the tie either. Its own rows for the two builds are identical:

| build | source row | hook | drums | tension | human | variety | structure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v4 medium | `data/ear_ledger.csv` 2026-10-22T14:34:29Z | 7 | 5 | 6 | 4 | 7 | 6 |
| v5 round 1 | `data/ear_ledger.csv` 2026-10-22T23:17:13Z | 7 | 5 | 6 | 4 | 7 | 6 |

## 2. The second listen did not run

The card asks for a re-listen pass with a second model. It did not happen, and this is the
evidence rather than an excuse:

    python tools/ear_critic.py --dry-run assets\audio\pp_01_title\pp_01_title.ogg
    key:     absent from GEMINI_API_KEY, a real run would refuse

`GEMINI_API_KEY` is not set on this machine (checked in the process environment, in the user
environment through `reg query HKCU\Environment` and `HKLM` system environment, and in the
Hermes config, where it appears only as a comment), and no other audio capable model key is
present. The ear's own round 1 rows are quoted above, so the pick does rest on ear evidence
from both builds, but no second model heard the landed file. The disagreement record is
therefore: second listen unavailable, winner decided by measurement plus the identical ear
rows, and one ear pass on `pp_01_title.ogg` is still owed the next time a key is on the
machine.

## 3. Checks, with their output

| check | result |
| --- | --- |
| duration, at least 74 s (ROADMAP S2) | `pp_01_title.ogg` 74.266803 s, `.wav` 74.266803 s, `.mp3` 74.267188 s, PASS |
| loop seam, needs below -60 dBFS | 0 samples, -90.31 dBFS, PASS (from the landed loop report) |
| peak | -1.00 dBFS, which is the renderer's own soft limiter target, no clipping |
| loop report paths | every path rewritten to `pp_01_title.*` by `land_asset.py`, no build folder left in the file |
| copy integrity | each landed and archived file hash checked against its source by sha256 |
| style bible check | `python tools/check_music_style_bible.py` prints 11 PASS lines and `RESULT: PASS`, and `data/music_recipes.json` comes back byte identical, so this run changed no shared file |
| NES rules | 8 voices exactly: 2 pulses, triangle, noise and DPCM on the 2A03, 2 pulses and saw on the VRC6, which is the bible's chip; every voice above -50 dBFS rms in the loop report, no silent and no clipping voice |
| RULE 0 | nothing outside `assets/audio/pp_01_title/` was written; `data/audio.json` is R36's file and was not touched |
| long dashes | none in this file or in the two scripts beside it |

## 4. One claim in the v5 notes is wrong, and here is the correction

`assets/audio/title_theme_v5/NOTES.md` lists 11 applied dissonance devices and says the
arranger records every one. Measured against the rendered MIDI, 10 of the 11 devices are
really there. The missing one is bar 42 beat 1.0, `DIS-03` on pulse 1, the displacement
74 to 70 back to 69: `title_theme_v5_pre.mid` has the 70 at bar 42 slot 0, and the humanized
`title_theme_v5.mid` (and so this render) does not. The humanizer dropped that note; the
arrange report still counts it.

This does not move the tension axis (both builds stay inside the policy band) and it is not
audible as a mistake, but the delivered record overstates the dissonance count by one, and the
landed file is one device short of what its own report says. It is written here so the next
person does not have to find it twice.

## 5. What is in this folder

| file | what it is |
| --- | --- |
| `pp_01_title.ogg`, `.mp3`, `.wav` | the landed render, byte for byte the v5 build that was measured |
| `pp_01_title.mid` | the humanized MIDI that produced it |
| `pp_01_title_loop.json` | the loop report, paths rewritten to the landed names |
| `pp_01_title_alt_v4_medium.ogg`, `.mp3` | the losing candidate, kept beside the winner under its own build name |
| `pp_01_title_alt_v4_medium_loop.json` | its loop report, same rewrite |
| `measure_candidates.py`, `measure_candidates.json` | the four axis comparison and its numbers |
| `hook_v5.json`, `hook_v4_medium.json` | the hook scorer reports the comparison quotes |
| `land_asset.py` | the copy, archive and path rewrite step, with the hash check |
| `NOTES.md` | this file |

The archive suffix is `alt_<build>`: the folder did not exist before this card, so there was no
previous name here to keep. The build name is the archive name because that is how the other
audio folders in this repository keep older renders (`title_theme_v4_medium`, `pp_drive_v2`).

## 6. For gamedev: the asset name does not match yet

`data/audio.json` still says PP-01 is `pp_01_wessex_lane`, and its title is "Wessex Lane,
Move-In Day". This card's output path is `pp_01_title/`, so the file landed as
`pp_01_title.ogg`. `game/scripts/pp_audio/pp_audio.gml` builds its path as
`music/<asset>.ogg`, so R36 (CUE-WIRING, the only card that owns `data/audio.json`) has to
decide one of two things: set PP-01's asset to `pp_01_title` and its title to the title theme,
or rename this folder. Nothing in this card touched `data/audio.json`.

## 7. The commit, which is not done

`tools/check_build_inputs.py` names this folder as a build input source and wants the two ogg
files committed:

    UNCOMMITTED SOURCE projects/primordial-paradox/assets/audio/pp_01_title/pp_01_title.ogg
    UNCOMMITTED SOURCE projects/primordial-paradox/assets/audio/pp_01_title/pp_01_title_alt_v4_medium.ogg

The commit was attempted three times and refused every time because another git process in the
shared repository holds `<workspace>/Shared/.git/index.lock` (present at 19:14 and
still present at 19:20 local, while HEAD moved under it). That lock was not removed, because
deleting another lane's lock is how a shared index gets corrupted. So the files are on disk and
tracked by nothing yet: the next run, or any lane with the lock free, should commit
`assets/audio/pp_01_title/` before the build input gate is read as green. The two lines above
are the whole gate item for this card; `datafiles/streams/pp_drive.ogg` and
`title_theme_v5.ogg` are other lanes' items and are not this card's.

## 8. What Nayil has to decide by ear


1. Whether the title theme should be PP-01 at all, since PP-01 is currently the first town
   cue ("Wessex Lane, Move-In Day") and this is the title screen theme. That is gamedev's
   spec question, but it is a listening question too: if both are wanted, the town cue needs
   its own card and this file needs its own cue id.
2. Whether the drum win is audible to him: v5 adds fills on the four and eight bar lines and
   lifts and drops section levels, and 12 more filled bars is a measurement, not a promise
   that it sounds better.
3. Whether to spend the one ear pass this folder is owed on `pp_01_title.ogg` once a key is
   available, because that is the only check on this page that did not run.
