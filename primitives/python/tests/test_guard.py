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
