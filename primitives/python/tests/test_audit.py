import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import provenance as p
import marked as m
import audit as a

def setup_function():
    p.reset_step_counter()

def test_silent_on_clean():
    assert a.audit_meta({'source':'real','confidence':'high','derived_from_mock':False,'lineage':[]}) == []

def test_flags_laundering():
    issues = a.audit_meta({'source':'real','confidence':'high','derived_from_mock':True,'lineage':[]})
    assert any('laundering' in i for i in issues)

def test_flags_over_claiming():
    meta = {'source':'derived','confidence':'high','derived_from_mock':False,
            'lineage':[{'id':'s1','confidence':'low','derived_from_mock':False}]}
    assert any('over-claiming' in i for i in a.audit_meta(meta))

# F1: audit must be no laxer than the combination law. An out-of-enum confidence
# on a step is laundering, not a free pass — treat it as the floor.
def test_flags_over_claim_out_of_enum_confidence():
    meta = {'source':'derived','confidence':'high','derived_from_mock':False,
            'lineage':[{'id':'s1','confidence':'huge','derived_from_mock':False}]}
    assert any('over-claiming' in i for i in a.audit_meta(meta))

def test_no_false_positive_when_step_has_no_confidence():
    meta = {'source':'derived','confidence':'high','derived_from_mock':False,
            'lineage':[{'id':'s1','derived_from_mock':False}]}
    assert not any('over-claiming' in i for i in a.audit_meta(meta))

# Totality (G3): audit must never raise, even on a malformed lineage step — it
# returns an issue list. Mirrors JS, which reads non-dict steps as no-signal.
def test_audit_is_total_on_malformed_lineage_step():
    meta = {'source':'derived','confidence':'high','derived_from_mock':False,
            'lineage':[None, 'oops', {'id':'s1','confidence':'low','derived_from_mock':False}]}
    issues = a.audit_meta(meta)  # must not raise
    # the one real dict step still drives the over-claim check
    assert any('over-claiming' in i for i in issues)

def test_flags_taint_dropped():
    meta = {'source':'derived','confidence':'low','derived_from_mock':False,
            'lineage':[{'id':'s1','confidence':'low','derived_from_mock':True}]}
    assert any('taint dropped' in i for i in a.audit_meta(meta))

def test_flags_unreproducible():
    assert any('unreproducible' in i for i in
               a.audit_meta({'source':'derived','confidence':'low','derived_from_mock':False,'lineage':[]}))

def test_silent_on_derive_output():
    base = m.mark(1, source='real', confidence='high')
    bad = m.mark(2, source='mock', confidence='low')
    out = m.derive([base, bad], lambda x, y: x + y)
    assert a.audit_meta(m.meta_of(out)) == []

def test_no_throw_on_invalid_top_confidence():
    result = a.audit_meta({'source': 'derived', 'confidence': None,
                           'lineage': [{'confidence': 'low', 'derivedFromMock': False}]})
    assert isinstance(result, list)

def test_empty_meta_returns_empty_list():
    assert a.audit_meta({}) == []

def test_none_meta_returns_missing_meta():
    assert a.audit_meta(None) == ['missing meta']

def test_flags_numeric_over_claiming():
    meta = {'source':'derived','confidence':'low','confidence_score':0.9,'derived_from_mock':False,
            'lineage':[{'id':'s1','confidence':'low','confidence_score':0.2}]}
    assert any('over-claiming: confidenceScore' in i for i in a.audit_meta(meta))

def test_silent_when_score_within_lineage():
    meta = {'source':'derived','confidence':'low','confidence_score':0.2,'derived_from_mock':False,
            'lineage':[{'id':'s1','confidence':'low','confidence_score':0.2}]}
    assert a.audit_meta(meta) == []

def test_flags_source_over_claim():
    meta = {'source':'derived','confidence':'low','derived_from_mock':True,'weakest_source':'real',
            'lineage':[{'id':'s1','source':'mock','confidence':'low','derived_from_mock':True}]}
    assert any('source over-claim' in i for i in a.audit_meta(meta))

VALID = {'source':'real','confidence':'high','derived_from_mock':False,'lineage':[]}

def test_validate_silent_on_complete_envelope():
    assert a.validate_envelope(VALID) == []

def test_validate_is_structural_complement_to_audit():
    # audit_meta({}) is [] (no claims to contradict); validate_envelope reports
    # all four required fields missing. The two checkers are complementary.
    assert a.audit_meta({}) == []
    issues = a.validate_envelope({})
    assert len(issues) == 4
    for f in ('source', 'confidence', 'derivedFromMock', 'lineage'):
        assert any(f'required field: {f}' in i for i in issues)

def test_validate_flags_single_missing_field():
    no_lineage = {k: v for k, v in VALID.items() if k != 'lineage'}
    assert any('required field: lineage' in i for i in a.validate_envelope(no_lineage))

def test_validate_flags_wrong_type():
    assert any("field 'lineage' must be" in i
               for i in a.validate_envelope({**VALID, 'lineage': 'nope'}))
    assert any("field 'derivedFromMock' must be" in i
               for i in a.validate_envelope({**VALID, 'derived_from_mock': 'false'}))

def test_validate_is_total():
    assert a.validate_envelope(None) == ['missing meta']
    assert any('not an envelope object' in i for i in a.validate_envelope('nope'))
    assert any('not an envelope object' in i for i in a.validate_envelope([]))
