# Dogfooding

plumb-line is held to its own principles. At each release that changes its
method surface, the `plumb-line-audit` methodology, the same two-pass audit
it tells you to run, is applied to plumb-line's own first-party source, and
what it found and what was done about each finding is recorded. (An auditor
that sniffs out code smells should pass its own smell test.)

Each self-audit is recorded in its own file in
[`records/dogfood/`](records/dogfood/). The records were moved here from
this file's earlier single-page form (#570); their words are unchanged, as
[`validation-results.md`](validation-results.md) describes. The two sections
after the table are living sections of this page, not records; they stood
before the v0.2.0 audit, and moved here unchanged except for the section rule
that separated them from it.

## Self-audits

Newest first.

| Self-audit | Date |
| --- | --- |
| [v0.12.0 dogfood self-audit — 2026-09-30](records/dogfood/v0.12.0.md) | 2026-09-30 |
| [v0.11.5 dogfood self-audit — 2026-09-28](records/dogfood/v0.11.5.md) | 2026-09-28 |
| [v0.11.4 dogfood self-audit — 2026-09-26](records/dogfood/v0.11.4.md) | 2026-09-26 |
| [v0.11.3 dogfood self-audit — 2026-09-25](records/dogfood/v0.11.3.md) | 2026-09-25 |
| [v0.11.2 dogfood self-audit — 2026-09-25](records/dogfood/v0.11.2.md) | 2026-09-25 |
| [v0.11.1 dogfood self-audit — 2026-09-20](records/dogfood/v0.11.1.md) | 2026-09-20 |
| [v0.11.0 dogfood self-audit — 2026-09-15](records/dogfood/v0.11.0.md) | 2026-09-15 |
| [v0.10.0 dogfood self-audit — 2026-08-19](records/dogfood/v0.10.0.md) | 2026-08-19 |
| [v0.9.0 dogfood self-audit — 2026-08-15](records/dogfood/v0.9.0.md) | 2026-08-15 |
| [v0.8.1 dogfood self-audit — 2026-08-14](records/dogfood/v0.8.1.md) | 2026-08-14 |
| [v0.8.0 dogfood self-audit — 2026-08-11](records/dogfood/v0.8.0.md) | 2026-08-11 |
| [v0.7.3 dogfood self-audit — 2026-07-19](records/dogfood/v0.7.3.md) | 2026-07-19 |
| [v0.7.2 dogfood self-audit — 2026-07-15](records/dogfood/v0.7.2.md) | 2026-07-15 |
| [v0.7.1 dogfood self-audit — 2026-07-12](records/dogfood/v0.7.1.md) | 2026-07-12 |
| [v0.7.0 dogfood self-audit](records/dogfood/v0.7.0.md) | 2026-07-11 |
| [v0.6.0 dogfood self-audit](records/dogfood/v0.6.0.md) | 2026-07-05 |
| [v0.5.1 dogfood self-audit](records/dogfood/v0.5.1.md) | 2026-07-03 |
| [v0.5.0 dogfood self-audit](records/dogfood/v0.5.0.md) | 2026-07-03 |
| [v0.4.1 dogfood self-audit](records/dogfood/v0.4.1.md) | 2026-07-02 |
| [v0.4.0 dogfood self-audit](records/dogfood/v0.4.0.md) | 2026-07-01 |
| [v0.3.1 dogfood self-audit](records/dogfood/v0.3.1.md) | 2026-07-01 |
| [v0.2.0 audit](records/dogfood/v0.2.0.md) | 2026-06-29 |
| [v0.1.0 dogfood self-audit — 2026-06-29](records/dogfood/v0.1.0.md) | 2026-06-29 |

## Beyond the fixtures

What is recorded of outside use, and where each piece landed:

- **2026-07-01** — an outside user's audit of a codebase they work on,
  submitted through the feedback form. The report is recorded below. Its
  friction note (move the marketplace install up) is quoted in #86; #83–#85
  cite the same first tester's feedback that day: the audit's report was
  hard to act on (bare `P#` codes, a report whose shape varied between runs,
  a report file written only sometimes). These four issues shipped in the
  v0.4.1 *Legible audit* release.
- **2026-08-14** — before adopting the primitives, doubt about starting on a
  project already under way, and about using them wrong. Quoted and answered
  in the fit map,
  [*Mid-project is the normal case*](../reference/fit-map.md#mid-project-is-the-normal-case).

Examples that arrive are added here with their date, the plumb-line version,
and what the audit found and missed, redacted as their owner asks.

### 2026-07-01 — outside audit, v0.3.1

Recorded 2026-09-26 from the feedback-form submission; the submitter agreed
to be quoted, and the codebase is described only in outline. Scope:
`plumb-line-audit` v0.3.1, a deep pass over a ~30k-line health-tracking
application. The form lists both languages; every file the report cites is
Python. The report says it read the highest-leverage paths line by line
rather than the whole codebase, and that it sharpens an earlier surface pass
whose other findings the form does not include. v0.3.1 predates the coverage
map (v0.5.0), so what it did not read is not recorded.

| # | Principle | Finding (as reported) |
| - | --------- | ------- |
| Headline | P3, P8, spine | One LLM call assigns items to categories and returns no confidence. Two decision chains then treat the guess as fact: a relative-risk figure rounded to three decimals, and an adherence verdict that decides whether an experiment can be evaluated at all, with nothing recording that the gate came from a classification. |
| N1 | P6 | A docstring says the new correlation engine "replaces" the old one. It does not: the old engine still feeds the user-facing export, so the export and the chat could tell different stories from the same data. |
| N2 | Spine | A "categories analysed" count includes only categories that produced a signal, so a run with no signals reports 0, which reads the same as a run that never happened. |
| N3 | P1 | The analysis rewrites the loaded source-of-truth records in place (lower-casing names), and matching elsewhere depends on that mutation, because another function does not normalise. |
| N4 | P3, P4 | Values an LLM extracted from web-search snippets are served with no confidence or caveat, while the AI estimate one tier below is honestly labelled, so the weaker source looks more authoritative. |
| N5 | P8 | Stored experiment verdicts do not record the environment-injectable thresholds that decided them, and some stored signal rows omit fields such as the score delta. |
| N6 | P9 | The signal maths has no golden or baseline test; a test of it stubs out the computation it would need to pin. |
| Confirmed | P5; P3, spine, P6; P7; P4 | The signal engine's thresholds are bare constants where the rest of the codebase injects them; research snippets are presented as "relevant current research" with their similarity score dropped and no floor; no output carries a contract version; a retrieval outage reads as "no research exists". |
| Clean | P2, spine | Layering holds apart from one call to another module's private function; the experiment evaluator (`inconclusive`), a not-found path and the export honour the null-result spine. |

**Outcome.** The submitter reports implementing all of the findings,
including finishing the migration to the new engine (N1).

**What this shows, and what it does not.** Every finding in this report was
acted on by someone who works on the code, which is the closest this project
has to precision evidence from outside. Recall is unknown: there is no
answer key for a real codebase, so nothing records what the audit missed. It
is one run, by one user, of the skill as it was on 2026-07-01; it says
nothing about the skill as it ships now.

An earlier version of this section, written on 2026-06-30 before this audit,
said the auditor "surfaced real issues that had passed human review" on an
unrelated production codebase. What that sentence rested on was not
recorded, so it is not repeated. This later record supports a similar claim
about real issues; nothing recorded shows the code had passed review.

## See also

[validation-results.md](validation-results.md) records the complementary check:
the auditor catching planted violations in the worked fixtures. Validation is the
external test; this is the self-test.
