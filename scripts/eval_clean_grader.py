"""The readable source of the eval suite's clean-case grader pattern (#591).

`evals/audit-{js,py}-clean/graders/no-confirmed-violations.md` must hold its
pattern as one regex string in YAML front matter, with no comments, so the
pattern is built here from named parts and written into both files. Edit the
parts below, never the one-liner; `scripts/test_eval_graders.py` fails if a
grader file differs from `pattern()`.

What it matches: a findings-table row, read as scripts/check_report_format.py
reads one, whose Status is anything but needs-review or advisory. The grader
is `match: not_contains`, so one such row fails the clean case (fail closed).

    python3 scripts/eval_clean_grader.py          # print the pattern
    python3 scripts/eval_clean_grader.py --write  # write it into both graders
"""
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADERS = [os.path.join(_ROOT, "evals", case, "graders", "no-confirmed-violations.md")
           for case in ("audit-js-clean", "audit-py-clean")]

# Whitespace on one line: any Unicode whitespace except a newline, and not a
# BOM (JavaScript's \s counts a BOM, Python's does not; excluding it keeps the
# two engines agreeing).
WS = r"[^\S\n\ufeff]*"

# One cell: any character but a pipe or a newline, where an escaped `\|` is
# cell text. The checker splits a row on pipes not preceded by a backslash.
CELL = r"(?:[^|\n]|(?<=\\)\|)*"

# The pipe that ends a cell: one not preceded by a backslash.
SEP = r"(?<!\\)\|"


def _any_case(word):
    """The word in any letter case, spelled out: the runner documents only the
    `i` flag, and this grader already needs `m`."""
    assert re.fullmatch(r"[a-z-]+", word), word   # letters and hyphens only: no escaping needed
    return "".join(f"[{c.upper()}{c.lower()}]" if c.isalpha() else c for c in word)


# A Status cell the checker accepts as NOT a violation: needs-review or
# advisory, any case, inside any `*` or backtick decoration, padded with
# whitespace, filling the whole cell. The checker reads the cell as
# `.strip().strip("*`").strip().lower()`.
ACCEPTED_STATUS = (rf"{WS}[*`]*{WS}(?:{_any_case('needs-review')}|{_any_case('advisory')})"
                   rf"{WS}[*`]*{WS}{SEP}")

# How a findings row is told from an omission-pass row (both have seven
# cells): the Principle cell opens with a principle code, P1-P9 or spine in
# any case, optionally after `*`, a backtick or `(`, then a dash of any kind.
# Known residual (pinned in the tests): a Principle cell that opens any other
# way is not seen.
PRINCIPLE_START = rf"{WS}[*`(]*{WS}(?:P[1-9]|{_any_case('spine')})[*`]*{WS}[—–-]"


def pattern():
    """Path | Line | Function | Status | Issue | Suggested Fix | Principle."""
    return (
        rf"^{WS}\|+"                              # the row starts: one or more pipes
        + (CELL + SEP) * 3                        # Path, Line, Function
        + rf"(?!{ACCEPTED_STATUS})"               # Status: anything but an accepted non-violation
        + (CELL + SEP) * 3                        # Status, Issue, Suggested Fix
        + rf"(?={PRINCIPLE_START})"               # Principle: opens with a code
        + CELL + rf"\|+{WS}\r?$"                  # Principle, the closing pipe(s), end of line
    )


def _grader_pattern(path):
    return re.search(r"^pattern: '(.*)'$", open(path, encoding="utf-8").read(), re.M).group(1)


def write():
    p = pattern()
    assert "'" not in p, "the pattern must not contain a single quote (YAML single-quoted string)"
    for path in GRADERS:
        text = open(path, encoding="utf-8").read()
        old = re.search(r"^pattern: '.*'$", text, re.M).group(0)
        open(path, "w", encoding="utf-8").write(text.replace(old, f"pattern: '{p}'"))


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        write()
        print("wrote", ", ".join(os.path.relpath(g, _ROOT) for g in GRADERS))
    else:
        print(pattern())
