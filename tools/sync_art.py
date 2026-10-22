#!/usr/bin/env python3
"""Mirror the title art from game\\sprites_src\\title\\ into the build as Included Files.

The art lane (TS-A, TS-B, TS-C) writes one PNG plus one JSON per animation into
game\\sprites_src\\title\\. The engine cannot read that folder at runtime, so this script copies the PNGs into
game\\art\\ and writes one index, art\\title_manifest.json, that the runtime reads to know every animation's
frame size and frame count.

The index is the contract between the art lane and the game: the game asks for a name and gets a frame count,
so a sprite that has not landed yet simply is not in the index and the game draws a rectangle in its place.

Deterministic: the index is written with sorted keys and LF endings, so the same art gives the same bytes.

Usage:
    python tools/sync_art.py
    python tools/sync_art.py --check      # exit 1 if the mirror is stale
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "game", "sprites_src", "title")
# The environment lane writes its tileset into game\sprites_src\env\ with the same PNG plus JSON contract, so the
# mirror reads both folders and the runtime needs no second index. Card ASSEMBLE loads ts_ship from it.
ENV_SRC = os.path.join(ROOT, "game", "sprites_src", "env")
SOURCES = (SRC, ENV_SRC)
DST = os.path.join(ROOT, "game", "datafiles", "art")
INDEX = "title_manifest.json"


def source_entries() -> list[dict]:
    """Every animation on disk, sorted by name, with the numbers the runtime needs."""
    entries = []
    for folder in SOURCES:
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(folder, fname), "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            if "name" not in meta or "frame_w" not in meta:
                # A tileset sidecar (ts_ship_tiled.json) describes a Tiled file, not an animation strip.
                continue
            png = fname[:-5] + ".png"
            if not os.path.isfile(os.path.join(folder, png)):
                raise SystemExit("sync_art: %s has no PNG beside it" % fname)
            entries.append({
                "name": meta["name"],
                "file": meta["name"] + ".png",
                "frame_w": int(meta["frame_w"]),
                "frame_h": int(meta["frame_h"]),
                "frames": int(meta["frames"]),
                "fps": float(meta.get("fps", 0.0)),
            })
    return entries


def source_path(fname: str) -> str:
    """The folder a mirrored PNG really lives in. Title first, so an old name keeps its old file."""
    for folder in SOURCES:
        if os.path.isfile(os.path.join(folder, fname)):
            return os.path.join(folder, fname)
    return os.path.join(SRC, fname)


def index_text(entries: list[dict]) -> str:
    payload = {"format": 1, "kind": "title_art", "animations": entries}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> int:
    """Mirror the title art into game/datafiles/art and return 0.

    The title theme stream is mirrored here too, so that anyone who calls main() gets the
    same result as someone who runs the script: a fresh checkout of a commit can only
    regenerate the committed .yyp when both mirrors exist. Measured 2026-10-21: with the
    stream mirrored only from the __main__ block, the PP suite failed with "lists Included
    File streams/title_theme.ogg which is not in game/datafiles".
    """
    mirror_streams()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    entries = source_entries()
    wanted_png = {e["file"]: e for e in entries}
    os.makedirs(DST, exist_ok=True)

    stale = []
    for name, entry in wanted_png.items():
        src = source_path(name)
        dst = os.path.join(DST, name)
        if not os.path.exists(dst) or hashlib.sha256(open(src, "rb").read()).digest() != \
                hashlib.sha256(open(dst, "rb").read()).digest():
            stale.append(name)
            if not args.check:
                shutil.copy2(src, dst)

    # A PNG that the art lane removed must not linger in the build.
    for fname in sorted(os.listdir(DST)):
        if fname.endswith(".png") and fname not in wanted_png:
            stale.append(fname)
            if not args.check:
                os.remove(os.path.join(DST, fname))

    index_path = os.path.join(DST, INDEX)
    text = index_text(entries)
    index_stale = True
    if os.path.exists(index_path):
        index_stale = open(index_path, "r", encoding="utf-8").read() != text
    if index_stale and not args.check:
        with open(index_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    if args.check:
        for name in stale:
            print("STALE: game/art/%s" % name)
        if index_stale:
            print("STALE: game/art/%s" % INDEX)
        if stale or index_stale:
            return 1
        print("art mirror is current: %d animations" % len(entries))
        return 0

    print("copied %d png, index %s, %d animations" % (len(stale), "written" if index_stale else "current", len(entries)))
    return 0


def mirror_streams() -> None:
    """Every rendered theme under assets\\audio\\<name>\\<name>.ogg is copied into game/datafiles/streams.

    One stream used to be enough, so this copied title_theme.ogg and nothing else. The music lane
    added title_theme_v2.ogg, and the committed .yyp lists every stream in the mirror, so a fresh
    checkout could not regenerate that .yyp while this script mirrored only the first theme. The
    rule now is the source tree's: one folder per theme, the render named after the folder.
    """
    base = os.path.join(ROOT, "assets", "audio")
    dst_dir = os.path.join(ROOT, "game", "datafiles", "streams")
    if not os.path.isdir(base):
        return
    for name in sorted(os.listdir(base)):
        src = os.path.join(base, name, name + ".ogg")
        if not os.path.isfile(src):
            continue
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, name + ".ogg"))


if __name__ == "__main__":
    mirror_streams()
    sys.exit(main())
