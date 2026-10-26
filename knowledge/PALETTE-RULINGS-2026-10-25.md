# PALETTE RULINGS 2026-10-25

gamedev rulings for card `t_474cde50` (the exhaust puff's classification, and the composer ordering that
decides what its ground is), and for card `t_8c27208b` (the party battle sheet budget, and the far side's
audit universe; sections 7 and 8). Every number below was measured in this repository on 2026-10-25, by the
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
separate wheel sprite that the v2 car bakes in. Fixed the same day by card t_2a34652e: the composer now
reads the placements out of the game's own macros and the layer table out of `data/title.json` (the file
`pp_title_data` loads), pastes no wheel, bust or bubble, and `tests/test_title_preview_placements.py` pins
all three. The drift did not change this ruling: the sweep section 1 ran at the game's placement (76,207)
stands, and the same four entries hold at the composer's old (76,200).

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

---

# Card `t_8c27208b`: the party battle sheet budget, and the far side's audit universe

Both questions were raised by AUTO-PINE-CHECKS run 10 (card `t_8b85f7e8`, page `knowledge/PALETTE-PASS-LIST.md`
sections 2, 7 and 9). Every number below was measured in this repository on 2026-10-25, by the script named
beside it, in this card's workspace. Nothing was quoted from a card, and no picture was taken on faith.

## 7. Q1: the party battle sheets get ONE hero triple each, and a fifth sprite palette does not exist

**Answer: it is the repaint, and the thing being repainted is the four RESERVED HERO PALETTES, not "the three
colours the sets already carry".**

- **(a) a fifth sprite palette per battle scene is refused.** The PPU picks a sprite palette with two attribute
  bits, so a frame has four sprite palettes of three entries plus transparency. That is the arithmetic
  `knowledge/ART-BIBLE.md` section 1.2 already prints (4 sprite palettes, 12 opaque sprite colours per frame),
  and RULE 0 point 1 fixes it as a project rule as well ("4 background palettes (3 colours each) and 4 sprite
  palettes (3 colours each)"). A fifth palette is not a budget that can be raised, so any drawing that needs
  one is a drawing that cannot be drawn.
- **(b) "a repaint of the four battle sheets to the three colours the sets carry" is refused as written.** No
  scene set carries them: the four sheets as drawn use 19 colours in 39 distinct per-tile colour sets and need
  **26** three-entry palettes, against a budget of 4. And "the three colours the sets carry" is four different
  triples depending on the scene, which is what the sheets already fail on.
- **(c) "exempt advisory through the store submission" is refused as the destination.** The row stays exempt
  only until the art lands. What changes now is that the exemption stops saying no card owns the decision: it
  names this ruling and the budget below.

### 7.1 Why a fifth palette looked available, and the defect that made this read as an open choice

The project's own data model already carries **eight** sprite palettes per scene. `tools/scene_palette_set.py`
writes, in `data/scene_palettes.json` `notes`, that "heroes true means the scene also carries the 4 reserved
hero palettes", and its `allowed()` unions the scene's four with the four hero triples; `tools/palette_synergy.py:349`
and `:441` then print the message

    8x8 tile at 8,0 needs $0F $17 $36, which no single sprite palette of the scene carries,
    so the frame needs a fifth sprite palette

so the tool names a fifth sprite palette as the remedy and the data model acts as if one exists. Neither is
true on the chip. **On a battle strip the four reserved hero palettes ARE the strip's four sprite palettes.**
The consequence is named here and is not this card's work: the deck row that passes today (card `t_cc0c5bd5`)
spends all four deck triples on `sailor_battle.png` and `navy_sailor.png`, so it has no slot left for the party
that the same room draws at x=224. That PASS is a PASS on the cast the row names, not on the room.

### 7.2 The budget, written: four triples, and they are already in the file

`data/scene_palettes.json` `hero_palettes` (RULE 0 point 3, `"fixed": true`):

| hero | triple | roles as the file writes them |
| --- | --- | --- |
| Percy | `$0F $12 $28` | outline black, blue body, gold accent |
| Hadrian | `$0F $03 $23` | outline black, dark violet, light violet |
| Zander | `$0F $21 $31` | outline black, light blue body, pale blue accent |
| Konrad | `$0F $00 $27` | outline black, grey, amber |

Nine entries of the twelve a frame allows, and four triples, which is exactly a battle strip's sprite budget.
So the budget does not have to be invented. It has to be spent.

### 7.3 The price of drawing each sheet to its own triple, measured

Per 8x8 tile colour sets, from `cover_count.py` (exact set cover over every tile's opaque colour set, candidate
palettes every set and every union of two sets that fits in three entries); recolour cost from `hero_price.py`
(each drawn colour snapped to the nearest entry of the hero triple, weighted RGB distance times pixel count):

| sheet | size | inked tiles | colours as drawn | distinct tile sets | min triples as drawn | after the repaint | pixels that change colour |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `percy_battle.png` | 168x32 | 73 | 10 | 17 | **12** | 3 colours, 1 triple | 1875 of 2816, **67%** |
| `hadrian_battle.png` | 168x32 | 72 | 6 | 9 | **4** | 3 colours, 1 triple | 434 of 2410, **18%** |
| `konrad_battle.png` | 168x32 | 72 | 7 | 11 | **7** | 3 colours, 1 triple | 673 of 2458, **27%** |
| `zander_battle.png` | 168x32 | 72 | 8 | 10 | **6** | 3 colours, 1 triple | 818 of 2411, **34%** |
| the four together | | 289 | 19 | 39 | **26** | 4 triples | |

Percy is the expensive one because his sheet is a 10 colour drawing: navy, grey steel, skin, rust, orange, white
and three more. Snapping it to three entries rewrites two thirds of his pixels, so his sheet is a redraw and not
a recolour, and the art card has to be priced that way. Hadrian's is nearly a recolour already (18 percent).

### 7.4 The two constraints a redraw has to satisfy, both measured

1. **The body role goes to the LIGHT entry of the triple.** The party block is drawn at `x=224, y=32` in four
   24x32 slots (`data/ui_layouts.json`), and the ground under that block, read from the four battle frames at
   x 224 to 247, y 32 to 159 (`hero_price.py`), is:

   | strip | top three colours under the party block |
   | --- | --- |
   | `bg_battle_corridor_frame.png` | `$00` 1161 px, `$0F` 1152 px, `$02` 573 px |
   | `bg_battle_deck_night_frame.png` | `$0F` 1152 px, `$00` 749 px, `$01` 624 px |
   | `bg_battle_quay_dusk_frame.png` | `$0F` 1152 px, `$01` 917 px, `$00` 558 px |
   | `bg_battle_wardroom_frame.png` | `$0F` 1152 px, `$17` 789 px, `$08` 624 px |

   With the dark entry as the body, the figure fails on all four: Hadrian's `$03` reads 2.28:1 at 0 rows from
   `$0F`, Konrad's `$00` IS the corridor block's floor colour (same colour, no edge), and Percy's `$12` is
   1.34:1 from `$00`. With the light entry as the body the same four read on `$0F`: Percy `$12` 3.75:1, Hadrian
   `$23` 6.38:1, Konrad `$27` 10.25:1, Zander `$21` 9.79:1 (`final_numbers.py`). So the body role per hero is
   `$12`, `$23`, `$27`, `$21`.
2. **The party block's floor is `$0F` on every battle strip.** The other three strips are already black there,
   and on `$0F` all four bodies clear RULE 0 point 2 on the contrast instrument. The corridor block is the one
   that has to move: 1161 of its pixels are `$00` today, which is the one floor on which Percy and Zander fail.
   Zander's `$21` also fails the wardroom's `$08` at 1.68:1, so that block's `$08`/`$17` under the party goes
   with it.
3. **Named cost, not solved:** the outline is `$0F` in all four triples and the floor is now `$0F`, so a
   hero's outer pixel merges into the floor. This is the exact risk section 8 of the deck ruling already wrote
   down for the enemy, and it is the Castlevania fact in ART-BIBLE section 2.4 read the other way round (Simon
   reads because his palette carries no black and the enemies' do). Nothing in RULE 0 fails, because a figure is
   judged on its body and all four bodies clear. If it reads badly, the escape is one line in
   `hero_palettes`: give each hero his own dark entry instead of `$0F` (Percy `$02`, Hadrian `$03`, Konrad
   `$00`, Zander `$11`), which changes no art, only the role.

### 7.5 The enemies: never a fifth slot

Measured on the seven enemy sheets against the four hero triples (`cast_budget.py`): `navy_sailor.png` has 10 of
37 tiles legal as drawn, `petty_officer.png` 7 of 32, `deck_rat.png` 7 of 42, `bilge_slime.png` **0 of 36**,
`gull.png` 8 of 41, `rogue_wave.png` 3 of 48, `rope_knot.png` 3 of 42. Borrowing a hero slot therefore means
recolouring 40 to 81 percent of each enemy's pixels, so an enemy either wears a hero's palette or it keeps its
own colours.

The ruling is the one the bible already studied: on a battle strip that draws all four heroes, the enemy is
drawn with the BACKGROUND palettes, which is what `knowledge/ART-BIBLE.md` section 1.1 records as the NES
convention ("it is why NES battle screens draw monsters as background art and keep sprites for the small things
that move") and what section 2.3 shows Final Fantasy I doing with a side view and a party on the right edge.
Where a strip draws fewer than four heroes, the enemy borrows the slot that is going spare, and its sheet is
quantised into that triple. The enemy keeps its own three colours either way, and the party keeps its identity.

### 7.6 So, before the submission

The repaint is the answer, and it is on the submission path, because the pitch is hardware discipline: the
write-up in `knowledge/SUBMISSION-KIT-2026-10-24.md` section 1.1 is headed "AI that obeys hardware limits", and
four party sheets that need 26 sprite palettes are the one measured place in the art where the project does not
obey its own headline. It does not block the 4 November build: 0 of 12 scenes carry `"gate": true` and the
store build reads PNGs, so nothing refuses to build while the sheets are red. The row stays exempt for the days
between this ruling and the art landing, and the exemption now names the card and the budget.

## 8. Q2: the release gate is Windows, the far side is advisory, and nothing is added to OUTPUT_KEEP

**Answer: the second one. The release gate runs on Windows and the Pine audit is advisory by design. Do not
grow `OUTPUT_KEEP` to the previews or to the contact sheet.**

**What the zip actually does.** `<workspace>\Shared\projects\arananet\pine\pine_offload.py` lines 77
to 148 ship `output/` tracked files plus `OUTPUT_KEEP` (three prefixes, `output/drive/`, `output/drive_frames/`
and `output/bg_`, plus 17 named files). The rule behind that list is written in the comment above it and it is
the right rule: **ship what a test reads**. Measured on this tree (`zipgap10.py` in the parent card's workspace):
universe 184 assets 130 output 54, keep set 31, and 31 output files are not carried, among them the two gated
frames and `output/sprites_v2_sheet.png`. Pine therefore reads 153 files and 13 failing where this machine reads
184 and 34.

**Why the list must not grow.**

1. **No test reads a preview.** The only readers of `output/*preview*.png` in the tree are
   `tools/nes_audit_all.py` `discover()` (which defines them as audit subjects) and prose in
   `data/sprite_redraw_queue.json`. A preview is a by-product of a GameMaker capture. Adding one to
   `OUTPUT_KEEP` ships a file nothing needs against a 40 MB upload ceiling that has already refused an upload
   twice (the comment at `pine_offload.py:77` to `:86` is that measurement).
2. **The far side cannot make them, so carrying them turns "not measured" into a stale pass.** No preview can be
   produced on the far side, because a preview is a capture of the running game. Carrying this machine's bytes
   there would let the far side measure bytes that are not that machine's art and print a verdict on them. That
   is the same class of false green card `t_19b41ab7` closed on the tracked ground rows, one directory over.
3. **The two gated frames are real screens, and their failure is real.** `output/gameover_preview.png` is
   256x240 and holds four colours that are on no 2C02 entry at all (`#0b0b0f`, `#1c1c24`, `#4a4a58`, `#c8c8d4`).
   `gameover` is a shipping screen: `data/slice.json` carries a scene with that id and
   `game/scripts/pp_battle_director/pp_battle_director.gml` runs `gameover_cursor` and `gameover_choice`.
   `output/drive_gantry_preview.png` is 256x240 and 2,355 bytes with 7 colours, also off the 2C02 table, so the
   page's "2 px" reading was of a frame that is nearly one colour. Both are defects of screens the game draws,
   and both are fixed on the machine that draws them, not carried to a machine that cannot.

**What does change, because the current behaviour is the defect.**

- **The absent universe is printed, not silently dropped.** `nes_audit_all` printing `FAIL 153 file(s)` while
  the same rule on the same tree finds 184 is a measurement that hides its own scope, and a reader cannot tell
  a clean 153 from a narrowed one. A far side run has to say how many output by-products the zip did not carry
  and name them, so "advisory" is a stated number and not a quieter universe.
- **`output/sprites_v2_sheet.png` is a by-product inside an audit entry.** It is gitignored, so no clean
  checkout reproduces it, and two generators write different content under the one name
  (`tools/art/make_characters_v2.py` draws the larger roster and measures 11 records here,
  `tools/art/make_title_rows_v2.py` 3 records on the far side). An audit entry is only worth its reproducibility,
  so the entry declares itself a by-product and the tool reports it **NOT MEASURED** with a printed line when the
  file is absent, instead of refusing the whole run. Three Pine jobs refused on exactly this
  (`v10aR-0`, `v10aU-0`, `v10aV-0`), which cost more than the sheet is worth.
- **The gate stays where the art is made.** The store submission reads the GameMaker build and the capture set,
  not the previews. So the release gate is the Windows run, and the Pine run is the second opinion it has always
  been.

**Nothing was added to `pine_offload.py` by this card.** It lives in the `arananet` tree, its rule is written in
its own comment, and this ruling agrees with it: the fix is on the audit side, not the upload side.

## 9. What landed on card `t_8c27208b`, and what it does not decide

**Landed.**

- This ruling.
- `data/palettes/scene_battle_corridor.json`: the party row's `exempt` note no longer says no card owns the
  decision. It names this ruling, the four triples and the measured price, and it keeps the row measuring while
  the art is red. `data/scene_palettes.json` is rebuilt from it with
  `python tools\scene_palette_set.py build --write` (the generator reproduces the shipped file byte for byte
  before the edit, checked with `diff --strip-trailing-cr`, so nothing else in it moves).
- Two cards, because both answers need work this card does not do: the repaint of the four party battle sheets
  to the four reserved triples, and the palette arithmetic on the tool side (the "fifth sprite palette" message,
  the eight-palette union in `allowed()`, the by-product flag on the contact sheet entry, and the far side
  printing its absent universe).

**Checks run on this tree, 2026-10-25.** `python tools\palette_synergy.py --gate`: 6 entries, 0 gated, 4
advisory, six pair totals 163, 11, 0, 0, 242, 135, 551 problems, `output/palette_synergy.json` written, exit 0
(`gate_report.py` reads the same numbers back out of that file). The measurement scripts are in this card's
workspace: `cover_count.py`, `hero_price.py`, `cast_budget.py`, `solve2.py`, `final_numbers.py`.

**Does not decide.**

- **The deck row's cast.** Section 7.1 says the deck PASS is a PASS on the cast that row names, and that the
  party has no slot there. Recasting that row means re-solving four triples against four heroes plus the enemy,
  and it re-opens a row another card just closed. It gets its own card when the party sheets land.
- **The corridor and wardroom party-block floor.** The floor change in 7.4 point 2 is a background change on
  two strips, owned by the art lane that made those frames (`tools/art/make_battle_bg.py`, card `t_1c5a8599`,
  and card `t_19b41ab7` is still open on the same files). Named, priced, not drawn here.
- **The contact sheet's owner.** Run 10's Q3 (`make_characters_v2.py` against `make_title_rows_v2.py`) is still
  open. This ruling only takes the sheet out of the shared gate path; it does not name the tool that owns the
  name.
- **Pair 5 and the title frame's 210.** Run 10's Q4 and Q5 are untouched by this card.
- **The store screenshot set.** Which captures the submission ships is the submission kit's question, and the
  kit is not this card.

---

# Card `t_0949bd4e`: the corridor and deck rows' cast, now that the party sheets are one triple each

Written by gamedev, 2026-10-25, answering the card that section 9 above reserved. Every number below was measured
in this repository on 2026-10-25 by the tools named beside it. The card's own before numbers were re-measured
first and reproduce exactly (corridor 191 fails, 73 / 86 / 32 cast problems on percy, hadrian and zander_ow_v2;
deck 0 fails), so the three answers start from the same state the card described.

The question is a cast question and it is answered with a cast, not with arithmetic: which sheets a strip's four
sprite palettes are spent on. The palette arithmetic itself is unchanged by this card.

## 10. Q1: the corridor row draws the party's four battle sheets and nothing else. `zander_ow_v2` comes off.

**Answer: the second branch. The row names `percy_battle.png`, `hadrian_battle.png`, `zander_battle.png` and
`konrad_battle.png`, and the walking sheet leaves the row.**

Three measured facts, in the order they decide it.

1. **Every battle screen draws four party sprites and no walking one.** `data/ui_layouts.json` holds one battle
   screen layout, `"name": "battle"`, and its `sprites` list is four 24x32 slots at x=224, y=32, 64, 96 and 128
   (`"role": "party"`) plus the 32x32 enemy slots at 24,64 and 96,88. There is no per strip variant, so the
   corridor strip is that screen: four 24x32 party figures on the right edge. `zander_ow_v2.png` is a 16x16
   walking sheet with 8 frames, the overworld cast, and the battle screen has no slot its geometry fits.
2. **The four hero triples cannot carry it, and that is a measurement rather than a preference.** Under the
   `party_cast` reading (the hero four as the scene's sprite palettes, which is what
   `scene_palette_set.allowed_sprite_sets()` already returns and what card `t_6e8ca42f` will make
   `palette_synergy` read) the row as shipped fails 24 pairs and every one of them is `zander_ow_v2.png`:
   8 `palette_count` and 16 `set_member`. 0 of its 32 inked 8x8 tiles fits any hero triple. The sheet is
   `{01, 11, 31}`, the deck's old sp3 (ruling section 5 of the 24 October file), and no hero triple holds those
   three entries.
3. **Removing it costs nothing that was working.** The corridor row was the only judged row in the tree that
   named `zander_ow_v2.png`, and it named it on a battle ground, which is not the ground the sheet is drawn on.
   Measured under the hero four, the party's four battle sheets on that same row and that same ground fail 0
   pairs and leave 0 of their 289 inked tiles uncovered.

## 11. Q2: yes, the corridor scene's sprite half is the four hero triples. Only the row and its note change.

**Answer: yes, and the derived file already says so.** `data/scene_palettes.json` carries `party_cast: true` on
all four battle strips (`tools/scene_palette_set.py` `PARTY_CAST_SCENES`), `allowed_sprite_sets()` returns the
four hero triples for such a scene instead of its own four rows, and `scene_entries()` unions the backdrop, the
four background rows and the hero four and nothing else. So the palette half of the question was answered on card
`t_c93a983f`; what was still wrong was the row, which named a cast the strip does not draw. This card changes the
row's `sprites` list, its `note` and its `exempt` text, and nothing else.

The one gap left is on the tool side and it is carded: `tools/palette_synergy.py` `analyse()` builds its `Scene`
from `scene_palette_set.scene(root, scene_id)`, and `scene()` uses `scene_payload()`, which returns the scene's own
four sprite rows. So the gate still judges a `party_cast` scene against rows the party does not spend, and the
recast row measures 324 fails in today's gate (see section 13). Card `t_6e8ca42f` closes that; this card writes
the row so that the cast is right the moment the tool reads the right half.

## 12. Q3: the deck is recast. The party takes its four sprite palettes and the enemy leaves the sprite half.

**Answer: recast, not leave. The deck row names the party's four battle sheets.**

The deck's PASS was real arithmetic on the wrong cast, and section 7.1 said so in advance: it "spends all four
deck triples on `sailor_battle.png` and `navy_sailor.png`, so it has no slot left for the party that the same room
draws at x=224. That PASS is a PASS on the cast the row names, not on the room." The card inherits that sentence
with one correction of its own: the walking sheet is not on the deck row and has not been since card `t_4f18c0ac`
(2026-10-24), so the row's cast was `sailor_battle.png` plus `enemies/navy_sailor.png`, not `sailor_ow_v2`.

Why recast is forced rather than chosen: the deck is the same battle screen as the corridor (`data/ui_layouts.json`
has one battle layout), so it draws the four 24x32 party slots, and the PPU gives a strip four sprite palettes.
A strip that draws all four heroes therefore has no sprite palette for an enemy at all, which is the Castlevania
and Final Fantasy convention ruling 7.5 already wrote down: the enemy is background art there.

Measured, all with the hero four as the scene's sprite palettes:

| row | result |
| --- | --- |
| the deck row as shipped (`sailor_battle.png`, `navy_sailor.png`) | FAIL, 126 fails, all cast: `sailor_battle.png` 93, `navy_sailor.png` 33 |
| the deck row recast (the four party battle sheets) | PASS, 0 fails, 0 uncovered tiles |
| the corridor row as shipped | FAIL, 24 fails, all `zander_ow_v2.png` |
| the corridor row recast | PASS, 0 fails, 0 uncovered tiles |

**Two prices, both measured, both other cards.**

1. **The enemy has no slot, and the deck's background set does not carry it either.** Ruling 7.5 sends the enemy
   to the background palettes. On the deck that is not a free move: a tile is drawn when one background triple
   carries its colour set, and measured per 8x8 tile against the deck's four background triples, 27 of
   `navy_sailor.png`'s 37 inked tiles fit none of them (10 fit), and 41 of `sailor_battle.png`'s 72 fit none
   (31 fit). So `navy_sailor`'s `$02 $0F $30` needs a deck background triple of its own before the enemy can be
   drawn on this strip at all. That is the art lane's file (`tools/art/make_battle_bg.py`).
2. **The deck's party block is not on `$0F`.** Section 7.4 point 2 ruled that the party block's floor is `$0F` on
   every battle strip, and card `t_d64eb2a9` landed that on the corridor and the wardroom. The deck and the quay
   were scoped out of that card, and the builder's own comment on it says the two floors are a gamedev decision.
   This is that decision: **the deck's block floor becomes `$0F`, the same change, and the quay's does too so the
   four strips cannot disagree.** Measured today, per slot, ground under the 24x32 box, under the hero four:

   | strip | y=32 | y=64 | y=96 | y=128 | pair fails at the block |
   | --- | --- | --- | --- | --- | --- |
   | corridor | `$0F` 768 | `$0F` 768 | `$0F` 768 | `$0F` 768 | 0 |
   | wardroom | `$0F` 768 | `$0F` 768 | `$0F` 768 | `$0F` 768 | 0 |
   | deck night | `$01` 624, `$11` 86, `$21` 58 | `$00` 443, `$10` 193, `$02` 132 | `$0F` 384, `$00` 306, `$02` 72 | `$0F` 768 | konrad 14, zander 7, percy 21, hadrian 0 = 42 `body_ground` |
   | quay dusk | `$01` 656, `$11` 96, `$26` 16 | `$00` 279, `$01` 261, `$11` 120, `$02` 83 | `$0F` 384, `$00` 279, `$02` 83, `$10` 22 | `$0F` 768 | konrad 14, percy 21, zander 21, hadrian 0 = 56 `body_ground` |

   The two strips that already stand on `$0F` read 0 at the block, which is the check that the reading is right
   and that the number is the floor's, not the sheets'.

## 13. What landed, measured before and after

**Landed.**

- `data/palettes/scene_battle_corridor.json`: `sprites` is the party's four battle sheets; `note` and `exempt`
  rewritten. The `exempt` now says the row draws the party four, that `zander_ow_v2` is a walking sheet the hero
  four cannot carry (24 pairs, 0 of 32 tiles), that the row measures red only for the tool reason carded as
  `t_6e8ca42f`, and that the exemption ends when that card lands.
- `data/palettes/scene_battle_deck_night.json`: the same four sheets, a new `note` that names the layout and
  where the sailor is still judged (the ship row against `ts_ship.png`), and a new `exempt` that carries the two
  measured prices above.
- `data/scene_palettes.json` rebuilt with `python tools/scene_palette_set.py build --write`: 10 lines added and
  6 removed, all inside those two audit rows. Nothing else in the derived file moved, and a second build is
  byte identical (`diff --strip-trailing-cr`, 0 lines).
- `tests/test_scene_palette_set.py`: the two battle rows are held to the party four and to an exemption; the
  mutation test now puts the walking sheet back on the corridor row (with its exemption cleared, because an
  exempt row is skipped by design) and requires the check to name it; the exempt list is the known three.

**Before and after, the gate, this tree, 2026-10-25.**

| run | entries | gated | advisory | per entry fails |
| --- | --- | --- | --- | --- |
| before | 6 | 0 | 4 | corridor 191, corridor contact sheet 11, deck 0, ship tileset 0, ship title 242, title 135 = 551 |
| after | 6 | 0 | 5 | corridor 324, corridor contact sheet 11, deck 324, ship tileset 0, ship title 242, title 135 = 1036 |

Both rows go from "wrong cast, some measurable state" to "right cast, 324 fails that are the tool's own half",
and both read 0 under the hero four. Nothing is gated, so `--gate` still exits 0, and
`python tools/scene_palette_set.py validate` prints PASS, 12 scenes, 4 hero palettes.

**Per row, the state that is honest to quote.**

| row | today's gate (scene's own rows) | hero four read (what `t_6e8ca42f` gives) | at the game's block |
| --- | --- | --- | --- |
| corridor, as shipped | 191 fails (percy 73, hadrian 86, zander_ow_v2 32) | 24 fails, all zander_ow_v2 | 24, all zander_ow_v2; percy and hadrian read 0 at every slot |
| corridor, recast | 324 fails (289 palette_count, 35 set_member) | **0 fails, 0 uncovered** | 0 fails |
| deck, as shipped | 0 fails (PASS) | 126 fails (sailor_battle 93, navy_sailor 33) | not restated: the enemy is never drawn in the party's slots |
| deck, recast | 324 fails (289 palette_count, 35 set_member) | **0 fails, 0 uncovered** | 42 body_ground at the block, the floor price above |

The "at the game's block" column is the placement the game actually draws (x=224, the four 24x32 slots) and the
other two are the row's own placement, which is the tool's default: for a 24x32 frame that is 116,192, centred
with the feet on the bottom band. The two are both quoted because they answer different questions and because
the row format cannot yet say "these four sheets sit in four different slots" (see section 14).

## 14. What this does not decide, and the two hazards it names

- **The tool half.** `tools/palette_synergy.py` still reads a `party_cast` scene's own four rows. Card
  `t_6e8ca42f` is ready on the board for that. Neither card alone makes the corridor row measure 0: this one
  makes the cast right, that one makes the reading right, and both are needed for the number.
- **The deck and quay block floors and the enemy's background triple.** Decided above, drawn by the art lane.
  Two cards carry the work: `t_12c9b18f` (the two floors, through `tools/art/make_battle_bg.py`, one region of two
  frames, the same shape as card `t_d64eb2a9`) and `t_34b1d96a` (which background triple on the deck spends the
  enemy's three colours, and what the strip costs for it).
- **A hazard this card found and did not cause.** `tools/art/make_battle_bg.py` writes
  `data/palettes/scene_battle_*.json` whole (`scene_palette_json()`, then `json.dump`), and it emits no `judged`
  key. So the next regeneration of any battle strip deletes that strip's audit row, which is where both rows this
  card just wrote live. Card `t_5802ecdb` is the fix: the generator has to carry the key forward. Until it does,
  anyone regenerating the corridor or the deck strip silently undoes this card, and card `t_12c9b18f` is
  sequenced behind it for exactly that reason.
- **The party walking sheets now sit on no audit row.** `zander_ow_v2.png` was named by exactly one row (the
  corridor battle row, on the wrong ground), and `percy_ow_v2.png`, `konrad_ow_v2.png` and `hadrian_ow_v2.png` are
  named by none. Their real ground is the map, not a battle strip, and the ship row already judges `sailor_ow_v2`
  against `ts_ship.png`, so the shape of the fix is known. Card `t_dec4e92c` asks which ground, and carries the
  measured starting point: of the four triples, two are still carried by town rows (`$02 $12 $30` for Percy and
  the sailor, `$07 $17 $28` for Konrad) and two are carried by NO row in the twelve sets at all (`$01 $11 $31`
  for Zander, `$00 $0F $30` for Hadrian), measured over `data/palettes/scene_*.json` by
  `measure_triples.py` in this card's workspace.
- **The row's single `at`.** One judged row carries one placement for its whole cast, so the four party slots
  cannot be expressed by one row; expressing them needs four rows (one sheet each, one `at` each) or a per sprite
  placement field. Named, not changed.
- **`"gate": false` on all twelve scenes.** Untouched, as before.

**Cards this ruling created, all with this card as their parent.**

| card | who | what |
| --- | --- | --- |
| `t_5802ecdb` | builder | the strip generator must carry the `judged` key forward instead of deleting the row it does not write |
| `t_12c9b18f` | builder | the deck night and quay dusk party block floors to `$0F` (waits on `t_5802ecdb`) |
| `t_34b1d96a` | gamedev | which deck background triple spends the enemy's three colours, and what the strip costs for it |
| `t_dec4e92c` | gamedev | which ground judges the four party walking sheets, two of which no row in the twelve sets carries |
| `t_39b06dd5` | builder | drops the two rows' exemptions once `t_6e8ca42f` is in HEAD, and holds both rows enforced (waits on that card) |

**Checks run on this tree, 2026-10-25, and what they returned.**

- `python tools/scene_palette_set.py build` before the edit: byte identical to the shipped file
  (`diff --strip-trailing-cr`, 0 lines), so the file was derived and the generator was not already drifted.
- `python tools/scene_palette_set.py build --write` after the edit: 10 insertions, 6 deletions, both inside the two
  audit rows; a second build byte identical.
- `python tools/scene_palette_set.py validate`: PASS, 12 scenes, 4 hero palettes.
- `python tools/palette_synergy.py --gate`: 6 entries, 0 gated, 5 advisory, 0 not measured, exit 0 (the numbers in
  section 13's table).
- `python -m pytest tests/test_scene_palette_set.py tests/test_palette_synergy.py tests/test_scene_palettes.py
  tests/test_make_battle_bg.py -q`: 57 passed.
- The per sheet and per slot readings are from `measure_cast.py`, `measure_slots.py` and `measure_enemy.py` in this
  card's workspace, which call `tools/palette_synergy.py`'s own `analyse()`, `frame_report()` and `Grid` rather
  than restating the arithmetic.

Provenance: studied this repository's own files only (`data/ui_layouts.json`, `data/palettes/scene_battle_*.json`,
`tools/scene_palette_set.py`, `tools/palette_synergy.py`, `tools/art/make_battle_bg.py`, the four battle frames and
the sheets in `game/sprites_src/`). No decompiled material, and no expression from another game, is in this
card. Copied expression: none.

## 15. Q1, Q2, Q3 on the deck: the enemy's three colours are spent on `bg2`, the one triple it actually stands on

**Answer, three parts.** Q1: neither of the two routes the card names. The deck's plate and railing triple,
`bg2`, changes from `$00 $10 $02` to `$00 $30 $02`, and that carries the enemy's `$02 $0F $30` whole, because
`$0F` is the shared backdrop every attribute area may already spend. Q2: `sailor_battle.png` is not drawn on the
deck at all, and it stays out of the deck's background budget. Q3: the walking sailor stays exactly where card
`t_1dc346b9` put him, on the ship row against `ts_ship.png`, and this card does not touch that row.

### 15.1 The fact the card did not have: where the enemy actually stands

The card's two candidate routes were argued on a union reading of the four deck triples. Background art is not
drawn from a union. It is drawn per 16x16 attribute area from that area's ONE triple, and both of the battle
screen's enemy slots land on `bg2` cells and nothing else. `data/ui_layouts.json` `screens[battle].enemies` is two
32x32 slots at tile 3,8 and tile 12,11:

| slot | pixels | 16x16 areas it covers | triple that governs it |
| --- | --- | --- | --- |
| tile 3,8 | 24,64 to 55,95 | 6 (rows 4 and 5, columns 1 to 3) | `bg2` only |
| tile 12,11 | 96,88 to 127,119 | 4 (rows 5 and 6, columns 6 and 7; 24 of the 32 rows fall inside the 112 px strip) | `bg2` only |

So the only triple that can ever draw the tutorial enemy on this strip is `bg2`. A `$30` spent on `bg3` is a
`$30` spent on cells no enemy stands on.

### 15.2 The card's headline number is an artefact of not counting the backdrop

The card quotes "27 of `navy_sailor.png`'s 37 inked tiles fit none of the deck's background triples". That is the
union reading with the backdrop left out. `tools/art/make_battle_bg.py`'s own rule is that an area's pixels are
"one of the palette's three colours plus the scene's one shared backdrop" (role 3, docstring point 1), so the right
union reading counts `$0F`:

| sheet, HEAD | union, backdrop not counted | union, backdrop counted | at the enemy's slots (backdrop counted) |
| --- | --- | --- | --- |
| `navy_sailor.png`, 36 inked tiles | 9 fit / 27 out | 36 fit / 0 out | 9 fit / 27 out, both slots |
| `petty_officer.png`, 30 inked tiles | 0 fit / 30 out | 30 fit / 0 out | 0 fit / 30 out, both slots |

`navy_sailor.png`'s `$02 $0F $30` is already carried by `bg0` (the sky, `$02 $01 $30`) the moment the backdrop
counts. The union was never the problem, and that is why a union reading could not choose the route. The slot
reading is the one that decides, and on the slot reading 27 of the 36 are uncovered.

The card's 37 tile count is a sheet with one more inked pixel than HEAD's; `git show HEAD:` gives 36. Both readings
are in the numbers above where they differ.

### 15.3 The four routes, measured

Strip cost is the pixel diff against the same scene built without the change, through `build_scene()` itself.
The enemy column is the slot at tile 3,8, backdrop counted, HEAD's sheet.

| route | strip pixels moved | 8x8 tiles changed | strip colours | enemy at tile 3,8 | enemy at tile 12,11 |
| --- | --- | --- | --- | --- | --- |
| as shipped | 0 | 0 | 8 | 9 fit / 27 out | 9 fit / 18 out |
| A `bg3 $0F $02 $00` to `$0F $02 $30` (the card's route) | 104, in a 216x16 box at 18,16 | 16 | 8 | **9 / 27, unchanged** | **9 / 18, unchanged** |
| B `bg2 $00 $10 $02` to `$00 $30 $02` | 2016, in a 256x46 box at 0,64 | 192 | 7 | **36 / 0** | **27 / 0** |
| C `bg2` to the enemy's own `$02 $0F $30` | 12288, in a 256x48 box at 0,64 | 192 | 7 | 36 / 0 | 27 / 0 |
| D `bg3` to the enemy's own `$02 $0F $30` | 200, in a 216x16 box at 18,16 | 16 | 8 | 9 / 27, unchanged | 9 / 18, unchanged |
| E repaint the sheet into the shipped `bg2` | 0 | 0 | 8 | needs 375 of 1001 opaque pixels repainted (`$30` to `$10` or `$00`), 37.5 percent of the figure | same |

Read down the enemy column. Route A and route D, the two that spend `bg3`, are the card's route and its literal
version, and both leave every enemy tile exactly as uncovered as it was, because no enemy tile is drawn under a
`bg3` cell. Routes B and C are the two that reach the slots. B and C draw the identical 36 of 36 and 27 of 27, so
the choice between them is cost alone: B changes one entry of `bg2` and leaves the plate body `$00` and the seam
`$02` where they are, C changes both and repaints the whole floor, 12288 pixels against 2016. E is the cheapest in
pixels and is refused on the ruling rather than on the cost: section 7.5 ends "the enemy keeps its own three
colours either way", and 7.5's quantise clause is about a strip drawing fewer than four heroes, which the deck
does not.

**Answer: B.** `bg2` becomes `$00 $30 $02`, and the deck's background row is rewritten by the generator that owns
it rather than by hand.

### 15.4 What the spend costs, exactly

Every one of the 2016 moved pixels is a single step: `$10` `#bcbcbc` was there before and `$30` `#fcfcfc` is there
after, and nothing else on the strip moves (`data/palettes/scene_battle_deck_night.json` records the same in its
own words, and the pixel diff of the two frames agrees):

- 128 px in the 32 `deck_plate` cells, which is the four rivet dots each cell carries;
- 1888 px in the 16 `deck_rail` cells, which is the rail's two highlight bands and its two uprights;
- attribute rows 4, 5 and 6 of 7, nothing in the sky, the horizon, the sea or the rigging;
- 1817 of them outside the party block and 199 inside it, and the 199 are inside the region card `t_12c9b18f`
  repaints to `$0F` anyway, so the two cards do not charge the player twice for the same pixels;
- the strip keeps its 29 unique 8x8 tiles and drops from 8 colours to 7, because `$10` no longer appears anywhere
  on the deck. That is a loss of one grey step on a night strip whose plate body stays `$00`; it is inside the
  25-colour budget either way.

The strip's own sidecar and its frame are both regenerated from the same build, so the shipped art and the record
in `game/sprites_src/bg/bg_battle_deck_night.json` cannot disagree.

### 15.5 Q2: `sailor_battle.png` is not drawn on the deck, and stays out of its budget

No. Three measured reasons.

1. **The encounter names one enemy and it is not that sheet.** `data/encounters/all.json` `tutorial_sailors` is
   `"enemies": ["navy_sailor"]`. `sailor_battle.png` is a 168x32 seven frame battle sheet with no column in that
   row.
2. **Its home is already written down and it is the ship.** `data/palettes/scene_ship.json`'s judged row names
   `sailor_battle.png` and `sailor_ow_v2.png` against `game/sprites_src/env/ts_ship.png` at 64,64 (card
   `t_1dc346b9`), where it measures PASS, 0 failing pairs, 0 uncovered. Moving it onto the deck would judge it on a
   ground it is not drawn on, which is the defect ruling 7.5 was written to stop.
3. **The deck cannot carry it and should not try.** Even after this card's spend, `sailor_battle.png` reads 31 of
   its 72 inked tiles inside the new `bg2` at the enemy slot, and the entries it needs and `bg2` does not have are
   `$07`, `$08`, `$17`, `$27` and `$36`. Carrying those is a second and third background entry spent on a sheet
   the room does not draw. It stays out of the deck's background budget, and out of the deck row.

### 15.6 Q3: the walking sailor stays where card `t_1dc346b9` put him

Yes, unchanged. `sailor_ow_v2.png` is judged on the ship row against `ts_ship.png` (measured there: PASS, 0 failing
pairs, 32 inked tiles, 0 uncovered) and this card touches no ship palette, no ship strip and no ship row. The deck
strip does not draw him and never did, which card `t_4f18c0ac` settled on 2026-10-24.

### 15.7 What landed, and the numbers before and after

**Landed.**

- `tools/art/make_battle_bg.py`: the `deck_night` scene's `bg2` is `[0x00, 0x30, 0x02]`, and its `notes` carry a
  fourth line saying why, so the generator owns the decision and a later run cannot quietly undo it.
- `data/palettes/scene_battle_deck_night.json`: written through the generator's own `scene_palette_json()` but
  assembled by hand at the keys the generator does not write (see 15.8), so `background` is the generator's
  new row, `judged[0].note` names the enemy's new route, `judged[0].exempt` records that price one is paid and
  price two is not, and the four sprite rows and notes 0 to 6 are byte for byte what they were.
- `game/sprites_src/bg/bg_battle_deck_night.png` and `.json`, `output/bg_battle_deck_night_frame.png`: regenerated
  from the same `build_scene()`, 976 B and 1072 B from 995 B and 1091 B, 2016 pixels each moved, all in the 256x46
  box at 0,64.
- `data/scene_palettes.json`: `python tools/scene_palette_set.py build --write`, 3 insertions and 3 deletions, all
  of them the three lines this decision moves (the deck's `bg2` second entry `16` to `48`, and the two audit
  strings). A second build is byte identical.

**What did not move, and the check that says so.** The other three strips are pixel identical to HEAD
(`bg_battle_corridor.png` 1237 B, `bg_battle_wardroom.png` 1421 B, `bg_battle_quay_dusk.png` 1178 B, all
unchanged), and so is `output/bg_battle_corridor_frame.png`.

**The deck row's own fail count does not move with this card, and that is the honest reading.** Under the tool as
it ships at HEAD the deck reads 324 fails before and after, and under card `t_6e8ca42f`'s half it reads 0 before
and after: all 324 are the four party sheets against the sprite half (289 `palette_count` plus 35 `set_member`),
and the strip's background does not enter them. This card is a background decision and it moves the background.

**The gate, this tree, 2026-10-25.**

| run | entries | gated | advisory | per entry fails |
| --- | --- | --- | --- | --- |
| parent card `t_0949bd4e`, before this card | 6 | 0 | 5 | corridor 324, corridor contact sheet 11, deck 324, ship tileset 0, ship title 242, title 135 = 1036 |
| this card | 6 | 0 | 3 | corridor 0, corridor contact sheet 16, deck 0, ship tileset 0, ship title 242, title 135 = 393 |

Both readings are on this tree with `tools/scene_palette_set.py` as card `t_6e8ca42f` has it in the working tree,
which is the half that makes a `party_cast` strip read the four hero triples. `python tools/scene_palette_set.py
validate` prints PASS, 12 scenes, 4 hero palettes.

**Checks run, and what they returned.**

- `python -m pytest tests/test_make_battle_bg.py tests/test_scene_palette_set.py tests/test_scene_palettes.py -q`:
  38 passed. `tests/test_make_battle_bg.py` includes "the committed strips are what the generator writes", so the
  regenerated PNG is in the commit that claims it.
- `python -m pytest tests/test_palette_synergy.py tests/test_kaggle_r7.py -q`: 32 passed.
- `python tools/scene_palette_set.py build` twice: the second is byte identical to the file this card commits.
- The measurements are in this card's workspace: `measure_deck_enemy.py` (the slots, the two union readings, all
  four routes through `build_scene()`), `measure_cost.py` (the pixel accounting and every enemy sheet against the
  new `bg2`), `measure_before_after.py` (before and after at the slots, HEAD's sheets), `measure_enemy_slots.py`
  and `png_diff.py`. They call `palette_synergy.Grid`, `contrast_check.load_sheet`, `palette_synergy.frame_size`
  and `make_battle_bg.build_scene` rather than restating the arithmetic.

### 15.8 What this does not decide

- **The draw.** Nothing on screen changes, because nothing draws the enemy or the strip yet: `pp_battle_director`
  resolves `_battle.bg_name` at line 92 and no draw call reads it, and no draw call loads any enemy sheet, so
  neither the strip nor the sailor reaches the screen. This card makes the palette able to carry the enemy; it
  does not draw it. Card `t_4275136f` owns the drawing, and it is not an art card: no sheet and no strip has to be
  redrawn for this ruling.
- **The other enemy on the deck.** `data/encounters/all.json` also carries `deck_hound`, which has no sheet in
  `game/sprites_src/enemies/` at all. When it gets one, its colours have to fit `bg2` or this decision reopens;
  the coverage table in this card's `measure_cost.py` is the tool that would say so. `petty_officer.png` already
  fits the new `bg2` whole, 30 of 30.
- **The deck's palette file has two owners.** `tools/art/make_battle_bg.py` writes it whole and emits no `judged`
  key (card `t_5802ecdb`), and its `SCENES` sprite rows for `deck_night` no longer match the four rows the file
  ships, so a full run today would rewrite both. Card `t_8ebcb489` owns that half. This card therefore writes the
  deck's file deck by deck and keeps the hand owned keys, which is the smallest move that does not lose another
  card's work.
- **The deck's party block floor** is still not `$0F`. Card `t_12c9b18f` owns it, and its 199 pixels of overlap
  with this change are inside the region that card repaints.

Provenance for section 15: studied this repository's own files only (`data/ui_layouts.json`,
`data/encounters/all.json`, `data/palettes/scene_battle_deck_night.json`, `data/palettes/scene_ship.json`,
`tools/art/make_battle_bg.py`, `tools/scene_palette_set.py`, `tools/palette_synergy.py`, `tools/art/contrast_check.py`,
the four battle strips and frames, and the sheets in `game/sprites_src/`). No decompiled material, and no
expression from another game, is in this card. Copied expression: none.

