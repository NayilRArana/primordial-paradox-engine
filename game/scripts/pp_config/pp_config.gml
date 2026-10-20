/// pp_config: the constants and enums every other module reads.
/// Written from specs\01, 03, 07, 08, 10, 13. No magic numbers live outside this file and data\.
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
enum PPResult {
    none = 0,
    kill = 1,
    spare = 2
}

/// Route derived from the ledger on read (spec 10).
enum PPRoute {
    undecided = 0,
    mercy = 1,
    blooded = 2,
    genocide = 3
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

// Dialogue box (spec 05). Box 240x64 at (8,168); portrait 48x48; text area from x 72, 30 characters over 3 rows.
#macro PP_BOX_X 8
#macro PP_BOX_Y 168
#macro PP_BOX_W 240
#macro PP_BOX_H 64
#macro PP_PORTRAIT_X 16
#macro PP_PORTRAIT_Y 176
#macro PP_PORTRAIT_SIZE 48
#macro PP_TEXT_X 72
#macro PP_TEXT_Y 176
#macro PP_TEXT_RIGHT 240
#macro PP_TEXT_LINE_H 10
#macro PP_TEXT_CHARS 30
#macro PP_TEXT_ROWS 3
#macro PP_TEXT_STEPS_SLOW 2
#macro PP_TEXT_STEPS_FAST 1
#macro PP_TEXT_PAUSE_STOP 8
#macro PP_TEXT_PAUSE_COMMA 3
#macro PP_TEXT_BLIP_EVERY 3
#macro PP_ARROW_ON 15
#macro PP_ARROW_OFF 15

// Cutscene runner (spec 06). Camera pans in 24 steps, music crossfades in 30, shake is 1 or 2 pixels every 2 steps.
#macro PP_CAMERA_MOVE_STEPS 24
#macro PP_MUSIC_FADE_STEPS 30
#macro PP_SHAKE_MAX_STEPS 60
#macro PP_SHAKE_PERIOD 2
#macro PP_SCENE_WARN_COMMANDS 256
