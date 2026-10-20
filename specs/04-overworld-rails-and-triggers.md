# Spec 04: overworld rails and triggers

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: the player walks a tile map and presses confirm on things; on some screens the game walks for them while the
story plays, and hands control back with no button press.

Three data pieces per map
1. Tile map: 16x16 tiles, 16 by 15 tiles visible, larger maps scroll (spec 03).
2. Collision grid: one byte per tile, 0 walkable, 1 blocked, 2 story blocked. Separate from tile art so walls can change
   without redrawing tiles.
3. Trigger list: `{x, y, kind, id, once, condition}` with kinds `scene`, `battle`, `map`, `say`, `flag`, `marker`.
   A map also carries name, spawn points and music id.

Rails: a list of `walk(direction, tiles)`, `wait(steps)`, `say(dialogue_id)`, `face(direction)`.
- Rail walk is 8 steps per tile; free walk is 12 steps per tile; the walker always finishes a tile and stays centred.
- A rail may not cross a blocked tile: the data checker rejects that rail, so a rail cannot soft lock.
- Confirm skips to the next `say` but never skips a walk. Only the rail's own end or a scene request cancels it.

Rules
1. Free movement is 4 directions, one tile per press, no diagonals, facing updates instantly.
2. Confirm on a trigger tile fires it; confirm facing a door fires that tile's map trigger.
3. A trigger marked once is recorded in the route ledger (spec 10), so doors stay open across a save and load.
4. Triggers are inert for 20 steps after any scene or battle ends, so an exit onto its own trigger does not loop.
5. Story blocked tiles open when a flag is set: that is the ship's locked door and the data center gate.
6. The walker never moves while a text box is open or a rail runs.

Encounters: markers only, drawn as a small silhouette, never random. Touching one starts a battle; the marker is gone
for 30 steps then respawns, so a corner cannot trap the player. An area may cap marker density.

Map changes: 12 step fade each way, spawn at the named spawn point unless the entry says `keep_position`.

PP content: Map 1 Soton High Street and Harbor is the free walk map; the Faux Wessex Lane Halls intro is one rail with
three `say` beats; Map 2 the small ship is a corridor with story blocked doors; Map 3 the AI data center uses trigger
chains for its hack puzzles; the London prison corridor is the case that needs the 20 step lock.

Acceptance (Nayil)
1. Single presses move exactly one tile, always centred.
2. Walking into a wall does nothing, with no animation past one push frame.
3. The intro rail walks on its own, confirm advances text, control returns unprompted.
4. An encounter marker does not immediately re-fight after the battle.
5. Deleting a dialogue id in data makes the checker name the missing id before the game runs.

Out of scope: diagonals, NPC pathfinding, parallax, a map editor GUI.
