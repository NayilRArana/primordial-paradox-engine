"""Copy data\\ into game\\datafiles\\ so GameMaker includes it in the build.

GameMaker only ships files it knows about: Included Files are copied into the game bundle, and the engine reads them
from the working directory at runtime. Rather than keep two copies of every table, data\\ is the source and this
script mirrors it into game\\datafiles\\, which tools\\gen_project.py then lists in the .yyp.

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


def source_files() -> list[str]:
    found = []
    for dirpath, _dirnames, filenames in os.walk(SRC):
        for name in sorted(filenames):
            if name.lower().endswith(".json"):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, SRC).replace("\\", "/")
                # data/schemas is documentation for editors and for tools/check_data.py. The game never reads a schema,
                # so it is not a runtime data file and does not belong in the build bundle.
                if rel.startswith("schemas/"):
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
