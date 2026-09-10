"""Tests for baseline.py — Principle 9 library. Mirror of primitives/js/baseline.test.mjs."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import baseline as bl  # noqa: E402


def step(**over):
    s = {'id': 'sha256:000000000000', 'of': 'input', 'source': 'real', 'confidence': 'high',
         'derivedFromMock': False, 'confidenceScore': 0.9}
    s.update(over)
    return s


def meta(**over):
    m = {'provenanceVersion': 2, 'source': 'derived', 'confidence': 'high', 'derivedFromMock': False,
         'confidenceScore': 0.9, 'lineage': [step(), step(id='sha256:111111111111')]}
    m.update(over)
    return m


def record(**over):
    r = {'baseline-format': bl.BASELINE_FORMAT, 'name': 'nightly-rate', 'provenanceVersion': 2,
         'value': 0.0412, 'meta': meta(),
         'history': [{'date': '2026-09-10', 'because': 'initial pin', 'change': 'initial'}]}
    r.update(over)
    return r


def test_canonical_json_sorts_keys_recursively_and_keeps_array_order():
    assert bl.canonical_json({'b': 1, 'a': {'d': [3, {'z': 1, 'y': 2}], 'c': 0}}) == \
        '{\n  "a": {\n    "c": 0,\n    "d": [\n      3,\n      {\n        "y": 2,\n        "z": 1\n      }\n    ]\n  },\n  "b": 1\n}\n'


def test_compact_json_renders_booleans_and_none():
    assert bl.compact_json(True) == 'true'
    assert bl.compact_json(None) == 'null'
    assert bl.compact_json({'b': [1, 'x'], 'a': None}) == '{"a":null,"b":[1,"x"]}'


def test_is_json_value_rejects_what_cannot_round_trip():
    assert bl.is_json_value({'a': [1, 'b', None, True]})
    for bad in (float('nan'), float('inf'), object(), {1, 2}, lambda: 1, b'x'):
        assert not bl.is_json_value(bad)


def test_deep_equal_compares_structure():
    assert bl.deep_equal({'a': [1, {'b': 2}]}, {'a': [1, {'b': 2}]})
    assert not bl.deep_equal({'a': 1}, {'a': 1, 'b': 2})
    assert not bl.deep_equal([1, 2], [2, 1])
    assert bl.deep_equal(1, 1.0)
    assert not bl.deep_equal(True, 1)   # bool is not a number here


def test_name_re_accepts_safe_names_only():
    assert bl.NAME_RE.match('nightly-rate.v2_x')
    for bad in ('../x', 'a b', 'a/b', '', 'é'):
        assert not bl.NAME_RE.match(bad)


def test_wire_conversion_round_trips_envelope_and_steps():
    snake = {'provenance_version': 2, 'source': 'derived', 'confidence': 'high', 'derived_from_mock': False,
             'confidence_score': 0.9, 'weakest_source': 'real',
             'lineage': [{'id': 'x', 'of': 'input', 'source': 'real', 'confidence': 'high',
                          'derived_from_mock': False, 'confidence_score': 0.9}]}
    wire = bl.to_wire(snake)
    assert wire['derivedFromMock'] is False and wire['lineage'][0]['confidenceScore'] == 0.9
    assert 'derived_from_mock' not in wire and 'confidence_score' not in wire['lineage'][0]
    assert bl.from_wire(wire) == snake


def test_compare_identical_yields_no_findings():
    assert bl.compare(record(), meta(), 0.0412, 2) == []


def test_compare_names_a_moved_step_field_by_position():
    m = meta(lineage=[step(), step(id='sha256:222222222222', source='fallback')])
    assert bl.compare(record(), m, 0.0412, 2) == [
        {'path': 'meta.lineage[1].source', 'before': 'real', 'after': 'fallback',
         'text': 'meta.lineage[1].source: "real" -> "fallback"'}]


def test_compare_never_diffs_ids():
    m = meta(lineage=[step(id='sha256:aaaaaaaaaaaa'), step(id='sha256:bbbbbbbbbbbb')])
    assert bl.compare(record(), m, 0.0412, 2) == []


def test_compare_lineage_length_changes():
    grew = bl.compare(record(), meta(lineage=[step(), step(), step()]), 0.0412, 2)
    assert grew == [{'path': 'meta.lineage.length', 'before': 2, 'after': 3,
                     'text': 'lineage grew by 1 (first new step: meta.lineage[2])'}]
    shrank = bl.compare(record(), meta(lineage=[step()]), 0.0412, 2)
    assert shrank[0]['text'] == 'lineage shrank by 1 (first missing step: meta.lineage[1])'


def test_compare_top_level_reported_only_when_unexplained():
    m = meta(confidence='medium', lineage=[step(), step(confidence='medium')])
    assert [f['path'] for f in bl.compare(record(), m, 0.0412, 2)] == ['meta.lineage[1].confidence']
    assert bl.compare(record(), meta(confidence='medium'), 0.0412, 2) == [
        {'path': 'meta.confidence', 'before': 'high', 'after': 'medium',
         'text': 'meta.confidence: "high" -> "medium"'}]


def test_compare_value_moved_with_no_input_change():
    assert bl.compare(record(), meta(), 0.05, 2) == [
        {'path': 'value', 'before': 0.0412, 'after': 0.05, 'text': 'value moved with no input change'}]


def test_compare_value_moved_alongside_trust_findings():
    f = bl.compare(record(), meta(confidence='low'), 0.05, 2)
    assert [x['text'] for x in f] == ['meta.confidence: "high" -> "low"',
                                     'value moved; attributed to the findings above']


def test_compare_trust_drift_with_unchanged_value_is_drift():
    assert len(bl.compare(record(), meta(derivedFromMock=True), 0.0412, 2)) == 1


def test_compare_wire_version_mismatch_is_first():
    f = bl.compare(record(provenanceVersion=1), meta(), 0.0412, 2)
    assert f[0] == {'path': 'provenanceVersion', 'before': 1, 'after': 2,
                    'text': 'pinned under wire v1, running v2'}


def test_compare_fixed_order():
    m = meta(confidence='low', derivedFromMock=True, lineage=[step(source='mock', derivedFromMock=True)])
    assert [f['path'] for f in bl.compare(record(provenanceVersion=1), m, 1, 2)] == [
        'provenanceVersion', 'meta.lineage[0].source', 'meta.lineage[0].derivedFromMock',
        'meta.lineage.length', 'meta.confidence', 'value']


def test_summarize():
    assert bl.summarize([{'text': 'a'}, {'text': 'b'}]) == 'a; b'
    assert bl.summarize([]) == 'none'
