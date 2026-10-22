"""The first fifteen minutes, recomputed by a test, for card t_098da427 (TEST-BEAT-SHEET).

Sources this file measures, not restates:

    ROADMAP-2026-10-22.md                              six steps S1 to S6
    knowledge/mechanics/PACING-AND-CUTSCENES.md        section 9, the beat table and the gates line
    data/mechanics/pacing_recipes.json                 beat_sheet, PAC-32, the checks block
    tools/check_pacing.py                              imported, never copied

What is proven here, in the card's own order:

  1. the 32 beat durations sum to exactly 900 s, and every running total recomputes from the durations
     already counted;
  2. the per kind totals recompute, the cutscene share is at most 60 percent, and walk plus battle is at
     least 20 percent;
  3. the five gates hold at 150 s, 342 s, 442 s, 592 s and 370 s, each inside the ceiling PAC-32 states,
     and the study's section 9 gate line says the same five numbers;
  4. each of the six steps in the roadmap names a spec number, a lane and a check, and the spec numbers
     resolve to files that exist in specs/;
  5. the checker itself can fail: one beat lengthened by one second, in a throwaway copy, is caught.

Two things this file deliberately does not pin, both reported on the card rather than decided here:

  - The start clock in the S5 heading (9:12) and the second start clock in the S6 heading (9:52) are the
    running total at the END of a named beat, not the start of one: beat 25 runs 8:40 to 9:12 and beat 28
    runs 10:42 to 12:12 in the sheet. The end clock of every step is asserted here because all six get it
    right; the two start clocks are gamedev's to fix, so no test encodes them either way.
  - The checks block of data/mechanics/pacing_recipes.json carries first_interior_seconds 442, while the
    sheet's dock office starts at 370 s. The study says 370 s and PAC-32's ceiling is met either way, and
    tools/check_pacing.py does not read that key, so it is left alone and reported.

No test in this file reads the network; the last test proves it by scanning its own source and the
checker's source for a network import.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys

import pytest

import check_pacing

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROADMAP = os.path.join(ROOT, "ROADMAP-2026-10-22.md")
STUDY = os.path.join(ROOT, "knowledge", "mechanics", "PACING-AND-CUTSCENES.md")
DATA = os.path.join(ROOT, "data", "mechanics", "pacing_recipes.json")
SPECS = os.path.join(ROOT, "specs")

TOTAL_SECONDS = 900
BEAT_COUNT = 32
CUTSCENE_SHARE_MAX = 0.6
PLAY_SHARE_MIN = 0.2

# label, the beat whose START is the gate, the second it falls on, the PAC-32 ceiling key, and the
# wording the study uses in section 9. The ceilings are read from the data file, never restated here.
GATES = (
    ("first_input", "services_interlude", 150, "first_input_seconds_max",
     r"first input at (\d+) s"),
    ("full_control", "yard_walk", 342, "full_control_seconds_max",
     r"full control at (\d+) s"),
    ("first_fight", "first_encounter_hound", 442, "first_fight_start_seconds_max",
     r"first fight beginning at (\d+) s"),
    ("first_save", "cabin_save", 592, "first_save_start_seconds_max",
     r"first save beginning at (\d+) s"),
    ("first_interior", "dock_office", 370, "first_interior_seconds_max",
     r"first interior \(the dock office, from (\d+) s"),
)

NETWORK_TOKENS = ("urllib", "requests", "socket", "http.client", "httplib", "aiohttp", "ftplib")


# --------------------------------------------------------------------------- loading

def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def _load() -> dict:
    with open(DATA, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def data() -> dict:
    return _load()


@pytest.fixture(scope="module")
def sheet(data: dict) -> dict:
    return data["beat_sheet"]


@pytest.fixture(scope="module")
def beats(sheet: dict) -> list:
    return sheet["beats"]


@pytest.fixture(scope="module")
def study_text() -> str:
    return _read(STUDY)


@pytest.fixture(scope="module")
def study_section_9(study_text: str) -> str:
    """Section 9 only, so an edit in section 10 or 13 cannot make a gate assertion pass or fail."""
    assert "## 9." in study_text and "## 10." in study_text, "the study lost its section 9 or 10 heading"
    return study_text.split("## 9.", 1)[1].split("## 10.", 1)[0]


@pytest.fixture(scope="module")
def study_flat(study_section_9: str) -> str:
    """Section 9 with its line wrapping undone, so a sentence that wraps still reads as one sentence."""
    return re.sub(r"\s+", " ", study_section_9)


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    return _read(ROADMAP)


# --------------------------------------------------------------------------- small helpers

def clock_to_seconds(clock: str) -> int:
    """"9:52" is 592 s, "15:00" is 900 s, "0:42" is 42 s."""
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)


def starts_by_id(beats: list) -> dict:
    """When each beat begins, taken from the sheet's own duration and running total."""
    return {beat["id"]: beat["running_total"] - beat["seconds"] for beat in beats}


def step_blocks(text: str) -> list:
    """The six step sections as (code, title, body), cut at the next heading of any level."""
    parts = re.split(r"^### (S\d)\. ", text, flags=re.M)
    blocks = []
    for index in range(1, len(parts), 2):
        code = parts[index]
        rest = re.split(r"^## ", parts[index + 1], maxsplit=1, flags=re.M)[0]
        title, _, body = rest.partition("\n")
        blocks.append((code, title.strip(), body))
    return blocks


def field(body: str, name: str):
    """One bullet of a step, with its wrapped continuation lines joined by a space."""
    match = re.search(r"^- " + name + r":\s*(.*(?:\n  (?!- ).*)*)", body, re.M)
    if match is None:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def named_beats(title: str) -> list:
    """The beat numbers a step heading claims: "beats 1 to 2", "beats 23 and 28"."""
    match = re.search(r"\(beats ([^,)]+)", title)
    assert match is not None, "a step heading names no beats: %r" % title
    spec = match.group(1)
    numbers = [int(value) for value in re.findall(r"\d+", spec)]
    if " to " in spec and len(numbers) == 2:
        return list(range(numbers[0], numbers[1] + 1))
    return numbers


def heading_clocks(title: str) -> list:
    """"(beats 25 to 27, 9:12 to 10:42)" gives [552, 642], in the order written."""
    found = re.findall(r"\b(\d{1,2}:\d{2})\b", title)
    assert found, "a step heading carries no clock: %r" % title
    return [clock_to_seconds(clock) for clock in found]


def lane_table(text: str) -> list:
    """The lane each of the twenty cards in section 3 names."""
    return [line.split("|")[3].strip() for line in text.splitlines()
            if re.match(r"^\|\s*R\d\d\s*\|", line)]


def lane_counts(text: str) -> dict:
    """The "Lane counts:" sentence, which wraps across two lines in the roadmap."""
    match = re.search(r"Lane counts:(.*?)\.\s", text, re.S)
    assert match is not None, "the roadmap lost its Lane counts sentence"
    return {name: int(count) for name, count in re.findall(r"([a-z][a-z-]+)\s+(\d+)", match.group(1))}


def spec_numbers(spec_text: str) -> list:
    """Spec ids as written, which are always a token on its own: "14 (the drive), 06 (cutscene runner)"."""
    return [match.group(1) for match in re.finditer(r"(?:^|,\s+)(\d{2})(?=[\s(])", spec_text)]


# --------------------------------------------------------------------------- 1. the sum and the clock

def test_the_sheet_holds_thirty_two_numbered_beats(beats: list, sheet: dict):
    """32 beats, numbered 1 to 32 in order, with no repeated id. ROADMAP-2026-10-22.md section 2 builds on this count."""
    assert len(beats) == BEAT_COUNT
    assert [beat["n"] for beat in beats] == list(range(1, BEAT_COUNT + 1))
    assert len({beat["id"] for beat in beats}) == BEAT_COUNT
    assert sheet["total_seconds"] == TOTAL_SECONDS


def test_the_beat_durations_sum_to_exactly_nine_hundred_seconds(beats: list, sheet: dict):
    """900 s is the sheet's whole claim, so it is asserted as an equality, not a tolerance."""
    assert sum(beat["seconds"] for beat in beats) == TOTAL_SECONDS
    assert sheet["total_seconds"] == TOTAL_SECONDS
    assert all(isinstance(beat["seconds"], int) and beat["seconds"] > 0 for beat in beats)


def test_every_running_total_recomputes_from_the_durations(beats: list):
    """Each running total is the sum of its own beat and everything before it, and the clock only moves forward."""
    counted = 0
    previous = 0
    for beat in beats:
        counted += beat["seconds"]
        assert beat["running_total"] == counted, "%s says %r, the durations say %d" % (
            beat["id"], beat["running_total"], counted)
        assert beat["seconds"] > 0, "%s has no duration" % beat["id"]
        assert beat["running_total"] > previous, "%s does not advance the clock" % beat["id"]
        previous = beat["running_total"]
    assert counted == TOTAL_SECONDS


# --------------------------------------------------------------------------- 2. the shares

def test_the_per_kind_totals_recompute_from_the_beats(beats: list, sheet: dict):
    """Every kind total in the sheet is the sum of the beats of that kind, and play_seconds is walk plus battle."""
    counted: dict = {}
    for beat in beats:
        counted[beat["kind"]] = counted.get(beat["kind"], 0) + beat["seconds"]
    assert counted == sheet["totals_by_kind"]
    assert sum(counted.values()) == TOTAL_SECONDS
    assert sheet["play_seconds"] == counted["walk"] + counted["battle"] == 318


def test_the_cutscene_share_is_at_most_sixty_percent(beats: list, sheet: dict):
    """A cutscene share over 60 percent is the card's forbidden line, and the declared share must be the real one."""
    total = sum(beat["seconds"] for beat in beats)
    cutscene = sum(beat["seconds"] for beat in beats if beat["kind"] == "cutscene")
    share = cutscene / total
    assert cutscene == 465
    assert share <= CUTSCENE_SHARE_MAX, "cutscene share %.3f is over %.2f" % (share, CUTSCENE_SHARE_MAX)
    assert abs(sheet["cutscene_share"] - share) <= 0.001, "declared %.3f, measured %.3f" % (
        sheet["cutscene_share"], share)


def test_walk_plus_battle_is_at_least_twenty_percent(beats: list, sheet: dict):
    """Play, meaning walk plus battle, is what keeps this a game; under 20 percent is the card's forbidden line."""
    total = sum(beat["seconds"] for beat in beats)
    play = sum(beat["seconds"] for beat in beats if beat["kind"] in ("walk", "battle"))
    share = play / total
    assert play == 318
    assert share >= PLAY_SHARE_MIN, "play share %.3f is under %.2f" % (share, PLAY_SHARE_MIN)
    assert abs(sheet["play_share"] - share) <= 0.001, "declared %.3f, measured %.3f" % (
        sheet["play_share"], share)


def test_the_two_shares_and_the_kind_totals_add_up(beats: list, sheet: dict):
    """Nothing is counted twice and nothing is lost between the shares and the per kind totals."""
    total = sum(beat["seconds"] for beat in beats)
    cutscene = sheet["totals_by_kind"]["cutscene"]
    play = sheet["play_seconds"]
    rest = total - cutscene - play
    assert rest == sheet["totals_by_kind"]["title"] + sheet["totals_by_kind"]["crawl"] + \
        sheet["totals_by_kind"]["menu"] + sheet["totals_by_kind"]["save"]
    assert abs((cutscene + play + rest) / total - 1.0) < 1e-9


# --------------------------------------------------------------------------- 3. the five gates

@pytest.mark.parametrize("label,beat_id,seconds,ceiling_key,_study_pattern", GATES,
                         ids=[gate[0] for gate in GATES])
def test_each_gate_falls_on_the_second_the_card_names(label, beat_id, seconds, ceiling_key,
                                                      _study_pattern, beats, data):
    """The gate is the START of a named beat, so it is subtracted from the running total, never read off it."""
    begins = starts_by_id(beats)
    assert beat_id in begins, "the sheet has no %s beat" % beat_id
    assert begins[beat_id] == seconds, "%s is at %d s, the card says %d s" % (label, begins[beat_id], seconds)


@pytest.mark.parametrize("label,beat_id,seconds,ceiling_key,_study_pattern", GATES,
                         ids=[gate[0] for gate in GATES])
def test_each_gate_is_inside_the_ceiling_pac_32_states(label, beat_id, seconds, ceiling_key,
                                                      _study_pattern, beats, data):
    """PAC-32 owns the ceilings; this reads them instead of restating them, and checks the declared measurement."""
    declared = next(recipe for recipe in data["recipes"] if recipe["id"] == "PAC-32")["params"]
    ceiling = declared[ceiling_key]
    measured = starts_by_id(beats)[beat_id]
    assert measured <= ceiling, "%s at %d s is over the ceiling %d s" % (label, measured, ceiling)
    written = declared.get("measured_" + label + "_seconds")
    if written is not None:
        assert written == measured, "PAC-32 says %s is %r, the sheet says %d" % (label, written, measured)


@pytest.mark.parametrize("label,beat_id,seconds,ceiling_key,study_pattern", GATES,
                         ids=[gate[0] for gate in GATES])
def test_each_gate_matches_the_studys_own_gates_line(label, beat_id, seconds, ceiling_key,
                                                    study_pattern, beats, study_flat):
    """The study and the data file must not drift: section 9 states the same five numbers in words."""
    match = re.search(study_pattern, study_flat)
    assert match is not None, "section 9 no longer states the %s gate" % label
    assert int(match.group(1)) == seconds, "section 9 says %s at %s s, the card says %d s" % (
        label, match.group(1), seconds)
    assert starts_by_id(beats)[beat_id] == seconds


def test_the_first_fight_and_the_first_save_end_where_the_study_says(beats: list, study_flat: str):
    """The study also gives the end of the fight and of the save; a start that moved without an end is caught here."""
    ends = {beat["id"]: beat["running_total"] for beat in beats}
    fight = re.search(r"first fight beginning at (\d+) s \(([\d:]+)\) and ending at (\d+) s", study_flat)
    save = re.search(r"first save beginning at (\d+) s \(([\d:]+)\) and ending at (\d+) s", study_flat)
    assert fight is not None and save is not None, "the study's gates line changed shape"
    assert ends["first_encounter_hound"] == int(fight.group(3)) == 490
    assert clock_to_seconds(fight.group(2)) == int(fight.group(1))
    assert ends["cabin_save"] == int(save.group(3)) == 642
    assert clock_to_seconds(save.group(2)) == int(save.group(1))


def test_the_studys_table_is_the_sheet_every_row_of_it(beats: list, study_section_9: str):
    """The 32 rows of the study's own table, against the sheet: number, kind, duration and clock on each row."""
    rows = re.findall(r"^\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", study_section_9, re.M)
    assert len(rows) == BEAT_COUNT, "the study's table has %d rows" % len(rows)
    for number, _name, kind, duration, clock in rows:
        beat = beats[int(number) - 1]
        assert beat["n"] == int(number)
        assert kind.strip() == beat["kind"], "beat %s kind %r in the study, %r in the sheet" % (
            number, kind.strip(), beat["kind"])
        assert duration.strip() == "%d s" % beat["seconds"], "beat %s is %r in the study, %d s in the sheet" % (
            number, duration.strip(), beat["seconds"])
        assert clock_to_seconds(clock.strip()) == beat["running_total"], (
            "beat %s ends at %r in the study, %d s in the sheet" % (number, clock.strip(), beat["running_total"]))


def test_the_study_still_states_the_nine_hundred_second_sum(study_section_9: str, beats: list):
    """The study's closing line of the table is "Sum: 900 s exactly"; it is a claim and it is checked."""
    assert "Sum: 900 s exactly" in study_section_9
    assert sum(beat["seconds"] for beat in beats) == 900


# --------------------------------------------------------------------------- 4. the six steps

def test_the_roadmap_holds_six_steps_in_order(roadmap_text: str):
    """S1 to S6, one section each, in the order the roadmap builds them. ROADMAP-2026-10-22.md section 2."""
    blocks = step_blocks(roadmap_text)
    assert [code for code, _title, _body in blocks] == ["S%d" % n for n in range(1, 7)]
    assert all(title for _code, title, _body in blocks)


def test_each_step_names_a_spec_number_a_lane_and_a_check(roadmap_text: str, beats: list):
    """The card's three fields, per step, all non empty, with the spec numbers resolving to real files.

    A spec id that names no file is the failure this catches: specs/ holds 01 to 16 and every step here
    cites one of them, so a step written against a spec that does not exist cannot pass.
    """
    for code, title, body in step_blocks(roadmap_text):
        spec_text = field(body, "Spec")
        lane_text = field(body, "Lane")
        check_text = field(body, "Check")
        assert spec_text, "%s (%s) names no spec" % (code, title)
        assert lane_text, "%s (%s) names no lane" % (code, title)
        assert check_text, "%s (%s) names no check" % (code, title)

        numbers = spec_numbers(spec_text)
        assert numbers, "%s (%s) has a Spec line with no spec number: %r" % (code, title, spec_text)
        for number in numbers:
            matches = [name for name in os.listdir(SPECS) if name.startswith(number + "-")]
            assert matches, "%s (%s) cites spec %s, which is not in specs/" % (code, title, number)

        assert len(check_text.split()) >= 8, "%s (%s) has a check too thin to run: %r" % (
            code, title, check_text)


def test_each_step_lane_is_a_lane_the_roadmap_itself_lists(roadmap_text: str):
    """Every lane a step names appears in the twenty card table and in the Lane counts sentence, and nowhere invented."""
    counts = lane_counts(roadmap_text)
    table = lane_table(roadmap_text)
    assert len(table) == 20, "the card table has %d rows" % len(table)
    assert set(table) == set(counts), "the table lanes and the counts sentence disagree"
    assert sum(counts.values()) == 20

    for code, title, body in step_blocks(roadmap_text):
        lane_text = field(body, "Lane")
        assert lane_text, "%s (%s) names no lane: %r" % (code, title, body[:60])
        named = [lane for lane in counts if re.search(r"(?<![\w-])" + re.escape(lane) + r"(?![\w-])", lane_text)]
        assert named, "%s (%s) names no lane from the roadmap's own table: %r" % (code, title, lane_text)
        assert set(named) <= set(counts), "%s (%s) names a lane the roadmap does not list: %r" % (
            code, title, lane_text)


def test_each_step_names_beats_that_exist_in_the_sheet(roadmap_text: str, beats: list):
    """A step can only claim beats the sheet has, and the six steps between them must not claim a beat twice."""
    ids = {beat["n"]: beat["id"] for beat in beats}
    seen: dict = {}
    for code, title, _body in step_blocks(roadmap_text):
        numbers = named_beats(title)
        assert numbers, "%s names no beat: %r" % (code, title)
        for number in numbers:
            assert number in ids, "%s names beat %d, the sheet has %d beats" % (code, number, len(beats))
            assert number not in seen, "beat %d is claimed by %s and %s" % (number, seen.get(number), code)
            seen[number] = code


def test_each_step_closes_on_the_clock_the_sheet_gives_its_last_beat(roadmap_text: str, beats: list):
    """The end clock in every one of the six headings is the running total of the last beat the step names.

    Only the end clock is asserted. The start clock of S5 (9:12) and the second start clock of S6 (9:52)
    are the running total at the end of a named beat rather than at its start, which is a roadmap edit for
    gamedev; writing either figure into a test here would pin a number the sheet contradicts.
    """
    ends = {beat["n"]: beat["running_total"] for beat in beats}
    for code, title, _body in step_blocks(roadmap_text):
        numbers = named_beats(title)
        clocks = heading_clocks(title)
        last = numbers[-1]
        assert clocks[-1] == ends[last], "%s closes at %d s, beat %d ends at %d s" % (
            code, clocks[-1], last, ends[last])


# --------------------------------------------------------------------------- 5. the checker, and it can fail

def test_the_pacing_checker_passes_on_the_real_files(capsys, monkeypatch):
    """tools/check_pacing.py is imported, not copied: it owns the recipe, source and clean room checks too.

    main() reads sys.argv through argparse, so the root is handed over the way the roadmap's gate calls it.
    """
    assert check_pacing.check(ROOT) == []
    monkeypatch.setattr(sys, "argv", ["check_pacing.py", "--root", ROOT])
    exit_code = check_pacing.main()
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "check_pacing: pass, 32 recipes, 32 beats, 900 seconds" in output


def _broken_root(tmp_path, mutate) -> str:
    """A throwaway root holding only the two files check_pacing reads, then mutated."""
    root = tmp_path / "root"
    (root / "data" / "mechanics").mkdir(parents=True)
    (root / "knowledge" / "mechanics").mkdir(parents=True)
    shutil.copy2(DATA, root / "data" / "mechanics" / "pacing_recipes.json")
    shutil.copy2(STUDY, root / "knowledge" / "mechanics" / "PACING-AND-CUTSCENES.md")
    path = root / "data" / "mechanics" / "pacing_recipes.json"
    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    mutate(data)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    return str(root)


def test_one_second_added_to_one_beat_is_caught(tmp_path, monkeypatch):
    """The card's own failing run: a single beat lengthened by one second, on a copy, must be refused.

    The real file is never touched: the copy lives under tmp_path and only the two inputs are written there.
    """
    def longer(data):
        beat = data["beat_sheet"]["beats"][0]
        assert beat["id"] == "title_attract" and beat["seconds"] == 32
        beat["seconds"] = 33

    root = _broken_root(tmp_path, longer)
    errors = check_pacing.check(root)
    assert errors, "a beat lengthened by one second passed the checker"
    assert any("running total" in line and "title_attract" in line for line in errors), errors
    assert any("901 seconds" in line for line in errors), errors
    monkeypatch.setattr(sys, "argv", ["check_pacing.py", "--root", root])
    assert check_pacing.main() == 1


def test_one_second_added_with_the_clock_recomputed_is_still_caught(tmp_path):
    """A subtler edit: the total and every running total are redone, so only the 900 s equality can see it.

    This is the case a test that only re-summed the clock would miss, and the kind totals and the share
    are what notice it besides the sum.
    """
    def longer_and_recomputed(data):
        sheet = data["beat_sheet"]
        sheet["beats"][13]["seconds"] += 1
        assert sheet["beats"][13]["id"] == "winchester_cathedral"
        counted = 0
        for beat in sheet["beats"]:
            counted += beat["seconds"]
            beat["running_total"] = counted

    root = _broken_root(tmp_path, longer_and_recomputed)
    errors = check_pacing.check(root)
    assert any("901 seconds" in line for line in errors), errors
    assert any("kind totals" in line for line in errors), errors
    assert not any("running total" in line for line in errors), (
        "this edit recomputed the clock on purpose: %s" % errors)


def test_dropping_a_recipe_from_prose_is_caught(tmp_path):
    """The study's own second failing case: a recipe reduced to prose has to be refused, not tolerated."""
    def prose(data):
        recipe = data["recipes"][3]
        assert recipe["id"] == "PAC-04"
        recipe["params"] = {"note": "see the study"}

    root = _broken_root(tmp_path, prose)
    errors = check_pacing.check(root)
    assert any("PAC-04 has fewer than three numeric parameters" in line for line in errors), errors


# --------------------------------------------------------------------------- 6. no network

def test_nothing_here_or_in_the_checker_reaches_the_network():
    """A test that reads a page is not a test of this repository, so the import lists are scanned."""
    for path in (os.path.abspath(__file__), os.path.join(ROOT, "tools", "check_pacing.py")):
        source = _read(path)
        for token in NETWORK_TOKENS:
            assert not re.search(r"^\s*(?:import|from)\s+" + re.escape(token), source, re.M), (
                "%s imports %s" % (os.path.basename(path), token))
    measured = {os.path.basename(path) for path in (DATA, STUDY, ROADMAP)}
    assert measured == {"pacing_recipes.json", "PACING-AND-CUTSCENES.md", "ROADMAP-2026-10-22.md"}
