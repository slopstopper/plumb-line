"""test_long_lineage — combine, audit and guard are total on a very long lineage (#560).

JS threw `RangeError: Maximum call stack size exceeded` here, from argument
spreads over the lineage, where Python's min() over a list does not. SPEC §5
requires the checker to be total, and the two languages must agree: the same
lineage and the same expected results are in the JS twin,
primitives/js/long-lineage.test.mjs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audit import audit_meta
from guard import guard, ProvenanceRefused
from provenance import combine_provenance, make_meta

N = 200_000
WEAK_AT = 150_000
STRONG = combine_provenance(make_meta(source='real', confidence='high', confidence_score=0.9))['lineage'][0]
WEAK = combine_provenance(make_meta(source='fallback', confidence='low', confidence_score=0.4))['lineage'][0]
LONG = make_meta(source='derived', confidence='low', confidence_score=0.4, derived_from_mock=False,
                 weakest_source='fallback',
                 lineage=[WEAK if i == WEAK_AT else STRONG for i in range(N)])


def _reasons(**options):
    try:
        guard({'value': 1, 'meta': LONG}, **options)
    except ProvenanceRefused as e:
        return e.reasons
    return 'passed'


def test_combines_to_the_weakest_confidence_score_and_source():
    c = combine_provenance(LONG)
    assert [c['confidence'], c['confidence_score'], c['weakest_source'], len(c['lineage'])] == \
        ['low', 0.4, 'fallback', N + 1]


def test_audits_clean_when_the_headline_matches_the_lineage():
    assert audit_meta(LONG) == []


def test_audits_each_over_claim_against_the_one_weak_step():
    assert audit_meta({**LONG, 'confidence': 'high', 'confidence_score': 0.9, 'weakest_source': 'real'}) == [
        "over-claiming: confidence 'high' exceeds weakest lineage confidence 'low'",
        "over-claiming: confidenceScore 0.9 exceeds weakest lineage score 0.4",
        "source over-claim: weakestSource 'real' is cleaner than lineage's 'fallback'",
    ]


def test_guards_on_the_weakest_step():
    assert _reasons(min_confidence='low') == 'passed'
    assert _reasons(min_confidence='medium') == ['confidence: low is below the required medium']
    assert _reasons(min_source='real') == ['source: fallback is below the required real']
