# SPRITE-CRAFT

How real NES RPG overworld sprites are built, measured as numbers, so that our 16 x 16 characters stop looking janky, cutesy and amateur.

Written by research-assistant on 2026-10-22 for card `t_2d71e943` (SPRITE-STUDY-1), after reading PLAN-V2 section 0, ART-BIBLE.md and CHARACTER-BIBLE.md REVISION 2.

The trigger, in Nayil's words: "the overworld character sprites look janky and cutesy, the sailors look like white blobs, it looks amateur". They must read as real NES RPG sprites (Final Fantasy I to III, Dragon Quest I to IV, EarthBound Beginnings / Mother) at 3x on the blue night road and on the ship.

## 0. Rules of this file

- Reference rule (PLAN-V2 section 0): the studied games were looked at and read about. No sprite was downloaded, ripped, traced, recoloured or decompiled. Nothing copied from a game is stored here. Every pixel map in this file is an original design for our own characters, drawn to the numbers the sources give.
- Every number carries a source tag `[S1]` to `[S19]`, resolved with link and read date in section 14.
- Confidence per number, in one of three words:
  - `stated`: the source says it in those terms.
  - `derived`: arithmetic on a `stated` number, or on our own palette file, run by this lane on 2026-10-22.
  - `inference`: a craft judgement this lane is making from the sources plus the 16 x 16 grid. It is a proposal, not a measurement, and it is marked inside the tables.
- The companion data file is `data/sprite_recipes.json`: 57 recipes, each with numbers, sources and a pass or fail check. This document explains them; the JSON is what a tool reads.
- Palette entries are written as `$xx` in PPU index space and resolve through `data/nes_palette.json` (64 entries). Contrast figures are computed on those hex values with the WCAG relative luminance formula, by this lane, `derived` `[S19]`.

## 1. The cell: what a 16 x 16 sprite really is

### 1.1 The arithmetic

| # | Fact | Number | Confidence | Source |
| --- | --- | --- | --- | --- |
| 1 | Cell PLAN-V2 fixes for an overworld character | 16 x 16 px | stated | PLAN-V2 s3 |
| 2 | Tiles the cell is made of | 4, as 2 x 2 of 8 x 8 | derived | S1, S4, S6, PLAN-V2 |
| 3 | Hardware sprites used per pose, 8 x 8 mode | 4 OAM entries | derived | S3 |
| 4 | Hardware sprites used per pose, 8 x 16 mode | 2 OAM entries | derived | S3 |
| 5 | Opaque colours per sprite tile | 3, plus transparent | stated | S2, S6 |
| 6 | Colours in the whole 16 x 16 sprite, worst case | 3 (one palette for all 4 tiles) | derived | S2, S3 |
| 7 | Sprite palettes available on screen | 4, of 4 entries each, entry 0 transparent | stated | S2 |
| 8 | OAM entries available | 64, 8 per scanline | stated | S3 |
| 9 | Scanlines a 16 x 16 sprite covers | 16, in two 8 px bands | derived | S3 |
| 10 | 16 x 16 characters side by side on one band before dropout | 4 (8 slots / 2 objects per band per character) | derived | S3 |
| 11 | Free transforms on an object | horizontal flip, vertical flip, no rotation | stated | S3 |

Three consequences that decide everything else:

1. **A sprite is one palette.** The four tiles of a 16 x 16 character share a 3 colour budget unless you deliberately split the character into two objects with different palette bits. That split is legal per object (§8.1) and it is the fix for white uniforms.
2. **Transparency is the fourth colour,** so the outline cannot be "the background showing through"; the outline must be one of the three opaque colours, and it competes with skin and clothing for those slots.
3. **The 16 x 16 cell is two 8 px bands,** so a sprite can be split horizontally into a head half and a body half that differ in palette without any seam, because the PPU has no idea the halves belong together.

### 1.2 The working area inside the cell

`inference`, from flip symmetry and from the 1 px outline rule:

| Margin | Pixels | Why |
| --- | --- | --- |
| Left and right | 1 px each | the figure spans columns 1 to 14 (14 px), so a horizontal flip mirrors it into the same footprint |
| Top | 0 or 1 px | hair may touch row 0, but a 1 px top margin stops the head merging with the tile above on a busy map |
| Bottom | 1 px | row 15 stays transparent so the feet have something to stand on and the sprite does not merge with the ground tile |

So the drawable figure is **14 px wide by 15 px tall**, not 16 x 16. Every proportion below is measured against 14 x 15 and then reported against the cell.

## 2. Proportion: two body plans, and when to use each

Two plans cover the studied games. Both fit the 14 x 15 working area. The difference is where the head sits and how much torso exists.

### 2.1 Plan A, the FF1 to FF3 style figure (head to body about 1:1.2)

| Rows | What they hold | Pixels |
| --- | --- | --- |
| y0 to y1 | hair mass and its 1 px outline; the top of the head | 2 |
| y2 to y5 | face, 4 rows; the eyes sit on y3 | 4 |
| y6 | jaw and chin line, narrowing to 4 px | 1 |
| **y0 to y6** | **the head, 7 rows** | **7** |
| y7 | neck and shoulder line, shoulders span 10 px | 1 |
| y8 to y12 | torso and arms, 5 rows | 5 |
| y13 | belt line, 1 px dark | 1 |
| y14 | legs and feet | 1 |
| **y7 to y14** | **the body, 8 rows** | **8** |
| y15 | empty, ground contact | 1 |

Head 7, body 8, so head to body is **1:1.14**. The card's target is 1:1.2; the grid cannot give 1.2 to one decimal at this size, and 7:8 (1.143) or 6:7 (1.167) are the two nearest exact ratios. Take **7:8** and accept 1.14. `inference` from the 16 row budget `[S1]`, matching the card's stated target.

### 2.2 Plan B, the Dragon Quest and Mother style figure (2 heads tall)

| Rows | What they hold | Pixels |
| --- | --- | --- |
| y0 to y6 | the head, 7 rows, 8 to 9 px wide, so it is wider than the shoulders | 7 |
| y7 | a 1 px neck line, or none if the head sits straight on the shoulders | 1 |
| y8 to y13 | the body, 6 rows, 7 to 8 px wide | 6 |
| y14 | feet | 1 |
| y15 | empty | 1 |

Head 7, body 7, so head to body is **1:1.0** and the figure is **14 rows tall, exactly 2 heads**. `derived` from the row budget; the 2 heads tall shape matches the descriptions of the early Dragon Quest look `[S13]` and the super deformed ("SD", super deformed) large head and large eye convention in Final Fantasy pixel art `[S14]`.

### 2.3 Which plan, and why the choice is not taste

| Situation | Plan | Reason |
| --- | --- | --- |
| Player avatar on a map where you read clothing and class | A (1:1.14) | the 8 rows of body are the only place a uniform, a coat or a rank stripe can exist at all |
| NPC crowd, town, 20 or more figures on screen | B (2 heads) | a bigger head reads at 3x from across the room, and Plan B spends 7 of 15 rows on identity instead of 7 of 15 on legs |
| A character whose face matters more than the outfit (children, Mother style modern clothes) | B | a 9 px wide head holds 1 px eyes plus hair shading; a 7 px head does not |
| Navy officer, soldier, anyone whose rank or uniform is a story point | A | rank is a 2 px detail on a shoulder; Plan B has no shoulders to put it on |
| Final boss of the family, god form | A with the body widened to 10 px at the shoulders | width reads as authority; height reads as childish |

`inference`. The trap that produces "cutesy" is using Plan B for everyone: two heads tall is a child's proportion, and a cast of six adults all drawn two heads tall reads as a toy set. The trap that produces "janky" is using Plan A badly, with the head too narrow for the face, which is §3.

### 2.4 The width ladder

`inference`, measured against the 14 px working width:

| Part | Width in px | Columns |
| --- | --- | --- |
| Head, Plan A | 7 to 8 | 4 to 11 |
| Head, Plan B | 8 to 9 | 4 to 12 |
| Shoulders | 10 | 3 to 12 |
| Torso | 8 | 4 to 11 |
| Hips | 7 | 4 to 10 |
| Each leg | 2 | 5 to 6 and 9 to 10 |
| Gap between legs | 2 | 7 to 8 |

The 2 px gap between the legs is load bearing: close it and the figure reads as a dress or a blob, which is one of the amateur mistakes in §11.

## 3. The head at 16 px

| # | Rule | Number | Confidence |
| --- | --- | --- | --- |
| 1 | Head silhouette width, Plan A | 7 to 8 px | inference |
| 2 | Head silhouette width, Plan B | 8 to 9 px | inference |
| 3 | Hair outline thickness, on every edge of the hair | 1 px, in the palette's dark tone | stated (1 px lines) S15, inference for the hair |
| 4 | Skin area inside the hair outline | 5 to 6 px wide, 4 rows | derived from 1 and 3 |
| 5 | Eyes | 2 px each, drawn as 1 x 2 or 2 x 1 | stated S16 |
| 6 | Gap between the eyes | 2 px (the nose bridge) | inference |
| 7 | Mouth | none by default; 1 px if the pose needs a beat | inference, card |
| 8 | Rows the head occupies | 7 | derived, s2.1 |
| 9 | Dark pixels on the head | 12 to 18 of the 56 to 64 head pixels | inference |

The head is the whole game at this size. The order of work that the sources support:

1. **Block the silhouette before any detail.** `stated` `[S16]` (Pixnote, via the Pine result): test the filled silhouette first, include the weapon in it.
2. **Hair first, then face.** The hair is the largest dark mass and it defines the head's shape. Draw the hair as a 1 px outline plus 1 to 2 rows of fill, then carve the face out of it.
3. **The 1 px hair outline is what stops the head reading as a ball.** Without it, a 7 px circle of skin with two eye dots *is* a ball, and a ball on a rectangle is the cutesy look.
4. **Two hairline pixels minimum.** A vertical 1 px of dark down the side of the face (sideburn) at column 4 or 11 tells the eye that the face is a plane facing us, not the front of a sphere.
5. **Eyes are 2 px and sit on row 3 of the head,** one row below the hair mass. `stated` 2 px eyes `[S16]`; the placement is `inference`.
6. **Never outline the eyes on all four sides at this size.** A 2 px eye with a 1 px dark fringe is a 4 px blob. Place the eye colour directly, with skin around it.

At 3x (48 x 48 on screen) a 2 px eye is 6 px wide, which is plenty; a 1 px eye becomes a 3 px speck and disappears into the hair. That is why 2 px is the floor, and why 3 px eyes (common on SNES) are wrong here: 3 px eyes plus 2 px gap plus 1 px margins is 8 px across a 7 px head, so something has to give and the head widens into a balloon.

## 4. Directions and the walk cycle

### 4.1 Eight poses from six drawings

| Pose | Drawn or derived | Cells | Notes |
| --- | --- | --- | --- |
| Down, frame 0 | drawn | 1 | the pose the player sees most |
| Down, frame 1 | drawn | 1 | leg swap |
| Up, frame 0 | drawn | 1 | no face; hair covers rows 0 to 5 |
| Up, frame 1 | drawn | 1 | leg swap, and the body rows may be reused from Down |
| Right, frames 0 and 1 | drawn | 2 | true side view with a 2 px stride |
| Left, frames 0 and 1 | **derived by OAM horizontal flip** | 0 | bit 6 of the attributes byte `[S3]` |

Total drawn cells: **6**. Total poses: **8**. Total hardware tiles: 6 x 4 = **24** of the 256 in a pattern table. `derived` `[S1]`, `[S3]`.

That is the standard NES answer and it is also the honest one: sprite flipping is a hardware transform, not a trick `[S3]`, and the Castlevania analysis records the same economy of reuse, with frames built from smaller tiles and tiles reused across frames `[S10]`, `[S12]`. Where a game goes past two frames it is usually 3, ping ponged, or 4 drawn frames, and the drawn-frame count is a feel decision: the same artist who shipped 4 frames per direction reported that 3 frames looked mechanical `[S11]`, `[S13]`.

Dragon Quest 1 goes further and does not even draw sides: it has a front facing only, and fakes its two frame cycle by mirroring a symmetric figure `[S7]`. That is the absolute floor of the craft and it is why early Dragon Quest characters look like waddling dolls. Our game needs four directions.

### 4.2 What changes between frame 0 and frame 1

The amateur version redraws the whole figure and the two frames fight each other. The correct version changes few pixels, in the right rows.

| View | Rows that change | Pixels changed | Percent of the figure | What moves |
| --- | --- | --- | --- | --- |
| Down | y13, y14 | 6 to 10 | 4 to 6 percent of 224 drawn pixels | one leg advances 1 px, the other retracts 1 px |
| Up | y13, y14 | 6 to 10 | same | same, mirrored logic |
| Side | y13, y14, plus y8 to y9 for the arm | 10 to 16 | 7 to 10 percent | front leg 2 px forward, back leg 2 px back, arm swings 1 px |

`inference`, from the 2 frame convention `[S13]` and the 2 px stride that reads at 3x. Three rules that follow:

1. **The torso never changes.** Rows y7 to y12 are byte identical between the two frames. Anything else is a second drawing, not an animation.
2. **The head never bobbles at 16 px.** A 1 px vertical bob costs a whole row of head detail and, on a 2 frame cycle, reads as a stutter rather than a step. Bob only if the game has 4 frames.
3. **The step must be visible in the silhouette.** If the two frames have the same silhouette, the walk is invisible and the character looks like it is sliding. The test: fill the figure in one colour, and the outline of frame 0 and frame 1 must differ by at least 2 px on the outer edge.

### 4.3 Frame timing

| Number | Value | Confidence |
| --- | --- | --- |
| Game frames each pose is held | 8, about 0.133 s at 60 Hz | inference |
| Pose changes per second | 7.5 | derived |
| Full cycle (2 poses) | about 0.27 s | derived |

`derived` from 60 frames per second. Tune between 6 and 10 frames per pose: under 6 the walk vibrates, over 10 it looks like it is wading. A 2 frame cycle held at 8 frames per pose is roughly the Dragon Quest feel; holding at 12 or more is the "always animated, slowly" feel that the Zeboyd account describes as making squat, big headed sprites feel alive `[S13]`.

### 4.4 The mirror problem, and what to do about it

Flipping is free but it flips the light too. If the light comes from the top left, the right facing sprite is lit from the top right, so Percy's right facing and left facing frames disagree about where the moon is.

Three fixes, in order of cost:

| Fix | Cost | Result |
| --- | --- | --- |
| Light the figure from straight above, with the shade only on the bottom 2 rows | 0 extra cells | mirror is nearly invisible; the figure reads a little flat |
| Keep top left light and accept the flip | 0 extra cells | visible if the player holds one direction and looks; most NES games did this |
| Draw the left frames separately | 2 extra cells, 8 extra tiles | correct light; only worth it for a hero who is on screen for hours |

`inference`. This project should take fix 1 for NPCs and the sailors, and fix 3 for nothing at this stage; the manager can revisit if the flip is visible on the night road.

## 5. Outline rules

| # | Rule | Number | Confidence |
| --- | --- | --- | --- |
| 1 | Outline thickness, standard | 1 px, never 2 | stated S15 (reduce every line to a single pixel), inference at 16 px |
| 2 | Outline colour | the palette's dark tone, which is not always black | derived s5.2 |
| 3 | Selective outline | drop the outline on the 1 px lit top left edge only | inference |
| 4 | Interior lines | 1 px, at the collar, the belt, the sleeve seam, the jaw | inference |
| 5 | Outline on the bottom edge | always, unless the background is darker than the outline | derived s12.1 |
| 6 | Minimum contrast of the outline against the ground it stands on | 2.5 : 1 | inference from the measured table in s12 |

### 5.1 Why 1 px and not 2

A 2 px outline on a 14 px wide figure eats 4 px of the 14, which is 29 percent of the figure's width spent on nothing. At 3x, a 2 px outline is a 6 px black band, and the sprite reads as a sticker with a border. Derek Yu's tutorial builds every sprite by reducing each line to one pixel and cleaning jaggies `[S15]`; that discipline is the difference between "pixel art" and "a small drawing".

### 5.2 The outline colour is per palette, not always black

The line that reads as an outline depends on what it sits against. Measured on our palette, contrast ratio against a navy road (`$02`, relative luminance 0.036) `[S19]`:

| Candidate outline | Entry | Contrast against the navy road | Verdict |
| --- | --- | --- | --- |
| Black | `$0F` #000000 | **1.73** | nearly invisible: the black outline and the night road are both almost black |
| Grey | `$00` #7c7c7c | 2.91 | usable |
| Light grey | `$10` #bcbcbc | 6.41 | strong, reads as a rim rather than an outline |
| Navy | `$02` #0000bc | 1.00 | invisible |

And against a grey ship deck (`$00`, luminance 0.202) `[S19]`:

| Candidate outline | Entry | Contrast against the grey deck | Verdict |
| --- | --- | --- | --- |
| Black | `$0F` | **5.03** | the strongest thing on the deck, use it |
| Navy | `$02` | 2.91 | usable |
| Light grey | `$10` | 2.20 | too weak |

So the same character needs **two different outline tones on two different maps**, which means the outline colour is a property of the room palette, not of the sprite. The toolchain defaults make this easy to check: black is `$0F` and white is `$30` `[S5]`, so a scene that wants a black outline on the road has to be changed deliberately, not by accident. This is the concrete answer to "readable at 3x on the blue night road and the ship": on the ship, outline in `$0F`; on the night road, outline in `$00` with a 1 px `$10` rim on the lit side, because `$0F` gives 1.73 and disappears.

This mirrors a documented NES practice from a different game with the same problem: Simon in Castlevania has a dedicated palette with no black in it while the enemies' palettes do hold black, and that difference is why he reads clearly against the backgrounds `[S12]`. The palette is a readability decision, not a decoration.

### 5.3 Selective outlining

Drop the outline only where the figure's edge is the lit edge: the top of the hair, the top of a shoulder, the outer edge of a sleeve, all on the top left. Keep it on the bottom, the right and every interior boundary. The effect is that the sprite looks lit from outside instead of drawn with a pen, and it costs no extra colour, because the pixel that would have been outline becomes the light tone.

The rule with a number: **at most 3 of the ~40 outline pixels on a 16 x 16 figure are omitted.** Omit more and the silhouette collapses, which is the "single flat blob" mistake in §11.

### 5.4 Never outline every side evenly

An even outline on all four sides of every part is the single most common amateur tell: it flattens the figure and it makes the sprite look like a sticker. The three fixes:

- outline the parts that overlap other parts (arm over torso, hat over hair) and not the parts at the outer edge;
- omit the outline where a lit edge meets the background;
- use the mid tone, not the dark, for an interior boundary between two similar materials (shirt against trousers on a grey deck).

## 6. Shading: palette steps, never dithering

### 6.1 Why no dithering

Dithering is a checkerboard of two colours that reads as a third at a distance. It was the main shading tool on machines with 2 to 16 colours and large sprites, and Derek Yu's tutorial presents it as an advanced technique for exactly that case `[S15]`. It is wrong here for three reasons with numbers:

1. **There are only 3 opaque colours.** A checkerboard spends 2 of the 3 on one apparent tone, leaving 1 for everything else, so a dithered 16 x 16 sprite is a two tone sprite.
2. **The checkerboard is 1 px.** At 3x, a 1 px checkerboard is a 3 px pattern which reads as texture, not as shading, and the eye reads it as noise at exactly the size the sprite is drawn for.
3. **A 16 x 16 figure has about 224 drawn pixels.** A shading band is 8 to 20 pixels of those. A dither of 8 pixels is not a band, it is four dots.

`inference`, plus `[S15]` on what dithering is for. The rule: **zero dithered pixels inside a character sprite.** Dither belongs to background gradients only.

### 6.2 The three step ramp

| Step | Role | Typical NES entries | Measured luminance |
| --- | --- | --- | --- |
| dark | outline, hair, boots, the shadow side | `$0F`, `$02`, `$0C` | 0.00 to 0.04 |
| mid | the largest garment area, the job colour | `$00`, `$12`, `$16`, `$1C`, `$28` | 0.14 to 0.54 |
| light | skin, the lit plane, the highlight | `$10`, `$30`, `$36`, `$31` | 0.50 to 0.97 |

`derived` `[S19]` for the luminances; `stated` for the base, shadow and highlight three tone structure `[S14]`, `[S16]`.

The step between adjacent tones is what makes three colours read as a form. Two tones that are 0.02 apart in luminance cannot shade anything; the measured gap you want is **at least 0.15 of relative luminance between adjacent steps.** Examples that pass on our palette: `$0F` 0.00, `$10` 0.50, `$30` 0.97 (steps of 0.50 and 0.47). Examples that fail: `$10` 0.503 against `$20` 0.939 is 0.44 apart, fine, but `$00` 0.202 against `$2D` 0.188 is 0.014 apart, so those two are the same tone to the eye and one of them is wasted.

### 6.3 Where the shade goes

Light from the top left, always, and then the shade is:

| Location | Pixels | Why |
| --- | --- | --- |
| The right 1 px column of the torso | 5 to 6 | the side away from the light |
| The bottom 1 px row of the torso | 7 to 8 | the underside |
| Under the chin, 1 px, 3 to 5 px wide | 3 to 5 | the head casts on the neck |
| Under the arms, 1 px, 2 to 3 px each | 4 to 6 | the arm casts on the torso |
| Under the belt, 1 px, 7 px wide | 7 | the belt casts on the hips |
| The back leg, whole | 6 to 8 | the leg behind the body |

Total shaded pixels: **30 to 40 of ~224**, so about 15 percent. Over 25 percent shading and the figure turns muddy at 3x; under 10 percent and it is flat. `inference`.

### 6.4 Pillow shading, named so it can be rejected

Pillow shading is shade on every edge and light in the middle, as though the figure were inflated. It is symmetrical, it ignores the light direction, and it makes a 16 x 16 character look like a cushion. The test: **on any horizontal row of the torso, the shade must be on one side only.** If a row has shade at both ends and light in the middle, delete one end.

## 7. Class identity in three colours

With 3 opaque colours the class cannot be carried by colour variety. It is carried by two things: **which of the three tones the garment gets**, and **the silhouette**.

### 7.1 Which tone carries the job colour

| Slot | What goes in it | Rule |
| --- | --- | --- |
| dark | outline, hair, boots, and the shadow side of the garment | always the darkest thing present |
| mid | the garment's main area, in the job colour | 40 to 60 percent of the drawn pixels |
| light | skin, and the lit plane of the garment if the garment is pale | never both at full area |

`inference`. The failure that produces a muddy class: putting the job colour in the light slot and skin in the mid slot. Then the face is a mid tone and the coat is a highlight, the two compete for attention, and the character reads as "a person with a bright coat" rather than "the Red Mage".

### 7.2 The silhouette devices, one per class

| Device | Pixels of extra silhouette | Reads as | Where it goes |
| --- | --- | --- | --- |
| Pointed or floppy hat | 3 to 6 px, 2 to 4 rows above the head | mage, wizard | rows y0 to y1, breaking the head outline |
| Hood | 0 extra height, 1 to 2 px wider than the head | cleric, white mage | rows y2 to y6, covering the hair |
| Cape | 2 to 4 px wider at the shoulders, tapering to the hip | noble, dark knight | columns 2 to 3 and 12 to 13 |
| Weapon at rest | 1 px shaft, 2 px head | fighter, knight, officer | beside the outer arm, breaking the outline |
| Bare arms | remove 2 px of sleeve | monk, brawler | columns 3 to 4 |
| Bandana | 1 px dark row across the forehead | thief | row y2, 5 px wide |

`inference`. The supporting claim is sourced: the Black Mage of Final Fantasy is described as a silhouette with two glowing eyes and nothing else, "a masterclass of less is more" `[S14]`, and the silhouette test (fill the sprite black; if you can still tell who it is, the design works) is the same article's recommendation. Final Fantasy I does the same job with height instead of shape, redrawing each class sprite taller at the class upgrade `[S8]`, and the series is credited with putting the party on the right of the battle screen instead of a first person view `[S9]`, which is a reminder that a class has to read from a standing figure with no animation at all.

### 7.3 The weapon is part of the silhouette, and it costs pixels

| Part | Pixels |
| --- | --- |
| Shaft | 1 px wide, 9 to 11 px long |
| Head (trident, spear, staff) | 2 to 3 px wide, 2 to 3 px tall |
| Where it sits | against the outer arm, so it changes the outer edge of the figure |

`stated` for the 1 px shaft and 1 to 2 px for the head `[S16]`; `inference` for the length. A weapon drawn *inside* the body outline costs pixels and reads as nothing.

### 7.4 Palettes must differ from the enemies'

ART-BIBLE check C15 already requires it, and the Castlevania evidence explains why: Simon has a palette without black while the enemies' palettes hold black, and that is what makes him the clearest object on the screen `[S12]`. For us: the player's palettes and the NPC palettes must not be able to draw the same 3 tones as the enemy palettes.

## 8. Uniforms, white clothing, and the end of the white blob

This is the section the sailors need. Nayil's complaint is exact: "the sailors look like white blobs". The blob has a measurable cause and a fixed solution.

### 8.1 The cause, with numbers

A white garment drawn as a single fill in the light tone has **no interior structure and no boundary**. Measured on our palette `[S19]`:

| Pair | Contrast | What it means |
| --- | --- | --- |
| white `$30` against light grey `$10` | 2.02 | the shirt and its own shadow are almost the same tone |
| white `$30` against the grey deck `$00` | 4.07 | the fill reads, but there is no line where the figure ends |
| white `$30` against the navy road `$02` | 11.86 | the fill screams; on the night road a white blob is the brightest object on the screen |

So on the deck a white figure has contrast for its fill and none for its edge, and on the night road it has too much fill contrast and no edge. Both cases read as a blob, for opposite reasons.

### 8.2 The fix 1: split the character across two palettes

The PPU selects a palette per OAM entry, not per character `[S2]`, `[S3]`. A 16 x 16 character in 8 x 8 mode is 4 entries, so the top two tiles (rows y0 to y7) can use palette A and the bottom two (rows y8 to y15) can use palette B, with no seam the player can see, because the split line is exactly the jaw and collar line where a real costume already changes.

| Palette | Entries | Used for |
| --- | --- | --- |
| Head palette (5) | `$0F` black, `$16` red orange or `$17` orange brown for hair and beard, `$36` skin | rows y0 to y7 |
| Uniform palette (6) | `$0F` black, `$10` light grey, `$30` white | rows y8 to y15 |

Cost: 2 of the 4 sprite palettes for the player character, leaving 2 for all NPCs and enemies on that map. That is affordable for a game with one visible NPC type at a time and it is the only way to get 3 tones for the shirt **and** 3 tones for the beads and skin.

`derived` from `[S2]`, `[S3]`. This trick is the direct application of the Castlevania finding that a dedicated palette is what makes a hero read `[S12]`.

### 8.3 The fix 2: spend the shirt in three tones with counts

For a 14 x 12 body block (about 110 drawn pixels), the white shirt is:

| Tone | Pixels | Location |
| --- | --- | --- |
| white `$30` | 55 to 65 | chest, the top of the sleeves, the top of the cap cover |
| light grey `$10` | 20 to 25 | right 1 px column, under the arm, under the collar, the lower 1 px of each sleeve |
| dark `$0F` | 15 to 22 | outline, collar, cuff bands, belt, cap brim, trouser tops |

`inference`, consistent with `stated` 3 tone ramps `[S16]` and with the rule that one lightest colour is a highlight, not a fill `[S14]`.

### 8.4 The fix 3: the details that name the garment

Each of these is 1 to 3 px and each one converts "white shape" into "naval uniform":

| Detail | Pixels | Position | Why it reads |
| --- | --- | --- | --- |
| V collar in the dark tone | 2 px band, 2 px deep, in a V from the shoulders to the sternum | y7 to y8, columns 6 to 9 | a dark V on a white ground is the strongest shape available at this size |
| Collar tab | 1 px dark, 2 px wide, each side of the V | y7 | reads as a shirt collar rather than a hole |
| Cuff band | 1 px dark across each sleeve | y11 | separates hand from sleeve |
| Belt | 1 px dark across the waist, with 1 px gold `$28` buckle | y13 | gives the body a middle; without it the torso is a tube |
| Cap | 1 px dark brim, 2 px light cover | y0 to y1 on a Plan A head | changes the head silhouette, which is the cheapest identity in the game |
| Trouser break | 1 px dark at y13 between the two legs | y13, columns 7 to 8 | stops the legs merging into one white column |

`inference`. This is the answer to "use the palette's light grey plus the dark outline plus one mid tone, a 1 px darker shade on one side, a contrasting cap, collar and belt", with counts attached.

### 8.5 The blob test

A pass or fail check that needs no vision model:

1. Count the pixels in the lightest tone of the sprite. **Must be under 30 percent of the drawn pixels** on a sheet that carries four entries. **On a three entry sheet, which is the only legal case below, it must be under 45 percent**, which is the blob line stated in this same sentence, and the dark entry must own at least 30 percent instead. A blob is over 45 percent whatever else the sheet carries.
2. Count the number of horizontal rows that contain **no** dark pixel. **Must be 0.** A row with no dark pixel is a row where the figure has no structure at all.
3. Count the number of **distinct vertical runs of dark** in the body block, read as a column scan down the body's midline, from row 8 to row 15. **Must be at least 3** (for example: collar, belt, trouser break). A blob has 1 or 2.
4. Count the dark pixels inside the body block that are **not** on the outer edge. **Must be at least 8.** Those are the interior lines, and interior lines are what stop a silhouette reading as a blob.

`inference`, all four measurable on our own PNG output by `tools\inspect_frame.py` or a 20 line script.

**Amendment, gamedev ruling on card t_a44ae3db (2026-10-24).** A 16 x 16 cell spends one sprite palette of three (ART-BIBLE RULE 0 point 3, hardware rule 16 in section 1), so a sheet cannot carry four entries without claiming a second sprite palette, and palette first refuses that. The four numbers above are therefore read like this, and they are what `tests/test_make_characters_v2.py` asserts on the down idle frame:

| What is counted | Gate | Sailor, 3 entries (shipped 2026-10-24) | The v1 white blob, `sailor_ow.png` |
| --- | --- | --- | --- |
| entries in the 16 x 16 cell | exactly 3, all three spent | 3 | 2, FAIL |
| check 1, lightest share of drawn pixels | under 45 percent (30 is the four entry margin) | 37.5 percent | 83.3 percent, FAIL |
| dark share of drawn pixels, the counterweight | at least 30 percent | 40.8 percent | 16.7 percent, FAIL |
| check 2, rows with no dark pixel | 0 | 0 | 9, FAIL |
| check 3, midline dark runs, rows 8 to 15 | at least 3 | 3 | 0, FAIL |
| check 4, interior dark pixels | at least 8 | 10 | 0, FAIL |

Why the ceiling moved rather than the drawing: on a three entry sheet the light tone carries the jumper and the face, because skin is the entry a white uniform costs at this palette size, so the light tone is a fill by design and the 30 percent margin (written for a sheet where a mid grey shaded the cloth) cannot be met by a white uniform at all. The dark share floor and check 3 take over the job the ceiling was doing, and the v1 blob fails five of the six numbers, so nothing was made cheap. The ten percent of colours the four entry sheet had (ink, white, navy, skin) bought it a second sprite palette on every scanline, which is the palette first defect card t_bd5cfad5 removed. A future crew that wants flesh tones gets them from a scene palette with a skin entry, budgeted at scene level, not from this sheet.

## 9. Faces at 16 px

| Feature | Rule | Numbers |
| --- | --- | --- |
| Eye | 2 px, dark, at row 3 of the head | 2 x 1 or 1 x 2 |
| Eye gap | 2 px | the nose bridge |
| Brow | optional, 1 px dark above each eye at row 2, only on an angry pose | 2 px |
| Mouth | none by default | 0 px |
| Mouth, when needed | 1 px dark, under the nose, only at 3x | 1 x 1 |
| Nose | never drawn, or 1 px mid tone | 0 to 1 px |
| Jaw line | 1 px dark, 3 to 5 px wide, at row 6 | 3 to 5 px |
| Blush, sweat, emotion | 1 px accent, one side only, on the cheek | 1 px |

`stated` 2 px eyes and the 1 x 1 or 1 x 2 or 2 x 1 shapes `[S16]`; the rest `inference`. The one rule to keep: **the mouth is optional and the eyes are not.** At 16 px, a mouth drawn as a 1 px line under a 2 px pair of eyes adds an expression the walk cycle cannot animate, and on a 2 frame cycle it flickers between frames if it is redrawn. Leave it out for the walk, and use it only in a fixed pose (a cutscene close up).

## 10. How Mother's ordinary modern clothes read

EarthBound Beginnings / Mother puts children in T shirts and shorts on a modern American map. The sprites are the same 16 x 16 cell, and the sheet index at The Spriters Resource lists walk cycles by direction (down, left, right, up) for each character `[S17]`. Nothing was downloaded; the sheet naming is the source for the structure.

The craft problem is the opposite of the sailor's: with no uniform, there is no shape handed to you. What carries the read:

| Element | Pixels | Why it works |
| --- | --- | --- |
| Hair as the identity | 3 to 5 rows, 1 to 2 tones | mother's cast is identified by hair shape and colour, because the clothes are generic |
| T shirt as a flat block | 4 to 5 rows, 1 tone plus 1 shade | a plain shirt must be *flat*, with the shade only at the right column and under the arm |
| Shorts as a second block with a hard line | 2 rows, dark | the waistline is the only structural event on the figure; without it the body is a tube |
| Socks and shoes | 1 row, light then dark | two 1 px values at the bottom give the figure a base |
| Skin as the light tone | face and arms | modern clothes are dark or mid, skin is light: that is what stops the shirt and the skin merging |
| One accent only | 1 to 3 px | a stripe, a shoe colour, a cap. One. |

`inference`, anchored to the 16 x 16 cell `[S17]` and to the general three tone structure `[S14]`.

The specific failure mode for modern clothes: drawing the shirt in the light tone, which makes the shirt and the skin the same value and the character a white blob with a head. In a modern scene, **the clothes own the mid and dark tones and the skin owns the light tone.**

## 11. The mistakes that look amateur, each with the number that fixes it

| # | Mistake | Why it looks wrong | The fix, as a number |
| --- | --- | --- | --- |
| 1 | Even outline weight on every side of every part | flattens the figure, reads as a sticker | omit the outline on the 1 px lit top left edge; at most 3 of ~40 outline pixels |
| 2 | Pillow shading (shade all edges, light in the middle) | symmetrical, no light direction | shade on one side per row; 30 to 40 shaded pixels out of ~224, all on the right and bottom |
| 3 | Symmetric stiff pose (arms straight down, both feet level, head dead centre) | "like a robot", the documented complaint about most RPG standing frames | offset one arm by 1 px, put the feet on different rows in frame 1, shift the head 0 to 1 px off centre |
| 4 | Mixed pixel sizes (a 2 px detail next to a 1 px detail, or a stray 1 px dot that is really a 2 px shape) | the eye sees two grids at once | every feature is 1, 2 or 3 px and every edge lands on the 1 px grid; no single isolated pixel unless it is an eye or a highlight |
| 5 | Too many colours (4 or more in a tile, or per-tile palettes that drift) | hardware illegal, and the eye reads noise | 3 opaque colours per tile, 3 per sprite unless the head and body palettes are split deliberately |
| 6 | Single flat blob (one tone, no interior lines) | no structure, and it is exactly the sailor complaint | 8 or more dark pixels *inside* the body block; 0 rows without a dark pixel |
| 7 | Jaggies (a 1 px step in the middle of a straight edge) | reads as a badly scanned drawing | every straight edge is a run of 2 or more px; a diagonal steps in a consistent 1-1-2 or 2-2-1 pattern `[S15]` |
| 8 | Cutesy proportions applied to adults | 2 heads tall is a child | Plan A (7 head rows, 8 body rows) for every adult who is not a comedy NPC |
| 9 | Head too small for the face, or a 1 px eye | the face cannot be drawn at all | head 7 to 8 px wide, eyes 2 px |
| 10 | Feet with no ground contact | the sprite looks like it is floating | feet on row 14, row 15 empty, the ground shadow drawn by the map |
| 11 | Shading the whole figure at 45 percent | muddy at 3x | 15 percent shaded, and only on the right and bottom |
| 12 | Clothes and skin in the same tone | the uniform merges into the face | skin and garment must be on different steps of the ramp, or split the palettes (§8.2) |

## 12. Readability at 3x on the blue night road and the ship

The card's requirement is concrete, so the check is concrete. At 3x, one sprite pixel is 3 screen pixels, and the figure is 48 x 48 on screen.

### 12.1 The contrast floor

| Rule | Number | Confidence |
| --- | --- | --- |
| Minimum contrast between the figure's outline and the ground it stands on | 3.0 : 1 | inference |
| Minimum contrast between the figure's largest fill and the ground | 2.0 : 1 | inference |
| Maximum contrast inside the figure | 12 : 1 (white against black) | derived from `[S19]` |

The ground colours to measure against (both are project facts this lane must not invent, so they are stated as the two cases the card names):

| Ground | Assumed colour | Luminance | Best outline | Its contrast | Best fill |
| --- | --- | --- | --- | --- | --- |
| Night road, dark blue ground | `$02` #0000bc | 0.036 | `$10` #bcbcbc, or `$00` #7c7c7c as a softer edge | 6.41, or 2.91 | `$30` 11.86, `$31` 8.74, `$36` 8.32 |
| Ship deck, grey steel | `$00` #7c7c7c | 0.202 | `$0F` #000000 | 5.03 | `$30` 4.07, `$20` 3.93, `$31` 3.00 |

`derived` `[S19]`. The manager should confirm the actual road and deck colours from the map data; the recipe holds for any ground whose luminance is under 0.10 (dark) or between 0.15 and 0.30 (mid grey), which covers both.

### 12.2 The palette consequences, per map

| Map | Forbidden in the sprite | Required | Reason |
| --- | --- | --- | --- |
| Night road | navy `$02` (contrast 1.00), mid blue `$12` (2.17), blue `$01` (1.39), dark teal `$0C` (1.09) | a light fill (`$30`, `$31`, `$36`, `$10`) and a non black outline (`$00` or `$10`) | blue on a blue road is an invisible character; a black outline at 1.73 is a merged one |
| Ship deck | red orange `$16` (1.10), teal `$1C` (1.03), light blue `$22` (1.30), mid blue `$12` (1.34), mid grey `$2D` (1.06) | a black outline `$0F` (5.03) and a fill of `$30`/`$20`/`$31` | on grey, only very light or very dark separates; saturated mid tones vanish |

Both tables are arithmetic, not opinion, and they are the most useful thing in this file: **the same sprite cannot serve both maps with one palette, and the fix is a second sprite palette per map, not a redraw.**

### 12.3 The 3x checks

| Check | Pass condition |
| --- | --- |
| Silhouette test | fill the figure in one colour; the outline is still identifiable as that character |
| Squint test | at 3x on the actual map, the figure's head and feet are separable from the ground without moving closer |
| Edge test | walk the sprite onto the darkest and the lightest ground tile of each map; in both cases the outline is visible along the bottom 4 px |
| Frame test | the frame 0 and frame 1 silhouettes differ by at least 2 px on the outer edge |
| Blob test | §8.5, four numbers |

## 13. Sailors and naval uniforms, drawn in 3 colours

### 13.1 The real uniform, as facts

Percy is a **Royal Navy Lieutenant**, modern uniform, in CHARACTER-BIBLE REVISION 2. The facts that matter at 16 px `[S18]`:

| Fact | Number | Confidence |
| --- | --- | --- |
| Lieutenant's rank on the sleeve, in cuff lace order | **two gold rings**, the upper one forming the executive curl | stated S18 |
| Ring width since 1931 | **9/16 in** (each half inch ring was increased to 9/16 in) | stated S18 |
| Where rank goes in shirt sleeve order | **shoulder straps** (introduced 1891 for white uniforms, in use for shirt sleeve order since) | stated S18 |
| The curl | introduced 1856, worn by the executive branch | stated S18 |

Conclusion for the sprite: in a white shirt, rank is **not** on the cuff, it is on the shoulder. So the rank read is a 2 px mark on the shoulder, not a stripe up the arm. `derived` from S18.

### 13.2 Two garments that both matter

The card names "a white shirt with blue collar", which is two different real things and the art has to choose:

| Garment | Who | What it is | How it reads at 16 px |
| --- | --- | --- | --- |
| Officer's white shirt, shirt sleeve order | the Lieutenant | white shirt, dark tie or open collar, navy or black trousers, shoulder rank slides | a white block with a dark V at the neck and 1 to 2 px of rank on the shoulder |
| Rating's white shirt with a navy collar | a sailor | white shirt with a square navy collar across the shoulders, a black silk tied at the front | a white block with a **horizontal** navy band across the top of the chest, and a 1 px black knot |

`inference` from S18 plus the uniform knowledge the setting needs; the officer version is the one Percy wears, and the rating version is the cheapest way to draw "this is a sailor" for background crew.

The difference is one shape, and it is the difference the eye reads immediately: **officer = V at the neck, rating = horizontal band across the chest.** Two different 3 to 5 px shapes on the same white ground.

### 13.3 The recipe, with numbers

Percy, front view, Plan A body (head 7 rows, body 8 rows), 3 colours per palette, head and body palettes split as in §8.2.

| Element | Pixels | Tone | Rows and columns |
| --- | --- | --- | --- |
| Hair and beard mass | 14 to 18 | `$16` red orange (or `$17`), against `$0F` | y0 to y1 hair, y5 to y6 beard, columns 4 to 11 |
| Skin | 10 to 14 | `$36` | y2 to y5, columns 5 to 10 |
| Eyes | 2 each | `$0F` | y3, columns 5 to 6 and 9 to 10 |
| Shirt, lit | 24 to 30 | `$30` | y8 to y12, columns 5 to 10 |
| Shirt, shadow | 8 to 10 | `$10` | y8 to y12, columns 11 and the 1 px under each arm |
| Collar V | 6 to 8 | `$0F` | y7 to y8, columns 6 to 9 |
| Rank slide | 2 | `$28` gold, or `$10` if the palette is spent | y7, column 5 (the visible shoulder) |
| Cuff bands | 2 | `$0F` | y11, one px on each outer arm |
| Belt | 7 | `$0F` with 1 px `$28` buckle | y13, columns 4 to 10 |
| Trousers | 6 to 8 | `$0F` or `$02` | y13 to y14, columns 5 to 6 and 9 to 10 |
| Trident | 4 to 6 | `$0F` shaft, `$10` head | column 12, y4 to y13, head at y4 to y6 |

`inference`, built on §2, §8 and §12. The counts are the part that matters: the light tone is 24 to 30 of about 110 body pixels, which is 22 to 27 percent, under the 30 percent blob ceiling.

### 13.4 What the sailor may not do

| Forbidden | Number | Why |
| --- | --- | --- |
| A white shirt with no dark interior line | 0 rows without a dark pixel is the rule | this is the white blob |
| Navy trousers on the navy night road | `$02` contrast 1.00 | the character has no legs |
| A white cap on a white shirt | both `$30`, 1.00 contrast against each other | the head merges into the body; the cap needs `$10` or `$02` |
| A face in the shirt's own tone | 1.00 contrast | the head merges into the chest |
| A trident drawn inside the body outline | loses 1 to 3 px of shop window | nothing reads; hold it outside the arm |
| Rank drawn as a cuff stripe on a white shirt | the wrong order, and 1 px cannot show 2 rings plus a curl | use the shoulder mark |

## 14. Sources

| Tag | Source | Link | Read |
| --- | --- | --- | --- |
| S1 | NESdev wiki, "PPU": 256 x 240, 8 x 8 tiles, 256 tiles per pattern table, 2 tables, about 2270 cycles in vblank | https://www.nesdev.org/wiki/PPU | 2026-10-21 |
| S2 | NESdev wiki, "PPU palettes": 64 entries, 4 background and 4 sprite palettes of 4, entry 0 transparent for sprites, palette selected per sprite, 25 colours on screen | https://www.nesdev.org/wiki/PPU_palettes | 2026-10-21 |
| S3 | NESdev wiki, "PPU OAM": 64 sprites of 4 bytes, 8 per scanline, 8x8 or 8x16, attributes carry palette, priority, horizontal and vertical flip | https://www.nesdev.org/wiki/PPU_OAM | 2026-10-21 |
| S4 | NESdev wiki, "PPU attribute tables": one palette per 16 x 16 background area | https://www.nesdev.org/wiki/PPU_attribute_tables | 2026-10-21 |
| S5 | nesdoug, "05. Palettes": toolchain black `$0F`, white `$30`, avoid the `$xD` entries | https://nesdoug.com/2018/09/05/05-palettes | 2026-10-21 |
| S6 | 8bitphoto, "NES Colour Palette": 64 entries, 55 distinct, 13 + 12 + 1 = 25 colour budget | https://8bitphoto.co.uk/palettes/nes.html | 2026-10-21 |
| S7 | Retrocean, "Dragon Quest (NES)": front facing only, no side or rear hero sprites, two frame walk faked by mirroring a symmetric figure | https://retrocean.com/nes/dragon-quest/ | 2026-10-21 |
| S8 | Retrocean, "Final Fantasy (NES)": four heroes, class upgrade redraws each sprite taller | https://retrocean.com/nes/final-fantasy/ | 2026-10-21 |
| S9 | Wikipedia, "Final Fantasy (video game)": party on the right, monsters on the left | https://en.wikipedia.org/wiki/Final_Fantasy_(video_game) | 2026-10-21 |
| S10 | GameAnim, "Original Castlevania Sprite Drawings": 16 animation frames for the player in total, frames built from smaller tiles and reused | https://gameanim.com/2022/02/19/original-castlevania-sprite-drawings/ | 2026-10-21 |
| S11 | KartikChugh, "NES 4 Frame Walk Cycle": 3 frame cycles, ping pong, split legs and torso | https://github.com/KartikChugh/NES-4-Frame-Walk-Cycle | 2026-10-21 |
| S12 | Empty Armor, "The Genius of Castlevania's Pixel Art" (video transcript): Simon's palette has no black while the enemies' palettes do; halves reused; 25 colours | https://youtube.com/watch?v=l_W9Yuqm8Ns | 2026-10-21 |
| S13 | Bill Stiernberg, "Zeboyd Weekly Art! Character Sprites", 2013-07-10: 16 x 16 characters with 2 frames, always animated, 4 directions, 2 main colours plus small accents; 16 x 24 gives 8 more rows for head and outfit; the "standing straight, arms down, facing 90 degrees, like a robot" complaint; 4 frames rather than 3 because 3 looked mechanical | https://zeboyd.com/2013/07/10/zeboyd-weekly-art-71013-character-sprites-and-csh/ | 2026-10-22 |
| S14 | Pixelation, "Final Fantasy Pixel Art: Why It Still Hits Different After 35 Years": Kazuko Shibuya, the super deformed large head and large eye convention for four angles in few colours; 25 colours on the NES; the 3 tone rule; the Black Mage as a silhouette with two glowing eyes; the black silhouette test | https://pixelation.org/final-fantasy-pixel-art-why-it-still-hits-different-after-35-years-1n99 | 2026-10-22 |
| S15 | Derek Yu, "Pixel Art Tutorial: Basics": reduce every line to a single pixel and clean jaggies; dithering as an advanced technique for limited palettes and larger sprites; 16 and 32 colour palette norms | https://derekyu.com/makegames/pixelart.html | 2026-10-22 |
| S16 | Pine sandbox result `sprite-uniforms.json` (this project's own research lane, 2026-10-22), summarising: SpriteGen "How to make a 16x16 pixel art sprite" (exact 16 x 16 grid, 4 to 8 colours, top left light, scale only by whole multiples); Pixnote "How to draw pixel art characters" (2 to 3 heads tall at 16 x 16, eyes 1 x 1 or 1 x 2 or 2 x 1, test the filled silhouette first, 1 px weapon shaft); Pixnote "Pixel art shading and lighting" (base plus shadow as the 16 x 16 standard, a near white highlight for a 3 tone ramp); Derek Yu "Pixel Art Tutorial: Basics" | <workspace>\Shared\projects\arananet\pine\data\results\sprite-uniforms.json | 2026-10-22 |
| S17 | The Spriters Resource, "EarthBound Beginnings (Prototype) / Mother (JPN), NES", character sheet index: walk cycles listed per direction, down, left, right, up | https://spriters-resource.com/nes/earthboundbeginningsprototypemotherjpn/asset/985 | 2026-10-22 |
| S18 | Wikipedia, "Ranks and insignia of the officers of the Royal Navy": the modern gold ring system from 1856; lieutenant two half inch rings (1863), all half inch rings increased to 9/16 in in 1931; the upper ring forms the executive curl; shoulder straps for white uniforms since 1891 and more recently for shirt sleeve order | https://en.wikipedia.org/wiki/Royal_Navy_officer_rank_insignia | 2026-10-22 |
| S19 | This project's `data/nes_palette.json` (64 entries) plus WCAG relative luminance and contrast ratio arithmetic run by this lane on 2026-10-22: `$0F` 0.000, `$02` 0.036, `$00` 0.202, `$10` 0.503, `$30` 0.973, `$36` 0.668, `$31` 0.704, `$28` 0.542 | data/nes_palette.json | 2026-10-22 |

## 15. What this file does not settle

| Open question | Why it matters | How to settle it |
| --- | --- | --- |
| The real pixel dimensions of the FF1 to FF3 overworld sprites, per direction | the 1:1.2 target in the card is adopted as a project decision, not measured here | a vision pass by the manager on a screenshot: count the head rows and the body rows |
| The exact night road and ship deck ground colours in our own maps | the contrast table in §12 uses the two most likely entries | read the map palette from `data/maps/` and recompute `[S19]` |
| Whether the 2 palette split of §8.2 costs an enemy palette that we need | 4 sprite palettes is the hardware ceiling `[S2]` | count the palettes the ship scene needs on paper before drawing the crew |
| Whether a 2 frame cycle is enough for the hero, or 4 frames are needed | 2 frames is the Dragon Quest convention `[S13]`; 4 was judged necessary by the same artist for a later game | Nayil's call on the game's feel; the pipeline can generate 4 for the hero at 4 extra cells |
| Whether the walk should bob 1 px | a bob needs 4 frames to read | test at 3x on the real map, one 10 s capture |

Confidence in this file as a whole: the hardware numbers (§1, §5.2, §6.2, §12.1) are arithmetic on documented limits and our own palette, and they are firm. The craft numbers (proportions, pixel counts, timings) are this lane's synthesis of the sources plus the 16 x 16 grid, marked `inference` where they are not stated, and should be re-read against a real sprite sheet before they are quoted outside the project.
