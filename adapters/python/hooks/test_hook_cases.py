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
_ROW = ['name', 'stdin', 'stdinHex', 'env', 'envHex', 'cfg', 'expectExit', 'expectStderr']
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
    # envHex sets a variable to raw bytes (#501). The JS twin passes it through
    # sh and printf, whose $(...) strips a trailing newline, so a trailing 0a
    # byte is refused in both twins.
    if 'envHex' in c:
        if not isinstance(c['envHex'], dict):
            problems.append('envHex must be an object')
        else:
            for k, v in c['envHex'].items():
                if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', k):
                    problems.append(f'envHex key {json.dumps(k)} must be a variable name')
                if not isinstance(v, str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2})*', v):
                    problems.append(f'envHex.{k} must be whole hex bytes')
                elif v.lower().endswith('0a'):
                    problems.append(f'envHex.{k} must not end with a newline byte')
                elif '00' in (v[i:i + 2] for i in range(0, len(v), 2)):
                    problems.append(f'envHex.{k} must not contain a NUL byte')
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
    if 'envHex' in c:
        # Raw bytes (#501): an environment of bytes, which POSIX allows.
        env = {os.fsencode(k): os.fsencode(v) for k, v in env.items()}
        env.update({k.encode(): bytes.fromhex(v) for k, v in c['envHex'].items()})
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


def test_a_planted_envhex_that_is_malformed_fails():
    assert _type_problems({'name': 'x', 'expectExit': 0, 'envHex': {'A': 'ff0'}}) == [
        'envHex.A must be whole hex bytes']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'envHex': {'A': 'ff0a'}}) == [
        'envHex.A must not end with a newline byte']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'envHex': {'A B': 'ff'}}) == [
        'envHex key "A B" must be a variable name']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'envHex': {'A': '610062'}}) == [
        'envHex.A must not contain a NUL byte']


@pytest.mark.parametrize('hex_', ['efbbb', '1g2c'])
def test_a_planted_stdinhex_that_is_not_whole_hex_bytes_fails(hex_):
    assert _type_problems({'name': 'x', 'expectExit': 0, 'stdinHex': hex_}) == [
        'stdinHex must be whole hex bytes']


@pytest.mark.parametrize('kind', list(_HOOKS))
def test_every_hook_has_at_least_one_case(kind):
    assert CASES.get(kind)


def _reads_branch(c):
    """(branch, unknown) when the row's reason shows how the guard read a named
    branch, else None. JS twin: readsBranch."""
    branch = c.get('env', {}).get('PLUMBLINE_BRANCH')
    if not isinstance(branch, str) or not branch.strip(' \t\n\r\f\v'):
        return None
    reason = c.get('expectStderr', '')
    if 'branch unknown' in reason:
        return branch, True
    if 'on protected branch' in reason:
        return branch, False
    return None


# #474: what counts as a branch name is git's rule, not ours. A row whose
# reason shows how the guard read a named branch (not unset or blank) must
# agree with `git check-ref-format --branch`: "branch unknown" means git
# rejects the name, "on protected branch" means git accepts it. JS twin:
# "branch names agree with git".
_READS = [(c, _reads_branch(c)) for c in CASES.get('branchGuard', []) if _reads_branch(c)]


def test_the_git_cross_check_selects_rows_on_both_sides_of_the_rule():
    # A change to the reason wording would otherwise select nothing, silently.
    assert sum(1 for _, (_, unknown) in _READS if unknown) >= 10
    assert sum(1 for _, (_, unknown) in _READS if not unknown) >= 3


@pytest.mark.parametrize('c', [c for c, _ in _READS], ids=lambda c: c['name'])
def test_branch_rows_agree_with_git(c, tmp_path):
    branch, unknown = _reads_branch(c)
    # git runs outside any repository: inside one, `--branch` expands `@{-1}`
    # and `@{u}` against that repository's history, so the verdict would
    # depend on where the tests run (#474 review).
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(tmp_path.parent))
    git = subprocess.run(['git', 'check-ref-format', '--branch', branch], capture_output=True,
                         cwd=tmp_path, env=env)
    assert (git.returncode == 0) is (not unknown), branch


@pytest.mark.parametrize('kind,c', [(k, c) for k in _HOOKS for c in CASES.get(k, [])],
                         ids=lambda v: v['name'] if isinstance(v, dict) else v)
def test_hook_case(kind, c):
    assert _type_problems(c) == []
    r = _run(kind, c)
    stderr = r.stderr.decode('utf-8', 'replace')
    assert r.returncode == c['expectExit'], stderr
    if 'expectStderr' in c:
        assert c['expectStderr'] in stderr
