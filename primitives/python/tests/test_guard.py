"""test_guard — the egress guard (#120).

The predicates are pinned for both languages by the `guard` kind in
../../conformance/cases.json; this file covers what a case row cannot express:
the exports, the error classes, the message, and the guard on values built by
mark() and derive(). JS twin: primitives/js/guard.test.mjs.
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guard import guard, ProvenanceRefused
from marked import mark, derive, unwrap


def test_returns_the_marked_value_it_was_given():
    price = mark(99.99, source='real', confidence='high')
    assert guard(price) is price
    assert unwrap(guard(price, min_confidence='high')) == 99.99


def test_refuses_a_value_derived_from_mock_by_default_and_passes_it_when_no_mock_is_off():
    rate = mark(1.17, source='mock', confidence='low')
    amount = derive([mark(100, source='real', confidence='high'), rate], lambda a, r: a * r)
    with pytest.raises(ProvenanceRefused) as e:
        guard(amount)
    assert any(r.startswith('mock:') for r in e.value.reasons)
    assert guard(amount, no_mock=False) is amount


def test_is_a_value_error_whose_message_starts_the_same_in_both_languages():
    with pytest.raises(ProvenanceRefused) as e:
        guard(mark(1, source='mock', confidence='low'), min_confidence='high')
    assert isinstance(e.value, ValueError)
    assert str(e.value).startswith('provenance refused: ')
    assert len(e.value.reasons) == 2
    for r in e.value.reasons:
        assert r in str(e.value)


@pytest.mark.parametrize('x', [42, 'text', None, [], {'value': 1}, {'value': 1, 'meta': 'x'}, {'meta': {}}])
def test_refuses_a_value_that_is_not_marked(x):
    with pytest.raises(ProvenanceRefused):
        guard(x)


@pytest.mark.parametrize('kwargs', [{'min_confidence': 'hi'}, {'min_confidence': 2}, {'no_mock': 'yes'},
                                    {'no_mock': 1}, {'min_confidence': None}, {'min_confidence': True},
                                    {'nomock': False}, {'noMock': False}])
def test_a_bad_option_is_a_type_error_never_a_value_error(kwargs):
    # A ValueError catch written for refusals must not swallow a bad option,
    # nor a bad-option catch swallow a refusal: the two types do not overlap.
    with pytest.raises(TypeError) as e:
        guard(42, **kwargs)
    assert not isinstance(e.value, ValueError)
    assert str(e.value).startswith('guard: ')


def test_an_unknown_option_names_itself():
    with pytest.raises(TypeError, match='guard: unknown option nomock'):
        guard(mark(1, source='real'), nomock=False)


def test_an_order_preserving_parsed_envelope_passes_as_in_js():
    # json.loads(s, object_pairs_hook=OrderedDict) builds dict subclasses, the
    # Python twin of JS's null-prototype parse, which JS's guard accepts.
    import json
    from collections import OrderedDict
    marked = json.loads(json.dumps(mark(1, source='real', confidence='high')), object_pairs_hook=OrderedDict)
    assert guard(marked) is marked


def test_the_package_exports_guard():
    # Load the directory as the package under its published name, in a
    # subprocess so this session's sys.modules stays clean (the technique of
    # test_http_module_name.py).
    py_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = subprocess.run([sys.executable, '-c', (
        'import importlib.util, os, sys\n'
        'spec = importlib.util.spec_from_file_location("plumb_line_provenance", "__init__.py",'
        ' submodule_search_locations=[os.getcwd()])\n'
        'pkg = importlib.util.module_from_spec(spec); sys.modules["plumb_line_provenance"] = pkg\n'
        'spec.loader.exec_module(pkg)\n'
        'from plumb_line_provenance import guard, ProvenanceRefused\n'
        'assert "guard" in pkg.__all__ and "ProvenanceRefused" in pkg.__all__\n'
        'assert issubclass(ProvenanceRefused, ValueError)\n'
        'print("ok")\n')], cwd=py_dir, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == 'ok'


def test_a_dict_subclass_step_is_judged_on_what_it_holds_not_what_it_answers():
    # A step whose accessors hide its taint: judged on a plain copy of its
    # contents, as JS judges a plain object and refuses anything else.
    class Sneaky(dict):
        def get(self, key, default=None):
            return default if key in ('source', 'derived_from_mock') else super().get(key, default)

        def __getitem__(self, key):
            if key in ('source', 'derived_from_mock'):
                raise KeyError(key)
            return super().__getitem__(key)

        def __contains__(self, key):
            return key not in ('source', 'derived_from_mock') and super().__contains__(key)

    step = Sneaky(id='s1', of='input', source='mock', confidence='high', derived_from_mock=True)
    x = {'value': 1, 'meta': {'provenance_version': 2, 'source': 'derived', 'confidence': 'high',
                              'derived_from_mock': False, 'lineage': [step]}}
    with pytest.raises(ProvenanceRefused) as e:
        guard(x)
    assert any(r.startswith('mock:') for r in e.value.reasons)


def test_a_dict_subclass_that_hides_fields_from_iteration_is_still_judged_on_them():
    hidden = ('source', 'derived_from_mock')

    class IterHide(dict):
        def __iter__(self):
            return (k for k in dict.__iter__(self) if k not in hidden)

        def keys(self):
            return [k for k in dict.keys(self) if k not in hidden]

        def get(self, key, default=None):
            return default if key in hidden else dict.get(self, key, default)

        def __getitem__(self, key):
            if key in hidden:
                raise KeyError(key)
            return dict.__getitem__(self, key)

        def __contains__(self, key):
            return key not in hidden and dict.__contains__(self, key)

    step = IterHide(id='s1', of='input', source='mock', confidence='high', derived_from_mock=True)
    x = {'value': 1, 'meta': {'provenance_version': 2, 'source': 'derived', 'confidence': 'high',
                              'derived_from_mock': False, 'lineage': [step]}}
    with pytest.raises(ProvenanceRefused) as e:
        guard(x)
    assert any(r.startswith('mock:') for r in e.value.reasons)


def test_a_step_whose_iteration_raises_is_judged_on_its_contents_not_raised():
    class Raising(dict):
        def __iter__(self):
            raise RuntimeError('no iteration')

        def keys(self):
            raise RuntimeError('no keys')

    step = Raising(id='s1', of='input', source='real', confidence='high', derived_from_mock=False)
    x = {'value': 1, 'meta': {'provenance_version': 2, 'source': 'derived', 'confidence': 'high',
                              'derived_from_mock': False, 'lineage': [step]}}
    assert guard(x) is x


def test_refuses_never_raises_for_a_malformed_value_it_cannot_print():
    class Unprintable:
        def __repr__(self):
            raise RuntimeError('no repr')

    base = mark(1, source='real', confidence='high')
    for field in ('confidence_score', 'weakest_source', 'source'):
        x = {'value': 1, 'meta': dict(base['meta'], **{field: Unprintable()})}
        with pytest.raises(ProvenanceRefused):
            guard(x)
    step = {'id': 's1', 'of': 'input', 'source': 'real', 'confidence': 'high',
            'derived_from_mock': False, 'confidence_score': Unprintable()}
    x = {'value': 1, 'meta': dict(base['meta'], source='derived', lineage=[step])}
    with pytest.raises(ProvenanceRefused):
        guard(x)


def test_guard_refuses_what_combine_makes_of_an_input_with_no_source():
    """#525 review: combine records the missing source as None, and the guard
    refuses it, as before #525; with the key left off, it passed."""
    import provenance as prov
    for handed in ({'confidence': 'high', 'derived_from_mock': False, 'lineage': []}, {}, 'x'):
        meta = prov.combine_provenance(handed)
        with pytest.raises(ProvenanceRefused) as refused:
            guard({'value': 1, 'meta': meta})
        assert any('lineage step 0 source null is not on the source ladder' in r
                   for r in refused.value.reasons), refused.value.reasons
