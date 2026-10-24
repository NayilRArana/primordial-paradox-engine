# Primordial Paradox decisions, 2026-10-24 (second file of the day): the TALK capture

Three rulings this card needed, and the two engine bugs the work uncovered. Written after the capture passed, so every
number here is quoted from a run rather than intended. Card **t_27aa179e** ("make the TALK path provable from outside
the game"), child of the first-fight capture card.

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
