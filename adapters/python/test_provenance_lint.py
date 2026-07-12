import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provenance_lint as pl

IMPORT = "from plumb_line_provenance import mark, derive, make_meta, unwrap\n"


def rules(src):
    return [i['rule'] for i in pl.check(IMPORT + src)]


# --- valid (must stay silent) ---

def test_clean_derive_is_silent():
    assert rules("t = derive([a, b], lambda x, y: x + y)") == []

def test_honest_mark_is_silent():
    assert rules("m = mark(1000, source='real', confidence='high')") == []

def test_mock_mark_is_silent():
    assert rules("m = mark(2, source='mock', confidence='low')") == []

def test_taint_true_on_non_clean_source_is_silent():
    assert rules("m = mark(2, source='mock', derived_from_mock=True)") == []

def test_non_clean_source_override_is_silent():
    assert rules("t = derive([a], lambda x: x, confidence='low')") == []

def test_dynamic_values_are_silent():
    assert rules("m = mark(1, source=src, derived_from_mock=flag)") == []

def test_non_primitive_mark_is_silent():
    src = "from myutils import mark\nm = mark(x['value'], source='real', derived_from_mock=True)"
    assert pl.check(src) == []

def test_derived_from_mock_false_on_mark_is_silent():
    # The honest stored default on a fresh mark — PB2 is derive-only, not mark.
    assert rules("m = mark(1000, source='real', derived_from_mock=False)") == []

def test_remark_of_subscript_is_silent():
    # x['value'] can't be proven a marked value without dataflow → not PB4.
    assert rules("m = mark(other['value'], source='real', confidence='high')") == []

def test_remark_of_attribute_is_silent():
    assert rules("m = mark(other.value, source='real', confidence='high')") == []


# --- invalid (must fire) ---

def test_pb1_laundered_meta():
    assert rules("m = mark(42, source='real', derived_from_mock=True)") == ['PB1']

def test_pb1_via_make_meta():
    assert rules("meta = make_meta(source='fallback', derived_from_mock=True)") == ['PB1']

def test_pb2_on_derive_override():
    assert rules("t = derive([a], lambda x: x, derived_from_mock=False)") == ['PB2']

def test_pb3_clean_source_override_on_derive():
    assert rules("t = derive([a, b], lambda x, y: x + y, source='real')") == ['PB3']

def test_pb4_remark_of_unwrap():
    assert rules("m = mark(unwrap(other), confidence='high')") == ['PB4']


# --- import forms ---

def test_aliased_import_resolves():
    src = "from plumb_line_provenance import mark as mk\nm = mk(1, source='semiReal', derived_from_mock=True)"
    assert [i['rule'] for i in pl.check(src)] == ['PB1']

def test_namespace_import_resolves():
    src = "import plumb_line_provenance as p\nt = p.derive([a], lambda x: x, source='real')"
    assert [i['rule'] for i in pl.check(src)] == ['PB3']

def test_from_marked_module_resolves():
    src = "from marked import mark, derive\nt = derive([a], lambda x: x, source='real')"
    assert [i['rule'] for i in pl.check(src)] == ['PB3']


# --- combined + message shape ---

def test_pb1_and_pb4_both_fire():
    assert rules("m = mark(unwrap(other), source='real', derived_from_mock=True)") == ['PB1', 'PB4']

def test_message_cites_source_and_line():
    issues = pl.check(IMPORT + "m = mark(42, source='real', derived_from_mock=True)")
    assert issues[0]['line'] == 2
    assert "'real'" in issues[0]['message']

def test_syntax_error_is_reported_not_raised():
    issues = pl.check("def (:\n")
    assert issues and issues[0]['rule'] == 'parse'


# --- injection path (D7 / GH #29): extra_modules + extra_tracked ---
# Both are ADDITIVE — built-in coverage can never be configured away.

WRAPPER_PB1 = "from myorg_data import mark\nm = mark(1, source='real', derived_from_mock=True)"

def test_wrapper_module_unseen_by_default():
    # Under-claim by default: an unconfigured wrapper module stays out of scope.
    assert pl.check(WRAPPER_PB1) == []

def test_extra_modules_extends_coverage_to_wrapper():
    issues = pl.check(WRAPPER_PB1, extra_modules={'myorg_data'})
    assert [i['rule'] for i in issues] == ['PB1']

def test_extra_modules_keeps_builtin_coverage():
    src = IMPORT + "m = mark(42, source='real', derived_from_mock=True)"
    assert [i['rule'] for i in pl.check(src, extra_modules={'myorg_data'})] == ['PB1']

def test_extra_modules_leaves_honest_wrapper_usage_silent():
    src = "from myorg_data import mark\nm = mark(2, source='mock', confidence='low')"
    assert pl.check(src, extra_modules={'myorg_data'}) == []

def test_extra_tracked_maps_renamed_wrapper_to_role():
    src = "from myorg_data import mark_value\nm = mark_value(1, source='real', derived_from_mock=True)"
    issues = pl.check(src, extra_modules={'myorg_data'}, extra_tracked={'mark_value': 'mark'})
    assert [i['rule'] for i in issues] == ['PB1']

def test_extra_tracked_namespace_form():
    src = "import myorg_data as d\nt = d.derive_all([a], lambda x: x, source='real')"
    issues = pl.check(src, extra_modules={'myorg_data'}, extra_tracked={'derive_all': 'derive'})
    assert [i['rule'] for i in issues] == ['PB3']

def test_extra_module_matches_on_normalized_basename():
    # #138 — basename + separator normalization; config "myorg-data" covers
    # a dotted path with underscores.
    src = ("from pkg.myorg_data import mark\n"
           "m = mark(42, source='real', derived_from_mock=True)")
    issues = pl.check(src, extra_modules={'myorg-data'})
    assert [i['rule'] for i in issues] == ['PB1']

def test_normalize_module_name_folds_separators_and_ext():
    assert pl._normalize_module_name('pkg.myorg_data') == 'myorg-data'
    assert pl._normalize_module_name('myorg-data') == 'myorg-data'

def test_extra_tracked_unknown_role_fails_loud():
    # A typo'd role would otherwise mean silently-missing coverage — the exact
    # failure mode this injection path exists to prevent. Fail loud instead.
    with pytest.raises(ValueError):
        pl.check("x = 1", extra_tracked={'mark_value': 'markk'})

# --- #91 check_outputs (declared-surface opt-out) ---

def out_rules(src):
    return [i['rule'] for i in pl.check_outputs(IMPORT + src)]

def test_direct_raw_return_is_flagged():
    assert out_rules("def f(x, r):\n    return x * r") == ['REQ-OUTPUT']

def test_raw_via_local_is_flagged():
    assert out_rules("def f(x, r):\n    t = x * r\n    return t") == ['REQ-OUTPUT']

def test_return_derive_is_silent():
    assert out_rules("def f(x, r):\n    return derive([x, r], lambda p, q: p * q)") == []

def test_return_local_derive_is_silent():
    assert out_rules("def f(x, r):\n    t = derive([x, r], lambda p, q: p * q)\n    return t") == []

def test_return_param_is_silent():
    assert out_rules("def f(marked):\n    return marked") == []

def test_return_unknown_call_is_silent():
    assert out_rules("def f(x):\n    return compute(x)") == []

def test_return_attribute_is_silent():
    assert out_rules("def f(o):\n    return o.total") == []

def test_return_constant_is_silent():
    assert out_rules("def f():\n    return 0") == []

def test_underscore_function_is_out_of_scope():
    assert out_rules("def _helper(x, r):\n    return x * r") == []

def test_nested_transform_lambda_not_flagged():
    # the lambda returns raw p*q by design; only module-level defs are checked
    assert out_rules("def f(x, r):\n    return derive([x, r], lambda p, q: p * q)") == []

def test_reassigned_local_is_silent():
    # a local reassigned more than once cannot be classified → silent (zero-FP)
    assert out_rules("def f(x, r):\n    t = derive([x, r], g)\n    t = x * r\n    return t") == []

def test_multi_return_early_tagged_is_not_flagged():
    # early return of a still-tagged local must NOT be flagged (flow-insensitivity trap)
    src = ("def f(x, r):\n"
           "    t = derive([x, r], g)\n"
           "    if x > 0:\n"
           "        return t\n"
           "    t = x * r\n"
           "    return t")
    assert out_rules(src) == []
