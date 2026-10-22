#!/usr/bin/env python3
"""Derive the title screen's timing macros from data\\title_timing.json and patch them into pp_title.gml.

Why this exists (card TEMPO-1): the theme is a 126 bpm waltz, and every animation on the title has to
sit on that tempo: the lane dashes pass one per beat, the car bobs a pixel and turns its wheels on the
beat, a puff leaves every two beats, the stars twinkle on bar starts, the logo shimmers every four bars
and the storm flashes every eight. A number typed into the GML by hand drifts from the music the first
time somebody changes the bpm, so the numbers live in data\\title_timing.json and this script writes
them into the game.

What it writes: the macros named in DERIVED, each as `#macro NAME <value>` inside the marked tempo
block of game\\scripts\\pp_title\\pp_title.gml. A macro that is missing is added to the block; a macro
that is there has its value replaced. Nothing else in the file is touched, the block is rewritten in a
stable order, and the run is idempotent, so the same json always gives the same bytes.

Usage:
    python tools\\apply_title_timing.py             write the macros
    python tools\\apply_title_timing.py --check     print the diff, exit 1 when the gml is stale
    python tools\\apply_title_timing.py --px 0.5    print the expected scroll of a duration in seconds
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMING = os.path.join(ROOT, "data", "title_timing.json")
GML = os.path.join(ROOT, "game", "scripts", "pp_title", "pp_title.gml")
MARKER = "// Beat macros derived from data\\title_timing.json by tools\\apply_title_timing.py: edit the json, not these."
ANCHOR = "#macro PP_TITLE_SCROLL_PX_PER_STEP"


def load_timing(path: str = TIMING) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    for key in ("bpm", "beat_steps", "bar_steps", "scroll", "car", "exhaust", "stars", "lightning", "shimmer"):
        if key not in data:
            raise SystemExit("title_timing.json has no %r, so the title cannot be timed" % key)
    return data


def derived(timing: dict) -> list[tuple[str, str]]:
    """The macro name and value pairs, in the order the block lists them.

    The values are the json's, not arithmetic on the bpm, so the file the manager reads and the numbers
    the game runs are the same numbers. format_value keeps an integer an integer and a fraction a
    fraction with three decimals, which is what the json states.
    """
    scroll = timing["scroll"]
    car = timing["car"]
    exhaust = timing["exhaust"]
    stars = timing["stars"]
    lightning = timing["lightning"]
    shimmer = timing["shimmer"]
    prompt = timing.get("prompt", {})
    cursor = timing.get("cursor", {})
    return [
        ("PP_TITLE_BPM", fmt(timing["bpm"])),
        ("PP_TITLE_BEAT_STEPS", fmt(timing["beat_steps"])),
        ("PP_TITLE_BAR_STEPS", fmt(timing["bar_steps"])),
        ("PP_TITLE_SCROLL_PX_PER_STEP", fmt(scroll["px_per_step"])),
        ("PP_TITLE_BOB_PX", fmt(car["bob_px"])),
        ("PP_TITLE_BOB_STEPS", fmt(car["bob_steps"])),
        ("PP_TITLE_EXHAUST_STEPS", fmt(exhaust["steps"])),
        ("PP_TITLE_TWINKLE_PERIOD", fmt(stars["steps"])),
        ("PP_TITLE_FLASH_STEPS", fmt(lightning["flash_steps"])),
        ("PP_TITLE_FLASH_MIN_STEPS", fmt(lightning["steps"])),
        ("PP_TITLE_FLASH_MAX_STEPS", fmt(lightning["steps"])),
        ("PP_TITLE_SHIMMER_STEPS", fmt(shimmer["length_steps"])),
        ("PP_TITLE_SHIMMER_PERIOD", fmt(shimmer["steps"])),
        ("PP_TITLE_BLINK_STEPS", fmt(prompt.get("blink_steps", timing["beat_steps"]))),
        ("PP_TITLE_CURSOR_PERIOD", fmt(cursor.get("steps", max(1, timing["beat_steps"] // 2)))),
    ]


def fmt(value) -> str:
    if isinstance(value, float) and not value.is_integer():
        return ("%.3f" % value).rstrip("0").rstrip(".")
    return str(int(value)) if isinstance(value, float) else str(value)


def block_text(pairs: list[tuple[str, str]]) -> list[str]:
    lines = [MARKER]
    for name, value in pairs:
        lines.append("#macro %s %s" % (name, value))
    return lines


def patched_source(source: str, pairs: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """The source with the pairs applied, plus one report line per macro: "name: old -> new" or "added".

    The macros live in one group under MARKER, so a reader of the GML sees all the tempo numbers together and
    the script always has one place to write. Any copy of one of those names elsewhere in the file is removed,
    because two #macro lines for one name is an error the compiler would report and a duplicate a person would
    have to hunt for. The report compares the values that were there with the ones being written, so the run
    prints its own before and after.
    """
    names = {name for name, _ in pairs}
    old_values: dict[str, str] = {}
    kept: list[str] = []
    for line in source.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#macro "):
            parts = stripped.split()
            if len(parts) >= 3 and parts[1] in names:
                old_values.setdefault(parts[1], parts[2])
                continue
        kept.append(line)
    report = []
    for name, value in pairs:
        if name not in old_values:
            report.append("%s: added %s" % (name, value))
        elif old_values[name] != value:
            report.append("%s: %s -> %s" % (name, old_values[name], value))
    # The group is written where the marker already is, or just after the logo fade macro on a first run. The
    # anchor is never one of the derived macros, because those lines were just removed in order to be rewritten.
    block = [MARKER] + ["#macro %s %s" % (name, value) for name, value in pairs]
    if MARKER in kept:
        at = kept.index(MARKER)
        out = kept[:at] + block + kept[at + 1:]
    else:
        at = next((i for i, line in enumerate(kept) if line.strip().startswith("#macro PP_TITLE_FADE_STEPS")), None)
        if at is None:
            raise SystemExit("could not find #macro PP_TITLE_FADE_STEPS in pp_title.gml to anchor the beat macros")
        out = kept[:at + 1] + block + kept[at + 1:]
    return "\n".join(out), report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write the title timing macros from data\\title_timing.json.")
    parser.add_argument("--check", action="store_true", help="exit 1 when pp_title.gml does not match the json")
    parser.add_argument("--px", type=float, default=None, help="print the road layer's travel over this many seconds")
    parser.add_argument("--timing", default=TIMING)
    parser.add_argument("--gml", default=GML)
    args = parser.parse_args(argv)

    timing = load_timing(args.timing)
    pairs = derived(timing)

    if args.px is not None:
        speed = float(timing["scroll"]["px_per_step"])
        steps = args.px * float(timing.get("fps", 60))
        print("%.3f s at %.3f px a step and %s steps a second: %.2f px of road, %.2f beats, %.2f lane dashes"
              % (args.px, speed, timing.get("fps", 60), speed * steps,
                 (speed * steps) / float(timing["scroll"]["dash_px"]),
                 (speed * steps) / float(timing["scroll"]["dash_px"])))
        return 0

    with open(args.gml, "r", encoding="utf-8", newline="") as handle:
        original = handle.read()
    newline = "\r\n" if "\r\n" in original else "\n"
    source = original.replace("\r\n", "\n")
    patched, report = patched_source(source, pairs)
    if args.check:
        if patched != source:
            for line in report:
                print(line)
            print("pp_title.gml is stale against %s" % os.path.relpath(args.timing, ROOT))
            return 1
        print("pp_title.gml matches %s: %d macros" % (os.path.relpath(args.timing, ROOT), len(pairs)))
        return 0
    if patched == source:
        print("pp_title.gml already matches %s: %d macros, nothing written" % (os.path.relpath(args.timing, ROOT), len(pairs)))
        return 0
    with open(args.gml, "w", encoding="utf-8", newline="") as handle:
        handle.write(patched.replace("\n", newline))
    for line in report:
        print(line)
    print("wrote %d timing macros into %s" % (len(pairs), os.path.relpath(args.gml, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
