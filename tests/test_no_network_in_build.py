"""R34 TEST-NO-NETWORK: prove the D5 promise mechanically, on the files a judge actually runs.

What this file claims, and nothing wider
========================================
`knowledge/GAMEDEV-DECISIONS-2026-10-22.md` D5 says the shipped build makes no network call, ever,
and holds no key. That is a promise about *reachability* and *credentials*, and it is the promise the
pitch makes, so it has to be measured rather than restated. This module measures it over every file
that ships: all of `game\\` (scripts, objects, options, rooms, the .yy files and the .yyp, and the
built datafiles the engine reads at runtime) plus `data\\meta_bake.json` and the top level
`data\\*.json` sources those come from.

Four refusals, and the sixth check a run has to pass to be trusted
==================================================================
1. NO CREDENTIAL NAME. The five names spec 19 and the Meta client read are refused wherever they
   appear in a shipped file: GEMINI_API_KEY, KAGGLE_API_TOKEN, PINE_SANDBOX_API_KEY, MODEL_API_KEY,
   META_API_KEY. The scan reads the NAME only and never echoes what follows it, so a key that was
   pasted into a file by mistake is named, not reprinted, and this module holds no key either.
2. NO NETWORK CALL IN CODE. `.gml`, `.yy` and `.yyp` files may not name a GameMaker network or socket
   function (`http_get`, `http_post_string`, `http_request`, `network_connect`, `network_send_*`,
   `url_open*`, and the rest of the list below). `async_load` is deliberately NOT on that list: the
   save system polls it for a local file write, and refusing it would refuse correct code.
3. NO URL OUTSIDE A COMMENT IN CODE. A URL in a GML comment is a citation to the engine manual. A URL
   in GML that is not in a comment is a string some function could be handed, so it is refused. Same
   rule for .yy and .yyp.
4. NO ENDPOINT AND NO CREDENTIAL IN DATA. A URL under an endpoint shaped key (`api`, `api_base`,
   `base_url`, `endpoint`, `host`, `server`, `socket`, `url` inside a request block, ...) is refused
   even in a file that is otherwise allowed to hold citations, and a URL that carries a credential
   inline (`user:pass@`, `?key=`, `&token=`, `Bearer `) is refused everywhere. A base64 blob longer
   than 4096 characters in a data file is refused: that is a key or a payload hiding from the two
   scans above. `data\\meta_bake.json` is held to the strictest rule of all: no URL at all.

THE ONE EXEMPTION, AND WHY IT IS NOT A SKIP
===========================================
This repository's shipped data legitimately carries other people's URLs: citation tables
(`data\\music_recipes.json`, `data\\drum_patterns.json`, `data\\dissonance_rules.json`) cite the
NESdev wiki and the papers they were read from, `data\\nes_palette.json` cites its palette source in
prose, and the map pipeline ships OpenStreetMap downloads whose own tags hold shop and heritage
websites. None of those is an endpoint the game can call: there is no network function in any shipped
GML file for layer 2 to miss, and layer 3 refuses the one shape that could become a call. So a data
file may hold a URL only when it proves FROM ITS OWN BYTES that it is a citation table or third party
geography:

    - it parses as a JSON object carrying a top level `generator` that starts with "Overpass API"
      (a download, not our prose), or
    - it carries a top level provenance block: `sources`, `source`, `citation`, `attribution`,
      `licence`, `license` or `provenance`, or
    - it is a Tiled map whose own properties carry an attribution or licence entry.

A plain data table (`data\\audio.json`, `data\\dialogue\\all.json`, `data\\talk_cards.json`,
`data\\project.json`, `data\\meta_bake.json`) carries no such block, so a URL planted in one is
refused. Every file the exemption covers is counted and printed by the run, so the exemption can
never widen quietly and can never be silent. What this file does NOT claim: that a URL string can be
told from an endpoint string by looking at it. It cannot, which is why the endpoint keys and the
inline credential marks are a separate, unconditional refusal, and why the report line says how many
citation files were exempted rather than reporting a clean zero.

THE SECOND HALF: THE BAKE IS STILL SERVED WITH THE NETWORK OFF
==============================================================
D5 point 3 says the demo survives a dead network. The test forces `PP_AI_MODE=replay`, removes every
key from the environment, and replaces `urllib.request.urlopen` with a trap that fails the test if
anything opens a socket. In that state it:

    a. proves the client refuses rather than calls: an unrecorded request raises CacheMiss, not a
       request, and the trap is never sprung;
    b. rebuilds every talk request from committed source data (`data\\talk_cards.json`,
       `data\\enemies\\all.json`, `data\\dialogue\\all.json`, `knowledge\\GATE-DIALOGUE.md`, the system
       text measured out of spec 19) and looks it up by `request_hash` in `data\\meta_bake.json`,
       exactly the rung 1 lookup of spec 19 section 8. Every rebuilt request has to land on the row
       written for it, so the demo shows Meta's baked lines with the network off;
    c. proves the file the engine actually reads, `game\\datafiles\\meta_bake.json`, is byte identical
       to the source it is mirrored from, because a stale mirror is a demo that shows hand written
       text while the bake looks perfect.

Usage
    python -m pytest tests/test_no_network_in_build.py -q
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import urllib.request

import pytest

import bake_meta
import meta_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAKE_FILE = os.path.join(ROOT, "data", "meta_bake.json")
SHIPPED_BAKE = os.path.join(ROOT, "game", "datafiles", "meta_bake.json")

# The five names the build must never hold. Names only: no value is ever read, stored or printed.
KEY_NAMES = (
    "GEMINI_API_KEY",
    "KAGGLE_API_TOKEN",
    "PINE_SANDBOX_API_KEY",
    "MODEL_API_KEY",
    "META_API_KEY",
)

# GameMaker's network surface, as function names. async_load is not here on purpose: pp_save polls it
# for a local file write, and that is not a network read.
NETWORK_CALLS = (
    "http_get", "http_get_file", "http_post_string", "http_request", "http_get_async",
    "network_connect", "network_connect_raw", "network_create_server",
    "network_create_server_raw", "network_create_socket", "network_create_socket_ext",
    "network_send_broadcast", "network_send_packet", "network_send_raw", "network_send_udp",
    "network_set_config", "network_destroy", "get_string_async_from_url",
    "url_open", "url_open_ext", "url_open_full", "steam_initialise", "steam_update",
)

# A URL under one of these keys is an endpoint, whatever file it sits in, and is refused there.
ENDPOINT_KEY_RE = re.compile(
    r"^(api|api_base|api_url|api_root|backend|base_url|base_uri|endpoint|endpoints|host|hosts|"
    r"origin|server|servers|socket|proxy|request_url|upload_url|poll_url|auth_url|token_url|"
    r"webhook|ws|wss|http|https)$",
    re.IGNORECASE,
)

# Marks that turn a URL into a credential carrier. Refused in every file, citations included.
INLINE_CREDENTIAL_RE = re.compile(
    r"(://[^/\s:@]+:[^/\s@]+@)|([?&](key|token|api_key|apikey|access_token|signature)=)|(bearer\s)",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://[^\s\"'<>)\\]+", re.IGNORECASE)
# Long base64 or hex runs: a blob this size in a data file is hiding from every scan above.
BLOB_RE = re.compile(r"[A-Za-z0-9+/=]{4096,}")

CODE_SUFFIXES = (".gml", ".yy", ".yyp")
GML_SUFFIXES = (".gml",)

# A data file may hold citations only when it declares them itself. Read the docstring for why.
PROVENANCE_BLOCK_KEYS = ("sources", "source", "citation", "attribution", "licence", "license",
                         "provenance")
OVERPASS_MARK = "Overpass API"
TILED_ATTRIBUTION_KEYS = ("attribution", "credit", "credits", "source", "sources", "licence",
                          "license", "copyright")

# The strictest file: the talk bake holds no URL of any kind (bake_meta --check says the same).
NO_URL_FILES = ("data/meta_bake.json", "game/datafiles/meta_bake.json")

REPORT: dict[str, int] = {}


# ---------------------------------------------------------------- what ships
def shipped_files(root: str) -> list[str]:
    """Every file the judge's build carries: all of game\\, plus data\\meta_bake.json and data\\*.json."""
    found: list[str] = []
    game = os.path.join(root, "game")
    for dirpath, dirnames, filenames in os.walk(game):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__", ".pytest_cache"))
        for name in sorted(filenames):
            found.append(os.path.join(dirpath, name))
    data = os.path.join(root, "data")
    if os.path.isdir(data):
        for name in sorted(os.listdir(data)):
            full = os.path.join(data, name)
            if name.endswith(".json") and os.path.isfile(full):
                found.append(full)
    return found


def read_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def read_text(text_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return text_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return text_bytes.decode("latin-1", "replace")


def code_part(line: str) -> str:
    """The part of a GML line that is code: everything before an unquoted //."""
    in_string = False
    for index, char in enumerate(line):
        if char == '"':
            in_string = not in_string
        elif not in_string and char == "/" and line[index:index + 2] == "//":
            return line[:index]
    return line


# ---------------------------------------------------------------- the scans
def carries_provenance(payload) -> str:
    """How this data file proves, from its own bytes, that its URLs are somebody else's citations."""
    if not isinstance(payload, dict):
        return ""
    generator = payload.get("generator")
    if isinstance(generator, str) and generator.startswith(OVERPASS_MARK):
        return "overpass download"
    for key in PROVENANCE_BLOCK_KEYS:
        if key in payload:
            return "provenance block %r" % key
    if payload.get("type") == "map":
        containers = [payload]
        for layer in payload.get("layers") or []:
            if isinstance(layer, dict):
                containers.append(layer)
        for container in containers:
            for prop in container.get("properties") or []:
                if isinstance(prop, dict) and str(prop.get("name", "")).lower() in TILED_ATTRIBUTION_KEYS:
                    return "Tiled map attribution"
    return ""


def url_key_problems(node, rel: str, text: str) -> list[str]:
    """Endpoint keys and inline credentials: refused in every data file, exemption or not."""
    problems: list[str] = []

    def line_of(value: str) -> int:
        needle = json.dumps(value)[:60]
        position = text.find(needle)
        return text.count("\n", 0, position) + 1 if position >= 0 else 0

    def walk(current, key):
        if isinstance(current, dict):
            for child_key, child in current.items():
                walk(child, child_key)
        elif isinstance(current, list):
            for child in current:
                walk(child, key)
        elif isinstance(current, str) and URL_RE.search(current):
            where = "%s:%d" % (rel, line_of(current)) if line_of(current) else rel
            if key is not None and ENDPOINT_KEY_RE.match(str(key)):
                problems.append("%s: endpoint under key %r (D5 allows no endpoint in the build)"
                                % (where, str(key)))
            if INLINE_CREDENTIAL_RE.search(current):
                problems.append("%s: URL carries a credential inline (D5 allows no credential in the "
                                "build)" % where)

    walk(node, None)
    return problems


def key_name_problems(text: str, rel: str) -> list[str]:
    """The five names only. The message names the variable and never what follows it."""
    problems: list[str] = []
    for name in KEY_NAMES:
        start = text.find(name)
        while start >= 0:
            line = text.count("\n", 0, start) + 1
            problems.append("%s:%d: names the credential %s (name only, value not read)"
                            % (rel, line, name))
            start = text.find(name, start + 1)
    return problems


def blob_problems(text: str, rel: str) -> list[str]:
    problems: list[str] = []
    for match in BLOB_RE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        problems.append("%s:%d: base64 blob of %d characters, over the 4096 limit for a data file"
                        % (rel, line, len(match.group(0))))
    return problems


def scan_file(path: str, rel: str) -> tuple[list[str], str]:
    """(problems, note). The note says how a data file earned its citation exemption, or ''."""
    problems: list[str] = []
    raw = read_bytes(path)
    text = read_text(raw)
    lowered_suffix = os.path.splitext(path)[1].lower()

    problems.extend(key_name_problems(text, rel))

    if lowered_suffix in CODE_SUFFIXES:
        for number, line in enumerate(text.splitlines(), start=1):
            body = code_part(line) if lowered_suffix in GML_SUFFIXES else line
            for url in URL_RE.finditer(body):
                problems.append("%s:%d: URL outside a comment in shipped code (%s)"
                                % (rel, number, url.group(0).split("//", 1)[0] + "//..."))
            for call in NETWORK_CALLS:
                if re.search(r"\b%s\b" % re.escape(call), body):
                    problems.append("%s:%d: names the GameMaker network function %s()"
                                    % (rel, number, call))
        return problems, ""

    if not rel.endswith(".json"):
        for number, line in enumerate(text.splitlines(), start=1):
            for url in URL_RE.finditer(line):
                problems.append("%s:%d: carries a URL (%s)" % (rel, number, url.group(0)))
        return problems, ""

    problems.extend(blob_problems(text, rel))
    if not URL_RE.search(text):
        return problems, ""

    if rel in NO_URL_FILES:
        for number, line in enumerate(text.splitlines(), start=1):
            for url in URL_RE.finditer(line):
                problems.append("%s:%d: the talk bake holds no URL, D5 and bake_meta --check both say "
                                "so (%s)" % (rel, number, url.group(0)))
        return problems, ""

    try:
        payload = json.loads(text)
    except ValueError as exc:
        problems.append("%s: does not parse as JSON, so no citation can be evidenced (%s)" % (rel, exc))
        return problems, ""

    # Endpoint keys and inline credentials are refused in every data file, exemption or not, so they
    # are measured before the file is allowed to claim its citations.
    problems.extend(url_key_problems(payload, rel, text))

    note = carries_provenance(payload)
    if not note:
        for number, line in enumerate(text.splitlines(), start=1):
            for url in URL_RE.finditer(line):
                problems.append("%s:%d: URL in a data file that declares no citation and no third "
                                "party provenance (%s)" % (rel, number, url.group(0)))
        return problems, ""

    return problems, note


def count_urls(path: str) -> int:
    """How many URLs a file holds, for the run line only. An unreadable file counts as zero."""
    try:
        return len(URL_RE.findall(read_text(read_bytes(path))))
    except OSError:
        return 0


def scan(root: str) -> tuple[list[str], dict[str, int], list[tuple[str, str]]]:
    """(problems, counts, exempted files). counts is what the run line reports."""
    problems: list[str] = []
    counts = {"files": 0, "gml": 0, "json": 0, "citation_files": 0, "urls": 0}
    exempted: list[tuple[str, str]] = []
    for path in shipped_files(root):
        rel = os.path.relpath(path, root).replace("\\", "/")
        found, note = scan_file(path, rel)
        problems.extend(found)
        counts["files"] += 1
        suffix = os.path.splitext(path)[1].lower()
        if suffix in GML_SUFFIXES:
            counts["gml"] += 1
        if suffix == ".json":
            counts["json"] += 1
        if note:
            counts["citation_files"] += 1
            exempted.append((rel, note))
        counts["urls"] += count_urls(path)
    counts["problems"] = len(problems)
    return problems, counts, exempted


# ---------------------------------------------------------------- the tests
def test_the_build_holds_no_endpoint_no_key_and_no_live_call():
    """D5 point 1: zero findings over every file that ships. The run line is the evidence."""
    problems, counts, exempted = scan(ROOT)
    print("check_no_network: %d files scanned (%d GML, %d JSON), %d credential names, %d network "
          "functions allowed, %d URL(s) seen in the tree, %d citation file(s) exempt by their own "
          "bytes, %d finding(s)"
          % (counts["files"], counts["gml"], counts["json"], len(KEY_NAMES), len(NETWORK_CALLS),
             counts["urls"], counts["citation_files"], len(problems)))
    for rel, note in exempted:
        print("citation URLs exempt (evidence inside the file): %s (%s)" % (rel, note))
    for problem in problems[:40]:
        print("REFUSED " + problem)
    if len(problems) > 40:
        print("... and %d more" % (len(problems) - 40))
    assert not problems, "%d finding(s), listed above with file and line" % len(problems)
    REPORT.update(counts)


def test_the_scan_is_not_vacuous():
    """A pass only means something if the scan actually walked a real tree."""
    counts = REPORT or scan(ROOT)[1]
    assert counts["files"] >= 500, "only %d shipped files found" % counts["files"]
    assert counts["gml"] >= 30, "only %d GML modules found" % counts["gml"]
    assert counts["json"] >= 200, "only %d JSON datafiles found" % counts["json"]
    # The bake is one of the files the scan must have refused a URL in, and it holds none today.
    assert os.path.isfile(SHIPPED_BAKE), "the engine's own copy of the bake is missing"
    _, _, exempted = scan(ROOT)
    names = {rel for rel, _note in exempted}
    assert any(name.endswith("music_recipes.json") for name in names), \
        "the citation exemption never fired, so the scan is not reading the citation tables"


def test_a_planted_url_in_a_data_file_is_refused(tmp_path):
    """The card's red case: a URL in a data file, named with the file and the line."""
    root = _tiny_tree(tmp_path)
    target = root / "data" / "audio.json"
    target.write_text(json.dumps({"format": 1, "kind": "audio",
                                  "tracks": [{"id": "pp_01", "endpoint": "https://api.meta.ai/v1"}]},
                                 indent=2), encoding="utf-8")
    problems, _counts, _exempted = scan(str(root))
    assert problems, "a URL under an endpoint key in data/audio.json went unnoticed"
    joined = "\n".join(problems)
    assert "data/audio.json" in joined, joined
    assert re.search(r"data/audio\.json:\d+: endpoint under key 'endpoint'", joined), joined


def test_a_plain_data_file_may_not_hold_a_citation_url_either(tmp_path):
    """No provenance block means no exemption at all, even for a harmless looking URL.

    This one plants into the built datafile (`game\\datafiles\\dialogue\\all.json`), which is the copy
    the engine actually reads, to prove the mirror is scanned and not just the source in data\\.
    """
    root = _tiny_tree(tmp_path)
    shipped = root / "game" / "datafiles" / "dialogue"
    shipped.mkdir(parents=True, exist_ok=True)
    target = shipped / "all.json"
    target.write_text(json.dumps({"entries": [{"id": "hound_win_kill", "lines": ["WIN."],
                                               "note": "read at https://en.wikipedia.org/wiki/Dog"}]},
                                 indent=2), encoding="utf-8")
    problems, counts, _exempted = scan(str(root))
    joined = "\n".join(problems)
    assert "game/datafiles/dialogue/all.json" in joined, joined
    assert "declares no citation" in joined, joined
    assert counts["files"] >= 1


def test_a_planted_key_name_in_a_gml_file_is_refused(tmp_path):
    """The card's second red case: a key name in a GML file, named with file and line."""
    root = _tiny_tree(tmp_path)
    target = root / "game" / "scripts" / "pp_meta" / "pp_meta.gml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("// meta reader\nfunction pp_meta_key() {\n"
                      "    return os_getenv(\"MODEL_API_KEY\");\n}\n", encoding="utf-8")
    problems, _counts, _exempted = scan(str(root))
    joined = "\n".join(problems)
    assert "game/scripts/pp_meta/pp_meta.gml:3: names the credential MODEL_API_KEY" in joined, joined


def test_a_planted_network_call_in_a_gml_file_is_refused(tmp_path):
    root = _tiny_tree(tmp_path)
    target = root / "game" / "scripts" / "pp_net" / "pp_net.gml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("var _req = http_get_file(\"data/meta_bake.json\", \"out.json\");\n",
                      encoding="utf-8")
    problems, _counts, _exempted = scan(str(root))
    joined = "\n".join(problems)
    assert "pp_net.gml:1: names the GameMaker network function http_get_file()" in joined, joined


def test_a_url_in_gml_code_is_refused_but_a_url_in_a_comment_is_not(tmp_path):
    root = _tiny_tree(tmp_path)
    code = root / "game" / "scripts" / "pp_url" / "pp_url.gml"
    code.parent.mkdir(parents=True, exist_ok=True)
    code.write_text("/// https://manual.gamemaker.io/monthly/en/ : the manual page this follows\n"
                    "var _where = \"https://api.meta.ai/v1\";\n", encoding="utf-8")
    problems, _counts, _exempted = scan(str(root))
    joined = "\n".join(problems)
    assert "pp_url.gml:2: URL outside a comment" in joined, joined
    assert "pp_url.gml:1" not in joined, joined


def test_the_credential_scan_names_the_variable_and_never_the_value(tmp_path):
    """A pasted key is named, and the paste itself is not repeated into a log or a report."""
    root = _tiny_tree(tmp_path)
    target = root / "game" / "scripts" / "pp_key" / "pp_key.gml"
    target.parent.mkdir(parents=True, exist_ok=True)
    planted_value = "fixture-not-a-real-credential-1234"
    target.write_text("var _k = \"%s\"; // MODEL_API_KEY\n" % planted_value, encoding="utf-8")
    problems, _counts, _exempted = scan(str(root))
    joined = "\n".join(problems)
    assert "MODEL_API_KEY" in joined, joined
    assert planted_value not in joined, "the scan reprinted the value it found"
    assert "pp_key.gml:1" in joined, joined


def test_an_endpoint_url_inside_a_citation_file_is_still_refused(tmp_path):
    """The exemption is about citations, never about endpoints: a citation file cannot hide one."""
    root = _tiny_tree(tmp_path)
    target = root / "data" / "music_recipes.json"
    target.write_text(json.dumps({"format": 1, "kind": "music_recipes",
                                  "sources": [{"id": "S1", "title": "NESdev",
                                               "url": "https://www.nesdev.org/wiki/APU"}],
                                  "api_base": "https://api.meta.ai/v1"}, indent=2),
                      encoding="utf-8")
    problems, counts, exempted = scan(str(root))
    joined = "\n".join(problems)
    assert counts["citation_files"] == 1 and exempted, "the citation file was not recognised"
    assert "endpoint under key 'api_base'" in joined, joined
    # ... and the citation URL that really is a citation is not refused.
    assert "nesdev.org" not in joined, joined


def test_a_base64_blob_over_4kb_in_data_is_refused(tmp_path):
    root = _tiny_tree(tmp_path)
    target = root / "data" / "audio.json"
    target.write_text(json.dumps({"format": 1, "kind": "audio", "blob": "A" * 5000}, indent=2),
                      encoding="utf-8")
    problems, _counts, _exempted = scan(str(root))
    joined = "\n".join(problems)
    assert "base64 blob of 5000 characters" in joined, joined
    assert "data/audio.json" in joined, joined


# ---------------------------------------------------------------- replay half
class _NoNetwork(object):
    """A transport that fails the test if the build tries to open anything at all."""

    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, *args, **kwargs):
        self.calls.append(str(args[0]) if args else "?")
        raise AssertionError("a network call escaped the replay build: %s" % (args[:1],))


@pytest.fixture()
def network_off(monkeypatch, tmp_path):
    """PP_AI_MODE=replay, no key, and a urlopen that is a tripwire rather than a client."""
    trap = _NoNetwork()
    for name in ("MODEL_API_KEY", "META_API_KEY", "GEMINI_API_KEY", "KAGGLE_API_TOKEN",
                 "PINE_SANDBOX_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PP_AI_MODE", "replay")
    monkeypatch.setenv("PP_AI_BACKEND", "meta")
    monkeypatch.setenv("PP_AI_CACHE", str(tmp_path / "empty_cache"))
    monkeypatch.setattr(urllib.request, "urlopen", trap)
    meta_client.reset_rate_state()
    return trap


def test_replay_mode_refuses_instead_of_calling(network_off):
    """With PP_AI_MODE=replay and no cache entry, the client refuses and never opens a socket."""
    assert meta_client.mode() == "replay"
    assert not meta_client.key_present()
    with pytest.raises(meta_client.CacheMiss):
        meta_client.chat([{"role": "user", "content": "R34 no network proof"}])
    assert network_off.calls == [], "urlopen was reached: %s" % network_off.calls


def test_the_bake_is_served_by_request_hash_with_the_network_off(network_off):
    """Spec 19 section 8 rung 1: rebuild the request from source data, then find the baked row."""
    served, missing, rows = _served_rows()
    assert rows, "data/meta_bake.json holds no rows"
    assert not missing, "no baked row for: %s" % "; ".join(missing[:6])
    assert len(served) == len(rows), "served %d of %d baked rows" % (len(served), len(rows))
    for row_id, row in served.items():
        assert row.get("source") == "fallback", "%s is not offline labelled" % row_id
        assert row.get("network") is False, "%s claims a network answer in a replay build" % row_id
        assert row.get("text"), "%s serves an empty box" % row_id
    assert network_off.calls == [], "urlopen was reached: %s" % network_off.calls


def test_the_engine_reads_the_same_bake_the_source_holds():
    """A stale mirror is a demo showing hand written text while the bake looks perfect."""
    if not os.path.isfile(SHIPPED_BAKE):
        pytest.fail("game/datafiles/meta_bake.json is missing, so the build carries no bake at all "
                    "(run python tools/sync_data.py)")
    source = read_bytes(BAKE_FILE)
    shipped = read_bytes(SHIPPED_BAKE)
    if source != shipped:
        source_rows = len(json.loads(read_text(source)).get("rows") or [])
        shipped_rows = len(json.loads(read_text(shipped)).get("rows") or [])
        pytest.fail("game/datafiles/meta_bake.json is stale: %d bytes and %d rows against the source "
                    "%d bytes and %d rows" % (len(shipped), shipped_rows, len(source), source_rows))


def _served_rows():
    """(served by id, missing ids, file rows): the rung 1 lookup, rebuilt from committed sources."""
    with open(BAKE_FILE, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    rows = document.get("rows") or []
    by_hash = {row.get("request_hash"): row for row in rows}
    model = (document.get("bake") or {}).get("model") or "muse-spark-1.3"
    system = bake_meta.load_system_text()
    _cards_doc, cards = bake_meta.load_cards()
    enemies = bake_meta.load_enemies()
    dialogue = bake_meta.load_dialogue()
    bank, blocks = bake_meta.load_gate_bank()

    served: dict[str, dict] = {}
    missing: list[str] = []
    last_reply: dict[str, str] = {}

    for unit in bake_meta.npc_plan(bank, blocks):
        npc = unit["npc"]
        scene = {"scene": "npc", "npc": npc["id"], "place": npc["place"], "turn": unit["turn"],
                 "mood": "guarded", "last_reply": last_reply.get(npc["id"], ""),
                 "allowed": list(bake_meta.NPC_EFFECTS)}
        _echo, digest = bake_meta.build_request("chat", model, system, unit["block"], scene, "")
        row_id = "npc/%s/turn_%d" % (npc["id"], unit["turn"])
        row = by_hash.get(digest)
        if row is None or row.get("id") != row_id:
            missing.append("%s (hash %s)" % (row_id, digest[:12]))
            continue
        served[row_id] = row
        last_reply[npc["id"]] = " ".join(row["text"])[:bake_meta.MAX_LAST_REPLY]

    units, _skipped = bake_meta.fight_plan(cards, enemies, dialogue)
    for unit in units:
        card = unit["card"]
        character = bake_meta.character_block(card, unit["enemy"])
        for index in range(1, bake_meta.OPTIONS_PER_UNIT + 1):
            scene = {"scene": "fight", "turn": index, "enemy_hp_band": "unhurt",
                     "player_hp_band": "steady", "mercy": (index - 1) * 20, "mood": "guarded",
                     "last_effect": "none",
                     "last_reply": last_reply.get(card["id"], ""),
                     "allowed": list(bake_meta.FIGHT_EFFECTS)}
            player_line = unit["option_lines"][index - 1]
            _echo, digest = bake_meta.build_request("chat", model, system, character, scene,
                                                    player_line)
            row_id = "fight/%s/%d" % (card["id"], index)
            row = by_hash.get(digest)
            if row is None or row.get("id") != row_id:
                missing.append("%s (hash %s)" % (row_id, digest[:12]))
                continue
            served[row_id] = row
            last_reply[card["id"]] = " ".join(row["text"])[:bake_meta.MAX_LAST_REPLY]

    return served, missing, rows


# ---------------------------------------------------------------- a tiny tree
def _tiny_tree(tmp_path):
    """A minimal but real shaped tree: the directories the scan walks, empty of data."""
    root = tmp_path / "build"
    for relative in ("game/scripts", "game/objects", "game/datafiles", "data", "data/dialogue"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "game" / "datafiles" / "meta_bake.json").write_text(
        json.dumps({"format": 1, "kind": "meta_bake", "bake": {"model": "muse-spark-1.3"},
                    "rows": []}, indent=2), encoding="utf-8")
    return root
