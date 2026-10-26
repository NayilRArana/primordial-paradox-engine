# SHIP-PALETTE-DRIFT, 2026-10-25: the ship's palette file is an INPUT to its own sheet, so the solver's proposal was refused and the tool was fixed (card t_92d59163)

Raised by card t_78db3b2c (PNG-BYTE-ROWS). While that card was landing, `data/palettes/scene_ship.json` sat modified
and uncommitted in the shared working tree, which left
`tests/test_scene_palette_set.py::test_build_reproduces_the_file_on_disk` red at the ship row. The commit gate maps a
staged file to the project suite, so that one row refused every commit in the repository, and because
`pine_offload.py` zips the working tree it travelled into every Pine upload as `SUMMARY passed=44 failed=1`.

The card offered two exits: land the edit and rebuild `data/scene_palettes.json`, or revert and leave
`git status -- data/palettes/` clean. The edit is REVERTED. This note is the measurement that decided it, because the
first answer ("this file is a solver output, so the solver is right and the committed rows are stale") is wrong in a
way the palette checks cannot see.

## What the uncommitted file was

Not a hand edit. It was the exact output of the ship's own solver:

```
git worktree add --detach <scratch>/pp-head 71f168d
cp <shared>/data/palettes/scene_ship.json <pp-head>/data/palettes/scene_ship.json
sha256sum data/palettes/scene_ship.json
  a31d53753eb0e5868089e2eed97b489b96641d290614e74b3517f1104fe79f81
python tools/art/scene_palette.py solve --scene ship --write
sha256sum data/palettes/scene_ship.json
  a31d53753eb0e5868089e2eed97b489b96641d290614e74b3517f1104fe79f81
```

Byte identical, and `write_scene()` had carried the sprite half, the notes and both `judged` rows forward verbatim
(`sprites_pinned` is true). So the only thing the uncommitted file changed was the background half, from
`bg1 $12 $28 $30` / `bg2 $02 $07 $17` to `bg1 $07 $17 $30` / `bg2 $02 $12 $28`.

Why the two disagree was also measured, and it is not the solver's code. The ship file and
`game/sprites_src/env/ts_ship.png` were added by the same commit, `7a73469`, and the sheet has not changed since
(`git diff --stat 7a73469 HEAD -- game/sprites_src/env/ts_ship.png` is empty). The `7a73469` copy of
`tools/art/scene_palette.py`, loaded and run against today's tree, prints today's rows. The input that moved is
`data/nes_palette.json`, the 2C02 master table: it did not exist at `7a73469` at all (the 667 lines arrive in
`e526c5f`), so the ship was solved against an uncommitted working copy of the master, and the table was committed
corrected afterwards. Three separate processes and two clean worktrees all print the same four rows, so this is a
deterministic answer and not a hash order artefact.

## Why the proposal was refused anyway: the sheet is painted INTO these rows

Every palette check passes with the proposal, and that is the trap:

| check, in a clean worktree at HEAD | committed rows | solver's proposal |
|------------------------------------|----------------|-------------------|
| pixels outside every background row over the 48 areas | 0 | 0 |
| palette index histogram over the 48 areas | `[35, 6, 6, 1]` | `[35, 6, 6, 1]` |
| `tools/check_scene_palettes.py` | PASS, 48 tiles | PASS, 48 tiles |
| `tools/palette_synergy.py --gate`, `ship ts_ship.png` | PASS, 0 fail(s) | PASS, 0 fail(s) |
| the whole `--gate` sweep | 9 entries, 0 gated, 7 advisory, 1 not measured | identical line for line |

All of those measure the committed sheet AGAINST the rows. The rows are not a description of the sheet, they are an
input to it: `tools/art/make_env_ship.py build()` runs `scene_palette.enforce_ship_sheet()` over the in-memory sheet
and saves the result, so a row move repaints the art. Measured by building the sheet into a scratch root seeded the
way `tests/test_make_env_ship.py` seeds it, once per row set:

```
committed rows    sha256 2d213039345402edede01a670e0771c6315e1dd9d17d675abc0220604d37bbbe
                  byte identical to the committed ts_ship.png: True    pixels that differ: 0

solver's proposal sha256 82394a4367ec265ae19b591a74a1278068cf76ce42dfaa51a31d5589a32102ce
                  byte identical to the committed ts_ship.png: False   pixels that differ: 151 of 12288
                  tiles that differ: 6, at (8,1), (11,2), (12,2), (13,2), (14,2), (15,2)
                  colours on the sheet: 9, and $2C #3cbcfc has left it
```

The ship tileset is a ten colour sheet by contract (`test_every_colour_on_the_sheet_is_one_of_the_ten_declared`, and
the `palette` list in `game/sprites_src/env/ts_ship_tiled.json`, card t_4f58c88d). Under the proposal a fresh build
drops `$2C` and the sheet reads nine, so `tests/test_make_env_ship.py` fails twice: the colour set no longer equals
the declared ten, and the committed `ts_ship.png` is no longer what the generator writes. Both rows pass with the
committed rows, and a fresh build at HEAD reproduces the committed sheet byte for byte, which is the property that
makes the committed art shippable at all.

So the committed rows are not stale. They are the fixed point of solve plus enforce, and only the two together can
move. Moving them means regenerating the sheet, which means either redrawing the tiles that carry `$2C` or re-ruling
the ten colour budget, and that is a card that owns the ship art, not this one. `t_92d59163` reverts the file and
leaves that card the measurement above.

## What landed instead: the trap is closed

The drift existed because `solve --scene ship` wrote `data/palettes/scene_ship.json` BY DEFAULT, while that file is an
input to the art. `solve_title()` was given `write=False` for exactly this reason on 2026-10-22; the ship half never
got it, so a bare `solve --scene ship` silently moved the art's palette. That is the edit the abandoned lane ran at
18:55.

`tools/art/scene_palette.py` now:

1. `solve_ship(root, write=False)`, same shape as `solve_title()`, with the measurement above in its docstring. A bare
   `solve --scene ship` prints the proposal and writes nothing; `--write` still writes, because a card that means to
   move the design must be able to.
2. `describe()` reports the PROPOSAL when nothing was written, through a new `proposed_scene()` that builds the same
   `Scene` object the enforcement reads. Before this, a bare solve printed the file's own rows, which is how a drift
   hides: the command looked like it agreed with the art while it was describing the art's input. The closing line
   now reads `proposal only, nothing written; the file is: ...` or `written: ...`.

Measured after the change, in the shared tree:

```
sha256 data/palettes/scene_ship.json  c61f2b29e293fec6c8d924f39d6fdf3d9360610e271b0d1d8e63a507d9519a98
python tools/art/scene_palette.py solve --scene ship
  ship: backdrop $0F #000000   48 16x16 areas, 0 pixels outside the chosen palette before enforcement
  background 1  $07 #881400  $17 #e45c10  $30 #fcfcfc
  background 2  $02 #0000bc  $12 #0058f8  $28 #f8b800
  proposal only, nothing written; the file is: data\palettes\scene_ship.json
sha256 data/palettes/scene_ship.json  c61f2b29e293fec6c8d924f39d6fdf3d9360610e271b0d1d8e63a507d9519a98
```

The disagreement is now printed on demand, and printing it changes nothing. `--write` was exercised once and its
write reverted with `git checkout HEAD --`, so the shipped file is HEAD's byte for byte.

## What is still red, and whose it is

In the shared working tree `python -m pytest tests/test_scene_palette_set.py tests/test_scene_palettes.py
tests/test_make_env_ship.py -q` reads 51 passed, 1 failed. The failure is the audit assertion at rows 5, 7 and 8,
southampton, westminster and winchester, and the difference is one appended sentence in each town's judged note
(`Closed on 2026-10-25: the paving, cobble, kerb, road, crossing and quay tiles now draw bg0_stone's M $00 #7c7c7c`).
Those three palette files are card `t_454c1876`'s (PARTY-TOWN-READABILITY), running with its evidence written and
uncommitted in this tree. The rebuild test derives the audit rows from the scene files, so any uncommitted town note
is red there no matter what this card commits, and the ship row is no longer part of it. Two rows that were red
before this card, the two `tests/test_make_env_ship.py` rows above, are green again.

## Still unproven

No GameMaker build and no hardware capture back any of this. The card did not regenerate the ship sheet, did not
redraw a tile and did not move a palette row; it left the art exactly as HEAD has it and closed the route that let a
generator edit it by accident. Whether the ship's rows SHOULD move is open, and it is open with the numbers attached.

Provenance for this note: read this repository's own files only, `tools/art/scene_palette.py` at HEAD and at
`7a73469`, `tools/art/make_env_ship.py`, `tests/test_make_env_ship.py`, `tools/scene_palette_set.py`,
`tools/check_scene_palettes.py`, `tools/palette_synergy.py`, `tools/sync_data.py`, `data/nes_palette.json`,
`data/palettes/scene_ship.json` and its history, `ts_ship.png` and its history, and the commit history of all of them.
No decompiled material was read for this card and no expression from any game is in it.
