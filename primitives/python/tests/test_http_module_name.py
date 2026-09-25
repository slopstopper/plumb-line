"""The HTTP adapter must not shadow the stdlib `http` package (#171).

It shipped as `http.py`; with this directory on sys.path (the documented flat
copy-paste path, or a test runner) `import http.client` resolved to it and
broke requests/httpx. The file is now `http_adapter.py`, and the installed
`plumb_line_provenance.http` path is kept as an alias so existing imports work.

Each check runs in a subprocess so this session's sys.modules stays clean."""
import os
import subprocess
import sys

_PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(code):
    return subprocess.run([sys.executable, '-c', code], cwd=_PY_DIR,
                          capture_output=True, text=True)


def test_no_module_named_http_in_the_package_dir():
    assert not os.path.exists(os.path.join(_PY_DIR, 'http.py'))


def test_flat_import_leaves_stdlib_http_intact():
    out = _run('import sys; sys.path.insert(0, "."); import http_adapter; import http.client; '
               'print(http.client.__file__)')
    assert out.returncode == 0, out.stderr
    assert not out.stdout.strip().startswith(_PY_DIR)


def test_installed_http_path_is_an_alias_of_http_adapter():
    # Load the directory as the package under its published name, as an
    # install would (same technique as scripts/test_fit_map_snippets.py).
    out = _run(
        'import importlib.util, os, sys\n'
        'spec = importlib.util.spec_from_file_location("plumb_line_provenance", "__init__.py",'
        ' submodule_search_locations=[os.getcwd()])\n'
        'pkg = importlib.util.module_from_spec(spec); sys.modules["plumb_line_provenance"] = pkg\n'
        'spec.loader.exec_module(pkg)\n'
        'from plumb_line_provenance.http import tag_requests\n'
        'import plumb_line_provenance.http as old, plumb_line_provenance.http_adapter as new\n'
        'assert old is new and tag_requests is new.tag_requests\n'
        'import http.client\n'
        'print("ok")\n')
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == 'ok'
