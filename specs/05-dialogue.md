# Spec 05: dialogue

Status: spec, 2026-10-19. No code yet. Numbers are DECISIONS.

Goal: a text box at the bottom of the frame, a portrait, typewriter text with a blip, word wrap, and a short choice
list. Confirm completes a line, then advances. Holding confirm speeds text up.

Geometry
- Box 240x64 at (8, 168): 2 pixel frame, 1 pixel dark outer line, drawn over the scene.
- Portrait 48x48 at (16, 176), 1 pixel frame, at most 4 colours.
- Text area x 72 to 240, y 176 to 224: our own 8x8 font, 30 characters per line, 3 lines per page.
- Optional name plate 64x12 over the left of the top border.
- Indicator 6x6 triangle at (236, 222), 15 steps on, 15 off.

Text rules
1. 2 steps per character (30 per second); fast forward 3x, floor 1 step per character.
2. Pause 8 steps after a full stop, question or exclamation; 3 after a comma. A source line break waits for confirm.
3. Blip every 3 characters, never on spaces, pitch fixed per speaker from a speaker table.
4. Wrap by word; a word that does not fit moves whole to the next line; over 3 lines becomes another page and the
   indicator becomes a page arrow.
5. Two control codes only: `{pause:N}` and `{speed:N}`. A line that cannot fit within the box is a checker error, not a
   runtime truncation.
6. Only two inks: text and highlight. No rich colour tags.

Choices: up to 4, in a 96 pixel panel right aligned inside the text area; 6 pixel arrow cursor, moves one per press and
wraps; an option with a `condition` flag stays hidden until the ledger says true, which is how TALK options unlock
(spec 08). Picking returns the choice id and keeps the box open for a reply line.

Data: a dialogue has id, speaker, portrait, pages, optional choices; a choice has id, label, optional condition, and a
target dialogue id or scene effect. All ids are strings and the checker proves each one exists.

PP content: every story beat, including Prometheus on the veil, Percy's pre fight speech, the Atlas variant of the
prison scene, the Kronos ending and the Ouranos post credits scene, plus battle TALK options.

Acceptance (Nayil)
1. A long dialogue wraps by word, never mid word, and the box never grows.
2. Confirm mid line completes it and does not advance twice.
3. Holding confirm gives about 3x speed with no skipped pages.
4. The cursor wraps in the choice panel, and a conditional option appears only after its flag is set.
5. A 40 character line in data is refused by the checker with the dialogue id named.

Out of scope: voice, per character sounds beyond blips, localisation.
