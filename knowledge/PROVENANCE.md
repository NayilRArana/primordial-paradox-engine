# Provenance: what was studied, and how ours differs

Rule: a subsystem cannot be committed until it has an entry here. Each entry names the source read, the mechanics
learned in plain language, and the concrete ways our implementation differs. "Copied expression: none" is a claim
about this repository, and it is checked by tools\check_provenance.py plus the clean-room scan described below.

THE STUDY COPIES ARE QUARANTINED AND MAY NOT BE USED. A read against a decompiled commercial game project took place
on 2026-10-19 and was ruled a clean-room breach; the copies were moved out of this repository and locked away. Nothing
in this repository may read, open, search, download or reason from them, or from any other decompiled, ripped or fan
ported copy of a commercial game, GitHub repositories included. The two subsystem entries below were written after that
read, so they do not get to assume their own innocence: the clean-room re-review of 2026-10-19 re-confirmed both of them
from public genre design and the official GameMaker manual alone, and each entry now opens with its status. The review
record for modules is knowledge\CLEANROOM-REVIEW.md, for specs knowledge\SPEC-REVIEW.md, and the method plus the per
source file outcome are in the section at the end of this file.

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

Status: written before the notice of 2026-10-19, re-confirmed by the clean-room re-review of the same date. Outcome:
the entry stands. No mechanic in it is reachable only through the quarantined read; each one is a public genre mechanic
described in knowledge\genre-design.md sections 2 to 5, and the differences below are structural, not reworded.
Changed in this review: the studied line named the copy's files and line numbers, which only ever served as navigation
for a copy nobody may open, so it now names the systems in plain language.

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

Status: written before the notice of 2026-10-19, re-confirmed by the clean-room re-review of the same date, with the
project format claims downgraded to UNVERIFIED. Outcome: the "our implementation differs by" list stands, but the four
file shape facts in this entry cannot be reached from the official manual, which publishes the roles of the files and
not their field or file name schema. They are kept as the shape our generator follows, and
knowledge\gamemaker-project-format.md now marks them unverified until the IDE writes a reference resource. Nothing in
game code depends on them.

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
