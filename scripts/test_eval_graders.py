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
import json
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
#
# The grader must say what the checker says about where the header is: the
# message opens with a `report-format: v4` header, after nothing but blank or
# fence lines. The openings are the #530 review's probes.

HEADERS = sorted(glob.glob(os.path.join(_ROOT, "evals", "*", "graders", "format-header.md")))
_V4 = _REPORT.replace("STATUS", "violation")
OPENINGS = {
    "as is": _V4,
    "leading blank lines": "\n\n\n" + _V4,
    "a spaces-only line first": "   \n" + _V4,
    "``` fence": "```\n" + _V4,
    "```text fence": "```text\n" + _V4,
    "```Text fence": "```Text\n" + _V4,
    "```yaml-x fence": "```yaml-x\n" + _V4,
    "```md5 fence": "```md5\n" + _V4,
    "~~~ fence": "~~~\n" + _V4,
    "four-backtick fence": "````\n" + _V4,
    "indented fence": "  ```\n" + _V4,
    "two fence lines": "```\n```text\n" + _V4,
    "blank, fence, blank": "\n```\n\n" + _V4,
    "CRLF": _V4.replace("\n", "\r\n"),
    "BOM": "\ufeff" + _V4,
    "indented header": "  " + _V4,
    "no space after the colon": _V4.replace("report-format: v4", "report-format:v4", 1),
    "two spaces after the colon": _V4.replace("report-format: v4", "report-format:  v4", 1),
    "a tab after the colon": _V4.replace("report-format: v4", "report-format:\tv4", 1),
    "v4. suffix": _V4.replace("report-format: v4", "report-format: v4.", 1),
    "v41": _V4.replace("report-format: v4", "report-format: v41", 1),
    "prose first": "Summary line.\n\n" + _V4,
    "heading first": "# Audit\n\n" + _V4,
    "header in a later fence": "Intro\n\n```\n" + _V4,
    "fence, prose, header": "```\nnote\n" + _V4,
    "v3 header": _V4.replace("report-format: v4", "report-format: v3", 1),
    "a non-breaking-space line first": "\u00a0\n" + _V4,
}


def _checker_header_is_v4(text):
    """The checker recognises a report contract here, and it is v4."""
    if any("unrecognised report contract" in i for i in crf.check(text, PRINCIPLES)):
        return False
    return dict(crf._header_lines(text)).get("report-format") == "v4"


def _search(pattern, text):
    return re.search(pattern, text) is not None  # no multiline flag, as in the grader


def test_four_header_graders_share_one_pattern():
    assert len(HEADERS) == 4, HEADERS
    assert len({_pattern(p) for p in HEADERS}) == 1


@pytest.mark.parametrize("name", sorted(OPENINGS))
def test_the_header_grader_agrees_with_the_checker(name):
    text = OPENINGS[name]
    assert _search(_pattern(HEADERS[0]), text) == _checker_header_is_v4(text), name


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH: the JavaScript half is not checked")
def test_javascript_reads_the_header_grader_as_python_does():
    p = _pattern(HEADERS[0])
    src = ("let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const a=JSON.parse(d);"
           "process.stdout.write(JSON.stringify(a.t.map(t=>new RegExp(a.p).test(t))))})")
    names = sorted(OPENINGS)
    out = subprocess.run(["node", "-e", src], input=json.dumps({"p": p, "t": [OPENINGS[n] for n in names]}),
                         capture_output=True, text=True, check=True).stdout
    for name, js in zip(names, json.loads(out)):
        assert js == _search(p, OPENINGS[name]), name


# --- no-confirmed-violations: the clean cases' mechanical grader (#591) ------
#
# The runner's llm judge is out of scoring until it records its reasoning and
# passes a calibration set (#591, owner decision 2026-09-30). The clean cases'
# grader is inverted (`match: not_contains`), so a row it fails to see would
# PASS the case: it must fail closed (#591 review). It matches any findings
# row, read as the checker reads one (a line that starts and ends with `|`
# after whitespace, split on unescaped pipes into seven cells, its Principle
# cell opening with a code), whose Status is anything but `needs-review` or
# `advisory` in a spelling the checker accepts. Known residual: a findings row
# whose Principle cell does not open with a code is not seen; every findings
# row in the committed reports opens with one (pinned below).

CLEAN = sorted(glob.glob(os.path.join(_ROOT, "evals", "*-clean", "graders", "no-confirmed-violations.md")))
_DELIVERED = sorted(glob.glob(os.path.join(_ROOT, "docs", "records", "evals", "2026-09-30", "*-with-*.md")))
_OK = ["needs-review", "advisory", "Needs-Review", "ADVISORY", "**needs-review**", "`advisory`",
       "*needs-review*", "**`advisory`**", " advisory ", "needs-review\u00a0"]
_NOT_OK = CONFIRMED + ["confirmed", "violation (P3)", "violation:", "violation ✓", "", "needs review",
                       "advisory.", "tbd", "\u2003violation", "violation\u00a0"]


def _front(path):
    text = open(path, encoding="utf-8").read()
    return dict(re.findall(r"^(\w+): (.*)$", text.split("---")[1], re.M))


def _clean_row(status, principle="P3 — Confidence + provenance", indent="", issue="an issue"):
    return f"{indent}| `src/foo.py` | 42 | `f` | {status} | {issue} | a fix | {principle} |"


def _statuses_the_checker_accepts(status):
    issues = crf.check_report(_REPORT.replace("STATUS", status), PRINCIPLES)
    return not [i for i in issues if "Status" in i]


def test_two_clean_graders_share_one_pattern_and_invert_it():
    assert len(CLEAN) == 2, CLEAN
    assert len({_pattern(p) for p in CLEAN}) == 1
    for p in CLEAN:
        front = _front(p)
        assert (front["type"], front["match"], front["flags"], front["arm"], front["target"]) == \
            ("regex", "not_contains", "m", "with-only", "last_message"), front


def test_no_llm_judge_grader_is_scored():
    judged = [p for p in glob.glob(os.path.join(_ROOT, "evals", "*", "graders", "*.md"))
              if _front(p).get("type") == "llm"]
    assert judged == []


@pytest.mark.parametrize("status", _OK)
def test_a_needs_review_or_advisory_row_passes(status):
    assert _statuses_the_checker_accepts(status), status
    assert not _matches(_pattern(CLEAN[0]), "text\n" + _clean_row(status) + "\nmore\n"), status


@pytest.mark.parametrize("status", _NOT_OK)
def test_any_other_status_fails_the_case(status):
    # Fail closed: a violation, and any status the checker would refuse, both
    # fail. The checker does not run inside the suite, so a status it would
    # reject must not pass here either.
    assert _matches(_pattern(CLEAN[0]), "text\n" + _clean_row(status) + "\nmore\n"), status


@pytest.mark.parametrize("row", [
    _clean_row("violation", indent="  "),                    # indented, as the checker strips
    _clean_row("violation", indent="\t"),
    _clean_row("violation", issue="C:\\\\|x"),               # `\\|` inside a cell: not a split
    _clean_row("violation", issue="a \\| b"),                # an escaped pipe: not a split
    _clean_row("violation", principle="`P3 — Confidence + provenance`"),
    _clean_row("violation", principle="spine — null-result expressibility"),
    _clean_row("violation") + "\r",                          # CRLF
])
def test_the_review_probes_are_caught(row):
    assert _matches(_pattern(CLEAN[0]), "text\n" + row + "\nmore\n"), row


@pytest.mark.parametrize("line", [
    "| Path | Line | Function | Status | Issue | Suggested Fix | Principle |",
    "| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |",
    "| `f` | yes | NO — violation (P3 — Confidence + provenance) | no | no | yes | no |",
    "| Output | Provenance | Confidence | Lineage | Contract | Null-expressible | Baseline |",
    "| `src/foo.py` | 42 | `f` | violation: an issue | a fix | P3 — Confidence + provenance |",   # v3, six cells
    "coverage: 1/1 files read | violation | x",
])
def test_no_non_findings_line_fails_the_case(line):
    assert not _matches(_pattern(CLEAN[0]), "text\n" + line + "\nmore\n"), line


def test_the_delivered_clean_reports_pass_it():
    # The with-plugin clean reports the 2026-09-30 run delivered: 0 violations
    # each, by their own summary line.
    assert len(_DELIVERED) == 6, _DELIVERED
    for path in _DELIVERED:
        text = open(path, encoding="utf-8").read()
        assert re.search(r"\b0 violations\b", text), path
        assert not _matches(_pattern(CLEAN[0]), text), path


def test_every_committed_findings_row_opens_its_principle_with_a_code():
    # The known residual (a row whose Principle cell does not open with a code
    # is not seen) does not occur in the reports this suite is held to.
    for path in _DELIVERED:
        cols, rows = crf._table_columns(open(path, encoding="utf-8").read(), crf.FINDINGS_COLUMNS)
        assert cols == crf.FINDINGS_COLUMNS, path
        for row in rows:
            assert re.match(r"^[*`]*\s*(P[1-9]|spine)\s*—", row[6].strip()), (path, row[6])


def test_flipping_any_row_of_a_delivered_report_to_violation_fails_it():
    # The positive direction on real reports: every findings row, flipped from
    # its needs-review or advisory status to violation, is caught.
    flips = 0
    for path in _DELIVERED:
        text = open(path, encoding="utf-8").read()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            cells = line.split("|")
            if len(cells) == 9 and cells[4].strip().strip("*`").strip().lower() in ("needs-review", "advisory"):
                flipped = lines[:i] + ["|".join(cells[:4] + [" violation "] + cells[5:])] + lines[i + 1:]
                assert _matches(_pattern(CLEAN[0]), "\n".join(flipped)), (path, line)
                flips += 1
    assert flips >= 20, flips


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH: the JavaScript half is not checked")
def test_javascript_reads_the_clean_grader_as_python_does():
    p = _pattern(CLEAN[0])
    texts = ["text\n" + _clean_row(s) + "\nmore\n" for s in _OK + _NOT_OK]
    texts += [open(path, encoding="utf-8").read() for path in _DELIVERED]
    src = ("let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const a=JSON.parse(d);"
           "process.stdout.write(JSON.stringify(a.t.map(t=>new RegExp(a.p,'m').test(t))))})")
    out = subprocess.run(["node", "-e", src], input=json.dumps({"p": p, "t": texts}),
                         capture_output=True, text=True, check=True).stdout
    for text, js in zip(texts, json.loads(out)):
        assert js == _matches(p, text), text[:80]
