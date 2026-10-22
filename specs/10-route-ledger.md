# Spec 10: route ledger

Status: spec, 2026-10-19, refreshed 2026-10-22 by card t_48020b30 (the per enemy exit rows and the fight verdict).
Numbers are DECISIONS.

Goal: the player never sees a score. They see consequences: an NPC comment, a different prison scene, and a final room
where one choice is refused.

Recorded (all saved, spec 11)
1. Counters: `bosses_killed`, `bosses_spared`, `regulars_killed`, `regulars_spared`.
2. Flags: named booleans set by scenes, triggers, dialogue choices and battle outcomes, for example `met_prometheus`,
   `ship_door_open`, `dc_gate_hacked`, `prison_entered`, `kronos_spared`.
3. Exit rows: the last fight as it happened, one row per enemy with `id`, `exit` and `round`. `exit` is one of
   `down`, `spared` and `turned`. The rows are cleared when the next fight starts, so what is kept is the fight the
   player just walked out of, which is what a summary screen or a line of dialogue about a particular enemy reads.
4. The fight verdict `verdict`: `quiet` when no enemy left down, `mixed` when at least one left down and at least one
   did not, `violent` when every enemy left down. It flatters the player on purpose while the rows underneath stay
   exact, so a soft word never hides what happened.

| Route | Condition | Effect |
| --- | --- | --- |
| undecided | no kills yet, before the prison | nothing yet |
| mercy | bosses_killed 0 and regulars_killed 0 | Prometheus prison scene; Kronos FIGHT refused |
| blooded | bosses_killed 0, regulars_killed above 0 | Prometheus scene plus two extra lines |
| genocide | bosses_killed 1 or more | Atlas prison scene; Kronos SPARE refused |

The route is derived on read and never stored, because two stored copies of one fact drift and then the save lies
about what the player did. The verdict follows the same rule for the same reason: it is a function of the exit rows,
so it is recomputed when they change and when they are loaded, and it is never written into the file.

Rules
1. Every kill and spare goes through one function; no scene increments a counter by hand. That function is the exit
   door below, and it is the only place in the tree that writes a counter.
2. SPARE and a wipe both count as a spare. A flee (not in the demo) counts as neither.
3. The checker cross references every flag name in data against the flag list, so a typo is caught before the game runs.
4. A trigger marked once records its flag, which is how doors stay open across a save and load.
5. Debug build: F3 lists counters, route, the last fight's verdict and rows, and every flag, and can flip a boolean; a
   flip is not saved unless the tester saves.
6. An enemy exit is recorded in one call, in this order: the row is written, the verdict is recomputed from the rows,
   then the counter moves. One call, one door, so a row and a counter cannot disagree, and a caller never increments a
   counter afterwards.
7. A turned enemy is neither a kill nor a spare: the fight stopped and a scene took over. It keeps its row and moves no
   counter, which is why the rows and the counters are read together rather than one standing in for the other.

Numbers: flag names up to 32 characters, lowercase with underscores; under 200 flags for the whole demo; the route is
recomputed per read and cached for the frame only. A fight holds at most 32 exit rows, a round is 0 to 9999, and an
enemy id is up to 64 characters with no spaces; a file outside those bounds is refused when it is loaded.

PP content: the prison split (Prometheus or Atlas), the Kronos forced kill or spare, and the High Street NPC whose line
changes at 0, at 1 to 2, and at 3 or more regulars killed. It is also what keeps no EXP honest: strength is a choice,
not a grind.

Acceptance (Nayil)
1. Kill every regular on Map 1: the NPC line changes to its third variant.
2. Spare everyone and reach the prison: the Prometheus variant plays.
3. Kill one boss and reach the prison: the Atlas variant plays.
4. Reach the final room on genocide: SPARE is refused visibly.
5. Flip a flag in the debug editor, save, relaunch, load: the flag is still set.
6. Spare one sailor and let the fight be stopped with another still standing: F3 reads `quiet` and lists both rows,
   one `spared` and one `turned`.
7. Put one enemy down and spare another in the same fight: F3 reads `mixed`, and the killed counter went up by exactly
   one.

Out of scope: a fight summary screen, per enemy dialogue variants that read these rows, a history of every fight in the
run (only the last fight is kept), a visible morality meter, endings beyond the two variants and the post credits scene.
