# Demo script: three minutes, six shots, one claim per shot

Card t_c0f33e5d (GAME-ROADMAP-2 child R39), research-assistant, written 2026-10-22 for Primordial Paradox.
Scope: this file only. It does not write route data, the recorder or the edit. `knowledge/VIDEO-PLAN.md` (R44) is
built from this file, and `data/demo/run_001.json` is the input script R44 extends.

What it is for: a person opens this file in the recording booth, presses the keys in the order they appear, and
makes no decision. Every shot names what is on screen, what the player inputs, what the music does, what the caption
says, and which claim of the write-up that shot is evidence for.

Authority, in the order it was read:
1. `ROADMAP-2026-10-23.md` section 0 is the route this demo must show; section 3 names this file R39's.
2. `..\arananet\meta-hackathon\PLAN-WIN-2026-10-22.md` section 1 and `..\arananet\meta-hackathon\kit\ONE-PAGER.md`
   are the claims the shots are evidence for. Quoted phrases below are verbatim from those two files.
3. `knowledge/mechanics/PACING-AND-CUTSCENES.md` section 9 (the beat sheet, 900 seconds) is the order and the budget
   of the beats.
4. `knowledge/DRIVE-SHOT-LIST.md` is the drive: this script takes its shot 3 and no other.
5. `knowledge/ARRIVAL-CONTENT.md` is the gate, the office, the boarding pass and the map's provenance.
6. `specs/19-llm-talk.md` is the bake and the receipt fields; `specs/05`, `07`, `11`, `14` are the inputs and the
   screens this script presses keys into.

---

## 1. The six shots at a glance

| Shot | Clock | Seconds | Steps | Route step (ROADMAP section 0) | The claim it proves | What is drawn over the frame |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | 0:00.00 to 0:16.00 | 16.00 | 960 | title attract, PRESS START, NEW GAME | "whether it works", and "AI that obeys hardware limits" | one caption |
| S2 | 0:16.00 to 0:29.00 | 13.00 | 780 | the crawl | "Kronos and Zeus reincarnated on the M3" | one caption |
| S3 | 0:29.00 to 0:39.03 | 10.03 | 602 | the drive, one shot, with a gantry sign | "an NES-faithful night drive" | one caption |
| S4 | 0:39.03 to 1:19.03 | 40.00 | 2,400 | arrival at Town Quay, the gate checkpoint and its three option choice | the block is a real street; the gate cannot be failed | one caption |
| S5 | 1:19.03 to 1:53.03 | 34.00 | 2,040 | the walk to the dock office, the boarding pass, the boarding | "the person judging your line is a Meta model answering inside a NES text box" (Meta shot 1) | caption plus the bake row |
| S6 | 1:53.03 to 3:00.00 | 66.97 | 4,018 | the first fight, the TALK fight, the ship's log save, the game over | "One is won with a single command. The other is won by talking", and the bake on a dead network (Meta shot 2, the offline shot) | caption plus three bake rows plus the network line |

Total: 180.00 s, 10,800 steps.

---

## 2. The clock, and why the total is 180.00

- The unit is the step, 60 to a second, the game's own step event (spec 05, spec 07). 180.00 s is 10,800 steps, and
  every row below carries its absolute step so the booth sheet in section 7 can be typed without arithmetic.
- 180 is the middle of the card's 170 to 190 band, so both fallbacks in the last paragraph stay inside it.
- Five of the six shots are round numbers of seconds. S3 is 602 steps (10.03 s) because that is the drive list's own
  number for its shot 3 (7 bars of 86, `knowledge/DRIVE-SHOT-LIST.md` section 2). Nothing else inherits an odd
  length, so S6 absorbs the 0.03 and ends at 66.97 s, not 67.
- The demo's own cuts are on seconds, not on the waltz's bar. The bar is the drive's rule (DRIVE-SHOT-LIST section 1)
  and it stays the drive's rule; this script does not add a second place where a bar length is decided, because
  `data/title_timing.json` and the drive list currently disagree about that length (Q4).
- Fallbacks, all designed, all inside the band:
  1. If R21 (the drive scene) has not landed, S3 is the intro's own night drive, which is 240 steps (4.00 s) today
     (`data/demo/run_001.json`, event e08). The total becomes 173.97 s.
  2. If R27 GAME-OVER has landed no forced defeat trigger, cut S6.4 (9.00 s). The total becomes 171.00 s.
  3. If both are missing at once, hold the crawl (beat sheet beats 4 to 6, 25 s) and the yard walk (beat 21, 28 s) at
     their sheet lengths instead of the trimmed ones below. The total returns to about 174 s with no new shot.

---

## 3. S1 to S6, second by second

### S1, the title, 0:00.00 to 0:16.00 (960 steps)

Screen: the attract loop of `rm_pp_title`, seven night layers, the car, the storm cloud, the logo.
Input: none until 0:11.80, then Enter twice.
Music: `title_theme`, the A minor waltz at 126 bpm in 3/4, one pass is 52 bars. It starts on step 0 and runs under
the whole shot. The menu press adds the two interface sounds (`menu_move`, then `menu_select`).
Caption, verbatim: `Cold boot to menu in 14 seconds. CONTINUE is dim because there is no save yet.`
Claim: "Whether it works is the floor" (PLAN-WIN section 1), proved by roadmap checks 1 and 2, a cold start with no
console window and a menu that opens; and "AI that obeys hardware limits", proved by the frame itself, one 256 by
240 screen, at most 16 colours from `data/palette.json`, a 2 frame palette swap instead of a filter (spec 13,
`data/title_flash.json`).

| t | step | On screen | Input | Music and sound |
| --- | --- | --- | --- | --- |
| 0:00.00 | 0 | attract: sky, moon, the two star layers, the storm cloud over the car, the logo; road dashes one per beat, car bob 1 pixel per beat | none | `title_theme` starts |
| 0:05.80 | 348 | the logo's gold shimmer pass (every 4 bars, 24 step pass) | none | `title_theme` |
| 0:11.60 | 696 | the lightning: the whole screen swaps to the flash palette for 2 frames, then back | none | `title_theme` |
| 0:11.80 | 708 | the logo, its line PRESS Z OR ENTER blinking one blink every 29 steps | Enter (the title's own confirm, `data/demo/run_001.json` event e02 uses the same key) | `menu_select` |
| 0:12.10 | 726 | the menu: NEW GAME, CONTINUE, SETTINGS, QUIT; the cursor sits on NEW GAME; CONTINUE is drawn in the second ink because `pp_save_01.json` does not exist | none | `menu_move` |
| 0:14.20 | 852 | NEW GAME chosen | Enter | `menu_select` |
| 0:14.40 | 864 | 12 step fade, then the star field of the crawl machine, 24 stars from `data/intro_stars.json`, twinkling on the bar | none | `title_theme` continues |

### S2, the crawl, 0:16.00 to 0:29.00 (780 steps)

Screen: the crawl, 6 beats and 14 rows, from `data/intro_text.json`, drawn over the star field.
Input: confirm held from 0:22.00 to 0:27.00, then released; no other key.
Music: the same cue, `title_theme`, ducked under the words (spec 14 addendum), with the text blip every 3 characters
(`data/title_timing.json` `text.blip_every_chars`).
Caption, verbatim: `The crawl is 1,238 steps on the engine. A held confirm reads it faster and never skips a page.`
Claim: "Kronos and Zeus reincarnated on the M3" (PLAN-WIN section 1), which is beats 2 and 3 of the crawl in the
game's own words; and the skip rule, that a held confirm speeds the reveal and a double tap cannot skip the story
(spec 14 addendum, recipe PAC-05).

| t | step | On screen | Input | Music and sound |
| --- | --- | --- | --- | --- |
| 0:16.00 | 960 | beat 1, one row: THE GODS NEVER DIED. | none | `title_theme` ducked; blip every 3 characters |
| 0:17.20 | 1,032 | beat 2, four rows: THEY WERE FORGOTTEN, ... WEARS THIN. | none | as above |
| 0:22.00 | 1,320 | beats 3 and 4 arrive (the four who do not know; tonight a father drives his son south) | confirm held, 3x reveal, no page skipped (spec 05 rule 3) | as above |
| 0:27.00 | 1,620 | release; beat 6 types at 1x: SOUTHAMPTON. OCTOBER. | released | as above, back to 1x |
| 0:28.00 | 1,680 | the last beat whole, then its 60 step hold | none | as above |
| 0:28.80 | 1,728 | 12 step fade out | none | `title_theme` carries the fade |

### S3, the drive, one shot, 0:29.00 to 0:39.03 (602 steps)

Screen: shot 3 of the twelve in `knowledge/DRIVE-SHOT-LIST.md`, the verge, the gantry sign frame 1 reading
SOUTHAMPTON 55, the cone, the 512 pixel layers at their fixed scroll speeds.
Input: confirm once at 0:35.00, which closes the one caption.
Music: `title_theme` plus `car_engine_loop` from the fade in, plus text blips while the caption types, which is the
cue column of shot 3 in the drive list.
Caption, verbatim: `One of the twelve drive shots: the sign counts down, and the cut lands on a bar of the waltz.`
Claim: "an NES-faithful night drive" (PLAN-WIN section 1), proved by one of the twelve shots at its own length, a
road sign as the film's only counting device, seven parallax layers at the speeds the title contract fixes
(`TITLE-COORD.md`), and a hard cut on the music's bar line.

| t | step | On screen | Input | Music and sound |
| --- | --- | --- | --- | --- |
| 0:29.00 | 1,740 | 12 step fade in; camera moves 24 steps; the gantry and the sign frame 1 come up | none | `title_theme`, `car_engine_loop` |
| 0:29.40 | 1,764 | the caption `drive_sign_55` opens and types at 2 steps a character; the sign's own face reads SOUTHAMPTON 55 | none | blips, engine |
| 0:35.00 | 2,100 | the caption closes; the verge holds, the camera drifts, the engine keeps time | confirm | engine, theme |
| 0:39.03 | 2,342 | hard cut on the bar, out of the drive and into the quay | none | cut |

The caption's wording belongs to whoever authors `drive_sign_55`; the drive list names the id and says in section 10
that it does not exist yet. This script needs only that the caption exists and names the sign's own number.

### S4, arrival, the gate checkpoint and the three option choice, 0:39.03 to 1:19.03 (2,400 steps)

Screen: the Town Quay block, the barrier arm on Town Quay at row 9, the hut with one lit window, Morgan at (8,9),
then the yard walk past Canute's Palace and the Watergate Ruin.
Input: confirm repeatedly, one Down press at 0:54.23 to move the choice cursor from `No pass.` to `Crew list.`, one
confirm to take it, then walking keys.
Music: the quay map's own cue from `data/maps/all.json` `music`, which this script expects to be PP-03 Harbor and
does not decide; it does not change inside the shot, because a cue changes only on a cut or a fade (pacing 4.4).
Caption, verbatim: `The gate cannot be failed. Three replies, three flags, and every one of them lifts the barrier.`
Claim: the block is a real street, 8 door names and 4 people read out of the project's own OpenStreetMap extract
(ARRIVAL-CONTENT sections 3 and 4), and the checkpoint is a choice with no failure state, three labels, three flags,
one barrier (ARRIVAL-CONTENT section 6).

| t | step | On screen | Input | Music and sound |
| --- | --- | --- | --- | --- |
| 0:39.03 | 2,342 | the quay: road tiles, the barrier, the hut, the lamp, one grey hull past the yard | none | the map's cue |
| 0:42.03 | 2,522 | `quay_gate_checkpoint` page 1: rain on the barrier arm, a hut, one lit window, the man stands up | confirm held 60 steps, 3x | blips |
| 0:44.03 | 2,642 | page 2, Morgan: That is far enough. Name and business. He holds a clipboard | confirm to close | blips |
| 0:48.03 | 2,882 | page 3: past him the yard is dark, past that a grey hull, one lamp on the water | confirm held 60 steps, then close | blips |
| 0:50.03 | 3,002 | page 4, Morgan: No pass, no gate. So. What is it? He waits, pen ready | confirm to close | blips |
| 0:54.03 | 3,242 | the choice panel, 96 pixels wide, three labels: No pass. Crew list. Ask him. | Down once at 0:54.23, cursor on Crew list. | `menu_move` |
| 0:57.03 | 3,422 | Crew list. taken | confirm | `menu_select` |
| 0:57.20 | 3,432 | `quay_gate_bluff` page 1: The list is full. Office, then. Sign. He does not look down | confirm to close | blips |
| 1:02.23 | 3,734 | page 2, narrator: He does not look down | confirm to close | blips |
| 1:04.23 | 3,854 | the barrier lifts itself; `gate_passed` and `gate_bluff` are set; the yard is walkable | none | the map's cue continues |
| 1:08.23 | 4,094 | the yard walk: Canute's Palace, the Watergate Ruin, St Julians Chapel to the east, the office frontage south west | walking keys, held | footsteps |
| 1:19.03 | 4,742 | hard cut at the office door | none | cut |

The three labels and the branch pages are already in `data/dialogue/all.json` as `quay_gate_truth`,
`quay_gate_bluff` and `quay_gate_authority`; the four page scene `quay_gate_checkpoint` with its `choices` block is
not in that file yet and is R22 DIALOGUE-V2's to land (data route table, section 6).

### S5, the office, the boarding pass and the boarding, 1:19.03 to 1:53.03 (2,040 steps)

Screen: `quay_dock_office`, a counter, a lamp, a ledger, Nye and the Navy sailor; then the quay south, the gangway,
and the deck of `ship_small`.
Input: confirm on the door, six page presses or holds, confirm on the log note, then walking keys.
Music: the office map's cue, then on the boarding fade the cue changes to `PP-05` Small Ship, which is the `music`
line of the `ship_boarding` scene in `data/scenes/all.json`, with `ship_ambient` under it (`data/audio.json`).
A cue change on a fade is legal (pacing 4.4); a change inside the office would not be.
Caption, verbatim: `The pass is one page and one flag. The clerk's line is a bake row, and here is the row.`
Claim: "the person judging your line is a Meta model answering inside a NES text box" (ONE-PAGER), proved on this
shot by Nye's page and its `data/meta_bake.json` row on screen, in a box whose four lines are 28 columns plus the
2 character narration marker, exactly spec 05's 30 (spec 19 section 5); and the boarding pass, which is one flag and
one page, not an inventory item (ARRIVAL-CONTENT section 4.2).

| t | step | On screen | Input | Music and sound |
| --- | --- | --- | --- | --- |
| 1:19.03 | 4,742 | the office door at (18,25); `map` trigger opens `quay_dock_office`, spawn `from_quay` | confirm on the door | door, then the office cue |
| 1:21.03 | 4,862 | page 1: a counter, a lamp, a ledger, two men, one is Navy | confirm held 60 steps, then close | blips |
| 1:23.03 | 4,982 | page 2, Nye: You are the last one. Name, then. Slowly. The pen is already wet | confirm to close at 1:27.53 | blips; the bake row overlay runs 1:23.4 to 1:27.4 |
| 1:27.53 | 5,252 | page 3: one line left in the ledger, the ink on it is dry, it is not the clerk's hand | confirm held 60 steps, then close | blips |
| 1:29.53 | 5,372 | page 4, Nye: Berth nine. Deck two. Do not leave the cabin | confirm held, then close | blips |
| 1:31.53 | 5,492 | page 5, the sailor: Sign it and come on. I have a ladder to hold | confirm held, then close | blips |
| 1:33.53 | 5,612 | page 6: the slip changes hands, it is warm from a pocket, behind them the gate shut; `has_boarding_pass` set | confirm to close at 1:36.53 | blips |
| 1:36.53 | 5,792 | back on the quay, south past the Red Jet ticket office toward the pier | walking keys | the office cue, footsteps |
| 1:42.53 | 6,152 | the gangway; the `ship_boarding` scene opens on `ship_small` | none | cue changes to PP-05 on the fade |
| 1:47.03 | 6,422 | `ship_gangway`: the horn shakes the deck, salt, rope and wet paint, a wardroom hatch shut; then the hero walks three tiles up, `ship_deck_seen` is set | confirm to close, then walking keys | PP-05, `ship_ambient` |
| 1:53.03 | 6,782 | the deck, the hatch, the door east | none | PP-05 |

### S6, the two fights, the save and the game over, 1:53.03 to 3:00.00 (4,018 steps)

Sub-shots, because the fallbacks in section 2 name them: S6.1 the hound, 1:53.03 to 2:10.03 (1,020 steps); S6.2 the
TALK fight, 2:10.03 to 2:40.03 (1,800 steps); S6.3 the ship's log save, 2:40.03 to 2:51.00 (658 steps); S6.4 the game
over and CONTINUE, 2:51.00 to 3:00.00 (540 steps).

Screen: the deck, the encounter flash, the battle frame, the five entry menu, the box, the HUD, then the cabin, the
ship's log, the Saving panel, the defeat, the game over screen, the title menu with CONTINUE lit, the loaded room.
Input: FIGHT once, TALK three times through three context options, SPARE once, confirm through the save, then the
defeat trigger R27 owns, then CONTINUE.
Music: `PP-04` Navy Sailors for both encounters (the `music` field of both encounter rows in
`data/encounters/all.json`), `PP-05` back on the deck and in the cabin, the save chime once (spec 11 acceptance 5),
and `game_over` once at the defeat (`assets/audio/sfx/game_over.ogg`, 1.4 s, ear gate row 7), after which the music
stops until the load restores the save's own `music` key (spec 11 keys).
Caption, verbatim: `FIGHT once ends the hound. Three TALK options reach MERCY 60 and SPARE. Then a save, and a defeat.`
Claim: "One is won with a single command. The other is won by talking" (ONE-PAGER), proved by two fights in one
take, the hound's 2 hp against a FIGHT that cannot roll under 2 (spec 07 damage 2 to 12, `data/enemies/all.json`),
and the sailor's `mercy_per_option` 20 against `mercy_to_spare` 60, which three context options reach exactly
`specs/19-llm-talk.md` section 11; and the save, proved by CONTINUE changing from the second ink in S1 to the first
ink here, and by the loaded room.

| t | step | On screen | Input | Music and sound |
| --- | --- | --- | --- | --- |
| 1:53.03 | 6,782 | the hound by the rope: Something moves by the rope, a hound on the deck, it is thin, FIGHT ends this in one blow | confirm to close the intro | PP-04 |
| 1:57.03 | 7,022 | the battle frame, the menu, cursor on FIGHT | confirm, the timed bar sweeps 0 to 100 in 60 steps | `hit` |
| 1:57.53 | 7,052 | the bar stops at about 66; damage is at least 2 against 2 hp, so this turn ends the fight | confirm at step 40 of the sweep | `hit`, then the victory beat |
| 1:58.03 | 7,082 | `hound_win_kill`: One blow. The hound is still. You step over the rope | confirm to close | PP-04 |
| 2:01.03 | 7,262 | 30 step victory beat, back to the deck, `PP-05`, then the walk to the deck watch trigger at (4,7) | walking keys | PP-05 |
| 2:10.03 | 7,802 | the deck watch trigger at (4,7); `battle_intro_sailors`: a Navy Sailor squares up, TALK can calm this, FIGHT can end it faster | confirm to close | PP-04 |
| 2:13.03 | 7,982 | the menu, cursor on FIGHT; move to TALK and open it | Down, then confirm | `menu_move`, `menu_select` |
| 2:14.03 | 8,042 | the TALK panel: three context options, in the encounter's own order | confirm on option 1 | blips |
| 2:15.03 | 8,102 | turn 1 reply (a bake row); MERCY 0 to 20 | confirm to close | blips |
| 2:17.03 | 8,222 | enemy turn 1, then the menu | none | `hit` or the pattern's own cue |
| 2:18.53 | 8,312 | option 2; turn 2 reply (a second bake row); MERCY 20 to 40 | confirm twice | blips |
| 2:22.03 | 8,522 | enemy turn 2, then the menu | none | as above |
| 2:23.53 | 8,612 | option 3; turn 3 reply (a third bake row); MERCY 40 to 60, so SPARE turns to the first ink and the ready beat plays once | confirm twice | the ready spark, then blips |
| 2:28.03 | 8,882 | SPARE taken, the peaceful end; `navy_win_spare` opens | confirm | PP-04, then PP-05 |
| 2:31.53 | 9,092 | `navy_win_spare` text: He steps aside. His eyes stay on the sea. Bridge is that way. | confirm to close | PP-04, then PP-05 |
| 2:34.40 | 9,264 | the win text still typing; the dead network overlay runs 2:34.40 to 2:38.40 (section 5) | none | PP-05 |
| 2:38.43 | 9,506 | back on the deck; `ship_door_open` set, which is what opens the cabin door at (18,7) | walking keys | PP-05 |
| 2:40.03 | 9,602 | S6.3 begins: the hatch and the cabin door | walking keys, then confirm | door |
| 2:42.53 | 9,752 | `ship_cabin`; the ship's log | confirm | PP-05 |
| 2:44.53 | 9,872 | the log's page, then the Saving panel: the chime once, `pp_save_01.json` written, the panel stays at least 20 steps (spec 11 numbers) | confirm, then confirm | chime |
| 2:48.03 | 10,082 | the cabin, the log, the save line | none | PP-05 |
| 2:51.00 | 10,260 | S6.4 begins: the forced defeat, the trigger R27 GAME-OVER exposes, 30 step defeat band (spec 07 turn flow) | the defeat key or the defeat hook R27 lands | `game_over` |
| 2:51.50 | 10,290 | `battle_lose`: The deck rises to meet you. Your last save still stands | confirm to close | silence |
| 2:53.50 | 10,410 | the game over screen | none | `game_over` plays once, 1.4 s, then silence |
| 2:55.50 | 10,530 | the title menu: CONTINUE is now in the first ink, with the plain line that says where the player is (spec 11 goal) | confirm on CONTINUE | `menu_select` |
| 2:57.00 | 10,620 | the load: the fade, then the cabin at the save point, which is where spec 11 rule 5 always lands | none | the save's own `music` key resumes |
| 3:00.00 | 10,800 | last frame: the cabin, the log, PP-05 | none | end |

---

## 4. The two Meta shots, and the field the frame prints

The bake is the architecture, not a nicety: the shipped build holds no key and makes no call (D5,
`specs/19-llm-talk.md` section 2). So the evidence that a model was in the loop is the row, and the two shots below
are the two places the recording shows it.

| Shot | The line on screen | The row behind it | The field the overlay prints | Why that field |
| --- | --- | --- | --- | --- |
| S5, Meta shot 1, 1:23.4 to 1:27.4 | Nye, page 2: You are the last one. Name, then. Slowly. | the `npc` chat row for Nye at `southampton_dock`, turn 1 (spec 19 section 2, Q10: Morgan first, Nye after) | `model` and `request_hash`, read out of `data/meta_bake.json` | `model` names the model that answered, `request_hash` names the exact assembled request, so the printed pair cannot be a hand typed line |
| S6, Meta shot 2, 2:15.03, 2:18.53, 2:23.53 | the three TALK replies, one per turn | the three `fight` rows for the deck watch at turn 1, 2 and 3 | `model` on the first reply, then `request_hash` alone on replies 2 and 3 | three different `request_hash` values prove three calls at three different scene states, not one line reused three times |

Rules for the two overlays, so R44 can build them without asking:
1. The text is read from the file at edit time, never typed. A row that is missing means the shot is not recordable
   and the booth stops, which is better than a receipt that lies.
2. The overlay is drawn as a caption under the frame or beside it, never inside the 256 by 240 area. The frame stays
   the game's own pixels (R44 carries the same rule for the ffmpeg chain).
3. `created_at` and the shadowed fallback are in the row by D5, and neither is printed on screen: the card asks for
   the field that proves a model answered, and two fields carry that. If a third line is wanted later, `created_at`
   is the one to add.

---

## 5. The one shot with a dead network

S6 is recorded with the machine's network dead: the adapter is disabled before the first frame at 00:00.00, and the
overlay from 2:34.4 to 2:38.4 says so while the win text is still typing.

| What the frame shows | What backs it |
| --- | --- |
| the reply `He steps aside. His eyes stay on the sea. Bridge is that way.` playing on a machine with no network | the text is a dialogue line in `data/dialogue/all.json`, not a call (spec 19 section 8 rung 1) |
| a line saying the adapter has been off since the first frame, and that the reply above came from `data/meta_bake.json` | the bake file's own row, printed by the same read as the section 4 overlays |
| the run continuing through the save and the game over with the network still dead | `tests/test_no_network_in_build.py` (R34), which asserts that nothing under `game/` carries a URL, an `http` or a key name |

What this shot does not claim: it does not claim the card pool rung (spec 19 section 8 rung 2), which answers a line
the bake does not cover. That rung is exercised by `tests/test_first_fight.py` and no demo line reaches it. Saying so
is part of the claim being honest.

---

## 6. The route, step by step, and where each step lives

Every step of `ROADMAP-2026-10-23.md` section 0 appears exactly once, in this order.

| Route step (section 0) | Shot | In data today | The card that lands it |
| --- | --- | --- | --- |
| title attract, PRESS START, NEW GAME | S1 | `rm_pp_title`, `data/title.json`, `data/title_flash.json`, `data/title_timing.json` | R25 TITLE-PATH (t_136b5d08) for the NEW GAME and CONTINUE path |
| the crawl | S2 | `data/intro_text.json`, 6 beats and 14 rows; the reveal machine measured at 1,238 steps (spec 14 addendum) | R25 |
| the drive | S3 | the drive block of `data/scenes/all.json`, not written yet; `knowledge/DRIVE-SHOT-LIST.md` shot 3 | R21, which roadmap section 3 creates after the two map cards release `data/scenes/all.json` |
| arrival at Town Quay | S4 | no quay map yet; `data/maps/osm/southampton_town_quay.json` is the terrain draft | ARRIVAL-MAP-2 (t_db2995d7), R28 EXTERIOR-TILESET (t_7d1380f9) |
| the gate checkpoint and the three option choice | S4 | `quay_gate_truth`, `quay_gate_bluff`, `quay_gate_authority` are in `data/dialogue/all.json`; `quay_gate_checkpoint` with its `choices` block is not | R22 DIALOGUE-V2 (t_5b27880e) for the scene, ARRIVAL-MAP-2 for the trigger at (8,9) |
| the walk to the dock office and the boarding pass | S5 | `quay_dock_office` is in ARRIVAL-CONTENT section 5, not in `data/dialogue/all.json`; `has_boarding_pass` is in no `data/flags.json` today | R22 for the pages, ARRIVAL-MAP-2 for the door trigger and the flags |
| boarding the ship | S5 | scene `ship_boarding` and map `ship_small` are in the data now, with `music PP-05` | nothing; it exists |
| the first fight, won with one FIGHT | S6.1 | encounter `deck_hound`, seed 20261022, beat 23, 2 hp; `battle_intro_hound`, `hound_win_kill` | nothing for the fight; R30 TALK-BAKED (t_8cd9c10a) for its talk side |
| the TALK fight through three options | S6.2 | encounter `tutorial_sailors`, seed 20261019, beat 28, `option_count` 3, `mercy_per_option` 20, `mercy_to_spare` 60; dialogue `talk_navy_sailor`; `ship_door_open` on kill or spare | R30 |
| the ship's log save | S6.3 | `data/maps/all.json` carries a `save` trigger `deck_save` on the deck at (2,5); the cabin log is beat 27 | R26 SAVE-SLICE (t_7099c5fe) |
| a game over that continues from a save | S6.4 | `battle_lose` is in `data/dialogue/all.json`; spec 07 acceptance 4 sends a defeat back to the title with the save intact | R27 GAME-OVER (t_24eab5ff) |

No step outside that list appears in this script. Percy, the Prometheus interruption, the cabin scenes, London, the
dungeon and the NES ROM are all outside the route and outside the demo (roadmap section 0, "Not in it"), so no shot
names one.

---

## 7. The booth sheet

Keys in the order they are pressed, in the vocabulary `data/demo/run_001.json` already uses (`enter`, `confirm`,
`right`, `up`, `down`), with the absolute step each one lands on. A held key is written as `confirm hold` with the
step it is released at. This is the list R44 turns into the recorder's events; nothing here is decided at the desk.

| Step | Key | Where the run is | Why |
| --- | --- | --- | --- |
| 0 | none | attract | the recording starts, no key until the flash has played |
| 708 | enter | title, PRESS Z OR ENTER | opens the menu |
| 852 | enter | menu, cursor on NEW GAME | NEW GAME |
| 1,320 | confirm hold to 1,620 | crawl, beat 2 ends | 3x reveal through beats 3 and 4 |
| 1,620 | release | crawl, beat 5 typing | the last beat reads at 1x |
| 2,100 | confirm | drive, caption open | closes `drive_sign_55` |
| 2,522 | confirm hold to 2,582, then confirm at 2,642 | gate, page 1 | fast read, then advance |
| 2,882 | confirm hold to 2,942, then confirm at 3,002 | gate, page 3 | fast read, then advance |
| 3,242 | confirm | gate, page 4 closed | the choice panel opens |
| 3,254 | down | choice panel | the cursor moves from No pass. to Crew list. |
| 3,422 | confirm | choice panel | takes Crew list. |
| 3,734 | confirm | `quay_gate_bluff` page 1 | advance |
| 3,854 | confirm | `quay_gate_bluff` page 2 | advance, the barrier lifts |
| 4,100 to 4,660 | up and right, held in turns | the yard | walks the block to the office frontage |
| 4,742 | confirm | the office door | enters `quay_dock_office` |
| 4,862 | confirm hold to 4,922, then confirm at 4,982 | office, page 1 | fast read, then advance |
| 5,252 | confirm hold to 5,312, then confirm at 5,372 | office, page 3 | fast read, then advance |
| 5,492 | confirm | office, page 4 | advance |
| 5,612 | confirm | office, page 5 | advance |
| 5,792 | confirm | office, page 6 | advance, `has_boarding_pass` set |
| 5,800 to 6,140 | right and down, held in turns | the quay south, the gangway | reaches the boarding trigger |
| 6,422 | confirm | `ship_gangway` | advance |
| 6,440 | up three presses | the deck | the scene's three tile move |
| 7,022 | confirm | hound fight, menu | FIGHT, the bar starts |
| 7,052 | confirm | the bar at about 66 | stops the bar, the blow lands |
| 7,262 | confirm | `hound_win_kill` | advance |
| 7,802 | confirm | `battle_intro_sailors` | advance |
| 7,970 | down | the battle menu | cursor moves to TALK |
| 7,982 | confirm | TALK | the option panel opens |
| 8,042 | confirm | option 1 | turn 1 |
| 8,102 | confirm | reply 1 | advance |
| 8,312 | confirm, then confirm | option 2 and its reply | turn 2 |
| 8,612 | confirm, then confirm | option 3 and its reply | turn 3, MERCY reaches 60 |
| 8,882 | confirm | SPARE | the peaceful end |
| 9,092 | confirm | `navy_win_spare` | advance |
| 9,506 | up and right | the deck to the hatch and the cabin door | `ship_door_open` is set by the fight |
| 9,602 | confirm | the cabin door | enters `ship_cabin` |
| 9,752 | confirm | the ship's log | the page opens |
| 9,872 | confirm | the Saving panel | the save writes, the chime once |
| 10,260 | the defeat input R27 lands | the cabin | the forced defeat |
| 10,290 | confirm | `battle_lose` | advance |
| 10,530 | confirm | the game over screen, then the title menu | CONTINUE, which is now lit |
| 10,620 | none | the load | the last frame |

---

## 8. What this script leaves out, on purpose

- Eleven of the twelve drive shots. Three minutes cannot hold 178 seconds of film and eight other route steps; the
  drive list keeps its own full length and this demo takes one shot that carries the sign.
- Percy, the Prometheus interruption, the cabin scenes, London, the dungeon, the NES ROM (roadmap section 0).
- The free typed TALK line. The demo takes the three context options because they are deterministic, cost nothing and
  reach the spare threshold exactly (spec 19 section 11). The typed line is the feature a player meets on their own
  laptop, and the recording says so in the caption rather than in a shot.
- The card pool and the encounter fallback. They are real (spec 19 section 8 rungs 2 and 3) and no demo line reaches
  them, so no shot claims them.
- Any number the build cannot print. The two receipts are read from the file at edit time; the game over carries no
  statistic; the save shows no counter.

---

## 9. Q: for gamedev, four items, and three notes

Per the gamedev specs rule, none of these is decided here. Q2 is the only one that would move a shot, and it says how;
the other three change no second of the 180.00 total.

1. **Q1, the route file.** The card's check says "a re-read against `data/slice.json` names no step the route does
   not carry". Today that file carries four keys (`map` ship_small, `spawn` start, `scene` ship_boarding,
   `encounter` tutorial_sailors) and two of this script's eleven route steps. R24 SLICE-ROUTE (t_e063f248) owns the
   file and has not run. Question: is the re-read done against R24's file, and does R24 have to carry one row per
   route step, in the vocabulary of section 6? If yes, section 6 is the list to check it against. If the check has to
   pass before R24, it cannot, and the honest place to move it is TEST-SLICE-ROUTE (R32, t_030a89e5).
2. **Q2, the save and the TALK fight.** Three files disagree about which comes first. The beat sheet puts the ship's
   log save at beat 27 and the hold encounter at beat 28. Roadmap section 0 lists the fights and then the save. The
   deck data opens the cabin door only on `ship_door_open`, which only the sailor fight sets, so in the data the
   order has to be fight then save. This script follows roadmap section 0 and the data: S6.2 then S6.3. If gamedev
   rules for the beat sheet's order, S6.3 and S6.2 swap places and no second of either changes, but the cabin door
   needs its condition taken off `ship_door_open` or the save shot cannot open it.
3. **Q3, three names, two characters.** `specs/19-llm-talk.md` section 2 calls the beat 28 talk fight "the talk fight
   with Morgan the gate sentry, 15 hp, attack 2"; `data/encounters/all.json` names that encounter's enemy
   `navy_sailor`; `knowledge/ARRIVAL-CONTENT.md` calls Morgan the gate sentry and the sailor Dylan. This script never
   types a name: it names the encounter by its data id (`tutorial_sailors`, enemy `navy_sailor`) and lets
   `data/enemies/all.json` put the name on screen. Gamedev to say which character the beat 28 fight is, because the
   caption in S6 says "the sailor" and the row in section 4 says "the deck watch".
4. **Q4, the bar length.** `knowledge/DRIVE-SHOT-LIST.md` section 1 snaps its cuts to `bar_steps` 86 from
   `data/title_timing.json`, but that file now carries 87, three beats of 29, and its own note says why 86 was
   rejected. The drive list's shot 3 is 602 steps, which is 7 bars of 86 and 609 steps at 87. This script keeps 602
   because it is the drive file's own number and the drive scene card owns the decision. The demo's own cuts are on
   seconds, so the demo is unaffected either way; the drive scene is not, and a 7 step drift every bar is the kind of
   thing the frame timing test catches late.

Notes, not questions:

- **N1, the defeat input.** Neither fight in the slice can be lost, so S6.4 needs a forced defeat. Roadmap check 9
  already requires one ("A forced defeat shows the game over screen and CONTINUE restores the save"), so the
  capability is in R27's scope; this script does not invent a key for it. If R27 lands no trigger, S6.4 is cut and
  the total is 171.00 s, still inside the band.
- **N2, the attribution line.** The frames from S4 are built from the OpenStreetMap extract, and ARRIVAL-CONTENT
  section 1 requires the ODbL line on any screenshot or credit built from that block. The recording therefore ends on
  a card carrying it verbatim: `(c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0,
  https://www.openstreetmap.org/copyright`. R44 owns where that card sits; this file names that it has to exist.
- **N3, the recorder.** `tools/play_demo.py` and `data/demo/run_001.json` already record the title, the menu, the
  crawl and one room at 60 fps and cut the frame to a true 3x of 256 by 240. This script adds no recorder; section 7
  is the event list that file grows into, and the run is short of today's recorder by four route steps that are not in
  the build yet (S3, S4, S5, and half of S6).

---

## 10. The checks, and how each is met

| The card's check | How this file meets it |
| --- | --- |
| the total runs 170 to 190 seconds | 180.00 s exactly, 10,800 steps, printed per shot in section 1 and recomputed in section 2; both designed fallbacks (173.97 s and 171.00 s) are inside the band |
| every step of the slice route appears | the eleven rows of section 6 are roadmap section 0's own list, each mapped to one shot, in order |
| each shot names its input and its claim | every shot heading carries a `Screen`, `Input`, `Music`, `Caption` and `Claim` line, and every beat row carries the input that lands on it |
| the two Meta shots name the bake receipt field the frame shows | section 4 names `model` and `request_hash` per shot and says which of the two each overlay prints; both are fields D5 and spec 19 section 2 put in the row |
| no dash characters | the file was scanned for U+2013, U+2014 and U+2015 after writing: zero |
| a re-read against `data/slice.json` names no step the route does not carry | the script names nine route steps that today's four key route file does not carry, so this check cannot pass until R24 lands; Q1 states that plainly rather than implying a pass, and section 6 is the list R24's file is checked against |

Written by research-assistant, 2026-10-22. Nothing here was run in the engine: this file plans the recording, and
the recording is where each row is proved or corrected.
