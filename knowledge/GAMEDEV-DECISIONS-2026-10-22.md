# Gamedev decisions, 2026-10-22: the four blockers and the slice's file owners

Card t_7ecd6549, GAME-ROADMAP-2, gamedev (head of build). This file is a ruling, not a discussion. Where a card or a
study disagrees with a line here, that line wins for this repository, and the card is wrong.

Why it exists. ARRIVAL-MAP (t_c024f8bc) did its work and then stopped on four questions it was not allowed to answer
on its own: the marker density rule, who owns `data/dialogue/all.json` and where a choice lives, five flags, and two
room palette sets. Every one of the four is answered below with a rule that can be checked by a test, and every card
struck by a ruling has its scope widened here.

---

## D1. Encounter markers: the density figure is about WILD markers only

The question. `knowledge/mechanics/PACING-AND-CUTSCENES.md` 6.2 states money figures of `1 marker per 40 to 60
walkable tiles, 2 on screen at most, none within 6 tiles of an entry, a door or a control handback`. The Town Quay
block has 1701 walkable tiles, so that sentence asks for 28 to 43 markers on one 3.3 by 3.7 screen block, which is a
fight every 8 to 12 seconds on foot, against a beat sheet that puts story fights 45 to 60 seconds apart. The card's
own CHECK inherited the contradiction and failed on it. This is a real defect in the study's phrasing, not in the
block.

The ruling. Split the marker kind, then the sentence applies to one of them.

| Kind | What it is | Rule it obeys |
| --- | --- | --- |
| `story` | authored in the map row, fires once, sets the scripted fight or scene | authored count wins; at most 2 on screen; none within 6 tiles of the entry, a door or a control handback; inert 20 steps after it fires; never re-arms |
| `wild` | generated for a random encounter table | 1 per 40 to 60 walkable tiles; at most 2 on screen; none within 6 tiles of the entry, a door or a control handback; no second wild marker within 225 walkable tiles of the last wild encounter fired, which is 45 seconds at the spec 04 free walk of 5 tiles a second |

Consequences, in order of force:

1. The density pair is a ceiling and a floor for wild markers, and the 225 tile spacing is the figure that makes the
   pair mean something. 40 to 60 tiles between markers is 8 to 12 seconds of walking, so read alone it contradicts the
   45 to 60 second fight cadence; read as a spacing floor plus the time spacing it does not.
2. A map that carries no wild encounters may carry any number of story markers inside the other three rules. The
   Town Quay block is such a map: it carries exactly 1 story marker, the scripted first encounter, and 0 wild.
3. `TEST-ARRIVAL-MAP` (t_3a52845d) is written against this table and not against the study's sentence. Its density
   assertion is: `wild <= 0` on `southampton_town_quay`, `story == 1`, and the four placement rules hold for every
   marker of either kind.
4. `data/maps/all.json` gains a marker `kind` field, default `story`, and a map level `encounters` field with values
   `scripted` or `random`, default `scripted`. ARRIVAL-MAP writes both on its own rows.

## D2. Dialogue: spec 05 wins, `pages` and `choices` are the canonical shape

The question had three parts: nobody owned `data/dialogue/all.json` in batch 1; the file's flat `lines` list caps at 9
lines while spec 05 and the arrival content need 4 and 6 pages; and no scene command can present a three option
choice.

The ruling, part by part.

1. Spec 05 wins over `dialogue.schema.json` as it stands. The schema is a description of the file, not a limit on the
   spec, and it is amended in the same commit that amends the file.
2. The entry shape becomes: `id`, `speaker`, and exactly one of `lines` or `pages`. `lines` stays legal forever as
   the one page shorthand, so the 14 existing ids and every committed test stay green. `pages` is a list of 1 to 3
   pages, each page 1 to 3 lines, each line at most 30 characters, which is the spec 05 box (30 by 3) and cap (3
   pages) with nothing new invented.
3. A choice lives in dialogue data, on the last page of an entry, as `choices`: 1 to 3 items, each `label` (at most
   12 characters, which is the menu column width), `sets` (a flag name from `data/flags.json`), and optional `goto`
   (another dialogue id). Picking one applies every flag in `sets` and then either continues at `goto` or closes the
   box.
4. There is NO `choice` scene command. `SCENE_COMMANDS` in `tools/check_data.py` and spec 06 stay exactly as they
   are: a scene `say`s the entry, the choice sets flags inside the box, and the next command `branch`es on the flag
   that was set, which the checker already validates against `data/flags.json` and `data/scenes/all.json`. This is
   the smallest change that reaches the screen and it adds no control flow to the cutscene runner, which spec 06 rule
   3 deliberately keeps to one `branch` command.
5. One writer owns the file: new card **R22 DIALOGUE-V2** owns `data/dialogue/all.json`,
   `data/schemas/dialogue.schema.json`, the dialogue check in `tools/check_data.py`, `game/scripts/pp_dialogue/` and
   the arrival rows from `knowledge/ARRIVAL-CONTENT.md`. ARRIVAL-MAP waits on it and never writes the file.
6. Engine obligation that rides with the ruling: `pp_dialogue` must apply `sets` before it closes the box. R22's
   check is a headless test that reads an entry with three choices, picks one, and asserts the flag is set in the
   save's flag block.

## D3. Flags: five names, appended, and the file has an owner

Ruling: `data/flags.json` is append only and never reordered or pruned. ARRIVAL-MAP's scope is widened to include it
and it appends exactly these five, in this order, after `kronos_spared`:

```
gate_passed, gate_truth, gate_bluff, gate_authority, has_boarding_pass
```

`gate_passed` is set by all three checkpoint replies, because the gate cannot be failed (ARRIVAL-CONTENT). The other
three are the three replies' own flags, and exactly one of them is set per reply. `has_boarding_pass` is set in the
dock office by Nye. The demo budget is 200 flags (`MAX_FLAGS` in `tools/check_data.py`) and the file will hold 14.

## D4. Room palettes: two sets, appended, and RULE 0 still comes first

Ruling: `data/room_palettes.json` is append only. ARRIVAL-MAP's scope is widened to include it and it appends exactly
two sets at the end of `sets`: `quay_night` (the Town Quay block after dark) and `office_night` (the dock office
interior). Each is at most 16 roles, every role is a name that already exists in the `roles` block of
`data/palette.json`, and neither adds a colour. Roles are named, never numbers, so a colour move in
`data/palette.json` still walks both sets.

RULE 0 (palette first) is not weakened by this: a role name that is already legal is being reused, not invented. A set
that needs a new colour is a `data/palette.json` change and a separate card with a NES legality check.

## D5. The network is never on the demo path

This is the Meta ruling the 30 cards are built around, and it is stated here because SPEC-19 and META-CLIENT both
point at it.

1. The game build makes no network call, ever, and holds no key. The shipped `game/` folder and the built datafiles
   contain no endpoint and no credential.
2. Every Meta model output the game shows is baked ahead of time by a tool into a plain data file under `data/`, next
   to the hand written fallback it replaces. `tools/meta_client.py` does the calling, `data/meta_bake.json` (chat,
   talk options, flavour lines) and the existing baked assets (art, music) are the results, and a bake file records
   `model`, `request_hash`, `created_at` and the fallback it shadows.
3. The demo therefore survives a dead network, a revoked key and a judge's laptop with no wifi, and it still shows
   Meta models in the loop in the recording, because the bake log is the evidence.
4. Both hook points from PLAN-WIN section 1 are in scope for the slice: the TALK command's three options for the
   current enemy phase, and Morgan's gate lines. A third, the critic loop (eye on frames, ear on music), stays in
   `tools/` and never touches the game at all.

## D6. Spec 19 (`specs/19-llm-talk.md`) section 0: approved, with the answers

Spec 19 landed and collected ten questions for the head. All ten are answered here and the spec is approved as written
with these answers folded in. A card that builds against spec 19 reads this table first.

| Q | Ruling |
| --- | --- |
| Q1 text shape | An array of at most 4 strings, each at most 28 characters. The game never word wraps a model sentence, and 28 plus the 2 character `* ` prefix is exactly spec 05's 30. |
| Q2 line geometry | 8 pixel pitch, four lines, box unchanged at 64 pixels tall. The 6 pixel advance at an 8 pixel pitch fits four lines in spec 05's 48 pixel text area. Growing the box is refused: it moves every UI layout, every capture region and the dodge arena origin for no play value. |
| Q3 reply shapes | Keep both. `effect` where the encounter names an effect table, `mercy_delta` for the rest. Spec 16's row is not retired, because the committed talk cards are written against it. |
| Q4 setback | -10, spec 16 section 2's existing row. No new number. One row for FIGHT damage and a bad talk keeps the mercy arithmetic single sourced. |
| Q5 NPC chat scope | In scope, two NPCs only: Morgan the gate sentry and Nye the dock office clerk. Both baked and replayed (D5), never live on the demo path. The rest of the roster stays canned. |
| Q6 narration marker | Code prepends `* `. The 46 glyph font cannot draw a model's own marker, and a model that writes one drifts out of it. |
| Q7 budget | Approved: 12 calls and 0.02 USD per fight, 0.05 USD per demo run. It is a bake budget, not a run budget, because the demo build makes zero live calls under D5. |
| Q8 profanity file | Create `data/talk_profanity.json` from a citable CC0 or public domain English list, keep the file in `data/`, and the guard is a lowercase substring check. |
| Q9 hint slot | A fourth line under the box in the second ink. The choice panel stays at spec 05's four entries. |
| Q10 who first | Morgan, then Nye. The roster's `petty_officer`, `gull`, `bilge_slime` and `deck_rat` keep their canned cards in the slice. |

---

## The file owner table for the slice

Batch 1 had two cards sharing `data/maps/all.json` and `data/scenes/all.json`, chained. Batch 2 adds three more
writers, so every shared file gets exactly one owner at a time and the chain is written down here.

| File | Order of writers | Notes |
| --- | --- | --- |
| `data/dialogue/all.json` | R22, then nobody | R22 lands the arrival rows for ARRIVAL-MAP as well |
| `data/maps/all.json` | ARRIVAL-MAP, then SHIP-DECK-MAP, then R21 DRIVE-SCENES | each appends its own map rows only |
| `data/scenes/all.json` | ARRIVAL-MAP, then R21 DRIVE-SCENES, then SHIP-DECK-MAP | R21 owns the drive block, 12 shots |
| `data/flags.json` | ARRIVAL-MAP only, append only | D3 |
| `data/room_palettes.json` | ARRIVAL-MAP only, append only | D4 |
| `tools/check_data.py` | R22 only for this batch | the dialogue check; other cards report, never edit |
| `data/slice.json` | SLICE-DEFINITION card only | it is the demo's own route, one row |
| `data/meta_bake.json` | META-BAKE card only, generated by tool | never hand edited |

A card that finds it needs a line in a file it does not own posts `Q: for gamedev` and blocks. It does not append
quietly, because a quiet append is how two workers lose each other's rows.

## What this unblocks

ARRIVAL-MAP (t_c024f8bc) is unblocked on these four rulings. Its workspace already holds the built and proven rows:
`arrival_maps.json`, `arrival_scenes.json`, `ARRIVAL-MAP-REPORT.md`, `prove_shim.py` (check_data exit 0 on the spliced
shim) and `verify_checks.py` (11 of 12). The remaining work is a splice of its own rows into five files, two of which
are now in scope and one of which is now another card's, and one test flip: its marker row changes to
`kind: "story"`, `encounters: "scripted"` and the check reads D1.

Provenance. No external code, art, dialogue or music was read or reused for this file. Every ruling above is this
repository's own spec 04, 05, 06 and 10 plus `knowledge/mechanics/PACING-AND-CUTSCENES.md`, which is our own
operationalisation of published manuals with its figures cited in place.

Written by gamedev, 2026-10-22. Check for this file: it exists, it answers D1 to D4 with a rule a test can read, it
names one owner per shared data file, and ARRIVAL-MAP is unblocked against it.
