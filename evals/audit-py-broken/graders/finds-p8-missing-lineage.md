---
type: regex
match: contains
target: last_message
pattern: '^\|(?:[^|\n\\]|\\.)*source\.py(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|\s*[*`]*\s*[Vv][Ii][Oo][Ll][Aa][Tt][Ii][Oo][Nn]\s*[*`]*\s*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*P8 — State-first lineage(?:[^|\n\\]|\\.)*\|'
flags: m
arm: with-only
---

A confirmed finding for this planted violation: a findings-table row whose
Path cell names the file, whose Status cell is `violation` and whose Principle
cell carries the principle's inline name. A needs-review or advisory row, an
omission-pass cell or a coverage line does not match. The Status column is
contracted by report-format v4 (#530) and checked by
`scripts/check_report_format.py`.
With-only: the no-plugin arm has no inline principle names to match.
