# Spec 09: bullet pattern recipes

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: every attack is a data recipe. The player never sees the recipe, only the shape: rain from the top, a wall with
a moving gap, a slow ring, a fan, a spiral, a sweep, a pincer, a lob.

Emitter fields
| Field | Meaning | Range |
| --- | --- | --- |
| at | step within the pattern | 0 to 899 |
| count | hazards in the group | 1 to 24 |
| spread | total angle covered | 0 to 360 degrees |
| origin | top, bottom, left, right, corner, or x,y in the box | named or numbers |
| speed | pixels per step | 0.25 to 4.0 |
| angle | direction, 0 is right, 90 is down | 0 to 359 |
| accel | speed change per step | minus 0.05 to 0.05 |
| curve | turn per step | minus 6 to 6 degrees |
| life | steps before despawn | 30 to 900 |
| sprite | hazard sprite id | registered ids |
| delay | steps between group members | 0 to 12 |
| wobble | sine amplitude and period | 0 to 8 px, 10 to 120 steps |

Shapes authors may build: rain, wall, ring, fan (aims at the marker at spawn time, never homing after), spiral, sweep,
pincer, lob.

Rules
1. Patterns are data only; no code path hardcodes a boss attack.
2. Deterministic: same pattern id, same seed, same step count gives the same positions, which makes patterns testable.
3. The 12 step warning is engine level (spec 08), so a recipe never telegraphs itself.
4. The arena enforces the 24 pixel spawn exclusion even if a recipe asks otherwise.
5. A pattern declares its length; the phase ends at that length plus the longest hazard life, capped at 900 steps.
6. Difficulty ladder: at most 2 concurrent hazards for a first pattern, 3 for a second, 4 for a third. More than 4
   needs a written fairness note in the enemy data.
7. One seed per battle, so a retried fight shows the same shapes rather than noise.

Testing: the checker validates every range and every sprite id; a preview room plays one pattern (spec 08 debug tools);
a GML unit test runs each pattern to its length and asserts no spawn inside the exclusion radius, no hazard outside the
box for more than 12 steps, and termination.

PP content: Percy's three attacks are rain, wall and fan; Hector uses pincer and sweep; Kronos reuses Percy's fan at
higher speed, which reads as the student outgrowing the teacher; the tutorial is one slow rain with two hazards.

Acceptance (Nayil)
1. Two patterns look different and the debug label names the shape correctly.
2. Changing one speed value in data changes the pattern with no code edit.
3. A speed of 9.0 in data is refused by the checker with the field named.
4. Replaying one pattern id twice shows hazards in the same places.
5. Percy's data shows 2, 3, 3 concurrent hazards, matching the ladder.

Out of scope: continuously homing hazards, gravity wells, destructible hazards, two enemy patterns combined.
