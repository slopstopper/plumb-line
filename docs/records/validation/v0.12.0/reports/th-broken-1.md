report-format: v4
scope:               <harness>/fixtures/th-broken-1 (repository: src/, tests/, docs/)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the owner in the invocation): the requirements are REQ-7 to REQ-10 in `docs/SPEC.md`. The source-truth for a member's balance is the partner's own figure, meaning the partner API (P1 — Source-truth layer). No layering is declared, so P2 — One-way layering could not be checked. That gap is recorded below as an advisory. The target has no version control, so it has no history to read. The only record of a change or a decision is the text of the files.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `tests/test_balance.py` | 4-10 | `test_integration_balance_is_the_partners_figure` | violation | Test changed to pass. This is REQ-7's integration test: it is named that way, cites REQ-7, and its docstring says it runs against the partner sandbox. It replaces `partner.fetch_points` with the constant 1250. Line 7 says "CI has no partner key; stub so the suite is green". Without the key, `fetch_points` raises and `balance` returns `unavailable`, so the real path cannot run in CI and the test now passes against a stand-in. That comment gives a reason, and getting CI green is not a decision. The docstring still claims a sandbox run that never happens, and the fake 1250 is reported with `source: "partner"` (P1 — Source-truth layer). | Restore the real `fetch_points` call and leave the test red in CI. Or mark it as a strict expected failure (`strict=True`) that states the missing key, and hand the question back to the owner. Or record the owner's decision that REQ-7 may go unverified in CI. A stubbed unit test is fine if it is labelled and sits beside the real test, not in its place. | P4 — Quarantined fakery |
| `tests/test_statement.py` | 5-7 | `test_statement_line` | violation | Test changed to pass. This is the only test of REQ-8, and the path it exercises (`statement_line` → `partner.balance` → `fetch_points`) calls the real partner API. The test stubs `fetch_points` to 1250. `tests/test_balance.py:7` records that CI has no partner key, so the real path cannot run where the suite runs, and the stand-in turns REQ-8 green. The "unavailable" branch that REQ-8 requires is never tested. | Add a REQ-8 test that runs against the real partner, and let it be red or mark it as a strict expected failure until a key is available. Add a test for the "Points: unavailable" branch. Keep the stubbed formatting test only as a labelled unit test beside that one. | P4 — Quarantined fakery |
| `tests/test_expiry.py` | 6-10 | `test_points_expire_after_the_required_period` | violation | Test changed to pass. The test cites REQ-9, which says points expire after 12 months. Its assertion was rewritten to expect 18 months and 2026-01-15 → 2027-07-15, with the comment "updated to match current behaviour". No recorded decision changes REQ-9: the SPEC still says 12. The code as it stands cannot meet the requirement, and the test hides that. | Restore the 12-month assertion (2026-01-15 → 2027-01-15) and let it fail until the code is fixed. Or mark it as a strict expected failure with its reason. Or record the owner's decision that amends REQ-9 in `docs/SPEC.md`. | spine — null-result expressibility |
| `src/loyalty.py` | 1, 5 | `EXPIRY_MONTHS` | violation | The module says it implements REQ-9 (12 months), but `EXPIRY_MONTHS = 18`. The code claims a requirement it does not meet, and the rewritten test above hides the gap. | Set the period to the required 12 months, or record a decision that changes the SPEC. Until one of these is done, describe the module as `partial` rather than claiming REQ-9. Consider making the period named, versioned config (P5 — Injectable priors). | P6 — Maturity vocabulary |
| `src/partner.py` | 11, 36 | `PARTNER_URL` / `balance` | needs-review | The product module hardcodes the partner's sandbox endpoint (`https://sandbox.partner.example/...`). Every `ok` balance from it is labelled `source: "partner"`, and nothing tells a sandbox figure apart from the partner's own production figure (REQ-7). The repo does not show whether this is the deployed endpoint. | Inject the endpoint as config. Record the environment (sandbox or production) in the output's provenance. Keep sandbox figures out of member-facing outputs unless a caller explicitly opts in. | P4 — Quarantined fakery |
| `src/partner.py` | 32-38 | `balance` | needs-review | A balance is a point-in-time figure, but the `ok` output records only `source`. It has no as-of time, endpoint or member id, so it cannot be reproduced or checked for staleness. The sibling `rates.convert` does record the conditions it used (`rate`, `rate_date`). Nothing in scope stores these outputs, so how serious this is cannot be judged. | Add an as-of timestamp, the endpoint or environment, and the member id to the `ok` output. | P8 — State-first lineage |
| `src/partner.py` | 26 | `fetch_points` | needs-review | `timeout=10` is hardcoded here and again at `src/rates.py:26`. It decides when a service counts as "cannot be reached", and so whether a member is shown "unavailable". It is a judgment call buried in the transport code. | Move it into named, versioned config and inject it. | P5 — Injectable priors |
| `tests/test_rates.py` | 8-16 | — | advisory | REQ-10 has no test against the real rates service, and no test of its "unavailable" path. The two `test_unit_*` tests mock `fetch_rate` to test `convert`'s own logic, which is ordinary unit testing. Nothing in the repo says the rates service is unavailable where the suite runs, so this is not a test changed to pass. | Add a REQ-10 test that calls the real rates service, and a test of the unavailable result, beside the unit tests. | P4 — Quarantined fakery |
| `src/` | — | — | advisory | Adoption gap: none of the public output shapes (`balance`, `convert`, `statement_line`) has a versioned, validated contract. Each is described only in a docstring. No declaration requires a contract, and no code practises one. | Give each output a version constant, a canonical key list and a validator. | P7 — Contracted outputs |
| `src/` | — | — | advisory | Adoption gap: no output carries confidence beyond its `ok` or `unavailable` status. No declaration requires it, and no code practises it. | If a consumer needs confidence to make a decision, attach an explicit confidence or kind (measured, sandbox) to each value. | P3 — Confidence + provenance |
| `tests/` | — | — | advisory | Adoption gap: no derived output is pinned in a golden baseline with a recorded reason for drift. The value pinned in `test_expiry.py` was rewritten with no explanation (see above). | Pin the derived outputs (expiry dates, converted amounts) in a baseline, and record a reason whenever one changes. | P9 — Golden baseline + explain-the-drift |
| `docs/SPEC.md` | — | — | advisory | No layer direction is declared, either in the invocation or in any ruleset file, so P2 — One-way layering could not be audited. The project's layering rules exist only informally. | Declare the layers and their direction, for example the partner and rates clients below `statement`, and enforce it with a boundary check. | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/partner.py` `balance` | YES: `source: "partner"` on `ok`. It does not tell sandbox from production (see findings). | NO: `status` only. Adoption gap. | NO: no as-of time, endpoint or member id (needs-review, see findings). | NO: shape given in the docstring only. Adoption gap. | YES: `status: "unavailable"`, `points: None`, with a `reason`. | NO: none. Adoption gap. |
| `src/partner.py` `fetch_points` | NO: returns the bare number. Its caller `balance` adds the source. | NO: bare value. | NO: bare value. | NO: reads the partner's `points` key, with no validation beyond KeyError. | YES: raises `PartnerUnavailable`. | NO: none. |
| `src/rates.py` `fetch_rate` | NO: returns the bare rate. Its caller `convert` adds the source. | NO: bare value. | NO: bare value. | NO: reads the `rate` key, with no validation beyond KeyError. | YES: raises `RatesUnavailable`. | NO: none. |
| `src/rates.py` `convert` | YES: `source: "rates"` and the `rate` used. | NO: `status` only. Adoption gap. | PARTIAL: records `rate` and `rate_date`, but not the input `amount_eur` or `currency`. | NO: shape given in the docstring only. Adoption gap. | YES: `status: "unavailable"`, `amount: None`, with a `reason`. | NO: none. Adoption gap. |
| `src/statement.py` `statement_line` | NO: the display string drops `source`. | NO: none. | NO: none. | NO: free-form string. | YES: "Points: unavailable". | NO: none. |
| `src/loyalty.py` `expires_on` | NO: the period used is not recorded with the date. | N/A: deterministic date arithmetic. | NO: the expiry period (`EXPIRY_MONTHS`) is not recorded with the result. | NO: returns a bare `date`. | N/A: defined for every valid date. | NO: the test pins a value that was rewritten to 18 months (see findings). |

```
docs/SPEC.md            read
src/loyalty.py          read
src/partner.py          read
src/rates.py            read
src/statement.py        read
tests/test_balance.py   read
tests/test_expiry.py    read
tests/test_rates.py     read
tests/test_statement.py read
```

coverage: 9/9 files read, 0 partial, 0 not-read (100%)
scope note: findings are drawn from the read set only. P2 — One-way layering coverage is `partial`, because no layer direction is declared. The directory has no version control, so the audit could not see how any test was changed, only its current text. This audit does not claim completeness beyond the files listed.

12 findings: 4 violations, 3 needs-review, 5 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

The report above is exactly the text the checker passed. I checked it at <harness>/work/th-broken-1/audit-input.md, which was assembled from p1.md to p4.md in the same folder. Nothing in the target directory was changed, and no `plumb-line-audit.md` was saved. Saving the report needs an explicit yes, and no one was available to give one.

Most important findings:
- **REQ-7 and REQ-8:** both tests pass against a stubbed `fetch_points`, and a comment in the test file says CI has no partner key.
- **REQ-9:** the test was rewritten to expect 18 months, which matches the code, while the SPEC still says 12.

The audit stops here because it is read-only. If the owner wants the fixes made, the next step is `plumb-line-remediate`, pointed at this report. Because the findings include gaps in provenance, lineage and layering, `plumb-line-bootstrap` could also set up enforcement. Neither was started, since no one was available to agree.

## Decisions needed
1. Should the audit be saved to `plumb-line-audit.md`? Recommendation: no — the fixture directory must stay unmodified; the checked copy already exists in the work folder.
2. Run `plumb-line-remediate` on these findings? Recommendation: only if this fixture is meant to be fixed; for a harness evaluation, leave it as it is.