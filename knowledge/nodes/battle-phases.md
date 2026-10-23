# Node: battle state machine and turn flow

Parent doctrine: `knowledge/FOX-STYLE.md` section 1 (battle state machine) and section 4 (battlefield
layout and turn flow). Specs: `specs/07-battle-director.md` (the battle spec),
`specs/08-dodge-arena.md`, `specs/09-bullet-pattern-recipes.md`, `specs/18-boss-phases.md`.

There is no `specs/01-battle.md`. The file numbered 01 is `specs/01-state-machine.md`, which owns the
application's mode list (boot, title, overworld, cutscene, battle, menu), not the fight. The fight's spec
is 07.

Code read: `game/scripts/pp_battle_director/pp_battle_director.gml` (1119 lines),
`game/scripts/pp_dodge_arena/pp_dodge_arena.gml` (249 lines),
`game/scripts/pp_dodge_recipe/pp_dodge_recipe.gml`,
`game/scripts/pp_battle_commands/pp_battle_commands.gml`,
`game/scripts/pp_battle_text/pp_battle_text.gml`, `game/scripts/pp_config/pp_config.gml`,
`game/scripts/pp_app/pp_app.gml` (mode battle), `game/scripts/pp_input/pp_input.gml` (movement vector).

Data read: `data/encounters/all.json`, `data/enemies/all.json`, `data/patterns/all.json`,
`data/characters/party.json`, `data/items.json`, `data/powers.json`, `data/audio.json`.

Reading rule for this page: every number is a macro in `pp_config.gml` or a value in one of those data
rows. A duration marked derived is arithmetic over those values and has not been timed on a build, so how
it feels is unmeasured. Anything the files do not state says unmeasured.

---

## 1. The phase set

One struct, one phase value, eight phases. The enum is `PPBattlePhase` in `pp_config.gml:77-86`, so no
bare number appears in the machine.

| value | phase | what the player sees | how it ends |
| --- | --- | --- | --- |
| 0 | intro | the fight frame with a 0.7 alpha flash over it, on for 4 steps and off for 4, for 30 steps | step 42 |
| 1 | menu | five command entries in the lower band, a triangle on the cursor, a reason line under the band when an entry is refused | an enabled entry is confirmed |
| 2 | resolve | the FIGHT timing bar sweeping across the field, letter Z under it | a confirm press, or 120 steps |
| 3 | message | a paper window over the top 48 pixels, typing out one line at a time | the board reaches its end |
| 4 | telegraph | the words "here it comes" at the field centre | 12 steps |
| 5 | dodge | the field dimmed, a 160 by 100 box, a bright marker, falling hazards | the arena reports ended |
| 6 | result | the outcome dialogue, then a 30 step beat; a defeat replaces the beat with a 12 step fade and the game over card | 30 steps, or a game over choice |
| 7 | ended | the outcome word and "press Z" in a panel drawn by `pp_app` | a confirm press, or no press at all on a story handoff |

Notes a card writer needs:

- The last phase is `ended` in the enum (`pp_config.gml:85`). FOX-STYLE section 1 calls it `ending`. Same
  phase, one word apart; use `ended` when naming code.
- `ended` is the one phase with no step function. `pp_battle_step` has `case PPBattlePhase.ended: break;`
  (`pp_battle_director.gml:187`). The screen belongs to `pp_app` from that point, which draws the outcome
  word and the prompt (`pp_app.gml:408-415`).
- There is no timer that jumps the machine. Every phase ends when a condition inside its own step function
  is met, and only `pp_battle_phase_set` writes the value.

## 2. What moves the machine from one phase to the next

The door: `pp_battle_phase_set` (`pp_battle_director.gml:164-171`) writes `phase`, resets `phase_steps` to
0, and prints the change when `PP_DEBUG`. A grep over `game/scripts` finds exactly one `.phase =` in this
module (`:165`); the other writes belong to `pp_title`, which is a different state machine.

Transitions, in the order the code tests them:

1. intro -> message: at exactly `PP_INTRO_FLASH_STEPS + PP_FRAME_SLIDE_STEPS` (30 + 12 = 42) the
   encounter's `intro_dialogue` is opened as a board whose close action is "menu"
   (`pp_battle_step_intro`, `:192-198`). The test is equality, not a greater than, so a skipped step would
   stall the fight here. Nothing skips steps today.
2. intro -> menu: the same step 42, when the encounter names no intro dialogue. All three demo rows name
   one (`battle_intro_sailors`, `battle_intro_hound`, `percy_entry`), so the first transition is the one
   every demo fight takes.
3. menu -> resolve: FIGHT confirmed and enabled. `turn` is incremented first (`:221`), then
   `pp_battle_begin_action` opens the timing bar.
4. menu -> message: POWER and ITEM resolve at once and open a board. TALK opens its three option panel,
   which is a second shape of the menu phase and not a phase of its own: `pp_battle_step_menu` hands the
   step to `pp_talk_step` while `talk_stage` is set (`:203-206`, `pp_battle_text.gml:525`).
5. menu -> result: SPARE, either accepted (`pp_battle_spare_allowed`) or refused inside the enemy's
   interrupt window (`pp_battle_interrupt_ready`, `:266-272`).
6. menu -> menu: a refused entry never advances the turn. It sets `cursor_note` for 30 steps and returns
   (`:214-219`). No press leaves the phase.
7. resolve -> message: the bar stops, damage lands, the board says what the blow did (`:288-305`).
8. message -> anything: `pp_battle_after_message` (`:347-383`) is the whole of the turn flow after a board
   closes, and it tests in this order:
   1. close action "_closing" -> result. This is the outcome board, checked first so it cannot re-enter.
   2. close action "result" -> the result beat through `pp_battle_enter_result`.
   3. `defeated`, or a result already set -> the result beat, whatever the close action said.
   4. close action "enemy_turn" -> the boss phase line once if a crossing queued one, then the attack roll,
      then telegraph.
   5. close action "menu", or anything else -> menu.
9. telegraph -> dodge: after `PP_TELEGRAPH_STEPS` (12) the director picks a pattern from `pattern_pool`
   with the fight's own rng, builds a fresh arena, and switches (`:386-396`).
10. telegraph -> menu: when `pattern_pool` is empty, the enemy takes no turn at all, the menu returns on the
    same step, and nothing is said about it (`:389-392`).
11. dodge -> menu: the arena reports ended and the party is still standing (`:432`).
12. dodge -> result: the arena reports ended and the party's health is 0. `defeated` is set first, so the
    result phase becomes the game over screen (`:427-430`).
13. result -> ended: 30 steps (`PP_RESULT_STEPS`, `:602-604`), unless the fight was lost.
14. ended -> overworld: `pp_app` waits for a confirm press, or leaves with no press when the fight hands a
    scene id over (`pp_app.gml:372-394`). Today only the interruption ending hands a scene over.

Input is edge triggered with a release gate (`pp_pressed`, `pp_action`), and menu cursors use press plus
repeat through `pp_menu_axis` (`pp_input.gml:194-201`), so one held key cannot carry a confirm out of one
phase and into the next.

## 3. Enemy phase timing

Two things in this project are called the enemy's phase, and they are different mechanisms:

- the enemy turn: the roll, the telegraph and the dodge arena, which follows every accepted command;
- the boss phase rows: hp thresholds in the enemy's `phases` array (spec 18) that widen the fight as the
  enemy is worn down.

The enemy turn is four beats and no more:

1. Roll. At the close of the player's board, `pp_battle_roll_attack` (`:410-415`) takes one integer from the
   fight's rng inside `attack_range`. That range starts as the enemy row's `attack` and changes only when a
   boss phase row names its own. The number is fixed before the telegraph, so the warning the player sees
   already has a value behind it.
2. Telegraph. `PP_TELEGRAPH_STEPS` 12 steps, 0.2 s at `PP_STEPS_PER_SECOND` 60, with "here it comes" drawn
   at the field centre (`:981-983`).
3. Arena warning. The box's first `PP_ARENA_WARN_STEPS` 12 steps, another 0.2 s: the border changes colour
   every 3 steps (`pp_dodge_arena.gml:100-103` and `:206-208`) and no hazard exists yet.
4. Recipe. Spawns fire at each frame's `at` step, members of a group spaced by `delay`
   (`pp_dodge_recipe.gml:65-90`, `:118-134`). The phase ends when the emitter is done and zero hazards are
   alive, or at `PP_ARENA_CAP_STEPS` 900 steps (15 s) so a bad recipe cannot trap the player.

Derived phase length, from the recipe rows in `data/patterns/all.json` and the end condition in
`pp_arena_step`: 12 warning steps, plus whichever is later, the recipe's `length` or the last spawn step
plus that hazard's `life`. Nobody has timed a phase on a build, so the seconds are arithmetic only.

| pattern | length | last spawn (at + delay) | hazard life | derived phase | in seconds |
| --- | --- | --- | --- | --- | --- |
| `tutorial_slow_rain` | 240 | 210 | 100 | about 322 steps | about 5.4 |
| `percy_rain` | 340 | 300 | 80 | about 392 steps | about 6.5 |
| `percy_wall` | 380 | 210 + 2 x 4 = 218 | 120 | about 392 steps | about 6.5 |
| `percy_fan` | 380 | 210 + 2 x 2 = 214 | 120 | about 392 steps | about 6.5 |

The two wall rows are pinned by their recipe length rather than by their hazards: the last hazard is gone
long before step 380. A hazard that leaves the box entirely for 12 steps is retired early
(`pp_dodge_arena.gml:160-167`), so a real phase can only be shorter than the table, never longer, unless
it hits the 900 step cap.

Three consequences a designer should know:

- There is no beat after the pattern. Spec 07's turn flow says telegraph, pattern, "then 20 steps", and the
  code goes from the last hazard straight back to the menu on that same step, with the arena dropped.
  `PP_MESSAGE_STEPS` 20 is defined at `pp_config.gml:56` and read by nothing in the tree.
- Fairness rule 3 of spec 08, "no hazard spawns in the last 12 steps of a pattern", is not enforced by
  code. `pp_recipe_step` spawns every event at its own step and `pp_arena_step` has no tail guard. Current
  data is safe by margin: the latest spawn is 218 of 380, 300 of 340 and 210 of 240. Nothing stops a future
  recipe from breaking the rule.
- Spec 09 rule 5 describes the phase as "length plus the longest hazard life". The code ends at the later
  of the recipe length and the last hazard's death, which is the same number whenever the longest-lived
  hazard is also the last one spawned. It is a different number when an early hazard lives longer.

Boss phase rows, the second thing called a phase. A row is entered when `enemy_hp * 100 <= hp_at_or_below *
max_hp`, compared in integers (`:117-119`), applied in data order, once each, from
`pp_battle_enemy_phase_sync` (`:125-137`). A row can append one pattern to the pool, set the attack range,
set the TALK set and queue one line, and the line plays once before the enemy's turn. A blow that ends the
fight crosses nothing, because the kill is checked first and the sync is skipped when the enemy is at 0
(`:318-320`). In the demo data only Percy has rows, at 70 percent and at 40 percent, and only Percy has an
interrupt block, at 40 percent of 120 hp.

## 4. What clears the arena

One line does it: `pp_battle_step_dodge` sets `_battle.arena = undefined` when the arena reports ended
(`pp_battle_director.gml:426`), before it decides between the menu and a defeat. There is no other clearing
path and no clear function anywhere in the tree.

- Every enemy turn builds a fresh arena at the end of the telegraph, replacing whatever the struct held, so
  the previous arena is dropped even in the impossible case that one survived.
- Hazards are plain structs in `arena.hazards` (`pp_dodge_arena.gml:37`, `:56-60`). They are destroyed with
  the arena struct, so nothing is spawned as an instance and nothing can leak past the phase. That is
  FOX-STYLE law 5 satisfied without a teardown call.
- The cost of that shape: anything a future change adds outside the arena struct (an instance, a looping
  sound, a surface) would not be cleared by this one line. Idle cost today.
- On a defeat the arena is cleared before the result phase, so the 12 step game over fade draws the last
  fight frame without a box over it.
- `cleared`, `capped` and `hits` are computed inside `pp_arena_step` (`pp_dodge_arena.gml:110-125`) and read
  by nobody. Two visible effects follow: the arena plays no sound on a hit or on a clean run, and the
  "clear" plate `pp_arena_draw` draws can never be seen, because the arena is drawn only during the dodge
  phase (`pp_battle_director.gml:942-944`) and is dropped on the same step the phase ends.

Arena geometry, for reference, all in `pp_config.gml:41-51`: a 160 by 100 box centred at (128, 120), so
x 48 to 208 and y 70 to 170; an 8 by 8 marker starting at the box centre every phase; 4 step trail; marker
speed 2 pixels per step along a normalised input vector, clamped at the border
(`pp_input.gml:181-190`); hitboxes 2 pixels in per side on both bodies (`PP_HITBOX_INSET`); no spawn within
24 pixels of the marker, enforced by pushing the spawn out to the radius rather than skipping it
(`pp_arena_fit_spawn`); 30 steps of invulnerability with the marker blinking every 4.

The box's bottom edge at 170 sits 2 pixels below the command band's top at `PP_MENU_TOP` 168. The draw order
handles it: the arena is drawn before the band (`pp_battle_director.gml:939-944`), so the band covers the
overhang instead of the overhang covering the band's border.

## 5. How a turn resolves

A turn is one accepted command plus the enemy's answer. `turn` is a counter, incremented once per accepted
command and never reset inside a fight; it is not a round and not a queue. It is written into the exit row
as that row's `round` (`pp_battle_record`, `:449-456`, into `pp_ledger_record_exit`, `pp_ledger.gml:54-58`).

The five commands, with the numbers in force today:

- FIGHT. The bar starts at 0, moves 100/60 (about 1.667) per step, reflects at 100 and at 0, and presses
  itself at 120 steps, which is two full sweeps and 2 s (`:288-305`). Power is
  `round(100 - abs(bar_pos - 50) * 2)`, so 100 at the bullseye and 0 at either end. Damage is
  `max(1, round((2 + 10 * power / 100) * power_multiplier))` from `PP_FIGHT_DAMAGE_MIN` 2,
  `PP_FIGHT_DAMAGE_MAX` 12 and the party's multiplier, which is 1.0 in `data/characters/party.json`
  (`pp_battle_fight_damage`, `:308-312`). So a perfect press deals 12 and a wild one deals 2.
- POWER. Spends the first power in the list, pays its `cost` from will, and deals its flat `power` value.
  `tide_step` in `data/powers.json` costs 1 will and deals 6. The party starts with `will_max` 3, so three
  uses per fight until a power curve changes that.
- TALK. Raises `trust` by the encounter's `trust_per_talk`, 1 in all three demo rows, then opens a three
  option panel from the talk bake or the card's own pool (`pp_talk_begin`, `pp_battle_text.gml:513-523`).
  The picked reply becomes the board and the enemy answers as it does after a FIGHT.
- ITEM. Uses the first item, heals its `heal`, deletes one copy. `salve` heals 6 and the party starts with
  2 (`data/items.json`, `data/characters/party.json`). No submenu.
- SPARE. Accepted when `trust` reaches `trust_to_spare` (3) or enemy health is at or below
  `spare_hp_percent` (25 percent of max) (`pp_battle_spare_allowed`, `:641-645`). An accepted spare sets
  enemy health to 0 for the bar but is recorded as a spare.

Every command is charged a turn, the gentle ones included: the increment happens before the action resolves
(`:221`), so a TALK, an ITEM and an accepted SPARE all move the counter. The one comment that disagrees is
covered in section 6.

The four ways a fight ends:

- kill: enemy health reaches 0 from a command. Recorded as `kill`; the exit row is `down`.
- spare: SPARE is accepted. Recorded as `spare`; the exit row is `spared`.
- interrupt: a SPARE press is refused while enemy health is at or below the enemy's `interrupt` threshold
  (`pp_battle_interrupt_ready`, `:667-680`). Recorded as `turned`, no counter moves, no closing board, and
  the caller continues with no press. The `unless_flag` field makes it a once-only story beat.
- defeat: party health reaches 0 in the dodge phase. No exit row is written and the run's ledger is left
  alone, because the honest health after a loss is the one in the save (`pp_battle_record`, `:458-469`).
  The fight's own actor is put back to full so nothing downstream reads a 0 that no one restores.

Recording happens once, guarded by `recorded`, on the way into the result phase, before the outcome lines
are chosen from the encounter row (`win_dialogue_kill`, `win_dialogue_spare`, `lose_dialogue`).

One order of events matters for the last blow: `pp_battle_after_message` tests `defeated` and a set result
before it tests "enemy_turn" (`:361-364`), so a killing blow goes from the player's board straight to the
result beat. The enemy does not answer a blow that ended the fight.

## 6. Conformance against FOX-STYLE section 1

Conforms:

1. One owner. The fight is one struct in `global.pp.battle`, created only in `pp_mode_battle.enter`
   (`pp_app.gml:353-370`) and stepped only from `pp_mode_battle.step` (`pp_app.gml:394`). No other module
   holds or advances it.
2. Mode is data. `PPBattlePhase` is an enum (`pp_config.gml:77-86`), dispatched by one switch in
   `pp_battle_step` (`:179-188`). No bare phase numbers.
3. One step function per phase, and one door for the change. `pp_battle_phase_set` is that door, and it also
   owns the step reset, which is what makes debug output and `phase_steps` trustworthy.
4. The turn order the code can express, party then enemy, is the order spec 07 rule 3 fixes, and no speed
   stat exists anywhere.
5. Every command costs a turn, including the peaceful ones (`:221`).
6. An enemy's shape is data, not code: `phases` rows and the `interrupt` block are read off the row without
   anything in the director branching on an enemy id (`pp_battle_enemy_phase_sync`, `:125-137`,
   `pp_battle_interrupt_block`, `:659-662`). The pattern pool is a copy per fight
   (`pp_battle_pattern_pool`, `:101-106`), so a second fight against the same enemy starts clean.

Diverges:

1. There is no turn queue. The struct has `turn` (a counter) and no `turn_queue`, `turn_index` or `round`
   (`:29-31`), while section 1 says the command phase iterates a queue built at round start. A grep for all
   three names over `game/scripts`, `data/` and `specs/` returns nothing. The single enemy scope is why this
   holds today: `pp_mode_battle.enter` reads `_enc.enemies[0]` and nothing else (`pp_app.gml:361`), so a
   second enemy row in an encounter is silently ignored, and a party of more than one is not expressible
   either.
2. The struct does not carry the doctrine's field names. No `enemies` array (one `enemy`), no `party_view`
   (one `actor`), no `pattern_runner` (the emitter sits inside the arena struct,
   `pp_dodge_arena.gml:34`), and no `timers` struct: timing is five loose step counters, `phase_steps`,
   `popup_steps`, `cursor_note_steps`, `bar_steps` and `gameover_note_steps`.
3. The encounter row names two of the four things section 1 lists. It names the enemy rows and the music,
   plus a seed, dialogue ids and pacing. It names no arena id and no party layout case. The arena is the
   fixed box in `pp_config`, the party layout is one case in the draw code, and the `music` id is read by
   nothing: `pp_mode_battle` plays `encounter_swoosh` and starts no theme (`pp_app.gml:370`), so a fight
   keeps whatever the map was playing. `data/audio.json` carries PP-04 for the two ship fights and PP-06 for
   Percy, and no battle code asks for either.
4. The enemy row carries no defence field. Section 1 says enemy rows carry name, health, attack, defence,
   the resolve threshold and the act list; `data/enemies/all.json` has `max_hp`, `attack` as a min and max
   pair, `trust_to_spare`, `spare_hp_percent`, `patterns` and `phases`, and no defence, so no incoming
   damage term exists to tune. Spec 07 also does not list defence, so the doctrine is the only place that
   asks for it.
5. The last phase is `ended`, not `ending` (`pp_config.gml:85`). Harmless, but a card written against the
   doctrine will not find the name.
6. One comment contradicts the counter. The interrupt branch says the turn is not spent
   (`:266-269`) after `pp_battle_step_menu` has already incremented `turn` at `:221`. What the player feels
   is unchanged, because the fight is over; the only visible effect is the round number in that fight's
   exit row.

## 7. Conformance against FOX-STYLE section 4

Conforms:

1. Party on the left, enemy on the right, band under both. The hero block is x 40 to 72, the enemy block
   x 176 to 224, and the command band starts at `PP_MENU_TOP` 168 (`:907-915`, `pp_config.gml:38`).
2. One text origin. Every battle message goes through `pp_text_board_draw` at (16, 16) inside a cell
   aligned window from 0 to 256 by 0 to 48 (`:789-792`, `:958-973`), and `pp_battle_text` is a layout over
   the single reveal machine in `pp_text` (`pp_battle_text.gml:1-7`), which closes the two typewriters gap
   that `knowledge/FOX-STYLE-AUDIT.md` section 3a recorded.
3. The fixed turn flow is present in order for the surviving path: intro, command, resolve, dodge, damage
   and exit recorded, then the next round or the result. Party damage only ever comes from arena hits
   (`:420-424`), so there is no "the enemy simply deals numbers" fallback.
4. Every command costs a turn, described in section 5.

Diverges:

1. The dodge phase does not always run, and section 4 says it always does. A blow that takes the enemy to 0
   goes from the player's board straight to the result phase (section 5), so there is no telegraph and no
   enemy answer. Spec 07 acceptance 1 says a FIGHT win always gets a dodge in reply, and
   `tests/test_first_fight.py` records the conflict in its docstring (`:38-40`) and deliberately asserts
   neither side. It is not an edge case in the demo: `deck_hound` has 2 hp and the minimum FIGHT damage is
   2, so the first fight's kill can never show a dodge.
2. There is no layout module. `pp_battle_layout`, `arena_top`, `arena_bottom`, `party_x`, `enemy_x`,
   `party_rows`, `text_origin` and `face_offset` appear nowhere in `game/`, `data/`, `specs/` or
   `knowledge/` outside `FOX-STYLE.md` itself. Positions are literal rectangles in `pp_battle_draw`
   (hero `40, 96, 72, 144`; enemy `176, 72, 224, 136`; name at y 56; health bar `168, 144, 232, 148`;
   party text at y 156), and the party placement is one case, not three by party size.
3. There is no per encounter layout override. No row in `data/encounters/all.json` has a `layout` field, so
   the boss arena override section 4 describes cannot be authored, and no code reads such a field.
4. Two authored beats are not drawn. The 12 step frame slide is 12 steps of nothing: the intro's only
   animation is the flash for the first 30 steps, and steps 30 to 41 change nothing on screen. The 30 step
   flash is drawn as 4 on and 4 off, so the player sees about four flashes rather than a countdown.
5. The message phase has no 20 step floor. `PP_MESSAGE_STEPS` 20 (`pp_config.gml:56`) is read by nothing. A
   board lasts as long as its text takes: 2 steps per character at `PP_TEXT_STEPS_SLOW`, 1 while confirm is
   held, 8 extra steps after a full stop, 3 after a comma, and an 8 step gap between lines
   (`pp_text.gml:77-160`). A short board is over in well under a second, which is where a fight can feel
   faster than spec 07 describes.
6. Dodge feedback is missing at the director's end. `pp_arena_step` flashes the border for 6 steps but plays
   nothing; `data/audio.json` defines `hit`, `chime` and `game_over` cues and no battle script calls any of
   them; the party's health is text only (`:927`), so spec 08's 12 step health bar animation has nothing to
   animate; and the "clear" plate cannot be seen, as described in section 4.
7. Enemy damage has no floor of 1. `pp_battle_step_dodge` subtracts `arena.attack` directly (`:421`), while
   spec 08 says a hit costs the attack value, minimum 1. Both demo rows roll at least 2, so play is correct
   today; a row with a `min` of 0 would deal nothing.
8. The command band is silent. `pp_command_move` (`pp_battle_commands.gml:64-70`) plays no `menu_move`, and
   the refused entry branch (`pp_battle_director.gml:214-219`) plays no low blip, while spec 07 rule 1 asks
   for one and the comment above that branch already claims the refusal is "visible and audible". The game
   over card does play `menu_move`, `menu_select` and `menu_cancel`, so the two menus in the same fight
   disagree about sound.
9. One stale comment misdescribes the ending. `pp_app.gml:384-385` still says a defeat returns to the
   overworld with the party restored. A defeat never reaches `ended`; it holds the result phase and shows
   the game over card, whose only roads are CONTINUE (restore the last save through `pp_save_apply`) and
   RETURN TO TITLE (`:510-575`). Anything read from that comment will build the wrong screen.

## 8. Where a designer changes these numbers

- `game/scripts/pp_config/pp_config.gml`: intro flash 30 and slide 12, telegraph 12, result 30, damage
  popup 24, bar sweep 60, damage 2 to 12, arena box 160 by 100 at (128, 120), marker 8 at speed 2, hit
  inset 2, invulnerability 30, spawn exclusion 24, arena warning 12, arena cap 900, menu band 168. The
  message hold `PP_MESSAGE_STEPS` 20 is here and unused.
- `data/enemies/all.json`: health, attack range, patterns, `phases` rows, `trust_to_spare`,
  `spare_hp_percent`, the `interrupt` block, the talk set, `route_kind`.
- `data/encounters/all.json`: which enemy, the seed, the dialogue ids, `trust_per_talk`, route refusal,
  pacing. Music is named here and not played.
- `data/patterns/all.json`: the shape of the enemy's answer, which is the only thing the player's dodging
  skill reads.
- `data/characters/party.json`, `data/items.json`, `data/powers.json`: party health, will, items and the
  power curve.

## 9. What to fix first, in the order that changes play most

1. Let the dodge run on a killing blow, or change spec 07 acceptance 1 and FOX-STYLE section 4 to say a kill
   ends the fight. Today the code and the doctrine disagree and the code wins silently, and the first fight
   in the demo is the case where it shows.
2. Give the dodge phase its feedback: the `hit` and `chime` cues, the clear plate held long enough to read,
   and a party health bar, or strike those lines from spec 08.
3. Draw the 12 step slide in, and either implement the 20 step message hold or delete `PP_MESSAGE_STEPS` so
   no card believes it exists.
4. Name the layout: create `pp_battle_layout` with the fields section 4 lists, or amend section 4 to the
   literals in `pp_battle_draw`. One of the two, so the next arena sized screen has a place to live.
5. Delete the stale defeat comment in `pp_app.gml:384-385` and the "audible" claim in
   `pp_battle_director.gml:215`, or make both true.
6. Add the turn queue only when a second actor exists. Until then, record in FOX-STYLE section 1 that the
   queue is deferred with the single enemy scope, so it stops reading as a missing implementation.
