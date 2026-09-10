"""Tests for baseline.py — Principle 9 library. Mirror of primitives/js/baseline.test.mjs."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import baseline as bl  # noqa: E402
from marked import mark, derive  # noqa: E402


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


def rate():
    return mark(0.04, source='real', confidence='high', confidence_score=0.9)


def fx():
    return mark(1.03, source='real', confidence='high', confidence_score=0.9)


def out(r=None, f=None):
    return derive([r or rate(), f or fx()], lambda a, b: a * b, basis='pricing.applyFx@v3')


def test_validate_baseline_accepts_a_well_formed_record():
    rec = bl.to_record('nightly-rate', out(), [{'date': '2026-09-10', 'because': 'initial pin', 'change': 'initial'}])
    assert bl.validate_baseline(rec) == []
    assert 'provenanceVersion' not in rec['meta'] and rec['provenanceVersion'] == 2
    assert 'derivedFromMock' in rec['meta'] and 'derived_from_mock' not in rec['meta']


def test_validate_baseline_names_every_defect():
    rec = bl.to_record('nightly-rate', out(), [])
    rec['baseline-format'] = 'v9'
    rec['name'] = 'bad name'
    rec['provenanceVersion'] = '2'
    del rec['meta']['lineage']
    issues = bl.validate_baseline(rec)
    for needle in ('baseline-format', 'name', 'provenanceVersion', 'history', 'lineage'):
        assert any(needle in i for i in issues), needle
    assert bl.validate_baseline(None) == ['not a baseline record']
    bad_hist = bl.to_record('n', out(), [{'date': '10/09/2026', 'because': ' ', 'change': 'initial'}])
    assert len([i for i in bl.validate_baseline(bad_hist) if 'history[0]' in i]) == 2


def test_check_missing_says_how_to_record(tmp_path):
    r = bl.check('nightly-rate', out(), dir=str(tmp_path))
    assert r['status'] == 'missing'
    assert 'update("nightly-rate", <marked>, because="<why this state is correct>", dir=' in bl.report_text(r)
    with pytest.raises(AssertionError, match='missing'):
        bl.assert_baseline('nightly-rate', out(), dir=str(tmp_path))


def test_update_requires_because_and_a_safe_name(tmp_path):
    with pytest.raises(ValueError, match='because'):
        bl.update('nightly-rate', out(), because='  ', dir=str(tmp_path))
    with pytest.raises(ValueError, match='name'):
        bl.update('../escape', out(), because='x', dir=str(tmp_path))
    assert list(tmp_path.iterdir()) == []


def test_update_writes_canonical_json_with_initial_history(tmp_path):
    rec = bl.update('nightly-rate', out(), because='initial pin after the v2 feed', dir=str(tmp_path), date='2026-09-10')
    text = (tmp_path / 'nightly-rate.json').read_text(encoding='utf-8')
    assert text.endswith('\n') and json.loads(text) == rec
    assert rec['history'] == [{'date': '2026-09-10', 'because': 'initial pin after the v2 feed', 'change': 'initial'}]
    assert list(json.loads(text)) == ['baseline-format', 'history', 'meta', 'name', 'provenanceVersion', 'value']


def test_check_matches_then_drifts_with_attribution(tmp_path):
    bl.update('nightly-rate', out(), because='initial', dir=str(tmp_path), date='2026-09-10')
    assert bl.check('nightly-rate', out(), dir=str(tmp_path))['status'] == 'match'
    drifted = out(mark(0.04, source='fallback', confidence='medium', confidence_score=0.5))
    r = bl.check('nightly-rate', drifted, dir=str(tmp_path))
    assert r['status'] == 'drift'
    assert [f['path'] for f in r['findings']] == [
        'meta.lineage[0].source', 'meta.lineage[0].confidence', 'meta.lineage[0].confidenceScore']
    with pytest.raises(AssertionError, match=r'meta\.lineage\[0\]\.source'):
        bl.assert_baseline('nightly-rate', drifted, dir=str(tmp_path))


def test_update_appends_summary_then_none(tmp_path):
    bl.update('nightly-rate', out(), because='initial', dir=str(tmp_path), date='2026-09-10')
    drifted = out(mark(0.04, source='fallback', confidence='medium', confidence_score=0.5))
    rec = bl.update('nightly-rate', drifted, because='feed lost its cache header', dir=str(tmp_path), date='2026-09-14')
    assert len(rec['history']) == 2
    assert rec['history'][1]['change'].startswith('meta.lineage[0].source: "real" -> "fallback"; ')
    again = bl.update('nightly-rate', drifted, because='re-pinned after review', dir=str(tmp_path), date='2026-09-15')
    assert again['history'][2]['change'] == 'none'


def test_invalid_file_is_invalid_never_missing(tmp_path):
    (tmp_path / 'broken.json').write_text('{ not json', encoding='utf-8')
    assert bl.check('broken', out(), dir=str(tmp_path))['status'] == 'invalid'
    (tmp_path / 'hollow.json').write_text('{"baseline-format": "v1"}', encoding='utf-8')
    r = bl.check('hollow', out(), dir=str(tmp_path))
    assert r['status'] == 'invalid' and 'missing required key' in bl.report_text(r)
    with pytest.raises(ValueError, match='invalid baseline'):
        bl.update('hollow', out(), because='x', dir=str(tmp_path))
    assert (tmp_path / 'hollow.json').read_text(encoding='utf-8') == '{"baseline-format": "v1"}'


def test_invalid_envelope_is_refused(tmp_path):
    bogus = {'value': 1, 'meta': {'source': 'real'}}
    assert bl.check('nightly-rate', bogus, dir=str(tmp_path))['status'] == 'invalid-envelope'
    with pytest.raises(ValueError, match='envelope'):
        bl.update('nightly-rate', bogus, because='x', dir=str(tmp_path))


def test_update_refuses_a_non_json_value(tmp_path):
    with pytest.raises(ValueError, match='JSON'):
        bl.update('fn', mark(object(), source='real'), because='x', dir=str(tmp_path))


def test_list_and_show(tmp_path):
    bl.update('b', out(), because='x', dir=str(tmp_path), date='2026-09-10')
    bl.update('a', out(), because='x', dir=str(tmp_path), date='2026-09-10')
    assert bl.list_baselines(dir=str(tmp_path)) == ['a', 'b']
    assert bl.list_baselines(dir=str(tmp_path / 'absent')) == []
    assert bl.show('a', dir=str(tmp_path))['name'] == 'a'
    with pytest.raises(LookupError, match='no baseline named nope'):
        bl.show('nope', dir=str(tmp_path))


def test_default_dir_is_under_the_working_directory():
    r = bl.check('x', out())
    assert os.path.join('.plumb-line', 'baselines') in bl.report_text(r)
