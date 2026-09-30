# Validation results

Independent checks that plumb-line's enforcement catches what it claims to,
run against the worked fixtures in `examples/`. Each run is recorded in its
own file: release-harness runs (the method is in
[`release-harness.md`](release-harness.md)) are named for their release, and
runs between releases for their date. The records were moved here, verbatim,
from this file's earlier single-page form (#570); only their headings and
relative links changed.

- Release validation: [`records/validation/`](records/validation/), below.
- The dogfood self-audits: [`dogfood.md`](dogfood.md).
- Eval suite runs (`claude plugin eval`): [`records/evals/`](records/evals/),
  below.

## Validation runs

Newest first. The two result columns quote each record's own `### Part 1`
and `### Format scoring` headings; records before v0.7.1 give their result
in prose, and a dash means the record has no format-scoring heading (the
format checker exists since v0.10.0, #139).

| Run | Date | Blind validation (Part 1) | Format scoring |
| --- | --- | --- | --- |
| [v0.11.5 release-harness record — 2026-09-28 (pre-tag)](records/validation/v0.11.5.md) | 2026-09-28 | 5/6 PASS first run; py-clean FAIL, fixed and re-validated 2/2 | 8/8 conform |
| [Impossible-task spike — 2026-09-26 (#462)](records/validation/2026-09-26-impossible-task-spike-462.md) | 2026-09-26 | in the record’s prose | — |
| [v0.11.4 release-harness record — 2026-09-26 (pre-tag)](records/validation/v0.11.4.md) | 2026-09-26 | 6/6 findings PASS | 6/6 conform |
| [Fixture change between releases — 2026-09-26 (#447)](records/validation/2026-09-26-fixture-change-447.md) | 2026-09-26 | in the record’s prose | — |
| [v0.11.3 release-harness record — 2026-09-25 (pre-tag)](records/validation/v0.11.3.md) | 2026-09-25 | 6/6 findings PASS | 6/6 conform |
| [v0.11.2 release-harness record — 2026-09-25 (pre-tag)](records/validation/v0.11.2.md) | 2026-09-25 | 6/6 findings PASS | 6/6 conform, after a checker bug |
| [v0.11.1 release-harness record — 2026-09-20 (pre-tag)](records/validation/v0.11.1.md) | 2026-09-20 | 6/6 findings PASS | 4/6 conform |
| [v0.11.0 release-harness record — 2026-09-15 (pre-tag)](records/validation/v0.11.0.md) | 2026-09-15 | 6/6 findings PASS | 6/6 conform, after a skill fix |
| [v0.10.0 release-harness record — 2026-08-19 (pre-tag)](records/validation/v0.10.0.md) | 2026-08-19 | 6/6 findings PASS | 5/6; the #297 fix observed working |
| [2026-08-18 — off-cycle blind validation (v0.9.0 skill as shipped)](records/validation/2026-08-18-off-cycle-blind-validation.md) | 2026-08-18 | 6/6 PASS | 5/6, one format FAIL |
| [v0.9.0 release-harness record — 2026-08-15](records/validation/v0.9.0.md) | 2026-08-15 | PASS (6/6) | — |
| [v0.8.1 release-harness record — 2026-08-14](records/validation/v0.8.1.md) | 2026-08-14 | PASS (6/6) | — |
| [v0.8.0 release-harness record — 2026-08-11](records/validation/v0.8.0.md) | 2026-08-11 | PASS (6/6) | — |
| [v0.7.3 release-harness record — 2026-07-19](records/validation/v0.7.3.md) | 2026-07-19 | PASS (6/6) | — |
| [v0.7.2 release-harness record — 2026-07-15](records/validation/v0.7.2.md) | 2026-07-15 | PASS (6/6) | — |
| [v0.7.1 release-harness record — 2026-07-12](records/validation/v0.7.1.md) | 2026-07-12 | PASS (6/6) | — |
| [0.7.0 release-harness record](records/validation/v0.7.0.md) | 2026-07-11 | in the record’s prose | — |
| [0.6.0 release-harness record](records/validation/v0.6.0.md) | 2026-07-05 | in the record’s prose | — |
| [0.5.1 release-harness record](records/validation/v0.5.1.md) | 2026-07-03 | in the record’s prose | — |
| [0.5.0 release-harness record](records/validation/v0.5.0.md) | 2026-07-03 | in the record’s prose | — |
| [0.4.1 release-harness record](records/validation/v0.4.1.md) | 2026-07-02 | in the record’s prose | — |
| [0.4.0 release-harness record](records/validation/v0.4.0.md) | 2026-07-01 | in the record’s prose | — |
| [0.3.1 release-harness record](records/validation/v0.3.1.md) | 2026-07-01 | in the record’s prose | — |
| [0.3.0 release-harness record](records/validation/v0.3.0.md) | 2026-06-30 | in the record’s prose | — |
| [v0.2.0 validation](records/validation/v0.2.0.md) | 2026-06-30 | in the record’s prose | — |
| [v0.1.0 validation — 2026-06-28](records/validation/v0.1.0.md) | 2026-06-28 | in the record’s prose | — |

## Eval suite runs

None recorded yet. The first green run of the `claude plugin eval` suite
(#530) is recorded in [`records/evals/`](records/evals/) and listed here.
