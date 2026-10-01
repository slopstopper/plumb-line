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
from marked import derive
from provenance import combine_confidence_score, combine_provenance, make_meta

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


def test_combines_200000_scores_to_the_weakest():
    # Twin of the JS row added by the v0.12.0 dogfood audit.
    assert combine_confidence_score([0.4 if i == WEAK_AT else 0.9 for i in range(N)]) == 0.4


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


# A lineage with a hole (#560 review): JS arrays can have holes, which reduce,
# every, some and forEach skip. Python has none; its twin is a None step, and
# both give the same results (primitives/js/long-lineage.test.mjs).
HOLED = make_meta(source='derived', confidence='high', derived_from_mock=False, weakest_source='real',
                  lineage=[None, STRONG])


def test_a_none_step_is_audited_as_a_step_that_is_not_an_object():
    assert audit_meta(HOLED) == [
        "source over-claim: weakestSource 'real' cannot be shown: a lineage step's source is unknown",
        "unknown source: lineage step 0 is not an object",
    ]


def test_a_none_step_is_refused_by_the_guard_with_or_without_a_confidence_floor():
    for options in ({'min_confidence': 'high'}, {}):
        guarded = {'value': 1, 'meta': HOLED}
        try:
            guard(guarded, **options)
        except ProvenanceRefused as e:
            assert e.reasons == ['invalid envelope: lineage step 0 is not a plain object']
        else:
            raise AssertionError(f'passed with {options}')


def test_combine_keeps_a_none_step():
    c = combine_provenance(HOLED)
    assert [len(c['lineage']), c['lineage'][0], 'weakest_source' in c] == [3, None, False]
    assert audit_meta(c) == ["unknown source: lineage step 0 is not an object"]


def test_a_none_step_is_refused_by_the_guard_after_a_derive():
    derived = derive([{'value': 1, 'meta': HOLED}], lambda v: v)
    for options in ({'min_confidence': 'high'}, {}):
        try:
            guard(derived, **options)
        except ProvenanceRefused as e:
            assert e.reasons == ['invalid envelope: lineage step 0 is not a plain object']
        else:
            raise AssertionError(f'passed with {options}')


def test_no_combined_score_over_a_gap():
    assert combine_confidence_score([0.5, None, 0.3]) is None
    assert combine_confidence_score([None, None]) is None
