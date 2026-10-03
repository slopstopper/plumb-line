report-format: v4
scope:               git diff --name-only 25f7aee 0a97ee6 -- skills/ reference/portable-principles.md primitives/ adapters/ (PR #617, the branch-aware pre-commit gate, #613 and #615; 21 files)
principles-revision: 1
date:                2026-10-03
commit:              0a97ee6556df1b114606d43db2e440b5dee817c4

```
P1 — Source-truth layer        P6 — Maturity vocabulary   P8 — State-first lineage
P2 — One-way layering          P7 — Contracted outputs    P9 — Golden baseline + explain-the-drift
P3 — Confidence + provenance
spine — null-result expressibility
```

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `adapters/js/hooks/branch-guard.mjs` | 64-80 | `fold`, `protectedMatch` | violation | The twins' case fold (`toUpperCase().toLowerCase()` here, `upper().lower()` in the Python twin `_fold`, `adapters/python/hooks/branch_guard.py` 78) takes each runtime's own Unicode tables, so the twins disagree on any letter whose case mapping is newer than one runtime's Unicode. Probe: branch `x꟎`, protected `x꟏`, ignore case on. Node 24.15 (Unicode 17) returns the protected name and the JS guard blocks the code edit. Python 3.14.4 (Unicode 16) returns None and the Python guard allows it. 28 code points differ between these two runtimes, and more against CI's Python 3.11. This needs a newly encoded letter, so it is rare, but one twin allows what the other blocks. No row covers it and PARITY.md records no waiver. | Name the reference fold and ship it with both twins (a pinned case-folding table, or ASCII plus listed mappings), and add a row on a letter newer than the oldest supported runtime. Or record a waiver in PARITY.md under the #505 rule, if the owner judges that no real input reaches it | P1 — Source-truth layer |
| `adapters/js/hooks/branch-guard.mjs` | 91-101 | `ignoreCaseFrom` | violation | The docstring says any answer other than exit 0 with true or false, or exit 1, "cannot be read, so it fails closed". But exit 0 with any stdout other than `true` returns false, so case is not ignored: it fails open. Both twins' tests pin `(0, "yes\n")` as false, under the comment "Anything else cannot be read: fail closed" (`adapters/js/hooks/__tests__/pre-commit-gate.test.mjs` 195, `adapters/python/hooks/test_hooks.py` 466). The Python twin `ignore_case_from` (`adapters/python/hooks/branch_guard.py` 107) is the same. Real `git config --bool` prints only true or false at exit 0, so only a nonstandard git reaches it, but an answer the code cannot read becomes a definite "case-sensitive". | Return false only for exactly `false` and true for anything else, and move the test row under the fail-closed comment. Or narrow the docstring and the comment to what the code does | spine — null-result expressibility |
| `adapters/adapter-contract.md` | 113 | — | violation | This PR edited the Exit bullet, and it still says the pre-commit gate exits 2 when `PLUMBLINE_TEST_CMD` "cannot be run (#467)". With `PLUMBLINE_CFG` set and `testsOnOtherBranches` "skip", the gate never runs the command on an unprotected branch, so a command that cannot be started exits 0. The contract's own line 106 says so: under "skip" such a command "is not caught". The summary claims more enforcement than the gate gives. | Narrow it to "cannot be split, or cannot be started where the tests run" | P6 — Maturity vocabulary |
| `skills/plumb-line-bootstrap/SKILL.md` | 164 | Hook I/O contract | violation | The same overstatement in the skill's Hook I/O summary: the gate exits 2 when `PLUMBLINE_TEST_CMD` "is unset, blank or cannot be run". Under "skip" on an unprotected branch, a command that cannot be started exits 0, as the same section's gate bullet says at line 182 ("blocks only where the tests run"). The skill is what builders wire from. | Use the same narrowed wording as the contract | P6 — Maturity vocabulary |
| `adapters/adapter-contract.md` | 107 | — | advisory | The gate's contract says a protected branch runs the tests and blocks. Bootstrap Step 4 says the same, and Step 4b item 4 adds "caught by the gate … before a commit to a protected branch". None of them says that a commit made unchecked ("skip", the default) or red ("run") on a feature branch reaches a protected branch through a local fast-forward or clean merge, which runs no pre-commit hook. Only CHANGELOG.md's Breaking entry for #613 says this, and that is a release note, not the durable contract builders are pointed to. | Add the CHANGELOG's caveat to the gate bullet here and to bootstrap Step 4's "Tell the builder" item | P6 — Maturity vocabulary |
| `adapters/js/hooks/pre-commit-gate.mjs` | 91-106 | `MESSAGES` | advisory | Adoption gap, reported once rather than per twin: a commit allowed unchecked ("skip") or red ("run") keeps no durable record of that, such as a trailer, a note or a log. The only trace is the stderr notice, which asks the agent to "say so when you report it". The owner-approved text for the protected, unknown and red messages no longer names the command that ran (#613). No hook output in the repository records lineage. The Python twin is `_skipped` and `_other_failed` in `adapters/python/hooks/pre_commit_gate.py`. | Consider recording the gate's verdict (branch, mode, command, result) where review sees it, such as a git note or a commit trailer, opt-in by a config key | P8 — State-first lineage |
| `adapters/adapter-contract.md` | 33 | — | needs-review | The #615 premise "on a case-insensitive filesystem `git checkout Main` is on `main`" is a claim about git that no row checks. Every case-alias row sets `headRef: refs/heads/Main` and `core.ignorecase` on CI's case-sensitive filesystem. Unlike the commit-hook bullet ("checked with git 2.39"), nothing records which git the claim was checked with. ADR-0018's 2026-09-30 amendment makes git the reference wherever a row encodes git's behaviour. The auditor could not run git outside its worktree to check the claim. A filesystem probe on APFS did confirm that `Master` and `maſter` resolve to `master`. If the claim is wrong, the guard over-protects (it fails closed), so it lets nothing through. | Record the git version and filesystem the claim was checked on, or add a macOS CI row that reaches the alias through `git checkout` rather than `headRef` | P1 — Source-truth layer |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| Pre-commit gate CLI verdict, exit code and stderr (`adapters/js/hooks/pre-commit-gate.mjs`, `adapters/python/hooks/pre_commit_gate.py`) | yes: each reason names the branch, or why it is unknown, and the mode on "skip" | yes: an unknown branch is its own kind, treated as protected; "skip" says the commit is unchecked, never passed | partial: names the branch, not the command (protected, unknown and red messages) or the config; not stored (advisory adoption gap, P8 — State-first lineage) | yes: `preCommitGate` rows of `adapters/commit-hook-cases.json` v1; both runners refuse a field, kind or version they do not interpret | yes: unknown branch, unchecked commit, "no gates configured" | yes: 47 rows with exact `expectStderr`, run by both twins |
| `classifyBranch` / `classify_branch` | yes: the kind, with the protected name or the reason | yes: an `unknown` kind | n/a: in-process value, consumed at once | partial: the shape is in docstrings, pinned by unit tests in both twins, not by table rows | yes: `unknown` | yes: unit assertions in both twins |
| Branch guard verdict with `ignoreCase` (`decide` and the CLI, `branch-guard.mjs`, `branch_guard.py`) | yes: the reason names the protected branch as configured | yes: an unknown branch blocks a code edit, never a pass | n/a: transient hook verdict, not stored (same adoption gap) | yes: `hook-cases.json` and the `branchGuard` rows of `commit-hook-cases.json` | yes: unknown branch | yes: exact-text rows |
| `protectedMatch` / `protected_match`, `isCaseAlias` / `is_case_alias` | yes: returns the configured name | n/a: a match or no match | n/a | partial: unit tests in both twins; no row on a runtime-dependent mapping (violation above, P1 — Source-truth layer) | yes: null or None | partial: the `maſter` rows only |
| `ignoreCaseFrom` / `readIgnoreCase` (and Python twins) | n/a: a boolean | NO: exit 0 with stdout it cannot read becomes a definite false (violation above, spine) | n/a | partial: unit rows in both twins pin the open case as false | NO: exit 0 with stdout it cannot read cannot be expressed as unknown | yes: unit rows |
| `resolveBranch` / `resolve_branch` (shared with the gate) | yes: `why` and `alsoWhy` say why a branch is unknown | yes: a null branch with its reason | n/a: in-process | partial: the shape is documented in docstrings; the gate checks the export exists (`COMMIT_HOOK_NEEDS`), not the shape | yes: null branch | yes: through the commit-hook and gate rows |
| Commit hook verdict (`judgeCommit` and `main`, `branch-guard-commit.mjs`, `branch_guard_commit.py`) | yes: the reason names the path and the branch, or HEAD | yes: unknown branch | n/a: transient hook verdict (same adoption gap) | yes: `commitHook` rows, v1 | yes: unknown branch | yes: exact-text rows |
| Boundary guard and branch guard config reasons (`readConfig` / `_read_config`, unknown-key message) | yes: names each unknown key and whose keys are whose | n/a: a refusal | n/a | yes: `hook-cases.json` rows pin the full text | yes: the config is refused, never read as a default | yes: exact-text rows |
| Bootstrap output `branch-guard.json` carrying `testsOnOtherBranches` (`skills/plumb-line-bootstrap/SKILL.md` Step 2, question 11) | yes: the builder's interview answer | n/a: a choice, not a measurement | partial: the answer is committed; the reason for it, such as no CI, is not | partial: validated when read (any other value blocks); the file has no version key | yes: absent means "skip", and the gate says the commit is unchecked | no: no baseline pins the installed file |

coverage: 2/21 files read, 19 partial, 0 not-read (100% examined; 10% read in full)

| File | Coverage |
| ---- | -------- |
| `adapters/adapter-contract.md` | partial: every changed line, plus §3, §4 and the Hook I/O convention |
| `adapters/commit-hook-cases.json` | partial: `_doc`, every `preCommitGate` and `branchGuard` row, and the #615 `commitHook` rows |
| `adapters/hook-cases.json` | partial: every changed row |
| `adapters/js/hooks/__tests__/branch-guard-commit.test.mjs` | partial: the changed tests |
| `adapters/js/hooks/__tests__/commit-hook-cases.test.mjs` | partial: the changed runner code |
| `adapters/js/hooks/__tests__/hook-cases.test.mjs` | partial: the changed lines |
| `adapters/js/hooks/__tests__/pre-commit-gate.test.mjs` | partial: the new #613 and #615 tests |
| `adapters/js/hooks/boundary-guard.mjs` | partial: `readConfig`, the changed lines |
| `adapters/js/hooks/branch-guard-commit.mjs` | partial: the changed lines, `git`, `resolveBranch`, `main` |
| `adapters/js/hooks/branch-guard.mjs` | partial: the new case helpers, `decide`, `readConfig`, `configFromEnv`, the CLI |
| `adapters/js/hooks/pre-commit-gate.mjs` | read |
| `adapters/python/hooks/boundary_guard.py` | partial: `_read_config`, the changed lines |
| `adapters/python/hooks/branch_guard.py` | partial: the new case helpers, `decide`, `_read_config`, `config_from_env`, `_main` |
| `adapters/python/hooks/branch_guard_commit.py` | partial: the changed lines, `_git`, `resolve_branch`, `_main` |
| `adapters/python/hooks/pre_commit_gate.py` | read |
| `adapters/python/hooks/test_branch_guard_commit.py` | partial: the changed tests |
| `adapters/python/hooks/test_commit_hook_cases.py` | partial: the changed runner code |
| `adapters/python/hooks/test_hook_cases.py` | partial: the changed lines |
| `adapters/python/hooks/test_hooks.py` | partial: the new #613 and #615 tests |
| `primitives/PARITY.md` | partial: the hooks paragraph and "When parity is waived" |
| `skills/plumb-line-bootstrap/SKILL.md` | partial: every changed line, plus Steps 2 to 4d |

scope note: findings are drawn from the read and partial set only, and a file read in part is not a clean file outside the parts read. This audit does not claim completeness. The parts left unread are code and rows this PR did not change.

The declared architecture is ADR-0018 with its amendments of 2026-09-28, 2026-09-30 and 2026-10-02, the last of which covers this PR. So P1 — Source-truth layer and P2 — One-way layering are scored in full. P2 — One-way layering: no new cross-layer use. The gate imports only the branch guard and its commit hook, both in the adapters layer. The tests' uses of `primitives/conformance/table-guards.mjs` and `primitives/python/tests/case_table_guards.py` are already recorded.

Check 10, a test changed to pass: two wiring tests in each twin changed what they expect. The "lines after it" test moved from a feature-branch code commit to a protected-branch docs commit, and the bootstrap-wiring test now expects the skip notice. This is a carve-out: behaviour changed on purpose under #613, the owner decision recorded in the ADR-0018 amendment of 2026-10-02 and in the CHANGELOG Breaking entry. New tests pin the red-commit path, so these changes are not flagged.

Evidence was gathered from a scratch copy of the tree at 0a97ee6, on macOS with Node v24.15.0 and Python 3.14.4. `adapters/js`: vitest passed 866 tests in 14 files. `adapters/python/hooks`: pytest passed 467 tests. The fold probe and the APFS probe are described in their findings. The session's worktree isolation refused git probes outside the repository, so git's own behaviour on a case-insensitive filesystem was not checked; that is the needs-review finding.

CHANGELOG.md and `docs/adr/0018-plumb-lines-own-source-truth-and-layers.md` changed in the same PR but are outside this scope. They were read for context only.

7 findings: 4 violations, 1 needs-review, 2 advisory

format-validation: scripts/check_report_format.py v6 — clean
