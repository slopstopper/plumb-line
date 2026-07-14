"""http — HTTP ingestion adapter for `requests`/`httpx`. Auto-tags a response with
a provenance envelope by status + cache state (see ADR-0012).

The classification core (`classify_response`) is dependency-free. The taggers and
convenience wrappers guard-import their library at call time, so importing this
module — and calling `classify_response` — needs no third-party package. Added in
a later task."""

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
