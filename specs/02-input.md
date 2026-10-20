# Spec 02: input map

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: keyboard and gamepad are one thing to the player, and no object outside this module reads a key.

| Action | Keyboard | Gamepad |
| --- | --- | --- |
| confirm | Z, Space, Enter | bottom face, Start in menus |
| cancel | X, Escape, Backspace | right face |
| menu | Enter, Tab | Start |
| up, down, left, right | arrows, WASD | d pad, left stick |
| debug_warp / debug_step / debug_flags | F1 / F2 / F3 | none, debug build only |

Key codes use `ord("Z")` and `vk_*` constants, per
https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Game_Input/Keyboard_Input/keyboard_check_pressed.htm
(checked 2026-10-19); gamepad constants come from the Game Input section
(https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Game_Input/Game_Input.htm, checked 2026-10-19)
and are re-exported, never used raw in game code.

Per step model: sample once in Begin Step, publish four facts per action: `held`, `pressed`, `released`, `repeat`.
The manual states keyboard_check_pressed is true only on the step a key goes from up to down
(https://manual.gamemaker.io/monthly/en/The_Asset_Editors/Object_Properties/Event_Order.htm, checked 2026-10-19, for
why Begin Step is the one sampling point), so a single read is edge correct and a second read in another event is not.

Rules
1. A grep for keyboard_check or gamepad_button_check outside this module is a code review failure.
2. Two keys for one action is one action: pressed fires once when both are held.
3. Mode entry clears pressed and repeat for one step.
4. Overworld movement is one axis at a time; if both axes are held the older press wins, a tie goes horizontal.
5. The dodge phase reads a normalised vector, not four buttons.
6. Keys live in one table so a later options screen can read them.

Numbers: stick deadzone 0.35; menu repeat after 16 steps held then every 8; text fast forward 3x, floor one line per 4
steps; keyboard dodge vector quantised to 8 directions, stick raw.

PP content: the intro rail needs repeat and the axis rule; battle menus need repeat; the dodge phase needs the vector;
the PLAN section 3 debug tools need the F keys.

Acceptance (Nayil)
1. Hold Right: one tile step, then steady repeat, no stutter at the first repeat.
2. Unplug and replug the gamepad mid session: movement works again without a restart.
3. Hold confirm through text: about 3x speed and no accidental advance.
4. Two directions at once in the dodge box: diagonal at the same speed as straight.

Out of scope: mouse, touch, rebinding screen, rumble.
