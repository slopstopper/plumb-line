# Eval suite runs

One file per recorded run of the `claude plugin eval` suite in `evals/`
(#291), named for its date, green or not: a missing record is
indistinguishable from "never run". The runs are listed in
[`../../validation-results.md`](../../validation-results.md#eval-suite-runs).

From the first green run on ([the 2026-09-30 re-run](2026-09-30-rerun.md),
#291), a record gives the plugin and
Claude Code versions, the cases and arms run, each arm's pass rate per case,
and the with-minus-without difference only where the same graders measure
both arms; elsewhere it records "n/a" with the reason (#530, #571). Since
#591 no grader measures both arms, so every difference is "n/a", and the
runner's own Δ is not cited.
