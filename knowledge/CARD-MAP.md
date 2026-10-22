# Card map: every gamedev card, ordered, with its FOX-STYLE parent

Rule from the 2026-10-22 order: a card with no parent in `knowledge/FOX-STYLE.md` is a bug. This file is the index
that makes an orphan card visible. It is committed and it is checked by reading, not by a script, because card ids
live on the board and not in the repo.

Ordering rule: each system is a derivative of the one before. Read the table top to bottom and the dependencies hold.

Legend: DONE, RUNNING, READY, BLOCKED, PLANNED (specified here, created when its predecessor lands).

## The ordered set

| # | Card | Board id | Status | FOX-STYLE parent |
| --- | --- | --- | --- | --- |
| 0 | P1-A knowledge pack, licence-clean references, specs | t_90bcee8e | DONE | 11, 12 |
| 1 | P1-B GameMaker skeleton, schemas, checker, run script, gates | t_f7d3a69d | DONE | 11, 12 |
| 2 | G0 engine orchestration (the parent of this lane) | t_38a5fbf4 | DONE | all |
| 3 | G0-1 save, load, resume and ledger persistence | t_a311bdff | DONE | 6, 2 |
| 4 | UI-NES JRPG screens (battle layout, windows, dialogue box) | t_0df13164 | DONE | 4, 7, 8 |
| 5 | SPRITE-1 procedural overworld and battle sprites | t_b2acf67d | DONE | 12 |
| 6 | BG-BATTLE NES battle backgrounds | t_1c5a8599 | DONE | 4, 12 |
| 7 | W1 wire the title room | t_9d403d42 | DONE | 8, 12 |
| 8 | TS1-CODE working title screen proven by a run | t_90c0cc4a | BLOCKED | 8 |
| 9 | TS2-CODE title v2 in the game | t_340b1578 | DONE | 8 |
| 10 | PP build and run for real; fix the save-backup crash | t_b72efa81 | DONE | 6 |
| 11 | NES-CHECK palette and font validator | t_a822bbbf | DONE | 11, 12 |
| 12 | ENV-TILES ship tileset and sample map | t_4f58c88d | DONE | 12 |
| 13 | SPEC study, doctrine and audit (this pass) | (no card, this session) | DONE | all |
| 14 | TEXT-REVEAL-1 one reveal machine, two layouts | t_fa2fc030 | READY | 7, law 8 |
| 15 | LEDGER-2 per-enemy exit ledger and verdict | t_48020b30 | READY | 2 |
| 16 | NES-PALETTES scene palette sets for title and ship | t_c8156a77 | READY | 12 |
| 17 | TS2-ART-A title v2 logo, emblem, car exterior | t_758934a8 | READY | 12 |
| 18 | SFX-1 NES style sound effect set | t_f9a87b4f | READY | 9 |
| 19 | SFX-WIRE menu and text sounds in every menu | t_efdf181b | RUNNING | 9, 8 |
| 20 | SFX-WIRE-PROOF prove footsteps, door, encounter in a scripted run | t_0cac113b | TODO | 9, 5 |
| 21 | ENEMIES-1 NES enemy sprites for the ship and the sea | t_97871d4b | READY | 12 |
| 22 | CHAR-PIPE concept art to sprite pipeline | t_d01614a1 | READY | 12 |
| 23 | ASSEMBLE playable Map 2 test room with tileset and walk | t_e32c2a29 | READY | 5, 12 |
| 24 | NES-AUDIT fixes, 24 gated art rows worst first | t_5f3bba57 | READY | 12 |
| 25 | INTRO-1 stars, fade, text crawl | t_d2ec48a1 | BLOCKED | 10, 9 |
| 26 | MENU-1 extract `pp_menu`, then the pause screen | PLANNED | PLANNED | 8, audit 3c |
| 27 | FLOW-1 door and transition module (`pp_flow`) | PLANNED | PLANNED | 5 |
| 28 | TALK-1 the TALK command as a battle command | PLANNED | PLANNED | 1, 2 |
| 29 | BATTLE-1 encounter and enemy rows as data | PLANNED | PLANNED | 1, 11 |
| 30 | PATTERN-1 the first three authored bullet recipes | PLANNED | PLANNED | 3 |
| 31 | SLICE-1 the Percy fight end to end | PLANNED | PLANNED | 1, 2, 3, 4 |
| 32 | SAVE-2 the slot list screen over the summary | PLANNED | PLANNED | 6, 8 |
| 33 | P6-ROUTE the prison branch and the Kronos ending | PLANNED | PLANNED | 2, 10 |
| 34 | AUDIT-NIGHT one pass re-running the whole gate set | PLANNED | PLANNED | 12 |

Count: 25 real cards on the board (20 before this pass, 2 created by it, 3 counted here from other lanes' boards that
this lane consumes), plus 9 planned. The target the order asks for is 30 to 40 in the G0 lineage; the planned tail is
deliberately not created yet, because a planned card with no spec behind it is the same bug as an orphan card with
no parent. Each planned row above names the section it must be specced against before it is created.

## Why each planned card exists

- MENU-1. The audit found no `pp_menu` module: the title menu is inline in `pp_title`. Not a violation yet, because
  there is one menu. It becomes one the moment a second is written inline. The trigger is explicit, so the card is
  created with whatever card needs the second menu, or earlier if that is cheaper.
- FLOW-1. `pp_overworld` currently handles rails. Doors and the fade belong in one module so a scene cannot implement
  half a transition (FOX-STYLE 5).
- TALK-1. Nayil's battle command set is FIGHT, POWER, TALK, SPARE, ITEM. TALK is the one with no implementation and no
  card. It is the command the whole non-violent premise rides on.
- BATTLE-1. The enemy and encounter tables are still code shaped in the battle director. Section 1 requires rows.
- PATTERN-1. The recipe runner exists and is tested; there is no authored content yet.
- SLICE-1. The vertical slice Nayil scoped: Map 2 ship plus Percy, end to end.
- SAVE-2. The save module works; there is no slot list screen, so a player cannot choose a file.
- P6-ROUTE. The two route branches exist in the ledger; no scene reads them yet.
- AUDIT-NIGHT. A scheduled-by-hand re-run of every gate, so the audit does not rot.

## Cards that must not be created

Anything that adds a subsystem with no FOX-STYLE section. If a card seems to need one, extend `FOX-STYLE.md` first and
add the section to the derivation table at the end of it. That is the rule that keeps the doctrine complete rather
than decorative.
