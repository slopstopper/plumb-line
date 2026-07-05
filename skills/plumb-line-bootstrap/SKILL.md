---
name: plumb-line-bootstrap
description: Use when setting up a project with the plumb-line discipline — interviews the builder to find their source-truth layer and layering, generates a domain-neutral ruleset, and installs parameterized enforcement (boundary check, test gate, pre-commit gate, branch guard) for the project's language. Ships no default layers and invents no answers.
---

# Bootstrap a project with plumb-line

Part of the four-skill flow: learn the discipline with `plumb-line-method`, set
the project up here, review changes with `plumb-line-audit`, and apply findings
with `plumb-line-remediate`.

REQUIRED READING FIRST: `reference/portable-principles.md` and
`adapters/adapter-contract.md` (plugin root).
If either file cannot be read, stop immediately and report which file is missing. Do not proceed from memory.

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
- **Accepted →** check the library is importable first (`plumb-line-provenance`
  on npm / PyPI). If absent, tell the builder the one-line install and pause —
  suggesting it is fine; running it or vendoring the source is not this slice.
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

Show each file's diff as you scaffold; every remaining unscaffolded Q4/Q8 site
goes in the report as `planned`, so the coverage claim stays honest.

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
