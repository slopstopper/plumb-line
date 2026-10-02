"""Runs adapters/commit-hook-cases.json against the Python branch guard's git
commit hook (#464) and the pre-commit gate (#613), in a real temporary git
repository per row. Twin of
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

# Each case kind and the hook its rows run. JS twin: HOOKS.
_HOOKS = {
    'commitHook': os.path.join(_HERE, 'branch_guard_commit.py'),
    'preCommitGate': os.path.join(_HERE, 'pre_commit_gate.py'),
}

# Every field, case kind and table version this runner interprets (#441). JS
# twin: MODEL in adapters/js/hooks/__tests__/commit-hook-cases.test.mjs.
_ROW = ['name', 'repo', 'committed', 'committedText', 'fakeGit', 'side', 'branch', 'tags', 'headRef', 'config', 'merge',
        'rebaseStop', 'rebaseApply', 'rebaseAlso', 'rebaseHeadName', 'rebaseHeadNameDir', 'rebaseUpdateRefsDir', 'remove', 'move', 'stage', 'stageHex', 'gitlink', 'stageCount', 'modify', 'env', 'commit',
        'expectExit', 'expectStderr']
_MODEL = {'versions': [1], 'meta': ['_doc', 'version'], 'fields': {kind: _ROW for kind in _HOOKS}}


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
    for f in ('committed', 'side', 'tags', 'merge', 'remove', 'stage', 'gitlink', 'modify', 'commit'):
        if f in c and not _is_strings(c[f]):
            problems.append(f'{f} must be an array of strings')
    if 'branch' in c and c['branch'] is not None and not isinstance(c['branch'], str):
        problems.append('branch must be a string or null')
    if 'headRef' in c and not isinstance(c['headRef'], str):
        problems.append('headRef must be a string')
    if 'stageHex' in c and not (isinstance(c['stageHex'], list) and all(_is_hex(h) for h in c['stageHex'])):
        problems.append('stageHex must be an array of whole hex bytes')
    for f in ('move', 'config'):
        if f in c and not (isinstance(c[f], list) and all(_is_strings(m) and len(m) == 2 for m in c[f])):
            problems.append(f'{f} must be an array of pairs of strings')
    if 'stageCount' in c:
        sc = c['stageCount']
        if not (isinstance(sc, list) and len(sc) == 2 and isinstance(sc[0], str) and sc[0]
                and _is_int(sc[1]) and 1 <= sc[1] <= 20000):
            problems.append('stageCount must be [a non-empty prefix, a count from 1 to 20000]')
    if 'env' in c:
        if not isinstance(c['env'], dict):
            problems.append('env must be an object')
        else:
            for k, v in c['env'].items():
                if v is not None and not isinstance(v, str):
                    problems.append(f'env.{k} must be a string or null')
    if 'committedText' in c and not (isinstance(c['committedText'], dict)
                                     and all(isinstance(v, str) for v in c['committedText'].values())):
        problems.append('committedText must be an object of strings')
    if 'fakeGit' in c:
        f = c['fakeGit']
        if not (isinstance(f, dict) and isinstance(f.get('script'), str)
                and isinstance(f.get('executable'), bool) and set(f) == {'script', 'executable'}):
            problems.append('fakeGit must be {script: string, executable: boolean}')
        if 'commit' in c:
            problems.append('fakeGit cannot be combined with commit')
    if not _is_int(c.get('expectExit')):
        problems.append('expectExit must be an integer')
    if not isinstance(c.get('expectStderr'), str):
        problems.append('expectStderr must be a string')
    # A detached HEAD, a tag, a HEAD ref, a side branch or a gitlink needs a
    # commit to stand on, and a merge needs the side branch.
    if 'committed' not in c and (('branch' in c and c['branch'] is None)
                                 or any(f in c for f in ('tags', 'headRef', 'side', 'gitlink'))):
        problems.append('branch null, tags, headRef, side and gitlink need committed')
    if 'merge' in c and 'side' not in c:
        problems.append('merge needs side')
    if 'rebaseStop' in c and not isinstance(c['rebaseStop'], str):
        problems.append('rebaseStop must be a string')
    if 'rebaseHeadName' in c and c['rebaseHeadName'] is not None and not isinstance(c['rebaseHeadName'], str):
        problems.append('rebaseHeadName must be a string or null')
    if 'rebaseHeadNameDir' in c and c['rebaseHeadNameDir'] is not True:
        problems.append('rebaseHeadNameDir must be true when present')
    if 'rebaseApply' in c and c['rebaseApply'] is not True:
        problems.append('rebaseApply must be true when present')
    if 'rebaseAlso' in c and not isinstance(c['rebaseAlso'], str):
        problems.append('rebaseAlso must be a string')
    if 'rebaseUpdateRefsDir' in c and c['rebaseUpdateRefsDir'] is not True:
        problems.append('rebaseUpdateRefsDir must be true when present')
    if any(f in c for f in ('rebaseApply', 'rebaseAlso')) and 'rebaseStop' not in c:
        problems.append('rebaseApply and rebaseAlso need rebaseStop')
    if 'rebaseApply' in c and 'rebaseAlso' in c:
        problems.append('rebaseApply cannot be combined with rebaseAlso')
    if 'rebaseUpdateRefsDir' in c and 'rebaseAlso' not in c:
        problems.append('rebaseUpdateRefsDir needs rebaseAlso')
    if 'rebaseStop' in c and 'committed' not in c:
        problems.append('rebaseStop needs committed')
    if ('rebaseHeadName' in c or 'rebaseHeadNameDir' in c) and 'rebaseStop' not in c:
        problems.append('rebaseHeadName and rebaseHeadNameDir need rebaseStop')
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
        for p, text in c.get('committedText', {}).items():
            _write(repo, p, text)
        _git(repo, 'add', '--', *c['committed'], *c.get('committedText', {}))
        _git(repo, 'commit', '-q', '--no-verify', '-m', 'base')
    if c.get('side'):
        _git(repo, 'checkout', '-q', '-b', 'side')
        for p in c['side']:
            _write(repo, p, 'side\n')
        _git(repo, 'add', '--', *c['side'])
        _git(repo, 'commit', '-q', '--no-verify', '-m', 'side')
        _git(repo, 'checkout', '-q', 'main')
    if 'branch' in c and c['branch'] is None:
        _git(repo, 'checkout', '-q', '--detach')
    elif c.get('branch') not in (None, 'main'):
        _git(repo, 'checkout', '-q', '-b', c['branch'])
    for t in c.get('tags', []):
        _git(repo, 'tag', t)
    if 'headRef' in c:
        _git(repo, 'symbolic-ref', 'HEAD', c['headRef'])
    for k, v in c.get('config', []):
        _git(repo, 'config', k, v)
    if c.get('merge'):
        _git(repo, 'merge', '-q', *c['merge'])
    if 'rebaseStop' in c:
        _write(repo, c['rebaseStop'], 'rebased\n')
        if c.get('rebaseApply'):
            _write(repo, 'conflict.txt', 'branch\n')
        _git(repo, 'add', '--', c['rebaseStop'], *(['conflict.txt'] if c.get('rebaseApply') else []))
        _git(repo, 'commit', '-q', '--no-verify', '-m', 'rebased')
        args = ['rebase', '-q', '--exec', 'false', 'HEAD~1']
        if c.get('rebaseApply'):
            # The apply backend has no --exec: it stops on an add/add
            # conflict, with rebase-apply/head-name written.
            name = _git(repo, 'rev-parse', '--abbrev-ref', 'HEAD').decode().strip()
            _git(repo, 'checkout', '-q', '-b', 'apply-onto', 'HEAD~1')
            _write(repo, 'conflict.txt', 'onto\n')
            _git(repo, 'add', '--', 'conflict.txt')
            _git(repo, 'commit', '-q', '--no-verify', '-m', 'onto')
            _git(repo, 'checkout', '-q', name)
            args = ['rebase', '-q', '--apply', 'apply-onto']
        elif 'rebaseAlso' in c:
            # --update-refs: rebaseAlso points at the commit the rebase stops
            # on, so the rebase will move it too.
            _git(repo, 'branch', '-f', c['rebaseAlso'], 'HEAD')
            _write(repo, 'tip.md', 'tip\n')
            _git(repo, 'add', '--', 'tip.md')
            _git(repo, 'commit', '-q', '--no-verify', '-m', 'tip')
            args = ['rebase', '-q', '--update-refs', '--exec', 'false', 'HEAD~2']
        # --exec false stops the rebase after the commit is replayed, with
        # HEAD detached and rebase-merge/head-name written, as an `edit` stop is.
        r = subprocess.run(['git', *args], cwd=repo, env=_BASE_ENV, capture_output=True)
        if r.returncode == 0:
            raise RuntimeError(f"git {' '.join(args)} did not stop")
        rebase_dir = _git(repo, 'rev-parse', '--git-path',
                          'rebase-apply' if c.get('rebaseApply') else 'rebase-merge').decode().strip()
        if c.get('rebaseUpdateRefsDir'):
            os.remove(os.path.join(repo, rebase_dir, 'update-refs'))
            os.mkdir(os.path.join(repo, rebase_dir, 'update-refs'))
        head_name = os.path.join(repo, rebase_dir, 'head-name')
        if c.get('rebaseHeadNameDir'):
            os.remove(head_name)
            os.mkdir(head_name)
        elif 'rebaseHeadName' in c and c['rebaseHeadName'] is None:
            os.remove(head_name)
        elif 'rebaseHeadName' in c:
            with open(head_name, 'w', encoding='utf-8') as f:
                f.write(c['rebaseHeadName'])
    for p in c.get('remove', []):
        _git(repo, 'rm', '-q', '--', p)
    for src, dst in c.get('move', []):
        os.makedirs(os.path.dirname(os.path.join(repo, dst)), exist_ok=True)
        _git(repo, 'mv', '--', src, dst)
    for p in c.get('stage', []):
        _write(repo, p, 'staged\n')
    if c.get('stage'):
        _git(repo, 'add', '--', *c['stage'])
    # Index only: a path that is not UTF-8 cannot be created on every
    # filesystem (APFS refuses it), but git's index takes any bytes, and
    # thousands of paths are staged without writing thousands of files.
    index_only = [('100644', bytes.fromhex(h)) for h in c.get('stageHex', [])]
    index_only += [('160000', p.encode()) for p in c.get('gitlink', [])]
    if 'stageCount' in c:
        prefix, n = c['stageCount']
        index_only += [('100644', f'{prefix}{i}'.encode()) for i in range(int(n))]
    if index_only:
        blob = _git(repo, 'hash-object', '-w', '--stdin', input=b'staged\n').decode().strip()
        head = _git(repo, 'rev-parse', 'HEAD').decode().strip() if c.get('gitlink') else ''
        info = b''.join(f"{mode} {head if mode == '160000' else blob}\t".encode() + p + b'\0'
                        for mode, p in index_only)
        _git(repo, 'update-index', '-z', '--add', '--index-info', input=info)
    for p in c.get('modify', []):
        _write(repo, p, 'modified\n')


def _run(c, tmp_path, kind='commitHook'):
    hook_file = _HOOKS[kind]
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
        return subprocess.run([sys.executable, hook_file], cwd=cwd, **options)
    repo = str(tmp_path / 'repo')
    os.mkdir(repo)
    _build(c, repo)
    if 'fakeGit' in c:
        bin_dir = tmp_path / 'fake-git'
        bin_dir.mkdir()
        (bin_dir / 'git').write_text(c['fakeGit']['script'], encoding='utf-8')
        os.chmod(bin_dir / 'git', 0o755 if c['fakeGit']['executable'] else 0o644)
        env['PATH'] = str(bin_dir)
    if 'commit' not in c:
        return subprocess.run([sys.executable, hook_file], cwd=repo, **options)
    hook = os.path.join(repo, '.git', 'hooks', 'pre-commit')
    with open(hook, 'w', encoding='utf-8') as f:
        f.write(f"#!/bin/sh\nexec '{sys.executable}' '{hook_file}'\n")
    os.chmod(hook, 0o755)

    def head():
        return subprocess.run(['git', 'rev-parse', '-q', '--verify', 'HEAD'], cwd=repo, env=_BASE_ENV,
                              capture_output=True).stdout
    before = head()
    r = subprocess.run(['git', 'commit', '-q', '-m', 'case', *c['commit']], cwd=repo, **options)
    r.committed = head() != before
    return r


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
    problems = [f"{kind} {json.dumps(c.get('name'))}: {p}"
                for kind in _HOOKS for c in CASES[kind] for p in _type_problems(c)]
    assert problems == []


def test_a_planted_wrong_type_fails():
    ok = {'name': 'x', 'expectExit': 0, 'expectStderr': ''}
    assert _type_problems({**ok, 'stage': 'src/a.js'}) == ['stage must be an array of strings']
    assert _type_problems({**ok, 'stageHex': ['ff0']}) == ['stageHex must be an array of whole hex bytes']
    assert _type_problems({**ok, 'move': [['a']]}) == ['move must be an array of pairs of strings']
    assert _type_problems({**ok, 'config': [['a', 1]]}) == ['config must be an array of pairs of strings']
    assert _type_problems({**ok, 'stageCount': ['p', 0]}) == [
        'stageCount must be [a non-empty prefix, a count from 1 to 20000]']
    assert _type_problems({**ok, 'committed': [], 'merge': ['side']}) == ['merge needs side']
    assert _type_problems({**ok, 'committedText': {'a': 1}}) == ['committedText must be an object of strings']
    assert _type_problems({**ok, 'fakeGit': {'script': 'x'}}) == [
        'fakeGit must be {script: string, executable: boolean}']
    assert _type_problems({**ok, 'fakeGit': {'script': 'x', 'executable': True}, 'commit': []}) == [
        'fakeGit cannot be combined with commit']
    assert _type_problems({**ok, 'branch': 1}) == ['branch must be a string or null']
    assert _type_problems({**ok, 'repo': True}) == ['repo must be false when present']
    assert _type_problems({**ok, 'env': {'A': 1}}) == ['env.A must be a string or null']
    assert _type_problems({**ok, 'branch': None}) == ['branch null, tags, headRef, side and gitlink need committed']
    assert _type_problems({'name': 'x', 'expectExit': 2.5}) == [
        'expectExit must be an integer', 'expectStderr must be a string']
    assert _type_problems({**ok, 'expectExit': 2.0}) == []


def test_covers_the_four_cases_464_names():
    """The acceptance of #464 names these four; a table edit cannot drop one."""
    names = '\n'.join(c['name'] for c in CASES['commitHook'])
    for kind in ('on a protected branch blocks', 'on an unprotected branch passes',
                 'detached HEAD blocks', 'docs-only commit on a protected branch passes'):
        assert kind in names


def test_covers_the_cases_613_names():
    """The branch-aware gate's cases (#613); a table edit cannot drop one."""
    names = '\n'.join(c['name'] for c in CASES['preCommitGate'])
    for kind in ('with no PLUMBLINE_CFG the tests run on any branch and a failure blocks',
                 'on a protected branch failing tests block', 'testsOnOtherBranches absent the tests are not run',
                 '"skip" the tests are not run', '"run" failing tests are allowed',
                 '"run" passing tests are allowed, silently', 'other than "skip" or "run" blocks',
                 'an unset PLUMBLINE_TEST_CMD blocks even where the tests would be skipped',
                 'on a detached HEAD failing tests block', '--update-refs that will move main'):
        assert kind in names


@pytest.mark.parametrize('kind,c', [(k, c) for k in _HOOKS for c in CASES[k]],
                         ids=lambda v: v['name'] if isinstance(v, dict) else v)
def test_commit_hook_case(kind, c, tmp_path):
    assert _type_problems(c) == []
    r = _run(c, tmp_path, kind)
    stderr = r.stderr.decode('utf-8')
    assert r.returncode == c['expectExit'], stderr
    assert stderr == c['expectStderr']
    # A commit row that passes made a commit; one that blocks made none.
    if 'commit' in c:
        assert r.committed == (c['expectExit'] == 0), 'a commit was made'
