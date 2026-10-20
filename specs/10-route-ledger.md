# Spec 10: route ledger

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: the player never sees a score. They see consequences: an NPC comment, a different prison scene, and a final room
where one choice is refused.

Recorded (both saved, spec 11)
1. Counters: `bosses_killed`, `bosses_spared`, `regulars_killed`, `regulars_spared`.
2. Flags: named booleans set by scenes, triggers, dialogue choices and battle outcomes, for example `met_prometheus`,
   `ship_door_open`, `dc_gate_hacked`, `prison_entered`, `kronos_spared`.

| Route | Condition | Effect |
| --- | --- | --- |
| undecided | no kills yet, before the prison | nothing yet |
| mercy | bosses_killed 0 and regulars_killed 0 | Prometheus prison scene; Kronos FIGHT refused |
| blooded | bosses_killed 0, regulars_killed above 0 | Prometheus scene plus two extra lines |
| genocide | bosses_killed 1 or more | Atlas prison scene; Kronos SPARE refused |

The route is derived on read and never stored, because two stored copies of one fact drift and then the save lies
about what the player did.

Rules
1. Every kill and spare goes through one function; no scene increments a counter by hand.
2. SPARE and a wipe both count as a spare. A flee (not in the demo) counts as neither.
3. The checker cross references every flag name in data against the flag list, so a typo is caught before the game runs.
4. A trigger marked once records its flag, which is how doors stay open across a save and load.
5. Debug build: F3 lists counters, route and every flag, and can flip a boolean; a flip is not saved unless the tester
   saves.

Numbers: flag names up to 32 characters, lowercase with underscores; under 200 flags for the whole demo; the route is
recomputed per read and cached for the frame only.

PP content: the prison split (Prometheus or Atlas), the Kronos forced kill or spare, and the High Street NPC whose line
changes at 0, at 1 to 2, and at 3 or more regulars killed. It is also what keeps no EXP honest: strength is a choice,
not a grind.

Acceptance (Nayil)
1. Kill every regular on Map 1: the NPC line changes to its third variant.
2. Spare everyone and reach the prison: the Prometheus variant plays.
3. Kill one boss and reach the prison: the Atlas variant plays.
4. Reach the final room on genocide: SPARE is refused visibly.
5. Flip a flag in the debug editor, save, relaunch, load: the flag is still set.

Out of scope: per enemy named kill records, a visible morality meter, endings beyond the two variants and the post
credits scene.
