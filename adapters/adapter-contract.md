# plumb-line adapter contract

An adapter makes the principles enforceable in one language. Every adapter
provides the four domain-neutral capabilities (§1–4). §5 and §5b apply only to
projects using the provenance primitive. §6 is the manifest that records which
enforcement a repo carries. Bootstrap detects the project language, then copies and parameterizes
these files into the target repo.

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

## 5b. Output-tag enforcement (declared surface)

- Purpose: invert the default inside a surface the builder declares — a
  trust-bearing function that returns a provably raw computation is an error,
  rather than something review must spot (ADR-0011). Opt-in once at the
  boundary, opt-out per function; with no surface declared it is a no-op.
- JS: `provenance-lint/require-provenance-output.cjs` (an ESLint rule) +
  the `__OUTPUT_GLOBS__` block in `eslint-provenance.template.cjs`.
- Python: `provenance_lint.py` — no config template; the output check is
  wired into the project's own test command via the library API
  (`check_outputs()` over the declared surface files), which the pre-commit
  gate already runs. The gate itself takes exactly one runner by design —
  never a second chained command (#214).
- Both sides prove the rule → `decide()` contract. The gate's CLI path
  (`PLUMBLINE_TEST_CMD` → spawn → exit code) is spawn-tested in both languages
  for an unset, blank, unstartable, failing and passing command (#467); what
  stays unproven is this rule's lint running through that spawn:
  `adapters/js/hooks/__tests__/provenance-lint-gate.integration.test.mjs` and
  `adapters/python/hooks/test_hooks.py::test_gate_blocks_on_untagged_output`.
- Note: unlike capabilities 1–4 this rule is *library-coupled* (it knows the
  primitive's API), not domain-neutral. It is grouped with the adapters as
  enforcement for now and may move under `primitives/` in a future version.

## 6. Enforcement manifest (`.plumb-line/enforcement.json`)

- Purpose: the one place a repo states which of capabilities 1, 5 and 5b it
  carries (plus a baselines directory), so the GitHub Action (`action.yml`,
  ADR-0016) can run them without guessing. `enforcement-format: v1`;
  validator `scripts/check_enforcement_manifest.py`.
- Every capability is optional. Absence means not enforced here: an absent
  capability is not run and does not appear in the Action's summary;
  nothing absent is ever counted as a pass. Nothing in the file is a
  default: bootstrap writes it from the interview (Step 4d), or a maintainer
  writes it by hand (shape in ACTION.md).
- Shape: `languages`; per language `boundary.config`, `provenance.config`
  (JS), `provenance.globs`, `provenance.outputGlobs` (the ADR-0011 declared
  surface — in Python this is its first home); `baselines.dir`.
- The JS configs the manifest names (`boundary.config`, `provenance.config`)
  must each be a standalone flat config — a complete `module.exports = [ … ]`
  registering its plugin and carrying only plumb-line rules — because the
  Action runs each with `--no-config-lookup`: the Step 4 boundary `rules`
  fragment is not one (bootstrap writes `eslint-boundary.config.cjs` beside
  it for this), and a consumer's full `eslint.config.*` turns every
  non-plumb-line finding into `PL/unparsed`.
- Optional top-level `ratchet.file` (#119, ADR-0017): the provenance-ratchet
  file, itself a contracted output (`ratchet-format: v1`, validator and
  writer `adapters/sarif/ratchet.py`). The manifest validator does not
  check the file exists — `ratchet.py update` creates it; the Action fails
  on its absence. Not a capability: it changes how `<lang>.output` results
  are levelled, it does not add a check.

## Hook I/O convention (shared)

- Contract version: 1. The version covers the **shape**: what is read from stdin and the environment, and that exit 0 allows and exit 2 blocks. A behaviour change within that shape, stricter or looser, is recorded in the CHANGELOG, not versioned, and a change that allows something a guard used to block is named there as a loosening (owner decisions, #475): a stricter guard fails loudly, but a looser one lets something through that no one sees.
- The cases in `adapters/hook-cases.json` are this convention's parity contract: both twins' CLIs run every row (#475). A CLI behaviour one twin's tests pin and the table does not is not yet a shared behaviour.
- Input is per guard, read as JSON on stdin (the pre-commit gate takes no stdin):
  - `boundary-guard`: `{ "filePath": "...", "importPath": "..." }`
  - `branch-guard`: `{ "filePath": "..." }`
  - `pre-commit-gate`: no stdin; reads the test command from `PLUMBLINE_TEST_CMD`. Both twins split it into words with shell-style quoting, by the rules of Python's `shlex.split` (single quotes literal; inside double quotes a backslash escapes only `"` and `\`; outside quotes it escapes any character; `#` is ordinary; an empty quoted word is kept), and run it without a shell (current, #472). A command that cannot be split (an unbalanced quote, a trailing backslash) blocks, with exit 2.
- Both guards read stdin as strict UTF-8, whatever the locale or `PYTHONIOENCODING` says, and do not strip a byte-order mark: each blocks, with exit 2, on stdin that is not valid UTF-8 (current; the branch guard since #475, the boundary guard since #471). Only JSON whitespace counts as empty stdin, and stdin that is not JSON blocks.
- The branch from `PLUMBLINE_BRANCH` and config from `PLUMBLINE_CFG` (JSON) are read from the environment.
- The branch guard's `PLUMBLINE_CFG`, when set, is a JSON object whose own keys are these two, each an array of strings: `protectedBranches` (default `["main"]`; an explicit `[]` protects no branch) and `docsAllowlist` (default none). Keys are camelCase only, in both twins. The guard fails closed on the config (current, #469): it blocks, with exit 2 and a reason naming `PLUMBLINE_CFG`, when the variable is set but is not valid JSON (including `""`) or is not an object (`null`, an array, a string, a number), when it has a key neither guard reads (a snake_case `protected_branches` or `docs_allowlist` is named with the camelCase key to use), when either field is not an array of strings, or when `docsAllowlist` has an empty entry. Unset, the defaults apply. `PLUMBLINE_CFG` is shared: one object may carry both the branch guard's keys and the boundary guard's (`layers`, `direction`), and the branch guard allows the boundary guard's keys without validating them (owner decision on #469).
- The boundary guard's `PLUMBLINE_CFG`, when set, is a JSON object whose own keys are these two: `layers` (the layer names, top to bottom; a non-empty array of non-empty strings; default none, so no import is judged) and `direction` (exactly `"downward"` or `"upward"`; default `"downward"`). It fails closed on the config the same way (current, #471): it blocks, with exit 2 and a reason naming `PLUMBLINE_CFG`, when the variable is set but is not valid JSON or is not an object, when it has a key neither guard reads, when `layers` is not an array of strings, is empty or has an empty entry, or when `direction` is anything else. It allows the branch guard's keys without validating them. That is the mirror of the branch guard's rule: one shared object works for both guards, each validates only its own keys, and a key neither reads blocks in both, with a reason naming each guard's keys.
- Exit 0 = allow. Exit 2 with a message on stderr = block. A Claude Code hook treats only exit 2 as a block (any other non-zero exit lets the action through), so a guard's failures exit 2 too: the branch guard blocks, with exit 2, on stdin it cannot read or with no `filePath` wherever the branch matters (#449); the boundary guard blocks on stdin it cannot read, with no `filePath` (missing, empty or not a string), or with an `importPath` that is present but not a string (#471), while with no `importPath`, or an empty one, it has nothing to judge and allows; and the pre-commit gate exits 2 when `PLUMBLINE_TEST_CMD` is unset, blank or cannot be run (#467).
- The branch guard treats an unset or empty `PLUMBLINE_BRANCH` as unknown (#449), and so a value git would not accept as a branch name, by git's own rule (such as `HEAD`, a leading `-`, a space or control character, `..`, `@{`, a component starting with `.` or ending `.lock`; #474): a code edit blocks, and a docs-allowlisted edit is allowed, as it is on every branch. An unknown branch is an inconclusive result, never a pass.
- Git runs a hook with no stdin and none of these variables, so the scripts are not git hooks on their own. The pre-commit gate works from a `.git/hooks/pre-commit` that sets `PLUMBLINE_TEST_CMD`; a git-hook wrapper for the branch guard is planned (#464). When wiring as a Claude Code PreToolUse hook, map the host tool payload's file path into the `{filePath}` the guard reads and set the branch in the hook command (e.g. `PLUMBLINE_BRANCH="$(git branch --show-current)"`) — add a one-line shim if the host payload shape differs rather than assuming it matches.
- A script's CLI entry point resolves symlinks before deciding whether it is the process entry (so it still runs when invoked via a symlinked path, e.g. macOS `/tmp`).
