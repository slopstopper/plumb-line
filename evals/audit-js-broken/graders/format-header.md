---
type: regex
pattern: 'report-format: v3'
match: contains
target: last_message
---
The report must open with the v3 header block. Per AUDIT-EXPECTATIONS.md this
is a format FAIL scored independently of finding accuracy.
