# Spec 14: title screen, "The Drive to Southampton"

Director: Claude manager, 2026-10-20, from Nayil's brief: Kronos is driving Zeus from London to Southampton; the car drives across the English countryside; that is the title screen, plus a nice logo. Everything original (clean-room rule). Replaces the night sky and sea plan in TS1-ART.

## The two reincarnations (names settled 2026-10-22, card t_e4f8bcae: they are the cast in knowledge\CHARACTER-BIBLE.md)
- **Kronos -> Konrad Skye.** 47, AI research scientist. Long blond hair streaked with white and grey, a close beard, a charcoal blazer or dark knit over an open collar shirt, ID lanyard, wristwatch. Calm, heavy presence, and the driver. Tells: checks his wristwatch constantly; a small sickle shaped keyring swings from the ignition.
- **Zeus -> Zander Skye.** 19, first year student. Messy blond hair, an oversized bomber jacket in LIGHT BLUE (CHARACTER-BIBLE says light blue, not green), wired earbuds. Tells: tiny static sparks off his hair when annoyed; a small grey storm cloud follows the car the whole way.
- Ronan Harrow and Theo Skye were this spec's own first picks and are retired: NAMES-BIBLE section 2 judged both superseded, and the two busts that carry these roles were renamed `spr_title_konrad` and `spr_title_zander` on 2026-10-22. The roles, the bust geometry, the tells and the watch glance are unchanged; only the names and, in the busts, the costume still to be redrawn.
- The irony the scene plays: the father who swallowed his children is now driving his son to the port (Southampton, where the ship of Map 2 leaves). Neither knows who they were.

## Scene layout (side view, car drives left to right, camera follows the car so the world scrolls right to left)
Base resolution and the 16 colour palette come from spec 13; integer scale, point sampling.
Parallax layers, back to front, with scroll speed relative to the road:
1. Sky gradient (static), soft afternoon going to golden hour over the 60 second loop (3 palette steps, no smooth blend).
2. Clouds, 0.05x, plus Zander's personal storm cloud: a small dark cloud that stays above the car (moves with the camera, not the world), with a 1 frame lightning flicker every 8 to 12 seconds.
3. Chalk downs and distant hills, 0.15x, with a white chalk horse figure on one hill (original drawing) and a far church spire.
4. Mid fields, 0.35x: patchwork fields, hedgerow lines, oak trees, a windmill or a stone farmhouse, sheep that occasionally turn their heads.
5. Near verge, 0.7x: dry stone wall, hedge, telegraph poles, a red phone box once per loop, a road sign that counts down SOUTHAMPTON 74, 52, 31, 9 across one loop.
6. Road, 1.0x: a two lane country A road with dashed centre line.
7. Foreground blur, 1.3x: occasional grass tufts and a fence post passing in front of the car.

## The car
- An original small, slightly battered British hatchback (think boxy 1980s family car, not any real model or badge). The body is near white ($20) so the car holds apart from the road it drives on; the racing green ($0B) is its shadow side, running along the bottom of the body, the sills, the arches and the tyres, and the darkest teal ($0C) takes the glass, the shut lines and the outline. There is no mismatched door. Roof rack with a suitcase strapped on (Zander's luggage for the ship). Colour decided in knowledge/PALETTE-RULINGS-2026-10-24.md section 11 Q2; the sheet is game/sprites_src/title/spr_title_car.png, three entries and no fourth.
- Animation: 4 frame wheels; body bob of 1 px on a 6 frame cycle; exhaust puff every 20 frames; headlights off until golden hour, then on.
- Through the windows, two bust sprites: Konrad driving (right side of the car, British), Zander in the passenger seat. Idle loops: Konrad glances at his watch (8 frames, every 6 seconds), Zander bobs his head to music (4 frames) and once per loop turns to say something, a tiny speech bubble with "..." appears and Konrad does not react.

## Logo
PRIMORDIAL PARADOX, big chunky pixel letters, two lines, sitting in the sky top centre. Style: weathered stone letters (Titan age) with a thin gold inlay, and a small lightning crack running through the second O of PARADOX; 1 px dark outline; 2 frame gold shimmer every 4 seconds. Under it, small text in our font: PRESS Z OR ENTER (blinking), and after the press the menu NEW GAME, CONTINUE, SETTINGS, QUIT.

## Sound hooks (no audio files required)
Cue ids through the audio bus: title_theme (loop), car_engine_loop, menu_move, menu_select, thunder_soft (with the lightning flicker).

## Deliverables and checks
- Art: tools\art\make_title_art.py generates every sprite and background above with Pillow, deterministic (same hashes on rerun); output\title_art_contact.png shows every asset at 3x, labelled; output\title_scene_preview.gif renders 10 seconds of the parallax plus car animation offline (no GameMaker, no window) so the director can judge motion before integration.
- Game: rm_pp_title as described in TS1-CODE; run check captures output\title_run_1.png (scene plus logo) and output\title_run_2.png (menu).
- The director accepts only after viewing the contact sheet, the gif and both run captures.

## Addendum 2026-10-20 (from Nayil's notebook, page 5): night drive, waltz, pan down
Nayil's own note: "Intro: A minor waltz while intro text scrolls. Starry night drive, English countryside, pan down." This overrides the golden hour idea above: the drive is at NIGHT under stars (sky gradient deep blue to near black, 2 star layers, a moon, headlights ON the whole time, road lit by headlights, windows of farmhouses glowing, the car's dash glow on both faces). The 3 step sky shift becomes a slow moon rise and a faint aurora-free star twinkle. The theme is cue PP-01, the A minor waltz with the Kronos family leitmotif (see notes\notebook-2026-10-19\round1\musician.md section 3), cue id title_theme. After NEW GAME, the camera pans down from the night sky to the road and the car, the intro text scrolls over it in time with the waltz, then fade to Map 2. Storm cloud stays (lightning flicker becomes a soft distant flash).

## Addendum 2026-10-21 (PLAN-V2 section 2): the night art redrawn to the hardware rule, TS2-ART-B

What the player sees, in order of what is nearest:

- Seven seamless night layers on a 512 px loop, back to front: sky (moon, stars, a faint sickle and a thunderbolt a
  player can trace), thin cloud, chalk downs (Twyford Down chalk cutting, Winchester Cathedral far off as a long nave
  with a square tower), patchwork fields and hedgerows, the verge (hedge, dry stone wall, sign posts), the road with
  lane markings, and foreground grass and fence posts.
- A green UK motorway sign reading SOUTHAMPTON, in four frames: 31, 22, 13 and 4 miles. The sign is a sprite, drawn
  over the posts, because the countdown changes and the posts scroll with the verge.
- The headlight cone is its own sprite, drawn over the road, because a cone baked into the 512 px road would repeat.
- A lightning flash swaps the whole screen to a second palette for 2 frames: every colour one step up its own ramp of
  the NES master palette, in data\title_flash.json. The flash strips are the normal strips drawn with it.
- Opening shot: one 256 by 240 background of Big Ben at night (original drawing, clock face in gold, the Palace along
  the horizon, the road leaving the bottom of the frame), for the camera pan down.

The rule every background here is held to: 16 by 16 attribute areas, three colours plus that layer's shared backdrop,
colours from data\palette.json only, at most 16 colours on a screen. tools\art\nes_bg.py solves and then checks it;
tools\art\measure_compose_areas.py reports the composed screen per area.

Acceptance for TS2-ART-B: the generator exits 0, nes_bg check passes on all eight backgrounds, every scrolling layer's
wrap edge is no sharper than its own interior, the suite covers those, and the 3x previews output\ts2_world_preview.png
and output\ts2_bigben_preview.png exist at 768 by 720 for the director's eyes.

Known limit, stated so it is not discovered later: the rule passes layer by layer, but where two layers overlap inside
one 16 by 16 screen area (the road, verge and foreground band) the composed area carries more than three colours plus a
backdrop. Bringing the composite inside the single universal backdrop reading is a composition change and belongs to a
follow-up card, not to this one.

## Addendum 2026-10-22 (TEXT-REVEAL-2): the intro crawl is a layout over the one reveal machine

Written before the change, because the card asks for the difference in prose first.

The two pauses, and why they are not the same thing:

- A punctuation pause is inside a line. It follows a character that is already on screen (a full stop, a question or an
  exclamation holds 8 steps, a comma 3), and the next character of the SAME line appears after it. It is a property of
  the text: a sentence has a rhythm.
- A beat pause is between lines. It follows the last line of a beat and holds 72 steps (1.2 s at 126 bpm, from
  data\intro_text.json) before any character of the next beat appears. Inside a beat one line follows the previous one
  with no hold at all. It is a property of the page: a reader stops between thoughts, not between rows.

Decision: one beat is one unit of pp_text, and the beat pause is the machine's gap at a unit end (the same
`max(wait, gap)` an auto advancing layout already uses). It is not an item hold. Reason: the machine already has one
definition of the end of a thought, and the beat is the crawl's end of thought; an item hold would put a second timing
mechanism inside the item list, which this card forbids. The consequence is that a unit is a beat and never a line:
pp_title draws the rows of the beat being typed and keeps no reveal state of its own.

The title's numbers are handed to the machine as settings (`pp_text_reveal_timing`), so pp_title keeps its values and
pp_text keeps the mechanism:

| what | value | source |
| --- | --- | --- |
| steps per character | 3.3333 (60 / 18) | data\title_timing.json text.chars_per_second |
| gap at a unit end (the beat pause) | 72 | text.pause_after_beat_seconds 1.2 at 60 steps a second |
| blip interval | 3 | text.blip_every_chars |
| lines on screen | 6 | text.lines_on_screen |

The skip (start, Z or X) is `pp_text_reveal_finish`: the last beat is shown whole, then the 60 step hold, then the run.
The pan, the two fades, the stars, the duck under the words and the room move are unchanged.

Pacing, measured, which is the delta the card requires before the pacing may move at all. The old algorithm was run
offline over data\intro_text.json as it stands (1221 steps), and the new one was measured on the engine itself, by the
intro step the game reported when the machine's done predicate first held:

- Before: 1221 steps (20.35 s) for the 14 rows. After: 1238 steps (20.63 s), measured as intro step 540 to intro step
  1777 in the run of 2026-10-22. That is +17 steps, +0.28 s, +1.4 percent.
- The offline mirror of the new algorithm predicts 1239 steps, one more than the engine measured, because the mirror
  counts a step before the first one the game steps the crawl on. The engine is the authority.
- Rows 1 and 2 (THE GODS NEVER DIED. and THEY WERE FORGOTTEN,) finish on exactly the same step as before; the other
  twelve finish 2 to 18 steps later.
- Two causes, both of them a machine rule applied to this text for the first time: the punctuation holds inside a line
  (+23 steps over the crawl), and the fractional step count now being carried across a row break instead of dropped
  (-5 steps). The old reveal reset its timer at every row end and ignored punctuation.

Acceptance for this addendum: tests\test_text_reveal.py audits pp_title by name (a step count, a pause or a blip
interval outside pp_text fails the suite), a real Igor Compile and Igor Run with the title up, capture_title.py exit 0
with both frames, a key scripted capture with the crawl mid reveal and finished (the game writes those two frames from
inside its own draw with PP_TITLE_CAPTURE set, because the last beat is held for one second and a screen copy of this
window is not reliable on this host), and no output\PrimordialParadox\pp_crash.log.
