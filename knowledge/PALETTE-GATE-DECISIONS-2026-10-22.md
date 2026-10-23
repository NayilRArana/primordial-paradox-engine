# PALETTE-GATE-DECISIONS: the two R8 questions answered, with the numbers that answer them

Card t_4bafb4a1, gamedev, 2026-10-22. The questions came from card t_f6d404fd (AUTO-KAGGLE-ART round R8,
`kaggle-concept-art/R8_SELECTS.md` section 6). Both are palette decisions, so both are mine. This page is the
answer and the evidence. No em dashes, no en dashes.

## 1. The area constrained quantizer: wanted, and it is in tools\quantize_concept.py

Decision: yes, the stage is wanted, and it is not a new tool. `tools\quantize_concept.py` maps per 16x16
attribute area by default from now on (`--map areas`), and `--map free` keeps the old whole-set mapping for the
colour loss comparison. RULE 0 point 4 already says it: a background spends its 4 palettes by area, and no
palette crosses a 16x16 area boundary it does not own. The quantizer was the one place in the pipeline that did
not obey the rule the rest of the project is written against.

Why not `tools\nes_enforce.py`: it already does per area assignment, but for a frame with NO written set (a
capture, a title render), so it INVENTS 4 palettes with k means over the master palette. For a scene that has a
written set there is nothing to invent, and inventing gives colours the scene does not own. Measured on the best
R8 quay frame with the scene's own vocabulary handed to it, `nes_enforce.enforce()` still left 68 `palette_count`
failures and cost 8.18 mean delta E against 7.83 for the fixed-vocabulary pass. Two tools, two jobs, and the
docstrings now say which is which.

What the pass does, in one paragraph: for each 16x16 area, score the scene's 4 written background palettes by the
summed CIE76 delta E of that area's pixels against their nearest colour inside the palette, paint every pixel
through the cheapest one, keep the shared backdrop. At most 3 colours besides the backdrop per area and at most
the scene's 4 rows per frame therefore hold by construction, and `tools\palette_synergy.py` measures 0 background
problems on the result instead of 203.

Measured on the best R8 frame per subject (`quay_dusk_scene_i2i_seed01`, `deck_night_scene_i2i_seed03`,
`title_attract_i2i_seed05`, `drive_m4_night_i2i_seed01`), free mapping then area mapping, background rules
before and after:

| subject | scene | free dE | area dE | limit | verdict | palettes used | background fails before | after |
|---|---|---|---|---|---|---|---|---|
| quay_dusk_scene seed 1 | battle_quay_dusk | 7.35 | 7.83 | 10.0 | ACCEPT | 4 of 4 [158, 33, 44, 5] | 203 | 0 |
| deck_night_scene seed 3 | battle_deck_night | 7.65 | 8.04 | 10.0 | ACCEPT | 3 of 4 [170, 17, 53, 0] | 141 | 0 |
| title_attract seed 5 | title | 8.20 | 8.45 | 10.0 | ACCEPT | 4 of 4 [110, 52, 75, 3] | 201 | 0 |
| drive_m4_night seed 1 | westminster | 15.09 | 14.10 | 10.0 | REJECT | 4 of 4 [97, 94, 36, 13] | 363 | 0 |

Three of the four best frames now pass the colour half of the gate, at a cost of 0.18 to 0.48 mean delta E. The
drive subject stays rejected on colour (14.10) and that is a real answer: the westminster set cannot carry that
painting, and no seed change is going to fix a 4 dE gap. Note the area pass is not always the more expensive one
(14.10 against 15.09 there) because the free mapping snaps to the nearest master entry first and then jumps to
the nearest entry in the set, which is a two step error; neither number is a bound on the other.

The background half of the gate is not the whole gate: `tools\palette_synergy.py` also asks whether a sprite
separates from the ground it stands on, and no quantizer can answer that. R9 still needs a per frame look.

## 2. output\nes_title_frame.png: nothing is wrong with the frame, the measurement paired it wrong

Decision: the frame stays, the title set stays, the rule stays. The R8 control run put `percy_ow_v2.png`, a battle
cast sprite, on the title frame and asked whether it worked on the TITLE set. No frame can survive that: percy's
colours are not in the title scene's 4 sprite palettes at all, so `set_member` fires on all 8 frames, and with it
`palette_count` (no title sprite palette carries him), `white_blob` (his white body `$30` on the title ground
`$20`) and `body_ground` (one luminance row apart). 8 frames times 4 rules is exactly the 32 the report cites.

Measured here, same tool, same frame:

| pairing | scene | fails | rules |
|---|---|---|---|
| title frame alone, background rules | title | 0 | none |
| title frame, `nes_composite_check.py` | title | 0 | none, palette_count 4, 0 offending blocks |
| title frame + percy_ow_v2 (what R8 ran) | title | 32 | set_member 8, palette_count 8, white_blob 8, body_ground 8 |
| title frame + the title scene's own sprites (the audit entry) | title | 57 | body_ground 39, set_member 8, invisible 7, palette_count 2, same_hue_row 1 |

Every one of the title frame's 11 background colours is a written entry of the title set, so "it is not palette
correct for the title set" is false. The real defect the title pair has is `spr_pp_title_logo.png` (it spends
`$0B`, a background green, as a sprite colour; 39 body_ground and 7 invisible against the title ground), which is
already on the record as row 1 of `knowledge/PALETTE-PASS-LIST.md` at 57 fails and belongs to card TS2-ART-A
t_758934a8. Do not repaint the title frame for it.

The durable fix is in `tools\palette_synergy.py`: its docstring now says to pair a frame with a sprite from its own
cast, and that a sprite failing `set_member` on every frame is a pairing question before it is an art question.

### 2b. The control table re-run with scene matched sprites

Same tool, each frame against its OWN scene's cast from the audit entries in `data\scene_palettes.json`, with the
frame's background rules counted apart from the sprite pair, because they are two different claims:

| frame | scene | background fails | pair fails | pair rules |
|---|---|---|---|---|
| output\bg_battle_deck_night_frame.png | battle_deck_night | 0 | 32 | set_member 15, sprite_tile 8, palette_count 8, body_ground 1 |
| output\bg_battle_quay_dusk_frame.png | battle_quay_dusk | 0 | 24 | set_member 8, sprite_tile 8, palette_count 8 |
| output\nes_title_frame.png | title | 0 | 99 | body_ground 75, invisible 13, same_hue_row 7, set_member 2, palette_count 2 |
| output\bg_battle_corridor_frame.png | battle_corridor | 0 | 77 | set_member 48, body_ground 13, sprite_tile 8, palette_count 8 |
| game\sprites_src\bg\bg_battle_deck_night.png | battle_deck_night | 0 | 31 | set_member 15, sprite_tile 8, palette_count 8 |
| R8 best quay frame, as R8 quantized it | battle_quay_dusk | 203 | 227 | background_area 91, palette_count 120, set_member 8, sprite_tile 8 |
| R8 best quay frame, per area mapping | battle_quay_dusk | 0 | 24 | set_member 8, sprite_tile 8, palette_count 8 |

Two things this settles. One: every frame of ours is background clean, and the R8 quantized frame is the only one
that is not, which is exactly the quantizer finding. Two: the pair counts are all in the sprite layer (set_member,
sprite_tile, palette_count) plus the title sheet's own body_ground, so no frame choice fixes them. The quay row
uses `sailor_ow_v2.png` because battle_quay_dusk has no audit entry and no encounter authored yet, and that sprite
is not in the quay set either: whoever writes the quay fight picks the cast, and the set decides what it can carry.

The title pair moved from 57 fails (this page, section 2) to 99 during this card because
`game\sprites_src\title\spr_pp_title_logo.png` was rewritten at 22:07 by the redraw lane, not because anything here
changed. Numbers on a live redraw lane are a moving target; the doctrine row for it is unchanged and stays with
TS2-ART-A t_758934a8.

The R8 control table in `R8_SELECTS.md` section 6 should be replaced by the rows above before it is quoted again,
and the R9 measure script should call `quantize_concept.quantise_areas(before, scene)` or
`quantize_concept.convert(..., mapping="areas")`; it currently calls `quantise(...)`, which is the free mapping and
is what produced the 203.


## 3. What this does not decide

- The threshold. 10.0 mean delta E stays where it is; three of four R8 subjects sit under it now, and moving a
  limit to make a picture pass is not a decision, it is a fudge.
- The 26 queued sprite sheets, the other 8 scene sets, and the strength sweep (0.45, 0.65) are untouched.
- Whether a frame reads as the beat. That is an eye, not a delta E.

Files this decision changed: `tools\quantize_concept.py` (per area mapping, `--map`, both numbers reported),
`tests\test_quantize_concept.py` (12 tests, 3 of them cross-tool against `palette_synergy`),
`tools\palette_synergy.py` (docstring pairing rule), this page, `DEVLOG.md`.
