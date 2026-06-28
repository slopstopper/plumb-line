# plumb-line — design spec

**Date:** 2026-06-28
**Status:** design approved, pre-implementation
**Type:** Claude Code plugin (skill collection + enforcement adapters)

## Thesis

**Epistemic honesty — including the honesty of a null result — enforced by tooling
and preserved across time, not vibes.**

A plumb line finds true vertical by gravity alone. It asserts nothing; it measures.
This collection helps a builder give *any* repository the same property: a clear
source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs,
and rules enforced by machines rather than goodwill.

It is the portable, domain-neutral distillation of the discipline developed in the
Veska Index project. **Veska is one example, never the subject.** No shipped
artifact contains domain vocabulary (no astronomy, no celestial/natal/ephemeris
terms). Domain specifics appear only in clearly-labelled examples.

## Origin

This system was extracted from an observation-first research prototype whose core
rule was *"record first, compare after, interpret cautiously."* The transferable
insight is not the domain — it is the **way of building**: keep layers separate,
keep uncertainty visible, never launder approximate data into clean truth, and make
those guarantees enforced rather than advisory.

## Who plumb-line is for

plumb-line is for builders whose **outputs are claims** — where being confidently
wrong is worse than being honestly uncertain. If a number, score, or finding your
code emits becomes someone's decision, this discipline is for you.

Concretely, it fits:

- **Research & scientific-software builders** — anyone whose code produces findings
  others will trust, and for whom *"no effect found"* must be a valid, expressible
  result.
- **Data & ML practitioners** — pipelines that mix measured data with
  imputed/synthetic/mock values, model outputs that carry confidence, results that
  must be reproducible from recorded inputs.
- **AI & agent builders** — LLM and agent systems where hallucinated confidence and
  unprovenanced output are the core risk. plumb-line's insistence on provenance,
  quarantined fakery, and expressible uncertainty maps directly onto keeping a
  generated answer honest about where it came from and how sure it is.
- **Decision-support / analytics / dashboard builders** — where a value on a screen
  quietly becomes an action, and provenance is the difference between insight and
  rumor.
- **Domain experts encoding a methodology into software** — you already hold a
  discipline in your head; plumb-line makes the code enforce it instead of relying
  on your vigilance.
- **Solo builders & small teams without a formal review process** — who want the
  discipline baked into hooks and lint, not dependent on remembering.
- **Anyone inheriting or auditing a codebase** — who needs to know, fast, what's
  real vs mock vs assumed.

**The disposition it rewards:** you'd rather ship *"we don't know yet"* than a
confident guess; you treat auditability as a feature; you're suspicious of numbers
without provenance.

**Strongest fit vs lighter fit.** plumb-line earns its keep in proportion to a
project's epistemic risk — how much it matters that an output is honest about its
own certainty and origin. Strongest fit: projects whose outputs are trusted claims
(research, data/ML, AI/agents, decision-support). Lighter fit: throwaway spikes
where speed beats honesty and nothing downstream trusts the output; projects with
little notion of truth or uncertainty (a purely aesthetic site, a game with no data
claims); teams already saturated with formal verification. plumb-line adds
discipline — where epistemic risk is low, apply it lightly or not at all.

## Goals

- Let any builder, in any repo and (v1) any of two languages, adopt this discipline.
- Keep the philosophy in exactly one place; have skills reference it, not restate it.
- Guarantee domain-agnosticism *by construction*, and prove it in our own tests.
- Be honest about our own maturity (which adapters are current vs planned).

## Non-goals

- Not a linter or a framework. It generates and installs config; it is not the runtime.
- Not opinionated about a project's domain, business logic, or tech choices beyond
  the discipline itself.
- Not a replacement for human review — the audit skill surfaces findings, it does
  not auto-fix.

## Packaging (Approach A — a collection)

A Claude Code plugin: an umbrella/teaching skill, two working skills, a single
shared principles document, and pluggable per-language enforcement adapters.

```
plumb-line/
  .claude-plugin/plugin.json          plugin manifest
  skills/
    plumb-line-method/SKILL.md        philosophy + principles + glossary (teaching)
    plumb-line-bootstrap/SKILL.md     interview -> ruleset -> install enforcement
    plumb-line-audit/SKILL.md         audit a diff/repo against the principles
  reference/
    portable-principles.md            the ONE source of the thesis + principles
    ruleset-template.md               domain-neutral AGENTS-style template
  adapters/
    adapter-contract.md               what any enforcement adapter must provide
    js/                               ESLint boundary rule + Vitest gate + guard hooks
    python/                           import-linter contract + pytest gate + guard hooks
  examples/                           same principles in 2-3 unrelated domains
  docs/specs/                         this document
```

**Design rule:** the disciplines are written once in `reference/portable-principles.md`.
The three skills *reference* it; they never restate it. This keeps each skill small
and prevents the philosophy from drifting between skills.

## The portable principles (the substance)

Each was lifted off its original domain into an abstract principle plus a
"find your version" prompt the bootstrap skill asks the builder.

1. **Source-truth layer.** Every system has a layer where measured/ground-truth
   data lives. Name it; forbid derived, symbolic, or mock logic inside it.
   *Prompt:* "What is your measured/ground-truth layer? What must never leak into it?"
2. **One-way layering.** Declare a one-way dependency direction; enforce it with
   tooling, not etiquette. Allow exactly one named exception (the composition root).
   *Prompt:* "What are your layers, top to bottom? What's the one allowed exception?"
3. **Confidence + provenance.** Anything that influences a downstream decision
   carries where it came from and how sure you are.
   *Prompt:* "What flows downstream? Tag each with origin + confidence."
4. **Quarantined fakery.** Mock/approximate/fallback/cached data is contained,
   labelled, and excluded from outputs unless explicitly opted in.
   *Prompt:* "Where do you use non-real data? How is it marked and kept out of exports?"
5. **Injectable priors.** Assumptions and tunable constants are injected config with
   versioned defaults — never magic numbers buried in logic.
   *Prompt:* "What constants encode a judgment call? Lift them to versioned config."
6. **Maturity vocabulary.** A shared, domain-neutral vocabulary for honesty about
   maturity: current / partial / mock / planned / not-implemented. Provided as-is.
7. **Contracted outputs.** Public outputs have a versioned, validated, named shape.
   *Prompt:* "What are your public output shapes? Give each a validator + version."
8. **State-first lineage.** Store the conditions that produced an output, not just
   the conclusion — an output you can't regenerate from recorded inputs is a claim
   you can't audit.
   *Prompt:* "For each important output, what inputs must be recorded to reproduce it?"
9. **Golden baseline + explain-the-drift.** Pin derived outputs in a baseline; any
   change forces an explanation of which input moved. Honesty enforced over time.
   *Prompt:* "Which derived outputs should be frozen, so drift must be justified?"

**The spine (into the thesis):** a null result is a first-class outcome. "No
structure found" / "no effect" / "inconclusive" must be expressible and honored —
this is what separates an instrument from a result-generator.

**The one-line test (the universal gut-check):**
*"What state produced this output, and are we preserving it honestly?"*

(Two secondary principles from the origin project — experimental-vs-real separation
via a per-record mode flag, and privacy/data-minimization as a structural default —
are not headline principles, but bootstrap may add them to a generated ruleset when
a project needs them.)

## The skills

### plumb-line-method (umbrella / teaching)
- **Triggers:** "teach me the plumb-line method"; auto-referenced by the other skills.
- **Behavior:** loads `reference/portable-principles.md` — thesis, principles,
  maturity vocabulary, the one-line test. Pure knowledge; takes no actions.

### plumb-line-bootstrap (starting a project)
- **Triggers:** "set up this project with the plumb-line discipline."
- **Behavior:**
  1. Detects the project language (selects the enforcement adapter).
  2. Interviews the builder via the "find your version" prompts.
  3. Generates a filled, domain-neutral ruleset from `ruleset-template.md`.
  4. Installs the selected adapter's enforcement: boundary check, test gate,
     pre-commit gate, branch guard — parameterized to the builder's layers/paths.
- **Honesty constraint:** ships no default layers and invents no answers. If the
  builder cannot name their source-truth layer, that is the finding; the skill
  surfaces it rather than guessing. (It eats its own dog food.)

### plumb-line-audit (auditing)
- **Triggers:** "audit this against the plumb-line principles"; pointed at a diff/repo.
- **Behavior:** dispatches read-only checks (generalized from the origin project's
  provenance-auditor and layer-boundary-reviewer subagents): laundered uncertainty,
  boundary leaks, hardcoded priors, overstated maturity, outputs lacking recorded
  lineage, baseline drift with no explanation.
- **Reporting:** audit format — findings surfaced not buried, each tagged with the
  principle it violates. Read-only; never auto-fixes.

## Domain-agnosticism — guaranteed by construction

1. **Zero domain vocabulary** in shipped artifacts; domain terms appear only in
   labelled examples.
2. **Bootstrap derives structure, never assumes it** — no default layers; builds
   from the interview.
3. **Parameterized enforcement** — adapters take layer names/paths/directions as
   generated config; no hardcoded source paths.
4. **Worked-examples directory** — the same principles in 2-3 unrelated domains
   (e.g. a payments service, a data pipeline, an ML-training repo).
5. **Proven in our own tests** — the bootstrap dogfood repos are deliberately
   non-origin-domain, in *both* supported languages.

## Enforcement adapters (language portability)

The principles are language-neutral; enforcement is not. v1 ships **two real
adapters** (JS/TS and Python) to force the abstraction to survive a second language
before shipping.

**Adapter contract** (`adapters/adapter-contract.md`) — every adapter supplies:
1. **Boundary check** — enforces the one-way layering (JS: ESLint
   `import/no-restricted-paths`; Python: `import-linter` contracts).
2. **Test gate** — runs the suite (JS: Vitest; Python: pytest).
3. **Pre-commit gate** — blocks a commit if build/test/lint fail.
4. **Branch guard** — blocks the first code edit on a protected branch.

Adding a language later means writing one adapter against this contract and touching
nothing else. Non-shipped languages are labelled **planned** per the maturity
vocabulary — the collection applies its own discipline to itself.

## Testing / validation

A skill collection's "tests" are dogfooding + trigger checks:
- **Bootstrap:** run against a non-origin-domain toy repo in *each* language
  (a JS payments-style repo and a Python pipeline-style repo); confirm it produces
  a coherent ruleset and working enforcement.
- **Audit:** point at a known-good repo (quiet) and a deliberately-broken fixture
  (finds the planted violations) in each language.
- **Trigger accuracy:** validate skill descriptions with skill-creator eval tooling
  if rigor is wanted.

## Open questions / future

- Worked-examples count (2 vs 3) and which domains.
- Whether `plumb-line-audit` should optionally emit machine-readable findings.
- Additional adapters (Go, Rust) — explicitly **planned**, not v1.
