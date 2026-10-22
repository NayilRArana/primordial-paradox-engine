# Open-source GameMaker references, licences first

Rule: nothing enters the project until its licence file has been read and recorded here. No download has been made as
of 2026-10-19. When we do import a library, we copy its licence text into game\licences\<name>.txt and record the exact
commit or release tag here. MIT and Apache 2.0 only. No copyleft (GPL, AGPL, LGPL) anywhere near the game, because a
GPL library would force the whole game open. No licence, no use, even if the code looks useful.

Every licence below was read from the repository's own licence file or license sidebar on 2026-10-19.

## How each licence was confirmed (verification pass, 2026-10-19)

Method: the raw licence file was fetched from each repository and its header read, and the repository metadata was
checked through the GitHub API (which reports an SPDX identifier) or the Codeberg API. Nothing was cloned and no
package was downloaded. Results, with the exact holder line found in the file:

| Library | Licence file header, as read | What the API detector said |
| --- | --- | --- |
| Scribble | MIT License, Copyright (c) 2023 Julian Adams | MIT |
| Input | MIT License, Copyright (c) 2023 Julian Adams (codeberg.org/offalynne/Input, LICENSE) | MIT |
| PictureFrame | MIT License, Copyright (c) 2024 Juju Adams | MIT |
| BeadyEye | MIT License, Copyright (c) 2024 Juju Adams | MIT |
| gmdialogue | MIT License, Copyright (c) 2026 danielpancake (LICENSE.txt) | MIT |
| crispy | MIT License, Copyright (c) 2020 Brent Frymire | MIT |
| GMAssert2 | MIT License, Copyright (c) 2019 Dickson Law | MIT |
| GM-TestFramework | Copyright 2021-2022, YoYo Games Ltd. Licensed under the Apache License, Version 2.0 | NOASSERTION |
| TurboGML | MIT License, Copyright (c) 2022 Mozart Junior (FoxyOfJungle) | MIT |
| cbDataGUI | The MIT License (MIT), Copyright (c) 2017 Cem Baspinar | MIT |

Two notes on that table, both worth keeping:

- GM-TestFramework is the one case where the detector and the file disagree. GitHub's detector reports NOASSERTION,
  which would read as "unlicensed, do not touch". Its own LICENSE file is the Apache License 2.0 text. The file is the
  authority and the row above follows the file. This is exactly the reason the rule at the top of this document says
  to read the licence, not a badge.
- gmdialogue's copyright year is 2026, not an earlier year. Recorded so nobody "tidies" it back to a guess.

None of the ten repositories was archived as of 2026-10-19, so none is a dead dependency yet. That will be re-checked
when a library is actually about to be imported, because an archived MIT library is still safe to use, but a fork
becomes the better link.

## Approved for use if we need them

| Library | What it does | Licence | Link | What we may reuse |
| --- | --- | --- | --- | --- |
| Scribble | Text renderer built for dynamic effects and dialogue text | MIT, Copyright (c) 2023 Julian Adams | https://github.com/JujuAdams/Scribble | The library as a dependency, with its copyright notice kept. Reference for how text effects can be structured. |
| Input | Comprehensive cross-platform input, now maintained by offalynne | MIT, Copyright (c) 2023 Julian Adams | https://codeberg.org/offalynne/Input | The input abstraction as a dependency. Our own input spec stays ours; we would use it as the device layer under it. |
| PictureFrame | Camera, view, GUI, window and application surface calculator | MIT, Copyright (c) 2024 Juju Adams | https://github.com/JujuAdams/PictureFrame | Integer scaling and viewport maths as a dependency, if our own 40 line scaler proves slower to write than to import. |
| BeadyEye | Camera helper with modes and screen shake | MIT, Copyright (c) 2024 Juju Adams | https://github.com/JujuAdams/BeadyEye | Camera follow and shake as a dependency, or as a design reference for our own camera spec. |
| gmdialogue | Dialogue system that applies command blocks to displayed text, GameMaker 2.3+ | MIT (repository sidebar states MIT License) | https://github.com/danielpancake/gmdialogue | Design reference only for a command block syntax. Our dialogue engine is written from our own spec, so this is a "read for ideas", not an import. |
| crispy | Unit testing framework in GML | MIT, Copyright (c) 2020 Brent Frymire | https://github.com/bfrymire/crispy | Test assertions and runner as a dependency, or as a comparison against the framework we write. |
| GMAssert2 | Assertion library for debugging and automated tests | MIT, Copyright (c) 2019 Dickson Law | https://github.com/dicksonlaw583/gmassert2 | Assertions as a dependency. |
| GM-TestFramework | YoYo Games' own test automation framework showcase | Apache 2.0, Copyright 2021-2022 YoYo Games Ltd | https://github.com/YoYoGames/GM-TestFramework | Reference for what the vendor itself expects a GML test harness to look like. Apache 2.0 obliges us to keep the notice and state changes. |
| TurboGML | General purpose GML function collection | MIT, Copyright (c) 2022 Mozart Junior (FoxyOfJungle) | https://github.com/FoxyOfJungle/TurboGML | Individual small helpers if a need appears. Not a base to build on. |
| cbDataGUI | In-game GUI for editing instance variables, debug tooling | MIT, Copyright 2017 Cem Baspinar | https://github.com/aft/cbDataGUI-GML-Library | Debug panels for our debug build flag, if writing our own is not cheaper. |

## Rejected, and why (so nobody re-proposes them)

| Thing | Why not |
| --- | --- |
| Any Undertale or Deltarune decompilation, its data files, its strings, its "engine" clones | COPYING ONLY. Nayil's order of 2026-10-19 permits reading a decompilation to understand architecture (see PLAN.md section 1 and knowledge\FOX-STYLE.md). What stays forbidden is expression: their code text, a reworded copy of it, their sprites, fonts, sounds, music, data tables, names or dialogue, and any module whose structure traces one to one onto one of their objects. Study copies live under knowledge\study\, are gitignored and are never shipped. |
| Marketplace assets with a "no redistribution" or "single project" licence we have not read | Some paid assets forbid reuse in a source-visible repo. Nothing is bought in this lane anyway; a purchase is Nayil's decision. |
| Projects with no licence file | Absence of a licence means all rights reserved, not "free to use". |
| GPL or AGPL GML libraries | They would force the game to be GPL. |
| The FMOD binding (FML, MIT) | The binding is MIT but FMOD itself has its own commercial licence. GameMaker's built-in audio is enough for a 20 sound 8-bit game. |

## Fonts and reference art (open licence only)

The rule for a font is the project's rule for everything else: read the licence file, record it here, keep the text.
A font used for on-screen text is a dependency just like a library, and a bitmap font that ships inside a sprite
sheet has to be redistributable.

| Asset | Licence, as read in the file | Source | Verified |
| --- | --- | --- | --- |
| Press Start 2P, by CodeMan38 (cody@zone38.net), Copyright 2012 The Press Start 2P Project Authors | SIL Open Font License 1.1, with Reserved Font Name "Press Start 2P" | https://github.com/google/fonts/blob/main/ofl/pressstart2p/OFL.txt | 2026-10-21, raw file fetched and diffed byte for byte: `knowledge\licences\PressStart2P-OFL.txt` is identical to upstream, sha256 `705960c3281a5765ecc0b59bd4ed7ca59eed165748076bc2fc3e8fdbfeb944b0` |

Why this is allowed: the OFL 1.1 permits use, embedding and redistribution, including inside commercial software, as
long as the copyright notice and the licence travel with it. It does not permit selling the font on its own, and it
forbids using the Reserved Font Name for a modified version. Rasterising the glyphs at their design size of 8 px into
our own sprite sheet is use of the font, not a modified font, so the sheet may ship with the game and
`knowledge\licences\PressStart2P-OFL.txt` is the notice that travels with it. `tools\art\pressstart2p_font.py` reads
the upstream TTF in `assets\fonts\`, never redraws it, and fails if a glyph does not fit the 8x8 cell.

## Attribution plan

When a library is imported:
1. Its licence text goes to game\licences\<name>.txt, unmodified.
2. This table gains the exact commit hash and the date imported.
3. The game's credits screen lists the library name and its author, even where the licence does not require it.
4. Nothing is copied into our own source: we import the library as an asset package or vendor folder and call it.

## What we are deliberately writing ourselves

Dialogue engine, cutscene runner, battle director, dodge arena, bullet recipe player, route ledger, save system,
state machine, camera scaler, 8-bit palette shader, data checker. Reasons: they are the heart of the game's feel, our
specs already define their numbers, and a borrowed engine would drag its own assumptions (and its licence) into the
core. The libraries above are candidates only for input, text rendering, scaling and test assertions, which are
solved problems.
