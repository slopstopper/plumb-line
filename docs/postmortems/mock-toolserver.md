# The server that reported success for dead tools

*A reconstruction postmortem. The incident below is real and documented in
public issue trackers. The code in this write-up is a small synthetic
reconstruction of the same failure pattern
([`examples/incident-toolserver/`](../../examples/incident-toolserver/)) —
not the project's actual code. Sources at the end.*

## The incident

In August 2025, a user of an agent-orchestration framework filed an issue
titled "🚨 Critical: 85% of MCP Tools Are Mock/Stub Implementations." (MCP
tools are functions an AI agent can call — read a file, spawn a worker, store
a result. The framework offered hundreds of them.) The user had tested the
tools one by one, and found that most of them did nothing. They just returned
a payload that looked like success:

```json
{ "success": true, "tool": "agent_spawn", "message": "Tool executed successfully" }
```

`agent_spawn` returned IDs for agents that never existed. `task_orchestrate`
returned IDs for tasks that never ran. These placeholder tools — stubs — are
normal during development. The problem was that nothing marked them as
placeholders. Status reports aggregated their fake successes into real-looking
summaries, and the AI agents calling the tools built further work on top of
the results. A human developer might get suspicious that a tool always
succeeds instantly. An LLM agent has no such smell test: it takes
`"success": true` at its word.

Then something stranger happened: the numbers themselves came apart. A
follow-up analysis disputed the 85% figure and put it at 40%. A third-party
audit of a later version counted "99% theater." Three audits of the same
project produced three different numbers for how much of it was fake — and
none of them could be settled by looking at the code's outputs, because a fake
success and a real one were byte-for-byte the same shape.

The maintainers fixed it the only way available: auditing every tool by hand
and reimplementing, across several releases, eventually reporting mock tools
reduced to under 5%. Nobody recorded how many person-hours all parties spent
just *counting which tools were real*. Nobody could have: the thing being
counted was a matter of opinion, not a property of the data.

## The timeline, generalized

This shape repeats far beyond one framework:

1. An ambitious tool surface ships. Stubs stand in for unbuilt tools and
   return success-shaped payloads, so everything appears to work end-to-end.
2. The stubs are indistinguishable from real implementations everywhere they
   are called — by the orchestrator, by reporting code, by the agents using
   them.
3. Reports aggregate fake successes into real-looking status. People and
   agents act on the reports.
4. Someone eventually audits by hand. Their count is contestable, and gets
   contested. The artifacts can't settle the argument.
5. The remedy is a hand-audit of every tool — exactly the work that an
   automatic label would have made unnecessary.

## Root cause

The stubs were normal development tooling. The failure is that **fake data
left its container and entered real output paths carrying no label**. Once
that happened, no artifact in the system could distinguish a real success
from a theatrical one — which is also why the audits disagreed: "how much of
this is fake?" had become unanswerable from the data itself.

In plumb-line's terms this violated two principles at once: *quarantined
fakery* (mock data must be labeled and kept out of real outputs unless
explicitly invited in) and the *maturity vocabulary* (nothing distinguished
finished tools from placeholders, so the tool surface claimed more than the
tool reality).

## The reconstruction

To make the pattern concrete without pointing at anyone's code,
[`examples/incident-toolserver/`](../../examples/incident-toolserver/)
rebuilds it in about 50 lines: a toy server with five tools, where two do
real work and three are stubs returning plausible success payloads. A status
report aggregates all five.

Run the uninstrumented version (`node broken/toolserver.mjs`) and this is the
entire output:

```
tool results:
  hash_text          success
  count_words        success
  spawn_worker       success
  orchestrate_tasks  success
  store_memory       success
system health: operational (5/5 tools succeeded)
```

Everything adds up. The summary is green. Three-fifths of it is theater, and
no signal anywhere says so. This is the incident, in miniature.

## Corrective action

The instrumented version (`node instrumented/toolserver.mjs`) changes one
thing: each tool result is wrapped in a small provenance envelope at the
moment it is produced, recording where the value came from — `real` for the
two working tools, `mock` for the three stubs. The stubs stay; quarantining
fake data means labeling it, not deleting it.

The status report is then *derived* from those wrapped results, and this is
where the library does its work. Derived values follow one rule, the
conservative combination law: a result is never more trustworthy than its
least trustworthy input, and once any input was fake, everything computed
from it says so, permanently. The same report now prints:

```
tool results:
  hash_text          success  [source: real]
  count_words        success  [source: real]
  spawn_worker       success  [source: mock]
  orchestrate_tasks  success  [source: mock]
  store_memory       success  [source: mock]
system health: operational (5/5 tools succeeded)

report provenance:
  derivedFromMock: true
  confidence: none
  weakestSource: mock
  mock inputs: 3/5 (computed from lineage, not estimated)
```

The health line hasn't changed — the stubs really did return success. What
changed is that the report can no longer forget what it was built from.
Notice the last line: the question that consumed the real incident's
hand-audits, *how much of this is fake?*, is now answered by the report
itself. The envelope records the ancestry of the value (its lineage), so the
mock fraction is computed, not estimated. Nobody argues about 85% versus 40%
when the denominator is machine-readable.

One more thing to try: cheat. The demo's last section re-derives the report
while explicitly claiming it is real:

```
attempted launder (derive with source: "real"):
  laundering: clean source 'real' but derivedFromMock is true
```

The claim is accepted; the taint is not cleared; the library's runtime
checker flags the contradiction. There is no API for making a value forget
that fake data went into it. That is the point of the library.

There is also a version of this catch that needs no code changes at all:
pointing `plumb-line-audit` — the review-time half of plumb-line, a Claude
Code skill — at the uninstrumented variant flags the success-shaped stubs
feeding a reporting path. That is the intended adoption order: run the audit
first (zero integration, decide later), reach for the runtime library when
you want the honesty enforced while the code runs.

## What this class of failure costs

Here the currency was developer trust, plus a rolling hand-audit nobody
enjoyed. With money or safety downstream of the fake values, the price goes
up. The pattern is always the same sentence: **a value that forgot where it
came from was combined into a claim someone acted on.** Any system that
mixes stub, cached, fallback, or LLM-generated data with real data can carry
this failure; the question is whether the fakery is visible by the time it
reaches an output.

## Sources

- [ruvnet/ruflo#653](https://github.com/ruvnet/ruflo/issues/653) — the
  original "85% mock/stub" validation analysis (August 2025).
- [ruvnet/claude-flow#658](https://github.com/ruvnet/claude-flow/issues/658) —
  follow-up analysis disputing the denominator (40%).
- [Third-party audit gist](https://gist.github.com/roman-rr/ed603b676af019b8740423d2bb8e4bf6) —
  "300+ MCP Tools — 99% Theater, 1% Real."
- [ruvnet/claude-flow#660](https://github.com/ruvnet/claude-flow/issues/660) —
  the Alpha 90 release notes reporting mock reduction to <5%.

---

*Provenance of this document: drafted by Claude (claude-fable-5), reviewed and
approved by the maintainer; audited with `plumb-line-audit` before
publication like everything else here. The reconstruction code is in
[`examples/incident-toolserver/`](../../examples/incident-toolserver/) with a
deterministic integrity test.*
