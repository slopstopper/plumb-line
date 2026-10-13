# ADR-0023: Plain words: one meaning for "mock", revision-2 principle names, and "operator" for the person

**Status:** Proposed · 2026-10-13 (drafted from the owner's decisions recorded on GH #612, #593 and #643)

## Context

Three changes to plumb-line's words are scheduled together in v0.13.0,
"Plain words", because each one touches the same live guidance.

- **"Mock" had three meanings** (#612). It meant a test double, a source
  rung for non-real data, and P6's maturity level for an unfinished
  implementation. In round 3b of the impossible-task spike (#462), five
  honest runs labelled the stand-ins in their unit tests `source: "mock"`,
  and an answer key written in a different sense made them look like
  cheats. The owner ruled them honest. The fault was in the vocabulary.
- **The principles' names were uneven** (#593). Some were noun phrases,
  some were slogans ("Golden baseline + explain-the-drift"), and some
  differed from the standard term for the same practice ("Source-truth
  layer", "Injectable priors"). The one-line test also still said "stop
  and document the concern before implementing", where the method skill
  had answered the same moments with "yes, and" since #487, under the
  owner's ruling on #485.
- **"Builder" is changing meaning across the family** (#643,
  slopstopper/tokenomics#34). tokenomics is giving "builder" to one of its
  routing classes, so the family's word for the person running a coding
  agent on a project becomes **operator**.

## Decision

The owner, 2026-10-03, on #612 and #593, and 2026-10-06, on #643. The
history rule was first confirmed on 2026-10-03, on tokenomics#34.

### 1. One meaning per word for stand-ins

| Sense | Word | Notes |
| --- | --- | --- |
| A stand-in for a collaborator in a test | **test double** | In all prose. "Stub" or "mock" only where the kind matters, as in Meszaros's *xUnit Test Patterns* and Fowler's "Mocks Aren't Stubs". |
| Invented data, which is not real | **`mock`**, the source rung | Unchanged on the wire, with `derivedFromMock` and `PROVENANCE_VERSION`. Defined narrowly in SPEC, the principles and the glossary. This is the only meaning "mock" has in plumb-line's own prose. |
| An unfinished implementation | **`stub`**, P6's maturity level | Replaces `mock` in the maturity vocabulary. |

Owner, on keeping the rung: "Keeping mock would make it a less
complicated change and says the same thing as fake would."

So a placeholder service built while prototyping is at maturity `stub`
(P6), and the data it returns is labelled `mock` (P4). A unit test that
replaces that service with a test double is ordinary testing, and what it
may claim is limited by the method skill's rule from #623: a test never
presents a stand-in's result as `real`.

### 2. Principles revision 2

The P-numbers stay. Every name is a short noun phrase.

| # | Revision 1 | Revision 2 |
| --- | --- | --- |
| spine | null-result expressibility | Null results count |
| P1 | Source-truth layer | Source-of-truth layer |
| P2 | One-way layering | One-way layering |
| P3 | Confidence + provenance | Provenance and confidence |
| P4 | Quarantined fakery | Labelled stand-ins |
| P5 | Injectable priors | Named assumptions |
| P6 | Maturity vocabulary | Maturity vocabulary |
| P7 | Contracted outputs | Output contracts |
| P8 | State-first lineage | Recorded lineage |
| P9 | Golden baseline + explain-the-drift | Golden baselines |

P4 names the family that `mock`, approximate, fallback and cached data
belong to. On the name, the owner said: "stand ins feels less obviously
fake but its a more accurate name".

Revision 2 also amends the one-line test to the method skill's "yes, and"
(#593). The wording is drafted, as (e) below.

### 3. "Operator" for the person

"Builder", meaning the person, becomes "operator" in live guidance. Only
that sense changes, so every hit is read rather than replaced.

### 4. What changes, and what is left as written

- **Changed:** live guidance. That means the skills, the principles, the
  live docs, the bootstrap interview, and any eval grader regex that
  matches a skill phrase that changes.
- **Left as written:** the ADRs, including the earlier ones' principle
  names (they are append-only); `docs/records/**`;
  `evals/trigger/results/*`; and the published write-ups in
  `docs/content/`. This ADR records the rename once, in the table above,
  for anyone reading them.

## Drafted with this ADR

These follow from the decisions above but are not in the owner's words.
Approving this ADR's text approves them.

- **(a) P4's opt-in is recorded at the output.** P4 says "excluded from
  outputs unless explicitly opted in" and does not say who opts in. The
  current text names four different parties:
  - the glossary says "the consumer";
  - SPEC says "the caller" (the egress guard);
  - the method skill says "the owner" in one row and "a builder asking"
    in another;
  - the adopt skill says "the builder".

  Revision 2 settles it. The opt-in is recorded where the output is
  produced, in code or configuration a reviewer can see, as the egress
  guard's `noMock: false` is (ADR-0020). Whoever owns the output records
  it. An operator asking for the stand-in in an output is the reason for
  the opt-in, not the opt-in itself. The guard enforces, and the recorded
  opt-in is auditable (ADR-0022).
- **(b) P6's `stub` reads:** "placeholder that returns invented or
  hardcoded data, or reports success without doing the work".
- **(c) The glossary gains "Test double" and "Stand-in",** and "Quarantined
  data" becomes "Stand-in". "Prior" stays as a glossary term, defined as a
  named assumption.
- **(d) The audit's finding classes keep their names** ("Escaped fakery",
  "Hardcoded prior" and the rest). Each class names a failure, not a
  practice: an escaped stand-in presented as real is fakery. Blind
  validation scores findings by P-code, so no score depends on a class's
  name. The classes' descriptions follow the new vocabulary (for example,
  "partial/mock/planned" becomes "partial/stub/planned"), as do the
  principles they cite.
- **(e) The one-line test reads:**

  > Use this as a gut-check before any change. If the change would make
  > the system look more certain than it is, blur a layer boundary,
  > hardcode an assumption, or hide a stand-in, say so in a line first.
  > Then meet the need honestly, and keep what is uncertain, stand-in or
  > unfinished visible. The only no is presenting it as real, measured or
  > done.

  The method skill's mid-task section is aligned to the same words.
- **(f) The history rule's edges.**
  - **Also changed:**
    - the ruleset template and the fit map;
    - the README, `ROADMAP.md` and plugin metadata;
    - the live examples and their answer keys;
    - `primitives/` and `adapters/` prose, with the bundled copies synced;
    - the tests that quote a name or phrase that changes.
  - **Also left as written:** past CHANGELOG entries, the postmortems in
    `docs/postmortems/`, the stored audit reports
    `examples/incident-toolserver/audit-2026-09-25.md` and
    `audit-2026-09-30.md`, and the dated run notes in
    `examples/REMEDIATE-EXPECTATIONS.md`. Live text that quotes one of
    them, such as the README's rows from the 2026-09-30 report, keeps the
    record's words.
- **(g) Names that stay.** The omission table's `Null-expressible` column
  keeps its name, because renaming it would change report-format v4.
  "Operator" already appears in other senses (a transit operator in an
  eval query). The sweep leaves those alone.

## Consequences

- **No wire, API or contract change.** These all stay as they are:
  - the `mock` value, `derivedFromMock` and `PROVENANCE_VERSION`;
  - the report formats: report-format v4, remediation-format v1 and
    routing-format v1;
  - the checker's logic and `CHECKER_VERSION`.

  The checker reads principle names from the ruleset at run time. Its
  messages, comments and tests that quote a revision-1 name or "builder"
  change.
- **New reports cite revision 2.** A stored report under revision 1 is a
  record as delivered. Run against revision 2, the checker fails it as
  behind the ruleset, as it has since #220, and does not accuse its
  `format-validation` stamp (#581). Stored reports are not re-validated.
  #593's note that revision-1 reports "stay valid" holds for their stamps,
  not for a re-run.
- **The release harness runs in full before the tag.** The skills and the
  principles change, so blind validation (Part 1) and remediate
  validation (Part 1b) re-run against revision 2.
- **The change reaches a lot of live text.** On `main` on 2026-10-07, live
  files held about 100 uses of "builder" in 19 files, about 210
  revision-1 principle names that change, and about 640 uses of "mock".
  Most "mock" uses are the wire value in `primitives/`, and they stay. The
  sweep is split into units, each with its own review.
