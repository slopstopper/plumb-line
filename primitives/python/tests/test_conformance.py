"""test_conformance — runs the shared cases.json against the Python primitive.

Its JS twin (primitives/js/conformance.test.mjs) runs the SAME file; together
they make JS/Python parity a data contract, not a prose promise. The JSON uses
camelCase (the canonical envelope shape); we translate to snake_case here.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import provenance as p
from audit import audit_meta, validate_envelope

_CASES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'conformance', 'cases.json')
with open(_CASES) as f:
    CASES = json.load(f)

# camelCase (JSON) -> snake_case (Python envelope) for the keys that differ.
_KEY = {
    'confidenceScore': 'confidence_score',
    'derivedFromMock': 'derived_from_mock',
    'weakestSource': 'weakest_source',
}


def _to_snake(d):
    return {_KEY.get(k, k): v for k, v in d.items()}


def _lineage_to_snake(lineage):
    # Malformed lineage (not a list, or steps that aren't dicts) passes through
    # verbatim — the validate cases feed deliberately wrong shapes, and the
    # checkers tolerate them, so the translation shim must too.
    if not isinstance(lineage, list):
        return lineage
    return [_to_snake(step) if isinstance(step, dict) else step for step in lineage]


def _meta_to_snake(meta):
    out = _to_snake(meta)
    if 'lineage' in out:
        out['lineage'] = _lineage_to_snake(out['lineage'])
    return out


def setup_function():
    p.reset_step_counter()


def test_combine_cases():
    for c in CASES['combine']:
        p.reset_step_counter()
        inputs = [_meta_to_snake(m) for m in c['inputs']]
        out = p.combine_provenance(*inputs)
        for k, v in c['expect'].items():
            sk = _KEY.get(k, k)
            assert out.get(sk) == v, f"{c['name']}: {sk} == {out.get(sk)!r}, expected {v!r}"
        for k in c.get('absent', []):
            sk = _KEY.get(k, k)
            assert sk not in out, f"{c['name']}: {sk} should be absent"


def test_audit_cases():
    for c in CASES['audit']:
        raw = c['meta']
        meta = None if raw is None else _meta_to_snake(raw)
        issues = audit_meta(meta)
        if not c['expectContains']:
            assert issues == [], f"{c['name']}: expected no issues, got {issues}"
        else:
            for needle in c['expectContains']:
                assert any(needle in i for i in issues), f"{c['name']}: '{needle}' not in {issues}"


def test_validate_cases():
    for c in CASES['validate']:
        raw = c['meta']
        # Only dict envelopes get snake-cased; null and non-object metas pass
        # through verbatim so the checker can exercise its totality guards.
        meta = _meta_to_snake(raw) if isinstance(raw, dict) else raw
        issues = validate_envelope(meta)
        if not c['expectContains']:
            assert issues == [], f"{c['name']}: expected no issues, got {issues}"
        else:
            for needle in c['expectContains']:
                assert any(needle in i for i in issues), f"{c['name']}: '{needle}' not in {issues}"
