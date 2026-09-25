"""The worked baseline example is a real P9 self-check: each record script
exits 0 only when the committed record matches, and non-zero on drift (#374).

Run from the repo root: python3 -m pytest -q examples/test_baseline_example.py
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = [
    ['node', os.path.join('examples', 'baseline', 'record.mjs')],
    [sys.executable, os.path.join('examples', 'baseline', 'record.py')],
]


def _copy_tree(tmp_path):
    """Copy the example into tmp_path, keeping its ../../primitives imports resolvable."""
    shutil.copytree(os.path.join(_ROOT, 'examples', 'baseline'), tmp_path / 'examples' / 'baseline')
    os.symlink(os.path.join(_ROOT, 'primitives'), tmp_path / 'primitives')
    return tmp_path


@pytest.mark.parametrize('cmd', _SCRIPTS, ids=['js', 'python'])
def test_committed_record_matches(cmd):
    out = subprocess.run(cmd, cwd=_ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.rstrip().endswith(': match')


@pytest.mark.parametrize('cmd', _SCRIPTS, ids=['js', 'python'])
def test_drifted_record_fails(cmd, tmp_path):
    root = _copy_tree(tmp_path)
    record = root / 'examples' / 'baseline' / 'baselines' / 'fx-rate.json'
    data = json.loads(record.read_text(encoding='utf-8'))
    data['value'] = 0.05
    record.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    out = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert out.returncode != 0, out.stdout
    assert 'drift' in out.stdout
