"""Runs adapters/commit-hook-cases.json against the Python branch guard's git
commit hook, in a real temporary git repository per row (#464). Twin of
adapters/js/hooks/__tests__/commit-hook-cases.test.mjs. As with
hook-cases.json, the twins' parity is a data contract: a case lives in the
table, so neither twin can quietly miss it."""
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

with open(os.path.join(_REPO, 'adapters', 'commit-hook-cases.json'), encoding='utf-8') as f:
    CASES = json.load(f)

_HOOK = os.path.join(_HERE, 'branch_guard_commit.py')

# Every field, case kind and table version this runner interprets (#441). JS
# twin: MODEL in adapters/js/hooks/__tests__/commit-hook-cases.test.mjs.
_ROW = ['name', 'repo', 'committed', 'branch', 'tags', 'headRef', 'remove', 'move', 'stage',
        'stageHex', 'modify', 'env', 'commit', 'expectExit', 'expectStderr']
_MODEL = {'versions': [1], 'meta': ['_doc', 'version'], 'fields': {'commitHook': _ROW}}


def _is_strings(v):
    return isinstance(v, list) and all(isinstance(s, str) for s in v)


def _is_hex(s):
    if not isinstance(s, str) or not s or len(s) % 2:
        return False
    return all(ch in '0123456789abcdefABCDEF' for ch in s)


def _is_int(v):
    """JSON cannot tell 2 from 2.0, so a whole float counts, as in the JS twin."""
    return not isinstance(v, bool) and (isinstance(v, int) or (isinstance(v, float) and v.is_integer()))


def _type_problems(c):
    """The field types this runner reads, checked before a row runs, so both
    twins refuse the same rows. JS twin: typeProblems."""
    problems = []
    if not isinstance(c.get('name'), str):
        problems.append('name must be a string')
    if 'repo' in c and c['repo'] is not False:
        problems.append('repo must be false when present')
    for f in ('committed', 'tags', 'remove', 'stage', 'modify', 'commit'):
        if f in c and not _is_strings(c[f]):
            problems.append(f'{f} must be an array of strings')
    if 'branch' in c and c['branch'] is not None and not isinstance(c['branch'], str):
        problems.append('branch must be a string or null')
    if 'headRef' in c and not isinstance(c['headRef'], str):
        problems.append('headRef must be a string')
    if 'stageHex' in c and not (isinstance(c['stageHex'], list) and all(_is_hex(h) for h in c['stageHex'])):
        problems.append('stageHex must be an array of whole hex bytes')
    if 'move' in c and not (isinstance(c['move'], list)
                            and all(_is_strings(m) and len(m) == 2 for m in c['move'])):
        problems.append('move must be an array of [from, to] pairs')
    if 'env' in c:
        if not isinstance(c['env'], dict):
            problems.append('env must be an object')
        else:
            for k, v in c['env'].items():
                if v is not None and not isinstance(v, str):
                    problems.append(f'env.{k} must be a string or null')
    if not _is_int(c.get('expectExit')):
        problems.append('expectExit must be an integer')
    if not isinstance(c.get('expectStderr'), str):
        problems.append('expectStderr must be a string')
    # A detached HEAD, a tag or a HEAD ref needs a commit to stand on.
    if 'committed' not in c and (('branch' in c and c['branch'] is None) or 'tags' in c or 'headRef' in c):
        problems.append('branch null, tags and headRef need committed')
    return problems


# The caller's git and plumb-line settings cannot leak in: every GIT_* and
# PLUMBLINE_* variable is removed (these tests may themselves run inside a git
# hook), and the global and system git config are not read, so a
# core.hooksPath or commit.gpgsign there changes nothing.
_BASE_ENV = {k: v for k, v in os.environ.items()
             if not k.startswith(('GIT_', 'PLUMBLINE_')) and k != 'PYTHONIOENCODING'}
_BASE_ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                 GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com',
                 GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.com')


def _git(cwd, *args, input=None):
    r = subprocess.run(['git', *args], cwd=cwd, env=_BASE_ENV, input=input, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr!r}")
    return r.stdout


def _write(repo, p, text):
    full = os.path.join(repo, p)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(text)


def _build(c, repo):
    """Build the row's repository, as the table's _doc orders it. JS twin: build."""
    _git(repo, 'init', '-q')
    _git(repo, 'symbolic-ref', 'HEAD', 'refs/heads/main')
    if 'committed' in c:
        for p in c['committed']:
            _write(repo, p, 'base\n')
        _git(repo, 'add', '--', *c['committed'])
        _git(repo, 'commit', '-q', '--no-verify', '-m', 'base')
    if 'branch' in c and c['branch'] is None:
        _git(repo, 'checkout', '-q', '--detach')
    elif c.get('branch') not in (None, 'main'):
        _git(repo, 'checkout', '-q', '-b', c['branch'])
    for t in c.get('tags', []):
        _git(repo, 'tag', t)
    if 'headRef' in c:
        _git(repo, 'symbolic-ref', 'HEAD', c['headRef'])
    for p in c.get('remove', []):
        _git(repo, 'rm', '-q', '--', p)
    for src, dst in c.get('move', []):
        os.makedirs(os.path.dirname(os.path.join(repo, dst)), exist_ok=True)
        _git(repo, 'mv', '--', src, dst)
    for p in c.get('stage', []):
        _write(repo, p, 'staged\n')
    if c.get('stage'):
        _git(repo, 'add', '--', *c['stage'])
    if c.get('stageHex'):
        # Index only: a path that is not UTF-8 cannot be created on every
        # filesystem (APFS refuses it), but git's index takes any bytes.
        blob = _git(repo, 'hash-object', '-w', '--stdin', input=b'staged\n').decode().strip()
        info = b''.join(f'100644 {blob}\t'.encode() + bytes.fromhex(h) + b'\0' for h in c['stageHex'])
        _git(repo, 'update-index', '-z', '--add', '--index-info', input=info)
    for p in c.get('modify', []):
        _write(repo, p, 'modified\n')


def _run(c, tmp_path):
    env = dict(_BASE_ENV)
    for k, v in c.get('env', {}).items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    options = dict(env=env, capture_output=True, timeout=30)  # a hang fails its row
    if c.get('repo') is False:
        cwd = tmp_path / 'no-repo'
        cwd.mkdir()
        env['GIT_CEILING_DIRECTORIES'] = str(tmp_path)
        return subprocess.run([sys.executable, _HOOK], cwd=cwd, **options)
    repo = str(tmp_path / 'repo')
    os.mkdir(repo)
    _build(c, repo)
    if 'commit' not in c:
        return subprocess.run([sys.executable, _HOOK], cwd=repo, **options)
    hook = os.path.join(repo, '.git', 'hooks', 'pre-commit')
    with open(hook, 'w', encoding='utf-8') as f:
        f.write(f"#!/bin/sh\nexec '{sys.executable}' '{_HOOK}'\n")
    os.chmod(hook, 0o755)
    return subprocess.run(['git', 'commit', '-q', '-m', 'case', *c['commit']], cwd=repo, **options)


def test_the_shipped_table_has_nothing_this_runner_ignores():
    assert table_problems(CASES, _MODEL) == []


def test_a_planted_unknown_field_fails():
    t = copy.deepcopy(CASES)
    t['commitHook'][0]['surprise'] = 1
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and 'unknown field(s) surprise' in problems[0]


def test_a_planted_unknown_kind_or_version_fails():
    assert 'unknown case kind pushHook' in table_problems({**copy.deepcopy(CASES), 'pushHook': []}, _MODEL)[0]
    assert 'unknown case-table version 2' in table_problems({**copy.deepcopy(CASES), 'version': 2}, _MODEL)[0]


def test_every_rows_fields_have_the_types_this_runner_reads():
    problems = [f"{json.dumps(c.get('name'))}: {p}" for c in CASES['commitHook'] for p in _type_problems(c)]
    assert problems == []


def test_a_planted_wrong_type_fails():
    ok = {'name': 'x', 'expectExit': 0, 'expectStderr': ''}
    assert _type_problems({**ok, 'stage': 'src/a.js'}) == ['stage must be an array of strings']
    assert _type_problems({**ok, 'stageHex': ['ff0']}) == ['stageHex must be an array of whole hex bytes']
    assert _type_problems({**ok, 'move': [['a']]}) == ['move must be an array of [from, to] pairs']
    assert _type_problems({**ok, 'branch': 1}) == ['branch must be a string or null']
    assert _type_problems({**ok, 'repo': True}) == ['repo must be false when present']
    assert _type_problems({**ok, 'env': {'A': 1}}) == ['env.A must be a string or null']
    assert _type_problems({**ok, 'branch': None}) == ['branch null, tags and headRef need committed']
    assert _type_problems({'name': 'x', 'expectExit': 2.5}) == [
        'expectExit must be an integer', 'expectStderr must be a string']
    assert _type_problems({**ok, 'expectExit': 2.0}) == []


def test_covers_the_four_cases_464_names():
    """The acceptance of #464 names these four; a table edit cannot drop one."""
    names = '\n'.join(c['name'] for c in CASES['commitHook'])
    for kind in ('on a protected branch blocks', 'on an unprotected branch passes',
                 'detached HEAD blocks', 'docs-only commit on a protected branch passes'):
        assert kind in names


@pytest.mark.parametrize('c', CASES['commitHook'], ids=lambda c: c['name'])
def test_commit_hook_case(c, tmp_path):
    assert _type_problems(c) == []
    r = _run(c, tmp_path)
    stderr = r.stderr.decode('utf-8')
    assert r.returncode == c['expectExit'], stderr
    assert stderr == c['expectStderr']
