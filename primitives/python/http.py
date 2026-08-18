"""http — HTTP ingestion adapter for `requests`/`httpx`. Auto-tags a response with
a provenance envelope by status + cache state (see ADR-0012).

The classification core (`classify_response`) is dependency-free. The taggers and
convenience wrappers guard-import their library at call time, so importing this
module — and calling `classify_response` — needs no third-party package."""

import math
import re


def _header(headers, name):
    """Case-insensitive header read; supports a dict or a .get()-bearing object."""
    if headers is None:
        return None
    if hasattr(headers, "get") and not isinstance(headers, dict):
        # httpx.Headers / requests CaseInsensitiveDict: .get is already CI
        return headers.get(name)
    want = name.lower()
    for k, v in headers.items():
        if k.lower() == want:
            return v
    return None


# Age is RFC 7234 delta-seconds: a decimal number. Parsed by an explicit pattern
# rather than float()/Number() because the two languages' built-in coercions
# disagree on non-decimal strings — float("0x10") raises while JS Number("0x10")
# is 16, and float("1_000") is 1000 while Number("1_000") is NaN. Either coercion
# would make cache detection language-dependent (#172). A fractional part is
# tolerated because some proxies emit one and it is already pinned in the
# conformance table; anything else reads as "no usable Age".
# Mirror of parseAge in http.mjs.
# EVERY character class is spelled explicitly. Neither \d nor \s may be used
# here: Python's are Unicode-aware and JS's (without the u flag) are not, in
# BOTH directions —
#   \d : Python accepts Arabic-Indic "٦٠", JS rejects it.
#   \s : Python matches U+0085 (JS does not) and not U+FEFF (JS does), and
#        Python's \s covers U+001C–001F, which float() then REJECTS — so a
#        header of "\x1c60" passed the regex and raised out of the tagger.
# Surrounding space is [ \t] because RFC 7230 OWS is SP/HTAB only; anything
# else is not optional whitespace around a header value, it is a malformed
# value. Getting this wrong replaces a coercion divergence with a regex one.
_AGE_DECIMAL = re.compile(r'^[ \t]*[0-9]+(\.[0-9]+)?[ \t]*$')


def parse_age(raw):
    """Age header as a float, or None when it is not a decimal value.

    Total by construction: never raises, whatever the remote sent. The pattern
    above admits only ASCII digits and SP/HTAB, so float() cannot fail — the
    try/except is a belt-and-braces guarantee, because this runs on
    attacker-controlled header bytes and a crash in the tagging path is a worse
    failure than an ignored Age.
    """
    if raw is None:
        return None
    s = str(raw)
    if not _AGE_DECIMAL.match(s):
        return None
    try:
        n = float(s)
    except (ValueError, OverflowError):
        return None
    return n if math.isfinite(n) else None


def _is_cached(status, headers, from_cache):
    if from_cache:
        return True
    if status == 304:
        return True
    age = _header(headers, "age")
    if age is not None:
        n = parse_age(age)
        if n is not None and n > 0:
            return True
    x_cache = _header(headers, "x-cache")
    if x_cache is not None and "HIT" in str(x_cache).upper():
        return True
    return False


def classify_response(status, headers, from_cache=False):
    """Map an HTTP response to (source, confidence). source = origin trust,
    confidence = freshness. A cache hit stays 'real', only confidence drops.
    Never returns 'fallback' (reserved for caller-supplied substitutes)."""
    cached = _is_cached(status, headers, from_cache)
    if status == 304:
        return ("real", "medium")
    if 200 <= status < 300:
        if cached:
            return ("real", "medium")
        age = _header(headers, "age")
        if age is not None and parse_age(age) is None:
            # Age present but unreadable: a staleness signal we can see but
            # cannot parse is a statement about our uncertainty, never
            # evidence of freshness — degrade, don't upgrade (#208, ADR).
            return ("real", "medium")
        return ("real", "high")
    return ("unavailable", "none")


try:  # installed as a package (plumb_line_provenance)
    from .marked import mark
except ImportError:  # flat / copy-paste usage (modules on sys.path)
    from marked import mark

_INSTALL = 'install it with: pip install "plumb-line-provenance[{extra}]"'


def _tag(response, headers, status, from_cache=False):
    source, confidence = classify_response(status, headers, from_cache)
    return mark(response, source=source, confidence=confidence)


def tag_requests(response):
    """Tag a `requests.Response` with a provenance envelope by status/cache.
    The marked value is the response itself; extract via
    `derive([tagged], lambda r: r.json())`."""
    try:
        import requests
    except ImportError as e:  # pragma: no cover - exercised in the no-extras CI step
        raise ImportError("tag_requests needs `requests`; " + _INSTALL.format(extra="requests")) from e
    if not isinstance(response, requests.Response):
        raise TypeError(f"tag_requests expects a requests.Response, got {type(response).__name__}")
    return _tag(response, response.headers, response.status_code,
                from_cache=bool(getattr(response, "from_cache", False)))


def tag_httpx(response):
    """Tag an `httpx.Response` with a provenance envelope by status/cache."""
    try:
        import httpx
    except ImportError as e:  # pragma: no cover - exercised in the no-extras CI step
        raise ImportError("tag_httpx needs `httpx`; " + _INSTALL.format(extra="httpx")) from e
    if not isinstance(response, httpx.Response):
        raise TypeError(f"tag_httpx expects an httpx.Response, got {type(response).__name__}")
    return _tag(response, response.headers, response.status_code,
                from_cache=bool(getattr(response, "from_cache", False)))


def tagged_get(url, **kwargs):
    """Fetch with `requests.get` and tag the response in one call."""
    try:
        import requests
    except ImportError as e:  # pragma: no cover - exercised in the no-extras CI step
        raise ImportError("tagged_get needs `requests`; " + _INSTALL.format(extra="requests")) from e
    return tag_requests(requests.get(url, **kwargs))


def tagged_httpx_get(url, **kwargs):
    """Fetch with `httpx.get` and tag the response in one call."""
    try:
        import httpx
    except ImportError as e:  # pragma: no cover - exercised in the no-extras CI step
        raise ImportError("tagged_httpx_get needs `httpx`; " + _INSTALL.format(extra="httpx")) from e
    return tag_httpx(httpx.get(url, **kwargs))
