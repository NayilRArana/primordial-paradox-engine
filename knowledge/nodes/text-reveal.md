# Node: text, dialogue, typewriter and menus

Written 2026-10-23 against the tree of that date. Parent doctrine: `knowledge/FOX-STYLE.md` section 7 (text), section 8
(menus), law 7 and law 8. Specs: `specs/05-dialogue.md`, `specs/07-battle-director.md` rule 6, and the crawl addendum in
`specs/14-title-screen-drive.md`. There is no `specs/07-text.md`; 07 is the battle director and the text spec is 05
`specs/05-dialogue.md`.

Files this node covers:

- `game/scripts/pp_text/pp_text.gml` (211 lines): the one reveal machine `game/scripts/pp_text/pp_text.gml`.
- `game/scripts/pp_dialogue/pp_dialogue.gml` (392 lines): the dialogue box layout `game/scripts/pp_dialogue/pp_dialogue.gml`.
- `game/scripts/pp_battle_text/pp_battle_text.gml` (709 lines): one board layout plus the talk bake path
  `game/scripts/pp_battle_text/pp_battle_text.gml`.
- `game/scripts/pp_title/pp_title.gml` (1101 lines): the intro crawl from line 830 `game/scripts/pp_title/pp_title.gml`.
- `game/scripts/pp_font/pp_font.gml` (190 lines): the one glyph path `game/scripts/pp_font/pp_font.gml`.
- `game/scripts/pp_input/pp_input.gml` line 194: the one cursor axis helper `game/scripts/pp_input/pp_input.gml`.
- `game/scripts/pp_config/pp_config.gml` lines 191 to 214: every text number below
  `game/scripts/pp_config/pp_config.gml`.

The one line: **one reveal machine in `pp_text` decides when a character appears, three layouts decide where the
characters sit, and the menu half of this node has no shared implementation at all.**

---

## 1. What the player sees and does

### The dialogue box

A 240 by 64 window at (8, 168) over the bottom of the frame `game/scripts/pp_config/pp_config.gml`. The text area is
x 16 to 240, y 176 to 224: 28 characters a row, 3 rows a page, one row every 10 pixels
`game/scripts/pp_config/pp_config.gml`. A name plate is a 68 by 12 rectangle from x 8 to x 76 at y 162 to y 174, and
it is not drawn when the page's speaker is `narrator` or empty `game/scripts/pp_dialogue/pp_dialogue.gml`. There is no
portrait, and no portrait geometry exists in the slice `specs/05-dialogue.md`.

Text types one character at a time at 2 steps a character `game/scripts/pp_config/pp_config.gml`. A 6 by 6 arrow
blinks at (236, 222), 15 steps on and 15 steps off `game/scripts/pp_config/pp_config.gml`. When the entry has another
page a second arrow appears at (230, 222), so two arrows mean a page follows and one means the last page
`game/scripts/pp_dialogue/pp_dialogue.gml`.

On a page that offers choices, once that page has finished typing its three rows are replaced, not covered, by one row
per choice in the same three 10 pixel rows `game/scripts/pp_dialogue/pp_dialogue.gml`. The cursor is a 6 by 6 block at
x 16 and the label starts at x 24, so a label can never land on a line of dialogue
`specs/05-dialogue.md`. A choice page draws no arrow, because the draw returns before the arrow block
`game/scripts/pp_dialogue/pp_dialogue.gml`.

### The battle message board

A 48 pixel strip across the top of the frame, x 0 to 256 and y 0 to 48, drawn from (16, 16) at 28 columns and a 10
pixel pitch `game/scripts/pp_battle_director/pp_battle_director.gml`. Every line reached so far shows at once, so the
player reads a growing block rather than one line at a time `game/scripts/pp_battle_text/pp_battle_text.gml`. A line
that wraps pushes the next line down by the rows it actually took, so two long lines cannot print over each other
`game/scripts/pp_battle_text/pp_battle_text.gml`. The board advances by itself 8 steps after each line except the last
`game/scripts/pp_battle_text/pp_battle_text.gml`.

### The talk reply block

The same board struct, drawn by its own function: four lines of 28 characters at an 8 pixel pitch from (16, 8), with an
optional hint on its own row at (16, 40) `game/scripts/pp_battle_text/pp_battle_text.gml`. There is no wrap, because a
line over 28 characters was cut at the load `game/scripts/pp_battle_text/pp_battle_text.gml`. The prompt
`* WHAT DO YOU SAY?` takes the message window while a talk is open `game/scripts/pp_battle_text/pp_battle_text.gml`.

### The intro crawl

One beat of the music is one unit of the reveal `game/scripts/pp_title/pp_title.gml`. Rows are drawn at 32 columns, 6
lines on screen, 12 pixels apart, from y 132 `data/title_timing.json`. Any of the confirm, menu or cancel key jumps
the whole crawl to its last beat `game/scripts/pp_title/pp_title.gml`.

### Menus

Five list surfaces exist: the battle command menu, the talk option panel, the dialogue choice rows, the title menu and
the game over card `game/scripts/pp_battle_director/pp_battle_director.gml`. Each is drawn by its own function and each
moves its own cursor; section 6 lists them `game/scripts/pp_battle_director/pp_battle_director.gml`.

---

## 2. The one reveal machine (`pp_text`)

Ten functions, and every layout goes through them `game/scripts/pp_text/pp_text.gml`:

| function | what it is | where |
| --- | --- | --- |
| `pp_text_items(text)` | splits one source line into items `{ch, wait, speed}` | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_visible(items, budget)` | the screen text of the first `budget` items | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_unit_length(rv)` | items in the current unit, 0 when done or missing | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_reveal_begin(units, speaker, auto)` | a reveal struct over an array of item lists | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_reveal_timing(rv, speed, gap, blip)` | a layout's own three numbers on the same machine | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_reveal_step(rv, fast)` | one frame | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_reveal_complete(rv)` | fill the current unit now and drop the hold | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_reveal_next(rv)` | turn to the next unit, empty | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_reveal_finish(rv)` | jump to the last unit, whole, and mark done | `game/scripts/pp_text/pp_text.gml` |
| `pp_text_reveal_done(rv)` | the predicate a layout reads instead of the field | `game/scripts/pp_text/pp_text.gml` |

The struct carries `units, unit, revealed, acc, wait, steps, blips, speaker, speed, gap, blip, auto, done`
`game/scripts/pp_text/pp_text.gml`. A unit is one dialogue page, one board line, or one beat of the crawl; the machine
never knows which, because a unit is a flat item list `game/scripts/pp_text/pp_text.gml`.

### The step, in order

Read `pp_text_reveal_step` top to bottom `game/scripts/pp_text/pp_text.gml`:

1. `steps` goes up by one. This is the machine's own frame clock, and the dialogue page arrow reads it
   `game/scripts/pp_dialogue/pp_dialogue.gml`.
2. If `wait` is above zero it drops by one and the frame ends. A hold blocks everything, including the end of a unit
   `game/scripts/pp_text/pp_text.gml`.
3. If the current unit is fully revealed the frame ends, so a finished unit does nothing on its own
   `game/scripts/pp_text/pp_text.gml`.
4. The speed is chosen: the layout's `speed` field, or `PP_TEXT_STEPS_FAST` while the caller says confirm is held, or
   the item's own `speed` from a `{speed:N}` code when confirm is not held `game/scripts/pp_text/pp_text.gml`.
5. `acc` goes up by one. Under the speed the frame ends; over it the speed is subtracted and the remainder is carried
   `game/scripts/pp_text/pp_text.gml`. At whole numbers that lands on zero. At a fraction, which is what the crawl's
   music timed speed gives, dropping the remainder would slow the text by about a fifth
   `game/scripts/pp_text/pp_text.gml`.
6. `revealed` goes up by one. If this item carries its own `wait` that is added to `wait` and the frame ends
   `game/scripts/pp_text/pp_text.gml`.
7. Punctuation holds: `.` `!` `?` add the stop pause, `,` adds the comma pause
   `game/scripts/pp_text/pp_text.gml`.
8. The blip: if the character is not a space, the speaker is not empty, and `revealed` divides by the blip interval,
   `pp_audio_blip(speaker)` fires `game/scripts/pp_text/pp_text.gml`.
9. End of unit: on the last unit `done` becomes true; otherwise an auto layout advances after `max(wait, gap)` and a
   confirm layout stops there until the layout calls `next` `game/scripts/pp_text/pp_text.gml`.

### The codes

Two codes, in braces so that a code can never be read as prose, exactly as `knowledge/FOX-STYLE.md` section 7 fixes
them `knowledge/FOX-STYLE.md`.

- `{pause:N}` becomes an item with no character and a hold of N `game/scripts/pp_text/pp_text.gml`. It costs **N frames
  of hold plus the ordinary character interval it took to reach it**, because it is one item like any other. A
  `{pause:20}` is 20 plus the normal gap between two characters, not 20 frames `game/scripts/pp_text/pp_text.gml`.
- `{speed:N}` is a setting, not an item: it adds nothing to the list, costs no frames, and applies to every character
  after it in the same source line `game/scripts/pp_text/pp_text.gml`. A value of 0 or less is ignored
  `game/scripts/pp_text/pp_text.gml`. A value of 1 is the same speed as holding confirm, and holding confirm overrides
  a code entirely `game/scripts/pp_text/pp_text.gml`.
- Anything else between braces is reported as `PP: unknown dialogue control code` and the text inside the braces is
  swallowed rather than printed `game/scripts/pp_text/pp_text.gml`. A typo is visible in the log, never on screen
  `game/scripts/pp_text/pp_text.gml`.

### Halt

The machine stops for three different reasons, and a designer needs to keep them apart:

1. **Inside a unit**, on the per character interval plus the holds. Nothing else runs
   `game/scripts/pp_text/pp_text.gml`.
2. **At the end of a unit**, an auto layout waits `gap` and continues; a confirm layout stops until its layout calls
   `pp_text_reveal_next` `game/scripts/pp_text/pp_text.gml`. That is the only difference between the board and the
   box: one boolean plus one number `game/scripts/pp_battle_text/pp_battle_text.gml`.
3. **At the end of the text**, `done` is true and the layout decides what that means
   `game/scripts/pp_text/pp_text.gml`.

### Skip

Three skips, all in the machine, none in a layout `game/scripts/pp_text/pp_text.gml`:

- `complete` fills the current unit and drops the hold. This is the first confirm on a dialogue page
  `game/scripts/pp_dialogue/pp_dialogue.gml`.
- `next` turns to the next unit, empty. This is the second confirm `game/scripts/pp_dialogue/pp_dialogue.gml`.
- `finish` jumps to the last unit, shows it whole and marks done. Only the crawl uses it, from the start key
  `game/scripts/pp_title/pp_title.gml`. A dialogue box cannot skip a whole conversation; the player turns it page by
  page `game/scripts/pp_dialogue/pp_dialogue.gml`.

---

## 3. The numbers

From `game/scripts/pp_config/pp_config.gml` unless marked. Steps are frames, and the project runs at
`PP_STEPS_PER_SECOND` 60 `game/scripts/pp_config/pp_config.gml`.

| thing | value | where |
| --- | --- | --- |
| normal reveal speed | 2 steps a character, so 30 a second | `game/scripts/pp_config/pp_config.gml` |
| speed while confirm is held | 1 step a character, so 60 a second | `game/scripts/pp_config/pp_config.gml` |
| hold after `.` `!` `?` | 8 steps, 0.133 s at 60 a second | `game/scripts/pp_config/pp_config.gml` |
| hold after `,` | 3 steps, 0.05 s | `game/scripts/pp_config/pp_config.gml` |
| hold at a unit end for an auto layout | 8 steps, the default `gap` | `game/scripts/pp_text/pp_text.gml` |
| blip interval | every 3 revealed items, never on a space | `game/scripts/pp_config/pp_config.gml` |
| dialogue box | 240 by 64 at (8, 168) | `game/scripts/pp_config/pp_config.gml` |
| text area | x 16 to 240, y 176, 28 characters, 3 rows, 10 pixel pitch | `game/scripts/pp_config/pp_config.gml` |
| page arrow | 6 by 6 at (236, 222), 15 on, 15 off | `game/scripts/pp_dialogue/pp_dialogue.gml` |
| choice cursor and label | 6 by 6 at x 16, label at x 24 | `game/scripts/pp_config/pp_config.gml` |
| battle window | x 0 to 256, y 0 to 48 | `game/scripts/pp_battle_director/pp_battle_director.gml` |
| battle board draw | (16, 16), 28 columns, 10 pixel pitch | `game/scripts/pp_battle_text/pp_battle_text.gml` |
| talk reply block | 4 lines, 8 pixel pitch, (16, 8), hint at y 40 | `game/scripts/pp_battle_text/pp_battle_text.gml` |
| crawl speed | 18 characters a second, so 3.33 steps a character | `data/title_timing.json` |
| crawl beat hold | 1.2 seconds, 72 steps | `data/title_timing.json` |
| crawl blip | every 3 characters | `data/title_timing.json` |

Three arithmetic consequences a designer will feel:

- Holding confirm is 1 step a character against a normal 2, which is **twice** the speed, not the three times
  `specs/05-dialogue.md` rule 1 promises. Rule 1 also says a floor of 1 step a character, and the floor is what lands
  here: three times 2 steps would be 0.67 steps, which does not exist `specs/05-dialogue.md`.
- A row is 28 items, not 28 glyphs `game/scripts/pp_config/pp_config.gml`. A `{pause:N}` item sits in the row and
  consumes one cell of the wrap budget while printing nothing `game/scripts/pp_dialogue/pp_dialogue.gml`. So a row
  carrying one pause code prints at most 27 characters `game/scripts/pp_dialogue/pp_dialogue.gml`.
- The blip interval counts `revealed` items, not printed glyphs `game/scripts/pp_text/pp_text.gml`. One `{pause:N}` in
  a line shifts the blip phase by one after it, so the cadence is measured from the pause rather than from the printed
  characters `game/scripts/pp_text/pp_text.gml`.

---

## 4. The layouts

| layout | units are | auto | speaker | numbers it overrides |
| --- | --- | --- | --- | --- |
| `pp_dialogue` | one page | no | the page's speaker | none, spec 05 numbers |
| `pp_battle_text` board | one line | yes | empty, so no blip | none |
| `pp_title` crawl | one beat of the music | yes | `narrator` | speed, gap, blip |
| `pp_talk_board_draw` reply | one line | yes | empty | pitch 8, no wrap, 4 line cap |

Every row of that table is one call into `pp_text` `game/scripts/pp_text/pp_text.gml`. What each layout owns, and what
it must never own again:

- `pp_dialogue` owns wrap, pagination, the page unit, the choice list, the name plate and the box draw
  `game/scripts/pp_dialogue/pp_dialogue.gml`. It owns no character clock, no hold, no blip and no done predicate, and
  its header says so `game/scripts/pp_dialogue/pp_dialogue.gml`.
- `pp_battle_text` owns the line list and the board draw `game/scripts/pp_battle_text/pp_battle_text.gml`.
- `pp_title` owns the beat grouping and the row stack `game/scripts/pp_title/pp_title.gml`.

### How a dialogue entry becomes pages

Two data shapes, and they behave differently `game/scripts/pp_dialogue/pp_dialogue.gml`:

- `pages`: 1 to 3 authored pages of 1 to 3 lines, taken as written
  `game/scripts/pp_dialogue/pp_dialogue.gml`. If wrapping makes an authored page taller than 3 rows it is re-chunked
  into more pages, so the authored break is not sacred `game/scripts/pp_dialogue/pp_dialogue.gml`.
- `lines` (shorthand): **one source line is one page** `game/scripts/pp_dialogue/pp_dialogue.gml`. A line that wraps to
  4 rows becomes 2 pages and a line of 1 row is a page of 1 row
  `game/scripts/pp_dialogue/pp_dialogue.gml`. The checker caps an entry at 9 lines and a page set at 3
  `specs/05-dialogue.md`. So a 9 line entry is 9 confirms, not the 3 pages of 3 that rule 4 describes
  `specs/05-dialogue.md`. The runtime has no page cap of its own; the checker is the only gate
  `specs/05-dialogue.md`.

---

## 5. Confirm, halt and skip, per surface

| surface | holding confirm | tapping confirm while typing | tapping confirm when the unit is full | advances alone |
| --- | --- | --- | --- | --- |
| dialogue box | fast, 1 step a character | fills the page, does not advance | turns the page, or closes | no |
| battle board | fast | fills the line and moves to the next line in one press | closes the board | yes, 8 steps after each line but the last |
| talk reply block | fast | same as the battle board | same | same |
| intro crawl | no effect | jumps the whole crawl to its last beat | same | yes, one beat |

Sources for that table: `game/scripts/pp_dialogue/pp_dialogue.gml` for the box,
`game/scripts/pp_battle_director/pp_battle_director.gml` for the board, and
`game/scripts/pp_title/pp_title.gml` for the crawl. The dialogue box is the one that matches
`specs/05-dialogue.md` acceptance 2: confirm mid line completes it and does not advance twice
`specs/05-dialogue.md`. The board does not, and that is divergence 3 in section 9
`game/scripts/pp_battle_text/pp_battle_text.gml`.

---

## 6. The menu primitives

### What exists

One helper: `pp_menu_axis(negative, positive)` in `game/scripts/pp_input/pp_input.gml`. It returns -1, 0 or 1 on the
step the player moves, using `pp_pressed` or `pp_repeat`, and returns 0 when both directions are down on the same step
`game/scripts/pp_input/pp_input.gml`. Four of the five surfaces call it `game/scripts/pp_input/pp_input.gml`.

### The five surfaces

| surface | cursor | draw | sound on move | disabled rows |
| --- | --- | --- | --- | --- |
| battle command menu | `pp_command_move`, `game/scripts/pp_battle_commands/pp_battle_commands.gml` | `pp_battle_draw_menu`, `game/scripts/pp_battle_director/pp_battle_director.gml` | none | struck through, reason printed for 30 steps |
| talk options | inline in `pp_talk_step`, `game/scripts/pp_battle_text/pp_battle_text.gml` | `pp_talk_draw_options`, `game/scripts/pp_battle_text/pp_battle_text.gml` | `menu_move` | not applicable |
| dialogue choices | `pp_dialogue_move_cursor`, `game/scripts/pp_dialogue/pp_dialogue.gml` | inline in `pp_dialogue_draw`, `game/scripts/pp_dialogue/pp_dialogue.gml` | none | none |
| title menu | inline in `pp_title_step`, `game/scripts/pp_title/pp_title.gml` | inline in the title draw, `game/scripts/pp_title/pp_title.gml` | `menu_move` | CONTINUE struck through when there is no save |
| game over card | inline in `pp_battle_step_gameover`, `game/scripts/pp_battle_director/pp_battle_director.gml` | `pp_battle_draw_gameover`, `game/scripts/pp_battle_director/pp_battle_director.gml` | `menu_move` | CONTINUE struck through, note printed for 90 steps |

Every one of them moves with the same arithmetic, `(cursor + dir + count) mod count`, written five times
`game/scripts/pp_battle_director/pp_battle_director.gml`. Every one of them draws its own rows, its own cursor and its
own disabled mark, written five times `game/scripts/pp_battle_director/pp_battle_director.gml`. That is the menu face
of the same defect as section 7, and `knowledge/FOX-STYLE-AUDIT.md` section 3c already records it as a declared gap
`knowledge/FOX-STYLE-AUDIT.md`.

### The shapes

- Battle command menu: five rows from `pp_command_table` in two columns at x 24 and x 128, first row y 176, a 20 pixel
  row pitch `game/scripts/pp_battle_director/pp_battle_director.gml`. The cursor is a triangle at x 14
  `game/scripts/pp_battle_director/pp_battle_director.gml`. A refused entry is struck through and never skipped by the
  cursor, so the player can always see why `game/scripts/pp_battle_director/pp_battle_director.gml`. The reason
  sentence is drawn at y 224, wrapped to 28 columns, for 30 steps
  `game/scripts/pp_battle_director/pp_battle_director.gml`.
- Talk options: three rows at x 24, y 178, 194 and 210, a 16 pixel pitch, cursor triangle at x 14, and the prompt
  `* WHAT DO YOU SAY?` in the message window above them `game/scripts/pp_battle_text/pp_battle_text.gml`.
- Dialogue choices: up to 3 rows at y 176, 186 and 196 inside the text area, a 6 by 6 cursor block, 12 character labels
  `game/scripts/pp_dialogue/pp_dialogue.gml`.
- Title: rows centred at x 128, from y 156 on a 12 pixel pitch, cursor sprite at x 64 with two frames on a 14 step
  period `game/scripts/pp_title/pp_title.gml`. When the cursor art is missing the row is simply not marked
  `game/scripts/pp_title/pp_title.gml`.
- Game over: two rows, CONTINUE and RETURN TO TITLE, at y 132 and 148, cursor a 2 pixel rule under the label blinking
  every 15 steps `game/scripts/pp_battle_director/pp_battle_director.gml`. The refusal sentence sits on the black band
  at y 182 for 90 steps `game/scripts/pp_battle_director/pp_battle_director.gml`.

### The rule the menus are missing

`knowledge/FOX-STYLE.md` section 8 names one module with `define(rows)`, `move`, `confirm`, `back`, `draw`, a
`selection` array indexed by depth, and row kinds `action, group, value, disabled` `knowledge/FOX-STYLE.md`. None of
that exists: there is no `pp_menu` script anywhere under `game/scripts/` `game/scripts/pp_battle_director/pp_battle_director.gml`.
The audit deferred extraction while the game had one menu and set the trigger at the second menu
`knowledge/FOX-STYLE-AUDIT.md`. There are now five, so the trigger has fired and the extraction has not happened
`knowledge/FOX-STYLE-AUDIT.md`. The cost to a designer today: adding one row means editing a draw function and a cursor
loop in a module that owns something else, and the sixth menu will be the sixth copy
`knowledge/FOX-STYLE-AUDIT.md`.

---

## 7. The named defect, and exactly what must be deleted

### The defect as named

`knowledge/FOX-STYLE-AUDIT.md` section 3a, "Two typewriter implementations (law 8, real violation)": `pp_dialogue` had
its own reveal loop (items, wait accumulation, punctuation pauses, advance, closed) and its own draw, and
`pp_battle_text` had a separate one (`pp_text_board_step`, `pp_text_board_skip_line`, `pp_text_board_done`) with a
`draw_text_ext` draw `knowledge/FOX-STYLE-AUDIT.md`. Two implementations of one presentation is exactly what law 8 and
section 7 forbid `knowledge/FOX-STYLE.md`.

### What is true now

The typing half of that defect is closed, by card TEXT-REVEAL-1, status DONE `knowledge/CARD-MAP.md`, provenance entry
`knowledge/PROVENANCE.md`. Evidence read from the tree rather than assumed:

- `pp_dialogue.gml` contains no character clock: no assignment to `revealed`, `acc` or `wait`. Its step calls
  `pp_text_reveal_step`, and its advance calls `pp_text_reveal_complete` and `pp_text_reveal_next`
  `game/scripts/pp_dialogue/pp_dialogue.gml`.
- The board functions in `pp_battle_text` are four thin wrappers that delegate straight to `pp_text`
  `game/scripts/pp_battle_text/pp_battle_text.gml`.
- `pp_title.gml` does the same for the crawl `game/scripts/pp_title/pp_title.gml`.
- Every player facing glyph goes through `pp_font_draw`; the only `draw_text` left under `game/` is the debug overlay
  `game/objects/obj_pp_debug_overlay/Draw_64.gml`.

So the defect the task names is history on the reveal path. What survives is its layout half, and the deletions below
are all that is left.

### What must be deleted for one machine to remain

Three functions, all in `game/scripts/pp_battle_text/pp_battle_text.gml`, 44 lines in total by those ranges.

1. **`pp_talk_board_draw`, `game/scripts/pp_battle_text/pp_battle_text.gml:569` to `583`. Delete it.** It is the
   second draw of the same board: the same unit walk, the same `pp_text_visible` call, differing only in a pitch of 8
   against 10, wrapping against not wrapping, and a 4 line cap `game/scripts/pp_battle_text/pp_battle_text.gml`. Two
   numbers, one boolean and one cap are the same class of difference that speed, gap and blip already are on the
   machine `game/scripts/pp_text/pp_text.gml`. Give `pp_text_board_draw` a pitch and a wrap flag, and the call site at
   `game/scripts/pp_battle_director/pp_battle_director.gml:967` to `972` becomes one call with different arguments
   `game/scripts/pp_battle_director/pp_battle_director.gml`.
2. **`pp_talk_wrap`, `game/scripts/pp_battle_text/pp_battle_text.gml:370` to `388`. Delete it.** It is a third greedy
   word fill with the same rule `pp_font_wrap` already implements, plus a cap at 4 rows
   `game/scripts/pp_font/pp_font.gml`. Keep the cap at the call site through `pp_talk_lines_max` and call
   `pp_font_wrap` `game/scripts/pp_battle_text/pp_battle_text.gml`.
3. **`pp_talk_cut`, `game/scripts/pp_battle_text/pp_battle_text.gml:144` to `153`. Delete it** and move the
   cut-at-the-last-space rule into `game/scripts/pp_font/pp_font.gml` beside `pp_font_wrap`
   `game/scripts/pp_font/pp_font.gml`. A text rule that lives in the battle module is how the third copy starts
   `game/scripts/pp_battle_text/pp_battle_text.gml`. Two callers use it: `pp_talk_reply_clean` and
   `pp_talk_option_label` `game/scripts/pp_battle_text/pp_battle_text.gml`.

**Do not delete `pp_dialogue_rows`** `game/scripts/pp_dialogue/pp_dialogue.gml:14` to `77`. It looks like a fourth
wrapper and it is not: it is the only one that keeps each character's own `wait` and `speed` attached to it and appends
the pause item to the row, which is what makes a `{pause:N}` survive a line break
`game/scripts/pp_dialogue/pp_dialogue.gml`. Its greedy fill should be expressed through one shared rule, but the item
mapping belongs to the dialogue layout `game/scripts/pp_dialogue/pp_dialogue.gml`.

Nothing on the reveal path itself is left to delete `game/scripts/pp_text/pp_text.gml`. What would recreate the defect
is a layout writing `revealed`, and the one place that comes close is `game/scripts/pp_scene/pp_scene.gml:431` to `436`,
where the scene's autoplay path reads `reveal.revealed` and `pp_text_unit_length` to choose between pick and advance
instead of asking the box `game/scripts/pp_scene/pp_scene.gml`. The overworld path is the conforming one: it calls
`pp_dialogue_advance` and `pp_dialogue_step` and touches no field `game/scripts/pp_dialogue/pp_dialogue.gml`.

---

## 8. Where the code conforms

- `pp_text` is one machine for all three layouts, with no field a layout also keeps
  `game/scripts/pp_text/pp_text.gml`.
- Punctuation pauses are owned by the writer and never authored in content
  `game/scripts/pp_text/pp_text.gml`.
- An unknown brace code is reported rather than ignored `game/scripts/pp_text/pp_text.gml`.
- Frame timing is authored in frames and converted once: the crawl's seconds become steps in one function
  `game/scripts/pp_title/pp_title.gml`.
- The auto versus confirm difference is a boolean plus a gap on one machine, not a second revealer
  `game/scripts/pp_text/pp_text.gml`.
- `pp_menu_axis` is one edge triggered axis helper with key repeat, used by four surfaces
  `game/scripts/pp_input/pp_input.gml`.
- A disabled row is marked by a rule through it, not by a tint, which the one ink font sheet requires
  `game/scripts/pp_font/pp_font.gml`.
- The choice panel replaces its rows instead of painting over them, and the spec's acceptance 6 depends on that
  `specs/05-dialogue.md`.

## 9. Where it diverges

1. **No `pp_menu` (law 8, section 8).** Five cursor loops and five draws, listed in section 6; the audit's trigger for
   extraction has passed `knowledge/FOX-STYLE-AUDIT.md`. This is the largest open item in this node
   `game/scripts/pp_battle_director/pp_battle_director.gml`.
2. **The battle command menu is silent.** Moving the cursor plays nothing, while the talk panel, the title and the game
   over card all play `menu_move` `game/scripts/pp_battle_director/pp_battle_director.gml`. A refused confirm sets the
   note and returns with no sound at all, which contradicts spec 07 rule 1 and acceptance 3
   `specs/07-battle-director.md`.
3. **The board's confirm does two things in one press.** `pp_battle_step_message` calls `pp_text_board_skip_line`,
   which completes the line and calls `pp_text_reveal_next` in the same call
   `game/scripts/pp_battle_text/pp_battle_text.gml`. The player never sees the completed line, because the next line
   starts empty instead `specs/05-dialogue.md`.
4. **The board clears in the same frame its last character appears.** `pp_text_reveal_step` sets `done` inside the
   frame that reveals the final character, and `pp_battle_after_message` then sets `messages` to undefined
   `game/scripts/pp_battle_director/pp_battle_director.gml`. The draw block only runs while `messages` is defined, so
   the last glyph of a board may never be drawn `game/scripts/pp_battle_director/pp_battle_director.gml`. Read from the
   source; not observed in a running build.
5. **The final hold is discarded.** A hold is added when the character is revealed, and the end of unit check in the
   same step sets `done`, so a full stop at the very end of the text holds nothing
   `game/scripts/pp_text/pp_text.gml`. Every other punctuation mark holds `game/scripts/pp_text/pp_text.gml`.
6. **`revealed` counts items, not glyphs** `game/scripts/pp_text/pp_text.gml`. A `{pause:N}` shifts the blip phase and
   the visible budget by one, and it also takes a cell of the 28 cell row `game/scripts/pp_dialogue/pp_dialogue.gml`.
7. **The spoken marker is prose, not writer state.** Section 7 says the marker is `marker` on the writer, and no such
   field exists `knowledge/FOX-STYLE.md`. The `* ` is written into data and into code strings and then stripped back
   off for a menu label `data/dialogue/all.json`. The glyph exists, so this is a doctrine gap rather than a rendering
   fault `game/scripts/pp_font/pp_font.gml`.
8. **A stale claim about the asterisk.** The game over draw says the sheet has no glyph for one, twice, while the sheet
   lists `*` among its glyphs `game/scripts/pp_font/pp_font.gml`. One of the two is wrong and a reader cannot tell
   which `game/scripts/pp_battle_director/pp_battle_director.gml`.
9. **The choice panel does not repeat.** It reads `pp_pressed("up")` and `pp_pressed("down")` directly rather than
   `pp_menu_axis`, so a held direction moves one row `game/scripts/pp_dialogue/pp_dialogue.gml`. That matches spec 05's
   "moves one per press", so it is not a fault, but it feels different from the other four menus and will stay
   different until the panel is a shared list `specs/05-dialogue.md`.
10. **`pp_battle_text` is mostly not a layout.** Of its 709 lines, the board is lines 11 to 61. The rest is the baked
    talk loader, the effect and mercy tables, the option list, the reply block, the NPC voices and a hash
    `game/scripts/pp_battle_text/pp_battle_text.gml`. Law 1 says the talk domain does not belong in the text module, and
    the module's own header claim is crossed by about 600 lines `knowledge/FOX-STYLE.md`.
11. **The board's second draw survives.** `pp_talk_board_draw` is the duplicate named in section 7 and is still in the
    tree `game/scripts/pp_battle_text/pp_battle_text.gml`.

---

## 10. Unmeasured here

- The blip's pitch and its gain. The cue is chosen per speaker, and the frequencies live in `data/audio.json`, which
  this node did not read: unmeasured `game/scripts/pp_text/pp_text.gml`.
- The audible and visible result of a character the sheet lacks. `pp_font_draw` draws it as a space and advances the
  cursor, and `tools/check_font_coverage.py` is meant to refuse such content before the build
  `game/scripts/pp_font/pp_font.gml`.
- Wall clock per dialogue page. Not a constant: the machine's worst case is arithmetic over section 3, and the
  player's own pace is not: unmeasured `game/scripts/pp_text/pp_text.gml`.
- Whether divergence 4, the missing last glyph, is visible in a running build. No capture in the tree shows the end of
  a board: unmeasured `game/scripts/pp_battle_director/pp_battle_director.gml`.
