---
type: regex
match: not_contains
target: last_message
pattern: '^[^\S\n\ufeff]*\|+(?:[^|\n]|(?<=\\)\|)*(?<!\\)\|(?:[^|\n]|(?<=\\)\|)*(?<!\\)\|(?:[^|\n]|(?<=\\)\|)*(?<!\\)\|(?![^\S\n\ufeff]*[*`]*[^\S\n\ufeff]*(?:[Nn][Ee][Ee][Dd][Ss]-[Rr][Ee][Vv][Ii][Ee][Ww]|[Aa][Dd][Vv][Ii][Ss][Oo][Rr][Yy])[^\S\n\ufeff]*[*`]*[^\S\n\ufeff]*(?<!\\)\|)(?:[^|\n]|(?<=\\)\|)*(?<!\\)\|(?:[^|\n]|(?<=\\)\|)*(?<!\\)\|(?:[^|\n]|(?<=\\)\|)*(?<!\\)\|(?=[^\S\n\ufeff]*[*`(]*[^\S\n\ufeff]*(?:P[1-9]|[Ss][Pp][Ii][Nn][Ee])[*`]*[^\S\n\ufeff]*[—–-])(?:[^|\n]|(?<=\\)\|)*\|+[^\S\n\ufeff]*\r?$'
flags: m
arm: with-only
---

The pattern is built by `scripts/eval_clean_grader.py`, which spells out
each part with a comment: edit it there and run it with `--write`, never
here. A clean fixture reaches zero confirmed violations. The grader is inverted
(`match: not_contains`), so a row it failed to see would pass the case: it
fails closed. It matches any findings row whose Status is anything but
`needs-review` or `advisory`, so a `violation`, and any status the checker
would refuse (`confirmed`, `violation (P3)`, an empty cell), fails the case.
It reads a findings row as `scripts/check_report_format.py` does: a line that
starts and ends with `|` after whitespace (indented rows, and doubled edge
pipes, included), split on pipes not preceded by a backslash into seven
cells, with the Status word read case-insensitively inside any `*` or
backtick decoration and any whitespace (a BOM is not whitespace, in either
regex engine).
A needs-review or advisory row passes, and so do advisory adoption gaps (P7,
P9) and a stub note held at needs-review, which is what AUDIT-EXPECTATIONS.md
allows on a clean fixture.

It tells a findings row from the omission-pass table's rows, which also have
seven cells, by the Principle cell opening with a principle code: `P1` to
`P9` or `spine` (any case), optionally inside `*`, backticks or a
parenthesis, then a dash of any kind. Two known residuals, both pinned by
tests. A findings row whose Principle cell does not open, after whitespace,
`*`, backticks or `(`, with a code is not seen: an empty cell, a name with
no code, `_P3 — …_`, `[P3 — …]`, curly quotes, or text before the code. That
is a false PASS, since the checker does not validate that cell. And an omission-pass row whose last cell opens with a
principle code fails the case: a false FAIL, on the safe side. Every
findings row in the committed 2026-09-30 reports opens with a code;
`scripts/test_eval_graders.py` pins that, holds the pattern to the
checker's spellings, and flips every row of those reports to `violation`
to show each one is caught.

This replaces the runner's `llm` judge, which is out of scoring until it
records its reasoning and reproduces the mechanical verdicts on a
calibration set (#591, owner decision 2026-09-30). With-only: it reads the
plugin's v4 findings table.
