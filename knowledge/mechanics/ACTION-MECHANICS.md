# Action mechanics: bullet board, i-frames, mercy, whip, jump, knockback, boss rule changes

Written 2026-10-22 (card t_65aaf2e6, MECH-STUDY-2). This file is the source of truth for
`data\mechanics\action_recipes.json`. Every recipe in that file cites a source id from section 1 and a
spec number from section 9. Nothing here is code. Numbers marked DECISION are ours and can be changed by
changing them here first.

Scope: the action half of Primordial Paradox. Two surfaces at once. Surface A is the framed battle,
whose enemy turn is the dodge arena of spec 08 fed by the patterns of spec 09. Surface B is the action
segment (ship corridor, prison, data center), which is side scrolling, with a fixed jump, a whip and a
knockback. Section 7 argues that the jump arc and the whip are one system with the dodge arena: both are
"commit, then read the tell", and both are hurt by the same three mistakes (air control, uneven damage,
unreadable telegraphs).

## 1. Sources read

All read 2026-10-22 unless the row says otherwise. Fan wikis and TAS notes are used as measurement
records, not as text to copy: numbers and behaviour only, described in my own words.

| ID | Source | URL | What it gave |
| --- | --- | --- | --- |
| S1 | TASVideos game resources, Castlevania (NES), frame data section | https://tasvideos.org/GameResources/NES/Castlevania | whip animation 22 frames with the hit landing at 17; flat jump 40 frames and the landing table 29 / 36 / 40 / 42 / 44 / 46; invincibility timer 48 units at one unit per two frames; knockback peak 14 pixels above; walk 1 pixel per frame; stairs half speed; forced crouch after a deep landing; player and boss HP 64 |
| S2 | TASVideos game resources, Castlevania 3, tricks page | https://tasvideos.org/GameResources/NES/Castlevania3?revision=6 | no control in mid air; a jump wastes 4 frames; stairs cannot be landed on; JP and US damage models differ (US is flat per stage, JP is per enemy and constant); one character has a variable jump, the others do not |
| S3 | DataCrystal, Castlevania 3 RAM map | https://datacrystal.tcrf.net/wiki/Castlevania_III:_Dracula%27s_Curse/RAM_map | wounded timer as an explicit invincibility frame counter; weapon level 0 short, 1 medium, 2 long; knockback direction as its own byte; six subweapon ids plus a [II] and [III] multiplier byte; health 40 is full; crash timer that stuns after a long fall; boss hitboxes stored as bitmasks; the final boss phase byte with three values, and a second boss whose phase bits select forms |
| S4 | GameFAQs, Castlevania 3 solo character guide (whip section) | https://gamefaqs.gamespot.com/nes/587180-castlevania-iii-draculas-curse/faqs/29763 | whip damage 2 at level 1 and 3 at levels 2 and 3; the level 2 upgrade barely changes reach; level 3 turns it into a mid range weapon; the whip has the second longest start up of any normal attack |
| S5 | GameFAQs, Castlevania 3 review (subweapon timings) | https://gamefaqs.gamespot.com/nes/587180-castlevania-iii-draculas-curse/reviews/161491 | stopwatch freezes time for 5 seconds; holy water burns on the ground for about 1 second; double and triple shot pickups exist |
| S6 | AtomechLLC, jump-test-classic project notes | https://github.com/AtomechLLC/jump-test-classic | a three way taxonomy of jump models (committed fixed arc, variable height by gravity switching, speed scaled), with a worked example of each and the observation that the committed model locks horizontal speed at takeoff |
| S7 | Pine job record for the battle study (Pine node, run 2026-10-22 06:50 to 06:52, status completed, 21 turns) | `<workspace>\Shared\projects\arananet\pine\data\results\` (the battle mechanics job listed in `arananet\pine\jobs_round5.json`; its own file name spells a trademark the clean-room gate refuses, so it is cited by job and date here, not by name) | the board and its movement numbers, the hidden invincibility stat and its item bonuses, the timing bar, ACT and mercy rules, six board movement modes tied to named bosses, the attack colour language, level scaling formulas |
| S8 | Pine job record for the Castlevania 3 action study, same run | `<workspace>\Shared\projects\arananet\pine\data\results\mech-castlevania3-action.json` | NOTHING. Status max_turns: stopped after 60 turns without an answer, wall 319.1 s, about 0.016 USD of computer time. Recorded here so no later reader counts it as a source, and so the Castlevania numbers in this file are known to come from S1 to S6 instead |
| S9 | vgmuseum, Castlevania (NES) mechanics page | https://www.vgmuseum.com/mrp/NewCV/game-cv1.htm | knockback is about the length of one block; a jump clears about 2 blocks vertically and horizontally, and at most a 3 block gap from a ledge edge |
| PP | This study's own decision, with no external source. Used only where a number is ours and the prose says so | (this file, sections 2 to 10) | the board's slow key, the whip's three pixel reaches, the deep landing stun length, the phase breakpoints |

Source ids are what `data\mechanics\action_recipes.json` cites. PP is not a study: it is the honest tag
for a number we chose, so that a reader looking for a citation finds an empty shelf rather than a
plausible one.

The wiki pages quoted by S7 are named there together with the exact figures; they are the battle wiki
pages for the encounter and the hidden stats. I did not re-read those pages myself, so a number from S7
carries S7's read date, not mine. If one of them decides a build item, re-read the page first.

One honesty note on method: S7 is a report from an autonomous browsing job, so every number in it is a
second hand read. Where a number from S7 drives a DECISION here, the decision is written so that the
number is a comfort margin, not a load bearing constant. Nothing in the game breaks if S7 misread by one
frame; the specs' own numbers (section 8) are the ones that must hold.

## 2. The bullet board, and the numbers around it

The board we already speced (spec 08): 160 x 100 box centred at (128, 120) on a 256 x 240 frame, dimmed
field, 8 x 8 marker in the brightest ink, 2 pixels per step in 8 directions, hazards with a hitbox 2
pixels smaller per side.

The ancestor's board, from S7: the player character is placed inside a framed box for the enemy turn and
every attack on screen targets that character. The marker moves in any direction at a hidden speed value
of 4, and that value rises to 5 (25 percent faster) for one boss fight only. A slow key exists. The
board is shared by several overlapping enemy patterns at once.

Put beside ours, the numbers say something useful. The ancestor's box is smaller than its frame in the
same proportion as ours, but its marker crosses the short side in about 1 second at speed 4 on a 320 x
240 field. Ours crosses the 100 pixel height at 2 pixels per step, which is 50 steps, or 0.83 s. So our
marker is relatively faster and our box relatively larger, which is the single biggest difficulty dial we
own, and it is why the concurrency ladder in spec 09 stays at 2, 3, 3 for the first three bosses.

DECISION (BRD-01 to BRD-05): keep the box, keep 8 x 8 and 2 pixels per step, and add one thing the
ancestor has and we do not: a slow key. Hold cancel, speed drops to 1 pixel per step. It costs one input
and it turns a bullet wall that already exists in spec 09 into a puzzle instead of a reflex gate, which
is what a music and story driven game should do with its hardest patterns.

DECISION (BRD-06): the ancestor raises marker speed by 25 percent for one boss. We do the same once,
for Kronos phase 3 only, as a data field `marker_speed` defaulting to 2, because a speed change at the
last boss is free difficulty that reads as the student being outpaced.

## 3. Invincibility frames

Four records, four different answers, and the differences matter more than the numbers.

- The first NES game in S1: a single timer counts 48 down to 0 at one unit every two frames, which is
  about 96 frames, or 1.6 s, and it does not start until the player lands after being hit. On stairs it
  starts at once, so stairs give less real protection.
- The third NES game in S3: the same idea, but as an explicit byte named "wounded timer, invincibility
  frames", plus a separate timer for a potion that grants invincibility and another for a stun after a
  long fall. Three separate timers, one job each.
- The ancestor in S7: invincibility is a hidden stat measured in frames, and equipment adds to it (+15
  frames, +30 frames), so it is a stat a player can invest in. One board mode also lengthens it.
- S7's hardest boss: invulnerability is zero. Damage is instead refused on a fixed cadence, one hit
  every 5 frames, or 4, or 3 with two items equipped. That is a very different promise: not "you cannot
  be hit twice" but "you cannot be hit faster than this".

DECISION (IFR-01 to IFR-05): we take the second model, 30 steps of invulnerability after a hit, blinking
every 4 steps, with an overlapping hazard unable to re-hit. Our reasoning is that 30 steps is half a
second, which is long enough for a player to see what happened and short enough that a 20 HP player with
enemy attacks of 2 to 6 cannot tank a pattern. The 96 frame ancestor window is a third of what a 20 HP
character needs, because there the player has 64 HP and healing items that do not cost a turn.

Our i-frame clock starts on the hit, not on landing. The ancestor's landing rule exists because the
knockback arc is a fixed ejection that already removes control; we do not eject the marker, so the
landing rule has nothing to attach to, and copying it would silently give a player who is hit near the
top of the box a fraction of the promised half second.

For the optional superboss we keep the fourth model in reserve as a flag, `iframes_mode: cadence`, with
a hit cadence of 4 steps. It is written down because it is the cleanest way to make a fight hard without
making it unfair: the player is always protected for the same amount, the boss is simply allowed to be
faster.

## 4. Mercy and the non violent options

From S7, in words: during a turn the player may spare instead of attacking. Sparing only works once the
enemy's name is shown in the spared colour; sparing an uncoloured enemy usually just skips the turn, and
some bosses demand repeated spares. There are per enemy ACT options, some of which end the fight at once
and some of which must be used in a fixed order first. The final boss deletes the spare option until it
is beaten, so the peaceful route is impossible there by design and not by accident.

Our specs already say: TALK offers up to 4 context options and adds 1 trust, SPARE unlocks at trust 3 or
enemy HP at or below 25 percent, and only the dodge phase damages the player (specs 07 and 16).

DECISION (MRC-01 to MRC-06), four additions taken from how the ancestor makes peace legible:

1. The refusal is visible. When SPARE is pressed and the condition is unmet, the menu entry draws in the
   second ink, plays a low blip and prints one line naming why (trust count, or HP gate). Spec 07 rule 1
   already demands the sound; this adds the reason.
2. A repeated spare exists on exactly one boss, Hector, who needs two spares in a row. This makes one
   fight where the peaceful path asks for nerve rather than bookkeeping.
3. Kronos refuses SPARE on the blooded and genocide routes until the kill condition is met, which is the
   ancestor's "deleted mercy" idea, and it is the only fight where the opposite entry is refused with a
   flag rather than a trust count.
4. Every TALK option that matters names something the boss is afraid of, in the boss's own words. This
   is content rule rather than mechanic, but it is the difference between four options that read as a
   quiz and four that read as an argument.

## 5. How a boss changes the rules

This is the most transferable idea in the whole study, so it gets its own section. In S7 the six board
movement modes are not cosmetic: a boss hands the player a different control scheme and the pattern is
built for that scheme. Gravity mode makes the marker fall. Track mode locks the marker to lines and uses
the perpendicular input to switch lines. Shield mode takes movement away and asks for timing. Shooter
mode adds a button that destroys hazards. One boss inverts the d-pad. One late fight splits the marker
into two halves under one input.

S3 shows the same instinct in a game with no board at all: the third NES game stores boss hitboxes as
bitmasks and gives the final boss a phase byte with exactly three values (a humanoid form, a demon form,
and a third form), and gives another boss a byte whose bits select "skull form" and "attacking". The
rule change is in data, one byte wide, which is why both games can afford many bosses.

Our mapping, DECISION (RUL-01 to RUL-07):

| Phase rule | Ours | Boss | Why this boss |
| --- | --- | --- | --- |
| baseline | free 8 direction marker, 2 px per step | Sailor tutorial, Percy phase 1 | teaches the box |
| narrowed box | box shrinks to 128 x 100 from phase 2 | Percy phase 2 | the corridor of a ship |
| slow key matters | same as baseline, one hazard type immune to grazing | Percy phase 3 | reads as the captain adapting |
| no fire button, hazard clears on contact | hazards that must be dodged, never destroyed | Hector phase 1, 2 | pincer and sweep already reward reading |
| inverted horizontal | left and right swapped for one phase | Hector phase 2 only | a small, honest cruelty, with a 30 step warning and the on screen arrow flipped |
| marker speed 2.5 | `marker_speed` 2.5 | Kronos phase 3 | the student outpaced |
| two markers, one input | mirrored pair, both must survive | Kronos final phase on the blooded route only | the ancestor's split halves, paid for at the end |

Rule changes are data fields, never code paths: `box_scale`, `marker_speed`, `invert`, `marker_count`,
`hazard_mode`. The rule change is announced in the 12 step warning window with a 24 step label ("BOX
NARROWED", "CONTROLS FLIPPED") because a rule change the player cannot name will be read as a bug.

## 6. The jump arc

Numbers from S1, S2, S6, S9:

- Horizontal speed is 1 pixel per frame while walking, jumping and while being knocked back. There is no
  running jump and no momentum to build.
- A flat jump is 40 frames. Landing 2 blocks higher ends it at frame 29, 1 block higher at 36, level at
  40, one block lower at 42, two lower at 44, three lower at 46.
- The arc is a preset table, not force plus gravity: the ROM holds the vertical values as a short byte
  table, which is why the arc is exactly repeatable and why changing one byte changes the physics (S1
  and the DataCrystal notes for the first game).
- Horizontal speed is committed at takeoff. There is no mid air steering, and no variable height: the
  jump button is a command, not a throttle. A jump wastes 4 frames before the character leaves the
  ground (S2).
- Apex is about 42 pixels, roughly 2.6 blocks of 16, and clears 2 blocks vertically; a 3 block gap is
  clearable only from the very edge of the ledge (S1, S9).
- Stairs are half walking speed, and you cannot land on stairs (S1, S2).
- Landing from a fall of 4 or more blocks forces a crouch and a short loss of control, which a whip
  timed to end on the landing frame cancels (S1).

S6 names the alternative models: variable height by switching gravity (weak on the way up while the
button is held, about 3.5 times stronger once released) and speed scaled takeoff. Both are more
forgiving. Both also make level design harder, because the same gap has many possible arcs.

DECISION (JMP-01 to JMP-05): fixed arc, 4 step startup, 40 steps of air, apex 42 pixels on a 16 pixel
block grid, no air control, stairs at half speed, and a deep landing stun of 10 steps that a whip started
in the air cancels. The reason is authorability. With one arc, a 3 block gap is a yes or a no, a hazard
at head height is a decision, and a level can be checked by a script that asks whether every gap is
clearable by exactly one jump from the foreground edge. Our game is not a platformer first; it is a game
with action segments, and a fixed arc is the cheapest way to keep them honest.

## 7. Whip range and knockback

From S4 and S1: the whip is three levels. Level 1 does 2 damage and is short. Level 2 does 3 damage and
the reach gain is described as negligible. Level 3 does 3 damage and the reach becomes mid range. Its
animation is 22 frames and the hit lands at frame 17, so a miss costs the whole 22 frames and a hit
still costs 5 frames of recovery after contact. It is the second slowest normal attack in the game,
which is exactly why the game's combat is about spacing rather than mashing.

From S1, S3 and S9, knockback: the player is thrown upward and away, peaking 14 pixels above the start,
travelling horizontally at the same 1 pixel per frame as a walk, about one block in total. Direction is
read from which side the hit came from, stored in its own byte. The arc ignores the player's current
momentum, which is why being hit mid jump drops you straight into the pit you were clearing. There is no
control until landing.

DECISION (WHP-01 to WHP-05, KNB-01 to KNB-03):

| Whip level | Reach | Damage | Animation | Hit lands | Recovery after hit |
| --- | --- | --- | --- | --- | --- |
| 1 | 24 px (1.5 blocks) | 2 | 12 steps | step 8 | 4 steps |
| 2 | 28 px | 3 | 12 steps | step 8 | 4 steps |
| 3 | 48 px (3 blocks) | 3 | 14 steps | step 9 | 5 steps |

Scaled down from 22 frames to 12 because our font and animations are shorter, and because 22 steps at 60
per second is nearly a third of a second of no input in a game where the player also has a menu.

Knockback: 16 pixels horizontal, 10 pixels of rise, 1 pixel per step, direction from the hit's side,
control locked until landing, then 30 steps of i-frames from the landing step. The design consequence is
the one the ancestor teaches and most clones forget: do not put a pit within 16 pixels of a hitbox that
survives one whip. A one whip enemy beside a ledge is not a challenge, it is a coin flip that looks like
a mistake.

## 8. Fair difficulty, as numbers

Fairness in our two ancestors is not a mood. It is a set of constants, and every one of them is in
data:

| Rule | Number | Where it comes from |
| --- | --- | --- |
| warning before any pattern | 12 steps, border flashes twice, no hazard on screen | our spec 08 |
| spawn exclusion | no hazard within 24 pixels of the marker | our spec 08, enforced by the arena even if a recipe asks otherwise |
| no late spawns | none in the last 12 steps of a pattern | our spec 08 |
| concurrency | 2, then 3, then 3 hazards; more needs a written note | our spec 09 |
| hard cap | 900 steps per phase, no hang possible | our spec 08 |
| damage floor | a hit costs the enemy's attack value, minimum 1 | our spec 07 |
| one hit per step | an overlapping hazard cannot re-hit inside i-frames | our spec 08 plus this file |
| player health | 20 start, plus 4 per upgrade | our spec 07 |
| determinism | one seed per battle, a retry shows the same shapes | our spec 09 |
| consistent damage | the damage an enemy does does not scale with the stage | S2: the US release made every enemy in a stage hit equally hard and scaled it upward, the JP release kept per enemy damage constant, and players read the JP version as the fair one |

That last row is the best free lesson in the study. Two releases of the same game, same art, same
controls; the one that keeps damage per enemy constant is remembered as easier in the good sense,
because a player can learn from a hit. We adopt constant per enemy damage and no stage scaling, which
our spec 07 already implies by giving each enemy an attack value.

Three more rules this study adds (FAI-01 to FAI-03): a rule change is labelled, not just executed; no
hazard may spawn inside the marker's 4 step trail; and every pattern ends at its declared length even if
the player is standing still, so a passive player sees the pattern finish and gets the clear chime.

## 9. Boss patterns in three phases, Percy and the Prometheus interruption

Spec 07 gives Percy 120 HP with three patterns and spec 09 gives him rain, wall and fan at 2, 3 and 3
concurrent hazards. This study turns that into a structure, DECISION (PHS-01 to PHS-04):

Phase 1, teach (100 to 70 percent HP). One pattern, rain, 2 hazards, marker free, no rule change. The
player learns what a hit costs.

Phase 2, change one rule (70 to 40 percent). The box narrows to 128 x 100, the wall pattern starts, 3
hazards. No new hazard type: the new thing is the space, not the bullets. 30 step break between phases,
marker re-centres, music layer 2 enters, health does not heal.

Phase 3, combine at speed (40 to 0). Fan enters, hazards move at 1.25 times phase 2 speed, 3 concurrent.
The rule set is now the phase 2 rule set, so the player is not learning a second rule under fire. All
three shapes have been seen once.

That "one new rule per phase, and never a new rule and a new shape in the same phase" rule is the whole
of the design. S3 gives the same shape in data: three values in one phase byte, each with its own full
set of behaviour, never a mixture.

The Prometheus interruption, at the 40 percent break of the Percy fight, is a spec 06 sequence and not
an arena feature:

1. The battle command returns a partial result: `battle_end = interrupted` at HP 40 percent, which the
   checker treats as a resolved battle, not an unresolved one (spec 06 rule 6).
2. `say` the interruption lines, `spawn` Prometheus at the arena's right edge, `shake` 2 pixels for 20
   steps, `music` crossfade to the interruption cue over 30 steps.
3. `branch` on the route flag: mercy and undecided go to the variant where Prometheus stops the fight,
   blooded and genocide go to the variant where he arrives late and Percy is already dead.
4. Each variant ends with `setflag` recording the route contribution (spec 10) and `end`, returning
   control with no press.

The arena never learns about Prometheus. It is asked for a phase, it gives one, and the director hands
control to a scene. That keeps spec 07 rule 7 intact ("the director asks spec 08 for a pattern and waits;
it never spawns hazards itself") and keeps the interruption authorable as data.

Kronos gets the same three phase skeleton with the rule change in phase 3 (marker speed 2.5) and, on the
blooded and genocide routes, a fourth phase that splits the marker in two. Hector gets two phases only,
because the ancestor's two phase bosses are the ones that are remembered as fights rather than as
gauntlets: pincer in phase 1, sweep with inverted horizontal in phase 2.

## 10. Mapping: every recipe to a spec

Specs read for this table: 06 cutscene runner, 07 battle director, 08 dodge arena, 09 bullet pattern
recipes, 10 route ledger, 16 talk command. Two gaps are real and are named as new specs, not smuggled
into an existing one.

| Family | Recipes | Maps to | Note |
| --- | --- | --- | --- |
| BRD, board and marker | BRD-01 to BRD-06 | spec 08 | BRD-05 and BRD-06 need a `marker_speed` field in spec 08, which spec 08 does not yet allow (it fixes 2) |
| IFR, invincibility | IFR-01 to IFR-05 | spec 08 (rules 4), spec 07 (health) | IFR-04 needs a new optional `iframes_mode` field in enemy data, spec 07's enemy schema |
| MRC, mercy | MRC-01 to MRC-06 | spec 07 (SPARE, TALK), spec 16 (talk options), spec 10 (route flag) | MRC-02 is a content rule for the dialogue data, so it lands in spec 05 and 16 |
| RUL, rule change | RUL-01 to RUL-07 | spec 08 and 09 (fields), and NEW spec 18 | the rule change fields do not exist in either spec today |
| JMP, jump | JMP-01 to JMP-05 | NEW spec 17 | no spec covers player movement outside the arena |
| WHP, whip | WHP-01 to WHP-05 | NEW spec 17 | as above |
| KNB, knockback | KNB-01 to KNB-03 | NEW spec 17, spec 07 (damage source) | knockdown direction is a player field, new |
| FAI, fairness | FAI-01 to FAI-03 | spec 08, spec 09, spec 07 | FAI-01 (labels) is a new UI element in spec 08's warning window |
| PHS, phases | PHS-01 to PHS-04 | spec 07 (patterns per boss), spec 09 (patterns), spec 06 (interruption), spec 10 (flag) | NEW spec 18 should hold the phase skeleton and the HP breakpoints, because spec 07's enemy data has one pattern list and no phases |

Two new specs to write, in this order:

- **NEW spec 17, action movement.** Player walk, stairs, jump arc (the table and the 4 step startup), the
  whip tiers with their reach and frame timings, knockback, the deep landing stun, and the debug tools
  (a jump arc overlay, a reach box for each whip level). Owner of the section 6 and 7 numbers.
- **NEW spec 18, boss phases and rule changes.** The phase skeleton (hp breakpoints in percent, 30 step
  break, marker re-centre, music layer), the rule change fields (`box_scale`, `marker_speed`, `invert`,
  `marker_count`, `hazard_mode`), the label rule, the interruption contract (`battle_end = interrupted`),
  and the check that a phase never introduces a new rule and a new hazard shape at the same time.

Both are counted in section 11 below as pending work, not done work.

## 11. P: lines, and what is not decided

P1. The dodge arena stays as speced (160 x 100, 8 x 8 marker, 2 pixels per step), and gains exactly one
input: a slow key at 1 pixel per step. Reason: the ancestor has one and our hardest patterns are built
for the same kind of box.

P2. Invincibility is 30 steps, starting on the hit, with a cadence mode kept in reserve for one optional
fight. Reason: half a second is the longest window a 20 HP player can be given without making enemy
attack values meaningless.

P3. Damage per enemy is constant and never scales with the stage. Reason: two releases of the same game,
one lesson, and the constant one is the one players call fair.

P4. The jump is a committed fixed arc on a 16 pixel grid, 4 step startup, 40 steps of air, apex 42
pixels, no air control, deep landings stun 10 steps. Reason: a single arc makes every gap a yes or no
and can be checked by script.

P5. The whip has three tiers at 24, 28 and 48 pixels, damage 2, 3, 3, and it does not hit before step 8
of 12. Reason: the level 2 tier in the ancestor is a damage tier with almost no reach, which is a good
shape and worth keeping.

P6. A boss changes one rule per phase and never a rule and a shape in the same phase. Percy: narrow box,
then speed. Hector: inverted controls. Kronos: marker speed, then two markers. Prometheus interrupts
Percy at 40 percent through a spec 06 scene, not an arena feature.

Q1 (for Nayil, one line, no action needed now): do the action segments get a whip at all, or does Percy
use the whip only in battle and a different verb in the corridors? Section 6 and 7 numbers assume a whip
in both, and spec 17 cannot be written until that is answered.

Not decided, and deliberately left alone: whether walking speed stays 1 pixel per step in the action
segment (the ancestor never raised it, and a 256 pixel wide frame at 1 pixel per step crosses in 4.3 s);
whether the slow key can be held during a phase's 12 step warning; and whether the two marker phase
survives the route ledger's genocide ending.

## 12. What this study could not get

- The Pine job for the Castlevania action numbers failed (S8), so the Castlevania figures here come from
  frame data and RAM documentation read directly (S1 to S6, S9). A second Pine attempt could confirm the
  jump table values byte by byte, but nothing in section 6 depends on those bytes: our numbers are our
  own decisions.
- No source gives exact pixel reach for the three whip levels in the third game. S4 describes the change
  in words only. Our three tiers are our own numbers, chosen to sit on a 16 pixel grid.
- Nothing here measures how a player reads a 12 step warning at 60 steps per second. That is a playtest
  question, and it is not answerable from documents.
