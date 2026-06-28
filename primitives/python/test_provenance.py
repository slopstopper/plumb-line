import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import provenance as p

def setup_function():
    p.reset_step_counter()

def test_constants_order():
    assert p.STATUS == ['unavailable','mock','fallback','semiReal','derived','real']
    assert p.CONFIDENCE == ['none','low','medium','high']

def test_make_meta_defaults():
    m = p.make_meta()
    assert m['source'] == 'derived'
    assert m['confidence'] == 'none'
    assert m['derived_from_mock'] is False
    assert m['lineage'] == []

def test_make_meta_infers_mock():
    assert p.make_meta(source='mock')['derived_from_mock'] is True

def test_make_meta_explicit_flag_wins():
    assert p.make_meta(source='real', derived_from_mock=True)['derived_from_mock'] is True

def test_weakest_confidence():
    assert p.weakest_confidence('high','low','medium') == 'low'
    assert p.weakest_confidence() == 'none'
    assert p.weakest_confidence('high','bogus') == 'none'

def test_taints():
    assert p.taints({'source':'mock','derived_from_mock':False}) is True
    assert p.taints({'source':'real','derived_from_mock':True}) is True
    assert p.taints({'source':'real','derived_from_mock':False}) is False

REAL = {'source':'real','confidence':'high','derived_from_mock':False,'lineage':[]}
MOCK = {'source':'mock','confidence':'low','derived_from_mock':True,'lineage':[]}
SEMI = {'source':'semiReal','confidence':'medium','derived_from_mock':False,'lineage':[]}

def test_combine_taints_on_any_mock():
    assert p.combine_provenance(REAL, MOCK)['derived_from_mock'] is True

def test_combine_stays_clean():
    assert p.combine_provenance(REAL, SEMI)['derived_from_mock'] is False

def test_combine_degrades_confidence():
    assert p.combine_provenance(REAL, SEMI)['confidence'] == 'medium'
    assert p.combine_provenance(REAL, MOCK)['confidence'] == 'low'

def test_combine_source_is_derived():
    assert p.combine_provenance(REAL, SEMI)['source'] == 'derived'

def test_combine_taints_from_mock_source_even_if_flag_false():
    sneaky = {'source':'mock','confidence':'low','derived_from_mock':False,'lineage':[]}
    assert p.combine_provenance(REAL, sneaky)['derived_from_mock'] is True

def test_combine_ors_three_inputs():
    assert p.combine_provenance(REAL, REAL, MOCK)['derived_from_mock'] is True

def test_combine_zero_inputs():
    out = p.combine_provenance()
    assert out['derived_from_mock'] is False
    assert out['confidence'] == 'none'
    assert out['source'] == 'derived'
    assert out['lineage'] == []

def test_combine_records_lineage_step_per_input():
    out = p.combine_provenance(REAL, MOCK)
    assert len(out['lineage']) == 2
    assert out['lineage'][1]['source'] == 'mock'
    assert out['lineage'][1]['derived_from_mock'] is True
    assert out['lineage'][0]['id'] == 'step-1'

def test_combine_accumulates_prior_lineage():
    with_history = dict(REAL); with_history['lineage'] = [{'id':'old','of':'prior'}]
    out = p.combine_provenance(with_history, SEMI)
    assert any(s['id'] == 'old' for s in out['lineage'])

def test_combine_tolerates_empty_dict_member():
    out = p.combine_provenance({})
    assert out['source'] == 'derived'
    assert out['derived_from_mock'] is False

def test_combine_tolerates_none_member():
    out = p.combine_provenance(None, REAL)
    assert out['source'] == 'derived'
