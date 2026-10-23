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
)
SFX_FOLDER = "sfx"


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


def main() -> int:
    problems = check(ROOT)
    if problems:
        print("The committed project declares Included Files that a fresh checkout cannot rebuild,")
        print("or mirrors sources git does not carry. Commit each one, or stop mirroring it.")
        for problem in problems:
            print("  " + problem)
        return 1

    print("included files: every declared file resolves to a committed source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
