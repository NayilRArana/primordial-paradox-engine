# The drive shot list: twelve shots, 178 seconds, eight locations

Card t_9b2e63d2 (GAME-ROADMAP-1 child R16, step S3), research-assistant, written 2026-10-22 for Primordial Paradox.
Scope: this file only. It does not touch `data/scenes/all.json`, the specs, or any art.

Corrected 2026-10-24 by gamedev, card t_ce63cb65, decision `D18` (`knowledge/GAMEDEV-DECISIONS-2026-10-24.md`):
section 1 and every step count that inherited its 86 step snap are now on the exact 85.714 grid, and section 4.1
records `D19`, that the drive ships as the scene and the room is capture only. The twelve bar counts, the twelve
shots, the twelve caption ids, the four signs and the eight places are unchanged.

What it is for: the coder who writes the drive scene commands reads this table and does not invent a shot. Every
duration below is a number in steps at 60 steps a second, so it can be typed into the scene data without converting.

Decision files this file must agree with, and does unless a `Q:` in section 9 says otherwise:
`knowledge/mechanics/PACING-AND-CUTSCENES.md` sections 4 and 7 and beat sheet beats 7 to 19,
`PLAN-V2-2026-10-21.md` section 2 (concept A, no interior), `specs/14-title-screen-drive.md`,
`specs/06-cutscene-runner.md` (the commands), `ROADMAP-2026-10-22.md` S3 (the shape and the check),
`data/title_timing.json` (the tempo grid), `data/scenes/all.json` (the command set the runner already reads),
`data/flags.json` and `specs/10-route-ledger.md` (flag names), and the route facts: 84.7 miles, signs at 55, 43, 30
and 20 miles remaining.

---

## 1. The grid the film is cut to

The music is the clock, so the shot list is written on the music's grid rather than on round seconds. The chain is
`bpm` -> `steps_per_bar = 3 x 3600 / bpm` -> `cut step = round(bar x steps_per_bar)`, and every number below comes
off that chain rather than being a round number that happens to sit near one. Decision `D18` in
`knowledge/GAMEDEV-DECISIONS-2026-10-24.md` is the ruling, and section 1.1 is why 85.714 is the answer and not 86 or 87.

| what | value | source |
| --- | --- | --- |
| tempo | 126 bpm, 3/4, one bar is 3 beats | `data/title_timing.json` `bpm`, `beats_per_bar` |
| steps a second | 60 | pacing section 1 |
| steps a bar | 85.714 exact (3 x 3600 / 126), and the only lattice a cut is placed on | `data/title_timing.json` `steps_per_bar` |
| the one cue | `title_theme`, the A minor waltz, one cue for the whole film | spec 14 addendum, pacing 4.4 |
| film length | 178 s = 10,680 steps | this card, pacing section 7 |
| interlude | 40 s budgeted, quantised to 28 bars = 2,400 steps = 40.00 s | section 6 below |
| wall time with the interlude | 13,080 steps = 218.00 s | the roadmap says 218 s |

Two consequences, both deliberate:

1. Every hard cut lands on a bar line, because a cut only reads as intended when the music says so (pacing 4.2).
   The eleven hard cuts are at steps 686, 1,543, 2,143, 2,914, 3,943, 5,057, 5,914, 6,771, 7,886, 9,000 and 9,686,
   which are bars 8, 18, 25, 34, 46, 59, 69, 79, 92, 105 and 113 of the cue. Each one is `round(bar x 85.714)`, so
   the worst rounding anywhere in the film is 0.43 steps, which is 0.007 s. The drift is stated once, here: it is
   not accumulating, it resets at every cut because every cut is computed from its own bar number.
2. The interlude is quantised to 28 bars, which is exactly 2,400 steps = 40.00 s, so film bar 69 is wall bar 97 with
   nothing left over. If a player walks the services faster or slower than the budget, the film resumes on the next
   bar line, so the cut into the cutting is still a downbeat.

Fades are 12 steps each, per spec 06 and pacing 4.2. There is no 24 step act fade in this film: see `N1` in
section 9. The opening fade in and the closing fade out are counted inside shot 1 and shot 12, so the twelve
durations still sum to 178.00 s.

### 1.1 The two lattices this is not, with their arithmetic

Both were available in the tree, and both are wrong for a cut. Written down so nobody has to re-derive them:

- **86, the old integer snap.** 86 x 113 bars = 9,718 steps against the exact 9,685.71, so the last hard cut was 32
  steps late, which is 0.54 s and more than one beat (a beat is 28.57 steps): the cut landed on beat two of its bar
  rather than on the downbeat. Every cut before it was late too, by 0.33 percent of its own bar count. 86 is not
  derivable from 126 bpm, and it cannot carry integer beat ticks either, because 86 is not three of anything whole.
  The shipped numbers were this snap until `D18`; they are now the exact grid.
- **87, `data/title_timing.json` `bar_steps`.** That is the title machine's animation clock, and it is 87 on purpose:
  a beat derived bob (29 steps) and a bar derived twinkle (87) then agree with each other, and the 1.5 percent it
  costs against the audio is invisible on a shimmer. On a cut it is 113 steps, 1.88 s, at the end of the film: the
  same twelve bar counts would give 10,793 steps = 179.88 s, moving every duration and the cue. The drive reads
  `title_timing.json` for `bpm`, `steps_per_bar` and `scroll.px_per_step`, and never for `bar_steps`.

---

## 2. The twelve shots: timing

| # | Beat | Location | Bars | Steps | Length s | Running total s | Wall bar of the cut out |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 7 | city: Big Ben, pan down to the street | 8 | 686 | 11.43 | 11.43 | 8 |
| 2 | 8 | city: the London street, the car pulls away, the Thames | 10 | 857 | 14.28 | 25.72 | 18 |
| 3 | 9 | gantry: the first sign, SOUTHAMPTON 55 | 7 | 600 | 10.00 | 35.72 | 25 |
| 4 | 10 | open motorway: rain starts, the wipers seen from outside | 9 | 771 | 12.85 | 48.57 | 34 |
| 5 | 11 (first half) | open motorway: radio pages 1 and 2, car in long shot | 12 | 1,029 | 17.15 | 65.72 | 46 |
| 6 | 11 (second half) | open motorway: radio pages 3 and 4, the sign 43 | 13 | 1,114 | 18.57 | 84.28 | 59 |
| 7 | 13 | Twyford Down: the chalk cutting, the headlight pool | 10 | 857 | 14.28 | 98.57 | 97 |
| 8 | 14 | cathedral: the silhouette far off, one caption | 10 | 857 | 14.28 | 112.85 | 107 |
| 9 | 15 | open motorway: radio pages 5, 6 and 7, the sign 30 | 13 | 1,115 | 18.58 | 131.43 | 120 |
| 10 | 16 and 17 | downland: the storm forms over the car, first lightning, moon | 13 | 1,114 | 18.57 | 150.00 | 133 |
| 11 | 18 | slip road: the Southampton sign 20, headlights | 8 | 686 | 11.43 | 161.43 | 141 |
| 12 | 19 | docks: cranes, containers, the ship lit at the quay | not aligned | 994 | 16.57 | 178.00 | ends on the fade |

Shots 1 to 11 are whole bars and end on a downbeat. Shot 12 is the only one off the grid, because it ends on the
12 step fade to black rather than on a cut, so its end does not have to be a bar line. Beat 11 is split into two
shots (its 36 s is twice the 20 s ceiling) and beats 16 and 17 are merged into one shot (their 24 s is under the
ceiling and they are the same place in the same weather). Twelve beats, twelve shots, one split and one merge.

---

## 3. The twelve shots: what the coder types

The runner implements sixteen commands (`pp_scene_commands()` in `game/scripts/pp_scene/pp_scene.gml`:
`say`, `move`, `face`, `wait`, `fade`, `music`, `sfx`, `camera`, `shake`, `flash`, `spawn`, `destroy`, `battle`, `setflag`,
`branch`, `end`). The column below names only commands from that list. `camera` is 24 steps a move (spec 06), so a
shot with one camera command spends 24 of its steps on movement and the rest on `wait` or on a `say` the player
closes. `flash` costs no steps at all: it floods the frame for two frames over steps the shot already spends.

| # | Commands in order | Cue it plays | Picture |
| --- | --- | --- | --- |
| 1 | `music title_theme`, `fade in 12`, `camera` x3 (72 steps, the pan down the clock face), `wait 602` | `title_theme` starts on the first step | `title_BG_bigben`, one 256x240 background, no scroll |
| 2 | `camera` x2 (48), `sfx car_engine_loop`, `wait 809` | `title_theme`, `car_engine_loop` from here to the end | London street and the Thames: no art in the layer set, see `Q3` |
| 3 | `camera` (24), `say drive_sign_55`, `wait 576` | `title_theme`, engine, text blips | verge, `spr_title_sign` frame 1, `spr_title_cone`; L3 window 0 to 90 |
| 4 | `camera` (24), `wait 747` | `title_theme`, engine, and no rain cue exists yet (`Q2`) | layers L1 to L7, rain overlay and wipers need art (`Q3`) |
| 5 | `say drive_radio_1`, `say drive_radio_2`, `camera` (24), `wait 1005` | `title_theme` ducked under the words, engine, blips | layers L1 to L7, car in long shot; L3 window 0 to 90 |
| 6 | `say drive_radio_3`, `say drive_radio_4`, `say drive_sign_43`, `camera` (24), `wait 1078`, `fade out 12` | `title_theme`, engine, blips | `spr_title_sign` frame 2 passes the car; L3 window 0 to 90 |
| 7 | `fade in 12` (back from the interlude), `camera` (24), `wait 821` | `title_theme` resumes on the bar line, engine | L3 offset 170 to 200: the chalk cutting at L3 x 232 to 300 centred |
| 8 | `camera` (24), `say drive_cathedral`, `wait 833` | `title_theme`, engine, blips | L3 offset 320 to 340: the cathedral nave at L3 x 400 to 452 |
| 9 | `say drive_radio_5`, `say drive_radio_6`, `say drive_radio_7`, `say drive_sign_30`, `camera` (24), `wait 1091` | `title_theme`, engine, blips | `spr_title_sign` frame 3; L3 window 0 to 90 |
| 10 | `camera` (24), `sfx thunder_soft`, `flash 2`, `wait 1090` | `title_theme`, engine, `thunder_soft` and the flash on the same frame | cloud sprite `spr_title_cloud`, then L3 offset 0 to 60 for the downland and the chalk horse at L3 x 148; the 2 frame `flash` is `Q1`, settled |
| 11 | `camera` (24), `say drive_sign_20`, `wait 662` | `title_theme`, engine, blips | `spr_title_sign` frame 4, cone up, the road narrowing to one lane |
| 12 | `camera` x2 (48), `wait 934`, `fade out 12`, then `end` | `title_theme` and engine hold through the fade | docks: no art in the layer set, see `Q3` |

Page budgets for the `say` shots, so a slow reader and a fast reader are both inside the plan, each one the shot's
steps minus its camera moves and its fade: 576 steps for the sign 55 caption, 502 steps a page for the two radio
pages in shot 5 (502.5 exact), 359 steps a page for the three pages in shot 6 (359.33 exact, which is the shot less
its camera move and its 12 step fade out, the fade being spent after the last page closes), 833 steps for the
cathedral caption, 272 steps a page for the four pages in shot 9 (272.75 exact),
662 steps for the sign 20 caption. A page advances on the player's press and never on its own (spec 05), so these
are budgets against the 178 s, measured at the pacing study's 4.5 s page cycle (pacing 3.2); the shot ends on the
next bar line after the last page closes, which is what keeps the cut on a downbeat whatever the reader does.

Camera offsets: a layer's on-screen offset is `round(camera_x * speed) mod 512` and L3 runs at 0.15x
(`tools/art/make_title_world.py`, the `LAYERS` table), so L3 offset 180 is camera x 1,200 px, offset 330 is
camera x 2,200 px and offset 60 is camera x 400 px. The scene card resolves those to the runner's tile
coordinates; this file fixes which part of the world each shot is about.

---

## 4. The eight locations, counted

Eight distinct locations, and the count is eight because the film is a compression of a journey and the density
rule in pacing section 7 is one new kind of place every 22 seconds: eight places in 178 s.

| Location | Shots | How the player knows the place moved |
| --- | --- | --- |
| city | 1, 2 | Big Ben, then the river and the car leaving |
| gantry | 3 | a green sign over the road, SOUTHAMPTON 55 |
| open motorway | 4, 5, 6, 9 | rain and wipers, then the radio pages, then the sign 30 |
| Twyford Down cutting | 7 | chalk walls both sides, one headlight pool |
| cathedral | 8 | the silhouette on the horizon, one caption |
| downland | 10 | open chalk, the moon, the storm keeping pace |
| slip road | 11 | the road narrowing, the sign 20, headlights turning off |
| docks | 12 | cranes, containers, the lit ship |

Two of the eight carry more than one shot (city two, open motorway four) and six carry one each. That is the
reason no location change is left to the caption: every cut between two of these rows changes the place.

### 4.1 Which artifact plays this: the scene, not the room

Decision `D19` in `knowledge/GAMEDEV-DECISIONS-2026-10-24.md`. The drive ships as the `drive_to_southampton` scene
of `data/scenes/all.json`, played by the spec 06 runner on the map `drive_m4_corridor`. The eight places above are
that corridor's camera windows: the scene's camera moves are the place changes, and this table is what the moves are
checked against.

`rm_pp_drive` (`game/scripts/pp_drive/pp_drive.gml`) is **capture only**. It exists so `tools/capture_drive.py` can
write the twelve pictures from inside the game, it is reachable only when `PP_DRIVE_ROOM` is set (unset in every real
launch), and its twelve durations are a copy of section 2 that `tests/test_drive_map.py` now compares to
`data/scenes/all.json` shot for shot, so the copy cannot drift silently. Its pages also advance on their own share
of a shot rather than on the player's press, against spec 05 and the paragraph in section 3: that is a defect in a
capture tool and a spec violation in a shipping screen, which is one of the reasons it is not the shipping screen.

---

## 5. The four gantry signs

The signs are the only counting device in the film, so each one is one beat, one flag and one caption. The four
sign frames are the four drawn in `SIGN_TEXTS` in `tools/art/make_title_world.py` (`spr_title_sign`, 4 frames),
which read SOUTHAMPTON 55, 43, 30 and 20.

| Sign | Miles remaining | Beat | Shot | Flag (`data/flags.json`, spec 10 naming) | Caption id |
| --- | --- | --- | --- | --- | --- |
| frame 1 | 55 | 9 | 3 | `sign_55_seen` | `drive_sign_55` |
| frame 2 | 43 | 11 | 6 | `sign_43_seen` | `drive_sign_43` |
| frame 3 | 30 | 15 | 9 | `sign_30_seen` | `drive_sign_30` |
| frame 4 | 20 | 18 | 11 | `sign_20_seen` | `drive_sign_20` |

From 84.7 miles to 20 miles in three signs and one interlude is the compression the viewer is meant to feel, and
it is measurable: a viewer who counts the signs sees the journey shorten by 35 miles in 150 seconds of film.

---

## 6. The interlude at the services is not a shot

Beat 12 is 40 s of play between shot 6 and shot 7: the player walks one screen, reads a sign and presses on, and
it is the first input in the game (pacing section 9 and its note on why it sits here rather than at the end of
the drive).

| Row | Steps | Length s | What it is |
| --- | --- | --- | --- |
| interlude | 2,400 | 40.00 | 28 bars of the same cue, one screen of walking, no caption except the services sign |

It owns its own map and its own scene, and it is not one of the twelve shots, so it is not in the 178 s. The music
does not change across it, because one cue per scene may only change on a cut or a fade (pacing 4.4) and the
interlude is neither: the theme keeps running under the walk, which is also what makes the 28 bar quantisation
meaningful.

---

## 7. Why there is no shot from inside the car

The car interior is never shown, because Nayil decided on 2026-10-21 that the car shows only its exterior
(PLAN-V2 section 2 item 4, restated as a pacing rule in pacing 4.5), so every line spoken in the car is a bottom of
screen caption over the car in long shot, and no shot in this list has a face in it.

---

## 8. The checks, with the numbers printed

- Shots: 12.
- Durations sum to 10,680 steps, which is 178.00 s. The running total is printed per row in section 2.
- Shortest shot 10.00 s (shot 3), longest 18.58 s (shot 9), median 14.28 s, mean 14.83 s. All twelve are
  between 8 and 20 s, so both this card's rule and the roadmap's looser "no shot under 6 s or over 20 s" pass.
- Locations: 8 distinct, each used at least once, two of them used twice or more.
- Hard cuts: 11, every one within 0.43 steps (0.007 s) of the bar line it names, bars 8, 18, 25, 34, 46, 59, 69,
  79, 92, 105, 113, on the grid of section 1: `round(bar x 85.714)`, steps 686, 1,543, 2,143, 2,914, 3,943, 5,057,
  5,914, 6,771, 7,886, 9,000, 9,686.
- Fades: 12 steps each, four of them (in on shot 1, out on shot 6 into the interlude, in on shot 7, out on shot 12).
- Gantry signs: 4, at 55, 43, 30 and 20 miles remaining, on beats 9, 11, 15 and 18.
- Every shot names at least one command from `pp_scene_commands()`.
- Interior shots: 0. Faces: 0.
- Arithmetic anyone can re-run: 178 x 60 = 10,680; 10,680 + 2,400 = 13,080 steps = 218.00 s. The seconds column is
  rounded to two decimals for reading and adds to 177.99; the exact figure is the 10,680 steps, which is 178.00 s.

This card proves the numbers, not the film. Nothing here has been run in the engine: the proving step is the
scene data card (R21) plus the timing test on the testing lane, which fail if a shot's steps do not match this
table or if a cut does not fall on a bar.

---

## 9. Q: for gamedev, and two notes

These are conflicts between the card, the specs and the code as they stand today. Per the gamedev specs rule I
am not deciding them, and none of them changes a duration in section 2. `Q1` is the exception: it was ruled by card
t_531bc76c on 2026-10-24 and is recorded settled below; `Q2` and `Q3` still stand.

- `Q1` **Settled 2026-10-24 (card t_531bc76c): `flash` is a runner command, and shot 10 uses it.** The card named
  `flash`; spec 06's table and `pp_scene_commands()` did not have it, and the only whole-screen palette flash in the
  build was the title's own storm clock in `pp_title.gml` (2 frames from `data/title_flash.json`). `D19` rules that the
  drive ships as a scene, so the "play it inside the title machine that already owns the flash" branch is closed; the
  runner grew the command instead. The shape: `flash` takes an optional `steps` (default `PP_FLASH_STEPS`, 2, the
  title's own clock, 8 at most) and an optional `role` (default `paper`, which every set in `data/room_palettes.json`
  declares). It floods the whole 256x240 frame in that role for those frames, so it is a palette change and never a
  blend (spec 13), it is drawn under the fade and over everything else, and the world counts the frames down on its own
  clock. **It costs the scene no steps**, which is why the film is still 10,680: a flash priced as a wait would have
  moved shot 10's 1,114, the eleven cuts after it and the cue's grid with them. In the scene, `flash` sits directly
  after `sfx thunder_soft`, and both commands advance in the same step, so the sound and the light land on the same
  frame. The checker refuses a role the scene's own room set does not declare.
- `Q2` Spec 14 calls the waltz `title_theme` and also cue PP-01, while `data/audio.json` registers PP-01 as
  "Wessex Lane, Move-In Day" and its `sounds` list has neither `title_theme`, `car_engine_loop` nor
  `thunder_soft` (nor any rain cue). This file uses the three ids spec 14 names. The musician lane owns
  registering them and settling which PP number the drive is.
- `Q3` Three of the twelve pictures do not exist in the title layer set (`data/title.json`: `title_BG_bigben`
  plus L1 to L7, `spr_title_sign`, `spr_title_cone`, `spr_title_car`, `spr_title_cloud`): the London street with
  the Thames (shot 2), the rain and wipers (shot 4), and the night docks (shot 12). The nearest existing picture
  is the dusk battle background `quay_dusk` in `tools/art/make_battle_bg.py`, which is dusk, not night. Art owns
  the answer: a new background, a reuse decision, or a re-cut of the shot.
- `N1` Not a conflict, a record: the roadmap's S3 check mentions a 24 step chapter card fade. The chapter card is
  beat 32, after the docks and outside this film (pacing 4.2 calls it the only act boundary in the opening), so
  every fade in the drive is 12 steps. If gamedev wants a 24 step fade inside S3 that is a new decision, not a
  correction to this list.
- `N2` Not a conflict, a record: spec 14's 2026-10-21 addendum still lists the sign frames as 31, 22, 13 and 4
  miles. The drawn signs, and this card's route facts, read 55, 43, 30 and 20, so the addendum's line is stale.

---

## 10. What this file does not do

It does not write the scene, the dialogue pages, the four flags, the maps or the art. It does not add the bedroom
marks or the intro's chapter card. The scene data card (R21) owns `data/scenes/all.json` and adds the four flags
to `data/flags.json`; the twelve caption ids named here (`drive_radio_1` to `drive_radio_7`, `drive_cathedral`,
`drive_sign_55`, `drive_sign_43`, `drive_sign_30`, `drive_sign_20`) have to be authored before the checker will
pass, because spec 06 rule 4 proves every dialogue id exists.
