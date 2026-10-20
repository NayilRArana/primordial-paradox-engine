# Clean-room review of the specs

Rule, set by Nayil and restated by the manager after the breach of 2026-10-19: no code is written from a spec that a
fresh reviewer has not confirmed from public genre design notes and the official GameMaker manual only. Specs 01 to 13
were drafted before the notice, so each of them starts as `pending` here.

This file is the ledger for that gate. `tools/check_spec_review.py` reads it:

- `python tools/check_spec_review.py` reports every pending spec by name and exits 0, so the debt is visible on every
  run without blocking work that is not derived from a spec.
- `python tools/check_spec_review.py --strict` exits 1 while any spec is pending. It is the check an implementation
  card runs before it writes code, and the check the gate card turns green.

A row may only say `confirmed` or `rewritten` when it names a reviewer and a date. `rewritten` means the spec text was
changed in that same change; the note says what changed and why. A row may not say `reviewed`, `checked` or `ok`.

| Spec | Status | Reviewer | Date | Note |
| --- | --- | --- | --- | --- |
| specs/01-state-machine.md | pending | code-review | - | - |
| specs/02-input.md | pending | code-review | - | - |
| specs/03-camera-and-scaling.md | pending | code-review | - | - |
| specs/04-overworld-rails-and-triggers.md | pending | code-review | - | - |
| specs/05-dialogue.md | pending | code-review | - | - |
| specs/06-cutscene-runner.md | pending | code-review | - | - |
| specs/07-battle-director.md | pending | code-review | - | - |
| specs/08-dodge-arena.md | pending | code-review | - | - |
| specs/09-bullet-pattern-recipes.md | pending | code-review | - | - |
| specs/10-route-ledger.md | pending | code-review | - | - |
| specs/11-save.md | pending | code-review | - | - |
| specs/12-audio.md | pending | code-review | - | - |
| specs/13-8bit-look.md | pending | code-review | - | - |

## What a pending row does not claim

It is not an accusation about the spec. It is a statement that no reviewer who has read only public material has yet
confirmed or rewritten it since the breach, and this repository does not get to assume its own innocence.
