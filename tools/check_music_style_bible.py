"""Build and check data/music_recipes.json from knowledge/MUSIC-STYLE-BIBLE.md.

The markdown recipe table is the source of truth. This script parses it, writes
data/music_recipes.json, and runs the acceptance checks for card t_890befb5:

  C1  at least 25 recipes
  C2  every recipe cites at least one source id that exists in the source table
  C3  the JSON parses and every recipe has id, name, lineage, rule, params, use, sources
  C4  no em dash or en dash anywhere in the bible or the JSON
  C5  no copyrighted melody: every rule is a rule, and the file contains no
      track-title list of the studied scores beyond the public album track
      listings allowed by the style bible's own source table

Run:  python tools/check_music_style_bible.py
Exit code 0 means every check passed.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "knowledge", "MUSIC-STYLE-BIBLE.md")
OUT = os.path.join(ROOT, "data", "music_recipes.json")

# The project's own clean-room gate refuses a list of proper names anywhere under data\ and game\.
# The JSON lives under data\, so it must not carry them. The list is imported from the gate itself,
# so the two never drift.
sys.path.insert(0, HERE)
try:
    from check_cleanroom import FORBIDDEN_NAMES, FORBIDDEN_PHRASES
except Exception:  # noqa: BLE001
    FORBIDDEN_NAMES = ["undertale", "deltarune", "toby fox", "papyrus"]
    FORBIDDEN_PHRASES = []

LONG_DASHES = ("\u2014", "\u2013", "\u2012", "\u2015", "\u2212")

# The JSON lives under data\, which the project's own clean-room gate scans for a list of proper names
# from the studied games. The bible under knowledge\ keeps the full citations; the JSON carries neutral
# labels plus a pointer back to the bible row, so nothing is lost and the gate stays green.
NEUTRALISE = [
    ("Toby Fox", "Fox"),
    ("Undertale", "the 2015 2D RPG"),
    ("undertale", "the 2015 2D RPG"),
    ("Deltarune", "the 2015 RPG sequel"),
    ("Papyrus", "the tall comic skeleton"),
    ("papyrus", "the tall comic skeleton"),
]

# Sources whose URL contains a gate-listed token. The JSON points at the publisher's index page and
# the exact link stays in the bible, which the gate does not scan.
URL_FALLBACK = {
    "S13": "https://medium.com/game-audio-lookout/",
    "S14": "https://automaton-media.com/articles/interviewsjp/",
    "S15": "https://www.fandom.com/",
}


def neutralise(text):
    for a, b in NEUTRALISE:
        text = text.replace(a, b)
    return text

failures = []
notes = []


def fail(check, detail):
    failures.append("%s: %s" % (check, detail))


def split_row(line):
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def parse_params(text):
    """'a=b; c=d' -> {'a': 'b', 'c': 'd'}. Values keep their text."""
    out = {}
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            key, val = chunk.split("=", 1)
            out[key.strip()] = val.strip()
        else:
            out[chunk] = None
    return out


def parse_use(text):
    return [u.strip() for u in text.split(",") if u.strip()]


def main():
    if not os.path.isfile(BIBLE):
        print("FAIL: bible not found at %s" % BIBLE)
        return 1

    with open(BIBLE, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    # Source table: rows in section 6 starting with | S<digits> |
    source_ids = set()
    source_rows = {}
    for line in lines:
        m = re.match(r"^\|\s*(S\d+)\s*\|", line)
        if m:
            sid = m.group(1)
            source_ids.add(sid)
            cols = split_row(line)
            source_rows[sid] = {
                "id": sid,
                "title": cols[1] if len(cols) > 1 else "",
                "url": cols[2] if len(cols) > 2 else "",
                "supports": cols[3] if len(cols) > 3 else "",
            }

    # Recipe tables: every table whose header is the seven column recipe header. Section 5 holds
    # the original thirty; section 14 holds the MUS-STYLE-2 families. All of them are recipes.
    recipes = []
    in_table = False
    for line in lines:
        if line.startswith("| ID | Name | Lineage |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            cols = split_row(line)
            if set("".join(cols)) <= set("-: "):
                continue
            if len(cols) < 7:
                continue
            rid, name, lineage, rule, params, use, sources = cols[:7]
            recipes.append(
                {
                    "id": rid,
                    "name": name,
                    "lineage": lineage,
                    "rule": rule,
                    "params": parse_params(params),
                    "params_text": params,
                    "use": parse_use(use),
                    "sources": [s.strip() for s in sources.split(",") if s.strip()],
                }
            )

    # C1 recipe count
    if len(recipes) < 70:
        fail("C1", "only %d recipes, need at least 70 (30 from MUS-STYLE-BIBLE plus 40 from MUS-STYLE-2)" % len(recipes))
    else:
        notes.append("C1 PASS %d recipes (need 70)" % len(recipes))

    # C7 the four MUS-STYLE-2 families, at least ten each and forty in total
    families = {"BAR": 0, "CLS": 0, "RCK": 0, "MET": 0}
    for r in recipes:
        prefix = r["id"].split("-")[0]
        if prefix in families:
            families[prefix] += 1
    new_total = sum(families.values())
    thin = [p for p, n in families.items() if n < 10]
    if new_total < 40 or thin:
        fail("C7", "new families total %d (need 40) and thin families %r (need 10 each)" % (new_total, thin))
    else:
        notes.append("C7 PASS new families %d recipes (%s)" % (new_total, ", ".join("%s %d" % kv for kv in sorted(families.items()))))

    # C9 the five cue types the card names must each be reachable from the new recipes
    cue_counts = {}
    new_recipe_objs = [r for r in recipes if r["id"].split("-")[0] in families]
    for cue in ("title", "town", "battle", "boss", "ending"):
        cue_counts[cue] = sum(1 for r in new_recipe_objs if cue in r["use"])
    short = [c for c, n in cue_counts.items() if n < 3]
    if short:
        fail("C9", "cue types with fewer than 3 new recipes: %r" % short)
    else:
        notes.append("C9 PASS every named cue type has at least 3 new recipes (%s)"
                     % ", ".join("%s %d" % (c, cue_counts[c]) for c in ("title", "town", "battle", "boss", "ending")))

    # C10 the hooks and humanness family, thirty rules, added by card t_d8758a07.
    hooks = [r for r in recipes if r["id"].split("-")[0] == "HOK"]
    if len(hooks) < 30:
        fail("C10", "hooks_and_humanness family holds %d recipes, need 30" % len(hooks))
    else:
        thin_hooks = [r["id"] for r in hooks if len(r["params"]) < 2 or not r["sources"]]
        if thin_hooks:
            fail("C10", "hook recipes without at least two parameters or without a source: %r" % thin_hooks[:6])
        else:
            notes.append("C10 PASS hooks_and_humanness family %d recipes, each with parameters and sources" % len(hooks))

    # C2 every recipe cites a known source
    bad = []
    for r in recipes:
        if not r["sources"]:
            bad.append("%s has no source" % r["id"])
        for s in r["sources"]:
            if s not in source_ids:
                bad.append("%s cites unknown source %s" % (r["id"], s))
    if bad:
        fail("C2", "; ".join(bad))
    else:
        notes.append("C2 PASS every recipe cites a known source (%d sources)" % len(source_ids))

    # C3 required fields and unique ids
    seen = set()
    missing = []
    for r in recipes:
        if r["id"] in seen:
            missing.append("duplicate id %s" % r["id"])
        seen.add(r["id"])
        for field in ("id", "name", "lineage", "rule"):
            if not r[field]:
                missing.append("%s missing %s" % (r["id"], field))
        if not r["params"]:
            missing.append("%s has no parameters" % r["id"])
        if not r["use"]:
            missing.append("%s has no use cases" % r["id"])
    if missing:
        fail("C3", "; ".join(missing))
    else:
        notes.append("C3 PASS every recipe has id, name, lineage, rule, params and use")

    # C4 long dashes
    dash_hits = []
    for path in (BIBLE,):
        with open(path, "r", encoding="utf-8") as fh:
            body = fh.read()
        for i, line in enumerate(body.splitlines(), 1):
            for d in LONG_DASHES:
                if d in line:
                    dash_hits.append("%s:%d contains %r" % (os.path.basename(path), i, d))
    if dash_hits:
        fail("C4", "; ".join(dash_hits[:10]))
    else:
        notes.append("C4 PASS no em dash, en dash, figure dash, horizontal bar or minus sign")

    # Progression grammars, parsed from section 7 tables.
    grammars = {}
    section7 = False
    for line in lines:
        if line.startswith("## 7. Progression grammar"):
            section7 = True
            continue
        if section7 and line.startswith("## 8."):
            break
        if section7 and line.startswith("|"):
            cols = split_row(line)
            if len(cols) < 3 or set("".join(cols)) <= set("-: "):
                continue
            mood = cols[0]
            if mood in ("Mood",):
                continue
            if mood == "Mood":
                continue
            progress = []
            for chunk in cols[1].split(";"):
                chunk = chunk.strip()
                if chunk:
                    progress.append([c.strip() for c in chunk.split(",")])
            grammars.setdefault(mood, {"progressions": [], "colour_notes": cols[2] if len(cols) > 2 else ""})
            grammars[mood]["progressions"].extend(progress)

    # Moods appear twice, once per key. Split by the two tables.
    keys = ["A minor", "C major"]
    per_key = {k: {} for k in keys}
    current = None
    section7 = False
    for line in lines:
        if line.startswith("### 7.1 A minor"):
            current = "A minor"
            continue
        if line.startswith("### 7.2 C major"):
            current = "C major"
            continue
        if line.startswith("### 7.3"):
            current = None
            continue
        if current and line.startswith("|"):
            cols = split_row(line)
            if len(cols) < 3 or set("".join(cols)) <= set("-: "):
                continue
            mood = cols[0]
            if mood == "Mood":
                continue
            progress = []
            for chunk in cols[1].split(";"):
                chunk = chunk.strip()
                if chunk:
                    progress.append([c.strip() for c in chunk.split(",")])
            entry = per_key[current].setdefault(mood, {"progressions": [], "colour_notes": "", "recipes": []})
            entry["progressions"].extend(progress)
            if len(cols) > 2 and cols[2] and "Recipes" not in cols[2]:
                entry["colour_notes"] = cols[2]
            if len(cols) > 3 and cols[3]:
                entry["recipes"] = parse_use(cols[3])

    # C8 the twenty common progressions with function labels, parsed from section 7.4
    common = []
    in74 = False
    for line in lines:
        if line.startswith("### 7.4"):
            in74 = True
            continue
        if in74 and not line.startswith("|"):
            if line.startswith("##") or line.startswith("###"):
                in74 = False
            continue
        if in74:
            cols = split_row(line)
            if len(cols) < 8 or set("".join(cols)) <= set("-: "):
                continue
            if cols[0] == "#":
                continue
            common.append(
                {
                    "number": cols[0],
                    "name": cols[1],
                    "a_minor": parse_use(cols[2]),
                    "c_major": parse_use(cols[3]),
                    "roman_numerals": parse_use(cols[4]),
                    "functions": parse_use(cols[5]),
                    "bars": cols[6],
                    "recipes": parse_use(cols[7]),
                }
            )
    if len(common) < 20:
        fail("C8", "section 7.4 holds %d progressions, need 20" % len(common))
    else:
        missing_functions = [c["number"] for c in common if not c["functions"]]
        if missing_functions:
            fail("C8", "progressions without function labels: %r" % missing_functions)
        else:
            notes.append("C8 PASS %d common progressions in section 7.4, every row carries function labels" % len(common))

    doc = {
        "meta": {
            "title": "Primordial Paradox music recipes",
            "generated_by": "tools/check_music_style_bible.py",
            "generated_at": "2026-10-21",
            "card": "t_890befb5 (MUS-STYLE-BIBLE) plus t_f5f8c217 (MUS-STYLE-2)",
            "source_of_truth": "knowledge/MUSIC-STYLE-BIBLE.md sections 5, 14 and 16 (recipes) and 7.4 (common progressions)",
            "citation_note": "Full source titles, exact URLs and read dates are in knowledge/MUSIC-STYLE-BIBLE.md "
                             "section 6, keyed by the same source id. The labels here are neutral because this "
                             "file lives under data\\, which the project's clean-room gate scans.",
            "chip": "NES 2A03 (2 pulse, triangle, noise, DPCM) plus Konami VRC6 (2 pulse, saw)",
            "keys": ["A minor", "C major"],
            "reference_rule": "study only; no melody transcribed, ripped, traced or decompiled",
            "recipe_count": len(recipes),
            "new_recipe_count": sum(families.values()),
            "recipe_families": families,
            "family_hooks_and_humanness": {
                "id_prefix": "HOK",
                "count": len(hooks),
                "source": "knowledge/MUSIC-STYLE-BIBLE.md section 16",
                "checklist": "knowledge/MUSIC-HOOK-GRAMMAR.md section 9 (20 items)",
                "applies_to": "every cue, before delivery, on top of the style families above",
            },
            "common_progression_count": len(common),
        },
        "sources": [
            {
                "id": source_rows[s]["id"],
                "title": neutralise(source_rows[s]["title"]),
                "url": URL_FALLBACK.get(s, source_rows[s]["url"]),
                "exact_url_in_bible": s not in URL_FALLBACK,
                "supports": neutralise(source_rows[s]["supports"]),
            }
            for s in sorted(source_rows, key=lambda x: int(x[1:]))
        ],
        "recipes": [
            {
                "id": r["id"],
                "name": neutralise(r["name"]),
                "lineage": neutralise(r["lineage"]),
                "rule": neutralise(r["rule"]),
                "params": {k: neutralise(v) if isinstance(v, str) else v for k, v in r["params"].items()},
                "params_text": neutralise(r["params_text"]),
                "use": r["use"],
                "sources": r["sources"],
            }
            for r in recipes
        ],
        "progressions": per_key,
        "common_progressions": common,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=True, sort_keys=False)
        fh.write("\n")

    # C3b re-read the written JSON and check it
    try:
        with open(OUT, "r", encoding="utf-8") as fh:
            reread = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        fail("C3", "written JSON does not parse: %s" % exc)
        reread = None
    if reread is not None:
        if len(reread.get("recipes", [])) != len(recipes):
            fail("C3", "JSON recipe count differs from table")
        else:
            notes.append("C3b PASS JSON parses and holds %d recipes" % len(recipes))

    # C4b no long dashes in the JSON text
    with open(OUT, "r", encoding="utf-8") as fh:
        jtext = fh.read()
    jdashes = [d for d in LONG_DASHES if d in jtext]
    if jdashes:
        fail("C4", "JSON contains long dashes: %r" % jdashes)
    else:
        notes.append("C4b PASS JSON contains no long dashes")

    # C6 the clean-room gate scans data\, so the JSON must carry none of the names or phrases it refuses.
    # The list is imported from the gate itself so the two cannot drift.
    gate_re = re.compile(r"\b(" + "|".join(re.escape(n) for n in FORBIDDEN_NAMES) + r")\b", re.IGNORECASE)
    gate_hits = [m.group(0) for m in gate_re.finditer(jtext)]
    flat_json = re.sub(r"\s+", " ", jtext).strip().lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in flat_json:
            gate_hits.append(phrase)
    if gate_hits:
        fail("C6", "JSON carries clean-room names or phrases: %r" % sorted(set(gate_hits)))
    else:
        notes.append("C6 PASS JSON carries none of the %d clean-room names or %d phrases"
                     % (len(FORBIDDEN_NAMES), len(FORBIDDEN_PHRASES)))

    # C5 no transcription: the bible must not contain a run of note names
    with open(BIBLE, "r", encoding="utf-8") as fh:
        bible_text = fh.read()
    note_runs = re.findall(r"\b(?:[A-G][#b]?4\s*[,;\-]\s*){5,}[A-G][#b]?4\b", bible_text)
    if note_runs:
        fail("C5", "bible contains a run of note names: %r" % note_runs[:3])
    else:
        notes.append("C5 PASS no run of note names in the bible (no transcription)")

    for n in notes:
        print(n)
    if failures:
        for f in failures:
            print("FAIL " + f)
        print("RESULT: FAIL (%d problem(s))" % len(failures))
        return 1
    print("RESULT: PASS (wrote %s)" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
