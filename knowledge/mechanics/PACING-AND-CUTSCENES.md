# Pacing and cutscenes: how the first fifteen minutes are built

Card t_0ef1125d (MECH-STUDY-3), research-assistant, written 2026-10-22 for Primordial Paradox.
Scope name `pacing`. Executable recipes: `data/mechanics/pacing_recipes.json` (32 recipes, machine checked).

Companion decision files this study feeds and must agree with: `specs/03-camera-and-scaling.md`,
`specs/04-overworld-rails-and-triggers.md`, `specs/05-dialogue.md`, `specs/06-cutscene-runner.md`,
`specs/11-save.md`. Where this file and a spec disagree, the spec wins and this file is the one to correct,
because the specs are Nayil's decisions and this file is a study.

Reference rule (PLAN-V2 section 0): the games below were studied from published manuals, wiki documentation,
guides, community measurements and developer interviews. Nothing was downloaded, ripped, traced, sampled or
decompiled. No line of another game's dialogue is reproduced here: every text claim is a count, a duration or
a description in my own words.

Tagging. Every claim ends with a source id in square brackets, for example [P-09]. Section 10 lists the link
and the read date for each id. `[inference]` marks my own operationalisation of a source, written so the beat
sheet and the recipe file have a number to hit.

A note on the word "first fifteen minutes": the card's beat sheet covers title, crawl, the drive on the M3,
arrival and ship boarding. Fifteen minutes is a long time in this format, so the beat sheet is built to fill
it with play as well as film, and section 9 states the measured share of each. If the drive were the only
interactive break, the player would not touch a control until about five minutes in, which no reference game
in section 2 does; the services stop interlude in beat 12 exists to fix exactly that.

---

## 1. The measured frame we are pacing inside

Everything below is in steps at 60 steps a second, the project's own unit.

| Quantity | Value | Source |
| --- | --- | --- |
| Frame | 256 by 240 pixels, hard constant | spec 03 |
| Playfield | 16 by 15 tiles of 16 by 16 pixels | spec 04 |
| Free walk | 12 steps per tile, so 5 tiles a second | spec 04 |
| Rail walk | 8 steps per tile, so 7.5 tiles a second | spec 04 |
| Cross one screen on foot | 16 tiles, 192 steps, 3.2 s | derived from the two rows above |
| Cross one screen on a rail | 128 steps, 2.1 s | derived |
| Text box | 30 characters a line, 3 lines a page, 2 steps a character | spec 05 |
| Type a full page | 90 characters, 180 steps, 3.0 s | derived |
| Fade | 12 steps, 24 at an act boundary | spec 06 |
| Camera move | 24 steps, linear | spec 06 |
| Music crossfade | 30 steps | spec 06 |

Two consequences follow immediately and both are used in section 9.

1. A screen is 3.2 s of walking, so "walk two screens to the gangway" is a six second beat, not a minute. In
   this format the time budget belongs to reading and to film, not to walking. Walking only becomes expensive
   in tens of screens, which is why maps are measured in screens rather than in tiles.
2. A page of text is 3.0 s of typing but needs about 1.2 s of dwell before the player has read it, so one
   page costs about 4.5 s of the fifteen minutes. Twelve pages is 54 s, which is one twentieth of the opening.

---

## 2. The four openings, side by side

What each game actually does between pressing start and the first real decision, in the order it happens.

### 2.1 The Legend of Zelda (Famicom Disk System 1986, NES 1987)

- Title screen: a waterfall between two cliffs under a pink sky, with the logo and a press start line. After
  9 seconds the sky fades to night and the screen goes black [P-01].
- Then a prologue text block, framed by vines, scrolls up from the bottom of the screen and holds for several
  seconds once fully shown [P-01]. It is short, roughly four sentences in the NES English version [P-01].
- After the text, the screen continues into a list of the game's items, then a card telling the player to read
  the manual, and then the whole sequence loops back to the beginning [P-01]. The title is therefore not a
  splash screen, it is a one minute attract film that a player can watch or interrupt.
- File creation, then control. The first thing the player does is walk into a cave and hear one line from an
  old man who gives the sword [P-02]. Game Informer's timing piece notes that hardly a minute passes from the
  start press to exploring the overworld [P-02].
- Text is centred and up to three rows on the NES release, where the disk version was right aligned and two
  rows [P-18]. There is no text box and no portrait [P-18].
- Scale: the overworld is 4096 by 1344 pixels, 16 columns by 8 rows of rooms, 128 rooms, each room 256 by 176
  pixels and 16 by 11 tiles [P-09]. The first area a new player sees is one room and one cave.

Lesson: the cheapest opening in the set is also the boldest. Zelda spends its minute on atmosphere it will
never explain and hands the player a weapon as the first reward. Nothing is typed.

### 2.2 Final Fantasy (NES, 1987)

- Title screen over a bridge, then new game, then the party workshop: four classes chosen from six and, on
  the original, named by the player. Party creation is the real opening cutscene and it is entirely menus.
- The battle message speed is a player setting called response rate, 1 (slow) to 8 (fast), set on the title
  before the game or from the menu, and it is described in Nintendo's own manual for the release [P-06]. The
  manual's wording is about messages shown during battle, which is the tell that the slow part of that game
  is combat text, not story text.
- Community memory of the same setting is specific: at the slowest rate a multi target spell can spend around
  thirty seconds showing its messages, and at the fastest rate the same round is about ten [P-06 companion
  discussion, treated as anecdote]. Nothing speeds up field text [P-06 companion discussion, anecdote].
- World scale: a 256 by 256 tile overworld in the ROM [P-10], at 16 by 16 pixels a tile, which is 4096 by 4096
  pixels [P-11, community measurement]. On a 256 pixel wide screen that is 16 screens across and about 17
  screens down.

Lesson: FF1 makes the party the prologue and then makes the player sit through battle text. The pacing
failure of that game is a text speed failure, and it was shipped with a player facing slider to fix it.

### 2.3 Mother (Famicom, 1989; released in English as EarthBound Beginnings in 2015)

- It opens with a short background story, the abduction of a couple from their home in the early 1900s, one
  of whom returns alone and studies something nobody understands [P-15].
- Then the player is a twelve year old boy in a house that is being attacked by a poltergeist; lamps and a
  doll come to life and the first fight is inside the first room, before any town, before any shop [P-15,
  P-16]. Beating the doll yields a music box melody [P-16].
- The father telephones, tells the boy to go on a little adventure, and points at the basement [P-16]. The
  diary in the basement is what actually starts the journey, and the first town follows [P-16].
- Saving is diegetic: the player picks up a telephone and calls the father, who also moves money into the
  bank account [P-14].
- The battle system is random encounters into a first person menu fight [P-14].

Lesson: Mother puts the first fight inside the first room of the first building, inside two minutes, and it
makes the save system a prop in the fiction. Both are cheap and both are copied in section 9.

### 2.4 The 2015 indie RPG whose opening crawl is the modern reference

Naming it in this file is fine; the data files cannot carry the name, see section 12.

- The intro is a crawl over a single music track that is 1 minute 20 seconds in the game's files, at 131 bpm
  [P-03]. The crawl and the track are the same length, so the music is the timing device rather than a timer
  in code.
- Then character naming, then the player wakes on a bed of flowers and walks right into a tutorial fight that
  the player cannot lose [P-19].
- The first save point is one room after the rescue, before the first puzzle [P-19, P-20]. A second save
  point follows after a phone call and one optional conversation, well inside the first ten minutes [P-19].
- A second tutorial fight teaches the non violent option, and the player is told explicitly to try it [P-19].
- Text speed is a per character delay measured in frames at 30 frames a second, and the game's slowest
  dialogue runs at 10 frames a character, which the wiki states as three characters a second [P-04, P-05].
  The engine's own delay codes span 5 to 150 frames for punctuation and dramatic pauses [P-05].

Lesson: the modern reference is not faster than the NES, it is slower and better timed. Three characters a
second at its slowest is one tenth of our type speed, and it still works, because the box is short and every
page is worth reading.

---

## 3. Text: speed, geometry, pauses

### 3.1 Characters a second, converted

| Game | Setting | Characters a second |
| --- | --- | --- |
| The 2015 indie RPG, slowest dialogue | 10 frames a character at 30 fps [P-04] | 3 |
| The same engine at one frame a character | 1 frame a character [P-05] | 30 |
| Final Fantasy, battle response rate 1 to 8 | a slider, no published frame figure [P-06] | not convertible, treated as a range |
| Our default (spec 05) | 2 steps a character at 60 steps [spec 05] | 30 |
| Our fast forward (spec 05) | 3x, floor 1 step | 60 to 90 |

So our default type speed is already at the fast end of what shipped, and our fast forward is twice as fast
as the quickest setting in the reference set. The reason that is acceptable is the box: 30 columns of an 8 by
8 font is a fifth of a screen a line, so the eye travels a short distance and the words land together. The
2015 game types slowly into a box that covers most of its frame width, so a 40 character line there still
finishes in about the same screen time as one of ours.

### 3.2 Pauses are the real pacing control

A character a second figure tells you the cost of typing and nothing about the rhythm. The rhythm is in the
pauses, and both reference engines publish theirs.

- The 2015 engine maps nine delay codes to 5, 10, 15, 20, 30, 40, 60, 90 and 150 frames, and uses the small
  ones before commas and the large ones inside ellipses [P-05]. In seconds at 30 frames that is 0.17 to 5.0 s.
- Our spec 05 sets 8 steps after a full stop, question mark or exclamation (0.13 s) and 3 steps after a comma
  (0.05 s), which is at the fast end of that ladder [spec 05].
- Reading dwell is not in either spec and both reference games solve it by requiring a press. Ours does too:
  a page never advances on its own [spec 05]. That means the dwell is the player's, and the design job is to
  make the page worth the press. `[inference]` A 90 character page needs about 1.2 s of dwell for an average
  reader, so a page cycle is about 4.5 s.

### 3.3 Box and page geometry

Zelda has no box: text is drawn over the playfield, centred, up to three rows, and stays until the player
presses [P-18]. FF1 uses a window that holds four lines of roughly 20 characters. Our spec 05 lands between
them at 30 characters by 3 lines, with the box pinned to the bottom 64 pixels of the frame [spec 05].

The number that matters for a study of the first fifteen minutes: a page is 90 characters, so a cutscene of
12 pages is 1080 characters, which is about four sentences a page and reads in under a minute of real time.
Our own `data/intro_text.json` crawl is 258 characters over 6 beats, which is a third of that budget.

---

## 4. Cutscene grammar

### 4.1 Shot length

The drive on the M3 is the only long film in the opening, so its shot length sets the feel of the game. Two
anchors: the Zelda attract sequence holds its night sky for 9 seconds before it changes state [P-01], and the
2015 intro holds a single crawl beat for the whole of an 80 second track, changing the picture far less often
than a film would [P-03].

`[inference]` On a 256 by 240 screen at 16 pixel tiles, a shot shorter than 6 seconds reads as a stutter,
because the player needs about 4 seconds to take in a new 16 by 15 tile composition. The recipe set therefore
uses 8 to 20 seconds a shot with a median of 14, and the beat sheet's drive averages 14.8 s over 12 shots.

### 4.2 Transitions

- A hard cut is free in steps and expensive in attention: it may only land on a musical downbeat, because the
  music is the only thing telling the player the cut was intended [P-03, which is the same principle: the
  track is the timing device].
- A fade costs 12 steps [spec 06]. Twelve steps is 0.2 s, which is fast for a scene change by film standards
  and correct for this one: at 60 steps a second, a slow fade would read as a loading break.
- An act boundary gets 24 steps [spec 06], and the only one in the opening is the fade under the chapter card.

### 4.3 Camera

The camera moves 24 steps per command, linear [spec 06]. Using that as the unit: a pan down Big Ben from the
clock face to the street is 3 camera commands, 72 steps, 1.2 s of movement spread over a 12 second beat. More
than 3 commands in a beat and the shot is about the camera rather than about the place.

The one rule worth stating as a refusal: no camera move while a text box is open [spec 06 forbids a second
confirm consumer, which is the same discipline]. A box and a moving camera compete for the same attention and
the player loses.

### 4.4 Music as the clock

The reference intro is 80 seconds long because its track is 80 seconds long [P-03]. Our title theme is a 52
bar waltz at 126 bpm, which is 156 beats and therefore 74.3 seconds a pass through the loop. The intro crawl
at 25 s is therefore about a third of one pass, which is a comfortable ratio: the crawl ends while the theme
still has somewhere to go.

Two recipes follow. One music cue per scene, changed only on a hard cut or a fade [inference]. And 90 steps
(1.5 s) of silence before a reveal, because silence is the only transition that costs nothing and reads as
intentional.

### 4.5 The car has no interior

Nayil's decision of 2026-10-21 is that the car interior is never shown (PLAN-V2 section 2, item 4). That is a
pacing constraint, not only an art one: dialogue inside a moving car cannot use a portrait, so it becomes a
bottom of screen caption with the car seen from outside, and the camera does the acting. The night drive shots
are listed as: wide exterior of the car, the gantry sign, the cutting, the cathedral silhouette, the storm,
the moon, the slip road, the docks. Nine shots, no interior, no faces.

---

## 5. Maps measured in screens

| Game | Overworld | In screens | First area |
| --- | --- | --- | --- |
| Zelda | 4096 by 1344 px, 16 by 8 rooms of 256 by 176 px [P-09] | 128 rooms | 1 room plus 1 cave [P-02] |
| Final Fantasy | 256 by 256 tiles of 16 by 16 px, 4096 by 4096 px [P-10, P-11] | 16 by about 17 | town plus a short field walk |
| Ours, Town Quay sample | 53 by 56 tiles at 8 m a tile, 424 by 448 m [P-22] | 3.3 by 3.7 screens of 16 by 15 tiles | the dock yard, 6 to 12 screens |

Two ratios worth carrying into the map pipeline.

1. Zelda's room is 16 by 11 tiles and ours is 16 by 15: our screen shows four more rows, so a "screen" of our
   map holds 36 percent more tiles than the reference room and needs more content per screen to feel as full.
2. A tile is 8 m in our OSM drafts [P-22], so one screen is 128 by 120 m of real ground. A real 500 m walk
   along Town Quay is 62 tiles, which is 3.9 screens, and 12.5 s of free walking. A city map is therefore
   cheap in screens and expensive in content, which is the opposite of the overworld.

---

## 6. Travel and encounters

### 6.1 What the references roll, and why we cannot

Dragon Quest 1 rolls an encounter per tile, per terrain type: 1 in 48 on a bridge, 1 in 24 on meadow, 1 in 16
in swamp and forest, 1 in 8 on hills and in desert, with the starting zone around the first castle at half
those rates, so 1 in 48 on its grass [P-07, P-08]. The same guide notes that walking 100 steps with no battle
is possible but very unlikely [P-07].

Put those rates against our walking speed and the design problem is immediate. At 5 tiles a second, 1 in 24 is
a fight every 4.8 seconds of walking and 1 in 8 is a fight every 1.6 seconds. On a 16 tile screen that is
between one and three fights per screen. That is what the reference does to a player at 1990 walking speeds,
and it is the single clearest thing not to copy.

Our spec 04 already refuses random encounters: encounters are visible markers, drawn as a small silhouette,
touched to start a battle, gone for 30 steps then respawned [spec 04]. The DQ1 table survives here only as a
density ceiling: the reference's most generous terrain is 1 encounter per 8 tiles, so a marker every 8 tiles
is an upper bound we must stay well under.

### 6.2 Encounter pacing that follows from that

- One marker per 40 to 60 walkable tiles, which at 5 tiles a second is a fight every 8 to 12 seconds of
  walking, and at most one per 2.5 screens. Two markers visible on one screen is the cap.
- No marker within 6 tiles of a map entry, a door, or the tile where a cutscene hands control back, because a
  fight in the first second of control reads as a punishment for arriving.
- Triggers are inert for 20 steps after a cutscene or battle [spec 04], which is the same idea one step up.
- First fight 45 to 60 s, field fight 25 to 40 s, boss 90 to 150 s. The first fight must be winnable with one
  command, which is the Mother lesson (fight in the first room) minus the death.

### 6.3 Save points

| Game | How you save | What it costs |
| --- | --- | --- |
| Zelda | the death prompt, then continue | you lose the room, not the run [P-02, P-17 context] |
| Dragon Quest | talk to the king in the first castle | a walk back to the throne room |
| Mother | pick up any telephone and call the father [P-14] | a screen of dialogue, in the fiction |
| The 2015 indie RPG | star points, the first one a room after the rescue [P-19] | nothing, it is free and it heals nothing |
| Ours | the ship's log terminal plus autosave on map entry after the fade [spec 11] | one page of text |

The spacing that follows: a save point every 8 to 12 screens, or every 120 s of dangerous walking, and the
first one inside the first fifteen minutes at 9 min 52 s to 10 min 42 s in the beat sheet (beat 27).

---

## 7. Real places: the M3 and Southampton

Real geography is the cheapest source of a map that feels designed, because the road was designed.

- The M3 runs from Sunbury on Thames to Eastleigh, 59 miles or 95 km, passing Basingstoke and Winchester, and
  its southern end feeds the Chilworth roundabout on the edge of Southampton [P-12]. One road reference gives
  61 miles for the same road, which is a reminder that a published length depends on where you stop counting,
  so we use 95 km and say "about" [P-13].
- The stretch that matters to our title and our drive is the one south of Winchester: the motorway curves
  around the east of the city through the deep cutting at Twyford Down, then crosses the South West Main Line
  beside the River Itchen and runs through Eastleigh to Southampton [P-12]. That cutting is a wall of chalk on
  both sides at night, which on a 256 pixel screen is two bands of one colour and a headlight pool, the
  cheapest possible "we are in the downs" shot.
- London to Southampton by road is about 80 miles, quoted between 1 h 23 min and 1 h 45 min depending on the
  source and the traffic [P-21]. Route tables put Winchester at 67 miles and 1 h 08 min, so two thirds of the
  drive is behind you at the cathedral [P-21].
- Turn that into film: 12 shots in the drive block, 178 seconds of screen time (218 with the playable
  interlude), for a journey of about 80 minutes of story time. That is a compression ratio of roughly 28 to 1,
  or one second of screen for every 28 seconds of road. `[inference]` A viewer tolerates that ratio only
  because each shot is a different kind of place: city, gantry, open motorway, cutting, cathedral, downland,
  slip road, docks. Eight locations in three minutes is the density rule for a compressed journey.
- Southampton docks themselves: the Town Quay block we already drafted is 424 by 448 m of real ground at 8 m
  a tile [P-22], which is 3.3 by 3.7 screens. Our first hub is that block, so the hub is under 4 screens of
  walking across, which is why it needs 6 to 10 doors and 3 to 5 people rather than a bigger map.

The rule this gives the map pipeline: a real place gives you the layout and the names for free, and it gives
you the distances, which are the thing a hand drawn map always gets wrong. It does not give you the interest
points, which still have to be authored at the density in section 5.

---

## 8. What we deliberately do not copy

- Random encounters at a rate per tile. Refused, for the arithmetic in section 6.1.
- A battle message speed the player has to find on the title screen, which is FF1's shipped patch for its own
  slowness [P-06]. Our text speed is fixed and our fast forward is a held button [spec 05].
- An unskippable two minute crawl. Our crawl allows a skip after any beat completes, with a 45 step hold on
  START and an ignore window of 60 steps so a double tap does not skip the story by accident (recipe PAC-05).
- A car interior with talking heads (Nayil, 2026-10-21).
- Any of the reference games' dialogue, phrasing, names, item names, map layouts or musical notation. Every
  number above is a measurement or a decision, not a transcription, and no line of text is quoted anywhere in
  this file or its data file.

---

## 9. Proposed beat sheet for our first 15 minutes

The rule the sheet is built to: the player touches a control by 2 min 30 s, has full control by 6 minutes, has
fought once by 8 minutes and has saved by 11 minutes, and the sheet sums to exactly 900 seconds.

| # | Beat | Kind | Duration | Running total |
| --- | --- | --- | --- | --- |
| 1 | Title attract: logo, moon, storm cloud, one lightning flash; loops until START | title | 32 s | 0:32 |
| 2 | PRESS START, menu, NEW GAME confirmed | menu | 10 s | 0:42 |
| 3 | Fade to black, star field, sickle and bolt constellations | cutscene | 5 s | 0:47 |
| 4 | Crawl beats 1 to 2 (the gods forgotten) | crawl | 8 s | 0:55 |
| 5 | Crawl beats 3 to 4 (the four who do not know) | crawl | 9 s | 1:04 |
| 6 | Crawl beats 5 to 6 (entropy, Southampton, October) and hold | crawl | 8 s | 1:12 |
| 7 | Fade in on Big Ben at night, camera pans down to the street | cutscene | 10 s | 1:22 |
| 8 | London street, the car pulls away, the Thames | cutscene | 12 s | 1:34 |
| 9 | M3 gantry, sign reading Southampton with a distance figure | cutscene | 8 s | 1:42 |
| 10 | Rain starts, wipers seen from outside the car | cutscene | 12 s | 1:54 |
| 11 | Radio: four caption pages, no portrait, car in long shot | cutscene | 36 s | 2:30 |
| 12 | Winchester services: player walks one screen, reads a sign, presses on | walk | 40 s | 3:10 |
| 13 | Twyford Down cutting at night, headlight pool on chalk | cutscene | 12 s | 3:22 |
| 14 | Winchester Cathedral silhouette far off, one caption | cutscene | 14 s | 3:36 |
| 15 | Radio: three caption pages, the subject turns to the sea | cutscene | 24 s | 4:00 |
| 16 | Storm cloud forms over the car, first lightning, 2 frame palette flash | cutscene | 14 s | 4:14 |
| 17 | Chalk downland, moon, road markers, the storm keeping pace | cutscene | 10 s | 4:24 |
| 18 | Hard cut: slip road, Southampton sign, headlights | cutscene | 8 s | 4:32 |
| 19 | The docks: cranes, containers, the ship lit at the quay | cutscene | 18 s | 4:50 |
| 20 | Gate checkpoint: guard, four pages, one three option choice | cutscene | 52 s | 5:42 |
| 21 | Full control: the dock yard, 3 screens, no text | walk | 28 s | 6:10 |
| 22 | Dock office: two people, six pages, the boarding pass | cutscene | 72 s | 7:22 |
| 23 | First encounter marker: the hold hound, one command win | battle | 48 s | 8:10 |
| 24 | Quay side walk, 2 screens, one short caption about the water | walk | 30 s | 8:40 |
| 25 | Gangway, deck, the ship's horn, the door | cutscene | 32 s | 9:12 |
| 26 | Ship corridor, 3 rooms, free walk | walk | 40 s | 9:52 |
| 27 | Cabin: the ship's log, first save, two pages and the menu | save | 50 s | 10:42 |
| 28 | Second encounter in the hold, teaches TALK, cannot be lost | battle | 90 s | 12:12 |
| 29 | Stairwell and upper deck, free walk | walk | 42 s | 12:54 |
| 30 | The ship leaves port, Quay receding, no text | cutscene | 36 s | 13:30 |
| 31 | Kronos seen from the deck, sickle of stars, no text | cutscene | 50 s | 14:20 |
| 32 | Chapter card and fade to black | cutscene | 40 s | 15:00 |

Sum: 900 s exactly, which is 15 min 00 s.

The measured shares, which are the check that this is not a film with a game attached:

| Kind | Seconds | Share |
| --- | --- | --- |
| Cutscene and dialogue | 465 | 51.7 percent |
| Walk | 180 | 20.0 percent |
| Battle | 138 | 15.3 percent |
| Save | 50 | 5.6 percent |
| Title | 32 | 3.6 percent |
| Crawl | 25 | 2.8 percent |
| Menu | 10 | 1.1 percent |
| Walk plus battle (real play) | 318 | 35.3 percent |

The gates this sheet meets: first input at 150 s (beat 12 starts at 2:30), full control at 342 s (5:42),
first fight beginning at 442 s (7:22) and ending at 490 s, first save beginning at 592 s (9:52) and ending at
642 s, first interior (the dock office, from 370 s, which is 6:10, and the cabin from 9:52) inside 10
minutes, cutscene share under 60 percent, play share over 20 percent.

Two honest risks.

1. Beat 11 alone is 36 s of reading before the first input. That is the price of the radio device, and it is
   why the services interlude sits immediately after it rather than at the end of the drive. If playtesting
   shows the player disengaging, cut one page from beat 11 and give the 9 s to beat 21.
2. Beat 31 is 50 s with no text and no input. It is the game's first look at the antagonist and it is the only
   beat with nothing to press. If it tests badly, the fix is not to shorten it but to move the chapter card
   inside it, so the fade begins while the image is still on screen.

---

## 10. Sources

Every link was read on 2026-10-22 unless stated. Nothing was downloaded as an asset.

| Id | Source | Link | What it supports |
| --- | --- | --- | --- |
| P-01 | Zelda Wiki, Title Display | https://zeldawiki.wiki/wiki/Title_Display | 9 s sky fade, upward text scroll, item list, loop, the press start line |
| P-02 | Game Informer, Getting the Ball Rolling: Timing Zelda's Lengthy Introductions (2013-11-07) | http://gameinformer.com/b/features/archive/2013/11/07/getting-the-ball-rolling-timing-zelda-s-lengthy-introductions.aspx | under a minute from start press to exploring; the cave and one line |
| P-03 | Undertale Wiki, Once Upon a Time | https://undertale.wiki/w/Once_Upon_a_Time | intro track 1:20 in the game file, 131 bpm, plays over the introduction on every launch |
| P-04 | Undertale Wiki, Toriel | https://undertale.wiki/w/Toriel | slowest text in the game, 10 frames a character, three characters a second |
| P-05 | UT/DR Reference, Text and Dialogue | https://sjelter-codes.github.io/utdr-reference/UNDERTALE/textdialogue.html | delay codes 5 to 150 frames, 30 frames a second |
| P-06 | Nintendo, official Final Fantasy manual (NES Classic) | https://nintendo.co.jp/clv/manuals/en/pdf/CLV-P-NABJE_en.pdf | response rate 1 slow to 8 fast for battle messages |
| P-07 | Dragon Quest Wiki, Random Battles | https://dragon-quest.org/w?title=Random_Battles | per tile encounter rates by terrain, 1 in 48 to 1 in 8 |
| P-08 | Ryan8bit, Dragon Quest formula guide | https://gamefaqs.gamespot.com/snes/564868-dragon-quest-i-and-ii/faqs/61640 | starting zone at half rate, 1 in 100 steps possible |
| P-09 | Invent with Python, 8-bit NES Legend of Zelda Map Data | https://inventwithpython.com/blog/8-bit-nes-legend-of-zelda-map-data.html | 4096 by 1344 px, 16 by 8 rooms, 256 by 176 px a room, 16 by 11 tiles |
| P-10 | Data Crystal, Final Fantasy world map data | https://datacrystal.tcrf.net/wiki/Final_Fantasy/World_map_data | 256 by 256 tile world map in the ROM |
| P-11 | GameFAQs, FF1 world map tile dimensions (community answer) | https://gamefaqs.gamespot.com/nes/323462-final-fantasy/answers/324302-how-many-tilesor-steps-is-the-world-maps-height-and-width | 16 by 16 px a tile, 4096 by 4096 px total |
| P-12 | Wikipedia, M3 motorway (Great Britain) | https://en.wikipedia.org/wiki/M3_motorway_(Great_Britain) | 59 miles, 95 km, Sunbury to Eastleigh, Twyford Down, Chilworth roundabout |
| P-13 | roads.org.uk, M3 | https://roads.org.uk/motorway/m3 | 61 miles, London to Southampton, junction list |
| P-14 | Wikipedia, EarthBound Beginnings | https://en.wikipedia.org/wiki/EarthBound_Beginnings | phone save to the father, random encounters, first person fights, 1989 |
| P-15 | Giant Bomb, EarthBound Beginnings | https://giantbomb.com/wiki/Games/Earthbound_Beginnings | opens with the background story of the couple; the house attack |
| P-16 | The Codex, MOTHER Ninten | https://thecodex.wiki/MOTHER/Ninten | poltergeist, doll fight, melody, father's call, basement diary, then town |
| P-17 | Wikipedia, The Legend of Zelda (video game) | https://en.wikipedia.org/wiki/The_Legend_of_Zelda_(video_game) | the short prologue that plays after the title screen |
| P-18 | The Cutting Room Floor, Zelda console differences | https://tcrf.net/The_Legend_of_Zelda/Console_Differences/ja | NES text centred, three rows; disk version right aligned, two rows |
| P-19 | IGN, Undertale Ruins guide | https://ign.com/wikis/undertale/Ruins | tutorial fight, save point after the rescue, dummy tutorial, phone call, second save |
| P-20 | StrategyWiki, Undertale Ruins | https://strategywiki.org/wiki/UNDERTALE/Ruins_(Pacifist) | save star before the stairs, the corridor, the cell phone |
| P-21 | DriveBestWay, London to Southampton | https://drivebestway.com/distance/london-gb/southampton-gb | 80 miles, 1 h 23 min, Winchester at 67 miles and 1 h 08 min |
| P-22 | Our own OSM drafts, `data/maps/osm/*.json` (Overpass fetch 2026-10-22T04:05Z) | local repo | 8 m a tile, Town Quay bbox, 53 by 56 tiles |
| P-23 | Project specs 03, 04, 05, 06, 11 | local repo, `specs/` | every number marked [spec NN] |

## 11. The recipe file

`data/mechanics/pacing_recipes.json` holds 32 recipes in six families, each with the parameters a writer or a
tool needs and a list of refusals:

| Family | Count | Ids | Subject |
| --- | --- | --- | --- |
| OP | 6 | PAC-01 to PAC-06 | title, boot, crawl length, crawl speed, skip guard, idle attract |
| TX | 5 | PAC-07 to PAC-11 | type speed, punctuation pauses, page geometry, dialogue budget, benchmark table |
| CS | 6 | PAC-12 to PAC-17 | shot length, fades, camera, music, flash and shake, the no interior rule |
| AR | 5 | PAC-18 to PAC-22 | screen unit, first area size, hub size, interest density, screen crossing time |
| TR | 6 | PAC-23 to PAC-28 | encounter model, marker density, grace, battle length, save spacing, save models |
| PL | 3 | PAC-29 to PAC-31 | tile to metres, drive compression, city map compression |
| GT | 1 | PAC-32 | the fifteen minute gates, with the measured values the beat sheet meets |

## 12. The clean room note

`tools/check_cleanroom.py` refuses a list of names and phrases anywhere under `game/` and `data/`, which is why
`data/mechanics/pacing_recipes.json` carries source ids only and no game titles: the ids resolve in the table
in section 10 of this file, which is under `knowledge/` and is not scanned. That is the same arrangement the
music recipe files already use. If a title must appear in a data file, the data file is wrong.

## 13. The check

The two deliverables were verified with a script that loads the JSON and asserts:

1. at least 25 recipes, ids unique and sequential, each recipe carrying at least three numeric parameters,
   and the declared family counts matching the recipes actually present;
2. the beat sheet sums to exactly 900 seconds, and every beat's running total recomputes from the durations;
3. the per kind totals recompute from the beats, cutscene at most 60 percent and walk plus battle at least
   20 percent;
4. every source id a recipe cites exists in the source table in section 10;
5. the measured gates (first input, full control, first fight, first save, first interior) fall inside the
   ceilings PAC-32 states, and the measured values written into PAC-32 match the sheet;
6. neither file contains an em dash, an en dash or a horizontal bar.

The commands, run from the repository root on 2026-10-22:

```
python tools/check_pacing.py
python tools/check_data.py
python tools/check_cleanroom.py
```

Results, measured rather than asserted:

- `tools/check_pacing.py`: pass, 32 recipes, 32 beats, 900 seconds. Every gate inside its ceiling: first
  input 150 s, full control 342 s, first fight 442 s, first save 592 s, first interior 370 s.
- The same checker on a deliberately broken copy (one beat lengthened by a second, one recipe reduced to
  prose) reports 35 problems, among them "PAC-04 has fewer than three numeric parameters" and a recomputed
  running total of 33 where the file said 32. A checker that cannot fail is not a check, so this was run and
  the output kept with the card.
- The data file trips none of the clean room gate's 26 names or 12 phrases, because it cites source ids and
  never a title or a link. The study does carry name hits, all inside the section 10 citation table where a
  link has to live; `check_cleanroom.py` does not scan `knowledge/`, so those are in scope by design and not
  a waiver.
- `tools/check_data.py`: all files pass.
- `tools/check_cleanroom.py` is RED repository wide, and not for anything this card wrote. Two causes, both
  outside this card and both reported on the card rather than fixed here: `data/mechanics/jrpg_recipes.json`
  and `game/datafiles/mechanics/jrpg_recipes.json` carry one of the refused names, and they were written by
  a concurrent card into the same directory on the same day; and `data/osm_cache/southampton_town_quay.json`
  plus `data/osm_cache/winchester_high_street.json` carry a refused name because a real Southampton street
  is called Queen Street, so the OSM harvest trips the list by accident. The Queen hits pre-date this card.

`tools/check_pacing.py` is in the shared tool directory rather than in the card's workspace because a red
gate needs a command anyone can rerun, and because this file will be re-checked every time the beat sheet
changes. It imports `check_cleanroom` rather than copying its lists, so the two gates cannot drift apart.
