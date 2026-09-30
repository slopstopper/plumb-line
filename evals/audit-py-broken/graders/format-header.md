---
type: regex
pattern: '^\s*(?:```[a-z]*\s*)?report-format: v4\b'
match: contains
target: last_message
arm: with-only
---
The report must open with the v4 header block: no title, heading or prose
above it, as the audit skill says and scripts/check_report_format.py checks
(which also skips leading blank lines and a leading code fence). No `m` flag,
so `^` is the start of the message. Until the 2026-09-30 run this grader
matched the header anywhere, and passed two reports that opened with a prose
summary. Per AUDIT-EXPECTATIONS.md this is a format FAIL scored independently
of finding accuracy.
