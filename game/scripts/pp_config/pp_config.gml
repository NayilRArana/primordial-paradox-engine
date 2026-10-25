/// pp_config: the constants and enums every other module reads.
/// Written from specs\01, 03, 06, 07, 08, 10, 11, 13. No magic numbers live outside this file and data\.
/// Provenance: knowledge\PROVENANCE.md, entries "battle state machine and turn loop" and
/// "room and object conventions across a whole game".

#macro PP_DEBUG false

// Frame and time (spec 03, spec 01).
#macro PP_FRAME_W 256
#macro PP_FRAME_H 240
#macro PP_MAX_SCALE 6
#macro PP_STEPS_PER_SECOND 60
#macro PP_FADE_STEPS 12
#macro PP_INPUT_LOCK_STEPS 6

// Colour (spec 13). No draw call in the game carries a colour literal: a colour comes from the palette set a room
// declares, by role. These two are the only exceptions and both are named here so the sweep test can point at them:
//   PP_UNTINTED is the blend factor that means "draw the sprite exactly as authored", not a colour choice. GameMaker's
//   own constant for it is c_white, so the one place that name may appear is this file.
//   PP_COLOUR_MISSING is what a bad palette index or an unknown role draws as. It is deliberately a colour no room
//   palette may declare, so a mistake is visible on screen instead of silently black.
#macro PP_UNTINTED c_white
#macro PP_COLOUR_MISSING make_colour_rgb(255, 0, 255)

// The title screen's inks and its backdrop, taken from the pixels the title art is drawn in. #f8f8f8 is 2C02 $20 and
// #005800 is 2C02 $0B, the two entries both ground bands declare (data/palettes/scene_title.json, bg2 and bg3), so the
// text and the rules are drawn from the picture and never tinted. PP_TITLE_DIM is the rule that marks an "off" row and
// the window frame: a real PPU entry, so a rule drawn in it is a colour the chip can output. There is deliberately no
// grey: the font sheet carries one ink, and a tinted grey came out as #7b7b7b, which no PPU can output (t_a1170172).
// The backdrop is $0F black, what the scene declares at $3F00 and what the clear rectangle spends.
#macro PP_TITLE_WHITE make_colour_rgb(248, 248, 248)
#macro PP_TITLE_DIM make_colour_rgb(0, 88, 0)
#macro PP_TITLE_BACKDROP c_black

// Battle field geometry (spec 07). The field is the whole 256x240 frame; the menu band is the lower third.
#macro PP_FIELD_W PP_FRAME_W
#macro PP_FIELD_H PP_FRAME_H
#macro PP_MENU_TOP 168

// Dodge arena geometry (spec 08): a 160x100 box centred at (128,120), inclusive bounds.
#macro PP_ARENA_W 160
#macro PP_ARENA_H 100
#macro PP_ARENA_CX 128
#macro PP_ARENA_CY 120
#macro PP_MARKER_SIZE 8
#macro PP_MARKER_SPEED 2
#macro PP_HITBOX_INSET 2
#macro PP_INVULN_STEPS 30
#macro PP_SPAWN_EXCLUSION 24
#macro PP_ARENA_WARN_STEPS 12
#macro PP_ARENA_CAP_STEPS 900

// Turn and message timing (spec 07).
#macro PP_INTRO_FLASH_STEPS 30
#macro PP_FRAME_SLIDE_STEPS 12
#macro PP_MESSAGE_STEPS 20
#macro PP_TELEGRAPH_STEPS 12
#macro PP_RESULT_STEPS 30
#macro PP_DAMAGE_POPUP_STEPS 24

// Fight bar (spec 07 T7): power 100 at the bullseye, 0 at the ends, 60 steps end to end.
#macro PP_FIGHT_SWEEP_STEPS 60
#macro PP_FIGHT_DAMAGE_MIN 2
#macro PP_FIGHT_DAMAGE_MAX 12

/// The application modes from spec 01. Only registered modes can be entered; pp_app_boot fails loudly otherwise.
enum PPMode {
    boot = 0,
    title = 1,
    overworld = 2,
    cutscene = 3,
    battle = 4,
    menu = 5
}

/// Battle phases. Every transition goes through pp_battle_phase_set() in pp_battle_director.
enum PPBattlePhase {
    intro = 0,
    menu = 1,
    resolve = 2,
    message = 3,
    telegraph = 4,
    dodge = 5,
    result = 6,
    ended = 7
}

/// The five battle commands, in cursor order (spec 07).
enum PPCommand {
    fight = 0,
    power = 1,
    talk = 2,
    spare = 3,
    item = 4
}

/// Encounter result for one enemy (spec 10). Recorded once, never inferred afterwards.
/// interrupt is the third ending a fight can have: the encounter data stops the fight without a win and without a
/// loss, and a scene takes over. It is never a kill and never a spare, so the ledger counts nothing for it.
enum PPResult {
    none = 0,
    kill = 1,
    spare = 2,
    interrupt = 3
}

/// The three ways an enemy can leave a fight (spec 10 rule 6). One row per enemy carries one of these, and the fight
/// verdict is computed from them. down is the only one that moves a kill counter; turned is an enemy who walked away
/// because the fight stopped, so it is neither a kill nor a spare.
enum PPExit {
    down = 0,
    spared = 1,
    turned = 2
}

/// What a whole fight reads as, from the rows under it (spec 10 rule 6). Generous in the player's favour: quiet means
/// nothing was put down, mixed means something was, violent means nothing left standing.
enum PPFightVerdict {
    quiet = 0,
    mixed = 1,
    violent = 2
}

/// Route derived from the ledger on read (spec 10).
enum PPRoute {
    undecided = 0,
    mercy = 1,
    blooded = 2,
    genocide = 3
}

/// The save slot's asynchronous states (spec 11). Every transfer is one state and pp_save_async_event is the only
/// thing that moves it on.
enum PPSaveState {
    idle = 0,
    reading = 1,
    retrying = 2,
    backing = 3,
    backing_write = 4,
    writing = 5,
    ready = 6,
    saved = 7,
    absent = 8,
    failed = 9
}

/// Element names are data; this enum only exists so a typo in code is a compile error.
enum PPElement {
    none = 0,
    sea = 1,
    stone = 2,
    time = 3,
    void = 4
}

// Overworld (spec 04). Free walk is 12 steps per tile, rail walk 8, and the walker always finishes a tile.
#macro PP_TILE 16
#macro PP_VIEW_W 16
#macro PP_VIEW_H 15
#macro PP_WALK_STEPS_FREE 12
#macro PP_WALK_STEPS_RAIL 8
#macro PP_TRIGGER_LOCK_STEPS 20
#macro PP_MARKER_RESPAWN_STEPS 30

// The first room of a new run (card ASSEMBLE, settled by card SFX-WIRE 2026-10-22): the Small Ship's deck, played in
// rm_pp_ship from the map file data\maps\all.json. It is here, in the constants, so a different first room is one line
// and not a search. data\slice.json and data\project.json already named ship_small as the slice's map, and
// ROADMAP-2026-10-22 puts the first two fights on this deck, so the constant follows the data instead of the
// provisional lower deck the ASSEMBLE card wrote when the deck did not exist yet.
#macro PP_NEW_GAME_MAP "ship_small"
#macro PP_NEW_GAME_SPAWN "start"
#macro PP_NEW_GAME_ROOM "rm_pp_ship"

// The environment variables the self checks read. Their names are macros because the project check refuses any PP_
// name that is not a macro, and the name is split so the literal in the macro definition is not itself an undefined
// use. Unset in every real launch, the checks cost one environment read per frame and write nothing.
#macro PP_SHIP_CAPTURE "PP_" + "SHIP_CAPTURE"
#macro PP_TITLE_CAPTURE "PP_" + "TITLE_CAPTURE"

// Dialogue box (spec 05). Box 240x64 at (8,168); the text area is the whole inside of the box, 8 pixels in from the
// frame on every side, and holds 28 characters over 3 rows with the 8x8 font: 16 + 28 * 8 = 240, which is the box's
// own right edge less its 8 pixel padding.
// The arithmetic is the whole reason for these numbers (card t_1d828fcd). The box is 240 wide, so the inside is 224,
// so 28 cells of 8 fit and 30 do not: 30 characters from an 8 pixel inset would end at x 256, past the frame. The
// earlier 30 was written against a text area that started at x 72 (a 48 pixel portrait column), and 30 cells from x 72
// end at x 312. PP_TEXT_CHARS, PP_TEXT_RIGHT and specs/05-dialogue.md all state 28, and
// tests/test_dialogue_v2.py::test_the_box_geometry_and_the_wrap_agree recomputes the identity on every run.
// There was no portrait in this slice until card t_4d6b0f4b: no speaker carried one, so pp_dialogue_draw drew none.
// A bust cannot take a column of the box either way, because a 48 pixel column would cost 6 of the 28 characters, so
// it stands ABOVE the box on the box's own top edge and the text area keeps every column it has (D10 point 3).
// The numbers: 48x48 at (16, 120) ends at y 167, one pixel above the box's top edge at 168, so the bust touches the
// box and covers none of it. 16 is the same inset as PP_TEXT_X, so the bust and the text area start on one line.
#macro PP_BOX_X 8
#macro PP_BOX_Y 168
#macro PP_BOX_W 240
#macro PP_BOX_H 64
#macro PP_PORTRAIT_X 16
#macro PP_PORTRAIT_Y 120
#macro PP_PORTRAIT_SIZE 48
// The name plate's own inset, and the x it takes when a bust is on the page: the bust's 48 pixels end at 63, so the
// plate starts at 68 and the two cannot overlap. The plate is 64 wide either way, from its x to x + 64.
#macro PP_PLATE_X 12
#macro PP_PLATE_W 64
#macro PP_PLATE_BUST_X 68
#macro PP_TEXT_X 16
#macro PP_TEXT_Y 176
#macro PP_TEXT_RIGHT 240
#macro PP_TEXT_LINE_H 10
#macro PP_TEXT_CHARS 28
#macro PP_TEXT_ROWS 3
// Choices (spec 05, card t_01432e14). A page that offers choices does not share its rows with the labels: once the
// page has finished typing, its three rows are replaced by one row per choice, drawn in the same three 10 pixel rows.
// The cursor is a 6x6 block in column 0 of the text area and the label starts in column 1, so the two cannot overlap
// and 24 + 27 * 8 = 240 still ends on the text area's own right edge.
#macro PP_CHOICE_ARROW_X 16
#macro PP_CHOICE_ARROW_W 6
#macro PP_CHOICE_LABEL_X 24
#macro PP_TEXT_STEPS_SLOW 2
#macro PP_TEXT_STEPS_FAST 1
#macro PP_TEXT_PAUSE_STOP 8
#macro PP_TEXT_PAUSE_COMMA 3
#macro PP_TEXT_BLIP_EVERY 3
#macro PP_ARROW_ON 15
#macro PP_ARROW_OFF 15

// Cutscene runner (spec 06). Camera pans in 24 steps, music crossfades in 30, shake is 1 or 2 pixels every 2 steps.
// A flash is 2 frames of one declared role flooded over the frame, 8 at most, and it costs the scene no steps.
#macro PP_CAMERA_MOVE_STEPS 24
#macro PP_MUSIC_FADE_STEPS 30
#macro PP_SHAKE_MAX_STEPS 60
#macro PP_SHAKE_PERIOD 2
#macro PP_FLASH_STEPS 2
#macro PP_FLASH_MAX_STEPS 8
#macro PP_SCENE_WARN_COMMANDS 256

// Save slot (spec 11). One file, one backup, a 64 KB buffer, and the format number the loader checks before anything
// else. The bounds are what the validator reads; a number outside them is a refused file, not a clamped one.
#macro PP_SAVE_FORMAT 1
#macro PP_SAVE_GAME_VERSION "0.1.0-slice"
#macro PP_SAVE_SLOT "pp_save_01.json"
#macro PP_SAVE_BACKUP "pp_save_01.json.bak"
#macro PP_SAVE_BUFFER 65536
#macro PP_SAVE_PANEL_STEPS 20
#macro PP_SAVE_ERROR_STEPS 150
#macro PP_SAVE_MAX_COUNTER 9999
#macro PP_SAVE_MAX_PLAY_SECONDS 360000
#macro PP_SAVE_MAX_HP 999
#macro PP_SAVE_MAX_ITEM_COUNT 99
#macro PP_SAVE_MAX_FLAG_CHARS 64
// The per-fight exit rows (spec 10 rule 6): a fight holds a handful of enemies, so a file claiming hundreds is a
// foreign file. The round bound matches the counter bound.
#macro PP_SAVE_MAX_EXIT_ROWS 32
#macro PP_SAVE_MAX_ROUND 9999
