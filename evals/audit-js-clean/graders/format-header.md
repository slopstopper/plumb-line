---
type: regex
pattern: '^(?:[ \t ]*(?:(?:```+|~~~+)[ \t]*[A-Za-z0-9_-]*[ \t]*)?\r?\n)*report-format:[ \t]*v4[ \t]*\r?(?:\n|$)'
match: contains
target: last_message
arm: with-only
---
The report must open with the v4 header block: no title, heading or prose
above it, as the audit skill says and scripts/check_report_format.py checks
(which also skips leading blank lines and fence lines, and allows spaces
or a tab after the colon). No `m` flag, so `^` is the start of the message.
`scripts/test_eval_graders.py` holds it to the checker on 27 openings. Until the 2026-09-30 run this grader
matched the header anywhere, and passed two reports that opened with a prose
summary. Per AUDIT-EXPECTATIONS.md this is a format FAIL scored independently
of finding accuracy.
