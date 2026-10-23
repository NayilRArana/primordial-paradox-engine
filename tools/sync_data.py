"""Copy data\\ into game\\datafiles\\ so GameMaker includes it in the build.

GameMaker only ships files it knows about: Included Files are copied into the game bundle, and the engine reads them
from the working directory at runtime. Rather than keep two copies of every table, data\\ is the source and this
script mirrors it into game\\datafiles\\, which tools\\gen_project.py then lists in the .yyp.

The mirror is a runtime question, not a "where does the data live" question. data\\ stays the single source of truth
for every file here, and the ones the engine never opens are left out of the bundle but stay in data\\. See
NOT_RUNTIME below for those and why.

Run order for a build:  sync_data.py  ->  check_data.py  ->  gen_project.py  ->  Igor
(`tools\\run.ps1` does exactly that).

Usage:
    python tools/sync_data.py
    python tools/sync_data.py --check      # exit 1 if the mirror is stale
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data")
DST = os.path.join(ROOT, "game", "datafiles")

# Files data\ holds that the engine never opens, so they are not mirrored into the bundle.
#
# palette_recipes.json and scene_palettes.json are build time inputs. They are read by tools, by path, out of data\:
# tools/check_palette_recipes.py, tools/palette_synergy.py --gate (its audit list lives in scene_palettes.json's
# "audit" key), tools/scene_palette_set.py and tools/nes_audit_all.py. No GML file names either one (grep of
# game/**/*.gml on 2026-10-22 found no reader, and the runtime loaders in pp_data name audio, flags, items,
# palette, powers, project, room_palettes, slice and the title tables instead). Mirroring them bought nothing and
# cost something: two generated files the .yyp then declared as Included Files, so every rebuild of the palette set
# was a build input the commit had to carry or the nightly worktree reported as missing. They stay tracked in data\
# because committed tests read them there (tests/test_scene_palette_set.py loads data\scene_palettes.json).
#
# Add a file here only when the engine provably never reads it. A file the GML loads belongs in the bundle.
NOT_RUNTIME = frozenset({
    "palette_recipes.json",
    "scene_palettes.json",
    # talk_profanity.json is the profanity guard's token list (R49, spec 19 layer D). The guard runs at
    # bake time in tools/talk_guard.py and no GML names the file (grep of game/**/*.gml on 2026-10-22:
    # no reader; under D5 the game's only talk input is data/meta_bake.json, and spec 19 section 12.5
    # forbids the list travelling in the bundle next to the bake it already guards).
    "talk_profanity.json",
})

# Directories under data\ that are not mirrored for the same reason, matched on the relative prefix.
#
# schemas/ is documentation for editors and for tools/check_data.py.
#
# ai_cache/ is the recorded Meta Model API cache from tools/meta_client.py (META-CLIENT). It is
# read by that client and by tests/test_meta_client.py, by path, out of data\; no GML file names it,
# and its file names are sha256 hashes that change whenever a call is recorded, so mirroring it put
# a new set of Included Files in the .yyp on every re-record (six of them on 2026-10-22, which
# tools/check_project.py reported as "not listed as an Included File"). It stays tracked in data\
# because the committed cache is what the offline demo and the replay tests read.
NOT_RUNTIME_DIRS = (
    "schemas/",
    "ai_cache/",
)


def source_files() -> list[str]:
    found = []
    for dirpath, _dirnames, filenames in os.walk(SRC):
        for name in sorted(filenames):
            if name.lower().endswith(".json"):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, SRC).replace("\\", "/")
                # schemas/ documents the data for editors and for tools/check_data.py, and ai_cache/ is
                # the Meta client's recorded answers: the game never reads either, so neither belongs
                # in the build bundle. See NOT_RUNTIME_DIRS above.
                if rel.startswith(NOT_RUNTIME_DIRS):
                    continue
                if rel in NOT_RUNTIME:
                    continue
                found.append(rel)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    wanted = source_files()
    stale = []

    for rel in wanted:
        src = os.path.join(SRC, rel)
        dst = os.path.join(DST, rel)
        if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
            continue
        stale.append(rel)
        if not args.check:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    # A file removed from data\ must not linger in the build.
    extras = []
    if os.path.isdir(DST):
        for dirpath, _dirnames, filenames in os.walk(DST):
            for name in filenames:
                rel = os.path.relpath(os.path.join(dirpath, name), DST).replace("\\", "/")
                if rel.startswith("art/") or rel.startswith("streams/"):
                    # The title art mirror is owned by tools/sync_art.py, not by data\.
                    # This continue used to sit on the same line as that comment, so the
                    # comment text swallowed the rest of the line and the "not in wanted"
                    # check below was unreachable for these paths. The clean code gate
                    # caught it on 2026-10-21 as "unreachable Expr after continue".
                    continue
                if rel.startswith("sfx/"):
                    # The sound effect mirror is owned by tools/sync_art.py (mirror_sfx),
                    # which also writes sfx/sfx.json with the WAV header offsets. Card
                    # SFX-1 puts the sources in assets\audio\sfx, so nothing under
                    # data\ produces these files and they are never extras to delete.
                    continue
                if rel not in wanted:
                    extras.append(rel)
                    if not args.check:
                        os.remove(os.path.join(dirpath, name))

    if args.check:
        for rel in stale:
            print("STALE: game/datafiles/%s" % rel)
        for rel in extras:
            print("EXTRA: game/datafiles/%s" % rel)
        if stale or extras:
            return 1
        print("datafiles mirror is current: %d files" % len(wanted))
        return 0

    print("copied %d, removed %d, %d unchanged" % (len(stale), len(extras), len(wanted) - len(stale)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
