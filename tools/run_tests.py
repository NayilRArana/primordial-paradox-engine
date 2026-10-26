#!/usr/bin/env python3
r"""run_tests.py: run the primordial-paradox pytest selection on Pine by default, the desktop only for
what Pine cannot run (card t_a6fc50a2, NODE-1).

    python tools/run_tests.py                                  # the whole suite: Pine first, then the desktop rows
    python tools/run_tests.py tests/test_arrange.py            # one file
    python tools/run_tests.py tests/test_arrange.py::test_x    # one node
    python tools/run_tests.py tests -k vibrato                 # a selection (-k/-m run as one shard)
    python tools/run_tests.py --local                          # force the desktop
    python tools/run_tests.py --name nightly --shards 2        # name the report, pin the shard count

Why: the Windows PC has 31.8 GB and often 1 to 4 GB free with 11 to 14 workers, and the suite is about
1,500 tests in 3 to 4 minutes of pure Python. Pine Computers run it on Linux instead, in up to four
shards at once, for about $0.003 per Computer minute.

What stays on the desktop, and why (the rule sets are read from pine_offload.py, never copied):
  * tests/test_build_inputs.py and tests/test_test_inputs.py shell out to git, and the offloaded tree is
    a zip (GIT_TESTS);
  * tests/test_sync_art.py needs the 34 MB stream mirror no zip under the upload ceiling can carry
    (ASSET_TESTS);
  * three nodes whose render or stream sources cannot travel (RENDER_NODES, STREAM_NODES) are
    deselected on the far side, so they are run here instead;
  * every row the markers in pytest.ini call host only (windows_only, host_png_bytes,
    needs_git_checkout) is skipped on Pine, so it is collected here with -m and run here;
  * every row Pine reports red is rerun here, and the desktop verdict is the one that counts. A far side
    gap (a missing file, a Win32 module, a missing package) is labelled as one, but nothing is decided
    by keyword: the row is simply measured again where it can pass.

The merged verdict names the node that ran each part:

    PART pine    node=Pine Computers (Linux, 4 shard(s)) passed=1427 failed=3 skipped=50 deselected=3 wall=435s cost=$0.022
    PART desktop node=desktop (Windows) targets=59 passed=84 failed=0 skipped=0 wall=39s
    SUMMARY passed=1511 failed=0 | pine 94.6 percent of 1511 tests | report ...\data\results\offload-<name>-merged.json

Exit code: 0 all green, 1 a test failed, 2 Pine itself did not deliver (so a broken offload is never
mistaken for a green suite), 3 the selection could not be built. A shard whose upload is refused is
retried on Pine before its rows fall back here, the retry waiting and starting again from a new
connection. Pine's share of the measured rows is a verdict of its own: below the target (90.0
percent by default) the run prints a named COVERAGE FAIL line and exits 2, so a 47 percent run can
never read as a 94 percent one.
"""
import argparse, ast, json, math, os, re, shlex, subprocess, sys, threading, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PINE_DIR = Path(os.environ.get("ARANANET_PINE_DIR") or (REPO.parent / "arananet" / "pine"))
OFFLOAD = PINE_DIR / "pine_offload.py"
OFLOW_RESULTS = PINE_DIR / "data" / "results"

# The interpreter that can import the pinesandbox SDK; pine_offload.py says it is
# AppData/Local/Python/bin/python (3.14), and the Hermes or project venv python cannot import it.
PINE_PY_CANDIDATES = (
    os.environ.get("PINE_PYTHON", ""),
    str(Path.home() / "AppData" / "Local" / "Python" / "bin" / "python.exe"),
    sys.executable,
)

COUNT_LINE = re.compile(r"^=*\s*(no tests ran|(?:\d+ [a-z]+)(?:, \d+ [a-z]+)*)\s+in\s+[\d.]+s")
ONE_COUNT = re.compile(r"(\d+) ([a-z]+)")
FAILED_LINE = re.compile(r"^(FAILED|ERROR)\s+(\S+?)(?:\s+-\s+(.*))?$")
AGENT_SUMMARY = re.compile(r"^SUMMARY passed=(\d+) failed=(\d+)", re.M)

# The phrases that say a red row is the far side's doing rather than the code's. They only label the
# handover line ("pine env gap" against "pine red"): every Pine red is rerun on the desktop either way,
# so a phrase missing from this list costs a word in the report, never a wrong verdict.
ENV_GAP_PATTERNS = (
    "FileNotFoundError", "No such file or directory", "[Errno 2]",
    "ModuleNotFoundError", "ImportError", "cannot open shared object file",
    "ctypes", "windll", "WinError", "not recognized as an internal or external command",
    "command not found", "PermissionError", "ReadTimeout", "ConnectionError",
    "TimeoutExpired", "Exec format error", "UnidentifiedImageError",
)

# NODE-1's Check asks Pine to carry the suite, not to try: at least this share of the measured rows.
# A green desktop fallback is still a green suite, which is exactly why the share has to be a
# verdict and not a number inside a sentence (card t_8e880980, following t_a6fc50a2).
PINE_TARGET_PERCENT = 90.0

# A shard whose upload dies is retried, and each retry waits first: the failure measured on
# 2026-10-25 was a keep-alive connection the peer had already closed, so an immediate retry on the
# same second is the worst possible timing. Two rounds and a 15 s first wait cost a few cents.
RETRY_ROUNDS = 2
RETRY_BACKOFF_SECONDS = 15.0


def say(text=""):
    print(text, flush=True)


# ---------------------------------------------------------------- pine_offload rules, read not copied
def offload_rules() -> dict:
    """The node sets pine_offload.py decides with, read from its source so the two cannot drift.

    Importing that module would pull in pinesandbox, which the interpreter running this file may not
    have, so the four literals are parsed instead. A missing file is a hard error: guessing which tests
    need the desktop is how a green Pine run hides a red desktop one.
    """
    if not OFFLOAD.is_file():
        raise SystemExit("run_tests: cannot find %s (set ARANANET_PINE_DIR)" % OFFLOAD)
    tree = ast.parse(OFFLOAD.read_text(encoding="utf-8"))
    rules = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("GIT_TESTS", "ASSET_TESTS", "RENDER_NODES", "STREAM_NODES"):
                rules[name] = set(ast.literal_eval(node.value))
    missing = {"GIT_TESTS", "ASSET_TESTS", "RENDER_NODES", "STREAM_NODES"} - set(rules)
    if missing:
        raise SystemExit("run_tests: %s no longer defines %s" % (OFFLOAD, ", ".join(sorted(missing))))
    return rules


def pine_python() -> str:
    for cand in PINE_PY_CANDIDATES:
        if not cand or not Path(cand).is_file():
            continue
        try:
            probe = subprocess.run([cand, "-c", "import pinesandbox"], capture_output=True,
                                   stdin=subprocess.DEVNULL, timeout=120)
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return cand
    raise SystemExit("run_tests: no interpreter with the pinesandbox SDK; set PINE_PYTHON to one")


# --------------------------------------------------------------------------------------- pytest log
def parse_log(text: str) -> dict:
    """The counts and the failed node ids out of a pytest -q run, from pytest's own lines.

    The agent's trailing SUMMARY line is recorded separately and never trusted as the evidence: the
    counts line pytest prints is the tool's own output, and the FAILED lines name the tests.
    """
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "deselected": 0,
              "xfailed": 0, "xpassed": 0, "warning": 0}
    failed_ids, error_ids, reasons = [], [], {}
    counts_line = ""
    for raw in text.splitlines():
        line = raw.strip()
        m = FAILED_LINE.match(line)
        if m:
            kind, node, why = m.group(1), m.group(2), (m.group(3) or "")
            (failed_ids if kind == "FAILED" else error_ids).append(node)
            reasons[node] = why
            continue
        m = COUNT_LINE.match(line)
        if m:
            counts_line = line
            counts = {}
            for number, word in ONE_COUNT.findall(m.group(1)):
                counts[{"errors": "error", "warnings": "warning"}.get(word, word)] = int(number)
    no_tests = counts_line.startswith("no tests ran")
    agent = AGENT_SUMMARY.search(text)
    return {
        "counts": counts,
        "counts_line": counts_line,
        "no_tests": no_tests,
        "failed_ids": failed_ids,
        "error_ids": error_ids,
        "reasons": reasons,
        "agent_summary": ("passed=%s failed=%s" % agent.groups()) if agent else "",
    }


def is_env_gap(message: str) -> bool:
    return any(pat in (message or "") for pat in ENV_GAP_PATTERNS)


def stream_cmd(cmd, cwd, prefix, timeout_s=1800):
    """Run a command, echo its output as it arrives, and keep it for the report."""
    say("%s $ %s" % (prefix, " ".join(shlex.quote(str(c)) for c in cmd)))
    lines = []
    proc = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1,
                            errors="replace", stdin=subprocess.DEVNULL)
    killed = threading.Event()

    def _kill():
        killed.set()
        proc.kill()

    timer = threading.Timer(timeout_s, _kill)
    timer.daemon = True
    timer.start()
    try:
        for line in (proc.stdout or ()):
            line = line.rstrip("\n")
            lines.append(line)
            say("  %s| %s" % (prefix, line))
        code = proc.wait()
    finally:
        timer.cancel()
    if killed.is_set():
        say("%s: killed after %s seconds" % (prefix, timeout_s))
        code = -1
    return code, "\n".join(lines)


# ------------------------------------------------------------------------------------- the selection
def selection_files(paths):
    """The default selection: every tests/test_*.py, the same list pine_offload.py would build."""
    if paths:
        return list(paths)
    return sorted("tests/" + p.name for p in (REPO / "tests").glob("test_*.py"))


def split_selection(selection, rules):
    """Which paths go to Pine, and which nodes the desktop owes even when their file travels."""
    pine, desktop, reasons = [], [], {}
    for path in selection:
        if path in rules["GIT_TESTS"] or path in rules["ASSET_TESTS"]:
            desktop.append(path)
            reasons[path] = "pine_offload rule: needs the desktop (git checkout or the stream mirror)"
        elif path in rules["RENDER_NODES"] or path in rules["STREAM_NODES"]:
            desktop.append(path)
            reasons[path] = "pine_offload rule: this node is deselected on the far side"
        else:
            pine.append(path)
    for group in ("RENDER_NODES", "STREAM_NODES"):
        for node in sorted(rules[group]):
            stem = node.split("::")[0]
            if any(p == stem or p.split("::")[0] == stem for p in pine) and node not in desktop:
                desktop.append(node)
                reasons[node] = "pine_offload rule: deselected on Pine (%s)" % group.lower().replace("_nodes", "")
    return pine, desktop, reasons


def shard_count(nfiles: int, forced):
    if forced:
        return max(1, min(4, forced))
    return max(1, min(4, math.ceil(nfiles / 20)))


# ------------------------------------------------------------------------------------- the pine part
def run_pine(pine_paths, name, shards, extra_args, timeout_s):
    py = pine_python()
    files = ",".join(pine_paths + extra_args)
    cmd = [py, str(OFFLOAD), "--shards", str(shards), "--name", name, "--files", files]
    started = time.time()
    code, log = stream_cmd(cmd, PINE_DIR, "pine", timeout_s)
    wall = round(time.time() - started, 1)
    shards_rec = []
    stale = []
    pattern = re.compile(r"^offload-%s-(\d+)\.json$" % re.escape(name))
    for path in sorted(OFLOW_RESULTS.glob("offload-%s-*.json" % name), key=lambda p: p.name):
        if not pattern.match(path.name):
            continue
        # A reused --name leaves the last run's shard files behind. Reading one of those would report
        # an old verdict as this run's, so anything written before the command started is named and left.
        try:
            if path.stat().st_mtime < started - 5:
                stale.append(path.name)
                continue
        except OSError:
            continue
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            rec = {"status": "unreadable", "summary": "%s: %s" % (type(exc).__name__, exc)}
        parsed = parse_log(rec.get("results_txt") or "")
        shards_rec.append({
            "path": str(path),
            "name": rec.get("name", path.stem),
            "status": rec.get("status", ""),
            "files": rec.get("files") or [],
            "deselected_on_pine": rec.get("deselected_on_pine") or [],
            "summary": rec.get("summary", ""),
            "wall_seconds": rec.get("wall_seconds"),
            "est_computer_usd": rec.get("est_computer_usd"),
            "counts": parsed["counts"],
            "counts_line": parsed["counts_line"],
            "failed_ids": parsed["failed_ids"],
            "error_ids": parsed["error_ids"],
            "reasons": parsed["reasons"],
            "agent_summary": parsed["agent_summary"],
            "no_tests": parsed["no_tests"],
        })
    if stale:
        say("pine: left %d shard file(s) from an earlier run under this name: %s"
            % (len(stale), ", ".join(stale)))
    return {"interpreter": py, "command": cmd, "exit_code": code, "wall_seconds": wall,
            "log": log, "shards": shards_rec, "stale_shard_files": stale}


def _undelivered(pine):
    """The shard records that never produced a verdict: an error, or a run with no tests in it."""
    return [s for s in (pine or {}).get("shards", []) if s["status"] != "completed" or s["no_tests"]]


def retry_failed_shards(pine, name, extra_args, timeout_s,
                        rounds=RETRY_ROUNDS, backoff=RETRY_BACKOFF_SECONDS):
    """More Pine attempts for the shards that never delivered, each waiting and each on a new process.

    The upload is the flaky part, not the tests: measured 2026-10-24 a 13.98 MB zip was closed with
    `ConnectionError: [Errno 10054]` on one of four parallel shards while the other three ran
    (`data/results/offload-node1-final-0.json`), and measured again 2026-10-25 on two of four
    (`offload-verifysweep-2026-10-25-0.json`, `-2.json`). `pine_client.put_file` now retries the
    upload itself on a fresh connection, and these rounds are the backstop above it: a fresh process
    per round (so a fresh client), a wait first, and the still-failing files only.

    One thing this must not do is count a file twice. A round's records replace the earlier records
    for the files it was given, so the merge sees one record per file set: the last attempt. Anything
    else would leave a delivered shard and a failed one holding the same files, and the merge would
    add the retry's passed rows on top of a desktop rerun of the same rows.

    If every round fails, those rows fall back to the desktop and the run exits 2 with a named
    coverage line, so it is never quiet.
    """
    failed = _undelivered(pine)
    if not failed:
        return pine
    settled = [s for s in pine["shards"] if s not in failed]
    commands = [pine["command"]]
    log = pine["log"]
    wall = pine["wall_seconds"] or 0
    retried = [s["name"] for s in failed]
    latest = list(failed)
    rounds_used = 0
    for round_no in range(1, max(1, int(rounds)) + 1):
        files = []
        for shard in latest:
            for path in shard["files"]:
                if path not in files:
                    files.append(path)
        if not files:
            break
        wait = max(0.0, float(backoff)) * (2 ** (round_no - 1))
        say("pine: %d shard(s) did not deliver; retrying their %d file(s) as one shard "
            "(round %d of %d, waiting %ds first)"
            % (len(latest), len(files), round_no, rounds, wait))
        if wait:
            time.sleep(wait)
        suffix = "-retry" if round_no == 1 else "-retry%d" % round_no
        attempt = run_pine(files, name + suffix, 1, extra_args, timeout_s)
        rounds_used = round_no
        commands.append(attempt["command"])
        log = log + "\n--- retry round %d ---\n" % round_no + attempt["log"]
        wall = round(wall + (attempt["wall_seconds"] or 0), 1)
        retried.extend(s["name"] for s in attempt["shards"])
        latest = _undelivered(attempt)
        if not latest:
            settled = settled + list(attempt["shards"])
            break
        # Nothing delivered again: keep this round's records as the latest word on those files.
        settled = settled + [s for s in attempt["shards"] if s not in latest]
    else:
        settled = settled + latest
    return {
        "interpreter": pine["interpreter"],
        "command": pine["command"],
        "commands": commands,
        "exit_code": pine["exit_code"],
        "wall_seconds": wall,
        "log": log,
        "shards": settled,
        "stale_shard_files": list(pine.get("stale_shard_files", [])),
        "retried_shards": retried,
        "retry_rounds": rounds_used,
    }


# ---------------------------------------------------------------------------------- the desktop part
HOST_MARKERS = "windows_only or host_png_bytes or needs_git_checkout"


def collect_host_marked(paths, passthrough=()):
    """The rows pytest.ini marks as host only, collected on this host.

    Pine skips them with the marker's reason instead of failing, so their names never reach the far
    side's tail; collecting them here is what puts them back in the run, on the host that can hold them.
    """
    cmd = ([sys.executable, "-m", "pytest"] + list(paths) + ["--collect-only", "-q",
            "-p", "no:cacheprovider", "-m", HOST_MARKERS] + list(passthrough))
    code, log = stream_cmd(cmd, REPO, "collect")
    if code == 5:
        # pytest exits 5 when the expression selects nothing, which is the normal answer for a
        # selection with no host-marked rows in it: not an error, and nothing to hand over.
        return []
    if code != 0:
        say("collect: the marker collection did not run cleanly (exit %s); the marker rows are left out "
            "and are counted as skipped" % code)
        return []
    nodes = []
    for line in log.splitlines():
        line = line.strip()
        if re.match(r"^\S+\.py(::\S+)?$", line):
            nodes.append(line)
    return nodes


def run_desktop(targets, extra_args=(), passthrough=()):
    if not targets:
        return None
    cmd = [sys.executable, "-m", "pytest"] + targets + list(extra_args) + list(passthrough) + [
        "-q", "-p", "no:cacheprovider", "--tb=line", "-rf"]
    started = time.time()
    code, log = stream_cmd(cmd, REPO, "desktop")
    parsed = parse_log(log)
    return {"command": cmd, "exit_code": code, "wall_seconds": round(time.time() - started, 1),
            "log": log, "targets": list(targets), **parsed}


def merge(pine, desktop):
    """One verdict: the desktop's word for every node it reran, Pine's for the rest."""
    pine_counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "deselected": 0}
    pine_failed, pine_errors = {}, {}
    for shard in (pine or {}).get("shards", []):
        for key in pine_counts:
            pine_counts[key] += shard["counts"].get(key, 0)
        pine_failed.update({n: shard["reasons"].get(n, "") for n in shard["failed_ids"]})
        pine_errors.update({n: shard["reasons"].get(n, "") for n in shard["error_ids"]})
    desk_counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    desk_failed, desk_errors = {}, {}
    if desktop:
        desk_counts = {k: desktop["counts"].get(k, 0) for k in desk_counts}
        desk_failed = {n: desktop["reasons"].get(n, "") for n in desktop["failed_ids"]}
        desk_errors = {n: desktop["reasons"].get(n, "") for n in desktop["error_ids"]}
    # pine_offload keeps only the tail of the far side's output, so a shard with many failures can lose
    # the names of the first ones. The counts line is last and always survives, so a shortfall between the
    # count and the ids found is carried as an unidentified failure instead of quietly shrinking the red.
    identified = len(set(pine_failed) | set(pine_errors))
    unidentified = max(0, pine_counts["failed"] + pine_counts["error"] - identified)
    rerun = set((desktop or {}).get("targets") or [])
    # A node the desktop reran speaks for itself; every other Pine failure stands.
    standing_failed = {n: why for n, why in pine_failed.items()
                       if n not in rerun and n.split("::")[0] not in rerun}
    standing_errors = {n: why for n, why in pine_errors.items()
                       if n not in rerun and n.split("::")[0] not in rerun}
    failed = dict(standing_failed)
    failed.update(desk_failed)
    errors = dict(standing_errors)
    errors.update(desk_errors)
    passed = pine_counts["passed"] + desk_counts["passed"]
    pine_tests = pine_counts["passed"] + pine_counts["failed"] + pine_counts["error"] + pine_counts["skipped"]
    desk_tests = desk_counts["passed"] + desk_counts["failed"] + desk_counts["error"] + desk_counts["skipped"]
    # Each row counts once: a row Pine skipped or reported red and the desktop then ran belongs to the
    # desktop, so the merged total lands on the same number a plain local run reports.
    pine_run = pine_counts["passed"] + pine_counts["failed"] + pine_counts["error"]
    desk_run = desk_counts["passed"] + desk_counts["failed"] + desk_counts["error"]
    handed_over = len([n for n in set(pine_failed) | set(pine_errors)
                       if n in rerun or n.split("::")[0] in rerun])
    total = max(0, pine_run + desk_run - handed_over)
    return {
        "passed": passed,
        "failed": len(failed) + unidentified,
        "errors": len(errors),
        "failed_ids": failed,
        "error_ids": errors,
        "unidentified_pine_failures": unidentified,
        "pine": pine_counts,
        "desktop": desk_counts,
        "pine_tests": pine_tests,
        "desktop_tests": desk_tests,
        "total_tests": total,
        "pine_share": round(100.0 * pine_run / max(1, pine_run + desk_run - handed_over), 1),
        "skipped": pine_counts["skipped"] + desk_counts["skipped"],
        "deselected": pine_counts["deselected"],
        "desktop_targets": list((desktop or {}).get("targets") or []),
    }


def coverage_gap(merged, target, pine) -> str:
    """The named failure when Pine carried less than `target` percent of the rows, else "".

    NODE-1's Check is about Pine carrying the suite, not about the suite being green: the desktop
    fallback makes every lost shard invisible in the pass count. So the share gets its own verdict,
    with the reason attached (which shards never delivered, and how many files that cost).
    """
    if not pine:
        return ""  # a --local run makes no Pine claim, so there is nothing to hold to the target
    if merged["pine_share"] + 1e-9 >= float(target):
        return ""
    undelivered = _undelivered(pine)
    if undelivered:
        because = "shard(s) %s never delivered" % ", ".join(s["name"] for s in undelivered)
    elif merged["pine_tests"] == 0:
        because = "no shard produced a count line"
    else:
        because = "the Pine rows that ran are too few against the desktop's"
    return ("COVERAGE FAIL pine carried %.1f percent of %d tests, target %.1f percent: %s, "
            "so %d desktop target(s) were rerun here"
            % (merged["pine_share"], merged["total_tests"], float(target), because,
               len(merged["desktop_targets"])))


def pine_undelivered(pine, merged) -> bool:
    """True when the rows Pine was given did not all come back from Pine.

    This is about the shard records, not the first attempt's exit code: a shard whose upload died
    and whose retry delivered is a delivered shard, and calling that a broken Pine run would make
    the retry worthless (it would report exit 2 on a suite Pine carried in full). A shard with no
    counts in it counts as undelivered even when its status says completed.
    """
    if not pine:
        return False
    return (not pine["shards"]
            or any(s["status"] != "completed" or s["no_tests"] for s in pine["shards"])
            or merged["pine_tests"] == 0)


def report_path(name):
    OFLOW_RESULTS.mkdir(parents=True, exist_ok=True)
    return OFLOW_RESULTS / ("offload-%s-merged.json" % name)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the primordial-paradox pytest selection on Pine by default.")
    ap.add_argument("paths", nargs="*", help="test files, node ids or directories; default: every tests/test_*.py")
    ap.add_argument("--local", action="store_true", help="force the desktop, no Pine call")
    ap.add_argument("--name", default="", help="report name; default suite-<HHMMSS>")
    ap.add_argument("--shards", type=int, default=0, help="Pine shards (1 to 4); default scaled to the file count")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds to allow the Pine command itself")
    ap.add_argument("--pine-target", type=float, default=PINE_TARGET_PERCENT,
                    help="the share of measured rows Pine must carry (default %.1f percent); below it the "
                         "run prints COVERAGE FAIL and exits 2" % PINE_TARGET_PERCENT)
    ap.add_argument("--retry-rounds", type=int, default=RETRY_ROUNDS,
                    help="Pine attempts for a shard whose upload or run died (default %d)" % RETRY_ROUNDS)
    ap.add_argument("-k", dest="keyword", default="", help="pytest -k expression")
    ap.add_argument("-m", dest="markexpr", default="", help="pytest -m expression")
    args, passthrough = ap.parse_known_args()

    if not (REPO / "tests").is_dir():
        say("run_tests: no tests directory under %s" % REPO)
        return 3
    selection = selection_files(args.paths)
    if not selection:
        say("run_tests: nothing selected")
        return 3
    name = args.name or ("suite-" + time.strftime("%H%M%S"))
    if "," in args.keyword or "," in args.markexpr:
        # pine_offload splits --files on commas, so an expression holding one would be cut in two.
        say("run_tests: a -k or -m expression cannot contain a comma (pine_offload splits --files on it)")
        return 3
    extra_args = []
    if args.keyword:
        extra_args += ["-k", shlex.quote(args.keyword)]
    if args.markexpr:
        extra_args += ["-m", shlex.quote(args.markexpr)]
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    say("run_tests: %d path(s) selected, name %s, %s" % (len(selection), name, started))

    if args.local:
        desk = run_desktop(selection, extra_args, passthrough) or {}
        merged = merge(None, desk)
        say("PART desktop node=desktop (Windows) targets=%d passed=%d failed=%d skipped=%d wall=%.0fs"
            % (len(selection), merged["desktop"]["passed"], merged["desktop"]["failed"],
               merged["desktop"]["skipped"], desk.get("wall_seconds", 0)))
        _print_failed(merged)
        say("SUMMARY passed=%d failed=%d | desktop 100.0 percent of %d tests | report %s"
            % (merged["passed"], merged["failed"], merged["total_tests"], report_path(name)))
        _write_report(name, started, {"mode": "local", "merged": merged, "desktop": desk}, merged)
        return 0 if merged["failed"] == 0 and merged["errors"] == 0 else 1

    rules = offload_rules()
    pine_paths, desktop_paths, why_desktop = split_selection(selection, rules)
    pine = None
    if pine_paths:
        # -k and -m have to travel inside the file list pine_offload.py hands to pytest, so a filtered
        # run goes as one shard: slicing a file list that ends with argument tokens would cut them apart.
        shards = 1 if extra_args else shard_count(len(pine_paths), args.shards)
        pine = retry_failed_shards(run_pine(pine_paths, name, shards, extra_args, args.timeout),
                                   name, extra_args, args.timeout, rounds=args.retry_rounds)
    else:
        say("run_tests: nothing to offload (every selected path needs the desktop)")

    # What the desktop owes: its own rules' rows, every row Pine reported red (its verdict is decided
    # here, so no keyword list can hide a real failure or take a far side gap for one), every row Pine
    # skipped for a host marker, and every file of a shard that never delivered.
    targets = list(desktop_paths)
    rerun_reasons = dict(why_desktop)
    if pine:
        for shard in pine["shards"]:
            if shard["status"] != "completed" or shard["no_tests"]:
                for path in shard["files"]:
                    if path not in targets:
                        targets.append(path)
                        rerun_reasons[path] = "pine shard %s %s: %s" % (
                            shard["name"], shard["status"] or "no counts",
                            (shard["summary"] or "").splitlines()[0][:200])
            for node in shard["failed_ids"] + shard["error_ids"]:
                message = shard["reasons"].get(node, "")
                if node not in targets and node.split("::")[0] not in targets:
                    targets.append(node)
                    label = "pine env gap" if is_env_gap(message) else "pine red, desktop verdict decides"
                    rerun_reasons[node] = "%s: %s" % (label, message[:200])
        for node in collect_host_marked(pine_paths, passthrough):
            if node not in targets and node.split("::")[0] not in targets:
                targets.append(node)
                rerun_reasons[node] = "pine skips it: a host marker in pytest.ini (windows_only, host_png_bytes or needs_git_checkout)"
    desktop = run_desktop(targets, extra_args, passthrough) if targets else None
    merged = merge(pine, desktop)

    if pine:
        wall = sum(s.get("wall_seconds") or 0 for s in pine["shards"])
        usd = sum(s.get("est_computer_usd") or 0 for s in pine["shards"])
        say("PART pine node=Pine Computers (Linux, %d shard(s)) passed=%d failed=%d skipped=%d "
            "deselected=%d wall=%.0fs cost=$%.3f"
            % (len(pine["shards"]), merged["pine"]["passed"], merged["pine"]["failed"],
               merged["pine"]["skipped"], merged["pine"]["deselected"], wall, usd))
        for shard in pine["shards"]:
            if shard["counts_line"]:
                say("  shard %-22s %s" % (shard["name"], shard["counts_line"]))
    if desktop:
        say("PART desktop node=desktop (Windows) targets=%d passed=%d failed=%d skipped=%d wall=%.0fs"
            % (len(desktop["targets"]), merged["desktop"]["passed"], merged["desktop"]["failed"],
               merged["desktop"]["skipped"], desktop["wall_seconds"]))
    for target, reason in rerun_reasons.items():
        say("  desktop owes %s (%s)" % (target, reason))
    if merged["unidentified_pine_failures"]:
        say("  PINEFAIL %d failure(s) whose node id was cut from the far side's tail; see the shard report"
            % merged["unidentified_pine_failures"])
    _print_failed(merged)

    gap = coverage_gap(merged, args.pine_target, pine)
    if gap:
        say("  " + gap)
    ratio = (("pine %.1f percent of %d tests%s" % (
                 merged["pine_share"], merged["total_tests"],
                 (", target %.1f percent NOT met" % args.pine_target) if gap else
                 " (target %.1f percent)" % args.pine_target))
             if pine else "desktop only, %d tests" % merged["total_tests"])
    say("SUMMARY passed=%d failed=%d | %s | report %s"
        % (merged["passed"], merged["failed"], ratio, report_path(name)))

    pine_code = pine["exit_code"] if pine else "n/a"
    broke = pine_undelivered(pine, merged)
    if pine and not broke and pine.get("retry_rounds"):
        say("run_tests: Pine delivered after %d retry round(s); every shard reported, so this is a "
            "Pine run (first attempt exit %s)" % (pine["retry_rounds"], pine_code))
    _write_report(name, started, {"mode": "pine+desktop", "selection": selection, "pine": pine,
                                  "desktop": desktop, "rerun_reasons": rerun_reasons, "merged": merged,
                                  "pine_target_percent": args.pine_target,
                                  "coverage_failure": gap}, merged)
    if broke:
        say("run_tests: Pine did not deliver the run (exit %s); those rows were rerun on the desktop and "
            "are counted there" % pine_code)
    if gap:
        say("run_tests: the Pine target was not met, so this run does not count as a Pine run (exit 2)")
    if broke or gap:
        return 2
    return 0 if merged["failed"] == 0 and merged["errors"] == 0 else 1


def _print_failed(merged):
    for node, why in sorted(merged["failed_ids"].items()):
        say("  FAILED %s%s" % (node, ("  " + why[:160]) if why else ""))
    for node, why in sorted(merged["error_ids"].items()):
        say("  ERROR %s%s" % (node, ("  " + why[:160]) if why else ""))


def _write_report(name, started, payload, merged):
    path = report_path(name)
    record = {
        "name": name,
        "card": "t_a6fc50a2",
        "started": started,
        "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
        "nodes": {"pine": "Pine Computers", "desktop": "desktop (Windows)"} if payload.get("pine") else
                 {"desktop": "desktop (Windows)"},
        "summary": "passed=%d failed=%d errors=%d pine_tests=%d desktop_tests=%d pine_share=%.1f"
                   % (merged["passed"], merged["failed"], merged["errors"], merged["pine_tests"],
                      merged["desktop_tests"], merged["pine_share"]),
        **payload,
    }
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    sys.exit(main())
