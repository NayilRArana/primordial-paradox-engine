# Clean-room review record

Rule, set by Nayil and restated by the manager after the breach of 2026-10-19: nothing in this repository may be
written from a decompiled or ripped commercial game. The study copies that P1-A cloned were quarantined by the manager
to `<workspace>\Private\quarantine-decomp-2026-10-19` and may not be read, searched, opened or reasoned
from again. Specs 01 to 13, the six knowledge files and the two PROVENANCE subsystems that were studied are PENDING a
fresh review by a reviewer who has read only public genre design and the official GameMaker manual.

This file is that review's ledger. `tools/check_cleanroom.py` reads it and refuses:

- a GML module with no row here at all;
- a row that says confirmed, rewritten or reviewed without a reviewer and a date;
- any file under `game\` or `data\` that names a study copy, the quarantine folder or the decompilation repository;
- any foreign character name or distinctive phrase from either of those games.

A row that says `pending` is not a pass. It is reported on every run, by name, until a reviewer rules on it.

Card owed: `t_ec0fb8be` (assignee code-review), created 2026-10-19.

| Module | Status | Reviewer | Date |
| --- | --- | --- | --- |
| game/objects/obj_pp_debug_overlay/Create_0.gml | pending | code-review | - |
| game/objects/obj_pp_debug_overlay/Draw_64.gml | pending | code-review | - |
| game/objects/obj_pp_debug_overlay/Step_0.gml | pending | code-review | - |
| game/objects/obj_pp_game/Create_0.gml | pending | code-review | - |
| game/objects/obj_pp_game/Draw_0.gml | pending | code-review | - |
| game/objects/obj_pp_game/Step_0.gml | pending | code-review | - |
| game/objects/obj_pp_game/Step_1.gml | pending | code-review | - |
| game/scripts/pp_app/pp_app.gml | pending | code-review | - |
| game/scripts/pp_battle_commands/pp_battle_commands.gml | pending | code-review | - |
| game/scripts/pp_battle_director/pp_battle_director.gml | pending | code-review | - |
| game/scripts/pp_battle_text/pp_battle_text.gml | pending | code-review | - |
| game/scripts/pp_camera/pp_camera.gml | pending | code-review | - |
| game/scripts/pp_config/pp_config.gml | pending | code-review | - |
| game/scripts/pp_data/pp_data.gml | pending | code-review | - |
| game/scripts/pp_dialogue/pp_dialogue.gml | pending | code-review | - |
| game/scripts/pp_dodge_arena/pp_dodge_arena.gml | pending | code-review | - |
| game/scripts/pp_dodge_recipe/pp_dodge_recipe.gml | pending | code-review | - |
| game/scripts/pp_input/pp_input.gml | pending | code-review | - |
| game/scripts/pp_ledger/pp_ledger.gml | pending | code-review | - |
| game/scripts/pp_map/pp_map.gml | pending | code-review | - |
| game/scripts/pp_overworld/pp_overworld.gml | pending | code-review | - |
| game/scripts/pp_rng/pp_rng.gml | pending | code-review | - |
| game/scripts/pp_scene/pp_scene.gml | pending | code-review | - |

## What the rows do not claim

A `pending` row is not a suspicion that a module was copied. It is a statement that no fresh reviewer has yet read it
against the public record since the breach, and this repository does not get to assume its own innocence.
