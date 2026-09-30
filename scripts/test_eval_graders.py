"""test_eval_graders — the eval suite's finds-* graders read a report-format v4
findings row the way scripts/check_report_format.py does (#530).

A broken case's verdict rests on these graders (the runner's LLM judge was
dropped there, #530), so a grader and the checker must agree on what a
confirmed row is: a Status cell that the checker accepts as `violation`
matches, and any other status does not. Each pattern is checked with Python's
`re`, and with JavaScript's RegExp when node is on PATH (a visible skip
otherwise; CI installs node). The spellings are a fixed list, each confirmed
by the real checker.

Run from the repo root:  python3 -m pytest -q scripts/test_eval_graders.py
"""
import glob
import importlib.util
import os
import re
import shutil
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("crf", os.path.join(_ROOT, "scripts", "check_report_format.py"))
crf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crf)

GRADERS = sorted(glob.glob(os.path.join(_ROOT, "evals", "*-broken", "graders", "finds-*.md")))

# Status cells the checker accepts as `violation`, and cells it refuses or
# reads as another status.
CONFIRMED = ["violation", "Violation", "VIOLATION", "**violation**", "*violation*",
             "***violation***", "`violation`", "**`violation`**"]
NOT_CONFIRMED = ["needs-review", "advisory", "**needs-review**", "violation.", "violation:",
                 "confirmed", "", "needs review"]


def _pattern(path):
    return re.search(r"^pattern: '(.*)'$", open(path, encoding="utf-8").read(), re.M).group(1)


def _row(pattern, status):
    """A findings row naming the grader's planted file and principle."""
    fname = re.search(r"\)\*([A-Za-z_]+\\\.[a-z]+)\(\?:", pattern).group(1).replace("\\.", ".")
    principle = re.search(r"\)\*(P\d — [^(]+?)\(\?:", pattern).group(1).replace("\\+", "+")
    return f"| `src/x/{fname}` | 8 | `f` | {status} | an issue | a fix | {principle} |"


def _matches(pattern, text):
    return re.search(pattern, text, re.M) is not None


def _js_matches(pattern, text):
    out = subprocess.run(
        ["node", "-e", "const [p,t]=process.argv.slice(1);process.stdout.write(String(new RegExp(p,'m').test(t)))",
         pattern, text], capture_output=True, text=True).stdout
    return out == "true"


PRINCIPLES = crf.load_principles(
    open(os.path.join(_ROOT, "reference", "portable-principles.md"), encoding="utf-8").read())
_REPORT = """report-format: v4
scope:               src/
principles-revision: 1
date:                2026-08-11
commit:              abab68d

P3 — Confidence + provenance

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/foo.py` | 42 | `f` | STATUS | an issue | a fix | P3 — Confidence + provenance |

| Output | Provenance | Confidence | Lineage | Contract | Null-expressible | Baseline |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `f` | yes | yes | yes | yes | yes | no |

coverage: 1/1 files read, 0 partial, 0 not-read (100%)
scope note: findings are drawn from the read set only.

1 finding
"""


def _checker_status_ok(status):
    """Whether the real checker accepts a v4 row with this Status, as the word
    `violation` (its other two words are accepted but are not confirmations)."""
    issues = crf.check_report(_REPORT.replace("STATUS", status), PRINCIPLES)
    assert not [i for i in issues if "Status" not in i], issues  # the fixture is otherwise clean
    word = status.strip().strip("*`").strip().lower()
    return not issues and word == "violation"


def test_six_graders_found():
    assert len(GRADERS) == 6, GRADERS


@pytest.mark.parametrize("status", CONFIRMED)
def test_the_checker_reads_these_as_violation(status):
    assert _checker_status_ok(status)


@pytest.mark.parametrize("path", GRADERS, ids=os.path.basename)
def test_a_grader_matches_every_confirmed_spelling_the_checker_accepts(path):
    p = _pattern(path)
    for status in CONFIRMED:
        assert _matches(p, "text\n" + _row(p, status) + "\nmore\n"), status


@pytest.mark.parametrize("path", GRADERS, ids=os.path.basename)
def test_a_grader_matches_no_other_status(path):
    p = _pattern(path)
    for status in NOT_CONFIRMED:
        assert not _checker_status_ok(status)
        assert not _matches(p, "text\n" + _row(p, status) + "\nmore\n"), status


@pytest.mark.parametrize("path", GRADERS, ids=os.path.basename)
def test_a_grader_matches_no_v3_row_and_no_shifted_row(path):
    p = _pattern(path)
    row = _row(p, "violation")
    cells = row.split(" | ")
    v3 = " | ".join(cells[:3] + ["violation: " + cells[4]] + cells[5:])  # status inside Issue, six cells
    assert not _matches(p, "text\n" + v3 + "\nmore\n")
    # An extra leading cell shifts every column: the row is anchored at `^|`.
    shifted = "| x " + row
    assert not _matches(p, "text\n" + shifted + "\nmore\n")


@pytest.mark.parametrize("path", GRADERS, ids=os.path.basename)
def test_a_grader_matches_no_omission_pass_row(path):
    # An omission-pass row as the skill writes it: yes / no cells. (A seven-
    # cell row holding the word `violation` and a principle name in the right
    # cells would match; no omission-pass row has that shape.)
    p = _pattern(path)
    fname = _row(p, "violation").split(" | ")[0].strip("| ")
    omission = f"| {fname} | yes | yes | no | NO | yes | no |"
    assert not _matches(p, "text\n" + omission + "\nmore\n")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH: the JavaScript half is not checked")
@pytest.mark.parametrize("path", GRADERS, ids=os.path.basename)
def test_javascript_reads_each_grader_as_python_does(path):
    # The eval runner is JavaScript; the Python checks above must hold there.
    p = _pattern(path)
    for status in CONFIRMED + NOT_CONFIRMED:
        text = "text\n" + _row(p, status) + "\nmore\n"
        assert _js_matches(p, text) == _matches(p, text), status
    shifted = "text\n| x " + _row(p, "violation") + "\nmore\n"
    assert _js_matches(p, shifted) == _matches(p, shifted)


# --- format-header: the header opens the message (2026-09-30 run) ----------

HEADERS = sorted(glob.glob(os.path.join(_ROOT, "evals", "*", "graders", "format-header.md")))
_REPORT_V4 = _REPORT.replace("STATUS", "violation")
HEADER_OK = [_REPORT_V4, "\n\n" + _REPORT_V4, "```\n" + _REPORT_V4, "```text\n" + _REPORT_V4]
HEADER_NOT_OK = ["The audit found no confirmed violations.\n\n" + _REPORT_V4,
                 "# Plumb-line audit\n\n" + _REPORT_V4,
                 _REPORT_V4.replace("report-format: v4", "report-format: v3")]


def _search(pattern, text):
    return re.search(pattern, text) is not None  # no multiline flag, as in the grader


def test_four_header_graders_found():
    assert len(HEADERS) == 4, HEADERS


@pytest.mark.parametrize("path", HEADERS, ids=lambda p: p.split(os.sep)[-3])
def test_the_header_grader_agrees_with_the_checker_on_where_the_header_is(path):
    p = _pattern(path)
    for text in HEADER_OK:
        assert crf.check(text, PRINCIPLES) == [], text[:40]
        assert _search(p, text), text[:40]
    for text in HEADER_NOT_OK[:2]:
        assert any("unrecognised report contract" in i for i in crf.check(text, PRINCIPLES))
        assert not _search(p, text), text[:40]
    assert not _search(p, HEADER_NOT_OK[2])


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH: the JavaScript half is not checked")
@pytest.mark.parametrize("path", HEADERS, ids=lambda p: p.split(os.sep)[-3])
def test_javascript_reads_the_header_grader_as_python_does(path):
    p = _pattern(path)
    for text in HEADER_OK + HEADER_NOT_OK:
        out = subprocess.run(
            ["node", "-e", "const [p,t]=process.argv.slice(1);process.stdout.write(String(new RegExp(p).test(t)))",
             p, text], capture_output=True, text=True).stdout
        assert (out == "true") == _search(p, text), text[:40]
