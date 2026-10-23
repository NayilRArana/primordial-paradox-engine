# PALETTE SYNERGY: how real NES games make a background and a character agree, and what that means for our eight scenes

Written by research-assistant on 2026-10-22 for card `t_3da3f037` (PAL-STUDY), for the gamedev lane.
Serves `knowledge/ART-BIBLE.md` RULE 0 (palette first, Nayil 2026-10-22). Data file: `data/palette_recipes.json`.
Read `knowledge/NES-AUDIT.md` first: this page assumes the frame rules written there.

## 0. Scope and how to read this

Nayil's complaint, in his words: the concept art, the art style, the backgrounds and the sprites are hamstrung because they are not colour coordinated to the NES palette limits, so backgrounds and characters do not work together. This page answers that with numbers taken from the hardware documentation and from published analyses of the games, and then applies them to our own scenes.

Rules of this file:

- Nothing here overrides a gamedev palette decision. Where our derived numbers disagree with a file on disk, the row says so and section 12 carries a `Q:` line for gamedev.
- Every number has a source tag `[S1]` to `[S13]`, resolved in section 13 with link and read date. Confidence is `stated` (the source says it in those terms), `derived` (arithmetic on stated numbers) or `inference` (our reading, not yet verified against a running game).
- We describe games, we do not reproduce them: no screenshot, rip, tile or palette table from a published game is stored in this repository.
- No long dashes anywhere in this file or in the data file, per Nayil's standing rule.

## 1. The hardware, in the numbers the art has to live inside

| Fact | Number | Confidence | Source |
| --- | --- | --- | --- |
| Colour outputs the PPU can address | 64, `$00` to `$3F` | stated | S1 S4 |
| Entries that are not usable | 9: the forbidden `$0D` plus 8 duplicate blacks (`$0E $1D $1E $1F $2E $2F $3E $3F`) | stated | S1 |
| Usable entries | 55 = 64 minus 9 | derived | S1 S4 |
| Of those, entries that are not black | 54, because `$0F` is the single canonical black | derived | S1 S13 |
| Structure | 4 background palettes and 4 sprite palettes, each 4 entries | stated | S1 |
| Drawable colours per background palette | 3 plus the shared backdrop | stated | S1 |
| Drawable colours per sprite palette | 3 plus transparency | stated | S1 |
| Colours a frame can carry | 25 = 12 background + 12 sprite + 1 backdrop | derived | S1 S13 |
| Smallest region that can change background palette | 16 x 16 pixels, 2 x 2 tiles | stated | S2 |
| Attribute byte | 32 x 32 pixels, four 16 x 16 quadrants | stated | S2 |
| The backdrop | entry 0 of background palette 0, `$3F00`, aliased at `$3F10`, one per frame | stated | S1 |

Note on the number 54. RULE 0 says "the 54 usable colours". The arithmetic that gets there honestly is 55 usable entries minus the one canonical black, not "55 minus `$0D`", because `$0D` is already inside the 9 unusable. `knowledge/ART-BIBLE.md` row 12 subtracts `$0D` from 55 and lands on 54 by a double count. The number is right, the reason is not. `[S1] [S13]`

The 54 are nine hue families by six levels in `data/palette.json`, but that file is a *different* palette: its hex values (`#0b0b0f`, `#1c1c24`, ...) are not PPU outputs at all. RULE 0 point 1 asks for colours picked from the NES master colours, so the pipeline has to quantise through `data/nes_palette.json` and not through `data/palette.json`. See section 12, item 1. `[S13]`

### 1.1 The luma rows, with measured luminance

The PPU numbers its colours as `VVHHHH`: two bits of value and four of hue. That makes four rows of sixteen. `[S1]`

| Row | Entries | Name in the documentation | Relative luminance of its entries (WCAG, measured from the published hex) |
| --- | --- | --- | --- |
| 0 | `$00` to `$0F` | dark colours, "similar to dark gray" | 0.000 to 0.202, median 0.070 |
| 1 | `$10` to `$1F` | medium colours | 0.138 to 0.503, median 0.228 |
| 2 | `$20` to `$2F` | light colours, "similar to light gray" | 0.188 to 0.939, median 0.463 |
| 3 | `$30` to `$3F` | pale colours, "light mixed with white" | 0.503 to 0.973, median 0.758 |

Row = entry number divided by 16, integer division, for every one of the 55 usable entries; that is `derived` from S1 and checked against `data/nes_palette.json` `[S13]`. The anchors are `$0F` black, `$00` dark grey, `$10` light grey, `$20` white `[S1]`.

The rows overlap: a row 0 entry can measure 0.202 and a row 2 entry can measure 0.188. So a row gap is a necessary check and not a sufficient one. Section 5 gives both numbers.

## 2. How real games pick the backdrop

There are two defensible answers and both are all over the NES catalogue.

**Black.** The backdrop is `$0F` and the art never draws on it. This wins whenever the scene has a dark field of its own: night exteriors, interiors, caves, and every battle screen that puts the monster on a black stage. It buys the artist a free fourth "colour" for holes and shadows, and it makes every pale sprite pop. All twelve scene palette files in this repository use backdrop 15 `[S13]`, so black is already our house answer. That is correct for the ship and for night, and it is exactly why our morning quay scene looks wrong (section 11, row 3).

**The sky colour.** When the sky is a flat field that covers the top of the screen and nothing is drawn on it, the sky becomes the backdrop and one whole background palette is freed for the buildings, the ground or the water. A 256 x 240 screen has 240 attribute areas of 16 x 16; a sky that fills the top 80 pixels owns 80 of them, which is 33 percent of the frame. Put 50 percent as the switch rule: if one colour owns half the areas, make it the backdrop `[S2] [S4]` `inference`.

Two consequences that decide layouts:

1. The backdrop cannot be changed for half the screen. A scene that needs both a black cave mouth and a blue sky in one frame has to make one of them a drawn colour out of the 12 background entries.
2. The backdrop is shared with the sprite layer storage, and only entry 0 is shared. Everything else has to be written twice to appear on both layers `[S1]`.

## 3. How a background keeps three colours per palette per 16 x 16

The attribute table is 64 bytes, each byte covering 32 x 32 pixels in four 2 bit quadrants, so an area is 16 x 16 pixels and uses exactly one of the four background palettes `[S2]`. Three practical consequences:

- Build metatiles at 16 x 16 or 32 x 32 so art boundaries land on the attribute grid, which is what the wiki recommends and what SMB does `[S2]`.
- A surface change costs a palette only when it crosses an area boundary. A 3 pixel kerb cannot get its own palette.
- The three entries want to be a ladder: outline or shadow, body, highlight, one luma row apart `[S1] [S13]`. Two of the four palettes is usually enough for the architecture (floor and wall); the third for a material accent; the fourth for a prop.

What real games do with the four: they group by material, not by object. Castlevania III builds its castle out of tiled variations of a small set of blocks, so one stone palette covers a room's worth of architecture `[S5]`. Final Fantasy's towns and dungeons reuse the same three entry ladders with the hue rotated, which is why the games read as colour coded regions rather than as hundreds of objects `[S8]` `inference`.

## 4. How a sprite borrows a palette that contrasts with every background it walks on

This is the heart of Nayil's complaint, so it gets the numbers.

A sprite tile carries three colours plus transparency, and the palette is chosen per sprite object, not per pixel, so a hero cannot borrow one colour from this palette and two from that one `[S1] [S3] [S5]`. Real games get round it two ways:

- Overlaid sprite objects: Mega Man's face is a separate sprite so it can use a second palette on top of the body `[S7]`.
- Transparent pixels as a fourth apparent colour: Kazuko Shibuya says she made certain pixels transparent as a trick to get a fourth colour out of three, most visibly in Final Fantasy helmet and armour outlines `[S8]`. Mother splits a character's palette between the top and bottom halves of the body, which is the same trick at the character level `[S10] [S11]`.

For our purposes the useful rule is not those tricks, it is the ordering: **the ground has to be chosen to suit the hero, and not the other way round**, because the hero palette is fixed across the whole game (RULE 0 point 3).

### 4.1 The plate rule

Define the **ground plate** as the single background entry that fills the tile the hero's feet stand on. Then:

- the hero's body entry must sit at least 2 luma rows from the plate (RULE 0 point 2), and
- the plate must be an entry the walkable band's palette actually owns, so the art cannot quietly draw a different entry under the feet.

With four rows and a body on row r, the plate must be on a row r + 2 or lower / r - 2 or higher:

| Hero body row | Plate rows that clear 2 rows | Plate rows that merge |
| --- | --- | --- |
| 0 (dark) | 2, 3 | 0, 1 |
| 1 (medium) | 3 | 0, 1, 2 |
| 2 (light) | 0 | 1, 2, 3 |
| 3 (pale) | 0, 1 | 2, 3 |

There is no plate row that clears both a row 0 body and a row 2 body. That is the single most useful finding on this page: **a near black hero and a light hero cannot share a walkable band.** Our Hadrian is near black (row 0) and Percy, Zander and Konrad are rows 2, 3 and 2, so Hadrian needs pale ground under him (weather decks, snow, whitewash, sand) or his own scenes, and the other three need dark ground. This is why the corridor row in section 11 fails.

## 5. Minimum separation: the number

RULE 0 sets 2 luma rows between a sprite body and the background behind it. Add a second gate, because rows alone lie:

- **Gate 1, rows:** 2 rows minimum. That is RULE 0 and the table in 4.1.
- **Gate 2, measured luminance:** 0.20 minimum between body and plate. Measured on the 55 usable entries: of the 378 pairs that are 2 rows apart, the *median* difference is 0.436 but the *lowest* is 0.0002 `derived` `[S1] [S13]`. A pair like `$02` dark blue and `$12` blue is 1 row apart and 0.070 apart in luminance; a pair like `$22` light blue and `$00` dark grey is 2 rows apart and only 0.074 apart. Rows alone would pass the second pair and the eye does not.

A single number to put in a checker, the way I would write it: **pass if (rows >= 2 and dlum >= 0.20), or (rows >= 1 and dlum >= 0.30 and a row 0 outline is present).** The outline carries the silhouette when the body cannot carry it `[S3] [S5]`.

## 6. Hue families that read together

Hue is the low four bits of the entry number: 0 grey, 1 azure, 2 blue, 3 violet, 4 magenta, 5 rose, 6 red, 7 orange, 8 yellow, 9 chartreuse, 10 green, 11 spring, 12 cyan `[S1]`. Distance on the wheel is the shortest way round out of the 13 positions.

| Pair | Wheel distance | Example entries | Measured luminance gap | Use |
| --- | --- | --- | --- | --- |
| blue and orange | 5 | `$02` `$07` | 0.071 | night street lamp against navy air; the classic |
| light blue and amber | 6 | `$12` `$27` | 0.475 | hero against a warm interior |
| green and red | 4 | `$0A` `$06` | 0.076 | moss on iron, copper on stone |
| cyan and orange | 5 | `$0C` `$17` | 0.352 | sea against sunset |
| violet and chartreuse | 6 | `$13` `$29` | 0.475 | the cheapest "unnatural" pair we own |
| rose and red | 1 | `$05` `$06` | 0.183 | refused: reads as a printing error |
| magenta and rose | 1 | `$04` `$05` | 0.130 | refused |

Rules of thumb, `inference` on top of `[S1] [S5]`:

- Two hue families per palette, maximum. With three entries that is: outline, surface, accent.
- A hue move under 3 is a shade, not a second material. If you want a second material, move 4 or more, or move a luma row.
- Distance is carried by rows and material is carried by hue: far things lose a row, they do not change hue. That is aerial perspective inside four rows.
- Grey is the third member of any palette that has to sit next to another material without arguing.

## 7. Outline colour choices

| Outline | Entry | Row | When | Source |
| --- | --- | --- | --- | --- |
| black | `$0F` | 0 | night, interiors, battles, anything on a non pale ground | S3 S5 |
| dark blue | `$02` | 0 | daylight and sea; reads as shadow rather than as a drawn line | inference |
| dark brown | `$07` or `$08` | 0 | warm interiors, wood, lamplight, the wardroom | inference |
| dark violet | `$03` | 0 | Hadrian, and anything that has to feel cold and undead | inference |

Three hard rules:

1. The outline is one of the three entries, not transparency. Transparency is not an outline; it lets the ground through and the silhouette disappears.
2. An outline colour cannot be shared across sprite palettes: only entry 0 is shared storage, so a common black outline costs one entry in each of the four sprite palettes `[S1]`. That is the price of a consistent look, and it is worth paying.
3. Never outline lighter than the body. It turns the silhouette inside out.

## 8. Fixed hero palettes

RULE 0 point 3 names the four. These are NES entries that fit those names, derived here so that the numbers exist before the art does:

| Hero | Brief | Entries | Outline | Body (row) | Accent (row) |
| --- | --- | --- | --- | --- | --- |
| Percy | blue and gold | 15, 34, 56 | `$0F` black | `$22` light blue, row 2 | `$38` pale gold, row 3 |
| Hadrian | near black and purple | 15, 3, 35 | `$0F` black | `$03` dark violet, row 0 | `$23` pale violet, row 2 |
| Zander | light blue | 15, 49, 18 | `$0F` black | `$31` pale azure, row 3 | `$12` blue, row 1 |
| Konrad | grey and amber | 15, 45, 39 | `$0F` black | `$2D` dark grey, row 2 | `$27` amber, row 2 |

The consequence of fixing them: the hero keeps these three entries in every scene, the scene has to supply a plate that clears him, and sprite palette zero belongs to the hero, leaving three palette slots for NPCs, enemies and props `[S3] [S13]`.

Hadrian is the problem child. His body is 0.034 away from black and 0.028 away from the corridor's deck entry, which is zero luma rows. Under the rule he is invisible on every dark ground we have. Options, for gamedev to pick:

- pale grounds wherever Hadrian walks: weather deck, snow, whitewashed bulkhead, sand;
- a pale violet rim at 1 pixel on every silhouette edge, at least 1 pixel wide on all four sides, spending 10 to 15 percent of the sprite's pixels;
- give Hadrian a row 1 body (`$13` violet, 0.135) and keep the near black to the outline and the boots.

## 9. Night scenes: what Final Fantasy and Mother do

Description only, from published analyses and screenshots, no images stored.

- **Final Fantasy.** The overworld and the battle screens keep one backdrop, black, and the sky is an entry rather than the backdrop. Shibuya's palette is a dark outline, one mid body, one light accent, with transparent pixels used to fake a fourth tone in the helmets and armour `[S8]`. Party characters keep one palette across the whole game, which is the pattern RULE 0 point 3 already asks for `[S8]` `inference`.
- **Mother / EarthBound Beginnings.** Characters are split into top and bottom palettes, which lets the face carry different colours from the clothes on the same body `[S10] [S11]`. Night is handled by dropping the whole scene one luma row and keeping the hue, with one pale entry reserved for the light source `inference`.
- **Dragon Quest.** One monster design is reused with palette swaps to make three variants, which is the cheapest content multiplication on the console and a reminder that a palette change is a content decision, not a polish step `[S10] [S12]`.
- **Castlevania III.** Moving sprites get three colours plus one colour shared across all sprites, and the environments are built from tiled variations rather than from new art `[S5]`.

What that means for us: night is one row down and zero hue changes, the backdrop stays black, exactly one entry on the screen is pale, and it is the lamp, the window or the eye.

## 10. Transitions and palette cycling

The PPU has no brightness register a game can simply turn down, and palette RAM is 32 bytes mirrored through `$3F00` to `$3FFF` `[S1]`. So every transition is a palette rewrite `[S1] [S2]`:

| Effect | What changes | Numbers | Source |
| --- | --- | --- | --- |
| fade to black | every background entry steps toward `$0F` | 4 steps, 8 frames each, 32 frames total, 25 entries rewritten per step | inference |
| flash on a hit | the background entries go to `$30` white | 2 frames, 12 entries | inference |
| lightning | the backdrop byte alone | 1 byte at `$3F00`, 2 frames, 15 to 48 and back | inference |
| palette cycling | one entry rotates between two neighbours | 2 entries, 8 frames per state, about 8 cycles per second | stated S4 S11 |
| scene cut | the whole 25 entry set is rewritten in one vblank | about 32 bytes, well inside the 567 byte vblank budget | derived S13 |

Cycling is the one that changes how a scene is designed: water, neon, lava and the title flash are free animation because the shapes do not move, only an entry does. Build one entry into every scene that is allowed to cycle.

## 11. The eight scene palette sets

Full data with hex, luma rows and luminance in `data/palette_recipes.json`, section `scene_sets`. Every entry below is an NES master palette entry number. `sp0` is the hero slot.

| Scene | Backdrop | bg0 | bg1 | bg2 | bg3 | sp0 hero | sp1 | sp2 | sp3 | Hero rows over the plate | Distinct colours |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| night M3 drive | 15 | 2, 1, 48 | 15, 16, 2 | 7, 23, 40 | 15, 2, 18 | Percy 15, 34, 56 | 0, 16, 15 | 7, 23, 40 | 2, 18, 48 | 2, dlum 0.276 | 12 |
| London street at night | 15 | 2, 1, 40 | 0, 16, 18 | 7, 23, 40 | 15, 8, 39 | Percy 15, 34, 56 | 0, 16, 15 | 7, 23, 40 | 3, 35, 48 | 2, dlum 0.074 | 16 |
| Southampton quay, morning | 15 | 0, 16, 48 | 7, 23, 40 | 9, 10, 42 | 2, 18, 48 | Percy 15, 34, 56 | 0, 15, 16 | 7, 23, 40 | 2, 18, 48 | 2, dlum 0.074 | 14 |
| Ship corridor | 15 | 0, 16, 2 | 2, 0, 18 | 22, 6, 38 | 16, 48, 18 | Hadrian 15, 3, 35 | 0, 16, 15 | 7, 23, 40 | 2, 18, 48 | 0, fails | 14 |
| Wardroom | 15 | 23, 7, 40 | 8, 7, 23 | 2, 1, 48 | 48, 16, 40 | Konrad 15, 45, 39 | 0, 16, 15 | 7, 23, 40 | 2, 18, 48 | 2, dlum 0.150 | 13 |
| Engine room | 15 | 0, 16, 2 | 22, 6, 38 | 7, 23, 40 | 23, 39, 40 | Konrad 15, 45, 39 | 0, 16, 15 | 7, 23, 40 | 22, 38, 48 | 2, dlum 0.014 | 13 |
| Bridge | 15 | 1, 17, 33 | 0, 16, 48 | 12, 2, 18 | 15, 8, 39 | Zander 15, 49, 18 | 0, 16, 15 | 7, 23, 40 | 19, 35, 48 | 3, dlum 0.503 | 18 |
| Battle backgrounds | 15 | 0, 16, 48 | 2, 18, 48 | 7, 23, 40 | 22, 38, 48 | Percy 15, 34, 56 | 0, 16, 15 | 7, 23, 40 | 22, 38, 48 | 2, dlum 0.240 | 13 |

What the table says, honestly:

1. Seven of eight scenes pass the row rule on their ground plate. The corridor fails, because the deck as specced (`bg1` = `2, 0, 18`, all rows 0 and 1) has no entry that clears Hadrian's row 0 body. The fix is one entry, not the hero: swap `bg1` entry 0 (`$00`) for `$20` white, or move Hadrian to the weather deck.
2. Row 2 plus a low measured gap is a warning, not a pass. London street and the quay both measure 0.074 between Percy's body and the plate even though they are 2 rows apart, so those two need a hue check as well (grey `$00` against light blue `$22` is 2 hue positions, which is thin). The safer plate for both is `$02` blue, 0.251 away.
3. The morning quay keeps the black backdrop of the ship scenes, which is the reason it reads as night with a light sky. Section 2's second answer applies here: the pale sky (`$30` white) wants to be the backdrop and `bg0` wants to become the stone. That is a gamedev call, so it is a `Q:` line.
4. The engine room's plate `$00` grey against Konrad's `$2D` grey is 0.014 apart: same hue family, adjacent luminance. It passes the row rule on a technicality. The plate should be `$02` blue (0.251 away) or the hero's body should move a row.
5. Every scene is inside the 25 colour ceiling, between 12 and 18 distinct colours. The ceiling is not the constraint; the area rule is.

## 12. Common amateur mistakes, with the number that catches each

| Mistake | Measurement | Why it fails | Caught by |
| --- | --- | --- | --- |
| every object gets its own palette | a room has 15 objects and the hardware has 4 background palettes | 3.75 objects per palette means nothing shares a material | palette count per scene |
| sprite and ground on the same luma row | 0 rows, median measured gap 0.096 | the silhouette is only the outline | gate 1 at 2 rows |
| 5 or more colours in one 16 x 16 | limit is 3 plus the backdrop | attribute area holds one palette | area count, as in NES-AUDIT |
| pastel mush, three entries on row 3 | rows spanned 1, no entry darker than another | nothing to read a shape against | rows spanned per palette |
| black as a background entry and as the backdrop | 1 entry wasted, empty and drawn black become one | the art loses its holes | backdrop audit |
| three rows of one hue | 1 hue, 3 rows | reads as a gradient, not as two materials | hue count per palette |
| a hero palette that changes per scene | 0 allowed substitutions | the character reads as a different character | hero palette diff |
| a fourth colour borrowed from the sprite layer | entries per palette is 3 | the palette is chosen per sprite object | palette diff |
| the white blob | row 3 body over a row 2 or row 3 ground | 0 to 1 rows | gate 1 and 2 |

## 13. Sources

| Tag | Source | Read | Note |
| --- | --- | --- | --- |
| S1 | NESdev wiki, PPU palettes, https://www.nesdev.org/wiki/PPU_palettes | 2026-10-22 | palette RAM, entry 0, backdrop aliasing, hue and value bits, luma names, `$0D` |
| S2 | NESdev wiki, PPU attribute tables, https://www.nesdev.org/wiki/PPU_attribute_tables | 2026-10-22 | 16 x 16 area, 32 x 32 byte, metatile alignment |
| S3 | NESdev wiki, PPU OAM, https://www.nesdev.org/wiki/PPU_OAM | 2026-10-22 | per sprite palette selection, 64 objects, 4 bytes an entry |
| S4 | Lospec, Nintendo Entertainment System palette, https://lospec.com/palette-list/nintendo-entertainment-system | 2026-10-22 | 55 colour presentation used for every hex here |
| S5 | Slynyrd, Pixelblog 37, Classic Castlevania Study, https://www.slynyrd.com/blog/2022/3/19/pixelblog-37-classic-castlevania-study | 2026-10-22 | 3 colours plus one shared on moving sprites; tiled environments |
| S6 | Rick Hair, On the NES flicker was a feature not a bug, https://rick.hair/posts/on-the-nes-flicker-was-a-feature-not-a-bug/ | 2026-10-22 | OAM cycling, why bosses are stacked sprites |
| S7 | Pirate Hearts, The Palette Tool, https://piratehearts.com/blog/2019/03/the-palette-tool/ | 2026-10-22 | Mega Man overlaying sprites to fake a bigger per sprite palette; the NES palette lacks darks and desaturates |
| S8 | NintendoSoup, Original Final Fantasy illustrator panel (Kazuko Shibuya), https://nintendosoup.com/original-final-fantasy-illustrator-shares-a-ton-of-details-about-her-history-with-the-series/ | 2026-10-22 | transparent pixels as a fourth colour; fixed character palettes |
| S9 | Pine result `pal-nesdev.json`, arananet/pine/data/results, run 2026-10-22 14:18 to 14:21, 34 turns, computer 0.0087 USD, llm 0.0828 USD | 2026-10-22 | palette RAM layout, 16 x 16 area, eight per scanline, `$0D`, luma bands |
| S10 | Pine result `nes-art-habits.json`, run 2026-10-21 21:26, 50 turns | 2026-10-22 | the habits list, which is the pointer to S11 and S12 |
| S11 | DragonDePlatino, MOTHER Sprites, https://www.deviantart.com/dragondeplatino/art/MOTHER-Sprites-737008342 (via S10) | 2026-10-21 | top and bottom palettes on one character |
| S12 | PixelJoint, Dragon Quest Golems, https://pixeljoint.com/pixelart/132188.htm (via S10) | 2026-10-21 | three palette swaps on one sprite design |
| S13 | This repository: `data/nes_palette.json`, `data/palettes/scene_*.json`, `knowledge/ART-BIBLE.md`, `knowledge/NES-AUDIT.md` | 2026-10-22 | our own measurements and specs |

Pine runs that were checked and had nothing to give: `nes-art-rules.json` stopped at `max_turns` after 25 turns without an answer, and its own note says to raise the limit only when the task needs it.

## 14. What this card actually changed

- `data/palette_recipes.json` (new, 57 recipes in 11 families, 8 scene sets, every colour resolved to hex, luma row and relative luminance from `data/nes_palette.json`).
- This page.
- No art was drawn and no scene file was edited. Section 11's failures are gamedev's to fix, not this card's.

## 15. Q: for gamedev

- `Q: the corridor deck (bg1 = 2, 0, 18) has no entry that clears Hadrian's row 0 body, so the hero is invisible on it. Fix by swapping bg1 entry 0 to $20 white, or move Hadrian to a pale deck. Which?`
- `Q: the morning quay keeps the black backdrop of the night scenes, so it reads as night with a light sky. Should the backdrop become the pale sky ($30) with bg0 re cut as stone, or does the quay stay black?`
- `Q: data/palette.json is a 54 colour design palette whose hex values are not PPU outputs, while RULE 0 point 1 asks for the NES master colours. Should the room palette roles resolve into data/nes_palette.json instead?`
- `Q: RULE 0 point 2 says 2 luma rows. Where the rows pass and the measured luminance gap is under 0.20 (London street and the quay both measure 0.074), does the row rule stand alone or is the 0.20 gate added?`
- `Q: RULE 0 point 3 fixes four hero palettes and gives the hero palette zero in every scene, which leaves three palettes for NPCs, enemies and props. Is that the intended split, or do some scenes give the hero a dedicated slot and stack enemies using overlays as Mega Man does?`

## 16. Check list for this card

| Check | Result |
| --- | --- |
| At least 40 recipes with numbers | 57 recipes, 11 families, every one carrying a `numbers` object |
| 8 scene palette sets in NES indexes | 8, each with 1 backdrop, 4 background palettes of 3, 4 sprite palettes of 3 |
| Every number sourced or marked inference | every recipe carries `confidence` in stated, derived or inference, plus source tags |
| JSON validates | `tools/check_palette_recipes.py`, exit 0 |
| No long dashes | checked by the same tool |
| Pine results read | `pal-nesdev.json` read, `nes-art-habits.json` read, `nes-art-rules.json` read and empty, `nesdev-rules.json` read |

## 17. Where the two data files live in the build (decided 2026-10-22, card t_ebb582e0)

Both files are build time inputs, not shipped data, and neither is an Included File in
`game/PrimordialParadox.yyp`.

- `data/palette_recipes.json` is authored source. No tool in `tools/` writes it; `tools/check_palette_recipes.py`
  validates it, `tools/palette_synergy.py` cites it, and this page is its documentation. It is committed for that
  reason and nothing regenerates it.
- `data/scene_palettes.json` is generated: `python tools/scene_palette_set.py build --write` rewrites it from the ten
  tracked `data/palettes/scene_*.json`. It is committed as well, because `tests/test_scene_palette_set.py` loads it
  through the loader and `tools/palette_synergy.py --gate` reads its `audit` list, and a HEAD checkout without it
  stops with `SystemExit` instead of passing.
- Neither goes into the bundle. Measured: 0 of the 35 `.gml` files under `game/` name either file, and the runtime
  loaders in `pp_data` name audio, flags, items, palette, powers, project, room_palettes, slice and the title tables
  instead. So `tools/sync_data.py` lists both in `NOT_RUNTIME`, `game/datafiles` does not carry them, and the
  regenerated project file (commit 79ffcad) declares 221 Included Files without them. A table the engine never opens
  is not a delivery input, and mirroring these two made every palette rebuild a commit obligation.
- The reason is pinned by a test rather than by this paragraph: `tests/test_project.py` asserts the two names stay out
  of `sync_data.source_files()`, out of the `.yyp` Included Files, and out of every `.gml` module, and that both stay
  tracked in `data/`. If a GML module ever starts reading one, that test fails and says to mirror it again.

