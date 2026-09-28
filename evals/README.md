# evals/ — blind validation as a `claude plugin eval` suite (#291)

This directory encodes the release harness's Part 1 (blind validation, see
`docs/release-harness.md` and `examples/AUDIT-EXPECTATIONS.md`) as a
`claude plugin eval` suite, so the non-deterministic layer of the harness can
run repeatably and leave a stored JSON result.

## Cases

One case per fixture variant, mirroring the blind protocol:

| Case | Fixture | PASS means |
| --- | --- | --- |
| `audit-js-broken` | `examples/js-payments-service/broken` | all 3 planted violations confirmed (P2 rates.js, P5 pricing.js, P3 gateway.js) |
| `audit-js-clean` | `examples/js-payments-service/clean` | zero confirmed violations; P7/P9 advisory only |
| `audit-py-broken` | `examples/python-data-pipeline/broken` | all 3 planted violations confirmed (P2 schema.py, P5 aggregate.py, P8 source.py) |
| `audit-py-clean` | `examples/python-data-pipeline/clean` | zero confirmed violations; P7/P9 advisory only |

Each case: `runs: 3`, set in its `prompt.md` front matter (the harness requires
>=2 independent auditors per broken fixture), an identical plain prompt carrying
the declared architecture from protocol step 3, and a `scaffold.sh` that stages
the fixture per protocol step 2 (answer keys deleted, every line naming a violation stripped
case-insensitively, strip verified before dispatch). The scaffold scripts are
plain bash and were tested directly on 2026-08-18; the planted violation lines
survive the strip.

Graders per case:
- `tool_used`: the audit skill was invoked. Under the default with/without
  ablation this is a with-only indicator of whether the plugin fired, not part
  of the score.
- `tool_used`: the report-format checker actually ran, as every blind auditor
  runs it in the manual harness. A report's own `format-validation:` line is
  not taken on trust.
- `regex`: the v3 report header. A format FAIL is scored independently of the
  findings, per the harness.
- `regex`, one per planted violation: the file **and** its principle's inline
  name on one line, which is a findings-table row. A bare file-name pattern
  would pass on a run that only listed the fixture's files. The first real run
  did exactly that, crediting a run that had audited nothing (#291).
- `llm` judge, holding the harness's scoring rule: a planted violation
  downgraded to advisory is a FAIL, and on clean fixtures any confirmed
  violation is a FAIL.

Each case lists the tools the auditor may use in `prompt.md`
(`allowed_tools`). The sandbox grants none by default. Without `Read`, the
skill cannot read its own `reference/portable-principles.md`, and it rightly
stops rather than audit from memory.

## Running

The scaffolds stage the fixtures, so `--scaffold` is required: without it
every case audits an empty directory.

Running the checker needs Bash. Bash is a gated tool: it cannot go in
`allowed_tools`, which takes read-only tools only, and without the operator
grant it is removed from the session. The grant is bare `Bash`, because the
skill first writes the report to a temp file, which a narrower pattern such
as `Bash(python3 *)` does not cover. Under eval, every Bash command runs in
the OS sandbox: writes are confined to the run's workspace, and the home
directory and Claude Code configuration are unreadable.

```sh
claude plugin eval --scaffold --allow-tools Bash --no-publish \
    --max-cost-usd 15 --json results.json --report report.html
claude plugin eval --scaffold --allow-tools Bash --no-publish \
    --case "audit-py-*"                  # one fixture
```

`--no-publish` keeps the HTML report local; by default it is published to
claude.ai. Pass `--trust-plugin` when there is no terminal to confirm the
first-run trust prompt.

## trigger/ — tiered trigger-quality checks (runnable today)

`evals/trigger/` holds description trigger-quality query sets
(`audit-queries.json`, `adopt-queries.json`: realistic should-trigger queries
plus near-miss should-NOT-trigger queries), run by
`scripts/trigger_check.py` against the *installed* plugin — no `claude plugin
eval` needed. The harness is tiered by design: a small-model screen over every
query, then a session-tier confirm pass over only the contested ones, with
every reported rate labeled by the model that measured it (a haiku-measured
trigger rate is a haiku claim). Triggering is detected on the Skill tool's
`skill` field, never by substring. Born from the 2026-08-18 incident where an
untiered run consumed a full usage window in minutes (#291).

```sh
python3 scripts/trigger_check.py evals/trigger/audit-queries.json \
    plumb-line-audit results.json            # cheap screen only
# add --confirm-model <session model> to re-measure contested queries
# add --threshold 0.75 to change the pass threshold (default 0.5; stamped
#   into the results, so a stored verdict always names the bar it cleared)
python3 scripts/trigger_check.py --validate results.json
```

The results file is a contracted record (`results-format: v2`; v1 #317, v2
#400). It records the probed installs, the models per tier, the per-tier run
counts, the threshold, and the probe settings that change verdicts: the
per-probe `timeout_s` (a timed-out run records as a non-trigger) and the
`max_turns` cap. `--validate` re-derives every row's pass from its rate, the
stamped threshold and its expectation, so a stored verdict is consistent with
its own numbers rather than asserted. It refuses a v1 record, which does not
say what the timeout or turn cap was. The record does not capture `--workers`
(concurrency can push a probe past its timeout), the `claude` CLI version, or
model sampling, so a re-run is not guaranteed to reproduce the same rates.

## Status and honest caveats

- `claude plugin eval` is early access and org-gated; it is enabled on the
  owner's account as of 2026-09-28 (#291, Claude Code 2.1.283). The suite
  was authored 2026-08-18 against the harness format as reported that day.
  Its first real run (2026-09-28, one run per case, with and without the
  plugin, $1.34) found drift, fixed here:
  - no tools were granted, so the skill could not read its principles file;
  - `--scaffold` is needed;
  - the file-name graders credited a bare file listing;
  - Bash needs the operator grant, and a narrow pattern is not enough, so
    the checker never ran;
  - the judge criteria did not say that extra confirmed violations are
    acceptable, which is how the manual harness has always scored them.

  `context.add_dirs` cannot reach outside the case directory, so it cannot be
  used to expose the plugin's own files. Read access alone was enough.
- Until a green run is recorded in `docs/validation-results.md`, this suite
  supplements the manual protocol in `examples/AUDIT-EXPECTATIONS.md` and does
  not replace it. The manual protocol remains the release gate.
- The auditor's grants are read-only tools plus sandboxed Bash for the
  checker. The audit skill's contract is read-only toward the audited code,
  and the sandbox confines writes to the run's workspace, where only the
  staged fixture copy and the temp report live.
