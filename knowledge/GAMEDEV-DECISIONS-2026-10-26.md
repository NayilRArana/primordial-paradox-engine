# Gamedev decisions, 2026-10-26

Card t_6d66f32d (REFINEMENT BACKLOG row RB-05, DECISIONS SWEEP), gamedev, head of build. Written 2026-10-26
07:15 to 07:40 PDT on CitadelArana, the desktop node. Authority: this file rules the four `Q for gamedev` cards that
were holding four other lanes. It sits beside `knowledge/GAMEDEV-DECISIONS-2026-10-23.md` and
`knowledge/GAMEDEV-DECISIONS-2026-10-24.md` and does not contradict either; where it extends one, it says so. A card
that disagrees with this file is wrong, not this file.

Every number below was measured on this node in this run, at HEAD 1a242a4. Where a number is priced from a spec by
arithmetic rather than read off a file, the line says `[inference]` and names the spec rule it rests on.

The four cards: `t_9275989a` (boarding cue), `t_f034f9d0` (drive palette), `t_279ef225` (battle cue wiring and tempo),
`t_16417018` (title theme acceptance).

Three of the four cards were written from measurements that have since moved. Every ruling below states today's
measurement next to the card's premise so a reader can see which half is stale.

---

## D1. The gangway keeps 32.000 s and the row keeps its steps; neither number moves, and the cue becomes row PP-17

Decision, one line: `SHIP-DECK-MAP` keeps its 32 s and `data/scenes/all.json` `ship_boarding` is **not** authored up to
1920 steps; the row keeps the 542 steps it costs today, gains cue `PP-17` (`pp_boarding`, one shot, 32.000 s) as its
only music track at the opening, and its last music command hands back to `PP-05` with spec 12's 30 step crossfade, so
no separate fallback row is needed.

Why: `208 steps` is a draft figure from a row that commit 5f5180b (SHIP-CAPTIONS) has already replaced. The row in the
tree today is `shake 40`, `wait 120`, `camera 24`, `wait 90`, `say ship_gangway`, `camera 24`, `move 1 tile`, `wait 60`,
`setflag`, `end`, which is 366 fixed steps plus `ship_gangway`'s own 176 step floor (three lines, `* The horn shakes the
deck.` 25 characters at 2 steps each plus 8, `* Salt, rope and wet paint.` 25 characters plus 3 plus 8, `* A wardroom
hatch, shut.` 23 characters plus 3 plus 8, spec 05 rule 1 and 2) = 542 steps, 9.033 s `[inference: spec 06 numbers for
camera, wait and shake, spec 04's 8 steps a tile for a railed move]`. The rest of beat 25's 32 s is the three confirm
gates on that dialogue: a `say` is player paced by spec 05, so no step count can own that time and padding the row to
1920 steps would author 1378 steps, 22.97 s, of dead wait. The 32 s is the beat sheet's number and the cue is cut to it;
both are correct and they are measuring different clocks. On the handback: spec 12 rule 1 allows one music track at a
time, so `PP-BOARDING` cannot play under `PP-05`; it replaces it for the scene, and rule 4's 30 step crossfade is the
handback. The row's last music command therefore names `PP-05` again, which is already the delivered ship cue, so no new
fallback row exists in this ruling.

Files and numbers it moves:

| file | before | after |
| --- | --- | --- |
| `data/mechanics/pacing_recipes.json` beat 25 `gangway_deck_horn` | 32 s | 32 s, unchanged |
| `data/scenes/all.json` `ship_boarding` | 208 steps in the card's draft, 542 steps measured today | 542 steps plus two music commands (`PP-17` first, `PP-05` last) |
| `data/audio.json` cues | 17 rows, `PP-16` the highest | 18 rows, new `PP-17` `asset: pp_boarding`, `loop: false`, `fallback: PP-05` |
| `assets/audio/pp_boarding/pp_boarding.ogg` | not named by any row | named by `PP-17`, 32.000 s measured by ffprobe |

Not a spec change: no number in `specs/` moves. The card's 208 is a data draft, retired here.
Landed by: the forward card that owns `data/scenes/all.json` and `data/audio.json` for this scene, not by this one.
`assets/audio/pp_boarding_v2/` is the lane's later revision of the same cue at the same 32.000 s; it is a candidate,
and it becomes the shipped build the same way D4 rules: by editing `PP-17`'s `delivered_file`.

## D2. The drive stills get no set of their own and must measure 1.0000 legal after the ppu conversion the capture tool already writes

Decision, one line: the drive stills are drawn from the roles `drive_night` already declares in
`data/room_palettes.json` and `data/scene_palettes.json` stays at 12 sets with no drive entry; after the fix all 12
stills measure **1.0000** legal against the 55 master colours in `data/nes_palette.json`, each as a `capture_drive.py`
`_ppu` twin at 256x240 that `tools/nes_check.py --type background` passes.

Why: measured in this run, the 12 frames at `output/drive/pp_drive_shot_01..12.png` are 768x720, carry 8 to 10 colours
each, and are 0.0000 to 0.0167 legal, which reproduces the audit's number exactly. Shot 01's top three colours are
`08131F` 45.1 pct, `1B1B22` 34.4 pct, `0B0B0F` 10.3 pct; the first two are in neither `data/nes_palette.json` nor
`data/palette.json`, so no palette set in this project can draw them and adding a 13th set to
`data/scene_palettes.json` would legalize nothing. What makes the target reachable is already on disk and already in the
tool: `output/drive/pp_drive_shot_03_1x_ppu.png` is 256x240, 7 colours, 1.0000 legal, and
`tools/nes_check.py --type background` passes it, while `tools/capture_drive.py:371` (`run_enforce`) is the code that
writes that twin for every shot through `tools/nes_enforce.py`. Only shot 03 currently has one. So the answer is the
quantized branch, and the pattern for all twelve is shot 03's ppu conversion, not a folder exemption.

Files and numbers it moves:

| file | before | after |
| --- | --- | --- |
| `data/scene_palettes.json` | 12 sets, none is the drive | 12 sets, unchanged |
| `data/room_palettes.json` `drive_night` | 13 roles, 10 distinct colours | unchanged, it is the drive's set |
| `output/drive/pp_drive_shot_01..12.png` | legal 0.0000 to 0.0167 | 12 of 12 at 1.0000 legal |
| `output/drive/pp_drive_shot_NN_1x_ppu.png` | 1 file (shot 03) | 12 files, each 256x240, `nes_check` background PASS |

Spec change, stated as one: `knowledge/ART-BIBLE.md` RULE 0 point 1 reads "every scene starts from a palette set
written in `data/scene_palettes.json`" and from today it reads "every scene starts from a palette set; the set lives in
`data/scene_palettes.json`, except for a room that is capture only and draws a tile sheet in its own roles, where
`data/room_palettes.json` carries it". That is the same reading D18 of `knowledge/DRIVE-MAP-2026-10-24.md` already
applied to the drive map, extended from the map to the room. The sentence lands in the art bible through the art lane's
own card; this file is the authority until then.
Extends: D18 of `knowledge/DRIVE-MAP-2026-10-24.md` (the map half), which left the room half open on this card.

## D3. PP-04 keeps the file it names and the battle cue stays 168 bpm; pp_fight_v2 is not wired

Decision, one line: `data/audio.json` `PP-04` keeps `assets/audio/pp_04_navy_sailors/pp_04_navy_sailors.ogg` and the
battle cue stays **168 bpm**; `pp_fight_v2` is not wired, and the only two lines that can change either are `PP-04`'s
`delivered_file` in `data/audio.json` and the tempo constant in the render script.

Why: the card's premise has moved twice. `PP-04` does not point at `pp_fight/pp_fight_fight.ogg`; it names
`pp_04_navy_sailors.ogg`, 43.636349 s by ffprobe, and `pp_fight_v2` is now four generations old: the lane is at
`pp_fight_v6`, built today at 13:16 UTC, with a paired ear read of 30 of 60 against 29 for v5 (its own
`NOTES.md`). Wiring v2 would wire a superseded take. Tempo stays 168 for the reason the musician gave and I am
confirming as a spec call: both states are 16 bars and the seam is state A's bar 16 landing tick for tick on state B's
bar 1, which is what lets the director cut on any bar line; at 126 bpm the same 16 bars is 30.476 s and the seam is
gone. The only 126 in `specs/` is spec 14's crawl beat pause, 72 steps at 126 bpm, which is the title crawl and not the
battle. Measured today per state: `pp_fight_v2_fight.ogg` 22.857143 s, `pp_fight_v2_calm.ogg` 22.857143 s,
`pp_fight_v2_states.ogg` 45.684558 s. No row in `data/audio.json` carries two states today (grep for `states` in that
file returns nothing), so the director has nothing to cut between yet: the row stays one file, `loop: true`, and adding
a states field is a schema change on its own card, not a side effect of this one.

Files and numbers it moves:

| file | before | after |
| --- | --- | --- |
| `data/audio.json` `PP-04` line 21 `delivered_file` | `assets/audio/pp_04_navy_sailors/pp_04_navy_sailors.ogg` | unchanged by this ruling |
| `assets/audio/pp_fight_v2/pp_fight_v2_fight.ogg` | 22.857143 s at 168 bpm, not named by any row | unchanged, candidate |
| battle tempo | 168 bpm, 16 bars per state | 168 bpm, unchanged |

Not a spec change: no number in `specs/` moves. The 126 in this card's brief was the card's own line and it loses to the
cue's spec, which is what the musician already did by keeping 168.
Landed by: nothing, this ruling changes no file. A promotion of `pp_04_navy_sailors_v3` (hook 100, ear 32) or of a
two-state fight take is a one line data change plus its note, on a forward card.

## D4. The accepted title theme is the file PP-01 names, and the percy pair belongs to t_cdb3a6be

Decision, one line: the accepted title theme is whatever `data/audio.json` `PP-01`'s `delivered_file` names, which today
is `assets/audio/pp_01_title/pp_01_title.ogg`; `pp_01_title_v7` and `pp_01_title_v8` stay committed candidates that no
row names, and the `percy_theme_v3`/`percy_theme_v4` pair belongs to card `t_cdb3a6be`, which already landed it.

Why: the card's five reds are green today and the measurement it rests on is two days old. `git ls-files` lists both
`assets/audio/pp_01_title_v7/pp_01_title_v7.ogg` and the `_v8` twin, `game/PrimordialParadox.yyp` names each of them
twice, `python tools/check_build_inputs.py` exits 0 with `every declared file resolves to a committed source`,
`python tools/check_project.py` exits 0 with `project graph and disk agree`, and the two test files the card blamed
(`tests/test_project.py`'s three rows and `tests/test_build_inputs.py`) run `16 passed in 12.14s`. v7 and v8 landed in
21785a8; percy v3 and v4 landed in a3fdc46. So the open question was never a
git question, it is an acceptance question, and the acceptance rule is the one this file applies to every cue: a build
is accepted when a cue row names it. v8 is the strongest candidate on the lane's own numbers (hook 83, ear 37 of 60, the
best title read in the lane's table), and it still is not the theme until `PP-01` says so, because a row that names a
file is the only thing the game plays.

Files and numbers it moves:

| file | before | after |
| --- | --- | --- |
| `data/audio.json` `PP-01` line 18 `delivered_file` | `assets/audio/pp_01_title/pp_01_title.ogg` | unchanged by this ruling |
| `tools/check_build_inputs.py` | 2 MISSING FROM COMMIT and 2 UNCOMMITTED SOURCE rows on 2026-10-24 | 0 rows, exit 0 today |
| the four test files in the card | 5 red rows | 0 red rows, 16 passed |

Not a spec change: no number in `specs/` moves.
Handoff: the percy pair goes to `t_cdb3a6be` and needs no ruling from this file; `a3fdc46` already carried both streams
and the yyp entries that name them. `percy_theme` in `data/audio.json` `PP-06` still names the v1 asset and neither
newer take, which is D4's rule applied: candidates do not become the boss theme until `PP-06` names them.

---

## The rule these four share

A cue is accepted when a row in `data/audio.json` names its build, a palette set is accepted when it is written in a
data file that a checker reads, and a number is accepted when the file that owns it says so. Three of the four cards
above were blocked on a measurement of a tree that had already moved; the ruling that fixes them is not a new number,
it is naming which file owns the number.

Provenance: no external source studied for this card. Every measurement is this repository's own files and tools, run on
the desktop node in this session; nothing was read from any decompilation, nothing copied, nothing pushed and nothing
published.
