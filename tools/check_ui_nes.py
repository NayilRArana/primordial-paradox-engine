#!/usr/bin/env python3
"""check_ui_nes.py: the three UI windows are NES legal, measured on the layouts json and the 3x previews.

What it reads, and why each file is evidence:

    data\\ui_layouts.json                     the window, band, cursor and sprite rectangles in whole tiles
    game\\sprites_src\\ui\\screens\\ui_<name>.png   the 1x frame the game draws (256x240)
    output\\ui_<name>_preview.png             the 3x preview the manager looks at (768x720)
    output\\ui_<name>_nes_report.json         the NES report committed beside them

The four things it proves, per screen:

  1. grid: every rectangle is a whole number of 8x8 tiles, sits inside the 32x30 tile frame, and a window is
     at least 3x3 tiles so it can hold its own one tile border plus an interior. Sprite rectangles are in
     pixels and must also be multiples of 8.
  2. the preview is the frame: output\\ui_<name>_preview.png is exactly game\\...\\ui_<name>.png at 3x, pixel
     for pixel (nearest neighbour). A preview that is not the frame proves nothing about the frame.
  3. attribute areas: measured on the 3x preview, every 16x16 background area carries at most 3 colours
     besides the one shared backdrop, and the frame carries at most 16 distinct colours (the chip ceiling is
     25; the UI set is held to 16 so a window can be dropped on any scene).
  4. the report agrees: output\\ui_<name>_nes_report.json passes, states 0 attribute area violations, and its
     numbers (blocks, distinct colour sets, colours on screen) equal what this run recomputes from the
     current preview. A report that describes some earlier frame fails here, which is the whole point:
     before this tool the reports were dated 2026-10-22 00:00 and the frames 22:47, and nothing noticed.

Usage:
    python tools\\check_ui_nes.py
    python tools\\check_ui_nes.py --write      # regenerate the three reports from the current frames first
    python tools\\check_ui_nes.py --quiet

--write calls tools\\nes_composite_check.py once per screen, writes output\\ui_checks\\<name>_composite.json,
the overlay it draws and output\\ui_<name>_nes_report.json, then runs the same checks. It never edits
data\\ui_layouts.json: that file belongs to tools\\art\\make_ui_nes.py, which refuses to write a layout whose
text does not fit its own window.

Exit code 0 when all three screens pass, 1 on any failure. No em dashes, no en dashes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from PIL import Image

CELL = 8
AREA = 16
SCALE = 3
FRAME_W = 256
FRAME_H = 240
MAX_COLOURS = 16
COLOURS_PER_AREA = 3


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def palette_entry(root: str, index: int) -> tuple:
    """The 2C02 output for an index in data\\nes_palette.json, as (r, g, b)."""
    data = load_json(os.path.join(root, "data", "nes_palette.json"))
    value = data["colours"][index].lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def tile_rect(rect: dict, label: str) -> list:
    """Problems with one tile rectangle: whole tiles, positive, inside the frame."""
    problems = []
    for key in ("x", "y", "w", "h"):
        value = rect.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            problems.append("%s.%s is %r, not a whole tile count" % (label, key, value))
    if problems:
        return problems
    if rect["x"] < 0 or rect["y"] < 0:
        problems.append("%s starts off frame at %d,%d" % (label, rect["x"], rect["y"]))
    if rect["w"] < 1 or rect["h"] < 1:
        problems.append("%s is %dx%d tiles" % (label, rect["w"], rect["h"]))
    if rect["x"] + rect["w"] > FRAME_W // CELL or rect["y"] + rect["h"] > FRAME_H // CELL:
        problems.append("%s runs off the frame: %d,%d %dx%d of %dx%d tiles"
                        % (label, rect["x"], rect["y"], rect["w"], rect["h"],
                           FRAME_W // CELL, FRAME_H // CELL))
    return problems


def point(rect: dict, label: str) -> list:
    """Problems with one tile position: whole tiles, inside the frame. A cursor is a position, not a box."""
    problems = []
    cols, rows = FRAME_W // CELL, FRAME_H // CELL
    for key, limit in (("x", cols), ("y", rows)):
        value = rect.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            return ["%s.%s is %r, not a whole tile count" % (label, key, value)]
        if value < 0 or value >= limit:
            problems.append("%s.%s is %d, off the %d tile frame" % (label, key, value, limit))
    return problems


def px_rect(rect: dict, label: str) -> list:
    """Problems with one pixel rectangle: multiples of 8 on both edges, inside the frame."""
    problems = []
    for key in ("x", "y", "w", "h"):
        value = rect.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            return ["%s.%s is %r, not a whole pixel count" % (label, key, value)]
        if value % CELL:
            problems.append("%s.%s is %d px, not a multiple of %d" % (label, key, value, CELL))
    if not problems:
        if rect["x"] + rect["w"] > FRAME_W or rect["y"] + rect["h"] > FRAME_H:
            problems.append("%s runs off the frame: %d,%d %dx%d"
                            % (label, rect["x"], rect["y"], rect["w"], rect["h"]))
    return problems


def measure_preview(preview_path: str, backdrop: tuple) -> dict:
    """Attribute areas and colours, measured on the 3x preview the manager opens."""
    with Image.open(preview_path) as img:
        preview = img.convert("RGB")
    if preview.size != (FRAME_W * SCALE, FRAME_H * SCALE):
        return {"error": "preview is %dx%d, expected %dx%d at %dx"
                         % (preview.size + (FRAME_W * SCALE, FRAME_H * SCALE, SCALE))}
    pixels = preview.load()
    area_px = AREA * SCALE
    offending = []
    colour_sets = set()
    for ay in range(0, FRAME_H * SCALE, area_px):
        for ax in range(0, FRAME_W * SCALE, area_px):
            colours = set()
            for y in range(ay, ay + area_px):
                for x in range(ax, ax + area_px):
                    colours.add(pixels[x, y])
            owned = colours - {backdrop}
            if owned:
                colour_sets.add(frozenset(owned))
            if len(owned) > COLOURS_PER_AREA:
                offending.append({"area": [ax // area_px, ay // area_px],
                                  "tile": [ax // (CELL * SCALE), ay // (CELL * SCALE)],
                                  "colours": sorted("#%02x%02x%02x" % rgb for rgb in owned)})
    screen_colours = set()
    for y in range(preview.height):
        for x in range(preview.width):
            screen_colours.add(pixels[x, y])
    return {"areas": (FRAME_W // AREA) * (FRAME_H // AREA),
            "offending": offending,
            "colour_sets": len(colour_sets),
            "colours": len(screen_colours),
            "colour_list": sorted("#%02x%02x%02x" % rgb for rgb in screen_colours)}


def preview_is_the_frame(frame_path: str, preview_path: str) -> list:
    """Every frame pixel repeated 3x3 in the preview, or a list of the first disagreements."""
    with Image.open(frame_path) as img:
        frame = img.convert("RGB")
    with Image.open(preview_path) as img:
        preview = img.convert("RGB")
    if frame.size != (FRAME_W, FRAME_H):
        return ["frame is %dx%d, expected %dx%d" % (frame.size + (FRAME_W, FRAME_H))]
    if preview.size != (FRAME_W * SCALE, FRAME_H * SCALE):
        return ["preview is %dx%d, expected %dx%d at %dx"
                % (preview.size + (FRAME_W * SCALE, FRAME_H * SCALE, SCALE))]
    fp = frame.load()
    pp = preview.load()
    problems = []
    for y in range(FRAME_H):
        for x in range(FRAME_W):
            want = fp[x, y]
            for dy in range(SCALE):
                for dx in range(SCALE):
                    got = pp[x * SCALE + dx, y * SCALE + dy]
                    if got != want:
                        problems.append("preview pixel %d,%d is %s, the frame pixel %d,%d is %s"
                                        % (x * SCALE + dx, y * SCALE + dy, got, x, y, want))
                        if len(problems) >= 5:
                            return problems
    return problems


def write_report(root: str, screen: dict, backdrop_index: int) -> list:
    """Regenerate one report from the current frame through tools\\nes_composite_check.py."""
    frame_png = os.path.join(root, screen["frame_png"].replace("\\", "/"))
    base = os.path.basename(frame_png)[:-4]
    sprites_json = os.path.join(os.path.dirname(frame_png), base + "_sprites.json")
    checks_dir = os.path.join(root, "output", "ui_checks")
    os.makedirs(checks_dir, exist_ok=True)
    overlay = os.path.join(checks_dir, "_" + screen["name"] + "_overlay.png")
    composite = os.path.join(checks_dir, screen["name"] + "_composite.json")
    report = os.path.join(root, "output", "ui_%s_nes_report.json" % screen["name"])
    command = [sys.executable, os.path.join(root, "tools", "nes_composite_check.py"), frame_png,
               "--sprites", sprites_json, "--backdrop", str(backdrop_index),
               "--overlay", overlay, "--json", composite, "--quiet"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return ["%s: nes_composite_check exit %d: %s"
                % (screen["name"], result.returncode, (result.stdout + result.stderr).strip()[-400:])]
    with open(composite, "r", encoding="utf-8") as handle:
        payload = load_json(composite)
    with open(report, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return []


def check_screen(root: str, screen: dict, backdrop: tuple) -> tuple:
    """All four proofs for one screen. Returns (problems, report line)."""
    problems = []
    name = screen["name"]

    for label_key in ("windows", "bands", "enemies", "party"):
        for index, rect in enumerate(screen.get(label_key, [])):
            problems.extend(tile_rect(rect, "%s.%s[%d] %s"
                                      % (name, label_key, index, rect.get("name") or rect.get("member", ""))))
    for index, rect in enumerate(screen.get("cursors", [])):
        problems.extend(point(rect, "%s.cursors[%d] %s" % (name, index, rect.get("name", ""))))
    for index, rect in enumerate(screen.get("sprites", [])):
        problems.extend(px_rect(rect, "%s.sprites[%d] %s" % (name, index, rect.get("role", ""))))
    for label_key in ("enemies", "party"):
        for index, rect in enumerate(screen.get(label_key, [])):
            declared = rect.get("pixels")
            if isinstance(declared, str) and isinstance(rect.get("w"), int) and isinstance(rect.get("h"), int):
                want = "%dx%d" % (rect["w"] * CELL, rect["h"] * CELL)
                if declared.replace(" ", "") != want:
                    problems.append("%s.%s[%d] says %s pixels but is %d x %d tiles, which is %s"
                                    % (name, label_key, index, declared, rect["w"], rect["h"], want))
    for window in screen.get("windows", []):
        if window.get("w", 0) < 3 or window.get("h", 0) < 3:
            problems.append("%s.window %s is %dx%d tiles, too small to hold its own border"
                            % (name, window.get("name"), window.get("w", 0), window.get("h", 0)))

    frame_png = os.path.join(root, screen["frame_png"].replace("\\", "/"))
    preview_png = os.path.join(root, screen["preview_png"].replace("\\", "/"))
    for path, what in ((frame_png, "frame_png"), (preview_png, "preview_png")):
        if not os.path.isfile(path):
            problems.append("%s.%s is missing: %s" % (name, what, screen[what]))
    if problems:
        return problems, None

    if screen.get("preview_scale") != SCALE:
        problems.append("%s.preview_scale is %r, expected %d" % (name, screen.get("preview_scale"), SCALE))
    problems.extend("%s: %s" % (name, line) for line in preview_is_the_frame(frame_png, preview_png))

    measured = measure_preview(preview_png, backdrop)
    if "error" in measured:
        problems.append("%s: %s" % (name, measured["error"]))
        return problems, None
    if measured["offending"]:
        for hit in measured["offending"][:5]:
            problems.append("%s: area %s (tile %s) carries %d colours besides the backdrop: %s"
                            % (name, hit["area"], hit["tile"], len(hit["colours"]),
                               " ".join(hit["colours"])))
        problems.append("%s: %d attribute areas violate the 3 colour rule"
                        % (name, len(measured["offending"])))
    if measured["colours"] > MAX_COLOURS:
        problems.append("%s: %d colours on screen, the UI set allows %d: %s"
                        % (name, measured["colours"], MAX_COLOURS, " ".join(measured["colour_list"])))

    report_path = os.path.join(root, "output", "ui_%s_nes_report.json" % name)
    if not os.path.isfile(report_path):
        problems.append("%s: no report at output\\ui_%s_nes_report.json" % (name, name))
        return problems, None
    report = load_json(report_path)
    background = report.get("background", {})
    screen_block = report.get("screen", {})
    if report.get("ok") is not True:
        problems.append("%s: the report says ok %r" % (name, report.get("ok")))
    if background.get("problems"):
        problems.append("%s: the report lists %d background problems" % (name, len(background["problems"])))
    if background.get("offending_blocks"):
        problems.append("%s: the report lists %d offending blocks"
                        % (name, len(background["offending_blocks"])))
    if background.get("blocks") != measured["areas"]:
        problems.append("%s: the report measured %r blocks, this run measured %d"
                        % (name, background.get("blocks"), measured["areas"]))
    if background.get("distinct_colour_sets") != measured["colour_sets"]:
        problems.append("%s: the report says %r distinct colour sets, this run measured %d: regenerate the report"
                        % (name, background.get("distinct_colour_sets"), measured["colour_sets"]))
    if screen_block.get("colours") != measured["colours"]:
        problems.append("%s: the report says %r colours on screen, this run measured %d: regenerate the report"
                        % (name, screen_block.get("colours"), measured["colours"]))
    reported_path = str(report.get("frame", {}).get("path", "")).replace("\\", "/")
    if not reported_path.endswith(screen["frame_png"]):
        problems.append("%s: the report describes %s, not %s" % (name, reported_path or "no frame", screen["frame_png"]))

    line = ("%s: %d windows on whole tiles, preview is the frame at %dx, %d areas 0 violations, "
            "%d colour sets, %d colours (limit %d), report agrees"
            % (name, len(screen.get("windows", [])), SCALE, measured["areas"],
               measured["colour_sets"], measured["colours"], MAX_COLOURS))
    return problems, line


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="prove the three UI windows are NES legal on the real files")
    parser.add_argument("--root", default=None, help="repository root; default is the parent of tools")
    parser.add_argument("--write", action="store_true",
                        help="regenerate output\\ui_<name>_nes_report.json from the current frames first")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root) if args.root else repo_root()
    layouts = load_json(os.path.join(root, "data", "ui_layouts.json"))
    if layouts.get("kind") != "ui_layouts":
        print("data\\ui_layouts.json is kind %r, expected ui_layouts" % layouts.get("kind"))
        return 1
    frame = layouts.get("frame", {})
    if (frame.get("w"), frame.get("h"), frame.get("tile"), frame.get("cols"), frame.get("rows")) != \
            (FRAME_W, FRAME_H, CELL, FRAME_W // CELL, FRAME_H // CELL):
        print("data\\ui_layouts.json frame is %r, expected %dx%d at %d px, %dx%d tiles"
              % (frame, FRAME_W, FRAME_H, CELL, FRAME_W // CELL, FRAME_H // CELL))
        return 1
    backdrop_index = layouts.get("colours", {}).get("backdrop")
    if not isinstance(backdrop_index, int):
        print("data\\ui_layouts.json colours.backdrop is %r, expected a nes_palette index" % backdrop_index)
        return 1
    backdrop = palette_entry(root, backdrop_index)

    screens = layouts.get("screens", [])
    if len(screens) != 3:
        print("data\\ui_layouts.json has %d screens, expected three (battle, dialogue, menu)" % len(screens))
        return 1

    problems = []
    lines = []
    for screen in screens:
        if args.write:
            problems.extend(write_report(root, screen, backdrop_index))
            if problems:
                break
        screen_problems, line = check_screen(root, screen, backdrop)
        problems.extend(screen_problems)
        if line:
            lines.append(line)

    if not args.quiet:
        for line in lines:
            print(line)
    if problems:
        for line in problems:
            print("FAIL " + line)
        return 1
    print("PASS: 3 screens, %d colours on screen at most, 0 attribute area violations, every report regenerated "
          "or agreeing with the current previews" % max(1, MAX_COLOURS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
