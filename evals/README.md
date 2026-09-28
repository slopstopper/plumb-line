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
- `tool_used` (with-only): the audit skill was invoked. This shows whether the
  plugin fired; it is not part of the score.
- `tool_used` (with-only): a Python interpreter **invoked** the report-format
  checker, as the audit skill instructs. It proves the call was made, not that
  it succeeded, because `tool_used` matches a call's input, never its outcome.
  The pattern needs the interpreter, so a heredoc whose report text names the
  checker does not count.
- `regex` (with-only): the v3 report header. A format FAIL is scored
  independently of the findings, per the harness.
- `regex` (with-only), one per planted violation: a findings-table row whose
  Path cell names the file, whose Issue cell opens with a `violation` status
  and whose Principle cell carries the principle's inline name.
  - A needs-review or advisory row does not match, and neither does an
    omission-pass cell or a coverage line.
  - The status word is the skill's reporting convention, not a contracted
    field, so a report that words its status differently would be missed.
  - A bare file-name pattern would pass on a run that only listed the
    fixture's files. The first real run did exactly that, crediting a run
    that had audited nothing (#291).
- `llm` judge, holding the harness's scoring rule: a planted violation
  downgraded to advisory is a FAIL, and on clean fixtures any confirmed
  violation is a FAIL.

**What the with/without delta measures.** Every grader except the `llm` judge
is with-only, because the no-plugin arm cannot pass it: it has no v3 header,
no inline principle names and no checker. So the delta comes from the judge
alone. On 2026-09-28 the runner's judge failed broken-fixture reports that it
passes when asked directly (#291). Until that is resolved, the delta is not
evidence of finding accuracy.

Each case lists the tools the auditor may use in `prompt.md`
(`allowed_tools`). The sandbox grants none by default. Without `Read`, the
skill cannot read its own `reference/portable-principles.md`, and it rightly
stops rather than audit from memory.

## Running

The scaffolds stage the fixtures, so `--scaffold` is required: without it
every case audits an empty directory.

Running the checker needs Bash. Bash is a gated tool: it cannot go in
`allowed_tools`, which takes read-only tools only, and without the operator
grant it is removed from the session. `Bash(python3 *)` alone is not enough,
because the skill first writes the report to a temp file. Bare `Bash` is the
grant used here; `--allow-tools Write "Bash(python3 *)"` would also cover it,
and is narrower. Under eval, every Bash command runs in the OS sandbox:
writes are confined to the run's workspace, and the home directory and
Claude Code configuration are unreadable.

```sh
claude plugin eval --scaffold --allow-tools Bash --no-publish \
    --max-cost-usd 15 --json results.json --report report.html
claude plugin eval --scaffold --allow-tools Bash --no-publish \
    --case "audit-py-*"                  # one fixture
```

`--no-publish` keeps the HTML report local; by default it is published to
claude.ai. Pass `--trust-plugin` with no terminal, or with `--json`: in
either case the first-run trust prompt cannot be answered, and the run is
refused.

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
# add --plugin-dir . to probe this checkout instead of the installed plugin
python3 scripts/trigger_check.py --validate results.json
```

By default the probes see what an interactive session sees: the user's
settings, every installed plugin, and those plugins' SessionStart hooks. On
the owner's machine that was 19 plugins and 9 hooks, one of which tells the
model to invoke any skill that might apply (measured 2026-09-28, #487), so a
default-mode rate describes that environment as much as the description.
`--plugin-dir PATH` probes a checkout instead, with `--setting-sources
project`, so the user's plugins, hooks and installed copy of plumb-line stay
out. Use it to compare descriptions before and after a change.

The results file is a contracted record (`results-format: v3`; v1 #317, v2
#400, v3 #487). It records the probed installs, the models per tier, the
per-tier run counts, the threshold, and the probe settings that change
verdicts: the per-probe `timeout_s` (a timed-out run records as a
non-trigger), the `max_turns` cap, and `setting_sources` (`all`, or
`project` for an isolated `--plugin-dir` run). `--validate` re-derives every
row's pass from its rate, the stamped threshold and its expectation, so a
stored verdict is consistent with its own numbers rather than asserted. It
refuses a v1 record, which does not say what the timeout or turn cap was, and
a v2 record, which does not say which setting sources were loaded. The record does not capture `--workers`
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
    acceptable, although recorded harness runs score them as PASS
    (`examples/AUDIT-EXPECTATIONS.md` now cites those runs). Whether the
    old wording caused any judge FAIL is not shown.

  `context.add_dirs` cannot reach outside the case directory, so it cannot be
  used to expose the plugin's own files. Read access alone was enough.
- Until a green run is recorded in `docs/validation-results.md`, this suite
  supplements the manual protocol in `examples/AUDIT-EXPECTATIONS.md` and does
  not replace it. The manual protocol remains the release gate.
- The auditor's grants are read-only tools plus sandboxed Bash for the
  checker. The read-only contract toward the audited code is the audit
  skill's, not the sandbox's. The staged fixture copy sits in the writable
  workspace, so Bash could modify it. The graders read only the final message
  and the tool calls.
