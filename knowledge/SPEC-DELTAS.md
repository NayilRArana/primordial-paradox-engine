# Spec deltas: what thirteen specs are missing or wrong about

Written 2026-10-19. The first draft of this file followed a read that was later quarantined as a clean-room breach, so
the list was re-derived in the clean-room re-review of 2026-10-19 from public genre design and the official manual only,
and each item was re-checked against that material. An item that could stand only on that read would have been
removed; none had to be. This file only LISTS deltas; it does not rewrite the specs, so Nayil can accept or reject each
one before any text moves. Status per item: CORRECTION (a spec states something that is wrong or impossible as written),
THIN (true but underspecified; code cannot be written from it), MISSING (no spec covers it at all).

Counts: 13 specs read, 24 deltas found, of which 4 CORRECTION, 13 THIN, 7 MISSING.

C4 and C5 were added in the gate pass of the same day (card t_e78500a3) after reading the specs against each other and
against the same manual pages once more. C1 and C3 were re-read at source in that pass and stand as written.

## CORRECTIONS

C1. specs\12-audio.md rule 3 is not supported by the manual. The page the spec cites for looping, audio_play_sound, says
only that the third argument makes the sound repeat until it is stopped, and the Sound Editor page documents volume,
loop preview and OGG conversion but no loop point metadata at all (both re-read 2026-10-19). So "loop points come from
the OGG file's own loop metadata" is a claim nobody here can source, and the musician lane could deliver files whose
intended loop point is ignored, with every track looping at the wrong place.
Fix: choose one of (a) whole-file loop, with the file trimmed to exactly the loop length and any intro delivered as a
separate one-shot sound, or (b) intro plus loop as two sounds with a scheduled handover. Recommend (a): it is what the
manual does support, it needs no engine code, and it keeps the musician lane's job unchanged apart from the file split.
Then test one looping track on a real build before the contract is fixed, and record the result here.

C2. specs\03-camera-and-scaling.md says the window is resized to the integer multiple so no bars appear, and its own
acceptance 5 requires black bars in fullscreen. Both cannot hold at once.
Fix: windowed mode resizes the window to 256*scale by 240*scale; fullscreen keeps the display size and letterboxes the
same integer scale. State which one a borderless window uses (recommend letterbox, same as fullscreen).

C3. specs\13-8bit-look.md rule 2 promises the checker "validates that every sprite's pixels reference palette
indices". There are no sprites yet, no image tooling in this repo, and that check cannot run without GameMaker or a
sprite importer.
Fix: for now the checker validates the data side (palette has exactly 54 entries, every room declares at most 16
palette indices, every declared index exists, appended only). The per pixel check moves to the importer ticket.

C4. specs\05-dialogue.md cannot fit its own line length. The text area runs from x 72 to x 240, so it is 168 pixels
wide, and the font is 8x8 with fixed cells (specs\13-8bit-look.md), so an 8 pixel advance fits 21 characters and a 6
pixel advance fits 28. The spec says 30 characters per line, which needs a 5.6 pixel advance, and it calls a 40
character line a checker error. Dialogue is the slice's main visible output, so this is one of the first things the
slice code would hit.
Fix: state the glyph advance explicitly and make the line length follow from it. Recommend a 6 pixel advance inside the
8 pixel cell, which stays legible at 1x and gives 28 characters, so the checker error becomes a word longer than 28
characters. The 3 line page still fits the 48 pixel text height at a 16 pixel pitch. Do not widen the text area: the
portrait and the box frame are already fixed by spec 05 and spec 13.

C5. specs\09-bullet-pattern-recipes.md states `angle` as "0 is right, 90 is down". That is the screen convention,
clockwise with y growing downward. The engine's own angle maths is the other one: a positive quarter turn points up,
because a positive y is downward and the angle is measured the other way round. The manual text I could read today (the
lengthdir and point_direction pages) states the convention in a picture, not in words, so a recipe driven straight
through lengthdir_x and lengthdir_y with a data angle of 90 sends its hazard up when the author read "down", and every
mirrored pattern is wrong without any error being raised.
Fix: keep the data convention, which is how an artist reads a box on screen, and require one named conversion
(`pp_angle_to_gm`) used by the arena and nowhere else, plus one test that a 90 degree emitter at origin top moves its
hazard toward the bottom of the box. Add the same sentence to the geometry section of specs\08-dodge-arena.md.

## THIN (underspecified, blocks code)

T1. specs\01-state-machine.md rule 5 says battle is entered by a request naming enemy id, return mode and position,
but nothing says what happens to the map underneath. The genre has two public answers: suspend the field and stage the
battle over it, or unload the field and enter a battle room (knowledge\genre-design.md section 2 describes the battle as
its own framed stage and does not say which). Ours: the map stays loaded and suspended, the battle mode draws over it,
and the map is redrawn unchanged on return, because spec 01 rule 4 already says the overworld step is not called while
another mode owns the frame, and its acceptance 4 requires the walker to be exactly where it was. Add that sentence and
the draw order (map, battle dimmer, battle field, GUI).

T2. specs\01-state-machine.md and specs\11-save.md together make defeat lose progress silently: autosave never fires in
battle (11.4), autosave fires on map entry (11.4), and defeat returns to title (1.6). So a player who dies to a boss can
lose everything since they entered the map. Decide: either autosave on battle entry is allowed, or the defeat screen
states the last save point. Recommend the second (it keeps 11.4 intact and costs no write).

T3. specs\02-input.md quantises the keyboard dodge vector to 8 directions while its own acceptance 4 requires diagonal
at the same speed as straight. Without normalisation a diagonal is 1.41 times faster.
Fix: publish one normalised vector, with the eight quantised directions already normalised (0.707 per component) and
rounded to whole pixels, and let specs\08 use it unchanged.

T4. specs\04-overworld-rails-and-triggers.md has a rail system, specs\06-cutscene-runner.md has a `move` command "at
rail speed". Two walkers will drift.
Fix: one walker. A scene is the only thing that walks anybody; a map rail is a scene that contains only walk, wait,
say and face. The rail fields in map data become a scene id plus a trigger, or the map rail list is deleted.

T5. specs\04 rule 4 ("triggers inert for 20 steps after any scene or battle ends") and the encounter respawn ("gone
for 30 steps then respawns") do not say whether those counters tick while the battle mode is open. If they do, the
marker respawns behind the fight and the player re-fights instantly.
Fix: both counters count overworld steps only; a marker whose encounter is flagged `once` is removed for good.

T6. specs\05-dialogue.md says a line that cannot fit in the box "is a checker error", but the same spec allows word
wrap and pages, so no line could ever be over length unless the author wanted a specific pagination.
Fix: name the page break (`{page}`), state the wrap rule exactly (greedy by word, never split a word, never hyphenate),
and make the checker error only for a WORD longer than 30 characters and a page with more than 3 wrapped lines.

T7. specs\07-battle-director.md does not define how the FIGHT bar becomes damage. "Sweeps 0 to 100 in 60 steps, damage
2 to 12" leaves the mapping open.
Fix: `power` is 100 at the bullseye and falls linearly to 0 at the bar ends; `damage = round(2 + 10 * power / 100)`
multiplied by the actor's power multiplier from data, floored at 1. Two numbers, no ambiguity, and it makes the
acceptance test (damage between 2 and 12) provable.

T8. specs\07 TALK and specs\05 choices describe the same UI twice: TALK has "up to 4 context options from enemy data"
and dialogue has a choice list with conditions. Which one draws it is unanswered.
Fix: TALK options are dialogue choices (id, label, condition, effect). The battle menu opens a dialogue with the
enemy's talk dialogue id; the trust increment is the choice's effect, not a rule inside the menu.

T9. specs\07 lists rewards as "god powers, items and health upgrades" but the enemy data fields do not include a drop
table shape.
Fix: enemy data gets `rewards: [{kind, id, count, condition}]` with kind in power, item, health.

T10. specs\09-bullet-pattern-recipes.md has no hazard size, while specs\08 allows 8x8 and 16x16 with a hitbox inset.
The checker cannot validate what it cannot see.
Fix: each spawn frame declares `size` (8 or 16); the hitbox inset of 2 px per side is applied by the arena.

T11. specs\09 rule 2 requires determinism, rule 7 says one seed per battle, but the fan shape "aims at the marker at
spawn time", which makes the pattern depend on the player. Nothing names the seed source.
Fix: each pattern declares `aim: fixed | at_marker`; the seed is a single integer on the encounter, and the checker
simulates with the marker at box centre for `fixed` and asserts the exclusion radius at each spawn for both modes.

T12. specs\10-route-ledger.md derives the route "on read and never stored", but its own table needs to know whether
the player is before or after the prison, and no value records that.
Fix: add a `stage` integer to the save (monotonic story stage, advanced by data) and derive the route from counters
plus stage. Otherwise "undecided" becomes "mercy" the moment the counters are zero, which is wrong after the prison.

## MISSING

M1. No spec defines the data file formats. Every spec points at data ("enemy data", "pattern recipes", "dialogue",
"map"), and nothing says the JSON shape, the version field, the id rules or the cross reference rules. This is the
single biggest gap and it blocks tools\check_data.
Fix: new specs\14-data-formats.md, written from this pass, covering characters, enemies, encounters, patterns, maps,
scenes, dialogue, items, powers, palette, and the rule that ids are lowercase snake_case and unique per kind.

M2. No spec covers runtime failure of data loading (missing file, bad id, unreadable JSON). The checker catches this
before shipping, but a hand edited build or a bad merge still runs.
Fix: one rule in 14: the game reports the file and the field in plain words on screen and stops, never silently
substitutes a default.

M3. No spec covers the debug build switch itself (`PP_DEBUG` appears in 01 only) or where debug tools live.
Fix: a section in 14 or a new spec 15: one compile time constant, tools behind it, and the rule that a release build
holds no debug draw calls.

M4. No spec covers the title screen content beyond the chapter card in 01 (title slots are deferred to 11, which only
covers the save slot). The vertical slice needs Continue and New Game now.
Fix: thin scope in 01: two entries, Continue visible only when a save exists, New Game warns before overwriting.

M5. No spec covers the encounter result screen (victory text variants for kill versus spare, the message that lists
rewards). Spec 07 says "30 step victory or defeat, then the result returns" and nothing says what is drawn.
Fix: a small table in 07: three lines maximum, source is dialogue ids per result kind, no numbers on screen.

M6. No spec covers audio asset naming and the sound registry, so the checker cannot prove a music id in a scene exists.
Fix: in 14, a `data\audio.json` registry with ids, kind (music, sfx, ui), and a file name the musician lane delivers.

M7. No spec names the resource a god power spends. Spec 07 says POWER uses a god power with a cost from data, and
every mention of a cost resource (will, spirit, focus) is absent from all 13 specs.
Fix: name it in 07 and give the numbers: one pool per party member, refilled to full at the start of every battle so a
battle can always be won without items, and the pool is not carried on the route ledger. The slice implements this as
`will`, with `will_max` on the character and `cost` on the power, and records it here because the spec does not.

## What this pass did NOT touch

The numbers that the specs already fix are all kept as written: 256x240, integer scale 1 to 6, 60 steps per second,
12 step fades, 16x16 tiles, 160x100 dodge box, 8x8 marker at 2 px per step, 30 step invulnerability, 2 steps per
character, 30 character lines, 3 line pages, 900 step phase cap, 54 colour palette, 16 colours on screen. No spec was
rewritten; every item above is a proposal with a recommended fix.
