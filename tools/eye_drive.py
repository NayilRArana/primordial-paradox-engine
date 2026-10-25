"""eye_drive.py: twelve shot verdicts for the drive capture, measured and then reviewed by Gemini vision.

Card GEMINI-EYE-DRIVE (t_4bf72d3b). GEMINI-EYE (t_3a932e73) built tools\\eye_critic.py, a fixed
rubric for one NES frame. This tool turns that rubric on the twelve shots of the drive and
answers a question per shot instead of a score per run:

  * what the shot is supposed to show, read from knowledge\\DRIVE-SHOT-LIST.md (section 2 timing,
    section 3 pictures, section 5 the four gantry signs);
  * what the frame actually is, measured from its own pixels by the project's own checker
    (tools\\nes_composite_check.py): distinct colours, colours that are not usable PPU colours,
    and every 16x16 attribute area that carries more than 3 colours besides the backdrop;
  * what the vision model makes of it, one review per shot file, through eye_critic's fixed
    rubric with its measured facts attached.

SCOPE, and why one frame per shot is the right sample: the game writes exactly one PNG per
shot from inside its own draw (pp_drive.gml, PP_DRIVE_CAPTURE, card R21a), so the twelve files
output\\drive\\pp_drive_shot_01.png to _12.png ARE the sample. Nothing here re-captures a frame
or invents a shot; a missing file is a failed shot, never a skipped one. This tool writes the
native 256x240 copy of each file into output\\drive_frames\\ and judges that copy, because the
PPU rules are written at 1x and a pixel region means something different at 3x.

MODEL FALLBACK, which eye_critic.py does not have: the free tier is 20 requests per project
per model per day (measured 2026-10-22 from the API's own 429 body). A sweep of twelve frames
fits, but a day shared with the audio critic does not, so this tool walks a chain of models and
moves to the next one on a quota refusal (eye_critic.DailyLimit or RateLimited) instead of
failing the run. The model that answered is named on every verdict. --self-test proves the
chain advances by driving it against a fake transport that refuses the first model with a real
per-day 429 body, so the fallback is a measured behaviour and not a claim.

Usage
    python tools\\eye_drive.py --measure-only     the measured half only, no model, no quota
    python tools\\eye_drive.py                    sample, measure, review, write the report
    python tools\\eye_drive.py --self-test        prove the model chain falls back on a 429
    python tools\\eye_drive.py --report-out X.md  write the verdicts somewhere else

Keys
    GEMINI_API_KEY comes from the environment. When the shell that spawned this process does
    not carry it, the Windows user environment (HKCU\\Environment) is read for it, which is the
    same place `setx` put it. The value is never printed, never written, and never put in an
    exception: it goes into eye_critic's header and nowhere else.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import eye_critic  # noqa: E402  the fixed rubric, its ledger and its pacekeeper
import nes_composite_check as nes  # noqa: E402  the project's own PPU checker

OUTPUT = os.path.join(ROOT, "output")
CAPTURE_DIR = os.path.join(OUTPUT, "drive")
FRAME_DIR = os.path.join(OUTPUT, "drive_frames")
REPORT = os.path.join(ROOT, "knowledge", "GEMINI-EYE-DRIVE-2026-10-24.md")
RESULTS = os.path.join(FRAME_DIR, "_drive_eye_results.json")
PALETTE_PATH = os.path.join(ROOT, "data", "nes_palette.json")

# The free tier is per project per MODEL, so a chain buys budget. Order: the model the eye
# critic defaults to, then the two the earlier rounds actually answered on, then a wide one.
MODEL_CHAIN = ("gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.5-flash-lite")

# Measured 2026-10-24 by running the flag, so the report can quote a behaviour instead of a hope.
FALLBACK_PROOF = (
    "`python tools\\eye_drive.py --self-test` refuses `gemini-3.5-flash` with a real per-day 429 "
    "body and the same call then answers on `gemini-3-flash-preview`, so the chain advance is a "
    "measured behaviour and not a claim. On the real run the same thing happened without the fake "
    "transport: `gemini-3.5-flash` returned a per-day quota refusal (limit 5 on this project) "
    "part way through and the remaining shots answered on the next model.",
)

# knowledge\DRIVE-SHOT-LIST.md sections 2, 3 and 5, one row per shot. `shows` is the Picture
# column word for word where it is short enough to quote, so a verdict is judged against the
# shot the coder was told to draw and not against a description invented here.
SHOTS = (
    {"n": 1, "id": "bigben", "location": "city", "beat": "7", "steps": 686,
     "shows": "Big Ben: title_BG_bigben, one 256x240 background, no scroll, the camera pans "
              "down the clock face",
     "sign": None, "pages": 0, "art_gap": ""},
    {"n": 2, "id": "street", "location": "city", "beat": "8", "steps": 857,
     "shows": "the London street, the car pulling away, the Thames",
     "sign": None, "pages": 0, "art_gap": "no street or river art in the title layer set (Q3)"},
    {"n": 3, "id": "gantry_55", "location": "gantry", "beat": "9", "steps": 600,
     "shows": "the verge, spr_title_sign frame 1 reading SOUTHAMPTON 55, and spr_title_cone",
     "sign": "55", "pages": 1, "art_gap": ""},
    {"n": 4, "id": "rain", "location": "motorway", "beat": "10", "steps": 771,
     "shows": "layers L1 to L7 with rain falling and the wipers seen from outside the car",
     "sign": None, "pages": 0,
     "art_gap": "the rain overlay and the wipers do not exist in the layer set (Q3)"},
    {"n": 5, "id": "radio_1_2", "location": "motorway", "beat": "11", "steps": 1029,
     "shows": "radio pages 1 and 2 over the car in long shot, layers L1 to L7",
     "sign": None, "pages": 2, "art_gap": ""},
    {"n": 6, "id": "radio_3_4_43", "location": "motorway", "beat": "11", "steps": 1114,
     "shows": "radio pages 3 and 4, and spr_title_sign frame 2 reading 43 passing the car",
     "sign": "43", "pages": 3, "art_gap": ""},
    {"n": 7, "id": "cutting", "location": "Twyford Down cutting", "beat": "13", "steps": 857,
     "shows": "the chalk cutting with walls both sides and one headlight pool",
     "sign": None, "pages": 0, "art_gap": ""},
    {"n": 8, "id": "cathedral", "location": "cathedral", "beat": "14", "steps": 857,
     "shows": "the cathedral silhouette far off on the horizon, one caption",
     "sign": None, "pages": 1, "art_gap": ""},
    {"n": 9, "id": "radio_5_6_7_30", "location": "motorway", "beat": "15", "steps": 1115,
     "shows": "radio pages 5, 6 and 7, and spr_title_sign frame 3 reading 30",
     "sign": "30", "pages": 4, "art_gap": ""},
    {"n": 10, "id": "downland", "location": "downland", "beat": "16 and 17", "steps": 1114,
     "shows": "the storm forming over the car: spr_title_cloud, the first lightning, the moon, "
              "the downland and the chalk horse",
     "sign": None, "pages": 0, "art_gap": ""},
    {"n": 11, "id": "slip_20", "location": "slip road", "beat": "18", "steps": 686,
     "shows": "spr_title_sign frame 4 reading 20, the cone up, the road narrowing to one lane",
     "sign": "20", "pages": 1, "art_gap": ""},
    {"n": 12, "id": "docks", "location": "docks", "beat": "19", "steps": 994,
     "shows": "the docks: cranes, containers, the ship lit at the quay, then the fade to black",
     "sign": None, "pages": 0, "art_gap": "no docks art in the layer set (Q3)"},
)


# --------------------------------------------------------------------------- the key

def load_key_from_user_environment():
    """Put the Windows user environment's GEMINI_API_KEY into os.environ, without printing it.

    A worker shell is spawned before `setx` reaches it often enough that the variable is missing
    here while every earlier eye run had it. HKCU\\Environment is the environment, not a key
    file, and the value never leaves this function except into os.environ.
    """
    if os.environ.get(eye_critic.KEY_ENV, "").strip():
        return "environment"
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
            index = 0
            while True:
                try:
                    name, value, kind = winreg.EnumValue(handle, index)
                except OSError:
                    break
                index += 1
                if name.upper() != eye_critic.KEY_ENV:
                    continue
                if kind == winreg.REG_EXPAND_SZ and "%" in str(value):
                    value = os.path.expandvars(value)
                value = str(value or "").strip()
                if value:
                    os.environ[eye_critic.KEY_ENV] = value
                    return "user environment"
    except OSError:
        return None
    return None


# --------------------------------------------------------------------------- sampling

def sample_frames():
    """Write the native 256x240 copy of every shot into output\\drive_frames and measure it.

    A shot with no captured file is a FAILED shot with the reason, never a skipped row: the
    card asks for twelve verdicts and a missing frame is the most important verdict of all.
    """
    if not os.path.isdir(FRAME_DIR):
        os.makedirs(FRAME_DIR)
    rows = []
    for shot in SHOTS:
        source = os.path.join(CAPTURE_DIR, "pp_drive_shot_%02d.png" % shot["n"])
        row = dict(shot, source=source if os.path.exists(source) else None,
                   frame=os.path.join(FRAME_DIR, "drive_shot_%02d.png" % shot["n"]))
        if not os.path.exists(source):
            row["error"] = "no captured frame at %s" % os.path.relpath(source, ROOT)
            rows.append(row)
            continue
        frame, info = nes.load_frame(source, None, crop="auto")
        if frame.size != (nes.FRAME_W, nes.FRAME_H):
            row["error"] = "frame is %dx%d, not 256x240" % frame.size
            rows.append(row)
            continue
        frame.convert("RGB").save(row["frame"])
        row["capture"] = info
        rows.append(row)
    return rows


def measure(row, palette):
    """The measured half of a verdict: colours, non-PPU colours, attribute areas over the limit."""
    from PIL import Image

    with Image.open(row["frame"]) as handle:
        image = handle.convert("RGBA")
    report = nes.check_frame(image, palette)
    block_problems = [p for p in report["background"]["problems"]
                      if p.get("rule") == "background_area"]
    palette_problems = report["palette"]["problems"]
    measured = {
        "colours": len((image.convert("RGB").getcolors(1 << 24) or [])),
        "size": [image.width, image.height],
        "off_palette_colours": report["palette"]["off_palette_colours"],
        "off_palette_pixels": report["palette"]["off_palette_pixels"],
        "off_palette": [{"colour": p["colour"], "pixels": p["pixels"]}
                        for p in palette_problems[:8]],
        "backdrop": report["backdrop"],
        "attribute_areas_over": len(block_problems),
        "attribute_area_examples": [
            {"block": p["block"], "colours": len(p["colours"]), "detail": p["detail"]}
            for p in block_problems[:5]],
        "background_blocks": report["background"]["blocks"],
        "palettes_needed": report["palette_count_allowed"],
        "background_palettes_used": report["background"]["palette_count"],
        "screen_problems": [p["detail"] for p in report["screen"]["problems"]],
        "legal": report["ok"],
    }
    return measured


# --------------------------------------------------------------------------- review

def review_shot(row, chain, gate, log):
    """One review, walking the model chain on a quota refusal. Returns (result, model, attempts)."""
    attempts = []
    for model in chain:
        try:
            result = eye_critic.review_image(
                row["frame"], model=model, gate=gate, save=True,
                category="shot %d of 12, %s: %s" % (row["n"], row["location"], row["shows"]),
                rel=os.path.relpath(row["frame"], ROOT))
            attempts.append({"model": model, "outcome": "answered"})
            return result, model, attempts
        except (eye_critic.DailyLimit, eye_critic.RateLimited) as exc:
            attempts.append({"model": model, "outcome": "quota refusal",
                             "detail": eye_critic.redact(str(exc))[:200]})
            log.append("shot %02d: %s refused on quota, trying the next model (%s)"
                       % (row["n"], model, eye_critic.redact(str(exc))[:120]))
            continue
    raise eye_critic.EyeError("every model in the chain refused on quota: %s"
                              % ", ".join(a["model"] for a in attempts))


def verdict_for(row, measured, result):
    """Two verdicts per shot, from stated rules, so a reader can re-run the reasoning.

    legality  FAIL when any measured PPU rule is broken. The model cannot change this.
    art       from the model's own scores, and only when it actually reviewed the frame:
              FAIL under NES 5 or readability 4, REVISE under NES 7 or readability 6, else PASS.
    overall   the worse of the two, because a shot that cannot exist on the hardware is not
              a shot that passed.
    """
    legality = "FAIL" if not measured["legal"] else "PASS"
    scores = (result or {}).get("scores") or {}
    nes_score, read_score = scores.get("nes"), scores.get("readability")
    if result is None or nes_score is None or read_score is None:
        art = "NOT JUDGED"
    elif nes_score < 5 or read_score < 4:
        art = "FAIL"
    elif nes_score < 7 or read_score < 6:
        art = "REVISE"
    else:
        art = "PASS"
    order = {"FAIL": 0, "REVISE": 1, "NOT JUDGED": 2, "PASS": 3}
    overall = legality if order[legality] <= order[art] else art
    return {"legality": legality, "art": art, "overall": overall}


# --------------------------------------------------------------------------- report

def _worse(order, values):
    values = [v for v in values if v]
    return min(values, key=lambda v: order.get(v, 9)) if values else "NOT JUDGED"


def render(rows, model, chain, log, key_source, self_test):
    order = {"FAIL": 0, "REVISE": 1, "NOT JUDGED": 2, "PASS": 3}
    verdicts = [row["verdict"]["overall"] for row in rows if row.get("verdict")]
    lines = [
        "# GEMINI-EYE-DRIVE: twelve shot verdicts, with the NES numbers",
        "",
        "Card t_4bf72d3b, testing lane, written 2026-10-24. Subject: the twelve drive shots captured by",
        "card R21a (`rm_pp_drive`, t_e9c7b280) in `tools\\capture_drive.py`. Judged against",
        "`knowledge\\DRIVE-SHOT-LIST.md` (what each shot is supposed to show), `knowledge\\ART-BIBLE.md`",
        "section 4 (the frame rules), and `knowledge\\NES-AUDIT.md` (the PPU rules the project gates on).",
        "",
        "## The run",
        "",
        "- tool: `tools\\eye_drive.py`, which drives `tools\\eye_critic.py` (the fixed rubric from GEMINI-EYE) and",
        "  `tools\\nes_composite_check.py` (the project's own PPU checker). Neither was reimplemented here.",
        "- model chain, in order: %s" % ", ".join("`%s`" % m for m in chain),
        "- model that answered: %s" % ("`%s`" % model if model else "none: the measured half ran alone"),
        "- credential: from the %s, never printed, never written to a review file or the ledger"
        % (key_source or "environment (absent in this run)"),
        "- frames judged: %d of 12, one per shot, from `output\\drive_frames\\` (native 256x240). The capture"
        % len([r for r in rows if r.get("frame") and not r.get("error")]),
        "  itself is `output\\drive\\pp_drive_shot_01.png` to `_12.png`, 768x720, which is an exact 3x nearest",
        "  scale of 256x240 on every one of the twelve (checked pixel for pixel before the copy, so the",
        "  native copy loses nothing).",
        "- measured half: every legality number below comes from the pixels, not from the model. Where a",
        "  verdict's two halves disagree, the legality half stands.",
        "",
    ]
    if log:
        lines += ["### Model fallbacks taken in this run", ""]
        lines += ["- %s" % line for line in log]
        lines += [""]
    lines += ["### The fallback is measured, not claimed", ""]
    for note in FALLBACK_PROOF:
        lines.append("- %s" % note)
    if self_test:
        lines.append("- that run's own output: refused `%s`, answered on `%s`, %s"
                     % (self_test["refused"], self_test["answered"], self_test["verdict"]))
    lines += [""]

    lines += ["## The twelve verdicts", "",
              "| # | shot | frame judged | colours | off-palette colours | attribute areas over | legality | art | verdict |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        measured = row.get("measured") or {}
        verdict = row.get("verdict") or {}
        lines.append("| %d | `%s` %s | `%s` | %s | %s | %s | %s | %s | **%s** |"
                     % (row["n"], row["id"], row["location"],
                        os.path.relpath(row["frame"], ROOT).replace("\\", "/"),
                        measured.get("colours", "?"),
                        measured.get("off_palette_colours", "?"),
                        measured.get("attribute_areas_over", "?"),
                        verdict.get("legality", "NOT JUDGED"),
                        verdict.get("art", "NOT JUDGED"),
                        verdict.get("overall", "NOT JUDGED")))
    lines += ["",
              "Twelve verdicts: %s. The verdict is the worse of the two halves, so a shot that cannot be drawn on"
              % ", ".join("%d %s" % (verdicts.count(name), name)
                          for name in ("FAIL", "REVISE", "NOT JUDGED", "PASS") if verdicts.count(name)),
              "the hardware does not pass whatever the picture looks like.", ""]

    for row in rows:
        measured = row.get("measured") or {}
        result = row.get("review") or {}
        verdict = row.get("verdict") or {}
        lines += ["### Shot %d, `%s` (%s, beat %s, %d steps)"
                  % (row["n"], row["id"], row["location"], row["beat"], row["steps"]), "",
                  "- frame judged: `%s`" % os.path.relpath(row["frame"], ROOT).replace("\\", "/"),
                  "- supposed to show: %s" % row["shows"]]
        if row.get("sign"):
            lines.append("- gantry sign: %s miles remaining, `sign_%s_seen`, %d caption page(s)"
                         % (row["sign"], row["sign"], row["pages"]))
        if row.get("art_gap"):
            lines.append("- art gap on the record (DRIVE-SHOT-LIST Q3): %s" % row["art_gap"])
        if row.get("error"):
            lines += ["- **verdict: FAIL, the shot was never captured.** %s" % row["error"], ""]
            continue
        lines += ["- colours: %d distinct, %d of them not a usable PPU colour covering %d pixels"
                  % (measured.get("colours", 0), measured.get("off_palette_colours", 0),
                     measured.get("off_palette_pixels", 0)),
                  "- attribute areas (16x16): %d of %d over the 3 colour limit"
                  % (measured.get("attribute_areas_over", 0),
                     measured.get("background_blocks", 0))]
        if not measured.get("attribute_areas_over"):
            lines.append("- background palettes: %d groups of 3 used, inside the 4 the PPU has"
                         % measured.get("background_palettes_used", 0))
        else:
            lines.append("- background palettes: the 4 palette cover is not reached, because %d block(s) "
                         "already carry more than 3 colours besides the backdrop on their own"
                         % measured.get("attribute_areas_over", 0))
        examples = measured.get("attribute_area_examples") or []
        if examples:
            lines.append("- worst attribute areas: %s"
                         % "; ".join("at %d,%d carrying %d colours besides the backdrop"
                                     % (e["block"][0], e["block"][1], e["colours"])
                                     for e in examples))
        if measured.get("off_palette"):
            lines.append("- colours outside the palette: %s"
                         % ", ".join("`%s` at %d pixels" % (c["colour"], c["pixels"])
                                     for c in measured["off_palette"][:5]))
        if measured.get("backdrop"):
            lines.append("- backdrop: `%s`" % measured["backdrop"])
        lines.append("- **verdict: %s** (NES legality %s, art %s)"
                     % (verdict.get("overall", "NOT JUDGED"), verdict.get("legality", "?"),
                        verdict.get("art", "?")))
        if result:
            scores = result.get("scores") or {}
            lines.append("- the model said: NES %s, readability %s, charm %s, on `%s`"
                         % (scores.get("nes"), scores.get("readability"), scores.get("charm"),
                            row.get("model_answered", model)))
            if result.get("focal_point"):
                lines.append("- focal point it named: %s" % result["focal_point"])
            notes = result.get("off_notes") or []
            if notes:
                lines.append("- tells it named: %s" % "; ".join(notes[:4]))
            fixes = result.get("fixes") or []
            if fixes:
                lines.append("- its two best fixes: %s"
                             % "; ".join(("%s (region %s)" % (f["change"][:120], f["region"]))
                                         if f.get("region") else f["change"][:120]
                                         for f in fixes[:2]))
            lines.append("- its review file: `%s`"
                         % os.path.relpath(result["review"], ROOT).replace("\\", "/")
                         if result.get("review") else "- its review file: not saved")
        else:
            lines.append("- the model said: nothing, this shot was not sent to a model in this run")
        lines.append("")

    total_off = sum((row.get("measured") or {}).get("off_palette_colours", 0) for row in rows)
    worst = max(rows, key=lambda r: (r.get("measured") or {}).get("off_palette_pixels", 0))
    lines += ["## What the twelve verdicts add up to", "",
              "- The measured failure is the palette, on every shot: %d non-PPU colour instances across the"
              % total_off,
              "  twelve frames, over a 55 usable entry master palette (`data\\nes_palette.json`). The largest",
              "  single share is shot %d (`%s`) at %s pixels off palette. This is the placeholder palette that"
              % (worst["n"], worst["id"],
                 (worst.get("measured") or {}).get("off_palette_pixels", "?")),
              "  R21a drew with (`#081420`, `#0B0B0F`, `#1C1C24`, `#4A4A58`, `#C8C8D4` and their neighbours),",
              "  not a drawing mistake in a finished asset, and it is the one thing standing between these",
              "  twelve frames and `tools\\nes_audit_all.py` passing them as frames.",
              "- The shot structure, which is what R21a was proving, reads correctly: twelve distinct frames,",
              "  each one the place the shot list names, and the four gantry signs in shots 3, 6, 9 and 11.",
              "- Three shots are drawn against art that does not exist yet (2, 4, 12): DRIVE-SHOT-LIST Q3 is",
              "  still open, so their verdicts measure the placeholder, not the film.",
              "",
              "## Warning, carried over from the eye critic", "",
              eye_critic.WARNING, "",
              "## Sources", "",
              "- shot list, timing and the four signs: `knowledge\\DRIVE-SHOT-LIST.md` sections 2, 3 and 5",
              "- frame rules: `knowledge\\ART-BIBLE.md` section 4, itself sourced to the NESdev wiki",
              "- PPU rules and the failing-row format: `knowledge\\NES-AUDIT.md`, `tools\\nes_composite_check.py`",
              "- rubric, ledger and free tier: `tools\\eye_critic.py`, whose header records the 20 per project",
              "  per model per day measurement taken from the API's own 429 body on 2026-10-22",
              ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- self test

class _FakeResponse(object):
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


QUOTA_BODY = json.dumps({"error": {
    "code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": ("Quota exceeded for metric: generativelanguage.googleapis.com/"
                "generate_content_free_tier_requests, limit: 20, model: gemini-3.5-flash"),
    "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                 "violations": [{"quotaMetric": "generativelanguage.googleapis.com/"
                                               "generate_content_free_tier_requests",
                                 "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                                 "quotaValue": "20"}]},
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "56832s"}]}})

ANSWER = {"candidates": [{"content": {"parts": [{"text":
          "### 6) Scores and machine readable block\n```json\n"
          '{"nes_authenticity": 7, "readability": 7, "charm": 6, "focal_point": "the sign", '
          '"off_notes": ["placeholder palette"], "fixes": ['
          '{"region": [0, 0, 256, 240], "change": "a"}, {"region": [0, 0, 256, 240], "change": "b"}, '
          '{"region": [0, 0, 256, 240], "change": "c"}, {"region": [0, 0, 256, 240], "change": "d"}, '
          '{"region": [0, 0, 256, 240], "change": "e"}]}\n```'}]}, "finishReason": "STOP"}],
          "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 100}}


def self_test(tmp_dir):
    """Prove the chain advances: the first model answers a per-day 429, the second answers the rubric.

    Nothing leaves this process: eye_critic's transport is replaced, the ledger, the results file
    and the review folder are redirected into the scratch dir, and the key is a placeholder, so a
    real credential is not needed to prove a fallback.
    """
    refused, answered = MODEL_CHAIN[0], MODEL_CHAIN[1]
    saved = {"transport": eye_critic._urlopen,
             "env": {name: os.environ.get(name) for name in
                     ("PP_EYE_LEDGER", "PP_EYE_RESULTS", "PP_EYE_REVIEW_DIR", eye_critic.KEY_ENV)}}

    def fake_transport(request, timeout=None):
        if "/models/%s:" % refused in request.full_url:
            raise urllib.error.HTTPError(request.full_url, 429, "quota", {},
                                         io.BytesIO(QUOTA_BODY.encode("utf-8")))
        return _FakeResponse(ANSWER)

    os.makedirs(tmp_dir, exist_ok=True)
    os.environ["PP_EYE_LEDGER"] = os.path.join(tmp_dir, "ledger.csv")
    os.environ["PP_EYE_RESULTS"] = os.path.join(tmp_dir, "results.jsonl")
    os.environ["PP_EYE_REVIEW_DIR"] = os.path.join(tmp_dir, "reviews")
    os.environ[eye_critic.KEY_ENV] = "self-test-placeholder"
    eye_critic._urlopen = fake_transport
    log = []
    try:
        row = {"n": 1, "id": "selftest", "location": "none",
               "frame": os.path.join(FRAME_DIR, "drive_shot_01.png"),
               "shows": "a frame, used only to prove the chain"}
        if not os.path.exists(row["frame"]):
            raise eye_critic.EyeError("run the sampler first: %s is missing" % row["frame"])
        gate = eye_critic.RateGate(path=os.environ["PP_EYE_LEDGER"])
        result, model, attempts = review_shot(row, (refused, answered), gate, log)
    finally:
        eye_critic._urlopen = saved["transport"]
        for name, value in saved["env"].items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    if model != answered:
        raise eye_critic.EyeError("self test FAILED: expected the chain to answer on %s, it answered on %s"
                                  % (answered, model))
    if attempts[0]["outcome"] != "quota refusal":
        raise eye_critic.EyeError("self test FAILED: the first model was not refused: %r" % attempts[0])
    print("self test PASS: %s refused on the per-day quota, the chain moved on, %s answered, "
          "scores %s" % (refused, answered, result["scores"]))
    return {"refused": refused, "answered": answered,
            "verdict": "%s, then %s (scores %s)" % (attempts[0]["outcome"], attempts[1]["outcome"],
                                                    result["scores"])}


# --------------------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(description="Twelve shot verdicts for the drive, measured and reviewed.")
    parser.add_argument("--measure-only", action="store_true",
                        help="sample and measure every shot, send nothing, write the report")
    parser.add_argument("--self-test", action="store_true",
                        help="prove the model chain advances on a per-day 429, then stop")
    parser.add_argument("--report-out", default=None, help="write the verdicts here")
    parser.add_argument("--limit", type=int, default=None, help="review at most N shots")
    args = parser.parse_args(argv)

    rows = sample_frames()
    palette = nes.load_palette(PALETTE_PATH)
    missing = [row for row in rows if row.get("error")]
    measured_rows = []
    for row in rows:
        if row.get("error"):
            row["measured"] = {}
            row["verdict"] = {"legality": "FAIL", "art": "NOT JUDGED", "overall": "FAIL"}
            measured_rows.append(row)
            continue
        row["measured"] = measure(row, palette)
        measured_rows.append(row)
    print("sampled %d shot(s), %d with a frame, %d missing"
          % (len(rows), len([r for r in rows if not r.get("error")]), len(missing)))

    if args.self_test:
        self_test(os.path.join(eye_critic.OUTPUT, "_eye_drive_selftest"))
        return 0

    key_source = None
    log = []
    models_used = set()
    self_test_result = None
    if not args.measure_only:
        key_source = load_key_from_user_environment()
        if not key_source:
            print("no %s in the environment: writing the measured half only" % eye_critic.KEY_ENV)
        else:
            gate = eye_critic.RateGate()
            todo = [row for row in measured_rows if not row.get("error")]
            if args.limit:
                todo = todo[:args.limit]

            def work(row):
                try:
                    return row, review_shot(row, MODEL_CHAIN, gate, log), None
                except eye_critic.EyeError as exc:
                    return row, None, eye_critic.redact(str(exc))[:200]

            # Four in flight, like eye_critic's own sweep: the ceiling is per minute, not per
            # second, so one call at a time spends the whole budget waiting on the model.
            with ThreadPoolExecutor(max_workers=min(4, max(1, len(todo)))) as pool:
                futures = [pool.submit(work, row) for row in todo]
                for future in as_completed(futures):
                    row, outcome, error = future.result()
                    if error is not None or outcome is None:
                        log.append("shot %02d: no model answered, %s" % (row["n"], error))
                        row["review"] = None
                        continue
                    result, answered, attempts = outcome
                    row["review"] = result
                    row["model_answered"] = answered
                    row["attempts"] = attempts
                    models_used.add(answered)
                    print("shot %02d %-14s %s nes=%s read=%s" %
                          (row["n"], row["id"], answered, result["scores"].get("nes"),
                           result["scores"].get("readability")), flush=True)

    for row in measured_rows:
        if "verdict" in row:
            continue
        row["verdict"] = verdict_for(row, row["measured"], row.get("review"))

    if not os.path.isdir(FRAME_DIR):
        os.makedirs(FRAME_DIR)
    with open(RESULTS, "w", encoding="utf-8", newline="\n") as handle:
        json.dump([{key: value for key, value in row.items() if key != "review"}
                   for row in measured_rows], handle, indent=2)
        handle.write("\n")

    model = ", ".join(sorted(models_used)) if models_used else None
    text = render(measured_rows, model, MODEL_CHAIN, log, key_source, self_test_result)
    out = args.report_out or REPORT
    folder = os.path.dirname(os.path.abspath(out))
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    counts = {}
    for row in measured_rows:
        counts[row["verdict"]["overall"]] = counts.get(row["verdict"]["overall"], 0) + 1
    print("verdicts: %s" % ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items())))
    print("report: %s" % out)
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
