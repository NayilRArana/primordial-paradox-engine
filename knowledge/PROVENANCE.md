# Provenance: what was studied, and how ours differs

Rule: a subsystem cannot be committed until it has an entry here. Each entry names the source read, the mechanics
learned in plain language, and the concrete ways our implementation differs. "Copied expression: none" is a claim
about this repository, and it is checked by tools\check_provenance.py plus the clean-room scan described below.

THE STUDY COPIES ARE QUARANTINED AND MAY NOT BE USED. A read against a decompiled commercial game project took place
on 2026-10-19 and was ruled a clean-room breach; the copies were moved out of this repository and locked away. Nothing
in this repository may read, open, search, download or reason from them, or from any other decompiled, ripped or fan
ported copy of a commercial game, GitHub repositories included.

The two subsystem entries that were written after that read are now WITHDRAWN. On 2026-10-19 (card t_bfaff47b) the
manager's rule was applied to the last two documents that still leaned on the read: documentation in this repository
has to stand on public sources, so anything that only the read supported is withdrawn rather than softened. Both
entries are kept below as an incident record of what was studied, each opens with its status, and each says in one line
that no current module descends from it. The module map now points every module at one entry, "modules written from the
specs alone", which names no studied source at all.

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
| game/scripts/pp_audio/pp_audio.gml | specs alone | 12, 14 (proposed) |
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
| game/scripts/pp_overworld/pp_overworld.gml | specs alone | 04 |
| game/scripts/pp_scene/pp_scene.gml | specs alone | 06 |
| game/scripts/pp_title/pp_title.gml | specs alone | 14 (proposed) |
| game/scripts/pp_input/pp_input.gml | specs alone | 02 |
| game/scripts/pp_font/pp_font.gml | specs alone | 13, 14 (proposed) |
| game/scripts/pp_ledger/pp_ledger.gml | specs alone | 10 |
| game/scripts/pp_rng/pp_rng.gml | specs alone | 09 |
| game/scripts/pp_save/pp_save.gml | save, load and resume | 01, 10, 11 |
| game/objects/obj_pp_game | specs alone | 01, 02 |
| game/objects/obj_pp_debug_overlay | specs alone | 10 |
| game/objects/obj_pp_title | specs alone | 14 (proposed) |
| game/rooms/rm_pp_boot | specs alone | 01 |
| tools/art/make_title_ui.py | title art generator | 14 (proposed) |
| tools/gen_project.py | specs alone | 14 (proposed) |
| tools/check_project.py | specs alone | 14 (proposed) |
| tools/check_data.py | specs alone | 08, 09, 14 (proposed) |
| tools/check_cleanroom.py | this file | PLAN 1 |
| tools/check_provenance.py | this file | PLAN 1 |

Every "specs alone" row is owned by the entry "modules written from the specs alone" below. That entry, not either
withdrawn entry, is what a new module must be written from.

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
