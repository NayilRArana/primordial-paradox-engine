# DRIVE TILES: the tile table the map wiring reads

Drawn by `tools/art/make_drive_tiles.py` for card t_d0e73725. Do not edit by hand: rerun the tool.

The sheet is `drive_tiles.png`, 128 by 48, 24 cells of 16 x 16, 24 tiles used. The manifest beside it (`drive_tiles.json`) is the machine readable copy of this table, and `data/tile_classes_drive.json` is the walkable classification the map reads.

The art root here is the card's `assets/tiles/drive/`, not `game/sprites_src/env/`. R46 QUAY-TILES put its sheet in the second place while the roadmap declared the first, which the cleanroom recheck recorded as catalog drift (`knowledge/CLEANROOM-RECHECK-2026-10-24.md`, R46 row). This sheet sits where the card says, so `tools/sync_art.py` and the map wiring must look here for it. That is a note for the wiring card, not a change this card makes.

## The scale, and where every number comes from

| fact | value | source |
|---|---|---|
| metres per tile | 8.0 | `tools/osm_to_map.py` `METRES_PER_TILE` at `TILE_PX` 16 |
| metres per pixel | 0.5 | derived: 8 m / 16 px |
| corridor width | 2 tiles = 16 m | `tools/osm_to_map.py` paints `road_major` 2 tiles wide; 3 lanes at 3.65 m plus a 3.3 m shoulder is 14.3 m, so one tile cannot hold it |
| lane width | 7 px = 3.5 m | 3.65 m a lane, rounded to the pixel |
| line paint | 1 px = 0.5 m | the narrowest thing the PPU draws; the paint is 0.15 m in life |
| lane line cycle | 4 px on, 12 px off = one tile | 2 m mark, 6 m gap: the tile is exactly one cycle |

## The four background palettes

| palette | roles | 2C02 entries | what it draws |
|---|---|---|---|
| `bg0_asphalt` | `asphalt`, `dim`, `bright` | $0F, $00, $20 | the corridor: tarmac, the shade under a line, the paint |
| `bg1_verge` | `green_deep`, `green_mid`, `green_pale` | $0B, $0A, $1A | the night verge: the floor, the blades, the moonlit tips |
| `bg2_sign` | `green_lit`, `green_mid`, `bright` | $09, $0A, $20 | the gantry's sign face, its dark rear, and the lit border |
| `bg3_lamp` | `gold`, `stone_mid`, `green_mid` | $38, $08, $0A | the roadside fittings: the sodium head, the stone, the grass at their feet |

## The colours

| role | role in data/palette.json | 2C02 entry | hex | why that entry |
|---|---|---|---|---|
| `dim` | `grey_3`, index 3 | $00 | `#7c7c7c` | road grain, the shade under a line, the barrier face |
| `stone_mid` | `stone_2`, index 32 | $08 | `#503000` | the kerb face, the marker post, the lamp column |
| `green_lit` | `moss_3`, index 27 | $09 | `#007800` | the gantry sign's face, as the drive's own sign uses it |
| `green_mid` | `moss_2`, index 26 | $0A | `#006800` | the grass blades and the kerb's grass above it |
| `green_deep` | `moss_1`, index 25 | $0B | `#005800` | the verge floor and the mass of the hedge |
| `asphalt` | `grey_1`, index 1 | $0F | `#000000` | the tarmac, and the steel of the gantry in the dark |
| `green_pale` | `moss_5`, index 29 | $1A | `#00a800` | the moonlit tips of the grass and the hedge's top edge |
| `bright` | `grey_5`, index 5 | $20 | `#f8f8f8` | lane paint, the sign border, the lit rail edge |
| `gold` | `gold_5`, index 41 | $38 | `#f8d878` | the sodium lamp head and the marker's reflector |

9 roles, 9 distinct colours on the sheet, against the card's ceiling of 16.

## The tiles

| # | name | char | palette | walkable | blob test | what it is |
|---|---|---|---|---|---|---|
| 0 | `road_surface` | `a` | `bg0_asphalt` | yes | n/a (light 9%, 0 rows no dark, 35 runs, 177 inner dark) | the carriageway between the lines |
| 1 | `road_surface_worn` | `b` | `bg0_asphalt` | yes | n/a (light 16%, 0 rows no dark, 31 runs, 167 inner dark) | the same tarmac with a reinstatement seam across it |
| 2 | `road_lane_dash` | `c` | `bg0_asphalt` | yes | n/a (light 2%, 0 rows no dark, 36 runs, 173 inner dark) | the lane line: 2 m of paint in a 6 m gap, one 8 m tile |
| 3 | `road_edge_line` | `d` | `bg0_asphalt` | yes | n/a (light 6%, 2 rows no dark, 30 runs, 157 inner dark) | the continuous edge line at the outside of the corridor |
| 4 | `road_shoulder` | `e` | `bg0_asphalt` | yes | n/a (light 6%, 1 rows no dark, 33 runs, 112 inner dark) | the hard shoulder, 3.3 m, inside its own white line |
| 5 | `road_wet` | `f` | `bg0_asphalt` | yes | n/a (light 2%, 0 rows no dark, 33 runs, 146 inner dark) | the surface in rain: the sheen and the glints of shot 4 |
| 6 | `road_stud` | `g` | `bg0_asphalt` | yes | n/a (light 2%, 0 rows no dark, 38 runs, 171 inner dark) | a cat's eye in the lane line, the one thing on the road that reflects |
| 7 | `road_single_lane` | `h` | `bg0_asphalt` | yes | n/a (light 12%, 4 rows no dark, 25 runs, 127 inner dark) | the slip road narrowing to one lane, both edges painted |
| 8 | `verge_grass` | `i` | `bg1_verge` | yes | n/a (light 2%, 0 rows no dark, 63 runs, 156 inner dark) | the night verge: blades on a dark floor, tips catching the moon |
| 9 | `verge_tuft` | `j` | `bg1_verge` | yes | n/a (light 3%, 0 rows no dark, 41 runs, 145 inner dark) | a denser clump for the verges between the posts |
| 10 | `hedge_night` | `k` | `bg1_verge` | no | n/a (light 4%, 4 rows no dark, 17 runs, 52 inner dark) | the hedge mass that closes the far side of the roadside |
| 11 | `verge_shadow` | `l` | `bg1_verge` | yes | n/a (light 33%, 5 rows no dark, 15 runs, 136 inner dark) | the dark band under the hedge, so its foot does not float |
| 12 | `kerb` | `m` | `bg3_lamp` | yes | n/a (light 38%, 6 rows no dark, 20 runs, 9 inner dark) | the kerb between verge and tarmac, 3 m of stone across the tile |
| 13 | `marker_post` | `n` | `bg3_lamp` | no | PASS (light 2%, 0 rows no dark, 18 runs, 174 inner dark) | the roadside marker post with its amber reflector |
| 14 | `lamp_post` | `o` | `bg3_lamp` | no | PASS (light 7%, 0 rows no dark, 16 runs, 188 inner dark) | the lamp column: sodium lighting is why the extract is tagged lit=yes |
| 15 | `lamp_head` | `p` | `bg3_lamp` | no | PASS (light 20%, 0 rows no dark, 35 runs, 145 inner dark) | the sodium head and the first rows of its cone |
| 16 | `gantry_beam` | `q` | `bg0_asphalt` | no | n/a (light 3%, 2 rows no dark, 27 runs, 154 inner dark) | the gantry's horizontal lattice member |
| 17 | `gantry_leg` | `r` | `bg0_asphalt` | no | n/a (light 3%, 0 rows no dark, 61 runs, 154 inner dark) | the gantry's upright lattice leg, standing on the verge |
| 18 | `gantry_sign_panel` | `s` | `bg2_sign` | no | n/a (light 22%, 15 rows no dark, 1 runs, 0 inner dark) | the green sign face; the miles come from spr_title_sign, not from this tile |
| 19 | `gantry_sign_edge` | `t` | `bg2_sign` | no | n/a (light 9%, 15 rows no dark, 1 runs, 0 inner dark) | the panel's lit top rim, for the top row of a two tile sign |
| 20 | `gantry_sign_back` | `u` | `bg2_sign` | no | n/a (light 6%, 15 rows no dark, 1 runs, 0 inner dark) | the rear of the sign, which is what the car sees after it has passed |
| 21 | `barrier_rail` | `v` | `bg0_asphalt` | no | n/a (light 12%, 4 rows no dark, 21 runs, 131 inner dark) | the steel safety barrier in its two bands |
| 22 | `barrier_post` | `w` | `bg0_asphalt` | no | n/a (light 1%, 0 rows no dark, 32 runs, 154 inner dark) | the post the barrier rail hangs on |
| 23 | `barrier_end` | `x` | `bg0_asphalt` | no | PASS (light 1%, 0 rows no dark, 18 runs, 194 inner dark) | the terminal where a barrier run ramps down into the ground |

## Where each tile's shape comes from

- **a33_lanes**: A33 Town Quay way/8150576, highway=primary, lanes=3, surface=asphalt, lit=yes, oneway=yes, 30 mph (data/osm_cache/southampton_town_quay.json)
- **a33_lanes4**: A33 way/24594762, highway=primary, lanes=4, surface=asphalt, lit=yes (data/osm_cache/southampton_town_quay.json)
- **barrier_none**: the extracts carry barrier= only 4 times (city_wall twice, wall twice) and no safety barrier, so the motorway barrier is not in the extract
- **dest**: Bridge Street way/406370787, destination:lanes:backward=A3211|A23: a sign that names the destination of the lanes under it (data/osm_cache/westminster_big_ben.json)
- **lit**: lit=yes is tagged on 125 of the 237 highway ways in data/osm_cache/southampton_town_quay.json
- **motorway_spec**: SPEC: the M3 is a motorway, so the corridor has a hard shoulder and a safety barrier; the drive shot list puts a gantry over it (knowledge/DRIVE-SHOT-LIST.md sections 3 and 5)
- **shoulder_no**: shoulder=no is tagged on 9 primary ways in data/osm_cache/westminster_big_ben.json (Parliament Square, Westminster Bridge, Broad Sanctuary), so a hard shoulder is not in the extract
- **width7**: A3211 Victoria Embankment way/236139546, width=7, lane_markings=no, oneway=yes, lit=yes (data/osm_cache/westminster_big_ben.json)

## How to wire it

1. Every tile is 16 x 16, and index i in the sheet is `floor(i / 8)` rows down and `i % 8` cells across.
2. A tile draws from exactly one background palette, so a 16 x 16 attribute area can never carry a fourth colour. Give the area the palette named in the table and no other.
3. The corridor is two tiles wide. Put `road_shoulder` on the outside and `road_lane_dash` between the two lanes; `road_edge_line` closes the inner edge.
4. `road_lane_dash` tiles horizontally: 4 px of paint, 12 px of tarmac, one 8 m cycle. Do not scale it.
5. Objects sit on the ground they stand on: `marker_post`, `lamp_post` and `barrier_end` include the grass or tarmac at their feet, so a map can place them without a transparency pass.
6. The sign face carries no lettering. The miles come from `spr_title_sign`'s four frames, which the drive draws over this panel; a tile that baked in SOUTHAMPTON 55 would freeze one sign into the map.
7. `data/tile_classes_drive.json` is the walkable answer for every tile and is the file the collision layer should read; it carries the ODbL line in its header because the geometry is derived OSM data.

## What this set does not do

1. **It is not the whole picture.** Sky, clouds, the downs and the chalk cutting are scrolling layers in `game/sprites_src/title/`, not tiles; this set is the corridor floor and its fittings.
2. **There is no hard shoulder source in the extract.** `shoulder=no` is tagged on the Westminster primary roads, so the shoulder, the safety barrier and the gantry are drawn from the drive's own facts (the M3 is a motorway) and are marked SPEC in the source table above.
3. **The lane line is the 8 m cycle, not the 9 m motorway one.** A 2 m mark and a 7 m gap is 9 m and would need a 3 tile repeat, so this sheet uses the cycle that fits the tile and says so.
4. **There is no lighting spill across tile edges.** Three colours and the backdrop per area means the lamp's cone stops at the tile; a spill needs a second lit-surface tile in the lamp palette, which the four palette budget cannot buy until the wiring card says which palette the scene can spare.
5. **No cat's eye in amber.** The stud is drawn in paint white because amber lives in the lamp palette and the corridor palette has no room for it; the amber reflector is on `marker_post` instead.

