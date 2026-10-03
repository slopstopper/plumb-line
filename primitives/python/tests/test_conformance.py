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
import marked as m
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


# A key the output lacks. _strict finds it equal to no value, None included.
_MISSING = object()


def _expect_problem(out, expect):
    """The first `expect` field the output does not hold, or None (#595).
    Compared with _strict, not `==`, which read True as 1, and with a
    sentinel, not `out.get`, which read a missing key as None. On the JSON
    values a case can hold this agrees with the JS twin's isDeepStrictEqual.
    It does not on values JSON cannot carry: NaN is unequal to itself here,
    0 equals -0.0, and a str subclass is unequal to a str."""
    for k, v in expect.items():
        got = out.get(_KEY.get(k, k), _MISSING)
        if not _strict(got, v):
            return f"expected {k}={v!r}, got {'no such field' if got is _MISSING else repr(got)}"
    return None


def setup_function():
    p.reset_step_counter()


def _check_combine_row(c):
    """One combine row; raises AssertionError when the output differs."""
    p.reset_step_counter()
    inputs = [_meta_to_snake(m) for m in c['inputs']]
    out = p.combine_provenance(*inputs)
    problem = _expect_problem(out, c['expect'])
    assert problem is None, f"{c['name']}: {problem}"
    for k in c.get('absent', []):
        sk = _KEY.get(k, k)
        assert sk not in out, f"{c['name']}: {sk} should be absent"
    if 'expectLineageIds' in c:
        assert _strict([_step_id(s) for s in out['lineage']], c['expectLineageIds']), \
            f"{c['name']}: lineage ids {[_step_id(s) for s in out['lineage']]}"
    if 'expectLineage' in c:
        got = [_step_to_camel(s) for s in out['lineage']]
        assert _strict(got, c['expectLineage']), f"{c['name']}: lineage {got!r}"


def test_combine_cases():
    for c in CASES['combine']:
        _check_combine_row(c)


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
    problem = _expect_problem(out, c['expect'])
    assert problem is None, f"{name}: {problem}"
    # A field that must not be written at all (#566).
    for k in c.get('absent', []):
        sk = _KEY.get(k, k)
        assert sk not in out, f"{name}: {sk} should be absent"


_BAD_ROWS = [
    ('construct', {'input': {}, 'expect': {}, 'absent': 'basis'}, 'absent must be a list of field names'),
    ('construct', {'input': {}, 'expect': {}, 'absent': {'basis': 1}}, 'absent must be a list of field names'),
    ('construct', {'input': {}, 'expect': {}, 'absent': ['basis', None]}, 'absent must be a list of field names'),
    ('construct', {'input': {}, 'expectError': 'x', 'absent': ['source']}, 'absent applies only to an expect case'),
    ('construct', {'input': {}}, 'a construct case needs exactly one of expect or expectError'),
    ('construct', {'input': {}, 'expect': {}, 'expectError': 'x'},
     'a construct case needs exactly one of expect or expectError'),
    ('derive', {'inputs': {}, 'expect': {}}, 'a derive case needs a list of inputs'),
    ('derive', {'inputs': [], 'override': None, 'expect': {}}, "a derive case's override must be an object"),
    ('derive', {'inputs': [], 'expect': {}, 'absent': 'basis'}, 'absent must be a list of field names'),
    ('construct', {'input': {}, 'expect': {}, 'absent': ['toString']}, None),
]


def test_the_row_shape_checks_refuse_what_the_js_runner_refuses():
    # #566 review: the same bad rows, the same messages, as the JS runner's
    # meta-tests in primitives/js/conformance-runner.test.mjs.
    for kind, row, expected in _BAD_ROWS:
        assert _shape_problem(kind, row) == expected, (kind, row)


def test_absent_fails_a_field_that_is_written():
    import pytest
    with pytest.raises(AssertionError, match='basis should be absent'):
        _envelope_problems('x', {'basis': 'b'}, {'expect': {}, 'absent': ['basis']})


def _check_construct_row(c, make_meta=p.make_meta):
    """One construct row (#443). A refusal must be a ValueError (SPEC §2): any
    other exception propagates and fails the row. The case pins a substring
    of the message, whose prefix both languages word identically. JS twin:
    runConstruct in primitives/conformance/run-cases.mjs."""
    problem = _shape_problem('construct', c)
    assert problem is None, f"{c['name']}: {problem}"
    kwargs = _to_snake(c['input'])
    if 'expectError' in c:
        try:
            make_meta(**kwargs)
        except ValueError as e:
            assert c['expectError'] in str(e), f"{c['name']}: error {str(e)!r}"
        else:
            raise AssertionError(f"{c['name']}: expected an error containing {c['expectError']!r}")
    else:
        out = make_meta(**kwargs)
        _envelope_problems(c['name'], out, c)


def test_construct_cases():
    for c in CASES['construct']:
        _check_construct_row(c)


def _check_derive_row(c, derive=m.derive):
    """One derive row (#566): each input is marked with its `inputs` fields,
    then derive runs a constant function with `override`. A refusal must be
    a ValueError, as for construct. JS twin: runDerive in run-cases.mjs."""
    problem = _shape_problem('derive', c)
    assert problem is None, f"{c['name']}: {problem}"
    p.reset_step_counter()
    items = [m.mark(i, **_to_snake(fields)) for i, fields in enumerate(c['inputs'])]
    kwargs = _to_snake(c.get('override', {}))
    if 'expectError' in c:
        try:
            derive(items, lambda *_: 0, **kwargs)
        except ValueError as e:
            assert c['expectError'] in str(e), f"{c['name']}: error {str(e)!r}"
        else:
            raise AssertionError(f"{c['name']}: expected an error containing {c['expectError']!r}")
    else:
        out = derive(items, lambda *_: 0, **kwargs)
        _envelope_problems(c['name'], out['meta'], c)


def test_derive_cases():
    for c in CASES['derive']:
        _check_derive_row(c)


_GUARD_OPTION = {'noMock': 'no_mock', 'minConfidence': 'min_confidence', 'minSource': 'min_source'}


def _guard_shape_problem(c):
    """A guard row's shape, as the JS twin's runGuard checks it, with the same
    messages; None when the row can be judged (#595)."""
    expectations = [k for k in ('expectPass', 'expectRefused', 'expectError') if k in c]
    if len(expectations) != 1:
        return 'a guard case needs exactly one of expectPass, expectRefused or expectError'
    if 'expectAbsent' in c and 'expectRefused' not in c:
        return 'expectAbsent is read only beside expectRefused'
    # These would otherwise be read as a pass, or as any refusal at all.
    if 'expectPass' in c and c['expectPass'] is not True:
        return 'expectPass must be true'
    for key in ('expectRefused', 'expectAbsent'):
        if key in c and not (isinstance(c[key], list) and c[key]):
            return f'{key} must list at least one reason'
    # An empty needle is in every string, so it would pin nothing.
    needles = c.get('expectRefused', []) + c.get('expectAbsent', []) + ([c['expectError']] if 'expectError' in c else [])
    if not all(isinstance(n, str) and n for n in needles):
        return 'every expected reason or error text must be a non-empty string'
    return None


def _check_guard_row(c):
    """One guard row (#120). JS twin: runGuard in
    primitives/conformance/run-cases.mjs. A row's `meta` becomes a marked
    value ({'value', 'meta'}, as mark() builds it); a non-dict `meta` is
    passed as is, to pin that a value with no envelope is refused."""
    name = c['name']
    problem = _guard_shape_problem(c)
    assert problem is None, f"{name}: {problem}"
    expectations = [k for k in ('expectPass', 'expectRefused', 'expectError') if k in c]
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


def test_guard_cases():
    for c in CASES['guard']:
        _check_guard_row(c)


# Every case field the tests above interpret. A field added to cases.json
# that this runner does not read would otherwise pass silently; the JS twin is
# KNOWN_FIELDS in primitives/conformance/run-cases.mjs (#369).
_KNOWN_FIELDS = {
    'combine': {'name', 'inputs', 'expect', 'absent', 'expectLineageIds', 'expectLineage'},
    'audit': {'name', 'meta', 'expectContains'},
    'validate': {'name', 'meta', 'expectContains'},
    'construct': {'name', 'input', 'expect', 'expectError', 'absent'},
    'derive': {'name', 'inputs', 'override', 'expect', 'expectError', 'absent'},
    'guard': {'name', 'meta', 'options', 'expectPass', 'expectRefused', 'expectAbsent', 'expectError'},
}


def _unknown_fields(kind, c):
    """The fields of a row this runner does not interpret, named in the row's
    order; or None. JS twin: unknownFields in run-cases.mjs, whose message
    names that file where this one says "this runner"."""
    extra = [k for k in c if k not in _KNOWN_FIELDS[kind]]
    return f"unknown case field(s) {', '.join(extra)}: teach this runner to interpret them" if extra else None


# Top-level keys of cases.json that are metadata, not case kinds.
_META_KEYS = {'_doc', 'version'}


def _kind_problems(cases):
    """What is wrong with a table's kinds, as the JS twin's runCases reports
    it: a modelled kind missing or not a list, then any kind no test reads.
    The last message says "this runner" where JS names run-cases.mjs."""
    problems = []
    for kind in _KNOWN_FIELDS:
        if kind not in cases:
            problems.append(f'case kind {kind} is missing from the table')
        elif not isinstance(cases[kind], list):
            problems.append(f'case kind {kind} is not a list of cases')
    for kind in sorted(set(cases) - _META_KEYS - set(_KNOWN_FIELDS)):
        problems.append(f'unknown case kind {kind}: teach this runner to interpret it')
    return problems


def test_every_case_field_is_interpreted():
    for kind in _KNOWN_FIELDS:
        for c in CASES[kind]:
            problem = _unknown_fields(kind, c)
            assert problem is None, f"{kind} case {c['name']!r}: {problem}"


def test_every_case_kind_is_interpreted():
    # A top-level kind no test above reads would otherwise never run (#369),
    # and a table with a kind deleted must not pass (#443 review).
    assert _kind_problems(CASES) == []


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


# #595: planted bad rows for the checks the JS runner proves in
# primitives/js/conformance-runner.test.mjs and this runner did not.

# `expect` is compared as the JS twin's isDeepStrictEqual compares it: True is
# not 1, and a key the output lacks is not None.
_BAD_EXPECT = [
    ({'derived_from_mock': True}, {'derivedFromMock': 1}),
    ({'confidence_score': 0}, {'confidenceScore': False}),
    ({'lineage': [{'id': 'a', 'n': True}]}, {'lineage': [{'id': 'a', 'n': 1}]}),
    ({}, {'basis': None}),
]


def test_expect_fails_a_bool_against_a_number_and_a_missing_key_against_null():
    for out, expect in _BAD_EXPECT:
        assert _expect_problem(out, expect) is not None, (out, expect)


def test_expect_passes_an_equal_value_and_one_number_written_two_ways():
    assert _expect_problem({'derived_from_mock': True, 'basis': None}, {'derivedFromMock': True, 'basis': None}) is None
    assert _expect_problem({'confidence_score': 1}, {'confidenceScore': 1.0}) is None


def test_a_construct_or_derive_envelope_is_compared_strictly():
    import pytest
    for out, expect in _BAD_EXPECT:
        with pytest.raises(AssertionError):
            _envelope_problems('x', out, {'expect': expect})


# The guard row-shape checks, with the JS runner's messages.
_CLEAN = {'provenanceVersion': 2, 'source': 'real', 'confidence': 'high', 'derivedFromMock': False, 'lineage': []}
_ONE = 'a guard case needs exactly one of expectPass, expectRefused or expectError'
_NEEDLE = 'every expected reason or error text must be a non-empty string'
_BAD_GUARD_ROWS = [
    ({'meta': _CLEAN}, _ONE),
    ({'meta': _CLEAN, 'expectPass': True, 'expectError': 'y'}, _ONE),
    ({'meta': _CLEAN, 'expectRefused': ['mock:'], 'expectError': 'y'}, _ONE),
    ({'meta': _CLEAN, 'expectPass': True, 'expectAbsent': ['mock:']}, 'expectAbsent is read only beside expectRefused'),
    ({'meta': _CLEAN, 'expectPass': False}, 'expectPass must be true'),
    ({'meta': _CLEAN, 'expectPass': 1}, 'expectPass must be true'),
    ({'meta': _CLEAN, 'expectRefused': []}, 'expectRefused must list at least one reason'),
    ({'meta': _CLEAN, 'expectRefused': 'mock:'}, 'expectRefused must list at least one reason'),
    ({'meta': _CLEAN, 'expectRefused': ['mock:'], 'expectAbsent': 'zzz'}, 'expectAbsent must list at least one reason'),
    ({'meta': _CLEAN, 'expectRefused': ['mock:'], 'expectAbsent': []}, 'expectAbsent must list at least one reason'),
    ({'meta': _CLEAN, 'expectRefused': ['']}, _NEEDLE),
    ({'meta': _CLEAN, 'expectRefused': [1]}, _NEEDLE),
    ({'meta': _CLEAN, 'expectRefused': ['mock:'], 'expectAbsent': ['']}, _NEEDLE),
    ({'meta': _CLEAN, 'options': {'minConfidence': 'hi'}, 'expectError': ''}, _NEEDLE),
    ({'meta': _CLEAN, 'expectPass': True}, None),
    ({'meta': _CLEAN, 'expectRefused': ['mock:'], 'expectAbsent': ['low']}, None),
    ({'meta': _CLEAN, 'options': {'minConfidence': 'hi'}, 'expectError': 'guard:'}, None),
]


def test_the_guard_row_shape_checks_refuse_what_the_js_runner_refuses():
    for row, expected in _BAD_GUARD_ROWS:
        assert _guard_shape_problem(row) == expected, row


def test_the_guard_runner_fails_a_badly_shaped_row():
    # Through the row checker the suite runs, not only the helper.
    import pytest
    for row, expected in _BAD_GUARD_ROWS:
        if expected is not None:
            with pytest.raises(AssertionError, match=expected):
                _check_guard_row({'name': 'x', **row})


def test_the_row_runners_compare_expect_strictly():
    # Through the row checkers the suite runs: a bool against a number, and
    # null against a field that is not written, must fail the row.
    import pytest
    row = next(c for c in CASES['combine'] if isinstance(c['expect'].get('derivedFromMock'), bool))
    _check_combine_row(row)
    with pytest.raises(AssertionError, match='derivedFromMock'):
        _check_combine_row({**row, 'expect': {**row['expect'], 'derivedFromMock': int(row['expect']['derivedFromMock'])}})
    for expect in ({'derivedFromMock': 0}, {'basis': None}):
        with pytest.raises(AssertionError):
            _check_construct_row({'name': 'x', 'input': {'source': 'real'}, 'expect': expect})
        with pytest.raises(AssertionError):
            _check_derive_row({'name': 'x', 'inputs': [{'source': 'real'}], 'expect': expect})


def test_a_construct_or_derive_refusal_that_is_not_a_value_error_fails_the_row():
    # SPEC §2: Python refuses with a ValueError. A port that raises any other
    # type, with the expected words, must not pass (#602's Python side).
    import pytest

    def raising(*_args, **_kwargs):
        raise TypeError('source must be one of these')
    with pytest.raises(TypeError):
        _check_construct_row({'name': 'x', 'input': {'source': 'bogus'}, 'expectError': 'source must be one of'},
                             make_meta=raising)
    with pytest.raises(TypeError):
        _check_derive_row({'name': 'x', 'inputs': [{'source': 'real'}], 'override': {'source': 'bogus'},
                           'expectError': 'source must be one of'}, derive=raising)
    # The reference's ValueError passes the same rows.
    _check_construct_row({'name': 'x', 'input': {'source': 'bogus'}, 'expectError': 'source must be one of'})
    _check_derive_row({'name': 'x', 'inputs': [{'source': 'real'}], 'override': {'source': 'bogus'},
                       'expectError': 'source must be one of'})


def test_an_unknown_case_field_is_named():
    row = {**CASES['combine'][0], 'expectSomethingNew': True}
    problem = _unknown_fields('combine', row)
    assert problem is not None and 'expectSomethingNew' in problem
    assert _unknown_fields('combine', CASES['combine'][0]) is None
    # Named in the row's order, as JS's Object.keys gives them.
    assert _unknown_fields('audit', {'name': 'x', 'zeta': 1, 'alpha': 2}).startswith('unknown case field(s) zeta, alpha:')


def test_an_unknown_missing_or_malformed_case_kind_fails_the_table():
    assert _kind_problems(CASES) == []
    assert _kind_problems({**CASES, 'clone': [{'name': 'x'}]}) == [
        'unknown case kind clone: teach this runner to interpret it']
    rest = {k: v for k, v in CASES.items() if k != 'construct'}
    assert _kind_problems(rest) == ['case kind construct is missing from the table']
    assert _kind_problems({**CASES, 'guard': {'name': 'x'}}) == ['case kind guard is not a list of cases']
