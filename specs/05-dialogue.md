# Spec 05: dialogue

Status: spec, 2026-10-19, amended 2026-10-23 to the shipped D2 shape. Numbers are DECISIONS.

Goal: a text box at the bottom of the frame, a portrait, typewriter text with a blip, word wrap, and a short choice
list. Confirm completes a line, then advances. Holding confirm speeds text up.

Geometry
- Box 240x64 at (8, 168): 2 pixel frame, 1 pixel dark outer line, drawn over the scene.
- Portrait 48x48 at (16, 120), a bust standing on the box's top edge, 1 pixel frame, at most 4 colours. It does not
  take a column of the text area: a 48 pixel column would cost 7 of the 28 characters a row. No speaker in the slice
  carries a portrait, so nothing is drawn there yet.
- Text area x 16 to 240, y 176 to 224: our own 8x8 font, 28 characters per line, 3 lines per page. 16 + 28 * 8 = 240,
  so a full line ends exactly on the text area's right edge and 8 pixels short of the box's 248. The box is 240 wide,
  so 30 characters cannot fit at 8 pixels a glyph from any inset: 30 characters would end at x 256.
- Choice panel 96 pixels wide, right aligned inside the text area, so a label is at most 12 characters at 8 pixels a
  glyph. No third column, no scrolling: the panel is exactly as wide as a full label.
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

Choices: 1 to 3, carried by the entry and shown after its last page, in the 96 pixel panel; 6 pixel arrow cursor, moves
one per press and wraps. A choice is `label` (at most 12 characters), `sets` (one or more flag names) and an optional
`goto` (another dialogue id). Picking one applies every flag in `sets` and then either continues at `goto` or closes the
box. There is no `condition` field and no `choice` scene command: an option that appears only under a condition is a
`branch` in the scene on a flag an earlier entry set (D2 item 4, spec 06 rule 3).

Data: a dialogue has `id`, `speaker` and exactly one of `lines` or `pages`, plus optional entry `sets` and optional
`choices`.
- `lines` is the one page shorthand, 1 to 9 lines. The checker wraps it by word, so only a WORD longer than 28
  characters is refused; a long sentence is legal shorthand and wraps on the screen.
- `pages` is the pre-broken shape: 1 to 3 pages, each page 1 to 3 lines, each line at most 28 characters. A page line
  is already one row of the box, so 29 characters is refused rather than wrapped. A page may name its own `speaker`,
  which is how a mixed scene keeps the right name plate; without it the entry's `speaker` is used (`narrator` is the
  no name case).
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

Out of scope: voice, per character sounds beyond blips, localisation.
