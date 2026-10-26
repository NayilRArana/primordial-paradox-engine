# PALETTE PASS LIST, week of 2026-10-24, run 11

Owner of this page: the testing lane. This is the eleventh run of the AUTO-PINE-CHECKS card series, this run on card
`t_e94deb3d`, measured on 25 October between 18:31 and 18:42 Pacific: the palette job on Pine ran 18:31:43 to
18:33:24 and the audit job 18:33:38 to 18:36:13, and the local reproductions of the same tree finished at 18:36:30
(palette) and 18:38:32 (audit). It answers one question for the rebrand week and the store submission: for every
frame and every sprite in the project, does it pass `knowledge/ART-BIBLE.md` RULE 0 (palette first), and if it
fails, which rule fails and whose card fixes it. RULE 0 was re-read this run at `knowledge/ART-BIBLE.md` line 283,
mtime 2026-10-25 04:55:55, sha256 `02767323d888b91c...`, the same text run 10 read, so every ruling quoted below is
the one the tools implement.

The headline: the two largest failures of run 10 are gone and the total barely moved, 551 to 549. The corridor pair
fell from 163 problems to 0 because the party's four battle sheets were repainted into one reserved hero triple each
(card `t_d5483a88`, measured and priced on `t_8c27208b`) and the row was recast to those four sheets (card
`t_0949bd4e`). Three new rows arrived, one per town, and they carry the party's four walking sheets against the
frame the map generates at its spawn: southampton 36, westminster 88, winchester 32, which is 156 problems on rows
that did not exist in run 10 (card `t_dec4e92c`, and section 2 below). The audit half did not move at the file
level: 184 files, the same 34 failing paths, exit 1, with four rows' counts moved.

This run also reproduces, independently and on another machine, the "after" table the gamedev lane wrote in
`knowledge/PALETTE-RULINGS-2026-10-25.md` section 16.5: 9 entries, 0 gated, 6 advisory failing, per entry 0, 16, 0,
0, 242, 36, 135, 88, 32, 549 problems. Same numbers, same order, from a run that read `data/scene_palettes.json`
at 18:11:06 (sha256 `11b9f257791e19cf...`) and had no hand in writing it.

Every number on this page comes from a run of the tools, not from memory:

| Run | Tool | Where it ran | Evidence file |
| --- | --- | --- | --- |
| palette sweep, 9 entries, 79.5 s wall, job 18:31:43 to 18:33:24, one upload attempt | `tools/palette_synergy.py --gate --out output/ps_auto11.json`, sheet rebuilt first by `tools/art/make_characters_v2.py` | Pine computer `po-autochecks-v11a-0` | `arananet/pine/data/results/offload-autochecks-v11a-0.json`, `SHEET_EXIT=0`, `TOOL_EXIT=0`, nine pair counts 0, 6, 0, 0, 242, 36, 135, 88, 32, `9 entry(ies), 0 gated failure(s), 6 advisory failure(s), 0 not measured` |
| every art file, 153 rows, 133.3 s wall, job 18:33:38 to 18:36:13 | `tools/nes_audit_all.py --no-write` | Pine computer `po-autochecks-v11b-0` | `offload-autochecks-v11b-0.json`, `AUDIT_EXIT=1`, `nes_audit_all: FAIL  153 file(s), 13 failing, 0 unmeasured` |
| same sweep, local reproduction, 18:36:30 | `tools/palette_synergy.py --gate --out ps_auto11_local.json` | this PC | this card's workspace, `ps_auto11_local.json`, 190,780 bytes, 549 problems, every per rule and per file count below is read from it |
| same audit, 184 rows, local reproduction ending 18:38:32 | `tools/nes_audit_all.py --no-write` | this PC | this card's workspace, `audit_local_v11.txt`, 34 FAIL rows, `AUDIT_EXIT=1` |
| per file audit records, 184 rows, 18:41:36 | `tools/nes_audit_all.py` called through `audit(write=False)` | this PC | this card's workspace, `audit_records11.json`, 19,442,338 bytes |
| inventory, 184 rows, 18:38:33 | `tools/nes_audit_all.py --list` | this PC | this card's workspace, `list_v11.txt`, 184 lines |
| four frames that ship, PPU composite, 18:42:19 | `tools/nes_composite_check.py <frame>` | this PC | section 6, quoting `composite11_full.txt` |
| the entries the sweep asks about, read from disk | `data/scene_palettes.json`, 12 scenes and 9 audit entries | this PC | `entries11.py` and `exempt11.py` outputs this run |
| baseline, run 10 of this card at 05:17 to 05:32 on 25 October | `palette_synergy.py --gate` and `nes_audit_all.py --no-write` | Pine computers `po-autochecks-v10aT-0` and `po-autochecks-v10b-0` | `offload-autochecks-v10aT-0.json`, `offload-autochecks-v10b-0.json`, `knowledge/PALETTE-PASS-LIST.md` run 10, and run 10's workspace (`ps_auto10_local.json`, `audit_records10.json`) still on disk |

How to re-run it, the commands this page cites:

```
python pine_offload.py --shards 1 --name autochecks-v11a --cmd '( cd ~/repo/projects/primordial-paradox || cd ~/shared/projects/primordial-paradox; python tools/art/make_characters_v2.py > ~/make_sheet.txt 2>&1; echo SHEET_EXIT=$?; python tools/palette_synergy.py --gate --out output/ps_auto11.json > ~/ps.txt 2>&1; echo TOOL_EXIT=$?; grep -E "PASS,|FAIL,|entry\(ies\)" ~/ps.txt )'
python pine_offload.py --shards 1 --name autochecks-v11b --cmd '( cd ~/repo/projects/primordial-paradox || cd ~/shared/projects/primordial-paradox; python tools/nes_audit_all.py --no-write > ~/audit.txt 2>&1; echo AUDIT_EXIT=$?; grep -c "FAIL" ~/audit.txt; grep "FAIL" ~/audit.txt | tail -20; tail -3 ~/audit.txt )'
```

Both were called with `<home>/AppData/Local/Python/bin/python` (3.14.7), the interpreter that imports the
pinesandbox SDK; `probe_sdk.py` printed `sdk ok 0.3.2` and `KEY_PRESENT True` against it before either job started,
and nothing else about the key. The palette job shipped a zip of 14,646,647 bytes (34 tracked output files) and the
audit job one of 14,664,965, both first attempt, no connection reset, against run 10's six attempts for the palette
half (source: the two job JSON files, fields `started`, `finished`, `wall_seconds`, `upload_attempts`,
`results_txt`).

Five traps, four the same as run 10 and one new:

1. The card body says `palette_synergy.py --all`. There is no `--all`; the every-entry switch is `--gate`, read from
   `python tools/palette_synergy.py --help` this run.
2. `pine_offload.py` wraps a `--cmd` as `{cmd} 2>&1 | tail -150 > ~/results.txt`, so `results_txt` is a tail. The
   palette command greps its per pair lines first, so all nine survive; the audit command greps every FAIL row and
   the summary, so the 13 fail rows survive and the earlier pass rows do not.
3. A count compared across runs compares two rulesets if the tools or the data moved, and this run BOTH moved:
   `tools/palette_synergy.py` is sha256 `bdcb0b6e5066004e...` at mtime 2026-10-25 06:15:24 and
   `tools/nes_audit_all.py` sha256 `20fabd83d9760657...` at 06:15:58, both from commit `c8364f7` (card
   `t_c93a983f`), where run 10 recorded `eea5a2cfd6be3cfb...` and `8936784a1ef61ff2...`. `data/scene_palettes.json`
   went from 6 audit entries to 9 (sha256 `11b9f257791e19cf...`, mtime 18:11:06). So neither half is like for like
   and section 7 says which term of the change is a repair and which is a new question.
4. A remote agent's prose summary is not evidence. The Pine runs are cited for the lines in their `results_txt`;
   every per rule and per file number below is read from the local reproductions of the same tree.
5. NEW this run: the upload still does not carry every file the audit universe contains. Both jobs shipped 34
   tracked `output/` files and skipped 1,690 by-products, so Pine read 153 files and 13 failing while this tree
   reads 184 and 34. The difference is the same 31-file gap run 10 named, and it is the far side's universe, not the
   art's (source: the `output/: shipping 34 tracked file(s), skipping 1690 by-product(s)` line on both job starts,
   and run 10's `zipgap10.py`).

No key was read or printed: `keyscan11.py` searched both job JSON files for `PINE_SANDBOX_API_KEY`,
`GEMINI_API_KEY`, `KAGGLE_API_TOKEN`, `bearer`, for a key shaped string (`sk-`, `pk-` or `ak-` plus 16 characters)
and for a run of 32 or more hex characters: zero of the first four, zero key shaped strings, and two 32 character hex
runs, both of them the job's own `turn_id` (`turn_b01939f827b4018a2ed6e01f6a2e936f_1` and
`turn_19ccf5b4a3c4747eee786253b396c354_1`), not a key.

## 1. The week in eleven numbers

| Number | Value | Source |
| --- | --- | --- |
| Files in the audit universe | 184 (130 game assets: 76 sprites and 54 backgrounds; 54 output files: 25 frames, 21 sheets, 8 captures) | `list_v11.txt`, 184 lines, and `audit_records11.json`, whose scope column gives 25 frame, 21 sheet, 8 capture |
| Rows the audit gates | 155 (130 assets and every 256x240 preview frame); 29 advisory (21 sheets, 8 captures) | `audit_records11.json`, and `tools/nes_audit_all.py` lines 10 to 26 |
| NES audit verdict, local | FAIL, 184 files, 34 failing, 0 unmeasured, 10 gated failures among them, exit 1 | `audit_local_v11.txt`, `AUDIT_EXIT=1` |
| NES audit verdict, Pine | FAIL, 153 files, 13 failing, 0 unmeasured, exit 1 | `offload-autochecks-v11b-0.json`, `results_txt` |
| Game assets that fail the NES audit | 0 of 130, on both hosts | `audit_records11.json`, where every `scope: asset` row is `ok: true` |
| Output files that fail the NES audit | 34 of 54: 10 frames (gated), 20 sheets and 4 captures (advisory) | `audit_records11.json` |
| Palette synergy entries | 9 entries (run 10: 6), 3 PASS, 6 FAIL, 0 gated, **549 problems** (run 10: 551) | `ps_auto11_local.json`, and `offload-autochecks-v11a-0.json`, whose nine totals match the local ones on eight of nine entries and print 6 against the local 16 on the contact sheet, which the far side rebuilds from a different generator |
| where the 549 sit | frame side 326 `palette_count`; sprite side 223 (palette_count 0, set_member 37, white_blob 96, body_ground 54, invisible 18, same_hue_row 4, sprite_tile 4, overlay_contrast 10) | `ps_auto11_local.json`, grouped in `matrix11.py` this run |
| Sprites that fail either check | 7 of the 76 sprite files, plus the contact sheet `output/sprites_v2_sheet.png` (a by-product, advisory by ruling) | section 3, and `ps_auto11_local.json` |
| Composite PPU check on the four frames that ship | 3 PASS at 11, 7 and 9 colours, 1 FAIL (`output/ship_dialogue.png`, 70 blocks violate, 407 colours) | local `nes_composite_check.py` run at 18:42:19, `composite11_full.txt` |
| The gate that decides the release | 0 of 12 scenes and 0 of 9 audit entries carry `"gate": true`, so `--gate` reports all 9 entries advisory and exits 0 on both hosts | `data/scene_palettes.json` read this run (`entries11.py`), and `TOOL_EXIT=0` in both palette jobs |

The finding that decides the release question has not moved. Nothing in `data/scene_palettes.json` is gated (0 of 12
scenes, 0 of 9 audit entries), so the palette gate cannot refuse a build; the gate that actually returns 1 is the
audit's own `frame` scope, and ten 256x240 preview frames fail it (source: `tools/nes_audit_all.py` lines 10 to 26,
the ten `FAIL frame` rows in `audit_local_v11.txt`, and `gated_failures: 10` in `audit_records11.json`).

## 2. The nine frame and sprite pairs (palette synergy, this run)

One row per audit entry, in the order `data/scene_palettes.json` lists them. Fail counts are problem records, so one
sprite standing on a bad ground many times counts many times. Every number is read from `ps_auto11_local.json`
(grouped by `matrix11.py` this run), and the entry text from `data/scene_palettes.json` (`entries11.py`,
`exempt11.py`).

| # | Scene | Frame (ground) | Sprites, problems each | Verdict | Fails | Rules hit | Owner card |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | battle_corridor | output/bg_battle_corridor_frame.png | percy_battle 0; hadrian_battle 0; zander_battle 0; konrad_battle 0 | **PASS** (exempt row) | 0 | none | cast ruled by t_0949bd4e (done), sheets by t_d5483a88 (done) |
| 2 | battle_corridor | output/bg_battle_corridor_frame.png | output/sprites_v2_sheet.png 16 (set_member 12, sprite_tile 4) | FAIL, by-product, advisory | 16 | set_member x12, sprite_tile x4 | PALETTE-ARITHMETIC t_c93a983f (done), by-product so no owner |
| 3 | battle_deck_night | output/bg_battle_deck_night_frame.png | percy_battle 0; hadrian_battle 0; zander_battle 0; konrad_battle 0 | **PASS** (exempt row) | 0 | none | cast by t_0949bd4e (done), bg2 spend by t_34b1d96a (done) |
| 4 | ship | game/sprites_src/env/ts_ship.png | hadrian_ow_v2 0; percy_ow_v2 0; zander_ow_v2 0; konrad_ow_v2 0; sailor_ow_v2 0 | **PASS** | 0 | none | rows by t_a6a7f436 (running, landed as 17c3660), ground by t_1dc346b9 (done) |
| 5 | ship | output/nes_title_frame.png | frame 210 (palette_count 210); sailor_ow_v2 32 (set_member 16, white_blob 8, body_ground 8) | FAIL | 242 | palette_count x210, set_member x16, white_blob x8, body_ground x8 | NES-PALETTES t_c8156a77 (done), gamedev decides |
| 6 | southampton | output/southampton_sample_frame.png | hadrian_ow_v2 12 (white_blob 6, body_ground 2, invisible 2, same_hue_row 2); percy_ow_v2 8 (white_blob 8); konrad_ow_v2 8 (body_ground 8); zander_ow_v2 8 (white_blob 8) | FAIL | 36 | white_blob x22, body_ground x10, invisible x2, same_hue_row x2 | PARTY-TOWN-READABILITY t_454c1876 (ready) |
| 7 | title | output/nes_title_frame.png | frame 116 (palette_count 116); spr_pp_title_logo 16 (set_member 6, overlay_contrast 10); spr_title_car 3 (set_member 3) | FAIL | 135 | palette_count x116, set_member x9, overlay_contrast x10 | TS2-ART-A t_758934a8 (done), gamedev decides |
| 8 | westminster | output/westminster_sample_frame.png | percy_ow_v2 24 (white_blob 16, invisible 8); zander_ow_v2 24 (white_blob 16, body_ground 8); hadrian_ow_v2 24 (white_blob 12, body_ground 2, invisible 8, same_hue_row 2); konrad_ow_v2 16 (body_ground 16) | FAIL | 88 | white_blob x44, body_ground x26, invisible x16, same_hue_row x2 | PARTY-TOWN-READABILITY t_454c1876 (ready) |
| 9 | winchester | output/winchester_sample_frame.png | percy_ow_v2 8 (white_blob 8); konrad_ow_v2 8 (body_ground 8); zander_ow_v2 8 (white_blob 8); hadrian_ow_v2 8 (white_blob 6, body_ground 2) | FAIL | 32 | white_blob x22, body_ground x10 | PARTY-TOWN-READABILITY t_454c1876 (ready) |

Problem totals across the nine entries: palette_count x326, white_blob x96, body_ground x54, set_member x37,
invisible x18, overlay_contrast x10, sprite_tile x4, same_hue_row x4, which is 549 (source: `ps_auto11_local.json`,
summed by `matrix11.py`; 342 on the frame side, of which 326 palette_count and 16 the contact sheet's, and 207 on the
sprite side).

The three readings that matter more than the counts:

1. The corridor and deck rows now measure what the gamedev lane said they would: 0 problems each on the party's four
   battle sheets, where run 10 measured 163 on the corridor row. This is the one real art repair in the window: the
   four sheets were redrawn into one reserved hero triple per hero (card `t_d5483a88`, priced on `t_8c27208b`
   section 7.3), and the sheets on disk carry mtime 07:05:44 today (source: `ps_auto11_local.json` entries 1 and 3,
   and `ls -l` on the four sheets).
2. The 156 on the three town rows is new measurement, not new damage. Those rows did not exist in run 10; card
   `t_dec4e92c` wrote them on 25 October and ruled the ground to be the frame `tools/art/make_exterior_maps.py`
   composes at each map's spawn rather than the five-group exterior atlas. Every record is a walking sheet's own body
   against the paving under the spawn tile at 128,112: the bodies are `$30` for percy and hadrian, `$31` for zander
   and `$28` for konrad, the paving is `$10 #bcbcbc` out of `bg0_stone {0,16,48}`, and on westminster hadrian's body
   IS the paving colour on all 8 frames, which is what `invisible` names (source: `ps_auto11_local.json` entries 6,
   8, 9; `knowledge/PALETTE-RULINGS-2026-10-25.md` section 16.3).
3. The title ground is still the most expensive single question on the page: 242 on the ship set and 135 on the
   title set, both against `output/nes_title_frame.png`, both unchanged from run 10 record for record, and both
   `palette_count` against a written set the frame was never designed against (source: `ps_auto11_local.json`
   entries 5 and 7, compared with run 10's pairs 5 and 6).

The four rule strings these new records use, each with one measured detail from this run, copied from
`ps_auto11_local.json` (`rules11.py` prints one record per rule):

- `white_blob`: "the frame's body vs ground at 120,208: body $30 at luminance 0.97 on ground $20 at 0.94, the white
  blob RULE 0 point 2 refuses" (sailor_ow_v2 on the title ground).
- `body_ground`: "the frame's body vs ground at 120,208: body $30 (row 3) and ground $20 (row 2) are 1 luminance
  row(s) apart at 1.04:1, and RULE 0 point 2 wants 2 rows or 3.0:1" (the same sprite, the same ground).
- `invisible`: "the frame's body vs ground at 128,112: body $00 is the ground colour, the figure has no edge there"
  (hadrian_ow_v2 on westminster, frame [32,0,48,16]).
- `same_hue_row`: "the frame's body vs ground at 128,112: body $00 and ground $0F are both grey on row 0" (the same
  sprite, the same frame).

## 3. Every sprite, pass or fail

76 sprite files, the full inventory from `nes_audit_all.py --list` with no sampling (130 game assets minus the 54
backgrounds), the same 76 paths as run 10, none added and none gone (source: `list_v11.txt` against run 10's
`list_v10.txt`, compared by `cmp11.py` this run, which reports `new paths in 11: []` and `paths gone: []`). Column 3
is the fresh `nes_audit_all.py` verdict (rules: palette, grid, sprite_tile, background_area, screen_colours, from
`knowledge/NES-AUDIT.md`), column 4 is the palette synergy verdict summed over the nine entries, column 5 is the
combined verdict, column 6 lists the rules that failed on either check, column 7 is the card the CARD-MAP assigns to
that directory and, where a newer card owns the failure, that card. Source for every row: `audit_records11.json` for
the audit column, where every sprite passes because all 34 audit failures are `output/` files, and
`ps_auto11_local.json` for the synergy column.

Headline: 7 of the 76 sprites fail something and 69 pass both checks, where run 10 had 6 failing, and no sprite in the
project fails the NES audit on either host (source: `audit_records11.json` and `tables11.md`, generated this run from
those two files). The set turned over almost completely: the four party battle sheets left it (`percy_battle` 78 to 0,
`hadrian_battle` 53 to 0, and `zander_battle` and `konrad_battle` were not failing before because the corridor row did
not name them), `zander_ow_v2` is still failing at 40, and the four walking sheets plus the title pair are now the
list: `hadrian_ow_v2` 44, `percy_ow_v2` 40, `zander_ow_v2` 40, `konrad_ow_v2` 32, `sailor_ow_v2` 32,
`spr_pp_title_logo` 16, `spr_title_car` 3 (source: `ps_auto11_local.json`, per sprite sums in `gen11.py` this run).

| # | Sprite file | NES audit | Synergy rules (9 pairs) | Verdict | Failing rule | Owner card |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | game/sprites_src/chars/hadrian_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 2 | game/sprites_src/chars/hadrian_god_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 3 | game/sprites_src/chars/hadrian_ow.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 4 | game/sprites_src/chars/hadrian_ow_v2.png | PASS | white_blob x24, invisible x10, body_ground x6, same_hue_row x4 | FAIL | body_ground, invisible, same_hue_row, white_blob | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 5 | game/sprites_src/chars/konrad_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 6 | game/sprites_src/chars/konrad_god_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 7 | game/sprites_src/chars/konrad_ow.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 8 | game/sprites_src/chars/konrad_ow_v2.png | PASS | body_ground x32 | FAIL | body_ground | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 9 | game/sprites_src/chars/percy_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 10 | game/sprites_src/chars/percy_god_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 11 | game/sprites_src/chars/percy_ow.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 12 | game/sprites_src/chars/percy_ow_v2.png | PASS | white_blob x32, invisible x8 | FAIL | invisible, white_blob | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 13 | game/sprites_src/chars/sailor_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 14 | game/sprites_src/chars/sailor_ow.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 15 | game/sprites_src/chars/sailor_ow_v2.png | PASS | set_member x16, body_ground x8, white_blob x8 | FAIL | body_ground, set_member, white_blob | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 16 | game/sprites_src/chars/spr_pp_portrait_guard.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 17 | game/sprites_src/chars/spr_pp_portrait_percy.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 18 | game/sprites_src/chars/spr_pp_portrait_prometheus.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 19 | game/sprites_src/chars/zander_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 20 | game/sprites_src/chars/zander_god_battle.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 21 | game/sprites_src/chars/zander_ow.png | PASS | not in the 9 pairs | PASS | - | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 22 | game/sprites_src/chars/zander_ow_v2.png | PASS | white_blob x32, body_ground x8 | FAIL | body_ground, white_blob | SPRITE-1 t_b2acf67d (done), towns card t_454c1876 (ready) |
| 23 | game/sprites_src/enemies/bilge_slime.png | PASS | not in the 9 pairs | PASS | - | ENEMIES-1 t_97871d4b (done) |
| 24 | game/sprites_src/enemies/deck_rat.png | PASS | not in the 9 pairs | PASS | - | ENEMIES-1 t_97871d4b (done) |
| 25 | game/sprites_src/enemies/gull.png | PASS | not in the 9 pairs | PASS | - | ENEMIES-1 t_97871d4b (done) |
| 26 | game/sprites_src/enemies/navy_sailor.png | PASS | not in the 9 pairs | PASS | - | ENEMIES-1 t_97871d4b (done) |
| 27 | game/sprites_src/enemies/petty_officer.png | PASS | not in the 9 pairs | PASS | - | ENEMIES-1 t_97871d4b (done) |
| 28 | game/sprites_src/enemies/rogue_wave.png | PASS | not in the 9 pairs | PASS | - | ENEMIES-1 t_97871d4b (done) |
| 29 | game/sprites_src/enemies/rope_knot.png | PASS | not in the 9 pairs | PASS | - | ENEMIES-1 t_97871d4b (done) |
| 30 | game/sprites_src/icons/spr_pp_icon_cursor_16.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 31 | game/sprites_src/icons/spr_pp_icon_cursor_8.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 32 | game/sprites_src/icons/spr_pp_icon_items_16.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 33 | game/sprites_src/icons/spr_pp_icon_items_8.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 34 | game/sprites_src/icons/spr_pp_icon_status_16.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 35 | game/sprites_src/icons/spr_pp_icon_status_8.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 36 | game/sprites_src/title/spr_pp_font8.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 37 | game/sprites_src/title/spr_pp_menu_cursor.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 38 | game/sprites_src/title/spr_pp_title_logo.png | PASS | overlay_contrast x10, set_member x6 | FAIL | overlay_contrast, set_member | TS2-ART-A t_758934a8 (done) |
| 39 | game/sprites_src/title/spr_pp_window.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 40 | game/sprites_src/title/spr_title_bubble.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 41 | game/sprites_src/title/spr_title_car.png | PASS | set_member x3 | FAIL | set_member | TS2-ART-A t_758934a8 (done) |
| 42 | game/sprites_src/title/spr_title_car_fade1.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 43 | game/sprites_src/title/spr_title_car_fade2.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 44 | game/sprites_src/title/spr_title_car_fade3.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 45 | game/sprites_src/title/spr_title_car_fade4.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 46 | game/sprites_src/title/spr_title_cloud.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 47 | game/sprites_src/title/spr_title_cloud_fade1.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 48 | game/sprites_src/title/spr_title_cloud_fade2.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 49 | game/sprites_src/title/spr_title_cloud_fade3.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 50 | game/sprites_src/title/spr_title_cloud_fade4.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 51 | game/sprites_src/title/spr_title_cone.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 52 | game/sprites_src/title/spr_title_cone_fade1.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 53 | game/sprites_src/title/spr_title_cone_fade2.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 54 | game/sprites_src/title/spr_title_cone_fade3.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 55 | game/sprites_src/title/spr_title_cone_fade4.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 56 | game/sprites_src/title/spr_title_cone_flash.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 57 | game/sprites_src/title/spr_title_exhaust.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 58 | game/sprites_src/title/spr_title_exhaust_fade1.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 59 | game/sprites_src/title/spr_title_exhaust_fade2.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 60 | game/sprites_src/title/spr_title_exhaust_fade3.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 61 | game/sprites_src/title/spr_title_exhaust_fade4.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 62 | game/sprites_src/title/spr_title_konrad.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 63 | game/sprites_src/title/spr_title_sign.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 64 | game/sprites_src/title/spr_title_sign_fade1.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 65 | game/sprites_src/title/spr_title_sign_fade2.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 66 | game/sprites_src/title/spr_title_sign_fade3.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 67 | game/sprites_src/title/spr_title_sign_fade4.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 68 | game/sprites_src/title/spr_title_sign_flash.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 69 | game/sprites_src/title/spr_title_star.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 70 | game/sprites_src/title/spr_title_wheel.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 71 | game/sprites_src/title/spr_title_zander.png | PASS | not in the 9 pairs | PASS | - | TS2-ART-A t_758934a8 (done) |
| 72 | game/sprites_src/ui/spr_pp_ui_cursor.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 73 | game/sprites_src/ui/spr_pp_ui_enemy.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 74 | game/sprites_src/ui/spr_pp_ui_party.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 75 | game/sprites_src/ui/spr_pp_ui_tab.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |
| 76 | game/sprites_src/ui/spr_pp_ui_window.png | PASS | not in the 9 pairs | PASS | - | UI-NES t_0df13164 (done) |

## 4. Every background, pass or fail

54 background files, the same 54 paths as run 10, and all 54 pass the NES audit. Two of them are measured grounds
this run: `game/sprites_src/env/ts_ship.png` carries the ship entry (0 problems on five walking sheets) and
`output/bg_battle_corridor_frame.png` carries two entries (the party's four battle sheets at 0, the contact sheet at
16). The grounds the three town entries use are output frames and sit in section 2. Source: `audit_records11.json`,
whose 54 `scope: asset, kind: background` rows are all `ok: true`, and `list_v11.txt`.

| # | Background file | NES audit | Synergy verdict | Verdict | Failing rule | Owner card |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | game/sprites_src/bg/bg_battle_corridor.png | PASS | not a synergy ground | PASS | - | BG-BATTLE t_1c5a8599 (done) |
| 2 | game/sprites_src/bg/bg_battle_deck_night.png | PASS | not a synergy ground | PASS | - | BG-BATTLE t_1c5a8599 (done) |
| 3 | game/sprites_src/bg/bg_battle_quay_dusk.png | PASS | not a synergy ground | PASS | - | BG-BATTLE t_1c5a8599 (done) |
| 4 | game/sprites_src/bg/bg_battle_wardroom.png | PASS | not a synergy ground | PASS | - | BG-BATTLE t_1c5a8599 (done) |
| 5 | game/sprites_src/env/quay/quay_tiles.png | PASS | not a synergy ground | PASS | - | ENV-TILES t_4f58c88d (done) |
| 6 | game/sprites_src/env/ts_exterior.png | PASS | not a synergy ground | PASS | - | ENV-TILES t_4f58c88d (done) |
| 7 | game/sprites_src/env/ts_ship.png | PASS | ground for 1 entry(ies) | PASS | - | ENV-TILES t_4f58c88d (done) |
| 8 | game/sprites_src/title/title_BG_bigben.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 9 | game/sprites_src/title/title_BG_bigben_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 10 | game/sprites_src/title/title_L1_sky.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 11 | game/sprites_src/title/title_L1_sky_fade1.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 12 | game/sprites_src/title/title_L1_sky_fade2.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 13 | game/sprites_src/title/title_L1_sky_fade3.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 14 | game/sprites_src/title/title_L1_sky_fade4.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 15 | game/sprites_src/title/title_L1_sky_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 16 | game/sprites_src/title/title_L2_clouds.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 17 | game/sprites_src/title/title_L2_clouds_fade1.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 18 | game/sprites_src/title/title_L2_clouds_fade2.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 19 | game/sprites_src/title/title_L2_clouds_fade3.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 20 | game/sprites_src/title/title_L2_clouds_fade4.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 21 | game/sprites_src/title/title_L2_clouds_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 22 | game/sprites_src/title/title_L3_downs.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 23 | game/sprites_src/title/title_L3_downs_fade1.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 24 | game/sprites_src/title/title_L3_downs_fade2.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 25 | game/sprites_src/title/title_L3_downs_fade3.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 26 | game/sprites_src/title/title_L3_downs_fade4.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 27 | game/sprites_src/title/title_L3_downs_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 28 | game/sprites_src/title/title_L4_fields.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 29 | game/sprites_src/title/title_L4_fields_fade1.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 30 | game/sprites_src/title/title_L4_fields_fade2.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 31 | game/sprites_src/title/title_L4_fields_fade3.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 32 | game/sprites_src/title/title_L4_fields_fade4.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 33 | game/sprites_src/title/title_L4_fields_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 34 | game/sprites_src/title/title_L5_verge.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 35 | game/sprites_src/title/title_L5_verge_fade1.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 36 | game/sprites_src/title/title_L5_verge_fade2.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 37 | game/sprites_src/title/title_L5_verge_fade3.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 38 | game/sprites_src/title/title_L5_verge_fade4.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 39 | game/sprites_src/title/title_L5_verge_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 40 | game/sprites_src/title/title_L6_road.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 41 | game/sprites_src/title/title_L6_road_fade1.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 42 | game/sprites_src/title/title_L6_road_fade2.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 43 | game/sprites_src/title/title_L6_road_fade3.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 44 | game/sprites_src/title/title_L6_road_fade4.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 45 | game/sprites_src/title/title_L6_road_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 46 | game/sprites_src/title/title_L7_fg.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 47 | game/sprites_src/title/title_L7_fg_fade1.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 48 | game/sprites_src/title/title_L7_fg_fade2.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 49 | game/sprites_src/title/title_L7_fg_fade3.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 50 | game/sprites_src/title/title_L7_fg_fade4.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 51 | game/sprites_src/title/title_L7_fg_flash.png | PASS | not a synergy ground | PASS | - | TS2-ART-A t_758934a8 (done) |
| 52 | game/sprites_src/ui/screens/ui_battle.png | PASS | not a synergy ground | PASS | - | UI-NES t_0df13164 (done) |
| 53 | game/sprites_src/ui/screens/ui_dialogue.png | PASS | not a synergy ground | PASS | - | UI-NES t_0df13164 (done) |
| 54 | game/sprites_src/ui/screens/ui_menu.png | PASS | not a synergy ground | PASS | - | UI-NES t_0df13164 (done) |

## 5. Every output file, pass or fail

54 output files, the same 54 paths as run 10. Column 3 is the scope the audit assigns, column 4 says whether that
scope is gated, column 5 is the fresh verdict with the pixels and size that break it, column 6 the rules, column 7
the owner. Source: `audit_records11.json` (scope, gate, ok, rules, offending_pixels) and `audit_local_v11.txt` for the
same 34 FAIL rows.

All 34 failing rows are the same 34 paths as run 10, checked path for path by `cmp11.py` this run, which reports
`fail set same: True`, `new failures: []` and `cleared: []`. Four rows' counts moved, and all four are by-products of
the party and enemy repaints that landed today: `output/bg_battle_preview.png` 2,525 to 2,484 px (`background_area`
117 to 119, the strip regenerated at 18:27:59), `output/chars_preview_3x.png` 645 to 438 (`background_area` 49 to 33,
the party battle sheets at 07:05:44), `output/enemies_preview.png` 112 to 0 px and `output/enemies_preview_3x.png`
55 to 0 px (`background_area` 5 and 4 gone, the enemy sheets at 17:23:16), both of which still FAIL on `grid x1`
(source: `cmp11.py`'s `moved audit rows`, and `ls -l` on those files).

| # | Output file | Scope | Gate | NES audit | Rules | Owner card |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | output/bg_battle_corridor_field_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 2 | output/bg_battle_corridor_fight_preview.png | frame | GATED | FAIL (256x240, 35,503 px) | background_area x7, palette x4 | no open card, Q: for gamedev (section 9) |
| 3 | output/bg_battle_corridor_text_preview.png | frame | GATED | FAIL (256x240, 47,791 px) | palette x4, background_area x3 | no open card, Q: for gamedev (section 9) |
| 4 | output/bg_battle_deck_night_field_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 5 | output/bg_battle_deck_night_fight_preview.png | frame | GATED | FAIL (256x240, 35,503 px) | background_area x5, palette x4 | no open card, Q: for gamedev (section 9) |
| 6 | output/bg_battle_deck_night_text_preview.png | frame | GATED | FAIL (256x240, 47,791 px) | background_area x5, palette x4 | no open card, Q: for gamedev (section 9) |
| 7 | output/bg_battle_preview.png | sheet | advisory | FAIL (520x232, 2,484 px) | background_area x119 | no open card, Q: for gamedev (section 9) |
| 8 | output/bg_battle_quay_dusk_field_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 9 | output/bg_battle_quay_dusk_fight_preview.png | frame | GATED | FAIL (256x240, 35,503 px) | palette x4, background_area x3 | no open card, Q: for gamedev (section 9) |
| 10 | output/bg_battle_quay_dusk_text_preview.png | frame | GATED | FAIL (256x240, 47,791 px) | palette x4, background_area x3 | no open card, Q: for gamedev (section 9) |
| 11 | output/bg_battle_wardroom_field_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 12 | output/bg_battle_wardroom_fight_preview.png | frame | GATED | FAIL (256x240, 35,503 px) | background_area x4, palette x4 | no open card, Q: for gamedev (section 9) |
| 13 | output/bg_battle_wardroom_text_preview.png | frame | GATED | FAIL (256x240, 47,791 px) | background_area x4, palette x4 | no open card, Q: for gamedev (section 9) |
| 14 | output/chars_preview_3x.png | sheet | advisory | FAIL (552x2076, 438 px) | background_area x33, grid x1 | no open card, Q: for gamedev (section 9) |
| 15 | output/drive_corridor_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 16 | output/drive_gantry_preview.png | frame | GATED | FAIL (256x240, 2 px) | background_area x1 | no open card, Q: for gamedev (section 9) |
| 17 | output/enemies_preview.png | sheet | advisory | FAIL (560x996, 0 px) | grid x1 | no open card, Q: for gamedev (section 9) |
| 18 | output/enemies_preview_3x.png | sheet | advisory | FAIL (464x772, 0 px) | grid x1 | no open card, Q: for gamedev (section 9) |
| 19 | output/env_ship_preview.png | sheet | advisory | FAIL (996x1092, 891 px) | background_area x67, grid x2 | no open card, Q: for gamedev (section 9) |
| 20 | output/gameover_preview.png | frame | GATED | FAIL (256x240, 61,440 px) | palette x4 | no open card, Q: for gamedev (section 9) |
| 21 | output/gate_textbox_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 22 | output/icons_preview.png | sheet | advisory | FAIL (884x804, 576,091 px) | background_area x613, palette x418, grid x2, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 23 | output/music_style_bible_preview.png | sheet | advisory | FAIL (1980x5844, 11,571,120 px) | background_area x9694, palette x61, grid x2, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 24 | output/nes_palette_preview.png | sheet | advisory | FAIL (768x824, 144 px) | background_area x8 | no open card, Q: for gamedev (section 9) |
| 25 | output/nes_ui_preview.png | sheet | advisory | PASS | - | no open card, Q: for gamedev (section 9) |
| 26 | output/percy_theme_preview_3x.png | sheet | advisory | FAIL (512x128, 65,536 px) | palette x292, background_area x137, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 27 | output/quay_block_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 28 | output/quay_office_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 29 | output/quay_tile_frame_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 30 | output/render2_demo_preview.png | sheet | advisory | FAIL (1920x2026, 3,889,920 px) | palette x538, background_area x186, grid x1, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 31 | output/sfx_preview_3x.png | sheet | advisory | FAIL (1560x1782, 2,779,920 px) | background_area x1303, palette x539, grid x1, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 32 | output/ship_deck_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 33 | output/southampton_sample_preview_2x.png | sheet | advisory | FAIL (1024x960, 4,456 px) | background_area x150 | no open card, Q: for gamedev (section 9) |
| 34 | output/title_car_preview.png | sheet | advisory | FAIL (400x744, 297,312 px) | background_area x28, palette x16 | no open card, Q: for gamedev (section 9) |
| 35 | output/title_preview_3x.png | sheet | advisory | FAIL (512x240, 122,880 px) | background_area x267, palette x32, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 36 | output/title_run_1.png | capture | advisory | FAIL (256x240, 2 px) | background_area x2, palette x2 | no open card, Q: for gamedev (section 9) |
| 37 | output/title_run_1_marks_overlay.png | capture | advisory | FAIL (256x240, 14,776 px) | background_area x39, palette x11, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 38 | output/title_run_1_nes.png | capture | advisory | PASS | - | no open card, Q: for gamedev (section 9) |
| 39 | output/title_run_1_nes_3x.png | capture | advisory | PASS | - | no open card, Q: for gamedev (section 9) |
| 40 | output/title_run_1_nes_3x_preview.png | capture | advisory | PASS | - | no open card, Q: for gamedev (section 9) |
| 41 | output/title_run_1_nes_diff.png | capture | advisory | PASS | - | no open card, Q: for gamedev (section 9) |
| 42 | output/title_run_2.png | capture | advisory | FAIL (256x240, 2 px) | background_area x2, palette x2 | no open card, Q: for gamedev (section 9) |
| 43 | output/title_run_reference_3x.png | capture | advisory | FAIL (256x240, 2 px) | background_area x2, palette x2 | no open card, Q: for gamedev (section 9) |
| 44 | output/title_theme_v2_preview_3x.png | sheet | advisory | FAIL (1920x2004, 3,847,680 px) | palette x530, background_area x181, grid x1, screen_colours x1 | no open card, Q: for gamedev (section 9) |
| 45 | output/title_ui_preview.png | sheet | advisory | FAIL (1920x784, 1,488,817 px) | background_area x301, palette x7 | no open card, Q: for gamedev (section 9) |
| 46 | output/ts2_art_a_preview.png | sheet | advisory | FAIL (224x168, 60 px) | background_area x7 | no open card, Q: for gamedev (section 9) |
| 47 | output/ts2_bigben_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 48 | output/ts2_world_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 49 | output/ts_exterior_preview_3x.png | sheet | advisory | FAIL (256x64, 172 px) | background_area x11 | no open card, Q: for gamedev (section 9) |
| 50 | output/ui_battle_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 51 | output/ui_dialogue_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 52 | output/ui_menu_preview.png | frame | GATED | PASS | - | no open card, Q: for gamedev (section 9) |
| 53 | output/westminster_sample_preview_2x.png | sheet | advisory | FAIL (1024x960, 4,000 px) | background_area x152 | no open card, Q: for gamedev (section 9) |
| 54 | output/winchester_sample_preview_2x.png | sheet | advisory | FAIL (1024x960, 7,140 px) | background_area x241 | no open card, Q: for gamedev (section 9) |

## 6. The composite PPU check on the four frames that ship

`tools/nes_composite_check.py` reads a finished frame as the player sees it: palette membership, four background
palette groups, sprite budget, 25 colours on screen. Run per frame on this PC at 18:42:19, one frame per invocation
(source: this section is the tool's own output for each of the four paths, `composite11_full.txt` in this card's
workspace).

| Frame | Colours on screen | Verdict |
| --- | --- | --- |
| output/nes_title_frame.png | 11 of 25, 4 of 4 palettes cover 240 blocks | PASS, 0 blocks violate |
| output/bg_battle_deck_night_frame.png | 7 of 25, 3 of 4 palettes cover 240 blocks | PASS, 0 blocks violate |
| output/bg_battle_corridor_frame.png | 9 of 25, 4 of 4 palettes cover 240 blocks | PASS, 0 blocks violate |
| output/ship_dialogue.png | 407 of 25, no palette covers them | FAIL, 70 blocks violate |

Two of those numbers are new since run 10 and both are explained by a ruling, not by drift. The deck frame reads 7
colours where run 10 read 8, which is card `t_34b1d96a`'s spend exactly: `bg2` moved from `$00 $10 $02` to
`$00 $30 $02` so the enemy's own triple is carried by the deck's background set, and that ruling says in terms "the
strip keeps its 29 unique tiles and drops from 8 colours to 7" (source: `composite11_full.txt`, and
`knowledge/PALETTE-RULINGS-2026-10-25.md` section 15.3). The corridor and deck frames on disk are dated 18:27:59 and
the title frame 2026-10-21 22:01:52, so the battle strips are the newest art on this page (source: `ls -l` on the
four paths).

`output/ship_dialogue.png` is unchanged and still not a 256x240 frame: it is a 768x720 capture read at scale 3, and
407 distinct colours means the picture was never quantised to the PPU palette (source: `composite11_full.txt`, the
`screen_colours` line). It is the dialogue screen that ships, and since card `t_1dc346b9` it is no longer named as a
ground for the ship cast (source: `data/scene_palettes.json`, audit entry 4 note). Its failure is the capture path's,
not a drawn frame's, so it is not counted as art debt on this page.

The two tools still disagree on the title frame on purpose: `nes_composite_check.py` PASSes it because some set of
four background palettes covers every 16x16 block, which is what the hardware allows, while `palette_synergy.py`
FAILs the same frame with 116 problems as the title set's frame and 210 as the ship set's frame, because it asks the
harder question of RULE 0 point 1 (do the frame's colours fit the set WRITTEN in `data/scene_palettes.json`), and
they do not (source: `composite11_full.txt`, and `ps_auto11_local.json` entries 5 and 7).

## 7. Trend versus the last run

The last run of this card is run 10, on 25 October 05:17 to 05:32: six entries, per pair 163, 11, 0, 0, 242, 135,
which is 551 problems, and an audit of 184 files with 34 failing, exit 1. This run returns nine entries, per entry
0, 16, 0, 0, 242, 36, 135, 88, 32, which is 549 problems, and the same local audit of 184 files with 34 failing, exit
1 (source: run 10's section 1 in `knowledge/PALETTE-PASS-LIST.md`, run 10's workspace `ps_auto10_local.json` and
`audit_records10.json`, and this run's `ps_auto11_local.json` and `audit_local_v11.txt`).

The two runs do not list the same entries, so the comparison below matches on (scene, ground, cast) and not on the
row number:

| Pair (scene / ground / cast) | Run 10 05:18 | This run 18:36 | Change | The rule or the tree that moved |
| --- | --- | --- | --- | --- |
| battle_corridor / bg_battle_corridor_frame / the party's four battle sheets | FAIL 163 | **PASS 0** | better by 163 | the four sheets were repainted into one reserved hero triple each (card `t_d5483a88`, price measured on `t_8c27208b` section 7.3), and the row was recast from three sheets including a walking sheet to those four (card `t_0949bd4e`, section 10). Sheets on disk at 07:05:44 |
| battle_corridor / bg_battle_corridor_frame / contact sheet | FAIL 11 | FAIL 16 | worse by 5 | `output/sprites_v2_sheet.png` is a by-product two generators write, regenerated at 18:12:01; ruling `t_c93a983f` section 8 makes the row advisory whatever it measures, and the two hosts disagree because the far side rebuilds it with a smaller roster (16 here, 6 on Pine) |
| battle_deck_night / bg_battle_deck_night_frame / the party's four battle sheets | PASS 0 | PASS 0 | none | the row was recast from the two sailor sheets to the party four (card `t_0949bd4e`, section 12) and still measures 0; what the recast cannot show is the deck block floor, 42 `body_ground` pairs at the party block, which is card `t_12c9b18f`'s and is not on this row |
| ship / ts_ship / the walking cast | PASS 0 | PASS 0 | none | the row now names the five walking sheets instead of the two sailor sheets (card `t_a6a7f436`, landed as commit `17c3660` at 18:42, after this run's measurement; the rebuild it cites is in `data/scene_palettes.json`, sha256 `11b9f257791e19cf...`, mtime 18:11:06, which is what this run read), and measures 0 both ways |
| ship / nes_title_frame / sailor_ow_v2 | FAIL 242 | FAIL 242 | none | the frame's 210 `palette_count` and the sailor's 16 `set_member`, 8 `white_blob` and 8 `body_ground`, rule for rule |
| title / nes_title_frame / the title cast | FAIL 135 | FAIL 135 | none | the frame's 116 `palette_count`, the logo's 10 `overlay_contrast` and 6 `set_member`, the car's 3 `set_member`, unchanged |
| southampton / southampton_sample_frame / the four walking sheets | not an entry | FAIL 36 | new row, new measurement | card `t_dec4e92c` wrote the row on 25 October and ruled the ground to be the composed spawn frame, not the five-group exterior atlas (section 16.1); every record is a walking body against the paving at 128,112 |
| westminster / westminster_sample_frame / the four walking sheets | not an entry | FAIL 88 | new row, new measurement | the same card; this is the worst town because hadrian's body and the paving are the same `$30` on the crop, which `invisible` x16 and `white_blob` x44 name |
| winchester / winchester_sample_frame / the four walking sheets | not an entry | FAIL 32 | new row, new measurement | the same card, the same paving |

The 2 problem fall decomposes exactly, and only one term is a repair of a drawing:

- 163 left with the corridor row, and this is the real repair in the window: the four party battle sheets were redrawn
  to the reserved hero triples, which is the change that took `percy_battle` from 78 to 0 and `hadrian_battle` from 53
  to 0.
- 5 arrived on the contact sheet, a by-product regenerated at 18:12:01.
- 156 arrived on the three town rows, which is a question that did not exist before card `t_dec4e92c` wrote it. It is
  not a regression and it is not nothing: those four sheets have to read on the paving the game draws.
- -163 + 5 + 156 = -2 (source: the two runs' per pair tables, `ps_auto11_local.json` and `ps_auto10_local.json`).

Neither half is like for like this run, and both tools moved for a reason this page can name:

- `tools/palette_synergy.py` moved, sha256 `bdcb0b6e5066004e...` at mtime 2026-10-25 06:15:24 against run 10's
  `eea5a2cfd6be3cfb...`, and `tools/nes_audit_all.py` moved, `20fabd83d9760657...` at 06:15:58 against
  `8936784a1ef61ff2...`. Both landed in commit `c8364f7` (card `t_c93a983f`), which prints the audit's universe and
  makes a party_cast scene read against its own four rows.
- `data/scene_palettes.json` moved from 6 audit entries to 9 and from 12 scenes with no gated row to 12 scenes with
  no gated row (sha256 `11b9f257791e19cf...`, mtime 18:11:06, committed as part of `17c3660` at 18:42). This is the
  change that added the three town rows and recast the corridor, deck and ship rows.
- `knowledge/ART-BIBLE.md` did not move: mtime 2026-10-25 04:55:55, sha256 `02767323d888b91c...`, the text run 10
  read.
- The art moved in six batches between the runs: the party battle sheets at 07:05:44, the enemy sheets at 17:23:16,
  the three town frames at 17:59:30, the contact sheet at 18:12:01, the four battle strips at 18:27:59, and commit
  `17c3660` at 18:42, which is after this run's local palette pass (18:36:30) but changes nothing it read
  (`data/scene_palettes.json` kept its 18:11:06 mtime and sha).

The tree is still moving under this page: `data/palettes/scene_battle_deck_night.json` and
`data/palettes/scene_battle_quay_dusk.json` are modified in the worktree since the run, and card `t_8ebcb489`
(MAKE-BATTLE-BG-OWNER, gamedev) and card `t_6e8ca42f` (PALETTE-SYNERGY-PARTY-CAST, builder) are `running` on exactly
these files. `t_454c1876` (PARTY-TOWN-READABILITY, builder) is `ready` on the towns. Nothing here is a verdict on
their work in progress (source: `git status --porcelain` on those two paths at 18:44, and `board11.py` against
`kanban.db` this run).

This page is committed by this run, where run 10 left it untracked: `git status --porcelain
knowledge/PALETTE-PASS-LIST.md` reported `??` through run 10 and holds no entry now, and the commit that carries it
is the one this card closes with (source: `git log --oneline -- knowledge/PALETTE-PASS-LIST.md` this run, one commit,
the testing lane's, 547 lines). A release gate that reads the commit rather than the worktree now sees the page.

## 8. Who fixes what

The board was read this run, not the map (query `board11.py` against `kanban.db` on board nayil-ops at 18:45):

| CARD-MAP row | Card | Board state | Owns |
| --- | --- | --- | --- |
| 4 | UI-NES t_0df13164 | done | the icons and UI sprites, 14 files, all 14 pass |
| 5 | SPRITE-1 t_b2acf67d | done | the character sprites, 2 of them carry synergy records (the four walking sheets are the towns card's) |
| 6 | BG-BATTLE t_1c5a8599 | done | the 4 battle backgrounds, all 4 pass |
| 12 | ENV-TILES t_4f58c88d | done | the ship and exterior tilesets, all pass |
| 16 | NES-PALETTES t_c8156a77 | done | the 12 scene sets in `data/scene_palettes.json`, which is what the nine entries are judged against |
| 17 | TS2-ART-A t_758934a8 | done | the title layers, the wordmark and the car, which are 19 of the title pair's 135 |
| 21 | ENEMIES-1 t_97871d4b | done | the 7 enemy sprites, all 7 pass the audit and none is on a synergy row |
| 15 | R15 t_7e72fe1c | done | the quay content row |
| 20 | R20 t_2924b0d7 | done | the five P0 sprite rows |
| not in the map | PARTY-CAST-REPAINT t_d5483a88 | done | the four battle sheets in one hero triple each, which is the 163 that left |
| not in the map | BATTLE-CAST-BUDGET t_8c27208b | done | the four hero triples and the price of drawing each sheet to its own |
| not in the map | BATTLE-CAST-ROWS t_0949bd4e | done | the corridor and deck rows' cast |
| not in the map | DECK-ENEMY-TRIPLE t_34b1d96a | done | the deck's `bg2` spend, which is the enemy's three colours and the 8 colours to 7 |
| not in the map | PALETTE-ARITHMETIC-AND-AUDIT-SCOPE t_c93a983f | done | the by-product rule and the audit's printed universe |
| not in the map | PARTY-FLOOR-BLOCK t_d64eb2a9 | done | the corridor and wardroom party blocks on `$0F` |
| not in the map | PARTY-WALK-SHEETS t_dec4e92c | done | the three town rows, which is the 156 that arrived |
| not in the map | PARTY-TOWN-READABILITY t_454c1876 | **ready** | the towns' paving against the party's bodies, all 156 |
| not in the map | Q: the ship's walking cast t_a6a7f436 | running (landed as `17c3660`) | the ship's four sprite rows, now the party's walking triples |
| not in the map | Q: sailor_battle's ground t_0b9c2faf | todo | where a battle sheet no room draws is judged |
| not in the map | PARTY-FLOOR-DECK t_12c9b18f | todo (builder) | the deck night and quay dusk party blocks, 42 `body_ground` pairs on the deck block, named in entry 3's exempt note |
| not in the map | MAKE-BATTLE-BG-OWNER t_8ebcb489 | running | the deck and quay dusk palette files, which are modified in the worktree now |
| not in the map | PALETTE-SYNERGY-PARTY-CAST t_6e8ca42f | running | how a party_cast scene is read, which is what the two exemptions say to remove |

The routing below is a `Q:` and not a new card. Every failing pair still sits on a directory whose card is closed,
and the two cards that touch those files are open on questions rather than on these failures.

## 9. Q: for gamedev

- `Q: the towns' four walking sheets do not read on the paving, and that is now 156 measured problems on three rows. All of them are the sheet's own body against the street surface under the spawn tile: bodies $30 for percy and hadrian, $31 for zander, $28 for konrad, paving $10 out of bg0_stone, and on westminster hadrian's body IS the paving on 8 of 8 frames, which is what invisible x16 names. Card t_454c1876 (ready, builder) carries two prices: move the walkable street off the light group, or repaint the four bodies. Which one, and if a repaint moves a triple does the town row solve of t_dec4e92c re-open with it?`
- `Q: two of the nine entries carry an exempt note that ends "remove this exemption when t_6e8ca42f lands", and both measure 0 today: the corridor row on the party's four battle sheets and the deck row on the same four. As the page stands, a reader cannot tell whether 0 means clean or means exempt. Does the exemption come off now, or after t_12c9b18f lands the deck block floor (entry 3's note measures 42 body_ground pairs at the party block, which this row does not carry)?`
- `Q: the title ground is 377 of the 549 problems (242 on the ship set, 135 on the title set) and no card on the board owns it. 0 of 12 scenes and 0 of 9 audit entries carry "gate": true, so --gate exits 0. Which is binding for the store submission: the frame as drawn, or the written set, and does any entry become gated before the build reads this page?`
- `Q: the sailor is still white on the title ground: sailor_ow_v2 carries set_member 16, white_blob 8 and body_ground 8 against the title frame. Does he ever stand in front of that frame in the shipping flow? If yes, either the entry pairs a sprite that does, or his body changes on that ground.`
- `Q: the wordmark still fails R1b: spr_pp_title_logo carries 10 overlay_contrast records (body $00 reads 1.69:1 and ink $0F reads 2.98:1 on ground $0A) and the car 3 set_member. The car's 15 overlay_contrast went to 0 with the near white $20 body on card t_1738de73, so the same treatment is available. Is the logo repainted, or does the sky under it change?`
- `Q: the contact sheet measures 16 here and 6 on Pine from make_characters_v2's smaller roster, and it is a by-product two generators write. Ruling t_c93a983f section 8 makes it advisory whatever it measures. Does it stay an audit entry at all, and if it does, which generator owns the name?`
- `Q: nes_audit_all.py exits 1 on this tree: 10 gated 256x240 preview frames fail (gameover, 4 text, 4 fight, drive_gantry). Are those previews part of the store submission, in which case they get quantised before the screenshot run, or are they internal and the frame scope should exclude output previews?`
- `Q: two audit rows now report FAIL with 0 offending pixels: output/enemies_preview.png and output/enemies_preview_3x.png fail on "grid x1" with background_area down to 0, because the enemy sheets were repainted at 17:23:16. Is the grid rule meant to carry no pixel count, or is that a reporting gap that hides whether the row is a real defect?`

## 10. Check list for this card

| Check | Result |
| --- | --- |
| palette_synergy ran on Pine with the real flag | yes, `--gate` (the card's `--all` does not exist): the cited run is `offload-autochecks-v11a-0.json`, sheet rebuilt by `make_characters_v2` first, 9 entries, 0 gated, 6 advisory, 0 not measured, per entry 0, 6, 0, 0, 242, 36, 135, 88, 32, `TOOL_EXIT=0`, `SHEET_EXIT=0`, 79.5 s, one upload attempt, no retry needed |
| nes_audit_all ran on Pine | yes, `--no-write`, `FAIL 153 file(s), 13 failing, 0 unmeasured`, exit 1, `offload-autochecks-v11b-0.json`, 133.3 s; its universe is the same 31 files smaller than the local one that run 10 named |
| the Pine result JSON was checked, as the card asks | yes, both job files read field by field: `status`, `started`, `finished`, `wall_seconds`, `upload_attempts`, `results_txt`, and the counts each prints |
| the local reproduction of the same tree | yes, `palette_synergy.py --gate` at 18:36:30 (549 problems, 9 entries, 0 gated, 6 advisory, exit 0) and `nes_audit_all.py --no-write` at 18:38:32 (184 files, 34 failing, exit 1), both in this card's workspace |
| the gamedev's own after table is reproduced | yes: `knowledge/PALETTE-RULINGS-2026-10-25.md` section 16.5 records 9 entries, 0 gated, 6 advisory, per entry 0, 14 to 16, 0, 0, 242, 36, 135, 88, 32, 549, and this run reads 0, 16, 0, 0, 242, 36, 135, 88, 32, 549 from its own run of the same command |
| nes_composite_check re-run | yes, all four frames at 18:42:19: 11, 7 and 9 colours PASS, `output/ship_dialogue.png` FAIL at 70 blocks and 407 colours |
| every frame and sprite listed, pass or fail | yes, 76 sprites, 54 backgrounds, 54 output files, 184 rows, the full `--list` inventory, no sampling |
| the failing rule named per failure | yes, columns 3 to 6 of sections 2, 3 and 5, rules as the tools name them, with one copied detail string per rule in section 2 |
| the owner card named per failure | yes, column 7 of sections 3, 4 and 5, and section 8, with the board state read from `kanban.db` this run |
| the trend against the last run | yes, section 7 matched on (scene, ground, cast) because the entries changed, with the 2 fall decomposed into three terms and both tool hashes printed |
| the tree did not move under the run | no, and it is named: six art batches between 07:05 and 18:27, commit `17c3660` at 18:42 after the local palette pass but not touching what it read, two scene palette files modified after the run, and three cards running on these files |
| the remote agent summary was not taken as evidence | yes: section 1's counts come from the JSON files and the local reproductions, and the Pine runs are cited only for what their `results_txt` prints |
| no key printed | yes, `keyscan11.py` over both job files: zero of PINE_SANDBOX_API_KEY, GEMINI_API_KEY, KAGGLE_API_TOKEN, bearer and sk-/pk-/ak- shapes; the only two 32 character hex runs are the jobs' own `turn_id` values (`turn_b01939f827b4018a2ed6e01f6a2e936f_1`, `turn_19ccf5b4a3c4747eee786253b396c354_1`), not keys |
| no em dash or en dash | yes, checked by search over this file |
