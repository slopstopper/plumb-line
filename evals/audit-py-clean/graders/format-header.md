---
type: regex
pattern: 'report-format: v4'
match: contains
target: last_message
arm: with-only
---
The report must open with the v4 header block. Per AUDIT-EXPECTATIONS.md this
is a format FAIL scored independently of finding accuracy.
