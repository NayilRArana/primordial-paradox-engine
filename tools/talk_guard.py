"""talk_guard: the one profanity check, per specs/19-llm-talk.md section 7 layer D and D6 Q8 (card R49).

The shape of the rule, in order of how much it matters:

1. The check is a lowercase substring scan over the token list in data\\talk_profanity.json. There is no
   regex, no word boundary logic, and no second input: the file holds data, the file cannot change how the
   check runs. load_tokens reads exactly the "words" key and ignores every other field a hand edited copy
   could add, so the data-is-never-instructions rule holds mechanically, not by promise.
2. A hit refuses the WHOLE reply. This module answers one question, did the text contain a listed word,
   and names the word. Dropping the reply and showing the card pool fallback line is the caller's job
   (the bake tool, R29 META-BAKE, and the talk director, R30 TALK-BAKED).
3. The guard is never run on a hand written talk card. The authored lines in data\\talk_cards.json are the
   fallback pool the guard itself promotes, and a guard that refused them would refuse the safety net. That
   is why the shipped token list is curated: tests\\test_talk_guard.py asserts every string in the hand
   written card file passes the check, so even a caller that misuses the guard cannot refuse authored
   content. A file the game never reads and no GML names is why data\\talk_profanity.json sits in
   tools\\sync_data.py's NOT_RUNTIME: this guard is a bake time tool check, the shipped bundle carries no
   list (spec 19 check 12.5, the game reads the bake and nothing else).

Usage:
    python tools/talk_guard.py            # prints the token count and a clean and dirty probe line
    from talk_guard import load_tokens, profane_hit, reply_refused   # from tools/ on sys.path
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "data", "talk_profanity.json")

MIN_TOKENS = 20  # spec 19 section 7: fewer than this, or a missing file, stops the bake loudly


class ProfanityListError(Exception):
    """The list is missing, too short, or holds a token that is not a bare lowercase word."""


def load_tokens(path: str = DATA_FILE) -> tuple:
    """Read the guard's only input: the words list, validated. Extra fields in the file are ignored.

    Every token must be [a-z]+ so the substring check below has nothing to escape from: a token carrying
    a regex metacharacter, a space or an uppercase letter is refused here, at the load, rather than
    silently bending how the check runs.
    """
    if not os.path.isfile(path):
        raise ProfanityListError("profanity list missing: %s" % path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ProfanityListError("profanity list is not valid JSON: %s" % exc)
    words = doc.get("words") if isinstance(doc, dict) else None
    if not isinstance(words, list):
        raise ProfanityListError("profanity list has no words array: %s" % path)
    if len(words) < MIN_TOKENS:
        raise ProfanityListError("profanity list holds %d tokens, the floor is %d (spec 19 check 6)"
                                 % (len(words), MIN_TOKENS))
    for token in words:
        if not isinstance(token, str) or token != token.lower() or not token.isalpha() \
                or not all("a" <= c <= "z" for c in token):
            raise ProfanityListError("profanity token is not a bare lowercase a-z word: %r" % token)
    return tuple(words)


def profane_hit(text: str, tokens: tuple):
    """Return the first token this text contains, or None. Pure, case insensitive, substring only."""
    low = text.lower()
    for token in tokens:
        if token in low:
            return token
    return None


def reply_refused(lines, tokens: tuple):
    """True, plus the offending token, when ANY line of a model reply carries a listed word.

    A reply is an array of at most 4 strings (spec 19 Q1); a hit on one line refuses the whole reply,
    which is what makes the check one boolean for the caller, not one boolean per line.
    """
    if isinstance(lines, str):
        lines = [lines]
    for line in lines:
        token = profane_hit(str(line), tokens)
        if token is not None:
            return True, token
    return False, None


def main() -> int:
    tokens = load_tokens()
    print("talk_guard: %d tokens from %s" % (len(tokens), os.path.relpath(DATA_FILE, ROOT)))
    clean = "THE HOUND WANTS A SMOKE AND THE WATCH TO END."
    dirty = "YOU OLD FUCK, MOVE ASIDE."
    print("clean line refused:", reply_refused([clean], tokens)[0])
    print("dirty line refused:", reply_refused([dirty], tokens)[0],
          "by token:", reply_refused([dirty], tokens)[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
