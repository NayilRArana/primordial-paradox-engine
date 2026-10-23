"""The automated ear: a Gemini audio critic with a fixed rubric and a calibration log (card MUS-EAR).

The point of this tool is not to replace Nayil's ears. It is to make the algorithmic
arranger measurable while he is asleep: every render goes through the same six questions,
in the same order, and the scores land in a ledger that can be compared to his own
numbers later. Two things follow from that, and both are enforced here:

  1. The rubric is FIXED. It is the one used in
     assets\\audio\\title_theme_v3\\EAR_REVIEW_126.md: sections in time order, six 1 to 10
     scores (hook memorability, rhythm and drum interest, tension and dissonance, human
     feel versus mechanical, instrumentation variety, structure and contrast), five
     concrete changes with bar ranges or timestamps, and the two most mechanical moments.
     The prompt asks for a JSON block at the end so the scores are machine readable.

  2. The model is a rough listener. It hears the mix, not the score: it misnames channels,
     miscounts bars and invents sections. Every saved review therefore carries a warning
     line, and the scores are a hint to check against Nayil, never a verdict.

WHAT IS SENT
    An MP3, OGG, WAV or FLAC file. Up to PP_EAR_MAX_INLINE_MB (15 MB) goes inline in one
    generateContent call. A longer file is cut by ffmpeg into 60 s chunks with a pre-roll
    overlap so no phrase is sliced cold; the first two seconds after the loop point ride
    along with the last chunk as a separate "loop seam" part, because a looping track is
    heard across that jump. Every chunk gets its own call, then one text only synthesis
    call merges the chunk notes into a single review.

WHERE THINGS LAND
    assets\\audio\\ear_reviews\\<stem>_<UTC timestamp>.md   the full review with its header
    data\\ear_ledger.csv                                   one row per API call
    data\\ear_calibration.csv                              Gemini scores plus blank Nayil
                                                          columns, filled in by hand later

FREE TIER
    At most PP_EAR_MAX_PER_MINUTE calls in any 60 s window (default 10; the ledger's
    timestamps are the counter, so the limit survives process restarts), at most
    PP_EAR_DAILY_MAX calls per UTC day (default 200), and 429 backoff that honours the
    retryDelay Gemini asks for before falling back to exponential waits.

KEYS
    GEMINI_API_KEY is read from os.environ at call time and put in the x-goog-api-key
    header. It is never in a URL, never printed, never written to the ledger or the review
    file, and never included in an exception message (every error string goes through
    redact()). Login and credential files are refused as audio input rather than opened.

Usage
    python tools\\ear_critic.py --dry-run assets\\audio\\title_theme_v3\\title_theme_v3_126.mp3
    python tools\\ear_critic.py assets\\audio\\title_theme_v3\\title_theme_v3_126.mp3
    python tools\\ear_critic.py --compare a.mp3 b.mp3
    python tools\\ear_critic.py --gap
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
REVIEW_DIR = os.path.join(ROOT, "assets", "audio", "ear_reviews")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
KEY_ENV = "GEMINI_API_KEY"
MODEL_ENV = "PP_EAR_MODEL"
DEFAULT_MODEL = "gemini-3.5-flash"

DEFAULT_MAX_INLINE_MB = 15.0
CHUNK_SECONDS = 60.0
CHUNK_PREROLL = 2.0
SEAM_SECONDS = 2.0

DIMENSIONS = ("hook", "drums", "tension", "human", "variety", "structure")
DIMENSION_LABELS = {
    "hook": "Hook memorability",
    "drums": "Rhythm and drum interest",
    "tension": "Tension and dissonance (is there enough tasteful clash)",
    "human": "Human feel versus mechanical",
    "variety": "Instrumentation variety",
    "structure": "Structure and contrast",
}
DIMENSION_ALIASES = {
    "hook": "hook",
    "hook_memorability": "hook",
    "memorability": "hook",
    "drums": "drums",
    "drum": "drums",
    "rhythm": "drums",
    "rhythm_and_drum_interest": "drums",
    "tension": "tension",
    "dissonance": "tension",
    "tension_and_dissonance": "tension",
    "human": "human",
    "human_feel": "human",
    "human_feel_versus_mechanical": "human",
    "variety": "variety",
    "instrumentation": "variety",
    "instrumentation_variety": "variety",
    "structure": "structure",
    "structure_and_contrast": "structure",
}

LEDGER_COLUMNS = ["at", "file", "role", "model", "chunk", "hook", "drums", "tension",
                  "human", "variety", "structure", "seconds", "status", "review"]
CALIBRATION_COLUMNS = (["file"]
                       + ["gemini_%s" % d for d in DIMENSIONS]
                       + ["nayil_%s" % d for d in DIMENSIONS]
                       + ["nayil_note", "updated"])
SEED_CALIBRATION = {
    "file": "title_theme_v3_126",
    "gemini_hook": 6, "gemini_drums": 4, "gemini_tension": 5,
    "gemini_human": 3, "gemini_variety": 6, "gemini_structure": 5,
    "nayil_hook": "", "nayil_drums": "", "nayil_tension": "",
    "nayil_human": "", "nayil_variety": "", "nayil_structure": "",
    "nayil_note": "unknown",
    "updated": "2026-10-21",
}

WARNING = ("Warning: the model is a rough listener. It can misdescribe details (channel "
           "names, bar counts, section times) and it hears the mix rather than the score. "
           "Treat these scores as a hint to check against Nayil, not as a verdict.")

AUDIO_MIME = {
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}
_CREDENTIAL_HINTS = ("token", "secret", "credential", "password", "apikey", "api_key",
                     "auth.json", ".env", "key.txt", "id_rsa")

_urlopen = urllib.request.urlopen  # tests replace this with a fake transport


class EarError(RuntimeError):
    """Anything this tool refuses to do, with a message safe to print."""


class NotConfigured(EarError):
    pass


class RateLimited(EarError):
    pass


class DailyLimit(EarError):
    pass


# ----------------------------------------------------------------------------- small helpers

def redact(text):
    """Strip anything that looks like a key before it can reach a log line."""
    text = str(text)
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


def ledger_path():
    return os.environ.get("PP_EAR_LEDGER") or os.path.join(DATA, "ear_ledger.csv")


def calibration_path():
    return os.environ.get("PP_EAR_CALIBRATION") or os.path.join(DATA, "ear_calibration.csv")


def review_dir():
    return os.environ.get("PP_EAR_REVIEW_DIR") or REVIEW_DIR


def _refuse_credential_path(path):
    lowered = os.path.basename(str(path)).lower().replace("-", "_")
    for hint in _CREDENTIAL_HINTS:
        if hint in lowered:
            raise EarError("refusing to send %r: the name looks like a credential store"
                           % os.path.basename(str(path)))


def audio_mime(path):
    ext = os.path.splitext(str(path))[1].lower()
    if ext not in AUDIO_MIME:
        raise EarError("unsupported audio extension %r (want one of %s)"
                       % (ext, ", ".join(sorted(AUDIO_MIME))))
    return AUDIO_MIME[ext]


# ----------------------------------------------------------------------------- ledger

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
    _ensure_csv_header(path, LEDGER_COLUMNS)
    clean = {column: row.get(column, "") for column in LEDGER_COLUMNS}
    with open(path, "a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS).writerow(clean)
    return path


def _call_rows(path=None):
    """Ledger rows that represent a real API call (the summary row is bookkeeping only)."""
    return [row for row in read_ledger(path)
            if row.get("status") != "refused" and row.get("role") != "summary"]


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
        if seconds is None:
            continue
        if datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).date() == day:
            count += 1
    return count


def _parse_stamp(stamp):
    stamp = (stamp or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.datetime.strptime(stamp, fmt)
            return parsed.replace(tzinfo=datetime.timezone.utc).timestamp()
        except ValueError:
            continue
    return None


# ----------------------------------------------------------------------------- rate limits

class RateGate(object):
    """At most N calls per 60 s and M per UTC day, counted from the ledger itself."""

    def __init__(self, path=None, per_minute=None, per_day=None, sleep=None, clock=None):
        self.path = path or ledger_path()
        self.per_minute = per_minute if per_minute is not None else _env_int("PP_EAR_MAX_PER_MINUTE", 10)
        self.per_day = per_day if per_day is not None else _env_int("PP_EAR_DAILY_MAX", 200)
        self._sleep = sleep or time.sleep
        self._clock = clock or time.time

    def before_call(self):
        if self.per_day and calls_today(self.path, self._clock()) >= self.per_day:
            raise DailyLimit("daily call budget reached (%d calls today, PP_EAR_DAILY_MAX)"
                             % self.per_day)
        if not self.per_minute:
            return
        waited = 0.0
        while calls_in_last_minute(self.path, self._clock()) >= self.per_minute:
            if waited >= 120:
                raise RateLimited("still at %d calls in the last minute after waiting; "
                                  "refusing to hammer the free tier" % self.per_minute)
            pause = 5.0
            self._sleep(pause)
            waited += pause


# ----------------------------------------------------------------------------- prompt

def context_line(loop=None):
    if not loop:
        return ""
    bits = []
    if loop.get("loop_bars"):
        bits.append("%s bars" % loop["loop_bars"])
    if loop.get("time_signature"):
        bits.append("%s" % loop["time_signature"])
    if loop.get("bpm"):
        bits.append("about %g bpm" % float(loop["bpm"]))
    if loop.get("loop_seconds"):
        bits.append("the loop is %.2f s long and jumps back to the start at its end"
                    % float(loop["loop_seconds"]))
    if not bits:
        return ""
    return ("Context supplied by the renderer (trust the audio over this if they disagree): "
            + ", ".join(bits) + ".")


def rubric_prompt(scope="", loop=None):
    lines = [
        "You are a strict but fair music critic reviewing an original NES-style chiptune "
        "track (2A03 plus the VRC6 expansion). Judge it as game title music: it has to be "
        "memorable, it has to move, and it has to sound played rather than printed.",
        "",
        "Use this fixed rubric. Answer in this order with these headings, and be concrete: "
        "name bars, timestamps and channels.",
        "",
        "### 1) Section overview",
        "Walk the track in time order. For each section give the timestamp, its bar range "
        "if you can count it, what the lead does, what the accompaniment does, and how the "
        "section differs from the one before. Say plainly when you are unsure of a bar "
        "number.",
        "",
        "### 2) Evaluation and scores (1 to 10)",
        "Score each of the six lines from 1 (bad) to 10 (excellent), one short paragraph "
        "each, and say which bar range or timestamp produced the score:",
    ]
    for key in DIMENSIONS:
        lines.append("- %s" % DIMENSION_LABELS[key])
    lines += [
        "",
        "### 3) Five concrete changes",
        "Exactly five numbered changes that would raise the scores, each one naming a bar "
        "range or timestamp, the channel to change, and the specific musical move (an "
        "altered chord, a fill, a drop-out, a delayed vibrato, a swung offbeat, a pedal "
        "point). No general advice: if it cannot be written in the score, it does not count.",
        "",
        "### 4) The two most mechanical moments",
        "The two places where the performance sounds most like a machine, with timestamps "
        "and what gives it away.",
        "",
        "### 5) Scores as JSON",
        "End the reply with one fenced json block, exactly these keys, integer scores 1 to 10:",
        "```json",
        '{"hook": 6, "drums": 4, "tension": 5, "human": 3, "variety": 6, "structure": 5}',
        "```",
        "Nothing after that block.",
    ]
    if scope:
        lines += ["", scope]
    extra = context_line(loop)
    if extra:
        lines += ["", extra]
    return "\n".join(lines)


def chunk_prompt(index, total, start, end, loop=None):
    scope = ("You are hearing chunk %d of %d of one continuous piece, from %.1f s to %.1f s "
             "of the whole track. Score it as it sounds on its own, and say when a judgement "
             "depends on the part you cannot hear." % (index, total, start, end))
    return rubric_prompt(scope=scope, loop=loop)


def synthesis_prompt(chunk_reviews, loop=None, name="the track"):
    body = [
        "Below are the notes a critic wrote while hearing %s in consecutive chunks. Merge "
        "them into ONE review of the whole piece, using the fixed rubric. Do not invent "
        "anything that is not in the notes; if the notes disagree, say so and pick the "
        "reading the audio evidence supports. Keep the bar ranges and timestamps the notes "
        "give." % name,
        "",
        "### Chunk notes",
    ]
    for index, text in enumerate(chunk_reviews, 1):
        body.append("#### Chunk %d" % index)
        body.append(text.strip())
        body.append("")
    body.append(rubric_prompt(loop=loop))
    return "\n".join(body)


def compare_prompt(loop_a=None, loop_b=None):
    lines = [
        "Two versions of the same piece of NES-style title music are attached, A first, "
        "then B. Judge them as a listener who has to hum one of them tomorrow.",
        "",
        "Answer in this order:",
        "### 1) Each version in time order",
        "What A does, then what B does: sections, lead, accompaniment, drums. Be concrete.",
        "### 2) Head to head",
        "For each of the six lines below, which version wins and why, in one sentence each:",
    ]
    for key in DIMENSIONS:
        lines.append("- %s" % DIMENSION_LABELS[key])
    lines += [
        "### 3) Which is more memorable, and why",
        "One paragraph that names the specific moment in the winning version that would "
        "stick, and the specific moment in the losing version that would not.",
        "### 4) Verdict as JSON",
        "End with one fenced json block and nothing after it:",
        "```json",
        '{"winner": "A", "a": {"hook": 6, "drums": 4, "tension": 5, "human": 3, "variety": 6, "structure": 5}, '
        '"b": {"hook": 5, "drums": 5, "tension": 4, "human": 4, "variety": 5, "structure": 5}}',
        "```",
    ]
    for label, loop in (("A", loop_a), ("B", loop_b)):
        extra = context_line(loop)
        if extra:
            lines += ["", "%s. %s" % (label, extra)]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- audio

def loop_info(path):
    """Find the renderer's loop json next to the audio, if there is one."""
    folder = os.path.dirname(os.path.abspath(str(path)))
    stem = os.path.splitext(os.path.basename(str(path)))[0]
    candidates = [os.path.join(folder, stem + "_loop.json")]
    trimmed = re.sub(r"_\d+$", "", stem)
    if trimmed != stem:
        candidates.append(os.path.join(folder, trimmed + "_loop.json"))
    for candidate in candidates:
        if os.path.exists(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as handle:
                    return json.load(handle)
            except (OSError, ValueError):
                return None
    return None


def inline_part(path, label=None):
    mime = audio_mime(path)
    with open(str(path), "rb") as handle:
        payload = base64.b64encode(handle.read()).decode("ascii")
    parts = []
    if label:
        parts.append({"text": label})
    parts.append({"inline_data": {"mime_type": mime, "data": payload}})
    return parts


def plan_chunks(duration, chunk_seconds=CHUNK_SECONDS, preroll=CHUNK_PREROLL):
    """Split a long track into 60 s windows that overlap by `preroll` so no phrase is cut cold."""
    duration = float(duration or 0.0)
    if duration <= chunk_seconds:
        return [{"start": 0.0, "length": duration, "label": "0.0 s to %.1f s" % duration}]
    windows = []
    index = 0
    while True:
        base = index * chunk_seconds
        start = 0.0 if index == 0 else max(0.0, round(base - preroll, 3))
        length = round(min(chunk_seconds, duration - start), 3)
        windows.append({"start": start, "length": length,
                        "label": "%.1f s to %.1f s" % (start, start + length)})
        index += 1
        if start + length >= duration - 0.05:
            break
    # A stunted tail chunk costs a whole call to hear ten seconds; fold it into its predecessor.
    if len(windows) > 1 and windows[-1]["length"] < chunk_seconds / 3.0:
        tail = windows.pop()
        merged = windows[-1]
        merged["length"] = round(tail["start"] + tail["length"] - merged["start"], 3)
        merged["label"] = "%.1f s to %.1f s" % (merged["start"], merged["start"] + merged["length"])
    return windows


def ffmpeg_binary():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_duration(path):
    probe = shutil.which("ffprobe") or "ffprobe"
    try:
        out = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                             capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def cut_audio(source, start, length, target):
    """Cut one chunk with ffmpeg. Returns the path or raises EarError."""
    command = [ffmpeg_binary(), "-hide_banner", "-loglevel", "error", "-y",
               "-ss", "%.3f" % start, "-t", "%.3f" % length, "-i", str(source),
               "-c:a", "libmp3lame", "-b:a", "128k", str(target)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        raise EarError(redact("ffmpeg could not split the file: %s" % exc))
    if done.returncode != 0 or not os.path.exists(target):
        raise EarError(redact("ffmpeg failed to cut %.1f s at %.1f s: %s"
                              % (length, start, (done.stderr or "").strip()[:300])))
    return target


# ----------------------------------------------------------------------------- HTTP

def endpoint(model, base=None):
    base = (base or os.environ.get("GEMINI_API_BASE") or GEMINI_BASE).rstrip("/")
    return "%s/models/%s:generateContent" % (base, model)


def _retry_delay(detail, attempt, base_delay, cap):
    # The pattern only admits digits and one dot, so float() cannot fail here; no
    # try/except is needed and a bare pass would hide a real parse bug anyway.
    match = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', detail or "")
    if match:
        return min(float(match.group(1)) + 0.5, cap)
    match = re.search(r"[Rr]etry-[Aa]fter:\s*(\d+)", detail or "")
    if match:
        return min(float(match.group(1)), cap)
    return min(base_delay * (2 ** attempt), cap)


def post_generate(model, payload, timeout=None, sleep=None):
    """One POST with 429 and 5xx backoff. Returns (decoded body, retries used).

    PP_AI_BACKEND=meta hands the same payload to tools\\meta_client.py, which sends it as one
    chat completion (with its own cache, rate gate and retries) and answers in the
    generateContent shape this module already parses. The rubric, the ledger and the score
    parsing stay unchanged; only the transport and the model change.
    """
    if (os.environ.get("PP_AI_BACKEND", "").strip().lower() == "meta"):
        import meta_client  # tools\\ is on sys.path in every documented entry point
        return meta_client.gemini_compat_generate(model, payload, timeout=timeout,
                                                  sleep=sleep), 0
    key = _key()
    body = json.dumps(payload).encode("utf-8")
    url = endpoint(model)
    timeout = timeout or _env_int("PP_EAR_TIMEOUT", 180)
    max_retries = _env_int("PP_EAR_MAX_RETRIES", 3)
    base_delay = _env_float("PP_EAR_RETRY_BASE", 4.0)
    cap = _env_float("PP_EAR_MAX_BACKOFF", 90.0)
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
        raise RateLimited(redact("gemini answered 429 after %d attempt(s): %s" % (attempt + 1, detail)))
    raise EarError(redact("gemini answered %s: %s" % (code or "no response", detail)))


def read_response(data):
    """Pull the text out of a generateContent body, with a useful error otherwise."""
    candidates = (data or {}).get("candidates") or []
    if not candidates:
        feedback = (data or {}).get("promptFeedback") or {}
        raise EarError(redact("gemini returned no candidates: %s" % json.dumps(feedback)[:300]))
    parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise EarError("gemini returned an empty answer (finishReason=%r)"
                       % (candidates[0] or {}).get("finishReason"))
    usage = (data or {}).get("usageMetadata") or {}
    return text, usage


# ----------------------------------------------------------------------------- parse

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
    objects = _balanced_objects(text)
    for candidate in reversed(objects):
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
    """Map whatever keys the model used onto the six rubric dimensions."""
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
    """JSON block first, then the human readable 'Hook memorability: 6/10' lines."""
    scores = normalise_scores(_last_json_object(text))
    if any(value is not None for value in scores.values()):
        return scores
    for dimension in DIMENSIONS:
        label = re.escape(DIMENSION_LABELS[dimension].split("(")[0].strip())
        match = re.search(label + r"[^0-9\n]{0,40}?(\d{1,2})\s*(?:/|out of)\s*10", text or "", re.I)
        if match:
            scores[dimension] = _clamp(match.group(1))
    return scores


def winner_from_text(text):
    payload = _last_json_object(text)
    winner = str(payload.get("winner", "")).strip().upper()[:1]
    if winner in ("A", "B"):
        return winner
    match = re.search(r"\bMORE MEMORABLE\s*[:\-]\s*([AB])\b", text or "", re.I)
    return match.group(1).upper() if match else ""


# ----------------------------------------------------------------------------- review

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


def _render_markdown(title, model, source, scores, body, extra_meta=None):
    body = _plain_dashes(body)
    title = _plain_dashes(title)
    stamp = utc_now().strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# Ear review: %s" % title, "",
             "- model: %s" % model,
             "- file: %s" % source,
             "- reviewed: %s" % stamp]
    for key, value in (extra_meta or {}).items():
        lines.append("- %s: %s" % (key, value))
    score_line = ", ".join("%s %s" % (key, scores.get(key) if scores.get(key) is not None else "?")
                           for key in DIMENSIONS)
    lines.append("- scores: %s" % score_line)
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


def review_file(path, model=None, gate=None, save=True, dry_run=False, loop=None):
    """Review one file end to end. Returns a dict with scores, text, review path, calls."""
    path = os.path.abspath(str(path))
    if not os.path.exists(path):
        raise EarError("no such audio file: %s" % path)
    _refuse_credential_path(path)
    model = model_name(model)
    loop = loop if loop is not None else loop_info(path)
    size_mb = os.path.getsize(path) / (1024.0 * 1024.0)
    max_inline = _env_float("PP_EAR_MAX_INLINE_MB", DEFAULT_MAX_INLINE_MB)
    gate = gate or RateGate()

    if size_mb <= max_inline:
        windows = [{"start": 0.0, "length": None, "label": "the whole file"}]
        chunks = False
    else:
        duration = ffprobe_duration(path)
        if not duration:
            raise EarError("cannot read the duration of %s with ffprobe, so the file cannot "
                           "be split" % os.path.basename(path))
        windows = plan_chunks(duration)
        chunks = True

    plan = {
        "file": path,
        "model": model,
        "size_mb": round(size_mb, 2),
        "inline": not chunks,
        "windows": [w["label"] for w in windows],
        "loop": bool(loop),
        "key_present": key_present(),
        "calls_planned": len(windows) + (1 if chunks else 0),
    }
    if dry_run:
        return {"plan": plan, "scores": {}, "text": "", "review": None, "calls": 0}

    started = time.time()
    reviews = []
    calls = 0
    workdir = None
    try:
        if not chunks:
            gate.before_call()
            parts = inline_part(path)
            payload = {"contents": [{"role": "user", "parts": [{"text": rubric_prompt(
                loop=loop)}] + parts}]}
            data, retries = post_generate(model, payload)
            text, usage = read_response(data)
            calls += 1
            append_ledger({"at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"), "file": path,
                           "role": "review", "model": model, "chunk": "whole",
                           "seconds": round(time.time() - started, 2), "status": "ok"})
            reviews.append(text)
            usage_meta = usage
        else:
            workdir = tempfile.mkdtemp(prefix="pp_ear_")
            usage_meta = {}
            for index, window in enumerate(windows, 1):
                cut = cut_audio(path, window["start"], window["length"],
                                os.path.join(workdir, "chunk_%02d.mp3" % index))
                parts = inline_part(cut, label="Chunk %d of %d, %s."
                                    % (index, len(windows), window["label"]))
                if index == len(windows) and loop and loop.get("loop_start_sample") is not None:
                    seam = cut_audio(path, 0.0, SEAM_SECONDS,
                                     os.path.join(workdir, "seam.mp3"))
                    parts += inline_part(seam, label="Loop seam: this is the first %.1f s "
                                         "after the track jumps from its end back to the "
                                         "start." % SEAM_SECONDS)
                gate.before_call()
                payload = {"contents": [{"role": "user", "parts": [{"text": chunk_prompt(
                    index, len(windows), window["start"],
                    window["start"] + (window["length"] or 0), loop=loop)}] + parts}]}
                data, retries = post_generate(model, payload)
                text, _usage = read_response(data)
                calls += 1
                append_ledger({"at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"), "file": path,
                               "role": "chunk", "model": model,
                               "chunk": "%d/%d" % (index, len(windows)),
                               "seconds": round(time.time() - started, 2), "status": "ok"})
                reviews.append(text)
            gate.before_call()
            payload = {"contents": [{"role": "user", "parts": [
                {"text": synthesis_prompt(reviews, loop=loop, name=os.path.basename(path))}]}]}
            data, retries = post_generate(model, payload)
            merged, usage_meta = read_response(data)
            calls += 1
            append_ledger({"at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"), "file": path,
                           "role": "synthesis", "model": model, "chunk": "all",
                           "seconds": round(time.time() - started, 2), "status": "ok"})
            reviews = [merged]
    finally:
        if workdir and os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)

    text = reviews[0]
    scores = scores_from_text(text)
    meta = {"size_mb": round(size_mb, 2),
            "tokens": "%s in / %s out" % ((usage_meta or {}).get("promptTokenCount", "?"),
                                          (usage_meta or {}).get("candidatesTokenCount", "?")),
            "chunks": len(windows) if chunks else 1}
    markdown = _render_markdown(os.path.basename(path), model, path, scores, text, meta)
    review_path = save_review(path, markdown) if save else None
    row = {"at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"), "file": path, "role": "summary",
           "model": model, "chunk": "%d" % calls,
           "seconds": round(time.time() - started, 2), "status": "ok",
           "review": review_path or ""}
    for dimension in DIMENSIONS:
        row[dimension] = scores.get(dimension) if scores.get(dimension) is not None else ""
    append_ledger(row)
    return {"plan": plan, "scores": scores, "text": text, "review": review_path,
            "calls": calls}


def compare_files(path_a, path_b, model=None, gate=None, save=True, dry_run=False):
    """Ask which of two renders is more memorable, and why."""
    for path in (path_a, path_b):
        if not os.path.exists(str(path)):
            raise EarError("no such audio file: %s" % path)
        _refuse_credential_path(path)
    model = model_name(model)
    loop_a, loop_b = loop_info(path_a), loop_info(path_b)
    max_inline = _env_float("PP_EAR_MAX_INLINE_MB", DEFAULT_MAX_INLINE_MB)
    sizes = [os.path.getsize(str(p)) / (1024.0 * 1024.0) for p in (path_a, path_b)]
    if max(sizes) > max_inline:
        raise EarError("compare takes files that fit inline (%.0f MB each); split the long "
                       "one with --chunk first" % max_inline)
    plan = {"a": os.path.abspath(str(path_a)), "b": os.path.abspath(str(path_b)),
            "model": model, "sizes_mb": [round(s, 2) for s in sizes],
            "key_present": key_present(), "calls_planned": 1}
    if dry_run:
        return {"plan": plan, "text": "", "review": None, "winner": "", "scores": {}}
    gate = gate or RateGate()
    gate.before_call()
    started = time.time()
    parts = inline_part(path_a)
    parts += inline_part(path_b)
    payload = {"contents": [{"role": "user", "parts": [{"text": compare_prompt(loop_a, loop_b)}]
                             + parts}]}
    data, retries = post_generate(model, payload)
    text, usage = read_response(data)
    winner = winner_from_text(text)
    payload_json = _last_json_object(text)
    scores_a = normalise_scores(payload_json.get("a") or {})
    scores_b = normalise_scores(payload_json.get("b") or {})
    body = text
    if winner:
        body = text.strip() + "\n\n**Verdict: version %s is more memorable.**\n" % winner
    meta = {"a": os.path.basename(str(path_a)), "b": os.path.basename(str(path_b)),
            "winner": winner or "unstated"}
    markdown = _render_markdown("%s versus %s" % (os.path.basename(str(path_a)),
                                                  os.path.basename(str(path_b))),
                                model, "%s | %s" % (path_a, path_b), scores_a, body, meta)
    review_path = save_review("compare_%s_%s" % (os.path.splitext(os.path.basename(str(path_a)))[0],
                                                 os.path.splitext(os.path.basename(str(path_b)))[0]),
                              markdown) if save else None
    row = {"at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "file": "%s vs %s" % (path_a, path_b), "role": "compare", "model": model,
           "chunk": "a+b", "seconds": round(time.time() - started, 2), "status": "ok",
           "review": review_path or ""}
    append_ledger(row)
    return {"plan": plan, "text": text, "review": review_path, "winner": winner,
            "a": scores_a, "b": scores_b, "scores": scores_a}


# ----------------------------------------------------------------------------- calibration

def seed_calibration(path=None):
    """Create the calibration file with the one row the card already knows about."""
    path = path or calibration_path()
    _ensure_csv_header(path, CALIBRATION_COLUMNS)
    rows = read_calibration(path)
    if not rows:
        with open(path, "a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=CALIBRATION_COLUMNS).writerow(SEED_CALIBRATION)
    return path


def read_calibration(path=None):
    path = path or calibration_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def record_nayil(file_key, scores, note="", path=None):
    """Enter Nayil's own 1 to 10 scores for a file (all six, or a subset by keyword)."""
    path = seed_calibration(path)
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
            raise EarError("score for %r must be an integer 1 to 10, got %r" % (key, value))
        entry["nayil_%s" % dimension] = number
    if note:
        entry["nayil_note"] = note
    entry["updated"] = utc_now().strftime("%Y-%m-%d")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALIBRATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CALIBRATION_COLUMNS})
    return path


def gap_report(path=None):
    """Compare the ear's scores to Nayil's, per dimension and overall."""
    seed_calibration(path)
    rows = read_calibration(path)
    per_dimension = {}
    compared = 0
    waiting = []
    for row in rows:
        pairs = []
        for dimension in DIMENSIONS:
            ear = _clamp(row.get("gemini_%s" % dimension))
            human = _clamp(row.get("nayil_%s" % dimension))
            if ear is not None and human is not None:
                pairs.append((dimension, ear - human))
        if pairs:
            compared += 1
            for dimension, diff in pairs:
                per_dimension.setdefault(dimension, []).append(diff)
        else:
            waiting.append(row.get("file", "?"))
    summary = {}
    for dimension in DIMENSIONS:
        diffs = per_dimension.get(dimension, [])
        if diffs:
            summary[dimension] = {
                "n": len(diffs),
                "signed_mean": round(sum(diffs) / float(len(diffs)), 2),
                "mean_abs": round(sum(abs(d) for d in diffs) / float(len(diffs)), 2),
                "max_abs": max(abs(d) for d in diffs),
            }
    all_diffs = [d for diffs in per_dimension.values() for d in diffs]
    return {
        "rows": len(rows),
        "compared_rows": compared,
        "waiting_for_nayil": waiting,
        "per_dimension": summary,
        "overall_mean_abs": round(sum(abs(d) for d in all_diffs) / float(len(all_diffs)), 2)
        if all_diffs else None,
    }


def format_gap(report):
    lines = ["Ear versus Nayil (%d calibration rows, %d with both sets of scores)"
             % (report["rows"], report["compared_rows"])]
    if not report["per_dimension"]:
        lines.append("No row has Nayil's scores yet, so there is no gap to report.")
    else:
        lines.append("dimension                 n   ear-human   mean |gap|   worst")
        for dimension in DIMENSIONS:
            stats = report["per_dimension"].get(dimension)
            if not stats:
                continue
            lines.append("%-24s %3d %+11.2f %11.2f %7d"
                         % (dimension, stats["n"], stats["signed_mean"],
                            stats["mean_abs"], stats["max_abs"]))
        lines.append("overall mean absolute gap: %.2f points (10 point scale)"
                     % report["overall_mean_abs"])
    if report["waiting_for_nayil"]:
        lines.append("waiting for Nayil: %s" % ", ".join(report["waiting_for_nayil"]))
    lines.append("positive ear-human means the ear is kinder than Nayil.")
    return "\n".join(lines)


def calibration_row_for(result, file_key):
    """Write a finished review's Gemini scores into the calibration table."""
    path = seed_calibration()
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
    for dimension in DIMENSIONS:
        value = (result.get("scores") or {}).get(dimension)
        entry["gemini_%s" % dimension] = "" if value is None else value
    entry["updated"] = utc_now().strftime("%Y-%m-%d")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALIBRATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CALIBRATION_COLUMNS})
    return path


# ----------------------------------------------------------------------------- cli

def _print_plan(plan):
    label = plan.get("file")
    if not label:
        label = "%s versus %s" % (plan.get("a"), plan.get("b"))
    print("file:    %s" % label)
    print("model:   %s" % plan["model"])
    if "size_mb" in plan:
        print("size:    %.2f MB (%s)" % (plan["size_mb"],
                                         "inline in one call" if plan["inline"]
                                         else "split into %d chunks" % len(plan["windows"])))
        print("chunks:  %s" % " | ".join(plan["windows"]))
        print("loop:    %s" % ("renderer loop json found" if plan["loop"] else "none"))
    if "sizes_mb" in plan:
        print("sizes:   A %.2f MB, B %.2f MB" % tuple(plan["sizes_mb"]))
    print("key:     %s" % ("present in %s" % KEY_ENV if plan["key_present"]
                           else "absent from %s, a real run would refuse" % KEY_ENV))
    print("calls:   %d planned" % plan["calls_planned"])


def build_parser():
    parser = argparse.ArgumentParser(
        description="Review NES-style audio with Gemini against the fixed ear rubric.")
    parser.add_argument("files", nargs="*", help="MP3, OGG, WAV or FLAC files to review")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"),
                        help="ask which of two renders is more memorable and why")
    parser.add_argument("--model", default=None,
                        help="model name (default: $%s or %s)" % (MODEL_ENV, DEFAULT_MODEL))
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and the key state, send nothing")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--no-save", action="store_true", help="do not write the review file")
    parser.add_argument("--gap", action="store_true",
                        help="report the gap between the ear and Nayil and exit")
    parser.add_argument("--nayil", metavar="FILE:hook,drums,tension,human,variety,structure",
                        help="record Nayil's own scores, for example "
                             "title_theme_v3_126:7,5,6,5,6,6")
    parser.add_argument("--ledger", action="store_true", help="print the ledger and exit")
    return parser


def _parse_nayil(text):
    if ":" not in text:
        raise EarError("--nayil wants FILE:s1,s2,s3,s4,s5,s6")
    file_key, values = text.split(":", 1)
    numbers = [part.strip() for part in values.split(",") if part.strip()]
    if len(numbers) != len(DIMENSIONS):
        raise EarError("--nayil wants %d scores in the order %s"
                       % (len(DIMENSIONS), ", ".join(DIMENSIONS)))
    return file_key.strip(), dict(zip(DIMENSIONS, numbers))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gap:
        print(format_gap(gap_report()))
        return 0
    if args.nayil:
        file_key, scores = _parse_nayil(args.nayil)
        path = record_nayil(file_key, scores)
        print("recorded Nayil's scores for %s in %s" % (file_key, path))
        print(format_gap(gap_report()))
        return 0
    if args.ledger:
        rows = read_ledger()
        print("%d ledger row(s) in %s" % (len(rows), ledger_path()))
        for row in rows[-10:]:
            print("  %s %-8s %-22s %s" % (row.get("at"), row.get("role"),
                                          os.path.basename(row.get("file", "")),
                                          " ".join("%s=%s" % (d, row.get(d) or "?")
                                                   for d in DIMENSIONS)))
        return 0

    try:
        if args.compare:
            path_a, path_b = args.compare
            result = compare_files(path_a, path_b, model=args.model,
                                   save=not args.no_save, dry_run=args.dry_run)
            if args.dry_run:
                _print_plan(result["plan"])
                return 0
            print(result["text"].strip())
            print("")
            print("winner: %s" % (result["winner"] or "unstated"))
            print("review: %s" % result["review"])
            print(WARNING)
            return 0

        if not args.files:
            parser.print_usage()
            print("nothing to do: pass one or more audio files, --compare, --gap or --ledger")
            return 2

        exit_code = 0
        for path in args.files:
            result = review_file(path, model=args.model, save=not args.no_save,
                                 dry_run=args.dry_run)
            if args.dry_run:
                _print_plan(result["plan"])
                continue
            scores = result["scores"]
            print("file:    %s" % os.path.basename(path))
            print("model:   %s" % result["plan"]["model"])
            print("scores:  %s" % ", ".join("%s %s" % (d, scores.get(d) if scores.get(d) is not None else "?")
                                            for d in DIMENSIONS))
            print("review:  %s" % result["review"])
            print("calls:   %d" % result["calls"])
            calibration_row_for(result, os.path.splitext(os.path.basename(str(path)))[0])
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
    except EarError as exc:
        print("error: %s" % redact(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
