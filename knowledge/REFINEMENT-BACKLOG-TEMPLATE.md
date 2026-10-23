# Refinement backlog template: the small cards the hackathon days burn down

Card t_7ecd6549, GAME-ROADMAP-2, gamedev. This file is the format, not a backlog. Copy the template, fill it, and put
the row in the table at the bottom.

Why a template at all. From Monday Oct 26 the project stops getting bigger and starts getting better. A large card that
touches five files is a day lost to a merge; a small card that touches one file and proves itself in fifteen minutes is
an hour of visible progress. The whole point of finishing the scaffold by Sunday is that every card after Sunday can be
this small.

## The rule of the small card

1. **One file, or one asset directory.** If the fix needs two files, either it is two cards or it is not a refinement.
2. **One check, runnable in under two minutes.** A pixel check, a duration check, a test, a diff of two captures. If
   the proof needs a person to squint, the card is wrong.
3. **15 to 30 minutes of work.** Anything bigger is a Monday card, not a hackathon card.
4. **Before and after, both kept.** The after state and the artifact that shows it. `output/before` and `output/after`
   or the numbers in the card. "It looks better" is not a result.
5. **No new number.** A refinement moves an existing value that a spec already fixes, or it makes an existing value
   true on screen. A refinement that invents a number is a spec change and is carded as one, for gamedev.
6. **RULE 0 first.** Palette before pixels, always. A refinement that adds a colour is refused; a refinement that moves
   an existing role to its right place is exactly what this backlog is for.

## The six refinement kinds

| Kind | What it is | The check | Typical size |
| --- | --- | --- | --- |
| PALETTE | a colour assigned to the wrong role, an attribute clash, a tile that reads as mud | `python tools/nes_audit_all.py` on the frame plus `check_palette_recipes.py` | 15 min |
| SPRITE | one frame, one bust, one 16x16 cell, one walk cycle step | the contrast tool and the blob test from `knowledge/SPRITE-CRAFT.md`, before and after captures | 30 min |
| TIMING | a fade length, a shot length, a text speed, a pause, a shake | the number in `data/` matches the spec, and a capture at the boundary step | 15 min |
| TEXT | a line over 30 characters, a box that wraps badly, a name plate, a wrong speaker | `python tools/check_font_coverage.py` plus a capture of the box | 15 min |
| JUICE | a hit flash, a 2 frame squash, a marker trail, a cursor blink | two captures, n frames apart, with the delta named | 30 min |
| SOUND | a cue that clips, a drum too loud, a crossfade that steps, a missing sting | `tools/ear_critic.py` before and after score on the four axes | 30 min |

## The card template

Copy this, fill every line, then create the card on `nayil-ops` with `assignee` set to the lane that owns the file.
A field left as a placeholder is a card that will come back.

```
Title: <KIND> <object>: <the one visible change, in the player's words>

Body:
REFINEMENT. Backlog row <id>. Kind: PALETTE | SPRITE | TIMING | TEXT | JUICE | SOUND.
OWNER LANE: <builder, musician, job-discovery, assistant>
FILE: <exactly one path, or one asset directory>
WHAT THE PLAYER SEES NOW: <one sentence, from a capture taken today, with the capture path>
WHAT THEY SHOULD SEE: <one sentence, and the spec section or palette role that says so>
THE CHANGE: <one or two sentences. No new colour, no new number unless the card names the spec that moves.>
CHECK: <the command> and <the artifact>. Before: <path or number>. After: <path or number>.
SIZE: 15 or 30 minutes. If it turns out bigger, stop and post Q: for gamedev.
RULE: gamedev specs rule; never open a file holding a key; no em dashes or en dashes; NES rules and RULE 0.
```

## The nightly demo recording rule

Non negotiable, from Oct 26 to Nov 3.

1. **One recording a night**, from the same script (`knowledge/DEMO-SCRIPT.md`, executed by the DEMO-KIT card's
   autoplay), at the same resolution and scale, with the same capture command. Same input, same frame count.
2. **Stored as `output/demo/night-NN.mp4`** plus the frame at t=0 and three sample frames, so a human can see drift
   without scrubbing.
3. **Diffed against last night**, in numbers: total length, frame count, the first frame that differs, and the count of
   distinct frames changed. A night with no change is a night with nothing in the log.
4. **One line in `DEVLOG.md` per night**: what changed on screen, what the recording proves, what is next. Written
   from the recording, never from the cards.
5. **The nightly recording is the submission build.** Not a special build made at the end. If the nightly is good, the
   submission is already made; if a night is bad, the regression shows up eight days before the deadline and not
   eight hours before it.
6. **A night with no recording is a lost night**, and the READINESS page must say so the next morning.

## The backlog table

Rows are added by the head after reading the nightly recording and the READINESS page. Order is by demo impact, then
by size. A row without a before capture does not enter the table.

| Id | Kind | Object | File | Seen at (route second) | Size | State |
| --- | --- | --- | --- | --- | --- | --- |
| RB-001 | PALETTE | the quay's water tile reads as stone at night | `assets/tiles/quay/` | 0:05:12 | 15 | queued |
| RB-002 | TIMING | the gate text advances one step per character, spec says two | `data/dialogue/all.json` | 0:05:40 | 15 | queued |
| RB-003 | JUICE | the first fight's hit has no flash frame | `game/scripts/pp_battle_director/` | 0:09:55 | 30 | queued |
| RB-004 | TEXT | Morgan's second line wraps a word across the box | `knowledge/GATE-DIALOGUE.md` then the bake | 0:05:44 | 15 | queued |
| RB-005 | SOUND | the ship cue's hat sits over the melody in the corridor | `assets/audio/pp_05_small_ship/` | 0:11:20 | 30 | queued |
| RB-006 | SPRITE | the hero's walk frame 2 has a doubled pixel at the boot | `game/sprites_src/chars/` | 0:01:20 | 30 | queued |

The six seed rows above are examples of the shape, not orders. Replace them with rows measured from the first nightly
recording.

## Provenance

No external code, art, dialogue or music is involved: this file is a card format. The kind list is derived from this
repository's own audits (`knowledge/NES-AUDIT.md`, `SPRITE-CRITIQUE.md`, `EAR_SWEEP_2026-10-22.md`), which name the
same six axes in their own words.

Written by gamedev, 2026-10-22. Check for this file: it exists, it carries one template with every field, six kinds
with their checks and sizes, and the six part nightly rule that makes drift visible as a diff.
