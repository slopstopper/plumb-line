# plumb-line — portable principles

**Principles revision:** 1

The single source of the discipline. The three skills (`plumb-line-method`,
`plumb-line-bootstrap`, `plumb-line-audit`) reference this document; they do
not restate it. Stable `##` headings allow direct linking by section name.

This revision number identifies the ruleset an audit was run against. Bump it
whenever a principle's meaning, scope, or the maturity vocabulary changes (not
for typo fixes); audit and bootstrap reports cite it in their `report-format: v1`
header so a stored report names the exact rules it was scored under.

---

## Thesis

Epistemic honesty — including the honesty of a null result — enforced by tooling
and preserved across time, not vibes.

---

## The spine: a null result is a first-class outcome

"No structure found" / "no effect" / "inconclusive" must be expressible and
honored — not collapsed into a default, a zero, or a silence. A system that
cannot report a null result is not an instrument; it is a result-generator whose
findings are artifacts of its own assumptions. This separates honest measurement
from noise dressed as signal.

---

## The one-line test

_"What state produced this output, and are we preserving it honestly?"_

Use this as a gut-check before any change: if the change makes the system look
more certain than it is, blurs a layer boundary, hardcodes a prior, or hides
approximate data — stop and document the concern before implementing.

---

## Principle 1 — Source-truth layer

**Statement:** Every system has a layer where measured or ground-truth data
lives. Name it explicitly and forbid derived, synthesized, or fake logic inside
it.

**Why:** When the source-truth layer is unnamed, derived values and real values
mix silently. Once mixed, you cannot tell which outputs are downstream of a
measurement and which are downstream of an assumption. The only fix is a hard
boundary: this layer receives ground truth; everything else is built on top of
it, never inside it.

**Find your version:** "What is your measured/ground-truth layer? What must
never leak into it?"

---

## Principle 2 — One-way layering

**Statement:** Declare a one-way dependency direction for your layers and enforce
it with tooling, not etiquette. Allow exactly one named exception — the
composition root.

**Why:** Without a declared and enforced direction, layer boundaries erode
gradually: a utility function pulls in business logic, a display component starts
to calculate, a data file starts making decisions. By the time this is visible it
is expensive to reverse. A machine-enforced rule stops the erosion at the first
violation, before it becomes architectural debt.

**Find your version:** "What are your layers, top to bottom? What's the one
allowed exception?"

---

## Principle 3 — Confidence + provenance

**Statement:** Anything that influences a downstream decision carries where it
came from and how sure you are.

**Why:** A number without provenance is a claim without a source. When
confidence and origin travel with a value, every consumer can decide how much
weight to give it — and can propagate uncertainty forward rather than silently
discarding it. Without this, the system systematically overstates certainty the
further downstream you go.

**Find your version:** "What flows downstream? Tag each with origin +
confidence."

---

## Principle 4 — Quarantined fakery

**Statement:** Mock, approximate, fallback, and cached data is contained,
labelled, and excluded from outputs unless explicitly opted in.

**Why:** Fake data that escapes its container and enters a real output path
launders approximation into apparent truth. Once a fake value reaches an
aggregate, an export, or a displayed result, the system has made a claim it
cannot support. Containment and labelling make the fakery visible to logic,
diagnostics, and the builder — rather than hiding it behind a clean-looking
number.

**Find your version:** "Where do you use non-real data? How is it marked and
kept out of exports?"

---

## Principle 5 — Injectable priors

**Statement:** Assumptions and tunable constants are injected config with
versioned defaults — never magic numbers buried in logic.

**Why:** A constant hardcoded inside a calculation is an invisible prior. No one
reading the output knows it exists, no one auditing the code can see its
effect without hunting for it, and no one running the system can change it
without editing logic. Lifting priors to named, versioned, injectable config
makes them visible, auditable, and replaceable — so results carry the version of
the assumptions that produced them.

**Find your version:** "What constants encode a judgment call? Lift them to
versioned config."

---

## Principle 6 — Maturity vocabulary

**Statement:** Use a shared, domain-neutral vocabulary to be honest about what
your system currently is vs. what it will become.

**Why:** Undifferentiated code makes it impossible to know at a glance whether a
module is production-ready or a placeholder. When the vocabulary is shared and
consistent, any reader — including the builder six months later — can immediately
see the maturity of each part without reading the implementation. The system
applies this vocabulary to itself.

**Terms (use as-is):**

- **current** — implemented, tested, and actively maintained
- **partial** — implemented but incomplete or not fully tested
- **mock** — placeholder returning fake or hardcoded data
- **planned** — intended for a future version; not yet started
- **not-implemented** — identified as needed but explicitly deferred

_No find-your-version prompt for this principle — the vocabulary is provided
as-is and adopted without modification._

---

## Principle 7 — Contracted outputs

**Statement:** Public outputs have a versioned, validated, named shape.

**Why:** Without a contract, any consumer of a public output silently depends on
whatever shape it happens to have today. When the shape changes — or the code is
refactored, extended, or ported — nothing warns the consumer. A contract with a
version constant, a validator, and a named key list means breakage is caught at
the boundary rather than discovered when a downstream calculation silently
produces a wrong answer.

**Find your version:** "What are your public output shapes? Give each a
validator + version."

---

## Principle 8 — State-first lineage

**Statement:** Store the conditions that produced an output, not just the
conclusion. An output you cannot regenerate from recorded inputs is a claim you
cannot audit.

**Why:** Storing only the result means losing the ability to verify it, explain
it, or compare it against a future run with different inputs. State-first lineage
makes outputs reproducible, debuggable, and comparable over time — and it makes
it impossible to mistake a stale result for a fresh one, because the recorded
conditions tell you exactly what was true when the output was produced.

**Find your version:** "For each important output, what inputs must be recorded
to reproduce it?"

---

## Principle 9 — Golden baseline + explain-the-drift

**Statement:** Pin derived outputs in a baseline; any change forces an
explanation of which input moved. Honesty enforced over time.

**Why:** Without a pinned baseline, derived outputs can drift silently. A
change to a weight, a constant, or an upstream value shifts every downstream
result — and without a before-after comparison no one notices. A golden baseline
makes drift visible and forces the builder to account for it: either the new
output is correct and the baseline needs updating with an explanation, or the
drift is a bug. Either way, the system cannot pretend nothing changed.

**Find your version:** "Which derived outputs should be frozen, so drift must be
justified?"

---

## Glossary

**Source-truth layer** — the named layer of a system where measured or
ground-truth data lives. Derived, synthesized, and fake logic are forbidden
inside it (Principle 1).

**Derived layer** — any layer that produces values by transforming, combining,
or interpreting source-truth inputs. Results here are only as trustworthy as
the inputs they were built from, and should propagate that uncertainty.

**Provenance** — the recorded origin of a value: where it came from, when it
was produced, and by what process. A value without provenance is a claim without
a source (Principle 3).

**Confidence** — the expressed degree of certainty attached to a value — whether
measured, estimated, imputed, or assumed. Confidence must travel with the value
downstream rather than being silently discarded (Principle 3).

**Quarantined data** — mock, approximate, fallback, or cached data that has been
explicitly labelled and kept separate from real data paths so it cannot enter
an output unless the consumer has opted in (Principle 4).

**Prior** — an assumption or tunable constant that encodes a judgment call about
the system's behavior. Priors must be injectable config with versioned defaults,
not magic numbers buried in logic (Principle 5).

**Contract** — the versioned, validated, named shape of a public output.
A contract includes a version constant, a validator function, and a canonical
key list. Consumers depend on the contract, not the implementation (Principle 7).

**Lineage** — the full recorded chain of conditions (inputs, config, priors,
mode flags) that produced a given output. Lineage makes outputs auditable and
reproducible (Principle 8).

**Baseline drift** — the difference between a pinned golden output and the
current output of the same derivation. Drift must be explained — either the new
result is correct and the baseline is updated with a reason, or the drift is a
bug (Principle 9).

**Composition root** — the one named exception to one-way layering: the single
module allowed to import across layer boundaries in order to wire the system
together. It must be explicitly named and kept narrow (Principle 2).
