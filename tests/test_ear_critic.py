"""Tests for tools/ear_critic.py (card MUS-EAR). No network: every call goes through a fake transport.

What is pinned here, because each one is a rule the card states:
  * the fixed rubric is the one from EAR_REVIEW_126.md and it asks for a JSON block,
  * the model comes from PP_EAR_MODEL, default gemini-3.5-flash,
  * a key is never printed, never in the URL, never in the ledger or the review file,
  * every review leaves a review file (with the rough-listener warning), a ledger row and a
    calibration row, including the six scores parsed out of the answer,
  * the free tier is respected: 10 calls per minute, a daily counter, and 429 backoff,
  * a long file is split into 60 s chunks with an overlap and the loop seam on the last one,
  * a file whose name looks like a credential store is refused, not opened,
  * --compare asks which is more memorable and reports the winner,
  * --gap reports the distance between the ear and Nayil, and the unknown stays unknown.
"""

from __future__ import annotations

import csv
import io
import json
import os
import urllib.error

import pytest

import ear_critic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENTINEL = "sentinel-key-do-not-print-0123456789abcdef"

ENV_VARS = ("GEMINI_API_KEY", "PP_EAR_MODEL", "PP_EAR_LEDGER", "PP_EAR_CALIBRATION",
            "PP_EAR_REVIEW_DIR", "PP_EAR_MAX_INLINE_MB", "PP_EAR_MAX_PER_MINUTE",
            "PP_EAR_DAILY_MAX", "PP_EAR_MAX_RETRIES", "PP_EAR_RETRY_BASE",
            "PP_EAR_MAX_BACKOFF", "GEMINI_API_BASE", "GEMINI_API_KEY")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PP_EAR_LEDGER", str(tmp_path / "ear_ledger.csv"))
    monkeypatch.setenv("PP_EAR_CALIBRATION", str(tmp_path / "ear_calibration.csv"))
    monkeypatch.setenv("PP_EAR_REVIEW_DIR", str(tmp_path / "ear_reviews"))
    monkeypatch.setenv("PP_EAR_MAX_RETRIES", "1")
    monkeypatch.setenv("PP_EAR_RETRY_BASE", "0.01")
    monkeypatch.setenv("PP_EAR_MAX_BACKOFF", "0.02")
    return tmp_path


@pytest.fixture()
def audio(tmp_path):
    path = tmp_path / "theme.mp3"
    path.write_bytes(b"ID3" + b"\x00" * 4096)
    return path


def rows(path=None):
    path = path or ear_critic.ledger_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_text(path):
    with open(str(path), "r", encoding="utf-8") as handle:
        return handle.read()


def datetime_stamp(epoch):
    import datetime
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


class FakeResponse(object):
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8") if isinstance(payload, dict) else payload

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def gemini_ok(text, prompt_tokens=1200, output_tokens=800):
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": prompt_tokens,
                              "candidatesTokenCount": output_tokens}}


GOOD_ANSWER = """### 1) Section overview
0:00 to 0:16 bars 1 to 11: A minor waltz, pulse arpeggios under a stepwise lead.

### 2) Evaluation and scores (1 to 10)
- Hook memorability: 7/10, bars 1 to 8.
- Rhythm and drum interest: 3/10, the same boom-chick-chick throughout.
- Tension and dissonance: 5/10, safe diatonic harmony.
- Human feel versus mechanical: 4/10, everything sits on the grid.
- Instrumentation variety: 6/10, VRC6 adds warmth but nothing drops out.
- Structure and contrast: 5/10, section B keeps the same drive.

### 3) Five concrete changes
1. Bars 20 to 21: add an E7b9 under the lead.
2. Bars 22 to 36: pedal point on the triangle instead of the waltz third.
3. Bars 37 to 40: mute the inner pulse arpeggio.
4. Bars 12 to 21: delayed vibrato on the VRC6 lead.
5. Bars 45 to 52: noise triplet fill into the loop cadence.

### 4) The two most mechanical moments
0:32 and 0:48, identical attack on every eighth.

```json
{"hook": 7, "drums": 3, "tension": 5, "human": 4, "variety": 6, "structure": 5}
```
"""


@pytest.fixture()
def fake_http(monkeypatch):
    """Replace the transport. Returns the recorded (url, headers, payload) calls."""
    seen = {"calls": [], "responses": [], "sleeps": []}

    def fake_urlopen(request, timeout=None):
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        seen["calls"].append({"url": request.full_url,
                              "headers": dict(request.headers),
                              "payload": body})
        if not seen["responses"]:
            return FakeResponse(gemini_ok(GOOD_ANSWER))
        item = seen["responses"].pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)

    monkeypatch.setattr(ear_critic, "_urlopen", fake_urlopen)
    monkeypatch.setattr(ear_critic.time, "sleep", lambda seconds: seen["sleeps"].append(seconds))
    return seen


def http_error(code, body='{"error": {"status": "RESOURCE_EXHAUSTED"}}'):
    return urllib.error.HTTPError("https://example.invalid/x", code, "err", None,
                                  io.BytesIO(body.encode("utf-8")))


# ------------------------------------------------------------------ rubric and model

def test_default_model_is_the_one_the_card_names():
    assert ear_critic.DEFAULT_MODEL == "gemini-3.5-flash"
    assert ear_critic.model_name() == "gemini-3.5-flash"


def test_model_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("PP_EAR_MODEL", "gemini-9-ear")
    assert ear_critic.model_name() == "gemini-9-ear"


def test_the_prompt_carries_the_fixed_rubric_and_asks_for_json():
    prompt = ear_critic.rubric_prompt()
    for heading in ("### 1) Section overview", "### 2) Evaluation and scores (1 to 10)",
                    "### 3) Five concrete changes", "### 4) The two most mechanical moments",
                    "### 5) Scores as JSON"):
        assert heading in prompt
    for dimension in ear_critic.DIMENSIONS:
        assert ear_critic.DIMENSION_LABELS[dimension].split("(")[0].strip() in prompt
    assert '"hook": 6' in prompt and '"structure": 5' in prompt
    assert "bar range" in prompt or "bar ranges" in prompt


def test_prompt_uses_the_renderer_loop_context_when_there_is_one():
    line = ear_critic.context_line({"loop_bars": 52, "time_signature": "3/4", "bpm": 126.0,
                                    "loop_seconds": 74.29})
    assert "52 bars" in line and "3/4" in line and "126" in line and "74.29" in line
    assert ear_critic.context_line(None) == ""


# ------------------------------------------------------------------ parsing

def test_scores_are_read_from_the_json_block():
    scores = ear_critic.scores_from_text(GOOD_ANSWER)
    assert scores == {"hook": 7, "drums": 3, "tension": 5, "human": 4, "variety": 6,
                      "structure": 5}


def test_scores_fall_back_to_the_prose_when_the_model_forgets_the_block():
    prose = GOOD_ANSWER.split("```json")[0]
    scores = ear_critic.scores_from_text(prose)
    assert scores["hook"] == 7 and scores["drums"] == 3 and scores["structure"] == 5


def test_nested_compare_json_is_parsed_not_truncated():
    text = ('Verdict.\n```json\n{"winner": "A", "a": {"hook": 7, "drums": 3}, '
            '"b": {"hook": 5, "drums": 6}}\n```\n')
    payload = ear_critic._last_json_object(text)
    assert payload["winner"] == "A"
    assert ear_critic.normalise_scores(payload["a"])["hook"] == 7
    assert ear_critic.normalise_scores(payload["b"])["drums"] == 6


def test_out_of_range_and_alias_keys_are_handled():
    scores = ear_critic.normalise_scores({"memorability": 11, "rhythm_and_drum_interest": 4,
                                          "human": "8", "nonsense": 5})
    assert scores["hook"] is None  # 11 is not a 1 to 10 score, so it is missing, not invented
    assert scores["drums"] == 4
    assert scores["human"] == 8
    assert scores["variety"] is None


# ------------------------------------------------------------------ dry run and the key

def test_dry_run_sends_nothing_and_says_whether_the_key_is_present(monkeypatch, audio,
                                                                  capsys, fake_http):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    code = ear_critic.main(["--dry-run", str(audio)])
    out = capsys.readouterr().out
    assert code == 0
    assert fake_http["calls"] == []
    assert "gemini-3.5-flash" in out
    assert "present in GEMINI_API_KEY" in out
    assert SENTINEL not in out
    assert rows() == []


def test_a_missing_key_refuses_before_any_request(audio, capsys, fake_http):
    code = ear_critic.main([str(audio)])
    out = capsys.readouterr().out
    assert code == 2
    assert "GEMINI_API_KEY is not set" in out
    assert fake_http["calls"] == []


def test_the_key_never_leaks(monkeypatch, audio, capsys, fake_http, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    assert ear_critic.main([str(audio)]) == 0
    out = capsys.readouterr().out
    assert SENTINEL not in out
    call = fake_http["calls"][0]
    assert SENTINEL not in call["url"]
    assert any(value == SENTINEL for value in call["headers"].values())
    assert SENTINEL not in read_text(ear_critic.ledger_path())
    review = os.path.join(str(tmp_path / "ear_reviews"), os.listdir(str(tmp_path / "ear_reviews"))[0])
    assert SENTINEL not in read_text(review)


def test_a_credential_looking_file_name_is_refused_not_opened(monkeypatch, tmp_path, fake_http):
    suspicious = tmp_path / "gemini_token.mp3"
    suspicious.write_bytes(b"ID3")
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    with pytest.raises(ear_critic.EarError) as caught:
        ear_critic.review_file(str(suspicious))
    assert "credential store" in str(caught.value)
    assert fake_http["calls"] == []


# ------------------------------------------------------------------ one review end to end

def test_a_review_writes_the_file_the_ledger_row_and_the_calibration_row(
        monkeypatch, audio, capsys, fake_http, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    code = ear_critic.main([str(audio)])
    out = capsys.readouterr().out
    assert code == 0
    assert len(fake_http["calls"]) == 1

    payload = fake_http["calls"][0]["payload"]
    parts = payload["contents"][0]["parts"]
    assert parts[0]["text"].startswith("You are a strict but fair music critic")
    audio_part = parts[-1]["inline_data"]
    assert audio_part["mime_type"] == "audio/mpeg"
    assert audio_part["data"]

    review_files = os.listdir(str(tmp_path / "ear_reviews"))
    assert len(review_files) == 1
    review = read_text(os.path.join(str(tmp_path / "ear_reviews"), review_files[0]))
    assert ear_critic.WARNING in review
    assert "hook 7" in review and "drums 3" in review
    assert "gemini-3.5-flash" in review

    ledger = rows()
    summary = [row for row in ledger if row["role"] == "summary"]
    assert len(summary) == 1
    assert summary[0]["hook"] == "7" and summary[0]["drums"] == "3"
    assert summary[0]["file"].endswith("theme.mp3")
    assert summary[0]["model"] == "gemini-3.5-flash"
    assert summary[0]["at"].endswith("Z")
    assert [row for row in ledger if row["role"] == "review"][0]["status"] == "ok"

    calibration = list(csv.DictReader(io.StringIO(read_text(ear_critic.calibration_path()))))
    entry = [row for row in calibration if row["file"] == "theme"][0]
    assert entry["gemini_hook"] == "7"
    assert entry["nayil_hook"] == ""

    assert "scores:  hook 7" in out
    assert ear_critic.WARNING in out


def test_the_review_file_name_is_stamped_and_unique(monkeypatch, audio, tmp_path, fake_http):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    first = ear_critic.review_file(str(audio))
    second = ear_critic.review_file(str(audio))
    assert first["review"] != second["review"]
    assert os.path.basename(first["review"]).startswith("theme_")


def test_the_review_body_keeps_house_style_without_long_dashes():
    """Nayil's rule: no em dashes or en dashes in our artifacts, even inside model prose."""
    body = ("Hook memorability \u2014 7/10. Sections 0:00 \u2013 0:15 stay calm, bars 1\u201311."
            " No dash here\u2013at all.")
    scores = dict((d, 5) for d in ear_critic.DIMENSIONS)
    markdown = ear_critic._render_markdown("x.mp3", "gemini-3.5-flash", "/tmp/x.mp3",
                                           scores, body, {"chunks": 1})
    assert "\u2014" not in markdown
    assert "\u2013" not in markdown
    assert "Hook memorability, 7/10" in markdown
    assert "0:00 - 0:15" in markdown
    assert "bars 1-11" in markdown
    assert "  " not in markdown.split("---", 1)[1]


def test_a_review_written_to_disk_under_assets_audio_carries_no_long_dashes():
    """The file boundary, not just the string: what lands under assets/audio is stripped too."""
    parts = ear_critic.REVIEW_DIR.replace("\\", "/").rstrip("/").split("/")
    assert parts[-3:] == ["assets", "audio", "ear_reviews"]

    body = ("Hook memorability \u2014 6/10, sections 0:00 \u2013 0:16 and 0:52\u20141:14,"
            " and the bridge at \u2013 no, at bars 22\u201136.")
    scores = dict((d, 5) for d in ear_critic.DIMENSIONS)
    markdown = ear_critic._render_markdown("x.mp3", "gemini-3.5-flash", "/tmp/x.mp3",
                                           scores, body, {"chunks": 1})
    target = ear_critic.save_review("x.mp3", markdown)
    on_disk = read_text(target)
    assert "\u2014" not in on_disk
    assert "\u2013" not in on_disk
    assert "Hook memorability, 6/10" in on_disk


def test_bypassing_the_stripper_puts_the_dashes_back(monkeypatch):
    """Pins the rule at the writer: if _plain_dashes is skipped, both dashes reach the file.

    This is the failure mode the pasted EAR_REVIEW_126.md note showed: a body that never went
    through the critic's stripper carried 14 long dashes into the tree.
    """
    body = "Hook memorability \u2014 6/10, bars 1\u201311."
    scores = dict((d, 5) for d in ear_critic.DIMENSIONS)

    stripped = ear_critic._render_markdown("x.mp3", "m", "/tmp/x.mp3", scores, body, {})
    assert "\u2014" not in stripped and "\u2013" not in stripped

    monkeypatch.setattr(ear_critic, "_plain_dashes", lambda text: str(text or ""))
    bypassed = ear_critic._render_markdown("x.mp3", "m", "/tmp/x.mp3", scores, body, {})
    assert "\u2014" in bypassed and "\u2013" in bypassed


# ------------------------------------------------------------------ the free tier

def test_429_is_retried_then_succeeds(monkeypatch, audio, fake_http):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    monkeypatch.setenv("PP_EAR_MAX_RETRIES", "2")
    monkeypatch.setenv("PP_EAR_MAX_BACKOFF", "5")
    fake_http["responses"] = [
        http_error(429, '{"error": {"details": [{"retryDelay": "0.01s"}]}}'),
    ]
    result = ear_critic.review_file(str(audio))
    assert result["scores"]["hook"] == 7
    assert len(fake_http["calls"]) == 2
    assert fake_http["sleeps"] == [0.01 + 0.5]  # the delay Gemini asked for, plus a margin


def test_429_after_the_retries_is_reported_and_exits_3(monkeypatch, audio, capsys, fake_http):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    monkeypatch.setenv("PP_EAR_MAX_RETRIES", "1")
    fake_http["responses"] = [http_error(429), http_error(429)]
    assert ear_critic.main([str(audio)]) == 3
    out = capsys.readouterr().out
    assert "rate limited" in out and "429" in out


def test_the_gate_holds_the_call_until_the_minute_window_has_room(monkeypatch):
    sleeps = []
    now = [1750000000.0]

    def fake_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    stamp = datetime_stamp(now[0] - 20)
    gate = ear_critic.RateGate(per_minute=2, per_day=100, sleep=fake_sleep,
                               clock=lambda: now[0])
    for _ in range(2):
        ear_critic.append_ledger({"at": stamp, "role": "review", "status": "ok", "file": "a"})
    assert ear_critic.calls_in_last_minute(now=now[0]) == 2
    gate.before_call()  # waited out the window instead of firing a third call in it
    assert sleeps and now[0] - 1750000000.0 >= 35
    assert len(sleeps) < 30


def test_the_daily_counter_stops_the_run(monkeypatch):
    monkeypatch.setenv("PP_EAR_DAILY_MAX", "1")
    now = ear_critic.utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    ear_critic.append_ledger({"at": now, "role": "review", "status": "ok", "file": "a"})
    gate = ear_critic.RateGate(sleep=lambda seconds: None)
    with pytest.raises(ear_critic.DailyLimit):
        gate.before_call()


def test_the_summary_row_does_not_count_as_a_call(monkeypatch):
    now = ear_critic.utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    ear_critic.append_ledger({"at": now, "role": "review", "status": "ok", "file": "a"})
    ear_critic.append_ledger({"at": now, "role": "summary", "status": "ok", "file": "a"})
    assert ear_critic.calls_in_last_minute() == 1


# ------------------------------------------------------------------ long files

def test_a_short_file_is_one_inline_call():
    assert len(ear_critic.plan_chunks(45.0)) == 1
    assert len(ear_critic.plan_chunks(60.0)) == 1


def test_a_long_file_is_cut_into_overlapping_windows_that_cover_it():
    windows = ear_critic.plan_chunks(150.0)
    assert len(windows) == 3
    assert windows[0]["start"] == 0.0
    assert windows[1]["start"] == pytest.approx(58.0)
    assert windows[-1]["start"] + windows[-1]["length"] == pytest.approx(150.0)
    for window in windows:
        assert window["length"] <= 60.0 + 1e-9


def test_a_long_file_is_sent_in_chunks_plus_one_synthesis_call(monkeypatch, tmp_path,
                                                               fake_http):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    monkeypatch.setenv("PP_EAR_MAX_INLINE_MB", "0.0001")
    source = tmp_path / "long.mp3"
    source.write_bytes(b"ID3" + b"\x00" * 2048)
    loop = {"loop_bars": 52, "time_signature": "3/4", "bpm": 126.0,
            "loop_seconds": 74.0, "loop_start_sample": 0}
    (tmp_path / "long_loop.json").write_text(json.dumps(loop), encoding="utf-8")
    monkeypatch.setattr(ear_critic, "ffprobe_duration", lambda path: 130.0)

    def fake_cut(src, start, length, target):
        with open(str(target), "wb") as handle:
            handle.write(b"ID3" + b"\x00" * 256)
        return str(target)

    monkeypatch.setattr(ear_critic, "cut_audio", fake_cut)
    result = ear_critic.review_file(str(source))
    assert result["calls"] == 3  # two chunks plus the synthesis call
    chunk_payloads = [call["payload"] for call in fake_http["calls"][:2]]
    first_text = chunk_payloads[0]["contents"][0]["parts"][0]["text"]
    assert "chunk 1 of 2" in first_text
    last_parts = chunk_payloads[1]["contents"][0]["parts"]
    seam = [part for part in last_parts if "Loop seam" in part.get("text", "")]
    assert seam, "the last chunk must carry the loop seam part"
    synthesis = fake_http["calls"][2]["payload"]["contents"][0]["parts"]
    assert "Merge them into ONE review" in synthesis[0]["text"]
    assert "Chunk 2" in synthesis[0]["text"]
    assert result["review"] and os.path.exists(result["review"])


# ------------------------------------------------------------------ compare

def test_compare_asks_which_is_more_memorable_and_reports_the_winner(monkeypatch, tmp_path,
                                                                   capsys, fake_http):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    a = tmp_path / "a.mp3"
    b = tmp_path / "b.mp3"
    a.write_bytes(b"ID3a")
    b.write_bytes(b"ID3b")
    answer = ('### 1) Each version in time order\nA states the theme plainly, B adds a fill.\n\n'
              '### 3) Which is more memorable, and why\nThe four note turn in A sticks.\n\n'
              '```json\n{"winner": "A", "a": {"hook": 7, "drums": 3, "tension": 5, '
              '"human": 4, "variety": 6, "structure": 5}, "b": {"hook": 5, "drums": 6, '
              '"tension": 4, "human": 4, "variety": 5, "structure": 5}}\n```\n')
    fake_http["responses"] = [gemini_ok(answer)]
    assert ear_critic.main(["--compare", str(a), str(b)]) == 0
    out = capsys.readouterr().out
    assert "winner: A" in out
    parts = fake_http["calls"][0]["payload"]["contents"][0]["parts"]
    assert "which is more memorable" in parts[0]["text"].lower()
    inline = [part for part in parts if "inline_data" in part]
    assert len(inline) == 2  # both versions go in the same request
    review = os.path.join(ear_critic.review_dir(), os.listdir(ear_critic.review_dir())[0])
    text = read_text(review)
    assert "version A is more memorable" in text
    assert ear_critic.WARNING in text
    assert rows()[-1]["role"] == "compare"


def test_compare_dry_run_sends_nothing(monkeypatch, tmp_path, capsys, fake_http):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL)
    a = tmp_path / "a.mp3"
    b = tmp_path / "b.mp3"
    a.write_bytes(b"ID3a")
    b.write_bytes(b"ID3b")
    assert ear_critic.main(["--compare", str(a), str(b), "--dry-run"]) == 0
    assert fake_http["calls"] == []


# ------------------------------------------------------------------ calibration and the gap

def test_the_calibration_seed_row_carries_the_scores_the_card_gives():
    ear_critic.seed_calibration()
    table = list(csv.DictReader(io.StringIO(read_text(ear_critic.calibration_path()))))
    assert len(table) == 1
    row = table[0]
    assert row["file"] == "title_theme_v3_126"
    assert [row["gemini_%s" % d] for d in ear_critic.DIMENSIONS] == ["6", "4", "5", "3", "6", "5"]
    assert row["nayil_hook"] == "" and row["nayil_note"] == "unknown"


def test_the_gap_is_reported_only_once_nayil_has_scored_a_file(capsys):
    assert ear_critic.main(["--gap"]) == 0
    out = capsys.readouterr().out
    assert "No row has Nayil's scores yet" in out
    assert "title_theme_v3_126" in out

    assert ear_critic.main(["--nayil", "title_theme_v3_126:8,6,6,5,7,6"]) == 0
    out = capsys.readouterr().out
    assert "recorded Nayil's scores" in out
    report = ear_critic.gap_report()
    assert report["compared_rows"] == 1
    assert report["per_dimension"]["hook"]["signed_mean"] == pytest.approx(-2.0)
    assert report["per_dimension"]["drums"]["signed_mean"] == pytest.approx(-2.0)
    assert report["per_dimension"]["human"]["signed_mean"] == pytest.approx(-2.0)
    assert report["overall_mean_abs"] == pytest.approx(1.5)


def test_a_nayil_score_outside_1_to_10_is_refused():
    with pytest.raises(ear_critic.EarError):
        ear_critic.record_nayil("x", {"hook": 12})


# ------------------------------------------------------------------ sharing the rubric with the manager

def test_the_saved_manager_review_matches_this_rubric(tmp_path):
    """The card says the prompt is the one used in EAR_REVIEW_126.md; keep them in step."""
    path = os.path.join(ROOT, "assets", "audio", "title_theme_v3", "EAR_REVIEW_126.md")
    # No skip when the note is missing (card t_50a290de, 2026-10-22): it is tracked, and the skip was
    # the reason a HEAD checkout passed this test without comparing anything.
    assert os.path.isfile(path), path
    text = read_text(path)
    prompt = ear_critic.rubric_prompt()
    for needle in ("Section overview", "Evaluation & Scores", "5 Concrete Changes",
                   "2 Most Mechanical Moments"):
        assert needle.split("&")[0].split()[0] in text
    assert "Hook memorability" in text and "Hook memorability" in prompt
    assert "Rhythm and drum interest" in text and "Rhythm and drum interest" in prompt
    assert "Tension and dissonance" in text and "Tension and dissonance" in prompt
    assert "Human feel" in text and "Human feel" in prompt
    assert "Instrumentation variety" in text and "Instrumentation variety" in prompt
    assert "Structure and contrast" in text and "Structure and contrast" in prompt
