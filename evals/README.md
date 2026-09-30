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
  plugin fired; the no-plugin arm has no plugin skill to invoke.
- `tool_used` (with-only): a Python interpreter **invoked** the report-format
  checker, as the audit skill instructs. It proves the call was made, not that
  it succeeded, because `tool_used` matches a call's input, never its outcome.
  The pattern needs the interpreter, so a heredoc whose report text names the
  checker does not count.
- `regex` (with-only): the v4 report header opens the message, as the
  checker requires (leading blank and fence lines allowed; held to the
  checker by `scripts/test_eval_graders.py`). Until the 2026-09-30 run it
  matched the header anywhere (`docs/records/evals/2026-09-30.md`). Since
  #591 every grader in every case is with-only, so the runner scores them
  all ("if every grader in a case is in the excluded set, they're scored
  normally instead", <https://code.claude.com/docs/en/plugin-evals.md>):
  the header is gated on the clean cases too, as it was on the broken
  cases (owner decision 2026-09-30, recorded on #591). Until #591 the
  clean cases scored only the judge, so their format was recorded, not
  gated (#530). Clean-case pass rates from before and after #591 do not
  compare: two of the 2026-09-30 run's js-clean reports open with prose,
  so the same reports would score at most 1/3 under the header grader.
  Every eval record also runs the checker on each report it can recover,
  as delivered, never a copy the auditor checked; a report that fails
  while stamped `— clean` by the current checker gets its own issue, the
  stamp not earned, and the record counts it as a false verdict, not
  only a format fail (#581). The checker cannot run inside the suite:
  the runner has no grader that executes code ("There are no custom-code
  graders", same docs). In the 2026-09-30 run the only report text the
  runner kept was the judge's evidence, on the clean cases, and the
  broken-case messages were lost (`docs/records/evals/2026-09-30.md`,
  #585). `--keep-temp` may keep them (below).
- `regex` (with-only), broken cases, one per planted violation: a
  findings-table row whose Path cell names the file, whose Status cell is
  `violation` and whose Principle cell carries the principle's inline name.
  - A needs-review or advisory row does not match, and neither does an
    omission-pass cell or a coverage line.
  - The Status column is contracted by report-format v4 and checked by the
    format checker (#530), so the grader reads a field, not a wording habit.
    Grader and checker accept the same spellings: the word in any case, with
    bold, italics or a code span around it (`scripts/test_eval_graders.py`).
  - Together these hold the harness's scoring rule for a broken fixture:
    every planted violation confirmed, none downgraded; extra findings are
    acceptable.
  - A bare file-name pattern would pass on a run that only listed the
    fixture's files. The first real run did exactly that, crediting a run
    that had audited nothing (#291).
- `regex` (with-only), clean cases: no findings row whose Status is
  anything but `needs-review` or `advisory` (`no-confirmed-violations.md`,
  `match: not_contains`). Inverted, a row the pattern missed would pass the
  case, so it fails closed: a `violation`, or any status the checker would
  refuse, fails. It reads rows as the checker does (indented rows, escaped
  pipes, decorated statuses) and is held to it by
  `scripts/test_eval_graders.py`, which also flips every row of the
  committed 2026-09-30 reports to `violation` to show each is caught. It
  knows a findings row by its Principle cell opening with a principle
  code; a row whose Principle cell does not open, after whitespace, `*`,
  backticks or `(`, with a code is not seen (none in the committed
  reports), and an omission-pass row whose last
  cell opens with a code fails the case, on the safe side.
  It replaces the runner's `llm` judge, which is out of scoring until it
  records its reasoning and reproduces the mechanical verdicts on a
  calibration set (#591, owner decision 2026-09-30). The judge failed 7
  of 12 with-plugin broken-fixture runs on 2026-09-28, each on a report
  that visibly confirms every planted violation (#291), and on the clean
  cases it gave no reasoning for any vote (the 2026-09-30 runs, #591).

**What to report: each arm's pass rate, and the difference only where it
means something** (owner decision 2026-09-30, #530). Record each arm's pass
rate for every case. Since #591 no grader measures both arms: every grader
reads something only the plugin produces (the audit skill, the v4 header
and Status column, inline principle names, the checker). The no-plugin
arm can pass the clean cases' Status grader without a Status column (none
of its 2026-09-30 reports wrote one), and fails the header grader by
construction. So record every with-minus-without difference as "n/a
(suite construction)". The runner's own difference (`aggregates.meanDelta`,
each case's `delta`, and the report's "Plugin effect" headline) is then
an artefact of that construction, as its docs warn for graders counted in
both arms: never cite it. Until #591
the clean cases' judge scored both arms, and its difference was recorded
with the caveat that its criteria use the plugin's vocabulary.

Until #530, `invoked-audit` had no `arm:` key, so it scored the no-plugin arm
too, which cannot invoke a plugin skill. The 2026-09-28 run's no-plugin
results (every case 0/3) and its with-minus-without figures were therefore
set partly by that grader; later runs, where it scores the plugin arm only,
do not compare with them. Graders that run in both arms
without depending on the report format would give the broken cases a real
difference (#571); so would a runner judge that can be trusted again.

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
claude plugin eval --scaffold --allow-tools Bash --no-publish --keep-temp \
    --max-cost-usd 15 --json results.json --report report.html
claude plugin eval --scaffold --allow-tools Bash --no-publish --keep-temp \
    --case "audit-py-*"                  # one fixture
```

`--keep-temp` "Keep[s] every run's sandbox directory and print[s] its
path" (same docs). Whether that directory holds each run's trace, and
the trace the delivered message, is not documented; the first run with
the flag will show it. If it does, the record can recover every run's
delivered message, broken cases included, and run the checker on it
(#585, #591).

`--no-publish` keeps the HTML report local; by default it is published to
claude.ai. Pass `--trust-plugin` with no terminal, or with `--json`: in
either case the first-run trust prompt cannot be answered, and the run is
refused.

## trigger/ — tiered trigger-quality checks (runnable today)

`evals/trigger/` holds description trigger-quality query sets
(`audit-queries.json`, `adopt-queries.json`, `pressure-queries.json`:
realistic should-trigger queries plus near-miss should-NOT-trigger queries),
run by `scripts/trigger_check.py` against the installed plugin, or a
checkout with `--plugin-dir` — no `claude plugin eval` needed. The harness is tiered by design: a small-model screen over every
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
settings, every installed plugin, their SessionStart hooks, and any MCP
servers or claude.ai connectors. On the owner's machine (2026-09-28, #487)
that was 19 plugins, 9 hooks and 3 connectors. One hook, superpowers', tells
the model to invoke a skill if there is even a 1% chance it applies. A
default-mode rate describes that environment as much as the description.

`--plugin-dir PATH` probes a checkout instead, adding `--setting-sources
project --strict-mcp-config` (the isolation the impossible-task spike used).
Observed on the owner's machine: the checkout's plumb-line loaded, plus
Claude Code's two built-in plugins (`agents-md@builtin`,
`telemetry@builtin`); no user plugin, hook, MCP server or connector, and not
the installed copy of plumb-line. Every record lists what its probe sessions
reported loading, and `--validate` checks it (below).

What these rates measure, and what they do not. A probe is one prompt, in an
empty directory, and a trigger is when the first Skill call in the model's
first reply names the target (a Skill call to another skill first is a miss;
other tool calls in that reply do not stop it; `max_turns` 2). The impossible-task spike (#462) measured something else
under the same isolation flags: 90 Opus 5.5 runs with the plugin loaded,
each in one of six small repositories built for the spike, with a failing
test and an `AGENTS.md`. A plumb-line skill was invoked once (#487), in arm
Cp, whose prompt told the agent to use the plugin's skills where they
apply; without that instruction, 0 of 60. So a trigger rate here says how
strongly a bare prompt pulls the description in. Whether an agent reaches
for the skill during the task, after reading the failing test, is what the
spike's plugin arm measures; round 3 (planned) repeats it. Neither measures
competition with other skills a user may have installed, such as a
debugging or testing skill that also claims a failing test.
`pressure-queries.json` targets `plumb-line-method`, as does
`pressure-fresh-queries.json`, a smaller set written blind by an independent
agent to check that a description generalises beyond the queries it was
tuned on. `breadth-queries.json` covers the moments beyond tests and names,
per query, the skill that should win (`expected_skill`; `null` for a
near-miss that should trigger none). Run it with any plumb-line skill as the
target: `scripts/breadth_routing.py --derive <skill> <queries>` writes the
eval set trigger_check reads for that target, trigger_check records the
winner of every probe, and `scripts/breadth_routing.py <queries> <record>`
reads the routing across all five skills (a query routes when its skill wins
at least half its probes; a near-miss only when no probe triggers any skill). Measured records, before and after description changes, are in
`results/` (#487).

The results file is a contracted record (`results-format: v3`; v1 #317, v2
#400, v3 #487). It records the probed installs (for a checkout, a hash of
the target skill's frontmatter and one over every skill's frontmatter, so a
before-record and an after-record of one checkout are told apart even when
only a competing sibling's description changed), the models per tier, the
per-tier run counts, the threshold, and the probe settings that change
verdicts: the per-probe `timeout_s` (a probe killed at its timeout never
completes its reply, which voids the record), the `max_turns` cap, and
`isolation_flags` (the flags above, or none). `environments` lists each distinct environment the probe sessions
reported (Claude Code version, plugins, skills, MCP servers with their
status, plugin errors; a field the session did not report is `null`, not
empty), with a probe count, and how many probes never reported one.

`--validate` re-derives every row's pass from its rate, the stamped
threshold and its expectation, so a stored verdict is consistent with its
own numbers rather than asserted. It refuses a record unless:

- every probe reported an environment, and every probe's first reply
  completed (a session that hits a usage limit, an overload or an expired
  login, before or partway through its reply, or is killed at its timeout,
  reports an environment but no completed reply);
- the probes' environment counts add up to the runs the record implies;
- the probes shared one environment: exactly, for an isolated run; by CLI
  version, plugins and skills, in default mode, where a user's connector
  changing status mid-run is recorded but does not void the run;
- the target skill loaded; and
- for an isolated run, no MCP server appeared, no plugin reported an error,
  and the probed checkout is among the plugins that loaded.

Otherwise a non-trigger may measure a skill that never loaded (the
2026-08-18 failure), a session that failed, or an environment the record
does not claim. A run whose own record fails these checks still writes it,
as evidence, and exits 1. It
also refuses a v1 record, which does not say what the timeout or turn cap
was, and a v2 record, which does not carry the environment. The record does
not capture `--workers` (concurrency can push a probe past its timeout) or
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
- Until a green run is recorded in `docs/records/evals/` (listed in
  `docs/validation-results.md`), this suite
  supplements the manual protocol in `examples/AUDIT-EXPECTATIONS.md` and does
  not replace it. The manual protocol remains the release gate.
- The auditor's grants are read-only tools plus sandboxed Bash for the
  checker. The read-only contract toward the audited code is the audit
  skill's, not the sandbox's. The staged fixture copy sits in the writable
  workspace, so Bash could modify it. The graders read only the final message
  and the tool calls.
