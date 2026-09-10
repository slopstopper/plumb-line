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
    import re
    for c in CASES['canonical']:
        text = bl.canonical_json(c['input'])
        assert json.loads(text) == json.loads(c['expect']), c['name']
        if not re.search(r'\d\.\d', c['expect']):
            assert text == c['expect'], c['name']
