# SHIP TILES: the tile table the map wiring reads

Drawn by `tools/art/make_ship_tiles.py` for card t_a0c1bccf. Do not edit by hand: rerun the tool.

The sheet is `ship_tiles.png`, 128 by 48, 24 cells of 16 x 16, 24 tiles used. The manifest beside it (`ship_tiles.json`) is the machine readable copy of this table, and `data/tile_classes_ship.json` is the walkable classification the map reads, with the hatch and the rail marked by name.

Colours are ROLES with their 2C02 entry written down. The ten entries are the ones the ship's own background strip draws from (`tools/art/make_env_ship.py` PALETTE, lines 61 to 72), so the deck tiles and the ship battle strip cannot drift apart. Ten colours against the card's ceiling of 16.

## The colours

| role | 2C02 entry | hex | why that entry |
|---|---|---|---|
| `m` | $00 | `#7c7c7c` | steel mid: deck plates, the bulkhead face, the opening in a plate |
| `a` | $02 | `#0000bc` | sea deep: the water under the rail |
| `r` | $07 | `#881400` | rust dark: the shadow under a bar, risers, the warm dark in a joint |
| `k` | $0F | `#000000` | backdrop: the hatch void, seams, the drop beyond the rail |
| `l` | $10 | `#bcbcbc` | steel light: lit plate edges, rails, rivets, ladder stringers |
| `b` | $12 | `#0058f8` | sea mid: one step of swell above the deep |
| `o` | $17 | `#e45c10` | rust: pipe bodies, the terminal bezel, the dark side of the brass |
| `c` | $21 | `#3cbcfc` | sea crest and the terminal's screen |
| `y` | $28 | `#f8b800` | brass and hazard yellow: the porthole ring, the keypad, the stripes |
| `w` | $30 | `#fcfcfc` | white paint: the walkway line, lamp glass, foam on a crest |

## The four background palettes

| palette | roles | 2C02 entries | what it draws |
|---|---|---|---|
| `bg0_deck` | `m`, `l`, `w` | $00, $10, $30 | the deck itself and everything painted on it: plate, line, hatch, sill, lamp |
| `bg1_hold` | `m`, `r`, `l` | $00, $07, $10 | the hold's ironwork: grating, bulkhead, ladder, stairs, pipes, locker, crate, the rail |
| `bg2_sea` | `a`, `b`, `c` | $02, $12, $21 | the water under the rail: deep, swell, the crest and the foam at the hull |
| `bg3_fixture` | `y`, `o`, `c` | $28, $17, $21 | the things that are read rather than walked on: hazard paint, the porthole, the log terminal |

A 256 x 240 screen shows four background palettes at once, which is the whole set: the deck spends `bg0_deck` on its plates and paint, `bg1_hold` on the ironwork and the rail, `bg2_sea` on the water under the rail, and `bg3_fixture` on the hazard paint, the porthole and the terminal. No room needs a fifth choice, and no tile spends two.

## The tiles

| # | name | char | palette | walkable | climbable | marked | what it is |
|---|---|---|---|---|---|---|---|
| 0 | `deck_plate` | `.` | `bg0_deck` | yes |  |  | a plate of the deck: one plate a tile, seam on two edges, four rivets |
| 1 | `deck_plate_worn` | `,` | `bg0_deck` | yes |  |  | the same plate with tread scuffs, so a long deck is not one tile repeated |
| 2 | `deck_line` | `=` | `bg0_deck` | yes |  |  | the painted walkway line, two pixels wide, along the plate |
| 3 | `deck_grating` | `g` | `bg1_hold` | yes |  |  | open steel grating: a two pixel bar and a three pixel hole |
| 4 | `deck_grating_cross` | `G` | `bg1_hold` | yes |  |  | the grating with a raised centre member over it |
| 5 | `hatch_closed` | `H` | `bg0_deck` | no |  | flag=ship_door_open, hatch=closed | a closed deck hatch: frame, recessed face, the wheel |
| 6 | `hatch_open` | `h` | `bg0_deck` | yes | yes | hatch=open | the same hatch swung open: the void below and the tops of its ladder |
| 7 | `door_sill` | `s` | `bg0_deck` | yes |  |  | the sill across a watertight doorway, worn to the steel |
| 8 | `bulkhead_rivet` | `#` | `bg1_hold` | no |  |  | a riveted bulkhead: plate seam, a four by four rivet grid, dark base course |
| 9 | `bulkhead_plain` | `B` | `bg1_hold` | no |  |  | the same bulkhead with no rivets, lit along its top edge |
| 10 | `bulkhead_light` | `i` | `bg0_deck` | no |  |  | a bulkhead lamp and the first row of its spill |
| 11 | `ladder` | `L` | `bg1_hold` | yes | yes |  | a vertical ladder: two stringers, rungs every three pixels |
| 12 | `stairs_up` | `U` | `bg1_hold` | yes | yes |  | a short stair up to the weather deck, four treads |
| 13 | `pipe_run` | `p` | `bg1_hold` | no |  |  | a pipe run along a bulkhead, with two flanges and a lagging line |
| 14 | `locker` | `K` | `bg1_hold` | no |  |  | a steel locker: louvred door, handle, dark base |
| 15 | `crate` | `C` | `bg1_hold` | no |  |  | a crate in the hold, banded with a diagonal brace |
| 16 | `hazard_stripes` | `!` | `bg3_fixture` | yes |  |  | hazard paint: a yellow field, black diagonal stripes, rust at its edge |
| 17 | `rail_post` | `|` | `bg1_hold` | no |  | rail=True | a rail stanchion standing on the deck plate it guards |
| 18 | `rail_bar` | `-` | `bg1_hold` | no |  | rail=True | the rail bar and its shadow, on the deck plate at the ship's edge, with the water beyond |
| 19 | `porthole` | `O` | `bg3_fixture` | no |  |  | a brass porthole: ring, glass, the harbour showing through it |
| 20 | `log_terminal` | `T` | `bg3_fixture` | no |  |  | the log terminal face: screen with five text rows, keypad, one live indicator |
| 21 | `water_deep` | `~` | `bg2_sea` | no |  |  | the water under the rail, frame 1 of 2: deep blue, two swells, three glints |
| 22 | `water_swell` | `w` | `bg2_sea` | no |  |  | the water under the rail, frame 2 of 2: the swell moves two pixels and the glints swap |
| 23 | `water_edge` | `W` | `bg2_sea` | no |  |  | the waterline at the hull: crest against the steel, foam breaking |

## The hatch and the rail, as the class file marks them

- **The hatch.** `hatch_closed` at index 5 is not walkable: a shut hatch is a solid, and it is the cell the map blocks until the story flag `ship_door_open` clears (collision 2 in the `data/maps/all.json` convention). `hatch_open` at index 6 is walkable and climbable, and it is the cell the `ladder_down` trigger sits on.
- **The rail.** `rail_post` at index 17 and `rail_bar` at index 18 are not walkable: the rail is the edge of the ship, and the water at index 21 to 23 is under it. Both stand on the deck plate they guard, so a map places them on the ground layer in the row above the water.

## The geometry, as decisions with their reasons

- **tile**: 16 x 16 px, the NES attribute area exactly, so one tile is one palette choice and the art cuts into four 8 x 8 pattern tiles without a repaint
- **plate_pitch**: one plate per tile: a 1 px seam on the top and left edge means the seams line up across a run and the deck reads as plates rather than as a flat grey field
- **rivet_pitch**: 4 px between rivets, so a plate shows four rivets a side at this size and no more; a real rivet pitch of 75 mm would be a third of a pixel
- **grating_pitch**: 5 px: a 2 px bar and a 3 px hole, which is the smallest mesh that still reads as a hole at 16 px and keeps the holes square
- **bar_width**: 2 px: one pixel of bar is a hairline at 3x and closes up on a TV; three pixels turns the grating into a solid plate
- **step**: 3 px a step, four steps a tile: an adult's step is about 180 mm, so a 16 px tile is a little over two and a half metres of stair, and the tile is one storey-to-half-storey flight
- **ladder**: rungs every 3 px, rails 2 px, which is the same rung pitch the stairs use so a climb looks like one piece of geometry seen two ways
- **hatch**: a 14 px frame and a 10 px face: 2 px of frame is the only width at which a recess reads as a recess at this size, and the wheel is a 6 px cross so it is not mistaken for a bolt
- **rail**: a 2 px bar and a 4 px post, both standing on the deck plate they guard: the rail is the edge of the ship, so the row below it is water and the class file says you cannot walk past it
- **water**: a swell every 5 px and a glint every 6 px, offset 2 px between the two frames, so the sea moves without the pattern visibly scrolling
- **terminal**: a 12 by 8 px screen with five text rows at 2 px pitch, and a 3 by 3 keypad: the row pitch is the smallest that draws a line of text as a line rather than as a smear

## How to wire it

1. Every tile is 16 x 16, and index i in the sheet is `floor(i / 8)` rows down and `i % 8` cells across.
2. A tile draws from exactly one background palette, so a 16 x 16 attribute area can never carry a fourth colour. Give the area the palette named in the table and no other.
3. `water_deep` and `water_swell` are one animation at 2 frames a second: hold each for about 30 game frames, which is a swell and not a flicker. `water_edge` is the static waterline tile at the hull.
4. The deck objects (`hatch_closed`, `hatch_open`, `rail_post`, `rail_bar`, `bulkhead_light`, `locker`, `crate`) draw their own steel around them, so a map places them on the ground layer without a transparency pass.
5. The bulkhead pair `bulkhead_rivet` and `bulkhead_plain` tiles horizontally and vertically: both carry the seam on the top and left edge and the dark base course on the bottom row.
6. `data/tile_classes_ship.json` is the walkable answer for every tile and is the file the collision layer should read. It marks the hatch and the rail by name, and it carries the flag that opens the hatch.

## What this set does not do

1. **It does not repaint the ship's ten colours.** The palette is the one `make_env_ship.py` already uses for the ship battle strip, so the deck and the fight behind it are the same steel.
2. **It is not the wardroom.** The wooden wardroom floor, the table and the bunk are Percy's room and the wooded tiles in `make_env_ship.py`; this card is the steel the fight starts on.
3. **It carries no lettering.** The terminal's text rows are the rows, not words: a tile that baked in a line of log text would freeze one frame of dialogue into the map. The words come from the dialogue layer.
4. **It does not edit `data/maps/all.json`.** That row is read only for this card. Its `H` cell is written as walkable (collision 0) and gated by `story_flag`; if the wiring moves to this class file the closed hatch cell should become collision 2, and that is a change for the wiring card, not this one.
5. **It does not light the deck.** A lamp pool on a wet plate needs a lit-plate tile in a fifth palette, and four is all a screen has; the bulkhead lamp's spill stops at its own tile, which is the same limitation the drive set recorded.

