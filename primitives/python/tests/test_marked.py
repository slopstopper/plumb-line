import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import provenance as p
import marked as m

def setup_function():
    p.reset_step_counter()

def test_mark_and_unwrap():
    x = m.mark(100, source='real', confidence='high')
    assert x['value'] == 100
    assert x['meta']['source'] == 'real'
    assert m.unwrap(x) == 100

def test_derive_value_and_taint():
    base = m.mark(100, source='real', confidence='high')
    rate = m.mark(0.029, source='mock', confidence='low')
    total = m.derive([base, rate], lambda b, r: b * (1 + r))
    assert abs(total['value'] - 102.9) < 1e-9
    assert total['meta']['derived_from_mock'] is True
    assert total['meta']['confidence'] == 'low'

def test_derive_meta_equals_combine():
    a = m.mark(1, source='real', confidence='high')
    b = m.mark(2, source='semiReal', confidence='medium')
    via_derive = m.meta_of(m.derive([a, b], lambda x, y: x + y))
    p.reset_step_counter()
    via_law = p.combine_provenance(m.meta_of(a), m.meta_of(b))
    assert via_derive == via_law

def test_source_override_cannot_clear_taint():
    clean = m.mark(1, source='real', confidence='high')
    dirty = m.mark(2, source='mock', confidence='low')
    out = m.derive([clean, dirty], lambda a, b: a + b, source='real')
    assert out['meta']['source'] == 'real'
    assert out['meta']['derived_from_mock'] is True

def test_derive_lineage_override_is_ignored():
    a = m.mark(1, source='real', confidence='high')
    b = m.mark(2, source='semiReal', confidence='medium')
    out = m.derive([a, b], lambda x, y: x + y, lineage=[])
    assert len(m.meta_of(out)['lineage']) > 0

# F2: derive must be no weaker than make_meta — an out-of-range confidence_score
# override is dropped by the same validation, not stored raw.
def test_derive_drops_out_of_range_score_override():
    base = m.mark(100, source='real', confidence='high', confidence_score=0.9)
    out = m.derive([base], lambda b: b, confidence_score=2)
    assert 'confidence_score' not in out['meta']

def test_derive_keeps_valid_score_override():
    base = m.mark(100, source='real', confidence='high', confidence_score=0.9)
    out = m.derive([base], lambda b: b, confidence_score=0.5)
    assert out['meta']['confidence_score'] == 0.5

# F3: a child derive owns a copy of its parent's lineage steps, so mutating one
# envelope's history can't rewrite a sibling that shares ancestry.
def test_child_derive_owns_copy_of_parent_lineage_steps():
    base = m.mark(100, source='mock', confidence='low')
    d1 = m.derive([base], lambda b: b)
    d2 = m.derive([d1], lambda b: b)
    assert d2['meta']['lineage'][0] is not d1['meta']['lineage'][0]
    assert d2['meta']['lineage'][0]['id'] == d1['meta']['lineage'][0]['id']
