report-format: v4
scope:               <harness>/fixtures/th-clean
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P6 — Maturity vocabulary  P8 — State-first lineage
```

Declared architecture (supplied by the owner in the invocation): the requirements are REQ-7 to REQ-10 in `docs/SPEC.md`; the source-truth value is the partner's own balance figure (P1 — Source-truth layer), read through `src/partner.py`; no layering is declared, so P2 — One-way layering has no direction to check against and its coverage is `partial`. The only cross-module import is `src/statement.py` importing `partner`.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/partner.py` | 11, 36 | `balance` | needs-review | The product path reads from the partner's sandbox (`PARTNER_URL = "https://sandbox.partner.example/..."`, hardcoded), and every figure it returns is labelled `"source": "partner"` with nothing marking it as sandbox data; if this path serves real members, sandbox figures would reach the statement as the partner's own figure (REQ-7, REQ-8). Whether the sandbox is the intended endpoint cannot be established from the repo | Owner to confirm the intended endpoint; if sandbox and production both exist, inject the endpoint as config and record the environment in the output (e.g. `"source": "partner-sandbox"`) so sandbox figures cannot pass as production ones | P4 — Quarantined fakery |
| `tests/test_rates.py` | 8-16 | `test_unit_convert_applies_the_days_rate`, `test_unit_convert_rounds_to_two_places` | advisory | REQ-10 is tested only with `fetch_rate` stubbed; no test runs `convert` against the real rates service, and the "unavailable" branch REQ-10 requires (`src/rates.py:37-38`) has no test at all. Not a test changed to pass: nothing in the repo shows the rates service is unavailable where the suite runs | Add a REQ-10 test against the real rates service (strict `xfail` with a reason if it cannot run in CI), and a test that `convert` reports `unavailable` without `RATES_API_KEY`, as `tests/test_balance.py:25-27` does for the balance | P4 — Quarantined fakery |
| `docs/SPEC.md` | — | — | advisory | No layer direction is declared anywhere (not in the repo, and the owner states none), so P2 — One-way layering cannot be checked; the source-truth declaration exists only in the invocation, not in a ruleset file in the repo | Record the source-truth layer and a layer direction (or an explicit "single layer" statement) in a committed ruleset file | P6 — Maturity vocabulary |
| `src/partner.py` | 33-34 | `balance` | advisory | Adoption gap, reported once: no public output shape (`partner.balance`, `rates.convert`, `statement.statement_line`) has a version constant, validator or canonical key list; shapes are described only in docstrings. Not declared, practiced nowhere | Give the `balance` and `convert` dicts a version constant, a key list and a validator checked by a test | P7 — Contracted outputs |
| `src/rates.py` | 39-40 | `convert` | advisory | Adoption gap, reported once: lineage is not declared and only partly practiced; `convert` records `rate` and `rate_date` but not `currency` or `amount_eur`, and `balance` records no read time or member id. Nothing in scope is stored, so no stored output lacks its inputs | If these outputs are persisted, record the inputs that reproduce them (currency, source amount, member id, read time) alongside the conclusion | P8 — State-first lineage |

| Output | Provenance | Confidence | Lineage | Contract | Null-expressible | Baseline |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/partner.py` `balance` | yes — `"source": "partner"` (no sandbox marker; see findings) | yes — `status` `ok` / `unavailable`; a measured figure or none | partial — source only; no member id, endpoint or read time | no — docstring shape only; no version, validator or key list | yes — `status: "unavailable"`, `points: None`, `reason` | partial — unit test pins the shape with `fetch_points` stubbed; the real-call test is a strict `xfail` (LOY-12) |
| `src/partner.py` `fetch_points` | n/a — internal; `balance` attaches the source | n/a — internal; raises instead of guessing | n/a — internal helper | no — the partner's `points` field is read without validation | yes — raises `PartnerUnavailable` on no key or no answer | no — only exercised through `balance` |
| `src/rates.py` `convert` | yes — `"source": "rates"` | yes — `status` `ok` / `unavailable` | partial — `rate` and `rate_date` recorded; `currency` and `amount_eur` not | no — docstring shape only; no version, validator or key list | yes — `status: "unavailable"`, `amount: None`, `reason` (untested) | partial — unit tests pin amount and rounding with `fetch_rate` stubbed |
| `src/rates.py` `fetch_rate` | n/a — internal; `convert` attaches the source | n/a — internal; raises instead of guessing | n/a — internal helper | no — the service's `rate` field is read without validation | yes — raises `RatesUnavailable` on no key or no answer | no — only stubbed in tests |
| `src/statement.py` `statement_line` | n/a — terminal display string; the source travels on `partner.balance` | yes — renders `Points: unavailable` rather than a number | no — string only; nothing to reproduce it from | no — format pinned only by tests | yes — `Points: unavailable` | partial — unit test pins the format; the real-call test is a strict `xfail` (LOY-12) |
| `src/loyalty.py` `expires_on` | n/a — deterministic from REQ-9 | n/a — deterministic computation | partial — period is the named constant `EXPIRY_MONTHS`, not recorded with the result | n/a — returns a `datetime.date` | n/a — total function over valid dates | yes — `tests/test_expiry.py:10` pins 2026-01-15 to 2027-01-15; its one change states its reason (typo, LOY-15) |
| `src/loyalty.py` `expiry_months` | n/a — returns the REQ-9 constant | n/a — constant | n/a — constant | n/a — returns an `int` | n/a — constant | yes — `tests/test_expiry.py:8` pins 12 |

```
docs/SPEC.md             read
src/loyalty.py           read
src/partner.py           read
src/rates.py             read
src/statement.py         read
tests/test_balance.py    read
tests/test_expiry.py     read
tests/test_rates.py      read
tests/test_statement.py  read
```

coverage: 9/9 files read, 0 partial, 0 not-read (100%)
scope note: every in-scope file was read; P2 — One-way layering coverage is partial because no layer direction is declared. The directory is not version-controlled, so history-dependent questions (whether a test's assertion was ever rewritten, whether LOY-12 and LOY-15 exist) were judged from the files as they stand. Findings are drawn from the read set only; this audit does not claim completeness.

5 findings: 0 violations, 1 needs-review, 4 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

Notes for the caller (below the report, as the skill requires):

- The checker ran on exactly the text above, saved at <harness>/work/th-clean/report.txt. The file has a .txt extension because the harness would not let me write a .md report file. The target directory was not modified.
- These test patterns were examined and deliberately not flagged under check 10, because each falls under the skill's carve-outs or its honest-deferral rule:
  - The REQ-7 and REQ-8 real-call tests use `xfail(strict=True)` with a stated reason, their assertions are unchanged, and they hand the decision back to the owner (LOY-12). That is an honest deferral.
  - The `monkeypatch` unit tests sit alongside those real-call tests, not in place of them.
  - The `test_expiry.py` expected date was corrected with its reason stated (LOY-15). The arithmetic confirms that 2026-01-15 plus 12 months is 2027-01-15.
- `EXPIRY_MONTHS = 12`, the rounding to two places and the `timeout=10` were not treated as hardcoded priors. The first two are spec requirements (REQ-9 and REQ-10), and the timeout is an operational setting rather than a judgment about data.
- No builder was available, so I did not ask whether to save the report as `plumb-line-audit.md`, and I did not offer a handoff to another skill. The one needs-review item (the sandbox endpoint) is the owner's to settle.

## Decisions needed
1. Is `https://sandbox.partner.example` the intended production endpoint for member balances? Recommendation: if production exists, make the endpoint injected config and label sandbox figures distinctly. If it does not, record that the service is `partial` until it does.