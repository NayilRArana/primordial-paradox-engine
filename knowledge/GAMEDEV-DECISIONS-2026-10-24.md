# Primordial Paradox decisions, 2026-10-24 (second file of the day): the TALK capture, and the drive's grid

Three rulings this card needed, and the two engine bugs the work uncovered. Written after the capture passed, so every
number here is quoted from a run rather than intended. Card **t_27aa179e** ("make the TALK path provable from outside
the game"), child of the first-fight capture card.

`D15` to `D17` and the two bugs are the TALK capture. `D18` and `D19`, at the bottom of this file under their own
heading, are the drive's bar lattice and which of its two artifacts ships (card **t_ce63cb65**, raised by the review
t_3cca8576 of R21a and R21b). They live in this file because `knowledge/DRIVE-SHOT-LIST.md`, `pp_drive.gml` and
`obj_pp_game/Create_0.gml` all already cite `knowledge/GAMEDEV-DECISIONS-2026-10-24.md` by path.

---

## D15. The TALK log lines live in the code that owns each fact, and they are `PP:` lines

Six lines, each written by the function that already knows the answer, so no caller has to be trusted:

| line | written by | what it proves |
|---|---|---|
| `PP: battle menu, turn N, cursor C, enemy hp H/M` | `pp_battle_step_menu`, once per phase entry | a press lands on the list, and which cursor it will be read against |
| `PP: command <key>, turn N, enemy <id>, enemy hp H, party hp P` | `pp_battle_begin_action`, before the command's body | the command the player chose, and the enemy's bar as the press found it |
| `PP: talk open, N options, mercy M, trust T` | `pp_talk_begin` | the panel is open and which meter it opened on |
| `PP: talk pick, option I, effect E, mercy M, trust T` | the panel's confirm in `pp_talk_step` | the option, the effect and the meter it actually moved to |
| `PP: fight result <word>, turn N, enemy <id>, enemy hp H/M` | `pp_battle_enter_result` | the outcome word the panel prints |
| `PP: talk bake, R rows kept of T read, F fight keys, V npc keys` | `pp_talk_bake`, once per run | the talk table loaded, and its shape |

Why here and not in a driver: a line written by the driver only proves the driver ran. These are written by the state
machine, at the moment the state changes, so a capture that reads them is reading the game and not a schedule.

Why `PP:` and one line per event: the log already has 200+ `PP:` lines with that shape, `tools/capture_first_fight.py`
already greps them, and one line per event is what makes a count meaningful (`talk: 3, fight: 0`).

**The `battle menu` line is per phase entry, not per step** (`phase_steps == 1`). A line per step would be 60 lines a
second and would make the log unreadable; a line per turn is what a driver can wait on.

---

## D16. The capture driver presses only where the log says a press lands, and it holds where a frame has to see it

`tools/capture_talk_fight.py` is driven by the game's own log, not by a stopwatch:

1. **Title leg**: three Enter presses at 2.5 s, 4.0 s and 18.0 s. The one place with no log line to wait on, because
   the title screen writes none, and these three are the presses the FIGHT capture already proved on this build.
2. **The deck is live**: wait for `PP: autosave, <map> <x>,<y>` and refuse the run if the map is not the deck. The
   run's own entry autosave is the first honest statement that the overworld is on screen.
3. **Walk and confirm, eight tries of a pair**: one step east, one confirm. The battle trigger at `ship_small (4,7)`
   is a CONFIRM trigger, not a walk-on one: `pp_overworld_step` only fires a `marker` on touch, and
   `pp_overworld_confirm_target` reads the tile the hero faces first and the tile under him second. A driver that only
   walks presses past the fight, which is exactly what happened on this tool's first run (eight footsteps in the log,
   no `battle start`).
4. **Per turn**: wait for the list line, move the cursor with `down` presses computed modulo the list's own length,
   hold 1.8 s, confirm, wait for the panel line, hold 1.8 s, then press the pick up to four times, 1.6 s apart,
   stopping on the pick line.
5. **Spare**: move onto SPARE from the cursor the game reported, confirm, wait for the result line.

Why the holds: the frame sample is one copy a second. A driver that presses the moment the list opens can finish a
turn in under a second and leave a recording that never shows the list, which is what the first run produced (63
frames, not one with the command list on it). A player reads the list before pressing; the capture holds.

Why the pick retries: the panel's confirm is an edge on the frame it is read, and a press that lands on the tail of
the reply board above the panel is spent there. Turn 2 of the first run lost its press exactly that way. The driver
stops on the pick line, so a press that lands the first time is the only press sent.

Why the log tail keeps **two cursors**: `position` is the byte the next read starts at, `scanned` is the line the next
`wait` looks from. Without the second one, two lines written between two polls would lose the second, and this driver
reads game state across polls.

---

## D17. The frame thresholds come off measured frames, and each one says which frame

Every number below was measured on this run's own frames before it was written down, and the report prints them
beside the measurement so a reader can see what it compared.

1. **The window is the paper, not the border.** `fig.is_battle_frame` asks for `battle_box_paper >= 0.70` AND
   `battle_box_border >= 0.70`, where the border is the share of the three rows ABOVE the window that are not paper.
   On the deck_day scene those rows are paper one row in three: measured `paper 1.00, border 0.67` on all 27 drawn
   frames of this run, so the FIGHT tool's border claim is unreachable here while the window is plainly drawn. This
   tool asks for the paper only, and prints the border as a number it does not require.
2. **The glyph colour is the sheet's, not a role.** `pp_font_draw` paints the 8x8 sheet with `PP_UNTINTED`, so what
   lands on screen is the sheet's own ink. The shipped `spr_pp_font8.png` is `(248,248,248)`; this run's frames carry
   it as `(232,231,236)`, 16 apart, which is the recording's own compression. `sheet_ink()` reads the colour from the
   PNG at run time and `GLYPH_TOLERANCE = 40` is the room around it. Before this, a check that looked for the `ink`
   role measured **0 pixels** on every frame: the TALK label is not painted in a role at all.
3. **The text rows are FOUND, not placed.** `pp_battle_draw_menu` spaces its rows at 20 px and
   `pp_talk_draw_options` at 16 px, and the first version of this tool copied one pitch and measured frames drawn by
   the other. `glyph_bands` now groups the rows that carry ink into bands, so a check cannot sample the wrong row.
   Measured rows on this scene: command list 176/196/216, option panel 178/194/210.
4. **The cursor is the one colour a glyph never is.** Both draw calls paint a 6 x 8 triangle at x 14 to x 20 in the
   `text` role, which is not the sheet's colour and not any other role. `CURSOR_INK_MIN = 8` against a 6 x 8
   triangle, exact match, no tolerance: `(200,200,212)` is 48 away from the sheet's ink, so a glyph cannot pass as one.
5. **TALK is four glyphs on the middle band.** `TALK_SPAN_MIN = 28` (a 32 px cell) and `TALK_INK_MIN = 30` measured
   `span 30, ink 97` on frame t_0025. The band index is computed from the command table (`labels.index("TALK") // 2`),
   not written as a 1, because the table's order is what puts TALK on the second row.
6. **The SPARE word is wider than `kill`.** `33..44` px, measured `word 35, press 53` on t_0059 against `kill` at 31 px
   in the FIGHT capture. A four glyph word cannot pass; a five glyph word cannot be narrower than the band.

---

## Two engine bugs this card found, and what they were

Both were found by running, not by reading, and both are in `game/scripts/pp_battle_text/pp_battle_text.gml`.

1. **The bake cache answered with the function itself.** `pp_talk_bake()` opened with
   `if (variable_global_exists("pp_talk_bake") && is_struct(global.pp_talk_bake)) return global.pp_talk_bake;` and
   then wrote `global.pp_talk_bake = _bake;`. A GMS2.3+ script function IS a global variable, so the guard was true on
   the very first call, the table was never built, and the function returned itself. Reading `.fight` off it killed
   the game: `PP CRASH: Variable <unknown_object>.fight not set before reading it` at `pp_talk_options`. This is why
   no release build has ever shown a baked talk line: the first TALK any player presses would end the game. The table
   now lives under `global.pp_talk_bake_table`, a name no function in the project carries, and the load writes
   `PP: talk bake, 18 rows kept of 18 read, 4 fight keys, 2 npc keys`.
2. **A member read could end the fight.** Every caller did `pp_talk_bake().fight` or `.npc` directly, so a bake of any
   other shape was a crash rather than a fallback. `pp_talk_bake_fight()` and `pp_talk_bake_npc()` are the two guarded
   reads now, and a table that is not there is an empty table: the ladder falls to the card pools, which is what the
   file's own header already promised for a missing file.

The first bug is the reason the capture could not have passed before this card: the TALK path was not slow or subtle,
it was fatal.

---

## Proof, all run on 2026-10-24

* `python tools/capture_talk_fight.py --idle-wait 300` exit 0, one launch, one recording: **13 of 13 checks ok**, no
  `ok=False` line in `build/talk_capture_run.txt`.
* The log the run wrote: `talk: 3` commands and `fight: 0`; picks `mercy [20, 40, 60]` against a declared
  `mercy_to_spare 60`; `trust [1, 2, 3]`; `spare` at turn 4 with `enemy hp 15` on the command line against
  `navy_sailor max_hp 15`, so the spare came through the trust gate and not the health threshold; one
  `fight result spare`; `no_crash_in_log` empty; `PP: talk bake, 18 rows kept of 18 read, 4 fight keys, 2 npc keys`.
* The recording: 768x720 at 60 fps, 73.80 s, 74 sampled frames; the command list with the cursor on TALK on 6 of
  them, the option panel on 6, the reply board on 2, the spare panel on 6.
* `python -m pytest tests/test_talk_fight_capture.py -q` -> 22 passed.
* `python tools/check_data.py` all files pass; `python tools/check_cleanroom.py` clean; `python tools/check_provenance.py`
  29 modules mapped; `python tools/check_spec_review.py` exit 0.

Two gates are red on this tree for another lane's files and not for this card's: `tools/check_project.py` reports
`game/datafiles/streams/pp_drive_v4.ogg` is not listed as an Included File, and `tools/check_build_inputs.py` lists
`pp_01_title_v7.ogg`, `pp_01_title_v8.ogg` and `pp_drive_v4.ogg` as uncommitted sources. Those are the title-theme and
drive lanes' assets, sitting uncommitted in the shared working tree; nothing this card touched is in them.

---

## Provenance

No external code, art, audio, dialogue or decompiled material was read, retyped or reused for this file or the cards
it rules. Every number is quoted from this repository's own files and its own runs: `game/scripts/pp_battle_director/`,
`game/scripts/pp_battle_text/pp_battle_text.gml`, `data/encounters/all.json`, `data/enemies/all.json`,
`data/dialogue/all.json`, `game/datafiles/art/spr_pp_font8.png`, `build/talk_capture_run.txt`,
`build/first_fight_talk_game.log` and `output/first_fight_talk_verify.json`.

Written by gamedev, 2026-10-24. Check for this file: it exists; D15 names all six lines and the function that writes
each one; D16 names the five legs and why each waits on a line; D17 names six thresholds and the frame each was
measured on; the bug section names the exact guard and the exact crash text; and the proof section names a run whose
log and recording are both in this repository.

---

# The drive: the lattice and the artifact, card t_ce63cb65

Raised by the review t_3cca8576 (`knowledge/REVIEW-R21-DRIVE-2026-10-24.md`, findings F1 and F5) of the drive room
(R21a, t_e9c7b280) and the drive scene (R21b, t_c27552e3). Neither finding was a code defect. Both were questions only
this lane can answer, and both are answered from the tree's own numbers rather than from preference.

## D18. The drive is cut to the exact 85.714 step bar, not 86 and not 87

**The ruling.** `steps_per_bar = 3 x 3600 / 126 = 85.7142857`, and a hard cut sits at
`cut step = round(bar x steps_per_bar)`. That one lattice owns every duration in the film: the twelve shots, the
scene's command list, the room's capture table, and the shot list's tables.

**Why the exact bar rather than the integer 86.** The clock under the picture is the rendered cue, and the cue's bar is
85.714 steps because 126 bpm at 60 steps a second is exactly that. 86 is not a second opinion about the music, it is
what the old durations were typed on: it divides all eleven of them perfectly only because they were built on it. Its
price is 0.286 steps a bar, which no single shot shows and the last cut does, 32 steps late, 0.54 s, more than a beat
(a beat is 28.57 steps). A cut that lands half a second after its downbeat is a mistake a viewer hears.

**Why not the 87 the title machine runs on.** `data/title_timing.json` `bar_steps` is 87 on purpose and its own
`_integer_note` says why: 87 is three whole beats of 29, so the title's beat derived car bob and its bar derived star
twinkle cannot slip against each other. That is right for a repeating animation constant, where a 1.5 percent tempo
error is invisible. It is wrong for a cut: 87 puts the last cut 113 steps (1.88 s) early, and the same twelve bar
counts then make a 10,793 step film, which moves the cue's own 10,680 scoring, the interlude's 2,400 and the 13,080
wall total. So the title keeps 87 for what it animates, and the drive reads `bpm`, `steps_per_bar` and
`scroll.px_per_step` from the same file and never `bar_steps`.

**The cost, printed by `assets/audio/pp_drive/cue_cut_v3.py` on this tree.**

| bar | cut step | downbeat with the file's 85.714 | drift steps | drift s |
| --- | --- | --- | --- | --- |
| 8 | 686 | 685.7 | +0.29 | +0.005 |
| 18 | 1,543 | 1,542.9 | +0.15 | +0.002 |
| 25 | 2,143 | 2,142.8 | +0.15 | +0.003 |
| 34 | 2,914 | 2,914.3 | -0.28 | -0.005 |
| 46 | 3,943 | 3,942.8 | +0.16 | +0.003 |
| 59 | 5,057 | 5,057.1 | -0.13 | -0.002 |
| 69 | 5,914 | 5,914.3 | -0.27 | -0.004 |
| 79 | 6,771 | 6,771.4 | -0.41 | -0.007 |
| 92 | 7,886 | 7,885.7 | +0.31 | +0.005 |
| 105 | 9,000 | 9,000.0 | +0.03 | +0.001 |
| 113 | 9,686 | 9,685.7 | +0.32 | +0.005 |

Worst 0.41 steps, 7 ms, at bar 79 with the file's three place 85.714; 0.43 steps on the exact `3 x 3600 / 126`, which
is the figure `knowledge/DRIVE-SHOT-LIST.md` section 8 quotes. Either way it is inside one frame at 60 steps a second,
and it does not accumulate because every cut is computed from its own bar number. The film stays 10,680 steps =
178.00 s, so the cue, the interlude and the 13,080 wall total do not move. That is the practical argument for this
lattice over 87: the decision costs no downstream number.

**What is retired and what is left standing.** The 86 snap is retired everywhere it decided a duration:
`data/scenes/all.json`, `pp_drive_shots()` in `game/scripts/pp_drive/pp_drive.gml`, and
`knowledge/DRIVE-SHOT-LIST.md` sections 1, 2, 3 and 8. `assets/audio/pp_drive/NOTES-v3.md` still prints the old 86 step
dump (cut 1 at step 688, drift +2.29) because it is the record of the CUE-DRIVE run that produced it; it is left as
evidence of the retired grid rather than rewritten, and no duration in it is spent by the game. The artifacts that
matter (`cue_map_v3.json`, `cut_dump_v3.txt`) are regenerated by the script on every run and now carry the exact grid.
`knowledge/BEAT-SHEET-VERIFY-2026-10-24.md` finding `D2` and question `Q1` ask exactly this question; D18 is the
answer, and that file is another lane's untracked work, so it is cited here rather than edited.

**What this does not prove.** This is the picture against the music's score, not against the record. If the rendered
`title_theme` ogg's real tempo is not exactly 126.000, or its first downbeat is not at sample zero, the whole picture
grid can still sit off the record by one constant offset. That is an ear question on the audio lane and it is named
here instead of assumed. What the arithmetic does prove is that no cut drifts from its own bar, which is the property
the film's rule asks for.

## D19. The drive ships as the scene on `drive_m4_corridor`; `rm_pp_drive` is capture only

**The ruling.** What a player sees is the `drive_to_southampton` scene of `data/scenes/all.json`, played by the spec 06
runner on the map `drive_m4_corridor`. `rm_pp_drive` and `pp_drive.gml` are a capture rig: reachable only when
`PP_DRIVE_ROOM` is set, which no real launch sets, and not on the route.

**Why, in order of weight.**

1. **The route already plays the scene.** `data/slice.json` step `drive` is kind `scene`, scene
   `drive_to_southampton`, map `drive_m4_corridor` (160 x 24, road on row 8, start (0,8), arrive (159,8)). It is built,
   mapped, palette set and tested. Shipping the room means building a second road to the same place.
2. **The scene is the architecture.** One command list in data, played by one runner, is how every other scene in the
   game works, and it is what lets the twelve shots be edited as content instead of as GML.
3. **The room would need three changes before it could ship, and one of them is a spec fix.** A door on the route; its
   twelve durations becoming a read of the data rather than a second copy; and pages that advance on the player's
   press, because `pp_drive_page_index` advances them on their own share of a shot today, against spec 05 and against
   the shot list's own "a page advances on the player's press". That is real work buying nothing the scene does not
   already do, on the screen most likely to be seen first.
4. **The eight places are not lost by choosing the scene.** They are the scene's camera windows on the corridor: tile
   x 37 for the gantry and the motorway shots, 83 for Twyford Down, 141 for the cathedral, 25 for the downland, 0 for
   the opening and the docks. The shot list section 4.1 says which window is which place, and the review checked all
   twelve pictures against it.
5. **The duplicate is closed by a test, not a promise.** `tests/test_drive_map.py` now cuts the scene's flat command
   list at the shot list's eleven cut steps and compares each window's steps and its `say` ids, in order, against
   `pp_drive_shots()`. A change to either copy fails the suite, which is the thing the review found missing.
6. **The cost is one small piece of unreachable code.** `pp_drive.gml` has to keep compiling while nothing launches
   it. The same test covers it, and `PP_DRIVE_ROOM` keeps it out of every real run. If it rots, what is lost is the
   `tools/capture_drive.py` path, not the game. If the room ever has to ship, that is a new decision on its own card,
   not a re-reading of this one.

**What choosing the scene gives up.** The title machine's two frame palette flash. Shot 10 is the storm, and the only
whole screen palette flash in the build lives in `pp_title.gml` (the storm clock, 2 frames from
`data/title_flash.json`), while the scene runner's fifteen commands have no flash. So shot 10 ships with
`sfx thunder_soft` and a wait, silent on the palette, until a `flash` command is added to spec 06. That is a runner
question on its own card, and it is the one thing the room branch would have given for free.

**Resolved 2026-10-24 by card t_531bc76c.** The cost is paid, and the film did not move. The scene runner grew a
`flash` command (spec 06 row and rule 8): an optional `steps` (default `PP_FLASH_STEPS`, 2, the title's own storm
clock, 8 at most) and an optional `role` (default `paper`, which every set in `data/room_palettes.json` declares). The
world holds the flash and floods the frame in that role, drawn under the fade and over everything else, so it is a
palette change and not a blend (spec 13). It costs the scene ZERO steps: the command advances in the step it runs and
`pp_overworld_step` counts the frames down on its own clock, exactly as it counts the shake down. `drive_to_southampton`
[49] is `sfx thunder_soft` and [50] is `flash 2`, both of which advance in the same step, so the sound and the light
land on the same frame. The film is still 10,680 steps and the twelve durations, the eleven cuts and the cue's grid are
untouched; `tests/test_drive_map.py` pins the flash's zero cost and reads its frame count from `data/title_flash.json`
rather than retyping it, and `tests/test_scene_runner.py` refuses a flash case that sets a runner state or a timer.
`knowledge/DRIVE-SHOT-LIST.md` `Q1` carries the ruling, so the shot list stops asking.

## Proof for D18 and D19, run on this tree

* `python tools/check_data.py` -> `check_data: all files pass`.
* `python -m pytest tests/test_drive_map.py tests/test_slice_route.py tests/test_scene_runner.py tests/test_cue_cut_v3.py
  tests/test_drive_tiles_wire.py -q` -> 82 passed in 1.40 s.
* `python -m pytest tests/test_audio.py tests/test_drive_v2.py tests/test_title_timing.py tests/test_mix_check_v3.py -q`
  -> 41 passed in 3.46 s, so the audio lane's own pins still hold and the title keeps its 87.
* `python assets/audio/pp_drive/cue_cut_v3.py` exit 0: `film: 12 shots, 10680 steps = 178.00 s`, `cut steps: section 2
  running totals match section 1`, every cut `snaps to the stated bar`, worst drift -0.41 steps at cut 8.
* `python tools/check_provenance.py` -> 29 modules, every one mapped. `python tools/check_cleanroom.py` -> clean.
  `python tools/check_spec_review.py` -> exit 0, with the three specs already pending before this card.
* The segmentation behind D19 reason 5 was run before it was written as a test: 59 scene commands summing 10,680, the
  eleven cut steps all landing on command boundaries, and all twelve windows' step totals and `say` ids equal to
  `pp_drive_shots()` row for row.
* What is not proven: nothing was launched in GameMaker, and no cut was listened to against the record.

## Provenance for D18 and D19

No external code, art, audio, dialogue or decompiled material was read, retyped or reused for these two rulings.
Every number is from this repository's own files and its own runs: `data/title_timing.json`,
`data/scenes/all.json`, `data/slice.json`, `data/maps/all.json`, `game/scripts/pp_drive/pp_drive.gml`,
`game/objects/obj_pp_game/Create_0.gml`, `game/scripts/pp_scene/pp_scene.gml`,
`game/scripts/pp_config/pp_config.gml`, `knowledge/DRIVE-SHOT-LIST.md`, `assets/audio/pp_drive/cue_cut_v3.py` with its
two artifacts, and `knowledge/REVIEW-R21-DRIVE-2026-10-24.md`.

The 85.714 lattice is arithmetic from the theme's own stated tempo, not a studied mechanic, and the scene over the room
is this project's own runner architecture.
