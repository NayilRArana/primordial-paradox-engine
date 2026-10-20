# Clean-room review of the specs

Rule, set by Nayil and restated by the manager after the breach of 2026-10-19: no code is written from a spec that a
fresh reviewer has not confirmed from public genre design notes and the official GameMaker manual only. Specs 01 to 13
were drafted before the notice, so each of them started as `pending` here.

This file is the ledger for that gate. `tools/check_spec_review.py` reads it:

- `python tools/check_spec_review.py` reports every pending spec by name and exits 0, so the debt is visible on every
  run without blocking work that is not derived from a spec.
- `python tools/check_spec_review.py --strict` exits 1 while any spec is pending. It is the check an implementation
  card runs before it writes code, and the check the gate card turns green.

A row may only say `confirmed` or `rewritten` when it names a reviewer and a date. `rewritten` means the spec text was
changed in that same change; the note says what changed and why. A row may not say `reviewed`, `checked` or `ok`.

Reviewer: code-review. Date: 2026-10-19. Card: t_ec0fb8be. The full reasoning, including the three closest calls, is
in the "clean-room re-review 2026-10-19" section of `knowledge\PROVENANCE.md`; the module rows are in
`knowledge\CLEANROOM-REVIEW.md`.

| Spec | Status | Reviewer | Date | Note |
| --- | --- | --- | --- | --- |
| specs/01-state-machine.md | confirmed | code-review | 2026-10-19 | Mode enum, one owner, one request door, fades and input lock are our decisions. What happens to the map under a battle is not asserted here and stays open as delta T1. |
| specs/02-input.md | confirmed | code-review | 2026-10-19 | Action table, one sample point and edge derivation from the manual's keyboard_check_pressed and Event Order pages; deadzone and repeat are ours. |
| specs/03-camera-and-scaling.md | confirmed | code-review | 2026-10-19 | Integer scale, one viewport and an application surface resize from the manual's page; dead zone, look ahead and the 4 pixel cap are ours. |
| specs/04-overworld-rails-and-triggers.md | confirmed | code-review | 2026-10-19 | Tile grid, separate collision grid, trigger list, rails and visible markers are genre-design section 6; the trigger lock and marker respawn are our fixes. |
| specs/05-dialogue.md | confirmed | code-review | 2026-10-19 | Typewriter, portrait, pages and conditional choices are the ordinary text box of the genre; the geometry and the two control codes are ours. |
| specs/06-cutscene-runner.md | confirmed | code-review | 2026-10-19 | A data command list with one blocking command at a time and branch as the only control flow is the ordinary scripted scene form. |
| specs/07-battle-director.md | confirmed | code-review | 2026-10-19 | Five entry menu, trust and spare thresholds and no EXP are genre-design sections 3 to 5. Closest call: the turn loop shape, which is the spec's own phase list. |
| specs/08-dodge-arena.md | confirmed | code-review | 2026-10-19 | Box, marker, telegraph, damage per hit and invulnerability are genre-design section 2; every number is a PP decision. |
| specs/09-bullet-pattern-recipes.md | confirmed | code-review | 2026-10-19 | Data recipes and the fairness ladder are ours; pattern-as-data is the deliberate opposite of the studied design, so a difference not a copy. |
| specs/10-route-ledger.md | confirmed | code-review | 2026-10-19 | Counters plus a route derived on read match genre-design section 4 and single source of truth reasoning. Closest call: the never-stored rule. |
| specs/11-save.md | confirmed | code-review | 2026-10-19 | Versioned JSON, a .bak, a format check first and a try/catch around json_parse follow the manual's Save/Load and json pages. |
| specs/12-audio.md | confirmed | code-review | 2026-10-19 | Bus priorities and crossfade follow the manual's audio pages. Rule 3's loop point claim is unsupported by them and is an open defect in SPEC-DELTAS C1, not a clean-room finding. |
| specs/13-8bit-look.md | confirmed | code-review | 2026-10-19 | Palette size, dither and frame rules are ours; the sprite convention is genre-design section 7. The per pixel check in rule 2 cannot run yet, as delta C3 records. |

## What a confirmed row does and does not claim

It claims the spec's content is reachable from public genre design and the official manual, read by a reviewer who did
not open the quarantined copies. It does not claim the spec is correct: two factual defects are open in
`knowledge\SPEC-DELTAS.md` (C1 on audio loop points, C3 on the sprite pixel check), and both are recorded where they
belong rather than hidden inside a clean-room verdict. It also does not claim a text comparison against the quarantined
copy was made, because that comparison is the one thing the rule forbids.
