# JRPG mechanics study: Final Fantasy 1 to 3, Dragon Quest 1 and 2, Mother

Status: study, 2026-10-22. Author: research-assistant (Hermes profile), for Primordial Paradox.
Companion data: `data/mechanics/jrpg_recipes.json` (41 recipes, machine readable).
Scope: battle skeletons, turn order, damage shapes, encounter curves, XP and level curves 1 to 30,
escape, menu flow, grind control, and what each rule buys in feel.

## How to trust this file

Every number carries a tag.

- `[S1]` ... `[S14]`: cited. The source, its link and the date read are in section 12.
- `[inf]`: the author's inference. It is my arithmetic or my design judgement, not a statement about
  any shipped game. In the JSON the same recipes carry `"numbers_source": "author_inference"`.
- `[PP]`: a value that already exists in our project files, with the file named.

Nothing in the game text of another game is copied. Rules are restated in plain words and plain
numbers. Where a source gave a machine level expression (bit shifts, packed bytes) I state the
arithmetic in words instead.

One correction after the clean-room fix of 2026-10-22 (card t_aa9d2e7d). Shipped data may not carry a citation to a
third party study dump, so `data/mechanics/jrpg_recipes.json` now points every `source_ids` entry at this file and at
`specs/07-battle-director.md`, and the public page behind each tag stays here in section 12 where it belongs. Three
recipes were removed from the JSON because the only source behind them was the S3 row and nothing restated their
numbers inside this repository: DH-03 (stats as straight lines of level), DH-04 (HP thresholds that add flat damage)
and ME-03 (mercy gated by a coloured name). The family counts in section 10 are recounted from the file, and the
mercy mechanic is still described in section 7 where the menu flow is argued. DM-08 (the timed FIGHT bar) also cited
S3 and stays, because `specs/07-battle-director.md` carries the sweep and the 2 to 12 damage on its own.

Two honesty notes up front.

1. The Pine job that was supposed to return `mech-mother-battle.json` returned
   `mech-undertale-battle.json` instead. So Mother coverage below rests on my own reading of
   WikiBound and the Mother 1+2 level chart `[S13][S14]`, and Undertale is used where the card
   expected Mother. Undertale matters here because our own battle spec is already Undertale shaped
   `[PP specs/07-battle-director.md]`, so its numbers are the ones we will actually collide with.
2. Our game has no experience points, by decision `[PP specs/07-battle-director.md]`. The level 1 to
   30 curves below are therefore reference material: they tell us how fast the genre expected a
   player to gain power, and they give a defensible shape for scaling enemy HP. They are not a
   proposal to add levels.

## 1. The six battle skeletons, in one paragraph each

**Final Fantasy 1 (NES, 1987).** A queue of slots, not a speed race. Thirteen slots exist, enemy
slots and player slots, and the game shuffles two random pairs seventeen times before the round
`[S1]`. Agility never decides who goes first; it decides who dodges, because evasion is built from
agility `[S1][S4]`. Damage is subtractive with a random band. The design consequence is that a boss
can be given a fixed rhythm and the player still feels variance, without a speed stat to balance.

**Final Fantasy 2 (NES, 1988).** No levels at all. Stats grow from what you did: attack often enough
and Strength has a chance to rise, take enough damage and max HP rises `[S5][S6]`. Weapons and spells
have their own levels from 1 to 16, each needing 100 points on the Famicom release `[S5]`. Armour
costs evasion and magic accuracy, so every defensive upgrade is also a mobility downgrade `[S6]`. The
design consequence is identity through behaviour, plus a permanent temptation to hurt your own party
to farm HP.

**Final Fantasy 3 (NES, 1990).** Jobs. Character level raises stats, job level raises what the job can
do, and both are paid for with time `[S9]`. The brake on job switching is a shared Capacity pool of at
most 255 points for the whole party, spent when you change a job, discounted by your skill level in
the job you are switching into `[S8]`. Physical damage is subtractive, then multiplied by a hit
multiplier that depends on agility and level `[S9]`. The design consequence is that class identity has
a price and a memory.

**Dragon Quest 1 (NES, 1986).** One hero, one enemy, one command. A command phase then an action
phase. Damage is a ratio of attack minus half of enemy agility, so numbers stay small and readable
`[S2]`. Encounters are per tile, by terrain type, with a full 8 by 8 zone grid deciding which five
enemies can appear `[S2]`. The design consequence is that the map itself is the difficulty curve.

**Dragon Quest 2 (NES, 1987).** The same shapes with a party, plus a real initiative roll: half of
agility plus a uniform random 0 to 255, so early on luck beats stats `[S11]`. The design consequence is
that turn order becomes a soft, legible promise rather than a rule.

**Mother / EarthBound.** Levels exist, but growth is a smoothing formula rather than a table: in
EarthBound a stat moves toward a target average in proportion to how far behind it is, with bigger
jumps every fourth level `[S14]`. Mother 1 uses a much blunter rule: an increase of a constant plus a
random 0 to 3, halved and rounded down `[S13]`. The design consequence is that a character never falls
permanently behind its archetype, which is what lets Mother put a 12-year-old, a girl, a nerd and a
prince in one party.

## 2. Turn order and agility

This is the most valuable section for us, because our spec currently fixes player then enemy with no
speed stat, and each of the four gods will need its own exception.

**FF1: schedule first, agility elsewhere.** Thirteen slots, enemy slots 00 to 08 and player slots 80
to 83, then seventeen random swaps of two positions in the range 0 to 12; dead, petrified or absent
units are skipped `[S1]`. Agility has no place in this. Instead evasion is 48 plus agility minus
armour weight, so a lightning fast character is a character who gets hit less, not one who acts first
`[S1][S4]`.

**FF2: evasion doubles as initiative.** Evasion percent is agility plus weapon and shield evasion
bonus minus armour penalty, and that same evasion percent decides turn order `[S6]`. One number, two
jobs. The side effect is a snowball: high evasion raises agility, which raises evasion `[S6]`.

**DQ2: half agility plus uniform noise.** The initiative value is half of agility plus a random 0 to
255 `[S11]`. With agility in the twenties, the noise is worth twenty times the stat. Early game is a
coin flip and late game is a stat check, continuously.

**DQ3: agility plus twenty, scaled by noise.** The initiative value is agility plus twenty, multiplied
by a random fraction of 0 to 255 over 256 `[S11]`. Every unit keeps between 0 and 100 percent of its
value, so a slow unit can never move first against a unit four times faster, but can against a unit
1.5 times faster. This is the cleanest curve of the four: variance that shrinks relative to the stat.

**DQ1 and 2 on NES: the enemy gets authored first strike.** First strike is a property of the fight,
not of the stats, with 100, 50, 37.5 and 25 percent chances in the NES releases `[S11]`, and the DQ1
and 2 stat guide states plainly that order is totally random in those two `[S12]`.

**What the four give us.**
- A fixed schedule (FF1) is the cheapest to implement and the easiest to script a boss on. It is what
  our spec 07 already does `[PP]`.
- Uniform noise added to a stat (DQ2) is a one line formula and reads as chaos.
- Multiplicative noise (DQ3) reads as fairness and preserves hierarchy. Recommended for any fight with
  more than two units `[inf]`.
- An authored first strike chance (DQ1) is the strongest narrative tool of the four, because it lets
  the designer say "this god always shoots first" without inventing a speed stat.

## 3. Damage formula shapes

**Subtractive with a random band, FF1 physical.** Attack value is weapon plus half of strength. Damage
per hit is a random number between that attack value and twice that attack value, minus total armour,
with a floor of 1 `[S4]`. A critical hit keeps the same random band and adds it instead of subtracting
armour, so a crit is roughly damage plus armour rather than double damage `[S4]`. Elemental weakness on
a weapon adds 4 and is broken on the NES `[S4]`.

Why it feels good: the floor of 1 means no attack is ever wasted, and the band between 1x and 2x makes
every hit a small reveal. Why it is dangerous for us: subtraction plus a wide band is unreadable on a
20 point HP bar, where 1x to 2x of a small number is a rounding error.

**Subtractive, hit test on a 201 sided die, FF1.** Chance to hit is a base of 168 plus attacker hit
percent minus target evasion, capped at 255 before evasion is subtracted, then rolled against 0 to
200; 0 always hits and 200 always misses `[S4]`. The cap is a bug in the NES version, and it is worth
knowing because it means very high accuracy does not buy proportional hit rate `[S4]`.

**Spell damage with a resistance multiplier, FF1.** Effectivity E gives a random E to twice E. If the
spell passes its hit test the damage doubles; if the target resists the element damage halves; if the
target is weak damage is multiplied by 1.5 `[S4][S15]`. Net range for a resisted, failed-hit spell is a
quarter of the best case. That spread, not the absolute numbers, is what makes elemental knowledge
feel like power.

**Ratio damage, DQ1.** Damage is attack minus half of the enemy's agility, multiplied by a random 256
to 511, then divided by 1024 and truncated `[S2]`. In words: between a quarter and a half of the
effective attack, floor of 0 or 1 when the effective attack is 1 or less, decided 50 50 `[S2]`. A
critical is 1 in 32, ignores the enemy's defense, and lands between half of attack and attack, and can
still be dodged `[S2]`.

Why it feels good: ratios age well. A formula that always returns a quarter to a half of attack needs
no rebalancing when attack doubles, which is why the numbers in DQ1 stay small enough to read (a
slime pays 1 experience, the hero's endgame equipment costs 14,800 gold) `[S2]`.

**Per enemy dodge rates, DQ1.** There is no universal hit percentage. Dodge rates are given out of 64:
slime 1, ghost 4, poltergeist 6, demon knight 15, golem and both Dragonlord forms 0 `[S2]`. This is a
cheap, exact way to make one enemy feel slippery without touching the damage formula.

**Timed input as the damage source, Undertale.** The FIGHT command runs a moving bar; pressing confirm
at the centre maximises damage; letting the bar run out is a miss `[S3]`. Our spec already fixes the
numbers: the bar sweeps 0 to 100 in 60 steps and damage lands between 2 and 12 `[PP specs/07]`.

**Verification note.** The Pine summary of FF1 rendered the random range as "A...2A", which I first
read as a malformed multiplication. The Formulas thread confirms the notation means an inclusive
random range from A to 2A `[S4]`. Recorded here so nobody repeats that misread.

## 4. Encounter rates

**FF1: a step counter with a small set of values.** A battle starts when a countdown hits zero. The
unique counter values are overworld 11, 17, 19, 24, 27, 29, 30, 32, 40 and 49 steps, and dungeon 11,
24, 29, 30, 32, 40, 44 and 46 steps `[S1]`. The first post power on value is 15 lower than the table
value `[S1]`.

Two lessons. First, a discrete table rather than a percentage gives the designer an exact worst case:
the player always gets at least 11 steps of peace, and never more than 49. Second, dungeons are
tighter at the top end (46 against 49) but identical at the bottom: the floor of 11 steps is a
constant of the design.

**DQ1: per tile probability by terrain and zone.** On the starting zone, grass and bridges are 1 in 48,
forest and hills 1 in 32, desert 1 in 16. Everywhere else, including dungeons, grass is 1 in 24,
swamp and forest 1 in 16, hills and desert 1 in 8, stairs and chests 1 in 24, barriers and bricks 1 in
16 `[S2]`. Because it is a per tile roll there is no floor and no ceiling: back to back fights are
possible and the source calls this out as a reason the game feels grindy `[S2]`.

**DQ1: the zone grid.** The overworld is an 8 by 8 grid of zones, and each zone draws from five
possible enemies at roughly equal odds `[S2]`. This is the cheapest content economy in the study: one
number per tile position, five enemy ids per zone, and the whole map has a difficulty texture.

**Undertale: authored encounters per room.** Encounters are placed content, and the same monster can
be talked out of the fight, which is the mechanic our TALK and SPARE already extend `[S3][PP]`.

**Recommendation shape `[inf]`.** Use the FF1 counter, not the DQ1 tile roll, because a demo needs a
guaranteed floor of quiet steps. Take the DQ1 zone idea for enemy selection, because our map data is
already regional.

## 5. XP and level curves, levels 1 to 30

### 5.1 The cited anchors

FF1 cumulative experience to reach a level `[S1]`:

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XP | 0 | 40 | 196 | 547 | 1,171 | 2,146 | 3,550 | 5,461 | 7,957 | 11,116 | 333,651 |

The step from level 29 to 30 is 32,800 on its own `[S1]`.

DQ1 cumulative experience `[S2]`:

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XP | 0 | 7 | 23 | 47 | 110 | 220 | 450 | 800 | 1,300 | 2,000 | 65,535 |

DQ1 also gates spells on levels: heal at 3, hurt at 4, sleep at 7, radiant at 9, stopspell at 10 `[S2]`.
Its level 30 figure of 65,535 is the largest number a 16 bit unsigned value holds, so treat that
endpoint as a chart cap rather than a designed value `[inf]`.

### 5.2 The two curves are the same curve

Two independent teams, two different tables, one shape.

- From level 2 to level 10 the requirement grows 277.9 times in FF1 and 285.7 times in DQ1 `[inf]`,
  computed from the cited anchors.
- From level 10 to level 30 it grows 30.0 times in FF1 and 32.8 times in DQ1 `[inf]`, same base.
- Both curves fit a power law of the form requirement equals a constant times (level minus one) raised
  to a power near 3.

Fit on levels 3 to 10 (the body of the curve), then check against the anchors `[inf]`:

| Game | Fitted requirement | Worst error inside the fit | Error at level 30 |
| --- | --- | --- | --- |
| FF1 | 28.951 times (level minus 1) to the 2.6928 | 4.5 percent | fit is 1.33 times too low, so the real curve bends up at the top |
| DQ1 | 1.941 times (level minus 1) to the 3.0729 | 29.0 percent | fit is 1.08 times too low |

The DQ1 body error is large for one readable reason: levels 2 to 4 are hand set to 7, 23 and 47, which
is far cheaper than any smooth curve. That is a deliberate gift, and it is the single most imitable
thing in this section (see 5.4).

### 5.3 Level table 1 to 30, model output

Read this as a reproduction of the cited anchors plus interpolation `[inf]`. Marked values are the
cited anchors; all others are the fitted model, with the tail correction applied above level 10.

| Level | FF1 model | FF1 cited | DQ1 model | DQ1 cited |
| --- | --- | --- | --- | --- |
| 1 | 0 | 0 | 0 | 0 |
| 2 | 29 | 40 | 2 | 7 |
| 3 | 187 | 196 | 16 | 23 |
| 4 | 558 | 547 | 57 | 47 |
| 5 | 1,210 | 1,171 | 137 | 110 |
| 6 | 2,207 | 2,146 | 273 | 220 |
| 7 | 3,606 | 3,550 | 478 | 450 |
| 8 | 5,462 | 5,461 | 767 | 800 |
| 9 | 7,825 | 7,957 | 1,156 | 1,300 |
| 10 | 10,746 | 11,116 | 1,661 | 2,000 |
| 11 | 14,283 | - | 2,296 | - |
| 12 | 18,508 | - | 3,080 | - |
| 13 | 23,490 | - | 4,028 | - |
| 14 | 29,307 | - | 5,158 | - |
| 15 | 36,042 | - | 6,490 | - |
| 16 | 43,785 | - | 8,040 | - |
| 17 | 52,638 | - | 9,830 | - |
| 18 | 62,708 | - | 11,880 | - |
| 19 | 74,115 | - | 14,210 | - |
| 20 | 86,989 | - | 16,843 | - |
| 21 | 101,469 | - | 19,803 | - |
| 22 | 117,710 | - | 23,114 | - |
| 23 | 135,875 | - | 26,800 | - |
| 24 | 156,143 | - | 30,889 | - |
| 25 | 178,704 | - | 35,408 | - |
| 26 | 203,766 | - | 40,387 | - |
| 27 | 231,548 | - | 45,857 | - |
| 28 | 262,286 | - | 51,848 | - |
| 29 | 296,231 | - | 58,396 | - |
| 30 | 333,651 | 333,651 | 65,535 | 65,535 |

Per level increment near the middle, for pacing arithmetic `[inf]`: FF1 needs 3,094 more at level 10
than at level 9, 4,421 more at 12, 11,510 more at 20 and 23,885 more at 30. DQ1 needs 463, 679, 1,900
and 4,166 at the same levels. If a typical fight pays 4 to 20 experience, then DQ1's level 10 to 11
step costs roughly 23 to 115 fights and FF1's costs roughly 155 to 775 `[inf]`.

### 5.4 The discounted first level

FF1's anchor for level 2 is 40, while its own trend predicts 29, so the first level costs about 38
percent more than the trend `[inf]`. DQ1 inverts this: 7 against 2, a large discount. In both cases the
first transition is hand set. Read together, the design statement is that the first power gain is
authored, and the curve only starts obeying itself at level 3. That is exactly the behaviour we want
for a first power drop.

### 5.5 Growth by use, and growth by job (the alternatives to XP)

FF2 has no levels. Strength rises with a chance of about one in forty six per attack selected in a
battle, intellect one in twenty six per black magic cast, spirit one in sixteen per white magic cast;
these are checked against a random 0 to 45, 0 to 25 and 0 to 15 respectively, so a battle with one
attack is far weaker than a battle with three `[S5][S7]`. Max HP only rises if the character ended the
fight having lost at least about an eighth of maximum HP, and agility only rises if evasion was
already high `[S5][S6]`. HP, MP, vitality and magic power are grown by spending them `[S6]`.

FF3 pays job progress per action, not per kill: 100 points to a job level, no more than 100 points
counted from one battle, about 12 points for most fighting jobs, 8 for Dragoon, Dark Knight, Thief,
Ninja, Red Mage and summoners, and 4 for Onion Kid and most mage jobs; fleeing pays nothing `[S10]`.
Capacity costs 255 at most, shared by the party, reduced by one point for each skill level you already
have in the job you are switching into `[S8]`.

Mother smooths instead of tabulating. EarthBound's gain for offense, defense, speed, guts, vitality, IQ
and luck is the growth rate times the old level, minus ten times the old stat minus two, all scaled by
a factor of 3 to 6, or 7 to 10 on levels divisible by four `[S14]`. Mother 1 is cruder: constant plus a
random 0 to 3, halved and rounded down, with offense tracking the fight stat and defense tracking speed
`[S13]`.

## 6. Escape and death costs

**FF1.** Escape is a luck test: success if luck exceeds a random 0 to level plus 15. Battles flagged
preemptive always escape and flagged unrunnable never do `[S1]`. On the NES the routine is broken
because later party slots read unrelated data, so the nominal formula does not describe what actually
happens `[S1]`.

**DQ1, both directions.** An enemy runs when the hero's strength is at least twice the enemy's
strength and a 25 percent check passes, and it can check on the very first beat of the encounter. The
hero's escape is an agility test weighted by enemy class: enemies in the lowest id band count 0.25, the
next 0.375, the next 0.5, the highest 1.0; a sleeping enemy always lets you go `[S2]`.

**FF3.** Choosing run or escape puts the whole party in a vulnerable state for the round: defense and
hit avoidance drop to zero and incoming physical damage doubles, and monsters that run pay no such
penalty `[S9]`. That is the sharpest statement of intent in the study: escape is a move that costs a
round of safety, not a free exit.

**DQ1 death.** Death keeps the experience earned but takes half of the gold carried `[S2]`.

For us, escape currently does not exist: our spec lists several enemies at once, guard, status effects
and flee as out of scope `[PP specs/07]`. The DQ1 and FF3 pair is the reason to bring it back
carefully: a costed escape is a decision, a free escape is a menu item nobody thinks about.

## 7. Menu flow

**FF1.** Battle commands are fight, magic, drink, item, run, each with one sub level (magic needs a
spell and then a charge; drink offers a heal potion or a pure potion). Outside battle the menu is a
separate screen, and party order is edited from the field with a different button than the menu `[S1]`.

**DQ1 to 2.** Commands are entered for every character before any action resolves: a command phase,
then an action phase `[S2]` and the DQ2 guide describes the same three beats `[S11]`. This is a
different mental model from FF1's immediate resolution, and it changes how the player reads risk.

**Undertale.** Fight, Act, Item and Mercy on one row, with Mercy requiring the monster's name to be
coloured before a spare works, and some bosses simply removing the Mercy option `[S3]`.

**Our spec already decided the frame**: five entries, cursor starts on fight, cancel backs out one
level, a disabled entry draws in the second ink and makes a low blip rather than silently doing
nothing `[PP specs/07]`. That last rule is the best single line in the spec and it comes from a
failure mode the classics never solved: in several of them, an unusable action is simply refused with
the same cursor movement, so the player learns nothing.

## 8. Grind control

The classics used six distinct brakes, and every one is worth knowing.

1. **A prize worth hunting.** DQ1's metal slime pays 115 experience for 4 HP, is immune to magic,
   often deals only 1 damage on a non critical hit, and flees `[S2]`. Rare, dangerous, high value.
2. **A parallel currency with a price ladder.** DQ1 equipment runs 10 gold for a bamboo pole, 60 for a
   club, 180 for a copper sword, 560 for a hand axe, 1,500 for a broad sword, 9,800 for a flame sword
   and 14,800 for a silver shield `[S2]`. The next tier is always visible and always slightly out of
   reach, which converts grinding into a shopping plan.
3. **A free refill node.** The starting castle restores magic, which lets the player farm without
   paying an inn `[S2]`. Note that this is a grind enabler, not a brake, and DQ1's reputation for
   grind comes partly from it.
4. **A toll on changing your mind.** FF3's capacity pool means a job change is a purchase `[S8]`.
5. **Anti synergy between growth paths.** In FF2 raising strength can cost intellect `[S5]`, so
   generalists are punished by the system itself.
6. **A hard cap on what one fight can pay for.** FF3 discards job points above 100 in a single battle
   `[S10]`, so one big fight cannot substitute for a route.

For a game with no XP, brake 1 and brake 6 are the transferable ones: a rare enemy that drops the
thing you actually want, and a cap that prevents farming a single encounter.

## 9. Mapping the classic rules onto the four gods

Our four god forms carry a sickle, a thunderbolt, a trident and a bident, and the prong counts are a
free mechanical language `[PP knowledge/CHARACTER-BIBLE.md]`.

| God | Weapon | Classic rule borrowed | Numbers to start with `[inf]` |
| --- | --- | --- | --- |
| Konrad (Kronos) | sickle | FF1 slot schedule, edited by the boss | he inserts one extra action slot every third round, and his reaping blow deals 1.5 times damage to a target under 25 percent HP |
| Zander (Zeus) | thunderbolt | DQ1 authored first strike, plus FF1 hit test | 100 percent first strike at battle open, then a hit test of 168 plus 20 minus evasion; a chain arc halves damage to a second target |
| Percy (Poseidon) | trident | FF1 random band per hit, three prongs | 3 hits, each 45 percent of attack, each rolling its own 1x to 2x band, armour subtracted per hit |
| Hadrian (Hades) | bident plus helm | DQ1 per enemy dodge rates, plus unrunnable flag | 2 hits at 60 percent each, dodge rate 8 out of 64, and the battle is flagged unrunnable while the helm is up |

The point of the table is that no god needs a speed stat. Each god needs one authored rule change, and
each rule change is a mechanic the genre already proved.

## 10. The recipe set

Forty one recipes live in `data/mechanics/jrpg_recipes.json`, grouped by family. Every recipe carries the
rule with numbers, the source or the inference marker, why it feels good, and how it maps onto
Primordial Paradox.

| Family | Count | What it covers |
| --- | --- | --- |
| turn_order | 7 | slot schedules, uniform and multiplicative noise, authored first strike, boss rhythm |
| damage | 9 | subtractive bands, criticals, spell resistance, hit tests, ratio damage, multi hit |
| defense_hp | 2 | agility as defence, armour as a mobility cost |
| encounter | 5 | step counters, per tile rolls, zone grids, pity floors, authored tutorial fights |
| progression | 7 | FF1 and DQ1 curves, the discounted first level, growth by use, job points, Mother smoothing |
| escape_death | 4 | luck tests, weighted escape, the costed escape, partial death loss |
| menu | 2 | command rings, command versus action phase |
| grind | 5 | rare prizes, price ladders, free refill nodes, job tolls, anti synergy |

## 11. What we should do

Ten decisions, with the number to start with. Each one names the mechanics it accepts or rejects.

**Decision 1. Keep zero experience points, and buy the curve's pacing instead.** Accept the shape of
section 5, reject the mechanic. Our progression is powers and max HP only, per spec 07. The demo's
pacing target, taken from the DQ1 increment sizes rather than its totals `[inf]`: one power drop every
3 fights, 12 fights per act, so a player who never grinds still ends act 1 with 4 powers. The first
drop arrives after 2 fights, not 3, copying the discounted first level in 5.4.

**Decision 2. Enemy damage to the player uses DQ1's ratio shape, never FF1's subtraction.** A hero at
20 HP cannot absorb a subtractive band. Formula `[inf]`: damage equals the god's power minus half of
hero defense, multiplied by a random 256 to 511, divided by 1024 and truncated, minimum 1. Starting
values: a Navy Sailor power of 2 gives exactly 1; Percy at 3 to 6 gives 1 to 3; Hector at 4 to 7 gives
1 to 3; Kronos at 5 to 9 gives 2 to 4. Hard ceiling: no single bullet or contact hit above 5, which is
25 percent of the hero's 20 HP, so a player always survives four clean mistakes.

**Decision 3. Keep player first, then enemy, and give each god one authored exception instead of a
speed stat.** This is the FF1 lesson (schedule is cheap) plus the DQ1 lesson (first strike is content).
Zander opens with a guaranteed first strike. Konrad gains one extra slot every third round. Percy and
Hadrian keep the standard order and gain their edge in hit count and dodge rate instead. Reject DQ2
and DQ3 noise for the demo: with two units, noise produces no readable decision.

**Decision 4. Weapon prongs are hit counts.** Bident 2 hits at 60 percent each, trident 3 hits at 45
percent each, sickle and thunderbolt 1 hit at 100 percent. Every hit rolls its own random band and
subtracts armour separately, per FF1 `[S4]`. Expected totals `[inf]`: bident 1.2x attack against
armoured targets, trident 1.35x against unarmoured targets, which makes the trident the correct answer
against the Navy and the bident the correct answer against armoured enemies. That is a weapon choice
that exists in the fiction and in the numbers at the same time.

**Decision 5. Critical rate 1 in 32 for attacks, 1 in 16 for charged god powers, multiplier 1.5,
armour ignored.** DQ1's rate `[S2]` is the readable one at low numbers; FF1's additive critical `[S4]`
is unreadable on a 2 to 12 damage scale. Keep our existing 24 step popup `[PP specs/07]`.

**Decision 6. Encounters use an FF1 step counter with a floor and a ceiling, not a per tile
percentage.** Values `[inf]`, adapted from the cited FF1 sets `[S1]`: land 24 to 40 steps, ship
interior 16 to 29, dungeon 11 to 24. Hard floor 8 steps, pity ceiling 48 steps, both absolute. Reject
DQ1's per tile roll because it has no floor and that is the documented cause of its grind `[S2]`.

**Decision 7. Add escape back, as a costed action.** Chance equals hero agility divided by the sum of
hero and enemy agility, rounded to a percent, with the boss flag setting it to 0 and drawing the entry
in the second ink with the low blip from spec 07. Starting agility `[inf]`: hero 8, Navy Sailor 4, so
67 percent; Percy 9, so 47 percent; Kronos 12, so 40 percent. Cost, per FF3 `[S9]`: a failed escape
forfeits the hero's next attack and takes one extra bullet in the next pattern.

**Decision 8. Death costs half of what you carry, not the save.** Copy DQ1's half gold rule `[S2]` as
half of carried salves, rounded down, with powers and spoken trust kept. This is the difference
between a retry and a reload, and reloading is what makes players stop trusting a game's pacing.

**Decision 9. Menu: five entries plus a conditional sixth.** Fight, Power, Talk, Spare, Item, and Run
only when the battle is runnable. Cursor still starts on Fight, cancel still backs out one level,
disabled entries still blip. This extends spec 07 rather than replacing it, and the FF1 ring `[S1]` is
the precedent for a fixed five.

**Decision 10. One rare enemy per area, one free heal node per area, no shop ladder.** The rare enemy
has 3 times normal HP, appears at most once per 120 steps, and drops a power rather than currency
(this is the metal slime lesson `[S2]` with our no XP rule). The heal node restores HP once per area
visit, named and placed like DQ1's castle `[S2]`, so the player never has to choose between walking
back and fighting hurt. Reject gold, shops and inns entirely: they buy a grind loop we are not
shipping.

Two things I am explicitly not recommending. First, FF2's growth by self harm `[S6]`: it produces
degenerate play and would poison a TALK based game. Second, FF3's capacity pool `[S8]`: it is a
brilliant answer to a four character job system we do not have.

## 12. Sources, with the date each was read

All read 2026-10-22.

| Tag | Source | Link |
| --- | --- | --- |
| S1 | Pine result `mech-ff1-battle.json`, summarising the FF1 NES mechanics FAQ and walkthrough | local: `Shared/projects/arananet/pine/data/results/mech-ff1-battle.json`; underlying pages `https://gamefaqs.gamespot.com/nes/522595-final-fantasy/faqs/57009` and `https://gamefaqs.gamespot.com/nes/522595-final-fantasy/faqs/25809` |
| S2 | Pine result `mech-dq1-battle.json`, summarising the Dragon Warrior formula, experience, item and guide FAQs | local: `.../mech-dq1-battle.json`; underlying pages `https://gamefaqs.gamespot.com/nes/563408-dragon-warrior/faqs/61640`, `.../11908`, `.../27862`, `.../2993` |
| S3 | Pine result `mech-undertale-battle.json`, summarising Undertale Wiki encounter, SOUL mode, stats and attack type pages | local: `.../mech-undertale-battle.json`; `https://undertale.wiki/w/Encounter`, `https://undertale.wiki/w/Stats` |
| S4 | "FF Formulas" thread, the physical and magic damage derivations for FF1 NES | `https://gamefaqs.gamespot.com/boards/522595-final-fantasy/41701255` |
| S5 | Final Fantasy Wiki, "Stat growth", FF2 table of growth conditions and the FF3 Famicom multipliers | `https://finalfantasy.fandom.com/wiki/Stat_growth` |
| S6 | FF2 System FAQ (NES), evasion, turn order, growth categories | `https://gamefaqs.gamespot.com/nes/563414-final-fantasy-ii/faqs/82770` |
| S7 | FF2 Leveling-Up FAQ (NES), skill point formulas and enemy strength factor | `https://gamefaqs.gamespot.com/nes/563414-final-fantasy-ii/faqs/21734` |
| S8 | FF3 Capacity List, pool of 255, cost by job pair and skill level | `http://shrines.rpgclassics.com/nes/ff3/capacity.shtml` |
| S9 | FF3 Damage Formula FAQ (NES), attack damage, hit and evade multipliers, run penalties | `https://gamefaqs.gamespot.com/nes/563415-final-fantasy-iii/faqs/29389` |
| S10 | FF3 board thread quoting the job point values per action and the 100 point per battle cap | `https://gamefaqs.gamespot.com/boards/563415-final-fantasy-iii/80176026` |
| S11 | Dragon Quest Wiki, "Agility", turn order formulas for DQ1 to DQ3 and first strike chances | `https://dragonquest-wiki.com/Agility` |
| S12 | Dragon Quest 1 and 2 stat guide, agility as the basis of defense, random turn order in DQ1 and 2 | `https://gamefaqs.gamespot.com/snes/564868-dragon-quest-i-and-ii/faqs/64545` |
| S13 | WikiBound, "Status", Mother 1 and EarthBound growth formulas | `https://wikibound.info/wiki/Status` |
| S14 | Mother 1+2 level and stat chart, EarthBound stat gain formula and growth rates | `https://gamefaqs.gamespot.com/gba/914618-mother-1-plus-2/faqs/54159` |
| S15 | Final Fantasy Wiki, "Magic (Final Fantasy)", NES spell damage range, doubling, resistance and weakness multipliers | `https://finalfantasy.fandom.com/wiki/Magic_(Final_Fantasy)` |
| PP | our own project files: `specs/07-battle-director.md`, `knowledge/CHARACTER-BIBLE.md`, `data/powers.json`, `data/characters/party.json` | local, project root |

## 13. Gaps, and what I did not verify

- No Mother result was returned by Pine; Mother coverage is second hand through S13 and S14 only, and I
  did not verify Mother 1's own experience table.
- FF3's per action job points (12, 8, 4) come from a forum post quoting a damage formula FAQ `[S10]`,
  not from that FAQ directly. Treat as medium confidence.
- FF1's encounter values and escape routine are as the FAQ states them; the FAQ itself documents that
  the NES escape routine is buggy, so the nominal formula is not what a player experiences `[S1]`.
- I did not verify the FF2 "lose at least an eighth of max HP" threshold against a second source; the
  two GameFAQs authors disagree between an eighth and a ninth `[S5][S6]`.
- The level 1 to 30 tables above level 10 are model output, not cited values. Only the anchors in 5.1
  are cited, and the 5.3 table repeats them in their own column so the model can be checked.
- Enemy HP scaling for our 30 ranks (15 at rank 1 growing 13 percent per rank, reaching 519 at rank 30)
  is pure inference `[inf]`; it is not derived from any of the six games.
