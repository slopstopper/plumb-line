"""Tests for scripts/check-bundle-sync.mjs — the plugin-bundle drift gate.

Run from the repo root:

    python3 -m pytest -q scripts/test_bundle_sync.py

The gate is a Node script that resolves the repo root from its own location,
so each case builds a miniature repo under tmp_path, copies the script into
its scripts/ directory, and runs it there. Until #157 the (source, bundled)
pairs were hand-enumerated and nothing compared them to what the package
actually publishes, so a new standalone module would have been silently
un-bundled.
"""
import os
import shutil
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SCRIPT = os.path.join(_HERE, "check-bundle-sync.mjs")

JS_CORE = ["provenance.mjs", "audit.mjs", "marked.mjs", "index.mjs"]
PY_CORE = ["provenance.py", "audit.py", "marked.py", "__init__.py"]
JS_PUBLISHED = JS_CORE + ["http.mjs"]
PY_PUBLISHED = PY_CORE + ["http.py", "arrays.py", "frames.py"]


def _write(root, rel, body):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)


def _mini_repo(tmp_path, js_files=None, py_files=None):
    """A tree the script accepts: manifests, source modules, bundled copies."""
    root = str(tmp_path / "repo")
    os.makedirs(os.path.join(root, "scripts"))
    shutil.copy(_SCRIPT, os.path.join(root, "scripts", "check-bundle-sync.mjs"))
    js_files = JS_PUBLISHED if js_files is None else js_files
    py_files = PY_PUBLISHED if py_files is None else py_files
    _write(root, "primitives/js/package.json",
           '{"name": "x", "version": "0.0.0", "files": %s}'
           % str(js_files + ["README.md"]).replace("'", '"'))
    for f in js_files:
        _write(root, f"primitives/js/{f}", f"// {f}\n")
    for f in py_files:
        _write(root, f"primitives/python/{f}", f"# {f}\n")
    for f in JS_CORE:
        if f in js_files:
            _write(root, f".claude-plugin/bundled/primitives/js/{f}", f"// {f}\n")
    for f in PY_CORE:
        if f in py_files:
            _write(root, f".claude-plugin/bundled/primitives/python/{f}", f"# {f}\n")
    return root


def _run(root):
    p = subprocess.run(["node", os.path.join(root, "scripts", "check-bundle-sync.mjs")],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def test_clean_tree_passes_and_reports_its_denominators(tmp_path):
    rc, out = _run(_mini_repo(tmp_path))
    assert rc == 0, out
    assert "8 files byte-checked" in out and "4 excluded" in out, out
    assert "js 5/5" in out and "python 7/7" in out, out


def test_byte_drift_still_fails(tmp_path):
    root = _mini_repo(tmp_path)
    _write(root, ".claude-plugin/bundled/primitives/js/audit.mjs", "// stale\n")
    rc, out = _run(root)
    assert rc == 1 and "audit.mjs: drifted" in out, out


def test_new_published_module_that_is_neither_bundled_nor_excluded_fails(tmp_path):
    # The #157 footgun: a standalone module added to the published surface
    # used to be silently un-bundled.
    root = _mini_repo(tmp_path, js_files=JS_PUBLISHED + ["lineage.mjs"])
    rc, out = _run(root)
    assert rc == 1, out
    assert "lineage.mjs" in out and "neither bundled nor excluded" in out, out


def test_new_python_module_is_caught_the_same_way(tmp_path):
    root = _mini_repo(tmp_path, py_files=PY_PUBLISHED + ["lineage.py"])
    rc, out = _run(root)
    assert rc == 1 and "lineage.py" in out, out


def test_manifest_entry_the_package_no_longer_publishes_fails(tmp_path):
    # The reverse: a module removed from the package but still in the
    # manifest is a stale claim, not a pass.
    root = _mini_repo(tmp_path, js_files=[f for f in JS_PUBLISHED if f != "http.mjs"])
    rc, out = _run(root)
    assert rc == 1 and "http.mjs" in out and "does not publish" in out, out


def test_orphan_in_the_bundled_tree_fails(tmp_path):
    root = _mini_repo(tmp_path)
    _write(root, ".claude-plugin/bundled/primitives/python/old_audit.py", "# left behind\n")
    rc, out = _run(root)
    assert rc == 1 and "old_audit.py" in out and "orphan" in out, out


def test_pycache_in_the_bundled_tree_is_not_an_orphan(tmp_path):
    # Running the bundle-conformance suite imports the bundled modules and
    # writes __pycache__ next to them; a build artefact is not a shipped file.
    root = _mini_repo(tmp_path)
    _write(root, ".claude-plugin/bundled/primitives/python/__pycache__/audit.cpython-311.pyc", "")
    rc, out = _run(root)
    assert rc == 0, out


def test_the_real_repo_passes():
    p = subprocess.run(["node", _SCRIPT], capture_output=True, text=True, cwd=_ROOT)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "published surface accounted" in p.stdout
