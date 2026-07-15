#!/usr/bin/env python3
"""Guard: with `requests`/`httpx` ABSENT, the http adapter core must still import
and `classify_response` must work, while the taggers raise a clear ImportError.
Run in CI *before* installing test deps. Pure stdlib — no pytest, no third party."""
import importlib.util
import os
import sys

_PY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "primitives", "python")

# Sanity: the libs really are absent in this environment. This MUST run while
# sys.path is still clean — inserting _PY_DIR first would put a flat `http.py`
# ahead of the stdlib `http` package, breaking requests' internal
# `import http.client` and making a genuinely-installed requests look absent.
for lib in ("requests", "httpx"):
    try:
        __import__(lib)
        print(f"FAIL: {lib} is installed; this guard must run without extras")
        sys.exit(1)
    except ImportError:
        pass

sys.path.insert(0, _PY_DIR)  # so http.py's flat `from marked import mark` resolves

# Load http.py under a private name so we never bind sys.modules['http'] to it —
# that would shadow the stdlib `http` package and break `import http.client`.
_spec = importlib.util.spec_from_file_location("_plumb_http_adapter", os.path.join(_PY_DIR, "http.py"))
plumb_http = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plumb_http)

# 1. Dependency-free core works.
assert plumb_http.classify_response(200, {}, False) == ("real", "high"), "classify_response broke without extras"
assert plumb_http.classify_response(500, {}, False) == ("unavailable", "none")

# 2. Taggers raise a clear, install-hinting ImportError.
for fn, hint in ((plumb_http.tag_requests, "requests"), (plumb_http.tag_httpx, "httpx")):
    try:
        fn(object())
        print(f"FAIL: {fn.__name__} did not raise ImportError without {hint}")
        sys.exit(1)
    except ImportError as e:
        assert hint in str(e) and "pip install" in str(e), f"{fn.__name__} ImportError lacks install hint: {e}"
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {fn.__name__} raised {type(e).__name__}, expected ImportError: {e}")
        sys.exit(1)

print("OK: http adapter core is dependency-free; taggers guard-import with install hints")
