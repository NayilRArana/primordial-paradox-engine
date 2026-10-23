"""The automated eye: a Gemini vision critic for NES frames, with a fixed rubric and a ledger (card GEMINI-EYE).

The point of this tool is not to replace Nayil's eyes. It is to make every captured frame
reviewable while he is asleep: every PNG goes through the same questions, in the same
order, and the scores land in a ledger that his own numbers can be compared against later.
Three things follow from that, and all three are enforced here:

  1. The rubric is FIXED. It is the checklist of knowledge\\ART-BIBLE.md section 4 made
     answerable from a picture: does it look like a real NES game (colour count, flat
     shading, sprite readability, no gradients or anti-aliasing), composition, text
     legibility, what the focal point is, what looks AI generated or off, five concrete
     fixes each naming a pixel region, and three 1 to 10 scores (NES authenticity,
     readability, charm). The prompt asks for one fenced JSON block at the end so the
     scores and the fixes are machine readable.

  2. The model is a rough critic. It cannot count pixels reliably, it misreads small
     text, and it does not know our palette. So the prompt also carries MEASURED facts
     taken from the file itself (size, distinct colours, how many of them are outside
     data\\nes_palette.json, grid alignment, the share of the frame one colour covers),
     labelled as measured, and every saved review carries a warning line. A measured
     fact always beats the model's impression in the report.

  3. Free tier. MEASURED 2026-10-22, not assumed: the key in this project is on the free
     tier with a DAILY cap of 20 generateContent requests per project per model
     ("Quota exceeded for metric: generativelanguage.googleapis.com/
     generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash", which is what
     gemini-3.5-flash resolves to; the 429 carried retryDelay 56832 s, so the reset is
     midnight Pacific). That is the real ceiling, so PP_EYE_DAILY_MAX defaults to 20 and the
     tool refuses at the cap instead of spending the last of the day on retries. Within the
     minute, at most PP_EYE_MAX_PER_MINUTE calls (default 10) in any 60 s window; the ledger
     timestamps are the counter, so the limit survives process restarts. A 429 is retried with
     the delay Gemini asks for, and a 429 that names the daily quota is NOT retried: it raises
     DailyLimit and the sweep stops with that sentence.

WHAT IS SENT
    One PNG per call, inline base64, plus the prompt with the measured facts. A file over
    PP_EYE_MAX_INLINE_MB (default 8 MB) or over PP_EYE_MAX_PIXELS (default 4.2 million,
    the API's own per-image ceiling) is refused rather than sent: Google bills and caps by
    picture size, and a 104 megapixel contact sheet is not a frame.

WHERE THINGS LAND
    output\\eye_reviews\\<stem>_<UTC stamp>.md    one review per frame, with its header data
    output\\eye_reviews\\_sweep_results.jsonl     one JSON line per finished frame (resumable)
    data\\eye_ledger.csv                         one row per API call

KEYS
    GEMINI_API_KEY is read from os.environ at call time and put in the x-goog-api-key
    header. It is never in a URL, never printed, never written to the ledger or the review
    file, and never included in an exception message (every error string goes through
    redact()). Files whose name looks like a credential store are refused as input rather
    than opened.

Usage
    python tools\\eye_critic.py --dry-run output\\title_run_1_nes.png
    python tools\\eye_critic.py output\\title_run_1_nes.png output\\intro_1.png
    python tools\\eye_critic.py --folder output --since 2026-10-22 --sweep
    python tools\\eye_critic.py --scope-list --since 2026-10-22
    python tools\\eye_critic.py --gap

Sources
    models and limits   https://ai.google.dev/gemini-api/docs/models          (read 2026-10-22)
    image input limits  https://ai.google.dev/gemini-api/docs/image-understanding (read 2026-10-22)
    request shape       https://ai.google.dev/api/generate-content             (read 2026-10-22)
    palette numbers     knowledge\\ART-BIBLE.md sections 1 and 4, itself sourced from the
                        NESdev wiki pages listed there (read 2026-10-21)
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUTPUT = os.path.join(ROOT, "output")
REVIEW_DIR = os.path.join(OUTPUT, "eye_reviews")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
KEY_ENV = "GEMINI_API_KEY"
MODEL_ENV = "PP_EYE_MODEL"
DEFAULT_MODEL = "gemini-3.5-flash"

DEFAULT_MAX_INLINE_MB = 8.0
DEFAULT_MAX_PIXELS = 4_200_000

DIMENSIONS = ("nes", "readability", "charm")
DIMENSION_LABELS = {
    "nes": "NES authenticity (does this look like a frame a 2C02 could have produced)",
    "readability": "Readability (can a player read the screen at a glance)",
    "charm": "Charm (does it look like a game someone wanted to play)",
}
DIMENSION_ALIASES = {
    "nes": "nes",
    "nes_authenticity": "nes",
    "authenticity": "nes",
    "nes_look": "nes",
    "readability": "readability",
    "legibility": "readability",
    "charm": "charm",
    "appeal": "charm",
    "character": "charm",
}

LEDGER_COLUMNS = ["at", "file", "role", "model", "nes", "readability", "charm",
                  "colours", "seconds", "status", "review"]
RESULT_KEYS = ("file", "rel", "category", "status", "model", "review", "scores",
               "measured", "focal_point", "off_notes", "fixes", "tokens", "seconds", "error")

WARNING = ("Warning: the model is a rough critic. It cannot count pixels reliably, it "
           "misreads small text, it does not know our palette, and it will describe things "
           "that are not in the frame. Where this review disagrees with a measured number, "
           "the measured number wins. Treat the scores as a hint to check against Nayil, "
           "not as a verdict.")

IMAGE_MIME = {".png": "image/png"}
_CREDENTIAL_HINTS = ("token", "secret", "credential", "password", "apikey", "api_key",
                     "auth.json", ".env", "key.txt", "id_rsa")

# ART-BIBLE.md section 1, as numbers the prompt can quote.
FRAME_WIDTH = 256
FRAME_HEIGHT = 240
TILE = 8
ATTRIBUTE_AREA = 16
MAX_COLOURS_ON_SCREEN = 25
BACKGROUND_COLOURS = 12
SPRITE_COLOURS = 12
BACKDROP_COLOURS = 1
SPRITES_PER_SCANLINE = 8
SPRITE_OBJECTS = 64

# Scope rules for a sweep of output\\ (see scope_note()).
SCRATCH_PREFIX = "_"
AUDIO_PREVIEWS = {"music_style_bible_preview.png", "percy_theme_preview_3x.png",
                  "sfx_preview_3x.png"}
CHART_FILES = {"art_bible_palette_sheet.png", "nes_palette_preview.png",
               "nes_audit_worst_3x.png"}

_urlopen = urllib.request.urlopen  # tests replace this with a fake transport
_LEDGER_LOCK = threading.Lock()     # one writer at a time for the ledger and the results file
_GATE_LOCK = threading.Lock()       # one pacekeeper at a time, so parallel workers share the limit


class EyeError(RuntimeError):
    """Anything this tool refuses to do, with a message safe to print."""


class NotConfigured(EyeError):
    pass


class RateLimited(EyeError):
    pass


class DailyLimit(EyeError):
    pass


# ----------------------------------------------------------------------------- small helpers

def redact(text):
    """Strip anything that looks like a key before it can reach a log line."""
    text = str(text)
    value = os.environ.get(KEY_ENV, "")
    if value and len(value) >= 8:
        text = text.replace(value, "[redacted]")
    text = re.sub(r"AIza[0-9A-Za-z_\-]{10,}", "[redacted]", text)
    text = re.sub(r"(?i)(x-goog-api-key|api[_-]?key|key)\s*[=:]\s*\S+", r"\1=[redacted]", text)
    text = re.sub(r"[?&]key=[^&\s]+", "key=[redacted]", text)
    return text


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def utc_stamp():
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def model_name(explicit=None):
    return (explicit or os.environ.get(MODEL_ENV, "").strip() or DEFAULT_MODEL)


def key_present():
    return bool(os.environ.get(KEY_ENV, "").strip())


def _key():
    value = os.environ.get(KEY_ENV, "").strip()
    if not value:
        raise NotConfigured("%s is not set in the environment" % KEY_ENV)
    return value


def _env_float(name, default):
    try:
        return float(os.environ.get(name, "") or default)
    except (TypeError, ValueError):
        return float(default)


def _env_int(name, default):
    try:
        return int(float(os.environ.get(name, "") or default))
    except (TypeError, ValueError):
        return int(default)


def review_dir():
    return os.environ.get("PP_EYE_REVIEW_DIR") or REVIEW_DIR


def ledger_path():
    return os.environ.get("PP_EYE_LEDGER") or os.path.join(DATA, "eye_ledger.csv")


def results_path():
    return os.environ.get("PP_EYE_RESULTS") or os.path.join(review_dir(), "_sweep_results.jsonl")


def _refuse_credential_path(path):
    lowered = os.path.basename(str(path)).lower().replace("-", "_")
    for hint in _CREDENTIAL_HINTS:
        if hint in lowered:
            raise EyeError("refusing to send %r: the name looks like a credential store"
                           % os.path.basename(str(path)))


def image_mime(path):
    ext = os.path.splitext(str(path))[1].lower()
    if ext not in IMAGE_MIME:
        raise EyeError("unsupported image extension %r (want %s)"
                       % (ext, ", ".join(sorted(IMAGE_MIME))))
    return IMAGE_MIME[ext]


# ----------------------------------------------------------------------------- ledger and rate limits

def _ensure_csv_header(path, columns):
    folder = os.path.dirname(os.path.abspath(path))
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=columns).writeheader()


def read_ledger(path=None):
    path = path or ledger_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def append_ledger(row, path=None):
    path = path or ledger_path()
    with _LEDGER_LOCK:
        _ensure_csv_header(path, LEDGER_COLUMNS)
        clean = {column: row.get(column, "") for column in LEDGER_COLUMNS}
        with open(path, "a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS).writerow(clean)
    return path


def _call_rows(path=None):
    """Ledger rows that represent a real API call (a summary row is bookkeeping only)."""
    return [row for row in read_ledger(path)
            if row.get("status") not in ("refused", "") and row.get("role") != "summary"]


def _parse_stamp(stamp):
    stamp = (stamp or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.datetime.strptime(stamp, fmt)
            return parsed.replace(tzinfo=datetime.timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def calls_in_last_minute(path=None, now=None):
    now = now or time.time()
    count = 0
    for row in _call_rows(path):
        seconds = _parse_stamp(str(row.get("at", "")))
        if seconds is not None and now - seconds < 60:
            count += 1
    return count


def calls_today(path=None, now=None):
    now = now or time.time()
    day = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).date()
    count = 0
    for row in _call_rows(path):
        seconds = _parse_stamp(str(row.get("at", "")))
        if seconds is not None and \
                datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).date() == day:
            count += 1
    return count


class RateGate(object):
    """At most N calls per 60 s and M per UTC day, counted from the ledger itself."""

    def __init__(self, path=None, per_minute=None, per_day=None, sleep=None, clock=None):
        self.path = path or ledger_path()
        self.per_minute = (per_minute if per_minute is not None
                           else _env_int("PP_EYE_MAX_PER_MINUTE", 10))
        self.per_day = (per_day if per_day is not None
                        else _env_int("PP_EYE_DAILY_MAX", 20))
        self._sleep = sleep or time.sleep
        self._clock = clock or time.time

    def before_call(self):
        """Block until this call fits both budgets. Serialised, so parallel workers share it."""
        with _GATE_LOCK:
            if self.per_day and calls_today(self.path, self._clock()) >= self.per_day:
                raise DailyLimit("daily call budget reached (%d calls today, PP_EYE_DAILY_MAX)"
                                 % self.per_day)
            if not self.per_minute:
                return
            waited = 0.0
            while calls_in_last_minute(self.path, self._clock()) >= self.per_minute:
                if waited >= 180:
                    raise RateLimited("still at %d calls in the last minute after waiting; "
                                      "refusing to hammer the free tier" % self.per_minute)
                pause = 6.0
                self._sleep(pause)
                waited += pause


# ----------------------------------------------------------------------------- measured facts

def load_palette():
    """The 64 entries of data\\nes_palette.json as a set of upper case #RRGGBB strings."""
    path = os.path.join(DATA, "nes_palette.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return set()
    colours = payload.get("colours") or []
    return {str(c).upper() for c in colours if isinstance(c, str)}


def measure_image(path):
    """Facts about the file, read from its own pixels. No model involved.

    Returns a dict with size, distinct colours, how many are outside the NES palette, the
    share of the frame taken by the most common colour, and grid alignment. Any value that
    cannot be measured is None, never a guess.
    """
    facts = {"width": None, "height": None, "colours": None, "off_palette": None,
             "off_palette_examples": [], "largest_colour_share": None,
             "width_on_grid": None, "height_on_grid": None, "palette_known": False}
    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001 - PIL missing is a fact to report, not a crash
        facts["error"] = "PIL not available: %s" % exc
        return facts
    try:
        with Image.open(str(path)) as img:
            img.load()
            width, height = img.size
            frame = img.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        facts["error"] = "could not read pixels: %s" % exc
        return facts
    facts["width"], facts["height"] = width, height
    counts = frame.getcolors(maxcolors=1 << 24) or []
    facts["colours"] = len(counts)
    if counts:
        biggest = max(counts, key=lambda pair: pair[0])
        total = float(width * height) or 1.0
        facts["largest_colour_share"] = round(biggest[0] / total, 3)
    palette = load_palette()
    facts["palette_known"] = bool(palette)
    if palette:
        off = set()
        for _count, rgb in counts:
            channels = list(rgb) if isinstance(rgb, (tuple, list)) else []
            if len(channels) != 3:
                continue
            hexed = "#%02X%02X%02X" % (int(channels[0]), int(channels[1]), int(channels[2]))
            if hexed not in palette:
                off.add(hexed)
        facts["off_palette"] = len(off)
        facts["off_palette_examples"] = sorted(off)[:6]
    facts["width_on_grid"] = (width % TILE == 0)
    facts["height_on_grid"] = (height % TILE == 0)
    return facts


def measured_lines(facts):
    """The measured facts as prompt lines. Only fields that were measured are stated."""
    lines = []
    if facts.get("width") and facts.get("height"):
        lines.append("Measured size: %d x %d pixels (%s a multiple of %d in both directions)."
                     % (facts["width"], facts["height"],
                        "is" if facts.get("width_on_grid") and facts.get("height_on_grid")
                        else "is NOT", TILE))
    if facts.get("colours") is not None:
        lines.append("Measured distinct colours in the file: %d. The hardware ceiling for one "
                     "frame is %d (12 background + 12 sprite + 1 backdrop), so this file is %s "
                     "the ceiling."
                     % (facts["colours"], MAX_COLOURS_ON_SCREEN,
                        "inside" if facts["colours"] <= MAX_COLOURS_ON_SCREEN else "OVER"))
    if facts.get("off_palette") is not None:
        if facts["off_palette"] == 0:
            lines.append("Measured: every colour in the file is one of the 64 NES palette "
                         "entries from data\\nes_palette.json.")
        else:
            lines.append("Measured: %d colour(s) in the file are NOT in the 64 entry NES palette "
                         "(%s). Those are almost always anti-aliasing or a gradient."
                         % (facts["off_palette"],
                            ", ".join(facts.get("off_palette_examples") or [])))
    if facts.get("largest_colour_share") is not None:
        lines.append("Measured: the most common single colour covers %.1f%% of the frame."
                     % (100.0 * facts["largest_colour_share"]))
    if facts.get("error"):
        lines.append("Measurement note: %s" % facts["error"])
    return lines


# ----------------------------------------------------------------------------- prompt

def frame_context(name=None, category=None, extra=""):
    bits = []
    if name:
        bits.append("File under review: %s." % name)
    if category:
        bits.append("What it is meant to be: %s." % category)
    if extra:
        bits.append(extra)
    return " ".join(bits)


def rubric_prompt(name=None, category=None, facts=None, extra=""):
    lines = [
        "You are a strict but fair art director who has shipped NES games. You are shown one "
        "frame from an original NES style game in development. Judge the frame, not the game: "
        "anything you cannot see, say you cannot see.",
        "",
        "The hardware the art must live inside (real limits, quote them when they matter): "
        "%d x %d pixels; 8 x 8 tiles; a background can change palette only on a %d x %d pixel "
        "boundary; 4 background palettes of 4 entries (3 colours plus one shared backdrop) and "
        "4 sprite palettes of 4 entries (3 colours plus transparency); at most %d colours on "
        "screen at once; sprites are 8 x 8 or 8 x 16, %d objects in OAM, %d per scanline, no "
        "rotation, no alpha, no gradients, no anti-aliasing."
        % (FRAME_WIDTH, FRAME_HEIGHT, ATTRIBUTE_AREA, ATTRIBUTE_AREA,
           MAX_COLOURS_ON_SCREEN, SPRITE_OBJECTS, SPRITES_PER_SCANLINE),
        "",
        "Answer in this order, with these headings, and be concrete. When you give a position, "
        "give it as a pixel region x,y,width,height measured from the top left of the image.",
        "",
        "### 1) What is on the screen",
        "One short paragraph: what the frame shows, where the eye goes first (name the focal "
        "point and the region it sits in), and what the player is being asked to do.",
        "",
        "### 2) Does it look like a real NES game",
        "Go through these five checks, one line each, pass or fail, with the evidence you can "
        "see: (a) the palette count reads as NES, not as a modern limited palette; (b) shading "
        "is flat, one colour per shape, no gradient banding; (c) sprites read at a glance "
        "against the background, with clear silhouettes and no muddy shared colours; (d) no "
        "anti-aliasing and no soft edges anywhere, including text and window borders; (e) "
        "colour changes in the background land on the 16 x 16 grid instead of drifting. If the "
        "measured numbers above contradict your impression, say so plainly.",
        "",
        "### 3) Composition and text",
        "Where the frame is crowded, where it is empty, whether the focal point is where the "
        "player needs it, and whether every piece of text is legible at 256 x 240 without "
        "guessing. Name the text regions and say what is wrong with the worst one.",
        "",
        "### 4) What looks AI generated or off",
        "The tells, named: pillow shading, detail without structure, text that is not on the "
        "glyph grid, borders that are not a whole number of tiles, stray pixels, colours that "
        "do not belong, a composition that reads as a prompt instead of a design. Be blunt. If "
        "the frame looks handmade and honest, say that instead.",
        "",
        "### 5) Five concrete fixes",
        "Exactly five numbered fixes that would raise the scores. Each one must name the pixel "
        "region and the specific change (a colour to replace with which of the NES palette "
        "entries by index or by name, a shape to simplify, a tile to move by a whole 8 or 16 "
        "pixels, a text row to redraw). No general advice: if it cannot be pointed at a "
        "region, it does not count.",
        "",
        "### 6) Scores and machine readable block",
        "Score each line from 1 (bad) to 10 (excellent) and then end the reply with exactly one "
        "fenced json block, these keys and nothing after it:",
        "```json",
        '{"nes_authenticity": 8, "readability": 7, "charm": 6, '
        '"focal_point": "what the eye lands on, in words", '
        '"off_notes": ["tells, one per string"], '
        '"fixes": [{"region": [x, y, w, h], "change": "the specific change"}, '
        '{"region": [x, y, w, h], "change": "..."}, {"region": [x, y, w, h], "change": "..."}, '
        '{"region": [x, y, w, h], "change": "..."}, {"region": [x, y, w, h], "change": "..."}]}',
        "```",
        "The fixes array must hold exactly five entries, in the order you ranked them, and each "
        "region must be inside the image. Scores are integers 1 to 10.",
    ]
    context = frame_context(name=name, category=category, extra=extra)
    if context:
        lines += ["", context]
    facts = facts or {}
    if facts:
        facts_lines = measured_lines(facts)
        if facts_lines:
            lines += ["", "Measured facts about this exact file, taken from its pixels by the "
                          "tool that sent it. These outrank your impression:"] \
                     + ["- " + line for line in facts_lines]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- HTTP

def endpoint(model, base=None):
    base = (base or os.environ.get("GEMINI_API_BASE") or GEMINI_BASE).rstrip("/")
    return "%s/models/%s:generateContent" % (base, model)


def _retry_delay(detail, attempt, base_delay, cap):
    match = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', detail or "")
    if match:
        return min(float(match.group(1)) + 0.5, cap)
    match = re.search(r"[Rr]etry-[Aa]fter:\s*(\d+)", detail or "")
    if match:
        return min(float(match.group(1)), cap)
    return min(base_delay * (2 ** attempt), cap)


def _daily_quota(detail):
    """True when a 429 body names the per day free tier cap rather than a per minute burst."""
    text = detail or ""
    return ("PerDay" in text or "generate_content_free_tier_requests" in text
            or "free_tier" in text)


def _quota_sentence(detail):
    """The one useful sentence out of a quota 429: the metric, the limit, the retry wait."""
    text = detail or ""
    metric = re.search(r"Quota exceeded for metric:\s*([^,\s]+),\s*limit:\s*(\d+)", text)
    model = re.search(r'"model":\s*"([^"]+)"', text)
    retry = re.search(r"Please retry in ([0-9hms.]+)", text)
    bits = []
    if metric:
        bits.append("%s limit %s" % (metric.group(1), metric.group(2)))
    if model:
        bits.append("model %s" % model.group(1))
    if retry:
        bits.append("retry in %s" % retry.group(1))
    return "; ".join(bits) if bits else text[:200]


def post_generate(model, payload, timeout=None, sleep=None):
    """One POST with 429 and 5xx backoff. Returns (decoded body, retries used).

    PP_AI_BACKEND=meta hands the same payload to tools\\meta_client.py, which sends it as one
    chat completion (with its own cache, rate gate and retries) and answers in the
    generateContent shape this module already parses, so the rubric, the ledger and the score
    parsing are untouched.
    """
    if (os.environ.get("PP_AI_BACKEND", "").strip().lower() == "meta"):
        import meta_client  # tools\\ is on sys.path in every documented entry point
        return meta_client.gemini_compat_generate(model, payload, timeout=timeout,
                                                  sleep=sleep), 0
    key = _key()
    body = json.dumps(payload).encode("utf-8")
    url = endpoint(model)
    timeout = timeout or _env_int("PP_EYE_TIMEOUT", 180)
    max_retries = _env_int("PP_EYE_MAX_RETRIES", 3)
    base_delay = _env_float("PP_EYE_RETRY_BASE", 4.0)
    cap = _env_float("PP_EYE_MAX_BACKOFF", 90.0)
    sleep = sleep or time.sleep
    attempt = 0
    last = None
    while True:
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("x-goog-api-key", key)  # the key never enters the URL
        try:
            with _urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), attempt
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:600]
            except Exception:  # noqa: BLE001 - a body that cannot be read is not the error
                detail = ""
            last = (exc.code, detail)
            if exc.code == 429 and _daily_quota(detail):
                # The daily free tier cap is gone for today. Retrying would only spend the
                # minutes left; stop with the sentence the API gave us.
                raise DailyLimit(redact("gemini daily free tier quota is exhausted: %s"
                                        % _quota_sentence(detail)))
            if exc.code not in (429, 500, 502, 503, 504) or attempt >= max_retries:
                break
            sleep(_retry_delay(detail, attempt, base_delay, cap))
            attempt += 1
        except urllib.error.URLError as exc:
            last = (0, str(exc.reason))
            if attempt >= max_retries:
                break
            sleep(min(base_delay * (2 ** attempt), cap))
            attempt += 1
    code, detail = last or (0, "no attempt made")
    if code == 429:
        raise RateLimited(redact("gemini answered 429 after %d attempt(s): %s"
                                 % (attempt + 1, detail)))
    raise EyeError(redact("gemini answered %s: %s" % (code or "no response", detail)))


def read_response(data):
    """Pull the text out of a generateContent body, with a useful error otherwise."""
    candidates = (data or {}).get("candidates") or []
    if not candidates:
        feedback = (data or {}).get("promptFeedback") or {}
        raise EyeError(redact("gemini returned no candidates: %s" % json.dumps(feedback)[:300]))
    parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise EyeError("gemini returned an empty answer (finishReason=%r)"
                       % (candidates[0] or {}).get("finishReason"))
    usage = (data or {}).get("usageMetadata") or {}
    return text, usage


# ----------------------------------------------------------------------------- parsing

def _balanced_objects(text):
    """Every balanced {...} run in the text, outermost only, in order of appearance."""
    found = []
    text = text or ""
    index = 0
    while index < len(text):
        if text[index] == "{":
            depth = 0
            in_string = False
            escape = False
            for cursor in range(index, len(text)):
                char = text[cursor]
                if in_string:
                    if escape:
                        escape = False
                    elif char == "\\":
                        escape = True
                    elif char == '"':
                        in_string = False
                    continue
                if char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        found.append(text[index:cursor + 1])
                        index = cursor
                        break
            else:
                break
        index += 1
    return found


def _last_json_object(text):
    for candidate in reversed(_balanced_objects(text)):
        try:
            parsed = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _clamp(value):
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if number < 1 or number > 10:
        return None
    return number


def normalise_scores(payload):
    scores = {}
    for key, value in (payload or {}).items():
        if isinstance(value, dict):
            continue
        name = DIMENSION_ALIASES.get(str(key).strip().lower().replace(" ", "_").replace("-", "_"))
        if name and name not in scores:
            number = _clamp(value)
            if number is not None:
                scores[name] = number
    return {dimension: scores.get(dimension) for dimension in DIMENSIONS}


def scores_from_text(text):
    """JSON block first, then the human readable 'NES authenticity: 6/10' lines."""
    scores = normalise_scores(_last_json_object(text))
    if any(value is not None for value in scores.values()):
        return scores
    for dimension in DIMENSIONS:
        label = re.escape(DIMENSION_LABELS[dimension].split("(")[0].strip())
        match = re.search(label + r"[^0-9\n]{0,40}?(\d{1,2})\s*(?:/|out of)\s*10",
                          text or "", re.I)
        if match:
            scores[dimension] = _clamp(match.group(1))
    return scores


def _clean_region(value):
    if isinstance(value, (list, tuple)) and len(value) == 4:
        out = []
        for item in value:
            try:
                out.append(int(round(float(item))))
            except (TypeError, ValueError):
                return None
        if out[2] > 0 and out[3] > 0:
            return out
        return None
    if isinstance(value, str):
        numbers = re.findall(r"-?\d+", value)
        if len(numbers) == 4:
            return _clean_region([int(n) for n in numbers])
    return None


def fixes_from_payload(payload):
    fixes = []
    for item in (payload or {}).get("fixes") or []:
        if isinstance(item, dict):
            change = str(item.get("change") or item.get("fix") or item.get("text") or "").strip()
            region = _clean_region(item.get("region") or item.get("pixels")
                                   or item.get("area"))
            if change:
                fixes.append({"region": region, "change": change})
        elif isinstance(item, str) and item.strip():
            fixes.append({"region": None, "change": item.strip()})
    return fixes


def fixes_from_text(text):
    """Numbered lines under the fixes heading, when the JSON block has none."""
    fixes = []
    section = ""
    collecting = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            collecting = "fix" in line.lower()
            if collecting:
                section = line
            continue
        if not collecting:
            continue
        match = re.match(r"^(\d+)[.)]\s+(.*)$", line)
        if match:
            body = match.group(2).strip()
            region = None
            found = re.search(r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", body)
            if found:
                region = [int(found.group(i)) for i in (1, 2, 3, 4)]
            fixes.append({"region": region, "change": body})
    return fixes


def off_notes_from_payload(payload):
    notes = []
    for key in ("off_notes", "off", "tells", "ai_tells"):
        value = (payload or {}).get(key)
        if isinstance(value, list):
            notes += [str(v).strip() for v in value if str(v).strip()]
        elif isinstance(value, str) and value.strip():
            notes.append(value.strip())
    return notes


def focal_from_payload(payload):
    for key in ("focal_point", "focal", "focus"):
        value = (payload or {}).get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


# ----------------------------------------------------------------------------- review files

def _plain_dashes(text):
    """House style: no em dashes or en dashes in our artifacts, not even when the model
    writes them. Long dashes become a comma or a hyphen; spacing is tidied after."""
    out = str(text or "")
    for long_dash in ("\u2014", "\u2015", "\u2e3a", "\u2e3b"):
        out = out.replace(long_dash, ", ")
    for short_dash in ("\u2013", "\u2212", "\u2011"):
        out = out.replace(short_dash, "-")
    out = re.sub(r"[ \t]+,", ",", out)
    out = re.sub(r",[ \t]*,[ \t]*", ", ", out)
    out = re.sub(r" {2,}", " ", out)
    return out


def _render_markdown(title, model, source, scores, body, measured=None, extra_meta=None):
    body = _plain_dashes(body)
    title = _plain_dashes(title)
    stamp = utc_now().strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# Eye review: %s" % title, "",
             "- model: %s" % model,
             "- file: %s" % source,
             "- reviewed: %s" % stamp]
    for key, value in (extra_meta or {}).items():
        lines.append("- %s: %s" % (key, value))
    score_line = ", ".join("%s %s" % (key, scores.get(key) if scores.get(key) is not None else "?")
                           for key in DIMENSIONS)
    lines.append("- scores: %s" % score_line)
    if measured:
        for line in measured_lines(measured):
            lines.append("- measured: %s" % line)
    lines += ["- warning: %s" % WARNING, "", "---", "", body.strip(), ""]
    return "\n".join(lines)


def save_review(name, markdown):
    folder = review_dir()
    if not os.path.isdir(folder):
        os.makedirs(folder)
    stem = os.path.splitext(os.path.basename(str(name)))[0]
    target = os.path.join(folder, "%s_%s.md" % (stem, utc_stamp()))
    suffix = 2
    while os.path.exists(target):
        target = os.path.join(folder, "%s_%s_%d.md" % (stem, utc_stamp(), suffix))
        suffix += 1
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown)
    return target


def append_result(row, path=None):
    path = path or results_path()
    with _LEDGER_LOCK:
        folder = os.path.dirname(os.path.abspath(path))
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        clean = {key: row.get(key) for key in RESULT_KEYS if key in row}
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(clean, ensure_ascii=False) + "\n")
    return path


def read_results(path=None):
    path = path or results_path()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


# ----------------------------------------------------------------------------- review one frame

def _size_check(path):
    size_mb = os.path.getsize(path) / (1024.0 * 1024.0)
    max_inline = _env_float("PP_EYE_MAX_INLINE_MB", DEFAULT_MAX_INLINE_MB)
    if size_mb > max_inline:
        raise EyeError("%s is %.1f MB, over PP_EYE_MAX_INLINE_MB %.0f"
                       % (os.path.basename(path), size_mb, max_inline))
    facts = measure_image(path)
    pixels = (facts.get("width") or 0) * (facts.get("height") or 0)
    max_pixels = _env_int("PP_EYE_MAX_PIXELS", DEFAULT_MAX_PIXELS)
    if pixels and pixels > max_pixels:
        raise EyeError("%s is %d pixels (%.1f megapixels), over the %d pixel ceiling; "
                       "review the native frame instead of an upscaled contact sheet"
                       % (os.path.basename(path), pixels, pixels / 1e6, max_pixels))
    return size_mb, facts


def inline_part(path, label=None):
    mime = image_mime(path)
    with open(str(path), "rb") as handle:
        payload = base64.b64encode(handle.read()).decode("ascii")
    parts = []
    if label:
        parts.append({"text": label})
    parts.append({"inline_data": {"mime_type": mime, "data": payload}})
    return parts


def review_image(path, model=None, gate=None, save=True, dry_run=False,
                 category=None, rel=None, record=True):
    """Review one PNG end to end. Returns a dict with scores, text, review path and calls."""
    path = os.path.abspath(str(path))
    if not os.path.exists(path):
        raise EyeError("no such image: %s" % path)
    _refuse_credential_path(path)
    model = model_name(model)
    size_mb, facts = _size_check(path)
    gate = gate or RateGate()

    plan = {"file": path, "model": model, "size_mb": round(size_mb, 2),
            "width": facts.get("width"), "height": facts.get("height"),
            "colours": facts.get("colours"), "off_palette": facts.get("off_palette"),
            "key_present": key_present(), "calls_planned": 1}
    if dry_run:
        return {"plan": plan, "scores": {}, "text": "", "review": None, "calls": 0,
                "measured": facts, "fixes": []}

    gate.before_call()
    started = time.time()
    prompt = rubric_prompt(name=os.path.basename(path), category=category, facts=facts)
    parts = [{"text": prompt}] + inline_part(path)
    payload = {"contents": [{"role": "user", "parts": parts}]}
    try:
        data, _retries = post_generate(model, payload)
        text, usage = read_response(data)
    except EyeError as exc:
        if record:
            append_ledger({"at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"), "file": path,
                           "role": "review", "model": model,
                           "seconds": round(time.time() - started, 2),
                           "status": "error" if not isinstance(exc, RateLimited)
                           else "rate_limited"})
        raise

    parsed = _last_json_object(text)
    scores = scores_from_text(text)
    fixes = fixes_from_payload(parsed) or fixes_from_text(text)
    meta = {"size_mb": round(size_mb, 2),
            "tokens": "%s in / %s out" % ((usage or {}).get("promptTokenCount", "?"),
                                          (usage or {}).get("candidatesTokenCount", "?")),
            "category": category or "unclassified"}
    markdown = _render_markdown(os.path.basename(path), model, path, scores, text,
                                measured=facts, extra_meta=meta)
    review_path = save_review(path, markdown) if save else None
    append_ledger({"at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"), "file": path,
                   "role": "review", "model": model,
                   "nes": scores.get("nes") or "", "readability": scores.get("readability") or "",
                   "charm": scores.get("charm") or "", "colours": facts.get("colours") or "",
                   "seconds": round(time.time() - started, 2), "status": "ok",
                   "review": review_path or ""})
    return {"plan": plan, "scores": scores, "text": text, "review": review_path, "calls": 1,
            "measured": facts, "fixes": fixes,
            "focal_point": focal_from_payload(parsed),
            "off_notes": off_notes_from_payload(parsed),
            "tokens": meta["tokens"], "seconds": round(time.time() - started, 2),
            "rel": rel}


# ----------------------------------------------------------------------------- scope

def scope_note():
    return ("Scope: every PNG under output\\ newer than the cutoff that is a FRAME or a "
            "PREVIEW of a frame. Excluded, with the reason: a name starting with an "
            "underscore (this project's convention for tool scratch output: diffs, overlays, "
            "contact sheet internals), a *_mask.png (one or two colour masks, not art), an "
            "individual asset strip under output\\PrimordialParadox\\art\\ (a sprite or one "
            "parallax layer, covered numerically by tools\\nes_audit_all.py, and there is no "
            "composition to judge), an audio preview (a spectrogram or waveform, not a frame), "
            "and a chart (art_bible_palette_sheet, nes_palette_preview, nes_audit_worst_3x).")


def classify(rel):
    """(category, skip_reason) for one path relative to output\\."""
    name = os.path.basename(rel)
    lower = name.lower()
    parts = rel.replace("\\", "/").split("/")
    if name.startswith(SCRATCH_PREFIX):
        return None, "tool scratch output (leading underscore)"
    if lower.endswith("_mask.png") or "_mask_" in lower:
        return None, "mask, one or two colours, not art"
    if lower in AUDIO_PREVIEWS:
        return None, "audio preview, not a frame"
    if lower in CHART_FILES:
        return None, "chart or audit contact sheet, not a frame"
    if len(parts) > 1 and parts[0] == "PrimordialParadox" and parts[1] == "art":
        return None, "single sprite or layer strip, covered by the palette audit"
    if lower.endswith("_diff.png"):
        return None, "difference image, not a frame"
    if "contact" in lower:
        return "preview", None
    if lower.startswith("intro") or "text_reveal" in lower or lower.startswith("crawl"):
        return "intro", None
    if lower.startswith("ship_") or "ship_preview" in lower:
        return "ship", None
    if "preview" in lower or "sample" in lower or lower.startswith("ts2_") \
            or lower.startswith("ts_exterior"):
        return "preview", None
    if lower.startswith("title") or lower.startswith("probe") or lower.startswith("w1_") \
            or lower.startswith("keys_run") or "title_frame" in lower:
        return "title", None
    if lower.startswith("bg_") or lower.startswith("enemies_") or lower.startswith("icons") \
            or lower.startswith("ui_") or lower.startswith("chars_"):
        return "preview", None
    return None, "not a frame or a preview of a frame"


CATEGORY_ORDER = {"title": 0, "intro": 1, "ship": 2, "preview": 3}


def _order_key(row):
    return (CATEGORY_ORDER.get(row.get("category"), 9), row.get("rel") or "")


def collect_scope(folder=None, since=None, include_skipped=False):
    """Walk the folder and return (keep, skipped) lists of dicts with rel, path, category."""
    folder = folder or OUTPUT
    cutoff = _parse_cutoff(since)
    keep, skipped = [], []
    for base, _dirs, files in os.walk(folder):
        for name in sorted(files):
            if not name.lower().endswith(".png"):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, folder)
            if cutoff is not None and os.path.getmtime(path) <= cutoff:
                continue
            category, reason = classify(rel)
            row = {"rel": rel.replace("\\", "/"), "path": path, "category": category,
                   "reason": reason}
            if category:
                keep.append(row)
            else:
                skipped.append(row)
    keep.sort(key=_order_key)
    skipped.sort(key=lambda r: r["rel"])
    return (keep, skipped) if include_skipped else keep


def _parse_cutoff(since):
    if not since:
        return None
    text = str(since).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            parsed = datetime.datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=datetime.timezone.utc).timestamp()
        except ValueError:
            continue
    raise EyeError("--since wants YYYY-MM-DD, got %r" % since)


def choose_one_per_scene(rows):
    """Collapse a scene captured at several scales onto one file, and say which others were
    skipped, so the sweep does not spend a call on a nearest neighbour copy of the last one.
    Preference order: native 256 x 240, then the largest, then the alphabetically first."""
    groups = {}
    order = []
    for row in rows:
        stem = os.path.basename(row["rel"])
        key = re.sub(r"_?(3x|2x|preview|native|sample)_?(preview|frame)?( \d)?$", "", stem)
        key = re.sub(r"\.png$", "", key)
        key = re.sub(r"_(frame|preview|native)$", "", key)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    chosen, dropped = [], []
    for key in order:
        members = groups[key]
        if len(members) == 1:
            chosen.append(members[0])
            continue
        def rank(row):
            facts = measure_image(row["path"])
            native = facts.get("width") == FRAME_WIDTH and facts.get("height") == FRAME_HEIGHT
            pixels = (facts.get("width") or 0) * (facts.get("height") or 0)
            return (0 if native else 1, -pixels, row["rel"])
        members = sorted(members, key=rank)
        chosen.append(members[0])
        for other in members[1:]:
            dropped.append(dict(other, reason="same scene as %s at another scale"
                                        % members[0]["rel"]))
    chosen.sort(key=_order_key)
    dropped.sort(key=lambda r: r["rel"])
    return chosen, dropped


# ----------------------------------------------------------------------------- sweep

def load_done(results=None):
    """Frames already reviewed with status ok, so a re-run resumes instead of paying twice."""
    done = {}
    for row in results if results is not None else read_results():
        if row.get("status") == "ok" and row.get("rel"):
            done[row["rel"]] = row
    return done


def run_sweep(folder=None, since=None, limit=None, model=None, save=True, resume=True,
              one_per_scene=True, workers=None, measure_only=False):
    """Review every frame in scope, no more than PP_EYE_MAX_PER_MINUTE calls per minute.

    Calls run in a small thread pool because the free tier's limit is per minute, not per
    second: one call at a time spends about a minute waiting on the model and reaches one
    frame a minute, while four in flight reach the limit the account actually allows. The
    pacekeeper and the two files are locked, so the ceiling still holds and neither the
    ledger nor the results file can be torn. One JSON line per frame is appended as it
    finishes, so a timeout loses nothing and a re-run resumes instead of paying twice.
    """
    keep, skipped = collect_scope(folder=folder, since=since, include_skipped=True)
    dropped_scene = []
    if one_per_scene:
        keep, dropped_scene = choose_one_per_scene(keep)
    if limit:
        keep = keep[:int(limit)]
    done = load_done() if resume else {}
    gate = RateGate()
    workers = workers or max(1, _env_int("PP_EYE_WORKERS", 4))
    finished, failed, reused = [], [], []
    todo = []
    for row in keep:
        if row["rel"] in done:
            reused.append(done[row["rel"]])
        else:
            todo.append(row)

    if measure_only:
        # No model, no quota: measure every frame in scope from its own pixels. A day with no
        # calls left still produces the honest half of the review, and it is the half that
        # needs no caveat.
        for row in todo:
            try:
                facts = measure_image(row["path"])
            except OSError as exc:
                failed.append({"rel": row["rel"], "error": redact(exc)})
                continue
            record = {"file": row["path"], "rel": row["rel"], "category": row["category"],
                      "status": "measured", "measured": facts}
            append_result(record)
            finished.append(record)
        return {"reviewed": finished, "reused": reused, "failed": failed,
                "skipped": skipped, "dropped_scene": dropped_scene,
                "scope": keep, "folder": folder or OUTPUT}

    def work(row):
        try:
            return row, review_image(row["path"], model=model, gate=gate, save=save,
                                     category=row["category"], rel=row["rel"]), None
        except (EyeError, OSError) as exc:
            return row, None, redact(exc)

    if todo:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(work, row) for row in todo]
            for future in as_completed(futures):
                row, result, error = future.result()
                if error is not None or result is None:
                    failed.append({"rel": row["rel"], "error": error or "no result"})
                    append_result({"file": row["path"], "rel": row["rel"],
                                   "category": row["category"], "status": "failed",
                                   "model": model_name(model), "error": error[:400]})
                    print("FAILED %-52s %s" % (row["rel"], error[:120]), flush=True)
                    continue
                record = {"file": row["path"], "rel": row["rel"], "category": row["category"],
                          "status": "ok", "model": result["plan"]["model"],
                          "review": result["review"], "scores": result["scores"],
                          "measured": result["measured"], "focal_point": result["focal_point"],
                          "off_notes": result["off_notes"], "fixes": result["fixes"],
                          "tokens": result["tokens"], "seconds": result["seconds"]}
                append_result(record)
                finished.append(record)
                print("OK     %-52s nes=%s read=%s charm=%s"
                      % (row["rel"], result["scores"].get("nes"),
                         result["scores"].get("readability"),
                         result["scores"].get("charm")), flush=True)
    return {"reviewed": finished, "reused": reused, "failed": failed,
            "skipped": skipped, "dropped_scene": dropped_scene,
            "scope": keep, "folder": folder or OUTPUT}


# ----------------------------------------------------------------------------- report

FIX_THEMES = (
    ("anti-aliasing or soft edges", ("anti-align", "anti align", "antialias", "soft edge",
                                     "blurry", "blur", "feather", "smooth")),
    ("gradient or too many colours", ("gradient", "too many colour", "too many color",
                                      "colour count", "color count", "banding",
                                      "reduce the palette", "shade")),
    ("contrast between sprite and background", ("contrast", "stands out", "silhouette",
                                                "reads against", "blend", "muddy")),
    ("text legibility or glyph grid", ("text", "font", "glyph", "letter", "label", "word")),
    ("focal point or composition", ("focal", "composition", "crowded", "empty", "clutter",
                                    "centre", "center", "balance")),
    ("grid or tile alignment", ("grid", "tile edge", "16 x 16", "16x16", "8 x 8", "8x8",
                                "align")),
    ("stray or misplaced pixels", ("stray", "single pixel", "orphan", "misplaced",
                                   "floating pixel")),
    ("colour outside the NES palette", ("palette entry", "not in the palette", "outside the",
                                        "unsupported colour", "unsupported color")),
)


def bucket_fix(text):
    lowered = str(text or "").lower()
    for name, needles in FIX_THEMES:
        for needle in needles:
            if needle in lowered:
                return name
    return "other"


def load_sweep_rows(results=None):
    """Rows with pixels measured, one per frame: a model reviewed row wins over a measured
    only row for the same frame, so a resumed sweep cannot double count."""
    best = {}
    for row in (results if results is not None else read_results()):
        status = row.get("status")
        if status not in ("ok", "measured"):
            continue
        rel = row.get("rel") or row.get("file")
        current = best.get(rel)
        if current is None or (status == "ok" and current.get("status") != "ok"):
            best[rel] = row
    return sorted(best.values(), key=lambda row: (row.get("category") or "", row.get("rel") or ""))


def rank_fixes(rows, top=10):
    """Rank fixes: a frame that scores low comes first, and a fix whose theme recurs across
    frames outranks a one off inside the same score band. Returns dicts."""
    ranked = []
    theme_counts = {}
    for row in rows:
        for fix in row.get("fixes") or []:
            theme = bucket_fix(fix.get("change"))
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
    for row in rows:
        nes = (row.get("scores") or {}).get("nes")
        nes = 10 if nes is None else nes
        for order, fix in enumerate(row.get("fixes") or []):
            theme = bucket_fix(fix.get("change"))
            ranked.append({
                "rel": row.get("rel"),
                "nes": (row.get("scores") or {}).get("nes"),
                "theme": theme,
                "region": fix.get("region"),
                "change": fix.get("change"),
                "score": (nes * 100) + order - (5 * theme_counts.get(theme, 0)),
            })
    ranked.sort(key=lambda r: (r["score"], r["rel"] or ""))
    return ranked[:top], theme_counts


def _md_table(rows):
    lines = ["| frame | category | NES | read | charm | colours (measured) | off palette | "
             "model review | review file |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        scores = row.get("scores") or {}
        measured = row.get("measured") or {}
        rel = row.get("rel") or os.path.basename(row.get("file") or "?")
        colours = measured.get("colours")
        off = measured.get("off_palette")
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (rel, row.get("category") or "?", scores.get("nes", "?"),
                        scores.get("readability", "?"), scores.get("charm", "?"),
                        colours if colours is not None else "?",
                        off if off is not None else "?",
                        "yes" if row.get("status") == "ok" else "no (measured only)",
                        os.path.basename(row.get("review") or "") or ""))
    return lines


def render_sweep_report(sweep, model=None, cutoff=None):
    """The EYE_SWEEP markdown: scope, the table, the ranked fixes, hard numbers, the warning."""
    rows = load_sweep_rows()
    if not rows:
        rows = sweep.get("reviewed") or []
    ranked, themes = rank_fixes(rows)
    stamp = utc_now().strftime("%Y-%m-%d %H:%M UTC")
    total_reviewed = len(rows)
    model_rows = [row for row in rows if row.get("status") == "ok"]
    measured_only = [row for row in rows if row.get("status") == "measured"]
    failed = sweep.get("failed") or []
    recorded = [row for row in read_results() if row.get("status") == "failed"]
    seen = {row.get("rel") for row in failed}
    for row in recorded:
        if row.get("rel") not in seen:
            failed.append({"rel": row.get("rel"), "error": row.get("error") or "unknown"})
            seen.add(row.get("rel"))
    skipped = sweep.get("skipped") or []
    dropped_scene = sweep.get("dropped_scene") or []
    keep = sweep.get("scope") or []

    def mean(key):
        values = [(row.get("scores") or {}).get(key) for row in rows]
        values = [v for v in values if isinstance(v, int)]
        return round(sum(values) / float(len(values)), 2) if values else None

    lines = ["# EYE SWEEP %s" % (utc_now().strftime("%Y-%m-%d")), "",
             "- tool: tools\\eye_critic.py (Gemini vision, model %s)"
             % (model or model_name()),
             "- written: %s" % stamp,
             "- frames found in scope: %d, with a model review: %d, measured only (no model "
             "call): %d, failed: %d, reused from an earlier run: %d"
             % (len(keep), len(model_rows), len(measured_only), len(failed),
                len(sweep.get("reused") or [])),
             "- skipped as not frames: %d, skipped as another scale of a reviewed frame: %d"
             % (len(skipped), len(dropped_scene)),
             "- warning: the model is a rough critic. It cannot count pixels, it misreads "
             "small text, and it does not know our palette. The measured columns "
             "(colours, off palette) come from the files themselves and outrank every score "
             "and every sentence in the reviews. Where a review disagrees with a measured "
             "number, the measured number wins. These scores are a hint to check against "
             "Nayil, not a verdict.",
             "",
             "## What was in scope",
             "",
             scope_note(),
             "",
             "Cutoff: files modified after %s (UTC). A row with 'model review: yes' has its own "
             "review file in output\\eye_reviews\\; a row marked 'measured only' was measured "
             "from its own pixels and has no model review yet, because the daily quota ran out "
             "(see the last section)." % (cutoff or "the start of the sweep"),
             ""]
    if dropped_scene:
        lines += ["Frames reviewed at one scale only, because the others are the same picture "
                  "at another scale:", ""]
        for row in dropped_scene:
            lines.append("- %s: %s" % (row["rel"], row.get("reason", "")))
        lines.append("")
    if skipped:
        lines += ["Not reviewed, with the reason (counted, not guessed):", ""]
        buckets = {}
        for row in skipped:
            buckets.setdefault(row.get("reason", "?"), []).append(row["rel"])
        for reason in sorted(buckets):
            lines.append("- %s (%d): %s" % (reason, len(buckets[reason]),
                                            ", ".join(buckets[reason][:8])
                                            + (" ..." if len(buckets[reason]) > 8 else "")))
        lines.append("")

    lines += ["## Scores", "",
              "Mean NES authenticity %s, mean readability %s, mean charm %s, over the %d "
              "frame(s) the model actually reviewed. A '?' is a frame measured but not "
              "reviewed, which is not a zero." % (mean("nes"), mean("readability"),
                                                  mean("charm"), len(model_rows)), ""]
    lines += _md_table(rows)
    lines.append("")

    lines += ["## Top 10 fixes, ranked", "",
              "Ranked by the frame's NES authenticity score first (lower scores first), then by "
              "how often the same theme recurs across frames, then by the critic's own order.",
              ""]
    for index, fix in enumerate(ranked, 1):
        region = fix.get("region")
        region_text = ("x=%d y=%d w=%d h=%d" % tuple(region)) if region else "region not given"
        lines.append("%d. %s (%s, NES %s): %s" % (index, fix["theme"],
                                                  fix.get("rel"), fix.get("nes"),
                                                  _plain_dashes(fix.get("change"))))
        lines.append("   region %s" % region_text)
    if not ranked:
        lines.append("No fixes were parsed: every review lacked a readable fixes array, which "
                     "is itself a finding about the model output, not about the art.")
    lines.append("")

    lines += ["## Themes across the sweep", ""]
    if themes:
        for theme in sorted(themes, key=lambda name: -themes[name]):
            lines.append("- %s: %d fix(es)" % (theme, themes[theme]))
    else:
        lines.append("- none parsed")
    lines.append("")

    hard = []
    for row in rows:
        measured = row.get("measured") or {}
        colours = measured.get("colours")
        off = measured.get("off_palette")
        if colours is not None and colours > MAX_COLOURS_ON_SCREEN:
            hard.append("%s: %d distinct colours, over the %d ceiling"
                        % (row.get("rel"), colours, MAX_COLOURS_ON_SCREEN))
        if off:
            hard.append("%s: %d colour(s) outside the 64 entry NES palette"
                        % (row.get("rel"), off))
        if measured.get("width") and measured.get("height") \
                and not (measured.get("width_on_grid") and measured.get("height_on_grid")):
            hard.append("%s: %d x %d is not a multiple of %d"
                        % (row.get("rel"), measured["width"], measured["height"], TILE))
    lines += ["## Measured failures (independent of the model)", "",
              "These come from the pixels, not from the critic. They are the claims in this "
              "file that do not need a caveat.", ""]
    lines += ["- %s" % item for item in hard] if hard else \
             ["- none: every reviewed frame is inside the 25 colour ceiling, on the 64 entry "
              "palette, and on the 8 pixel grid"]
    lines.append("")

    if failed:
        lines += ["## Frames that could not be reviewed", ""]
        quota = [row for row in failed if "429" in str(row.get("error"))]
        if quota:
            lines += ["All %d of these were stopped by the same wall, not by the art: the free "
                      "tier allows 20 generateContent requests per project per model per day, "
                      "and that budget was already spent when the sweep reached them (the audio "
                      "critic, tools\\ear_critic.py, had spent part of the same 20 on the same "
                      "key earlier the same day). Measured from the API's own 429 body on "
                      "2026-10-22: quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier, "
                      "quotaValue 20, model gemini-3.6-flash, retryDelay 56832 s. gemini-3.8-flash "
                      "answered 503 (high demand) on the same key at the same moment, so a "
                      "different model name is not a way around the cap." % len(quota),
                      ""]
        for row in failed:
            error = " ".join(str(row.get("error") or "").split())[:240]
            lines.append("- %s: %s" % (row["rel"], error))
        lines.append("")

    lines += ["## Sources", "",
              "- Gemini model and free tier limits: https://ai.google.dev/gemini-api/docs/models "
              "(read 2026-10-22)",
              "- Image input size and token rules: "
              "https://ai.google.dev/gemini-api/docs/image-understanding (read 2026-10-22)",
              "- Request shape (generateContent, inline data): "
              "https://ai.google.dev/api/generate-content (read 2026-10-22)",
              "- Hardware numbers in the rubric: knowledge\\ART-BIBLE.md sections 1 and 4, "
              "sourced there to the NESdev wiki PPU, PPU palettes, PPU OAM and PPU attribute "
              "table pages (read 2026-10-21)",
              "- Palette membership check: data\\nes_palette.json (built by "
              "tools\\art\\nes_palette_build.py, cited in its own header, read 2026-10-22)",
              ""]
    return "\n".join(lines)


def sweep_report_path():
    return os.path.join(OUTPUT, "EYE_SWEEP_%s.md" % utc_now().strftime("%Y-%m-%d"))


def write_sweep_report(sweep, path=None, model=None, cutoff=None):
    text = render_sweep_report(sweep, model=model, cutoff=cutoff)
    path = path or sweep_report_path()
    folder = os.path.dirname(os.path.abspath(path))
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


# ----------------------------------------------------------------------------- gap (scores versus Nayil)

CALIBRATION_COLUMNS = (["file"] + ["gemini_%s" % d for d in DIMENSIONS]
                       + ["nayil_%s" % d for d in DIMENSIONS] + ["nayil_note", "updated"])


def calibration_path():
    return os.environ.get("PP_EYE_CALIBRATION") or os.path.join(DATA, "eye_calibration.csv")


def read_calibration(path=None):
    path = path or calibration_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def record_nayil(file_key, scores, note="", path=None):
    path = path or calibration_path()
    _ensure_csv_header(path, CALIBRATION_COLUMNS)
    rows = read_calibration(path)
    entry = None
    for row in rows:
        if row.get("file") == file_key:
            entry = row
            break
    if entry is None:
        entry = {column: "" for column in CALIBRATION_COLUMNS}
        entry["file"] = file_key
        rows.append(entry)
    for key, value in (scores or {}).items():
        dimension = DIMENSION_ALIASES.get(str(key).strip().lower().replace(" ", "_"))
        if not dimension:
            continue
        number = _clamp(value)
        if number is None:
            raise EyeError("score for %r must be an integer 1 to 10, got %r" % (key, value))
        entry["nayil_%s" % dimension] = str(number)
    if note:
        entry["nayil_note"] = note
    entry["updated"] = utc_now().strftime("%Y-%m-%d")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALIBRATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CALIBRATION_COLUMNS})
    return path


def gap_report(rows=None, path=None):
    rows = rows if rows is not None else load_sweep_rows()
    per_dimension = {}
    compared = 0
    for row in read_calibration(path):
        pairs = []
        for dimension in DIMENSIONS:
            eye = _clamp(row.get("gemini_%s" % dimension))
            human = _clamp(row.get("nayil_%s" % dimension))
            if eye is not None and human is not None:
                pairs.append(eye - human)
        if pairs:
            compared += 1
            for dimension in DIMENSIONS:
                eye = _clamp(row.get("gemini_%s" % dimension))
                human = _clamp(row.get("nayil_%s" % dimension))
                if eye is not None and human is not None:
                    per_dimension.setdefault(dimension, []).append(eye - human)
    summary = {}
    for dimension, diffs in per_dimension.items():
        summary[dimension] = {"n": len(diffs),
                              "signed_mean": round(sum(diffs) / float(len(diffs)), 2),
                              "mean_abs": round(sum(abs(d) for d in diffs) / float(len(diffs)), 2)}
    return {"frames_reviewed": len(rows), "calibration_rows": len(read_calibration(path)),
            "compared_rows": compared, "per_dimension": summary}


# ----------------------------------------------------------------------------- cli

def _print_plan(plan):
    print("file:     %s" % plan["file"])
    print("model:    %s" % plan["model"])
    print("size:     %.2f MB, %s x %s, %s distinct colours, %s off palette"
          % (plan["size_mb"], plan["width"], plan["height"], plan["colours"],
             plan["off_palette"]))
    print("key:      %s" % ("present in %s" % KEY_ENV if plan["key_present"]
                            else "absent from %s, a real run would refuse" % KEY_ENV))
    print("calls:    %d planned" % plan["calls_planned"])


def build_parser():
    parser = argparse.ArgumentParser(
        description="Review NES frames with Gemini vision against the fixed eye rubric.")
    parser.add_argument("files", nargs="*", help="PNG files to review")
    parser.add_argument("--model", default=None,
                        help="model name (default: $%s or %s)" % (MODEL_ENV, DEFAULT_MODEL))
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and the key state, send nothing")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--no-save", action="store_true", help="do not write the review file")
    parser.add_argument("--folder", default=None, help="sweep this folder (default output\\)")
    parser.add_argument("--since", default=None,
                        help="only files modified after this date, YYYY-MM-DD")
    parser.add_argument("--sweep", action="store_true",
                        help="review every frame in scope and write the EYE_SWEEP report")
    parser.add_argument("--scope-list", action="store_true",
                        help="print the scope decision for every PNG and exit, sends nothing")
    parser.add_argument("--measure-only", action="store_true",
                        help="measure every frame in scope from its pixels and write the "
                             "report, sending nothing (use when the daily quota is gone)")
    parser.add_argument("--limit", type=int, default=None, help="stop after N frames")

    parser.add_argument("--all-scales", action="store_true",
                        help="review the same scene at every scale instead of one")
    parser.add_argument("--no-resume", action="store_true",
                        help="ignore frames already reviewed in the results file")
    parser.add_argument("--report-out", default=None, help="path for the EYE_SWEEP markdown")
    parser.add_argument("--gap", action="store_true",
                        help="report the gap between the eye and Nayil and exit")
    parser.add_argument("--nayil", metavar="FILE:nes,readability,charm",
                        help="record Nayil's own scores for one frame")
    parser.add_argument("--category", default=None,
                        help="what the frame is meant to be, passed into the prompt")
    return parser


def _parse_nayil(text):
    if ":" not in text:
        raise EyeError("--nayil wants FILE:nes,readability,charm")
    file_key, values = text.split(":", 1)
    numbers = [part.strip() for part in values.split(",") if part.strip()]
    if len(numbers) != len(DIMENSIONS):
        raise EyeError("--nayil wants %d scores in the order %s"
                       % (len(DIMENSIONS), ", ".join(DIMENSIONS)))
    return file_key.strip(), dict(zip(DIMENSIONS, numbers))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gap:
        report = gap_report()
        print("frames reviewed: %d, calibration rows: %d, compared: %d"
              % (report["frames_reviewed"], report["calibration_rows"],
                 report["compared_rows"]))
        if not report["per_dimension"]:
            print("no row has Nayil's scores yet, so there is no gap to report.")
        for dimension in DIMENSIONS:
            stats = report["per_dimension"].get(dimension)
            if stats:
                print("%-12s n=%d signed mean %+0.2f, mean |gap| %0.2f"
                      % (dimension, stats["n"], stats["signed_mean"], stats["mean_abs"]))
        return 0
    if args.nayil:
        file_key, scores = _parse_nayil(args.nayil)
        path = record_nayil(file_key, scores)
        print("recorded Nayil's scores for %s in %s" % (file_key, path))
        return 0

    if args.scope_list:
        keep, skipped = collect_scope(folder=args.folder, since=args.since,
                                      include_skipped=True)
        chosen, dropped = (choose_one_per_scene(keep) if not args.all_scales
                           else (keep, []))
        print("in scope: %d (reviewing %d), skipped: %d, same scene at another scale: %d"
              % (len(keep), len(chosen), len(skipped), len(dropped)))
        for row in chosen:
            print("  REVIEW %-58s %s" % (row["rel"], row["category"]))
        for row in dropped:
            print("  SCALE  %-58s %s" % (row["rel"], row["category"]))
        for row in skipped:
            print("  SKIP   %-58s %s" % (row["rel"], row["reason"]))
        return 0

    try:
        if args.sweep or (args.folder and not args.files):
            sweep = run_sweep(folder=args.folder, since=args.since, limit=args.limit,
                              model=args.model, save=not args.no_save,
                              resume=not args.no_resume, one_per_scene=not args.all_scales,
                              measure_only=args.measure_only)
            report = write_sweep_report(sweep, path=args.report_out, model=args.model,
                                        cutoff=args.since)
            print("reviewed %d, reused %d, failed %d, report %s"
                  % (len(sweep["reviewed"]), len(sweep["reused"]), len(sweep["failed"]),
                     report))
            return 0 if not sweep["failed"] else 1

        if not args.files:
            parser.print_usage()
            print("nothing to do: pass PNG files, --folder, --sweep, --scope-list or --gap")
            return 2

        exit_code = 0
        for path in args.files:
            result = review_image(path, model=args.model, save=not args.no_save,
                                  dry_run=args.dry_run, category=args.category)
            if args.dry_run:
                _print_plan(result["plan"])
                continue
            scores = result["scores"]
            print("file:    %s" % os.path.basename(path))
            print("model:   %s" % result["plan"]["model"])
            print("scores:  %s" % ", ".join("%s %s" % (d, scores.get(d) if scores.get(d) is not None
                                                      else "?") for d in DIMENSIONS))
            print("review:  %s" % result["review"])
            print("calls:   %d" % result["calls"])
            print(WARNING)
            print("")
            if args.json:
                print(json.dumps({"file": os.path.abspath(str(path)),
                                  "model": result["plan"]["model"],
                                  "scores": scores, "review": result["review"],
                                  "calls": result["calls"]}, indent=2))
        return exit_code
    except NotConfigured as exc:
        print("not configured: %s" % redact(exc))
        return 2
    except (DailyLimit, RateLimited) as exc:
        print("rate limited: %s" % redact(exc))
        return 3
    except EyeError as exc:
        print("error: %s" % redact(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
