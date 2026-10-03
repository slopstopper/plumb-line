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

- Purpose: block a commit if build/test/lint fail: on a protected branch, or on every branch when `PLUMBLINE_CFG` is unset. On other branches with `testsOnOtherBranches` `"run"` a failure is reported, not blocked; with `"skip"` the tests do not run.
- Provides: a hook script returning non-zero to block. JS `hooks/pre-commit-gate.mjs`; Python `hooks/pre_commit_gate.py`.
- Branch-aware when `PLUMBLINE_CFG` is set (current, #613; see *Hook I/O convention*): a protected or unknown branch runs the tests and blocks on failure; any other branch skips them by default (`testsOnOtherBranches`). Unset, the tests run on every branch and a failure blocks, as before. The gate imports the branch guard's commit-hook wrapper, so it sits in the same directory.
- Both export `decide()`, which takes runners and blocks unless every runner returns exactly `true` (current, #493). `false` is a failure; any other result (`undefined`/`None`, a number, a string, an object) blocks as an answer the gate cannot read; no runners at all blocks too (#476). The JS gate awaits each runner; the Python gate runs synchronous runners only, and blocks on one that returns an awaitable. A boolean-like value that is not the language's own boolean (`np.bool_(True)`, `new Boolean(true)`) also blocks, so convert it first (`bool(...)` in Python).

## 4. Branch guard

- Purpose: block the first code edit on a protected branch.
- Provides: a hook script. JS `hooks/branch-guard.mjs`; Python `hooks/branch_guard.py`. And a git commit-hook wrapper for it: JS `hooks/branch-guard-commit.mjs`; Python `hooks/branch_guard_commit.py` (current, #464; see *Hook I/O convention*).
- Parameterized by: PROTECTED_BRANCHES (default: main), and a docs-allowlist (paths that may be edited on a protected branch).
- Protected names are compared exactly, or without case when the repository's `core.ignorecase` is true, since on a case-insensitive filesystem `git checkout Main` is on `main` (current, #615). The guard, its commit hook and the pre-commit gate share one helper for this. It reads `core.ignorecase` only for a branch that matches a protected name only where case is ignored (by case, by NFC, or through a character the runtime does not know; below). The guard reads it from the repository at `CLAUDE_PROJECT_DIR` when that is set, otherwise from the working directory; the commit hook and the gate read the repository git runs them in. If git cannot say (not a repository, git failing, or an answer other than `true` or `false`), the comparison ignores case: fail closed. Without case, both names are normalized to NFC, then folded to upper case and then lower case, with the runtime's own Unicode tables (current, #625): so `cafe` + U+0301 is `café`, and `maſter` is `master`, as APFS reads them. A character the runtime's Unicode does not know (general category `Cn`) cannot be folded with certainty, so without case it matches any one character (current, #625): after NFC and the fold, a branch is an alias of a protected name when the two are equal character for character (by code point, so the lengths must agree), a `Cn` character in either name matching whatever is opposite it. So `mai` + U+40000 (unassigned) is an alias of `main`, and `fix-🫎` is not, on any runtime. The reason names a protected name whose fold is equal, else the first that matches this way. With no branch protected nothing matches. Which characters a runtime knows depends on its Unicode version, so a twin on an older runtime can protect a name a newer one does not, and, through normalization, an older runtime can allow a name a newer one protects (a protected name holding a character the older runtime does not know; see `primitives/PARITY.md`). Both directions are open divergences, tracked in #642. Where `core.ignorecase` is false nothing is normalized or folded. Reasons name the protected branch as configured. The premise is git's behaviour, checked with git 2.39.5 on APFS (macOS, `core.ignorecase` true): `git checkout Main` succeeds, `git branch --show-current` reports `Main`, and a commit there moves `main`.
- Allowlist entry forms (exactly three; empty entries are rejected): exact file (`README.md`), directory with trailing slash (`docs/`, matches everything under it), and extension glob (`*.md`, matches that extension at any depth). No other globbing is supported — paths are normalized and a candidate that escapes upward (`..`) never matches. Normalization is POSIX, exactly as Node's `path.posix.normalize`, in both twins (current, #515): a trailing slash is kept, so a bare directory (`docs`) or a path ending in `/` is not a file inside an allowlisted directory or the allowlisted file; and `\` is an ordinary character, as in git paths, never a separator.

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
- The cases in `adapters/hook-cases.json` are this convention's parity contract: both twins' CLIs run every row (#475). A CLI behaviour one twin's tests pin and the table does not is not yet a shared behaviour. The table is source truth (ADR-0018, amendment of 2026-09-28, #517): where it and this prose disagree, the table holds, and a row's expected result is recorded only once both twins produce it.
- Input is per guard, read as JSON on stdin (the pre-commit gate takes no stdin):
  - `boundary-guard`: `{ "filePath": "...", "importPath": "..." }`
  - `branch-guard`: `{ "filePath": "..." }`
  - `pre-commit-gate`: no stdin; reads the test command from `PLUMBLINE_TEST_CMD`. Both twins split it into words with shell-style quoting, by the rules of Python's `shlex.split` (single quotes literal; inside double quotes a backslash escapes only `"` and `\`; outside quotes it escapes any character; `#` is ordinary; an empty quoted word is kept), and run it without a shell (current, #472). A command that cannot be split (an unbalanced quote, a trailing backslash) blocks, with exit 2. The command is checked before anything else, so one that is unset, blank, cannot be split or is not valid UTF-8 blocks even where the tests would be skipped. Whether its program exists is found only by running it: under `"skip"` a command that cannot be started is not caught.
- The pre-commit gate is branch-aware when `PLUMBLINE_CFG` is set (current, #613). It reads `PLUMBLINE_CFG` with the branch guard's checks (a config the branch guard refuses blocks the gate too), plus `testsOnOtherBranches`: exactly `"skip"` or `"run"`, absent meaning `"skip"`; any other value blocks. It reads the branch exactly as the branch guard's commit hook does (below: HEAD's full ref, a rebase's `head-name`, and every branch `update-refs` will move). If any of those branches is protected (compared as the branch guard compares them, including without case where `core.ignorecase` is true, #615) the commit is protected; if the branch cannot be read (a detached HEAD, a name git refuses, git failing) it is treated as protected. On a protected branch the tests run, and a failure blocks with exit 2. On any other branch, `"skip"` does not run them and allows with a notice on stderr that the commit is unchecked; `"run"` runs them, and a failure is allowed (exit 0) with a notice that the commit is red, while a pass is silent. A command that cannot be started blocks wherever it is run, naming the program and the error code (such as `nosuchprog: ENOENT`) in both twins, with `PLUMBLINE_CFG` set or not. With `PLUMBLINE_CFG` set the gate needs the branch guard and its commit hook from the same release beside it: missing, or lacking what it reads, it blocks with one reason in both twins. With `PLUMBLINE_CFG` unset the gate reads no branch: it runs the tests on every branch and a failure blocks, as before #613. A commit allowed on another branch, unchecked or red, can still reach a protected branch without the gate: a local fast-forward or a clean merge runs no pre-commit hook. CI and branch protection guard that route; the gate does not. The gate's messages are approved text (#613); its cases are the `preCommitGate` rows of `adapters/commit-hook-cases.json`, run against a real temporary repository.
- Both guards read stdin as strict UTF-8, whatever the locale or `PYTHONIOENCODING` says, and do not strip a byte-order mark: each blocks, with exit 2, on stdin that is not valid UTF-8 (current; the branch guard since #475, the boundary guard since #471). Only JSON whitespace counts as empty stdin, and stdin that is not JSON blocks.
- The branch from `PLUMBLINE_BRANCH` and config from `PLUMBLINE_CFG` (JSON) are read from the environment.
- Every environment variable a hook reads (`PLUMBLINE_BRANCH`, `PLUMBLINE_CFG`, `PLUMBLINE_TEST_CMD`) must be valid UTF-8, judged from its bytes whatever the locale: a value that is not blocks, with exit 2 and a reason naming the variable, in both twins (current, #501). A value holding the replacement character U+FFFD blocks too, because Node turns bytes that are not UTF-8 into U+FFFD before the JS twin can see them, so that is how such a value reaches it.
- The branch guard's `PLUMBLINE_CFG`, when set, is a JSON object whose own keys are these two, each an array of strings: `protectedBranches` (default `["main"]`; an explicit `[]` protects no branch) and `docsAllowlist` (default none). Keys are camelCase only, in both twins. The guard fails closed on the config (current, #469): it blocks, with exit 2 and a reason naming `PLUMBLINE_CFG`, when the variable is set but is not valid JSON (including `""`) or is not an object (`null`, an array, a string, a number), when it has a key neither guard reads (a snake_case `protected_branches` or `docs_allowlist` is named with the camelCase key to use), when either field is not an array of strings, or when `docsAllowlist` has an empty entry. Unset, the defaults apply. `PLUMBLINE_CFG` is shared: one object may carry both the branch guard's keys and the boundary guard's (`layers`, `direction`), and the branch guard allows the boundary guard's keys without validating them (owner decision on #469). It allows the pre-commit gate's `testsOnOtherBranches` the same way (#613), and so does the boundary guard.
- The boundary guard's `PLUMBLINE_CFG`, when set, is a JSON object whose own keys are these two: `layers` (the layer names, top to bottom; a non-empty array of non-empty strings; default none, and with none an import to judge blocks, see below) and `direction` (exactly `"downward"` or `"upward"`; default `"downward"`). It fails closed on the config the same way (current, #471): it blocks, with exit 2 and a reason naming `PLUMBLINE_CFG`, when the variable is set but is not valid JSON or is not an object, when it has a key neither guard reads, when `layers` is not an array of strings, is empty or has an empty entry, or when `direction` is anything else. It allows the branch guard's keys without validating them. That is the mirror of the branch guard's rule: one shared object works for both guards, each validates only its own keys, and a key neither reads blocks in both, with a reason naming each guard's keys.
- Exit 0 = allow. Exit 2 with a message on stderr = block. A Claude Code hook treats only exit 2 as a block (any other non-zero exit lets the action through), so a guard's failures exit 2 too: the branch guard blocks, with exit 2, on stdin it cannot read or with no `filePath` wherever the branch matters (#449); the boundary guard blocks on stdin it cannot read, with no `filePath` (missing, empty or not a string), or with an `importPath` that is present but not a string (#471), while with no `importPath`, or an empty one, it has nothing to judge and allows; with an import to judge and no `layers` configured (`PLUMBLINE_CFG` unset, `{}`, or holding only `direction` or the branch guard's keys) it blocks with the reason "no layers configured", rather than allowing it as a pass would (current, #516; stricter than v0.11.5, which allowed it as "same or unscoped layer"); and the pre-commit gate exits 2 when `PLUMBLINE_TEST_CMD` is unset, blank or cannot be split, or cannot be started where the tests run (#467), or when `PLUMBLINE_CFG` is set and invalid (#613).
- The branch guard treats an unset or empty `PLUMBLINE_BRANCH` as unknown (#449), and so a value git would not accept as a branch name, by git's own rule (such as `HEAD`, a leading `-`, a space or control character, `..`, `@{`, a component starting with `.` or ending `.lock`; #474): a code edit blocks, and a docs-allowlisted edit is allowed, as it is on every branch. An unknown branch is an inconclusive result, never a pass.
- Git runs a hook with no stdin and none of these variables, so the scripts are not git hooks on their own. The pre-commit gate works from a `.git/hooks/pre-commit` that sets `PLUMBLINE_TEST_CMD`, and the branch guard through its commit-hook wrapper (next item). When wiring as a Claude Code PreToolUse hook, map the host tool payload's file path into the `{filePath}` the guard reads and set the branch in the hook command (e.g. `PLUMBLINE_BRANCH="$(git branch --show-current)"`) — add a one-line shim if the host payload shape differs rather than assuming it matches.
- The branch guard's git commit hook (current, #464) is JS `hooks/branch-guard-commit.mjs` or Python `hooks/branch_guard_commit.py`, copied into the same directory as its guard, which it imports. It reads no stdin and never reads `PLUMBLINE_BRANCH`. It reads `PLUMBLINE_CFG` exactly as the guard does, then the branch from `git symbolic-ref HEAD`'s full ref (never the short name, which git turns into `heads/main` when a tag is also named `main`), and judges each path `git diff --cached --name-only -z --no-renames --ignore-submodules=none` lists, in git's order, with the guard's `decide`. That is the index being committed against HEAD, including the temporary index `git commit -a` or `git commit <path>` uses; so an amend is judged by what is staged now, not by the whole amended commit. A rename is judged as the path it leaves and the path it makes, so moving a code file into `docs/` blocks on the code path; a deletion is judged like any other edit; a submodule bump is judged as its path even where `diff.ignoreSubmodules` or a submodule's `ignore` setting (in `.git/config` or a committed `.gitmodules`) would hide it. A HEAD on no branch (detached, or pointing outside `refs/heads/`), or on a branch git would not accept as a branch name (such as `-x`, which `git symbolic-ref` allows), is an unknown branch, as an unset `PLUMBLINE_BRANCH` is: a code path blocks, a docs-allowlisted path passes, and the reason names HEAD. The exception is a rebase in progress (#547): while the directory `git rev-parse --git-path rebase-merge` (or `rebase-apply`) names exists, which git itself reads as a rebase in progress, the branch is the one git records there as being rebased, read from its `head-name`, whatever detached HEAD. A `head-name` that cannot be read, or that names no branch (git writes `detached HEAD` when a detached HEAD is rebased, and `git am` writes none) or no valid branch name, leaves the branch unknown, and the reason says which. With `--update-refs` (or `rebase.updateRefs`) the rebase also moves every branch listed in that directory's `update-refs`, so each path is judged against each of those branches too, and blocks if any of them blocks it (including one whose `update-ref` step has already run, which fails closed); an `update-refs` that cannot be read leaves the branch unknown. A path that is not UTF-8 is decoded with U+FFFD for each bad sequence and judged, not refused. The first blocked path's reason goes to stderr with exit 2, and git refuses the commit on any non-zero exit. A bad `PLUMBLINE_CFG` blocks, and so does a git step that fails: outside a repository, or git that cannot be started (the reason names the error code, such as `ENOENT`, in both twins). Git runs `pre-commit` for `git commit` itself, and not for the commits a rebase makes or a cherry-pick, a revert or a merge that completes on its own (a clean merge runs `pre-merge-commit`). One that stops (a conflict, or a merge with `--no-commit` or `--squash`) and is finished with `git commit` or `--continue` is judged, with every path it brings in; and a commit made by hand at a rebase stop, such as `git commit --amend` at an `edit`, is judged on the branch being rebased and every branch the rebase will move: it passes on a feature branch and blocks a code path when one of them is protected. `git rebase --continue` runs no hook, so a change staged at a stop and carried on by `--continue` is not judged. This is git's behaviour, checked with git 2.39, and may differ between versions. `git commit --no-verify` skips the hook, as it skips every pre-commit hook: it catches an accident, it is not a lock. The cases in `adapters/commit-hook-cases.json` are its parity contract, run by both twins against a real temporary repository.
- A script's CLI entry point resolves symlinks before deciding whether it is the process entry (so it still runs when invoked via a symlinked path, e.g. macOS `/tmp`).
