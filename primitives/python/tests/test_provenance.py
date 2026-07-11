import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import provenance as p

def setup_function():
    p.reset_step_counter()

def test_provenance_version_is_2():
    assert p.PROVENANCE_VERSION == 2

def test_make_meta_stamps_version():
    assert p.make_meta(source='real')['provenance_version'] == 2

def test_combine_carries_version():
    out = p.combine_provenance(p.make_meta(source='real'))
    assert out['provenance_version'] == 2

def test_constants_order():
    assert p.STATUS == ['unavailable','mock','inferred','fallback','semiReal','derived','real']
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
    # A value combined from no inputs is derived from nothing — 'unavailable',
    # not 'derived'. 'derived' would contradict audit_meta's "derived value has
    # no lineage" check (SPEC §3 vs §5). See #25.
    out = p.combine_provenance()
    assert out['derived_from_mock'] is False
    assert out['confidence'] == 'none'
    assert out['source'] == 'unavailable'
    assert out['lineage'] == []

def test_combine_step_ids_are_reproducible_content_addressed():
    # No module-level counter: two independent combines with identical inputs
    # produce identical step ids, since ids are a pure function of content. See #23.
    first = p.combine_provenance(REAL, MOCK)
    second = p.combine_provenance(REAL, MOCK)
    assert [s['id'] for s in first['lineage']] == [s['id'] for s in second['lineage']]
    assert all(s['id'].startswith('sha256:') for s in first['lineage'])

def test_combine_dedups_identical_sub_lineages_by_design():
    # Two independently-built envelopes with identical content produce identical
    # ids for their steps — that collision is intended dedup, not an error,
    # because it means "the same derivation happened twice." See #52.
    a = p.combine_provenance(REAL, MOCK)
    b = p.combine_provenance(REAL, MOCK)
    out = p.combine_provenance(a, b)
    ids = [s['id'] for s in out['lineage']]
    assert len(ids) == 6
    assert ids[0] == ids[2]
    assert ids[1] == ids[3]
    assert all(i.startswith('sha256:') for i in ids)

def test_input_step_id_stable_across_recombination():
    a = dict(REAL)
    once = p.combine_provenance(a)
    twice = p.combine_provenance(a, {'source': 'mock', 'confidence': 'low', 'derived_from_mock': True, 'lineage': []})
    id_in_once = next(s['id'] for s in once['lineage'] if s['source'] == 'real')
    id_in_twice = next(s['id'] for s in twice['lineage'] if s['source'] == 'real')
    assert id_in_once == id_in_twice

def test_combine_no_longer_emits_sequential_step_ids():
    out = p.combine_provenance(REAL)
    assert all(s['id'].startswith('sha256:') for s in out['lineage'])

def test_combine_records_lineage_step_per_input():
    out = p.combine_provenance(REAL, MOCK)
    assert len(out['lineage']) == 2
    assert out['lineage'][1]['source'] == 'mock'
    assert out['lineage'][1]['derived_from_mock'] is True
    assert out['lineage'][0]['id'].startswith('sha256:')

def test_combine_accumulates_prior_lineage():
    # Inherited steps are carried into the output (identified by content, not by
    # their original id — the output renumbers every step for §4 uniqueness).
    with_history = dict(REAL)
    with_history['lineage'] = [{'id':'old','of':'prior'}]
    out = p.combine_provenance(with_history, SEMI)
    assert any(s.get('of') == 'prior' for s in out['lineage'])

def test_combine_tolerates_empty_dict_member():
    out = p.combine_provenance({})
    assert out['source'] == 'derived'
    assert out['derived_from_mock'] is False

def test_combine_tolerates_none_member():
    out = p.combine_provenance(None, REAL)
    assert out['source'] == 'derived'

def test_weakest_source():
    assert p.weakest_source('real', 'mock', 'semiReal') == 'mock'
    assert p.weakest_source('real', 'semiReal') == 'semiReal'
    assert p.weakest_source('real', 'bogus') == 'real'
    assert p.weakest_source() is None
    assert p.weakest_source('bogus') is None

def test_is_score():
    assert p.is_score(0) is True
    assert p.is_score(1) is True
    assert p.is_score(0.5) is True
    assert p.is_score(1.1) is False
    assert p.is_score(-0.1) is False
    assert p.is_score('0.5') is False
    assert p.is_score(True) is False

def test_combine_confidence_score():
    assert p.combine_confidence_score([0.9, 0.2, 0.6]) == 0.2
    assert p.combine_confidence_score([0.9, None]) is None
    assert p.combine_confidence_score([]) is None

REAL_SCORED = {'source':'real','confidence':'high','confidence_score':0.9,'derived_from_mock':False,'lineage':[]}
MOCK_SCORED = {'source':'mock','confidence':'low','confidence_score':0.2,'derived_from_mock':True,'lineage':[]}

def test_combine_floors_confidence_score():
    assert p.combine_provenance(REAL_SCORED, MOCK_SCORED)['confidence_score'] == 0.2

def test_combine_omits_score_on_partial_coverage():
    out = p.combine_provenance(REAL_SCORED, {'source':'real','confidence':'high'})
    assert 'confidence_score' not in out

def test_combine_records_weakest_source():
    assert p.combine_provenance(REAL_SCORED, MOCK_SCORED)['weakest_source'] == 'mock'

def test_combine_omits_weakest_source_for_zero_inputs():
    assert 'weakest_source' not in p.combine_provenance()

def test_combine_records_score_on_lineage_step():
    out = p.combine_provenance(REAL_SCORED, MOCK_SCORED)
    assert out['lineage'][0]['confidence_score'] == 0.9
    assert out['lineage'][1]['confidence_score'] == 0.2

def test_combine_omits_score_on_step_without_one():
    out = p.combine_provenance(REAL_SCORED, {'source':'real','confidence':'high'})
    assert 'confidence_score' not in out['lineage'][1]

def test_inferred_between_mock_and_fallback():
    assert p.STATUS.index('mock') < p.STATUS.index('inferred') < p.STATUS.index('fallback')

def test_combine_inferred_weakest_over_fallback():
    out = p.combine_provenance(p.make_meta(source='fallback', confidence='low'),
                               p.make_meta(source='inferred', confidence='low'))
    assert out['weakest_source'] == 'inferred'

def test_step_id_known_leaf():
    step = {'of': 'input', 'source': 'real', 'confidence': 'high', 'derived_from_mock': False}
    assert p.step_id(step, []) == 'sha256:097181b20233'

def test_step_id_input_order_independent():
    step = {'of': 'input', 'source': 'real', 'confidence': 'high', 'derived_from_mock': False}
    assert p.step_id(step, ['b', 'a']) == p.step_id(step, ['a', 'b'])
