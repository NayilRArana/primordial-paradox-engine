# FIRST-FIGHT finding, 2026-10-26: why output/first_fight_verify.json is ok false

Card t_ecad67bd (lane testing, node CitadelArana, the desktop). Every number here was measured on this PC on
2026-10-26 between 07:21 and 07:40, not read off another lane's report. Commands and their output are in the card's
comment; the frames named below are on disk at the paths given.

The short answer: four of the report's seven checks are red because the NEW GAME run never reaches the fight, which is
a game route defect (finding 1). On a real first fight, recorded for this card, two of the seven are still red and both
are measurement defects, one in the verifier (finding 2) and one in the art the verifier is judging (finding 3). A
fourth defect is named in finding 4: `battle_box_border` is green on 123 frames that contain no battle at all.

Nothing on the card's MUST NOT list was done: no `--force`, no idle gate override, no threshold lowered, no test edited,
no skipped frame counted as a pass, nothing posted or published.


## What the card's own command does today

`python tools/capture_first_fight.py` (quiet window, idle gate allowed at 520 s of no input) records 123.1 s, cuts 123
frames, and writes ok false. The report's seven entries:

| entry | ok | measured |
| --- | --- | --- |
| battle_box_in_sample | false | 0 frames; best paper 0.0001 against 0.70 |
| fight_command_in_sample | false | 0 frames; best FIGHT ink 16 px, bbox 6 px |
| victory_text_in_sample | false | 0 frames; best panel paper 0.0000 against 0.85 |
| muted_line_in_log | true | `PP: muted, PP_MUTE=1 ...` |
| battle_start_in_log | false | count 0 |
| no_crash_in_log | true | no `PP CRASH` line |
| video | true | 768x720, 60/1 fps, 123.08 s, union picture share 0.951 to 0.970 on all 7 samples |

So the count is 4 red and 3 green, not 5 and 2: the `video` entry is green on this run and was green on the 18:15 file
too (its `game_picture_ok` field reads true there). The card's own summary counted it out.

The game's log for that run, `build/first_fight_game.log`, says what happened instead of a fight:

    line 71  PP title: intro finished, starting the run in rm_pp_ship
    line 72  PP title: the crawl handed to the route's step drive
    line 75  PP: music PP-02 requested
    line 83  PP: sfx car_engine_loop requested
    ...      105 `PP audio: text_blip_a played` lines, then ###game_end###254

and `PP: battle start` appears 0 times in 208 lines. The frames show the same thing:
`output/first_fight_frames/f_0020.png` (20 s, the moment the tool's two Right presses are sent) is already the road
corridor of the drive, and `output/first_fight_frames/f_0050.png` (50 s) is the same corridor. There is no command box,
no FIGHT label and no victory panel anywhere in the 123 frames.


## Finding 1 (causes the four red checks): NEW GAME cannot reach the first fight

The chain, in the game's own data and code:

1. `data/slice.json:23` gives the crawl step `"next": "drive"`, and `data/slice.json:26` names the drive row's scene
   `drive_to_southampton`.
2. `game/scripts/pp_title/pp_title.gml:412` (`pp_title_crawl_handoff`) takes that handoff whenever the PP_SLICE walk is
   off, which is every real launch, and prints the line seen in the log at `pp_title.gml:437`.
3. `game/scripts/pp_app/pp_app.gml:632` (`pp_slice_handoff`, scene case) requests the overworld on the scene's own map,
   so the run leaves `ship_small` and is placed on `drive_m4_corridor` at its start tile.
4. `data/scenes/all.json:262` (`drive_to_southampton`) is 64 commands with 10,248 explicit `wait` steps, which is 170.8 s
   at 60 steps a second before its final `fade` and `end` (measured by summing the row's own `steps` values).
5. `game/scripts/pp_scene/pp_scene.gml:507` (`pp_scene_end`) hands control back to the walker on the same map. Nothing
   advances the route there: the only reader of a row's `next` is `pp_slice_walk_step`
   (`pp_app.gml:804`), and `pp_slice_walk_enabled` (`pp_app.gml:748`) is true only when PP_SLICE is set.
6. `data/maps/all.json:507` is `drive_m4_corridor`, and `data/maps/all.json:609` gives it `"triggers": []`. The map has no
   battle, no scene, no map trigger and no portal, so when the drive does end the player stands on a map with nothing on
   it and no way out.

What that means for this card: the recording is 123 s and the drive alone is 170.8 s before any of the quay gate,
boarding and fight steps the route names after it, so no schedule of key presses inside a 123 s recording can put the
first fight on video. Even a longer recording cannot, because step 6 leaves nothing to walk to.

When this appeared: commit `3c349b6` (2026-10-24 20:55, card t_e8a8f18a, DRIVE-MAP) is the commit that put
`drive_to_southampton` into `data/scenes/all.json` and made the handoff takeable. The talk capture's log from 2026-10-24
16:00, `build/first_fight_talk_game.log:73`, shows the state before it: `PP title: the route's next step drive cannot be
taken yet: the scene drive_to_southampton is not in data/scenes/all.json`, after which a new run stayed on `ship_small`
and `PP: battle start tutorial_sailors on ship_small 3,7` appears at line 78. The first capture after that commit, on
2026-10-25 18:15, is the file this card was written from, and it is the first one with count 0. Nothing in the capture
tool changed between those runs; the game did.

## Finding 2 (a verifier defect): `fight_command_in_sample` searches a colour the frame does not carry

Measured on a real first fight, recorded for this card from the title screen's CONTINUE row (the game's own entry
autosave, `map ship_small`, spawn `start` (2,7), `flags {}`, `fight_exits []`), so the fight the data authors is the fight
on the video:

    PP: battle start tutorial_sailors on ship_small 4,7      (count 1)
    f_0045.png  box paper 0.952  border 0.708  FIGHT ink 0 px
    f_0046.png  box paper 0.952  border 0.708  FIGHT ink 0 px
    f_0090.png  panel paper 0.953  word 28 px  press 53 px  (the result panel)

A crop of `resume_probe/frames/f_0046.png` at the command window reads, left to right by row: `FIGHT POWER` then
`TALK SPARE`. The FIGHT label is on screen and legible. The check reads 0 px of it because of how it looks:

- `tools/capture_first_fight.py:876` passes `glyph_ink = roles["ink"]`, which is `data/palette.json`'s index 0,
  `#0b0b0f`, and `capture_first_fight.py:627` builds the cell mask by exact equality with that one colour.
- On the cut frame the label's strokes are h264 bloom, not `#0b0b0f`: the 41 px that are exactly the `text` role
  `#c8c8d4` plus roughly 500 px spread over about 20 near-white values such as `(248,247,252)` and `(255,253,255)`,
  none of which is within 12 of any of the 54 palette entries, so the frame reader leaves them as they are.
- The cell measured as "any pixel that differs from the paper role by more than 24" reads 121 px, bbox 39 px of the 40 px
  cell, and 5 ink runs, which is the five glyphs (see `probe_fight_mask.py`). The check's own thresholds are
  `FIGHT_SPAN_MIN 32` and `FIGHT_INK_MIN 20` (`capture_first_fight.py:702`), so a correct measurement of this frame clears
  both by a wide margin.

The tool's comment at `capture_first_fight.py:716` to `726` records that the borders, the label rows and the label colour
were all changed once before, on material where the labels did land on the ink role. On this build they do not: what the
cell carries is a spray of near-white values (unverified whether the sheet's own white or the text role is the source;
what is measured is that `#0b0b0f` is absent and that 41 px sit exactly on the text role).

## Finding 3 (an art defect the verifier is right to redden): the battle screen spends a deep blue outside both palettes

On the same real fight, `video.game_picture_ok` is false, and the report's samples say why:

    at 23.48 s  union 0.6702   at 46.96 s  union 0.9175   at 64.57 s  union 0.9168
    at 82.18 s  union 0.6720   at 99.79 s  union 0.9682   at 111.53 s union 0.9678

`resume_probe/build/first_fight_sample_20.png` is the 23.48 s frame: a battle screen with "Navy Sailor", `HP 20/20`,
`WILL 3/3` and the enemy stack, not a terminal and not a desktop. 0.3298 of its pixels are further than 12 from every one
of the 109 entries in the two palette files, and the largest offender is a deep blue, `(6,5,108)`, on 4.98 pc of the
frame with the nearest palette entry 44 away (`probe_offpalette.py`). No room set can produce it: every role in
`data/room_palettes.json` resolves through `data/palette.json`, and `data/palette.json` has no colour anywhere near it.
So the pixel is in the art drawn behind the command window, which is the palette lane's open RULE 0 question
(`knowledge/PALETTE-SYNERGY.md` line 261), not a tolerance the capture should raise.

The floor is 0.90 (`VIDEO_PICTURE_MIN`, `capture_first_fight.py:713`). Lowering it would let a terminal screenshot through,
so it must not be lowered; the art has to come inside the palette. This is the same class the audit counted as the 9
frame-class palette violations.

## Finding 4 (a check that cannot fail): `battle_box_border` is 1.0000 on every frame of a recording with no battle

On the card's own 123 frames the border measure reads exactly 1.0000 on 123 of 123, including the title screen at 0 s and
the drive corridor at 50 s, while the paper measure that is supposed to go with it reads 0.0001 at most. The measure is
the share of the three rows above the window that are not paper (`capture_first_fight.py:604`), which any screen that is
not paper satisfies.

On the real fight it is the opposite: of the 42 frames whose command window is up (box paper at least 0.90), 40 read
0.667 to 0.678 and fail the 0.70 threshold, and only `f_0045.png` and `f_0046.png` pass at 0.708, a margin of 0.008. So
the half of the check that is supposed to prove a window is bounded is green where there is no window and a coin flip
where there is one. The paper half is the half that discriminates.


## What makes the report 7 of 7, in order

1. Game, gamedev lane: the route has to carry a player from the crawl to a map where the first fight can start (finding 1).
   Until that lands, no honest capture of a NEW GAME run can contain a battle, and no threshold change can fix it.
   The same fix decides how long the demo's opening is: the drive's 170.8 s of waits is longer than the capture's own
   123 s recording, so either the capture's schedule and length change with it, or the drive gets a player-legitimate
   skip, which is a design decision and not this card's.
2. Verifier, testing lane: measure the FIGHT cell in a way that survives the encoder (finding 2), and make the border
   measure discriminate or say in the report that it does not (finding 4). Neither needs a new threshold; the corrected
   numbers are 121 px, 39 px span and 5 runs on `f_0046.png`.
3. Art, palette lane: bring the battle backdrop inside `data/palette.json` (finding 3), which is the only way
   `video.game_picture_ok` can pass on a frame that contains the fight without lowering its floor.

The frames this finding rests on, all on the desktop node:

    output/first_fight_frames/f_0020.png                       card run, 20 s, drive corridor, no battle
    output/first_fight_frames/f_0050.png                       card run, 50 s, drive corridor, no battle
    resume_probe/frames/f_0046.png                             real fight, FIGHT POWER / TALK SPARE on screen
    resume_probe/frames/f_0090.png                             real fight, result panel, word 28 px, press 53 px
    resume_probe/build/first_fight_sample_20.png               real fight, HP 20/20 and WILL 3/3, 0.33 off palette

The resume recording is 117.4 s at 768x720, 60/1 fps, and is a real run of the same build
(`output/PrimordialParadox/PrimordialParadox.win`, written 2026-10-26 06:12).
