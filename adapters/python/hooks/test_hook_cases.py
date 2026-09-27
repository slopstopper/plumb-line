"""Runs adapters/hook-cases.json against the Python hook CLIs (#475). Twin of
adapters/js/hooks/__tests__/hook-cases.test.mjs. The twins' CLI parity is a
data contract: a case lives in the table, not in one language's spawn tests,
so neither twin can quietly miss it."""
import copy
import json
import os
import re
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, os.path.join(_REPO, 'primitives', 'python', 'tests'))
from case_table_guards import table_problems  # noqa: E402

with open(os.path.join(_REPO, 'adapters', 'hook-cases.json'), encoding='utf-8') as f:
    CASES = json.load(f)

_HOOKS = {
    'branchGuard': 'branch_guard.py',
    'boundaryGuard': 'boundary_guard.py',
    'preCommitGate': 'pre_commit_gate.py',
}

# Every field, case kind and table version this runner interprets (#441). JS
# twin: MODEL in adapters/js/hooks/__tests__/hook-cases.test.mjs.
_ROW = ['name', 'stdin', 'stdinHex', 'env', 'cfg', 'expectExit', 'expectStderr']
_MODEL = {
    'versions': [1],
    'meta': ['_doc', 'version'],
    'fields': {kind: _ROW for kind in _HOOKS},
}

def _type_problems(c):
    """The field types this runner reads. Each row is checked before it runs, so
    both twins refuse the same rows: a null or a number where a string belongs,
    or stdinHex that is not whole hex bytes, is a table error, not something
    each language coerces its own way. JS reads JSON 2.0 as the integer 2, so a
    whole float is accepted here too. JS twin: typeProblems."""
    problems = []
    for f in ('name', 'stdin', 'stdinHex', 'expectStderr'):
        if f in c and not isinstance(c[f], str):
            problems.append(f'{f} must be a string')
    if isinstance(c.get('stdinHex'), str) and not re.fullmatch(r'(?:[0-9a-fA-F]{2})*', c['stdinHex']):
        problems.append('stdinHex must be whole hex bytes')
    exit_code = c.get('expectExit')
    whole = (isinstance(exit_code, int) and not isinstance(exit_code, bool)) or (
        isinstance(exit_code, float) and exit_code.is_integer())
    if not whole:
        problems.append('expectExit must be an integer')
    if 'env' in c:
        if not isinstance(c['env'], dict):
            problems.append('env must be an object')
        else:
            problems += [f'env.{k} must be a string or null'
                         for k, v in c['env'].items() if v is not None and not isinstance(v, str)]
    return problems


def _is_cleared(k):
    """Removed first so the caller's shell cannot leak in: every PLUMBLINE_*
    variable (including ones a later hook adds) and PYTHONIOENCODING."""
    return k.startswith('PLUMBLINE_') or k == 'PYTHONIOENCODING'


def _run(kind, c):
    env = {k: v for k, v in os.environ.items() if not _is_cleared(k)}
    if 'cfg' in c:
        env['PLUMBLINE_CFG'] = json.dumps(c['cfg'])
    for k, v in c.get('env', {}).items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    stdin = bytes.fromhex(c['stdinHex']) if 'stdinHex' in c else c.get('stdin', '').encode('utf-8')
    return subprocess.run([sys.executable, os.path.join(_HERE, _HOOKS[kind])], input=stdin,
                          capture_output=True, env=env,
                          timeout=30)  # a hook that hangs fails its row, not the suite


def test_the_shipped_table_has_nothing_this_runner_ignores():
    assert table_problems(CASES, _MODEL) == []


def test_a_planted_unknown_field_fails():
    t = copy.deepcopy(CASES)
    t['branchGuard'][0]['surprise'] = 1
    [problem] = table_problems(t, _MODEL)
    assert 'unknown field(s) surprise' in problem


def test_a_planted_unknown_kind_fails():
    t = dict(copy.deepcopy(CASES), commitMsgGuard=[])
    [problem] = table_problems(t, _MODEL)
    assert 'unknown case kind commitMsgGuard' in problem


def test_a_planted_unknown_version_fails():
    t = dict(copy.deepcopy(CASES), version=2)
    [problem] = table_problems(t, _MODEL)
    assert 'unknown case-table version 2' in problem


def test_a_planted_boolean_version_fails_as_it_does_in_the_js_twin():
    t = dict(copy.deepcopy(CASES), version=True)
    [problem] = table_problems(t, _MODEL)
    assert 'unknown case-table version true' in problem


def test_every_rows_fields_have_the_types_this_runner_reads():
    problems = [f'{kind} {json.dumps(c.get("name"))}: {p}'
                for kind in _HOOKS for c in CASES.get(kind, []) for p in _type_problems(c)]
    assert problems == []


def test_a_planted_null_or_number_where_a_string_belongs_fails():
    assert _type_problems({'name': 'x', 'expectExit': 0, 'stdin': None}) == ['stdin must be a string']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'env': None}) == ['env must be an object']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'env': {'A': 1}}) == ['env.A must be a string or null']
    assert _type_problems({'name': 'x', 'expectExit': '2'}) == ['expectExit must be an integer']
    assert _type_problems({'name': 'x', 'expectExit': 2.5}) == ['expectExit must be an integer']
    assert _type_problems({'name': 'x', 'expectExit': 2.0}) == []


@pytest.mark.parametrize('hex_', ['efbbb', '1g2c'])
def test_a_planted_stdinhex_that_is_not_whole_hex_bytes_fails(hex_):
    assert _type_problems({'name': 'x', 'expectExit': 0, 'stdinHex': hex_}) == [
        'stdinHex must be whole hex bytes']


@pytest.mark.parametrize('kind', list(_HOOKS))
def test_every_hook_has_at_least_one_case(kind):
    assert CASES.get(kind)


@pytest.mark.parametrize('kind,c', [(k, c) for k in _HOOKS for c in CASES.get(k, [])],
                         ids=lambda v: v['name'] if isinstance(v, dict) else v)
def test_hook_case(kind, c):
    assert _type_problems(c) == []
    r = _run(kind, c)
    stderr = r.stderr.decode('utf-8', 'replace')
    assert r.returncode == c['expectExit'], stderr
    if 'expectStderr' in c:
        assert c['expectStderr'] in stderr
