"""One client for the Meta Model API: chat, vision, image, edit, segmentation (card META-CLIENT).

Primordial Paradox talks to Meta models in four places: the TALK judge (Muse Spark, structured
verdict), the eye critic (Muse Spark vision on a 256x240 frame), concept art (Muse Image) and
the silhouette cut (SAM 3.1). This module is the only place that knows the HTTP shapes, so a
change of model, a rate limit, a cache replay or a missing key is fixed once.

README
======
Quick start, offline first (no key, no network, deterministic):

    set PP_AI_BACKEND=mock
    python tools\\meta_client.py --dry-run
    python tools\\meta_client.py --record-demo

Against the real API (once the Meta key exists):

    set MODEL_API_KEY=<your key>          (META_API_KEY also accepted; never paste it in a file)
    python tools\\meta_client.py --dry-run --json
    python tools\\meta_client.py --record-demo --live

For the demo, and for any test, replay the committed cache with the network off:

    set PP_AI_MODE=replay
    python tools\\meta_client.py --cache-status

From Python:

    import meta_client
    text = meta_client.chat([{"role": "user", "content": "Judge this line."}])
    verdict = meta_client.parse_json(text)
    note = meta_client.vision("Score this frame for NES authenticity.", "output\\frame_010.png")
    made = meta_client.generate_image("a flat 16 colour knight on a plain background")
    cut = meta_client.segment("output\\knight_concept.png", "knight")
    framed = meta_client.edit_image("output\\knight_concept.png", "same knight, front view")

    # a schema enforced by the API instead of by a regex afterwards
    verdict = meta_client.chat_structured(messages, schema=TALK_SCHEMA)

Environment (read at call time, never at import):

    PP_AI_BACKEND    meta (default) | gemini | mock
    PP_AI_MODE       record (default) | replay | live
    MODEL_API_KEY    first choice for the Meta key
    META_API_KEY     fallback (Muse Code's headless name)
    META_API_BASE    default https://api.meta.ai/v1
    PP_AI_CACHE      cache directory, default data\\ai_cache
    PP_META_MODEL    default chat model, default muse-spark-1.3, role overrides below
    PP_META_MODEL_<ROLE>  e.g. PP_META_MODEL_VISION, PP_META_MODEL_IMAGE, PP_META_MODEL_SEGMENT
    PP_META_RPM      request per minute ceiling, default per model from RPMS below
    PP_META_TIMEOUT  seconds per HTTP call, default 120
    PP_META_MAX_RETRIES  retries after a 429 or a 5xx, default 3
    PP_META_MAX_BACKOFF  backoff ceiling in seconds, default 60

Cache, and why every call goes through it
=========================================
Every call is keyed by a sha256 over (kind, model, base URL, request payload), so the same
question gets the same answer, and the answer survives the network, the key and the credits.

    data\\ai_cache\\<key>.json    one file per call, written in record mode

Entry fields: key, kind, backend, model, mode, recorded_at, network (true when a real HTTP
call produced it), request (the payload with any inline image replaced by its sha256, so a
cache file stays small), response (the normalised answer the client returns).

Modes: record calls the API and writes the entry; replay never touches the network and raises
CacheMiss when the entry is missing; live calls the API and writes nothing. The default is
record, because the demo must never depend on a live call succeeding.

The directory is a build time input: the engine never opens it, so tools\\sync_data.py lists
ai_cache/ in NOT_RUNTIME_DIRS and the game bundle does not carry it (the same reason
data\\palette_recipes.json is not mirrored), and tests/test_project.py pins that. The entries
stay committed anyway, because replay and the offline demo read them from data\\.

The committed cache is honestly labelled: entries recorded with PP_AI_BACKEND=mock carry
backend "mock" and network false, and they are what CI and the offline demo replay. Real
Meta responses can only be recorded on a machine that has the key, with --live omitted and
--record-demo, and that run replaces the mock entries with network true ones.

What is verified and what is not, as of 2026-10-22
=================================================
Facts taken from the hackathon brief (itself read from dev.meta.ai on 2026-10-21) and marked
below where the docs are silent. No Meta key exists in this environment on 2026-10-22, so no
request in this file has been exercised against the live API. The shapes are the documented
OpenAI-compatible ones, and the test suite drives them through a fake transport.

    base and auth      https://api.meta.ai/v1, Bearer MODEL_API_KEY, drop-in OpenAI: documented.
    chat completions   POST /chat/completions with {model, messages}: documented.
    structured output  response_format json_schema: documented as API enforced, OpenAI shape.
    images             POST /images/generations and /images/edits: documented as OpenAI Images
                       compatible; {"size"} sets an aspect ratio only, not exact pixels.
    image edits        the docs also accept a Meta specific JSON "images" array of URL or
                       file_id; this client sends an inline data URL there. UNVERIFIED which
                       of the two field names the server prefers for inline bytes.
    segmentation       SAM 3.1 is called over POST /responses with one noun phrase plus one
                       image part, and answers special token text with a box and a one bit
                       mask. The exact token grammar is NOT in the docs we hold, so
                       parse_segmentation() is tolerant, returns the raw text every time and
                       reports boxes as [] rather than inventing a box it did not read.
    vision token cost  about 3 tokens for a 1x1 and 1,300 to 1,500 for a 1280 px image, so a
                       256x240 frame is a few hundred tokens: documented.
    audio in chat      Muse Spark takes audio input, but the OpenAI-compatible part type for
                       audio is not documented; gemini_compat_generate() sends inline audio as
                       a data URL and labels the result UNVERIFIED for the ear critic.

Keys
====
The key is read from os.environ at call time, put in exactly one place (the Authorization
header) and nowhere else: not in the URL, not in a cache entry, not in a log line, not in an
exception message. Every error string goes through redact() first, and a transport that
somehow echoes a header has its token stripped before it reaches a caller.

Rate limits
===========
A per process gate keeps the request rate under the documented per model RPM (muse-image-1.0
is the tightest at 150 RPM), and a 429 is retried with the Retry-After the server sends, or
exponential backoff with jitter starting at 0.5 s, capped at PP_META_MAX_BACKOFF. Running out
of retries raises RateLimited, never a silent empty answer.

Sources read 2026-10-21 for these facts: https://dev.meta.ai/docs/overview,
https://dev.meta.ai/docs/image-generation, https://dev.meta.ai/docs/media-segmentation,
https://dev.meta.ai/docs/pricing-rate-limits (all quoted in HACKATHON-BRIEF.md).

Usage
    python tools\\meta_client.py --dry-run
    python tools\\meta_client.py --dry-run --json
    python tools\\meta_client.py --cache-status
    python tools\\meta_client.py --record-demo
"""

from __future__ import annotations

import zlib
import argparse
import base64
import contextlib
import hashlib
import json
import mimetypes
import os
import random
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_CACHE_DIR = os.path.join(ROOT, "data", "ai_cache")

DEFAULT_BASE = "https://api.meta.ai/v1"
KEY_ENVS = ("MODEL_API_KEY", "META_API_KEY")
DEFAULT_MODELS = {
    "chat": "muse-spark-1.3",
    "vision": "muse-spark-1.3",
    "image": "muse-image-1.0",
    "edit": "muse-image-1.0",
    "segment": "sam-3.1",
}
# Documented per team RPM, from the pricing and rate limits page read 2026-10-21. Anything not
# listed keeps DEFAULT_RPM. The gate is a courtesy, not a quota manager: the server's 429 is
# still honoured, and PP_META_RPM overrides this table.
RPMS = {
    "muse-image-1.0": 150,
    "sam-3.1": 3000,
    "muse-spark-1.3-contributor": 150,
}
DEFAULT_RPM = 3000
DEFAULT_TIMEOUT = 120
MODE_CHOICES = ("record", "replay", "live")
BACKEND_CHOICES = ("meta", "gemini", "mock")

# The exact SAM 3.1 token grammar is not in the docs we hold; this sentence is what segment()
# says about a text answer it could not turn into boxes, so a caller is never told a mask
# exists when it does not.
SAM_PARSE_NOTE = ("boxes parsed from the documented special token text; the token grammar is "
                  "UNKNOWN in the docs read 2026-10-21, so raw text is always returned")
MOCK_PALETTE = ((15, 15, 15), (252, 252, 252), (60, 60, 200), (220, 60, 60),
                (60, 190, 60), (240, 200, 60), (150, 80, 200), (60, 200, 200))
CREDENTIAL_MARKERS = ("token", "secret", "credential", "password", "apikey", "api_key",
                      "auth.json", ".env", ".pem")


# ---------------------------------------------------------------- errors

class MetaError(RuntimeError):
    """A model call failed. The message is already redacted."""


class MetaKeyMissing(MetaError):
    """Neither MODEL_API_KEY nor META_API_KEY is in the environment, so no request was made."""


class CacheMiss(MetaError):
    """Replay mode found no recorded answer for this request."""


class RateLimited(MetaError):
    """The API kept answering 429 after the retry budget was spent."""


class BadResponse(MetaError):
    """The API answered 2xx with a body this client cannot read."""


class NotConfigured(MetaError):
    """The chosen backend cannot serve that kind of call, so no request was made."""


# ---------------------------------------------------------------- small helpers

def redact(text):
    """Strip any environment key that leaked into a string bound for a log or an exception."""
    if text is None:
        return ""
    out = str(text)
    for name in KEY_ENVS + ("GEMINI_API_KEY", "PINE_SANDBOX_API_KEY"):
        value = os.environ.get(name)
        if value and len(value) >= 8:
            out = out.replace(value, "[REDACTED]")
    out = re.sub(r"(?i)(api[_-]?key|key|token|authorization)(=|:\s*|\s+bearer\s+)[^\s&\"',}]+",
                 r"\1\2[REDACTED]", out)
    return out


def _env(name, default=""):
    return (os.environ.get(name, "") or "").strip() or default


def _env_int(name, default):
    try:
        return int(_env(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name, default):
    try:
        return float(_env(name, str(default)))
    except (TypeError, ValueError):
        return default


def base_url():
    return _env("META_API_BASE", DEFAULT_BASE).rstrip("/")


def backend_name():
    chosen = _env("PP_AI_BACKEND", "meta").lower()
    return chosen


def mode():
    chosen = _env("PP_AI_MODE", "record").lower()
    return chosen


def model_for(role):
    role_env = "PP_META_MODEL_%s" % str(role or "chat").upper().replace("-", "_")
    return (_env(role_env) or _env("PP_META_MODEL") or DEFAULT_MODELS.get(role)
            or DEFAULT_MODELS["chat"])


def api_key():
    for name in KEY_ENVS:
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    raise MetaKeyMissing(
        "no Meta API key: set MODEL_API_KEY (or META_API_KEY) in the environment. "
        "Nothing was sent. Use PP_AI_BACKEND=mock or PP_AI_MODE=replay to work offline.")


def key_present():
    return any(os.environ.get(name, "").strip() for name in KEY_ENVS)


def _refuse_credential_path(path):
    lowered = os.path.basename(str(path)).lower()
    if any(marker in lowered for marker in CREDENTIAL_MARKERS):
        raise ValueError("refusing to read %r as an image: the name looks like a credential "
                         "file" % os.path.basename(str(path)))


def _utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise_messages(messages):
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    if isinstance(messages, dict):
        return [messages]
    out = []
    for item in messages:
        if isinstance(item, str):
            out.append({"role": "user", "content": item})
        elif isinstance(item, dict) and "content" in item:
            out.append({"role": item.get("role", "user"), "content": item["content"]})
        else:
            raise ValueError("each message must be a string or a {role, content} dict")
    if not out:
        raise ValueError("messages is empty")
    return out


def parse_json(text):
    """The last JSON object in a model answer, as a dict. Raises BadResponse when there is none."""
    if isinstance(text, dict):
        return text
    body = str(text or "")
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", body, re.S)
    candidates = fenced + [body]
    for chunk in candidates:
        start = chunk.find("{")
        while start != -1:
            depth = 0
            for index in range(start, len(chunk)):
                if chunk[index] == "{":
                    depth += 1
                elif chunk[index] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            value = json.loads(chunk[start:index + 1])
                        except ValueError:
                            break
                        if isinstance(value, dict):
                            return value
                        break
            start = chunk.find("{", start + 1)
    raise BadResponse("the answer held no JSON object to parse (%d chars)" % len(body))


# ---------------------------------------------------------------- images

def _read_image(path):
    """(mime, base64 text, sha256 hex) for an image path. Refuses credential looking names."""
    _refuse_credential_path(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    with open(path, "rb") as handle:
        raw = handle.read()
    return mime, base64.b64encode(raw).decode("ascii"), hashlib.sha256(raw).hexdigest()


def _data_url(mime, b64_text):
    return "data:%s;base64,%s" % (mime or "image/png", b64_text)


def png_bytes(width, height, rgb=(15, 15, 15)):
    """A valid PNG of one flat colour, built with the standard library only (mock output)."""
    width = max(1, int(width))
    height = max(1, int(height))
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def parse_size(size, cap=None):
    """'1024x1024' -> (1024, 1024). A cap keeps a mock PNG small; the real API is not capped."""
    match = re.match(r"^\s*(\d+)\s*[xX*]\s*(\d+)\s*$", str(size or ""))
    if not match:
        raise ValueError("size must look like 1024x1024, got %r" % size)
    width, height = int(match.group(1)), int(match.group(2))
    if cap:
        width, height = min(width, cap), min(height, cap)
    return width, height


# ---------------------------------------------------------------- cache

def cache_dir():
    return os.path.abspath(_env("PP_AI_CACHE", DEFAULT_CACHE_DIR))


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def request_key(kind, model, payload, extra=""):
    material = _canonical({"kind": kind, "model": model, "base": base_url(),
                           "payload": payload, "extra": extra})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def cache_path(key):
    return os.path.join(cache_dir(), "%s.json" % key)


def _shrink(payload):
    """The payload with long strings (inline images) replaced by their digest, for the entry."""
    if isinstance(payload, dict):
        return {str(k): _shrink(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [_shrink(v) for v in payload]
    if isinstance(payload, str) and len(payload) > 512:
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return "<sha256:%s:%d chars>" % (digest[:16], len(payload))
    return payload


def cache_read(key):
    path = cache_path(key)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        entry = json.load(handle)
    if not isinstance(entry, dict) or "response" not in entry:
        raise BadResponse("cache entry %s has no response field" % os.path.basename(path))
    return entry


def cache_write(key, kind, backend, model, payload, response, network):
    path = cache_path(key)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    entry = {
        "key": key,
        "kind": kind,
        "backend": backend,
        "model": model,
        "mode": "record",
        "recorded_at": _utc_stamp(),
        "network": bool(network),
        "request": _shrink(payload),
        "response": response,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(entry, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return entry


def cache_entries():
    folder = cache_dir()
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(folder, name), "r", encoding="utf-8") as handle:
                entry = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(entry, dict):
            out.append(entry)
    return out


# ---------------------------------------------------------------- rate limit and transport

class RateGate(object):
    """A sliding 60 s window per process, so a burst never reaches the server's RPM ceiling."""

    def __init__(self, window=60.0):
        self.window = window
        self.stamps = deque()

    def acquire(self, rpm, sleep):
        if rpm is None or rpm <= 0:
            return 0.0
        waited = 0.0
        now = time.monotonic()
        while self.stamps and now - self.stamps[0] > self.window:
            self.stamps.popleft()
        if len(self.stamps) >= rpm:
            wait = self.window - (now - self.stamps[0]) + 0.001
            if wait > 0:
                sleep(wait)
                waited = wait
            now = time.monotonic()
            while self.stamps and now - self.stamps[0] > self.window:
                self.stamps.popleft()
        self.stamps.append(time.monotonic())
        return waited

    def reset(self):
        self.stamps.clear()


GATE = RateGate()
SLEEP = time.sleep


def rpm_for(model):
    return _env_int("PP_META_RPM", RPMS.get(model, DEFAULT_RPM))


def reset_rate_state():
    GATE.reset()


class UrllibTransport(object):
    """One POST, no SDK. Returns (status, headers, body text) instead of raising on 4xx."""

    name = "urllib"

    def post(self, url, payload, headers, timeout):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        for name, value in headers.items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return (getattr(response, "status", 200),
                        {str(k).lower(): str(v) for k, v in response.headers.items()},
                        response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001 - a body that cannot be read is not an error
                detail = ""
            headers_out = {str(k).lower(): str(v) for k, v in (exc.headers or {}).items()}
            return exc.code, headers_out, detail
        except urllib.error.URLError as exc:
            return 0, {}, "network error: %s" % (exc.reason,)


TRANSPORT = UrllibTransport()


def _retry_after(headers, body_text, attempt):
    """Seconds to wait: Retry-After when the server sends it, else jittered exponential."""
    cap = _env_float("PP_META_MAX_BACKOFF", 60.0)
    for name in ("retry-after", "retry-after-ms"):
        raw = (headers or {}).get(name)
        if raw:
            try:
                value = float(str(raw).strip())
            except ValueError:
                break
            if name.endswith("-ms"):
                value = value / 1000.0
            return max(0.0, min(value, cap))
    match = re.search(r'"retry_after"\s*:\s*(\d+(?:\.\d+)?)', body_text or "")
    if match:
        return max(0.0, min(float(match.group(1)), cap))
    base = _env_float("PP_META_RETRY_BASE", 0.5)
    delay = min(base * (2 ** attempt), cap)
    return delay + random.uniform(0, delay / 2.0)


def _post_with_retry(url, payload, sleep=None):
    """POST with the key header, the rate gate, and the 429 and 5xx retry policy."""
    marker, key = api_key()
    sleep = sleep or SLEEP
    headers = {"Content-Type": "application/json", "Authorization": "Bearer %s" % key}
    timeout = _env_float("PP_META_TIMEOUT", DEFAULT_TIMEOUT)
    model = str(payload.get("model") or "")
    max_retries = _env_int("PP_META_MAX_RETRIES", 3)
    attempt = 0
    while True:
        GATE.acquire(rpm_for(model), sleep)
        status, response_headers, body_text = TRANSPORT.post(url, payload, headers, timeout)
        if status in (429, 500, 502, 503, 504):
            if attempt >= max_retries:
                detail = redact(str(body_text)[:300])
                if status == 429:
                    raise RateLimited("%s answered 429 after %d attempt(s): %s"
                                      % (marker, attempt + 1, detail))
                raise MetaError("%s answered %s after %d attempt(s): %s"
                                % (marker, status, attempt + 1, detail))
            sleep(_retry_after(response_headers, body_text, attempt))
            attempt += 1
            continue
        if status == 0:
            raise MetaError(redact("no response from %s: %s" % (url, str(body_text)[:200])))
        if status >= 400:
            raise MetaError(redact("%s answered %s: %s"
                                   % (marker, status, str(body_text)[:400])))
        try:
            return json.loads(body_text)
        except ValueError:
            raise BadResponse(redact("the answer was not JSON (%d chars, status %s)"
                                     % (len(str(body_text)), status)))


# ---------------------------------------------------------------- mock answers

def _mock_color(prompt):
    digest = hashlib.sha256(str(prompt).encode("utf-8")).digest()
    return MOCK_PALETTE[digest[0] % len(MOCK_PALETTE)]


def _mock_from_schema(schema):
    """A canned instance of a JSON schema: strings, numbers, booleans, arrays in order."""
    if not isinstance(schema, dict):
        return "mock"
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        return {name: _mock_from_schema(sub)
                for name, sub in (schema.get("properties") or {}).items()}
    if kind == "array":
        return [_mock_from_schema(schema.get("items") or {})]
    if kind == "integer":
        return 0
    if kind == "number":
        return 0.0
    if kind == "boolean":
        return False
    if kind == "null":
        return None
    return "mock"


def _mock_answer(kind, model, payload, schema=None):
    """Deterministic, offline, content addressed: same request, same answer, no network."""
    digest = hashlib.sha256(_canonical({"kind": kind, "model": model,
                                       "payload": _shrink(payload)}).encode("utf-8")).hexdigest()
    short = digest[:12]
    if kind in ("chat", "vision"):
        if kind == "chat":
            turns = normalise_messages(payload.get("messages") or [])
            last = turns[-1]["content"]
            last = last if isinstance(last, str) else _canonical(last)
            text = "mock chat %s (%d turns): %s" % (short, len(turns), last[:120])
        else:
            parts = payload.get("messages") or [{"content": ""}]
            content = parts[-1].get("content")
            text_part = ""
            images = 0
            if isinstance(content, list):
                text_part = " ".join(str(p.get("text", "")) for p in content
                                     if isinstance(p, dict) and p.get("type") == "text")
                images = sum(1 for p in content
                             if isinstance(p, dict) and p.get("type") == "image_url")
            text = "mock vision %s (%d image(s)): %s" % (short, images, text_part[:120])
        if schema:
            text = json.dumps(_mock_from_schema(schema), sort_keys=True)
        return {"text": text,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "mock": True}
    if kind in ("image", "edit"):
        width, height = parse_size(payload.get("size") or "1024x1024", cap=64)
        prompt = payload.get("prompt") or ""
        return {"image_b64": base64.b64encode(png_bytes(width, height,
                                                        _mock_color(prompt))).decode("ascii"),
                "format": "png", "url": None, "width": width, "height": height, "mock": True}
    if kind == "segment":
        return {"text": "mock segmentation %s: %s" % (short, payload.get("prompt") or ""),
                "boxes": [[0, 0, 16, 16]], "masks": ["mock-mask-%s" % short], "mock": True}
    raise NotConfigured("no mock for kind %r" % kind)


# ---------------------------------------------------------------- the one dispatch

def _gemini_live(kind, payload, schema=None):
    """PP_AI_BACKEND=gemini keeps working: the existing Gemini client does the HTTP."""
    try:
        import ai_client
    except ImportError as exc:  # pragma: no cover - tools is on the path in every real use
        raise NotConfigured("PP_AI_BACKEND=gemini needs tools\\ai_client.py on the path: %s"
                            % (exc,))
    if kind == "chat":
        text = ai_client.chat(payload["messages"], backend="gemini")
        return {"text": text, "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                                        "total_tokens": 0}}
    if kind == "vision":
        content = payload["messages"][-1]["content"]
        image = [p for p in content if p.get("type") == "image_url"][0]["image_url"]["url"]
        prompt = " ".join(p.get("text", "") for p in content if p.get("type") == "text")
        text = _gemini_vision_via_file(ai_client, image, prompt)
        return {"text": text, "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                                        "total_tokens": 0}}
    raise NotConfigured("PP_AI_BACKEND=gemini cannot serve %r here: %s needs the Meta backend"
                       % (kind, kind))


def _gemini_vision_via_file(ai_client, data_url, prompt):
    """ai_client.vision() takes a path, so the data URL is written to a temp file first."""
    import tempfile
    header, _, b64_text = data_url.partition(",")
    suffix = ".png" if "png" in header else ".jpg"
    handle, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(base64.b64decode(b64_text))
        return ai_client.vision(path, prompt, backend="gemini")
    finally:
        # A temp file that cannot be removed must not mask the model answer or its error.
        with contextlib.suppress(OSError):
            os.unlink(path)


def _dispatch(kind, model, payload, schema=None, sleep=None, request_echo=None):
    """Run one call through the cache. Returns (response dict, cached flag, backend, mode)."""
    backend = backend_name()
    chosen_mode = mode()
    if backend not in BACKEND_CHOICES:
        raise NotConfigured("unknown PP_AI_BACKEND %r (known: %s)"
                            % (backend, ", ".join(BACKEND_CHOICES)))
    if chosen_mode not in MODE_CHOICES:
        raise NotConfigured("unknown PP_AI_MODE %r (known: %s)"
                            % (chosen_mode, ", ".join(MODE_CHOICES)))
    if backend == "gemini":
        # The Gemini client has its own ledger and cache policy, so keying it again here would
        # record the same call twice. Pass through, and say so in the dry run.
        return _gemini_live(kind, payload, schema), False, backend, "live"
    echo = request_echo if request_echo is not None else payload
    key = request_key(kind, model, echo, extra=str(backend))
    if chosen_mode == "replay":
        entry = cache_read(key)
        if entry is None:
            raise CacheMiss("no recorded answer for %s with model %s (looked for %s). Record it "
                            "with PP_AI_MODE=record, or run offline with PP_AI_BACKEND=mock."
                            % (kind, model, os.path.basename(cache_path(key))))
        return entry["response"], True, backend, chosen_mode
    if backend == "mock":
        response = _mock_answer(kind, model, payload, schema)
        if chosen_mode == "record":
            cache_write(key, kind, backend, model, echo, response, network=False)
        return response, False, backend, chosen_mode
    if not key_present():
        api_key()  # raises MetaKeyMissing with the offline advice
    data = _live_call(kind, model, payload, sleep)
    response = _normalise(kind, data)
    if chosen_mode == "record":
        cache_write(key, kind, backend, model, echo, response, network=True)
    return response, False, backend, chosen_mode


def _live_call(kind, model, payload, sleep=None):
    url = base_url()
    if kind in ("chat", "vision"):
        return _post_with_retry("%s/chat/completions" % url, payload, sleep=sleep)
    if kind == "image":
        return _post_with_retry("%s/images/generations" % url, payload, sleep=sleep)
    if kind == "edit":
        return _post_with_retry("%s/images/edits" % url, payload, sleep=sleep)
    if kind == "segment":
        return _post_with_retry("%s/responses" % url, payload, sleep=sleep)
    raise NotConfigured("no endpoint for kind %r" % kind)


def _normalise(kind, data):
    """The answer the public functions return, and the only thing written to the cache."""
    if not isinstance(data, dict):
        raise BadResponse("the answer was not a JSON object")
    if kind in ("chat", "vision"):
        choices = data.get("choices") or []
        if not choices:
            raise BadResponse(redact("no choices in the answer: %s" % _canonical(data)[:300]))
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
        if not str(content or "").strip():
            raise BadResponse("the first choice carried no text (finish_reason=%s)"
                              % (choices[0].get("finish_reason"),))
        return {"text": str(content), "usage": data.get("usage") or {}}
    if kind in ("image", "edit"):
        items = data.get("data") or []
        if not items:
            raise BadResponse("no image in the answer")
        first = items[0] or {}
        return {"image_b64": first.get("b64_json"),
                "url": first.get("url"),
                "format": data.get("output_format") or "png",
                "revised_prompt": first.get("revised_prompt"),
                "usage": data.get("usage") or {}}
    if kind == "segment":
        text = segmentation_text(data)
        boxes, masks = parse_segmentation(text, data)
        return {"text": text, "boxes": boxes, "masks": masks, "note": SAM_PARSE_NOTE}
    raise NotConfigured("cannot normalise kind %r" % kind)


# ---------------------------------------------------------------- segmentation parsing

def segmentation_text(data):
    """The output_text lane of a Responses body, flattened to a string."""
    if not isinstance(data, dict):
        return ""
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    chunks = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if not isinstance(part, dict):
                continue
            if isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "".join(chunks)


def parse_segmentation(text, data=None):
    """(boxes, masks) from a SAM answer. Tolerant, and empty rather than guessed.

    The docs say the answer is special token text with, per object, a box in source pixels and
    a one bit mask raster, and we do not hold the token grammar. So this reads the shapes it
    can recognise: any box a server chooses to send as JSON in the body, then four integers
    that follow a box marker in the text. Anything else yields [] and the caller keeps the raw
    text. Zero objects is a documented valid outcome, so [] is not an error.
    """
    boxes = []
    masks = []
    if isinstance(data, dict):
        for key in ("boxes", "detections", "objects"):
            found = data.get(key)
            if isinstance(found, list):
                for item in found:
                    if isinstance(item, dict) and isinstance(item.get("box"), list):
                        boxes.append([int(v) for v in item["box"][:4]])
                    elif isinstance(item, (list, tuple)) and len(item) >= 4:
                        boxes.append([int(v) for v in item[:4]])
        for key in ("masks", "mask"):
            found = data.get(key)
            if isinstance(found, list):
                masks.extend(found)
            elif isinstance(found, str):
                masks.append(found)
    body = str(text or "")
    if body:
        for match in re.finditer(r"(?i)(?:box|bbox)[^\d\n]{0,24}?(-?\d+)\s*[, ]\s*(-?\d+)\s*[, ]"
                                 r"\s*(-?\d+)\s*[, ]\s*(-?\d+)", body):
            box = [int(match.group(i)) for i in range(1, 5)]
            if box not in boxes:
                boxes.append(box)
        # A special token lane carries the mask as its own labelled payload; keep the payload
        # verbatim and labelled by kind, never decoded into pixels we cannot verify.
        for match in re.finditer(r"(?i)<\|?\s*mask(?:_?rle|_?bits)?\s*\|?>([^<\n]{4,})", body):
            masks.append(match.group(1).strip()[:4000])
    return boxes, masks


# ---------------------------------------------------------------- public API

def _finish(kind, model, response, cached, backend, chosen_mode, **extra):
    out = {"kind": kind, "model": model, "backend": backend, "mode": chosen_mode,
           "cached": bool(cached)}
    out.update(response)
    out.update(extra)
    return out


def chat(messages, model=None, json_schema=None, sleep=None, transport=None):
    """A chat completion. Returns the text, or the JSON string when a schema was asked for.

    `transport` is an optional dict this call fills with what the door actually did: `backend`,
    `mode`, `cached` and `network`, exactly the values `_dispatch()` computed. A caller that has to
    report where an answer came from (R43 B1: the bake header) reads it here instead of reading the
    environment and guessing what happened.
    """
    model = model or model_for("chat")
    turns = normalise_messages(messages)
    payload = {"model": model, "messages": turns}
    if json_schema:
        payload["response_format"] = {"type": "json_schema",
                                      "json_schema": {"name": "answer", "strict": True,
                                                      "schema": json_schema}}
    response, cached, backend, chosen_mode = _dispatch("chat", model, payload,
                                                       schema=json_schema, sleep=sleep)
    if transport is not None:
        transport.update(transport_verdict(backend, chosen_mode, cached))
    return response["text"]


def transport_verdict(backend, chosen_mode, cached):
    """What one dispatched call did, as the four fields a reporting caller needs."""
    return {"backend": backend, "mode": chosen_mode, "cached": bool(cached),
            "network": network_used(backend, chosen_mode, cached)}


def network_used(backend, chosen_mode, cached=False):
    """True only when this call's answer came over the wire now, not from the cache and not from mock."""
    if cached:
        return False
    if backend == "gemini":
        return chosen_mode == "live"
    return backend == "meta" and chosen_mode in ("live", "record")


def chat_structured(messages, schema, model=None, sleep=None, transport=None):
    """chat() with a schema, parsed. Raises BadResponse when the answer is not a JSON object."""
    text = chat(messages, model=model, json_schema=schema, sleep=sleep, transport=transport)
    return parse_json(text)


def vision(prompt, image_path, model=None, sleep=None):
    """One image plus one question. Returns the text. vision(prompt, image_path) as specced."""
    if not prompt or not str(prompt).strip():
        raise ValueError("vision() needs a prompt")
    model = model or model_for("vision")
    mime, b64_text, digest = _read_image(image_path)
    content = [{"type": "text", "text": str(prompt)},
               {"type": "image_url", "image_url": {"url": _data_url(mime, b64_text)}}]
    payload = {"model": model, "messages": [{"role": "user", "content": content}]}
    echo = {"model": model, "image_sha256": digest, "image_bytes": os.path.getsize(image_path),
            "prompt": str(prompt)}
    response, cached, backend, chosen_mode = _dispatch("vision", model, payload,
                                                       request_echo=echo, sleep=sleep)
    return response["text"]


def _image_result(kind, prompt, size, data, model, cached, backend, chosen_mode, out_path):
    b64_text = data.get("image_b64")
    url = data.get("url")
    path = None
    if out_path:
        if not b64_text:
            raise BadResponse("the answer carried a URL and no bytes, so %s was not written"
                              % out_path)
        parent = os.path.dirname(os.path.abspath(out_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        with open(out_path, "wb") as handle:
            handle.write(base64.b64decode(b64_text))
        path = os.path.abspath(out_path)
    return _finish(kind, model, data, cached, backend, chosen_mode, prompt=str(prompt),
                   size=size, image_b64=b64_text, url=url, path=path)


def generate_image(prompt, size="1024x1024", model=None, out_path=None, sleep=None):
    """Muse Image generation. size sets an aspect ratio on the real API, not exact pixels."""
    if not prompt or not str(prompt).strip():
        raise ValueError("generate_image() needs a prompt")
    model = model or model_for("image")
    parse_size(size)
    payload = {"model": model, "prompt": str(prompt), "size": size, "n": 1,
               "output_format": "png"}
    response, cached, backend, chosen_mode = _dispatch("image", model, payload, sleep=sleep)
    return _image_result("image", prompt, size, response, model, cached, backend,
                         chosen_mode, out_path)


def edit_image(image_path, prompt, size="1024x1024", model=None, out_path=None, sleep=None,
               extra_images=None):
    """Muse Image edit of one or more source images, inline as data URLs (shape UNVERIFIED)."""
    if not prompt or not str(prompt).strip():
        raise ValueError("edit_image() needs a prompt")
    model = model or model_for("edit")
    parse_size(size)
    sources = [image_path] + list(extra_images or [])
    images = []
    digests = []
    for source in sources:
        mime, b64_text, digest = _read_image(source)
        images.append({"image_url": _data_url(mime, b64_text)})
        digests.append(digest)
    payload = {"model": model, "prompt": str(prompt), "size": size, "n": 1,
               "output_format": "png", "images": images}
    echo = {"model": model, "prompt": str(prompt), "size": size, "image_sha256": digests}
    response, cached, backend, chosen_mode = _dispatch("edit", model, payload,
                                                       request_echo=echo, sleep=sleep)
    return _image_result("edit", prompt, size, response, model, cached, backend,
                         chosen_mode, out_path)


def segment(image_path, prompt, model=None, sleep=None):
    """SAM 3.1 for one noun phrase in one image. Returns {text, boxes, masks, ...}."""
    if not prompt or not str(prompt).strip():
        raise ValueError("segment() needs one noun phrase, e.g. 'knight'")
    model = model or model_for("segment")
    mime, b64_text, digest = _read_image(image_path)
    content = [{"type": "input_text", "text": str(prompt)},
               {"type": "input_image", "image_url": _data_url(mime, b64_text)}]
    payload = {"model": model,
               "input": [{"role": "user", "content": content}],
               "metadata": {"mask_encoding": "one_bit"}}
    echo = {"model": model, "prompt": str(prompt), "image_sha256": digest,
            "image_bytes": os.path.getsize(image_path), "mask_encoding": "one_bit"}
    response, cached, backend, chosen_mode = _dispatch("segment", model, payload,
                                                       request_echo=echo, sleep=sleep)
    return _finish("segment", model, response, cached, backend, chosen_mode,
                   prompt=str(prompt), image_path=str(image_path))


# ---------------------------------------------------------------- critics adapter

def gemini_compat_generate(model, payload, timeout=None, sleep=None):
    """A Gemini generateContent payload in, a Gemini generateContent body out.

    tools\\ear_critic.py and tools\\eye_critic.py already build {contents:[{role, parts:[...]}]}
    and already read {candidates:[{content:{parts:[{text}]}}]}. This translates that payload
    to a chat completion, sends it through this client (cache, rate gate, retries), and
    translates the answer back, so both critics can run on Meta by setting PP_AI_BACKEND=meta
    without touching their rubric, their ledger or their parsing.

    UNVERIFIED: inline audio (the ear critic sends MP3 chunks) travels as an image_url data
    URL with an audio mime type, because the OpenAI-compatible part type for audio is not
    documented. Vision (the eye critic) uses the documented image_url part.
    """
    global SLEEP
    if not isinstance(payload, dict):
        raise ValueError("gemini_compat_generate() needs the critic's payload dict")
    contents = payload.get("contents") or []
    messages = []
    image_count = 0
    for item in contents:
        if not isinstance(item, dict):
            continue
        role = "assistant" if str(item.get("role")) == "model" else "user"
        parts_out = []
        for part in item.get("parts") or []:
            if not isinstance(part, dict):
                continue
            if isinstance(part.get("text"), str):
                parts_out.append({"type": "text", "text": part["text"]})
            inline = part.get("inline_data") or part.get("inlineData")
            if isinstance(inline, dict) and inline.get("data"):
                mime = inline.get("mime_type") or inline.get("mimeType") or "image/png"
                parts_out.append({"type": "image_url",
                                  "image_url": {"url": _data_url(mime, inline["data"])}})
                image_count += 1
        if not parts_out:
            continue
        if all(p["type"] == "text" for p in parts_out):
            messages.append({"role": role,
                             "content": "\n".join(p["text"] for p in parts_out)})
        else:
            messages.append({"role": role, "content": parts_out})
    if not messages:
        raise ValueError("the critic payload carried no text or image parts")

    chat_payload = {"model": model, "messages": messages}
    schema = None
    response, cached, backend, chosen_mode = _dispatch(
        "vision" if image_count else "chat", model, chat_payload,
        request_echo={"model": model, "messages": _shrink(messages)}, sleep=sleep)
    text = response.get("text", "")
    usage = response.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("promptTokenCount") or 0)
    output_tokens = int(usage.get("completion_tokens") or usage.get("candidatesTokenCount") or 0)
    body = {
        "candidates": [{"content": {"parts": [{"text": text}], "role": "model"},
                        "finishReason": "STOP", "index": 0}],
        "usageMetadata": {"promptTokenCount": prompt_tokens,
                          "candidatesTokenCount": output_tokens,
                          "totalTokenCount": prompt_tokens + output_tokens},
        "modelVersion": model,
        "ppMeta": {"backend": backend, "mode": chosen_mode, "cached": bool(cached),
                   "audio_audio_part_unverified": True},
    }
    return body


# ---------------------------------------------------------------- dry run and CLI

def describe(role="chat"):
    backend = backend_name()
    return {
        "backend": backend,
        "mode": mode(),
        "base_url": base_url(),
        "key_env": " then ".join(KEY_ENVS),
        "key_present": key_present(),
        "model": model_for(role),
        "models": {name: model_for(name) for name in DEFAULT_MODELS},
        "cache_dir": cache_dir(),
        "cache_entries": len(cache_entries()),
        "rpm": {name: rpm_for(model_for(name)) for name in DEFAULT_MODELS},
        "capabilities": {
            "meta": ["chat", "vision", "image", "edit", "segment"],
            "gemini": ["chat", "vision"],
            "mock": ["chat", "vision", "image", "edit", "segment"],
        }.get(backend, []),
    }


def cache_status():
    entries = cache_entries()
    kinds = {}
    models = set()
    network = 0
    backends = {}
    for entry in entries:
        kinds[entry.get("kind")] = kinds.get(entry.get("kind"), 0) + 1
        if entry.get("model"):
            models.add(entry["model"])
        backends[entry.get("backend")] = backends.get(entry.get("backend"), 0) + 1
        if entry.get("network"):
            network += 1
    return {"cache_dir": cache_dir(), "entries": len(entries), "kinds": kinds,
            "backends": backends, "models": sorted(models),
            "recorded_against_live_api": network,
            "replayable_offline": len(entries)}


DEMO_PROMPTS = (
    "TALK verdict for Zeus: 'I did not come to fight, I came to be remembered.'",
    "a flat 16 colour knight in profile on a plain background",
    "knight",
)


def record_demo(out_dir=None, sleep=None):
    """Record one call of each kind so the demo can replay with the network off."""
    out_dir = out_dir or os.path.join(ROOT, "output", "meta_demo")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    schema = {"type": "object",
              "properties": {"mercy_delta": {"type": "integer"},
                             "refusal": {"type": "boolean"},
                             "line": {"type": "string"}},
              "required": ["mercy_delta", "refusal", "line"]}
    done = []
    plain = chat([{"role": "user", "content": DEMO_PROMPTS[0]}], sleep=sleep)
    done.append(("chat", plain[:80]))
    verdict = chat_structured([{"role": "user", "content": DEMO_PROMPTS[0]}], schema=schema,
                              sleep=sleep)
    done.append(("chat+json_schema", verdict))
    made = generate_image(DEMO_PROMPTS[1], size="512x512",
                          out_path=os.path.join(out_dir, "concept.png"), sleep=sleep)
    done.append(("image", made.get("path") or made.get("url")))
    note = vision("Score this concept for NES palette limits.", made["path"], sleep=sleep)
    done.append(("vision", note[:80]))
    cut = segment(made["path"], DEMO_PROMPTS[2], sleep=sleep)
    done.append(("segment", "%d box(es)" % len(cut.get("boxes") or [])))
    edited = edit_image(made["path"], "the same knight, front view", size="512x512",
                        out_path=os.path.join(out_dir, "concept_edit.png"), sleep=sleep)
    done.append(("edit", edited.get("path") or edited.get("url")))
    return done


def dry_run(as_json=False, role="chat"):
    info = describe(role)
    if as_json:
        print(json.dumps(info, indent=2, sort_keys=True))
        return 0
    print("backend: %s (PP_AI_BACKEND)" % info["backend"])
    print("mode: %s (PP_AI_MODE)" % info["mode"])
    print("base: %s" % info["base_url"])
    print("model: %s (role %s)" % (info["model"], role))
    print("key: %s" % ("present in the environment (value never printed)" if info["key_present"]
                       else "MISSING (%s); offline work still runs with mock or replay"
                       % info["key_env"]))
    print("cache: %s (%d entr(y/ies))" % (info["cache_dir"], info["cache_entries"]))
    print("capabilities: %s" % ", ".join(info["capabilities"]))
    print("dry run: nothing was sent")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="One client for chat, vision, image, edit and "
                                                 "segmentation (card META-CLIENT).")
    parser.add_argument("--dry-run", action="store_true",
                        help="print backend, mode, key state and cache, then stop")
    parser.add_argument("--cache-status", action="store_true",
                        help="what the recorded cache holds, and how much of it is real")
    parser.add_argument("--record-demo", action="store_true",
                        help="record one call of each kind so the demo replays offline")
    parser.add_argument("--role", default="chat", help="model role to report (default chat)")
    parser.add_argument("--json", action="store_true", help="machine readable output")
    args = parser.parse_args(argv)
    if args.dry_run:
        return dry_run(as_json=args.json, role=args.role)
    if args.cache_status:
        status = cache_status()
        print(json.dumps(status, indent=2, sort_keys=True) if args.json else
              "cache %s: %d entr(y/ies), recorded against the live API: %d"
              % (status["cache_dir"], status["entries"], status["recorded_against_live_api"]))
        return 0
    if args.record_demo:
        for label, value in record_demo():
            print("%-16s %s" % (label, value))
        print("cache: %s (%d entries)" % (cache_dir(), len(cache_entries())))
        return 0
    parser.print_help()
    print("\nnothing was called: pass --dry-run, --cache-status or --record-demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
