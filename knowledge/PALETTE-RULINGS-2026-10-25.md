# PALETTE RULINGS 2026-10-25

gamedev rulings for card `t_474cde50` (the exhaust puff's classification, and the composer ordering that
decides what its ground is). Every number below was measured in this repository on 2026-10-25, by the
tools named beside it, not quoted from a card.

## 1. Q1: the exhaust puff is a TILED LAYER, and the sidecar is where it says so

`game/sprites_src/title/spr_title_exhaust.png` declares `"layer": true`. The declaration is written by the
generator that owns the name (`tools/art/make_title_car.py`, `LAYER_SHEETS`), so a regeneration carries it
and a hand edit cannot be lost.

**Why it is a layer and not a figure, measured.**

The question RULE 0 point 2 asks of a figure is "does the body separate from the ground it stands on". That
question presumes one ground. The puff does not have one. Sweeping the title's own layer table
(`output/title_world_manifest.json`) over 1200 scroll steps and reading the 16x16 window the game draws the
puff in (`PP_TITLE_CAR_X` 76, `PP_TITLE_CAR_Y` 193 plus 14, so y 207 to 222), the window holds exactly four
entries, and all four are present at once, in every frame of the sweep:

| ground | share of the window | luma | body `$20` | ink `$0C` | R1b |
| --- | --- | --- | --- | --- | --- |
| `$0F` black (ten duplicate codes decode to it) | 72.7 percent (202245 of 278136 samples) | 0.0000 | 19.77:1 | 1.87:1 | PASS on the body |
| `$0B` green | 15.4 percent (42817) | 0.0698 | 8.25:1 | 1.28:1 | PASS on the body |
| `$0C` teal | 6.0 percent (16618) | 0.0437 | 10.55:1 | 1.00:1 | PASS on the body |
| `$20` white | 5.9 percent (16456) | 0.9387 | 1.00:1 | 10.55:1 | PASS on the ink |

The composer's own placement (76,200, `CAR_Y` 186 plus 14) gives the same four entries with a different mix,
`$0F` 57.4 percent, `$0B` 27.8, `$20` 10.3, `$0C` 4.5. Nothing in the ruling depends on which of the two
placements is used; the four entries are the road strip's, at either.

As a figure the sheet cannot pass, and not for a reason any redraw can fix: a body clearing 3:1 on `$0B`
(luma 0.0698) needs luminance 0.31 or more, and one clearing 3:1 on `$20` (luma 0.9387) needs 0.30 or less.
The window between them is empty in the 2C02 table, so no entry in any title sprite palette satisfies both,
and the row's measured floor of 4 failing pairs (one per frame, body on the road's white marking) is the
floor for any 16x16 drawing on this ground. The row gap cannot rescue it either: a ground that spans rows 0
and 2 refuses every entry that would have to be two rows from both ends of it.

As a layer it passes on all four frames, 0 failing pairs, because R1b asks that the ink OR the body be
tellable from what is under it, and the two-tone drawing does exactly that: the ink carries the `$20`
marking at 10.55:1 and the body carries the three dark grounds at 8.25:1 or better.

Measured, `python tools/palette_synergy.py --scene title --background output/exhaust_road_ground.png
--sprite game/sprites_src/title/spr_title_exhaust.png --frame-w 16 --frame-h 16 --at 0,0`: `PASS, 1 sprite
file(s), 0 failing pair(s)`, each frame printing "tiled layer so R1b: ink $0C". `python tools/nes_check.py
game/sprites_src/title/spr_title_exhaust.png --type sprite`: `64x16 16 tiles 2 colours PASS`.

## 2. The test this ruling writes down, so the flag cannot spread to figures

The previous ruling (`PALETTE-RULINGS-2026-10-24.md` section 7) settled that a sheet is a layer when the
sheet declares itself one. It did not say what qualifies a sheet to declare it, and that is the question
this row turned on. Two questions, both measured, neither of them about width or about 16 pixels:

1. **Does the sheet have one ground?** Sweep the scene's own layer table over a scroll and read the window
   the sprite is drawn in. A figure stands on one surface and its instrument can be asked of that surface.
   A sheet whose window crosses four entries, two luminance rows apart at the ends, is being asked a
   question that has no answer.
2. **Is it an object that stands somewhere, or an effect or scenery over a strip?** Exhaust gas, a sky-band
   cloud, a wordmark, a car seen as a whole are not standing on anything; a wheel in an arch, a bust behind
   glass, a walking sailor are.

Applied to the title's four undeclared 16x16 sheets, so nobody has to guess later:

| sheet | one ground? | object or effect | verdict |
| --- | --- | --- | --- |
| `spr_title_exhaust` | no, four entries across rows 0 to 2 | effect over the road | **layer** (this ruling) |
| `spr_title_wheel` | yes, the car's arch, one surface | object (and the v2 car bakes its wheels, so the title does not draw it) | figure |
| `spr_title_konrad` | yes, the car interior behind the glass | character | figure |
| `spr_title_zander` | yes, the same interior | character | figure |

The point of the table is the cost of being wrong: the flag is not a way around the row gap and the blob
test. Both are still asked of every figure at 16x16 and under, and a figure that cannot pass them is a
redraw or a palette, never a declaration.

## 3. Q2: the composer's ordering is intended, and the black under the puff is the tarmac

The ordering that makes 73.8 percent of the puff's ground `$0F` is not an accident of the composer. Both
sides draw the same order, and each was read before the answer was given:

- `game/scripts/pp_title/pp_title.gml`, the draw event: `pp_title_draw_layers` (the seven night layers,
  `title_L7_fg` among them) at line 488, then the sign, the cone, the car at 491, the cloud, the logo.
  Inside `pp_title_draw_car` the exhaust is drawn before the car body, so the finish covers the near part of
  the puff.
- `tools/art/compose_title_preview.py`: the layer loop, then the sign, then the cone, then the exhaust, then
  the wheels, then the car body.

So the order is the same on both sides and the puff is behind the car on purpose.

The black is the scene's own dark, not a missing layer: the title's road band is painted with
`data/palettes/scene_title.json` bg3 (`$0C $0B $20`) plus the shared backdrop `$0F`, and the foreground and
road strips spend that backdrop entry on the tarmac. The sweep in section 1 is the evidence: the four
entries under the puff are exactly the four the road strip carries, in the shares a scrolling tarmac and its
`$20` marking produce.

**No composer change follows from this row.** One drift was found while measuring and is carded separately:
the composer's `CAR_Y` is 186 where the game uses `PP_TITLE_CAR_Y` 193, and the composer still pastes the
separate wheel sprite that the v2 car bakes in.

## 4. The band consequence: the body that ships is `$20`, not the redraw's `$10`

The redraw that card `t_9774ff51` produced drew its body in `$10` light grey. That entry cannot ship: the
puff sits in screen bands 12 and 13, `data/palettes/scene_title.json` `band_sprites` gives `spr_title_exhaust`
bg3, and bg3 is `$0C $0B $20`. `tools/art/title_bands.py` maps every pixel of a band-painted sheet into its
band palette, so a `$10` body becomes `$20` on the way to the tree.

Measured with that same `map_image` call: 118 pixels move, and the landed sheet is `#f8f8f8` 118 px plus
`#004058` 70 px. A generator that drew `$10` and let the pass recolour it would be drawing something the
tree never ships, which is the failure RULE 0 point 5 names, so:

- the four cells now live in `tools/art/make_title_exhaust_v2.py` and are rasterised in the shipping pair;
- `tools/art/make_title_car.py` asks that file for them (`build_exhaust_frames`) instead of drawing a second
  puff, and its `parts` entry is no longer fitted into a frame, because the cells are already 16x16;
- `output/redraws/spr_title_exhaust.png` is drawn in the same pair, so the preview and the tree agree.

R6 still holds: both entries are in title sp2 (`$0C $10 $20`) and sp3 (`$0C $0B $20`), palette_synergy
prints `palettes that fit [2, 3]` on every frame, and `nes_check` PASS with a worst 8x8 tile of 2 colours.

What the redraw fixed stays fixed. The shipped sheet before this ruling flipped its body from `$0C` in frame
0, where it was the ground's own colour at 1.00:1 on the `$0C` ground, to `$20` in frames 1 to 3. The sheet
now has a 1 px `$0C` outline on every frame and a body that clears the dark grounds, and it grows 5x4, 8x6,
10x8, 12x10 across the four frames, which is craft rule SP-046.

## 5. What landed on this card

- `game/sprites_src/title/spr_title_exhaust.png` and its four fade twins rewritten by the owning generator,
  with `"layer": true` in the base sidecar and inherited by each twin (`tools/pp_intro_art.py` copies the
  base sidecar, so the twins cannot drift out of the declaration).
- `tools/art/make_title_car.py`: `LAYER_SHEETS` and `CHIP_DRAWN_SHEETS` replace the one-name cloud special
  case; `build_exhaust` is gone, `build_exhaust_frames` calls the shared cells.
- `tools/art/make_title_exhaust_v2.py`: `build_frames(body, ink)` is the shared drawing, `main` writes the
  shipping pair, and the docstring carries the numbers behind both changes.
- `data/sprite_redraw_queue.json`: the row is `done`, with the landed numbers and this ruling named.
- `knowledge/ART-BIBLE.md` RULE 0 point 2 carries the two-question test in one sentence and points here.
- Checks: `nes_check` PASS; `palette_synergy` PASS 0 failing pairs, with and without `--frame-w`/`--frame-h`
  (the sidecar geometry alone is enough now); `python -m pytest tests/test_intro.py tests/test_title_bands.py
  tests/test_make_font_row.py tests/test_palette_synergy.py tests/test_nes_check.py -q` 71 passed;
  `tests/test_title_art_v2.py tests/test_scene_palettes.py tests/test_scene_palette_set.py
  tests/test_nes_composite_check.py tests/test_sprite_pipe.py tests/test_sync_art.py
  tests/test_make_title_ui.py tests/test_make_title_world.py` 120 passed.

## 6. What this ruling does not decide

- **The fade twins.** They are derived art and they do not hold R1b against the unfaded ground, measured as
  layers: fade1 2 failing pairs, fade2 8, fade3 12, fade4 12, the worst being body `$0F` and ink `$0F` on
  the `$0F` tarmac at 1.00:1. That is not a defect this row can fix and it predates it (on the old base the
  same four measured 5, 9, 12 and 12): in the game a fade twin is drawn while the whole frame, ground
  included, fades under it, so the ground file they are measured against is not the ground they are drawn
  on. Nothing in the audit measures them today. What would settle it is either a faded ground per step or an
  exclude list in `data/scene_palettes.json` the way the contact sheet has one, and it is a separate card.
- **Q3 on the car row**, bg3 and sp3 carrying the same three entries, is untouched. It is still the reason
  the exhaust's body is `$20` and not `$10`.
- **Konrad and Zander** still want entries no title palette carries (`$36` skin with `$10` and `$07` tweed,
  `$21` and `$31`), so those two rows still need a palette before they can be drawn to their own brief.
- **The wheel row** stays a figure and stays drawn by this generator even though the v2 car bakes its
  wheels, so the title does not draw it. Whether the row retires is an art lane question, not this one.
