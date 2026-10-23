"""Tests for tools/bake_meta.py (card R29 META-BAKE, spec 19 sections 2 to 11, D5).

What is pinned here, in the order the card argues it:

1. `--offline` is total. Every fight phase the data can reach and both NPCs get three option rows, every
   row is fallback sourced, and the file records where each fallback came from (a card pool line in
   data/talk_cards.json, or a line id in knowledge/GATE-DIALOGUE.md).
2. The shape is spec 19's. Every line is inside the font alphabet and at most 28 characters, at most 4
   lines, the mood is one of five, the effect is one of five and legal for the scene, and no row carries
   the string `spare`.
3. `--check` refuses what the card says it refuses: a line over 28 characters, an effect outside the
   enum, and a fallback id that does not exist in data/talk_cards.json. It refuses four more that keep
   the file honest: a URL or a key name, a hash that does not recompute, an offline row claiming a live
   answer, and a bake block whose counts disagree with its rows.
4. The offline bake never calls the client, a valid live answer is written as live, and a refused answer
   falls back with the reason recorded, so no row can claim a call it did not make (R43's check 4).
5. The file is ASCII with no long dash, which the manager and the pre-commit hook both require.
"""

from __future__ import annotations

import json
import os

import pytest

import bake_meta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAKE_FILE = os.path.join(ROOT, "data", "meta_bake.json")


@pytest.fixture(scope="module")
def baked():
    """The offline document, built once: the same call `--offline` makes, without writing the file."""
    document, mode, state, skipped, units = bake_meta.run_bake(offline=True)
    return {"document": document, "mode": mode, "state": state, "skipped": skipped, "units": units}


@pytest.fixture()
def copy_of_the_file(tmp_path):
    """A writable copy of data/meta_bake.json, so a mutation never touches the committed file."""
    with open(BAKE_FILE, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    path = tmp_path / "meta_bake.json"

    def write(mutate=None):
        data = json.loads(json.dumps(document))
        if mutate:
            mutate(data)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        return str(path)

    return write


# ----------------------------------------------------------------- the offline bake is total

def test_offline_writes_every_row_from_the_hand_written_fallback(baked):
    document = baked["document"]
    rows = document["rows"]
    assert rows, "the offline bake wrote no rows"
    assert all(row["source"] == "fallback" for row in rows)
    assert all(row["network"] is False for row in rows)
    assert all(row["reason"] for row in rows), "an offline row must say why it is offline"
    assert document["bake"]["live"] == 0
    assert document["bake"]["fallback"] == len(rows)
    assert document["bake"]["network"] is False


def test_every_reachable_fight_phase_gets_three_options(baked):
    document = baked["document"]
    counts = {}
    for row in document["rows"]:
        if row["scene"] == "fight":
            counts[row["card"]] = counts.get(row["card"], 0) + 1
    for unit in baked["units"]:
        card = unit["card"]["id"]
        assert counts.get(card) == 3, "card %s is reachable and needs three options" % card
    listed = {row["card"] for row in document["coverage"]["fight_phases"]}
    assert listed == set(counts)


def test_both_approved_npcs_are_baked_morgan_first(baked):
    document = baked["document"]
    npc_rows = [row for row in document["rows"] if row["scene"] == "npc"]
    order = [row["npc"] for row in npc_rows]
    assert order == ["morgan", "morgan", "morgan", "nye", "nye", "nye"], "Q10: Morgan first, then Nye"
    assert [row["effect"] for row in npc_rows[:3]] == ["none", "none", "end"]
    assert [row["effect"] for row in npc_rows[3:]] == ["none", "none", "end"]


def test_a_card_with_no_enemy_row_is_skipped_and_named(baked):
    document = baked["document"]
    cards = bake_meta.load_cards()[1]
    enemies = bake_meta.load_enemies()
    reachable = {card["id"] for card in cards.values()
                 if (card.get("enemy") or card["id"]) in enemies}
    listed = {row["card"] for row in document["rows"] if row["scene"] == "fight"}
    skipped = {row["card"] for row in document["coverage"]["skipped"]}
    assert listed == reachable
    assert not (skipped & listed)
    assert all("enemies" in row["reason"] or "dialogue" in row["reason"]
               for row in document["coverage"]["skipped"])


# ----------------------------------------------------------------- the shape is spec 19's

def test_every_row_is_inside_the_font_and_the_28_column_shape(baked):
    glyphs = bake_meta.load_glyphs()
    for row in baked["document"]["rows"]:
        assert 1 <= len(row["text"]) <= bake_meta.MAX_LINES, row["id"]
        for line in row["text"]:
            assert 1 <= len(line) <= 28, "%s: %r" % (row["id"], line)
            assert all(character in glyphs for character in line), "%s: %r" % (row["id"], line)
            assert bake_meta.REPLY_PATTERN.match(line), "%s: %r" % (row["id"], line)
        assert row["mood"] in bake_meta.MOODS
        assert row["effect"] in bake_meta.EFFECTS
        assert len(row["hint"]) <= 28
        assert all(character in glyphs for character in row["hint"])


def test_the_effect_is_legal_for_the_scene_and_spare_is_not_an_effect(baked):
    for row in baked["document"]["rows"]:
        allowed = bake_meta.NPC_EFFECTS if row["scene"] == "npc" else bake_meta.FIGHT_EFFECTS
        assert row["effect"] in allowed, row["id"]
    assert "spare" not in bake_meta.EFFECTS
    assert "spare" not in baked["document"]["effects"]


def test_a_fight_option_moves_the_effect_its_pool_belongs_to(baked):
    """Soften reads the weak pool, nudge the neutral pool, setback the strong pool (spec 19 section 6)."""
    for row in baked["document"]["rows"]:
        if row["scene"] != "fight":
            continue
        fallback = row["fallback"]
        assert fallback["source"] == "talk_cards"
        assert fallback["pool"] == bake_meta.EFFECT_TO_POOL[row["effect"]]
        assert row["effect"] == fallback["effect"]


# ----------------------------------------------------------------- --check accepts the shipped file

def test_the_committed_file_passes_its_own_check():
    assert bake_meta.check_file(BAKE_FILE) == 0


def test_the_committed_file_is_ascii_with_no_long_dash():
    raw = open(BAKE_FILE, "rb").read()
    assert max(raw) <= 127, "non ascii byte in the bake file"
    text = raw.decode("ascii")
    for dash in ("\u2013", "\u2014", "\u2015", "\u2212"):
        assert dash not in text
    assert "MODEL_API_KEY" not in text and "https://" not in text and "www." not in text


def test_every_row_carries_the_four_d5_fields_and_its_fallback(baked):
    for row in baked["document"]["rows"]:
        for field in ("model", "request_hash", "created_at", "fallback", "source"):
            assert row.get(field), "%s: %s is empty" % (row["id"], field)
        assert len(row["request_hash"]) == 64
        assert row["request"]["system_chars"] > 2000
        assert (row["created_at"].endswith("Z"))


# ----------------------------------------------------------------- --check refuses what the card names

def test_check_refuses_a_line_over_28_characters(copy_of_the_file):
    def mutate(document):
        document["rows"][0]["text"] = ["THIS LINE IS MUCH TOO LONG FOR THE BOX BY ANY MEASURE"]

    assert bake_meta.check_file(copy_of_the_file(mutate)) > 0


def test_check_refuses_an_effect_outside_the_enum(copy_of_the_file):
    def mutate(document):
        document["rows"][0]["effect"] = "spare"

    assert bake_meta.check_file(copy_of_the_file(mutate)) > 0


def test_check_refuses_a_fallback_id_that_is_not_a_talk_card(copy_of_the_file):
    def mutate(document):
        fight = next(row for row in document["rows"] if row["scene"] == "fight")
        fight["fallback"]["card"] = "morgan"
        fight["fallback"]["id"] = "morgan:weak:0"

    assert bake_meta.check_file(copy_of_the_file(mutate)) > 0


def test_check_refuses_a_url_or_a_key_name(copy_of_the_file):
    def mutate(document):
        document["bake"]["note"] = "see https://api.meta.ai/v1 with MODEL_API_KEY"

    assert bake_meta.check_file(copy_of_the_file(mutate)) > 0


def test_check_refuses_a_hash_that_does_not_recompute(copy_of_the_file):
    def mutate(document):
        document["rows"][0]["request_hash"] = "0" * 64

    assert bake_meta.check_file(copy_of_the_file(mutate)) > 0


def test_check_refuses_an_offline_row_that_claims_a_live_answer(copy_of_the_file):
    def mutate(document):
        document["rows"][0]["source"] = "live"
        document["rows"][0]["network"] = True
        document["rows"][0]["reason"] = ""

    assert bake_meta.check_file(copy_of_the_file(mutate)) > 0


def test_check_refuses_a_dropped_option_row(copy_of_the_file):
    def mutate(document):
        document["rows"].pop(0)

    assert bake_meta.check_file(copy_of_the_file(mutate)) > 0


def test_check_refuses_a_missing_file(tmp_path):
    assert bake_meta.check_file(str(tmp_path / "not_there.json")) > 0


# ----------------------------------------------------------------- the live branch, with the door replaced

def test_the_offline_bake_never_calls_the_client(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("the offline bake must not call the model client")

    monkeypatch.setattr(bake_meta, "call_model", refuse)
    document, _mode, state, _skipped, _units = bake_meta.run_bake(offline=True)
    assert state["calls"] == 0
    assert all(row["source"] == "fallback" for row in document["rows"])


def _live_document(monkeypatch, answer):
    monkeypatch.setenv("MODEL_API_KEY", "dummy-not-a-real-key")
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.setenv("PP_AI_BACKEND", "meta")
    monkeypatch.setattr(bake_meta, "call_model", lambda messages, schema=None, sleep=None: answer)
    document, _mode, state, _skipped, _units = bake_meta.run_bake(offline=False)
    return document, state


def test_a_valid_live_answer_is_written_as_live_and_keeps_its_fallback(monkeypatch):
    answer = {"text": ["IT SNIFFS YOUR HAND."], "mood": "warm", "effect": "soften",
              "hint": "THE ROPE."}
    document, state = _live_document(monkeypatch, answer)
    live = [row for row in document["rows"] if row["source"] == "live"]
    assert state["calls"] == len(document["rows"])
    assert live, "a valid answer must be written as live"
    assert all(row["network"] is True for row in live)
    assert all(row["fallback"]["id"] for row in live), "a live row still records what it shadows"
    assert document["bake"]["live"] == len(live)


def test_a_refused_answer_falls_back_with_the_reason_recorded(monkeypatch):
    answer = {"text": ["it is too quiet in here"], "mood": "happy", "effect": "soften", "hint": ""}
    document, _state = _live_document(monkeypatch, answer)
    assert all(row["source"] == "fallback" for row in document["rows"])
    assert all(row["reason"].startswith("refused:") for row in document["rows"])
    assert document["bake"]["live"] == 0


def test_an_npc_row_refuses_an_effect_that_only_a_fight_allows(monkeypatch):
    answer = {"text": ["THE LEDGER BALANCES."], "mood": "calm", "effect": "soften", "hint": ""}
    document, _state = _live_document(monkeypatch, answer)
    npc = [row for row in document["rows"] if row["scene"] == "npc" and row["source"] == "fallback"]
    assert npc, "spec 19 section 6 rule 2 refuses soften in the npc scene"
    assert all("not legal in the npc scene" in row["reason"] for row in npc)


# ----------------------------------------------------------------- small rules

def test_wrapping_uppercases_and_never_breaks_a_word():
    glyphs = bake_meta.load_glyphs()
    lines = bake_meta.wrap_alphabet('* "The watch is long. That is all."', glyphs)
    assert lines == ["THE WATCH IS LONG. THAT IS", "ALL."]
    assert bake_meta.wrap_alphabet("go on then", glyphs) == ["GO ON THEN"]


def test_wrapping_refuses_a_character_the_font_cannot_draw():
    glyphs = bake_meta.load_glyphs()
    with pytest.raises(bake_meta.BakeError):
        bake_meta.wrap_alphabet("a line with a \u00e9 in it", glyphs)


def test_the_system_text_is_measured_from_the_spec():
    text = bake_meta.load_system_text()
    assert len(text) == 2408, "spec 19 section 3 measures 2409 including the final newline"
    assert text.startswith("You are the voice of PRIMORDIAL PARADOX")
    assert text.endswith("Return only the JSON object.")


def test_the_effects_table_is_the_spec_enum_and_maps_to_existing_pool_names():
    assert bake_meta.EFFECTS == ("none", "nudge", "soften", "setback", "end")
    assert set(bake_meta.EFFECT_TO_POOL) == {"soften", "nudge", "setback"}
    assert set(bake_meta.EFFECT_TO_POOL.values()) <= {"weak", "neutral", "strong"}
