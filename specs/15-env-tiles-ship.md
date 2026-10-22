# Spec 15: Map 2 environment tiles, the small Royal Navy ship

Status: spec, 2026-10-21, card ENV-TILES (t_4f58c88d). Numbers are DECISIONS unless a source is named.
Sources this spec is written from: PLAN-V2-2026-10-21 section 0 (the reference rule), knowledge\CHARACTER-BIBLE.md
REVISION 2 (Percy Skye, 23, Royal Navy lieutenant, "the boss fight happens inside a Navy ship: grey steel corridors,
bulkheads, a wardroom"), knowledge\ART-BIBLE.md, spec 13 (the 8-bit look) and data\nes_palette.json.

Goal: a player walks into the ship from the harbour and reads, without a caption, "small modern warship, grey steel,
painted lines, hatches, a wooden wardroom, and a way down to the hold". Everything is drawn from geometry in one
deterministic Pillow script; nothing is ripped, traced or sampled from any game.

## What the player does with it

- Walks a corridor with two rooms off it, a ladder down to the lower deck, stairs up to the weather deck, and a hatch
  that opens onto Percy's wardroom (the boss room).
- Cannot walk through bulkheads, crates, pipes, machinery, bunks, tables or closed hatches. Can walk through an open
  hatch, a door sill and up a ladder or stairs.

## Colour rule (hardware, not taste)

- Stock NES: a background area of 16x16 pixels carries 3 colours plus the one shared backdrop; a sprite 8x8 tile
  carries 3 colours plus transparent.
- This scene uses 10 colours total, all exact Ricoh 2C02 outputs from `data\nes_palette.json`: black backdrop, three
  steel greys, three sea blues, rust dark, rust and brass.
- Every 16x16 tile carries at most 3 non backdrop colours, and every 8x8 quarter of it at most 3 opaque colours, so the
  art can be cut down to 8x8 pattern tiles without a repaint.
- Spec 13 allows 16 colours on screen; 10 is stricter, so both hold.

## Tiles (48, in a 16 column grid, 256x48 pixels)

Row 1, steel deck and walls: deck plates two variants, plain plate, grating, rivet plate, painted line horizontal,
painted line vertical, painted line corner, bulkhead with rivets, plain bulkhead, vent, bulkhead light.
Row 2, fittings and doors: hatch closed, hatch open, door sill, ladder, stairs up, stairs down, pipes, vertical pipe,
cable run, crate, crate stack, barrel, lifebuoy, hazard stripes, locker, porthole (frame 1 of 2).
Row 3, wardroom, harbour and sea: porthole frame 2, wardroom sign, machinery sign, bridge sign, wardroom wood floor
two variants, table, bunk, quay stone two variants, dark quay, quay cap, bollard, rail post, rail bar, water frame 1,
water frame 2, water edge, deep water, foam.

- Animations, both at 2 frames per second: `water_a` to `water_b` (the sea), `porthole_a` to `porthole_b` (glare
  moving across the glass).
- Solid flags live on the tile, not in the map: bulkheads, closed hatch, pipes, crates, barrel, locker, lifebuoy, signs,
  machinery, table, bunk, quay stone, bollard, rail, and every water tile are solid. Open hatch, door sill, ladder,
  stairs and every floor tile are not.

## Sample map (20x15, 300 cells)

`data\maps\ship_sample.json` holds this generator's Tiled map when that name is free, and
`data\maps\ship_sample_tiled.json` when another lane's map already owns the plain name. A foreign map is never
overwritten.

- Rows 2 to 6: officer cabin on the left (wood deck, bunk, locker, crate), wardroom in the middle (wood deck, table,
  barrel, lifebuoy), engine space on the right (grating, pipes and cable runs on the hull, hazard paint).
- Row 7: bulkhead with an open hatch into the cabin, an open hatch into the wardroom and a sill into the engine space.
- Rows 8 and 9: the corridor. Deck plates and rivets, the painted line down row 9, a lifebuoy on the port hull, and
  the closed hatch on the starboard hull which is the way out.
- Row 10: bulkhead to the hold with a two tile sill.
- Rows 11 to 13: the hold. Crates, barrel, hazard paint, stairs up at the starboard end and a ladder down beside them.
- Spawns: `player_start` at 2,8; `from_percy` at 18,8; `from_lower_deck` at 17,12.
- Exit triggers: `hatch_percy` on the closed hatch at 19,8 to `percy_wardroom` (gated by flag `ship_hatch_open`),
  `ladder_down` at 17,12 to `ship_lower_deck`, `stairs_up` at 17,11 to `ship_weather_deck`.
- Collision layer: `0` walkable, `1` blocked, `2` blocked until a story flag clears it (the `data\maps\all.json`
  convention). Every blocked cell is blocked because the tile above it is solid; the generator derives the layer from
  the tile flags so the two cannot disagree.

## Outputs, all deterministic

- `game\sprites_src\env\ts_ship.png` (256x48) with `ts_ship.json` beside it: name, frame_w 16, frame_h 16, frames 48,
  fps 0.
- `game\sprites_src\env\ts_ship_tiled.json`: Tiled 1.11 tileset, 48 tiles, tile names, solid and climb flags, palette
  group, per tile colour list, the two animations.
- the sample map above, with `tile_legend`, `spawns`, `collision_rows`, ground and collision layers and an object group
  of spawns and exits.
- `output\env_ship_preview.png` at 3x: the whole sheet with tile ids, the map, and the harbour strip in both water
  frames.

## Acceptance

1. `python tools\art\make_env_ship.py` then `python tools\check_env_tiles.py` exits 0, and the checker's facts read 10
   colours, worst 16x16 tile 3 colours, worst 8x8 tile 3 colours, nes_check 0, reachable cells equal walkable cells.
2. Two runs produce byte identical files (sha256 equal), so the committed art is the code.
3. The map is 20x15, every spawn sits on a walkable cell, and every walkable cell is reachable from `player_start`.
4. `python -m pytest tests\test_make_env_ship.py -q` passes.
5. Manual check by Nayil, on the 3x preview: the deck plates tile without a seam, the bulkhead rivet line reads as a
   wall, the open and closed hatches are told apart at a glance, the wardroom wood reads as a different room from the
   steel corridor, and the two water frames differ without looking like noise.
