"""test_http — the classification core + the shared http-cases.json parity
fixture (its JS twin is primitives/js/http.test.mjs, same file). The stdlib `http`
package is kept intact against our sibling http.py by tests/conftest.py."""
import importlib.util
import json
import os
import sys

_PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # primitives/python
sys.path.insert(0, _PY_DIR)  # so `marked` + our http.py's flat imports resolve

import pytest  # noqa: E402
import requests  # noqa: E402
import httpx  # noqa: E402
from marked import meta_of, unwrap  # noqa: E402

# Load our http.py under a PRIVATE name — never bind sys.modules['http'] (stdlib
# http is preserved by tests/conftest.py). Do NOT use `import http`.
_spec = importlib.util.spec_from_file_location("_plumb_http_adapter", os.path.join(_PY_DIR, "http.py"))
plumb_http = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plumb_http)

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

def test_parse_age_never_raises_on_hostile_header_bytes():
    r"""#172 review: parse_age dropped the old try/except on the assumption that
    the regex fully vetted its input. It did not — Python's \s matches the C0
    separators U+001C-U+001F, which float() then rejects, so an Age of
    "\x1c60" raised straight out of classify_response and the requests/httpx
    taggers. Header bytes are remote-controlled, so a crash there is a worse
    failure than an ignored Age.
    """
    hostile = ['\x1c60', '\x1d60', '\x1e60', '\x1f60', '\x8560', '﻿60',
               '\xa060', ' 60', '　60', '٦٠', '0x10', '1_000', '1e3',
               'abc', '', '   ', '-5', '+60', '.5', '60.', 'Infinity', 'NaN']
    for raw in hostile:
        assert plumb_http.parse_age(raw) is None, repr(raw)
        # ...and the whole classification path stays total on the same input
        assert plumb_http.classify_response(200, {'Age': raw}) == ('real', 'high'), repr(raw)

def test_parse_age_accepts_only_ows_and_ascii_digits():
    # RFC 7230 OWS is SP/HTAB only; RFC 7234 delta-seconds is ASCII digits.
    assert plumb_http.parse_age('60') == 60.0
    assert plumb_http.parse_age(' 60 ') == 60.0
    assert plumb_http.parse_age('\t60\t') == 60.0
    assert plumb_http.parse_age('60.5') == 60.5
    assert plumb_http.parse_age(None) is None
