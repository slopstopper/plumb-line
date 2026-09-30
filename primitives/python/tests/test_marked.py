import os
import sys

import pytest
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


# #443: mark and a derive override build on make_meta, so they refuse an
# off-ladder rung or source too. JS twin: the #443 tests in marked.test.mjs.
def test_mark_refuses_a_numeric_confidence():
    import pytest
    with pytest.raises(ValueError, match=r"^confidence must be one of none, low, medium, high; got 0$"):
        m.mark(1, source='mock', confidence=0)


def test_mark_refuses_a_source_outside_status():
    import pytest
    with pytest.raises(ValueError, match=r"^source must be one of unavailable, mock"):
        m.mark(1, source='bogus')


def test_mark_refuses_a_missing_source():
    # #177: a leaf has no parents, so "derived" was never true of it.
    import pytest
    with pytest.raises(ValueError, match=r"^source is required \(one of unavailable, mock"):
        m.mark(1)
    with pytest.raises(ValueError, match=r"^source is required"):
        m.mark(1, confidence='high')


@pytest.mark.parametrize('key', ['confidence_score', 'basis', 'adapter'])
def test_a_none_override_on_derive_is_no_override(key):
    """#566: None is no override for the optional keys, as null is in the JS
    twin (primitives/js/marked.test.mjs): the combined score stands."""
    a = m.mark(1, source='real', confidence='high', confidence_score=0.9)
    b = m.mark(2, source='fallback', confidence='medium', confidence_score=0.6)
    plain = m.derive([a, b], lambda x, y: x + y)
    out = m.derive([a, b], lambda x, y: x + y, **{key: None})
    assert out == plain
    assert list(out['meta']) == list(plain['meta'])
    assert out['meta']['confidence_score'] == 0.6


@pytest.mark.parametrize('key', ['source', 'confidence'])
def test_a_none_source_or_confidence_override_is_still_refused(key):
    """#443: None is a value there, off the ladder; #566 changes only the
    optional keys."""
    a = m.mark(1, source='real', confidence='high')
    with pytest.raises(ValueError, match=f'^{key} must be one of'):
        m.derive([a], lambda x: x, **{key: None})


def test_a_derive_override_is_refused_the_same_way():
    import pytest
    a = m.mark(1, source='real', confidence='high')
    with pytest.raises(ValueError, match=r"^confidence must be one of none, low, medium, high; got 0\.8$"):
        m.derive([a], lambda x: x, confidence=0.8)


def test_derive_override_refuses_a_derived_from_mock_that_is_not_a_boolean():
    """#555 (reversing #525): a malformed override is refused, not read as
    taint or as clean, as the JS twin refuses it. True still taints; False
    and None cannot clear taint and leave a clean input clean."""
    import pytest
    clean = m.mark(1, source='real', confidence='high')
    for flag in ([], {}, 0, '', 'false', 'true'):
        with pytest.raises(ValueError, match='derivedFromMock must be a boolean'):
            m.derive([clean], lambda v: v, derived_from_mock=flag)
    # Values json.dumps cannot write are refused with the same message
    # (make_meta's own quoting), not a serialization error (#555 review).
    cycle = []
    cycle.append(cycle)
    for flag in (object(), {1, 2}, b'x', cycle, float('nan')):
        with pytest.raises(ValueError, match='derivedFromMock must be a boolean'):
            m.derive([clean], lambda v: v, derived_from_mock=flag)
    assert m.derive([clean], lambda v: v, derived_from_mock=True)['meta']['derived_from_mock'] is True
    for flag in (False, None):
        assert m.derive([clean], lambda v: v, derived_from_mock=flag)['meta']['derived_from_mock'] is False



class _Box:
    value = 1


def test_derive_refuses_an_input_that_is_not_a_marked_value_before_calling_fn():
    """#550: a marked value as the guard reads one, a dict holding 'value'
    and 'meta'. Python used to raise an unrelated KeyError or TypeError; JS
    combined an unmarked object or null as an unknown input."""
    import pytest
    clean = m.mark(1, source='real', confidence='high')
    for bad in ({'a': 1}, None, 3, [1], _Box(), {'value': 1}):
        called = []
        with pytest.raises(TypeError, match=r'^derive: input 1 is not a marked value \(mark it first\)$'):
            m.derive([clean, bad], lambda *a: called.append(1))
        assert called == [], bad


def test_derive_still_accepts_a_handed_marked_value_with_an_empty_envelope():
    assert m.derive([m.mark(1, source='real', confidence='high')], lambda v: v + 1)['value'] == 2
    assert m.derive([{'value': 2, 'meta': {}}], lambda v: v)['meta']['lineage'][0]['source'] is None


def test_derive_reads_a_generator_once_and_keeps_its_taint():
    """#550 review: the check used the generator up, and it was combined as
    zero inputs, dropping its taint (the guard then let a mock value out)."""
    mock = m.mark(41, source='mock', confidence='low')
    out = m.derive((x for x in [mock]), lambda v: v + 1)
    assert out['value'] == 42
    assert out['meta']['derived_from_mock'] is True
    assert out['meta']['source'] == 'derived'


def test_derive_refuses_inputs_that_are_not_a_list():
    import pytest
    clean = m.mark(1, source='real', confidence='high')
    for inputs in (3, None, 'ab', {'a': clean}):
        with pytest.raises(TypeError, match=r'^derive: inputs must be a list of marked values$'):
            m.derive(inputs, lambda *a: 0)
