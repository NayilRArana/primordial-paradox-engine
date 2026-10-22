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

Reviewer: code-review. Date: 2026-10-19. Cards: t_ec0fb8be did the review and t_e78500a3 was the gate pass after it,
which re-read the manual pages the specs cite and added the two findings listed at the end of this file. The full
reasoning, including the three closest calls, is in the "clean-room re-review 2026-10-19" section of
`knowledge\PROVENANCE.md`; the module rows are in `knowledge\CLEANROOM-REVIEW.md`.

| Spec | Status | Reviewer | Date | Note |
| --- | --- | --- | --- | --- |
| specs/01-state-machine.md | confirmed | code-review | 2026-10-19 | Mode enum, one owner, one request door, fades and input lock are our decisions. What happens to the map under a battle is not asserted here and stays open as delta T1. |
| specs/02-input.md | confirmed | code-review | 2026-10-19 | Action table, one sample point and edge derivation from the manual's keyboard_check_pressed and Event Order pages; deadzone and repeat are ours. |
| specs/03-camera-and-scaling.md | confirmed | code-review | 2026-10-19 | Integer scale, one viewport and an application surface resize from the manual's page, whose own example is camera size times a resolution scale (re-read 2026-10-19). The page also states that Draw events draw to that surface while Draw GUI does not, which is what lets `display_set_gui_size(256, 240)` stand beside a scaled surface. Dead zone, look ahead and the 4 pixel cap are ours. |
| specs/04-overworld-rails-and-triggers.md | confirmed | code-review | 2026-10-19 | Tile grid, separate collision grid, trigger list, rails and visible markers are genre-design section 6; the trigger lock and marker respawn are our fixes. |
| specs/05-dialogue.md | confirmed | code-review | 2026-10-19 | Typewriter, portrait, pages and conditional choices are the ordinary text box of the genre; the geometry and the two control codes are ours. Its own text metrics do not fit its line length: 168 pixels of text area fits 21 characters at an 8 pixel advance, not the 30 it states. That is delta C4, a number for Nayil, not a clean-room finding. |
| specs/06-cutscene-runner.md | confirmed | code-review | 2026-10-19 | A data command list with one blocking command at a time and branch as the only control flow is the ordinary scripted scene form. |
| specs/07-battle-director.md | confirmed | code-review | 2026-10-19 | Five entry menu, trust and spare thresholds and no EXP are genre-design sections 3 to 5. Closest call: the turn loop shape, which is the spec's own phase list. |
| specs/08-dodge-arena.md | confirmed | code-review | 2026-10-19 | Box, marker, telegraph, damage per hit and invulnerability are genre-design section 2; every number is a PP decision. |
| specs/09-bullet-pattern-recipes.md | confirmed | code-review | 2026-10-19 | Data recipes and the fairness ladder are ours and need no public source: the emitter fields are our own generalisation, asked for by authoring needs. The angle convention is stated in screen terms while the engine's own maths runs the other way, which is delta C5 and is named there rather than settled here. |
| specs/10-route-ledger.md | rewritten | gamedev | 2026-10-22 | Additive refresh by card t_48020b30: the per enemy exit rows (an id, one of `down`, `spared` and `turned`, and the round) and the fight verdict (`quiet`, `mixed`, `violent`), plus rule 6 (one door, row then verdict then counter) and rule 7 (a turned enemy moves no counter), two acceptance cases and an out of scope line narrowed to name what is still not built. The source of the addition is `knowledge\FOX-STYLE.md` section 2 and this project's own spec 11, nothing outside the repo was read, and the counters, flags, derived route and their conditions are unchanged. |
| specs/11-save.md | rewritten | gamedev | 2026-10-22 | Additive refresh by card t_48020b30: an "Optional keys:" paragraph naming `fight_exits`, and rule 5 extended to say a load restores the last fight's exit rows and that a file without the optional key still loads with an empty record. Nothing in the 16 required keys, the format number, the backup rotation, the validation order or the manual citations changed, so the code-review verdict of 2026-10-19 on those parts stands. |
| specs/12-audio.md | confirmed | code-review | 2026-10-19 | Bus priorities follow the manual's audio_play_sound page (re-read 2026-10-19): the priority argument decides which sound is stopped when the channel limit is reached, and the third argument is a whole file loop. Crossfade is ours, built on the gain functions, not a manual feature. Rule 3's loop point claim is unsupported by that page and is open defect C1 in SPEC-DELTAS, not a clean-room finding. |
| specs/13-8bit-look.md | confirmed | code-review | 2026-10-19 | Palette size, dither and frame rules are ours; the sprite convention is genre-design section 7. The per pixel check in rule 2 cannot run yet, as delta C3 records. |
| specs/14-title-screen-drive.md | confirmed | gamedev | 2026-10-21 | Parallax layers at different scroll rates, a scrolling road and a title logo over a scene are the ordinary shape of a title screen and the shape the engine already had for the overworld (spec 04's camera and map). The scene itself is original: the two reincarnations driving from London to Southampton, the night drive and the waltz are Nayil's notebook and this project's own invention, and no element of it comes from a studied source. The pixel art, the palette, the 8 pixel font and the cue names are this project's own, checked by tools\art\make_title_ui.py against data\palette.json. The sound hook names are spec 12's cue idea. Reviewed against the public manual pages for sprite_add, draw_sprite_part_ext and audio playback, and against genre-design sections 2 and 7, and against nothing else. |
| specs/15-env-tiles-ship.md | confirmed | gamedev | 2026-10-22 | Read at the source on 2026-10-22 by card G0-3, which did not write this spec or its code. The hardware rules are the NES PPU's own (a 16x16 background area carries 3 colours plus the shared backdrop, an 8x8 sprite carries 3 plus transparent), restated from `data\nes_palette.json`, whose own citation is the NESdev wiki's PPU palettes page and the 2C02 `.pal` decode set. Every tile is drawn by `tools\art\make_env_ship.py` from geometry, with no sampled art: the placement, the 48 tile names, the solid flags carried on the tile rather than the map, the flag derived collision layer and the animation of the sea and the porthole glare are this project's own decisions. The 10 colour scene budget is stricter than spec 13's 16, so the two agree rather than conflict. Nothing outside this repository and that public hardware document was read for it. |
| specs/16-talk-command.md | confirmed | gamedev | 2026-10-22 | Read at the source on 2026-10-22 by card G0-3, which did not write this spec or its code. The one study reference the spec names is the ACT command as a DESIGN idea (a menu entry where the player speaks and the enemy answers), and a design idea is not protected expression, so nothing is taken from it: the system message, both enemy cards, the pool lines, the cache key, the validation pipeline V1 to V9, the clamp arithmetic, the offline keyword scorer and the budget are this project's own writing and engineering. The prompt is written as a data/instruction boundary rather than as a quoted prompt from anywhere, which is the safer shape and also the original one. Section 17 lists six deltas it opens, including spec 07's fifth menu entry and one sentence needed in spec 05; those are decisions for the manager and are recorded there, not settled here. Hostile input handling was judged as engineering, not as taken text: clamping, an allowlist schema with no extra fields, a fallback pool and a per battle call cap are our own choices. |

## What a confirmed row does and does not claim

It claims the spec's content is reachable from public genre design and the official manual, read by a reviewer who did
not open the quarantined copies. It does not claim the spec is correct: two factual defects are open in
`knowledge\SPEC-DELTAS.md` (C1 on audio loop points, C3 on the sprite pixel check), and both are recorded where they
belong rather than hidden inside a clean-room verdict. It also does not claim a text comparison against the quarantined
copy was made, because that comparison is the one thing the rule forbids.

## Gate pass, card t_e78500a3

The first pass read the specs against public material. This pass read them against each other and against the manual
pages again, and ran the arithmetic the specs state as if it were the acceptance test.

Pages re-read at the source today, all public, all five agreeing with the spec text:

- application_surface: the page's own example is camera size multiplied by a resolution scale, which is the pattern
  spec 03 uses, and it separates Draw events (this surface) from Draw GUI (not this surface), which is what makes
  `display_set_gui_size(256, 240)` correct next to a surface already scaled by the same factor.
- audio_play_sound: the priority argument decides which sound is stopped when `audio_channel_num` is reached, the
  third argument is a whole file loop, and the call returns a unique index. This confirms spec 12 rules 1 and 2 and
  leaves rule 3's loop point claim exactly as unsupported as C1 says.
- json_parse: an invalid value throws. Confirms spec 11 rule 6.
- Save/Load async event: `id` and `status`, on buffer_save_async and buffer_load_async. Confirms spec 11's file rule.
- json_stringify: an asset is stored as an internal handle whose index changes between runs, and assets are saved by
  name. Confirms spec 11's rule that ids are names, never indexes.

Arithmetic checked and found sound: 1080p at scale 4 is 1024x960 as acceptance 5 says; 256x240 is 16 by 15 tiles of
16 pixels; 900 steps is 15 seconds and 30 steps is half a second; 9 hues by 6 levels is 54; the FIGHT mapping in delta
T7 lands inside the 2 to 12 the spec promises.

Two findings, both new, both recorded rather than fixed inside a verdict, because each is a decision number and not a
traceability problem:

- C4, specs\05-dialogue.md: the stated 30 characters per line needs a 5.6 pixel advance, and the 168 pixel text area at
  an 8 pixel advance holds 21. Dialogue is the slice's main visible output, so this would have been found the hard way.
- C5, specs\09-bullet-pattern-recipes.md: the data says 90 degrees is down, the engine's own angle maths turns the
  other way, and the manual states that in a picture rather than in words. The fix is a named conversion in one place
  and one test, not a change to the authored data.

One conflict between a knowledge file and a spec was corrected here: `knowledge\genre-design.md` section 2 gave the
stick speed as 1.6 with an 8 direction clamp, while specs\02-input.md reads the stick raw and quantises only the
keyboard, and specs\08-dodge-arena.md takes its vector from spec 02. Section 8 of that file says the spec wins and the
file is corrected, so it now says 2 pixels per step with the keyboard quantised and the stick read raw.

