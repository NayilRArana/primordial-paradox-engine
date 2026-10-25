# Spec 06: cutscene runner

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: a scene is a list of plain commands in a data file. Characters walk, text opens, the screen fades, music changes.
The player presses confirm to advance text and otherwise watches. At the end, control returns with no press.

Commands
| Command | Arguments | Effect |
| --- | --- | --- |
| say | dialogue id | opens the box, waits for it to close |
| move | actor, direction, tiles | walks an actor at rail speed |
| face | actor, direction | instant turn |
| wait | steps | waits |
| fade | out or in, steps | fades the screen |
| music | id or stop | starts, crossfades or stops |
| sfx | id | plays once |
| camera | x,y or an actor | 24 step move, or back to the walker |
| shake | steps, strength | integer pixel shake |
| flash | steps, role | floods the frame in one declared role for 2 frames, 8 at most; costs no steps (2026-10-24) |
| spawn / destroy | actor, tile x, tile y / actor | story actors |
| battle | enemy id | starts a battle, waits for its result |
| setflag | name, value | writes a route ledger fact |
| branch | flag, scene id | jumps if true |
| end | none | returns control |

Rules
1. Commands run one at a time; anything that takes time blocks the list.
2. All commands are data: Nayil reorders a scene or adds a line without code.
3. `branch` is the only control flow. No loops, because an authoring loop can hang the game.
4. The checker proves every dialogue, music, sfx, actor, scene and enemy id exists, and that every `move` lands on a
   walkable tile.
5. Confirm advances a `say` and is ignored by every other command, so nobody skips a camera move into a black frame.
6. A scene that ends with a battle unresolved is a checker error.
7. Debug build: F2 steps one command and prints the index.
8. A `flash` spends no steps of its own. It is a palette change over steps the scene already spends, so it advances in
   the step it runs and the world counts its frames down. A flash priced as a wait would move every shot duration after
   it, and on the drive it would move the cue's cut grid with them.

Numbers: camera move 24 steps, linear, floored; fade 12 steps when the argument is omitted; music crossfade 30 steps;
shake 1 or 2 pixels changing every 2 steps, maximum 60 steps; a scene over 256 commands is a checker warning, because
that scene should be two scenes. Flash: 2 frames when the argument is omitted (the title's own storm clock), 8 at most,
and the role defaults to `paper`, which every set in `data\room_palettes.json` declares. A role the scene's own room
set does not declare is a checker error: a flash may only spend a colour the screen already draws with (spec 13).

PP content: the intro uses spawn, move, say, camera and music; Prometheus interrupting the Percy fight uses battle then
say then branch; the prison scene picks the Prometheus or Atlas variant with one branch on the route flag; the Kronos
ending uses spawn, camera, say and fade; the Ouranos post credits scene is a separate scene entered from credits.

Acceptance (Nayil)
1. The intro plays in order, cannot be mashed past, and returns control at the end.
2. A wrong dialogue id in a scene is named by the checker with its command line number.
3. A camera pan stops exactly on target with no overshoot.
4. Both branch variants play when the flag is flipped.
5. F2 in a debug build steps one command per press, printing the index.

Out of scope: parallel tracks, actor physics, a timeline editor.
