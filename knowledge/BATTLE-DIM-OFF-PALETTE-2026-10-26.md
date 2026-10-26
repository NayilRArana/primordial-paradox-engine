# BATTLE-DIM finding, 2026-10-26: the 0.67 battle frames are the dodge phase's ink at 60 percent, not art

Card t_e92abcb0 (lane builder, node CitadelArana, measured on this PC). Every number below was measured here, on the
frames the testing lane kept from the 117.4 s resume recording of the same build. The commands and their output are in
the card's comment; the probe is `build\_probe_battle_dim.py`, its log `build\_probe_battle_dim.log`, and the three
frames are unmodified copies in `build\resume_frames\` whose sha256 is printed by the probe and matches
`<agent-runtime>\kanban\boards\nayil-ops\attachments\t_ecad67bd\`.

The card asked for one of two outputs: the backdrop's blue brought onto `data/palette.json`, or a written finding that
the rule and the palette file disagree about this blue, with the entry that should exist and the audit output that says
so. **This is neither.** The sheet already draws only colours the NES master list names, and no entry should be added,
because the deep blue is not an art colour at all: it is one legal colour blended with the ink role at 60 percent, and
the blend is the defect.

## The answer in one paragraph

The strip this fight draws is `bg_battle_deck_night.png` and its seven colours are all entries of
`data/nes_palette.json`, so the sheet can never contribute an off palette pixel. The two frames under the floor are the
battle screen's dodge phase, where `pp_dodge_arena.gml:201` draws one rectangle of the ink role (`#0b0b0f`) at alpha
0.6 over the whole 256x240 frame, exactly as spec 08 line 11 asks ("the rest of the field is dimmed by a 60 percent
black rectangle"). Every off palette colour in the 23.48 s frame is `out = 0.4 * in + 0.6 * ink` to within video
compression: the sky's `#0000bc` reads `(5,5,83)` where the arithmetic says `(6.6,6.6,83.0)`, and the sea's `#0000fc`
reads `(6,5,108)` where the arithmetic says `(6.6,6.6,109.8)`. Applying that same arithmetic to two battle frames of
the same recording that DO pass turns 0.9163 into 0.6678 and 0.9260 into 0.6833, against the report's under floor
samples of 0.6702 and 0.6720. The palette file is right; a blended ramp is what has no right to be on screen.

## 1. What the sheet is (measured, not argued)

- The fight is on `ship_small`, whose `room_palette` is `deck_day` (`data/maps/all.json:15`), and
  `pp_battle_bg_for_room()` maps `deck_day` to `deck_night` (`game/scripts/pp_battle_director/pp_battle_director.gml:851`).
  The frame confirms it: its sky is `(0,0,185)` and its upper band is `(0,0,252)`, which are the deck strip's
  `#0000bc` (29.6 pc of the sheet) and `#0000fc` (23.1 pc), and the corridor strip carries no `#0000fc` at all.
- The sheet's own colour list (`game/sprites_src/bg/bg_battle_deck_night.json`, `colours_used`) is `#000000`,
  `#0000bc`, `#0000fc`, `#0078f8`, `#3cbcfc`, `#7c7c7c`, `#fcfcfc`: 2C02 entries 15, 2, 1, 17, 33, 0 and 48. Every one
  of them is in `data/nes_palette.json`, which the capture's union measure already allows.
- `python tools\nes_check.py --type background --backdrop 15 game\sprites_src\bg\bg_battle_deck_night.png`
  prints `256x112 448 tiles 7 colours PASS`, exit 0. Run without `--backdrop 15` the same checker fails two 16x16
  areas, and that failure is the checker guessing the backdrop as `#0000bc` when the sheet's own JSON declares backdrop
  index 15 (`#000000`), not a colour the art spends.
- The frame's own measure with the verifier's two loaders: `tools/capture_first_fight.py` `game_palette()` (54) plus
  `tools/play_demo.py` `palette_entries()` (55) is the union of 109, and the same recording's frames read 0.9163
  (`f_0046.png`, the command window with `FIGHT POWER / TALK SPARE`) and 0.9260 (`f_0090.png`, the result panel). Both
  are above the 0.90 floor. The floor is met by the art as authored; nothing in the sheet needs repainting.

## 2. What the 0.67 frame is (measured)

Region by region, the same elements in a frame that passes and in the frame that fails:

| element | `f_0046.png` (menu phase) | `sample_20_23s48.png` (dodge phase) | `0.4 * in + 0.6 * (11,11,15)` |
| --- | --- | --- | --- |
| strip sky `#0000bc` | `(0,0,185)` | `(5,5,83)` | `(6.6, 6.6, 83.0)` |
| strip blue `#0000fc` | `(0,0,252)` | `(6,5,108)` | `(6.6, 6.6, 109.8)` |
| role `dim` `#4a4a58` | `(73,72,87)` | `(35,35,43)` | `(36.2, 36.2, 44.2)` |
| role `paper` `#1c1c24` | `(27,27,35)` | `(18,17,22)` | `(17.4, 17.4, 23.0)` |
| black `#000000` | `(0,0,0)` | `(6,5,8)` | `(6.6, 6.6, 9.0)` |

Five pairs, one linear blend, and the ink role is the blend's other side: the green column is
`pp_dodge_arena.gml:201` to `:203` read literally. Three further measurements say the same thing:

- The 23.48 s frame's darkest blue family (`r < 40`, `g < 40`, `60 < b < 130`) is 23.78 pc of the frame; the same class
  is 0.53 pc and 0.54 pc of `f_0046.png` and `f_0090.png`. The two frames that pass carry almost none of it.
- The frame carries no paper band at full brightness: its bottom 40 rows are `(18,17,22)` on 86 pc, the dimmed paper
  role. In `f_0046.png` the same band is `(27,27,35)` on 68 pc, the paper role undimmed. The command band is drawn
  after the arena's dim in the phases that have it, and the dodge phase has no command band, so nothing bright is left
  below the field.
- The arena's frame edge is on screen at full brightness: column `x = 629` of the 3x frame is `(74,74,88)` (the `dim`
  role) on 282 of the 313 rows from `y = 204` to `y = 516`, which is spec 08's box (`x1-2 .. x2+2` at
  `46..210`, `68..172` in NES pixels, times 3) drawn after the dim.

And the frame's three magenta squares are the arena's missing roles, not a compression artefact: `pp_arena_draw()` asks
for `hazard` (`:215`), `marker_trail` (`:227`) and `marker` (`:233`), none of which the `deck_day` set declares, so
`pp_role_colour()` returns `PP_COLOUR_MISSING` = `(255,0,255)` (`pp_config.gml:23`). The 23.48 s frame carries exactly
`(255,0,255)` at full brightness on 251 px, inside the arena box, while the two menu phase frames carry none. The game's
own log from the 2026-10-24 talk capture says it in words (`build\first_fight_talk_game.log:88` to `:90`):

    PP: role hazard is not in the room palette set deck_day, drawing it as PP_COLOUR_MISSING
    PP: role marker is not in the room palette set deck_day, drawing it as PP_COLOUR_MISSING
    PP: role marker_trail is not in the room palette set deck_day, drawing it as PP_COLOUR_MISSING

## 3. The proof: the same screen, the build's own dim applied

Take the two battle frames of the same recording that pass, apply `0.4 * in + 0.6 * ink` pixel by pixel, and measure
with the verifier's own `play_demo.palette_share`:

| frame | as recorded | with `pp_dodge_arena.gml:201` applied |
| --- | --- | --- |
| `f_0046.png` | 0.9163 | 0.6678 |
| `f_0090.png` | 0.9260 | 0.6833 |

The report's two under floor samples are 0.6702 (23.48 s) and 0.6720 (82.18 s). A 60 percent band of the ink role over
a battle frame lands on those numbers and nothing else in the code path does. This is the whole finding: the floor is
not measuring the art, it is measuring a blend the game draws on purpose.

## 4. Why no entry should be added to `data/palette.json`

1. A blend is a continuum, not a colour. The frame's blue class alone spans `(5,5,83)`, `(6,5,108)`, `(6,4,112)`,
   `(7,5,83)`, `(6,6,84)`, `(5,6,108)` and thousands of intermediate tones between the sheet's colours and the ink. An
   appended entry would name one point of that ramp and leave the rest exactly as red as before, so it would not even
   turn the measure green; and if it did, it would be a green bought by writing down the output of a blend.
2. The rule already forbids the blend. `specs/13-8bit-look.md:21` allows two dither patterns and says "A gradient is a
   stack of those, never a blended ramp", and `:44` says the veil is "a 25 percent dither over the world rather than a
   transparency effect". The codebase already follows that where it matters: `pp_overworld.gml:579` calls a full frame
   statement "a palette change, never a blend, so the screen still spends one declared colour" (card t_531bc76c). The
   dodge dim is the one full frame statement that does not.
3. `data/palette.json` is frozen at 54 (`frozen: 54`, `frozen_digest` at line 7) and an append past index 53 is its own
   decision, which this card must not take on the strength of one blended frame.

The nearest entry to the offending blue is `data/palette.json[44] #271640` (the purple family) at distance 44, and
`#271640` is not it either: at 44 px away nothing in a 54 colour palette is close, which is the honest signal that the
pixel was never an entry in the first place.

## 5. What the audit says, and what it does not say

`knowledge/NES-AUDIT.md` line 12 reads `frame | 25 | 15 | 10 | 0 | 25 of 25`: ten finished frames fail. None of them
fails on this blue, and none of them is a recording. The ten are the design palette's role hex values not being PPU
outputs (`#1c1c24`, `#4a4a58`, `#0b0b0f`, `#c8c8d4` are named in the proposed fixes for
`output/bg_battle_deck_night_text_preview.png`) plus attribute areas carrying four colours where the rule allows three.
That is the open question at `knowledge/PALETTE-SYNERGY.md:261` (should the room palette roles resolve into
`data/nes_palette.json`?), and it is not this card's blue.

So the card's line "the same class the audit counted as the 9 frame-class palette violations" does not hold as written:
the audit's frame failures and this frame's blue are two different defects, and `python tools\palette_synergy.py --gate`
reports `10 entry(ies), 0 gated failure(s), 3 advisory failure(s)` on the sheets, none of them about a dim.

## 6. What a fix measures (simulated on the two passing battle frames, not recorded)

| dim over the same frame | `f_0046.png` | `f_0090.png` |
| --- | --- | --- |
| none, as recorded | 0.9163 | 0.9260 |
| ink at alpha 0.6, what the build draws | 0.6678 | 0.6833 |
| 50 percent checker in ink, 1 px | 0.9582 | 0.9630 |
| 50 percent checker in ink, 8 px cells | 0.9586 | 0.9635 |
| 25 percent dither in ink | 0.9373 | 0.9448 |

The three dithers are the two patterns spec 13 allows. They are offered as measurement, not as a design decision: a
dither is a different look from a 60 percent band and the choice between them is not a builder's.

## 7. The decision this card cannot make, and the two routes

Route A, the game changes: the dodge dim stops being a blend and becomes an opaque statement, either a dither of the
ink role (measured above, 0.937 to 0.964) or the field redrawn in the room's `dim` role. `pp_dodge_arena.gml` is
gamedev's file, and the look changes.

Route B, the spec stands and the verifier changes: spec 08 keeps its 60 percent rectangle and a dimmed frame stops
being asked to pass a floor designed to keep a terminal screenshot out. That needs the sampling to skip the dodge
phase, which is a testing lane change and a ruling on what the floor is for.

Both routes also need the `deck_day` role gap answered, because even undimmed the arena draws magenta: the set carries
14 of its 16 allowed roles (`data/room_palettes.json:22`), so `hazard`, `marker` and `marker_trail` cannot all be added
without a decision about which colours the demo's fight spends.

Nothing in either route lowers `VIDEO_PICTURE_MIN`, widens the 12 px tolerance, or edits a frame.

## 8. What I assess the frame to be, by eye and by arithmetic

`build/first_fight_sample_20.png` from the card's own run is not this frame; the frame named here is
`build\resume_frames\sample_20_23s48.png`, the 23.48 s frame of the resume recording. It is a real battle screen of the
dodge phase on the small ship's night deck: the field strip dimmed to 40 percent brightness, the arena's 2 px frame on
screen at `x = 629` and across the top, the enemy and the party column visible only as dimmed sheets, `HP 20/20` and
`WILL 3/3` on the row inside the arena box, and three hazard and marker shapes in `(255,0,255)` because the set they
stand on does not declare the roles. Nothing about it is a terminal, a window frame or a broken sheet. Its 0.6702 is a
faithful measurement of a 40 percent brightness blended screen, and that measurement is correct: the screen is the thing
that is off the rule.

## 9. What was not done

No threshold moved (`VIDEO_PICTURE_MIN` is 0.90 in `tools/capture_first_fight.py:773`, `palette_share` still allows 12),
no frame, recording or report edited or re-recorded, no entry appended to `data/palette.json` and its digest untouched,
nothing posted or published, no window opened, no game build run, `a protected profile` untouched. The three frames were
copied into `build\resume_frames\` for the probe and are byte identical to the kanban attachments.
