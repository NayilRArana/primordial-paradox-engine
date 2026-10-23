# Spec 05: dialogue

Status: spec, 2026-10-19, amended 2026-10-23 to the shipped D2 shape, and again to the choice layout (card
t_01432e14). Numbers are DECISIONS.

Goal: a text box at the bottom of the frame, typewriter text with a blip, word wrap, and a short choice list. Confirm
completes a line, then advances. Holding confirm speeds text up.

Geometry
- Box 240x64 at (8, 168): 2 pixel frame, 1 pixel dark outer line, drawn over the scene.
- Portrait: a 48x48 bust at (16, 120), at most 4 colours from `data/nes_palette.json` and at most 3 in any 8x8 tile,
  with its 1 pixel frame drawn into the sheet. 120 + 48 = 168, which is the box's own top edge, so the bust stands on
  the box and covers none of it. It never takes a column of the text area: a 48 pixel column inside the box would cost
  6 of the 28 characters, which is the reason the 28 ruling exists. 16 is the text area's own inset, so the bust and the
  first row of text start on one line, and 48 pixels of bust is 36 sprite tiles, six to a scanline, inside the PPU's
  eight sprites a scanline and 64 in OAM. The sheet is `spr_pp_portrait_<name>`, on the same one sheet index as the
  window and the font (`pp_art_info`), so the bust draws through the box's own path and a page with no sheet draws
  nothing rather than a frame with nothing in it (card t_4d6b0f4b).
- Name plate 64x12 over the left of the top border, at x 12 without a bust and at x 68 with one, because the bust's 48
  pixels end at 63 and the plate is the one other thing on that border: 68 keeps them from sharing a pixel, and the
  text area is untouched either way.
- Text area x 16 to 240, y 176 to 224: our own 8x8 font, 28 characters per line, 3 lines per page. 16 + 28 * 8 = 240,
  so a full line ends exactly on the text area's right edge and 8 pixels short of the box's 248. The box is 240 wide,
  so 30 characters cannot fit at 8 pixels a glyph from any inset: 30 characters would end at x 256.
- Choices take the rows' place. On a page that offers choices, once that page has finished typing, its three rows are
  replaced by one row per choice, in the same three 10 pixel rows: the cursor is a 6x6 block at x 16 (column 0 of the
  text area) and the label starts at x 24 (column 1), so 27 columns fit from x 24 to 240 and no choice glyph is ever
  drawn over a line of dialogue. Nothing is painted over anything: the rows are not drawn at all while the labels are
  up. A label is at most 12 characters, a DECISION rather than a geometry limit: it keeps three options readable as a
  list, and the row itself has room for 27.
  Why this and not the alternatives (ruling of card t_01432e14, option a): there are 8 pixels between the third row's
  cell and the box's bottom edge and the panel needs 3 rows of 10, so it cannot be moved inside the box; making the
  question a header row of the panel still leaves the panel over the prompt rows and needs every choice page
  re-authored; narrowing the prompt rows to 15 columns moves authored dialogue and caps a choice page at two rows. The
  cost here is deliberate and it is the only cost: the question is not on screen while the three labels are, and it
  was the line the player had just confirmed.
- Optional name plate 64x12 over the left of the top border.
- Indicator 6x6 triangle at (236, 222), 15 steps on, 15 off.

Text rules
1. 2 steps per character (30 per second); fast forward 3x, floor 1 step per character.
2. Pause 8 steps after a full stop, question or exclamation; 3 after a comma. A source line break waits for confirm.
3. Blip every 3 characters, never on spaces, pitch fixed per speaker from a speaker table.
4. Wrap by word; a word that does not fit moves whole to the next line; over 3 lines becomes another page and the
   indicator becomes a page arrow. A page holds 3 lines and an entry holds 3 pages, so a beat longer than 9 lines is
   two dialogue entries, not one longer entry (ARRIVAL-CONTENT beat 20 is four pages on paper and ships as
   `quay_gate_checkpoint` then `quay_gate_choice`).
5. Two control codes only: `{pause:N}` and `{speed:N}`. A line that cannot fit within the box is a checker error, not a
   runtime truncation.
6. Only two inks: text and highlight. No rich colour tags.

Choices: 1 to 3, carried by the entry and shown after its last page, in the rows' place (a choice page replaces its
three text rows, one row per choice); 6 pixel arrow cursor in column 0, moves one per press and wraps. A choice is
`label` (at most 12 characters), `sets` (one or more flag names) and an optional `goto` (another dialogue id). Picking
one applies every flag in `sets` and then either continues at `goto` or closes the box. There is no `condition` field
and no `choice` scene command: an option that appears only under a condition is a `branch` in the scene on a flag an
earlier entry set (D2 item 4, spec 06 rule 3).

Data: a dialogue has `id`, `speaker` and exactly one of `lines` or `pages`, plus optional entry `sets` and optional
`choices`.
- `lines` is the one page shorthand, 1 to 9 lines. The checker wraps it by word, so only a WORD longer than 28
  characters is refused; a long sentence is legal shorthand and wraps on the screen.
- `pages` is the pre-broken shape: 1 to 3 pages, each page 1 to 3 lines, each line at most 28 characters. A page line
  is already one row of the box, so 29 characters is refused rather than wrapped. A page may name its own `speaker`,
  which is how a mixed scene keeps the right name plate; without it the entry's `speaker` is used (`narrator` is the
  no name case).
- `portrait` names the bust, on an entry or on a page exactly the way `speaker` does, and the page's own value replaces
  the entry's. The empty string is legal and means "nobody", which is how a page inside a bust carrying entry keeps the
  frame clear, and `narrator` never carries one. `tools/check_data.py` proves the name matches a real sheet
  (`game/sprites_src/chars/spr_pp_portrait_<name>.png`) and refuses a narrator with a bust, so a typo is a data error
  and not a portrait that silently never appears.
- `sets` on an entry names flags applied when the box closes. A `choice` names `label`, `sets` and optional `goto`.
All ids are strings, every flag is a name in `data/flags.json`, and the checker proves each one exists.

PP content: every story beat, including Prometheus on the veil, Percy's pre fight speech, the Atlas variant of the
prison scene, the Kronos ending and the Ouranos post credits scene, plus battle TALK options.

Acceptance (Nayil)
1. A long dialogue wraps by word, never mid word, and the box never grows.
2. Confirm mid line completes it and does not advance twice.
3. Holding confirm gives about 3x speed with no skipped pages.
4. The cursor wraps in the choice panel; picking an option applies every flag in its `sets` before the box moves, then
   follows `goto` when it has one and closes when it has none.
5. A 29 character page line in data is refused by the checker with the dialogue id and the line index named, and a
   fourth page is refused the same way; a 28 character page line passes.
6. A page that offers choices never shows a label over a line of dialogue: the rows are replaced by the labels, not
   covered by them, and a cursor cell and a label cell never share a cell with a row.
7. A page that names a bust draws that 48x48 sheet at (16, 120), standing on the box: the last row of the sheet is
   y 167 and the box starts at y 168, no pixel of the text area is covered, and the name plate moves to x 68 so the
   plate and the bust never share a pixel. A page with no bust draws none, and a page whose sheet is missing draws
   nothing at all rather than an empty frame.

Out of scope: voice, per character sounds beyond blips, localisation, and animation of a bust (a bust is one frame; a
second expression is a second sheet and a data change, not a runtime feature).
