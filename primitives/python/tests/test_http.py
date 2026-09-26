"""test_http — the classification core + the shared http-cases.json parity
fixture (its JS twin is primitives/js/http.test.mjs, same file). The adapter is
http_adapter.py, so importing it flat no longer shadows the stdlib `http` (#171)."""
import copy
import json
import os
import sys

_PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # primitives/python
sys.path.insert(0, _PY_DIR)  # so `marked` + the adapter's flat imports resolve

import pytest  # noqa: E402
import requests  # noqa: E402
import httpx  # noqa: E402
from marked import meta_of, unwrap  # noqa: E402
import http_adapter as plumb_http  # noqa: E402
from case_table_guards import table_problems  # noqa: E402

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

@pytest.mark.parametrize("c", CASES["parseAge"], ids=[c["name"] for c in CASES["parseAge"]])
def test_parse_age_fixture(c):
    r"""#224/#172 review: parse_age parity is table-driven — the shared list in
    http-cases.json (JS consumer: js/http.test.mjs) holds every hostile header
    a built-in coercion would mishandle. parse_age once dropped its try/except
    on the assumption the regex fully vetted its input; it did not — Python's
    \s matches the C0 separators U+001C-U+001F, which float() then rejects, so
    an Age of "\x1c60" raised straight out of classify_response and the
    requests/httpx taggers. Header bytes are remote-controlled, so a crash
    there is a worse failure than an ignored Age.
    """
    got = plumb_http.parse_age(c["raw"])
    if c["expect"] is None:
        assert got is None, repr(c["raw"])
    else:
        assert got == c["expect"], repr(c["raw"])
    # ...and the whole classification path stays total on the same input:
    # Age=0 reads as fresh; a positive Age as cached; a rejected-but-present
    # Age degrades — a signal we can see but cannot read is a statement about
    # our uncertainty, never evidence of freshness (#208).
    if c["raw"] is not None:
        confidence = "high" if c["expect"] == 0 else "medium"
        assert plumb_http.classify_response(200, {"Age": c["raw"]}) == ("real", confidence), repr(c["raw"])


# Every field, case kind and table version this runner interprets (#441), the
# guards cases.json has had since #369 and #433. Anything else in
# http-cases.json fails here instead of being ignored. JS twin: MODEL in
# primitives/js/http.test.mjs.
_MODEL = {
    "versions": [1],
    "meta": ["version"],
    "fields": {
        "classify": ["name", "status", "headers", "fromCache", "expect"],
        "parseAge": ["name", "raw", "expect"],
    },
}


def test_the_shipped_table_has_nothing_this_runner_ignores():
    assert table_problems(CASES, _MODEL) == []


def test_a_planted_unknown_field_fails():
    t = copy.deepcopy(CASES)
    t["classify"][0]["surprise"] = 1
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and "unknown field(s) surprise" in problems[0], problems


def test_a_planted_unknown_kind_fails():
    t = {**copy.deepcopy(CASES), "retry": []}
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and "unknown case kind retry" in problems[0], problems


def test_a_planted_unknown_version_fails():
    t = {**copy.deepcopy(CASES), "version": 2}
    problems = table_problems(t, _MODEL)
    assert len(problems) == 1 and "unknown case-table version 2" in problems[0], problems
