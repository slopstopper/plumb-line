---
type: regex
match: not_contains
target: last_message
pattern: '^\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|[ \t]*[*`]*[ \t]*[Vv][Ii][Oo][Ll][Aa][Tt][Ii][Oo][Nn][ \t]*[*`]*[ \t]*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|[ \t]*\r?$'
flags: m
arm: with-only
---

A clean fixture reaches zero confirmed violations: the report has no
findings-table row whose Status cell is `violation`. It is the `finds-*`
graders' Status reading, naming no file or principle, and inverted
(`match: not_contains`). A needs-review or advisory row passes, and so do
advisory adoption gaps (P7, P9) and a stub note held at needs-review, which
is what AUDIT-EXPECTATIONS.md allows on a clean fixture. The Status column is
contracted by report-format v4 (#530) and checked by
`scripts/check_report_format.py`; `scripts/test_eval_graders.py` holds this
pattern to the checker's spellings and to the delivered 2026-09-30 reports.

This replaces the runner's `llm` judge, which is out of scoring until it
records its reasoning and reproduces the mechanical verdicts on a
calibration set (#591, owner decision 2026-09-30). With-only: the no-plugin
arm has no Status column, so this grader cannot tell it anything.
