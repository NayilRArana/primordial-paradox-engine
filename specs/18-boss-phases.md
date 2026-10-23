# Spec 18: boss phases and rule changes

Status: spec, 2026-10-22. No code yet. Numbers are DECISIONS.
Card: t_92ee7b8e, step S6 of `ROADMAP-2026-10-22.md`. This is the spec `knowledge/mechanics/ACTION-MECHANICS.md`
section 10 names as NEW spec 18; the decisions it turns into data are RUL-01 to RUL-07 (section 5), PHS-01 to PHS-04
(section 9) and FAI-01 (section 8) of that study. Specs read for it: 06 cutscene runner, 07 battle director, 08 dodge
arena, 09 bullet pattern recipes, 10 route ledger, 12 audio. Section 8 was answered by gamedev on card t_00a94c86.

Goal: a boss is one enemy row with phases in percent of max hp, and a phase may change exactly one rule by naming one of
five data fields. Nothing about a phase lives in code. The director reads the row, asks the arena for the phase's
pattern, and hands the fight to a scene when a row says the fight stops. Every rule change is named on screen for 24
steps, because a rule change the player cannot name reads as a bug. No phase ever asks the player to learn a new rule
and a new hazard shape at the same moment.

## 0. What this changes in the specs that already exist

1. Spec 08 fixes the box at 160x100 and the marker at 2 pixels per step, and puts "a second marker" out of scope. This
   spec adds the three fields that move those constants (`box_scale`, `marker_speed`, `marker_count`) and the gates
   that keep them rare. Spec 08 is not edited: where they disagree, this spec wins for a boss phase and spec 08 wins
   everywhere else.
2. Spec 08 already says the marker starts at the box centre every phase. That sentence is what makes a narrower box
   safe without a transition animation, and it is the skeleton's re-centre rule.
3. Spec 07's enemy data gains two blocks: `phases` (at most 4 rows) and `interrupt` (at most 1). The enemy's own
   `patterns` list stays and is phase 1's pool.
4. Spec 07 rule 7 (the director asks spec 08 for a pattern and never spawns hazards itself) is unchanged, and it is
   the reason the interruption is a scene hook and not an arena feature.
5. Spec 06 rule 6 (a scene that ends with a battle unresolved is a checker error) is satisfied by making
   `interrupted` a resolved result with its own exit row. No new command is needed: the interrupting scene is where
   the branching happens.
6. Spec 10 rule 7 already has the vocabulary: `turned` is "the fight stopped and a scene took over", it moves no
   counter and keeps its row. The interruption writes that row.
7. Spec 12 puts "layered dynamic music" out of scope, so the skeleton asks for a per phase CUE id, not a layer (A18-2).
8. Spec 09's determinism (one seed per battle), its 900 step cap and its concurrency ladder are inherited unchanged.
   A phase never reseeds and never resets a pattern's length.
9. The interruption is not triggered by an hp crossing (A18-1). This is a change of mechanism from the study's own
   wording, and section 4 carries the arithmetic that forces it: a 120 hp boss with an interrupt above 9 percent of its
   hp cannot be killed by FIGHT at all, and 14 percent is the same wall once `tide_step` is spent.

## 1. The phase skeleton

Phase 1 is the enemy row itself: hp above the first breakpoint, patterns equal to the enemy's `patterns`, every rule
field at its default, no break on entry, no label, cue variant 1.

Every later row is entered when the enemy's hp first satisfies `hp * 100 <= hp_at_or_below * max_hp`. The integer
compare matters: no float, no rounding, the same crossing on every machine.

| Part | Rule | Number |
| --- | --- | --- |
| HP breakpoint | percent of `max_hp`, compared as `hp * 100 <= threshold * max_hp` | integer 1 to 99, strictly descending, at most 4 rows |
| Break | starts after the player's damage message (spec 07's 20 steps) and before the enemy's turn | 30 steps, fixed, cannot be skipped or shortened |
| Hazards in the break | every hazard despawns at break step 0; none spawns before step 30 | 0 hazards on screen for the 30 steps |
| Marker in the break | teleports to the new box centre at break step 0 and is frozen; input is read and discarded | full control returns at step 30 |
| Box in the break | redrawn at the new `box_scale` at break step 0, 2 pixel frame, 1 pixel dark line outside (spec 08) | centre stays (128, 120) |
| Warning | the new phase's first pattern gets spec 08's 12 step warning as the last 12 steps of the break | break steps 18 to 29 |
| Music | the new phase's cue variant is requested at break step 0 and crossfaded over 30 steps (spec 06's number). A request that resolves to the sound already playing is a no-op, never a restart (A18-2) | in place at break step 30 |
| Health | nothing heals, nothing is restored, no message, no menu, no save | spec 07 health unchanged |
| Cap | 900 steps per phase (spec 08 rule 5) | unchanged |
| Pattern order | on entry the pool cursor is set to the pattern this row adds, then the pool cycles in data order | deterministic per battle seed (spec 09 rule 7) |
| Fight state | the player's hp, the trust meter, the item count and the arena's seed all carry across the break | nothing resets except the marker's position |

Why the break is 30 steps with the warning inside it: 30 steps is half a second at 60 steps per second, which is long
enough to read a 12 character label and short enough not to feel like a cutscene. Putting the warning window inside the
break rather than after it means a phase change costs 30 steps, not 42, and the player still gets spec 08's full
warning: the border flashes twice with no hazard on screen.

Why the marker is frozen and not animated: a marker that slides or accepts input while the box changes size is how a
player ends up outside their own box through no decision of their own. Spec 08 already re-centres the marker every
phase, so a teleport is the existing rule, not a new one.

## 2. The rule change fields

A rule change is one of the five fields below moving away from the value the phase inherited. A phase changes at most
one of them (section 5 checks it). An absent field means inherited; a rule never silently resets to its default in the
middle of a fight.

| Field | Type | Legal range | Phase 1 default | What the player feels |
| --- | --- | --- | --- | --- |
| `box_scale` | array of exactly 2 integers, `[width_percent, height_percent]` | width 50 to 100 in steps of 5, height 50 to 100 in steps of 2, each component may only go DOWN from the previous phase | `[100, 100]` | the corridor narrows |
| `marker_speed` | number, pixels per step, in steps of 0.25 | 1.00 to 3.00 | 2.00 (spec 08) | the marker answers faster or slower |
| `invert` | string enum | `"none"` or `"horizontal"` | `"none"` | left and right swap |
| `marker_count` | integer | 1 or 2; 2 only on `route_kind: boss` and only when the derived route is `blooded` or `genocide` (A18-3) | 1 | two markers, one input |
| `hazard_mode` | string enum | `"dodge"` or `"clearable"`; `"clearable"` is refused in demo data | `"dodge"` | hazards are only ever dodged |

Every field is optional in a phase row; the five permitted values above are the whole legal set, and a value outside a
range is a checker error that names the field, the row and the legal set (section 7).

### 2.1 `box_scale`

The box is mirrored from spec 08's 160x100 at centre (128, 120): width `160 * width_percent / 100`, height
`100 * height_percent / 100`, frame 2 pixels inside and a 1 pixel dark line outside. Both results are even integers by
construction (`160 * w / 100` is `8 * (w / 5)`, even for every legal `w`; `100 * h / 100` is `h`, so `h` is required
even). The narrowest legal box is 80x50, which still holds an 8x8 marker with room on every side and stays inside the
256x240 frame with its frame and outline.

Two axes and not one scalar: the study's corridor is 128 x 100, which is 0.8 across and 1.0 down. A single scalar
would give 128 x 80 and take away vertical dodge room the patterns were authored for.

A box may only narrow. A widening phase is refused, because the study's rule changes all tighten and because a phase
that gives space back would have to be read as mercy by the player while the bullets say otherwise.

### 2.2 `marker_speed`

The value replaces spec 08's fixed 2 pixels per step for the phase. The slow key that spec 08 gains (1 pixel per step)
is unaffected and stays available in every phase, because taking an input away is a different rule change and the study
asks for it only where it says so.

Ceiling 3.00: the narrowest legal box is 80 pixels wide, which leaves the 8 pixel marker 72 pixels of centre travel, so
at 3 pixels per step it crosses the box in 24 steps. A 12 step warning then stops being long enough to read before the
marker can reach a wall. Floor 1.00: below that the marker moves slower than the slowest hazard in the data, which
turns a dodge into a coin flip.

### 2.3 `invert`

Input is sampled and normalised exactly as spec 02 rule 5 says (8 directions, one vector), and then the x component is
negated inside the arena, for the dodge phase only. Menus, the menu cursor, TALK, the overworld and every other mode
keep the unflipped map, so a player who is inverted in the box is not inverted in the menu they open next.

The persistent signal, for the whole phase and not only the 24 label steps, is the marker's 4 step trail drawn in the
highlight ink instead of the dim ink. No new sprite is introduced by this spec: art stays spec 13's and the trail
already exists in spec 08.

### 2.4 `marker_count`

`2` is the mirrored pair the study gives Kronos. The contract, because a field without one is code inventing it:

| Part | Rule |
| --- | --- |
| Geometry | pair mirrored about the box's vertical centre line: marker A at `(cx - dx, cy + dy)`, marker B at `(cx + dx, cy + dy)` |
| One input | the spec 02 vector moves A directly and B with its x component negated |
| Clamp | each marker clamps independently to the box's inner edge |
| Trail | each marker carries its own 4 step trail (spec 08) |
| A hit | one hit costs one attack value no matter how many markers or hazards overlap; the 30 step i-frames are shared by the pair |
| Health | there is one health bar, so "both must survive" means the player must keep both clear, not that there are two pools |
| Phase change | both re-centre, which for the pair means `dx = 0` and they overlap until the first input separates them |
| Death | `dx = 0` at recentre cannot be hit twice: the shared i-frames and the one hit per step rule (spec 08 rule 4) both hold |

`2` is refused on a regular enemy, because two markers against a tutorial sailor is not a lesson, and refused on the
`undecided` and `mercy` routes, because the study gives the split marker to the player who has already killed (its
section 9 hands it to blooded and genocide) and leaves the genocide ending open (A18-3: it gets the pair too). A phase
row that must enter on some routes and not others carries `route_gate`, a list of route keys, and section 5 runs its
checks on each route's own phase list.

### 2.5 `hazard_mode`

`"dodge"` is spec 08 as written: no hazard can be destroyed, cleared, reflected or grazed away, and the marker's only
verb is to move. This is the whole demo, and it is the study's own mapping of the ancestor's "no fire button" row.

`"clearable"` is a reserved value, legal in the type and refused in data. It exists so that the day a spec defines a
clearing effect (a god power with a clear effect, or a whip that cuts hazards) the change is a data edit rather than a
code path. Today no spec defines such an effect: `data/powers.json` holds one power and its effect is `attack`. A value
nobody has specified must not be authorable, so the checker refuses it and names the missing spec.

## 3. The label rule

A rule change is named on screen, and the words are a function of the field and its direction. The label text is never
authored in data: the checker derives it, so no rule change can be silent and no phase can invent a word for a rule the
player has to learn (FAI-01).

| Change | Label | Characters |
| --- | --- | --- |
| `box_scale` lower on either axis | `BOX NARROWED` | 12 |
| `marker_speed` higher | `MARKER FASTER` | 13 |
| `marker_speed` lower | `MARKER SLOWER` | 13 |
| `invert` to `"horizontal"` | `CONTROLS FLIPPED` | 16 |
| `invert` back to `"none"` | `CONTROLS BACK` | 13 |
| `marker_count` 1 to 2 | `TWO MARKERS` | 11 |
| `hazard_mode` to `"clearable"` | `HAZARDS HOLD` | 12 |

Placement and timing, all fixed:

- One line of spec 05's font, 8x8, centred on the frame centre x 128, glyph tops at y 58, so the line occupies y 58 to
  65: 4 pixels above the top edge of the tallest legal box (y 70) and never over a hazard, the health bar or spec 05's
  text box at y 168.
- First ink with a 1 pixel dark outline on all four sides, so it reads over the dimmed field (spec 08 dims by 60
  percent black).
- 24 steps, beginning at the first step of the 12 step warning. On a phase break that is break steps 18 to 41, so the
  label is still on screen for the first 12 steps of the new pattern. 24 steps is the study's number: a label that ends
  when the warning ends leaves the player reading a new rule with the hazards already moving.
- Drawn whole, no typewriter, no blip, steady, no blink. A label the player has to wait for is a label the player
  misses.
- The longest string is 16 characters, 128 pixels, inside the 160 pixel box width and inside spec 05's text area
  (x 72 to 240). No wrap, no second line, ever.
- A phase with no rule change draws nothing. A field that changes back later draws the label for that direction
  (only `invert` and `marker_speed` can).
- The label is cancelled immediately when the fight ends, and it is never drawn over a hazard or the health bar.

## 4. The interruption contract: battle_end = interrupted

The enemy block gains at most one `interrupt` object:

| Field | Type | Legal range |
| --- | --- | --- |
| `on` | string enum | `"spare_refused"`, the only trigger in the demo; the set is closed |
| `hp_at_or_below` | integer, percent of `max_hp` | 1 to 99, and strictly above the enemy's `spare_hp_percent` (section 7 refusal 8) |
| `unless_flag` | string, optional, an existing flag name from spec 10 | the trigger is disabled while this flag is true; a flag no other file names is a checker error |
| `scene` | string, an existing scene id, or an object with all four route keys (`undecided`, `mercy`, `blooded`, `genocide`) mapping to existing scene ids | as above; a partial object is an error, never a default |

The fight returns exactly one value in `battle_end`, and the set is closed: `victory`, `defeat`, `spared`,
`interrupted`. A scene that receives anything else is a checker error, not a runtime default.

Resolution order, evaluated one step at a time with the first match winning:

1. The player's hp reaches 0 during a dodge phase: `defeat`.
2. SPARE is accepted (trust reached, or hp at or below `spare_hp_percent`): `spared`.
3. Enemy hp reaches 0 from the player's damage: `victory`.
4. SPARE is pressed on this enemy while its hp is at or below `interrupt.hp_at_or_below` and its spare condition is
   unmet: `interrupted`. Read the field name literally: it is the gate on the request, not a crossing of the bar.
5. Enemy hp crosses a phase breakpoint: the phase changes (section 1).

Why the trigger is a refused SPARE and not an hp crossing (A18-1). Rule 3 can only win on a blow that takes the bar
from above the threshold all the way to 0, because a blow that stops short crosses the threshold and rule 4 fires
first. Percy is 120 hp and the biggest legal blow is 12 (spec 07's FIGHT ceiling), or 18 with `tide_step`, so a kill
needs the interrupt threshold at most 11 hp with FIGHT alone (9 percent of 120) or at most 17 hp with the power (14
percent). At 40 percent, or at the 25 percent Q18-1 suggested as the fix, no sequence of legal inputs can ever kill
him: the fight is unwinnable by damage on every route. The spec's own acceptance 6 asked for a 49 damage blow that does
not exist. A crossing trigger and a kill are therefore mutually exclusive above 14 percent, and a story beat cannot
live below it. So the interruption is moved to the one thing a 120 hp boss can always offer: a player asking for mercy
that Percy will not take.

Nothing is shared: rule 4 is a player action, rule 5 is an hp crossing, so a phase row and an interrupt may carry the
same percent and neither shadows the other. The phase still enters on the damage that crosses it, and the interruption
waits for the player to press SPARE.

What happens when rule 4 fires, in order:

1. The pending dodge phase is dropped. It never starts, so there is no warning, no hazard and no break to cancel, and
   the marker is where the player left it.
2. The exit row is written as `turned` with the current round (spec 10 rules 6 and 7), no counter moves, and the
   verdict is recomputed from the rows.
3. The route is derived from the counters and rows as they stand after that row is written (spec 10 recomputes the
   route per read and never stores it), and the scene id is chosen from `interrupt.scene`: the single id, or the id
   under the derived route's key. This is how the study's "branch on the route flag" is realised without storing a
   route and without a new command (A18-4).
4. `battle_end = interrupted` and the scene id are returned to the caller that ran `battle` (spec 06), which continues
   with no press.
5. The scene does the story work with existing commands: `say`, `spawn` Prometheus at the arena's right edge, `shake` 2
   pixels for 20 steps, `music` crossfade over 30 steps, then `branch` on route flags the scene sets itself, `setflag`
   for the route contribution, `end`.
6. On `end`, control returns to the map. The fight is not resumed, the arena object is destroyed, and no state from it
   survives except the exit row, the counters and whatever the scene set.

Three more rules:

- `interrupted` counts as resolved for spec 06 rule 6, so a scene may end with it and the checker passes it. This is
  the whole reason the exit value exists: without it the Prometheus scene is an unresolved battle and the checker
  refuses the scene file.
- The arena never learns about the interruption. No arena code path names an enemy, a scene or a route (spec 07 rule
  7); the arena is asked for a pattern, it supplies one, and it is simply not asked again.
- The refusal line spec 16 section 11 owes an unmet SPARE is not printed on the turn the interruption fires. The
  scene's first `say` is the reason, and the interruption is not a punishment: the unmet SPARE never consumed the turn
  (spec 07 acceptance 3), so the player loses nothing by asking.

## 5. The no double novelty check

Four definitions, then the rules. Getting the unit right is the whole check, so it is defined before it is enforced.

- A **rule change** in a phase is that phase's effective value of any of the five fields differing from its parent
  phase's effective value.
- A **hazard shape** is the pair `(size, sprite)` of a pattern frame. Every frame in `data/patterns/all.json` names a
  size (8 or 16) and none names a sprite today (measured 2026-10-22), so the shape is the size today and the sprite
  joins the pair the day frames carry one.
- The **shape set** of a phase is every shape used by any frame of any pattern in that phase's pool: the enemy's
  `patterns` plus every `pattern_id` from rows at or above it.
- A **new shape in a phase** is a shape in that phase's shape set that appears in no earlier phase's shape set.

Rules:

1. At most one rule change per phase.
2. A phase may not change a rule and introduce a new shape in the same phase. The error names the phase index, the
   field and the pattern that carries the new shape.
3. A phase may introduce a new shape with no rule change. Percy's phase 3 does exactly this.
4. A phase may change a rule with no new shape. Percy's phase 2 does: the wall pattern is a new PATTERN, but every
   hazard in it is 8x8, the shape phase 1 already showed. This is the distinction the whole rule rests on. A new bullet
   pattern is not a new hazard shape. The study fixes the unit in its own words ("No new hazard type: the new thing is
   the space, not the bullets"): the shape is the hazard's size and art, not its recipe.
5. Two rule changes in one phase is an error even when both could be labelled, because the label rule draws one line for
   24 steps and the skeleton's point is one new thing at a time.
6. The check runs per fight over the pool, not per pattern: a pattern that adds no shape of its own can still be reached
   in the same phase as a rule change, and that is legal.
7. A phase set may be route conditional through `route_gate` on the row, and the check runs on each route's own phase
   list: the ungated rows plus the rows whose gate contains that route. An enemy is legal when every route it can be
   fought on produces a legal list. No other field gating exists; a gate on anything else is a checker error.

## 6. Percy, three phases (the example)

Percy is 120 hp in `data/enemies/all.json`, attack 3 to 5, boss, with `percy_rain`, `percy_wall` and `percy_fan` in
`data/patterns/all.json`. The study's bands are 100 to 70 percent, 70 to 40 and 40 to 0, so at 120 hp the crossings are
at 84 and 48 hp.

| Phase | Band | hp at entry | Pattern pool | Rule in force | Label | Cue |
| --- | --- | --- | --- | --- | --- | --- |
| 1 teach | 100 to 70 percent | 120 down to 85 | `percy_rain` (2 concurrent) | none, all defaults, box 160x100 | none | variant 1 |
| 2 change one rule | 70 to 40 percent | 84 down to 49 | adds `percy_wall` (3 concurrent) | `box_scale` `[80, 100]`, which is 128x100 | `BOX NARROWED` | variant 2 |
| 3 combine | 40 to 0 percent | 48 down to 1 | adds `percy_fan` (3 concurrent) | unchanged from phase 2 | none | variant 3 |

The concurrency numbers 2, 3 and 3 are the study's ladder and spec 09's acceptance 5. The cue variants are the phase
index: spec 12 owns what each one is, and with one battle cue in the table the phase 3 request resolves to the sound
already playing, which is a no-op rather than a restart (A18-2), so nothing is heard and the pattern is not interrupted.

The data block this spec asks for. Where every key in it comes from:

| Key | Defined by |
| --- | --- |
| `max_hp`, `attack`, `route_kind`, `patterns` at the enemy level | spec 07's enemy data list, already in `data/schemas/enemies.schema.json` |
| `phases`, `interrupt` at the enemy level | sections 1 and 4 of this spec |
| `hp_at_or_below`, `pattern_id`, `talk_set`, `line_id`, `attack` inside a phase row | the phase row the enemies schema already carries; this spec fixes `hp_at_or_below` as percent, see C18-2 |
| `talk_phase` inside a phase row | spec 16 section 10: the talk card's phase value, copied verbatim so the crossing swaps the card, card t_155e22e2 |
| `box_scale` inside a phase row | section 2.1 of this spec |
| `scene` inside `interrupt`, and its four route keys | section 4 of this spec |

Every id in the block exists in the repository today except `talk_percy_phase3` and `percy_phase3_line`, which are two
new dialogue ids for the row that adds the fan (R05 owns them), and `prometheus_interrupt_blooded`, which is the scene
the blooded and genocide keys need (R04 owns it, delta C18-3).

```
"percy": {
  "max_hp": 120,
  "attack": { "min": 3, "max": 5 },
  "route_kind": "boss",
  "patterns": ["percy_rain"],
  "phases": [
    { "hp_at_or_below": 70, "pattern_id": "percy_wall",
      "talk_set": "talk_percy_phase2", "talk_phase": "percy_phase2", "line_id": "percy_phase2_line",
      "attack": { "min": 4, "max": 5 },
      "box_scale": [80, 100] },
    { "hp_at_or_below": 40, "pattern_id": "percy_fan",
      "talk_set": "talk_percy_phase3", "line_id": "percy_phase3_line",
      "attack": { "min": 4, "max": 6 } }
  ],
  "interrupt": {
    "on": "spare_refused",
    "hp_at_or_below": 40,
    "scene": {
      "undecided": "prometheus_interrupt",
      "mercy": "prometheus_interrupt",
      "blooded": "prometheus_interrupt_blooded",
      "genocide": "prometheus_interrupt_blooded"
    }
  }
}
```

Four consequences worth writing down, because each one is a design decision the numbers already made:

1. A phase may raise the attack value inside the enemy's spec 07 band (3 to 6 for Percy), and that is not a rule change:
   it is a number the player cannot name and does not have to learn, so it carries no label and does not count toward
   the novelty check. Damage per enemy still never scales with the stage (the study's FAI section), because the band is
   the enemy's own.
2. The study's "hazards move at 1.25 times phase 2 speed" is realised in the pattern rows, not in a field:
   `percy_fan` runs at 2.0 and 2.1 pixels per step against `percy_wall`'s 1.6 and 1.7, which is 1.25x and 1.24x (1.7 x
   1.25 = 2.125, written as 2.1 on the 0.1 step the pattern rows use). A multiplier field would be a second way to say
   one number, and spec 09 rule 1 says an attack is data.
3. Percy's spare by hp is reachable, and the threshold is left at 25 percent as spec 07 wrote it (A18-5). Grinding him
   to 30 hp and pressing SPARE ends the fight as a spare, because nothing pre-empts the fight on the way down: the
   interruption only fires on a refused SPARE, and at 30 hp SPARE is accepted rather than refused (rule 2 beats rule
   4). The window the story exit lives in is 40 percent down to 26 percent, which is 48 hp to 31 hp, and it is entered
   only by pressing SPARE there.
4. `genocide` cannot be the derived route at this fight, because it needs one boss already killed and Percy is the
   first boss in the game, so its key is unreachable here and aliases the blooded scene. The four keys stay required
   anyway: a contract that shortened itself per enemy would be a route table in the schema (A18-4).

## 7. What the checker must refuse

Today `tools/check_data.py` validates enemies against `data/schemas/enemies.schema.json` and knows nothing about
phases: a search for `hp_at_or_below` and for `PHASE_ATTACK_BAND` under `tools/` returns nothing on 2026-10-22, so the
Percy phase row in data passes with no rule in this file enforced. The schema's own description claims the checker pins
a `PHASE_ATTACK_BAND`; no such constant exists anywhere in the tree, which is delta C18-2. Until the checker grows
these, this section is the list, not a statement of what runs.

Each refusal names the file, the enemy id, the phase index and the field:

1. A breakpoint outside 1 to 99, not strictly descending, a duplicate threshold, or a fifth phase row.
2. A `pattern_id` that is not in `data/patterns/all.json`, or that is already in the pool above the row.
3. Two rule fields changed in one phase, naming both fields.
4. A rule change and a new hazard shape in the same phase, naming the field and the pattern (section 5).
5. A `box_scale` component outside its set, a component that went up from the previous phase, or a non even height.
6. `marker_speed` outside 1.00 to 3.00 or off the 0.25 step, `invert` outside its enum, `marker_count` outside 1 or 2,
   `marker_count` 2 on a non boss or on an `undecided` or `mercy` route, `hazard_mode` `"clearable"` in demo data.
7. An `interrupt` on a non boss, more than one interrupt, an `on` outside its closed set, a scene id that does not
   exist, a route object missing any of its four keys, or an interrupt threshold outside 1 to 99.
8. An `interrupt.hp_at_or_below` at or below the enemy's `spare_hp_percent`, because then SPARE always wins rule 2 and
   the story exit can never fire. On Percy that is 40 against 25, which passes. This refusal replaces the older one
   about a phase row below the interrupt threshold: the interruption no longer precedes anything on the hp axis, so no
   phase is shadowed by it (A18-1).
9. A `route_gate` that names a key outside the four routes, that is empty, or that leaves a route with a phase list
   that fails any rule above.
10. An `interrupt` on an encounter row in `data/encounters/all.json`, because the enemy row owns it (C18-7: two copies
    of one fact drift, and the encounter copy is the one nothing checks).
11. A `battle_end` value outside the four, in a test double or in a scene that checks the result.

## 8. P: lines and A: for gamedev (answered 2026-10-22, card t_00a94c86)

P1. Five rule fields and at most one change per phase, with the label derived from the field and its direction rather
than authored in data. Reason: the study's whole point is that a rule change is data one byte wide, and a free text
label is a way for the data to lie about what it changed.

P2. The 30 step break contains the 12 step warning instead of preceding it. Reason: 30 steps is the study's number, and
a break plus a separate warning would cost 42 steps, a fifth of a second of extra nothing in a fight that already
spends 20 steps on a damage message.

P3. Breakpoints are percent of `max_hp` and compared in integer arithmetic. Reason: spec 07's acceptance 5 says changing
Percy's hp in data to 60 changes the fight with no code edit; with absolute breakpoints, halving his hp would move the
phases to the wrong bands and the acceptance criterion would be false.

P4. A hazard shape is the hazard's size and art, not the bullet pattern. Reason: the study's own phase 2 changes a rule
and adds a pattern, and calls that legal because "the new thing is the space, not the bullets". Reading a pattern as a
shape would make the study's own example illegal.

P5. The interruption is an enemy field read by the director, and the scene id may be per route. Reason: spec 10 refuses
to store a route, so a "route flag" cannot exist; deriving the route on read at the moment the fight ends is the same
rule spec 10 already states, and it keeps spec 06's command set unchanged.

P6. The marker is frozen and teleported during the break, not animated. Reason: spec 08 already re-centres it every
phase, and an animated marker during a box change is a hit the player cannot avoid.

P7. The interruption fires on a refused SPARE, not on an hp crossing. Reason: an hp threshold above 9 percent makes a
120 hp boss unkillable when the biggest legal blow is 18, so a crossing trigger and the kill route cannot coexist.
Section 4 carries the arithmetic.

A18-1 (phase 3 against the interruption). Answered by moving the trigger off the hp axis: `interrupt.on:
"spare_refused"`, with `hp_at_or_below` as the gate on the request, so the fight is interrupted when the player presses
SPARE at or below the threshold and SPARE is unmet. All three options on the card are refused, each for a measured
reason. Option 1 (interrupt at 25 percent) and option 2 (keep 40) both leave Percy unkillable: rule 3 only wins when
one blow takes the bar to 0, the biggest legal blow is 12 (18 with `tide_step`), so a kill needs the threshold at most
11 hp on FIGHT alone (9 percent) or at most 17 hp with the power (14 percent). Option 3 (hook unset) takes the only
non-committal exit away from a player who will neither kill nor TALK, and that player then owns a kill they did not
choose, which is the one thing the route ledger exists to make honest. With the trigger on the SPARE press, phase 3 is
entered on the 40 percent crossing exactly as authored, the fan plays for as long as the player keeps fighting, and the
story exit is a deliberate act rather than a timer. The study's line "all three shapes have been seen once" is now true for every
player who fights through phase 3, and unavailable only to the player who asks for mercy there, which is the correct
trade.

A18-2 (music vocabulary). Confirmed: a cue VARIANT per phase, indexed by phase number, not a layer. Spec 12's "layered
dynamic music" out of scope stands, and a variant is a different arrangement file played whole and crossfaded, which is
one track at a time and nothing more. One refinement the question exposed: a request that resolves to the sound already
playing must be a NO-OP, never a restart. Without that rule the phase 3 request on a cue with one variant restarts the
battle theme from the top at the moment the fan enters, which is a fault the current table would hit on the first boss.
The audio table gains an optional `variants` array of 1 to 4 sound ids per cue; a cue with one variant answers every
phase index with the same sound and every request after the first is a no-op.

A18-3 (the split marker on genocide). Genocide gets it. The study's section 9 already hands the fourth phase to
blooded and genocide together; restricting it to blooded would give the harsher route the easier final phase and make
the hardest phase in the game a reward for killing only regulars, which is backwards. The genocide route's own extra
cost is already written: SPARE is refused at Kronos, so the player must kill. Two consequences, both now in the spec:
the legal set for `marker_count` 2 is `blooded` or `genocide`, and phase rows gain `route_gate` so the fourth phase can
exist on some routes only, with section 5's novelty check run per route.

A18-4 (selecting the variant). Confirmed: the per route scene id in `interrupt.scene`, all four keys required, a
partial object an error. The alternative is refused because spec 06's `branch` takes a flag name and nothing else; a
counter comparison would add an expression language to a command set whose whole safety property is that every command
is a plain field, and it would put the route table in a second place, which is exactly what spec 10 forbids. The per
route object also costs nothing at runtime: the exit door already derives the route to write the row and the verdict.
One addition: a key may alias another key's scene id, and Percy's genocide key does, since genocide needs a boss
already dead and Percy is the first boss, so that key is unreachable at this fight. The keys stay required anyway,
because a contract that shortens itself per enemy is a route table smuggled into the schema.

A18-5 (the hp based spare). It was never intended to be unreachable; it was a symptom of the crossing trigger. With the
trigger moved, `spare_hp_percent` stays at 25 and works: grind Percy to 30 hp, press SPARE, rule 2 accepts it. The
checker now refuses an interrupt threshold at or below `spare_hp_percent` (section 7 refusal 8), because there SPARE
always wins and the story exit is dead data. Percy passes at 40 against 25, with a 6 hp window (48 hp down to 31) in
which a pressed SPARE summons Prometheus instead of sparing.

## 9. Deltas this spec opens for other cards

- C18-1, R05 (t_8a7ada73), `data/enemies/all.json`: Percy's `patterns` narrows to `["percy_rain"]` and the wall moves to
  the 70 percent row, because the study's phase 1 is rain only. The current row has `["percy_rain", "percy_wall"]` plus a
  single phase at 60, so as written today the fight has one crossing and phase 1 already shows two shapes. Section 6 is
  the target row.
- C18-2, R05, `data/schemas/enemies.schema.json`: `hp_at_or_below` narrows from absolute hp (minimum 0, maximum 9999)
  to percent (1 to 99), `$defs/phase` gains the five rule fields with their types and ranges plus `route_gate`, the
  enemy gains `interrupt` with its `on`, `hp_at_or_below` and `scene` fields, and the description's claim about a
  `PHASE_ATTACK_BAND` constant is corrected, since no such constant exists.
- C18-3, R04 (t_a3fa132a), `data/scenes/all.json`: `prometheus_interrupt` exists and sets `met_prometheus` and
  `percy_standing`, but it has no shake, no spawn, no 30 step crossfade and no route variant. Two scenes are still to
  write: `prometheus_interrupt` gains the study's step 2 beats, and `prometheus_interrupt_blooded` is new. The blooded
  variant is written for a Percy who is still standing, not for one already dead: under A18-1 the interruption fires on
  a refused SPARE, so the boss is alive in every variant the interrupt can reach. The "arrives late, Percy is dead"
  beat moves to `percy_aftermath_kill`, which is already the kill path.
- C18-4, R17 (t_eab7904b), `knowledge/SPEC-REVIEW.md`: this file needs a row, or `tools/check_spec_review.py` reports
  "no row" for it. Measured on 2026-10-22 after this file landed: 18 specs, 2 problems, the two being
  `specs/17-action-movement.md` and this file, both for the missing row. The gate passed with 16 specs and 0 problems
  before the two new specs landed, so the row is the only thing standing between the tree and a green run.
- C18-5, spec 08's out of scope line ("a second marker") and its fixed speed of 2 are superseded for a boss phase by
  section 2 of this spec, and unchanged everywhere else.
- C18-6, no card yet: `tools/check_data.py` gains section 7's refusals. Until it does, every rule here is unenforced
  and the phase rows pass by default.
- C18-7, R05 and R04, `data/encounters/all.json`: the Percy encounter row carries its own
  `interrupt: { hp_at_or_below: 60, unless_flag: met_prometheus, scene: prometheus_interrupt }`, which is a second
  copy of a fact this spec puts on the enemy row, and it disagrees with it (60 against 40, and a crossing trigger
  against a SPARE trigger). The encounter block comes out. A `met_prometheus` guard is still wanted, so the enemy level
  keeps an optional `unless_flag` and the encounter copy is refused by section 7 refusal 10.

## Acceptance (Nayil)

1. Fight Percy: at 84 hp the box narrows to 128x100, `BOX NARROWED` is on screen for 24 steps, the wall pattern is the
   first pattern of the new phase, and nothing else about the fight changes.
2. Fight him twice: the same patterns and the same hazard positions appear at the same steps, because one seed per
   battle (spec 09 rule 7).
3. Put a rule change and a 16x16 hazard in the same phase in data: the checker refuses it and names both the field and
   the pattern.
4. Put `box_scale` `[80, 100]` and `marker_speed` 2.5 in the same phase row: the checker refuses it and names both
   fields.
5. Press SPARE at 48 hp or below with trust under 3: control goes to the scene with no press, the SPARE press costs no
   turn, and F3 shows the exit row `turned` with the boss counters unmoved.
6. Kill him: FIGHT a 120 hp Percy to 0 hp with no SPARE press and no TALK, and the fight ends as a victory, no scene
   plays, and `bosses_killed` is 1.
7. A phase row at 0 percent, at 100 percent, or on a regular enemy: each is refused with the row named.
8. Grind him to 30 hp and press SPARE: the fight ends as a spare and the fan was on screen at least once on the way
   down.

Out of scope: more than four phases, a phase that changes the enemy's sprite, element or rewards, a phase that heals,
resuming a fight after an interruption, player side phases, hazard shapes beyond 8x8 and 16x16, true layered music, a
second marker on the undecided or mercy route, and any rule change that needs a new field.
