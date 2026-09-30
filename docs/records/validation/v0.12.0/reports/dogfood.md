report-format: v4
scope:               v0.11.5..77c8878 -- skills/ reference/portable-principles.md primitives/ adapters/ (diff-scoped, 71 files)
principles-revision: 1
date:                2026-09-30
commit:              77c887831d8d40bde550d6cdbb84c38e5b97a6ab

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture: ADR-0018 (source truth = `primitives/SPEC.md`, `primitives/conformance/*.json`, `reference/portable-principles.md`, and since the #517 amendment `adapters/hook-cases.json`; layers source truth → primitives → adapters → consumers, with the stated cross-layer uses), plus ADR-0019, ADR-0020 and ADR-0021 for this release's contracts. P1 — Source-truth layer and P2 — One-way layering are scored in full against it.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `primitives/PARITY.md` | 107, 117 | parity table and notes | violation | Says "`derive` output is always consistent (the checker returns no issues)". That is false. A clean `source` override is flagged as laundering, as the note just above it says. Since #556 in this release, `derive([fallback, real], f, {source: "real"})` is also flagged as `source over-claim` in both languages, and cases.json pins it. | Limit the claim to a `derive` with no `source` override, and make the table row say the same | P6 — Maturity vocabulary |
| `adapters/commit-hook-cases.json` | 2 | `_doc` | needs-review | `adapters/adapter-contract.md` line 113 calls this new table the commit hook's "parity contract", run by both twins. ADR-0018 §1, as amended for `hook-cases.json` (#517), does not list it as source truth. This repeats the gap the v0.11.5 dogfood filed as #517. | Add an ADR-0018 amendment declaring it source truth (or say why not) before tagging | P1 — Source-truth layer |
| `adapters/js/hooks/__tests__/commit-hook-cases.test.mjs` | 12 | — | needs-review | An adapter test imports the consumer `primitives/conformance/table-guards.mjs`. ADR-0018's amendment records this use for `hook-cases.test.mjs` only, and says the planned layering test must allow such uses by name. | Record it in the same ADR-0018 amendment | P2 — One-way layering |
| `primitives/conformance/run-cases.mjs` | 213–225 | `judgeGuardThrow` | needs-review | The JS and Python runners read a guard row's `expectError` differently. Python requires a `TypeError`. JS accepts any throw outside the refusal's prototype chain, so a `RangeError` would pass. No JS test pins a `TypeError` for a bad `minSource`. SPEC §5c "Programmer errors" says only "an error", while ADR-0020 and SPEC's `minSource` paragraph say `TypeError`. | Make SPEC §5c state the error kind, then have every runner assert it | P7 — Contracted outputs |
| `primitives/PARITY.md` | 143–187 | Handed envelopes, resolved (#525) | needs-review | The counts ("20 of 28", "143-input probe leaves 19 differences") come from a probe that is not in the repo. The 19 residual differences are not recorded under "When parity is waived", yet the heading says "resolved" and the file's rule is that counts are run, not typed. | Commit the probe or cite where it lives, and record the residue as a waiver with an issue, or pin it in cases.json | P8 — State-first lineage |
| `skills/plumb-line-method/SKILL.md` | 55–58 | What this does not forbid: "A wrong test gets fixed" | needs-review | The method requires "say what was wrong and whose decision set the new expectation". The audit carve-out (`skills/plumb-line-audit/SKILL.md` line 64) exempts "a wrong test fixed with its reason stated", and line 63 of that file says "A stated reason alone is not a decision". The two skills set different bars. | Align the audit carve-out with the method wording, or record why they differ | spine — null-result expressibility |
| `skills/plumb-line-method/SKILL.md` | 171 | Mid-task: other moments, hardcoded-prior row | needs-review | The "yes, and" answer is "a named config value noting where it came from". It drops "versioned", which P5 and audit check 3 require, so the audit could flag the version the method teaches as honest. | Carry "versioned" into the row | P5 — Injectable priors |
| `skills/plumb-line-method/SKILL.md` | 170 | Mid-task: other moments, fallback row | needs-review | The row allows "the stand-in labelled as a fallback" in the output with no opt-in clause. P4 and audit check 8 require exclusion from outputs unless opted in. The method's own stub carve-out (line 63) keeps that clause. | Add the opt-in clause, or state that the builder's request is the opt-in | P4 — Quarantined fakery |
| `skills/plumb-line-adopt/SKILL.md` | 202–206 | Surfacing mid-task | needs-review | "The lightest tracking that fits is enough: a label on the value…" is unqualified for a stand-in that reaches an export or an aggregate. That is the case check 8 flags. | Qualify it: enough while the stand-in stays out of exports, or where the builder opted in | P4 — Quarantined fakery |
| `skills/plumb-line-method/SKILL.md` | 146–147 | When the requirement cannot be met | needs-review | The skill points to `examples/honest-deferral/`, a consumer-to-consumer use that ADR-0018 §2 does not state. Existing pointers from skills to `reference/fit-map.md` follow the same unrecorded pattern. Whether a doc pointer counts as a dependency is undecided. | Rule in an ADR-0018 amendment whether doc pointers are dependencies, and list them if they are | P2 — One-way layering |
| `primitives/js/vitest.mjs` | 41–45 | `markFixture` | advisory | The fixture helpers (and the Python twin `_quarantine`, `pytest_plugin.py` 50–58) mark a value `mock` without recording which fixture produced it. `guard`'s `mock:` reason names no step, so a failing `assertNoTaint` cannot say which fixture leaked. Checked: both twins print only "mock: the value derives from mock data…". | Record the fixture's name in `basis` (or `adapter`), or have the `mock:` reason name the tainted step | P8 — State-first lineage |
| `primitives/python/tests/test_conformance.py` | 89–91, 148–151 | `test_combine_cases`, `_envelope_problems` | advisory | `expect` is compared with `==` (`True == 1`, and a missing key reads as `None`). The JS runner uses `isDeepStrictEqual`. `_strict` exists in this file but is used only for lineage. No current row passes vacuously. | Use `_strict` with a missing-key sentinel, and plant a bool-vs-number row | P7 — Contracted outputs |
| `primitives/python/tests/test_conformance.py` | 238–252 | `test_guard_cases` | advisory | The guard row-shape checks, and the unknown-field and unknown-kind checks, have no planted bad row. The JS runner proves each one (`conformance-runner.test.mjs`), and Python does so only for construct and derive (`_BAD_ROWS`). | Factor the checks out and table-test them with planted rows | spine — null-result expressibility |
| `primitives/conformance/run-cases.mjs` | 113–123 | `runDerive` | advisory | The inputs are marked inside the `try` that judges `expectError`, so a port whose `mark` threw a matching message would pass a derive `expectError` row. Python marks outside the `try`. No current row is affected. | Mark the inputs before the `try` | P7 — Contracted outputs |
| `primitives/conformance/README.md` | 60 | Certifying a port | advisory | The new combine field `expectLineage` (4 rows) is named neither here nor in `primitives/SPEC.md` §7 (lines 614–617). A port that follows the explicit list could skip whole-lineage assertions. | Name `expectLineage` in both | P7 — Contracted outputs |
| `primitives/js/vitest.test.mjs` | 99–103 | "never imports vitest" | advisory | The test is a regex over the source for `from "vitest"`. A side-effect or dynamic import would pass it. The Python twin proves its claim by making `pytest` unimportable. | Load the module with `vitest` unresolvable, or rename the test | spine — null-result expressibility |
| `primitives/python/tests/test_pytest_plugin.py` | 137–146 | `test_the_plugin_registers_itself_under_its_module_name` | advisory | The test only reads `pyproject.toml`. No pytest session loads the plugin through the `pytest11` entry point or `-p`, yet `primitives/python/README.md` states load and disable behaviour. | Add one pytester run against the installed name, or word the README as configuration | P6 — Maturity vocabulary |
| `primitives/js/provenance.mjs` | 270–281 | `combineConfidenceScore` | advisory | The #560 fold here has no failing test. `long-lineage.test.mjs` calls it with only 1–3 scores, so reverting to `Math.min(...scores)` stays green. It also still copies with `Array.from`, which follows iterators and which the #560 third review replaced elsewhere. | Add a 200,000-score test (both twins), and use the plain index copy | spine — null-result expressibility |
| `skills/plumb-line-method/SKILL.md` | 159–166 | Mid-task: other moments, intro | advisory | "Yes, and: meet the need" softens the source-truth one-line test ("stop and document the concern before implementing", `reference/portable-principles.md` 38–40). The owner ruling on #485 supports the softer stance, but the principles file was not amended. | Amend the one-line test and bump the principles revision, or reword the skill as documenting the concern | P6 — Maturity vocabulary |
| `skills/plumb-line-method/SKILL.md` | 172 | Mid-task: other moments, maturity row | advisory | The row redefines `mock` as "stubbed, returns success without doing the work", narrower than the principles file's "placeholder returning fake or hardcoded data". | Use the principles definition, or point to it | P6 — Maturity vocabulary |
| `skills/plumb-line-method/SKILL.md` | 139–141 | When the requirement cannot be met | advisory | The skill says the observable-failure test, "not the marker", is what stops a crash hiding behind a deferral. In Python, `raises=AssertionError` on the marker does that, as lines 127–129 and `examples/test_honest_deferral.py` show. | Scope the sentence to JS | spine — null-result expressibility |
| `skills/plumb-line-method/SKILL.md` | 51–54, 70–72 | What this does not forbid | advisory | "Behaviour you changed on purpose" (tests of a removed feature) asks you to say the change was intended. "Decided changes" (a test removed with its behaviour) asks you to say whose decision it was. These are two bars for one case. | Pick one bar for test removal | spine — null-result expressibility |
| `skills/plumb-line-bootstrap/SKILL.md` | 195–210 | Hook I/O contract (for wiring) | advisory | A near-verbatim copy of the git-behaviour paragraph in `adapters/adapter-contract.md` line 113, which is already the contract bootstrap tells you to read. Nothing pins the two copies together, and the #547 re-review already had to edit both. | Keep the wiring lines and point to adapter-contract for git's behaviour | P7 — Contracted outputs |

| Output | Provenance | Confidence | Lineage | Contract | Null-expressible | Baseline |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `guard` (`primitives/js/guard.mjs`, `primitives/python/guard.py`) | yes: returns the marked value and its envelope unchanged | yes: `minConfidence` judged over the whole lineage | partial: a refusal lists reasons, but `mock:` names no step or fixture (advisory above, P8 — State-first lineage) | yes: SPEC §5c and the `guard` kind in cases.json; error kind unsettled (needs-review above, P7 — Contracted outputs) | yes: `ProvenanceRefused` with reasons; a bad option is a separate `TypeError` | yes: 52 `guard` rows, run by both twins |
| `makeMeta` / `make_meta` / `mark` | yes: `source` required (#177) | yes: `confidence` on the ladder, default `none` | yes: `lineage` field, steps copied (JS: frozen) | yes: SPEC §1–§2, `PROVENANCE_VERSION` 2, `validateEnvelope` | yes: refuses a missing or off-ladder source, confidence or taint flag | yes: 18 `construct` rows |
| `combineProvenance` / `combine_provenance` | yes: `source: derived`, per-step sources | yes: weakest confidence, score floor | yes: lineage steps with content-addressed ids | yes: SPEC §3–§4, `combine` kind | yes: `weakestSource` omitted when unknown; zero inputs give `unavailable` | yes: 24 `combine` rows incl. `expectLineageIds` |
| `derive` (both twins) | yes | yes | yes | yes: SPEC §2 derive rules, `derive` kind | yes: refuses an unmarked input or non-list inputs | yes: 5 `derive` rows |
| `auditMeta` / `audit_meta` | n/a: a report on the envelope it is given | n/a | n/a: pure function of its input | yes: SPEC §5 issue prefixes, checks 1–10 | yes: an empty list is the clean result | yes: 39 `audit` rows |
| `stepId` / `step_id` | n/a | n/a | yes: hash of the step and its sorted input ids | yes: SPEC §4 canon | n/a | yes: `expectLineageIds` rows |
| `markFixture` / `plumb_mock_fixture` | yes: `source: mock` | yes: `none` | NO: a leaf with no record of which fixture made it (advisory above, P8 — State-first lineage) | partial: ADR-0021 plus unit tests; no cases.json kind | yes: refuses a value that is already marked | no: unit tests only |
| `assertNoTaint` / `assertTainted` / `assert_no_taint` / `assert_tainted` | n/a: a verdict | n/a | partial: the failure message carries guard's reasons | partial: message prefixes pinned in each language's unit tests | yes: `assertTainted` fails a refusal made for another reason | no: unit tests only |
| branch-guard commit hook CLI (`branch-guard-commit.mjs`, `branch_guard_commit.py`) | yes: the reason names where the branch came from (HEAD, rebase head-name) | n/a: a binary verdict | partial: names the first blocked path and branch, not the config used | yes: Hook I/O convention v1 and `commit-hook-cases.json`; not declared source truth (needs-review above, P1 — Source-truth layer) | yes: an unknown branch blocks as inconclusive, never a pass | yes: 53 rows run by both twins in real repos |
| boundary guard `decide` (#516 change) | n/a | n/a | n/a | yes: `adapters/hook-cases.json` | yes: no layers now blocks, not passes | yes: hook-cases rows |
| SARIF PB1–PB4 rules (`adapters/sarif/assemble.py`) | n/a: a catalogue | n/a | n/a | yes: SARIF 2.1.0, names held to the SPEC §6 table by `test_assemble.py` | n/a | yes: test pins names and descriptions to SPEC §6 |
| baseline CLI `show` taint label (`baseline-cli.mjs`, `baseline.py`) | yes: prints each step's source | yes: prints each step's confidence | partial: prints steps, not reproduction inputs | no: human-readable CLI text, no versioned contract | yes: a malformed flag is named, not read as clean | no: unit tests only |
| audit skill report (`skills/plumb-line-audit/SKILL.md`) | yes: header scope and commit | yes: Status column | yes: principles revision, commit, coverage map | yes: report-format v4 and `scripts/check_report_format.py` | yes: an explicit `No findings.` line | no: scored by the release harness per run, not pinned |

```
coverage (read = the file's diff read in full, and the whole file where new):
read     skills/plumb-line-audit/SKILL.md
read     skills/plumb-line-remediate/SKILL.md
read     skills/plumb-line-method/SKILL.md            (whole file, sub-auditor)
read     skills/plumb-line-bootstrap/SKILL.md         (whole file, sub-auditor)
read     skills/plumb-line-adopt/SKILL.md             (whole file, sub-auditor)
read     reference/portable-principles.md
read     primitives/SPEC.md
read     primitives/PARITY.md                         (sub-auditor)
partial  primitives/README.md                         (diff hunk only, sub-auditor)
read     primitives/conformance/README.md             (sub-auditor)
read     primitives/conformance/cases.json            (all 105 new rows; older rows counted, not re-read; sub-auditor)
read     primitives/conformance/run-cases.mjs         (sub-auditor)
partial  primitives/js/README.md                      (diff hunk only, sub-auditor)
read     primitives/js/audit.mjs
read     primitives/js/baseline-cli.mjs
read     primitives/js/guard.mjs
read     primitives/js/index.mjs
read     primitives/js/marked.mjs
read     primitives/js/package-lock.json
read     primitives/js/package.json
read     primitives/js/provenance.mjs
read     primitives/js/vitest.mjs
read     primitives/js/audit.test.mjs                 (sub-auditor)
read     primitives/js/baseline-cli.test.mjs          (sub-auditor)
read     primitives/js/conformance-runner.test.mjs    (sub-auditor)
read     primitives/js/conformance.test.mjs           (sub-auditor)
read     primitives/js/fit-map-snippets.test.mjs      (sub-auditor)
read     primitives/js/guard.test.mjs                 (sub-auditor)
read     primitives/js/long-lineage.test.mjs          (sub-auditor)
read     primitives/js/marked.test.mjs                (sub-auditor)
read     primitives/js/provenance.test.mjs            (sub-auditor)
read     primitives/js/vitest.test.mjs                (sub-auditor)
partial  primitives/python/README.md                  (diff hunk only, sub-auditor)
read     primitives/python/__init__.py
read     primitives/python/arrays.py
read     primitives/python/audit.py
read     primitives/python/baseline.py
read     primitives/python/frames.py
read     primitives/python/guard.py
read     primitives/python/marked.py
read     primitives/python/provenance.py
read     primitives/python/pyproject.toml
read     primitives/python/pytest_plugin.py
read     primitives/python/tests/test_arrays.py       (sub-auditor)
read     primitives/python/tests/test_audit.py        (sub-auditor)
read     primitives/python/tests/test_baseline_cli.py (sub-auditor)
read     primitives/python/tests/test_conformance.py  (sub-auditor)
read     primitives/python/tests/test_frames.py       (sub-auditor)
read     primitives/python/tests/test_guard.py        (sub-auditor)
read     primitives/python/tests/test_long_lineage.py (sub-auditor)
read     primitives/python/tests/test_marked.py       (sub-auditor)
read     primitives/python/tests/test_provenance.py   (sub-auditor)
read     primitives/python/tests/test_pytest_plugin.py (sub-auditor)
read     adapters/adapter-contract.md
partial  adapters/commit-hook-cases.json              (_doc, all 53 row names and exit codes; about 7 rows in full)
read     adapters/hook-cases.json
read     adapters/js/hooks/boundary-guard.mjs
read     adapters/js/hooks/branch-guard-commit.mjs
read     adapters/js/hooks/branch-guard.mjs
read     adapters/js/package-lock.json
read     adapters/js/hooks/__tests__/boundary-guard.test.mjs
read     adapters/js/hooks/__tests__/branch-guard-commit.test.mjs
read     adapters/js/hooks/__tests__/commit-hook-cases.test.mjs
read     adapters/python/hooks/boundary_guard.py
read     adapters/python/hooks/branch_guard.py
read     adapters/python/hooks/branch_guard_commit.py
partial  adapters/python/hooks/test_branch_guard_commit.py (test names and the bootstrap-wiring tests only)
partial  adapters/python/hooks/test_commit_hook_cases.py   (lines 200-350: build tail, run, guards, row loop)
read     adapters/python/hooks/test_hooks.py
read     adapters/sarif/assemble.py
read     adapters/sarif/test_assemble.py
coverage: 65/71 files read, 6 partial, 0 not-read (92% read)
scope note: findings are drawn from the read and partial sets only; the partial files'
unread parts carry no finding, and that is not a clean result. Behaviour claims were
checked by running both twins on probe inputs (macOS). Three sub-auditors read the files
marked "sub-auditor"; the lead spot-checked each finding that came from them. This audit
does not claim completeness.
```

format-validation: not run (the host refused writing this report to a temp file, so scripts/check_report_format.py could not be run on this text; run it on this message as delivered)

23 findings: 1 violation, 9 needs-review, 13 advisory

---

The release harness's Part 2 dogfood self-audit for v0.12.0 is done. It found 23 findings: 1 violation, 9 needs-review and 13 advisories. **The format checker was not run:** the host blocked writing the report to a temp file, so I stamped the report `not run` rather than `clean`. The harness's pre-tag checks say to run the checker on the report as delivered, so it should be run on this message.

**How it was done:**
- **Who read what:** I read the primitives' guard, provenance, audit and marked code and the adapters' commit-hook wrappers and guards myself. Three read-only sub-auditors covered the primitives tests, the conformance tables and parity docs, and the method/bootstrap/adopt skills. I spot-checked their main findings against the code.
- **No repo changes:** nothing in the repository was modified and no branch was switched. Two sub-auditors' pytest runs rewrote the git-ignored `primitives/python/.coverage` through the configured `--cov`; `git status` stayed clean. My probe scripts are in `<harness>/work/dogfood/probe/`.

**What matters most:**
- **The violation:** `primitives/PARITY.md` line 117 says `derive` output always audits clean. That is false, and this release's #556 made it false in more cases.
- **The #517 gap came back:** the new `adapters/commit-hook-cases.json` is called a parity contract, but ADR-0018 does not declare it source truth. Its JS runner's import of `table-guards.mjs` is also unrecorded.
- **The runners disagree on `expectError`:** JS accepts any error type for a guard row's `expectError`, while Python requires a `TypeError`. SPEC §5c and ADR-0020 also differ on whether `TypeError` is required.
- **The method skill contradicts the audit skill** in several places, most importantly on the bar for fixing a "wrong" test. The method also drops "versioned" from its prior advice and the opt-in clause from its fallback advice.

**What held up:**
- The new guard, the constructor refusals, the #551/#553/#556 audit checks and the commit-hook wrappers agree between JS and Python on everything read. My probes on guard gave identical results in both languages.
- All three conformance runners interpret every kind and field in the table, and all 146 cases pass in both languages.
- #516 is resolved: the boundary guard now blocks when no layers are configured.

**Outside the diff's scope (not in the findings table):**
- `CHANGELOG.md` line 115 and ADR-0021 line 32 say "40 `guard` rows"; the table has 52.
- `CHANGELOG.md`'s #464 entry says a hand-made commit at a rebase stop blocks "even on a feature branch", but its #547 entry says such a commit now uses the branch being rebased.

**Next steps for the harness:** record the run in `docs/records/dogfood/v0.12.0.md` with a row in `docs/dogfood.md`. Each finding is either fixed in place or filed as an `audit-deferral` issue. Dogfood findings do not block the tag.

## Decisions needed
1. **commit-hook-cases.json:** declare it source truth in an ADR-0018 amendment, and in the same amendment record `commit-hook-cases.test.mjs`'s import of `table-guards.mjs`. Recommend yes, before tagging, as you decided for `hook-cases.json` in #517.
2. **The one-line test in the principles file:** amend it to match the method skill's "yes, and" stance (your #485 ruling) and bump the principles revision, or reword the skill. Recommend amending and bumping to revision 2.
3. **Error type for a bad guard option:** SPEC §5c says only "an error", ADR-0020 says `TypeError`. Recommend making `TypeError` required for every bad option in SPEC §5c, as ADR-0020 decided, and having all three runners assert it.
4. **Skills pointing at `examples/` and `reference/fit-map.md`:** decide whether a doc pointer counts as a dependency under ADR-0018. Recommend ruling that it does not, recorded in an amendment, so the planned layering test does not have to list prose links.