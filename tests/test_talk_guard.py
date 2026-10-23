"""Tests for tools/talk_guard.py (card R49 TALK-PROFANITY).

The three claims the card makes about the guard, each pinned here:
1. A clean line passes and a line carrying a listed word is refused whole (the substring rule of
   specs/19-llm-talk.md section 7 layer D, lowercase, case insensitive on the text side).
2. The file is data, never instructions: the load reads the words list and nothing else, so a field a
   hand edited copy adds cannot change how the check runs, and a missing file, a short file, or a token
   that is not a bare lowercase word stops the load loudly (the same rule the bake inherits).
3. The check never runs on a hand written talk card, and the proof is the curation: every string in
   data/talk_cards.json, and every authored dialogue line, passes the guard as shipped. A token that
   ate an authored word (ass, crap, tit, fag) would fail this test and must leave the list, not the card.
"""

from __future__ import annotations

import json
import os

import pytest

import talk_guard
from talk_guard import ProfanityListError, load_tokens, profane_hit, reply_refused

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "data", "talk_profanity.json")


# ----------------------------------------------------------------- the file itself

def test_file_names_its_source_and_licence():
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["kind"] == "talk_profanity"
    assert "corpora" in doc["source"]
    assert doc["licence"].startswith("CC0")
    prov = doc["provenance"]
    assert prov["url"].startswith("https://")
    assert len(prov["read_at"]) == len("2026-10-22")
    assert len(prov["source_sha256"]) == 64


def test_tokens_lowercase_sorted_at_least_twenty():
    tokens = load_tokens()
    assert len(tokens) >= 20
    assert list(tokens) == sorted(tokens)
    for token in tokens:
        assert token == token.lower()
        assert token.isalpha() and all("a" <= c <= "z" for c in token)


def test_no_dash_characters_and_no_non_ascii_byte():
    raw = open(DATA_FILE, "rb").read()
    assert max(raw) <= 127, "non ascii byte in the list file"
    text = raw.decode("ascii")
    assert "\u2013" not in text and "\u2014" not in text
    assert "--" not in text


# ----------------------------------------------------------------- the guard rule

def test_clean_line_passes():
    tokens = load_tokens()
    clean = ["THE HOUND WANTS A SMOKE AND THE WATCH TO END.",
             "You are not on the list.",
             "Pass, and keep moving."]
    for line in clean:
        assert profane_hit(line, tokens) is None
        refused, _ = reply_refused([line], tokens)
        assert refused is False


def test_planted_line_is_refused_whole():
    tokens = load_tokens()
    planted = ["YOU OLD FUCK, MOVE ASIDE.",
               "the bastard hound will pay",          # case: the text is lowercased, the check is one rule
               "THAT SHIT AGAIN?",
               "say it to my face, asshole"]
    for line in planted:
        refused, token = reply_refused([line], tokens)
        assert refused is True
        assert token in line.lower()


def test_one_dirty_line_refuses_the_whole_reply():
    tokens = load_tokens()
    reply = ["THE HOUND SHIFTS HIS WEIGHT,", "ONE PAW OVER THE BREACH,",
             "AND WANTS A GODDAMN SMOKE.", "ASK HIM FAIR."]
    refused, token = reply_refused(reply, tokens)
    assert refused is True
    assert token == "goddamn"


def test_guard_is_pure():
    tokens = load_tokens()
    first = profane_hit("you old fuck", tokens)
    assert first == profane_hit("you old fuck", tokens)
    assert profane_hit("", tokens) is None


# ----------------------------------------------------------------- data is never instructions

def test_extra_fields_are_ignored_by_the_load(tmp_path):
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["pattern"] = ".*"            # a field that must not bend the check
    doc["case_sensitive"] = True
    bad_path = tmp_path / "talk_profanity.json"
    with open(bad_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    assert load_tokens(str(bad_path)) == load_tokens()   # same tuple, guard unchanged


def test_missing_file_stops_the_load(tmp_path):
    with pytest.raises(ProfanityListError):
        load_tokens(str(tmp_path / "absent.json"))


def test_short_file_stops_the_load(tmp_path):
    path = tmp_path / "short.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"kind": "talk_profanity", "words": ["fuck"]}, fh)
    with pytest.raises(ProfanityListError):
        load_tokens(str(path))


def test_token_that_is_not_a_bare_lowercase_word_stops_the_load(tmp_path):
    for bad in ["F4CK", "bull.shit", "bad regex.*", "", "a b"]:
        path = tmp_path / "bad.json"
        words = ["fuck", "shit", bad] + ["token%02d" % n for n in range(17)]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"kind": "talk_profanity", "words": words}, fh)
        with pytest.raises(ProfanityListError):
            load_tokens(str(path))


# ----------------------------------------------------------------- the hand written cards never meet it

def _all_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from _all_strings(item)
    elif isinstance(node, dict):
        for value in node.values():
            yield from _all_strings(value)


def test_guard_passes_every_hand_written_talk_card_string():
    """The curated list eats no authored word. This is the proof the guard can never refuse the
    hand written pool it is meant to protect (the card's third clause)."""
    tokens = load_tokens()
    for rel in ["data/talk_cards.json", "data/dialogue/all.json", "data/intro_text.json",
                "knowledge/GATE-DIALOGUE.md"]:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        if rel.endswith(".json"):
            with open(path, "r", encoding="utf-8") as fh:
                blob = " ".join(_all_strings(json.load(fh)))
        else:
            blob = open(path, "r", encoding="utf-8").read()
        # line by line: a whole blob could join two safe words across a boundary and still be safe,
        # but per line is exactly what the guard receives.
        for line in blob.splitlines():
            hit = profane_hit(line, tokens)
            assert hit is None, "%s carries guarded token %r: %r" % (rel, hit, line[:80])
