# Genre design notes: how these mechanics work as GENRE mechanics

Source rule for this file (the clean-room rule in PLAN section 1): every note here comes from public descriptions of
how games in this genre PLAY, from general game design writing, and from our own reasoning. No decompiled code, no
game data files, no copied text, no character names, no numbers lifted from another game. A mechanic is free to use;
a specific game's expression of it is not. Where a number appears below it is our choice, marked DECISION.

## 1. Why the sub-genre works at all

The sub-genre is a turn based role playing game whose enemy turn is a short action dodging sequence rather than a
menu. It works because it splits one fight into two different pleasures:

- Thinking: choosing an action, reading an enemy's tells, managing a resource.
- Doing: two to fifteen seconds of movement under pressure, where skill matters and failure is cheap.

Because the two halves alternate, neither wears out. A menu only fight becomes arithmetic; a dodge only game becomes
reflex fatigue. Alternation also gives the player a natural breathing rhythm: think, move, think, move.

The cost is that the two halves must share one resource (health) and one clock (the turn count), or they feel like two
games stapled together.

## 2. Turn based battle with a bullet dodge phase

Genre pattern, as publicly described:
- A player phase with a menu of actions, then an enemy phase where the player controls a small marker inside a bounded
  box and avoids moving hazards.
- The box is a separate stage: the background dims, the box frames the action, and hazards enter from the edges.
- Damage in the dodge phase is per hit, not per second, so a good player can take zero.
- Some attacks telegraph (a warning frame, a flash, a sound) before hazards enter.

Design consequences worth copying at the genre level:
1. The box must be small enough that every hazard is readable and large enough that a careful player can thread it.
2. Telegraph beats fairness: a hazard that enters at the player's exact position with no warning feels like a cheat
   even when it is dodgeable.
3. Hazard count should climb with the fight, not with time: a boss's third attack may be denser than its first.
4. The player must always be able to see their own marker. Highest contrast object on screen.

DECISION for PP: arena box 160x100 pixels, marker 8x8, marker speed 2 pixels per step, with the keyboard vector
quantised to 8 directions and the analog stick read raw, both corrected on 2026-10-19 to match specs\02-input.md, which
wins where this file and a spec disagree (section 8 below). Every pattern has a telegraph of at least 12 steps.

## 3. ACT style talk options (our name: TALK)

Genre pattern:
- A menu of contextual talk actions per enemy, plus FIGHT.
- A talk action either reveals information, changes the enemy's mood, or unlocks a non violent ending to the fight.
- Correct talk choices accumulate into a visible state change (the enemy stops attacking as hard, or offers an exit).
- Talk options are content, not a puzzle with one hidden answer: several paths lead to the peaceful end.

Design consequences:
1. Talk options must be written per enemy, so they are data: a list of {label, lines, effect}.
2. The player needs feedback that talk is working, or nobody tries it twice.
3. A fight must be winnable by talking alone, or the mechanic is decoration.

DECISION for PP: four TALK slots maximum shown at once, each costing the player's action for that turn. Talking
never deals damage. Talking raises a "trust" counter; at 3 the enemy offers SPARE on its own turn.

## 4. Spare and kill routes

Genre pattern:
- SPARE ends a fight without killing, and is often unavailable until the enemy is weakened or talked down.
- Killing and sparing are both tracked across the whole game, and the world reacts later.
- The route is usually coarse (a flag, or a small count) rather than a moral score with a slider, because a coarse
  flag is what a writer can pay off in scenes.

Design consequences:
1. The route must be readable by the player before the payoff, or the ending feels arbitrary. One NPC who comments on
   the count is enough.
2. Neither route may be the "obviously correct" one in mechanical reward, or the choice is fake. Killing gives
   strength; sparing gives access and allies.
3. The ledger must be saved, not held in memory only.

DECISION for PP: see specs/10-route-ledger.md. Three named routes: mercy (no kills), mixed, genocide (a boss killed).

## 5. No EXP progression

Genre pattern:
- Fights give no experience points. Power comes from equipment, found items, story granted abilities, and health
  upgrades.
- Because grinding cannot fix a hard fight, encounter design has to be tuned tightly and every fight must be
  survivable with the gear the player is guaranteed to have.
- The benefit is pacing: the player never has a reason to walk in circles.

Design consequences:
1. Every enemy needs a designed counter, not a level check.
2. Bosses must be beatable by a first time player who has not fought optional enemies.
3. Rewards for winning non violently can be powers or items, so mercy is not weaker.

DECISION for PP: god powers come from defeated or spared enemies alike. The tutorial fight rewards a power on either
route. No stat growth from battle count anywhere.

## 6. FF3 style overworld

Genre pattern (the 8-bit console role playing tradition):
- Tile based maps with a character sprite on a grid, movement in four or eight directions.
- Towns, interiors and dungeons are separate maps entered through door or edge triggers.
- A world map with vehicle transitions (walk, ship, later flight) and scripted routes.
- Random or visible encounters at a designed rate, with safe zones near towns.

Design consequences:
1. A tile map is a grid plus a collision grid plus a trigger list. Three data files, not one.
2. Scripted movement ("rails") keeps a small game cheap: the player presses up and the story walks them down a street.
3. Interiors are small maps with a single exit rule; never a second navigation system.

DECISION for PP: 16x16 tiles, 16x15 tiles visible at 256x240, movement 4 directions at 1 tile per 12 steps when
free and 1 tile per 8 steps on a rail. Encounters are visible symbols on the map, not random.

## 7. Castlevania style sprites in battle

Genre pattern (the 8-bit action game sprite tradition):
- Side view figures built to read at small size: strong silhouettes, few colours, high contrast, clear weapon shape.
- Short loops (2 to 4 frames) for idle, walk and attack; impact is carried by pose and timing rather than frames.
- Bosses are large and use the frame budget differently: fewer frames, bigger shapes, more holds.

Design consequences:
1. At 32x32 and under, shape beats detail. Test every sprite as a black silhouette first.
2. Three or four colours per sprite including the outline; the palette is shared, so a sprite is a palette index map.
3. Animation is pose driven: anticipation, contact, recovery, and the contact frame is held 2 to 4 frames.

DECISION for PP: battle sprites are 32x48 for the player, 48x64 for characters, 96x96 or larger for bosses set in a
detailed backdrop. No sprite rotation. No more than 3 palette ramps per sprite.

## 8. What this file is NOT a source for

- No Undertale or Deltarune code, data, text, sprite, sound or "engine" of any kind was consulted for this file.
- No specific game's numeric tuning is reproduced. All numbers above are our design decisions.
- A future feature gets its own spec in specs\ before code. If a note here conflicts with a spec, the spec wins and
  this file is corrected.
