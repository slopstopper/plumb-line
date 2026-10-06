report-format: v4
scope:               v0.12.0..origin/main -- skills/ reference/portable-principles.md primitives/ adapters/ (diff-scoped, 20 files)
principles-revision: 1
date:                2026-10-03
commit:              1a1afc2c3572c476893269ac93b9ff8fd4661325

```
P1 — Source-truth layer      P6 — Maturity vocabulary  P8 — State-first lineage
P2 — One-way layering        P7 — Contracted outputs   P9 — Golden baseline + explain-the-drift
P3 — Confidence + provenance
spine — null-result expressibility
```

Declared architecture: ADR-0018 and its amendments through 2026-10-02 (source truth = `primitives/SPEC.md`, `primitives/conformance/*.json`, `reference/portable-principles.md`, `adapters/hook-cases.json`, `adapters/commit-hook-cases.json`; layers source truth → primitives → adapters → consumers, with the stated cross-layer uses), plus ADR-0019 for the #602 and #594 amendments. P1 — Source-truth layer and P2 — One-way layering are scored in full against it.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `adapters/js/hooks/__tests__/pre-commit-gate.test.mjs` | 240–248 | "pins a known open divergence" | violation | Deferral #642 is the only open record of the fail-open divergence, and it says "Both routes are pinned by a unit test in each twin". Only the reordering route is pinned, here and in `adapters/python/hooks/test_hooks.py` 516–523. No test in either twin covers the composition route (branch `x` + U+105D2 + U+0307 against protected `x` + U+105C9), and `primitives/PARITY.md` 171–172 itself says only the reordering case is pinned. Checked: the composition pair blocks on Node 24.15.0 and Python 3.14.4, and is allowed on Python 3.11.15 and 3.13.13. | Add a runtime-conditional composition pin to each twin, like the reordering pin, or correct #642's text | P6 — Maturity vocabulary |
| `primitives/PARITY.md` | 148–172 | Open divergence, safe direction / fails open | needs-review | Both open, not-waived divergences cite only #625, which closed on 2026-10-03. The fail-open one is tracked by #642, but no file in the tree cites #642 (both pinning tests cite #625). The safe-direction one has no open issue at all: Python 3.11 blocks `mai🫎` against `main` and Node allows it (reproduced). AGENTS.md says a deferral requires a filed issue. | Cite #642 here and in both pinning tests. File the safe-direction divergence as an `audit-deferral`, or record the owner's ruling that "recorded, not waived" needs no tracker | P6 — Maturity vocabulary |
| `primitives/PARITY.md` | 129–172 | Case folding across Unicode versions | needs-review | The section types figures from a check that is not committed: "checked one code point at a time" across Node 22.23.3 and 24.15.0 and Python 3.11 to 3.14, then 15,104 and 4,803 code points Node knows and Python does not, 20 composing sequences, and 18 and 5 reordering marks. This release's #594 fix replaced exactly this kind of count in the same file with a committed probe and a test that holds the file to it. The auditor re-ran the Node 24.15.0 against Python 3.11.15 and 3.14.4 parts, and they match: 15,104, 4,803, 18 marks, and 5 marks (the same five code points). The Node 22 figures and the six-runtime fold agreement were not reproduced. | Commit the code-point sweep beside `handed_probe.py` and have a test hold these figures to its output. Otherwise label them a dated one-off measurement and name the tool | P8 — State-first lineage |
| `primitives/conformance/handed_probe.py` | — | — | needs-review | This new file has no layer in ADR-0018 §2. The consumers row lists `primitives/conformance/*.mjs` and the source-truth row lists `*.json`, but neither lists a `.py`. If the probe is a consumer, `scripts/test_handed_probe.py` loading it is a consumer-to-consumer use that §2 does not state. If it belongs to the primitives layer (its directory), its spawning of the consumer `handed-probe.mjs` is a primitives-to-consumer use. No amendment records either, although each earlier use of this kind was recorded (2026-09-28, 2026-09-30). | Add an ADR-0018 amendment that places the probe and records `scripts/test_handed_probe.py`'s use of it | P2 — One-way layering |
| `adapters/js/hooks/branch-guard.mjs` | 95–104, 147 | `protectedMatch`, `decide` | needs-review | When a match rests on a character the runtime does not know (one the docstring says "cannot be folded with certainty"), the block reason uses the words of an exact match: "on protected branch main". On Python 3.11 a branch `mai🫎` is told it is on `main`. It is not, and Node allows the same branch. The twin does the same (`adapters/python/hooks/branch_guard.py` 102–121, 166), and so does the gate's "`main` is a protected branch". A guess is reported as a fact. | Say in the reason when the match is through an unknown character (for example, "may be an alias of protected branch main: this runtime does not know U+…"), and pin it with case rows in both tables | P3 — Confidence + provenance |
| `primitives/js/provenance.mjs` | 166–167 | `makeMeta` | needs-review | The comment "Each refusal is a RangeError (#602, owner decision 2026-10-03)" covers all four throws. `primitives/js/marked.test.mjs` 233–236 says the same of the taint-flag refusal. But ADR-0019's #602 amendment records the type of the non-boolean `derivedFromMock` refusal as "Implementation choice, made in the PR, not by the owner", and `primitives/SPEC.md` 100–101 states it as law. The code credits the owner with a choice the decision record says the owner did not make. | Ask the owner to rule on the taint-flag refusal's type and amend ADR-0019, or word the comments as the ADR does | P3 — Confidence + provenance |
| `primitives/PARITY.md` | 115 | When parity is waived | needs-review | The waiver says "The taint, the computed ids and the guard's verdict and reason all agree." The probe (re-run: 224 inputs, 34 differ) shows 15 inputs whose guard reason text differs in the quoted value (`-0.0`/`0`, `1.0`/`1`, `{"a": 1}`/`{"a":1}`). ADR-0019's amendment and the section at 328–339 say "the same reason class and the same field". The owner approved this wording as drafted on #594, so "reason" may mean the reason class. | Say "verdict, reason class and field" | P6 — Maturity vocabulary |
| `primitives/conformance/handed_probe.py` | 371–409 | `run`, `main` | advisory | The probe's output (the printed counts and `--json`) records no lineage: not the probed tree's commit, and not the Node and Python versions whose JSON parsers produce the `number` class. PARITY.md's column says only "`main`". The same gap is deferred for `report.mjs --json` (#448). | Print the `--root` commit and both runtime versions in the output, and name them beside the table | P8 — State-first lineage |

| Output | Provenance | Confidence | Lineage | Contract | Null-expressible | Baseline |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `makeMeta` / `make_meta` refusals, and `mark` and `derive` overrides (`primitives/js/provenance.mjs`, `primitives/python/provenance.py`) | n/a — a refusal returns no value | n/a — a refusal returns no value | yes — the message quotes the refused value and the ladder | yes — the SPEC §2 type and message prefix, the cases.json construct and derive rows, and both runners require the type (P7 — Contracted outputs) | yes — the accepting path returns an envelope | yes — cases.json construct and derive rows; `marked.test.mjs` pins the full messages |
| `audit_meta` / `auditMeta` issues, `laundering:` and `taint dropped:` (`primitives/python/audit.py`) | yes — each issue names the field and the source it judged | n/a — a list of findings, not an estimate | n/a — judged from the envelope the caller holds and passes in | yes — SPEC §5 prefixes, the docs/api.md table, cases.json audit rows with the full text of both #635 messages | yes — an empty list | yes — cases.json audit rows |
| `guard` refusal reasons built from the audit | yes — the `audit:` prefix and the issue text | n/a — a verdict, not an estimate | n/a — the reasons name what was judged on the value passed in | yes — cases.json guard rows; `reasons` is a list of strings in both twins | yes — a pass returns the marked value | yes — cases.json guard rows, two of them new for #635 |
| `protectedMatch` / `protected_match` verdict, as the hooks' exit code and stderr reason (`adapters/js/hooks/branch-guard.mjs`, `adapters/python/hooks/branch_guard.py`) | yes — the reason names the protected name as configured | NO — a match through an unknown character is reported in the words of an exact match (P3 — Confidence + provenance) | partial — the reason does not say which rule matched (exact, fold, or unknown character) or the runtime's Unicode version; lineage is not adopted for hook reasons, so this is not a separate finding | yes — `adapters/commit-hook-cases.json` and `adapters/hook-cases.json`, source truth under ADR-0018's amendments (P7 — Contracted outputs) | yes — `null` / `None`, exit 0 | yes — 20 new case rows run by both twins (P9 — Golden baseline + explain-the-drift) |
| `isCaseAlias` / `is_case_alias`, which decides whether `core.ignorecase` is read | n/a — an internal boolean | n/a — an internal boolean | n/a — an internal boolean | indirect — through the case rows that need a repository's `core.ignorecase` | yes — false | yes — unit tests in both twins |
| `handed_probe.py` result, printed counts and `--json` (`primitives/conformance/handed_probe.py`) | partial — it names "JS vs Python", but not the tree probed | n/a — counts, not estimates | NO — no commit, Node or Python version recorded (P8 — State-first lineage) | no — `--json` has no version constant or validator; an internal tool, whose sibling `report.mjs --json` is deferred as #448 | yes — the `agree` count, and exit 0 when no outcome differs | yes — `scripts/test_handed_probe.py` holds PARITY.md's table to it; the pre-fix column only in a full clone |
| `handed-probe.mjs` records (`primitives/conformance/handed-probe.mjs`) | n/a — consumed only by `handed_probe.py` | n/a — consumed only by `handed_probe.py` | n/a — consumed only by `handed_probe.py` | by convention — the record shape mirrors the Python half's; no validator | yes — a pass is recorded as `{"pass": true}` | indirect — through the Python half's counts |
| `runCases` row verdicts (`primitives/conformance/run-cases.mjs`) | yes — the kind and row name | n/a — a verdict | yes — `describeCaseTable` records the table version and sha256 | partial — the row-result shape is internal; `report.mjs --json` has no contract (#448) | yes — `error: null` | yes — `conformance-runner.test.mjs` planted ports and rows |
| Python conformance runner verdicts (`primitives/python/tests/test_conformance.py`) | yes — the row name in each assertion | n/a — a verdict | partial — the table version is checked, no table hash is recorded | n/a — pytest's own pass or fail | yes — a passing row | yes — planted bad rows (#595) |
| PARITY.md counts: the handed-envelope table and the #625 Unicode figures (`primitives/PARITY.md`) | handed table: yes, the committed probe; #625 figures: NO, an uncommitted check | n/a — counts | handed table: yes; #625 figures: NO (P8 — State-first lineage) | n/a — prose | yes — zero-count rows and "no gap" are stated | handed table: yes, held by a test; #625 figures: no (P9 — Golden baseline + explain-the-drift) |

| File | Coverage |
| ---- | -------- |
| `adapters/adapter-contract.md` | partial — the changed §4 bullet |
| `adapters/commit-hook-cases.json` | partial — the 20 added rows |
| `adapters/js/hooks/__tests__/pre-commit-gate.test.mjs` | partial — the added #625 tests |
| `adapters/js/hooks/branch-guard.mjs` | partial — `fold`, `foldsAlike`, `protectedMatch`, `isCaseAlias` and their callers |
| `adapters/python/hooks/branch_guard.py` | partial — `_fold`, `_unknown`, `_folds_alike`, `protected_match` |
| `adapters/python/hooks/test_hooks.py` | partial — the added #625 tests |
| `primitives/PARITY.md` | partial — the changed sections (waivers, case folding, handed envelopes) |
| `primitives/SPEC.md` | partial — §2 (ladders and refusals) |
| `primitives/conformance/README.md` | partial — the added probe section |
| `primitives/conformance/cases.json` | partial — the 4 added rows |
| `primitives/conformance/handed-probe.mjs` | read |
| `primitives/conformance/handed_probe.py` | read |
| `primitives/conformance/run-cases.mjs` | partial — `judgeRefusal`, `thrownKind`, `judgeRow`, `runCases` |
| `primitives/js/conformance-runner.test.mjs` | partial — the added #602 block |
| `primitives/js/marked.test.mjs` | partial — the added #602 block |
| `primitives/js/provenance.mjs` | partial — `makeMeta` |
| `primitives/js/vitest.test.mjs` | partial — the added #597 block |
| `primitives/python/audit.py` | partial — the two changed messages and the module docstring |
| `primitives/python/tests/test_conformance.py` | partial — every changed hunk |
| `primitives/python/tests/test_pytest_plugin.py` | partial — the added #597 block |

```
coverage: 2/20 files read, 18 partial, 0 not-read (10%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness. Every
changed hunk in the 18 partial files was read in full; their unchanged parts
were read only as far as needed to judge the change. No file under skills/ or
reference/portable-principles.md changed in this range.
```

Behaviour checks, run on a scratch copy of the audited tree (macOS, Node 24.15.0, Python 3.14.4, plus 3.11.15 and 3.13.13 for the fold probes): `node primitives/conformance/report.mjs` passes 150/150. The Python suites `test_conformance.py`, `test_pytest_plugin.py`, `adapters/python/hooks/` (496) and `scripts/test_handed_probe.py` (33, 1 skipped by design without history) pass. The JS vitest files `pre-commit-gate`, `commit-hook-cases` and `hook-cases` (745) and `conformance-runner`, `marked`, `vitest` and `conformance` (326) pass, as does `check-bundle-sync.mjs`. `handed_probe.py --verbose` prints exactly PARITY.md's `main` column (224 inputs, 190 agree, 19 / 9 / 6), and the guard verdicts behind the waiver hold as stated. The #594 waivers match the owner's 2026-10-03 decision on #594: 15 + 12 + 3 waived, 4 by design, 2 fixed by #635. P1 — Source-truth layer: the new cases.json and commit-hook-cases.json rows are reproduced by both twins, and no single implementation's output was pasted in. P2 — One-way layering: no primitives runtime module imports an adapter or consumer, the hook twins add only the standard library, and the one gap found is the probe's unplaced layer above.

8 findings: 1 violation, 6 needs-review, 1 advisory

format-validation: scripts/check_report_format.py v6 — clean
