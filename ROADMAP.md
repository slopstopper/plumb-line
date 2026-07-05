# Roadmap

Planned features for future versions. The **Milestones** section below is the
authoritative version→work index; the **Planned** section holds the detail for
each numbered item (item IDs are stable — GitHub issues reference them as
"ROADMAP #N"). GitHub milestones track issue-level status.

## North star

The long-run identity (status: **planned** — this names direction, not current
capability): plumb-line is **the epistemic honesty layer for agent-built
software**, with the provenance library as its runtime enforcement arm. Three
horizons: (1) deepen the existing promise — P9 tooling, boundary gates,
CI-native enforcement (v0.8.0–v0.9.0); (2) make provenance a property of a
*system*, not a process — taint that survives serialization, files, and HTTP
(Provenance across boundaries); (3) make honest self-reporting a spec any agent
can adopt — coverage maps, honest denominators, and envelopes on agent-produced
claims (Agent epistemic state). What is **current** is exactly what the README
Status section says; everything in this file is planned until CHANGELOG says
otherwise.

---

## Milestones

Version themes for the near-term releases, and the GitHub issues under each.

- **v0.4.0 — Contracted, verifiable outputs** · *shipped 2026-06-30.*
  `validateEnvelope` (#4 / GH #27), reproducible report header + `report-format:
  v1` (#9 / GH #28), documented `basis` convention (GH #26). Additive;
  `PROVENANCE_VERSION` stayed 1.

- **v0.4.1 — Legible audit** (patch). First-tester UX pass on `plumb-line-audit`:
  principle glossary + inline names (#15 / GH #83), canonical report format —
  always a table, Path/Line/Function split, Suggested Fix column (#16 / GH #84),
  report-file determinism (#17 / GH #85), README marketplace-install-first
  (#18 / GH #86), plus the `audit_meta` totality parity bug (GH #80). Method-
  surface → runs the release harness.

- **v0.5.0 — Audit you can trust and act on** · *shipped 2026-07-03 (partial —
  see note).* Coverage honesty — up-front traversal plan + read/partial/not-read
  coverage map + honest denominator (#19 / GH #87) — plus the spine calibration
  fix (GH #101, closing the v0.4.1 waiver); report-format v2→v3. **The rest of the
  milestone's planned scope did NOT make 0.5.0** — remediation handoff (#20 / GH #88) and
  onboarding (#21 / GH #89) moved to v0.5.1 below. The adopt-the-primitive offer
  slice (method names it, GH #106; bootstrap teaches it, GH #107; from item #6)
  moved to v0.6.0. Recorded as-shipped rather than
  backfilled: 0.5.0 went out narrower than this milestone first scoped, so the
  milestone is split honestly instead of the tracker pretending it was complete.

- **v0.5.1 — Audit you can act on (completes 0.5.0's theme).** The two themes cut
  from 0.5.0: lightweight remediation handoff — audit offers to hand findings to
  `writing-plans` / plan mode and suggests bootstrap on a provenance gap (#20 /
  GH #88); onboarding polish — bootstrap suggested from method, three-skill
  cross-links, and a documented first-run flow (#21 / GH #89). Skill-surface →
  runs the release harness.

- **v0.6.0 — Apply the discipline.** Close the two-halves gap: the adopt-the-
  primitive offer slice — method names the primitive (GH #106) and bootstrap
  teaches it (GH #107), **deferred here from v0.5.0** — plus the bundle slice
  (GH #99, gated on wire v2), all from item #6; and a new `plumb-line-remediate`
  skill applies audit findings (#11 / GH #57). Depends on `report-format: v1`
  (GH #28, shipped).

- **v0.7.0 — Lower the on-ramp** (runtime + wire v2). Static lint for untagged
  outputs (#1 / GH #91), ecosystem adapters (#2 / GH #92), `PROVENANCE_VERSION`
  per-envelope embedding (#5 / GH #93), durable/stable lineage step IDs — the
  wire-format break, `PROVENANCE_VERSION` → 2 (GH #52), lint injection path
  (#10 / GH #29), dual-import hardening (GH #24). The wire-v2 break lives here,
  and so must the source-ladder decision: an `inferred` (LLM/agent-produced)
  slot or a profile mechanism, decided **before** v2 tags (#23 / GH #116) —
  it is the last cheap chance to touch the ladder.

- **v0.8.0 — Honest over time** (P9 tooling + CI-native). Principle 9 finally
  gets an implementation: `plumb-line baseline` CLI — golden baseline with
  lineage-attributed drift (#24 / GH #117); a GitHub Action running the
  deterministic adapters with SARIF output (#25 / GH #118); a provenance
  ratchet — "no *new* untagged outputs vs. main" — for incremental adoption on
  legacy codebases (#26 / GH #119, deps #1). Deterministic-only, no
  wire-format dependency: **can start alongside v0.7.0**.

- **v0.9.0 — Refuse and explain** (runtime gates + legibility). The runtime
  learns to say no and to explain itself: egress guard `require()` (#27 /
  GH #120), `explain()` human-readable lineage + Mermaid/DOT (#28 / GH #121),
  `summarize()` trust summary for artifacts (#29 / GH #122), pytest/vitest
  quarantine plugins (#30 / GH #123). Sequenced after wire v2 so new envelope
  fields are settled; every primitive lands in both languages with conformance
  rows.

- **Portable beyond Claude** (parallel track, version TBD). Agent-neutral method
  core + agent-adapter contract (#12 / GH #58), MCP server exposing the three
  skills (#13 / GH #59, deps #12), per-host rule-file packs (#14 / GH #60).
  Orthogonal to the release train — can run alongside the versions above.

- **Provenance across boundaries** (parallel track, version TBD; starts after
  wire v2). Taint must survive process boundaries or the guarantee only holds
  in-memory: canonical JSON serialization convention (#31 / GH #124),
  file-artifact sidecars (#32 / GH #125, deps #31), HTTP provenance-context
  header (#33 / GH #126, deps #31).

- **Agent epistemic state** (parallel track, version TBD; the identity track —
  can start early, it is skill-surface with no runtime dependency beyond the
  ladder decision). Generalize the audit skill's coverage-map / honest-
  denominator machinery into a versioned spec for honest agent self-reporting
  (#34 / GH #127), and a convention + Claude Code hook so agent-produced claims
  and code carry envelopes (#35 / GH #128, deps #23, #34).

- **Ecosystem docking** (parallel track, demand-driven — design notes first,
  code when a real user asks). OpenLineage exporter (#36 / GH #129), W3C PROV-O
  vocabulary mapping (#37 / GH #130), dbt model-level tags through the DAG
  (#38 / GH #131).

- **Backlog** (unversioned). Guaranteed total-sweep audit via subagent fan-out,
  with a token-cost warning (#22 / GH #90); IDE integration (#3); Go and Rust
  ports (#7); relocate `provenance-lint` to `primitives/` (#8); type-level
  enforcement — `Marked<T>` branded type + mypy plugin (#39 / GH #132, behind
  v0.9.0).

### Priority order

The sequencing rule: **finish the audit-trust arc first** (v0.5.1 → v0.6.0,
already scoped — the only external user adopted the audit skill), then take the
one-shot schema window (v0.7.0 + the ladder decision), then the two new
deepening milestones. Parallel tracks interleave by their stated dependencies:

1. **Now:** v0.5.1, then v0.6.0 (unchanged scope).
2. **Next:** v0.7.0 — with #23 (ladder decision) added as a hard rider on the
   wire-v2 tag. v0.8.0 may start in parallel (no wire dependency).
3. **Then:** v0.8.0 → v0.9.0.
4. **Parallel, start early:** Agent epistemic state (#34 first; #35 after the
   ladder decision) and Portable beyond Claude — both skill-surface.
5. **Parallel, after wire v2:** Provenance across boundaries (#31 → #32/#33).
6. **Opportunistic:** Ecosystem docking — PROV-O mapping (#37) is cheap and
   credibility-bearing, do it whenever; OpenLineage/dbt wait for a pilot user.

---

## Planned

### 1. Static lint for untagged output-producing functions

**Priority: high** · Milestone: v0.7.0 · GitHub: #91

The provenance primitive is fully opt-in: a developer can write
`const result = a.value + b.value` and bypass taint propagation entirely. The
existing `plumb-line-audit` skill can catch this in review, but it is
LLM-probabilistic, not deterministic.

Add a static AST-level pass that identifies functions which *produce* a return
value but never call `mark` or `derive`. This inverts the model from opt-in to
opt-out: provenance is assumed required on output-producing functions, and
absence is a lint error.

Scope:
- JS: ESLint rule (extend `provenance-lint/`) that flags functions returning a
  value without a `mark`/`derive` call on the return path
- Python: extend `adapters/python/provenance_lint.py` with an equivalent AST
  visitor
- Update `primitives/conformance/` to cover the new checker condition
- Hook into `adapters/*/hooks/pre-commit-gate` so untagged outputs block commit

---

### 2. Ecosystem adapters for common data sources

**Priority: high** · Milestone: v0.7.0 · GitHub: #92

Taint propagation in security tools works because common sources (HTTP
requests, user input, env vars) are pre-tagged — developers don't mark every
individual call. plumb-line currently requires manual instrumentation at every
call site, which is a steep on-ramp for data/ML teams.

Build thin wrappers that auto-tag values at the point of ingestion:

- **Python:** `pandas` adapter — `PlumbDataFrame` wraps a DataFrame with a
  provenance envelope; operations that combine frames propagate taint
  automatically via `combineProvenance`. Similar wrapper for `numpy` arrays.
- **Python:** `requests`/`httpx` adapter — responses tagged `source: real` or
  `source: fallback` based on status code / cache header.
- **JS:** `fetch` adapter — same pattern; tags the resolved value before
  returning to the caller.

Each adapter ships as an optional extra in the respective package so the zero-
dependency core is not affected.

---

### 3. IDE integration

**Priority: medium** · Milestone: Backlog

Real-time provenance feedback at development time would change the adoption
curve. Right now enforcement is at commit time (git hooks) or review time
(Claude skill). A developer writing code has no inline signal.

- **VS Code extension:** inline decorations showing the provenance envelope on
  a hovered variable; warning gutter icons for untagged outputs or tainted
  values flowing into exports
- **Language server protocol:** surface `auditMeta` violations as diagnostics
  so any LSP-capable editor benefits (JetBrains, Neovim, etc.)
- **Quick-fix:** code action to wrap an untagged return in `mark()`/`derive()`
  with a prompt for source + confidence

---

### 4. `validateEnvelope` structural field-presence checker

**Priority: medium** · GitHub: #27 · **Shipped in v0.4.0**

`auditMeta({})` returned `[]` for an empty envelope — it passed silently even
though required fields (`source`, `confidence`, `lineage`, `derivedFromMock`)
were absent. `validateEnvelope(meta)` now checks required field presence and
correct types before any combination or audit logic runs, in both JS and Python,
with conformance coverage.

---

### 5. `PROVENANCE_VERSION` per-envelope embedding and validation

**Priority: medium** · Milestone: v0.7.0 · GitHub: #93

This is a wire-format change, so it rides the v0.7.0 wire-v2 bump alongside GH
#52 (durable step IDs) rather than shipping on its own.

`PROVENANCE_VERSION` is exported from both `primitives/js/provenance.mjs` and
`primitives/python/provenance.py` but is not embedded in individual envelopes
at creation time and is not validated on read. Consumers cannot tell which
schema version produced an envelope they receive.

Embed `PROVENANCE_VERSION` in every envelope produced by `makeMeta` /
`combine`. Add validation in `auditMeta` (or `validateEnvelope`) that the
version field is present and matches the running library version. Document the
forward-compatibility policy: unknown future versions are allowed through with a
warning; unknown past versions are flagged.

---

### 6. Adopt the primitive from the skills (bootstrap + method)

**Priority: medium** · Tracked as three issues across a skill-scoped split. The
*offer* slice (**v0.6.0** — originally scoped to v0.5.0, deferred when 0.5.0
shipped narrower; no schema dependency) is two issues by responsibility —
**method** introduces the primitive + suggests getting it
([#106](https://github.com/effythealien/plumb-line/issues/106)), **bootstrap**
teaches how to use it in the user's codebase
([#107](https://github.com/effythealien/plumb-line/issues/107)); the onboarding
handoff between them is [#89](https://github.com/effythealien/plumb-line/issues/89).
The *bundle* slice
([#99](https://github.com/effythealien/plumb-line/issues/99), **v0.6.0**, gated on
the wire-v2 release) makes that download frictionless.

The `plumb-line-bootstrap` skill generates an `AGENTS.md` ruleset and installs
enforcement adapters, but it does not wire the provenance primitive into the
host project, and `plumb-line-method` teaches the confidence/provenance and
lineage principles without naming the library that implements them. A
less-technical user who installs only the plugin never learns there is a runtime
primitive to adopt — the two halves stay decoupled and the value is left on the
table.

Close the gap from the skill side. The first two bullets are the *offer* slice
(v0.6.0 — deferred from v0.5.0; no schema dependency), split by skill responsibility;
the third is the *bundle* slice
([#99](https://github.com/effythealien/plumb-line/issues/99), v0.6.0, gated on
wire v2):
- **Method — introduce + suggest download:** when teaching P3 (confidence +
  provenance) or P8 (lineage), name the runtime library as the concrete
  implementation, with the three-line `mark`/`derive` example, and suggest how to
  get it. A bounded softening of method's "takes no actions" stance — mention and
  suggest, don't install. ([#106](https://github.com/effythealien/plumb-line/issues/106))
- **Bootstrap — teach usage in the codebase:** after the interview, offer to
  scaffold `mark`/`derive` at the exact call sites the answers surfaced (Q4
  downstream values, Q8 lineage-bearing outputs) and teach the usage pattern.
  Opt-in prompt, not silent wiring. Hook `validateEnvelope` into the pre-commit
  gate so unmarked returns are caught before they reach review. ([#107](https://github.com/effythealien/plumb-line/issues/107))
- **Bundle the primitive source in the plugin** so adoption needs no separate
  `npm`/`pip` step. The modules are zero-dependency and copy-pasteable (dual-import
  shim), so bootstrap can drop them in directly. Soft-depends on the wire-v2
  release: bundle once the schema has settled at v2, to avoid vendoring
  v1 and re-vendoring. (#99)

Tracked as a consequence of ADR-0005; the integration was deliberately deferred
to keep that decision scoped to the primitive itself.

---

### 7. Go and Rust adapters

**Priority: low** · Milestone: Backlog

JS and Python ship at v0.1; Go and Rust are the next planned ports. Each new
language adapter must:

- Implement the combination law from `primitives/SPEC.md`
- Pass the full `primitives/conformance/cases.json` suite
- Provide the five adapter contract capabilities from
  `adapters/adapter-contract.md` (boundary check, test gate, pre-commit gate,
  branch guard, provenance-bypass lint)

---

### 8. Move `provenance-lint` from `adapters/` to `primitives/`

**Priority: low** · Milestone: Backlog

The provenance-bypass lint rules (`adapters/js/provenance-lint/` and
`adapters/python/provenance_lint.py`) check correct *use* of the primitive
library specifically, not domain-neutral architectural boundaries. They are
library-coupled in a way the boundary/branch/pre-commit hooks are not.

Relocating them to `primitives/` makes the coupling explicit and keeps
`adapters/` reserved for domain-neutral enforcement. Both source files note
this move as a future possibility.

---

### 9. Audit report header block

**Priority: low** · GitHub: #28 · **Shipped in v0.4.0**

The output of `plumb-line-audit` lacked a header recording scope, principles
version, date, and git SHA. A required header block plus `report-format: v1`
versioning now let a saved audit report be re-verified and parsed reliably.

---

### 10. Configurable primitive module/function names in provenance lint

**Priority: low** · Milestone: v0.7.0 · GitHub: #29

`PRIMITIVE_MODULES` and `TRACKED` function lists in both the JS ESLint rule
and the Python AST checker are hardcoded. Projects that re-export the
primitive under a different name (e.g., `import { mark } from '@myorg/data'`)
get no lint coverage without patching the source.

Add an injection path (ESLint rule option / Python checker argument) so callers
can extend the tracked module and function lists. This also makes the linter
reusable for third-party primitives that follow the same envelope contract.

---

### 11. `plumb-line-remediate` skill — apply audit findings

**Priority: high** · Milestone: v0.6.0 · GitHub: #57 · depends on #9 (GH #28)

The skills teach (method), set up (bootstrap), and find (audit) — but nothing
applies a fix. `plumb-line-audit` is deliberately read-only, so after it reports
"P3 laundered uncertainty at `foo.ts:42`" the builder is on their own. Keeping the
auditor read-only is worth preserving — review you can trust does not mutate — so
remediation belongs in a separate skill, not folded into audit.

`plumb-line-remediate` consumes a machine-readable audit report (the
`report-format: v1` from #9) and applies the mechanical fixes: wrap an untagged
return in `mark`/`derive`, lift a magic number to injected config (P5), add a
validator + version to an uncontracted output (P7), add lineage recording (P8),
relabel overstated maturity (P6). It shows diffs and never silently edits. The
lightweight handoff shipped in v0.5.0 (#20) is the on-ramp to this full skill.

HONESTY GUARDRAIL: a remediation may never resolve a finding by making the code
*less* honest — clearing a taint flag, deleting a null-result branch, or dropping
a confidence field to make a check pass. That is the laundering the whole project
exists to stop; the fixer needs the same honesty constraint bootstrap has ("if
you cannot name a source-truth layer, that absence is the finding").

---

### 12. Agent-neutral method core + agent-adapter contract

**Priority: high** · Milestone: Portable beyond Claude · GitHub: #58

The discipline is already portable in substance — `reference/portable-principles.md`
is referenced, not restated; bootstrap emits `AGENTS.md` (not `CLAUDE.md`); and the
guard hooks are agent-neutral stdin/exit-code CLIs. Only the packaging and
invocation layer is Claude-specific.

Factor the three skills' instructions (the audit check catalogue, the bootstrap
interview, the method walk) into host-agnostic modules stripped of "Claude" /
"skill" / "PreToolUse" wording, and define an `agent-adapter-contract.md` — the
capabilities any host must provide (load principles, run interview, run audit,
wire hooks, invoke on a diff). This mirrors the existing language
`adapters/adapter-contract.md` one level up: Claude Code becomes one adapter
among several rather than the substrate.

---

### 13. MCP server exposing method/bootstrap/audit

**Priority: high** · Milestone: Portable beyond Claude · GitHub: #59 · depends on #12

An MCP server that exposes the three skills as tools lets any MCP-capable agent
(Codex, Cursor, Qwen, Continue) run them with zero rewrite — the highest-leverage
step toward "transferable to any agentic coder." Depends on the agent-neutral
core (#12) for the underlying instruction modules. Success test: run the audit
unmodified from a non-Claude host against the worked fixtures in `examples/`.

---

### 14. Per-host rule-file packs

**Priority: medium** · Milestone: Portable beyond Claude · GitHub: #60

Beyond `AGENTS.md`, generate the host-specific rule file for whichever agent the
builder uses — `.cursor/rules`, `.github/copilot-instructions.md`, `CLAUDE.md`,
`AGENTS.md`. Bootstrap already writes `AGENTS.md`; generalize that step into
"emit the rule file for the detected host." Pairs with the agent-adapter contract
(#12).

---

### 15. Audit: principle legibility — glossary + inline names

**Priority: high** · Milestone: v0.4.1 · GitHub: #83

From first-tester feedback: `P1/P2/...` codes are opaque to infrequent users, and
principles get explained mid-report rather than up front, leaving the reader
dangling. Open every audit with a one-line-per-principle glossary and render each
`P#` reference with its name inline (`P3 — visible uncertainty`), before use.

---

### 16. Audit report format — canonical structure

**Priority: high** · Milestone: v0.4.1 · GitHub: #84

The report shape varies run to run — sometimes a structured table, sometimes
blocks of prose — a non-deterministic artifact that cannot be reliably diffed or
parsed (the same reproducibility property the skill demands of reviewed code).
Pin one canonical structure: the findings section is **always** a table; replace
the ambiguous `Site` column with **Path / Line / Function**; add a **Suggested
Fix** column after **Issue**.

---

### 17. Audit report-file determinism

**Priority: medium** · Milestone: v0.4.1 · GitHub: #85

The skill sometimes writes `plumb-line-audit.md` and sometimes does not. Pick one
contract (always write, or always offer) and make it deterministic — the
coin-flip is itself a small honesty violation.

---

### 18. README — marketplace install first

**Priority: medium** · Milestone: v0.4.1 · GitHub: #86

Promote the marketplace install path to the top of the install section as the
least-friction on-ramp (first-tester note); keep manual/dev install below.

---

### 19. Audit coverage honesty — traversal plan + coverage map

**Priority: high** · GitHub: #87 · **Shipped in v0.5.0**

The auditor "confidently acts like it found everything," but on a large repo it
does not — the skill overstating its own coverage is the exact laundered-
uncertainty / overstated-maturity failure it exists to catch (P8 + the honest-
denominator spine). Emit an up-front **traversal plan**; include a **coverage
map** in the report (file tree marked read / partial / not-read); report an honest
**denominator** and caveat instead of implying completeness. "Plan + map" depth;
the guaranteed sweep is #22.

---

### 20. Audit — lightweight remediation handoff

**Priority: medium** · Milestone: v0.5.1 · GitHub: #88

At the end of a run, offer to hand findings to superpowers `writing-plans` / plan
mode for a fix-plan markdown, and — when provenance gaps appear — suggest
`plumb-line-bootstrap` (principles into the host rule file + git hooks). The
auditor stays read-only; this is an offer, not an apply. Bridges to the full
`plumb-line-remediate` skill (#11).

---

### 21. Onboarding — suggest bootstrap from method

**Priority: medium** · Milestone: v0.5.1 · GitHub: #89

Suggest `plumb-line-bootstrap` from inside `plumb-line-method` and cross-link
method ↔ audit ↔ bootstrap so first-time users find the next step. Includes a
research task: whether a marketplace plugin can auto-run `/method` on install
(likely not — plugins don't auto-execute skills); if infeasible, document the
intended first-run flow instead of promising auto-run.

---

### 22. Audit — guaranteed total sweep (subagent fan-out)

**Priority: low** · Milestone: Backlog · GitHub: #90

Fan out subagents to chunk the whole tree so large repos are genuinely fully read,
not sampled. **Must ship a token-consumption warning** — this is expensive.
Deliberately deferred beyond v0.5.0; #19's plan + map is the honest-floor version.

---

### 23. Source ladder — decide an `inferred` (LLM/agent-produced) slot

**Priority: high** · Milestone: v0.7.0 (hard rider on wire v2) · GitHub: #116

The source ladder has no seat for a value an LLM or agent estimated; teams will
shoehorn it into `semiReal` or `fallback` inconsistently. Decide **before wire
v2 tags** — it is the last cheap chance to touch the ladder: either add
`inferred`/`estimated`, or define a registered profile/extension mechanism that
preserves cross-language parity. Record as an ADR; pin with conformance cases.
The Agent epistemic state track (#35) needs a ladder position to point at.

---

### 24. `plumb-line baseline` CLI — golden baseline + lineage-attributed drift

**Priority: high** · Milestone: v0.8.0 · GitHub: #117

Principle 9 (golden baseline + explain-the-drift) currently has **no
implementation anywhere in the repo** — until this ships, P9 is
`not-implemented` and must be labelled as such wherever the principles are
presented as enforced. The CLI pins an output *with its lineage*, diffs runs,
refuses silent drift, and demands a recorded one-line explanation on update.
Differentiator vs. snapshot testing: lineage lets drift be **attributed**
("output moved because `rate` source changed real→fallback at step 3"), not
just diffed. Deterministic; both languages; no wire dependency.

---

### 25. GitHub Action + SARIF output for the deterministic adapters

**Priority: high** · Milestone: v0.8.0 · GitHub: #118

Review-time enforcement currently assumes a Claude session. A composite GitHub
Action running the boundary check, provenance lint, and (once shipped) the
baseline check — emitting **SARIF** so findings land in GitHub's native
code-scanning UI — works for every contributor regardless of agent, at zero
marginal cost. The LLM audit stays out of scope: this is the always-on
deterministic floor.

---

### 26. Provenance ratchet — no new untagged outputs vs. main

**Priority: high** · Milestone: v0.8.0 · GitHub: #119 · depends on #1 (GH #91)

The honest answer to "how does a 300k-line legacy repo adopt this?" is
currently "it can't, realistically." The proven incremental pattern from
type-coverage tooling: measure untagged output-producing functions on main,
fail CI only when a PR *increases* the count. A ratchet mode for the lint
(JS + Python) with a committed manifest, wired into the Action (#25) and the
pre-commit gate.

---

### 27. Egress guard — `require(x, { noMock, minConfidence })`

**Priority: high** · Milestone: v0.9.0 · GitHub: #120

`auditMeta` flags problems after the fact; nothing *stops* a tainted value at
the door. A small guard that throws (or returns a typed refusal) at
export/display/publish points converts the discipline from detectable to
**enforced at the boundary** — what P4 ("excluded from outputs unless
explicitly opted in") actually promises. Tiny surface; both languages;
conformance rows per predicate; failing test first.

---

### 28. `explain(envelope)` — human-readable lineage

**Priority: medium** · Milestone: v0.9.0 · GitHub: #121

Lineage is stored but not legible: no way to ask an envelope *why* it is
low-confidence and get "tainted at step 2: `rate` was mock", and no visual
form (lineage → Mermaid/DOT). The first-tester pattern — opaque codes kill
legibility — will recur at the envelope level the moment anyone debugs a real
pipeline. Debuggability is the adoption lever for the runtime half.
Deterministic output, parity-pinned.

---

### 29. `summarize(envelopes)` — trust summary for artifacts

**Priority: medium** · Milestone: v0.9.0 · GitHub: #122

One small record per artifact — % derived-from-mock, weakest source present,
confidence floor, lineage depth — printable at the bottom of any report or
export. Makes provenance visible to stakeholders who will never read an
envelope, which is what keeps instrumentation alive. **Guardrail, by design:**
never collapse this into a single scalar "honesty score" — a grade invites
gaming and is itself laundered uncertainty. Distributions and drift, never a
grade.

---

### 30. Test-harness plugins — automatic fixture quarantine

**Priority: medium** · Milestone: v0.9.0 · GitHub: #123

Tests are where fake data is *supposed* to live; make the quarantine automatic
there. A pytest plugin and vitest helper that auto-mark fixture-constructed
values `source: mock` and assert no mock taint reaches golden outputs — the
classic disaster (test fixture leaks into a prod default) caught at near-zero
adoption friction. Ships as optional extras; zero-dependency core untouched.

---

### 31. Envelope transport — canonical JSON serialization convention

**Priority: high** · Milestone: Provenance across boundaries · GitHub: #124

Envelopes are in-memory objects; taint evaporates at every HTTP response, DB
write, file, or queue — today the guarantee only holds inside one process, and
taint systems historically die exactly here (taint cleared at a serialization
boundary gets routed around). A normative SPEC section: how an envelope embeds
in a JSON payload (canonical key, camelCase wire form, version field per #5)
and how `parse`/`revive` restores it losslessly, both languages,
conformance-pinned. Foundation for #32 and #33.

---

### 32. File-artifact sidecar convention

**Priority: medium** · Milestone: Provenance across boundaries · GitHub: #125 · depends on #31

Data teams pass files around; taint dies at the file boundary. Define
`<name>.provenance.json` sidecars for CSV/parquet/JSON artifacts (whole-file or
per-column envelopes), write/read helpers in both languages, and audit-skill
awareness: an output artifact with no sidecar is a P8 finding.

---

### 33. HTTP provenance-context header

**Priority: medium** · Milestone: Provenance across boundaries · GitHub: #126 · depends on #31

Envelope context that travels across services the way W3C `traceparent`
carries trace context: a header carrying the compact envelope so a consuming
service `mark`s the received value with its true upstream provenance instead
of defaulting to `real`. Header format in SPEC.md, middleware for the
fetch/requests/httpx adapters (#2), a worked two-service example. This is the
"OpenTelemetry for certainty" claim made concrete.

---

### 34. Agent-run epistemic-state spec

**Priority: high** · Milestone: Agent epistemic state · GitHub: #127

The audit skill's coverage-honesty machinery (traversal plan,
read/partial/not-read map, honest denominator — #19) is the seed of a general
spec for **honest agent self-reporting**: what an agent read, assumed, and
skipped, at what confidence. "It confidently acts like it found everything" is
true of every agent everywhere, not just this auditor. Extract the format into
a small versioned spec (like `report-format`) that other skills — and other
tools entirely — can adopt. This is the identity track.

---

### 35. Agent-output provenance convention + hook

**Priority: high** · Milestone: Agent epistemic state · GitHub: #128 · depends on #23, #34

A convention whereby agent-produced claims and code carry envelopes:
`source: inferred` (pending #23), stated confidence, lineage recording the
evidence actually consulted (#34's denominator). Documented against SPEC.md; a
Claude Code hook that stamps provenance on agent-written artifacts; guidance in
the method skill.

---

### 36. OpenLineage exporter

**Priority: low (demand-driven)** · Milestone: Ecosystem docking · GitHub: #129

plumb-line is value-level lineage; OpenLineage is dataset/job-level. An
exporter mapping envelope lineage onto OpenLineage facets slots plumb-line into
Airflow/dbt/Marquez shops as the fine-grained complement, not a competitor.
Design note first; build when a real user asks.

---

### 37. W3C PROV-O vocabulary mapping

**Priority: medium (cheap)** · Milestone: Ecosystem docking · GitHub: #130

A documented mapping from the envelope schema to PROV-O terms
(Entity/Activity/Agent, `wasDerivedFrom`, …). A reference document, not code —
and immediate credibility with the research/scientific-software audience the
README names as primary. Lives in `reference/`.

---

### 38. dbt adapter — source/confidence through the DAG

**Priority: low (demand-driven)** · Milestone: Ecosystem docking · GitHub: #131

SQL is where most real-world derivation happens and neither primitive touches
it. Models declare `source`/`confidence` meta tags; a macro or post-hook
propagates the conservative-combination law through the DAG and surfaces the
result in docs/exposures. Largest potential audience of any adapter, furthest
from the current codebase — validate with a design note + one pilot user first.

---

### 39. Type-level enforcement — `Marked<T>` + mypy plugin

**Priority: low** · Milestone: Backlog (behind v0.9.0) · GitHub: #132

Stronger than the AST lint (#1): a TypeScript branded type `Marked<T>` and a
Python `typing.Annotated` + mypy plugin so functions declared to return
provenance-bearing values fail to *compile* when they return bare ones. The
lint finds absence heuristically; the type system proves it. They compose:
lint for gradual adoption, types for the committed core.

---

## Deferred — Known Issues

The v0.2.0 / v0.3.0 dogfood deferrals GH #23, #25, and #26 have shipped — see
[CHANGELOG.md](CHANGELOG.md). Two remain open, folded into the runtime
milestone:

| GH # | Summary | File | Milestone |
|------|---------|------|-----------|
| GH #24 | Dual-import shim can be displaced by a top-level `provenance.py` in a consumer project | `primitives/python/{marked,audit}.py` | v0.7.0 |
| GH #96 | `auditMeta`/`audit_meta` non-plain-object (Map/Date/class-instance) parity + SPEC §5 totality wording | `primitives/js/audit.mjs`, `primitives/SPEC.md` | v0.7.0 |

The related `audit_meta` totality bug on falsy-but-not-`None` input (GH #80)
shipped in v0.4.1; #96 above tracks the non-plain-object parity edge that review
surfaced next.

---

## Completed

See [CHANGELOG.md](CHANGELOG.md) for shipped work.
