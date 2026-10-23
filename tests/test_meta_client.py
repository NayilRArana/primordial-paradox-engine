"""Tests for tools/meta_client.py (card META-CLIENT). No network: a fake transport, or the mock.

The fake transport is a real seam, not a patched urlopen: tools/meta_client.UrllibTransport.post
returns (status, headers, body text), so every test drives the same code path the live client
takes for chat, vision, images, edits and segmentation, including the 429 backoff, without a
socket ever being opened. ForbidTransport answers any request with an AssertionError, which is
how the replay tests prove that no network call happened at all.
"""

from __future__ import annotations

import base64
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import meta_client  # noqa: E402

TEST_KEY = "sk-" + "test" + "-not-a-real-key-0123456789abcdef"
COMMITTED_CACHE = meta_client.DEFAULT_CACHE_DIR


# ---------------------------------------------------------------- fake HTTP layer

class FakeTransport(object):
    """Plays back a list of (status, headers, body) and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, payload, headers, timeout):
        self.calls.append({"url": url, "payload": payload, "headers": dict(headers),
                           "timeout": timeout})
        if not self.responses:
            raise AssertionError("the client made one more request than the test expected")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ForbidTransport(object):
    """Any request is a test failure: this is how replay is proved to be offline."""

    def __init__(self):
        self.calls = []

    def post(self, url, payload, headers, timeout):
        self.calls.append(url)
        raise AssertionError("replay mode touched the network: %s" % url)


def ok(body):
    return (200, {}, json.dumps(body))


def chat_body(text="a verdict", prompt_tokens=11, completion_tokens=3):
    return ok({"choices": [{"index": 0, "finish_reason": "stop",
                            "message": {"role": "assistant", "content": text}}],
               "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                         "total_tokens": prompt_tokens + completion_tokens}})


def image_body(b64_text=None, url=None):
    item = {"revised_prompt": "a knight"}
    if b64_text is not None:
        item["b64_json"] = b64_text
    if url is not None:
        item["url"] = url
    return ok({"data": [item], "output_format": "png"})


def segmentation_body(text):
    return ok({"output": [{"type": "message", "role": "assistant",
                           "content": [{"type": "output_text", "text": text}]}]})


@pytest.fixture()
def sleeps(monkeypatch, tmp_path):
    """Offline defaults: fake cache dir, meta backend, record mode, no real sleeping."""
    monkeypatch.setenv("PP_AI_CACHE", str(tmp_path / "ai_cache"))
    monkeypatch.setenv("PP_AI_BACKEND", "meta")
    monkeypatch.setenv("PP_AI_MODE", "record")
    monkeypatch.setenv("MODEL_API_KEY", TEST_KEY)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.setenv("PP_META_MAX_RETRIES", "2")
    monkeypatch.setenv("PP_META_RETRY_BASE", "0.001")
    monkeypatch.setenv("PP_META_RPM", "0")
    monkeypatch.delenv("PP_META_MODEL", raising=False)
    recorded = []
    monkeypatch.setattr(meta_client, "SLEEP", recorded.append)
    meta_client.reset_rate_state()
    yield recorded
    meta_client.reset_rate_state()


def entries(tmp_path):
    folder = str(tmp_path / "ai_cache")
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            with open(os.path.join(folder, name), "r", encoding="utf-8") as handle:
                out.append(json.load(handle))
    return out


@pytest.fixture()
def png(tmp_path):
    path = tmp_path / "frame.png"
    path.write_bytes(meta_client.png_bytes(8, 8, (60, 60, 200)))
    return str(path)


# ---------------------------------------------------------------- environment

def test_defaults_are_meta_and_record(monkeypatch):
    monkeypatch.delenv("PP_AI_BACKEND", raising=False)
    monkeypatch.delenv("PP_AI_MODE", raising=False)
    assert meta_client.backend_name() == "meta"
    assert meta_client.mode() == "record"
    assert meta_client.base_url() == "https://api.meta.ai/v1"
    assert meta_client.model_for("chat") == "muse-spark-1.3"
    assert meta_client.model_for("image") == "muse-image-1.0"
    assert meta_client.model_for("segment") == "sam-3.1"


def test_role_model_override(monkeypatch):
    monkeypatch.setenv("PP_META_MODEL", "muse-spark-1.3-contributor")
    monkeypatch.setenv("PP_META_MODEL_IMAGE", "muse-image-1.0")
    assert meta_client.model_for("chat") == "muse-spark-1.3-contributor"
    assert meta_client.model_for("image") == "muse-image-1.0"


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    with pytest.raises(meta_client.MetaKeyMissing) as caught:
        meta_client.chat("judge this line")
    message = str(caught.value)
    assert "MODEL_API_KEY" in message
    assert "replay" in message and "mock" in message
    assert TEST_KEY not in message


def test_blank_key_is_missing(monkeypatch, sleeps):
    monkeypatch.setenv("MODEL_API_KEY", "   ")
    monkeypatch.setenv("META_API_KEY", "")
    assert meta_client.key_present() is False
    with pytest.raises(meta_client.MetaKeyMissing):
        meta_client.chat("hello")


def test_fallback_key_env(monkeypatch, sleeps):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("META_API_KEY", TEST_KEY)
    meta_client.TRANSPORT = FakeTransport(chat_body("from the fallback key"))
    assert meta_client.chat("hi") == "from the fallback key"


def test_unknown_backend_and_mode_are_refused(monkeypatch, sleeps):
    monkeypatch.setenv("PP_AI_BACKEND", "openai")
    with pytest.raises(meta_client.NotConfigured) as caught:
        meta_client.chat("hi")
    assert "PP_AI_BACKEND" in str(caught.value)
    monkeypatch.setenv("PP_AI_BACKEND", "meta")
    monkeypatch.setenv("PP_AI_MODE", "cached")
    with pytest.raises(meta_client.NotConfigured) as caught:
        meta_client.chat("hi")
    assert "PP_AI_MODE" in str(caught.value)


# ---------------------------------------------------------------- chat

def test_chat_posts_openai_shape_and_records(tmp_path, sleeps, monkeypatch):
    transport = FakeTransport(chat_body("mercy up"))
    monkeypatch.setattr(meta_client, "TRANSPORT", transport)
    text = meta_client.chat([{"role": "system", "content": "you are Zeus"},
                             {"role": "user", "content": "I came to be remembered"}])
    assert text == "mercy up"
    call = transport.calls[0]
    assert call["url"] == "https://api.meta.ai/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer %s" % TEST_KEY
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["payload"]["model"] == "muse-spark-1.3"
    assert call["payload"]["messages"][1]["content"] == "I came to be remembered"
    assert "response_format" not in call["payload"]
    # the key is in the header and nowhere else
    assert TEST_KEY not in call["url"]
    assert TEST_KEY not in json.dumps(call["payload"])
    recorded = entries(tmp_path)
    assert len(recorded) == 1
    entry = recorded[0]
    assert entry["kind"] == "chat" and entry["backend"] == "meta"
    assert entry["network"] is True
    assert entry["response"]["text"] == "mercy up"
    assert entry["request"]["messages"][0]["content"] == "you are Zeus"


def test_chat_with_schema_sets_response_format(tmp_path, sleeps, monkeypatch):
    transport = FakeTransport(chat_body('{"mercy_delta": 2, "refusal": false, "line": "hm"}'))
    monkeypatch.setattr(meta_client, "TRANSPORT", transport)
    schema = {"type": "object",
              "properties": {"mercy_delta": {"type": "integer"},
                             "refusal": {"type": "boolean"},
                             "line": {"type": "string"}},
              "required": ["mercy_delta", "refusal", "line"]}
    verdict = meta_client.chat_structured([{"role": "user", "content": "judge"}], schema=schema)
    assert verdict["mercy_delta"] == 2
    assert verdict["refusal"] is False
    sent = transport.calls[0]["payload"]["response_format"]
    assert sent["type"] == "json_schema"
    assert sent["json_schema"]["schema"] == schema
    assert sent["json_schema"]["strict"] is True


def test_chat_structured_rejects_a_non_json_answer(sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(chat_body("no json here")))
    with pytest.raises(meta_client.BadResponse):
        meta_client.chat_structured("judge", schema={"type": "object"})


def test_parse_json_finds_a_fenced_block():
    text = 'Here is the verdict:\n```json\n{"mercy_delta": -1, "line": "begone"}\n```\nDone.'
    assert meta_client.parse_json(text)["line"] == "begone"
    assert meta_client.parse_json('prefix {"a": {"b": 1}} suffix')["a"]["b"] == 1
    with pytest.raises(meta_client.BadResponse):
        meta_client.parse_json("nothing to parse")


def test_chat_empty_answer_is_a_bad_response(sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT",
                        FakeTransport(ok({"choices": [{"message": {"content": "  "}}]})))
    with pytest.raises(meta_client.BadResponse):
        meta_client.chat("hi")


# ---------------------------------------------------------------- vision

def test_vision_sends_an_image_data_url(png, tmp_path, sleeps, monkeypatch):
    transport = FakeTransport(chat_body("2 colours outside the palette"))
    monkeypatch.setattr(meta_client, "TRANSPORT", transport)
    text = meta_client.vision("count the colours", png)
    assert text.startswith("2 colours")
    content = transport.calls[0]["payload"]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "count the colours"}
    url = content[1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == open(png, "rb").read()
    entry = entries(tmp_path)[0]
    assert entry["kind"] == "vision"
    assert entry["request"]["image_sha256"]
    assert "base64" not in json.dumps(entry["request"])  # the entry stays small


def test_vision_refuses_a_credential_looking_path(tmp_path, sleeps):
    path = tmp_path / "GEMINI_API_KEY.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        meta_client.vision("what is this", str(path))
    assert "credential" in str(caught.value)


def test_vision_needs_a_prompt(png, sleeps):
    with pytest.raises(ValueError):
        meta_client.vision("", png)


# ---------------------------------------------------------------- images

def test_generate_image_writes_the_bytes_and_records(tmp_path, sleeps, monkeypatch):
    raw = meta_client.png_bytes(4, 4, (220, 60, 60))
    monkeypatch.setattr(meta_client, "TRANSPORT",
                        FakeTransport(image_body(base64.b64encode(raw).decode("ascii"))))
    out = tmp_path / "sub" / "concept.png"
    made = meta_client.generate_image("a knight", size="1024x1024", out_path=str(out))
    assert made["kind"] == "image" and made["backend"] == "meta" and made["cached"] is False
    assert made["path"] == str(out)
    assert out.read_bytes() == raw
    recorded = entries(tmp_path)
    assert recorded and recorded[0]["kind"] == "image" and recorded[0]["network"] is True


def test_generate_image_url_only_answer_is_reported_not_invented(tmp_path, sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT",
                        FakeTransport(image_body(url="https://cdn.example/a.png"),
                                      image_body(url="https://cdn.example/a.png")))
    made = meta_client.generate_image("a knight")
    assert made["url"] == "https://cdn.example/a.png"
    assert made["image_b64"] is None and made["path"] is None
    with pytest.raises(meta_client.BadResponse):
        meta_client.generate_image("a knight", out_path=str(tmp_path / "x.png"))


def test_edit_image_sends_the_source_array(png, tmp_path, sleeps, monkeypatch):
    raw = meta_client.png_bytes(4, 4, (60, 190, 60))
    transport = FakeTransport(image_body(base64.b64encode(raw).decode("ascii")))
    monkeypatch.setattr(meta_client, "TRANSPORT", transport)
    made = meta_client.edit_image(png, "the same knight, front view", size="512x512")
    assert made["kind"] == "edit"
    sent = transport.calls[0]["payload"]
    assert transport.calls[0]["url"].endswith("/images/edits")
    assert sent["images"][0]["image_url"].startswith("data:image/png;base64,")
    assert sent["prompt"] == "the same knight, front view"
    assert len(entries(tmp_path)) == 1


# ---------------------------------------------------------------- segmentation

def test_segment_reads_boxes_and_masks(png, sleeps, monkeypatch):
    text = ('<|object|> knight <|box|> 10, 20, 30, 40 <|mask_bits|> 0110 1001 '
            '<|object|> shield <|box|> 1, 2, 3, 4')
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(segmentation_body(text)))
    cut = meta_client.segment(png, "knight")
    assert cut["kind"] == "segment" and cut["model"] == "sam-3.1"
    assert cut["boxes"] == [[10, 20, 30, 40], [1, 2, 3, 4]]
    assert len(cut["masks"]) == 1
    assert "knight" in cut["text"]
    assert "UNKNOWN" in cut["note"]


def test_segment_zero_objects_is_not_an_error(png, sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(segmentation_body("")))
    cut = meta_client.segment(png, "dragon")
    assert cut["boxes"] == [] and cut["masks"] == [] and cut["text"] == ""


def test_segment_needs_one_noun_phrase(png, sleeps):
    with pytest.raises(ValueError):
        meta_client.segment(png, "")


def test_parse_segmentation_prefers_json_boxes_from_the_body():
    data = {"boxes": [{"box": [5, 6, 7, 8]}], "masks": ["abc"], "output_text": ""}
    boxes, masks = meta_client.parse_segmentation(meta_client.segmentation_text(data), data)
    assert boxes == [[5, 6, 7, 8]]
    assert masks == ["abc"]


# ---------------------------------------------------------------- cache modes

def test_replay_answers_from_the_cache_with_no_network(tmp_path, sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(chat_body("recorded answer")))
    assert meta_client.chat("record me") == "recorded answer"
    forbid = ForbidTransport()
    monkeypatch.setattr(meta_client, "TRANSPORT", forbid)
    monkeypatch.setenv("PP_AI_MODE", "replay")
    assert meta_client.chat("record me") == "recorded answer"
    assert forbid.calls == []


def test_replay_does_not_need_a_key(tmp_path, sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(chat_body("cached")))
    meta_client.chat("offline demo line")
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.setattr(meta_client, "TRANSPORT", ForbidTransport())
    monkeypatch.setenv("PP_AI_MODE", "replay")
    assert meta_client.chat("offline demo line") == "cached"


def test_replay_miss_is_a_clear_error(tmp_path, sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT", ForbidTransport())
    monkeypatch.setenv("PP_AI_MODE", "replay")
    with pytest.raises(meta_client.CacheMiss) as caught:
        meta_client.chat("never recorded")
    assert "PP_AI_MODE=record" in str(caught.value)


def test_live_mode_writes_nothing(tmp_path, sleeps, monkeypatch):
    monkeypatch.setenv("PP_AI_MODE", "live")
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(chat_body("one"),
                                                               chat_body("one")))
    meta_client.chat("twice")
    meta_client.chat("twice")
    assert entries(tmp_path) == []


def test_cache_key_is_stable_and_model_sensitive(tmp_path, sleeps, monkeypatch):
    payload = {"model": "muse-spark-1.3", "messages": [{"role": "user", "content": "x"}]}
    first = meta_client.request_key("chat", "muse-spark-1.3", payload, extra="meta")
    second = meta_client.request_key("chat", "muse-spark-1.3", payload, extra="meta")
    other = meta_client.request_key("chat", "muse-spark-1.3-contributor", payload, extra="meta")
    assert first == second and first != other and len(first) == 64


def test_no_key_material_in_any_cache_file(tmp_path, sleeps, monkeypatch):
    image = _tiny_png(tmp_path)
    monkeypatch.setattr(meta_client, "TRANSPORT",
                        FakeTransport(chat_body("a"), image_body("AAAA"), segmentation_body("x")))
    meta_client.chat("hello")
    meta_client.generate_image("a knight")
    meta_client.segment(image, "knight")
    folder = tmp_path / "ai_cache"
    assert os.listdir(folder)
    for name in os.listdir(folder):
        text = (folder / name).read_text(encoding="utf-8")
        assert TEST_KEY not in text
        assert "Bearer" not in text
        assert "Authorization" not in text


def _tiny_png(tmp_path):
    path = tmp_path / "tiny.png"
    path.write_bytes(meta_client.png_bytes(2, 2, (15, 15, 15)))
    return str(path)


# ---------------------------------------------------------------- retries and limits

def test_429_is_retried_with_retry_after_then_answers(sleeps, monkeypatch):
    transport = FakeTransport((429, {"retry-after": "0.25"}, '{"error": "slow down"}'),
                              chat_body("second attempt"))
    monkeypatch.setattr(meta_client, "TRANSPORT", transport)
    assert meta_client.chat("hi") == "second attempt"
    assert sleeps == [0.25]
    assert len(transport.calls) == 2


def test_429_exhausted_raises_rate_limited(sleeps, monkeypatch):
    monkeypatch.setenv("PP_META_MAX_RETRIES", "1")
    monkeypatch.setattr(meta_client, "TRANSPORT",
                        FakeTransport(*[(429, {}, "too many")] * 2))
    with pytest.raises(meta_client.RateLimited) as caught:
        meta_client.chat("hi")
    assert "429" in str(caught.value)


def test_5xx_exhausted_raises_meta_error_not_rate_limited(sleeps, monkeypatch):
    monkeypatch.setenv("PP_META_MAX_RETRIES", "0")
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport((503, {}, "unavailable")))
    with pytest.raises(meta_client.MetaError) as caught:
        meta_client.chat("hi")
    assert not isinstance(caught.value, meta_client.RateLimited)
    assert "503" in str(caught.value)


def test_401_body_is_redacted(sleeps, monkeypatch):
    leaky = '{"error": "bad key", "sent": "Bearer %s"}' % TEST_KEY
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport((401, {}, leaky)))
    with pytest.raises(meta_client.MetaError) as caught:
        meta_client.chat("hi")
    assert TEST_KEY not in str(caught.value)


def test_network_failure_is_reported(sleeps, monkeypatch):
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport((0, {}, "network error: refused")))
    with pytest.raises(meta_client.MetaError) as caught:
        meta_client.chat("hi")
    assert "no response" in str(caught.value)


def test_rate_gate_waits_before_a_second_call(sleeps, monkeypatch):
    monkeypatch.setenv("PP_META_RPM", "1")
    meta_client.reset_rate_state()
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(chat_body("one"),
                                                               chat_body("two")))
    meta_client.chat("first")
    meta_client.chat("second")
    assert sleeps and sleeps[0] > 0


# ---------------------------------------------------------------- mock backend

def test_mock_is_deterministic_and_offline(tmp_path, sleeps, monkeypatch):
    monkeypatch.setenv("PP_AI_BACKEND", "mock")
    monkeypatch.setattr(meta_client, "TRANSPORT", ForbidTransport())
    first = meta_client.chat("judge this")
    second = meta_client.chat("judge this")
    assert first == second and first.startswith("mock chat")
    entry = entries(tmp_path)[0]
    assert entry["backend"] == "mock" and entry["network"] is False


def test_mock_answers_a_schema_with_a_canned_object(sleeps, monkeypatch):
    monkeypatch.setenv("PP_AI_BACKEND", "mock")
    schema = {"type": "object",
              "properties": {"mercy_delta": {"type": "integer"},
                             "refusal": {"type": "boolean"},
                             "line": {"type": "string"}},
              "required": ["mercy_delta", "refusal", "line"]}
    verdict = meta_client.chat_structured("judge", schema=schema)
    assert verdict == {"mercy_delta": 0, "refusal": False, "line": "mock"}


def test_mock_image_is_a_real_png(tmp_path, sleeps, monkeypatch):
    monkeypatch.setenv("PP_AI_BACKEND", "mock")
    made = meta_client.generate_image("a knight", size="512x512",
                                      out_path=str(tmp_path / "mock.png"))
    assert made["width"] == 64 and made["height"] == 64  # capped, kept small for the cache
    with open(made["path"], "rb") as handle:
        assert handle.read(8) == b"\x89PNG\r\n\x1a\n"


def test_mock_segment_returns_one_box(tmp_path, sleeps, monkeypatch):
    monkeypatch.setenv("PP_AI_BACKEND", "mock")
    cut = meta_client.segment(_tiny_png(tmp_path), "knight")
    assert cut["boxes"] == [[0, 0, 16, 16]]


# ---------------------------------------------------------------- critics adapter

def test_gemini_compat_generate_translates_both_ways(tmp_path, sleeps, monkeypatch):
    transport = FakeTransport(chat_body("scores: 7/10", prompt_tokens=1300,
                                        completion_tokens=120))
    monkeypatch.setattr(meta_client, "TRANSPORT", transport)
    payload = {"contents": [{"role": "user", "parts": [
        {"text": "score this frame"},
        {"inline_data": {"mime_type": "image/png", "data": "QUJD"}}]}]}
    body = meta_client.gemini_compat_generate("muse-spark-1.3", payload)
    assert body["candidates"][0]["content"]["parts"][0]["text"] == "scores: 7/10"
    assert body["candidates"][0]["finishReason"] == "STOP"
    assert body["usageMetadata"]["promptTokenCount"] == 1300
    assert body["usageMetadata"]["candidatesTokenCount"] == 120
    assert body["ppMeta"]["cached"] is False
    sent = transport.calls[0]["payload"]
    assert transport.calls[0]["url"].endswith("/chat/completions")
    assert sent["messages"][0]["content"][0] == {"type": "text", "text": "score this frame"}
    assert sent["messages"][0]["content"][1]["image_url"]["url"] == "data:image/png;base64,QUJD"


def test_gemini_compat_generate_text_only_is_a_chat_call(sleeps, monkeypatch):
    transport = FakeTransport(chat_body("text only"))
    monkeypatch.setattr(meta_client, "TRANSPORT", transport)
    body = meta_client.gemini_compat_generate("muse-spark-1.3",
                                              {"contents": [{"parts": [{"text": "hi"}]}]})
    assert body["candidates"][0]["content"]["parts"][0]["text"] == "text only"
    assert isinstance(transport.calls[0]["payload"]["messages"][0]["content"], str)


def test_ear_critic_uses_meta_when_selected(sleeps, monkeypatch):
    import ear_critic
    monkeypatch.setattr(meta_client, "TRANSPORT",
                        FakeTransport(chat_body("hook: 7, rhythm: 6, tension: 5")))
    body, retries = ear_critic.post_generate("muse-spark-1.3",
                                            {"contents": [{"parts": [{"text": "review this"}]}]})
    assert retries == 0
    text, usage = ear_critic.read_response(body)
    assert text.startswith("hook: 7")
    assert "promptTokenCount" in usage


def test_eye_critic_uses_meta_when_selected(sleeps, tmp_path, monkeypatch):
    import eye_critic
    monkeypatch.setattr(meta_client, "TRANSPORT", FakeTransport(chat_body("nes: 8, readable: 9")))
    body, retries = eye_critic.post_generate(
        "muse-spark-1.3",
        {"contents": [{"parts": [{"text": "score"}, {"inline_data": {"mime_type": "image/png",
                                                                    "data": "QUJD"}}]}]})
    assert retries == 0
    text, _usage = eye_critic.read_response(body)
    assert text.startswith("nes: 8")


def test_ear_critic_keeps_gemini_when_selected(monkeypatch):
    import ear_critic
    monkeypatch.setenv("PP_AI_BACKEND", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ear_critic.NotConfigured):
        ear_critic.post_generate("gemini-3.6-flash",
                                 {"contents": [{"parts": [{"text": "hi"}]}]})


def test_gemini_backend_still_routes_to_the_gemini_client(tmp_path, sleeps, monkeypatch):
    import ai_client
    monkeypatch.setenv("PP_AI_BACKEND", "gemini")
    monkeypatch.setattr(ai_client, "chat", lambda messages, **kw: "gemini says hi")
    assert meta_client.chat("hello") == "gemini says hi"
    assert entries(tmp_path) == []


# ---------------------------------------------------------------- CLI and committed cache

def test_cli_dry_run_and_cache_status(capsys, sleeps, monkeypatch):
    monkeypatch.setenv("PP_AI_MODE", "replay")
    assert meta_client.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "backend: meta" in out and "mode: replay" in out
    assert TEST_KEY not in out
    assert meta_client.main(["--dry-run", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "meta" and payload["key_present"] is True
    assert meta_client.main(["--cache-status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["entries"] == 0


def _committed_entries():
    if not os.path.isdir(COMMITTED_CACHE):
        return []
    out = []
    for name in sorted(os.listdir(COMMITTED_CACHE)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(COMMITTED_CACHE, name), "r", encoding="utf-8") as handle:
            out.append(json.load(handle))
    return out


def test_committed_cache_is_keyed_correctly_and_replays_offline(monkeypatch):
    recorded = _committed_entries()
    if not recorded:
        pytest.skip("no committed cache yet: run meta_client.py --record-demo")
    monkeypatch.setenv("PP_AI_CACHE", COMMITTED_CACHE)
    monkeypatch.setenv("PP_AI_MODE", "replay")
    monkeypatch.setenv("PP_AI_BACKEND", "meta")
    monkeypatch.setattr(meta_client, "TRANSPORT", ForbidTransport())
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    replayed = 0
    for entry in recorded:
        key = meta_client.request_key(entry["kind"], entry["model"], entry["request"],
                                      extra=str(entry["backend"]))
        assert key == entry["key"], "cache file name does not match its own key"
    for entry in recorded:
        if entry["kind"] != "chat" or "response_format" in entry["request"]:
            continue
        monkeypatch.setenv("PP_AI_BACKEND", str(entry["backend"]))
        text = meta_client.chat(entry["request"]["messages"], model=entry["model"])
        assert text == entry["response"]["text"]
        replayed += 1
    assert replayed >= 1, "the committed cache has no plain chat entry to replay"
    assert meta_client.cache_status()["replayable_offline"] == len(recorded)
