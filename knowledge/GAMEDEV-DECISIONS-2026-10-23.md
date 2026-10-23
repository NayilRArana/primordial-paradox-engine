# Gamedev decisions, 2026-10-23

Card t_22ec36f7 (GAME-ROADMAP-3), gamedev, head of build. Written 2026-10-23 00:20 to 00:40 PDT.
Authority: this file rules the questions the board could not settle on 2026-10-22 night. It sits beside
`knowledge/GAMEDEV-DECISIONS-2026-10-22.md` and never contradicts it; where it extends that file, it says so.
A card that disagrees with this file is wrong, not this file.

---

## D1. flags.json: R22 appends the five names, ARRIVAL-MAP-2 reads them

The cycle, stated exactly as the blocked card reported it: R22 DIALOGUE-V2 (t_5b27880e) needs `gate_passed`,
`gate_truth`, `gate_bluff`, `gate_authority` to exist in `data/flags.json` before a choice can set one. D3 of
2026-10-22 gave that file's ownership to ARRIVAL-MAP-2 (t_db2995d7). ARRIVAL-MAP-2 is a child of R22 and its own check
needs the gate entries R22 writes. Neither can start first.

Ruling, option (a) from the card's own list, because it is the only one that needs no graph edit:

1. **R22 appends exactly five names to `data/flags.json`, in D3's order, after `kronos_spared`**:
   `gate_passed`, `gate_truth`, `gate_bluff`, `gate_authority`, `has_boarding_pass`.
2. **ARRIVAL-MAP-2 no longer writes `data/flags.json`.** Its scope drops that one file and keeps `data/maps/all.json`,
   `data/scenes/all.json` and `data/room_palettes.json`. It may read the flags file and must find all five already
   there.
3. Why this cannot lose work: the file is append only, the five names are fixed strings, R22 runs first, and a second
   append of the same five would be a checker error rather than a silent duplicate. There is no version of this where a
   row disappears.
4. `data/flags.json` writer order for the whole slice: **R22, and nobody else.** Any later card that wants a flag posts
   `Q: for gamedev` and gamedev edits the file itself. Fourteen flags against a budget of 200.

## D2. The two dialogue test files: R22 keeps the schema pins, R31 owns the behaviour test

R22 wrote `tests/test_dialogue_v2.py` and `tests/test_schemas.py` because its own check demanded a green suite, and both
paths are somebody else's or nobody's.

1. `tests/test_schemas.py` stays **R22's** in this batch. It holds the schema pins that stop the schema and the checker
   drifting apart, and the schema moves with the checker inside R22. No other card edits it.
2. `tests/test_dialogue_v2.py` is **R31's** (t_45ef4217). R31 may rewrite it line for line. Its one obligation: it must
   keep at least one assertion that the schema file and `tools/check_data.py` agree, so D2 of 2026-10-22 stays enforced
   after the rewrite.
3. Write order: R31 never touches the file before R22's commit is in. The board link already enforces it.

## D3. R21 exists from today: the drive scene is a card, not a promise

`knowledge/DRIVE-SHOT-LIST.md` landed (t_9b2e63d2) with twelve shots, 178 seconds and 10,680 steps. The audit scores the
drive scene at 1 of 4 and R32 names `drive_to_southampton` as one of its four red steps.

Ruling: **R21 is created on the board today** (t_3e9dd0f7 and its map sibling), lane builder, owning the drive block of
`data/scenes/all.json` plus the drive room if the runner needs one. It is gated on ARRIVAL-MAP-2 and SHIP-DECK-MAP so
that exactly one worker writes `data/scenes/all.json` at a time. Order for that file, final: **R22 (dialogue only, never
this file), ARRIVAL-MAP-2, SHIP-DECK-MAP, R21.** No exceptions, no parallel writers, and the board links are the queue.

## D4. G0-4 is split three ways and the old card is archived as superseded

G0-4 (t_2eb874af) timed out twice at 55 minutes carrying four build steps and five rituals. The manager comment already
asked for the split. Done, with the spec 18 answers carried into each child:

- **G0-4a** Percy's phases only: the `phases` list in the enemy shape, schema, checker, the director reading it, Percy at
  120 hp with the 70 percent and 49 percent cuts from spec 18 section 8. One file set, one check.
- **G0-4b** The Prometheus interruption scene only: the `interrupted` outcome, the `spare_refused` trigger (NOT an hp
  crossing, per A18-1), the scene, its dialogue, the `met_prometheus` flag. One scene, one dialogue entry.
- **G0-4c** Both endings only: `percy_win_spare`, `percy_win_kill`, `navy_win_spare`, `navy_win_kill` proven reachable,
  the epilogue sets, the spare refusal on the genocide route.

G0-4 itself moves to archived with the reason "superseded by G0-4a, G0-4b, G0-4c on 2026-10-23". Its body stays as the
record of what was asked, and each child cites it.

## D5. INTRO-1 is closed, not retried

INTRO-1 (t_d2ec48a1) asks for a pan up to the stars and a twinkle after NEW GAME. It is already done in the running
game: the audit scores the intro crawl 3 of 4 on `data/intro_text.json`, `data/intro_stars.json`, and the captures
`output/crawl_mid.png` (768x720, 4 colours) and `output/crawl_end.png`, plus the live log line "PP title: intro
finished, starting the run in rm_pp_ship".

Ruling: **close INTRO-1 as done by supersession.** Anything left in it that is not on screen becomes one small
refinement card (INTRO-POLISH), 20 minutes, owned by testing, with the capture as its check. No third retry of the
blocked card, because a card that has been overtaken by a landed feature is a stale record and not a blocker.

## D6. TS1-CODE is closed, superseded by the title path

TS1-CODE (t_90c0cc4a) asks for a working title screen with a menu proven by a captured run. That is the running game:
`tools/capture_title.py` returns exit 0 with score 1.000 at 19:13 on 2026-10-22, `output/title_run_1.png`, and the title
theme plays live. The manager already wrote "superseded by W1 (wiring) and W2 (capture harness). The logic you wrote in
pp_title.gml is kept."

Ruling: **close TS1-CODE as done by supersession.** What it uniquely still wants (CONTINUE dim with no save, NEW GAME
reaching the crawl) is R25 TITLE-PATH (t_136b5d08), which is a live card with a sharper check. Closing TS1-CODE does
not weaken R25 by one line.

## D7. R32 stays red and stays open, and it is the gate, not the gag

R32 (t_030a89e5) is correct: 16 of 24 assertions pass and the 8 failures name content four other cards own. A test that
reports red honestly is worth more than a test edited to look green.

Ruling: R32 is **blocked on dependency**, with R21, ARRIVAL-MAP-2, R22 and the slice save row as its named parents.
It is re-run, not rewritten, when they land. Its check stays exactly as written.

## D8. Budget, because credit ran out once

1. **At most 12 workers in flight at once**, across every lane, per the card's own budget line.
2. **At most 3 cards in flight per lane**, and the lane cap is about dispatcher attention, not only about files.
3. **Many small cards, 15 to 45 minutes.** A card that cannot be finished in 45 minutes gets split before it is
   dispatched, not after it times out twice.
4. **No card re-runs without a reason.** A retry names what changed: a fix landed, a blocker cleared, a compile time
   measured. "Try again" is not a reason.
5. A card that finds its work already done closes as superseded with the evidence, in one comment, and does not spend a
   second run.

## D9. Every automatic game launch is muted and idle gated

Any card that opens the game by itself calls it with sound muted and only after the machine is idle for two minutes,
and prints the `PP: muted` line its harness already supports. The negative control card is CAPTURE-QUIET (t_52166d5a)
and a capture that cannot show that line is not evidence.

## D10. The dialogue box's line is 28 characters, and its only text path is pp_font_draw

Card t_1d828fcd (DIALOGUE-FONT-WIRE), ruled from the audit card t_6469ef68's two measured defects: the box drew its
rows, name plate and choice labels with `draw_text` while the project holds no font resource at all, and `PP_TEXT_CHARS`
30 from x 72 ends at x 312 against a box that ends at 248. Five rulings, and the numbers they were decided from.

1. **Draw path: pp_font_draw, and not a font resource.** A sprite font asset would be one line, but `spr_pp_font8` is a
   sprite the NES checker audits as a sprite (74 frames, one ink, 8x8, no descender outside its cell), and a font
   resource is a different kind of thing that audit cannot see. One code path for text is worth more than one line.
   So `pp_dialogue_draw` now calls `pp_font_draw` three times, once for the rows, once for the name plate and once for
   the labels, and the module holds no `draw_text` at all.
2. **Columns: 28.** The box is 240 wide, so the inside is 224 pixels; at 8 pixels a glyph that is 28 characters and 30
   is arithmetically impossible from any inset (30 would end at x 256, past the frame). The text area moved from
   x 72 to x 16 so it uses the whole inside of the box, 8 pixels in from the frame on every side: 16 + 28 * 8 = 240.
   `PP_TEXT_CHARS`, `PP_TEXT_RIGHT` and `specs/05-dialogue.md` all state 28, `tools/check_data.py` reads the same
   number, and `tests/test_dialogue_v2.py::test_the_box_geometry_and_the_wrap_agree` recomputes the identity so the
   four cannot drift apart again.
3. **The portrait gives up its column.** A 48 pixel portrait inside the box costs 7 of the 28 characters, and the
   authored dialogue is written at 21 to 30 characters a row: measured at 21 columns, 40 of the 46 authored page lines
   wrap to a second row and every arrival page doubles. The portrait is now a bust above the box
   (`PP_PORTRAIT_X/Y` at 16, 120). No speaker in the slice carries a portrait, so nothing draws it, the dim placeholder
   rectangle inside the box is gone, and the portrait itself is a card of its own.
4. **Case: sentence case stays.** The sheet carries `a` to `z` because the data is sentence case and 62 of the 74
   frames are what the 111 printed strings use. The name plate still goes through `string_upper`, which costs no glyph.
5. **Four lines in `data/dialogue/all.json` were re-broken, and nothing else in the data moved.** At 28 columns only
   four authored page lines did not fit (`quay_dock_office` three, `quay_dock_office_pass` one), so those four lose at
   most two characters each and keep their meaning; every other entry is byte for byte what it was, and no id, scene
   command, flag or page count changed. The alternative, lowering `LINE_CHARS` to 21, was measured and refused: it
   would have needed every arrival entry re-paged and the 3 page cap raised.

---

## D11. BATTLE-FONT-WIRE: the sheet's one ink gets marks, and the wrap is one function

Card t_7eb8835f, written after D10 moved the dialogue box onto `pp_font_draw` and left 34 sites on the GameMaker
default font. Seven rulings, each with the number it came from.

1. **Every screen prints through pp_font_draw, and the tree holds no text call outside a comment except the debug
   overlay.** The 34 sites were pp_app (10), pp_battle_director (12), pp_battle_text (6), pp_dodge_arena (2),
   pp_overworld (1) and pp_save (1), plus pp_font's own sanctioned call. All of them now draw the sheet.
   `game/objects/obj_pp_debug_overlay/Draw_64.gml` keeps `draw_text` on purpose: it is a developer dump drawn in Draw
   GUI space at the window's own scale, not a screen a player sees, and `tests/test_battle_font.py` pins it by name so
   converting it later turns the test red on purpose rather than silently.
2. **The wrap is a column count, in pp_font, once.** The default font wrapped at a pixel width; the sheet's cell is
   8 px, so `pp_font_cols(pixels)`, `pp_font_wrap(text, columns)`, `pp_font_draw_wrapped` and
   `pp_font_draw_wrapped_centre` are now the one wrap. `draw_text_ext(..., 10, PP_FRAME_W - 32)` became
   `pp_font_cols(PP_FRAME_W - 32)`, which is 28 columns from x 16 to x 240, the same row the dialogue box uses.
   `pp_text_board_draw` advances by the rows a line actually took, so two long lines can no longer print over each
   other. `pp_talk_wrap` in pp_battle_text stays: it is the talk loader's own step (four rows at most, cut at the last
   space through `pp_talk_cut`), it predates this card, and merging it into the font's wrap would change what the
   loader accepts. That merge is a follow up.
3. **The sheet stays 74 glyphs, so the HP line says OF rather than a slash.** `spr_pp_font8` has no `/`, and adding
   one touches the rasteriser's GLYPHS, `data/ui_layouts.json`'s copy, the generated `make_ui_nes.py` copy, the sheet
   PNG and its sidecar, and four frame-count assertions (74 frames, 592x8, "74 tiles"). That is an art card, not a
   screen card, so the battle line reads `HP 12 OF 12   WILL 5 OF 5` (25 characters, x 16 to x 216) until the sheet
   grows the glyph. Carded. **Superseded by D13**: the sheet grew the slash and the two brackets, so the line reads
   `HP 12/12   WILL 5/5` from card t_f476435e on.
4. **One ink: a state is a mark or a place, never a tint.** The sheet is `#f8f8f8` and a tint is a multiply no PPU can
   output (font contract rule 6). So: a refused command or game over row is ruled through with
   `pp_font_draw_struck` (the same idiom `pp_title_draw_disabled` already used); the game over row the cursor is on
   carries a 2 px rule under it, because a 6 px arrow at `_x - 12` would sit outside the card for `RETURN TO TITLE`
   (15 glyphs = 120 of the card's 124 inner pixels); the talk hint is marked by its own row under the block; and the
   damage number and the arena's `clear` line sit on `pp_font_draw_plated_centre`'s plate of the room's ink, because
   the enemy block is filled with the light role and white on `#c8c8d4` is unreadable.
5. **The game over sentence moved under the card, and the card did not move.** At 8 px the card's inner rectangle
   (x 66 to x 190) holds 15 glyphs, and the three refusal sentences are 27 to 30 characters, so two rows of them
   cannot sit between the rows at y 148 and the card's bottom at y 174. The sentence is now one row at 30 columns on
   the black band under the card, y 182, still inside the frame and clear of the card's edge at y 177. The card's own
   rectangles are the numbers they were, and `tools/preview_battle_font.py` refuses if they ever disagree with
   `pp_battle_draw_gameover`'s source.
6. **The refusal note moved up 4 pixels.** It was drawn at `PP_FRAME_H - 20` (220), which crosses the third command
   row at 216 once a glyph is 8 px tall; at `PP_FRAME_H - 16` (224) its cell ends on 231, under the labels and inside
   the band's border at 232.
7. **Every character the battle screens print is a frame of the sheet, checked by test.** The checker
   `tools/check_font_coverage.py` reads the data files and not the literals in GML, so
   `tests/test_battle_font.py::test_the_battle_screens_print_no_character_the_sheet_lacks` reads the command labels,
   the game over rows, the refusal reasons and the fixed strings out of the source and proves every character is in
   the sheet's glyph set. Extending the checker to GML literals generally is still carded; the one GML site that
   composes a path (`Data problem: ` plus `dialogue/all.json`) stopped printing a hole when the sheet grew a slash in
   D13, and `tests/test_battle_font.py` now reads the two composed sites it can name.

---

## D12. The choice labels take the rows' place, and the box draws no portrait

Card t_01432e14, the follow up D10 created. Two defects, one ruling each, and both were measured before they were ruled
on.

1. **The choice panel is gone; the labels take the rows' place.** Measured with `tools/preview_dialogue_box.py`: the
   panel sat at x 140..240 over prompt rows whose ink ended at x 183, 167 and 191, so 5, 3 and 6 characters of the
   three rows were covered and each row was cut mid phrase. It could not be moved inside the box, because there are 8
   pixels between the third row's cell and the box's bottom edge and the panel needed 3 rows of 10. Of the three
   options on the card, ruling: option (a). Once the last page has finished typing, its three rows are not drawn at all
   and the labels are drawn in them: the 6x6 cursor at `PP_CHOICE_ARROW_X` 16 (column 0) and the label at
   `PP_CHOICE_LABEL_X` 24 (column 1), so 24 + 27 * 8 = 240 and nothing shares a pixel. The cost is stated in the spec
   rather than hidden: the question is not on screen while the three labels are, and it was the line the player had
   just confirmed. Options (b) and (c) were refused because (b) still leaves a panel over the prompt rows and needs
   every choice page re-authored, and (c) moves authored dialogue and caps a choice page at two rows.
2. **The portrait is out of the slice, and its macros are gone.** Spec 05 promised a 48x48 bust at (16, 120) while no
   speaker carried one and `pp_dialogue_draw` had no portrait branch, so spec and code disagreed about a frame that
   never drew. `PP_PORTRAIT_X`, `PP_PORTRAIT_Y` and `PP_PORTRAIT_SIZE` are deleted from `pp_config`, the spec says
   `Portrait: none.`, and a bust is its own card: it must stand above the box on its top edge, never a column, because
   48 pixels would cost 6 of the 28 characters.
3. **The check is arithmetic, not an eyeball.** `tools/preview_dialogue_box.py` now composes a choice page with the
   rows replaced, reads the choice columns out of `pp_config`, and refuses (exit 1) any dialogue row cell that shares a
   pixel with a label cell or the cursor (`layout_conflicts`). `tests/test_dialogue_choice_layout.py` feeds that check
   the exact old panel geometry (a label at x 140 over a row reaching x 191) and requires it to fail, so the fault
   cannot come back quietly.

---

## D13. The sheet grows `/`, `[` and `]` and nothing else, in ASCII order

Card t_f476435e (SHEET-GLYPH-GAP), the card D11 item 3 opened. Ruled D13 and not D12 because card t_01432e14 took
D12 later the same day; the numbers in this file are append only, so a ruling that arrives second takes the next
number rather than renumbering a decision another card already quotes.

1. **The sheet grows exactly three characters: 74 frames to 77.** Each one has a shipped string behind it, which is
   the test for every future glyph too.
   - `/` is asked for by two sites. The battle HP line had to spell `HP 12 OF 12` to avoid a hole (D11 item 3), and
     the boot data error card prints `Data problem: ` plus `dialogue/all.json`, `maps/ship_sample.json` and the rest
     of `pp_data_load`'s names, every one of them with `/` in it, so the loader's own failure message was printing
     blank cells in the middle of the file name. The slash pays twice.
   - `[` and `]` are a live defect and not a preference. `pp_drive_draw_caption` draws `"[" + string(_page) + "]"` at
     x 16, y 196, and both brackets printed as a space, so the caption read ` 1 ` with two empty cells either side of
     the number.
   - **Nothing else was added.** A probe of the licensed face at 8 px (the same `bitmap()` the sheet is built from)
     shows `; \ | < > @ # % & + = _ { } ~ $ ^` all rasterise inside the 8x8 cell and none of them is printed by any
     file in the tree today. A glyph nothing draws is a frame the NES checker audits forever and a false claim about
     what the game can say. The rule this sets: a character is added when a shipped string asks for it, and the string
     is named in the ruling.
2. **The position is ASCII order, so no existing frame moves.** `/` is 0x2F, between `.` and `0`; `[` is 0x5B and `]`
   is 0x5D, between `Z` and `a`. All 74 old frames keep their index, so the sheet is the old 592x8 with three cells
   spliced in, and every sprite frame number the game already stores stays valid. `order[0] == " "` and
   `order[-1] == "z"` still hold, and `tests/test_make_title_ui.py` still asserts both.
3. **The glyphs are the licensed rasteriser's, at 8 px, in the one ink.** `/` is a 7 px diagonal drawn one pixel a row;
   `[` and `]` are 4 px wide and 7 rows tall: a 4 px top serif, a 2 px stem and a 4 px bottom serif. Nothing hand drawn,
   nothing tinted, nothing widened: the cell is 8 px and spec 13 owns it.
4. **One change, five files, and the sheet is the sixth.** `tools/art/pressstart2p_font.py`'s `GLYPHS`,
   `tools/art/make_ui_nes.py`'s copy, `game/scripts/pp_font/pp_font.gml`'s `pp_font_glyphs()`,
   `data/ui_layouts.json`'s `font.glyphs`, and the generated `spr_pp_font8.png` plus its sidecar (`frames` 74 to 77).
   The frame-count assertions moved with them: `tests/test_make_title_ui.py` reads 77 frames and a 616x8 image,
   `tests/test_nes_check.py` reads `616x8  77 tiles  1 colours`. `tools/check_font_coverage.py` refuses a run where
   any of the four declarations disagree, so a half done addition is a red check and not a sheet at the wrong index.
5. **What reads differently on screen.** The HP line is `HP 20/20   WILL 3/3` at x 16 to x 167, inside its region and
   clear of the frame; the drive caption's `[1]` is three cells at x 16 to x 39; the boot data error's file name is
   legible. Nothing else changed: the sheet's ink is still `#f8f8f8`, its colour count is still 1, and no other string
   in the tree contains a character it did not contain before.

Proof, all run on 2026-10-23: `python tools/check_font_coverage.py` exit 0 with 77 covered, 62 required, 0 missing,
one ink `#f8f8f8`; `python tools/nes_check.py game/sprites_src/title/spr_pp_font8.png --type sprite` prints
`616x8  77 tiles  1 colours  PASS`; `python tools/preview_battle_font.py` exit 0 with the HP line measured at
x 16..167 y 156..163 inside its region; `python tools/nes_audit_all.py --quiet` exits 1 on 34 preview files under
`output/` and that is not this sheet: the asset scope is 127 of 127 pass, the sheet's own row reads 616x8, 1 colour,
0 offending pixels, and every one of the 34 failures is a preview composite drawn in the project palette rather than
the 2C02 one.

---

## D14. The bust stands above the box on the box's own left margin, and the plate moves out of its way

Card t_4d6b0f4b (DIALOGUE-PORTRAIT), the card D12 item 2 handed the portrait to. D12 removed a frame nothing drew and
required that any bust stand above the box, never take a column, because 48 pixels would cost 6 of the 28 characters.
This ruling keeps that boundary and fills the frame that D12 emptied.

1. **Geometry: 48x48 at (16, 120), drawn into the sheet with its own 1 pixel frame.** 120 + 48 = 168, and 168 is
   `PP_BOX_Y`, so the bust's last row is the pixel above the box's top edge: it stands on the box and covers none of it.
   `PP_PORTRAIT_X` is `PP_TEXT_X`, so the bust and the words share one left margin without sharing a pixel. The three
   macros came back to `pp_config` as literals because the preview and the tests read them out of the source text, and a
   computed value there would be a number nothing could check.
2. **The bust is the page's, resolved the way the speaker already is.** A dialogue entry may carry `portrait`, and a
   page may override it, including to `""` for a page that draws none. `quay_gate_checkpoint` is the case that forced
   this: it is a `narrator` entry whose second page is the guard speaking, so the bust belongs to the page, not to the
   entry. A `narrator` carrying a bust is a data error, because the narrator is the case with no face.
3. **The name plate moves right, and only when a bust is up.** The plate was 64 wide at x 12 over the box's top border,
   and the bust occupies x 16..63 of that same border band, so the two would have shared pixels. `PP_PLATE_X` 12 stays
   the no-bust position and `PP_PLATE_BUST_X` 68 is the bust position: 68 is one past the bust's last column, and
   68 + 64 = 132 ends well inside the box's 240 width. The plate is still 13 rows tall and still sits over the border,
   so nothing about it changes for a page with no bust.
4. **What the bust costs nothing.** The text area is untouched: 28 characters from x 16 to x 240, 3 rows, 10 pixels a
   line. The box is still 240x64 at (8, 168) and the frame is still 256x224. Nothing was reserved, shrunk or re-wrapped,
   which is the whole reason the bust went above the box rather than beside the words.
5. **The art is a framed panel, not a cut-out.** A transparent bust over a dark scene read as a hole in the level, so
   each sheet is a solid panel in one entry with ink line art over it and one accent colour: four entries a sheet, three
   in any 8x8 tile, a 1 pixel frame ring in one colour, every colour a `data/nes_palette.json` entry. Three sheets ship
   for the three speakers who are on screen in the slice: the quay guard, Percy, and Prometheus. A speaker with no sheet
   draws no bust, which is what every remaining entry in `dialogue/all.json` does.
6. **The check is arithmetic and has a failing case.** `tools/preview_dialogue_box.py` composes the bust and the plate
   from the macros and refuses (exit 1) a bust whose last row is not `PP_BOX_Y - 1`, a bust outside the frame, and a
   bust that shares a pixel with a text row, a choice label or the plate. `tests/test_dialogue_choice_layout.py` moves
   the composed bust into the text area and requires that check to fail, so the geometry cannot drift back quietly.
   `tools/check_data.py` refuses a `portrait` naming a sheet that is not there, and the copy of the data rules on a root
   with no art lane says so instead of guessing.
7. **What this does NOT do.** No bust is drawn in battle (`pp_battle_text` owns that panel and has no portrait, by its
   own header comment), no portrait animates, and no bust is authored for a speaker who never appears in the slice. The
   sheets are 1 frame each on purpose: a portrait that blinks is a later card with its own timing ruling.

Proof, all run on 2026-10-23: `python tools/check_data.py` exit 0, all files pass; `python tools/preview_dialogue_box.py`
exit 0, PASS, with the guard's page measuring a bust at `x 16..63 y 120..167` whose last row is 167 against the box top
edge 168 and a plate at `x 68..132 y 162..174`; `python tools/nes_check.py` PASS on each of the three sheets; and
`python -m pytest tests/test_dialogue_choice_layout.py tests/test_dialogue_v2.py tests/test_schemas.py` 77 passed.

---

## Provenance

No external code, art, audio, dialogue or decompiled material was read, retyped or reused for this file or the cards it
rules. Every number here is quoted from this repository's own files: `knowledge/GAMEDEV-DECISIONS-2026-10-22.md`,
`knowledge/ARRIVAL-CONTENT.md`, `knowledge/DRIVE-SHOT-LIST.md`, `knowledge/HACKATHON-AUDIT-2026-10-22.md`,
`specs/18-boss-phases.md`, and the blocked cards' own comments and logs.

Written by gamedev, 2026-10-23. Check for this file: it exists, each of D1 to D14 states a ruling and a reason, D1 names
the exact five flags and the one writer, D4 names the three children, D10 carries the box's three numbers and the four
re-broken lines, D12 names the three choice numbers and the fault the overlap check refuses, D13 names the three
characters the sheet grew and the ASCII index each one took, D14 names the bust's three numbers, the plate's two
positions and the one page shape that forced the bust onto the page rather than the entry, and every claim of "already
done" is tied to a capture or a log line in this repository.
