# SPRITE-CRITIQUE

Why our character sprites look amateur, measured one pixel at a time, with the fix and the check for
every sheet in the game.

Card `t_039ec0db` (SPRITE-STUDY-2), research-assistant, 2026-10-22. Read with
`knowledge/SPRITE-CRAFT.md` (588 lines, the recipes) open beside it; every rule quoted below is that
file's, cited by section. Hardware limits are `knowledge/ART-BIBLE.md` section 1. Character facts are
`knowledge/CHARACTER-BIBLE.md` REVISION 2. Nayil's verdict this card answers: "the overworld character
sprites look janky and cutesy, the sailors look like white blobs, it looks amateur".

## 0. What was measured, and what was not

Every number in this file comes from reading the PNG files as data, never from looking at them.

| Method | What it produced |
| --- | --- |
| `Pillow`, per frame, every sheet in `game/sprites_src/chars`, `enemies`, the two title character sheets | the ASCII grid of every frame with a colour legend, so a pixel coordinate can be named |
| the same, plus connected component analysis | opaque pixel count; the share of each colour; the number of rows with no dark pixel; the number of separate dark runs in the body block; the count of interior dark pixels; symmetry; the silhouette boundary share that is not outlined |
| `data/nes_palette.json` plus WCAG relative luminance | contrast ratio of every sprite colour against the declared ground colours of the ship deck and the night road |
| `tools/nes_check.py --type sprite` | the hardware verdict on every sheet today |
| `tools/nes_composite_check.py` | available, not run in this card: it needs a composited 256 x 240 frame, and no restaged frame exists yet for the redraws |

What was **not** done: nobody looked at the sprite previews. This lane cannot see images, and PLAN-V2
section 0 gives the eye check to the manager. So this file says nothing about how a sprite feels; it
says what its pixels are, and it names the number that would have to change. The manager still has to
confirm the result, and the three mocks in section 5 have never been rendered.

## 1. The headline: the validator says PASS on every sprite we have

This is the finding that explains the whole card.

```
game/sprites_src/chars/sailor_ow.png   128x16  32 tiles  2 colours  PASS
```

`sailor_ow` is 2 colours, 90 of its 108 drawn pixels are one flat white, and it has no face. It passes.
All 13 character sheets and all 7 enemy sheets pass `nes_check.py --type sprite` today. The validator
tests the hardware rules (C1 to C6 of ART-BIBLE section 4) and none of the art rules, because the art
rules had not been written when it was written. `nes_check` passing is necessary and it is not
sufficient, and treating PASS as done is exactly how a set of sheets this weak got shipped into the
repo.

The craft rules that decide whether a sprite reads are in `SPRITE-CRAFT.md` sections 8.5 (the blob
test, four numbers), 12.1 (the contrast floor, two numbers) and 2.1 to 2.4 (the body plan and the
width ladder). Those are the checks in `data/sprite_redraw_queue.json`.

## 2. The six defects, and the number that fixes each

Measured across the 13 character sheets. Every one of these appears in more than one sprite.

| # | Defect | Where it shows | What the numbers say | The fix, as a number |
| --- | --- | --- | --- | --- |
| D1 | **No outline at all** (Zander), or an outline in a tone the ground already uses (sailor, Percy) | `zander_ow` has 4 black pixels in the whole sprite; `sailor_ow` outlines in `$02` navy; every other sheet outlines in `$0F` black | black `$0F` against the night road `$02` is **1.73 : 1** where SPRITE-CRAFT 12.1 demands **3.0 : 1**; navy `$02` against the same road is **1.00** | 1 px outline in `$0F` on the ship deck (5.03 : 1) and in `$10` on the night road (6.41 : 1); the outline tone belongs to the room palette, not the sprite |
| D2 | **Cutesy proportions** | head 9 of 16 rows in `konrad_ow`, 9 in `hadrian_ow`, rows 0 to 13 in `sailor_ow` | konrad and hadrian are **1.8 heads tall**; SPRITE-CRAFT Plan A is head 7 rows, body 8 rows, **1 : 1.14** | head rows 0 to 6, neck and shoulders row 7, torso rows 8 to 12, belt row 13, legs 13 and 14, row 15 empty |
| D3 | **Face unreadable** | every overworld sheet: 2 single pixels for eyes on a flat 6 x 4 skin block | eyes are 1 px; SPRITE-CRAFT section 3 rule 5 says **2 px**; the head has 2 dark pixels where the recipe wants **12 to 18 of 56 to 64** | 2 px eyes, 1 px or 2 px nose bridge, 1 px jaw line at row 6, 1 px hairline down at least one side of the face |
| D4 | **The white blob** | `sailor_ow` | 1 tone is **83 percent** of the sprite; the blob ceiling is 30 percent and the blob line is 45 | light tone under 30 percent; 0 rows without a dark pixel; 3 or more dark runs in the body block; 8 or more interior dark pixels |
| D5 | **The figure is one flat mass of the darkest tone** | `hadrian_battle` 82 percent black, `konrad_battle` 68 percent, `hadrian_ow` 61 percent | the suit, the outline and the legs are the same entry, so there is no interior line anywhere | 15 percent shaded, all of it on the right and bottom; 8 or more interior dark or light lines; a distinct mid tone for the garment |
| D6 | **Fills that are the same colour as the ground** | Percy's jacket `$02` 37 percent of the sprite; the trident shaft `$10` in `percy_battle`; Zander's jacket `$21` | `$02` against the night road is **1.00**; `$10` against the ship deck is **1.00**; `$21` against the deck is **1.95** where the floor is 2.0 | the largest fill clears **2.0 : 1** against every ground tile the sprite can stand on, which is the measurable form of the card's "at least 2 palette steps" |

D6 is the one Nayil's eye caught first and the one no validator was checking. Six of the seven colours
that make up Percy's overworld sprite are declared background entries in our own scene files.

## 3. What is wrong, sheet by sheet

Coordinates are `(column, row)` with 0,0 at the top left of the frame, matching the ASCII grids in
`output/_sprite_grids.txt` if that dump is regenerated. "Light tone" means the most luminous entry in
the sheet.

### 3.1 Konrad (`konrad_ow`, 16 x 16, 8 frames)

What is wrong, in plain words:

- The hair is 55 px of one flat `$38` blond, 46 percent of the whole sprite, and it runs from row 0 to
  row 8. From row 2 to row 5 it wraps a 6 x 4 skin rectangle at columns 4 to 9. That rectangle is the
  face and it has two 1 px black pixels at (6,4) and (9,4) and nothing else. This is the definition of
  cutesy: a ball of hair with a mask under it.
- There are **8 rows with no dark pixel** in a drawn figure of 16 rows. A row with no dark pixel has no
  structure at all (SPRITE-CRAFT 8.5 test 2).
- The body block has **1 dark run**. Test 3 wants 3 or more.
- The torso, rows 9 to 12, is pure `$000000` 8 px wide. There is no blazer, no shirt, no open collar and
  no lanyard, all of which CHARACTER-BIBLE REVISION 2 requires for Konrad, an AI research scientist.
- Two transparent holes sit inside the body at (5,8) and (10,8), and there is a stray skin pixel inside
  the hair at (5,1). Six of the eight rows 0 to 8 are one tone with no interior line.
- The legs, rows 13 to 15, are two 2 px black bars at columns 5 to 6 and 9 to 10, with no boot line and
  no ground contact detail. They merge into the black torso above them.
- The walk is fake. The per-frame pixel differences are `[8, 49, 8, 55, 8, 64, 8]`: two real poses and
  an 8 pixel flicker on the frames between them, so a 2 pose cycle has been padded out to 8 cells.
- Frame 2 replaces the head with flat hair: 71 px of `$38` and the face drops to 8 px. Frame 2 is a
  different character from frame 0.

The fix, pixel by pixel:

1. Head rows 0 to 6 only. Row 0: `$38` hair mass, columns 5 to 10, with `$0F` at (4,0) and (11,0).
   Row 1: `$0F` at (4,1) and (11,1), `$38` at columns 5 to 10, and a `$18` shade pixel at (10,1).
   Row 2: hairline `$0F` at (4,2) and (5,2), skin `$36` at columns 6 to 9, `$0F` at (10,2) and (11,2).
   Row 3: eyes, 2 px each, `$0F` at (5,3),(6,3) and (9,3),(10,3); skin `$36` at (7,3) and (8,3).
   Row 4: skin `$36` at columns 5 to 10, `$0F` jaw shadow at (4,4) and (11,4).
   Row 5: beard `$38` at columns 5 to 10 (close beard, one row), `$0F` at (4,5) and (11,5).
   Row 6: chin, `$0F` at (4,6),(5,6),(10,6),(11,6), skin `$36` at columns 6 to 9.
2. Row 7, the shoulder line: `$0F` at columns 3 and 12, `$2E` charcoal blazer at columns 4 to 11, with
   `$36` skin at (7,7),(8,7) for the neck.
3. Rows 8 to 12, the body: blazer `$2E` at columns 4 to 11; the **open collar** as a `$0F` V at (7,8),
   (6,9),(8,9); the lanyard as a 1 px `$30` line at (9,8),(9,9),(9,10); the right column (11,8) to
   (11,12) in `$1C` as the shade side. That is 8 interior dark pixels and 2 dark runs on its own.
4. Row 13: belt, `$0F` at columns 4 to 11.
5. Row 14: legs, `$0F` at columns 5 and 6 and at 9 and 10, with a 1 px `$2E` boot at row 14 and row 15
   empty. The leg gap is columns 7 and 8, 2 px, which is load bearing (SPRITE-CRAFT 2.4).
6. Redraw the walk as 2 poses with 6 to 10 changed pixels, all of them in rows 13 and 14. The torso must
   be byte identical between the two poses. Kill frames 2 to 7 or make them the mirrored leg swap.

The redraw brief: one figure, 7 head rows, 8 body rows, charcoal blazer with an open collar and a
lanyard, blond hair with a `$18` shade, a close one row beard, a wristwatch as 1 px of `$28` at (4,11),
and a sickle keyring as 2 px at (12,13) to (13,14) hanging outside the hip so the silhouette breaks.

### 3.2 Zander (`zander_ow`, 16 x 16, 8 frames)

What is wrong:

- **The sprite has no outline.** It contains exactly 4 black pixels in total: (6,4),(9,4) for the eyes
  and (5,7),(10,7) at the bottom of the face. 14 of the 16 rows have no dark pixel, and there are 0
  interior dark pixels. This is why it reads as a sticker rather than a drawing.
- 3 of its 7 colours are exact background entries from our own scene files: `$21` `#3cbcfc` (34 px,
  the jacket, 30 percent of the sprite), `$31` `#a4e4fc` (12 px) and `$11` `#0078f8` (4 px). On the
  night sea tiles of `scene_sea.json` bg1 and the sky of `scene_battle_deck_night.json` bg1, the
  contrast against the jacket is **1.00**: the bomber disappears into the sky.
- Head rows 0 to 7, 8 of 16, so 2 heads tall: the cutesy proportion again, and Zander is 19, an adult.
- Frame 2 replaces the whole head with one flat `$38` block rows 0 to 7 and drops the face entirely,
  exactly as Konrad's does. The walk frames are not the same character.

The fix, pixel by pixel:

1. Head rows 0 to 6, with an `$0F` outline on every row. Row 0: `$0F` at (4,0),(9,0). Row 1: `$0F` at
   (3,1),(10,1). Row 2: `$38` hair at columns 4 to 9, `$0F` hairline at (5,2) and (8,2). Row 3: eyes
   `$0F` at (5,3),(6,3) and (9,3),(10,3), skin `$36` at (7,3),(8,3). Row 4: skin `$36` columns 4 to 10,
   `$0F` at (3,4) and (10,4). Row 5: skin, plus one `$38` lock of hair over the forehead at (6,5).
   Row 6: jaw `$0F` at (4,6),(9,6).
2. Give the bomber a mid tone that clears the floor. `$21` against the ship deck is 1.95, under the 2.0
   floor; `$31` is 3.00 and `$30` is 4.07. So: jacket light plane `$31` on the left 3 columns, jacket
   `$21` on the right, `$0F` outline all round. The jacket then has 3 tones and its lightest plane
   clears the deck.
3. Rows 7 to 12: bomber at columns 3 to 10 with the zip as a 1 px `$0F` line at column 7 from row 8 to
   row 11, a 2 px `$0F` pocket flap at (4,11),(5,11), and the hem `$0F` at row 12.
4. Row 13 waistband `$0F`, row 14 legs `$0F` at columns 5,6 and 9,10, row 15 empty.

The redraw brief: light blue oversized bomber with a visible zip and a pocket, earbud as 1 px of `$0F`
at (12,4) **touching** the hair outline so it is not a floating pixel, blond messy hair as the identity
mass, and the storm cloud is not part of the sprite (the map draws it).

### 3.3 Percy (`percy_ow`, 16 x 16, 8 frames)

What is wrong:

- **The jacket is the road.** `$0000bc` is 42 px, 37 percent of the sprite, and `$0000bc` is entry 0 of
  `bg0` in `data/palettes/scene_battle_deck_night.json` and entry 0 of `bg1` in `scene_sea.json`.
  Contrast against the night ground is **1.00**. On the blue night road Percy has no torso and no legs;
  only his face and his ginger hair float.
- **Outline coverage is 0.174.** Only 17 percent of the silhouette boundary is dark. The navy jacket
  touches the background directly on rows 9 to 13, so even against a ground it did contrast with, the
  edge would be open.
- **Symmetry is 1.000.** The sprite is a perfect left to right mirror. There is no facing, no stride and
  no light direction, which is SPRITE-CRAFT 11 mistake 3, the stiff symmetric pose.
- The uniform is not the uniform. CHARACTER-BIBLE REVISION 2 asks for a Royal Navy lieutenant: a white
  shirt, a dark tie or an open collar, a shoulder rank mark and a TRIDENT. The sprite has none of them.
  The beard is a solid 6 px black bar at row 7 sitting on a 6 px moustache row at row 6.
- Face: 2 single pixel eyes at (6,4) and (9,4) on a 6 x 4 skin block, the same mask as everyone else's.
- Head rows 0 to 7, 50 percent of the figure.

The fix, pixel by pixel. This is the first of the three mocks and section 5 has the whole grid:

1. Head rows 0 to 6: ginger `$17` hair at rows 0 to 1 with a `$0F` outline, skin `$36` rows 2 to 4 with
   2 px eyes at (5,3),(6,3) and (9,3),(10,3), beard `$17` at rows 5 to 6 with a `$0F` jaw.
2. Row 7 the shoulder line with the neck at columns 5 to 7.
3. Rows 8 to 9: the **collar V** in `$0F` at columns 5 to 8 narrowing to 6, on a `$30` white shirt. The
   V is the officer shape; the rating gets a horizontal band instead (SPRITE-CRAFT 13.2).
4. Rows 10 to 12: shirt `$30` at columns 3 to 8, shirt shadow `$10` at column 9, arm outline `$0F` at
   columns 2 and 10. A `$28` gold rank pixel at (3,8) is the shoulder mark.
5. Row 13 the belt `$0F`, row 14 legs `$0F` at columns 4,5 and 8,9.
6. The trident at columns 12 to 14: prongs `$10` at (12,8),(14,8) and (12,9),(14,9), dark centre prong
   `$0F` at (13,8),(13,9), crossbar `$0F` at (12,10),(13,10),(14,10), shaft `$0F` at (13,11) to (13,14).
   It stands outside the body outline, which is the point: a weapon inside the outline reads as nothing
   (SPRITE-CRAFT 7.3).

### 3.4 Hadrian (`hadrian_ow`, 16 x 16, 8 frames)

What is wrong:

- **61 percent of the sprite is one black mass**: 65 px of `$000000`. The suit, the head outline, the
  arms and the legs are the same entry, so the figure is a black rectangle with a hole for a face.
- The face is **32 px of pure `$fcfcfc` white**, 30 percent of the sprite, at columns 4 to 9 rows 2 to 8.
  `$fcfcfc` is not a skin tone: it is the white of `bg0` entry 2 in `scene_battle_deck_night.json`, at a
  contrast of **1.00** against that sky. A white block on a black bar is not a person.
- 2 rows have no dark pixel, and the eyes are again two single pixels at (6,4) and (9,4) with a 2 px
  bridge, when SPRITE-CRAFT section 3 rule 5 asks for 2 px eyes.
- Frame 2 blinks the face out of existence: 4 px of white and 3 of black at row 3. For one frame of the
  eight the head is gone.
- The gems of CHARACTER-BIBLE REVISION 2 are 3 px of `$6844fc`, one pixel each, at (10,12),(13,12) and
  (13,12): single isolated pixels, which is SPRITE-CRAFT 11 mistake 4.

The fix, pixel by pixel:

1. Split the suit into three tones: `$0F` outline, `$2D` mid for the suit body, `$10` light for the lit
   shoulder and the shirt front. 61 percent black becomes at most 25 percent black.
2. Skin `$36` at columns 5 to 10 rows 2 to 5, not white. Eyes `$0F` 2 px each at (5,3),(6,3) and
   (8,3),(9,3) with a 1 px bridge at (7,3), and 1 px `$13` dark circles under them at row 4.
3. The gem pin: a 2 x 2 `$2D` gem at (7,8) on a `$28` tie, or drop it. One pixel is noise, four pixels
   is a detail.
4. Row 13 belt, row 14 legs with a 1 px `$10` shoe highlight at (4,14) and (9,14).

### 3.5 The sailor (`sailor_ow`, 16 x 16, 8 frames)

This is Nayil's white blob, and the numbers are worse than they look in words:

- **2 colours in the entire sheet.** `#fcfcfc` 90 px and `#0000bc` 18 px. The record is not that it is
  simple; it is that it under-uses the hardware by a third. A sprite tile may hold 3 opaque colours.
- The white is **83 percent** of the sprite. SPRITE-CRAFT 8.5 sets the ceiling at 30 percent and calls
  anything over 45 percent a blob. This is 1.8 times the blob line.
- The only other colour, `$0000bc`, is a declared background entry: **1.00** contrast on the night road
  and **2.91** on the ship deck, under the 3.0 outline floor. On the road the figure has no edge at all;
  on the deck it has a weak one. It fails the contrast rule on both maps it has to walk on.
- 9 rows with no dark pixel; 0 interior dark pixels; the only suggestion of a face is 4 navy pixels at
  row 4, columns 4, 6, 7, 9 and 10.
- The head runs from row 0 to row 13. There is no neck, no jaw and no shoulder line: 88 percent of the
  figure is head.
- The frames disagree about the costume: frames 0 and 1 have a white torso with navy rows at 2 to 7,
  frames 2 and 3 have a solid navy torso. Four of the eight frames are a different uniform.

The fix, pixel by pixel. The grid is in section 5. This is the second mock:

1. A cap, because it is the cheapest identity in the game (SPRITE-CRAFT 8.4): rows 0 to 1 the cover in
   `$10` light grey with a `$0F` outline, row 2 the peak in `$0F` across columns 3 to 10.
2. Rows 3 to 6 the face, skin `$36`, 2 px eyes at (5,4),(6,4) and (8,4),(9,4), a `$0F` jaw at row 6.
3. Row 7 the **rating's collar**: a horizontal `$0F` band across columns 2 to 11. That single shape is
   what separates a rating from an officer; Percy has the V, the crew has the band.
4. Rows 8 to 12 the white shirt `$30` at columns 3 to 10, with `$10` light grey on the right 2 columns
   as the shadow, a 2 px `$0F` black silk knot at (7,9) to (7,10), and a 1 px `$0F` cuff at (9,11).
5. Row 12 a 1 px `$0F` shirt hem inset from the outline, row 13 the trouser break `$0F`, row 14 the
   legs, row 15 empty.

Every one of those is a 1 to 3 px detail and every one converts a white shape into a naval rating.

### 3.6 The crew as enemies (`enemies/navy_sailor`, `enemies/petty_officer`, 32 x 32, 3 frames)

- Both sheets have **3 colours** (`$0F`, `$02`, `$30`) and both change costume on frame 2: the body goes
  from navy 114 px to white 201 px. The same drift as `sailor_ow`.
- The two are near duplicates: 336 and 340 opaque pixels, the same 3 colours, the same silhouette. An
  officer and a rating cannot be the same drawing with a 4 px difference.
- White 87 px is 26 percent of the frame, which passes the blob ceiling, but `$0000bc` against the night
  deck is 2.91 and the shapes at that size have no interior line at all.

Fix: give the officer the horizontal collar band plus a 2 px `$28` gold shoulder mark and a 2 px `$0F`
peak on the cap; give the rating the band only. Both in the deck palette `$0F`, `$10`, `$30` per
SPRITE-CRAFT 8.2, both with the same 4 rules as the overworld sailor.

### 3.7 Konrad, Zander, Percy and Hadrian in battle (24 x 32)

| Sheet | Black share | Distinct entries | What is wrong, with coordinates |
| --- | --- | --- | --- |
| `konrad_battle` | 255 of 373 = **68 percent** | 6 | the coat, the trousers and the shoes are one tone from row 13 to row 31; the only interior event is a 3 px skin hand at (17,20) to (19,22); a transparent hole at (16,23); the whole figure is redrawn per frame (frame 0 to frame 2 differ by about 50 px) instead of the legs |
| `zander_battle` | 119 of 373 = 32 percent | 8 | the bomber is 114 px of `$3cbcfc`, which is 31 percent of the sprite and an exact background entry in two scene files (d = 0); the highlight is 1 px of `$a4e4fc` |
| `percy_battle` | 150 of 448 = 33 percent | 8 | jacket `$0000bc` 129 px at 1.00 contrast on the road; **the trident shaft is `$bcbcbc` at columns 20 to 22 rows 12 to 30, and `$bcbcbc` is the deck grey of `scene_battle_deck_night.json` bg2 (1.00)**, so the trident vanishes precisely where Percy fights; 8 entries means 3 of the 4 sprite palettes for one character |
| `percy_god_battle` | 148 of 449 = 33 percent | **11** | 11 entries need ceil(11/3) = **4 sprite palettes, the whole PPU allowance**, leaving nothing for the enemy line (SPRITE-CRAFT 7.4 and ART-BIBLE C15); the sea aura is 2 stray pixels of `$6844fc` at (2,12) and (4,12) |
| `hadrian_battle` | 299 of 365 = **82 percent** | 6 | the highest black share in the project; the white face is 47 px of `$fcfcfc`; the gems are 3 single pixels at rows 16, 17 and 19 |

The fix that applies to all five: the body block gets interior lines (lapel, belt, knee, cuff) at 1 px,
the garment gets a mid tone instead of black, and any colour that equals a declared ground entry is
replaced. The trident in `percy_battle` must be redrawn in `$0F` shaft with `$10` prongs so its head
clears 5.03 : 1 on the deck; the shaft being grey is the single most expensive mistake on that sheet
because the trident is the character.

### 3.8 Konrad and Zander (the two 16 x 16 title sheet characters)

Naming settled 2026-10-22 (card t_e4f8bcae): the two car figures are **Konrad Skye** (driver, front
window on the right) and **Zander Skye** (passenger, rear window). The files were `spr_title_ronan.png`
and `spr_title_theo.png` and are now `spr_title_konrad.png` and `spr_title_zander.png`. Ronan Harrow and
Theo Skye were the superseded Kronos and Zeus picks, judged not adopted in NAMES-BIBLE section 2, so they
are retired names and never characters; the pixel art and the two roles stay.

- **Both are cut in half.** `spr_title_konrad` has its content in rows 8 to 15 only, and row 15 carries
  12 px, so the figure is clipped by the bottom of the cell. `spr_title_zander` has the same: rows 0 to 7
  are empty. A 16 x 16 cell used as 16 x 8 wastes half of the two hardware sprites it costs.
- **Konrad does not animate.** The pixel differences between consecutive frames are `[0,0,0,0,2,3,4]`:
  5 of the 8 frames are byte identical and the movement is 4 px in total.
- **Zander is almost entirely untested geometry**: 2 colours (`$0F` 37 px, `$f8b800` 34 px, 48 percent),
  floating single pixels at (3,8) and (13,8), and one detached black pixel at (12,12).
- **The costumes are stale even after the rename**, because both busts were drawn for the retired designs:
  Konrad wears a flat cap, a grey beard, tweed and driving gloves, and CHARACTER-BIBLE has him at 47 with
  long blond hair streaked white and grey, a close beard and a charcoal blazer or dark knit; Zander wears an
  olive bomber, and CHARACTER-BIBLE says LIGHT BLUE and says "not green" outright. The roles, the pose and
  the wristwatch glance (Konrad's own tell) are right, so the fix is the costume only, and each queue entry
  carries it in its `design_note`.
- Both are static art that sits on top of a scrolling background, so the fix is not the walk cycle: it is
  the frame height (use the full 16 rows), the silhouette and one interior line each.

## 4. The three contradictions inside SPRITE-CRAFT that this card found

The craft file was written in parallel with this one and it anticipated the sailor exactly. Three of its
rules cannot all hold for the same sprite, and a redraw lane will hit all three:

1. **Section 8.3 against section 8.5.** 8.3 budgets the white shirt at 55 to 65 px of about 110 body
   pixels, which is 50 to 59 percent. 8.5 requires the lightest tone under 30 percent and calls anything
   over 45 percent a blob. A white uniform cannot satisfy both. The reconciliation that works: 8.5's
   ceiling applies to the whole figure, so 55 to 65 px of a 224 px sprite is 25 to 29 percent and it
   passes; and with the 8.2 palette split the head's light entry and the body's light entry are
   different entries, so they must be counted separately. This critique uses that reading, and the three
   mocks in section 5 measure 25 to 27 percent on their largest single entry.
2. **Section 8.5 test 3 against section 7.1.** The test counts *dark* runs in the body block, but 7.1
   puts the job colour in the mid slot, so on a light blue bomber the interior line (the zip) is the
   *light* tone and the counter does not see it. The counter should count interior line runs whatever
   their tone. Until it does, Zander's redraw must include at least one genuine dark interior line; the
   mock does, with the pocket and the zip both in `$0F`.
3. **Section 13.3 against section 8.2.** 13.3 puts the trident at column 12 from row 4 to row 13, but
   8.2 splits the palette at row 7 to row 8, so rows 4 to 7 of that trident fall in the head palette,
   where the light entry is skin. A held weapon in the top half needs either a third palette or the
   shorter 7 row trident in the body half. The mock takes the second, and says so.

None of the three blocks a redraw. All three will produce a wrong sprite if they are not decided before
the lane starts.

## 5. The three redraw briefs, with 16 x 16 ASCII mocks

Rules for reading the mocks:

- `.` is palette entry **0**, the transparent slot.
- `1`, `2` and `3` are the three opaque slots of a sprite palette. **Each mock uses exactly 3 colours.**
- Each mock is a two-palette sprite (SPRITE-CRAFT 8.2): rows 0 to 7 are one set of three entries, rows 8
  to 15 another. The symbol to entry table is given per sprite. Slot 1 is the outline tone in both
  halves, which is why the split is invisible to the player.
- All three were measured on the four numbers of SPRITE-CRAFT 8.5. Results are under each grid.

### 5.1 Percy, Royal Navy lieutenant, white shirt order, with the trident

| Slot | Head rows 0 to 7 | Body rows 8 to 15 |
| --- | --- | --- |
| 1 | `$0F` black (`$10` on the night road) | `$0F` black (`$10` on the night road) |
| 2 | `$17` red orange, hair and beard | `$10` light grey, shirt shadow |
| 3 | `$36` skin | `$30` white, the shirt |

```
     0123456789ABCDEF
 0   ....111111......
 1   ...12222221.....
 2   ...12333321.....
 3   ...31133131.....
 4   ...13333331.....
 5   ...12222221.....
 6   ....122221......
 7   ..111333111.....
 8   ..133111331.212.
 9   ..133313331.212.
10   ..133333321.111.
11   ..123333321..1..
12   ..123333321..1..
13   ..111111111..1..
14   ....11..11...1..
15   ................
```

Read it: rows 0 to 6 are the head, 7 rows, hair at rows 0 to 1, skin at rows 2 to 4, the 2 px eyes on
row 3 at columns 5 to 6 and 9 to 10 (the left eye is 1 px wider because column 4 is skin, so the outline
is omitted on the lit side only, SPRITE-CRAFT 5.3), the beard at rows 5 to 6. Row 7 is the shoulder line
with the neck. Rows 8 to 9 are the **collar V** in dark: this is the officer read. Rows 10 to 12 are the
white shirt with a light grey shade on the right column and a dark arm at columns 2 and 10. Row 13 is
the belt, row 14 the legs with the 2 px gap, row 15 empty. Columns 12 to 14 are the trident: light
prongs at rows 8 and 9, a dark crossbar at row 10, a dark shaft at column 13 from row 11 to row 14.

Measured: 3 colours, 132 drawn px, largest single entry 27 percent, 0 rows without a dark pixel, 3 dark
runs in the body block, 13 interior dark pixels. Passes SPRITE-CRAFT 8.5.

Its one honest shortfall: a 7 row trident is shorter than the 9 to 11 px shaft of SPRITE-CRAFT 7.3,
because the 8.2 palette split leaves the body half only. The battle sheet is where the full length
belongs.

### 5.2 A Navy rating (the sailor), white shirt with the navy collar band

| Slot | Head rows 0 to 7 | Body rows 8 to 15 |
| --- | --- | --- |
| 1 | `$0F` black (`$10` on the night road) | `$0F` black (`$10` on the night road) |
| 2 | `$10` light grey, the cap cover | `$10` light grey, shirt shadow |
| 3 | `$36` skin | `$30` white, the shirt |

```
     0123456789ABCDEF
 0   ....122221......
 1   ...12222221.....
 2   ...11111111.....
 3   ...13333331.....
 4   ...31133131.....
 5   ...13333331.....
 6   ....133331......
 7   ..1111111111....
 8   ...133333331....
 9   ...133313221....
10   ...133313221....
11   ...123333121....
12   ...133111321....
13   ...111111111....
14   ....11..11......
15   ................
```

Read it: rows 0 to 1 are the cap cover, row 2 the dark peak, the cap in light grey so it never merges
with the white shirt. Rows 3 to 6 are the face. **Row 7 is the horizontal dark band across columns 2
to 11: the rating's collar.** That one shape is the whole difference from Percy. Rows 8 to 12 are the
white shirt, the 2 px black silk knot at (7,9) to (7,10), the shadow on the right 2 columns, the cuff
at (9,11), the shirt hem at row 12.

Measured: 3 colours, 120 drawn px, largest single entry 27 percent, 0 rows without a dark pixel, 3 dark
runs, 16 interior dark pixels. Passes SPRITE-CRAFT 8.5.

Compared with the sheet in the repo: 83 percent white becomes 27 percent, 2 colours become 3, and the
invisible `$0000bc` outline becomes the `$0F` / `$10` pair that clears 5.03 : 1 on the deck and 6.41 : 1
on the road.

### 5.3 Zander, first year student, light blue bomber

| Slot | Head rows 0 to 7 | Body rows 8 to 15 |
| --- | --- | --- |
| 1 | `$0F` black (`$10` on the night road) | `$0F` black (`$10` on the night road) |
| 2 | `$38` blond, the hair mass | `$21` light blue, the bomber |
| 3 | `$36` skin | `$31` pale blue, the lit plane and the zip |

```
     0123456789ABCDEF
 0   ....1222221.....
 1   ...122222221....
 2   ...223133312....
 3   ...21133131.....
 4   ...13333331.....
 5   ...13333331.....
 6   ....133331......
 7   ..1122222211....
 8   ..1222212221....
 9   ..1222212221....
10   ..1222212221....
11   ..1211212221....
12   ..1122222211....
13   ...11111111.....
14   ....11..11......
15   ................
```

Read it: rows 0 to 2 are the messy blond mass with a dark hairline at (6,2) and (10,2) so the hair has
an interior line and not just a fill. Rows 3 to 6 the face with the 2 px eyes on row 3. Rows 7 to 12 the
oversized bomber, one size too big, with a dark zip at column 7 rows 8 to 11 and a 2 px dark pocket flap
at (4,11),(5,11). Row 13 the waistband, row 14 the legs.

Measured: 3 colours, 127 drawn px, largest single entry 25 percent, 0 rows without a dark pixel, 3 dark
runs, 12 interior dark pixels. Passes SPRITE-CRAFT 8.5.

The palette finding that goes with it: `$21` alone is **1.95 : 1** against the ship deck, under the 2.0
floor, and `$3cbcfc` is an exact background entry in two of our scene files. The mock replaces the fill
with `$31` on the lit plane, which is 3.00 : 1 on the deck and 8.74 : 1 on the road. Zander can then be
read on both maps without a second sprite.

## 6. The check every redraw must pass

Three gates, in this order. The first two are tooling and the third is arithmetic on the palette.

1. `python tools/nes_check.py <sheet.png> --type sprite` must pass. It already does on the current art,
   so passing it is the floor, not the goal.
2. `python tools/nes_composite_check.py <restaged 256x240 frame.png>` must pass, with `--sprite-mask`
   naming the new sheet, and the frame must be restaged on the two real grounds: the deck night strip
   (`game/sprites_src/bg/bg_battle_deck_night.png`) and the night road tiles. Passing on black proves
   nothing.
3. Every opaque colour must clear SPRITE-CRAFT 12.1 against the ground it stands on: outline 3.0 : 1,
   largest fill 2.0 : 1, and no fill may equal a declared background entry (contrast 1.00). This is the
   measurable form of the card's rule that a sprite must differ from the background by at least 2 palette
   steps: on the 2C02 grid, which is 4 brightness rows by 16 hue columns, two steps means
   `|drow| + |dcol|` of 2 or more, and the contrast floor is the same test in luminance. Both numbers are
   in the queue entry for every sprite.

The four blob numbers of SPRITE-CRAFT 8.5 are the fourth gate and they need no tool:
lightest single entry under 30 percent of the drawn pixels; 0 drawn rows without a dark pixel; 3 or more
dark runs in the body block; 8 or more interior dark pixels.

## 7. The `_v2` sheets, measured mid card (08:36 on 2026-10-22)

Five overworld sheets changed on disk while this card was being written (`*_ow_v2.png`, all written at
08:11 today), so the critique above describes the v1 sheets and this section measures what replaced
them. A redraw lane is active; these numbers are a snapshot and must be re-taken before it dispatches.

| Sheet | Colours | Rows with no dark pixel | Largest entry | Outline vs road | Biggest remaining failure |
| --- | --- | --- | --- | --- | --- |
| `percy_ow_v2` | 5 | 0 | 10 percent | 1.73 | its second fill is `$0058f8` at **1.34 : 1 on the deck**; still no trident |
| `sailor_ow_v2` | 4 | 0 | 23 percent (white) | 1.73 | still 33 px of `$0000bc` at **1.00 : 1 on the road** (the collar band) |
| `zander_ow_v2` | 5 | 0 | 14 percent | 1.73 | `$0058f8` 39 px at **1.34 : 1 on the deck** |
| `konrad_ow_v2` | 5 | 0 | 22 percent | 1.73 | 40 px of `$7c7c7c`, the deck grey, at **1.00 : 1** |
| `hadrian_ow_v2` | 3 | 0 | 14 percent | 1.73 | 122 of 152 px is `$000000`, **80 percent black**, the same slab as v1 |

What v2 fixed, in the numbers the v1 critique named: the sailor's 83 percent white blob became 23
percent with a face and 4 colours; all five sheets went from 5 to 14 drawn rows with no dark pixel down
to **0**; the lightest tone on every sheet is under the 30 percent ceiling. What v2 did not fix is the
two cross-cutting failures, and they are the same two on all five:

1. **The outline is still `$0F`.** Against the night road that is 1.73 : 1 where the floor is 3.0. On the
   ship deck the same outline is 5.03 : 1 and correct. No single PNG can be right on both, which is
   SPRITE-CRAFT 5.2 and is why the fix is a room palette remap (`$0F` on the deck, `$10` on the road),
   not another redraw.
2. **The second fill is still a declared background entry.** `$0058f8`, `$0000bc` and `$7c7c7c` are all
   in our own scene files, at 1.00 to 1.34 : 1 against the ground they sit on.

Three god form sheets also exist and were not in the v1 pass: `konrad_god_battle` (9 colours),
`zander_god_battle` (8) and `hadrian_god_battle` (6, and **89 percent** of it is `$000000`). They inherit
the same two failures plus the palette budget one: 9, 8 and 6 entries need 3, 3 and 2 sprite palettes of
the 4 the PPU has.

## 8. What this file does not settle, and who decides

| Open question | Why it matters | How to settle it |
| --- | --- | --- |
| Whether the mocks read as the characters | pixel arithmetic cannot judge a face | the manager renders the three mocks at 3x on the deck and the road and looks |
| The real night road ground colour | SPRITE-CRAFT 12.1 uses `$02` as the assumption; no scene palette file for a road exists in `data/palettes` | read the palette the road map ships with and recompute; the contrast table then fixes the outline entry per map |
| Whether 4 sprite palettes can be spent | `percy_god_battle` already spends 4 (11 entries) and the enemy line needs one | count the palettes the ship battle scene needs on paper before the redraw lane starts |
| Whether the crew needs more than two drawings | the rating and the petty officer are 4 px apart today | Nayil: reuse one crew drawing with a rank mark, or draw two |
| Whether `$000000` in the PNGs is `$0F` or the forbidden `$0D` | both decode to `#000000`, so the PNG cannot prove which; ART-BIBLE C2 and C17 require the key to say `$0F` | the redraw lane writes a colour key per sheet; nothing is invalid about the current files, the proof is just missing |

The last row is worth stating plainly rather than fixing by assumption: every sheet in the repo paints
black as raw `#000000` and no sidecar file names the entry, so nobody can say from the file whether the
forbidden `$0D` was used. `nes_check` accepts it. A colour key per sheet closes it.
