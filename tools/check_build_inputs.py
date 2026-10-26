"""Every Included File the committed project demands must resolve to a source the commit carries.

Why this exists. The audit nightly builds a detached worktree at HEAD, so a file that lives only in
the live tree is absent there while the suite that reads it sits fine in the working tree. On
2026-10-22 that cost 88 failures and 23 errors at commit dc104a7. Four theme .ogg streams and two
.mid scores were named as Included Files by the committed game/PrimordialParadox.yyp while the
commit did not contain them, and the two MIDI exceptions in the root .gitignore sat above the
blanket *.mid rule, so they had never taken effect at all. The suite reported that as dozens of
unrelated FileNotFoundError.

This reports it as one named failure instead. It is the cheap assertion the audit asked for.

THE TWO DIRECTIONS, because they catch different halves and only one of them works in a worktree.

Direction A, project to source. Read every GMIncludedFile in the .yyp, which is what the committed
project says it needs, resolve each to the source tools/sync_art.py copies it from, and require that
source to be tracked. This works in a bare HEAD worktree, where the missing files are simply not on
disk, so nothing can be learned by walking the tree. This is the direction that catches dc104a7.

Direction B, source to project. Walk the sources sync_art will mirror and require each to be
tracked. This catches the live-tree case, where a lane drops a new theme .ogg into a folder and the
mirror will pick it up on the next run while the file is uncommitted. It cannot fire in a worktree,
because an uncommitted file is not there.

Direction C, the staged pairing, judged against the INDEX, behind --staged. A commit is the index,
so the only honest way to judge what a commit will carry is to read the index rather than the
working tree: `git ls-files` already reads the index, and the index copy of the project file is
`git -C <repo> show :<repo-relative yyp path>`. Measured 2026-10-24 in a scratch repository:
`git add staged_only.ogg` with nothing committed puts staged_only.ogg in `git ls-files`, while
Direction A opens the WORKING TREE .yyp, which by commit time is already regenerated. So the shape
"three oggs staged, yyp unstaged" exited 0 while the commit would have declared three streams it did
not carry; it only reddened while the oggs were still UNTRACKED, which is why six recurrences each
looked green until the moment of the commit. Direction C is the only direction that can judge a
staged commit, because a commit is the index.

Direction C's word is UNPAIRED IN COMMIT, never MISSING FROM COMMIT or UNCOMMITTED SOURCE, because
run_suites.py and the gate log grep for those two exact strings to count what the older directions
found. Directions A and B are deliberately NOT re-run under --staged: they read the working tree and
the whole tracked set, and on this tree one shared index carries several lanes' work, so a lane's
commit must not be refused for a file another lane has not committed yet. The nightly and
tests/test_build_inputs.py keep their meaning, which is why the flag is what turns Direction C on.

Scope, stated so nobody over-reads it. This checks delivery inputs mirrored into game/datafiles. It
does not check generated project resources, which tools/gen_project.py owns, and it does not check
the mirror itself, because game/datafiles is generated and deliberately gitignored.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YPP = os.path.join(ROOT, "game", "PrimordialParadox.yyp")
AUDIO = os.path.join(ROOT, "assets", "audio")
ART_SOURCES = (
    os.path.join(ROOT, "game", "sprites_src", "title"),
    os.path.join(ROOT, "game", "sprites_src", "env"),
    os.path.join(ROOT, "game", "sprites_src", "chars"),
    # Card R28: the exterior tile set (card R46) is written one folder down, in env/quay/, and tools/sync_art.py reads
    # that folder too. A source this list does not name would read as a mirror with nothing committed behind it.
    os.path.join(ROOT, "game", "sprites_src", "env", "quay"),
    # Card t_af836a62: the drive tile set is read from assets/tiles/drive, outside the sprites_src tree, so its folder
    # is named here too. Without this line the mirrored drive_tiles.png resolves to no committed source.
    os.path.join(ROOT, "assets", "tiles", "drive"),
    # Card t_4275136f: the battle screen's strips and enemy sheets are mirrored now (tools/sync_art.py BG_SRC and
    # ENEMY_SRC). A folder this list does not name would make eleven new Included Files resolve to no committed
    # source, so both are named here, and tests/test_battle_draw.py fails when the two lists drift apart.
    os.path.join(ROOT, "game", "sprites_src", "bg"),
    os.path.join(ROOT, "game", "sprites_src", "enemies"),
)
SFX_FOLDER = "sfx"
# Direction C's vocabulary. Kept apart from the two older words on purpose; see the docstring.
UNPAIRED = "UNPAIRED IN COMMIT"
AUDIO_PREFIX = "assets/audio/"
STREAMS_PREFIX = "datafiles/streams/"
# The tail the .yyp always sits at inside a project tree, used to work out the project's own
# repository-relative directory when the caller names a different repository (the scratch-repo rows).
YPP_TAIL = "game/PrimordialParadox.yyp"


def load_sync_art():
    """Load tools/sync_art.py so this checker reads the real mirror rules, not a copy of them."""
    path = os.path.join(ROOT, "tools", "sync_art.py")
    spec = importlib.util.spec_from_file_location("pp_sync_art", path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load tools/sync_art.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def included_files(yyp_text):
    """Every Included File the project declares, as paths relative to game/.

    The .yyp is JSON, but GameMaker writes trailing commas in places, so a strict parse is tried
    first and a lenient scan of the same two fields is the fallback.
    """
    try:
        data = json.loads(yyp_text)
        return sorted(
            {
                "%s/%s" % (item.get("filePath", "").strip("/"), item.get("name", "")).lstrip("/")
                for item in data.get("IncludedFiles", [])
                if item.get("name")
            }
        )
    except (ValueError, AttributeError):
        pairs = re.findall(
            r'"filePath":\s*"([^"]*)"[^}]*?"name":\s*"([^"]*)"', yyp_text, re.DOTALL
        )
        return sorted({"%s/%s" % (folder.strip("/"), name) for folder, name in pairs})


# Files the build GENERATES rather than copies from a source file. The art manifest is an index
# tools/sync_art.py writes over the sprites that are themselves checked individually below, so it
# has no source file of its own to require.
GENERATED = {"datafiles/art/title_manifest.json", "datafiles/sfx/sfx.json"}


def source_candidates(rel_path):
    """Where this Included File is produced from, as absolute candidate paths.

    Two mirrors feed game/datafiles, and a path can legitimately come from either: tools/sync_data.py
    copies the whole data/ tree, tools/sync_art.py copies sprites, sound effects and theme streams.
    """
    folder, name = os.path.split(rel_path)
    candidates = []
    if rel_path.startswith("datafiles/"):
        # sync_data mirrors data/** into game/datafiles/**, so the source keeps the same tail.
        candidates.append(os.path.join(ROOT, "data", rel_path[len("datafiles/"):]))
    if folder.endswith("streams") or folder == "datafiles":
        if os.path.isdir(AUDIO):
            for theme in sorted(os.listdir(AUDIO)):
                theme_dir = os.path.join(AUDIO, theme)
                # mirror_streams walks every folder under assets/audio, sfx included, so an sfx
                # .ogg also lands in datafiles/streams and has a source here.
                if os.path.isdir(theme_dir):
                    candidates.append(os.path.join(theme_dir, name))
    if folder.endswith("sfx"):
        candidates.append(os.path.join(AUDIO, SFX_FOLDER, name))
    if folder.endswith("art"):
        for art_dir in ART_SOURCES:
            candidates.append(os.path.join(art_dir, name))
    candidates.append(os.path.join(ROOT, "game", rel_path))
    return candidates


def unresolved(included, tracked, repo):
    """Included Files whose target and whose every source candidate are absent from the commit.

    Pure apart from os.path, so it tests without a repository: `tracked` is the set of
    repository-relative paths git carries, `repo` is the absolute repository root.
    """
    missing = []
    for rel_path in included:
        if rel_path in GENERATED:
            continue
        target = os.path.relpath(os.path.join(ROOT, "game", rel_path), repo).replace(os.sep, "/")
        if target in tracked:
            continue
        if any(
            os.path.relpath(os.path.abspath(c), repo).replace(os.sep, "/") in tracked
            for c in source_candidates(rel_path)
        ):
            continue
        missing.append(rel_path)
    return sorted(set(missing))


def uncommitted_sources(sync, tracked, repo):
    """Sources sync_art will mirror that git does not carry. Direction B."""
    found = []
    for entry in sync.source_entries():
        try:
            found.append(sync.source_path(entry["file"]))
        except (KeyError, OSError):
            continue
    for cue in getattr(sync, "SFX_CUES", ()):
        path = os.path.join(AUDIO, SFX_FOLDER, cue + ".wav")
        if os.path.isfile(path):
            found.append(path)
    if os.path.isdir(AUDIO):
        for theme in sorted(os.listdir(AUDIO)):
            theme_dir = os.path.join(AUDIO, theme)
            if not os.path.isdir(theme_dir) or theme == SFX_FOLDER:
                continue
            for fname in sorted(os.listdir(theme_dir)):
                if fname.endswith(".ogg"):
                    found.append(os.path.join(theme_dir, fname))
    out = []
    for path in found:
        rel = os.path.relpath(os.path.abspath(path), repo).replace(os.sep, "/")
        if rel not in tracked:
            out.append(rel)
    return sorted(set(out))


def repo_root():
    result = subprocess.run(
        ["git", "-C", ROOT, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise SystemExit("not inside a git repository: " + result.stderr.strip())
    return result.stdout.strip().replace("\\", "/")


def tracked_files(repo):
    result = subprocess.run(
        ["git", "-C", repo, "ls-files", "-z"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise SystemExit("git ls-files failed")
    return {name for name in result.stdout.decode("utf-8", "replace").split("\0") if name}


def index_copy(repo, rel_path):
    """The INDEX copy of one repository-relative file, or None when the index does not carry it.

    Not the working tree copy: by commit time the .yyp has already been regenerated, so the file on
    disk is exactly the thing that cannot answer "what will this commit carry". `git show :<path>`
    is the blob the next commit would contain (measured 2026-10-24).
    """
    result = subprocess.run(
        ["git", "-C", repo, "show", ":" + rel_path],
        capture_output=True,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace")


def declared_streams(included):
    """The Included File paths that live in a streams folder, keyed by file name.

    Keyed by name because the pairing is by name: mirror_streams copies assets/audio/<asset>/<name>
    to game/datafiles/streams/<name>, so one name on both sides is one landed cue.
    """
    return {
        os.path.basename(path): path
        for path in included
        if os.path.dirname(path).split("/")[-1].endswith("streams")
    }


def unpaired(index_paths, yyp_text, yyp_rel, prefix=""):
    """Direction C: the index project and the index sources must name each other. Pure.

    `index_paths` are repository-relative paths in the INDEX (git ls-files already reads the index),
    `yyp_text` is the index copy of the project file or None when the index does not carry it, and
    `prefix` is the project's own directory inside the repository ("" when the project is the root,
    which is the scratch-repo shape).
    """
    included = included_files(yyp_text) if yyp_text else []
    streams = declared_streams(included)
    audio_prefix = prefix + AUDIO_PREFIX
    index_oggs = sorted(
        path for path in index_paths
        if path.startswith(audio_prefix) and path.lower().endswith(".ogg")
    )
    problems = []
    for rel in index_oggs:
        name = os.path.basename(rel)
        if name in streams:
            continue
        problems.append(
            "%s | the index project names no %s%s" % (rel, STREAMS_PREFIX, name))
    carried = {os.path.basename(rel) for rel in index_oggs}
    for name, declared in sorted(streams.items()):
        if name in carried:
            continue
        problems.append(
            "%s | %s in the index names it and no %s*/%s is in the index"
            % (declared, yyp_rel or "(no project file)", audio_prefix, name))
    return problems


def staged_problems(repo=None, yyp_rel=None, prefix=None):
    """Direction C over a repository's index, as problems. Reads the index, never the tree."""
    repo = repo or repo_root()
    if yyp_rel is None:
        yyp_rel = os.path.relpath(YPP, repo).replace(os.sep, "/")
    if prefix is None:
        prefix = yyp_rel[:-len(YPP_TAIL)] if yyp_rel.endswith(YPP_TAIL) else ""
    index_paths = tracked_files(repo)
    yyp_text = index_copy(repo, yyp_rel)
    return ["%s %s" % (UNPAIRED, detail)
            for detail in unpaired(index_paths, yyp_text, yyp_rel, prefix)]


def check(root=ROOT):
    """Every problem found, as strings, matching the convention of the other checkers here.

    The helpers read this module's own paths, so a different root is refused rather than silently
    measured against the wrong tree.
    """
    if os.path.abspath(root) != os.path.abspath(ROOT):
        raise SystemExit("check_build_inputs measures only its own project tree: " + str(root))
    repo = repo_root()
    tracked = tracked_files(repo)
    with open(YPP, "r", encoding="utf-8") as fh:
        included = included_files(fh.read())
    problems = ["MISSING FROM COMMIT " + name for name in unresolved(included, tracked, repo)]
    problems += [
        "UNCOMMITTED SOURCE " + name
        for name in uncommitted_sources(load_sync_art(), tracked, repo)
    ]
    return problems


def main(staged: bool = False) -> int:
    """Exit 0 when nothing is wrong. `staged=True` adds Direction C and reads the index.

    The flag is a parameter rather than a scan of sys.argv because the test module calls main()
    inside pytest, where sys.argv carries pytest's own options and a scan would misread them.
    """
    problems = staged_problems() if staged else check(ROOT)
    if problems:
        if staged:
            print("This commit would carry an Included File entry with no source, or a cue source")
            print("the commit's project does not name. Stage the .ogg and the regenerated")
            print("game/PrimordialParadox.yyp together, or stage neither.")
        else:
            print("The committed project declares Included Files that a fresh checkout cannot rebuild,")
            print("or mirrors sources git does not carry. Commit each one, or stop mirroring it.")
        for problem in problems:
            print("  " + problem)
        return 1

    if staged:
        print("staged pairing: every staged cue source is named by the staged project file")
    else:
        print("included files: every declared file resolves to a committed source")
    return 0


if __name__ == "__main__":
    sys.exit(main(staged="--staged" in sys.argv[1:]))
