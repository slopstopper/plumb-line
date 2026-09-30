"""test_bundle_conformance — runs the shared cases.json against the
plugin-BUNDLED copy of the Python primitive (.claude-plugin/bundled/primitives/python),
proving the vendored runtime behaves identically to the published package.

Mirrors primitives/python/tests/test_conformance.py, but loads the bundled
modules (not primitives/python/) and resolves cases.json by an explicit
repo-root-relative path rather than directory traversal, since the bundle
lives at a different depth than primitives/python/tests/.

The JS bundle's twin is scripts/check-bundle-conformance.mjs; CI runs each in
its own job. Run this one with:

    python3 -m pytest -q scripts/test_bundle_conformance.py

IMPORTANT: run this in its own pytest process, never in the same session as
primitives/python/tests/test_conformance.py — both import a module named
`provenance` from different paths, and Python's sys.modules cache would serve
whichever one imported first to the other, silently testing the wrong copy.
"""
import json
import os
import sys

# Prepend the plugin-bundled primitive to sys.path BEFORE importing it, inlined
# so no assignment precedes the import (mirrors primitives/python/tests/
# test_conformance.py and keeps ruff's E402 satisfied). See the module docstring
# on why this must run in its own pytest process.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '.claude-plugin', 'bundled', 'primitives', 'python'))
import provenance as p
import marked as m
from audit import audit_meta, validate_envelope
from guard import guard, ProvenanceRefused

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CASES = os.path.join(_ROOT, 'primitives', 'conformance', 'cases.json')

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
    # An input that is not an envelope passes through verbatim, so combine
    # itself meets it (#525).
    if not isinstance(meta, dict):
        return meta
    out = _to_snake(meta)
    if 'lineage' in out:
        out['lineage'] = _lineage_to_snake(out['lineage'])
    return out


_CAMEL = {v: k for k, v in _KEY.items()}


def _step_to_camel(step):
    return {_CAMEL.get(k, k): v for k, v in step.items()} if isinstance(step, dict) else step


def _step_id(step):
    """A prior step that is not a dict has no id: None, as in the JS runner."""
    return step.get('id') if isinstance(step, dict) else None


def _strict(a, b):
    """== with JSON's types kept apart: True is not 1 (Python's == says it
    is), as JS isDeepStrictEqual keeps them apart. 1 and 1.0 are one number."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_strict(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_strict(x, y) for x, y in zip(a, b))
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        return False
    return (type(a) is type(b) or (isinstance(a, (int, float)) and isinstance(b, (int, float)))) and a == b


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
            assert _strict([_step_id(s) for s in out['lineage']], c['expectLineageIds']), \
                f"{c['name']}: lineage ids {[_step_id(s) for s in out['lineage']]}"
        if 'expectLineage' in c:
            got = [_step_to_camel(s) for s in out['lineage']]
            assert _strict(got, c['expectLineage']), f"{c['name']}: lineage {got!r}"


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


def _shape_problem(kind, c):
    """A construct or derive row's shape, as the JS twin's shapeProblem: one
    expectation, and `absent` a list of names beside `expect` only."""
    if ('expect' in c) == ('expectError' in c):
        return f"a {kind} case needs exactly one of expect or expectError"
    if 'absent' in c and not (isinstance(c['absent'], list) and all(isinstance(k, str) for k in c['absent'])):
        return 'absent must be a list of field names'
    if 'absent' in c and 'expect' not in c:
        return 'absent applies only to an expect case'
    if kind == 'derive':
        if not isinstance(c.get('inputs'), list):
            return 'a derive case needs a list of inputs'
        if 'override' in c and not isinstance(c['override'], dict):
            return "a derive case's override must be an object"
    return None


def _envelope_problems(name, out, c):
    for k, v in c['expect'].items():
        sk = _KEY.get(k, k)
        assert out.get(sk) == v, f"{name}: {sk} == {out.get(sk)!r}, expected {v!r}"
    # A field that must not be written at all (#566).
    for k in c.get('absent', []):
        sk = _KEY.get(k, k)
        assert sk not in out, f"{name}: {sk} should be absent"


def test_bundle_construct_cases():
    # Mirrors test_construct_cases in primitives/python/tests/test_conformance.py (#443).
    for c in CASES['construct']:
        problem = _shape_problem('construct', c)
        assert problem is None, f"{c['name']}: {problem}"
        kwargs = _to_snake(c['input'])
        if 'expectError' in c:
            try:
                p.make_meta(**kwargs)
            except ValueError as e:
                assert c['expectError'] in str(e), f"{c['name']}: error {str(e)!r}"
            else:
                raise AssertionError(f"{c['name']}: expected an error containing {c['expectError']!r}")
        else:
            out = p.make_meta(**kwargs)
            _envelope_problems(c['name'], out, c)


def test_bundle_derive_cases():
    # What derive writes for an override (#566): each input is marked with its
    # `inputs` fields, then derive runs a constant function with `override`.
    # JS twin: runDerive in primitives/conformance/run-cases.mjs.
    for c in CASES['derive']:
        problem = _shape_problem('derive', c)
        assert problem is None, f"{c['name']}: {problem}"
        p.reset_step_counter()
        items = [m.mark(i, **_to_snake(fields)) for i, fields in enumerate(c['inputs'])]
        kwargs = _to_snake(c.get('override', {}))
        if 'expectError' in c:
            try:
                m.derive(items, lambda *_: 0, **kwargs)
            except ValueError as e:
                assert c['expectError'] in str(e), f"{c['name']}: error {str(e)!r}"
            else:
                raise AssertionError(f"{c['name']}: expected an error containing {c['expectError']!r}")
        else:
            out = m.derive(items, lambda *_: 0, **kwargs)
            _envelope_problems(c['name'], out['meta'], c)


_GUARD_OPTION = {'noMock': 'no_mock', 'minConfidence': 'min_confidence', 'minSource': 'min_source'}


def test_bundle_guard_cases():
    # The egress guard (#120). JS twin: runGuard in
    # primitives/conformance/run-cases.mjs. A row's `meta` becomes a marked
    # value ({'value', 'meta'}, as mark() builds it); a non-dict `meta` is
    # passed as is, to pin that a value with no envelope is refused.
    for c in CASES['guard']:
        name = c['name']
        expectations = [k for k in ('expectPass', 'expectRefused', 'expectError') if k in c]
        assert len(expectations) == 1, \
            f"{name}: a guard case needs exactly one of expectPass, expectRefused or expectError"
        assert 'expectAbsent' not in c or 'expectRefused' in c, \
            f"{name}: expectAbsent is read only beside expectRefused"
        # As in the JS twin: these would otherwise be read as a pass, or as
        # any refusal at all.
        assert 'expectPass' not in c or c['expectPass'] is True, f"{name}: expectPass must be true"
        for key in ('expectRefused', 'expectAbsent'):
            assert key not in c or (isinstance(c[key], list) and c[key]), \
                f"{name}: {key} must list at least one reason"
        # An empty needle is in every string, so it would pin nothing.
        needles = c.get('expectRefused', []) + c.get('expectAbsent', []) + ([c['expectError']] if 'expectError' in c else [])
        assert all(isinstance(n, str) and n for n in needles), \
            f"{name}: every expected reason or error text must be a non-empty string"
        raw = c['meta']
        x = {'value': 1, 'meta': _meta_to_snake(raw)} if isinstance(raw, dict) else raw
        kwargs = {_GUARD_OPTION.get(k, k): v for k, v in c.get('options', {}).items()}
        try:
            out = guard(x, **kwargs)
        except ProvenanceRefused as e:
            reasons = e.reasons
            assert isinstance(reasons, list) and all(isinstance(r, str) for r in reasons), \
                f"{name}: a refusal must carry reasons as a list of strings, got {reasons!r}"
            assert 'expectRefused' in c, f"{name}: expected {expectations[0]}, got a refusal: {reasons}"
            for needle in c['expectRefused']:
                assert any(needle in r for r in reasons), f"{name}: {needle!r} not in {reasons}"
            for needle in c.get('expectAbsent', []):
                assert not any(needle in r for r in reasons), f"{name}: {needle!r} in {reasons}"
        except (TypeError, ValueError) as e:
            assert 'expectError' in c, f"{name}: expected {expectations[0]}, got an error: {e}"
            # SPEC §5c: never the refusal's type or a supertype of it, so a
            # catch for refusals (a ValueError) cannot swallow a bad option.
            assert not isinstance(e, ValueError), f"{name}: a bad option raised a ValueError: {e}"
            assert c['expectError'] in str(e), f"{name}: error {str(e)!r}"
        else:
            assert 'expectPass' in c, f"{name}: expected {expectations[0]}, got a pass"
            assert out is x, f"{name}: a pass must return the marked value it was given"


# Every case field the tests above interpret; mirrors
# primitives/python/tests/test_conformance.py and run-cases.mjs (#369).
_KNOWN_FIELDS = {
    'combine': {'name', 'inputs', 'expect', 'absent', 'expectLineageIds', 'expectLineage'},
    'audit': {'name', 'meta', 'expectContains'},
    'validate': {'name', 'meta', 'expectContains'},
    'construct': {'name', 'input', 'expect', 'expectError', 'absent'},
    'derive': {'name', 'inputs', 'override', 'expect', 'expectError', 'absent'},
    'guard': {'name', 'meta', 'options', 'expectPass', 'expectRefused', 'expectAbsent', 'expectError'},
}


def test_bundle_every_case_field_is_interpreted():
    for kind, known in _KNOWN_FIELDS.items():
        for c in CASES[kind]:
            extra = set(c) - known
            assert not extra, (f"{kind} case {c['name']!r}: unknown field(s) {sorted(extra)} "
                               f"— teach this runner to interpret them")


def test_bundle_every_case_kind_is_interpreted():
    # A top-level kind no test above reads would otherwise never run (#369).
    kinds = set(CASES) - {'_doc', 'version'}
    assert kinds == set(_KNOWN_FIELDS), f"unknown case kind(s) {sorted(kinds - set(_KNOWN_FIELDS))}"


def _version_is_modelled(version):
    """`True == 1` in Python: a boolean version is refused, as the main
    runners refuse it (#441; #525)."""
    return not isinstance(version, bool) and version in {1}


def test_bundle_case_table_version_is_one_this_runner_models():
    # Mirrors primitives/python/tests/test_conformance.py and run-cases.mjs (#433).
    version = CASES.get("version")
    assert _version_is_modelled(version), f"unknown case-table version {version!r}"


def test_bundle_a_boolean_or_unknown_version_is_refused():
    assert not _version_is_modelled(True)
    assert not _version_is_modelled(2)
    assert _version_is_modelled(1) and _version_is_modelled(1.0)
