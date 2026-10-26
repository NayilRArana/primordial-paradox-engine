# SPAWN-HANDLES: WinError 6 was inherited handles, and the tests own it

2026-10-25. gamedev. Raised by audit from the 07:38 nightly at `73e6203`, which measured 3 failed, 1557 passed.

## The three reds, and that they are not content

    tests/test_drive_map.py::test_the_tree_carries_what_the_generator_writes
    tests/test_drive_map.py::test_a_tree_without_the_row_is_refused_and_a_write_restores_it
    tests/test_walk_ship_aboard.py::test_the_walker_tool_passes_and_names_the_trigger

All three ended in `OSError: [WinError 6] The handle is invalid` at `subprocess.py:1431`. No missing row, no
missing dialogue, nothing to write.

## The measurement that settled the trigger

Same two files, same interpreter, same tree:

    stdout redirected to a log      3 failed, 21 passed    (the runner's condition)
    stdout not redirected          24 passed

So the red is not the code under test. It is the environment the test was run in, and it only appears in the
condition the nightly actually uses. That is why it never showed up locally.

## The mechanism

`subprocess.py:1431` is inside `Popen._make_inheritable`, which calls `DuplicateHandle` on a parent handle. A
spawn that does not pass `stdin` asks subprocess to duplicate the parent's stdin handle. When the parent's stdout
has been redirected to a log and the capture machinery has replaced or closed the inherited handle, the duplicate
fails before the child exists, and the error surfaces as a failure of whatever the test was asserting.

## The ruling: the tests own it, the runner keeps its redirection

Audit left this open and floated the test side as its preference. It is the test side, on evidence and not
preference:

- 65 call sites in this project already pass `stdin` explicitly. The six that did not were the defect, not the
  convention.
- The runner's redirection is what makes the ledger readable. Making the runner stop redirecting trades a real
  capability for a workaround.
- A test's child process should never depend on the parent's handle table. Fixing it at the spawn makes every
  such test correct in every runner, including ones we have not written yet.

## What changed

Six spawn sites gained `stdin=subprocess.DEVNULL`:

    tests/test_drive_map.py            run_tool()
    tests/test_walk_ship_aboard.py     the walker spawn
    tests/test_event_log.py            the git call and the tool call
    tests/test_scene_palette_set.py    the git() helper

And `tests/test_spawn_handles.py` pins it: an AST scan of every `subprocess.run/Popen/check_output/check_call/call`
in the suite, failing if any leaves `stdin` unset, plus a second row asserting the scan actually finds at least 20
spawns so a scanner that matches nothing cannot pass silently.

## Verified

- The three reds, redirected: `24 passed`.
- The guard test: `2 passed`.
- Whole suite, stdout redirected to a log, the exact nightly condition: `1652 passed, 1 failed`, and
  `grep -c "WinError 6"` returns 0. The one red is
  `tests/test_make_env_ship.py::test_build_writes_the_five_outputs_the_card_names`, which passes alone in 8.58 s
  and whose file is modified by another lane in the working tree; it is not this change.

## Still open, and deliberately not fixed here

`tools/` carries thirteen unguarded one-shot spawns, found by the same scan:

    tools/art/make_ship_tiles.py:731     tools/capture_drive.py:354,381,387
    tools/check_readme.py:200            tools/check_ui_nes.py:199
    tools/drive_v2.py:375                tools/event_log.py:61
    tools/kaggle/r7_concepts/script.py:33,183,186
    tools/kaggle_r7.py:672               tools/kaggle_r7_gpu.py:108

They are the same shape one level deeper: a tool spawned by a test that itself spawns a child inherits the same
dead handle. They are not in this commit because each needs its own run to prove the edit harmless, and a
thirteen-site blind edit late in the day is how a green tool becomes a red one. They want a card with that list.
