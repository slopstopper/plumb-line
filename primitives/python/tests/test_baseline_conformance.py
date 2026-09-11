# primitives/python/tests/test_baseline_conformance.py
"""Runs baseline-cases.json against the Python baseline. Twin of
primitives/js/baseline.conformance.test.mjs; parity is a data contract."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import baseline as bl  # noqa: E402

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
