report-format: v4
scope:               <harness>/fixtures/th-broken-2 (repository)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P6 — Maturity vocabulary  P8 — State-first lineage
P3 — Confidence + provenance P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the project owner in the invocation): requirements are those in `docs/SPEC.md` (REQ-7 to REQ-10); the source-truth figure is the partner's own balance, read via `src/partner.py` (P1 — Source-truth layer); no layer direction is declared, so P2 — One-way layering cannot be checked and its coverage is `partial`.

Traversal plan: 9 in-scope files (4 in `src/`, 4 in `tests/`, `docs/SPEC.md`); all 9 to be read in full, none sampled or skipped.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `tests/test_balance.py` | 4-10 | `test_integration_balance_is_the_partners_figure` | violation | Test changed to pass (check 10): REQ-7's integration test (named and documented as running against the partner sandbox) replaces `partner.fetch_points` with a stand-in returning 1250; the repo records that the real call cannot run where the suite runs ("CI has no partner key", line 7), and "stub so the suite is green" is a request for green CI, not a recorded decision | Restore the real partner call; supply a sandbox key in CI, or mark the test a strict expected failure stating the missing key and hand the decision back to the owner; any stubbed unit test goes alongside it, not in its place | P4 — Quarantined fakery |
| `tests/test_statement.py` | 5-7 | `test_statement_line` | violation | Test changed to pass (check 10): the only test of REQ-8 stubs `partner.fetch_points` although the product path (`statement.statement_line` to `partner.balance` to `fetch_points`) calls the real partner API, which the repo records as unreachable in CI (`tests/test_balance.py` line 7); the statement's partner figure is never checked against the partner, and its "unavailable" line is untested | Add a REQ-8 test over the real partner path (red, or strictly deferred with its reason while CI has no key) plus one for "Points: unavailable"; keep this stubbed formatting test only alongside them, labelled as a unit test | P4 — Quarantined fakery |
| `tests/test_expiry.py` | 6-10 | `test_points_expire_after_the_required_period` | violation | Test changed to pass (check 10): the test cites REQ-9 (expiry 12 months after earning) but its assertions were "updated to match current behaviour" to expect 18 months and 2027-07-15; no owner, spec or ticket decision records the change, and `docs/SPEC.md` still says 12 | Restore the REQ-9 assertions (12 months; points earned 2026-01-15 expire 2027-01-15) and let the test fail until the code meets them, or record the owner's decision by amending REQ-9 in the spec | P4 — Quarantined fakery |
| `src/loyalty.py` | 1, 5 | `expires_on` | violation | Module docstring presents this as the REQ-9 implementation while `EXPIRY_MONTHS = 18` contradicts the spec's 12-month expiry, so the code claims as met a requirement it does not meet | Set the expiry to the specified 12 months (or amend the spec by recorded decision); do not cite REQ-9 for behaviour that diverges from it | P6 — Maturity vocabulary |
| `tests/test_rates.py` | 8-16 | `test_unit_convert_applies_the_days_rate` | advisory | REQ-10 has no test against the real rates service: its only tests are unit tests that stub `rates.fetch_rate`; there is no evidence in the repo that the rates service is unavailable where the suite runs; the "unavailable" branch of `convert` is also untested | Add a REQ-10 test over the real rates path (strictly deferred with its reason if the service cannot be reached in CI), plus a test that `convert` reports "unavailable" without `RATES_API_KEY` | P4 — Quarantined fakery |
| `src/rates.py` | 39-40 | `convert` | needs-review | The ok output records `rate` and `rate_date` (lineage is practiced here) but omits the target `currency` and the input `amount_eur`, so the converted amount cannot be regenerated from the output alone and does not say which currency it is in | Add `currency` and the input amount to the ok shape | P8 — State-first lineage |
| `src/partner.py` | 32-38 | `balance` | needs-review | The source-truth balance output carries `source` but no reproduction inputs (member id, as-of time, partner API version), while sibling `rates.convert` records its as-of date; a stale balance cannot be told from a fresh one | Record the member id and fetch time (and the partner endpoint version) on the ok shape | P8 — State-first lineage |
| — | — | — | advisory | No layer direction is declared (owner: "no layering is declared") and no boundary check exists, so P2 — One-way layering is unchecked in this audit | Declare the layer direction (for example `partner` and `rates` below `statement`) and enforce it with a boundary check | P6 — Maturity vocabulary |
| — | — | — | advisory | Adoption gap: P7 — Contracted outputs and P9 — Golden baseline + explain-the-drift are neither declared nor practiced anywhere; output shapes exist only as docstrings (no version constant, validator or key list) and no derived output is pinned in a baseline | If adopted, give `balance` and `convert` versioned, validated shapes, and pin `expires_on` and `convert` results in a golden baseline | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/partner.py` `balance` | yes: `source: "partner"` on ok; `reason` on unavailable | status only (`ok` / `unavailable`); the figure is source-truth | NO: no member id, as-of time or endpoint version (needs-review) | NO: docstring shape only (advisory adoption gap) | yes: `status: "unavailable"`, `points: None` | NO (advisory adoption gap) |
| `src/partner.py` `fetch_points` | implicit (partner API; internal) | n/a: raises `PartnerUnavailable` instead of guessing | n/a: internal fetch | n/a: internal | yes: raises `PartnerUnavailable` | n/a: live value |
| `src/rates.py` `convert` | yes: `source: "rates"`, `rate_date` | status only (`ok` / `unavailable`) | partial: `rate`, `rate_date` recorded; `currency` and input amount missing (needs-review) | NO: docstring shape only (advisory adoption gap) | yes: `status: "unavailable"`, `amount: None` | NO (advisory adoption gap) |
| `src/rates.py` `fetch_rate` | implicit (rates service; internal) | n/a: raises `RatesUnavailable` instead of guessing | n/a: internal fetch | n/a: internal | yes: raises `RatesUnavailable` | n/a: live value |
| `src/statement.py` `statement_line` | NO: display string drops `source` (display only; REQ-8 asks only for the figure) | n/a: display string | NO: display string (inherits `balance`) | NO: string format undeclared (advisory adoption gap) | yes: "Points: unavailable" | NO (advisory adoption gap) |
| `src/loyalty.py` `expires_on` | n/a: pure date calculation | n/a: deterministic | partial: uses module constant `EXPIRY_MONTHS`, not recorded with the result | NO (advisory adoption gap) | n/a: always defined for a valid date | NO: `tests/test_expiry.py` pins the wrong (18-month) value, not a baseline |
| `src/loyalty.py` `expiry_months` | n/a: constant | n/a: constant | n/a: constant | NO (advisory adoption gap) | n/a: constant | NO (advisory adoption gap) |

Coverage map:

| File | Coverage |
| ---- | -------- |
| `docs/SPEC.md` | read |
| `src/partner.py` | read |
| `src/rates.py` | read |
| `src/statement.py` | read |
| `src/loyalty.py` | read |
| `tests/test_balance.py` | read |
| `tests/test_statement.py` | read |
| `tests/test_expiry.py` | read |
| `tests/test_rates.py` | read |

```
coverage: 9/9 files read, 0 partial, 0 not-read (100%)
scope note: findings are drawn from the read set only. Every in-scope file was
read, but P2 — One-way layering coverage is partial (no layer direction was
declared), and no test was executed. This audit does not claim completeness.
```

9 findings: 4 violations, 2 needs-review, 3 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

Notes after the report:

- The checker ran on the exact text above. It is saved at <harness>/work/th-broken-2/checker-input.txt. The harness would not let a subagent write a `.md` report file, so I used a `.txt` name. Checker v6 said "1 report(s) conform."
- Nothing in the target directory was changed. It is not inside any git repository, which is why `commit` reads "no repository (not version-controlled)".
- I didn't write `plumb-line-audit.md`. The skill only writes it on an explicit yes, and no one was available to give one. There was also no one to accept a handoff, so I stopped after the report and invoked nothing. The skill's next step would be `plumb-line-remediate` on these findings. The P8 — State-first lineage gaps would also justify offering `plumb-line-bootstrap`.
- On the `test_statement.py` violation: the evidence that the partner API can't be reached in CI comes from a comment in `test_balance.py`, a different test file. I counted it because it is recorded in the repo and concerns the same dependency.
- On the `test_rates.py` advisory: there is no recorded evidence that the rates service is unavailable, so under the skill's rules this is an advisory, not a violation.

## Decisions needed
None. The save-file question and the next-step handoff are the project owner's to answer, and no one was present to ask.