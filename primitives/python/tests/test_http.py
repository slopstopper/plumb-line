"""test_http — the classification core + the shared http-cases.json parity
fixture (its JS twin is primitives/js/http.test.mjs, same file)."""
import importlib.util
import json
import os
import sys

# primitives/python contains our own http.py. `python3 -m pytest` (run from
# primitives/python, per this suite's own run instructions) already has that
# directory on sys.path by the time this module's code starts running (as the
# cwd entry '' and/or an absolute-path entry pytest itself inserts for rootdir
# discovery — verified empirically, not just via the '' convention). If the
# very first `import http.client` (done internally by requests/httpx, see
# Task 2) hits while that directory is still on sys.path, 'http' resolves to
# our plain-module http.py instead of the stdlib package and blows up with
# "'http' is not a package". So: compute _PY_DIR, strip every sys.path entry
# that points at it (in any spelling) plus the cwd placeholders, pre-cache the
# real stdlib `http` package in sys.modules, *then* put _PY_DIR back (as an
# explicit absolute path, needed below for http.py's own flat `from marked
# import mark`). Once cached, later imports resolve 'http'/'http.client' from
# sys.modules and never re-search sys.path, so our http.py can't shadow it.
_PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # primitives/python
sys.path = [p for p in sys.path if p not in ("", ".", _PY_DIR) and os.path.abspath(p or ".") != _PY_DIR]
import http.client  # noqa: E402,F401 — must follow the sys.path fix above; see rationale above

# Grouped here (rather than at each first use) so this is the only place E402
# fires: once http.client is cached, ordering no longer matters for these.
import httpx  # noqa: E402
import pytest  # noqa: E402
import requests  # noqa: E402
from marked import meta_of, unwrap  # noqa: E402

# We must NOT do `import http` for our OWN module — that would bind
# sys.modules['http'] to it and shadow the stdlib `http` package we just
# secured above. Load our module under a private name via importlib instead.
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


def _requests_response(status, headers=None):
    r = requests.Response()
    r.status_code = status
    r.headers.update(headers or {})
    return r

def test_tag_requests_fresh_200():
    m = plumb_http.tag_requests(_requests_response(200))
    assert meta_of(m)["source"] == "real"
    assert meta_of(m)["confidence"] == "high"
    assert unwrap(m).status_code == 200  # the response is the marked value

def test_tag_requests_stale_cache():
    m = plumb_http.tag_requests(_requests_response(200, {"Age": "60"}))
    assert (meta_of(m)["source"], meta_of(m)["confidence"]) == ("real", "medium")

def test_tag_requests_404_unavailable():
    m = plumb_http.tag_requests(_requests_response(404))
    assert (meta_of(m)["source"], meta_of(m)["confidence"]) == ("unavailable", "none")

def test_tag_requests_rejects_non_response():
    with pytest.raises(TypeError):
        plumb_http.tag_requests({"status_code": 200})  # not a requests.Response

def test_tag_httpx_fresh_200():
    m = plumb_http.tag_httpx(httpx.Response(200))
    assert (meta_of(m)["source"], meta_of(m)["confidence"]) == ("real", "high")

def test_tag_httpx_stale_cache():
    m = plumb_http.tag_httpx(httpx.Response(200, headers={"Age": "5"}))
    assert (meta_of(m)["source"], meta_of(m)["confidence"]) == ("real", "medium")

def test_tagged_get_calls_requests_and_tags(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url, **kw: _requests_response(200))
    m = plumb_http.tagged_get("https://example.test/data")
    assert (meta_of(m)["source"], meta_of(m)["confidence"]) == ("real", "high")

def test_tagged_httpx_get_calls_httpx_and_tags(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: httpx.Response(200))
    m = plumb_http.tagged_httpx_get("https://example.test/data")
    assert (meta_of(m)["source"], meta_of(m)["confidence"]) == ("real", "high")
