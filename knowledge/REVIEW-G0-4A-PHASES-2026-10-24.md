# Review: G0-4a enemy phases, are the thresholds only in data, is there no branch on an enemy name

Reviewer: code-review lane. Written 2026-10-23 03:20 PDT at the path card t_292c6f55 names.
Subject: card t_d1eb2a47, commit `2ff1b6d` (five paths), repaired by `76254a6`.
Reviewer wrote only this file in the project.

## Independence, stated first because it decides what this file is worth

This card (t_292c6f55) and the card under review (t_d1eb2a47) are both assigned to code-review, and code-review wrote
`2ff1b6d`. So this is the author's own check, run again from scratch, not a second lane's sign-off. Every number below
is reproducible from the commands named; the verdict is not independent. The implementer raised this on the card
before I started and I agree with it, so it is P1 rather than a footnote.

## What state was read

`git rev-parse --short HEAD` during this review: `c464edd` (another lane landed two commits after the subject).

| Input | State measured | Trusted as |
| --- | --- | --- |
| `data/enemies/all.json` | two phase rows at 70 and 40 landed in `2ff1b6d`; the working tree adds only G0-4b's enemy level `interrupt` block (another lane, uncommitted). The phase rows are identical at HEAD and in the tree | landed for the phase rows |
| `data/schemas/enemies.schema.json` | `phase` def landed in `2ff1b6d`, `hp_at_or_below` 1 to 99 percent, `additionalProperties: false`; the working tree adds the `interrupt` def (G0-4b) | landed for the phase def |
| `tools/check_data.py` | `PHASE_ROWS_MAX = 4` (line 65), `PHASE_ATTACK_BAND = (3, 6)` (line 66), `check_enemy_phases` (933) and `check_phase_talk` (988) landed in `2ff1b6d`; the working tree adds 59 lines of interrupt checking | landed for the phase checks |
| `game/scripts/pp_battle_director/pp_battle_director.gml` | clean at HEAD, 1010 lines | landed |
| `game/datafiles/enemies/all.json` | byte for byte identical to `data/enemies/all.json` (`diff` empty), and `tools/gen_project.py --check` exits 0 | the build copy is not a second home for the numbers |
| `specs/18-boss-phases.md` sections 1, 6, 7, 8 and `specs/07-battle-director.md` line 32 and acceptance 5 | read as written | the source of truth for the numbers |
| `knowledge/GAMEDEV-DECISIONS-2026-10-23.md` D4 (lines 57 and 58) | the only text in the tree that says "49 percent" | where this card's 49 came from |

Path correction: the card names `data/schemas/enemy.schema.json`. The file is `data/schemas/enemies.schema.json`.

Method: read the inputs, then three runs of my own in this card's workspace, with nothing in the project tree edited.
`probe_thresholds.py` recomputes each crossing from the GML's own formula and greps all 25 GML files under
`game/scripts` for enemy names and for the `* 100 <=` comparison shape. `mutate_checker.py` runs nine copies of `data/`
with one edit each through `tools/check_data.py --root`. `mutate_schema.py` does the same for three attempts to write
spec 18 section 6's own block. The repo's own gates were run as well: `python tools/check_data.py` exit 0,
`python -m pytest tests/test_enemy_phases.py` 19 passed, `python tests/test_enemy_phases.py` (the probe) exit 0,
`python tools/gen_project.py --check` exit 0. GameMaker is not installed on this host, so no GML was compiled or run:
the director's behaviour below rests on its text, pinned line by line, which is the same limit the implementer stated.

## Q1. Is the phase data the only place a threshold lives

Verdict: PASS. Two limits, F2 and F3, neither of them a threshold outside data for the crossings.

| Fact | Where it is measured |
| --- | --- |
| exactly one threshold comparison exists in the director | `pp_battle_director.gml:118` `return (_battle.enemy_hp * 100 <= _row.hp_at_or_below * _battle.enemy.max_hp);`. Over all 25 GML files, two lines hold the `* 100 <=` shape and line 114 is the comment for line 118 |
| it reads the row and the battle's own `max_hp`, never an absolute hp | same line; the highest absolute numbers in the file (84, 48, 120 and friends) are drawing coordinates at lines 677, 686, 803, 872 and 1001 |
| the two shipped integers are the only legal ones for the spec's crossings | enumerating 1 to 99 against `crossing_hp(t, 120) = t * 120 // 100`: only `t = 70` gives exactly 84 hp, only `t = 40` gives exactly 48 hp |
| 70 percent of 120 is 84 and 40 percent of 120 is 48 | `70 * 120 // 100 == 84`, `40 * 120 // 100 == 48`, printed by the probe and pinned at `tests/test_enemy_phases.py:128-129` |
| the card's own number is a misreading, not a rival ruling | 49 percent of 120 is 58.8 hp, correct as arithmetic; the crossing for threshold 49 is 58 hp, and 58 appears nowhere in spec 18. The spec's `49` is the hp floor of band 2 (section 6 table, "84 down to 49" in the hp column); 49 hp is 40.83 percent of 120, and a crossing at 49 hp would be written as threshold 41 (measured: `41 * 120 // 100 == 49`). The data follows section 6, and there is nothing to return to the data |
| percent, not absolute hp, is real | `70 * 60 // 100 == 42` and `40 * 60 // 100 == 24`, so halving `max_hp` to 60 moves both crossings and keeps the bands, which is spec 07 acceptance 5 and spec 18 section 8 P3 |
| the pool, the attack range and the TALK set only move through one function | writes exist at lines 93 (construction, from the enemy row), 132 and 133 (inside `pp_battle_enemy_phase_sync`, from the row being applied) and nowhere else |
| enemy hp has one door that syncs a crossing | lines 261 (a SPARE that ends the fight, so nothing more needs crossing) and 306 (`pp_battle_hurt_enemy`), with the sync at 311 behind `enemy_hp > 0`, so a killing blow crosses nothing |

## Q2. Does the director hold no branch on an enemy name

Verdict: PASS.

- `grep -rn -i percy game/scripts` returns exactly one line in 25 GML files:
  `game/scripts/pp_audio/pp_audio.gml:495:        case "percy":      return "text_blip_c";`. That is a per speaker blip
  voice in the audio module, introduced by `0fa9d0a` (INTRO-1, 2026-10-22 01:02) which predates `2ff1b6d`, and it is
  not on a battle decision.
- `grep -rn -E "\"(navy_sailor|deck_hound|hector|kronos)\"" game/scripts` returns nothing.
- Inside the director there is no enemy name at all. The only `switch` on a string is on room ids, lines 708 to 710
  (`"lower_deck"`, `"ship_cabin"`, `"deck_day"`, card R48). `_battle.enemy.name` is drawn twice, lines 809 and 938,
  and never compared. Nothing compares `enemy.id` either.
- Outside the director but in the battle code, the nearest thing to a name dependent path is
  `pp_battle_text.gml:314-315`, `string(_battle.enemy.id) + "|"` as a fallback key into the talk card index, used only
  when the card plus `talk_phase` key misses. A lookup keyed by an id that came from data is not a branch, and the
  primary key is data too (`encounter.talk.card` plus the row's own `talk_phase`, `pp_battle_text.gml:278-286`).
- The card's own CHECK sentence does not describe this tree. It expects the grep to return "the data load and the log
  line". Neither exists: no line loads an enemy by name (the enemy comes from `data/` through the encounter id) and no
  log line names one (the director's only debug print is the phase and the turn, line 168). Measured against the tree
  the answer is stronger than the card expected and differently shaped: one module names an enemy and it is audio.

## Findings

F1, medium, in the evidence artifact. The headless probe's last two lines are wrong. `python tests/test_enemy_phases.py`
prints `set 2 (at or below 70 percent, hp 84 to 1): ['percy_rain', 'percy_wall', 'percy_fan']`, but the pool from 84
down to 49 hp is `['percy_rain', 'percy_wall']` and the fan arrives at 48. Line 359 prints the pool at the second
crossing under a label claiming the whole 84 to 1 range, and "the two sets the card asks for" frames a three phase spec
as two sets. The per hp table above it (hp 120, 84, 48) and the two crossing lines are correct, so the probe is still
the evidence the card asked for; its summary is not, and it is the part a later reader will quote.

F2, medium, a limit of the gate. The checker does not pin the spec's numbers; a test does. Three mutations pass
`tools/check_data.py` with exit 0: row 1 at 49 (the card's own number), row 1 at 71 (crossing moves to 85 hp), row 2 at
41 (crossing moves to 49 hp). What the checker does refuse, each run here: threshold 0 (out of range, refused twice, by
the schema and by the checker), a pattern already in the pool above the row, an unknown `talk_set`, an attack on a
regular enemy, and a fifth row. So a wrong threshold is a data edit the checker will bless, and
`tests/test_enemy_phases.py` is what holds 70 and 40, for percy only. The split is right as designed; the note is for
whoever reads the checker's exit 0 as "the numbers are the spec's".

F3, low, a spec constant in code. `PHASE_ATTACK_BAND = (3, 6)` at `tools/check_data.py:66` is applied to every boss.
Spec 07 line 32 writes 3 to 6 for Percy and writes no band for Hector (140 hp) or Kronos (180 hp), so the second boss's
row is refused if its band differs from Percy's, and the band is not in data. Spec 18 section 7 asks the checker to pin
it, so this is deliberate; it is still one boss's number held for all bosses (Q1 to gamedev).

F4, low, wording. The schema's `phases` description says "The director applies the FIRST phase whose `hp_at_or_below`
the enemy's current hp has reached". The code applies every reached row, in order, in one `while` loop (lines 127 to
135), so a single blow that crosses two rows applies both. The sentence reads as if only one can apply.

F5, declared deviation, verified forced. Both rows name the phase 2 dialogue ids. Spec 18 section 6's block names
`talk_percy_phase3` and `percy_phase3_line` for row 2, and section 6 itself says those ids do not exist yet. Measured:
writing the spec's ids into a copy makes the checker refuse all three fields (unknown dialogue id twice, and
`talk_phase: percy_phase3` resolves to no card), so the shipped row is the only one the tree allows and follow-up
t_9319d333 owns the swap. Consequence worth stating: until then the 40 percent crossing changes the TALK set to the id
it already had and plays the same line, so phase 3 is a new pattern and a raised attack but not a new voice.

F6, outside this card's gap, decides the next one. Spec 18 section 6's own data block cannot be written today. Adding
`box_scale: [80, 100]` to row 1 makes the checker refuse the row, because the `phase` def has `additionalProperties:
false` and no `box_scale` (measured, exit 1). The card declared `box_scale` out of scope and that is correct; the
consequence to record is that section 6's block is unrepresentable until that card lands, so the shipped row is
section 6's numbers and not yet section 6's block.

## P: lines, for the manager and gamedev

P1. Independence. This verdict is the author's own, because card t_292c6f55 and t_d1eb2a47 are both code-review and
code-review wrote the commit. Either reassign the review to another lane before it counts as a gate, or record on the
board that G0-4a's check was a re-run by its author. Nothing here is unmeasured; what is missing is a second reader.

P2. D4 of `knowledge/GAMEDEV-DECISIONS-2026-10-23.md` should be corrected in one line. It reads "the 70 percent and 49
percent cuts", and 49 is the hp floor of band 2, not a percent. Spec 18 section 6, section 8 A18-5, spec 07 and the data
all say 70 and 40. This card repeated D4, so two documents carry the slip.

P3. The card's CHECK sentence cannot be satisfied as written, because no data load and no log line names an enemy. A
reusable form for this project: grep the enemy names under `game/scripts`, quote every hit, and name the module that
owns each one. That is what Q2 did.

## Q: lines, for gamedev

Q1. Does `PHASE_ATTACK_BAND` stay one constant for every boss, or move to the enemy row before Hector lands? Spec 07
writes a band for Percy only, and the checker as written would refuse a Hector row with a different band.

Q2. Is the probe's mislabelled two set summary (F1) fixed inside t_9319d333, or does it want its own card?

## Verdict

PASS on both questions the card asks: the phase thresholds live only in `data/enemies/all.json` (70 and 40 percent, the
only integers whose integer crossings are the spec's 84 and 48 hp) and the director holds no branch on an enemy name
(one name in 25 GML files, in the audio module, predating the commit). Six findings returned, none a defect in those two
questions: F1 the probe's last two lines, F2 the checker does not pin the spec's numbers, F3 the attack band is a spec
constant applied to every boss, F4 a schema sentence that understates the crossing loop, F5 the phase 3 dialogue ids are
the phase 2 ones by force until t_9319d333, F6 spec 18 section 6's block is not representable until `box_scale` lands.
