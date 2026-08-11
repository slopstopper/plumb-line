#!/usr/bin/env python3
"""Validator for plumb-line's own report contracts (#139).

P7 (Contracted outputs) names three parts: a version constant, a canonical key
list, and a validator. `report-format` and `remediation-format` shipped the
first two and not the third — so "no format FAILs" in
docs/validation-results.md was a human judgement, repeated across six release
runs. This makes it mechanical.

Validates either contract, auto-detected from the first key line:

    report-format: v3        the plumb-line-audit report
    remediation-format: v1   the plumb-line-remediate record

Principle names are read from reference/portable-principles.md, never
hardcoded — a second copy of the ruleset in here would be exactly the drift
P9 warns about, and the hardcoded prior P5 forbids.

Pure stdlib. Run from the repo root:

    python3 scripts/check_report_format.py <report.md> [<more.md> ...]
    python3 scripts/check_report_format.py --self-test
"""
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PRINCIPLES_DOC = os.path.join(_ROOT, "reference", "portable-principles.md")

# Known-good contract versions. An unknown version is a FAIL, not a shrug: a
# report claiming v9 was produced by something this checker does not model.
KNOWN_REPORT_VERSIONS = {"v1", "v2", "v3"}
KNOWN_REMEDIATION_VERSIONS = {"v1"}

REPORT_HEADER_KEYS = ["report-format", "scope", "principles-revision", "date", "commit"]
REMEDIATION_HEADER_KEYS = ["remediation-format", "source-report", "source-report-format",
                           "principles-revision", "date", "commit"]

FINDINGS_COLUMNS = ["Path", "Line", "Function", "Issue", "Suggested Fix", "Principle"]
RECORD_COLUMNS = ["Finding", "Path", "Class", "Action", "Change summary"]

ACTIONS = {"applied-mechanical", "applied-judgment", "applied-conservative",
           "proposed", "blocked", "skipped"}

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
_WORKING_TREE = "working tree (uncommitted)"
# Principle citations are found by code alone; the name is then checked as a
# PREFIX of what follows (see _check_principles). Capturing the name with a
# regex instead means choosing an end delimiter, and every choice was wrong for
# some legal case: the glossary packs several per line, and prose cites one
# mid-sentence. Prefix-matching the canonical name needs no delimiter at all.
_PRINCIPLE_CODE = re.compile(r"\bP([1-9])\b")


def load_principles(text):
    """{"P3": "Confidence + provenance", ...} from the ruleset's own headings."""
    out = {}
    for m in re.finditer(r"^##\s*Principle\s+([1-9])\s+—\s+(.+?)\s*$", text, re.M):
        out["P" + m.group(1)] = m.group(2)
    return out


def _header_lines(text):
    """Leading `key: value` lines, stopping at the first blank or non-key line."""
    pairs = []
    for line in text.split("\n"):
        if not line.strip():
            break
        m = re.match(r"^([a-z][a-z-]*):\s*(.*)$", line)
        if not m:
            break
        pairs.append((m.group(1), m.group(2).strip()))
    return pairs


def detect_format(text):
    pairs = _header_lines(text)
    if not pairs:
        return None
    key = pairs[0][0]
    if key == "report-format":
        return "report"
    if key == "remediation-format":
        return "remediation"
    return None


def _check_header(pairs, required, version_key, known_versions, issues):
    present = [k for k, _ in pairs]
    values = dict(pairs)

    for key in required:
        if key not in present:
            issues.append(f"missing required header key: {key}")

    # Order matters: a stored report is meant to be diffable across runs.
    ordered = [k for k in present if k in required]
    if ordered != [k for k in required if k in present]:
        issues.append(f"header keys out of order: expected {required}, got {ordered}")

    version = values.get(version_key, "")
    if version and version not in known_versions:
        issues.append(
            f"unknown {version_key} version: {version!r} "
            f"(this checker models {sorted(known_versions)})")

    if "date" in values and not _DATE.match(values["date"]):
        issues.append(f"date must be YYYY-MM-DD, got {values['date']!r}")

    if "principles-revision" in values and not values["principles-revision"].isdigit():
        issues.append(
            f"principles-revision must be an integer, got {values['principles-revision']!r}")

    commit = values.get("commit")
    if commit is not None and commit != _WORKING_TREE and not _COMMIT.match(commit):
        issues.append(
            f"commit must be a git SHA or {_WORKING_TREE!r}, got {commit!r}")

    return values


def _table_columns(text, expected):
    """Find a markdown table whose header row is exactly `expected`. Returns
    (found_columns_or_None, rows) — rows are the body cell-lists."""
    want = "| " + " | ".join(expected) + " |"
    lines = text.split("\n")
    best = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set(cells) <= {"", "----", "-" * len(cells[0] or "-")} or all(
                set(c) <= {"-", " "} for c in cells):
            continue  # separator row
        if stripped == want:
            rows = []
            for body in lines[i + 2:]:
                b = body.strip()
                if not (b.startswith("|") and b.endswith("|")):
                    break
                rows.append([c.strip() for c in b.strip("|").split("|")])
            return cells, rows
        if best is None and len(cells) >= 3:
            best = cells
    return best, []


def _check_principles(text, principles, glossary_required, issues):
    """Every P# citation must be inline-named with the ruleset's own wording.

    The canonical name is matched as a PREFIX of what follows the em-dash, not
    as the whole remainder. The format explicitly allows a citation mid-sentence
    ("this run leaned on P3 — Confidence + provenance throughout"), and the
    glossary packs several per line — so comparing against everything up to the
    line end rejects the format's own documented usage. A false positive in a
    format checker is the fastest way to get the checker disabled.
    """
    cited, seen = set(), set()

    def add(issue):
        if issue not in seen:      # one citation repeated N times is one problem
            seen.add(issue)
            issues.append(issue)

    for m in re.finditer(r"\bP([1-9])\b", text):
        code = "P" + m.group(1)
        cited.add(code)
        rest = text[m.end():]
        dash = re.match(r"[ \t]*—[ \t]*", rest)
        if not dash:
            add(f"{code} is not inline-named (bare code); "
                f"render it as '{code} — {principles.get(code, '<name>')}'")
            continue
        after = rest[dash.end():]
        canonical = principles.get(code)
        if canonical and after.startswith(canonical):
            continue
        snippet = re.split(r"\s{2,}|[|)\n]", after)[0].strip()
        add(f"{code} has the wrong name: {snippet!r}, "
            f"ruleset says {canonical!r}")

    if glossary_required:
        glossary = _glossary_codes(text)
        for code in sorted(cited):
            if code not in glossary:
                add(f"{code} is cited but not in the glossary")
    return cited


def _glossary_codes(text):
    """Codes defined in the glossary block: the inline-named lines that appear
    before the findings table."""
    head = text.split("| Path |")[0]
    head = "\n".join(ln for ln in head.split("\n") if not re.match(r"^[a-z][a-z-]*:", ln))
    return {"P" + m.group(1) for m in re.finditer(r"\bP([1-9])\b", head)}


def check_report(text, principles):
    issues = []
    _check_header(_header_lines(text), REPORT_HEADER_KEYS, "report-format",
                  KNOWN_REPORT_VERSIONS, issues)

    cols, _rows = _table_columns(text, FINDINGS_COLUMNS)
    if cols != FINDINGS_COLUMNS:
        if "No findings." not in text:
            issues.append(
                f"findings table columns must be exactly {FINDINGS_COLUMNS}; "
                f"found {cols} (a clean run instead states 'No findings.')")

    _check_principles(text, principles, glossary_required=True, issues=issues)

    if not re.search(r"^coverage:\s*\S", text, re.M):
        issues.append("missing the coverage map — the audit's honest denominator "
                      "(REQUIRED on every run, including clean ones)")
    if not re.search(r"^scope note:\s*\S", text, re.M):
        issues.append("missing the 'scope note:' no-completeness caveat")
    return issues


def check_remediation(text, principles):
    issues = []
    _check_header(_header_lines(text), REMEDIATION_HEADER_KEYS, "remediation-format",
                  KNOWN_REMEDIATION_VERSIONS, issues)

    cols, rows = _table_columns(text, RECORD_COLUMNS)
    if cols != RECORD_COLUMNS:
        issues.append(
            f"record table columns must be exactly {RECORD_COLUMNS}; found {cols}")
    else:
        action_at = RECORD_COLUMNS.index("Action")
        for row in rows:
            if len(row) > action_at and row[action_at] not in ACTIONS:
                issues.append(
                    f"unknown Action verb {row[action_at]!r}; "
                    f"must be one of {sorted(ACTIONS)}")

    _check_principles(text, principles, glossary_required=False, issues=issues)
    return issues


def check(text, principles):
    kind = detect_format(text)
    if kind == "report":
        return check_report(text, principles)
    if kind == "remediation":
        return check_remediation(text, principles)
    return ["unrecognised report contract: the first header key must be "
            "'report-format:' or 'remediation-format:'"]


def main(argv):
    if not argv:
        print(__doc__.strip().split("\n\n")[0])
        print("\nusage: python3 scripts/check_report_format.py <report.md> [...]")
        return 2

    with open(_PRINCIPLES_DOC, encoding="utf-8") as fh:
        principles = load_principles(fh.read())
    if not principles:
        print(f"✗ could not read principle names from {_PRINCIPLES_DOC}")
        return 1

    failed = 0
    for path in argv:
        with open(path, encoding="utf-8") as fh:
            issues = check(fh.read(), principles)
        if issues:
            failed += 1
            print(f"✗ {path}")
            for issue in issues:
                print(f"    {issue}")
        else:
            print(f"✓ {path}")

    if failed:
        print(f"\nFAIL: {failed} of {len(argv)} report(s) violate their own contract.")
        return 1
    print(f"\n✓ {len(argv)} report(s) conform.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
