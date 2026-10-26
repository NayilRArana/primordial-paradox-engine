#!/usr/bin/env python3
"""Mirror the title art from game\\sprites_src\\title\\ into the build as Included Files.

The art lane (TS-A, TS-B, TS-C) writes one PNG plus one JSON per animation into
game\\sprites_src\\title\\. The engine cannot read that folder at runtime, so this script copies the PNGs into
game\\datafiles\\art\\ and writes one index, game\\datafiles\\art\\title_manifest.json, that the runtime reads to know
every animation's frame size and frame count.

game\\datafiles\\art\\ is build output: it is gitignored, and this script is the only thing that writes it. The
authored tree is game\\sprites_src\\, and since card t_4e54cc9e the sprite queue in data\\sprite_redraw_queue.json
measures there too. The older folder game\\art\\ is retired and deleted: this script never wrote it, the game never
read it, and a redraw left in it reached nothing that ships.

The index is the contract between the art lane and the game: the game asks for a name and gets a frame count,
so a sprite that has not landed yet simply is not in the index and the game draws a rectangle in its place.

Deterministic: the index is written with sorted keys and LF endings, so the same art gives the same bytes.

Usage:
    python tools/sync_art.py
    python tools/sync_art.py --check      # exit 1 if the mirror is stale
    python tools/sync_art.py --no-project # mirror only, leave the .yyp alone

A write run ends by regenerating game\\PrimordialParadox.yyp from the mirror it just wrote, because
every file under game\\datafiles is an Included File in that project. That is what stops a landed cue
from leaving the .yyp stale (card t_e40f9705).
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
# Card ASSEMBLE: the character lane writes the overworld and battle sheets into game\sprites_src\chars\ with the same
# contract, so the mirror reads three folders and the walker in rm_pp_ship draws its own sheet without a second index.
CHARS_SRC = os.path.join(ROOT, "game", "sprites_src", "chars")
# Card R28: the exterior tile set (R46) is written into game\sprites_src\env\quay\ rather than beside the ship sheet,
# because it is one set of its own and the art lane keeps its generator and its TILES.md page with it. The mirror
# therefore reads that subfolder too, so a set written there still reaches the build with no hand copy.
ENV_QUAY_SRC = os.path.join(ENV_SRC, "quay")
# Card t_af836a62: the drive tile set (DRIVE-TILES, t_d0e73725) is written into assets\tiles\drive\ and its own TILES.md
# fixes that as the place to look, so the map row that names drive_tiles reaches the build from here. The sheet stays
# where its card put it: this mirror reads the card's folder rather than the card moving its sheet into sprites_src.
DRIVE_SRC = os.path.join(ROOT, "assets", "tiles", "drive")
# Card t_4275136f: the battle screen's own two art folders were never mirrored. game\sprites_src\bg\ holds the four
# baked 256x112 strips (BG-BATTLE) and game\sprites_src\enemies\ holds the seven 32x32 enemy sheets, and neither
# reached game\datafiles\art, so pp_art_has("bg_battle_deck_night") was false in every build: pp_battle_draw_field
# printed "not in the art index" and drew the field without its strip, and the tutorial fight had no enemy sheet to
# draw. Two folders here, one index, nothing else changes.
BG_SRC = os.path.join(ROOT, "game", "sprites_src", "bg")
ENEMY_SRC = os.path.join(ROOT, "game", "sprites_src", "enemies")
SOURCES = (SRC, ENV_SRC, CHARS_SRC, ENV_QUAY_SRC, DRIVE_SRC, BG_SRC, ENEMY_SRC)
DST = os.path.join(ROOT, "game", "datafiles", "art")
INDEX = "title_manifest.json"


def _folders():
    for folder in SOURCES:
        if os.path.isdir(folder):
            yield folder


def source_entries() -> list[dict]:
    """Every animation on disk, sorted by name, with the numbers the runtime needs.

    A tileset sidecar (ts_ship_tiled.json, ts_exterior_tiled.json) is not an animation: it
    declares kind tileset and names its sheet in "image". Measured 2026-10-21: the sidecar was
    read as a strip and stopped the whole suite at session setup with "has no PNG beside it",
    because its sheet is ts_exterior.png, not ts_exterior_tiled.png. The strip naming rule
    therefore only applies to real animations; the tileset sheets are mirrored by
    source_pngs() below, because the committed .yyp lists them as Included Files.
    """
    entries = []
    seen = set()
    for folder in _folders():
        for fname in sorted(os.listdir(folder)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(folder, fname), "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            if "name" not in meta:
                continue
            if "frame_w" not in meta:
                # Card t_4275136f: a battle strip's sidecar is not an animation record. Its own generator,
                # tools\art\make_battle_bg.py, writes kind battle_background and declares the size as width and
                # height, because a strip is one 256x112 picture and not a row of frames. Before this branch the
                # four strips were skipped here in silence, which is why no build ever carried one.
                if meta.get("kind") != "battle_background":
                    continue
                if "width" not in meta or "height" not in meta:
                    raise SystemExit("sync_art: %s is a battle background with no width or height" % fname)
                meta = dict(meta, frame_w=int(meta["width"]), frame_h=int(meta["height"]), frames=1, fps=0.0)
            if meta["name"] in seen:
                continue
            png = fname[:-5] + ".png"
            if not os.path.isfile(os.path.join(folder, png)):
                # A Tiled export (ts_ship_tiled.json) names its sheet in "image" and carries no frame_w, so it never
                # reaches this line. A tileset sidecar that does carry frame_w but no PNG is the Tiled export's twin
                # and is skipped; a character or title animation without its PNG is still an error.
                if meta.get("kind") == "tileset":
                    continue
                raise SystemExit("sync_art: %s has no PNG beside it" % fname)
            entry = {
                "name": meta["name"],
                "file": meta["name"] + ".png",
                "frame_w": int(meta["frame_w"]),
                "frame_h": int(meta["frame_h"]),
                "frames": int(meta["frames"]),
                "fps": float(meta.get("fps", 0.0)),
            }
            # Card ASSEMBLE: a tileset is a grid, not a strip, so the index carries the column count and the kind.
            # The runtime reads "columns" to turn a tile id into a cell; a strip keeps the old shape untouched.
            if meta.get("kind") == "tileset":
                entry["kind"] = "tileset"
                entry["columns"] = int(meta.get("columns", 1))
            elif meta.get("kind") == "battle_background":
                # Card t_4275136f: one picture, 256x112, drawn whole at the field origin. The kind is written so a
                # reader of the index can tell a strip from an animation without opening the sidecar, and the
                # runtime is unchanged: frames is 1, so pp_art_draw asks for source x 0.
                entry["kind"] = "background"
            seen.add(meta["name"])
            entries.append(entry)
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


def regenerate_project() -> bool:
    """Rewrite the project files after this run has written into game/datafiles.

    game/datafiles is what the .yyp lists as Included Files, and mirror_streams() writes into it, so
    a landed cue makes the committed .yyp stale the moment it is copied. Nothing ran the generator
    at that point, so the yyp disagreed with disk until a person noticed and an FIX-YYP card was
    raised: five cards, five commits of the same two entries (card t_e40f9705). The landing path
    closes its own loop now, so a cue cannot land through this script and leave the project stale.

    Imported inside the function, not at module scope, because tools/check_build_inputs.py loads
    this module by file path to read its folder constants and has no reason to load the generator.

    Returns True when the project files on disk match the mirror after the call.
    """
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import gen_project

    ok, written = gen_project.regenerate(check=False)
    if written:
        print("project: %d file(s) rewritten after the mirror: %s" % (len(written), ", ".join(written)))
    else:
        print("project: current after the mirror")
    return ok


def main() -> int:
    """Mirror the title art into game/datafiles/art and return 0.

    The title theme stream is mirrored here too, so that anyone who calls main() gets the
    same result as someone who runs the script: a fresh checkout of a commit can only
    regenerate the committed .yyp when both mirrors exist. Measured 2026-10-21: with the
    stream mirrored only from the __main__ block, the PP suite failed with "lists Included
    File streams/title_theme.ogg which is not in game/datafiles".

    A write run ends by regenerating the project files from the mirror it just wrote, because
    the mirror is what the .yyp lists (card t_e40f9705). --no-project turns that off for the
    callers that must measure the committed .yyp rather than repair it, which is the suite
    fixture in tests/conftest.py.
    """
    mirror_streams()
    mirror_sfx()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-project", action="store_true",
                        help="mirror only: do not rewrite game/PrimordialParadox.yyp")
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
            print("STALE: game/datafiles/art/%s" % name)
        if index_stale:
            print("STALE: game/datafiles/art/%s" % INDEX)
        if stale or index_stale:
            return 1
        print("art mirror is current: %d animations" % len(entries))
        return 0

    print("copied %d png, index %s, %d animations" % (len(stale), "written" if index_stale else "current", len(entries)))
    # --check above answers only for the mirror: it writes nothing, and reporting the project
    # graph there would turn this script's exit code into a second, quieter gen_project --check.
    if not args.no_project:
        if not regenerate_project():
            print("project files still disagree with the mirror after regeneration")
            return 1
    return 0


# -----------------------------------------------------------------------------------------------------------------
# Sound effects (card SFX-WIRE). The effects are rendered as 16 bit mono WAV by tools\sfx.py. The game plays them
# with audio_play_sound on a buffer sound, which needs the header lengths, not a guess, so this mirror copies each
# WAV into game\datafiles\sfx and writes sfx\sfx.json with the offset and length measured from the file itself.

SFX_SRC = os.path.join(ROOT, "assets", "audio", "sfx")
SFX_DST = os.path.join(ROOT, "game", "datafiles", "sfx")
SFX_INDEX = "sfx.json"
# Every cue name the game asks for. A cue not in this list is a typo in GML, and the manifest catches it here
# rather than at runtime.
SFX_CUES = (
    "menu_move", "menu_select", "menu_cancel",
    "text_blip_a", "text_blip_b", "text_blip_c",
    "footstep", "door_hatch", "encounter_swoosh", "thunder_soft",
    "car_engine_loop",
    "item_get", "heal", "hit_light", "hit_heavy", "miss", "crit",
    "level_up", "alarm", "wave_wash", "save_jingle", "game_over",
)


def wav_info(path: str) -> dict | None:
    """Read a WAV header: the data chunk offset and length, the sample rate, the channels and the bit depth.

    The chunk walk is the reason this is here: the game hands audio_create_buffer_sound an offset and a byte
    length, and a hardcoded 44 would be wrong the moment a renderer writes a LIST or fact chunk.
    """
    with open(path, "rb") as handle:
        blob = handle.read()
    if len(blob) < 44 or blob[0:4] != b"RIFF" or blob[8:12] != b"WAVE":
        return None
    info = {"rate": 0, "channels": 0, "bits": 0, "offset": 0, "data_bytes": 0}
    pos = 12
    while pos + 8 <= len(blob):
        tag = blob[pos:pos + 4]
        size = int.from_bytes(blob[pos + 4:pos + 8], "little")
        body = pos + 8
        if tag == b"fmt " and body + 16 <= len(blob):
            info["channels"] = int.from_bytes(blob[body + 2:body + 4], "little")
            info["rate"] = int.from_bytes(blob[body + 4:body + 8], "little")
            info["bits"] = int.from_bytes(blob[body + 14:body + 16], "little")
        elif tag == b"data":
            info["offset"] = body
            info["data_bytes"] = min(size, len(blob) - body)
            break
        pos = body + size + (size % 2)
    if info["offset"] == 0 or info["data_bytes"] <= 0 or info["rate"] <= 0 or info["channels"] <= 0:
        return None
    return info


def mirror_sfx() -> list:
    """Copy every cue's WAV into the build and return the manifest cues, sorted by cue name."""
    if not os.path.isdir(SFX_SRC):
        return []
    os.makedirs(SFX_DST, exist_ok=True)
    cues = []
    for cue in sorted(SFX_CUES):
        name = cue + ".wav"
        src = os.path.join(SFX_SRC, name)
        if not os.path.isfile(src):
            print("MISSING sfx source: assets/audio/sfx/%s" % name)
            continue
        info = wav_info(src)
        if info is None:
            print("BAD wav header: assets/audio/sfx/%s" % name)
            continue
        shutil.copy2(src, os.path.join(SFX_DST, name))
        cues.append({
            "bits": info["bits"],
            "channels": info["channels"],
            "data_bytes": info["data_bytes"],
            "file": name,
            "id": cue,
            "offset": info["offset"],
            "rate": info["rate"],
            "sample_format": "buffer_s16" if info["bits"] == 16 else "buffer_u8",
            "seconds": round(info["data_bytes"] / float(info["rate"] * info["channels"] * (info["bits"] // 8)), 3),
        })
    # A WAV the cue list no longer names must not linger in the build.
    for fname in sorted(os.listdir(SFX_DST)):
        if fname.endswith(".wav") and fname[:-4] not in SFX_CUES:
            os.remove(os.path.join(SFX_DST, fname))
    manifest = {
        "format": 1,
        "kind": "sfx",
        "source": "generated by tools/sync_art.py from assets/audio/sfx; 2A03 voices, no sampled or copied audio",
        "cues": cues,
    }
    with open(os.path.join(SFX_DST, SFX_INDEX), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("mirrored %d sound effects into game/datafiles/sfx" % len(cues))
    return cues


def mirror_streams() -> None:
    """Every rendered theme .ogg under assets\\audio\\<name>\\ is copied into game/datafiles/streams.

    One stream used to be enough, so this copied title_theme.ogg and nothing else. The music lane
    added title_theme_v2.ogg, and the committed .yyp lists every stream in the mirror, so a fresh
    checkout could not regenerate that .yyp while this script mirrored only the first theme. The
    rule now is: every .ogg in a theme folder is a stream, named by its own basename, so a faster
    render of the same piece (title_theme_v3_126.ogg beside title_theme_v3.ogg) ships with it.
    """
    base = os.path.join(ROOT, "assets", "audio")
    dst_dir = os.path.join(ROOT, "game", "datafiles", "streams")
    if not os.path.isdir(base):
        return
    for name in sorted(os.listdir(base)):
        folder = os.path.join(base, name)
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.endswith(".ogg"):
                continue
            src = os.path.join(folder, fname)
            if not os.path.isfile(src):
                continue
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src, os.path.join(dst_dir, fname))


if __name__ == "__main__":
    # main() mirrors the streams and the effects itself, so the duplicate mirror_streams() call that
    # used to sit here is gone: it copied every cue twice for nothing.
    sys.exit(main())
