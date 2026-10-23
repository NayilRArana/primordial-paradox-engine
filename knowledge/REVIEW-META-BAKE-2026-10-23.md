# R43 review: the Meta bake, four checks (task t_380f8661)

Reviewed 2026-10-23 by the code-review lane. Tree `<workspace>\Shared`, HEAD `43f4243` at the moment of
writing (HEAD moved from `62aa00c` to `43f4243` on another lane's battle background commit while this review ran, and
neither touches the artifact). The artifact under review is committed as `c862814` and `a41a52b` (R29 META-BAKE, task
t_f943951a). Scope of this review: the one file named on the card, plus its evidence. Nothing here was written by the
author of the bake, and every number below was measured in this run.

No key was read, printed or written. No endpoint, token or credential value appears in this file. The two key names
that the tools hold (`MODEL_API_KEY`, `META_API_KEY`) are named only where a check has to name them.

## How each check was measured

| Check | Method, and the probe that holds it |
| --- | --- |
| 1. No network, no key in the build | My own scan of every `.gml`, `.yy`, `.yyp` and `.json` under `game/` and under the shipped copy at `output/PrimordialParadox`, with a function and key name list of my own, not the project test. Two throwaway scripts, run against the tree in this session |
| 2. Every row traceable, every fallback exists | My own recomputation of all 18 `request_hash` values from the stored request echo, and my own lookup of all 18 fallbacks into `data/talk_cards.json` and `knowledge/GATE-DIALOGUE.md`, with the hash and the card reader re implemented rather than imported from the bake tool |
| 3. Fallback with the bake renamed away | A detached sparse worktree of HEAD (`r43-head`, since removed), the file moved, the tool run there. Transcript below |
| 4. The file cannot mislead a judge | Every one of the 18 rows read by hand, then three mutations of a COPY of the file and the replay run, each pushed through the tool's own `check_file` |

Standing checks rerun this run, all from the live tree:

- `python tools/bake_meta.py --check`: `meta bake check: 18 rows, 0 problems, 0 live, 18 fallback, no key, no URL, exit 0`.
- `python -m pytest tests/test_bake_meta.py -q`: 28 passed.
- `python tools/check_data.py`: all files pass.
- `python -m pytest tests/test_no_network_in_build.py -q`: 13 passed. That file is R34's (task t_72c3bc02) and it
  landed staged and uncommitted during this review, so the card's named input now exists; its own report line reads
  `604 files scanned (36 GML, 226 JSON), 5 credential names, 23 network functions allowed, 292 URL(s) seen in the
  tree, 20 citation file(s) exempt by their own bytes, 0 finding(s)`.
- `python tools/sync_data.py --check`: exit 1 on `game/datafiles/ui_layouts.json` only. That is another lane's
  uncommitted `data/ui_layouts.json` (`git status` shows it modified; the two shas differ). The meta bake mirror is
  current and byte identical: `data/meta_bake.json` and `game/datafiles/meta_bake.json` both hash
  `f5450e812767ed13f289965e96cf05b57cb59f7eb2e650be81da09f9b65a8ba4`.

## Check 1: the game never calls the network and holds no key. PASS

Measured on the tree, not taken from the test:

- 36 `.gml` files. Zero call sites for `http_`, `url_open`, `net_`, `network_`, `web_socket`, `request_url` or
  `socket` (0 hits each). The 6 `async_load` hits are the Async Save/Load event in `pp_save.gml:447-448` and its two
  doc comments (`pp_save.gml:11-12`), plus `obj_pp_game/Other_72.gml:2,4`; none of them is a transport.
- `game/PrimordialParadox.yyp` declares no Extensions at all (`"Extensions": []`), so no third party library can carry
  a transport either.
- `data/meta_bake.json`: zero occurrences of `http`, `Bearer`, `API_KEY`, `api_key`, `sk-`, `token`, `endpoint`,
  `localhost` or `127.0.0.1`. The same is true of its build copy.
- Key names exist only in `tools/meta_client.py` and `tools/bake_meta.py`, which are build time and outside the bundle.
- `grep -rn meta_bake game/ --include=*.gml` returns 0.

One limit a judge could hit, stated because it is true of the tree and not of this card: 15 shipped JSON files carry
URL strings as citation fields, in each of `game/datafiles/` and `output/PrimordialParadox/`, and no `.gml` names any
of them. The largest are `music_recipes.json` (66), `recipes/jrpg.json` (34), `osm_cache/winchester_high_street.json`
(29), `osm_cache/westminster_big_ben.json` (18), `maps/real_places.json` (12), `drum_patterns.json` (10),
`dissonance_rules.json` (10). They are inert strings and no code path opens them, so they do not breach check 1, and
R34's test agrees: it exempts a data file only when the file proves from its own bytes that it is a citation table or
third party geography, prints all 20 exemptions, and reports 0 findings. Its 20 are my 15 plus the five `data/`
sources those build copies come from (`dissonance_rules`, `drum_patterns`, `music_recipes`, `nes_palette`,
`talk_profanity`).

## Check 2: every row traceable, every fallback exists. PASS, with one declared deviation

Independent recomputation over all 18 rows, from the file alone:

| Fact | Measured |
| --- | --- |
| Rows | 18 |
| Distinct `request_hash` | 18, and all 18 recompute from `{kind, model, request}` with `kind` = chat |
| `model` on every row, and in the bake block | `muse-spark-1.3`, one value |
| System text binding | one `system_sha256` (`7beca544...`), 2408 characters, on all 18 rows |
| `created_at` | one stamp, `2026-10-23T05:04:32Z` |
| Row ids | unique; 3 each for `deck_hound`, `navy_sailor`, `percy`, `percy_phase2`, `morgan`, `nye` |
| Effects | `none` 4, `nudge` 4, `soften` 4, `setback` 4, `end` 2 |
| Fallback source | `talk_cards` 12, `gate_dialogue` 6 |
| Rows whose fallback does not resolve | 0 |

What the 18 fallbacks resolve to:

- 12 fight rows resolve into `data/talk_cards.json`: the card, the pool name and the index all exist, the pool has
  that index, and the row's `source_text` equals the card's line with a leading `* ` stripped.
- 6 NPC rows resolve into `knowledge/GATE-DIALOGUE.md`: `line_id` exists in the bank and the row's `text` is that
  line byte for byte.

Deviation, and it is the one R29 declared: `data/talk_cards.json` holds no `morgan` or `nye` card, so the card's
literal clause ("every row has a fallback that exists in `data/talk_cards.json`") is met by 12 of 18 rows and the
other 6 are traceable to the R38 line bank instead. Both halves check out; the wording of the clause does not. This
is Q1 below.

## Check 3: the fallback path with the bake renamed away. FAIL (the runnable part of the bake passes)

The shipped build has no reader for the bake file, so there is no fallback to observe:

- `grep -rn meta_bake game/ --include=*.gml` returns 0.
- `game/scripts/pp_data/pp_data.gml:100-112` is the one data loader and it names 8 files (`room_palettes`, `audio`,
  `slice` among them; the other five are `flags`, `items`, `palette`, `powers`, `project`). `meta_bake` is not one of
  them.
- `game/scripts/pp_battle_commands/pp_battle_commands.gml:13,33-34` holds TALK as a menu entry and a rail check, and
  no talk content path at all.
- The consumer, R30 TALK-BAKED (task t_8cd9c10a), is `todo` in the dispatcher with a blocked parent. Until it lands,
  renaming `data/meta_bake.json` away changes nothing the game can do; the check measures absence, not a fallback.
- `data/meta_bake.json` is nonetheless declared an Included File (`game/PrimordialParadox.yyp:126`) and mirrored into
  `game/datafiles/`, so the build ships a file nothing reads yet.

What I could run, in the worktree, is the bake's own offline path. Transcript, verbatim:

```
$ sha256sum data/meta_bake.json
f5450e812767ed13f289965e96cf05b57cb59f7eb2e650be81da09f9b65a8ba4 *data/meta_bake.json
$ python tools/bake_meta.py --check
meta bake check: 18 rows, 0 problems, 0 live, 18 fallback, no key, no URL, exit 0      (exit 0)
$ mv data/meta_bake.json data/meta_bake.json.bak
$ python tools/bake_meta.py --check
REFUSED: no bake file at data\meta_bake.json
meta bake check: 1 problem(s), exit 1                                                  (exit 1)
$ python tools/bake_meta.py --offline
meta bake: 18 rows, 0 live, 18 fallback, 6 skipped card(s), backend 'none', network false
  system text: 2408 characters, model muse-spark-1.3
  why: offline: --offline was asked for, so every row is the fallback
  fallback reason offline  18 row(s)
  skipped: card bilge_slime (no row in data/enemies/all.json, ...)
  skipped: card deck_rat (no row in data/enemies/all.json, ...)
  skipped: card gull (no row in data/enemies/all.json, ...)
  skipped: card petty_officer (no row in data/enemies/all.json, ...)
  skipped: card rogue_wave (no row in data/enemies/all.json, ...)
  skipped: card rope_knot (no row in data/enemies/all.json, ...)
  wrote data\meta_bake.json                                                            (exit 0)
```

With the file deleted, the offline bake rebuilt the document and the rebuilt document is identical to the committed
one except the timestamp: 18 rows, all 18 `request_hash` values equal, every other field equal, `created_at` moved
from `2026-10-23T05:04:32Z` to `2026-10-23T05:30:57Z`.

So: the bake tool survives the file being absent and regenerates a truthful fallback file (pass), and the game has
nothing to fall back from because it never opened the file (the card's check fails). The live tree was never without
the file: the run happened in a detached worktree of HEAD, and the claim it depends on, that no `.gml` names the bake
file, was measured again in the live tree (0 hits).

R34's test (which landed during this review) closes part of the gap in Python and no more: it rebuilds all 18 talk
requests from committed source data and looks each one up by `request_hash` in `data/meta_bake.json`, the rung 1
lookup of spec 19 section 8, with the network trapped. That proves the bake file serves the demo in Python. It does
not put a reader in the game, and no GML run exists that could show rung 2 or rung 3.

## Check 4: the file cannot mislead a judge. FAIL, one blocker

The rows themselves are honest. All 18 say `"source": "fallback"`, `"network": false`, and carry the reason
`offline: --offline was asked for, so every row is the fallback`; the shown `text` equals the fallback text on all 18
(measured); the header says `mode offline`, `offline true`, `network false`, `live 0`, `calls_attempted 0`.

The header can still be made to lie, and the tool's own check accepts it:

1. Measurements with `PP_AI_BACKEND=meta`, a placeholder key in the environment (value never printed, never used) and
   `PP_AI_MODE=replay`. `tools/meta_client.py:713-724` serves replay from the committed cache and never opens a socket;
   no cache entry matches these requests, so all 18 calls raise `CacheMiss` and every row falls back honestly with
   `reason` = `no live answer: ...`.
2. The bake block that same run produces:

```
"backend": "meta", "calls_attempted": 18, "fallback": 18, "live": 0,
"mode": "live", "network": true, "offline": false,
"note": "live answers from the Meta client, each one schema validated before it was written",
rows in the document: 18, live rows: 0
```

3. That block pasted onto the real 18 rows was passed through the tool's own `check_file`: **0 problems, exit 0**.
   So a file that says a live, networked bake happened, over 18 rows that all fell back and zero requests that left
   the machine, passes its own gate.

Root cause, file and line: the live decision is taken from the environment only, at `tools/bake_meta.py:598-618`
(`mode.update({"offline": False, "why": "", "network": True})` at line 616), and the note at
`tools/bake_meta.py:660-663` prints the live sentence whenever `mode["why"]` is empty. `_check_counts`
(`tools/bake_meta.py:958-974`) checks only one direction, `if not bake.get("network") and live:` at line 969, so a
header that says live with zero live rows is accepted. The transport's own verdict is discarded earlier: `chat()`
returns only the text (`tools/meta_client.py:856-867`), dropping the `cached`, `backend` and `mode` fields that
`_dispatch` computed at `tools/meta_client.py:703-706`.

The same defect fires on a real key that is revoked or exhausted in record mode: every call fails, every row falls
back, and the header still says live with the live note, because nothing compares the header to the rows.

Second hole, same class, measured: a fallback row's shown text is not tied to its fallback. Changing row 1's `text`
to `["A LIVE LOOKING SENTENCE."]` while leaving its fallback untouched passes `check_file` with 0 problems
(`tools/bake_meta.py:804-838` validates the reply shape and `:856-890` validates the fallback, and nothing compares
the two). A hand edit, or any future code path that writes model text into a row labelled fallback, would ship an
offline row carrying words no fallback ever held, and the gate would bless it.

Third, smaller: `reason` is only required to be non empty (`tools/bake_meta.py:826`); setting it to `because` also
passes. Nothing requires an offline row to say offline.

## Live versus offline, and agreement with the bake log

The file states 0 live rows and 18 offline rows, and four independent statements agree:

| Source | Live | Offline |
| --- | --- | --- |
| `data/meta_bake.json:19-35` bake block | `"live": 0` | `"fallback": 18`, `fallback_reasons {offline: 18}`, `calls_attempted 0`, `network false` |
| Rows at `data/meta_bake.json:106-1887` | 0 rows with `source live` | 18 rows with `source fallback` and `network false` |
| The bake's own report (`--offline`, pasted above) | `0 live` | `18 fallback` |
| R29's handoff on the parent card | `0 live` | `18 fallback` |

No disagreement found. The count is 0 live, 18 offline, and that is the truth of every call this bake made: none.

## Blockers

**B1. The bake block can say live and networked over zero live rows, and the gate accepts it.**
`tools/bake_meta.py:598-618` (the decision), `:660-663` (the note), `:958-974` (the one way count rule),
`tools/meta_client.py:856-867` (the transport verdict discarded). Measured twice: the replay run above, and the
header pasted onto the real rows passing `check_file`. This is the card's own blocker clause ("makes an offline row
look live") at the document level.

**B2. A fallback row's text is not tied to its fallback.**
`tools/bake_meta.py:804-838` and `:856-890`. Measured: a fabricated sentence in a fallback row passes with 0
problems. Fix shape: for `source fallback`, require `row["text"] == fallback["text"]` and `row["effect"]`,
`row["mood"]` and `row["hint"]` equal to the fallback's, the way `_check_talk_cards_fallback` already compares the
rest byte for byte.

## Defects and notes, not blocking

- **D1. The fallback does not follow the band the row records.** `tools/bake_meta.py:296-307` reads the `mid` band
  first for any card whose pool is written low/mid/high, and `:562` picks the line by option number,
  `(index - 1) % len(pool)`. Spec 16 section 9 step 5 (`specs/16-talk-command.md:205`) picks by mercy bucket and by
  `(fnv1a32(norm_line) + mercy_before) mod len(pool)`. The six rows for `navy_sailor`, `percy` and `percy_phase2` at
  options 1 and 3 record `mercy` 0 and 40 in their own `scene` while their fallback text comes from the mid band and
  the option index. Harmless for honesty; it means the line the row "shadows" is not the line the game would have
  picked at rung 2.
- **D2. `reason` is only required to be non empty** (`tools/bake_meta.py:826`). It should require the offline cause,
  not any string.
- **D3. `request_hash` is not recomputable inside the game.** It hashes `{kind, model, request}` with Python's sorted
  key JSON (`tools/bake_meta.py:448-456`), and the request echo carries `system_sha256` and `system_chars` for a
  system prompt that lives only in `specs/19-llm-talk.md` and is read by the tool at `:175-190`. GML struct
  serialisation cannot reproduce that byte string, so spec 19 section 8 rung 1 (`specs/19-llm-talk.md:389`, "looked
  up by `request_hash` over the assembled request") is not implementable as written. R30's own card keys rows by card
  plus phase and by npc plus turn, which works. Q2 below.
- **D4. The card's named input arrived during this review.** `tests/test_no_network_in_build.py` did not exist when
  the review started; R34 (task t_72c3bc02) wrote it while this ran, it is staged and uncommitted, and it passes
  (13 tests, 604 files, 20 citation files exempt by their own bytes, 0 findings). My hand scan of the same claim agrees
  with it file for file. What it does not cover, and this card does: the bake file's honesty about what produced it,
  and the game's side of the fallback ladder.
- **D5. `model` on a fallback row is the model the row would have asked, not the one that wrote it.** Every row and
  the block carry `muse-spark-1.3`; only `source` and `reason` say no model touched the row. A judge skimming a row
  sees a model name, a `request_hash` and a 2408 character system prompt hash before reaching `source`. A field named
  for that distinction (for example `asked_model` plus `model_used: ""` on a fallback row) would remove the doubt
  rather than argue it.

## Questions for gamedev

- **Q1** (open since R29, still unanswered): do Morgan and Nye get talk cards? If yes, six rows flip their fallback
  source and the card's literal clause becomes true.
- **Q2** (new): spec 19 section 8 rung 1 says the game looks the bake up by `request_hash`, and D3 shows that key
  cannot be recomputed in GML. May R30 key by card plus phase and by npc plus turn, with the spec amended to say the
  hash is an audit field?
- **Q3** (new): should a baked fallback follow the mercy band its row records (spec 16 section 9 step 5), or is the
  mid band deliberate? D1.

## What I did not measure

- No live Meta call was made, and none could be made from this session: `meta_client.key_present()` was measured here
  and returned False (client mode `record`, backend `meta`), so the live branch of the bake cannot run without a key.
  R29 proved that branch on its own card with `call_model` replaced; I did not re prove it. Check 4's blocker needed no
  key and no network: it was measured entirely in replay, where the client refuses each request itself.
- The game itself was not run. GameMaker LTS is installed on this PC (`C:\Program Files\GameMaker-LTS2026`), but no
  `.gml` reads the bake, so a run would exercise nothing in this review. Check 3's failure is a property of the tree,
  not of the runtime.
- `output/PrimordialParadox/` was scanned for URLs and key names only; I did not test the built executable, because
  no build of this commit exists on this machine.
