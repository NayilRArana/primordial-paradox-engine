# Command line build with Igor (what is needed once GameMaker is installed)

Source: https://manual.gamemaker.io/monthly/en/Settings/Building_via_Command_Line.htm (checked 2026-10-19), and the
Long Term Support copy of the same page, https://manual.gamemaker.io/lts/en/Settings/Building_via_Command_Line.htm
(checked 2026-10-19). The two copies are not identical: /jsonErrors and the verbose flag /v are listed in the LTS
option table and are absent from the Monthly page, so those two rows come from LTS. Everything else below appears on
both.

## The hard precondition

The manual states it twice, in a note at the top and again in the CI setup list: you must have logged into the IDE
with an account at least once before command line building works. Igor is not a standalone compiler. Nothing in this
document can be exercised until Nayil installs GameMaker, launches it, and logs in. That is his step, not ours.

Building executables from the command line also requires the licence file: either the one the IDE wrote, or an access
key turned into a licence. The access key route is documented as: gamemaker.io/account/access_keys, generate a key,
then run `igor runtime FetchLicense -ak=<key> -of=<licence path>` and pass the result with /lf. We do not do this: an
access key is a credential, and credentials are Nayil's.

## Where Igor lives

- Windows: C:\ProgramData\GameMakerStudio2\Cache\runtimes\runtime-[version]\bin\igor\<OS>\<architecture>\
- macOS: /Users/Shared/GameMakerStudio2/Cache/runtimes/runtime-[version]/bin/igor/osx/<architecture>/

So the run script must discover the runtime folder rather than hardcode a version string.

## Options we will use

| Option | Meaning |
| --- | --- |
| /project=<path to .yyp> | the project file, quoted because our path holds spaces |
| /rp=<runtime root> | the runtime folder |
| /uf=<user folder> | user folder for licence lookup, %appdata%\GameMakerStudio2\<user>_<number> |
| /lf=<licence.plist> | direct path to the licence instead of /uf |
| /cache=<dir> | build cache directory (defaults to \cache in the working directory) |
| /temp=<dir> | temp directory (defaults to c:\temp) |
| /config=<name> | build configuration, default "Default" |
| /runtime=VM or YYC | output type, default VM |
| /of=<output name> | output executable name without extension |
| /tf=<target file> | the actual ZIP or installer file name |
| /j=<N> | number of CPUs |
| /launch | launch the built game, same as Create Executable and Launch |
| /v | more verbose output |
| /jsonErrors | errors as a JSON struct on standard error |

## Platform commands

The manual documents the command after a double dash. For Windows the ones we need:

- `Igor.exe /uf=... /rp=... /project=... /cache=... /temp=... -- Windows Run` builds and runs.
- `-- Windows Compile` builds without running.
- `-- Windows PackageZip` with /of and /tf produces a zip package.
- Adding `/runtime=YYC` before the double dash switches to the compiled runner.

## Testing target

Igor also runs a test set: `Igor.exe Tests RunTests <dir or tests.json>`, with /timeout (default 120 seconds) and
/waittime (default 30 seconds). A project passes a plain test if the runner is still alive after the wait time. A
tests.json can list per project entries with name, path, target, command, timeout and waittime.

DECISION for PP: we do not build our GML unit tests on Igor's Tests command. It answers "did the game start and stay
alive", which is a smoke test, not a unit test. We use it as the integration gate (does the project compile and run),
and our GML unit tests are run inside the game from a debug-only room, writing a plain text result log that a Python
checker reads. That keeps the unit gate runnable on a machine with no GPU window and gives a per-test line.

## What tools\run.ps1 must do

1. Find the runtime folder under C:\ProgramData\GameMakerStudio2\Cache\runtimes\ (newest runtime-[version] wins,
   overridable by an environment variable PP_RUNTIME).
2. Find Igor under that runtime, with the OS and architecture subfolders.
3. If Igor, the runtime or the licence is missing, print one clear plain sentence saying GameMaker is not installed
   or not logged in yet, and exit with a non-zero code without opening anything.
4. Otherwise run the Run command with the project path quoted, a cache dir inside the project's build folder, and the
   log tee'd to build\last-build.log. No visible console window for Nayil: the script is started hidden and the game
   window is the only thing he sees.
5. On failure, print the last 20 lines of the Igor output and the path to the full log.

Verification status: VERIFIED 2026-10-25. GameMaker LTS2026 is installed on this PC (card t_4848159e measured it):
`C:\Program Files\GameMaker-LTS2026` is version 2026.0.0.23, the runtime is
`C:\ProgramData\GameMakerStudio2-LTS2026\Cache\runtimes\runtime-2026.0.0.23` with `Igor.exe` under
`bin\igor\windows\x64\`, and the licence folder `tools\run.ps1` resolves is
`%APPDATA%\GameMakerStudio2-LTS2026` (the product folder that holds `um.json`, because the LTS line keeps no named
account folder). Measured that day: `tools\run.ps1 -SkipChecks -Compile` returned 0 with `Igor complete.` and wrote
`output\PrimordialParadox\PrimordialParadox.win`, and `python tools\integration_build.py` printed
`BUILD PASS: Igor compiled the project and launched the game`, exit 0.

One measured detail for the Run command: Igor WAITS for the launched game to exit, so `-- Windows Run` does not return
while the window is open, and `tools\integration_build.py` (which calls run.ps1 without `-Compile`) therefore blocks
until the game closes. The window title is `Primordial Paradox` and the process is `Runner.exe`. A command line check
that only wants "did it compile and launch" can either pass `-Compile` or close the window when it is up.
