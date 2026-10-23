# BUILD-TIMELINE: what is scaffold, what is hackathon work, and how to prove which is which

Card t_8d7bad5f (R45). Written 2026-10-22. Owner of this file: assistant. It is updated on every night of the
hackathon and never rewritten backwards.

Purpose. The Meta Global AI Developer Hackathon runs Oct 26 to Nov 4, 2026, with submission at 9 PM ET on Nov 4. The
official rules on prior work had not been published when this file was written, so the repository answers the question
itself instead of an entrant's memory (`PLAN-WIN-2026-10-22.md` section 0.2: prior work is UNKNOWN until the official
rules land). Two mechanisms, both mechanical:

1. A baseline tag on the last commit of Saturday Oct 25, so "before" and "after" are a `git diff` and not an opinion.
2. A dated row per hackathon night, added by this file, with the commit range and the recording that goes with it.

## 0. The line, in one place

| Item | Value |
| --- | --- |
| Repository | one shared git index at `<workspace>\Shared`; this project lives at `projects/primordial-paradox` |
| First commit naming this project | `2fb4158`, 2026-10-19, "Primordial Paradox: study allowed, copying forbidden; handoff for Claude" |
| HEAD when this file was written | `dd9fe93`, 2026-10-22 19:01, SPEC-19-LLM-TALK |
| Commits touching this project, `2fb4158` to `dd9fe93` | 104 |
| Of those, by day | 11 on 10-19, 4 on 10-20, 22 on 10-21, 68 on 10-22 |
| Baseline tag | `pp-baseline-2026-10-25`, to be placed on the last commit of Sat 2026-10-25. NOT PLACED YET |
| Hackathon window | 2026-10-26 00:00 to 2026-11-04 21:00 ET |
| Commit range for the scaffold so far | `2fb4158..dd9fe93` |

Reproduce every figure above with the path filter, because the index is shared and a bare `git log` counts the whole
estate:

    git log --oneline 2fb4158..dd9fe93 -- projects/primordial-paradox
    git log --format=%ad --date=short -- projects/primordial-paradox | sort | uniq -c

## 1. Scaffold, built before Oct 26

Everything below existed at `dd9fe93` and is scaffold: the engine, the tools, the pipeline and the checks. It is
deliberately generic, so a "new work only" rule still leaves the hackathon's own work visible.

| Piece | At `dd9fe93` | Where |
| --- | --- | --- |
| The engine contract, one spec per system | 19 spec files (18 committed), specs 01 to 19 | `specs/` |
| Game code | 35 GML files, 7745 lines, 23 script folders, 3 rooms (`rm_pp_boot`, `rm_pp_title`, `rm_pp_ship`) | `game/` |
| Content as data | 80 JSON files, every one checked against its schema | `data/` |
| Tooling | 111 Python files: checkers, art pipeline, audio renderers, model clients | `tools/` |
| Tests | 52 test files, 809 test functions | `tests/` |
| Art | 126 of 126 gated assets pass the picture chip rules; the audit reports 160 files with 24 advisory failures, all contact sheets | `assets/`, `game/`, `knowledge/NES-AUDIT.md` |
| Audio | 21 sound effects and 101 animation mirrors in the build data; the title theme proven live | `assets/audio/`, `game/datafiles/` |
| The Meta client | `tools/meta_client.py` with chat, structured chat, vision, image, edit and segment, behind a mock and a replay cache that is still empty | `tools/` |
| The gates | data, project, clean room, provenance, scene palettes, palette synergy, art audit | `tools/`, run by `tools/run.ps1` |
| The docs | 40 or so files in `knowledge/`: art bible, provenance, licences, mechanics notes, this timeline | `knowledge/` |

Built and proven inside that range, on this machine, on 2026-10-22: the build compiles and launches (Igor exit 0,
sc=536, ob=3, ro=3, da=227), the title screen and the opening crawl are captured live, the overworld walk and the
dialogue box run with their sound cues, and 905 of 921 tests pass, with all 15 red rows in the art regeneration class.

HEAD moves every few minutes while lanes work, so the figures in this table are as measured at `dd9fe93` and are a
snapshot, not a fixed constant. The anchor for a diff is the tag, not a hash.


Not in the scaffold, and therefore available as visible new work: any Meta model output (`data/meta_bake.json` does
not exist), the drive room, the arrival map, boarding, the two fights wired live, game over, the licence, and every
piece of polish.

## 2. The hackathon window, filled in as it happens

Empty by design on 2026-10-22. One row per night, appended, never edited later. The commit range is
`<tag>..<that night's HEAD>`, so a reader can diff exactly one night.

| Night | Commit range | What changed | Recording | Notes |
| --- | --- | --- | --- | --- |
| (none yet) | | | | |

The rule for each row, from `knowledge/REFINEMENT-BACKLOG-TEMPLATE.md`: the night's work is small detail cards, one
file and one check each, and the night ends with one recording from the same script, so the change is visible as a
diff between two videos and not as a memory of what was meant.

## 3. How a judge or an organiser checks this file

1. `git log --oneline pp-baseline-2026-10-25..HEAD -- projects/primordial-paradox` is every commit made during the
   hackathon; before the tag exists, the range is `dd9fe93..HEAD`, which is the same statement with a later start.
2. `git diff --stat pp-baseline-2026-10-25..HEAD -- projects/primordial-paradox` is every line changed during it.
3. The rows in section 2 must match those ranges. When a row and the log disagree, the log wins and the row is
   corrected in the next night's commit, with the correction named.

## 4. What this file refuses

- No claim about what the official rules allow. That is a fact about Meta's rules, and the rules had not been read
  when this was written.
- No retroactive tidy up. A night that changed its mind keeps both rows.
- No row without a commit range and a recording. A night with nothing recorded is a night with nothing to show, and
  the row says so in the Notes column.

Written by assistant, 2026-10-22. Checked by a working tree script (`_r45_check.py` in the project root, kept out of
the commit because the repository's commit gate refuses a source file no test maps to) and by `git log` for every
figure above.
