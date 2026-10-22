#!/usr/bin/env python3
"""measure_title_scroll_native.py: measure the title's scroll from the game's own frames, layer by layer.

Why this exists (card TEMPO-1, review round 1): the window copy of this PC resamples the game (111 colours where the
art is palette clean, only 74.7 percent of 3x3 blocks uniform) and one PowerShell copy costs about 7.5 s, so a pair of
copies could never be half a second apart, and an independent cross correlation of such a pair found no scroll at all.
The frames this tool reads are written by the game itself, with screen_save inside the title's draw, at three steps a
half beat apart (pp_title_capture_frames, PP_TITLE_SCROLL_CAPTURE_FIRST and _GAP). So the elapsed time is not a
stopwatch reading: it is the difference between two step counts the game logged, and the pixels are the game's own.

What it measures: for each band of the frame, the horizontal distance the band's content travelled between two frames,
by minimum mean absolute difference. Each band is cut to rows that carry ONE scrolling layer and no sprite, because
the first pass of this measurement read the whole road strip and got 0 px: the car, its exhaust and the road sign sit
in that strip at screen fixed positions, and their bobbing and cycling dominated the match. The bands below were read
off the game's own frames rather than guessed: the sky's glare (rows 112-123), the fields (136-156), the verge
(160-184), and the road's lane dashes (196-203) with the car's columns excluded.

Usage:
    python tools\\measure_title_scroll_native.py --frames output\\title_scroll_1_native.png \
        output\\title_scroll_2_native.png output\\title_scroll_3_native.png --steps 290 304 318 \
        --scroll 160.080 167.810 175.540

Exit codes:
    0  every band moved by its own layer's expected distance, within TOLERANCE_PX
    1  a band's movement did not match its layer, or a band had no measurable content
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
TIMING = os.path.join(ROOT, "data", "title_timing.json")
TITLE = os.path.join(ROOT, "data", "title.json")
# (name, first row, last row inclusive, first column, last column exclusive). Each band is one layer's own rows with
# the screen fixed sprites left out: the car occupies about x 76-120 of the road strip, so the road band reads the
# right hand side of the lane, and rows 196-203 are above the road sign and the car's body.
BANDS = (
    ("downs", "title_L3_downs", 112, 123, 0, 256),
    ("fields", "title_L4_fields", 136, 156, 0, 256),
    ("verge", "title_L5_verge", 160, 184, 0, 256),
    ("road dashes", "title_L6_road", 196, 203, 140, 256),
)
# A band's shift is searched this far either way. Half a beat is at most 10 px on this title, and the road's dashes
# repeat every 16 px, so the search stays under half that period: the first pass searched +-24 and reported a travel of
# -24 px on one pair, which is the same alignment as +8 px seen one dash earlier. Twelve keeps every answer inside one
# dash and keeps the match unambiguous.
SEARCH_PX = 12
# A shift is only believed when the mean absolute difference at that shift is this small. The game's own frames are
# exact, so a real match scores near zero (0.00 to 0.29 measured) and a band with no matching content scores 3 or more.
MATCH_SCORE = 1.0
# The drawn offsets are rounded to whole pixels per frame, so a band can land a pixel either side of the tempo's
# arithmetic. One pixel is the tolerance, and the measured number is printed, never smoothed.
TOLERANCE_PX = 1


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def frame_array(path):
    """The frame as an (h, w, 3) int16 array of the game's own pixels.

    A 768x720 screen_save is the exact 3x of the game screen, so it is sampled every third pixel instead of resized: a
    filter would blend two game pixels into a third and the dashes this measurement follows would lose their edges.
    """
    with Image.open(path) as handle:
        image = handle.convert("RGB")
    array = np.asarray(image).astype(np.int16)
    if array.shape[0] % 240 == 0 and array.shape[1] % 256 == 0:
        factor = array.shape[1] // 256
        if factor > 1:
            array = array[::factor, ::factor]
    return array


def shift_between(first, second, limit=SEARCH_PX):
    """(travel, score) for the horizontal distance the band's content moved between the two frames.

    The layers are drawn at a negative offset that grows with the scroll, so the content moves LEFT as time passes.
    A candidate shift d compares first[x] with second[x + d]; the content satisfies second[x] = first[x + s] for a
    leftward travel s, so the match sits at d = -s and travel = -d. Getting this sign the wrong way round is what
    made the first pass report a negative travel on every band.
    """
    width = first.shape[1]
    best = (None, None)
    for d in range(-limit, limit + 1):
        if d >= 0:
            left_a, left_b, span = 0, d, width - d
        else:
            left_a, left_b, span = -d, 0, width + d
        if span < width // 2:
            continue
        difference = np.abs(first[:, left_a:left_a + span] - second[:, left_b:left_b + span]).mean()
        if best[0] is None or difference < best[0]:
            best = (difference, d)
    if best[0] is None:
        return None, None
    return -best[1], float(best[0])


def main():
    parser = argparse.ArgumentParser(description="Measure the title scroll from the game's own frames.")
    parser.add_argument("--frames", nargs="+", required=True)
    parser.add_argument("--steps", nargs="+", type=int, required=True)
    parser.add_argument("--scroll", nargs="+", type=float, required=True)
    parser.add_argument("--json", default="")
    parser.add_argument("--timing", default=TIMING)
    parser.add_argument("--title", default=TITLE)
    args = parser.parse_args()

    if not (len(args.frames) == len(args.steps) == len(args.scroll)):
        print("each frame needs a step count and a scroll value, and the three lists are %d, %d and %d long"
              % (len(args.frames), len(args.steps), len(args.scroll)))
        return 1

    timing = load_json(args.timing)
    title = load_json(args.title)
    speeds = {layer["name"]: float(layer.get("speed", 0.0)) for layer in title["layers"]}
    arrays = [frame_array(path) for path in args.frames]
    print("timing: %s bpm, %.3f px a step, %s steps a second"
          % (timing["bpm"], timing["scroll"]["px_per_step"], timing["fps"]))
    for path, step, scroll, array in zip(args.frames, args.steps, args.scroll, arrays):
        print("frame %s: step %d, scroll %.3f, %dx%d" % (os.path.basename(path), step, scroll,
                                                         array.shape[1], array.shape[0]))
    print("")

    results = {"timing": {"bpm": timing["bpm"], "px_per_step": timing["scroll"]["px_per_step"],
                          "fps": timing["fps"]},
               "frames": [{"path": path, "step": step, "scroll": scroll}
                          for path, step, scroll in zip(args.frames, args.steps, args.scroll)],
               "bands": []}
    failures = []
    for index in range(1, len(arrays)):
        first, second = arrays[index - 1], arrays[index]
        steps = args.steps[index] - args.steps[index - 1]
        seconds = steps / float(timing["fps"])
        print("pair %d: %d steps = %.3f s at %s fps" % (index, steps, seconds, timing["fps"]))
        for name, layer, top, bottom, x0, x1 in BANDS:
            speed = speeds.get(layer, 0.0)
            # The distance the layer's drawn offset moved, exactly as pp_title_draw_layers rounds it, plus the exact
            # tempo's own arithmetic for the same steps. Both are printed so a pixel of rounding is visible and not
            # hidden inside a tolerance.
            drawn = round(args.scroll[index] * speed) - round(args.scroll[index - 1] * speed)
            exact = timing["scroll"]["px_per_step"] * steps * speed
            travel, score = shift_between(first[top:bottom + 1, x0:x1].mean(axis=2),
                                          second[top:bottom + 1, x0:x1].mean(axis=2))
            record = {"pair": index, "steps": steps, "band": name, "layer": layer, "speed": speed,
                      "measured_px": travel, "score": None if score is None else round(score, 3),
                      "drawn_offset_px": drawn, "exact_tempo_px": round(exact, 2),
                      "tolerance_px": TOLERANCE_PX}
            if travel is None or score is None or score > MATCH_SCORE:
                record["verdict"] = "NO MATCH"
                failures.append("%s on pair %d: no content matched (best score %.2f, limit %.2f)"
                                % (name, index, -1.0 if score is None else score, MATCH_SCORE))
                print("  %-12s rows %3d-%3d: NO MATCH (best score %.2f, limit %.1f)"
                      % (name, top, bottom, -1.0 if score is None else score, MATCH_SCORE))
                results["bands"].append(record)
                continue
            within = abs(travel - drawn) <= TOLERANCE_PX
            record["verdict"] = "MATCH" if within else "MISMATCH"
            print("  %-12s rows %3d-%3d: measured %+d px (score %.2f); drawn offset %+d px, exact tempo %.2f px -> %s"
                  % (name, top, bottom, travel, score, drawn, exact, record["verdict"]))
            if not within:
                failures.append("%s on pair %d measured %+d px against the layer's %+d px (exact %.2f)"
                                % (name, index, travel, drawn, exact))
            results["bands"].append(record)
        print("")

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
        print("wrote %s" % args.json)

    if failures:
        print("")
        for failure in failures:
            print("FAIL %s" % failure)
        return 1
    print("PASS every band travelled the distance its own layer's tempo sets, within %d px" % TOLERANCE_PX)
    return 0


if __name__ == "__main__":
    sys.exit(main())
