# Save, load, resume and the ledger

Node NODE-04. Parent doctrine: `knowledge/FOX-STYLE.md` section 6, save layout, with section 2 for the
route ledger and law 9 for durability.

Read for this note: `game/scripts/pp_save/pp_save.gml`, `game/scripts/pp_ledger/pp_ledger.gml`,
`game/scripts/pp_config/pp_config.gml`, `game/scripts/pp_app/pp_app.gml`,
`game/scripts/pp_overworld/pp_overworld.gml`, `game/objects/obj_pp_game/Other_72.gml`,
`specs/11-save.md`, `specs/10-route-ledger.md`, `tests/test_save.py`, `tests/test_save_gameover.py`,
`DEVLOG.md`, `output/save_capture_verify.json`, `build/save_capture_run1.log`,
`build/save_capture_run2.log`.

There is no `specs/06-save.md`. The save spec is `specs/11-save.md`; FOX-STYLE section 6 names it in its
own derivation map, and section 10 is the cutscene runner, which owns 06.

## Status in one line

A built game wrote a save at the ship's log terminal, was closed, and a second launch chose CONTINUE and
landed on the saved tile (`output/save_capture_verify.json`, written 2026-10-23 03:43:34, card
t_673fba81 SAVE-LOAD-CAPTURE). The same two logs show the silent entry autosave firing once and the
loaded run not writing it back.

## 1. What the player sees and does

Start with a save on disk. The title card reads `Continue: Small Ship, Deck, 0:00` on the first line, and
the second line is empty unless something has gone wrong (the exact wording of a real title line is
recorded in `DEVLOG.md`, 2026-10-22). While the slot is still being read the second line reads
`checking the save`. If the main file was damaged and the backup was the one that loaded, the second line
reads `the save was damaged, so the backup was loaded`.

Press confirm on the title to continue; press cancel to start a new run, and the cancel cue `menu_cancel`
plays (`game/scripts/pp_app/pp_app.gml`, the boot card's step function).

Start with no save. The first line is empty. Confirm starts a new run at once; with no input the run
starts by itself once the boot card has been up for more than 60 steps, which is 1 second at 60 steps a
second. The exception is a save file that exists and was refused: then the card waits for a key, so the
player reads the sentence instead of losing it (spec 11 acceptance 3).

Saving on foot. A save point is a trigger row of kind `save` in the map data, and it fires on confirm, like
every other trigger except a marker (`game/scripts/pp_overworld/pp_overworld.gml`, the confirm branch:
the tile ahead first, then the tile underfoot). So the player walks up to the ship's log terminal, faces
it or stands on it, and presses confirm. No menu opens. The row's label is a name for the player and for
the log line only, never a row in a table. After a trigger fires, the 20 step trigger lock keeps confirm
from firing another one immediately, and a second save is two presses with the lock drained.
(`build/save_capture_run1.log` carries two `ship's log` lines at 2,5, lines 59 and 62, and the CONTINUE
proof in `output/save_capture_verify.json` is that same line firing again after the load.)

What the panel shows. A save the player asked for prints `Saving` in a paper panel at x 48 to x 207, y 92
to y 148, centred at x 128, first row y 101, 10 pixels between rows, 18 characters per row, up to 3 rows.
It holds for at least 20 steps (0.33 seconds) even when the disk answers sooner. A failure prints its
sentence in the same panel for up to 150 steps (2.5 seconds), and that sentence is the only thing a silent
save ever shows.

The autosave. Entering a map arms one silent save for that map. It fires once the fade is finished and
nothing else owns the screen: not a scene, not an open dialogue box, no fight requested. It draws nothing
and writes one log line, `PP: autosave, <map> <tx>,<ty>`. `build/save_capture_run1.log` line 53 is that
line for `ship_small 2,7`; `build/save_capture_run2.log` has none, because a load cancels the arm
(`pp_save_autosave_cancel`, called at the end of `pp_save_apply`).

Continuing. A load puts the player back on the saved tile in the overworld, at the save point, with the
saved music, never inside a scene. If the saved tile is not walkable under the flags that were just
restored, the load falls back to the map's named spawn point instead of dropping the hero into a wall.

The game over screen calls the same door: `pp_battle_director.gml` line 582 calls `pp_save_apply`, and a
refused continue prints its sentence rather than doing nothing.

## 2. What a save contains

Seventeen keys, sixteen required and one optional. The list is `pp_save_key_list()` in `pp_save.gml`, and
`tests/test_save.py` fails if the writer, the reader and the spec stop agreeing on it.

| key | shape | bound |
| --- | --- | --- |
| `format` | whole number, checked first | must be 1 |
| `game_version` | non empty string | `0.1.0-slice` |
| `saved_at` | string, clock stamp | `date_datetime_string` |
| `play_seconds` | whole number | 0 to 360000 |
| `map` | map id from data | must resolve |
| `spawn` | spawn name on that map | must resolve |
| `x` | whole number | 0 to map width minus 1 |
| `y` | whole number | 0 to map height minus 1 |
| `hp` | whole number | 0 to `max_hp` |
| `max_hp` | whole number | 1 to 999 |
| `powers` | list of power ids | each must resolve in data |
| `items` | list of `{id, count}` | count 1 to 99, id must resolve |
| `flags` | table of name to true | name up to 64 chars, no spaces, must be known |
| `counters` | exactly the four route counters | each 0 to 9999 |
| `seen_scenes` | list of scene ids | each must resolve, cross checked against flags |
| `music` | audio id or empty string | must be a cue of kind music |
| `fight_exits` | optional, list of `{id, exit, round}` | at most 32 rows, round 0 to 9999 |

Everything is a name, never an index. Powers and items are stored as ids only, and the full row is rebuilt
from `data/` on load, so a balance change lands on the next load instead of being frozen into an old save.

What is deliberately not in the file:

- the route name and the fight verdict, because both are functions of what is in the file
  (spec 10 lines 27 to 29, and `tests/test_save.py::test_no_route_word_is_stored_in_the_save`);
- the ledger's story stage, so a save carries the four counters and the flags and nothing else;
- money, because there is no money system anywhere in this build or in spec 11;
- hero facing, camera, and any scene position, which is why a load always lands in the overworld;
- input bindings, which are a fixed table in `game/scripts/pp_input/pp_input.gml` and are not rebindable
  yet, so there is nothing to save per slot or globally.

Only flags that are true are written. A false flag is the absence of a flag, here and in the ledger.

Flags and seen scenes are two copies of one fact, so `pp_save_validate` checks them against each other in
both directions and refuses a file where they disagree. That is the rule the whole validator follows: a
missing field is not a default, it is a file this build did not write.

## 3. The file on disk

Two files in the game's save area, under the `default` folder:
`<home>\AppData\Local\PrimordialParadox\default\pp_save_01.json` and the same name plus `.bak`.
Both names are macros in `pp_config.gml` (`PP_SAVE_SLOT`, `PP_SAVE_BACKUP`) and are reached through
`pp_save_name_main()` and `pp_save_name_backup()`.

Byte layout: a 4 byte unsigned count of the JSON text, then the JSON text as a null terminated string,
then nothing. The buffer is fixed at 65536 bytes, so the text is refused when it exceeds 65531 bytes
(65536 minus the 4 byte count and the terminator). `buffer_tell` gives the write its length, so only the
used bytes reach the disk.

The count is the whole point. On read, the count and `string_byte_length` of the text must agree, so a cut
file is refused with `the save file is not whole` instead of half parsed. The only file size on record is
314 bytes with a declared count of 309 (`DEVLOG.md`, 2026-10-22), so a real save is a few hundred bytes
and the 64 KB ceiling is headroom, not a target.

There is no `file_exists` and no `file_copy` anywhere on the slot. A relative name handed to
`buffer_load_async` lands in the save area's `default` folder while `file_exists` resolves the same name
against the save area root, measured 2026-10-20, so an existence check could not see the game's own file.
The async load's `status` is the existence test.

## 4. Writing: the gate, then the order of operations

The slot is one struct in `global.pp.save` with one state value, from `PPSaveState` in `pp_config.gml`:
idle 0, reading 1, retrying 2, backing 3, backing_write 4, writing 5, ready 6, saved 7, absent 8,
failed 9. Only `pp_save_async_event` moves it on, and that function is called from one place,
`game/objects/obj_pp_game/Other_72.gml`, the IDE's Async Save/Load event.

The gate is `pp_save_busy()`, true while the state is reading, retrying, backing, backing_write or
writing. Both `pp_save_write` and `pp_save_read` refuse while it is true, and the autosave step waits
instead of dropping its save. The request id lives in `request`, starts at negative one, holds the value
the async call returned, and returns to negative one when the transfer reports back. The event ignores any
`async_load` id that does not match `request`, so another transfer later, an audio group load for example,
can never be mistaken for a save.

Order of a player save:

1. Refuse if busy, if the app mode is not overworld, or if a scene, a dialogue or a requested fight owns
   the screen. The mode and screen refusals each print their own line, so a save that a scene blocked
   leaves a trace in the log.
2. Build the document from the live game (`pp_save_snapshot`), stringify it, and refuse it if it is not a
   string, is empty, or is larger than 65531 bytes.
3. If this session holds the slot as good (`present`, which a good read or a good write sets), rotate it:
   load the current file into a spare buffer, re-emit those bytes with a count into a second buffer, and
   save that as `pp_save_01.json.bak`. The new payload waits for that to report back (states backing, then
   backing_write).
4. Save the new payload as `pp_save_01.json` (state writing).
5. On a good report, state becomes saved and `present` becomes true. On a bad report, the sentence
   `the save could not be written` and state failed.

Every buffer is 65536 bytes. Nothing waits: the write hands the buffer to the runtime and returns, which
is the "game does not freeze" half of spec 11 acceptance 5. The panel is drawn from the app's draw event
(`pp_app.gml` line 253, `pp_save_draw_panel`), not from the save step.

If a transfer cannot start at all, the id comes back negative, the buffer is abandoned rather than
deleted, and the player is told. One lost 64 KB is deliberate; the alternative is deleting memory the
runtime still holds, which is section 5.

## 5. The first frame crash, and what fixed it

On 2026-10-20 at 18:32 the first real run wrote
`<home>\AppData\Local\PrimordialParadox\pp_crash.log` and ended. The trace, quoted in `DEVLOG.md`:

```
message: Cannot delete buffer, it's in use by 1 others
where: gml_Script_pp_save_read_backup line 237
  gml_Script_pp_save_read_backup (line 237) - buffer_delete(_s.spare);
  gml_Script_pp_save_read (line 226) - pp_save_read_backup();
  gml_Script_pp_save_title_start (line 114) - return pp_save_read("title");
  pp_app_boot -> obj_pp_game Create
```

That is the first frame: the boot card asks the slot what it holds before the title draws, so the crash
happened ahead of any frame the player could see. The game reached the room and ended.

The cause was one wrong comparison. The first asynchronous request in a GameMaker process gets the id 0,
and the module treated an id of 0 or less as "the transfer refused to start". So the very first read of
the slot took the failure branch, and that branch deletes the buffer it had just created, which the
runtime was still reading into.

The fix has three parts, all in `pp_save.gml`:

1. The refusal test is `id < 0`, so zero is a real request. `request` starts at negative one and the event
   guard is `_s.request < 0`, so "no request" is negative rather than "not positive".
2. When a transfer cannot start, the buffer is abandoned by setting it to `undefined`, never deleted,
   because the runtime may still hold it. The same rule is in `pp_save_read`, `pp_save_read_backup` and
   `pp_save_start_write`.
3. A buffer the module does hold is deleted only after its transfer has reported back, which is the one
   moment the runtime is done with it.

Two more refusals were found by measurement the same night and fixed the same way. A buffer handle is a
reference in this runtime, not a number (`typeof` is `ref`, `is_real` is false), so the old guard refused
every valid buffer and every load said the file was not whole; `is_undefined` is the test that works. A
number read with `buffer_read(buffer_u32)` is an int64, not a real, so the length prefix was refused even
on a perfect file; `is_numeric` is the test that works.

After the fix the build launched, sat on the title, and `pp_crash.log` was not recreated. FOX-STYLE
section 6 keeps the lesson in one line: an async operation id is valid at zero, so idle is negative.

## 6. Reading, and the backup slot

Reading is the same state machine backwards. `pp_save_read(_from)` creates a 65536 byte buffer and starts
an async load of the main name. No existence test first.

- Good transfer and a document that validates: state ready, `present` true, and one log line,
  `PP: save read and accepted, music <cue>`. The line exists because silence cannot tell an accepted read
  from a read that never happened.
- Bad transfer or a document that fails validation: the backup is tried exactly once
  (`pp_save_read_backup`), with state retrying. On a good backup the state is ready, the note is
  `the save was damaged, so the backup was loaded`, and `present` stays false. That last part is load
  bearing: the next write must not rotate a damaged main file over the backup that just proved itself.
- Neither file can be loaded: state absent, no error text, and the title shows no save line at all. A
  player who has never saved is not told anything is wrong.
- A main file that is absent and a backup that fails validation: state failed with a plain sentence, and
  the boot card waits for a key.

What the backup is worth: it is the previous good save, not a copy of whatever is on disk. It is written
only when this session holds the main file as good, so a corrupt file is never promoted into it. The cost
of that choice is written down in `tests/test_save.py`: when the backup write cannot start, the new file
is written anyway, so the good file can be overwritten with no backup. The test names it as a defect on
record rather than hiding it. The alternative, refusing the save because a backup failed, was judged the
worse failure for a player.

## 7. The summary split, which does not exist yet

FOX-STYLE section 6 asks for a versioned payload plus a small summary, and for `summary(slot)` and
`exists(slot)` beside `write(slot)` and `read(slot)`. The summary is JSON with only what a slot list
needs: name, progress, the route counters, play time, the room name and the version. Its purpose is that
a list of slots renders from small files, without decoding and validating a whole payload per slot, and
that a slot is only claimed once its payload is verified.

What the code has instead. There is no summary file, no `pp_save_summary`, and no `pp_save_exists`. The
title asks the slot when it appears (`pp_save_title_start`, from the boot card and from `pp_title.gml`),
which is a full 64 KB asynchronous read plus `pp_save_parse` and `pp_save_validate`, and only then does
`pp_save_status_line` build `Continue: <map name>, <M:SS>` from the decoded document. The status line is a
view of the payload, not a small file beside it.

What that costs today: nothing a player would notice. One slot, one read at boot, one line on the title,
and the boot card simply reads `checking the save` while it happens.

What it would cost at three slots: three 64 KB reads, each followed by a full validation that resolves
every power, item, flag, seen scene and music id against `data/`, before the first line of the list can
be drawn. Serialised through `pp_save_busy` that is three round trips to disk; parallel it is three
buffers of 65536 bytes held at once. The summary split is what turns that into three small reads.

Two qualifications worth keeping straight:

1. `specs/11-save.md` puts several slots out of scope, along with thumbnails and cloud sync, so the code
   conforms to the spec and diverges from the doctrine's general architecture. With one slot there is no
   list for a summary to serve, which is why this is a gap and not a defect.
2. The doctrine's other demand, that the summary never claims a slot before the payload is verified, is
   already satisfied by other means: the title line only draws when `pp_save_ready()` is true, which
   requires state ready and a decoded document, and `present` only becomes true after a good read or a
   good write. What is missing is the small file, not the discipline.

If the node is asked for a slot list, the shape that follows from section 6 is: write
`pp_save_01.json.summary` in the same rotation that writes the payload, after the payload reports a good
status, carrying name, progress, the four counters, play seconds, room display name and the format
number; `exists(slot)` reads only that file's header; the list renders from summaries and the full read
happens on the one slot the player picks. That is a spec line in `specs/11-save.md` first, because the
doctrine says an unstated pattern gets written into the doctrine or the spec before it gets built.

## 8. What the ledger records about a route

The ledger is `game/scripts/pp_ledger/pp_ledger.gml`, and the save carries exactly three of its parts.

The four counters: `bosses_killed`, `bosses_spared`, `regulars_killed`, `regulars_spared`, each 0 to 9999.
They are cumulative for the run and they are the only coarse record. One door writes them,
`pp_ledger_record_exit`, which writes the row, recomputes the verdict and moves the counter in that order
and in that one call, so a row and a counter cannot disagree.

The flags: a table of name to true, from scenes, triggers, dialogue choices and fight outcomes. Only the
true ones are written. A load turns each written name into a true flag and leaves the rest absent.

The last fight's exit rows: one row per enemy, `{id, exit, round}`, where exit is `down`, `spared` or
`turned` (0, 1, 2 as `PPExit`), at most 32 rows, round 0 to 9999. They are cleared when the next fight
starts (`pp_ledger_begin_fight`), so what a save keeps is the fight the player just walked out of. A
`turned` enemy keeps its row and moves no counter, which is why the rows and the counters are read
together rather than one standing in for the other.

Not recorded, by design: the fight verdict and the route name. Both are functions of what is recorded.

- The verdict, `pp_ledger_verdict_of`: no row is down, `quiet`; at least one down and at least one not,
  `mixed`; every row down, `violent`. It is recomputed from the rows on every change and again on load.
- The route, `pp_ledger_route`: `genocide` if `bosses_killed` is above 0; else `blooded` if
  `regulars_killed` is above 0; else `mercy` if the story stage has reached `prison_stage`, which comes
  from `data/project.json`; else `undecided`.

One consequence a designer must know: the story stage is not in the save. `pp_save_apply` builds a fresh
ledger, so the stage is 0 after a load and the mercy route reads `undecided` until something advances the
stage again. The counters, flags and exit rows all come back correctly, so a run that already killed
stays `blooded` or `genocide`; a clean run that had reached the prison does not stay `mercy`. `DEVLOG.md`
records the reasoning on 2026-10-20: the stage was not advancing yet, so writing it would have added a
recorded fact nobody had asked for, and it becomes a spec change the day the prison scenes start setting
it. That day is now the open question in section 11.

## 9. Numbers, in one place

From `game/scripts/pp_config/pp_config.gml` unless marked otherwise.

| constant | value | what it does |
| --- | --- | --- |
| `PP_SAVE_FORMAT` | 1 | checked before any other key |
| `PP_SAVE_GAME_VERSION` | `0.1.0-slice` | written, never compared on load |
| `PP_SAVE_SLOT` | `pp_save_01.json` | the main file |
| `PP_SAVE_BACKUP` | `pp_save_01.json.bak` | the previous good save |
| `PP_SAVE_BUFFER` | 65536 | bytes per buffer; payload ceiling 65531 |
| `PP_SAVE_PANEL_STEPS` | 20 | `Saving` holds at least this long, 0.33 s at 60 steps |
| `PP_SAVE_ERROR_STEPS` | 150 | an error sentence holds up to this long, 2.5 s |
| `PP_SAVE_MAX_COUNTER` | 9999 | per counter |
| `PP_SAVE_MAX_PLAY_SECONDS` | 360000 | 100 hours, shown as `6000:00` |
| `PP_SAVE_MAX_HP` | 999 | ceiling for `max_hp` |
| `PP_SAVE_MAX_ITEM_COUNT` | 99 | per item row |
| `PP_SAVE_MAX_FLAG_CHARS` | 64 | flag name length; spec 10 says 32, see section 11 |
| `PP_SAVE_MAX_EXIT_ROWS` | 32 | rows in the last fight |
| `PP_SAVE_MAX_ROUND` | 9999 | round on an exit row |
| `PP_STEPS_PER_SECOND` | 60 | the one conversion for play time |
| `PP_TRIGGER_LOCK_STEPS` | 20 | steps after a trigger fires before confirm can fire another |
| `PP_FADE_STEPS` | 12 | fade length; the autosave waits for the fade to finish |
| `PP_FRAME_W`, `PP_FRAME_H` | 256, 240 | the panel box is 48,92 to 207,148 inside it |

Play time counts only overworld and battle steps (`pp_app.gml` lines 222 to 225); the title, the menu and
the cutscene mode do not count. Spec 11's numbers line says overworld, cutscene and battle, and the
cutscene mode is real: `game/scripts/pp_drive/pp_drive.gml` enters it for the drive. So the clock is short
by the length of every cutscene, which is a divergence with a player visible effect (section 11, item 9).
The clock text is `M:SS` with seconds zero padded; seconds are floored from ticks divided by 60.

The boot card starts a new run on its own after 60 steps with no input (`pp_app.gml` line 308); that
number is written at the call site, not in `pp_config`.

## 10. What already matches FOX-STYLE section 6

1. A versioned payload. `format` is the first key examined and an unknown number is refused with a
   sentence naming both numbers (`pp_save_validate`). `game_version` rides along.
2. Backup first, from a named constant, not from a guessed name. `pp_save_name_backup` and
   `PP_SAVE_BACKUP`; the rotation states sit before the writing state, and
   `tests/test_save.py::test_the_backup_is_written_before_the_real_file_is_replaced` pins the order.
3. Gated on no live operation. `pp_save_busy` over five states, `request` negative when idle, refusal on a
   negative id rather than on zero, and an event guard that matches the id. This is the doctrine's
   `op_id` with a different name.
4. Nothing applied from a half read file. `pp_save_apply` begins with `pp_save_ready()`, and every field
   is validated before the first one is used, so a refused file leaves the run exactly as it was.
5. The payload length verified. A 4 byte count is written and compared with the text length on read.
6. One module owns the domain. `pp_save.gml` owns the slot, the state, the buffers and the panel;
   `Other_72.gml` is one line handing the event over; `pp_overworld.gml` and `pp_app.gml` call the door
   rather than writing a file.
7. Timing authored in frames, converted once. 20 and 150 are steps in `pp_config`; play time crosses to
   seconds in one place through `PP_STEPS_PER_SECOND`.
8. Durability explicit by name. What survives a room change is the named key list, and the validator
   refuses a field it does not know, so nothing durable can hide in a shared flag index.

## 11. Where it diverges, and what to do about it

1. No summary and no `exists(slot)`. Section 6's split is absent, and the title decodes the payload to
   draw one line. Not a player facing defect today (one slot), and the first thing to build when a slot
   list is asked for. Conforms to `specs/11-save.md`, diverges from section 6.
2. No slot parameter. `pp_save_write(_purpose, _silent)` and `pp_save_read(_from)` take a label and a
   source, and the two names are macros, so the module is one slot by construction. Section 6's
   `write(slot)` and `read(slot)` would each need the name pair to travel with the call.
3. Field names differ from the doctrine's prose. Section 6 lists `version`, `story`, `route`, `party`,
   `money`, `room`, `entrance`, `audio`, `started_at`; the code has `format`, `game_version`, `map`,
   `spawn`, `hp`, `powers`, `items`, `flags`, `counters`, `music`, `saved_at`. `money` does not exist as a
   system at all, and `story` and `route` are deliberately not stored. Per the authority order in
   FOX-STYLE, the spec owns the numbers and the player experience here, so this is a doctrine wording gap
   to reconcile rather than code to rewrite.
4. `op_id` is called `request`.
5. A backup that cannot start does not stop the save. `pp_save.gml`, the `backing` case: when the backup
   write cannot be started the main write runs anyway. `tests/test_save.py` records it as a known defect,
   "the good file can be overwritten with no backup".
6. No chime on a save. Spec 11 acceptance 5 asks for the chime once; `data/audio.json` carries a `chime`
   cue, and neither `pp_save.gml` nor the `save` case in `pp_overworld.gml` plays any sound. The panel and
   the log line exist; the cue is unwired.
7. Flag name length disagrees with spec 10: the spec says up to 32 characters, `PP_SAVE_MAX_FLAG_CHARS`
   allows 64, so a 40 character flag passes the validator and breaks the spec. One of the two numbers
   should move.
8. The ledger stage is not durable, so a mercy run reads `undecided` after a load (section 8). This is
   consistent with spec 10's list of what is saved and with the 2026-10-20 note, and it will be wrong the
   day the prison scenes advance the stage. The fix is one key in the payload and one line in
   `pp_save_apply`, but it is a spec change first.
9. The play clock skips cutscene time. Spec 11 says play time counts overworld, cutscene and battle steps;
   `pp_app.gml` lines 222 to 225 count overworld and battle only, while `PPMode.cutscene` is entered by
   `game/scripts/pp_drive/pp_drive.gml`. A run that watches the drive under-reports its own length. The
   fix is one mode test in `pp_app.gml` and a spec sentence agreeing which modes count.

## 12. Measured, and not measured

Measured in a real run, 2026-10-23 03:43:34 (card t_673fba81, `output/save_capture_verify.json`): a save
written at the ship's log terminal, the digest of the file unchanged between the two launches, the title
reading the slot at boot, CONTINUE landing on the saved tile, and the panel visibly on screen at t=4.90 s
with 0.9887 of its box changed. `build/save_capture_run1.log` line 53 shows the silent autosave line, and
`build/save_capture_run2.log` has no autosave line after a load.

Unmeasured, and named rather than guessed:

- how long the write itself takes on this PC; the panel's 20 steps are a floor, not a measurement of the
  disk;
- how a document larger than 64 KB behaves in a run, since the refusal is a code path with no run behind
  it;
- the backup load path in a run: no capture walks it, and no test drives the `retrying` state, so
  `pp_save_read_backup` and its note are proven by reading the module only, not by a run or a test;
- the failure sentences at 150 steps, which no capture has held on screen;
- three or more slots, which do not exist, and therefore the cost the summary split would save.
