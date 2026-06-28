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

## Hook I/O convention (shared)

- Each guard reads JSON on stdin: `{ "filePath": "...", "command": "..." }`.
- Exit 0 = allow. Exit non-zero with a message on stderr = block.
- This matches Claude Code PreToolUse hook semantics so the same scripts work as git hooks and as Claude hooks.
