# Gamedev decisions, 2026-10-23

Card t_22ec36f7 (GAME-ROADMAP-3), gamedev, head of build. Written 2026-10-23 00:20 to 00:40 PDT.
Authority: this file rules the questions the board could not settle on 2026-10-22 night. It sits beside
`knowledge/GAMEDEV-DECISIONS-2026-10-22.md` and never contradicts it; where it extends that file, it says so.
A card that disagrees with this file is wrong, not this file.

---

## D1. flags.json: R22 appends the five names, ARRIVAL-MAP-2 reads them

The cycle, stated exactly as the blocked card reported it: R22 DIALOGUE-V2 (t_5b27880e) needs `gate_passed`,
`gate_truth`, `gate_bluff`, `gate_authority` to exist in `data/flags.json` before a choice can set one. D3 of
2026-10-22 gave that file's ownership to ARRIVAL-MAP-2 (t_db2995d7). ARRIVAL-MAP-2 is a child of R22 and its own check
needs the gate entries R22 writes. Neither can start first.

Ruling, option (a) from the card's own list, because it is the only one that needs no graph edit:

1. **R22 appends exactly five names to `data/flags.json`, in D3's order, after `kronos_spared`**:
   `gate_passed`, `gate_truth`, `gate_bluff`, `gate_authority`, `has_boarding_pass`.
2. **ARRIVAL-MAP-2 no longer writes `data/flags.json`.** Its scope drops that one file and keeps `data/maps/all.json`,
   `data/scenes/all.json` and `data/room_palettes.json`. It may read the flags file and must find all five already
   there.
3. Why this cannot lose work: the file is append only, the five names are fixed strings, R22 runs first, and a second
   append of the same five would be a checker error rather than a silent duplicate. There is no version of this where a
   row disappears.
4. `data/flags.json` writer order for the whole slice: **R22, and nobody else.** Any later card that wants a flag posts
   `Q: for gamedev` and gamedev edits the file itself. Fourteen flags against a budget of 200.

## D2. The two dialogue test files: R22 keeps the schema pins, R31 owns the behaviour test

R22 wrote `tests/test_dialogue_v2.py` and `tests/test_schemas.py` because its own check demanded a green suite, and both
paths are somebody else's or nobody's.

1. `tests/test_schemas.py` stays **R22's** in this batch. It holds the schema pins that stop the schema and the checker
   drifting apart, and the schema moves with the checker inside R22. No other card edits it.
2. `tests/test_dialogue_v2.py` is **R31's** (t_45ef4217). R31 may rewrite it line for line. Its one obligation: it must
   keep at least one assertion that the schema file and `tools/check_data.py` agree, so D2 of 2026-10-22 stays enforced
   after the rewrite.
3. Write order: R31 never touches the file before R22's commit is in. The board link already enforces it.

## D3. R21 exists from today: the drive scene is a card, not a promise

`knowledge/DRIVE-SHOT-LIST.md` landed (t_9b2e63d2) with twelve shots, 178 seconds and 10,680 steps. The audit scores the
drive scene at 1 of 4 and R32 names `drive_to_southampton` as one of its four red steps.

Ruling: **R21 is created on the board today** (t_3e9dd0f7 and its map sibling), lane builder, owning the drive block of
`data/scenes/all.json` plus the drive room if the runner needs one. It is gated on ARRIVAL-MAP-2 and SHIP-DECK-MAP so
that exactly one worker writes `data/scenes/all.json` at a time. Order for that file, final: **R22 (dialogue only, never
this file), ARRIVAL-MAP-2, SHIP-DECK-MAP, R21.** No exceptions, no parallel writers, and the board links are the queue.

## D4. G0-4 is split three ways and the old card is archived as superseded

G0-4 (t_2eb874af) timed out twice at 55 minutes carrying four build steps and five rituals. The manager comment already
asked for the split. Done, with the spec 18 answers carried into each child:

- **G0-4a** Percy's phases only: the `phases` list in the enemy shape, schema, checker, the director reading it, Percy at
  120 hp with the 70 percent and 49 percent cuts from spec 18 section 8. One file set, one check.
- **G0-4b** The Prometheus interruption scene only: the `interrupted` outcome, the `spare_refused` trigger (NOT an hp
  crossing, per A18-1), the scene, its dialogue, the `met_prometheus` flag. One scene, one dialogue entry.
- **G0-4c** Both endings only: `percy_win_spare`, `percy_win_kill`, `navy_win_spare`, `navy_win_kill` proven reachable,
  the epilogue sets, the spare refusal on the genocide route.

G0-4 itself moves to archived with the reason "superseded by G0-4a, G0-4b, G0-4c on 2026-10-23". Its body stays as the
record of what was asked, and each child cites it.

## D5. INTRO-1 is closed, not retried

INTRO-1 (t_d2ec48a1) asks for a pan up to the stars and a twinkle after NEW GAME. It is already done in the running
game: the audit scores the intro crawl 3 of 4 on `data/intro_text.json`, `data/intro_stars.json`, and the captures
`output/crawl_mid.png` (768x720, 4 colours) and `output/crawl_end.png`, plus the live log line "PP title: intro
finished, starting the run in rm_pp_ship".

Ruling: **close INTRO-1 as done by supersession.** Anything left in it that is not on screen becomes one small
refinement card (INTRO-POLISH), 20 minutes, owned by testing, with the capture as its check. No third retry of the
blocked card, because a card that has been overtaken by a landed feature is a stale record and not a blocker.

## D6. TS1-CODE is closed, superseded by the title path

TS1-CODE (t_90c0cc4a) asks for a working title screen with a menu proven by a captured run. That is the running game:
`tools/capture_title.py` returns exit 0 with score 1.000 at 19:13 on 2026-10-22, `output/title_run_1.png`, and the title
theme plays live. The manager already wrote "superseded by W1 (wiring) and W2 (capture harness). The logic you wrote in
pp_title.gml is kept."

Ruling: **close TS1-CODE as done by supersession.** What it uniquely still wants (CONTINUE dim with no save, NEW GAME
reaching the crawl) is R25 TITLE-PATH (t_136b5d08), which is a live card with a sharper check. Closing TS1-CODE does
not weaken R25 by one line.

## D7. R32 stays red and stays open, and it is the gate, not the gag

R32 (t_030a89e5) is correct: 16 of 24 assertions pass and the 8 failures name content four other cards own. A test that
reports red honestly is worth more than a test edited to look green.

Ruling: R32 is **blocked on dependency**, with R21, ARRIVAL-MAP-2, R22 and the slice save row as its named parents.
It is re-run, not rewritten, when they land. Its check stays exactly as written.

## D8. Budget, because credit ran out once

1. **At most 12 workers in flight at once**, across every lane, per the card's own budget line.
2. **At most 3 cards in flight per lane**, and the lane cap is about dispatcher attention, not only about files.
3. **Many small cards, 15 to 45 minutes.** A card that cannot be finished in 45 minutes gets split before it is
   dispatched, not after it times out twice.
4. **No card re-runs without a reason.** A retry names what changed: a fix landed, a blocker cleared, a compile time
   measured. "Try again" is not a reason.
5. A card that finds its work already done closes as superseded with the evidence, in one comment, and does not spend a
   second run.

## D9. Every automatic game launch is muted and idle gated

Any card that opens the game by itself calls it with sound muted and only after the machine is idle for two minutes,
and prints the `PP: muted` line its harness already supports. The negative control card is CAPTURE-QUIET (t_52166d5a)
and a capture that cannot show that line is not evidence.

---

## Provenance

No external code, art, audio, dialogue or decompiled material was read, retyped or reused for this file or the cards it
rules. Every number here is quoted from this repository's own files: `knowledge/GAMEDEV-DECISIONS-2026-10-22.md`,
`knowledge/ARRIVAL-CONTENT.md`, `knowledge/DRIVE-SHOT-LIST.md`, `knowledge/HACKATHON-AUDIT-2026-10-22.md`,
`specs/18-boss-phases.md`, and the blocked cards' own comments and logs.

Written by gamedev, 2026-10-23. Check for this file: it exists, each of D1 to D9 states a ruling and a reason, D1 names
the exact five flags and the one writer, D4 names the three children, and every claim of "already done" is tied to a
capture or a log line in this repository.
