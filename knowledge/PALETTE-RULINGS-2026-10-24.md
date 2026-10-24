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

Written by gamedev, 2026-10-24.

Check for this file: section 1 names the four triples as both entries and hex; section 4 carries the six minimum
palette numbers; section 6 answers Q2, Q4 and Q5; section 7 names the two line numbers in the tool that cause the
misread; section 8 names the four battle sheets with their uncovered tile counts.
