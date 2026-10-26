# PNG-BYTE-ROWS, 2026-10-25: the two byte comparison rows read the crop, not the encoder (card t_78db3b2c)

Raised by the Pine gate card t_07946efc, whose run of 2026-10-25 18:31 to 18:36 at HEAD 0b5dd01 left two red rows
that pass on this machine. This note is the evidence that the fix reads the picture and that the two rows still
refuse a changed picture.

## What was red

1. `tests/test_make_battle_bg.py:164` `test_the_committed_strips_are_what_the_generator_writes`, red as
   `AssertionError: run tools/art/make_battle_bg.py: game/sprites_src/bg/bg_battle_corridor.png is not what the
   generator writes`, `At index 36 diff: b'\x80' != b'\x9c'`.
2. `tests/test_scene_palette_set.py:436` `test_the_committed_cloud_ground_is_the_crop_its_generator_builds`, red as
   `AssertionError: output/cloud_sky_ground.png is not what tools/art/title_cloud_ground.py builds`, `At index 36
   diff: b'|' != b'w'`.

Both `At index 36 diff` lines are the whole diagnosis. Byte 36 of a PNG is the low byte of the first IDAT chunk
length, so bytes 0 to 35, the 8 byte signature plus the whole IHDR block (width, height, bit depth, colour type,
interlace), were equal on the two sides. The two files agreed on size and format and first differed in how much
deflate produced. That is the class `pytest.ini` line 9 already names: "The pixels agree; the encoder does not".

The far side held the right pictures. `data/results/offload-perc-0.json` from `arananet\pine` printed
`bg_battle_corridor.png SHA-256: 0d1036688fc56c777fbd63ae60433254a554fd6181cc55e0efdcfaabe8204176` and
`cloud_sky_ground.png SHA-256: 80a7f373397fe133dc9f8043c59f43ef5ac498b655996b6ad3da6a52df0f2b15`, and both equal
this machine's copies of the same two files byte for byte.

## What changed

Each row now compares decoded pixels: `Image.open(...).convert("RGBA").tobytes()` on both sides plus a size check.
The strips row keeps its temp folder build through `mb.write_png`, and the cloud row decodes the bytes
`title_cloud_ground.build(ROOT)` returns through `io.BytesIO`. That is the shape
`tests/test_title_art_v2.py::test_the_committed_logo_is_the_generator_output` already uses for the committed title
logo, and `tests/test_make_characters_v2.py::test_committed_sheet_is_the_generator_output` for the walking sheets.

The card offered two routes: mark both rows `@pytest.mark.host_png_bytes`, or compare pixels. Pixel comparison was
taken because the marker removes both rows from every offloaded run, and these two rows are the only thing holding
the shipped strip and the shipped cloud crop to the tools that own them. `tests/conftest.py:112` turns the marker
into a skip whenever `sys.platform != "win32"`, so the marker route would have made the Pine gate quiet by making
it blind. The pixel route keeps the pin and keeps the coverage.

Nothing else moved: no generator, no committed PNG, no `data/scene_palettes.json` row, no `pine_offload.py` line.
`knowledge/ART-BIBLE.md` RULE 0 stands as written.

## The pins still bite, measured

A probe copied each committed file to a scratch backup, shifted one pixel at (0, 0), ran the row, then restored the
file and compared hashes:

```
game/sprites_src/bg/bg_battle_corridor.png
  original 0d1036688fc56c77 damaged 274a85c1d528314b
  exit 1  1 failed in 0.94s
  restored 0d1036688fc56c77  match True
output/cloud_sky_ground.png
  original 80a7f373397fe133 damaged d07e08ef05e58908
  exit 1  1 failed in 0.89s
  restored 80a7f373397fe133  match True
```

One changed pixel fails each row, and both files came back byte identical to their committed copies.

## Runs

- This machine, `python -m pytest tests/test_make_battle_bg.py tests/test_scene_palette_set.py -q`: 46 passed.
- This machine, with the house style gate `tests/test_project.py` in the same command: 69 passed.
- Isolated at HEAD 482a862 in a throwaway `git worktree` with only this card's test edit applied:
  46 passed in 4.39s. That run exists because the live tree of that moment carried another lane's uncommitted
  `data/palettes/scene_ship.json`, which leaves `test_build_reproduces_the_file_on_disk` red for a reason that is
  not this card; the worktree proves the two rows at a tree nobody else was editing.
- Pine, live tree, `python pine_offload.py --files tests/test_make_battle_bg.py,tests/test_scene_palette_set.py
  --shards 1 --name pngbytes` from `arananet\pine`: `results_txt` reads `45 passed, 1 skipped in 3.70s` and
  `summary` reads `SUMMARY passed=45 failed=0`. Both rows PASSED there rather than skipping. The one skip is
  `test_every_judged_rows_ground_is_a_file_a_clean_checkout_carries`, which asks git and the upload is a zip.
  Evidence: `arananet\pine\data\results\offload-pngbytes-0.json`, `status: completed`, `upload_attempts: 1`.
- Pine, live tree again at 19:12 after this card's commit, `--name pngbytes2`: `44 passed, 1 failed, 1 skipped` and
  `SUMMARY passed=44 failed=1`, the one failure being
  `tests/test_scene_palette_set.py::test_build_reproduces_the_file_on_disk` at `At index 6 diff: {'id': 'ship'...}`.
  That is the other lane's uncommitted ship palette edit travelling in the zip, not a card row. Evidence:
  `arananet\pine\data\results\offload-pngbytes2-0.json`.
- Pine, the committed tree, `--name pngbytes-commit3`: `.........................................s.... [100%]
  45 passed, 1 skipped in 3.48s` and `SUMMARY passed=45 failed=0`. This is the card's acceptance measurement. It
  offloads a throwaway `git worktree` checked out at `d70ff45` (this card's commit) through a copy of
  `pine_offload.py` placed two directories below `projects`, so `REPO` resolves to that clean checkout instead of
  the shared working tree; the zip was 11,349,650 bytes and the upload needed two attempts after a
  `ConnectionError` on the first, which the tool retried. Both card rows passed there, and the one skip is the git
  row above. Result file:
  `wt-t_78db3b2c\projects\gamedev\pine\data\results\offload-pngbytes-commit3-0.json` under the gamedev scratch
  directory, copied to `knowledge\PNG-BYTE-ROWS-2026-10-25-pine.json` in the follow-up commit that carries this
  section.

The two Pine numbers differ only in the tree they measure: the live tree at 19:12 held another lane's uncommitted
`data/palettes/scene_ship.json`, and the committed tree at `d70ff45` does not. Neither number was taken with a card
row failing.


## One thing the repo did to this card, recorded because it is the hazard the lane wrapper exists for

`tests/test_make_battle_bg.py` was carried into commit `031a96c` (card `t_8ebcb489`, MAKE-BATTLE-BG-OWNER,
"the deck's four declared rows are its file's") because that lane named the same path and the private index is
built from that lane's working tree, which held this card's edit at the time. The change itself is in HEAD and
correct there; the commit that carries it is not this card's. `tests/test_scene_palette_set.py` and the DEVLOG
entry are this card's own commit. Nothing was edited twice, and no file was reverted to fix the attribution.

## Still unproven

Nothing here measured a Pine-only failure of the same class in any other row. The three rows that still carry
`@pytest.mark.host_png_bytes` and the committed-CRLF JSON row are other cards' to judge, not this one's.
