# The retraction that started as a sign flip

*A reconstruction postmortem. The incident below is real and documented in
the scientific record. The code in this write-up is a small synthetic
reconstruction of the same failure pattern
([`examples/incident-pipeline/`](../../examples/incident-pipeline/)) — not
the lab's actual pipeline. Sources at the end.*

## The incident

In December 2006, the journal *Science* ran a news story with an unusually
blunt headline: "A Scientist's Nightmare: Software Problem Leads to Five
Retractions." Geoffrey Chang's structural-biology lab at Scripps had
retracted five papers — three of them in *Science* — describing the shapes
of proteins that move molecules across cell membranes. Five entries in the
Protein Data Bank, the shared reference library other labs build on, were
withdrawn with them.

The cause was a homemade data-processing script — trusted and unversioned —
that changed the sign of certain values on their way through the pipeline. In protein crystallography that
sign carries the handedness of the structure — flip it and you derive a
mirror image of the truth. The derived structures looked plausible, passed
peer review, and were published.

Then the error compounded, because published structures are inputs to other
people's work. Groups whose experimental results disagreed with the
published structures were, in effect, told the anomaly was theirs.
Follow-up work across the field was measured against a mirror image. The wrong
claim sat upstream of a research field, and nothing in the published record
could reveal it — the script was not versioned, not published, and its
effect was invisible in the output.

What finally broke the spell came from outside the lab: in 2006 another
group published a structure of a related protein, determined independently,
that could not be reconciled with Chang's. Only then did the lab hunt
backward through its own pipeline and find the script. The retraction
followed, along with years of re-derivation and repair — because no stored
artifact could point at the error; only redoing the work could.

## The timeline, generalized

Strip the crystallography and the shape is any data pipeline:

1. A processing step is inherited and trusted. Somewhere inside it, a
   transform is not what its users believe. Nothing records its presence in
   the pipeline, let alone its version.
2. Conclusions computed through it look plausible and are stored — as
   figures or database entries — with no record of what produced them.
3. The conclusions become inputs to further work. Contradicting evidence
   downstream reads as *someone else's* anomaly.
4. A contradiction too strong to dismiss finally arrives. Attribution now
   requires re-deriving everything, because the artifacts themselves can
   answer no questions.
5. The correction costs years. The corrective action available at the time:
   retraction and starting over.

## Root cause

The sign flip was the trigger, but scripts have bugs; that is not the class.
The class is that **the conclusions could not answer for themselves**. Each
published result was a claim whose full derivation — which raw data, through
which code, at which version — existed nowhere except, temporarily and
partially, in the lab's working memory. An output you cannot regenerate from
recorded inputs is a claim you cannot audit; when doubt eventually arrived,
there was nothing to audit, only everything to redo.

In plumb-line's terms this is *state-first lineage*: store the conditions
that produced an output, not just the conclusion. The unversioned script is
also a familiar face — a *prior* buried in logic, an assumption (about what
the processing step does) that no one reading the output could see or check.

## The reconstruction

[`examples/incident-pipeline/`](../../examples/incident-pipeline/) rebuilds
the pattern in about 40 lines of Python: raw instrument readings are
calibrated against a baseline, averaged, and stored as a one-line
conclusion. Then the pipeline is run again with an "inherited" calibration
step whose operands are reversed — the sign flip.

Run the uninstrumented version (`python3 broken/pipeline.py`):

```
analysis — dataset D42
conclusion: effect: positive (mean +0.40)

analysis — dataset D42
conclusion: effect: negative (mean -0.40)
```

Two runs, same data, opposite conclusions — and the stored artifacts are
indistinguishable. Which one is right? Which processing produced which?
Neither artifact can say. This is the incident, in miniature: the moment the
first conclusion is contradicted, the only way to attribute the difference
is to re-derive everything by hand.

## Corrective action

The instrumented version (`python3 instrumented/pipeline.py`) changes one
thing: every stage of the pipeline derives its output through a provenance
envelope, naming the exact code that produced it, and each stored conclusion
keeps its whole chain:

```
analysis — dataset D42
conclusion: effect: positive (mean +0.40)
provenance chain:
  analysis.mean_effect@v1
    <- preprocess.baseline_subtract@v1
      <- measurements.csv [real/high]

analysis — dataset D42
conclusion: effect: negative (mean -0.40)
provenance chain:
  analysis.mean_effect@v1
    <- preprocess.inherited@v2
      <- measurements.csv [real/high]
```

The conclusions still contradict each other — provenance does not fix a
flipped sign, and no label makes a wrong number right. What changed is the
cost of the question that took the real incident years: *which data, through
which code, produced this number?* Read the two chains. The only line that
differs names the inherited preprocessing step. The flip is attributable in
one read, from the artifacts alone, by someone with no access to anybody's
working memory.

The demo's last section shows the incident's storage habit directly — a
conclusion kept as a derived result with no lineage at all:

```
a conclusion stored bare (derived, no lineage):
  unreproducible: derived value has no lineage
```

The library's runtime checker flags it: a derived value that cannot point at
its inputs is only an assertion. That check is the whole incident compressed
to one line.

## What this class of failure costs

This one is the expensive end of the family. Demo 2's mock tools cost an
argument and a hand-audit; the load sheet cost a thrust margin; here the
bill was five retractions, years of a field's time, and other scientists'
work read as error because a wrong claim upstream carried no way to question
it. The pattern is the same sentence as ever — **a value that forgot where
it came from was combined into a claim someone acted on** — with the tail
risk made visible: the longer a conclusion outlives its derivation, the more
work builds on top, and the more the eventual correction costs. Lineage is
cheap at write time; at doubt time it is the difference between reading a
chain and redoing the work — and here the doubt-time price was paid by a
whole field.

## Sources

- [Retraction, *Science* 314, 1875 (2006)](https://www.science.org/doi/10.1126/science.314.5807.1875b)
  — the formal retraction of the three *Science* papers.
- [G. Miller, "A Scientist's Nightmare: Software Problem Leads to Five
  Retractions," *Science* 314, 1856 (2006)](https://www.science.org/doi/full/10.1126/science.314.5807.1856)
  — the news account: the inherited script, the sign change, the five
  papers, the contradicting independent structure.
- [K. Diederichs, "Analysis of errors in the structure determination of
  MsbA," *Acta Cryst.* D65 (2009)](https://journals.iucr.org/d/issues/2009/02/00/ba5129/)
  — technical post-mortem of how the wrong structures arose.

---

*Provenance of this document: drafted by Claude (claude-fable-5), reviewed and
approved by the maintainer; audited with `plumb-line-audit` before
publication like everything else here. The reconstruction code is in
[`examples/incident-pipeline/`](../../examples/incident-pipeline/) with a
deterministic integrity test.*
