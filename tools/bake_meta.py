"""bake_meta: write `data/meta_bake.json` ahead of time, offline and total (card R29, spec 19, D5).

Why this tool exists
====================
`knowledge/GAMEDEV-DECISIONS-2026-10-22.md` D5 says the shipped game makes no network call and holds no
key, and every Meta model output the game shows was baked before the build by a tool into a plain data
file. This is that tool for spec 19's talk path: for every fight phase the talk command can reach and for
the two NPCs D6 Q5 approved (Morgan the gate sentry, Nye the dock office clerk) it writes three reply
options, the effect each option is allowed to move, and a hint line, in the shape of spec 19 section 4
(1 to 4 lines of at most 28 characters, one mood of five, one effect of five, a hint of at most 28).

Every row records what D5 asks for: `model`, `request_hash`, `created_at` and `fallback`, where
`fallback` is the hand written row the row shadows. The fallback is never invented here:

  fight rows   the card's own pool line in `data\\talk_cards.json`, chosen by the effect the option moves
               (soften reads the weak pool, nudge the neutral pool, setback the strong pool), uppercased
               into the 46 glyph alphabet and wrapped to at most 28 columns. Nothing else changes.
  npc rows     the hand written line bank in `knowledge\\GATE-DIALOGUE.md` (R38), a bank line id per turn,
               already inside the alphabet, so it is copied verbatim and checked byte for byte.

A row whose source is `fallback` says so (`"source": "fallback"`, `"network": false`) and carries the
reason it fell back (`"reason"`: no key, no network, a refusal, a cap). A row never claims a live call it
did not make; R43 REVIEW-META-BAKE checks exactly that, and a fallback row's `text`, `mood`, `effect` and
`hint` must be its fallback's four fields byte for byte, so a fallback row cannot show words no fallback
holds (`--check` compares them, R43 B2).

The `bake` block is derived from the calls, not from the environment (R43 B1)
==================================================================================
`resolve_mode()` reads what the environment permits; it is never evidence that a call happened. The block
is built by `bake_header()` from the run's own tally: `live` counts the validated answers written into
rows, and each one is either `live_wire` (answered over the network now) or `live_cached` (read back from
the recorded cache). So:

    mode live      at least one validated answer crossed the network this run, and `network` is true
    mode replay    the rows are validated answers read back from the recorded cache, `network` false
    mode offline   no row is live, whatever the environment allowed, `network` false

and the note always starts with `live:`, `cached:` or `offline:` to match. A run whose every call missed
the cache (a replay with nothing recorded) or whose key is revoked or spent writes mode offline, network
false and an offline note, not a live header over 0 live rows. A validated answer whose transport verdict
is missing, or which the door places neither on the wire nor in the cache, stops the bake rather than being
labelled from a guess, so `live` always equals `live_wire` plus `live_cached`.

Three modes, and none of them blocks
====================================
    python tools\\bake_meta.py --offline    # every row is the hand written fallback, no key, no network
    python tools\\bake_meta.py              # try the live call, fall back row by row, never fail the bake
    python tools\\bake_meta.py --check      # re-read the file and refuse anything off contract

No key, no network, a refusal or a spent call budget writes the fallback for that row and says so. The
bake never leaves a hole: a missing key is a labelled file, not an error, because a hole in the bake is a
box that says nothing on a judge's laptop. A missing or too short `data\\talk_profanity.json` is the one
loud stop, because spec 19 section 7 layer D says so.

The key is read from the environment by `tools\\meta_client.py`, never here, and never printed. This file
holds no endpoint and no credential: `--check` refuses the bake if it finds a URL or a key name in it.

What --check refuses
====================
    1. a line over 28 characters, more than 4 lines, an empty line, or a character outside the font
       (read from `data\\ui_layouts.json`, not typed here) or outside spec 19 section 4's pattern;
    2. a mood outside the five, or an effect outside spec 19's enum, or `end` in a fight, or soften,
       nudge or setback in chat (spec 19 section 6 rule 2);
    3. a fallback id that does not resolve: a talk_cards id (`<card>:<pool>:<index>`) whose card is not in
       `data\\talk_cards.json` or whose pool or index does not exist, or a gate_dialogue id that is not a
       line id in `knowledge\\GATE-DIALOGUE.md`, and either kind whose stored text is not the text that id
       really holds;
    4. a row missing `model`, `request_hash`, `created_at`, `fallback`, `source` or `text`, a
       `request_hash` that does not recompute from the row's stored request echo, a duplicate id, a row
       whose scene and effects disagree, an incomplete option set, or a card phase the data can reach that
       the bake quietly dropped;
    5. a key name, an endpoint, a URL, or an unvalidated model answer, anywhere in the file;
    6. a bake block that claims more than its rows did: mode live or network true over zero live rows, an
       offline flag that disagrees with the network flag, or a note that does not begin with the run's own
       word (`live:`, `cached:` or `offline:`); and a row labelled fallback whose shown text, mood, effect
       or hint is not its fallback's, or a fallback reason that names none of the four causes (R43 B1, B2).

Usage
    python tools\\bake_meta.py --offline
    python tools\\bake_meta.py --check
    python tools\\bake_meta.py               (live: needs MODEL_API_KEY or META_API_KEY in the environment)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import talk_guard  # noqa: E402  (tools/ is this file's own directory, and the guard is R49's one check)

DATA = os.path.join(ROOT, "data")
OUT_FILE = os.path.join(DATA, "meta_bake.json")
SPEC_FILE = os.path.join(ROOT, "specs", "19-llm-talk.md")
CARDS_FILE = os.path.join(DATA, "talk_cards.json")
ENEMIES_FILE = os.path.join(DATA, "enemies", "all.json")
DIALOGUE_FILE = os.path.join(DATA, "dialogue", "all.json")
UI_FILE = os.path.join(DATA, "ui_layouts.json")
GATE_FILE = os.path.join(ROOT, "knowledge", "GATE-DIALOGUE.md")

FORMAT = 1
KIND = "meta_bake"
RULE = ("specs/19-llm-talk.md sections 2 to 11 and D5 in knowledge/GAMEDEV-DECISIONS-2026-10-22.md: "
        "written by tools/bake_meta.py only, never by hand, and the game reads this file and nothing else")

MOODS = ("calm", "guarded", "rattled", "warm", "angry")
EFFECTS = ("none", "nudge", "soften", "setback", "end")
FIGHT_EFFECTS = ("none", "nudge", "soften", "setback")
NPC_EFFECTS = ("none", "end")
# spec 19 section 6: soften is the weak topic row (+20), nudge the neutral row (+5), setback the hostile
# row (-10). The pool names are data/talk_cards.json's own, so no name is invented here.
EFFECT_TO_POOL = {"soften": "weak", "nudge": "neutral", "setback": "strong"}
# spec 19 section 4: on a missing or out of range mood the game derives one from the effect. This is that
# derivation, used for every fallback row.
EFFECT_TO_MOOD = {"soften": "warm", "nudge": "calm", "none": "guarded", "setback": "angry", "end": "calm"}
OPTION_EFFECTS = ("soften", "nudge", "setback")
OPTIONS_PER_UNIT = 3

MAX_LINE = 28
MAX_LINES = 4
MAX_LAST_REPLY = 112
# spec 19 section 10 budget 3: one bake of the demo set is 40 replies, and 18 rows is this card's set.
MAX_CALLS = 40
REPLY_PATTERN = re.compile(r"^[A-Z0-9 .,:!?'()]+$")
HINT_PATTERN = re.compile(r"^[A-Z0-9 .,:!?'()]*$")
# spec 19 section 7 layer D: a reply carrying one of these loses its text to the card pool line.
ECHO_PHRASES = ("as an ai", "language model", "system prompt", "my instructions", "i cannot", "i'm sorry")
DIGIT_RUN = re.compile(r"\d{3,}")
LINK_MARKS = ("http", "www.", "@")
# What must never appear in the bake file (D5: no endpoint, no credential, and R43 reads the file itself).
FORBIDDEN_IN_FILE = ("http://", "https://", "www.", "api.", "model_api_key", "meta_api_key", "api_key",
                     "authorization", "bearer ", "sk-")
# R43 B1: the header's mode, and the first word of its note. A note that does not name the run is refused,
# so "mode live" cannot stand over 0 live rows or over a run that never left the machine.
MODE_NOTES = {"live": "live:", "offline": "offline:", "replay": "cached:"}
# R43: a fallback row's reason must name one of these causes and then say what happened, so "because"
# cannot stand in for a reason.
REASON_PREFIXES = ("offline:", "no live answer:", "refused:", "call budget ")
NPCS = (
    {
        "id": "morgan",
        "name": "Morgan",
        "place": "southampton_dock",
        "turns": (("M10", "none", "H1"), ("M11", "none", "H2"), ("M12", "end", "")),
    },
    {
        "id": "nye",
        "name": "Nye",
        "place": "quay_dock_office",
        "turns": (("N7", "none", "H3"), ("N8", "none", "H4"), ("N10", "end", "")),
    },
)


class BakeError(Exception):
    """An input the bake cannot start without, or a hand written row that cannot be read."""


# ---------------------------------------------------------------- inputs

def safe_relpath(path):
    """The path relative to the repo for a message, or the path itself across drives (C: vs D:)."""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return str(path)


def load_json(path):
    if not os.path.isfile(path):
        raise BakeError("missing input: %s" % os.path.relpath(path, ROOT))
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except ValueError as exc:
        raise BakeError("%s is not valid JSON: %s" % (os.path.relpath(path, ROOT), exc))


def load_text(path):
    if not os.path.isfile(path):
        raise BakeError("missing input: %s" % os.path.relpath(path, ROOT))
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def load_glyphs():
    """The font's own alphabet, from data/ui_layouts.json (spec 19 section 4 reads it, never types it)."""
    layout = load_json(UI_FILE)
    glyphs = (layout.get("font") or {}).get("glyphs")
    if not isinstance(glyphs, str) or len(glyphs) < 40:
        raise BakeError("data/ui_layouts.json font.glyphs is missing or too short")
    return glyphs


def load_system_text():
    """The byte identical system message, measured out of spec 19 section 3 rather than retyped here.

    The fenced block is taken verbatim, indentation and all, because it is the text spec 19 measures:
    2409 characters counting the final newline, 2408 as this string (the reference copies in section 10
    use the 2409 figure). A change here is a `sys_version` bump in spec 16 section 8, which invalidates
    every baked entry at once, so the count is printed by `report()` and stored in the bake block.
    """
    text = load_text(SPEC_FILE)
    match = re.search(r"The system text below measures.*?```\n(.*?)\n```", text, re.S)
    if not match:
        raise BakeError("specs/19-llm-talk.md section 3 no longer holds the fenced system text")
    body = match.group(1)
    if not 1000 < len(body) < 8000:
        raise BakeError("the system text measured %d characters, expected about 2409" % len(body))
    return body


def load_gate_bank():
    """Line bank ids and the two ready to paste character blocks, read from knowledge/GATE-DIALOGUE.md."""
    text = load_text(GATE_FILE)
    bank = {}
    for match in re.finditer(r"^\|\s*([MN]\d+|[AH]\d[A-Z]?)\s*\|\s*`([^`]+)`\s*\|", text, re.M):
        bank[match.group(1)] = match.group(2).strip()
    blocks = {}
    for chunk in re.findall(r"```json\n(.*?)```", text, re.S):
        try:
            block = json.loads(chunk)
        except ValueError:
            continue
        if isinstance(block, dict) and block.get("id") in ("morgan", "nye"):
            blocks[block["id"]] = block
    if len(bank) < 30:
        raise BakeError("knowledge/GATE-DIALOGUE.md holds %d bank rows, expected 32" % len(bank))
    if set(blocks) != {"morgan", "nye"}:
        raise BakeError("knowledge/GATE-DIALOGUE.md holds no character block for both NPCs")
    return bank, blocks


def load_cards():
    doc = load_json(CARDS_FILE)
    cards = doc.get("cards")
    if not isinstance(cards, list) or not cards:
        raise BakeError("data/talk_cards.json holds no cards")
    return doc, {card["id"]: card for card in cards if isinstance(card, dict) and card.get("id")}


def load_enemies():
    doc = load_json(ENEMIES_FILE)
    enemies = doc.get("enemies")
    if not isinstance(enemies, list):
        raise BakeError("data/enemies/all.json holds no enemies array")
    return {enemy["id"]: enemy for enemy in enemies if isinstance(enemy, dict) and enemy.get("id")}


def load_dialogue():
    doc = load_json(DIALOGUE_FILE)
    rows = doc.get("entries") or doc.get("dialogue")
    if not isinstance(rows, list):
        for key in ("entries", "dialogue", "rows"):
            if isinstance(doc.get(key), list):
                rows = doc[key]
                break
    if not isinstance(rows, list):
        raise BakeError("data/dialogue/all.json holds no entry list")
    return {row["id"]: row for row in rows if isinstance(row, dict) and row.get("id")}


# ---------------------------------------------------------------- text rules

def strip_marker(line):
    """Spec 05 writes `* "Line."`; code prepends the marker, so it is stripped before the model sees it."""
    out = str(line or "").strip()
    while out.startswith("*"):
        out = out[1:].strip()
    return out.replace('"', "").strip()


def wrap_alphabet(text, glyphs, what="line"):
    """One hand written sentence into the reply shape: uppercase, alphabet only, greedy 28 column wrap."""
    flat = " ".join(strip_marker(text).split())
    if not flat:
        raise BakeError("%s is empty" % what)
    upper = flat.upper()
    bad = sorted({char for char in upper if char not in glyphs})
    if bad:
        raise BakeError("%s holds characters the font cannot draw: %r" % (what, "".join(bad)))
    if not REPLY_PATTERN.match(upper):
        raise BakeError("%s holds a character spec 19 section 4 refuses: %r" % (what, upper))
    lines = []
    current = ""
    for word in upper.split(" "):
        if len(word) > MAX_LINE:
            raise BakeError("%s holds a word longer than %d characters: %r" % (what, MAX_LINE, word))
        candidate = word if not current else current + " " + word
        if len(candidate) <= MAX_LINE:
            current = candidate
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    if len(lines) > MAX_LINES:
        raise BakeError("%s needs %d lines, the shape allows %d" % (what, len(lines), MAX_LINES))
    return lines


def hint_from_topic(topic, glyphs):
    """A card's topic as a hint: a noun phrase the character answers to, never a command (Q9)."""
    text = " ".join(str(topic or "").split()).upper()
    if not text:
        return ""
    text = text.rstrip(".") + "."
    if len(text) > MAX_LINE:
        return ""
    bad = {char for char in text if char not in glyphs or not HINT_PATTERN.match(char)}
    if bad:
        return ""
    return text


def resolve_pool(card, pool_name):
    """The hand written pool a fallback reads. Some cards write a pool as low/mid/high bands."""
    pools = card.get("pools") or {}
    pool = pools.get(pool_name)
    if isinstance(pool, list) and pool:
        return list(pool)
    if isinstance(pool, dict):
        for band in ("mid", "low", "high"):
            if isinstance(pool.get(band), list) and pool[band]:
                return list(pool[band])
    raise BakeError("card %s has no usable %s pool" % (card.get("id"), pool_name))


def talk_options_id(card, enemy):
    """The dialogue entry holding the three option lines, from the enemy row the card belongs to."""
    phase = card.get("phase") or ""
    if not phase:
        return enemy.get("talk_dialogue")
    for row in enemy.get("phases") or []:
        if isinstance(row, dict) and row.get("talk_phase") == phase:
            return row.get("talk_set")
    return None


# ---------------------------------------------------------------- reply validation (spec 19 sections 4, 6, 7)

def validate_reply(reply, scene, glyphs, tokens):
    """(True, []) for a reply the game could draw and act on, else (False, [problems])."""
    problems = []
    if not isinstance(reply, dict):
        return False, ["reply is not an object"]
    if set(reply) != {"text", "mood", "effect", "hint"}:
        return False, ["fields are %s, the shape is text, mood, effect, hint"
                       % ",".join(sorted(reply))]
    text = reply.get("text")
    if not isinstance(text, list) or not text:
        problems.append("text is not a non empty array")
    elif len(text) > MAX_LINES:
        problems.append("text holds %d lines, the shape allows %d" % (len(text), MAX_LINES))
    else:
        for line in text:
            problems.append(_line_problem(line, glyphs))
    mood = reply.get("mood")
    if mood not in MOODS:
        problems.append("mood %r is not one of %s" % (mood, ", ".join(MOODS)))
    effect = reply.get("effect")
    allowed = NPC_EFFECTS if scene == "npc" else FIGHT_EFFECTS
    if effect not in EFFECTS:
        problems.append("effect %r is not in the spec 19 enum" % (effect,))
    elif effect not in allowed:
        problems.append("effect %r is not legal in the %s scene" % (effect, scene))
    hint = reply.get("hint")
    if not isinstance(hint, str):
        problems.append("hint is not a string")
    elif len(hint) > MAX_LINE:
        problems.append("hint is %d characters, the shape allows %d" % (len(hint), MAX_LINE))
    elif not HINT_PATTERN.match(hint):
        problems.append("hint holds a character the font cannot draw: %r" % (hint,))
    problems.extend(_tone_problems(reply, tokens))
    problems = [problem for problem in problems if problem]
    return (not problems), problems


def _line_problem(line, glyphs):
    if not isinstance(line, str):
        return "text line is not a string"
    if not line:
        return "text line is empty"
    if len(line) > MAX_LINE:
        return "text line is %d characters, the shape allows %d" % (len(line), MAX_LINE)
    bad = sorted({char for char in line if char not in glyphs})
    if bad:
        return "text line holds characters the font cannot draw: %r" % ("".join(bad),)
    if not REPLY_PATTERN.match(line):
        return "text line holds a character spec 19 section 4 refuses: %r" % (line,)
    return ""


def _tone_problems(reply, tokens):
    """Spec 19 section 7 layer D: profanity, links, digit runs, and the echo list."""
    problems = []
    blob = " ".join([str(reply.get("text") or ""), str(reply.get("hint") or "")])
    hit, token = talk_guard.reply_refused(reply.get("text") or [], tokens)
    if hit:
        problems.append("text carries the listed token %r" % (token,))
    low = blob.lower()
    for mark in LINK_MARKS:
        if mark in low:
            problems.append("reply carries a link mark %r" % (mark,))
    if DIGIT_RUN.search(blob):
        problems.append("reply carries a run of three or more digits")
    for phrase in ECHO_PHRASES:
        if phrase in low:
            problems.append("reply carries the echo phrase %r" % (phrase,))
    return problems


# ---------------------------------------------------------------- the bake plan

def character_block(card, enemy):
    """Spec 19 section 3: only these eight fields travel, and no field is invented here."""
    return {
        "id": card["id"],
        "name": enemy["name"],
        "voice": card.get("voice", ""),
        "wants": list(card.get("wants") or []),
        "fears": list(card.get("fears") or []),
        "weak_topics": [{"topic": row.get("topic", "")} for row in card.get("weak_topics") or []],
        "strong_topics": [{"topic": row.get("topic", "")} for row in card.get("strong_topics") or []],
        "phase_note": card.get("phase_note", ""),
    }


def fight_plan(cards, enemies, dialogue):
    """(units, skipped): one unit per talk card phase the data can actually reach, with its option lines."""
    units = []
    skipped = []
    for card_id in sorted(cards):
        card = cards[card_id]
        enemy = enemies.get(card.get("enemy") or card_id)
        if enemy is None:
            skipped.append({"card": card_id,
                            "reason": "no row in data/enemies/all.json, so spec 19 section 3's character "
                                      "block would have to invent a name"})
            continue
        options_id = talk_options_id(card, enemy)
        entry = dialogue.get(options_id) if options_id else None
        lines = (entry or {}).get("lines") or []
        if len(lines) < OPTIONS_PER_UNIT:
            skipped.append({"card": card_id,
                            "reason": "no dialogue entry with %d option lines (looked for %r)"
                                      % (OPTIONS_PER_UNIT, options_id)})
            continue
        units.append({"card": card, "enemy": enemy, "options_id": options_id,
                      "option_lines": [strip_marker(line) for line in lines[:OPTIONS_PER_UNIT]]})
    return units, skipped


def npc_plan(bank, blocks):
    units = []
    for npc in NPCS:
        block = blocks[npc["id"]]
        for index, (line_id, effect, hint_id) in enumerate(npc["turns"], start=1):
            if line_id not in bank:
                raise BakeError("knowledge/GATE-DIALOGUE.md holds no bank row %s" % line_id)
            if hint_id and hint_id not in bank:
                raise BakeError("knowledge/GATE-DIALOGUE.md holds no hint row %s" % hint_id)
            units.append({"npc": npc, "block": block, "turn": index, "line_id": line_id,
                          "effect": effect, "hint_id": hint_id})
    return units


def build_request(kind, model, system, character, scene, player_line):
    """The stored echo and the hash over it: enough to rebuild the exact request, small enough to keep."""
    system_sha = hashlib.sha256(system.encode("utf-8")).hexdigest()
    echo = {"system_sha256": system_sha, "system_chars": len(system), "character": character,
            "scene": scene, "player_line": player_line}
    material = json.dumps({"kind": kind, "model": model, "request": echo},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return echo, hashlib.sha256(material.encode("utf-8")).hexdigest()


def render_messages(system, character, scene, player_line):
    """Three blocks, one message, in the fixed order spec 19 section 3 fixes."""
    user = "<character>\n%s\n</character>\n<scene>\n%s\n</scene>\n<player_line>\n%s\n</player_line>" % (
        json.dumps(character, sort_keys=True), json.dumps(scene, sort_keys=True), player_line)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


TALK_REPLY_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Primordial Paradox LLM talk reply",
    "type": "object",
    "required": ["text", "mood", "effect", "hint"],
    "additionalProperties": False,
    "properties": {
        "text": {"type": "array", "minItems": 1, "maxItems": MAX_LINES,
                 "items": {"type": "string", "minLength": 1, "maxLength": MAX_LINE,
                           "pattern": "^[A-Z0-9 .,:!?'()]+$"}},
        "mood": {"enum": list(MOODS)},
        "effect": {"enum": list(EFFECTS)},
        "hint": {"type": "string", "maxLength": MAX_LINE, "pattern": "^([A-Z0-9 .,:!?'()]*)$"},
    },
}


def row_base(row_id, scene, request_echo, request_hash, model, stamp):
    return {"id": row_id, "scene": scene, "text": [], "mood": "", "effect": "", "hint": "",
            "model": model, "request_hash": request_hash, "created_at": stamp,
            "source": "fallback", "network": False, "reason": "", "request": request_echo}


def bake_row(base, reply, fallback, source, reason):
    row = dict(base)
    row.update({"text": list(reply["text"]), "mood": reply["mood"], "effect": reply["effect"],
                "hint": reply["hint"], "source": source, "reason": reason,
                "network": source == "live", "fallback": fallback})
    return row


def fallback_reply(text_lines, effect):
    return {"text": list(text_lines), "mood": EFFECT_TO_MOOD[effect], "effect": effect, "hint": ""}


# ---------------------------------------------------------------- one bake

def call_model(messages, schema, sleep=None, transport=None):
    """One call through tools/meta_client.py, the only door (spec 19 section 2).

    `transport` comes back filled with what the door did (`backend`, `mode`, `cached`, `network`), so
    the bake reports the transport that happened instead of the transport the environment permitted.
    """
    import meta_client
    return meta_client.chat_structured(messages, schema=schema, sleep=sleep, transport=transport)


def new_state():
    """The bake's own tally of what its calls did. Every header count is read from here."""
    return {"calls": 0, "live": 0, "live_wire": 0, "live_cached": 0,
            "failed": 0, "refused": 0, "capped": 0}


def attempt(reply_builder, base, fallback, mode, state, scene, glyphs, tokens):
    """(row, reason): the live answer when it validates, else the fallback, and never an exception."""
    if mode["offline"]:
        return bake_row(base, reply_builder(fallback), fallback, "fallback", mode["why"]), ""
    if state["calls"] >= MAX_CALLS:
        state["capped"] += 1
        return bake_row(base, reply_builder(fallback), fallback, "fallback",
                        "call budget %d spent" % MAX_CALLS), "cap"
    state["calls"] += 1
    transport = {}
    try:
        answer = call_model(render_messages(mode["system"], base["request"]["character"], scene,
                                          base["request"]["player_line"]), TALK_REPLY_SCHEMA,
                            transport=transport)
    except Exception as exc:  # noqa: BLE001 - any client failure is a labelled fallback, never a hole
        state["failed"] += 1
        return bake_row(base, reply_builder(fallback), fallback, "fallback",
                        "no live answer: %s" % str(exc)[:160]), "error"
    if not transport:
        # A validated answer whose provenance nobody recorded cannot be told from a cache read, and
        # the header would have to guess. R43 B1 is exactly that guess, so it stops instead.
        raise BakeError("the client returned an answer and no transport verdict (%s), so the bake "
                        "cannot say where it came from" % base["id"])
    ok, problems = validate_reply(answer, "npc" if scene.get("scene") == "npc" else "fight",
                                  glyphs, tokens)
    if not ok:
        state["refused"] += 1
        return bake_row(base, reply_builder(fallback), fallback, "fallback",
                        "refused: %s" % "; ".join(problems)[:200]), "refused"
    state["live"] += 1
    if transport.get("network"):
        state["live_wire"] += 1
    elif transport.get("cached"):
        state["live_cached"] += 1
    else:
        # A live row the door cannot place on the wire or in the cache would make the note a guess
        # again, one level down from R43 B1, so it stops the bake instead of being labelled.
        raise BakeError("the client said %s came from neither the wire nor the cache (%r), so the "
                        "bake cannot say what the answer was" % (base["id"], transport))
    return bake_row(base, answer, fallback, "live", ""), "live"


def build_rows(mode, state, glyphs, tokens, plans):
    """Every row of the bake, in spec 19 section 12's order: Morgan's chat, Nye's, then the fights."""
    stamp = utc_stamp()
    rows = []
    model = mode["model"]
    for unit in plans["npc"]:
        npc = unit["npc"]
        effect = unit["effect"]
        text = [plans["bank"][unit["line_id"]]]
        hint = plans["bank"][unit["hint_id"]] if unit["hint_id"] else ""
        fallback = {"source": "gate_dialogue", "id": "gate_dialogue:%s" % unit["line_id"],
                    "line_id": unit["line_id"], "text": text, "mood": EFFECT_TO_MOOD[effect],
                    "effect": effect, "hint": hint}
        scene = {"scene": "npc", "npc": npc["id"], "place": npc["place"], "turn": unit["turn"],
                 "mood": "guarded", "last_reply": plans["last_npc_reply"].get(npc["id"], ""),
                 "allowed": list(NPC_EFFECTS)}
        echo, digest = build_request("chat", model, mode["system"], unit["block"], scene, "")
        base = row_base("npc/%s/turn_%d" % (npc["id"], unit["turn"]), "npc", echo, digest, model, stamp)
        base.update({"npc": npc["id"], "card": "", "place": npc["place"], "option": unit["turn"],
                     "turn": unit["turn"]})
        row, _ = attempt(lambda fb: dict(fb, hint=hint), base, fallback, mode, state, scene, glyphs,
                         tokens)
        row["fallback"] = fallback
        rows.append(row)
        plans["last_npc_reply"][npc["id"]] = " ".join(text)[:MAX_LAST_REPLY]
    for unit in plans["fight"]:
        card = unit["card"]
        character = character_block(card, unit["enemy"])
        for index, effect in enumerate(OPTION_EFFECTS, start=1):
            pool = EFFECT_TO_POOL[effect]
            pool_lines = resolve_pool(card, pool)
            pool_index = (index - 1) % len(pool_lines)
            pool_text = pool_lines[pool_index]
            text = wrap_alphabet(pool_text, glyphs, "card %s %s pool line %d" % (card["id"], pool, pool_index))
            hint = hint_from_topic((card.get("weak_topics") or [{}])[0].get("topic", ""), glyphs) \
                if index == 1 else ""
            fallback = {"source": "talk_cards", "id": "%s:%s:%d" % (card["id"], pool, pool_index),
                        "card": card["id"], "pool": pool, "index": pool_index,
                        "source_text": strip_marker(pool_text), "text": text,
                        "mood": EFFECT_TO_MOOD[effect], "effect": effect, "hint": hint}
            scene = {"scene": "fight", "turn": index, "enemy_hp_band": "unhurt",
                     "player_hp_band": "steady", "mercy": (index - 1) * 20, "mood": "guarded",
                     "last_effect": "none", "last_reply": plans["last_fight_reply"].get(card["id"], ""),
                     "allowed": list(FIGHT_EFFECTS)}
            player_line = unit["option_lines"][index - 1]
            echo, digest = build_request("chat", mode["model"], mode["system"], character, scene,
                                         player_line)
            base = row_base("fight/%s/%d" % (card["id"], index), "fight", echo, digest, mode["model"],
                            stamp)
            base.update({"npc": "", "card": card["id"], "enemy": unit["enemy"]["id"],
                         "phase": card.get("phase", ""), "option": index, "turn": index,
                         "options_dialogue": unit["options_id"], "player_line": player_line})
            row, _ = attempt(lambda fb: dict(fb, hint=hint), base, fallback, mode, state, scene, glyphs,
                             tokens)
            row["fallback"] = fallback
            rows.append(row)
            plans["last_fight_reply"][card["id"]] = " ".join(text)[:MAX_LAST_REPLY]
    return rows


def utc_stamp():
    override = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if override.isdigit():
        return datetime.fromtimestamp(int(override), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_mode(offline):
    """offline, live, or a labelled reason not to call. Reads the key state, never the key.

    `live_allowed` says only that the environment permits a live call. It is never evidence that one
    happened: the header is built from `state`, the calls themselves (R43 B1).
    """
    import meta_client
    model = meta_client.model_for("chat")
    mode = {"offline": True, "why": "offline: --offline was asked for, so every row is the fallback",
            "model": model, "system": "", "backend": "", "live_allowed": False}
    if offline:
        return mode
    backend = meta_client.backend_name()
    mode["backend"] = backend
    if backend != "meta":
        mode["why"] = ("offline: PP_AI_BACKEND is %r, not meta, so no live Meta answer was asked "
                       "for" % backend)
        return mode
    if not meta_client.key_present():
        mode["why"] = ("offline: no key in the environment (%s), so every row is the fallback"
                       % " then ".join(meta_client.KEY_ENVS))
        return mode
    mode.update({"offline": False, "why": "", "live_allowed": True})
    return mode


def bake_header(mode, state, rows, fallback_rows, reasons, system):
    """The bake block, taken from what the calls did, never from what the environment allowed.

    `mode["live_allowed"]` only says a live call was permitted. Whether one happened is `state`, the
    rows' own provenance: a live row is a validated answer this bake wrote, `live_wire` the ones that
    crossed the network now, `live_cached` the ones served from the recorded cache. So a run whose
    every call missed the cache or failed is mode offline with a note that starts "offline:", and a
    run served from the cache is mode replay with a note that starts "cached:". R43 B1 measured the
    old block saying live and networked over 0 live rows, and this is the replacement.
    """
    live = state["live"]
    wire = state["live_wire"]
    cached = state["live_cached"]
    network = wire > 0
    if live == 0:
        kind = "offline"
        note = mode["why"] or (
            "offline: %d call(s) were made and none came back as a validated answer (%d failed, %d "
            "refused, %d over the call budget), so every row is the hand written fallback"
            % (state["calls"], state["failed"], state["refused"], state["capped"]))
    elif network:
        kind = "live"
        note = ("live: %d of %d rows are answers from the Meta client, each one schema validated "
                "before it was written" % (live, len(rows)))
        if cached:
            note += ", and %d of those were read back from the recorded cache" % cached
        if live < len(rows):
            note += "; the other %d are the hand written fallback" % (len(rows) - live)
    else:
        kind = "replay"
        note = ("cached: %d of %d rows are answers read back from the recorded cache, so no request "
                "left this machine" % (live, len(rows)))
        if live < len(rows):
            note += "; the other %d are the hand written fallback" % (len(rows) - live)
    return {
        "created_at": rows[0]["created_at"] if rows else utc_stamp(),
        "mode": kind,
        "offline": not network,
        "backend": mode["backend"],
        "network": network,
        "model": mode["model"],
        "system_chars": len(system),
        "calls_attempted": state["calls"],
        "rows": len(rows),
        "live": live,
        "fallback": fallback_rows,
        "fallback_reasons": reasons,
        "note": note,
    }


def run_bake(offline=False):
    """Build the file's document and write it. Returns (document, mode, state, skipped, units)."""
    glyphs = load_glyphs()
    tokens = talk_guard.load_tokens()  # missing or short list stops the bake loudly (spec 19 layer D)
    system = load_system_text()
    cards_doc, cards = load_cards()
    enemies = load_enemies()
    dialogue = load_dialogue()
    bank, blocks = load_gate_bank()
    mode = resolve_mode(offline)
    mode["system"] = system
    fight_units, skipped = fight_plan(cards, enemies, dialogue)
    npc_units = npc_plan(bank, blocks)
    plans = {"npc": npc_units, "fight": fight_units, "bank": bank,
             "last_npc_reply": {}, "last_fight_reply": {}}
    state = new_state()
    rows = build_rows(mode, state, glyphs, tokens, plans)
    fallback_rows = sum(1 for row in rows if row["source"] == "fallback")
    reasons = {}
    for row in rows:
        if row["source"] == "fallback":
            key = row["reason"].split(":")[0]
            reasons[key] = reasons.get(key, 0) + 1
    document = {
        "format": FORMAT,
        "kind": KIND,
        "rule": RULE,
        "effects": list(EFFECTS),
        "moods": list(MOODS),
        "bake": bake_header(mode, state, rows, fallback_rows, reasons, system),
        "coverage": {
            "talk_cards_in_data": len(cards_doc.get("cards") or []),
            "fight_phases": [{"card": unit["card"]["id"], "enemy": unit["enemy"]["id"],
                              "phase": unit["card"].get("phase", ""),
                              "options_dialogue": unit["options_id"]} for unit in fight_units],
            "npc": [{"id": npc["id"], "name": npc["name"], "place": npc["place"],
                     "fallback_source": "knowledge/GATE-DIALOGUE.md"}
                    for npc in NPCS],
            "skipped": skipped,
            "note": ("data/talk_cards.json holds no morgan or nye card (R38 Q1 and Q2 are with gamedev), "
                     "so the two NPC units take their hand written fallback from the R38 line bank and "
                     "their character block from the R38 ready to paste block. A card added there later "
                     "flips one fallback source with no other change."),
        },
        "rows": rows,
    }
    return document, mode, state, skipped, fight_units


def keep_previous_stamp(document):
    """Reuse the previous bake's created_at when every row is otherwise identical.

    A rerun of `--offline` that changes nothing must not churn a 53 KB generated file (or the mirror
    `tools/sync_data.py` keeps of it) just to move a timestamp, so the stamp means "when this content
    was baked", not "when this command last ran". Returns True when the previous stamp was kept.
    """
    if not os.path.isfile(OUT_FILE):
        return False
    try:
        old = load_json(OUT_FILE)
    except BakeError:
        return False
    if not isinstance(old, dict) or not isinstance(old.get("rows"), list):
        return False
    if len(old["rows"]) != len(document["rows"]):
        return False
    for new_row, old_row in zip(document["rows"], old["rows"]):
        if not isinstance(old_row, dict):
            return False
        if _without_stamp(new_row) != _without_stamp(old_row):
            return False
    stamp = (old.get("bake") or {}).get("created_at")
    if not stamp:
        return False
    for row in document["rows"]:
        row["created_at"] = stamp
    document["bake"]["created_at"] = stamp
    return True


def _without_stamp(row):
    return {key: value for key, value in row.items() if key != "created_at"}


def write_file(document):
    parent = os.path.dirname(OUT_FILE)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    return OUT_FILE


def report(document, state, skipped, stream=sys.stdout):
    bake = document["bake"]
    print("meta bake: %s, %d rows, %d live, %d fallback, %d skipped card(s), backend %r, network %s"
          % (bake["mode"], bake["rows"], bake["live"], bake["fallback"], len(skipped),
             bake["backend"] or "none", str(bake["network"]).lower()), file=stream)
    print("  system text: %d characters, model %s" % (bake["system_chars"], bake["model"]), file=stream)
    if bake["note"]:
        print("  why: %s" % bake["note"], file=stream)
    for reason, count in sorted(bake["fallback_reasons"].items()):
        print("  fallback reason %-8s %d row(s)" % (reason, count), file=stream)
    for row in skipped:
        print("  skipped: card %s (%s)" % (row["card"], row["reason"]), file=stream)
    print("  wrote %s" % os.path.relpath(OUT_FILE, ROOT), file=stream)


# ---------------------------------------------------------------- the check

def check_file(path=OUT_FILE, stream=sys.stdout):
    """Re-read the bake and refuse anything off contract. Returns the number of problems."""
    problems = []
    shown = safe_relpath(path)
    if not os.path.isfile(path):
        print("REFUSED: no bake file at %s" % shown, file=stream)
        return 1
    raw = load_text(path)
    lowered = raw.lower()
    for mark in FORBIDDEN_IN_FILE:
        if mark in lowered:
            problems.append("the file carries %r, and D5 allows no endpoint and no credential" % mark)
    document = load_json(path)
    glyphs = load_glyphs()
    tokens = talk_guard.load_tokens()
    _cards_doc, cards = load_cards()
    enemies = load_enemies()
    dialogue = load_dialogue()
    bank = load_gate_bank()[0]
    problems.extend(_check_header(document))
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        problems.append("the file holds no rows")
        rows = []
    seen = set()
    for row in rows:
        problems.extend(_check_row(row, seen, cards, glyphs, tokens, bank))
    problems.extend(_check_coverage(document, rows, cards, enemies, dialogue))
    problems.extend(_check_counts(document, rows))
    for problem in problems:
        print("REFUSED: %s" % problem, file=stream)
    if problems:
        print("meta bake check: %d problem(s), exit 1" % len(problems), file=stream)
        return len(problems)
    live = sum(1 for row in rows if row.get("source") == "live")
    print("meta bake check: %d rows, 0 problems, %d live, %d fallback, no key, no URL, exit 0"
          % (len(rows), live, len(rows) - live), file=stream)
    return 0


def _check_header(document):
    problems = []
    if document.get("format") != FORMAT or document.get("kind") != KIND:
        problems.append("format is %r and kind is %r, expected %d and %r"
                        % (document.get("format"), document.get("kind"), FORMAT, KIND))
    if document.get("moods") and list(document.get("moods")) != list(MOODS):
        problems.append("the moods table is not spec 19's five")
    if document.get("effects") and list(document.get("effects")) != list(EFFECTS):
        problems.append("the effects table is not spec 19's enum")
    bake = document.get("bake") or {}
    for field in ("model", "created_at", "mode", "rows", "live", "fallback", "network"):
        if field not in bake:
            problems.append("the bake block has no %r field" % field)
    if "key" in json.dumps(bake, sort_keys=True).lower():
        problems.append("the bake block names a key field")
    return problems


def _check_row(row, seen, cards, glyphs, tokens, bank):
    problems = []
    if not isinstance(row, dict):
        return ["a row is not an object"]
    row_id = row.get("id") or "<no id>"
    if row.get("id") in seen:
        problems.append("%s: duplicate row id" % row_id)
    seen.add(row.get("id"))
    for field in ("id", "scene", "text", "mood", "effect", "hint", "model", "request_hash",
                  "created_at", "fallback", "source"):
        if field not in row:
            problems.append("%s: no %r field, and D5 asks for it" % (row_id, field))
    scene = row.get("scene")
    if scene not in ("fight", "npc"):
        problems.append("%s: scene %r is neither fight nor npc" % (row_id, scene))
    problems.extend("%s: %s" % (row_id, problem)
                    for problem in validate_reply({key: row.get(key) for key in
                                                   ("text", "mood", "effect", "hint")},
                                                  scene if scene in ("fight", "npc") else "fight",
                                                  glyphs, tokens)[1])
    if row.get("source") not in ("live", "fallback"):
        problems.append("%s: source %r is neither live nor fallback" % (row_id, row.get("source")))
    if row.get("source") == "fallback":
        if not row.get("reason"):
            problems.append("%s: an offline row must say why it is offline" % row_id)
        else:
            problems.extend(_check_reason(row, row_id))
    if row.get("source") == "fallback" and row.get("network"):
        problems.append("%s: a fallback row cannot claim the network" % row_id)
    if row.get("source") == "live" and not row.get("network"):
        problems.append("%s: a live row must record network true" % row_id)
    for field in ("model", "request_hash", "created_at"):
        if not str(row.get(field) or "").strip():
            problems.append("%s: %s is empty" % (row_id, field))
    problems.extend(_check_hash(row, row_id))
    problems.extend(_check_fallback(row, row_id, cards, glyphs, bank))
    return problems


def _check_reason(row, row_id):
    """A reason has to name one of the bake's causes and then say what happened (R43's smaller item)."""
    reason = str(row.get("reason") or "")
    for prefix in REASON_PREFIXES:
        if reason.startswith(prefix):
            if len(reason) >= len(prefix) + 8:
                return []
            return ["%s: the reason %r names a cause and no detail" % (row_id, reason)]
    return ["%s: the reason %r is none of the bake's causes (%s)"
            % (row_id, reason, ", ".join(prefix.strip() for prefix in REASON_PREFIXES))]


def _check_hash(row, row_id):
    echo = row.get("request") or {}
    for field in ("system_sha256", "system_chars", "character", "scene", "player_line"):
        if field not in echo:
            return ["%s: the request echo has no %r, so the hash cannot be recomputed" % (row_id, field)]
    material = json.dumps({"kind": "chat", "model": row.get("model"), "request": echo},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    if digest != row.get("request_hash"):
        return ["%s: request_hash does not recompute from the stored request echo" % row_id]
    if echo["system_chars"] < 1500:
        return ["%s: the stored system text is %d characters, spec 19's measures about 2409"
                % (row_id, echo["system_chars"])]
    return []


def _check_fallback(row, row_id, cards, glyphs, bank):
    fallback = row.get("fallback")
    if not isinstance(fallback, dict):
        return ["%s: the fallback is not an object" % row_id]
    problems = []
    for field in ("source", "id", "text", "mood", "effect"):
        if field not in fallback:
            problems.append("%s: the fallback has no %r" % (row_id, field))
    source = fallback.get("source")
    want_mood = EFFECT_TO_MOOD.get(str(fallback.get("effect") or ""), "")
    if fallback.get("mood") != want_mood:
        problems.append("%s: the fallback mood is %r, the effect derives %r"
                        % (row_id, fallback.get("mood"), want_mood))
    if row.get("source") == "fallback":
        # R43 B2: a row labelled fallback shows its fallback and nothing else, so the four fields a
        # fallback holds are compared here byte for byte. A live row keeps its fallback as what it
        # shadows, so its own text and effect are the model's and are not compared.
        for field in ("text", "mood", "effect", "hint"):
            if row.get(field) != fallback.get(field):
                problems.append("%s: the row is a fallback and its %s is %r while its fallback holds %r"
                                % (row_id, field, row.get(field), fallback.get(field)))
    if source == "talk_cards":
        problems.extend(_check_talk_cards_fallback(row_id, fallback, cards, glyphs))
    elif source == "gate_dialogue":
        line_id = fallback.get("line_id")
        if line_id not in bank:
            problems.append("%s: the fallback id %r is not a line in knowledge/GATE-DIALOGUE.md"
                            % (row_id, fallback.get("id")))
        elif list(fallback.get("text") or []) != [bank[line_id]]:
            problems.append("%s: the fallback text is not the GATE-DIALOGUE row %s"
                            % (row_id, line_id))
    else:
        problems.append("%s: fallback source %r is neither talk_cards nor gate_dialogue"
                        % (row_id, source))
    return problems


def _check_talk_cards_fallback(row_id, fallback, cards, glyphs):
    card_id = fallback.get("card")
    pool_name = fallback.get("pool")
    index = fallback.get("index")
    if card_id not in cards:
        return ["%s: the fallback id %r names a card that does not exist in data/talk_cards.json"
                % (row_id, fallback.get("id"))]
    if not isinstance(index, int) or not isinstance(pool_name, str):
        return ["%s: the fallback id %r has no card, pool and index" % (row_id, fallback.get("id"))]
    card = cards[card_id]
    try:
        pool = resolve_pool(card, pool_name)
    except BakeError:
        return ["%s: card %s has no %r pool, so the fallback id cannot resolve"
                % (row_id, card_id, pool_name)]
    if not 0 <= index < len(pool):
        return ["%s: the fallback index %d is outside card %s's %s pool"
                % (row_id, index, card_id, pool_name)]
    effect = str(fallback.get("effect") or "")
    if effect not in EFFECT_TO_MOOD:
        return ["%s: the fallback effect %r is not in the spec 19 enum" % (row_id, effect)]
    try:
        expected_text = wrap_alphabet(pool[index], glyphs, "card %s %s pool line %d"
                                      % (card_id, pool_name, index))
    except BakeError as exc:
        return ["%s: the hand written pool line cannot be wrapped: %s" % (row_id, exc)]
    expected = {"id": "%s:%s:%d" % (card_id, pool_name, index), "card": card_id, "pool": pool_name,
                "index": index, "source_text": strip_marker(pool[index]), "text": expected_text,
                "mood": EFFECT_TO_MOOD[effect], "effect": effect, "hint": fallback.get("hint", "")}
    problems = []
    for field, value in expected.items():
        if fallback.get(field) != value:
            problems.append("%s: the fallback %r is not what %s holds (%r != %r)"
                            % (row_id, field, expected["id"], fallback.get(field), value))
    return problems


def _check_coverage(document, rows, cards, enemies, dialogue):
    """The bake must cover every fight phase and both NPCs, and must not quietly drop a reachable card."""
    problems = []
    fight_units, skipped = fight_plan(cards, enemies, dialogue)
    skipped_cards = {unit["card"] for unit in skipped}
    counts = {}
    for row in rows:
        key = row.get("card") if row.get("scene") == "fight" else row.get("npc")
        counts[(row.get("scene"), key)] = counts.get((row.get("scene"), key), 0) + 1
    for unit in fight_units:
        card_id = unit["card"]["id"]
        got = counts.get(("fight", card_id), 0)
        if got != OPTIONS_PER_UNIT:
            problems.append("card %s has %d option row(s), every reachable phase needs %d"
                            % (card_id, got, OPTIONS_PER_UNIT))
    for npc in NPCS:
        got = counts.get(("npc", npc["id"]), 0)
        if got != OPTIONS_PER_UNIT:
            problems.append("npc %s has %d row(s), the unit needs %d" % (npc["id"], got, OPTIONS_PER_UNIT))
    for card_id in counts:
        if card_id in skipped_cards:
            problems.append("card %s is listed as skipped and still has rows" % card_id)
    coverage = document.get("coverage") or {}
    listed = coverage.get("fight_phases") or []
    if len(listed) != len(fight_units):
        problems.append("coverage lists %d fight phases, the data reaches %d"
                        % (len(listed), len(fight_units)))
    return problems


def _check_counts(document, rows):
    bake = document.get("bake") or {}
    problems = []
    if bake.get("rows") != len(rows):
        problems.append("the bake block says %r rows, the file holds %d" % (bake.get("rows"), len(rows)))
    live = sum(1 for row in rows if row.get("source") == "live")
    if bake.get("live") != live:
        problems.append("the bake block says %r live rows, the file holds %d" % (bake.get("live"), live))
    if bake.get("fallback") != len(rows) - live:
        problems.append("the bake block says %r fallback rows, the file holds %d"
                        % (bake.get("fallback"), len(rows) - live))
    network = bake.get("network")
    if not isinstance(network, bool):
        problems.append("the bake block network is %r, not a boolean" % (network,))
        network = bool(network)
    if bake.get("offline") is not (not network):
        problems.append("the bake block says offline %r with network %r, so one of the two is wrong"
                        % (bake.get("offline"), network))
    mode = bake.get("mode")
    if mode not in MODE_NOTES:
        problems.append("the bake block mode is %r, and the only modes are %s"
                        % (mode, ", ".join(sorted(MODE_NOTES))))
        return problems
    note = str(bake.get("note") or "")
    # R43 B1: the block is read against the rows, in both directions, so a header cannot say more than
    # the calls did. `live` counts the rows the file itself calls live; network is what the run proved.
    if network and live == 0:
        problems.append("the bake block claims the network over 0 live rows, so it is refused")
    if mode == "live" and not live:
        problems.append("the bake block is mode live over 0 live rows, so it is refused")
    if mode == "live" and not network:
        problems.append("the bake block is mode live and records no network")
    if mode == "offline" and live:
        problems.append("the bake block is mode offline and %d row(s) are live" % live)
    if mode == "replay" and (not live or network):
        problems.append("the bake block is mode replay with %d live row(s) and network %r, and a replay "
                        "reads the cache without the network" % (live, network))
    if not note.startswith(MODE_NOTES[mode]):
        problems.append("the note %r does not start with %r, so it does not say what the run was"
                        % (note[:70], MODE_NOTES[mode]))
    return problems


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Bake the talk options and the two NPC voices into data/meta_bake.json "
                    "(spec 19, D5, card R29).")
    parser.add_argument("--offline", action="store_true",
                        help="write every row from the hand written fallback: no key, no network")
    parser.add_argument("--check", action="store_true",
                        help="re-read data/meta_bake.json and refuse anything off contract")
    parser.add_argument("--json", action="store_true", help="machine readable summary")
    args = parser.parse_args(argv)
    try:
        if args.check:
            return 1 if check_file() else 0
        document, _mode, state, skipped, _units = run_bake(offline=args.offline)
        kept = keep_previous_stamp(document)
        write_file(document)
        if args.json:
            print(json.dumps({key: document["bake"][key] for key in
                              ("created_at", "mode", "network", "rows", "live", "fallback")},
                             indent=2, sort_keys=True))
        else:
            report(document, state, skipped)
            if kept:
                print("  content unchanged, so the previous created_at was kept", file=sys.stdout)
        return 0
    except BakeError as exc:
        print("bake stopped: %s" % exc, file=sys.stderr)
        return 2
    except talk_guard.ProfanityListError as exc:
        print("bake stopped: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
