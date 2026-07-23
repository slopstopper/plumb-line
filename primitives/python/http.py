"""http — HTTP ingestion adapter for `requests`/`httpx`. Auto-tags a response with
a provenance envelope by status + cache state (see ADR-0012).

The classification core (`classify_response`) is dependency-free. The taggers and
convenience wrappers guard-import their library at call time, so importing this
module — and calling `classify_response` — needs no third-party package."""

import math


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


def _is_cached(status, headers, from_cache):
    if from_cache:
        return True
    if status == 304:
        return True
    age = _header(headers, "age")
    if age is not None:
        try:
            n = float(age)
        except (ValueError, TypeError):
            n = None
        if n is not None and math.isfinite(n) and n > 0:
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
        return ("real", "medium") if cached else ("real", "high")
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
