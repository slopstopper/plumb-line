# The plane that thought its passengers were children

*A reconstruction postmortem. The incident below is real and documented by the
UK Air Accidents Investigation Branch. The code in this write-up is a small
synthetic reconstruction of the same failure pattern
([`examples/incident-loadsheet/`](../../examples/incident-loadsheet/)) — not
the airline's actual system. Sources at the end.*

## The incident

On 21 July 2020, a TUI Airways Boeing 737 took off from Birmingham for Palma
de Mallorca weighing 1,244 kg more than its paperwork said. The load sheet —
the document that tells the crew the aircraft's mass, from which they set
engine thrust — was internally consistent, arithmetically correct, and wrong.

The cause was a single assumption inside an upgraded check-in system.
Airlines don't weigh passengers; they assign standard weights by category —
one figure for an adult, a smaller one for a child. The upgraded system
decided the category from the passenger's honorific, and it had been
programmed in a country where "Miss" is the title of a child and "Ms" the
title of an adult woman. On this flight, 38 adult women had "Miss" on their
booking. The system counted every one of them as a child: 35 kg each instead
of 69 kg.

Nothing on the load sheet distinguished a category that was *known* from a
category that had been *guessed from a title*. The AAIB report records that
the crew noticed a discrepancy between the load sheet and the flight-plan
figures and checked what the paperwork allowed them to check; the commander
was content with the sheet — which is the point: the sheet was internally
consistent, and nothing on it could reveal that 38 categories had been
guessed. Thrust was set from the understated total. The AAIB classified it a
serious incident; the flight landed safely, the thrust shortfall being
marginal. The airline's corrective action was manual checks — humans
re-reading honorifics and double-checking passenger status until the
software could be fixed.

## The timeline, generalized

Strip the aviation specifics and the shape is familiar:

1. A system change alters how a value is guessed. The guess itself is old —
   standard weights are always assumptions — but its behavior moves, and
   nothing records that it moved.
2. Guessed values enter the data path through the same door as recorded ones.
   Every row looks like every other row.
3. A downstream aggregate is computed correctly from partly-guessed inputs.
   It looks exactly as trustworthy as one computed from known inputs.
4. A human acts on the aggregate. The one artifact in front of them — the
   tidy total — carries no signal that anything under it was inferred.
5. The error surfaces after the fact, and the remedy is more human
   checking.

## Root cause

The arithmetic was never wrong. The failure is that **an inference was
dressed as a fact**: a category guessed from an honorific entered the
calculation indistinguishable from a category read off a booking record, and
every number computed downstream inherited that disguise. Once the guess was
in, the load sheet could not have confessed it even if anyone had asked —
"how sure are we of this total?" was not a question the data could answer.

In plumb-line's terms: the honorific convention and the standard weights are
*priors* — judgment calls that were buried as constants inside logic rather
than surfaced as versioned, inspectable configuration — and the values they
produced carried no *provenance or confidence*, so a guess and a measurement
were the same thing to every consumer downstream.

## The reconstruction

[`examples/incident-loadsheet/`](../../examples/incident-loadsheet/) rebuilds
the pattern in about 50 lines of Python: a ten-passenger manifest where seven
categories come from the booking record and three are guessed from
honorifics — three adult passengers titled "Miss", counted at child weight.

Run the uninstrumented version (`python3 broken/loadsheet.py`):

```
load sheet — flight PL123:
  1A  Mr     adult  84 kg
  1B  Mrs    adult  84 kg
  2A  Ms     adult  84 kg
  2B  Mr     adult  84 kg
  3A  Miss   child  35 kg
  3B  Mr     adult  84 kg
  4A  Miss   child  35 kg
  4B  Mrs    adult  84 kg
  5A  Miss   child  35 kg
  5B  Mr     adult  84 kg
total takeoff mass: 693 kg
load sheet: complete
```

Tidy, confident, and 147 kg light. The three guessed rows are
indistinguishable from the seven known ones. This is the incident, in
miniature.

## Corrective action

The instrumented version (`python3 instrumented/loadsheet.py`) changes one
thing: each weight is wrapped in a provenance envelope at the moment its
category is decided, recording *how it was known*. And here an honest
objection surfaces immediately: aren't all ten weights guesses? Nobody
weighed anyone — even the correctly categorized rows use a standard figure,
a statistical estimate. Quite right, and the envelope says so. A weight
whose category came from the booking record is marked `real` for source (the
category is a recorded fact) but only `medium` for confidence (the weight
built on it is an approved estimate). A weight whose category was guessed
from a title is `inferred`, confidence `low` — an estimate resting on a
guess. No row can honestly claim high confidence, and none does.

The total is then *derived* from the wrapped weights under the library's one
rule, the conservative combination law: a result is never more trustworthy
than its least trustworthy input. The same sheet now prints:

```
load sheet — flight PL123:
  1A  Mr     84 kg  [real/medium — booking]
  1B  Mrs    84 kg  [real/medium — booking]
  2A  Ms     84 kg  [real/medium — booking]
  2B  Mr     84 kg  [real/medium — booking]
  3A  Miss   35 kg  [inferred/low — guessed from title]
  3B  Mr     84 kg  [real/medium — booking]
  4A  Miss   35 kg  [inferred/low — guessed from title]
  4B  Mrs    84 kg  [real/medium — booking]
  5A  Miss   35 kg  [inferred/low — guessed from title]
  5B  Mr     84 kg  [real/medium — booking]
total takeoff mass: 693 kg

load sheet provenance:
  confidence: low
  weakest_source: inferred
  inferred inputs: 3/10 (computed from lineage, not estimated)
```

The total is the same number — provenance does not fix a wrong guess. What
changed is what the total *knows about itself*. The envelope records the
ancestry of the value (its lineage), so the sheet can now answer the question
the crew asked and the paperwork couldn't: how much of this rests on a guess?
Three inputs in ten, and the total is only as confident as its shakiest one.
A consumer — a human reading the sheet, or code deciding whether the number
is fit to act on — sees `confidence: low` before anything is done with it.
And note what the law implies for the best case: a sheet with every category
known would come out `medium`, never `high` — because a total built from
estimates is an estimate, and now the paperwork admits it.

The last section of the demo makes the incident's exact move: it issues the
sheet as fully confident anyway, deriving the total while claiming
`confidence: "high"`:

```
attempted over-claim (derive with confidence: "high"):
  over-claiming: confidence 'high' exceeds weakest lineage confidence 'low'
```

The claim is accepted; the lineage is not fooled; the library's runtime
checker flags the contradiction. A load sheet that says "complete" over
guessed inputs is exactly this over-claim — made structural, and therefore
catchable, instead of invisible.

## What this class of failure costs

Here the margin held: the thrust shortfall was small and the aircraft flew.
The airline's fix — humans double-checking honorifics — treats the symptom;
the class-level fix is a value that cannot forget it was guessed. The pattern
generalizes past aviation: **an inference dressed as a fact was aggregated
into a number someone acted on.** Any system that assigns values by rule,
convention, or model — and mixes them with recorded ones — can carry this
failure. It needs no AI to arise — and systems where agents generate values
at scale can reproduce it at scale.

## Sources

- [AAIB investigation: Boeing 737-8K5, G-TAWG, 21 July 2020](https://www.gov.uk/aaib-reports/aaib-investigation-to-boeing-737-8k5-g-tawg-21-july-2020)
  ([full report PDF](https://assets.publishing.service.gov.uk/media/604f423be90e077fdf88493f/Boeing_737-8K5_G-TAWG_04-21.pdf))
  — the incident, the 1,244 kg figure, the standard weights, and the
  corrective actions.
- [BBC: "Software flaw led to 'serious incident' on Tui flight"](https://www.bbc.co.uk/news/technology-56690529)
  — contemporary coverage.

---

*Provenance of this document: drafted by Claude (claude-fable-5), reviewed and
approved by the maintainer; audited with `plumb-line-audit` before
publication like everything else here. The reconstruction code is in
[`examples/incident-loadsheet/`](../../examples/incident-loadsheet/) with a
deterministic integrity test.*
