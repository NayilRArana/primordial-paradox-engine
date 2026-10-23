# Node 05: audio routing, music and sound effects

Node 05 of knowledge/GAMING-NODES.md, whose FOX-STYLE parent is section 9, the audio section, knowledge/FOX-STYLE.md.
Written 2026-10-23 from four files read in full: game/scripts/pp_audio/pp_audio.gml, data/audio.json, game/datafiles/sfx/sfx.json, specs/12-audio.md.
Runtime evidence is quoted from build/last-igor.log, the last Igor build's own console, build/last-igor.log.
Every number below is copied from one of those files; anything this read could not see is marked unmeasured.

## 1. What the player hears

One title theme streams on the title screen, loops, and drops 6 dB under the intro's text crawl before coming back, game/scripts/pp_title/pp_title.gml.
No other music is started by this build: the only call site of pp_audio_music in the whole game is the scene command, game/scripts/pp_scene/pp_scene.gml.
Effects are short 2A03 WAV rows played from a manifest, 21 of them, the longest 1.45 s, game/datafiles/sfx/sfx.json.
Text blips are the same effect path at priority 4 and 0.45 gain, one every three revealed characters, game/scripts/pp_text/pp_text.gml.
Losing window focus pauses music and stops effects; regaining focus resumes the music where it stopped, game/scripts/pp_audio/pp_audio.gml.

## 2. The cue table

Two tables sit behind one module, and both are data, game/scripts/pp_audio/pp_audio.gml.
The effect table is game/datafiles/sfx/sfx.json, written by tools/sync_art.py with the data chunk offset and byte length measured from each WAV, tools/sync_art.py.
The music table is data/audio.json, keyed by the musician's own ids PP-01 to PP-16, data/audio.json.

### 2.1 Effects: 21 rows ship, 23 names can be asked for

The module accepts 23 effect/style names in pp_audio_cues(), 23 names in one array, game/scripts/pp_audio/pp_audio.gml.
Twenty-one of those names have a row in the manifest; the other two are title_theme (routed to the stream player instead) and car_engine_loop (no row at all), game/scripts/pp_audio/pp_audio.gml.
car_engine_loop is asked for on the title screen and is silent in the build, which the log states in plain words, game/scripts/pp_title/pp_title.gml and build/last-igor.log.

| cue | file | seconds | asked for in game code |
| --- | --- | --- | --- |
| menu_move | menu_move.wav | 0.06 | pp_battle_director.gml:537, pp_title.gml:326 |
| text_blip_a | text_blip_a.wav | 0.06 | pp_text.gml:156 via pp_audio_blip |
| text_blip_b | text_blip_b.wav | 0.06 | pp_text.gml:156 via pp_audio_blip |
| text_blip_c | text_blip_c.wav | 0.06 | pp_text.gml:156 via pp_audio_blip |
| footstep | footstep.wav | 0.09 | pp_overworld.gml:124 |
| hit_light | hit_light.wav | 0.12 | no call site today |
| menu_select | menu_select.wav | 0.16 | pp_title.gml:316, pp_battle_director.gml:561 |
| menu_cancel | menu_cancel.wav | 0.18 | pp_app.gml:298, pp_battle_director.gml:527 |
| miss | miss.wav | 0.20 | no call site today |
| door_hatch | door_hatch.wav | 0.30 | pp_overworld.gml:150, pp_overworld.gml:266 |
| item_get | item_get.wav | 0.32 | no call site today |
| hit_heavy | hit_heavy.wav | 0.34 | no call site today |
| crit | crit.wav | 0.42 | no call site today |
| heal | heal.wav | 0.52 | no call site today |
| alarm | alarm.wav | 0.64 | no call site today |
| encounter_swoosh | encounter_swoosh.wav | 0.70 | pp_app.gml:370 |
| wave_wash | wave_wash.wav | 1.10 | no call site today |
| level_up | level_up.wav | 1.20 | no call site today |
| game_over | game_over.wav | 1.40 | no call site today |
| save_jingle | save_jingle.wav | 1.40 | no call site today |
| thunder_soft | thunder_soft.wav | 1.45 | pp_title.gml:361 |

Every row above is from game/datafiles/sfx/sfx.json, and every call site was read in game/scripts/.
Eleven of the 21 rows are shipped and named but nothing in the game asks for them yet, game/scripts/pp_audio/pp_audio.gml.
The one effect entry a scene can reach directly is the sfx command, and data/scenes/all.json carries no sfx command today, game/scripts/pp_scene/pp_scene.gml.

### 2.2 Music: 17 cues registered, six delivered

Six cues have an OGG on disk under assets/audio/<asset>/<asset>.ogg, and those same six are mirrored into the build as game/datafiles/streams, data/audio.json.
The other eleven are pending, each with a fallback that points at a delivered cue, so every chain ends at a file, data/audio.json.

| cue | title | asset | priority | state |
| --- | --- | --- | --- | --- |
| PP-01 | Title Theme | pp_01_title | 10 | delivered |
| PP-02 | The Drive | pp_drive_v2 | 10 | delivered |
| PP-03 | Harbor | pp_03_harbor | 10 | delivered |
| PP-04 | Navy Sailors | pp_04_navy_sailors | 10 | delivered |
| PP-05 | Small Ship | pp_05_small_ship | 10 | delivered |
| PP-06 | Percy, Tyrant of the Harbor | percy_theme | 12 (boss) | delivered |
| PP-07 | Prometheus Explains | pp_07_prometheus_explains | 10 | pending, fallback PP-05 |
| PP-08 | Dead Rising | pp_08_dead_rising | 10 | pending, fallback PP-03 |
| PP-09 | The Data Center | pp_09_data_center | 10 | pending, fallback PP-03 |
| PP-10 | Hector, Warden of the Dead | pp_10_hector | 12 (boss) | pending, fallback PP-06 |
| PP-11 | Rush to Prison | pp_11_rush_to_prison | 10 | pending, fallback PP-02 |
| PP-12 | One North Quay | pp_12_one_north_quay | 10 | pending, fallback PP-03 |
| PP-13 | Titan Employees | pp_13_titan_employees | 10 | pending, fallback PP-03 |
| PP-14 | Kronos | pp_14_kronos | 12 (boss) | pending, fallback PP-06 |
| PP-15a | Entropy | pp_15a_entropy | 10 | pending, fallback PP-01 |
| PP-15b | Mercy | pp_15b_mercy | 10 | pending, fallback PP-01 |
| PP-16 | Ouranos | pp_16_ouranos | 10 | pending, fallback PP-01 |

Rows, ids, assets and fallbacks are from data/audio.json; the priority 12 rule is the boss flag read at game/scripts/pp_audio/pp_audio.gml.
Who asks for a music cue today: three rooms ask PP-05 and two ask PP-03, and data/scenes/all.json asks PP-05 and PP-07, data/maps/all.json and data/scenes/all.json.
Two encounters ask PP-04 and one asks PP-06 in their own rows, but the battle entry path reads the encounter and never starts that music, game/scripts/pp_app/pp_app.gml.
That gap is spec 12 rule 7, the encounter sting then the battle theme crossfading in, and only the sting half is wired, specs/12-audio.md.

### 2.3 The four numbers that govern every cue

Priorities are music 10, boss music 12, effects 5, UI blips 4, and the channel count is 10, set once before the first cue, game/scripts/pp_audio/pp_audio.gml.
Gains are music 0.7, effects 0.9, and a blip is that 0.9 times 0.5, which is 0.45, game/scripts/pp_audio/pp_audio.gml.
The crossfade is 30 steps, and one step is 16.6667 ms, game/scripts/pp_audio/pp_audio.gml.
The effect instance list is capped at 8 entries so the pause rule's working set cannot grow without bound, game/scripts/pp_audio/pp_audio.gml.

## 3. How a theme stream is chosen and looped

The title theme is a separate path from the music cues, and it is the one music source the build actually plays today, game/scripts/pp_audio/pp_audio.gml.
It tries four files in order and plays the first that exists: streams/title_theme_v3_126.ogg, then streams/title_theme_v3.ogg, then streams/title_theme_v2.ogg, then streams/title_theme.ogg, game/scripts/pp_audio/pp_audio.gml.
It opens the file with audio_create_stream, plays it at priority 10, looped, starting at the music gain of 0.7, game/scripts/pp_audio/pp_audio.gml.
The build log confirms the first candidate wins, gain 0.70, instance 400001, build/last-igor.log.

A music cue by id goes through pp_audio_music and a different chain, game/scripts/pp_audio/pp_audio.gml.
The cue id is looked up in data/audio.json; an unregistered id logs and plays nothing, game/scripts/pp_audio/pp_audio.gml.
Asking for the cue that is already playing returns true without restarting it, so a room trigger on every step cannot stutter, game/scripts/pp_audio/pp_audio.gml.
The OGG is looked for at working_directory/music/<asset>.ogg, then working_directory/datafiles/music/<asset>.ogg, game/scripts/pp_audio/pp_audio.gml.
Neither path can resolve on this checkout: no directory named music exists anywhere in the project, and the mirror tool writes only streams and sfx, tools/sync_art.py.
The six delivered OGGs are mirrored to game/datafiles/streams/<asset>.ogg, where the music path does not look, data/audio.json and game/datafiles/streams.
So a cue asked for by id today takes the "no OGG yet" branch, counts one silent request, and returns false, game/scripts/pp_audio/pp_audio.gml.
The cue id is still recorded as the current cue in that branch, which is what the log and the tests read, game/scripts/pp_audio/pp_audio.gml.

Looping is one flag, not a loop point pair, game/scripts/pp_audio/pp_audio.gml.
Every music row in data/audio.json carries loop true, and the module passes that flag to audio_play_sound, so the engine repeats the whole stream, data/audio.json.
Spec 12 rule 3 asks for the OGG's own loop metadata to own the loop, and no GML file reads the sidecar loop JSON that the music lane writes beside each render, specs/12-audio.md.
The 126 render's sidecar says the loop is the whole form: 52 bars, loop_start_sample 0, loop_end_sample 3275997, seam sample difference 0, assets/audio/title_theme_v3/title_theme_v3_126_loop.json.
Those sidecar numbers are documentation for a human today, not a value the game reads, unmeasured.

Crossfade behaviour, in the order the code does it, game/scripts/pp_audio/pp_audio.gml.
A request with fewer than 1 step is raised to 30 steps, game/scripts/pp_audio/pp_audio.gml.
A live title theme is handed to the fade slot first, so there is never a second music source, game/scripts/pp_audio/pp_audio.gml.
The incoming stream starts at gain 0 and rises to 0.7 over the fade; the outgoing one falls to 0 over the same fade, game/scripts/pp_audio/pp_audio.gml.
The step function stops the outgoing instance once the fade's end time has passed, and destroys the stream with it, game/scripts/pp_audio/pp_audio.gml.
Stopping music is the same fade, never a cut, and it silences a live theme too, game/scripts/pp_audio/pp_audio.gml.
The theme candidate list stops at the 126 render even though the build also ships v4_medium, v4_spicy, v4_subtle and v5, game/datafiles/streams.

## 4. Ducking during dialogue

There is no duck during dialogue today, game/scripts/pp_audio/pp_audio.gml.
The only caller of pp_audio_duck_db in the project is the title screen's text crawl, at 6 dB, game/scripts/pp_title/pp_title.gml.
6 dB below the music level is a gain of 0.3508, which is 0.7 times 10 to the power of minus 6 over 20, game/scripts/pp_audio/pp_audio.gml.
The duck is instant, a gain call with a time of 0, and the unduck is instant too, so there is no ramp either way, game/scripts/pp_audio/pp_audio.gml.
The duck only addresses the theme's instance; if a music cue were playing there would be no instance to turn down, and the call returns false after recording the level, game/scripts/pp_audio/pp_audio.gml.
The duck level is stored on the bus even with no stream in the build, so a log line or a test can see the request, game/scripts/pp_audio/pp_audio.gml.
Unduck puts the theme back to exactly the music level, not to a remembered previous gain, game/scripts/pp_audio/pp_audio.gml.

What a designer should assume: a dialogue scene does not lower the music, game/scripts/pp_text/pp_text.gml.
If a scene needs the music out of the way of a long speech, the tools today are the scene's music command with a stop, or writing the duck into the dialogue path, which nothing does, game/scripts/pp_scene/pp_scene.gml.
Ducking music cues (not only the theme) needs one code change in pp_audio_duck_db, game/scripts/pp_audio/pp_audio.gml.

## 5. Frame to millisecond conversion for fades

GameMaker's gain fade takes milliseconds, and the game authors fades in steps, game/scripts/pp_audio/pp_audio.gml.
The one constant is 16.6667 ms per step, which is 1000 divided by 60, game/scripts/pp_audio/pp_audio.gml.
30 steps at that constant is 500.001 ms, terminal arithmetic on the macro value, and the manual call is audio_sound_gain(instance, gain, milliseconds).
The conversion is written inline twice, once in pp_audio_music and once in pp_audio_music_stop, and there is no pp_audio_frames_to_ms function, game/scripts/pp_audio/pp_audio.gml.
The fade's end is compared against current_time, which is a wall clock in milliseconds, so a hitch does not stretch the fade, game/scripts/pp_audio/pp_audio.gml.
The 60 in the constant matches the 60 fps the title's animation timing assumes, data/title_timing.json.
If the game ever runs at a different room speed, 16.6667 is wrong and every fade is wrong by the same ratio, unmeasured.

## 6. The blip cue

The blip is a UI sound at priority 4, gain 0.45, from one of three 0.06 s files, game/scripts/pp_audio/pp_audio.gml.
The table is four speakers and a default: sailor gets text_blip_b, percy gets text_blip_c, prometheus gets text_blip_b, narrator gets text_blip_a, and every other name also gets text_blip_a, game/scripts/pp_audio/pp_audio.gml.
So the sailor and Prometheus share text_blip_b, Percy is the only text_blip_c voice, and the narrator doubles as the unknown fallback, game/scripts/pp_audio/pp_audio.gml.
The interval is 3 revealed characters, and a space never blips, game/scripts/pp_config/pp_config.gml and game/scripts/pp_text/pp_text.gml.
The interval lives on the reveal state, so a layout timed against the music can set its own, and it is still the same blip call, game/scripts/pp_text/pp_text.gml.
The gain is lowered on the instance in the same step it is played, so nothing is heard at the full effect level first, game/scripts/pp_audio/pp_audio.gml.
Speed affects the blip rate only through the reveal rate: 2 steps a character normally, 1 while confirm is held, game/scripts/pp_config/pp_config.gml.
A fast forward therefore blips every third character faster, which is the spec's own acceptance case, specs/12-audio.md.
Whether that reads as a buzz rather than speech is unmeasured here; no listening was done for this note.

## 7. The tempo move, 108 to 126, and the old value

The title theme is a 126 bpm waltz now, 52 bars of 3/4, and the title's animation is locked to that tempo, data/title_timing.json.
126 bpm at 60 steps a second is 28.571 steps a beat and 85.714 a bar; the counters run on 29 and 87 so a bar is exactly three beats, data/title_timing.json.
The 126 render's own loop file agrees: 126.0001 bpm, 74.285646 s per loop, assets/audio/title_theme_v3/title_theme_v3_126_loop.json.
The build plays that render, by name, at gain 0.70, build/last-igor.log.

Two tests assert the new value, and both are green by construction: tests/test_arrange_v3.py asserts 126 bpm and 74.286 s, tests/test_title_timing.py asserts 126 and the 60 fps lattice, tests/test_arrange_v3.py and tests/test_title_timing.py.
The claim that a test still asserts 108 is itself stale: it survives only as prose in the spice note, which says "the v3 arrange tests that still expect 108 bpm", assets/audio/title_theme_v3/spice/SPICE.md.
A search of every .py file in the project for a bare 108 returns no hits, so no test file holds that assertion today, whole-tree search for the pattern, this session.
The old value survives as committed data, not as an assertion: the pre-126 arrange report says bpm 108.0, midi_bpm 108.0, tempo 555556 us per quarter, assets/audio/title_theme_v3/arrange_report.json.
The pre-126 loop sidecar says 107.9999 bpm, beside the 108 render's MIDI, assets/audio/title_theme_v3/title_theme_v3_loop.json.
The prose in that folder still says 108 in two places, the folder note's summary line and its MIDI line, assets/audio/title_theme_v3/NOTES.md.
The only test pin that touches the old render at all is a file-name pin, which requires datafiles/streams/title_theme_v3.ogg to stay an Included File, tests/test_build_inputs.py.
That pin would still pass with the 108 render as the shipped one, which is why it is worth naming next to the tempo question, tests/test_build_inputs.py.
The stale 108 values in the report and sidecar are the ones a reader will find first when they grep for the tempo, assets/audio/title_theme_v3/arrange_report.json.

## 8. Where the code conforms to FOX-STYLE

1. One owner: every sound is asked for through the pp_audio module and no call site names a file, game/scripts/pp_audio/pp_audio.gml.
2. Music outranks effects: 10 and 12 against 5 and 4, exactly as FOX-STYLE section 9 and spec 12 rule 1 and 2 say, game/scripts/pp_audio/pp_audio.gml.
3. Volume is applied at the entry point, not at each caller, and the saved-setting shape is a gain on the bus, game/scripts/pp_audio/pp_audio.gml.
4. Streamed audio dies with its owner: every path that hands an instance away either destroys the stream or passes it to the step that destroys it, game/scripts/pp_audio/pp_audio.gml.
5. A missing file is a logged silence, never a crash and never a guess: manifest missing, OGG missing, stream create failed, no channel, all four say so, game/scripts/pp_audio/pp_audio.gml.
6. Cue ids are validated at check time: the id shape, uniqueness, the asset name, the loop flag and the four slice cues are enforced by the checker, tools/check_data.py.
7. One music source at a time, theme included, which is the fix the tests pin, game/scripts/pp_audio/pp_audio.gml and tests/test_audio.py.
8. One blip path: the text writer calls pp_audio_blip, and no second implementation of the blip gain exists, tests/test_audio.py.

## 9. Where it diverges from FOX-STYLE

1. The music path and the delivery path disagree, and this is the biggest one: the bus looks in music/, the six delivered OGGs are in streams/, so no music cue can play, game/scripts/pp_audio/pp_audio.gml and game/datafiles/streams.
2. A cue name in the code table has no manifest row: car_engine_loop is in pp_audio_cues() and absent from sfx.json, so the title asks for it and the log answers "silent", game/scripts/pp_audio/pp_audio.gml and build/last-igor.log.
3. Law 6 wants one conversion function per domain; the frame-to-millisecond multiply is written inline in two places instead, game/scripts/pp_audio/pp_audio.gml.
4. Ducking is theme-only and dialogue never ducks at all, which leaves the speech-over-music case with no answer, game/scripts/pp_audio/pp_audio.gml and game/scripts/pp_text/pp_text.gml.
5. The fallback field the data promises is never read by the bus, so eleven pending cues stay silent rather than falling back, data/audio.json and game/scripts/pp_audio/pp_audio.gml.
6. The stand-in path is dead: pp_audio_music hands placeholder_sound to pp_audio_play, which refuses any name not in pp_audio_cues(), and none of the three stand-ins is in that list, game/scripts/pp_audio/pp_audio.gml.
7. Two effect entry points with different guards: pp_audio_play checks the code list, pp_audio_sfx checks only the manifest, and the scene's sfx command uses the looser one, game/scripts/pp_audio/pp_audio.gml and game/scripts/pp_scene/pp_scene.gml.
8. Loop points are left to the engine's whole-file loop while the spec says the OGG's metadata owns them, and nothing reads the sidecar, specs/12-audio.md and assets/audio/title_theme_v3/title_theme_v3_126_loop.json.
9. The data still says placeholder true on all seventeen rows while six are delivered, which the data file itself admits in a note, data/audio.json.
10. Three rendered blip files stand in for one pitched sound, where FOX-STYLE section 9 asks for pitch reuse before a second rendered track, game/scripts/pp_audio/pp_audio.gml.
11. The theme candidate list is frozen at the 126 render while four newer renders ship in the build, game/scripts/pp_audio/pp_audio.gml and game/datafiles/streams.

## 10. What a designer may change, and what needs the audio owner

Safe to change alone: which cue a map, an encounter or a scene names, from the ids in data/audio.json, data/audio.json.
Safe to change alone: the blip speaker table, if a new speaker should sound like a sailor or like Percy, game/scripts/pp_audio/pp_audio.gml.
Needs the audio owner first: anything that adds a cue name, because the name must exist in pp_audio_cues() and in the manifest, game/scripts/pp_audio/pp_audio.gml.
Needs the audio owner first: the duck level and whether dialogue ducks, because the duck currently reaches only the theme, game/scripts/pp_audio/pp_audio.gml.
Needs the audio owner first: the crossfade length, because it is one macro read by three paths, game/scripts/pp_audio/pp_audio.gml.
Never do: edit data/audio.json's placeholder flags to claim a delivery that is not on disk, since tests pin them and the data note explains why, data/audio.json and tests/test_audio.py.
