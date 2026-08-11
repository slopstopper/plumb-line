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


# --- false positives: valid-but-unusual reports the checker MUST accept ----
#
# Found by an adversarial pass before merge. Each of these is legal per the
# skill's own format spec; a checker that rejects them is one a user disables,
# after which it catches nothing.

def test_principle_cited_inline_named_mid_sentence_is_accepted():
    """The spec REQUIRES prose citations to be inline-named. Comparing the
    canonical name against everything up to the line end rejected exactly the
    usage the format mandates."""
    text = VALID_REPORT.replace(
        "\n| Path |",
        "\nThis run leaned on P3 — Confidence + provenance throughout.\n\n| Path |")
    assert _check(text) == []


def test_glossary_with_several_principles_per_line_is_accepted():
    assert _check(VALID_REPORT) == []   # the fixture glossary packs two per line


def test_em_dash_placeholders_in_line_and_function_are_accepted():
    text = VALID_REPORT.replace("| 42 | `load_scores` |", "| — | — |")
    assert _check(text) == []


def test_extra_optional_header_key_after_the_required_ones_is_accepted():
    text = VALID_REPORT.replace("commit:              abab68d\n",
                                "commit:              abab68d\nauditor:             plumb-line-audit\n")
    assert _check(text) == []


def test_repeated_bare_citation_reports_the_problem_once():
    text = VALID_REPORT.replace("P3 — Confidence + provenance", "P3")
    bare = [i for i in _check(text) if "not inline-named" in i]
    assert len(bare) == 1, bare


# --- review findings, pinned ----------------------------------------------

ALIGNED_RECORD = """remediation-format: v1
source-report:       r.md
source-report-format: v3
principles-revision: 1
date:                2026-08-11
commit:              abab68d

| Finding | Path   | Class      | Action        | Change summary |
| ------- | ------ | ---------- | ------------- | -------------- |
| 1       | `a.py` | mechanical | totally-bogus | did a thing    |
"""


def test_column_aligned_table_is_still_parsed():
    """Comparing the RAW header line required single-space padding, so an
    aligned table — what a model actually emits — never matched, and the
    fallback returned zero rows. Every per-row check was silently dead: this
    record passed clean with a bogus Action verb."""
    issues = _check(ALIGNED_RECORD)
    assert any("unknown Action" in i for i in issues), issues


def test_record_row_with_wrong_cell_count_is_flagged():
    text = ALIGNED_RECORD.replace(
        "| 1       | `a.py` | mechanical | totally-bogus | did a thing    |",
        "| 1       | mechanical | applied-mechanical |")
    assert any("cells, expected" in i for i in _check(text))


def test_bootstrap_report_is_header_only_by_design():
    """Bootstrap shares the v3 header block and nothing else — glossary,
    findings table and coverage map are audit-specific. Without this the
    checker failed a conformant bootstrap report three times over, and the
    harness runs it on every report."""
    text = """report-format: v3
scope:               my-project
principles-revision: 1
date:                2026-08-11
commit:              abab68d
adapter:             js

Created: eslint.config.cjs, .claude/guards/pre-commit-gate.mjs
Step 4b: declined — project untouched.
"""
    assert _check(text) == []


def test_v1_report_is_not_judged_by_v3_rules():
    """The contract grew: glossary and findings table in v2, coverage map in
    v3. A stored v1 report must not fail for lacking parts it never had."""
    text = """report-format: v1
scope:               src/
principles-revision: 1
date:                2026-08-11
commit:              abab68d

Two findings, described in prose as v1 allowed.
"""
    assert _check(text) == []


def test_non_ascii_digits_are_rejected_in_date_and_revision():
    """Same class as the Age-header fix one commit earlier: \\d and isdigit()
    are Unicode-aware, so both accepted values int() cannot parse."""
    text = VALID_REPORT.replace("2026-08-11", "٢٠٢٦-٠٨-١١")
    assert any("date" in i for i in _check(text))
    text = VALID_REPORT.replace("principles-revision: 1", "principles-revision: ²")
    assert any("principles-revision" in i for i in _check(text))


def test_principle_code_inside_a_path_is_not_a_citation():
    """An audit report quotes repo paths and identifiers; `src/P3-loader.py` is
    a quotation, not a bare citation."""
    text = VALID_REPORT.replace("`src/foo.py`", "`src/P3-loader.py`")
    assert _check(text) == []


def test_principle_code_inside_an_identifier_is_not_a_citation():
    text = VALID_REPORT.replace("`load_scores`", "`P4_STEP`")
    assert _check(text) == []


def test_unreadable_path_fails_cleanly_without_a_traceback():
    assert crf.main(["/nonexistent/report.md"]) == 1


# --- second review round: checks that were silently vacuous ---------------
#
# Three of these made the checker print "conforms" on a report that violates
# the contract — strictly worse than not shipping it.

ALIGNED_REPORT = """report-format: v3
scope:               src/
principles-revision: 1
date:                2026-08-11
commit:              abab68d

| Path        | Line | Function | Issue | Suggested Fix | Principle              |
| ----------- | ---- | -------- | ----- | ------------- | ---------------------- |
| `src/a.py`  | 42   | `f`      | issue | fix           | P5 — Injectable priors |

coverage: 1/1 files read, 0 partial, 0 not-read (100%)
scope note: no completeness claimed.
"""


def test_glossary_check_works_on_an_aligned_table():
    """_glossary_codes split on the literal '| Path |', so an aligned table put
    the WHOLE document in the glossary head — cited set equalled glossary set
    and this check could never fire. Same aligned-table bug as _table_columns,
    left one function below it."""
    assert any("not in the glossary" in i for i in _check(ALIGNED_REPORT))


def test_no_findings_phrase_in_prose_does_not_excuse_a_bad_table():
    """'No findings.' stands IN PLACE OF the table; accepting it anywhere in the
    document let a prose sentence excuse a malformed one."""
    text = ALIGNED_REPORT.replace(
        "| Path        | Line | Function | Issue | Suggested Fix | Principle              |",
        "| Path | Line | Issue | Suggested Fix | Principle |").replace(
        "scope note: no completeness claimed.",
        "scope note: No findings. in adapters/; completeness not claimed.")
    assert any("findings table columns" in i for i in _check(text))


def test_findings_row_missing_the_principle_cell_is_flagged():
    text = VALID_REPORT.replace(
        "| `src/bar.py` | — | — | output has no contract | add a version constant | P7 — Contracted outputs |",
        "| `src/bar.py` | — | — | output has no contract | add a version constant |")
    assert any("findings row" in i and "cells" in i for i in _check(text))


def test_empty_contract_version_is_a_failure_not_a_default():
    text = VALID_REPORT.replace("report-format: v3", "report-format:")
    assert any("has no value" in i for i in _check(text))


def test_bare_code_before_a_full_stop_is_flagged():
    """The most common prose position for a bare citation; excluding '.' from
    the lookahead put a hole in the headline 'never a bare P3' rule."""
    text = VALID_REPORT.replace("2 findings:", "This clearly violates P3.\n\n2 findings:")
    assert any("not inline-named" in i for i in _check(text))


def test_en_dash_principle_range_is_not_two_bare_citations():
    text = VALID_REPORT.replace("2 findings:", "Audited against P1–P9 as a set.\n\n2 findings:")
    assert not any("not inline-named" in i for i in _check(text))


def test_leading_blank_line_does_not_break_header_detection():
    assert _check("\n" + VALID_REPORT) == []


def test_escaped_pipe_in_a_cell_is_not_an_extra_column():
    text = VALID_REMEDIATION.replace("tagged via derive", r"ran `a \| b`")
    assert not any("cells, expected" in i for i in _check(text))


def issues_of(text):
    return _check(text)
