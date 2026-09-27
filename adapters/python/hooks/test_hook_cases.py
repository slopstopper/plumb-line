"""Runs adapters/hook-cases.json against the Python hook CLIs (#475). Twin of
adapters/js/hooks/__tests__/hook-cases.test.mjs. The twins' CLI parity is a
data contract: a case lives in the table, not in one language's spawn tests,
so neither twin can quietly miss it."""
import copy
import json
import os
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

# Variables a row may set; removed first so the caller's shell cannot leak in.
_CLEARED = ('PLUMBLINE_BRANCH', 'PLUMBLINE_CFG', 'PLUMBLINE_TEST_CMD', 'PYTHONIOENCODING')


def _run(kind, c):
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED}
    if 'cfg' in c:
        env['PLUMBLINE_CFG'] = json.dumps(c['cfg'])
    for k, v in c.get('env', {}).items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    stdin = bytes.fromhex(c['stdinHex']) if 'stdinHex' in c else c.get('stdin', '').encode('utf-8')
    return subprocess.run([sys.executable, os.path.join(_HERE, _HOOKS[kind])], input=stdin,
                          capture_output=True, env=env)


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


@pytest.mark.parametrize('kind', list(_HOOKS))
def test_every_hook_has_at_least_one_case(kind):
    assert CASES.get(kind)


@pytest.mark.parametrize('kind,c', [(k, c) for k in _HOOKS for c in CASES.get(k, [])],
                         ids=lambda v: v['name'] if isinstance(v, dict) else v)
def test_hook_case(kind, c):
    r = _run(kind, c)
    stderr = r.stderr.decode('utf-8', 'replace')
    assert r.returncode == c['expectExit'], stderr
    if 'expectStderr' in c:
        assert c['expectStderr'] in stderr
