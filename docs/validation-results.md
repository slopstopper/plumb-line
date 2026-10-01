# Validation results

Independent checks that plumb-line's enforcement catches what it claims to,
most of them run against the worked fixtures in `examples/`. Each run is
recorded in its own file: release-harness runs (the method is in
[`release-harness.md`](release-harness.md)) are named for their release, and
records between releases for their date.

The records were moved here from this file's earlier single-page form
(#570). Their words are unchanged. What changed: each `##` heading became the
record's title, and the two v0.1.0 records (validation and dogfood), which had
no heading of their own, have written ones; relative links point from the
record's new folder, and
each "see `dogfood.md`, vX section" link to that release's dogfood record;
and four references to "above" or "this file" that now lie in another record
are linked to it.

- Release validation: [`records/validation/`](records/validation/), below.
- The dogfood self-audits: [`dogfood.md`](dogfood.md).
- Eval suite runs (`claude plugin eval`): [`records/evals/`](records/evals/),
  below.

## Validation runs

Newest first. The result columns quote each record's own result headings
(`### Part 1`, or `### Finding accuracy` for the 2026-08-18 run, and
`### Format scoring`). Records before v0.7.1 give their blind-validation
result in prose. The format checker exists since v0.8.0 (#139); the v0.8.0
to v0.9.0 records give its result in prose. A dash means no tool-scored
format check: from v0.5.0 to v0.7.3 the records note format by eye, in prose,
and earlier ones not at all.

| Run | Date | Blind validation (Part 1) | Format scoring |
| --- | --- | --- | --- |
| [v0.12.0 release-harness record — 2026-09-30 (pre-tag)](records/validation/v0.12.0.md) | 2026-09-30 | 9/9 PASS | 17/18 conform; the dogfood report fails, honestly stamped |
| [v0.11.5 release-harness record — 2026-09-28 (pre-tag)](records/validation/v0.11.5.md) | 2026-09-28 | 5/6 PASS first run; py-clean FAIL, fixed and re-validated 2/2 | 8/8 conform |
| [Impossible-task spike — 2026-09-26 (#462)](records/validation/2026-09-26-impossible-task-spike-462.md) | 2026-09-26 | — (a spike, not a blind validation) | — (a spike, not a blind validation) |
| [v0.11.4 release-harness record — 2026-09-26 (pre-tag)](records/validation/v0.11.4.md) | 2026-09-26 | 6/6 findings PASS | 6/6 conform |
| [Fixture change between releases — 2026-09-26 (#447)](records/validation/2026-09-26-fixture-change-447.md) | 2026-09-26 | — (a fixture change, not a run) | — (a fixture change, not a run) |
| [v0.11.3 release-harness record — 2026-09-25 (pre-tag)](records/validation/v0.11.3.md) | 2026-09-25 | 6/6 findings PASS | 6/6 conform |
| [v0.11.2 release-harness record — 2026-09-25 (pre-tag)](records/validation/v0.11.2.md) | 2026-09-25 | 6/6 findings PASS | 6/6 conform, after a checker bug |
| [v0.11.1 release-harness record — 2026-09-20 (pre-tag)](records/validation/v0.11.1.md) | 2026-09-20 | 6/6 findings PASS | 4/6 conform |
| [v0.11.0 release-harness record — 2026-09-15 (pre-tag)](records/validation/v0.11.0.md) | 2026-09-15 | 6/6 findings PASS | 6/6 conform, after a skill fix |
| [v0.10.0 release-harness record — 2026-08-19 (pre-tag)](records/validation/v0.10.0.md) | 2026-08-19 | 6/6 findings PASS | 5/6; the #297 fix observed working |
| [2026-08-18 — off-cycle blind validation (v0.9.0 skill as shipped)](records/validation/2026-08-18-off-cycle-blind-validation.md) | 2026-08-18 | 6/6 PASS | 5/6, one format FAIL |
| [v0.9.0 release-harness record — 2026-08-15](records/validation/v0.9.0.md) | 2026-08-15 | PASS (6/6) | in the record’s prose |
| [v0.8.1 release-harness record — 2026-08-14](records/validation/v0.8.1.md) | 2026-08-14 | PASS (6/6) | in the record’s prose |
| [v0.8.0 release-harness record — 2026-08-11](records/validation/v0.8.0.md) | 2026-08-11 | PASS (6/6) | in the record’s prose |
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
| [Initial validation (v0.1.0, 2026-06-28), with two standing checks added 2026-06-29](records/validation/v0.1.0.md) | 2026-06-28 | in the record’s prose | — |

## Eval suite runs

Newest first. Whether a run counts as green is recorded with it, or marked pending the owner (#530).

| Run | Date | Result |
| --- | --- | --- |
| [2026-09-30 re-run — the first green run: with the plugin 12/12, on the committed fixtures, every with-plugin clean report conforming](records/evals/2026-09-30-rerun.md) | 2026-09-30 | Green (owner decision, #291; #530's condition: the re-run with the scaffold and grader fixes). With the plugin 3/3 on all four cases; the anchored header grader passed every with-plugin broken run. Without: 0/3 everywhere (broken n/a; clean by the judge alone, out of scoring since #591). 6/6 with-plugin clean reports conform. |
| [2026-09-30 — first run after #530: findings clean in every plugin run, but the js fixture was not the committed one, and two reports fail the format checker](records/evals/2026-09-30.md) | 2026-09-30 | Not green (owner decision, #530). With the plugin 3/3 on all four cases, every planted violation confirmed. Without: broken cases 0/3 (n/a, structural), js-clean 0/3, py-clean 2/3. The js fixture's ESLint was broken by the scaffold. 4 of the 6 with-plugin clean reports conform to the format checker; the broken reports' format is unknown. |
| [2026-09-28 — first real run: drift pass, probes and full pass](records/evals/2026-09-28.md) | 2026-09-28 | Not a green run: it found and fixed drift, and the runner's LLM judge failed reports that confirm every planted violation (#291, #530). On every deterministic grader the plugin arm was clean and the no-plugin arm failed every case. |
