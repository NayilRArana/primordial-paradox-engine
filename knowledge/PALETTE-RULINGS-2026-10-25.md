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


## 16. The party's four walking sheets are judged on the towns' own spawn frames, and the two homeless triples are bought back on the towns' two free rows

Card `t_dec4e92c`, raised by section 14's last hazard. Measured 2026-10-25 on this tree. Section 15 is card
`t_34b1d96a`'s deck background ruling and landed as e53a160 while this one was being written; the two sections are
numbered against the file, not against either card's clock, and this one owns the party's walking sheets and nothing
else.

### 16.1 Q1: the ground is the frame `tools/art/make_exterior_maps.py` composes at the spawn, not `ts_exterior.png`

The candidates were the three towns and the ship. The ship's worked example (card `t_1dc346b9`) is
`game/sprites_src/env/ts_ship.png` at `--at 64,64`, and the reason it works is not that it is a tileset: it is that
a ground has to measure clean, so only the sprite's own rules can fail on it. `ts_ship.png` spends four background
palettes and reads 0. The exterior atlas cannot do that:

| ground | what it measures |
| --- | --- |
| `game/sprites_src/env/ts_exterior.png` against southampton | **7** `palette_count` problems |
| the same atlas against westminster | **4** |
| the same atlas against winchester | **4** |
| `game/sprites_src/env/ts_ship.png` against ship | **0** |

The atlas spends FIVE groups (`bg0_stone`, `bg1_brick`, `bg2_green`, `bg3_water`, `bg4_red`, read off
`ts_exterior.json`) and a scene spends four. So the atlas is a legal ground for no town at all, and judging a
walking sheet on it would charge the atlas's own fifth-group areas to the sprite standing there: the exact defect
card `t_1dc346b9` ruled out, in a different file.

A screen capture is out for the reason that card gave: a composed capture carries colours off the 2C02 table and
the tool charges them to the sprite. What replaces the atlas is not a capture but the other build product the same
generator writes: `output/<place>_sample_frame.png`, the 256x240 viewport the PPU would show at the spawn, built
tile by tile from that atlas under the four group budget `enforce_palette_budget()` refuses to break.

| property | measurement |
| --- | --- |
| drawn inside the town's own four background rows | `background_report` 0 problems on all three, and 0 `set_member` on any pixel (3 scenes x 256x240 px) |
| a file a clean checkout carries | committed by this card: three `.gitignore` exceptions after `output/*`, three `tools/check_test_inputs.py` FIXTURES entries |
| reproducible, so a row measures art and not a capture | a probe root carrying only the inputs the generator opens (`ts_exterior.png/.json`, the three OSM drafts, `data/nes_palette.json`) rerun to **byte identical** on all three frames and all three scene files |
| the ground the party actually stands on | spawn tiles southampton 17,18, westminster 16,20, winchester 16,19; crop origin 9,11 / 8,13 / 8,12, so the spawn tile is at **128,112** in every frame |

So the rule that governs both maps is one sentence: the ground is the thing the room is built from, and it has to
be drawn inside the scene's own four background rows. For the ship those are the same file. For the towns only the
composed frame satisfies both halves, and that is the file the rows name.

### 16.2 Q2: what the four sheets read there, and the fact that decided the answer

Measured before this card's edits, at `--at 128,112`, on the towns' rows as they shipped
(`sp0 $00 $0F $10`, `sp1 $07 $17 $28`, `sp2 $09 $0A $2A`, `sp3 $02 $12 $30`):

| sheet | its triple | carried by | cast problems per town (S / W / W) |
| --- | --- | --- | --- |
| `percy_ow_v2` | `$02 $12 $30` | town `sp3`, ship `sp1` | 0 / 0 / 0 |
| `konrad_ow_v2` | `$07 $17 $28` | town `sp1` (and `bg1` as a background row) | 0 / 0 / 0 |
| `zander_ow_v2` | `$01 $11 $31` | **nothing in the twelve sets** | 32 / 32 / 32 |
| `hadrian_ow_v2` | `$00 $0F $30` | **nothing in the twelve sets** | 8 / 8 / 8 |

The two homeless sheets fail in two different ways, and the difference matters. Zander's three entries are in no
town row at all, so he reads 24 `set_member` plus 8 `palette_count` per town. Hadrian reads 8 `palette_count` and
**no** `set_member`: `$00` and `$0F` sit in `sp0`, `$30` sits in `sp3`, and no single row holds all three. A row
check that only counted `set_member` would have called Hadrian legal.

The tempting fix is to solve the towns' two placeholder rows to those two triples. That is what this card does, and
the measurement that decided it is that the rows are free:

- `data/palettes/scene_southampton.json`'s own note says the sprite rows were written as "the same entries as the
  background set, reserved for the CHAR lane".
- `sp0 {0,15,16}` is `bg0` and `sp2 {9,10,42}` is `bg2`, copied. Neither is a decision about a cast.
- Measured across every one of the **78** PNGs in `game/sprites_src/`, exactly two fit a town row today:
  `konrad_ow_v2` (`sp1`) and `percy_ow_v2`/`sailor_ow_v2` (`sp3`). **No sheet in the tree fits `sp0` or `sp2`.**
- `tools/art/make_characters_v2.py` already wrote down where Zander's triple was to go: "the deck is the battle
  strip and draws its fight cast, so Zander's walking triple is bought back on a ground he walks on, not here"
  (card `t_cc0c5bd5`, on the zander entry). This is that ground.

**Ruled: `sp0` becomes `$00 $0F $30` and `sp2` becomes `$01 $11 $31` in all three towns.** No pixel of any sheet
changes for the cast.

What that buys, measured through `tools/palette_synergy.py`'s own `frame_report` after the edit, on all three
towns: **cast 0 for all four sheets**, each fitting exactly one row (`sp0` hadrian, `sp1` konrad, `sp2` zander,
`sp3` percy), 32 inked 8x8 tiles per sheet and **0 uncovered**.

The other fix, repainting the four walking sheets into their reserved hero triples, was measured and refused:

| after the repaint (towns = hero four) | southampton | westminster | winchester |
| --- | --- | --- | --- |
| cast | 0 | 0 | 0 |
| pair fails | 16 / 12 / 8 / 10 | 16 / 16 / 16 / 10 | 8 / 8 / 8 / 6 |

It is not better on the pair column, it overwrites the four sheets the art lane drew "palette first" (the four
battle sheets already ARE the hero triples, `percy_battle $0F $12 $28` and so on, so battle identity is intact),
and it contradicts the project's own written plan for Zander quoted above. The walking sheet is a different drawing
on a different ground; it gets a triple bought from that ground.

### 16.3 Q3: the rows are `judged` lists in the town scene files, enforced, and here is when an exemption is the answer

One row per town, in `data/palettes/scene_southampton.json`, `scene_westminster.json` and
`scene_winchester.json`: `background` the town's own frame, `at [128, 112]`, `sprites` the four walking sheets,
and no `exempt`. They are enforced from the day they land, because the cast is carried.

An exemption is the bookkeeping while a card is open, never the answer to "this scene cannot carry the sheet"
(section 10 and 12's shape: row landed, exempt with the reason and the card that ends it). Here it was not needed:
the scene had two free rows, and the first move when a scene cannot carry a sheet is to check whether a row is
free, which is a measurement and not a preference. If no row had been free, the answer would have been a repaint
card with the row exempt until it landed.

What the rows report beyond the cast is not a cast question and is not exempt:

| town | pair fails | of which |
| --- | --- | --- |
| southampton | 36 | `white_blob` 22, `body_ground` 10, `invisible` 2, `same_hue_row` 2 |
| westminster | 88 | `white_blob` 44, `body_ground` 26, `invisible` 16, `same_hue_row` 2 |
| winchester | 32 | `white_blob` 22, `body_ground` 10 |

Every one of them is the sheet's own body against the street surface under the spawn tile: `$10 #bcbcbc`, with
`$30 #fcfcfc` on the westminster crop, out of `bg0_stone {0,16,48}`. The bodies are `$30` for percy and hadrian,
`$31` for zander, `$28` for konrad. On westminster, hadrian's body IS the paving colour on 8 of the 8 frames of the
walk cycle, which is what `invisible` names. Card **`t_454c1876`** (builder) carries it, with both prices named:
move the walkable street off the light group, or repaint the four bodies, and if a repaint moves a triple it
re-opens this card's row solve.

### 16.4 The generator hazard is closed here, not carded

`tools/art/make_exterior_maps.py` wrote each `scene_<place>.json` WHOLE and emitted neither `judged` nor a solved
sprite half, so the rows and the row solve this card just wrote were one regeneration away from deletion: the
identical defect card `t_5802ecdb` closed on `tools/art/make_battle_bg.py`. Fixed at the cause:

- `judged_rows()` keeps any `judged` list it finds, verbatim.
- `solved_sprites()` keeps a sprite half that DIFFERS from the generator's own placeholder, and does not carry an
  identical one (a copy of the background groups is reproduced, not preserved), so a later background change is
  not fought by a stale copy.
- both are printed when they happen, so a run says what it kept.
- `tests/test_make_exterior_maps.py` holds five behaviours: fresh file gets the placeholder and no `judged`; a
  solved half survives; a judged row survives verbatim; a placeholder half is not carried; and the three shipped
  town files are reproduced byte for byte by the generator in a scratch root.

### 16.5 What landed, measured before and after

| run | entries | gated | advisory failing | per entry fails |
| --- | --- | --- | --- | --- |
| before | 6 | 0 | 3 | corridor 0, corridor contact sheet 14, deck 0, ship tileset 0, ship title ground 242, title 135 = **391** |
| after | 9 | 0 | 6 | corridor 0, contact sheet 16, deck 0, ship tileset 0, ship title ground 242, southampton 36, title 135, westminster 88, winchester 32 = **549** |

The three new rows carry **0 cast problems between them** and 156 pair fails, all of them card `t_454c1876`'s. The
contact sheet moved 14 to 16 without this card touching it: `output/sprites_v2_sheet.png` is a by-product two
generators write and another lane regenerated it at 17:24, which is why section 8 made it advisory whatever it
measures. `--gate` exits 0 before and after.

Landed:

- `data/palettes/scene_southampton.json`, `scene_westminster.json`, `scene_winchester.json`: `sp0` and `sp2`
  solved to the party's walking triples, `sp1` and `sp3` unchanged, the placeholder note rewritten, one `judged`
  row each.
- `data/scene_palettes.json` rebuilt with `python tools/scene_palette_set.py build --write`: 57 insertions and 12
  deletions, all of them the three town scene entries and the three new audit rows.
- `.gitignore` and `tools/check_test_inputs.py`: the three frames committed and named as fixtures.
- `tools/art/make_exterior_maps.py`: the carry-forward above.
- `tests/test_scene_palette_set.py`: the three rows, the four rows, and each sheet's own colour set held against
  them; `tests/test_make_exterior_maps.py` new.

Checks on this tree, 2026-10-25:

- `python tools/scene_palette_set.py build --write` then `validate`: **PASS, 12 scenes, 4 hero palettes**.
- `python tools/palette_synergy.py --gate`: the table above, exit 0.
- `python -m pytest tests/test_scene_palette_set.py tests/test_palette_synergy.py tests/test_scene_palettes.py
  tests/test_make_exterior_maps.py tests/test_test_inputs.py -q`: 67 passed, including the two rows that read the
  repository's own tracked file list (`test_every_judged_rows_ground_is_a_file_a_clean_checkout_carries`,
  `test_test_inputs`), which were red until the commit landed because the frames are staged by it.
- The per sheet, per town and per state numbers are from `measure_frames.py`, `measure_carriers.py`,
  `measure_states.py` and `simulate_rows.py` in this card's workspace, which call `palette_synergy`'s
  `frame_report`, `Grid` and `background_report` rather than restating the arithmetic.

### 16.6 What this does not decide

- **The party inside the ship.** The ship's four rows are spent on `sailor_battle` and `sailor_ow_v2` (its row
  measures 0 on `ts_ship.png`), and of the four walking sheets only Percy fits one of them. Card `t_a6a7a436`.
- **The towns' paving against the party's bodies.** Card `t_454c1876`, with the numbers above.
- **A town NPC.** The towns' four rows are now entirely the party, so a townsfolk sprite has no palette of its
  own: it must be drawn inside one of the four, or a row has to be given up, and which is a card this one does not
  write because no townsfolk sheet exists yet.
- **One identity everywhere.** The walking sheets stay off the reserved hero triples, and that is now a written
  fact rather than an oversight: battle sheets are the hero triples, walking sheets are triples bought from a
  walking ground. A card that wants one identity on both would change `make_characters_v2.py` and the three towns'
  rows together, and would have to beat the pair numbers in 16.2 to say why.

Provenance: studied this repository's own files only (`data/palettes/scene_*.json`, `data/scene_palettes.json`,
`tools/scene_palette_set.py`, `tools/palette_synergy.py`, `tools/art/make_exterior_maps.py`,
`tools/art/make_characters_v2.py`, `tools/art/scene_palette.py`, `game/sprites_src/env/ts_exterior.json`, the four
walking sheets, the three map frames and `data/maps/*.json`). Copied expression: none.

## 17. The ship's four sprite palettes are the party's four walking triples, and the walking sailor costs no row because his triple IS Percy's

Card `t_a6a7a436`, raised by 16.6. Measured 2026-10-25 on this tree at `d429b7a`, over
`data/palettes/scene_ship.json` as HEAD carried it and `game/sprites_src/env/ts_ship.png` at `--at 64,64`.

**Answer, three parts.** Q1: the first option, with one correction to its own parenthetical. The ship's four
sprite rows are re-solved for the party and become the party's four walking triples, `$00 $0F $30` (hadrian),
`$02 $12 $30` (percy), `$01 $11 $31` (zander), `$07 $17 $28` (konrad). The sailor's walking row does not have to
MOVE, it has to be SHARED: `sailor_ow_v2.png` is `$02 $12 $30` to the entry, which is Percy's triple, so he is
drawn in Percy's row and the party's four rows carry five walking sheets with nothing repainted. Q2 is refused on
two measurements, not one. Q3 is refused because the file-per-room split would carry the same four rows twice.
`sailor_battle.png` comes off the ship's judged row in the same edit, and its ground is card `t_0b9c2faf`.

### 17.1 The starting state, measured per sheet

Seven colours across the four rows, and of the five walking sheets exactly one fitted one of them:

| sheet | its triple | row it fits at HEAD | cast problems | inked 8x8 tiles that fit no row |
| --- | --- | --- | --- | --- |
| `hadrian_ow_v2` | `$00 $0F $30` | none | 8 `palette_count` | 30 of 32 |
| `konrad_ow_v2` | `$07 $17 $28` | none | 8 `palette_count` | 26 of 32 |
| `zander_ow_v2` | `$01 $11 $31` | none | 24 `set_member` + 8 `palette_count` | 32 of 32 |
| `percy_ow_v2` | `$02 $12 $30` | `sp1` | 0 | 0 |
| `sailor_ow_v2` | `$02 $12 $30` | `sp1` | 0 | 0 |
| `sailor_battle` | ten entries, `$00 $02 $07 $08 $0F $10 $17 $27 $30 $36` | mixes, no single row | 0 uncovered | 0 of 72 |

The card's numbers reproduce exactly. What the card did not say is WHY the rows were what they were, and it is the
fact that decides Q1: `tools/art/scene_palette.py` `solve_ship()` solves the sprite half from
**`ts_ship.png`'s own 8x8 subtiles with `SHIP_SPRITES` in the pool**, so the four rows are a property of the
tileset plus the sailor, and `scene_ship.json`'s note said so in its own words ("the sheet cut to 8x8, so any tile
can also be drawn as sprites"). They were never solved for a walking cast at all.

### 17.2 Q1: the rows are the party's four, and the sailor is carried by one of them exactly

The constraint is section 7.1 and 16.6: a ground that draws the party has to carry the party's four walking
triples in its four rows, because the PPU has four sprite palettes and no fifth. The ship is a ground that draws
the party: `data/maps/ship_sample.json` is the map `rm_pp_ship` plays (`game/scripts/pp_data/pp_data.gml` lines
115 to 121 append it beside `maps/all.json`), the deck and the cabin are `ship_small` and `ship_cabin` in
`data/maps/all.json`, and `pp_overworld_draw_hero()` draws the party's figure on all three.

The measurement that makes this cheap is one row of the table above: `sailor_ow_v2.png` and `percy_ow_v2.png` are
the same three entries, not merely similar ones. A shared triple is the only kind of sharing the hardware allows,
and it is exact here, so the sailor does not displace a hero and no hero loses his colours. Percy keeps `sp1`,
where his triple already was and where the sailor was already drawn; the other three rows are solved:

| row | HEAD | after | whose |
| --- | --- | --- | --- |
| `sp0` | `$00 $0F $10` | `$00 $0F $30` | hadrian (`$10` `#bcbcbc` becomes `$30` `#fcfcfc`) |
| `sp1` | `$02 $12 $30` | `$02 $12 $30` | percy, unchanged, and the walking sailor |
| `sp2` | `$07 $17 $36` | `$01 $11 $31` | zander (the rust and the skin leave, the pale blues arrive) |
| `sp3` | `$08 $27 $28` | `$07 $17 $28` | konrad (`$08` `#503000` becomes `$07` `#881400`) |

Measured after, `tools/palette_synergy.py --scene ship --background game/sprites_src/env/ts_ship.png` with all
five sheets at `--at 64,64`: **PASS, 0 failing pair(s)**, 32 inked 8x8 tiles each and 0 uncovered, and each sheet
reports exactly one row in its `palettes that fit` column (hadrian `[0]`, percy `[1]`, zander `[2]`, konrad `[3]`,
the sailor `[1]`).

The four rows are now the same four triples the three towns carry (16.2), which is what makes the party's walk
read the same on every ground it walks. The row ORDER differs from the towns because it is not a decision: Percy
stays on `sp1` because the sailor is there, and `scene_palette_set.HEROES` already orders the battle strips
differently again, so there is no project-wide hero-to-row convention to break or keep.

**What the spend costs, measured.** The rows stop being a second drawable copy of the ship tileset. Every 8x8
subtile of `ts_ship.png` with pixels, against the four rows:

| rows | subtiles | fit no row |
| --- | --- | --- |
| HEAD | 192 | **52** |
| this ruling | 192 | **141** |

So the old note's promise was already only two thirds true, and it is now a third true. Nothing draws a ship tile
as a sprite today: `pp_map_draw()` draws the room from the tileset, and the four BACKGROUND rows still carry all
48 tiles (`tools/check_scene_palettes.py`: 0 tiles outside the background palettes). A ship effect that has to be
drawn from the sprite layer is a card that moves a row or draws it from the background set.

**And the four sheets cost the rows nothing.** `tools/art/scene_palette.py` `enforce_sprites()` against the four
rows, in memory, on this tree:

| sheet | opaque pixels moved, HEAD rows | this ruling's rows |
| --- | --- | --- |
| `hadrian_ow_v2` | 288 | **0** |
| `konrad_ow_v2` | 376 | **0** |
| `zander_ow_v2` | 1150 (all of it) | **0** |
| `percy_ow_v2` | 0 | **0** |
| `sailor_ow_v2` | 0 | **0** |
| `sailor_battle` | 0 | 621 of 2398 |

The last row is 17.4's business.

### 17.3 Q2: the two casts DO share a screen, and three heroes lose their colours, not two

The option is "the party is drawn with the sailor's rows indoors because the two casts never share a screen, which
needs a measured statement of which hero triple survives and which two heroes lose their colours there". Both
halves of that premise fail.

1. **They share a screen.** `data/maps/ship_sample.json` (the room `rm_pp_ship` plays) declares two sailor actors
   on the map the party walks: `sailor_watch` at 9,9 facing left and `sailor_galley` at 20,13 facing up, both
   `kind: sailor`. `pp_overworld` draws them with `PP_SAILOR_SHEET "sailor_ow_v2"` (line 627) on the same frame it
   draws the hero with `PP_HERO_SHEET "zander_ow_v2"` (line 626). There is no room in the slice where a sailor
   actor and the party are not on one screen together.
2. **Three heroes lose their colours, not two.** Under the sailor's rows the survivors are Percy and the sailor:
   konrad 8 `palette_count` with 26 of his 32 inked tiles fitting no row, hadrian 8 with 30 of 32, zander 32 with
   32 of 32. Forty eight failing pairs over three sheets, and Zander's whole body leaves the set.

So Q2 is not a trade that can be measured better, it is a trade whose premise is false. Refused.

### 17.4 `sailor_battle.png` comes off the row, and that is the same defect in the other direction

The card's DO NOT says not to put a walking sheet on a battle strip. Card `t_0949bd4e` removed exactly that
(`zander_ow_v2` off the corridor row) on the reasoning that a row's ground has to be the ground the room draws on.
The ship's row was carrying the mirror image: a 168x32 seven frame BATTLE sheet, judged on a walking room's
tileset, under rows now spent on walking figures. Three measurements say it does not belong there.

1. **Nothing draws it.** `data/encounters/all.json` has three encounters and the ship one is `tutorial_sailors`
   with `"enemies": ["navy_sailor"]`; `data/enemies/roster.json` gives `navy_sailor` the sheet
   `game/sprites_src/enemies/navy_sailor.png`. `pp_overworld` draws two sheets and neither is this one. No GML file
   names it.
2. **The ship's rows cannot carry it any more.** Under the four walking rows, 40 of its 72 inked 8x8 tiles fit no
   row (0 of 72 before), and the tool reads **FAIL, 53 failing pairs** on the ship ground.
3. **Enforcing it into those rows would damage the sheet.** 621 of its 2398 opaque pixels would be repainted, which
   is why `tools/art/make_characters.py` no longer runs its `enforce_sprites()` pass over it.

Section 15.5 said its home "is already written down and it is the ship". That sentence was answering a different
question (whether the DECK STRIP's background budget should carry it) and it is corrected here: a judged row's
ground is the ground the room is drawn on, and the ship's ground is a walking room. Its own card, `t_0b9c2faf`,
asks whether it is the sailor fight's battle art or a retired sheet, and where a battle figure is judged. Until
that lands it is judged on no row, which is the honest state for a sheet no room draws.

### 17.5 Q3: a second scene file would carry the same four rows and drift

Refused on measurement. The three ship rooms (`ship_small` deck, `ship_cabin`, `ship_sample` lower deck) share one
tileset and one walking cast: the party walks all three, and the only cast difference between them is the two
sailor actors on the lower deck, who cost no row because they are Percy's triple. A file per room would therefore
hold four identical triples twice, and the second copy could only drift from the first. The pattern the towns use
is one file per TOWN because each town is its own ground; the ship is one ground (`ts_ship.png`) with three rooms
drawn on it. The deck's own row already exists and is a battle strip (`scene_battle_deck_night`, recast by card
`t_0949bd4e` and spent on the enemy's colours by card `t_34b1d96a`); nothing about it is touched here.

### 17.6 The generator hazard, closed here rather than carded

`tools/art/scene_palette.py` `write_scene()` wrote the scene file WHOLE with no `judged` key, so
`solve --scene ship --write` would have (a) deleted card `t_1dc346b9`'s audit row and (b) re-solved the party's
four rows back into the tileset plus sailor pool. That is the third instance of one defect: card `t_5802ecdb`
closed it on `tools/art/make_battle_bg.py` and card `t_dec4e92c` on `tools/art/make_exterior_maps.py`.

Fixed at the cause, with two behaviours and two constants (`JUDGED_KEY`, `SPRITES_PINNED_KEY`):

- `judged` is carried forward verbatim, always, whatever wrote it. Printed when it happens.
- a sprite half marked `"sprites_pinned": true` in the file is a CAST DECISION, not a solve product: the solve
  keeps the rows AND the notes that explain them, and prints that it kept them. The background half is still the
  solver's. `data/palettes/scene_ship.json` carries the flag and a note that says why.
- `tests/test_scene_palettes.py` holds both: a scratch root with a copy of the shipped file, a solve against it
  that must keep the sprite half, the notes and the judged row while the background half moves, and a control with
  the pin removed that must take the solver's rows.

The pin exists because the row solve is a decision shared by hand with the towns (16.2). A scene whose sprite half
is a solve product keeps no flag and behaves exactly as before, which is every other scene file in the tree.

### 17.7 What landed, measured before and after

| run | entries | gated | advisory | ship row | ship/title row | total problems |
| --- | --- | --- | --- | --- | --- | --- |
| before | 9 | 0 | 6 | 0 | 242 | 549 |
| after | 9 | 0 | 6 | 0 | 242 | 549 |

The totals do not move, and that is the honest reading: the old row measured 0 on the cast it named (the sailor's
two sheets), so the gate could not see the defect at all. What moves is WHAT the row measures. The same is true of
`tools/check_scene_palettes.py`, which passes before and after and now holds five walking sheets instead of two
sailor sheets: `0` groups over three colours and `0` groups outside a palette on all five.

Landed:

- `data/palettes/scene_ship.json`: `sp0`, `sp2` and `sp3` solved to hadrian, zander and konrad, `sp1` unchanged,
  `sprites_pinned: true`, the sprite note and the judged row rewritten with the numbers above, and
  `judged[0].sprites` now the walking cast (hadrian, percy, zander, konrad, sailor_ow_v2) at the unchanged
  `at [64, 64]`.
- `data/scene_palettes.json`: rebuilt with `python tools/scene_palette_set.py build --write`, one ship entry and
  one audit row moved.
- `tools/art/scene_palette.py`: `write_scene()` carries `judged` and a pinned sprite half forward; both printed.
- `tools/check_scene_palettes.py`: `SHIP_SPRITES` is the walking cast.
- `tools/art/make_characters.py`: the enforce pass is `sailor_ow` only, with the 621 pixels measured in the comment.
- Tests: `tests/test_scene_palette_set.py` (the ship row's cast, and the four walking grounds carry the same four
  triples, with the sailor and Percy's sheets held to the same three entries), `tests/test_scene_palettes.py` (the
  pinned half and the judged row survive a solve), `tests/test_palette_synergy.py` (the ship ground carries the
  five walking sheets; `sailor_battle`'s coverage is recorded as 40 of 72 rather than asserted as clean).

Checks on this tree, 2026-10-25:

- `python tools/scene_palette_set.py build --write` then `validate`: **PASS, 12 scenes, 4 hero palettes**.
- `python tools/palette_synergy.py --gate`: the table above, exit 0.
- `python tools/check_scene_palettes.py`: **PASS**, five ship sprites, no group over three colours.
- `python -m pytest tests/test_scene_palette_set.py tests/test_palette_synergy.py tests/test_scene_palettes.py
  tests/test_nes_composite_check.py tests/test_make_env_ship.py tests/test_make_characters_v2.py -q`: 97 passed.
- The per sheet, per row and per subtile numbers are from `measure_sheets.py` and `measure_spend.py` in this
  card's workspace, which call `palette_synergy.Grid`, `frame_pixels`, `scene_palette.Scene` and
  `enforce_sprites()` rather than restating the arithmetic.

### 17.8 What this does not decide

- **`sailor_battle.png`'s ground.** Card `t_0b9c2faf`. It is judged on no row until that lands, and
  `tools/art/scene_palette.py`'s `SHIP_SPRITES` solve pool still lists it, which only matters for a scene file
  created from scratch (a pinned half never reaches the file). The two lists disagreeing is named on that card.
- **A ship tile drawn from the sprite layer.** 141 of 192 subtiles fit no row now. Nothing draws one; a card that
  wants one moves a row or draws it as background.
- **A ship NPC that is not the sailor.** The four rows are the party's and the sailor's exactly; a third walking
  cast on the ship has no row and would have to displace one, which is a card this one does not write.
- **The body-against-ground pairs on the new cast.** The ship reads 0 failing pairs, so there is nothing to hand
  on: `ts_ship.png` at 64,64 is dark plating and every body reads against it. The towns' paving question stays
  card `t_454c1876`'s.
- **The party's walking identity everywhere.** Unchanged from 16.6: battle sheets are the hero triples, walking
  sheets are triples bought from a walking ground, and the ship is now a signed-up member of that rule.

Provenance for section 17: studied this repository's own files only (`data/palettes/scene_ship.json`,
`data/scene_palettes.json`, `data/maps/all.json`, `data/maps/ship_sample.json`, `data/encounters/all.json`,
`data/enemies/roster.json`, `data/nes_palette.json`, `tools/art/scene_palette.py`, `tools/scene_palette_set.py`,
`tools/palette_synergy.py`, `tools/check_scene_palettes.py`, `tools/art/make_characters.py`,
`game/scripts/pp_overworld/pp_overworld.gml`, `game/scripts/pp_data/pp_data.gml`, the four walking sheets, the
sailor's two sheets and `game/sprites_src/env/ts_ship.png`). No decompiled material, and no expression from
another game, is in this card. Copied expression: none.

## 18. Q1 and Q2 on the battle strip's scene file: the deck's four declared rows are the 2026-10-24 solve, and the notes list is the generator's (card t_8ebcb489)

**Answer, both parts.** Q1: the deck's four own sprite rows ARE dead data (a `party_cast` strip is read against
the four reserved hero triples and nothing else), and they are still the record, so `SCENES` in
`tools/art/make_battle_bg.py` now declares the four rows the file carries. Q2: there is no `notes` carry rule. The
generator owns the notes list whole, the two hand written notes are lines in `SCENES` now, and nothing else about
the file is hand editable. After the change, regenerating all four strips moves **0 lines** in all four palette
files, where HEAD 0b5dd01 moved 64 in the deck's and 5 in the quay's.

### 18.1 The measurement, refreshed

The card's numbers were taken at HEAD 29128aa (deck 46 changed lines, quay 3). Between that measurement and this
card, card `t_34b1d96a` added a note to the deck's `SCENES` entry and typed the generator's stock sprite note into
the file by hand, so the same scratch root comparison at HEAD 0b5dd01 reads:

| file | changed lines at HEAD | what they were |
| --- | --- | --- |
| `scene_battle_corridor.json` | 0 | 2 judged rows carried |
| `scene_battle_wardroom.json` | 0 | nothing carried |
| `scene_battle_deck_night.json` | 64 | 38 of them the four sprite rows, and three notes lines: the missing bg2 note, the 2026-10-24 solve note, and the stock note the file carried twice |
| `scene_battle_quay_dusk.json` | 5 | the ruling note the generator does not emit |

So the deck had three defects in one file, not two: rows the generator did not emit, a note the generator emits
that the file did not carry (the bg2 enemy note from `t_34b1d96a`, which reached the background numbers and not the
note), and a hand note. A regeneration is a two way disagreement, and both directions are closed here.

### 18.2 Q1: the rows are dead, and dead data still has an owner

Measured, not assumed, on this tree:

- `tools/scene_palette_set.py` `allowed_sprite_rows()` returns the four `HERO_PALETTES` triples for a scene in
  `PARTY_CAST_SCENES`, and `scene()` and `allowed_sprite_sets()` both go through it, so every reader that draws or
  measures a `party_cast` strip spends the hero four and never the file's own rows.
- `scene_entries()` takes the backdrop, the four background rows and the hero four for such a scene.
- The rows are not spent on nothing: `validate()` unions background and sprite rows for the scene's 25 colour
  ceiling, so they are still declaration level data and a bad entry there fails the build.
- No GML reads `data/palettes/scene_battle_*.json` (the only GML mentions are two comments in `pp_config.gml` and
  `pp_title.gml`), so no runtime spends them either.

Dead or not, the two candidate sets were not equal in kind. The generator's four (`sp0` `$00 $10 $0F`, `sp1`
`$07 $17 $28`, `sp2` `$02 $12 $30`, `sp3` `$01 $11 $31`) were the corridor's boilerplate: `sp0`, `sp1` and `sp2`
byte equal to the corridor's own (`battle_corridor/sprites/sp0..sp2`), `sp3` zander's walking triple. The file's
four (`$00 $0F $10`, `$02 $0F $30`, `$07 $17 $36`, `$08 $27 $28`) are carried by exactly one row each in the twelve
sets, and they are the four entries card `t_cc0c5bd5` measured on 2026-10-24 to carry `sailor_battle.png`'s inks and
`navy_sailor.png`'s own triple.

**Ruling: the generator follows the file.** A regeneration must never replace a measured set with an unmeasured
default; that is the same defect class card `t_5802ecdb` closed for `judged`, and the direction of the fix is fixed
by which side holds a measurement. Adopting the generator's set would have deleted four triples that exist nowhere
else in the twelve sets and written the corridor's rows into a strip that has its own.

Two limits, written rather than implied:

- The rows name a cast ruling 12 retired from the sprite half, so nothing draws them today. They are kept because
  they are the only set ever measured for this strip's own four slots and because they cost nothing (14 colours
  across the deck set, ceiling 25). The strip's own note says exactly that, in the generator, so the next reader
  does not have to re-derive it.
- A deck that stops being `party_cast` (a pier fight is the case the quay's note already anticipates) **re-measures**
  these rows. It does not resurrect them, and it does not copy another strip's.

### 18.3 Q2: notes are the generator's whole list, so a note that must survive is a line in `SCENES`

`judged` is carried by key because it is a whole key that only a card writes, it sits in a position the file
chooses, and carrying it is one dictionary insertion. `notes` is different in every one of those respects: it is a
single list mixing four stock lines, the scene's own lines and a trailing stock line, so a carry rule would need a
marker that tells generator lines from hand lines, and every future hand edit would have to keep the marker honest.
That convention is more machinery than the two notes are worth.

So the notes list stays derived, whole, and the two notes that had to survive became generator content verbatim:

- the deck's `solved 2026-10-24 (card t_cc0c5bd5 ...)` note, with one clause added, because the cast it names has
  since been retired and a reader deserves the current fact: `since card t_0949bd4e this strip is party_cast, so
  these four rows are the declaration and not the spend ... a deck that stops being party_cast re-measures them
  rather than resurrects them (card t_8ebcb489)`;
- the quay's `NO cast and NO judged row, by gamedev ruling on card t_4f18c0ac ...` note, unchanged word for word.

The quay note moves up one line, because the writer emits the stock sprite note last and always has. That is a
position inside a JSON array, no palette entry moved, and it buys the property this card exists for: the committed
file is what the generator writes, byte for byte, so the next strip regeneration cannot lose the ruling again.

### 18.4 What landed, and what moved

- `tools/art/make_battle_bg.py`: the deck's `sprites` table is the four rows the file carries, with a comment saying
  so; the deck's scene notes gained the 2026-10-24 solve note (plus the `party_cast` clause); the quay's scene notes
  gained the ruling note; the module docstring's point 7 states the notes policy and the reason `judged` is
  different.
- `data/palettes/scene_battle_deck_night.json`: 2 lines (the bg2 note inserted, the solve note amended). The four
  sprite rows did not move because they were already right.
- `data/palettes/scene_battle_quay_dusk.json`: 2 lines (the ruling note reordered ahead of the stock sprite note,
  and the comma that goes with it).
- `game/sprites_src/bg/bg_battle_deck_night.json`: the deck sidecar's `sprite_palettes` now carry the file's four
  rows. They had carried the generator's boilerplate since 2026-10-24, so the sidecar was consistent with the code
  and inconsistent with the palette file, which is the same two owners defect in a third file.
- `data/scene_palettes.json` does not move and is not in this commit: the derived entry reads the background and
  sprite NUMBERS, and neither changed (measured by running `scene_from_source()` over HEAD's file and this one for
  all four battle scenes: equal).
- No strip pixel moved: the four PNGs hash to the same sha256 before and after
  (`0d103668...` corridor, `0512e531...` deck, `0ea86642...` quay, `2b6b4208...` wardroom).

### 18.5 What this does not decide

- **The deck's and the quay's party block floors.** Card `t_12c9b18f` owns both, and its acceptance now holds: a
  regeneration moves 0 palette lines before it starts.
- **Whether a `party_cast` strip should carry the hero four in its own `sprites` list.** That is the honest end
  state (the file would then say what the strip spends), and it is a four file change with its own measurements, so
  it is not smuggled in here. Named.
- **No carry rule for any other key.** `notes` is not carried, `judged` is, and a future hand written block in one of
  these files is expected to become a `SCENES` line or a `judged` row rather than an edit to the output.

**Checks run on this tree, 2026-10-25, and what they returned.**

- The card's own evidence command, re-run after the change: `python tools/art/make_battle_bg.py --root <scratch>`
  over a copy of `data/nes_palette.json`, `data/ui_layouts.json` and `data/palettes/`, then
  `diff --strip-trailing-cr` each regenerated palette file against the committed one: **0 lines, all four**. The
  four regenerated PNGs are byte identical to the committed ones (`cmp` clean).
- `python -m pytest tests/test_make_battle_bg.py -q`: 17 passed (13 before, plus four new pins: the deck's declared
  rows are the file's, every committed palette file reproduces byte for byte, a hand added note does not survive,
  and the two ruling notes are generator content).
- `python -m pytest tests/test_make_battle_bg.py tests/test_scene_palette_set.py tests/test_scene_palettes.py
  tests/test_palette_synergy.py tests/test_battle_draw.py tests/test_nes_audit_all.py -q`: 113 passed.
- `python tools/scene_palette_set.py validate`: PASS, 12 scene(s), 4 hero palette(s).
- `python tools/check_scene_palettes.py`: PASS.
- `python tools/palette_synergy.py --gate`: 9 entry(ies), 0 gated failure(s), 6 advisory failure(s), exit 0, the
  same shape as HEAD because no palette number moved.

Provenance for section 18: studied this repository's own files only (`tools/art/make_battle_bg.py`,
`tools/scene_palette_set.py`, `tools/palette_synergy.py`, `tools/check_scene_palettes.py`,
`data/palettes/scene_battle_*.json`, `data/scene_palettes.json`, `data/nes_palette.json`, `data/ui_layouts.json`,
the four strips and their sidecars, `game/scripts/pp_battle_director/pp_battle_director.gml`, and the 2026-10-24 and
2026-10-25 ruling files plus the commits `157f11a`, `e53a160`, `0b5dd01`). No decompiled material, and no
expression from another game, is in this card. Copied expression: none.

## 19. Q1, Q2 and Q3 on `sailor_battle.png`: it is not the fight's art, no ground in this project can carry it, and it is retired from both lists (card t_0b9c2faf)

**Answer, all three.** Q1: the sheet is retired, and neither of the card's two options is what happened. It is not
the sailor fight's battle art, because that art exists and is `game/sprites_src/enemies/navy_sailor.png`, drawn
untinted as background art in the battle screen's own 32x32 enemy slot; and `navy_sailor.png` did not replace it,
because the two were drawn for two different slots and neither slot has ever named this sheet. The honest sentence
is shorter than either option: **`sailor_battle.png` is the fifth character sheet of the sprite pipeline, built for
a 24x32 party column that has exactly four slots and four names, and no encounter, no layout slot and no draw call
in any commit has ever asked for it.** Q2: it is judged on no row, and no row could be found for it, because a
24x32 slot on a battle strip holds one figure in one sprite palette and this sheet is not one palette in any of its
seven frames, while as background art the best strip in the project carries 21 of its 72 inked 8x8 tiles. Q3: the
judge's list is right and the pool's was a 2026-10-22 leftover; `tools/art/scene_palette.py` now carries the judge's
five names, `tools/check_scene_palettes.py` says in words that the sheet is retired, and
`tools/art/make_characters.py` stops writing it.

### 19.1 What the sheet is, measured on this tree, 2026-10-25

| sheet | size | frames | opaque px | entries |
| --- | --- | --- | --- | --- |
| `chars/sailor_battle.png` | 168x32 | 7 of 24x32, 8 fps | 2398 | 10: `$00 $02 $07 $08 $0F $10 $17 $27 $30 $36` |
| `chars/hadrian_battle.png` | 168x32 | 7 of 24x32, 8 fps | 2424 | 3: `$03 $0F $23` |
| `chars/percy_battle.png` | 168x32 | 7 of 24x32, 8 fps | 2819 | 3: `$0F $12 $28` |
| `chars/zander_battle.png` | 168x32 | 7 of 24x32, 8 fps | 2425 | 3: `$0F $21 $31` |
| `chars/konrad_battle.png` | 168x32 | 7 of 24x32, 8 fps | 2472 | 3: `$00 $0F $27` |
| `enemies/navy_sailor.png` | 96x32 | 3 of 32x32, 8 fps | 1002 | 3: `$02 $0F $30` |

Where it came from: `tools/art/make_characters.py` `character_specs()` is a five entry cast list (`percy`, `hadrian`,
`zander`, `konrad`, `sailor`), and `build()` writes an `_ow` sheet and a `_battle` sheet for every entry. The four
heroes are in `PARTY_TRIPLES` and get one reserved triple each; the sailor is not, so he went through
`solve_tiles()` like a 2026-10-22 character and came out at ten entries. That is the whole of the sheet's identity.
Last pixel change: commit `e29612f` on 2026-10-22 08:24 (SPRITE-REDRAW-1). `navy_sailor.png` first tracked in
`10e0b00` the same morning at 08:34, written by `tools/art/make_enemies.py`. **There was no 2026-10-21 retirement
event**, and the card's guess of one is the one part of its premise the history does not carry.

### 19.2 Q1: the fight's enemy is `navy_sailor.png`, and this sheet has never had a draw call

1. **The slot it would need is 32x32 and it reads a different folder.** `data/ui_layouts.json` screen `battle`
   declares its two enemy slots as `32x32` px at tile (3,8) and tile (12,11). `pp_battle_enemy_slot()` resolves the
   first one, and `pp_battle_draw_enemy()` asks the art index for the enemy's **id** (`pp_battle_enemy_sprite`), which
   `tools/sync_art.py` mirrors out of `game/sprites_src/enemies/`. The tutorial encounter is
   `data/encounters/all.json` `tutorial_sailors` with `"enemies": ["navy_sailor"]`, and `data/enemies/roster.json`
   gives `navy_sailor` the sheet `game/sprites_src/enemies/navy_sailor.png`. A 24 px wide sheet under a 32 px slot
   from a folder the resolver never reads is not a candidate; it is a different animal.
2. **No GML file has ever named it.** `git log --all -S sailor_battle -- game/scripts` returns no commit. Every
   reference to the string in this repository is a tool, a palette note, a queue row about a different asset, or the
   cleanroom record. Nothing in the game has ever asked for it, so there is no draw call to name, and the card's
   request to name one is answered with that: none exists, and none ever did.
3. **It ships anyway.** It is an entry in `game/datafiles/art/title_manifest.json` (the `chars` mirror reads the
   whole folder) and an `IncludedFile` at `game/PrimordialParadox.yyp` line 522. That is the only thing the game ever
   did with it: carry 5376 px of art it never reads. Section 19.6 says why this card does not remove that.
4. **So the two options in Q1 are both wrong in the same direction.** `navy_sailor.png` was not a replacement, it
   was always the enemy: it is painted in exactly three entries (`$02 $0F $30`), which is what ruling 7.5 and card
   `t_34b1d96a` require of a figure drawn as background art, and its 32x32 frame matches the slot. The party column
   is the only place a 24x32 sheet can stand, its four slots are named in `data/ui_layouts.json` (KONRAD, ZANDER,
   PERCY, HADRIAN), and `data/characters/party.json` has never had a fifth member.

### 19.3 Q2: it is judged nowhere, and the measurement says no row in this project can hold it

**No sprite row can carry a frame of it.** The PPU has four sprite palettes and a party slot is one figure in one
of them (ruling 7, card `t_8c27208b`), which is why every party battle sheet is exactly one triple in every frame.
Measured per frame, using the project's own `load_master()` table: `sailor_battle` carries 7, 5, 7, 7, 8, 7 and 4
entries across its seven frames, so the fewest sprite triples that carry a frame is **2** (frames 1 and 6) or **3**
(every other frame), ten across the sheet, against **1** for each of the four hero sheets. It cannot be a party
figure at any ground, at any placement, in any row.

**No background triple can carry it either.** As background art the figure stands on the strip and each inked 8x8
tile of it has to fit ONE of that strip's four background triples plus the shared backdrop (ruling 7.5, section 12).
Swept over all twelve scenes in `data/scene_palettes.json`, the number of its 72 inked 8x8 tiles that some triple of
that strip carries whole:

| strip | carried | of 72 inked | uncovered |
| --- | --- | --- | --- |
| `battle_wardroom` | 21 | 72 | 51 |
| `battle_deck_night` | 20 | 72 | 52 |
| `battle_corridor` | 2 | 72 | 70 |
| `battle_quay_dusk` | 2 | 72 | 70 |
| `ship` | 3 | 72 | 69 |
| `title` | 0 | 72 | 72 |

Priced against the deck, the best the project has: the entries it needs and `bg2` (`$00 $30 $02`, or `$02 $0F $30`
plus the `$0F` backdrop) does not have are `$07 $08 $17 $27 $36`, which is section 15.5's list and section 15.5's
count, and this sweep agrees with it from the other end. Carrying it would cost three more background entries on a
strip whose enemy slots are already spent, for a figure the room does not draw.

**And the two DO NOTs are both held by measurement.** A walking room's row: the ship's four walking rows read
`FAIL, 53 failing pairs` and 40 of 72 inked tiles uncovered on it, and `enforce_sprites()` would rewrite 621 of its
2398 opaque pixels (measured this card, and unchanged from section 17.4). A fifth sprite palette: does not exist
(ruling 7.1), and it would not help, because the sheet needs three.

So Q2's answer is the card's own second branch: **it is not drawn, so it is retired from the budget instead of judged
on a ground it never stands on.** The ship's row already stopped carrying it on card `t_a6a7a436` (40 of its 72 inked
tiles fit no row under the party's four walking triples, against 0 of 72 under the old rows). Nothing replaces that
absence: the count of rows it is judged on is zero, and this card keeps it zero on purpose.

### 19.4 Q3: one list, and it is the judge's

At HEAD before this card the two constants named different casts:

| file | constant | what it drove |
| --- | --- | --- |
| `tools/art/scene_palette.py:824` | `SHIP_SPRITES = ["sailor_ow", "sailor_battle"]` | the ship solve's sprite pool, AND the `enforce_sprites()` pass in `apply_ship()` that WRITES pixels |
| `tools/check_scene_palettes.py:56` | `SHIP_SPRITES = ("hadrian_ow_v2", "konrad_ow_v2", "zander_ow_v2", "percy_ow_v2", "sailor_ow_v2")` | what the suite measures against the ship's four rows |

The judge's list is right: it is the cast the three ship rooms actually draw (the party's four walking sheets plus
the sailor actor, `pp_overworld` `pp_hero_sheet` and `pp_sailor_sheet`), and it is the same five names
`data/palettes/scene_ship.json` judged row carries. The pool's list was the 2026-10-22 cast, and it still carried the
enforcement pass, which is not a dead line: `apply --scene ship` would have repainted 621 pixels of a sheet no room
draws. The pin card `t_a6a7a436` added to `write_scene()` protects the palette FILE, not the pixels on disk.

So the pool now IS the judge's five, in the judge's order, and both files say the retirement in words so that the
next worker reading either one cannot put the sheet back. The pool change moves no palette row, because the ship's
sprite half is pinned (`sprites_pinned: true`) and `solve --scene ship --write` keeps it; what it does change is what
the enforce pass touches, which is the point.

`tools/art/make_characters.py` is the third place, and the one that would put the file back. It is now:

- `BATTLE_RETIRED = {"sailor"}` and `writes_battle_sheet(name)`, consulted by `build()` before it draws or writes a
  battle sheet, so a regeneration leaves the retired sheet alone instead of rewriting it through `solve_tiles()`.
- the four heroes are untouched: they are still in `PARTY_TRIPLES` and still get their one triple each.
- the committed PNG and its sidecar stay on disk byte for byte. A generator that stops writing a file is not the same
  as deleting art, and deleting it is section 19.6's paragraph.

### 19.5 What landed, measured before and after

**Landed.**

- `tools/art/scene_palette.py`: `SHIP_SPRITES` is the judge's five walking sheets, with the retirement and the numbers
  above written beside it.
- `tools/check_scene_palettes.py`: the list is unchanged (it was right) and its comment now records the verdict
  instead of deferring to this card.
- `tools/art/make_characters.py`: `BATTLE_RETIRED`, `writes_battle_sheet()`, and a `build()` that writes a battle
  sheet only for a character who has a slot.
- `tests/test_scene_palettes.py`: two new tests. One holds the pool, the judge and the judged row to the same five
  names and holds `sailor_battle` and `sailor_ow` out of all three. The other holds the retirement three ways: the
  generator refuses to write it, no scene file in `data/scene_palettes.json` names it on any row and no `.gml` under
  `game/scripts` names it at all, and the shape argument is measured rather than asserted (every party battle frame
  is exactly one triple, no frame of this sheet is).
- No palette number, no strip pixel and no sheet pixel moved: `data/palettes/scene_ship.json`,
  `data/scene_palettes.json`, the four strips, the four hero sheets and `sailor_battle.png` are byte identical.

**Checks run on this tree, 2026-10-25, and what they returned.**

- `python tools/art/scene_palette.py apply --scene ship --root <scratch>` over a scratch root carrying
  `data/nes_palette.json`, `data/palettes/scene_ship.json`, `ts_ship.png` and every chars sheet: **exit 0, 0 pixels
  moved** on the tileset and on all five walking sheets, and `sailor_battle.png` byte identical afterwards
  (`2400b4ff8b23` before and after). Under the old pool the same command reported **621 pixels moved** on it.
- `python tools/art/scene_palette.py solve --scene ship`: keeps the pinned sprite half and the 2 judged rows, prints
  the four rows the file carries, exit 0.
- `python tools/check_scene_palettes.py`: PASS, both scenes inside their declared palettes, five ship sprites.
- `python tools/scene_palette_set.py validate`: PASS, 12 scenes, 4 hero palettes.
- `python tools/palette_synergy.py --gate`: 9 entries, 0 gated, 6 advisory, exit 0, unchanged.
- `python -m pytest tests/test_scene_palettes.py`: 7 passed (5 before, plus these 2).
- Whole suite: see the DEVLOG entry for this card.

### 19.6 What this does not decide

- **The file itself, and the build's Included File entry.** `game/sprites_src/chars/sailor_battle.png` stays on disk
  and stays listed in `game/PrimordialParadox.yyp` in this section's own commit. Removing it drops one art index entry
  (117 to 116), one Included File (276 data files to 275) and 5376 px of shipped art, and it can only be proven by a
  build. GameMaker was believed absent on this machine when this was written, so a card that does it has to land with a
  build, not before one. Named, not smuggled in. **Card `t_4848159e` did it, see 19.7.**
- **`sailor_ow` (v1).** It is out of the pool by this card because it is not the sheet the room draws
  (`pp_overworld` draws `sailor_ow_v2`), and it costs nothing to leave out: it carries two entries, so the enforce
  pass moved 0 pixels of it before and does not open it now. But `make_characters.py` still writes it and still runs
  an `enforce_sprites()` pass over it, and the same is true of every other `_ow` sheet the v1 generator writes. The
  v1 walking set is a separate dead set with its own provenance and its own card.
- **Any other scene's pool.** Only the ship's two constants are reconciled here. No other scene file carries a
  solve pool of its own.
- **No strip's background spend.** This card buys no colour for anything: the deck's `bg2` stays `$00 $30 $02`, which
  is what its own enemy stands on and what card `t_34b1d96a` paid for, and the sheet that needed `$07 $08 $17 $27 $36`
  is not drawn, so it is not paid.

Provenance for section 19: studied this repository's own files only
(`tools/art/scene_palette.py`, `tools/check_scene_palettes.py`, `tools/art/make_characters.py`,
`tools/art/make_enemies.py`, `tools/sync_art.py`, `tools/palette_synergy.py`, `tools/scene_palette_set.py`,
`data/ui_layouts.json`, `data/encounters/all.json`, `data/enemies/roster.json`, `data/characters/party.json`,
`data/nes_palette.json`, `data/scene_palettes.json`, `data/palettes/scene_ship.json`,
`game/scripts/pp_battle_director/pp_battle_director.gml`, `game/scripts/pp_overworld/pp_overworld.gml`,
`game/PrimordialParadox.yyp`, the five `_battle` sheets, the seven `_ow` sheets and `navy_sailor.png`, and the commit
history of all of them). No decompiled material was read for this card and no expression from any game is in it.
Copied expression: none.

## 20. The towns' spawning street moves off the light group: the party walks in white, the paving was $10, and no light entry can carry them (card t_454c1876)

The card arrived with three failing rows, one per town, all three measured against the frame the map generator composes at
that town's spawn: southampton 36 failing pairs, westminster 88, winchester 32, 156 in all. Every one of them was the street
against the sheets' own bodies, and every one of them was a light ground. This section answers the three questions the card
asked, Q1 what the ground under the party is, Q2 which entries each of the party's bodies clears, Q3 whether the ground or
the sprite moves, and records the one ruling that came out of them: **the walkable ground is the thing that moves, because a
white body is the thing that cannot.**

### 20.1 The four lines that decide the question, and the four bodies they judge

All four are read from `tools/palette_synergy.py`, not restated: `NEAR_WHITE = 0.60` (line 109), `LIGHT_GROUND = 0.25`
(line 110), `ROW_GAP_MIN = 2` (line 108), `FIGURE_GROUND_CONTRAST_MIN = 3.0` (line 129). A pair fails as

- **white_blob** when the body is 0.60 or more AND the ground is 0.25 or more;
- **body_ground** when the two are fewer than 2 rows apart AND under 3.0:1;
- **same_hue_row** when body and ground are one hue family on one row;
- **invisible** when they are the same entry.

Luminance and row come from `tools/art/contrast_check.py`'s 2C02 table through `Grid`:

| entry | hex | luminance | row | hue | who wears it as a body |
| --- | --- | --- | --- | --- | --- |
| `$30` | `#fcfcfc` | 0.973 | 3 | grey | `percy_ow_v2`, `hadrian_ow_v2` |
| `$31` | `#a4e4fc` | 0.704 | 3 | hue_1 | `zander_ow_v2` |
| `$28` | `#f8b800` | 0.542 | 2 | hue_8 | `konrad_ow_v2` |
| `$10` | `#bcbcbc` | 0.503 | 1 | grey | the paving, before this card |
| `$00` | `#7c7c7c` | 0.202 | 0 | grey | the asphalt and the kerbstone |
| `$0F` | `#000000` | 0.000 | 0 | grey | the shared backdrop |

Two of the four party bodies are at or above `NEAR_WHITE` on the tool's own reading (`$30` 0.973, `$31` 0.704); `$28` at
0.542 is not, and fails by the row gap instead. The street's `$10` at 0.503 is nearly twice `LIGHT_GROUND`. So the street and
the party cannot both keep what they had.

### 20.2 Q2 first, because it settles Q1 and Q3: which ground can carry each body

`pair_rules` called for every body the party walks in, against every entry a town ground draws, is the whole answer:

| body | paving `$10` | white `$30` | stone `$00` | black `$0F` | grass `$2A` |
| --- | --- | --- | --- | --- | --- |
| `$30` percy, hadrian | white_blob | invisible, white_blob | **PASS** | **PASS** | body_ground, white_blob |
| `$31` zander | white_blob | body_ground, white_blob | **PASS** (3.00:1) | **PASS** | body_ground, white_blob |
| `$28` konrad | body_ground | body_ground | **PASS** (2 rows) | **PASS** | body_ground |
| `$00` hadrian, before | body_ground | PASS | invisible | same_hue_row | PASS |

Read the last row carefully, because it is the reason the sprite could not be the thing that moved: a `$00` grey body
clears exactly two of the five grounds in that table, `$30` white and `$2A` grass, and neither is a ground a town lets the
party stand on. `$30` is the cathedral and tower stone, which is solid; grass is the park, which is carded separately
(section 20.8). Against the street it is `invisible` on the asphalt (the same entry) and `same_hue_row` on a black joint.

Every other row of that table says the same thing from the other side: **`$00` and `$0F` are the only two entries a street
can be made of that all four walking bodies clear.** `$00` passes all four, `$0F` passes all four, and every light entry
fails at least three of them.

### 20.3 Q1: what the ground under the party actually was

The three spawn boxes were light pavement and nothing else that mattered. At the tile level, before and after, counted
pixel by pixel out of `game/sprites_src/env/ts_exterior.png` (HEAD against this card's working tree; `3F` is the 2C02 byte
that carries the same `#000000` as the row's `$0F`):

| tile | walkable | before (HEAD) | after |
| --- | --- | --- | --- |
| `pavement_a` | yes | `$10` 256 | `$00` 196, black 60 |
| `pavement_b` | yes | `$10` 256 | `$00` 169, black 87 |
| `pavement_grate` | yes | `$00` 56, `$10` 176, black 24 | `$00` 157, black 99 |
| `kerb_w`, `kerb_e` | yes | `$00` 118, `$10` 80, `$30` 42, black 16 | `$00` 192, black 64 |
| `road_b` | yes | `$00` 230, `$10` 6, black 20 | `$00` 230, black 26 |
| `road_line` | yes | `$00` 220, `$30` 20, black 16 | `$00` 220, black 36 |
| `road_line_h` | yes | `$00` 215, `$10` 3, `$30` 20, black 18 | `$00` 215, black 41 |
| `crosswalk` | yes | `$00` 128, `$30` 128 | `$00` 128, black 128 |
| `gutter` | yes | `$00` 136, `$10` 64, black 56 | `$00` 144, black 112 |
| `cobble_a` | yes | `$00` 146, `$10` 110 | `$00` 110, black 146 |
| `cobble_b` | yes | `$00` 171, `$10` 85 | `$00` 85, black 171 |
| `cobble_c` | yes | `$00` 139, `$10` 117 | `$00` 117, black 139 |
| `quay_stone` | yes | `$00` 74, `$10` 182 | `$00` 182, black 74 |
| `quay_flag` | yes | `$00` 135, `$10` 121 | `$00` 121, black 135 |
| `road_a` | yes | `$00` 240, black 16 | unchanged |
| `grass_a`, `grass_b`, `grass_c` | yes | `$09`, `$0A`, `$2A` | unchanged, carded |
| `blank` | yes | black 256 | unchanged |

Two details the table makes plain and the earlier notes did not. `pavement_a` and `pavement_b` were a **flat field of one
entry**: their slab rectangles covered all 16x16, so the `M` under them never showed and Winchester's spawn tile had a box
of 256 pixels of `$10` with no joint in it at all. And the kerb spent **all three** of `bg0_stone`'s entries on an edge the
party stands on: Westminster's spawn is `kerb_w` at tile 16,20.

### 20.4 The ruling: `$10` and `$30` become architecture, and the street is drawn in `$00` and the backdrop

`bg0_stone` keeps its three entries. Nothing about the palette row moves; what moves is **which of the three a walkable tile
may spend**. `M` `$00` and the shared backdrop `$0F` are the walkable band. `L` `$10` and `W` `$30` are architecture only and
stay exactly where they are on roofs, tower and cathedral stone, benches, railings, lamps, the phone box, the sign and the
awning. The street is now:

- asphalt in `$00` with black wear and a **black** centre line (`$00` against `$0F` reads 5.03:1; the line was `$30` on `$00`
  and that is a light ground a party walks on);
- flagstones in `$00` with a one pixel black joint, which also gives `pavement_a` and `pavement_b` their texture back;
- cobbles and quay flags in `$00` with black between the stones (they used to be `$00` gaps with `$10` stones, i.e. the same
  two entries with the light one on the majority of the tile);
- a kerb of grey stone with a black gutter on the road side and a black shadow line, three tones down to two;
- and the crossing bars in black rather than white.

The generator's header now carries the numbers and the reason, and the `FEATURES` key it writes into
`game/sprites_src/env/ts_exterior.json` reads **"road with centre line"** instead of "road with white line", because the
marking is no longer white and a key that says white about black art is a lie in a committed file.
`tools/check_ts_exterior.py`'s `CARD_FEATURES` moved with it, since that list is where the string is asserted.

### 20.5 Hadrian moves with the street, and the palette row does not

Hadrian's walking sheet is the one sprite that could not simply be left alone. `hadrian_ow_v2` was drawn with `$00` grey as
the suit and `$30` pale as the accent (`tools/art/make_characters_v2.py`, card t_bd32a72e's redraw), so his measured body
was `$00`, and section 20.2's last row is the verdict on that body: it clears no street the party can walk on. His frames
were therefore reporting `invisible` and `same_hue_row` against the very ground he walks on.

The fix is an accent swap inside `sp0`, not a new row: ink stays the outline, seams and sleek hair; **pale `$30` becomes the
suit** (24 and 40 pixels of the largest fill in the two frames where the arms cover the shirt, so the body is pale in all
eight frames); **grey `$00` returns as the shaded rim** the `rim` part already draws on the shoulders and sleeves (8 pixels).
The sheet still spends all three of `sp0`'s entries, `$00 $0F $30`, so `tests/test_scene_palette_set.py`'s "each sheet's own
colours are exactly its row" still holds, and RULE 0 point 3 still gets an outline, a body and a third tone. The row itself
is untouched: `sp0` is `$00 $0F $30` before and after, and no scene palette file moves.

I tried the two tone version first (grey dropped entirely) and reverted it: it satisfies the pair rules and fails the art
bible, which asks a walking sheet for three tones, and it also failed that same row test honestly. A pale suit with a mid
grey edge is also what the rim was written for; it used to light a black suit's edge and now it shades a white one's.

### 20.6 What landed, measured before and after

**Landed.**

- `tools/art/make_ts_exterior.py`: the fourteen walkable street tiles above, the header note with the measured numbers, and
  the `FEATURES` key rename.
- `tools/art/make_characters_v2.py`: hadrian's `palette` entry, with the record of card t_bd32a72e's redraw kept as written
  and this card's ruling appended beside it.
- `tools/check_ts_exterior.py`: **check 13**, "every tile a player can walk on draws only entries under 0.25 luminance",
  with a named exemption list whose only members are `grass_a`, `grass_b` and `grass_c`, each carrying the card that ends
  the exemption (`t_b01c88ff`). The check reads the sheet pixel by pixel and names the tile and entry that breaks it. This is
  the durable half of the card: the street cannot drift back, and neither can any future walkable tile.
- `game/sprites_src/env/ts_exterior.png` and `.json`, `game/sprites_src/chars/hadrian_ow_v2.png`, all regenerated by their
  own generators.
- `output/southampton_sample_frame.png`, `output/westminster_sample_frame.png`, `output/winchester_sample_frame.png`: the
  three grounds, regenerated by `tools/art/make_exterior_maps.py`. The sweep measures these pixels, so a commit that moved
  the tileset and left the frames behind would report the same 156 failures again on a clean checkout.
- `output/ts2_world_preview.png`: the tileset preview, written by `tools/art/make_ts_exterior.py`.
- `data/scene_palettes.json`: three lines, the three judged notes, so the committed payload matches the scene files it is
  built from.
- `data/palettes/scene_southampton.json`, `scene_westminster.json`, `scene_winchester.json`: the judged note in each one
  gains a dated closing sentence. The measurement that was there is kept, not overwritten.
- `knowledge/DEVLOG.md`: one entry, newest first.

**Measured.**

- The three town rows: southampton 36, westminster 88, winchester 32 failing pairs, **0, 0, 0** after. Per sheet per town:
  percy body `$30`, konrad `$28`, zander `$31`, hadrian `$30`, every one of them on ground `$00,$0F`, 0 failing pairs and
  0 cast problems.
- `python tools/palette_synergy.py --gate`: 9 entries, 0 gated, **6 advisory failing and 549 problems** before; 9 entries,
  0 gated, **3 advisory and 383 problems** after. The 166 that left are the 156 town pairs plus the character contact
  sheet's 16 problems falling to 6, which is a by-product no card judges (the sheet is regenerated by two generators, and
  hadrian's pale suit moves it). Per entry now: 0, 6, 0, 0, 242, 0, 135, 0, 0.
- `python tools/check_ts_exterior.py`: 61 checks passed, 0 failed, with check 13 PASS over **all 20 walkable tiles** and 3
  exemptions printed.
- `python tools/scene_palette_set.py validate`: PASS, 12 scenes, 4 hero palettes.
- `build --write` run in a **clean worktree of HEAD** (`git worktree add --detach HEAD`, 71f168d) with exactly this card's
  files applied changes `data/scene_palettes.json` by three lines: the three judged notes, and nothing else. No scene
  palette number moves, no row moves, no colour is bought. That file is in this commit for those three lines only.
- **The clean worktree suite**: `<home>/AppData/Local/Python/bin/python.exe -m pytest -q -p no:cacheprovider tests`
  in that worktree, after `tools/sync_data.py` and `tools/sync_art.py --no-project`, is **1622 passed, 0 failed, 479
  warnings in 270.74s**.
- **The shared working tree cannot run the gate at all, and that is not this card.** Three tests fail in it,
  `test_make_env_ship.py::test_every_colour_on_the_sheet_is_one_of_the_ten_declared`,
  `test_make_env_ship.py::test_the_committed_outputs_are_what_the_script_writes_today` and
  `test_scene_palette_set.py::test_build_reproduces_the_file_on_disk`, because `data/palettes/scene_ship.json` is being
  edited and not committed by the ship lane (its `bg1` and `bg2` rows are swapped). Measured rather than assumed:
  `make_env_ship.build()` into an isolated root carrying that palette file **at HEAD** reproduces the committed
  `game/sprites_src/env/ts_ship.png` exactly, sha256 `2d2130393454...604d37bbbe`, so the committed art is right and the
  fresh build under the uncommitted rows is what differs. The commit therefore went in on a private index with the clean
  worktree as its gate evidence and a BYPASS entry in `guard/gate-log/2026-10-25.md`, the same arrangement card t_12c9b18f
  used two commits before this one. The hook's own FAIL entry for the attempt it refused is in that log too, unedited.
- `output/scene_palettes.json` is **not** in this commit, and that was measured too: regenerating it with hadrian's sheet
  put back to HEAD's bytes still differs from the committed copy by 58 insertions and 25 deletions, all of them in the
  ship's reported sprite rows. It was already stale at HEAD for another lane's reason and card **t_8690e219** closes it;

### 20.7 Q3, and the option that was refused

The card offered three ways out: move the ground, move the sprite, or buy a second walking triple for the party. The third
is closed by the hardware and by two earlier rulings. A scene spends **four** sprite palettes, all four are the party
(section 16.6), and the towns' four rows are `sp0 $00 $0F $30`, `sp1 $07 $17 $28`, `sp2 $01 $11 $31`, `sp3 $02 $12 $30`
because each walking sheet's own colours fit exactly one of them (section 16, card t_dec4e92c). There is no fifth row to
darken, and the same four rows are the ship's walking rows in a solve that is in flight on another lane (section 17,
t_a6a7a436). Moving any row would reopen a solve that two cards just closed, to buy a colour the party has no room for.

Moving the sprite was the option that looked cheapest and is the one that fails measurement: the party is **deliberately**
white. Its bodies are pale or gold because these are the same four heroes drawn on a night deck, a black title and a dark
corridor, and their near white bodies are what makes them read there. If the street stayed light, the honest fix would be to
repaint four hero sheets once for the asphalt and once for the paving, and that is precisely the extra palette per hero the
project has already ruled it cannot afford.

So the ground moved, and the ground is the part of a town the project has thousands of tiles of and can restyle without
touching a single character.

### 20.8 What this does not decide, and the hazards it names

- **The park is still light, and it is still walkable.** `grass_a`, `grass_b` and `grass_c` draw `$2A #58d854` at 0.518,
  which is a light ground by the same 0.25 line: `$30` on it is `body_ground, white_blob`, `$31` and `$28` are
  `body_ground`. The three tiles are what `make_exterior_maps.py` paints OSM park cells with, so the party can walk into the
  park in all three towns. Card **t_b01c88ff** closes it and owns the exemption check 13 carries.
- **The street is now one tone plus the backdrop.** That is a real art consequence of a white party on a NES: it reads as a
  dark street with the buildings providing the light, which is how these three towns already read under their black
  backdrop, but nobody has looked at it. A screenshot card is the honest next step, and this section deliberately does not
  claim the street looks better, only that it measures clean.
- **No frame was captured on hardware and no build was run.** GameMaker is not installed on this machine, so these are
  palette and pixel measurements through the project's own tools, not the PPU. `tools/nes_composite_check.py` is run over
  the three frames by check 12 and passed; nothing here claims more than that.
- **The character contact sheet** (`output/sprites_v2_sheet.png`) is a by-product two generators write, and hadrian's two
  tone attempt showed it moving with any sheet change. Its 6 remaining problems are advisory and no card judges it.
- **`output/scene_palettes.json` is stale at HEAD** and this card leaves it alone: card **t_8690e219**.
- **Any other scene's ground.** Only the three towns' street group is reconciled here. The ship's deck, the corridor and the
  battle strips are other groups with their own cards.

Provenance for section 20: studied this repository's own files only (`tools/palette_synergy.py`,
`tools/check_ts_exterior.py`, `tools/art/make_ts_exterior.py`, `tools/art/make_characters_v2.py`,
`tools/art/make_exterior_maps.py`, `tools/art/contrast_check.py`, `tools/scene_palette_set.py`, `knowledge/ART-BIBLE.md`,
`knowledge/PALETTE-SYNERGY.md`, `data/nes_palette.json`, `data/palettes/scene_southampton.json`,
`scene_westminster.json`, `scene_winchester.json`, `game/sprites_src/env/ts_exterior.json`, the tileset and the four
walking sheets, and the commit history of all of them). No decompiled material was read for this card and no expression
from any game is in it. Copied expression: none.

# Card `t_23b5739a`: the ship's four background rows, and what stops a solve from moving them

## 21. Q1, Q2 and Q3 on the ship's background rows: the sheet keeps the rows it was painted into, because the solver's rows trade white foam for deep blue, and the half is now pinned (card `t_23b5739a`)

Carried over from card `t_92d59163`, which refused an uncommitted edit to `data/palettes/scene_ship.json` because the
rows are an INPUT to the pixels of `ts_ship.png`, and left the design question here with its numbers attached. Q1: do
the rows move to the solver's grouping or stay. Q2: if they move, how the sheet keeps ten colours. Q3: if they stay,
what stops the next solve from re-proposing them.

The answers are Q1 stay, Q2 not taken (and measured so the redraw card can take it), Q3 a key in the file that the
solver honours, not a convention.

### 21.1 The card's fact, re-measured, and one number corrected

`tools/art/scene_palette.py solve --scene ship` (report only since `cbb6ff4`) prints a different background half from
the one the file ships with, and the disagreement reproduces on this tree:

```
proposed: bg1 $07 $17 $30   bg2 $02 $12 $28        (bg0 $00 $10 $30 and bg3 $00 $02 $21 agree, sprite half agrees)
shipped : bg1 $12 $28 $30   bg2 $02 $07 $17
```

One correction. The card, and the note it came from, name the colour that leaves the sheet as `$2C #3cbcfc`. That
pairing is wrong, and `data/nes_palette.json` is the authority: `$21` is `#3cbcfc` (entry 33, the sheet's `c`, "sea
crest") and `$2C` is `#00e8d8`, which has never been on this sheet. Measured by listing the sheet's own colours
against the master table, the entry that leaves is `$21`. Every other number in the card reproduces exactly.

### 21.2 The measurement, refreshed on the tree this section lands on

Two builds of `tools/art/make_env_ship.py` into scratch roots seeded the way `tests/test_make_env_ship.py` seeds
them, one per row set, and the drawn sheet read without the scene palette pass for the third column:

| | shipped rows | solver's proposal |
| --- | --- | --- |
| rows | bg0 `$00 $10 $30`, bg1 `$12 $28 $30`, bg2 `$02 $07 $17`, bg3 `$00 $02 $21` | bg0 `$00 $10 $30`, bg1 `$07 $17 $30`, bg2 `$02 $12 $28`, bg3 `$00 $02 $21` |
| the built `ts_ship.png` | sha256 `2d213039345402edede01a670e0771c6315e1dd9d17d675abc0220604d37bbbe`, byte identical to the committed sheet | sha256 `82394a4367ec265ae19b591a74a1278068cf76ce42dfaa51a31d5589a32102ce` |
| pixels that differ from the committed sheet | 0 of 12288 | 151 of 12288 |
| tiles that differ | none | 6: `lifebuoy` 20 px, `water_a` 40, `water_b` 40, `water_edge` 22, `water_deep` 13, `water_foam` 16 |
| colours on the built sheet | the ten declared (`$0F $00 $10 $30 $02 $12 $17 $28 $07 $21`) | nine: `$21 #3cbcfc` leaves, nothing enters |
| pixels the rows repaint on the RAW drawn sheet | 762 of 12288 (6.20%) | 625 of 12288 (5.09%) |

Fourteen of the 48 tiles are assigned to a different row under the two sets; only six of them change pixels, because
the cargo family (`crate` 36 px, `crate_stack` 12, `barrel` 20, `table` 12) is drawn with brass `$28` that NEITHER set
can carry, so it loses the same pixels either way. The per tile difference is the whole of the proposal's gain:

| tile | row, shipped / proposal | raw pixels repainted, shipped / proposal | what the proposal keeps |
| --- | --- | --- | --- |
| `lifebuoy` (placed twice in `ship_sample_tiled.json`) | bg0 / bg1 | 16 / 4 | the ring's 16 rust `$17` pixels, which the shipped rows repaint to steel mid `$00` |
| `water_a` | bg1 / bg2 | 54 / 14 | 40 deep `$02` pixels |
| `water_b` | bg1 / bg2 | 54 / 14 | 40 deep `$02` pixels |
| `water_edge` | bg1 / bg2 | 66 / 44 | 22 deep `$02` pixels |
| `water_deep` | bg3 / bg2 | 10 / 3 | 10 mid `$12` pixels, at the cost of the 3 `$21` crest pixels it was the last home of |
| `water_foam` | bg1 / bg2 | 90 / 74 | 16 deep `$02` pixels |

`warning` (0 lost either way) and `bollard` (43 lost either way) also change row, to no pixel effect.

### 21.3 Q1: the rows stay. The solver is the closer fit to the drawing, and that is not the only thing a row has to be

The proposal is better on the metric that is not circular: it repaints 137 fewer of the artist's drawn pixels, it is
worse on no tile, and it fixes a real defect, because the lifebuoy is drawn orange and white and the shipped rows
render it grey. Three things keep the rows where they are.

**One, the water family it improves is a flat fill that no room draws.** On the committed sheet `water_a`, `water_b`,
`water_edge` and `water_foam` are 256 identical pixels of `$12` each; on the raw sheet they are `$12` with strips of
`$02` and `$21`, and every build repaints 149 of those crest pixels. `ship_sample_tiled.json` places no water tile at
all, and only `lifebuoy` out of the six is placed (twice). So 137 pixels of gain lands on art no map on this tree
draws, and 12 of them are the lifebuoy ring.

**Two, the proposal takes the only row the declared foam colour can live on.** The sheet's own table says `$30` is
"white paint: corridor lines, rim light, foam". The shipped rows put the water family on bg1 `$12 $28 $30`, where white
is itself; the proposal puts it on bg2 `$02 $12 $28`, where `nearest_in($30)` measured through the tool is `$28
#f8b800`. White foam on the ship would be repainted gold, and `$10` steel light goes the same way. The deep blue the
proposal keeps is a colour the water already loses today at the fill level; the white is the one the redraw is going
to want.

**Three, dropping the tenth colour is not a one sheet change.** `$21` is what `tools/art/make_ship_tiles.py` draws
the ship interior's terminal screen with (its `PALETTE` row `("c", 0x21, "#3cbcfc", "sea crest and the terminal's
screen")`), and `tests/test_make_ship_tiles.py` holds that sheet's palette as a SUBSET of this one. A nine colour ship
sheet therefore means redrawing a 96 tile interior sheet and its test, which is another sheet's card and another
sheet's art.

So the mismatch this card was handed is in the DRAWING, not in the rows: the cargo is drawn with brass the rows cannot
show, and the water with crest that no water row can show under either set (149 drawn pixels, of which 3 survive).
Both rows are orderings of the same trade, and the trade can only be settled by the redraw. The rows stay, and this
section hands the redraw both sides of it.

### 21.4 Q2: not taken, and the receipt a redraw card needs to take it

If a later card moves the rows it has to move the sheet in the same commit: `ts_ship.png` becomes sha256 `82394a43...`,
six tiles are repainted, and the ten colour budget has to be paid for by redrawing `lifebuoy`, `water_a`, `water_b`,
`water_edge`, `water_deep` and `water_foam` inside the new rows, or by dropping `$21` to nine colours, which takes
`tools/art/make_ship_tiles.py` and `tests/test_make_ship_tiles.py` with it. The numbers it needs are in 21.2, and the
`background_pinned` key documented below is the switch it removes to do it.

### 21.5 Q3: the pin, because a solver that is right keeps proposing

The report is not the problem; the write was, and `cbb6ff4` already gave the ship the `write=False` default the title
had. What was still open is a deliberate `solve --scene ship --write`, and the answer is the same mechanism the sprite
half already uses:

- `data/palettes/scene_ship.json` carries `"background_pinned": true` and a note with the numbers above.
- `tools/art/scene_palette.py` has `BACKGROUND_PINNED_KEY`; `write_scene()` keeps a pinned background half and its
  notes the way it keeps `sprites_pinned`, and prints what it kept. Removing the key is how a card that means to move
  the design does it.
- `write_scene()` no longer rewrites a file whose parsed payload is already what it would write, so a pinned `--write`
  leaves no layout only diff behind.
- `solve --scene ship` still prints the PROPOSAL and now says it is not applied and what the file's rows are, so the
  disagreement stays visible without being applied.
- `tests/test_scene_palettes.py::test_a_solve_keeps_a_pinned_background_half` holds it, with the control that the same
  call moves the rows once the key is gone. The sprite half's test seeds its scratch copy without the new key, with a
  comment saying why.

Measured at the command line, in a scratch root holding the master palette, the scene file, the sheet and the five
cast sheets:

```
before:        sha256 44b68bfa...  rows [[0,16,48],[18,40,48],[2,7,23],[0,2,33]]  pinned True
solve --scene ship --write
  scene_palette: scene_ship.json already holds these rows; nothing written
after:         sha256 44b68bfa...  rows unchanged                                     pinned True
(key removed, same command)
after control: sha256 0fdbecd4...  rows [[0,16,48],[7,23,48],[2,18,40],[0,2,33]]      pinned False
```

### 21.6 What landed, and what this does not decide

Landed on card `t_23b5739a`: the ruling above; `background_pinned: true` plus its note in
`data/palettes/scene_ship.json`; the key, the `write_scene()` handling, the unchanged-file guard, the honest report
and the pin plumbing in `tools/art/scene_palette.py`; the new test and the comment in the existing one; this section;
a DEVLOG entry and a PROVENANCE entry. No palette row, no pixel of `ts_ship.png`, no tile table and no map moved.

Green on this tree: `python -m pytest tests/test_make_env_ship.py tests/test_scene_palette_set.py
tests/test_scene_palettes.py -q` reads 53 passed, 0 failed; `python tools/check_scene_palettes.py --quiet` exits 0;
`python tools/scene_palette_set.py build` exits 0 and derives the same set.

Not decided here. Whether the ship's sea is deep `$02` or mid `$12` at the fill level; whether the cargo family should
carry brass `$28`; whether the budget should be nine. The lifebuoy stays grey in the one room that places it until the
redraw, and that is the cost this ruling accepts, on the record, with its 16 pixels measured. No GameMaker build and
no hardware capture back any of it; this is palette and pixel measurement through the project's own tools.

Two hazards. The sheet's water family is a flat fill named after things it does not draw (foam, edge, two frames),
which is what makes a 137 pixel row difference hard to judge and is the redraw's first job. And the background half
printed the same four rows on every run of this card, while the sprite half's row ORDER was seen once to come back
permuted in a scratch root (the same four rows in different slots); it was not chased, and nothing in this section
rests on the sprite half's order.

Provenance for section 21: studied this repository's own files only (`tools/art/scene_palette.py` at `7a73469` and at
HEAD, `tools/art/make_env_ship.py`, `tools/art/make_ship_tiles.py`, `tests/test_make_env_ship.py`,
`tests/test_scene_palettes.py`, `tests/test_scene_palette_set.py`, `tests/test_make_ship_tiles.py`,
`tools/scene_palette_set.py`, `tools/check_scene_palettes.py`, `tools/check_env_tiles.py`, `data/nes_palette.json`,
`data/palettes/scene_ship.json`, `game/sprites_src/env/ts_ship.png` and `ts_ship_tiled.json`,
`data/maps/ship_sample_tiled.json`, `knowledge/SHIP-PALETTE-DRIFT-2026-10-25.md`, and the commit history of all of
them). No decompiled material was read for this card and no expression from any game is in it. Copied expression:
none.

## 22. The park leaves the light group: the walkable grass was the last exemption check 13 carried, and the fix is in the tile rather than in the check (card t_b01c88ff)

Section 20.8 named this hole and carded it: the street under the party moved to the two dark entries, and the park stayed
light. This section closes it with the same instrument the street was judged by, and it records the one design call that
the card left open, which is what a park made of two greens that are 1.24:1 apart is supposed to look like.

### 22.1 The numbers the card came with, re-measured through the tool

All read from `tools/art/contrast_check.py`'s 2C02 table through `tools/palette_synergy.py`'s `Grid`, not restated:

| entry | hex | luminance | row | hue | who wears it |
| --- | --- | --- | --- | --- | --- |
| `$2A` | `#58d854` | 0.518 | 2 | hue_A | the walkable grass before this card, and the tree canopies, hedges and green awning after it |
| `$09` | `#007800` | 0.134 | 0 | hue_9 | `bg2_green`'s G, the park's field after this card |
| `$0A` | `#006800` | 0.099 | 0 | hue_A | `bg2_green`'s D, the park's shade |
| `$0F` | `#000000` | 0.000 | 0 | grey | the shared backdrop, the park's accent after this card |
| `$00` | `#7c7c7c` | 0.202 | 0 | grey | the walkable street (section 20) |
| `$30` | `#fcfcfc` | 0.973 | 3 | grey | percy's and hadrian's body |
| `$31` | `#a4e4fc` | 0.704 | 3 | hue_1 | zander's body |
| `$28` | `#f8b800` | 0.542 | 2 | hue_8 | konrad's body |

Contrast between the candidate grounds and the four bodies, measured on this tree: `$30` on G 5.55:1 (3 rows), `$31` on G
4.09:1 (3 rows), `$28` on G 3.21:1 (2 rows), and `$00` on G 1.36:1 (0 rows). That last line is the reason hadrian's suit
had to move in section 20.5 rather than the street: a `$00` body clears no dark ground either.

Three tiles carry the grass: `grass_a` (index 13), `grass_b` (14) and `grass_c` (62), all `bg2_green`, all `solid: false`
in `game/sprites_src/env/ts_exterior.json`. `tools/art/make_exterior_maps.py` paints OSM park cells with `grass_a` and
`grass_b` only (`remap_cell`, `name == "park"`), so a composed town frame can never show `grass_c`; check 13 still holds
all three, because a later card can place the third variant without any measurement moving.

### 22.2 The ground the party actually stands on, and what it measured

The frame a town is judged on is a 16 by 15 tile crop around its spawn (`render_frame`), so whether a town can even show
the park is arithmetic on its map. Measured on the three maps at this commit:

| town | crop origin | spawn | park cells inside the frame | reachable from the spawn |
| --- | --- | --- | --- | --- |
| westminster | 8, 13 | 16, 20 | 31, every one of them walkable | 24, over 511 walkable cells |
| southampton | 9, 11 | 17, 18 | 0 | 0 |
| winchester | 8, 12 | 16, 19 | 0 | 0 |

So Westminster is the only town that can hold a judged row about the park, and two of its park cells were measured. Before
this card, on the frame HEAD ships, at `--at 96,176` (map cell 14,24, `grass_a`) and at `--at 80,176` (map cell 13,24,
`grass_b`), the party's four walking sheets measured **56 failing pairs each**, every one of them on ground `$2A`:
`white_blob` 24 and `body_ground` 32, which is percy 8 plus 8, konrad 8, zander 8 plus 8, hadrian 8 plus 8. The cast half
was already clean (0 uncovered 8x8 tiles on all four sheets), so the 56 were the ground and nothing else.

After the fix, on the regenerated frame, at the same two positions: **0 failing pairs, 0 cast problems**, every sheet's
body on ground `$09`, `$0A` and `$0F`.

### 22.3 Q1: what a walkable park can be made of

`bg2_green` is `$09 $0A $2A` and the row does not move (section 22.5). Under RULE 0 point 2's 0.25 line exactly two of its
three entries are legal under a foot: G `$09` at 0.134 and D `$0A` at 0.099, plus the shared backdrop `$0F` at 0.000,
which every palette row shares and which the street already uses for its joints (section 20.4). The light `$2A` at 0.518
is legal exactly where nothing walks on it, and that is where it stays: the three tree canopies, the two hedges and the
green awning, all `solid: true`.

The card's first price was this one, and the measurement agrees with it. Its second price (a second, darker walking triple
for the party) is refused by the hardware for the reason section 16.6 and section 20.7 already gave: a scene has four
sprite palettes, all four are the party's walking triples here, and there is no fifth row to darken.

### 22.4 Q2: the call the card left open, which is how a tuft is drawn in this band

Two greens 1.24:1 apart are one tone. Filling the park with G and putting D where the old art had shade would have made a
flat field with invisible texture, and it would have thrown away the shape of the three variants, which are the ground
noise the maps rely on. The light accent H was 3.08:1 against the field, and the only entry left in this palette that
clears 3:1 against G is the shared backdrop at 3.69:1. So the light accent became the dark accent, in the same shapes:
`grass_a` puts a single black fleck where it put a single light fleck, `grass_b` puts a 2 by 2 black clump where it put a
2 by 2 light clump, and `grass_c` keeps its 2 pixel checker as a G/D dither and puts the four black flecks where its shade
flecks were. Counted on the regenerated sheet, per tile:

| tile | G `$09` | D `$0A` | backdrop `$0F` | worst luminance |
| --- | --- | --- | --- | --- |
| `grass_a` | 205 | 47 | 4 | 0.134 |
| `grass_b` | 222 | 10 | 24 | 0.134 |
| `grass_c` | 125 | 127 | 4 | 0.134 |

No tile spends more than 2 colours besides the backdrop, so the 3 colour area rule and the 25 colour frame ceiling are
untouched, and the sheet's own colour count stays 14.

### 22.5 What landed, measured before and after

**Landed.**

- `tools/art/make_ts_exterior.py`: the three walkable grass tiles, the header note with the measured numbers, and the
  comment beside `bg2_green` that says H is now solid-only.
- `game/sprites_src/env/ts_exterior.png` and `.json`, regenerated by that generator. The json's per-tile `entries` for the
  three grass tiles now read `9, 10, 15` with the matching hexes, which is the generator describing what it drew.
- `output/westminster_sample_frame.png`, regenerated by `tools/art/make_exterior_maps.py`. The two other towns' frames
  come out byte-identical to HEAD, which is the table in 22.2 seen from the other side.
- `tools/check_ts_exterior.py`: `WALKABLE_LIGHT_EXEMPT` is empty, and check 13's docstring and comment say so.
- `data/palettes/scene_westminster.json`: a second judged row, the park at `--at 96,176`, with the party's four walking
  sheets, the 56 before and the 0 after written into its note.
- `data/scene_palettes.json`: that row as the tenth audit entry, from `scene_palette_set.py build --write`. Nothing else
  in the file moves.
- `tests/test_check_ts_exterior.py`: three rows over check 13, its empty exemption list and the park's ground colours,
  because no test in the suite ran that check before this card.
- `tests/test_scene_palette_set.py`: the town row format holds three spawn rows and the one park row, with its map cell,
  its cast and the card in its note.
- `knowledge/DEVLOG.md`: one entry.

**Measured.**

- `python tools/check_ts_exterior.py`: **58 checks passed, 0 failed**, exit 0, check 13 PASS over all 20 walkable tiles
  with 0 exemptions. It was 61 checks with 3 EXEMPT lines before, and the 3 that left are exactly those lines.
- `python tools/palette_synergy.py --gate`: 9 entry(ies), 0 gated failure(s), 2 advisory failure(s), 1 not measured
  before; **10 entry(ies), 0 gated failure(s), 2 advisory failure(s), 1 not measured** after. The entry count rises by
  one because this card adds one judged row, and the two advisories are the `battle_corridor` and `title` readings of the
  title frame, which this card does not touch. Westminster now appears twice and both of its rows PASS with 0 fails.
- `python tools/scene_palette_set.py validate`: PASS, 12 scene(s), 4 hero palette(s).
- Both generators reproduce their own output byte for byte on a second run (md5 of the scene file, the tileset and the
  frame unchanged on the rerun).
- The judged row at `--at 96,176` and at `--at 80,176`, four sheets each: 0 failing pairs, 0 cast problems, ground `$09`,
  `$0A` and `$0F`.

### 22.6 What this does not decide

- **Whether it looks like grass.** A park made of a 0.134 field, a 0.099 shade and black tufts is what the measurement
  allows, and it was drawn in the shapes the old art used. Whether that reads as grass on a CRT is not measured by this
  card, the same open question section 20.8 left for the street. A screenshot card is the honest next step.
- **`grass_c` is measured only at the tile level.** No map places it, so no judged frame can stand a party on it. Check
  13 holds it; a row would need a map that paints it.
- **The other two towns' parks.** Their crops carry no park cell (table, 22.2), so their grass is held by check 13 and by
  the fact that the tiles are the same three tiles, not by a judged frame of their own.
- **No build and no hardware capture.** GameMaker is not installed on this machine, so these are pixel, palette and ground
  measurements through the project's own tools. `tools/nes_composite_check.py` is run over the three frames by check 12
  and passes; nothing here claims more than that.
- **Section 21 landed while this section was being measured.** Card `t_23b5739a` committed it as `080dc56`, so this
  section was re-applied on top of that commit rather than merged beside it, and the two are in this file in order.

Provenance for section 22: studied this repository's own files only (`tools/palette_synergy.py`,
`tools/check_ts_exterior.py`, `tools/art/make_ts_exterior.py`, `tools/art/make_exterior_maps.py`,
`tools/art/contrast_check.py`, `tools/scene_palette_set.py`, `knowledge/ART-BIBLE.md`, `data/nes_palette.json`,
`data/palettes/scene_westminster.json`, `scene_southampton.json`, `scene_winchester.json`,
`game/sprites_src/env/ts_exterior.json`, the tileset, the four walking sheets, and the commit history of all of them). No
decompiled material was read for this card and no expression from any game is in it. Copied expression: none.

## 23. Q1, Q2 and Q3 on the ship's background rows, second pass: the drawing moves under the rows, the pin comes out, and a measured floor takes its place (card `t_463cb8c1`)

Section 21 kept the ship's four rows and handed the redraw both sides of the trade; this card is that redraw, and it
pays 21.4's receipt line by line. The short version: the water family is now drawn on the sea's own three tones, the
portholes are drawn on the steel row, the cargo family keeps every brass pixel because a row now carries brass, and
the rows are the measured best fit to the drawing. The pin comes out, and what replaces it is a number.

### 23.1 Q1: the water family is redrawn on the sea's own three tones. Foam is crest `$21`, not white `$30`

The defect 21.6 named first was that the water family is "a flat fill named after things it does not draw". On the
committed sheet `water_a`, `water_b`, `water_edge` and `water_foam` were 256 identical pixels of `$12` each and
`water_deep` was 246 of `$02`, because the row they were painted into carried `$12` and nothing else the water drew.
The five tiles are now drawn on `bg3` `$02 $12 $21`, which is the sea's own triple:

| tile | what it draws now | `$02` deep | `$12` mid | `$21` crest |
| --- | --- | --- | --- | --- |
| `water_a` | open sea frame one: four crests on an uneven pitch, each with its own trough under it | 11 | 230 | 15 |
| `water_b` | the same swell, every crest drifted three pixels, the big one a pixel longer | 12 | 228 | 16 |
| `water_edge` | the water line: a ragged two row foam line across the top, trough under it, sea below | 15 | 213 | 28 |
| `water_deep` | deep water: navy body, three low swells, two glints | 246 | 8 | 2 |
| `water_foam` | breaking water: a mass of foam with holes and a trough under its near edge | 15 | 142 | 99 |

The animation pair is `water_a` / `water_b` at `ANIM_FPS` 2.0, and the pair now differs by the three pixel drift and
the one pixel of crest growth, so the sea moves rather than flickers. The foam tile is deliberately the light one: at
16 px the thing that says "foam" is how MUCH of the tile is the light tone, so it is 99 crest pixels on a mid body
where `water_a` is 15 crest pixels on a mid body. A version with six small whitecaps measured 19 crest pixels and read
as busier calm water; that is recorded because it was tried and rejected on the render, not on the numbers.

**Foam is not white, and the reason is arithmetic.** A row holds three entries. Water needs the deep and the mid to be
water at all, so the third slot is white or it is crest, never both, and the sheet's own table said `$30` was foam.
It has to be crest, because `$21` has no other home on this sheet and may not leave it: `tools/art/make_ship_tiles.py`
draws the ship interior's terminal screen with `$21` and
`tests/test_make_ship_tiles.py::test_the_palette_is_the_ships_own_strip_palette` holds that sheet's ten colours as a
SUBSET of this sheet's ten (recited in 21.3 as the third refusal). White foam would therefore mean redrawing a 96 tile
interior sheet and its test, which is another sheet's card. The table's two lines were rewritten to say what the rows
can actually do: `$21` reads "sea crest: wave light and foam (the water family's light tone)" and `$30` reads "white
paint: corridor lines, rim light, porthole glare". White is still on the sheet and still on the water's row set, one
row over, as the glare in the porthole glass and the paint on the bulkheads.

Measured on the drawing, the water family's loss went from 274 pixels to 0: `water_a` 54 to 0, `water_b` 54 to 0,
`water_edge` 66 to 0, `water_deep` 10 to 0, `water_foam` 90 to 0.

### 23.2 Q2: the cargo family keeps its brass because a row now carries it

Nothing in the cargo family is redrawn. `crate` 36 brass pixels, `crate_stack` 12, `barrel` 20, `table` 12 and
`bollard` 67 were being repainted under `bg2` `$02 $07 $17`; `bg2` is now `$07 $17 $28`, the rust pair plus the
brass, so the whole family repaints nothing and the wood floors, which need only `$07 $17`, are unaffected. The
fittings that were already drawn with brass on the steel row keep it too: `bulkhead_light` 16, `hatch_closed` 39,
`pipes` 22, `pipe_vert` 16, `cable_run` 24 and `locker` 12. Brass on the sheet is 276 pixels, cargo plus fittings, and
all 276 survive the palette pass. The bollard's 43 rust pixels survive as well.

So Q2 of section 21, "whether the cargo family should carry brass", is answered yes, and it is answered in the ROWS
rather than in the art: the art was already right.

### 23.3 The porthole, which section 21's tables could not see

Both of section 21's candidate sets repainted 80 pixels of `porthole_a` and 80 of `porthole_b`: 160 pixels, the
largest single loss on the sheet and four times the largest water tile. Neither table in 21.2 names it, because both
sets lose it equally, so the per tile difference was zero and the total hid it. It is visible on `porthole_a`, which
`data/maps/ship_sample_tiled.json` places: the glass was sea mid `$12` and the frame steel `$00` and `$10`, and no
three entry row can hold a sea and a steel frame at once. It could be bought, at a price: the best four row set that
carries a porthole capable row is 205 pixels against the 76 this card ships, which is the fittings' 129 brass and the
rest. It is not worth 129 brass pixels, so the tile is redrawn instead: the glass is steel light `$10` with a white
`$30` glare and one scratch across it, which is daylight through a window and the right read for a porthole on a lit
deck. The tile table moves `porthole_a` and `porthole_b` from palette group `sea` to `steel`, where a porthole set
into a bulkhead belongs. Cost: 0 pixels, on a placed tile.

### 23.4 Q3: the rows take the drawing's grouping, the pin comes out, and a measured floor replaces it

The four rows `data/palettes/scene_ship.json` now carries are `bg0` `$00 $10 $30` steel and white paint, `bg1`
`$00 $10 $28` steel and brass fittings, `bg2` `$07 $17 $28` rust and brass cargo and wood, `bg3` `$02 $12 $21` the
sea. On the raw drawn sheet they repaint 76 pixels of 12288 (0.62%), in two tiles: the bunk's rust frame 60 and the
lifebuoy's four rust bands 16. That is 762 down to 76, and 19 tiles down to 2.

The set was not hand picked. `itertools.combinations` over the 84 three entry groups the nine non backdrop entries
make, taken four at a time, is 1929501 four row sets, and every one of them was scored by how many drawn pixels it
repaints. The shipped set is the minimum at 76. The nearest rivals:

| repaint | rows | what it buys and what it costs |
| --- | --- | --- |
| 76 | `$00 $10 $28`, `$00 $10 $30`, `$02 $12 $21`, `$07 $17 $28` | the set that ships |
| 145 | `$00 $07 $10` in place of `$00 $10 $28` | the bunk's 60 rust pixels, at the cost of the fittings' 129 brass |
| 187 | `$07 $17 $30` in place of `$07 $17 $28` | the lifebuoy ring, at the cost of the cargo's 147 brass |
| 189 | adds `$10 $17 $30` | the bunk and the lifebuoy, and it still pays for the fittings |
| 205 | `$00 $12 $21` in place of `$00 $10 $28` | the porthole's old steel and sea glass, at the cost of the fittings' brass |

Every rival trades a placed tile for the fittings row, and the fittings row is 129 brass pixels spread over six tiles,
so the minimum is also the set that costs the fewest placed tiles. The search is in this card's scratch, not in the
repository: it is a one off measurement, and what lands is the set, the number, and the guard below.

**The solver, measured on the drawing.** `solve_ship()` used to measure `game/sprites_src/env/ts_ship.png`, which is
the drawing after the rows were already applied, so the solver was scoring its proposal with the pass it was proposing
to change. On the enforced sheet its proposal "covered every tile", which is the rows agreeing with themselves. It now
measures `make_env_ship.render_sheet()`, the drawing before the pass, and the difference is the whole of section 21.5:

```
$ python tools/art/scene_palette.py solve --scene ship
ship: backdrop $0F #000000   48 16x16 areas, 725 pixels outside the chosen palette before enforcement
  background 0  $00 #7c7c7c  $10 #bcbcbc  $30 #fcfcfc
  background 1  $07 #881400  $28 #f8b800  $30 #fcfcfc
  background 2  $02 #0000bc  $12 #0058f8  $17 #e45c10
  background 3  $00 #7c7c7c  $02 #0000bc  $21 #3cbcfc
  repaint on the drawing: the proposal 725 of 12288 pixels over 19 tiles, the file's rows 76 over 2 tiles
  NOT applied: the proposal repaints more of the drawing than the rows already in the file, so a write would make
  the art worse (card t_463cb8c1).
  the file's rows are the better fit and stay as they are.
```

`--write` prints the same refusal and leaves the file byte identical: sha256 `11199e298c4efd...` before and after,
which is measured, not assumed. The solver is a heuristic that groups the sheet's colour pairs; it misses the grouping
the art is drawn in, and the redraw widened the gap rather than narrowing it, because the new foam tile is 99 crest
pixels the proposal's rows cannot show. That is the honest state of the tool: its proposal is not a better answer to
argue with, and a refusal is the right output for it.

`background_pinned` therefore comes out of `data/palettes/scene_ship.json`. The key, the `write_scene()` handling and
`tests/test_scene_palettes.py::test_a_solve_keeps_a_pinned_background_half` all stay, because the mechanism is general
and a future half may need it; the test now seeds its own scratch copy with the key and keeps its control (the same
call moves the rows once the key is gone), instead of asserting the shipped file is pinned. What the ship carries
instead is the note with both numbers in it, and the floor in the solver, which needs no key: a proposal that repaints
more of the drawing than the rows in the file is reported and not written.

### 23.5 What landed, and what this does not decide

Landed: `tools/art/make_env_ship.py` (the colour rule in the docstring, the ten colour table with its new `$21` and
`$30` lines, the five water tiles, the porthole glass, the porthole tile group); `tools/art/scene_palette.py`
(`ship_drawing()`, `repaint_cost()`, the floor in `solve_ship()`, both numbers in `describe()`, the module docstring,
the `BACKGROUND_PINNED_KEY` comment); `data/palettes/scene_ship.json` (the four rows, the note, no pin);
`data/scene_palettes.json` and the generated `game/sprites_src/env/ts_ship.png`, `ts_ship.json`,
`ts_ship_tiled.json`, `data/maps/ship_sample_tiled.json` and `output/env_ship_preview.png`, rebuilt by their own
generators; `tests/test_make_env_ship.py` (the water family, the brass that survives the pass, and the 76 pixel pin)
and `tests/test_scene_palettes.py` (the pin test rewritten, the floor's own test with a worse and a better proposal);
this section; a DEVLOG entry and a PROVENANCE entry. The rebuilt sheet is sha256 `31ff08230addd3eec2a5e41ee71c35e32f8fb79ade433fee744795e8d948c883`.

Green on this tree: `python -m pytest tests/test_make_env_ship.py tests/test_scene_palette_set.py
tests/test_scene_palettes.py tests/test_make_ship_tiles.py -q` reads 68 passed, 3 warnings (two of them Pillow's
`getdata` deprecation in `tests/test_make_ship_tiles.py`), 0 failed; `python tools/check_env_tiles.py` exits 0;
`python tools/check_scene_palettes.py --quiet` exits 0; `python tools/scene_palette_set.py build --write` exits 0 and
derives the same set.

Not decided here, with the number each would cost. The lifebuoy keeps its orange ring and pays 16 pixels of grey,
because the row that can show its white ring cannot show its `$17` rust bands, and the row that could show them costs
the cargo's 147 brass; making the bands grey instead is a redraw of a tile that reads correctly today, and this card
declines it. The bunk keeps its rust frame and pays 60 pixels of grey for the same reason, and the row that would save
it costs the fittings' 129 brass. Whether `$21` should leave the sheet and take the ship to nine colours is still
another sheet's card, and the water family now depends on that colour, so the answer has hardened rather than softened.
And whether the sea should be drawn at all before a room needs it: the water family is the one part of this card that
no map places.

Two hazards. `data/maps/ship_sample_tiled.json` places 32 of the 48 tiles and none of the five water tiles, so the sea
is judgeable only on `output/env_ship_preview.png`, the strip the generator composes, and on the sheet; a room that
places it may still find the three tone sea too flat against a bulkhead. And the palette pass still repaints 76
pixels, now pinned by a test that names the two tiles and the number, so the next art change that loses more fails
loudly instead of silently.

Provenance for section 23: studied this repository's own files only (`tools/art/make_env_ship.py`,
`tools/art/scene_palette.py`, `tools/art/make_ship_tiles.py`, `tools/scene_palette_set.py`, `tools/check_env_tiles.py`,
`tools/check_scene_palettes.py`, the four test files named above, `data/nes_palette.json`,
`data/palettes/scene_ship.json`, `data/scene_palettes.json`, `game/sprites_src/env/ts_ship.png` and
`ts_ship_tiled.json`, `data/maps/ship_sample_tiled.json`, `output/env_ship_preview.png`, sections 21 and 22 of this
file, `knowledge/SHIP-PALETTE-DRIFT-2026-10-25.md`, and the commit history of all of them). No decompiled material was
read for this card and no expression from any game is in it. Copied expression: none.

## 24. The ship sheet declares its backdrop: the 44 px the audit charged were the steel grey guess, not a drawing bug (card `t_4d5984b4`)

Run 12 of the palette pass list (`knowledge/PALETTE-PASS-LIST.md`, card `t_585efccb`) turned one GAME ASSET red for the
first time since run 11: `game/sprites_src/env/ts_ship.png`, 256x48, `44 px background_area x3`, reproduced on this PC
and on Pine at HEAD `8220c95`. This section is the ruling. The drawing is legal NES art, `background_area` is right, and
the input the audit measured was wrong: the sheet's sidecar did not declare its backdrop, so the audit guessed one and
guessed the steel grey.

### 24.1 What the three areas actually carry

The three failing blocks are `[112, 16]` (20 px), `[96, 16]` (12 px) and `[32, 32]` (12 px), which are tile ids 23
`barrel`, 22 `crate_stack` and 34 `table`, the rust group, each already declaring `colours: "r,o,y"` in
`ts_ship_tiled.json`. Every one of them carries `#000000 #881400 #e45c10 #f8b800`. That is four colours including the
backdrop and three besides it, and the three besides it are exactly the ship scene's `bg2` row in
`data/scene_palettes.json`, entry numbers `[7, 23, 40]`. So each area is the hardware maximum and nothing over it: the
one shared backdrop `$0F` plus one three entry background row. There is nothing here to repaint.

### 24.2 Why the audit saw four colours besides the backdrop

`tools/nes_audit_all.py::declared_backdrop()` reads a background's backdrop from the sidecar beside the PNG and falls
back to the sheet's most common opaque colour only when that key is missing. `ts_ship.json` did not carry the key. On
this sheet the fallback picks the wrong colour, because steel mid `$00 #7c7c7c` is 3553 opaque pixels and the black
backdrop `$0F` is 3350. A guessed grey then makes every black seam on the rust row a fourth colour in its area. Measured
both ways on the same committed PNG: guessed `#7c7c7c` gives 44 offending pixels over 3 areas; declared `#000000` gives
0 offending pixels over 0 areas.

`game/sprites_src/env/ts_exterior.json` already declares `{"entry": 15, "hex": "#000000"}` and has never failed this
rule. The ship's sidecar was the one beside a measured sheet that was missing it.

### 24.3 The fix

`tools/art/make_env_ship.py` gains `BACKDROP_DECLARED`, derived from the backdrop row of its own `PALETTE` table (entry
15, `#000000`), and writes it into both `ts_ship.json` and `ts_ship_tiled.json`, so the declaration cannot drift from
the palette table and a regeneration keeps it. No pixel moved: after `python tools/art/make_env_ship.py`, `git diff
--stat` on the build's outputs names the two JSON files and nothing else, with `ts_ship.png`,
`data/maps/ship_sample_tiled.json` and `output/env_ship_preview.png` byte identical.

`tests/test_make_env_ship.py::test_build_writes_the_five_outputs_the_card_names` pins the meta dict exactly, so it gains
the key too. That pin is what holds the declaration through a rebuild.

### 24.4 Checked

- `python tools/nes_audit_all.py --only ts_ship --no-write`: PASS, 1 file, 0 failing, exit 0. Before: FAIL, 44 px,
  `background_area x3`, exit 1.
- `python tools/nes_audit_all.py --no-write`: 183 files, 34 failing, exit 1. Before: 183 files, 35 failing. The row that
  left the list is this asset; the 34 that remain are output previews and captures, all another lane's.
- `python tools/check_env_tiles.py`: PASS, 48 tiles, 10 colours, map 20x15, `worst_area_colours 3`.
- `python -m pytest` over the ten env, palette, audit and ship suites: 171 passed.

### 24.5 The class this names, and what it does not decide

45 of the 54 background assets the audit measures carry no declared backdrop: the 42 title layers including every fade
and flash variant, and the 3 ui screens. Every one of them passes today only because its most common opaque colour
happens to BE the backdrop. Any repaint that flips that count turns a legal sheet red exactly the way this one did, with
the same phantom that cost this card. The rule the audit's own docstring states is the durable one: art whose backdrop
is not its commonest colour must declare it. Enforcing the declaration on every background sheet belongs to whichever
generator owns that sheet, not to this card, and none of them fails today, so no card is opened for it here.

`data/scene_palettes.json` was not touched; the palette entries are NES-PALETTES `t_c8156a77`'s.

Provenance for section 24: studied this repository's own files only (`tools/nes_audit_all.py`,
`tools/art/make_env_ship.py`, `tools/check_env_tiles.py`, `game/sprites_src/env/ts_ship.json`,
`game/sprites_src/env/ts_ship_tiled.json`, `game/sprites_src/env/ts_exterior.json`, `data/scene_palettes.json`,
`data/nes_palette.json`, `tests/test_make_env_ship.py`, `tests/test_nes_audit_all.py`, and the audit's own measured
output at HEAD `8220c95`). No decompiled material was read for this card and no expression from any game is in it.
Copied expression: none.
