import os
import sys

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
