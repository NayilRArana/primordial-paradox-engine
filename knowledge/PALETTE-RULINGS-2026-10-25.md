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


