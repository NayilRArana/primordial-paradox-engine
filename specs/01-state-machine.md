# Spec 01: state machine

Status: spec, 2026-10-19. No code yet. Every number is a DECISION.

Goal: the game is always in exactly one mode, and every mode swap is covered by a fade so nothing pops.

| Mode | Owns | Entered from |
| --- | --- | --- |
| title | confirm, up, down | game start, defeat, quit |
| overworld | move, confirm, menu | title, cutscene end, menu close |
| cutscene | confirm (advance text only) | trigger, battle end |
| battle | battle menu, dodge keys | encounter, battle command |
| menu | up, down, confirm, cancel | overworld menu key, battle ITEM |
| transition | nothing | any swap |

Rules
1. One persistent controller owns `mode`; nothing else sets it, and only through `state_request(name, params)`.
2. A swap is request, fade out 12 steps, enter, fade in 12 steps. One request may queue during a fade; the newest
   replaces the older.
3. Input is sampled once per step and cleared on mode entry, so a held confirm cannot act in the new mode (spec 02).
4. Pause is a mode, not a flag: the overworld step is not called while the menu is open.
5. Battle is entered only by a request naming the enemy id plus a return mode and position.
6. Defeat never deletes a save; it returns to title with Continue available.
7. Debug build logs mode name, frame and params on every entry.

Numbers
- 60 steps per second. Fades 12 steps each. Input lock 6 steps after entry.
- Title chapter card shows for the middle 12 of 18 steps.
- Battle intro: 30 steps encounter flash, 12 steps frame slide.
- `PP_DEBUG` is a compile time constant, false in release.

Each mode is a struct with `name`, `step`, `draw`, `on_enter`, `on_exit`, registered at start so a missing mode fails
loudly at launch rather than mid scene.

PP content: the intro (Faux Wessex Lane Halls move-in) is cutscene into overworld; the Navy Sailors tutorial is
overworld into battle; Percy is cutscene, battle, cutscene, which is why the request queue exists; the Ouranos post
credits scene is entered from the credits.

Acceptance (Nayil)
1. Held confirm does not skip the title animation.
2. Walking after a fade shows no flash of the previous mode and no movement during the fade.
3. The tutorial fight enters after the flash, with no overworld movement during it.
4. Pausing and closing the menu leaves the walker exactly where it was.
5. Dying returns to title with Continue working.

Out of scope: title slot list (spec 11), turn order (spec 07), command list (spec 06).
