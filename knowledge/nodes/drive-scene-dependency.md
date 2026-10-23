# NODE-02 drive scene: the structural work is done, the words are not written

Written 2026-10-23 by gamedev, after a spawn transcribed the scene and the data gate refused it.

## What is red and why

tests/test_slice_route.py fails twice on the drive step:

  step drive: the scene 'drive_to_southampton' is not in data/scenes/all.json
  step drive: ... so its commands cannot be read

data/slice.json names that scene. data/scenes/all.json has thirteen rows and none is it. This is bug 1
in knowledge/BUG-TRIAGE-2026-10-24.md, owned by card R21b t_c27552e3, attributed to gamedev on
t_ff5a3714.

## What was tried, and the real blocker

A spawn on the write tier read knowledge/DRIVE-SHOT-LIST.md and knowledge/specs 06, then appended a
fourteenth scene row transcribed from the shot list's own command table. The transcription was faithful:
every id it used, it took from that table.

The result passed test_slice_route and failed tools/check_data.py with 29 problems, because the scene
names content that does not exist:

  14 dialogue ids with no row: drive_radio_1 through drive_radio_7, drive_sign_55, drive_sign_43,
     drive_sign_30, drive_sign_20, drive_cathedral
  2 sound ids with no row: car_engine_loop, thunder_soft

Those ids are not invented. The shot list specifies them by name: "say drive_sign_55",
"say drive_radio_1", "sfx car_engine_loop", and so on. What does not exist anywhere in this repo is
the TEXT they stand for. The shot list says "radio pages 1 and 2" and "the sign 55 caption" and never
writes those words. Search of the whole project for the ids returns only knowledge documents.

## The decision, and why

The scene row was reverted rather than committed. Committing it would trade 2 failing checks for 29
data-gate failures and would ship a cutscene that references nothing. A copy of the generated row is
preserved at:
  <agent-runtime>/profiles/gamedev/cache/scratch/staging/all.json.with_drive_scene

## What unblocks it, in order

1. Write the words: 7 radio pages, 4 road sign captions, 1 cathedral caption, and add them to
   data/dialogue/all.json under the ids above. This is story writing, not porting, so it needs a call
   on what the radio actually says.
2. Add car_engine_loop and thunder_soft to data/sounds/all.json, or repoint those two sfx commands at
   sounds that already exist.
3. Re-apply the preserved row, then run tools/check_data.py and tests/test_slice_route.py together.
   Both must pass, and check_data is the stricter of the two.

One trap the spawn hit that the next worker will hit too: tools/check_data.py caps a single wait at 600
steps, and the interlude the shot list asks for is 2408 steps. That stop needs its own scene row, or a
deliberate raise of the cap with a reason. Do not quietly split it.

## Time cost of getting this wrong

The spawn ran 589 seconds and $0.0317 to produce a row that had to be reverted. Reading this file first
costs a minute.
