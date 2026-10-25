# Palette rulings, 2026-10-24: the deck's pair half, and what a battle figure is

Card `t_af6fd431`, gamedev. The question came from card `t_d6653aec` (AUTO-KAGGLE-ART R13): the deck subject fails
the pair half on every frame with exactly 3 problems, all `set_member` on `game/sprites_src/chars/sailor_battle.png`,
and the lane asked for a ruling between (a) a repaint of that sheet in the treatment `sailor_ow_v2.png` got at
08:15:08 and (b) adding $36, $08 and $27 to `battle_deck_night`'s sprite palettes in `data/scene_palettes.json`.

Read with: `knowledge/ART-BIBLE.md` RULE 0 (point 2 gains one sentence from this ruling), `data/scene_palettes.json`,
`data/palettes/scene_battle_deck_night.json`, `data/palettes/scene_ship.json`, `tools/palette_synergy.py`,
`data/sprite_redraw_queue.json` (Q2, Q4, Q5), `knowledge/genre-design.md` section 7.

## 1. The answer

Neither. (a) is refused, (b) is refused as written, and the decision is the third path:

**`battle_deck_night`'s four sprite palettes are re-solved for the cast that fights on a battle strip, and the
measured solution is these four, which is the ship's set with one entry changed:**

| slot | entries | hex | what it carries |
| --- | --- | --- | --- |
| sp0 | $00 $0F $10 | #7c7c7c #000000 #bcbcbc | the battle sheet's greys, ink and metal (same as ship sp0) |
| sp1 | $02 $0F $30 | #0000bc #000000 #fcfcfc | `navy_sailor`'s declared triple, plus the sheet's navy and white tiles |
| sp2 | $07 $17 $36 | #881400 #e45c10 #f0d0b0 | the sheet's rust and **skin** (same as ship sp2) |
| sp3 | $08 $27 $28 | #503000 #fca044 #f8b800 | the sheet's boots and orange trim (same as ship sp3) |

`data/palettes/scene_battle_deck_night.json` today holds `[0,16,15] [7,23,40] [2,18,48] [1,17,49]`; the four above are
`[0,15,16] [2,15,48] [7,23,54] [8,39,40]`.

Measured on `output/bg_battle_deck_night_frame.png`, 2026-10-24, `tools/palette_synergy.py --scene
battle_deck_night` with `game/sprites_src/chars/sailor_battle.png` and `game/sprites_src/enemies/navy_sailor.png`:

- shipped set: FAIL, 3 failing pairs, the card's exact three, all `set_member` on the battle sheet.
- the four above: **PASS, 0 failing pairs**, on both sprite files.

`sailor_battle.png` is not repainted and not requantised. The 3 colours were never the defect.

## 2. Why (a) is refused: the sheet is already carried whole, one room over

`sailor_battle.png` is 168x32, seven frames of 24x32, ten colours, and 72 inked 8x8 tiles with a worst tile of 3
opaque colours (`tools/nes_check.py check_sprite_tiles` PASS). A multi-tile figure spends more than one palette by
design: each 8x8 tile picks one of the four. Measured per tile against the twelve scene sets:

| scene | single palette carries `navy_sailor`'s $02 $0F $30 | battle sheet tile groups with no palette (of 10) |
| --- | --- | --- |
| ship | no | **0** |
| battle_corridor, battle_deck_night, battle_quay_dusk, battle_wardroom | no | 3 |
| southampton, westminster, winchester | no | 3 |
| sea | **yes** ($0F $02 $30) | 6 |
| icons | no | 9 |
| title | no | 8 |
| ui | no | 7 |

The ship set carries the sheet 10 of 10. That is the whole argument against a repaint: the sheet is legal, the deck
set is solved for something else. Repainting the only 24x32 battle sheet that any scene set already carries, to fit a
set that carries none of them, moves the defect and loses the working pairing. RULE 0 point 5 already says it in the
other direction: an image that does not survive quantisation is rejected, not patched later. The corollary is that a
sheet that does survive its set is not repainted to fit a different one.

## 3. Why (b) is refused as written: adding is evicting, and a union pass is not a palette

An NES sprite palette is three entries plus transparency. "Adding $36, $08 and $27 to the scene's 4 sprite palettes"
is three evictions from four triples that currently serve named things:

| shipped slot | entries | what it is spent on |
| --- | --- | --- |
| sp0 | $00 $10 $0F | greys; also the battle sheet's ink and metal |
| sp1 | $07 $17 $28 | Konrad's amber, `{7,23,40}`, the same sp1 in the other three battle strips and the three towns |
| sp2 | $02 $12 $30 | the sailor's and Percy's three-colour walking sheet, and ship sp1 |
| sp3 | $01 $11 $31 | Zander's light blue, `{1,17,49}`, the only palette in the twelve sets that carries it |

And `set_member` is a union test: it asks only whether a colour appears anywhere in the twelve entries. Adding the
three would turn the deck's pair half green while the figure still could not be drawn, because no single palette of
the deck carries `navy_sailor`'s own triple. That is the case `knowledge/PALETTE-GATE-DECISIONS-2026-10-22.md` calls
"legalise a sheet"; it would be legalising a figure against a rule that is not the rule.

## 4. The budget, measured, and why the deck has to choose

Minimum sprite palettes needed to carry each set of sheets, solved as an exact set cover over the 8x8 tile colour
groups (a group is carried when some triple contains it):

| requirement | groups | minimum palettes |
| --- | --- | --- |
| `sailor_battle.png` alone | 10 | **4** |
| `sailor_battle.png` + `navy_sailor.png` | 11 | **4** |
| `sailor_battle.png` + `navy_sailor.png` + `sailor_ow_v2.png` | 12 | 5 |
| the five party walking sheets | 4 | **4** |
| `navy_sailor.png` + the five party walking sheets | 5 | 5 |
| `sailor_battle.png` + `navy_sailor.png` + the five party walking sheets | 15 | more than 6 |

The PPU gives four. So the deck carries the cast that is drawn on it or the cast that walks past it, not both, and
which one is not a palette question, it is a question about the object. `battle_deck_night` is the battle strip:
`game/scripts/pp_battle_director/pp_battle_director.gml` line 774 lists it with the other three strips, line 889
says every actor there is drawn in a palette role today, and `knowledge/genre-design.md` section 7 fixes battle
sprites as their own sheets. The walking sheets are the map's cast, not the strip's. The deck carries the fight.

## 5. What the decision costs, named

Measured with `--scene battle_deck_night` on the same frame, the five party walking sheets:

- shipped set: 12 failing pairs, all `hadrian_ow_v2.png`.
- the four above: 84 failing pairs, `sailor_ow_v2` 16, `percy_ow_v2` 16, `konrad_ow_v2` 8, `zander_ow_v2` 32,
  `hadrian_ow_v2` 12.

That number is the price and it is not hidden. It is also not damage to those sheets: each one is built to a palette
that survives on the ground it actually stands on, and none of those grounds changes.

- `sailor_ow_v2.png` and `percy_ow_v2.png` are `{02,12,30}` = ship sp1, unchanged.
- `konrad_ow_v2.png` is `{07,17,28}` = sp1 of the other three battle strips and all three towns, unchanged.
- `zander_ow_v2.png` is `{01,11,31}`, the deck sp3 that this ruling spends on the enemy's black outline. Zander's
  light blue is the entry the deck costs, exactly as skin `$36` was the entry the walking sheet cost in
  `t_a44ae3db`, and it is bought back on a ground Zander is drawn on, not on a strip he is not.
- `hadrian_ow_v2.png` fails both sets and was failing before this ruling. His purple is Q2 below.

## 6. The questions left open on the record

**Q5, skin `$36`.** Skin stays on the battle sheet, and the deck set now carries it in sp2. The walking sheet keeps
its three: a 16x16 figure is four 8x8 tiles under ONE palette, so navy, white and skin cost two palettes on a
scanline, which is the defect `t_bd5cfad5` removed. A 24x32 figure is not under one palette, so the same rule does
not apply to it. The sailor has skin in battle and no skin on the map. That is the hardware's answer, not an
inconsistency to paint away.

**Q4, Zander's light blue.** A ground carries the cast drawn on it. The deck strip draws the battle cast, so its four
palettes are the battle cast's and Zander's walking palette is not among them. Zander's walking sheet keeps its
triple and stands on the grounds that carry it; the deck's answer for Zander is `zander_battle.png`, and that sheet
is Q2's problem, not this one.

**Q2, Hadrian's purple.** The purple is kept. RULE 0 point 3 reserves it, and the measured fact is that the four
violet entries $03 $13 $23 $33 appear in 0 of the 12 sets, so keeping it costs one entry somewhere. It is not bought
on the deck: the deck's four are now the enemy's ink and the battle sheet's skin, greys and browns, and taking one
back to buy a violet would put this card's defect straight back. `hadrian_ow_v2.png` is `{$00,$0F,$30}` and fits no
single palette in any of the twelve sets, so he needs a slot and a redraw whichever ground is chosen. That is its own
card, and it is not the deck.

## 7. The ruler cannot see the object, and that is why this took five rounds of draws

`tools/palette_synergy.py` line 98 sets `SPRITE_FRAME_W = 16` and line 267 turns that into `is_sprite_frame()`. Any
sheet 17 px wide or wider is a **tiled layer**: R1 body_ground, R2 same_hue_row, R3 white_blob and R6 palette_count
are all skipped, and `set_member` alone decides. Every battle figure in this project is 24x32 or 32x32, so every one
of them is measured as a layer. There is no `--frame-w` value that makes them figures, because 17 is already past the
line.

Measured consequence, on the shipped deck set, today: `navy_sailor.png` reports **PASS, 0 failing pairs**, with
`palettes that fit []` printed on each of its three frames and "tiled layer so R1b" beside it. The enemy that deck
exists to fight has no sprite palette that carries its declared triple `{$02,$0F,$30}`, and the ruler calls it clean.
The same blindness is why five rounds of draws moved the deck column by 0: the draw lane was asked to fix a palette
that could not be named by the rule being applied.

**Ruling.** A sheet is a tiled layer when the sheet says so (the wordmark, the car, a window strip), not when it is
17 px wide. A battle figure up to 32x32 is a figure: R6 asks whether ONE palette carries the figure, and a multi-tile
figure additionally asks that every 8x8 tile fits some palette of the scene. The layer branch keeps R1b for the
sheets that declare themselves layers. `knowledge/ART-BIBLE.md` RULE 0 point 2 carries the sentence.

## 8. What this ruling does not decide

- The party battle sheets. `percy_battle.png` has 60 of 73 inked tiles with no palette in any scene set,
  `zander_battle.png` 66 of 72, `konrad_battle.png` 35 of 72, `hadrian_battle.png` 40 of 72, and no cover in 6
  palettes carries all four plus an enemy. That is a project budget decision across every battle strip, far larger
  than one deck, and it gets its own card.
- The deck's four background palettes. Untouched; the background half stays 0 fails on all 8 R13 frames.
- The deck's `"gate": false`. Nothing lands blocked by this ruling; the gate stays advisory until gamedev opens it.
- One risk, named not solved: the enemy's ink is `$0F` and the deck's backdrop is `$0F`, so the figure's outer pixel
  merges into the night. If that reads badly, the backdrop moves, not the enemy's palette.

## 9. Evidence and provenance

Every number above was produced on 2026-10-24 in this repository, not quoted from a card: the per-tile colour groups
and the exact set covers from the sheets in `game/sprites_src/`, the twelve-set table from `data/scene_palettes.json`,
the two `palette_synergy.py` runs from `tools/palette_synergy.py` itself (shipped root and a scratch root carrying
only the four proposed triples), and the R13 reproduction of the 3 fails on `output/bg_battle_deck_night_frame.png`.

No external code, art, audio, dialogue or decompiled material was read, retyped or reused. Sources studied: the
repository's own palette sets, `tools/palette_synergy.py`, `tools/nes_check.py`, `tools/check_scene_palettes.py`, and
the NES sprite palette budget already written down in `knowledge/ART-BIBLE.md` section 1. Mechanism learned: a
multi-tile NES figure spends one palette per 8x8 tile, so a scene set is judged against a figure by tile fit and not
by a single-palette union. Ours differs: the check is written as an exact set cover over tile colour groups, and the
layer exemption is decided by what a sheet declares, not by its width.

## 10. Card `t_50193088`: the deck's last pair, and the row as an instrument

One pair survived card `t_cc0c5bd5` on the deck: `body_ground` on `sailor_battle.png` frame 2, body `$10` row 1
against ground `$0F` row 0, one row short of point 2's two. The same pair fires on `battle_corridor`, a set that
card never touched, so it is neither the deck's palette nor the sheet's three colours.

Two measured facts decide it.

**The ground under every battle figure is the backdrop.** On all four strips (`bg_battle_deck_night`,
`bg_battle_corridor`, `bg_battle_quay_dusk`, `bg_battle_wardroom`) rows 112 to 239 are one colour, `$0F`, and the
tool's automatic placement for a 24x32 figure is 116,192: all 768 pixels of the ground box are `$0F`. Each strip
is art in the top half and a black field where the figures stand. So `body_ground` on a battle figure reads: is
the frame's largest fill row 2 or row 3. Six of the seven sailor frames answer `$30` and pass; frame 2 answers
`$10`.

**The row is a coarse band, not a luminance.** On the 2C02 table `$10` (`#bcbcbc`, 0.503) against `$0F` (0.000)
is one row apart at **11.06:1**, and `$10` against `$30` (0.973) is two rows apart at **1.85:1**. The instrument
refuses the most readable pair a NES can draw and accepts a pair that is nearly one tone. Point 2 asks for
separation from the ground; the row is a proxy for separation, and on the low rows the proxy ranks pairs
backwards.

### The three moves the card named, each refused by measurement

(a) **Move the backdrop.** Of the 64 entries, exactly the 16 row 3 entries clear body `$10` under the two-row
rule, so a night deck would have to stand on a pale field; and because the lower half of all four strips has
`$0F` baked into the PNG, the move is four backgrounds repainted plus a scene-set entry all four strips share.
It also does not answer the card: a row 0 or row 1 backdrop, the only kind a night deck can have, leaves the
pair failing.

(b) **Ask `body_ground` per 8x8 tile**, as R6 already is. Measured on this sheet over this ground: **43 failing
tiles** (7, 9, 6, 7, 5, 7, 2 across the seven frames) against 1 whole-frame pair today, and frame 2 alone goes
from 1 to 9 of its 11 inked tiles. The per-tile reading is right for R6, because a palette is spent per 8x8 tile,
and wrong for R1: a fill that reads at 11:1 does not stop reading because it shares a tile with the outline.

(c) **Repaint frame 2's `$10` to `$30`.** It clears the pair, the frame's body becoming row 3, and immediately
uncovers the tile at sheet 40,8, which then needs `$00 $0F $30`: no deck palette carries all three, and the
sheet's uncovered tiles go 0 to 1. That is a fifth-palette fail bought to satisfy an instrument that is refusing
a pair reading at 11:1. Section 2's refusal of a repaint stands, with this measurement on top of it.

### The ruling: two instruments for one question, either one clears it

R1 `body_ground` passes a pair when EITHER of these holds, and refuses it only when both are short:

- at least 2 brightness rows apart on the 2C02 grid, which is what point 2 already said; or
- at least 3:1 WCAG contrast between the two luminances, which is the floor R1b already uses for a tiled layer.

The 3:1 floor is not new and not tuned to this card: it is the WCAG large text floor already implemented in
`tools/art/contrast_check.py`, and it arrives here the same way it arrived in R1b, from a measured case where the
row arithmetic cannot see the difference that decides whether a thing reads.

The pairs the two instruments still refuse, measured, so the amendment is not a rubber stamp: `$02` on `$0F`
1.73:1, `$08` on `$0F` 1.76:1, `$07` on `$0F` 2.15:1, `$00` on `$02` 2.91:1, and `$00` on `$11` one row apart at
1.00:1. The deck's enemy triple `$02 $0F $30` still cannot be read on a black field, which is the real defect the
row arithmetic could never name.

### Measured before and after, on every battle strip

| command | before | after |
| --- | --- | --- |
| `--scene battle_deck_night` with `sailor_battle` and `navy_sailor` | FAIL, 1 failing pair (`body_ground` @24,0) | **PASS, 0 failing pairs** |
| `--scene battle_corridor`, same two sheets | FAIL, 46 | FAIL, 45 |
| `--scene battle_quay_dusk`, same two sheets | FAIL, 46 | FAIL, 45 |
| `--scene battle_wardroom`, same two sheets | FAIL, 45 | FAIL, 44 |
| `--gate` | 6 entries, 0 gated, 6 advisory, 792 fails, `body_ground` 19 | 6 entries, 0 gated, 6 advisory, 790 fails, `body_ground` 17 |
| `--selftest` | 12 checks PASS | 13 checks PASS |
| `pytest` on `test_palette_synergy`, `test_scene_palette_set`, `test_make_characters_v2`, `test_kaggle_r7` | 48 passed | 49 passed |

Each of the four strips loses exactly one `body_ground` pair and nothing else moves. Across the gate's six
entries the amendment clears exactly 2 of the 19 `body_ground` fails (the deck's frame 2 and one pair on
`ship_dialogue`) and leaves 17 refused, so it is not a rubber stamp: the title frame keeps its 2, the ship title
pairing keeps its 8, and `battle_corridor` keeps its 7. The 45, 45 and 44 left on the other three strips are
`set_member` and `palette_count` on the same sheet: those sets do not carry its colour groups, which is the
backlog section 8 names, not this card.

### Where it landed, and why that is written down

The rule change (the constant, `pair_rules`, the selftest cases, the module docstring, the two test cases and the
ART-BIBLE sentence) is in commit `cf3d43a`, which is card `t_c498add9`'s commit. That card staged
`tools/palette_synergy.py`, `tests/test_palette_synergy.py` and `knowledge/ART-BIBLE.md` by explicit path while
this card's hunks were unstaged in those same three files, and explicit-path staging takes the whole file, so the
hunks went with it. Its message therefore says R1 is unchanged and quotes the pre-hunk counts (selftest 12, that
test file 14 passed, the deck gate entry 17 with `body_ground` 1), which the committed content contradicts: on
`cf3d43a` the selftest reports 13 checks, that test file passes 15, and the deck gate entry reads 16 with
`body_ground` 0.

This section, the DEVLOG entry and the `knowledge/PROVENANCE.md` line went in twice over. They were committed as
`4c68fec` on top of `cf3d43a`; minutes later card `t_c498add9` ran `git commit --amend` against `cf3d43a` rather
than against the new head, to rewrite its own message, which produced `4993014`, and that amend carried this
card's three documents in its tree under that card's message. `4c68fec` is therefore no longer reachable from
`master`, and `4993014`'s tree is identical to it for these three files (`git diff --stat 4993014 4c68fec` on
those paths prints nothing). Nothing is rewritten and nothing is lost: the content is on `master`, and this
paragraph is the one place that says which card wrote it and what the numbers are.

### What this does not decide

- **The ink merge.** Frame 2's outline is `$0F` and the ground is `$0F`, so its silhouette edge is the backdrop.
  Section 8 named this from the other side and it is still true and still unmeasured by any rule. It is not this
  card: no rule asks ink against ground, and one that did would refuse six of the seven frames on every strip.
- `navy_sailor`'s `$02` on `$0F` (1.73:1) stays refused in the pair table and is not caught by the frame's body,
  because its largest fill is `$30`. The enemy's dark blue is still unreadable on the strips' black field.
- The deck's `"gate": false`. Untouched by this card.
- Two historical tables carry `body_ground` counts taken under the one-instrument rule,
  `knowledge/NES-AUDIT.md` and `knowledge/PALETTE-GATE-DECISIONS-2026-10-22.md`. They are dated measurements and
  are not rewritten; this section is the re-measure.

### Evidence

Every number above was produced in this repository on 2026-10-24: the four strips' row bands and the 768 pixel
ground box from the PNGs in `output/`, the contrasts and rows from `tools/art/contrast_check.py` through
`tools/palette_synergy.py`'s own `Grid`, the 43 per-tile fails and the 0 to 1 uncovered tiles from
`tools/palette_synergy.py`'s `tile_fails()` on an in-memory copy of the sheet, and the before/after columns from
that tool itself.

No external code, art, audio, dialogue or decompiled material was read, retyped or reused. Sources studied: the
repository's own battle frames, `tools/palette_synergy.py`, `tools/art/contrast_check.py`, and `knowledge/ART-BIBLE.md`
point 2. Mechanism learned: on the NES the four luminance rows are a coarse quantisation of brightness, so two
colours one row apart can differ by more light than two colours two rows apart. Ours differs: the check keeps the
rows as one instrument and adds the contrast floor it already uses elsewhere as the other, refusing only when
both are short.

Written by gamedev, 2026-10-24.

Check for this file: section 1 names the four triples as both entries and hex; section 4 carries the six minimum
palette numbers; section 6 answers Q2, Q4 and Q5; section 7 names the two line numbers in the tool that cause the
misread; section 8 names the four battle sheets with their uncovered tile counts; section 10 carries the measured
refusals of all three options and the five-strip before/after table.

## 11. Card `t_4f18c0ac`: the deck's row, the title car's colour, and a quay with no cast

Written by gamedev, 2026-10-24 23:20 to 2026-10-25 00:40, from card `t_bf3f9fea` (AUTO-KAGGLE-ART R15) sections 5
and 9. Three questions, all palette or cast data, none a draw. The R15 report's own proposal was a proposal, not a
ruling, and one of its three is refused below.

### Q1. `battle_deck_night`'s audit row was stale. Corrected, and the drift is now a failing check.

The deck carries the fight, not the map's walking cast. Three facts, in this order:

1. Section 4 of this file: a ground carries the cast drawn on it, and the walking sheets are the map's cast.
2. The budget in section 4: `sailor_battle` + `navy_sailor` + `sailor_ow_v2` needs 5 sprite palettes and the PPU
   gives 4. The deck cannot carry the walking sailor at any price short of dropping the fight.
3. Measured tonight, read only:
   `python tools/palette_synergy.py --scene battle_deck_night --background output/bg_battle_deck_night_frame.png
   --sprite game/sprites_src/chars/sailor_battle.png --sprite game/sprites_src/enemies/navy_sailor.png`
   gives `PASS, 2 sprite file(s), 0 failing pair(s)`, with 72 inked 8x8 tiles on the battle sheet and 37 on the
   enemy, `0` uncovered by any deck palette.

So the row is `sailor_battle.png` plus `enemies/navy_sailor.png`, and the walking sailor is judged on the ship rows,
where ship sp1 `$02 $12 $30` carries his `$12`.

What changed, and why the drift cannot repeat:

- `data/palettes/scene_battle_deck_night.json` carries a `judged` list with the fight cast, and its note says the
  walking sheet is not on the row and why.
- The audit rows LEFT the hand constant (`AUDIT`, formerly line 84 of `tools/scene_palette_set.py`). Each scene file
  now holds its own `judged` rows, so the cast decision and the row that measures it are one edit in one file. The
  R15 report named the constant as the reason the two could drift; the constant is gone.
- `tools/scene_palette_set.py` gained `cast_problems()` inside `validate()`: every enforced row's sheets are measured
  against that scene's four sprite palettes through `palette_synergy.cast_problems()` (R7 on the sheet's own colours,
  R6 in both readings, marked on the problem itself with `subject="cast"` so the check never reads prose). The old
  row, put back, now fails validate with
  `battle_deck_night: the audit row on output/bg_battle_deck_night_frame.png names
  game/sprites_src/chars/sailor_ow_v2.png, and the scene's 4 sprite palettes cannot carry it (16 problem(s); first:
  sprite colour #0058f8 ($12) is not in any of the scene's 4 sprite palettes)`.
  That is the same 16 the draw lane measured on 64 of 64 frames, now raised by the tools instead of by a round of
  GPU draws.
- Two rows are exempt because the cast they name cannot fit any set in the project, each with the reason in the
  scene file and the exact list held in `tests/test_scene_palette_set.py`: the corridor's party battle sheets
  (section 8 here) and the `sprites_v2` contact sheet, which is a diagnostic and not a cast.

The deck's pair column is measurable clean at the 13:33 solve, which is what the lane asked. Its floor of 16 on this
subject is 0 as of tonight.

### Q2. The title car: repaint, and the colour is the `$20` its own palette already carries. Neither branch offered works as stated.

Measured on the shipped sheet, read only (the recoloured sheets were written to a scratch folder, never into the
repo):

- `game/sprites_src/title/spr_title_car.png` is 3 frames of 64x32, 1054 drawn pixels a frame: `$0B` 52.8 percent,
  `$0C` 43.7, `$20` 3.5. Body = the largest fill = `$0B`.
- The grounds under the car at its own placement (`--at 76,186` on `output/nes_title_frame.png`): `$08 $09 $0A $0B
  $0C $0F $20`. On `output/car_road_ground.png`, the composed road that carries the road's `$20` marking: `$0B
  $0C $0F $20`.
- Contrast of the shipped colours, from the 2C02 table the tool uses: `$0B` reads 1.00:1 to 2.68:1 on those
  grounds and `$0C` reads 1.00:1 to 2.68:1, so the car costs 18 `overlay_contrast` failures at its placement and 9
  on the road ground.

Why neither branch works as written:

- A lighter ink cannot exist. The tool's ink is the frame's DARKEST colour by definition (`frame_report` takes
  `ink = grid.entry(outline_rgb)` from the darkest entry), so any colour a repaint calls a light ink is read as a
  body, never as an ink, and the layer keeps failing on its dark body.
- A uniform dark ground does not save a dark body. `$0B` against black tops out at 2.40:1 and against itself at
  1.00:1. There is no dark ground on which a dark body clears 3.0:1.

The instrument asks body OR ink. A two-tone layer passes because its ink covers the light grounds and its body covers
the dark ones; both of the car's colours are dark, so it has no second reading.

**Ruling.** Repaint the car so its LARGEST FILL is `$20`, the near-white its own sprite palette sp3 (`$0C $0B $20`)
already holds. `$0C` stays the darkest entry (glass, tyres, shut lines, outline) and `$0B` moves to the shadow side
of the body, so the racing green stays on the car as its shadow. No scene palette changes and no ground changes: the
road's `$20` marking does NOT have to move, because on a light ground the `$0C` ink is what clears the floor
(10.55:1).

Measured on recoloured copies, largest fill `$0B` to `$20`, every other pixel byte identical:

| ground | placement | shipped | body `$20` | body `$10` | body `$28` |
|---|---|---|---|---|---|
| `output/nes_title_frame.png` | 76,186 | 18 overlay fails | **0** | 3 | 0 |
| `output/car_road_ground.png` | 0,0 | 9 overlay fails | **0** | 0 | 0 |

`$10` is refused with its number: a light grey body reads exactly 3.00:1 on `$09` and is still under the floor
(2.998, printed as 3.00), so it would come back as a red round. `$28` gold also clears, but `$28` lives in title sp0
(the wordmark's palette), so it moves the car into another palette for no gain over `$20`.

The floor of 16 is this car and nothing else on the title subject. When the repaint lands, the title subject's
`overlay_contrast` count is 0 and what is left on that subject is the composite frame's own background, which is a
different question and already reported under `palette_count`.

The repaint is one generator, `tools/art/title_car_v2.py`: it draws in seven roles and ends with
`scene_palette.enforce_sprites` and `title_bands.paint_sheet`, which is what leaves the shipped sheet on bg3's three
entries. The card that executes this must make the body role a light entry so the band pass lands it on `$20`, keep
nothing darker than `$0C` in the drawing (so the tool's ink reading stays `$0C`), and prove it with the two
measurements above plus the title capture tests.

### Q3. `battle_quay_dusk` has no cast because nothing in play draws it. The lane stops drawing it.

Measured tonight:

- No row of `data/encounters/all.json` carries a `bg_battle` or a `background` key, so no fight names the strip.
- `pp_battle_bg_for_room` (`game/scripts/pp_battle_director/pp_battle_director.gml:844`) maps `lower_deck`,
  `ship_cabin` and `deck_day` only. The quay map `southampton_town_quay` carries `room_palette` `quay_night`, which
  is not in that switch, so a fight on the quay falls back to the corridor strip (line 884).
- The slice's two fights are both on the ship: `deck_hound` in the hold and `tutorial_sailors` on the deck watch.

So the strip is unreachable. Eight frames a round on it cannot be judged and cannot ship, which is the measurement
with no subject the lane suspected.

**Ruling.** The draw lane stops drawing `battle_quay_dusk` until a pier fight exists. It is not a "wait for a cast"
case: a cast authored for a strip nothing draws is speculative data, which is the thing this project keeps paying
for.

When a pier fight is authorised, the card that authorises it lands three things together, and the first two are
already measured so it does not re-derive them:

1. The room mapping `quay_night` to `quay_dusk`.
2. The cast, which is the Navy pair: `enemies/navy_sailor.png` plus `enemies/petty_officer.png`. Both need
   `$02 $0F $30`; the quay's sp2 is `$02 $12 $30` today, so that card moves `$12` to `$0F`, exactly the move the
   deck made on 2026-10-24, and one palette then carries both sheets (measured tonight, the two sheets share the
   same per-tile need: 57 cast problems between them against today's quay set, every one a `$02 $0F $30` tile).
3. The `judged` row in the same edit as the palette, which is now the only way this file lets a row exist.

The ruling is also written into `data/palettes/scene_battle_quay_dusk.json`'s notes, so the next card reads it there.

### Where it landed

`data/palettes/scene_title.json`, `scene_battle_deck_night.json`, `scene_ship.json`, `scene_battle_corridor.json` and
`scene_battle_quay_dusk.json` (judged rows and the quay note), `data/scene_palettes.json` (rebuilt),
`tools/scene_palette_set.py` (judged loading, cast check), `tools/palette_synergy.py` (`subject` marks and
`cast_problems`), `tests/test_scene_palette_set.py` (eight new tests).

Check for this section: `python tools/scene_palette_set.py validate` gives PASS, 12 scenes; the old deck row put back
gives 1 problem naming `sailor_ow_v2.png` and `$12`; `python -m pytest tests/test_scene_palette_set.py
tests/test_palette_synergy.py -q` gives 33 passed.
