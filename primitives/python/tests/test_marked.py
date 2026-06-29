import os, sys
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
