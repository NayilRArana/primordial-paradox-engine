# Provenance: what was studied, and how ours differs

Rule: a subsystem cannot be committed until it has an entry here. Each entry names the source read, the mechanics
learned in plain language, and the concrete ways our implementation differs. "Copied expression: none" is a claim
about this repository, and it is checked by tools\check_provenance.py plus the clean-room scan described below.

### What is allowed, and what is not

Nayil's order of 2026-10-19, recorded in PLAN.md section 1, permits READING a decompiled copy of a commercial
GameMaker game in order to understand its architecture, and states that this order supersedes the earlier no-study
rule. That is the current rule and it is not the one this file was originally written under.

Three buckets decide every case, in one second:

- FREE, take it whole: architecture, state machines, room and event flow, data layout, menu structure, battle flow,
  save shape, system design. Ideas are not protected. Take them.
- RENAME, take the shape and change the skin: GML patterns, function structure, event layout, variable roles. Same
  machine, our names.
- REWRITE, write fresh: the actual code text, assets, names, dialogue. Never paste their text. Retype from a
  dossier.

What stays forbidden, and this is the part that keeps a takedown notice away: their code text or a reworded copy of
it, their sprites, fonts, sounds, music or data tables, their character names, dialogue or item names, and a module
whose structure traces one to one onto one of their objects.

The study copies live under `knowledge/study/`, which is gitignored, and they are never shipped, published or
committed. The dossiers distilled from them are under `knowledge/study/DOSSIER/`, prose only, no code text. The
committed doctrine that every future system derives from is `knowledge/FOX-STYLE.md`.

The 2026-10-19 entries below that were written under the older rule are kept as history. They are not a
prohibition; they are the record of what that read covered.

The review record for modules is knowledge\CLEANROOM-REVIEW.md, for specs knowledge\SPEC-REVIEW.md, and the method plus
the per source file outcome are in the section at the end of this file.

How the no-copy claim is checked, mechanically, on every commit:
1. `tools\check_cleanroom.py`: fails if anything under game\ or data\ names a study copy, the quarantine folder or the
   decompilation repository; fails on a foreign character or game name as a whole word; fails on a listed distinctive
   phrase from those games; fails on a GML module with no row in knowledge\CLEANROOM-REVIEW.md or a row that claims a
   review with no reviewer or no date. It does NOT compare our text against theirs, because that comparison requires
   reading the thing we refuse to read. The corpus comparison it replaced is gone with the corpus.
2. `tools\check_provenance.py`: fails if any module file is missing from the module map below, or if any entry is
   missing a field or the line "Copied expression: none".
3. `tools\check_project.py`: fails if the .yyp, the .yy files and the folders on disk disagree, and fails if any file
   under game\ references knowledge\study.
4. The human step: a reviewer named on each row of knowledge\CLEANROOM-REVIEW.md reads that module against the public
   record and a spec in specs\, and every module is written from a spec, not from a studied file. A row that still says
   pending is printed by name on every checker run until it is ruled on.

## module map (which entry owns which file)

Every file that ships is listed here, and tools\check_provenance.py refuses a module that is not.

| File | Entry | Spec |
| --- | --- | --- |
| game/scripts/pp_app/pp_app.gml | specs alone | 01 |
| game/scripts/pp_art/pp_art.gml | specs alone | 14 (proposed) |
| game/scripts/pp_audio/pp_audio.gml | specs alone, plus the G0-2 cue registry entry | 12, 14 (proposed) |
| game/scripts/pp_battle_commands/pp_battle_commands.gml | specs alone | 07 |
| game/scripts/pp_battle_director/pp_battle_director.gml | specs alone | 07 |
| game/scripts/pp_battle_text/pp_battle_text.gml | specs alone | 05, 07 |
| game/scripts/pp_camera/pp_camera.gml | specs alone | 03 |
| game/scripts/pp_config/pp_config.gml | specs alone | 01, 03, 06, 07, 08, 10, 11, 13 |
| game/scripts/pp_data/pp_data.gml | specs alone | 14 (proposed) |
| game/scripts/pp_dodge_arena/pp_dodge_arena.gml | specs alone | 08 |
| game/scripts/pp_dodge_recipe/pp_dodge_recipe.gml | specs alone | 09 |
| game/scripts/pp_dialogue/pp_dialogue.gml | specs alone | 05 |
| game/scripts/pp_map/pp_map.gml | specs alone | 04 |
| game/scripts/pp_map_tile/pp_map_tile.gml | specs alone, with card R46's tile manifest as the source of the numbers | 04, 15 |
| game/scripts/pp_overworld/pp_overworld.gml | specs alone | 04 |
| game/scripts/pp_scene/pp_scene.gml | specs alone | 06 |
| game/scripts/pp_drive/pp_drive.gml | specs alone, with knowledge/DRIVE-SHOT-LIST.md as the source of the twelve durations and the signs | 06, 14 (proposed) |
| game/scripts/pp_text/pp_text.gml | specs alone | 05 |
| game/scripts/pp_title/pp_title.gml | specs alone | 14 (proposed) |
| game/scripts/pp_input/pp_input.gml | specs alone | 02 |
| game/scripts/pp_font/pp_font.gml | specs alone | 13, 14 (proposed) |
| game/scripts/pp_ledger/pp_ledger.gml | specs alone | 10 |
| game/scripts/pp_look/pp_look.gml | the 8 bit look: one scale, one palette set per room | 03, 13 |
| game/scripts/pp_rng/pp_rng.gml | specs alone | 09 |
| game/scripts/pp_save/pp_save.gml | save, load and resume | 01, 10, 11 |
| game/objects/obj_pp_game | specs alone | 01, 02 |
| game/objects/obj_pp_debug_overlay | specs alone | 10 |
| game/objects/obj_pp_title | specs alone | 14 (proposed) |
| game/objects/obj_pp_drive | specs alone | 14 (proposed) |
| game/rooms/rm_pp_drive | specs alone | 14 (proposed) |
| tools/capture_drive.py | specs alone, plus the window primitives proved in tools/capture_title.py | 14 (proposed) |
| game/rooms/rm_pp_boot | specs alone | 01 |
| tools/art/make_title_ui.py | title art generator | 14 (proposed) |
| tools/gen_project.py | specs alone | 14 (proposed) |
| tools/check_project.py | specs alone | 14 (proposed) |
| tools/check_data.py | specs alone | 08, 09, 14 (proposed) |
| tools/check_cleanroom.py | this file | PLAN 1 |
| tools/check_provenance.py | this file | PLAN 1 |

Every "specs alone" row is owned by the entry "modules written from the specs alone" below. That entry, not either
withdrawn entry, is what a new module must be written from.

## the sprite palette rows and the title band plan (2026-10-22, card t_a1170172)

Status: this entry owns the palette half of the title art pipeline and no other row of the module map above. The code
it describes is `tools/art/scene_palette.py`, `tools/art/title_bands.py` and `tools/scene_palette_set.py`, which run at
build time and ship nothing; the GML it feeds is `game/scripts/pp_config/pp_config.gml` and
`game/scripts/pp_title/pp_title.gml`, both already owned by the "specs alone" entry.

Studied: the 2C02's two palette systems, as the repository already states them in ART-BIBLE 1.3 and in
`data/nes_palette.json` (which carries the four brightness rows and sixteen hue columns of the chip and the meaning of
the entry numbers). No decompiled, ripped, fan ported or commercial material of any kind was read, opened or searched
for this entry, and no other game's sprite sheet, code or data informed it.

Mechanics learned, in plain words: a sprite palette is not a subset of the background palettes and shares no entries
with them by rule. A sprite picks one of four rows of three colours plus a transparent state, per 8x16 group, and a
background picks one of four rows per 16x16 attribute area. So a sprite may carry an ink that no background at that
place spends, which is what a 1 px outline around a wordmark needs. Treating the sprite rows as copies of the band rows
looks tidy and makes the outline impossible, and it also flattens art that was authored for a different palette.

Our implementation differs by: the four sprite rows are written by hand in `data/palettes/scene_title.json`, one row per
group of sheets that really needs it, and `tools/check_scene_palettes.py` proves every 8x16 group of every title sheet
fits one of them. The band plan stays a background rule and only touches the strips it declares, so the two systems
cannot bleed into each other, and a sprite's backdrop-black is repainted into its own band palette except on the two
sheets that spend black as an ink. `data/scene_palettes.json` carries the band plan and the band sprite map as data
instead of leaving them inside a script. The title's text is one ink and no tint, because a tint is a multiply and the
product of that multiply was a colour the chip cannot output; a disabled row is marked with a rule in an entry both
ground bands declare.

Amended 2026-10-23, review round 2: a palette is only half of a drawable pixel, and the other half is alpha. A sprite
pixel is on or off, so a sheet that keeps a half transparent pixel is not made legal by having the right three colours:
the game blends it against whatever it sits on and the frame carries a value that is on no palette at all. That is how
24 pixels of `#616161`, `#001923` and `#619761` reached the captured title frame from the exhaust puff. Every pass that
writes a sheet now resolves partial alpha through `nes_tile.solid_alpha` before it repaints anything, which turns a fade
into the 2 px checker the hardware can actually draw, and a test holds every title sheet to alpha 0 or 255.

Copied expression: none.

## the 8 bit look: one scale, one palette set per room (2026-10-22, card G0-3)

Status: this entry owns `game/scripts/pp_look/pp_look.gml` and no other row of the module map above.

Studied: nothing. No decompiled, ripped or fan ported material was read, opened, searched or reasoned from for this
entry. The module was written from two documents of this repository, `specs\13-8bit-look.md` and
`specs\03-camera-and-scaling.md`, plus three official GameMaker manual pages read at the source today
(application_surface, gpu_set_tex_filter, display_set_gui_size) for the call shapes only.

Mechanics learned: how the engine's own frame pipeline is arranged, from the manual and from the two specs: an
application surface sized to the frame times an integer scale, a camera view of exactly the base frame, a GUI layer fixed
at the base frame so one GUI unit is one pixel, texture interpolation off once, and a resize noticed by polling the
window because the runtime has no resize event. The palette half is a rule from spec 13: at most 16 colours on screen,
chosen per room, drawn from one master palette by role name so the art can be re-coloured without new art.

Our implementation differs by: one module owns the frame instead of the camera module, so `pp_camera_apply_window` and
`pp_camera_scale_for` now delegate and a second scale computation cannot exist. The scale formula is spec 03's own
`max(1, min(6, floor(min(w / 256, h / 240))))` written once. The letterbox offset is stored as a whole number of pixels,
which spec 03 does not state and spec 13 implies. The palette sets are this game's own: a set is a list of role names in
`data\room_palettes.json`, the master palette carries 66 roles over 54 colours, and a set may not name a role the master
palette does not declare. Nothing here was taken from any other game's project file, code or data.

Copied expression: none.

## modules written from the specs alone (2026-10-19)

Status: this entry exists because the two study entries further down are withdrawn. Every row of the module map above is
owned here. It is the entry a new module is written from.

Studied: nothing. No decompiled, ripped or fan ported material was read, opened, searched or reasoned from for this
entry, and it names no studied source at all. Each module was written from its spec in specs\, and each spec was
confirmed against public genre design and the official manual in the reviews recorded in knowledge\SPEC-REVIEW.md and
knowledge\CLEANROOM-REVIEW.md.

Mechanics learned: none that a study supplied. The behaviours the modules implement are the specs' own decisions: a mode
registry with one request door and one fade (spec 01), an action table sampled once per step (spec 02), integer scaling
from the manual's own application surface resizing example (spec 03), a tile grid with a separate collision grid and a
trigger list (spec 04), a command table resolved by id (spec 07), a bounded arena with hazards as structs in one array
(spec 08), data recipes interpreted by one emitter (spec 09), counters with the route derived on read (spec 10), async
save behind a small state machine (spec 11). Those are public mechanics and our numbers, and the manual links for each
are in knowledge\gml-essentials.md.

Our implementation differs by: there is nothing to differ from, because nothing was studied. What the withdrawn entries
recorded as differences still stands as our design, with one downgrade: the project file shapes in
knowledge\gamemaker-project-format.md are unsourced and UNVERIFIED, and the modules are written so that nothing in game
code depends on them.

Copied expression: none.

## the title art generator and its test (2026-10-21)

Studied: nothing. No decompiled, ripped or fan ported material was read, opened, searched, fetched, downloaded or
reasoned from for this entry. The sources were this repository's own data\palette.json, the art contract in
TITLE-COORD.md, the game\sprites_src\title\spr_pp_title_logo.png, spr_pp_font8.png and spr_pp_menu_cursor.png that
the generator writes, and the Pillow documentation for the drawing primitives used.

Mechanics learned (public mechanics and our own decisions, not a studied design):
- A sprite sheet of a pixel font is one frame per glyph, laid out left to right in a fixed order, so a glyph is
  addressed by index rather than by name. The contract is that the strip is 8x8 per frame and 44 frames long, and the
  test checks the frame count and the strip's pixel width against it.
- A sprite sheet of an animated sprite holds its frames side by side, so a frame is a horizontal slice of one image and
  the strip's width is the frame count times the frame width.
- A pixel art file is a PNG whose every visible pixel is an exact entry of the master palette, and a room has a colour
  cap, so a generator can be checked by comparing the set of colours it used against the palette and counting them.
- Two runs of the same generator over the same input must produce byte identical files, so the generator is
  deterministic by construction: no clock, no randomness, no dict ordering that depends on insertion order.
- A child process spawn is the fragile part of a test harness, not the work. The generator's job was moved into a
  function so the test can call it in process, which removes the whole class of failure where the child fails to start
  (measured on this machine as "The request is not supported", WinError 50) and the failure is misread as a fault in
  the art.

Our implementation differs by: the generator lives in tools\art\make_title_ui.py, is a pure function of a root
directory, writes into game\sprites_src\title\ and produces output\title_ui_preview.png as a contact sheet at 3x. The
test writes into a throwaway copy of the data tree and never into the live tree, and it proves the properties above
rather than asserting them in a comment: byte identical reruns, every pixel in the palette, the colour cap, the
contract sizes and frame counts, the logo reading PRIMORDIAL over PARADOX, the crack crossing the O of PARADOX, the
cursor being an outlined arrow that changes state, and the committed PNGs matching what a fresh run produces.

Copied expression: none.

## the Map 2 ship tileset and its sample map (2026-10-21, card ENV-TILES)

Studied: nothing. No decompiled, ripped or fan ported material was read, opened, searched, fetched, downloaded or
reasoned from for this entry, and no published game's art was looked at to draw these tiles. The sources were this
repository's own `data\nes_palette.json` (the Ricoh 2C02 outputs, built and cited by `tools\art\nes_palette_build.py`),
`knowledge\CHARACTER-BIBLE.md` REVISION 2 for what the ship is (Percy Skye, 23, Royal Navy lieutenant, grey steel
corridors, bulkheads, a wardroom, no knight armour), `knowledge\ART-BIBLE.md`, spec 13, `specs\15-env-tiles-ship.md`,
and the Pillow documentation for the drawing primitives used.

Mechanics learned (public hardware facts and our own decisions, not a studied design):
- A NES background is built from 16x16 attribute areas that each select 3 colours plus the one backdrop the frame
  shares, and from 8x8 pattern tiles. So a drawing that is legal at 16x16 has to be re-checked per 8x8 quarter if it is
  ever to be cut into pattern tiles.
- A 10 colour scene is built by spending the budget in groups: here black backdrop, a steel ramp (dark, mid, light),
  a sea ramp (deep, mid, crest), and rust, orange, brass. Propaganda-era steel reads as steel when the light ramp runs
  in one direction down the plate, not when it is speckled.
- A tileset that a map can be validated against carries its own properties: solid, climb, palette group, animation
  pairs. Deriving the collision layer from those properties makes "walls and objects are solid" a measurement instead
  of a second hand transcription.
- A deterministic generator (no clock, no unseeded randomness, sorted JSON keys, LF endings) is what lets committed
  art be regenerated and diffed, so the picture in the repository is the code that made it.

Our implementation differs by: the generator is `tools\art\make_env_ship.py`, a pure function of a root directory that
writes five files (the sheet, its animation contract JSON, the Tiled tileset, the sample map and a 3x preview) and
nothing else. Every tile function paints one 16x16 cell through six primitives (`rect`, `frame`, `hline`, `vline`,
`annulus`, `disc`, plus `hazard` and `checker`) so no tile is a pasted bitmap and each one can be read as geometry. The
palette is a 10 entry table in the file, and `tools\check_env_tiles.py` compares every opaque pixel against it and
against `data\nes_palette.json`, so a colour cannot drift into "nearly NES". The map is written by the same script from
a legend of letters, its collision layer is computed from the tileset's solid flags, and the preview is rendered from
the map file rather than drawn beside it. The name of the map file is decided by a rule that refuses to overwrite
another lane's `ship_sample.json`. `tests\test_make_env_ship.py` pins the five outputs, byte identical reruns, the two
colour ceilings, the collision layer against the flags, reachability, both halves of the name rule, the committed files
against a fresh build, and the checker's own verdict.

Copied expression: none.

## the NES validator, the 8x8 font and the window frame (2026-10-21, card NES-CHECK)

Studied: the NESdev wiki pages "PPU palettes" (https://www.nesdev.org/wiki/PPU_palettes), ".pal" and
"PPU pattern tables" for the hardware rules only, and the licence file of Press Start 2P from its official home in
google/fonts. No game was opened, no ROM, tile sheet, screenshot or decompiled code was read, and no existing game's
window frame was measured. What the wiki gave us is a specification: 64 palette outputs, 4 background and 4 sprite
palettes of 3 colours plus a shared backdrop, 8x8 pattern table tiles, 16x16 attribute areas, 25 colours on screen.

Mechanics learned (public hardware facts, not a studied design):
- A pixel is legal only if it is one of the 64 outputs, and the count of distinct colours in one frame is capped at
  4 palettes x 3 colours x 2 kinds plus the backdrop, which is 25.
- Sprite tiles pick from 3 colours plus transparent, background areas pick 3 plus the one backdrop shared by the frame,
  so the same 8x8 drawing can be legal as background and illegal as a sprite.
- A bitmap font ships inside a sprite sheet, so its pixels answer to the same rule as any other sprite: the old
  project paper colour `#c8c8d4` was not a 2C02 output and the font failed the validator on exactly that pixel. The
  fix was the chip's own white, `#fcfcfc` ($30), not a new palette entry.
- Press Start 2P was designed on an 8x8 grid, so rasterising it at 8 px and thresholding the alpha gives one crisp
  cell per glyph with no resampling.

Our implementation differs by: `tools\nes_check.py` checks the four rules plus the grid and the screen cap, lists the
offending tile or area for each failure and exits 1; `tests\test_nes_check.py` has a passing and a failing PNG fixture
for each rule, and also runs the validator on the committed font and window. The window frame in
`tools\art\make_pp_window.py` is drawn from nine hand written 8x8 bitmaps (border, inner line, fill, rounded corner),
imitating a layout convention rather than any particular game's artwork.

Copied expression: none.

## save, load and resume (2026-10-20)

Status: the live entry for card t_a311bdff: the save slot in game\scripts\pp_save, the Save/Load event at
game\objects\obj_pp_game\Other_72.gml that forwards async_load to it, and the save point trigger in data\maps\all.json.
It owns the pp_save row of the module map above and no other row. It names no studied source.

Studied: nothing. No decompiled, ripped or fan ported material was read, opened, searched, fetched, downloaded or reasoned
from for this entry. The sources were this repository's specs\11-save.md, specs\10-route-ledger.md and
specs\01-state-machine.md, plus these official manual pages, each read at the source on 2026-10-20: the Save/Load
asynchronous event page, buffer_save_async, buffer_load_async, buffer_create, buffer_write, buffer_read, buffer_tell,
buffer_seek, buffer_delete, buffer_get_size, json_stringify, json_parse, date_current_datetime and
date_datetime_string.

Mechanics learned (public mechanics and our own decisions, not a studied design):
- An asynchronous buffer save and load report back through one event carrying "id" (the value the function returned) and
  "status" (true when the transfer worked), which is what keeps a save from blocking a frame.
- A relative filename given to those two functions lands in the save area's "default" folder, and every other file
  function would need that folder in the path. Existence is therefore answered by a load attempt and not by a path guess,
  which is also why the title asks the slot once at boot instead of probing a file.
- buffer_string writes and reads a null terminated string while buffer_text does not, and buffer_tell is the number of
  bytes a buffer holds after writing, which is what hands the exact byte count to the write.
- json_parse throws on invalid text and json_stringify stores an asset's handle rather than its name, so every parse
  sits in a try/catch and every id in the document is a name.
- Our own rules from the specs: the format number is checked before any other field, the last good file is rotated to
  .bak, a load validates every field and then applies nothing, and the route ledger is saved as its four counters plus
  its named flags with the route derived on read.
- MEASURED on this runtime on 2026-10-20 while fixing the save crash (card t_b72efa81), by printing the values from a
  running game rather than by reading the manual: the request id is 0 for the first async call in the process, so an
  `id <= 0` test wrongly calls a good first request a refusal; a buffer handle has typeof "ref" and is_real false, so
  is_real must not be used to test one; a number read with buffer_read(buffer_u32) is an int64 with is_real false and
  is_numeric true, so is_numeric is the test for a number that came out of a file; and a buffer handed to the async
  pair cannot be deleted until the event has reported back. These are runtime facts about the engine, not a design
  taken from anywhere, and they are written up in knowledge\gml-essentials.md section 8.

Our implementation differs by: there is nothing to differ from, because nothing was studied. The shape is a 4 byte
byte-count followed by the JSON text in a fixed 64 KB buffer, a state enum (PPSaveState) in pp_config, bounds and message
timings as macros in pp_config, a save point as a trigger of kind "save" in map data, and the map, spawn, item and power
ids all coming from data\. The title line, the backup rotation, the panel timing and the save point are spec 11's own
decisions. The buffer fields hold a handle or undefined and never a number, the existence test is the async pair's own
status rather than a path guess, and the length prefix is read with is_numeric.

Copied expression: none.

## WITHDRAWN incident record: battle state machine and turn loop (2026-10-19)

Status: WITHDRAWN on 2026-10-19 by card t_bfaff47b, at the manager's order that documentation in this repository stand
on public sources only. This entry described the internals of a decompiled commercial game project. Anything that only
that read supported is withdrawn rather than softened, and this entry is no longer a source for any module: no current
module descends from it, and the module map above points every module at "modules written from the specs alone". It is
kept so the incident of what was studied stays on the record, and so nobody re-learns it by accident.

Studied: (historical record of where a mechanic was first noticed, not a source and not navigable) the battle
controller's create, step, draw and alarm events; the whole turn loop script; the phase handoff inside the spell script;
the attack config switch and its controller data; the bullet controller and the bullet maker objects; the player
marker's step event; the graze box collision; the monster script's mercy handling; and the battle start script.

Mechanics learned:
- A battle is an overlay inside the running room, not a separate room: starting one creates a background object, an
  encounter object and a single controller at (0,0), and the overworld objects stay alive underneath.
- One controller object owns the whole fight in its Step event. The phase is two shared globals: a coarse fight phase
  number and a menu panel number, and the Step event is a long if chain over those numbers. Spells, acts, items and
  the attack timing game are separate objects created when a phase needs them.
- The turn loop is: for each party member in slot order, pick a command, then when the last member is done resolve
  acts, then the attacking phase, then the enemy attack, then refill items and restart. A per member "can act" check
  skips downed members. Cancel walks back to the previous member and undoes that member's staged choice.
- Commands are staged in per member arrays (action id, target, special, and a per member copy of the item list), and
  the whole set is committed when the last member confirms. Nothing applies immediately.
- The player attack is a timing minigame object that yields the damage number; the enemy reply is a dodge phase.
- The dodge phase is: arena box object grows in, marker object exists with a grace/invulnerability counter, a
  controller object ticks a timer and calls one big switch on a pattern id, spawning generic bullet objects that
  carry damage, speed and lifetime; a small child box on the marker handles grazing and contacts.
- Bullet controllers carry a single pattern id plus timing fields, and the pattern bodies live in one script as switch
  cases; a pattern is code, not data. Difficulty scaling is a ratio multiplier derived from how many enemies remain.
- Spare is a per enemy mercy counter clamped to 0 to 100 and raised by act results; spare is allowed once it reaches
  the cap. The fight result is written per enemy slot as a result enum (spare, pacify, frozen, kill) into the save flag
  array, and the kill route is derived later from those flags rather than stored as a separate morality value.
- The end of a fight is a message object plus a timer, then a single cleanup script that destroys every battle object
  by name (controller, marker, arena, writers, faces, delayed script objects) and returns to the overworld.

Our implementation differs by (files: game\scripts\pp_battle_director, pp_battle_commands, pp_dodge_arena,
pp_dodge_recipe, pp_ledger. The names pp_battle_turn and pp_route_ledger in an earlier draft were the plan's working
names and do not exist):
- A battle is a MODE owned by pp_app (specs\01), drawn over the suspended map, so the overworld is never destroyed and
  never rebuilt. There is no battle room and no global phase number.
- The director is one enum state machine (`PPBattlePhase`) with explicit enter/step/exit per state, held in a struct
  (`battle`), not in globals and not in a long if chain. Every transition goes through `pp_battle_phase_set()`.
- The turn queue is a data-built array of party slots (`pp_battle_turn_build`), not a slot order implied by an array
  index, and staged commands live on the actor entries themselves.
- Commands are a data-driven table (id, label, enabled predicate id, disabled reason) resolved by id string
  (`fight`, `power`, `talk`, `spare`, `item`), so adding a command is a data change and the disabled reason is a
  returned string that the menu draws, rather than a per case branch.
- Damage, hp, attack, spare thresholds and pattern linkage come from data files (`data\enemies\*.json`,
  `data\encounters\*.json`). No enemy number appears in GML.
- Spare is a trust counter on the encounter entry with a data threshold per enemy, plus an hp threshold, and the
  ledger records `kill` or `spare` once through `pp_ledger_record_result()`; the route is derived on read, never stored.
- Bullet patterns are data recipes (`data\patterns\*.json`) interpreted by one emitter, with our own deterministic RNG
  (`pp_rng_*`), instead of a script of switch cases. Shape names, spawn exclusion, warning window and the step cap are
  enforced by the arena, not by each pattern.
- The arena is one struct with geometry, marker state and a hazard array; hazards are plain structs in an array, not
  one object instance per bullet, which makes the whole phase serialisable and testable in the checker.
- The dodge marker is 8x8 at 2 px per step over a 160x100 box per specs\08, and input arrives as one normalised
  vector from pp_input, not from four direct key reads inside the marker object.

Copied expression: none.

## WITHDRAWN incident record: room and object conventions across a whole game (2026-10-19)

Status: WITHDRAWN on 2026-10-19 by card t_bfaff47b, for the same reason as the entry above, and with the same effect.
Its file shape facts were never in the official manual, which publishes the role of each project file and not its field
or file name schema. No current module descends from it: the module map points every module at "modules written from the
specs alone", and knowledge\gamemaker-project-format.md marks the shapes unsourced and UNVERIFIED. The historical body
is kept below as the incident record, and the counts in it are history, not evidence. One artefact of that copy is
still visible in the repo: the .yyp carries `IDEVersion 2024.1400.0.911`. Nothing reads it, no check asserts it and
GameMaker rewrites it on the first save, so it is inert; it is named here rather than quietly replaced with a number
nobody here has seen.

Studied: (historical record, not a source and not navigable) the project file and its resource graph, the folder layout
on disk, ten object resource files, three room files, three script files, the fonts folder, the options folder, and the
event file naming across every object.

Mechanics learned, with the counts as measured then (history, not evidence):
- 1148 resources in one flat list in the .yyp, each entry only {"id": {name, path}}, grouped into a virtual folder
  tree declared separately in a Folders array (folderPath strings like folders/Custom/Objects/World). Folders are a
  browser view; they are not directories on disk and their .yy files are not required for the project to load.
- One directory per resource, named exactly like the resource. A script directory holds one .gml plus one .yy. A room
  directory holds exactly one .yy and NO separate layer files: layers, instances and tile data are all inside that one
  room .yy. An earlier note in knowledge\gamemaker-project-format.md said one .yy per layer; that is wrong for this
  IDE version and is corrected here.
- Object event files are named by event type and number and there is one file per event: Create_0, Step_0, Step_1
  (begin step), Step_2 (end step), Draw_0, Draw_64 (draw gui), Draw_76, Alarm_0 upward, Destroy_0, CleanUp_0,
  Other_10 upward (user events), Collision_<object>. 525 event files over 232 objects.
- The .yy is JSON with trailing commas allowed and a version tag per resource kind ("$GMObject", "$GMRoom",
  "$GMScript", "$GMMainOptions"). Assets carry both "%Name" and "name"; resourceType and resourceVersion "2.0".
- Objects support single inheritance via parentObjectId (48 of 232 use it), so shared behaviour lives in a parent
  object and children only override events they need.
- Rooms hold a layer list ordered by depth: instance layers, background layers, tile layers, asset layers and path
  layers. Instance layers carry an array of instances with objectId as {name, path}, x, y, scale, rotation, and a
  hasCreationCode flag. Room size and view settings sit in roomSettings and viewSettings inside the same file.
- Game options are per platform (options\main, options\windows, and one per export target), each a .yy with a fixed
  key set; the Windows one carries executable name, texture page size, interpolation and scale flags.
- Naming across the whole game is flat and prefix based: obj_, scr_, spr_, snd_, fnt_, rm_/ROOM_/PLACE_, and scripts
  group by feature with no namespaces. Several config scripts are 30 to 50 KB switch tables of content.

Our implementation differs by (files: game\PrimordialParadox.yyp, game\objects\*, game\rooms\*, game\scripts\*):
NOTE, 2026-10-19: this list was written when the plan had four objects, two rooms and a module called pp_app_modes.
The project today has two objects (obj_pp_game, obj_pp_debug_overlay), one room (rm_pp_boot) and sixteen scripts, and
the module is pp_app. The list is kept as the withdrawn record says, with the counts corrected here rather than there.
- Same on-disk contract (one directory per resource, one .yy per resource, one .gml per event) because that is what our
  generator writes and it is all we can say: the manual publishes the role of a .yy and not a layout, so this is
  unsourced in knowledge\gamemaker-project-format.md. Our naming scheme is our own: every script is a `pp_` module
  (`pp_input`, `pp_app`, `pp_battle_director`, `pp_dodge_arena`), every object is `obj_pp_*`, every room is `rm_pp_*`.
- We use NO object inheritance. There are two objects at all; behaviour lives in functions that take a struct, so a
  parent object hierarchy is unnecessary and the logic is testable without instances.
- Content never lives in a config script. Every table that their project writes as a GML switch (items, spells,
  enemies, patterns) is a JSON file in data\ validated by tools\check_data.py before it can be loaded.
- Rooms are generated from data too: one battle presenter room and one boot room, so adding a map does not add a
  room, it adds a data file. This is the opposite of a room per screen.
- Every .yy we write is strict JSON (no trailing commas) so that tools\check_project.py can parse it with the Python
  standard library. The manual calls the format JSON-like and does not define it further, so strict JSON is our
  reading of "JSON-like", not a documented equivalence.
- Folder view is a single `Primordial Paradox` folder tree in the .yyp, and it is generated by tools\gen_project.py
  so the resource list, the folder list and the disk can never disagree. The folder entries are unsourced: the manual
  does not publish them.

Copied expression: none.

### What is deliberately NOT studied or taken

- No art, sprite, font, sound, music, dialogue, character name or item name from either game. Every asset in this
  project is original or public domain Greek myth naming.
- No text from any dialogue file was read. Only system structure was opened.
- The NES constraint in PLAN.md section 2 comes from Nayil's notebook and the research note, not from any decomp.

## clean-room re-review 2026-10-19

Reviewer: code-review, on card t_ec0fb8be, after the manager's breach notice on t_f7d3a69d.

Studied: nothing. No decompiled, ripped or fan ported material was opened, searched, read or reasoned from for this
review. The two entries above were read only as this repository's own historical text, not as a route to the thing they
describe, and the file names they used to carry were removed rather than looked up. The sources were
knowledge\genre-design.md, knowledge\gml-essentials.md, knowledge\gamemaker-project-format.md, knowledge\igor-cli.md,
knowledge\LICENSES.md and the official manual pages each spec already cites, re-read at the source where a rule needed
its own ground.

Mechanics learned: none that are new. The finding is that the specs' mechanics are genre mechanics: the turn and dodge
alternation, the talk and spare route, no EXP progression and the visible encounter map are described in public terms in
genre-design.md, and the numbers in the specs are this project's own decisions. Two knowledge files did carry study
derived claims; both were rewritten rather than reworded, the project format facts are now UNVERIFIED, and the delta
file no longer rests a delta on what a study pass saw.

Per spec, what changed. The same verdicts, with this reviewer and date, are in knowledge\SPEC-REVIEW.md.

| Spec | Verdict | What changed, or why it stands |
| --- | --- | --- |
| specs/01-state-machine.md | confirmed | Mode enum, one owner, one request door, 12 step fades and a 6 step input lock are our decisions; the spec asserts nothing about what the map does under a battle, and that gap stays open as delta T1. |
| specs/02-input.md | confirmed | The action table, the single sample point and the edge derivation come from the manual's keyboard_check_pressed and Event Order pages, which the spec cites; deadzone and repeat timings are ours. |
| specs/03-camera-and-scaling.md | confirmed | Integer scale, one viewport and an application surface resize follow the manual's page; dead zone, look ahead and the 4 pixel cap are DECISIONs. |
| specs/04-overworld-rails-and-triggers.md | confirmed | Tile grid, separate collision grid and trigger list, rails and visible encounter markers are genre-design section 6; the 20 step trigger lock and the 30 step respawn are our own fixes for failure modes anyone can name. |
| specs/05-dialogue.md | confirmed | Typewriter, portrait, pages and a conditional choice list are the ordinary text box of the genre; every geometry number is a DECISION and the two control codes are ours. |
| specs/06-cutscene-runner.md | confirmed | A data command list with one blocking command at a time and branch as the only control flow is the ordinary scripted scene form; each command and number is ours. |
| specs/07-battle-director.md | confirmed | Five entry menu, trust and spare thresholds and no EXP are genre-design sections 3 to 5, and the turn flow is the public think/move alternation of section 2. Closest call: the shape of the turn loop. It is the spec's own phase list, expressed as a data driven turn, and no rule depends on a studied controller. |
| specs/08-dodge-arena.md | confirmed | Bounded box, bright marker, telegraph, damage per hit and invulnerability are genre-design section 2; box size, speeds, exclusion radius and step cap are PP decisions. |
| specs/09-bullet-pattern-recipes.md | confirmed | Recipes as data and the fairness ladder are our decisions, and "a pattern is data, not a switch case" is the deliberate opposite of the studied design, so it is a difference and not a copy. Closest call: the per pattern field list, which is the spec's own vocabulary for shapes anyone can describe. |
| specs/10-route-ledger.md | confirmed | Counters plus a route derived on read match genre-design section 4 ("coarse, not a score"), and deriving once instead of storing twice is single source of truth reasoning. Closest call: the "never stored" rule, which stands on that reasoning plus delta T12 rather than on anything studied. |
| specs/11-save.md | confirmed | Versioned JSON with a .bak, a format check first and a try/catch around json_parse follow the manual's Save/Load and json pages, which the spec cites. |
| specs/12-audio.md | confirmed | Bus priorities, the crossfade and the channel budget follow the manual's audio pages. Rule 3's claim that loop points come from the file's own metadata is NOT supported by those pages; it is recorded as an open factual defect in SPEC-DELTAS C1 and is not a clean-room finding. |
| specs/13-8bit-look.md | confirmed | Palette size, two dither patterns and the frame rules are our decisions; the battle sprite convention is genre-design section 7. Rule 2's per pixel check cannot run yet, which delta C3 already records. |

Per source file outside the specs.

| File | Verdict | What changed, or why it stands |
| --- | --- | --- |
| knowledge\gamemaker-project-format.md | rewritten | The section headed "verified against a real GameMaker 2024.1400 project" cited the quarantined copy as its authority and counted its files. Rewritten: the manual publishes the roles of the project files and not their field or file name schema, so the four shape claims are now UNVERIFIED and point at the IDE reference procedure the file already had. |
| knowledge\SPEC-DELTAS.md | rewritten | The framing said the list came after a study pass, and T1 said "study shows an overlay is the usual answer". Rewritten: the framing names the quarantine and says every item was re-derived from public material, T1 now reasons from specs 01 rules 4 and 5 plus genre-design section 2, and C1 is restated as a claim the manual does not settle instead of a correction the manual proves. |
| knowledge\genre-design.md | confirmed | Every note is a public description of genre play or our own DECISION; no studied construct, no copied text, and the file states its own source rule. |
| knowledge\gml-essentials.md | confirmed | Every fact carries a manual link and the date it was read, a second read pass re-checked the words, and DECISIONs are labelled. |
| knowledge\igor-cli.md | confirmed | The command line build facts come from the manual's Building via Command Line page, Monthly and LTS, with the difference between the two branches recorded. |
| knowledge\LICENSES.md | confirmed | Each licence was read from the repository's own licence file and its API metadata; nothing was cloned or downloaded, and nothing is imported. |
| knowledge\README.md | rewritten | The index still advertised a study folder as a live, read only source and undercounted the deltas. Both rows corrected: the quarantine is stated and the delta count matches the file. |

Our implementation differs by: nothing in the logic of the 23 GML modules. Eight module headers were rewritten, and each
one only removed a provenance parenthetical describing the internals of the quarantined copy, replacing it with the spec
the structure is written from; knowledge\CLEANROOM-REVIEW.md names the construct in each case. The difference lists in
the two entries above stand, with one substantive downgrade: the project format facts are now UNVERIFIED rather than
confirmed. Nothing was published, uploaded or pushed.

Copied expression: none.

### Withdrawal pass, 2026-10-19 (card t_bfaff47b)

Same reviewer, same day, after the manager's order that this repository's own documentation stand on public sources
only. What changed, and why it is not a re-review of the specs:

- The two study entries above are now WITHDRAWN incident records. They were re-confirmed earlier in the day from
  public material, but the manager's rule is stricter than that: the entry itself was written from the quarantined
  read, so it is withdrawn rather than softened. Each carries one line saying no current module descends from it.
- A new entry, "modules written from the specs alone", owns every row of the module map. It names no studied source.
- knowledge\SPEC-DELTAS.md: every one of the 24 deltas now carries an explicit source line, and the file carries a
  source index a reader can audit without reading the detail. Totals by script: 3 `manual`, 4 `genre`, 17 `internal`,
  0 `withdrawn`. The `internal` form is a fourth form the card did not name: those items are spec against spec or
  arithmetic over our own numbers, and labelling them manual or genre would be an invented citation.
- knowledge\gamemaker-project-format.md: re-derived from the Project Format page read today. The page publishes the
  role of each file and not one field name, so the shapes our generator writes are now labelled unsourced rather than
  described as what a real project contained, and the honest cannot-verify list is kept.
- Counts in the withdrawn room entry that were true when it was written and are not true now (four objects, two rooms,
  a module called pp_app_modes) are corrected in a NOTE inside that entry rather than silently edited.
- Not touched: any GML or data file, any spec, and the substance of any delta. Eleven module headers still cite the two
  withdrawn entries by name (pp_app, pp_battle_commands, pp_battle_director, pp_camera, pp_config, pp_dialogue,
  pp_dodge_arena, pp_ledger, pp_map, pp_overworld, pp_scene), and pp_input cites this file without naming an entry.
  They are named in the card's completion summary for a gamedev rewrite card, because this card is documentation only.

Checks run on this machine for this pass are recorded in DEVLOG.md, top entry.

## INTRO-1 intro shot (2026-10-22)
Studied: the NES fade rule as documented in knowledge/ART-BIBLE.md and the 2C02 table in data/nes_palette.json.
Mechanics learned: a hardware fade rewrites each palette entry to a darker row of the same hue, and past the
darkest row the entry is black, which is why a four step fade ends on a black screen instead of a dark blue one.
Our implementation differs by: the fade is pre-drawn into named strips beside each art strip and picked by name at
runtime, so the shot costs no per-pixel work and every strip is checked against the 55 usable PPU entries.
Copied expression: none.

## G0-2: the music cue registry and the crossfade bus (2026-10-22)

Studied: nothing outside this repository. The cue ids, titles, meters and tempos are the musician lane's own cue list
(note round1\musician.md, PP-01 to PP-16), which is our project's document, and the bus rules are spec 12. Every
behaviour of every audio call used is cited from the official GameMaker manual page read on 2026-10-22, named in the
module header: audio_play_sound, audio_sound_gain, audio_pause_sound, audio_resume_sound, audio_stop_sound,
audio_is_playing (whose own note says it still returns true for a paused sound), audio_channel_num, audio_create_stream
(with audio_destroy_stream), audio_create_buffer_sound (whose page defines the audio_mono and audio_stereo constants it
is given), and window_has_focus.

Rule 9 of spec 12 is not proven, and this entry records that rather than quoting the rule back as if the engine said
it. audio_channel_num.htm says a sound of lower priority is stopped to free a channel when the limit is reached; it
says nothing about which of several equal priority sounds goes, and nothing about age. "Replaces the oldest of that
kind" is therefore our wish, not a documented behaviour, and the module comment says so.

Mechanics learned: a music bus is three separate things and keeping them apart is what makes it simple. One, a registry
that turns a stable id into the file to stream, held in data rather than in code, so a new render arrives as a file and
never as an edit. Two, a crossfade that is only bookkeeping: two instances live for the length of the fade, the outgoing
one is driven to zero and then stopped, and a step function finishes the job, because a fade that is never followed by a
stop is a leak or a click. Three, a pause rule that is a poll, not an event: the window's focus is a question that can
be asked every step, and audio_pause_sound plus audio_resume_sound already keep the play position, so nothing has to
remember where the music was.

Our implementation differs by: registering the cues under the musician's ids PP-01 to PP-16 in data\audio.json with an
asset name and an explicit placeholder flag, instead of a code list of file names; keeping the old sounds table as the
stand-in behind a cue that has one, so the data moves across one room at a time; treating an unknown cue id as a checker
failure at build time and a silent log line at run time, never a crash; polling window_has_focus from pp_audio_step
rather than trusting an event number this project has never compiled; and reporting the fade as 30 steps of the spec but
converting to milliseconds at the one place the manual says the engine wants them.

Copied expression: none. No audio file was generated, downloaded or invented. Nothing was heard by the lane that wrote
the module, and that is a limit of a scripted build and not of the machine: GameMaker LTS 2026 is installed here and
this tree builds and runs, so the module compiles and its log lines are real (build/capture-intro-game.log). What the
checks prove is the data, its cross references and the arithmetic, by tools\check_data.py and its tests.

---

## SFX-WIRE: the effects bus (2026-10-22)

Studied: none outside this repo. The cue bus, the buffer sound load and the blip rule are written from our
own specs 05 (dialogue: blip every three characters, never on a space), 12 (audio) and 14 (title). The effect WAVs
are synthesised by tools/sfx.py from the 2A03 voice set with a manifest of their own; no audio and no code was
taken from anywhere.

Mechanics learned: a cue is a name. The bus looks the name up in a manifest measured from the file header, loads the
data chunk once into a fixed buffer and plays it with audio_play_sound as a buffer sound. A cue with no file, no
manifest entry, or a measurement that does not fit stays silent and says so in the log; nothing throws.

Our implementation differs by: the manifest numbers are measured by tools/sync_art.py (mirror_sfx) from each WAV
header instead of assumed, the three blip pitches are chosen per speaker by pp_audio_blip_cue, and the theme stays an
external OGG stream while the effects are buffer sounds, so a 60 ms tick never decodes from disk.

Copied expression: none.

Verified by log on the 2026-10-21 23:40 build: menu_move, menu_select and menu_cancel from a scripted title menu,
and text_blip_a from the intro crawl, with no PP CRASH. footstep, door_hatch and encounter_swoosh are wired in
pp_overworld and pp_app but are not yet proven in a scripted run.

---

# Subsystem study, 2026-10-22 (twelve dossiers, doctrine and audit)

Read: the Deltarune decompilation (TeamBlossomDevs/DeltaruneDecomp) and the Undertale decompilation
(kittibyte/UndertaleDecomp), cloned read-only into knowledge/study/, which is gitignored. Deltarune is the source for
all twelve entries below; Undertale was read for confirmation of the same engine patterns and did not change any
conclusion. Each entry names the dossier under knowledge/study/DOSSIER/ that the next implementer codes from, and the
committed doctrine each derives into is knowledge/FOX-STYLE.md.

No code text, identifier, sprite, font, sound, music, data table, name or line of prose from either repository is in
this project. The dossiers are prose only. Verified by tools/check_cleanroom.py.

## 1. battle state machine

Studied: the Deltarune battle controller object (create, step, draw) and its submenu branching. Dossier
01-battle-state-machine.md, doctrine section 1.

Mechanics learned: one controller object owns the whole battle and its mode is a menu index plus three flags, not a
state graph. Submenus are index values with per-character cursor memory in a small 2D array. Input is edge triggered
through four counters that must go negative before a press counts. After each committed action one shared call
advances the turn. The dodge phase is a timer that, at zero, destroys bullets and generators in one frame, un-darkens
the arena, returns the player marker and arms a 15 frame hand-back alarm.

Our implementation differs by: keeping one owner but making the mode a named phase value in a battle struct rather
than interacting globals, so the battle can be instantiated and tested twice. Turn order is a queue built at round
start, not a fixed three slot index. Bullets are cleared by a typed owned list rather than an empty parent object, so
the guarantee survives while the mechanism is testable. Our command set and our recover slot naming are ours.

Copied expression: none.

## 2. morality and no-EXP routing

Studied: the monster defeat path, the mercy accumulator, the monster setup table and the battle aggregate flags.
Dossier 02-morality-and-no-exp.md, doctrine section 2.

Mechanics learned: every monster's experience field is assigned zero in every branch of the setup table, so the
running total is always zero and money is the only reward axis. Each enemy gets an outcome flag when it leaves the
fight (killed, spared, pacified, or a fourth kind), defaulting to spared and overridden to killed only when health
actually reached zero. When the last enemy leaves, the fight computes a verdict that is generous: pacified beats
spared beats killed. Four durable counters, incremented at the same moment as the per-enemy flag, are what the story
reads later. Separately, a per-enemy mercy accumulator with a per-monster cap gates whether spare will work.

Our implementation differs by: recording each enemy's exit as one of our three named states plus a fight verdict, and
deriving the route on read rather than storing a second copy. Our vocabulary is our own. We deliberately carry no
experience field at all, not even a zeroed one, so a future contributor cannot make it non-zero and break the
premise. Resolve pressure is data driven from the enemy row rather than a setup switch.

Copied expression: none.

## 3. bullet pattern system

Studied: the empty bullet and generator parent objects, several concrete projectile objects, the player marker and
its collision event, and the dodge phase teardown. Dossier 03-bullet-patterns.md, doctrine section 3.

Mechanics learned: two empty parent objects with no events exist only so the controller can mass destroy every
bullet and every generator in two calls at the end of a phase, which is why nothing leaks into the command menu.
Concrete patterns are one hand-written object each, with their own timers, that spawn bullet children. Collision is
handled on the player marker rather than on each bullet, so damage, invulnerability and the hit sound live in one
place.

Our implementation differs by: keeping the guarantee and inverting the ownership. A pattern is a validated data
recipe compiled once into a stable sorted spawn list and interpreted by one runner that owns every projectile, so
clearing the arena is one call that cannot be forgotten and works in a unit test with no room running. Pattern
authoring is data, which is a deliberate divergence: the studied game hard-codes each pattern as an object.

Copied expression: none.

## 4. battlefield layout and turn flow

Studied: the encounter setup that places actors, the controller's layout constants, battle text placement and the
turn advance call. Dossier 04-battlefield-layout-and-turn-flow.md, doctrine section 4.

Mechanics learned: all placement is view relative. Party on the left at a fixed x, enemies on the right at a fixed x,
with three explicit party size cases that recentre the group vertically. The arena is a band between two y values,
and the narration writer and its portrait are created at fixed offsets from the view origin, the portrait four
pixels inside the text corner. A round is intro, command in slot order, resolve, dodge, apply, then next round or
victory, and there is no fallback where enemies simply deal numbers.

Our implementation differs by: putting every one of those constants in one layout module overridable per encounter,
expressing the party size cases as data rows rather than branches, and building the turn order as a queue. Our
numbers are derived from our own 256 by 240 frame, not reused.

Copied expression: none.

## 5. room and event flow

Studied: room files and their layered instance lists, a door object's create, collision and alarm events, the marker
helper, depth-from-y, and the story progress global. Dossier 05-room-and-event-flow.md, doctrine section 5.

Mechanics learned: transitions are door objects, not a transition manager. The collision event deactivates overworld
projectiles, sets a busy interaction state, spawns a fade out, and arms an 8 frame alarm exactly once thanks to a
touched guard that makes the transition idempotent. The alarm sets an entrance value, spawns a persistent fade in and
moves to the next room, so the fade survives the room change and the next room knows which door was used. Story
scenes are one bespoke object per scene with a fractional counter, branching on one story number, and dialogue
completion is detected by polling that the dialogue object no longer exists.

Our implementation differs by: keeping the door, the touch guard and the entrance flag, but routing them through one
transition module that owns the fade and the room change so no scene can implement half a transition. Scenes are
validated command lists interpreted by one runner rather than one object each. Story progress is one named value in
the save payload, not an index into a shared flag array.

Copied expression: none.

## 6. save layout

Studied: the save entry point, the per-slot save process, the async buffer save and load functions, the summary ini
writer and the key config writer. Dossier 06-save-layout.md, doctrine section 6.

Mechanics learned: a save is three artifacts. A JSON payload written through an async buffer; a small summary ini the
file select reads without decoding the payload; and a per-slot key config. Every save first writes the same state to a
reserved backup slot, then restores the chosen slot and writes that, so a primary write interrupted mid-flight still
leaves a consistent previous generation. Both the save and the load refuse to start while an operation id is live or
a load is in progress, and the buffer is created grow sized from the encoded JSON rather than a guessed capacity.

Our implementation differs by: keeping the three way split and the backup-before-primary ordering, but writing the
summary as JSON because we already have a JSON reader, gating on idle being negative because a valid async id can be
zero, verifying the written payload length before the summary claims the slot, saving input bindings globally once
rather than per slot, and storing a start timestamp instead of incrementing a play time counter everywhere.

Copied expression: none.

## 7. text, dialogue and typewriter

Studied: the writer object's create, alarm and draw events, the text setup helper, the message advance helper, the
battle text entry point and the portrait pairing. Dossier 07-text-dialogue-typewriter.md, doctrine section 7.

Mechanics learned: one writer object renders every piece of text in the game, created with a parameter block and
advanced by an alarm whose period is the character rate, drawing from an array of pre-loaded message strings. The
advance routine has a five behaviour control grammar: a three character style escape, a one character skip, a halt
that waits for the player with an auto-advancing variant, a two character escape, and a caret plus digit that adds a
measured delay of 5, 10, 15, 20, 30, 40, 60, 90 or 150 frames. Typing sound is paced by its own alarm, not the
character alarm. The spoken marker is writer state, not part of the string, and the portrait is a sibling object
positioned relative to the text.

Our implementation differs by: using our own brace codes with our own pause values rather than the studied
punctuation family, reading the spoken marker and portrait from data rows rather than writer defaults, and keeping
our reveal logic in a module so it can be tested without a room. Our line width is computed from our own font
metrics, not a hard-coded character count. None of their prose exists anywhere in our project.

Copied expression: none.

## 8. menu systems

Studied: the recursive menu drawing helper, the item appender, the selection decoration, and the battle command menu
for contrast. Dossier 08-menu-systems.md, doctrine section 8.

Mechanics learned: the general menu is a flat list read in triples of type, nested list and display name, rendered by
recursion over an array of selection indices indexed by depth, so cursor position at every nesting level is one small
integer and the renderer is a pure function of that array. The deepest depth reached is recorded into globals so a
caller can draw a detail pane. The battle menu, by contrast, is hand-coded branches with a per-submenu per-character
cursor array, which is why its clamping logic is repeated three times.

Our implementation differs by: using the data shaped approach for every menu including battle, rows as validated
structs rather than a flat tripled list so a row naming a missing action fails a unit test, and our own selection
decoration at our own palette. Recorded gap: the title menu is currently inline in pp_title, and extracting a shared
renderer is the first task of whichever card adds the second menu.

Copied expression: none.

## 9. audio routing

Studied: the music play and loop helpers, the volume and pitch helpers, the audio group loader, the group gain on
load, the sound name map and the stream teardown object. Dossier 09-audio-routing.md, doctrine section 9.

Mechanics learned: sound effects resolve by name through a global map, so a call site never names an asset id. Music
is played at a high fixed priority so effects cannot steal it, with a loop flag distinguishing a loop from a one
shot, and the volume is multiplied by the saved user setting at that single entry point rather than at each call.
A fade length in frames is converted to milliseconds in one place by multiplying by a thousand and dividing by the
room speed. Audio groups load through an idempotent loader. A tiny object exists only to hold a stream handle and
destroy it on its own destroy event.

Our implementation differs by: resolving cues through a generated manifest so an unknown name is a check failure
rather than silence, keeping the frame to millisecond conversion inside one function, using no audio groups yet with
a no-op loader so adding them later touches one place, and storing music volume in our own save key rather than a
shared flag index.

Copied expression: none.

## 10. cutscene and scripted sequences

Studied: several scene objects and their create and step events, the dialogue object's existence as a wait signal,
and the story progress global. Dossier 10-cutscene-and-scripted-sequences.md, doctrine section 10.

Mechanics learned: there is no scene engine. A scene is an object whose step event is a chain of independent counter
comparisons, which lets a branch jump forward by assigning a later counter value, with fractional values used for
part frame states. Waiting for dialogue is done by polling that the dialogue object no longer exists, so the running
thing is its own wait condition. A scene branches on one story number at the top of its create event, which selects
one of several variants of the scene.

Our implementation differs by: replacing the authoring model entirely. A scene is a validated command list in JSON
interpreted by one runner with a cursor and a wait value, which makes the story editable, diffable and testable
without a room. We keep three ideas as commands: staging actors by name rather than pre-placement, branching on one
named progress value, and a first class wait-for-dialogue command instead of chained frame counts. No scene is ever
an object.

Copied expression: none.

## 11. data-driven content pipeline

Studied: per-language JSON files, the language lookup helper, the JSON map loader, the sound name map, the monster
setup table and the encounter setup switch. Dossier 11-data-driven-content-pipeline.md, doctrine section 11.

Mechanics learned: text is genuinely data, held in flat per-language maps keyed by a name generated from the source
location, resolved through one helper, with control codes living inside the translated string. Map data can be loaded
from JSON through a four line helper that loads a buffer, reads it, deletes the buffer and decodes. Everything else
that makes a fight what it is, including the enemy table and the encounter table, is a branch per type in code, and
there is no schema validation anywhere, so a mistyped key resolves to nothing and a missing file returns nothing
silently.

Our implementation differs by: making the enemy and encounter tables data as well, choosing meaningful key names
rather than generated ones, validating every file against a schema and resolving every reference at check time so
broken content stops the build, and treating a missing or malformed file as an error rather than a silence.

Copied expression: none.

## 12. project organisation

Studied: the project file's resource list, the folder per resource convention, a representative script, object and
room folder. Dossier 12-project-organisation.md, doctrine section 12.

Mechanics learned: the project file is a flat list of resources with a name, a path and an order, so the editor tree
is derived from paths and the whole list can be generated and verified. Each resource is its own directory holding
its definition plus one file per event, so every resource is text and every event is a separate file. The
decompilation does not preserve localisation strings, build settings or comments, so a dossier written from one can
describe a mechanism but never a rationale.

Our implementation differs by: generating the resource list and the event stubs while never overwriting a
hand-written event body, checking the list against disk in both directions so an orphan folder or a dangling entry
both fail, and adding the layer the studied project has no analogue for: specs, schemas, checks, tests and this
provenance record. Our naming is our own and is reviewed by the clean room check.

Copied expression: none.

## 13. screen ownership: one room and one object per screen

Studied: no new decompilation was read for this entry. It applies the room and event flow of section 5 and the project
organisation of section 12 to the one screen that had two possible owners. The source of truth is this repository:
`game\scripts\pp_app\pp_app.gml`, `game\scripts\pp_title\pp_title.gml` and `game\objects\obj_pp_title\`.

Mechanics learned: a screen drawn by a persistent frame controller can move its content into its own room without
splitting ownership, but only if the mode machine stops running the same screen once the room exists. Two owners on one
screen do not fail loudly: they advance one state twice per step, so the scroll runs at double speed and a looping
track is started twice. The guard that fixes it is a single instance check in the mode's enter, step and draw, placed
where the room's object is the only thing that can satisfy it.

Our implementation differs by: giving the hand over its own door (`pp_app_enter_room`) rather than letting the mode
machine set the mode directly, keeping the boot card in the boot room for a data failure, and proving the frame with a
capture the game writes from inside its own draw event instead of a screen copy of whatever window is on top.

Copied expression: none.


## NES-PALETTES, 2026-10-22: scene palettes for the title and the ship
Studied: published NES hardware behaviour (Ricoh 2C02 PPU palettes and attribute tables: four background
palettes of three plus a shared backdrop, four sprite palettes of three plus transparency, one attribute entry per
16x16 area) and the manager's 2026-10-21 research note on how NES artists worked inside it (transparent as an
apparent colour, stacked sprites for a fourth colour, tiled variation, flicker to hide the 8 per scanline limit).
Those sources are documented technique and public hardware facts, not art.
Mechanics learned: the budget is a property of the composed frame, not of each layer, so the palette must be decided
before the art and enforced at the moment each asset is written.
Our implementation differs by: making the scene palette a data file per scene (data/palettes/scene_title.json,
scene_ship.json) with a solver that picks the four triples from the art, an enforcement pass that runs inside the
generators (title_car_v2, title_logo_v2, make_characters, make_title_world, make_title_ui, make_env_ship) so a
regeneration cannot undo it, and a checker that re-measures the pixels without trusting the solver.
Copied expression: none. No sprite, tile, palette swatch, font, sound or code text from any published game is in
this change; the drawing code, the solver and the checker are ours, written from the hardware rules above.

## 2026-10-22, card ASSEMBLE: a playable tile room on a 16 pixel grid

Studied: the project's own specs 03 (camera and integer scale), 04 (tile map, collision grid, triggers, spawn
points) and 14 (title drive), the GameMaker manual pages for screen_save, sprite_add and draw_sprite_part_ext, and the
FOX-STYLE dossier "rooms and doors" for the one owner per room pattern already in the codebase.
Mechanics learned: a room is three separate data pieces (tile art per cell, a collision byte grid, a list of triggers)
and the camera is a clamp over the map's pixel size; a room of 256x240 can show a map larger than itself and the frame
is scaled by an integer, never a fraction.
Our implementation differs by: the map loads from data\maps\ship_sample.json with a character legend and a separate
collision row per tile row; the tileset cell is chosen by a small explicit table (wall 8, floor 2, door 13, crate 21,
pipe 18, grate 3) read from the index's column count; the figures are frame math over a single row sheet with the
frames per direction measured at runtime; and the proof of the room is the room's own screen_save frame written from
inside its draw, not a copy of the desktop.
Copied expression: none. No sprite, tile, font, sound or code text from any published game is in this change.

## TEXT-REVEAL-1, 2026-10-22: one reveal machine, two layouts
Studied: this repository's own two typewriter modules (pp_dialogue and pp_battle_text) and FOX-STYLE.md section 7, which
already fixed the shape in prose: one writer per message, advanced by a per character tick, with the punctuation pauses
owned by the writer and not by the caller. No decompiled text was read for this card and none is needed, because section
7 exists so the answer does not have to be looked up again.
Mechanics learned: a character reveal is four things and nothing more. An item list built once from the source text, a
step counter that turns frames into revealed characters, a hold value that punctuation and control codes add to, and a
predicate that says the current unit is finished. Everything else a text box does, wrapping, pagination, a portrait, the
place the lines sit, is a layout and belongs to the layout.
Our implementation differs by: keeping the item list, the hold, the speed, the skip and the done predicate in one module
(pp_text) and leaving pp_dialogue and pp_battle_text with their geometry only; naming the pause values PP_TEXT_PAUSE_STOP
and PP_TEXT_PAUSE_COMMA in pp_config exactly as spec 05 rule 2 gives them; carrying the reveal in a plain struct with no
closures; and expressing the one behavioural difference between the two layouts, that the battle board advances by itself
at the end of a line while the dialogue box waits for confirm, as a single boolean on the machine instead of as a second
revealer.
Copied expression: none

## LEDGER-2, 2026-10-22: each enemy's exit, and a generous fight verdict
Studied: this repository's own doctrine and specs only. `knowledge\FOX-STYLE.md` section 2 already fixed the shape in
prose: one row per enemy carrying one of three exit states, rolled up into a fight verdict that flatters the player
while the rows stay exact, and no experience field anywhere. Spec 10 as refreshed on this date and spec 11 carry the
rest. No decompiled material was read for this card.
Mechanics learned: a morality record needs two resolutions, not one. The counters answer "how many", which is what the
prison branch and the final room read, and the rows answer "which one, and when", which is what any summary, any per
enemy line and any later scene needs. The verdict is a third thing and the cheapest of the three, because it is a
function of the rows: quiet when nothing was put down, violent when everything was, mixed in between. Writing the rows
and the counters in the same call, in that order, is what stops the two from ever disagreeing.
Our implementation differs by: keeping the four counters and the derived route exactly as they were, so the story
reading does not change; adding `exits` and `verdict` to the ledger struct and clearing them at the start of a fight
rather than at the end, so the record survives to be looked at; naming the states `PPExit.down`, `PPExit.spared`,
`PPExit.turned` and the verdicts `PPFightVerdict.quiet`, `mixed`, `violent`, which are the doctrine's own words; making
the door `pp_ledger_record_exit` the only place a counter is written, replacing `pp_ledger_record_result`, which took
no enemy and no round; storing only the rows in the save under an optional `fight_exits` key and recomputing the
verdict on load, so a save written before this card still loads with an empty record; and refusing to count a turned
enemy, which keeps the counters the coarse instrument spec 10 says they are.
Copied expression: none. No code text, sprite, font, sound or line of prose from any published game is in this change.

## NES-AUDIT TITLE, 2026-10-22: measuring a still frame with no sprite mask
Studied: this repository's own measuring tools and notes (`tools/nes_check.py`, `tools/nes_composite_check.py`,
`tools/art/scene_palette.py`, `knowledge/NES-AUDIT.md`), plus the published 2C02 PPU facts the notes rest on: one
backdrop colour shared by both layers, four background palettes of three entries selected per 16x16 area, four
sprite palettes of three entries plus transparency selected per 8x16 sprite, and an alpha channel that has an on
and an off and nothing between them. No decompiled material was read for this card, so there is nothing here that
could have come from one.
Mechanics learned: a photograph of a frame cannot say which pixel belongs to which sprite. The background area rule
counts colours in a 16x16 box, so a captured title screen charges the car's white against the sky's three blues and
reports a fault that is in the measuring, not in the art. The honest split is the one this project already makes in
`tools/check_scene_palettes.py`: judge the composed background frame against the four background palettes, and judge
each sprite sheet per 8x16 group against the four sprite palettes, and never let one check speak for the other. The
second thing learned: a background asset's backdrop is a fact that belongs in the asset's own file. Guessing it as
the most common colour makes the verdict depend on how much of the picture happens to be sky.
Our implementation differs by: reading `backdrop` out of each asset's JSON sidecar and printing where it came from
(`backdrop_from`) instead of choosing a colour from the pixels; recording the captured viewport beside each window
capture (`title_run_1.json`) and cropping to that box rather than searching the picture a second time; composing the
3x preview after the palette pass and declaring its backdrop in its own sidecar; and keeping the star, the wheel, the
bust, the fade strips and the cast in whole 8x8 tiles with solid alpha, which is a rule about what a pattern table
can hold rather than about how the art looks.
Copied expression: none. No code text, sprite, font, sound or line of prose from any published game is in this change.

## CLEANROOM-FIX, 2026-10-22: shipped data cites this repository, never a study dump
Studied: this repository only. `knowledge/mechanics/JRPG-MECHANICS.md` section 12, `specs/07-battle-director.md`, the
attribution header inside the Overpass downloads under `data/osm_cache/` (their own `generator` and `osm3s.copyright`
fields), and the published Overpass API response shape that header belongs to. No decompiled or ripped material was
read, opened or reasoned from for this card, and the study artifact the old citations named was not opened either: a
citation can be deleted without knowing what it said.
Mechanics learned: a citation chain has a direction. Shipped data may point at our own documents, and our own documents
may point at a public page; the reverse, a shipped table naming a downloaded study dump, puts material we do not
control into the build bundle. The second lesson is about a scanner: a directory based allowlist is a hole, because the
next hand written file parked in that directory inherits the exemption, so an exemption has to be earned by evidence
inside the file itself, and the run has to report how many files took it.
Our implementation differs by: keeping the numbers and rewriting only the provenance, so every `source_ids` entry now
resolves to a file under `knowledge/` or `specs/`; deleting the three recipes that had no internal source rather than
inventing one; and replacing the path-prefix skip with a four-part test (folder, parses as JSON, `generator` starts
with `Overpass API`, `osm3s.copyright` contains `openstreetmap.org`) that `tests/test_cleanroom.py` breaks on purpose
one marker at a time.
Copied expression: none. No code text, sprite, font, sound or line of prose from any published game is in this change.

## TEXT-REVEAL-2, 2026-10-22: the title crawl is a layout over the one reveal machine
Studied: this repository's own three text modules (pp_text, pp_dialogue, pp_battle_text), the crawl inside pp_title and
its data (data\intro_text.json, data\title_timing.json), and FOX-STYLE.md section 7 and law 8. No decompiled material was
read for this card, and no expression from any game is in it.
Mechanics learned: two things a page model has that a flat item list does not. The first is a beat: a group of rows the
author means to be read as one thought, with a pause after it and no pause between its rows. The second is the
difference between a punctuation pause and a beat pause. A punctuation pause sits inside a row, after a character that
is already on screen, and is a property of the sentence. A beat pause sits between rows, before any character of the
next thought appears, and is a property of the page. The machine already owns a hold at the end of a unit, so a beat is
a unit and the beat pause is that hold; nothing new is needed.
Our implementation differs by: making one beat one unit of pp_text and never one row, so the beat pause is the machine's
existing gap and no second timing mechanism was added; passing the title's own three numbers (steps per character from
60 / chars_per_second, the gap from pause_after_beat_seconds, the blip interval from blip_every_chars) through a
`pp_text_reveal_timing` setter, so pp_title names no PP_TEXT_ constant and the audit can say so by file name; adding the
skip as `pp_text_reveal_finish` on the machine rather than walking the item list in the title; carrying the fractional
per character remainder instead of resetting it, which is identical at the box's whole number speeds and correct at the
crawl's 60 / 18; and drawing the rows by spending the machine's revealed count over the current beat's row lengths, so
pp_title keeps no counter, timer, pause or blip of its own. The pacing delta this causes is written down in the spec 14
addendum of this date: plus 17 steps over 1238, +0.28 s, from honouring punctuation and carrying the remainder.
Copied expression: none

## SFX-WIRE, 2026-10-22: the first room is the deck, and a hatch is a way between maps
Studied: this repository's own map data (data\maps\all.json, data\maps\ship_sample.json), the trigger and walk code in
pp_overworld and pp_map, specs 04 and 12, ROADMAP-2026-10-22 S5 and S6, and the review comment on card t_efdf181b. No
decompiled material was read for this card, and no expression from any game is in it.
Mechanics learned: two things about how a room's exits work. The first is that a door between two rooms is a tile the
walker can stand on plus a trigger on that tile, and the tile art only decides what it looks like, never whether it
works, because the ship sheet draws both a door and a hatch with the same open hatch tile. The second is that a trigger
fires on confirm, not on arrival, while the hatch sound fires on the step that lands on the tile, so one tile can
honestly give both the walker's cue and the door's cue without a second mechanism.
Our implementation differs by: naming kinds rather than art, so the deck's legend carries a "hatch" kind that pp_map
gives the door colour and the ship sheet's tile 13, with no new sheet entry; pairing the two ship rooms with one hatch
each, the deck's at (2,13) down to the lower deck and the lower deck's at (3,11) back up, both `map` triggers, so a new
game begins on the deck that data\slice.json and data\project.json already named; and making the code follow the data
rather than the other way round by changing one constant, PP_NEW_GAME_MAP, and leaving the lower deck's save, sailors
and flag trigger in place as the room the hatch leads to.
Copied expression: none

## NAME-KONRAD-ZANDER, 2026-10-22: the two car figures take the cast names
Studied: this repository's own sources, all of them read-only for naming: knowledge\NAMES-BIBLE.md section 2 (which judged
Ronan Harrow and Theo Skye and marked both not adopted), knowledge\CHARACTER-BIBLE.md (the four Skyes, their ages and their
costume, including the explicit light blue and not green for Zander's bomber), specs\14-title-screen-drive.md, the two bust
generators tools\art\make_title_car.py and tools\art\compose_title_preview.py, data\sprite_redraw_queue.json, and the
concept art round 5 notes and prompts in Shared\projects\arananet\compute-2026-10-20\kaggle-concept-art\out_r5. No
decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: that a stale name survives in more places than the label, and each one keeps working while being wrong.
The interesting one is the art pipeline: tools\art\scene_palette.py enforces the per tile three colour rule against a
literal list of sprite names, so a rename that skips that list leaves the two busts silently unenforced while every test
that only checks the folder still passes. Also that a bust's pose can carry a character role independent of its costume:
frames 5 to 7 raise a wrist and check a watch, which is Konrad's tell in the bible, so the role was decidable from the
pixels rather than from memory.
Our implementation differs by: retiring both names rather than reinstating them, and folding the two sprites into Konrad
(driver) and Zander (passenger) instead of drawing new art, because the geometry, the pose and the tells are the project's
own and only the names and the costumes were wrong; then carrying the rename through every place that holds a literal
sprite name, the .yyp Included Files, the mirror index, the redraw queue ids, the palette enforcement list and the spec, and
writing the adopted costume into each queue entry as a design_note so the redraw cannot inherit the rejected farmer.
Copied expression: none

## TALK-PHASE-NAME, 2026-10-22: what a phase crossing names when it changes the talk card
Studied: this repository's own sources, read only: specs\16-talk-command.md section 10 and sections 1, 3 and 8, specs\18-boss-phases.md
sections 4 and C18-2, data\schemas\enemies.schema.json, data\schemas\talk_cards.schema.json, data\talk_cards.json, data\dialogue\all.json,
data\enemies\all.json, tools\check_data.py's enemy walk, and tests\test_schemas.py's talk card cases. No decompiled material was read for
this card and no expression from any game is in it.
Mechanics learned: that a data model can disagree with itself without failing, when the same string is legal in two namespaces. "percy_phase2"
is a talk card's phase and "talk_percy_phase2" is a dialogue row, and because both are plain strings in the same JSON, nothing rejected the
sentence that said one was matched against the other. The useful shape: when a crossing has to swap two different runtime things (the card the
model judges against, and the choice lines the player picks from), the row that triggers the crossing carries one field per thing, each named for
the namespace it resolves in, and a checker proves both directions, including the reachability one (a phase card that no row names is dead data
that every other check happily passes).
Our implementation differs by: keeping talk_set as the dialogue id and adding a separate talk_phase for the card phase, rather than redefining
talk_set, because four sources already document talk_set as a dialogue id and only one spec sentence claimed otherwise; giving the card file
ownership of the phase spelling and the enemy file a checked copy; and putting the cross reference in tools\check_data.py itself instead of
waiting for the planned tools\check_talk.py, so the drift cannot land before that tool exists.
Copied expression: none

## GAME-ROADMAP-2, 2026-10-22: ruling four blockers and ordering thirty cards
Studied: this repository's own sources, read only: specs\04, 05, 06, 07, 10, 11, 16, 19, knowledge\mechanics\PACING-AND-CUTSCENES.md
sections 6.2, 6.3 and 9, knowledge\ARRIVAL-CONTENT.md, ROADMAP-2026-10-22.md, tools\check_data.py's SCENE_COMMANDS, dialogue
walk and flag walk, data\schemas\dialogue.schema.json, data\flags.json, data\room_palettes.json, data\slice.json, and the
blocked card t_c024f8bc's own report and probe scripts in its workspace. No decompiled material was read for this card and no
expression from any game is in it.
Mechanics learned: that a density figure without a kind attached is not a rule but a trap. One sentence said "one marker per 40
to 60 walkable tiles" and, applied to a 1701 tile hub, asked for a fight every 8 to 12 seconds; the sentence was true only of
random markers, and splitting the marker into story and wild is what made it checkable. The same shape recurs twice more: a
file format that is legal but not expressive (a flat nine line dialogue list against spec 05's pages and a choice) is fixed by
making the shorthand legal beside the real shape rather than by migrating everything, and a network feature in a demo is fixed
by moving the call to bake time so the run is replay. The useful general form: when a worker blocks on a contradiction, the
contradiction is usually a missing distinction, and the answer is a distinction plus a rule a test can read, never an
exemption.
Our implementation differs by: scoping the density pair to wild markers and adding a 45 second spacing rule rather than raising
the count; keeping `lines` legal forever as a one page shorthand instead of rewriting fourteen committed entries; putting the
choice in dialogue data and branching on the flag with the existing `branch` command rather than adding a `choice` scene
command to the runner; and baking model output into data/meta_bake.json with a request hash, a model name and a fallback rather
than letting the build hold a key.
Copied expression: none

## DIALOGUE-FONT-WIRE, 2026-10-23: the box draws the sheet, and its line is 28
Studied: this repository's own files, read only: knowledge\FONT-CONTRACT-AUDIT-2026-10-23.md (the two measured defects),
specs\05-dialogue.md, specs\13-8bit-look.md, game\scripts\pp_font\pp_font.gml, game\scripts\pp_dialogue\pp_dialogue.gml,
game\scripts\pp_config\pp_config.gml, game\scripts\pp_art\pp_art.gml (pp_window_draw and pp_art_draw),
game\sprites_src\title\spr_pp_font8.png and .json, spr_pp_window.png and .json, data\dialogue\all.json, data\palette.json
(ink and paper roles), data\nes_palette.json, tools\check_data.py, tools\check_font_coverage.py, data\schemas\dialogue.schema.json,
and the tests that pin those numbers. No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: two things. One, a text box's column count is not a taste, it is a division: box width less padding,
divided by the glyph cell, and every other place that names a column count is a copy of that division that will drift unless
one test recomputes it from the macros. Two, wrapping and page breaking are two different promises, and a data shape that
promises "the author already broke these lines" is only true if the line length the checker enforces equals the length the
box draws; when they differ, the runtime silently re-breaks the author's work and the checker keeps passing.
Our implementation differs by: routing the box through the existing pp_font_draw instead of adding a sprite font resource,
so the sheet stays a sprite the NES checker audits; drawing the sheet untinted (a multiply of its one ink lands on colours
no PPU outputs, card t_a1170172); sizing the text area from the box's own padding (x 16 to 240 = 28 characters) rather than
from a portrait column, and moving the portrait to a bust above the box because a 48 pixel column costs 7 of the 28; and
re-breaking four authored page lines rather than lowering the column count, because at 21 columns 40 of 46 authored page
lines double and every arrival page grows.
Copied expression: none

## BATTLE-FONT-WIRE, 2026-10-23: the other 34 text sites draw the sheet, in its one ink
Studied: this repository's own files, read only: knowledge\FONT-CONTRACT-AUDIT-2026-10-23.md (rules 1 to 6 and the two
measured defects), knowledge\GAMEDEV-DECISIONS-2026-10-23.md D10 (the box's 28 columns), specs\13-8bit-look.md,
specs\07-battle-director.md, specs\19-llm-talk.md (the reply block and the hint row), game\scripts\pp_font\pp_font.gml,
game\scripts\pp_config\pp_config.gml, pp_battle_director.gml, pp_battle_text.gml, pp_app.gml, pp_save.gml,
pp_dodge_arena.gml, pp_overworld.gml, pp_title.gml (pp_title_draw_disabled, the rule-through idiom reused here),
pp_commands and data\palette.json plus data\room_palettes.json (the roles behind the plates). No decompiled material was
read for this card and no expression from any game is in it.
Mechanics learned: three things. One, moving a UI onto a fixed cell font is an arithmetic exercise first and a drawing
exercise second: every draw_text_ext pixel width is a column count (width / 8), every centred label is a width
computation, and the two places that used the default font's own metrics (string_width, draw_set_halign) become dead
code that has to go or it silently keeps lying about the layout. Two, a one colour bitmap font removes a whole state
vocabulary: a disabled row, a selected row and a hint used three role colours before, and each needs a replacement that
is a shape or a position (a rule through the row, a rule under it, its own row) rather than a tint, because tinting a
white sheet is a multiply and the product is a colour the hardware cannot output. Three, a preview tool that mirrors the
draw path is worth more than a screenshot for this class of change: it can refuse numbers (a row past a panel edge, a
glyph the sheet lacks) where an image can only show them.
Our implementation differs by: putting the wrap in pp_font once (pp_font_cols, pp_font_wrap, pp_font_draw_wrapped,
pp_font_draw_wrapped_centre) instead of per screen; keeping the sheet at 74 glyphs and writing the HP line as OF rather
than adding a slash to the art; using pp_title_draw_disabled's existing rule-through idiom for refused rows instead of
inventing a second one; putting the damage number and the arena's clear line on a plate of the room's ink instead of
tinting them; and moving the game over sentence under the card rather than shrinking the card or shortening the
sentence, because the card's geometry is spec 13's and the sentence is what the player needs to read.
Copied expression: none

## R7-GPU-LANE, 2026-10-23: the GPU concept lane, measured against the painted baseline
Studied: this repository's own R7 lane, read only: tools/kaggle_r7.py, tools/quantize_concept.py, tools/palette_synergy.py,
tools/nes_check.py, tools/scene_palette_set.py, tests/test_kaggle_r7.py; plus public model cards for
stabilityai/stable-diffusion-xl-base-1.0, nerijs/pixel-art-xl, keras/sam3 and metaresearch/segment-anything-2.1, the
keras_hub SAM 3 preset source, and the Kaggle API client's own documentation strings. No decompiled material was read for
this card and no expression from any game is in it.
Mechanics learned: two. One, a generation lane and a measurement lane have to stay separate artifacts with separate
provenance, because a tool that both paints and grades cannot tell you whose work a good score belongs to; the fix is a
concept source field and a manifest with a sha256 per frame. Two, promptable segmentation fails on stylised low resolution
art for a measurable reason (confidence, recorded as a distribution) rather than a mysterious one, so the right move is to
keep the deterministic segmenter and report the scores instead of tuning thresholds until something appears.
Our implementation differs by: mounting the segmenter as a read only Kaggle model source and loading the preset by path,
because kagglehub refuses to attach a model from a non interactive session (measured on run 2); recording the EFFECTIVE
LoRA after the load attempt rather than the requested one, because the Kaggle image's torchao breaks diffusers' peft bridge
and a run that drops the LoRA must not claim it used it; reducing the frame with nearest neighbour so no colour enters the
concept the model did not draw; and parking the painted report as a baseline file that a later model run cannot overwrite.
Copied expression: none

## CREDITS-PROVENANCE, 2026-10-23: the credits data proves its own citations
Studied: this repository only, read only: data/credits.json, data/nes_palette.json (as the shape of an in-file citation
block), tools/sync_data.py, and the refusal logic in tests/test_no_network_in_build.py, which is the test this card
answers. The two upstream documents the credits carry were not opened again this run; the licence text already stored at
knowledge/licences/PressStart2P-OFL.txt (4413 bytes, sha256 705960c3...) is what the file quotes. No decompiled material was
read for this card and no expression from any game is in it.
Mechanics learned: one. A citation pin can only be satisfied by evidence that travels WITH the data it excuses, because a
file the game ships cannot be trusted on the strength of a commit message; so the exemption belongs in the shipped bytes as a
provenance block, is counted and printed on every run, and a plain table stays refused. The second thing learned is a
boundary: an address that a licence text itself names as its home, and an attribution address that ODbL obliges us to carry,
are credits rather than endpoints, and the honest way to say so is to name them inside the file instead of widening the
checker for everybody.
Our implementation differs by: keeping the exemption inside data/credits.json (a top level sources block naming the holder,
the stored copy, its sha256 and the status of each URL) rather than adding a per-file allowlist to the test, so the checker
and its own file are untouched; and by leaving every licence line, count and screen row byte for byte as it was, adding 27
lines and deleting none.
Copied expression: none

## DIALOGUE-CHOICE-PANEL, 2026-10-23: the labels take the rows' place, and the slice has no portrait
Studied: this repository's own files, read only: specs\05-dialogue.md, game\scripts\pp_dialogue\pp_dialogue.gml,
game\scripts\pp_config\pp_config.gml, game\scripts\pp_look\pp_look.gml (pp_role_colour), tools\preview_dialogue_box.py,
data\dialogue\all.json (the quay_gate_choice page and its three labels), data\schemas\dialogue.schema.json, and
knowledge\GAMEDEV-DECISIONS-2026-10-23.md D10. No decompiled material was read for this card and no expression from any
game is in it.
Mechanics learned: two things. One, a choice menu drawn inside a text box is a layout problem with an arithmetic answer:
the panel's rows and the prompt's rows are the same three rows, so either the prompt narrows, or the choice becomes a
separate surface, or the two take turns in the same space; and "take turns" is the only one of the three that costs no
authored dialogue and keeps three options visible. Two, an unrendered feature and a rendered one are both facts that need
the same treatment: a spec line for a frame that never draws is a claim with no evidence, so it goes with the code that
would have drawn it, and the number that justified it (48 pixels costs 6 of 28 characters) stays written down for the
card that adds it back.
Our implementation differs by: replacing the 96 pixel filled panel with the choice rows themselves (cursor in column 0 at
x 16, labels in column 1 at x 24, 27 columns to the text area's right edge), so nothing is ever painted over a glyph and
the rows are skipped rather than covered; by deleting the three portrait macros and saying "Portrait: none." in the spec
instead of leaving geometry for a bust no speaker carries; and by making the overlap a refused case in the composed
preview (a row cell sharing a pixel with a label cell or the cursor is exit 1, and a test feeds it the exact old panel
geometry and requires it to fail).
Copied expression: none

## SHEET-GLYPH-GAP, 2026-10-23: the 8x8 sheet grows a slash and the two brackets
Studied: this repository's own files, read only: tools\art\pressstart2p_font.py (the rasteriser and its GLYPHS
literal), tools\art\make_title_ui.py (glyph_frame, write_sprite, generate), tools\art\make_ui_nes.py (its copy of the
order), game\scripts\pp_font\pp_font.gml (pp_font_glyphs, pp_font_glyph_index and the skip-a-missing-index rule),
tools\check_font_coverage.py (read_gml_glyphs, read_declared_glyphs, read_sheet), tools\preview_battle_font.py,
game\scripts\pp_drive\pp_drive.gml (pp_drive_draw_caption), game\scripts\pp_data\pp_data.gml (the error strings and
pp_data_load's file names), and knowledge\GAMEDEV-DECISIONS-2026-10-23.md D11. No decompiled material was read for this
card and no expression from any game is in it.
Mechanics learned: two things. One, a bitmap font sheet is an address space, not a picture: pp_font_glyph_index finds a
character by string_pos in one ordered string, so a glyph's position IS its identity, and growing the set is only safe
in ASCII order, which is what keeps the 74 existing frame numbers valid when three arrive. Two, the answer to "the sheet
cannot say this" is a ruling on the set, not a workaround at each site: the same hole had already been worked around
once by spelling OF in the HP line, and the moment the set grew, both that site and the drive caption's bracket cells
healed together, along with the boot error's file paths that nobody had noticed.
Our implementation differs by: adding exactly the three characters a shipped string asks for, and refusing the ones that
merely could be added (the probe shows `; \ | < > @ # % & + = _ { } ~ $ ^` all rasterise cleanly at 8 px and are
unused, so they stay out until a string asks); by taking the glyph shapes from the licensed Press Start 2P rasteriser at
8 px rather than drawing them, so the diagonal and the bracket serifs are the font's own and match the other 74 frames;
and by making the count agree in four declarations plus the sheet's sidecar, with tools\check_font_coverage.py refusing
any run where one of them disagrees.
Copied expression: none

## DIALOGUE-PORTRAIT, 2026-10-23: the bust stands on the box because a column would cost six characters
Studied: this repository's own files, read only: specs\05-dialogue.md, knowledge\ART-BIBLE.md (the sprite rules and the
tile budget), data\nes_palette.json (the entries the three sheets are drawn from), game\scripts\pp_dialogue\pp_dialogue.gml
(pp_dialogue_pages, pp_dialogue_push_page, pp_dialogue_open and pp_dialogue_draw), game\scripts\pp_config\pp_config.gml,
game\scripts\pp_art\pp_art.gml (pp_art_info and the one sheet index), tools\preview_dialogue_box.py,
tools\art\make_characters_v2.py (the house way a sprite sheet and its sidecar are written), tools\sync_art.py,
tools\gen_project.py, data\dialogue\all.json, data\schemas\dialogue.schema.json and knowledge\GAMEDEV-DECISIONS-2026-10-23.md
D12 and D14. No decompiled material was read for this card, no expression from any game is in it, and the three faces
are invented from the characters' written descriptions rather than traced from anything.
Mechanics learned: three things. One, a portrait in a fixed-width text box is a budget question before it is an art
question: 48 pixels is 6 of 28 characters, and the only placements that cost no character are above the box or outside
it, so the box's own top edge becomes the bust's floor and the arithmetic is `y + size == box top`. Two, an attached
face wants to be the same thing as the name plate, because both answer "who is talking", and the only page shape that
proves it is a narrator entry whose second page is another speaker, which is why the bust is resolved per page exactly
the way the speaker already was and why the plate has to move when the bust takes its corner. Three, a framed panel
beats a cut-out at this size: with four entries and a three-colours-a-tile budget, a solid panel in one entry plus ink
line art plus one accent reads as a portrait, while the same face on transparency reads as a hole in the scene.
Our implementation differs by: placing the bust above the box on the text area's own left margin (x 16, y 120, 48x48,
last row 167 against the box top 168) rather than in a column beside the words; by carrying the bust on the page as an
optional `portrait` name with `""` meaning none, and refusing a bust on the narrator; by moving the existing 64 wide
plate to x 68 when a bust is up instead of growing the plate or stacking the two; by authoring the three sheets in this
repository's generator (tools\art\make_dialogue_busts.py, role names resolved against data\nes_palette.json at render
time) in the NES framed-panel idiom; and by extending the composed preview into a refused case for a bust that starts
inside the text area, breaks the box's top edge, or touches the plate.
Copied expression: none

## BATTLE-FIGURE-RULER, 2026-10-24: a sheet says whether it is a figure or a layer (card t_c498add9)
Studied: this repository's own files, read only: knowledge/PALETTE-RULINGS-2026-10-24.md sections 7 and 8 (the
ruling this card implements), knowledge/ART-BIBLE.md RULE 0 point 2 (the amendment it carries), tools/palette_synergy.py
(the layer branch and the 16 px size test), tools/art/contrast_check.py (geometry(), the one frame-split reader),
tools/nes_check.py (the 3 colours per 8x8 tile rule, reused not rewritten), data/sprite_redraw_queue.json and the
sprite sidecars beside the PNGs in game/sprites_src/, and the two NES sprite-budget facts already written down in
ART-BIBLE section 1 (a sprite palette is 3 entries plus transparency, and one scanline spends one palette per 8x8
tile). No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: two. One, a size proxy is a rule with a hole in it: the 16 px line was standing in for "one
object", and every 24x32 and 32x32 battle figure in the project fell on the wrong side of it, so the strongest rule
(palette-count) never ran on the only sheets it was written for, and a PASS on a scene that could not draw the enemy
looked like health. Two, a multi-tile figure is judged the way the hardware is built: a 3-entry palette is a budget
per 8x8 tile, not per figure, so "does one palette carry this figure" has to become "does every tile have a palette",
with the per-frame reading kept for a frame small enough to be one object.
Our implementation differs by: making the declaration the rule rather than widening the proxy, with `"layer": true`
in the sheet's own sidecar and a 32x32 fallback for a sheet that declares nothing; by reading the declared frame size
through contrast_check.geometry() so a 168x32 sheet is seven 24x32 frames instead of one guess; by reporting one
palette_count FAIL per uncovered 8x8 tile with the tile's position and its colour set; and by keeping the whole-frame
reading, and the frame-level 3 colour restatement, for frames of 16x16 and under only, so no measurement already on
record moves.
Copied expression: none

## DECK-FIGURE-BODY, 2026-10-24: the row gap and the contrast floor are two instruments for R1 (card t_50193088)
Studied: this repository's own files, read only: the four battle frames in output/ (bg_battle_deck_night,
bg_battle_corridor, bg_battle_quay_dusk, bg_battle_wardroom), tools/palette_synergy.py (R1 body_ground, R1b
overlay_contrast, tile_fails), tools/art/contrast_check.py (the WCAG ratio and the 2C02 luminance table),
knowledge/ART-BIBLE.md RULE 0 point 2 with both amendments it carries, and knowledge/PALETTE-RULINGS-2026-10-24.md
(the deck ruling this card follows). No decompiled material was read for this card and no expression from any game is
in it.
Mechanics learned: two. One, the four NES luminance rows are a coarse quantisation of brightness rather than a
brightness itself: $10 sits one row from $0F at 11.06:1 and two rows from $30 at 1.85:1, so a rule written on rows
alone can refuse the most readable pair the console draws and accept a pair that is nearly one tone. Two, on all four
battle strips every pixel a 24x32 figure stands on is the backdrop ($0F, 768 of 768 in the placement box), so a
frame-level body-versus-ground test on a battle figure silently becomes "is the main colour white".
Our implementation differs by: keeping the row gap as one instrument and adding the WCAG 3:1 large-text floor the
project already uses for R1b as the other, refusing a pair only when both are short, so 17 of the gate's 19
body_ground fails stay refused and only 2 clear; by refusing the three alternatives the card offered with
measurements instead (only the 16 palest entries clear the old rule, so a night deck would go pale; asking the rule
per 8x8 tile turns 1 fail into 43; repainting the grey to white uncovers a tile needing $00 $0F $30 together); and by
keeping the ink-against-ground merge and the enemy's $02 on $0F at 1.73:1 out of scope and named rather than fixed
by widening a palette.
Copied expression: none

## TALK-CAPTURE, 2026-10-24: the talk path is proved by the game's own lines, not by a picture of a menu (card t_27aa179e)
Studied: this repository's own files, read only: `game/scripts/pp_battle_director/pp_battle_director.gml` (the command
list, `pp_battle_begin_action`, `pp_battle_enter_result`), `game/scripts/pp_battle_text/pp_battle_text.gml` (the bake,
the panel, the reply board, the option labels), `game/scripts/pp_font/pp_font.gml` with
`game/datafiles/art/spr_pp_font8.png`, `game/scripts/pp_overworld/pp_overworld.gml` (the trigger, the confirm target,
the entry autosave), `tools/capture_first_fight.py` (the palette reader, the ink measures, the victory panel),
`data/encounters/all.json`, `data/enemies/all.json`, `data/dialogue/all.json`, and the frames the run itself wrote.
No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, a GMS2.3+ script function is itself a global variable, so a cache guarded by
`variable_global_exists("<the function's own name>")` is true before its first call and returns the function instead
of what it was supposed to build: reading a member off that value ends the game. Two, `pp_font_draw` paints the 8x8
sheet with `PP_UNTINTED`, so a glyph is the sheet's colour (248,248,248 in the PNG, 232,231,236 after the capture's
compression) and NOT any palette role, which is why every ink-role reading of the command list measured zero pixels
on every frame of this run. Three, the deck's battle trigger is a confirm trigger and not a walk-on one, so a driver
that only walks presses past the first fight.
Our implementation differs by: putting the six provable facts in the six functions that own them instead of in the
driver; driving the whole run off the log the game writes (deck autosave, list line, panel line, pick line, result
line) with holds long enough for a one-second frame sample to land on the list and the panel; reading the glyph colour
and the text row bands off the shipped sheet and the frames rather than placing them from a draw call's pitch, after
one draw call's pitch and another's frames disagreed by four pixels; and by naming the two engine bugs the run found
(the bake cache answering with its own function, and two unguarded member reads that could end a fight) rather than
working around them in the tool.
Copied expression: none

## DRIVE-MAP, 2026-10-24: the drive corridor's map row and palette set (card t_e8a8f18a)
Studied: this repository's own files, read only: `assets/tiles/drive/TILES.md` and `drive_tiles.json` (the sheet's
character column, its four background palettes and the palette.json role behind every sheet role),
`data/tile_classes_drive.json` (the walkable classification), `data/palette.json` (the master roles and indices),
`data/room_palettes.json` (the append only sets), `data/maps/all.json`, `data/scenes/all.json`,
`game/scripts/pp_map/pp_map.gml` and `game/scripts/pp_map_tile/pp_map_tile.gml` (how a row is loaded, which set a
room palette resolves to, and the three draw planes), `game/scripts/pp_scene/pp_scene.gml` (a camera command is a
tile coordinate times `PP_TILE`), `game/scripts/pp_config/pp_config.gml` (`PP_FRAME_W`, `PP_FRAME_H`,
`PP_CAMERA_MOVE_STEPS`, `PP_FADE_STEPS`), `tools/check_data.py` (the row rules), `tools/sync_art.py` (which folders
reach the build index), `tests/test_quay_tiles_wire.py` (the shape a wire test takes), `knowledge/DRIVE-SHOT-LIST.md`
and `specs/14-title-screen-drive.md`. No decompiled material was read for this card and no expression from any game
is in it.
Mechanics learned: three. One, a map row's geometry is derivable from the cutscene that plays over it rather than
authored beside it: the furthest camera tile in the scene's own commands plus the frame width is the width floor,
and the camera's own y plus the frame height is the height floor, so a row can be checked against the film instead of
against taste. Two, the same room palette id chooses the tile table at draw time (`pp_map_tile_set_for_room`), which
means a new room palette is also a new art set and the row can be legal while the art it names is not yet wired. And
three, a palette set can be derived from an art sheet's own manifest: every group lists sheet roles, every sheet role
names a palette.json role, so the set is the union of those names plus the four drawing roles, and no one has to pick
colours.
Our implementation differs by: computing the collision grid from the tile class file rather than typing it, so a
reclassification moves it; opening the safety barrier in four named places so the near verge is walkable from the
road and the map is one region rather than two; generating the row from a tool that refuses a tree which has drifted
(`--check`) instead of pasting it once; and declaring the whole sheet colourable in the set even though this row
places no gantry tile, because the sign belongs to the corridor and not to this pass.
Copied expression: none

## DRIVE-TILE-WIRE, 2026-10-24: the drive sheet is wired to its map row (card t_af836a62)
Studied: this repository's own files, read only: `assets/tiles/drive/drive_tiles.json` (the character column, the
index of every tile, the four palette groups and the palette.json role behind each sheet role) and its `TILES.md`
(where the sheet lives, and the 16px grid rule), `data/room_palettes.json` (the `drive_night` set and its thirteen
roles), `data/palette.json` (the master roles), `data/maps/all.json` (the `drive_m4_corridor` row and its legend),
`game/scripts/pp_map_tile/pp_map_tile.gml` (the existing ship, quay and office tables, the plane constants and the
four answer functions this card extends), `game/scripts/pp_map/pp_map.gml` (how a room palette becomes a set and how
a set becomes a sheet and a column count at draw time), `tools/sync_art.py` and `tools/check_build_inputs.py` (the
mirror folders and the two directions the commit gate checks), and `tests/test_quay_tiles_wire.py` (the shape a wire
test takes). No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, a set name is not a set until the table builder branches on it: adding a room palette
id and a rows function is not enough, because the builder answers every unknown set with another set's rows, so a
half wired set draws the wrong planes and the wrong palette groups while looking correct in the data. Two, a
character is not a tile: the drive sheet reuses `w`, which the quay spends on water, so a per-set branch written as
"everything except the ship" silently animates the wrong art once a third sheet reuses the letter; naming the set the
animation belongs to is the fix, and the rule generalises to every character-keyed behaviour. Three, delivery is part
of the wire and has two gates, not one: the mirror has to read the folder the art card chose (`sync_art.py`), and the
commit checker has to know that folder as a source (`check_build_inputs.py`), or the sheet ships in the build index
while a fresh checkout cannot rebuild it.
Our implementation differs by: reading every character, index, palette group and plane from the sheet's own manifest
in the test rather than restating 24 numbers, so a redraw that reorders the sheet is caught instead of pinned; keeping
the sheet in the art card's own `assets/tiles/drive` folder and teaching the mirror to read it rather than moving
another lane's art to fit an existing source list; asserting the empty above plane explicitly, because "the corridor
has no fitting drawn over the walker" is a decision that a later tile could violate without any test noticing; and
pinning the drive's `w` to `barrier_post` so the quay's water branch cannot reach it.
Copied expression: none

## TITLE-FADE-DRIFT, 2026-10-25: derived art is lifted last, and the checker reads it (card t_cd6a0d24)
Studied: this repository's own files, read only: `tools/pp_intro_art.py` (the fade rule, the forbidden `$0D` entry, the
star's own palette-enforcement fix, and a `--check` that documented staleness it never measured),
`tools/art/scene_palette.py` (`apply_title`'s pass order: two area passes, the checker flatten, the sprite list, the
`rebuild_flash` call, then `title_bands.apply`; `enforce_sprites` and its 8x16 grouping; `TITLE_SPRITES` and which
names the band plan takes over), `data/palettes/scene_title.json` (`band_sprites`, the four sprite palettes, the note
that the fade twins are not band painted), `tools/art/make_title_world.py:rebuild_flash` (the same derived-strip
argument, already solved for the `_flash` twins), `tools/check_scene_palettes.py` (every `TITLE_SPRITES` sheet is
judged for three colours per 8x16 group and one sprite palette per group), and `tests/conftest.py` plus `pytest.ini`
(the `host_png_bytes` and `needs_git_checkout` classes, which is why the new pins compare pixels and read HEAD). No
decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: two. One, a derived strip is a build-order fact and not a file: any pass that can rewrite a base
strip invalidates every picture named after it, so the only durable arrangement is that the last pass rebuilds the
derived strips from the base as it is on disk, which is what this repo had already accepted for the `_flash` twins and
had never extended to the fades. Two, two tools writing one file with two different rules cannot be detected by a
checker that asks whether the file exists: the cloud's fade twin was being written raw by one tool and re-mapped into
the sprite palette by the other, so the shipped bytes were neither one rule nor the other, and only a pixel-level
comparison against the base names which rule lost.
Our implementation differs by: computing the fade twin inside the generator for exactly the sheets the scene's sprite
pass owns, read from the scene data rather than from a copy of the list, so the two writers now compose to the same
answer in either order; rebuilding the fades at the end of `apply_title` next to the flash rebuild instead of asking
lanes to remember a command; making `--check` report the pixel count that differs per strip, which is the number that
tells a lane whether the base moved or the rule moved; and judging the new pin from the HEAD pair so a lane's
uncommitted repaint can never make another lane's suite red, while the working copy is still judged by the command a
lane actually runs.
Copied expression: none

## SPRITE-GROUND-TRUTH, 2026-10-25: a sky element is judged as a layer, and a ground must be measurable (card t_1dc346b9)
Studied: this repository's own files, read only: `tools/palette_synergy.py` (R1b `layer_rules`, the figure/layer declaration
path cf3d43a introduced, and the audit `at` field the gate reads), `knowledge/PALETTE-RULINGS-2026-10-24.md` sections 7 and
11, `data/palettes/scene_title.json` and `scene_ship.json` (the band plan, the sprite palettes, the judged rows),
`data/sprite_redraw_queue.json` (the two rows' own remeasured blocks), `output/cloud_sky_ground.png` and the title strips it
is cropped from, `game/sprites_src/env/ts_ship.png`, and `tools/pp_intro_art.py` (the fade sidecar chain that copies the base
declaration). No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: two. One, a palette rule with an OR in it (R1b: ink OR body clears the floor on every ground colour)
exists precisely so a bright element can share material with the scenery behind it; reading such an element as a figure,
where the same-hue and white-blob tests have no OR, turns scenery-on-scenery into a failure the drawing cannot answer. Two,
a ground for a cast must be an artefact authored inside the scene's own palettes; a composed capture carries colours off the
console palette and the checker charges them to the sprite standing on it, so a capture cannot be evidence about a sprite.
Our implementation differs by: the cloud's layer declaration lives in its sidecar and is re-written by the generator that
owns the sheet, not hand-edited once; the sailor's judged row in `scene_ship.json` names the tileset with a fixed `at` the
gate can run, not a capture; and both rulings are recorded inside the queue rows beside the old measurements rather than
overwriting them, so the history of what each PASS meant on its day survives the ruling.
Copied expression: none

## EXHAUST-LAYER, 2026-10-25: an effect with no single ground is a layer, and the band plan decides its body (card t_474cde50)
Studied: this repository's own files, read only: `knowledge/ART-BIBLE.md` RULE 0 point 2 and its two amendments,
`knowledge/PALETTE-RULINGS-2026-10-24.md` section 7 (the declaration rule) and section 11 Q2 (the car's repaint to `$20`),
`tools/palette_synergy.py` (`is_sprite_frame`, `layer_rules`, `frame_report`), `tools/art/contrast_check.py` (`geometry`,
`sidecar_entry`, the 2C02 luminance and WCAG contrast the numbers come from), `tools/art/title_bands.py` (`sprite_palettes`,
`map_image`, `paint_sheet`), `tools/art/scene_palette.py` (`apply_title`'s pass order and its fade rebuild),
`tools/pp_intro_art.py` (`fade_sidecar` copying the base declaration), `tools/art/compose_title_preview.py` and
`game/scripts/pp_title/pp_title.gml` (the draw order on both sides), `output/title_world_manifest.json` and the seven title
layer strips (the swept ground), and `data/palettes/scene_title.json` (bands and `band_sprites`). No decompiled material was
read for this card and no expression from any game is in it.
Mechanics learned: two. One, a contrast instrument that asks about "the ground" is answering a question about one surface;
an effect drawn over a scrolling strip is measured against every ground colour of that strip at once, and when those colours
span the brightness rows the instrument has an empty answer window, so the honest reading is the layer one where EITHER the
ink or the body may carry the edge. Two, the painting passes that make a composite frame legal (the band plan) are upstream of
any redraw: a body colour the band does not hold is not a design choice, it is a pixel the pass will rewrite, so the generator
has to draw the colour the tree can keep.
Our implementation differs by: the qualification test is written down as a measurement (sweep the scene's own layer table and
read the window) rather than as an argument about size or subject; the declaration is written by the generator that owns the
sheet, so a regeneration cannot drop it; the four frames are drawn once and shared between the redraw tool and the owning
generator instead of being copied; and the row keeps the old figure measurement beside the new layer one, so what changed and
why is legible later.
Copied expression: none

## BATTLE-CAST-BUDGET, 2026-10-25: a scene's sprite palettes are four, and the party is drawn in one triple each (card t_8c27208b)
Studied: this repository's own files, read only: `knowledge/ART-BIBLE.md` section 1.1 (what a scanline of sprites can
be), section 1.2 (the 4 + 4 palette arithmetic, 12 opaque sprite colours per frame), section 2.3 (Final Fantasy I's
side view with the party down the right edge) and section 2.4 (Castlevania's one palette for Simon and the rest shared
by enemies, and why Simon reads: no black in his palette), `data/scene_palettes.json` `hero_palettes`,
`data/palettes/scene_battle_corridor.json`, `data/ui_layouts.json` (the party block at x 224 and the two 32x32 enemy
slots), `tools/palette_synergy.py` (the per tile R6 reading and the two messages that name a fifth sprite palette),
`tools/scene_palette_set.py` (`allowed()` unioning the scene four with the hero four), `tools/nes_audit_all.py`
(`discover()` and what it treats as a frame, a sheet and a captured frame), `pine_offload.py` in the arananet tree
(`OUTPUT_KEEP` and the comment that argues for it), `knowledge/PALETTE-PASS-LIST.md` run 10 sections 2, 7 and 9, and
`knowledge/SUBMISSION-KIT-2026-10-24.md` section 1.1. No decompiled material was read for this card and no expression
from any game is in it.
Mechanics learned: three. One, a multi tile NES figure is not one palette's worth of pixels, so a scene's sprite
budget has to be checked per 8x8 tile, and the question "does one palette carry this figure" is the wrong question for
anything taller than one tile. Two, the four sprite palettes a frame has are a CEILING, so a cast of four figures plus
an enemy cannot each own a palette; the studied games solve it by drawing the monster as background art and giving the
player figure the palette with no black in it. Three, an upload manifest that ships "what a test reads" is right, and
the measurement defect is on the other side: a checker that prints a smaller universe without saying so is not
advisory, it is quieter.
Our implementation differs by: the budget is written per scene in `data/scene_palettes.json` with the four hero triples
fixed by number rather than chosen at draw time; the measurement is an exact set cover over every tile's opaque colour
set, so the price of a repaint is a number of triples and a percentage of pixels rather than an opinion; the body role
and the floor are decided by two instruments the tool already owns (row gap or 3:1) instead of by a rule of thumb; and
the audit treats a by product that no clean checkout can reproduce as NOT MEASURED rather than as a hard refusal.
Copied expression: none

## PALETTE-ARITHMETIC-AND-AUDIT-SCOPE, 2026-10-25: four sprite palettes, a by-product that cannot refuse a run, and an audit that prints the universe it measured (card t_c93a983f)
Studied: this repository's own tools and its own ruling, read only: `knowledge/PALETTE-RULINGS-2026-10-25.md`
sections 7.1, 8 and 9 (the four sprite palettes the PPU has, the eight the data model spent, the by-product row and
the far side's shrunken universe), `knowledge/ART-BIBLE.md` section 1.2 and RULE 0 point 1 (the 4 + 4 arithmetic),
`tools/palette_synergy.py` (`frame_report()`, `tile_fails()`, `gate()`, `write_audit()`), `tools/scene_palette_set.py`
(`scene_entries()`, `build()`, `judged_rows()`, `audit_rows()`), `tools/nes_audit_all.py` (`discover()` and the
verdict it prints), `pine_offload.py` in the arananet tree (`OUTPUT_KEEP` and the comment that argues for it, read
only, not edited), and `tests/` for the rows that measure all four. No decompiled material was read for this card and
no expression from any game is in it.
Mechanics learned: four. One, a palette budget the hardware does not have cannot be described as a missing resource:
a message that names a remedy no frame can hold turns a settled ruling into an open question, which is what the
party battle cast read as for a week. Two, a set of palettes and a set of COLOURS are different objects, so a checker
that unions palettes and then tests membership in the union approves art that no single palette carries; the union
has to be replaced at the palette level, not filtered afterwards. Three, evidence has a provenance: a file two
generators write differently and git ignores is not evidence about either, so the honest report is NOT MEASURED with
a named path rather than a refusal that costs whole runs. Four, a universe built from what is on disk is a claim
about the tree, not about the project, so a run has to print its scope as numbers or a narrowed tree reads as a
passing one.
Our implementation differs by: the party cast is a per scene property emitted into the derived set
(`party_cast`, true for the four battle strips) rather than a global change, so the eight other scenes keep the
behaviour they had; the declaration lives in the tool because the strip generator writes the four scene files whole
and drops what it does not itself write (measured 2026-10-25 06:17); the by-product is a flag on the audit row and the
gate reports it NOT MEASURED or advisory, never gated, whatever it measures; and the audit scope is counted from two
independent sources, the output PNGs on disk that its name excludes and the output PNGs this repository's data names
but the tree does not hold, so the absent half is a number and a list rather than silence.
Copied expression: none

## TITLE-PREVIEW-DRIFT, 2026-10-25: a preview that is judged must read its placement from the thing it previews (card t_2a34652e)
Studied: this repository's own files, read only: `tools/art/compose_title_preview.py` (the composer's own constants,
the manifest reader, the compose order), `game/scripts/pp_title/pp_title.gml` (`PP_TITLE_CAR_X/Y`, `PP_TITLE_CONE_X/Y`,
`PP_TITLE_SIGN_X/Y`, `PP_TITLE_LOGO_X/Y`, `pp_title_defaults`, `pp_title_read_data`, `pp_title_data`,
`pp_title_draw_car`, `pp_title_draw_sign`, `pp_title_draw_cone`, `pp_title_draw_logo`), `data/title.json` and its
`game/datafiles/title.json` mirror (`cmp`: identical), `output/title_world_manifest.json`,
`tests/test_title_bands.py` (the cross-read style and its pinned `(76, 193)`), `tools/art/title_car_v2.py` (the baked
wheels), `tools/art/title_cloud_ground.py` (the reader of `CLOUD_DY` from the composer's source), and
`knowledge/PALETTE-RULINGS-2026-10-25.md` sections 3 and 6. No decompiled material was read for this card and no
expression from any game is in it.
Mechanics learned: two. One, a hand-copied constant in a preview tool is a drift with a delay built in: CAR_Y 186
against the game's 193 stayed invisible because the preview and the screen are read by different eyes and nothing
compared them; the fix that holds is the one that removes the second copy (read the value from the file that draws
the screen, refuse to run without it) rather than the one that corrects the number. Two, the drift was worse than
the card named: the composer's manifest carried the pre-I32 layer table (downs 92, road 196) while the game reads
96 and 192 from data/title.json, so "the world can never drift apart" was true only against the world generator
that wrote the manifest, not against the screen the manifest's own numbers had already been corrected away from.
Our implementation differs by: the composer now takes its placements from the game's macros and its layer table
from the game's data file, in the same order `pp_title_data` layers them, with no silent fallback for the macro
numbers at all; the pastes match `pp_title_draw_car` (exhaust, body, nothing else over the car), while the arch
and window pixel readers stay in the file as a reported sprite check instead of a paste position; and
`tests/test_title_preview_placements.py` pins all three drift surfaces (car and cone and sign and logo equal the
.gml, no module-level CAR_Y exists, the table equals data/title.json, the fallback equals pp_title_defaults, no
wheel/bust/bubble is pasted by either side), so the halves cannot disagree quietly again.
Copied expression: none

## BATTLE-CAST-ROWS, 2026-10-25: a battle strip's four sprite palettes are spent on the four figures the screen draws (card t_0949bd4e)
Studied: this repository's own files, read only: `data/ui_layouts.json` (the one battle screen layout and its four
24x32 party slots at x=224 plus the two 32x32 enemy slots), `data/palettes/scene_battle_corridor.json` and
`data/palettes/scene_battle_deck_night.json` (the two judged rows), `tools/scene_palette_set.py` (`scene_payload`,
`scene`, `allowed_sprite_sets`, `scene_entries`, `cast_problems`, `JUDGED_KEY`), `tools/palette_synergy.py`
(`analyse`, `frame_report`, `tile_fails`, `pair_rules`, `cast_problems`, `gate`), `tools/art/make_battle_bg.py`
(`scene_palette_json` and the whole file write that drops the `judged` key), the four battle frames in `output/`,
the party, sailor and enemy sheets in `game/sprites_src/`, and `knowledge/PALETTE-RULINGS-2026-10-24.md` sections 4,
5 and 11 plus `knowledge/PALETTE-RULINGS-2026-10-25.md` sections 7 and 9. No decompiled material was read for this
card and no expression from any game is in it.
Mechanics learned: two, both about the NES rather than about this project. One, a sprite palette is selected per
8x8 tile from four palettes, so a screen that draws four full size party figures has spent the entire sprite budget
before an enemy is drawn at all: the standard answer, and the one this project's own art bible records for Final
Fantasy and Castlevania, is that the monster becomes background art, because background palettes are selected per
16x16 attribute area and are a separate budget. Two, background art is not free either: one palette carries a whole
16x16 area, so an enemy redrawn as background still needs a background triple that carries its three colours, and
on the deck today none of the four does (27 of navy_sailor's 37 inked tiles fit none). That is why the recast is a
cast decision with a measured price rather than a relabel.
Our implementation differs by: the battle screen's cast is declared as data, one `judged` row per scene, and the
four reserved hero triples are substituted for a `party_cast` scene's own four sprite rows by
`allowed_sprite_sets()` rather than a scene being allowed to carry eight palettes; the row that measures a strip
lives in the scene file that solved it, so a cast and the thing that checks it cannot drift into two files; the
enemy route is recorded as a card with its own measurement instead of being quietly dropped when the party took the
fourth slot; and a row that cannot be measured honestly (this one, until the tool reads the hero four) carries an
exemption that names the card that ends it, so the red state is a dated decision and not a silenced check.
Copied expression: none

## DECK-ENEMY-TRIPLE, 2026-10-25: the deck's plate triple spends the enemy's white, because that is where the enemy stands (card t_34b1d96a)
Studied: this repository's own files, read only: `data/ui_layouts.json` (screen `battle`, its `enemies` slots and
its `party` slots), `data/encounters/all.json` (`tutorial_sailors`, `deck_hound`, `percy`), `data/palettes/
scene_battle_deck_night.json` and `scene_ship.json` with their judged rows, `tools/art/make_battle_bg.py`
(`build_scene`, `scene_palette_json`, the `deck_night` scene, the cell painters), `tools/scene_palette_set.py`,
`tools/palette_synergy.py`, `tools/art/contrast_check.py`, the four battle strips and their frames, the sheets in
`game/sprites_src/enemies/` and `game/sprites_src/chars/`, and `knowledge/PALETTE-RULINGS-2026-10-25.md` sections 7
and 12. No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, a background-art enemy is not drawn from a palette set, it is drawn from the ONE
palette of the 16x16 area it stands in, so a fit measured over the union of a strip's triples cannot say whether the
enemy can be drawn: the placement has to be resolved to its attribute cells first, and on this strip the answer was
a single triple for both slots. Two, the shared backdrop is an entry every area may spend, so the palette an enemy
needs is two entries and not three, which is what turned a 12288 pixel palette replacement into a 2016 pixel one
entry swap. Three, a cost measured in strip pixels and a cost measured in sheet pixels are not comparable until the
figure is the subject: 2016 pixels of rivets leave the player's subject alone, while 37.5 percent of the enemy's
own pixels rewrites the thing the fight is about.
Our implementation differs by: the decision lives in the strip generator's own scene table, so the numbers keep one
owner and a later run cannot drift from them; the spend is the minimum that reaches the enemy's cells (one entry of
`bg2`, keeping the plate body `$00` and the seam `$02`), not the enemy's triple in full and not the rigging triple
the card first proposed; and the enemy's sheet is left untouched, because the ruling that sent it to the background
also ruled that it keeps its own three colours.
Copied expression: none

## PARTY-WALK-GROUNDS, 2026-10-25: a walking sheet is judged on the room it walks in, and a scene's free sprite row is where a homeless triple goes (card t_dec4e92c)
Studied: this repository's own files, read only: `data/palettes/scene_southampton.json`,
`scene_westminster.json`, `scene_winchester.json` and `scene_ship.json` (the judged row format and the one worked
example of a tileset ground), `data/scene_palettes.json` (the derived set, the hero four, `party_cast`),
`tools/art/make_exterior_maps.py` (`render_frame`, `enforce_palette_budget`, `write_scene_palette` and the whole
file write that drops `judged`), `tools/art/make_characters_v2.py` (how the four walking sheets chose their three
entries, and the note on zander that named this card's answer in advance), `tools/palette_synergy.py` (`Grid`,
`background_report`, `frame_report`, `tile_fails`, `pair_rules`, `cast_problems`, `gate`),
`tools/scene_palette_set.py` (`judged_rows`, `audit_rows`, `allowed_sprite_sets`, `cast_problems`),
`game/sprites_src/env/ts_exterior.json` (the five background groups), `data/maps/*.json` (the spawn tiles), the
four walking sheets and the three map frames. No decompiled material was read for this card and no expression from
any game is in it.
Mechanics learned: three. One, a tileset atlas is not automatically a usable ground: an atlas that covers five
background groups cannot be drawn inside any one scene's four, so measuring a sprite on it charges the atlas's own
areas to the sprite, which is the same failure mode as measuring on a screen capture and has the same cure, namely
to measure on the composed frame the generator builds under the four group budget. Two, the four sprite palettes
are a property of the frame, and a scene file's placeholder rows are a copy of the background groups, so a sheet can
be "in the set" entry by entry and still be carried by no single palette: hadrian's `$00 $0F $30` raises
`palette_count` and no `set_member` at all, and a check that counted only the latter would have passed him. Three,
a walking sheet and a battle sheet are drawn on different grounds, so the same character legitimately spends two
different triples, and the way to give a walking triple a home is to spend a free sprite row on the ground the
character walks, not to repaint the sheet to match the fight palette.
Our implementation differs by: the ground is named as a file a generator writes and a row measures, with the file
committed and held in a fixture list rather than a capture; each scene's cast lives in its own `judged` list at the
spawn tile the map actually starts on; the two placeholder rows are solved for the two homeless walk triples rather
than a repaint being ordered, because the rows carried no art at all (measured over every sheet in the tree); and
the generator that owns those files now carries a `judged` list and a solved sprite half forward instead of
rewriting the file whole, so the decision cannot be deleted by a rerun.
Copied expression: none

## DECK-ENEMY-TRIPLE, 2026-10-25: the deck's plate triple spends the enemy's white, because that is where the enemy stands (card t_34b1d96a)
Studied: this repository's own files, read only: `data/ui_layouts.json` (screen `battle`, its `enemies` slots and
its `party` slots), `data/encounters/all.json` (`tutorial_sailors`, `deck_hound`, `percy`), `data/palettes/
scene_battle_deck_night.json` and `scene_ship.json` with their judged rows, `tools/art/make_battle_bg.py`
(`build_scene`, `scene_palette_json`, the `deck_night` scene, the cell painters), `tools/scene_palette_set.py`,
`tools/palette_synergy.py`, `tools/art/contrast_check.py`, the four battle strips and their frames, the sheets in
`game/sprites_src/enemies/` and `game/sprites_src/chars/`, and `knowledge/PALETTE-RULINGS-2026-10-25.md` sections 7
and 12. No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, a background-art enemy is not drawn from a palette set, it is drawn from the ONE
palette of the 16x16 area it stands in, so a fit measured over the union of a strip's triples cannot say whether the
enemy can be drawn: the placement has to be resolved to its attribute cells first, and on this strip the answer was
a single triple for both slots. Two, the shared backdrop is an entry every area may spend, so the palette an enemy
needs is two entries and not three, which is what turned a 12288 pixel palette replacement into a 2016 pixel one
entry swap. Three, a cost measured in strip pixels and a cost measured in sheet pixels are not comparable until the
figure is the subject: 2016 pixels of rivets leave the player's subject alone, while 37.5 percent of the enemy's
own pixels rewrites the thing the fight is about.
Our implementation differs by: the decision lives in the strip generator's own scene table, so the numbers keep one
owner and a later run cannot drift from them; the spend is the minimum that reaches the enemy's cells (one entry of
`bg2`, keeping the plate body `$00` and the seam `$02`), not the enemy's triple in full and not the rigging triple
the card first proposed; and the enemy's sheet is left untouched, because the ruling that sent it to the background
also ruled that it keeps its own three colours.
Copied expression: none

## DECK-ENEMY-TRIPLE, 2026-10-25: the deck's plate triple spends the enemy's white, because that is where the enemy stands (card t_34b1d96a)
Studied: this repository's own files, read only: `data/ui_layouts.json` (screen `battle`, its `enemies` slots and
its `party` slots), `data/encounters/all.json` (`tutorial_sailors`, `deck_hound`, `percy`), `data/palettes/
scene_battle_deck_night.json` and `scene_ship.json` with their judged rows, `tools/art/make_battle_bg.py`
(`build_scene`, `scene_palette_json`, the `deck_night` scene, the cell painters), `tools/scene_palette_set.py`,
`tools/palette_synergy.py`, `tools/art/contrast_check.py`, the four battle strips and their frames, the sheets in
`game/sprites_src/enemies/` and `game/sprites_src/chars/`, and `knowledge/PALETTE-RULINGS-2026-10-25.md` sections 7
and 12. No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, a background-art enemy is not drawn from a palette set, it is drawn from the ONE
palette of the 16x16 area it stands in, so a fit measured over the union of a strip's triples cannot say whether the
enemy can be drawn: the placement has to be resolved to its attribute cells first, and on this strip the answer was
a single triple for both slots. Two, the shared backdrop is an entry every area may spend, so the palette an enemy
needs is two entries and not three, which is what turned a 12288 pixel palette replacement into a 2016 pixel one
entry swap. Three, a cost measured in strip pixels and a cost measured in sheet pixels are not comparable until the
figure is the subject: 2016 pixels of rivets leave the player's subject alone, while 37.5 percent of the enemy's
own pixels rewrites the thing the fight is about.
Our implementation differs by: the decision lives in the strip generator's own scene table, so the numbers keep one
owner and a later run cannot drift from them; the spend is the minimum that reaches the enemy's cells (one entry of
`bg2`, keeping the plate body `$00` and the seam `$02`), not the enemy's triple in full and not the rigging triple
the card first proposed; and the enemy's sheet is left untouched, because the ruling that sent it to the background
also ruled that it keeps its own three colours.
Copied expression: none

## SHIP-WALKING-CAST, 2026-10-25: the ship's four sprite palettes are the party's four walking triples, and the sailor rides one of them (card t_a6a7a436)
Studied: this repository's own files, read only: `data/palettes/scene_ship.json` and the three town scene files,
`data/scene_palettes.json`, `data/maps/all.json`, `data/maps/ship_sample.json`, `data/encounters/all.json`,
`data/enemies/roster.json`, `data/nes_palette.json`, `tools/art/scene_palette.py` (`solve_ship`, `write_scene`,
`enforce_sprites`), `tools/scene_palette_set.py` (`validate`, `cast_problems`), `tools/palette_synergy.py`
(`analyse`, `frame_report`, `tile_fails`, `gate`), `tools/check_scene_palettes.py` (`check_ship`),
`tools/art/make_characters.py` (the ship enforce pass), `game/scripts/pp_overworld/pp_overworld.gml` (both drawing
macros and `pp_overworld_draw_hero`), `game/scripts/pp_data/pp_data.gml` (how the ship map is loaded), the four
party walking sheets, the sailor's two sheets and `game/sprites_src/env/ts_ship.png`. No decompiled material was
read for this card and no expression from any game is in it.
Mechanics learned: two. One, the four sprite palettes are chosen per 8x8 tile at draw time, so two figures share a
row for free when their three entries are identical, and that equality is a measurement rather than a hope: the
walking sailor's `$02 $12 $30` IS Percy's triple, which is why a five-sheet walking cast fits four rows and why the
question "whose row does the sailor take" has the answer "nobody's". Two, a palette file that two owners write is a
file one of them silently deletes: this solver wrote the scene file whole and emitted no audit row, so the row a
previous card landed was one `solve --write` from gone, and the third instance of that defect (after the battle
strip generator and the exterior map generator) is what closed it for good rather than per scene.
Our implementation differs by: the ship's rows are declared a cast decision in the file itself (`sprites_pinned`)
instead of being defended in prose, and `write_scene()` reads that flag before it solves, so the guard travels with
the data rather than with a card; the audit row is carried forward unconditionally, so no future generator can drop
it by forgetting the key; and the walking cast is named in one place per tool (`SHIP_SPRITES` in the checker, the
enforce list in the character generator) so a sheet that stops being drawn leaves both lists instead of one.
Copied expression: none

## PARTY-CAST-READ, 2026-10-25: a party_cast strip is read against the four palettes it can actually draw (card t_6e8ca42f)
Studied: this repository's own files, read only: `tools/scene_palette_set.py` (`find_scene`, `scene_payload`,
`scene`, `allowed_sprite_sets`, `scene_entries`, `cast_problems` and the `party_cast` key), `tools/palette_synergy.py`
(`analyse`, the caller that mattered, plus `frame_report`, `tile_fails` and `gate`), `tools/art/scene_palette.py`
(the `Scene` class those callers hand the payload to, and what it does with `sprites`), `data/scene_palettes.json`
(`hero_palettes`, the four `party_cast` strips, and the six audit rows with their two exemptions),
`data/palettes/scene_battle_corridor.json`, `data/palettes/scene_battle_deck_night.json`, the four party battle
sheets in `game/sprites_src/chars/`, the two corridor and deck frames in `output/`, and
`knowledge/PALETTE-RULINGS-2026-10-25.md` sections 7.1 and 8. No decompiled material was read for this card and no
expression from any game is in it.
Mechanics learned: two, one about the hardware and one about the tool. One, the four sprite palettes are a hard
ceiling per screen and the palette is chosen per 8x8 tile at draw time, so what a screen can draw is a property of
the frame rather than of the declaration a scene file happens to hold: an audit that judges a sheet against a list
the frame never uploads is measuring a room that does not exist. Two, when the same arithmetic is reached through
more than one door (a checker reading an audit row, a quantiser reading a scene, a painter reading a palette set),
fixing the door that happens to be red leaves the others reading the wrong four, so the substitution belongs at the
one point all of them pass through, and the older accessor has to keep returning the same rows or a second list
quietly grows back.
Our implementation differs by: the substitution is a single function, `allowed_sprite_rows()`, and both shapes
readers ask for (rows with names, bare colour sets) are derived from it rather than maintained beside it;
`scene_payload()` takes the sprite half as an argument instead of deciding it, so the default stays the scene's own
rows and only the caller that knows about `party_cast` opts in; and a scene without the flag is left as it was,
which is how the ship, the title and the towns are shown untouched by the change.
Copied expression: none

## BATTLE-BG-OWNER, 2026-10-25: a generated file and its generator are one owner, and dead data still has to be declared somewhere (card t_8ebcb489)
Studied: this repository's own files, read only: `tools/art/make_battle_bg.py` (`SCENES`, `scene_palette_json`,
`read_existing_scene_palette`, `carry_judged`, `write_scene_palette`), `tools/scene_palette_set.py`
(`allowed_sprite_rows`, `allowed_sprite_sets`, `scene`, `scene_payload`, `scene_entries`, `scene_from_source`,
`validate`, `PARTY_CAST_SCENES`), `tools/palette_synergy.py` (the gate), `data/palettes/scene_battle_*.json` (all
four), `data/scene_palettes.json`, `data/nes_palette.json`, `data/ui_layouts.json`, the four strips and their
sidecars, the commits `157f11a`, `e53a160` and `0b5dd01`, and `knowledge/PALETTE-RULINGS-2026-10-24.md` plus
sections 11, 12, 15 and 17 of `knowledge/PALETTE-RULINGS-2026-10-25.md`. No decompiled material was read for this
card and no expression from any game is in it.
Mechanics learned: two. One, a file written whole by a generator has exactly one owner, and the disagreement can run
in either direction: the deck's palette file carried four rows the generator did not emit AND was missing a note the
generator did emit, so "the hand copy is stale" and "the generator is stale" were both true in one file, and only
regenerating and diffing tells you which lines belong to which direction. Two, data nobody spends is not data nobody
reads: a `party_cast` strip's own four sprite rows are substituted away for drawing and for cast measurement, and
they are still read by the scene validator (the 25 colour ceiling) and emitted into the derived set, so they are
declaration level and cannot be left to drift even though no frame uploads them.
Our implementation differs by: the generator's table follows the measurement rather than the other way around, and
the reason is written as a test (the deck's declared rows must not equal the corridor's, because that is what the
defect looked like); the notes policy is stated in the module docstring as a numbered rule with the reason `judged`
is carried and `notes` is not, so the next hand written block in one of these files has a documented home; and the
end to end property (regenerate every committed palette file, byte for byte) is a pin rather than a manual check, so
the next strip card cannot pass its acceptance while the generator and the files disagree.
Copied expression: none

## BATTLE-DRAW, 2026-10-25: the battle field's strip, enemy and party are drawn from the shipped sheets (card t_4275136f)
Studied: this repository's own files, read only: `game/scripts/pp_battle_director/pp_battle_director.gml` (the field
draw and its state), `game/scripts/pp_data/pp_data.gml` (the bundle loader), `game/scripts/pp_art/pp_art.gml` (the
index reader and `pp_art_draw`), `game/scripts/pp_font/pp_font.gml` (`pp_font_draw_centre`, `pp_font_width`),
`data/ui_layouts.json` (the battle slots and the four member names), `data/enemies/all.json` and
`data/enemies/roster.json`, `data/characters/party.json`, `data/palettes/scene_battle_deck_night.json`,
`data/scene_palettes.json`, `data/nes_palette.json`, `game/sprites_src/bg/bg_battle_*.json` and the four strips,
`game/sprites_src/enemies/*.json` and the seven enemy sheets, the four `game/sprites_src/chars/*_battle.json` sheets,
`tools/sync_art.py`, `tools/check_build_inputs.py`, `tools/palette_synergy.py`, `tools/scene_palette_set.py`,
`tools/capture_first_fight.py`, `tools/play_demo.py`, `tools/capture_title.py`, `tools/pp_launch.py`, and
`knowledge/PALETTE-RULINGS-2026-10-25.md` sections 7 and 15. No decompiled material was read for this card and no
expression from any game is in it.
Mechanics learned: two. One, a battle screen is three draw calls with three different colour owners: the strip is
background art and spends the ground's own rows, the enemy is background art too and is judged on `bg2` plus the
backdrop (36 inked 8x8 tiles, 0 out, ruling 15.3), and the party is four sprite sheets judged one reserved triple
each, so the same pixel coordinates on one screen are governed by three different rules and no single "the battle
background passes" claim covers all of them. Two, art that no tool mirrors is art no build has: `pp_battle_draw_field`
asked for the deck strip on every frame for months and `pp_art_has` answered no every time, because the mirror read
five source folders and `bg` was not one of them, and a sidecar with no `frame_w` was skipped as malformed, so the
defect was two lines apart in one file and neither line could see the other.
Our implementation differs by: the slots are read from `data/ui_layouts.json` at run time instead of being restated in
the GML, so the director cannot disagree with the design file and no hero name lives in code; the battle strip's
sidecar is accepted as a single frame background record instead of being forced into the animation shape it never had;
and the two placeholder rectangles the screen drew before there was art were removed rather than left under the real
draws, because a flat block beside an enemy sprite reads as a second enemy.
Copied expression: none

## SAILOR-BATTLE-RETIRED, 2026-10-25: a battle sheet for a slot the game does not have is retired from the budget, not given a ground (card t_0b9c2faf)
Studied: this repository's own files, read only: `tools/art/scene_palette.py`, `tools/check_scene_palettes.py`,
`tools/art/make_characters.py`, `tools/art/make_enemies.py`, `tools/sync_art.py`, `tools/palette_synergy.py`,
`tools/scene_palette_set.py`, `data/ui_layouts.json`, `data/encounters/all.json`, `data/enemies/roster.json`,
`data/characters/party.json`, `data/nes_palette.json`, `data/scene_palettes.json`, `data/palettes/scene_ship.json`,
`game/scripts/pp_battle_director/pp_battle_director.gml`, `game/scripts/pp_overworld/pp_overworld.gml`,
`game/PrimordialParadox.yyp`, the four hero battle sheets, the walking cast, `navy_sailor.png`, and their commit
history. No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: two. One, a slot's geometry is the first disqualifier and it is cheaper to read than the palette:
the battle screen's enemy slot is declared 32x32 in `data/ui_layouts.json` and reads `enemies/<id>.png` through the
art index, while the party column is four 24x32 slots named by member, so a 24x32 sheet that is not a hero has no
slot to be drawn in no matter what colour it carries. Two, "three colours per 8x8 tile" and "one palette per figure"
are different rules and only the second one decides a party slot: every party battle sheet is 3 entries per frame
because a slot draws ONE sprite palette, and a sheet whose worst TILE is legal can still need three palettes in a
single frame, which is what this one does (2 to 3 per frame, 10 across the sheet) and why the old PASS on a 16x16
tile rule never meant it could be drawn.
Our implementation differs by: the retired sheet is declared rather than deleted (`BATTLE_RETIRED` in the v1
character generator plus one list in each tool), so the game keeps its art and the pipeline stops producing it, and
the two `SHIP_SPRITES` constants that had drifted apart are one cast by test rather than by comment.
Copied expression: none


## SHIP-PALETTE-DRIFT, 2026-10-25: a palette file that a generator repaints INTO is an input, so a solver that writes it by default edits the art (card t_92d59163)
Studied: this repository's own files, read only: `tools/art/scene_palette.py` at HEAD and at `7a73469`,
`tools/art/make_env_ship.py`, `tests/test_make_env_ship.py`, `tools/scene_palette_set.py`,
`tools/check_scene_palettes.py`, `tools/palette_synergy.py`, `data/nes_palette.json`, `data/scene_palettes.json`,
`data/palettes/scene_ship.json` and its history, `game/sprites_src/env/ts_ship.png` and its sidecar and their
history, and the commit history of all of them. No decompiled material was read for this card and no expression
from any game is in it.
Mechanics learned: two. One, when a "reproduces the file on disk" row is red and the working tree holds an
uncommitted copy of a derived file, the uncommitted copy is not automatically the drift: run the generator in a
clean worktree at the candidate file and compare hashes. Here the result was byte identical, which proved the
working tree was a derivation, and it still did not settle the question, because the derivation was of the wrong
thing. Two, direction of dependency is what decides who wins: a palette row set that a generator READS is a
description, and a row set that a generator REPAINTS INTO is an input, and `enforce_ship_sheet()` makes the ship's
rows the second kind. Every check that compares the committed art against the rows passes either way, because it
is measuring the rows' own output; only building the art from each candidate set shows the difference (0 pixels
and a byte identical sheet for the committed rows, 151 pixels over 6 tiles and a lost `$2C` entry for the solver's
proposal). The same asymmetry is why `solve_title()` had needed `write=False` since 2026-10-22.
Our implementation differs by: the file is reverted rather than moved, and the recurring cause is closed in the
tool instead of in the data (a `write` flag on `solve_ship()` mirroring the title's, plus a report that prints the
PROPOSAL rather than the file, so the disagreement is visible without being applied). Nothing was redrawn, no
palette row moved, and the open question (should the ship's rows move, and at what cost to the ten colour budget)
is left to a card that owns the ship art, with the measurement attached.
Copied expression: none

## SAILOR-BATTLE-UNSHIPPED, 2026-10-25: a retirement is not landed until the sheet stops shipping, and the build is the only proof (card t_4848159e)
Studied: this repository's own files, read only: `tools/sync_art.py`, `tools/gen_project.py`,
`tools/integration_build.py`, `tools/run.ps1`, `tools/check_build_inputs.py`, `tools/check_test_inputs.py`,
`game/PrimordialParadox.yyp` and its generator, `game/datafiles/art/title_manifest.json` (generated), the four hero
battle sheets, `tests/test_sync_art.py`, `tests/test_scene_palettes.py`, `tests/test_palette_synergy.py`, the ruling
`knowledge/PALETTE-RULINGS-2026-10-25.md` section 19, and the installed toolchain under
`C:\ProgramData\GameMakerStudio2-LTS2026` and `C:\Program Files\GameMaker-LTS2026`. No decompiled material was read
for this card and no expression from any game is in it.
Mechanics learned: three. One, a build list is a mirror plus a generator, so deleting art is two steps and one
command: the mirror removes the stale PNG by comparing its wanted set against the folder, and a write run of the
mirror then regenerates the project from what it wrote, which is why the `.yyp` edit is one removed block and not a
hand edit. Two, an Igor Run mode build does not return until the game process exits, so a command line CI step that
reads "did it compile and launch" has to close the launched window itself; the window title is the project name and
the process is `Runner.exe`. Three, the compiled data file count in Igor's own stats line (`da=`) is a cheap before
and after for any change that adds or removes an Included File, and it reads 276 before and 275 after this deletion.
Our implementation differs by: the sheet is deleted rather than excluded, because an Included File exception would
keep a file in the tree that no slot can draw; the two tests that measured the deleted drawing now measure its
absence in the authored tree, the mirror, the art index and the project instead of pretending to measure art that is
gone.
Copied expression: none

## SHIP-ROWS-PINNED, 2026-10-25: a row set that is an input to the art is a ruling, so the file says which half a solve may not touch (card t_23b5739a)
Studied: this repository's own files, read only: `tools/art/scene_palette.py` at `7a73469` and at HEAD (the solver,
`write_scene()`, `solve_ship()`, `describe()`, `enforce_ship_sheet()`), `tools/art/make_env_ship.py` and its `PALETTE`,
`tools/art/make_ship_tiles.py`, `tests/test_make_env_ship.py`, `tests/test_scene_palettes.py`,
`tests/test_scene_palette_set.py`, `tests/test_make_ship_tiles.py`, `tools/scene_palette_set.py`,
`tools/check_scene_palettes.py`, `tools/check_env_tiles.py`, `data/nes_palette.json`,
`data/palettes/scene_ship.json`, `game/sprites_src/env/ts_ship.png` and `ts_ship_tiled.json`,
`data/maps/ship_sample_tiled.json`, `knowledge/SHIP-PALETTE-DRIFT-2026-10-25.md`, and the commit history of all of
them. No decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, when a generator repaints its own output into a data file, the data file is an input
and not a product, so "the solver is right and the file is stale" is the wrong reading even when every checker passes:
the honest measurement is the one against the RAW sheet, before the pass, which is why the two row sets read 762 and
625 repainted pixels of 12288 here and both read a perfect sheet after enforcement. Two, a palette row is not only a
coverage optimum, it is the set of colours a future drawing is allowed to use, so a row that wins on today's flat
fills can still be the wrong row: the solver's water row has no white in it, and the sheet's own table reserves `$30`
for foam, which the tool maps to `$28` gold under those rows. Three, "pin the half" is cheaper and more honest than
"remember not to run the generator": the pin is a key in the file the solver already reads, it is testable with a
control that removes the key, and refusing to rewrite a file whose parsed payload is unchanged keeps a pinned write
from leaving a layout only diff.
Our implementation differs by: the pin is generic in the writer (`background_pinned` handled beside
`sprites_pinned`) rather than a ship special case, the report still prints the proposal and adds the file's own rows
beside it, and the design move itself is deferred to a redraw card with both sides of the trade written down
(ruling section 21.3) instead of being taken here on 137 pixels of art that no map places.
Copied expression: none

## PARK-IN-THE-DARK-BAND, 2026-10-25: a walkable ground is chosen by the bodies that stand on it, and the last exemption closes in the tile (card t_b01c88ff)
Studied: this repository's own files, read only: `tools/palette_synergy.py`, `tools/check_ts_exterior.py`,
`tools/art/make_ts_exterior.py`, `tools/art/make_exterior_maps.py`, `tools/art/contrast_check.py`,
`tools/scene_palette_set.py`, `knowledge/ART-BIBLE.md` RULE 0 point 2, `knowledge/PALETTE-RULINGS-2026-10-25.md`
sections 16.6, 20 and 20.8, `data/nes_palette.json`, the three town scene files, `game/sprites_src/env/ts_exterior.json`,
the tileset and the four walking sheets. No decompiled material was read for this card and no expression from any game
is in it.
Mechanics learned: three. One, an exemption list is only as strong as the card name on each entry, and the entry has to
be closed in the art rather than in the tool: check 13 already printed "EXEMPT grass_a/b/c ... carded as t_b01c88ff", so
the work was to darken the tile and empty the list in one commit, because a list that keeps a fixed tile after the fix
is a check that quietly permits exactly what it exists to stop. Two, a two tone ground inside a fixed three entry row
needs its accent from outside that row: bg2_green's two legal entries are 1.24:1 apart, so the texture moved to the
shared backdrop (3.69:1 against the field, 2.98:1 against the shade) rather than to the shade, and the backdrop costs no
entry because every palette row already shares it. Three, a judged row can only be written where the composed crop can
see the ground: the town frame is a 16 by 15 tile crop around the spawn, so of the three towns only Westminster carries
park cells inside it (31 of them, 24 reachable from the spawn over 511 walkable cells), and a row written for the other
two would measure pavement and prove nothing.
Our implementation differs by: the park keeps bg2_green's three entries and loses its light accent instead of buying a
second walking triple for the party, which the four sprite palettes per scene do not have room for (sections 16.6 and
20.7); the accent that used to be light is now the backdrop, drawn in the shapes the old art already used, so the
variants stay distinguishable without a fourth colour; and the measurement lives in a new test file as well as in the
check, because nothing in this suite ran check 13 before this card.
Copied expression: none

## SHIP-DRAWN-IN-ITS-ROWS, 2026-10-25: a palette row is a budget of three slots, and the art has to be drawn inside it (card `t_463cb8c1`)
Studied: this repository's own files, read only: `tools/art/make_env_ship.py`, `tools/art/scene_palette.py`,
`tools/art/make_ship_tiles.py`, `tools/scene_palette_set.py`, `tools/check_env_tiles.py`,
`tools/check_scene_palettes.py`, `tests/test_make_env_ship.py`, `tests/test_scene_palettes.py`,
`tests/test_scene_palette_set.py`, `tests/test_make_ship_tiles.py`, `data/nes_palette.json`,
`data/palettes/scene_ship.json`, `data/scene_palettes.json`, `game/sprites_src/env/ts_ship.png` and
`ts_ship_tiled.json`, `data/maps/ship_sample_tiled.json`, `output/env_ship_preview.png`,
`knowledge/PALETTE-RULINGS-2026-10-25.md` sections 21 and 22, and `knowledge/SHIP-PALETTE-DRIFT-2026-10-25.md`. No
decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, a three entry palette row is a budget, and a family of tiles that all need the same
three colours has to be PAINTED with those three rather than measured into them: the sea was flat because its tiles
asked for a fourth tone the row could not carry, and no row ordering fixes that, only the drawing does. Two, the
measure a solver minimises has to be the drawing, not the enforced output, or the solver scores its proposal with the
very pass it is proposing to change (on the enforced PNG it "covered every tile", which is the rows agreeing with
themselves); the fix is to measure the generator's own render and to make a worse proposal refused rather than written,
which is a floor and not a pin, because a floor can be beaten and a pin cannot. Three, when a metric is minimised over
a whole sheet, the loss that both candidate answers share is invisible: the portholes lost 160 pixels under either row
set, the largest loss on the sheet, and it appeared in no per tile table because the per tile DIFFERENCE was zero. A
per tile table of differences hides a constant, so the absolute column has to be read too.
Our implementation differs by: the deck's four rows keep their meaning (steel and white paint, steel and brass,
rust and brass, the sea) and the art is redrawn into them instead of the rows being re-solved around the art, so no
tile's design changes for palette reasons alone; the sea's third tone is the crest `$21` rather than white `$30`
because `$21` has no other home on this sheet and `make_ship_tiles.py` draws its terminal with it, and the porthole
takes the steel row's pale glass instead of spending a row on its old steel and sea glass; and the guard is a measured
floor inside the solver that prints both numbers and refuses a worse write, with `background_pinned` still supported
for a half that genuinely is a ruling.
Copied expression: none

Correction on the same card, 2026-10-26: two pointers in this card's own prose were wrong. The card number was
written as `t_463bc8c1` (two letters transposed) in the shipped note of `data/palettes/scene_ship.json`, in five
docstrings of `tools/art/scene_palette.py` and in four in the two ship test files; it is `t_463cb8c1`. The same note
and three code comments cited "ruling section 21.7", which this card never wrote: the ruling is section 23, because
the card allowed an addendum 21.7 or a new section and a new section is what was written. Both classes of pointer are
now the real identifiers. The lesson is that a receipt has to name the thing the board answers to, and that choosing a
new section obliges every pointer to say 23. No row, pixel or number changed; the sheet was regenerated after the
edit and is byte identical, and
`pytest tests/test_make_env_ship.py tests/test_scene_palette_set.py tests/test_scene_palettes.py -q -> 59 passed`
re-ran green.

## PALETTE-REPORT-POSIX, 2026-10-26: a committed record may not carry a machine's path separator (card `t_8bb7bdea`)
Studied: this repository's own files, read only: `tools/nes_composite_check.py`, `tools/check_scene_palettes.py`,
`tests/test_scene_palettes.py`, `tests/test_nes_composite_check.py`, `output/scene_palettes.json`, and the separator
convention already in `tools/art/make_drive_tiles.py`, `tools/art/make_quay_tiles.py`, `tools/art/make_font_row_v2.py`,
`tools/art/make_dialogue_busts.py`, `tools/art/make_exterior_maps.py` and `tools/art/make_icons_nes.py`. No decompiled
material was read for this card and no expression from any game is in it.
Mechanics learned: two. One, a tool's stdout stops being ephemeral the moment a report embeds it, so every path that
stdout prints is a committed byte: `os.path.relpath` is a display decision that a Windows run and a Linux run answer
differently, and a gate that compares a committed report with a fresh run turns that difference into a permanent red row
with no measured number out of place. Two, the guard has to be asserted on the separate axis, not only through equality:
an equality check between two runs on the SAME platform reproduces the leak faithfully and stays green, so the report
itself has to be refused for carrying a separator at all, which is the only assertion that fires on the machine that
wrote it.
Our implementation differs by: the normalization sits at the printer (`shown_path()` in `tools/nes_composite_check.py`)
rather than at the embedder, so every consumer of this tool's stdout inherits the portable form, and it matches the
`.replace(os.sep, "/")` spelling the art lane already uses instead of introducing a second convention. The row stays
measured on Pine rather than being deselected there.
Copied expression: none

## TS-SHIP-AREA, 2026-10-26: a checker that guesses its input is measuring the guess, so an art sheet has to declare its own backdrop (card `t_4d5984b4`)
Studied: this repository's own files, read only: `tools/nes_audit_all.py` (`declared_backdrop()`, `block_offenders()`,
`measure()`), `tools/nes_check.py`, `tools/art/make_env_ship.py`, `tools/check_env_tiles.py`,
`game/sprites_src/env/ts_ship.json`, `game/sprites_src/env/ts_ship_tiled.json`,
`game/sprites_src/env/ts_exterior.json`, `data/scene_palettes.json`, `data/nes_palette.json`,
`tests/test_make_env_ship.py`, `tests/test_nes_audit_all.py`, and the audit's own measured output at HEAD `8220c95`. No
decompiled material was read for this card and no expression from any game is in it.
Mechanics learned: three. One, a rule that reads its own free parameter from the pixels cannot be trusted on a sheet
where two candidate values are close: the NES area rule charges every colour besides the backdrop, so a backdrop guessed
as the commonest colour makes the true backdrop a chargeable colour, and on this sheet the guess was decided by 203
pixels of margin (3553 grey against 3350 black). The rule was right and the measurement was wrong, which is the failure
mode that looks exactly like an art bug from the outside. Two, the fix belongs in the art's declaration and not in the
rule's tolerance, because relaxing the checker to accept four colours would let a genuinely over-budget area through
forever; declaring the input is what keeps the rule strict and the reading true. Three, the declaration has to be
generated from the same table the art is drawn from, or the next build resets it: the key now comes from the backdrop row
of the generator's own palette table, so the two cannot drift, and the proof that no pixel moved is that a rerun leaves
the sheet, the map and the preview byte identical and changes only the two sidecars.
Our implementation differs by: the declaration lives in the tileset sidecar that already exists beside every sheet in this
project, rather than in a new per-asset config, because `tools/nes_audit_all.py` already reads exactly that file and
already prefers it over the guess; and the class the card exposed is recorded rather than silenced, since 45 of the 54
measured background assets carry no declaration and pass today only because their commonest colour happens to be the
backdrop.
Copied expression: none

## FIRST-FIGHT-ROUTE, 2026-10-26: a route file only one harness followed is a route no player has (card `t_009836b9`)
Studied: this repository's own files, read only, no decompiled material and no expression from any game in it:
`data/slice.json`, `data/scenes/all.json` (`drive_to_southampton`, `quay_gate_checkpoint`, `ship_boarding`),
`data/maps/all.json` (`drive_m4_corridor`, `southampton_town_quay`, `ship_small`), `game/scripts/pp_app/pp_app.gml`
(the route reader and the `PP_SLICE` walk), `game/scripts/pp_scene/pp_scene.gml` (the runner's `take_scene`, `end` and
`branch`), `game/scripts/pp_overworld/pp_overworld.gml` (the one place a finished runner is dropped, and the encounter
door), `game/scripts/pp_title/pp_title.gml` (`pp_title_crawl_handoff`), `game/scripts/pp_input/pp_input.gml` (the
action table), `data/schemas/cutscenes.schema.json`, `tools/check_data.py`, `tools/art/make_drive_map.py`,
`tests/test_slice_route.py`, `tests/test_scene_runner.py`, `tests/test_drive_map.py`, and
`knowledge/FIRST-FIGHT-FINDING-2026-10-26.md` as it stood at commit `35806b1`.
Mechanics learned: three. One, a route that is only read behind an environment flag is not a route but a harness: the
crawl took its handoff from the same file every launch reads, and the very next edge was read only when `PP_SLICE` was
set, so the demo advanced exactly one step for a player and stopped on a map with no trigger. The fix is not a second
walk but the same `next` edge taken by the player's run through the same handoff door, with a cursor of its own so a
`PP_SLICE` run never takes a step twice. Two, the honest place to catch "this scene ended" is the one place a finished
runner is let go, not the `end` command: a scene can also finish by running out of commands or by its command cap, and a
hook on `end` alone would miss those and be a second path that can disagree. Three, a long opening cutscene is not the
gate in front of the first fight, it is the invitation: 10,680 steps and twelve press-gated captions is the drive's own
work (cue PP-02, eleven cuts), so it stays whole and gains the skip a player can press instead of being cut down to a
capture's length.
Our implementation differs by: the route's player half lives in five small functions beside the walk rather than in a
second state machine, a scene row opts in to being skippable with one boolean instead of the runner guessing from
length, and the corridor gets a `map` trigger on its own start tile as a floor under the route rather than a portal the
scene has to name. The decisions are written in `specs/20-demo-route.md` and rules 9 and 10 of `specs/06`.
Copied expression: none
