---
type: regex
match: contains
target: last_message
pattern: '^\|(?:[^|\n\\]|\\.)*gateway\.js(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|\s*(?:\*\*)?\s*[Vv]iolation\b(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*\|(?:[^|\n\\]|\\.)*P3 — Confidence \+ provenance(?:[^|\n\\]|\\.)*\|'
flags: m
arm: with-only
---

A confirmed finding for this planted violation: a findings-table row whose
Path cell names the file, whose Issue cell opens with a "violation" status and
whose Principle cell carries the principle's inline name. A needs-review or
advisory row, an omission-pass cell or a coverage line does not match. The
status word is the skill's reporting convention, not a contracted field.
With-only: the no-plugin arm has no inline principle names to match.
