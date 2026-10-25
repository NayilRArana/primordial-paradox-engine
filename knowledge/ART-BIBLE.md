# ART-BIBLE

Hard limits of the NES and the art conventions of the games this project is measured against
(Final Fantasy I to III, Dragon Quest I to IV, Castlevania I and III), written as numbers that a
reviewer can check a frame against.

Written by research-assistant on 2026-10-21 for card `t_6cfeecbf` (ART-BIBLE).

## 0. Rules of this file

- Reference rule (PLAN-V2 section 0): the games were studied by reading published analyses, published
  hardware documentation and one published video transcript. Nothing was downloaded, ripped, traced,
  edited, transcribed or decompiled. No game image is stored in this repository. No game window was
  opened for this card (the card allows one, for at most 15 s, only when it says so; it does not).
- Every number carries a source tag `[S1]` to `[S12]`, resolved with link and read date in section 6.
- Confidence is stated per row, in one of three words:
  - `stated`: the source says it in those terms.
  - `derived`: arithmetic on a `stated` number (for example, 8 hardware sprites of 8 px wide is 64 px).
  - `open`: not verified yet, listed in section 5 with the measurement that would settle it.
- Nothing in this file is a claim about what our game must look like. Section 3 records the numbers
  PLAN-V2 already decided; section 4 is the review checklist. Style choices stay with the manager and
  Nayil.
- The file is checked by `tools\check_art_bible.py`, which also validates `data\nes_palette.json`
  (64 entries, 10 flagged, 55 distinct, no long dashes anywhere).

## 1. Hard limits, as numbers

### 1.1 The picture

| # | Fact | Number | Confidence | Source |
| --- | --- | --- | --- | --- |
| 1 | Picture size the PPU generates | 256 x 240 pixels | stated | S1, S6 |
| 2 | Visible lines per NTSC frame | 240 of 262 (20 spent in vblank) | stated | S1 |
| 3 | Background tile | 8 x 8 pixels | stated | S4, S6 |
| 4 | Tiles per pattern table | 256 (16 x 16 grid), 4 KB of CHR | stated | S1, S3 |
| 5 | Pattern tables available | 2 (8 KB of CHR in the usual cartridge) | stated | S1 |
| 6 | Nametable | 32 x 30 tiles = 960 bytes, plus a 64 byte attribute table | stated | S4 |
| 7 | VRAM on the console | 2 KB (two nametables and their attributes) | stated | S1 |
| 8 | Attribute area (the smallest region that can change background palette) | 16 x 16 pixels = 2 x 2 tiles | stated | S2, S4 |
| 9 | Metatile sizes that align with the attribute grid | 16 x 16 or 32 x 32 pixels | stated | S4 |
| 10 | Colour entries in the master palette | 64, addressed $00 to $3F | stated | S2 |
| 11 | Distinct colours in the master palette | 55 (10 entries decode to black; see 1.3) | derived | S2, S6 |
| 12 | Colours usable without caveat | 54 (55 minus the forbidden $0D black) | derived | S2, S5, S6 |
| 13 | Background palettes on screen | 4, of 4 entries each | stated | S2 |
| 14 | Sprite palettes on screen | 4, of 4 entries each | stated | S2 |
| 15 | Colours a background tile can carry | 3, plus the one shared backdrop | stated | S2, S6 |
| 16 | Colours a sprite tile can carry | 3, plus transparency | stated | S2, S6 |
| 17 | Colours on screen at once, ceiling | 25 = 3x4 background + 3x4 sprite + 1 backdrop | derived | S6, S12 |
| 18 | Sprite objects in OAM | 64 | stated | S3 |
| 19 | Sprite objects per scanline before drop out | 8 | stated | S3 |
| 20 | Sprite sizes the PPU supports | 8 x 8 or 8 x 16 | stated | S2, S3 |
| 21 | Bytes per sprite entry in OAM | 4 (Y, tile, attributes, X) | stated | S3 |
| 22 | Widest sprite-built object on one scanline | 64 pixels (8 sprites x 8 px) | derived | S3 |
| 23 | Free transforms on a sprite | horizontal flip, vertical flip, no rotation | stated | S3 |
| 24 | Sprite draw order | lower OAM index in front | stated | S3 |
| 25 | CPU cycles available in vblank | about 2270 | stated | S1 |
| 26 | Bytes updatable per frame (vblank budget) | about 567 (2270 / 4 cycles per absolute store) | derived | S1 |

Two consequences that decide layouts:

- Anything wider than 64 pixels on a single scanline cannot be made of sprites. It is either drawn as
  background tiles, or it flickers. This is the arithmetic of rules 19 and 22, and it is why NES
  battle screens draw monsters as background art and keep sprites for the small things that move.
- A background can change palette only every 16 x 16 pixels. An artist who wants a red brick next to a
  grey one on the same 16 x 16 block has to spend one of the four background palettes on both.

### 1.2 The tile colour budget, written out

| Layer | Palettes | Entries each | Opaque colours | Extra | Total |
| --- | --- | --- | --- | --- | --- |
| Background | 4 | 4 | 3 | entry 0 of palette 0 is the shared backdrop | 13 |
| Sprites | 4 | 4 | 3 | entry 0 is transparent | 12 |
| Frame | 8 | 32 | 24 | 1 backdrop | 25 |

So the working budget for one frame of our title or game screen is 12 background colours, 12 sprite
colours and 1 backdrop colour that both layers share. `[S2] [S6] [S12]`

### 1.3 The master palette

The 64 entries are four brightness rows of 16 hues: row $0x dark, $1x medium, $2x light, $3x pale;
columns $x0 grey, $x1 to $xC blue through green to cyan, $xD dark grey, $xE and $xF black. `[S2]`

The arithmetic that produces the "54 colours" figure people quote:

- 10 entries decode to black in the common decode set: $0D, $0E, $0F, $1D, $1E, $1F, $2E, $2F, $3E, $3F.
  `[S2] [S6]`
- Keeping one black gives 55 distinct colours. `[S6]` also publishes 55.
- $0D is the entry to avoid: writing it to a palette made some 2C02 sets pull the composite signal low
  during horizontal blanking, and toolchains such as neslib rewrite it to $0F. `[S2] [S5]`
- 55 distinct minus the black that is only reachable through the forbidden $0D leaves 54 usable
  colours. Black itself stays available at $0F, which the wiki calls the canonical black. `[S2] [S5]`

`data\nes_palette.json` holds all 64 indices with hex, a `usable` flag and a `flag` line, built and
cited by `tools\art\nes_palette_build.py` (the hex values are its tables, cross checked against the
published 55 value set). The values are a composite decode approximation: the wiki states plainly that
no two televisions agree and that every emulator palette differs. `[S2]`

Default choices that follow from the sources, not from taste:

- Black is $0F, never $0D. `[S2] [S5]`
- White is $30 (the toolchain default for white is $30, black $0F). `[S5]`
- The backdrop is whatever colour sits at $3F00, entry 0 of background palette 0, and it is shared with
  every sprite palette's entry 0. `[S2]`

### 1.4 Sprites in detail

| Field | Meaning | Source |
| --- | --- | --- |
| Y | top of the sprite, delayed one scanline, so write Y - 1; $EF to $FF hides it; nothing shows on line 0 | S3 |
| Tile | tile number in the sprite pattern table; in 8x16 mode bit 0 picks the table and the bottom half is the next tile | S3 |
| Attributes | low 2 bits palette 4 to 7, bit 5 priority behind the background, bit 6 horizontal flip, bit 7 vertical flip | S3 |
| X | left edge; $F9 to $FF pushes a sprite off the right edge; there is no partial sprite at X = 0 | S3 |

Copying OAM costs 513 or 514 CPU cycles per frame (OAMDMA), which fits inside the vblank budget of
rule 25. `[S3]`

## 2. Conventions of the studied games, as numbers

### 2.1 Dragon Quest I (1986, Enix, Chunsoft)

| Fact | Number or shape | Confidence | Source |
| --- | --- | --- | --- |
| Battle view | first person; the hero is off screen | stated | S7 |
| Enemies per battle | 1, against 1 hero | stated | S7 |
| Monster animation | none; monsters are static images | stated | S7 |
| Compensation for static monsters | screen shake on damage, HP digits that turn red | stated | S7 |
| Commands | 4 (fight, spell, item, run) | stated | S7 |
| Hero facings on the map | front facing only; no side and no rear sprites | stated | S7 |
| How the walk "cycle" is made | most figures drawn symmetrical and mirrored to fake a two frame cycle | stated | S7 |
| NPC animation | none; the king, the princess and the Dragonlord are static | stated | S7 |
| Glyph budget (Japanese release) | about 20 katakana glyphs plus a dash and voicing marks | stated | S7 |

That last row matters more than it looks: the font was small because the cartridge was 512 kbit, not
because an 8 x 8 grid forces it. Our font can hold 96 or more glyphs; the grid only fixes the cell.

### 2.2 Dragon Quest, North American release (1989, Iwata's conversion)

| Fact | Change | Confidence | Source |
| --- | --- | --- | --- |
| Hero sprite | enlarged | stated | S7 |
| Facing | directional facings added, so the crab-walk oddity went away | stated | S7 |

### 2.3 Final Fantasy I (1987, Square)

| Fact | Number or shape | Confidence | Source |
| --- | --- | --- | --- |
| Battle view | side view; party on the right edge, monsters on the left | stated | S8, S9 |
| Party on screen | 4 heroes, stacked down the right edge | stated | S8 |
| Background in battle | the terrain of the encounter, behind the monsters | stated | S8 |
| Hero animation in battle | visible weapon swing on attack, a slump to one knee when hurt | stated | S8 |
| Hero sprite size tiers | 2: the class upgrade after Bahamut redraws each sprite taller | stated | S8 |
| Screens in rotation | 4: world map, towns and dungeons, combat, menu | stated | S8 |
| Historical note | credited as the first RPG to show the party on the right instead of a first person view | stated | S9 |

### 2.4 Castlevania (1986) and Castlevania III (1989), Konami

| Fact | Number or shape | Confidence | Source |
| --- | --- | --- | --- |
| Player character animation frames, Castlevania 1 | 16 in total for the whole game | stated | S10 |
| Frame construction | frames built from smaller tiles, tiles reused across many frames | stated | S10 |
| Sprite structure | split into top and bottom halves so attacking does not need new legs | stated | S11, S12 |
| Simon's legs | the same leg tiles serve duck, jump, death and stair descent with different tops or filler tiles | stated | S12 |
| Castlevania 1 walk cycle | a few distinct frames plus reuse of the idle | stated | S12 |
| Castlevania III walk cycle | 3 drawn frames, ping ponged, with the idle as a fourth | stated | S11 |
| Palette assignment | Simon gets a dedicated sprite palette; all enemies share the other three | stated | S12 |
| Why Simon reads clearly | his palette has no black and the enemies' palettes do | stated | S12 |
| Subweapons | every frame of a subweapon is an existing tile elsewhere in the game; the axe is one sprite rotated by 90 degrees per frame | stated | S12 |
| Whip upgrades | level 2 is a redrawn spikier outline, level 3 is the same sprite recoloured to Simon's palette plus one tile of reach | stated | S12 |
| Typical platformer hero size on NES | 16 x 32, 16 x 24 or 16 x 16, built from 2 to 4 hardware sprites | stated (forum level) | S11 note |

The 16 x 32 figure is worth reading with rule 22: 16 px wide by 32 tall is 2 columns by 2 rows of
8 x 16 hardware sprites, 4 objects, and 16 px wide sits well inside the 64 px scanline budget. It also
means a hero that size costs 4 of the 64 OAM slots and 4 of the 8 slots on each of its two scanline
bands. `derived` from S3.

Sources disagree in one place and the disagreement is useful: S11 says the Castlevania 1 walk cycle is
a small number of frames plus idle, S12 describes the cycle through reuse rather than frame counts. The
one hard count for Castlevania 1 is 16 animation frames for the player character in total `[S10]`.

### 2.5 Windows, frames and fonts

The dark blue box with a light border, holding a menu and a line of stats, is the shared JRPG furniture
of this generation; both studied series use it and our title screen menu uses it by decision (PLAN-V2
section 2). What the sources above establish about it is only its content: a command list, HP and MP
digits, and a text line, all drawn on the 8 x 8 grid. `stated` for the content `[S7] [S8]`, `open` for
pixel measurements.

Consequences a frame reviewer can hold us to, all `derived` from section 1:

- Every window edge and border pixel sits on the 8 x 8 grid, so a border is a whole number of tiles
  thick, 1 or 2, and the box interior is a whole number of tiles.
- Text is 8 x 8 per glyph, one tile per character, so a 32 tile wide screen holds 32 characters.
- A window drawn from background tiles costs at most 3 colours plus the backdrop, and every 16 x 16
  region of it must pick one of the four background palettes.

## 3. Project numbers already decided (PLAN-V2 sections 2 and 3)

These are decisions, not history. They are repeated here so the checklist can test them.

| Item | Number | Where decided |
| --- | --- | --- |
| Overworld character sprite | 16 x 16 (2 x 2 tiles) | PLAN-V2 section 3 |
| Directions and walk frames | 4 directions x 2 frames = 8 poses | PLAN-V2 section 3 |
| Battle sprite size | about 16 x 32 or 24 x 32 | PLAN-V2 section 3 |
| Battle animation counts | idle 2, attack 3, hurt 1, down 1 | PLAN-V2 section 3 |
| Logo colours | 4 NES colours | PLAN-V2 section 2 |
| Menu window | dark blue box, white rounded border, hand or arrow cursor | PLAN-V2 section 2 |
| Font cell | 8 x 8 | PLAN-V2 section 2 |
| Colours on screen | at most 25 | PLAN-V2 section 2 |
| Palette sources | master palette only | PLAN-V2 section 2 |
| Sprite tile colours | 3 plus transparent | PLAN-V2 section 2 |
| Background area colours | 3 plus the shared backdrop, on 16 x 16 areas | PLAN-V2 section 2 |

A 16 x 16 overworld sprite with 8 poses costs 4 hardware sprites per pose in 8 x 8 mode (2 x 2), so 8
poses = 32 objects of the 64 available if every pose were on screen at once, which it never is. One
16 x 16 sprite uses 2 objects on each of its 2 scanline bands, so 4 such characters side by side on one
band hits the 8 per line ceiling exactly. `derived` from S3.

## 4. Checklist for reviewing a frame

Each line is pass or fail. Where a tool exists it is named; the rest are eye checks against section 1.
The manager does the eye checks.

| # | Check | Pass condition | How |
| --- | --- | --- | --- |
| C1 | Palette membership | every pixel is one of the 64 PPU colours | `python tools\nes_check.py <png> --type background` |
| C2 | Forbidden entry | $0D / #000000 used as black is never what makes a black area | eye: black must come from $0F, listed in the colour key |
| C3 | Colour count | 25 distinct colours or fewer in the whole frame | `nes_check` counts and fails above 25 |
| C4 | Grid | image width and height are multiples of 8 | `nes_check` |
| C5 | Background areas | each 16 x 16 area holds at most 3 colours plus the backdrop | `nes_check --type background` |
| C6 | Sprite tiles | each 8 x 8 sprite tile holds at most 3 opaque colours | `nes_check --type sprite` |
| C7 | Attribute alignment | every colour change in the background falls on a 16 x 16 boundary | eye plus the 3x preview |
| C8 | Sprite object budget | 64 or fewer sprite objects in the frame | eye on the sprite list, or `tools\inspect_frame.py` output |
| C9 | Scanline budget | 8 or fewer sprite objects overlapping on any scanline | eye on the sprite list; count per band |
| C10 | Wide objects | no sprite-built object is wider than 64 px on one scanline; anything wider is background | eye |
| C11 | Backdrop | exactly one backdrop colour in the frame, and it is the colour in background palette 0 entry 0 | eye |
| C12 | Text | every glyph occupies one 8 x 8 tile, baseline and cell edges on the grid | eye plus the 3x preview |
| C13 | Window frame | border thickness is a whole number of tiles, interior is whole tiles, no stray pixels | eye |
| C14 | Safe area | nothing that matters sits in the outer 8 px of the top or bottom (overscan, section 5) | eye on the 3x preview |
| C15 | Differentiating palette | the player character does not share a palette with the enemies | eye, per the Castlevania finding `[S12]` |
| C16 | Reuse | no two poses differ only by redraw where a tile flip or an existing half would do | judgement, per S10 and S12 |
| C17 | Honest documentation | the frame's colour key lists palette index, hex and role for every colour used | file check |

A frame that fails C1, C3, C4, C5 or C6 is not reviewable as NES art at all; those are hardware, not
style.

## 5. Open numbers, and the measurement that settles each

| Open question | Why it matters | How to settle it |
| --- | --- | --- |
| Exact overscan safe area in pixels | decides C14 | read NESdev wiki, "Overscan", and quote the 8 px figure |
| Final Fantasy II and III battle layout numbers | the card names FF1 to FF3; only FF1 layout is verified here | read a published analysis or watch a long play, then count the party column and monster field in tiles |
| Window border thickness in FF1 and DQ1, in tiles | the border design is a decided feature, its thickness is not sourced | count tiles on a screenshot; needs a vision pass by the manager |
| FF1 text cell metrics (8 x 8 versus 8 x 16 rows) | decides how many lines a window holds | same screenshot pass |
| Enemy sprite dimensions in FF1 and DQ1 to DQ4 | decides our battle enemy budget | count tiles on a screenshot; also check whether the monster is background or sprites by counting OAM in an emulator debugger |
| Castlevania 1 frame count per animation (walk, attack, hurt) | the 16 total is stated; the split is not | count from the published frame sheet reproduced in S10, or from a sprite analysis |
| Size of DQ4 monster sprites and whether they animate | DQ4 is the last of the four and the most advanced | analysis or long play |

None of these blocks the title screen cards: every title screen number in section 1 is sourced.

## 6. Sources

| Tag | Source | Link | Read |
| --- | --- | --- | --- |
| S1 | NESdev wiki, "PPU": 240 lines, 262 line NTSC frame, 20 vblank lines, 10 KB address space, about 2270 cycles after NMI, 2 KB VRAM, 3 PPU ticks per CPU cycle | https://www.nesdev.org/wiki/PPU | 2026-10-21 |
| S2 | NESdev wiki, "PPU palettes": 64 outputs of 6 bits, 4 background and 4 sprite palettes of 4, backdrop at entry 0 of palette 0, 16 x 16 attribute regions (8 x 1 with a mapper), sprite palette selection per object, hue $D dark grey, $E to $F mirrors of $1D, canonical black $0F, composite decode variation | https://www.nesdev.org/wiki/PPU_palettes | 2026-10-21 |
| S3 | NESdev wiki, "PPU OAM": 64 sprites of 4 bytes, 8x8 or 8x16, secondary OAM of 32 bytes so 8 sprites per scanline, priority by OAM order, flip bits, Y $EF to $FF hides, OAMDMA cost 513 to 514 cycles | https://www.nesdev.org/wiki/PPU_OAM | 2026-10-21 |
| S4 | NESdev wiki, "PPU attribute tables": 64 byte table per nametable, one palette per 16 x 16 pixels, common metatiles 16 x 16 and 32 x 32 | https://www.nesdev.org/wiki/PPU_attribute_tables | 2026-10-21 |
| S5 | nesdoug, "05. Palettes": 64 choices but many black, toolchain forces $0F for black and $30 for white, avoid the $xD colours | https://nesdoug.com/2018/09/05/05-palettes | 2026-10-21 |
| S6 | 8bitphoto, "NES Colour Palette", published 2026-09-05: 256 x 240, 64 hardware entries with 55 distinct usable colours, hex table, the 13 + 12 + 1 = 25 budget | https://8bitphoto.co.uk/palettes/nes.html | 2026-10-21 |
| S7 | Retrocean, "Dragon Quest (NES)": first person one enemy battles, static monsters with screen shake and red digits, no side or rear hero sprites, mirrored two frame walk, about 20 katakana glyphs, enlarged and faceted sprites in the US release | https://retrocean.com/nes/dragon-quest/ | 2026-10-21 |
| S8 | Retrocean, "Final Fantasy (NES)": four heroes stacked down the right edge, monsters left, terrain background, weapon swing and knee slump, class upgrade redraws sprites taller, four screens | https://retrocean.com/nes/final-fantasy/ | 2026-10-21 |
| S9 | Wikipedia, "Final Fantasy (video game)": the party on the right and the enemies on the left, instead of a first person view | https://en.wikipedia.org/wiki/Final_Fantasy_(video_game) | 2026-10-21 |
| S10 | GameAnim, "Original Castlevania Sprite Drawings", 2022: 16 animation frames in total for the player character, frames built from smaller tiles and reused | https://gameanim.com/2022/02/19/original-castlevania-sprite-drawings/ | 2026-10-21 |
| S11 | KartikChugh, "NES 4 Frame Walk Cycle", reproducing Dadako: 128 x 128 sprite sheet budget, 3 frame cycles, Castlevania III middle frame ping pong with idle fourth, Castlevania splits legs and torso; the 16 x 32, 16 x 24, 16 x 16 platformer hero sizes appear in the linked Castlevania Dungeon forum thread | https://github.com/KartikChugh/NES-4-Frame-Walk-Cycle | 2026-10-21 |
| S12 | Empty Armor, "The Genius of Castlevania's Pixel Art", video transcript: Simon's halves reused, dedicated palette without black while enemies hold black, subweapon frames reused from other tiles, whip upgrade redraw then recolour, 25 colours and 8 palettes of 3 | https://youtube.com/watch?v=l_W9Yuqm8Ns | 2026-10-21 |

Confidence in this file as a whole: rules in section 1 are hardware documentation and are as firm as
that wiki; conventions in section 2 are one source each, mostly secondary analyses, and should be
re-read before they are quoted to anyone outside the project.


## RULE 0 (Nayil, 2026-10-22): palette first, synergy between background and sprites

Concept art, backgrounds and sprites are designed INSIDE the NES palette system, never converted into it afterwards.
1. Every scene starts from a palette set: 4 background palettes (3 colours each) and 4 sprite palettes (3 colours each),
   all sharing ONE backdrop colour, all colours picked from the 54 usable NES master colours. Write it down first
   (data\scene_palettes.json) and put it in the prompt or the brief.
2. A character sprite palette must separate from the background it stands on: at least 2 luminance steps (NES rows
   0 to 3) between the sprite's body colour and the background colour behind it, and a different hue family for the
   outline or the body. White clothing on a light background is refused (the white blob).
   Scope, gamedev ruling on card t_1c04d011 (2026-10-23), and it is the same intent, measured the only way it can be
   measured: the row gap and the white blob test are asked of a character or a prop, the object that stands on
   something. They are NOT asked of a tiled layer, a sheet that declares itself one in its sidecar or whose frame is
   bigger than a 32x32 battle figure (the title wordmark, the car, a window strip), because a layer has no feet and
   the row arithmetic cannot see what makes it read: the wordmark's ink $0F and its stone body $00 are both row 0
   while their luminances are 0.000 and 0.202.
   A tiled layer is held to the other half of the same intent: it must be tellable from the pixels it is drawn over,
   so its ink or its body has to clear 3:1 contrast (the WCAG large text floor already in tools\art\contrast_check.py)
   on every ground colour under it. tools\palette_synergy.py implements that as R1b overlay_contrast on exactly that
   size test, and prints "tiled layer so R1b" on the frame so nobody reads the pairing as skipped. Measured that day:
   the title wordmark passes on its own ground, ink $0F on the $12 sky 3.75:1 and stone $00 on the $0F backdrop
   5.03:1, with gold $28 at 3.16:1 on the sky. A character sprite's verdict is unchanged by this clause: every frame
   up to 32x32 that does not declare itself a layer is still judged by the row gap and the white blob exactly as
   written above.
   Amendment, gamedev ruling on card t_af6fd431 (2026-10-24): the size test is a proxy, and on battle figures it was
   reading the wrong object. A sheet is a tiled layer when the sheet declares itself one, not when it is 17 px wide.
   Every battle figure in this project is 24x32 or 32x32, so the text above classified all of them as layers and
   skipped the one rule that decides whether a figure can be drawn at all. A battle figure up to 32x32 is a figure:
   R6 is asked of it, and because twelve to sixteen 8x8 tiles cannot live under one three-entry palette, R6 is asked
   the way the hardware asks it, per 8x8 tile: every tile's opaque colour set has to be a subset of some sprite
   palette of the scene, one FAIL per uncovered tile with the tile's position and its colour set. A frame 16x16 and
   under keeps the whole-frame reading, so nothing already measured moves. Measured while
   the proxy stood: `navy_sailor.png`, the tutorial fight's enemy, reported PASS on `battle_deck_night` with
   "palettes that fit []" printed beside it, while no palette of that scene carried its declared triple $02 $0F $30.
   The ruling, the four deck triples it lands and the numbers are in `knowledge\PALETTE-RULINGS-2026-10-24.md`.
   Amendment, gamedev ruling on card t_50193088 (2026-10-24): the two-row gap is a READING of luminance, not a
   substitute for it, and measured on the 2C02 table it ranks some pairs backwards. Body $10 is one row from the
   backdrop $0F at 11.06:1 (the most readable thing a NES draws) and two rows from $30 at 1.85:1 (nearly one tone).
   So point 2 now has two instruments and EITHER one clears it: at least 2 rows apart, OR at least 3:1 contrast
   between the body's luminance and the ground's (the same WCAG large text floor the layer clause above already
   uses, so the file holds one number for "these can be told apart"). A pair is refused only when both are short,
   which keeps a mid body on a mid ground refused: $00 on $11 is one row apart at 1.00:1 and still FAILS. Measured
   on the four battle strips, this removes exactly one pair, `sailor_battle.png` frame 2's $10 on the deck's $0F
   backdrop, and changes nothing else on corridor, quay dusk, wardroom or deck.
   Amendment, gamedev ruling on card t_474cde50 (2026-10-25): what qualifies a sheet to declare itself a layer is
   that it has NO single ground, and that is measured, not argued from its size or its subject. Sweep the scene's
   own layer table over a scroll and read the window the sprite is drawn in: the exhaust puff's 16x16 window holds
   four entries in every frame, $0F black 72.7 percent, $0B green 15.4, $0C teal 6.0, $20 white 5.9, and its ends
   are 2C02 luminance rows 0 and 2, so no body can clear 3:1 on both (a body clearing $0B needs luminance 0.31 or
   more, one clearing $20 needs 0.30 or less) and no entry can be two rows from a ground that spans rows 0 and 2.
   Under R1b the same drawing passes on all four frames, ink $0C at 10.55:1 on the $20 marking and body $20 at
   19.77:1, 8.25:1 and 10.55:1 on the three dark grounds. A sheet with ONE ground is a figure however small it is,
   so the wheel, the driver busts and every walking sheet stay under the two instruments above; the declaration is
   granted per sheet with the sweep done, never claimed, and it is never a way around a figure that cannot be
   drawn. The title set, the numbers and what was left open are in `knowledge\PALETTE-RULINGS-2026-10-25.md`.
3. A sprite's 3 colours: 1 dark outline, 1 mid body, 1 accent or light. The hero palettes are reserved and reused
   (Percy blue and gold, Hadrian near black and purple, Zander light blue, Konrad grey and amber).
4. Backgrounds spend their 4 palettes by area (attribute 16x16 rule): sky, ground, buildings, accents. No palette
   crosses a 16x16 area boundary it does not own.
5. Concept art (Kaggle, Gemini) is only accepted after it is quantized to the scene's palette set and passes
   tools\palette_synergy.py. A pretty image that does not survive quantization is rejected, not patched later.
6. Every new scene, sprite sheet and concept round names its palette set in the card and in the output manifest.
Gamedev owns the palette decisions; others propose.


## RULE 1 (Nayil, 2026-10-22, card CAPTURE-QUIET): a proof run is silent and out of sight, or it does not run

The game window and its music kept opening by themselves while Nayil was at the PC and his partner was home. Every lane
that launches the built game, for a capture, a probe or a demo, obeys this rule from now on. It is not about the art; it
is here because the capture helpers are the tools that produce the art frames and the demo video, and every one of them
follows it.

1. PP_MUTE. The game reads the environment variable PP_MUTE at boot (game\scripts\pp_app\pp_app.gml,
   pp_app_mute_from_env) and, when it is "1", calls audio_master_gain(0) before any mode is entered. Nothing plays. A
   real player's launch leaves the variable unset and the game sounds as built.
2. Three quiet minutes. No worker opens a window unless the user has had no keyboard or mouse input for three minutes
   (tools\idle_check.py, the same GetLastInputInfo arithmetic the manager's guard uses). A launch that is refused says
   so in a P: line and exits 4; it is a skip, never a failure of the work, and the next run tries again.
3. Off the primary screen. The window is moved onto a monitor other than the primary one unless the run passes --show,
   so the screen Nayil is working on stays his.
4. Audio proofs are named. A card that has to prove a sound passes --sound, which clears PP_MUTE instead of setting it,
   and says in its report that the sound was real.
5. One implementation. tools\pp_launch.py holds the environment, the gate and the placement, and every launching tool
   goes through it: tools\capture_title.py, tools\play_demo.py, tools\inspect_frame.py, tools\probe_states.py,
   tools\measure_title_scroll.py and tools\_save_load_probe.py. tests\test_capture_quiet.py fails when a launch site
   drifts, so this rule is checked and not remembered.
