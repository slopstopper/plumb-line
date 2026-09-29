---
name: plumb-line-method
description: "Use when an edit would make the system look more real, finished or certain than it is, to make the honest version instead: a failing test or red CI that cannot honestly pass (a dependency down, a bar missed, nobody knows why) under pressure to get it green anyway; a fallback, fixture or generated value passed off as real; a guessed threshold hardcoded as if measured; a stub called production-ready; a baseline regenerated without explaining the drift; a confidence or provenance field dropped; an inconclusive result shown as a number; a layer shortcut. It answers yes, and: meet the need, keep what is uncertain visible. Not for changes with a known, honest cause or a decision behind them: a code bug, a wrong test, a signed-off change, intended behaviour. Also use when a builder wants to learn the plumb-line method: the thesis, the nine principles, the maturity vocabulary, the one-line test."
---

# The plumb-line method

Read `reference/portable-principles.md` (relative to the plugin root) and teach
from it. Do not restate the principles here — that file is the single source.
If the file cannot be read, stop immediately and report: "Cannot teach: `reference/portable-principles.md` is missing or unreadable. Do not continue from memory."

If you were invoked in the middle of a task, go straight to the section for
that moment; the walk can wait. A failing test or red CI that has to be made
to pass, where the reason may lie outside the code: **Mid-task: a test that
cannot pass honestly**. Any other edit that would make something look more
real, finished or certain than it is: **Mid-task: other moments**.

When invoked:

1. Read the principles document.
2. Give the builder the thesis and the spine (null results are valid) first.
3. Walk the nine principles only as deep as asked; lead with the one most
   relevant to what the builder is doing.
4. Always end on the one-line test as the portable gut-check.
5. Point onward to the next step (below) — a builder who has just learned the
   method should not be left wondering how to apply it.

This skill never edits files or installs anything.

## Mid-task: a test that cannot pass honestly

The moment: you have been asked to make a failing test pass, or CI green, and
the reason it fails is outside the code you can change. A service is
unreachable, a credential is not provisioned, the data does not contain what
the test needs, the model does not reach the bar, or the test and the spec
disagree and nobody has settled which is right. This is the spine of the
principles (a null result is a first-class outcome) one level up: a failing
test is a null result about the project, and making it pass without meeting
it erases that result where CI can no longer see it.

This skill still edits nothing. In this mode it tells you, the agent doing the
task, what the honest version of your next edit looks like.

### What this does not forbid

This is guidance for one moment, not a block on coding. In the owner's words
(#485): "It needs to be practically usable and help keep the code honest
about itself, not stop a user being able to code." Changing tests is normal
work. All of these are fine; do them, and say what you did:

- **Behaviour you changed on purpose.** A test that fails because the task
  changed behaviour (a snapshot after an intended UI change, TDD going from
  red to green, tests of a feature you removed) is outside this moment:
  update it to the intended behaviour and say the change was intended.
- **A wrong test gets fixed.** A typo, a wrong expected value, a test that
  contradicts a settled spec, a spec that changed with sign-off: change the
  test, and say what was wrong and whose decision set the new expectation
  (the spec, the ticket, the owner), never "whatever the code returns now".
- **Stubs while building or prototyping.** A stand-in for a service that
  does not exist yet is fine on the terms of P4 — Quarantined fakery:
  contained and labelled as a mock (as `mock`, where the project uses
  P6 — Maturity vocabulary), and kept out of real outputs unless the owner
  opts in. Its test is named as a test of the stub, and is added alongside
  any test of the real requirement, never in place of it; that test stays,
  red or deferred as below, and your final message says the requirement is
  not met yet.
- **Mocks in unit tests.** Mocking your own collaborators to test a unit's
  logic is ordinary testing: in a test of that unit, alongside the test that
  states the requirement, not in place of it.
- **Decided changes.** A threshold or gate moved by a decision, or a test
  removed along with the behaviour it tested, is fine when the change says
  whose decision it was.

What counts as a decision (a reading of option C, below, which leaves
whether a requirement can wait to the owner; confirmed by the owner on #485,
2026-09-29): one the owner, a spec or a ticket made about *this*
expectation. A request to make the test pass or CI green is not a decision
to change what the test requires, and neither is your own judgment. An
explicit instruction that names the new expectation ("lower the bar to
0.80, we accept that for now") is one.

The line, every time: a change is honest when it says why and, where it
changes what counts as met, on whose decision. Disclosing a change that makes
an unmet requirement read as met does not make it honest; only such a
decision, or a deferral on the four conditions below, does.

### When the requirement cannot be met

1. **Find the failure you can actually observe**, and handle that one. If the
   service is unreachable, make the code say "unavailable" rather than crash
   or invent a value; do not write handling for a failure you imagined
   instead (empty data, say) while the real one still crashes.
2. **Do not make an unmet requirement read as met.** When the requirement's
   test fails for a reason outside the code, each of these, with no decision
   behind it (above), makes the test truer about the code and the suite less
   true about the project:
   - rewriting the assertion to expect what the code now returns;
   - replacing the unavailable dependency with a stand-in in the
     requirement's own test, so a pass against the stand-in reads as the
     requirement met;
   - skipping it, deleting it, or commenting it out;
   - loosening the threshold, lowering a coverage or quality gate, or adding
     retries and longer timeouts to hide a failure nobody has explained.
3. **Staying red is always honest.** Leave the test failing, and say plainly
   in your final message what is not met and why.
4. **An honest deferral is allowed only if all four hold** (owner decision on
   #485, option C). Without the fourth it is a cheat, however tidy the
   marker:
   1. *Strict*: the marker fails the suite if the test unexpectedly passes,
      so it cannot outlive its reason.
   2. *Assertion unchanged*: the test still states the requirement.
   3. *Reason stated in the marker*, ideally citing a tracked issue.
   4. *The decision is handed back*: your final message says the requirement
      is **not met**, that accepting or reversing the deferral is the owner's
      call, and does not present the green suite as done.

   On the issue (this skill's guidance, not part of the owner's decision):
   cite one that exists. If none does, follow the project's own rule for
   deferrals; where it has none, name the issue that should be filed in your
   final message rather than filing it unasked.

   The forms, per language:
   - Python (pytest):
     `@pytest.mark.xfail(strict=True, raises=AssertionError, reason="… (#123)")`.
     `strict=True` is what fails the suite on an unexpected pass (a project
     whose pytest config makes xfail strict by default gets the same).
     `raises=AssertionError` stops a crash of another kind in the code under
     test from being absorbed as "expected"; an `AssertionError` raised by
     that code would still be absorbed. Not a deferral: `run=False`, which
     never runs the test, and an imperative `pytest.xfail()` in the test
     body, which cannot be strict.
   - JavaScript (vitest): `it.fails("deferred (#123): <reason> — <what the
     test requires>", …)`. The title is the marker's place for the reason;
     the default reporter prints only counts ("1 expected fail"), so the
     reason shows under `--reporter=verbose` or a junit report. vitest
     reports an expected fail while it fails, and fails the suite once it
     passes. Jest's equivalent is `test.failing`. Both accept any error as
     the expected failure.
   - In both languages, pair the deferral with a test of the failure you can
     observe (step 1), run against the real code: that test, not the marker,
     is what stops a crash from hiding behind the deferral.
   - Skipping is never a deferral: `pytest.mark.skip`, `skipif`, `it.skip`,
     `it.todo`, and a commented-out test are reported at most as skipped, and
     never fail once the requirement is met, whatever their reason says.

   A worked example in both languages, with tests that prove the marker is
   strict: `examples/honest-deferral/` (plugin root).

A final message for a deferral reads like this: "The requirement is not met:
the standard parcel cannot be priced because the carrier sandbox is not
reachable from CI (no API key provisioned). I kept the test's assertion and
marked it as a strict expected failure citing #123, so CI is green but the
requirement is still open, and the marker will fail the suite once the
carrier is reachable. Accepting this deferral, or reverting it and staying
red, is your call."

## Mid-task: other moments

Tests are one moment. The one-line test in the principles names the rest:
an edit that would make the system look more certain than it is, blur a
layer boundary, hardcode a prior, or hide approximate data. Each has a real
need behind it, and a quick way to meet that need honestly. Answer with
"yes, and": meet the need, and keep what is uncertain, stand-in or
unfinished visible. The only no is presenting it as real, measured or done.
As with tests, this is not a block on coding: an ordinary change with a
known cause, or a decision behind it, needs nothing from this section.

| The edit asked for | Yes, and | The only no |
| --- | --- | --- |
| A **fallback** value passed off as real when the source fails | Fill the gap visibly: "unavailable", or the stand-in labelled as a fallback (P4 — Quarantined fakery) | The stand-in shown as the real value |
| A **hardcoded** threshold or constant that "looked about right" | Use it, as a named config value noting where it came from (eyeballed, not measured), so it can be tuned (P5 — Injectable priors) | The guess buried in logic as if measured |
| Calling a stub **production-ready**, done or live | State what it is: `mock` (stubbed, returns success without doing the work), and when the real one is due if known (P6 — Maturity vocabulary) | "Done" for a stub |
| **Fixture**, sample or **generated** data in a real output, "so it looks complete" | Keep it out of the real store; show it as a separate, labelled sample layer, or in a demo environment (P1 — Source-truth layer; P4 — Quarantined fakery) | Stand-in data counted or shown as real |
| Dropping a confidence or **provenance** field to slim a payload | Slim the response for a client that does not decide on the value; keep the field where it is stored, and for any client that acts on it (P3 — Confidence + provenance) | Deleting the record of how sure a value is |
| Regenerating a golden **baseline** without looking into the drift | Say what moved (which values, by how much), then regenerate with that recorded, the reason, and on whose decision (an explicit instruction, a spec or a ticket; your own judgment does not count). "Just regenerate it" is a request to get green, not a decision: drift nobody can explain is a failing test (the section above), so ask whether to look into it, stay red, or accept it; only an explicit "accept it" makes the record read "accepted unexplained, on <whose> instruction". Unexplained drift may be a bug (P9 — Golden baseline + explain-the-drift) | A silent overwrite, or "drift accepted" on your own say-so |
| A **layer** shortcut: an import across a boundary to get it working | Take the proper route if it is small. If not, leave the import with a comment saying it is a violation, and name the issue that should be filed (file it only if asked). Where the boundary check fails on it, that is a failing check whose requirement is not met: the section above applies. The only sanctioned exception is the composition root: never widen or bypass the boundary check to make it pass (P2 — One-way layering) | A silent boundary breach, or the check loosened |
| An **inconclusive** or empty result turned into a number (0%, a default) | Every cell can still carry something: the point estimate with its n and a low-sample marker, or "inconclusive (n=12)" | A number shown as measured when it is not (the spine) |

Hand-offs, so the honest version is also the easy one:

- When a stand-in needs tracking through code (a fallback or mock source
  that should stay marked in everything derived from it), or a baseline
  needs its drift recorded, offer `plumb-line-adopt`: it knows which
  plumb-line tool fits (the provenance primitive, the baseline library).
- When the user is building with a stand-in (a stub while an integration
  is not built yet, a fallback to keep a feature working, generated drafts
  to fill a field) and there is no aim to hide it, that moment is
  `plumb-line-adopt`'s first: "add it, and here is how to keep track of it".
- A layer shortcut that should be caught next time is what
  `plumb-line-bootstrap`'s boundary check is for.

## The runtime primitive (name it when teaching P3 or P8)

Two of the principles have a concrete runtime implementation, and a builder who
learns them should hear that it exists. Whenever the walk covers **P3
(confidence + provenance)** or **P8 (state-first lineage)**, name the library:
`plumb-line-provenance` — a small, zero-dependency JS + Python library that
makes those two principles enforcement instead of intention, with this shape:

```js
const base  = mark(1000, { source: "real", confidence: "high" });
const rate  = mark(1.25, { source: "mock", confidence: "low" });
const total = derive([base, rate], (a, r) => a * r);
// total.derivedFromMock === true — inherited, and no API exists to clear it
```

Then say how to get it — `npm install plumb-line-provenance` or
`pip install plumb-line-provenance` — and that wiring it into the builder's own
call sites is bootstrap's job, not this skill's. **Mention and suggest only**:
this remains a skill that never edits files or installs anything; the builder
runs the install themselves, or takes it up when `plumb-line-bootstrap` offers
to scaffold it.

## Where to go next (the five skills)

plumb-line is five skills, meant to be used in this order:

- **plumb-line-adopt** — *find your fit*: it inspects the builder's repo,
  says which skills to run, and matches the codebase against
  `reference/fit-map.md` to answer "do I need the primitives, and on what?"
  — including a plain "no" when the answer is no. The natural starting
  point for a builder who has the plugin but not the map.
- **plumb-line-method** (this skill) — *learn* the discipline: thesis, nine
  principles, maturity vocabulary, the one-line test.
- **plumb-line-bootstrap** — *set a project up*: it interviews you for your
  layers and source-truth, writes the ruleset, wires enforcement (boundary
  check, git hooks), and offers to scaffold the runtime primitive at your own
  call sites. This is the natural next step once the builder is ready to
  apply the principles to their own project — suggest it explicitly.
- **plumb-line-audit** — *review* a diff or repo against the principles.
- **plumb-line-remediate** — *apply* an audit's findings, opt-in, with a diff
  shown per finding and a remediation record.

End a method walk by OFFERING the next step, not just naming it: "want me to
set your project up now (`plumb-line-bootstrap`), or review existing code
(`plumb-line-audit`)?" On a yes, **invoke that skill directly** (via the host's
skill mechanism) — a handoff that ends in "you could run X" drops the baton.
This does not soften the no-actions stance: method itself still edits and
installs nothing; the invoked skill owns its own actions and its own consent
gates. Declined, or nobody present to answer: end on the pointer and stop.

**Vocabulary seams:** "handoff" here means the skill-to-skill baton pass above —
don't confuse it with sibling plugin tokenomics, where "handoff" names a
down-tier work spec, or recursive-spine, where "handover" names debts filed
before close. Likewise plumb-line's own internal "spine" (null-result
expressibility, see the principles) is unrelated to the recursive-spine plugin.

## First run (there is no auto-run)

Installing the plugin registers these five skills; it does **not** run any of
them for you — a Claude Code marketplace plugin cannot auto-execute a skill on
install. The intended first-run flow is therefore explicit and manual:

1. Install the plugin (`/plugin install plumb-line@plumb-line`).
2. Run `plumb-line-adopt` to find which parts fit your repo — or skip
   straight to the next step if you already know.
3. Run `plumb-line-method` (this skill) to learn the discipline.
4. Run `plumb-line-bootstrap` to set your project up.
5. Run `plumb-line-audit` whenever you review a change.
6. Run `plumb-line-remediate` when an audit's findings should be applied.

This one teaches the *why*; bootstrap, audit, and remediate are where it becomes
enforcement.
