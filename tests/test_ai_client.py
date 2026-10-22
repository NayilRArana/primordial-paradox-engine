"""Tests for tools/ai_client.py (card AI-CLIENT). No network: the mock backend, or a fake urlopen.

What is pinned here, because each one is a rule the card states:
  * the dry run prints the backend and the model and sends nothing,
  * a key is never printed, never written to the ledger, and never put in a URL,
  * every call, including a refused or failed one, leaves a ledger row,
  * the ledger says which basis the cost number uses, and an unpriced model never invents one,
  * 429 is retried the documented number of times and then reported as rate limited,
  * the azure, meta and gemini image/segment paths refuse with NotConfigured instead of guessing.
"""

from __future__ import annotations

import csv
import io
import json
import os
import socket
import subprocess
import sys
import urllib.error

import pytest

import ai_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENTINEL = "sentinel-key-do-not-print-0123456789abcdef"

ENV_VARS = ("PP_AI_BACKEND", "PP_GEMINI_MODEL", "PP_GEMINI_MODEL_CHAT", "PP_GEMINI_MODEL_VISION",
            "GEMINI_API_KEY", "AZURE_OPENAI_API_KEY", "META_API_KEY", "AZURE_OPENAI_ENDPOINT",
            "META_API_BASE", "PP_AI_MAX_RETRIES", "PP_AI_RETRY_BASE", "PP_AI_MAX_BACKOFF")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    """Every test starts without keys, without a backend override, and with a private ledger."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    ledger = tmp_path / "ai_ledger.csv"
    monkeypatch.setenv("PP_AI_LEDGER", str(ledger))
    return ledger


def rows(ledger):
    if not os.path.exists(str(ledger)):
        return []
    with open(str(ledger), "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ledger_text(ledger):
    if not os.path.exists(str(ledger)):
        return ""
    with open(str(ledger), "r", encoding="utf-8", newline="") as handle:
        return handle.read()


class FakeResponse(object):
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8") if isinstance(payload, dict) else payload

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def gemini_ok(text="hello", prompt_tokens=12, output_tokens=34):
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": prompt_tokens,
                              "candidatesTokenCount": output_tokens}}


def http_error(code, body):
    return urllib.error.HTTPError("https://example.invalid/x", code, "err", None,
                                  io.BytesIO(body.encode("utf-8")))


# ---------------------------------------------------------------- dry run

def test_dry_run_reports_gemini_and_sends_nothing(clean_env):
    assert ai_client.main(["--dry-run"]) == 0
    text = ledger_text(clean_env)
    assert text == "", "a dry run must not write a ledger row"
    assert not os.path.exists(str(clean_env)), "a dry run must not create the ledger file"


def test_dry_run_prints_backend_and_key_state_but_not_the_key(capsys):
    os.environ["GEMINI_API_KEY"] = SENTINEL
    try:
        assert ai_client.main(["--dry-run"]) == 0
        out = capsys.readouterr().out
    finally:
        del os.environ["GEMINI_API_KEY"]
    assert "backend: gemini" in out
    assert ai_client.DEFAULT_GEMINI_MODEL in out
    assert "present in GEMINI_API_KEY" in out
    assert "value not printed" in out
    assert SENTINEL not in out, "the dry run printed the key"
    assert "no request sent" in out


def test_dry_run_says_missing_key_instead_of_failing(capsys):
    assert ai_client.main(["--dry-run", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "gemini"
    assert payload["key_present"] is False
    assert payload["sent"] is False
    assert payload["model_for_role"] == ai_client.DEFAULT_GEMINI_MODEL
    assert "chat" in payload["capabilities"] and "image" in payload["not_implemented"]
    assert payload["price_table_checked"] == ai_client.PRICE_CHECKED


def test_dry_run_exits_2_on_an_unknown_backend(monkeypatch):
    monkeypatch.setenv("PP_AI_BACKEND", "openai")
    assert ai_client.main(["--dry-run"]) == 2


def test_dry_run_role_picks_the_role_model(monkeypatch):
    monkeypatch.setenv("PP_AI_BACKEND", "mock")
    monkeypatch.setenv("PP_GEMINI_MODEL", "gemini-3.6-flash")
    # mock ignores gemini names on purpose; the role mapping is what is under test here
    assert ai_client.get_backend("mock").model_for("vision") == "mock-vision"


# ---------------------------------------------------------------- mock backend and ledger

def test_mock_chat_appends_one_row_with_the_documented_columns(clean_env):
    text = ai_client.chat([{"role": "user", "content": "describe the sprite"}], backend="mock")
    assert text.startswith("mock(1 turns")
    loaded = rows(clean_env)
    assert len(loaded) == 1
    row = loaded[0]
    assert list(row.keys()) == ai_client.LEDGER_COLUMNS
    assert row["backend"] == "mock"
    assert row["model"] == "mock-chat"
    assert row["role"] == "chat"
    assert row["status"] == "ok"
    assert int(row["prompt_tokens"]) > 0 and int(row["output_tokens"]) > 0
    assert row["images"] == "0"
    assert row["minute_count"] == "1"
    assert row["cost_basis"] == "unknown_price_model", "mock has no price, so no price is claimed"
    assert float(row["estimated_cost_usd"]) == 0.0
    assert row["time_utc"].endswith("Z") and len(row["time_utc"]) == 20


def test_second_call_in_the_same_minute_counts_up(clean_env):
    ai_client.chat("one", backend="mock")
    ai_client.chat("two", backend="mock")
    counts = [row["minute_count"] for row in rows(clean_env)]
    assert counts[1] == "2", "the per minute counter must see the earlier call"


def test_mock_vision_records_an_image_and_its_estimated_tokens(clean_env, tmp_path):
    picture = tmp_path / "sprite.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    text = ai_client.vision(str(picture), "what is wrong with this palette?", backend="mock")
    assert text.startswith("mock-vision(72 bytes")
    row = rows(clean_env)[0]
    assert row["images"] == "1"
    assert row["role"] == "vision"
    assert int(row["prompt_tokens"]) >= ai_client.IMAGE_TOKEN_ESTIMATE
    assert row["tokens_source"] == "estimate"


def test_mock_image_and_segment_answer(clean_env):
    made = ai_client.image("a title logo", size="512x512", backend="mock")
    assert made["mock"] is True and made["size"] == "512x512"
    cut = ai_client.segment("sprite.png", box=[0, 0, 16, 16], backend="mock")
    assert cut["box"] == [0, 0, 16, 16]
    assert [row["role"] for row in rows(clean_env)] == ["image", "segment"]


def test_segment_refuses_a_call_with_no_target(tmp_path):
    with pytest.raises(ValueError):
        ai_client.segment("sprite.png", backend="mock")


def test_ledger_header_is_written_once(clean_env):
    ai_client.chat("a", backend="mock")
    ai_client.chat("b", backend="mock")
    header_lines = [line for line in ledger_text(clean_env).splitlines()
                    if line.startswith("time_utc,")]
    assert len(header_lines) == 1


def test_mock_chat_makes_no_network_call(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("the mock backend opened a socket")

    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(socket, "create_connection", explode)
    assert ai_client.chat("offline please", backend="mock").startswith("mock(")


# ---------------------------------------------------------------- gemini wire format

def test_gemini_chat_puts_the_key_in_a_header_and_never_in_the_ledger(clean_env, monkeypatch):
    os.environ["GEMINI_API_KEY"] = SENTINEL
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["headers"] = {k.lower(): v for k, v in request.header_items()}
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(gemini_ok())

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", fake_urlopen)
    try:
        text = ai_client.chat([{"role": "user", "content": "hi"}], backend="gemini")
    finally:
        del os.environ["GEMINI_API_KEY"]

    assert text == "hello"
    assert seen["url"].endswith(":generateContent")
    assert ai_client.DEFAULT_GEMINI_MODEL in seen["url"]
    assert SENTINEL not in seen["url"], "the key must not travel in the URL"
    assert seen["headers"]["x-goog-api-key"] == SENTINEL
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "hi"

    text_ledger = ledger_text(clean_env)
    assert SENTINEL not in text_ledger, "the ledger must never hold a key"
    row = rows(clean_env)[0]
    assert row["backend"] == "gemini"
    assert row["model"] == ai_client.DEFAULT_GEMINI_MODEL
    assert row["status"] == "ok"
    assert row["prompt_tokens"] == "12" and row["output_tokens"] == "34"
    assert row["tokens_source"] == "api"
    assert row["cost_basis"] == "paid_list_price"
    # 12/1e6*0.75 + 34/1e6*3.75
    assert abs(float(row["estimated_cost_usd"]) - 0.00013650) < 1e-9


def test_gemini_vision_sends_the_image_inline(clean_env, monkeypatch, tmp_path):
    os.environ["GEMINI_API_KEY"] = SENTINEL
    picture = tmp_path / "art.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\n0123456789")
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(gemini_ok("the palette has four colours"))

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", fake_urlopen)
    try:
        text = ai_client.vision(str(picture), "count the colours", backend="gemini")
    finally:
        del os.environ["GEMINI_API_KEY"]

    parts = seen["body"]["contents"][0]["parts"]
    assert text == "the palette has four colours"
    assert parts[0]["text"] == "count the colours"
    assert parts[1]["inline_data"]["mime_type"] == "image/png"
    assert parts[1]["inline_data"]["data"], "the image bytes must be base64 at the wire"
    assert SENTINEL not in ledger_text(clean_env)
    assert rows(clean_env)[0]["images"] == "1"


def test_gemini_role_model_overrides_the_default(monkeypatch):
    monkeypatch.setenv("PP_GEMINI_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("PP_GEMINI_MODEL_VISION", "gemini-3.6-flash")
    backend = ai_client.get_backend("gemini")
    assert backend.model_for("chat") == "gemini-3.8-flash"
    assert backend.model_for("vision") == "gemini-3.6-flash"


# ---------------------------------------------------------------- failures

def test_missing_key_raises_not_configured_and_writes_no_ok_row(clean_env):
    with pytest.raises(ai_client.NotConfigured) as caught:
        ai_client.chat("hi", backend="gemini")
    assert "GEMINI_API_KEY" in str(caught.value)
    assert rows(clean_env) == []


def test_429_is_retried_then_succeeds(clean_env, monkeypatch):
    os.environ["GEMINI_API_KEY"] = SENTINEL
    monkeypatch.setenv("PP_AI_RETRY_BASE", "0")
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise http_error(429, '{"error":{"status":"RESOURCE_EXHAUSTED",'
                                  '"details":[{"retryDelay":"17s"}]}}')
        return FakeResponse(gemini_ok())

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", fake_urlopen)
    try:
        assert ai_client.chat("hi", backend="gemini") == "hello"
    finally:
        del os.environ["GEMINI_API_KEY"]
    assert calls["n"] == 3
    row = rows(clean_env)[0]
    assert row["status"] == "ok" and row["note"] == "retries=2"


def test_429_exhausted_is_rate_limited_and_recorded(clean_env, monkeypatch):
    os.environ["GEMINI_API_KEY"] = SENTINEL
    monkeypatch.setenv("PP_AI_RETRY_BASE", "0")
    monkeypatch.setenv("PP_AI_MAX_RETRIES", "1")
    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        raise http_error(429, '{"error":{"status":"RESOURCE_EXHAUSTED"}}')

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", fake_urlopen)
    try:
        with pytest.raises(ai_client.RateLimited):
            ai_client.chat("hi", backend="gemini")
    finally:
        del os.environ["GEMINI_API_KEY"]
    assert calls["n"] == 2
    row = rows(clean_env)[0]
    assert row["status"] == "rate_limited"
    assert row["tokens_source"] == "none"
    assert row["cost_basis"] == "not_applicable"


def test_an_error_body_carrying_the_key_is_redacted(clean_env, monkeypatch):
    os.environ["GEMINI_API_KEY"] = SENTINEL
    monkeypatch.setenv("PP_AI_MAX_RETRIES", "0")

    def fake_urlopen(request, timeout=None):
        raise http_error(401, '{"error":{"message":"API key not valid: %s"}}' % SENTINEL)

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", fake_urlopen)
    try:
        with pytest.raises(ai_client.AIError) as caught:
            ai_client.chat("hi", backend="gemini")
    finally:
        del os.environ["GEMINI_API_KEY"]
    message = str(caught.value)
    assert SENTINEL not in message, "the key leaked through the error message"
    assert "[REDACTED]" in message
    assert SENTINEL not in ledger_text(clean_env)
    assert rows(clean_env)[0]["status"] == "error"


def test_an_empty_answer_is_an_error_not_an_empty_string(clean_env, monkeypatch):
    os.environ["GEMINI_API_KEY"] = SENTINEL
    monkeypatch.setenv("PP_AI_MAX_RETRIES", "0")

    def fake_urlopen(request, timeout=None):
        return FakeResponse({"candidates": [{"content": {"parts": []},
                                             "finishReason": "SAFETY"}]})

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", fake_urlopen)
    try:
        with pytest.raises(ai_client.AIError) as caught:
            ai_client.chat("hi", backend="gemini")
    finally:
        del os.environ["GEMINI_API_KEY"]
    assert "finishReason=SAFETY" in str(caught.value)


# ---------------------------------------------------------------- refusals

def test_gemini_image_and_segment_refuse_instead_of_guessing(monkeypatch):
    monkeypatch.setenv("PP_AI_BACKEND", "gemini")
    with pytest.raises(ai_client.NotConfigured):
        ai_client.image("a title logo")
    with pytest.raises(ai_client.NotConfigured):
        ai_client.segment("sprite.png", box=[0, 0, 8, 8])


def test_azure_and_meta_are_stubs(monkeypatch):
    for name in ("azure", "meta"):
        backend = ai_client.get_backend(name)
        with pytest.raises(ai_client.NotConfigured):
            backend.chat("hi")
        with pytest.raises(ai_client.NotConfigured):
            backend.image("a logo")


def test_a_credential_looking_path_is_never_opened(tmp_path):
    for name in (".env", "auth.json", "AZURE_OPENAI_API_KEY.txt", "meta_token.txt"):
        with pytest.raises(ValueError) as caught:
            ai_client.vision(str(tmp_path / name), "read this", backend="mock")
        assert "credential file" in str(caught.value)
    assert not os.path.exists(str(tmp_path / ".env")), "the file must not have been created or read"


# ---------------------------------------------------------------- the price table itself

def test_the_default_model_has_a_dated_price(clean_env):
    assert ai_client.DEFAULT_GEMINI_MODEL in ai_client.PRICE_TABLE, \
        "the default model must be priced, or every call logs unknown_price_model"
    for model, price in ai_client.PRICE_TABLE.items():
        assert price["input_per_1m"] >= 0 and price["output_per_1m"] >= 0, model
        assert price["free_tier"] is True
    assert ai_client.PRICE_CHECKED == "2026-10-21"
    assert ai_client.PRICE_SOURCE.startswith("https://ai.google.dev/")


def test_an_unpriced_model_is_logged_as_unknown_not_as_free(clean_env, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    monkeypatch.setenv("PP_GEMINI_MODEL", "gemini-9-not-a-real-model")
    monkeypatch.setattr(ai_client.urllib.request, "urlopen",
                        lambda request, timeout=None: FakeResponse(gemini_ok()))
    try:
        ai_client.chat("hi", backend="gemini")
    finally:
        del os.environ["GEMINI_API_KEY"]
    row = rows(clean_env)[0]
    assert row["model"] == "gemini-9-not-a-real-model"
    assert row["cost_basis"] == "unknown_price_model"
    assert float(row["estimated_cost_usd"]) == 0.0


# ---------------------------------------------------------------- the CLI as a process

def test_the_module_runs_as_a_process_and_prints_no_key(tmp_path):
    env = dict(os.environ)
    for name in ENV_VARS:
        env.pop(name, None)
    env["GEMINI_API_KEY"] = SENTINEL
    env["PP_AI_LEDGER"] = str(tmp_path / "cli_ledger.csv")
    done = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ai_client.py"), "--dry-run"],
                          capture_output=True, text=True, cwd=ROOT, env=env, timeout=120, stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stderr
    assert SENTINEL not in done.stdout and SENTINEL not in done.stderr
    assert "backend: gemini" in done.stdout
    assert not os.path.exists(str(tmp_path / "cli_ledger.csv"))
