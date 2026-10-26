# Refinement backlog, 2026-10-26: every known gap in the 3 minute slice and the submission kit, ranked

Card `t_42c85e88` (H1 REFINEMENT-BACKLOG), gamedev. Written on the desktop node (CitadelArana), 2026-10-26
07:00 to 07:35 PDT, at HEAD `8220c95` with 1337 dirty porcelain entries and the baseline tag
`hackathon-baseline-2026-10-25` still naming `ae3a6cb`.

This is the first backlog written against the event itself. The format comes from
`knowledge/REFINEMENT-BACKLOG-TEMPLATE.md`; the evidence comes from commands this run ran, not from a worker
report and not from an earlier readiness page. Where a number here disagrees with `READINESS-2026-10-26.md`,
the disagreement is named in section 6 and the measurement behind it is printed.

Nine days. Submission is Wed Nov 4, 9 PM ET. Every row below is either carded in this run, already owned by an
open card, or reachable only by Nayil.

## 1. The ranking rule, stated once

Judging weights, from the card and `PLAN-WIN-2026-10-22.md` section 1: **Impact 30 per cent**, **Use of Meta AI
tooling 25**, **Technical depth 20**. The demo video is scored inside Demo at 25 and the brief calls it out by
name, so this file treats **Demo as a fourth axis at 25** and says so rather than folding it into Impact.
Creativity and theme fit are the remaining 25 and no row here can move them in nine days, so they are not scored.

Each row gets three numbers and one derived score:

- **W**, the axis weight above.
- **S**, severity on that axis. **3** means the axis cannot be earned at all while the gap stands. **2** means a
  judge sees a defect or a missing proof on that axis. **1** means insurance, spec consistency, or a defect no
  judge would see.
- **Score = W x S.** Maximum 90.

Order is **score descending**, then **effort ascending** (1 is 15 to 30 minutes, 2 is half a day, 3 is a day or
more), then **risk ascending** (1 touches no gate, 2 touches a gated artifact or a generator, 3 touches a gate
or a spec), then **leverage descending** (rows it unblocks). The order is what makes the table a plan instead
of a list.

Two statuses keep the table honest:

- **COVERED** means an open card already owns the row. The card id is named and no new card is opened for it.
  A backlog that re-cards work in flight burns the same nine days twice.
- **NAYIL** means no agent can move it. It keeps its true score, it sits where its score puts it, and it is not
  carded. Four rows in this file are NAYIL, and two of them can end the submission outright, which is the most
  useful thing this file says.

Nothing here weakens a test or a gate. Every check named below is a command that already exists in `tools/` or
`tests/`, run unchanged.

## 2. The ranked table

| Id | Kind | The gap, in one line | W | S | Score | Eff | Risk | Owner lane | Node | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RB-01 | SUBMIT | the Official Rules are not accepted on Nayil's account, and the terms make acceptance a precondition of any payout | 30 | 3 | 90 | 1 | 3 | Nayil | none | NAYIL |
| RB-02 | META | no live Meta call has ever produced a shipped asset: the bake is 18 of 18 fallback with `live` 0 and `calls_attempted` 0 | 25 | 3 | 75 | 2 | 1 | builder | desktop | CARDED |
| RB-03 | DEMO | the first fight has no green capture: the verifier is `ok false` on 5 of 7 checks and its 123.1 s recording shows no battle box and no FIGHT command | 25 | 3 | 75 | 3 | 2 | testing | desktop | CARDED |
| RB-04 | SUBMIT | the write-up and both scripts describe a route the recording does not contain, and their state paragraph is a week old | 30 | 2 | 60 | 1 | 1 | assistant | desktop | CARDED |
| RB-05 | DECISIONS | four `Q for gamedev` cards are blocked holding four lanes' work, and one of them holds the drive's whole look | 30 | 2 | 60 | 1 | 1 | gamedev | desktop | CARDED |
| RB-06 | SUBMIT | there is no public remote and no `LICENSE` a judge can read: one `backup` bare repo on this disk | 30 | 2 | 60 | 1 | 2 | Nayil | none | NAYIL |
| RB-07 | SUBMIT | no hosted demo link, so a judge must install GameMaker to see the game | 30 | 2 | 60 | 1 | 1 | Nayil | none | NAYIL |
| RB-08 | PALETTE | the drive's 12 stills are outside the 2C02 master set, exact share 0.0000 to 0.0167, and they are the S3 shot in every script | 25 | 2 | 50 | 1 | 1 | builder | desktop | CARDED |
| RB-09 | META | sam-3.1 has never segmented anything: no `segment` entry exists in `data/ai_cache` | 25 | 2 | 50 | 1 | 1 | builder | desktop | CARDED |
| RB-10 | META | the eye critic has never run on a Meta model: `data/eye_ledger.csv` carries no Meta vision row | 25 | 2 | 50 | 2 | 1 | builder | desktop | CARDED |
| RB-11 | AUDIT | the gate's 35 reds mix 9 real frame violations with 26 diagnostic sheets whose background area is 0 to 11 pixels | 20 | 2 | 40 | 1 | 2 | gamedev | desktop | CARDED |
| RB-12 | PARTY | `data/characters/party.json` is 295 B with one character, and no capture shows a stat number on screen | 20 | 2 | 40 | 2 | 1 | builder | desktop | CARDED |
| RB-13 | SUBMIT | the submission form's team section is unfilled and the field list is behind a login | 30 | 2 | 60 | 1 | 3 | Nayil | none | NAYIL |
| RB-14 | DEMO | the in-window log exists and is untracked: `EVENT-LOG.md` 360 B at 06:45 today | 30 | 1 | 30 | 1 | 1 | builder | desktop | CARDED |
| RB-15 | PALETTE | the crawl's white is `#F9F9F9` on 18,423 px, six levels off `#FCFCFC`, so RULE 0 is bent but gate 4 passes it | 25 | 1 | 25 | 1 | 1 | builder | desktop | queued |
| RB-16 | SOUND | the boarding cue is 32.000 s against a `ship_boarding` row of 208 authored steps, 3.467 s | 25 | 1 | 25 | 1 | 2 | musician | desktop | queued, waits on RB-05 |
| RB-17 | SOUND | `pp_fight_v2` landed but `data/audio.json` PP-04 still points at v1 | 25 | 1 | 25 | 1 | 1 | musician | desktop | queued, waits on RB-05 |
| RB-18 | LEDGER | no capture reads a ledger row back, while `tests/test_ledger.py` is green | 20 | 1 | 20 | 1 | 1 | testing | desktop | queued |
| RB-19 | SPRITE | 12 of 13 planned sprite sheets have a row; the thirteenth has an open card and no art | 20 | 1 | 20 | 2 | 1 | assistant | desktop | COVERED `t_bd32a72e` |
| RB-20 | CAPTURE | the live capture tools refuse while the machine is in use, so six readiness rows can only be re-earned in a quiet window | 20 | 1 | 20 | 1 | 1 | testing | desktop | COVERED `t_52166d5a` |
| RB-21 | ROUTE | the slice route is data and tests but nothing plays it: 4 rooms against 9 route steps, and the walk stops at step 3 | 30 | 3 | 90 | 3 | 3 | gamedev | desktop | COVERED `t_030a89e5` and `t_c024f8bc` |
| RB-22 | DEMO | the nightly recording passed every gated check and contains 0 footsteps, so the walk it exists to show is not in it | 25 | 3 | 75 | 1 | 1 | gamedev | desktop | COVERED `t_0badbb0c` |
| RB-23 | SUBMIT | the write-up's NES audit boast quotes a red count that overstates the art state (see RB-11) | 20 | 1 | 20 | 1 | 1 | assistant | desktop | waits on RB-11 |

RB-21 and RB-22 are the two highest scores in the project and both are already carded, which is the single most
important fact on this page: **the two things that stop the entry from being a game are not waiting on this
backlog.** They are waiting on a blocked card and a ready one.

## 3. The ten cards opened by this run

Each body carries Goal, Inputs, Output, Check, Must not, and the row it comes from. Assignees are the lane that
owns the file, not the lane that noticed the gap.

| # | Row | Card | Lane | Node | Depends on |
| --- | --- | --- | --- | --- | --- |
| 1 | RB-02 | META-LIVE-BAKE: one live Meta call replaces the fallback and the bake prints `source: live` | builder | desktop | the Meta key in the environment |
| 2 | RB-03 | FIRST-FIGHT-GREEN: `output/first_fight_verify.json` reaches `ok true`, or the card names which check is wrong | testing | desktop | a quiet window for the idle gate |
| 3 | RB-05 | DECISIONS-SWEEP: the four `Q for gamedev` cards get one rulings file and four unblocks | gamedev | desktop | nothing |
| 4 | RB-04 | KIT-REBASELINE: the one page and both scripts state today's route and today's seconds | assistant | desktop | the nightly recording |
| 5 | RB-08 | DRIVE-STILLS-LEGAL: all 12 drive shots inside the master set | builder | desktop | RB-05 ruling on the drive palette |
| 6 | RB-09 | SAM-SEGMENT-LIVE: one real `sam-3.1` segmentation recorded in `data/ai_cache` | builder | desktop | card 1, same key |
| 7 | RB-10 | EYE-CRITIC-META: the eye critic scores four real battle frames on a Meta vision model | builder | desktop | card 1, same key |
| 8 | RB-11 | AUDIT-TRUTH: the audit separates real frame violations from diagnostic noise, and the nine orphan frames go | gamedev | desktop | nothing |
| 9 | RB-12 | PARTY-STATS: one capture shows HP and WILL changing on screen | builder | desktop | RB-03 |
| 10 | RB-14 | EVENT-LOG-COMMIT: `EVENT-LOG.md` is tracked, generated from the baseline tag, and reads as item 9 needs | builder | desktop | nothing |

Lane load: builder 5, gamedev 2, testing 1, assistant 1. The builder lane is the bottleneck on this board and
RB-16 of `READINESS-2026-10-26.md` already says its work is what the art rows depend on. Cards 6 and 7 are
declared children of card 1 on purpose: all three need the same key, and a worker who finds no key should fail
one card, not three.

## 4. What this run measured, with the command beside each number

All runs on the desktop node, in `<repo>`.

| Measurement | Command or source | Result |
| --- | --- | --- |
| HEAD and dirt | `git rev-parse --short HEAD`, `git status --porcelain \| wc -l` | `8220c95`, 1337 entries |
| Baseline tag | `git tag -n hackathon-baseline-2026-10-25` | names `ae3a6cb`, message says work after it is in-window |
| Gate 4 | `python tools/nes_audit_all.py` | **EXIT 1**, `FAIL 183 file(s), 35 failing, 0 unmeasured` |
| Gate 4, the 9 real frames | same, `FAIL frame` rows | `gameover_preview` and the 8 `bg_battle_*_text_preview` / `*_fight_preview`, each `palette x4` |
| Gate 4, the 26 noisy rows | same, `FAIL sheet*` and `FAIL capture*` rows | `background_area` counts of 0 to 11 px, largest `title_run_1_marks_overlay` at 39 px |
| Master set | `tools/nes_check.palette_path(root)` then `data/nes_palette.json` | 55 usable colours of 64 |
| Frame legality, my own probe | Pillow over 25 output files against those 55 | `nes_title_frame` 1.0000; `crawl_mid` 0.9667 (`#F9F9F9` 18,423 px); `gameover_preview` **0.0000** (`#0B0B0F` 58,824 px); 8 battle previews **0.2222 / 0.4222** (`#1C1C24` 27,762 / 17,185 px); drive **12 of 12** between 0.0000 and 0.0167 |
| Orphan frames | `grep -rln` for each name over `tools/`, `tests/`, `data/`, `specs/`, `game/` and `git ls-files` | no tool writes them, no test reads them, git does not track them |
| Bake | `data/meta_bake.json` | 18 rows, `source` fallback 18, `bake.live` 0, `calls_attempted` 0, `mode` offline, model `muse-spark-1.3` |
| Model cache | `data/ai_cache` | 7 entries, `backend: mock` 6, 1 unparsed |
| First fight | `output/first_fight_verify.json` | `ok false`, `checked_at 2026-10-25T18:15:50`; `battle_box_in_sample` 0 frames, `fight_command_in_sample` 0, `victory_text_in_sample` 0, `battle_start_in_log` 0; video 123.1 s, 768x720, 60 fps |
| Last night's demo | `output/demo/nightly-2026-10-26_verify.json` | `ok true`, 73.483 s, 768x720 h264 60.00 fps, 7 of 7 on-palette, `run.failures` holds one line, `footsteps` 0 |
| Content that exists | `data/scenes/all.json`, `data/maps/all.json`, `ls game/rooms` | 15 scene rows and 48 ids, `drive_to_southampton` present, 0 game over ids; 5 maps including `southampton_town_quay`; 4 rooms |
| Party | `data/characters/party.json` | 295 B, one character, `max_hp` 20, `will_max` 3 |
| Build inputs | `python tools/check_build_inputs.py` | **EXIT 1**, `MISSING FROM COMMIT datafiles/streams/percy_theme_v3.ogg` and `_v4`, plus the two uncommitted sources |
| Project graph | `python tools/check_project.py` | `project graph and disk agree`, exit 0 |
| Submission docs | `ls -la README.md EVENT-LOG.md docs/` | `README.md` 16,081 B at 07:06 today, `EVENT-LOG.md` 360 B at 06:45 and untracked, `docs/architecture.png` and `.svg` at 07:03 |
| Board | read-only copy of `boards/nayil-ops/kanban.db`, `sqlite3` over `tasks` | 89 open cards: 67 blocked, 10 todo, 11 running, 1 ready |

No key, token or login file was opened, printed or copied. `PINE_SANDBOX_API_KEY` and `MODEL_API_KEY` are read by
their own tools from the environment and this run never touched either value; it never ran a Meta call, which is
exactly why RB-02 and RB-09 exist.

## 5. The four Q cards RB-05 has to answer, and what the answer decides

The rulings themselves are card 3's job, not this file's. What this file records is why each one blocks real
work, so the answer is written once and not four times.

1. `t_9275989a`, boarding cue. The musician cut `pp_boarding.ogg` to the 32.000 s beat that `SHIP-DECK-MAP`
   states, and `data/scenes/all.json` authors 208 steps, 3.467 s. Either the scene grows to the beat or the cue
   is recut. Both are cheap; doing neither leaves a 28 second gap between the horn and the door.
2. `t_f034f9d0`, drive palette. The `drive_night` role set exists in `data/room_palettes.json` and
   `data/scene_palettes.json` still has no drive entry, and the 12 stills measure 0.0000 to 0.0167 against the
   master set today. Card 5 cannot start without this ruling.
3. `t_279ef225`, fight cue. `pp_fight_v2` landed and nothing points at it; PP-04 still names v1, and the card
   asks 168 or 126 bpm. RB-17 exists only because this is unanswered.
4. `t_16417018`, title theme v7 and v8. **This one has moved on its own**: the two reds it named are gone, and
   `python tools/check_build_inputs.py` today exits 1 on `percy_theme_v3` and `_v4` instead, which is exactly
   `t_cdb3a6be` (builder, running). The ruling is now one line: v7 and v8 are not the accepted theme, the
   accepted theme is whatever `data/audio.json` names, and the percy pair belongs to that other card.

## 6. Where this file disagrees with the audit page, and why

Three disagreements, all measured, all in the direction of less work rather than more.

1. **`READINESS-2026-10-26.md` section 6 proposes `CRAWL-WHITE` as a defect.** The crawl is `#F9F9F9` on 18,423
   px, exact share 0.9667, and it is **not in gate 4's fail list today**: the audit tolerates it. So this is a
   RULE 0 consistency row at score 25, not a gate row at 50, and it does not enter the top ten.
2. **The same page proposes `PALETTE-REPORT-COMMIT` and `GAMEOVER-PREVIEW-LEGAL` as separate builder rows.** The
   first is done: `output/scene_palettes.json` is 13,949 B at 06:58 today, regenerated after the POSIX path fix
   in `8220c95`, and the Pine red it explains is the one that commit closes. The second is not a regeneration
   problem at all: `gameover_preview.png` is written by no tool in the tree, read by no test, and untracked by
   git, and it is one of 9 such frames. They are one row, RB-11, and the fix is deletion plus a class column in
   the report, not art.
3. **`t_16417018` (the title v7 and v8 question) is stale.** `check_build_inputs.py` no longer names either
   file. It names `percy_theme_v3` and `_v4`, which `t_cdb3a6be` already owns and is running. A backlog that
   re-carded that would send a worker to a red that does not exist.

One thing this page agrees with the audit about, and it is the important one: the fight capture is red, and the
card that used to own it (`t_87ee4228`) is closed. Card 2 is the reopen.

## 7. What this file does not do

- It does not re-card the drive scene, the arrival map, the slice route, the build step, the gate capture, the
  intro polish or the sprite rows: `t_c27552e3`, `t_c024f8bc`, `t_030a89e5`, `t_9d9b5b1d`, `t_d2b724e3`,
  `t_b50612ab` and `t_bd32a72e` hold them.
- It does not answer the four Q cards. That is card 3, and the rulings belong in
  `knowledge/GAMEDEV-DECISIONS-2026-10-26.md` with the measurements beside them.
- It does not move a number. Every row names a value a spec or a palette role already fixes; a row that needed
  a new number would have been carded as a spec change and sent to gamedev, and no row did.
- It does not publish, push, upload or spend anything.

## Provenance

No external code, art, dialogue or music is involved: this file is a ranked list of this repository's own gaps,
scored against the published judging weights and measured by this repository's own gates. The card format is
`knowledge/REFINEMENT-BACKLOG-TEMPLATE.md`. The weights are in `PLAN-WIN-2026-10-22.md` section 1 and in this
card's own body. Nothing was learned from a decompilation for this file.

Written by gamedev, 2026-10-26. The check for this file: it exists, section 1 states the rule that produces the
order, section 2 carries every row with the axis, severity, effort, risk, lane, node and the check that proves
it, and section 3 lists the ten cards with their lanes.
