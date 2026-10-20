"""Tests for the project as text: the .yyp graph, the naming rules, the clean room checks and the static GML check.

These are the checks that can run on this PC today, with no GameMaker installed. They cannot prove the project opens;
they can prove it is internally consistent, which is the failure they are for.
"""

from __future__ import annotations

import json
import os
import re

import check_cleanroom
import check_data
import check_project
import check_provenance
import gen_project
import sync_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_project_graph_matches_disk():
    assert check_project.check(ROOT) == []


def test_every_yy_parses_as_strict_json():
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in filenames:
            if name.lower().endswith((".yy", ".yyp")):
                with open(os.path.join(dirpath, name), "r", encoding="utf-8") as fh:
                    json.load(fh)


def test_yyp_lists_every_script_object_and_room():
    with open(os.path.join(ROOT, "game", "PrimordialParadox.yyp"), "r", encoding="utf-8") as fh:
        yyp = json.load(fh)
    listed = {entry["id"]["name"] for entry in yyp["resources"]}

    expected = set()
    for kind in ("scripts", "objects", "rooms"):
        base = os.path.join(ROOT, "game", kind)
        for name in os.listdir(base):
            if os.path.isfile(os.path.join(base, name, name + ".yy")):
                expected.add(name)
    assert listed == expected


def test_naming_conventions():
    scripts = os.listdir(os.path.join(ROOT, "game", "scripts"))
    objects = os.listdir(os.path.join(ROOT, "game", "objects"))
    rooms = os.listdir(os.path.join(ROOT, "game", "rooms"))
    assert scripts and all(name.startswith("pp_") for name in scripts)
    assert objects and all(name.startswith("obj_pp_") for name in objects)
    assert rooms and all(name.startswith("rm_pp_") for name in rooms)


def test_generated_project_files_are_current():
    assert gen_project.main.__name__ == "main"
    import sys
    argv = sys.argv
    sys.argv = ["gen_project.py", "--check"]
    try:
        assert gen_project.main() == 0
    finally:
        sys.argv = argv


def test_datafiles_mirror_is_current():
    assert sync_data.main.__name__ == "main"
    import sys
    argv = sys.argv
    sys.argv = ["sync_data.py", "--check"]
    try:
        assert sync_data.main() == 0
    finally:
        sys.argv = argv


def test_cleanroom_passes():
    assert check_cleanroom.check(ROOT) == []


def test_provenance_covers_every_module():
    assert check_provenance.check(ROOT) == []


def test_data_passes():
    assert check_data.check(ROOT) == []


def test_no_em_or_en_dashes_anywhere():
    bad = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "study", "build", "__pycache__", ".pytest_cache")]
        for name in filenames:
            if not name.lower().endswith((".gml", ".json", ".md", ".py", ".ps1", ".vbs", ".yy", ".yyp", ".txt")):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="utf-8-sig") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            for index, line in enumerate(text.split("\n"), start=1):
                if "\u2013" in line or "\u2014" in line:
                    bad.append("%s:%d" % (os.path.relpath(path, ROOT), index))
    assert bad == []


def test_gml_calls_only_defined_pp_functions():
    """A compile-lite check: every pp_ function called somewhere is defined somewhere."""
    defined = set()
    called = set()
    files = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in filenames:
            if name.endswith(".gml"):
                files.append(os.path.join(dirpath, name))
    for path in files:
        with open(path, "r", encoding="utf-8-sig") as fh:
            text = fh.read()
        defined.update(re.findall(r"^function\s+([A-Za-z_]\w*)\s*\(", text, re.MULTILINE))
        called.update(re.findall(r"\b(pp_[a-z0-9_]+)\s*\(", text))
    missing = sorted(called - defined)
    assert missing == [], "called but never defined: %s" % missing


def test_gml_uses_only_defined_macros_and_enums():
    defined = set()
    used = set()
    files = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in filenames:
            if name.endswith(".gml"):
                files.append(os.path.join(dirpath, name))
    for path in files:
        with open(path, "r", encoding="utf-8-sig") as fh:
            text = fh.read()
        defined.update(re.findall(r"#macro\s+([A-Za-z_]\w*)", text))
        used.update(re.findall(r"\b(PP_[A-Z0-9_]+)\b", text))
    missing = sorted(used - defined)
    assert missing == [], "used but never defined: %s" % missing


def test_gml_does_not_read_keys_outside_the_input_module():
    offenders = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for name in filenames:
            if not name.endswith(".gml"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            if rel.endswith("scripts/pp_input/pp_input.gml"):
                continue
            with open(path, "r", encoding="utf-8-sig") as fh:
                text = fh.read()
            if re.search(r"\b(keyboard_check|gamepad_button_check|gamepad_axis_value)", text):
                offenders.append(rel)
    assert offenders == [], "raw input reads outside pp_input: %s" % offenders
