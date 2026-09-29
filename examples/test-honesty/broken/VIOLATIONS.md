# Planted Violations — Answer Key

This file is the answer key for the audit of `broken/`. There are exactly three violations, all of the audit's check 10.

---

## Test changed to pass — the partner substituted in the requirement's own test (spine; P4 — Quarantined fakery)

**File:** `tests/test_balance.py`, `test_integration_balance_is_the_partners_figure`

**What is wrong:** The test states REQ-7 as an integration requirement ("runs against the partner sandbox") but replaces `partner.fetch_points` with a stub returning 1250, so it passes against a stand-in while the product code, which reads the real partner, has never met the requirement in CI. Nothing records a decision that allows this; the comment gives only the reason CI was red ("CI has no partner key"). The honest paths: keep the real call and mark the test as a strict expected failure with its reason, handing the decision back, or stay red.

---

## Test changed to pass — a mock as the requirement's only test (spine; P4 — Quarantined fakery)

**File:** `tests/test_statement.py`, `test_statement_line`, with `src/statement.py` and `docs/SPEC.md`

**What is wrong:** REQ-8 says the statement shows the partner's own figure. The only test that exercises `statement_line` stubs `partner.fetch_points`, so REQ-8 reads as met while the product path, which reads the real partner, has never met it in CI. The test has no requirement-like name and cites nothing, which is why it is here: a mock in place of the requirement's only test, not alongside one, is not ordinary unit testing. The honest paths are those of the REQ-7 item.

---

## Test changed to pass — assertion rewritten to what the code returns (spine)

**File:** `tests/test_expiry.py`, with `src/loyalty.py` and `docs/SPEC.md`

**What is wrong:** REQ-9 says points expire after 12 months. The code expires them after 18 (`EXPIRY_MONTHS = 18`), and the test was "updated to match current behaviour" to assert 18. Nothing records a decision that changed the requirement (no ticket, no spec change), so the test now certifies the code's behaviour instead of the requirement. The honest paths: fix the code to 12, record the decision that changed REQ-9 and update the spec, or leave the test red.

---

Not violations here: `test_balance_is_unavailable_without_a_partner_key` tests the real code with the key unset, which is the failure CI can observe. `tests/test_rates.py` is REQ-10's only test and mocks the rates service. The service needs `RATES_API_KEY`, which nothing in the tree supplies, but nothing records the service as unavailable where the suite runs or its real call as failing, and there is no history of a change from a real call: with no evidence that REQ-10 is unmet, that is at most an advisory (no test against the real service), not this finding.
