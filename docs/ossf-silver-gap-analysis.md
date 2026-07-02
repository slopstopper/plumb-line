# OpenSSF Best Practices — Silver badge gap analysis

Status of plumb-line against the **Silver** level of the [OpenSSF Best
Practices badge](https://www.bestpractices.dev) (project
[#13453](https://www.bestpractices.dev/projects/13453)). Silver requires **all
passing-level criteria** plus the additional criteria below. Criteria and
statuses are taken from the badge project's own
[`criteria.yml`](https://github.com/coreinfrastructure/best-practices-badge/blob/main/criteria/criteria.yml).

Legend: ✅ met · 🟡 partial / needs a form justification · ❌ not yet · N/A not
applicable (still needs a written justification in the badge form).

> **Prerequisite:** Silver cannot be awarded until the **passing** badge is at
> 100%. This analysis assumes passing is complete; confirm on the project page
> before submitting Silver answers.

---

## Scorecard summary

| Area | MUST met | Real work remaining |
| --- | --- | --- |
| Basics / oversight | most | **GOVERNANCE.md** (governance + roles + access continuity), bus factor, DCO |
| Documentation | all ✅ | — |
| Change control / reporting | all ✅ | — |
| Quality | most | **test coverage ≥80% measurement**, lint enforcement on own code |
| Security | most ✅ (strong) | crypto/hardening N/A justifications, signed tags (optional) |
| Analysis | ✅ / N/A | dynamic-analysis N/A justification |

**Three concrete deliverables close almost every gap:**
1. Add `GOVERNANCE.md` — satisfies `governance`, `roles_responsibilities`, and
   `access_continuity` (3 MUSTs) in one file.
2. Add statement-coverage measurement to CI and confirm ≥80% —
   `test_statement_coverage80`.
3. Add a lint step on the repo's own code (ESLint + Ruff) —
   `coding_standards_enforced` and `warnings_strict`.

Everything else is either already true (needs the badge form filled in) or a
legitimate N/A that needs a one-line justification.

---

## Basics

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `achieve_passing` | MUST | 🟡 | Passing badge exists (#13453). Verify it reads 100% before Silver. |
| `contribution_requirements` | MUST | ✅ | `CONTRIBUTING.md`: single-change focus, failing test required, CI must pass, CHANGELOG update, coding-style section. |
| `dco` | SHOULD | ❌ | No Developer Certificate of Origin / sign-off. `CONTRIBUTING.md` "License of contributions" relies on Apache-2.0 §5 (inbound=outbound). Acceptable alternative, but DCO is what the criterion names. |
| `governance` | MUST | ❌ | No `GOVERNANCE.md`. Decision-making model is undocumented. |
| `code_of_conduct` | MUST | ✅ | `CODE_OF_CONDUCT.md` (Contributor Covenant), linked from CONTRIBUTING. |
| `roles_responsibilities` | MUST | 🟡 | `.github/CODEOWNERS` documents ownership; roles/responsibilities not written up. Fold into `GOVERNANCE.md`. |
| `access_continuity` | MUST | ❌ | Continuity of access (repo, npm, PyPI, tags, key material) not documented. Fold into `GOVERNANCE.md`. |
| `bus_factor` | SHOULD | ❌ | Currently 1 (solo maintainer). Structural; see plan. |

### Documentation

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `documentation_roadmap` | MUST | ✅ | `ROADMAP.md` — milestones + numbered planned items. |
| `documentation_architecture` | MUST (N/A ok) | ✅ | `docs/adr/` (9 ADRs), `docs/threat-model.md`, `primitives/SPEC.md`, `primitives/README.md`. |
| `documentation_security` | MUST (N/A ok) | ✅ | `SECURITY.md` + `docs/threat-model.md` state what users can and cannot rely on. |
| `documentation_quick_start` | MUST (N/A ok) | ✅ | README "Install" + runnable `mark`/`derive` quick-start snippet. |
| `documentation_current` | MUST (N/A ok) | ✅ | `CHANGELOG.md` kept current; `documentation_current` maintained per release. |
| `documentation_achievements` | MUST | ✅ | README badge row + "Status" section describe achievements (Scorecard, coverage of adapters, conformance). |

### Accessibility, i18n, other

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `accessibility_best_practices` | SHOULD (N/A ok) | 🟡 | Static docs site (`docs/index.html`, `feedback.html`). Either confirm basic a11y or mark N/A (developer library). |
| `internationalization` | SHOULD (N/A ok) | N/A | Provenance library; no user-facing localizable UI. Justify N/A. |
| `sites_password_security` | MUST (N/A ok) | N/A | GitHub Pages static site stores no passwords. Justify N/A. |

---

## Change control

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `maintenance_or_update` | MUST (N/A ok) | ✅ | `SECURITY.md` "Supported versions" — fixes land on latest published minor; no pre-1.0 backport branch (stated). |

---

## Reporting

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `report_tracker` | MUST (N/A ok) | ✅ | GitHub Issues + `.github/ISSUE_TEMPLATE/`. |
| `vulnerability_report_credit` | MUST (N/A ok) | ✅ | `SECURITY.md` "Disclosure" credits reporter in advisory + changelog. |
| `vulnerability_response_process` | MUST | ✅ | `SECURITY.md` documents private reporting, acknowledgement window, embargo, fix, credit. |

---

## Quality

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `coding_standards` | MUST (N/A ok) | ✅ | `CONTRIBUTING.md` "Coding style" names ES-module + `const`/arrow conventions and PEP 8. |
| `coding_standards_enforced` | MUST (N/A ok) | ❌ | No linter on the repo's own code (CONTRIBUTING: "no enforced formatter"). Enforcement is review-only today. |
| `build_standard_variables` | MUST (N/A ok) | N/A | Interpreted JS/Python; no `CC`/`CFLAGS`. Justify N/A. |
| `build_preserve_debug` | SHOULD (N/A ok) | N/A | No compiled artifacts. Justify N/A. |
| `build_non_recursive` | MUST (N/A ok) | N/A | No recursive make. Justify N/A. |
| `build_repeatable` | MUST (N/A ok) | ✅ | Deterministic package builds; hash-pinned test deps (`--require-hashes`); pinned toolchain in release. |
| `installation_common` | MUST (N/A ok) | ✅ | `npm install` / `pip install`, plus Claude Code plugin path. |
| `installation_standard_variables` | MUST (N/A ok) | N/A | `DESTDIR` etc. not meaningful for npm/pip. Justify N/A. |
| `installation_development_quick` | MUST (N/A ok) | ✅ | `CONTRIBUTING.md` "Running the tests" gives one-line setup per package. |
| `external_dependencies` | MUST (N/A ok) | ✅ | `package.json` (zero runtime deps), `pyproject.toml`, hash-pinned `requirements-test.txt`. |
| `dependency_monitoring` | MUST (N/A ok) | ✅ | Dependabot (4 ecosystems) + OpenSSF Scorecard + Socket badge. |
| `updateable_reused_components` | MUST (N/A ok) | ✅ | Zero runtime deps; dev/test deps updateable via Dependabot. |
| `interfaces_current` | SHOULD (N/A ok) | ✅ | Tracks current Node/Python; envelope schema versioned (`PROVENANCE_VERSION`). |
| `automated_integration_testing` | MUST | ✅ | CI runs cross-language conformance report + `examples` import-linter boundary integration test. |
| `regression_tests_added50` | MUST (N/A ok) | ✅ | Policy in `CONTRIBUTING.md`: "New behaviour needs a test that fails without it." Confirm ≥50% of fixed bugs carry a regression test. |
| `test_statement_coverage80` | MUST (N/A ok) | ❌ | No coverage measurement in CI. Suites are substantial but coverage is unmeasured/unproven. |
| `test_policy_mandated` | MUST (N/A ok) | ✅ | `CONTRIBUTING.md` requires tests for new functionality; CI gates it. |
| `tests_documented_added` | MUST (N/A ok) | ✅ | Requirement documented in `CONTRIBUTING.md`. |
| `warnings_strict` | MUST (N/A ok) | 🟡 | No compiler warnings (interpreted). Satisfy by running ESLint / Ruff as errors in CI, or justify N/A. |

---

## Security

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `implement_secure_design` | MUST (N/A ok) | ✅ | Conservative-combination law with no taint-clearing escape hatch; documented in `docs/threat-model.md` + SPEC §6. |
| `crypto_weaknesses` | MUST (N/A ok) | N/A/✅ | Library implements no bespoke crypto system; relies on registry TLS + Sigstore attestations. Justify scope. |
| `crypto_algorithm_agility` | SHOULD (N/A ok) | N/A | No project-controlled crypto suite. Justify N/A. |
| `crypto_credential_agility` | MUST (N/A ok) | N/A/✅ | Release auth is OIDC trusted publishing — no stored long-lived credentials. Justify. |
| `crypto_used_network` | SHOULD (N/A ok) | ✅ | All network use (registries, Pages) is HTTPS/TLS. |
| `crypto_tls12` | SHOULD (N/A ok) | ✅ | Registries/GitHub enforce TLS ≥1.2. |
| `crypto_certificate_verification` | MUST (N/A ok) | ✅ | TLS verification never disabled; `pip --require-hashes` pins artifacts. |
| `crypto_verification_private` | MUST (N/A ok) | N/A | No private-key operations performed by the software. Justify N/A. |
| `signed_releases` | MUST (N/A ok) | ✅ | npm `--provenance` attestations + PyPI trusted-publishing attestations (Sigstore). Publicly verifiable. Note this in the form. |
| `version_tags_signed` | SUGGESTED | ❌ | Git tags are not GPG/Sigstore-signed. Optional at Silver. |
| `input_validation` | MUST (N/A ok) | ✅ | `auditMeta`/`audit_meta` + `validateEnvelope` validate envelope inputs; checker totality (ADR 0009). |
| `hardening` | SHOULD (N/A ok) | 🟡 | Library is secure-by-default; add site security headers or justify N/A for a static docs site. |
| `assurance_case` | MUST | ✅ | `docs/threat-model.md` is effectively an assurance case: property defended (taint cannot be laundered), actors, threats, honest non-guarantees, plus SPEC + SECURITY scope. Reference it directly in the form. |

---

## Analysis

| Criterion | Status | Have? | Evidence / gap |
| --- | --- | --- | --- |
| `static_analysis_common_vulnerabilities` | MUST (N/A ok) | ✅ | CodeQL (JS + Python) on push, PR, and weekly schedule (`.github/workflows/codeql.yml`). |
| `dynamic_analysis_unsafe` | MUST (N/A ok) | N/A | JS/Python are memory-safe; Valgrind/ASAN don't apply. Justify N/A. |

---

## What to implement, and when

### Phase 1 — documentation (≈ half a day, closes 3 MUSTs)
- **Add `GOVERNANCE.md`** covering, in one file:
  - *Governance model* — single-maintainer / BDFL-style decision-making, how
    proposals are raised (issue first), how ADRs record durable decisions
    (`governance`).
  - *Roles & responsibilities* — maintainer duties, reviewer expectations,
    how someone becomes a contributor/committer (`roles_responsibilities`).
  - *Access & continuity* — who holds repo/npm/PyPI/tag access, that release
    auth is OIDC (no shared secrets), and the succession plan if the maintainer
    becomes unavailable (`access_continuity`).
- Link `GOVERNANCE.md` from `README.md` and `CONTRIBUTING.md`.

### Phase 2 — test coverage (≈ 1 day, closes the main Quality gap)
- Add statement-coverage measurement to CI:
  - JS: `c8` (or nyc) around the existing `npm test`.
  - Python: `pytest --cov` (coverage.py) for `primitives/python` + `adapters/python`.
- Confirm each package meets ≥80% statement coverage; add tests where short.
- Optionally publish a coverage badge and record the numbers in
  `docs/validation-results.md` for `test_statement_coverage80`.

### Phase 3 — lint enforcement (≈ half a day)
- Add ESLint (JS) and Ruff (Python) configs matching the CONTRIBUTING style,
  run as a CI job with warnings treated as errors — satisfies
  `coding_standards_enforced` and `warnings_strict`. (Natural fit: the project
  already ships a lint adapter; this dogfoods lint on its own code.)

### Phase 4 — optional / ongoing
- **DCO** (`dco`, SHOULD): enable the DCO bot / require `Signed-off-by`, or keep
  the Apache-§5 statement and note it in the form.
- **Signed tags** (`version_tags_signed`, SUGGESTED): sign `v*` tags with GPG or
  Sigstore in the release process.
- **Bus factor** (`bus_factor`, SHOULD): recruit a second maintainer/reviewer;
  until then, document the honest state in `GOVERNANCE.md`.

### Phase 5 — fill in the badge questionnaire
Most remaining criteria are already satisfied or are legitimate N/As — they just
need answers + justifications entered at
<https://www.bestpractices.dev/projects/13453>. Use the "Evidence / gap" column
above as the source text. In particular, write short N/A justifications for the
build/installation/crypto/dynamic-analysis rows marked N/A, and point
`assurance_case` and `documentation_security` at `docs/threat-model.md`.

---

*Generated as a planning aid; the authoritative record is the badge
questionnaire itself.*
