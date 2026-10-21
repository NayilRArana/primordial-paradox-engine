# Clean-room review record

Rule, set by Nayil and restated by the manager after the breach of 2026-10-19: nothing in this repository may be
written from a decompiled or ripped commercial game. The study copies that P1-A cloned were quarantined by the manager
on 2026-10-19 and may not be read, searched, opened or reasoned from again. Specs 01 to 13, the six knowledge files and
the two PROVENANCE subsystems that were studied were reviewed against public genre design and the official GameMaker
manual only, on this card, and only by text: nothing decompiled was opened, and no comparison against the quarantined
copy was possible or attempted, because making that comparison is the breach.

This file is that review's ledger. `tools/check_cleanroom.py` reads it and refuses:

- a GML module with no row here at all;
- a row that says confirmed, rewritten or reviewed without a reviewer and a date;
- any file under `game\` or `data\` that names a study copy, the quarantine folder or the decompilation repository;
- any foreign character name or distinctive phrase from either of those games.

A row that says `pending` is not a pass. It is reported on every run, by name, until a reviewer rules on it.

Reviewer: code-review. Date: 2026-10-19. Spec verdicts: `knowledge\SPEC-REVIEW.md`. Source file verdicts and the
review's method: the "clean-room re-review 2026-10-19" section at the end of `knowledge\PROVENANCE.md`.

| Module | Status | Reviewer | Date |
| --- | --- | --- | --- |
| game/objects/obj_pp_debug_overlay/Create_0.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_debug_overlay/Draw_64.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_debug_overlay/Step_0.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_game/Create_0.gml | reviewed | gamedev | 2026-10-21 |
| game/objects/obj_pp_game/Draw_0.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_game/Other_72.gml | reviewed | gamedev | 2026-10-21 |
| game/objects/obj_pp_game/Step_0.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_game/Step_1.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_app/pp_app.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_art/pp_art.gml | reviewed | gamedev | 2026-10-21 |
| game/scripts/pp_audio/pp_audio.gml | reviewed | gamedev | 2026-10-21 |
| game/scripts/pp_battle_commands/pp_battle_commands.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_battle_director/pp_battle_director.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_battle_text/pp_battle_text.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_camera/pp_camera.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_config/pp_config.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_data/pp_data.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_dialogue/pp_dialogue.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_dodge_arena/pp_dodge_arena.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_dodge_recipe/pp_dodge_recipe.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_input/pp_input.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_font/pp_font.gml | reviewed | gamedev | 2026-10-21 |
| game/scripts/pp_ledger/pp_ledger.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_map/pp_map.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_overworld/pp_overworld.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_rng/pp_rng.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_save/pp_save.gml | reviewed | gamedev | 2026-10-21 |
| game/scripts/pp_scene/pp_scene.gml | rewritten | code-review | 2026-10-19 |

The two rows that were `pending` are now `reviewed` by gamedev on 2026-10-21, and the reviewer is named in the row
rather than left to the next person. `game/scripts/pp_save/pp_save.gml` and `game/objects/obj_pp_game/Other_72.gml` were
both added by card t_a311bdff on 2026-10-20 (the save slot, spec 11). The review that closed them read this
repository's own text only: the spec, the manual pages the module's own header cites, and the module's source. What it
found is recorded under "the save module" below, and the same two modules are the ones exercised by the real run, so
their behaviour is measured rather than assumed.

`rewritten` means the file text changed in this review. All eight rewrites are comment only: each one removed a
provenance parenthetical that described the internals of the quarantined copy, and replaced it with the spec the
structure is actually written from. No logic line, no number and no data field changed, and `python -m pytest tests -q`
plus the three checkers were run afterwards.

## Why each module is genre level

Each line is the reviewer's one sentence answer to "why is this logic the ordinary shape of the genre rather than
someone's expression". A module that leaned on a studied detail has the exact construct named.

- `game/objects/obj_pp_debug_overlay/Create_0.gml`: confirmed. One visibility boolean for a debug view (spec 10 rule 5);
  a toggle flag is the smallest possible overlay state.
- `game/objects/obj_pp_debug_overlay/Draw_64.gml`: confirmed. Reads the mode name and the ledger dump and draws two
  strings in the GUI layer; presenting state as text is what every debug overlay does and the ledger is ours (spec 10).
- `game/objects/obj_pp_debug_overlay/Step_0.gml`: confirmed. One `pp_pressed("debug_flags")` toggle; the action table and
  the edge flag are spec 02's, so no key code appears here.
- `game/objects/obj_pp_game/Create_0.gml`: reviewed. One call to `pp_app_boot()` is spec 01 rule 1, and a single
  boot entry point is the ordinary shape of a game frame. Changed on 2026-10-21: an unhandled exception handler is
  installed before the boot call, so a runtime error is written to `pp_crash.log` and to the Igor log instead of
  appearing as a Windows error box that no build or unattended run can read. The handler is the manual's own documented
  mechanism for taking over the error message, its fields are the ones the manual names (message, longMessage, script,
  line, stacktrace), and it reads them defensively so that the handler cannot itself throw and lose the error. This is
  a diagnostic aid written from the manual's example, not a mechanic taken from anywhere else.
- `game/objects/obj_pp_game/Draw_0.gml`: confirmed. One call to `pp_app_draw()`; the mode machine owning the frame is
  spec 01 rule 1, and the manual's event order makes Draw the one place that draws (gml-essentials section 1).
- `game/objects/obj_pp_game/Other_72.gml`: reviewed. One call to `pp_save_async_event()`, which matches the reported
  async id against its own request before acting, from spec 11 and the manual's Save/Load asynchronous event page. The
  event number 72 is the IDE's Async Save/Load slot, which the manual does not print; the module says so in its own
  header rather than asserting it as a fact, and the number is confirmed by the fact that the module is reached at all
  in a real run on this machine (measured 2026-10-21: the save was read and its line drawn on the title card).
- `game/objects/obj_pp_game/Step_0.gml`: confirmed. Camera poll then app step; the manual's guaranteed Step ordering is
  the reason this object can be the only Step in the game (gml-essentials section 1).
- `game/objects/obj_pp_game/Step_1.gml`: confirmed. The single Begin Step input sample of spec 02; the manual states
  Begin Step runs before every Step, which is why the sample lives here rather than in a Step.
- `game/scripts/pp_app/pp_app.gml`: rewritten. Construct named and removed: the provenance parenthetical citing the
  studied controller's "shared phase globals". The logic is a mode registry with one request door, one fade and explicit
  enter/step/draw methods, which is spec 01 rules 1 to 3; a state machine with one owner is the ordinary shape for a game
  frame, and no phase number is shared between modules.
- `game/scripts/pp_art/pp_art.gml`: reviewed. The module reads a JSON index of animations at boot, loads one sprite per
  PNG with `sprite_add`, and draws frames with `draw_sprite_part_ext`; a layer is one image wider than the view and is
  scrolled by drawing its tail and then its head, which is the ordinary way to scroll a wrapping strip. The sources
  are spec 14 and the manual's sprite_add, draw_sprite_part, file_text_open_read and json_parse pages, and the module's
  own data-driven index. Every value in it comes from the manifest or from the spec: the frame period is
  `round(60 / fps)`, the frame is wrapped into range, and an animation that is not in the index is simply not drawn.
  Reviewed on 2026-10-21 by gamedev while the art lane was still landing its files; the verdict is on the module's
  shape and sources, not on the art it draws.
- `game/scripts/pp_audio/pp_audio.gml`: reviewed. The module answers a cue by name, and the cue list is the one spec
  12 and spec 14 name. A cue whose sound has not been delivered is silent on purpose rather than making a noise out
  of nothing, and every request is counted so the log shows what the screen asked for. The sources are spec 12, spec
  14 and the manual's show_debug_message page. A cue bus is ordinary practice, and the cue names are ours.
- `game/scripts/pp_battle_commands/pp_battle_commands.gml`: rewritten. Construct named and removed: the parenthetical
  citing the studied menu's "per case branches". The logic is a five row table (FIGHT, POWER, TALK, SPARE, ITEM) whose
  enable test returns a reason string, from the spec 07 action table and rule 1; a command table for a menu is
  genre-level, and the reason string is our own.
- `game/scripts/pp_battle_director/pp_battle_director.gml`: confirmed. An explicit `PPBattlePhase` enum with one step
  function per phase and a single transition door, from the spec 07 turn flow; a turn loop written as a phase machine is
  the ordinary implementation of "player phase, message, enemy telegraph, dodge, repeat", and every number comes from
  data or pp_config.
- `game/scripts/pp_battle_text/pp_battle_text.gml`: confirmed. A reveal counter, a per character step count and a
  punctuation pause, from spec 05 text rules 1 to 2; typewriter presentation is genre standard and the parameters are
  ours.
- `game/scripts/pp_camera/pp_camera.gml`: rewritten. Construct named and removed: the parenthetical citing a window
  resize "event index we have not verified", a detail of the studied project's event wiring. The logic is an integer
  scale from the window size, an application surface resize, a dead zone follow and a whole pixel clamp, from spec 03 and
  the manual's application_surface page; the window is polled, so no event number is assumed.
- `game/scripts/pp_config/pp_config.gml`: confirmed. Constants and enums that transcribe numbers the specs already fix;
  there is no logic to copy, and each macro names its spec.
- `game/scripts/pp_data/pp_data.gml`: confirmed. A JSON loader with a try/catch, an id index and a plain error list, from
  the manual's json_parse and json_stringify pages and spec delta M1; loading data by id is ordinary practice and the
  file deliberately holds no content.
- `game/scripts/pp_dialogue/pp_dialogue.gml`: rewritten. Construct named and removed: the parenthetical citing the
  studied "message and dialogue flow". The logic is control code parsing, greedy word wrap, page splitting and a reveal
  clock, from spec 05 rules 1 to 6; text presentation with pages and pauses is genre level, and the box geometry is the
  spec's decision.
- `game/scripts/pp_dodge_arena/pp_dodge_arena.gml`: confirmed. A bounded box, a clamped marker, an AABB hit test with a
  two pixel inset, an invulnerability counter and a step cap, from spec 08's geometry and fairness rules; the physics of
  a bounded playfield is the genre mechanic itself (genre-design section 2), and every number is a PP decision.
- `game/scripts/pp_dodge_recipe/pp_dodge_recipe.gml`: confirmed. Compiles a data recipe into a sorted spawn list and
  walks it by elapsed step, with origin, spread, accel, curve and wobble from the spec 09 field table; an emitter driven
  by a schedule is ordinary machinery, and the data-not-code choice is a deliberate difference from the studied design,
  not a copy.
- `game/scripts/pp_input/pp_input.gml`: confirmed. One action table sampled once per step in Begin Step, edge flags
  derived from held/prev, a stick dead zone and one normalised vector, from spec 02 and the manual's keyboard and game
  input pages; an action abstraction over raw keys is the manual's own recommendation.
- `game/scripts/pp_font/pp_font.gml`: reviewed. The module draws text from the 8x8 sprite sheet, one frame per glyph
  in ASCII order, so a glyph is addressed by its position in the ASCII set rather than by a table of offsets. The
  sources are spec 13 (the font and UI rule) and the art lane's own contract in TITLE-COORD.md, plus the manual's
  draw_sprite_part_ext and string_pos pages. A bitmap font sheet addressed by glyph index is the ordinary way to draw
  pixel text without the engine's default font, which is exactly what the spec asks for, and the glyph set and the 8
  pixel advance are this project's own.
- `game/scripts/pp_ledger/pp_ledger.gml`: rewritten. Construct named and removed: the parenthetical citing a "per enemy
  result enum". The logic is four counters, named flags and a route derived on read from counters plus story stage, from
  spec 10 rules 1 to 5 and delta T12; "count, do not score" is a public genre pattern (genre-design section 4) and
  deriving one value instead of storing two is ordinary single-source-of-truth practice.
- `game/scripts/pp_map/pp_map.gml`: rewritten. Construct named and removed: the parenthetical citing the studied "room
  and tile layer data". The logic is a character tile grid, a parallel collision grid, a trigger lookup and a rectangle
  draw loop, from spec 04's three data pieces; separating art from collision is stated in spec 04 as a design choice.
- `game/scripts/pp_overworld/pp_overworld.gml`: rewritten. Construct named and removed: the parenthetical citing the
  studied "room flow and overlay battle start". The logic is a tile step walker, a confirm target, a marker respawn
  clock, a trigger lock and a fade, from spec 04 rules 1 to 6 and delta T5; a grid walker with doors and triggers is the
  8-bit console RPG convention (genre-design section 6).
- `game/scripts/pp_rng/pp_rng.gml`: confirmed. A linear congruential generator with the published Numerical Recipes
  constants and a mod wrap, used to make patterns deterministic per spec 09 rule 2; the algorithm is public textbook
  code and the choice to seed one stream per battle is ours.
- `game/scripts/pp_save/pp_save.gml`: reviewed. The module reads and writes one versioned JSON document through the
  asynchronous buffer functions, validates every field before applying any of it, and keeps the route derived from
  counters rather than stored, all of which is spec 11 and spec 10. The review read the module's source against those
  specs and against the manual pages its own header cites (buffer_create, buffer_write, buffer_read, buffer_tell,
  buffer_seek, buffer_delete, buffer_load_async, buffer_save_async, json_parse, json_stringify, the Save/Load
  asynchronous event, date_current_datetime, date_datetime_string), and against nothing else.
  Three runtime facts were measured on this machine on 2026-10-20 and 2026-10-21, and each one is a property of the
  engine rather than of any game:
  - the first asynchronous request in a process is given the id 0, so "the transfer did not start" is a negative id and
    not "less than or equal to zero". The guard in the module now says so.
  - a buffer handle is not a real number in this runtime, so the "is this a usable buffer" test cannot be `is_real`;
    the module tests for the value being defined instead.
  - a number read with `buffer_read(buffer_u32)` is an int64, so `is_real` is false for it too; `is_numeric` is the
    test that works.
  None of these is a mechanic borrowed from anywhere. They are the engine's own types, read from the engine's own
  documentation and confirmed by running it, and the module's data model (a 4 byte count then a null terminated JSON
  string in one fixed buffer, with a format number checked first and a backup that is only ever rotated from a file
  this session read as good) is spec 11's own design.
- `game/scripts/pp_scene/pp_scene.gml`: rewritten. Construct named and removed: the parenthetical citing the studied
  "phase sequencing". The logic is a command list runner with one blocking state per command and branch as the only
  control flow, from spec 06 rules 1 to 3; a scripted sequence interpreter is the ordinary form for cutscenes, and the
  no-loops rule is ours.

## What the rows do not claim

A confirmed row is not a proof that no sentence in a module resembles a sentence somewhere else. It is the reviewer's
statement that the module's structure is reachable from its spec, and that the spec is reachable from genre design and
the manual, having read this repository's own text only. A text diff against the quarantined copy is the one check the
rule forbids, so this file does not pretend to have run it.
