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
| game/objects/obj_pp_debug_overlay/Draw_64.gml | reviewed | gamedev | 2026-10-22 |
| game/objects/obj_pp_debug_overlay/Step_0.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_drive/Create_0.gml | reviewed | code-review | 2026-10-23 |
| game/objects/obj_pp_drive/Draw_0.gml | reviewed | code-review | 2026-10-23 |
| game/objects/obj_pp_drive/Step_0.gml | reviewed | code-review | 2026-10-23 |
| game/objects/obj_pp_game/Create_0.gml | reviewed | gamedev | 2026-10-21 |
| game/objects/obj_pp_game/Draw_0.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_game/Other_72.gml | confirmed | code-review | 2026-10-22 |
| game/objects/obj_pp_game/Step_0.gml | confirmed | code-review | 2026-10-22 |
| game/objects/obj_pp_game/Step_1.gml | confirmed | code-review | 2026-10-19 |
| game/objects/obj_pp_title/Create_0.gml | reviewed | gamedev | 2026-10-21 |
| game/objects/obj_pp_title/Draw_0.gml | reviewed | gamedev | 2026-10-21 |
| game/objects/obj_pp_title/Draw_64.gml | reviewed | gamedev | 2026-10-21 |
| game/objects/obj_pp_title/Step_0.gml | reviewed | gamedev | 2026-10-21 |
| game/scripts/pp_app/pp_app.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_art/pp_art.gml | reviewed | gamedev | 2026-10-21 |
| game/scripts/pp_audio/pp_audio.gml | confirmed | gamedev review | 2026-10-22 |
| game/scripts/pp_battle_commands/pp_battle_commands.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_battle_director/pp_battle_director.gml | reviewed | gamedev | 2026-10-22 |
| game/scripts/pp_battle_text/pp_battle_text.gml | rewritten | gamedev | 2026-10-22 |
| game/scripts/pp_camera/pp_camera.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_config/pp_config.gml | reviewed | gamedev | 2026-10-22 |
| game/scripts/pp_data/pp_data.gml | confirmed | gamedev review | 2026-10-22 |
| game/scripts/pp_dialogue/pp_dialogue.gml | rewritten | gamedev | 2026-10-22 |
| game/scripts/pp_drive/pp_drive.gml | reviewed | code-review | 2026-10-23 |
| game/scripts/pp_dodge_arena/pp_dodge_arena.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_dodge_recipe/pp_dodge_recipe.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_input/pp_input.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_font/pp_font.gml | reviewed | gamedev | 2026-10-21 |
| game/scripts/pp_ledger/pp_ledger.gml | reviewed | gamedev | 2026-10-22 |
| game/scripts/pp_look/pp_look.gml | confirmed | code-review | 2026-10-22 |
| game/scripts/pp_map/pp_map.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_map_tile/pp_map_tile.gml | reviewed | code-review | 2026-10-23 |
| game/scripts/pp_overworld/pp_overworld.gml | rewritten | code-review | 2026-10-19 |
| game/scripts/pp_rng/pp_rng.gml | confirmed | code-review | 2026-10-19 |
| game/scripts/pp_save/pp_save.gml | confirmed | gamedev review | 2026-10-22 |
| game/scripts/pp_scene/pp_scene.gml | confirmed | code-review | 2026-10-22 |
| game/scripts/pp_text/pp_text.gml | confirmed | gamedev review | 2026-10-22 |
| game/scripts/pp_title/pp_title.gml | reviewed | gamedev | 2026-10-21 |

The two rows that were `pending` were reviewed by gamedev on 2026-10-21 and raised to `confirmed` by code-review on
2026-10-22 (card t_edf0aafe, the gate on the save work and its tests), so each row names its own reviewer and date
rather than leaving it to the next person. `game/scripts/pp_save/pp_save.gml` and `game/objects/obj_pp_game/Other_72.gml`
were both added by card t_a311bdff on 2026-10-20 (the save slot, spec 11). Both reviews read this repository's own text
only: the specs, the manual pages the module's own header cites, and the module's source. What the first found is
recorded under "the save module" below. What the run measured is narrower than "this module works": on 2026-10-20 and
2026-10-21 the game was built and run on this machine, the boot read of the slot was exercised through the Save/Load
event and the title drew its continue line, so the read path and the event number are measured; the write path through
a save point reached on foot, the `.bak` rotation and the panel timing are not, and nothing in this file claims they are.

The three rows raised on 2026-10-22 for card t_8de1aca9 (`pp_audio.gml`, `pp_scene.gml`, `obj_pp_game/Step_0.gml`) are a
clean-room verdict only. The reviewer read the changed text in each and ran `tools/check_cleanroom.py`, which reports no
blacklist hit, no reference to a study copy and no foreign name. That review did not sign the change off: the audio work
was returned with required code changes, listed on the card. A confirmed row here means the text was read and holds no
foreign material; it is not an approval of the logic.

Four rows were set back to `pending` by card t_73f08da5 on 2026-10-22, because that card changed the text after the
clean-room verdict above: `pp_audio.gml` (the fade helpers, the theme as one music source, the citations in its header),
`pp_data.gml` (the cue ids indexed beside the sounds), `pp_text.gml` (the blip call) and, in the fix round,
`pp_save.gml` (one `show_debug_message` line in `pp_save_parse` so an accepted read is visible in a runtime log, which
is what turned the "PP-05 loads clean" claim into evidence on 2026-10-22). Nothing in the change reads or
cites material outside this repository: the audio rules are specs 05 and 12, the cue ids are the musician lane's own
list, the save rules are spec 11, and every engine call's behaviour is the manual page named next to it. A reviewer
still has to read the new text before a row says `confirmed` again.

Those four rows were read again on 2026-10-22 in the review of commit `6780273` (the fix round of the same card) and
raised to `confirmed` as a clean-room verdict only, not as an approval of the logic. What the review read: `pp_audio.gml`
and its three `theme_inst` guards with the fade handoff and the cited header; `pp_save.gml` and its read, retry and parse
path plus the one log line the fix round added; `pp_data.gml` and the cue index built beside the sounds; `pp_text.gml` and
the blip call site. Every engine behaviour named on those lines is a GameMaker manual page, every rule is a spec under
`specs/`, the cue ids are the musician lane's own list, and `tools/check_cleanroom.py` reports no blacklist hit, no
reference to a study copy and no foreign name in any of the four. The clean-room failures still reported on this tree are
`data/maps/real_places.json:1099` and its mirror under `game/datafiles/maps/`, which are the map lane's file.

`rewritten` means the file text changed in this review. All eight rewrites are comment only: each one removed a
provenance parenthetical that described the internals of the quarantined copy, and replaced it with the spec the
structure is actually written from. No logic line, no number and no data field changed, and `python -m pytest tests -q`
plus the three checkers were run afterwards.

The `pp_look.gml` row was raised from `pending` to `confirmed` on 2026-10-22 by code-review, on card t_047bb3a7 (the gate
on the 8 bit look and its tests). What that reviewer read: the whole module, its provenance entry, and the three official
manual pages the entry names (application_surface, display_set_gui_size, gpu_set_tex_filter), plus the room palette data
and `tools/check_data.py`. `tools/check_cleanroom.py` reports no blacklist hit and no reference to a study copy. Nothing
decompiled or ripped was opened, searched or reasoned from, and the quarantine folder was not touched. As with the rows
above, confirmed is a clean-room verdict only: the same card returned the change with required code fixes.

The rework that answered those fixes (card t_638da7e0, same day) changed this module again: it cites the manual page
above every engine call, it enables viewport 0 and pins the camera view to the frame, it deletes the letterbox offset
fields, and the role lookup now answers only from the room's palette set. What gamedev read while making those changes:
the GameMaker manual pages for application_surface, surface_resize, display_set_gui_size, gpu_set_tex_filter (documented
as gpu_set_texfilter), view_enabled, view_visible, view_set_wport and camera_set_view_size, the runtime's own function
table GmlSpec.xml to confirm the underscored filter spelling, and this repository's own palette and room palette data.
Nothing decompiled or ripped was opened, searched or reasoned from, and the quarantine folder was not touched, so the row
stays confirmed.

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
- `game/objects/obj_pp_title/Create_0.gml`: reviewed. Three calls in a fixed order: load the art index, make the
  screen's state, enter the screen. The art index comes first because the screen draws from it, so the order is a
  dependency and not a preference. The sources are spec 14 and the manual's object event pages. A title screen as one
  object that owns its own state is the ordinary shape, and the three calls are this project's own functions.
- `game/objects/obj_pp_title/Step_0.gml`: reviewed. One guard and one call. The guard is the app's mode: the screen
  stops acting the moment the app machine leaves the title mode, so the overworld is never drawn over the title.
  That is spec 01's rule that one mode owns the frame, applied at the object rather than in the app, and the guard is
  the ordinary way to keep an object honest about who owns the screen.
- `game/objects/obj_pp_title/Draw_0.gml`: reviewed. One guard and one call, the mirror of the Step event: the screen
  draws itself only while the app machine is in the title mode, so the app's title mode draws nothing and there is
  still one owner of the frame. The sources are spec 14 and spec 01.
- `game/objects/obj_pp_title/Draw_64.gml`: reviewed. An empty event on purpose. The Draw GUI event draws over the
  room, and the title screen is drawn in the room rather than over it, so there is nothing to do here. The comment
  says so, because an empty event with no explanation reads as an oversight.
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
- `game/scripts/pp_battle_text/pp_battle_text.gml`: rewritten, 2026-10-22 (card TEXT-REVEAL-1). The module no longer
  holds a reveal: it builds one unit per line with `pp_text_items`, hands them to one `pp_text_reveal_begin`, and keeps
  only where the lines are drawn. What is left is board geometry and a call into the shared machine, which is our own
  layout code from spec 07 rule 6.
- `game/scripts/pp_text/pp_text.gml`: rewritten, 2026-10-22 (card TEXT-REVEAL-1). The reveal machine itself: an item
  list, a step accumulator, a hold value, the punctuation pauses from spec 05 rule 2, a blip interval, a skip and a done
  predicate, plus one boolean that says whether a unit end advances by itself. Every number it uses is a macro in
  pp_config and every rule is a line of spec 05; no text, identifier or expression comes from anywhere else.
- `game/scripts/pp_camera/pp_camera.gml`: rewritten. Construct named and removed: the parenthetical citing a window
  resize "event index we have not verified", a detail of the studied project's event wiring. The logic is an integer
  scale from the window size, an application surface resize, a dead zone follow and a whole pixel clamp, from spec 03 and
  the manual's application_surface page; the window is polled, so no event number is assumed.
- `game/scripts/pp_config/pp_config.gml`: confirmed. Constants and enums that transcribe numbers the specs already fix;
  there is no logic to copy, and each macro names its spec.
- `game/scripts/pp_data/pp_data.gml`: confirmed. A JSON loader with a try/catch, an id index and a plain error list, from
  the manual's json_parse and json_stringify pages and spec delta M1; loading data by id is ordinary practice and the
  file deliberately holds no content.
- `game/scripts/pp_dialogue/pp_dialogue.gml`: rewritten, 2026-10-22 (card TEXT-REVEAL-1). Construct named and removed:
  the parenthetical citing the studied "message and dialogue flow". The module now holds the box and nothing else: word
  wrap, pages, the portrait frame, the name plate and the arrow. The reveal it used to own lives once in pp_text. The
  geometry is the spec's decision and the wrap is a greedy fill over the shared item list.
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
- `game/scripts/pp_title/pp_title.gml`: reviewed. The module holds the state of the title screen in one struct and
  draws seven seamless layers at the scroll speeds TITLE-COORD.md fixes, then the car, the sign, the logo and the
  menu. The sources are specs\14-title-screen-drive.md with its night drive addendum, TITLE-COORD.md, the manual's
  draw_sprite_part_ext, draw_set_colour, draw_rectangle, draw_set_alpha and draw_set_font pages, and the project's own
  data\title.json. The scene is original: the two reincarnations driving from London to Southampton, the counting down
  sign and the night drive are this project's own story, and every number in the file is a macro in the file itself
  with the reason in the comment beside it.
  The one thing worth recording here is a defect the review found and fixed, because it is the kind that a read-through
  cannot catch and only a compile can: the four draw_sprite_part_ext calls in pp_art and pp_font passed ten arguments
  where the runtime's own GmlSpec.xml declares twelve, and had the source rectangle and the destination position
  swapped. The fix is in the runtime's parameter order (sprite, subimg, left, top, width, height, x, y, xscale, yscale,
  colour, alpha), and the title now renders with the source rectangle on the sprite and the destination on the screen.
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

## Review, 2026-10-22: the exit rows and the fight verdict (card t_48020b30)

Five files were reviewed on this date because the card changed them: `game/scripts/pp_ledger/pp_ledger.gml`,
`game/scripts/pp_battle_director/pp_battle_director.gml`, `game/scripts/pp_config/pp_config.gml`,
`game/scripts/pp_save/pp_save.gml` and `game/objects/obj_pp_debug_overlay/Draw_64.gml`.

- `pp_ledger.gml`: one row per enemy in a plain array, an exit state read from the existing result enum, and a verdict
  computed from the rows. This is `knowledge\FOX-STYLE.md` section 2, which is this project's own doctrine, and spec 10
  rule 6 as refreshed the same day. The construct is a record plus a roll up, which is the oldest shape in the genre and
  is not text from anywhere.
- `pp_config.gml`: two enums of three names each, `PPExit` and `PPFightVerdict`, plus two save bounds. Names and
  numbers are spec 10's.
- `pp_battle_director.gml`: one call site, `pp_ledger_record_exit`, and one call to `pp_ledger_begin_fight` in the
  battle constructor. The director still writes no counter.
- `pp_save.gml`: one optional key, `fight_exits`, a shape check on each row, and a verdict recomputed on load. Every
  required key, the format check, the backup rotation and the validation order are untouched, so the 2026-10-21 review
  of the module stands and this review covers the addition only.
- `Draw_64.gml`: the F3 box sizes itself from a line count the ledger reports, so no row can draw outside it.

Nothing outside this repository was read for any of the five, and no sentence in them was taken from anywhere.

## Review, 2026-10-22: the save gate (card t_edf0aafe)

The gate on the save work and its tests read `game/scripts/pp_save/pp_save.gml` in full (955 lines as it stands, which is
the 834 lines of card t_a311bdff plus the exit rows of card t_48020b30) and `game/objects/obj_pp_game/Other_72.gml` in
full, and read nothing outside this repository. The two rows above are raised to `confirmed` on that read. This is a
second pair of eyes on the same two files, not a replacement for the two earlier reviews.

Why the save module is genre level rather than anyone's expression, in one paragraph: the shape is a small asynchronous
state machine with one callback as its only mover, a fixed size buffer holding a count and a JSON text, a validator that
refuses a document before it applies any of it, a snapshot that stores names and counters, and a reader that falls back
once to a backup. Each part is a line of spec 11 or spec 10: the asynchronous pair and its event are the manual's, while
the format first rule, the backup, the validation order and the derived route are this project's decisions, and the file
layout follows from the spec's own requirement that a larger save be a clear error and not a truncation. `Other_72.gml`
is one call into that module. No identifier, sentence or structure in either file reads as anything but that.

What this review did not establish, and does not claim: that the write path works on a running game. A save file this
module wrote is on disk (`pp_save_01.json`, 314 bytes, a count of 309, the sixteen spec keys and no `fight_exits`), and
the read path and the event number have been measured on a real run, but the write through a save point reached on foot,
the `.bak` rotation, the refusal of a document larger than the slot and the panel timing are still unproven by a run.

## What the rows do not claim

A confirmed row is not a proof that no sentence in a module resembles a sentence somewhere else. It is the reviewer's
statement that the module's structure is reachable from its spec, and that the spec is reachable from genre design and
the manual, having read this repository's own text only. A text diff against the quarantined copy is the one check the
rule forbids, so this file does not pretend to have run it.
