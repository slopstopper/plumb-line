# OpenSSF Best Practices — Silver badge gap analysis

Status of plumb-line against the **Silver** level of the [OpenSSF Best
Practices badge](https://www.bestpractices.dev) (project
[#13453](https://www.bestpractices.dev/projects/13453)). The **passing** badge
is already earned; Silver adds the criteria below. Criteria and statuses are
taken from the badge project's own
[`criteria.yml`](https://github.com/coreinfrastructure/best-practices-badge/blob/main/criteria/criteria.yml).

Legend: ✅ met · N/A not applicable (with justification) · ⚠️ SHOULD/SUGGESTED
not met (allowed at Silver).

> **How to use this doc:** the tables show status + evidence. The
> [Form-ready answers](#form-ready-answers) section at the bottom gives, per
> criterion, the exact **Met / N/A / Unmet** value and answer text to paste into
> the questionnaire.

---

## What changed to reach Silver

Three deliverables landed on branch `claude/ossf-silver-badge-gaps-66wk27`:

1. **`GOVERNANCE.md`** — documents the governance model, roles &
   responsibilities, and access/continuity. Closes `governance`,
   `roles_responsibilities`, `access_continuity`.
2. **Coverage gate** — `npm test` (vitest, both JS packages) and `pytest` (both
   Python packages) now measure statement coverage and **fail under 80%**.
   Actuals: primitives/js 98%, adapters/js 96%, primitives/python 96%,
   adapters/python 99%. Closes `test_statement_coverage80`.
3. **Enforced lint** — an ESLint + Ruff CI job (`.github/workflows/ci.yml`).
   Closes `coding_standards_enforced` and `warnings_strict`.

Remaining open items are all SHOULD/SUGGESTED (optional at Silver): `dco`,
`bus_factor`, `version_tags_signed`.

---

## Scorecard summary

| Area | State |
| --- | --- |
| Basics / oversight | ✅ governance, roles, continuity documented; ⚠️ `dco`, `bus_factor` optional & open |
| Documentation | ✅ all met |
| Change control / reporting | ✅ all met |
| Quality | ✅ coverage ≥80% gated, lint enforced, integration tests |
| Security | ✅ met (strong: threat model = assurance case, OIDC/provenance releases); ⚠️ `version_tags_signed` optional |
| Analysis | ✅ CodeQL; dynamic-analysis N/A (memory-safe langs) |

---

## Basics

| Criterion | Status | Evidence |
| --- | --- | --- |
| `achieve_passing` | ✅ | Passing badge earned (#13453). |
| `contribution_requirements` | ✅ | `CONTRIBUTING.md`: single-change focus, failing test required, CI + lint must pass, CHANGELOG update, coding-style + lint sections. |
| `dco` | ⚠️ | No DCO sign-off. `CONTRIBUTING.md` § *License of contributions* relies on Apache-2.0 §5 (inbound = outbound) — a valid alternative; DCO is optional at Silver. |
| `governance` | ✅ | `GOVERNANCE.md` § *How decisions are made*. |
| `code_of_conduct` | ✅ | `CODE_OF_CONDUCT.md` (Contributor Covenant), linked from CONTRIBUTING + GOVERNANCE. |
| `roles_responsibilities` | ✅ | `GOVERNANCE.md` § *Roles and responsibilities* + `.github/CODEOWNERS`. |
| `access_continuity` | ✅ | `GOVERNANCE.md` § *Access and continuity* (no stored secrets; OIDC release; transfer plan). |
| `bus_factor` | ⚠️ | Currently 1; documented honestly in `GOVERNANCE.md`. SHOULD, and a stated goal; optional at Silver. |

### Documentation

| Criterion | Status | Evidence |
| --- | --- | --- |
| `documentation_roadmap` | ✅ | `ROADMAP.md`. |
| `documentation_architecture` | ✅ | `docs/adr/` (9 ADRs), `docs/threat-model.md`, `primitives/SPEC.md`. |
| `documentation_security` | ✅ | `SECURITY.md` + `docs/threat-model.md` (what users can/can't rely on). |
| `documentation_quick_start` | ✅ | README "Install" + runnable `mark`/`derive` snippet. |
| `documentation_current` | ✅ | `CHANGELOG.md` kept current per release. |
| `documentation_achievements` | ✅ | README badge row + "Status" section. |

### Accessibility, i18n, other

| Criterion | Status | Evidence |
| --- | --- | --- |
| `accessibility_best_practices` | N/A | Developer library; static docs site only. |
| `internationalization` | N/A | No user-facing localizable UI. |
| `sites_password_security` | N/A | GitHub Pages static site stores no passwords. |

---

## Change control

| Criterion | Status | Evidence |
| --- | --- | --- |
| `maintenance_or_update` | ✅ | `SECURITY.md` § *Supported versions*. |

## Reporting

| Criterion | Status | Evidence |
| --- | --- | --- |
| `report_tracker` | ✅ | GitHub Issues + `.github/ISSUE_TEMPLATE/`. |
| `vulnerability_report_credit` | ✅ | `SECURITY.md` § *Disclosure*. |
| `vulnerability_response_process` | ✅ | `SECURITY.md` (private report → ack → embargo → fix → credit). |

---

## Quality

| Criterion | Status | Evidence |
| --- | --- | --- |
| `coding_standards` | ✅ | `CONTRIBUTING.md` § *Coding style* (ES modules; PEP 8). |
| `coding_standards_enforced` | ✅ | ESLint + Ruff CI job (`.github/workflows/ci.yml`); `ruff.toml`, `eslint.config.mjs` in each JS package. |
| `build_standard_variables` | N/A | Interpreted JS/Python; no `CC`/`CFLAGS`. |
| `build_preserve_debug` | N/A | No compiled artifacts. |
| `build_non_recursive` | N/A | No recursive make. |
| `build_repeatable` | ✅ | Deterministic npm/PyPI builds; hash-pinned test deps (`--require-hashes`); pinned release toolchain. |
| `installation_common` | ✅ | `npm install` / `pip install` + Claude Code plugin. |
| `installation_standard_variables` | N/A | `DESTDIR` etc. not meaningful for npm/pip. |
| `installation_development_quick` | ✅ | `CONTRIBUTING.md` § *Running the tests*. |
| `external_dependencies` | ✅ | `package.json` (zero runtime deps), `pyproject.toml`, hash-pinned `requirements-test.txt`. |
| `dependency_monitoring` | ✅ | Dependabot (4 ecosystems) + Scorecard + Socket. |
| `updateable_reused_components` | ✅ | Zero runtime deps; dev deps updateable via Dependabot. |
| `interfaces_current` | ✅ | Tracks current Node/Python; envelope schema versioned. |
| `automated_integration_testing` | ✅ | CI runs cross-language conformance report + `examples` import-linter boundary integration test. |
| `regression_tests_added50` | ✅ | Policy in `CONTRIBUTING.md`: a test that fails without the change is required; CI gates it. |
| `test_statement_coverage80` | ✅ | Coverage gated ≥80% in `npm test` + `pytest`; actuals 96–99%. |
| `test_policy_mandated` | ✅ | `CONTRIBUTING.md` requires tests for new functionality. |
| `tests_documented_added` | ✅ | Documented in `CONTRIBUTING.md`. |
| `warnings_strict` | ✅ | ESLint recommended + Ruff run as errors in CI (no warning-only mode). |

---

## Security

| Criterion | Status | Evidence |
| --- | --- | --- |
| `implement_secure_design` | ✅ | `docs/threat-model.md` + SPEC §6 (no taint-clearing escape hatch). |
| `crypto_weaknesses` | N/A | No bespoke crypto system; relies on registry TLS + Sigstore attestations. |
| `crypto_algorithm_agility` | N/A | No project-controlled crypto suite. |
| `crypto_credential_agility` | ✅ | OIDC trusted publishing — no stored long-lived credentials to rotate. |
| `crypto_used_network` | ✅ | All network use is HTTPS/TLS. |
| `crypto_tls12` | ✅ | Registries/GitHub enforce TLS ≥1.2. |
| `crypto_certificate_verification` | ✅ | TLS verification never disabled; `pip --require-hashes`. |
| `crypto_verification_private` | N/A | No private-key operations in the software. |
| `signed_releases` | ✅ | npm `--provenance` + PyPI trusted-publishing attestations (Sigstore), publicly verifiable. |
| `version_tags_signed` | ⚠️ | Tags not GPG/Sigstore-signed. SUGGESTED; optional at Silver. |
| `input_validation` | ✅ | `auditMeta`/`audit_meta` + `validateEnvelope`; checker totality (ADR 0009). |
| `hardening` | N/A | Library, secure-by-default; static docs site. |
| `assurance_case` | ✅ | `docs/threat-model.md` is the assurance case (property defended, actors, threats, non-guarantees) + SPEC + SECURITY. |

---

## Analysis

| Criterion | Status | Evidence |
| --- | --- | --- |
| `static_analysis_common_vulnerabilities` | ✅ | CodeQL (JS + Python) on push/PR/weekly (`.github/workflows/codeql.yml`). |
| `dynamic_analysis_unsafe` | N/A | JS/Python are memory-safe; Valgrind/ASAN don't apply. |

---

## Remaining optional items (allowed unmet at Silver)

- **`dco` (SHOULD)** — to satisfy explicitly, enable the DCO GitHub App /
  require `Signed-off-by`. Otherwise keep the Apache-§5 statement and answer
  "Met" citing it, or "Unmet" with that justification.
- **`bus_factor` (SHOULD)** — raise to ≥2 by adding a second maintainer; until
  then answer honestly (documented in `GOVERNANCE.md`).
- **`version_tags_signed` (SUGGESTED)** — sign `v*` tags (GPG or Sigstore) in
  the release process.

---

## Form-ready answers

Paste these into <https://www.bestpractices.dev/projects/13453> (Silver tab).
"Met" = check the box; "N/A" = mark N/A and paste the justification; "Unmet" =
leave unchecked (allowed for SHOULD/SUGGESTED).

### Basics
- **achieve_passing** — Met. Passing badge earned.
- **contribution_requirements** — Met. `CONTRIBUTING.md` states requirements for acceptable contributions (single focused change; a test that fails without it; CI + lint green; CHANGELOG update) and the coding style/lint rules.
- **dco** — Unmet (optional). No DCO; contributions are Apache-2.0 inbound = outbound per `CONTRIBUTING.md` § License of contributions. (Or enable the DCO app to mark Met.)
- **governance** — Met. `GOVERNANCE.md` documents the benevolent-maintainer model and how everyday, design, and architectural decisions are made (issues → PRs → ADRs).
- **code_of_conduct** — Met. Contributor Covenant in `CODE_OF_CONDUCT.md`.
- **roles_responsibilities** — Met. `GOVERNANCE.md` § Roles and responsibilities; ownership in `.github/CODEOWNERS`; path to becoming a maintainer documented.
- **access_continuity** — Met. `GOVERNANCE.md` § Access and continuity: source of truth in Git, OIDC trusted publishing (no stored secrets), and a transfer/succession plan.
- **bus_factor** — Unmet (optional). Currently 1; stated honestly in `GOVERNANCE.md`, with the no-stored-secrets release design so low bus factor ≠ unrecoverable infra. Raising to 2 is a goal.

### Documentation
- **documentation_roadmap** — Met. `ROADMAP.md`.
- **documentation_architecture** — Met. `docs/adr/`, `docs/threat-model.md`, `primitives/SPEC.md`.
- **documentation_security** — Met. `SECURITY.md` + `docs/threat-model.md`.
- **documentation_quick_start** — Met. README Install + `mark`/`derive` example.
- **documentation_current** — Met. `CHANGELOG.md` maintained per release.
- **documentation_achievements** — Met. README badges + Status section.
- **accessibility_best_practices** — N/A. Developer library; only a small static docs site, no interactive UI.
- **internationalization** — N/A. No user-facing localizable strings; library API and messages are developer-facing English.
- **sites_password_security** — N/A. Project sites are static (GitHub Pages / registries); no passwords stored.

### Change control / reporting
- **maintenance_or_update** — Met. `SECURITY.md` § Supported versions states the support policy (fixes on latest published minor; no pre-1.0 backport branch).
- **report_tracker** — Met. GitHub Issues + issue templates.
- **vulnerability_report_credit** — Met. `SECURITY.md` § Disclosure credits reporters in advisory + changelog.
- **vulnerability_response_process** — Met. `SECURITY.md` documents private reporting, acknowledgement window, embargo, fix, and credit.

### Quality
- **coding_standards** — Met. `CONTRIBUTING.md` § Coding style (ES-module JS conventions; PEP 8).
- **coding_standards_enforced** — Met. ESLint (recommended) + Ruff run as a CI gate (`.github/workflows/ci.yml`); configs `eslint.config.mjs` per JS package and `ruff.toml`.
- **build_standard_variables** — N/A. Interpreted languages; no C-style build variables.
- **build_preserve_debug** — N/A. No compiled artifacts.
- **build_non_recursive** — N/A. No recursive make/build.
- **build_repeatable** — Met. npm/PyPI builds are deterministic; test deps hash-pinned (`--require-hashes`); release toolchain pinned.
- **installation_common** — Met. Standard `npm install` / `pip install`, plus the Claude Code plugin marketplace.
- **installation_standard_variables** — N/A. `DESTDIR`/staging not applicable to npm/pip.
- **installation_development_quick** — Met. `CONTRIBUTING.md` § Running the tests: one-line setup per package.
- **external_dependencies** — Met. Zero runtime deps; dev/test deps in `package.json` / `pyproject.toml` / hash-pinned `requirements-test.txt`.
- **dependency_monitoring** — Met. Dependabot (github-actions, npm ×2, pip) + OpenSSF Scorecard + Socket.
- **updateable_reused_components** — Met. Zero runtime deps; dev deps updateable via Dependabot.
- **interfaces_current** — Met. Tracks current Node/Python; envelope schema versioned via `PROVENANCE_VERSION`.
- **automated_integration_testing** — Met. CI runs the cross-language conformance report and the `examples` import-linter boundary integration test.
- **regression_tests_added50** — Met. `CONTRIBUTING.md` requires a test that fails without the change; CI enforces it.
- **test_statement_coverage80** — Met. `npm test` (vitest) and `pytest` gate statement coverage ≥80% (fail-under); current actuals 96–99%.
- **test_policy_mandated** — Met. Testing required for new functionality (`CONTRIBUTING.md`).
- **tests_documented_added** — Met. Requirement documented in `CONTRIBUTING.md`.
- **warnings_strict** — Met. ESLint + Ruff run as errors (no warning-only mode) in CI.

### Security
- **implement_secure_design** — Met. Conservative combination law with no taint-clearing escape hatch; `docs/threat-model.md` + SPEC §6.
- **crypto_weaknesses** — N/A. The software implements no cryptographic protocol of its own; it relies on registry TLS and Sigstore-based release attestations.
- **crypto_algorithm_agility** — N/A. No project-controlled crypto suite.
- **crypto_credential_agility** — Met. Release auth is OIDC trusted publishing; there are no long-lived credentials embedded that would need rotation.
- **crypto_used_network** — Met. All network communication (registries, Pages, GitHub) is over TLS.
- **crypto_tls12** — Met. Registries and GitHub enforce TLS ≥1.2.
- **crypto_certificate_verification** — Met. TLS certificate verification is never disabled; `pip --require-hashes` pins artifacts.
- **crypto_verification_private** — N/A. No private-key signing/decryption performed by the software.
- **signed_releases** — Met. npm publishes with `--provenance`; PyPI uses trusted-publishing attestations (Sigstore) — both publicly verifiable.
- **version_tags_signed** — Unmet (optional). Git tags are not cryptographically signed yet.
- **input_validation** — Met. `auditMeta`/`audit_meta` and `validateEnvelope` validate envelope inputs; checker is total over inputs (ADR 0009).
- **hardening** — N/A / Met. Library with secure defaults; no server to harden. Static docs site.
- **assurance_case** — Met. `docs/threat-model.md` is the assurance case: the property defended (taint cannot be laundered through the public API), the actors, the threats, and honest non-guarantees; backed by `primitives/SPEC.md` and `SECURITY.md`.

### Analysis
- **static_analysis_common_vulnerabilities** — Met. CodeQL for JavaScript and Python on push, PR, and a weekly schedule.
- **dynamic_analysis_unsafe** — N/A. JavaScript and Python are memory-safe; memory-error tools (Valgrind/ASan) do not apply.

---

*Generated as a planning aid; the authoritative record is the badge
questionnaire itself.*
