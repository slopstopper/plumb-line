"""Facts the skills state about the code, pinned so they cannot drift (#445).

The skills ship in the plugin and are followed literally by agents. The
2026-09-25 staleness sweep found them teaching things the code contradicts:
a vendoring list that omitted a bundled file (a vendored copy then lost the
baseline API), a numeric `confidence: 0` the envelope does not accept, a JS
`=== []` assertion that can never pass, and "the checker is usually
unavailable" when it ships inside the plugin.

Run from the repo root: python3 -m pytest -q scripts/test_skill_facts.py
"""
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKILLS = os.path.join(_ROOT, "skills")
_BUNDLE = os.path.join(_ROOT, ".claude-plugin", "bundled", "primitives")


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


SKILLS = {d: _read(_SKILLS, d, "SKILL.md") for d in sorted(os.listdir(_SKILLS))
          if os.path.isfile(os.path.join(_SKILLS, d, "SKILL.md"))}


@pytest.mark.parametrize("lang", ["js", "python"])
def test_bootstrap_vendoring_list_is_the_whole_bundle(lang):
    bundled = {f for f in os.listdir(os.path.join(_BUNDLE, lang))
               if f.endswith((".mjs", ".py"))}
    text = SKILLS["plumb-line-bootstrap"]
    section = text[text.index("bundled/primitives/js/"):text.index("They carry a dual-import shim")]
    ext = ".mjs" if lang == "js" else ".py"
    listed = set(re.findall(r"`([\w]+%s)`" % re.escape(ext), section))
    assert listed == bundled, f"bootstrap lists {sorted(listed)}; the {lang} bundle has {sorted(bundled)}"


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_no_js_array_identity_assertion(skill):
    # `===` compares array identity: a test written from this never passes.
    assert not re.search(r"===\s*\[\s*\]|\.toBe\(\s*\[\s*\]\s*\)", SKILLS[skill]), skill


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_confidence_is_never_written_as_a_number(skill):
    # confidence is a rung (none|low|medium|high); the number is confidenceScore.
    # JS `confidence: 0`, Python `confidence=0`, dict/JSON `'confidence': 0`.
    assert not re.search(r"\bconfidence['\"]?\s*[:=]\s*[0-9]", SKILLS[skill]), skill


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_skills_do_not_call_the_shipped_checker_unavailable(skill):
    for phrase in ("common case in a consumer repo", "usually unavailable", "is not reachable (the"):
        assert phrase not in SKILLS[skill], (skill, phrase)
    if "check_report_format.py" in SKILLS[skill]:
        assert "<plugin root>/scripts/check_report_format.py" in SKILLS[skill], (
            f"{skill} names the checker but not where it ships in the plugin")


# #514: an agent copies a skill's own wording into its report or record, and
# the report contract rejects a principle code that is not inline-named with
# its canonical name. So the skills whose output the checker validates must
# model that form. As strict as the checker on names (the canonical name must
# follow the dash), and stricter on joiners on purpose: a code joined by "/"
# or "-" (P1/P2, P6-adjacent) is still a bare citation to a reader, whatever
# the checker's path-shaped exclusions let through. Inline code spans are
# masked, as the checker masks them: that is where a skill quotes the forms
# it forbids. A range (P1–P9) is not a citation.
_SKILL_CODE = re.compile(r"(?<![\w–—])P([1-9])(?![\w–—])")
_FENCE_LINE = re.compile(r"^[ \t]*(?:```+|~~~+).*$", re.M)
# A span may soft-wrap onto the next line, so it may cross a newline, but not
# a blank line: one stray backtick must not mask the rest of the file.
_CODE_SPAN = re.compile(r"`(?:[^`\n]|\n(?![ \t]*\n))*`")
_PRINCIPLE_HEADING = re.compile(r"^## Principle (\d) — (.+?)\s*$", re.M)
PRINCIPLES = dict(_PRINCIPLE_HEADING.findall(_read(_ROOT, "reference", "portable-principles.md")))


def _scan_codes(text):
    """(bare, named): lines citing a code without its canonical name, and the
    set of codes seen correctly inline-named, after masking."""
    masked = _FENCE_LINE.sub(lambda m: " " * len(m.group(0)), text)
    masked = _CODE_SPAN.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), masked)
    lines, masked_lines = text.split("\n"), masked.split("\n")
    assert len(lines) == len(masked_lines), "masking must keep line numbers"
    bare, named = [], set()
    for n, line in enumerate(masked_lines, 1):
        for m in _SKILL_CODE.finditer(line):
            # The name may start on the next line when the prose wraps after "—".
            rest = line[m.end():] + " " + (masked_lines[n].lstrip() if n < len(masked_lines) else "")
            dash = re.match(r"[ \t]*—[ \t]*", rest)
            if dash and rest[dash.end():].startswith(PRINCIPLES[m.group(1)]):
                named.add(m.group(1))
                continue
            bare.append(f"line {n}: {lines[n - 1].strip()[:90]}")
            break
    return bare, named


def _bare_codes(text):
    return _scan_codes(text)[0]


def test_principle_names_are_read_from_the_reference():
    assert sorted(PRINCIPLES) == [str(i) for i in range(1, 10)], PRINCIPLES


# The skills whose output check_report_format.py validates for principle
# names (audit reports, remediation records), plus adopt, whose routing
# output names principles in prose an agent may carry forward.
@pytest.mark.parametrize("skill", ["plumb-line-audit", "plumb-line-remediate", "plumb-line-adopt"])
def test_skill_models_inline_named_codes(skill):
    bare, named = _scan_codes(SKILLS[skill])
    assert bare == [], f"principle codes not inline-named in {skill}:\n" + "\n".join(bare)
    assert named, f"the scan saw no named code in {skill}: masking may have blanked it"


def test_the_scan_sees_the_audit_skills_named_codes():
    # Guards a vacuous pass: if masking ever blanked the file, the scan would
    # find no bare codes and also no named ones. The audit skill's glossary
    # example names all nine.
    _, named = _scan_codes(SKILLS["plumb-line-audit"])
    assert named == set(PRINCIPLES), sorted(set(PRINCIPLES) - named)


def test_bare_code_scan_catches_the_forms_it_must():
    assert _bare_codes("the audit's P1/P2 coverage is partial")
    assert _bare_codes("a P6-adjacent advisory")
    assert _bare_codes("this violates P3.")
    assert _bare_codes("a **P3** finding")
    assert _bare_codes("| x | P8 |")
    assert _bare_codes("P3 — Confidence and provenance")           # wrong name
    assert _bare_codes("P9 — the explanation IS the fix")          # wrong name
    assert _bare_codes("a `stray tick\n\nthen P3 in the next paragraph")
    assert not _bare_codes("P3 — Confidence + provenance")
    assert not _bare_codes("P1–P9")
    assert not _bare_codes("never `Provenance (P3)`")
    assert not _bare_codes("a header (`Provenance (P3 —\nConfidence + provenance)`, not `Provenance (P3)`)")
    assert not _bare_codes("cite P3 —\nConfidence + provenance")
    assert not _bare_codes("P8 — State-first\n  lineage")                # wrapped, indented
    assert _bare_codes("```\na fenced example citing P3 bare\n```")   # examples get copied too


# --- #485: honest deferral, as the method skill teaches it (option C) --------

_EXAMPLE = os.path.join(_ROOT, "examples", "honest-deferral")


def _deferral_section():
    text = SKILLS["plumb-line-method"]
    start = text.index("## Mid-task: a test that cannot pass honestly")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else len(text)]


def test_method_skill_states_all_four_deferral_conditions():
    # Owner decision on #485, option C: all four, or it is a cheat.
    section = _deferral_section().lower()
    for condition in ("strict", "assertion unchanged", "reason", "not met"):
        assert condition in section, f"the deferral section must state: {condition}"
    assert "never a deferral" in section, "skipping must be named as never a deferral"


def test_method_skill_forms_are_the_ones_the_example_runs():
    # The skill teaches these spellings; the example (run by
    # examples/test_honest_deferral.py) proves they behave as taught.
    section = _deferral_section()
    py = _read(_EXAMPLE, "python", "test_carrier.py")
    js = _read(_EXAMPLE, "js", "carrier.test.js")
    assert "pytest.mark.xfail(strict=True" in section and "pytest.mark.xfail(strict=True" in py
    assert "it.fails(" in section and "it.fails(" in js


def test_remediate_points_to_the_method_skill_for_a_test_it_cannot_fix():
    text = " ".join(SKILLS["plumb-line-remediate"].split())  # prose wraps
    assert "Mid-task: a test that cannot pass honestly" in text


def test_deferral_keeps_the_owners_wording_on_issues():
    # Option C: "Reason stated in the marker, ideally citing a tracked issue".
    assert "ideally" in _deferral_section()


def test_deferral_forms_do_not_let_a_crash_pass_as_the_expected_failure():
    # xfail and it.fails accept any failing test. pytest can be narrowed with
    # raises=AssertionError; vitest cannot, so the skill must say so and pair
    # it with a test of the observable failure (#485 review).
    section = " ".join(_deferral_section().split())
    py = _read(_EXAMPLE, "python", "test_carrier.py")
    assert "raises=AssertionError" in section and "raises=AssertionError" in py
    assert "any error" in section
    # Markers that look strict but never run, or cannot be strict.
    assert "run=False" in section and "pytest.xfail()" in section


def test_js_deferral_reason_is_in_the_marker_not_a_comment():
    js = _read(_EXAMPLE, "js", "carrier.test.js")
    title = re.search(r'it\.fails\(\s*"([^"]+)"', js)
    assert title and "not reachable" in title.group(1) and "EXAMPLE-1" in title.group(1)


def test_remediate_records_an_approved_deferral_as_applied_judgment():
    text = " ".join(SKILLS["plumb-line-remediate"].split())
    start = text.index("Mid-task: a test that cannot pass honestly")
    assert "applied-judgment" in text[start - 600:start + 600]


# --- #485 owner ruling on PR #536: usable, not a block on coding ------------
# "It needs to be practically usable and help keep the code honest about
# itself, not stop a user being able to code."

def _not_forbidden():
    section = _deferral_section()
    start = section.index("### What this does not forbid")
    end = section.find("\n### ", start + 1)
    return " ".join(section[start:end if end != -1 else len(section)].split())


def test_the_carve_outs_come_before_the_steps():
    # Read first, so the section is not over-applied to ordinary test work.
    section = _deferral_section()
    assert section.index("### What this does not forbid") < section.index("1. **Find the failure")


def test_the_carve_outs_name_each_legitimate_change():
    text = _not_forbidden()
    assert "wrong" in text and "say what was wrong" in text      # a wrong test is fixed
    assert "P4" in text and "labelled" in text and "`mock`" in text  # stubs while building
    assert "unit test" in text                                    # ordinary mocks
    assert "whose decision" in text                               # thresholds, removals
    assert "not stop" in text or "not a block" in text            # the ruling itself


def test_step_two_targets_an_unmet_requirement_read_as_met():
    # Step 2 itself, not "read as met" anywhere in the section (#485 review).
    assert "2. **Do not make an unmet requirement read as met.**" in _deferral_section()


def test_the_carve_outs_close_the_loopholes_the_review_found():
    text = _not_forbidden()
    # Intended behaviour changes are outside the moment (snapshots, TDD).
    assert "Behaviour you changed on purpose" in text
    # B1: a request to get CI green is not a decision about the requirement,
    # and disclosing a change that fakes the requirement does not make it honest.
    assert "is not a decision" in text and "does not make it honest" in text
    # B2, B3: stubs and unit-test mocks sit alongside the requirement's test,
    # never in place of it.
    assert text.count("in place of") >= 2
    # A2: P4's own terms, including the owner's opt-in.
    assert "opts in" in text


def test_the_carve_outs_name_principles_in_house_style():
    text = _not_forbidden()
    assert "P4 — Quarantined fakery" in text and "P6 — Maturity vocabulary" in text


# --- #487: the method skill's other moments, and its description in step ---
# Owner decisions on #487 (2026-09-29): a "yes, and" framing for every
# moment; method first where the aim is to make something look more real,
# finished or certain than it is; adopt first when building with a stand-in.

def _other_moments():
    text = SKILLS["plumb-line-method"]
    start = text.index("## Mid-task: other moments")
    end = text.find("\n## ", start + 1)
    return " ".join(text[start:end if end != -1 else len(text)].split())


def test_other_moments_meet_the_need_and_name_the_one_no():
    text = _other_moments().lower()
    for moment in ("fallback", "hardcod", "production-ready", "generated", "fixture",
                   "provenance", "baseline", "layer", "inconclusive"):
        assert moment in text, f"the other-moments section must cover: {moment}"
    assert "yes, and" in text and "the only no" in text


def test_other_moments_hand_off_to_the_skills_with_the_tools():
    text = _other_moments()
    assert "plumb-line-adopt" in text and "plumb-line-bootstrap" in text


def _method_description():
    text = SKILLS["plumb-line-method"]
    front = text.split("\n---", 1)[0]
    line = next(ln for ln in front.splitlines() if ln.startswith("description:"))
    return line.split(":", 1)[1].strip().strip('"').lower()


# A moment the description claims must be taught in the body, or the
# description overstates what the skill does (P6 — Maturity vocabulary).
_CLAIMS = {"fallback": "fallback", "baseline": "baseline", "inconclusive": "inconclusive",
           "hardcod": "hardcod", "production-ready": "production-ready",
           "provenance": "provenance", "layer": "layer",
           "failing test": "a test that cannot pass"}


def test_adopt_mid_task_says_yes_and_with_tracking_short_of_the_primitive():
    # Owner, #487: "add the mock but here's how we can keep track of it".
    text = SKILLS["plumb-line-adopt"]
    start = text.index("## Surfacing mid-task")
    section = " ".join(text[start:].split("\n## ")[0].split()).lower()
    assert "yes, and" in section and "keep track" in section
    # Not every repo uses the primitive: a plain label or marker counts.
    assert "label" in section and "marker" in section


def test_adopt_description_claims_building_with_a_stand_in():
    front = SKILLS["plumb-line-adopt"].split("\n---", 1)[0].lower()
    assert "stand-in" in front and "keep track" in front


def _mid_task_sections():
    # Both in-task sections, not the whole body: "provenance" and "layer"
    # also appear in the runtime-primitive and next-steps sections, which
    # would let a claim pass with the table deleted (#487 review).
    text = SKILLS["plumb-line-method"]
    start = text.index("## Mid-task: a test that cannot pass honestly")
    end = text.index("## The runtime primitive")
    return " ".join(text[start:end].split()).lower()


def test_every_moment_the_description_claims_is_taught_in_a_mid_task_section():
    desc = _method_description()
    body = _mid_task_sections()
    claimed = [c for c in _CLAIMS if c in desc]
    assert len(claimed) >= 6, f"the description should claim the moments; found {claimed}"
    for claim in claimed:
        assert _CLAIMS[claim] in body, f"description claims {claim!r}; no mid-task section teaches it"


def _row(keyword):
    # One table line of "Mid-task: other moments"; the first cell names the moment.
    text = SKILLS["plumb-line-method"]
    start = text.index("## Mid-task: other moments")
    lines = text[start:text.index("\n## ", start + 1)].splitlines()
    rows = [ln for ln in lines if ln.startswith("| ") and keyword in ln.split("|")[1].lower()]
    assert len(rows) == 1, f"expected one table row for {keyword}, found {len(rows)}"
    return rows[0].lower()


def test_the_baseline_row_needs_a_decision_and_sends_unexplained_drift_to_the_test_section():
    row = _row("baseline")
    assert "on whose decision" in row and "own judgment" in row
    assert "failing test" in row


def test_the_layer_row_never_widens_or_bypasses_the_boundary_check():
    row = _row("layer")
    assert "composition root" in row and "never widen or bypass" in row


def test_the_fixture_row_keeps_stand_in_data_out_of_the_real_store():
    row = _row("fixture")
    assert "out of the real store" in row and "p1 — source-truth layer" in row


def test_the_fallback_row_is_about_passing_a_stand_in_off_as_real():
    assert "passed off as real" in _row("fallback").split("|")[1]


def test_adopt_says_the_task_agent_adds_the_stand_in_and_adopt_edits_nothing():
    text = SKILLS["plumb-line-adopt"]
    start = text.index("## Surfacing mid-task")
    section = " ".join(text[start:].split("\n## ")[0].split()).lower()
    assert "edits nothing" in section and "not a routing report" in section


def test_the_baseline_row_settles_just_regenerate_it():
    # "Just regenerate it, I don't know why it moved" is a request for green,
    # not a decision (#485's confirmed reading); the row must not allow both.
    row = _row("baseline")
    assert "just regenerate" in row and "accepted unexplained" in row


def test_the_layer_row_agrees_with_the_test_section_and_covers_a_failing_gate():
    row = _row("layer")
    assert "name the issue" in row          # never filed unasked (the test section)
    assert "boundary check fails" in row    # then it is that section's moment


def test_adopt_contract_names_the_mid_task_exception_and_keeps_the_citation():
    text = SKILLS["plumb-line-adopt"]
    contract = text[text.index("## The routing report is contracted"):]
    contract = " ".join(contract.split("\n## ")[0].split()).lower()
    assert "brief mid-task answer" in contract
    mid = " ".join(text[text.index("## Surfacing mid-task"):].split()).lower()
    assert "cite what you saw" in mid


# --- #486: the audit names a test changed so an unmet requirement reads as met ---
# Owner decisions 2026-09-29 (#485, #486): one finding class, the method
# skill's line (flag only when nothing records why or on whose decision),
# never the method skill's carve-outs.

def _audit_check_10():
    text = SKILLS["plumb-line-audit"]
    start = text.index("10. Test changed to pass")
    end = text.index("\n## Method", start)
    return " ".join(text[start:end].split())


def test_audit_catalogue_has_the_test_changed_to_pass_check():
    check = _audit_check_10().lower()
    for form in ("substitut", "skipped", "rewritten", "threshold", "retries"):
        assert form in check, f"check 10 must name the form: {form}"
    assert "spine" in check and "p4 — quarantined fakery" in check


def test_audit_check_10_uses_the_method_skills_line_and_carve_outs():
    check = _audit_check_10().lower()
    assert "whose decision" in check
    for carve_out in ("on purpose", "wrong test", "labelled stub", "unit test"):
        assert carve_out in check, f"check 10 must exempt: {carve_out}"


def test_audit_check_10_does_not_excuse_a_double_for_being_in_a_test_file():
    # Four spike audits called the test double acceptable (#486).
    assert "not acceptable because it sits in a test file" in _audit_check_10().lower()


def test_audit_check_10_names_itself_and_the_honest_paths():
    check = _audit_check_10().lower()
    assert "not as evidence for a product defect" in check
    assert "strict" in check and "stay red" in check


def test_audit_reads_the_tests_that_state_requirements():
    text = " ".join(SKILLS["plumb-line-audit"].split()).lower()
    assert "test files are in scope" in text


# --- #486 option (a): check 10 tightened to the method skill's line ---------

def test_audit_check_10_a_stated_reason_alone_is_not_a_decision():
    check = _audit_check_10().lower()
    assert "a stated reason alone is not a decision" in check
    # The loose gate the review found must be gone.
    assert "nothing records why or on whose decision" not in check


def test_audit_check_10_is_not_downgraded_by_the_spine_calibration():
    assert "the spine calibration does not govern check 10" in _audit_check_10().lower()


def test_audit_check_10_markers_that_do_not_count_as_a_record():
    check = _audit_check_10().lower()
    assert "run=false" in check and "commented out" in check


def test_audit_check_10_asks_whether_the_test_states_the_requirement():
    # Mocking transport in an HTTP-client unit test is ordinary; the question
    # is whether this test states the requirement (#486 review).
    assert "states the requirement" in _audit_check_10().lower()
