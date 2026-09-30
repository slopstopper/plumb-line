# 2026-08-18 — off-cycle blind validation (v0.9.0 skill as shipped)

First off-cycle run: not gating a release, but the first validation of the
audit skill *as shipped* (the v0.9.0 harness ran pre-tag). Motivated by the
standardized-evals workstream (#291); doubles as a baseline for the future
`claude plugin eval` suite (PR #292), whose scaffolds staged these fixtures.

Protocol per `examples/AUDIT-EXPECTATIONS.md`: fixtures staged by the #292
scaffold scripts (answer keys deleted, violation-naming lines stripped, strip
verified by grep before dispatch); six read-only auditors (one per clean
variant, two independent per broken variant), each reading only
`skills/plumb-line-audit/SKILL.md` + `reference/portable-principles.md` and
the staged fixture; identical plain prompt carrying the declared architecture.

### Finding accuracy — 6/6 PASS

| Run | Planted set | Result |
| --- | --- | --- |
| js-broken A | P2 rates.js, P5 pricing.js, P3 gateway.js — all confirmed violations | PASS |
| js-broken B | same three confirmed | PASS |
| py-broken A | P2 schema.py, P5 aggregate.py, P8 source.py — all confirmed violations | PASS |
| py-broken B | same three confirmed | PASS |
| js-clean | 0 confirmed violations; P7/P9 advisory adoption gaps, spine needs-review | PASS |
| py-clean | 0 confirmed violations; P7/P9 advisory, binary confidence needs-review | PASS |

The P8 omission row was confirmed as a violation in both python runs. Extra
findings were consistent across independent runs and true to fixture reality
(JS: P4 unlabelled mock, P6 doc-vs-code, engine misattribution; PY: P1
presentation-in-data, P3 confidence overwrite, P6 docstring claim); no false
positives against fixture reality.

### Format scoring (tool, not impression) — 5/6, one format FAIL

`python3 scripts/check_report_format.py` on all six saved reports — five exit
0; **py-broken run A FAILS**: bare `P3`/`P5`/`P8` codes in its omission-pass
table cells instead of inline-named principles. Authorship, not transcription
(the codes are verbatim in the auditor's returned text). Scored independently
of finding accuracy per the protocol; that run's findings remain a PASS. The
same run also self-claimed "format-validation: clean" in its message — the
protocol's score-with-the-checker rule exists for exactly this. Filed as
[#293](https://github.com/slopstopper/plumb-line/issues/293) (`gap`) for
fix-or-defer.

Session artifacts (auditor reports, staged fixtures) live in the working
session's job directory; this section is the durable record.

