# plumb-line adapter contract

An adapter makes the principles enforceable in one language. Every adapter
provides four capabilities. Bootstrap detects the project language, then copies
and parameterizes these files into the target repo.

## 1. Boundary check

- Purpose: enforce one-way layering (Principle 2).
- Provides: a config template with layer placeholders that bootstrap fills with the project's layers/direction.
- JS: `eslint-boundary.template.cjs` (import/no-restricted-paths) — placeholder `__ZONES__`.
- Python: `importlinter-boundary.template.ini` (import-linter contracts) — placeholders `{{ROOT_PACKAGE}}`, `{{LAYERS_TOP_TO_BOTTOM}}`. (import-linter's `layers` contract is inherently one-way, so the direction is implicit in layer order rather than a separate placeholder.)

## 2. Test gate

- Purpose: run the project's test suite as a required gate.
- Command the adapter declares: JS `npx vitest run`; Python `pytest -q`.

## 3. Pre-commit gate

- Purpose: block a commit if build/test/lint fail.
- Provides: a hook script returning non-zero to block. JS `hooks/pre-commit-gate.mjs`; Python `hooks/pre_commit_gate.py`.

## 4. Branch guard

- Purpose: block the first code edit on a protected branch.
- Provides: a hook script. JS `hooks/branch-guard.mjs`; Python `hooks/branch_guard.py`.
- Parameterized by: PROTECTED_BRANCHES (default: main), and a docs-allowlist (paths that may be edited on a protected branch).
- Allowlist entry forms (exactly three; empty entries are rejected): exact file (`README.md`), directory with trailing slash (`docs/`, matches everything under it), and extension glob (`*.md`, matches that extension at any depth). No other globbing is supported — paths are normalized and a candidate that escapes upward (`..`) never matches.

## 5. Provenance-bypass lint

- Purpose: statically flag source-code patterns that bypass the provenance
  combination law or launder taint by hand (SPEC PB1–PB4) — the review-time
  complement to the runtime `auditMeta` / `audit_meta`. Applies only to projects
  using the provenance primitive.
- JS: `provenance-lint/no-provenance-bypass.cjs` (an ESLint rule) + the
  `eslint-provenance.template.cjs` config (placeholder `__GLOBS__`).
- Python: `provenance_lint.py` — a stdlib-`ast` checker exposing
  `check(source, filename) -> [issue]` and a CLI (`file:line: RULE message`,
  non-zero exit on any issue).
- Note: unlike capabilities 1–4 this rule is *library-coupled* (it knows the
  primitive's API), not domain-neutral. It is grouped with the adapters as
  enforcement for now and may move under `primitives/` in a future version.

## Hook I/O convention (shared)

- Contract version: 1.
- Input is per guard, read as JSON on stdin (the pre-commit gate takes no stdin):
  - `boundary-guard`: `{ "filePath": "...", "importPath": "..." }`
  - `branch-guard`: `{ "filePath": "..." }`
  - `pre-commit-gate`: no stdin; reads the test command from `PLUMBLINE_TEST_CMD`.
- The branch from `PLUMBLINE_BRANCH` and config from `PLUMBLINE_CFG` (JSON) are read from the environment.
- Exit 0 = allow. Exit non-zero with a message on stderr = block.
- The scripts work directly as git hooks. When wiring as a Claude Code PreToolUse hook, map the host tool payload's file path into the `{filePath}` the guard reads — add a one-line shim if the host payload shape differs rather than assuming it matches.
- A script's CLI entry point resolves symlinks before deciding whether it is the process entry (so it still runs when invoked via a symlinked path, e.g. macOS `/tmp`).
