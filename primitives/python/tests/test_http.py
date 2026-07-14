"""test_http — the classification core + the shared http-cases.json parity
fixture (its JS twin is primitives/js/http.test.mjs, same file)."""
import importlib.util
import json
import os
import sys

# primitives/python must be on the path so http.py's own flat `from marked import
# mark` resolves. But we must NOT do `import http` — that binds sys.modules['http']
# to our module and shadows the stdlib `http` PACKAGE, breaking requests/httpx's
# internal `import http.client` (see Task 2). Load our module under a private name
# via importlib so the stdlib `http` package stays intact.
_PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # primitives/python
sys.path.insert(0, _PY_DIR)
_spec = importlib.util.spec_from_file_location("_plumb_http_adapter", os.path.join(_PY_DIR, "http.py"))
plumb_http = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plumb_http)  # RED before Step 8: http.py absent -> FileNotFoundError

_CASES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "conformance", "http-cases.json",
)
with open(_CASES) as f:
    CASES = json.load(f)

import pytest

@pytest.mark.parametrize("c", CASES["classify"], ids=[c["name"] for c in CASES["classify"]])
def test_classify_fixture(c):
    source, confidence = plumb_http.classify_response(c["status"], c["headers"], c["fromCache"])
    assert {"source": source, "confidence": confidence} == c["expect"]


class _GetHeaders:
    """A .get()-bearing, case-insensitive Headers stub (httpx.Headers-shaped)."""
    def __init__(self, d):
        self._d = {k.lower(): v for k, v in d.items()}
    def get(self, k, default=None):
        return self._d.get(k.lower(), default)

def test_classify_accepts_get_bearing_headers():
    assert plumb_http.classify_response(200, _GetHeaders({"Age": "60"}), False) == ("real", "medium")
