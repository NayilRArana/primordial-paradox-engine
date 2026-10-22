# CHAR-PIPE review (card t_d01614a1), code-review, 2026-10-21

Independent review of commit ecef6a1: tools\sprite_pipe.py, tests\test_sprite_pipe.py, DEVLOG.md.
Every number below was measured by this lane's own scripts against the pixels, not read from
output\char_pipe\*\char_pipe_report.json.

Verdict: NOT SIGNED OFF. Six of seven checks pass. One check fails on the card's own standard for a
TODO slot; three documentation and labelling findings follow it.

## Checks that pass, with the measurement

1. nes_check on all committed outputs, run by the CLI in this lane:
   - with_poses\spr_pp_char_overworld.png 32x64 32 tiles 4 colours PASS
   - with_poses\spr_pp_char_battle.png 168x32 84 tiles 5 colours PASS
   - no_poses\spr_pp_char_overworld.png 32x64 32 tiles 3 colours PASS
   - no_poses\spr_pp_char_battle.png 168x32 84 tiles 5 colours PASS
   All four exit 0, palette read from data\nes_palette.json (64 colours).
2. Own pixel measurement, no nes_check code reused: 0 tiles over 3 opaque colours on all four
   sheets, worst tile 3; alpha is only 0 and 255; 0 off-palette colours; previews 504x312.
3. Geometry: overworld 32x64 = 8 frames at 16x16 in 4 rows (down, up, left, right) by 2 columns
   (walk 0, walk 1); battle 168x32 = 7 frames at 24x32 (idle 2, attack 3, hurt 1, down 1).
4. Left is the byte mirror of right, row for row. Walk 0 differs from walk 1 in all four rows.
   All seven battle frames are non-empty and mutually distinct.
5. With no pose folder, six battle frames are a visible single-colour X (64 opaque pixels each)
   and idle_0 is the labelled concept stand-in. Six names in the todo list, as claimed.
6. The validator is load bearing, not decorative: injecting a 5-colour 8x8 tile into a real sheet
   makes nes_check exit 1 and name the tile, so a PASS above means something.
7. Reproducible from a clean folder: `--selftest --out <empty dir>` exits 0 and writes both sheets,
   both previews and both reports; nes_check on the freshly written sheets also passes.
8. A supplied mask PNG is honoured in pixels, not just in the report string: a band mask changed
   the overworld sheet from 1132 to 384 opaque pixels, still within the tile rule.
9. pytest tests/test_sprite_pipe.py: 15 passed in 1.52 s under the gate's pinned interpreter
   <home>/AppData/Local/Python/bin/python.exe.
10. No long dashes in the three added files.

## F1 (FAIL): a frame with no visible pixels passes as finished art

The card allows a frame with no pose to be marked TODO. The tool does that for a MISSING pose file.
It does not do it for an EMPTY one, and it does not do it for a mask that removes everything.

Measured, three inputs:
- an all-black mask PNG: exit 0, overworld sheet 0 opaque pixels, printed "0 colours ... PASS
  nes_check", no warning anywhere.
- a pose folder where all seven battle pose PNGs are present but fully transparent: exit 0,
  battle sheet 0 opaque pixels of 5376, printed "battle TODO none, every frame came from a pose
  image", report nes_check ok true.
- the same path covers a concept whose corner matte removes everything, since fit_frame returns a
  transparent frame and nes_check counts 0 colours as legal.

Why it matters: the pose images come from an image model next, and that model returning a blank or
blocked image is the ordinary failure. The pipeline would then hand the manager a PASS and an empty
sheet, which is the exact opposite of the guarantee the file's own docstring makes ("a blank slot
can never pass for finished art").

Suggested fix, small: count opaque pixels per finished frame; when a frame is blank, substitute the
TODO X, name it in todo, and set run() ok false (or a loud warning) when a whole sheet is blank.

## F2 (minor): unreadable inputs raise a traceback instead of the documented refusal

`--concept` pointing at a missing file raises FileNotFoundError; a non-image file raises
PIL.UnidentifiedImageError. The exit code is 1, which matches the docstring, but only by accident of
an unhandled exception, and the operator gets a stack trace instead of a reason. collect_poses()
already shows the intended shape (SystemExit with a message).

## F3 (minor): three of the four directions are the same picture, and nothing says so

down_0, up_0 and right_0 are byte identical by construction (three calls to _concept_frame with the
same concept and mask), and down_1, up_1, right_1 were identical here too. The sidecar labels all
three frame 0s "concept", which is true and does not record that the sheet is not directional. A
visual reviewer looking at four rows can read them as four views. Suggested: a per frame facing note
or a report field such as "facing: same render as right".

## F4 (minor): the docstring describes a mock reply that does not happen, and the ledger never appears

The header says the mock backend "answers with metadata and no mask pixels" and that the model call
"still lands in data\ai_ledger.csv". Measured: the call refuses ("ai_client.segment refused: gemini
backend has no segmentation here: SAM style segmentation is the Meta lane, and Meta's docs arrive
Oct 26"), which the sidecar records honestly, and data\ai_ledger.csv does not exist after a full
selftest run. The behaviour is defensible; the documentation overstates it.

## Note on the suite number in the builder's comment

tests today: 14 failed, 14 errors, 421 passed, under the pinned interpreter. None of the failures or
errors names sprite_pipe.py or char_pipe, so this commit is not their cause (the dash gate for
example is red on assets\audio\title_theme_v3\EAR_REVIEW_126.md, another lane's file). The builder's
"339 passed, 5 failed" no longer describes the tree: three later commits landed after it ran.

## Re-confirmation on the current tree (2026-10-22 00:02, run 2161)

The reviewed code is unchanged: tools\sprite_pipe.py and tests\test_sprite_pipe.py last changed in
ecef6a1 and are clean in git status. F1 was re-measured from a committed probe rather than carried
over from the first run: knowledge\char-pipe-review\review_char_pipe5_reconfirm.py, under the pinned
interpreter, on the tree at 90f8513. Same result, exit 0 both times:

    seven battle pose PNGs present, all fully transparent
      battle 168x32  0 colours  PASS nes_check | 0 of 5376 opaque | todo [] | nes_check ok true
      printed "battle TODO  none, every frame came from a pose image"
    all black mask
      overworld 32x64  0 colours  PASS nes_check | 0 of 2048 opaque
      the battle sheet lists all seven names in todo, and the blank overworld sheet still exits 0

So the defect is live on the code the builder is being asked to fix, not a stale measurement.

## Re-confirmation of all four findings (2026-10-22 02:15, run 2189)

After the card was unblocked, every finding and every pass-side number was re-measured from scratch,
not copied from the section above. Code still at ecef6a1 for tools\sprite_pipe.py (git log -1 -- it
and git diff ecef6a1 both empty).

  nes_check --type sprite, four committed sheets, four exit 0:
    with_poses overworld 32x64  32 tiles  4 colours  PASS
    with_poses battle    168x32 84 tiles  5 colours  PASS
    no_poses   overworld 32x64  32 tiles  3 colours  PASS
    no_poses   battle    168x32 84 tiles  5 colours  PASS
  pytest tests\test_sprite_pipe.py: 15 passed in 1.94 s.
  overworld: walk 0 differs from walk 1 in all four rows, left walk 0 is the byte mirror of right walk 0.

  F1 live: seven transparent pose PNGs give exit 0, battle 0 of 5376 opaque, "battle TODO none, every
  frame came from a pose image", nes_check ok true. All black mask gives exit 0, overworld 0 of 2048
  opaque, 0 colours printed as PASS.
  F2 live: corrupt concept raises PIL.UnidentifiedImageError with a traceback; missing concept raises
  FileNotFoundError with a traceback. Exit 1 in both cases, by accident.
  F3 live: down 0, up 0 and right 0 are byte identical (down==right, up==right, down==up all true).
  F4 live: data\ai_ledger.csv still does not exist; ai_client exports segment.

Probes for this pass: recheck_f1.py and recheck_f234.py in the review workspace
(<agent-runtime>\kanban\boards\nayil-ops\workspaces\t_d01614a1), writing only to
the Hermes profile scratch dir.

## How to rerun every check here

Interpreter for all of it (the gate's pinned one):
<home>/AppData/Local/Python/bin/python.exe, run from the project root.

    python tools\nes_check.py output\char_pipe\with_poses\spr_pp_char_overworld.png --type sprite
    python tools\nes_check.py output\char_pipe\with_poses\spr_pp_char_battle.png    --type sprite
    python tools\nes_check.py output\char_pipe\no_poses\spr_pp_char_overworld.png   --type sprite
    python tools\nes_check.py output\char_pipe\no_poses\spr_pp_char_battle.png      --type sprite
    python -m pytest -q -p no:cacheprovider tests\test_sprite_pipe.py

The independent pixel probes sit in knowledge\char-pipe-review\ and write only to the system temp dir
(<home>\AppData\Local\Temp\char_pipe_review), never into the repo. Run them in order:
review_char_pipe.py (own tile, palette, geometry, mirror and preview measurement),
review_char_pipe2.py (load-bearing validator, clean-folder reproduction, mask honoured, error path),
review_char_pipe3.py (black mask, corrupt concept, sidecar origins, duplicate direction frames),
review_char_pipe4.py (blank pose files). review_char_pipe2.py is the one that prints SECOND HALF FAIL,
and F2 is why.

