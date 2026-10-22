"""One model client for the Primordial Paradox tooling, plus a cost ledger (card AI-CLIENT).

Every tool that wants a model (art critics, sprite briefs, the battle TALK judge) goes
through this module, so that the backend, the model name and the money all live in one
place instead of being copied into six scripts.

Public API
    chat(messages, model_role="chat")      -> str
    vision(image_path, prompt, ...)        -> str
    image(prompt, size="1024x1024")        -> dict
    segment(image_path, points=..., box=...) -> dict
    get_backend(name=None)                 -> a Backend object

Backends, selected by the environment only
    PP_AI_BACKEND        gemini (default) | azure | meta | mock
    gemini               GEMINI_API_KEY, PP_GEMINI_MODEL, PP_GEMINI_MODEL_<ROLE>
    azure                AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION,
                         AZURE_OPENAI_DEPLOYMENT_CHAT, AZURE_OPENAI_DEPLOYMENT_IMAGE
    meta                 META_API_BASE, META_API_KEY
    mock                 no key, no network, used by tests and by --dry-run demos

WHAT IS REAL AND WHAT IS NOT, as of 2026-10-21
    gemini   real: chat() and vision() against the Gemini REST API (generateContent).
             image() and segment() raise NotConfigured: no image model is wired yet.
    azure    stub, raises NotConfigured. Azure is shelved (zero quota, no credits), so the
             REST call is documented below but deliberately not implemented.
    meta     stub, raises NotConfigured. The Meta Model API docs (Muse Spark, Muse Image,
             SAM 3.1) arrive with the hackathon rules on Oct 26; writing an untested
             HTTP client against guessed shapes would be fiction.
    mock     real: all four calls, deterministic, no network.

Keys
    A key is read from os.environ at call time, put in a request header, and nowhere
    else. It is never printed, logged, written to the ledger or included in an exception
    message: every error string goes through redact() first, and the ledger row carries
    no header, URL or key material. Files whose name looks like a credential store
    (.env, auth.json, anything with token/secret/credential in the name) are refused as
    vision() input rather than opened.

Ledger
    data\\ai_ledger.csv, append only, header written once. One row per call, including
    refused and failed calls, so "how many calls did this lane make and what did they
    cost" is answerable from the file alone. Columns are LEDGER_COLUMNS. The estimated
    cost is the paid list price from PRICE_TABLE (see the note there): on the free tier
    the actual spend is zero, so cost_basis says which basis the number uses instead of
    pretending to a precise bill.

Rate limits
    The Gemini free tier answers 429 (RESOURCE_EXHAUSTED) under bursts. A 429 is retried
    with the delay the API asks for (RetryInfo.retryDelay) or 2, 4, 8 s, up to
    PP_AI_MAX_RETRIES (default 2). Each row records minute_count, the number of calls
    this ledger saw in the same UTC minute, so a burst is visible in the CSV afterwards.

Sources checked 2026-10-21
    models      https://ai.google.dev/gemini-api/docs/models          (page updated 2026-10-09)
    pricing     https://ai.google.dev/gemini-api/docs/pricing
    request     https://ai.google.dev/api/generate-content

Usage
    python tools\\ai_client.py --dry-run
    python tools\\ai_client.py --dry-run --role vision --json
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_LEDGER = os.path.join(ROOT, "data", "ai_ledger.csv")

GEMINI_BASE = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_TIMEOUT = 120

LEDGER_COLUMNS = [
    "time_utc",        # YYYY-MM-DDTHH:MM:SSZ, when the call finished
    "backend",         # gemini | azure | meta | mock
    "model",           # model or deployment name actually asked for
    "role",            # chat | vision | image | segment, or a caller's own role name
    "status",          # ok | not_configured | error | rate_limited | bad_response
    "prompt_tokens",   # from usageMetadata when the API reports it, else an estimate
    "output_tokens",
    "images",          # number of images sent or asked for
    "minute_count",    # calls in the same UTC minute as this row, this row included
    "estimated_cost_usd",
    "cost_basis",      # paid_list_price | unknown_price_model | not_applicable
    "tokens_source",   # api | estimate | none
    "latency_ms",
    "note",            # short, redacted, never a key, header or full prompt
]

# Paid list price per 1M tokens, USD, read from https://ai.google.dev/gemini-api/docs/pricing
# on 2026-10-21. The free tier is free of charge for the two Flash models below, which is why
# the ledger records the basis next to the number: 0.00 in the ledger would mean "free", and
# this table answers "what would this have cost on the paid tier". Prices carry an end date
# in the source ("through December 31, 2026"); re-read the page before trusting this table
# after that date. A model that is not in the table is logged with cost 0.0 and
# cost_basis=unknown_price_model, so a missing price can never look like a measured one.
PRICE_TABLE = {
    "gemini-3.8-flash": {"input_per_1m": 0.75, "output_per_1m": 3.75, "free_tier": True},
    "gemini-3.6-flash": {"input_per_1m": 0.75, "output_per_1m": 3.75, "free_tier": True},
}
PRICE_CHECKED = "2026-10-21"
PRICE_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"

# Gemini bills an image up to 384 px as 258 tokens. Used only when the response carries no
# usageMetadata; the row then says tokens_source=estimate.
IMAGE_TOKEN_ESTIMATE = 258

CHARS_PER_TOKEN = 4.0
_CREDENTIAL_NAMES = ("token", "secret", "credential", "password", "apikey", "api_key", "key",
                     "auth.json", ".env", ".pem")


class AIError(RuntimeError):
    """A model call failed. The message is already redacted."""


class NotConfigured(AIError):
    """The backend or the capability is not wired up, so no request was made."""


class RateLimited(AIError):
    """The API kept answering 429 after the retry budget was spent."""


# ---------------------------------------------------------------- keys and redaction

def redact(text):
    """Strip anything that looks like a key out of a string bound for a log or an exception."""
    if text is None:
        return ""
    out = str(text)
    for name in ("GEMINI_API_KEY", "AZURE_OPENAI_API_KEY", "META_API_KEY"):
        value = os.environ.get(name)
        if value and len(value) >= 8:
            out = out.replace(value, "[REDACTED]")
    out = re.sub(r"(?i)(api[_-]?key|key|token|authorization)(=|\s*:\s*)[^\s&\"',}]+",
                 r"\1\2[REDACTED]", out)
    return out


def _refuse_credential_path(path):
    """vision() must never open a file that holds keys; check the name before reading it."""
    lowered = os.path.basename(str(path)).lower()
    if any(marker in lowered for marker in _CREDENTIAL_NAMES):
        raise ValueError("refusing to read %r as an image: the name looks like a credential file"
                         % os.path.basename(str(path)))


def _env_int(name, default):
    try:
        return int(os.environ.get(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- ledger

def ledger_path():
    return os.environ.get("PP_AI_LEDGER") or DEFAULT_LEDGER


def _utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _minute_of(stamp):
    return stamp[:16]


def ledger_rows(path=None):
    """Read the ledger back as dicts. Missing file means no rows, not an error."""
    path = path or ledger_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _minute_count(path, minute):
    return sum(1 for row in ledger_rows(path) if str(row.get("time_utc", "")).startswith(minute))


def append_row(row, path=None):
    """Append one row. Header is written when the file is created, and only then."""
    path = path or ledger_path()
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    clean = {name: row.get(name, "") for name in LEDGER_COLUMNS}
    clean["note"] = redact(clean.get("note", ""))[:200]
    with open(path, "a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(clean)
    return clean


def estimate_cost(model, prompt_tokens, output_tokens):
    """(usd, basis) for a call. Never invent a price for a model that is not in the table."""
    price = PRICE_TABLE.get(model)
    if not price:
        return 0.0, "unknown_price_model"
    usd = (max(0, prompt_tokens) / 1e6) * price["input_per_1m"]
    usd += (max(0, output_tokens) / 1e6) * price["output_per_1m"]
    return round(usd, 8), "paid_list_price"


def _record(backend, model, role, status, prompt_tokens=0, output_tokens=0, images=0,
            tokens_source="none", latency_ms=0, note="", path=None):
    path = path or ledger_path()
    stamp = _utc_stamp()
    cost, basis = estimate_cost(model, prompt_tokens, output_tokens) \
        if tokens_source != "none" else (0.0, "not_applicable")
    return append_row({
        "time_utc": stamp,
        "backend": backend,
        "model": model,
        "role": role,
        "status": status,
        "prompt_tokens": int(prompt_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "images": int(images or 0),
        "minute_count": _minute_count(path, _minute_of(stamp)) + 1,
        "estimated_cost_usd": "%.8f" % cost,
        "cost_basis": basis,
        "tokens_source": tokens_source,
        "latency_ms": int(latency_ms or 0),
        "note": note,
    }, path=path)


# ---------------------------------------------------------------- message shapes

def normalise_messages(messages):
    """Accept a bare string, a list of strings, or a list of {role, content} dicts."""
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


def _estimate_tokens(text):
    return max(1, int(len(str(text)) / CHARS_PER_TOKEN) + 1)


# ---------------------------------------------------------------- backends

class Backend(object):
    """Common shape. Every backend answers the same four calls."""

    name = "base"

    def model_for(self, role):
        raise NotImplementedError

    def chat(self, messages, role="chat"):
        raise NotImplementedError

    def vision(self, image_path, prompt, role="vision"):
        raise NotImplementedError

    def image(self, prompt, size="1024x1024"):
        raise NotImplementedError

    def segment(self, image_path, points=None, box=None):
        raise NotImplementedError

    def describe(self):
        return {"backend": self.name, "capabilities": []}


class GeminiBackend(Backend):
    """Gemini Developer API, REST generateContent. No SDK: one POST, one key header."""

    name = "gemini"
    key_env = "GEMINI_API_KEY"

    def model_for(self, role):
        role_env = "PP_GEMINI_MODEL_%s" % str(role or "chat").upper().replace("-", "_")
        return (os.environ.get(role_env, "").strip()
                or os.environ.get("PP_GEMINI_MODEL", "").strip()
                or DEFAULT_GEMINI_MODEL)

    def _key(self):
        key = os.environ.get(self.key_env, "").strip()
        if not key:
            raise NotConfigured("%s is not set in the environment" % self.key_env)
        return key

    def endpoint(self, model):
        return "%s/models/%s:generateContent" % (GEMINI_BASE.rstrip("/"), model)

    def _post(self, model, payload):
        """POST, with the retry policy for 429 and 5xx. Returns the decoded JSON body."""
        key = self._key()
        body = json.dumps(payload).encode("utf-8")
        url = self.endpoint(model)
        attempt = 0
        max_retries = _env_int("PP_AI_MAX_RETRIES", 2)
        base_delay = float(os.environ.get("PP_AI_RETRY_BASE", "2") or 2)
        cap = float(os.environ.get("PP_AI_MAX_BACKOFF", "60") or 60)
        timeout = _env_int("PP_AI_TIMEOUT", DEFAULT_TIMEOUT)
        last = None
        while True:
            request = urllib.request.Request(url, data=body, method="POST")
            request.add_header("Content-Type", "application/json")
            request.add_header("x-goog-api-key", key)  # the key never enters the URL
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8")), attempt
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:400]
                except Exception:  # noqa: BLE001 - a body that cannot be read is not an error
                    detail = ""
                last = (exc.code, detail)
                if exc.code not in (429, 500, 502, 503, 504) or attempt >= max_retries:
                    break
                delay = _retry_delay(detail, attempt, base_delay, cap)
                time.sleep(delay)
                attempt += 1
            except urllib.error.URLError as exc:
                last = (0, str(exc.reason))
                if attempt >= max_retries:
                    break
                time.sleep(min(base_delay * (2 ** attempt), cap))
                attempt += 1
        code, detail = last or (0, "no attempt made")
        if code == 429:
            raise RateLimited(redact("gemini answered 429 after %d attempt(s): %s"
                                     % (attempt + 1, detail)))
        raise AIError(redact("gemini answered %s: %s" % (code or "no response", detail)))

    def _generate(self, model, parts, role, images=0, prompt_chars=0):
        payload = {"contents": [{"role": "user", "parts": parts}]}
        started = time.time()
        data, retries = self._post(model, payload)
        latency = int((time.time() - started) * 1000)
        text, usage = _read_gemini_response(data)
        if usage:
            prompt_tokens = int(usage.get("promptTokenCount") or 0)
            output_tokens = int(usage.get("candidatesTokenCount") or 0)
            source = "api"
        else:
            prompt_tokens = int(prompt_chars / CHARS_PER_TOKEN) + 1 + images * IMAGE_TOKEN_ESTIMATE
            output_tokens = _estimate_tokens(text)
            source = "estimate"
        note = "retries=%d" % retries
        _record(self.name, model, role, "ok", prompt_tokens, output_tokens, images, source,
                latency, note)
        return text

    def chat(self, messages, role="chat"):
        model = self.model_for(role)
        parts = [{"text": m["content"]} for m in normalise_messages(messages)]
        prompt_chars = sum(len(p["text"]) for p in parts)
        try:
            return self._generate(model, parts, role, 0, prompt_chars)
        except NotConfigured:
            raise
        except (RateLimited, AIError) as exc:
            _fail_record(self.name, model, role, exc)
            raise

    def vision(self, image_path, prompt, role="vision"):
        model = self.model_for(role)
        _refuse_credential_path(image_path)
        data = _read_image(image_path)
        parts = [{"text": prompt}, {"inline_data": {"mime_type": data[0], "data": data[1]}}]
        try:
            return self._generate(model, parts, role, 1, len(prompt) + len(data[1]))
        except NotConfigured:
            raise
        except (RateLimited, AIError) as exc:
            _fail_record(self.name, model, role, exc)
            raise

    def image(self, prompt, size="1024x1024"):
        raise NotConfigured("gemini backend has no image generation here: /pricing lists image "
                            "models (gemini-3.1-flash-image and friends) but none is wired yet")

    def segment(self, image_path, points=None, box=None):
        raise NotConfigured("gemini backend has no segmentation here: SAM style segmentation is "
                            "the Meta lane, and Meta's docs arrive Oct 26")

    def describe(self):
        return {
            "backend": self.name,
            "key_env": self.key_env,
            "key_present": bool(os.environ.get(self.key_env, "").strip()),
            "model": self.model_for("chat"),
            "endpoint": self.endpoint("{model}"),
            "capabilities": ["chat", "vision"],
            "not_implemented": ["image", "segment"],
        }


class AzureStub(Backend):
    """Documented but not implemented: Azure is shelved (zero quota, no credits).

    When it comes back, the shape is POST
    {AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT_CHAT}/chat/completions
    ?api-version={AZURE_OPENAI_API_VERSION} with the api-key header, body {messages, model}
    in the OpenAI chat shape, and the deployment name rather than a model name in the URL.
    """

    name = "azure"

    def model_for(self, role):
        env = "AZURE_OPENAI_DEPLOYMENT_IMAGE" if role == "image" else "AZURE_OPENAI_DEPLOYMENT_CHAT"
        return os.environ.get(env, "").strip() or "(deployment not set)"

    def _refuse(self):
        raise NotConfigured("azure backend is a stub: Azure is shelved (zero quota, no credits, "
                            "manager 2026-10-21). Set PP_AI_BACKEND=gemini or mock")

    def chat(self, messages, role="chat"):
        self._refuse()

    def vision(self, image_path, prompt, role="vision"):
        self._refuse()

    def image(self, prompt, size="1024x1024"):
        self._refuse()

    def segment(self, image_path, points=None, box=None):
        self._refuse()

    def describe(self):
        return {"backend": self.name, "model": self.model_for("chat"), "capabilities": [],
                "not_implemented": ["chat", "vision", "image", "segment"]}


class MetaStub(Backend):
    """Documented but not implemented: the Meta Model API docs arrive with the rules on Oct 26."""

    name = "meta"

    def model_for(self, role):
        return os.environ.get("META_MODEL", "").strip() or "(model not set)"

    def _refuse(self):
        raise NotConfigured("meta backend is a stub: META_API_BASE and META_API_KEY are read but no "
                            "request shape is documented yet (rules arrive Oct 26)")

    def chat(self, messages, role="chat"):
        self._refuse()

    def vision(self, image_path, prompt, role="vision"):
        self._refuse()

    def image(self, prompt, size="1024x1024"):
        self._refuse()

    def segment(self, image_path, points=None, box=None):
        self._refuse()

    def describe(self):
        return {"backend": self.name, "model": self.model_for("chat"), "capabilities": [],
                "not_implemented": ["chat", "vision", "image", "segment"]}


class MockBackend(Backend):
    """Deterministic, offline, and the only backend the test suite is allowed to reach."""

    name = "mock"
    model_name = "mock-model-1"

    def model_for(self, role):
        return "mock-%s" % (role or "chat")

    def chat(self, messages, role="chat"):
        model = self.model_for(role)
        turns = normalise_messages(messages)
        last = turns[-1]["content"]
        text = "mock(%d turns, %d chars): %s" % (len(turns), len(last), last[:120])
        prompt_tokens = sum(_estimate_tokens(t["content"]) for t in turns)
        output_tokens = _estimate_tokens(text)
        _record(self.name, model, role, "ok", prompt_tokens, output_tokens, 0, "estimate", 0,
                "offline mock")
        return text

    def vision(self, image_path, prompt, role="vision"):
        model = self.model_for(role)
        _refuse_credential_path(image_path)
        size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
        text = "mock-vision(%d bytes, prompt %d chars): %s" % (size, len(prompt), prompt[:120])
        _record(self.name, model, role, "ok", _estimate_tokens(prompt) + IMAGE_TOKEN_ESTIMATE,
                _estimate_tokens(text), 1, "estimate", 0, "offline mock")
        return text

    def image(self, prompt, size="1024x1024"):
        model = self.model_for("image")
        _record(self.name, model, "image", "ok", _estimate_tokens(prompt), 0, 1, "estimate", 0,
                "offline mock, no bytes written")
        return {"backend": self.name, "model": model, "prompt": prompt, "size": size,
                "image_bytes": 0, "mock": True}

    def segment(self, image_path, points=None, box=None):
        model = self.model_for("segment")
        if box is None and not points:
            raise ValueError("segment() needs points or a box")
        _record(self.name, model, "segment", "ok", 0, 0, 1, "estimate", 0, "offline mock")
        return {"backend": self.name, "model": model, "points": points, "box": box,
                "masks": 1, "mock": True}

    def describe(self):
        return {"backend": self.name, "model": self.model_for("chat"), "key_present": True,
                "capabilities": ["chat", "vision", "image", "segment"]}


BACKENDS = {"gemini": GeminiBackend, "azure": AzureStub, "meta": MetaStub, "mock": MockBackend}


# ---------------------------------------------------------------- helpers

def _read_image(path):
    """(mime_type, base64_text) for an image path. Refuses credential-looking names first."""
    _refuse_credential_path(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    with open(path, "rb") as handle:
        raw = handle.read()
    return mime, base64.b64encode(raw).decode("ascii")


def _retry_delay(detail, attempt, base_delay, cap):
    """Honour RetryInfo.retryDelay (a string like "17s") when it is in the 429 body."""
    match = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', detail or "")
    if match:
        return min(float(match.group(1)), cap)
    return min(base_delay * (2 ** attempt), cap)


def _read_gemini_response(data):
    """(text, usage) from a generateContent body; raises AIError on a blocked or empty answer."""
    if not isinstance(data, dict):
        raise AIError("gemini returned a body that is not an object")
    usage = data.get("usageMetadata") or {}
    candidates = data.get("candidates") or []
    if not candidates:
        feedback = (data.get("promptFeedback") or {}).get("blockReason")
        raise AIError(redact("gemini returned no candidates (blockReason=%s)" % (feedback or "none")))
    candidate = candidates[0]
    parts = ((candidate.get("content") or {}).get("parts") or [])
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        reason = candidate.get("finishReason") or "unknown"
        raise AIError(redact("gemini returned no text (finishReason=%s)" % reason))
    return text, usage


def _fail_record(backend, model, role, exc):
    status = "rate_limited" if isinstance(exc, RateLimited) else "error"
    _record(backend, model, role, status, note=str(exc)[:160])


def backend_name():
    return (os.environ.get("PP_AI_BACKEND", "").strip().lower() or "gemini")


def get_backend(name=None):
    chosen = (name or backend_name()).lower()
    if chosen not in BACKENDS:
        raise NotConfigured("unknown PP_AI_BACKEND %r (known: %s)"
                            % (chosen, ", ".join(sorted(BACKENDS))))
    return BACKENDS[chosen]()


# ---------------------------------------------------------------- public API

def chat(messages, model_role="chat", backend=None):
    return get_backend(backend).chat(messages, role=model_role)


def vision(image_path, prompt, model_role="vision", backend=None):
    return get_backend(backend).vision(image_path, prompt, role=model_role)


def image(prompt, size="1024x1024", backend=None):
    return get_backend(backend).image(prompt, size=size)


def segment(image_path, points=None, box=None, backend=None):
    return get_backend(backend).segment(image_path, points=points, box=box)


# ---------------------------------------------------------------- dry run CLI

def dry_run(as_json=False, role="chat"):
    """Say which backend and model a call would use, and stop. Sends nothing, writes nothing."""
    chosen = backend_name()
    if chosen not in BACKENDS:
        payload = {"backend": chosen, "error": "unknown PP_AI_BACKEND",
                   "known": sorted(BACKENDS), "sent": False}
        print(json.dumps(payload, indent=2) if as_json else
              "backend: %s (UNKNOWN; known: %s)" % (chosen, ", ".join(sorted(BACKENDS))))
        return 2
    found = BACKENDS[chosen]().describe()
    path = ledger_path()
    rows = ledger_rows(path)
    now_minute = _minute_of(_utc_stamp())
    payload = {
        "backend": chosen,
        "model_for_role": get_backend(chosen).model_for(role),
        "role": role,
        "key_env": found.get("key_env"),
        "key_present": found.get("key_present"),
        "endpoint": found.get("endpoint"),
        "capabilities": found.get("capabilities", []),
        "not_implemented": found.get("not_implemented", []),
        "ledger": path,
        "ledger_rows": len(rows),
        "ledger_rows_this_minute": sum(1 for r in rows
                                       if str(r.get("time_utc", "")).startswith(now_minute)),
        "price_table_checked": PRICE_CHECKED,
        "price_source": PRICE_SOURCE,
        "sent": False,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
        return 0
    print("backend: %s (from PP_AI_BACKEND)" % chosen)
    print("model: %s (role %s)" % (payload["model_for_role"], role))
    if payload["key_env"]:
        print("key: %s" % ("present in %s (value not printed)" % payload["key_env"]
                           if payload["key_present"] else "MISSING (%s is not set)" % payload["key_env"]))
    else:
        print("key: none needed")
    if payload["endpoint"]:
        print("endpoint: %s" % payload["endpoint"])
    print("capabilities: %s" % ", ".join(payload["capabilities"]))
    if payload["not_implemented"]:
        print("raises NotConfigured: %s" % ", ".join(payload["not_implemented"]))
    print("ledger: %s (%d rows, %d in this minute)"
          % (path, payload["ledger_rows"], payload["ledger_rows_this_minute"]))
    print("prices: checked %s against %s" % (PRICE_CHECKED, PRICE_SOURCE))
    print("dry run: no request sent, no ledger row written")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="One model client plus a cost ledger (AI-CLIENT).")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the backend, model and key state, then stop")
    parser.add_argument("--role", default="chat", help="model role to report (default chat)")
    parser.add_argument("--json", action="store_true", help="machine readable dry run")
    args = parser.parse_args(argv)
    if args.dry_run:
        return dry_run(as_json=args.json, role=args.role)
    parser.print_help()
    print("\nnothing was called: pass --dry-run, or import the module and call chat()/vision()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
