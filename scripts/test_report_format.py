"""Tests for scripts/check_report_format.py — the report-contract validator.

Run from the repo root:

    python3 -m pytest -q scripts/test_report_format.py

P7 (Contracted outputs) names three parts: a version constant, a canonical key
list, and a VALIDATOR. The first two shipped with report-format v1; this is the
third (#139). Until it existed, "no format FAILs" in docs/validation-results.md
was a human judgement repeated across six release runs.
"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_spec = importlib.util.spec_from_file_location(
    "_check_report_format", os.path.join(_HERE, "check_report_format.py"))
crf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crf)

PRINCIPLES = crf.load_principles(
    open(os.path.join(_ROOT, "reference", "portable-principles.md"), encoding="utf-8").read())

VALID_REPORT = """report-format: v3
scope:               src/
principles-revision: 1
date:                2026-08-11
commit:              abab68d

P3 — Confidence + provenance  P7 — Contracted outputs

| Path | Line | Function | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ----- | ------------- | --------- |
| `src/foo.py` | 42 | `load_scores` | mock given a real source | tag via derive | P3 — Confidence + provenance |
| `src/bar.py` | — | — | output has no contract | add a version constant | P7 — Contracted outputs |

coverage: 12/47 files read, 3 partial, 32 not-read (32%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness.

2 findings: 2 violations, 0 needs-review
"""

VALID_REMEDIATION = """remediation-format: v1
source-report:       plumb-line-audit.md
source-report-format: v3
principles-revision: 1
date:                2026-08-11
commit:              working tree (uncommitted)

| Finding | Path | Class | Action | Change summary |
| ------- | ---- | ----- | ------ | -------------- |
| 1 | `src/foo.py` | mechanical | applied-mechanical | tagged via derive |
| 2 | `src/bar.py` | judgment | blocked | needs a source decision (P3 — Confidence + provenance) |
"""


def _check(text):
    return crf.check(text, PRINCIPLES)


# --- principle table is read from the ruleset, never hardcoded -------------

def test_principles_are_loaded_from_the_ruleset():
    assert PRINCIPLES["P3"] == "Confidence + provenance"
    assert PRINCIPLES["P9"] == "Golden baseline + explain-the-drift"
    assert len(PRINCIPLES) == 9


# --- happy paths -----------------------------------------------------------

def test_valid_audit_report_passes():
    assert _check(VALID_REPORT) == []


def test_valid_remediation_record_passes():
    assert _check(VALID_REMEDIATION) == []


def test_clean_run_with_no_findings_passes():
    text = VALID_REPORT.split("| Path |")[0] + "No findings.\n\n" + \
        "coverage: 4/4 files read, 0 partial, 0 not-read (100%)\n" + \
        "scope note: diff-scoped run; denominator is the touched files.\n"
    assert _check(text) == []


# --- header contract -------------------------------------------------------

def test_unknown_format_is_rejected():
    issues = _check("nonsense: v1\n")
    assert any("unrecognised report contract" in i for i in issues)


def test_missing_header_key_is_flagged():
    text = VALID_REPORT.replace("commit:              abab68d\n", "")
    assert any("missing required header key: commit" in i for i in issues_of(text))


def test_header_keys_out_of_order_are_flagged():
    text = VALID_REPORT.replace(
        "scope:               src/\nprinciples-revision: 1\n",
        "principles-revision: 1\nscope:               src/\n")
    assert any("header keys out of order" in i for i in issues_of(text))


def test_malformed_date_is_flagged():
    text = VALID_REPORT.replace("2026-08-11", "11/08/2026")
    assert any("date" in i for i in issues_of(text))


def test_unknown_format_version_is_flagged():
    text = VALID_REPORT.replace("report-format: v3", "report-format: v9")
    assert any("unknown report-format version" in i for i in issues_of(text))


def test_commit_accepts_working_tree_literal():
    text = VALID_REPORT.replace("commit:              abab68d",
                                "commit:              working tree (uncommitted)")
    assert _check(text) == []


def test_bad_commit_value_is_flagged():
    text = VALID_REPORT.replace("commit:              abab68d",
                                "commit:              yesterday")
    assert any("commit" in i for i in issues_of(text))


# --- findings table --------------------------------------------------------

def test_wrong_findings_columns_are_flagged():
    text = VALID_REPORT.replace(
        "| Path | Line | Function | Issue | Suggested Fix | Principle |",
        "| Path | Line | Issue | Suggested Fix | Principle |")
    assert any("findings table columns" in i for i in issues_of(text))


def test_missing_findings_table_and_no_findings_line_is_flagged():
    head, _, tail = VALID_REPORT.partition("| Path |")
    text = head + "\n".join(tail.split("\n")[6:])
    assert any("findings table" in i or "No findings." in i for i in issues_of(text))


# --- glossary + inline naming ---------------------------------------------

def test_bare_principle_reference_is_flagged():
    text = VALID_REPORT.replace("(P3 — Confidence + provenance)", "(P3)")
    text = text.replace("| P7 — Contracted outputs |", "| P7 |")
    assert any("not inline-named" in i for i in issues_of(text))


def test_wrong_principle_name_is_flagged():
    text = VALID_REPORT.replace("P3 — Confidence + provenance",
                                "P3 — Confidence and provenance")
    assert any("wrong name" in i for i in issues_of(text))


def test_cited_principle_missing_from_glossary_is_flagged():
    text = VALID_REPORT.replace("P3 — Confidence + provenance  P7 — Contracted outputs",
                                "P3 — Confidence + provenance")
    assert any("not in the glossary" in i for i in issues_of(text))


# --- coverage map ----------------------------------------------------------

def test_missing_coverage_map_is_flagged():
    text = "\n".join(ln for ln in VALID_REPORT.split("\n")
                     if not ln.startswith("coverage:"))
    assert any("coverage map" in i for i in issues_of(text))


def test_missing_scope_note_is_flagged():
    text = VALID_REPORT.replace("scope note: findings are drawn", "note: findings are drawn")
    assert any("scope note" in i for i in issues_of(text))


# --- remediation record ----------------------------------------------------

def test_unknown_action_verb_is_flagged():
    text = VALID_REMEDIATION.replace("applied-mechanical", "sort-of-applied")
    assert any("unknown Action" in i for i in issues_of(text))


def test_wrong_remediation_columns_are_flagged():
    text = VALID_REMEDIATION.replace(
        "| Finding | Path | Class | Action | Change summary |",
        "| Finding | Path | Action | Change summary |")
    assert any("record table columns" in i for i in issues_of(text))


def test_remediation_missing_source_report_format_is_flagged():
    text = VALID_REMEDIATION.replace("source-report-format: v3\n", "")
    assert any("source-report-format" in i for i in issues_of(text))


def issues_of(text):
    return _check(text)
