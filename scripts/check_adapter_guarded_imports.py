#!/usr/bin/env python3
"""Guard: with the adapter extras (`requests`/`httpx`/`pandas`/`numpy`) ABSENT, the
adapter modules must still import and their dependency-free surface must work,
while the taggers/wrappers raise a clear install-hinting ImportError. Run in CI
*before* installing test deps. Pure stdlib — no pytest, no third party."""
import importlib.util
import os
import sys

_PY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "primitives", "python")

# Sanity: the extras really are absent. This MUST run while sys.path is still
# clean — inserting _PY_DIR first would put a flat `http.py` ahead of the stdlib
# `http` package, breaking requests' internal `import http.client` and making a
# genuinely-installed requests look absent.
for lib in ("requests", "httpx", "pandas", "numpy"):
    try:
        __import__(lib)
        print(f"FAIL: {lib} is installed; this guard must run without extras")
        sys.exit(1)
    except ImportError:
        pass

sys.path.insert(0, _PY_DIR)  # so the adapters' flat `from marked import ...` resolves


def _load(name):
    """Load primitives/python/<name>.py under a private module name. For `http`
    this also avoids binding sys.modules['http'] (which would shadow the stdlib
    `http` package); frames/arrays don't clash but load the same way for uniformity."""
    spec = importlib.util.spec_from_file_location(f"_plumb_{name}", os.path.join(_PY_DIR, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- http adapter: dep-free core works; taggers raise install-hinting ImportError
plumb_http = _load("http")
assert plumb_http.classify_response(200, {}, False) == ("real", "high"), "classify_response broke without extras"
assert plumb_http.classify_response(500, {}, False) == ("unavailable", "none")
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

# --- dataframe adapters: module imports dep-free; construction raises install-hinting ImportError
for name, cls_name, hint in (("frames", "PlumbDataFrame", "pandas"), ("arrays", "PlumbArray", "numpy")):
    mod = _load(name)
    cls = getattr(mod, cls_name)
    try:
        cls(object())
        print(f"FAIL: {cls_name} did not raise ImportError without {hint}")
        sys.exit(1)
    except ImportError as e:
        assert hint in str(e) and "pip install" in str(e), f"{cls_name} ImportError lacks install hint: {e}"
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {cls_name} raised {type(e).__name__}, expected ImportError: {e}")
        sys.exit(1)

print("OK: adapter cores are dependency-free; taggers/wrappers guard-import with install hints")
