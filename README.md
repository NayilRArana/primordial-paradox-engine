# Primordial Paradox

A 256 x 240 NES-style adventure built in GameMaker, with Meta's models doing the art, the art review and the
dialogue judge, under a Python gate that enforces the drawing limits of the Ricoh 2C02 picture chip.

Two Greek houses, Kronos and Zeus, reincarnated on the M3 at night: the drive down to Southampton, a ship waiting at
the quay, and two encounters. The first is won with one command. The second is won by talking your way past a sailor,
and a model judges the line.

**Where this stands, stated plainly (2026-10-22).** This is a vertical slice under construction, not a finished game.
The title screen, the opening crawl, the ship room, the overworld walk and the dialogue box run today, from one build,
captured in the screenshots below. The drive, the arrival map, boarding, the two fights, save and game over exist as
specification, data and tests, and are scheduled in a fixed order (`ROADMAP-2026-10-23.md`). No Meta model call has
been made from this repository yet, so every line of text the game prints today is the written fallback. No ROM is
produced; this is a GameMaker build at native 256 x 240. The full audit, 22 subsystems scored out of 4 with the
evidence for each score, is `knowledge/HACKATHON-AUDIT-2026-10-22.md` (mean 2.2).

## What the demo shows

One scripted run, the same order every night, so drift shows up as a diff:

| Beat | State on 2026-10-22 | Evidence |
| --- | --- | --- |
| Title attract, then PRESS START, then NEW GAME | runs | live capture `output/title_run_1.png` |
| The opening crawl | runs, and hands off to the ship room | `output/crawl_mid.png`, log line "intro finished, starting the run in rm_pp_ship" |
| The drive to Southampton | shot list and generator, no room yet | `knowledge/DRIVE-SHOT-LIST.md`, card R21 |
| Arrival at the quay, the gate checkpoint | data and tests, no room yet | card ARRIVAL-MAP-2 |
| Walking the deck, doors, the dialogue box with a typewriter and choices | runs | footstep and text blip cues in the recorded run |
| Boarding, the first fight, the TALK fight | code and tests, no live capture yet | `tests/test_first_fight.py`, card R30 |
| The log save, game over, CONTINUE | save is tested, game over does not exist yet | cards R26 and R27 |

A recorded run exists at `output/demo/run_001.mp4` (73.5 s, 768 x 720, 60 fps). Its strict verifier still calls 5 of 7
sampled frames "not the game", so the recording is evidence, not yet the demo.

## The AI pipeline: what it does, and what it does not

The rule is ruling D5 of `knowledge/GAMEDEV-DECISIONS-2026-10-22.md`, and it is the reason a judge can run this on a
laptop with the wifi off.

**The shipped build makes no network call and holds no key.** No GML file in this project calls an HTTP, socket or URL
function (the only URLs in the game code are manual links inside comments), and the build compiles and runs with an
empty environment.

**Model output is baked, not called.** That is ruling D5. The bake runs once, before a build, and its answer lands in
`data/meta_bake.json` with the model name, the request hash, the creation time and the hand written fallback beside
it. The game reads that file and nothing else, and a bake that is missing or stale is meant to stop the build rather
than fall back quietly at runtime.

**Where it stands today, without rounding up.** The bake tool (card R29) does not exist yet, `data/meta_bake.json` is
absent, `game/datafiles/ai_cache` is empty, and no Meta call has been made from this repository. Every line the game
prints today is the written fallback. What is written and exercised against a mock backend is the client,
`tools/meta_client.py`, with `chat`, `chat_structured`, `vision`, `generate_image`, `edit_image` and `segment`.

| Job | Model | Entry point | Fallback when there is no bake |
| --- | --- | --- | --- |
| Concept art | muse-image-1.0 | `generate_image()` | a checked in concept |
| Silhouette | sam-3.1 | `segment()` | a threshold silhouette |
| Art review | muse-spark-1.3 with vision | `vision()` into `tools/eye_critic.py` | the checklist in `knowledge/ART-BIBLE.md` |
| Dialogue judge for TALK | muse-spark-1.3, structured output | `chat_structured()` behind the battle director | a fixed verdict table, so the fight never stalls |
| Ear review | any vision capable model on a spectrogram | `tools/ear_critic.py` | the scores in `assets/audio/` |

Modes are environment only: `PP_AI_MODE` set to `record` (default), `replay` or `live`. Keys are read from the
environment at call time and nowhere else, never printed, never written to a ledger, and a file whose name looks like
a credential store (`.env`, `auth.json`, anything with token, secret or credential in the name) is refused as input
instead of opened.

**What it does not do.** No model runs while a player plays. Nothing is generated on the judge's machine. No model
owns a pixel: whatever a model proposes still has to pass the palette and tiling checks before it can ship. The
critics score and report; a person decides.

## How to run

Windows, GameMaker LTS2026 (runtime 2026.0.0.23 tested), Python 3 with `jsonschema` (`tools/requirements.txt`), and
pytest for the suite. The one command, from the repository root:

    powershell -NoProfile -ExecutionPolicy Bypass -File tools\run.ps1

It copies the data mirrors, checks every data file against its schema, regenerates and checks the project file, runs
the clean room and provenance gates, validates the scene palettes, then builds and launches with Igor. Exit codes: 0
launched, 1 a gate failed and nothing was built, 2 GameMaker missing or unlicensed, 3 Igor returned an error. Flags:
`-SkipChecks` skips the Python gates, `-Compile` builds and stops. `tools\run.vbs` runs the same script with no
console window.

The gates on their own, in the order the roadmap runs them:

    python tools/check_data.py          content against data/schemas/
    python tools/check_cleanroom.py     nothing traced, copied or decompiled from a published game
    python -m pytest tests -q           the suite
    python tools/nes_audit_all.py       every art file against the picture chip rules

**Landing a cue.** A cue is landed only when its source `.ogg` under `assets/audio/<asset>/` and the regenerated
`game/PrimordialParadox.yyp` that names it are in ONE commit. Stage both, or stage neither. A commit that carries the
source without the entry names no stream that a fresh checkout can build, and a commit that carries the entry without
the source declares a stream it does not carry; six commits in the week of 2026-10-19 were one of those two shapes.
The commit gate enforces this on every primordial-paradox commit, asset-only commits included, by running
`python tools/check_build_inputs.py --staged`, which reads the INDEX rather than the working tree because a commit
is the index. It refuses with one `UNPAIRED IN COMMIT` line per unpaired file. The same command run by hand prints
the same thing, so there is no separate ritual to remember: `python tools/check_build_inputs.py` covers what is
committed, `--staged` covers what this commit is about to carry.

Run on this machine on 2026-10-22, pasted as they printed:

    sync_data.py        exit 0  copied 0, removed 0, 65 unchanged
    sync_art.py         exit 0  mirrored 21 sound effects, 101 animations, index current
    check_data.py       exit 0  check_data: all files pass
    gen_project.py      exit 0  wrote game/PrimordialParadox.yyp, 29 resources, 227 included files
    check_project.py    exit 0  check_project: project graph and disk agree
    check_cleanroom.py  exit 0  341 files, 26 names, 12 phrases, 35 GML modules, 0 awaiting review
    check_provenance.py exit 0  26 modules, every one mapped to an entry
    scene_palette_set.py validate   exit 0  PASS, 12 scenes, 4 hero palettes
    palette_synergy.py --gate       exit 0  6 entries, 0 gated failures, 6 advisory
    nes_audit_all.py    exit 0  PASS, 160 files, 24 failing (every one an advisory contact sheet or window capture)
    Igor build          exit 0  "Igor complete.", sc=536, ob=3, ro=3, da=227, artifact rebuilt

The suite is the one gate that is not green today: `python -m pytest tests -q` reports 905 passed, 15 failed and 1
skipped in 363 s, run at 19:53 on 2026-10-22. All 15 are one class of red: a generated artefact (a sprite, a window
layout, a palette set, the project file) does not match what the script that generates it produces right now, because
other lanes are rebuilding that art today. The nine checks that gate a build are green, which is why the build above
ran.

On a machine short of memory, the suite and the checks run on a sandbox instead; the wrapper lives outside this
repository.

## The tools

| Tool | What it does |
| --- | --- |
| `tools/check_data.py` | every JSON file against its schema in `data/schemas/`, with the failing field named |
| `tools/check_project.py` | the GameMaker project graph against the files on disk |
| `tools/check_cleanroom.py` | no study reference, no foreign name, no foreign phrase, every module reviewed |
| `tools/check_provenance.py` | every GML module maps to a provenance entry with its sources |
| `tools/nes_check.py` | palette membership, the 8 x 8 tile grid, 3 opaque colours a sprite tile, 4 a background area |
| `tools/nes_audit_all.py` | every asset, sheet and capture, with a verdict and the pixel count of each fix |
| `tools/palette_synergy.py` | whether a sprite separates from the ground it stands on, measured, not judged |
| `tools/scene_palette_set.py` | one palette per scene, chosen and validated before anything is drawn |
| `tools/meta_client.py` | the only file that knows the model HTTP shapes; the bake tool lands with card R29 |
| `tools/eye_critic.py`, `tools/ear_critic.py` | the model critics that score a frame or a spectrogram |
| `tools/render_chip.py`, `tools/arrange.py` | the chip audio renderer and the composition engine |
| `tools/osm_to_map.py` | map geometry from OpenStreetMap, with the ODbL attribution kept in the build |

## Screenshots

Three frames that exist today, each from a real run of this build:

- `output/title_run_1.png` (784 x 759, captured 19:13 on 2026-10-22): the title screen at three times scale, with the
  menu open.
- `output/crawl_mid.png` (768 x 720): the opening crawl mid run, four colours.
- `output/bg_battle_deck_night_frame.png`: one of the four battle backgrounds, drawn and gated, waiting on the card
  that wires the strips into the fight.

## Licence

The licence position for this repository is stated in `LICENCE` at the root: all rights reserved today, with the
choice of an outbound grant left to the holder and still open.

What does bind today, and is recorded rather than assumed:

- **Engine.** GameMaker LTS2026 by YoYo Games, used under its own licence.
- **Libraries.** None imported. The rule for any that is: MIT or Apache 2.0 only, no copyleft anywhere near the
  game, and the licence file read before use, never a badge. `knowledge/LICENSES.md` records the ten repositories
  considered with the exact copyright line found in each file, including the one where a detector said "unlicensed"
  and the file said Apache 2.0.
- **Font.** Press Start 2P by CodeMan38, SIL Open Font License 1.1 with a reserved font name, shipped with its
  notice at `knowledge/licences/PressStart2P-OFL.txt` and byte for byte identical to upstream.
- **Geography.** Map geometry from OpenStreetMap, ODbL, attribution kept inside the build.
- **Music and sound.** Original, rendered from our own recipes. No sample pack, no soundbank, no commercial chip
  instrument is redistributed.
- **Credits.** `CREDITS.md` is the row per attribution obligation: engine, font, map data, our own work, and the ten
  libraries that were read and not imported.
- **Licence file.** `LICENCE` at the root, carrying the copyright notice, the terms that hold today, and the
  third-party obligations a grant cannot override.

## Provenance and clean room

Everything here was written for this project. Published games were studied as behaviour and rules, never traced,
transcribed or decompiled; `knowledge/PROVENANCE.md` says exactly what was studied and what was never copied, and
`tools/check_cleanroom.py` enforces it on every commit. No third party code, art, dialogue or music was read,
retyped or reused. Work on this repository was done by Nayil with his agent lanes (builder, testing, musician,
research, audit, critics) under his direction, and every commit names the card that produced it.

## Links

- Build order and the gate: `ROADMAP-2026-10-23.md`
- The decisions the build obeys: `knowledge/GAMEDEV-DECISIONS-2026-10-22.md`
- What was built when, and what the hackathon window adds: `knowledge/BUILD-TIMELINE.md`
- The whole project audit: `knowledge/HACKATHON-AUDIT-2026-10-22.md`
- The art audit, regenerated by its own tool: `knowledge/NES-AUDIT.md`
