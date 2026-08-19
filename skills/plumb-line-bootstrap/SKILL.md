---
name: plumb-line-bootstrap
description: Use when setting up a project with the plumb-line discipline — interviews the builder to find their source-truth layer and layering, generates a domain-neutral ruleset, and installs parameterized enforcement (boundary check, test gate, pre-commit gate, branch guard) for the project's language. Ships no default layers and invents no answers.
---

# Bootstrap a project with plumb-line

Part of the five-skill flow: find your fit with `plumb-line-adopt`, learn the
discipline with `plumb-line-method`, set the project up here, review changes
with `plumb-line-audit`, and apply findings with `plumb-line-remediate`.

REQUIRED READING FIRST: `reference/portable-principles.md` and
`adapters/adapter-contract.md` (plugin root).
If either file cannot be read, stop immediately and report which file is missing. Do not proceed from memory.

## Two entries: full bootstrap vs. declaration-only (mid-audit)

This skill has two entry modes. **Full bootstrap** — the builder asked for
setup — runs every step below. **Declaration-only** — `plumb-line-audit`
invoked this skill because the project declares no architecture and the audit
needs that context before proceeding — runs a deliberately two-minute detour:

- Ask ONLY interview questions 1–3 (layers + direction; source-truth layer;
  composition root). The audit needs the declaration, not the ceremony.
- Write the ruleset from those answers (Step 3), marking every section the
  interview did not reach as `planned` — an un-asked question must not read as
  an answered one.
- Skip Step 4, Step 4b, and Step 6's audit offer entirely: no enforcement
  install, no primitive offer, nothing added to the project beyond the ruleset
  file. Those belong to a full bootstrap run — name it as the follow-up in the
  report's TODOs.
- Emit the Step 5 report header with one extra line — `entry: declaration-only`
  — then return the baton: the calling audit resumes with the freshly declared
  architecture (do not start a second audit).

The honesty constraint applies in both modes: if the builder cannot name a
source-truth layer, stop and say so — in declaration-only mode that answer goes
back to the audit, which then proceeds calibrated with the gap on record.

## Step 1 — Detect language, pick the adapter

- Look for `package.json` -> JS adapter (`adapters/js`).
- Look for `pyproject.toml` / `setup.py` / `requirements.txt` -> Python adapter (`adapters/python`).
- If both or neither, ASK the builder which to use. Never guess silently.

## Step 2 — Interview (one question at a time)

Ask the find-your-version prompts from the principles, in this order (ask one, wait for the answer, then proceed). Do NOT
supply defaults; these answers are the builder's, not yours:

1. Layers, top to bottom, and the one-way direction.
2. The source-truth layer, and what must never leak into it.
3. The one allowed exception (composition root), if any.
4. What flows downstream (gets provenance + confidence).
5. Where non-real (mock/fallback/cached) data is used.
6. Which constants encode judgment calls (priors to lift to config).
7. Public output shapes that need a versioned contract.
8. For each key output, the inputs needed to reproduce it.
9. Which derived outputs to freeze as a golden baseline.
10. The phrasing for a valid null result in this domain.

HONESTY CONSTRAINT: if the builder cannot name a source-truth layer, stop and
say so — that absence is the finding. Do not fabricate one.

## Step 3 — Generate the ruleset

Fill `reference/ruleset-template.md` placeholders with the answers; write it to
the target repo as `AGENTS.md` (or append if one exists — never overwrite silently).

## Step 4 — Install enforcement (from the chosen adapter)

- Copy the boundary config template, replacing layer placeholders with the
  builder's layers/direction. (JS: eslint zones; Python: import-linter layers.)
- Copy the two guard hook scripts (branch guard + pre-commit gate) into the
  target repo's `.claude/guards/` (or hooks dir).
- Wire the pre-commit gate to the adapter's declared test command.
- Tell the builder exactly what was written and how to enable the hooks.
- **Verify, don't assume.** After installing, plant a deliberate upward import
  and confirm the boundary check errors; pipe a code path to the branch guard on
  the protected branch and confirm it blocks. An installed-but-inert guard is the
  failure mode to rule out.

### JS boundary zones — get the direction right (easy to invert silently)

In `import/no-restricted-paths`, each zone reads: **`target` = the layer doing
the importing; `from` = the layer it must NOT import.** To forbid the bottom
layer importing upward, list one entry per forbidden (lower imports higher) pair:

```js
zones: [
  {
    target: "./src/data",
    from: "./src/ui",
    message: "data must not import from ui",
  },
  {
    target: "./src/data",
    from: "./src/services",
    message: "data must not import from services",
  },
  {
    target: "./src/data",
    from: "./src/engine",
    message: "data must not import from engine",
  },
  // ...repeat for services (must not import ui), engine (must not import ui/services), etc.
];
```

A reversed `{ target: "./src/ui", from: "./src/data" }` forbids the _opposite_
(ui importing data) and leaves the real upward leak unguarded — and nothing
errors, so the mistake is invisible. This is why the verify step above matters.

ESLint v9 uses flat config (`eslint.config.mjs`); the template is a `.cjs`
fragment. Load it from the flat config (import the fragment and spread its
`rules`) rather than expecting a legacy `.eslintrc` to be read.

### Branch-guard allowlist forms

The docs allowlist matches an entry in exactly three forms — no other globbing:

- exact file: `README.md`
- directory (trailing slash): `docs/` — everything under it
- extension glob: `*.md` — that extension at any depth

Empty entries are rejected. (Earlier versions matched files exactly only; a bare
`*.md` silently matched nothing — fixed, but still: prefer these three forms.)

### Hook I/O contract (for wiring)

Each guard is a stdin/exit-code CLI: it reads `{ "filePath": "..." }` on stdin,
the branch from `PLUMBLINE_BRANCH`, and config from `PLUMBLINE_CFG` (JSON), and
exits non-zero to block (per `adapter-contract.md`). It works directly as a git
hook. To wire it as a Claude Code PreToolUse hook, map the host's tool payload's
file path into the `{filePath}` stdin the guard expects — if the host payload
shape differs, add a one-line shim rather than assuming it matches.

## Step 4b — Offer the runtime primitive (opt-in; never silent)

The interview's own answers say exactly where runtime provenance belongs: **Q4**
named what flows downstream (gets provenance + confidence), **Q8** named the
lineage-bearing outputs. After enforcement is installed, make ONE explicit
offer — scaffold `mark`/`derive` from `plumb-line-provenance` at those exact
call sites — and act only on an explicit yes:

- **Declined → the project is untouched.** Record the offer as declined in the
  report and move on; no library, no marking, no new dependency appears.
- **Accepted →** ask which route the builder wants, then act on their answer —
  don't default to one silently:
  - **Install the published package** (`plumb-line-provenance` on npm / PyPI).
    Check it's importable first; if absent, tell the builder the one-line
    install and pause.
  - **Vendor the bundled source instead (no npm/pip, no network install).**
    This plugin ships the same v2 primitive under its own payload at
    `.claude-plugin/bundled/primitives/js/` (`provenance.mjs`, `audit.mjs`,
    `marked.mjs`, `index.mjs`) and `.claude-plugin/bundled/primitives/python/`
    (`provenance.py`, `audit.py`, `marked.py`, `__init__.py`) — copy those
    four files for the builder's language straight into the target repo (e.g.
    a `provenance/` dir next to the source-truth layer named in the
    interview), unmodified. They carry a dual-import shim, so they work
    copied flat with no `package.json`/`pyproject.toml` entry required. State
    plainly that this is a vendored copy the builder now owns and updates
    manually (no auto-sync) — the published-package route is what stays
    current automatically.
  This adds no mandatory step: a builder who never accepts never needs it.

When scaffolding, **teach the pattern at the first site rather than carpeting
all of them** — the goal is a builder who can extend it, not a wrapped codebase:

1. At a Q4 site: wrap the value's origin in `mark(value, { source, confidence })`
   — the builder supplies `source`/`confidence` per site (their answers, not
   your defaults; the interview's honesty rule applies here too).
2. At a derivation: `derive([inputs], fn)` (JS) / the Python equivalent —
   show that the output inherits `derivedFromMock` and the weakest confidence
   automatically, and that no API exists to clear taint.
3. At a Q8 output: show `metaOf(x)` / `meta_of(x)` exposing the lineage, and
   `auditMeta` / `audit_meta` returning `[]` when the envelope is consistent.
4. Add one failing-then-passing test that asserts the key output audits clean
   (`auditMeta(metaOf(out)) === []` / `audit_meta(meta_of(out)) == []`), and
   wire it into the test command the pre-commit gate already runs (Step 4) — so
   an unmarked or laundered return is caught before review, by the gate the
   builder just installed.
5. **Install the bypass lint over the scaffolded sites** (#214 — until this
   step existed, nothing ever installed it). **JS:** copy the adapter's
   `provenance-lint/` directory and `eslint-provenance.template.cjs` from
   `adapters/js/` **into the target repo**, plugin directory next to the
   config so the template's `require("./provenance-lint/index.cjs")`
   resolves. Fill the placeholder **in the code line, never the comments**:
   replace exactly `files: __GLOBS__` with the scaffolded sites' globs — both
   placeholders appear in the template's comments before their code use, so a
   first-occurrence replace fills prose and leaves the code `undefined`.
   Leave the `__OUTPUT_GLOBS__` block untouched: Step 4c, which always runs
   next when this step ran, fills it or removes it — the placeholder never
   survives to a finished bootstrap. Load the fragment from the flat config
   the same way as the boundary template (import and spread its entries).
   **Python:** copy `adapters/python/provenance_lint.py` into the repo's
   tooling directory and extend the test from item 4 to run its `check()`
   over the scaffolded files — the pre-commit gate runs the project's one
   test command and takes exactly one runner by design, so the lint rides
   that command; never try to chain a second runner onto the gate.

Show each file's diff as you scaffold; every remaining unscaffolded Q4/Q8 site
goes in the report as `planned`, so the coverage claim stays honest.

## Step 4c — Offer output-tag enforcement (opt-in; only after 4b was accepted)

Step 4b scaffolds `mark`/`derive` at the trust-bearing sites. This step offers
the gate that keeps them tagged: `require-provenance-output` flags a function
that returns a *provably raw* computation, inside a surface the builder declares
(ADR-0011).

**Only offer this if Step 4b was accepted.** With no primitive in the project,
every trust-bearing function returns raw by definition, so the rule would fire
across the surface on day one — the exact cry-wolf failure ADR-0011 exists to
avoid. If 4b was declined, skip this step and record it as not-offered (with
that reason) rather than silently omitting it — nothing dangles, because the
provenance config only exists when 4b's item 5 installed it.

**When 4b was accepted, this step ALWAYS resolves the `__OUTPUT_GLOBS__`
placeholder** — filled on accept, removed on decline. A skipped resolution
ships a config that throws `ReferenceError` on load and takes the bypass rule
down with it. And every edit here targets **the copy installed in the target
repo in Step 4b item 5** — never `eslint-provenance.template.cjs` inside the
plugin's own directory, which is the shipped template every future bootstrap
starts from.

The surface is **not** the same as the bypass-lint globs. Those cover "files
that use the primitive"; this covers "files whose outputs must carry
provenance". Propose the surface from the interview's own answers — the Q4
downstream values and Q8 lineage-bearing outputs — and let the builder correct
it. Do not widen it for them: a surface drawn too broad is how this rule earns a
blanket disable, after which it catches nothing.

- **Declined → remove the `__OUTPUT_GLOBS__` block from the installed config
  entirely**: delete the second object in the exported array — from its
  leading `// Output-tag enforcement` comment through that object's closing
  `},` — leaving the bypass block as the array's only entry. Not a
  placeholder left in place, not the rule set to `"off"` — an unreplaced
  placeholder throws `ReferenceError` when ESLint loads the config, and a
  disabled rule is a claim the project enforces something it doesn't. Record
  the decline in the report.
- **Accepted →** wire it for the builder's language:
  - **JS:** in the installed config, replace exactly `files: __OUTPUT_GLOBS__`
    (the code line — the same never-the-comments rule as `__GLOBS__`) with
    the agreed surface. The rule is already registered in that block.
  - **Python:** there is no config template — extend the suite test from
    Step 4b item 5 to also assert the surface files' outputs carry
    provenance (`provenance_lint.py`'s require-output check over the agreed
    files, via its library API). The check rides the project's test command;
    the pre-commit gate takes exactly one runner, so never bolt a second
    command onto the gate itself.
- **Verify, don't assume** (same rule as Step 4): plant a function inside the
  surface that returns a raw computation, confirm the gate blocks, then remove
  it. An installed-but-inert rule is the failure mode to rule out — and this one
  is silent by design outside its surface, so "no output" is not evidence it is
  working.

## Step 5 — Report (audit format)

Open with the same **required header block** as the audit format (`report-format:
v3`, `scope`, `principles-revision`, `date`, `commit` — see
`skills/plumb-line-audit/SKILL.md`). For a bootstrap run `scope` is the project
being wired, and add one line — `adapter: <name>` — recording the adapter used.
Bootstrap shares only the v3 **header block**; the glossary, findings table, and
coverage map are audit-specific and are not part of a bootstrap report.

Then list every file created/modified and any unanswered prompt left as a TODO
for the builder. Label anything not done as `planned`. (The adapter is recorded
in the header's `adapter:` line above.) Record the Step 4b outcome explicitly —
`accepted` (with the scaffolded sites and the `planned` remainder) or
`declined` — so the report says whether runtime provenance exists in this
project or was offered and turned down.

## Step 6 — Hand the baton

The project is now declared and enforced; the natural next step is a first
audit against the freshly written ruleset. Offer it — "want me to run
`plumb-line-audit` now for a baseline read?" — and on a yes, **invoke the skill
directly** (via the host's skill mechanism) rather than telling the builder to
run it. If bootstrap was itself invoked mid-audit (the audit stops when no
architecture is declared and hands here for the interview), return the baton
instead: the calling audit resumes with the now-declared architecture — do not
start a second audit.
