# Credits, and every attribution this repository owes

Written 2026-10-23 by card t_4fefed64 (LICENSE-AND-CREDITS, blocker 8 of knowledge/HACKATHON-AUDIT-2026-10-22.md).
This file is the one place that answers "who else's work is in here, and what does their licence require me to say".
It is read by a judge, by a redistributor and by the next contributor, so it states obligations as they are today, not
as they were planned.

The outbound licence is `LICENCE` at the root, beside this file. Today it records all rights reserved; the holder has
not chosen a grant yet, and when he does only that file's section 2 changes. Nothing on this page changes with it,
because nothing on this page is ours to licence.

## 1. The rule this file is kept under

1. One row per attribution obligation. A licence that requires a line gets its line here, verbatim, even if the thing
   it covers is not yet distributed. A row with no required line says so.
2. A row names where the obligation travels in the build, not just where it is recorded in the repository. A notice
   that sits in `knowledge/` is not in the game bundle: `tools/sync_data.py` mirrors `data/` into
   `game/datafiles/`, and nothing else ships.
3. No obligation without a row. `grep` of the tree for a third party's name, or for "licence", must land on this
   page; if it lands on a file that does not point here, this page is wrong.
4. Nothing is imported without a row first. `knowledge/LICENSES.md` holds the longer record: each library's licence
   header as it was read in the file, the API's own detector verdict, and the link. This page is the summary that a
   reader outside the project can use on its own.

## 2. What this build actually ships

| What | Whose | Licence | Required line, verbatim | Where it travels in the build |
| --- | --- | --- | --- | --- |
| GameMaker runtime and compiler, LTS2026 | YoYo Games Ltd | YoYo Games' own licence, not open source, not distributed here | GameMaker LTS2026, by YoYo Games Ltd, used under YoYo Games' own licence. | `data/credits.json`, screen row "GAMEMAKER LTS2026" and "BY YOYO GAMES LTD". The engine itself is not in the repository and is not redistributed with the source. |
| Font, Press Start 2P, rasterised into `spr_pp_font8` and the title wordmark | Copyright 2012 The Press Start 2P Project Authors (cody@zone38.net), Reserved Font Name "Press Start 2P" | SIL Open Font License 1.1 | Copyright 2012 The Press Start 2P Project Authors, with Reserved Font Name "Press Start 2P". Licensed under the SIL Open Font License, Version 1.1. | The full licence text, byte for byte as published, is carried inside the build in `data/credits.json` (`notices`), and kept in the repository at `knowledge/licences/PressStart2P-OFL.txt`. The screen shows the holder line in the font's own alphabet. |
| Street geometry derived from OpenStreetMap data (`data/maps/southampton_sample.json`, `westminster_sample.json`, `winchester_sample.json`, `data/maps/osm/`, `data/osm_cache/`) | (c) OpenStreetMap contributors | Open Database Licence (ODbL) 1.0 | (c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0, https://www.openstreetmap.org/copyright | The line is a value inside every derived map file (`source.attribution`), inside each Overpass extract (`osm3s.copyright`), in `data/credits.json` (`notices`), and on the credits screen in the font's alphabet. Section 3 below is the same line, byte for byte. |
| Music, sound effects, art, sprites, tiles, palettes, code, dialogue, data tables | Nayil Arana, with his agent lanes under his direction | His own work, copyright as in `LICENCE` | Copyright (c) 2026 Nayil Arana. All rights reserved. | The credits screen, first rows. Every commit names the card that produced it, so authorship is traceable from `git log`. |

Nothing else is shipped. There is no audio sample pack, no soundbank, no commercial chip instrument, no third party
sprite, tile or font beyond the one font above, no stock image, and no imported GML library. The music and the effects
are rendered by this project's own tools from its own recipes (`data/music_recipes.json`, `data/drum_patterns.json`,
`data/palette_recipes.json`, `tools/sfx.py`).

## 3. The ODbL line, byte for byte

This is the line, and it must stay byte identical to the quotation in `knowledge/ARRIVAL-CONTENT.md` section 1:

    (c) OpenStreetMap contributors, Open Database Licence (ODbL) 1.0, https://www.openstreetmap.org/copyright

What that licence asks of this project, in plain terms, because a row that only copies a line is not an audit:

- Attribution to OpenStreetMap contributors, in the manner above, on anything built from the data. That is the map
  data files, the credits screen, the game build and the demo video's credit card
  (`knowledge/VIDEO-PLAN.md`, `knowledge/SUBMISSION-KIT-2026-10-24.md` both carry the same line).
- Share alike on the derived database, not on the game's own story, art or code. The derived map data is the tile
  grids rasterised from the extracts, and they are in this repository under ODbL. The story text, the characters, the
  art and the GML are not derived from the database and are not covered by it.
- No suggestion that OpenStreetMap endorses this game, and no reuse of the OpenStreetMap name or logo as a mark. This
  project uses the name only in the attribution line.
- The extracts carry their own statement, in `osm3s.copyright`, and it is left in the files rather than stripped.

## 4. The font notice, and why it is inside the build

The SIL Open Font License 1.1 requires that the copyright notice and the licence travel with the font software, and
it forbids using the Reserved Font Name for a modified version. Three consequences, all of them already true here:

- The rasterised sheets are use of the font, not a modified font. The upstream TTF in `assets/fonts/` is read, never
  redrawn, and `tools/art/pressstart2p_font.py` fails if a glyph does not fit the 8x8 cell.
- The notice travels in two places. In the repository it is `knowledge/licences/PressStart2P-OFL.txt`, verified byte
  for byte against upstream on 2026-10-21 with sha256
  `705960c3281a5765ecc0b59bd4ed7ca59eed165748076bc2fc3e8fdbfeb944b0`. In the build it is the same text inside
  `data/credits.json`, because `knowledge/` is not mirrored into `game/datafiles/` and a notice left in `knowledge/`
  would not reach a player.
- The font is not sold on its own, and the name "Press Start 2P" is not used for any modified version of it.

## 5. Approved for use, and NOT imported

Ten libraries were read and approved on 2026-10-19, one licence file each, before any of them could be used
(`knowledge/LICENSES.md`). **None of them is imported.** No code from any of these repositories is in this tree, which
is why none of their notices is required in the build today; the rows exist so that a future import lands with its
line already written and its holder already named.

| Library | Licence and the holder line as read in its own file | Link | What may be reused |
| --- | --- | --- | --- |
| Scribble | MIT License, Copyright (c) 2023 Julian Adams | https://github.com/JujuAdams/Scribble | The library as a dependency with its notice kept. Not imported. |
| Input | MIT License, Copyright (c) 2023 Julian Adams | https://codeberg.org/offalynne/Input | The device layer as a dependency. Not imported; the input spec is ours. |
| PictureFrame | MIT License, Copyright (c) 2024 Juju Adams | https://github.com/JujuAdams/PictureFrame | Viewport and integer scaling maths as a dependency. Not imported; `pp_camera` and `pp_look` are ours. |
| BeadyEye | MIT License, Copyright (c) 2024 Juju Adams | https://github.com/JujuAdams/BeadyEye | Camera follow and shake. Not imported. |
| gmdialogue | MIT License, Copyright (c) 2026 danielpancake (LICENSE.txt) | https://github.com/danielpancake/gmdialogue | Read for ideas about command block syntax only. Not imported, and no text or code was copied. |
| crispy | MIT License, Copyright (c) 2020 Brent Frymire | https://github.com/bfrymire/crispy | Test assertions and runner. Not imported. |
| GMAssert2 | MIT License, Copyright (c) 2019 Dickson Law | https://github.com/dicksonlaw583/gmassert2 | Assertions. Not imported. |
| GM-TestFramework | Copyright 2021-2022, YoYo Games Ltd. Licensed under the Apache License, Version 2.0 | https://github.com/YoYoGames/GM-TestFramework | Reference for what the vendor expects a GML test harness to look like. Not imported. Apache 2.0 would oblige this project to keep the notice and state changes, so a future import adds that statement to this row. |
| TurboGML | MIT License, Copyright (c) 2022 Mozart Junior (FoxyOfJungle) | https://github.com/FoxyOfJungle/TurboGML | Individual small helpers. Not imported. |
| cbDataGUI | The MIT License (MIT), Copyright (c) 2017 Cem Baspinar | https://github.com/aft/cbDataGUI-GML-Library | Debug panels behind the debug flag. Not imported. |

Two facts from that pass worth carrying, because they are the reason the rule is "read the file, never the badge":

- GM-TestFramework's GitHub detector reports NOASSERTION, which reads as unlicensed, while its own LICENSE file is the
  Apache 2.0 text. The file is the authority and the row above follows the file.
- gmdialogue's copyright year is 2026. It is recorded as read and is not to be "tidied" back to a guess.

A permissive licence's only obligation is to keep its notice: MIT requires the copyright notice and permission notice
in all copies or substantial portions, and Apache 2.0 requires the notice plus a statement of changes in modified
files. A row above becomes live the day a file from that library lands in `game/`, and this page is edited in the same
commit that imports it, not afterwards.

## 6. Refused, and why (so nobody re-proposes them)

| Thing | Why, and what it means for credits |
| --- | --- |
| GPL, AGPL or LGPL libraries (including GML libraries under them) | Copyleft would force this whole game open, which is the holder's decision and not a reader's. None is used, so no row here owes anything to them. |
| The FMOD binding (FML, MIT) | The binding is MIT but FMOD itself has its own commercial licence, and a credits line would not satisfy it. None is used; the game's audio is GameMaker's own plus this project's own buffers. |
| Marketplace assets under a "no redistribution" or "single project" licence | Some forbid reuse in a source visible repository, and this repository is source visible. None is used, and no such asset is in the tree. |
| Anything with no licence file | Absence of a licence means all rights reserved, not "free to use". Nothing was taken from such a project. |
| Any Undertale or Deltarune decompilation, its data, strings, sprites, fonts, sounds or music | COPYING ONLY. Reading was permitted by the holder's order of 2026-10-19 to understand architecture; expression was never taken. No row here can make that material reusable, and none is present. `tools/check_cleanroom.py` fails the build if any of it appears. |

## 7. Read, not reproduced

These were read as reference and nothing was copied from them, so no attribution line is required. They are listed so a
future audit does not have to re-derive the question:

- Wikipedia articles on Westminster Bridge, Big Ben, the Palace of Westminster, Fleet Services, the M3, Twyford Down,
  St Catherine's Hill, the Port of Southampton, Southampton and the River Itchen: text consulted under CC BY-SA 4.0,
  paraphrased into place notes and never reproduced at length, no images downloaded (`knowledge/maps/REAL-PLACES.md`
  records each URL). CC BY-SA covers the article text, not the facts, and no article text is in this game.
- NESdev wiki pages on PPU palettes, `.pal` files and pattern tables: hardware behaviour only, which is not
  copyrightable expression. The 2C02 palette table in `data/nes_palette.json` is built from those facts by this
  project's own tool.
- The official GameMaker manual: call shapes and event semantics, cited page by page in the module headers and in
  `knowledge/gml-essentials.md`.
- `knowledge/music-styles/` (capcom, classical, composers, fox, jrpg, konami, nintendo): written for this project as
  analysis of technique. No score, no audio and no transcription is in it, and no composer's work is reproduced.
- The OSM extracts' own contributor `source` tags (Bing, survey, maxar) are OSM contributors' notes on how a feature was
  mapped. They travel inside ODbL data and are covered by the line in section 3, not by a separate credit.

## 8. Authorship

Built by Nayil Arana with his agent lanes (builder, testing, musician, research, audit, critics) under his direction.
Every commit names the card that produced it, so the record of who wrote what is `git log` plus `DEVLOG.md`. The lanes
are tools he runs, not separate copyright holders; nothing in this repository is credited to a model vendor, and no
generated asset here carries a vendor attribution requirement.

## 9. The in game screen

`data/credits.json` is the one screen the credits display draws. Its shape is deliberate, because the screen is drawn
with `spr_pp_font8`, which is an 8x8 sheet with one ink and 77 glyphs:

- 32 characters per row (256 px of frame at 8 px a glyph) and 30 rows (240 px at 8 px a row). One screen, no scrolling,
  no second page.
- Only characters the font has: space, `! " ' ( ) * , - . /` digits, `:`, `?`, `[`, `]`, capitals and lowercase. The
  sheet carries a `/` since card t_f476435e grew the slash and the two brackets, and it still has no `;`, which is why
  the OpenStreetMap line on screen is split across rows (it is 40 characters against a 32 column row) and the full
  address is carried in `notices` instead of being drawn.
- Every string in the file is checked against that glyph set and against the row budget, so a row added later cannot
  quietly run off the frame.
- The full text of the notices that must travel with the build (the SIL OFL 1.1 text, 4413 bytes as published) sits in
  the file's `notices` array. It is data, not screen text: it ships because `data/` is mirrored into the bundle, and it
  is never drawn.

The screen is not wired into `pp_app` yet. When it is, the reader belongs with the other runtime data loaders in
`pp_data`, and the printed fields have to be added to `tools/check_font_coverage.py` so the glyph gate covers them the
way it covers dialogue and the title.
