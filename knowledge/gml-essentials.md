# GML essentials we actually need (Primordial Paradox)

Every fact below was read from the official GameMaker manual on 2026-10-19. Branch read: Monthly, base URL
https://manual.gamemaker.io/monthly/en/index.htm (checked 2026-10-19). The same pages exist under /lts/en/ for the
Long Term Support branch; when Nayil installs GameMaker we pin this file to whichever branch he installed.

Rule for this file: a fact only enters here with its manual link and the date it was checked. If a fact is our own
decision (a number we chose), it says DECISION instead of a link.

## 1. Objects, instances, events

Source: https://manual.gamemaker.io/monthly/en/The_Asset_Editors/Object_Properties/Object_Events.htm (checked 2026-10-19)

- An object holds events; an instance is one live copy in a room. Events are the moments in the game loop where the
  instance's code runs. A "step" is one frame, governed by the Game Frames Per Second setting, so a step and a frame
  are the same thing.
- A new object starts with an empty event list; events are added per object.
- The Step event is actually three sub events, Begin Step, Step and End Step. All instances run Begin Step first, then
  all Step, then all End Step. That relative order never varies.
- The Draw event is where an instance draws; without a Draw event the instance draws its sprite automatically.

Source: https://manual.gamemaker.io/monthly/en/The_Asset_Editors/Object_Properties/Event_Order.htm (checked 2026-10-19)

- The exact order of ALL events in a step cannot be stated and may change between versions and platforms. Only a
  subset is guaranteed.
- On entering a room, instances are created in the room's Instance Creation Order; for each instance the Object
  Variables (pre-creation code) are initialised, then the Create event runs, then that instance's Instance Creation
  Code runs.
- Draw events run, in this order: Pre-Draw, Draw Begin, Draw, Draw End, Post-Draw, Draw GUI Begin, Draw GUI, Draw GUI
  End. Within one draw event, instance order follows layer depth.
- Guaranteed ordering lever: put code that must run before other instances' Step code in Begin Step, and code that
  must run after it in End Step.

DECISION for PP: one persistent controller object runs the game state machine in Begin Step, so every other object
reads a settled state in its own Step. No gameplay logic depends on creation order.

## 2. Structs and constructors

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Overview/Structs.htm (checked 2026-10-19)

- A struct is a variable that holds a collection of variables (named fields). Fields can be read and written after
  declaration, and new fields can be added later with the dot operator.
- Structs can be created at local, instance or global scope, and can hold methods, arrays and runtime function results.
- A struct takes no processing overhead while it exists, though it occupies memory.
- The manual documents "Constructors & Structs vs. Objects & Instances" as a comparison; structs can hold static
  variables, object instances cannot.
- Struct field names follow normal variable naming: no leading digit, letters, digits and underscore only.

DECISION for PP: parsed JSON becomes structs and arrays and is passed around as data. No JSON-derived handle is ever
stored in an object variable of the same name as a built-in variable.

## 3. Methods and script functions

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Overview/Method_Variables.htm (checked 2026-10-19)

- A method variable is a variable that holds a function, binding that function to an instance or a struct, so the
  variable can be called like a built in function.
- This page documents the assignment form, `name = function(a, b) { ... };`, with examples at local, instance and
  global scope. The named declaration form, `function name(a, b) { ... }`, is the script function form; the related
  page below states that a script function and a method are not interchangeable in every context.
- Variable functions documented for methods: method, method_get_self, method_get_index, method_call.
- Related page: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Overview/Script_Functions_vs_Methods.htm
  (checked 2026-10-19), which states a script function and a method are not interchangeable in every context.

DECISION for PP: every state (title, overworld, cutscene, battle, menu) is a struct with step, draw and input
methods assigned at construction; the state machine only calls method_call on them. No state is a switch statement
spread over events.

## 4. Arrays, structs and data structures

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Data_Structures/Data_Structures.htm (checked 2026-10-19)

- Six data structure types exist: stacks, queues, lists, maps, priority queues and grids. Each is created, used
  through a reference, and must be destroyed.
- The manual states the recommendation directly: use arrays and structs over DS lists and maps, because they have
  similar functionality, are easier to use, and are garbage collected automatically.
- ds_exists checks whether a data structure reference is still valid.
- DS maps can hold nested lists and maps only for JSON purposes; the manual says nested structures are not read
  correctly when written to disk or accessed in any other way.

DECISION for PP: arrays and structs everywhere. No ds_list, no ds_map in our code. The one exception we may allow
later is the built in async_load map, which GameMaker fills for us (section 8).

## 5. Surfaces and the application surface

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Drawing/Surfaces/Surfaces.htm (checked 2026-10-19)

- In normal Draw events GameMaker does not draw to the screen directly. It draws to the application surface.
- Custom surfaces can be created and drawn to, then drawn elsewhere; a surface is a volatile resource, so the
  documented pattern is a guard: if (!surface_exists(surf)) { surf = surface_create(w, h); }.
- Documented application surface functions include application_surface_enable,
  application_surface_is_enabled, application_get_position, application_surface_draw_enable,
  application_surface_is_draw_enabled, plus the variable application_surface.

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Drawing/Surfaces/application_surface.htm (checked 2026-10-19)

- application_surface is a built-in global variable holding the surface the game is drawn to; it is permanently
  available.
- The regular Draw events (Draw Begin, Draw, Draw End) draw to it by default. Pre-Draw, Post-Draw and Draw GUI do NOT
  draw on it.
- The manual's own example resizes it, with its own local variable names:
  surface_resize(application_surface, _cam_width * _resolution_scale, _cam_height * _resolution_scale), which sets the
  game's output resolution from the camera size times an integer scale.

DECISION for PP: camera view is 256x240; application surface is resized to 256 * scale by 240 * scale with scale an
integer from 1 to 6; the window is sized to the same numbers. See specs/03-camera-and-scaling.md.

## 6. Cameras and viewports

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Cameras_And_Display/Cameras_And_Viewports/Cameras_And_View_Ports.htm (checked 2026-10-19)

- Up to 8 viewports, numbered 0 to 7, and an unlimited number of cameras, of which up to 8 can be active, one per
  viewport. Normally one viewport is enough.
- A camera defines the area of the room shown; a viewport is the area on screen where that view is drawn. Viewport
  size may differ from camera view size, which scales (and can distort) the view.
- Documented functions include view_set_camera, view_set_visible, view_set_xport, view_set_yport, view_set_wport,
  view_set_hport, view_set_surface_id, and the array view_camera[0..7].

DECISION for PP: exactly one viewport (0), camera view 256x240, viewport 256*scale by 240*scale. Cameras are never
created at runtime; the room's camera is reused and moved with camera_set_view_pos.

## 7. Tile maps

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Asset_Management/Rooms/Tile_Map_Layers/Tile_Map_Layers.htm (checked 2026-10-19)

- Three things: a tile set (the asset), a tile layer (created in the Room Editor, a layer type that exists only in
  the editor), and a tile map (the collection of tiles on a layer, one element).
- In the Room Editor a layer holds exactly one tile map; in code you can assign several tile maps to one layer.
- Each cell stores a tile data "blob": the tile index plus rotate, mirror and flip bits.
- 19 bits are reserved for the tile index; spare bits can carry a custom mask, which the manual documents for custom
  tile collisions. Reading and writing is tilemap_get / tilemap_set (cell) and tilemap_get_at_pixel /
  tilemap_set_at_pixel (pixel).
- Full function list on that page includes layer_tilemap_get_id, layer_tilemap_exists, layer_tilemap_create,
  tilemap_get_width, tilemap_get_height, tilemap_get_tile_width, tilemap_get_tile_height.

DECISION for PP: tiles are 16x16 for the overworld and 8x8 for the battle backdrop detail. Collision comes from a
separate JSON collision grid, not from tile bits, so Nayil can edit a map's walls without touching tile art.

## 8. Async save and load

Source: https://manual.gamemaker.io/monthly/en/The_Asset_Editors/Object_Properties/Async_Events/Save_Load.htm (checked 2026-10-19)

- The Save/Load asynchronous event is triggered by buffer_save_async and buffer_load_async when the transfer
  completes, and also by zip_unzip_async, zip_save and audio group load/unload.
- The event reads the built-in async_load map. For buffers it holds "id" (the value the save or load function
  returned) and "status" (true on success).
- For audio groups it holds "type" = "audiogroup_load" and "group_id".
- The documented poll pattern is: store the returned id, then in the event compare ds_map_find_value(async_load,
  "id") with it and check "status".

DECISION for PP: saves are written with buffer_save_async from a buffer holding a JSON string, and the Save/Load
event flips a small state machine (saving, saved, failed). The player never sees a frozen frame; the "Saving" label
is drawn while the async is in flight. See specs/11-save.md.

MEASURED on this runtime (runtime-2026.0.0.23, 2026-10-20, card t_b72efa81), all four found by running the game
and printing the values, not by reading the manual:

- The request id is **0 for the first async call in the process**, then 1, 2, 3. A test of `id <= 0` for "the
  transfer refused to start" therefore rejects a perfectly good first request, and a test of `id > 0` for "the
  transfer started" rejects it too. Compare the id against the one you stored, and treat a negative id (if it ever
  happens) as the failure case.
- A buffer handle is not a number. `typeof(buffer)` is `"ref"` and `is_real(buffer)` is **false**. A buffer id
  must not be tested with `is_real`, and must not be compared against a number with `<` or `>=`. Use `undefined` as
  the "no buffer" sentinel and `is_undefined` as the test.
- A number read from a buffer with `buffer_read(buffer, buffer_u32)` is an **int64**: `typeof` says `"int64"`,
  `is_real` is false, and `is_numeric` is true. `is_int` does not exist in this runtime. A number that came out of
  a file must be tested with `is_numeric`, never `is_real`.
- The save area is `<save area>\default\` for a relative name. `file_exists("pp_save_01.json")` is false while
  `file_exists("default/pp_save_01.json")` is true, and the async pair reads and writes the `default` folder. A
  relative name must not be checked with `file_exists` on the bare name, and the async pair's own status is the
  only trustworthy existence test.
- A buffer handed to `buffer_load_async` or `buffer_save_async` must not be deleted until the event has reported
  back. Deleting it while the transfer is in flight raises `Cannot delete buffer, it's in use by 1 others`. If a
  transfer is abandoned, drop the handle instead of freeing it.

## 9. JSON

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/File_Handling/Encoding_And_Hashing/json_parse.htm (checked 2026-10-19)

- json_parse turns a JSON string into nested arrays and structs (JSON object becomes struct, JSON array becomes
  array) and returns the top level value.
- Parsing an invalid value or invalid JSON throws an exception, so every call site must be wrapped.
- The maximum nesting limit is 128.
- null is parsed as undefined.

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/File_Handling/Encoding_And_Hashing/json_stringify.htm (checked 2026-10-19)

- json_stringify converts a struct or array hierarchy into a valid JSON string, with an optional prettify flag and an
  optional filter function.
- It does NOT serialise the contents of assets, data structures or other runtime assets; it stores the internal
  handle, which changes between runs. So no asset index and no DS handle may live in save data or content data.

DECISION for PP: all data files and save files are JSON parsed with json_parse inside a try/catch, then checked
field by field against our schema checker before use. Asset references in data are names (strings), never indexes.

## 10. Input

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Game_Input/Game_Input.htm (checked 2026-10-19)

- GameMaker offers dedicated mouse, keyboard and gesture events, but for gamepad support and multiple control
  schemes the manual points at the game input functions: keyboard, mouse, gamepad, touch and device input.
- keyboard_check_pressed returns true only in the step the key changes from not held to held, and needs a release
  before it can fire again: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Game_Input/Keyboard_Input/keyboard_check_pressed.htm
  (checked 2026-10-19). Key argument is a keycode from ord (capital letters A to Z, digits 0 to 9) or a vk_* constant.

DECISION for PP: one input module converts keyboard and gamepad state into named actions (confirm, cancel, up,
down, left, right, menu, debug) once per step in Begin Step, and nothing else reads raw keys. See specs/02-input.md.

## 11. Sound

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Asset_Management/Audio/audio_play_sound.htm (checked 2026-10-19)

- audio_play_sound(sound, priority, loop) plays a sound asset and returns a unique sound instance ID, which can be
  stored to stop or change that one playback later.
- Priority is compared against the limit set by audio_channel_num() when more sounds are playing than allowed;
  higher priority wins, the actual numeric range is arbitrary.
- An optional pitch multiplier is documented; values at or below zero are clipped to the lowest positive number.

DECISION for PP: music is priority 10 and looped, boss music priority 12, SFX priority 5, UI blips 4. Fades are done
with audio_sound_gain over 30 steps. See specs/12-audio.md.

## 12. Rooms

Source: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Asset_Management/Rooms/room_goto.htm (checked 2026-10-19)

- room_goto does not change the room until the end of the event that called it; code after the call in the same
  event still runs, and the Room End event triggers.
- New instances cannot be created in the same event after room_goto, unless the object is persistent.
- Room IDs are not the Asset Browser order; the manual says to use the room name constant, not a number.

DECISION for PP: room changes are requested by name string through one wrapper, which resolves the string to a room
asset in a lookup built at start, and only the wrapper calls room_goto. A room change also clears the input "pressed"
flags for one step so a held confirm cannot leak into the next room.

## 13. What this file does not cover yet

- Anything about the .yy and .yyp field schemas (the manual publishes the file roles, not the fields): see
  gamemaker-project-format.md.
- Anything that can only be measured in a running build: frame cost of the dodge arena, real audio latency, real
  async save timing on this PC. These are marked UNVERIFIED until GameMaker is installed and a build runs.

## 14. Verification pass, 2026-10-19

A second read of every page above was run the same day, before this file was called done, because a link that returns
200 proves nothing about the words next to it.

- All 21 manual links cited across knowledge\ and specs\ were requested again: 21 of 21 returned HTTP 200.
- The manual pages carry no "last updated" date, so the date recorded in each section is the date the page was read,
  not a page revision date. Re-reading is the only way to catch a change.
- Claims re-read in the page text, word for word, in this pass: json_parse (maximum nesting limit 128, null parsed as
  undefined, invalid JSON throws); Data Structures (six types, and the manual's own recommendation to use arrays and
  structs, which are garbage collected); Cameras And Viewports (8 viewports numbered 0 to 7, unlimited cameras, 8
  active at once, one is normally enough); Tile Map Elements (one tile map per layer in the Room Editor, multiple when
  assigned in code; index in bits 0 to 18, mirror 28, flip 29, rotate 30); audio_play_sound (priority any real number,
  higher wins; pitch at or below zero clipped to the lowest positive number); Event Order (Instance Creation Order);
  application_surface (Draw Begin, Draw and Draw End draw to it by default, Pre/Post Draw and Draw GUI do not; the
  manual's resize example uses _cam_width and _resolution_scale); room_goto (the room does not change until the end of
  the event, code after the call still runs, Room End triggers, a persistent object is the one creation exception).
- Two lines were corrected by this pass: the surface_resize example now quotes the manual's own variable names, and the
  method section no longer credits the named `function name()` declaration to the method variables page.
