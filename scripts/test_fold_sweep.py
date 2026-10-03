"""The case-fold sweep across Unicode versions (#625, #642).

primitives/conformance/fold_sweep.py compares, one code point at a time, how
the running Node and Python read every code point, as the hooks' case-alias
check reads them. PARITY.md cites its figures as a dated measurement on named
runtimes: a CI job has one Node and one Python, so CI cannot reproduce
figures that pair other versions, and this suite does not hold them. It
proves that the sweep reads code points as the hooks do, and that on the pair
it runs on, the premises PARITY.md states hold: the folds agree where both
runtimes know a code point, and a code point one does not know folds to one
code point in the other.

Run from the repo root: python3 -m pytest -q scripts/test_fold_sweep.py
"""
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import unicodedata

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SWEEP = os.path.join(_ROOT, 'primitives', 'conformance', 'fold_sweep.py')
_SWEEP_JS = os.path.join(_ROOT, 'primitives', 'conformance', 'fold-sweep.mjs')
_GUARD_PY = os.path.join(_ROOT, 'adapters', 'python', 'hooks', 'branch_guard.py')
_GUARD_JS = os.path.join(_ROOT, 'adapters', 'js', 'hooks', 'branch-guard.mjs')


def _load(name, path):
    # Loaded by path under its own name, so no flat module name is shadowed.
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _code_points():
    return (cp for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF)


def test_the_python_half_reads_every_code_point_as_the_python_hook_does():
    sweep = _load('fold_sweep', _SWEEP)
    guard = _load('fold_sweep_branch_guard', _GUARD_PY)
    for cp in _code_points():
        c = chr(cp)
        assert sweep.fold(c) == guard._fold(c), f'U+{cp:04X}'
        assert sweep.unknown(c) == guard._unknown(c), f'U+{cp:04X}'


@pytest.mark.parametrize('line', [
    'const fold = (name) => String(name).normalize("NFC").toUpperCase().toLowerCase();',
    'const UNKNOWN = /^\\p{Cn}$/u;',
])
def test_the_js_half_reads_code_points_as_the_js_hook_does(line):
    # The hook does not export these, so the sweep restates them; this holds
    # the two copies to one text.
    for path in (_GUARD_JS, _SWEEP_JS):
        with open(path, encoding='utf-8') as fh:
            assert line in fh.read().splitlines(), f'{os.path.relpath(path, _ROOT)} no longer has: {line}'


@pytest.mark.parametrize('cp, cls', [
    (0x0061, 0), (0x0334, 1), (0x0323, 220), (0x0301, 230), (0x0315, 232), (0x0345, 240),
])
def test_the_class_rules_the_js_half_uses_hold_on_known_marks(cp, cls):
    sweep = _load('fold_sweep', _SWEEP)
    assert unicodedata.combining(chr(cp)) == cls
    assert sweep.reorders(chr(cp)) is (cls != 0)
    assert sweep.acute_moves(chr(cp)) is (cls not in (0, 230))


def _run_sweep():
    if shutil.which('node') is None:
        pytest.skip('node is not on PATH; the sweep runs the JS half')
    proc = subprocess.run([sys.executable, _SWEEP, '--json'], cwd=_ROOT,
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode in (0, 1), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_on_this_pair_the_premises_parity_md_states_hold():
    code, out = _run_sweep()
    # The JS half's class rule, checked on every code point Python knows.
    assert out['markRuleMisses'] == 0, out['detail']['markRuleMisses']
    assert out['foldDiffers'] == 0, out['detail']['foldDiffers']
    assert out['foldNotOne'] == 0, out['detail']['foldNotOne']
    assert code == 0
    assert out['codePoints'] == 0x110000 - 0x800


def test_the_sweep_names_the_runtimes_it_compared():
    _, out = _run_sweep()
    m = out['measured']
    node = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True)
    assert m['node'] == node.stdout.strip()
    assert m['python'] == platform.python_version()
    assert m['pythonUnicode'] == unicodedata.unidata_version
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=_ROOT, capture_output=True, text=True)
    assert m['commit'] == (head.stdout.strip() if head.returncode == 0 else None)
