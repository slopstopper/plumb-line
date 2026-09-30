# Eval suite runs

One file per recorded run of the `claude plugin eval` suite in `evals/`
(#291), named for its date, green or not: a missing record is
indistinguishable from "never run". The runs are listed in
[`../../validation-results.md`](../../validation-results.md#eval-suite-runs).

From the first green run on (planned, #530), a record gives the plugin and
Claude Code versions, the cases and arms run, each arm's pass rate per case,
and the with-minus-without difference only where the same graders score both
arms; elsewhere it records "n/a" with the reason (#530, #571).
