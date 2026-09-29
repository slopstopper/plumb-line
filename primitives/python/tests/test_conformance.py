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
from guard import guard, ProvenanceRefused

_CASES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'conformance', 'cases.json')
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
        if 'expectLineageIds' in c:
            assert [s.get('id') for s in out['lineage']] == c['expectLineageIds'], \
                f"{c['name']}: lineage ids {[s.get('id') for s in out['lineage']]}"


def test_audit_cases():
    for c in CASES['audit']:
        raw = c['meta']
        # Only dict envelopes get snake-cased; None and non-dict scalars pass
        # through so audit_meta itself is exercised on them (mirrors validate).
        meta = _meta_to_snake(raw) if isinstance(raw, dict) else raw
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


def test_construct_cases():
    # What make_meta accepts and refuses (#443). A refusal raises; the case
    # pins a substring of the message, whose prefix both languages word identically.
    # JS twin: runConstruct in primitives/conformance/run-cases.mjs.
    for c in CASES['construct']:
        assert ('expect' in c) != ('expectError' in c), \
            f"{c['name']}: a construct case needs exactly one of expect or expectError"
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
            for k, v in c['expect'].items():
                sk = _KEY.get(k, k)
                assert out.get(sk) == v, f"{c['name']}: {sk} == {out.get(sk)!r}, expected {v!r}"


_GUARD_OPTION = {'noMock': 'no_mock', 'minConfidence': 'min_confidence'}


def test_guard_cases():
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


# Every case field the tests above interpret. A field added to cases.json
# that this runner does not read would otherwise pass silently; the JS twin is
# KNOWN_FIELDS in primitives/conformance/run-cases.mjs (#369).
_KNOWN_FIELDS = {
    'combine': {'name', 'inputs', 'expect', 'absent', 'expectLineageIds'},
    'audit': {'name', 'meta', 'expectContains'},
    'validate': {'name', 'meta', 'expectContains'},
    'construct': {'name', 'input', 'expect', 'expectError'},
    'guard': {'name', 'meta', 'options', 'expectPass', 'expectRefused', 'expectAbsent', 'expectError'},
}


def test_every_case_field_is_interpreted():
    for kind, known in _KNOWN_FIELDS.items():
        for c in CASES[kind]:
            extra = set(c) - known
            assert not extra, (f"{kind} case {c['name']!r}: unknown field(s) {sorted(extra)} "
                               f"— teach this runner to interpret them")


def test_every_case_kind_is_interpreted():
    # A top-level kind no test above reads would otherwise never run (#369).
    kinds = set(CASES) - {'_doc', 'version'}
    assert kinds == set(_KNOWN_FIELDS), f"unknown case kind(s) {sorted(kinds - set(_KNOWN_FIELDS))}"


def _is_modelled_version(v):
    # `True == 1` in Python, so a bare `in {1}` would read "version": true as
    # version 1, which the JS twin's Set.has rejects (#441 review).
    return not isinstance(v, bool) and v in {1}


def test_case_table_version_is_one_this_runner_models():
    # A table at another version must fail here, not be read as v1 (#433);
    # the JS twin is KNOWN_TABLE_VERSIONS in run-cases.mjs.
    assert _is_modelled_version(CASES.get("version")), f"unknown case-table version {CASES.get('version')!r}"


def test_a_boolean_version_is_not_version_one():
    assert not _is_modelled_version(True)
    assert _is_modelled_version(1)
