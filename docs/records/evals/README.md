# Eval suite runs

One file per recorded run of the `claude plugin eval` suite in `evals/`
(#291), named for its date. Each record gives the plugin and Claude Code
versions, the cases and arms run, each arm's pass rate per case, and the
with-minus-without difference only where the same graders score both arms
(#530). The runs are listed in
[`../../validation-results.md`](../../validation-results.md#eval-suite-runs).

None is recorded yet: the first green run (#530) will be. The first real run
(2026-09-28) found drift in the suite rather than a result, and is described
in [`evals/README.md`](../../../evals/README.md).
