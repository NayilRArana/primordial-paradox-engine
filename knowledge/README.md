# knowledge\ index

Files in this folder, and what each one is for. Read the file you need, not the folder.

| File | Purpose | Status |
| --- | --- | --- |
| gml-essentials.md | GML facts we build on: objects and events, structs, methods, arrays vs DS, surfaces and the application surface, cameras and viewports, tile maps, async save, json_parse and json_stringify, input, audio, rooms. Every fact carries its manual link and the date checked. | written 2026-10-19 |
| MUSIC-STYLE-BIBLE.md | Composition techniques of the studied composers (Toby Fox; Keiichi Suzuki and Hirokazu Tanaka of the Mother series; Nobuo Uematsu of Final Fantasy I to III) plus four period families (Baroque, Classical, rock on 2A03, metal) turned into 76 executable arranger recipes for the 2A03 plus the Konami VRC6: 30 in section 5 and 46 in section 14 (BAR, CLS, RCK, MET), a progression grammar per mood in A minor and C major, and 20 named common progressions with function labels and bar counts in section 7.4. 44 numbered sources with links and read dates; no melody is transcribed. `tools\check_music_style_bible.py` builds `data\music_recipes.json` from it and runs the acceptance checks (C1 count, C2 citation, C3 fields, C4 dashes, C5 no transcription, C6 clean-room, C7 families, C8 progressions, C9 cue coverage). | written 2026-10-21, extended 2026-10-21 (MUS-STYLE-2) |
| ART-BIBLE.md | The NES hardware limits as numbers (256 x 240, 8 x 8 tiles, 16 x 16 attribute areas, 4 plus 4 palettes, 8 sprites per line, 64 in OAM, 64 colours of which 54 are usable without caveat) and the art conventions of Final Fantasy I to III, Dragon Quest I to IV and Castlevania I and III, each number tagged with a source, plus a 17 item frame review checklist. `tools\check_art_bible.py` runs the acceptance checks and `tools\art\make_palette_sheet.py` renders the 3x palette sheet. | written 2026-10-21 |
| gamemaker-project-format.md | What the .yyp, .yy and .gml files are, what the manual does and does not guarantee, the safe hand edit procedure, and what stays unverified until GameMaker is installed. | written 2026-10-19 |
| igor-cli.md | Command line build with Igor: the login precondition, the runtime path, the options we use, the Windows commands, and what tools\run.ps1 must do. | written 2026-10-19 |
| genre-design.md | How turn based battles with a dodge phase, TALK options, spare and kill routes, no EXP progression, FF3 style overworlds and Castlevania style sprites work as genre mechanics. Public descriptions only. | written 2026-10-19 |
| mechanics\ACTION-MECHANICS.md | The action half as numbers: bullet board and marker, invincibility frames, mercy and ACT, six boss rule changes, the fixed jump arc and its landing table, three whip tiers with frame timings, knockback, fairness constants, and a three phase boss skeleton including the Prometheus interruption. 10 source ids with links and read dates, 44 recipes in `data\mechanics\action_recipes.json`, checked by `tools\check_action_recipes.py`. Ends with a mapping table naming two new specs (17 action movement, 18 boss phases). | written 2026-10-22 |
| LICENSES.md | Every open-source library considered, its licence read from the repository, what we may reuse, what is rejected and why, and the attribution plan. | written 2026-10-19, licences re-read 2026-10-19 |
| PROVENANCE.md | One entry per subsystem: the module map, the "modules written from the specs alone" entry that owns every module, two WITHDRAWN incident records of what was studied, and the clean-room re-review's outcome per spec and per source file. A subsystem with no entry cannot be committed. | live, studied entries withdrawn 2026-10-19 |
| SPEC-DELTAS.md | The delta list: 24 items across the thirteen specs, each with an explicit source line (manual, genre, internal or withdrawn) and a source index. Awaiting Nayil's accept or reject per item. | re-derived 2026-10-19, sources set 2026-10-19 |
| SPEC-REVIEW.md | One row per spec: confirmed or rewritten, by which reviewer, when. `tools\check_spec_review.py --strict` refuses implementation work while any row is pending. | live, seeded pending 2026-10-19 |
| study\ | QUARANTINED by the manager on 2026-10-19 and moved outside this repository. Nothing may read it, and nothing in this repository may be written from it. The entry stays only as a record that it must not be used. | quarantined, never read |

Related, outside this folder:
- Plan and architecture: ..\PLAN.md
- Specs, one per core system: ..\specs\
- Data, once it exists: ..\data\
- Dev log: ..\DEVLOG.md

The clean-room rule (PLAN section 1) applies to every file in this folder: no decompiled Undertale or Deltarune code,
data or text, ever, from any bot.

Dates in this folder mean "read at the source on that date". A manual page that changes later invalidates the fact,
not the file: re-read the page and correct the line.
