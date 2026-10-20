"""Prove the clean room, mechanically, as far as a text comparison can.

Four tests, all fail closed:

1. NO STUDY DEPENDENCY. Nothing under game\\ or data\\ may name the study copies. The game must build from this
   repository alone.
2. NO FOREIGN NAMES. A short list of character and game names from the studied games is refused as a whole word
   anywhere in our text, so no name can arrive by accident.
3. NO COPIED EXPRESSION. Every comment (GML) and every string value (JSON data) here that is 20 characters or longer
   is compared, normalised for whitespace and case, against the same extract from every .gml file in the study copy.
   A comment or a line of dialogue that appears word for word in the studied project is exactly what would make this
   repository a copy, so it fails loudly. Short strings and identifiers are ignored, because builtin API calls and
   ordinary words necessarily coincide.
4. NO SHARED IDENTIFIER. Every pp_ identifier here is checked against the study copy. A pp_ name cannot exist there,
   so a hit means an identifier arrived by paste.

If the study copy is absent (a fresh clone never has it), tests 3 and 4 report SKIP. That is honest: they are
comparisons, and there is nothing to compare against.

Usage:
    python tools/check_cleanroom.py
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY = os.path.join(ROOT, "knowledge", "study")
MIN_EXPRESSION = 20

FOREIGN_NAMES = [
    "undertale", "deltarune", "kris", "susie", "ralsei", "noelle", "berdly",
    "undyne", "toriel", "asgore", "alphys", "papyrus", "napstablook", "asriel",
    "chara", "frisk", "gaster", "jevil", "spamton",
]

COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
IDENT_RE = re.compile(r"\bpp_[A-Za-z0-9_]+")


def text_files(base: str, suffixes: tuple[str, ...]):
    for dirpath, _dirnames, filenames in os.walk(base):
        for fname in filenames:
            if fname.lower().endswith(suffixes):
                yield os.path.join(dirpath, fname)


def read(path: str) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as fh:
                return fh.read()
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def expressions(text: str, json_mode: bool) -> list[tuple[str, int]]:
    """Comments in GML, string values in JSON, each with the line it starts on."""
    found: list[tuple[str, int]] = []
    if json_mode:
        for match in STRING_RE.finditer(text):
            value = match.group(1)
            if len(value) >= MIN_EXPRESSION:
                found.append((value, text.count("\n", 0, match.start()) + 1))
        return found
    for match in COMMENT_RE.finditer(text):
        raw = match.group(0)
        raw = raw[2:] if raw.startswith("//") else raw[2:-2]
        line = text.count("\n", 0, match.start()) + 1
        for piece in raw.split("\n"):
            piece = piece.strip().lstrip("/").strip()
            if len(piece) >= MIN_EXPRESSION:
                found.append((piece, line))
    return found


def check(root: str = ROOT) -> list[str]:
    errors: list[str] = []
    game = os.path.join(root, "game")
    data = os.path.join(root, "data")

    for base in (game, data):
        for path in text_files(base, (".gml", ".json", ".yy", ".yyp")):
            text = read(path)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if "knowledge/study" in text or "knowledge\\study" in text:
                errors.append("%s: names the study copies" % rel)

    name_re = re.compile(r"\b(" + "|".join(FOREIGN_NAMES) + r")\b", re.IGNORECASE)
    for base in (game, data):
        for path in text_files(base, (".gml", ".json", ".yy", ".yyp", ".md")):
            text = read(path)
            rel = os.path.relpath(path, root).replace("\\", "/")
            for match in name_re.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append("%s:%d: foreign name %r" % (rel, line, match.group(0)))
                break

    if not os.path.isdir(STUDY):
        print("check_cleanroom: SKIP the comparison tests, knowledge/study is not present")
        return errors

    study_expressions: set[str] = set()
    study_identifiers: set[str] = set()
    study_files = 0
    for path in text_files(STUDY, (".gml",)):
        study_files += 1
        text = read(path)
        for value, _line in expressions(text, json_mode=False):
            study_expressions.add(normalise(value))
        for match in STRING_RE.finditer(text):
            value = match.group(1)
            if len(value) >= MIN_EXPRESSION:
                study_expressions.add(normalise(value))
        study_identifiers.update(match.group(0).lower() for match in IDENT_RE.finditer(text))

    compared = 0
    hits = 0
    for path in text_files(game, (".gml", ".json")):
        rel = os.path.relpath(path, root).replace("\\", "/")
        text = read(path)
        is_json = path.lower().endswith(".json")
        for value, line in expressions(text, json_mode=is_json):
            compared += 1
            if normalise(value) in study_expressions:
                hits += 1
                errors.append("%s:%d: this text appears word for word in the study copy: %r"
                              % (rel, line, value[:60]))
        if not is_json:
            for match in IDENT_RE.finditer(text):
                if match.group(0).lower() in study_identifiers:
                    line = text.count("\n", 0, match.start()) + 1
                    errors.append("%s:%d: identifier %r exists in the study copy"
                                  % (rel, line, match.group(0)))

    print("check_cleanroom: %d comments and strings compared against %d study .gml files, %d matches"
          % (compared, study_files, hits))
    return errors


def main() -> int:
    errors = check()
    if errors:
        for line in errors[:40]:
            print("FAIL " + line)
        if len(errors) > 40:
            print("... and %d more" % (len(errors) - 40))
        print("\n%d clean room problem(s)" % len(errors))
        return 1
    print("check_cleanroom: no study dependency, no foreign names, no copied text or identifiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
