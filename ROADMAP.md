# Roadmap

Planned features for future versions. The **Milestones** section below is the
authoritative version→work index; the **Planned** section holds the detail for
each numbered item (item IDs are stable — GitHub issues reference them as
"ROADMAP #N"). GitHub milestones track issue-level status.

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
  fix (GH #101, closing the v0.4.1 waiver); report-format v2→v3. **The other two
  planned themes did NOT make 0.5.0** — remediation handoff (#20 / GH #88) and
  onboarding (#21 / GH #89) moved to v0.5.1 below. Recorded as-shipped rather than
  backfilled: 0.5.0 went out narrower than this milestone first scoped, so the
  milestone is split honestly instead of the tracker pretending it was complete.

- **v0.5.1 — Audit you can act on (completes 0.5.0's theme).** The two themes cut
  from 0.5.0: lightweight remediation handoff — audit offers to hand findings to
  `writing-plans` / plan mode and suggests bootstrap on a provenance gap (#20 /
  GH #88); onboarding polish — bootstrap suggested from method, three-skill
  cross-links, and a documented first-run flow (#21 / GH #89). Skill-surface →
  runs the release harness.

- **v0.6.0 — Apply the discipline.** Close the two-halves gap: bootstrap scaffolds
  the primitive and method names it (#6), and a new `plumb-line-remediate` skill
  applies audit findings (#11 / GH #57). Depends on `report-format: v1` (GH #28,
  shipped).

- **v0.7.0 — Lower the on-ramp** (runtime + wire v2). Static lint for untagged
  outputs (#1 / GH #91), ecosystem adapters (#2 / GH #92), `PROVENANCE_VERSION`
  per-envelope embedding (#5 / GH #93), durable/stable lineage step IDs — the
  wire-format break, `PROVENANCE_VERSION` → 2 (GH #52), lint injection path
  (#10 / GH #29), dual-import hardening (GH #24). The wire-v2 break lives here.

- **Portable beyond Claude** (parallel track, version TBD). Agent-neutral method
  core + agent-adapter contract (#12 / GH #58), MCP server exposing the three
  skills (#13 / GH #59, deps #12), per-host rule-file packs (#14 / GH #60).
  Orthogonal to the release train — can run alongside the versions above.

- **Backlog** (unversioned). Guaranteed total-sweep audit via subagent fan-out,
  with a token-cost warning (#22 / GH #90); IDE integration (#3); Go and Rust
  ports (#7); relocate `provenance-lint` to `primitives/` (#8).

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
*offer* slice (**v0.5.0**, no schema dependency) is two issues by responsibility —
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
(v0.5.0 — no schema dependency, shippable now), split by skill responsibility;
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

## Deferred — Known Issues

The v0.2.0 / v0.3.0 dogfood deferrals #23, #25, and #26 have shipped — see
[CHANGELOG.md](CHANGELOG.md). One remains open and is folded into the runtime
milestone:

| # | Summary | File | Milestone |
|---|---------|------|-----------|
| #24 | Dual-import shim can be displaced by a top-level `provenance.py` in a consumer project | `primitives/python/{marked,audit}.py` | v0.7.0 |

A separate totality-parity bug (`audit_meta` throws on falsy-but-not-`None`
input; GH #80) is scheduled for v0.4.1.

---

## Completed

See [CHANGELOG.md](CHANGELOG.md) for shipped work.
