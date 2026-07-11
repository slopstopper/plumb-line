"""test_bundle_conformance — runs the shared cases.json against the
plugin-BUNDLED copy of the Python primitive (.claude-plugin/bundled/primitives/python),
proving the vendored runtime behaves identically to the published package.

Mirrors primitives/python/tests/test_conformance.py, but loads the bundled
modules (not primitives/python/) and resolves cases.json by an explicit
repo-root-relative path rather than directory traversal, since the bundle
lives at a different depth than primitives/python/tests/.

Invoked directly by scripts/check-bundle-conformance.mjs, and can also be run
on its own:

    python3 -m pytest -q scripts/test_bundle_conformance.py
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUNDLE = os.path.join(_ROOT, '.claude-plugin', 'bundled', 'primitives', 'python')
_CASES = os.path.join(_ROOT, 'primitives', 'conformance', 'cases.json')

sys.path.insert(0, _BUNDLE)
import provenance as p
from audit import audit_meta, validate_envelope

with open(_CASES) as f:
    CASES = json.load(f)

# camelCase (JSON) -> snake_case (Python envelope) for the keys that differ.
_KEY = {
    'confidenceScore': 'confidence_score',
    'derivedFromMock': 'derived_from_mock',
    'weakestSource': 'weakest_source',
    'provenanceVersion': 'provenance_version',
}


def _to_snake(d):
    return {_KEY.get(k, k): v for k, v in d.items()}


def _lineage_to_snake(lineage):
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


def test_bundle_combine_cases():
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
        if 'expectLineageIds' in c:
            assert [s.get('id') for s in out['lineage']] == c['expectLineageIds'], \
                f"{c['name']}: lineage ids {[s.get('id') for s in out['lineage']]}"


def test_bundle_audit_cases():
    for c in CASES['audit']:
        raw = c['meta']
        meta = _meta_to_snake(raw) if isinstance(raw, dict) else raw
        issues = audit_meta(meta)
        if not c['expectContains']:
            assert issues == [], f"{c['name']}: expected no issues, got {issues}"
        else:
            for needle in c['expectContains']:
                assert any(needle in i for i in issues), f"{c['name']}: '{needle}' not in {issues}"


def test_bundle_validate_cases():
    for c in CASES['validate']:
        raw = c['meta']
        meta = _meta_to_snake(raw) if isinstance(raw, dict) else raw
        issues = validate_envelope(meta)
        if not c['expectContains']:
            assert issues == [], f"{c['name']}: expected no issues, got {issues}"
        else:
            for needle in c['expectContains']:
                assert any(needle in i for i in issues), f"{c['name']}: '{needle}' not in {issues}"
