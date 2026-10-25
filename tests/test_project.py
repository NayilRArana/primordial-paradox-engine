"""Tests for the project as text: the .yyp graph, the naming rules, the clean room checks and the static GML check.

These are the checks that can run on this PC today, with no GameMaker installed. They cannot prove the project opens;
they can prove it is internally consistent, which is the failure they are for.
"""

from __future__ import annotations

import json
import os
import re

import pytest

import check_build_inputs
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


def test_build_time_data_is_kept_out_of_the_bundle():
    """The mirror is a runtime question: a table no GML opens is not an Included File.

    data/palette_recipes.json and data/scene_palettes.json are read by tools, by path, out of data\\: the palette
    checker, the synergy gate, the scene palette builder and the NES audit. Mirroring them made the .yyp declare two
    build inputs as Included Files, so every palette rebuild was a file the commit had to carry or the nightly
    worktree reported as missing (card t_40501f46).

    The names are asserted one by one on purpose. Reading them out of sync_data.NOT_RUNTIME instead would make the
    test vacuous the moment someone deletes an entry from that set, which is the exact edit it exists to catch (the
    mutation was run: dropping scene_palettes.json from the set passed a set driven version of this test). The last
    check is the one that says what to do when the answer changes: if a module ever reads one of these tables at
    runtime, this fails and names the file to mirror again.
    """
    table_names = ("palette_recipes.json", "scene_palettes.json")
    wanted = set(sync_data.source_files())
    for name in table_names:
        assert name in sync_data.NOT_RUNTIME, (
            "%s is no longer excluded in tools/sync_data.py, so it is either mirrored again or silently dropped"
            % name)
        assert name not in wanted, "%s is excluded from the bundle but sync_data still mirrors it" % name

    with open(os.path.join(ROOT, "game", "PrimordialParadox.yyp"), "r", encoding="utf-8") as fh:
        declared = {entry.get("name") for entry in json.load(fh)["IncludedFiles"]}
    for name in table_names:
        assert name not in declared, "the committed project declares %s as an Included File" % name

    gml = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for filename in filenames:
            if filename.endswith(".gml"):
                with open(os.path.join(dirpath, filename), "r", encoding="utf-8-sig") as fh:
                    gml.append(fh.read())
    blob = "\n".join(gml)
    for name in table_names:
        assert name not in blob, (
            "%s is excluded from the bundle but a GML module names it: take it out of sync_data.NOT_RUNTIME "
            "so the engine ships it" % name)


# Card TEST-CLASSIFY-33: the last assertion lists the tracked sources through git, and a zip of the
# tree has no history, so off the box this is a skip and not a verdict.
@pytest.mark.needs_git_checkout
def test_the_ai_cache_is_kept_out_of_the_bundle():
    """The Meta client's recorded answers are a build input read by tools, never by GML.

    tools/meta_client.py writes data/ai_cache/<sha256>.json and reads it back by path, and no GML module names the
    directory. Mirroring it put six hash named files into game/datafiles and the .yyp then wanted each of them as an
    Included File: tools/check_project.py reported all six on 2026-10-22 and took the project check red (card
    t_6f73263f). The exclusion is pinned here the same one by one way as the palette tables above, so deleting it
    fails in this test rather than in the build. The last check is the opposite direction: the cache has to stay in
    the commit, because replay and the offline demo read it out of data\\.
    """
    assert "ai_cache/" in sync_data.NOT_RUNTIME_DIRS, (
        "ai_cache/ is no longer excluded in tools/sync_data.py, so the recorded answers are mirrored again")
    wanted = sync_data.source_files()
    mirrored = [rel for rel in wanted if rel.startswith("ai_cache/")]
    assert mirrored == [], "sync_data still mirrors the Meta cache into the bundle: %r" % mirrored

    with open(os.path.join(ROOT, "game", "PrimordialParadox.yyp"), "r", encoding="utf-8") as fh:
        declared = {entry.get("name") for entry in json.load(fh)["IncludedFiles"]}
    assert [name for name in declared if "ai_cache/" in name] == [], (
        "the committed project declares a Meta cache entry as an Included File")

    gml = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "game")):
        for filename in filenames:
            if filename.endswith(".gml"):
                with open(os.path.join(dirpath, filename), "r", encoding="utf-8-sig") as fh:
                    gml.append(fh.read())
    assert "ai_cache" not in "\n".join(gml), (
        "a GML module names ai_cache: if the engine reads it, take it out of NOT_RUNTIME_DIRS so it ships")

    repo = check_build_inputs.repo_root()
    tracked = check_build_inputs.tracked_files(repo)
    entries = sorted(name for name in os.listdir(os.path.join(ROOT, "data", "ai_cache"))
                     if name.endswith(".json"))
    assert entries, "data/ai_cache holds no recorded answer, so replay has nothing to serve"
    for name in entries:
        rel = os.path.relpath(os.path.join(ROOT, "data", "ai_cache", name), repo).replace(os.sep, "/")
        assert rel in tracked, "%s is not in the commit, so replay cannot answer from it" % rel


# Card TEST-CLASSIFY-33: reads the tracked file list out of git, which a zip of the tree cannot answer.
@pytest.mark.needs_git_checkout
def test_the_palette_tables_stay_committed_where_the_tests_read_them():
    """Not mirrored, still tracked.

    tests/test_scene_palette_set.py loads data\\scene_palettes.json through tools/scene_palette_set.py, which refuses a
    missing file rather than reading an empty set, and tools/palette_synergy.py --gate reads its audit list. So the
    file has to be in the commit even though the bundle does not carry it. Untracked was the state card t_40501f46
    found, and a HEAD worktree failed on it.
    """
    repo = check_build_inputs.repo_root()
    tracked = check_build_inputs.tracked_files(repo)
    for name in ("data/palette_recipes.json", "data/scene_palettes.json"):
        rel = os.path.relpath(os.path.join(ROOT, name), repo).replace(os.sep, "/")
        assert rel in tracked, "%s is not in the commit, so a HEAD worktree cannot read it" % rel


def test_cleanroom_passes():
    assert check_cleanroom.check(ROOT) == []


def test_provenance_covers_every_module():
    assert check_provenance.check(ROOT) == []


def test_data_passes():
    assert check_data.check(ROOT) == []


# Card TEST-CLASSIFY-33: tools/check_build_inputs.py asks git what the commit carries, and it exits
# with "not inside a git repository" on a copy of the tree, which is a skip and not a defect.
@pytest.mark.needs_git_checkout
def test_build_inputs_are_committed():
    """Every Included File the project declares must resolve to a source the commit carries.

    This is the assertion that turns "HEAD references a file HEAD lacks" from dozens of unrelated
    FileNotFoundError in the nightly worktree into one named failure here.
    """
    assert check_build_inputs.check(ROOT) == []


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


def gml_code_only(text):
    """Drop // and /// comments so the static checks read code, not prose.

    A comment that names a module ("performed by pp_app") is not a call. This used to trip the call audit, so the
    stripping lives here, in one place, and both audits use it.
    """
    lines = []
    for line in text.split("\n"):
        cut = line.find("//")
        lines.append(line if cut == -1 else line[:cut])
    return "\n".join(lines)


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
            text = gml_code_only(fh.read())
        defined.update(re.findall(r"^function\s+([A-Za-z_]\w*)\s*\(", text, re.MULTILINE))
        called.update(re.findall(r"\b(pp_[a-z0-9_]+)\s*\(", text))
    missing = sorted(called - defined)
    assert missing == [], "called but never defined: %s" % missing


def test_comment_mention_of_a_module_is_not_a_call():
    """The audit above must not read prose as code."""
    prose = "/// a battle is a mode swap performed by pp_app (specs 01 and 04).\n"
    assert re.findall(r"\b(pp_[a-z0-9_]+)\s*\(", gml_code_only(prose)) == []


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


# ---------------------------------------------------------------------------------------------------------------
# Defects that the text can prove without an engine. Each of these pins a bug that would only surface at the first run,
# so a later edit that brings the bug back fails here instead of mid fight.

def read_gml(relative):
    with open(os.path.join(ROOT, "game", "scripts", relative), "r", encoding="utf-8-sig") as fh:
        return gml_code_only(fh.read())


def brace_block(text, marker):
    """The brace balanced block that starts at the first '{' after marker."""
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


def test_scene_battle_request_is_drained_while_a_scene_runs():
    """A scene `battle` command used to deadlock: pp_scene set battle_request and waited for battle_done, but the test
    for pp_scene_running returned before the only drain, and only the overworld could start the fight."""
    code = read_gml("pp_overworld/pp_overworld.gml")
    branch = brace_block(code, "if (pp_scene_running(_world.scene)) {")
    drain = "pp_app_request(PPMode.battle"
    assert drain in branch, "the scene branch must drain battle_request itself"
    assert branch.index(drain) < branch.index("return;"), "the drain must run before the scene branch returns"
    assert code.count("pp_app_request(PPMode.battle") == 2, "one drain for a scene and one for free walking"


def test_recipe_angle_is_mirrored_once_by_pp_angle_to_gm():
    """Delta C5: recipes are written as screen angles (0 right, 90 down) and GameMaker directions point the other way,
    so the emitter converts exactly once and the arena never sees a raw data angle again."""
    arena = read_gml("pp_dodge_arena/pp_dodge_arena.gml")
    recipe = read_gml("pp_dodge_recipe/pp_dodge_recipe.gml")
    assert "function pp_angle_to_gm(_data_angle)" in arena

    spawn = recipe[recipe.index("function pp_recipe_spawn"):]
    assert "pp_angle_to_gm(_ev.angle)" in spawn
    assert "dir: _dir" in spawn
    assert "curve: -_ev.curve" in spawn
    assert "_ev.angle" not in spawn[spawn.index("pp_angle_to_gm(_ev.angle)") + len("pp_angle_to_gm(_ev.angle)"):], \
        "the raw data angle must be used once, by the conversion"

    move = arena[arena.index("function pp_arena_move_hazards"):]
    assert "lengthdir_x(_hz.speed, _hz.dir)" in move
    assert "_hz.angle" not in arena, "the arena works in GameMaker directions only"


def test_pp_angle_to_gm_formula_matches_the_checker():
    """The engine cannot be run here, so the sign is pinned where it lives: the function body is read out of the GML,
    its `mod` translated to Python's `%`, and every value compared with tools/check_data.py's mirror. Flip the sign in
    either place and this fails."""
    arena = read_gml("pp_dodge_arena/pp_dodge_arena.gml")
    body = arena[arena.index("function pp_angle_to_gm"):]
    match = re.search(r"return\s+(.+?);", body, re.S)
    assert match is not None, "pp_angle_to_gm must have a single return expression"
    python_expression = match.group(1).replace(" mod ", " % ")
    for data_angle in (0, 30, 90, 180, 270, 359, 450, -90):
        engine = eval(python_expression, {"__builtins__": {}}, {"_data_angle": data_angle})
        assert engine == check_data.angle_to_gm(data_angle), \
            "pp_angle_to_gm(%s) is %s in GML but %s in the checker" % (
                data_angle, engine, check_data.angle_to_gm(data_angle))


def test_no_key_or_button_belongs_to_two_input_actions():
    """One key firing two actions is a silent double fire, and this table is what a later options screen reads."""
    table = read_gml("pp_input/pp_input.gml")
    table = table[table.index("function pp_input_table"):]
    table = table[:table.index("\n}")]
    owners = {}
    for row in re.findall(r"\{[^{}]*\}", table):
        action = re.search(r'id:\s*"([a-z_]+)"', row)
        if action is None:
            continue
        for field in ("keys", "pads"):
            group = re.search(r"%s:\s*\[([^\]]*)\]" % field, row)
            if group is None:
                continue
            for token in [part.strip() for part in group.group(1).split(",") if part.strip()]:
                owners.setdefault(token, []).append(action.group(1))
    shared = {token: users for token, users in owners.items() if len(users) > 1}
    assert shared == {}, "a key or button bound to more than one action: %s" % shared


def test_defeat_restores_health_before_it_reaches_the_ledger():
    """A defeat used to write hp 0 into the ledger, and the next fight starts from the ledger."""
    director = read_gml("pp_battle_director/pp_battle_director.gml")
    body = director[director.index("function pp_battle_record"):]
    body = body[:body.index("\n}")]
    assert "_battle.defeated" in body
    restore = body.index("_battle.actor.hp = _battle.actor.max_hp;")
    write = body.index("_battle.ledger.hp = _battle.actor.hp;")
    assert restore < write, "restore on defeat must happen before the ledger write"
