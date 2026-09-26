# primitives/python/tests/test_baseline_conformance.py
"""Runs baseline-cases.json against the Python baseline. Twin of
primitives/js/baseline.conformance.test.mjs; parity is a data contract."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import baseline as bl  # noqa: E402
from case_table_guards import table_problems  # noqa: E402

_CASES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      'conformance', 'baseline-cases.json')
with open(_CASES, encoding='utf-8') as f:
    CASES = json.load(f)


def test_attribute_cases():
    for c in CASES['attribute']:
        f = bl.compare(c['record'], c['meta'], c['value'], c['runningVersion'])
        assert f == c['expectFindings'], c['name']
        assert bl.summarize(f) == c['expectSummary'], c['name']


def test_canonical_cases():
    # Parsed equality is the contract in every case; byte-exactness is a
    # stronger claim the case table makes explicitly, rather than a runner
    # guessing from the shape of the expected text.
    for c in CASES['canonical']:
        text = bl.canonical_json(c['input'])
        assert json.loads(text) == json.loads(c['expect']), c['name']
        if c.get('expectBytes') is not False:
            assert text == c['expect'], c['name']


def test_validate_cases():
    for c in CASES['validate']:
        issues = bl.validate_baseline(c['record'])
        if not c['expectContains']:
            assert issues == [], c['name']
        for needle in c['expectContains']:
            assert any(needle in i for i in issues), (c['name'], needle, issues)


# Every field, case kind and table version this runner interprets (#441), the
# guards cases.json has had since #369 and #433. Anything else in
# baseline-cases.json fails here instead of being ignored. `_expectBytes` is
# the table's inline note on `expectBytes`, read by people, not runners. JS
# twin: MODEL in primitives/js/baseline.conformance.test.mjs.
_MODEL = {
    'versions': [1],
    'meta': ['_doc', 'version'],
    'fields': {
        'attribute': ['name', 'record', 'meta', 'value', 'runningVersion',
                      'expectFindings', 'expectSummary'],
        'canonical': ['name', 'input', 'expect', 'expectBytes', '_expectBytes'],
        'validate': ['name', 'record', 'expectContains'],
    },
}


def test_the_shipped_table_has_nothing_this_runner_ignores():
    assert table_problems(CASES, _MODEL) == []


def test_a_planted_unknown_field_fails():
    t = copy.deepcopy(CASES)
    t['validate'][0]['surprise'] = 1
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and 'unknown field(s) surprise' in problems[0], problems


def test_a_planted_unknown_kind_fails():
    t = {**copy.deepcopy(CASES), 'drift': []}
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and 'unknown case kind drift' in problems[0], problems


def test_a_planted_unknown_version_fails():
    t = {**copy.deepcopy(CASES), 'version': 2}
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and 'unknown case-table version 2' in problems[0], problems


def test_a_planted_boolean_version_fails():
    # `True == 1` in Python, so a bare membership test would read
    # "version": true as version 1; the JS twin rejects it (#441 review).
    t = {**copy.deepcopy(CASES), 'version': True}
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and 'unknown case-table version true' in problems[0], problems
