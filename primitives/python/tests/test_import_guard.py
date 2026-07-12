import os
import subprocess
import sys

PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # primitives/python

def _run(code, extra_path):
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([extra_path, PY_DIR])
    # cwd=extra_path matters: `python -c` prepends '' (cwd) to sys.path ahead of
    # PYTHONPATH entries, so without pinning cwd here the real provenance.py
    # (found via the inherited primitives/python cwd) would shadow the foreign
    # one instead of the reverse, defeating the collision this test exercises.
    return subprocess.run(
        [sys.executable, '-c', code], env=env, cwd=extra_path, capture_output=True, text=True
    )

def test_foreign_provenance_is_rejected(tmp_path):
    # A foreign top-level provenance.py that lacks our sentinel symbols.
    (tmp_path / 'provenance.py').write_text("X = 1\n")
    # Force the flat/fallback path by importing 'marked' with the foreign module
    # ahead on the path. The guard must raise ImportError, not silently proceed.
    r = _run("import marked", str(tmp_path))
    assert r.returncode != 0
    assert 'ImportError' in r.stderr
    assert 'provenance' in r.stderr.lower()

def test_normal_flat_import_still_works(tmp_path):
    # No foreign module: flat import of the real modules must succeed.
    r = _run("import marked, audit; print('ok')", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert 'ok' in r.stdout
