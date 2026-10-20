# Provenance: what was studied, and how ours differs

Rule: a subsystem cannot be committed until it has an entry here. Each entry names the source read, the mechanics
learned in plain language, and the concrete ways our implementation differs. "Copied expression: none" is a claim
about this repository, and it is checked by tools\check_provenance.py plus the clean-room scan described below.

The study copy lives at knowledge\study\deltamodkit (gitignored, never committed, never shipped, never read at
runtime by anything in game\). Repository: https://github.com/deltamodders/deltamodkit, read 2026-10-19, project file
records IDE version 2024.1400.0.911. Files read are named per entry. Nothing from it was copied, quoted or renamed
into this repository.

How the no-copy claim is checked, mechanically, on every commit:
1. `tools\check_cleanroom.py`: fails if anything under game\ or data\ names the study copies, fails on a foreign
   character or game name as a whole word, fails if any comment (GML) or string value (JSON) of 20 characters or more
   here appears word for word in the study copy, and fails if any `pp_` identifier exists there. Measured on
   2026-10-19: 237 of our comments and strings compared against 650 study .gml files, 0 matches.
2. `tools\check_provenance.py`: fails if any module file is missing from the module map below, or if any entry is
   missing a field or the line "Copied expression: none".
3. `tools\check_project.py`: fails if the .yyp, the .yy files and the folders on disk disagree, and fails if any file
   under game\ references knowledge\study.
4. A human read of each new module against the study files named in its entry, recorded in DEVLOG.md, and every module
   is written from a spec in specs\, not from a studied file.

## module map (which entry owns which file)

Every file that ships is listed here, and tools\check_provenance.py refuses a module that is not.

| File | Subsystem entry | Spec |
| --- | --- | --- |
| game/scripts/pp_app/pp_app.gml | room and object conventions across a whole game | 01 |
| game/scripts/pp_battle_commands/pp_battle_commands.gml | battle state machine and turn loop | 07 |
| game/scripts/pp_battle_director/pp_battle_director.gml | battle state machine and turn loop | 07 |
| game/scripts/pp_battle_text/pp_battle_text.gml | battle state machine and turn loop | 05, 07 |
| game/scripts/pp_camera/pp_camera.gml | room and object conventions across a whole game | 03 |
| game/scripts/pp_config/pp_config.gml | battle state machine and turn loop | 01, 07, 08 |
| game/scripts/pp_data/pp_data.gml | room and object conventions across a whole game | 14 (proposed) |
| game/scripts/pp_dodge_arena/pp_dodge_arena.gml | battle state machine and turn loop | 08 |
| game/scripts/pp_dodge_recipe/pp_dodge_recipe.gml | battle state machine and turn loop | 09 |
| game/scripts/pp_dialogue/pp_dialogue.gml | battle state machine and turn loop | 05 |
| game/scripts/pp_map/pp_map.gml | room and object conventions across a whole game | 04 |
| game/scripts/pp_overworld/pp_overworld.gml | room and object conventions across a whole game | 04 |
| game/scripts/pp_scene/pp_scene.gml | battle state machine and turn loop | 06 |
| game/scripts/pp_input/pp_input.gml | room and object conventions across a whole game | 02 |
| game/scripts/pp_ledger/pp_ledger.gml | battle state machine and turn loop | 10 |
| game/scripts/pp_rng/pp_rng.gml | battle state machine and turn loop | 09 |
| game/objects/obj_pp_game | room and object conventions across a whole game | 01, 02 |
| game/objects/obj_pp_debug_overlay | room and object conventions across a whole game | 10 |
| game/rooms/rm_pp_boot | room and object conventions across a whole game | 01 |
| tools/gen_project.py | room and object conventions across a whole game | 14 (proposed) |
| tools/check_project.py | room and object conventions across a whole game | 14 (proposed) |
| tools/check_data.py | battle state machine and turn loop | 08, 09, 14 (proposed) |
| tools/check_cleanroom.py | this file | PLAN 1 |
| tools/check_provenance.py | this file | PLAN 1 |

Not studied, written from the specs alone: `pp_camera`, `pp_input`, `pp_ledger`, `pp_battle_text`, `pp_map`, `pp_dialogue`, `pp_scene`, `pp_overworld`, `tools/run.ps1`.
They carry an entry here only because the module map is a completeness check, not a claim that a study happened. The two
studied systems are the battle state machine and the room and object conventions; the overworld, dialogue and cutscene
modules are written from specs 04, 05 and 06 and borrow nothing but the fact that a game has phases and a room tree.

## battle state machine and turn loop (2026-10-19)

Studied: objects\obj_battlecontroller (Create_0, Step_0, Draw_0, Draw_64, Alarm_11), scripts\scr_turn (the whole turn
loop), scripts\scr_spell lines 61 to 105 (the phase handoff), scripts\scr_attack_config (the pattern switch and its
controller data), objects\obj_dbulletcontroller, objects\obj_dbullet_maker, objects\obj_heart (Step_0),
objects\obj_grazebox (collision), scripts\scr_monster around mercy, and scripts\scr_battle (how a battle is started).

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

Our implementation differs by (files: game\scripts\pp_battle_director, pp_battle_turn, pp_battle_commands,
pp_dodge_arena, pp_dodge_recipe, pp_route_ledger):
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

## room and object conventions across a whole game (2026-10-19)

Studied: the project file (DELTAModKit.yyp) and its resource graph, the folder layout on disk, 10 object .yy files
including obj_heart, obj_battlecontroller and obj_monsterparent, 3 room .yy files, 3 script .yy files, the fonts
folder, the options folder (main, windows), and the event file naming across all 232 objects.

Mechanics learned, with the counts as measured:
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
- Same on-disk contract (one directory per resource, one .yy per resource, one .gml per event) because that is the
  format, but our naming scheme is our own: every script is a `pp_` module (`pp_input`, `pp_app_modes`,
  `pp_battle_director`, `pp_dodge_arena`), every object is `obj_pp_*`, every room is `rm_pp_*`.
- We use NO object inheritance. There are four objects at all (boot, input sampler, frame presenter, battle
  presenter); behaviour lives in functions that take a struct, so a parent object hierarchy is unnecessary and the
  logic is testable without instances.
- Content never lives in a config script. Every table that their project writes as a GML switch (items, spells,
  enemies, patterns) is a JSON file in data\ validated by tools\check_data.py before it can be loaded.
- Rooms are generated from data too: one battle presenter room and one boot room, so adding a map does not add a
  room, it adds a data file. This is the opposite of a room per screen.
- Every .yy we write is strict JSON (no trailing commas) so that tools\check_project.py can parse it with the Python
  standard library; GameMaker reads both forms, so we keep the stricter one as the machine checkable one.
- Folder view is a single `Primordial Paradox` folder tree in the .yyp, and it is generated by tools\check_project.py
  so the resource list, the folder list and the disk can never disagree.

Copied expression: none.

### What is deliberately NOT studied or taken

- No art, sprite, font, sound, music, dialogue, character name or item name from either game. Every asset in this
  project is original or public domain Greek myth naming.
- No text from any dialogue file was read. Only system structure was opened.
- The NES constraint in PLAN.md section 2 comes from Nayil's notebook and the research note, not from any decomp.
