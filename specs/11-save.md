# Spec 11: save system

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: one save slot, versioned JSON, written without freezing the game, safe when the file is damaged, and the title
shows a plain line saying where the player is.

File: `pp_save_01.json` in GameMaker's save folder, written by json_stringify into a 64 KB buffer and saved with
buffer_save_async. The Save/Load asynchronous event reports `id` and `status` through async_load, per
https://manual.gamemaker.io/monthly/en/The_Asset_Editors/Object_Properties/Async_Events/Save_Load.htm (checked
2026-10-19). Both the write and the read keep the frame alive (spec 01).

Keys: `format` (1), `game_version`, `saved_at`, `play_seconds`, `map`, `spawn`, `x`, `y`, `hp`, `max_hp`, `powers`,
`items` (id and count), `flags`, `counters` (the four from spec 10), `seen_scenes`, `music`. Ids are names, never
indexes: json_stringify only stores a handle for an asset and that handle changes between runs, per
https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/File_Handling/Encoding_And_Hashing/json_stringify.htm
(checked 2026-10-19).

Optional keys: `fight_exits` (the last fight's exit rows from spec 10, each with an enemy id, the exit state and the
round it left on). A save written before this key existed does not carry it, so its absence means an empty record and a
quiet verdict, never a damaged file; when it is present it is checked as strictly as every other record. The fight
verdict itself is not a key: it is a function of these rows and is recomputed on load.

Rules
1. `format` is checked first; an unknown format is refused with a plain message, never guessed at.
2. The current file is copied to `.bak` before a write. A failed write leaves the old file in place.
3. Loading validates format, every id against the data set and every number in range. A failed validation is reported,
   then the `.bak` is tried once.
4. Only the save panel and autosave write. Autosave fires on entering a new map, after the fade in, never in battle.
5. Loading restores position, health, powers, items, flags, counters, seen scenes, the last fight's exit rows and music,
   and always lands in the overworld at the save point, so a save taken mid scene cannot resume mid scene. A file with
   no optional key still loads, and the missing record starts empty.
6. json_parse throws on invalid JSON (https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/File_Handling/Encoding_And_Hashing/json_parse.htm,
   checked 2026-10-19), so every read sits in a try/catch that prints the file name and a plain sentence.
7. No obfuscation and no anti tamper: a single player story game, so an edited save is not a threat.

Numbers: 64 KB buffer, a larger save is a clear error not a silent truncation; the "Saving" panel shows at least 20
steps even if the async returns sooner; play time counts only overworld, cutscene and battle steps, never paused time.

PP content: the demo has route branches, so a player who reaches the prison must be able to come back and see the other
version, which means the save must carry the route counters and flags.

Acceptance (Nayil)
1. Save, quit, relaunch, Continue: position, health, powers and flags are as left.
2. Save, kill the map, load: counters return to their saved values.
3. Delete one brace in the file: the game says the save is unreadable, offers New Game, and the `.bak` still loads.
4. Save before a boss, load: the boss is present and has not already been defeated.
5. The "Saving" panel appears, the game does not freeze, the chime plays once.

Out of scope: several slots, cloud sync, encryption, slot thumbnails.
