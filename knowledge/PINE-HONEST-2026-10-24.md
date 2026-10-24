# PINE-HONEST: two Pine cards of every three were measuring an import failure

Card t_84fe63ff, 2026-10-24. gamedev.

## The defect

`tools/play_demo.py` imported `capture_title` at module level, and `capture_title.py:39` imported
`ctypes.wintypes`. `pp_launch.py:41` imported it too. Off Windows that import fails, so on Pine the
demonstration tools could not be imported at all, and every red that the suite produced there was
classified in the shadow of that failure.

Measured on 2026-10-24: 21 Pine reds, 19 of which pass on Windows.

Worse than a broken import: it is a broken import that produced a plausible verdict. A reader saw
21 failures and a classification note, not a traceback.

## The fix

Two guarded imports, one refusal each:

- `tools/capture_title.py`: `WINDOW_PRIMITIVES = sys.platform == "win32"`, with `ctypes.wintypes`
  imported only when true, and the module-level `ctypes.windll.user32`, the DPI block and
  `ctypes.WINFUNCTYPE` now behind the same guard. Off Windows `user32` and `EnumWindowsProc` are None.
- `tools/pp_launch.py`: the same guard on the same import.
- `tools/play_demo.py` `run_demo`: refuses with the message `play_demo: unavailable on this platform`
  and returns `pp_launch.EXIT_REFUSED`, which is 4.
- `tools/capture_title.py` `main`: refuses the same way.

Exit 4 is not a new convention. `tools/idle_check.py:48` defines `EXIT_REFUSED = 4` and its header
explains it is 4 and not 3 because 3 is the watchdog's code in this harness.

The refusal lives in `run_demo` and not at import on purpose: `--check` and `--dry-run` inspect an
existing file and must keep working on a machine that cannot show a game.

## Proof, both directions

Probe at `profiles/gamedev/cache/scratch/probe_pine_honest.py`:

```
branch 1, this machine
  sys.platform        : win32
  capture_title flag  : True
  pp_launch flag      : True
  user32 object       : WinDLL
branch 2, primitives absent
  import succeeded    : yes, which is the fix
  capture_title flag  : False
  pp_launch flag      : False
  user32 object       : NoneType
  play_demo run_demo  : returned 4 | play_demo: unavailable on this platform
  capture_title main  : returned 4 | capture_title: unavailable on this platform
  refused, not passed : True
```

Windows behaviour unchanged: 129 passed across `test_capture_title.py`, `test_play_demo.py`,
`test_capture_quiet.py`, `test_capture_quiet_impl.py`, `test_first_fight_capture.py`,
`test_talk_fight_capture.py`.

## The cards whose verdicts were never measured

These closed on Pine numbers that this defect was producing. Their verdicts are UNMEASURED and must be
re-run, not inherited. Named as the card requires:

- t_cb1f931b TEST-TRIAGE-PINE, testing. It sorted 49 Pine failures into windows-only, zip gaps and
  real regressions. Its windows-only bucket was very likely right in substance and cannot be trusted in
  detail until re-run against this fix.
- t_fa895ddf PINE-CHECKS, testing. Palette and NES checks over every frame through Pine.
- t_dacb50c7, t_1ed727b8, t_37657207, t_e7c9dcc2, t_9a18f2e9, t_1649d513, t_f6f73680, AUTO-GATE-GREEN,
  testing. Seven cards, each of which classified Pine failures and raised fix cards for the ones it
  called real.
- t_e87e71e6, t_d8f13f33, t_64d39815, AUTO-PINE-CHECKS, testing. Three cards, same exposure.
- t_a14fbdd3 MUS-V5, musician. Used Pine side checks on the title theme; its audio verdicts stand on the
  rendered files, but its Pine column does not.

Not affected, checked and named so nobody re-opens them: t_429b26d4 PINE-SKILL and t_7e5ece0f
PINE-RESEARCH are client and research cards with no suite verdict, and t_753fb388 PINE-PLACES-DIGEST
is a research digest.

## What to do with a not-measured result

Do not treat 4 as a pass and do not treat it as a failure. Re-run on Windows, or record the row as not
measured. The one thing this project must not do again is convert "I could not measure" into a green.
