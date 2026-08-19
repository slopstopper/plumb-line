#!/usr/bin/env python3
"""Validator for plumb-line's own report contracts (#139).

P7 (Contracted outputs) names three parts: a version constant, a canonical key
list, and a validator. `report-format` and `remediation-format` shipped the
first two and not the third — so "no format FAILs" in
docs/validation-results.md was a human judgement, repeated across six release
runs. This makes it mechanical.

Validates any of the contracts, auto-detected from the first key line:

    report-format: v3        the plumb-line-audit report
    remediation-format: v1   the plumb-line-remediate record
    routing-format: v1       the plumb-line-adopt routing report (#269)

Principle names are read from reference/portable-principles.md, never
hardcoded — a second copy of the ruleset in here would be exactly the drift
P9 warns about, and the hardcoded prior P5 forbids.

Pure stdlib. Run from the repo root:

    python3 scripts/check_report_format.py <report.md> [<more.md> ...]

Exits 0 when every report conforms, 1 otherwise (including an unreadable path).
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
KNOWN_ROUTING_VERSIONS = {"v1"}

REPORT_HEADER_KEYS = ["report-format", "scope", "principles-revision", "date", "commit"]
REMEDIATION_HEADER_KEYS = ["remediation-format", "source-report", "source-report-format",
                           "principles-revision", "date", "commit"]
# The adopt skill's routing recommendation (#269): a deliberately LIGHT
# contract — header + five body elements — because the output is
# conversational prose around a routing decision, not a findings table.
ROUTING_HEADER_KEYS = ["routing-format", "scope", "date"]
# The verdict/citation separator accepts em-dash, en-dash, or hyphen: this
# project's prose leans on em-dashes, but an agent producing the report is a
# realistic source of any of the three, and the citation's presence is the
# load-bearing part (#309 review).
_ROUTING_FIT = re.compile(
    r"^fit:\s*(profile\s+[0-9]+|anti-profile|no fit|mixed|uncertain)\b.*[—–-]\s*cited",
    re.M | re.I)
_ROUTING_FIT_LINE = re.compile(r"^fit:", re.M | re.I)

FINDINGS_COLUMNS = ["Path", "Line", "Function", "Issue", "Suggested Fix", "Principle"]
RECORD_COLUMNS = ["Finding", "Path", "Class", "Action", "Change summary"]

ACTIONS = {"applied-mechanical", "applied-judgment", "applied-conservative",
           "proposed", "blocked", "skipped"}

# [0-9] not \d, and an explicit ASCII test rather than str.isdigit(): Python's
# \d matches any Unicode decimal digit and isdigit() is broader still (it is
# True for "²"), so both would accept a date of "٢٠٢٦-٠٨-١١" or a revision of
# "²" that int() cannot parse. Same class of bug as the Age-header fix in
# primitives/python/http.py — it recurs anywhere a "digit" is assumed ASCII.
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
_ASCII_INT = re.compile(r"^[0-9]+$")
_WORKING_TREE = "working tree (uncommitted)"
# Principle citations are found by code alone; the name is then checked as a
# PREFIX of what follows (see _check_principles). Capturing the name with a
# regex instead means choosing an end delimiter, and every choice was wrong for
# some legal case: the glossary packs several per line, and prose cites one
# mid-sentence. Prefix-matching the canonical name needs no delimiter at all.
#
# The code must stand alone: `\bP3\b` also matches inside `src/P3-loader.py`
# and `P3_STEP`, and an audit report is precisely the artifact that quotes repo
# paths and identifiers — so that fired on valid reports.
#
# The lookarounds exclude en/em dashes as well as ASCII "-", because "P1–P9" is
# a RANGE, not two bare citations, and this project's prose uses those dashes
# heavily. They do NOT exclude a trailing "." — "this violates P3." is exactly
# the bare citation the format forbids, and excluding "." created a hole in the
# rule at its most common prose position.
_PRINCIPLE_CODE = re.compile(r"(?<![\w/–—-])P([1-9])(?![\w/–—-])")

# Inline code spans are masked before scanning: a path in backticks is a
# quotation, not a citation, and must not be read as either.
_CODE_SPAN = re.compile(r"`[^`\n]*`")
_FENCE = re.compile(r"^\s*(?:```+|~~~+)\s*[A-Za-z0-9_-]*\s*$")
_HEADER_START = re.compile(r"^(?:report|remediation|routing)-format:", re.M)


def _mask_code_spans(text):
    """Replace inline `code` spans with same-length blanks, preserving offsets
    and line structure so reported positions and prefix matches stay accurate."""
    return _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), text)


def load_principles(text):
    """{"P3": "Confidence + provenance", ...} from the ruleset's own headings."""
    out = {}
    for m in re.finditer(r"^##\s*Principle\s+([1-9])\s+—\s+(.+?)\s*$", text, re.M):
        out["P" + m.group(1)] = m.group(2)
    return out


def _header_lines(text):
    """The header's `key: value` lines.

    Leading blank lines are skipped: a single stray newline before the header
    otherwise turned a conformant report into 'unrecognised report contract',
    and the harness runs this on every report before tagging.

    A leading code fence is skipped for the same reason. Both skills print the
    header template inside a ``` fence, so an agent copying the template
    literally produces a fenced header — which failed with a message that never
    mentioned fencing. Seen for real in the v0.8.0 harness.
    """
    pairs = []
    started = False
    for line in text.split("\n"):
        if not line.strip():
            if not started:
                continue          # leading blank — not yet in the header
            break                 # blank after the header ends it
        if _FENCE.match(line):
            if not started:
                continue          # opening fence around the header block
            break                 # closing fence ends it
        m = re.match(r"^([a-z][a-z-]*):[ \t]*(.*)$", line)
        if not m:
            break
        started = True
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
    if key == "routing-format":
        return "routing"
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

    if version_key in values:
        version = values[version_key]
        # An EMPTY value is a failure, not a default. The version constant is the
        # first of P7's three parts; silently treating a bare "report-format:" as
        # current is the checker inventing the very thing it exists to verify.
        if not version:
            issues.append(f"{version_key} has no value; it must state a version "
                          f"(one of {sorted(known_versions)})")
        elif version not in known_versions:
            issues.append(
                f"unknown {version_key} version: {version!r} "
                f"(this checker models {sorted(known_versions)})")

    if "date" in values and not _DATE.match(values["date"]):
        issues.append(f"date must be YYYY-MM-DD, got {values['date']!r}")

    if "principles-revision" in values and not _ASCII_INT.match(values["principles-revision"]):
        issues.append(
            f"principles-revision must be an integer, got {values['principles-revision']!r}")

    commit = values.get("commit")
    if commit is not None and commit != _WORKING_TREE and not _COMMIT.match(commit):
        issues.append(
            f"commit must be a git SHA or {_WORKING_TREE!r}, got {commit!r}")

    return values


def _split_row(line):
    """Split a markdown row on UNESCAPED pipes.

    `\\|` is the legal way to put a literal pipe in a cell — a Change summary
    quoting a shell pipeline, for instance. Splitting naively invented an extra
    cell and reported a fabricated 'shifted row' failure.
    """
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def _is_separator(cells):
    return bool(cells) and all(set(c) <= {"-", ":", " "} and c for c in cells)


def _table_columns(text, expected):
    """Find the markdown table whose header cells are exactly `expected`.

    Compares PARSED CELLS, never the raw line. Comparing raw text required
    single-space padding, so a column-aligned table — which is what a model
    emitting a report actually produces — never matched. It then fell through to
    the fallback and returned zero rows, silently disabling every per-row check
    (a remediation record with an aligned table and a bogus Action verb passed
    clean), while also reporting the WRONG table's columns on a report that
    legitimately contains more than one table.

    Returns (columns_of_the_matching_table_or_best_guess, body_rows).
    """
    lines = text.split("\n")
    best = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = _split_row(stripped)
        if _is_separator(cells):
            continue
        if cells == expected:
            rows, j = [], i + 1
            if j < len(lines) and _is_separator(_split_row(lines[j])):
                j += 1                      # skip the separator, if present
            for body in lines[j:]:
                b = body.strip()
                if not (b.startswith("|") and b.endswith("|")):
                    break
                rows.append(_split_row(b))
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
    text = _mask_code_spans(text)

    def add(issue):
        if issue not in seen:      # one citation repeated N times is one problem
            seen.add(issue)
            issues.append(issue)

    for m in _PRINCIPLE_CODE.finditer(text):
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
    masked = _mask_code_spans(text)
    lines = masked.split("\n")

    # The glossary is what sits between the header and the FIRST table. Locating
    # that table by the literal string "| Path |" required single-space padding,
    # so an aligned table put the whole document in `head` — the cited set then
    # equalled the glossary set and this check could never fire. That is the
    # same aligned-table bug fixed in _table_columns, left behind one function
    # below it. Find the first table row structurally instead.
    end = len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and len(_split_row(s)) >= 2:
            end = i
            break
        if s == "No findings.":
            end = i
            break

    head = "\n".join(ln for ln in lines[:end]
                     if not re.match(r"^[a-z][a-z-]*:", ln))
    return {"P" + m.group(1) for m in _PRINCIPLE_CODE.finditer(head)}


def check_report(text, principles):
    issues = []
    values = _check_header(_header_lines(text), REPORT_HEADER_KEYS, "report-format",
                           KNOWN_REPORT_VERSIONS, issues)

    # A BOOTSTRAP report shares the v3 header block and nothing else — the
    # glossary, findings table and coverage map are audit-specific
    # (skills/plumb-line-bootstrap/SKILL.md, "Step 5 — Report"). It is
    # identified by the `adapter:` key the bootstrap header adds. Without this
    # branch the checker emitted three FAILs on a perfectly conformant bootstrap
    # report — and the harness tells the operator to run it on every report, so
    # that would have blocked a release on a false failure.
    if "adapter" in values:
        _check_principles(text, principles, glossary_required=False, issues=issues)
        return issues

    # The contract grew: the glossary and canonical findings table arrived in
    # v2, the coverage map in v3 (docs/validation-results.md). Applying v3 rules
    # to a stored v1 report would fail it for lacking parts its own contract
    # never had — the checker must model the version it is reading.
    version = values.get("report-format", "v3")
    level = int(version[1:]) if re.match(r"^v[0-9]+$", version) else 3

    if level >= 2:
        cols, rows = _table_columns(text, FINDINGS_COLUMNS)
        if cols != FINDINGS_COLUMNS:
            # 'No findings.' stands IN PLACE OF the table. Accepting the phrase
            # anywhere in the document meant a prose sentence containing it
            # excused a genuinely malformed table, so require that no candidate
            # findings table is present at all.
            clean_run = re.search(r"^No findings\.\s*$", text, re.M) and cols is None
            if not clean_run:
                issues.append(
                    f"findings table columns must be exactly {FINDINGS_COLUMNS}; "
                    f"found {cols} (a clean run instead states 'No findings.' "
                    f"on its own line, with no findings table)")
        else:
            # Same reasoning as the record table: a shifted row moves the
            # Principle cell, and the Principle is the whole point of the row.
            for n, row in enumerate(rows, start=1):
                if len(row) != len(FINDINGS_COLUMNS):
                    issues.append(
                        f"findings row {n} has {len(row)} cells, expected "
                        f"{len(FINDINGS_COLUMNS)} — a shifted row loses its Principle")

    _check_principles(text, principles, glossary_required=level >= 2, issues=issues)

    if level >= 3:
        if not re.search(r"^coverage:[ \t]*\S", text, re.M):
            issues.append("missing the coverage map — the audit's honest denominator "
                          "(REQUIRED on every run, including clean ones)")
        if not re.search(r"^scope note:[ \t]*\S", text, re.M):
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
        for n, row in enumerate(rows, start=1):
            # A row with the wrong cell count is not "skip it" — a stray or
            # missing pipe shifts every later cell, so Action would be read from
            # the Class column and the record would misdescribe what was done.
            if len(row) != len(RECORD_COLUMNS):
                issues.append(
                    f"record row {n} has {len(row)} cells, expected "
                    f"{len(RECORD_COLUMNS)} — a shifted row misreports its Action")
                continue
            # SKILL.md names the vocabulary as `applied-mechanical` and its
            # table template carries no example row, so records arrive with the
            # verb in an inline-code span. That is the documented rendering, not
            # a wrong verb — strip the markers before matching rather than
            # failing a record whose Action is correct.
            verb = row[action_at].strip().strip("`").strip()
            if verb not in ACTIONS:
                issues.append(
                    f"unknown Action verb {verb!r}; "
                    f"must be one of {sorted(ACTIONS)}")

    _check_principles(text, principles, glossary_required=False, issues=issues)
    return issues


def check_routing(text, principles):
    """routing-format v1 (#269): the adopt skill's contracted output. Light by
    design — the report is conversational routing prose, so the contract pins
    the five elements the skill already requires rather than a table shape:
    the header, a denominator line, both surface sections, a fit verdict from
    the vocabulary with cited evidence, and a handoff line. `principles` is
    accepted for dispatch symmetry and deliberately unused: routing prose is
    not held to the inline-naming rule the audit/remediation formats enforce
    (part of the same light-by-design decision)."""
    issues = []
    pairs = _header_lines(text)
    _check_header(pairs, ROUTING_HEADER_KEYS, "routing-format",
                  KNOWN_ROUTING_VERSIONS, issues)

    body = _mask_code_spans(text)
    if not re.search(r"^denominator:\s*\S", body, re.M | re.I):
        issues.append("missing 'denominator:' line — the scan's coverage claim "
                      "(what was scanned, what was not) is required")
    for section in ("Skills surface", "Primitives surface"):
        if not re.search(rf"^#+\s.*{re.escape(section)}", body, re.M | re.I):
            issues.append(f"missing '{section}' section — the routing answer "
                          f"covers both surfaces, always")
    if not _ROUTING_FIT_LINE.search(body):
        issues.append("missing 'fit:' line — the primitives verdict must be "
                      "stated (profile N / anti-profile / no fit / mixed / "
                      "uncertain) with cited evidence")
    elif not _ROUTING_FIT.search(body):
        issues.append("fit: line must name a verdict from the vocabulary "
                      "(profile N / anti-profile / no fit / mixed / uncertain) "
                      "followed by '— cited: <what was seen>'")
    if not re.search(r"^handoff:\s*\S", body, re.M | re.I):
        issues.append("missing 'handoff:' line — the one offered next step, or "
                      "'none (<reason>)' when declined or no builder is present")
    return issues


def check(text, principles):
    kind = detect_format(text)
    if kind in ("report", "remediation", "routing"):
        # Exactly one header block, or the checker cannot say which one it
        # validated. Fence tolerance made `_header_lines` take the FIRST header
        # it found, so a document quoting the template in a fence and then
        # carrying its own malformed header validated clean — the quoted block
        # shadowed the real one and a loud failure became a silent pass on the
        # release gate. Both skills print the template in a fence, so "quote the
        # format, then emit the report" is the shape agents actually produce.
        starts = _HEADER_START.findall(text)
        issues = []
        if len(starts) > 1:
            issues.append(
                f"ambiguous report: {len(starts)} header lines "
                f"('report-format:'/'remediation-format:'/'routing-format:') — "
                f"a report carries exactly one header block, and the checker "
                f"cannot tell which one it is validating")
        checker = {"report": check_report, "remediation": check_remediation,
                   "routing": check_routing}[kind]
        return issues + checker(text, principles)
    return ["unrecognised report contract: the first header key must be "
            "'report-format:', 'remediation-format:' or 'routing-format:' — "
            "check for a title line, prose, or an unclosed code fence above "
            "the header block"]


def main(argv):
    if not argv:
        print(__doc__.strip().split("\n\n")[0])
        print("\nusage: python3 scripts/check_report_format.py <report.md> [...]")
        return 2

    # Trapped for the same reason report paths are: a checkout without
    # reference/ (a plugin-bundled or partial copy) should get a FAIL line, not
    # a traceback. The docstring promises exit 1 on an unreadable path.
    try:
        with open(_PRINCIPLES_DOC, encoding="utf-8") as fh:
            principles = load_principles(fh.read())
    except OSError as exc:
        print(f"✗ cannot read {_PRINCIPLES_DOC}: {exc.strerror}")
        return 1
    if not principles:
        print(f"✗ could not read principle names from {_PRINCIPLES_DOC}")
        return 1

    failed = 0
    for path in argv:
        # An unreadable path is a FAIL line, not a traceback: this runs from the
        # release harness, where a mistyped filename should read like every
        # other failure rather than a stack trace.
        try:
            with open(path, encoding="utf-8") as fh:
                issues = check(fh.read(), principles)
        except OSError as exc:
            failed += 1
            print(f"✗ {path}\n    cannot read: {exc.strerror}")
            continue
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
