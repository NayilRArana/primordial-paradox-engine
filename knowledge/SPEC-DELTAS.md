# Spec deltas: what thirteen specs are missing or wrong about

Written 2026-10-19. The first draft of this file followed a read that was later quarantined as a clean-room breach, so
the list was re-derived in the clean-room re-review of 2026-10-19 from public genre design and the official manual only.
This pass (card t_bfaff47b) gives every item an explicit source line and re-reads at the source every document it
names. An item that could stand only on that read would have been removed rather than softened; none had to be, and
the one line the earlier draft carried from the study (T1's "study shows an overlay is the usual answer") is gone,
replaced by the public reasoning that is cited below.

This file only LISTS deltas; it does not rewrite the specs, so Nayil can accept or reject each one before any text
moves. Status per item: CORRECTION (a spec states something that is wrong or impossible as written), THIN (true but
underspecified; code cannot be written from it), MISSING (no spec covers it at all).

Counts: 13 specs read, 26 deltas found, of which 6 CORRECTION, 12 THIN, 8 MISSING. Counted from the headings in this
file on 2026-10-19 after the review fix pass added C6 and M8. (An earlier line said 4, 13 and 7, then 5, 12 and 7;
neither matched the headings once more items landed, so the numbers are counted from the headings, not carried
forward.)

## How to read a source line

Every delta carries exactly one source line, and the index below repeats it. The card that ordered this pass named
three source forms. Four are used here, because the three do not cover the case this file has most of:

- `manual: <url>`: the official manual, re-read at the source on 2026-10-19 in this pass. A manual page named
  anywhere in this repository without that mark is carried over, not re-verified here.
- `genre: <public description>`: a public description of how games in this genre play, from
  knowledge\genre-design.md, which was re-read in this pass. No source outside this repository is claimed.
- `internal: <file and line reference>`: the only source is this repository's own documents, meaning a spec, a spec's
  own arithmetic, or the repository's current state. All were re-read today. No external source is claimed and none is
  invented to fill the gap.
- `withdrawn: <what the study said, and why it cannot be kept>`: a claim that only the quarantined read supported.

Why the fourth form matters: 17 of the 24 items are contradictions inside our own specs, or arithmetic over our own
numbers. Labelling those `manual` or `genre` would be an invented citation, which the card that ordered this pass
forbids in the same breath. The card's three form list should gain `internal`; this is the one place where its wording
and the material disagree, and it is reported as such rather than papered over.

Withdrawn: 0. Nothing in this list now stands only on the quarantined read: each item was re-derived in this pass
against a spec, a manual page opened today, or knowledge\genre-design.md, and the study-only line the earlier draft
carried is already gone (it is recorded in knowledge\PROVENANCE.md, row for this file, which was re-read today).

## Source index

| Delta | What it says, in one line | Source |
| --- | --- | --- |
| C1 | Loop points come from the OGG file's own metadata, which nothing we can cite supports | manual: audio_play_sound and The Sound Editor, re-read today |
| C2 | Window resized so no bars, and fullscreen must show bars: both cannot hold | internal: specs\03 window bullet against acceptance 5 |
| C3 | A per pixel palette check that cannot run with no sprites and no importer | internal: specs\13 rule 2 against the repository's state |
| C4 | 30 characters in 168 pixels needs a 5.6 pixel advance in an 8x8 fixed cell font | internal: specs\05 line 11 against specs\13, arithmetic |
| C5 | Data angle 90 is down, the engine's quarter turn is not, so one conversion plus one test | manual: point_direction and lengthdir_x, re-read today |
| T1 | Nothing says what happens to the map under a battle | genre: genre-design section 2 |
| T2 | Defeat can lose everything since the map was entered | internal: specs\01 rule 6 against specs\11 11.4 |
| T3 | Eight quantised directions, and acceptance demands equal diagonal speed | internal: specs\02 quantisation against its acceptance 4 |
| T4 | A rail system and a scene runner both walk the player | internal: specs\04 rails against specs\06 move command |
| T5 | Two step counters with no statement of which mode ticks them | internal: specs\04 rule 4 and its respawn sentence |
| T6 | A line that cannot fit is a checker error, while wrapping makes that impossible | internal: specs\05 rule 4 against acceptance 5 |
| T7 | The FIGHT bar sweeps 0 to 100 and damage is 2 to 12, with no mapping | internal: specs\07 bar numbers |
| T8 | TALK options and dialogue choices are the same UI, drawn by nobody in particular | genre: genre-design section 3, plus an internal duplicate |
| T9 | Rewards are named in prose and absent from the enemy data shape | genre: genre-design section 5 |
| T10 | Patterns have no hazard size while the arena allows two | internal: specs\09 frame fields against specs\08 |
| T11 | Determinism is required, and one shape aims at the player at spawn | internal: specs\09 rules 2 and 7 against the fan shape |
| T12 | A route derived from counters cannot tell which side of a story event you are on | genre: genre-design section 4, gap found internally |
| M1 | No spec defines the data file formats | internal: the thirteen specs, read file by file |
| M2 | Nothing covers a data file that fails at runtime | manual: json_parse, re-read today |
| M3 | The debug switch itself appears in one spec and is defined nowhere | internal: specs\01, the only place PP_DEBUG appears |
| M4 | The title screen's entries are missing | internal: specs\01 chapter card against specs\11 |
| M5 | The encounter result screen is a 30 step pause that draws nothing defined | internal: specs\07 end of fight |
| M6 | No audio registry, so a music id cannot be checked | internal: specs\12 and specs\06 name ids nothing defines |
| M7 | POWER spends a resource no spec names | internal: specs\07 cost, with no resource in any spec |

Totals: 3 `manual`, 4 `genre`, 17 `internal`, 0 `withdrawn`. Every row was counted from this file by script on
2026-10-19, not by hand.

C4 and C5 were added in the gate pass of the same day (card t_e78500a3) after reading the specs against each other and
against the same manual pages once more. C1 and C3 were re-read at source in that pass and stand as written. Every
source line in this file was set or re-checked in this pass.

## CORRECTIONS

C1. specs\12-audio.md rule 3 is not supported by the manual. The page the spec cites for looping, audio_play_sound,
documents the third argument as making the sound repeat until it is stopped, and the Sound Editor page documents
volume, a loop toggle and rewind in its Playback controls, OGG conversion, attributes, target options, audio group and
export directory, but no loop point metadata anywhere on it (both re-read 2026-10-19). So "loop points come from the
OGG file's own loop metadata" is a claim nobody here can source, and the musician lane could deliver files whose
intended loop point is ignored, with every track looping at the wrong place.
Fix: choose one of (a) whole-file loop, with the file trimmed to exactly the loop length and any intro delivered as a
separate one-shot sound, or (b) intro plus loop as two sounds with a scheduled handover. Recommend (a): it is what the
manual does support, it needs no engine code, and it keeps the musician lane's job unchanged apart from the file split.
Then test one looping track on a real build before the contract is fixed, and record the result here.
Source: manual: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Asset_Management/Audio/audio_play_sound.htm
and https://manual.gamemaker.io/monthly/en/The_Asset_Editors/Sounds.htm, both re-read 2026-10-19. The fix is our decision.

C2. specs\03-camera-and-scaling.md says the window is resized to the integer multiple so no bars appear, and its own
acceptance 5 requires black bars in fullscreen. Both cannot hold at once.
Fix: windowed mode resizes the window to 256*scale by 240*scale; fullscreen keeps the display size and letterboxes the
same integer scale. State which one a borderless window uses (recommend letterbox, same as fullscreen).
Source: internal: specs\03-camera-and-scaling.md, the window bullet "window resized to match so an integer scale
leaves no bars" against its acceptance 5 ("1024x960 with black bars"). Re-read 2026-10-19. No manual page settles it;
the contradiction is internal.

C3. specs\13-8bit-look.md rule 2 promises the checker "validates that every sprite's pixels reference palette
indices". There are no sprites yet, no image tooling in this repo, and that check cannot run without GameMaker or a
sprite importer.
Fix: for now the checker validates the data side (palette has exactly 54 entries, every room declares at most 16
palette indices, every declared index exists, appended only). The per pixel check moves to the importer ticket.
Source: internal: specs\13-8bit-look.md rule 2 against the repository's current state (no sprite asset in game\ and no
image tooling in tools\), checked 2026-10-19. No external source is involved.

C4. specs\05-dialogue.md cannot fit its own line length. The text area runs from x 72 to x 240, so it is 168 pixels
wide, and the font is 8x8 with fixed cells (specs\13-8bit-look.md), so an 8 pixel advance fits 21 characters and a 6
pixel advance fits 28. The spec says 30 characters per line, which needs a 5.6 pixel advance, and it calls a 40
character line a checker error. Dialogue is the slice's main visible output, so this is one of the first things the
slice code would hit.
Fix: state the glyph advance explicitly and make the line length follow from it. Recommend a 6 pixel advance inside the
8 pixel cell, which stays legible at 1x and gives 28 characters, so the checker error becomes a word longer than 28
characters. The 3 line page still fits the 48 pixel text height at a 16 pixel pitch. Do not widen the text area: the
portrait and the box frame are already fixed by spec 05 and spec 13.
Source: internal: specs\05-dialogue.md line 11 (text area x 72 to 240, 30 characters per line) and acceptance 5 (a 40
character line is refused) against specs\13-8bit-look.md (one 8x8 font with fixed cells). The arithmetic 168 / 30 =
5.6 and 168 / 28 = 6 was done in this pass, 2026-10-19. No external source.

C5. specs\09-bullet-pattern-recipes.md states `angle` as "0 is right, 90 is down". That is the screen convention,
clockwise with y growing downward. The engine's own angle maths is the other way round: a positive quarter turn points
up, because a positive y is downward and the angle is measured the other way. The manual pages that define that maths
state the convention in a picture, not in words, so a recipe driven straight through lengthdir_x and lengthdir_y with
a data angle of 90 sends its hazard up when the author read "down", and every mirrored pattern is wrong without any
error being raised.
Fix: keep the data convention, which is how an artist reads a box on screen, and require one named conversion
(`pp_angle_to_gm`) used by the arena and nowhere else, plus one test that a 90 degree emitter at origin top moves its
hazard toward the bottom of the box. Add the same sentence to the geometry section of specs\08-dodge-arena.md.
Source: manual: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Maths_And_Numbers/Angles_And_Distance/point_direction.htm
and https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Maths_And_Numbers/Angles_And_Distance/lengthdir_x.htm,
both re-read 2026-10-19. Neither page states the turn direction in words; it is in their pictures. That is exactly why
the delta asks for a named conversion and one directional test: the test is what settles the turn, and if it shows the
opposite, the conversion's sign flips and nothing else in the design changes. Recorded as a manual reading of a
picture, not as a quotable sentence.
Implemented 2026-10-19: `pp_angle_to_gm` lives in game\scripts\pp_dodge_arena, the recipe emitter calls it once at
spawn, a data curve is negated in the same place, and tests\test_check_data.py proves that a 90 degree emitter at
origin top crosses the box and that a positive curve bends clockwise on screen. tools\check_data.py mirrors the same
maths, including the negated sine in lengthdir_y. specs\08 has not been edited, so the geometry sentence this delta
asks for is still owed to the spec text.

C6. specs\02-input.md binds Enter to two actions. `confirm` lists "Z, Space, Enter" and `menu` lists "Enter, Tab", so
one key fires both. The gamepad column has the same shape: Start is listed under confirm "in menus" and under menu
always. pp_input's table is the thing a later options screen reads, so a duplicate binding is a bug waiting for a
screen to show it.
Fix as implemented: confirm keeps Z, Space and Enter; menu keeps Tab and Start. "Start acts as confirm inside a menu"
is a context rule that a one row per action table cannot express, so it is not in the table at all; if it is wanted it
becomes a menu-local accept stated in the spec. No module reads `menu` yet, so today this changes no behaviour.
Source: internal: specs\02-input.md action table against game\scripts\pp_input\pp_input.gml, checked 2026-10-19.
tests\test_project.py now fails if any key or pad button is bound to more than one action.

## THIN (underspecified, blocks code)

T1. specs\01-state-machine.md rule 5 says battle is entered by a request naming enemy id, return mode and position,
but nothing says what happens to the map underneath. The genre has two public answers: suspend the field and stage the
battle over it, or unload the field and enter a battle room (knowledge\genre-design.md section 2 describes the battle
as its own framed stage and does not say which). Ours: the map stays loaded and suspended, the battle mode draws over
it, and the map is redrawn unchanged on return, because spec 01 rule 4 already says the overworld step is not called
while another mode owns the frame, and its acceptance 4 requires the walker to be exactly where it was. Add that
sentence and the draw order (map, battle dimmer, battle field, GUI).
Source: genre: knowledge\genre-design.md section 2 ("the box is a separate stage: the background dims, the box frames
the action"), re-read 2026-10-19, plus the internal basis in specs\01-state-machine.md rules 4 and 5 and acceptance 4.

T2. specs\01-state-machine.md and specs\11-save.md together make defeat lose progress silently: autosave never fires in
battle (11.4), autosave fires on map entry (11.4), and defeat returns to title (1.6). So a player who dies to a boss can
lose everything since they entered the map. Decide: either autosave on battle entry is allowed, or the defeat screen
states the last save point. Recommend the second (it keeps 11.4 intact and costs no write).
Source: internal: specs\01-state-machine.md rule 6 (defeat returns to title) against specs\11-save.md 11.4 (autosave
on map entry, never in battle). Re-read 2026-10-19.

T3. specs\02-input.md quantises the keyboard dodge vector to 8 directions while its own acceptance 4 requires diagonal
at the same speed as straight. Without normalisation a diagonal is 1.41 times faster.
Fix: publish one normalised vector, with the eight quantised directions already normalised (0.707 per component) and
rounded to whole pixels, and let specs\08 use it unchanged.
Source: internal: specs\02-input.md, the eight direction quantisation against its acceptance 4. The 1.414 factor is
the diagonal of a unit square, computed here 2026-10-19.

T4. specs\04-overworld-rails-and-triggers.md has a rail system, specs\06-cutscene-runner.md has a `move` command "at
rail speed". Two walkers will drift.
Fix: one walker. A scene is the only thing that walks anybody; a map rail is a scene that contains only walk, wait,
say and face. The rail fields in map data become a scene id plus a trigger, or the map rail list is deleted.
Source: internal: specs\04-overworld-rails-and-triggers.md (rail system) against specs\06-cutscene-runner.md (the move
command at rail speed). Re-read 2026-10-19.

T5. specs\04 rule 4 ("triggers inert for 20 steps after any scene or battle ends") and the encounter respawn ("gone
for 30 steps then respawns") do not say whether those counters tick while the battle mode is open. If they do, the
marker respawns behind the fight and the player re-fights instantly.
Fix: both counters count overworld steps only; a marker whose encounter is flagged `once` is removed for good.
Source: internal: specs\04-overworld-rails-and-triggers.md rule 4 and its encounter respawn sentence, neither of which
names the mode its counter runs in. Re-read 2026-10-19.

T6. specs\05-dialogue.md says a line that cannot fit in the box "is a checker error", but the same spec allows word
wrap and pages, so no line could ever be over length unless the author wanted a specific pagination.
Fix: name the page break (`{page}`), state the wrap rule exactly (greedy by word, never split a word, never hyphenate),
and make the checker error only for a WORD longer than 30 characters and a page with more than 3 wrapped lines.
Note: the 30 in that fix is superseded by C4, which lands the line length at 28 for a 6 pixel advance. If C4 is
accepted, this delta's threshold becomes 28 and the two must be decided together; if C4 is rejected, it stays as
written here.
Source: internal: specs\05-dialogue.md rule 4 (wrap by word, over 3 lines becomes another page) against its acceptance
5 (a 40 character line is a checker error). Re-read 2026-10-19.

T7. specs\07-battle-director.md does not define how the FIGHT bar becomes damage. "Sweeps 0 to 100 in 60 steps, damage
2 to 12" leaves the mapping open.
Fix: `power` is 100 at the bullseye and falls linearly to 0 at the bar ends; `damage = round(2 + 10 * power / 100)`
multiplied by the actor's power multiplier from data, floored at 1. Two numbers, no ambiguity, and it makes the
acceptance test (damage between 2 and 12) provable.
Source: internal: specs\07-battle-director.md, the FIGHT bar numbers, with no mapping stated. Re-read 2026-10-19.

T8. specs\07 TALK and specs\05 choices describe the same UI twice: TALK has "up to 4 context options from enemy data"
and dialogue has a choice list with conditions. Which one draws it is unanswered.
Fix: TALK options are dialogue choices (id, label, condition, effect). The battle menu opens a dialogue with the
enemy's talk dialogue id; the trust increment is the choice's effect, not a rule inside the menu.
Source: genre: knowledge\genre-design.md section 3 (talk options are content, so they are data: label, lines, effect;
four slots at most), re-read 2026-10-19. The duplicate that needs collapsing is internal to specs\05 and specs\07.

T9. specs\07 lists rewards as "god powers, items and health upgrades" but the enemy data fields do not include a drop
table shape.
Fix: enemy data gets `rewards: [{kind, id, count, condition}]` with kind in power, item, health.
Source: genre: knowledge\genre-design.md section 5 (power comes from equipment, found items, story granted abilities
and health upgrades; mercy is not the weaker route), re-read 2026-10-19. The field shape the fix proposes is ours.

T10. specs\09-bullet-pattern-recipes.md has no hazard size, while specs\08 allows 8x8 and 16x16 with a hitbox inset.
The checker cannot validate what it cannot see.
Fix: each spawn frame declares `size` (8 or 16); the hitbox inset of 2 px per side is applied by the arena.
Source: internal: specs\09-bullet-pattern-recipes.md frame fields against specs\08-dodge-arena.md (two hazard sizes
with a hitbox inset). Re-read 2026-10-19.

T11. specs\09 rule 2 requires determinism, rule 7 says one seed per battle, but the fan shape "aims at the marker at
spawn time", which makes the pattern depend on the player. Nothing names the seed source.
Fix: each pattern declares `aim: fixed | at_marker`; the seed is a single integer on the encounter, and the checker
simulates with the marker at box centre for `fixed` and asserts the exclusion radius at each spawn for both modes.
Source: internal: specs\09-bullet-pattern-recipes.md rules 2 and 7 against the fan shape in the same file (aims at the
marker at spawn time). Re-read 2026-10-19.

T12. specs\10-route-ledger.md derives the route "on read and never stored", but its own table needs to know whether
the player is before or after the prison, and no value records that.
Fix: add a `stage` integer to the save (monotonic story stage, advanced by data) and derive the route from counters
plus stage. Otherwise "undecided" becomes "mercy" the moment the counters are zero, which is wrong after the prison.
Source: genre: knowledge\genre-design.md section 4 (the route is coarse, a flag or a small count, and it must be
readable before the payoff), re-read 2026-10-19. The gap, that counters carry no story position, was found internally
in specs\10-route-ledger.md.

## MISSING

M1. No spec defines the data file formats. Every spec points at data ("enemy data", "pattern recipes", "dialogue",
"map"), and nothing says the JSON shape, the version field, the id rules or the cross reference rules. This is the
single biggest gap and it blocks tools\check_data.
Fix: new specs\14-data-formats.md, written from this pass, covering characters, enemies, encounters, patterns, maps,
scenes, dialogue, items, powers, palette, and the rule that ids are lowercase snake_case and unique per kind.
Source: internal: the thirteen files in specs\, read one by one in this pass (2026-10-19): each names data, none
defines its shape. No external source is relevant; this is an absence in our own set.

M2. No spec covers runtime failure of data loading (missing file, bad id, unreadable JSON). The checker catches this
before shipping, but a hand edited build or a bad merge still runs.
Fix: one rule in 14: the game reports the file and the field in plain words on screen and stops, never silently
substitutes a default.
Source: manual: https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/File_Handling/Encoding_And_Hashing/json_parse.htm,
re-read 2026-10-19 (an invalid value or invalid JSON throws an exception error; nesting limit 128; null parses as
undefined). The report in plain words and stop rule is our decision, not a manual rule.

M3. No spec covers the debug build switch itself (`PP_DEBUG` appears in 01 only) or where debug tools live.
Fix: a section in 14 or a new spec 15: one compile time constant, tools behind it, and the rule that a release build
holds no debug draw calls.
Source: internal: specs\01-state-machine.md, the only one of the thirteen that names PP_DEBUG, checked in this pass
(2026-10-19).

M4. No spec covers the title screen content beyond the chapter card in 01 (title slots are deferred to 11, which only
covers the save slot). The vertical slice needs Continue and New Game now.
Fix: thin scope in 01: two entries, Continue visible only when a save exists, New Game warns before overwriting.
Source: internal: specs\01-state-machine.md (chapter card) against specs\11-save.md (the save slot, not the title
entries). Re-read 2026-10-19.

M5. No spec covers the encounter result screen (victory text variants for kill versus spare, the message that lists
rewards). Spec 07 says "30 step victory or defeat, then the result returns" and nothing says what is drawn.
Fix: a small table in 07: three lines maximum, source is dialogue ids per result kind, no numbers on screen.
Source: internal: specs\07-battle-director.md, the 30 step end of fight with nothing said about what is drawn.
Re-read 2026-10-19.

M6. No spec covers audio asset naming and the sound registry, so the checker cannot prove a music id in a scene exists.
Fix: in 14, a `data\audio.json` registry with ids, kind (music, sfx, ui), and a file name the musician lane delivers.
Source: internal: specs\12-audio.md and specs\06-cutscene-runner.md name music and sound ids that no registry in
data\ defines (data\ holds no audio file today). Checked 2026-10-19.

M7. No spec names the resource a god power spends. Spec 07 says POWER uses a god power with a cost from data, and
every mention of a cost resource (will, spirit, focus) is absent from all 13 specs.
Fix: name it in 07 and give the numbers: one pool per party member, refilled to full at the start of every battle so a
battle can always be won without items, and the pool is not carried on the route ledger. The slice implements this as
`will`, with `will_max` on the character and `cost` on the power, and records it here because the spec does not.
Source: internal: specs\07-battle-director.md (POWER cost from data) with no cost resource in any of the thirteen
specs, checked in this pass (2026-10-19).

M8. No spec says what happens to party health after a defeat. Spec 07 records the fight result and spec 01 sends the
player to the title (rule 6), but nothing says whether hp is restored, and a ledger written with the hp the fight ended
on would carry 0 into the next battle.
Fix as implemented for the slice: a defeat does not record a result and does not write the hp the fight ended on. The
party is restored to max hp and the app returns to the overworld, because the title and save modes that spec 01 names
do not exist yet; when they do, this becomes the save restore point and rule 6 is implemented as written.
game\scripts\pp_battle_director.gml carries the decision at pp_battle_record, and tests\test_project.py pins the order:
restore first, ledger write second.
Source: internal: specs\01-state-machine.md rules 5 and 6, specs\07-battle-director.md result recording, and
specs\11-save.md 11.4, none of which name post defeat health. Checked 2026-10-19.

## What this pass did NOT touch

The numbers that the specs already fix are all kept as written: 256x240, integer scale 1 to 6, 60 steps per second,
12 step fades, 16x16 tiles, 160x100 dodge box, 8x8 marker at 2 px per step, 30 step invulnerability, 2 steps per
character, 30 character lines (C4 disputes the arithmetic behind that one and recommends 28; the number is listed here
as the spec states it, not as endorsed), 3 line pages, 900 step phase cap, 54 colour palette, 16 colours on screen.
No spec was rewritten; every item above is a proposal with a recommended fix.
