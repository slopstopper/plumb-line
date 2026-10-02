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
_ROW = ['name', 'stdin', 'stdinHex', 'env', 'envHex', 'repeat', 'cfg', 'expectExit', 'expectStderr']
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
    # repeat declares long strings instead of writing them out: every {{NAME}}
    # in stdin, env, cfg or expectStderr becomes the string repeated. A token
    # used but not declared, or declared but not used, is a table error, so a
    # typo cannot silently test the literal token instead.
    if 'repeat' in c:
        if not isinstance(c['repeat'], dict):
            problems.append('repeat must be an object')
        else:
            for k in sorted(c['repeat']):
                v = c['repeat'][k]
                if not re.fullmatch(r'[A-Z][A-Z0-9_]*', k):
                    problems.append(f'repeat key {json.dumps(k)} must be an upper-case name')
                count = v[1] if isinstance(v, list) and len(v) == 2 else None
                # JSON cannot tell 2 from 2.0, and the JS twin reads both as 2.
                whole = (isinstance(count, int) and not isinstance(count, bool)) or (
                    isinstance(count, float) and count.is_integer())
                if not (isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0]
                        and whole and 1 <= count <= 1_000_000):
                    problems.append(f'repeat.{k} must be [a non-empty string, a count from 1 to 1000000]')
                elif len(v[0].encode('utf-16-le')) // 2 * int(count) > 100_000:
                    # Linux caps one environment value at 128 KB (MAX_ARG_STRLEN); counted
                    # in UTF-16 units, as the JS twin's .length is.
                    problems.append(f'repeat.{k} must expand to at most 100000 characters')
    declared = sorted(c['repeat']) if isinstance(c.get('repeat'), dict) else []
    if any('{{' in _TOKEN.sub('', s) for s in _repeatable_strings(c)):
        problems.append('a repeat token must be written {{UPPER_CASE}}')
    if any('{{' in k for k in _repeatable_keys(c)):
        problems.append('repeat tokens are expanded only in values, not keys')
    used = set(_repeat_tokens(c))
    problems += [f'repeat token {{{{{t}}}}} is not declared' for t in sorted(used) if t not in declared]
    problems += [f'repeat.{k} is not used' for k in declared if k not in used]
    return problems


_TOKEN = re.compile(r'\{\{([A-Z][A-Z0-9_]*)\}\}')


def _repeatable_strings(c):
    """Every string a repeat token may appear in: stdin, env values, cfg
    (deeply), expectStderr. JS twin: repeatableStrings."""
    out = []

    def walk(v):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    walk([c.get('stdin'), c.get('env'), c.get('cfg'), c.get('expectStderr')])
    return out


def _repeatable_keys(c):
    """Every object key in env and cfg, where tokens are never expanded."""
    out = []

    def walk(v):
        if isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for k, x in v.items():
                out.append(k)
                walk(x)

    walk([c.get('env'), c.get('cfg')])
    return out


def _repeat_tokens(c):
    return [m.group(1) for s in _repeatable_strings(c) for m in _TOKEN.finditer(s)]


def _expand_repeat(c):
    """The row with every declared {{NAME}} expanded. JS twin: expandRepeat."""
    if 'repeat' not in c:
        return c

    def expand(v):
        if isinstance(v, str):
            return _TOKEN.sub(lambda m: c['repeat'][m.group(1)][0] * int(c['repeat'][m.group(1)][1])
                              if m.group(1) in c['repeat'] else m.group(0), v)
        if isinstance(v, list):
            return [expand(x) for x in v]
        if isinstance(v, dict):
            return {k: expand(x) for k, x in v.items()}
        return v

    return {**c, **{f: expand(c[f]) for f in ('stdin', 'env', 'cfg', 'expectStderr') if f in c}}


def _is_cleared(k):
    """Removed first so the caller's shell cannot leak in: every PLUMBLINE_*
    variable (including ones a later hook adds), PYTHONIOENCODING, and
    CLAUDE_PROJECT_DIR, the repository the branch guard reads core.ignorecase
    from (#615)."""
    return k.startswith('PLUMBLINE_') or k in ('PYTHONIOENCODING', 'CLAUDE_PROJECT_DIR')


def _run(kind, row):
    c = _expand_repeat(row)
    env = {k: v for k, v in os.environ.items() if not _is_cleared(k)}
    if 'cfg' in c:
        # The same bytes the JS runner's JSON.stringify sends: compact and raw
        # UTF-8, not ASCII-escaped (v0.11.5 dogfood).
        env['PLUMBLINE_CFG'] = json.dumps(c['cfg'], ensure_ascii=False, separators=(',', ':'))
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


def test_repeat_expands_a_declared_token_and_refuses_misuse():
    row = {'name': 'x', 'expectExit': 0, 'repeat': {'LONG': ['ab', 3]},
           'cfg': {'layers': ['{{LONG}}']}, 'expectStderr': '{{LONG}}!'}
    assert _type_problems(row) == []
    assert _expand_repeat(row)['cfg']['layers'] == ['ababab']
    assert _expand_repeat(row)['expectStderr'] == 'ababab!'
    assert _type_problems({'name': 'x', 'expectExit': 0, 'stdin': '{{LONG}}'}) == [
        'repeat token {{LONG}} is not declared']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'repeat': {'LONG': ['a', 2]}}) == [
        'repeat.LONG is not used']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'repeat': {'LONG': ['a', 0]},
                           'stdin': '{{LONG}}'}) == [
        'repeat.LONG must be [a non-empty string, a count from 1 to 1000000]']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'repeat': {'long': ['a', 2]},
                           'stdin': '{{long}}'}) == [
        'repeat key "long" must be an upper-case name',
        'a repeat token must be written {{UPPER_CASE}}', 'repeat.long is not used']


def test_repeat_accepts_a_whole_float_count_and_refuses_misuse():
    assert _type_problems({'name': 'x', 'expectExit': 0, 'repeat': {'A': ['a', 2.0]}, 'stdin': '{{A}}'}) == []
    assert _expand_repeat({'name': 'x', 'expectExit': 0, 'repeat': {'A': ['a', 2.0]},
                           'stdin': '{{A}}'})['stdin'] == 'aa'
    assert _type_problems({'name': 'x', 'expectExit': 0, 'cfg': {'{{A}}': 'x'}}) == [
        'repeat tokens are expanded only in values, not keys']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'stdin': '{{long}}'}) == [
        'a repeat token must be written {{UPPER_CASE}}']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'repeat': {'A': ['ab', 60000]},
                           'stdin': '{{A}}'}) == ['repeat.A must expand to at most 100000 characters']
    assert _type_problems({'name': 'x', 'expectExit': 0, 'repeat': {'B': ['a', 1], '10': ['a', 1]},
                           'stdin': '{{B}}'}) == [
        'repeat key "10" must be an upper-case name', 'repeat.10 is not used']


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
# Judged as the row runs: after any repeat is expanded (#513 review).
_READS = [(c, _reads_branch(_expand_repeat(c))) for c in CASES.get('branchGuard', [])
          if _reads_branch(_expand_repeat(c))]


def test_the_git_cross_check_selects_rows_on_both_sides_of_the_rule():
    # A change to the reason wording would otherwise select nothing, silently.
    assert sum(1 for _, (_, unknown) in _READS if unknown) >= 10
    assert sum(1 for _, (_, unknown) in _READS if not unknown) >= 3


@pytest.mark.parametrize('c', [c for c, _ in _READS], ids=lambda c: c['name'])
def test_branch_rows_agree_with_git(c, tmp_path):
    branch, unknown = _reads_branch(_expand_repeat(c))
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
    expected = _expand_repeat(c).get('expectStderr')
    if expected is not None:
        assert expected in stderr
