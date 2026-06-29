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
