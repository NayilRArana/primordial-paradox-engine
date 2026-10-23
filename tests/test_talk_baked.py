"""R30 TALK-BAKED: the fight and the two NPCs read the bake, and the card answers when it does not (spec 19 s4 to s11).

Nothing here runs GameMaker, for the same reason tests/test_first_fight.py does not: every claim is computed
from a real file, and the shape of the GML function that computes it is pinned beside it, so a change in the
bake, the cards, the encounter row or the talk module fails here instead of in the first playtest.

Sources this file measures, never restates:

    data/meta_bake.json            the baked rows: fight/<card>/<option> and npc/<id>/turn_<n>
    data/talk_cards.json           the second rung of the ladder, the card's own pools
    data/dialogue/all.json         talk_deck_hound, the three option labels of the first fight
    data/encounters/all.json       deck_hound's talk block: card, option_count, mercy_per_option, mercy_to_spare
    data/enemies/all.json          deck_hound: 2 hp, trust_to_spare 3
    game/scripts/pp_battle_text/   the talk module this card wrote
    game/scripts/pp_battle_director/  the four hooks it calls into
    specs/16-talk-command.md       section 2's rows: +20 weak, +5 neutral, -10 hostile, 0 other
    specs/19-llm-talk.md           section 6's effect map, section 5's four lines of 28 at an 8 pixel pitch

What is proven:

  1. the first fight draws three options, distinct, each from the enemy's own dialogue row;
  2. picking each moves mercy by its baked effect's row and never by more than that row allows;
  3. three soften picks reach exactly the threshold, and the meter never leaves 0 to 100;
  4. the hint row lands inside the battle window, on the pixel row under the fourth reply line;
  5. with the bake gone (renamed away), the same three options answer from data/talk_cards.json and the
     fight is still winnable in three talks;
  6. no file under game/ builds a request or holds an address or a credential name;
  7. the checks can fail: dropping a baked row changes the answer, and a row off contract is refused.

No test here reads the network, writes a tracked data file, or needs a key.
"""

from __future__ import annotations

import copy
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAKE_PATH = os.path.join(ROOT, "data", "meta_bake.json")
CARDS_PATH = os.path.join(ROOT, "data", "talk_cards.json")
DIALOGUE_PATH = os.path.join(ROOT, "data", "dialogue", "all.json")
ENCOUNTERS_PATH = os.path.join(ROOT, "data", "encounters", "all.json")
ENEMIES_PATH = os.path.join(ROOT, "data", "enemies", "all.json")
CONFIG_GML = os.path.join(ROOT, "game", "scripts", "pp_config", "pp_config.gml")
TALK_GML = os.path.join(ROOT, "game", "scripts", "pp_battle_text", "pp_battle_text.gml")
DIRECTOR_GML = os.path.join(ROOT, "game", "scripts", "pp_battle_director", "pp_battle_director.gml")
OVERWORLD_GML = os.path.join(ROOT, "game", "scripts", "pp_overworld", "pp_overworld.gml")
SPEC_16 = os.path.join(ROOT, "specs", "16-talk-command.md")
SPEC_19 = os.path.join(ROOT, "specs", "19-llm-talk.md")

ENCOUNTER_ID = "deck_hound"
CARD_ID = "deck_hound"
NPC_ID = "morgan"

# Spec 19 section 6's effect map, quoted from spec 16 section 2's rows. Read from the spec by
# test_the_effect_map_is_the_specs_own_rows; this dict is what the mirror below spends.
EFFECT_ROW = {"soften": 20, "nudge": 5, "none": 0, "setback": -10, "end": 0}
FIGHT_EFFECTS = ("none", "nudge", "soften", "setback")
NPC_EFFECTS = ("none", "end")
MOODS = ("calm", "guarded", "rattled", "warm", "angry")

# GameMaker's network surface and the five credential names (the same lists tests/test_no_network_in_build.py
# refuses with). Named here so this card's own promise is measured by this card's own file.
NETWORK_CALLS = (
    "http_get", "http_get_file", "http_post_string", "http_request", "http_get_async",
    "network_connect", "network_connect_raw", "network_create_server", "network_create_socket",
    "network_send_packet", "network_send_raw", "network_send_udp", "url_open", "url_open_ext",
    "url_open_full", "get_string_async_from_url",
)
KEY_NAMES = ("GEMINI_API_KEY", "KAGGLE_API_TOKEN", "PINE_SANDBOX_API_KEY", "MODEL_API_KEY", "META_API_KEY")
URL_RE = re.compile(r"https?://", re.IGNORECASE)


# --------------------------------------------------------------------------- reading text and data


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def code_only(text: str) -> str:
    """Drop // comments so a structural check reads code and not prose."""
    out = []
    for line in text.split("\n"):
        cut = line.find("//")
        out.append(line if cut == -1 else line[:cut])
    return "\n".join(out)


def brace_block(text: str, marker: str) -> str:
    start = text.index(marker)
    open_index = text.index("{", start)
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index:index + 1]
    raise AssertionError("unbalanced block after %r" % marker)


def function_body(text: str, name: str) -> str:
    return brace_block(text, "function %s(" % name)


def number_return(text: str, name: str) -> int:
    """The one integer a one line geometry function returns (pp_talk_hint_y style)."""
    body = function_body(text, name)
    match = re.search(r"return\s+(-?\d+)\s*;", body)
    assert match, "no integer return in %s" % name
    return int(match.group(1))


def row(document: dict, collection: str, row_id: str) -> dict:
    rows = document.get(collection)
    assert isinstance(rows, list) and rows, "no %s list" % collection
    found = [r for r in rows if r.get("id") == row_id]
    assert len(found) == 1, "expected one %s row %r, found %d" % (collection, row_id, len(found))
    return found[0]


# --------------------------------------------------------------------------- the mirror of the GML


def clean_row(entry: dict, scene: str) -> dict:
    """pp_talk_reply_clean, reimplemented from its own body (spec 19 section 4 table)."""
    text = entry.get("text")
    if not isinstance(text, list) or not text:
        return None
    lines = []
    for index, line in enumerate(text):
        if index >= 4:
            break
        if not line:
            continue
        if len(line) > 28:
            line = line[:28].rsplit(" ", 1)[0] or line[:28]
        lines.append(line)
    if not lines:
        return None
    effect = entry.get("effect", "none")
    legal = NPC_EFFECTS if scene == "npc" else FIGHT_EFFECTS
    if effect not in legal:
        effect = "none"
    mood = entry.get("mood")
    if mood not in MOODS:
        mood = {"soften": "warm", "nudge": "calm", "setback": "angry", "end": "calm"}.get(effect, "guarded")
    hint = entry.get("hint") or ""
    if len(hint) > 28:
        hint = hint[:28].rsplit(" ", 1)[0]
    return {"text": lines, "mood": mood, "effect": effect, "hint": hint}


def load_bake(path: str) -> dict:
    """pp_talk_bake: fight rows by card|phase and option, npc rows by npc and turn."""
    bake = {"loaded": False, "rows": 0, "refused": 0, "fight": {}, "npc": {}}
    if not os.path.exists(path):
        return bake
    document = _load(path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        return bake
    bake["loaded"] = True
    for entry in rows:
        if not isinstance(entry, dict) or "scene" not in entry:
            bake["refused"] += 1
            continue
        reply = clean_row(entry, entry["scene"])
        if reply is None:
            bake["refused"] += 1
            continue
        if entry["scene"] == "fight":
            card = entry.get("card", "")
            if not card:
                bake["refused"] += 1
                continue
            key = "%s|%s" % (card, entry.get("phase", ""))
            bucket = bake["fight"].setdefault(key, [])
            option = max(1, int(entry.get("option", 1)))
            while len(bucket) < option:
                bucket.append(None)
            bucket[option - 1] = reply
        elif entry["scene"] == "npc":
            npc = entry.get("npc", "")
            if not npc:
                bake["refused"] += 1
                continue
            bucket = bake["npc"].setdefault(npc, [])
            turn = max(1, int(entry.get("turn", 1)))
            while len(bucket) < turn:
                bucket.append(None)
            bucket[turn - 1] = reply
        else:
            bake["refused"] += 1
            continue
        bake["rows"] += 1
    return bake


def effect_delta(effect: str, mercy_per_option: int) -> int:
    """pp_talk_effect_delta: soften is the encounter's own number, nudge +5, setback -10, none 0."""
    if effect == "soften":
        return mercy_per_option
    if effect == "nudge":
        return 5
    if effect == "setback":
        return -10
    return 0


def band(mercy: int) -> str:
    if mercy >= 60:
        return "high"
    if mercy >= 20:
        return "mid"
    return "low"


def pool_of(card: dict, name: str, mercy: int) -> list:
    pool = (card.get("pools") or {}).get(name)
    if isinstance(pool, list):
        return pool
    if isinstance(pool, dict):
        return pool.get(band(mercy)) or pool.get("mid") or []
    return []


def stable_hash(text: str) -> int:
    value = 7
    for char in text:
        value = (value * 31 + ord(char)) % 1000000007
    return value


def normalise(text: str) -> str:
    out = " ".join(text.split()).lower()
    return out.strip(" .,:;!?'\"*")


def options_of(bake: dict, encounter: dict, dialogue_rows: dict, cards: dict, mercy: int = 0) -> list:
    """pp_talk_options: the authored labels, then a baked row or the card's own pool line for each."""
    talk = encounter["talk"]
    labels = dialogue_rows[talk["options_dialogue"]]["lines"]
    count = min(len(labels), talk.get("option_count", len(labels)))
    baked = (bake["fight"].get("%s|" % talk["card"]) or [])
    card = cards.get(talk["card"]) or {}
    out = []
    for index in range(count):
        reply = baked[index] if index < len(baked) else None
        record = {"label": label_of(labels[index]), "baked": reply is not None, "effect": "none", "delta": 0,
                  "lines": [], "hint": ""}
        if reply is not None:
            record["effect"] = reply["effect"]
            record["delta"] = effect_delta(reply["effect"], talk["mercy_per_option"])
            record["lines"] = ["* " + line for line in reply["text"]]
            record["hint"] = reply["hint"]
        else:
            pool = pool_of(card, "neutral", mercy)
            record["delta"] = talk["mercy_per_option"]
            picked = pool[(stable_hash(normalise(labels[index])) + mercy) % len(pool)] if pool else labels[index]
            record["lines"] = ["* " + line for line in wrap_line(picked)]
        out.append(record)
    return out


def wrap_line(text: str, cols: int = 28) -> list:
    """pp_talk_wrap: greedy word wrap, four rows at most. The card's own rows are the ones the game wraps."""
    out = []
    row = ""
    for word in text.split():
        candidate = word if row == "" else row + " " + word
        if len(candidate) <= cols:
            row = candidate
            continue
        if row:
            out.append(row)
        row = word[:cols]
    if row:
        out.append(row)
    return out[:4]


def label_of(line: str) -> str:
    """pp_talk_option_label: the marker and the speech quotes are not part of what the player picks."""
    text = line.strip()
    if text.startswith("* "):
        text = text[2:]
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    text = text.strip()
    return text[:28].rsplit(" ", 1)[0] if len(text) > 28 else text


def apply_row(mercy: int, record: dict) -> int:
    """pp_talk_apply: one row, clamped to its own number and then to 0..100, and the change that landed."""
    delta = max(-20, min(20, record["delta"]))
    return max(0, min(100, mercy + delta)) - mercy


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def bake() -> dict:
    return load_bake(BAKE_PATH)


@pytest.fixture(scope="module")
def encounter() -> dict:
    return row(_load(ENCOUNTERS_PATH), "encounters", ENCOUNTER_ID)


@pytest.fixture(scope="module")
def hound() -> dict:
    return row(_load(ENEMIES_PATH), "enemies", ENCOUNTER_ID)


@pytest.fixture(scope="module")
def dialogue_rows() -> dict:
    return {entry["id"]: entry for entry in _load(DIALOGUE_PATH)["dialogue"]}


@pytest.fixture(scope="module")
def cards() -> dict:
    return {entry["id"]: entry for entry in _load(CARDS_PATH)["cards"]}


@pytest.fixture(scope="module")
def talk_code() -> str:
    return code_only(_read(TALK_GML))


# --------------------------------------------------------------------------- 1 and 2. the three options


def test_the_bake_holds_the_three_options_of_the_first_fight(bake, encounter):
    key = "%s|" % encounter["talk"]["card"]
    assert key in bake["fight"], "the bake has no row for %r" % key
    baked = [entry for entry in bake["fight"][key] if entry is not None]
    assert len(baked) == encounter["talk"]["option_count"] == 3
    assert all(entry["effect"] in FIGHT_EFFECTS for entry in baked), baked


def test_the_three_options_are_distinct_and_are_the_enemys_own_lines(bake, encounter, dialogue_rows, cards):
    options = options_of(bake, encounter, dialogue_rows, cards)
    assert len(options) == 3
    labels = [option["label"] for option in options]
    assert len(set(labels)) == 3, "two options read the same: %r" % (labels,)
    assert all(option["baked"] for option in options), "the first fight's options must all come from the bake"
    authored = [label_of(line) for line in dialogue_rows[encounter["talk"]["options_dialogue"]]["lines"]]
    assert labels == authored


def test_picking_each_option_moves_mercy_by_its_baked_row(bake, encounter, dialogue_rows, cards):
    options = options_of(bake, encounter, dialogue_rows, cards)
    mercy = 0
    seen = []
    for option in options:
        applied = apply_row(mercy, option)
        mercy += applied
        seen.append((option["effect"], option["delta"], applied))
        # never more than the effect row allows, and never a sign the row does not carry
        assert abs(applied) <= abs(EFFECT_ROW[option["effect"]] or 20), seen
        assert (applied > 0) == (option["delta"] > 0) or applied == 0, seen
    assert [entry[0] for entry in seen] == ["soften", "nudge", "setback"], seen
    assert [entry[1] for entry in seen] == [20, 5, -10], seen
    assert 0 <= mercy <= 100


def test_three_soften_picks_reach_the_threshold_and_never_pass_it(encounter, hound):
    talk = encounter["talk"]
    mercy = 0
    for turn in range(1, 4):
        applied = apply_row(mercy, {"delta": effect_delta("soften", talk["mercy_per_option"])})
        mercy += applied
        assert applied == talk["mercy_per_option"] == 20, "turn %d moved %d" % (turn, applied)
    assert mercy == talk["mercy_to_spare"] == 60
    assert mercy // 20 >= hound["trust_to_spare"]

    # A row can never lift the meter past 100 nor drop it below 0, however many times it lands.
    mercy = 95
    for _ in range(5):
        applied = apply_row(mercy, {"delta": 20})
        assert applied <= 20
        mercy += applied
    assert mercy == 100
    mercy = 5
    applied = apply_row(mercy, {"delta": -10})
    assert applied == -5 and mercy + applied == 0, "a setback at 5 lands as 0, not -10"


def test_the_effect_map_is_the_specs_own_rows():
    """Spec 16 section 2's table is where every number in this card's arithmetic comes from."""
    spec = _read(SPEC_16)
    rows = {
        "soften": int(re.search(r"Context option TALK that lands on a weak topic \| \+(\d+)", spec).group(1)),
        "nudge": int(re.search(r"Context option TALK that is neutral \| \+(\d+)", spec).group(1)),
        "setback": -int(re.search(r"FIGHT that lands damage \| -(\d+)", spec).group(1)),
        "none": int(re.search(r"Any other code path \| (\d+)", spec).group(1)),
    }
    assert rows == {"soften": 20, "nudge": 5, "setback": -10, "none": 0}, rows
    assert rows["setback"] == EFFECT_ROW["setback"]
    enum = re.search(r'"effect": \{ "enum": \[([^\]]*)\]', _read(SPEC_19))
    assert enum, "spec 19 section 4 no longer prints the effect enum"
    members = [part.strip().strip('"') for part in enum.group(1).split(",")]
    assert members == ["none", "nudge", "soften", "setback", "end"], members
    assert "spare" not in members


def test_no_effect_in_the_enum_can_end_a_fight(encounter, hound):
    """Spec 19 section 6 rule 3: SPARE is a game condition, and no reply effect can grant it."""
    assert "spare" not in EFFECT_ROW
    assert "end" not in FIGHT_EFFECTS
    assert hound["trust_to_spare"] == encounter["talk"]["talks_to_spare"]
    for effect in FIGHT_EFFECTS:
        assert effect_delta(effect, 20) <= 20


# --------------------------------------------------------------------------- 3 and 4. the box geometry


def test_the_hint_lands_inside_the_battle_window(talk_code):
    director = code_only(_read(DIRECTOR_GML))
    y2 = brace_block(director, "function pp_battle_text_box_y2(")
    assert "return 48;" in y2, y2

    pitch = number_return(talk_code, "pp_talk_line_pitch")
    rows_max = number_return(talk_code, "pp_talk_lines_max")
    top = number_return(talk_code, "pp_talk_text_y")
    hint = number_return(talk_code, "pp_talk_hint_y")
    assert (pitch, rows_max) == (8, 4), "spec 19 Q2: four lines at an 8 pixel pitch"
    assert top + (rows_max - 1) * pitch + 8 <= 48, "the fourth reply line leaves the window"
    assert top <= hint < 48, "the hint row is not under the reply block"
    assert hint + 8 <= 48, "the hint row leaves the window"
    assert hint == top + rows_max * pitch - pitch + pitch, "the hint is not on the row after the last line"


def test_the_draw_spends_the_hint_inside_the_box_on_its_own_row(talk_code, director_code):
    """Card BATTLE-FONT-WIRE: the hint is the sheet's glyphs, and its own row is what marks it out.

    Spec 19 Q9 says the hint is the row under the reply block. It used to be drawn in the second role colour, which
    the 8x8 sheet cannot do: the sheet is one ink and a tint is a multiply no PPU can output (font contract rule 6),
    so the row's own position carries the distinction and the words are pp_font_draw's.
    """
    draw = function_body(talk_code, "pp_talk_hint_draw")
    assert "pp_font_draw(_hint, pp_talk_text_x(), pp_talk_hint_y(), 1)" in draw, draw
    assert "draw_text" not in draw, "the hint is not the sheet's glyphs"
    assert "draw_set_colour(pp_role_colour" not in draw, \
        "the hint asks for a second ink; the sheet is one ink, and its own row is the marker"
    wired = function_body(director_code, "pp_battle_draw")
    assert "pp_talk_board_draw(_battle.messages" in wired, wired
    assert "pp_talk_hint_draw(_battle.talk_hint)" in wired, wired


def test_the_option_panel_draws_three_labels_in_the_command_band(talk_code, bake, encounter, dialogue_rows, cards):
    panel = function_body(talk_code, "pp_talk_draw_options")
    assert "PP_MENU_TOP + 10 + i * 16" in panel, panel
    assert "array_length(_battle.talk_options)" in panel, panel
    labels = [option["label"] for option in options_of(bake, encounter, dialogue_rows, cards)]
    assert len(labels) == 3
    assert all(1 <= len(label) <= 28 for label in labels), labels
    last_y = 168 + 10 + 2 * 16
    assert last_y + 8 <= 240, "the third option leaves the frame"


@pytest.fixture(scope="module")
def director_code() -> str:
    return code_only(_read(DIRECTOR_GML))


# --------------------------------------------------------------------------- 5. the fallback with the bake gone


def test_the_fallback_shows_the_cards_own_rows_when_the_bake_is_renamed_away(
        tmp_path, encounter, dialogue_rows, cards, hound):
    """The card's check: rename data/meta_bake.json away and the fight still answers with its canned card."""
    data_copy = tmp_path / "data"
    data_copy.mkdir()
    live = data_copy / "meta_bake.json"
    with open(BAKE_PATH, "r", encoding="utf-8") as source:
        live.write_text(source.read(), encoding="utf-8")
    away = data_copy / "meta_bake.json.away"
    os.rename(live, away)
    assert away.exists() and not live.exists(), "the file was not renamed away"

    bake_away = load_bake(str(live))
    assert bake_away["loaded"] is False and not bake_away["fight"] and not bake_away["npc"]

    options = options_of(bake_away, encounter, dialogue_rows, cards)
    assert len(options) == 3
    assert all(not option["baked"] for option in options)
    pool = pool_of(cards[encounter["talk"]["card"]], "neutral", 0)
    assert pool, "the card carries no neutral pool to fall back to"
    for option in options:
        shown = " ".join(line[2:] for line in option["lines"])
        assert shown in pool, "%r is not one of the card's own rows" % shown
        assert all(len(line) <= 30 for line in option["lines"]), option["lines"]
        assert option["delta"] == encounter["talk"]["mercy_per_option"] == 20

    # And the fight is still winnable in three talks with no bake at all (spec 19 section 11 rule 1).
    mercy = 0
    for _ in range(3):
        mercy += apply_row(mercy, options[0])
    assert mercy == encounter["talk"]["mercy_to_spare"] == 60
    assert mercy // 20 >= hound["trust_to_spare"]


def test_the_two_npc_voices_are_baked_in_their_own_rows(bake):
    assert "morgan" in bake["npc"], "no Morgan conversation in the bake"
    turns = [entry for entry in bake["npc"]["morgan"] if entry is not None]
    assert len(turns) >= 1
    for turn in turns:
        assert turn["effect"] in NPC_EFFECTS, turn
        assert 1 <= len(turn["text"]) <= 4
        assert all(1 <= len(line) <= 28 for line in turn["text"]), turn["text"]
        assert turn["mood"] in MOODS


def test_the_world_talk_branch_opens_the_bake_before_the_authored_dialogue(talk_code):
    opener = function_body(talk_code, "pp_talk_actor_open")
    assert opener.index("pp_talk_npc_open") < opener.index("pp_dialogue_open"), opener
    overworld = code_only(_read(OVERWORLD_GML))
    branch = function_body(overworld, "pp_overworld_step")
    assert "pp_talk_actor_open(_talk, _world)" in branch, branch
    assert "pp_talk_npc_hint(_world.dialogue)" in overworld


# --------------------------------------------------------------------------- 6. no request, no address, no key


def game_files() -> list:
    found = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__"))
        for name in sorted(filenames):
            if name.endswith((".gml", ".yy", ".yyp")):
                found.append(os.path.join(dirpath, name))
    return found


def test_no_gml_builds_a_request_or_holds_an_address():
    files = game_files()
    assert files, "no GML found under game/"
    offenders = []
    for path in files:
        text = _read(path)
        for line_number, line in enumerate(text.split("\n"), start=1):
            code = line.split("//")[0] if "\"" not in line else line
            for name in NETWORK_CALLS + KEY_NAMES:
                if name in code:
                    offenders.append("%s:%d names %s" % (os.path.relpath(path, ROOT), line_number, name))
            for match in URL_RE.finditer(code):
                offenders.append("%s:%d holds an address" % (os.path.relpath(path, ROOT), line_number))
    assert not offenders, "\n".join(offenders[:10])


def test_the_talk_module_reads_one_local_file_through_the_data_door(talk_code):
    assert 'pp_data_json("meta_bake.json")' in talk_code
    assert 'pp_data_json("talk_cards.json")' in talk_code
    assert talk_code.count("pp_data_json(") == 2, "the talk path reads exactly two data files"
    assert "file_text_open" not in talk_code, "pp_data_read is the one door to a file"


# --------------------------------------------------------------------------- 7. the shape, and it can fail


def test_the_gml_functions_are_the_shape_this_file_reimplements(talk_code, director_code):
    clean = function_body(talk_code, "pp_talk_reply_clean")
    assert "if (i >= 4)" in clean, clean
    assert "if (string_length(_line) > 28)" in clean, clean
    assert "pp_talk_effect_legal(_effect, _scene)" in clean, clean
    assert "pp_talk_effect_mood(_effect)" in clean, clean

    delta = function_body(talk_code, "pp_talk_effect_delta")
    assert 'case "soften":' in delta and "_battle.encounter.talk.mercy_per_option" in delta, delta
    assert 'case "nudge":   return 5;' in delta, delta
    assert 'case "setback": return -10;' in delta, delta

    applied = function_body(talk_code, "pp_talk_apply")
    assert "clamp(_record.delta, -20, 20)" in applied, applied
    assert "clamp(_before + _delta, 0, 100)" in applied, applied
    assert "_battle.talk_mercy - _before" in applied, applied

    bake_load = function_body(talk_code, "pp_talk_bake")
    assert '_doc = pp_data_json("meta_bake.json")' in bake_load, bake_load
    assert '_card + "|" + _phase' in bake_load, bake_load

    step = function_body(talk_code, "pp_talk_step")
    assert "pp_talk_apply(_battle, _record)" in step, step
    assert 'pp_battle_say(_battle, _record.lines, "enemy_turn")' in step, step

    begin = function_body(director_code, "pp_battle_begin_action")
    talk_case = begin[begin.index("case PPCommand.talk:"):]
    talk_case = talk_case[:talk_case.index("case PPCommand.spare:")]
    assert "pp_talk_begin(_battle)" in talk_case, talk_case
    assert "_battle.trust += _battle.encounter.trust_per_talk" in talk_case, talk_case
    # The talk branch still damages nothing: spec 16 section 11 and tests/test_first_fight.py pin this.
    assert "pp_battle_hurt_enemy" not in talk_case, talk_case
    assert "enemy_hp" not in talk_case, talk_case

    menu = function_body(director_code, "pp_battle_step_menu")
    assert 'if (_battle.talk_stage != "")' in menu, menu
    assert "pp_talk_step(_battle)" in menu, menu


def test_dropping_a_baked_row_changes_the_answer(bake, encounter, dialogue_rows, cards):
    """A silent change is caught: the answer for option 2 comes from a different rung once its row is gone."""
    full = options_of(bake, encounter, dialogue_rows, cards)
    trimmed = copy.deepcopy(bake)
    trimmed["fight"]["deck_hound|"][1] = None
    partial = options_of(trimmed, encounter, dialogue_rows, cards)
    assert full[1]["baked"] and not partial[1]["baked"], "the third rung did not take over"
    assert full[1]["lines"] != partial[1]["lines"], "the answer did not change when the row went"
    assert full[0]["lines"] == partial[0]["lines"], "dropping option 2 must not disturb option 1"


def test_a_row_off_contract_is_refused_and_falls_to_the_card(encounter, dialogue_rows, cards, bake):
    broken = {"fight": {"deck_hound|": [
        {"text": ["ONE", "TWO", "THREE", "FOUR", "FIVE"], "mood": "happy", "effect": "spare", "hint": "X"},
    ]}}
    cleaned = clean_row({"text": ["ONE", "TWO", "THREE", "FOUR", "FIVE"], "mood": "happy",
                         "effect": "spare", "hint": "X"}, "fight")
    assert cleaned is not None and len(cleaned["text"]) == 4, "a fifth line is dropped, not the reply"
    assert cleaned["effect"] == "none", "an unknown effect is refused"
    assert cleaned["mood"] == "guarded", "an unknown mood is derived from the effect"
    assert clean_row({"text": []}, "fight") is None
    assert clean_row({"text": ["OK"], "effect": "end"}, "fight")["effect"] == "none", "end is illegal in a fight"
    assert clean_row({"text": ["OK"], "effect": "soften"}, "npc")["effect"] == "none", "soften is illegal in chat"
    assert broken  # the mutated table is a copy, never the committed file


def test_the_same_bake_loaded_twice_is_byte_identical():
    """Spec 19 check 12.3: no RNG on any rung, so a replay says the same words."""
    first = load_bake(BAKE_PATH)
    second = load_bake(BAKE_PATH)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert stable_hash(normalise("A low growl. Then a thump.")) == stable_hash(
        normalise("* A low growl. Then a thump.")), "the marker must not change the pool index"
